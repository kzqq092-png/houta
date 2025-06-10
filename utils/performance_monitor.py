"""
性能监控模块

提供系统性能监控和优化功能
"""

import os
import time
import psutil
import threading
import traceback
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QThread
from contextlib import contextmanager


class PerformanceMonitor(QObject):
    """性能监控器类，负责监控系统性能指标"""

    performance_updated = pyqtSignal(dict)  # 性能指标更新信号
    alert_triggered = pyqtSignal(str)       # 性能警报信号

    def __init__(self, cpu_threshold=80, memory_threshold=80, disk_threshold=90, log_manager=None):
        """初始化性能监控器

        Args:
            cpu_threshold (float): CPU使用率阈值（百分比）
            memory_threshold (float): 内存使用率阈值（百分比）
            disk_threshold (float): 磁盘使用率阈值（百分比）
            log_manager (LogManager): 日志管理器实例
        """
        super().__init__()

        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.log_manager = log_manager

        self.is_monitoring = False
        self.monitor_thread = None
        self.check_timer = None
        self._metrics = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'response_time': 0,
            'response_times': {}
        }

    def start_monitoring(self):
        """启动性能监控"""
        if self.is_monitoring:
            if self.log_manager:
                self.log_manager.warning("性能监控已在运行中")
            return

        try:
            # 初始化性能指标
            self._metrics = {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'response_time': 0,
                'response_times': {}
            }

            # 创建监控线程
            self.monitor_thread = QThread()
            self.moveToThread(self.monitor_thread)
            self.monitor_thread.started.connect(self.monitor_performance)
            self.monitor_thread.start()

            # 创建性能检查定时器
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._check_performance)
            self.check_timer.start(1000)  # 每秒检查一次

            self.is_monitoring = True
            if self.log_manager:
                self.log_manager.info("性能监控启动成功")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"启动性能监控失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            self.is_monitoring = False
            raise

    def stop_monitoring(self):
        """停止性能监控"""
        try:
            if self.check_timer:
                self.check_timer.stop()
                self.check_timer = None

            if self.monitor_thread:
                self.monitor_thread.quit()
                self.monitor_thread.wait()
                self.monitor_thread = None

            self.is_monitoring = False
            if self.log_manager:
                self.log_manager.info("性能监控已停止")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"停止性能监控失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            raise

    def monitor_performance(self):
        """监控性能指标"""
        while self.is_monitoring:
            try:
                self._metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
                self._metrics['memory_usage'] = psutil.virtual_memory().percent
                self._metrics['disk_usage'] = psutil.disk_usage('/').percent

                self.performance_updated.emit(self._metrics.copy())
                time.sleep(1)

            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"监控性能指标失败: {str(e)}")
                time.sleep(5)  # 发生错误时等待5秒后重试

    def _check_performance(self):
        """检查性能指标是否超过阈值"""
        try:
            if self._metrics['cpu_usage'] > self.cpu_threshold:
                self.alert_triggered.emit(
                    f"CPU使用率过高: {self._metrics['cpu_usage']}%")

            if self._metrics['memory_usage'] > self.memory_threshold:
                self.alert_triggered.emit(
                    f"内存使用率过高: {self._metrics['memory_usage']}%")

            if self._metrics['disk_usage'] > self.disk_threshold:
                self.alert_triggered.emit(
                    f"磁盘使用率过高: {self._metrics['disk_usage']}%")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"检查性能指标失败: {str(e)}")

    def get_metrics(self) -> dict:
        """获取当前性能指标

        Returns:
            dict: 包含CPU、内存、磁盘使用率的字典
        """
        return self._metrics.copy()


def monitor_performance(name: str = None, threshold_ms: int = 1000):
    """
    性能监控装饰器：用于监控函数/方法的执行耗时，超阈值自动日志告警。
    Args:
        name (str): 监控名称（可选）
        threshold_ms (int): 超过该毫秒数则记录告警
    """
    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = (time.time() - start) * 1000  # ms
            func_name = name or func.__name__
            if elapsed > threshold_ms:
                logging.warning(f"[性能监控] {func_name} 执行耗时 {elapsed:.1f} ms 超过阈值 {threshold_ms} ms")
            else:
                logging.info(f"[性能监控] {func_name} 执行耗时 {elapsed:.1f} ms")
            return result
        return wrapper
    return decorator
