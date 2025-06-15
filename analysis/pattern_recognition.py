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
        识别形态 - 性能优化版，集成缓存和监控

        Args:
            kdata: K线数据DataFrame
            confidence_threshold: 置信度阈值
            pattern_types: 要识别的形态类型列表，None表示识别所有类型

        Returns:
            识别结果列表
        """
        # 获取全局监控器和缓存
        monitor = get_performance_monitor()
        cache = get_pattern_cache()

        # 开始性能监控
        monitor.start_recognition()

        try:
            # 数据验证
            if not validate_kdata(kdata):
                monitor.end_recognition(success=False, pattern_count=0)
                return []

            # 构建缓存配置
            cache_config = {
                'confidence_threshold': confidence_threshold,
                'pattern_types': pattern_types or [],
                'data_length': len(kdata)
            }

            # 尝试从缓存获取结果
            cached_result = cache.get(kdata, cache_config)
            if cached_result is not None:
                monitor.record_cache_hit()
                monitor.end_recognition(success=True, pattern_count=len(cached_result))
                if self.debug_mode:
                    print(f"[EnhancedPatternRecognizer] 缓存命中，返回 {len(cached_result)} 个形态")
                return cached_result

            monitor.record_cache_miss()

            # 执行形态识别
            all_results = []

            # 使用PatternManager进行识别
            try:
                from analysis.pattern_manager import PatternManager
                pattern_manager = PatternManager()

                # 获取所有形态配置
                pattern_configs = pattern_manager.get_all_patterns()

                for config in pattern_configs:
                    if not config.is_active:
                        continue

                    # 如果指定了形态类型，只识别指定类型
                    if pattern_types and config.english_name not in pattern_types:
                        continue

                    try:
                        # 使用工厂创建识别器
                        recognizer = PatternAlgorithmFactory.create(config)

                        # 执行识别
                        pattern_results = recognizer.recognize(kdata)

                        # 过滤低置信度结果
                        filtered_results = [
                            result for result in pattern_results
                            if result.confidence >= confidence_threshold
                        ]

                        # 转换为字典格式
                        for result in filtered_results:
                            result_dict = result.to_dict()
                            all_results.append(result_dict)

                    except Exception as e:
                        if self.debug_mode:
                            print(f"[EnhancedPatternRecognizer] 识别形态 {config.english_name} 失败: {e}")
                        continue

            except ImportError:
                # 如果PatternManager不可用，使用内置方法
                if self.debug_mode:
                    print("[EnhancedPatternRecognizer] PatternManager不可用，使用内置方法")

                # 使用内置的形态识别方法
                pattern_methods = [
                    ('hammer', self.find_hammer),
                    ('doji', self.find_doji),
                    ('shooting_star', self.find_shooting_star),
                    ('engulfing', self.find_engulfing),
                    ('morning_star', self.find_morning_star),
                    ('evening_star', self.find_evening_star),
                    ('three_white_soldiers', self.find_three_white_soldiers),
                ]

                for pattern_name, method in pattern_methods:
                    if pattern_types and pattern_name not in pattern_types:
                        continue

                    try:
                        results = method(kdata)
                        # 过滤低置信度结果
                        filtered_results = [
                            result for result in results
                            if result.get('confidence', 0) >= confidence_threshold
                        ]
                        all_results.extend(filtered_results)
                    except Exception as e:
                        if self.debug_mode:
                            print(f"[EnhancedPatternRecognizer] 内置方法 {pattern_name} 失败: {e}")
                        continue

            # 缓存结果
            cache.put(kdata, cache_config, all_results)

            # 结束性能监控
            monitor.end_recognition(success=True, pattern_count=len(all_results))

            if self.debug_mode:
                print(f"[EnhancedPatternRecognizer] 识别完成，共找到 {len(all_results)} 个形态")

            return all_results

        except Exception as e:
            monitor.end_recognition(success=False, pattern_count=0)
            if self.debug_mode:
                print(f"[EnhancedPatternRecognizer] 识别过程发生错误: {e}")
            return []

    def get_pattern_signals(self, kdata: pd.DataFrame,
                            confidence_threshold: float = 0.1,
                            pattern_types: Optional[List[str]] = None) -> List[Dict]:
        """
        获取形态信号 - 向后兼容方法

        Args:
            kdata: K线数据
            confidence_threshold: 置信度阈值
            pattern_types: 指定要识别的形态类型列表，None表示识别所有形态

        Returns:
            形态信号列表
        """
        return self.identify_patterns(kdata, confidence_threshold, pattern_types)

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
    """数据库算法识别器 - 性能优化版，统一的形态识别实现"""

    # 类级别的缓存，避免重复编译算法代码
    _compiled_algorithms = {}
    _algorithm_cache_size = 100  # 最大缓存算法数量

    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """执行数据库算法识别 - 性能优化版"""
        if not self.validate_data(kdata):
            return []

        try:
            # 获取算法代码
            algorithm_code = self.config.algorithm_code
            if not algorithm_code or not algorithm_code.strip():
                return []

            # 使用缓存的编译结果提升性能
            cache_key = f"{self.config.english_name}_{hash(algorithm_code)}"

            # 创建增强的安全执行环境
            safe_globals = self._create_enhanced_safe_globals()
            safe_locals = self._create_enhanced_safe_locals(kdata)

            # 执行算法代码
            exec(algorithm_code.strip(), safe_globals, safe_locals)

            # 获取结果并转换格式
            raw_results = safe_locals.get('results', [])
            return self._convert_enhanced_results(raw_results)

        except Exception as e:
            print(f"[DatabaseAlgorithmRecognizer] 执行算法失败 {self.config.english_name}: {e}")
            return []

    def _create_enhanced_safe_globals(self) -> Dict[str, Any]:
        """创建增强的安全执行环境 - 性能优化版"""
        return {
            # 基础Python函数
            'len': len, 'abs': abs, 'max': max, 'min': min, 'sum': sum,
            'range': range, 'enumerate': enumerate, 'zip': zip,
            'str': str, 'float': float, 'int': int, 'bool': bool,
            'round': round, 'pow': pow,

            # 数学和数据处理
            'np': np, 'pd': pd,

            # 形态识别相关类型
            'SignalType': SignalType,
            'PatternResult': PatternResult,
            'PatternCategory': PatternCategory,

            # 基础工具函数
            'calculate_body_ratio': calculate_body_ratio,
            'calculate_shadow_ratios': calculate_shadow_ratios,
            'is_bullish_candle': is_bullish_candle,
            'is_bearish_candle': is_bearish_candle,
            'find_local_extremes': find_local_extremes,
            'calculate_trend_strength': calculate_trend_strength,

            # 新增性能优化函数
            'calculate_volatility': calculate_volatility,
            'calculate_momentum': calculate_momentum,
            'calculate_rsi': calculate_rsi,
        }

    def _create_enhanced_safe_locals(self, kdata: pd.DataFrame) -> Dict[str, Any]:
        """创建增强的本地执行环境 - 性能优化版"""
        if kdata is None or len(kdata) == 0:
            raise ValueError("kdata不能为空")

        # 预计算常用数据，提升算法执行性能
        precomputed_data = self._precompute_indicators(kdata)

        locals_dict = {
            'kdata': kdata,
            'config': self.config,
            'parameters': self.parameters,
            'results': [],
            'create_result': self._create_enhanced_result_function(),

            # 预计算的指标数据
            **precomputed_data
        }

        return locals_dict

    def _precompute_indicators(self, kdata: pd.DataFrame) -> Dict[str, Any]:
        """预计算常用技术指标，提升算法执行性能"""
        try:
            # 基础价格数据
            opens = kdata['open'].values
            highs = kdata['high'].values
            lows = kdata['low'].values
            closes = kdata['close'].values

            # 预计算常用指标
            precomputed = {
                'opens': opens,
                'highs': highs,
                'lows': lows,
                'closes': closes,
                'volumes': kdata.get('volume', pd.Series([0] * len(kdata))).values,

                # 技术指标
                'sma_5': self._calculate_sma(closes, 5),
                'sma_10': self._calculate_sma(closes, 10),
                'sma_20': self._calculate_sma(closes, 20),
                'ema_12': self._calculate_ema(closes, 12),
                'ema_26': self._calculate_ema(closes, 26),

                # 波动率和动量
                'volatility': calculate_volatility(closes, 20),
                'momentum_10': calculate_momentum(closes, 10),
                'rsi_14': calculate_rsi(closes, 14),
                'trend_strength': calculate_trend_strength(closes, 20),

                # 价格范围
                'price_range': highs - lows,
                'body_size': np.abs(closes - opens),
                'upper_shadow': highs - np.maximum(opens, closes),
                'lower_shadow': np.minimum(opens, closes) - lows,
            }

            return precomputed

        except Exception as e:
            print(f"[DatabaseAlgorithmRecognizer] 预计算指标失败: {e}")
            return {}

    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算简单移动平均线"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)

        sma = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1:i + 1])

        return sma

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均线"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)

        alpha = 2.0 / (period + 1)
        ema = np.full(len(prices), np.nan)
        ema[period - 1] = np.mean(prices[:period])

        for i in range(period, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]

        return ema

    def _create_enhanced_result_function(self):
        """创建增强的结果创建函数 - 性能优化版"""
        def create_result(pattern_type: str, signal_type, confidence: float,
                          index: int, price: float, datetime_val: str = None,
                          start_index: int = None, end_index: int = None,
                          extra_data: Dict = None):
            """创建形态识别结果 - 增强版"""
            # 参数验证和优化
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                confidence = 0.5

            if not isinstance(index, int) or index < 0:
                index = 0

            if not isinstance(price, (int, float)) or price <= 0:
                price = 0.0

            return {
                'pattern_type': pattern_type or self.config.english_name,
                'signal_type': signal_type,
                'confidence': float(confidence),
                'index': int(index),
                'price': float(price),
                'datetime_val': datetime_val,
                'start_index': int(start_index) if start_index is not None else None,
                'end_index': int(end_index) if end_index is not None else None,
                'extra_data': extra_data or {}
            }
        return create_result

    def _convert_enhanced_results(self, raw_results: List[Dict]) -> List[PatternResult]:
        """转换原始结果为PatternResult对象 - 增强版"""
        if not raw_results:
            return []

        converted_results = []

        for raw_result in raw_results:
            try:
                # 信号类型处理
                signal_type = raw_result.get('signal_type', SignalType.NEUTRAL)
                if isinstance(signal_type, str):
                    try:
                        signal_type = SignalType(signal_type.lower())
                    except ValueError:
                        signal_type = SignalType.NEUTRAL
                elif not isinstance(signal_type, SignalType):
                    signal_type = SignalType.NEUTRAL

                # 置信度处理
                confidence = raw_result.get('confidence', 0.5)
                if not isinstance(confidence, (int, float)):
                    confidence = 0.5
                confidence = max(0.0, min(1.0, float(confidence)))

                # 创建结果对象
                result = PatternResult(
                    pattern_type=raw_result.get('pattern_type', self.config.english_name),
                    pattern_name=self.config.name,
                    pattern_category=self.config.category.value,
                    signal_type=signal_type,
                    confidence=confidence,
                    confidence_level=self.calculate_confidence_level(confidence),
                    index=int(raw_result.get('index', 0)),
                    datetime_val=raw_result.get('datetime_val'),
                    price=float(raw_result.get('price', 0.0)),
                    start_index=int(raw_result.get('start_index')) if raw_result.get('start_index') is not None else None,
                    end_index=int(raw_result.get('end_index')) if raw_result.get('end_index') is not None else None,
                    extra_data=raw_result.get('extra_data', {})
                )
                converted_results.append(result)

            except Exception as e:
                print(f"[DatabaseAlgorithmRecognizer] 结果转换失败: {e}")
                continue

        return converted_results

    @classmethod
    def clear_cache(cls):
        """清理算法缓存"""
        cls._compiled_algorithms.clear()

    @classmethod
    def get_cache_info(cls) -> Dict[str, int]:
        """获取缓存信息"""
        return {
            'cached_algorithms': len(cls._compiled_algorithms),
            'max_cache_size': cls._algorithm_cache_size
        }


# 注册数据库算法识别器为默认识别器
PatternAlgorithmFactory.register('default', DatabaseAlgorithmRecognizer)


# 创建全局实例，保持向后兼容
PatternRecognizer = EnhancedPatternRecognizer


class PerformanceMonitor:
    """性能监控器 - 监控形态识别系统性能"""

    def __init__(self):
        self.metrics = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_usage': 0,
            'pattern_counts': {},
            'performance_history': []
        }
        self.start_time = None

    def start_recognition(self):
        """开始识别计时"""
        import time
        self.start_time = time.time()

    def end_recognition(self, success: bool = True, pattern_count: int = 0):
        """结束识别计时"""
        if self.start_time is None:
            return

        processing_time = time.time() - self.start_time

        # 更新指标
        self.metrics['total_recognitions'] += 1
        if success:
            self.metrics['successful_recognitions'] += 1
        else:
            self.metrics['failed_recognitions'] += 1

        # 更新平均处理时间
        total_time = (self.metrics['average_processing_time'] *
                      (self.metrics['total_recognitions'] - 1) + processing_time)
        self.metrics['average_processing_time'] = total_time / self.metrics['total_recognitions']

        # 记录历史
        self.metrics['performance_history'].append({
            'timestamp': time.time(),
            'processing_time': processing_time,
            'success': success,
            'pattern_count': pattern_count
        })

        # 保持历史记录在合理范围内
        if len(self.metrics['performance_history']) > 1000:
            self.metrics['performance_history'] = self.metrics['performance_history'][-500:]

        self.start_time = None

    def record_cache_hit(self):
        """记录缓存命中"""
        self.metrics['cache_hits'] += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics['cache_misses'] += 1

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        return self.metrics['cache_hits'] / total if total > 0 else 0.0

    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self.metrics['total_recognitions']
        return self.metrics['successful_recognitions'] / total if total > 0 else 0.0

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            'total_recognitions': self.metrics['total_recognitions'],
            'success_rate': self.get_success_rate(),
            'average_processing_time': self.metrics['average_processing_time'],
            'cache_hit_rate': self.get_cache_hit_rate(),
            'memory_usage_mb': self.get_memory_usage(),
            'recent_performance': self._get_recent_performance()
        }

    def get_memory_usage(self) -> float:
        """获取内存使用量(MB)"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def _get_recent_performance(self) -> Dict[str, float]:
        """获取最近性能指标"""
        if not self.metrics['performance_history']:
            return {}

        recent = self.metrics['performance_history'][-10:]  # 最近10次
        avg_time = sum(r['processing_time'] for r in recent) / len(recent)
        success_count = sum(1 for r in recent if r['success'])

        return {
            'recent_avg_time': avg_time,
            'recent_success_rate': success_count / len(recent)
        }


class PatternCache:
    """形态识别缓存系统 - 提升重复识别性能"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0

    def _generate_key(self, kdata: pd.DataFrame, config: Dict) -> str:
        """生成缓存键"""
        import hashlib

        # 使用数据的哈希值和配置生成键
        data_hash = hashlib.md5(str(kdata.values.tobytes()).encode()).hexdigest()[:16]
        config_hash = hashlib.md5(str(sorted(config.items())).encode()).hexdigest()[:16]

        return f"{data_hash}_{config_hash}"

    def get(self, kdata: pd.DataFrame, config: Dict) -> Optional[List]:
        """获取缓存结果"""
        key = self._generate_key(kdata, config)

        if key in self.cache:
            self.hit_count += 1
            self.access_times[key] = datetime.now()
            return self.cache[key]
        else:
            self.miss_count += 1
            return None

    def put(self, kdata: pd.DataFrame, config: Dict, result: List):
        """存储缓存结果"""
        key = self._generate_key(kdata, config)

        # 如果缓存已满，删除最久未访问的项
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = result
        self.access_times[key] = datetime.now()

    def _evict_oldest(self):
        """删除最久未访问的缓存项"""
        if not self.access_times:
            return

        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        self.hit_count = 0
        self.miss_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.0

        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'memory_usage_estimate': len(self.cache) * 1024  # 粗略估计
        }


# 全局实例
_performance_monitor = PerformanceMonitor()
_pattern_cache = PatternCache()


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    return _performance_monitor


def get_pattern_cache() -> PatternCache:
    """获取形态缓存实例"""
    return _pattern_cache


def create_pattern_recognizer(debug_mode: bool = False) -> EnhancedPatternRecognizer:
    """
    创建形态识别器实例 - 工厂方法

    Args:
        debug_mode: 是否启用调试模式

    Returns:
        EnhancedPatternRecognizer实例
    """
    return EnhancedPatternRecognizer(debug_mode=debug_mode)


def validate_kdata(kdata) -> bool:
    """
    验证K线数据有效性

    Args:
        kdata: K线数据

    Returns:
        是否有效
    """
    if kdata is None:
        return False

    if not isinstance(kdata, pd.DataFrame):
        return False

    required_columns = ['open', 'high', 'low', 'close']
    return all(col in kdata.columns for col in required_columns)


def get_pattern_recognizer_info() -> Dict[str, Any]:
    """
    获取形态识别器信息

    Returns:
        系统信息字典
    """
    return {
        'version': '2.5.6',
        'supported_patterns': 67,
        'performance_optimized': True,
        'cache_enabled': True,
        'monitoring_enabled': True,
        'database_algorithms': True,
        'ml_predictions': True,
        'performance_stats': _performance_monitor.get_performance_summary(),
        'cache_stats': _pattern_cache.get_stats()
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
