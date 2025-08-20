import threading
import webbrowser
import logging
import json
from waitress import serve
from PIL import Image, ImageDraw, ImageFont
import pystray
import os
import sys
import psutil
from apscheduler.schedulers.background import BackgroundScheduler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def is_process_running(script_name):
    """检测指定脚本是否已在运行"""
    current_pid = os.getpid()
    for proc in psutil.process_iter():
        try:
            # 检查进程名或命令行参数
            if script_name in proc.name() or script_name in " ".join(proc.cmdline()):
                if proc.pid != current_pid:  # 排除当前进程
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

from app import create_app
from update_gacha_data import run_full_process

# 配置日志 - 禁用文件日志，仅输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# 防御性代码：确保移除所有文件日志处理器
for handler in logging.getLogger().handlers[:]:
    if isinstance(handler, logging.FileHandler):
        logging.getLogger().removeHandler(handler)
logger = logging.getLogger(__name__)

# 全局变量
web_thread = None
flask_app = None
scheduler = None
WEB_HOST = '0.0.0.0'
WEB_PORT = 16300
WEB_URL = f'http://127.0.0.1:{WEB_PORT}'

def run_web_server():
    """在后台线程中运行Web服务器"""
    global flask_app
    try:
        flask_app = create_app()
        logger.info(f"启动Web服务器: {WEB_URL}")
        serve(flask_app, host=WEB_HOST, port=WEB_PORT)
    except Exception as e:
        logger.error(f"Web服务器启动失败: {e}")

def create_tray_icon():
    """创建系统托盘图标"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 加载Flask应用目录中的自定义图标(PNG格式)
        icon_path = os.path.join(base_dir, 'app', 'static', 'tray_icon.png')
        logger.info(f"尝试加载图标文件: {icon_path}")
        
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
            logger.info(f"图标文件加载成功: {icon_path}")
            
            # 添加中文编码支持
            try:
                image.load()
            except IOError:
                pass
        else:
            raise FileNotFoundError(f"图标文件不存在: {icon_path}")
            
    except Exception as e:
        logger.error(f"自定义图标加载失败: {e}")
        # 创建备用图标
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='white')
    
    # 创建菜单
    menu = pystray.Menu(
        pystray.MenuItem('打开Web界面', open_web_interface),
        pystray.MenuItem('更新数据', update_data),
        pystray.MenuItem('重启应用', restart_app),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('退出', quit_app)
    )
    
    return pystray.Icon(
        "arknights_hr",
        image,
        "明日方舟人事部档案",
        menu
    )

def open_web_interface(icon=None, item=None):
    """打开Web界面"""
    try:
        webbrowser.open(WEB_URL)
        logger.info("已打开Web界面")
    except Exception as e:
        logger.error(f"无法打开Web界面: {e}")

def update_data(icon=None, item=None):
    """更新数据"""
    logger.info("开始更新数据...")
    # 这里使用默认的测试账户配置
    # 实际使用时，应该从配置文件读取
    account_config_path = "users/test/accounts/test_account/config.json"
    user_uid = "test"
    
    if os.path.exists(account_config_path):
        success = run_full_process(account_config_path, user_uid)
        if success:
            logger.info("数据更新成功")
        else:
            logger.error("数据更新失败")
    else:
        logger.error(f"配置文件不存在: {account_config_path}")

def restart_app(icon=None, item=None):
    """重启应用程序"""
    logger.info("正在重启应用程序...")
    if icon:
        icon.stop()
    
    # 启动一个新进程
    python_executable = sys.executable
    script_path = os.path.abspath(__file__)
    os.execv(python_executable, [python_executable, script_path])

def quit_app(icon=None, item=None):
    """退出应用程序"""
    logger.info("正在退出应用程序...")
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("后台调度器已关闭。")
    if icon:
        icon.stop()
    sys.exit(0)

def main():
    """主函数"""
    global web_thread
    
    # 进程检测 - 仅检查app.py是否已在运行
    if is_process_running("app.py"):
        print("错误：明日方舟人事部档案已在运行中")
        print("请勿重复启动程序")
        sys.exit(1)
    
    logger.info("启动明日方舟人事部档案系统...")
    
    # 读取系统配置
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'system.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        default_schedule = config.get('default_schedule', '0 30 4 * * *')  # 默认值
        logger.info(f"读取到默认调度时间: {default_schedule}")
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        default_schedule = '0 30 4 * * *'  # 使用默认值
        logger.info(f"使用默认调度时间: {default_schedule}")
    
    # 启动Web服务器线程
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # 等待Web服务器启动
    import time
    time.sleep(2)
    
    # 初始化并启动后台调度器
    from scheduled_tasks import update_all_accounts
    global scheduler
    scheduler = BackgroundScheduler()
    # 解析 cron 表达式并配置定时任务
    try:
        parts = default_schedule.split()
        if len(parts) == 6:
            second, minute, hour, day, month, day_of_week = parts
            scheduler.add_job(
                update_all_accounts, 
                'cron', 
                second=second, 
                minute=minute, 
                hour=hour, 
                day=day, 
                month=month, 
                day_of_week=day_of_week
            )
        else:
            raise ValueError("Cron表达式格式不正确")
    except Exception as e:
        logger.error(f"解析调度时间失败: {e}")
        logger.info("使用默认时间: 每天凌晨4点30分")
        scheduler.add_job(update_all_accounts, 'cron', hour=4, minute=30)
        
    scheduler.start()
    logger.info("后台调度器已启动，每日数据更新任务已安排。")
    
    # 创建并运行系统托盘图标
    tray_icon = create_tray_icon()
    logger.info("系统托盘图标已创建，右键点击查看菜单")
    
    try:
        tray_icon.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        quit_app(tray_icon)
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        quit_app(tray_icon)

if __name__ == "__main__":
    main()
