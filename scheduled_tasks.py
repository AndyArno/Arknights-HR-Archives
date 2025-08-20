import logging
from user_system.user_management import get_all_user_accounts
from update_gacha_data import run_full_process

logger = logging.getLogger(__name__)

def update_all_accounts():
    """
    定时任务：更新所有用户的账户数据。
    """
    logger.info("=== 开始执行每日数据更新任务 ===")
    
    # 获取所有账户配置
    accounts = get_all_user_accounts()
    
    if not accounts:
        logger.info("没有找到任何账户配置，跳过本次更新。")
        return
    
    success_count = 0
    failure_count = 0
    
    # 遍历每个账户并执行更新
    for config_path, user_uid in accounts:
        logger.info(f"开始更新用户 '{user_uid}' 的账户数据 (配置文件: {config_path})")
        try:
            success = run_full_process(config_path, user_uid)
            if success:
                logger.info(f"用户 '{user_uid}' 的账户数据更新成功。")
                success_count += 1
            else:
                logger.error(f"用户 '{user_uid}' 的账户数据更新失败。")
                failure_count += 1
        except Exception as e:
            logger.error(f"更新用户 '{user_uid}' 的账户数据时发生未预期错误: {e}", exc_info=True)
            failure_count += 1
    
    logger.info(f"=== 每日数据更新任务完成 ===")
    logger.info(f"成功: {success_count}, 失败: {failure_count}")
