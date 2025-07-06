"""
基础服务模块

定义所有服务的基础接口和通用功能。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..events import EventBus, get_event_bus


logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    基础服务接口

    所有业务服务都应该继承此类。
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        初始化基础服务

        Args:
            event_bus: 事件总线，如果为None则使用全局事件总线
        """
        self._event_bus = event_bus or get_event_bus()
        self._initialized = False
        self._disposed = False
        self._name = self.__class__.__name__

    @property
    def name(self) -> str:
        """获取服务名称"""
        return self._name

    @property
    def initialized(self) -> bool:
        """检查服务是否已初始化"""
        return self._initialized

    @property
    def disposed(self) -> bool:
        """检查服务是否已释放"""
        return self._disposed

    @property
    def event_bus(self) -> EventBus:
        """获取事件总线"""
        return self._event_bus

    def initialize(self) -> None:
        """
        初始化服务

        子类可以重写此方法来执行初始化逻辑。
        """
        if self._initialized:
            logger.warning(f"Service {self._name} is already initialized")
            return

        try:
            self._do_initialize()
            self._initialized = True
            logger.info(f"Service {self._name} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service {self._name}: {e}")
            raise

    def dispose(self) -> None:
        """
        释放服务资源

        子类可以重写此方法来执行清理逻辑。
        """
        if self._disposed:
            logger.warning(f"Service {self._name} is already disposed")
            return

        try:
            self._do_dispose()
            self._disposed = True
            self._initialized = False
            logger.info(f"Service {self._name} disposed successfully")
        except Exception as e:
            logger.error(f"Failed to dispose service {self._name}: {e}")
            raise

    def _do_initialize(self) -> None:
        """
        执行初始化逻辑

        子类应该重写此方法来实现具体的初始化逻辑。
        """
        pass

    def _do_dispose(self) -> None:
        """
        执行清理逻辑

        子类应该重写此方法来实现具体的清理逻辑。
        """
        pass

    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if not self._initialized:
            raise RuntimeError(f"Service {self._name} is not initialized")

    def _ensure_not_disposed(self) -> None:
        """确保服务未被释放"""
        if self._disposed:
            raise RuntimeError(f"Service {self._name} has been disposed")

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


class AsyncBaseService(BaseService):
    """
    异步基础服务接口

    支持异步操作的服务应该继承此类。
    """

    async def initialize_async(self) -> None:
        """
        异步初始化服务
        """
        if self._initialized:
            logger.warning(f"Service {self._name} is already initialized")
            return

        try:
            await self._do_initialize_async()
            self._initialized = True
            logger.info(f"Service {self._name} initialized successfully (async)")
        except Exception as e:
            logger.error(f"Failed to initialize service {self._name} (async): {e}")
            raise

    async def dispose_async(self) -> None:
        """
        异步释放服务资源
        """
        if self._disposed:
            logger.warning(f"Service {self._name} is already disposed")
            return

        try:
            await self._do_dispose_async()
            self._disposed = True
            self._initialized = False
            logger.info(f"Service {self._name} disposed successfully (async)")
        except Exception as e:
            logger.error(f"Failed to dispose service {self._name} (async): {e}")
            raise

    async def _do_initialize_async(self) -> None:
        """
        执行异步初始化逻辑

        子类应该重写此方法来实现具体的异步初始化逻辑。
        """
        pass

    async def _do_dispose_async(self) -> None:
        """
        执行异步清理逻辑

        子类应该重写此方法来实现具体的异步清理逻辑。
        """
        pass

    async def __aenter__(self):
        await self.initialize_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.dispose_async()


class ConfigurableService(BaseService):
    """
    可配置服务基类

    需要配置的服务应该继承此类。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, event_bus: Optional[EventBus] = None):
        """
        初始化可配置服务

        Args:
            config: 服务配置
            event_bus: 事件总线
        """
        super().__init__(event_bus)
        self._config = config or {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取服务配置"""
        return self._config.copy()

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新服务配置

        Args:
            config: 新的配置
        """
        self._config.update(config)
        self._on_config_updated()
        logger.debug(f"Updated config for service {self._name}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)

    def _on_config_updated(self) -> None:
        """
        配置更新回调

        子类可以重写此方法来响应配置更新。
        """
        pass


class CacheableService(BaseService):
    """
    可缓存服务基类

    需要缓存功能的服务应该继承此类。
    """

    def __init__(self, cache_size: int = 100, event_bus: Optional[EventBus] = None):
        """
        初始化可缓存服务

        Args:
            cache_size: 缓存大小
            event_bus: 事件总线
        """
        super().__init__(event_bus)
        self._cache_size = cache_size
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def get_from_cache(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据或None
        """
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        else:
            self._cache_misses += 1
            return None

    def put_to_cache(self, key: str, value: Any) -> None:
        """
        将数据放入缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        if len(self._cache) >= self._cache_size:
            # 简单的LRU：删除第一个元素
            first_key = next(iter(self._cache))
            del self._cache[first_key]

        self._cache[key] = value

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.debug(f"Cache cleared for service {self._name}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

        return {
            'cache_size': len(self._cache),
            'max_cache_size': self._cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate
        }

    def _do_dispose(self) -> None:
        """清理缓存资源"""
        self.clear_cache()
        super()._do_dispose()
