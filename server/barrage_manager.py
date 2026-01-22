"""
弹幕管理器

提供弹幕发送的限流和过滤功能。

验证需求: 6.5, 6.6, 11.4, 11.6
"""

import time
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class BarrageManager:
    """
    弹幕管理器
    
    功能:
    - 限流: 防止用户频繁发送弹幕
    - 过滤: 过滤敏感词和重复内容
    - 统计: 记录弹幕发送统计
    """
    
    def __init__(self, rate_limit=3, time_window=10, max_history=100):
        """
        初始化弹幕管理器
        
        Args:
            rate_limit: 时间窗口内允许的最大弹幕数
            time_window: 时间窗口大小（秒）
            max_history: 保留的历史弹幕数量
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.max_history = max_history
        
        # 用户发送记录: {user_id: deque([timestamp1, timestamp2, ...])}
        self.user_records = defaultdict(lambda: deque(maxlen=rate_limit))
        
        # 房间弹幕历史: {room_id: deque([{text, user_id, timestamp}, ...])}
        self.room_history = defaultdict(lambda: deque(maxlen=max_history))
        
        # 敏感词列表（可扩展）
        self.blocked_words = set([
            # 添加需要过滤的敏感词
        ])
        
        logger.info(f"弹幕管理器初始化: 限流={rate_limit}条/{time_window}秒")
    
    def check_rate_limit(self, user_id):
        """
        检查用户是否超过发送频率限制
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否允许发送, 剩余冷却时间)
        
        验证需求: 6.5 - 弹幕限流
        """
        current_time = time.time()
        user_record = self.user_records[user_id]
        
        # 清理过期记录
        while user_record and current_time - user_record[0] > self.time_window:
            user_record.popleft()
        
        # 检查是否超过限制
        if len(user_record) >= self.rate_limit:
            # 计算需要等待的时间
            oldest_time = user_record[0]
            cooldown = self.time_window - (current_time - oldest_time)
            logger.warning(f"用户 {user_id} 发送弹幕过于频繁，需等待 {cooldown:.1f}秒")
            return False, cooldown
        
        # 记录本次发送
        user_record.append(current_time)
        return True, 0
    
    def filter_content(self, text):
        """
        过滤弹幕内容
        
        Args:
            text: 原始弹幕文本
        
        Returns:
            tuple: (是否通过过滤, 过滤后的文本, 拒绝原因)
        
        验证需求: 6.5 - 弹幕过滤
        """
        if not text or not text.strip():
            return False, "", "弹幕内容为空"
        
        text = text.strip()
        
        # 检查敏感词
        for word in self.blocked_words:
            if word in text:
                logger.warning(f"弹幕包含敏感词: {word}")
                return False, "", f"弹幕包含敏感词"
        
        # 检查是否全是重复字符
        if len(set(text)) == 1 and len(text) > 5:
            logger.warning(f"弹幕内容无效: 全是重复字符")
            return False, "", "弹幕内容无效"
        
        return True, text, ""
    
    def check_duplicate(self, room_id, user_id, text, time_threshold=5):
        """
        检查是否为重复弹幕
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            text: 弹幕文本
            time_threshold: 时间阈值（秒），在此时间内的相同内容视为重复
        
        Returns:
            bool: 是否为重复弹幕
        
        验证需求: 6.5 - 弹幕过滤
        """
        current_time = time.time()
        history = self.room_history[room_id]
        
        # 检查最近的弹幕
        for record in reversed(history):
            # 只检查时间阈值内的弹幕
            if current_time - record['timestamp'] > time_threshold:
                break
            
            # 检查是否为同一用户发送的相同内容
            if record['user_id'] == user_id and record['text'] == text:
                logger.warning(f"用户 {user_id} 发送重复弹幕: {text}")
                return True
        
        return False
    
    def add_barrage(self, room_id, user_id, text):
        """
        添加弹幕到历史记录
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            text: 弹幕文本
        """
        self.room_history[room_id].append({
            'text': text,
            'user_id': user_id,
            'timestamp': time.time()
        })
    
    def get_room_history(self, room_id, limit=50):
        """
        获取房间弹幕历史
        
        Args:
            room_id: 房间ID
            limit: 返回的最大数量
        
        Returns:
            list: 弹幕历史记录
        """
        history = list(self.room_history[room_id])
        return history[-limit:] if len(history) > limit else history
    
    def clear_room_history(self, room_id):
        """
        清除房间弹幕历史
        
        Args:
            room_id: 房间ID
        """
        if room_id in self.room_history:
            del self.room_history[room_id]
            logger.info(f"已清除房间 {room_id} 的弹幕历史")
    
    def clear_user_records(self, user_id):
        """
        清除用户发送记录
        
        Args:
            user_id: 用户ID
        """
        if user_id in self.user_records:
            del self.user_records[user_id]
    
    def get_stats(self, room_id=None):
        """
        获取统计信息
        
        Args:
            room_id: 房间ID（可选），如果提供则返回该房间的统计
        
        Returns:
            dict: 统计信息
        """
        if room_id:
            history = self.room_history.get(room_id, deque())
            return {
                'room_id': room_id,
                'total_barrages': len(history),
                'unique_users': len(set(r['user_id'] for r in history))
            }
        else:
            return {
                'total_rooms': len(self.room_history),
                'total_users': len(self.user_records),
                'total_barrages': sum(len(h) for h in self.room_history.values())
            }
