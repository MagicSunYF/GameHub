"""
游戏插件基类

定义标准的游戏插件接口，提供统一的初始化流程、事件注册方式和错误处理机制。

验证需求: 2.1, 2.2, 2.3
"""

from abc import ABC, abstractmethod
from flask import request
from flask_socketio import emit
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from barrage_manager import BarrageManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GamePlugin(ABC):
    """
    游戏插件基类
    
    所有游戏插件必须继承此类并实现抽象方法。
    提供标准的初始化流程、事件注册和错误处理。
    """
    
    def __init__(self, app, socketio, db, game_manager, barrage_manager=None):
        """
        标准初始化流程
        
        Args:
            app: Flask应用实例
            socketio: SocketIO实例
            db: 数据库连接管理器
            game_manager: 游戏房间管理器
            barrage_manager: 弹幕管理器（可选）
        """
        self.app = app
        self.socketio = socketio
        self.db = db
        self.game_manager = game_manager
        self.barrage_manager = barrage_manager or BarrageManager()
        
        # 执行标准初始化流程
        try:
            logger.info(f"初始化游戏插件: {self.__class__.__name__}")
            
            # 注册HTTP路由
            self.register_routes()
            logger.info(f"{self.__class__.__name__}: HTTP路由注册完成")
            
            # 注册WebSocket事件
            self.register_events()
            logger.info(f"{self.__class__.__name__}: WebSocket事件注册完成")
            
            # 初始化数据库（如果数据库可用）
            if self.db:
                self.init_db()
                logger.info(f"{self.__class__.__name__}: 数据库初始化完成")
            else:
                logger.warning(f"{self.__class__.__name__}: 数据库不可用，跳过数据库初始化")
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__} 初始化失败: {e}")
            raise
    
    @abstractmethod
    def register_routes(self):
        """
        注册HTTP路由
        
        子类必须实现此方法来注册游戏特定的HTTP端点。
        使用 @self.app.route() 装饰器注册路由。
        """
        pass
    
    @abstractmethod
    def register_events(self):
        """
        注册WebSocket事件
        
        子类必须实现此方法来注册游戏特定的WebSocket事件处理器。
        使用 @self.socketio.on() 装饰器注册事件。
        """
        pass
    
    def init_db(self):
        """
        初始化数据库表
        
        子类可以重写此方法来创建游戏特定的数据库表。
        默认实现创建通用游戏记录表。
        
        验证需求: 10.2, 10.4, 10.5
        """
        if not self.db:
            return
        
        # 创建通用游戏记录表
        schema = ['''
            CREATE TABLE IF NOT EXISTS game_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                game_type VARCHAR(32) NOT NULL,
                room_id VARCHAR(16) NOT NULL,
                moves TEXT NOT NULL,
                winner VARCHAR(32),
                player_count INT DEFAULT 0,
                spectator_count INT DEFAULT 0,
                duration INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_game_type (game_type),
                INDEX idx_room_id (room_id),
                INDEX idx_created_at (created_at)
            ) CHARSET=utf8mb4 ENGINE=InnoDB;
        ''']
        
        try:
            self.db.init_tables(schema)
            logger.info(f"{self.__class__.__name__}: 通用游戏记录表初始化完成")
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: 数据库表初始化失败: {e}")
    
    def handle_error(self, error, context=""):
        """
        标准化错误处理
        
        Args:
            error: 异常对象或错误消息
            context: 错误上下文描述
        
        Returns:
            dict: 标准化的错误响应
        """
        error_msg = str(error)
        
        # 记录错误日志
        if context:
            logger.error(f"{self.__class__.__name__} - {context}: {error_msg}")
        else:
            logger.error(f"{self.__class__.__name__}: {error_msg}")
        
        # 返回标准化错误响应
        return {
            'status': 'error',
            'msg': error_msg
        }
    
    def emit_error(self, error_msg, context=""):
        """
        向客户端发送错误消息
        
        Args:
            error_msg: 错误消息
            context: 错误上下文描述
        """
        if context:
            logger.error(f"{self.__class__.__name__} - {context}: {error_msg}")
        else:
            logger.error(f"{self.__class__.__name__}: {error_msg}")
        
        emit('error', {'msg': error_msg})
    
    def safe_emit(self, event, data, room=None, **kwargs):
        """
        安全的事件发送，带错误处理
        
        Args:
            event: 事件名称
            data: 事件数据
            room: 房间ID（可选）
            **kwargs: 其他emit参数
        """
        try:
            if room:
                emit(event, data, room=room, **kwargs)
            else:
                emit(event, data, **kwargs)
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 发送事件失败 {event}: {e}")
    
    def validate_room(self, room_id):
        """
        验证房间是否存在
        
        Args:
            room_id: 房间ID
        
        Returns:
            dict: 房间数据，如果不存在返回None
        
        Raises:
            ValueError: 如果房间不存在
        """
        room = self.game_manager.get_room(room_id)
        if not room:
            raise ValueError('房间不存在')
        return room
    
    def get_player_position(self, room_id, player_id):
        """
        获取玩家在房间中的位置
        
        Args:
            room_id: 房间ID
            player_id: 玩家ID
        
        Returns:
            int: 玩家位置索引（从0开始），如果玩家不在房间返回-1
        """
        room = self.game_manager.get_room(room_id)
        if not room:
            return -1
        
        try:
            return room['players'].index(player_id)
        except ValueError:
            return -1
    
    def is_player_turn(self, room, player_id):
        """
        检查是否轮到该玩家操作
        
        Args:
            room: 房间数据
            player_id: 玩家ID
        
        Returns:
            bool: 是否轮到该玩家
        """
        try:
            player_idx = room['players'].index(player_id)
            current_turn = room['state'].get('current', 0)
            return player_idx + 1 == current_turn
        except (ValueError, KeyError):
            return False
    
    def save_to_db(self, query, params):
        """
        安全的数据库保存操作（带健康检查和优雅降级）
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            bool: 是否保存成功
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，跳过保存")
            return False
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，跳过保存")
            return False
        
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                cur.close()
            return True
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 数据库保存失败: {e}")
            # 数据库操作失败不影响游戏继续运行
            return False
    
    def query_from_db(self, query, params=None):
        """
        安全的数据库查询操作（带健康检查和优雅降级）
        
        Args:
            query: SQL查询语句
            params: 查询参数（可选）
        
        Returns:
            list: 查询结果，失败返回空列表
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，返回空结果")
            return []
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，返回空结果")
            return []
        
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                results = cur.fetchall()
                cur.close()
            return results
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 数据库查询失败: {e}")
            # 数据库操作失败不影响游戏继续运行
            return []
    
    def handle_spectator_join(self, room_id, spectator_id):
        """
        统一的观战者加入处理
        
        Args:
            room_id: 房间ID
            spectator_id: 观战者ID
        
        Returns:
            dict: 包含房间状态的响应数据，失败返回None
        """
        try:
            room = self.validate_room(room_id)
        except ValueError as e:
            self.emit_error(str(e))
            return None
        
        # 添加观战者
        if not self.game_manager.add_spectator(room_id, spectator_id):
            self.emit_error('加入观战失败')
            return None
        
        logger.info(f"{self.__class__.__name__}: 观战者 {spectator_id} 加入房间 {room_id}")
        
        # 返回当前游戏状态供子类使用
        return {
            'room_id': room_id,
            'state': room['state'],
            'players': room['players'],
            'spectators': room['spectators']
        }
    
    def broadcast_to_room(self, event, data, room_id, include_spectators=True):
        """
        向房间内所有人广播消息（包括观战者）
        
        Args:
            event: 事件名称
            data: 事件数据
            room_id: 房间ID
            include_spectators: 是否包括观战者（默认True）
        """
        if include_spectators:
            # 使用room参数会自动发送给房间内所有人（玩家+观战者）
            self.safe_emit(event, data, room=room_id)
        else:
            # 只发送给玩家
            room = self.game_manager.get_room(room_id)
            if room:
                for player_id in room['players']:
                    self.socketio.emit(event, data, room=player_id)
    
    def is_spectator(self, room_id, user_id):
        """
        检查用户是否为观战者
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        
        Returns:
            bool: 是否为观战者
        """
        return self.game_manager.is_spectator(room_id, user_id)
    
    def get_spectator_list(self, room_id):
        """
        获取房间的观战者列表
        
        Args:
            room_id: 房间ID
        
        Returns:
            list: 观战者ID列表
        """
        return self.game_manager.get_spectators(room_id)
    
    def handle_spectator_leave(self, room_id, spectator_id):
        """
        统一的观战者离开处理
        
        Args:
            room_id: 房间ID
            spectator_id: 观战者ID
        
        Returns:
            bool: 是否成功移除
        """
        if self.game_manager.remove_spectator(room_id, spectator_id):
            logger.info(f"{self.__class__.__name__}: 观战者 {spectator_id} 离开房间 {room_id}")
            
            # 通知房间内其他人观战者列表更新
            spectators = self.get_spectator_list(room_id)
            self.broadcast_to_room('spectator_list_updated', {
                'spectator_count': len(spectators)
            }, room_id, include_spectators=False)
            
            return True
        return False
    
    def sync_state_to_spectator(self, spectator_id, room_id, state_data):
        """
        同步游戏状态给特定观战者
        
        Args:
            spectator_id: 观战者ID
            room_id: 房间ID
            state_data: 要同步的状态数据
        """
        self.socketio.emit('spectator_joined', {
            'room_id': room_id,
            **state_data
        }, room=spectator_id)
    
    def prevent_spectator_action(self, room_id, user_id):
        """
        阻止观战者执行游戏操作
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
        
        Returns:
            bool: 如果是观战者返回True（应阻止操作），否则返回False
        """
        if self.is_spectator(room_id, user_id):
            self.emit_error('观战者不能执行游戏操作')
            logger.warning(f"{self.__class__.__name__}: 观战者 {user_id} 尝试执行游戏操作")
            return True
        return False
    
    def handle_barrage(self, room_id, user_id, comment):
        """
        统一的弹幕处理
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            comment: 弹幕内容
        
        Returns:
            bool: 是否成功发送弹幕
        
        验证需求: 6.5, 6.6
        """
        # 检查限流
        allowed, cooldown = self.barrage_manager.check_rate_limit(user_id)
        if not allowed:
            self.emit_error(f'发送过于频繁，请等待 {int(cooldown)} 秒')
            return False
        
        # 过滤内容
        passed, filtered_text, reason = self.barrage_manager.filter_content(comment)
        if not passed:
            self.emit_error(f'弹幕被过滤: {reason}')
            return False
        
        # 检查重复
        if self.barrage_manager.check_duplicate(room_id, user_id, filtered_text):
            self.emit_error('请勿发送重复弹幕')
            return False
        
        # 添加到历史记录
        self.barrage_manager.add_barrage(room_id, user_id, filtered_text)
        
        # 广播弹幕
        self.broadcast_to_room('new_comment', {'comment': filtered_text}, room_id)
        
        logger.info(f"{self.__class__.__name__}: 用户 {user_id} 在房间 {room_id} 发送弹幕")
        return True
    
    def get_barrage_history(self, room_id, limit=50):
        """
        获取房间弹幕历史
        
        Args:
            room_id: 房间ID
            limit: 返回的最大数量
        
        Returns:
            list: 弹幕历史记录
        """
        return self.barrage_manager.get_room_history(room_id, limit)
    
    def clear_barrage_history(self, room_id):
        """
        清除房间弹幕历史
        
        Args:
            room_id: 房间ID
        """
        self.barrage_manager.clear_room_history(room_id)
    
    def save_game_record(self, room_id, moves, winner=None, duration=0):
        """
        标准化游戏记录保存接口
        
        保存游戏记录到通用游戏记录表。
        
        Args:
            room_id: 房间ID
            moves: 游戏走法/操作记录（将被转换为JSON）
            winner: 获胜者标识（可选）
            duration: 游戏时长（秒，可选）
        
        Returns:
            bool: 是否保存成功
        
        验证需求: 10.2, 10.4, 10.5
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，跳过游戏记录保存")
            return False
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，跳过游戏记录保存")
            return False
        
        try:
            import json
            from datetime import datetime
            
            # 获取房间信息
            room = self.game_manager.get_room(room_id)
            if not room:
                logger.warning(f"{self.__class__.__name__}: 房间 {room_id} 不存在，无法保存记录")
                return False
            
            game_type = room.get('game_type', 'unknown')
            player_count = len(room.get('players', []))
            spectator_count = len(room.get('spectators', []))
            
            # 将走法转换为JSON字符串
            moves_json = json.dumps(moves, ensure_ascii=False)
            
            # 保存到数据库
            query = """
                INSERT INTO game_records 
                (game_type, room_id, moves, winner, player_count, spectator_count, duration, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (game_type, room_id, moves_json, winner, player_count, spectator_count, duration, datetime.now())
            
            success = self.save_to_db(query, params)
            if success:
                logger.info(f"{self.__class__.__name__}: 游戏记录已保存 - 房间: {room_id}, 游戏类型: {game_type}")
            return success
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 保存游戏记录失败: {e}")
            return False
    
    def query_game_records(self, game_type=None, limit=50, offset=0):
        """
        标准化游戏记录查询接口
        
        查询游戏记录，支持按游戏类型过滤。
        
        Args:
            game_type: 游戏类型（可选，None表示查询所有类型）
            limit: 返回记录数量限制（默认50）
            offset: 偏移量（默认0）
        
        Returns:
            list: 游戏记录列表，每条记录为字典格式
        
        验证需求: 10.2, 10.4, 10.5
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，返回空结果")
            return []
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，返回空结果")
            return []
        
        try:
            if game_type:
                query = """
                    SELECT id, game_type, room_id, moves, winner, 
                           player_count, spectator_count, duration, created_at
                    FROM game_records 
                    WHERE game_type = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                params = (game_type, limit, offset)
            else:
                query = """
                    SELECT id, game_type, room_id, moves, winner, 
                           player_count, spectator_count, duration, created_at
                    FROM game_records 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                params = (limit, offset)
            
            results = self.query_from_db(query, params)
            logger.info(f"{self.__class__.__name__}: 查询到 {len(results)} 条游戏记录")
            return results
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 查询游戏记录失败: {e}")
            return []
    
    def query_game_record_by_id(self, record_id):
        """
        根据ID查询单条游戏记录
        
        Args:
            record_id: 记录ID
        
        Returns:
            dict: 游戏记录，如果不存在返回None
        
        验证需求: 10.2, 10.4, 10.5
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，返回空结果")
            return None
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，返回空结果")
            return None
        
        try:
            query = """
                SELECT id, game_type, room_id, moves, winner, 
                       player_count, spectator_count, duration, created_at
                FROM game_records 
                WHERE id = %s
            """
            results = self.query_from_db(query, (record_id,))
            
            if results:
                logger.info(f"{self.__class__.__name__}: 查询到记录 ID={record_id}")
                return results[0]
            else:
                logger.info(f"{self.__class__.__name__}: 记录 ID={record_id} 不存在")
                return None
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 查询游戏记录失败: {e}")
            return None
    
    def query_game_stats(self, game_type=None):
        """
        查询游戏统计信息
        
        Args:
            game_type: 游戏类型（可选，None表示查询所有类型）
        
        Returns:
            dict: 统计信息，包含总局数、平均时长等
        
        验证需求: 10.2, 10.4, 10.5
        """
        if not self.db:
            logger.debug(f"{self.__class__.__name__}: 数据库不可用，返回空结果")
            return {}
        
        # 检查数据库健康状态
        if not self.db.is_healthy():
            logger.warning(f"{self.__class__.__name__}: 数据库不健康，返回空结果")
            return {}
        
        try:
            if game_type:
                query = """
                    SELECT 
                        COUNT(*) as total_games,
                        AVG(duration) as avg_duration,
                        AVG(player_count) as avg_players,
                        AVG(spectator_count) as avg_spectators
                    FROM game_records 
                    WHERE game_type = %s
                """
                params = (game_type,)
            else:
                query = """
                    SELECT 
                        COUNT(*) as total_games,
                        AVG(duration) as avg_duration,
                        AVG(player_count) as avg_players,
                        AVG(spectator_count) as avg_spectators
                    FROM game_records
                """
                params = None
            
            results = self.query_from_db(query, params)
            
            if results:
                stats = results[0]
                logger.info(f"{self.__class__.__name__}: 查询到统计信息")
                return stats
            else:
                return {}
                
        except Exception as e:
            logger.error(f"{self.__class__.__name__} - 查询游戏统计失败: {e}")
            return {}
