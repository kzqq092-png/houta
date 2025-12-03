#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
渲染引擎模块

提供PyQtGraph高性能图表渲染能力，替代matplotlib的静态图表渲染

作者: FactorWeave-Quant团队
版本: 1.0
"""

from .pyqtgraph_engine import (
    PyQtGraphEngine,
    PyQtGraphChartWidget,
    LineChartWidget,
    CandlestickChartWidget,
    RealTimeChartWidget,
    ChartConfig,
    ChartType,
    get_pyqtgraph_engine,
    reset_pyqtgraph_engine
)

from .chart_manager import ChartManager, get_chart_manager
from .performance_optimizer import ChartPerformanceOptimizer
from .matplotlib_adapter import MatplotlibAdapter

__all__ = [
    # 核心引擎
    'PyQtGraphEngine',
    'PyQtGraphChartWidget',
    'LineChartWidget',
    'CandlestickChartWidget',
    'RealTimeChartWidget',
    
    # 配置和类型
    'ChartConfig',
    'ChartType',
    
    # 管理器
    'ChartManager',
    'get_chart_manager',
    'ChartPerformanceOptimizer',
    
    # 适配器和处理器
    'MatplotlibAdapter',
    
    # 工具函数
    'get_pyqtgraph_engine',
    'reset_pyqtgraph_engine'
]