import os
import json
from pathlib import Path

class DirectoryService:
    """用户目录管理服务"""
    
    @staticmethod
    def create_user_directory(username):
        """创建用户目录结构"""
        user_path = Path(f"users/{username}/accounts/")
        user_path.mkdir(parents=True, exist_ok=True)
        return str(user_path)
    
    @staticmethod
    def user_exists(username):
        """检查用户是否存在"""
        return os.path.exists(f"users/{username}")
    
    @staticmethod
    def get_user_accounts(username):
        """获取用户的所有游戏账号"""
        accounts_path = Path(f"users/{username}/accounts/")
        if not accounts_path.exists():
            return []
        
        return [item.name for item in accounts_path.iterdir() if item.is_dir()]
    
    @staticmethod
    def create_account_directory(username, game_uid):
        """创建游戏账号目录"""
        account_path = Path(f"users/{username}/accounts/{game_uid}")
        account_path.mkdir(parents=True, exist_ok=True)
        
        # 创建必要的文件
        config_file = account_path / "config.json"
        data_file = account_path / "data.json"
        metadata_file = account_path / "metadata.json"
        
        # 初始化空文件
        if not config_file.exists():
            config_file.write_text('{}')
        if not data_file.exists():
            data_file.write_text('{"gacha_records": []}')
        if not metadata_file.exists():
            metadata_file.write_text(json.dumps({
                "created_at": "2025-01-01T00:00:00Z",
                "last_updated": "2025-01-01T00:00:00Z",
                "version": "1.0"
            }))
        
        return str(account_path)
