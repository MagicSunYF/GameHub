"""
WebSocket心跳检测服务端模块
处理客户端心跳请求并响应
"""

import logging
import time
from flask_socketio import emit

logger = logging.getLogger(__name__)

class HeartbeatHandler:
    """心跳处理器"""
    
    def __init__(self, socketio, timeout=60):
        """
        初始化心跳处理器
        
        Args:
            socketio: SocketIO实例
            timeout: 心跳超时时间（秒），默认60秒
        """
        self.socketio = socketio
        self.timeout = timeout
        self.client_heartbeats = {}  # {sid: last_heartbeat_time}
        
    def register_events(self):
        """注册心跳相关事件"""
        
        @self.socketio.on('ping')
        def handle_ping(data):
            """处理客户端心跳请求"""
            from flask import request
            sid = request.sid
            
            # 记录心跳时间
            self.client_heartbeats[sid] = time.time()
            
            # 响应心跳
            emit('pong', {
                'timestamp': data.get('timestamp'),
                'server_time': int(time.time() * 1000)
            })
            
            logger.debug(f"收到客户端 {sid} 心跳")
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接时初始化心跳"""
            from flask import request
            sid = request.sid
            self.client_heartbeats[sid] = time.time()
            logger.info(f"客户端 {sid} 已连接，初始化心跳")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开时清理心跳记录"""
            from flask import request
            sid = request.sid
            if sid in self.client_heartbeats:
                del self.client_heartbeats[sid]
            logger.info(f"客户端 {sid} 已断开，清理心跳记录")
    
    def check_timeouts(self):
        """
        检查超时的客户端连接
        
        Returns:
            list: 超时的客户端SID列表
        """
        current_time = time.time()
        timeout_clients = []
        
        for sid, last_heartbeat in list(self.client_heartbeats.items()):
            if current_time - last_heartbeat > self.timeout:
                timeout_clients.append(sid)
                logger.warning(f"客户端 {sid} 心跳超时")
        
        return timeout_clients
    
    def remove_client(self, sid):
        """
        移除客户端心跳记录
        
        Args:
            sid: 客户端Socket ID
        """
        if sid in self.client_heartbeats:
            del self.client_heartbeats[sid]
    
    def get_client_status(self, sid):
        """
        获取客户端连接状态
        
        Args:
            sid: 客户端Socket ID
            
        Returns:
            dict: 包含连接状态信息的字典
        """
        if sid not in self.client_heartbeats:
            return {'connected': False}
        
        last_heartbeat = self.client_heartbeats[sid]
        current_time = time.time()
        elapsed = current_time - last_heartbeat
        
        return {
            'connected': True,
            'last_heartbeat': last_heartbeat,
            'elapsed_seconds': elapsed,
            'is_timeout': elapsed > self.timeout
        }
    
    def get_all_clients(self):
        """
        获取所有客户端的心跳状态
        
        Returns:
            dict: {sid: status_dict}
        """
        return {
            sid: self.get_client_status(sid)
            for sid in self.client_heartbeats.keys()
        }
