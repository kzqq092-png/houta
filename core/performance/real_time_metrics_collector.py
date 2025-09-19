#!/usr/bin/env python3
"""
实时性能指标收集器

建立实时性能指标收集和处理系统，支持CPU、内存、磁盘I/O、网络等关键指标
提供准确及时的性能数据，最小化收集开销，确保数据准确性
"""

import time
import threading
import asyncio
import queue
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
from enum import Enum
from loguru import logger

# 系统监控依赖
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil不可用，系统指标收集功能受限")

# 网络监控依赖
try:
    import socket
    import struct
    NETWORK_MONITORING_AVAILABLE = True
except ImportError:
    NETWORK_MONITORING_AVAILABLE = False

# 性能监控组件
from .unified_monitor import PerformanceMetric, PerformanceCategory, MetricType


class CollectionMode(Enum):
    """收集模式"""
    REALTIME = "realtime"      # 实时收集
    BATCH = "batch"            # 批量收集
    ADAPTIVE = "adaptive"      # 自适应收集
    ON_DEMAND = "on_demand"    # 按需收集


class MetricPriority(Enum):
    """指标优先级"""
    CRITICAL = 1    # 关键指标（CPU、内存）
    HIGH = 2        # 高优先级（磁盘、网络）
    MEDIUM = 3      # 中等优先级（进程、线程）
    LOW = 4         # 低优先级（扩展指标）


@dataclass
class CollectionConfig:
    """收集配置"""
    # 收集间隔（秒）
    critical_interval: float = 0.5    # 关键指标收集间隔
    high_interval: float = 1.0        # 高优先级指标收集间隔
    medium_interval: float = 2.0      # 中等优先级指标收集间隔
    low_interval: float = 5.0         # 低优先级指标收集间隔

    # 收集模式
    collection_mode: CollectionMode = CollectionMode.ADAPTIVE

    # 缓冲区配置
    buffer_size: int = 1000           # 指标缓冲区大小
    batch_size: int = 50              # 批量处理大小

    # 性能配置
    max_collection_time: float = 0.1  # 最大收集时间（秒）
    enable_async_collection: bool = True  # 启用异步收集
    max_workers: int = 4              # 最大工作线程数

    # 指标配置
    enable_cpu_details: bool = True   # 启用CPU详细信息
    enable_memory_details: bool = True  # 启用内存详细信息
    enable_disk_details: bool = True   # 启用磁盘详细信息
    enable_network_details: bool = True  # 启用网络详细信息
    enable_process_monitoring: bool = True  # 启用进程监控

    # 阈值配置
    cpu_threshold: float = 90.0       # CPU使用率阈值
    memory_threshold: float = 85.0    # 内存使用率阈值
    disk_threshold: float = 90.0      # 磁盘使用率阈值
    network_threshold: float = 100.0  # 网络使用率阈值（MB/s）


@dataclass
class MetricCollectionResult:
    """指标收集结果"""
    metrics: List[PerformanceMetric]
    collection_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class SystemMetricsCollector:
    """系统指标收集器"""

    def __init__(self, config: CollectionConfig):
        self.config = config
        self._last_network_stats = None
        self._last_disk_stats = None
        self._last_cpu_times = None

    def collect_cpu_metrics(self) -> List[PerformanceMetric]:
        """收集CPU指标"""
        metrics = []

        try:
            if not PSUTIL_AVAILABLE:
                return metrics

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            metrics.append(PerformanceMetric(
                name="cpu_usage_percent",
                value=cpu_percent,
                category=PerformanceCategory.SYSTEM,
                metric_type=MetricType.GAUGE,
                description="CPU使用率百分比"
            ))

            if self.config.enable_cpu_details:
                # 每个CPU核心的使用率
                cpu_percents = psutil.cpu_percent(interval=None, percpu=True)
                for i, percent in enumerate(cpu_percents):
                    metrics.append(PerformanceMetric(
                        name=f"cpu_core_{i}_usage",
                        value=percent,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.GAUGE,
                        description=f"CPU核心{i}使用率"
                    ))

                # CPU频率
                try:
                    cpu_freq = psutil.cpu_freq()
                    if cpu_freq:
                        metrics.append(PerformanceMetric(
                            name="cpu_frequency_current",
                            value=cpu_freq.current,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description="当前CPU频率(MHz)"
                        ))
                except Exception:
                    pass

                # CPU时间统计
                cpu_times = psutil.cpu_times()
                metrics.extend([
                    PerformanceMetric(
                        name="cpu_time_user",
                        value=cpu_times.user,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="用户态CPU时间"
                    ),
                    PerformanceMetric(
                        name="cpu_time_system",
                        value=cpu_times.system,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="内核态CPU时间"
                    ),
                    PerformanceMetric(
                        name="cpu_time_idle",
                        value=cpu_times.idle,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="空闲CPU时间"
                    )
                ])

                # 负载平均值（仅Linux/Unix）
                try:
                    load_avg = psutil.getloadavg()
                    for i, load in enumerate(load_avg):
                        period = [1, 5, 15][i]
                        metrics.append(PerformanceMetric(
                            name=f"load_average_{period}min",
                            value=load,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description=f"{period}分钟负载平均值"
                        ))
                except (AttributeError, OSError):
                    pass

        except Exception as e:
            logger.error(f"收集CPU指标失败: {e}")

        return metrics

    def collect_memory_metrics(self) -> List[PerformanceMetric]:
        """收集内存指标"""
        metrics = []

        try:
            if not PSUTIL_AVAILABLE:
                return metrics

            # 虚拟内存
            memory = psutil.virtual_memory()
            metrics.extend([
                PerformanceMetric(
                    name="memory_usage_percent",
                    value=memory.percent,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="内存使用率百分比"
                ),
                PerformanceMetric(
                    name="memory_total_bytes",
                    value=memory.total,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="总内存大小(字节)"
                ),
                PerformanceMetric(
                    name="memory_available_bytes",
                    value=memory.available,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="可用内存大小(字节)"
                ),
                PerformanceMetric(
                    name="memory_used_bytes",
                    value=memory.used,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="已用内存大小(字节)"
                )
            ])

            if self.config.enable_memory_details:
                # 详细内存信息
                metrics.extend([
                    PerformanceMetric(
                        name="memory_free_bytes",
                        value=memory.free,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.GAUGE,
                        description="空闲内存大小(字节)"
                    ),
                    PerformanceMetric(
                        name="memory_cached_bytes",
                        value=getattr(memory, 'cached', 0),
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.GAUGE,
                        description="缓存内存大小(字节)"
                    ),
                    PerformanceMetric(
                        name="memory_buffers_bytes",
                        value=getattr(memory, 'buffers', 0),
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.GAUGE,
                        description="缓冲区内存大小(字节)"
                    )
                ])

                # 交换内存
                try:
                    swap = psutil.swap_memory()
                    metrics.extend([
                        PerformanceMetric(
                            name="swap_usage_percent",
                            value=swap.percent,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description="交换内存使用率"
                        ),
                        PerformanceMetric(
                            name="swap_total_bytes",
                            value=swap.total,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description="总交换内存大小(字节)"
                        ),
                        PerformanceMetric(
                            name="swap_used_bytes",
                            value=swap.used,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description="已用交换内存大小(字节)"
                        )
                    ])
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"收集内存指标失败: {e}")

        return metrics

    def collect_disk_metrics(self) -> List[PerformanceMetric]:
        """收集磁盘指标"""
        metrics = []

        try:
            if not PSUTIL_AVAILABLE:
                return metrics

            # 磁盘使用情况
            disk_partitions = psutil.disk_partitions()
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device = partition.device.replace(':', '').replace('\\', '_').replace('/', '_')

                    metrics.extend([
                        PerformanceMetric(
                            name=f"disk_{device}_usage_percent",
                            value=(usage.used / usage.total) * 100,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description=f"磁盘{partition.device}使用率",
                            tags={"device": partition.device, "mountpoint": partition.mountpoint}
                        ),
                        PerformanceMetric(
                            name=f"disk_{device}_total_bytes",
                            value=usage.total,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description=f"磁盘{partition.device}总大小",
                            tags={"device": partition.device}
                        ),
                        PerformanceMetric(
                            name=f"disk_{device}_free_bytes",
                            value=usage.free,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description=f"磁盘{partition.device}可用空间",
                            tags={"device": partition.device}
                        )
                    ])
                except (PermissionError, OSError):
                    continue

            if self.config.enable_disk_details:
                # 磁盘I/O统计
                try:
                    disk_io = psutil.disk_io_counters(perdisk=False)
                    if disk_io:
                        current_time = time.time()

                        # 计算I/O速率
                        if self._last_disk_stats:
                            time_delta = current_time - self._last_disk_stats['timestamp']
                            if time_delta > 0:
                                read_rate = (disk_io.read_bytes - self._last_disk_stats['read_bytes']) / time_delta
                                write_rate = (disk_io.write_bytes - self._last_disk_stats['write_bytes']) / time_delta

                                metrics.extend([
                                    PerformanceMetric(
                                        name="disk_read_rate_bytes_per_sec",
                                        value=read_rate,
                                        category=PerformanceCategory.SYSTEM,
                                        metric_type=MetricType.GAUGE,
                                        description="磁盘读取速率(字节/秒)"
                                    ),
                                    PerformanceMetric(
                                        name="disk_write_rate_bytes_per_sec",
                                        value=write_rate,
                                        category=PerformanceCategory.SYSTEM,
                                        metric_type=MetricType.GAUGE,
                                        description="磁盘写入速率(字节/秒)"
                                    )
                                ])

                        # 更新上次统计
                        self._last_disk_stats = {
                            'timestamp': current_time,
                            'read_bytes': disk_io.read_bytes,
                            'write_bytes': disk_io.write_bytes
                        }

                        # 累计I/O统计
                        metrics.extend([
                            PerformanceMetric(
                                name="disk_read_bytes_total",
                                value=disk_io.read_bytes,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.COUNTER,
                                description="累计磁盘读取字节数"
                            ),
                            PerformanceMetric(
                                name="disk_write_bytes_total",
                                value=disk_io.write_bytes,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.COUNTER,
                                description="累计磁盘写入字节数"
                            ),
                            PerformanceMetric(
                                name="disk_read_count_total",
                                value=disk_io.read_count,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.COUNTER,
                                description="累计磁盘读取次数"
                            ),
                            PerformanceMetric(
                                name="disk_write_count_total",
                                value=disk_io.write_count,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.COUNTER,
                                description="累计磁盘写入次数"
                            )
                        ])
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"收集磁盘指标失败: {e}")

        return metrics

    def collect_network_metrics(self) -> List[PerformanceMetric]:
        """收集网络指标"""
        metrics = []

        try:
            if not PSUTIL_AVAILABLE:
                return metrics

            # 网络I/O统计
            net_io = psutil.net_io_counters(pernic=False)
            if net_io:
                current_time = time.time()

                # 计算网络速率
                if self._last_network_stats:
                    time_delta = current_time - self._last_network_stats['timestamp']
                    if time_delta > 0:
                        bytes_sent_rate = (net_io.bytes_sent - self._last_network_stats['bytes_sent']) / time_delta
                        bytes_recv_rate = (net_io.bytes_recv - self._last_network_stats['bytes_recv']) / time_delta

                        metrics.extend([
                            PerformanceMetric(
                                name="network_bytes_sent_rate",
                                value=bytes_sent_rate,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.GAUGE,
                                description="网络发送速率(字节/秒)"
                            ),
                            PerformanceMetric(
                                name="network_bytes_recv_rate",
                                value=bytes_recv_rate,
                                category=PerformanceCategory.SYSTEM,
                                metric_type=MetricType.GAUGE,
                                description="网络接收速率(字节/秒)"
                            )
                        ])

                # 更新上次统计
                self._last_network_stats = {
                    'timestamp': current_time,
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                }

                # 累计网络统计
                metrics.extend([
                    PerformanceMetric(
                        name="network_bytes_sent_total",
                        value=net_io.bytes_sent,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="累计网络发送字节数"
                    ),
                    PerformanceMetric(
                        name="network_bytes_recv_total",
                        value=net_io.bytes_recv,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="累计网络接收字节数"
                    ),
                    PerformanceMetric(
                        name="network_packets_sent_total",
                        value=net_io.packets_sent,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="累计网络发送包数"
                    ),
                    PerformanceMetric(
                        name="network_packets_recv_total",
                        value=net_io.packets_recv,
                        category=PerformanceCategory.SYSTEM,
                        metric_type=MetricType.COUNTER,
                        description="累计网络接收包数"
                    )
                ])

                if self.config.enable_network_details:
                    # 网络错误统计
                    metrics.extend([
                        PerformanceMetric(
                            name="network_errin_total",
                            value=net_io.errin,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.COUNTER,
                            description="网络接收错误总数"
                        ),
                        PerformanceMetric(
                            name="network_errout_total",
                            value=net_io.errout,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.COUNTER,
                            description="网络发送错误总数"
                        ),
                        PerformanceMetric(
                            name="network_dropin_total",
                            value=net_io.dropin,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.COUNTER,
                            description="网络接收丢包总数"
                        ),
                        PerformanceMetric(
                            name="network_dropout_total",
                            value=net_io.dropout,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.COUNTER,
                            description="网络发送丢包总数"
                        )
                    ])

            if self.config.enable_network_details:
                # 网络连接统计
                try:
                    connections = psutil.net_connections()
                    connection_stats = defaultdict(int)

                    for conn in connections:
                        connection_stats[conn.status] += 1

                    for status, count in connection_stats.items():
                        metrics.append(PerformanceMetric(
                            name=f"network_connections_{status.lower()}",
                            value=count,
                            category=PerformanceCategory.SYSTEM,
                            metric_type=MetricType.GAUGE,
                            description=f"网络连接数({status})"
                        ))
                except (PermissionError, psutil.AccessDenied):
                    pass

        except Exception as e:
            logger.error(f"收集网络指标失败: {e}")

        return metrics

    def collect_process_metrics(self) -> List[PerformanceMetric]:
        """收集进程指标"""
        metrics = []

        try:
            if not PSUTIL_AVAILABLE or not self.config.enable_process_monitoring:
                return metrics

            # 进程总数
            process_count = len(psutil.pids())
            metrics.append(PerformanceMetric(
                name="process_count_total",
                value=process_count,
                category=PerformanceCategory.SYSTEM,
                metric_type=MetricType.GAUGE,
                description="系统进程总数"
            ))

            # 线程总数
            thread_count = 0
            running_processes = 0
            sleeping_processes = 0

            for proc in psutil.process_iter(['pid', 'status', 'num_threads']):
                try:
                    info = proc.info
                    if info['num_threads']:
                        thread_count += info['num_threads']

                    status = info['status']
                    if status == psutil.STATUS_RUNNING:
                        running_processes += 1
                    elif status == psutil.STATUS_SLEEPING:
                        sleeping_processes += 1

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            metrics.extend([
                PerformanceMetric(
                    name="thread_count_total",
                    value=thread_count,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="系统线程总数"
                ),
                PerformanceMetric(
                    name="process_running_count",
                    value=running_processes,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="运行中进程数"
                ),
                PerformanceMetric(
                    name="process_sleeping_count",
                    value=sleeping_processes,
                    category=PerformanceCategory.SYSTEM,
                    metric_type=MetricType.GAUGE,
                    description="睡眠中进程数"
                )
            ])

        except Exception as e:
            logger.error(f"收集进程指标失败: {e}")

        return metrics


class RealTimeMetricsCollector:
    """
    实时性能指标收集器

    功能特性：
    1. 实时性能指标收集
    2. 多优先级指标管理
    3. 自适应收集频率
    4. 异步并发收集
    5. 指标缓冲和批处理
    6. 收集性能优化
    7. 错误处理和恢复
    """

    def __init__(self, config: Optional[CollectionConfig] = None):
        """
        初始化实时指标收集器

        Args:
            config: 收集配置
        """
        self.config = config or CollectionConfig()

        # 状态管理
        self._running = False
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

        # 收集器组件
        self.system_collector = SystemMetricsCollector(self.config)

        # 数据管理
        self.metrics_buffer: queue.Queue = queue.Queue(maxsize=self.config.buffer_size)
        self.collection_results: deque = deque(maxlen=100)

        # 线程管理
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers, thread_name_prefix="MetricsCollector")
        self.collection_threads: Dict[MetricPriority, threading.Thread] = {}

        # 回调系统
        self.metric_callbacks: List[Callable] = []
        self.batch_callbacks: List[Callable] = []

        # 统计信息
        self._stats = {
            'total_metrics_collected': 0,
            'total_collection_errors': 0,
            'average_collection_time': 0.0,
            'last_collection_time': None,
            'buffer_overflow_count': 0
        }

        logger.info("实时性能指标收集器初始化完成")

    def start(self) -> bool:
        """启动收集器"""
        with self._lock:
            if self._running:
                logger.warning("指标收集器已在运行")
                return False

            try:
                self._running = True
                self._shutdown_event.clear()

                # 启动不同优先级的收集线程
                self._start_collection_threads()

                # 启动批处理线程
                self._start_batch_processor()

                logger.info("实时性能指标收集器已启动")
                return True

            except Exception as e:
                self._running = False
                logger.error(f"启动指标收集器失败: {e}")
                return False

    def stop(self) -> bool:
        """停止收集器"""
        with self._lock:
            if not self._running:
                return True

            try:
                logger.info("正在停止实时性能指标收集器...")

                self._running = False
                self._shutdown_event.set()

                # 等待收集线程结束
                for thread in self.collection_threads.values():
                    if thread and thread.is_alive():
                        thread.join(timeout=5)

                # 关闭线程池
                self.executor.shutdown(wait=True)

                logger.info("实时性能指标收集器已停止")
                return True

            except Exception as e:
                logger.error(f"停止指标收集器失败: {e}")
                return False

    def _start_collection_threads(self):
        """启动收集线程"""
        # 关键指标收集线程
        self.collection_threads[MetricPriority.CRITICAL] = threading.Thread(
            target=self._collection_loop,
            args=(MetricPriority.CRITICAL, self.config.critical_interval),
            name="MetricsCollector-Critical",
            daemon=True
        )

        # 高优先级指标收集线程
        self.collection_threads[MetricPriority.HIGH] = threading.Thread(
            target=self._collection_loop,
            args=(MetricPriority.HIGH, self.config.high_interval),
            name="MetricsCollector-High",
            daemon=True
        )

        # 中等优先级指标收集线程
        self.collection_threads[MetricPriority.MEDIUM] = threading.Thread(
            target=self._collection_loop,
            args=(MetricPriority.MEDIUM, self.config.medium_interval),
            name="MetricsCollector-Medium",
            daemon=True
        )

        # 低优先级指标收集线程
        self.collection_threads[MetricPriority.LOW] = threading.Thread(
            target=self._collection_loop,
            args=(MetricPriority.LOW, self.config.low_interval),
            name="MetricsCollector-Low",
            daemon=True
        )

        # 启动所有线程
        for thread in self.collection_threads.values():
            thread.start()

    def _start_batch_processor(self):
        """启动批处理器"""
        self.batch_thread = threading.Thread(
            target=self._batch_processing_loop,
            name="MetricsCollector-BatchProcessor",
            daemon=True
        )
        self.batch_thread.start()

    def _collection_loop(self, priority: MetricPriority, interval: float):
        """指标收集循环"""
        logger.info(f"启动{priority.name}优先级指标收集循环，间隔: {interval}秒")

        while not self._shutdown_event.is_set():
            try:
                start_time = time.time()

                # 根据优先级收集不同的指标
                metrics = self._collect_metrics_by_priority(priority)

                # 将指标添加到缓冲区
                for metric in metrics:
                    try:
                        self.metrics_buffer.put_nowait(metric)
                    except queue.Full:
                        self._stats['buffer_overflow_count'] += 1
                        logger.warning("指标缓冲区已满，丢弃指标")

                # 更新统计信息
                collection_time = time.time() - start_time
                self._update_collection_stats(len(metrics), collection_time)

                # 检查收集时间是否超过阈值
                if collection_time > self.config.max_collection_time:
                    logger.warning(f"{priority.name}优先级指标收集耗时过长: {collection_time:.3f}秒")

                # 计算睡眠时间
                sleep_time = max(0, interval - collection_time)
                if sleep_time > 0:
                    self._shutdown_event.wait(sleep_time)

            except Exception as e:
                logger.error(f"{priority.name}优先级指标收集错误: {e}")
                self._stats['total_collection_errors'] += 1
                self._shutdown_event.wait(5)  # 出错后等待5秒

    def _collect_metrics_by_priority(self, priority: MetricPriority) -> List[PerformanceMetric]:
        """根据优先级收集指标"""
        metrics = []

        try:
            if priority == MetricPriority.CRITICAL:
                # 关键指标：CPU和内存
                metrics.extend(self.system_collector.collect_cpu_metrics())
                metrics.extend(self.system_collector.collect_memory_metrics())

            elif priority == MetricPriority.HIGH:
                # 高优先级：磁盘和网络
                metrics.extend(self.system_collector.collect_disk_metrics())
                metrics.extend(self.system_collector.collect_network_metrics())

            elif priority == MetricPriority.MEDIUM:
                # 中等优先级：进程信息
                metrics.extend(self.system_collector.collect_process_metrics())

            elif priority == MetricPriority.LOW:
                # 低优先级：扩展指标
                pass  # 可以添加其他扩展指标

        except Exception as e:
            logger.error(f"收集{priority.name}优先级指标失败: {e}")

        return metrics

    def _batch_processing_loop(self):
        """批处理循环"""
        logger.info("启动指标批处理循环")

        batch = []

        while not self._shutdown_event.is_set():
            try:
                # 从缓冲区获取指标
                try:
                    metric = self.metrics_buffer.get(timeout=1.0)
                    batch.append(metric)
                except queue.Empty:
                    # 超时，处理当前批次
                    if batch:
                        self._process_batch(batch)
                        batch = []
                    continue

                # 批次达到大小限制，处理批次
                if len(batch) >= self.config.batch_size:
                    self._process_batch(batch)
                    batch = []

            except Exception as e:
                logger.error(f"批处理循环错误: {e}")

        # 处理剩余的指标
        if batch:
            self._process_batch(batch)

    def _process_batch(self, metrics: List[PerformanceMetric]):
        """处理指标批次"""
        try:
            # 触发批处理回调
            for callback in self.batch_callbacks:
                try:
                    callback(metrics)
                except Exception as e:
                    logger.error(f"批处理回调执行失败: {e}")

            # 触发单个指标回调
            for metric in metrics:
                for callback in self.metric_callbacks:
                    try:
                        callback(metric)
                    except Exception as e:
                        logger.error(f"指标回调执行失败: {e}")

            logger.debug(f"处理指标批次: {len(metrics)}个指标")

        except Exception as e:
            logger.error(f"处理指标批次失败: {e}")

    def _update_collection_stats(self, metric_count: int, collection_time: float):
        """更新收集统计信息"""
        with self._lock:
            self._stats['total_metrics_collected'] += metric_count
            self._stats['last_collection_time'] = datetime.now()

            # 更新平均收集时间
            current_avg = self._stats['average_collection_time']
            total_collections = self._stats['total_metrics_collected']

            if total_collections > 0:
                self._stats['average_collection_time'] = (
                    (current_avg * (total_collections - metric_count) + collection_time * metric_count) / total_collections
                )

    def register_metric_callback(self, callback: Callable[[PerformanceMetric], None]):
        """注册指标回调"""
        self.metric_callbacks.append(callback)

    def register_batch_callback(self, callback: Callable[[List[PerformanceMetric]], None]):
        """注册批处理回调"""
        self.batch_callbacks.append(callback)

    def collect_metrics_sync(self, priority: Optional[MetricPriority] = None) -> List[PerformanceMetric]:
        """同步收集指标"""
        try:
            if priority:
                return self._collect_metrics_by_priority(priority)
            else:
                # 收集所有优先级的指标
                all_metrics = []
                for p in MetricPriority:
                    all_metrics.extend(self._collect_metrics_by_priority(p))
                return all_metrics

        except Exception as e:
            logger.error(f"同步收集指标失败: {e}")
            return []

    async def collect_metrics_async(self, priority: Optional[MetricPriority] = None) -> List[PerformanceMetric]:
        """异步收集指标"""
        try:
            loop = asyncio.get_event_loop()

            if priority:
                return await loop.run_in_executor(
                    self.executor, self._collect_metrics_by_priority, priority
                )
            else:
                # 并发收集所有优先级的指标
                tasks = []
                for p in MetricPriority:
                    task = loop.run_in_executor(
                        self.executor, self._collect_metrics_by_priority, p
                    )
                    tasks.append(task)

                results = await asyncio.gather(*tasks)
                all_metrics = []
                for metrics in results:
                    all_metrics.extend(metrics)

                return all_metrics

        except Exception as e:
            logger.error(f"异步收集指标失败: {e}")
            return []

    def get_current_metrics(self) -> List[PerformanceMetric]:
        """获取当前缓冲区中的指标"""
        metrics = []
        temp_queue = queue.Queue()

        try:
            # 从缓冲区获取所有指标
            while not self.metrics_buffer.empty():
                try:
                    metric = self.metrics_buffer.get_nowait()
                    metrics.append(metric)
                    temp_queue.put(metric)
                except queue.Empty:
                    break

            # 将指标放回缓冲区
            while not temp_queue.empty():
                try:
                    metric = temp_queue.get_nowait()
                    self.metrics_buffer.put_nowait(metric)
                except (queue.Empty, queue.Full):
                    break

        except Exception as e:
            logger.error(f"获取当前指标失败: {e}")

        return metrics

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self._stats.copy()
            stats['buffer_size'] = self.metrics_buffer.qsize()
            stats['is_running'] = self._running
            stats['active_threads'] = sum(1 for t in self.collection_threads.values() if t.is_alive())

            return stats

    def clear_buffer(self):
        """清空缓冲区"""
        try:
            while not self.metrics_buffer.empty():
                try:
                    self.metrics_buffer.get_nowait()
                except queue.Empty:
                    break
            logger.info("指标缓冲区已清空")
        except Exception as e:
            logger.error(f"清空缓冲区失败: {e}")

    @contextmanager
    def measure_collection_time(self, operation_name: str):
        """测量收集时间的上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            logger.debug(f"{operation_name} 收集耗时: {elapsed_time:.3f}秒")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# 全局单例实例
_collector_instance: Optional[RealTimeMetricsCollector] = None
_collector_lock = threading.RLock()


def get_metrics_collector() -> RealTimeMetricsCollector:
    """获取全局指标收集器实例"""
    global _collector_instance

    with _collector_lock:
        if _collector_instance is None:
            _collector_instance = RealTimeMetricsCollector()
            _collector_instance.start()

        return _collector_instance


def initialize_metrics_collector(config: Optional[CollectionConfig] = None) -> RealTimeMetricsCollector:
    """初始化全局指标收集器"""
    global _collector_instance

    with _collector_lock:
        if _collector_instance is not None:
            _collector_instance.stop()

        _collector_instance = RealTimeMetricsCollector(config)
        _collector_instance.start()

    return _collector_instance
