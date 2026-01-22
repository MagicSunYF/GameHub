import os
import sys
import logging

logger = logging.getLogger(__name__)

class Config:
    """应用配置类"""
    
    # 数据库配置
    MYSQL_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', '123456'),
        'database': os.getenv('DB_NAME', 'gomoku'),
        'charset': 'utf8mb4',
    }
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # CORS配置
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
    
    @classmethod
    def validate(cls):
        """
        验证配置有效性
        
        Returns:
            bool: 配置是否有效
        """
        errors = []
        
        # 验证端口范围
        if not (1 <= cls.PORT <= 65535):
            errors.append(f"无效的端口号: {cls.PORT}")
        
        # 验证数据库端口
        if not (1 <= cls.MYSQL_CONFIG['port'] <= 65535):
            errors.append(f"无效的数据库端口: {cls.MYSQL_CONFIG['port']}")
        
        # 清理空字符串
        if cls.ALLOWED_ORIGINS:
            cls.ALLOWED_ORIGINS = [origin.strip() for origin in cls.ALLOWED_ORIGINS if origin.strip()]
        
        if errors:
            for error in errors:
                logger.error(f"配置错误: {error}")
            return False
        
        logger.info("配置验证通过")
        return True
    
    @classmethod
    def log_config(cls):
        """记录当前配置（隐藏敏感信息）"""
        logger.info("=== 应用配置 ===")
        logger.info(f"服务器: {cls.HOST}:{cls.PORT}")
        logger.info(f"调试模式: {cls.DEBUG}")
        logger.info(f"CORS源: {cls.ALLOWED_ORIGINS if cls.ALLOWED_ORIGINS else '所有源（开发模式）'}")
        logger.info(f"数据库: {cls.MYSQL_CONFIG['host']}:{cls.MYSQL_CONFIG['port']}/{cls.MYSQL_CONFIG['database']}")
        logger.info("================")
