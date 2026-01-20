from app import create_app
from database import Database
from game_manager import GameManager
from config import Config
from plugins.gomoku import GomokuPlugin
from plugins.landlord import LandlordPlugin

def main():
    # 创建应用
    app, socketio = create_app(Config)
    
    # 初始化数据库
    db = Database(Config.MYSQL_CONFIG)
    
    # 初始化游戏管理器
    game_manager = GameManager()
    
    # 加载游戏插件
    GomokuPlugin(app, socketio, db, game_manager)
    LandlordPlugin(app, socketio, db, game_manager)
    
    # 启动服务器
    print(f'服务器启动: http://{Config.HOST}:{Config.PORT}')
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)

if __name__ == '__main__':
    main()
