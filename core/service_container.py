#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务容器模块
用于依赖注入和服务管理
"""

from typing import Dict, Any, Callable, Optional, Type, TypeVar
import inspect

T = TypeVar('T')


class ServiceContainer:
    """服务容器类，用于依赖注入"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}

    def register(self, name: str, service: Any, singleton: bool = True):
        """注册服务"""
        self._services[name] = service
        self._singletons[name] = singleton

    def register_factory(self, name: str, factory: Callable, singleton: bool = True):
        """注册工厂函数"""
        self._factories[name] = factory
        self._singletons[name] = singleton

    def get(self, name: str) -> Any:
        """获取服务"""
        if name in self._services:
            return self._services[name]

        if name in self._factories:
            factory = self._factories[name]

            # 如果是单例，创建后缓存
            if self._singletons.get(name, True):
                service = factory()
                self._services[name] = service
                return service
            else:
                return factory()

        raise ValueError(f"Service '{name}' not found")

    def has(self, name: str) -> bool:
        """检查是否有服务"""
        return name in self._services or name in self._factories

    def remove(self, name: str):
        """移除服务"""
        if name in self._services:
            del self._services[name]
        if name in self._factories:
            del self._factories[name]
        if name in self._singletons:
            del self._singletons[name]

    def clear(self):
        """清空所有服务"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()

    def auto_wire(self, cls: Type[T], *args, **kwargs) -> T:
        """自动装配类实例"""
        # 获取构造函数的参数
        sig = inspect.signature(cls.__init__)
        params = list(sig.parameters.values())[1:]  # 跳过self参数

        # 尝试从容器中获取依赖
        injected_kwargs = {}
        for param in params:
            if param.name not in kwargs and self.has(param.name):
                injected_kwargs[param.name] = self.get(param.name)

        # 合并参数
        final_kwargs = {**injected_kwargs, **kwargs}

        return cls(*args, **final_kwargs)
