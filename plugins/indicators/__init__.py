"""
指标插件模块

提供多种指标计算后端支持：
- HIkyuu指标插件：基于HIkyuu框架的高性能指标计算
- TA-Lib指标插件：基于TA-Lib库的经典技术指标
- Pandas-TA指标插件：基于pandas-ta的纯Python指标实现
- 自定义指标插件：支持用户自定义指标开发

所有插件都实现统一的IIndicatorPlugin接口，确保兼容性和可扩展性。
"""

# 可选导入，如果依赖不存在则跳过
try:
    from .hikyuu_indicators_plugin import HikyuuIndicatorsPlugin
except ImportError:
    HikyuuIndicatorsPlugin = None

try:
    from .talib_indicators_plugin import TALibIndicatorsPlugin
except ImportError:
    TALibIndicatorsPlugin = None

try:
    from .pandas_ta_indicators_plugin import PandasTAIndicatorsPlugin
except ImportError:
    PandasTAIndicatorsPlugin = None

try:
    from .custom_indicators_plugin import CustomIndicatorsPlugin
except ImportError:
    CustomIndicatorsPlugin = None

__all__ = [
    'HikyuuIndicatorsPlugin',
    'TALibIndicatorsPlugin',
    'PandasTAIndicatorsPlugin',
    'CustomIndicatorsPlugin'
]
