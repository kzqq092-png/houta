"""
Core Services Package

提供统一的指标计算服务和UI适配器
"""

from .indicator_service import IndicatorCalculationService, get_indicator_service
from .indicator_ui_adapter import IndicatorUIAdapter, get_indicator_ui_adapter

__all__ = [
    'IndicatorCalculationService',
    'get_indicator_service',
    'IndicatorUIAdapter',
    'get_indicator_ui_adapter',
]
