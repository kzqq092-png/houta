"""
GUI面板模块

包含各种功能面板组件
"""

from .stock_panel import StockManagementPanel
from .chart_panel import ChartAnalysisPanel
from .analysis_panel import AnalysisPanel
from .strategy_panel import StrategyManagementPanel
from .optimization_panel import OptimizationManagementPanel
from .bottom_panel import BottomPanel
from .analysis_tools_panel import AnalysisToolsPanel

__all__ = [
    'StockManagementPanel',
    'ChartAnalysisPanel',
    'AnalysisPanel',
    'StrategyManagementPanel',
    'OptimizationManagementPanel',
    'BottomPanel',
    'AnalysisToolsPanel'
]
