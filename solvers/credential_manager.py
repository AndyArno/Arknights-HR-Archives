import json
import os
from cryptography.fernet import Fernet

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
        """从账户配置文件加载凭证
        
        Args:
            account_config_path: 账户配置文件路径
            skip_token: 是否跳过令牌加载，默认为False
        """
        try:
            with open(account_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # 解密凭证
            encrypted_token = config.get("encrypted_token")
            if encrypted_token and not skip_token:
                token = self.cipher.decrypt(encrypted_token.encode()).decode()
                return {"token": token}
            
            # 如果没有加密令牌，尝试获取用户名和密码
            username = config.get("username")
            password = config.get("password")
            if username and password:
                # 解密密码
                decrypted_password = self.cipher.decrypt(password.encode()).decode()
                return {"username": username, "password": decrypted_password}
            
            return None
        except Exception as e:
            print(f"加载凭证时出错: {e}")
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
