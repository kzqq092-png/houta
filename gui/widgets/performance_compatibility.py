"""
性能监控模块兼容性文件

提供从新模块结构到旧代码的兼容性导入
这个文件允许现有代码继续正常工作，同时逐步迁移到新的模块结构
"""

# 从新的模块结构导入所有类
from gui.widgets.performance.workers.async_workers import (
    AsyncDataWorker,
    AsyncStrategyWorker,
    SystemHealthCheckThread,
    AlertHistoryWorker,
    AsyncDataSignals,
    AlertHistorySignals,
    EmailTestWorker,
    SMSTestWorker,
    NotificationTestSignals
)

from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart
from gui.widgets.performance.tabs.system_monitor_tab import ModernSystemMonitorTab
# 2024量化交易优化版标签页 - 已重构和合并
from gui.widgets.performance.tabs.strategy_performance_tab import ModernStrategyPerformanceTab
from gui.widgets.performance.tabs.algorithm_optimization_tab import ModernAlgorithmOptimizationTab
from gui.widgets.performance.tabs.risk_control_center_tab import ModernRiskControlCenterTab
from gui.widgets.performance.tabs.trading_execution_monitor_tab import ModernTradingExecutionMonitorTab
from gui.widgets.performance.tabs.data_quality_monitor_tab import ModernDataQualityMonitorTab
from gui.widgets.performance.tabs.system_health_tab import ModernSystemHealthTab
# 已删除的标签页：UI优化、深度分析、算法性能、自动调优、告警配置
from gui.widgets.performance.unified_performance_widget import ModernUnifiedPerformanceWidget
# from gui.widgets.performance.dialogs.enhanced_stock_pool_settings_dialog import EnhancedStockPoolSettingsDialog  # 类不存在
# from gui.widgets.performance.data_import_monitoring_widget import DataImportMonitoringWidget  # 类不存在

# 重新导出所有类，保持兼容性
__all__ = [
    'AsyncDataWorker',
    'AsyncStrategyWorker',
    'SystemHealthCheckThread',
    'AlertHistoryWorker',
    'AsyncDataSignals',
    'AlertHistorySignals',
    'ModernMetricCard',
    'ModernPerformanceChart',
    'ModernSystemMonitorTab',
    'ModernStrategyPerformanceTab',
    'ModernAlgorithmOptimizationTab',
    'ModernRiskControlCenterTab',
    'ModernTradingExecutionMonitorTab',
    'ModernDataQualityMonitorTab',
    'ModernSystemHealthTab',
    # 兼容性：已删除的标签页类名不再导出
    'ModernUnifiedPerformanceWidget',
    # 'EnhancedStockPoolSettingsDialog',  # 暂时注释，类不存在
    # 'DataImportMonitoringWidget',       # 暂时注释，类不存在
]
