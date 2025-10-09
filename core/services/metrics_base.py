"""
Metrics基类 - 统一Metrics接口

为所有服务的Metrics类提供统一的接口，支持：
1. 字典式访问 (metrics['key'])
2. 属性访问 (metrics.key)
3. 转换为字典 (metrics.to_dict())

解决测试中"Metrics对象不可下标"的问题。
"""

from typing import Any, Dict
from dataclasses import dataclass, asdict


@dataclass
class MetricsBase:
    """
    Metrics基类

    所有服务的Metrics类应该继承此类或使用dataclass+__getitem__方法。
    """

    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"Metric '{key}' not found")

    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """字典式get方法"""
        try:
            return getattr(self, key, default)
        except AttributeError:
            return default

    def keys(self):
        """返回所有指标名称"""
        return [k for k in self.__dict__.keys() if not k.startswith('_')]

    def values(self):
        """返回所有指标值"""
        return [v for k, v in self.__dict__.items() if not k.startswith('_')]

    def items(self):
        """返回所有指标项"""
        return [(k, v) for k, v in self.__dict__.items() if not k.startswith('_')]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        try:
            # 如果是dataclass，使用asdict
            return asdict(self)
        except TypeError:
            # 否则手动转换
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def update(self, **kwargs):
        """批量更新指标"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        """字符串表示"""
        metrics_str = ', '.join(f"{k}={v}" for k, v in self.items())
        return f"{self.__class__.__name__}({metrics_str})"


# 便捷函数：为现有Metrics类添加字典接口
def add_dict_interface(metrics_class):
    """
    装饰器：为Metrics类添加字典接口

    用法:
    @add_dict_interface
    @dataclass
    class MyMetrics:
        counter: int = 0
        value: float = 0.0
    """

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"Metric '{key}' not found")

    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        try:
            return asdict(self)
        except TypeError:
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def keys(self):
        return [k for k in self.__dict__.keys() if not k.startswith('_')]

    def values(self):
        return [v for k, v in self.__dict__.items() if not k.startswith('_')]

    def items(self):
        return [(k, v) for k, v in self.__dict__.items() if not k.startswith('_')]

    # 添加方法到类
    metrics_class.__getitem__ = __getitem__
    metrics_class.__setitem__ = __setitem__
    metrics_class.get = get
    metrics_class.to_dict = to_dict
    metrics_class.keys = keys
    metrics_class.values = values
    metrics_class.items = items

    return metrics_class
