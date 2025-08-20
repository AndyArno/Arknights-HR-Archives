from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from user_system.models import User
from user_system.directory_service import DirectoryService
import json
import os

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 初始化LoginManager
login_manager = LoginManager()

@login_manager.user_loader
def load_user(username):
    """Flask-Login用户加载回调"""
    return User.get_user(username)

def init_login_manager(app):
    """初始化登录管理器"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/register.html')
        
        if User.user_exists(username):
            flash('用户名已存在', 'error')
            return render_template('auth/register.html')
        
        # 检查是否是第一个用户（自动成为管理员）
        users = User.get_all_users()
        is_admin = len(users) == 0
        
        # 创建用户
        user = User(username, password, is_admin=is_admin, force_password_change=False)
        user.save()
        
        # 创建用户目录结构
        DirectoryService.create_user_directory(username)
        
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 验证输入
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('auth/login.html')
        
        user = User.get_user(username)
        if not user or not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html')
        
        # 登录用户
        login_user(user)
        
        # 检查是否需要强制修改密码
        if user.force_password_change:
            flash('首次登录请修改密码', 'info')
            return redirect(url_for('auth.change_password'))
        
        # 重定向到首页
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证旧密码
        if not current_user.check_password(old_password):
            flash('原密码错误', 'error')
            return render_template('auth/change_password.html')
        
        # 验证新密码
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 6:
            flash('密码长度至少6位', 'error')
            return render_template('auth/change_password.html')
        
        # 更新密码
        current_user.set_password(new_password)
        current_user.force_password_change = False
        current_user.save()
        
        flash('密码修改成功', 'success')
        return redirect(url_for('index'))
    
    return render_template('auth/change_password.html')

@auth_bp.route('/check_auth')
def check_auth():
    """检查认证状态（API）"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'is_admin': current_user.is_admin,
            'force_password_change': current_user.force_password_change
        })
    else:
        return jsonify({
            'authenticated': False
        })
