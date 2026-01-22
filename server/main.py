from app import create_app
from database import Database
from game_manager import GameManager
from barrage_manager import BarrageManager
from config import Config
from plugins.gomoku import GomokuPlugin
from plugins.landlord import LandlordPlugin
from plugins.racing import RacingPlugin
import logging
import sys
from flask_socketio import SocketIO
import threading
import time

logger = logging.getLogger(__name__)

def cleanup_task(game_manager, interval=300):
    """定期清理超时房间的后台任务"""
    while True:
        time.sleep(interval)
        try:
            inactive_rooms = game_manager.cleanup_inactive_rooms()
            if inactive_rooms:
                logger.info(f"清理了 {len(inactive_rooms)} 个超时房间: {inactive_rooms}")
        except Exception as e:
            logger.error(f"清理房间时出错: {e}")

def main():
    """主函数：初始化并启动应用"""
    
    # 验证配置
    if not Config.validate():
        logger.error("配置验证失败，退出")
        sys.exit(1)
    
    # 记录配置
    Config.log_config()
    
    # 创建Flask应用
    app, socketio, heartbeat_handler = create_app(Config)
    
    # 初始化游戏管理器
    game_manager = GameManager()
    logger.info("游戏管理器初始化完成")
    
    # 初始化弹幕管理器
    barrage_manager = BarrageManager(rate_limit=3, time_window=10)
    logger.info("弹幕管理器初始化完成")
    
    # 启动清理任务
    cleanup_thread = threading.Thread(
        target=cleanup_task,
        args=(game_manager, 300),
        daemon=True
    )
    cleanup_thread.start()
    logger.info("房间清理任务已启动（每5分钟执行一次）")
    
    # 初始化数据库（可选）
    db = None
    try:
        db = Database(
            Config.MYSQL_CONFIG,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            health_check_interval=60
        )
        # 执行初始健康检查
        if db.health_check():
            logger.info("数据库连接成功，连接池已就绪")
            stats = db.get_pool_stats()
            logger.info(f"连接池状态: {stats}")
        else:
            logger.warning("数据库健康检查失败，将以降级模式运行")
            db = None
    except Exception as e:
        logger.warning(f'数据库连接失败，跳过数据库功能: {e}')
        db = None
    
    # 加载游戏插件
    plugins = []
    try:
        plugins.append(GomokuPlugin(app, socketio, db, game_manager, barrage_manager))
        logger.info("五子棋插件加载成功")
    except Exception as e:
        logger.error(f"五子棋插件加载失败: {e}")
    
    try:
        plugins.append(LandlordPlugin(app, socketio, db, game_manager, barrage_manager))
        logger.info("斗地主插件加载成功")
    except Exception as e:
        logger.error(f"斗地主插件加载失败: {e}")
    
    try:
        plugins.append(RacingPlugin(app, socketio, db, game_manager, barrage_manager))
        logger.info("极速狂飙插件加载成功")
    except Exception as e:
        logger.error(f"极速狂飙插件加载失败: {e}")
    
    if not plugins:
        logger.error("没有成功加载任何游戏插件，退出")
        sys.exit(1)
    
    logger.info(f"成功加载 {len(plugins)} 个游戏插件")
    
    # 启动服务器
    logger.info(f'服务器启动: http://{Config.HOST}:{Config.PORT}')
    try:
        socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
