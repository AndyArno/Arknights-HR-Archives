from flask import request, redirect, url_for, flash, abort
from flask_login import current_user
import functools

def permission_middleware():
    """全局权限检查中间件"""
    
    # 路径白名单（无需登录即可访问）
    public_paths = [
        '/auth/login',
        '/auth/register',
        '/auth/check_auth',
        '/health',
        '/static/'
    ]
    
    # 检查是否在白名单中
    path = request.path
    for public_path in public_paths:
        if path.startswith(public_path):
            return None
    
    # 检查用户是否已登录
    if not current_user.is_authenticated:
        flash('请先登录', 'error')
        return redirect(url_for('auth.login', next=request.path))
    
    # 检查是否需要强制修改密码
    if current_user.force_password_change and not path.startswith('/auth/change_password'):
        flash('请先修改密码', 'info')
        return redirect(url_for('auth.change_password'))
    
    # 管理员权限检查
    if path.startswith('/admin'):
        if not current_user.is_admin:
            flash('无管理员权限', 'error')
            abort(403)
    
    # 用户数据访问权限检查
    if path.startswith('/user'):
        # 提取目标用户名
        parts = path.split('/')
        if len(parts) >= 3 and parts[2] != current_user.username:
            # 管理员可以访问所有用户数据（仅用于管理目的）
            if not current_user.is_admin:
                flash('无权访问其他用户数据', 'error')
                abort(403)
    
    return None

def admin_required(f):
    """管理员权限装饰器"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'error')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_admin:
            flash('需要管理员权限', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def login_required_custom(f):
    """自定义登录要求装饰器（包含强制密码修改检查）"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'error')
            return redirect(url_for('auth.login', next=request.url))
        
        if current_user.force_password_change and not request.endpoint == 'auth.change_password':
            flash('请先修改密码', 'info')
            return redirect(url_for('auth.change_password'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_user_data_access(username):
    """检查用户数据访问权限"""
    if not current_user.is_authenticated:
        return False
    
    # 用户只能访问自己的数据
    if current_user.username == username:
        return True
    
    # 管理员可以访问所有用户数据（仅用于管理目的）
    if current_user.is_admin:
        return True
    
    return False
