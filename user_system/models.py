import json
import os
from pathlib import Path
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """用户模型"""
    
    def __init__(self, username, password, is_admin=False, force_password_change=False, is_hashed=False):
        self.username = username
        if not is_hashed:
            self.set_password(password)
        else:
            self.password_hash = password
        self.is_admin = is_admin
        self.force_password_change = force_password_change
        self.user_file = Path(f"users/{username}/user.json")

    def set_password(self, password):
        """设置密码，并生成哈希值"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """检查密码是否正确"""
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        """返回用户的唯一标识符"""
        return self.username
    
    def save(self):
        """保存用户信息"""
        # 确保用户目录存在
        user_dir = Path(f"users/{self.username}")
        user_dir.mkdir(exist_ok=True)
        
        user_data = {
            "username": self.username,
            "password": self.password_hash,
            "is_admin": self.is_admin,
            "force_password_change": self.force_password_change
        }
        
        with open(self.user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def get_user(username):
        """获取用户实例"""
        user_file = Path(f"users/{username}/user.json")
        if not user_file.exists():
            return None
        
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        
        return User(
            username=user_data['username'],
            password=user_data['password'],
            is_admin=user_data.get('is_admin', False),
            force_password_change=user_data.get('force_password_change', False),
            is_hashed=True  # 从文件加载时，密码已是哈希值
        )
    
    @staticmethod
    def user_exists(username):
        """检查用户是否存在"""
        return Path(f"users/{username}/user.json").exists()
    
    @staticmethod
    def get_all_users():
        """获取所有用户列表"""
        users_dir = Path("users")
        if not users_dir.exists():
            return []
        
        users = []
        for user_dir in users_dir.iterdir():
            if user_dir.is_dir():
                user_file = user_dir / "user.json"
                if user_file.exists():
                    users.append(User.get_user(user_dir.name))
        
        return users
    
    def delete(self):
        """删除用户（不包括admin用户）"""
        if self.username == "admin":
            return False
        
        user_dir = Path(f"users/{self.username}")
        if user_dir.exists():
            import shutil
            shutil.rmtree(user_dir)
        return True
