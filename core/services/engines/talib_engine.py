"""
基于TA-Lib的指标计算引擎

该引擎专门处理TA-Lib库的指标计算，
提供标准化的接口和错误处理。
"""

import pandas as pd
from typing import List, Dict, Union, Any
import numpy as np
import time
import logging

from .indicator_engine import IndicatorEngine, IndicatorNotSupportedError, CalculationError


class TALibEngine(IndicatorEngine):
    """基于TA-Lib的指标计算引擎"""

    def __init__(self):
        """初始化TA-Lib引擎"""
        super().__init__("TA-Lib")
        self.logger = logging.getLogger(__name__)
        self.talib_available = self._init_talib()

        if self.talib_available:
            self._supported_indicators = [
                'SMA', 'MA', 'EMA', 'WMA', 'MACD', 'RSI', 'BBANDS', 'BOLL',
                'STOCH', 'KDJ', 'ATR', 'OBV', 'CCI', 'WILLR', 'ROC', 'MOM'
            ]
            self._available = True
            self.logger.info(f"TA-Lib引擎初始化成功，支持 {len(self._supported_indicators)} 个指标")
        else:
            self._available = False

    def _init_talib(self) -> bool:
        """初始化TA-Lib库"""
        try:
            import talib
            self.talib = talib
            return True
        except ImportError:
            self.logger.warning("TA-Lib库不可用")
            return False

    def supports_indicator(self, indicator_name: str) -> bool:
        """检查是否支持指定指标"""
        if not self.talib_available:
            return False
        return indicator_name.upper() in [ind.upper() for ind in self._supported_indicators]

    def calculate(self,
                  indicator_name: str,
                  data: Union[pd.DataFrame, Dict[str, pd.Series]],
                  **params) -> Union[pd.Series, Dict[str, pd.Series]]:
        """使用TA-Lib计算指标"""
        if not self.talib_available:
            raise CalculationError("TA-Lib库不可用")

        if not self.supports_indicator(indicator_name):
            raise IndicatorNotSupportedError(f"TA-Lib不支持指标: {indicator_name}")

        if not self.validate_data(data):
            raise CalculationError("输入数据格式无效")

        start_time = time.time()

        try:
            result = self._calculate_talib_indicator(indicator_name, data, params)
            computation_time = time.time() - start_time
            self.logger.debug(f"TA-Lib计算 {indicator_name} 耗时: {computation_time:.4f}s")
            return result

        except Exception as e:
            error_msg = f"TA-Lib计算失败: {e}"
            self.logger.error(error_msg)
            raise CalculationError(error_msg) from e

    def _calculate_talib_indicator(self,
                                   indicator_name: str,
                                   data: Union[pd.DataFrame, Dict[str, pd.Series]],
                                   params: Dict[str, Any]) -> Union[pd.Series, Dict[str, pd.Series]]:
        """计算TA-Lib指标"""
        indicator_name = indicator_name.upper()

        # 准备数据
        if isinstance(data, pd.DataFrame):
            close = data['close'].values.astype(float) if 'close' in data.columns else None
            high = data['high'].values.astype(float) if 'high' in data.columns else None
            low = data['low'].values.astype(float) if 'low' in data.columns else None
            volume = data['volume'].values.astype(float) if 'volume' in data.columns else None
            open_price = data['open'].values.astype(float) if 'open' in data.columns else None
            index = data.index
        else:
            close = data['close'].values.astype(float) if 'close' in data else None
            high = data['high'].values.astype(float) if 'high' in data else None
            low = data['low'].values.astype(float) if 'low' in data else None
            volume = data['volume'].values.astype(float) if 'volume' in data else None
            open_price = data['open'].values.astype(float) if 'open' in data else None
            index = data['close'].index if 'close' in data else None

        # 数据验证
        if close is None or len(close) == 0:
            raise CalculationError("缺少必要的close价格数据")

        # 处理NaN值
        close = np.array(close, dtype=float)
        close = np.where(np.isnan(close), 0, close)

        # 根据指标名称调用相应的TA-Lib函数
        if indicator_name in ['MA', 'SMA']:
            period = params.get('period', params.get('timeperiod', 20))
            result = self.talib.SMA(close, timeperiod=period)
            return pd.Series(result, index=index, name='sma')

        elif indicator_name == 'EMA':
            period = params.get('period', params.get('timeperiod', 20))
            result = self.talib.EMA(close, timeperiod=period)
            return pd.Series(result, index=index, name='ema')

        elif indicator_name == 'WMA':
            period = params.get('period', params.get('timeperiod', 20))
            result = self.talib.WMA(close, timeperiod=period)
            return pd.Series(result, index=index, name='wma')

        elif indicator_name == 'MACD':
            fast = params.get('fast_period', params.get('fastperiod', 12))
            slow = params.get('slow_period', params.get('slowperiod', 26))
            signal = params.get('signal_period', params.get('signalperiod', 9))
            macd, signal_line, histogram = self.talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal)
            return {
                'macd': pd.Series(macd, index=index, name='macd'),
                'macdsignal': pd.Series(signal_line, index=index, name='macdsignal'),
                'macdhist': pd.Series(histogram, index=index, name='macdhist')
            }

        elif indicator_name == 'RSI':
            period = params.get('period', params.get('timeperiod', 14))
            result = self.talib.RSI(close, timeperiod=period)
            return pd.Series(result, index=index, name='rsi')

        elif indicator_name in ['BBANDS', 'BOLL']:
            period = params.get('period', params.get('timeperiod', 20))
            std_dev = params.get('std_dev', params.get('nbdevup', params.get('nbdevdn', 2)))
            upper, middle, lower = self.talib.BBANDS(close, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
            return {
                'upperband': pd.Series(upper, index=index, name='upperband'),
                'middleband': pd.Series(middle, index=index, name='middleband'),
                'lowerband': pd.Series(lower, index=index, name='lowerband')
            }

        elif indicator_name in ['STOCH', 'KDJ']:
            if high is None or low is None:
                raise CalculationError("随机指标需要高低价数据")

            high = np.where(np.isnan(high), 0, high)
            low = np.where(np.isnan(low), 0, low)

            k_period = params.get('k_period', params.get('fastk_period', 14))
            d_period = params.get('d_period', params.get('slowk_period', 3))

            slowk, slowd = self.talib.STOCH(high, low, close,
                                            fastk_period=k_period,
                                            slowk_period=d_period,
                                            slowd_period=d_period)

            result = {
                'slowk': pd.Series(slowk, index=index, name='slowk'),
                'slowd': pd.Series(slowd, index=index, name='slowd')
            }

            # KDJ需要J值
            if indicator_name == 'KDJ':
                j = 3 * slowk - 2 * slowd
                result['j'] = pd.Series(j, index=index, name='j')

            return result

        elif indicator_name == 'ATR':
            if high is None or low is None:
                raise CalculationError("ATR指标需要高低价数据")

            high = np.where(np.isnan(high), 0, high)
            low = np.where(np.isnan(low), 0, low)

            period = params.get('period', params.get('timeperiod', 14))
            result = self.talib.ATR(high, low, close, timeperiod=period)
            return pd.Series(result, index=index, name='atr')

        elif indicator_name == 'OBV':
            if volume is None:
                raise CalculationError("OBV指标需要成交量数据")

            volume = np.where(np.isnan(volume), 0, volume)
            result = self.talib.OBV(close, volume)
            return pd.Series(result, index=index, name='obv')

        elif indicator_name == 'CCI':
            if high is None or low is None:
                raise CalculationError("CCI指标需要高低价数据")

            high = np.where(np.isnan(high), 0, high)
            low = np.where(np.isnan(low), 0, low)

            period = params.get('period', params.get('timeperiod', 14))
            result = self.talib.CCI(high, low, close, timeperiod=period)
            return pd.Series(result, index=index, name='cci')

        elif indicator_name == 'WILLR':
            if high is None or low is None:
                raise CalculationError("WILLR指标需要高低价数据")

            high = np.where(np.isnan(high), 0, high)
            low = np.where(np.isnan(low), 0, low)

            period = params.get('period', params.get('timeperiod', 14))
            result = self.talib.WILLR(high, low, close, timeperiod=period)
            return pd.Series(result, index=index, name='willr')

        elif indicator_name == 'ROC':
            period = params.get('period', params.get('timeperiod', 10))
            result = self.talib.ROC(close, timeperiod=period)
            return pd.Series(result, index=index, name='roc')

        elif indicator_name == 'MOM':
            period = params.get('period', params.get('timeperiod', 10))
            result = self.talib.MOM(close, timeperiod=period)
            return pd.Series(result, index=index, name='mom')

        else:
            raise IndicatorNotSupportedError(f"TA-Lib引擎不支持指标: {indicator_name}")

    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化参数

        将常用参数名映射到TA-Lib期望的参数名
        """
        normalized = super().normalize_params(params)

        # 参数名映射
        param_mappings = {
            'period': 'timeperiod',
            'fast_period': 'fastperiod',
            'slow_period': 'slowperiod',
            'signal_period': 'signalperiod'
        }

        for old_name, new_name in param_mappings.items():
            if old_name in normalized and new_name not in normalized:
                normalized[new_name] = normalized.pop(old_name)

        return normalized
