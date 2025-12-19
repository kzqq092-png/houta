from loguru import logger
"""
Pandas-TA指标插件

基于pandas-ta库的纯Python技术指标计算插件。
pandas-ta提供易于使用的技术指标实现，与pandas DataFrame完美集成。
"""

import pandas as pd
import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None

from core.indicator_extensions import (
    IIndicatorPlugin, IndicatorMetadata, ParameterDef, ParameterType,
    IndicatorCategory, StandardKlineData, StandardIndicatorResult,
    IndicatorCalculationContext
)

logger = logger


class PandasTAIndicatorsPlugin(IIndicatorPlugin):
    """
    Pandas-TA指标插件

    封装pandas-ta库的指标计算能力，提供纯Python的技术指标实现。
    pandas-ta具有良好的易用性和扩展性。
    """

    def __init__(self):
        self._plugin_info = {
            "id": "pandas_ta_indicators",
            "name": "Pandas-TA指标插件",
            "version": "1.0.0",
            "description": "基于pandas-ta库的纯Python技术指标计算插件",
            "author": "FactorWeave-Quant Team",
            "backend": "pandas-ta Python",
            "performance_level": "medium"
        }

        # 指标元数据缓存
        self._metadata_cache = {}
        self._initialize_metadata()

        # 统计信息
        self._calculation_count = 0
        self._total_calculation_time = 0.0
        self._error_count = 0

        if not PANDAS_TA_AVAILABLE:
            logger.warning("pandas-ta库不可用，Pandas-TA指标插件将无法正常工作")

    @property
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        return self._plugin_info.copy()

    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        if not PANDAS_TA_AVAILABLE:
            return []

        return [
            # 趋势指标
            'SMA', 'EMA', 'WMA', 'HMA', 'KAMA', 'MAMA', 'TRIMA', 'T3',
            'MACD', 'PPO', 'TRIX', 'UO', 'VORTEX',

            # 动量指标
            'RSI', 'STOCH', 'STOCHF', 'STOCHRSI', 'CCI', 'CMO', 'ROC', 'WILLR',
            'ADX', 'AROON', 'BOP', 'CG', 'CTI', 'DPO', 'ER', 'FISHER', 'INERTIA',
            'KDJ', 'KST', 'MFI', 'MOM', 'PGO', 'PSL', 'PVO', 'QQE', 'SLOPE',
            'SMI', 'SQUEEZE', 'STDEV', 'TSI', 'ULTIMATE',

            # 波动率指标
            'ATR', 'NATR', 'TRUE_RANGE', 'BBANDS', 'DONCHIAN', 'KELTNER', 'MASSI',
            'PDIST', 'RVI', 'THERMO', 'UI', 'HWMA',

            # 成交量指标
            'AD', 'ADOSC', 'AOBV', 'CMF', 'EFI', 'EOM', 'KVO', 'MFI', 'NVI',
            'OBV', 'PVI', 'PVOL', 'PVOT', 'PVTR', 'VWAP', 'VWMA',

            # 价格指标
            'HL2', 'HLC3', 'HLCC4', 'OHLC4', 'TYPICAL', 'WEIGHTED',

            # 统计指标
            'ENTROPY', 'KURTOSIS', 'MAD', 'MEDIAN', 'QUANTILE', 'SKEW',
            'STDEV', 'VARIANCE', 'ZSCORE',

            # 趋势识别
            'DECREASING', 'INCREASING', 'LONG_RUN', 'SHORT_RUN',

            # 周期指标
            'EBSW', 'SINWMA', 'SUPERTREND'
        ]

    def get_indicator_metadata(self, indicator_name: str) -> Optional[IndicatorMetadata]:
        """获取指标元数据"""
        return self._metadata_cache.get(indicator_name.upper())

    def validate_parameters(self, indicator_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """验证指标参数"""
        indicator_name = indicator_name.upper()
        
        # 检查指标是否支持
        if indicator_name not in self.get_supported_indicators():
            return False, f"不支持的指标: {indicator_name}"
        
        # 基础参数验证
        try:
            # 验证通用数值参数
            for param_name, param_value in parameters.items():
                if isinstance(param_value, (int, float)):
                    if not np.isfinite(param_value):
                        return False, f"参数 {param_name} 必须是有限的数值"
            
            # 特殊指标的特殊验证
            if indicator_name in ['SMA', 'EMA', 'WMA', 'RSI', 'ATR']:
                length = parameters.get('length', 10)
                if not isinstance(length, int) or length <= 0 or length > 10000:
                    return False, "length参数必须是1-10000之间的正整数"
            
            elif indicator_name == 'MACD':
                fast = parameters.get('fast', 12)
                slow = parameters.get('slow', 26)
                signal = parameters.get('signal', 9)
                if not all(isinstance(x, int) and x > 0 for x in [fast, slow, signal]):
                    return False, "MACD参数必须是正整数"
                if fast >= slow:
                    return False, "MACD快线周期必须小于慢线周期"
            
            elif indicator_name == 'ADOSC':
                fast = parameters.get('fast', 3)
                slow = parameters.get('slow', 10)
                if not all(isinstance(x, int) and x > 0 for x in [fast, slow]):
                    return False, "ADOSC参数必须是正整数"
                if fast >= slow:
                    return False, "ADOSC快线周期必须小于慢线周期"
            
            elif indicator_name == 'BBANDS':
                length = parameters.get('length', 20)
                std = parameters.get('std', 2.0)
                if not isinstance(length, int) or length <= 0 or length > 1000:
                    return False, "length参数必须是1-1000之间的正整数"
                if not isinstance(std, (int, float)) or std <= 0 or std > 10:
                    return False, "std参数必须是0.1-10之间的正数"
            
            return True, ""
            
        except Exception as e:
            return False, f"参数验证失败: {e}"

    def calculate_indicator(self, indicator_name: str, kline_data: StandardKlineData,
                            params: Dict[str, Any], context: IndicatorCalculationContext) -> StandardIndicatorResult:
        """计算单个指标"""
        if not PANDAS_TA_AVAILABLE:
            raise RuntimeError("pandas-ta库不可用，无法计算指标")

        start_time = time.time()
        self._calculation_count += 1

        try:
            # 验证参数
            is_valid, error_msg = self.validate_parameters(indicator_name, params)
            if not is_valid:
                raise ValueError(f"参数验证失败: {error_msg}")

            # 准备输入数据
            df = kline_data.to_dataframe()

            # 计算指标
            result_data = self._calculate_pandas_ta_indicator(indicator_name.upper(), df, params)

            # 转换结果格式
            result_df = self._convert_result_to_dataframe(result_data, indicator_name)

            calculation_time = (time.time() - start_time) * 1000
            self._total_calculation_time += calculation_time

            return StandardIndicatorResult(
                indicator_name=indicator_name,
                data=result_df,
                metadata={
                    'backend': 'pandas-ta',
                    'calculation_time_ms': calculation_time,
                    'symbol': context.symbol,
                    'timeframe': context.timeframe,
                    'parameters': params.copy(),
                    'data_points': len(result_df)
                },
                calculation_time_ms=calculation_time,
                parameters=params.copy()
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"Pandas-TA指标计算失败 {indicator_name}: {e}")
            raise

    def _calculate_pandas_ta_indicator(self, indicator_name: str, df: pd.DataFrame, params: Dict[str, Any]) -> Any:
        """使用pandas-ta计算指标"""
        try:
            # 趋势指标
            if indicator_name == 'SMA':
                length = params.get('length', 10)
                return ta.sma(df['close'], length=length)

            elif indicator_name == 'EMA':
                length = params.get('length', 10)
                return ta.ema(df['close'], length=length)

            elif indicator_name == 'WMA':
                length = params.get('length', 10)
                return ta.wma(df['close'], length=length)

            elif indicator_name == 'HMA':
                length = params.get('length', 10)
                return ta.hma(df['close'], length=length)

            elif indicator_name == 'KAMA':
                length = params.get('length', 10)
                return ta.kama(df['close'], length=length)

            elif indicator_name == 'T3':
                length = params.get('length', 10)
                a = params.get('a', 0.7)
                return ta.t3(df['close'], length=length, a=a)

            elif indicator_name == 'MACD':
                fast = params.get('fast', 12)
                slow = params.get('slow', 26)
                signal = params.get('signal', 9)
                return ta.macd(df['close'], fast=fast, slow=slow, signal=signal)

            elif indicator_name == 'PPO':
                fast = params.get('fast', 12)
                slow = params.get('slow', 26)
                signal = params.get('signal', 9)
                return ta.ppo(df['close'], fast=fast, slow=slow, signal=signal)

            # 动量指标
            elif indicator_name == 'RSI':
                length = params.get('length', 14)
                return ta.rsi(df['close'], length=length)

            elif indicator_name == 'STOCH':
                k = params.get('k', 14)
                d = params.get('d', 3)
                smooth_k = params.get('smooth_k', 3)
                return ta.stoch(df['high'], df['low'], df['close'], k=k, d=d, smooth_k=smooth_k)

            elif indicator_name == 'STOCHRSI':
                length = params.get('length', 14)
                rsi_length = params.get('rsi_length', 14)
                k = params.get('k', 3)
                d = params.get('d', 3)
                return ta.stochrsi(df['close'], length=length, rsi_length=rsi_length, k=k, d=d)

            elif indicator_name == 'CCI':
                length = params.get('length', 14)
                c = params.get('c', 0.015)
                return ta.cci(df['high'], df['low'], df['close'], length=length, c=c)

            elif indicator_name == 'CMO':
                length = params.get('length', 14)
                return ta.cmo(df['close'], length=length)

            elif indicator_name == 'ROC':
                length = params.get('length', 10)
                return ta.roc(df['close'], length=length)

            elif indicator_name == 'WILLR':
                length = params.get('length', 14)
                return ta.willr(df['high'], df['low'], df['close'], length=length)

            elif indicator_name == 'ADX':
                length = params.get('length', 14)
                return ta.adx(df['high'], df['low'], df['close'], length=length)

            elif indicator_name == 'AROON':
                length = params.get('length', 14)
                return ta.aroon(df['high'], df['low'], length=length)

            elif indicator_name == 'BOP':
                return ta.bop(df['open'], df['high'], df['low'], df['close'])

            elif indicator_name == 'KDJ':
                k = params.get('k', 9)
                d = params.get('d', 3)
                return ta.kdj(df['high'], df['low'], df['close'], k=k, d=d)

            elif indicator_name == 'MFI':
                length = params.get('length', 14)
                return ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=length)

            # 波动率指标
            elif indicator_name == 'ATR':
                length = params.get('length', 14)
                return ta.atr(df['high'], df['low'], df['close'], length=length)

            elif indicator_name == 'NATR':
                length = params.get('length', 14)
                return ta.natr(df['high'], df['low'], df['close'], length=length)

            elif indicator_name == 'TRUE_RANGE':
                return ta.true_range(df['high'], df['low'], df['close'])

            elif indicator_name == 'BBANDS':
                length = params.get('length', 5)
                std = params.get('std', 2)
                return ta.bbands(df['close'], length=length, std=std)

            elif indicator_name == 'DONCHIAN':
                lower_length = params.get('lower_length', 20)
                upper_length = params.get('upper_length', 20)
                return ta.donchian(df['high'], df['low'], lower_length=lower_length, upper_length=upper_length)

            elif indicator_name == 'KELTNER':
                length = params.get('length', 20)
                scalar = params.get('scalar', 2)
                return ta.kc(df['high'], df['low'], df['close'], length=length, scalar=scalar)

            # 成交量指标
            elif indicator_name == 'AD':
                return ta.ad(df['high'], df['low'], df['close'], df['volume'])

            elif indicator_name == 'ADOSC':
                fast = params.get('fast', 3)
                slow = params.get('slow', 10)
                return ta.adosc(df['high'], df['low'], df['close'], df['volume'], fast=fast, slow=slow)

            elif indicator_name == 'OBV':
                return ta.obv(df['close'], df['volume'])

            elif indicator_name == 'CMF':
                length = params.get('length', 20)
                return ta.cmf(df['high'], df['low'], df['close'], df['volume'], length=length)

            elif indicator_name == 'EFI':
                length = params.get('length', 13)
                return ta.efi(df['close'], df['volume'], length=length)

            elif indicator_name == 'VWAP':
                return ta.vwap(df['high'], df['low'], df['close'], df['volume'])

            elif indicator_name == 'VWMA':
                length = params.get('length', 10)
                return ta.vwma(df['close'], df['volume'], length=length)

            # 价格指标
            elif indicator_name == 'HL2':
                return ta.hl2(df['high'], df['low'])

            elif indicator_name == 'HLC3':
                return ta.hlc3(df['high'], df['low'], df['close'])

            elif indicator_name == 'OHLC4':
                return ta.ohlc4(df['open'], df['high'], df['low'], df['close'])

            # 统计指标
            elif indicator_name == 'STDEV':
                length = params.get('length', 30)
                return ta.stdev(df['close'], length=length)

            elif indicator_name == 'VARIANCE':
                length = params.get('length', 30)
                return ta.variance(df['close'], length=length)

            elif indicator_name == 'ZSCORE':
                length = params.get('length', 30)
                return ta.zscore(df['close'], length=length)

            elif indicator_name == 'ENTROPY':
                length = params.get('length', 10)
                return ta.entropy(df['close'], length=length)

            elif indicator_name == 'KURTOSIS':
                length = params.get('length', 30)
                return ta.kurtosis(df['close'], length=length)

            elif indicator_name == 'SKEW':
                length = params.get('length', 30)
                return ta.skew(df['close'], length=length)

            else:
                # 尝试动态调用pandas-ta函数
                if hasattr(ta, indicator_name.lower()):
                    func = getattr(ta, indicator_name.lower())
                    # 根据参数智能调用
                    return self._smart_call_pandas_ta_function(func, df, params)
                else:
                    raise ValueError(f"不支持的pandas-ta指标: {indicator_name}")

        except Exception as e:
            logger.error(f"pandas-ta指标计算错误 {indicator_name}: {e}")
            raise

    def _smart_call_pandas_ta_function(self, func, df: pd.DataFrame, params: Dict[str, Any]):
        """智能调用pandas-ta函数"""
        try:
            # 获取函数签名信息
            import inspect
            sig = inspect.signature(func)

            # 准备参数
            kwargs = params.copy()
            args = []

            # 根据函数签名智能传递数据
            for param_name in sig.parameters:
                if param_name in ['close', 'src']:
                    args.append(df['close'])
                elif param_name == 'high':
                    args.append(df['high'])
                elif param_name == 'low':
                    args.append(df['low'])
                elif param_name == 'open':
                    args.append(df['open'])
                elif param_name == 'volume':
                    args.append(df['volume'])
                elif param_name in kwargs:
                    # 参数已在kwargs中，跳过
                    continue
                else:
                    # 如果是第一个参数且没有明确指定，使用close价格
                    if len(args) == 0:
                        args.append(df['close'])
                    break

            # 调用函数
            return func(*args, **kwargs)

        except Exception as e:
            logger.error(f"智能调用pandas-ta函数失败: {e}")
            raise

    def _convert_result_to_dataframe(self, result_data: Any, indicator_name: str) -> pd.DataFrame:
        """将pandas-ta指标结果转换为DataFrame"""
        try:
            if isinstance(result_data, pd.DataFrame):
                # 已经是DataFrame，直接返回，但需要验证数据
                return self._validate_and_clean_dataframe(result_data, indicator_name)

            elif isinstance(result_data, pd.Series):
                # Series转换为DataFrame，但需要验证数据
                df = pd.DataFrame({'value': result_data})
                return self._validate_and_clean_dataframe(df, indicator_name)

            elif isinstance(result_data, dict):
                # 字典转换为DataFrame，但需要验证数据
                df = pd.DataFrame(result_data)
                return self._validate_and_clean_dataframe(df, indicator_name)

            elif isinstance(result_data, (list, tuple, np.ndarray)):
                # 数组转换为DataFrame，但需要验证数据
                if len(result_data) > 0 and isinstance(result_data[0], pd.Series):
                    # 多个Series
                    data_dict = {f'output_{i}': series for i, series in enumerate(result_data)}
                    df = pd.DataFrame(data_dict)
                    return self._validate_and_clean_dataframe(df, indicator_name)
                else:
                    # 单个数组，需要先验证数组内容
                    cleaned_data = self._clean_numeric_array(result_data)
                    df = pd.DataFrame({'value': cleaned_data})
                    return self._validate_and_clean_dataframe(df, indicator_name)

            else:
                # 其他类型，尝试转换但先验证
                try:
                    if isinstance(result_data, str):
                        # 尝试解析字符串为数值
                        cleaned_value = self._clean_numeric_value(result_data)
                        return pd.DataFrame({'value': [cleaned_value]})
                    else:
                        return pd.DataFrame({'value': [result_data]})
                except Exception as e:
                    logger.warning(f"无法转换值类型 {type(result_data)} 到数值: {result_data}")
                    return pd.DataFrame({'value': [np.nan]})

        except Exception as e:
            logger.error(f"转换pandas-ta结果到DataFrame失败: {e}")
            # 返回空DataFrame，但确保有合适的索引
            return pd.DataFrame()

    def _validate_and_clean_dataframe(self, df: pd.DataFrame, indicator_name: str) -> pd.DataFrame:
        """验证和清理DataFrame数据"""
        try:
            if df.empty:
                return df
            
            # 检查并清理每列的数据
            for column in df.columns:
                if df[column].dtype == 'object':
                    # 对于字符串列，尝试转换为数值
                    df[column] = df[column].apply(self._safe_convert_to_numeric)
                elif df[column].dtype in ['float64', 'int64', 'float32', 'int32']:
                    # 数值列，清理无效值
                    df[column] = df[column].replace([np.inf, -np.inf], np.nan)
            
            return df
            
        except Exception as e:
            logger.error(f"验证和清理DataFrame失败 {indicator_name}: {e}")
            return pd.DataFrame()

    def _clean_numeric_array(self, data: Any) -> np.ndarray:
        """清理数值数组中的无效数据"""
        try:
            if isinstance(data, (list, tuple)):
                # 清理列表数据
                cleaned = []
                for item in data:
                    try:
                        cleaned_item = self._clean_numeric_value(item)
                        cleaned.append(cleaned_item)
                    except (ValueError, TypeError):
                        cleaned.append(np.nan)
                return np.array(cleaned)
            elif isinstance(data, np.ndarray):
                # 处理numpy数组
                if data.dtype.kind in ['U', 'S']:  # Unicode or Byte strings
                    # 字符串数组，转换为数值
                    return np.array([self._safe_convert_to_numeric(item) for item in data])
                else:
                    # 数值数组，清理无效值
                    cleaned = data.astype(float)
                    cleaned[~np.isfinite(cleaned)] = np.nan
                    return cleaned
            else:
                return np.array([np.nan])
        except Exception as e:
            logger.warning(f"清理数值数组失败: {e}")
            return np.array([np.nan])

    def _clean_numeric_value(self, value: Any) -> float:
        """清理单个数值，处理字符串和异常情况"""
        try:
            if isinstance(value, str):
                # 检查是否包含重复模式
                if len(value) > 10 and value == value[0:6] * (len(value) // 6):
                    # 检测到重复字符串，返回NaN
                    logger.warning(f"检测到重复字符串模式: {value[:20]}...")
                    return np.nan
                
                # 尝试转换为浮点数
                try:
                    return float(value)
                except ValueError:
                    # 如果包含非数字字符，尝试提取数字
                    import re
                    numbers = re.findall(r'[-+]?\d*\.?\d+', value)
                    if numbers:
                        return float(numbers[0])
                    else:
                        logger.warning(f"无法从字符串提取数值: {value}")
                        return np.nan
            
            elif isinstance(value, (int, float)):
                if np.isfinite(value):
                    return float(value)
                else:
                    return np.nan
            
            else:
                logger.warning(f"不支持的值类型: {type(value)}")
                return np.nan
                
        except Exception as e:
            logger.warning(f"清理数值失败 {value}: {e}")
            return np.nan

    def _safe_convert_to_numeric(self, value: Any) -> Any:
        """安全地转换值为数值类型"""
        try:
            if pd.isna(value) or value is None:
                return np.nan
            
            if isinstance(value, (int, float)):
                return value if np.isfinite(value) else np.nan
            
            if isinstance(value, str):
                # 检查重复字符串模式
                if len(value) > 10 and value == value[0:6] * (len(value) // 6):
                    logger.warning(f"检测到重复字符串模式: {value[:20]}...")
                    return np.nan
                
                # 尝试直接转换
                try:
                    return float(value)
                except ValueError:
                    # 使用正则表达式提取数字
                    import re
                    numbers = re.findall(r'[-+]?\d*\.?\d+', value)
                    if numbers:
                        return float(numbers[0])
                    else:
                        return np.nan
            
            return np.nan
            
        except Exception as e:
            logger.debug(f"安全转换数值失败: {value} -> {e}")
            return np.nan

    def _initialize_metadata(self):
        """初始化指标元数据"""
        # 趋势指标
        self._metadata_cache['SMA'] = IndicatorMetadata(
            name='SMA',
            display_name='简单移动平均线',
            description='简单移动平均线，计算指定周期内的平均价格',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 10, 1, 1000, '移动平均周期')
            ],
            output_columns=['value'],
            tags=['trend', 'moving_average', 'basic']
        )

        self._metadata_cache['EMA'] = IndicatorMetadata(
            name='EMA',
            display_name='指数移动平均线',
            description='指数移动平均线，对近期价格赋予更高权重',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 10, 1, 1000, '移动平均周期')
            ],
            output_columns=['value'],
            tags=['trend', 'exponential', 'moving_average']
        )

        self._metadata_cache['MACD'] = IndicatorMetadata(
            name='MACD',
            display_name='指数平滑移动平均线',
            description='MACD指标，用于判断趋势变化和买卖信号',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('fast', ParameterType.INTEGER, 12, 1, 100, '快线周期'),
                ParameterDef('slow', ParameterType.INTEGER, 26, 1, 200, '慢线周期'),
                ParameterDef('signal', ParameterType.INTEGER, 9, 1, 50, '信号线周期')
            ],
            output_columns=['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9'],
            tags=['momentum', 'oscillator', 'classic']
        )

        self._metadata_cache['RSI'] = IndicatorMetadata(
            name='RSI',
            display_name='相对强弱指数',
            description='RSI指标，衡量价格变动的速度和变化，识别超买超卖',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 14, 1, 100, 'RSI周期')
            ],
            output_columns=['value'],
            tags=['momentum', 'oscillator', 'overbought_oversold']
        )

        self._metadata_cache['BBANDS'] = IndicatorMetadata(
            name='BBANDS',
            display_name='布林带',
            description='布林带指标，基于标准差的价格通道指标',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 5, 1, 100, '移动平均周期'),
                ParameterDef('std', ParameterType.FLOAT, 2.0, 0.1, 5.0, '标准差倍数')
            ],
            output_columns=['BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0'],
            tags=['volatility', 'bands', 'channel']
        )

        self._metadata_cache['ATR'] = IndicatorMetadata(
            name='ATR',
            display_name='平均真实波幅',
            description='ATR指标，衡量价格波动的强度',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 14, 1, 100, 'ATR周期')
            ],
            output_columns=['value'],
            tags=['volatility', 'range', 'risk']
        )

        self._metadata_cache['OBV'] = IndicatorMetadata(
            name='OBV',
            display_name='能量潮',
            description='OBV指标，通过成交量变化衡量买卖力道',
            category=IndicatorCategory.VOLUME,
            parameters=[],
            output_columns=['value'],
            tags=['volume', 'accumulation', 'distribution']
        )

        # 添加更多指标元数据...

    def get_statistics(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        avg_time = (self._total_calculation_time / self._calculation_count
                    if self._calculation_count > 0 else 0.0)

        return {
            'calculation_count': self._calculation_count,
            'total_calculation_time_ms': self._total_calculation_time,
            'average_calculation_time_ms': avg_time,
            'error_count': self._error_count,
            'error_rate': (self._error_count / max(self._calculation_count, 1)) * 100,
            'supported_indicators_count': len(self.get_supported_indicators()),
            'pandas_ta_available': PANDAS_TA_AVAILABLE
        }
