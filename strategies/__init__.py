"""
策略模块
包含各种交易策略实现
"""

# 导出策略类供外部使用
try:
    from .adj_vwap_strategies import AdjMomentumPlugin, VWAPReversionPlugin
    from .strategy_manager import StrategyManager, get_strategy_manager
    __all__ = ['AdjMomentumPlugin', 'VWAPReversionPlugin', 'StrategyManager', 'get_strategy_manager']
except ImportError:
    __all__ = []

# 版本信息
__version__ = '1.0.0'
