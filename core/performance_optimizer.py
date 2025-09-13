from loguru import logger
"""
专业级性能优化器模块
提供内存管理、缓存策略、并行处理等性能优化功能
对标行业专业软件标准
"""

import gc
import time
import psutil
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import wraps, lru_cache
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import OrderedDict
import weakref
from dataclasses import dataclass
from enum import Enum
from core.performance import measure_performance


class OptimizationLevel(Enum):
    """优化级别枚举"""
    BASIC = "basic"          # 基础优化
    STANDARD = "standard"    # 标准优化
    AGGRESSIVE = "aggressive"  # 激进优化
    PROFESSIONAL = "professional"  # 专业级优化


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    execution_time: float
    memory_usage: float
    cpu_usage: float
    cache_hit_rate: float
    optimization_level: OptimizationLevel
    timestamp: datetime


class MemoryManager:
    """
    专业级内存管理器
    监控和优化内存使用
    """

    def __init__(self):
        # 纯Loguru架构，移除log_manager依赖
        self.memory_threshold = 0.8  # 内存使用阈值 80%
        self.cleanup_callbacks = []
        self._monitoring = False

    def monitor_memory(self) -> Dict[str, float]:
        """监控内存使用情况"""
        memory_info = psutil.virtual_memory()
        return {
            "total": memory_info.total / (1024**3),  # GB
            "available": memory_info.available / (1024**3),  # GB
            "used": memory_info.used / (1024**3),  # GB
            "percentage": memory_info.percent
        }

    def cleanup_memory(self, force: bool = False) -> bool:
        """清理内存"""
        try:
            memory_before = self.monitor_memory()

            # 执行垃圾回收
            collected = gc.collect()

            # 执行注册的清理回调
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.warning(
                        f"内存清理回调执行失败: {str(e)}")

            memory_after = self.monitor_memory()
            freed_memory = memory_before["used"] - memory_after["used"]

            logger.info(
                f"内存清理完成 - 回收对象: {collected}, 释放内存: {freed_memory:.2f}GB",
                LogLevel.INFO
            )

            return True

        except Exception as e:
            logger.error(f"内存清理失败: {str(e)}")
            return False

    def register_cleanup_callback(self, callback: Callable):
        """注册内存清理回调函数"""
        self.cleanup_callbacks.append(callback)

    def auto_cleanup_if_needed(self) -> bool:
        """根据内存使用情况自动清理"""
        memory_info = self.monitor_memory()
        if memory_info["percentage"] > self.memory_threshold * 100:
            logger.info(
                f"内存使用率过高 ({memory_info['percentage']:.1f}%)，开始自动清理",
                LogLevel.WARNING
            )
            return self.cleanup_memory()
        return False


class CacheManager:
    """
    专业级缓存管理器
    提供LRU缓存策略和缓存统计
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self.cache:
                # 检查TTL
                if self._is_expired(key):
                    self._remove(key)
                    self.miss_count += 1
                    return None

                # 更新访问时间和位置（LRU）
                self.cache.move_to_end(key)
                self.access_times[key] = time.time()
                self.hit_count += 1
                return self.cache[key]

            self.miss_count += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            current_time = time.time()

            if key in self.cache:
                # 更新现有键
                self.cache[key] = value
                self.cache.move_to_end(key)
            else:
                # 添加新键
                if len(self.cache) >= self.max_size:
                    # 移除最久未使用的项
                    oldest_key = next(iter(self.cache))
                    self._remove(oldest_key)

                self.cache[key] = value

            self.access_times[key] = current_time

    def remove(self, key: str) -> bool:
        """移除缓存项"""
        with self._lock:
            return self._remove(key)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.hit_count = 0
            self.miss_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": hit_rate,
                "memory_usage": self._estimate_memory_usage()
            }

    def _is_expired(self, key: str) -> bool:
        """检查缓存项是否过期"""
        if key not in self.access_times:
            return True

        return time.time() - self.access_times[key] > self.ttl_seconds

    def _remove(self, key: str) -> bool:
        """内部移除方法"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return True
        return False

    def _estimate_memory_usage(self) -> float:
        """估算缓存内存使用量（MB）"""
        try:
            import sys
            total_size = 0
            for key, value in self.cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return total_size / (1024 * 1024)  # MB
        except:
            return 0.0


class ParallelProcessor:
    """
    并行处理器
    提供多线程和多进程处理能力
    """

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(
            32, (multiprocessing.cpu_count() or 1) + 4)
        self.thread_pool = None
        self.process_pool = None

    @measure_performance("ParallelProcessor.process_parallel_threads")
    def process_parallel_threads(self, func: Callable, data_list: List[Any],
                                 **kwargs) -> List[Any]:
        """使用多线程并行处理"""
        if not data_list:
            return []

        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_data = {
                executor.submit(func, data, **kwargs): data
                for data in data_list
            }

            for future in as_completed(future_to_data):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 记录错误但继续处理其他任务
                    results.append(None)

        return results

    @measure_performance("ParallelProcessor.process_parallel_processes")
    def process_parallel_processes(self, func: Callable, data_list: List[Any],
                                   **kwargs) -> List[Any]:
        """使用多进程并行处理"""
        if not data_list:
            return []

        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_data = {
                executor.submit(func, data, **kwargs): data
                for data in data_list
            }

            for future in as_completed(future_to_data):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(None)

        return results

    def process_batch(self, func: Callable, data_list: List[Any],
                      batch_size: int = 100, use_processes: bool = False,
                      **kwargs) -> List[Any]:
        """批量处理数据"""
        if not data_list:
            return []

        # 分批处理
        batches = [data_list[i:i + batch_size]
                   for i in range(0, len(data_list), batch_size)]

        if use_processes:
            return self.process_parallel_processes(func, batches, **kwargs)
        else:
            return self.process_parallel_threads(func, batches, **kwargs)


class ProfessionalPerformanceOptimizer:
    """
    专业级性能优化器
    整合内存管理、缓存策略、并行处理等功能
    """

    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.PROFESSIONAL):
        self.optimization_level = optimization_level
        # 纯Loguru架构，移除log_manager依赖

        # 初始化组件
        self.memory_manager = MemoryManager()
        self.cache_manager = CacheManager()
        self.parallel_processor = ParallelProcessor()

        # 性能监控
        self.performance_history = []
        self.start_time = None

        # 配置优化参数
        self._configure_optimization()

    def _configure_optimization(self):
        """根据优化级别配置参数"""
        if self.optimization_level == OptimizationLevel.BASIC:
            self.cache_manager.max_size = 100
            self.parallel_processor.max_workers = 2
        elif self.optimization_level == OptimizationLevel.STANDARD:
            self.cache_manager.max_size = 500
            self.parallel_processor.max_workers = 4
        elif self.optimization_level == OptimizationLevel.AGGRESSIVE:
            self.cache_manager.max_size = 1000
            self.parallel_processor.max_workers = 8
        else:  # PROFESSIONAL
            self.cache_manager.max_size = 2000
            self.parallel_processor.max_workers = min(
                32, multiprocessing.cpu_count() * 2)

    def start_monitoring(self):
        """开始性能监控"""
        self.start_time = time.time()

    def stop_monitoring(self) -> PerformanceMetrics:
        """停止性能监控并返回指标"""
        if self.start_time is None:
            raise ValueError("监控未开始")

        execution_time = time.time() - self.start_time
        memory_info = self.memory_manager.monitor_memory()
        cache_stats = self.cache_manager.get_stats()

        metrics = PerformanceMetrics(
            execution_time=execution_time,
            memory_usage=memory_info["percentage"],
            cpu_usage=psutil.cpu_percent(),
            cache_hit_rate=cache_stats["hit_rate"],
            optimization_level=self.optimization_level,
            timestamp=datetime.now()
        )

        self.performance_history.append(metrics)
        self.start_time = None

        return metrics

    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化DataFrame内存使用"""
        if df is None or df.empty:
            return df

        optimized_df = df.copy()

        # 优化数值类型
        for col in optimized_df.select_dtypes(include=['int64']).columns:
            col_min = optimized_df[col].min()
            col_max = optimized_df[col].max()

            if col_min >= -128 and col_max <= 127:
                optimized_df[col] = optimized_df[col].astype('int8')
            elif col_min >= -32768 and col_max <= 32767:
                optimized_df[col] = optimized_df[col].astype('int16')
            elif col_min >= -2147483648 and col_max <= 2147483647:
                optimized_df[col] = optimized_df[col].astype('int32')

        for col in optimized_df.select_dtypes(include=['float64']).columns:
            optimized_df[col] = pd.to_numeric(
                optimized_df[col], downcast='float')

        # 优化字符串类型
        for col in optimized_df.select_dtypes(include=['object']).columns:
            if optimized_df[col].dtype == 'object':
                try:
                    optimized_df[col] = optimized_df[col].astype('category')
                except:
                    pass

        return optimized_df

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.performance_history:
            return {"message": "暂无性能数据"}

        recent_metrics = self.performance_history[-10:]  # 最近10次

        avg_execution_time = np.mean(
            [m.execution_time for m in recent_metrics])
        avg_memory_usage = np.mean([m.memory_usage for m in recent_metrics])
        avg_cpu_usage = np.mean([m.cpu_usage for m in recent_metrics])
        avg_cache_hit_rate = np.mean(
            [m.cache_hit_rate for m in recent_metrics])

        cache_stats = self.cache_manager.get_stats()
        memory_info = self.memory_manager.monitor_memory()

        return {
            "optimization_level": self.optimization_level.value,
            "performance_summary": {
                "avg_execution_time": avg_execution_time,
                "avg_memory_usage": avg_memory_usage,
                "avg_cpu_usage": avg_cpu_usage,
                "avg_cache_hit_rate": avg_cache_hit_rate
            },
            "current_status": {
                "memory_usage": memory_info,
                "cache_stats": cache_stats,
                "cpu_usage": psutil.cpu_percent()
            },
            "history_count": len(self.performance_history),
            "last_update": datetime.now().isoformat()
        }

# 装饰器函数


def performance_monitor(optimizer: ProfessionalPerformanceOptimizer):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            optimizer.start_monitoring()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                metrics = optimizer.stop_monitoring()
                logger.info(
                    f"函数 {func.__name__} 执行完成 - 耗时: {metrics.execution_time:.3f}s, "
                    f"内存: {metrics.memory_usage:.1f}%, CPU: {metrics.cpu_usage:.1f}%"
                )
        return wrapper
    return decorator


def optimize_function(cache_key_func: Optional[Callable] = None,
                      cache_ttl: int = 3600):
    """函数优化装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            global_cache = getattr(wrapper, '_cache', None)
            if global_cache is None:
                global_cache = CacheManager(ttl_seconds=cache_ttl)
                wrapper._cache = global_cache

            cached_result = global_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            global_cache.set(cache_key, result)

            return result
        return wrapper
    return decorator


def optimize_dataframe_memory(func):
    """DataFrame内存优化装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, pd.DataFrame):
            optimizer = ProfessionalPerformanceOptimizer()
            return optimizer.optimize_dataframe(result)

        return result
    return wrapper

# 便捷函数


def create_performance_optimizer(level: OptimizationLevel = OptimizationLevel.PROFESSIONAL) -> ProfessionalPerformanceOptimizer:
    """创建性能优化器实例"""
    return ProfessionalPerformanceOptimizer(optimization_level=level)


def optimize_pandas_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """快速优化DataFrame"""
    optimizer = create_performance_optimizer()
    return optimizer.optimize_dataframe(df)


def get_system_performance_info() -> Dict[str, Any]:
    """获取系统性能信息"""
    memory_info = psutil.virtual_memory()
    cpu_info = psutil.cpu_percent(interval=1)

    return {
        "memory": {
            "total_gb": memory_info.total / (1024**3),
            "available_gb": memory_info.available / (1024**3),
            "used_percent": memory_info.percent
        },
        "cpu": {
            "usage_percent": cpu_info,
            "core_count": multiprocessing.cpu_count()
        },
        "timestamp": datetime.now().isoformat()
    }
