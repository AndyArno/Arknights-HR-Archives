import os
import sys
import json

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solvers.credential_manager import CredentialManager
from solvers.authenticator import Authenticator
from solvers.gacha_data_storer import GachaDataStorer

def test_credential_manager():
    """测试凭证管理模块"""
    print("--- 正在测试凭证管理模块 ---")
    cm = CredentialManager()
    config_path = "./users/test/accounts/test_account/config.json"
    
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        print("请确保您已在配置文件中填写了真实的账号密码")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_credentials = json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None

    if "username" in user_credentials and "password" in user_credentials:
        try:
            cm.cipher.decrypt(user_credentials["password"].encode()).decode()
            print("凭证已加密，直接加载。")
        except:
            print("凭证未加密，正在加密并保存...")
            cm.encrypt_and_save_credentials(user_credentials, config_path)
        
        return cm.load_credentials(config_path)
    else:
        print("配置文件中的凭证格式不正确，请确保包含username和password字段")
        return None

def test_authenticator():
    """测试身份认证模块"""
    print("\n--- 正在测试身份认证模块 ---")
    auth = Authenticator()
    config_path = "./users/test/accounts/test_account/config.json"
    
    print("开始认证...")
    result = auth.authenticate(config_path, "test")
    
    if result:
        print(f"认证成功，游戏UID: {result['game_uid']}")
        return auth
    else:
        print("认证失败，请检查账号信息和网络连接。")
        return None

def test_data_fetcher(authenticator: Authenticator):
    """测试数据获取模块"""
    print("\n--- 正在测试数据获取模块 ---")
    fetcher = authenticator
    
    print("开始获取寻访记录...")
    records = fetcher.fetch_all_gacha_records()
    
    if records is not None:
        print(f"成功获取 {len(records)} 条寻访记录。")
        return records
    else:
        print("获取寻访记录失败。")
        return None

def test_data_storer(records, user_uid, game_uid):
    """测试数据存储模块"""
    print("\n--- 正在测试数据存储模块 ---")
    storer = GachaDataStorer()
    
    print(f"准备增量保存 {len(records)} 条记录...")
    result = storer.save_incremental_records(records, user_uid, game_uid)
    
    if result:
        print("保存成功。")
        return True
    else:
        print("保存失败。")
        return False

def main():
    """主测试函数"""
    print("开始执行端到端测试...")
    
    credentials = test_credential_manager()
    if not credentials:
        print("\n凭证管理模块测试失败，终止测试。")
        return
    print("凭证管理模块测试通过。")
    
    auth_result = test_authenticator()
    if not auth_result:
        print("\n身份认证模块测试失败，终止测试。")
        return
    print("身份认证模块测试通过。")
    
    records = test_data_fetcher(auth_result)
    if records is None:
        print("\n数据获取模块测试失败，终止测试。")
        return
    print("数据获取模块测试通过。")
    
    store_result = test_data_storer(records, "test", auth_result.game_uid)
    if not store_result:
        print("\n数据存储模块测试失败。")
        return
    print("数据存储模块测试通过。")
    
    print("\n所有模块测试完成！")

if __name__ == "__main__":
    main()
