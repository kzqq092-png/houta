"""
基础指标特征提取模块
使用统一指标管理器进行指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
import warnings

# 使用统一指标管理器替代旧的直接导入
from core.services.indicator_ui_adapter import IndicatorUIAdapter  # 兼容层

warnings.filterwarnings('ignore')


class BasicIndicators:
    """基础技术指标计算类"""

    def __init__(self):
        """初始化基础指标计算器"""
        # 使用新的指标UI适配器
        self.indicator_adapter = IndicatorUIAdapter()

    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有基础指标

        Args:
            data: K线数据，包含open, high, low, close, volume列

        Returns:
            包含所有指标的DataFrame
        """
        try:
            if data is None or data.empty:
                return pd.DataFrame()

            result_df = data.copy()

            # 计算各类指标
            self._add_trend_indicators(result_df)
            self._add_momentum_indicators(result_df)
            self._add_volatility_indicators(result_df)
            self._add_volume_indicators(result_df)

            return result_df

        except Exception as e:
            print(f"计算所有指标失败: {str(e)}")
            return data.copy() if data is not None else pd.DataFrame()

    def _add_trend_indicators(self, df: pd.DataFrame):
        """添加趋势指标"""
        try:
            # 移动平均线
            for period in [5, 10, 20, 60]:
                ma_result = self.indicator_adapter.calculate_indicator('MA', df, period=period)
                if ma_result and ma_result.get('success'):
                    values = ma_result.get('data')
                    if values is not None:
                        df[f'MA{period}'] = values
                else:
                    # 手工计算作为备用
                    df[f'MA{period}'] = df['close'].rolling(window=period).mean()

            # 指数移动平均线
            for period in [12, 26]:
                ema_result = self.indicator_adapter.calculate_indicator('EMA', df, period=period)
                if ema_result and ema_result.get('success'):
                    values = ema_result.get('data')
                    if values is not None:
                        df[f'EMA{period}'] = values
                else:
                    # 手工计算作为备用
                    df[f'EMA{period}'] = df['close'].ewm(span=period).mean()

            # MACD
            macd_result = self.indicator_adapter.calculate_indicator('MACD', df,
                                                                     fast_period=12,
                                                                     slow_period=26,
                                                                     signal_period=9)
            if macd_result and macd_result.get('success'):
                macd_data = macd_result.get('data')
                if macd_data and isinstance(macd_data, dict):
                    if 'main' in macd_data:
                        df['MACD'] = macd_data['main']
                    if 'signal' in macd_data:
                        df['MACD_signal'] = macd_data['signal']
                    if 'histogram' in macd_data:
                        df['MACD_histogram'] = macd_data['histogram']
                elif isinstance(macd_data, tuple) and len(macd_data) >= 3:
                    df['MACD'], df['MACD_signal'], df['MACD_histogram'] = macd_data[:3]
            else:
                # 手工计算作为备用
                ema12 = df['close'].ewm(span=12).mean()
                ema26 = df['close'].ewm(span=26).mean()
                df['MACD'] = ema12 - ema26
                df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
                df['MACD_histogram'] = df['MACD'] - df['MACD_signal']

            # 布林带
            boll_result = self.indicator_adapter.calculate_indicator('BOLL', df, period=20, std_dev=2)
            if boll_result and boll_result.get('success'):
                boll_data = boll_result.get('data')
                if boll_data and isinstance(boll_data, dict):
                    if 'upper' in boll_data:
                        df['BOLL_upper'] = boll_data['upper']
                    if 'middle' in boll_data:
                        df['BOLL_middle'] = boll_data['middle']
                    if 'lower' in boll_data:
                        df['BOLL_lower'] = boll_data['lower']
                elif isinstance(boll_data, tuple) and len(boll_data) >= 3:
                    middle, upper, lower = boll_data[:3]
                    df['BOLL_upper'] = upper
                    df['BOLL_middle'] = middle
                    df['BOLL_lower'] = lower
            else:
                # 手工计算作为备用
                ma20 = df['close'].rolling(window=20).mean()
                std20 = df['close'].rolling(window=20).std()
                df['BOLL_upper'] = ma20 + 2 * std20
                df['BOLL_middle'] = ma20
                df['BOLL_lower'] = ma20 - 2 * std20

        except Exception as e:
            print(f"添加趋势指标失败: {str(e)}")

    def _add_momentum_indicators(self, df: pd.DataFrame):
        """添加动量指标"""
        try:
            # RSI
            rsi_result = self.indicator_adapter.calculate_indicator('RSI', df, period=14)
            if rsi_result and rsi_result.get('success'):
                values = rsi_result.get('data')
                if values is not None:
                    df['RSI'] = values
            else:
                # 手工计算作为备用
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                avg_loss = avg_loss.replace(0, 0.00001)
                rs = avg_gain / avg_loss
                df['RSI'] = 100 - (100 / (1 + rs))

            # KDJ
            kdj_response = self.indicator_adapter.calculate_indicator('KDJ', df, k_period=9, d_period=3)
            kdj_result = kdj_response.get('data') if kdj_response and kdj_response.get('success') else None
            if kdj_result is not None:
                if isinstance(kdj_result, dict):
                    if 'K' in kdj_result:
                        df['KDJ_K'] = kdj_result['K']
                    if 'D' in kdj_result:
                        df['KDJ_D'] = kdj_result['D']
                    if 'J' in kdj_result:
                        df['KDJ_J'] = kdj_result['J']
                elif isinstance(kdj_result, tuple) and len(kdj_result) >= 3:
                    df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = kdj_result[:3]
            else:
                # 使用兼容层作为备用
                kdj_result = self.compat_manager.calc_kdj(df, k_period=9, d_period=3)
                if kdj_result is not None:
                    if isinstance(kdj_result, tuple) and len(kdj_result) >= 3:
                        df['KDJ_K'], df['KDJ_D'], df['KDJ_J'] = kdj_result[:3]
                    elif isinstance(kdj_result, dict):
                        if 'K' in kdj_result:
                            df['KDJ_K'] = kdj_result['K']
                        if 'D' in kdj_result:
                            df['KDJ_D'] = kdj_result['D']
                        if 'J' in kdj_result:
                            df['KDJ_J'] = kdj_result['J']

            # CCI
            cci_response = self.indicator_adapter.calculate_indicator('CCI', df, period=14)
            cci_result = cci_response.get('data') if cci_response and cci_response.get('success') else None
            if cci_result is not None:
                df['CCI'] = cci_result
            else:
                # 使用兼容层作为备用
                cci_result = self.compat_manager.calc_cci(df, period=14)
                if cci_result is not None:
                    df['CCI'] = cci_result

        except Exception as e:
            print(f"添加动量指标失败: {str(e)}")

    def _add_volatility_indicators(self, df: pd.DataFrame):
        """添加波动率指标"""
        try:
            # ATR
            atr_result = self.indicator_adapter.calculate_indicator('ATR', df, period=14)
            if atr_result and atr_result.get('success'):
                values = atr_result.get('data')
                if values is not None:
                    df['ATR'] = values
            else:
                # 手工计算作为备用
                high_low = df['high'] - df['low']
                high_close = abs(df['high'] - df['close'].shift())
                low_close = abs(df['low'] - df['close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(window=14).mean()

        except Exception as e:
            print(f"添加波动率指标失败: {str(e)}")

    def _add_volume_indicators(self, df: pd.DataFrame):
        """添加成交量指标"""
        try:
            # OBV
            obv_result = self.indicator_adapter.calculate_indicator('OBV', df)
            if obv_result and obv_result.get('success'):
                values = obv_result.get('data')
                if values is not None:
                    df['OBV'] = values
            else:
                # 手工计算作为备用
                obv = [0]
                for i in range(1, len(df)):
                    if df['close'].iloc[i] > df['close'].iloc[i-1]:
                        obv.append(obv[-1] + df['volume'].iloc[i])
                    elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                        obv.append(obv[-1] - df['volume'].iloc[i])
                    else:
                        obv.append(obv[-1])
                df['OBV'] = obv

        except Exception as e:
            print(f"添加成交量指标失败: {str(e)}")

    def get_indicator_features(self, data: pd.DataFrame,
                               indicators: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取指标特征

        Args:
            data: K线数据
            indicators: 指定的指标列表，如果为None则计算所有指标

        Returns:
            指标特征字典
        """
        try:
            if data is None or data.empty:
                return {}

            features = {}

            # 如果没有指定指标，使用默认指标列表
            if indicators is None:
                indicators = ['MA', 'EMA', 'MACD', 'RSI', 'KDJ', 'BOLL', 'ATR', 'OBV', 'CCI']

            for indicator in indicators:
                try:
                    feature_value = self._calculate_indicator_feature(data, indicator)
                    if feature_value is not None:
                        features[indicator] = feature_value
                except Exception as e:
                    print(f"计算指标 {indicator} 特征失败: {str(e)}")
                    continue

            return features

        except Exception as e:
            print(f"获取指标特征失败: {str(e)}")
            return {}

    def _calculate_indicator_feature(self, data: pd.DataFrame, indicator: str) -> Optional[Any]:
        """计算单个指标特征

        Args:
            data: K线数据
            indicator: 指标名称

        Returns:
            指标特征值
        """
        try:
            indicator_upper = indicator.upper()

            # 首先尝试使用新架构
            response = self.indicator_adapter.calculate_indicator(indicator_upper, data)
            result = response.get('data') if response and response.get('success') else None

            if result is None:
                # 使用兼容层作为备用
                result = self._calculate_indicator_fallback(data, indicator_upper)

            if result is not None:
                # 提取特征值（通常是最新值）
                if isinstance(result, (pd.Series, np.ndarray)):
                    return result.iloc[-1] if len(result) > 0 else None
                elif isinstance(result, dict):
                    # 对于复合指标，返回主要组件的最新值
                    if 'main' in result:
                        main_result = result['main']
                        return main_result.iloc[-1] if len(main_result) > 0 else None
                    elif len(result) > 0:
                        # 返回第一个组件的最新值
                        first_key = list(result.keys())[0]
                        first_result = result[first_key]
                        return first_result.iloc[-1] if len(first_result) > 0 else None
                elif isinstance(result, tuple):
                    # 返回第一个组件的最新值
                    first_result = result[0]
                    return first_result.iloc[-1] if len(first_result) > 0 else None
                else:
                    return result

            return None

        except Exception as e:
            print(f"计算指标 {indicator} 特征失败: {str(e)}")
            return None

    def _calculate_indicator_fallback(self, data: pd.DataFrame, indicator: str) -> Optional[Any]:
        """使用兼容层计算指标（备用方案）

        Args:
            data: K线数据
            indicator: 指标名称

        Returns:
            指标计算结果
        """
        try:
            if indicator == 'MA':
                return self.compat_manager.calc_ma(data, period=20)
            elif indicator == 'EMA':
                return self.compat_manager.calc_ema(data, period=12)
            elif indicator == 'MACD':
                return self.compat_manager.calc_macd(data)
            elif indicator == 'RSI':
                return self.compat_manager.calc_rsi(data, period=14)
            elif indicator == 'KDJ':
                return self.compat_manager.calc_kdj(data)
            elif indicator == 'BOLL':
                return self.compat_manager.calc_boll(data, period=20, std_dev=2)
            elif indicator == 'ATR':
                return self.compat_manager.calc_atr(data, period=14)
            elif indicator == 'OBV':
                return self.compat_manager.calc_obv(data)
            elif indicator == 'CCI':
                return self.compat_manager.calc_cci(data, period=14)
            else:
                return None

        except Exception as e:
            print(f"兼容层计算指标 {indicator} 失败: {str(e)}")
            return None

    def get_trend_signals(self, data: pd.DataFrame) -> Dict[str, str]:
        """获取趋势信号

        Args:
            data: K线数据

        Returns:
            趋势信号字典
        """
        try:
            signals = {}

            if data is None or data.empty or len(data) < 2:
                return signals

            # MA趋势信号
            ma20_response = self.indicator_adapter.calculate_indicator('MA', data, period=20)
            ma20_result = ma20_response.get('data') if ma20_response and ma20_response.get('success') else None
            if ma20_result is not None and len(ma20_result) >= 2:
                current_price = data['close'].iloc[-1]
                ma20_current = ma20_result.iloc[-1]

                if current_price > ma20_current:
                    signals['MA_trend'] = 'bullish'
                else:
                    signals['MA_trend'] = 'bearish'

            # MACD信号
            macd_response = self.indicator_adapter.calculate_indicator('MACD', data)
            macd_result = macd_response.get('data') if macd_response and macd_response.get('success') else None
            if macd_result is not None:
                if isinstance(macd_result, dict) and 'histogram' in macd_result:
                    histogram = macd_result['histogram']
                    if len(histogram) >= 2:
                        if histogram.iloc[-1] > 0:
                            signals['MACD_trend'] = 'bullish'
                        else:
                            signals['MACD_trend'] = 'bearish'
                elif isinstance(macd_result, tuple) and len(macd_result) >= 3:
                    histogram = macd_result[2]
                    if len(histogram) >= 2:
                        if histogram.iloc[-1] > 0:
                            signals['MACD_trend'] = 'bullish'
                        else:
                            signals['MACD_trend'] = 'bearish'

            return signals

        except Exception as e:
            print(f"获取趋势信号失败: {str(e)}")
            return {}

    def get_momentum_signals(self, data: pd.DataFrame) -> Dict[str, str]:
        """获取动量信号

        Args:
            data: K线数据

        Returns:
            动量信号字典
        """
        try:
            signals = {}

            if data is None or data.empty:
                return signals

            # RSI信号
            rsi_response = self.indicator_adapter.calculate_indicator('RSI', data, period=14)
            rsi_result = rsi_response.get('data') if rsi_response and rsi_response.get('success') else None
            if rsi_result is not None and len(rsi_result) > 0:
                rsi_current = rsi_result.iloc[-1]
                if rsi_current > 70:
                    signals['RSI_signal'] = 'overbought'
                elif rsi_current < 30:
                    signals['RSI_signal'] = 'oversold'
                else:
                    signals['RSI_signal'] = 'neutral'

            # KDJ信号
            kdj_response = self.indicator_adapter.calculate_indicator('KDJ', data)
            kdj_result = kdj_response.get('data') if kdj_response and kdj_response.get('success') else None
            if kdj_result is not None:
                if isinstance(kdj_result, dict):
                    k_value = kdj_result.get('K')
                    d_value = kdj_result.get('D')
                elif isinstance(kdj_result, tuple) and len(kdj_result) >= 2:
                    k_value = kdj_result[0]
                    d_value = kdj_result[1]
                else:
                    k_value = d_value = None

                if k_value is not None and d_value is not None and len(k_value) > 0 and len(d_value) > 0:
                    k_current = k_value.iloc[-1]
                    d_current = d_value.iloc[-1]

                    if k_current > 80 and d_current > 80:
                        signals['KDJ_signal'] = 'overbought'
                    elif k_current < 20 and d_current < 20:
                        signals['KDJ_signal'] = 'oversold'
                    else:
                        signals['KDJ_signal'] = 'neutral'

            return signals

        except Exception as e:
            print(f"获取动量信号失败: {str(e)}")
            return {}


# 便捷函数
def create_basic_indicators() -> BasicIndicators:
    """创建基础指标计算器

    Returns:
        BasicIndicators实例
    """
    return BasicIndicators()


def calculate_indicators(data: pd.DataFrame, indicators: Optional[List[str]] = None) -> pd.DataFrame:
    """计算指标的便捷函数

    Args:
        data: K线数据
        indicators: 指标列表

    Returns:
        包含指标的DataFrame
    """
    calculator = create_basic_indicators()
    if indicators is None:
        return calculator.calculate_all_indicators(data)
    else:
        result_df = data.copy()
        for indicator in indicators:
            try:
                # 使用新架构计算单个指标
                indicator_response = calculator.indicator_adapter.calculate_indicator(indicator, data)
                indicator_result = indicator_response.get('data') if indicator_response and indicator_response.get('success') else None
                if indicator_result is not None:
                    if isinstance(indicator_result, (pd.Series, np.ndarray)):
                        result_df[indicator] = indicator_result
                    elif isinstance(indicator_result, dict):
                        for key, value in indicator_result.items():
                            result_df[f"{indicator}_{key}"] = value
                    elif isinstance(indicator_result, tuple):
                        for i, value in enumerate(indicator_result):
                            result_df[f"{indicator}_{i}"] = value
            except Exception as e:
                print(f"计算指标 {indicator} 失败: {str(e)}")
                continue

        return result_df


def get_indicator_features(data: pd.DataFrame, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
    """获取指标特征的便捷函数

    Args:
        data: K线数据
        indicators: 指标列表

    Returns:
        指标特征字典
    """
    calculator = create_basic_indicators()
    return calculator.get_indicator_features(data, indicators)


def get_signals(data: pd.DataFrame) -> Dict[str, Any]:
    """获取交易信号的便捷函数

    Args:
        data: K线数据

    Returns:
        交易信号字典
    """
    calculator = create_basic_indicators()

    signals = {}
    signals.update(calculator.get_trend_signals(data))
    signals.update(calculator.get_momentum_signals(data))

    return signals


# 向后兼容的别名
def get_basic_indicators() -> BasicIndicators:
    """获取基础指标计算器（向后兼容）"""
    return create_basic_indicators()
