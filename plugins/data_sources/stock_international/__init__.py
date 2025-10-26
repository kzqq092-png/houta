"""
国际股票数据源插件目录

包含国际股票市场的数据源插件（非A股）
"""

# 插件列表
INTERNATIONAL_STOCK_PLUGINS = [
    'wind_plugin',           # Wind万得（专业）
    'yahoo_finance_plugin'   # 雅虎财经（美股）
]

__all__ = INTERNATIONAL_STOCK_PLUGINS
