import uuid
import time
from enum import Enum

class RoomStatus(Enum):
    WAITING = 'waiting'
    PLAYING = 'playing'
    FINISHED = 'finished'

class PlayerStatus(Enum):
    CONNECTED = 'connected'
    READY = 'ready'
    PLAYING = 'playing'
    DISCONNECTED = 'disconnected'

class GameManager:
    def __init__(self, room_timeout=1800):
        self.rooms = {}
        self.room_timeout = room_timeout
        self.player_status = {}  # {player_id: {room_id: str, status: PlayerStatus, joined_at: float}}
    
    def create_room(self, game_type, initial_state):
        room_id = str(uuid.uuid4())[:8]
        self.rooms[room_id] = {
            'game_type': game_type,
            'players': [],
            'state': initial_state,
            'spectators': [],
            'status': RoomStatus.WAITING,
            'created_at': time.time(),
            'last_activity': time.time()
        }
        return room_id
    
    def get_room(self, room_id):
        return self.rooms.get(room_id)
    
    def get_all_rooms(self):
        return {
            room_id: {
                'game_type': room['game_type'],
                'player_count': len(room['players']),
                'spectator_count': len(room['spectators']),
                'status': room['status'].value,
                'created_at': room['created_at']
            }
            for room_id, room in self.rooms.items()
        }
    
    def get_rooms_by_game(self, game_type):
        return {
            room_id: room
            for room_id, room in self.rooms.items()
            if room['game_type'] == game_type
        }
    
    def update_room_status(self, room_id, status):
        if room_id in self.rooms:
            if isinstance(status, RoomStatus):
                self.rooms[room_id]['status'] = status
                self.rooms[room_id]['last_activity'] = time.time()
                return True
        return False
    
    def update_room_activity(self, room_id):
        if room_id in self.rooms:
            self.rooms[room_id]['last_activity'] = time.time()
            return True
        return False
    
    def delete_room(self, room_id):
        if room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False
    
    def cleanup_inactive_rooms(self):
        current_time = time.time()
        inactive_rooms = [
            room_id for room_id, room in self.rooms.items()
            if current_time - room['last_activity'] > self.room_timeout
        ]
        for room_id in inactive_rooms:
            del self.rooms[room_id]
        return inactive_rooms
    
    def add_player(self, room_id, player_id):
        """Add a player to a room, preventing duplicates"""
        if room_id not in self.rooms:
            return False
        
        # Prevent duplicate joins
        if player_id in self.rooms[room_id]['players']:
            return True  # Already in room, return success
        
        self.rooms[room_id]['players'].append(player_id)
        
        # Track player status
        self.player_status[player_id] = {
            'room_id': room_id,
            'status': PlayerStatus.CONNECTED,
            'joined_at': time.time()
        }
        
        self.update_room_activity(room_id)
        return True
    
    def remove_player(self, room_id, player_id):
        """Remove a player from a room"""
        if room_id in self.rooms:
            if player_id in self.rooms[room_id]['players']:
                self.rooms[room_id]['players'].remove(player_id)
            
            # Remove player status tracking
            if player_id in self.player_status:
                del self.player_status[player_id]
            
            self.update_room_activity(room_id)
            return True
        return False
    
    def kick_player(self, room_id, player_id):
        """Kick a player from a room (explicit removal)"""
        if room_id not in self.rooms:
            return False
        
        if player_id not in self.rooms[room_id]['players']:
            return False
        
        # Remove player
        self.rooms[room_id]['players'].remove(player_id)
        
        # Update player status to disconnected
        if player_id in self.player_status:
            self.player_status[player_id]['status'] = PlayerStatus.DISCONNECTED
        
        self.update_room_activity(room_id)
        return True
    
    def update_player_status(self, player_id, status):
        """Update a player's status"""
        if player_id in self.player_status:
            if isinstance(status, PlayerStatus):
                self.player_status[player_id]['status'] = status
                return True
        return False
    
    def get_player_status(self, player_id):
        """Get a player's current status"""
        return self.player_status.get(player_id)
    
    def get_player_room(self, player_id):
        """Get the room ID a player is currently in"""
        if player_id in self.player_status:
            return self.player_status[player_id]['room_id']
        return None
    
    def is_player_in_room(self, room_id, player_id):
        """Check if a player is in a specific room"""
        if room_id in self.rooms:
            return player_id in self.rooms[room_id]['players']
        return False
    
    def add_spectator(self, room_id, spectator_id):
        """Add a spectator to a room, preventing duplicates"""
        if room_id not in self.rooms:
            return False
        
        # Prevent duplicate joins
        if spectator_id in self.rooms[room_id]['spectators']:
            return True  # Already spectating, return success
        
        self.rooms[room_id]['spectators'].append(spectator_id)
        self.update_room_activity(room_id)
        return True
    
    def remove_spectator(self, room_id, spectator_id):
        """Remove a spectator from a room"""
        if room_id in self.rooms:
            if spectator_id in self.rooms[room_id]['spectators']:
                self.rooms[room_id]['spectators'].remove(spectator_id)
            self.update_room_activity(room_id)
            return True
        return False
    
    def is_spectator(self, room_id, spectator_id):
        """Check if a user is a spectator in a specific room"""
        if room_id in self.rooms:
            return spectator_id in self.rooms[room_id]['spectators']
        return False
    
    def get_spectators(self, room_id):
        """Get list of spectators in a room"""
        if room_id in self.rooms:
            return self.rooms[room_id]['spectators'].copy()
        return []
