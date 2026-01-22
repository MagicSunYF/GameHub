"""
数据库连接管理测试

测试连接池、健康检查和优雅降级功能
验证需求: 10.1, 10.3, 10.6
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from database import Database
import time
import threading


class TestDatabaseConnectionPool(unittest.TestCase):
    """测试数据库连接池功能"""
    
    @patch('database.pymysql.connect')
    def test_connection_pool_initialization(self, mock_connect):
        """测试连接池初始化"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=3, max_overflow=2)
        
        # 验证创建了指定数量的连接
        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(db._current_size, 3)
        self.assertTrue(db.is_healthy())
    
    @patch('database.pymysql.connect')
    def test_get_connection_from_pool(self, mock_connect):
        """测试从连接池获取连接"""
        mock_conn = Mock()
        mock_conn.ping = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=2)
        
        # 获取连接
        with db.get_connection() as conn:
            self.assertIsNotNone(conn)
            mock_conn.ping.assert_called()
    
    @patch('database.pymysql.connect')
    def test_connection_pool_reuse(self, mock_connect):
        """测试连接池复用"""
        mock_conn = Mock()
        mock_conn.ping = Mock()
        mock_conn.commit = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=2)
        
        initial_call_count = mock_connect.call_count
        
        # 使用并归还连接
        with db.get_connection() as conn:
            pass
        
        # 再次获取连接，应该复用而不是创建新连接
        with db.get_connection() as conn:
            pass
        
        # 连接创建次数不应增加
        self.assertEqual(mock_connect.call_count, initial_call_count)
    
    @patch('database.pymysql.connect')
    def test_connection_pool_overflow(self, mock_connect):
        """测试连接池溢出"""
        mock_conn = Mock()
        mock_conn.ping = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1, max_overflow=2, pool_timeout=1)
        
        # 获取多个连接
        conns = []
        for _ in range(3):
            conn = db._get_connection_from_pool()
            conns.append(conn)
        
        # 验证创建了溢出连接
        self.assertEqual(db._current_size, 3)
        
        # 归还连接
        for conn in conns:
            db._return_connection_to_pool(conn)


class TestDatabaseHealthCheck(unittest.TestCase):
    """测试数据库健康检查功能"""
    
    @patch('database.pymysql.connect')
    def test_health_check_success(self, mock_connect):
        """测试健康检查成功"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.ping = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 执行健康检查
        result = db.health_check()
        
        self.assertTrue(result)
        self.assertTrue(db.is_healthy())
        mock_cursor.execute.assert_called_with("SELECT 1")
    
    @patch('database.pymysql.connect')
    def test_health_check_failure(self, mock_connect):
        """测试健康检查失败"""
        mock_conn = Mock()
        mock_conn.ping = Mock(side_effect=Exception("Connection lost"))
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 模拟连续失败
        for _ in range(3):
            db.health_check()
        
        # 验证标记为不健康
        self.assertFalse(db.is_healthy())
    
    @patch('database.pymysql.connect')
    def test_health_recovery(self, mock_connect):
        """测试健康状态恢复"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.ping = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 标记为不健康
        db._is_healthy = False
        db._consecutive_failures = 3
        
        # 执行健康检查
        result = db.health_check()
        
        # 验证恢复健康
        self.assertTrue(result)
        self.assertTrue(db.is_healthy())
        self.assertEqual(db._consecutive_failures, 0)


class TestDatabaseGracefulDegradation(unittest.TestCase):
    """测试数据库优雅降级功能"""
    
    @patch('database.pymysql.connect')
    def test_operation_blocked_when_unhealthy(self, mock_connect):
        """测试不健康时阻止操作"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 标记为不健康
        db._is_healthy = False
        
        # 尝试获取连接应该失败
        with self.assertRaises(Exception) as context:
            with db.get_connection() as conn:
                pass
        
        self.assertIn("不健康", str(context.exception))
    
    @patch('database.pymysql.connect')
    def test_consecutive_failures_trigger_unhealthy(self, mock_connect):
        """测试连续失败触发不健康状态"""
        mock_conn = Mock()
        mock_conn.ping = Mock()
        mock_conn.commit = Mock(side_effect=Exception("DB Error"))
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 模拟连续失败
        for _ in range(3):
            try:
                with db.get_connection() as conn:
                    pass
            except:
                pass
        
        # 验证标记为不健康
        self.assertFalse(db.is_healthy())
    
    @patch('database.pymysql.connect')
    def test_init_tables_skips_when_unhealthy(self, mock_connect):
        """测试不健康时跳过表初始化"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=1)
        
        # 标记为不健康
        db._is_healthy = False
        
        # 尝试初始化表应该跳过
        schema = ["CREATE TABLE test (id INT)"]
        db.init_tables(schema)
        
        # 验证没有执行SQL
        mock_conn.cursor.assert_not_called()


class TestDatabasePoolStats(unittest.TestCase):
    """测试连接池统计功能"""
    
    @patch('database.pymysql.connect')
    def test_get_pool_stats(self, mock_connect):
        """测试获取连接池统计信息"""
        mock_conn = Mock()
        mock_conn.ping = Mock()
        mock_connect.return_value = mock_conn
        
        config = {'host': 'localhost', 'user': 'test'}
        db = Database(config, pool_size=3, max_overflow=2)
        
        stats = db.get_pool_stats()
        
        self.assertEqual(stats['pool_size'], 3)
        self.assertEqual(stats['current_size'], 3)
        self.assertEqual(stats['available'], 3)
        self.assertEqual(stats['in_use'], 0)
        self.assertTrue(stats['is_healthy'])
        self.assertEqual(stats['consecutive_failures'], 0)


if __name__ == '__main__':
    unittest.main()
