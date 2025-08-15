"""
事件定义模块

定义系统中使用的各种事件类型，所有事件都继承自BaseEvent。
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Union
import uuid

from ..plugin_types import AssetType


@dataclass
class BaseEvent(ABC):
    """
    事件基类

    所有系统事件都应该继承此类。
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """事件创建后的初始化处理"""
        if not self.source:
            self.source = self.__class__.__name__


@dataclass
class AssetSelectedEvent(BaseEvent):
    """
    资产选择事件（通用）

    当用户选择任意类型资产时触发，支持股票、加密货币、期货等。
    """
    symbol: str = ""                        # 交易代码
    name: str = ""                          # 资产名称
    asset_type: AssetType = AssetType.STOCK  # 资产类型
    market: str = ""                        # 市场
    period: str = ""                        # 周期：日线、周线、月线等
    time_range: str = ""                    # 时间范围：最近7天、最近30天等
    chart_type: str = ""                    # 图表类型：K线图、分时图等

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'symbol': self.symbol,
            'name': self.name,
            'asset_type': self.asset_type.value if isinstance(self.asset_type, AssetType) else self.asset_type,
            'market': self.market,
            'period': self.period,
            'time_range': self.time_range,
            'chart_type': self.chart_type
        })


@dataclass
class StockSelectedEvent(AssetSelectedEvent):
    """
    股票选择事件（向后兼容）

    继承自AssetSelectedEvent，保持与现有代码的兼容性。
    """
    stock_code: str = ""  # 向后兼容属性
    stock_name: str = ""  # 向后兼容属性

    def __init__(self, stock_code: str = "", stock_name: str = "",
                 market: str = "", period: str = "", time_range: str = "",
                 chart_type: str = "", **kwargs):
        # 使用父类构造函数，映射股票特定字段到通用字段
        super().__init__(
            symbol=stock_code,
            name=stock_name,
            asset_type=AssetType.STOCK,
            market=market,
            period=period,
            time_range=time_range,
            chart_type=chart_type,
            **kwargs
        )

        # 保持向后兼容的属性
        self.stock_code = stock_code
        self.stock_name = stock_name

    def __post_init__(self):
        super().__post_init__()
        # 确保向后兼容的数据字段
        self.data.update({
            'stock_code': self.stock_code,
            'stock_name': self.stock_name
        })


@dataclass
class AssetDataReadyEvent(BaseEvent):
    """
    资产数据就绪事件（通用）

    当任意类型资产的数据加载完成时触发。
    """
    symbol: str = ""
    name: str = ""
    asset_type: AssetType = AssetType.STOCK
    market: str = ""
    data_type: str = "kline"  # kline, realtime, analysis等
    data: Any = None

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'symbol': self.symbol,
            'name': self.name,
            'asset_type': self.asset_type.value if isinstance(self.asset_type, AssetType) else self.asset_type,
            'market': self.market,
            'data_type': self.data_type
        })


@dataclass
class UIDataReadyEvent(AssetDataReadyEvent):
    """
    UI数据就绪事件（向后兼容）

    继承自AssetDataReadyEvent，保持与现有UI代码的兼容性。
    """
    stock_code: str = ""  # 向后兼容
    stock_name: str = ""  # 向后兼容
    kline_data: Any = None  # 向后兼容

    def __init__(self, stock_code: str = "", stock_name: str = "",
                 kline_data: Any = None, market: str = "", **kwargs):
        super().__init__(
            symbol=stock_code,
            name=stock_name,
            asset_type=AssetType.STOCK,
            market=market,
            data_type="kline",
            data=kline_data,
            **kwargs
        )

        # 向后兼容属性
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.kline_data = kline_data

    def __post_init__(self):
        super().__post_init__()
        # 向后兼容的数据字段
        self.data.update({
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'kline_data': self.kline_data
        })


@dataclass
class ChartUpdateEvent(BaseEvent):
    """
    图表更新事件

    当图表需要更新时触发。
    """
    stock_code: str = ""
    chart_type: str = ""
    period: str = ""
    indicators: list = field(default_factory=list)
    time_range: int = -365

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'stock_code': self.stock_code,
            'chart_type': self.chart_type,
            'period': self.period,
            'indicators': self.indicators,
            'time_range': self.time_range
        })


@dataclass
class AnalysisCompleteEvent(BaseEvent):
    """
    分析完成事件

    当股票分析完成时触发。
    """
    stock_code: str = ""
    analysis_type: str = ""
    results: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'stock_code': self.stock_code,
            'analysis_type': self.analysis_type,
            'results': self.results
        })


@dataclass
class DataUpdateEvent(BaseEvent):
    """
    数据更新事件

    当数据发生更新时触发。
    """
    data_type: str = ""
    stock_code: str = ""
    update_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'data_type': self.data_type,
            'stock_code': self.stock_code,
            'update_info': self.update_info
        })


@dataclass
class ErrorEvent(BaseEvent):
    """
    错误事件

    当系统发生错误时触发。
    """
    error_type: str = ""
    error_message: str = ""
    error_traceback: str = ""
    severity: str = "error"  # error, warning, info

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'severity': self.severity
        })


@dataclass
class UIUpdateEvent(BaseEvent):
    """
    UI更新事件

    当UI需要更新时触发。
    """
    component: str = ""
    action: str = ""
    update_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'component': self.component,
            'action': self.action,
            'update_data': self.update_data
        })


@dataclass
class ThemeChangedEvent(BaseEvent):
    """
    主题变更事件

    当系统主题发生变更时触发。
    """
    theme_name: str = ""
    theme_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'theme_name': self.theme_name,
            'theme_config': self.theme_config
        })


@dataclass
class PerformanceUpdateEvent(BaseEvent):
    """
    性能更新事件

    当系统性能指标更新时触发。
    """
    metrics: Dict[str, Union[int, float, str]] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'metrics': self.metrics
        })


@dataclass
class IndicatorChangedEvent(BaseEvent):
    """
    指标变化事件

    当用户选择或取消选择指标时触发。
    """
    selected_indicators: list = field(default_factory=list)
    indicator_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'selected_indicators': self.selected_indicators,
            'indicator_params': self.indicator_params
        })


@dataclass
class UIDataReadyEvent(BaseEvent):
    """
    UI数据准备就绪事件

    当Coordinator准备好所有UI所需的数据时触发。
    这个事件携带了用于更新UI的完整数据包，避免了各个面板的重复加载。
    """
    ui_data: Dict[str, Any] = field(default_factory=dict)
    stock_code: str = ""
    stock_name: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'ui_data': self.ui_data,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name
        })


@dataclass
class MultiScreenToggleEvent(BaseEvent):
    """
    多屏模式切换事件

    当系统在单屏模式和多屏模式之间切换时触发。
    """
    is_multi_screen: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'is_multi_screen': self.is_multi_screen
        })


@dataclass
class TradeExecutedEvent(BaseEvent):
    """
    交易执行事件

    当交易（买入/卖出）执行完成时触发。
    """
    trade_record: Any = None  # TradeRecord object

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'trade_record': self.trade_record
        })


@dataclass
class PositionUpdatedEvent(BaseEvent):
    """
    持仓更新事件

    当持仓信息发生变化时触发。
    """
    portfolio: Any = None  # Portfolio object
    updated_positions: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'portfolio': self.portfolio,
            'updated_positions': self.updated_positions
        })


@dataclass
class PatternSignalsDisplayEvent(BaseEvent):
    """
    形态信号显示事件

    当用户在形态分析表中点击某一行时触发，通知图表显示和高亮相关信号。
    """
    pattern_name: str = ""
    all_signal_indices: list = field(default_factory=list)
    highlighted_signal_index: int = -1

    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'pattern_name': self.pattern_name,
            'all_signal_indices': self.all_signal_indices,
            'highlighted_signal_index': self.highlighted_signal_index
        })
