"""
多层缓存管理模块

实现多级缓存架构，支持TTL、事件驱动和版本缓存等高级功能。
设计目标：提供高性能、高可用的数据缓存解决方案。

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import threading
from loguru import logger
import hashlib
import pickle
import gzip
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
import pandas as pd
import weakref

# 导入项目模块
from .plugin_types import AssetType, DataType

logger = logger


class CacheLevel(Enum):
    """缓存级别枚举"""
    L1_MEMORY = "l1_memory"          # L1内存缓存（最快）
    L2_MEMORY = "l2_memory"          # L2内存缓存（较快）
    L3_DISK = "l3_disk"              # L3磁盘缓存（持久化）
    L4_REMOTE = "l4_remote"          # L4远程缓存（如Redis）


class CachePolicy(Enum):
    """缓存策略枚举"""
    LRU = "lru"                      # 最近最少使用
    LFU = "lfu"                      # 最少使用频率
    FIFO = "fifo"                    # 先进先出
    TTL = "ttl"                      # 基于时间过期
    ADAPTIVE = "adaptive"            # 自适应策略


class InvalidationStrategy(Enum):
    """失效策略枚举"""
    TTL_BASED = "ttl_based"          # 基于TTL
    EVENT_DRIVEN = "event_driven"    # 事件驱动
    VERSION_BASED = "version_based"  # 版本控制
    MANUAL = "manual"                # 手动失效


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_time: datetime
    access_time: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    version: str = "1.0"
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.ttl_seconds is None:
            return False

        elapsed = (datetime.now() - self.created_time).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """获取条目年龄（秒）"""
        return (datetime.now() - self.created_time).total_seconds()


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_ratio(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ICacheLayer(ABC):
    """缓存层接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """存储缓存值"""
        pass

    @abstractmethod
    def remove(self, key: str) -> bool:
        """移除缓存值"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        pass


class L1MemoryCache(ICacheLayer):
    """L1内存缓存 - 最快速的缓存层"""

    def __init__(self,
                 max_size: int = 1000,
                 default_ttl: int = 300,
                 policy: CachePolicy = CachePolicy.LRU):
        """
        初始化L1内存缓存

        Args:
            max_size: 最大条目数
            default_ttl: 默认TTL（秒）
            policy: 缓存策略
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.policy = policy

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._access_frequency: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        self._stats = CacheStats()

        logger.info(f"L1MemoryCache初始化，容量: {max_size}, TTL: {default_ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired:
                del self._cache[key]
                if key in self._access_frequency:
                    del self._access_frequency[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            # 更新访问信息
            entry.access_time = datetime.now()
            entry.access_count += 1
            self._access_frequency[key] += 1

            # LRU策略：移到末尾
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            self._stats.hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """存储缓存值"""
        try:
            with self._lock:
                # 计算值的大小
                size_bytes = self._calculate_size(value)

                # 如果key已存在，更新
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._stats.size_bytes -= old_entry.size_bytes

                # 创建新条目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_time=datetime.now(),
                    access_time=datetime.now(),
                    ttl_seconds=ttl_seconds or self.default_ttl,
                    size_bytes=size_bytes
                )

                # 检查是否需要淘汰
                while len(self._cache) >= self.max_size and key not in self._cache:
                    self._evict_one()

                # 存储条目
                self._cache[key] = entry
                self._stats.size_bytes += size_bytes
                self._stats.entry_count = len(self._cache)

                logger.debug(f"L1缓存存储: {key}, 大小: {size_bytes}字节")
                return True

        except Exception as e:
            logger.error(f"L1缓存存储失败: {str(e)}")
            return False

    def remove(self, key: str) -> bool:
        """移除缓存值"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.size_bytes -= entry.size_bytes
                del self._cache[key]
                if key in self._access_frequency:
                    del self._access_frequency[key]
                self._stats.entry_count = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_frequency.clear()
            self._stats = CacheStats()
            logger.info("L1缓存已清空")

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        with self._lock:
            self._stats.entry_count = len(self._cache)
            return self._stats

    def _evict_one(self) -> None:
        """淘汰一个条目"""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # 淘汰最久未使用的
            key, entry = self._cache.popitem(last=False)
        elif self.policy == CachePolicy.LFU:
            # 淘汰访问频率最低的
            min_freq_key = min(self._access_frequency, key=self._access_frequency.get)
            entry = self._cache.pop(min_freq_key)
            del self._access_frequency[min_freq_key]
            key = min_freq_key
        elif self.policy == CachePolicy.FIFO:
            # 淘汰最早的
            key, entry = self._cache.popitem(last=False)
        else:
            # 默认使用LRU
            key, entry = self._cache.popitem(last=False)

        self._stats.size_bytes -= entry.size_bytes
        self._stats.evictions += 1
        logger.debug(f"L1缓存淘汰: {key}")

    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            if isinstance(value, pd.DataFrame):
                return value.memory_usage(deep=True).sum()
            elif isinstance(value, (str, bytes)):
                return len(value)
            else:
                # 使用pickle序列化计算大小
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # 默认1KB


class L2MemoryCache(ICacheLayer):
    """L2内存缓存 - 较大容量的内存缓存"""

    def __init__(self,
                 max_size_mb: int = 100,
                 default_ttl: int = 600,
                 compression: bool = True):
        """
        初始化L2内存缓存

        Args:
            max_size_mb: 最大大小（MB）
            default_ttl: 默认TTL（秒）
            compression: 是否启用压缩
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.compression = compression

        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

        logger.info(f"L2MemoryCache初始化，容量: {max_size_mb}MB, 压缩: {compression}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired:
                self._remove_entry(key)
                self._stats.misses += 1
                return None

            # 更新访问信息
            entry.access_time = datetime.now()
            entry.access_count += 1
            self._access_order[key] = time.time()
            self._access_order.move_to_end(key)

            # 解压数据（如果启用了压缩）
            value = self._decompress_value(entry.value)

            self._stats.hits += 1
            return value

    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """存储缓存值"""
        try:
            with self._lock:
                # 压缩数据（如果启用了压缩）
                compressed_value = self._compress_value(value)
                size_bytes = self._calculate_size(compressed_value)

                # 检查容量
                while (self._stats.size_bytes + size_bytes > self.max_size_bytes and
                       len(self._cache) > 0):
                    self._evict_lru()

                # 如果单个值太大，拒绝存储
                if size_bytes > self.max_size_bytes:
                    logger.warning(f"L2缓存值太大，拒绝存储: {key}")
                    return False

                # 移除旧条目（如果存在）
                if key in self._cache:
                    self._remove_entry(key)

                # 创建新条目
                entry = CacheEntry(
                    key=key,
                    value=compressed_value,
                    created_time=datetime.now(),
                    access_time=datetime.now(),
                    ttl_seconds=ttl_seconds or self.default_ttl,
                    size_bytes=size_bytes
                )

                # 存储条目
                self._cache[key] = entry
                self._access_order[key] = time.time()
                self._stats.size_bytes += size_bytes
                self._stats.entry_count = len(self._cache)

                logger.debug(f"L2缓存存储: {key}, 大小: {size_bytes}字节")
                return True

        except Exception as e:
            logger.error(f"L2缓存存储失败: {str(e)}")
            return False

    def remove(self, key: str) -> bool:
        """移除缓存值"""
        with self._lock:
            return self._remove_entry(key)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()
            logger.info("L2缓存已清空")

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        with self._lock:
            self._stats.entry_count = len(self._cache)
            return self._stats

    def _remove_entry(self, key: str) -> bool:
        """内部移除条目方法"""
        if key in self._cache:
            entry = self._cache[key]
            self._stats.size_bytes -= entry.size_bytes
            del self._cache[key]
            if key in self._access_order:
                del self._access_order[key]
            self._stats.entry_count = len(self._cache)
            return True
        return False

    def _evict_lru(self) -> None:
        """淘汰最久未使用的条目"""
        if not self._access_order:
            return

        lru_key = next(iter(self._access_order))
        self._remove_entry(lru_key)
        self._stats.evictions += 1
        logger.debug(f"L2缓存淘汰: {lru_key}")

    def _compress_value(self, value: Any) -> Any:
        """压缩值"""
        if not self.compression:
            return value

        try:
            if isinstance(value, pd.DataFrame):
                # DataFrame使用pickle+gzip压缩
                pickled = pickle.dumps(value)
                return gzip.compress(pickled)
            else:
                return value
        except Exception as e:
            logger.warning(f"压缩失败，使用原值: {str(e)}")
            return value

    def _decompress_value(self, value: Any) -> Any:
        """解压值"""
        if not self.compression:
            return value

        try:
            if isinstance(value, bytes) and value.startswith(b'\x1f\x8b'):
                # 检测到gzip压缩数据
                decompressed = gzip.decompress(value)
                return pickle.loads(decompressed)
            else:
                return value
        except Exception as e:
            logger.warning(f"解压失败，返回原值: {str(e)}")
            return value

    def _calculate_size(self, value: Any) -> int:
        """计算值的大小"""
        try:
            if isinstance(value, bytes):
                return len(value)
            elif isinstance(value, pd.DataFrame):
                return value.memory_usage(deep=True).sum()
            elif isinstance(value, str):
                return len(value.encode('utf-8'))
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # 默认1KB


class EventDrivenInvalidator:
    """事件驱动的缓存失效器"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[str], None]]] = defaultdict(list)
        self._lock = threading.RLock()
        logger.info("EventDrivenInvalidator初始化完成")

    def subscribe(self, event_type: str, callback: Callable[[str], None]) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数，接收键作为参数
        """
        with self._lock:
            self._subscribers[event_type].append(callback)
            logger.debug(f"订阅事件: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[str], None]) -> None:
        """取消订阅事件"""
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass

    def publish(self, event_type: str, key: str) -> None:
        """
        发布事件

        Args:
            event_type: 事件类型
            key: 相关的缓存键
        """
        with self._lock:
            callbacks = self._subscribers.get(event_type, [])
            for callback in callbacks:
                try:
                    callback(key)
                except Exception as e:
                    logger.error(f"事件回调执行失败: {str(e)}")


class MultiLayerCache:
    """
    多层缓存管理器

    实现L1内存缓存、L2内存缓存、L3磁盘缓存的统一管理，
    支持TTL、事件驱动和版本控制的失效策略。
    """

    def __init__(self,
                 l1_config: Optional[Dict[str, Any]] = None,
                 l2_config: Optional[Dict[str, Any]] = None,
                 enable_events: bool = True):
        """
        初始化多层缓存

        Args:
            l1_config: L1缓存配置
            l2_config: L2缓存配置
            enable_events: 是否启用事件驱动失效
        """
        # 初始化缓存层
        l1_config = l1_config or {}
        l2_config = l2_config or {}

        self.l1_cache = L1MemoryCache(
            max_size=l1_config.get('max_size', 1000),
            default_ttl=l1_config.get('default_ttl', 300),
            policy=CachePolicy(l1_config.get('policy', 'lru'))
        )

        self.l2_cache = L2MemoryCache(
            max_size_mb=l2_config.get('max_size_mb', 100),
            default_ttl=l2_config.get('default_ttl', 600),
            compression=l2_config.get('compression', True)
        )

        # 事件驱动失效器
        self.event_invalidator = EventDrivenInvalidator() if enable_events else None

        # 版本管理
        self._versions: Dict[str, str] = {}
        self._version_lock = threading.RLock()

        # 统计信息
        self._global_stats = CacheStats()

        # 设置事件监听
        if self.event_invalidator:
            self.event_invalidator.subscribe('data_updated', self._on_data_updated)
            self.event_invalidator.subscribe('version_changed', self._on_version_changed)

        logger.info("MultiLayerCache初始化完成")

    def get(self, key: str, version: Optional[str] = None) -> Optional[Any]:
        """
        获取缓存值，按L1 -> L2的顺序查找

        Args:
            key: 缓存键
            version: 期望的版本（可选）

        Returns:
            缓存值或None
        """
        try:
            # 检查版本
            if version and not self._check_version(key, version):
                return None

            # L1缓存查找
            value = self.l1_cache.get(key)
            if value is not None:
                self._global_stats.hits += 1
                logger.debug(f"L1缓存命中: {key}")
                return value

            # L2缓存查找
            value = self.l2_cache.get(key)
            if value is not None:
                # 将数据提升到L1缓存
                self.l1_cache.put(key, value)
                self._global_stats.hits += 1
                logger.debug(f"L2缓存命中: {key}")
                return value

            # 所有层都未命中
            self._global_stats.misses += 1
            logger.debug(f"缓存未命中: {key}")
            return None

        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {str(e)}")
            self._global_stats.misses += 1
            return None

    def put(self,
            key: str,
            value: Any,
            ttl_seconds: Optional[int] = None,
            version: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        存储缓存值到所有层

        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: TTL（秒）
            version: 版本号
            metadata: 元数据

        Returns:
            是否成功
        """
        try:
            # 更新版本
            if version:
                self._update_version(key, version)

            # 存储到所有层
            l1_success = self.l1_cache.put(key, value, ttl_seconds)
            l2_success = self.l2_cache.put(key, value, ttl_seconds)

            success = l1_success or l2_success

            if success:
                logger.debug(f"缓存存储成功: {key}")

                # 发布数据更新事件
                if self.event_invalidator:
                    self.event_invalidator.publish('data_stored', key)

            return success

        except Exception as e:
            logger.error(f"存储缓存失败 {key}: {str(e)}")
            return False

    def remove(self, key: str) -> bool:
        """
        从所有层移除缓存值

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        try:
            l1_removed = self.l1_cache.remove(key)
            l2_removed = self.l2_cache.remove(key)

            # 移除版本信息
            with self._version_lock:
                if key in self._versions:
                    del self._versions[key]

            success = l1_removed or l2_removed

            if success:
                logger.debug(f"缓存移除成功: {key}")

                # 发布移除事件
                if self.event_invalidator:
                    self.event_invalidator.publish('data_removed', key)

            return success

        except Exception as e:
            logger.error(f"移除缓存失败 {key}: {str(e)}")
            return False

    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        按模式失效缓存

        Args:
            pattern: 匹配模式（支持通配符*）

        Returns:
            失效的条目数
        """
        try:
            import fnmatch

            # 获取所有键
            l1_keys = list(self.l1_cache._cache.keys())
            l2_keys = list(self.l2_cache._cache.keys())
            all_keys = set(l1_keys + l2_keys)

            # 匹配并移除
            removed_count = 0
            for key in all_keys:
                if fnmatch.fnmatch(key, pattern):
                    if self.remove(key):
                        removed_count += 1

            logger.info(f"按模式 '{pattern}' 失效了 {removed_count} 个缓存条目")
            return removed_count

        except Exception as e:
            logger.error(f"按模式失效缓存失败: {str(e)}")
            return 0

    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        按标签失效缓存

        Args:
            tags: 标签列表

        Returns:
            失效的条目数
        """
        # 实现基于标签的失效逻辑
        # 这需要在存储时记录标签信息
        # 此处提供基础实现框架
        removed_count = 0

        try:
            # 遍历所有缓存条目，检查标签
            for cache_layer in [self.l1_cache, self.l2_cache]:
                if hasattr(cache_layer, '_cache'):
                    keys_to_remove = []
                    for key, entry in cache_layer._cache.items():
                        entry_tags = entry.metadata.get('tags', [])
                        if any(tag in entry_tags for tag in tags):
                            keys_to_remove.append(key)

                    for key in keys_to_remove:
                        if self.remove(key):
                            removed_count += 1

            logger.info(f"按标签失效了 {removed_count} 个缓存条目")
            return removed_count

        except Exception as e:
            logger.error(f"按标签失效缓存失败: {str(e)}")
            return 0

    def clear_all(self) -> None:
        """清空所有缓存层"""
        try:
            self.l1_cache.clear()
            self.l2_cache.clear()

            with self._version_lock:
                self._versions.clear()

            self._global_stats = CacheStats()

            logger.info("所有缓存层已清空")

        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取所有层的统计信息"""
        try:
            l1_stats = self.l1_cache.get_stats()
            l2_stats = self.l2_cache.get_stats()

            return {
                'global': {
                    'total_hits': l1_stats.hits + l2_stats.hits,
                    'total_misses': l1_stats.misses + l2_stats.misses,
                    'overall_hit_ratio': (l1_stats.hits + l2_stats.hits) /
                    max(1, l1_stats.hits + l2_stats.hits + l1_stats.misses + l2_stats.misses),
                    'total_size_bytes': l1_stats.size_bytes + l2_stats.size_bytes,
                    'total_entries': l1_stats.entry_count + l2_stats.entry_count
                },
                'l1': {
                    'hits': l1_stats.hits,
                    'misses': l1_stats.misses,
                    'hit_ratio': l1_stats.hit_ratio,
                    'evictions': l1_stats.evictions,
                    'size_bytes': l1_stats.size_bytes,
                    'entry_count': l1_stats.entry_count
                },
                'l2': {
                    'hits': l2_stats.hits,
                    'misses': l2_stats.misses,
                    'hit_ratio': l2_stats.hit_ratio,
                    'evictions': l2_stats.evictions,
                    'size_bytes': l2_stats.size_bytes,
                    'entry_count': l2_stats.entry_count
                }
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {}

    def _check_version(self, key: str, expected_version: str) -> bool:
        """检查版本是否匹配"""
        with self._version_lock:
            current_version = self._versions.get(key)
            return current_version == expected_version if current_version else True

    def _update_version(self, key: str, version: str) -> None:
        """更新版本信息"""
        with self._version_lock:
            old_version = self._versions.get(key)
            self._versions[key] = version

            # 如果版本变化，发布版本变化事件
            if old_version and old_version != version and self.event_invalidator:
                self.event_invalidator.publish('version_changed', key)

    def _on_data_updated(self, key: str) -> None:
        """数据更新事件处理"""
        logger.debug(f"收到数据更新事件: {key}")
        # 可以在这里实现额外的逻辑，如通知其他组件

    def _on_version_changed(self, key: str) -> None:
        """版本变化事件处理"""
        logger.debug(f"版本变化: {key}")
        # 版本变化时可能需要失效相关缓存


# 工厂函数
def create_multi_layer_cache(
    l1_max_size: int = 1000,
    l1_ttl: int = 300,
    l2_max_size_mb: int = 100,
    l2_ttl: int = 600,
    enable_compression: bool = True,
    enable_events: bool = True
) -> MultiLayerCache:
    """
    创建多层缓存实例

    Args:
        l1_max_size: L1缓存最大条目数
        l1_ttl: L1缓存默认TTL
        l2_max_size_mb: L2缓存最大大小（MB）
        l2_ttl: L2缓存默认TTL
        enable_compression: 是否启用压缩
        enable_events: 是否启用事件驱动

    Returns:
        MultiLayerCache: 多层缓存实例
    """
    l1_config = {
        'max_size': l1_max_size,
        'default_ttl': l1_ttl,
        'policy': 'lru'
    }

    l2_config = {
        'max_size_mb': l2_max_size_mb,
        'default_ttl': l2_ttl,
        'compression': enable_compression
    }

    return MultiLayerCache(
        l1_config=l1_config,
        l2_config=l2_config,
        enable_events=enable_events
    )


# 导出的公共接口
__all__ = [
    'MultiLayerCache',
    'CacheLevel',
    'CachePolicy',
    'InvalidationStrategy',
    'CacheEntry',
    'CacheStats',
    'ICacheLayer',
    'L1MemoryCache',
    'L2MemoryCache',
    'EventDrivenInvalidator',
    'create_multi_layer_cache'
]
