import json
import os
from typing import Dict, Any


def map_pool_type(pool_name: str) -> int:
    """
    根据卡池名称映射 pt 值。
    0: 限定寻访
    1: 标准寻访
    2: 中坚寻访
    """
    if "标准寻访" in pool_name or "常驻标准寻访" in pool_name:
        return 1
    elif "中坚寻访" in pool_name or "中坚甄选" in pool_name:
        return 2
    else:
        # 默认为限定寻访
        return 0


def convert_source_data(source_data: Dict[str, Any]) -> Dict[str, Any]:
    """将源数据转换为目标格式"""
    converted = {}
    for timestamp_str, record in source_data.get("data", {}).items():
        # 转换干员列表，星级+1
        converted_chars = []
        for char in record.get("c", []):
            # 确保角色数据格式正确 [name, rarity, isNew]
            if len(char) >= 3:
                name, rarity, is_new = char[0], char[1], char[2]
                # 稀有度转换: 2->3, 3->4, 4->5, 5->6
                converted_rarity = rarity + 1
                converted_chars.append([name, converted_rarity, is_new])
            else:
                # 如果数据格式不完整，跳过该项
                print(f"警告: 角色数据不完整，跳过: {char}")

        # 创建新记录
        converted[timestamp_str] = {
            "p": record.get("p", ""),
            "pt": map_pool_type(record.get("p", "")),
            "c": converted_chars
        }
    return converted


def merge_data(existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """合并现有数据和新数据，避免重复"""
    # 使用 existing_data 作为基础
    merged = existing_data.copy()

    # 遍历新数据
    for timestamp, record in new_data.items():
        # 如果时间戳不存在于现有数据中，则添加
        if timestamp not in merged:
            merged[timestamp] = record
        else:
            # 可选：如果时间戳已存在，可以选择覆盖或者保留原有数据
            # 这里我们选择保留原有数据，不做覆盖
            pass
            
    return merged




def import_gacha_data(source_json_path: str, target_json_path: str, output_json_path: str) -> bool:
    """
    导入并合并抽卡数据
    
    Args:
        source_json_path: 源JSON文件路径 (例如: 684774691.json)
        target_json_path: 目标JSON文件路径 (例如: users/Arno/accounts/684774691/data.json)
        output_json_path: 输出JSON文件路径 (例如: 684774691_converted.json)
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 1. 读取源文件 (684774691.json)
        if not os.path.exists(source_json_path):
            print(f"错误: 源文件 {source_json_path} 不存在")
            return False
            
        with open(source_json_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        # 2. 读取目标文件 (users/Arno/accounts/684774691/data.json)
        if not os.path.exists(target_json_path):
            print(f"错误: 目标文件 {target_json_path} 不存在")
            return False
            
        with open(target_json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # 3. 转换源数据
        converted_data = convert_source_data(source_data)
        
        # 4. 合并数据
        merged_data = merge_data(existing_data, converted_data)
        
        # 5. 写入新文件 (使用标准的json.dump)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print(f"数据导入和合并完成，结果已保存到 {output_json_path}")
        return True
        
    except Exception as e:
        print(f"导入过程中发生错误: {e}")
        return False
