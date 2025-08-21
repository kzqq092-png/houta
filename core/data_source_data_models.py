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
    symbol: str                               # 股票代码
    start_date: Optional[str] = None         # 开始日期
    end_date: Optional[str] = None           # 结束日期
    period: str = "D"                        # 周期 (D-日, W-周, M-月)
    count: Optional[int] = None              # 数量限制
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 额外参数


# HealthCheckResult类已移至core/data_source_extensions.py进行统一管理
# 请从core.data_source_extensions导入HealthCheckResult
