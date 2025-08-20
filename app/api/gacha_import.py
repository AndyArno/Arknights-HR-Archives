import json
import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from pathlib import Path
from solvers.gacha_data_importer import import_gacha_data
import tempfile

# 创建蓝图
gacha_import_bp = Blueprint('gacha_import_bp', __name__)

@gacha_import_bp.route('/api/import/gacha_data/<string:account_uid>', methods=['POST'])
@login_required
def import_gacha_data_api(account_uid):
    """导入抽卡数据API接口"""
    temp_file_path = None
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有上传文件'}), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({'success': False, 'message': '未选择文件'}), 400
        
        # 检查文件类型（可选）
        if not file.filename.endswith('.json'):
            return jsonify({'success': False, 'message': '只支持JSON文件'}), 400
        
        # 获取用户账号路径
        username = current_user.username
        account_path = Path(f"users/{username}/accounts/{account_uid}")
        
        # 检查账号是否存在
        if not account_path.exists():
            return jsonify({'success': False, 'message': '账号不存在'}), 404
        
        # 创建临时文件来保存上传的文件
        temp_file_path = tempfile.mktemp(suffix='.json')
        file.save(temp_file_path)
        
        # 目标文件路径
        target_file_path = account_path / "data.json"
        
        # 输出文件路径（覆盖原文件）
        output_file_path = str(target_file_path)
        
        # 调用导入函数
        success = import_gacha_data(
            temp_file_path,  # 源文件路径（临时文件）
            str(target_file_path),  # 目标文件路径
            output_file_path  # 输出文件路径
        )
        
        if success:
            return jsonify({'success': True, 'message': '数据导入成功'}), 200
        else:
            return jsonify({'success': False, 'message': '数据导入失败'}), 500
                
    except Exception as e:
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'}), 500
    finally:
        # 确保临时文件被删除
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass  # 忽略删除失败的情况
