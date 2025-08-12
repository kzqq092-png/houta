"""
数据源插件专用数据模型
为数据源插件提供统一的数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class StockInfo:
    """股票/证券基本信息"""
    code: str                               # 证券代码
    name: str                               # 证券名称
    market: str                            # 市场
    currency: str = 'CNY'                  # 货币
    sector: Optional[str] = None           # 板块/行业分类
    industry: Optional[str] = None         # 具体行业
    list_date: Optional[datetime] = None   # 上市日期
    extra_info: Dict[str, Any] = field(default_factory=dict)  # 额外信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'market': self.market,
            'currency': self.currency,
            'sector': self.sector,
            'industry': self.industry,
            'list_date': self.list_date.isoformat() if self.list_date else None,
            'extra_info': self.extra_info
        }


@dataclass
class KlineData:
    """K线数据"""
    symbol: str                            # 证券代码
    timestamp: datetime                    # 时间戳
    open: float                           # 开盘价
    high: float                           # 最高价
    low: float                            # 最低价
    close: float                          # 收盘价
    volume: float                         # 成交量
    frequency: str = "1d"                 # 频率
    extra_info: Dict[str, Any] = field(default_factory=dict)  # 额外信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'frequency': self.frequency,
            'extra_info': self.extra_info
        }


@dataclass
class MarketData:
    """实时市场数据"""
    symbol: str                            # 证券代码
    current_price: float                   # 当前价格
    open_price: float                     # 开盘价
    high_price: float                     # 最高价
    low_price: float                      # 最低价
    volume: float                         # 成交量
    timestamp: datetime                   # 时间戳
    change_amount: float = 0.0            # 涨跌额
    change_percent: float = 0.0           # 涨跌幅
    extra_info: Dict[str, Any] = field(default_factory=dict)  # 额外信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'current_price': self.current_price,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'change_amount': self.change_amount,
            'change_percent': self.change_percent,
            'extra_info': self.extra_info
        }


@dataclass
class QueryParams:
    """查询参数"""
    symbol: str                           # 证券代码
    start_date: Optional[datetime] = None  # 开始日期
    end_date: Optional[datetime] = None   # 结束日期
    frequency: str = "1d"                 # 频率
    limit: Optional[int] = None           # 数量限制
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 额外参数


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    is_healthy: bool                      # 是否健康
    message: str                          # 状态消息
    response_time: float = 0.0           # 响应时间(毫秒)
    extra_info: Dict[str, Any] = field(default_factory=dict)  # 额外信息
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_healthy': self.is_healthy,
            'message': self.message,
            'response_time': self.response_time,
            'extra_info': self.extra_info,
            'timestamp': self.timestamp.isoformat()
        }
