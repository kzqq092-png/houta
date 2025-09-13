"""
缓存管理器

实现多层缓存策略和性能优化，包括：
- 内存缓存（LRU）
- 磁盘缓存
- 分布式缓存支持
- 缓存预热和失效策略
- 性能监控和统计

作者: FactorWeave-Quant团队
版本: 1.0
"""

from loguru import logger
import pickle
import hashlib
import asyncio
import threading
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict
import json
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
import weakref

logger = logger


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"           # 内存缓存
    DISK = "disk"              # 磁盘缓存
    DISTRIBUTED = "distributed"  # 分布式缓存


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[timedelta] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > self.ttl

    def update_access(self):
        """更新访问信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """缓存统计信息"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_access_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate


class LRUCache:
    """LRU内存缓存实现"""

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """
        初始化LRU缓存

        Args:
            max_size: 最大条目数
            max_memory_mb: 最大内存使用量(MB)
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.stats.total_requests += 1

            if key not in self.cache:
                self.stats.cache_misses += 1
                return None

            entry = self.cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self.cache[key]
                self.stats.cache_misses += 1
                return None

            # 更新访问信息并移到末尾（最近使用）
            entry.update_access()
            self.cache.move_to_end(key)

            self.stats.cache_hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            # 计算值的大小
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = 1024  # 默认大小

            # 检查内存限制
            if size_bytes > self.max_memory_bytes:
                logger.warning(f"缓存值过大，无法存储: {size_bytes} bytes")
                return False

            # 如果key已存在，更新
            if key in self.cache:
                old_entry = self.cache[key]
                self.stats.total_size_bytes -= old_entry.size_bytes
                del self.cache[key]

            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl=ttl,
                size_bytes=size_bytes
            )

            # 确保有足够空间
            while (len(self.cache) >= self.max_size or
                   self.stats.total_size_bytes + size_bytes > self.max_memory_bytes):
                if not self.cache:
                    break
                self._evict_lru()

            # 添加新条目
            self.cache[key] = entry
            self.stats.total_size_bytes += size_bytes

            return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                self.stats.total_size_bytes -= entry.size_bytes
                del self.cache[key]
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.stats.total_size_bytes = 0

    def _evict_lru(self):
        """淘汰最近最少使用的条目"""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.evictions += 1

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        with self.lock:
            return CacheStats(
                total_requests=self.stats.total_requests,
                cache_hits=self.stats.cache_hits,
                cache_misses=self.stats.cache_misses,
                evictions=self.stats.evictions,
                total_size_bytes=self.stats.total_size_bytes
            )


class DiskCache:
    """磁盘缓存实现"""

    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 1000):
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大磁盘使用量(MB)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.db_path = self.cache_dir / "cache_metadata.db"
        self.lock = threading.RLock()
        self.stats = CacheStats()

        self._init_database()

    def _init_database(self):
        """初始化元数据数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    ttl_seconds INTEGER,
                    size_bytes INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache_entries(last_accessed)
            """)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.stats.total_requests += 1

            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT file_path, created_at, ttl_seconds, access_count
                        FROM cache_entries WHERE key = ?
                    """, (key,))

                    row = cursor.fetchone()
                    if not row:
                        self.stats.cache_misses += 1
                        return None

                    file_path, created_at_str, ttl_seconds, access_count = row

                    # 检查是否过期
                    created_at = datetime.fromisoformat(created_at_str)
                    if ttl_seconds and (datetime.now() - created_at).total_seconds() > ttl_seconds:
                        self._delete_entry(key, file_path)
                        self.stats.cache_misses += 1
                        return None

                    # 检查文件是否存在
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        self._delete_entry(key)
                        self.stats.cache_misses += 1
                        return None

                    # 读取文件内容
                    with open(file_path_obj, 'rb') as f:
                        value = pickle.load(f)

                    # 更新访问信息
                    cursor.execute("""
                        UPDATE cache_entries 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE key = ?
                    """, (datetime.now().isoformat(), key))

                    self.stats.cache_hits += 1
                    return value

            except Exception as e:
                logger.error(f"磁盘缓存读取失败: {e}")
                self.stats.cache_misses += 1
                return None

    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            try:
                # 生成文件路径
                key_hash = hashlib.md5(key.encode()).hexdigest()
                file_path = self.cache_dir / f"{key_hash}.cache"

                # 序列化并写入文件
                with open(file_path, 'wb') as f:
                    pickle.dump(value, f)

                file_size = file_path.stat().st_size

                # 检查磁盘空间限制
                if file_size > self.max_size_bytes:
                    file_path.unlink()
                    logger.warning(f"缓存文件过大，无法存储: {file_size} bytes")
                    return False

                # 确保有足够空间
                self._ensure_space(file_size)

                # 更新元数据
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # 删除旧条目（如果存在）
                    cursor.execute("SELECT file_path FROM cache_entries WHERE key = ?", (key,))
                    old_row = cursor.fetchone()
                    if old_row:
                        old_file_path = Path(old_row[0])
                        if old_file_path.exists():
                            old_file_path.unlink()

                    # 插入新条目
                    cursor.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (key, file_path, created_at, last_accessed, ttl_seconds, size_bytes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        key,
                        str(file_path),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        ttl.total_seconds() if ttl and hasattr(ttl, 'total_seconds') else (ttl if isinstance(ttl, (int, float)) else None),
                        file_size
                    ))

                self.stats.total_size_bytes += file_size
                return True

            except Exception as e:
                logger.error(f"磁盘缓存写入失败: {e}")
                return False

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT file_path FROM cache_entries WHERE key = ?", (key,))
                    row = cursor.fetchone()

                    if row:
                        file_path = Path(row[0])
                        if file_path.exists():
                            file_path.unlink()

                        cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                        return True

                return False

            except Exception as e:
                logger.error(f"磁盘缓存删除失败: {e}")
                return False

    def _delete_entry(self, key: str, file_path: Optional[str] = None):
        """删除缓存条目（内部方法）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if not file_path:
                    cursor.execute("SELECT file_path FROM cache_entries WHERE key = ?", (key,))
                    row = cursor.fetchone()
                    if row:
                        file_path = row[0]

                if file_path:
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        file_path_obj.unlink()

                cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))

        except Exception as e:
            logger.error(f"删除缓存条目失败: {e}")

    def _ensure_space(self, required_bytes: int):
        """确保有足够的磁盘空间"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 获取当前总大小
                cursor.execute("SELECT SUM(size_bytes) FROM cache_entries")
                current_size = cursor.fetchone()[0] or 0

                # 如果需要清理空间
                while current_size + required_bytes > self.max_size_bytes:
                    # 删除最旧的条目
                    cursor.execute("""
                        SELECT key, file_path, size_bytes FROM cache_entries 
                        ORDER BY last_accessed ASC LIMIT 1
                    """)
                    row = cursor.fetchone()

                    if not row:
                        break

                    key, file_path, size_bytes = row
                    self._delete_entry(key, file_path)
                    current_size -= size_bytes
                    self.stats.evictions += 1

        except Exception as e:
            logger.error(f"清理磁盘空间失败: {e}")

    def clear(self):
        """清空缓存"""
        with self.lock:
            try:
                # 删除所有缓存文件
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()

                # 清空数据库
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM cache_entries")

                self.stats.total_size_bytes = 0

            except Exception as e:
                logger.error(f"清空磁盘缓存失败: {e}")

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache_entries")
                    count, total_size = cursor.fetchone()

                    return CacheStats(
                        total_requests=self.stats.total_requests,
                        cache_hits=self.stats.cache_hits,
                        cache_misses=self.stats.cache_misses,
                        evictions=self.stats.evictions,
                        total_size_bytes=total_size or 0
                    )

            except Exception as e:
                logger.error(f"获取磁盘缓存统计失败: {e}")
                return self.stats

    def close(self):
        """关闭缓存，清理资源"""
        with self.lock:
            try:
                # 强制关闭所有可能的数据库连接
                import gc
                gc.collect()  # 强制垃圾回收，释放数据库连接

                # 等待一小段时间确保连接被释放
                import time
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"关闭磁盘缓存失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class MultiLevelCacheManager:
    """多级缓存管理器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化多级缓存管理器

        Args:
            config: 缓存配置
        """
        self.config = config
        self.logger = logger

        # 初始化各级缓存
        self.memory_cache = None
        self.disk_cache = None

        # 缓存策略配置
        self.cache_levels = config.get('levels', [CacheLevel.MEMORY])
        self.default_ttl = timedelta(minutes=config.get('default_ttl_minutes', 30))

        # 性能监控
        self.total_stats = CacheStats()

        self._initialize_caches()

    def _initialize_caches(self):
        """初始化缓存"""
        try:
            if CacheLevel.MEMORY in self.cache_levels:
                memory_config = self.config.get('memory', {})
                self.memory_cache = LRUCache(
                    max_size=memory_config.get('max_size', 1000),
                    max_memory_mb=memory_config.get('max_memory_mb', 100)
                )
                self.logger.info("内存缓存初始化完成")

            if CacheLevel.DISK in self.cache_levels:
                disk_config = self.config.get('disk', {})
                self.disk_cache = DiskCache(
                    cache_dir=disk_config.get('cache_dir', 'cache'),
                    max_size_mb=disk_config.get('max_size_mb', 1000)
                )
                self.logger.info("磁盘缓存初始化完成")

        except Exception as e:
            self.logger.error(f"缓存初始化失败: {e}")
            raise

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（多级查找）

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        start_time = datetime.now()

        try:
            self.total_stats.total_requests += 1

            # L1: 内存缓存
            if self.memory_cache:
                value = self.memory_cache.get(key)
                if value is not None:
                    self.total_stats.cache_hits += 1
                    self._update_access_time(start_time)
                    return value

            # L2: 磁盘缓存
            if self.disk_cache:
                value = self.disk_cache.get(key)
                if value is not None:
                    # 回填到内存缓存
                    if self.memory_cache:
                        self.memory_cache.put(key, value, self.default_ttl)

                    self.total_stats.cache_hits += 1
                    self._update_access_time(start_time)
                    return value

            # 缓存未命中
            self.total_stats.cache_misses += 1
            self._update_access_time(start_time)
            return None

        except Exception as e:
            self.logger.error(f"缓存获取失败: {e}")
            self.total_stats.cache_misses += 1
            return None

    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        设置缓存值（多级存储）

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间

        Returns:
            是否成功
        """
        if ttl is None:
            ttl = self.default_ttl

        success = True

        try:
            # 存储到内存缓存
            if self.memory_cache:
                if not self.memory_cache.put(key, value, ttl):
                    success = False

            # 存储到磁盘缓存
            if self.disk_cache:
                if not self.disk_cache.put(key, value, ttl):
                    success = False

            return success

        except Exception as e:
            self.logger.error(f"缓存设置失败: {e}")
            return False

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        设置缓存值（put方法的别名，保持向后兼容性）
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间
            
        Returns:
            是否成功
        """
        return self.put(key, value, ttl)

    def delete(self, key: str) -> bool:
        """
        删除缓存值（所有级别）

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        success = True

        try:
            if self.memory_cache:
                if not self.memory_cache.delete(key):
                    success = False

            if self.disk_cache:
                if not self.disk_cache.delete(key):
                    success = False

            return success

        except Exception as e:
            self.logger.error(f"缓存删除失败: {e}")
            return False

    def clear(self):
        """清空所有缓存"""
        try:
            if self.memory_cache:
                self.memory_cache.clear()

            if self.disk_cache:
                self.disk_cache.clear()

            self.logger.info("所有缓存已清空")

        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")

    def get_cache_key(self, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键
        """
        try:
            # 创建一个包含所有参数的字符串
            key_parts = []

            # 添加位置参数
            for arg in args:
                if hasattr(arg, '__dict__'):
                    # 对象类型，使用其字符串表示
                    key_parts.append(str(arg))
                else:
                    key_parts.append(str(arg))

            # 添加关键字参数
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")

            # 生成哈希
            key_string = "|".join(key_parts)
            return hashlib.md5(key_string.encode()).hexdigest()

        except Exception as e:
            self.logger.error(f"生成缓存键失败: {e}")
            return hashlib.md5(str(datetime.now()).encode()).hexdigest()

    def _update_access_time(self, start_time: datetime):
        """更新访问时间统计"""
        access_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # 更新平均访问时间
        total_requests = self.total_stats.total_requests
        current_avg = self.total_stats.avg_access_time_ms
        self.total_stats.avg_access_time_ms = (
            (current_avg * (total_requests - 1) + access_time_ms) / total_requests
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                'total': self.total_stats,
                'levels': {}
            }

            if self.memory_cache:
                stats['levels']['memory'] = self.memory_cache.get_stats()

            if self.disk_cache:
                stats['levels']['disk'] = self.disk_cache.get_stats()

            return stats

        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {e}")
            return {'error': str(e)}


def cache_result(ttl_minutes: int = 30, cache_manager: Optional[MultiLevelCacheManager] = None):
    """
    缓存装饰器

    Args:
        ttl_minutes: 缓存生存时间（分钟）
        cache_manager: 缓存管理器实例

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 如果没有提供缓存管理器，跳过缓存
            if cache_manager is None:
                return func(*args, **kwargs)

            # 生成缓存键
            cache_key = f"{func.__name__}:{cache_manager.get_cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_manager.put(cache_key, result, timedelta(minutes=ttl_minutes))

            return result

        return wrapper
    return decorator
