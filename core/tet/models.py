"""
TET框架数据模型定义

定义标准化的数据请求和响应模型，确保数据处理的一致性。
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class AssetType(Enum):
    """资产类型枚举"""
    STOCK = "stock"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"
    FUND = "fund"
    BOND = "bond"
    INDEX = "index"
    OPTION = "option"


class DataType(Enum):
    """数据类型枚举"""
    KDATA = "kdata"              # K线数据
    TICK = "tick"                # 分笔数据
    ORDER_BOOK = "order_book"    # 订单簿
    FUNDAMENTAL = "fundamental"   # 基本面数据
    NEWS = "news"                # 新闻数据
    SENTIMENT = "sentiment"      # 情绪数据
    TECHNICAL = "technical"      # 技术指标
    REALTIME = "realtime"        # 实时行情


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"      # 优秀 (>0.95)
    GOOD = "good"               # 良好 (0.8-0.95)
    FAIR = "fair"               # 一般 (0.6-0.8)
    POOR = "poor"               # 较差 (<0.6)


@dataclass
class StandardQuery:
    """标准化查询请求"""
    symbol: str                                    # 标的代码
    asset_type: AssetType = AssetType.STOCK       # 资产类型
    data_type: DataType = DataType.KDATA          # 数据类型
    period: str = "D"                             # 周期 (1/5/15/30/60/D/W/M)
    start_date: Optional[datetime] = None         # 开始日期
    end_date: Optional[datetime] = None           # 结束日期
    count: Optional[int] = None                   # 数据条数
    parameters: Dict[str, Any] = field(default_factory=dict)  # 额外参数

    def __post_init__(self):
        """后处理初始化"""
        # 标准化symbol格式
        self.symbol = self.symbol.upper().strip()

        # 验证参数
        if not self.symbol:
            raise ValueError("symbol不能为空")

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("开始日期不能晚于结束日期")

    def to_cache_key(self) -> str:
        """生成缓存键"""
        key_parts = [
            self.symbol,
            self.asset_type.value,
            self.data_type.value,
            self.period,
            str(self.start_date) if self.start_date else '',
            str(self.end_date) if self.end_date else '',
            str(self.count) if self.count else '',
            str(sorted(self.parameters.items()))
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'asset_type': self.asset_type.value,
            'data_type': self.data_type.value,
            'period': self.period,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'count': self.count,
            'parameters': self.parameters
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardQuery':
        """从字典创建实例"""
        return cls(
            symbol=data['symbol'],
            asset_type=AssetType(data.get('asset_type', 'stock')),
            data_type=DataType(data.get('data_type', 'kdata')),
            period=data.get('period', 'D'),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            count=data.get('count'),
            parameters=data.get('parameters', {})
        )


@dataclass
class StandardData:
    """标准化数据响应"""
    data: pd.DataFrame                            # 数据内容
    metadata: Dict[str, Any]                      # 元数据
    source: str                                   # 数据源
    timestamp: datetime                           # 时间戳
    quality_score: float = 1.0                    # 质量评分 (0-1)

    def __post_init__(self):
        """后处理初始化"""
        # 验证数据
        if self.data is None:
            raise ValueError("data不能为None")

        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("data必须是pandas.DataFrame类型")

        # 验证质量评分
        if not 0 <= self.quality_score <= 1:
            raise ValueError("quality_score必须在0-1之间")

    @property
    def quality_level(self) -> DataQuality:
        """获取数据质量等级"""
        if self.quality_score > 0.95:
            return DataQuality.EXCELLENT
        elif self.quality_score > 0.8:
            return DataQuality.GOOD
        elif self.quality_score > 0.6:
            return DataQuality.FAIR
        else:
            return DataQuality.POOR

    @property
    def record_count(self) -> int:
        """获取记录数量"""
        return len(self.data)

    @property
    def is_empty(self) -> bool:
        """检查数据是否为空"""
        return self.data.empty

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'data': self.data.to_dict('records'),
            'metadata': self.metadata,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'quality_score': self.quality_score,
            'record_count': self.record_count
        }


@dataclass
class DataRequest:
    """数据请求包装器"""
    request_id: str                               # 请求ID
    query: StandardQuery                          # 查询对象
    priority: int = 0                            # 优先级 (0=最高)
    timeout: int = 30                            # 超时时间(秒)
    retry_count: int = 3                         # 重试次数
    callback: Optional[callable] = None          # 回调函数

    def __post_init__(self):
        """后处理初始化"""
        if not self.request_id:
            # 自动生成请求ID
            self.request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"


@dataclass
class DataResponse:
    """数据响应包装器"""
    request_id: str                               # 请求ID
    success: bool                                 # 是否成功
    data: Optional[StandardData] = None           # 数据内容
    error: Optional[str] = None                   # 错误信息
    processing_time: float = 0.0                 # 处理时间(秒)
    cache_hit: bool = False                      # 是否命中缓存

    def __post_init__(self):
        """后处理初始化"""
        if self.success and self.data is None:
            raise ValueError("成功响应必须包含数据")

        if not self.success and self.error is None:
            raise ValueError("失败响应必须包含错误信息")


@dataclass
class StockInfo:
    """股票信息模型"""
    code: str                                     # 股票代码
    name: str                                     # 股票名称
    market: str                                   # 市场代码
    industry: str = "其他"                        # 行业分类
    listing_date: Optional[datetime] = None       # 上市日期
    total_shares: Optional[float] = None          # 总股本
    float_shares: Optional[float] = None          # 流通股本
    market_cap: Optional[float] = None            # 市值

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'market': self.market,
            'industry': self.industry,
            'listing_date': self.listing_date.isoformat() if self.listing_date else None,
            'total_shares': self.total_shares,
            'float_shares': self.float_shares,
            'market_cap': self.market_cap
        }


@dataclass
class BacktestResult:
    """回测结果模型"""
    strategy_name: str                            # 策略名称
    start_date: datetime                          # 开始日期
    end_date: datetime                            # 结束日期
    total_return: float                           # 总收益率
    annual_return: float                          # 年化收益率
    max_drawdown: float                           # 最大回撤
    sharpe_ratio: float                           # 夏普比率
    win_rate: float                               # 胜率
    trade_count: int                              # 交易次数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'trade_count': self.trade_count
        }
