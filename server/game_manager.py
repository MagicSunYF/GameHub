import uuid

class GameManager:
    def __init__(self):
        self.rooms = {}
    
    def create_room(self, game_type, initial_state):
        room_id = str(uuid.uuid4())[:8]
        self.rooms[room_id] = {
            'game_type': game_type,
            'players': [],
            'state': initial_state,
            'spectators': []
        }
        return room_id
    
    def get_room(self, room_id):
        return self.rooms.get(room_id)
    
    def delete_room(self, room_id):
        if room_id in self.rooms:
            del self.rooms[room_id]
    
    def add_player(self, room_id, player_id):
        if room_id in self.rooms:
            self.rooms[room_id]['players'].append(player_id)
            return True
        return False
    
    def remove_player(self, room_id, player_id):
        if room_id in self.rooms:
            if player_id in self.rooms[room_id]['players']:
                self.rooms[room_id]['players'].remove(player_id)
            return True
        return False
    
    def add_spectator(self, room_id, spectator_id):
        if room_id in self.rooms:
            self.rooms[room_id]['spectators'].append(spectator_id)
            return True
        return False
