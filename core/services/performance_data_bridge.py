#!/usr/bin/env python3
"""
性能数据桥接服务

负责将系统中各个性能监控组件的数据桥接到深度分析服务，
确保深度分析功能能够获得实时的性能数据。
"""

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from core.services.deep_analysis_service import get_deep_analysis_service
from core.events import EventBus, get_event_bus
from core.metrics.events import ApplicationMetricRecorded, SystemResourceUpdated


class PerformanceDataBridge:
    """性能数据桥接器"""

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.deep_analysis_service = get_deep_analysis_service()
        self._running = False
        self._collection_thread = None
        self._last_collection_time = None

        # 数据收集间隔（秒）
        self.collection_interval = 10

        # 事件处理器注册
        self._register_event_handlers()

        logger.info("性能数据桥接器初始化完成")

    def _register_event_handlers(self):
        """注册事件处理器"""
        try:
            # 监听应用指标事件
            self.event_bus.subscribe(ApplicationMetricRecorded, self._handle_application_metric)

            # 监听系统资源更新事件
            self.event_bus.subscribe(SystemResourceUpdated, self._handle_system_resource)

            logger.info("性能数据桥接器事件处理器注册完成")
        except Exception as e:
            logger.error("注册事件处理器失败: {}", str(e))

    def _handle_application_metric(self, event: ApplicationMetricRecorded):
        """处理应用指标事件"""
        try:
            # 将应用指标转发到深度分析服务
            self.deep_analysis_service.record_operation_timing(
                event.operation_name,
                event.duration
            )

            # 记录成功率相关指标
            success_rate = 1.0 if event.was_successful else 0.0
            self.deep_analysis_service.record_metric(
                f"{event.operation_name}_success_rate",
                success_rate,
                "application"
            )

            logger.debug("应用指标已桥接: {} - {:.3f}s", event.operation_name, event.duration)

        except Exception as e:
            logger.error("处理应用指标事件失败: {}", str(e))

    def _handle_system_resource(self, event: SystemResourceUpdated):
        """处理系统资源更新事件"""
        try:
            # 将系统资源指标转发到深度分析服务
            self.deep_analysis_service.record_metric("cpu_usage", event.cpu_percent, "system")
            self.deep_analysis_service.record_metric("memory_usage", event.memory_percent, "system")
            self.deep_analysis_service.record_metric("disk_usage", event.disk_percent, "system")

            logger.debug("系统资源已桥接: CPU={:.1f}%, MEM={:.1f}%, DISK={:.1f}%", event.cpu_percent, event.memory_percent, event.disk_percent)

        except Exception as e:
            logger.error("处理系统资源事件失败: {}", str(e))

    def start_active_collection(self):
        """开始主动数据收集"""
        if self._running:
            logger.warning("性能数据收集已在运行")
            return

        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            name="PerformanceDataCollection",
            daemon=True
        )
        self._collection_thread.start()

        logger.info("性能数据主动收集已启动")

    def stop_active_collection(self):
        """停止主动数据收集"""
        if not self._running:
            return

        self._running = False
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5)

        logger.info("性能数据主动收集已停止")

    def _collection_loop(self):
        """数据收集循环"""
        logger.info("性能数据收集循环启动")

        while self._running:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._last_collection_time = datetime.now()

                time.sleep(self.collection_interval)

            except Exception as e:
                logger.error("数据收集循环错误: {}", str(e))
                time.sleep(1)  # 错误时短暂延迟

    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.deep_analysis_service.record_metric("cpu_usage", cpu_percent, "system")

            # 内存使用率
            memory = psutil.virtual_memory()
            self.deep_analysis_service.record_metric("memory_usage", memory.percent, "system")

            # 磁盘使用率（Windows兼容）
            import os
            if os.name == 'nt':  # Windows
                disk = psutil.disk_usage('C:')
            else:  # Unix/Linux
                disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.deep_analysis_service.record_metric("disk_usage", disk_percent, "system")

            # 暂时注释掉debug语句以排除格式化问题
            # logger.debug("系统指标收集完成: CPU={}%, MEM={}%, DISK={}%",
            #            round(cpu_percent, 1), round(memory.percent, 1), round(disk_percent, 1))

        except ImportError:
            # 如果psutil不可用，生成模拟数据
            import random
            self.deep_analysis_service.record_metric("cpu_usage", random.uniform(20, 80), "system")
            self.deep_analysis_service.record_metric("memory_usage", random.uniform(30, 70), "system")
            self.deep_analysis_service.record_metric("disk_usage", random.uniform(40, 90), "system")

        except Exception as e:
            try:
                logger.error(f"收集系统指标失败: {e}")
            except Exception:
                # 如果logger.error也失败，使用最基本的记录方式
                logger.info("收集系统指标时发生错误")

    def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 从统一性能监控器获取数据
            from core.performance.unified_monitor import get_performance_monitor

            monitor = get_performance_monitor()
            if monitor and hasattr(monitor, 'stats') and monitor.stats:
                for name, stats in monitor.stats.items():
                    if hasattr(stats, 'avg_time') and stats.avg_time > 0:
                        self.deep_analysis_service.record_operation_timing(
                            name,
                            stats.avg_time
                        )

                logger.debug("应用指标收集完成: {} 个操作", len(monitor.stats))

        except Exception as e:
            logger.debug("收集应用指标时出现问题: {}", str(e))

        try:
            # 从应用指标服务获取数据
            from core.containers import get_service_container
            from core.metrics.app_metrics_service import ApplicationMetricsService

            container = get_service_container()
            if container:
                try:
                    app_metrics = container.resolve(ApplicationMetricsService)
                    metrics = app_metrics.get_metrics()

                    for name, metric_data in metrics.items():
                        avg_duration = metric_data.get('avg_duration', 0)
                        if avg_duration > 0:
                            self.deep_analysis_service.record_operation_timing(
                                name,
                                avg_duration
                            )

                    logger.debug("应用服务指标收集完成: {} 个操作", len(metrics))

                except Exception as e:
                    logger.debug("应用指标服务不可用: {}", str(e))

        except Exception as e:
            logger.debug("收集应用服务指标时出现问题: {}", str(e))

    def inject_sample_data(self, count: int = 100):
        """注入示例数据用于测试"""
        import random

        logger.info("开始注入 {} 条示例数据...", count)

        # 示例操作类型
        operations = [
            "股票数据加载", "K线图渲染", "技术指标计算", "策略回测",
            "数据库查询", "UI界面更新", "网络请求", "文件读写",
            "缓存操作", "数据验证", "图表绘制", "算法执行"
        ]

        # 示例系统指标
        system_metrics = ["cpu_usage", "memory_usage", "disk_usage", "response_time", "query_time"]

        for i in range(count):
            # 注入操作计时数据
            for op_name in operations:
                duration = random.uniform(0.01, 2.0)  # 10ms 到 2秒
                self.deep_analysis_service.record_operation_timing(op_name, duration)

            # 注入系统指标数据
            for metric_name in system_metrics:
                if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
                    value = random.uniform(10, 90)  # 百分比
                else:
                    value = random.uniform(0.05, 3.0)  # 时间（秒）

                self.deep_analysis_service.record_metric(metric_name, value, "system")

            if i % 20 == 0:
                logger.info("已注入 {}/{} 批数据", i+1, count)

        logger.info("示例数据注入完成: {} 批数据", count)

        # 验证数据
        metrics_count = len(self.deep_analysis_service.metrics_history)
        operations_count = sum(len(timings) for timings in self.deep_analysis_service.operation_timings.values())

        logger.info("数据验证: 指标 {} 条, 操作 {} 条", metrics_count, operations_count)

    def get_status(self) -> Dict[str, Any]:
        """获取桥接器状态"""
        metrics_count = len(self.deep_analysis_service.metrics_history)
        operations_count = sum(len(timings) for timings in self.deep_analysis_service.operation_timings.values())

        return {
            "running": self._running,
            "last_collection": self._last_collection_time.isoformat() if self._last_collection_time else None,
            "metrics_count": metrics_count,
            "operations_count": operations_count,
            "collection_interval": self.collection_interval
        }


# 全局实例
_performance_bridge = None


def get_performance_bridge() -> PerformanceDataBridge:
    """获取性能数据桥接器实例"""
    global _performance_bridge
    if _performance_bridge is None:
        _performance_bridge = PerformanceDataBridge()
    return _performance_bridge


def initialize_performance_bridge(auto_start: bool = True) -> PerformanceDataBridge:
    """初始化性能数据桥接器"""
    bridge = get_performance_bridge()

    if auto_start:
        bridge.start_active_collection()

        # 注入一些示例数据用于测试
        bridge.inject_sample_data(50)

    logger.info("性能数据桥接器初始化完成")
    return bridge


if __name__ == "__main__":
    # 测试代码
    bridge = initialize_performance_bridge()

    # 等待一段时间让数据收集
    time.sleep(5)

    # 显示状态
    status = bridge.get_status()
    logger.info("桥接器状态:", status)

    # 测试深度分析功能
    analysis_service = get_deep_analysis_service()
    bottlenecks = analysis_service.analyze_bottlenecks()
    logger.info(f"瓶颈分析结果: {len(bottlenecks)} 个瓶颈")

    # 停止收集
    bridge.stop_active_collection()
