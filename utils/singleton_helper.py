"""
单例访问助手模块

提供统一的数据管理器访问方式，确保整个系统使用同一个实例
"""

from core.services.unified_data_manager import get_unified_data_manager
from core.containers import get_service_container

def get_data_manager():
    """
    获取统一数据管理器实例
    
    Returns:
        UnifiedDataManager: 统一数据管理器单例实例
    """
    return get_unified_data_manager()

def get_plugin_manager():
    """
    获取插件管理器实例
    
    Returns:
        PluginManager: 插件管理器实例
    """
    try:
        container = get_service_container()
        if container and container.is_registered('PluginManager'):
            return container.resolve('PluginManager')
    except Exception:
        pass
    return None

def get_service(service_type):
    """
    从服务容器获取服务实例
    
    Args:
        service_type: 服务类型
        
    Returns:
        服务实例或None
    """
    try:
        container = get_service_container()
        if container and container.is_registered(service_type):
            return container.resolve(service_type)
    except Exception:
        pass
    return None
