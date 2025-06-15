#!/usr/bin/env python3
"""
性能监控模块

提供统一的性能监控和度量功能
"""

import time
import threading
import psutil
import gc
from typing import Dict, Any, Optional, Callable, ContextManager
from contextlib import contextmanager
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标数据类"""

    def __init__(self):
        self.execution_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.memory_usage: deque = deque(maxlen=1000)
        self.cpu_usage: deque = deque(maxlen=1000)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.start_time = datetime.now()
        self._lock = threading.RLock()

    def add_execution_time(self, operation: str, duration: float):
        """添加执行时间记录"""
        with self._lock:
            self.execution_times[operation].append(duration)
            self.call_counts[operation] += 1

    def add_memory_usage(self, usage: float):
        """添加内存使用记录"""
        with self._lock:
            self.memory_usage.append(usage)

    def add_cpu_usage(self, usage: float):
        """添加CPU使用记录"""
        with self._lock:
            self.cpu_usage.append(usage)

    def increment_error(self, error_type: str):
        """增加错误计数"""
        with self._lock:
            self.error_counts[error_type] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = {
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                'total_operations': sum(self.call_counts.values()),
                'total_errors': sum(self.error_counts.values()),
                'operations': {}
            }

            # 操作统计
            for operation, times in self.execution_times.items():
                if times:
                    stats['operations'][operation] = {
                        'count': self.call_counts[operation],
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times),
                        'total_time': sum(times)
                    }

            # 系统资源统计
            if self.memory_usage:
                stats['memory'] = {
                    'current': self.memory_usage[-1],
                    'avg': sum(self.memory_usage) / len(self.memory_usage),
                    'max': max(self.memory_usage)
                }

            if self.cpu_usage:
                stats['cpu'] = {
                    'current': self.cpu_usage[-1],
                    'avg': sum(self.cpu_usage) / len(self.cpu_usage),
                    'max': max(self.cpu_usage)
                }

            # 错误统计
            stats['errors'] = dict(self.error_counts)

            return stats


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, enable_system_monitoring: bool = True,
                 monitoring_interval: float = 5.0):
        """
        初始化性能监控器

        Args:
            enable_system_monitoring: 是否启用系统监控
            monitoring_interval: 系统监控间隔（秒）
        """
        self.metrics = PerformanceMetrics()
        self.enable_system_monitoring = enable_system_monitoring
        self.monitoring_interval = monitoring_interval
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()

        if enable_system_monitoring:
            self._start_system_monitoring()

        logger.info("性能监控器初始化完成")

    def _start_system_monitoring(self):
        """启动系统监控线程"""
        self._monitoring_thread = threading.Thread(
            target=self._monitor_system_resources,
            daemon=True
        )
        self._monitoring_thread.start()

    def _monitor_system_resources(self):
        """监控系统资源使用情况"""
        process = psutil.Process()

        while not self._stop_monitoring.wait(self.monitoring_interval):
            try:
                # 监控内存使用
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.metrics.add_memory_usage(memory_mb)

                # 监控CPU使用
                cpu_percent = process.cpu_percent()
                self.metrics.add_cpu_usage(cpu_percent)

            except Exception as e:
                logger.warning(f"系统资源监控失败: {e}")

    @contextmanager
    def measure_time(self, operation: str) -> ContextManager[None]:
        """
        测量操作执行时间的上下文管理器

        Args:
            operation: 操作名称
        """
        start_time = time.time()
        try:
            yield
        except Exception as e:
            self.metrics.increment_error(type(e).__name__)
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.add_execution_time(operation, duration)

    def time_function(self, operation: str = None) -> Callable:
        """
        装饰器：测量函数执行时间

        Args:
            operation: 操作名称，如果为None则使用函数名
        """
        def decorator(func: Callable) -> Callable:
            op_name = operation or f"{func.__module__}.{func.__name__}"

            def wrapper(*args, **kwargs):
                with self.measure_time(op_name):
                    return func(*args, **kwargs)

            return wrapper
        return decorator

    def record_error(self, error: Exception, context: str = None):
        """
        记录错误

        Args:
            error: 异常对象
            context: 错误上下文
        """
        error_type = type(error).__name__
        if context:
            error_type = f"{context}.{error_type}"

        self.metrics.increment_error(error_type)
        logger.error(f"性能监控记录错误: {error_type} - {str(error)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return self.metrics.get_stats()

    def reset_metrics(self):
        """重置性能指标"""
        self.metrics = PerformanceMetrics()
        logger.info("性能指标已重置")

    def shutdown(self):
        """关闭性能监控器"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5.0)

        logger.info("性能监控器已关闭")

    def __del__(self):
        """析构函数"""
        try:
            self.shutdown()
        except:
            pass


# 全局单例实例
_performance_monitor = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例"""
    global _performance_monitor

    if _performance_monitor is None:
        with _monitor_lock:
            if _performance_monitor is None:
                _performance_monitor = PerformanceMonitor()

    return _performance_monitor


def initialize_performance_monitor(enable_system_monitoring: bool = True,
                                   monitoring_interval: float = 5.0) -> PerformanceMonitor:
    """
    初始化性能监控器

    Args:
        enable_system_monitoring: 是否启用系统监控
        monitoring_interval: 系统监控间隔（秒）

    Returns:
        性能监控器实例
    """
    global _performance_monitor

    with _monitor_lock:
        if _performance_monitor is not None:
            _performance_monitor.shutdown()

        _performance_monitor = PerformanceMonitor(
            enable_system_monitoring, monitoring_interval
        )

    return _performance_monitor


# 便捷函数
def measure_time(operation: str):
    """测量时间的装饰器"""
    monitor = get_performance_monitor()
    return monitor.time_function(operation)


def record_performance(operation: str, duration: float):
    """记录性能数据"""
    monitor = get_performance_monitor()
    monitor.metrics.add_execution_time(operation, duration)


def record_error(error: Exception, context: str = None):
    """记录错误"""
    monitor = get_performance_monitor()
    monitor.record_error(error, context)


def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计"""
    monitor = get_performance_monitor()
    return monitor.get_stats()
