from loguru import logger
"""
异步数据处理器模块
提供多线程数据处理、批量处理和性能优化功能
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from queue import Queue, Empty
import numpy as np
import pandas as pd
from enum import Enum
import psutil
from utils.trace_context import get_trace_id, set_trace_id
from core.performance import measure_performance

logger = logger


class ProcessingPriority(Enum):
    """处理优先级"""
    CRITICAL = 1    # 关键数据（K线主图）
    HIGH = 2        # 高优先级（成交量）
    NORMAL = 3      # 普通优先级（主要指标）
    LOW = 4         # 低优先级（次要指标）
    BACKGROUND = 5  # 后台处理（装饰元素）


@dataclass
class ProcessingTask:
    """处理任务"""
    id: str
    data: Any
    processor: Callable
    priority: ProcessingPriority
    callback: Optional[Callable] = None
    created_time: float = None

    def __post_init__(self):
        if self.created_time is None:
            self.created_time = time.time()


class AsyncDataProcessor:
    """异步数据处理器"""

    def __init__(self, max_workers: int = None, enable_monitoring: bool = True):
        """
        初始化异步数据处理器

        Args:
            max_workers: 最大工作线程数，默认根据系统配置自动设置
            enable_monitoring: 是否启用性能监控
        """
        self.max_workers = max_workers or self._calculate_optimal_workers()
        self.enable_monitoring = enable_monitoring

        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # 任务队列（按优先级分组）
        self.task_queues = {
            priority: Queue() for priority in ProcessingPriority
        }

        # 运行状态
        self.is_running = False
        self.worker_threads = []

        # 性能统计
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'average_processing_time': 0.0,
            'queue_sizes': {priority: 0 for priority in ProcessingPriority}
        }

        # 锁
        self.stats_lock = threading.Lock()

        logger.info(f"AsyncDataProcessor初始化完成 - 工作线程数: {self.max_workers}")

    def _calculate_optimal_workers(self) -> int:
        """根据系统资源计算最优工作线程数"""
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)

        if memory_gb >= 16:
            # 16GB+内存：更多线程
            return min(cpu_count * 2, 16)
        elif memory_gb >= 8:
            # 8-16GB内存：适中线程数
            return min(cpu_count + 2, 8)
        else:
            # <8GB内存：保守线程数
            return min(cpu_count, 4)

    def start(self):
        """启动处理器"""
        if self.is_running:
            return

        self.is_running = True

        # 为每个优先级启动工作线程
        for priority in ProcessingPriority:
            thread = threading.Thread(
                target=self._worker_loop,
                args=(priority,),
                name=f"AsyncProcessor-{priority.name}",
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)

        logger.info("AsyncDataProcessor已启动")

    def stop(self):
        """停止处理器"""
        if not self.is_running:
            return

        self.is_running = False

        # 等待所有任务完成
        for priority in ProcessingPriority:
            while not self.task_queues[priority].empty():
                time.sleep(0.1)

        # 关闭线程池
        self.executor.shutdown(wait=True)

        logger.info("AsyncDataProcessor已停止")

    @measure_performance("AsyncDataProcessor._worker_loop")
    def _worker_loop(self, priority: ProcessingPriority):
        set_trace_id(get_trace_id())
        """工作线程主循环"""
        queue = self.task_queues[priority]

        while self.is_running:
            try:
                # 获取任务（带超时）
                task = queue.get(timeout=1.0)

                # 更新队列大小统计
                with self.stats_lock:
                    self.stats['queue_sizes'][priority] = queue.qsize()

                # 处理任务
                self._process_task(task)

                queue.task_done()

            except Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程 {priority.name} 处理任务时出错: {e}")

    @measure_performance("AsyncDataProcessor._process_task")
    def _process_task(self, task: ProcessingTask):
        set_trace_id(get_trace_id())
        """处理单个任务"""
        start_time = time.time()

        try:
            # 执行处理函数
            result = task.processor(task.data)

            # 调用回调函数
            if task.callback:
                task.callback(result)

            # 更新成功统计
            with self.stats_lock:
                self.stats['completed_tasks'] += 1

            if self.enable_monitoring:
                processing_time = time.time() - start_time
                logger.debug(f"任务 {task.id} 处理完成 - 耗时: {processing_time:.4f}s")

        except Exception as e:
            # 更新失败统计
            with self.stats_lock:
                self.stats['failed_tasks'] += 1

            logger.error(f"任务 {task.id} 处理失败: {e}")

        finally:
            # 更新处理时间统计
            if self.enable_monitoring:
                processing_time = time.time() - start_time
                with self.stats_lock:
                    total_completed = self.stats['completed_tasks'] + \
                        self.stats['failed_tasks']
                    if total_completed > 0:
                        current_avg = self.stats['average_processing_time']
                        self.stats['average_processing_time'] = (
                            (current_avg * (total_completed - 1) +
                             processing_time) / total_completed
                        )

    def submit_task(self, task_id: str, data: Any, processor: Callable,
                    priority: ProcessingPriority = ProcessingPriority.NORMAL,
                    callback: Optional[Callable] = None) -> bool:
        """
        提交处理任务

        Args:
            task_id: 任务ID
            data: 要处理的数据
            processor: 处理函数
            priority: 任务优先级
            callback: 完成回调函数

        Returns:
            bool: 是否成功提交
        """
        if not self.is_running:
            logger.warning("处理器未启动，无法提交任务")
            return False

        task = ProcessingTask(
            id=task_id,
            data=data,
            processor=processor,
            priority=priority,
            callback=callback
        )

        try:
            self.task_queues[priority].put(task)

            with self.stats_lock:
                self.stats['total_tasks'] += 1

            logger.debug(f"任务 {task_id} 已提交到 {priority.name} 队列")
            return True

        except Exception as e:
            logger.error(f"提交任务 {task_id} 失败: {e}")
            return False

    def submit_batch_tasks(self, tasks: List[Dict[str, Any]]) -> int:
        """
        批量提交任务

        Args:
            tasks: 任务列表，每个任务包含 id, data, processor, priority, callback

        Returns:
            int: 成功提交的任务数量
        """
        success_count = 0

        for task_info in tasks:
            if self.submit_task(**task_info):
                success_count += 1

        logger.info(f"批量提交任务完成 - 成功: {success_count}/{len(tasks)}")
        return success_count

    def clear_queue(self, priority: ProcessingPriority = None):
        """
        清空队列

        Args:
            priority: 要清空的优先级队列，None表示清空所有队列
        """
        if priority:
            queue = self.task_queues[priority]
            cleared_count = queue.qsize()

            while not queue.empty():
                try:
                    queue.get_nowait()
                    queue.task_done()
                except Empty:
                    break

            logger.info(f"已清空 {priority.name} 队列 - 清除任务数: {cleared_count}")
        else:
            total_cleared = 0
            for p in ProcessingPriority:
                queue = self.task_queues[p]
                cleared_count = queue.qsize()
                total_cleared += cleared_count

                while not queue.empty():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except Empty:
                        break

            logger.info(f"已清空所有队列 - 总清除任务数: {total_cleared}")

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        status = {
            'is_running': self.is_running,
            'max_workers': self.max_workers,
            'queue_sizes': {},
            'total_pending': 0
        }

        for priority in ProcessingPriority:
            size = self.task_queues[priority].qsize()
            status['queue_sizes'][priority.name] = size
            status['total_pending'] += size

        return status

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self.stats_lock:
            stats = self.stats.copy()

        # 计算成功率
        total_processed = stats['completed_tasks'] + stats['failed_tasks']
        success_rate = (stats['completed_tasks'] /
                        total_processed * 100) if total_processed > 0 else 0

        stats['success_rate'] = success_rate
        stats['total_processed'] = total_processed
        stats['pending_tasks'] = stats['total_tasks'] - total_processed

        return stats

    def process_dataframe_chunks(self, df: pd.DataFrame, processor: Callable,
                                 chunk_size: int = 1000,
                                 priority: ProcessingPriority = ProcessingPriority.NORMAL) -> List[Any]:
        """
        分块处理DataFrame

        Args:
            df: 要处理的DataFrame
            processor: 处理函数
            chunk_size: 分块大小
            priority: 处理优先级

        Returns:
            List[Any]: 处理结果列表
        """
        if df.empty:
            return []

        # 分块
        chunks = [df[i:i+chunk_size] for i in range(0, len(df), chunk_size)]

        # 提交任务
        futures = []
        for i, chunk in enumerate(chunks):
            future = self.executor.submit(processor, chunk)
            futures.append(future)

        # 收集结果
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"分块处理失败: {e}")

        logger.info(
            f"DataFrame分块处理完成 - 分块数: {len(chunks)}, 成功: {len(results)}")
        return results

    def process_array_parallel(self, data: np.ndarray, processor: Callable,
                               num_splits: int = None,
                               priority: ProcessingPriority = ProcessingPriority.NORMAL) -> np.ndarray:
        """
        并行处理数组

        Args:
            data: 要处理的数组
            processor: 处理函数
            num_splits: 分割数量，默认为工作线程数
            priority: 处理优先级

        Returns:
            np.ndarray: 处理结果数组
        """
        if data.size == 0:
            return data

        num_splits = num_splits or self.max_workers
        splits = np.array_split(data, num_splits)

        # 提交任务
        futures = []
        for split in splits:
            future = self.executor.submit(processor, split)
            futures.append(future)

        # 收集结果
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"数组并行处理失败: {e}")

        # 合并结果
        if results:
            combined_result = np.concatenate(results)
            logger.info(
                f"数组并行处理完成 - 分割数: {len(splits)}, 结果长度: {len(combined_result)}")
            return combined_result
        else:
            logger.warning("数组并行处理无有效结果")
            return np.array([])


# 全局异步处理器实例
_global_processor = None


def get_async_processor() -> AsyncDataProcessor:
    """获取全局异步处理器实例"""
    global _global_processor
    if _global_processor is None:
        _global_processor = AsyncDataProcessor()
        _global_processor.start()
    return _global_processor


def initialize_processor(max_workers: int = None, enable_monitoring: bool = True):
    """初始化全局处理器"""
    global _global_processor
    if _global_processor is not None:
        _global_processor.stop()

    _global_processor = AsyncDataProcessor(max_workers, enable_monitoring)
    _global_processor.start()


def shutdown_processor():
    """关闭全局处理器"""
    global _global_processor
    if _global_processor is not None:
        _global_processor.stop()
        _global_processor = None

# 便捷函数


def submit_task(task_id: str, data: Any, processor: Callable,
                priority: ProcessingPriority = ProcessingPriority.NORMAL,
                callback: Optional[Callable] = None) -> bool:
    """提交任务到全局处理器"""
    return get_async_processor().submit_task(task_id, data, processor, priority, callback)


def process_dataframe_async(df: pd.DataFrame, processor: Callable,
                            chunk_size: int = 1000,
                            priority: ProcessingPriority = ProcessingPriority.NORMAL) -> List[Any]:
    """异步处理DataFrame"""
    return get_async_processor().process_dataframe_chunks(df, processor, chunk_size, priority)


def process_array_async(data: np.ndarray, processor: Callable,
                        num_splits: int = None,
                        priority: ProcessingPriority = ProcessingPriority.NORMAL) -> np.ndarray:
    """异步处理数组"""
    return get_async_processor().process_array_parallel(data, processor, num_splits, priority)


# 导出接口
__all__ = [
    'ProcessingPriority',
    'ProcessingTask',
    'AsyncDataProcessor',
    'get_async_processor',
    'initialize_processor',
    'shutdown_processor',
    'submit_task',
    'process_dataframe_async',
    'process_array_async'
]
