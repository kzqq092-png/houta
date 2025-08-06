#!/usr/bin/env python3
"""
性能监控模块

监控系统性能，包括事件处理时间、数据加载性能等。
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    start_time: float
    end_time: float = 0
    duration: float = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def finish(self):
        """完成性能测量"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        return self.duration


class PerformanceMonitor:
    """
    性能监控器

    功能：
    1. 监控事件处理性能
    2. 监控数据加载性能
    3. 收集性能统计信息
    4. 提供性能报告
    """

    def __init__(self, max_metrics: int = 1000):
        """
        初始化性能监控器

        Args:
            max_metrics: 最大保存的指标数量
        """
        self.max_metrics = max_metrics

        # 性能指标存储
        self._metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_metrics))
        self._active_metrics: Dict[str, PerformanceMetric] = {}
        self._lock = threading.Lock()

        # 统计信息
        self._stats = {
            'total_events': 0,
            'total_data_loads': 0,
            'avg_event_time': 0,
            'avg_data_load_time': 0,
            'slow_operations': 0,
            'fast_operations': 0
        }

        # 阈值设置
        self.slow_threshold = 1.0  # 1秒
        self.fast_threshold = 0.1  # 0.1秒

        logger.info("Performance monitor initialized")

    def measure_time(self, name: str = None):
        """测量时间上下文管理器"""
        return TimingContext(self, name or "operation")

    def start_metric(self, name: str, metadata: Dict[str, Any] = None) -> str:
        """
        开始性能测量

        Args:
            name: 指标名称
            metadata: 元数据

        Returns:
            指标ID
        """
        metric_id = f"{name}_{int(time.time() * 1000000)}"

        with self._lock:
            metric = PerformanceMetric(
                name=name,
                start_time=time.time(),
                metadata=metadata or {}
            )
            self._active_metrics[metric_id] = metric

        logger.debug(f"Started metric: {name} ({metric_id})")
        return metric_id

    def end_metric(self, metric_id: str) -> Optional[float]:
        """
        结束性能测量

        Args:
            metric_id: 指标ID

        Returns:
            持续时间（秒）
        """
        with self._lock:
            if metric_id not in self._active_metrics:
                logger.warning(
                    f"Metric {metric_id} not found in active metrics")
                return None

            metric = self._active_metrics[metric_id]
            duration = metric.finish()

            # 移动到历史记录
            self._metrics[metric.name].append(metric)
            del self._active_metrics[metric_id]

            # 更新统计信息
            self._update_stats(metric)

        logger.debug(
            f"Ended metric: {metric.name} ({metric_id}) - {duration:.3f}s")
        return duration

    def measure_event(self, event_name: str, stock_code: str = None):
        """
        事件性能测量装饰器

        Args:
            event_name: 事件名称
            stock_code: 股票代码
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                metadata = {'event_name': event_name}
                if stock_code:
                    metadata['stock_code'] = stock_code

                metric_id = self.start_metric(f"event_{event_name}", metadata)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_metric(metric_id)
            return wrapper
        return decorator

    def measure_data_load(self, data_type: str, stock_code: str = None):
        """
        数据加载性能测量装饰器

        Args:
            data_type: 数据类型
            stock_code: 股票代码
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                metadata = {'data_type': data_type}
                if stock_code:
                    metadata['stock_code'] = stock_code

                metric_id = self.start_metric(
                    f"data_load_{data_type}", metadata)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_metric(metric_id)
            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        with self._lock:
            stats = self._stats.copy()

            # 添加详细统计
            detailed_stats = {}
            for metric_name, metrics in self._metrics.items():
                if metrics:
                    durations = [m.duration for m in metrics]
                    detailed_stats[metric_name] = {
                        'count': len(durations),
                        'avg': statistics.mean(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'median': statistics.median(durations)
                    }

            stats['detailed'] = detailed_stats
            stats['active_metrics'] = len(self._active_metrics)

            return stats

    def get_slow_operations(self, threshold: float = None) -> List[PerformanceMetric]:
        """
        获取慢操作列表

        Args:
            threshold: 时间阈值（秒）

        Returns:
            慢操作列表
        """
        threshold = threshold or self.slow_threshold
        slow_ops = []

        with self._lock:
            for metrics in self._metrics.values():
                for metric in metrics:
                    if metric.duration > threshold:
                        slow_ops.append(metric)

        # 按持续时间排序
        slow_ops.sort(key=lambda x: x.duration, reverse=True)
        return slow_ops

    def get_performance_report(self) -> str:
        """生成性能报告"""
        stats = self.get_stats()
        slow_ops = self.get_slow_operations()

        report = []
        report.append("=" * 60)
        report.append("性能监控报告")
        report.append("=" * 60)

        # 总体统计
        report.append(f"总事件数: {stats['total_events']}")
        report.append(f"总数据加载数: {stats['total_data_loads']}")
        report.append(f"平均事件处理时间: {stats['avg_event_time']:.3f}s")
        report.append(f"平均数据加载时间: {stats['avg_data_load_time']:.3f}s")
        report.append(f"慢操作数: {stats['slow_operations']}")
        report.append(f"快操作数: {stats['fast_operations']}")
        report.append(f"活跃指标数: {stats['active_metrics']}")

        # 详细统计
        if 'detailed' in stats:
            report.append("\n详细统计:")
            for metric_name, metric_stats in stats['detailed'].items():
                report.append(f"  {metric_name}:")
                report.append(f"    数量: {metric_stats['count']}")
                report.append(f"    平均: {metric_stats['avg']:.3f}s")
                report.append(f"    最小: {metric_stats['min']:.3f}s")
                report.append(f"    最大: {metric_stats['max']:.3f}s")
                report.append(f"    中位数: {metric_stats['median']:.3f}s")

        # 慢操作
        if slow_ops:
            report.append(f"\n最慢的{min(10, len(slow_ops))}个操作:")
            for i, op in enumerate(slow_ops[:10]):
                report.append(f"  {i+1}. {op.name}: {op.duration:.3f}s")
                if op.metadata:
                    for key, value in op.metadata.items():
                        report.append(f"     {key}: {value}")

        report.append("=" * 60)
        return "\n".join(report)

    def clear_metrics(self):
        """清理性能指标"""
        with self._lock:
            self._metrics.clear()
            self._active_metrics.clear()
            self._stats = {
                'total_events': 0,
                'total_data_loads': 0,
                'avg_event_time': 0,
                'avg_data_load_time': 0,
                'slow_operations': 0,
                'fast_operations': 0
            }

        logger.info("Performance metrics cleared")

    def _update_stats(self, metric: PerformanceMetric):
        """更新统计信息"""
        # 更新计数
        if metric.name.startswith('event_'):
            self._stats['total_events'] += 1
            # 更新平均事件时间
            total = self._stats['total_events']
            current_avg = self._stats['avg_event_time']
            self._stats['avg_event_time'] = (
                current_avg * (total - 1) + metric.duration) / total

        elif metric.name.startswith('data_load_'):
            self._stats['total_data_loads'] += 1
            # 更新平均数据加载时间
            total = self._stats['total_data_loads']
            current_avg = self._stats['avg_data_load_time']
            self._stats['avg_data_load_time'] = (
                current_avg * (total - 1) + metric.duration) / total

        # 更新快慢操作计数
        if metric.duration > self.slow_threshold:
            self._stats['slow_operations'] += 1
        elif metric.duration < self.fast_threshold:
            self._stats['fast_operations'] += 1


# 全局性能监控器实例
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def measure_performance(name: str, metadata: Dict[str, Any] = None):
    """
    性能测量装饰器

    Args:
        name: 指标名称
        metadata: 元数据
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            metric_id = monitor.start_metric(name, metadata)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_metric(metric_id)
        return wrapper
    return decorator


def measure_event_performance(event_name: str, stock_code: str = None):
    """
    事件性能测量装饰器

    Args:
        event_name: 事件名称
        stock_code: 股票代码
    """
    return get_performance_monitor().measure_event(event_name, stock_code)


def measure_data_load_performance(data_type: str, stock_code: str = None):
    """
    数据加载性能测量装饰器

    Args:
        data_type: 数据类型
        stock_code: 股票代码
    """
    return get_performance_monitor().measure_data_load(data_type, stock_code)


class TimingContext:
    """时间测量上下文管理器"""

    def __init__(self, monitor: PerformanceMonitor, name: str):
        self.monitor = monitor
        self.name = name
        self.start_time = None
        self.metric_id = None

    def __enter__(self):
        self.start_time = time.time()
        self.metric_id = self.monitor.start_metric(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.metric_id:
            self.monitor.end_metric(self.metric_id)
