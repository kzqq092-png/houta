"""
指标管理器兼容层
将旧的indicator_manager调用转发到新的统一指标管理器
"""

import warnings
from typing import Dict, List, Optional, Union, Any
import pandas as pd

from core.services.indicator_ui_adapter import IndicatorUIAdapter


class IndicatorManager:
    """指标管理器兼容类

    这个类提供与旧的IndicatorManager相同的接口，
    但内部使用新的UnifiedIndicatorManager实现。
    """

    def __init__(self):
        """初始化指标管理器兼容层"""
        self.indicator_adapter = IndicatorUIAdapter()
        warnings.warn(
            "IndicatorManager已弃用，请使用新的指标服务架构",
            DeprecationWarning,
            stacklevel=2
        )

    def get_indicator_list(self, category: Optional[str] = None, use_chinese: bool = False) -> List[str]:
        """获取指标列表（兼容方法）"""
        return self.indicator_adapter.get_available_indicators()

    def get_indicators_by_category(self, use_chinese: bool = False) -> Dict[str, List[str]]:
        """按分类获取指标（兼容方法）"""
        return self.indicator_adapter.get_indicator_categories()

    def get_chinese_name(self, english_name: str) -> Optional[str]:
        """获取指标中文名称（兼容方法）"""
        info = self.indicator_adapter.get_indicator_info(english_name)
        return info.get('chinese_name', english_name) if info else english_name

    def get_english_name(self, chinese_name: str) -> Optional[str]:
        """获取指标英文名称（兼容方法）"""
        # 遍历所有指标查找中文名称匹配的
        indicators = self.indicator_adapter.get_available_indicators()
        for indicator in indicators:
            info = self.indicator_adapter.get_indicator_info(indicator)
            if info and info.get('chinese_name') == chinese_name:
                return indicator
        return chinese_name

    def calculate_indicator(self, name: str, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                            **params) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
        """计算指标（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator(name, data, **params)
        return result.get('data') if result and result.get('success') else None

    # 提供一些常见的calc_*方法作为兼容接口
    def calc_ma(self, data, period=20):
        """计算移动平均线（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator('MA', data, period=period)
        return result.get('data') if result and result.get('success') else None

    def calc_ema(self, data, period=20):
        """计算指数移动平均线（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator('EMA', data, period=period)
        return result.get('data') if result and result.get('success') else None

    def calc_macd(self, data, fast_period=12, slow_period=26, signal_period=9):
        """计算MACD（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator('MACD', data,
                                                            fast_period=fast_period,
                                                            slow_period=slow_period,
                                                            signal_period=signal_period)
        return result.get('data') if result and result.get('success') else None

    def calc_rsi(self, data, period=14):
        """计算RSI（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator('RSI', data, period=period)
        return result.get('data') if result and result.get('success') else None

    def calc_boll(self, data, period=20, std_dev=2):
        """计算布林带（兼容方法）"""
        result = self.indicator_adapter.calculate_indicator('BOLL', data,
                                                            period=period,
                                                            std_dev=std_dev)
        return result.get('data') if result and result.get('success') else None


# 全局实例缓存
_indicator_manager = None


def get_indicator_manager() -> IndicatorManager:
    """获取指标管理器实例（兼容函数）"""
    global _indicator_manager
    if _indicator_manager is None:
        _indicator_manager = IndicatorManager()
    return _indicator_manager


# 便捷函数（兼容接口）
def get_indicator_categories(use_chinese: bool = False) -> Dict[str, List[str]]:
    """获取指标分类（兼容函数）"""
    adapter = IndicatorUIAdapter()
    return adapter.get_indicator_categories()


def calculate_indicator_compat(name: str, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                               **params) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
    """计算指标的兼容函数"""
    manager = get_indicator_manager()
    return manager.calculate_indicator(name, data, **params)
