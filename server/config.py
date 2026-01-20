import os
import sys

class Config:
    # 验证必需的环境变量
    @staticmethod
    def _get_required_env(key, error_msg):
        value = os.getenv(key)
        if not value:
            print(f"错误: {error_msg}")
            sys.exit(1)
        return value
    
    # 数据库配置
    MYSQL_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': _get_required_env.__func__('DB_PASSWORD', '必须设置 DB_PASSWORD 环境变量'),
        'database': os.getenv('DB_NAME', 'gomoku'),
        'charset': 'utf8mb4',
    }
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # CORS 配置
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else []
