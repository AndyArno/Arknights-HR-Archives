import argparse
from solvers.authenticator import Authenticator
from solvers.gacha_data_fetcher import GachaDataFetcher
from solvers.gacha_data_storer import GachaDataStorer

def run_full_process(account_config_path, user_uid):
    """
    执行完整的自动化流程：认证 -> 获取数据 -> 保存数据。
    """
    print("--- 开始执行自动化流程 ---")

    # 第一步：调用认证专家
    print("步骤 1/3: 进行身份验证...")
    authenticator = Authenticator()
    auth_result = authenticator.authenticate(account_config_path, user_uid)
    if not auth_result:
        print("流程终止：认证失败。")
        return False
    
    authenticated_session = auth_result['session']
    game_uid = auth_result['game_uid']
    print(f"认证成功，游戏UID: {game_uid}")

    # 第二步：调用数据获取专家
    print("步骤 2/3: 获取寻访记录...")
    fetcher = GachaDataFetcher(authenticated_session, game_uid)
    all_records = fetcher.fetch_all_gacha_records()
    if all_records is None:
        print("流程终止：数据获取失败。")
        return False
    
    print(f"成功获取 {len(all_records)} 条记录。")

    # 第三步：调用数据存储专家
    print("步骤 3/3: 保存寻访记录...")
    storer = GachaDataStorer()
    save_success = storer.save_gacha_records(all_records, user_uid, game_uid)
    if not save_success:
        print("流程终止：数据保存失败。")
        return False
    
    print("--- 流程成功完成！ ---")
    return True

def main():
    """
    主函数，用于解析命令行参数并启动流程。
    """
    parser = argparse.ArgumentParser(description="明日方舟人事部档案 - 自动化数据拉取工具")
    parser.add_argument(
        "account_config_path",
        type=str,
        help="账户配置文件的路径 (例如: ./users/test_user/accounts/test_account/account_config.json)"
    )
    parser.add_argument(
        "user_uid",
        type=str,
        help="系统用户ID，用于创建目录结构 (例如: test_user)"
    )
    
    args = parser.parse_args()

    # 执行完整流程
    success = run_full_process(args.account_config_path, args.user_uid)
    
    if success:
        print("所有任务已成功完成。")
    else:
        print("任务执行过程中遇到错误，请检查日志。")

if __name__ == "__main__":
    main()
