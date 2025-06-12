"""
形态识别基础框架
定义统一的形态识别接口和抽象基类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


class PatternCategory(Enum):
    """形态类别枚举"""
    SINGLE_CANDLE = "单根K线"
    DOUBLE_CANDLE = "双根K线"
    TRIPLE_CANDLE = "三根K线"
    REVERSAL = "反转形态"
    CONTINUATION = "整理形态"
    COMPLEX = "复合形态"


@dataclass
class PatternResult:
    """形态识别结果"""
    pattern_type: str
    pattern_name: str
    pattern_category: str
    signal_type: SignalType
    confidence: float
    confidence_level: str
    index: int
    datetime_val: Optional[str]
    price: float
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'type': self.pattern_type,
            'pattern_name': self.pattern_name,
            'pattern_category': self.pattern_category,
            'signal': self.signal_type.value,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level,
            'index': self.index,
            'datetime': self.datetime_val,
            'price': self.price,
            'start_index': self.start_index,
            'end_index': self.end_index,
            **(self.extra_data or {})
        }


@dataclass
class PatternConfig:
    """形态配置"""
    id: int
    name: str
    english_name: str
    category: PatternCategory
    signal_type: SignalType
    description: str
    min_periods: int
    max_periods: int
    confidence_threshold: float
    algorithm_code: str
    parameters: Dict[str, Any]
    is_active: bool


class BasePatternRecognizer(ABC):
    """形态识别器基类"""

    def __init__(self, config: PatternConfig):
        self.config = config
        self.parameters = config.parameters

    @abstractmethod
    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """
        识别形态

        Args:
            kdata: K线数据DataFrame

        Returns:
            识别结果列表
        """
        pass

    def validate_data(self, kdata: pd.DataFrame) -> bool:
        """
        验证数据有效性

        Args:
            kdata: K线数据

        Returns:
            是否有效
        """
        if kdata is None or len(kdata) == 0:
            return False

        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in kdata.columns for col in required_columns):
            return False

        if len(kdata) < self.config.min_periods:
            return False

        return True

    def calculate_confidence_level(self, confidence: float) -> str:
        """计算置信度等级"""
        if confidence >= 0.8:
            return '高'
        elif confidence >= 0.5:
            return '中'
        else:
            return '低'

    def create_result(self, pattern_type: str, signal_type: SignalType,
                      confidence: float, index: int, price: float,
                      datetime_val: Optional[str] = None,
                      start_index: Optional[int] = None,
                      end_index: Optional[int] = None,
                      extra_data: Optional[Dict[str, Any]] = None) -> PatternResult:
        """创建识别结果"""
        return PatternResult(
            pattern_type=pattern_type,
            pattern_name=self.config.name,
            pattern_category=self.config.category.value,
            signal_type=signal_type,
            confidence=confidence,
            confidence_level=self.calculate_confidence_level(confidence),
            index=index,
            datetime_val=datetime_val,
            price=price,
            start_index=start_index,
            end_index=end_index,
            extra_data=extra_data
        )


class PatternAlgorithmFactory:
    """形态算法工厂"""

    _algorithms = {}

    @classmethod
    def register(cls, pattern_type: str, algorithm_class):
        """注册算法"""
        cls._algorithms[pattern_type] = algorithm_class

    @classmethod
    def create(cls, config: PatternConfig) -> BasePatternRecognizer:
        """创建算法实例"""
        algorithm_class = cls._algorithms.get(config.english_name)
        if algorithm_class is None:
            # 如果没有专门的算法类，使用通用算法
            algorithm_class = GenericPatternRecognizer

        return algorithm_class(config)

    @classmethod
    def get_available_algorithms(cls) -> List[str]:
        """获取可用算法列表"""
        return list(cls._algorithms.keys())


class GenericPatternRecognizer(BasePatternRecognizer):
    """通用形态识别器，基于数据库存储的算法代码 - 修复版本"""

    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """执行通用形态识别 - 使用增强的执行环境"""
        if not self.validate_data(kdata):
            return []

        try:
            # 执行存储在数据库中的算法代码
            algorithm_code = self.config.algorithm_code
            if not algorithm_code:
                return []

            # 清理算法代码 - 移除开头的空行和多余的空白
            algorithm_code = algorithm_code.strip()
            if not algorithm_code:
                return []

            # 创建增强的安全执行环境
            safe_globals = self._create_enhanced_safe_globals()
            safe_locals = self._create_enhanced_safe_locals(kdata)

            # 调试信息：确认kdata在执行环境中
            if 'kdata' not in safe_locals:
                print(f"[GenericPatternRecognizer] 警告: kdata未在safe_locals中找到")
                safe_locals['kdata'] = kdata

            # 验证kdata的有效性
            if safe_locals['kdata'] is None or len(safe_locals['kdata']) == 0:
                print(f"[GenericPatternRecognizer] 警告: kdata为空或无效")
                return []

            # 额外保险：将kdata也放入globals中，确保算法代码能访问到
            safe_globals['kdata'] = kdata

            # 执行算法代码
            exec(algorithm_code, safe_globals, safe_locals)

            # 获取结果并转换格式
            raw_results = safe_locals.get('results', [])
            return self._convert_raw_results(raw_results)

        except NameError as e:
            print(f"[GenericPatternRecognizer] 变量未定义错误 {self.config.english_name}: {e}")
            print(f"[GenericPatternRecognizer] 可用变量: {list(safe_locals.keys()) if 'safe_locals' in locals() else '未知'}")
            # 尝试修复：重新创建执行环境并强制设置kdata
            try:
                safe_globals = self._create_enhanced_safe_globals()
                safe_locals = self._create_enhanced_safe_locals(kdata)

                # 强制确保kdata在两个作用域中都存在
                safe_locals['kdata'] = kdata
                safe_globals['kdata'] = kdata

                print(f"[GenericPatternRecognizer] 重试执行，kdata类型: {type(kdata)}, 长度: {len(kdata)}")

                exec(algorithm_code, safe_globals, safe_locals)
                raw_results = safe_locals.get('results', [])
                return self._convert_raw_results(raw_results)
            except Exception as retry_e:
                print(f"[GenericPatternRecognizer] 重试执行也失败: {retry_e}")
                # 最后的调试信息
                print(f"[GenericPatternRecognizer] 算法代码前50字符: {repr(algorithm_code[:50])}")
                return []
        except Exception as e:
            print(f"[GenericPatternRecognizer] 执行形态算法失败 {self.config.english_name}: {e}")
            if hasattr(e, 'lineno'):
                print(f"[GenericPatternRecognizer] 错误位置: 第{e.lineno}行")
            # 调试信息
            if hasattr(e, 'text') and e.text:
                print(f"[GenericPatternRecognizer] 错误文本: {repr(e.text)}")
            return []

    def _create_enhanced_safe_globals(self) -> Dict[str, Any]:
        """创建增强的安全执行环境"""
        return {
            # 基础Python函数
            'len': len,
            'abs': abs,
            'max': max,
            'min': min,
            'sum': sum,
            'range': range,
            'enumerate': enumerate,
            'str': str,
            'float': float,
            'int': int,
            'bool': bool,

            # 数学和数据处理
            'np': np,
            'pd': pd,

            # 形态识别相关类型
            'SignalType': SignalType,
            'PatternResult': PatternResult,
            'PatternCategory': PatternCategory,

            # 工具函数
            'calculate_body_ratio': calculate_body_ratio,
            'calculate_shadow_ratios': calculate_shadow_ratios,
            'is_bullish_candle': is_bullish_candle,
            'is_bearish_candle': is_bearish_candle,
        }

    def _create_enhanced_safe_locals(self, kdata: pd.DataFrame) -> Dict[str, Any]:
        """创建增强的本地执行环境"""
        # 确保kdata不为None且有效
        if kdata is None:
            raise ValueError("kdata不能为None")

        locals_dict = {
            'kdata': kdata,
            'config': self.config,
            'parameters': self.parameters,
            'results': [],
            'create_result': self._create_enhanced_result_function(),
        }

        # 调试信息：确认kdata已正确设置
        if 'kdata' not in locals_dict or locals_dict['kdata'] is None:
            print(f"[GenericPatternRecognizer] 错误: kdata未正确设置到locals_dict中")

        return locals_dict

    def _create_enhanced_result_function(self):
        """创建增强的结果创建函数"""
        def create_result(pattern_type: str, signal_type, confidence: float,
                          index: int, price: float, datetime_val: str = None,
                          start_index: int = None, end_index: int = None,
                          extra_data: Dict = None):
            """创建形态识别结果"""
            return {
                'pattern_type': pattern_type,
                'signal_type': signal_type,
                'confidence': confidence,
                'index': index,
                'price': price,
                'datetime_val': datetime_val,
                'start_index': start_index,
                'end_index': end_index,
                'extra_data': extra_data or {}
            }
        return create_result

    def _convert_raw_results(self, raw_results: List[Dict]) -> List[PatternResult]:
        """转换原始结果为PatternResult对象"""
        converted_results = []

        for raw_result in raw_results:
            try:
                # 确保signal_type是SignalType枚举
                signal_type = raw_result.get('signal_type')
                if isinstance(signal_type, str):
                    signal_type = SignalType(signal_type)
                elif not isinstance(signal_type, SignalType):
                    signal_type = SignalType.NEUTRAL

                result = PatternResult(
                    pattern_type=raw_result.get('pattern_type', self.config.english_name),
                    pattern_name=self.config.name,
                    pattern_category=self.config.category.value,
                    signal_type=signal_type,
                    confidence=raw_result.get('confidence', 0.5),
                    confidence_level=self.calculate_confidence_level(raw_result.get('confidence', 0.5)),
                    index=raw_result.get('index', 0),
                    datetime_val=raw_result.get('datetime_val'),
                    price=raw_result.get('price', 0.0),
                    extra_data=raw_result.get('extra_data')
                )
                converted_results.append(result)

            except Exception as e:
                print(f"[GenericPatternRecognizer] 结果转换失败: {e}")
                continue

        return converted_results


def register_pattern_algorithm(pattern_type: str):
    """装饰器：注册形态算法"""
    def decorator(cls):
        PatternAlgorithmFactory.register(pattern_type, cls)
        return cls
    return decorator


# 工具函数
def calculate_body_ratio(open_price: float, close_price: float, high_price: float, low_price: float) -> float:
    """计算实体比例"""
    body_size = abs(close_price - open_price)
    total_range = high_price - low_price
    return body_size / total_range if total_range > 0 else 0


def calculate_shadow_ratios(open_price: float, close_price: float, high_price: float, low_price: float) -> Tuple[float, float]:
    """计算上下影线比例"""
    total_range = high_price - low_price
    if total_range == 0:
        return 0, 0

    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price

    upper_ratio = upper_shadow / total_range
    lower_ratio = lower_shadow / total_range

    return upper_ratio, lower_ratio


def is_bullish_candle(open_price: float, close_price: float) -> bool:
    """判断是否为阳线"""
    return close_price > open_price


def is_bearish_candle(open_price: float, close_price: float) -> bool:
    """判断是否为阴线"""
    return close_price < open_price


def find_local_extremes(prices: np.ndarray, window: int = 5) -> Tuple[List[int], List[int]]:
    """寻找局部极值点"""
    peaks = []
    troughs = []

    for i in range(window, len(prices) - window):
        # 寻找峰值
        if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] >= prices[i+j] for j in range(1, window+1)):
            peaks.append(i)

        # 寻找谷值
        if all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] <= prices[i+j] for j in range(1, window+1)):
            troughs.append(i)

    return peaks, troughs


def calculate_trend_strength(prices: np.ndarray, window: int = 20) -> float:
    """计算趋势强度"""
    if len(prices) < window:
        return 0

    recent_prices = prices[-window:]
    slope = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

    # 标准化斜率
    price_range = np.max(recent_prices) - np.min(recent_prices)
    if price_range == 0:
        return 0

    return slope / price_range
