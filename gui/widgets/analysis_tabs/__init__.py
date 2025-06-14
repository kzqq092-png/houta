"""
Analysis tabs package
"""

from .base_tab import BaseAnalysisTab
from .technical_tab import TechnicalAnalysisTab
from .pattern_tab import PatternAnalysisTab
from .trend_tab import TrendAnalysisTab
from .sector_flow_tab import SectorFlowTab
from .wave_tab import WaveAnalysisTab
from .sentiment_tab import SentimentAnalysisTab
from .hotspot_tab import HotspotAnalysisTab
from .sentiment_report_tab import SentimentReportTab

__all__ = [
    'BaseAnalysisTab',
    'TechnicalAnalysisTab',
    'PatternAnalysisTab',
    'TrendAnalysisTab',
    'SectorFlowTab',
    'WaveAnalysisTab',
    'SentimentAnalysisTab',
    'HotspotAnalysisTab',
    'SentimentReportTab'
]
