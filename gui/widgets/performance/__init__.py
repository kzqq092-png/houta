"""
性能监控模块

提供现代化的性能监控UI组件
"""

# 导入异步工作线程
from .workers.async_workers import (
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

# 导入UI组件
from .components.metric_card import ModernMetricCard
from .components.performance_chart import ModernPerformanceChart

# 导入标签页组件
from .tabs.system_monitor_tab import ModernSystemMonitorTab
from .tabs.ui_optimization_tab import ModernUIOptimizationTab
from .tabs.strategy_performance_tab import ModernStrategyPerformanceTab
from .tabs.algorithm_performance_tab import ModernAlgorithmPerformanceTab
from .tabs.auto_tuning_tab import ModernAutoTuningTab
from .tabs.system_health_tab import ModernSystemHealthTab
from .tabs.alert_config_tab import ModernAlertConfigTab
from .tabs.deep_analysis_tab import ModernDeepAnalysisTab

# 导入主要组件
from .unified_performance_widget import ModernUnifiedPerformanceWidget

# 注意：EnhancedStockPoolSettingsDialog 和 DataImportMonitoringWidget
# 在重构过程中发现这些类可能不存在或未正确迁移，暂时注释掉

# 为了兼容性，重新导出所有类
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
    'ModernUIOptimizationTab',
    'ModernStrategyPerformanceTab',
    'ModernAlgorithmPerformanceTab',
    'ModernAutoTuningTab',
    'ModernSystemHealthTab',
    'ModernAlertConfigTab',
    'ModernDeepAnalysisTab',
    'ModernUnifiedPerformanceWidget',
    # 'EnhancedStockPoolSettingsDialog',  # 暂时注释，类不存在
    # 'DataImportMonitoringWidget',       # 暂时注释，类不存在
]
