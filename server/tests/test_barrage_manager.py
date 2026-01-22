"""
弹幕管理器测试

验证需求: 6.5, 6.6, 11.4, 11.6
"""

import unittest
import time
from barrage_manager import BarrageManager


class TestBarrageManager(unittest.TestCase):
    """弹幕管理器测试类"""
    
    def setUp(self):
        """每个测试前初始化"""
        self.manager = BarrageManager(rate_limit=3, time_window=10)
    
    def test_rate_limit_allows_within_limit(self):
        """测试限流：允许限制内的发送"""
        user_id = "user1"
        
        # 前3条应该都允许
        for i in range(3):
            allowed, cooldown = self.manager.check_rate_limit(user_id)
            self.assertTrue(allowed, f"第{i+1}条弹幕应该被允许")
            self.assertEqual(cooldown, 0)
    
    def test_rate_limit_blocks_over_limit(self):
        """测试限流：阻止超过限制的发送"""
        user_id = "user1"
        
        # 发送3条
        for _ in range(3):
            self.manager.check_rate_limit(user_id)
        
        # 第4条应该被阻止
        allowed, cooldown = self.manager.check_rate_limit(user_id)
        self.assertFalse(allowed, "超过限制的弹幕应该被阻止")
        self.assertGreater(cooldown, 0, "应该返回冷却时间")
    
    def test_rate_limit_resets_after_window(self):
        """测试限流：时间窗口后重置"""
        manager = BarrageManager(rate_limit=2, time_window=1)
        user_id = "user1"
        
        # 发送2条
        for _ in range(2):
            manager.check_rate_limit(user_id)
        
        # 等待时间窗口过期
        time.sleep(1.1)
        
        # 应该可以再次发送
        allowed, cooldown = manager.check_rate_limit(user_id)
        self.assertTrue(allowed, "时间窗口后应该允许发送")
    
    def test_filter_empty_content(self):
        """测试过滤：空内容"""
        passed, text, reason = self.manager.filter_content("")
        self.assertFalse(passed, "空内容应该被过滤")
        self.assertIn("空", reason)
        
        passed, text, reason = self.manager.filter_content("   ")
        self.assertFalse(passed, "纯空格应该被过滤")
    
    def test_filter_repeated_characters(self):
        """测试过滤：重复字符"""
        passed, text, reason = self.manager.filter_content("aaaaaa")
        self.assertFalse(passed, "全是重复字符应该被过滤")
        self.assertIn("无效", reason)
    
    def test_filter_valid_content(self):
        """测试过滤：有效内容"""
        passed, text, reason = self.manager.filter_content("这是一条正常的弹幕")
        self.assertTrue(passed, "正常内容应该通过")
        self.assertEqual(text, "这是一条正常的弹幕")
    
    def test_check_duplicate_same_user(self):
        """测试重复检测：同一用户"""
        room_id = "room1"
        user_id = "user1"
        text = "重复的弹幕"
        
        # 第一次发送
        self.manager.add_barrage(room_id, user_id, text)
        
        # 立即发送相同内容
        is_duplicate = self.manager.check_duplicate(room_id, user_id, text)
        self.assertTrue(is_duplicate, "相同用户的相同内容应该被识别为重复")
    
    def test_check_duplicate_different_user(self):
        """测试重复检测：不同用户"""
        room_id = "room1"
        text = "相同的弹幕"
        
        # 用户1发送
        self.manager.add_barrage(room_id, "user1", text)
        
        # 用户2发送相同内容
        is_duplicate = self.manager.check_duplicate(room_id, "user2", text)
        self.assertFalse(is_duplicate, "不同用户的相同内容不应该被识别为重复")
    
    def test_check_duplicate_after_threshold(self):
        """测试重复检测：超过时间阈值"""
        manager = BarrageManager()
        room_id = "room1"
        user_id = "user1"
        text = "弹幕内容"
        
        # 发送弹幕
        manager.add_barrage(room_id, user_id, text)
        
        # 等待超过阈值
        time.sleep(6)
        
        # 应该不再被识别为重复
        is_duplicate = manager.check_duplicate(room_id, user_id, text, time_threshold=5)
        self.assertFalse(is_duplicate, "超过时间阈值后不应该被识别为重复")
    
    def test_add_and_get_history(self):
        """测试历史记录：添加和获取"""
        room_id = "room1"
        
        # 添加多条弹幕
        for i in range(5):
            self.manager.add_barrage(room_id, f"user{i}", f"弹幕{i}")
        
        # 获取历史
        history = self.manager.get_room_history(room_id)
        self.assertEqual(len(history), 5, "应该有5条历史记录")
        self.assertEqual(history[0]['text'], "弹幕0")
        self.assertEqual(history[4]['text'], "弹幕4")
    
    def test_history_limit(self):
        """测试历史记录：数量限制"""
        manager = BarrageManager(max_history=3)
        room_id = "room1"
        
        # 添加5条弹幕
        for i in range(5):
            manager.add_barrage(room_id, f"user{i}", f"弹幕{i}")
        
        # 应该只保留最后3条
        history = manager.get_room_history(room_id)
        self.assertEqual(len(history), 3, "应该只保留最后3条")
        self.assertEqual(history[0]['text'], "弹幕2")
        self.assertEqual(history[2]['text'], "弹幕4")
    
    def test_clear_room_history(self):
        """测试清除房间历史"""
        room_id = "room1"
        
        # 添加弹幕
        self.manager.add_barrage(room_id, "user1", "弹幕1")
        
        # 清除历史
        self.manager.clear_room_history(room_id)
        
        # 应该为空
        history = self.manager.get_room_history(room_id)
        self.assertEqual(len(history), 0, "清除后应该为空")
    
    def test_get_stats_single_room(self):
        """测试统计：单个房间"""
        room_id = "room1"
        
        # 添加弹幕
        self.manager.add_barrage(room_id, "user1", "弹幕1")
        self.manager.add_barrage(room_id, "user1", "弹幕2")
        self.manager.add_barrage(room_id, "user2", "弹幕3")
        
        # 获取统计
        stats = self.manager.get_stats(room_id)
        self.assertEqual(stats['total_barrages'], 3)
        self.assertEqual(stats['unique_users'], 2)
    
    def test_get_stats_global(self):
        """测试统计：全局"""
        # 添加多个房间的弹幕
        self.manager.add_barrage("room1", "user1", "弹幕1")
        self.manager.add_barrage("room2", "user2", "弹幕2")
        
        # 发送限流记录
        self.manager.check_rate_limit("user1")
        self.manager.check_rate_limit("user2")
        
        # 获取全局统计
        stats = self.manager.get_stats()
        self.assertEqual(stats['total_rooms'], 2)
        self.assertEqual(stats['total_users'], 2)
        self.assertEqual(stats['total_barrages'], 2)


if __name__ == '__main__':
    unittest.main()
