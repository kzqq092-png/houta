"""
HIkyuu策略插件 - 已被移除

此文件已被重命名为 hikyuu_strategy_plugin.py.hikyuu_backup，因为系统已经完全脱离HIkyuu依赖。

现在的策略应该使用：
- MovingAverageTrendStrategy (移动平均趋势策略)
- BreakoutStrategy (突破策略) 
- MeanReversionTemplate (均值回归模板)
- CustomStrategyBase (自定义策略基类)

或者集成其他框架：
- Backtrader策略插件
- 自定义策略插件

如果需要使用HIkyuu功能，请安装hikyuu并使用备份文件。
"""

import warnings
from loguru import logger

# 发出警告，提示用户迁移策略
warnings.warn(
    "HIkyuu策略插件已被移除。系统现在使用基于pandas/TA-Lib的策略实现。"
    "请迁移到新的策略接口或集成Backtrader等其他框架。",
    DeprecationWarning,
    stacklevel=2
)

class HikyuuPluginRemoved:
    """HIkyuu插件移除占位符"""
    
    def __init__(self):
        logger.warning("HIkyuu策略插件已移除，请使用替代策略实现")

# 为了向后兼容，提供一个简单的占位符
class HikyuuStrategyAdapter:
    """HIkyuu策略适配器占位符"""
    
    def __init__(self):
        logger.warning("HIkyuu策略功能已移除")
        
    def create_signal(self, *args, **kwargs):
        """创建信号 - 抛出异常"""
        raise NotImplementedError(
            "HIkyuu策略插件已被移除，请使用MovingAverageTrendStrategy、"
            "BreakoutStrategy或其他替代策略"
        )