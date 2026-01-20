import re
import os

class InputValidator:
    """输入验证工具类"""
    
    @staticmethod
    def validate_game_id(game_id):
        """验证游戏ID，防止路径遍历攻击"""
        if not game_id:
            raise ValueError("游戏ID不能为空")
        
        # 只允许字母、数字、下划线和连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', game_id):
            raise ValueError("游戏ID包含非法字符")
        
        # 防止路径遍历
        if '..' in game_id or '/' in game_id or '\\' in game_id:
            raise ValueError("游戏ID包含非法路径字符")
        
        return game_id
    
    @staticmethod
    def validate_room_id(room_id):
        """验证房间ID"""
        if not room_id:
            raise ValueError("房间ID不能为空")
        
        # 只允许字母数字和连字符
        if not re.match(r'^[a-zA-Z0-9-]+$', room_id):
            raise ValueError("房间ID格式错误")
        
        return room_id
    
    @staticmethod
    def sanitize_comment(comment):
        """清理评论内容，防止XSS"""
        if not comment:
            return ""
        
        # 限制长度
        max_length = 500
        comment = str(comment)[:max_length]
        
        # 移除潜在的HTML标签
        comment = re.sub(r'<[^>]*>', '', comment)
        
        return comment.strip()
    
    @staticmethod
    def validate_coordinates(row, col, board_size=15):
        """验证棋盘坐标"""
        if not isinstance(row, int) or not isinstance(col, int):
            raise ValueError("坐标必须是整数")
        
        if row < 0 or row >= board_size or col < 0 or col >= board_size:
            raise ValueError(f"坐标超出范围 (0-{board_size-1})")
        
        return row, col
