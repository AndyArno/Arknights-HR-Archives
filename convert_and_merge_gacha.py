import json

def map_pool_type(pool_name):
    """根据卡池名称映射 pt 值"""
    if "标准寻访" in pool_name or "常驻标准寻访" in pool_name:
        return 1
    elif "中坚寻访" in pool_name or "中坚甄选" in pool_name:
        return 2
    else:
        # 默认为限定寻访
        return 0

def convert_source_data(source_data):
    """将源数据转换为目标格式"""
    converted = {}
    for timestamp, record in source_data["data"].items():
        # 转换干员列表，星级+1
        converted_chars = []
        for char in record["c"]:
            name, rarity, is_new = char
            converted_chars.append([name, rarity + 1, is_new])
        
        # 创建新记录
        converted[timestamp] = {
            "p": record["p"],
            "pt": map_pool_type(record["p"]),
            "c": converted_chars
        }
    return converted

def merge_data(existing_data, new_data):
    """合并现有数据和新数据，避免重复"""
    merged = existing_data.copy()
    
    for timestamp, record in new_data.items():
        # 如果时间戳不存在于现有数据中，则添加
        if timestamp not in merged:
            merged[timestamp] = record
        # 如果存在，可以选择跳过或覆盖，这里我们选择跳过
        # 如果需要覆盖，可以去掉下面的else if注释并调整逻辑
        # else:
        #     print(f"Timestamp {timestamp} already exists. Skipping.")
            
    return merged

def main():
    # 读取源文件 (684774691.json)
    with open('684774691.json', 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    
    # 读取目标文件 (users/Arno/accounts/684774691/data.json)
    with open('users/Arno/accounts/684774691/data.json', 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
    
    # 转换源数据
    converted_data = convert_source_data(source_data)
    
    # 合并数据
    merged_data = merge_data(existing_data, converted_data)
    
    # 写入新文件
    with open('684774691_converted.json', 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    print("数据转换和合并完成，结果已保存到 684774691_converted.json")

if __name__ == "__main__":
    main()
