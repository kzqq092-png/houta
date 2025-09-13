from loguru import logger
"""
DuckDB连接管理器

提供DuckDB数据库连接的统一管理，包括：
- 连接池管理
- 数据库初始化
- 性能配置应用
- 连接健康检查
- 异常处理和重连机制

作者: FactorWeave-Quant团队
版本: 1.0
"""

import duckdb
import threading
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager
from queue import Queue, Empty
import json
import os

logger = logger


@dataclass
class DuckDBConfig:
    """DuckDB配置参数"""
    memory_limit: str = '8GB'
    threads: str = 'auto'
    max_memory: str = '6GB'  # 修改为绝对单位，避免百分比解析错误
    checkpoint_threshold: str = '16MB'
    enable_progress_bar: bool = True
    enable_profiling: bool = True
    preserve_insertion_order: bool = False
    enable_external_access: bool = True
    enable_fsst_vectors: bool = True  # 启用FSST字符串压缩
    compression: str = 'zstd'        # 使用ZSTD压缩

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'memory_limit': self.memory_limit,
            'threads': self.threads,
            'max_memory': self.max_memory,
            'checkpoint_threshold': self.checkpoint_threshold,
            'enable_progress_bar': self.enable_progress_bar,
            'enable_profiling': self.enable_profiling,
            'preserve_insertion_order': self.preserve_insertion_order,
            'enable_external_access': self.enable_external_access,
            'enable_fsst_vectors': self.enable_fsst_vectors,
            'compression': self.compression
        }


@dataclass
class ConnectionInfo:
    """连接信息"""
    connection_id: str
    database_path: str
    created_at: float
    last_used_at: float
    is_active: bool
    query_count: int = 0
    error_count: int = 0


class DuckDBConnectionPool:
    """DuckDB连接池"""

    def __init__(self, database_path: str, pool_size: int = 10, config: DuckDBConfig = None):
        """
        初始化连接池

        Args:
            database_path: 数据库文件路径
            pool_size: 连接池大小
            config: DuckDB配置
        """
        self.database_path = database_path
        self.pool_size = pool_size
        self.config = config or DuckDBConfig()

        # 连接池
        self._pool = Queue(maxsize=pool_size)
        self._all_connections: Dict[str, duckdb.DuckDBPyConnection] = {}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        self._conn_id_mapping: Dict[int, str] = {}  # 连接对象ID到连接ID的映射

        # 线程锁
        self._lock = threading.RLock()

        # 统计信息
        self._total_connections = 0
        self._active_connections = 0

        # 初始化连接池
        self._initialize_pool()

        logger.info(f"DuckDB连接池初始化完成: {database_path}, 池大小: {pool_size}")

    def _initialize_pool(self):
        """初始化连接池"""
        try:
            # 确保数据库目录存在
            db_dir = Path(self.database_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # 创建初始连接
            for i in range(self.pool_size):
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn)

        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise

    def _create_connection(self) -> Optional[duckdb.DuckDBPyConnection]:
        """创建新的数据库连接"""
        try:
            # 创建连接
            conn = duckdb.connect(self.database_path)

            # 生成连接ID
            conn_id = f"conn_{self._total_connections}_{int(time.time())}"

            # 应用配置
            self._apply_config(conn)

            # 记录连接信息
            with self._lock:
                self._all_connections[conn_id] = conn
                self._connection_info[conn_id] = ConnectionInfo(
                    connection_id=conn_id,
                    database_path=self.database_path,
                    created_at=time.time(),
                    last_used_at=time.time(),
                    is_active=True
                )
                self._total_connections += 1
                self._active_connections += 1

            # 使用字典来存储连接ID映射，而不是直接设置属性
            if not hasattr(self, '_conn_id_mapping'):
                self._conn_id_mapping = {}
            self._conn_id_mapping[id(conn)] = conn_id

            logger.debug(f"创建DuckDB连接: {conn_id}")
            return conn

        except Exception as e:
            logger.error(f"创建DuckDB连接失败: {e}")
            return None

    def _apply_config(self, conn: duckdb.DuckDBPyConnection):
        """应用配置到连接"""
        try:
            config_dict = self.config.to_dict()

            # 设置内存限制
            conn.execute(f"SET memory_limit='{config_dict['memory_limit']}'")

            # 设置线程数
            if config_dict['threads'] != 'auto':
                conn.execute(f"SET threads={config_dict['threads']}")

            # 设置最大内存使用
            conn.execute(f"SET max_memory='{config_dict['max_memory']}'")

            # 设置检查点阈值
            conn.execute(f"SET checkpoint_threshold='{config_dict['checkpoint_threshold']}'")

            # 启用进度条
            if config_dict['enable_progress_bar']:
                conn.execute("SET enable_progress_bar=1")

            # 启用性能分析
            if config_dict['enable_profiling']:
                conn.execute("SET enable_profiling='json'")

            # 设置插入顺序保持
            conn.execute(f"SET preserve_insertion_order={str(config_dict['preserve_insertion_order']).lower()}")

            # 启用外部访问（注意：此设置不能在数据库运行时更改）
            # if config_dict['enable_external_access']:
            #     conn.execute("SET enable_external_access=true")

            # 启用FSST字符串压缩
            if config_dict['enable_fsst_vectors']:
                conn.execute("SET enable_fsst_vectors=true")

            # 设置默认压缩（DuckDB不支持default_compression参数）
            # conn.execute(f"SET default_compression='{config_dict['compression']}'")

            logger.debug("DuckDB配置应用完成")

        except Exception as e:
            logger.warning(f"应用DuckDB配置失败: {e}")

    @contextmanager
    def get_connection(self):
        """获取连接（上下文管理器）"""
        conn = None
        try:
            # 从池中获取连接
            try:
                conn = self._pool.get(timeout=30)  # 30秒超时
            except Empty:
                logger.warning("连接池已满，创建临时连接")
                conn = self._create_connection()
                if not conn:
                    raise Exception("无法创建数据库连接")

            # 更新连接信息
            if hasattr(self, '_conn_id_mapping') and id(conn) in self._conn_id_mapping:
                conn_id = self._conn_id_mapping[id(conn)]
                with self._lock:
                    if conn_id in self._connection_info:
                        self._connection_info[conn_id].last_used_at = time.time()
                        self._connection_info[conn_id].query_count += 1

            yield conn

        except Exception as e:
            # 记录错误
            if conn and hasattr(self, '_conn_id_mapping') and id(conn) in self._conn_id_mapping:
                conn_id = self._conn_id_mapping[id(conn)]
                with self._lock:
                    if conn_id in self._connection_info:
                        self._connection_info[conn_id].error_count += 1
            logger.error(f"数据库连接使用错误: {e}")
            raise

        finally:
            # 归还连接到池中
            if conn:
                try:
                    # 检查连接是否仍然有效
                    if self._is_connection_valid(conn):
                        self._pool.put(conn)
                    else:
                        # 连接无效，创建新连接替换
                        logger.warning("连接无效，创建新连接替换")
                        new_conn = self._create_connection()
                        if new_conn:
                            self._pool.put(new_conn)
                except Exception as e:
                    logger.error(f"归还连接到池中失败: {e}")

    def _is_connection_valid(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """检查连接是否有效"""
        try:
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            with self.get_connection() as conn:
                # 执行简单查询测试
                result = conn.execute("SELECT 1 as test").fetchone()

                # 获取数据库信息
                db_info = conn.execute("PRAGMA database_list").fetchall()

                # 统计信息
                with self._lock:
                    stats = {
                        'status': 'healthy',
                        'database_path': self.database_path,
                        'pool_size': self.pool_size,
                        'total_connections': self._total_connections,
                        'active_connections': self._active_connections,
                        'available_connections': self._pool.qsize(),
                        'database_info': db_info,
                        'test_query_result': result,
                        'config': self.config.to_dict()
                    }

                return stats

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database_path': self.database_path
            }

    def get_connection_stats(self) -> List[Dict[str, Any]]:
        """获取连接统计信息"""
        with self._lock:
            return [
                {
                    'connection_id': info.connection_id,
                    'database_path': info.database_path,
                    'created_at': info.created_at,
                    'last_used_at': info.last_used_at,
                    'is_active': info.is_active,
                    'query_count': info.query_count,
                    'error_count': info.error_count,
                    'uptime_seconds': time.time() - info.created_at
                }
                for info in self._connection_info.values()
            ]

    def close_all_connections(self):
        """关闭所有连接"""
        try:
            with self._lock:
                # 关闭池中的连接
                while not self._pool.empty():
                    try:
                        conn = self._pool.get_nowait()
                        conn.close()
                    except Empty:
                        break
                    except Exception as e:
                        logger.error(f"关闭连接失败: {e}")

                # 关闭所有记录的连接
                for conn_id, conn in self._all_connections.items():
                    try:
                        conn.close()
                        self._connection_info[conn_id].is_active = False
                    except Exception as e:
                        logger.error(f"关闭连接 {conn_id} 失败: {e}")

                self._active_connections = 0

            logger.info("所有DuckDB连接已关闭")

        except Exception as e:
            logger.error(f"关闭连接时出错: {e}")


class DuckDBConnectionManager:
    """DuckDB连接管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化连接管理器

        Args:
            config_file: 配置文件路径
        """
        self._pools: Dict[str, DuckDBConnectionPool] = {}
        self._lock = threading.RLock()
        self._config_file = config_file
        self._default_config = DuckDBConfig()

        # 加载配置
        if config_file and Path(config_file).exists():
            self._load_config()

        logger.info("DuckDB连接管理器初始化完成")

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 更新默认配置
            if 'duckdb' in config_data:
                duckdb_config = config_data['duckdb']
                for key, value in duckdb_config.items():
                    if hasattr(self._default_config, key):
                        setattr(self._default_config, key, value)

            logger.info(f"配置文件加载完成: {self._config_file}")

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")

    def get_pool(self, database_path: str, pool_size: int = 10,
                 config: Optional[DuckDBConfig] = None) -> DuckDBConnectionPool:
        """
        获取或创建连接池

        Args:
            database_path: 数据库文件路径
            pool_size: 连接池大小
            config: DuckDB配置

        Returns:
            DuckDB连接池
        """
        # 标准化路径
        database_path = str(Path(database_path).resolve())

        with self._lock:
            if database_path not in self._pools:
                # 使用提供的配置或默认配置
                pool_config = config or self._default_config

                # 创建新的连接池
                pool = DuckDBConnectionPool(
                    database_path=database_path,
                    pool_size=pool_size,
                    config=pool_config
                )

                self._pools[database_path] = pool
                logger.info(f"创建新的连接池: {database_path}")

            return self._pools[database_path]

    @contextmanager
    def get_connection(self, database_path: str, pool_size: int = 10,
                       config: Optional[DuckDBConfig] = None):
        """
        获取数据库连接

        Args:
            database_path: 数据库文件路径
            pool_size: 连接池大小
            config: DuckDB配置
        """
        pool = self.get_pool(database_path, pool_size, config)
        with pool.get_connection() as conn:
            yield conn

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """检查所有连接池的健康状态"""
        results = {}

        with self._lock:
            for db_path, pool in self._pools.items():
                try:
                    results[db_path] = pool.health_check()
                except Exception as e:
                    results[db_path] = {
                        'status': 'error',
                        'error': str(e)
                    }

        return results

    def get_all_stats(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有连接池的统计信息"""
        results = {}

        with self._lock:
            for db_path, pool in self._pools.items():
                try:
                    results[db_path] = pool.get_connection_stats()
                except Exception as e:
                    logger.error(f"获取连接池统计信息失败 {db_path}: {e}")
                    results[db_path] = []

        return results

    def close_all_pools(self):
        """关闭所有连接池"""
        with self._lock:
            for db_path, pool in self._pools.items():
                try:
                    pool.close_all_connections()
                    logger.info(f"连接池已关闭: {db_path}")
                except Exception as e:
                    logger.error(f"关闭连接池失败 {db_path}: {e}")

            self._pools.clear()

        logger.info("所有DuckDB连接池已关闭")

    def remove_pool(self, database_path: str):
        """移除指定的连接池"""
        database_path = str(Path(database_path).resolve())

        with self._lock:
            if database_path in self._pools:
                try:
                    self._pools[database_path].close_all_connections()
                    del self._pools[database_path]
                    logger.info(f"连接池已移除: {database_path}")
                except Exception as e:
                    logger.error(f"移除连接池失败 {database_path}: {e}")


# 全局连接管理器实例
_connection_manager: Optional[DuckDBConnectionManager] = None
_manager_lock = threading.Lock()


def get_connection_manager(config_file: Optional[str] = None) -> DuckDBConnectionManager:
    """获取全局连接管理器实例"""
    global _connection_manager

    with _manager_lock:
        if _connection_manager is None:
            _connection_manager = DuckDBConnectionManager(config_file)

        return _connection_manager


def initialize_duckdb_manager(config_file: Optional[str] = None) -> DuckDBConnectionManager:
    """初始化DuckDB连接管理器"""
    global _connection_manager

    with _manager_lock:
        if _connection_manager is not None:
            _connection_manager.close_all_pools()

        _connection_manager = DuckDBConnectionManager(config_file)
        logger.info("DuckDB连接管理器已初始化")

        return _connection_manager


def cleanup_duckdb_manager():
    """清理DuckDB连接管理器"""
    global _connection_manager

    with _manager_lock:
        if _connection_manager is not None:
            _connection_manager.close_all_pools()
            _connection_manager = None
            logger.info("DuckDB连接管理器已清理")
