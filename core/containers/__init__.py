"""
依赖注入容器模块

提供依赖注入和服务管理的核心组件。
"""

from .service_container import ServiceContainer, get_service_container
from .service_registry import ServiceRegistry, ServiceInfo, ServiceScope

__all__ = [
    'ServiceContainer',
    'get_service_container',
    'ServiceRegistry',
    'ServiceInfo',
    'ServiceScope'
]
