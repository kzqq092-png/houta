"""
统一指标计算服务
整合所有指标计算逻辑，提供统一的接口和标准化的参数处理
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from utils.cache import Cache
from .engines.indicator_engine import IndicatorEngine


@dataclass
class IndicatorRequest:
    """标准化的指标请求"""
    indicator_name: str
    data: Union[pd.DataFrame, Dict[str, pd.Series]]
    parameters: Dict[str, Any] = field(default_factory=dict)
    cache_key: Optional[str] = None


@dataclass
class IndicatorResponse:
    """标准化的指标响应"""
    indicator_name: str
    result: Union[pd.Series, pd.DataFrame, Dict[str, pd.Series]]
    parameters: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None
    computation_time: float = 0.0
    cache_hit: bool = False


class IndicatorCategory(Enum):
    """指标分类"""
    TREND = "trend"          # 趋势指标
    MOMENTUM = "momentum"    # 动量指标
    VOLATILITY = "volatility"  # 波动率指标
    VOLUME = "volume"        # 成交量指标
    SUPPORT_RESISTANCE = "support_resistance"  # 支撑阻力指标
    OTHER = "other"          # 其他指标


@dataclass
class IndicatorInfo:
    """指标信息"""
    name: str
    chinese_name: str
    category: IndicatorCategory
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


class ParameterNormalizer:
    """参数标准化器"""

    # 参数名映射表
    PARAMETER_MAPPING = {
        'period': ['timeperiod', 'n', 'window'],
        'fast_period': ['fastperiod', 'n1', 'fast'],
        'slow_period': ['slowperiod', 'n2', 'slow'],
        'signal_period': ['signalperiod', 'n3', 'signal'],
        'std_dev': ['nbdevup', 'nbdevdn', 'width'],
        'k_period': ['fastk_period', 'k'],
        'd_period': ['slowk_period', 'd'],
        'j_period': ['slowd_period', 'j']
    }

    @classmethod
    def normalize_parameters(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化参数名称"""
        normalized = {}

        for standard_name, aliases in cls.PARAMETER_MAPPING.items():
            # 查找参数值
            value = None
            for alias in [standard_name] + aliases:
                if alias in params:
                    value = params[alias]
                    break

            if value is not None:
                normalized[standard_name] = value

        # 保留未映射的参数
        for key, value in params.items():
            if not any(key in aliases + [std_name] for std_name, aliases in cls.PARAMETER_MAPPING.items()):
                normalized[key] = value

        return normalized


class ResultFormatter:
    """结果格式化器"""

    @staticmethod
    def format_result(result: Any, indicator_name: str) -> Union[pd.Series, Dict[str, pd.Series]]:
        """标准化结果格式"""
        if result is None:
            return pd.Series(dtype=float)

        # MACD特殊处理
        if indicator_name.upper() == 'MACD':
            if isinstance(result, tuple) and len(result) == 3:
                return {
                    'macd': pd.Series(result[0]) if not isinstance(result[0], pd.Series) else result[0],
                    'signal': pd.Series(result[1]) if not isinstance(result[1], pd.Series) else result[1],
                    'histogram': pd.Series(result[2]) if not isinstance(result[2], pd.Series) else result[2]
                }
            elif isinstance(result, dict):
                return result

        # 布林带特殊处理
        elif indicator_name.upper() in ['BOLL', 'BBANDS']:
            if isinstance(result, tuple) and len(result) == 3:
                return {
                    'upper': pd.Series(result[0]) if not isinstance(result[0], pd.Series) else result[0],
                    'middle': pd.Series(result[1]) if not isinstance(result[1], pd.Series) else result[1],
                    'lower': pd.Series(result[2]) if not isinstance(result[2], pd.Series) else result[2]
                }
            elif isinstance(result, dict):
                return result

        # KDJ特殊处理
        elif indicator_name.upper() in ['KDJ', 'STOCH']:
            if isinstance(result, tuple) and len(result) >= 2:
                formatted = {
                    'k': pd.Series(result[0]) if not isinstance(result[0], pd.Series) else result[0],
                    'd': pd.Series(result[1]) if not isinstance(result[1], pd.Series) else result[1]
                }
                if len(result) > 2:
                    formatted['j'] = pd.Series(result[2]) if not isinstance(result[2], pd.Series) else result[2]
                return formatted
            elif isinstance(result, dict):
                return result

        # 默认处理
        if isinstance(result, (list, np.ndarray)):
            return pd.Series(result, dtype=float)
        elif isinstance(result, pd.Series):
            return result
        elif isinstance(result, dict):
            return result
        else:
            return pd.Series([result], dtype=float)


class IndicatorCalculationService:
    """统一指标计算服务"""

    def __init__(self, cache_manager: Optional[Cache] = None):
        self.logger = logging.getLogger(__name__)
        self.cache_manager = cache_manager or Cache()

        # 初始化计算引擎
        self.engines: List[IndicatorEngine] = []
        self._init_engines()

        # 参数标准化器和结果格式化器
        self.parameter_normalizer = ParameterNormalizer()
        self.result_formatter = ResultFormatter()

        # 初始化指标信息
        self.indicator_info_dict = self._init_indicator_info()

    def _init_engines(self):
        """初始化计算引擎（按照新架构，不使用UnifiedIndicatorEngine）"""
        try:
            # 添加TA-Lib引擎 (最高优先级)
            from .engines import TALibEngine
            self.engines.append(TALibEngine())
            self.logger.info("TA-Lib引擎已加载")

            # 添加Hikyuu引擎
            from .engines import HikyuuEngine
            self.engines.append(HikyuuEngine())
            self.logger.info("Hikyuu引擎已加载")

            # 添加备用引擎
            from .engines import FallbackEngine
            self.engines.append(FallbackEngine())
            self.logger.info("备用引擎已加载")

        except ImportError as e:
            self.logger.warning(f"部分引擎初始化失败: {e}")

    def _init_indicator_info(self) -> Dict[str, IndicatorInfo]:
        """初始化指标信息"""
        info_dict = {}

        # 趋势指标
        info_dict.update({
            'SMA': IndicatorInfo(
                name='SMA', chinese_name='简单移动平均', category=IndicatorCategory.TREND,
                description='简单移动平均线', inputs=['close'], outputs=['sma'],
                parameters={'period': 20}
            ),
            'EMA': IndicatorInfo(
                name='EMA', chinese_name='指数移动平均', category=IndicatorCategory.TREND,
                description='指数移动平均线', inputs=['close'], outputs=['ema'],
                parameters={'period': 20}
            ),
            'WMA': IndicatorInfo(
                name='WMA', chinese_name='加权移动平均', category=IndicatorCategory.TREND,
                description='加权移动平均线', inputs=['close'], outputs=['wma'],
                parameters={'period': 20}
            ),
            'BOLL': IndicatorInfo(
                name='BOLL', chinese_name='布林带', category=IndicatorCategory.TREND,
                description='布林带指标', inputs=['close'], outputs=['upper', 'middle', 'lower'],
                parameters={'period': 20, 'std_dev': 2}
            ),
        })

        # 动量指标
        info_dict.update({
            'MACD': IndicatorInfo(
                name='MACD', chinese_name='MACD', category=IndicatorCategory.MOMENTUM,
                description='指数平滑移动平均线', inputs=['close'], outputs=['macd', 'signal', 'histogram'],
                parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            ),
            'RSI': IndicatorInfo(
                name='RSI', chinese_name='相对强弱指标', category=IndicatorCategory.MOMENTUM,
                description='相对强弱指标', inputs=['close'], outputs=['rsi'],
                parameters={'period': 14}
            ),
            'KDJ': IndicatorInfo(
                name='KDJ', chinese_name='KDJ', category=IndicatorCategory.MOMENTUM,
                description='随机指标', inputs=['high', 'low', 'close'], outputs=['k', 'd', 'j'],
                parameters={'k_period': 9, 'd_period': 3, 'j_period': 3}
            ),
        })

        # 波动率指标
        info_dict.update({
            'ATR': IndicatorInfo(
                name='ATR', chinese_name='真实波动幅度', category=IndicatorCategory.VOLATILITY,
                description='平均真实波动幅度', inputs=['high', 'low', 'close'], outputs=['atr'],
                parameters={'period': 14}
            ),
        })

        # 成交量指标
        info_dict.update({
            'OBV': IndicatorInfo(
                name='OBV', chinese_name='能量潮', category=IndicatorCategory.VOLUME,
                description='能量潮指标', inputs=['close', 'volume'], outputs=['obv'],
                parameters={}
            ),
        })

        return info_dict

    def calculate_indicator(self,
                            indicator_name: str,
                            data: Union[pd.DataFrame, Dict[str, pd.Series]],
                            **parameters) -> IndicatorResponse:
        """统一指标计算入口"""
        import time
        start_time = time.time()

        try:
            # 创建请求对象
            request = IndicatorRequest(
                indicator_name=indicator_name,
                data=data,
                parameters=self.parameter_normalizer.normalize_parameters(parameters)
            )

            # 生成缓存键
            cache_key = self._generate_cache_key(request)

            # 检查缓存
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                self.logger.debug(f"缓存命中: {indicator_name}")
                return IndicatorResponse(
                    indicator_name=indicator_name,
                    result=cached_result,
                    parameters=request.parameters,
                    success=True,
                    computation_time=time.time() - start_time,
                    cache_hit=True
                )

            # 尝试使用各个引擎计算
            for engine in self.engines:
                if engine.is_available and engine.supports_indicator(indicator_name):
                    try:
                        result = engine.calculate(indicator_name, data, **request.parameters)

                        # 格式化结果
                        formatted_result = self.result_formatter.format_result(result, indicator_name)

                        # 缓存结果
                        self.cache_manager.set(cache_key, formatted_result)

                        computation_time = time.time() - start_time
                        self.logger.debug(f"使用 {engine.name} 引擎计算 {indicator_name} 成功，耗时: {computation_time:.4f}s")

                        return IndicatorResponse(
                            indicator_name=indicator_name,
                            result=formatted_result,
                            parameters=request.parameters,
                            success=True,
                            computation_time=computation_time,
                            cache_hit=False
                        )
                    except Exception as e:
                        self.logger.warning(f"{engine.name} 引擎计算失败: {e}")
                        continue

            # 所有引擎都失败
            error_msg = f"所有引擎都无法计算指标: {indicator_name}"
            self.logger.error(error_msg)

            return IndicatorResponse(
                indicator_name=indicator_name,
                result=pd.Series(dtype=float),
                parameters=request.parameters,
                success=False,
                error_message=error_msg,
                computation_time=time.time() - start_time
            )

        except Exception as e:
            error_msg = f"指标计算服务异常: {e}"
            self.logger.error(error_msg)

            return IndicatorResponse(
                indicator_name=indicator_name,
                result=pd.Series(dtype=float),
                parameters=parameters,
                success=False,
                error_message=error_msg,
                computation_time=time.time() - start_time
            )

    def _generate_cache_key(self, request: IndicatorRequest) -> str:
        """生成缓存键"""
        import hashlib

        try:
            # 基于数据哈希、指标名称和参数生成键
            if isinstance(request.data, pd.DataFrame):
                data_hash = hashlib.md5(str(request.data.shape).encode()).hexdigest()[:8]
            else:
                data_hash = hashlib.md5(str(len(request.data)).encode()).hexdigest()[:8]

            params_str = str(sorted(request.parameters.items()))
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

            return f"indicator_{request.indicator_name}_{data_hash}_{params_hash}"
        except Exception:
            # 如果生成失败，返回简单键
            return f"indicator_{request.indicator_name}_{hash(str(request.parameters))}"

    def get_supported_indicators(self) -> List[str]:
        """获取所有支持的指标列表"""
        indicators = set()
        for engine in self.engines:
            if engine.is_available:
                indicators.update(engine.supported_indicators)
        return sorted(list(indicators))

    def get_indicator_info(self, indicator_name: str) -> Optional[IndicatorInfo]:
        """获取指标信息"""
        return self.indicator_info_dict.get(indicator_name.upper())

    def get_indicators_by_category(self, use_chinese: bool = False) -> Dict[str, List[str]]:
        """按分类获取指标"""
        categories = {}
        for indicator_name, info in self.indicator_info_dict.items():
            category_name = info.category.value
            if category_name not in categories:
                categories[category_name] = []

            name_to_add = info.chinese_name if use_chinese else info.name
            categories[category_name].append(name_to_add)

        return categories

    def get_indicator_list(self, use_chinese: bool = False) -> List[str]:
        """获取指标列表"""
        if use_chinese:
            return [info.chinese_name for info in self.indicator_info_dict.values()]
        else:
            return list(self.indicator_info_dict.keys())

    def get_chinese_name(self, english_name: str) -> Optional[str]:
        """获取指标中文名称"""
        info = self.get_indicator_info(english_name)
        return info.chinese_name if info else None

    def get_english_name(self, chinese_name: str) -> Optional[str]:
        """获取指标英文名称"""
        for info in self.indicator_info_dict.values():
            if info.chinese_name == chinese_name:
                return info.name
        return None

    def clear_cache(self):
        """清除缓存"""
        self.cache_manager.clear()
        self.logger.info("指标计算服务缓存已清除")


# 全局服务实例
_indicator_service = None


def get_indicator_service() -> IndicatorCalculationService:
    """获取全局指标计算服务实例"""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorCalculationService()
    return _indicator_service
