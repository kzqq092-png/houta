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
            "author": "HIkyuu-UI Team",
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
                }
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
                # 已经是DataFrame，直接返回
                return result_data

            elif isinstance(result_data, pd.Series):
                # Series转换为DataFrame
                return pd.DataFrame({'value': result_data})

            elif isinstance(result_data, dict):
                # 字典转换为DataFrame
                return pd.DataFrame(result_data)

            elif isinstance(result_data, (list, tuple, np.ndarray)):
                # 数组转换为DataFrame
                if len(result_data) > 0 and isinstance(result_data[0], pd.Series):
                    # 多个Series
                    data_dict = {f'output_{i}': series for i, series in enumerate(result_data)}
                    return pd.DataFrame(data_dict)
                else:
                    # 单个数组
                    return pd.DataFrame({'value': result_data})

            else:
                # 其他类型，尝试转换
                return pd.DataFrame({'value': [result_data]})

        except Exception as e:
            logger.error(f"转换pandas-ta结果到DataFrame失败: {e}")
            # 返回空DataFrame
            return pd.DataFrame()

    def _initialize_metadata(self):
        """初始化指标元数据"""
        # 趋势指标
        self._metadata_cache['SMA'] = IndicatorMetadata(
            name='SMA',
            display_name='简单移动平均线',
            description='简单移动平均线，计算指定周期内的平均价格',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 10, '长度', 1, 1000)
            ],
            output_columns=['value'],
            tags=['trend', 'moving_average', 'basic'],
            source='pandas-ta'
        )

        self._metadata_cache['EMA'] = IndicatorMetadata(
            name='EMA',
            display_name='指数移动平均线',
            description='指数移动平均线，对近期价格赋予更高权重',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 10, '长度', 1, 1000)
            ],
            output_columns=['value'],
            tags=['trend', 'exponential', 'moving_average'],
            source='pandas-ta'
        )

        self._metadata_cache['MACD'] = IndicatorMetadata(
            name='MACD',
            display_name='指数平滑移动平均线',
            description='MACD指标，用于判断趋势变化和买卖信号',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('fast', ParameterType.INTEGER, 12, '快线周期', 1, 100),
                ParameterDef('slow', ParameterType.INTEGER, 26, '慢线周期', 1, 200),
                ParameterDef('signal', ParameterType.INTEGER, 9, '信号线周期', 1, 50)
            ],
            output_columns=['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9'],
            tags=['momentum', 'oscillator', 'classic'],
            source='pandas-ta'
        )

        self._metadata_cache['RSI'] = IndicatorMetadata(
            name='RSI',
            display_name='相对强弱指数',
            description='RSI指标，衡量价格变动的速度和变化，识别超买超卖',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 14, '长度', 1, 100)
            ],
            output_columns=['value'],
            tags=['momentum', 'oscillator', 'overbought_oversold'],
            source='pandas-ta'
        )

        self._metadata_cache['BBANDS'] = IndicatorMetadata(
            name='BBANDS',
            display_name='布林带',
            description='布林带指标，基于标准差的价格通道指标',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 5, '长度', 1, 100),
                ParameterDef('std', ParameterType.FLOAT, 2.0, '标准差倍数', 0.1, 5.0)
            ],
            output_columns=['BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0'],
            tags=['volatility', 'bands', 'channel'],
            source='pandas-ta'
        )

        self._metadata_cache['ATR'] = IndicatorMetadata(
            name='ATR',
            display_name='平均真实波幅',
            description='ATR指标，衡量价格波动的强度',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('length', ParameterType.INTEGER, 14, '长度', 1, 100)
            ],
            output_columns=['value'],
            tags=['volatility', 'range', 'risk'],
            source='pandas-ta'
        )

        self._metadata_cache['OBV'] = IndicatorMetadata(
            name='OBV',
            display_name='能量潮',
            description='OBV指标，通过成交量变化衡量买卖力道',
            category=IndicatorCategory.VOLUME,
            parameters=[],
            output_columns=['value'],
            tags=['volume', 'accumulation', 'distribution'],
            source='pandas-ta'
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
