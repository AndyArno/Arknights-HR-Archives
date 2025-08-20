from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from user_system.models import User
from user_system.middleware import admin_required
import json

# 创建管理员蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def dashboard():
    """管理员控制台"""
    users = User.get_all_users()
    return render_template('admin/dashboard.html', users=users)

@admin_bp.route('/users')
@admin_required
def list_users():
    """用户列表"""
    users = User.get_all_users()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/reset_password/<username>', methods=['POST'])
@admin_required
def reset_password(username):
    """重置用户密码"""
    if username == 'admin':
        flash('无法重置超级管理员密码', 'error')
        return redirect(url_for('admin.list_users'))
    
    user = User.get_user(username)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.list_users'))
    
    # 根据用户类型设置默认密码
    if user.is_admin:
        user.set_password('admin')
    else:
        user.set_password('123456')
    
    user.force_password_change = True
    user.save()
    
    flash(f'已重置用户 {username} 的密码', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/toggle_admin/<username>', methods=['POST'])
@admin_required
def toggle_admin(username):
    """切换用户管理员权限"""
    if username == 'admin':
        flash('无法修改超级管理员权限', 'error')
        return redirect(url_for('admin.list_users'))
    
    user = User.get_user(username)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.list_users'))
    
    # 切换管理员权限
    user.is_admin = not user.is_admin
    user.save()
    
    status = '授予' if user.is_admin else '取消'
    flash(f'已{status}用户 {username} 的管理员权限', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/delete_user/<username>', methods=['POST'])
@admin_required
def delete_user(username):
    """删除用户"""
    if username == 'admin':
        flash('无法删除超级管理员', 'error')
        return redirect(url_for('admin.list_users'))
    
    user = User.get_user(username)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.list_users'))
    
    # 删除用户
    if user.delete():
        flash(f'已删除用户 {username}', 'success')
    else:
        flash('删除用户失败', 'error')
    
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/create_admin', methods=['POST'])
@admin_required
def create_admin():
    """创建初始管理员账户"""
    # 检查是否已存在admin用户
    if User.user_exists('admin'):
        flash('管理员账户已存在', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # 创建admin用户
    admin_user = User('admin', 'admin', is_admin=True, force_password_change=True)
    admin_user.save()
    
    # 创建用户目录
    from user_system.directory_service import DirectoryService
    DirectoryService.create_user_directory('admin')
    
    flash('已创建管理员账户，用户名：admin，密码：admin', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/users')
@admin_required
def api_users():
    """获取用户列表API"""
    users = User.get_all_users()
    user_list = []
    for user in users:
        user_list.append({
            'username': user.username,
            'is_admin': user.is_admin,
            'force_password_change': user.force_password_change
        })
    
    return jsonify({
        'users': user_list,
        'total': len(user_list)
    })

@admin_bp.route('/api/user/<username>')
@admin_required
def api_user_detail(username):
    """获取用户详情API"""
    user = User.get_user(username)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    from user_system.directory_service import DirectoryService
    accounts = DirectoryService.get_user_accounts(username)
    
    return jsonify({
        'username': user.username,
        'is_admin': user.is_admin,
        'force_password_change': user.force_password_change,
        'accounts': accounts
    })
