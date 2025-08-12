#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析标签页模块
"""

from .base_tab import BaseAnalysisTab
# from .professional_sentiment_tab import ProfessionalSentimentTab, SentimentAnalysisTab
from .enhanced_kline_sentiment_tab import EnhancedKLineSentimentTab
from .technical_tab import TechnicalAnalysisTab
from .trend_tab import TrendAnalysisTab
from .wave_tab import WaveAnalysisTab
from .wave_tab_pro import WaveAnalysisTabPro
from .sector_flow_tab import SectorFlowTab
from .sector_flow_tab_pro import SectorFlowTabPro
from .pattern_tab import PatternAnalysisTab
from .pattern_tab_pro import PatternAnalysisTabPro
from .hotspot_tab import HotspotAnalysisTab

__all__ = [
    'BaseAnalysisTab',
    # 'ProfessionalSentimentTab',
    # 'SentimentAnalysisTab',  # 向后兼容别名
    'EnhancedKLineSentimentTab',
    'TechnicalAnalysisTab',
    'TrendAnalysisTab',
    'WaveAnalysisTab',
    'WaveAnalysisTabPro',
    'SectorFlowTab',
    'SectorFlowTabPro',
    'PatternAnalysisTab',
    'PatternAnalysisTabPro',
    'HotspotAnalysisTab',
]
