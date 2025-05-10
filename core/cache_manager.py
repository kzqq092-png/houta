"""
缓存管理器模块

提供统一的缓存管理功能，支持TTL、LRU等缓存策略
"""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import threading
from core.logger import LogManager
import traceback


class CacheManager:
    """缓存管理器类"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        """初始化缓存管理器

        Args:
            max_size: 最大缓存条目数，默认10000
            default_ttl: 默认缓存有效期（秒），默认300秒
        """
        self.log_manager = LogManager()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._last_cleanup = datetime.now()
        self._cleanup_interval = 3600  # 清理间隔（秒）

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        try:
            with self._lock:
                if key not in self._cache:
                    self._misses += 1
                    return None

                cache_item = self._cache[key]
                now = datetime.now()

                # 检查是否过期
                if 'expire_time' in cache_item and now > cache_item['expire_time']:
                    del self._cache[key]
                    self._misses += 1
                    return None

                self._hits += 1
                return cache_item['data']

        except Exception as e:
            self.log_manager.error(f"获取缓存数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 缓存有效期（秒），None表示使用默认值

        Returns:
            bool: 是否设置成功
        """
        try:
            with self._lock:
                # 如果缓存已满，删除最旧的条目
                if len(self._cache) >= self._max_size:
                    oldest_key = min(self._cache.keys(),
                                     key=lambda k: self._cache[k].get('timestamp', datetime.min))
                    del self._cache[oldest_key]

                # 计算过期时间
                expire_time = None
                if ttl is not None:
                    expire_time = datetime.now() + timedelta(seconds=ttl)
                elif self._default_ttl > 0:
                    expire_time = datetime.now() + \
                        timedelta(seconds=self._default_ttl)

                # 存储数据
                self._cache[key] = {
                    'data': value,
                    'timestamp': datetime.now(),
                    'expire_time': expire_time
                }

                # 检查是否需要清理
                self._check_cleanup()

                return True

        except Exception as e:
            self.log_manager.error(f"设置缓存数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return False

    def delete(self, key: str) -> bool:
        """删除缓存数据

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    return True
                return False

        except Exception as e:
            self.log_manager.error(f"删除缓存数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        try:
            with self._lock:
                self._cache.clear()
                self._hits = 0
                self._misses = 0
                self._last_cleanup = datetime.now()

        except Exception as e:
            self.log_manager.error(f"清空缓存失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict[str, Any]: 包含缓存统计信息的字典
        """
        try:
            with self._lock:
                total_requests = self._hits + self._misses
                hit_rate = self._hits / total_requests if total_requests > 0 else 0

                return {
                    'size': len(self._cache),
                    'max_size': self._max_size,
                    'hits': self._hits,
                    'misses': self._misses,
                    'hit_rate': hit_rate,
                    'last_cleanup': self._last_cleanup,
                    'cleanup_interval': self._cleanup_interval
                }

        except Exception as e:
            self.log_manager.error(f"获取缓存统计信息失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return {}

    def _check_cleanup(self) -> None:
        """检查是否需要清理过期缓存"""
        try:
            now = datetime.now()
            if (now - self._last_cleanup).total_seconds() > self._cleanup_interval:
                self._cleanup_expired()
                self._last_cleanup = now

        except Exception as e:
            self.log_manager.error(f"检查缓存清理失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _cleanup_expired(self) -> None:
        """清理过期的缓存条目"""
        try:
            now = datetime.now()
            expired_keys = [
                key for key, item in self._cache.items()
                if 'expire_time' in item and now > item['expire_time']
            ]
            for key in expired_keys:
                del self._cache[key]

            self.log_manager.info(f"已清理 {len(expired_keys)} 个过期缓存")

        except Exception as e:
            self.log_manager.error(f"清理过期缓存失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def set_max_size(self, size: int) -> None:
        """设置最大缓存大小

        Args:
            size: 新的最大缓存条目数
        """
        try:
            with self._lock:
                self._max_size = size
                # 如果当前缓存大小超过新的最大值，删除多余的条目
                while len(self._cache) > self._max_size:
                    oldest_key = min(self._cache.keys(),
                                     key=lambda k: self._cache[k].get('timestamp', datetime.min))
                    del self._cache[oldest_key]

        except Exception as e:
            self.log_manager.error(f"设置最大缓存大小失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def set_default_ttl(self, ttl: int) -> None:
        """设置默认缓存有效期

        Args:
            ttl: 新的默认缓存有效期（秒）
        """
        try:
            with self._lock:
                self._default_ttl = ttl

        except Exception as e:
            self.log_manager.error(f"设置默认缓存有效期失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def set_cleanup_interval(self, interval: int) -> None:
        """设置清理间隔

        Args:
            interval: 新的清理间隔（秒）
        """
        try:
            with self._lock:
                self._cleanup_interval = interval

        except Exception as e:
            self.log_manager.error(f"设置清理间隔失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def get_keys(self) -> list:
        """获取所有缓存键

        Returns:
            list: 缓存键列表
        """
        try:
            with self._lock:
                return list(self._cache.keys())

        except Exception as e:
            self.log_manager.error(f"获取缓存键列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return []

    def get_size(self) -> int:
        """获取当前缓存大小

        Returns:
            int: 当前缓存条目数
        """
        try:
            with self._lock:
                return len(self._cache)

        except Exception as e:
            self.log_manager.error(f"获取缓存大小失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存键是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在且未过期
        """
        try:
            with self._lock:
                if key not in self._cache:
                    return False

                cache_item = self._cache[key]
                if 'expire_time' in cache_item and datetime.now() > cache_item['expire_time']:
                    return False

                return True

        except Exception as e:
            self.log_manager.error(f"检查缓存键是否存在失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return False

    def touch(self, key: str) -> bool:
        """更新缓存项的访问时间

        Args:
            key: 缓存键

        Returns:
            bool: 是否更新成功
        """
        try:
            with self._lock:
                if key not in self._cache:
                    return False

                self._cache[key]['timestamp'] = datetime.now()
                return True

        except Exception as e:
            self.log_manager.error(f"更新缓存访问时间失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """获取缓存项的剩余有效期

        Args:
            key: 缓存键

        Returns:
            Optional[int]: 剩余有效期（秒），如果没有过期时间则返回None
        """
        try:
            with self._lock:
                if key not in self._cache:
                    return None

                cache_item = self._cache[key]
                if 'expire_time' not in cache_item:
                    return None

                remaining = (cache_item['expire_time'] -
                             datetime.now()).total_seconds()
                return max(0, int(remaining))

        except Exception as e:
            self.log_manager.error(f"获取缓存剩余有效期失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return None
