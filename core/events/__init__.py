"""
事件系统模块

提供事件驱动架构的核心组件，包括事件总线、事件定义和事件处理器。
"""

from .event_bus import EventBus, get_event_bus
from .events import (
    BaseEvent,
    StockSelectedEvent,
    ChartUpdateEvent,
    AnalysisCompleteEvent,
    DataUpdateEvent,
    ErrorEvent,
    UIUpdateEvent,
    ThemeChangedEvent,
    PerformanceUpdateEvent,
    IndicatorChangedEvent,
    UIDataReadyEvent,
    MultiScreenToggleEvent,
    TradeExecutedEvent,
    PositionUpdatedEvent,
    PatternSignalsDisplayEvent,
)
from .event_handler import EventHandler, AsyncEventHandler

__all__ = [
    'EventBus',
    'BaseEventHandler',
    'BaseEvent',
    'StockSelectedEvent',
    'ChartUpdateEvent',
    'AnalysisCompleteEvent',
    'DataUpdateEvent',
    'ErrorEvent',
    'UIUpdateEvent',
    'ThemeChangedEvent',
    'PerformanceUpdateEvent',
    'IndicatorChangedEvent',
    'UIDataReadyEvent',
    'MultiScreenToggleEvent',
    'TradeExecutedEvent',
    'PositionUpdatedEvent',
    'PatternSignalsDisplayEvent',
]
