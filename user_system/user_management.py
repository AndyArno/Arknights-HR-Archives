import os
import logging

logger = logging.getLogger(__name__)

def get_all_user_accounts(users_base_path="users"):
    """
    扫描 users 目录，获取所有用户的账户配置文件路径。
    
    Args:
        users_base_path (str): users 目录的根路径。默认为 "users"。
        
    Returns:
        list: 包含 (config_path, user_uid) 元组的列表。
              config_path: 账户配置文件的完整路径。
              user_uid: 系统用户ID。
    """
    accounts = []
    
    # 检查 users 目录是否存在
    if not os.path.exists(users_base_path):
        logger.warning(f"Users base directory '{users_base_path}' does not exist.")
        return accounts
    
    # 遍历 users 目录下的每个用户文件夹
    for user_uid in os.listdir(users_base_path):
        user_dir = os.path.join(users_base_path, user_uid)
        
        # 确保这是一个目录
        if os.path.isdir(user_dir):
            accounts_dir = os.path.join(user_dir, "accounts")
            
            # 检查 accounts 目录是否存在
            if os.path.exists(accounts_dir) and os.path.isdir(accounts_dir):
                # 遍历 accounts 目录下的每个账户文件夹
                for account_name in os.listdir(accounts_dir):
                    account_dir = os.path.join(accounts_dir, account_name)
                    
                    # 确保这是一个目录
                    if os.path.isdir(account_dir):
                        config_path = os.path.join(account_dir, "config.json")
                        
                        # 检查 config.json 文件是否存在
                        if os.path.exists(config_path):
                            accounts.append((config_path, user_uid))
                            logger.debug(f"Found account config: {config_path} for user: {user_uid}")
                        else:
                            logger.warning(f"Config file not found in account directory: {account_dir}")
            else:
                logger.info(f"No 'accounts' directory found for user: {user_uid}")
    
    logger.info(f"Found {len(accounts)} account(s) to update.")
    return accounts
