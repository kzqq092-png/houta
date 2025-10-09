"""
业务逻辑层

包含应用程序的核心业务逻辑，独立于UI和数据访问层。
遵循领域驱动设计原则，将业务规则集中管理。
"""

from .stock_manager import StockManager

__all__ = [
    'StockManager',
    'PortfolioManager',
    'AnalysisManager',
    'TradingManager'
]
