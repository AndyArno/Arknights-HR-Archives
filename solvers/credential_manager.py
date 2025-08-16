import json
import os
from cryptography.fernet import Fernet, InvalidToken

class CredentialManager:
    def __init__(self, config_path="./config/system.json"):
        self.config_path = config_path
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_generate_key(self):
        """加载或生成加密密钥"""
        key_file = "./config/secret.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def load_credentials(self, account_config_path, skip_token=False):
        """从账户配置文件加载凭证。
        如果检测到明文密码，会自动加密并更新配置文件。
        
        Args:
            account_config_path: 账户配置文件路径。
            skip_token: 是否跳过令牌加载，默认为False。
        """
        try:
            with open(account_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # 解密凭证 (token)
            encrypted_token = config.get("encrypted_token")
            if encrypted_token and not skip_token:
                token = self.cipher.decrypt(encrypted_token.encode()).decode()
                return {"token": token}
            
            # 如果没有加密令牌，尝试获取用户名和密码
            username = config.get("username")
            password = config.get("password")
            if username and password:
                # 尝试解密密码，如果失败则说明是明文
                try:
                    decrypted_password = self.cipher.decrypt(password.encode()).decode()
                    # 解密成功，说明密码已经是加密的
                    return {"username": username, "password": decrypted_password}
                except InvalidToken:
                    # 捕获到InvalidToken错误，说明密码是明文
                    print("检测到明文密码，将自动为您加密并更新配置文件...")
                    
                    # 准备要加密并保存的凭证
                    credentials_to_save = {
                        "username": username,
                        "password": password
                    }
                    
                    # 调用加密方法覆盖原文件
                    self.encrypt_and_save_credentials(credentials_to_save, account_config_path)
                    
                    # 对于本次运行，直接返回明文密码以确保流程继续
                    print("配置文件已更新。本次将使用明文密码继续。")
                    return {"username": username, "password": password}
            
            return None
        except FileNotFoundError:
            print(f"加载凭证时出错: 找不到文件 {account_config_path}")
            return None
        except json.JSONDecodeError:
            print(f"加载凭证时出错: 文件 {account_config_path} 不是有效的JSON格式。")
            return None
        except Exception as e:
            # 保留一个通用的异常捕获，用于处理其他意外情况
            print(f"加载凭证时发生未知错误: {e}")
            return None
    
    def encrypt_and_save_credentials(self, credentials, account_config_path):
        """加密并保存凭证到账户配置文件"""
        try:
            # 如果文件存在，先加载现有配置
            if os.path.exists(account_config_path):
                with open(account_config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}
            
            # 加密凭证
            if "token" in credentials:
                encrypted_token = self.cipher.encrypt(credentials["token"].encode()).decode()
                config["encrypted_token"] = encrypted_token
            elif "username" in credentials and "password" in credentials:
                config["username"] = credentials["username"]
                encrypted_password = self.cipher.encrypt(credentials["password"].encode()).decode()
                config["password"] = encrypted_password
            
            # 保存到文件
            os.makedirs(os.path.dirname(account_config_path), exist_ok=True)
            with open(account_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存凭证时出错: {e}")
            return False
