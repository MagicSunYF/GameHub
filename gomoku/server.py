from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import pymysql
import json
from datetime import datetime
import uuid
import os

# 数据库配置信息
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'gomoku',
    'charset': 'utf8mb4',
}

def get_db_conn():
    return pymysql.connect(**MYSQL_CONFIG)

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS game_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            moves TEXT NOT NULL,
            winner VARCHAR(8),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) CHARSET=utf8mb4 ENGINE=InnoDB;
    ''')
    conn.commit()
    cur.close()
    conn.close()

app = Flask(__name__, static_folder='..')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据库表
init_db()

# 房间管理
rooms = {}  # {room_id: {'players': [sid1, sid2], 'board': [], 'current': 1}}

@app.route('/')
def index():
    return send_from_directory('..', 'index.html')

@app.route('/gomoku/<path:path>')
def gomoku_files(path):
    return send_from_directory('.', path)

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('..', path)

@app.route('/save_game', methods=['POST'])
def save_game():
    data = request.json
    try:
        moves = json.dumps(data.get('moves', []), ensure_ascii=False)
        winner = data.get('winner', '')
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO game_records (moves, winner, created_at) VALUES (%s, %s, %s)",
            (moves, winner, datetime.now())
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 500

@socketio.on('create_room')
def handle_create_room():
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {'players': [request.sid], 'board': [[0]*15 for _ in range(15)], 'current': 1, 'moves': []}
    join_room(room_id)
    emit('room_created', {'room_id': room_id, 'color': 1})

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data.get('room_id')
    is_spectator = data.get('spectator', False)
    if room_id not in rooms:
        emit('error', {'msg': '房间不存在'})
        return
    if is_spectator:
        join_room(room_id)
        emit('spectator_joined', {'room_id': room_id, 'board': rooms[room_id]['board'], 'current': rooms[room_id]['current']})
        return
    if len(rooms[room_id]['players']) >= 2:
        emit('error', {'msg': '房间已满'})
        return
    rooms[room_id]['players'].append(request.sid)
    join_room(room_id)
    emit('room_joined', {'room_id': room_id, 'color': 2})
    emit('game_start', {}, room=room_id)

@socketio.on('make_move')
def handle_move(data):
    room_id = data.get('room_id')
    r, c = data.get('row'), data.get('col')
    if room_id not in rooms:
        return
    room = rooms[room_id]
    player_idx = room['players'].index(request.sid)
    color = player_idx + 1
    if room['current'] != color or room['board'][r][c] != 0:
        return
    room['board'][r][c] = color
    room['moves'].append({'row': r, 'col': c, 'color': 'black' if color == 1 else 'white'})
    room['current'] = 3 - color
    emit('move_made', {'row': r, 'col': c, 'color': color}, room=room_id)
    if check_win(room['board'], r, c, color):
        winner = 'black' if color == 1 else 'white'
        emit('game_over', {'winner': color}, room=room_id)
        save_game_to_db(room['moves'], winner)

def save_game_to_db(moves, winner):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        moves_json = json.dumps(moves, ensure_ascii=False)
        cur.execute(
            "INSERT INTO game_records (moves, winner, created_at) VALUES (%s, %s, %s)",
            (moves_json, winner, datetime.now())
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'保存对局失败: {e}')

@socketio.on('send_comment')
def handle_comment(data):
    room_id = data.get('room_id')
    comment = data.get('comment')
    if room_id in rooms:
        emit('new_comment', {'comment': comment}, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    for room_id, room in list(rooms.items()):
        if request.sid in room['players']:
            emit('player_left', {}, room=room_id)
            del rooms[room_id]
            break

def check_win(board, r, c, color):
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

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)


