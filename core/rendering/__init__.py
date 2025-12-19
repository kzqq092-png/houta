"""
核心渲染模块

提供统一的图表渲染接口和实现，支持多种渲染后端。
"""

from .interfaces import IChartRenderer, IRendererFactory
from .base_renderer import BaseChartRenderer
from .matplotlib_renderer import MatplotlibChartRenderer
from .factory import ChartRendererFactory, get_chart_renderer_factory, create_chart_renderer

__all__ = [
    'IChartRenderer',
    'IRendererFactory', 
    'BaseChartRenderer',
    'MatplotlibChartRenderer',
    'ChartRendererFactory',
    'get_chart_renderer_factory',
    'create_chart_renderer'
]

__version__ = '1.0.0'
__author__ = 'Hikyuu UI Team'