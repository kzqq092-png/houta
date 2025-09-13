from loguru import logger
"""
策略插件扩展模块

定义统一的策略插件接口和相关数据结构，支持多种策略框架的插件化。
"""

import pandas as pd
import numpy as np
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logger


class StrategyType(Enum):
    """策略类型"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    ARBITRAGE = "arbitrage"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    QUANTITATIVE = "quantitative"
    MACHINE_LEARNING = "machine_learning"
    MULTI_FACTOR = "multi_factor"
    HIGH_FREQUENCY = "high_frequency"
    CUSTOM = "custom"


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class TradeAction(Enum):
    """交易动作"""
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    ADJUST = "adjust"


class TradeStatus(Enum):
    """交易状态"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class StrategyLifecycle(Enum):
    """策略生命周期"""
    CREATED = "created"
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class AssetType(Enum):
    """资产类型"""
    STOCK = "stock"
    INDEX = "index"
    FUND = "fund"
    BOND = "bond"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CRYPTO = "crypto"
    FUTURES = "futures"
    OPTIONS = "options"


class TimeFrame(Enum):
    """时间周期"""
    TICK = "tick"
    SECOND_1 = "1s"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


@dataclass
class ParameterDef:
    """策略参数定义"""
    name: str
    type: type
    default_value: Any
    description: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    required: bool = True


@dataclass
class StrategyInfo:
    """策略信息"""
    name: str
    display_name: str
    description: str
    version: str
    author: str
    strategy_type: StrategyType
    parameters: List[ParameterDef] = field(default_factory=list)
    supported_assets: List[AssetType] = field(default_factory=list)
    time_frames: List[TimeFrame] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    strength: float
    timestamp: datetime
    price: float
    volume: Optional[int] = None
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    confidence: float = 1.0


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeResult:
    """交易结果"""
    trade_id: str
    symbol: str
    action: TradeAction
    quantity: float
    price: float
    timestamp: datetime
    commission: float
    status: TradeStatus
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    start_date: datetime
    end_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StandardMarketData:
    """标准化市场数据格式"""
    symbol: str
    datetime: pd.Series
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    volume: pd.Series
    amount: Optional[pd.Series] = None

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str = "unknown") -> 'StandardMarketData':
        """从DataFrame创建StandardMarketData"""
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Missing required columns: {', '.join(set(required_cols) - set(df.columns))}")

        return cls(
            symbol=symbol,
            datetime=df.index.to_series(),
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            volume=df['volume'],
            amount=df.get('amount')
        )

    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        data = {
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }
        if self.amount is not None:
            data['amount'] = self.amount

        df = pd.DataFrame(data, index=self.datetime)
        return df


@dataclass
class StrategyContext:
    """策略执行上下文"""
    symbol: str
    timeframe: TimeFrame
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage: float = 0.001
    benchmark: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IStrategyPlugin(ABC):
    """策略插件接口"""

    @property
    @abstractmethod
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        pass

    @abstractmethod
    def get_strategy_info(self) -> StrategyInfo:
        """获取策略信息"""
        pass

    @abstractmethod
    def initialize_strategy(self, context: StrategyContext, parameters: Dict[str, Any]) -> bool:
        """初始化策略"""
        pass

    @abstractmethod
    def generate_signals(self, market_data: StandardMarketData, context: StrategyContext) -> List[Signal]:
        """生成交易信号"""
        pass

    @abstractmethod
    def execute_trade(self, signal: Signal, context: StrategyContext) -> TradeResult:
        """执行交易"""
        pass

    @abstractmethod
    def update_position(self, trade_result: TradeResult, context: StrategyContext) -> Position:
        """更新持仓"""
        pass

    @abstractmethod
    def calculate_performance(self, context: StrategyContext) -> PerformanceMetrics:
        """计算策略性能"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """清理资源"""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """验证策略参数"""
        strategy_info = self.get_strategy_info()

        for param_def in strategy_info.parameters:
            param_name = param_def.name

            if param_def.required and param_name not in parameters:
                return False, f"Missing required parameter: {param_name}"

            if param_name in parameters:
                value = parameters[param_name]

                # 类型检查
                if not isinstance(value, param_def.type):
                    try:
                        value = param_def.type(value)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param_name}' must be of type {param_def.type.__name__}"

                # 范围检查
                if param_def.min_value is not None and value < param_def.min_value:
                    return False, f"Parameter '{param_name}' must be >= {param_def.min_value}"
                if param_def.max_value is not None and value > param_def.max_value:
                    return False, f"Parameter '{param_name}' must be <= {param_def.max_value}"

                # 选择检查
                if param_def.choices is not None and value not in param_def.choices:
                    return False, f"Parameter '{param_name}' must be one of {param_def.choices}"

        return True, ""


class StrategyPluginAdapter:
    """策略插件适配器"""

    def __init__(self, plugin: IStrategyPlugin, plugin_id: str):
        self.plugin = plugin
        self.plugin_id = plugin_id
        self.logger = logger

        # 性能统计
        self._signal_count = 0
        self._trade_count = 0
        self._total_signal_time = 0.0
        self._total_trade_time = 0.0
        self._error_count = 0
        self._last_activity = None

    def get_strategy_info(self) -> StrategyInfo:
        """获取策略信息"""
        try:
            return self.plugin.get_strategy_info()
        except Exception as e:
            self.logger.error(f"获取策略信息失败: {e}")
            raise

    def initialize_strategy(self, context: StrategyContext, parameters: Dict[str, Any]) -> bool:
        """初始化策略"""
        try:
            # 验证参数
            is_valid, error_msg = self.plugin.validate_parameters(parameters)
            if not is_valid:
                self.logger.error(f"参数验证失败: {error_msg}")
                return False

            # 初始化策略
            result = self.plugin.initialize_strategy(context, parameters)
            self._last_activity = datetime.now()
            return result
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"策略初始化失败: {e}")
            return False

    def generate_signals(self, market_data: StandardMarketData, context: StrategyContext) -> List[Signal]:
        """生成交易信号"""
        start_time = time.time()
        try:
            signals = self.plugin.generate_signals(market_data, context)

            # 更新统计
            self._signal_count += len(signals)
            self._total_signal_time += (time.time() - start_time) * 1000
            self._last_activity = datetime.now()

            return signals
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"信号生成失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        avg_signal_time = (self._total_signal_time / self._signal_count
                           if self._signal_count > 0 else 0.0)
        avg_trade_time = (self._total_trade_time / self._trade_count
                          if self._trade_count > 0 else 0.0)

        return {
            'plugin_id': self.plugin_id,
            'signal_count': self._signal_count,
            'trade_count': self._trade_count,
            'avg_signal_time_ms': avg_signal_time,
            'avg_trade_time_ms': avg_trade_time,
            'error_count': self._error_count,
            'last_activity': self._last_activity.isoformat() if self._last_activity else None
        }


def validate_strategy_plugin_interface(plugin_instance) -> bool:
    """验证插件是否实现了必要的IStrategyPlugin接口"""
    required_methods = [
        'get_strategy_info', 'initialize_strategy', 'generate_signals',
        'execute_trade', 'update_position', 'calculate_performance', 'cleanup'
    ]

    # 检查plugin_info属性
    if not hasattr(plugin_instance, 'plugin_info'):
        logger.error("策略插件缺少plugin_info属性")
        return False

    plugin_info = getattr(plugin_instance, 'plugin_info')
    if callable(plugin_info):
        try:
            plugin_info()
        except Exception as e:
            logger.error(f"策略插件plugin_info方法调用失败: {e}")
            return False
    elif not isinstance(plugin_info, dict):
        logger.error("策略插件plugin_info必须是字典或返回字典的方法")
        return False

    # 检查必要方法
    for method_name in required_methods:
        if not hasattr(plugin_instance, method_name):
            logger.error(f"策略插件缺少必要方法: {method_name}")
            return False

        method = getattr(plugin_instance, method_name)
        if not callable(method):
            logger.error(f"策略插件方法不可调用: {method_name}")
            return False

    return True
