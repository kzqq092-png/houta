from loguru import logger
"""
策略事件系统

定义策略生命周期中的各种事件，支持事件驱动的策略管理。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .strategy_extensions import (
    Signal, TradeResult, Position, PerformanceMetrics,
    StrategyContext, StrategyLifecycle
)

logger = logger


class EventType(Enum):
    """事件类型"""
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    STRATEGY_PAUSED = "strategy_paused"
    STRATEGY_RESUMED = "strategy_resumed"
    SIGNAL_GENERATED = "signal_generated"
    TRADE_EXECUTED = "trade_executed"
    POSITION_UPDATED = "position_updated"
    STRATEGY_ERROR = "strategy_error"
    MARKET_OPENED = "market_opened"
    MARKET_CLOSED = "market_closed"
    BAR_UPDATED = "bar_updated"
    ORDER_FILLED = "order_filled"
    PERFORMANCE_UPDATED = "performance_updated"


@dataclass
class BaseEvent:
    """基础事件类"""
    timestamp: datetime
    strategy_id: str
    event_type: EventType = field(init=False)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyStartedEvent(BaseEvent):
    """策略启动事件"""
    context: Optional[StrategyContext] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_STARTED


@dataclass
class StrategyStoppedEvent(BaseEvent):
    """策略停止事件"""
    reason: str = ""
    performance: Optional[PerformanceMetrics] = None

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_STOPPED


@dataclass
class StrategyPausedEvent(BaseEvent):
    """策略暂停事件"""
    reason: str = ""

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_PAUSED


@dataclass
class StrategyResumedEvent(BaseEvent):
    """策略恢复事件"""

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_RESUMED


@dataclass
class SignalGeneratedEvent(BaseEvent):
    """信号生成事件"""
    signals: List[Signal] = field(default_factory=list)

    def __post_init__(self):
        self.event_type = EventType.SIGNAL_GENERATED


@dataclass
class TradeExecutedEvent(BaseEvent):
    """交易执行事件"""
    trade_result: Optional[TradeResult] = None
    signal: Optional[Signal] = None

    def __post_init__(self):
        self.event_type = EventType.TRADE_EXECUTED


@dataclass
class PositionUpdatedEvent(BaseEvent):
    """持仓更新事件"""
    position: Optional[Position] = None
    previous_position: Optional[Position] = None

    def __post_init__(self):
        self.event_type = EventType.POSITION_UPDATED


@dataclass
class StrategyErrorEvent(BaseEvent):
    """策略错误事件"""
    error_message: str = ""
    error: Optional[Exception] = None
    stack_trace: Optional[str] = None

    def __post_init__(self):
        self.event_type = EventType.STRATEGY_ERROR


@dataclass
class MarketOpenedEvent(BaseEvent):
    """市场开盘事件"""
    market_name: str = ""

    def __post_init__(self):
        self.event_type = EventType.MARKET_OPENED


@dataclass
class MarketClosedEvent(BaseEvent):
    """市场收盘事件"""
    market_name: str = ""

    def __post_init__(self):
        self.event_type = EventType.MARKET_CLOSED


@dataclass
class BarUpdatedEvent(BaseEvent):
    """K线更新事件"""
    symbol: str = ""
    timeframe: str = ""
    bar_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.event_type = EventType.BAR_UPDATED


@dataclass
class OrderFilledEvent(BaseEvent):
    """订单成交事件"""
    trade_result: Optional[TradeResult] = None

    def __post_init__(self):
        self.event_type = EventType.ORDER_FILLED


@dataclass
class PerformanceUpdatedEvent(BaseEvent):
    """性能更新事件"""
    performance: Optional[PerformanceMetrics] = None

    def __post_init__(self):
        self.event_type = EventType.PERFORMANCE_UPDATED


class IEventHandler(ABC):
    """事件处理器接口"""

    @abstractmethod
    def handle_event(self, event: BaseEvent) -> None:
        """
        处理事件

        Args:
            event: 事件对象
        """
        pass

    @abstractmethod
    def can_handle(self, event_type: EventType) -> bool:
        """
        检查是否可以处理指定类型的事件

        Args:
            event_type: 事件类型

        Returns:
            bool: 是否可以处理
        """
        pass


class EventBus:
    """
    事件总线

    负责事件的发布、订阅和分发
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[IEventHandler]] = {}
        self._global_handlers: List[IEventHandler] = []
        self._event_history: List[BaseEvent] = []
        self._max_history_size = 1000
        self.logger = logger

    def subscribe(self, event_type: EventType, handler: IEventHandler) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            self.logger.debug(f"订阅事件: {event_type.value}, 处理器: {handler.__class__.__name__}")

    def subscribe_all(self, handler: IEventHandler) -> None:
        """
        订阅所有事件

        Args:
            handler: 事件处理器
        """
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)
            self.logger.debug(f"订阅所有事件, 处理器: {handler.__class__.__name__}")

    def unsubscribe(self, event_type: EventType, handler: IEventHandler) -> None:
        """
        取消订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            self.logger.debug(f"取消订阅事件: {event_type.value}, 处理器: {handler.__class__.__name__}")

    def unsubscribe_all(self, handler: IEventHandler) -> None:
        """
        取消订阅所有事件

        Args:
            handler: 事件处理器
        """
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)
            self.logger.debug(f"取消订阅所有事件, 处理器: {handler.__class__.__name__}")

    def publish(self, event: BaseEvent) -> None:
        """
        发布事件

        Args:
            event: 事件对象
        """
        try:
            # 记录事件历史
            self._add_to_history(event)

            # 通知全局处理器
            for handler in self._global_handlers:
                try:
                    if handler.can_handle(event.event_type):
                        handler.handle_event(event)
                except Exception as e:
                    self.logger.error(f"全局事件处理器错误: {e}")

            # 通知特定类型处理器
            if event.event_type in self._handlers:
                for handler in self._handlers[event.event_type]:
                    try:
                        handler.handle_event(event)
                    except Exception as e:
                        self.logger.error(f"事件处理器错误: {e}")

            self.logger.debug(f"发布事件: {event.event_type.value}, 策略: {event.strategy_id}")

        except Exception as e:
            self.logger.error(f"事件发布失败: {e}")

    def _add_to_history(self, event: BaseEvent) -> None:
        """添加事件到历史记录"""
        self._event_history.append(event)

        # 限制历史记录大小
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]

    def get_event_history(self,
                          strategy_id: Optional[str] = None,
                          event_type: Optional[EventType] = None,
                          limit: int = 100) -> List[BaseEvent]:
        """
        获取事件历史

        Args:
            strategy_id: 策略ID过滤
            event_type: 事件类型过滤
            limit: 返回数量限制

        Returns:
            List[BaseEvent]: 事件列表
        """
        events = self._event_history

        # 过滤策略ID
        if strategy_id:
            events = [e for e in events if e.strategy_id == strategy_id]

        # 过滤事件类型
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # 限制数量
        return events[-limit:] if limit > 0 else events

    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()
        self.logger.info("事件历史已清空")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取事件统计信息

        Returns:
            Dict: 统计信息
        """
        event_counts = {}
        strategy_counts = {}

        for event in self._event_history:
            # 事件类型统计
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # 策略统计
            strategy_id = event.strategy_id
            strategy_counts[strategy_id] = strategy_counts.get(strategy_id, 0) + 1

        return {
            'total_events': len(self._event_history),
            'event_type_counts': event_counts,
            'strategy_counts': strategy_counts,
            'handler_counts': {
                event_type.value: len(handlers)
                for event_type, handlers in self._handlers.items()
            },
            'global_handlers': len(self._global_handlers)
        }


class LoggingEventHandler(IEventHandler):
    """日志事件处理器"""

    def __init__(self, log_level: str = "INFO"):
        self.logger = logger
        self.log_level = log_level

    def handle_event(self, event: BaseEvent) -> None:
        """处理事件并记录日志"""
        message = f"[{event.event_type.value.upper()}] 策略: {event.strategy_id}"

        if isinstance(event, StrategyStartedEvent):
            message += f" 已启动, 初始资金: {event.context.initial_capital}"
        elif isinstance(event, StrategyStoppedEvent):
            message += f" 已停止, 原因: {event.reason}"
        elif isinstance(event, SignalGeneratedEvent):
            message += f" 生成 {len(event.signals)} 个信号"
        elif isinstance(event, TradeExecutedEvent):
            trade = event.trade_result
            message += f" 执行交易: {trade.action.value} {trade.symbol} {trade.quantity}@{trade.price}"
        elif isinstance(event, StrategyErrorEvent):
            message += f" 发生错误: {event.error_message}"
            self.logger.error(message)
            return

        # 使用Loguru的动态日志级别
        if self.log_level.upper() == "DEBUG":
            self.logger.debug(message)
        elif self.log_level.upper() == "WARNING":
            self.logger.warning(message)
        elif self.log_level.upper() == "ERROR":
            self.logger.error(message)
        else:  # INFO 或其他
            self.logger.info(message)

    def can_handle(self, event_type: EventType) -> bool:
        """可以处理所有事件类型"""
        return True


class MetricsEventHandler(IEventHandler):
    """指标收集事件处理器"""

    def __init__(self):
        self.metrics = {
            'strategy_starts': 0,
            'strategy_stops': 0,
            'signals_generated': 0,
            'trades_executed': 0,
            'errors_occurred': 0
        }

    def handle_event(self, event: BaseEvent) -> None:
        """处理事件并更新指标"""
        if isinstance(event, StrategyStartedEvent):
            self.metrics['strategy_starts'] += 1
        elif isinstance(event, StrategyStoppedEvent):
            self.metrics['strategy_stops'] += 1
        elif isinstance(event, SignalGeneratedEvent):
            self.metrics['signals_generated'] += len(event.signals)
        elif isinstance(event, TradeExecutedEvent):
            self.metrics['trades_executed'] += 1
        elif isinstance(event, StrategyErrorEvent):
            self.metrics['errors_occurred'] += 1

    def can_handle(self, event_type: EventType) -> bool:
        """处理特定类型的事件"""
        return event_type in [
            EventType.STRATEGY_STARTED,
            EventType.STRATEGY_STOPPED,
            EventType.SIGNAL_GENERATED,
            EventType.TRADE_EXECUTED,
            EventType.STRATEGY_ERROR
        ]

    def get_metrics(self) -> Dict[str, int]:
        """获取收集的指标"""
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """重置指标"""
        for key in self.metrics:
            self.metrics[key] = 0


# 全局事件总线实例
global_event_bus = EventBus()

# 默认事件处理器
default_logging_handler = LoggingEventHandler()
default_metrics_handler = MetricsEventHandler()

# 注册默认处理器
global_event_bus.subscribe_all(default_logging_handler)
global_event_bus.subscribe_all(default_metrics_handler)


def publish_strategy_event(event: BaseEvent) -> None:
    """
    发布策略事件的便捷函数

    Args:
        event: 事件对象
    """
    global_event_bus.publish(event)


def get_event_metrics() -> Dict[str, Any]:
    """
    获取事件指标的便捷函数

    Returns:
        Dict: 事件指标
    """
    return {
        'bus_statistics': global_event_bus.get_statistics(),
        'metrics_handler': default_metrics_handler.get_metrics()
    }
