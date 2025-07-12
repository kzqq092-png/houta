# core/metrics/resource_service.py
import threading
import time
import psutil
from typing import Optional

from core.metrics import SystemResourceUpdated
from core.events.event_bus import EventBus
from core.config import config_manager


class SystemResourceService:
    """一个后台服务，定期监控并发布系统资源（CPU、内存、磁盘）使用情况。"""

    def __init__(self, event_bus: EventBus, interval: Optional[float] = None):
        """
        初始化系统资源服务。

        :param event_bus: 事件总线实例。
        :param interval: 监控间隔（秒）。如果为None，则从配置中读取。
        """
        self.event_bus = event_bus
        # 优先使用传入的interval，否则从配置中心获取，最后使用默认值
        self._interval = interval or config_manager.get('monitoring.resource_interval', 1.0)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """启动后台监控线程。"""
        if self._thread is not None and self._thread.is_alive():
            return  # 服务已在运行

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("系统资源监控服务已启动。")

    def _run(self):
        """监控循环，定期采集并发布资源数据。"""
        while not self._stop_event.is_set():
            try:
                # 采集数据
                cpu_percent = psutil.cpu_percent()
                memory_info = psutil.virtual_memory()
                # 尝试获取根目录的磁盘使用情况
                try:
                    disk_usage = psutil.disk_usage('/')
                    disk_percent = disk_usage.percent
                except FileNotFoundError:
                    # 在Windows上，根目录可能是'C:\'
                    disk_usage = psutil.disk_usage('C:\\')
                    disk_percent = disk_usage.percent

                # 创建事件
                event = SystemResourceUpdated(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_info.percent,
                    disk_percent=disk_percent,
                )

                # 发布事件
                self.event_bus.publish(event)

            except Exception as e:
                print(f"资源监控线程错误: {e}")

            # 等待下一个间隔
            self._stop_event.wait(self._interval)

    def dispose(self):
        """停止后台监控线程。"""
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()  # 等待线程完全停止
            print("系统资源监控服务已停止。")
