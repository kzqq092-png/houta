"""
智能模型选择机制UI组件包

提供智能模型选择功能的完整用户界面组件，包括：
- IntelligentModelControlPanel: 智能模型选择控制面板
- MarketStateMonitor: 市场状态监控界面
- ModelPerformancePanel: 模型性能展示界面
- PredictionResultsPanel: 预测结果展示界面
"""

from .control_panel import IntelligentModelControlPanel
from .market_monitor import MarketStateMonitor
from .performance_panel import ModelPerformancePanel
from .results_panel import PredictionResultsPanel

__all__ = [
    'IntelligentModelControlPanel',
    'MarketStateMonitor', 
    'ModelPerformancePanel',
    'PredictionResultsPanel'
]

__version__ = '1.0.0'