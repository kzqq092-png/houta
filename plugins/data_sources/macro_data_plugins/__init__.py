"""
宏观经济数据源插件包

提供各种宏观经济数据源的插件实现，包括：
- FRED (Federal Reserve Economic Data)
- 央行数据
- 统计局数据
- 国际组织数据

作者: FactorWeave-Quant增强团队
版本: 1.0
日期: 2025-09-21
"""

from .fred_plugin import FREDPlugin
from .pboc_plugin import PBOCPlugin
from .nbs_plugin import NBSPlugin

__all__ = [
    'FREDPlugin',
    'PBOCPlugin',
    'NBSPlugin'
]
