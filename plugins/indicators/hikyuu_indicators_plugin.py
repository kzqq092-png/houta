from loguru import logger
"""
HIkyuu指标插件

基于HIkyuu框架的高性能指标计算插件，提供完整的技术指标支持。
HIkyuu是专业的量化分析框架，具有优秀的性能和丰富的指标库。
"""

import pandas as pd
import numpy as np
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    import hikyuu as hku
    HIKYUU_AVAILABLE = True
except ImportError:
    HIKYUU_AVAILABLE = False
    hku = None

from core.indicator_extensions import (
    IIndicatorPlugin, IndicatorMetadata, ParameterDef, ParameterType,
    IndicatorCategory, StandardKlineData, StandardIndicatorResult,
    IndicatorCalculationContext
)

logger = logger


class HikyuuIndicatorsPlugin(IIndicatorPlugin):
    """
    HIkyuu指标插件

    封装HIkyuu框架的指标计算能力，提供高性能的技术指标计算。
    支持趋势、动量、波动率、成交量等各类技术指标。
    """

    def __init__(self):
        self._plugin_info = {
            "id": "hikyuu_indicators",
            "name": "HIkyuu指标插件",
            "version": "1.0.0",
            "description": "基于HIkyuu框架的高性能技术指标计算插件",
            "author": "HIkyuu-UI Team",
            "backend": "HIkyuu C++",
            "performance_level": "high"
        }

        # 指标元数据缓存
        self._metadata_cache = {}
        self._initialize_metadata()

        # 统计信息
        self._calculation_count = 0
        self._total_calculation_time = 0.0
        self._error_count = 0

        if not HIKYUU_AVAILABLE:
            logger.warning("HIkyuu库不可用，HIkyuu指标插件将无法正常工作")

    @property
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        return self._plugin_info.copy()

    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        if not HIKYUU_AVAILABLE:
            return []

        return [
            # 趋势指标
            'MA', 'EMA', 'SMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA',
            'MACD', 'BOLL', 'SAR', 'KAMA', 'MAMA',

            # 动量指标
            'RSI', 'KDJ', 'CCI', 'WR', 'ROC', 'MOMENTUM',
            'ADX', 'ADXR', 'DX', 'MINUS_DI', 'PLUS_DI',
            'AROON', 'AROONOSC', 'BOP', 'CMO',

            # 波动率指标
            'ATR', 'NATR', 'TRANGE', 'STDDEV', 'VAR',

            # 成交量指标
            'OBV', 'AD', 'ADOSC', 'CMF', 'VWAP', 'PVT',

            # 价格指标
            'MEDPRICE', 'TYPPRICE', 'WCLPRICE',

            # 数学函数
            'MAX', 'MIN', 'SUM', 'ABS', 'SQRT',

            # 自定义HIkyuu指标
            'HSL', 'VIGOR', 'COPPOCK'
        ]

    def get_indicator_metadata(self, indicator_name: str) -> Optional[IndicatorMetadata]:
        """获取指标元数据"""
        return self._metadata_cache.get(indicator_name.upper())

    def calculate_indicator(self, indicator_name: str, kline_data: StandardKlineData,
                            params: Dict[str, Any], context: IndicatorCalculationContext) -> StandardIndicatorResult:
        """计算单个指标"""
        if not HIKYUU_AVAILABLE:
            raise RuntimeError("HIkyuu库不可用，无法计算指标")

        start_time = time.time()
        self._calculation_count += 1

        try:
            # 验证参数
            is_valid, error_msg = self.validate_parameters(indicator_name, params)
            if not is_valid:
                raise ValueError(f"参数验证失败: {error_msg}")

            # 转换数据格式
            hku_kdata = self._convert_to_hikyuu_kdata(kline_data, context.symbol)

            # 计算指标
            result_data = self._calculate_hikyuu_indicator(indicator_name.upper(), hku_kdata, params)

            # 转换结果格式
            result_df = self._convert_result_to_dataframe(result_data, kline_data.datetime)

            calculation_time = (time.time() - start_time) * 1000
            self._total_calculation_time += calculation_time

            return StandardIndicatorResult(
                indicator_name=indicator_name,
                data=result_df,
                metadata={
                    'backend': 'HIkyuu',
                    'calculation_time_ms': calculation_time,
                    'symbol': context.symbol,
                    'timeframe': context.timeframe,
                    'parameters': params.copy(),
                    'data_points': len(result_df)
                }
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"HIkyuu指标计算失败 {indicator_name}: {e}")
            raise

    def batch_calculate_indicators(self, indicators: List[Tuple[str, Dict[str, Any]]],
                                   kline_data: StandardKlineData,
                                   context: IndicatorCalculationContext) -> Dict[str, StandardIndicatorResult]:
        """批量计算指标（HIkyuu优化版本）"""
        if not HIKYUU_AVAILABLE:
            raise RuntimeError("HIkyuu库不可用，无法计算指标")

        start_time = time.time()
        results = {}

        try:
            # 转换数据格式（只需要转换一次）
            hku_kdata = self._convert_to_hikyuu_kdata(kline_data, context.symbol)

            # 批量计算指标
            for indicator_name, params in indicators:
                try:
                    # 验证参数
                    is_valid, error_msg = self.validate_parameters(indicator_name, params)
                    if not is_valid:
                        logger.warning(f"跳过指标 {indicator_name}: {error_msg}")
                        continue

                    # 计算指标
                    result_data = self._calculate_hikyuu_indicator(indicator_name.upper(), hku_kdata, params)
                    result_df = self._convert_result_to_dataframe(result_data, kline_data.datetime)

                    results[indicator_name] = StandardIndicatorResult(
                        indicator_name=indicator_name,
                        data=result_df,
                        metadata={
                            'backend': 'HIkyuu',
                            'symbol': context.symbol,
                            'timeframe': context.timeframe,
                            'parameters': params.copy(),
                            'data_points': len(result_df)
                        }
                    )

                except Exception as e:
                    logger.warning(f"批量计算中跳过指标 {indicator_name}: {e}")
                    continue

            total_time = (time.time() - start_time) * 1000
            self._calculation_count += len(results)
            self._total_calculation_time += total_time

            # 添加批量计算的元数据
            for result in results.values():
                result.metadata['batch_calculation'] = True
                result.metadata['batch_total_time_ms'] = total_time
                result.metadata['batch_indicator_count'] = len(results)

            return results

        except Exception as e:
            self._error_count += 1
            logger.error(f"HIkyuu批量指标计算失败: {e}")
            raise

    def _convert_to_hikyuu_kdata(self, kline_data: StandardKlineData, symbol: str) -> 'hku.KData':
        """将标准K线数据转换为HIkyuu KData格式"""
        try:
            # 创建HIkyuu Stock对象（如果需要的话）
            # 这里简化处理，直接使用数据创建KData

            # 将pandas数据转换为HIkyuu格式
            # 注意：这里需要根据实际HIkyuu API调整
            kdata_list = []

            for i in range(len(kline_data.datetime)):
                # 创建HIkyuu KRecord
                record = hku.KRecord()
                record.datetime = hku.Datetime(kline_data.datetime.iloc[i])
                record.open = float(kline_data.open.iloc[i])
                record.high = float(kline_data.high.iloc[i])
                record.low = float(kline_data.low.iloc[i])
                record.close = float(kline_data.close.iloc[i])
                record.volume = float(kline_data.volume.iloc[i])
                if kline_data.amount is not None:
                    record.amount = float(kline_data.amount.iloc[i])

                kdata_list.append(record)

            # 创建KData对象
            kdata = hku.KData(kdata_list)
            return kdata

        except Exception as e:
            logger.error(f"转换K线数据到HIkyuu格式失败: {e}")
            # 如果转换失败，尝试其他方式或抛出异常
            raise ValueError(f"无法转换K线数据到HIkyuu格式: {e}")

    def _calculate_hikyuu_indicator(self, indicator_name: str, kdata: 'hku.KData', params: Dict[str, Any]) -> Any:
        """使用HIkyuu计算指标"""
        try:
            # 根据指标名称调用相应的HIkyuu指标函数
            if indicator_name == 'MA':
                period = params.get('period', 20)
                return hku.MA(kdata, period)

            elif indicator_name == 'EMA':
                period = params.get('period', 12)
                return hku.EMA(kdata, period)

            elif indicator_name == 'SMA':
                period = params.get('period', 20)
                return hku.SMA(kdata, period)

            elif indicator_name == 'MACD':
                fast_period = params.get('fast_period', 12)
                slow_period = params.get('slow_period', 26)
                signal_period = params.get('signal_period', 9)
                return hku.MACD(kdata, fast_period, slow_period, signal_period)

            elif indicator_name == 'RSI':
                period = params.get('period', 14)
                return hku.RSI(kdata, period)

            elif indicator_name == 'KDJ':
                k_period = params.get('k_period', 9)
                k_slowing = params.get('k_slowing', 3)
                d_period = params.get('d_period', 3)
                return hku.KDJ(kdata, k_period, k_slowing, d_period)

            elif indicator_name == 'BOLL':
                period = params.get('period', 20)
                std_dev = params.get('std_dev', 2.0)
                return hku.BOLL(kdata, period, std_dev)

            elif indicator_name == 'ATR':
                period = params.get('period', 14)
                return hku.ATR(kdata, period)

            elif indicator_name == 'OBV':
                return hku.OBV(kdata)

            elif indicator_name == 'CCI':
                period = params.get('period', 14)
                return hku.CCI(kdata, period)

            elif indicator_name == 'WR':
                period = params.get('period', 14)
                return hku.WR(kdata, period)

            elif indicator_name == 'ROC':
                period = params.get('period', 10)
                return hku.ROC(kdata, period)

            elif indicator_name == 'STDDEV':
                period = params.get('period', 20)
                return hku.STDDEV(kdata, period)

            elif indicator_name == 'MAX':
                period = params.get('period', 20)
                return hku.HHV(kdata, period)  # HIkyuu中可能叫HHV

            elif indicator_name == 'MIN':
                period = params.get('period', 20)
                return hku.LLV(kdata, period)  # HIkyuu中可能叫LLV

            else:
                # 尝试动态调用HIkyuu指标函数
                if hasattr(hku, indicator_name):
                    indicator_func = getattr(hku, indicator_name)
                    # 根据参数数量调用
                    if len(params) == 0:
                        return indicator_func(kdata)
                    elif len(params) == 1:
                        return indicator_func(kdata, list(params.values())[0])
                    else:
                        # 更复杂的参数处理
                        return indicator_func(kdata, **params)
                else:
                    raise ValueError(f"不支持的HIkyuu指标: {indicator_name}")

        except Exception as e:
            logger.error(f"HIkyuu指标计算错误 {indicator_name}: {e}")
            raise

    def _convert_result_to_dataframe(self, result_data: Any, datetime_index: pd.Series) -> pd.DataFrame:
        """将HIkyuu指标结果转换为DataFrame"""
        try:
            if hasattr(result_data, '__len__') and len(result_data) > 0:
                # 处理单列结果
                if hasattr(result_data, '__getitem__'):
                    values = [float(result_data[i]) if not np.isnan(result_data[i]) else np.nan
                              for i in range(len(result_data))]
                    df = pd.DataFrame({'value': values}, index=datetime_index[:len(values)])
                    return df

                # 处理多列结果（如MACD, KDJ, BOLL等）
                elif hasattr(result_data, 'keys') or isinstance(result_data, dict):
                    data_dict = {}
                    for key, values in result_data.items():
                        data_dict[key] = [float(values[i]) if not np.isnan(values[i]) else np.nan
                                          for i in range(len(values))]
                    df = pd.DataFrame(data_dict, index=datetime_index[:len(list(data_dict.values())[0])])
                    return df

                else:
                    # 默认处理
                    values = [float(x) if not np.isnan(x) else np.nan for x in result_data]
                    df = pd.DataFrame({'value': values}, index=datetime_index[:len(values)])
                    return df

            else:
                # 空结果
                return pd.DataFrame(index=datetime_index)

        except Exception as e:
            logger.error(f"转换HIkyuu结果到DataFrame失败: {e}")
            # 返回空DataFrame
            return pd.DataFrame(index=datetime_index)

    def _initialize_metadata(self):
        """初始化指标元数据"""
        # 趋势指标
        self._metadata_cache['MA'] = IndicatorMetadata(
            name='MA',
            display_name='移动平均线',
            description='简单移动平均线，平滑价格波动，识别趋势方向',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 20, '周期', 1, 200)
            ],
            output_columns=['value'],
            tags=['trend', 'moving_average', 'basic'],
            author='HIkyuu'
        )

        self._metadata_cache['EMA'] = IndicatorMetadata(
            name='EMA',
            display_name='指数移动平均线',
            description='指数移动平均线，对近期价格赋予更高权重',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 12, '周期', 1, 200)
            ],
            output_columns=['value'],
            tags=['trend', 'exponential', 'moving_average'],
            author='HIkyuu'
        )

        self._metadata_cache['MACD'] = IndicatorMetadata(
            name='MACD',
            display_name='指数平滑移动平均线',
            description='MACD指标，用于判断趋势变化和买卖信号',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('fast_period', ParameterType.INTEGER, 12, '快线周期', 1, 50),
                ParameterDef('slow_period', ParameterType.INTEGER, 26, '慢线周期', 1, 100),
                ParameterDef('signal_period', ParameterType.INTEGER, 9, '信号线周期', 1, 50)
            ],
            output_columns=['macd', 'signal', 'histogram'],
            tags=['momentum', 'oscillator', 'classic'],
            author='HIkyuu'
        )

        self._metadata_cache['RSI'] = IndicatorMetadata(
            name='RSI',
            display_name='相对强弱指数',
            description='RSI指标，衡量价格变动的速度和变化，识别超买超卖',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 14, '周期', 1, 50)
            ],
            output_columns=['value'],
            tags=['momentum', 'oscillator', 'overbought_oversold'],
            author='HIkyuu'
        )

        self._metadata_cache['KDJ'] = IndicatorMetadata(
            name='KDJ',
            display_name='随机指标',
            description='KDJ指标，基于随机理论的超买超卖指标',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('k_period', ParameterType.INTEGER, 9, 'K值周期', 1, 50),
                ParameterDef('k_slowing', ParameterType.INTEGER, 3, 'K值平滑', 1, 10),
                ParameterDef('d_period', ParameterType.INTEGER, 3, 'D值周期', 1, 10)
            ],
            output_columns=['k', 'd', 'j'],
            tags=['momentum', 'stochastic', 'overbought_oversold'],
            author='HIkyuu'
        )

        self._metadata_cache['BOLL'] = IndicatorMetadata(
            name='BOLL',
            display_name='布林带',
            description='布林带指标，基于标准差的价格通道指标',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 20, '周期', 1, 100),
                ParameterDef('std_dev', ParameterType.FLOAT, 2.0, '标准差倍数', 0.1, 5.0)
            ],
            output_columns=['upper', 'middle', 'lower'],
            tags=['volatility', 'bands', 'channel'],
            author='HIkyuu'
        )

        self._metadata_cache['ATR'] = IndicatorMetadata(
            name='ATR',
            display_name='平均真实波幅',
            description='ATR指标，衡量价格波动的强度',
            category=IndicatorCategory.VOLATILITY,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 14, '周期', 1, 100)
            ],
            output_columns=['value'],
            tags=['volatility', 'range', 'risk'],
            author='HIkyuu'
        )

        self._metadata_cache['OBV'] = IndicatorMetadata(
            name='OBV',
            display_name='能量潮',
            description='OBV指标，通过成交量变化衡量买卖力道',
            category=IndicatorCategory.VOLUME,
            parameters=[],
            output_columns=['value'],
            tags=['volume', 'accumulation', 'distribution'],
            author='HIkyuu'
        )

        # 添加更多指标元数据...
        # 这里可以继续添加其他指标的元数据定义

    def validate_parameters(self, indicator_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """验证指标参数是否有效"""
        metadata = self.get_indicator_metadata(indicator_name)
        if not metadata:
            return False, f"Indicator '{indicator_name}' not found."

        for param_def in metadata.parameters:
            param_name = param_def.name
            if param_name not in params:
                # 检查是否有默认值，如果没有则认为缺失
                if param_def.default_value is None and param_def.type != ParameterType.BOOLEAN:
                    return False, f"Missing required parameter: {param_name}"
                continue

            value = params[param_name]

            # 类型检查
            if param_def.type == ParameterType.INTEGER:
                if not isinstance(value, int):
                    return False, f"Parameter '{param_name}' must be an integer."
            elif param_def.type == ParameterType.FLOAT:
                if not isinstance(value, (int, float)):
                    return False, f"Parameter '{param_name}' must be a float."
            elif param_def.type == ParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    return False, f"Parameter '{param_name}' must be a boolean."
            elif param_def.type == ParameterType.STRING:
                if not isinstance(value, str):
                    return False, f"Parameter '{param_name}' must be a string."
            elif param_def.type == ParameterType.ENUM:
                if hasattr(param_def, 'options') and param_def.options and value not in param_def.options:
                    return False, f"Parameter '{param_name}' must be one of {param_def.options}."

            # 范围检查
            if param_def.min_value is not None and value < param_def.min_value:
                return False, f"Parameter '{param_name}' must be >= {param_def.min_value}."
            if param_def.max_value is not None and value > param_def.max_value:
                return False, f"Parameter '{param_name}' must be <= {param_def.max_value}."
        return True, ""

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
            'hikyuu_available': HIKYUU_AVAILABLE
        }
