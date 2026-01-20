from flask import request
from flask_socketio import emit, join_room
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validators import InputValidator

class LandlordPlugin:
    def __init__(self, app, socketio, db, game_manager):
        self.app = app
        self.socketio = socketio
        self.game_manager = game_manager
        self.register_events()
    
    def register_events(self):
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
                'bids': {}
            }
            room_id = self.game_manager.create_room('landlord', initial_state)
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            emit('room_created', {'room_id': room_id, 'position': 0})
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            if data.get('game') != 'landlord':
                return
            
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
            except ValueError as e:
                emit('error', {'msg': str(e)})
                return
            
            room = self.game_manager.get_room(room_id)
            if not room:
                emit('error', {'msg': '房间不存在'})
                return
            
            if data.get('spectator'):
                self.game_manager.add_spectator(room_id, request.sid)
                join_room(room_id)
                emit('spectator_joined', {'room_id': room_id})
                return
            
            if len(room['players']) >= 3:
                emit('error', {'msg': '房间已满'})
                return
            
            position = len(room['players'])
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            emit('room_joined', {'room_id': room_id, 'position': position})
            
            if len(room['players']) == 3:
                self.start_game(room_id, room)
        
        @self.socketio.on('bid')
        def handle_bid(data):
            room_id = data.get('room_id')
            bid = data.get('bid')
            room = self.game_manager.get_room(room_id)
            
            if not room:
                return
            
            player_idx = room['players'].index(request.sid)
            room['state']['bids'][player_idx] = bid
            
            if len(room['state']['bids']) == 3:
                landlord = max(room['state']['bids'], key=room['state']['bids'].get)
                room['state']['landlord'] = landlord
                room['state']['current_turn'] = landlord
                
                emit('landlord_decided', {
                    'landlord': landlord,
                    'bottom_cards': room['state']['bottom_cards']
                }, room=room_id)
                
                emit('play_turn', {'position': landlord}, room=room_id)
            else:
                next_player = (player_idx + 1) % 3
                emit('bid_turn', {'position': next_player}, room=room_id)
        
        @self.socketio.on('play_cards')
        def handle_play_cards(data):
            room_id = data.get('room_id')
            cards = data.get('cards')
            room = self.game_manager.get_room(room_id)
            
            if not room:
                return
            
            player_idx = room['players'].index(request.sid)
            room['state']['last_play'] = cards
            
            for card in cards:
                room['state']['cards'][player_idx].remove(card)
            
            remaining = len(room['state']['cards'][player_idx])
            emit('cards_played', {
                'position': player_idx,
                'cards': cards,
                'remaining': remaining
            }, room=room_id)
            
            if remaining == 0:
                spring = all(len(room['state']['cards'][i]) == 17 for i in range(3) if i != player_idx)
                emit('game_over', {'winner': player_idx, 'spring': spring}, room=room_id)
                return
            
            room['state']['current_turn'] = (player_idx + 1) % 3
            emit('play_turn', {'position': room['state']['current_turn']}, room=room_id)
        
        @self.socketio.on('pass')
        def handle_pass(data):
            room_id = data.get('room_id')
            room = self.game_manager.get_room(room_id)
            
            if not room:
                return
            
            player_idx = room['players'].index(request.sid)
            room['state']['current_turn'] = (player_idx + 1) % 3
            emit('play_turn', {'position': room['state']['current_turn']}, room=room_id)
    
    def start_game(self, room_id, room):
        deck = self.create_deck()
        random.shuffle(deck)
        
        room['state']['bottom_cards'] = deck[:3]
        
        for i in range(3):
            room['state']['cards'][i] = deck[3 + i*17:3 + (i+1)*17]
        
        for i, player_sid in enumerate(room['players']):
            self.socketio.emit('game_start', {
                'cards': room['state']['cards'][i]
            }, room=player_sid)
        
        self.socketio.emit('bid_turn', {'position': 0}, room=room_id)
    
    def create_deck(self):
        suits = ['♠', '♥', '♣', '♦']
        values = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
        deck = [{'suit': s, 'value': v} for s in suits for v in values]
        deck.append({'suit': '', 'value': 'joker'})
        deck.append({'suit': '', 'value': 'JOKER'})
        return deck
