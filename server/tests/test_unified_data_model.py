"""
统一数据模型测试

测试通用游戏记录表和标准化数据接口
验证需求: 10.2, 10.4, 10.5
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
sys.path.append(os.path.dirname(__file__))

from plugins.base import GamePlugin
from game_manager import GameManager


class MockDatabase:
    """模拟数据库"""
    def __init__(self, healthy=True):
        self._healthy = healthy
        self.records = []
        self.init_called = False
        
    def is_healthy(self):
        return self._healthy
    
    def init_tables(self, schema):
        self.init_called = True
        
    def get_connection(self):
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def cursor(self):
        cursor = Mock()
        cursor.execute = Mock()
        cursor.fetchall = Mock(return_value=self.records)
        cursor.fetchone = Mock(return_value=self.records[0] if self.records else None)
        cursor.close = Mock()
        return cursor


class TestGamePluginImpl(GamePlugin):
    """测试用游戏插件实现"""
    def register_routes(self):
        pass
    
    def register_events(self):
        pass


class TestUnifiedDataModel(unittest.TestCase):
    """测试统一数据模型"""
    
    def setUp(self):
        """测试前准备"""
        self.app = Mock()
        self.socketio = Mock()
        self.game_manager = GameManager()
        
    def test_init_db_creates_unified_table(self):
        """测试初始化创建通用游戏记录表"""
        db = MockDatabase()
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 验证数据库初始化被调用
        self.assertTrue(db.init_called)
    
    def test_save_game_record_success(self):
        """测试保存游戏记录成功"""
        db = MockDatabase()
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 创建测试房间
        room_id = self.game_manager.create_room('test_game', {'test': 'state'})
        self.game_manager.add_player(room_id, 'player1')
        
        # 保存游戏记录
        moves = [{'move': 1}, {'move': 2}]
        result = plugin.save_game_record(room_id, moves, 'player1', 120)
        
        # 验证保存成功
        self.assertTrue(result)
    
    def test_save_game_record_no_db(self):
        """测试无数据库时保存游戏记录"""
        plugin = TestGamePluginImpl(self.app, self.socketio, None, self.game_manager)
        
        # 保存游戏记录
        result = plugin.save_game_record('room123', [], 'player1')
        
        # 验证返回False
        self.assertFalse(result)
    
    def test_save_game_record_unhealthy_db(self):
        """测试数据库不健康时保存游戏记录"""
        db = MockDatabase(healthy=False)
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 保存游戏记录
        result = plugin.save_game_record('room123', [], 'player1')
        
        # 验证返回False
        self.assertFalse(result)
    
    def test_save_game_record_room_not_exist(self):
        """测试房间不存在时保存游戏记录"""
        db = MockDatabase()
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 保存不存在的房间记录
        result = plugin.save_game_record('nonexistent', [], 'player1')
        
        # 验证返回False
        self.assertFalse(result)
    
    def test_query_game_records_all(self):
        """测试查询所有游戏记录"""
        db = MockDatabase()
        db.records = [
            {'id': 1, 'game_type': 'gomoku', 'room_id': 'room1', 'moves': '[]', 
             'winner': 'black', 'player_count': 2, 'spectator_count': 0, 
             'duration': 120, 'created_at': '2024-01-01'},
            {'id': 2, 'game_type': 'landlord', 'room_id': 'room2', 'moves': '[]', 
             'winner': 'player1', 'player_count': 3, 'spectator_count': 1, 
             'duration': 300, 'created_at': '2024-01-02'}
        ]
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询所有记录
        results = plugin.query_game_records()
        
        # 验证返回结果
        self.assertEqual(len(results), 2)
    
    def test_query_game_records_by_type(self):
        """测试按游戏类型查询记录"""
        db = MockDatabase()
        db.records = [
            {'id': 1, 'game_type': 'gomoku', 'room_id': 'room1', 'moves': '[]', 
             'winner': 'black', 'player_count': 2, 'spectator_count': 0, 
             'duration': 120, 'created_at': '2024-01-01'}
        ]
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询五子棋记录
        results = plugin.query_game_records(game_type='gomoku')
        
        # 验证返回结果
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['game_type'], 'gomoku')
    
    def test_query_game_records_no_db(self):
        """测试无数据库时查询记录"""
        plugin = TestGamePluginImpl(self.app, self.socketio, None, self.game_manager)
        
        # 查询记录
        results = plugin.query_game_records()
        
        # 验证返回空列表
        self.assertEqual(results, [])
    
    def test_query_game_records_unhealthy_db(self):
        """测试数据库不健康时查询记录"""
        db = MockDatabase(healthy=False)
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询记录
        results = plugin.query_game_records()
        
        # 验证返回空列表
        self.assertEqual(results, [])
    
    def test_query_game_record_by_id(self):
        """测试根据ID查询单条记录"""
        db = MockDatabase()
        db.records = [
            {'id': 1, 'game_type': 'gomoku', 'room_id': 'room1', 'moves': '[]', 
             'winner': 'black', 'player_count': 2, 'spectator_count': 0, 
             'duration': 120, 'created_at': '2024-01-01'}
        ]
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询记录
        result = plugin.query_game_record_by_id(1)
        
        # 验证返回结果
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 1)
    
    def test_query_game_record_by_id_not_found(self):
        """测试查询不存在的记录"""
        db = MockDatabase()
        db.records = []
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询不存在的记录
        result = plugin.query_game_record_by_id(999)
        
        # 验证返回None
        self.assertIsNone(result)
    
    def test_query_game_stats(self):
        """测试查询游戏统计信息"""
        db = MockDatabase()
        db.records = [
            {'total_games': 10, 'avg_duration': 180.5, 
             'avg_players': 2.5, 'avg_spectators': 1.2}
        ]
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询统计信息
        stats = plugin.query_game_stats()
        
        # 验证返回结果
        self.assertEqual(stats['total_games'], 10)
        self.assertAlmostEqual(stats['avg_duration'], 180.5)
    
    def test_query_game_stats_by_type(self):
        """测试按游戏类型查询统计信息"""
        db = MockDatabase()
        db.records = [
            {'total_games': 5, 'avg_duration': 150.0, 
             'avg_players': 2.0, 'avg_spectators': 0.5}
        ]
        plugin = TestGamePluginImpl(self.app, self.socketio, db, self.game_manager)
        
        # 查询五子棋统计信息
        stats = plugin.query_game_stats(game_type='gomoku')
        
        # 验证返回结果
        self.assertEqual(stats['total_games'], 5)
    
    def test_query_game_stats_no_db(self):
        """测试无数据库时查询统计信息"""
        plugin = TestGamePluginImpl(self.app, self.socketio, None, self.game_manager)
        
        # 查询统计信息
        stats = plugin.query_game_stats()
        
        # 验证返回空字典
        self.assertEqual(stats, {})


if __name__ == '__main__':
    unittest.main()
