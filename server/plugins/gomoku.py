from flask import request, jsonify
from flask_socketio import emit, join_room
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validators import InputValidator, ValidationError
from game_manager import RoomStatus
from plugins.base import GamePlugin

class GomokuPlugin(GamePlugin):
    """五子棋游戏插件"""
    
    def init_db(self):
        """初始化五子棋游戏记录表"""
        # 使用基类的通用游戏记录表
        super().init_db()
    
    def register_routes(self):
        """注册五子棋HTTP路由"""
        @self.app.route('/save_game', methods=['POST'])
        def save_game():
            """保留旧接口以保持向后兼容"""
            data = request.json
            try:
                moves = data.get('moves', [])
                winner = data.get('winner', '')
                room_id = data.get('room_id', 'unknown')
                
                # 使用新的标准化接口
                success = self.save_game_record(room_id, moves, winner)
                
                if success:
                    return jsonify({'status': 'ok'}), 200
                else:
                    return jsonify({'status': 'error', 'reason': '数据库不可用'}), 500
            except Exception as e:
                return jsonify(self.handle_error(e, "保存游戏记录")), 500
    
    def register_events(self):
        """注册五子棋WebSocket事件"""
        @self.socketio.on('create_room')
        def handle_create_room():
            initial_state = {
                'board': [[0]*15 for _ in range(15)],
                'current': 1,
                'moves': []
            }
            room_id = self.game_manager.create_room('gomoku', initial_state)
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_created', {'room_id': room_id, 'color': 1})
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            is_spectator = data.get('spectator', False)
            
            if is_spectator:
                # 使用统一的观战者加入处理
                spectator_data = self.handle_spectator_join(room_id, request.sid)
                if spectator_data:
                    join_room(room_id)
                    # 同步当前游戏状态给观战者
                    self.safe_emit('spectator_joined', {
                        'room_id': room_id,
                        'board': spectator_data['state']['board'],
                        'current': spectator_data['state']['current'],
                        'moves': spectator_data['state']['moves']
                    })
                    # 通知房间内其他人有新观战者
                    self.broadcast_to_room('spectator_list_updated', {
                        'spectator_count': len(spectator_data['spectators'])
                    }, room_id, include_spectators=False)
                return
            
            if len(room['players']) >= 2:
                self.emit_error('房间已满')
                return
            
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_joined', {'room_id': room_id, 'color': 2})
            self.game_manager.update_room_status(room_id, RoomStatus.PLAYING)
            self.broadcast_to_room('game_start', {}, room_id)
        
        @self.socketio.on('make_move')
        def handle_move(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                r, c = InputValidator.validate_coordinates(data.get('row'), data.get('col'))
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except (ValueError, TypeError) as e:
                self.emit_error(str(e))
                return
            
            # 阻止观战者执行游戏操作
            if self.prevent_spectator_action(room_id, request.sid):
                return
            
            player_idx = self.get_player_position(room_id, request.sid)
            if player_idx == -1:
                return
            
            color = player_idx + 1
            state = room['state']
            
            if state['current'] != color or state['board'][r][c] != 0:
                return
            
            state['board'][r][c] = color
            state['moves'].append({'row': r, 'col': c, 'color': 'black' if color == 1 else 'white'})
            state['current'] = 3 - color
            
            # 广播给所有人（包括观战者）
            self.broadcast_to_room('move_made', {'row': r, 'col': c, 'color': color}, room_id)
            
            if self.check_win(state['board'], r, c, color):
                winner = 'black' if color == 1 else 'white'
                self.game_manager.update_room_status(room_id, RoomStatus.FINISHED)
                self.broadcast_to_room('game_over', {'winner': color}, room_id)
                # 使用标准化接口保存游戏记录
                self.save_game_record(room_id, state['moves'], winner)
        
        @self.socketio.on('send_comment')
        def handle_comment(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                comment = InputValidator.sanitize_comment(data.get('comment'))
                self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            # 使用统一的弹幕处理（包含限流和过滤）
            self.handle_barrage(room_id, request.sid, comment)
        
        @self.socketio.on('rejoin_room')
        def handle_rejoin_room(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            # 重新加入房间
            join_room(room_id)
            
            # 同步当前游戏状态
            player_idx = self.get_player_position(room_id, request.sid)
            if player_idx != -1:
                color = player_idx + 1
                self.safe_emit('room_joined', {'room_id': room_id, 'color': color})
                self.safe_emit('game_start', {})
                
                # 重放所有走法
                for move in room['state']['moves']:
                    self.safe_emit('move_made', {
                        'row': move['row'],
                        'col': move['col'],
                        'color': 1 if move['color'] == 'black' else 2
                    })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            for room_id, room in list(self.game_manager.rooms.items()):
                if request.sid in room['players']:
                    self.safe_emit('player_left', {}, room=room_id)
                    self.game_manager.delete_room(room_id)
                    break
                elif request.sid in room['spectators']:
                    # 处理观战者离开
                    self.handle_spectator_leave(room_id, request.sid)
                    break
    
    def check_win(self, board, r, c, color):
        """
        检查是否获胜（优化版本）
        
        优化特性：
        - 严格边界检查：防止数组越界
        - 性能优化：提前终止，减少不必要的检查
        - 清晰逻辑：使用辅助函数提高可读性
        
        Args:
            board: 15x15棋盘
            r: 最后落子的行坐标
            c: 最后落子的列坐标
            color: 棋子颜色 (1=黑, 2=白)
        
        Returns:
            bool: 是否形成五连
        
        验证需求: 12.5, 12.6
        """
        # 边界检查：确保坐标在有效范围内
        if not (0 <= r < 15 and 0 <= c < 15):
            return False
        
        # 验证当前位置是否为指定颜色
        if board[r][c] != color:
            return False
        
        # 辅助函数：计算指定方向上的连续棋子数
        def count_direction(row, col, delta_row, delta_col):
            """
            从指定位置沿某方向计数连续相同颜色的棋子
            
            Args:
                row, col: 起始位置
                delta_row, delta_col: 方向增量
            
            Returns:
                int: 连续棋子数（不包括起始位置）
            """
            count = 0
            for step in range(1, 5):  # 最多检查4步（加上中心点共5个）
                new_row = row + delta_row * step
                new_col = col + delta_col * step
                
                # 边界检查
                if not (0 <= new_row < 15 and 0 <= new_col < 15):
                    break
                
                # 颜色匹配检查
                if board[new_row][new_col] == color:
                    count += 1
                else:
                    break
            
            return count
        
        # 四个方向：横、竖、主对角线、副对角线
        # 每个方向检查正反两个方向
        directions = [
            (0, 1),   # 横向：左右
            (1, 0),   # 竖向：上下
            (1, 1),   # 主对角线：左上到右下
            (1, -1)   # 副对角线：右上到左下
        ]
        
        for dr, dc in directions:
            # 计算正反两个方向的连续棋子数，加上中心点（1）
            total_count = 1 + count_direction(r, c, dr, dc) + count_direction(r, c, -dr, -dc)
            
            # 性能优化：一旦找到五连立即返回
            if total_count >= 5:
                return True
        
        return False
