from loguru import logger
"""
trace_context.py - 调用链追踪上下文管理模块

提供 trace_id 的上下文管理功能，支持同步和异步环境下的调用链追踪
"""

import contextvars
import uuid
from typing import Optional


# 创建 trace_id 上下文变量
trace_id_var = contextvars.ContextVar('trace_id', default='')


def generate_trace_id() -> str:
    """生成新的 trace_id

    Returns:
        str: 新生成的 trace_id
    """
    return str(uuid.uuid4())[:8]


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """设置当前上下文的 trace_id

    Args:
        trace_id: 要设置的 trace_id，如果为 None 则生成新的

    Returns:
        str: 设置的 trace_id
    """
    if trace_id is None:
        trace_id = generate_trace_id()
    trace_id_var.set(trace_id)
    return trace_id


def get_trace_id() -> str:
    """获取当前上下文的 trace_id

    Returns:
        str: 当前的 trace_id，如果未设置则返回空字符串
    """
    return trace_id_var.get()


def clear_trace_id():
    """清除当前上下文的 trace_id"""
    trace_id_var.set('')


class TraceIdFilter:
    """Loguru日志过滤器，为日志记录添加 trace_id"""

    def __call__(self, record):
        """为Loguru日志记录添加 trace_id 属性

        Args:
            record: Loguru日志记录对象

        Returns:
            bool: 始终返回 True，不过滤任何日志
        """
        record["extra"]["trace_id"] = get_trace_id()
        return True


class TraceContext:
    """trace_id 上下文管理器"""

    def __init__(self, trace_id: Optional[str] = None):
        """初始化上下文管理器

        Args:
            trace_id: 要设置的 trace_id，如果为 None 则生成新的
        """
        self.trace_id = trace_id or generate_trace_id()
        self.old_trace_id = None

    def __enter__(self):
        """进入上下文，设置新的 trace_id"""
        self.old_trace_id = get_trace_id()
        set_trace_id(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，恢复旧的 trace_id"""
        set_trace_id(self.old_trace_id)


def with_trace_id(trace_id: Optional[str] = None):
    """装饰器：为函数调用设置 trace_id

    Args:
        trace_id: 要设置的 trace_id，如果为 None 则生成新的
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TraceContext(trace_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# 导出主要接口
__all__ = [
    'trace_id_var',
    'generate_trace_id',
    'set_trace_id',
    'get_trace_id',
    'clear_trace_id',
    'TraceIdFilter',
    'TraceContext',
    'with_trace_id'
]
