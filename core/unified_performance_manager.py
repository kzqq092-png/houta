"""
统一性能管理器
整合所有性能监控和优化功能，避免重复代码，提高系统性能
专业级性能管理，对标专业交易软件
"""

import os
import sys
import platform
import time
import threading
import gc
import psutil
import weakref
import logging
import traceback
from typing import Dict, Any, Optional, Callable, List, ContextManager
from contextlib import contextmanager
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QThread

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """性能级别"""
    BASIC = "basic"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ULTRA = "ultra"


class AlertLevel(Enum):
    """警报级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """统一的性能指标"""
    execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    throughput: float = 0.0
    error_count: int = 0
    response_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    operation_name: str = ""
    thread_id: int = 0
    process_id: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.thread_id == 0:
            self.thread_id = threading.get_ident()
        if self.process_id == 0:
            self.process_id = os.getpid()


@dataclass
class PerformanceAlert:
    """性能警报"""
    level: AlertLevel
    message: str
    timestamp: datetime
    metrics: PerformanceMetrics
    threshold: float
    actual_value: float


class UnifiedCache:
    """统一缓存管理器 - 专业级缓存系统"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600, enable_stats: bool = True):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_stats = enable_stats
        self._cache = {}
        self._access_times = {}
        self._access_counts = defaultdict(int)
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._lock = threading.RLock()

    def get(self, key: str, default=None):
        """获取缓存值"""
        with self._lock:
            if key in self._cache and not self._is_expired(key):
                self._access_times[key] = time.time()
                if self.enable_stats:
                    self._access_counts[key] += 1
                    self._hit_count += 1
                return self._cache[key]
            else:
                if self.enable_stats:
                    self._miss_count += 1
                return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 清理过期项
            self._cleanup_expired()

            # 如果缓存已满，使用LRU策略移除最旧的项
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            self._cache[key] = value
            self._access_times[key] = time.time()
            if ttl is not None:
                # 支持单独设置TTL
                self._cache[f"{key}_ttl"] = ttl

    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._access_times:
            return True

        # 检查是否有单独的TTL设置
        ttl_key = f"{key}_ttl"
        ttl = self._cache.get(ttl_key, self.ttl_seconds)

        return time.time() - self._access_times[key] > ttl

    def _cleanup_expired(self):
        """清理过期项"""
        expired_keys = [key for key in self._access_times
                        if self._is_expired(key)]
        for key in expired_keys:
            self._remove(key)

    def _evict_lru(self):
        """使用LRU策略移除最旧的项"""
        if not self._access_times:
            return

        oldest_key = min(self._access_times, key=self._access_times.get)
        self._remove(oldest_key)
        self._eviction_count += 1

    def _remove(self, key: str):
        """移除缓存项"""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
        self._access_counts.pop(key, None)
        # 同时移除TTL设置
        ttl_key = f"{key}_ttl"
        self._cache.pop(ttl_key, None)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._access_counts.clear()
            self._hit_count = 0
            self._miss_count = 0
            self._eviction_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计 - 专业级统计信息"""
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total if total > 0 else 0

            # 计算热点数据
            hot_keys = sorted(self._access_counts.items(),
                              key=lambda x: x[1], reverse=True)[:10]

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
                'eviction_count': self._eviction_count,
                'hot_keys': hot_keys,
                'memory_usage_mb': self._estimate_memory_usage(),
                'efficiency_score': self._calculate_efficiency_score()
            }

    def _estimate_memory_usage(self) -> float:
        """估算内存使用量"""
        try:
            import sys
            total_size = 0
            for key, value in self._cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return total_size / 1024 / 1024  # MB
        except Exception:
            return 0.0

    def _calculate_efficiency_score(self) -> float:
        """计算缓存效率评分 (0-100)"""
        if self._hit_count + self._miss_count == 0:
            return 0.0

        hit_rate = self._hit_count / (self._hit_count + self._miss_count)
        utilization = len(self._cache) / self.max_size
        eviction_penalty = max(0, 1 - self._eviction_count / max(1, len(self._cache)))

        return (hit_rate * 0.5 + utilization * 0.3 + eviction_penalty * 0.2) * 100


class UnifiedPerformanceManager(QObject):
    """统一性能管理器 - 专业级性能管理系统"""

    # 专业级信号
    performance_updated = pyqtSignal(dict)  # 性能指标更新
    alert_triggered = pyqtSignal(str, str)  # 警报触发 (level, message)
    threshold_exceeded = pyqtSignal(str, float, float)  # 阈值超出 (metric, threshold, actual)
    system_health_changed = pyqtSignal(str)  # 系统健康状态变化

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        super().__init__()
        self._initialized = True

        # 专业级配置
        self.performance_level = PerformanceLevel.PROFESSIONAL
        self.cache = UnifiedCache()
        self.metrics_history = deque(maxlen=10000)  # 增加历史记录容量
        self.operation_times = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts = defaultdict(int)
        self.alert_history = deque(maxlen=1000)

        # 专业级阈值设置
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 5.0,  # 秒
            'error_rate': 0.05,    # 5%
            'cache_hit_rate': 0.8  # 80%
        }

        # 监控线程和定时器
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._callbacks = []
        self._qt_timer = None

        # 系统进程信息
        try:
            self._process = psutil.Process()
        except Exception as e:
            logger.warning(f"无法获取进程信息: {e}")
            self._process = None

        # 启动监控
        self.start_monitoring()
        logger.info("统一性能管理器初始化完成 - 专业级模式")

    def start_monitoring(self):
        """启动性能监控 - 支持Qt信号和多线程"""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitoring_thread = threading.Thread(
                target=self._monitor_system_resources,
                daemon=True,
                name="PerformanceMonitor"
            )
            self._monitoring_thread.start()

        # 启动Qt定时器用于UI更新
        if self._qt_timer is None:
            self._qt_timer = QTimer()
            self._qt_timer.timeout.connect(self._emit_performance_update)
            self._qt_timer.start(1000)  # 每秒更新一次UI

    def stop_monitoring(self):
        """停止性能监控"""
        self._stop_monitoring.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)

        if self._qt_timer:
            self._qt_timer.stop()
            self._qt_timer = None

    def _monitor_system_resources(self):
        """监控系统资源 - 专业级监控"""
        while not self._stop_monitoring.wait(10.0):  # 每2秒监控一次，提高精度
            try:
                if self._process is None:
                    continue

                # 获取系统指标
                memory_info = self._process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = self._process.cpu_percent()

                # 获取磁盘使用率
                disk_usage = 0.0
                try:
                    disk_usage = psutil.disk_usage('/').percent
                except Exception:
                    try:
                        disk_usage = psutil.disk_usage('C:').percent
                    except Exception:
                        pass

                # 获取缓存统计
                cache_stats = self.cache.get_stats()

                # 创建性能指标
                metrics = PerformanceMetrics(
                    memory_usage_mb=memory_mb,
                    cpu_usage_percent=cpu_percent,
                    disk_usage_percent=disk_usage,
                    cache_hit_rate=cache_stats['hit_rate'],
                    operation_name="system_monitor"
                )

                self.metrics_history.append(metrics)

                # 检查阈值并触发警报
                self._check_thresholds(metrics)

                # 自动内存清理
                if memory_mb > 1500:  # 内存使用超过1GB
                    collected = self.cleanup_memory()
                    if collected > 0:
                        logger.info(f"自动内存清理完成，回收对象: {collected}")

                # 执行回调函数
                for callback in self._callbacks:
                    try:
                        callback("system_monitor", metrics)
                    except Exception as e:
                        logger.warning(f"性能回调执行失败: {e}")

            except Exception as e:
                logger.warning(f"性能监控失败: {e}")

    def _check_thresholds(self, metrics: PerformanceMetrics):
        """检查阈值并触发警报"""
        checks = [
            ('cpu_usage', metrics.cpu_usage_percent, "CPU使用率"),
            ('memory_usage', metrics.memory_usage_mb / 1024 * 100, "内存使用率"),  # 转换为百分比
            ('disk_usage', metrics.disk_usage_percent, "磁盘使用率"),
        ]

        for metric_name, value, display_name in checks:
            threshold = self.thresholds.get(metric_name, 100)
            if value > threshold:
                alert = PerformanceAlert(
                    level=AlertLevel.WARNING if value < threshold * 1.2 else AlertLevel.CRITICAL,
                    message=f"{display_name}过高: {value:.1f}% (阈值: {threshold}%)",
                    timestamp=datetime.now(),
                    metrics=metrics,
                    threshold=threshold,
                    actual_value=value
                )
                self.alert_history.append(alert)
                self.alert_triggered.emit(alert.level.value, alert.message)
                self.threshold_exceeded.emit(metric_name, threshold, value)

    def _emit_performance_update(self):
        """发送性能更新信号"""
        if self.metrics_history:
            latest_metrics = self.metrics_history[-1]
            stats = self.get_performance_stats()
            self.performance_updated.emit(stats)

    @contextmanager
    def measure_operation(self, operation_name: str) -> ContextManager[PerformanceMetrics]:
        """测量操作性能的上下文管理器 - 增强版"""
        start_time = time.time()
        start_memory = 0

        if self._process:
            try:
                start_memory = self._process.memory_info().rss / 1024 / 1024
            except Exception:
                pass

        metrics = PerformanceMetrics(operation_name=operation_name)

        try:
            yield metrics
        except Exception as e:
            self.error_counts[f"{operation_name}.{type(e).__name__}"] += 1
            metrics.error_count = 1
            raise
        finally:
            # 计算性能指标
            metrics.execution_time = time.time() - start_time

            if self._process:
                try:
                    end_memory = self._process.memory_info().rss / 1024 / 1024
                    metrics.memory_usage_mb = end_memory - start_memory
                    metrics.cpu_usage_percent = self._process.cpu_percent()
                except Exception:
                    pass

            # 记录操作时间
            self.operation_times[operation_name].append(metrics.execution_time)
            self.metrics_history.append(metrics)

            # 执行回调
            for callback in self._callbacks:
                try:
                    callback(operation_name, metrics)
                except Exception as e:
                    logger.warning(f"性能回调执行失败: {e}")

    def cleanup_memory(self, force: bool = False) -> int:
        """清理内存 - 专业级内存管理"""
        try:
            # 清理缓存
            if force or len(self.cache._cache) > self.cache.max_size * 0.8:
                self.cache._cleanup_expired()

            # 清理历史记录
            if force or len(self.metrics_history) > 8000:
                # 保留最近的5000条记录
                while len(self.metrics_history) > 5000:
                    self.metrics_history.popleft()

            # 清理操作时间记录
            for operation, times in self.operation_times.items():
                if len(times) > 500:
                    # 保留最近的300条记录
                    while len(times) > 300:
                        times.popleft()

            # 强制垃圾回收
            collected = gc.collect()

            # 记录内存清理
            if collected > 0:
                logger.info(f"内存清理完成，回收对象: {collected}")

            return collected

        except Exception as e:
            logger.error(f"内存清理失败: {e}")
            return 0

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息 - 专业级统计"""
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': 0,
                'total_operations': sum(len(times) for times in self.operation_times.values()),
                'total_errors': sum(self.error_counts.values()),
                'system_health': self._calculate_system_health(),
                'operations': {},
                'cache_stats': self.cache.get_stats(),
                'alerts': {
                    'total': len(self.alert_history),
                    'recent': [
                        {
                            'level': alert.level.value,
                            'message': alert.message,
                            'timestamp': alert.timestamp.isoformat()
                        }
                        for alert in list(self.alert_history)[-10:]  # 最近10条警报
                    ]
                }
            }

            # 计算运行时间
            if self.metrics_history:
                first_metric = self.metrics_history[0]
                stats['uptime_seconds'] = (datetime.now() - first_metric.timestamp).total_seconds()

            # 操作统计
            for operation, times in self.operation_times.items():
                if times:
                    times_list = list(times)
                    stats['operations'][operation] = {
                        'count': len(times_list),
                        'avg_time': sum(times_list) / len(times_list),
                        'min_time': min(times_list),
                        'max_time': max(times_list),
                        'total_time': sum(times_list),
                        'p95_time': self._calculate_percentile(times_list, 95),
                        'p99_time': self._calculate_percentile(times_list, 99)
                    }

            # 系统资源统计
            if self.metrics_history:
                recent_metrics = list(self.metrics_history)[-100:]  # 最近100条记录

                memory_values = [m.memory_usage_mb for m in recent_metrics if m.memory_usage_mb > 0]
                cpu_values = [m.cpu_usage_percent for m in recent_metrics if m.cpu_usage_percent > 0]

                if memory_values:
                    stats['memory'] = {
                        'current': memory_values[-1],
                        'avg': sum(memory_values) / len(memory_values),
                        'max': max(memory_values),
                        'min': min(memory_values)
                    }

                if cpu_values:
                    stats['cpu'] = {
                        'current': cpu_values[-1],
                        'avg': sum(cpu_values) / len(cpu_values),
                        'max': max(cpu_values),
                        'min': min(cpu_values)
                    }

            # 错误统计
            stats['errors'] = dict(self.error_counts)

            # 性能趋势分析
            stats['trends'] = self._analyze_performance_trends()

            return stats

        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _calculate_system_health(self) -> str:
        """计算系统健康状态"""
        if not self.metrics_history:
            return "unknown"

        recent_alerts = [alert for alert in self.alert_history
                         if (datetime.now() - alert.timestamp).seconds < 300]  # 最近5分钟

        critical_alerts = [alert for alert in recent_alerts
                           if alert.level == AlertLevel.CRITICAL]
        warning_alerts = [alert for alert in recent_alerts
                          if alert.level == AlertLevel.WARNING]

        if critical_alerts:
            return "critical"
        elif len(warning_alerts) >= 3:
            return "warning"
        elif warning_alerts:
            return "caution"
        else:
            return "healthy"

    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """分析性能趋势"""
        if len(self.metrics_history) < 10:
            return {}

        recent_metrics = list(self.metrics_history)[-50:]  # 最近50条记录

        # 分析内存趋势
        memory_values = [m.memory_usage_mb for m in recent_metrics if m.memory_usage_mb > 0]
        memory_trend = "stable"
        if len(memory_values) >= 10:
            first_half = memory_values[:len(memory_values)//2]
            second_half = memory_values[len(memory_values)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg * 1.1:
                memory_trend = "increasing"
            elif second_avg < first_avg * 0.9:
                memory_trend = "decreasing"

        # 分析响应时间趋势
        response_times = []
        for operation, times in self.operation_times.items():
            if times:
                response_times.extend(list(times)[-20:])  # 每个操作最近20次

        response_trend = "stable"
        if len(response_times) >= 20:
            first_half = response_times[:len(response_times)//2]
            second_half = response_times[len(response_times)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg * 1.2:
                response_trend = "degrading"
            elif second_avg < first_avg * 0.8:
                response_trend = "improving"

        return {
            'memory_trend': memory_trend,
            'response_time_trend': response_trend,
            'error_rate_trend': self._calculate_error_rate_trend()
        }

    def _calculate_error_rate_trend(self) -> str:
        """计算错误率趋势"""
        if not self.metrics_history:
            return "stable"

        recent_metrics = list(self.metrics_history)[-100:]
        total_operations = len(recent_metrics)
        error_operations = sum(1 for m in recent_metrics if m.error_count > 0)

        error_rate = error_operations / total_operations if total_operations > 0 else 0

        if error_rate > 0.1:  # 10%以上错误率
            return "high"
        elif error_rate > 0.05:  # 5%以上错误率
            return "elevated"
        else:
            return "low"

    def register_performance_callback(self, callback: Callable[[str, PerformanceMetrics], None]):
        """注册性能回调函数"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_performance_callback(self, callback: Callable):
        """注销性能回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def set_performance_level(self, level: PerformanceLevel):
        """设置性能级别"""
        self.performance_level = level

        # 根据性能级别调整监控频率和缓存大小
        if level == PerformanceLevel.ULTRA:
            self.cache.max_size = 2000
            # 可以调整监控频率等参数
        elif level == PerformanceLevel.PROFESSIONAL:
            self.cache.max_size = 1000
        elif level == PerformanceLevel.STANDARD:
            self.cache.max_size = 500
        else:  # BASIC
            self.cache.max_size = 200

        logger.info(f"性能级别已设置为: {level.value}")

    def set_threshold(self, metric: str, value: float):
        """设置性能阈值"""
        self.thresholds[metric] = value
        logger.info(f"性能阈值已设置: {metric} = {value}")

    def get_alerts(self, level: Optional[AlertLevel] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取警报列表"""
        alerts = list(self.alert_history)

        if level:
            alerts = [alert for alert in alerts if alert.level == level]

        alerts = alerts[-limit:]  # 获取最近的N条

        return [
            {
                'level': alert.level.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'threshold': alert.threshold,
                'actual_value': alert.actual_value
            }
            for alert in alerts
        ]

    def export_performance_report(self, filepath: str = None) -> str:
        """导出性能报告"""
        import json

        if filepath is None:
            filepath = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            'generated_at': datetime.now().isoformat(),
            'performance_stats': self.get_performance_stats(),
            'alerts': self.get_alerts(),
            'system_info': {
                'python_version': sys.version,
                'platform': platform.platform(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024  # GB
            }
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"性能报告已导出: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"导出性能报告失败: {e}")
            raise

    def __del__(self):
        """析构函数"""
        try:
            self.stop_monitoring()
        except Exception:
            pass


# 全局实例管理
_performance_manager = None
_manager_lock = threading.Lock()


def get_performance_manager() -> UnifiedPerformanceManager:
    """获取性能管理器单例"""
    global _performance_manager

    if _performance_manager is None:
        with _manager_lock:
            if _performance_manager is None:
                _performance_manager = UnifiedPerformanceManager()

    return _performance_manager


def performance_monitor(operation_name: str):
    """性能监控装饰器 - 专业级装饰器"""
    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_performance_manager()
            with manager.measure_operation(operation_name or func.__name__):
                return func(*args, **kwargs)

        return wrapper
    return decorator


def cached_operation(cache_key_func: Optional[Callable] = None, ttl: int = 3600):
    """缓存操作装饰器 - 专业级缓存"""
    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_performance_manager()

            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # 默认缓存键生成策略
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = "|".join(key_parts)

            # 尝试从缓存获取
            cached_result = manager.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            with manager.measure_operation(f"cached_{func.__name__}"):
                result = func(*args, **kwargs)
                manager.cache.set(cache_key, result, ttl)
                return result

        return wrapper
    return decorator


# 兼容性函数 - 保持向后兼容
def monitor_performance(name: str = None, threshold_ms: int = 1000):
    """兼容性装饰器 - 重定向到统一性能管理器"""
    return performance_monitor(name)


# 导出的公共接口
__all__ = [
    'UnifiedPerformanceManager',
    'PerformanceMetrics',
    'PerformanceLevel',
    'PerformanceAlert',
    'AlertLevel',
    'get_performance_manager',
    'performance_monitor',
    'cached_operation',
    'monitor_performance'  # 兼容性
]
