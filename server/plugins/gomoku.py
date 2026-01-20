from flask import request, jsonify
from flask_socketio import emit, join_room
from datetime import datetime
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from validators import InputValidator

class GomokuPlugin:
    def __init__(self, app, socketio, db, game_manager):
        self.app = app
        self.socketio = socketio
        self.db = db
        self.game_manager = game_manager
        self.register_routes()
        self.register_events()
        self.init_db()
    
    def init_db(self):
        schema = ['''
            CREATE TABLE IF NOT EXISTS game_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                moves TEXT NOT NULL,
                winner VARCHAR(8),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) CHARSET=utf8mb4 ENGINE=InnoDB;
        ''']
        self.db.init_tables(schema)
    
    def register_routes(self):
        @self.app.route('/save_game', methods=['POST'])
        def save_game():
            data = request.json
            try:
                moves = json.dumps(data.get('moves', []), ensure_ascii=False)
                winner = data.get('winner', '')
                with self.db.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO game_records (moves, winner, created_at) VALUES (%s, %s, %s)",
                        (moves, winner, datetime.now())
                    )
                    cur.close()
                return jsonify({'status': 'ok'}), 200
            except Exception as e:
                return jsonify({'status': 'error', 'reason': str(e)}), 500
    
    def register_events(self):
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
            emit('room_created', {'room_id': room_id, 'color': 1})
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
            except ValueError as e:
                emit('error', {'msg': str(e)})
                return
            
            is_spectator = data.get('spectator', False)
            room = self.game_manager.get_room(room_id)
            
            if not room:
                emit('error', {'msg': '房间不存在'})
                return
            
            if is_spectator:
                self.game_manager.add_spectator(room_id, request.sid)
                join_room(room_id)
                emit('spectator_joined', {
                    'room_id': room_id,
                    'board': room['state']['board'],
                    'current': room['state']['current']
                })
                return
            
            if len(room['players']) >= 2:
                emit('error', {'msg': '房间已满'})
                return
            
            self.game_manager.add_player(room_id, request.sid)
            join_room(room_id)
            emit('room_joined', {'room_id': room_id, 'color': 2})
            emit('game_start', {}, room=room_id)
        
        @self.socketio.on('make_move')
        def handle_move(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                r, c = InputValidator.validate_coordinates(data.get('row'), data.get('col'))
            except (ValueError, TypeError) as e:
                emit('error', {'msg': str(e)})
                return
            
            room = self.game_manager.get_room(room_id)
            
            if not room:
                return
            
            player_idx = room['players'].index(request.sid)
            color = player_idx + 1
            state = room['state']
            
            if state['current'] != color or state['board'][r][c] != 0:
                return
            
            state['board'][r][c] = color
            state['moves'].append({'row': r, 'col': c, 'color': 'black' if color == 1 else 'white'})
            state['current'] = 3 - color
            
            emit('move_made', {'row': r, 'col': c, 'color': color}, room=room_id)
            
            if self.check_win(state['board'], r, c, color):
                winner = 'black' if color == 1 else 'white'
                emit('game_over', {'winner': color}, room=room_id)
                self.save_game_to_db(state['moves'], winner)
        
        @self.socketio.on('send_comment')
        def handle_comment(data):
            try:
                room_id = InputValidator.validate_room_id(data.get('room_id'))
                comment = InputValidator.sanitize_comment(data.get('comment'))
            except ValueError as e:
                emit('error', {'msg': str(e)})
                return
            
            if self.game_manager.get_room(room_id):
                emit('new_comment', {'comment': comment}, room=room_id)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            for room_id, room in list(self.game_manager.rooms.items()):
                if request.sid in room['players']:
                    emit('player_left', {}, room=room_id)
                    self.game_manager.delete_room(room_id)
                    break
    
    def check_win(self, board, r, c, color):
        directions = [[0, 1], [1, 0], [1, 1], [1, -1]]
        for dr, dc in directions:
            cnt = 1
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] == color:
                    cnt += 1
                else:
                    break
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] == color:
                    cnt += 1
                else:
                    break
            if cnt >= 5:
                return True
        return False
    
    def save_game_to_db(self, moves, winner):
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                moves_json = json.dumps(moves, ensure_ascii=False)
                cur.execute(
                    "INSERT INTO game_records (moves, winner, created_at) VALUES (%s, %s, %s)",
                    (moves_json, winner, datetime.now())
                )
                cur.close()
        except Exception as e:
            print(f'保存对局失败: {e}')
