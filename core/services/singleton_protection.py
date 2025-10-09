"""
单例保护机制

用于确保关键组件只有一个实例，避免重复初始化问题。
"""

import threading
from typing import Dict, Any, Type
from loguru import logger


class SingletonMeta(type):
    """
    线程安全的单例元类

    确保每个类只能有一个实例，防止重复初始化。
    """
    _instances: Dict[Type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """
        控制实例创建，确保单例
        """
        if cls not in cls._instances:
            with cls._lock:
                # 双重检查锁定模式
                if cls not in cls._instances:
                    logger.info(f"[SECURE] 创建单例实例: {cls.__name__}")
                    cls._instances[cls] = super().__call__(*args, **kwargs)
                else:
                    logger.info(f"♻️ 返回已存在的单例实例: {cls.__name__}")
        else:
            logger.info(f"♻️ 返回已存在的单例实例: {cls.__name__}")

        return cls._instances[cls]

    @classmethod
    def clear_instance(mcs, cls: Type):
        """清除指定类的单例实例（用于测试）"""
        with mcs._lock:
            if cls in mcs._instances:
                del mcs._instances[cls]
                logger.info(f"🗑️ 已清除单例实例: {cls.__name__}")

    @classmethod
    def get_instances(mcs) -> Dict[str, Any]:
        """获取所有单例实例（用于调试）"""
        return {cls.__name__: instance for cls, instance in mcs._instances.items()}


class InitializationTracker:
    """
    初始化跟踪器

    跟踪组件的初始化状态，防止重复初始化。
    """
    _initialized_components: Dict[str, bool] = {}
    _lock = threading.Lock()

    @classmethod
    def mark_initialized(cls, component_name: str):
        """标记组件为已初始化"""
        with cls._lock:
            cls._initialized_components[component_name] = True
            logger.info(f"组件已标记为已初始化: {component_name}")

    @classmethod
    def is_initialized(cls, component_name: str) -> bool:
        """检查组件是否已初始化"""
        return cls._initialized_components.get(component_name, False)

    @classmethod
    def reset_component(cls, component_name: str):
        """重置组件初始化状态（用于测试）"""
        with cls._lock:
            if component_name in cls._initialized_components:
                del cls._initialized_components[component_name]
                logger.info(f"已重置组件初始化状态: {component_name}")

    @classmethod
    def get_status(cls) -> Dict[str, bool]:
        """获取所有组件的初始化状态"""
        return cls._initialized_components.copy()


def ensure_single_initialization(component_name: str):
    """
    装饰器：确保方法只执行一次

    Args:
        component_name: 组件名称
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if InitializationTracker.is_initialized(component_name):
                logger.warning(f" 组件 {component_name} 已初始化，跳过重复初始化")
                return None

            logger.info(f"开始初始化组件: {component_name}")
            result = func(*args, **kwargs)
            InitializationTracker.mark_initialized(component_name)
            logger.info(f"组件初始化完成: {component_name}")
            return result
        return wrapper
    return decorator


# 示例用法
if __name__ == "__main__":
    # 测试单例保护
    class TestService(metaclass=SingletonMeta):
        def __init__(self, name):
            self.name = name
            print(f"创建 {name}")

    # 创建实例
    service1 = TestService("Service1")
    service2 = TestService("Service2")  # 应该返回同一个实例

    print(f"service1 is service2: {service1 is service2}")
    print(f"实例: {SingletonMeta.get_instances()}")
