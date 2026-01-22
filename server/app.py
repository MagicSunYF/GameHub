from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import sys
import logging
from heartbeat import HeartbeatHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config):
    """
    创建并配置Flask应用
    
    Args:
        config: 配置对象
        
    Returns:
        tuple: (app, socketio, heartbeat_handler) Flask应用、SocketIO实例和心跳处理器
    """
    app = Flask(__name__, static_folder='..')
    
    # 配置CORS
    _configure_cors(app, config)
    
    # 配置SocketIO
    socketio = _configure_socketio(app, config)
    
    # 配置心跳检测
    heartbeat_handler = _configure_heartbeat(socketio, config)
    
    # 注册路由
    _register_routes(app)
    
    # 注册错误处理器
    _register_error_handlers(app)
    
    logger.info("Flask应用初始化完成")
    return app, socketio, heartbeat_handler

def _configure_cors(app, config):
    """配置CORS跨域设置"""
    # if config.ALLOWED_ORIGINS:
    #     # 生产环境：使用配置的允许源
    #     CORS(app, resources={r"/*": {"origins": config.ALLOWED_ORIGINS}})
    #     logger.info(f"CORS配置: 允许源 {config.ALLOWED_ORIGINS}")
    # else:
    #     if config.DEBUG:
    #         # 开发环境：允许所有源
    #         CORS(app)
    #         logger.warning("CORS配置: 允许所有源（仅用于开发）")
    #     else:
    #         # 生产环境必须配置ALLOWED_ORIGINS
    #         logger.error("生产环境必须设置ALLOWED_ORIGINS环境变量")
    #         sys.exit(1)

def _configure_socketio(app, config):
    """配置SocketIO实时通信"""
    cors_origins = config.ALLOWED_ORIGINS if config.ALLOWED_ORIGINS else "*"
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_origins,
        logger=config.DEBUG,
        engineio_logger=config.DEBUG
    )
    logger.info(f"SocketIO配置: CORS源 {cors_origins}")
    return socketio

def _configure_heartbeat(socketio, config):
    """配置心跳检测"""
    heartbeat_timeout = getattr(config, 'HEARTBEAT_TIMEOUT', 60)
    heartbeat_handler = HeartbeatHandler(socketio, timeout=heartbeat_timeout)
    heartbeat_handler.register_events()
    logger.info(f"心跳检测配置: 超时时间 {heartbeat_timeout}秒")
    return heartbeat_handler

def _register_routes(app):
    """注册HTTP路由"""
    
    @app.route('/')
    def index():
        """主页"""
        try:
            return send_from_directory('..', 'index.html')
        except Exception as e:
            logger.error(f"加载主页失败: {e}")
            return jsonify({'error': '加载主页失败'}), 500
    
    @app.route('/<game>/<path:path>')
    def game_files(game, path):
        """游戏文件"""
        try:
            return send_from_directory(f'../{game}', path)
        except Exception as e:
            logger.error(f"加载游戏文件失败 {game}/{path}: {e}")
            return jsonify({'error': '文件不存在'}), 404
    
    @app.route('/<path:path>')
    def static_files(path):
        """静态文件"""
        try:
            return send_from_directory('..', path)
        except Exception as e:
            logger.error(f"加载静态文件失败 {path}: {e}")
            return jsonify({'error': '文件不存在'}), 404
    
    logger.info("HTTP路由注册完成")

def _register_error_handlers(app):
    """注册全局错误处理器"""
    
    @app.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return jsonify({'error': '资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        logger.error(f"服务器内部错误: {error}")
        return jsonify({'error': '服务器内部错误'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """通用异常处理"""
        logger.error(f"未处理的异常: {error}", exc_info=True)
        return jsonify({'error': '服务器错误'}), 500
    
    logger.info("错误处理器注册完成")
