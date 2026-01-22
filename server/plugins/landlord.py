from flask import request
from flask_socketio import emit, join_room
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validators import InputValidator, ValidationError
from plugins.base import GamePlugin

class LandlordPlugin(GamePlugin):
    """斗地主游戏插件"""
    
    def register_routes(self):
        """斗地主无需HTTP路由"""
        pass
    
    def register_events(self):
        """注册斗地主WebSocket事件"""
        @self.socketio.on('create_room')
        def handle_create_room(data):
            if data.get('game') != 'landlord':
                return
            
            initial_state = {
                'players_ready': 0,
                'cards': {},
                'bottom_cards': [],
                'landlord': None,
                'current_turn': 0,
                'last_play': [],
                'last_play_position': None,
                'bids': {},
                'bid_multiplier': 1,
                'pass_count': 0
            }
            room_id = self.game_manager.create_room('landlord', initial_state)
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_created', {'room_id': room_id, 'position': 0})
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            if data.get('game') != 'landlord':
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
                        'landlord': spectator_data['state']['landlord'],
                        'current_turn': spectator_data['state']['current_turn'],
                        'last_play': spectator_data['state']['last_play']
                    })
                    # 通知房间内其他人有新观战者
                    self.broadcast_to_room('spectator_list_updated', {
                        'spectator_count': len(spectator_data['spectators'])
                    }, room_id, include_spectators=False)
                return
            
            if len(room['players']) >= 3:
                self.emit_error('房间已满')
                return
            
            position = len(room['players'])
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            self.safe_emit('room_joined', {'room_id': room_id, 'position': position})
            
            if len(room['players']) == 3:
                self.start_game(room_id, room)
        
        @self.socketio.on('bid')
        def handle_bid(data):
            try:
                # 验证房间ID (需求11.2)
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                # 验证叫牌值 (需求11.1, 11.3, 需求13.3)
                bid = InputValidator.validate_dict_field(data, 'bid', required=True, field_type=int)
                if bid < 0 or bid > 3:
                    raise ValidationError("叫牌值必须在0-3之间", 'bid', bid)
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
            
            # 记录叫牌 (需求13.3)
            room['state']['bids'][player_idx] = bid
            
            # 广播叫牌信息给所有人
            self.broadcast_to_room('player_bid', {
                'position': player_idx,
                'bid': bid
            }, room_id)
            
            # 检查是否所有人都叫牌完毕
            if len(room['state']['bids']) == 3:
                # 找出最高叫牌者作为地主 (需求13.3)
                max_bid = max(room['state']['bids'].values())
                
                # 如果所有人都不叫(bid=0)，重新开始
                if max_bid == 0:
                    self.broadcast_to_room('no_landlord', {}, room_id)
                    return
                
                # 确定地主（如果多人叫同样分数，取最先叫的）
                landlord = None
                for i in range(3):
                    if room['state']['bids'].get(i) == max_bid:
                        landlord = i
                        break
                
                room['state']['landlord'] = landlord
                room['state']['current_turn'] = landlord
                room['state']['bid_multiplier'] = max_bid
                
                # 将底牌给地主 (需求13.4)
                room['state']['cards'][landlord].extend(room['state']['bottom_cards'])
                
                # 广播地主确定信息给所有人（包括观战者）
                self.broadcast_to_room('landlord_decided', {
                    'landlord': landlord,
                    'bottom_cards': room['state']['bottom_cards'],
                    'bid_multiplier': max_bid
                }, room_id)
                
                # 通知地主更新手牌
                self.socketio.emit('update_cards', {
                    'cards': room['state']['cards'][landlord]
                }, room=room['players'][landlord])
                
                # 地主先出牌
                self.broadcast_to_room('play_turn', {
                    'position': landlord,
                    'can_pass': False
                }, room_id)
            else:
                # 下一位玩家叫牌
                next_player = (player_idx + 1) % 3
                self.broadcast_to_room('bid_turn', {'position': next_player}, room_id)
        
        @self.socketio.on('play_cards')
        def handle_play_cards(data):
            try:
                # 验证房间ID (需求11.2)
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                # 验证出牌数据 (需求11.1, 11.3)
                cards = InputValidator.validate_dict_field(data, 'cards', required=True, field_type=list)
                if not cards:
                    raise ValidationError("出牌不能为空", 'cards', cards)
                if len(cards) > 20:  # 最多20张牌（顺子等）
                    raise ValidationError("出牌数量过多", 'cards', cards)
                # 验证每张牌的格式
                for card in cards:
                    if not isinstance(card, dict):
                        raise ValidationError("牌格式错误", 'cards', card)
                    if 'suit' not in card or 'value' not in card:
                        raise ValidationError("牌缺少必需字段", 'cards', card)
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
            
            # 验证是否轮到该玩家
            if room['state']['current_turn'] != player_idx:
                self.emit_error("还没轮到你出牌")
                return
            
            # 记录上次出牌
            room['state']['last_play'] = cards
            room['state']['last_play_position'] = player_idx
            room['state']['pass_count'] = 0  # 重置pass计数
            
            # 从玩家手牌中移除出的牌
            try:
                for card in cards:
                    room['state']['cards'][player_idx].remove(card)
            except (ValueError, KeyError) as e:
                self.emit_error("出牌无效：牌不在手中")
                return
            
            remaining = len(room['state']['cards'][player_idx])
            
            # 广播出牌信息给所有人（包括观战者）
            self.broadcast_to_room('cards_played', {
                'position': player_idx,
                'cards': cards,
                'remaining': remaining
            }, room_id)
            
            # 检查游戏是否结束 (需求13.7)
            if remaining == 0:
                # 计算是否春天（其他玩家一张牌都没出）
                spring = all(
                    len(room['state']['cards'][i]) == 17 
                    for i in range(3) 
                    if i != player_idx
                )
                
                # 计算得分倍数
                multiplier = room['state'].get('bid_multiplier', 1)
                if spring:
                    multiplier *= 2
                
                # 广播游戏结束
                self.broadcast_to_room('game_over', {
                    'winner': player_idx,
                    'spring': spring,
                    'multiplier': multiplier,
                    'is_landlord': player_idx == room['state']['landlord']
                }, room_id)
                return
            
            # 下一位玩家出牌
            room['state']['current_turn'] = (player_idx + 1) % 3
            
            # 判断下一位玩家是否可以pass（如果上家是自己则不能pass）
            can_pass = True
            
            self.broadcast_to_room('play_turn', {
                'position': room['state']['current_turn'],
                'can_pass': can_pass
            }, room_id)
        
        @self.socketio.on('pass')
        def handle_pass(data):
            try:
                # 验证房间ID (需求11.2)
                room_id = InputValidator.validate_room_id(data.get('room_id'))
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
            
            # 验证是否轮到该玩家
            if room['state']['current_turn'] != player_idx:
                self.emit_error("还没轮到你")
                return
            
            # 增加pass计数
            room['state']['pass_count'] = room['state'].get('pass_count', 0) + 1
            
            # 广播pass信息
            self.broadcast_to_room('player_passed', {
                'position': player_idx
            }, room_id)
            
            # 下一位玩家
            next_player = (player_idx + 1) % 3
            room['state']['current_turn'] = next_player
            
            # 如果连续两人pass，则清空上次出牌，下一位玩家可以出任意牌
            can_pass = True
            if room['state']['pass_count'] >= 2:
                room['state']['last_play'] = []
                room['state']['last_play_position'] = None
                room['state']['pass_count'] = 0
                can_pass = False  # 新一轮开始，不能pass
            
            self.broadcast_to_room('play_turn', {
                'position': next_player,
                'can_pass': can_pass
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
                if player_idx in room['state']['cards']:
                    self.safe_emit('game_start', {'cards': room['state']['cards'][player_idx]})
                
                if room['state']['landlord'] is not None:
                    self.safe_emit('landlord_decided', {
                        'landlord': room['state']['landlord'],
                        'bottom_cards': room['state']['bottom_cards']
                    })
                
                if room['state']['last_play']:
                    self.safe_emit('cards_played', {
                        'position': -1,
                        'cards': room['state']['last_play'],
                        'remaining': 0
                    })
                
                if room['state']['current_turn'] is not None:
                    self.safe_emit('play_turn', {'position': room['state']['current_turn']})
        
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
    
    def start_game(self, room_id, room):
        """开始游戏，发牌"""
        deck = self.create_deck()
        random.shuffle(deck)
        
        room['state']['bottom_cards'] = deck[:3]
        
        for i in range(3):
            room['state']['cards'][i] = deck[3 + i*17:3 + (i+1)*17]
        
        for i, player_sid in enumerate(room['players']):
            self.socketio.emit('game_start', {
                'cards': room['state']['cards'][i]
            }, room=player_sid)
        
        # 广播给所有人（包括观战者）
        self.broadcast_to_room('bid_turn', {'position': 0}, room_id)
    
    def create_deck(self):
        """创建一副牌"""
        suits = ['♠', '♥', '♣', '♦']
        values = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
        deck = [{'suit': s, 'value': v} for s in suits for v in values]
        deck.append({'suit': '', 'value': 'joker'})
        deck.append({'suit': '', 'value': 'JOKER'})
        return deck
