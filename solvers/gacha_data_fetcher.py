import json
import time

class GachaDataFetcher:
    def __init__(self, session, game_uid, config_path="./config/system.json"):
        """
        初始化数据获取器。
        :param session: 一个已经完成认证的 requests.Session 对象，包含 X-Role-Token。
        :param game_uid: 游戏角色的 UID。
        :param config_path: 系统配置文件路径。
        """
        self.session = session
        self.game_uid = game_uid
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return {}

    def fetch_gacha_pool_ids(self):
        """获取所有可用的卡池ID列表"""
        try:
            url = self.config["api_endpoints"]["gacha_cate"]
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"获取卡池信息失败，状态码: {response.status_code}")
                return None
            
            result = response.json()
            if result.get("code") != 0:
                print(f"获取卡池信息失败: {result.get('msg', '未知错误')}")
                return None
            
            pool_data_list = result.get("data", [])
            pool_id_list = [item["id"] for item in pool_data_list]
            
            return pool_id_list
        except Exception as e:
            print(f"获取卡池信息时出错: {e}")
            return None

    def fetch_all_gacha_records(self):
        """获取该账号下所有的寻访记录"""
        if not self.game_uid:
            print("游戏UID未设置，无法获取寻访记录")
            return None
            
        try:
            all_records = []
            pool_id_list = self.fetch_gacha_pool_ids()

            if not pool_id_list:
                print("未能获取到卡池ID列表")
                return None

            for pool_id in pool_id_list:
                params = {
                    "uid": self.game_uid,
                    "category": pool_id,
                    "size": 50
                }
                
                while True:
                    response = self.session.get(
                        self.config["api_endpoints"]["gacha_records"],
                        params=params
                    )
                    
                    if response.status_code != 200:
                        print(f"获取寻访记录失败，状态码: {response.status_code}")
                        print(f"Response content: {response.text}")
                        return None
                    
                    result = response.json()
                    if result.get("code") != 0:
                        print(f"获取寻访记录失败: {result.get('msg', '未知错误')}")
                        return None
                    
                    records = result.get("data", {}).get("list", [])
                    if not records:
                        break
                    
                    # 为每条记录添加 poolType 字段
                    for record in records:
                        record["poolType"] = pool_id
                    
                    all_records.extend(records)
                    
                    has_more = result.get("data", {}).get("hasMore", False)
                    if not has_more:
                        break
                    
                    last_record = records[-1]
                    params["gachaTs"] = last_record["gachaTs"]
                    params["pos"] = last_record["pos"]
                    
                    # 添加延时，避免请求过于频繁
                    time.sleep(0.5)
            
            print(f"总共获取到 {len(all_records)} 条寻访记录")
            return all_records

        except Exception as e:
            print(f"获取寻访记录时出错: {e}")
            return None

if __name__ == "__main__":
    # 这个部分用于独立测试 GachaDataFetcher
    # 需要手动提供一个已认证的 session 和 game_uid
    print("GachaDataFetcher 需要一个已认证的 session 和 game_uid 才能运行。")
    print("请通过 main_orchestrator.py 进行完整流程测试。")
