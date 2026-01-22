import unittest
from validators import InputValidator, ValidationError

class TestInputValidator(unittest.TestCase):
    """验证器单元测试"""
    
    def test_validate_room_id_valid(self):
        """测试有效的房间ID"""
        valid_id = "abc12345"
        result = InputValidator.validate_room_id(valid_id)
        self.assertEqual(result, valid_id)
    
    def test_validate_room_id_invalid_length(self):
        """测试无效长度的房间ID"""
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_room_id("abc")
        self.assertIn("长度", ctx.exception.message)
    
    def test_validate_room_id_invalid_chars(self):
        """测试包含非法字符的房间ID"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_room_id("abc@1234")
    
    def test_validate_room_id_empty(self):
        """测试空房间ID"""
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_room_id("")
        self.assertIn("不能为空", ctx.exception.message)
    
    def test_validate_coordinates_valid(self):
        """测试有效坐标"""
        row, col = InputValidator.validate_coordinates(5, 10)
        self.assertEqual(row, 5)
        self.assertEqual(col, 10)
    
    def test_validate_coordinates_out_of_range(self):
        """测试超出范围的坐标"""
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_coordinates(20, 5)
        self.assertIn("超出范围", ctx.exception.message)
    
    def test_validate_coordinates_negative(self):
        """测试负数坐标"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_coordinates(-1, 5)
    
    def test_validate_coordinates_invalid_type(self):
        """测试非整数坐标"""
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_coordinates("5", 10)
        self.assertIn("整数", ctx.exception.message)
    
    def test_sanitize_comment_valid(self):
        """测试有效评论"""
        comment = "这是一条评论"
        result = InputValidator.sanitize_comment(comment)
        self.assertEqual(result, comment)
    
    def test_sanitize_comment_with_html(self):
        """测试包含HTML标签的评论"""
        comment = "这是<script>alert('xss')</script>评论"
        result = InputValidator.sanitize_comment(comment)
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)
    
    def test_sanitize_comment_too_long(self):
        """测试过长的评论"""
        comment = "a" * 300
        result = InputValidator.sanitize_comment(comment)
        self.assertEqual(len(result), 200)
    
    def test_sanitize_comment_special_chars(self):
        """测试包含特殊字符的评论"""
        comment = "评论<>&\"'"
        result = InputValidator.sanitize_comment(comment)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
    
    def test_validate_game_id_valid(self):
        """测试有效的游戏ID"""
        valid_id = "gomoku"
        result = InputValidator.validate_game_id(valid_id)
        self.assertEqual(result, valid_id)
    
    def test_validate_game_id_path_traversal(self):
        """测试路径遍历攻击"""
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_game_id("../etc/passwd")
        self.assertIn("路径", ctx.exception.message)
    
    def test_validate_player_name_valid(self):
        """测试有效的玩家名称"""
        name = "玩家123"
        result = InputValidator.validate_player_name(name)
        self.assertEqual(result, name)
    
    def test_validate_player_name_too_long(self):
        """测试过长的玩家名称"""
        name = "a" * 100
        with self.assertRaises(ValidationError) as ctx:
            InputValidator.validate_player_name(name)
        self.assertIn("过长", ctx.exception.message)
    
    def test_validate_position_valid(self):
        """测试有效的位置"""
        position = InputValidator.validate_position(1, 3)
        self.assertEqual(position, 1)
    
    def test_validate_position_out_of_range(self):
        """测试超出范围的位置"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_position(5, 3)
    
    def test_validation_error_to_dict(self):
        """测试ValidationError转换为字典"""
        error = ValidationError("测试错误", "test_field", "test_value")
        error_dict = error.to_dict()
        self.assertEqual(error_dict['error'], "测试错误")
        self.assertEqual(error_dict['field'], "test_field")

if __name__ == '__main__':
    unittest.main()
