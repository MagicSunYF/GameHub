import re
import os
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """统一的验证错误类"""
    def __init__(self, message, field=None, value=None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典格式，用于API响应"""
        result = {'error': self.message}
        if self.field:
            result['field'] = self.field
        return result

class InputValidator:
    """输入验证工具类"""
    
    # 验证规则常量
    ROOM_ID_LENGTH = 8
    ROOM_ID_PATTERN = r'^[a-zA-Z0-9-]+$'
    GAME_ID_PATTERN = r'^[a-zA-Z0-9_-]+$'
    MAX_COMMENT_LENGTH = 200  # 需求11.6: 限制弹幕长度不超过200字符
    MAX_PLAYER_NAME_LENGTH = 50
    
    @staticmethod
    def _log_validation(field, value, success, error_msg=None):
        """记录验证日志"""
        if success:
            logger.debug(f"验证成功: {field}={value}")
        else:
            logger.warning(f"验证失败: {field}={value}, 错误: {error_msg}")
    
    @staticmethod
    def validate_game_id(game_id):
        """
        验证游戏ID，防止路径遍历攻击
        需求: 11.1 - 验证所有客户端输入
        """
        field = 'game_id'
        
        try:
            if not game_id:
                raise ValidationError("游戏ID不能为空", field, game_id)
            
            if not isinstance(game_id, str):
                raise ValidationError("游戏ID必须是字符串", field, game_id)
            
            # 防止路径遍历 (优先检查)
            if '..' in game_id or '/' in game_id or '\\' in game_id:
                raise ValidationError("游戏ID包含非法路径字符", field, game_id)
            
            # 只允许字母、数字、下划线和连字符
            if not re.match(InputValidator.GAME_ID_PATTERN, game_id):
                raise ValidationError("游戏ID包含非法字符", field, game_id)
            
            # 长度限制
            if len(game_id) > 50:
                raise ValidationError("游戏ID过长", field, game_id)
            
            InputValidator._log_validation(field, game_id, True)
            return game_id
            
        except ValidationError as e:
            InputValidator._log_validation(field, game_id, False, e.message)
            raise
    
    @staticmethod
    def validate_room_id(room_id):
        """
        验证房间ID
        需求: 11.2 - 检查房间ID格式和长度
        """
        field = 'room_id'
        
        try:
            if not room_id:
                raise ValidationError("房间ID不能为空", field, room_id)
            
            if not isinstance(room_id, str):
                raise ValidationError("房间ID必须是字符串", field, room_id)
            
            # 检查长度 (需求11.2)
            if len(room_id) != InputValidator.ROOM_ID_LENGTH:
                raise ValidationError(
                    f"房间ID长度必须为{InputValidator.ROOM_ID_LENGTH}位", 
                    field, 
                    room_id
                )
            
            # 只允许字母数字和连字符
            if not re.match(InputValidator.ROOM_ID_PATTERN, room_id):
                raise ValidationError("房间ID格式错误", field, room_id)
            
            InputValidator._log_validation(field, room_id, True)
            return room_id
            
        except ValidationError as e:
            InputValidator._log_validation(field, room_id, False, e.message)
            raise
    
    @staticmethod
    def sanitize_comment(comment):
        """
        清理评论内容，防止XSS
        需求: 11.4 - 过滤HTML标签和特殊字符
        需求: 11.6 - 限制弹幕长度不超过200字符
        """
        field = 'comment'
        
        try:
            if not comment:
                return ""
            
            if not isinstance(comment, str):
                comment = str(comment)
            
            # 限制长度 (需求11.6)
            if len(comment) > InputValidator.MAX_COMMENT_LENGTH:
                logger.info(f"评论被截断: 原长度={len(comment)}, 限制={InputValidator.MAX_COMMENT_LENGTH}")
                comment = comment[:InputValidator.MAX_COMMENT_LENGTH]
            
            # 移除潜在的HTML标签 (需求11.4)
            comment = re.sub(r'<[^>]*>', '', comment)
            
            # 移除特殊字符 (需求11.4)
            comment = re.sub(r'[<>\"\'&]', '', comment)
            
            result = comment.strip()
            InputValidator._log_validation(field, f"{len(result)}字符", True)
            return result
            
        except Exception as e:
            InputValidator._log_validation(field, comment, False, str(e))
            return ""
    
    @staticmethod
    def validate_coordinates(row, col, board_size=15):
        """
        验证棋盘坐标
        需求: 11.3 - 检查坐标范围和类型
        """
        field = 'coordinates'
        
        try:
            # 类型检查 (需求11.3)
            if not isinstance(row, int) or not isinstance(col, int):
                raise ValidationError("坐标必须是整数", field, f"({row}, {col})")
            
            # 范围检查 (需求11.3)
            if row < 0 or row >= board_size or col < 0 or col >= board_size:
                raise ValidationError(
                    f"坐标超出范围 (0-{board_size-1})", 
                    field, 
                    f"({row}, {col})"
                )
            
            InputValidator._log_validation(field, f"({row}, {col})", True)
            return row, col
            
        except ValidationError as e:
            InputValidator._log_validation(field, f"({row}, {col})", False, e.message)
            raise
    
    @staticmethod
    def validate_player_name(name):
        """
        验证玩家名称
        需求: 11.1 - 验证所有客户端输入
        """
        field = 'player_name'
        
        try:
            if not name:
                raise ValidationError("玩家名称不能为空", field, name)
            
            if not isinstance(name, str):
                raise ValidationError("玩家名称必须是字符串", field, name)
            
            # 长度限制
            if len(name) > InputValidator.MAX_PLAYER_NAME_LENGTH:
                raise ValidationError(
                    f"玩家名称过长(最多{InputValidator.MAX_PLAYER_NAME_LENGTH}字符)", 
                    field, 
                    name
                )
            
            # 移除特殊字符
            if re.search(r'[<>\"\'&]', name):
                raise ValidationError("玩家名称包含非法字符", field, name)
            
            InputValidator._log_validation(field, name, True)
            return name.strip()
            
        except ValidationError as e:
            InputValidator._log_validation(field, name, False, e.message)
            raise
    
    @staticmethod
    def validate_position(position, max_players):
        """
        验证玩家位置
        需求: 11.1 - 验证所有客户端输入
        """
        field = 'position'
        
        try:
            if not isinstance(position, int):
                raise ValidationError("位置必须是整数", field, position)
            
            if position < 0 or position >= max_players:
                raise ValidationError(
                    f"位置超出范围 (0-{max_players-1})", 
                    field, 
                    position
                )
            
            InputValidator._log_validation(field, position, True)
            return position
            
        except ValidationError as e:
            InputValidator._log_validation(field, position, False, e.message)
            raise
    
    @staticmethod
    def validate_dict_field(data, field_name, required=True, field_type=None):
        """
        验证字典中的字段
        需求: 11.1 - 验证所有客户端输入
        需求: 11.5 - 输入无效时返回错误消息而不是崩溃
        """
        try:
            if field_name not in data:
                if required:
                    raise ValidationError(f"缺少必需字段: {field_name}", field_name, None)
                return None
            
            value = data[field_name]
            
            if field_type and not isinstance(value, field_type):
                raise ValidationError(
                    f"字段类型错误: {field_name} 应为 {field_type.__name__}", 
                    field_name, 
                    value
                )
            
            return value
            
        except ValidationError as e:
            InputValidator._log_validation(field_name, data.get(field_name), False, e.message)
            raise
