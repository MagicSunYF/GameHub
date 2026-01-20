from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import json

def create_app():
    app = Flask(__name__, static_folder='..')
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*")
    
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
