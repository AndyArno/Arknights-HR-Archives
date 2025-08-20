from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import current_user
import os
import threading
from threading import Lock
from datetime import datetime
import json
from pathlib import Path

# 导入数据更新函数
from update_gacha_data import run_full_process
# 导入用户系统
from user_system.auth import init_login_manager
from user_system.middleware import permission_middleware
# 导入统计函数
from app.api.stats import _get_all_pulls, _calculate_dashboard_summary, _calculate_pool_list_and_latest, _calculate_pulls_by_pool, _calculate_pool_details, _calculate_pulls_by_month

# 创建更新锁，防止重复触发
update_lock = {}

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # 配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # 初始化用户系统
    init_login_manager(app)
    
    # 注册权限中间件
    @app.before_request
    def before_request():
        result = permission_middleware()
        if result is not None:
            return result
    
    @app.route('/')
    def index():
        """主页路由"""
        accounts = []
        gacha_summary = None
        # 初始化变量，避免未定义错误
        pool_data = {"pool_list": [], "latest_pool": None}
        pulls_by_pool_data = []
        pulls_by_month_data = []
        latest_pool_details = None
        gacha_data = {}
        gacha_summary = None
        
        if current_user.is_authenticated:
            from user_system.directory_service import DirectoryService
            from pathlib import Path
            import json
            
            username = current_user.username
            account_uids = DirectoryService.get_user_accounts(username)
            
            for account_uid in account_uids:
                account_path = Path(f"users/{username}/accounts/{account_uid}")
                metadata_file = account_path / "metadata.json"
                
                metadata = {}
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except (IOError, json.JSONDecodeError):
                        metadata = {} # 出错时使用空字典
                
                accounts.append({
                    'uid': account_uid,
                    'created_at': metadata.get('created_at', '未知'),
                    'last_updated': metadata.get('last_updated', '未知'),
                    'version': metadata.get('version', 'N/A')
                })
            
            # 如果存在账号，则获取第一个账号的抽卡统计数据
            if accounts:
                first_account_uid = accounts[0]['uid']
                all_pulls, error = _get_all_pulls(username, first_account_uid)
                if error is None:
                    gacha_summary = _calculate_dashboard_summary(all_pulls)
                    
                    # 获取额外的图表数据
                    pool_data = _calculate_pool_list_and_latest(all_pulls)
                    pulls_by_pool_data = _calculate_pulls_by_pool(all_pulls)
                    latest_pool_name = pool_data.get("latest_pool")
                    latest_pool_details = None
                    if latest_pool_name:
                        latest_pool_details = _calculate_pool_details(all_pulls, latest_pool_name)
                    
                    # 获取用于"按月份"分布的数据
                    pulls_by_month_data = _calculate_pulls_by_month(all_pulls)
                    
                    # 获取原始数据用于历史记录表格
                    users_dir = Path("users")
                    data_file = users_dir / username / 'accounts' / first_account_uid / 'data.json'
                    gacha_data = {}
                    if data_file.exists():
                        try:
                            with open(data_file, 'r', encoding='utf-8') as f:
                                gacha_data = json.load(f)
                        except (IOError, json.JSONDecodeError):
                            pass # 如果读取失败，gacha_data 保持为空字典
                    
                else:
                    # 如果获取数据失败，确保这些变量被定义，避免模板渲染错误
                    pool_data = {"pool_list": [], "latest_pool": None}
                    pulls_by_pool_data = []
                    pulls_by_month_data = []
                    latest_pool_details = None
                    gacha_data = {}

        return render_template('index.html', 
                             accounts=accounts, 
                             gacha_summary=gacha_summary,
                             pool_data=pool_data,
                             pulls_by_pool_data=pulls_by_pool_data,
                             pulls_by_month_data=pulls_by_month_data,
                             latest_pool_details=latest_pool_details,
                             gacha_data=gacha_data)
    
    # 注册用户系统蓝图
    from user_system.auth import auth_bp
    from user_system.admin_views import admin_bp
    from user_system.user_views import user_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    
    # 注册数据统计API蓝图
    from app.api.stats import stats_bp
    app.register_blueprint(stats_bp)
    
    # 注册抽卡数据导入API蓝图
    from app.api.gacha_import import gacha_import_bp
    app.register_blueprint(gacha_import_bp)

    # 注册自定义模板过滤器
    @app.template_filter('timestamp_to_datetime')
    def timestamp_to_datetime(s):
        return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')
    
    @app.route('/health')
    def health():
        """健康检查路由"""
        return {'status': 'ok', 'message': 'Service is running'}
    
    @app.route('/update-test-data')
    def update_test_data():
        """用户数据更新路由（每个用户都有权限使用）"""
        if not current_user.is_authenticated:
            return jsonify({"message": "请先登录"}), 401
        
        # 获取用户参数
        account_uid = request.args.get('account_uid', 'default_account')
        username = current_user.username
        
        # 检查用户是否有该账号
        from user_system.directory_service import DirectoryService
        accounts = DirectoryService.get_user_accounts(username)
        if account_uid not in accounts:
            return jsonify({"message": "账号不存在"}), 404
        
        # 检查是否已有更新任务在进行
        user_lock_key = f"{username}_{account_uid}"
        if user_lock_key in update_lock and update_lock[user_lock_key].locked():
            return jsonify({"message": "已有更新任务在进行中"}), 429
        
        # 创建用户专用的锁
        if user_lock_key not in update_lock:
            update_lock[user_lock_key] = Lock()
        
        def run_update():
            try:
                # 获取账号配置路径
                account_config = f"users/{username}/accounts/{account_uid}/config.json"
                
                # 执行更新
                success = run_full_process(account_config, username)
                # 更新成功状态通过日志查看
            except Exception as e:
                # 异常信息通过日志查看
                pass
            finally:
                if update_lock.get(user_lock_key):
                    update_lock[user_lock_key].release()
        
        # 启动后台更新线程
        if update_lock[user_lock_key].acquire(blocking=False):
            threading.Thread(target=run_update).start()
            return jsonify({"message": f"已开始后台更新用户 {username} 的账号 {account_uid} 数据"})
        
        return jsonify({"message": "更新请求处理失败"}), 500
    
    return app
