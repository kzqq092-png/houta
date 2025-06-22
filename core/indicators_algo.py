"""
技术指标算法兼容层
将旧的indicators_algo调用转发到新的统一指标管理器

这个模块保持与旧版本的兼容性，同时将实际计算委托给新的架构。
"""

import warnings
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple

from core.services.indicator_ui_adapter import IndicatorUIAdapter


class TechnicalIndicators:
    """技术指标算法类（兼容层）

    这个类提供与旧的TechnicalIndicators相同的接口，
    但内部使用新的UnifiedIndicatorManager实现。
    """

    def __init__(self):
        """初始化技术指标算法类"""
        self.indicator_adapter = IndicatorUIAdapter()
        warnings.warn(
            "TechnicalIndicators已弃用，请使用新的指标服务架构",
            DeprecationWarning,
            stacklevel=2
        )

    # 移动平均指标
    def sma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """简单移动平均线"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('SMA', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    def ema(self, data: pd.Series, period: int = 20) -> pd.Series:
        """指数移动平均线"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('EMA', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    def wma(self, data: pd.Series, period: int = 20) -> pd.Series:
        """加权移动平均线"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('WMA', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    # 动量指标
    def macd(self, data: Union[pd.Series, pd.DataFrame],
             fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """MACD指标"""
        if isinstance(data, pd.Series):
            data = {'close': data}
        elif isinstance(data, pd.DataFrame):
            data = {'close': data['close']}

        result = self.indicator_adapter.calculate_indicator('MACD', data,
                                                            fast_period=fast_period,
                                                            slow_period=slow_period,
                                                            signal_period=signal_period)
        if result and result.get('success'):
            macd_data = result.get('data')
            return macd_data if isinstance(macd_data, dict) else {'macd': macd_data}
        return {'macd': pd.Series(), 'signal': pd.Series(), 'histogram': pd.Series()}

    def rsi(self, data: Union[pd.Series, pd.DataFrame], period: int = 14) -> pd.Series:
        """相对强弱指标"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('RSI', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    def stoch(self, high: pd.Series, low: pd.Series, close: pd.Series,
              k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """随机指标"""
        data = {'high': high, 'low': low, 'close': close}
        result = self.indicator_adapter.calculate_indicator('STOCH', data,
                                                            k_period=k_period,
                                                            d_period=d_period)
        if result and result.get('success'):
            stoch_data = result.get('data')
            return stoch_data if isinstance(stoch_data, dict) else {'stoch': stoch_data}
        return {'k': pd.Series(), 'd': pd.Series()}

    def cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """商品通道指标"""
        data = {'high': high, 'low': low, 'close': close}
        result = self.indicator_adapter.calculate_indicator('CCI', data, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    def willr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """威廉指标"""
        data = {'high': high, 'low': low, 'close': close}
        result = self.indicator_adapter.calculate_indicator('WILLR', data, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    # 波动性指标
    def bbands(self, data: Union[pd.Series, pd.DataFrame],
               period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """布林带"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('BBANDS', {'close': data},
                                                            period=period,
                                                            std_dev=std_dev)
        if result and result.get('success'):
            bb_data = result.get('data')
            return bb_data if isinstance(bb_data, dict) else {'bbands': bb_data}
        return {'upper': pd.Series(), 'middle': pd.Series(), 'lower': pd.Series()}

    def atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        data = {'high': high, 'low': low, 'close': close}
        result = self.indicator_adapter.calculate_indicator('ATR', data, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    # 成交量指标
    def obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮指标"""
        data = {'close': close, 'volume': volume}
        result = self.indicator_adapter.calculate_indicator('OBV', data)
        return result.get('data') if result and result.get('success') else pd.Series()

    # 其他指标
    def roc(self, data: Union[pd.Series, pd.DataFrame], period: int = 10) -> pd.Series:
        """变动率指标"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('ROC', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()

    def mom(self, data: Union[pd.Series, pd.DataFrame], period: int = 10) -> pd.Series:
        """动量指标"""
        if isinstance(data, pd.DataFrame):
            data = data['close']
        result = self.indicator_adapter.calculate_indicator('MOM', {'close': data}, period=period)
        return result.get('data') if result and result.get('success') else pd.Series()


# 全局实例
_technical_indicators = None


def get_technical_indicators() -> TechnicalIndicators:
    """获取技术指标实例（兼容函数）"""
    global _technical_indicators
    if _technical_indicators is None:
        _technical_indicators = TechnicalIndicators()
    return _technical_indicators


# 便捷函数（兼容接口）
def calculate_sma(data: pd.Series, period: int = 20) -> pd.Series:
    """计算简单移动平均线（兼容函数）"""
    return get_technical_indicators().sma(data, period)


def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
    """计算指数移动平均线（兼容函数）"""
    return get_technical_indicators().ema(data, period)


def calculate_macd(data: Union[pd.Series, pd.DataFrame],
                   fast_period: int = 12, slow_period: int = 26,
                   signal_period: int = 9) -> Dict[str, pd.Series]:
    """计算MACD（兼容函数）"""
    return get_technical_indicators().macd(data, fast_period, slow_period, signal_period)


def calculate_rsi(data: Union[pd.Series, pd.DataFrame], period: int = 14) -> pd.Series:
    """计算RSI（兼容函数）"""
    return get_technical_indicators().rsi(data, period)


def calculate_bbands(data: Union[pd.Series, pd.DataFrame],
                     period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
    """计算布林带（兼容函数）"""
    return get_technical_indicators().bbands(data, period, std_dev)


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = 14) -> pd.Series:
    """计算平均真实波幅（兼容函数）"""
    return get_technical_indicators().atr(high, low, close, period)


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """计算能量潮指标（兼容函数）"""
    return get_technical_indicators().obv(close, volume)


# 导出的符号列表
__all__ = [
    'TechnicalIndicators',
    'get_technical_indicators',
    'calculate_sma',
    'calculate_ema',
    'calculate_macd',
    'calculate_rsi',
    'calculate_bbands',
    'calculate_atr',
    'calculate_obv'
]
