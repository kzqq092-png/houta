"""
基本面数据源插件包

包含财务报表、公司公告、分析师评级等基本面数据源插件。

作者: HIkyuu-UI增强团队
版本: 1.0
日期: 2025-09-21
"""

from .eastmoney_fundamental_plugin import EastmoneyFundamentalPlugin
from .sina_fundamental_plugin import SinaFundamentalPlugin
from .cninfo_plugin import CninfoPlugin

__all__ = [
    'EastmoneyFundamentalPlugin',
    'SinaFundamentalPlugin',
    'CninfoPlugin'
]
