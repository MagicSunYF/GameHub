import pymysql
from contextlib import contextmanager
from pymysql.cursors import DictCursor
import logging
import time
from queue import Queue, Empty
import threading

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, config, pool_size=5, max_overflow=10, pool_timeout=30, health_check_interval=60):
        """
        初始化数据库连接池
        
        Args:
            config: 数据库配置字典
            pool_size: 连接池基础大小
            max_overflow: 最大溢出连接数
            pool_timeout: 获取连接超时时间（秒）
            health_check_interval: 健康检查间隔（秒）
        """
        self.config = config
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.health_check_interval = health_check_interval
        
        # 连接池
        self._pool = Queue(maxsize=pool_size + max_overflow)
        self._pool_lock = threading.Lock()
        self._current_size = 0
        self._in_use = set()
        
        # 健康状态
        self._is_healthy = True
        self._last_health_check = 0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        
        # 初始化连接池
        self._initialize_pool()
        
        # 启动健康检查线程
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.info(f"数据库连接池初始化完成: pool_size={pool_size}, max_overflow={max_overflow}")
    
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
                self._current_size += 1
            except Exception as e:
                logger.error(f"初始化连接池失败: {e}")
                self._is_healthy = False
                break
    
    def _create_connection(self):
        """创建新的数据库连接"""
        conn = pymysql.connect(**self.config)
        # 设置连接属性
        conn.ping(reconnect=True)
        return conn
    
    def _get_connection_from_pool(self):
        """从连接池获取连接"""
        try:
            # 尝试从池中获取连接
            conn = self._pool.get(timeout=self.pool_timeout)
            
            # 验证连接是否有效
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception as e:
                logger.warning(f"连接无效，创建新连接: {e}")
                # 连接无效，创建新连接
                with self._pool_lock:
                    self._current_size -= 1
                return self._create_connection()
                
        except Empty:
            # 池中没有可用连接
            with self._pool_lock:
                if self._current_size < self.pool_size + self.max_overflow:
                    # 可以创建新连接
                    conn = self._create_connection()
                    self._current_size += 1
                    return conn
                else:
                    raise Exception("连接池已满，无法获取连接")
    
    def _return_connection_to_pool(self, conn):
        """将连接归还到连接池"""
        try:
            # 检查连接是否有效
            conn.ping(reconnect=True)
            self._pool.put_nowait(conn)
        except Exception as e:
            logger.warning(f"归还连接失败，关闭连接: {e}")
            try:
                conn.close()
            except:
                pass
            with self._pool_lock:
                self._current_size -= 1
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        使用示例:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        if not self._is_healthy:
            raise Exception("数据库连接不健康，操作被拒绝")
        
        conn = None
        try:
            conn = self._get_connection_from_pool()
            self._in_use.add(id(conn))
            yield conn
            conn.commit()
            self._consecutive_failures = 0  # 重置失败计数
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                self._is_healthy = False
                logger.error(f"连续失败{self._consecutive_failures}次，标记数据库为不健康")
            raise e
        finally:
            if conn:
                self._in_use.discard(id(conn))
                self._return_connection_to_pool(conn)
    
    def health_check(self):
        """
        执行健康检查
        
        Returns:
            bool: 数据库是否健康
        """
        try:
            # 临时允许连接以进行健康检查
            was_unhealthy = not self._is_healthy
            if was_unhealthy:
                self._is_healthy = True  # 临时标记为健康以允许连接
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
            
            # 健康检查成功
            if was_unhealthy:
                logger.info("数据库健康检查通过，恢复健康状态")
            self._is_healthy = True
            self._consecutive_failures = 0
            return True
            
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                self._is_healthy = False
            return False
    
    def _health_check_loop(self):
        """健康检查循环（后台线程）"""
        while True:
            try:
                time.sleep(self.health_check_interval)
                current_time = time.time()
                
                # 执行健康检查
                if current_time - self._last_health_check >= self.health_check_interval:
                    self.health_check()
                    self._last_health_check = current_time
                    
            except Exception as e:
                logger.error(f"健康检查循环出错: {e}")
    
    def is_healthy(self):
        """
        检查数据库是否健康
        
        Returns:
            bool: 数据库是否健康
        """
        return self._is_healthy
    
    def get_pool_stats(self):
        """
        获取连接池统计信息
        
        Returns:
            dict: 连接池统计信息
        """
        return {
            'pool_size': self.pool_size,
            'current_size': self._current_size,
            'available': self._pool.qsize(),
            'in_use': len(self._in_use),
            'is_healthy': self._is_healthy,
            'consecutive_failures': self._consecutive_failures
        }
    
    def init_tables(self, schema):
        """
        初始化数据库表
        
        Args:
            schema: SQL语句列表
        """
        if not self._is_healthy:
            logger.warning("数据库不健康，跳过表初始化")
            return
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for table_sql in schema:
                    cursor.execute(table_sql)
                cursor.close()
            logger.info("数据库表初始化成功")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise
    
    def close(self):
        """关闭所有连接池中的连接"""
        logger.info("关闭数据库连接池...")
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass
        logger.info("数据库连接池已关闭")
