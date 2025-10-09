"""
多级缓存管理器
"""

import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict
from enum import Enum


class CacheLevel(Enum):
    """缓存级别枚举"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"


class MultiLevelCacheManager:
    """多级缓存管理器"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None

            # 检查是否过期
            if self._is_expired(key):
                self._remove(key)
                return None

            # 移动到末尾（LRU）
            value = self._cache.pop(key)
            self._cache[key] = value
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                self._remove(key)

            # 检查容量
            if len(self._cache) >= self.max_size:
                # 删除最旧的项
                oldest_key = next(iter(self._cache))
                self._remove(oldest_key)

            # 添加新项
            self._cache[key] = value
            self._timestamps[key] = time.time() + (ttl or self.ttl)

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._timestamps:
            return True
        return time.time() > self._timestamps[key]

    def _remove(self, key: str) -> None:
        """移除缓存项"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def cleanup_expired(self) -> int:
        """清理过期项"""
        with self._lock:
            expired_keys = [
                key for key in self._cache.keys()
                if self._is_expired(key)
            ]

            for key in expired_keys:
                self._remove(key)

            return len(expired_keys)


# 全局实例
cache_manager = MultiLevelCacheManager()
