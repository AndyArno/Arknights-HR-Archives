from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from user_system.models import User
from user_system.directory_service import DirectoryService
from user_system.middleware import check_user_data_access
import json
import os
from pathlib import Path
from solvers.authenticator import Authenticator
from solvers.credential_manager import CredentialManager
from solvers.gacha_data_fetcher import GachaDataFetcher
from solvers.gacha_data_storer import GachaDataStorer
from app.api.stats import _get_all_pulls, _calculate_dashboard_summary, _calculate_pool_list_and_latest, _calculate_pool_details, _calculate_pulls_by_pool, _calculate_pulls_by_month

# 创建用户蓝图
user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/<username>')
@login_required
def profile(username):
    """用户个人主页"""
    if not check_user_data_access(username):
        flash('无权访问该用户数据', 'error')
        abort(403)
    
    user = User.get_user(username)
    if not user:
        flash('用户不存在', 'error')
        abort(404)
    
    # 获取用户的所有游戏账号
    accounts = DirectoryService.get_user_accounts(username)
    
    return render_template('user/profile.html', user=user, accounts=accounts)


@user_bp.route('/<username>/add_account', methods=['GET', 'POST'])
@login_required
def add_account(username):
    """添加新游戏账号"""
    if not check_user_data_access(username):
        abort(403)

    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')

        if not phone or not password:
            flash('手机号和密码不能为空', 'error')
            return redirect(url_for('user.add_account', username=username))

        try:
            # 1. 手动执行完整的认证流程以获得有效的session和game_uid
            authenticator = Authenticator()
            
            initial_token = authenticator._get_initial_token(phone, password)
            if not initial_token:
                flash('账号或密码错误，认证失败 (Code: 1)', 'error')
                return redirect(url_for('user.add_account', username=username))
            
            authenticator._perform_csrf_request()
            app_token = authenticator._get_app_token(initial_token)
            if not app_token:
                flash('认证失败 (Code: 2)', 'error')
                return redirect(url_for('user.add_account', username=username))
                
            game_uid = authenticator._get_default_game_uid(app_token)
            if not game_uid:
                flash('认证失败 (无法获取游戏UID，请确认账号已绑定游戏)', 'error')
                return redirect(url_for('user.add_account', username=username))

            u8_token = authenticator._get_u8_token(app_token, game_uid)
            if not u8_token:
                flash('认证失败 (Code: 3)', 'error')
                return redirect(url_for('user.add_account', username=username))

            if not authenticator._login_role(u8_token):
                flash('认证失败 (Code: 4)', 'error')
                return redirect(url_for('user.add_account', username=username))
            
            # 认证成功，获取session
            session = authenticator.session

            # 2. 检查账号是否已存在
            account_path = Path(f"users/{username}/accounts/{game_uid}")
            if account_path.exists():
                flash(f'游戏账号 {game_uid} 已存在，无需重复添加', 'warning')
                return redirect(url_for('user.account_detail', username=username, account_uid=game_uid))

            # 3. 创建目录并加密保存凭证
            account_path.mkdir(parents=True, exist_ok=True)
            config_path = account_path / "config.json"
            credential_manager = CredentialManager()
            credentials_to_save = {"username": phone, "password": password}
            if not credential_manager.encrypt_and_save_credentials(credentials_to_save, str(config_path)):
                flash('关键错误：保存加密凭证失败！', 'error')
                return redirect(url_for('user.add_account', username=username))
            
            flash('凭证已成功加密保存，正在获取数据...', 'info')

            # 4. 获取并存储抽卡数据
            fetcher = GachaDataFetcher(session, game_uid)
            all_records = fetcher.fetch_all_gacha_records()
            if all_records is None:
                flash('成功添加账号，但获取抽卡数据失败。您可以稍后手动更新。', 'warning')
                return redirect(url_for('user.account_detail', username=username, account_uid=game_uid))

            storer = GachaDataStorer()
            storer.save_gacha_records(all_records, username, game_uid)

            flash(f'成功添加并同步游戏账号 {game_uid}', 'success')
            return redirect(url_for('user.account_detail', username=username, account_uid=game_uid))

        except Exception as e:
            flash(f'添加账号时发生未知错误: {str(e)}', 'error')
            return redirect(url_for('user.add_account', username=username))

    return render_template('user/add_account.html', username=username)


@user_bp.route('/<username>/account/<account_uid>')
@login_required
def account_detail(username, account_uid):
    """游戏账号详情"""
    if not check_user_data_access(username):
        flash('无权访问该用户数据', 'error')
        abort(403)
    
    account_path = Path(f"users/{username}/accounts/{account_uid}")
    if not account_path.exists():
        flash('账号不存在', 'error')
        abort(404)
    
    # 读取账号数据
    config_file = account_path / "config.json"
    data_file = account_path / "data.json"
    metadata_file = account_path / "metadata.json"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        config = {}
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            # 直接加载JSON文件的内容，它应该是一个以时间戳为键的对象
            data = json.load(f)
    except (IOError, json.JSONDecodeError):
        # 如果文件不存在或为空/格式错误，则data为空字典
        data = {}
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except (IOError, json.JSONDecodeError):
        # If file is missing or invalid, provide a default dict with correct keys
        metadata = {"created_at": "未知", "last_update": "未知", "version": "N/A"}

    # 获取抽卡统计数据
    gacha_summary = None
    pool_data = None
    latest_pool_details = None
    pulls_by_pool_data = None
    pulls_by_month_data = None

    if data:
        all_pulls, error = _get_all_pulls(username, account_uid)
        if error is None:
            gacha_summary = _calculate_dashboard_summary(all_pulls)
            pool_data = _calculate_pool_list_and_latest(all_pulls)
            if pool_data and pool_data.get("latest_pool"):
                latest_pool_details = _calculate_pool_details(all_pulls, pool_data["latest_pool"])
            pulls_by_pool_data = _calculate_pulls_by_pool(all_pulls)
            pulls_by_month_data = _calculate_pulls_by_month(all_pulls)
    
    return render_template('user/account_detail.html',
                         username=username,
                         account_uid=account_uid,
                         config=config,
                         data=data,
                         metadata=metadata,
                         gacha_summary=gacha_summary,
                         pool_data=pool_data,
                         latest_pool_details=latest_pool_details,
                         pulls_by_pool_data=pulls_by_pool_data,
                         pulls_by_month_data=pulls_by_month_data)

@user_bp.route('/<username>/update_data/<account_uid>', methods=['POST'])
@login_required
def update_account_data(username, account_uid):
    """更新账号数据（调用update_gacha_data.py）"""
    if not check_user_data_access(username):
        flash('无权访问该用户数据', 'error')
        abort(403)
    
    account_path = Path(f"users/{username}/accounts/{account_uid}")
    if not account_path.exists():
        flash('账号不存在', 'error')
        abort(404)
    
    # 调用update_gacha_data.py
    try:
        from update_gacha_data import run_full_process
        
        config_file = str(account_path / "config.json")
        # 修复BUG：第二个参数应该是系统用户名 `username`，而不是游戏账号UID `account_uid`
        success = run_full_process(config_file, username)
        
        if success:
            flash('数据更新成功', 'success')
        else:
            flash('数据更新失败', 'error')
    except Exception as e:
        flash(f'数据更新出错：{str(e)}', 'error')
    
    return redirect(url_for('user.account_detail', username=username, account_uid=account_uid))

import shutil  # 添加在文件顶部

# ... 其他代码保持不变 ...

@user_bp.route('/<username>/delete_account/<account_uid>', methods=['POST'])
@login_required
def delete_account(username, account_uid):
    """删除游戏账号"""
    if not check_user_data_access(username):
        flash('无权访问该用户数据', 'error')
        abort(403)
    
    account_path = Path(f"users/{username}/accounts/{account_uid}")
    if not account_path.exists():
        flash('账号不存在', 'error')
        abort(404)
    
    try:
        # 递归删除整个账号目录
        shutil.rmtree(account_path)
        flash(f'游戏账号 {account_uid} 已成功删除', 'success')
    except Exception as e:
        flash(f'删除账号时出错: {str(e)}', 'error')
    
    return redirect(url_for('user.profile', username=username))

@user_bp.route('/<username>/api/accounts')
@login_required
def api_accounts(username):
    """获取用户账号列表API"""
    if not check_user_data_access(username):
        return jsonify({'error': '无权访问'}), 403
    
    accounts = DirectoryService.get_user_accounts(username)
    return jsonify({
        'username': username,
        'accounts': accounts
    })

@user_bp.route('/<username>/api/account/<account_uid>/data')
@login_required
def api_account_data(username, account_uid):
    """获取账号数据API"""
    if not check_user_data_access(username):
        return jsonify({'error': '无权访问'}), 403
    
    account_path = Path(f"users/{username}/accounts/{account_uid}")
    if not account_path.exists():
        return jsonify({'error': '账号不存在'}), 404
    
    # 读取数据文件
    data_file = account_path / "data.json"
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except:
        return jsonify({'error': '读取数据失败'}), 500
