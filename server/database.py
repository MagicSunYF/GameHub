import pymysql
from contextlib import contextmanager

class Database:
    def __init__(self, config):
        self.config = config
    
    @contextmanager
    def get_connection(self):
        conn = pymysql.connect(**self.config)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_tables(self, schema):
        with self.get_connection() as conn:
            cur = conn.cursor()
            for table_sql in schema:
                cur.execute(table_sql)
            cur.close()
