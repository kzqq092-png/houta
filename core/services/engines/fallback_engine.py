"""
备用指标计算引擎

该引擎使用pandas和numpy实现常用指标计算，
当专业库不可用时作为后备方案。
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Union, Any
import time
import logging

from .indicator_engine import IndicatorEngine, IndicatorNotSupportedError, CalculationError


class FallbackEngine(IndicatorEngine):
    """备用指标计算引擎

    使用pandas和numpy实现的基础指标计算，
    作为TA-Lib和Hikyuu引擎的后备方案。
    """

    def __init__(self):
        """初始化备用引擎"""
        super().__init__("Fallback")
        self.logger = logging.getLogger(__name__)
        self._supported_indicators = [
            'SMA', 'MA', 'EMA', 'MACD', 'RSI', 'BBANDS', 'BOLL',
            'KDJ', 'STOCH', 'ATR', 'OBV', 'CCI', 'ROC', 'MOM'
        ]
        self._available = True
        self.logger.info(f"备用引擎初始化成功，支持 {len(self._supported_indicators)} 个指标")

    def supports_indicator(self, indicator_name: str) -> bool:
        """检查是否支持指定指标"""
        return indicator_name.upper() in [ind.upper() for ind in self._supported_indicators]

    def calculate(self,
                  indicator_name: str,
                  data: Union[pd.DataFrame, Dict[str, pd.Series]],
                  **params) -> Union[pd.Series, Dict[str, pd.Series]]:
        """计算指标"""
        if not self.supports_indicator(indicator_name):
            raise IndicatorNotSupportedError(f"备用引擎不支持指标: {indicator_name}")

        if not self.validate_data(data):
            raise CalculationError("输入数据格式无效")

        start_time = time.time()

        try:
            result = self._calculate_fallback_indicator(indicator_name, data, params)
            computation_time = time.time() - start_time
            self.logger.debug(f"备用引擎计算 {indicator_name} 耗时: {computation_time:.4f}s")
            return result

        except Exception as e:
            error_msg = f"备用引擎计算失败: {e}"
            self.logger.error(error_msg)
            raise CalculationError(error_msg) from e

    def _calculate_fallback_indicator(self,
                                      indicator_name: str,
                                      data: Union[pd.DataFrame, Dict[str, pd.Series]],
                                      params: Dict[str, Any]) -> Union[pd.Series, Dict[str, pd.Series]]:
        """使用备用实现计算指标"""
        indicator_name = indicator_name.upper()

        # 获取数据
        close = self._get_close_data(data)

        # 根据指标类型调用相应方法
        if indicator_name in ['SMA', 'MA']:
            period = params.get('period', params.get('timeperiod', 20))
            return self._fallback_sma(close, period)

        elif indicator_name == 'EMA':
            period = params.get('period', params.get('timeperiod', 20))
            return self._fallback_ema(close, period)

        elif indicator_name == 'MACD':
            return self._fallback_macd(data, params)

        elif indicator_name == 'RSI':
            period = params.get('period', params.get('timeperiod', 14))
            return self._fallback_rsi(close, period)

        elif indicator_name in ['BBANDS', 'BOLL']:
            return self._fallback_bbands(data, params)

        elif indicator_name == 'ATR':
            period = params.get('period', params.get('timeperiod', 14))
            return self._fallback_atr(data, period)

        elif indicator_name in ['KDJ', 'STOCH']:
            return self._fallback_kdj(data, params)

        elif indicator_name == 'OBV':
            return self._fallback_obv(data)

        elif indicator_name == 'CCI':
            period = params.get('period', params.get('timeperiod', 14))
            return self._fallback_cci(data, period)

        elif indicator_name == 'ROC':
            period = params.get('period', params.get('timeperiod', 10))
            return self._fallback_roc(close, period)

        elif indicator_name == 'MOM':
            period = params.get('period', params.get('timeperiod', 10))
            return self._fallback_mom(close, period)

        else:
            raise IndicatorNotSupportedError(f"备用引擎不支持指标: {indicator_name}")

    def _get_close_data(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> pd.Series:
        """获取收盘价数据"""
        if isinstance(data, pd.DataFrame):
            if 'close' not in data.columns:
                raise CalculationError("缺少收盘价数据")
            return data['close']
        else:
            if 'close' not in data:
                raise CalculationError("缺少收盘价数据")
            return data['close']

    def _get_ohlcv_data(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> Dict[str, pd.Series]:
        """获取OHLCV数据"""
        if isinstance(data, pd.DataFrame):
            result = {}
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in data.columns:
                    result[col] = data[col]
            return result
        else:
            return data

    def _fallback_sma(self, close: pd.Series, period: int) -> pd.Series:
        """SMA备用实现"""
        result = close.rolling(window=period).mean()
        result.name = 'sma'
        return result

    def _fallback_ema(self, close: pd.Series, period: int) -> pd.Series:
        """EMA备用实现"""
        result = close.ewm(span=period).mean()
        result.name = 'ema'
        return result

    def _fallback_macd(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """MACD备用实现"""
        close = self._get_close_data(data)
        fast_period = params.get('fast_period', params.get('fastperiod', 12))
        slow_period = params.get('slow_period', params.get('slowperiod', 26))
        signal_period = params.get('signal_period', params.get('signalperiod', 9))

        ema_fast = close.ewm(span=fast_period).mean()
        ema_slow = close.ewm(span=slow_period).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line.rename('macd'),
            'macdsignal': signal_line.rename('macdsignal'),
            'macdhist': histogram.rename('macdhist')
        }

    def _fallback_rsi(self, close: pd.Series, period: int) -> pd.Series:
        """RSI备用实现"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # 避免除零
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi.name = 'rsi'
        return rsi

    def _fallback_bbands(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """布林带备用实现"""
        close = self._get_close_data(data)
        period = params.get('period', params.get('timeperiod', 20))
        std_dev = params.get('std_dev', params.get('nbdevup', params.get('nbdevdn', 2)))

        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upperband': upper_band.rename('upperband'),
            'middleband': sma.rename('middleband'),
            'lowerband': lower_band.rename('lowerband')
        }

    def _fallback_atr(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """ATR备用实现"""
        ohlcv = self._get_ohlcv_data(data)

        if not all(col in ohlcv for col in ['high', 'low', 'close']):
            raise CalculationError("ATR计算需要高低收价格数据")

        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']

        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        atr.name = 'atr'
        return atr

    def _fallback_kdj(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """KDJ备用实现"""
        ohlcv = self._get_ohlcv_data(data)

        if not all(col in ohlcv for col in ['high', 'low', 'close']):
            raise CalculationError("KDJ计算需要高低收价格数据")

        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']

        k_period = params.get('k_period', params.get('fastk_period', 14))
        d_period = params.get('d_period', params.get('slowk_period', 3))

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        # 避免除零
        range_hl = highest_high - lowest_low
        rsv = 100 * ((close - lowest_low) / range_hl.replace(0, np.nan))

        k = rsv.ewm(alpha=1/d_period).mean()
        d = k.ewm(alpha=1/d_period).mean()
        j = 3 * k - 2 * d

        return {
            'slowk': k.rename('slowk'),
            'slowd': d.rename('slowd'),
            'j': j.rename('j')
        }

    def _fallback_obv(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> pd.Series:
        """OBV备用实现"""
        ohlcv = self._get_ohlcv_data(data)

        if not all(col in ohlcv for col in ['close', 'volume']):
            raise CalculationError("OBV计算需要价格和成交量数据")

        close = ohlcv['close']
        volume = ohlcv['volume']

        price_change = close.diff()
        volume_direction = np.where(price_change > 0, volume,
                                    np.where(price_change < 0, -volume, 0))

        obv = pd.Series(volume_direction, index=close.index).cumsum()
        obv.name = 'obv'
        return obv

    def _fallback_cci(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """CCI备用实现"""
        ohlcv = self._get_ohlcv_data(data)

        if not all(col in ohlcv for col in ['high', 'low', 'close']):
            raise CalculationError("CCI计算需要高低收价格数据")

        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']

        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mean_dev = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean())), raw=True
        )

        # 避免除零
        cci = (typical_price - sma) / (0.015 * mean_dev.replace(0, np.nan))
        cci.name = 'cci'
        return cci

    def _fallback_roc(self, close: pd.Series, period: int) -> pd.Series:
        """ROC备用实现"""
        shifted_close = close.shift(period)
        roc = ((close - shifted_close) / shifted_close.replace(0, np.nan)) * 100
        roc.name = 'roc'
        return roc

    def _fallback_mom(self, close: pd.Series, period: int) -> pd.Series:
        """MOM备用实现"""
        mom = close - close.shift(period)
        mom.name = 'mom'
        return mom

    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化参数"""
        normalized = super().normalize_params(params)

        # 处理常见的参数名映射
        param_mappings = {
            'timeperiod': 'period',
            'fastperiod': 'fast_period',
            'slowperiod': 'slow_period',
            'signalperiod': 'signal_period',
            'nbdevup': 'std_dev',
            'nbdevdn': 'std_dev'
        }

        for old_name, new_name in param_mappings.items():
            if old_name in normalized and new_name not in normalized:
                normalized[new_name] = normalized.pop(old_name)

        return normalized
