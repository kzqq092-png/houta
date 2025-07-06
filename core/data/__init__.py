"""
数据访问层

提供统一的数据访问接口，支持多种数据源。
"""

from .repository import (
    BaseRepository,
    StockRepository,
    KlineRepository,
    MarketRepository
)

from .models import (
    StockInfo,
    KlineData,
    MarketData
)

from .data_access import DataAccess

__all__ = [
    'BaseRepository',
    'StockRepository',
    'KlineRepository',
    'MarketRepository',
    'StockInfo',
    'KlineData',
    'MarketData',
    'DataAccess'
]
