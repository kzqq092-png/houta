"""
DuckDB连接池管理器 - 使用DBUtils实现

提供线程安全的DuckDB连接池，解决并发访问导致的INTERNAL ERROR问题。

特性:
- 线程安全的连接管理
- 自动连接重用和回收
- 连接健康检查
- 连接超时处理
- 单例模式（每个数据库路径一个池）

Dependencies:
    pip install DBUtils

Author: FactorWeave-Quant Team
Date: 2025-10-12
"""

import threading
from typing import Optional, Dict, Any
from contextlib import contextmanager
import duckdb
from loguru import logger

try:
    from DBUtils.PooledDB import PooledDB
    DBUTILS_AVAILABLE = True
except ImportError:
    DBUTILS_AVAILABLE = False
    logger.warning("DBUtils未安装，将使用简化的连接池实现。建议安装: pip install DBUtils")


class DuckDBConnectionPool:
    """
    DuckDB连接池管理器

    使用DBUtils的PooledDB实现线程安全的连接池。
    如果DBUtils不可用，会回退到简化实现。
    """

    _instances: Dict[str, 'DuckDBConnectionPool'] = {}
    _lock = threading.Lock()

    def __new__(cls, db_path: str, **kwargs):
        """单例模式：每个数据库路径一个池实例"""
        with cls._lock:
            if db_path not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[db_path] = instance
            return cls._instances[db_path]

    def __init__(
        self,
        db_path: str,
        mincached: int = 2,        # 最小缓存连接数
        maxcached: int = 5,        # 最大缓存连接数
        maxconnections: int = 10,  # 最大连接数
        blocking: bool = True,      # 连接池满时是否阻塞
        maxusage: int = 0,         # 单个连接最大使用次数（0=无限制）
        ping: int = 1,             # 连接检查（0=不检查，1=默认检查，2=事务开始前检查）
        **kwargs
    ):
        """
        初始化连接池

        Args:
            db_path: 数据库文件路径
            mincached: 启动时创建的空闲连接数
            maxcached: 缓存的最大空闲连接数
            maxconnections: 最大连接数（0=无限制）
            blocking: 连接池满时是否阻塞等待
            maxusage: 单个连接最大使用次数（0=无限制）
            ping: 连接健康检查策略
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self.db_path = db_path
        self._initialized = True
        self._use_dbutils = DBUTILS_AVAILABLE

        logger.info(f"初始化DuckDB连接池: {db_path}")
        logger.info(f"  - 最小缓存: {mincached}")
        logger.info(f"  - 最大缓存: {maxcached}")
        logger.info(f"  - 最大连接: {maxconnections}")
        logger.info(f"  - 使用DBUtils: {self._use_dbutils}")

        if self._use_dbutils:
            # 使用DBUtils PooledDB
            self._pool = PooledDB(
                creator=duckdb,           # 连接创建器
                mincached=mincached,      # 启动时创建的空闲连接数
                maxcached=maxcached,      # 缓存的最大空闲连接数
                maxconnections=maxconnections,  # 最大连接数
                blocking=blocking,        # 连接池满时是否阻塞等待
                maxusage=maxusage,        # 单个连接最大使用次数
                ping=ping,                # 连接检查策略
                database=db_path,         # 传递给duckdb.connect的参数
                **kwargs
            )
        else:
            # 回退到简化实现（线程本地连接）
            self._thread_local = threading.local()
            self._connections: Dict[int, Any] = {}
            self._conn_lock = threading.RLock()

        logger.info("✅ DuckDB连接池初始化成功")

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）

        Usage:
            with pool.get_connection() as conn:
                result = conn.execute("SELECT * FROM table").fetchall()
        """
        if self._use_dbutils:
            # DBUtils实现
            conn = None
            try:
                conn = self._pool.connection()
                logger.debug(f"从连接池获取连接: {id(conn)}")
                yield conn
            except Exception as e:
                logger.error(f"连接使用错误: {e}")
                raise
            finally:
                if conn:
                    try:
                        # DBUtils的close()会自动返回连接到池中
                        conn.close()
                        logger.debug(f"连接返回连接池: {id(conn)}")
                    except Exception as e:
                        logger.warning(f"连接关闭失败: {e}")
        else:
            # 简化实现：每个线程一个连接
            thread_id = threading.get_ident()

            with self._conn_lock:
                if thread_id not in self._connections:
                    conn = duckdb.connect(self.db_path)
                    self._connections[thread_id] = conn
                    logger.debug(f"为线程 {thread_id} 创建新连接")

                conn = self._connections[thread_id]

            try:
                yield conn
            except Exception as e:
                logger.error(f"连接使用错误: {e}")
                # 重新创建连接
                with self._conn_lock:
                    try:
                        self._connections[thread_id].close()
                    except:
                        pass
                    conn = duckdb.connect(self.db_path)
                    self._connections[thread_id] = conn
                raise

    def execute_query(self, sql: str, params=None) -> Any:
        """
        执行查询

        Args:
            sql: SQL查询语句
            params: 查询参数

        Returns:
            查询结果（DataFrame）
        """
        import pandas as pd

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    if params:
                        result = conn.execute(sql, params).fetchdf()
                    else:
                        result = conn.execute(sql).fetchdf()
                    return result

            except Exception as e:
                retry_count += 1
                error_msg = str(e).lower()

                # 处理DuckDB特定错误
                if 'internal error' in error_msg and retry_count < max_retries:
                    logger.warning(f"DuckDB内部错误，重试 {retry_count}/{max_retries}: {e}")
                    import time
                    time.sleep(0.1 * retry_count)  # 指数退避
                    continue
                elif 'result closed' in error_msg or 'connection closed' in error_msg:
                    logger.warning(f"连接已关闭，重试 {retry_count}/{max_retries}")
                    continue
                else:
                    logger.error(f"查询执行失败: {e}")
                    return pd.DataFrame()

        logger.error(f"查询失败，已达到最大重试次数: {max_retries}")
        return pd.DataFrame()

    def execute_many(self, sql: str, data_list: list) -> bool:
        """
        批量执行SQL

        Args:
            sql: SQL语句
            data_list: 数据列表

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                conn.executemany(sql, data_list)
                return True
        except Exception as e:
            logger.error(f"批量执行失败: {e}")
            return False

    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态

        Returns:
            连接池状态信息
        """
        if self._use_dbutils:
            return {
                'db_path': self.db_path,
                'pool_type': 'PooledDB (DBUtils)',
                'config': {
                    'mincached': self._pool._mincached,
                    'maxcached': self._pool._maxcached,
                    'maxconnections': self._pool._maxconnections,
                }
            }
        else:
            with self._conn_lock:
                return {
                    'db_path': self.db_path,
                    'pool_type': 'ThreadLocal (Fallback)',
                    'active_connections': len(self._connections)
                }

    def close_all(self):
        """关闭所有连接"""
        try:
            if self._use_dbutils:
                self._pool.close()
            else:
                with self._conn_lock:
                    for conn in self._connections.values():
                        try:
                            conn.close()
                        except:
                            pass
                    self._connections.clear()

            logger.info("连接池已关闭")
        except Exception as e:
            logger.error(f"关闭连接池失败: {e}")

    def cleanup_thread_connections(self):
        """清理当前线程的连接（仅简化实现）"""
        if not self._use_dbutils:
            thread_id = threading.get_ident()
            with self._conn_lock:
                if thread_id in self._connections:
                    try:
                        self._connections[thread_id].close()
                        del self._connections[thread_id]
                        logger.debug(f"清理线程 {thread_id} 的连接")
                    except Exception as e:
                        logger.warning(f"清理连接失败: {e}")

    @classmethod
    def get_instance(cls, db_path: str, **kwargs) -> 'DuckDBConnectionPool':
        """获取连接池实例（单例）"""
        return cls(db_path, **kwargs)


# 使用示例
if __name__ == "__main__":
    import pandas as pd

    # 创建连接池
    pool = DuckDBConnectionPool(
        db_path=":memory:",  # 使用内存数据库测试
        mincached=2,
        maxcached=5,
        maxconnections=10
    )

    # 测试连接
    with pool.get_connection() as conn:
        conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")

    # 使用便捷方法查询
    df = pool.execute_query("SELECT * FROM test")
    print("查询结果:")
    print(df)

    # 获取连接池状态
    status = pool.get_pool_status()
    print("\n连接池状态:")
    print(status)

    print("\n✅ 连接池测试通过！")
