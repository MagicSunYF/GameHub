from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import json

def create_app(config):
    app = Flask(__name__, static_folder='..')
    
    # 配置 CORS - 限制允许的源
    # if config.ALLOWED_ORIGINS:
    #     CORS(app, resources={r"/*": {"origins": config.ALLOWED_ORIGINS}})
    # else:
    #     # 开发环境警告
    #     if config.DEBUG:
    #         print("警告: CORS 允许所有来源（仅用于开发）")
    #         CORS(app)
    #     else:
    #         print("错误: 生产环境必须设置 ALLOWED_ORIGINS")
    #         import sysquit
    #         sys.exit(1)
    
    # 配置 SocketIO CORS
    cors_origins = config.ALLOWED_ORIGINS if config.ALLOWED_ORIGINS else "*"
    socketio = SocketIO(app, cors_allowed_origins=cors_origins)
    
    @app.route('/')
    def index():
        return send_from_directory('..', 'index.html')
    
    @app.route('/<game>/<path:path>')
    def game_files(game, path):
        return send_from_directory(f'../{game}', path)
    
    @app.route('/<path:path>')
    def static_files(path):
        return send_from_directory('..', path)
    
    return app, socketio
