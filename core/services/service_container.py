"""
服务容器

实现依赖注入容器，管理所有服务的生命周期。
"""

import logging
from typing import Dict, Type, Any, Optional, Callable
from threading import Lock

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    服务容器

    功能：
    1. 服务注册和发现
    2. 依赖注入
    3. 生命周期管理
    4. 单例模式支持
    """

    def __init__(self):
        """初始化服务容器"""
        self._services: Dict[str, BaseService] = {}
        self._factories: Dict[str, Callable[[], BaseService]] = {}
        self._singletons: Dict[str, bool] = {}
        self._lock = Lock()

        logger.info("Service container initialized")

    def register(self,
                 name: str,
                 factory: Callable[[], BaseService],
                 singleton: bool = True) -> None:
        """
        注册服务

        Args:
            name: 服务名称
            factory: 服务工厂函数
            singleton: 是否单例模式
        """
        with self._lock:
            self._factories[name] = factory
            self._singletons[name] = singleton

            logger.debug(f"Service registered: {name} (singleton={singleton})")

    def get(self, name: str) -> Optional[BaseService]:
        """
        获取服务实例

        Args:
            name: 服务名称

        Returns:
            服务实例，如果不存在则返回None
        """
        with self._lock:
            # 如果是单例且已创建，直接返回
            if self._singletons.get(name, True) and name in self._services:
                return self._services[name]

            # 检查是否有工厂函数
            if name not in self._factories:
                logger.warning(f"Service not found: {name}")
                return None

            try:
                # 创建服务实例
                service = self._factories[name]()

                # 如果是单例，保存实例
                if self._singletons.get(name, True):
                    self._services[name] = service

                logger.debug(f"Service created: {name}")
                return service

            except Exception as e:
                logger.error(f"Failed to create service {name}: {e}")
                return None

    def get_service(self, name: str) -> Optional[BaseService]:
        """
        获取服务实例（get方法的别名）

        Args:
            name: 服务名称

        Returns:
            服务实例，如果不存在则返回None
        """
        return self.get(name)

    def has(self, name: str) -> bool:
        """
        检查服务是否存在

        Args:
            name: 服务名称

        Returns:
            True如果服务存在，否则False
        """
        with self._lock:
            return name in self._factories

    def remove(self, name: str) -> bool:
        """
        移除服务

        Args:
            name: 服务名称

        Returns:
            True如果成功移除，否则False
        """
        with self._lock:
            removed = False

            # 移除实例
            if name in self._services:
                service = self._services[name]
                try:
                    if hasattr(service, 'dispose'):
                        service.dispose()
                except Exception as e:
                    logger.error(f"Error disposing service {name}: {e}")

                del self._services[name]
                removed = True

            # 移除工厂
            if name in self._factories:
                del self._factories[name]
                removed = True

            # 移除单例标记
            if name in self._singletons:
                del self._singletons[name]

            if removed:
                logger.debug(f"Service removed: {name}")

            return removed

    def clear(self) -> None:
        """清空所有服务"""
        with self._lock:
            # 释放所有服务实例
            for name, service in self._services.items():
                try:
                    if hasattr(service, 'dispose'):
                        service.dispose()
                except Exception as e:
                    logger.error(f"Error disposing service {name}: {e}")

            # 清空所有字典
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()

            logger.info("All services cleared")

    def get_all_services(self) -> Dict[str, BaseService]:
        """
        获取所有已创建的服务实例

        Returns:
            服务名称到实例的映射
        """
        with self._lock:
            return self._services.copy()

    def get_service_names(self) -> list:
        """
        获取所有已注册的服务名称

        Returns:
            服务名称列表
        """
        with self._lock:
            return list(self._factories.keys())

    def initialize_all(self) -> None:
        """初始化所有已注册的服务"""
        with self._lock:
            for name in self._factories.keys():
                try:
                    service = self.get(name)
                    if service and hasattr(service, 'initialize'):
                        service.initialize()
                        logger.debug(f"Service initialized: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize service {name}: {e}")

    def dispose(self) -> None:
        """释放容器资源"""
        try:
            self.clear()
            logger.info("Service container disposed")

        except Exception as e:
            logger.error(f"Error disposing service container: {e}")

    def __contains__(self, name: str) -> bool:
        """支持 in 操作符"""
        return self.has(name)

    def __len__(self) -> int:
        """返回已注册服务的数量"""
        with self._lock:
            return len(self._factories)

    def __repr__(self) -> str:
        """返回容器的字符串表示"""
        with self._lock:
            return f"ServiceContainer(services={len(self._services)}, factories={len(self._factories)})"
