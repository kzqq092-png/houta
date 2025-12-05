"""
Hikyuu指标插件 - 迁移占位符

该文件已被移除hikyuu依赖处理流程标记为占位符。
原有的hikyuu指标功能已迁移到纯pandas + TA-Lib实现。
"""

import warnings
from loguru import logger

warnings.warn(
    "Hikyuu指标插件已迁移到新架构。请使用其他指标插件："
    "1. talib_indicators_plugin (TA-Lib)"
    "2. pandas_ta_indicators_plugin (pandas-ta)"
    "3. custom_indicators_plugin (自定义)",
    DeprecationWarning,
    stacklevel=2
)


class HikyuuIndicatorsPlugin:
    """
    Hikyuu指标插件占位符
    
    原hikyuu指标功能已迁移。新架构使用纯pandas + TA-Lib实现。
    """
    
    def __init__(self):
        logger.error(
            "Hikyuu指标插件已废弃。请使用其他指标插件：\n"
            "- talib_indicators_plugin: TA-Lib技术指标\n"
            "- pandas_ta_indicators_plugin: pandas-ta技术指标\n"
            "- custom_indicators_plugin: 自定义指标"
        )
        raise NotImplementedError(
            "Hikyuu指标插件已迁移到新架构。请使用其他指标插件替代。"
        )


def __getattr__(name):
    """模块级属性访问器"""
    if name in ['HIKYUU_AVAILABLE', 'hku']:
        return f"{name} 已废弃。hikyuu库依赖已移除。"
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")