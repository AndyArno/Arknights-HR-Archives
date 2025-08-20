import json
import os
from datetime import datetime
from collections import defaultdict

class GachaDataStorer:
    POOL_TYPE_MAPPING = {
        "normal": 1,
        "classic": 2,
    }
    
    def __init__(self, config_path="./config/system.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return {}
    
    def _map_pool_type(self, pool_type_id):
        """将卡池类型ID映射到整数代码"""
        # 如果在映射中，使用映射值；否则默认为 0 (限定寻访)
        return self.POOL_TYPE_MAPPING.get(pool_type_id, 0)
    
    def _write_compact_json(self, data, fp):
        """
        将数据以指定的紧凑格式写入文件对象。
        格式：外层对象有缩进，内层数组元素在同一行。
        """
        fp.write('{\n')
        num_items = len(data)
        for i, (ts, record) in enumerate(data.items()):
            fp.write(f'  "{ts}": {{\n')
            fp.write(f'    "p": {json.dumps(record["p"], ensure_ascii=False)},\n')
            fp.write(f'    "pt": {record["pt"]},\n')
            fp.write(f'    "c": [\n')
            
            num_chars = len(record['c'])
            for j, char_list in enumerate(record['c']):
                fp.write(f'      {json.dumps(char_list, ensure_ascii=False)}')
                if j < num_chars - 1:
                    fp.write(',')
                fp.write('\n')
                
            fp.write(f'    ]\n')
            fp.write(f'  }}')
            if i < num_items - 1:
                fp.write(',')
            fp.write('\n')
        fp.write('}\n')
    
    def _transform_records_for_saving(self, records):
        """将原始记录列表转换为新的紧凑JSON格式"""
        if not records:
            return {}
        
        grouped_data = defaultdict(list)
        
        for record in records:
            ts_in_seconds = str(int(record["gachaTs"]) // 1000)
            grouped_data[ts_in_seconds].append(record)
        
        final_data = {}
        for ts, record_list in grouped_data.items():
            first_record = record_list[0]
            pool_name = first_record.get("poolName", "未知卡池")
            pool_type_id = first_record.get("poolType", "unknown")
            pool_type_code = self._map_pool_type(pool_type_id)
            
            chars_data = []
            for record in record_list:
                char_data = [
                    record.get("charName", "未知角色"),
                    record.get("rarity", 0) + 1,
                    1 if record.get("isNew", False) else 0
                ]
                chars_data.append(char_data)
            
            final_data[ts] = {
                "p": pool_name,
                "pt": pool_type_code,
                "c": chars_data
            }
        
        return final_data
    
    def save_gacha_records(self, records, user_uid, game_uid):
        try:
            if not user_uid:
                user_uid = "default_user"
            
            data_dir = f"./users/{user_uid}/accounts/{game_uid}"
            data_file_path = os.path.join(data_dir, "data.json")
            metadata_file_path = os.path.join(data_dir, "metadata.json")
            
            os.makedirs(data_dir, exist_ok=True)
            
            # 读取现有数据
            existing_data = {}
            if os.path.exists(data_file_path):
                with open(data_file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            
            transformed_data = self._transform_records_for_saving(records)
            
            # 合并数据
            existing_data.update(transformed_data)
            
            sorted_ts = sorted(existing_data.keys(), key=int, reverse=True)
            sorted_transformed_data = {ts: existing_data[ts] for ts in sorted_ts}

            with open(data_file_path, "w", encoding="utf-8") as f:
                self._write_compact_json(sorted_transformed_data, f)
            
            metadata = {
                "last_update": datetime.now().isoformat(),
                "game_uid": game_uid,
                "record_count": len(sorted_transformed_data)
            }
            with open(metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"已保存 {len(records)} 条寻访记录到 {data_file_path}")
            print(f"已保存元数据到 {metadata_file_path}")
            return True
        except Exception as e:
            print(f"保存寻访记录时出错: {e}")
            return False
    
    def save_incremental_records(self, new_records, user_uid, game_uid):
        try:
            if not user_uid:
                user_uid = "default_user"
            
            data_dir = f"./users/{user_uid}/accounts/{game_uid}"
            data_file_path = os.path.join(data_dir, "data.json")
            metadata_file_path = os.path.join(data_dir, "metadata.json")
            
            existing_data = {}
            if os.path.exists(data_file_path):
                with open(data_file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            
            new_data = self._transform_records_for_saving(new_records)
            
            existing_data.update(new_data)
            
            sorted_ts = sorted(existing_data.keys(), key=int, reverse=True)
            sorted_existing_data = {ts: existing_data[ts] for ts in sorted_ts}
            
            os.makedirs(data_dir, exist_ok=True)
            
            with open(data_file_path, "w", encoding="utf-8") as f:
                self._write_compact_json(sorted_existing_data, f)
            
            metadata = {
                "last_update": datetime.now().isoformat(),
                "game_uid": game_uid,
                "record_count": len(sorted_existing_data)
            }
            with open(metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"已增量保存 {len(new_records)} 条新寻访记录到 {data_file_path}")
            print(f"已更新元数据到 {metadata_file_path}")
            return True
        except Exception as e:
            print(f"增量保存寻访记录时出错: {e}")
            return False
    
    def load_gacha_data(self, user_uid, game_uid):
        """加载寻访数据文件 (data.json)"""
        try:
            if not user_uid:
                user_uid = "default_user"
            
            data_file_path = f"./users/{user_uid}/accounts/{game_uid}/data.json"
            
            if not os.path.exists(data_file_path):
                print(f"数据文件不存在: {data_file_path}")
                return None
            
            with open(data_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            print(f"加载寻访数据时出错: {e}")
            return None
            
    def load_gacha_metadata(self, user_uid, game_uid):
        """加载元数据文件 (metadata.json)"""
        try:
            if not user_uid:
                user_uid = "default_user"
            
            metadata_file_path = f"./users/{user_uid}/accounts/{game_uid}/metadata.json"
            
            if not os.path.exists(metadata_file_path):
                print(f"元数据文件不存在: {metadata_file_path}")
                return None
            
            with open(metadata_file_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            return metadata
        except Exception as e:
            print(f"加载元数据时出错: {e}")
            return None
