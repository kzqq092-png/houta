# core/metrics/events.py
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SystemResourceUpdated:
    """当系统资源指标被采集时发布的事件。"""
    event_type: ClassVar[str] = "SystemResourceUpdated"
    cpu_percent: float
    memory_percent: float
    disk_percent: float


@dataclass(frozen=True)
class ApplicationMetricRecorded:
    """当一个被监控的操作执行完成时发布的事件。"""
    event_type: ClassVar[str] = "ApplicationMetricRecorded"
    operation_name: str
    duration: float  # in seconds
    was_successful: bool
