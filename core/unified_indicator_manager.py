"""
统一指标管理器
集成TA-Lib，提供完整的技术指标计算、分类管理和中英文对照功能
优化版本：支持更多指标，完善备用实现，优化性能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import warnings
from dataclasses import dataclass
from enum import Enum
import hashlib

warnings.filterwarnings('ignore')

# 尝试导入TA-Lib
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("Warning: TA-Lib not available, using fallback implementations")


class IndicatorCategory(Enum):
    """指标分类枚举"""
    OVERLAP_STUDIES = "重叠研究"
    MOMENTUM_INDICATORS = "动量指标"
    VOLUME_INDICATORS = "成交量指标"
    VOLATILITY_INDICATORS = "波动率指标"
    PRICE_TRANSFORM = "价格变换"
    CYCLE_INDICATORS = "周期指标"
    PATTERN_RECOGNITION = "形态识别"
    STATISTIC_FUNCTIONS = "统计函数"
    MATH_TRANSFORM = "数学变换"
    MATH_OPERATORS = "数学运算"


@dataclass
class IndicatorInfo:
    """指标信息数据类"""
    name: str  # 英文名称
    chinese_name: str  # 中文名称
    category: IndicatorCategory  # 分类
    description: str  # 描述
    inputs: List[str]  # 输入参数
    outputs: List[str]  # 输出参数
    parameters: Dict[str, Any]  # 默认参数
    talib_func: Optional[str] = None  # TA-Lib函数名


class UnifiedIndicatorManager:
    """统一指标管理器 - 优化版本"""

    def __init__(self):
        """初始化统一指标管理器"""
        self.cache = {}
        self.max_cache_size = 200  # 增加缓存大小
        self._init_indicator_registry()

    def _init_indicator_registry(self):
        """初始化指标注册表 - 完整版本"""
        self.indicators = {}

        # 添加重叠研究指标
        self.indicators['SMA'] = IndicatorInfo(
            name='SMA',
            chinese_name='简单移动平均',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='简单移动平均线',
            inputs=['close'],
            outputs=['sma'],
            parameters={'period': 20},
            talib_func='SMA'
        )

        self.indicators['MA'] = IndicatorInfo(
            name='MA',
            chinese_name='移动平均',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='移动平均线',
            inputs=['close'],
            outputs=['ma'],
            parameters={'period': 20},
            talib_func='SMA'
        )

        self.indicators['EMA'] = IndicatorInfo(
            name='EMA',
            chinese_name='指数移动平均',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='指数移动平均线',
            inputs=['close'],
            outputs=['ema'],
            parameters={'period': 20},
            talib_func='EMA'
        )

        self.indicators['WMA'] = IndicatorInfo(
            name='WMA',
            chinese_name='加权移动平均',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='加权移动平均线',
            inputs=['close'],
            outputs=['wma'],
            parameters={'period': 20},
            talib_func='WMA'
        )

        self.indicators['BBANDS'] = IndicatorInfo(
            name='BBANDS',
            chinese_name='布林带',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='布林带指标',
            inputs=['close'],
            outputs=['upperband', 'middleband', 'lowerband'],
            parameters={'period': 20, 'std_dev': 2},
            talib_func='BBANDS'
        )

        self.indicators['BOLL'] = IndicatorInfo(
            name='BOLL',
            chinese_name='布林线',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='布林线指标',
            inputs=['close'],
            outputs=['upper', 'middle', 'lower'],
            parameters={'period': 20, 'std_dev': 2},
            talib_func='BBANDS'
        )

        self.indicators['SAR'] = IndicatorInfo(
            name='SAR',
            chinese_name='抛物线SAR',
            category=IndicatorCategory.OVERLAP_STUDIES,
            description='抛物线止损转向指标',
            inputs=['high', 'low'],
            outputs=['sar'],
            parameters={'acceleration': 0.02, 'maximum': 0.2},
            talib_func='SAR'
        ),

        # 添加动量指标
        self._add_momentum_indicators()

        # 添加成交量指标
        self._add_volume_indicators()

        # 添加波动率指标
        self._add_volatility_indicators()

        # 添加其他分类指标
        self._add_other_indicators()

    def _add_momentum_indicators(self):
        """添加动量指标"""
        self.indicators['MACD'] = IndicatorInfo(
            name='MACD',
            chinese_name='MACD',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='MACD指标',
            inputs=['close'],
            outputs=['macd', 'macdsignal', 'macdhist'],
            parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            talib_func='MACD'
        )

        self.indicators['RSI'] = IndicatorInfo(
            name='RSI',
            chinese_name='相对强弱指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='相对强弱指标',
            inputs=['close'],
            outputs=['rsi'],
            parameters={'period': 14},
            talib_func='RSI'
        )

        self.indicators['STOCH'] = IndicatorInfo(
            name='STOCH',
            chinese_name='随机指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='随机指标',
            inputs=['high', 'low', 'close'],
            outputs=['slowk', 'slowd'],
            parameters={'k_period': 14, 'd_period': 3, 'j_period': 3},
            talib_func='STOCH'
        )

        self.indicators['WILLR'] = IndicatorInfo(
            name='WILLR',
            chinese_name='威廉指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='威廉指标',
            inputs=['high', 'low', 'close'],
            outputs=['willr'],
            parameters={'period': 14},
            talib_func='WILLR'
        )

        self.indicators['ADX'] = IndicatorInfo(
            name='ADX',
            chinese_name='平均方向指数',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='平均方向指数',
            inputs=['high', 'low', 'close'],
            outputs=['adx'],
            parameters={'period': 14},
            talib_func='ADX'
        )

        self.indicators['CCI'] = IndicatorInfo(
            name='CCI',
            chinese_name='顺势指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='顺势指标',
            inputs=['high', 'low', 'close'],
            outputs=['cci'],
            parameters={'period': 14},
            talib_func='CCI'
        )

        self.indicators['MOM'] = IndicatorInfo(
            name='MOM',
            chinese_name='动量指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='动量指标',
            inputs=['close'],
            outputs=['mom'],
            parameters={'period': 10},
            talib_func='MOM'
        )

        self.indicators['ROC'] = IndicatorInfo(
            name='ROC',
            chinese_name='变动率指标',
            category=IndicatorCategory.MOMENTUM_INDICATORS,
            description='变动率指标',
            inputs=['close'],
            outputs=['roc'],
            parameters={'period': 10},
            talib_func='ROC'
        )

    def _add_volume_indicators(self):
        """添加成交量指标"""
        volume_indicators = {
            'OBV': IndicatorInfo(
                name='OBV',
                chinese_name='能量潮',
                category=IndicatorCategory.VOLUME_INDICATORS,
                description='平衡交易量指标',
                inputs=['close', 'volume'],
                outputs=['obv'],
                parameters={},
                talib_func='OBV'
            ),
            'AD': IndicatorInfo(
                name='AD',
                chinese_name='累积分布线',
                category=IndicatorCategory.VOLUME_INDICATORS,
                description='累积分布线指标',
                inputs=['high', 'low', 'close', 'volume'],
                outputs=['ad'],
                parameters={},
                talib_func='AD'
            ),
        }
        self.indicators.update(volume_indicators)

    def _add_volatility_indicators(self):
        """添加波动率指标"""
        self.indicators['ATR'] = IndicatorInfo(
            name='ATR',
            chinese_name='真实波动幅度',
            category=IndicatorCategory.VOLATILITY_INDICATORS,
            description='真实波动幅度',
            inputs=['high', 'low', 'close'],
            outputs=['atr'],
            parameters={'period': 14},
            talib_func='ATR'
        )

        self.indicators['NATR'] = IndicatorInfo(
            name='NATR',
            chinese_name='标准化真实波动幅度',
            category=IndicatorCategory.VOLATILITY_INDICATORS,
            description='标准化真实波动幅度',
            inputs=['high', 'low', 'close'],
            outputs=['natr'],
            parameters={'period': 14},
            talib_func='NATR'
        )

    def _add_other_indicators(self):
        """添加其他分类的指标"""
        # 这里可以继续添加更多指标
        pass

    def get_indicator_list(self, category: Optional[IndicatorCategory] = None,
                           use_chinese: bool = False) -> List[str]:
        """获取指标列表

        Args:
            category: 指标分类，None表示获取所有指标
            use_chinese: 是否返回中文名称

        Returns:
            指标名称列表
        """
        if category is None:
            indicators = list(self.indicators.values())
        else:
            indicators = [info for info in self.indicators.values() if info.category == category]

        if use_chinese:
            return [info.chinese_name for info in indicators]
        else:
            return [info.name for info in indicators]

    def get_categories(self, use_chinese: bool = False) -> List[str]:
        """获取所有分类

        Args:
            use_chinese: 是否返回中文名称

        Returns:
            分类列表
        """
        categories = set()
        for info in self.indicators.values():
            categories.add(info.category.value if use_chinese else info.category.name)
        return sorted(list(categories))

    def get_indicators_by_category(self, use_chinese: bool = False) -> Dict[str, List[str]]:
        """按分类获取指标

        Args:
            use_chinese: 是否使用中文名称

        Returns:
            分类->指标列表的字典
        """
        result = {}
        for name, info in self.indicators.items():
            category_name = info.category.value if use_chinese else info.category.name
            if category_name not in result:
                result[category_name] = []
            indicator_name = info.chinese_name if use_chinese else info.name
            result[category_name].append(indicator_name)

        # 排序
        for category in result:
            result[category].sort()

        return result

    def get_indicator_info(self, name: str) -> Optional[IndicatorInfo]:
        """获取指标信息

        Args:
            name: 指标名称（英文或中文）

        Returns:
            指标信息对象
        """
        # 直接查找英文名
        if name in self.indicators:
            return self.indicators[name]

        # 通过中文名查找
        for indicator_name, info in self.indicators.items():
            if info.chinese_name == name:
                return info

        return None

    def calculate_indicator(self, name: str, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                            params: Dict[str, Any] = None) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
        """计算指标

        Args:
            name: 指标名称（英文或中文）
            data: 价格数据
            params: 指标参数字典

        Returns:
            计算结果
        """
        # 获取指标信息
        info = self.get_indicator_info(name)
        if info is None:
            raise ValueError(f"未知指标: {name}")

        # 合并默认参数
        final_params = info.parameters.copy()
        if params:
            final_params.update(params)

        # 生成缓存键
        cache_key = self._generate_cache_key(info.name, data, final_params)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 计算指标
        result = self._calculate_with_talib_or_fallback(info, data, final_params)

        # 缓存结果
        self._update_cache(cache_key, result)

        return result

    def _calculate_with_talib_or_fallback(self, info: IndicatorInfo,
                                          data: Union[pd.DataFrame, Dict[str, pd.Series]],
                                          params: Dict[str, Any]) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
        """使用TA-Lib计算或降级到自定义实现"""
        if TALIB_AVAILABLE and info.talib_func and hasattr(talib, info.talib_func):
            try:
                return self._calculate_with_talib(info, data, params)
            except Exception as e:
                print(f"TA-Lib计算失败，使用备用实现: {e}")
                return self._calculate_with_fallback(info, data, params)
        else:
            return self._calculate_with_fallback(info, data, params)

    def _calculate_with_talib(self, info: IndicatorInfo,
                              data: Union[pd.DataFrame, Dict[str, pd.Series]],
                              params: Dict[str, Any]) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
        """使用TA-Lib计算指标"""
        try:
            func = getattr(talib, info.talib_func)

            # 准备输入数据
            inputs = []
            original_index = None

            if isinstance(data, pd.DataFrame):
                original_index = data.index
                for input_name in info.inputs:
                    column_data = None
                    # 尝试不同的列名匹配方式
                    for col_name in [input_name, input_name.lower(), input_name.upper()]:
                        if col_name in data.columns:
                            column_data = data[col_name]
                            break

                    if column_data is None:
                        raise ValueError(f"缺少输入数据: {input_name}")

                    # 数据预处理：移除NaN值，转换为float64
                    clean_data = column_data.fillna(method='ffill').fillna(method='bfill')
                    clean_data = clean_data.astype(np.float64)
                    inputs.append(clean_data.values)

            elif isinstance(data, dict):
                # 假设字典中的所有Series有相同的索引
                first_series = next(iter(data.values()))
                if hasattr(first_series, 'index'):
                    original_index = first_series.index

                for input_name in info.inputs:
                    if input_name not in data:
                        raise ValueError(f"缺少输入数据: {input_name}")

                    series_data = data[input_name]
                    if hasattr(series_data, 'values'):
                        # 数据预处理
                        clean_data = series_data.fillna(method='ffill').fillna(method='bfill')
                        clean_data = clean_data.astype(np.float64)
                        inputs.append(clean_data.values)
                    else:
                        # 如果是numpy数组
                        clean_data = pd.Series(series_data).fillna(method='ffill').fillna(method='bfill')
                        clean_data = clean_data.astype(np.float64)
                        inputs.append(clean_data.values)

            # 验证输入数据
            for i, input_data in enumerate(inputs):
                if len(input_data) < 2:
                    raise ValueError(f"输入数据 {info.inputs[i]} 长度不足")
                if np.all(np.isnan(input_data)):
                    raise ValueError(f"输入数据 {info.inputs[i]} 全部为NaN")

            # 调用TA-Lib函数

            # 参数名映射和清理
            talib_params = params.copy()

            # 映射period到timeperiod
            if 'period' in talib_params and 'timeperiod' not in talib_params:
                talib_params['timeperiod'] = talib_params.pop('period')
            elif 'period' in talib_params and 'timeperiod' in talib_params:
                # 如果两个都存在，移除period，保留timeperiod
                talib_params.pop('period')

            # 映射其他参数名
            param_mappings = {
                'fast_period': 'fastperiod',
                'slow_period': 'slowperiod',
                'signal_period': 'signalperiod',
                'std_dev': 'nbdevup'  # 布林带标准差
            }

            for old_name, new_name in param_mappings.items():
                if old_name in talib_params and new_name not in talib_params:
                    talib_params[new_name] = talib_params.pop(old_name)
                elif old_name in talib_params and new_name in talib_params:
                    # 如果两个都存在，移除旧名称
                    talib_params.pop(old_name)

            # 对于布林带，需要设置nbdevdn等于nbdevup
            if 'nbdevup' in talib_params and 'nbdevdn' not in talib_params:
                talib_params['nbdevdn'] = talib_params['nbdevup']

            result = func(*inputs, **talib_params)

            # 处理返回结果
            if isinstance(result, tuple):
                # 多个输出
                result_dict = {}
                for i, output_name in enumerate(info.outputs):
                    if original_index is not None:
                        result_series = pd.Series(result[i], index=original_index, name=output_name)
                    else:
                        result_series = pd.Series(result[i], name=output_name)
                    result_dict[output_name] = result_series
                return result_dict
            else:
                # 单个输出
                if original_index is not None:
                    return pd.Series(result, index=original_index, name=info.outputs[0])
                else:
                    return pd.Series(result, name=info.outputs[0])

        except Exception as e:
            print(f"TA-Lib计算指标 {info.name} 失败: {str(e)}")
            print(f"参数: {params}")
            print(f"输入数据形状: {[inp.shape if hasattr(inp, 'shape') else len(inp) for inp in inputs] if 'inputs' in locals() else 'N/A'}")
            raise

    def _calculate_with_fallback(self, info: IndicatorInfo,
                                 data: Union[pd.DataFrame, Dict[str, pd.Series]],
                                 params: Dict[str, Any]) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
        """使用备用实现计算指标 - 完善版本"""
        # 处理别名映射
        if info.name in ['MA', 'SMA']:
            return self._fallback_sma(data, params.get('timeperiod', params.get('period', 20)))
        elif info.name == 'EMA':
            return self._fallback_ema(data, params.get('timeperiod', params.get('period', 20)))
        elif info.name == 'MACD':
            return self._fallback_macd(data, params)
        elif info.name == 'RSI':
            return self._fallback_rsi(data, params.get('timeperiod', params.get('period', 14)))
        elif info.name in ['BBANDS', 'BOLL']:
            return self._fallback_bbands(data, params)
        elif info.name == 'ATR':
            return self._fallback_atr(data, params.get('timeperiod', params.get('period', 14)))
        elif info.name in ['STOCH', 'KDJ']:
            return self._fallback_kdj(data, params)
        elif info.name == 'OBV':
            return self._fallback_obv(data)
        elif info.name == 'CCI':
            return self._fallback_cci(data, params.get('timeperiod', params.get('period', 14)))
        else:
            raise NotImplementedError(f"指标 {info.name} 的备用实现尚未完成")

    def _fallback_sma(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """SMA备用实现"""
        close = self._get_close_data(data)
        result = close.rolling(window=period).mean()
        result.name = 'sma'
        return result

    def _fallback_ema(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """EMA备用实现"""
        close = self._get_close_data(data)
        result = close.ewm(span=period).mean()
        result.name = 'ema'
        return result

    def _fallback_macd(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """MACD备用实现"""
        close = self._get_close_data(data)
        fast_period = params.get('fastperiod', 12)
        slow_period = params.get('slowperiod', 26)
        signal_period = params.get('signalperiod', 9)

        ema_fast = close.ewm(span=fast_period).mean()
        ema_slow = close.ewm(span=slow_period).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'macdsignal': signal_line,
            'macdhist': histogram
        }

    def _fallback_rsi(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """RSI备用实现"""
        close = self._get_close_data(data)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi.name = 'rsi'
        return rsi

    def _fallback_bbands(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """布林带备用实现"""
        close = self._get_close_data(data)
        period = params.get('timeperiod', params.get('period', 20))
        std_dev = params.get('nbdevup', params.get('std_dev', 2))

        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upperband': upper_band,
            'upper': upper_band,  # 别名支持
            'middleband': sma,
            'middle': sma,  # 别名支持
            'lowerband': lower_band,
            'lower': lower_band  # 别名支持
        }

    def _fallback_atr(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """ATR备用实现"""
        if isinstance(data, pd.DataFrame):
            high = data['high']
            low = data['low']
            close = data['close']
        else:
            high = data['high']
            low = data['low']
            close = data['close']

        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        atr.name = 'atr'
        return atr

    def _fallback_kdj(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """KDJ备用实现"""
        if isinstance(data, pd.DataFrame):
            high = data['high']
            low = data['low']
            close = data['close']
        else:
            high = data['high']
            low = data['low']
            close = data['close']

        k_period = params.get('fastk_period', params.get('k_period', 14))
        d_period = params.get('slowk_period', params.get('d_period', 3))

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        rsv = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k = rsv.ewm(alpha=1/d_period).mean()
        d = k.ewm(alpha=1/d_period).mean()
        j = 3 * k - 2 * d

        return {
            'slowk': k,
            'k': k,  # 别名支持
            'slowd': d,
            'd': d,  # 别名支持
            'j': j
        }

    def _fallback_obv(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> pd.Series:
        """OBV备用实现"""
        close = self._get_close_data(data)
        if isinstance(data, pd.DataFrame):
            volume = data['volume']
        else:
            volume = data['volume']

        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]

        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        obv.name = 'obv'
        return obv

    def _fallback_cci(self, data: Union[pd.DataFrame, Dict[str, pd.Series]], period: int) -> pd.Series:
        """CCI备用实现"""
        if isinstance(data, pd.DataFrame):
            high = data['high']
            low = data['low']
            close = data['close']
        else:
            high = data['high']
            low = data['low']
            close = data['close']

        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )

        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        cci.name = 'cci'
        return cci

    def _get_close_data(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> pd.Series:
        """获取收盘价数据"""
        if isinstance(data, pd.DataFrame):
            if 'close' in data.columns:
                return data['close']
            elif 'Close' in data.columns:
                return data['Close']
            elif 'CLOSE' in data.columns:
                return data['CLOSE']
            else:
                raise ValueError("无法找到收盘价数据列")
        elif isinstance(data, dict):
            if 'close' in data:
                return data['close']
            elif 'Close' in data:
                return data['Close']
            elif 'CLOSE' in data:
                return data['CLOSE']
            else:
                raise ValueError("无法找到收盘价数据")
        else:
            raise ValueError("不支持的数据类型")

    def _generate_cache_key(self, name: str, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                            params: Dict[str, Any]) -> str:
        """生成缓存键 - 优化版本"""
        # 使用数据哈希和参数生成缓存键
        if isinstance(data, pd.DataFrame):
            data_hash = hashlib.md5(str(data.shape).encode() + str(data.index[-1]).encode()).hexdigest()[:8]
        else:
            data_hash = hashlib.md5(str(len(data)).encode()).hexdigest()[:8]

        params_str = str(sorted(params.items()))
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

        return f"{name}_{data_hash}_{params_hash}"

    def _update_cache(self, key: str, value: Any):
        """更新缓存"""
        if len(self.cache) >= self.max_cache_size:
            # 删除最旧的缓存项
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = value

    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()

    def get_chinese_name(self, english_name: str) -> Optional[str]:
        """获取指标中文名称"""
        info = self.get_indicator_info(english_name)
        return info.chinese_name if info else None

    def get_english_name(self, chinese_name: str) -> Optional[str]:
        """获取指标英文名称"""
        info = self.get_indicator_info(chinese_name)
        return info.name if info else None

    def get_indicator_category(self, indicator_name: str) -> Optional[str]:
        """获取指标分类"""
        info = self.get_indicator_info(indicator_name)
        return info.category.value if info else None

    # 向后兼容的便捷方法
    def calc_ma(self, data, period=20):
        """计算移动平均 - 向后兼容方法"""
        try:
            result = self.calculate_indicator('MA', data, params={'period': period})
            if isinstance(result, pd.Series):
                return result
            return result.get('ma', pd.Series(dtype=float))
        except Exception as e:
            self.logger.error(f"计算MA失败: {e}")
            return pd.Series(dtype=float)

    def calc_ema(self, data, period=20):
        """计算指数移动平均 - 向后兼容方法"""
        try:
            result = self.calculate_indicator('EMA', data, params={'period': period})
            if isinstance(result, pd.Series):
                return result
            return result.get('ema', pd.Series(dtype=float))
        except Exception as e:
            self.logger.error(f"计算EMA失败: {e}")
            return pd.Series(dtype=float)

    def calc_macd(self, data, fast_period=12, slow_period=26, signal_period=9):
        """计算MACD - 向后兼容方法"""
        try:
            result = self.calculate_indicator('MACD', data, params={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period
            })
            if isinstance(result, dict):
                return (result.get('macd', pd.Series(dtype=float)),
                        result.get('macdsignal', pd.Series(dtype=float)),
                        result.get('macdhist', pd.Series(dtype=float)))
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
        except Exception as e:
            self.logger.error(f"计算MACD失败: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    def calc_rsi(self, data, period=14):
        """计算RSI - 向后兼容方法"""
        try:
            result = self.calculate_indicator('RSI', data, params={'period': period})
            if isinstance(result, pd.Series):
                return result
            return result.get('rsi', pd.Series(dtype=float))
        except Exception as e:
            self.logger.error(f"计算RSI失败: {e}")
            return pd.Series(dtype=float)

    def get_all_indicators(self) -> Dict[str, IndicatorInfo]:
        """获取所有指标信息 - 向后兼容方法"""
        return self.indicators.copy()


# 全局实例
_unified_indicator_manager = None


def get_unified_indicator_manager() -> UnifiedIndicatorManager:
    """获取统一指标管理器实例"""
    global _unified_indicator_manager
    if _unified_indicator_manager is None:
        _unified_indicator_manager = UnifiedIndicatorManager()
    return _unified_indicator_manager


# 便捷函数
def calculate_indicator(name: str, data: Union[pd.DataFrame, Dict[str, pd.Series]],
                        **params) -> Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]:
    """计算指标的便捷函数"""
    manager = get_unified_indicator_manager()
    return manager.calculate_indicator(name, data, params)


def get_indicator_list(category: Optional[str] = None, use_chinese: bool = False) -> List[str]:
    """获取指标列表的便捷函数"""
    manager = get_unified_indicator_manager()
    cat_enum = None
    if category:
        # 尝试匹配分类枚举
        for cat in IndicatorCategory:
            if cat.name == category or cat.value == category:
                cat_enum = cat
                break
    return manager.get_indicator_list(cat_enum, use_chinese)


def get_indicators_by_category(use_chinese: bool = False) -> Dict[str, List[str]]:
    """获取按分类组织的指标列表的便捷函数"""
    manager = get_unified_indicator_manager()
    return manager.get_indicators_by_category(use_chinese)


def get_indicator_chinese_name(english_name: str) -> Optional[str]:
    """获取指标中文名称的便捷函数"""
    manager = get_unified_indicator_manager()
    return manager.get_chinese_name(english_name)


def get_indicator_english_name(chinese_name: str) -> Optional[str]:
    """获取指标英文名称的便捷函数"""
    manager = get_unified_indicator_manager()
    return manager.get_english_name(chinese_name)
