import unittest
import time
from game_manager import GameManager, RoomStatus, PlayerStatus


class TestGameManager(unittest.TestCase):
    def setUp(self):
        self.manager = GameManager(room_timeout=2)
    
    def test_create_room(self):
        """Test room creation with initial state"""
        room_id = self.manager.create_room('gomoku', {'board': []})
        self.assertIsNotNone(room_id)
        self.assertEqual(len(room_id), 8)
        
        room = self.manager.get_room(room_id)
        self.assertIsNotNone(room)
        self.assertEqual(room['game_type'], 'gomoku')
        self.assertEqual(room['status'], RoomStatus.WAITING)
        self.assertEqual(len(room['players']), 0)
    
    def test_room_status_enum(self):
        """Test room status transitions"""
        room_id = self.manager.create_room('gomoku', {})
        
        # Initial status should be WAITING
        room = self.manager.get_room(room_id)
        self.assertEqual(room['status'], RoomStatus.WAITING)
        
        # Update to PLAYING
        self.manager.update_room_status(room_id, RoomStatus.PLAYING)
        room = self.manager.get_room(room_id)
        self.assertEqual(room['status'], RoomStatus.PLAYING)
        
        # Update to FINISHED
        self.manager.update_room_status(room_id, RoomStatus.FINISHED)
        room = self.manager.get_room(room_id)
        self.assertEqual(room['status'], RoomStatus.FINISHED)
    
    def test_room_timeout_cleanup(self):
        """Test automatic cleanup of inactive rooms"""
        room_id1 = self.manager.create_room('gomoku', {})
        room_id2 = self.manager.create_room('landlord', {})
        
        # Wait for timeout
        time.sleep(2.5)
        
        # Create a new room that should not be cleaned up
        room_id3 = self.manager.create_room('racing', {})
        
        # Cleanup inactive rooms
        inactive = self.manager.cleanup_inactive_rooms()
        
        # room_id1 and room_id2 should be cleaned up
        self.assertIn(room_id1, inactive)
        self.assertIn(room_id2, inactive)
        self.assertNotIn(room_id3, inactive)
        
        # Verify rooms are deleted
        self.assertIsNone(self.manager.get_room(room_id1))
        self.assertIsNone(self.manager.get_room(room_id2))
        self.assertIsNotNone(self.manager.get_room(room_id3))
    
    def test_update_room_activity(self):
        """Test that activity updates prevent timeout"""
        room_id = self.manager.create_room('gomoku', {})
        
        # Wait 1 second
        time.sleep(1)
        
        # Update activity
        self.manager.update_room_activity(room_id)
        
        # Wait another 1.5 seconds (total 2.5 from creation, but only 1.5 from activity update)
        time.sleep(1.5)
        
        # Room should still exist
        inactive = self.manager.cleanup_inactive_rooms()
        self.assertNotIn(room_id, inactive)
        self.assertIsNotNone(self.manager.get_room(room_id))
    
    def test_get_all_rooms(self):
        """Test querying all rooms"""
        room_id1 = self.manager.create_room('gomoku', {})
        room_id2 = self.manager.create_room('landlord', {})
        
        self.manager.add_player(room_id1, 'player1')
        self.manager.add_spectator(room_id2, 'spectator1')
        
        all_rooms = self.manager.get_all_rooms()
        
        self.assertEqual(len(all_rooms), 2)
        self.assertIn(room_id1, all_rooms)
        self.assertIn(room_id2, all_rooms)
        
        self.assertEqual(all_rooms[room_id1]['game_type'], 'gomoku')
        self.assertEqual(all_rooms[room_id1]['player_count'], 1)
        self.assertEqual(all_rooms[room_id2]['spectator_count'], 1)
    
    def test_get_rooms_by_game(self):
        """Test querying rooms by game type"""
        gomoku_id1 = self.manager.create_room('gomoku', {})
        gomoku_id2 = self.manager.create_room('gomoku', {})
        landlord_id = self.manager.create_room('landlord', {})
        
        gomoku_rooms = self.manager.get_rooms_by_game('gomoku')
        
        self.assertEqual(len(gomoku_rooms), 2)
        self.assertIn(gomoku_id1, gomoku_rooms)
        self.assertIn(gomoku_id2, gomoku_rooms)
        self.assertNotIn(landlord_id, gomoku_rooms)
    
    def test_delete_room(self):
        """Test room deletion"""
        room_id = self.manager.create_room('gomoku', {})
        self.assertIsNotNone(self.manager.get_room(room_id))
        
        result = self.manager.delete_room(room_id)
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_room(room_id))
        
        # Deleting non-existent room should return False
        result = self.manager.delete_room(room_id)
        self.assertFalse(result)
    
    def test_add_player_updates_activity(self):
        """Test that adding a player updates room activity"""
        room_id = self.manager.create_room('gomoku', {})
        initial_activity = self.manager.get_room(room_id)['last_activity']
        
        time.sleep(0.1)
        self.manager.add_player(room_id, 'player1')
        
        updated_activity = self.manager.get_room(room_id)['last_activity']
        self.assertGreater(updated_activity, initial_activity)
    
    def test_prevent_duplicate_player_join(self):
        """Test that adding the same player twice doesn't create duplicates"""
        room_id = self.manager.create_room('gomoku', {})
        
        # Add player first time
        result1 = self.manager.add_player(room_id, 'player1')
        self.assertTrue(result1)
        
        room = self.manager.get_room(room_id)
        self.assertEqual(len(room['players']), 1)
        
        # Add same player again
        result2 = self.manager.add_player(room_id, 'player1')
        self.assertTrue(result2)
        
        # Should still have only 1 player
        room = self.manager.get_room(room_id)
        self.assertEqual(len(room['players']), 1)
        self.assertEqual(room['players'][0], 'player1')
    
    def test_kick_player(self):
        """Test kicking a player from a room"""
        room_id = self.manager.create_room('gomoku', {})
        self.manager.add_player(room_id, 'player1')
        self.manager.add_player(room_id, 'player2')
        
        room = self.manager.get_room(room_id)
        self.assertEqual(len(room['players']), 2)
        
        # Kick player1
        result = self.manager.kick_player(room_id, 'player1')
        self.assertTrue(result)
        
        room = self.manager.get_room(room_id)
        self.assertEqual(len(room['players']), 1)
        self.assertNotIn('player1', room['players'])
        self.assertIn('player2', room['players'])
        
        # Player status should be updated to disconnected
        status = self.manager.get_player_status('player1')
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], PlayerStatus.DISCONNECTED)
    
    def test_kick_nonexistent_player(self):
        """Test kicking a player that's not in the room"""
        room_id = self.manager.create_room('gomoku', {})
        
        # Try to kick player that doesn't exist
        result = self.manager.kick_player(room_id, 'nonexistent')
        self.assertFalse(result)
    
    def test_kick_from_nonexistent_room(self):
        """Test kicking from a room that doesn't exist"""
        result = self.manager.kick_player('nonexistent_room', 'player1')
        self.assertFalse(result)
    
    def test_player_status_tracking(self):
        """Test player status is tracked when joining"""
        room_id = self.manager.create_room('gomoku', {})
        
        # Add player
        self.manager.add_player(room_id, 'player1')
        
        # Check player status
        status = self.manager.get_player_status('player1')
        self.assertIsNotNone(status)
        self.assertEqual(status['room_id'], room_id)
        self.assertEqual(status['status'], PlayerStatus.CONNECTED)
        self.assertIn('joined_at', status)
    
    def test_update_player_status(self):
        """Test updating player status"""
        room_id = self.manager.create_room('gomoku', {})
        self.manager.add_player(room_id, 'player1')
        
        # Update to READY
        result = self.manager.update_player_status('player1', PlayerStatus.READY)
        self.assertTrue(result)
        
        status = self.manager.get_player_status('player1')
        self.assertEqual(status['status'], PlayerStatus.READY)
        
        # Update to PLAYING
        result = self.manager.update_player_status('player1', PlayerStatus.PLAYING)
        self.assertTrue(result)
        
        status = self.manager.get_player_status('player1')
        self.assertEqual(status['status'], PlayerStatus.PLAYING)
    
    def test_update_nonexistent_player_status(self):
        """Test updating status of non-existent player"""
        result = self.manager.update_player_status('nonexistent', PlayerStatus.READY)
        self.assertFalse(result)
    
    def test_get_player_room(self):
        """Test getting the room a player is in"""
        room_id = self.manager.create_room('gomoku', {})
        self.manager.add_player(room_id, 'player1')
        
        player_room = self.manager.get_player_room('player1')
        self.assertEqual(player_room, room_id)
        
        # Non-existent player
        player_room = self.manager.get_player_room('nonexistent')
        self.assertIsNone(player_room)
    
    def test_is_player_in_room(self):
        """Test checking if a player is in a specific room"""
        room_id1 = self.manager.create_room('gomoku', {})
        room_id2 = self.manager.create_room('landlord', {})
        
        self.manager.add_player(room_id1, 'player1')
        
        # Player should be in room1
        self.assertTrue(self.manager.is_player_in_room(room_id1, 'player1'))
        
        # Player should not be in room2
        self.assertFalse(self.manager.is_player_in_room(room_id2, 'player1'))
        
        # Non-existent room
        self.assertFalse(self.manager.is_player_in_room('nonexistent', 'player1'))
    
    def test_remove_player_clears_status(self):
        """Test that removing a player clears their status tracking"""
        room_id = self.manager.create_room('gomoku', {})
        self.manager.add_player(room_id, 'player1')
        
        # Verify status exists
        status = self.manager.get_player_status('player1')
        self.assertIsNotNone(status)
        
        # Remove player
        self.manager.remove_player(room_id, 'player1')
        
        # Status should be cleared
        status = self.manager.get_player_status('player1')
        self.assertIsNone(status)


if __name__ == '__main__':
    unittest.main()
