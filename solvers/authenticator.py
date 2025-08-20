import json
import os
import requests
import time
from .credential_manager import CredentialManager

class Authenticator:
    def __init__(self, config_path="./config/system.json"):
        self.config_path = config_path
        self.credential_manager = CredentialManager(config_path)
        self.config = self._load_config()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.112 Safari/537.36",
            "Referer": "https://ak.hypergryph.com/",
        })
        self.u8_token = None
        self.game_uid = None
    
    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return {}
    
    def authenticate(self, account_config_path, user_uid=None):
        """
        执行完整的身份验证流程。
        :param account_config_path: 账户配置文件的路径。
        :param user_uid: 系统用户ID，用于创建目录结构。
        :return: 包含已认证session和game_uid的字典，成功则返回字典，失败则返回None。
        """
        try:
            credentials = self.credential_manager.load_credentials(account_config_path, skip_token=True)
            if not credentials:
                print("无法加载凭证")
                return None
            
            if "username" in credentials and "password" in credentials:
                initial_token = self._get_initial_token(credentials["username"], credentials["password"])
                if not initial_token:
                    print("无法获取初始token")
                    return None
                
                self._perform_csrf_request()
                
                app_token = self._get_app_token(initial_token)
                if not app_token:
                    print("无法获取app_token")
                    return None
                
                self.game_uid = self._get_default_game_uid(app_token)
                if not self.game_uid:
                    print("无法获取默认角色UID")
                    return None
                
                self.u8_token = self._get_u8_token(app_token, self.game_uid)
                if not self.u8_token:
                    print("无法获取u8_token")
                    return None
                
                if not self._login_role(self.u8_token):
                    print("角色登录失败")
                    return None
                
                self._create_user_directory(user_uid, self.game_uid)
                
                print("认证成功")
                
                self.session.headers.update({
                    "X-Role-Token": self.u8_token
                })
                return {
                    "session": self.session,
                    "game_uid": self.game_uid
                }
            
            return None
        except Exception as e:
            print(f"认证过程中出错: {e}")
            return None
    
    def _get_initial_token(self, phone, password):
        try:
            auth_data = {
                "phone": phone,
                "password": password
            }
            
            response = self.session.post(
                self.config["api_endpoints"]["initial_auth"],
                json=auth_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 0:
                    return result["data"]["token"]
            else:
                print(f"获取初始token请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取初始token时出错: {e}")
        
        return None

    def _get_app_token(self, initial_token):
        try:
            app_data = {
                "token": initial_token,
                "appCode": "be36d44aa36bfb5b",
                "type": 1
            }
            
            response = self.session.post(
                self.config["api_endpoints"]["app_token"],
                json=app_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 0:
                    return result["data"]["token"]
            else:
                print(f"获取app_token请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取app_token时出错: {e}")
        
        return None

    def _get_default_game_uid(self, app_token):
        try:
            params = {
                "token": app_token,
                "appCode": "arknights"
            }
            
            response = self.session.get(
                self.config["api_endpoints"]["binding_list"],
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 0:
                    data_list = result.get("data", {}).get("list", [])
                    
                    if not data_list:
                        print("警告: API返回的app列表为空，该账号可能未绑定任何游戏。")
                        return None

                    found_default_uid = None
                    for app in data_list:
                        for binding in app.get("bindingList", []):
                            if binding.get("isDefault") is True:
                                found_default_uid = binding.get("uid")
                                return found_default_uid
                    
                    if not found_default_uid:
                        print("警告: 未找到任何被标记为isDefault的角色。")
                        if data_list and data_list[0].get("bindingList"):
                            first_binding_uid = data_list[0]["bindingList"][0].get("uid")
                            print(f"未找到默认角色，将使用第一个找到的角色UID作为备选: {first_binding_uid}")
                            return first_binding_uid
                        else:
                            print("错误: app列表或bindingList为空，无法提供备选UID。")
                            return None
                else:
                    print(f"获取角色列表API返回错误状态: {result.get('status')}, 消息: {result.get('msg')}")
            else:
                print(f"获取角色列表请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取默认角色UID时出错: {e}")
        
        return None

    def _get_u8_token(self, app_token, game_uid):
        try:
            u8_data = {
                "token": app_token,
                "uid": game_uid
            }
            
            response = self.session.post(
                self.config["api_endpoints"]["u8_token"],
                json=u8_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 0:
                    return result["data"]["token"]
            else:
                print(f"获取u8_token请求失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"获取u8_token时出错: {e}")
        
        return None

    def _login_role(self, u8_token):
        try:
            url = self.config["api_endpoints"]["role_login"]
            login_data = {
                "token": u8_token,
                "source_from": "",
                "share_type": "",
                "share_by": ""
            }

            response = self.session.post(url, json=login_data)
            
            return response.status_code == 200
        except Exception as e:
            print(f"角色登录时出错: {e}")
        
        return False

    def _perform_csrf_request(self):
        try:
            self.session.get(self.config["api_endpoints"].get("csrf", "https://ak.hypergryph.com/user"))
        except Exception as e:
            print(f"CSRF请求时出错: {e}")

    def _get_game_uid_with_u8_token(self, u8_token):
        try:
            params = {
                "token": u8_token,
                "appCode": "arknights"
            }
            
            original_token = self.session.headers.get("X-Role-Token")
            self.session.headers.update({"X-Role-Token": u8_token})
            
            response = self.session.get(
                self.config["api_endpoints"]["binding_list"],
                params=params
            )
            
            if original_token:
                self.session.headers.update({"X-Role-Token": original_token})
            else:
                self.session.headers.pop("X-Role-Token", None)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 0:
                    for app in result.get("data", {}).get("list", []):
                        for binding in app.get("bindingList", []):
                            if binding.get("isDefault") is True:
                                return binding.get("uid")
            else:
                print(f"使用u8_token获取角色列表失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"使用u8_token获取游戏账号UID时出错: {e}")
        
        return None

    def _create_user_directory(self, user_uid, game_uid):
        try:
            if not user_uid:
                user_uid = "default_user"
            
            user_dir = f"./users/{user_uid}/accounts/{game_uid}"
            os.makedirs(user_dir, exist_ok=True)
        except Exception as e:
            print(f"创建用户目录时出错: {e}")


if __name__ == "__main__":
    auth = Authenticator()
    result = auth.authenticate("./users/example_user/accounts/example_account/account_config.json", "example_user")
    if result:
        print(f"认证成功，令牌: {result['token']}, 游戏UID: {result['game_uid']}")
    else:
        print("认证失败")
