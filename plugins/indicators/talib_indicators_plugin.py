from loguru import logger
"""
TA-Lib指标插件

基于TA-Lib库的经典技术指标计算插件。
TA-Lib是广泛使用的技术分析库，提供150+种技术指标的高性能C实现。
"""

import pandas as pd
import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None

from core.indicator_extensions import (
    IIndicatorPlugin, IndicatorMetadata, ParameterDef, ParameterType,
    IndicatorCategory, StandardKlineData, StandardIndicatorResult,
    IndicatorCalculationContext
)

logger = logger


class TALibIndicatorsPlugin(IIndicatorPlugin):
    """
    TA-Lib指标插件

    封装TA-Lib库的指标计算能力，提供经典的技术指标实现。
    TA-Lib具有优秀的性能和广泛的兼容性。
    """

    def __init__(self):
        self._plugin_info = {
            "id": "talib_indicators",
            "name": "TA-Lib指标插件",
            "version": "1.0.0",
            "description": "基于TA-Lib库的经典技术指标计算插件",
            "author": "FactorWeave-Quant Team",
            "backend": "TA-Lib C",
            "performance_level": "high"
        }

        # 指标元数据缓存
        self._metadata_cache = {}
        self._initialize_metadata()

        # 统计信息
        self._calculation_count = 0
        self._total_calculation_time = 0.0
        self._error_count = 0

        if not TALIB_AVAILABLE:
            logger.warning("TA-Lib库不可用，TA-Lib指标插件将无法正常工作")

    @property
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        return self._plugin_info.copy()

    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        if not TALIB_AVAILABLE:
            return []

        return [
            # 趋势指标
            'SMA', 'EMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA', 'KAMA', 'MAMA', 'T3',
            'MACD', 'MACDEXT', 'MACDFIX', 'SAR', 'SAREXT',

            # 动量指标
            'RSI', 'STOCH', 'STOCHF', 'STOCHRSI', 'CCI', 'CMO', 'ROC', 'ROCP', 'ROCR', 'ROCR100',
            'ADX', 'ADXR', 'APO', 'AROON', 'AROONOSC', 'BOP', 'DX', 'MINUS_DI', 'PLUS_DI',
            'MFI', 'MINUS_DM', 'PLUS_DM', 'PPO', 'ULTOSC', 'WILLR',

            # 波动率指标
            'ATR', 'NATR', 'TRANGE', 'BBANDS',

            # 成交量指标
            'AD', 'ADOSC', 'OBV',

            # 价格指标
            'AVGPRICE', 'MEDPRICE', 'TYPPRICE', 'WCLPRICE',

            # 数学运算
            'ADD', 'DIV', 'MAX', 'MAXINDEX', 'MIN', 'MININDEX', 'MINMAX', 'MINMAXINDEX',
            'MULT', 'SUB', 'SUM',

            # 统计函数
            'BETA', 'CORREL', 'LINEARREG', 'LINEARREG_ANGLE', 'LINEARREG_INTERCEPT',
            'LINEARREG_SLOPE', 'STDDEV', 'TSF', 'VAR'
        ]

    def get_indicator_metadata(self, indicator_name: str) -> Optional[IndicatorMetadata]:
        """获取指标元数据"""
        return self._metadata_cache.get(indicator_name.upper())

    def calculate_indicator(self, indicator_name: str, kline_data: StandardKlineData,
                            params: Dict[str, Any], context: IndicatorCalculationContext) -> StandardIndicatorResult:
        """计算单个指标"""
        if not TALIB_AVAILABLE:
            raise RuntimeError("TA-Lib库不可用，无法计算指标")

        start_time = time.time()
        self._calculation_count += 1

        try:
            # 验证参数
            is_valid, error_msg = self.validate_parameters(indicator_name, params)
            if not is_valid:
                raise ValueError(f"参数验证失败: {error_msg}")

            # 准备输入数据
            high = kline_data.high.values.astype(np.float64)
            low = kline_data.low.values.astype(np.float64)
            close = kline_data.close.values.astype(np.float64)
            open_price = kline_data.open.values.astype(np.float64)
            volume = kline_data.volume.values.astype(np.float64)

            # 计算指标
            result_data = self._calculate_talib_indicator(
                indicator_name.upper(), high, low, close, open_price, volume, params
            )

            # 转换结果格式
            result_df = self._convert_result_to_dataframe(result_data, kline_data.datetime, indicator_name)

            calculation_time = (time.time() - start_time) * 1000
            self._total_calculation_time += calculation_time

            return StandardIndicatorResult(
                indicator_name=indicator_name,
                data=result_df,
                metadata={
                    'backend': 'TA-Lib',
                    'calculation_time_ms': calculation_time,
                    'symbol': context.symbol,
                    'timeframe': context.timeframe,
                    'parameters': params.copy(),
                    'data_points': len(result_df)
                }
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"TA-Lib指标计算失败 {indicator_name}: {e}")
            raise

    def _calculate_talib_indicator(self, indicator_name: str, high: np.ndarray, low: np.ndarray,
                                   close: np.ndarray, open_price: np.ndarray, volume: np.ndarray,
                                   params: Dict[str, Any]) -> Any:
        """使用TA-Lib计算指标"""
        try:
            # 趋势指标
            if indicator_name == 'SMA':
                timeperiod = params.get('timeperiod', 30)
                return talib.SMA(close, timeperiod=timeperiod)

            elif indicator_name == 'EMA':
                timeperiod = params.get('timeperiod', 30)
                return talib.EMA(close, timeperiod=timeperiod)

            elif indicator_name == 'MACD':
                fastperiod = params.get('fastperiod', 12)
                slowperiod = params.get('slowperiod', 26)
                signalperiod = params.get('signalperiod', 9)
                return talib.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)

            elif indicator_name == 'RSI':
                timeperiod = params.get('timeperiod', 14)
                return talib.RSI(close, timeperiod=timeperiod)

            elif indicator_name == 'BBANDS':
                timeperiod = params.get('timeperiod', 5)
                nbdevup = params.get('nbdevup', 2)
                nbdevdn = params.get('nbdevdn', 2)
                matype = params.get('matype', 0)
                return talib.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdevup,
                                    nbdevdn=nbdevdn, matype=matype)

            elif indicator_name == 'ATR':
                timeperiod = params.get('timeperiod', 14)
                return talib.ATR(high, low, close, timeperiod=timeperiod)

            elif indicator_name == 'OBV':
                return talib.OBV(close, volume)

            elif indicator_name == 'ADOSC':
                # ADOSC (Chaikin A/D Oscillator) 需要 high, low, close, volume
                fastperiod = params.get('fastperiod', 3)
                slowperiod = params.get('slowperiod', 10)
                return talib.ADOSC(high, low, close, volume, fastperiod=fastperiod, slowperiod=slowperiod)

            elif indicator_name == 'AD':
                # AD (Accumulation/Distribution) 需要 high, low, close, volume
                return talib.AD(high, low, close, volume)

            # 🔥 新增：方向性指标系列 - DX及相关指标
            elif indicator_name == 'DX':
                # DX (Directional Movement Index) 需要 high, low, close
                timeperiod = params.get('timeperiod', 14)
                return talib.DX(high, low, close, timeperiod=timeperiod)

            elif indicator_name == 'MINUS_DI':
                # -DI (Minus Directional Indicator) 需要 high, low, close
                timeperiod = params.get('timeperiod', 14)
                return talib.MINUS_DI(high, low, close, timeperiod=timeperiod)

            elif indicator_name == 'PLUS_DI':
                # +DI (Plus Directional Indicator) 需要 high, low, close
                timeperiod = params.get('timeperiod', 14)
                return talib.PLUS_DI(high, low, close, timeperiod=timeperiod)

            elif indicator_name == 'MINUS_DM':
                # -DM (Minus Directional Movement) 需要 high, low
                timeperiod = params.get('timeperiod', 14)
                return talib.MINUS_DM(high, low, timeperiod=timeperiod)

            elif indicator_name == 'PLUS_DM':
                # +DM (Plus Directional Movement) 需要 high, low
                timeperiod = params.get('timeperiod', 14)
                return talib.PLUS_DM(high, low, timeperiod=timeperiod)

            else:
                # 🔥 改进：使用统一的input_mapping来动态调用TA-Lib函数
                if hasattr(talib, indicator_name):
                    func = getattr(talib, indicator_name)

                    # 使用get_indicator_inputs获取正确的输入列表
                    from core.indicator_adapter import get_indicator_inputs
                    required_inputs = get_indicator_inputs(indicator_name)

                    # 准备输入参数（按顺序映射到OHLCV数据）
                    input_args = []
                    ohlcv_mapping = {
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'close': close,
                        'volume': volume
                    }

                    for input_name in required_inputs:
                        if input_name in ohlcv_mapping:
                            input_args.append(ohlcv_mapping[input_name])
                        else:
                            logger.warning(f"指标 {indicator_name} 需要的输入 '{input_name}' 未在OHLCV映射中找到，跳过")

                    # 如果没有匹配到任何输入参数，使用close作为默认值
                    if not input_args:
                        logger.warning(f"指标 {indicator_name} 没有匹配到输入参数，使用close作为默认值")
                        input_args = [close]

                    # 🔥 关键：使用inspect.signature动态提取配置参数
                    import inspect
                    sig = inspect.signature(func)
                    param_names = list(sig.parameters.keys())

                    # 过滤掉OHLCV输入参数，只保留配置参数
                    config_params = {}
                    for param_name in param_names:
                        # 跳过OHLCV数据参数
                        if param_name.lower() in ['open', 'high', 'low', 'close', 'volume',
                                                    'real', 'inreal', 'real0', 'real1', 'price', 'prices']:
                            continue
                        # 如果params中提供了这个配置参数，使用它
                        if param_name in params:
                            config_params[param_name] = params[param_name]

                    logger.debug(f"动态调用TA-Lib指标 {indicator_name}，输入参数: {required_inputs}, 配置参数: {config_params}")
                    return func(*input_args, **config_params)
                else:
                    raise ValueError(f"不支持的TA-Lib指标: {indicator_name}")

        except Exception as e:
            logger.error(f"TA-Lib指标计算错误 {indicator_name}: {e}")
            raise

    def _convert_result_to_dataframe(self, result_data: Any, datetime_index: pd.Series, indicator_name: str) -> pd.DataFrame:
        """将TA-Lib指标结果转换为DataFrame"""
        try:
            if isinstance(result_data, tuple):
                # 多输出结果（如MACD, BBANDS等）
                if indicator_name.upper() == 'MACD':
                    df = pd.DataFrame({
                        'macd': result_data[0],
                        'signal': result_data[1],
                        'histogram': result_data[2]
                    }, index=datetime_index)
                elif indicator_name.upper() == 'BBANDS':
                    df = pd.DataFrame({
                        'upper': result_data[0],
                        'middle': result_data[1],
                        'lower': result_data[2]
                    }, index=datetime_index)
                else:
                    # 通用多输出处理
                    columns = [f'output_{i}' for i in range(len(result_data))]
                    data_dict = {col: values for col, values in zip(columns, result_data)}
                    df = pd.DataFrame(data_dict, index=datetime_index)

            elif isinstance(result_data, np.ndarray):
                # 单输出结果
                df = pd.DataFrame({'value': result_data}, index=datetime_index)

            else:
                # 其他类型
                df = pd.DataFrame({'value': result_data}, index=datetime_index)

            # 处理NaN值
            df = df.replace([np.inf, -np.inf], np.nan)

            return df

        except Exception as e:
            logger.error(f"转换TA-Lib结果到DataFrame失败: {e}")
            # 返回空DataFrame
            return pd.DataFrame(index=datetime_index)

    def _initialize_metadata(self):
        """初始化指标元数据"""
        # 趋势指标
        self._metadata_cache['SMA'] = IndicatorMetadata(
            name='SMA',
            display_name='简单移动平均线',
            description='简单移动平均线，计算指定周期内的平均价格',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('timeperiod', ParameterType.INTEGER, 30, '时间周期', 2, 100000)
            ],
            output_columns=['value'],
            tags=['trend', 'moving_average', 'basic'],
            source='TA-Lib'
        )

        self._metadata_cache['RSI'] = IndicatorMetadata(
            name='RSI',
            display_name='相对强弱指数',
            description='RSI指标，衡量价格变动的速度和变化，识别超买超卖',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('timeperiod', ParameterType.INTEGER, 14, '时间周期', 2, 100000)
            ],
            output_columns=['value'],
            tags=['momentum', 'oscillator', 'overbought_oversold'],
            source='TA-Lib'
        )

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
            'talib_available': TALIB_AVAILABLE
        }
