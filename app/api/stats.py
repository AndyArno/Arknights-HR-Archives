import json
from pathlib import Path
from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from collections import Counter
from datetime import datetime

stats_bp = Blueprint('stats_bp', __name__)

# --- 核心计算函数 ---

def calculate_prob(current_pity):
    """根据当前水位计算下一次出六星的概率"""
    pull_number = current_pity + 1
    if pull_number <= 50:
        return 0.02
    else:
        prob = 0.02 + (pull_number - 50) * 0.02
        return min(prob, 1.0)

def get_average_pity(pulls):
    """计算六星的平均出货抽数"""
    pity_counter = 0
    pity_list = []
    for pull in pulls:
        pity_counter += 1
        if pull['rarity'] == 6:
            pity_list.append(pity_counter)
            pity_counter = 0
    if not pity_list:
        return 0
    return sum(pity_list) / len(pity_list)

def get_current_pity(pulls):
    """计算当前水位"""
    pity = 0
    for pull in reversed(pulls):
        if pull['rarity'] == 6:
            break
        pity += 1
    return pity

def analyze_pool_data(pulls):
    """对单个卡池类型的抽卡记录进行全面分析"""
    if not pulls:
        return {
            "total_pulls": 0,
            "average_pity": 0,
            "current_pity": 0,
            "current_prob": 0.02
        }
    
    # 按时间戳正序排序
    pulls.sort(key=lambda x: x['ts'])
    
    current_pity = get_current_pity(pulls)
    
    # 特殊规则：对于限定池，需要找到最近抽的那个池子来计算水位
    # (此简化版本暂时不对限定池做特殊处理，后续可迭代)

    return {
        "total_pulls": len(pulls),
        "average_pity": get_average_pity(pulls),
        "current_pity": current_pity,
        "current_prob": calculate_prob(current_pity)
    }


# --- 核心计算函数 ---

def _calculate_dashboard_summary(all_pulls):
    """计算仪表盘统计数据的核心逻辑"""
    if not all_pulls:
        return {
            "limited": {"total_pulls": 0, "average_pity": 0, "current_pity": 0, "current_prob": 0.02},
            "standard": {"total_pulls": 0, "average_pity": 0, "current_pity": 0, "current_prob": 0.02},
            "joint_op": {"total_pulls": 0, "average_pity": 0, "current_pity": 0, "current_prob": 0.02},
            "global_stats": {
                "total_pulls": 0,
                "rarity_counts": {"six_star": 0, "five_star": 0, "four_star": 0, "three_star": 0},
                "rarity_prob": {"six_star": 0, "five_star": 0, "four_star": 0, "three_star": 0},
            }
        }

    # 2. 分类数据
    limited_pulls = [p for p in all_pulls if p['pool_type'] == 0]
    standard_pulls = [p for p in all_pulls if p['pool_type'] == 1]
    joint_op_pulls = [p for p in all_pulls if p['pool_type'] == 2]

    # 3. 分类计算
    limited_stats = analyze_pool_data(limited_pulls)
    standard_stats = analyze_pool_data(standard_pulls)
    joint_op_stats = analyze_pool_data(joint_op_pulls)

    # 4. 全局统计
    total_pulls_all = len(all_pulls)
    rarity_counts = {6: 0, 5: 0, 4: 0, 3: 0}
    for pull in all_pulls:
        if pull['rarity'] in rarity_counts:
            rarity_counts[pull['rarity']] += 1

    global_stats = {
        "total_pulls": total_pulls_all,
        "rarity_counts": {
            "six_star": rarity_counts.get(6, 0),
            "five_star": rarity_counts.get(5, 0),
            "four_star": rarity_counts.get(4, 0),
            "three_star": rarity_counts.get(3, 0)
        },
        "rarity_prob": {
            "six_star": rarity_counts.get(6, 0) / total_pulls_all if total_pulls_all > 0 else 0,
            "five_star": rarity_counts.get(5, 0) / total_pulls_all if total_pulls_all > 0 else 0,
            "four_star": rarity_counts.get(4, 0) / total_pulls_all if total_pulls_all > 0 else 0,
            "three_star": rarity_counts.get(3, 0) / total_pulls_all if total_pulls_all > 0 else 0,
        }
    }

    # 5. 组织并返回最终结果
    response_data = {
        "limited": limited_stats,
        "standard": standard_stats,
        "joint_op": joint_op_stats,
        "global_stats": global_stats
    }
    
    return response_data

# --- API Endpoint ---

def _get_all_pulls(username, game_uid):
    """辅助函数：读取、解析并返回一个用户账号的所有抽卡记录"""
    # 注意：这里不再使用 current_app，而是直接使用传入的 username
    users_dir = Path("users")  # 假设工作目录是项目根目录
    data_file = users_dir / username / 'accounts' / game_uid / 'data.json'

    if not data_file.exists():
        # 返回错误信息和状态码，让调用者处理
        return None, ({"error": "Data file not found"}, 404)

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            gacha_data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        return None, ({"error": f"Failed to read or parse data file: {str(e)}"}, 500)

    all_pulls = []
    for ts, record in gacha_data.items():
        for char_name, rarity, is_new in record['c']:
            all_pulls.append({
                "ts": int(ts),
                "pool_name": record['p'],
                "pool_type": record['pt'],
                "char_name": char_name,
                "rarity": rarity,
                "is_new": is_new
            })
    
    all_pulls.sort(key=lambda x: x['ts'])
    return all_pulls, None


@stats_bp.route('/api/stats/<string:game_uid>/dashboard_summary')
@login_required
def get_dashboard_summary(game_uid):
    """提供全局数据仪表盘所需的统计数据 (API路由)"""
    all_pulls, error = _get_all_pulls(current_user.username, game_uid)
    if error:
        return jsonify(error[0]), error[1]
        
    response_data = _calculate_dashboard_summary(all_pulls)
    return jsonify(response_data)


# --- 新增图表和详情 API ---

def _calculate_pulls_by_pool(all_pulls):
    """按卡池名称分组，统计总抽数 (核心逻辑)"""
    if not all_pulls:
        return []
    pool_counts = Counter(p['pool_name'] for p in all_pulls)
    
    # 创建一个按时间顺序排列的唯一卡池名称列表
    ordered_unique_pools = []
    seen_pools = set()
    for pull in all_pulls:
        pool_name = pull['pool_name']
        if pool_name not in seen_pools:
            ordered_unique_pools.append(pool_name)
            seen_pools.add(pool_name)
    
    # 根据有序列表构建结果，确保按首次出现时间排序
    result = [{"name": name, "value": pool_counts[name]} for name in ordered_unique_pools]
    return result

def _calculate_pulls_by_month(all_pulls):
    """按“年-月”分组，统计总抽数 (核心逻辑)"""
    if not all_pulls:
        return []
    month_counts = Counter(datetime.fromtimestamp(p['ts']).strftime('%Y-%m') for p in all_pulls)
    # 转换为 ECharts 需要的格式并按月份排序
    result = [{"name": name, "value": value} for name, value in sorted(month_counts.items())]
    return result

def _calculate_pool_list_and_latest(all_pulls):
    """获取用户寻访过的所有卡池的唯一名称列表，并附带最新的卡池名 (核心逻辑)"""
    if not all_pulls:
        return {"pool_list": [], "latest_pool": None}
    # all_pulls 已经按时间戳升序排序
    latest_pool_name = all_pulls[-1]['pool_name']
    # 获取所有唯一的卡池名并排序
    pool_names = sorted(list(set(p['pool_name'] for p in all_pulls)))
    return {
        "pool_list": pool_names,
        "latest_pool": latest_pool_name
    }

def _calculate_pool_details(all_pulls, pool_name):
    """提供指定卡池的详细寻访分析 (核心逻辑)"""
    if not all_pulls:
        return {
            "pool_name": pool_name,
            "total_pulls": 0,
            "six_star_list": []
        }
    pool_pulls = [p for p in all_pulls if p['pool_name'] == pool_name]
    if not pool_pulls:
        return {
            "pool_name": pool_name,
            "total_pulls": 0,
            "six_star_list": []
        }
    six_star_list = []
    pity_counter = 0
    for pull in pool_pulls:
        pity_counter += 1
        if pull['rarity'] == 6:
            six_star_list.append({
                "char_name": pull['char_name'],
                "pity": pity_counter,
                "is_new": pull['is_new'],
                "ts": pull['ts']
            })
            pity_counter = 0
    return {
        "pool_name": pool_name,
        "total_pulls": len(pool_pulls),
        "six_star_list": six_star_list
    }


@stats_bp.route('/api/stats/<string:game_uid>/pulls_by_pool')
@login_required
def get_pulls_by_pool(game_uid):
    """按卡池名称分组，统计总抽数 (API路由)"""
    all_pulls, error = _get_all_pulls(current_user.username, game_uid)
    if error:
        return jsonify(error[0]), error[1]
    result = _calculate_pulls_by_pool(all_pulls)
    return jsonify(result)


@stats_bp.route('/api/stats/<string:game_uid>/pulls_by_month')
@login_required
def get_pulls_by_month(game_uid):
    """按“年-月”分组，统计总抽数 (API路由)"""
    all_pulls, error = _get_all_pulls(current_user.username, game_uid)
    if error:
        return jsonify(error[0]), error[1]
    result = _calculate_pulls_by_month(all_pulls)
    return jsonify(result)


@stats_bp.route('/api/utils/<string:game_uid>/pool_list')
@login_required
def get_pool_list(game_uid):
    """获取用户寻访过的所有卡池的唯一名称列表，并附带最新的卡池名 (API路由)"""
    all_pulls, error = _get_all_pulls(current_user.username, game_uid)
    if error:
        return jsonify(error[0]), error[1]
    result = _calculate_pool_list_and_latest(all_pulls)
    return jsonify(result)


@stats_bp.route('/api/stats/<string:game_uid>/pool_details/<path:pool_name>')
@login_required
def get_pool_details(game_uid, pool_name):
    """提供指定卡池的详细寻访分析 (API路由)"""
    all_pulls, error = _get_all_pulls(current_user.username, game_uid)
    if error:
        return jsonify(error[0]), error[1]
    result = _calculate_pool_details(all_pulls, pool_name)
    return jsonify(result)
