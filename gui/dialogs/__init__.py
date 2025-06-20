"""
GUI对话框模块
包含系统中所有对话框组件
"""

from .plugin_manager_dialog import PluginManagerDialog
from .language_settings_dialog import LanguageSettingsDialog
from .advanced_search_dialog import AdvancedSearchDialog
from .indicator_params_dialog import IndicatorParamsDialog
from .database_admin_dialog import DatabaseAdminDialog
from .interval_stat_dialog import IntervalStatDialog

__all__ = [
    'PluginManagerDialog',
    'LanguageSettingsDialog',
    'AdvancedSearchDialog',
    'IndicatorParamsDialog',
    'DatabaseAdminDialog',
    'IntervalStatDialog'
]
