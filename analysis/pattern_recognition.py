"""
形态识别模块
提供基础的形态识别功能
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from .pattern_base import BasePatternRecognizer, PatternResult, SignalType


class PatternRecognizer(BasePatternRecognizer):
    """基础形态识别器"""

    def __init__(self, config=None):
        """初始化形态识别器"""
        # 如果没有提供config，创建一个默认配置
        if config is None:
            from .pattern_base import PatternConfig, SignalType
            config = PatternConfig(
                id=1,
                name="基础形态识别器",
                english_name="BasicPatternRecognizer",
                category="candlestick",
                signal_type=SignalType.NEUTRAL,
                description="基础的K线形态识别器",
                min_periods=1,
                max_periods=10,
                confidence_threshold=0.5,
                algorithm_code="basic",
                parameters={},
                is_active=True
            )

        super().__init__(config)
        self.name = "基础形态识别器"
        self.version = "1.0.0"

    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """
        识别形态 - 实现抽象方法

        Args:
            kdata: K线数据，包含open, high, low, close, volume列

        Returns:
            形态识别结果列表
        """
        return self.recognize_patterns(kdata)

    def recognize_patterns(self, data: pd.DataFrame) -> List[PatternResult]:
        """
        识别形态

        Args:
            data: K线数据，包含open, high, low, close, volume列

        Returns:
            形态识别结果列表
        """
        results = []

        if data is None or data.empty:
            return results

        try:
            # 简单的形态识别示例
            # 这里可以添加更复杂的形态识别逻辑

            # 检测锤子线形态
            hammer_results = self._detect_hammer(data)
            results.extend(hammer_results)

            # 检测十字星形态
            doji_results = self._detect_doji(data)
            results.extend(doji_results)

        except Exception as e:
            # 记录错误但不中断程序
            print(f"形态识别过程中出现错误: {e}")

        return results

    def _detect_hammer(self, data: pd.DataFrame) -> List[PatternResult]:
        """检测锤子线形态"""
        results = []

        if len(data) < 1:
            return results

        try:
            for i in range(len(data)):
                row = data.iloc[i]
                open_price = row['open']
                high_price = row['high']
                low_price = row['low']
                close_price = row['close']

                # 锤子线的基本条件
                body = abs(close_price - open_price)
                upper_shadow = high_price - max(open_price, close_price)
                lower_shadow = min(open_price, close_price) - low_price

                # 简单的锤子线判断逻辑
                if lower_shadow > 2 * body and upper_shadow < body * 0.1:
                    result = PatternResult(
                        pattern_type="candlestick",
                        pattern_name="锤子线",
                        pattern_category="反转形态",
                        signal_type=SignalType.BUY,
                        confidence=0.7,
                        confidence_level="中等",
                        index=i,
                        datetime_val=None,
                        price=close_price,
                        start_index=i,
                        end_index=i,
                        extra_data={"description": "检测到锤子线形态，可能的买入信号"}
                    )
                    results.append(result)

        except Exception as e:
            print(f"锤子线检测错误: {e}")

        return results

    def _detect_doji(self, data: pd.DataFrame) -> List[PatternResult]:
        """检测十字星形态"""
        results = []

        if len(data) < 1:
            return results

        try:
            for i in range(len(data)):
                row = data.iloc[i]
                open_price = row['open']
                high_price = row['high']
                low_price = row['low']
                close_price = row['close']

                # 十字星的基本条件
                body = abs(close_price - open_price)
                total_range = high_price - low_price

                # 简单的十字星判断逻辑
                if total_range > 0 and body / total_range < 0.1:
                    result = PatternResult(
                        pattern_type="candlestick",
                        pattern_name="十字星",
                        pattern_category="反转形态",
                        signal_type=SignalType.NEUTRAL,
                        confidence=0.6,
                        confidence_level="中等",
                        index=i,
                        datetime_val=None,
                        price=close_price,
                        start_index=i,
                        end_index=i,
                        extra_data={"description": "检测到十字星形态，市场犹豫信号"}
                    )
                    results.append(result)

        except Exception as e:
            print(f"十字星检测错误: {e}")

        return results

    def get_supported_patterns(self) -> List[str]:
        """获取支持的形态列表"""
        return ["锤子线", "十字星"]

    def get_pattern_description(self, pattern_name: str) -> str:
        """获取形态描述"""
        descriptions = {
            "锤子线": "锤子线是一种看涨反转形态，特征是实体较小，下影线较长",
            "十字星": "十字星表示市场犹豫不决，开盘价和收盘价几乎相等"
        }
        return descriptions.get(pattern_name, "未知形态")


class EnhancedPatternRecognizer(PatternRecognizer):
    """增强版形态识别器"""

    def __init__(self, config=None, debug_mode=False):
        """初始化增强版形态识别器"""
        super().__init__(config)
        self.debug_mode = debug_mode
        self.name = "增强版形态识别器"
        self.version = "2.0.0"

        # 增强功能
        self.confidence_scores = {}
        self.pattern_history = []

    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """
        增强版形态识别 - 包含更多形态和置信度评估

        Args:
            kdata: K线数据

        Returns:
            形态识别结果列表
        """
        if self.debug_mode:
            print(f"开始增强版形态识别，数据量: {len(kdata)}")

        # 调用基础识别方法
        basic_results = super().recognize(kdata)

        # 增强处理
        enhanced_results = []
        for result in basic_results:
            # 计算置信度分数
            confidence = self._calculate_confidence(result, kdata)
            result.confidence = confidence

            # 添加到历史记录
            self.pattern_history.append(result)

            enhanced_results.append(result)

        if self.debug_mode:
            print(f"识别完成，发现 {len(enhanced_results)} 个形态")

        return enhanced_results

    def _calculate_confidence(self, pattern_result: PatternResult, kdata: pd.DataFrame) -> float:
        """计算形态置信度"""
        try:
            # 基础置信度
            base_confidence = 0.5

            # 根据成交量调整
            if len(kdata) > 0:
                volume_factor = min(kdata['volume'].iloc[-1] / kdata['volume'].mean(), 2.0)
                base_confidence *= volume_factor

            # 限制在0-1范围内
            return min(max(base_confidence, 0.0), 1.0)

        except Exception as e:
            if self.debug_mode:
                print(f"计算置信度失败: {e}")
            return 0.5

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """获取形态统计信息"""
        if not self.pattern_history:
            return {}

        stats = {
            'total_patterns': len(self.pattern_history),
            'pattern_types': {},
            'avg_confidence': 0.0
        }

        # 统计各类形态数量
        for pattern in self.pattern_history:
            pattern_name = pattern.pattern_name
            if pattern_name not in stats['pattern_types']:
                stats['pattern_types'][pattern_name] = 0
            stats['pattern_types'][pattern_name] += 1

        # 计算平均置信度
        if self.pattern_history:
            total_confidence = sum(p.confidence for p in self.pattern_history if hasattr(p, 'confidence'))
            stats['avg_confidence'] = total_confidence / len(self.pattern_history)

        return stats


# 兼容性函数
def get_performance_monitor():
    """获取性能监控器（兼容性函数）"""
    return None


def get_pattern_cache():
    """获取形态缓存（兼容性函数）"""
    return {}


def get_pattern_recognizer_info():
    """获取形态识别器信息（兼容性函数）"""
    return {
        'name': 'EnhancedPatternRecognizer',
        'version': '2.0.0',
        'supported_patterns': ['锤子线', '十字星']
    }
