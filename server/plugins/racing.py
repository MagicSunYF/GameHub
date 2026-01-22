from flask import request
from flask_socketio import emit, join_room
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validators import InputValidator, ValidationError
from plugins.base import GamePlugin

class RacingPlugin(GamePlugin):
    """极速狂飙游戏插件"""
    
    def register_routes(self):
        """极速狂飙无需HTTP路由"""
        pass
    
    def register_events(self):
        """注册极速狂飙WebSocket事件"""
        @self.socketio.on('create_room')
        def handle_create_room(data):
            if data.get('game') != 'racing':
                return
            
            initial_state = {
                'players_ready': 0,
                'scores': {},
                'game_started': False
            }
            room_id = self.game_manager.create_room('racing', initial_state)
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_created', {'room_id': room_id, 'position': 0})
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            if data.get('game') != 'racing':
                return
            
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            if data.get('spectator'):
                # 使用统一的观战者加入处理
                spectator_data = self.handle_spectator_join(room_id, request.sid)
                if spectator_data:
                    join_room(room_id)
                    # 同步当前游戏状态给观战者
                    self.safe_emit('spectator_joined', {
                        'room_id': room_id,
                        'game_started': spectator_data['state']['game_started'],
                        'scores': spectator_data['state']['scores']
                    })
                    # 通知房间内其他人有新观战者
                    self.broadcast_to_room('spectator_list_updated', {
                        'spectator_count': len(spectator_data['spectators'])
                    }, room_id, include_spectators=False)
                return
            
            if len(room['players']) >= 2:
                self.emit_error('房间已满')
                return
            
            position = len(room['players'])
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_joined', {'room_id': room_id, 'position': position})
            self.broadcast_to_room('player_joined', {'players': len(room['players'])}, room_id)
            
            if len(room['players']) == 2:
                self.broadcast_to_room('game_start', {}, room_id)
        
        @self.socketio.on('update_score')
        def handle_update_score(data):
            try:
                # 验证房间ID (需求11.2)
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                # 验证分数 (需求11.1, 11.3)
                score = InputValidator.validate_dict_field(data, 'score', required=True, field_type=int)
                if score < 0:
                    raise ValidationError("分数不能为负数", 'score', score)
                if score > 1000000:  # 合理的分数上限
                    raise ValidationError("分数超出合理范围", 'score', score)
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            # 阻止观战者执行游戏操作
            if self.prevent_spectator_action(room_id, request.sid):
                return
            
            player_idx = self.get_player_position(room_id, request.sid)
            if player_idx == -1:
                return
            
            room['state']['scores'][player_idx] = score
            
            # 广播给所有人（包括观战者）
            self.broadcast_to_room('score_update', {
                'position': player_idx,
                'score': score
            }, room_id)
        
        @self.socketio.on('game_over')
        def handle_game_over(data):
            try:
                # 验证房间ID (需求11.2)
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                # 验证分数 (需求11.1, 11.3)
                score = InputValidator.validate_dict_field(data, 'score', required=True, field_type=int)
                if score < 0:
                    raise ValidationError("分数不能为负数", 'score', score)
                if score > 1000000:  # 合理的分数上限
                    raise ValidationError("分数超出合理范围", 'score', score)
                room = self.validate_room(room_id)
            except ValidationError as e:
                self.emit_error(e.message)
                return
            except ValueError as e:
                self.emit_error(str(e))
                return
            
            # 阻止观战者执行游戏操作
            if self.prevent_spectator_action(room_id, request.sid):
                return
            
            player_idx = self.get_player_position(room_id, request.sid)
            if player_idx == -1:
                return
            
            room['state']['scores'][player_idx] = score
            
            # 广播给所有人（包括观战者）
            self.broadcast_to_room('player_finished', {
                'position': player_idx,
                'score': score
            }, room_id)
        
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
            
            join_room(room_id)
            
            player_idx = self.get_player_position(room_id, request.sid)
            if player_idx != -1:
                self.safe_emit('room_joined', {'room_id': room_id, 'position': player_idx})
                
                # 同步游戏状态
                if room['state']['game_started']:
                    self.safe_emit('game_start', {})
                
                # 同步分数
                for pos, score in room['state']['scores'].items():
                    self.safe_emit('score_update', {'position': pos, 'score': score})
        
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
