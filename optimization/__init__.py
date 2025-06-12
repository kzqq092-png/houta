#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
形态识别算法自动优化系统
提供智能的算法优化、版本管理和UI集成功能
"""

from .performance_evaluator import PerformanceEvaluator
from .version_manager import VersionManager
from .algorithm_optimizer import AlgorithmOptimizer
from .auto_tuner import AutoTuner
from .ui_integration import UIIntegration
from .optimization_dashboard import OptimizationDashboard

__version__ = "1.0.0"
__author__ = "HiKyuu-UI Team"

__all__ = [
    'PerformanceEvaluator',
    'VersionManager',
    'AlgorithmOptimizer',
    'AutoTuner',
    'UIIntegration',
    'OptimizationDashboard'
]
