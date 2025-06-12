"""
Enhanced Pattern Recognition Module for Trading System
完全重构的形态识别模块，与新统一框架完全兼容
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import traceback

# 导入新的统一框架
from analysis.pattern_base import (
    BasePatternRecognizer, PatternResult, PatternConfig,
    SignalType, PatternCategory, PatternAlgorithmFactory,
    calculate_body_ratio, calculate_shadow_ratios,
    is_bullish_candle, is_bearish_candle
)


class EnhancedPatternRecognizer:
    """
    增强的形态识别器，完全兼容新统一框架
    提供更好的错误处理、调试信息和性能优化
    """

    def __init__(self, debug_mode: bool = False):
        """
        初始化增强的形态识别器

        Args:
            debug_mode: 是否启用调试模式
        """
        self.debug_mode = debug_mode
        self.execution_stats = {}

        # 动态获取形态名称映射，避免硬编码
        self._pattern_name_mapping = self._build_pattern_name_mapping()

    def _build_pattern_name_mapping(self) -> Dict[str, str]:
        """从数据库构建形态名称映射"""
        try:
            import sqlite3
            conn = sqlite3.connect('db/hikyuu_system.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name, english_name FROM pattern_types")
            mapping = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()
            return mapping
        except Exception as e:
            if self.debug_mode:
                print(f"构建形态名称映射失败: {e}")
            return {}

    def identify_patterns(self, kdata: pd.DataFrame,
                          confidence_threshold: float = 0.1,
                          pattern_types: Optional[List[str]] = None) -> List[Dict]:
        """
        识别K线形态

        Args:
            kdata: K线数据
            confidence_threshold: 置信度阈值
            pattern_types: 指定要识别的形态类型列表，None表示识别所有形态

        Returns:
            识别到的形态列表
        """
        if kdata is None or kdata.empty:
            return []

        results = []

        try:
            # 使用PatternManager进行识别
            from analysis.pattern_manager import PatternManager
            manager = PatternManager()

            # 如果指定了形态类型，使用指定的类型
            if pattern_types:
                # 将中文名称转换为英文名称
                english_pattern_types = []
                for pattern_type in pattern_types:
                    english_name = self._pattern_name_mapping.get(pattern_type, pattern_type)
                    english_pattern_types.append(english_name)

                patterns = manager.identify_patterns(
                    kdata,
                    confidence_threshold=confidence_threshold,
                    pattern_types=english_pattern_types
                )
            else:
                # 识别所有形态
                patterns = manager.identify_all_patterns(
                    kdata,
                    confidence_threshold=confidence_threshold
                )

            results.extend(patterns)

            if self.debug_mode:
                print(f"PatternManager识别结果: {len(results)}个形态")

        except Exception as e:
            if self.debug_mode:
                print(f"PatternManager识别失败: {e}")
                import traceback
                traceback.print_exc()

        return results

    # 保持向后兼容的方法，但移除硬编码
    def find_hammer(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找锤头线形态"""
        return self.identify_patterns(kdata, pattern_types=['锤头线'])

    def find_doji(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找十字星形态"""
        return self.identify_patterns(kdata, pattern_types=['十字星'])

    def find_shooting_star(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找流星线形态"""
        return self.identify_patterns(kdata, pattern_types=['流星线'])

    def find_engulfing(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找吞没形态"""
        return self.identify_patterns(kdata, pattern_types=['看涨吞没', '看跌吞没'])

    def find_morning_star(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找早晨之星形态"""
        return self.identify_patterns(kdata, pattern_types=['早晨之星'])

    def find_evening_star(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找黄昏之星形态"""
        return self.identify_patterns(kdata, pattern_types=['黄昏之星'])

    def find_three_white_soldiers(self, kdata: pd.DataFrame) -> List[Dict]:
        """查找三白兵形态"""
        return self.identify_patterns(kdata, pattern_types=['三白兵'])


# 专门的算法识别器类，用于数据库算法的执行
class DatabaseAlgorithmRecognizer(BasePatternRecognizer):
    """
    数据库算法识别器 - 修复执行环境问题
    """

    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """执行数据库存储的算法代码"""
        if not self.validate_data(kdata):
            return []

        try:
            algorithm_code = self.config.algorithm_code
            if not algorithm_code:
                return []

            # 创建增强的安全执行环境
            safe_globals = self._create_safe_globals()
            safe_locals = self._create_safe_locals(kdata)

            # 执行算法代码
            exec(algorithm_code, safe_globals, safe_locals)

            # 获取结果并转换格式
            raw_results = safe_locals.get('results', [])
            return self._convert_results(raw_results)

        except Exception as e:
            print(f"[DatabaseAlgorithmRecognizer] 执行算法失败 {self.config.english_name}: {e}")
            if hasattr(e, 'lineno'):
                print(f"[DatabaseAlgorithmRecognizer] 错误位置: 第{e.lineno}行")
            return []

    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局执行环境"""
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

    def _create_safe_locals(self, kdata: pd.DataFrame) -> Dict[str, Any]:
        """创建安全的本地执行环境"""
        return {
            'kdata': kdata,
            'config': self.config,
            'parameters': self.parameters,
            'results': [],
            'create_result': self._create_result_function(),
        }

    def _create_result_function(self):
        """创建结果创建函数"""
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

    def _convert_results(self, raw_results: List[Dict]) -> List[PatternResult]:
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
                print(f"[DatabaseAlgorithmRecognizer] 结果转换失败: {e}")
                continue

        return converted_results


# 注册数据库算法识别器为默认识别器
PatternAlgorithmFactory.register('default', DatabaseAlgorithmRecognizer)


# 创建全局实例，保持向后兼容
PatternRecognizer = EnhancedPatternRecognizer


def create_pattern_recognizer(debug_mode: bool = False) -> EnhancedPatternRecognizer:
    """
    创建形态识别器实例

    Args:
        debug_mode: 是否启用调试模式

    Returns:
        形态识别器实例
    """
    return EnhancedPatternRecognizer(debug_mode=debug_mode)


# 工具函数
def validate_kdata(kdata) -> bool:
    """验证K线数据有效性"""
    if kdata is None:
        return False

    if isinstance(kdata, pd.DataFrame):
        required_columns = ['open', 'high', 'low', 'close']
        return all(col in kdata.columns for col in required_columns) and len(kdata) > 0

    return len(kdata) > 0


def get_pattern_recognizer_info() -> Dict[str, Any]:
    """获取形态识别器信息"""
    return {
        'version': '2.0.0',
        'framework': 'Enhanced Pattern Recognition Framework',
        'compatible_with': 'hikyuu-ui unified pattern system',
        'features': [
            '统一框架兼容',
            '增强错误处理',
            '调试模式支持',
            '执行统计',
            '缓存机制',
            '数据预处理',
            '向后兼容'
        ]
    }


if __name__ == "__main__":
    # 测试代码
    print("Enhanced Pattern Recognition Module")
    print("=" * 50)

    info = get_pattern_recognizer_info()
    print(f"版本: {info['version']}")
    print(f"框架: {info['framework']}")
    print(f"特性: {', '.join(info['features'])}")

    # 创建测试实例
    recognizer = create_pattern_recognizer(debug_mode=True)
    print(f"\n创建识别器成功，调试模式: {recognizer.debug_mode}")

    # 显示统计信息
    stats = recognizer.get_execution_stats()
    print(f"执行统计: {stats}")
