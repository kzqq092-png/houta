"""
性能监控工具

提供应用程序性能监控、指标收集和自动调优功能。
"""

import time
import threading
import logging
import os
import json
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import psutil
import numpy as np
import functools
import asyncio
from enum import Enum, auto

from utils.trace_context import get_trace_id

logger = logging.getLogger(__name__)


class TuningDirection(Enum):
    """调优方向"""
    STABLE = auto()
    INCREASE = auto()
    DECREASE = auto()


@dataclass
class TuningState:
    """单个参数的调优状态"""
    value: Any
    direction: TuningDirection = TuningDirection.STABLE
    momentum: int = 0  # 连续同向调整的次数
    last_metric: float = 0.0  # 上次调优后的性能指标


@dataclass
class PerformanceStats:
    """性能统计数据"""
    name: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    p90_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    std_dev: float = 0.0
    timestamps: List[float] = field(default_factory=list)
    durations: List[float] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def add_measurement(self, duration: float):
        """添加一次测量结果"""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.timestamps.append(time.time())
        self.durations.append(duration)
        self.last_updated = time.time()

        # 限制存储的数据量
        max_samples = 1000
        if len(self.durations) > max_samples:
            self.timestamps = self.timestamps[-max_samples:]
            self.durations = self.durations[-max_samples:]

        # 更新统计数据
        self._update_stats()

    def _update_stats(self):
        """更新统计数据"""
        if self.count == 0:
            return

        self.avg_time = self.total_time / self.count

        if len(self.durations) > 0:
            self.median_time = statistics.median(self.durations)

            if len(self.durations) > 1:
                self.std_dev = statistics.stdev(self.durations)

            if len(self.durations) >= 10:
                self.p90_time = np.percentile(self.durations, 90)
                self.p95_time = np.percentile(self.durations, 95)
                self.p99_time = np.percentile(self.durations, 99)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'count': self.count,
            'total_time': round(self.total_time, 3),
            'min_time': round(self.min_time, 3) if self.min_time != float('inf') else 0,
            'max_time': round(self.max_time, 3),
            'avg_time': round(self.avg_time, 3),
            'median_time': round(self.median_time, 3),
            'p90_time': round(self.p90_time, 3),
            'p95_time': round(self.p95_time, 3),
            'p99_time': round(self.p99_time, 3),
            'std_dev': round(self.std_dev, 3),
            'last_updated': self.last_updated
        }


class PerformanceMonitor:
    """
    性能监控器

    功能：
    1. 测量函数执行时间
    2. 收集性能指标
    3. 自动调整性能参数
    4. 生成性能报告
    """

    def __init__(self, auto_tune: bool = True, monitor_interval: int = 180):
        """
        初始化性能监控器

    Args:
            auto_tune: 是否启用自动调优
            monitor_interval: 监控间隔（秒）
        """
        self.auto_tune = auto_tune
        self.monitor_interval = monitor_interval

        # 性能指标
        self.stats: Dict[str, PerformanceStats] = {}
        self.stats_lock = threading.Lock()

        # 资源使用情况
        self.resource_stats = {
            'cpu': deque(maxlen=60),  # 存储1分钟的数据
            'memory': deque(maxlen=60),
            'disk_io': deque(maxlen=60),
            'network': deque(maxlen=60)
        }

        # 调优参数 - 使用TuningState进行管理
        self.tuning_params: Dict[str, TuningState] = {
            'thread_pool_size': TuningState(8),
            'cache_size': TuningState(1000),
            'batch_size': TuningState(50),
            'update_interval_ms': TuningState(50),
            'progressive_loading': TuningState(True),
            'preload_depth': TuningState(2)
        }

        # 调优历史
        self.tuning_history = []

        # 监控线程
        self.monitor_thread = None
        self.is_running = False

        # 调优回调
        self.tuning_callbacks: Dict[str, Callable] = {}

        # 指标导出
        self.export_path = 'logs/performance_metrics.json'

        # 系统信息
        self.system_info = self._get_system_info()

        logger.info(f"性能监控器初始化完成 - 自动调优: {auto_tune}")

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        info = {}
        try:
            info['cpu_count'] = psutil.cpu_count(
                logical=False) or psutil.cpu_count()
            info['cpu_count_logical'] = psutil.cpu_count()
            mem = psutil.virtual_memory()
            info['memory_total'] = mem.total
            info['memory_total_gb'] = round(mem.total / (1024**3), 2)
            info['platform'] = os.name

            # 检测是否为低性能设备
            info['is_low_end'] = (info['cpu_count'] <
                                  4 or info['memory_total_gb'] < 8)
            info['is_high_end'] = (info['cpu_count'] >=
                                   8 and info['memory_total_gb'] >= 16)

            # 基于系统信息的默认参数
            if info['is_high_end']:
                self.tuning_params['thread_pool_size'].value = min(
                    info['cpu_count'] * 2, 16)
                self.tuning_params['cache_size'].value = 2000
                self.tuning_params['batch_size'].value = 100
                self.tuning_params['update_interval_ms'].value = 10
                self.tuning_params['preload_depth'].value = 3
            elif info['is_low_end']:
                self.tuning_params['thread_pool_size'].value = min(
                    info['cpu_count'], 4)
                self.tuning_params['cache_size'].value = 500
                self.tuning_params['batch_size'].value = 20
                self.tuning_params['update_interval_ms'].value = 200
                self.tuning_params['preload_depth'].value = 1
            else:
                # 中等配置
                self.tuning_params['thread_pool_size'].value = min(
                    info['cpu_count'] + 2, 8)
                self.tuning_params['cache_size'].value = 1000
                self.tuning_params['batch_size'].value = 50
                self.tuning_params['update_interval_ms'].value = 50
                self.tuning_params['preload_depth'].value = 2

        except Exception as e:
            logger.warning(f"获取系统信息失败: {e}")
            # 使用默认值
            info['cpu_count'] = 8
            info['memory_total_gb'] = 8
            info['is_low_end'] = False
            info['is_high_end'] = False

        return info

    def start(self):
        """启动监控"""
        if self.is_running:
            return

        self.is_running = True

        # 启动监控线程
        if self.auto_tune:
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="PerformanceMonitor",
                daemon=True
            )
            self.monitor_thread.start()
            logger.info("性能监控线程已启动")

    def stop(self):
        """停止监控"""
        if not self.is_running:
            return

        self.is_running = False

        # 等待监控线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        # 导出最终指标
        self.export_metrics()

        logger.info("性能监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集资源使用情况
                self._collect_resource_stats()

                # 自动调优
                if self.auto_tune:
                    metrics = self._get_tuning_metrics()
                    self._auto_tune(metrics)

                # 等待下一次监控
                time.sleep(self.monitor_interval)

            except Exception as e:
                logger.error(f"监控循环出错: {e}", exc_info=True)
                time.sleep(5)  # 出现错误时等待，避免日志刷屏

    def _collect_resource_stats(self):
        """收集资源使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.resource_stats['cpu'].append({'percent': cpu_percent})

            # 内存使用
            mem = psutil.virtual_memory()
            self.resource_stats['memory'].append({
                'percent': mem.percent,
                'used': mem.used,
                'total': mem.total
            })

            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            self.resource_stats['disk_io'].append({
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes
            })

            # 网络IO
            net_io = psutil.net_io_counters()
            self.resource_stats['network'].append({
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            })

            logger.debug(
                f"资源使用情况: CPU={cpu_percent:.1f}%, MEM={mem.percent:.1f}%")

        except Exception as e:
            logger.warning(f"收集资源使用情况失败: {e}")

    def _get_tuning_metrics(self) -> Dict[str, Any]:
        """获取用于调优的关键性能指标"""
        metrics = {
            'cpu_usage': np.mean([s['percent'] for s in self.resource_stats['cpu'] if s]) if self.resource_stats['cpu'] else 0,
            'memory_usage': np.mean([s['percent'] for s in self.resource_stats['memory'] if s]) if self.resource_stats['memory'] else 0,
        }

        # 获取特定操作的性能指标
        render_stats = self.get_stats("ChartWidget.render")
        if render_stats:
            metrics['chart_render_p95'] = render_stats.p95_time

        update_stats = self.get_stats("TradingSystem.update")
        if update_stats:
            metrics['trading_update_p95'] = update_stats.p95_time

        return metrics

    def _auto_tune(self, metrics: Dict[str, Any]):
        """
        新的自动调优逻辑，基于状态和反馈。
        """
        logger.debug("开始新一轮自动调优...")
        self._tune_thread_pool_size(metrics)
        self._tune_update_interval(metrics)
        self._tune_cache_size(metrics)
        # 其他调优方法...

    def _tune_thread_pool_size(self, metrics: Dict[str, Any]):
        param_name = 'thread_pool_size'
        state = self.tuning_params[param_name]
        cpu_usage = metrics.get('cpu_usage', 50)

        # 简单示例：如果CPU使用率在理想区间，则保持稳定
        if 40 < cpu_usage < 75:
            state.direction = TuningDirection.STABLE
            state.momentum = 0
            return

        # 评估性能变化
        # 注意：这里的性能指标是“越低越好”
        performance_improved = cpu_usage < state.last_metric

        if state.direction == TuningDirection.STABLE:
            # 开始试探性调整
            new_direction = TuningDirection.DECREASE if cpu_usage > 75 else TuningDirection.INCREASE
        elif (state.direction == TuningDirection.INCREASE and not performance_improved) or \
             (state.direction == TuningDirection.DECREASE and not performance_improved):
            # 方向错误，反转
            new_direction = TuningDirection.DECREASE if state.direction == TuningDirection.INCREASE else TuningDirection.INCREASE
            state.momentum = 0  # 重置动量
        else:
            # 方向正确，保持
            new_direction = state.direction
            state.momentum = min(state.momentum + 1, 5)  # 增加动量

        state.direction = new_direction

        # 根据动量计算调整步长
        step = 1 + state.momentum // 2

        old_value = state.value
        if state.direction == TuningDirection.INCREASE:
            state.value = min(
                old_value + step, self.system_info.get('cpu_count_logical', 16) * 2)
        else:  # DECREASE
            state.value = max(old_value - step, 2)

        if old_value != state.value:
            state.last_metric = cpu_usage
            self._record_tuning(param_name, old_value,
                                state.value, f"CPU usage {cpu_usage:.1f}%")

    def _tune_update_interval(self, metrics: Dict[str, Any]):
        param_name = 'update_interval_ms'
        state = self.tuning_params[param_name]
        render_time = metrics.get('chart_render_p95', 0.1) * 1000  # to ms

        if render_time == 0:
            return

        # 目标：渲染时间应占更新间隔的40%左右
        target_interval = render_time / 0.4

        # 如果接近目标，保持稳定
        if 0.9 < state.value / target_interval < 1.1:
            state.direction = TuningDirection.STABLE
            state.momentum = 0
            return

        performance_improved = abs(
            state.value - target_interval) < abs(state.last_metric - target_interval)

        if state.direction == TuningDirection.STABLE:
            new_direction = TuningDirection.INCREASE if state.value < target_interval else TuningDirection.DECREASE
        elif (state.direction == TuningDirection.INCREASE and not performance_improved) or \
             (state.direction == TuningDirection.DECREASE and not performance_improved):
            new_direction = TuningDirection.DECREASE if state.direction == TuningDirection.INCREASE else TuningDirection.INCREASE
            state.momentum = 0
        else:
            new_direction = state.direction
            state.momentum = min(state.momentum + 1, 5)

        state.direction = new_direction

        step = (5 + 10 * state.momentum)  # 调整步长 5ms-55ms

        old_value = state.value
        if state.direction == TuningDirection.INCREASE:
            state.value = min(old_value + step, 1000)  # 上限1秒
        else:  # DECREASE
            state.value = max(old_value - step, 50)  # 下限50ms

        if old_value != state.value:
            state.last_metric = state.value
            self._record_tuning(param_name, old_value, state.value,
                                f"P95 Render Time {render_time:.1f}ms")

    def _tune_cache_size(self, metrics: Dict[str, Any]):
        param_name = 'cache_size'
        state = self.tuning_params[param_name]
        memory_usage = metrics.get('memory_usage', 50)

        # 如果内存使用在理想区间，则保持稳定
        if 60 < memory_usage < 80:
            state.direction = TuningDirection.STABLE
            state.momentum = 0
            return

        performance_improved = memory_usage < state.last_metric

        if state.direction == TuningDirection.STABLE:
            new_direction = TuningDirection.DECREASE if memory_usage > 80 else TuningDirection.INCREASE
        elif (state.direction == TuningDirection.INCREASE and not performance_improved) or \
             (state.direction == TuningDirection.DECREASE and not performance_improved):
            new_direction = TuningDirection.DECREASE if state.direction == TuningDirection.INCREASE else TuningDirection.INCREASE
            state.momentum = 0
        else:
            new_direction = state.direction
            state.momentum = min(state.momentum + 1, 5)

        state.direction = new_direction

        # 调整步长基于当前值的百分比和动量
        step_percent = 0.1 + (state.momentum * 0.05)  # 10% - 35%
        step = int(state.value * step_percent)

        old_value = state.value
        if state.direction == TuningDirection.INCREASE:
            state.value = min(old_value + step, 100000)  # 上限10000
        else:  # DECREASE
            state.value = max(old_value - step, 1000)  # 下限100

        if old_value != state.value:
            state.last_metric = memory_usage
            self._record_tuning(param_name, old_value, state.value,
                                f"Memory usage {memory_usage:.1f}%")

    def _tune_batch_size(self, metrics: Dict[str, Any]):
        pass

    def _tune_preload_depth(self, metrics: Dict[str, Any]):
        pass

    def _record_tuning(self, param: str, old_value: Any, new_value: Any, reason: str):
        """记录调优操作"""
        record = {
            'timestamp': time.time(),
            'param': param,
            'old_value': old_value,
            'new_value': new_value,
            'reason': reason
        }
        self.tuning_history.append(record)
        logger.info(
            f"性能自动调优: {param} 从 {old_value} 调整为 {new_value} - {reason}")

        # 限制历史记录数量
        if len(self.tuning_history) > 100:
            self.tuning_history = self.tuning_history[-100:]

    def measure_time(self, name: str) -> 'TimingContext':
        """
        测量代码块执行时间的上下文管理器

        Args:
            name: 测量名称

        Returns:
            时间测量上下文管理器
        """
        return TimingContext(self, name)

    def record_time(self, name: str, duration: float):
        """
        记录执行时间

        Args:
            name: 测量名称
            duration: 执行时间（秒）
        """
        with self.stats_lock:
            if name not in self.stats:
                self.stats[name] = PerformanceStats(name=name)
            self.stats[name].add_measurement(duration)

    def get_stats(self, name: str = None) -> Union[Dict[str, PerformanceStats], Optional[PerformanceStats]]:
        """
        获取性能统计

        Args:
            name: 统计名称，如果为None则返回所有统计

        Returns:
            性能统计对象或字典
        """
        with self.stats_lock:
            if name is not None:
                return self.stats.get(name)
            return self.stats.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        result = {}

        # 获取性能统计
        with self.stats_lock:
            for name, stats in self.stats.items():
                result[name] = stats.to_dict()

        # 添加资源使用情况
        resource_summary = {}
        for resource, measurements in self.resource_stats.items():
            if not measurements:
                continue

            if resource in ['cpu', 'memory']:
                values = [value for _, value in measurements]
                resource_summary[resource] = {
                    'current': values[-1] if values else 0,
                    'avg': sum(values) / len(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0
                }

        result['resources'] = resource_summary

        # 添加调优参数
        result['tuning_params'] = {
            k: v.value for k, v in self.tuning_params.items()}

        # 添加系统信息
        result['system_info'] = self.system_info.copy()

        return result

    def export_metrics(self, path: str = None):
        """
        导出性能指标到文件

        Args:
            path: 导出路径，如果为None则使用默认路径
        """
        export_path = path or self.export_path

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            # 获取性能摘要
            summary = self.get_performance_summary()

            # 添加导出时间
            summary['export_time'] = time.time()
            summary['export_time_str'] = datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S')

            # 添加调优历史
            summary['tuning_history'] = self.tuning_history

            # 写入文件
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.debug(f"性能指标已导出到 {export_path}")

        except Exception as e:
            logger.error(f"导出性能指标失败: {e}")

    def register_tuning_callback(self, param: str, callback: Callable):
        """
        注册调优回调函数

        Args:
            param: 参数名称
            callback: 回调函数，接收参数值
        """
        self.tuning_callbacks[param] = callback
        logger.debug(f"已注册调优回调: {param}")

    def set_tuning_param(self, param: str, value: Any):
        """
        手动设置调优参数

        Args:
            param: 参数名称
            value: 参数值
        """
        if param in self.tuning_params:
            old_value = self.tuning_params[param].value
            self.tuning_params[param].value = value
            self._record_tuning(param, old_value, value, "手动设置")

            # 调用回调
            if param in self.tuning_callbacks:
                try:
                    self.tuning_callbacks[param](value)
                except Exception as e:
                    logger.error(f"调用调优回调 {param} 失败: {e}")
        else:
            logger.warning(f"未知的调优参数: {param}")

    def reset_stats(self):
        """重置性能统计"""
        with self.stats_lock:
            self.stats.clear()


class TimingContext:
    """时间测量上下文管理器"""

    def __init__(self, monitor: PerformanceMonitor, name: str):
        """
        初始化时间测量上下文

        Args:
            monitor: 性能监控器
            name: 测量名称
        """
        self.monitor = monitor
        self.name = name
        self.start_time = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.record_time(self.name, duration)


def measure_performance(tag: str = "func"):
    """
    性能监控装饰器，兼容同步和异步函数，自动记录耗时、trace_id、异常。
    :param tag: 监控标签
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logging.error(
                        f"[PERF][{tag}] 异步异常: {e} trace_id={get_trace_id()}", exc_info=True)
                    raise
                finally:
                    elapsed = time.time() - start
                    logging.info(
                        f"[PERF][{tag}] async耗时: {elapsed:.3f}s trace_id={get_trace_id()}")
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.error(
                        f"[PERF][{tag}] 同步异常: {e} trace_id={get_trace_id()}", exc_info=True)
                    raise
                finally:
                    elapsed = time.time() - start
                    logging.info(
                        f"[PERF][{tag}] sync耗时: {elapsed:.3f}s trace_id={get_trace_id()}")
            return sync_wrapper
    return decorator


# 全局实例
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        _performance_monitor.start()
    return _performance_monitor


def monitor_performance(name: str):
    """
    性能监控装饰器

    Args:
        name: 测量名称
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with monitor.measure_time(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
