"""
性能监控模块
"""
import time
import logging
import functools
import tracemalloc
import psutil
from typing import Dict, Any, Optional, Callable, Union
from contextlib import contextmanager
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from datetime import datetime
import sqlite3
from config.performance_config import (
    PERFORMANCE_THRESHOLDS,
    PERFORMANCE_CONFIG,
    DECORATOR_CONFIG
)
from core.logger import LogManager

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """性能监控类"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.metrics = {}
        self._thresholds = {
            "数据加载": 1.0,  # 秒
            "指标计算": 0.5,
            "图表更新": 0.2,
            "策略回测": 2.0,
            "UI更新": 0.1
        }
        
    @contextmanager
    def start_operation(self, operation: str):
        """开始监控操作
        
        Args:
            operation: 操作名称
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self._update_metrics(operation, duration)
            
    def _update_metrics(self, operation: str, duration: float):
        """更新性能指标
        
        Args:
            operation: 操作名称
            duration: 持续时间
        """
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'max_time': 0,
                'min_time': float('inf')
            }
            
        metrics = self.metrics[operation]
        metrics['count'] += 1
        metrics['total_time'] += duration
        metrics['avg_time'] = metrics['total_time'] / metrics['count']
        metrics['max_time'] = max(metrics['max_time'], duration)
        metrics['min_time'] = min(metrics['min_time'], duration)
        
        # 检查是否超过阈值
        if operation in self._thresholds and duration > self._thresholds[operation]:
            from utils.logger import log_manager
            log_manager.log(
                f"性能警告: {operation} 操作耗时 {duration:.3f}秒，超过阈值 "
                f"{self._thresholds[operation]:.3f}秒",
                level="WARNING"
            )
            
    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取性能指标
        
        Args:
            operation: 操作名称，如果为None则返回所有指标
            
        Returns:
            性能指标字典
        """
        if operation:
            return self.metrics.get(operation, {})
        return self.metrics
        
    def get_metrics_report(self) -> Dict[str, Dict[str, float]]:
        """获取性能指标报告
        
        Returns:
            性能指标报告字典
        """
        return {
            op: {
                'avg_time': metrics['avg_time'],
                'max_time': metrics['max_time'],
                'min_time': metrics['min_time'],
                'total_time': metrics['total_time'],
                'count': metrics['count']
            }
            for op, metrics in self.metrics.items()
        }
        
    def clear_metrics(self):
        """清除性能指标"""
        self.metrics.clear()
        
    def get_threshold(self, operation: str) -> float:
        """获取操作的性能阈值
        
        Args:
            operation: 操作名称
            
        Returns:
            性能阈值
        """
        return self._thresholds.get(operation, float('inf'))
        
    def set_threshold(self, operation: str, threshold: float):
        """设置操作的性能阈值
        
        Args:
            operation: 操作名称
            threshold: 性能阈值
        """
        self._thresholds[operation] = threshold
        
    def create_widget(self) -> QWidget:
        """创建性能监控控件
        
        Returns:
            性能监控控件
        """
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 创建性能指标表格
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "操作", "平均时间(ms)", "最大时间(ms)", 
            "最小时间(ms)", "调用次数"
        ])
        
        # 填充数据
        metrics = self.get_metrics_report()
        table.setRowCount(len(metrics))
        
        for i, (operation, data) in enumerate(metrics.items()):
            table.setItem(i, 0, QTableWidgetItem(operation))
            table.setItem(i, 1, QTableWidgetItem(f"{data['avg_time']*1000:.1f}"))
            table.setItem(i, 2, QTableWidgetItem(f"{data['max_time']*1000:.1f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{data['min_time']*1000:.1f}"))
            table.setItem(i, 4, QTableWidgetItem(str(data['count'])))
            
        # 调整列宽
        table.resizeColumnsToContents()
        
        layout.addWidget(table)
        widget.setLayout(layout)
        
        return widget

class PerformanceMetric:
    """性能指标类"""
    def __init__(self, name: str):
        self.name = name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.memory_start = 0
        self.memory_end = 0
        self.memory_diff = 0
        self.cpu_percent = 0
        self.exception: Optional[Exception] = None
        
        if DECORATOR_CONFIG['track_memory']:
            tracemalloc.start()
            self.memory_start = tracemalloc.get_traced_memory()[0]
            
    def stop(self) -> None:
        """停止性能指标收集"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        
        if DECORATOR_CONFIG['track_memory']:
            self.memory_end = tracemalloc.get_traced_memory()[0]
            self.memory_diff = self.memory_end - self.memory_start
            tracemalloc.stop()
            
        if DECORATOR_CONFIG['track_cpu']:
            self.cpu_percent = psutil.Process().cpu_percent()
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'timestamp': datetime.now().isoformat(),
            'duration': self.duration,
            'memory_diff': self.memory_diff,
            'cpu_percent': self.cpu_percent,
            'exception': str(self.exception) if self.exception else None
        }

def save_metric(metric: PerformanceMetric) -> None:
    """保存性能指标到数据库"""
    if not PERFORMANCE_CONFIG['collect_metrics']:
        return
        
    try:
        conn = sqlite3.connect(PERFORMANCE_CONFIG['metrics_db'])
        cursor = conn.cursor()
        
        # 创建性能指标表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                timestamp TEXT,
                duration REAL,
                memory_diff INTEGER,
                cpu_percent REAL,
                exception TEXT
            )
        ''')
        
        # 插入性能指标数据
        metric_dict = metric.to_dict()
        cursor.execute('''
            INSERT INTO performance_metrics 
            (name, timestamp, duration, memory_diff, cpu_percent, exception)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            metric_dict['name'],
            metric_dict['timestamp'],
            metric_dict['duration'],
            metric_dict['memory_diff'],
            metric_dict['cpu_percent'],
            metric_dict['exception']
        ))
        
        # 清理过期数据
        retention_days = PERFORMANCE_CONFIG['metrics_retention']
        cursor.execute('''
            DELETE FROM performance_metrics 
            WHERE timestamp < datetime('now', ?)
        ''', (f'-{retention_days} days',))
        
        conn.commit()
    except Exception as e:
        logger.error(f"保存性能指标失败: {e}")
    finally:
        conn.close()

def check_performance(metric: PerformanceMetric) -> None:
    """检查性能指标是否超过阈值"""
    if not PERFORMANCE_CONFIG['alert_enabled']:
        return
        
    threshold = PERFORMANCE_THRESHOLDS.get(metric.name)
    if threshold and metric.duration > threshold:
        alert_msg = (
            f"性能警告: {metric.name} 执行时间 {metric.duration:.2f}s "
            f"超过阈值 {threshold}s"
        )
        
        # 记录告警日志
        if 'log' in PERFORMANCE_CONFIG['alert_channels']:
            logger.warning(alert_msg)
            
        # TODO: 添加其他告警通道（如UI提示）的实现

def monitor_performance(func: Callable) -> Callable:
    """性能监控装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not PERFORMANCE_CONFIG['enable_monitoring']:
            return func(*args, **kwargs)
            
        metric = PerformanceMetric(func.__name__)
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if DECORATOR_CONFIG['track_exceptions']:
                metric.exception = e
            raise
        finally:
            metric.stop()
            check_performance(metric)
            save_metric(metric)
            
    return wrapper

# 创建全局性能监控器实例
performance_monitor = PerformanceMonitor() 