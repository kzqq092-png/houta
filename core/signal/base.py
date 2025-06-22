"""
基础信号模块
提供技术指标信号生成的基础功能
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from abc import ABC, abstractmethod
from core.services.indicator_ui_adapter import IndicatorUIAdapter
from hikyuu import *

# 修复hikyuu指标导入
try:
    from hikyuu.indicator import MA, MACD, RSI, KDJ, ATR, OBV, CCI, CLOSE, HIGH, LOW, VOL
    # 尝试导入BOLL，如果不存在则使用UPPER和LOWER
    try:
        from hikyuu.indicator import BOLL
    except ImportError:
        # hikyuu可能使用UPPER/LOWER而不是BOLL
        from hikyuu.indicator import UPPER, LOWER
        BOLL = None
except ImportError:
    # 如果导入失败，设置为None，后续会使用备用方案
    MA = MACD = RSI = KDJ = ATR = OBV = CCI = None
    BOLL = UPPER = LOWER = None
    CLOSE = HIGH = LOW = VOL = None


class BaseSignal(ABC):
    """信号生成基类"""

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        # 获取统一指标管理器
        self.indicator_adapter = IndicatorUIAdapter()

    @abstractmethod
    def generate_signal(self, data: Any) -> Dict[str, Any]:
        """生成信号"""
        pass

    def calculate_indicator(self, indicator_name: str, data: Any, **kwargs) -> Any:
        """计算指标的统一接口"""
        try:
            # 首先尝试使用新架构
            response = self.indicator_adapter.calculate_indicator(indicator_name, data, **kwargs)
            if response and response.get('success'):
                return response.get('data')
        except Exception as e:
            print(f"统一指标管理器计算失败，回退到hikyuu指标: {str(e)}")
            # 回退到hikyuu指标
            return self._calculate_hikyuu_indicator(indicator_name, data, **kwargs)

    def _calculate_hikyuu_indicator(self, indicator_name: str, data: Any, **kwargs) -> Any:
        """使用hikyuu指标作为回退方案"""
        try:
            # 如果hikyuu指标不可用，直接返回None
            if CLOSE is None:
                return None

            close_ind = CLOSE(data)
            high_ind = HIGH(data) if HIGH else close_ind
            low_ind = LOW(data) if LOW else close_ind
            vol_ind = VOL(data) if VOL else None

            if indicator_name.upper() == 'MA':
                period = kwargs.get('period', kwargs.get('n', 20))
                return MA(close_ind, n=period) if MA else None
            elif indicator_name.upper() == 'EMA':
                period = kwargs.get('period', kwargs.get('n', 20))
                return EMA(close_ind, n=period) if EMA else None
            elif indicator_name.upper() == 'MACD':
                fast = kwargs.get('fastperiod', kwargs.get('n1', 12))
                slow = kwargs.get('slowperiod', kwargs.get('n2', 26))
                signal = kwargs.get('signalperiod', kwargs.get('n3', 9))
                return MACD(close_ind, n1=fast, n2=slow, n3=signal) if MACD else None
            elif indicator_name.upper() == 'RSI':
                period = kwargs.get('period', kwargs.get('n', 14))
                return RSI(close_ind, n=period) if RSI else None
            elif indicator_name.upper() == 'BOLL':
                period = kwargs.get('period', kwargs.get('n', 20))
                width = kwargs.get('std_dev', kwargs.get('width', 2))
                if BOLL:
                    return BOLL(close_ind, n=period, width=width)
                elif UPPER and LOWER:
                    # 使用UPPER和LOWER构造布林带
                    ma_ind = MA(close_ind, n=period) if MA else None
                    if ma_ind:
                        upper = UPPER(close_ind, n=period, width=width)
                        lower = LOWER(close_ind, n=period, width=width)
                        return {'upper': upper, 'lower': lower, 'middle': ma_ind}
                return None
            elif indicator_name.upper() == 'KDJ':
                k_period = kwargs.get('k_period', kwargs.get('n', 9))
                d_period = kwargs.get('d_period', kwargs.get('m1', 3))
                j_period = kwargs.get('j_period', kwargs.get('m2', 3))
                return KDJ(data, n=k_period, m1=d_period, m2=j_period) if KDJ else None
            elif indicator_name.upper() == 'ATR':
                period = kwargs.get('period', kwargs.get('n', 14))
                return ATR(data, n=period) if ATR else None
            elif indicator_name.upper() == 'OBV':
                return OBV(data) if OBV else None
            elif indicator_name.upper() == 'CCI':
                period = kwargs.get('period', kwargs.get('n', 20))
                return CCI(data, n=period) if CCI else None
            else:
                return None
        except Exception as e:
            print(f"hikyuu指标计算失败: {str(e)}")
            return None


class TrendSignal(BaseSignal):
    """趋势信号"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'ma_short': 5,
            'ma_mid': 20,
            'ma_long': 60,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9
        }
        if params:
            default_params.update(params)
        super().__init__("TrendSignal", default_params)

    def generate_signal(self, data: Any) -> Dict[str, Any]:
        """生成趋势信号"""
        try:
            signals = {}

            # 计算移动平均线
            ma_short = self.calculate_indicator('MA', data, period=self.params['ma_short'])
            ma_mid = self.calculate_indicator('MA', data, period=self.params['ma_mid'])
            ma_long = self.calculate_indicator('MA', data, period=self.params['ma_long'])

            # 计算MACD
            macd_result = self.calculate_indicator('MACD', data,
                                                   fast_period=self.params['macd_fast'],
                                                   slow_period=self.params['macd_slow'],
                                                   signal_period=self.params['macd_signal'])

            # 均线趋势信号
            if ma_short is not None and ma_mid is not None and ma_long is not None:
                signals['ma_trend'] = self._analyze_ma_trend(ma_short, ma_mid, ma_long)

            # MACD趋势信号
            if macd_result is not None:
                signals['macd_trend'] = self._analyze_macd_trend(macd_result)

            # 综合趋势信号
            signals['trend_signal'] = self._combine_trend_signals(signals)

            return signals

        except Exception as e:
            print(f"趋势信号生成错误: {str(e)}")
            return {}

    def _analyze_ma_trend(self, ma_short: Any, ma_mid: Any, ma_long: Any) -> str:
        """分析均线趋势"""
        try:
            # 获取最新值
            if hasattr(ma_short, 'iloc'):
                short_val = ma_short.iloc[-1]
                mid_val = ma_mid.iloc[-1]
                long_val = ma_long.iloc[-1]
            else:
                short_val = ma_short[-1]
                mid_val = ma_mid[-1]
                long_val = ma_long[-1]

            if short_val > mid_val > long_val:
                return "strong_bullish"
            elif short_val > mid_val:
                return "bullish"
            elif short_val < mid_val < long_val:
                return "strong_bearish"
            elif short_val < mid_val:
                return "bearish"
            else:
                return "neutral"
        except Exception:
            return "neutral"

    def _analyze_macd_trend(self, macd_result: Any) -> str:
        """分析MACD趋势"""
        try:
            if isinstance(macd_result, dict):
                macd_val = macd_result.get('main', 0)
                signal_val = macd_result.get('signal', 0)
                hist_val = macd_result.get('histogram', 0)
            elif hasattr(macd_result, 'iloc'):
                macd_val = macd_result.iloc[-1]
                signal_val = 0
                hist_val = 0
            else:
                macd_val = macd_result[-1] if hasattr(macd_result, '__getitem__') else 0
                signal_val = 0
                hist_val = 0

            if macd_val > signal_val and hist_val > 0:
                return "bullish"
            elif macd_val < signal_val and hist_val < 0:
                return "bearish"
            else:
                return "neutral"
        except Exception:
            return "neutral"

    def _combine_trend_signals(self, signals: Dict[str, Any]) -> str:
        """综合趋势信号"""
        ma_trend = signals.get('ma_trend', 'neutral')
        macd_trend = signals.get('macd_trend', 'neutral')

        if ma_trend in ['strong_bullish', 'bullish'] and macd_trend == 'bullish':
            return 'strong_buy'
        elif ma_trend == 'bullish' or macd_trend == 'bullish':
            return 'buy'
        elif ma_trend in ['strong_bearish', 'bearish'] and macd_trend == 'bearish':
            return 'strong_sell'
        elif ma_trend == 'bearish' or macd_trend == 'bearish':
            return 'sell'
        else:
            return 'hold'


class MomentumSignal(BaseSignal):
    """动量信号"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'cci_period': 20,
            'cci_overbought': 100,
            'cci_oversold': -100
        }
        if params:
            default_params.update(params)
        super().__init__("MomentumSignal", default_params)

    def generate_signal(self, data: Any) -> Dict[str, Any]:
        """生成动量信号"""
        try:
            signals = {}

            # 计算RSI
            rsi = self.calculate_indicator('RSI', data, period=self.params['rsi_period'])

            # 计算CCI
            cci = self.calculate_indicator('CCI', data, period=self.params['cci_period'])

            # RSI信号
            if rsi is not None:
                signals['rsi_signal'] = self._analyze_rsi_signal(rsi)

            # CCI信号
            if cci is not None:
                signals['cci_signal'] = self._analyze_cci_signal(cci)

            # 综合动量信号
            signals['momentum_signal'] = self._combine_momentum_signals(signals)

            return signals

        except Exception as e:
            print(f"动量信号生成错误: {str(e)}")
            return {}

    def _analyze_rsi_signal(self, rsi: Any) -> str:
        """分析RSI信号"""
        try:
            if hasattr(rsi, 'iloc'):
                rsi_val = rsi.iloc[-1]
            else:
                rsi_val = rsi[-1] if hasattr(rsi, '__getitem__') else 50

            if rsi_val > self.params['rsi_overbought']:
                return "overbought"
            elif rsi_val < self.params['rsi_oversold']:
                return "oversold"
            else:
                return "neutral"
        except Exception:
            return "neutral"

    def _analyze_cci_signal(self, cci: Any) -> str:
        """分析CCI信号"""
        try:
            if hasattr(cci, 'iloc'):
                cci_val = cci.iloc[-1]
            else:
                cci_val = cci[-1] if hasattr(cci, '__getitem__') else 0

            if cci_val > self.params['cci_overbought']:
                return "overbought"
            elif cci_val < self.params['cci_oversold']:
                return "oversold"
            else:
                return "neutral"
        except Exception:
            return "neutral"

    def _combine_momentum_signals(self, signals: Dict[str, Any]) -> str:
        """综合动量信号"""
        rsi_signal = signals.get('rsi_signal', 'neutral')
        cci_signal = signals.get('cci_signal', 'neutral')

        if rsi_signal == 'oversold' and cci_signal == 'oversold':
            return 'strong_buy'
        elif rsi_signal == 'oversold' or cci_signal == 'oversold':
            return 'buy'
        elif rsi_signal == 'overbought' and cci_signal == 'overbought':
            return 'strong_sell'
        elif rsi_signal == 'overbought' or cci_signal == 'overbought':
            return 'sell'
        else:
            return 'hold'


class VolumeSignal(BaseSignal):
    """成交量信号"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'volume_ma': 20,
            'volume_threshold': 1.5,
            'obv_ma': 10
        }
        if params:
            default_params.update(params)
        super().__init__("VolumeSignal", default_params)

    def generate_signal(self, data: Any) -> Dict[str, Any]:
        """生成成交量信号"""
        try:
            signals = {}

            # 计算OBV
            obv = self.calculate_indicator('OBV', data)

            # 计算成交量均线
            if hasattr(data, 'to_df'):
                df = data.to_df()
                volume = df['volume']
                volume_ma = volume.rolling(window=self.params['volume_ma']).mean()
            elif isinstance(data, pd.DataFrame) and 'volume' in data.columns:
                volume = data['volume']
                volume_ma = volume.rolling(window=self.params['volume_ma']).mean()
            else:
                # 使用hikyuu指标
                if VOL and MA:
                    volume = VOL(data)
                    volume_ma = MA(volume, n=self.params['volume_ma'])
                else:
                    volume = None
                    volume_ma = None

            # 成交量信号
            if volume is not None and volume_ma is not None:
                signals['volume_signal'] = self._analyze_volume_signal(volume, volume_ma)

            # OBV信号
            if obv is not None:
                signals['obv_signal'] = self._analyze_obv_signal(obv)

            # 综合成交量信号
            signals['volume_combined'] = self._combine_volume_signals(signals)

            return signals

        except Exception as e:
            print(f"成交量信号生成错误: {str(e)}")
            return {}

    def _analyze_volume_signal(self, volume: Any, volume_ma: Any) -> str:
        """分析成交量信号"""
        try:
            if hasattr(volume, 'iloc'):
                vol_val = volume.iloc[-1]
                vol_ma_val = volume_ma.iloc[-1]
            else:
                vol_val = volume[-1]
                vol_ma_val = volume_ma[-1]

            if vol_val > vol_ma_val * self.params['volume_threshold']:
                return "high_volume"
            elif vol_val < vol_ma_val / self.params['volume_threshold']:
                return "low_volume"
            else:
                return "normal_volume"
        except Exception:
            return "normal_volume"

    def _analyze_obv_signal(self, obv: Any) -> str:
        """分析OBV信号"""
        try:
            # 计算OBV的移动平均线
            if hasattr(obv, 'rolling'):
                obv_ma = obv.rolling(window=self.params['obv_ma']).mean()
                obv_val = obv.iloc[-1]
                obv_ma_val = obv_ma.iloc[-1]
            elif MA:
                obv_ma = MA(obv, n=self.params['obv_ma'])
                obv_val = obv[-1]
                obv_ma_val = obv_ma[-1]
            else:
                return "obv_neutral"

            if obv_val > obv_ma_val:
                return "obv_bullish"
            elif obv_val < obv_ma_val:
                return "obv_bearish"
            else:
                return "obv_neutral"
        except Exception:
            return "obv_neutral"

    def _combine_volume_signals(self, signals: Dict[str, Any]) -> str:
        """综合成交量信号"""
        volume_signal = signals.get('volume_signal', 'normal_volume')
        obv_signal = signals.get('obv_signal', 'obv_neutral')

        if volume_signal == 'high_volume' and obv_signal == 'obv_bullish':
            return 'strong_bullish'
        elif volume_signal == 'high_volume' and obv_signal == 'obv_bearish':
            return 'strong_bearish'
        elif volume_signal == 'high_volume':
            return 'attention'
        else:
            return 'normal'


class VolatilitySignal(BaseSignal):
    """波动率信号"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'boll_period': 20,
            'boll_width': 2,
            'atr_period': 14,
            'atr_multiplier': 2
        }
        if params:
            default_params.update(params)
        super().__init__("VolatilitySignal", default_params)

    def generate_signal(self, data: Any) -> Dict[str, Any]:
        """生成波动率信号"""
        try:
            signals = {}

            # 计算布林带
            boll_result = self.calculate_indicator('BOLL', data,
                                                   period=self.params['boll_period'],
                                                   std_dev=self.params['boll_width'])

            # 计算ATR
            atr = self.calculate_indicator('ATR', data, period=self.params['atr_period'])

            # 获取价格数据
            if hasattr(data, 'to_df'):
                df = data.to_df()
                close = df['close']
            elif isinstance(data, pd.DataFrame) and 'close' in data.columns:
                close = data['close']
            elif CLOSE:
                close = CLOSE(data)
            else:
                close = None

            # 布林带信号
            if boll_result is not None and close is not None:
                signals['boll_signal'] = self._analyze_boll_signal(close, boll_result)

            # ATR信号
            if atr is not None:
                signals['atr_signal'] = self._analyze_atr_signal(atr)

            # 综合波动率信号
            signals['volatility_signal'] = self._combine_volatility_signals(signals)

            return signals

        except Exception as e:
            print(f"波动率信号生成错误: {str(e)}")
            return {}

    def _analyze_boll_signal(self, close: Any, boll_result: Any) -> str:
        """分析布林带信号"""
        try:
            if hasattr(close, 'iloc'):
                close_val = close.iloc[-1]
            else:
                close_val = close[-1]

            if isinstance(boll_result, dict):
                upper = boll_result.get('upper', close_val)
                lower = boll_result.get('lower', close_val)
                middle = boll_result.get('middle', close_val)

                # 如果是hikyuu指标对象，获取最新值
                if hasattr(upper, '__getitem__'):
                    upper = upper[-1]
                if hasattr(lower, '__getitem__'):
                    lower = lower[-1]
                if hasattr(middle, '__getitem__'):
                    middle = middle[-1]
            else:
                # 假设是hikyuu的BOLL指标
                upper = boll_result.upper[-1] if hasattr(boll_result, 'upper') else close_val
                lower = boll_result.lower[-1] if hasattr(boll_result, 'lower') else close_val
                middle = boll_result.middle[-1] if hasattr(boll_result, 'middle') else close_val

            if close_val > upper:
                return "above_upper"
            elif close_val < lower:
                return "below_lower"
            elif close_val > middle:
                return "above_middle"
            else:
                return "below_middle"
        except Exception:
            return "normal"

    def _analyze_atr_signal(self, atr: Any) -> str:
        """分析ATR信号"""
        try:
            if hasattr(atr, 'iloc'):
                current_atr = atr.iloc[-1]
                avg_atr = atr.iloc[-20:].mean()
            else:
                current_atr = atr[-1]
                # 简化处理，直接使用当前值
                avg_atr = current_atr

            if current_atr > avg_atr * self.params['atr_multiplier']:
                return "high_volatility"
            elif current_atr < avg_atr / self.params['atr_multiplier']:
                return "low_volatility"
            else:
                return "normal_volatility"
        except Exception:
            return "normal_volatility"

    def _combine_volatility_signals(self, signals: Dict[str, Any]) -> str:
        """综合波动率信号"""
        boll_signal = signals.get('boll_signal', 'normal')
        atr_signal = signals.get('atr_signal', 'normal_volatility')

        if boll_signal == 'below_lower' and atr_signal == 'high_volatility':
            return 'oversold_high_vol'
        elif boll_signal == 'above_upper' and atr_signal == 'high_volatility':
            return 'overbought_high_vol'
        elif boll_signal == 'below_lower':
            return 'oversold'
        elif boll_signal == 'above_upper':
            return 'overbought'
        elif atr_signal == 'high_volatility':
            return 'high_volatility'
        elif atr_signal == 'low_volatility':
            return 'low_volatility'
        else:
            return 'normal'


class CompositeSignal:
    """复合信号生成器"""

    def __init__(self):
        self.trend_signal = TrendSignal()
        self.momentum_signal = MomentumSignal()
        self.volume_signal = VolumeSignal()
        self.volatility_signal = VolatilitySignal()

    def generate_composite_signal(self, data: Any) -> Dict[str, Any]:
        """生成复合信号"""
        try:
            # 生成各类信号
            trend_signals = self.trend_signal.generate_signal(data)
            momentum_signals = self.momentum_signal.generate_signal(data)
            volume_signals = self.volume_signal.generate_signal(data)
            volatility_signals = self.volatility_signal.generate_signal(data)

            # 合并所有信号
            all_signals = {
                'trend': trend_signals,
                'momentum': momentum_signals,
                'volume': volume_signals,
                'volatility': volatility_signals
            }

            # 生成综合信号
            composite_signal = self._generate_final_signal(all_signals)
            all_signals['composite'] = composite_signal

            return all_signals

        except Exception as e:
            print(f"复合信号生成错误: {str(e)}")
            return {}

    def _generate_final_signal(self, signals: Dict[str, Any]) -> str:
        """生成最终综合信号"""
        try:
            trend_signal = signals.get('trend', {}).get('trend_signal', 'hold')
            momentum_signal = signals.get('momentum', {}).get('momentum_signal', 'hold')
            volume_signal = signals.get('volume', {}).get('volume_combined', 'normal')
            volatility_signal = signals.get('volatility', {}).get('volatility_signal', 'normal')

            # 信号权重
            buy_score = 0
            sell_score = 0

            # 趋势信号权重最高
            if trend_signal == 'strong_buy':
                buy_score += 3
            elif trend_signal == 'buy':
                buy_score += 2
            elif trend_signal == 'strong_sell':
                sell_score += 3
            elif trend_signal == 'sell':
                sell_score += 2

            # 动量信号
            if momentum_signal == 'strong_buy':
                buy_score += 2
            elif momentum_signal == 'buy':
                buy_score += 1
            elif momentum_signal == 'strong_sell':
                sell_score += 2
            elif momentum_signal == 'sell':
                sell_score += 1

            # 成交量信号
            if volume_signal == 'strong_bullish':
                buy_score += 1
            elif volume_signal == 'strong_bearish':
                sell_score += 1

            # 波动率信号调整
            if volatility_signal in ['oversold', 'oversold_high_vol']:
                buy_score += 1
            elif volatility_signal in ['overbought', 'overbought_high_vol']:
                sell_score += 1

            # 综合判断
            if buy_score >= 4:
                return 'strong_buy'
            elif buy_score >= 2:
                return 'buy'
            elif sell_score >= 4:
                return 'strong_sell'
            elif sell_score >= 2:
                return 'sell'
            else:
                return 'hold'

        except Exception as e:
            print(f"最终信号生成错误: {str(e)}")
            return 'hold'
