"""
Enhanced Pattern Recognition Module for Trading System
完全重构的形态识别模块，与新统一框架完全兼容
"""

from utils.data_preprocessing import validate_kdata
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import traceback
import time

# 导入新的统一框架
from analysis.pattern_base import (
    BasePatternRecognizer, PatternResult, PatternConfig,
    PatternAlgorithmFactory, SignalType,
    calculate_body_ratio, calculate_shadow_ratios,
    is_bullish_candle, is_bearish_candle
)

# 导入指标收集
from core.metrics.app_metrics_service import measure


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

    @measure("pattern.identify_patterns")
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
                monitor.end_recognition(
                    success=True, pattern_count=len(cached_result))
                if self.debug_mode:
                    print(
                        f"[EnhancedPatternRecognizer] 缓存命中，返回 {len(cached_result)} 个形态")
                return cached_result

            monitor.record_cache_miss()

            all_results = []
            from analysis.pattern_manager import PatternManager
            pattern_manager = PatternManager()

            # 重构核心逻辑：明确处理两种情况
            target_configs: List[PatternConfig] = []
            if pattern_types:
                # 情况A：用户指定了要识别的形态类型
                if self.debug_mode:
                    print(f"[EnhancedPatternRecognizer] 模式A：识别指定的 {len(pattern_types)} 个形态: {pattern_types}")
                for p_type in pattern_types:
                    config = pattern_manager.get_pattern_config(p_type)
                    if config and config.is_active:
                        target_configs.append(config)
                    elif self.debug_mode:
                        print(f"[EnhancedPatternRecognizer] 警告：无法找到或形态 '{p_type}' 未激活，已跳过。")
            else:
                # 情况B：用户未指定，识别所有激活的形态
                if self.debug_mode:
                    print("[EnhancedPatternRecognizer] 模式B：识别所有已激活的形态。")
                all_configs = pattern_manager.get_all_patterns()
                target_configs = [config for config in all_configs if config.is_active]

            if self.debug_mode:
                print(f"[EnhancedPatternRecognizer] 最终确定要执行识别的形态数量: {len(target_configs)}")

            if not target_configs:
                print("[EnhancedPatternRecognizer] 警告：没有找到任何可以执行的形态配置。")
                monitor.end_recognition(success=False, pattern_count=0)
                return []

            # 统一的执行循环
            for config in target_configs:
                try:
                    # 使用工厂创建识别器
                    recognizer = PatternAlgorithmFactory.create(config)

                    # 执行识别
                    pattern_results = recognizer.recognize(kdata)

                    if self.debug_mode:
                        print(f"[EnhancedPatternRecognizer] 形态 '{config.name}' 识别到 {len(pattern_results)} 个原始结果")

                    # 过滤低置信度结果
                    filtered_results = [
                        result for result in pattern_results
                        if result.confidence >= confidence_threshold
                    ]

                    if self.debug_mode:
                        print(f"[EnhancedPatternRecognizer] 形态 '{config.name}' 筛选后剩余 {len(filtered_results)} 个结果 (置信度 > {confidence_threshold})")

                    # 转换为字典格式
                    for result in filtered_results:
                        result_dict = result.to_dict()

                        # 确保必要的字段都被正确设置
                        if 'pattern_name' not in result_dict:
                            result_dict['pattern_name'] = config.name

                        if 'pattern_type' not in result_dict or not result_dict['pattern_type']:
                            result_dict['pattern_type'] = config.english_name

                        if 'type' not in result_dict:
                            result_dict['type'] = config.english_name

                        # 添加形态的分类信息
                        result_dict['category'] = config.category

                        # 确保有明确的索引信息
                        if 'index' not in result_dict or result_dict['index'] is None:
                            result_dict['index'] = len(kdata) - 1  # 默认使用最后一根K线

                        # 添加成功率信息
                        success_rate = config.success_rate if hasattr(config, 'success_rate') and config.success_rate is not None else 0.7
                        if success_rate > 1.0:
                            success_rate = success_rate / 100.0  # 归一化
                        result_dict['success_rate'] = success_rate

                        # 添加风险级别信息
                        result_dict['risk_level'] = config.risk_level if hasattr(config, 'risk_level') else 'medium'  # 默认为中等风险

                        all_results.append(result_dict)

                except Exception as e:
                    if self.debug_mode:
                        print(f"[EnhancedPatternRecognizer] 识别形态 {config.english_name} 时发生内部错误: {e}\n{traceback.format_exc()}")
                    continue

            # 缓存结果
            cache.put(kdata, cache_config, all_results)

            # 结束性能监控
            monitor.end_recognition(
                success=True, pattern_count=len(all_results))

            if self.debug_mode:
                print(
                    f"[EnhancedPatternRecognizer] 识别完成，共找到 {len(all_results)} 个形态")

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


# 专门的算法识别器类，用于数据库算法的执行
class DatabaseAlgorithmRecognizer(BasePatternRecognizer):
    """数据库算法识别器 - 性能优化版，统一的形态识别实现"""

    # 类级别的缓存，避免重复编译算法代码
    _compiled_algorithms = {}
    _algorithm_cache_size = 100  # 最大缓存算法数量

    @measure("pattern.database_recognize")
    def recognize(self, kdata: pd.DataFrame) -> List[PatternResult]:
        """执行数据库算法识别 - 安全增强版，防止系统崩溃"""
        if not self.validate_data(kdata):
            return []

        try:
            # 获取算法代码
            algorithm_code = self.config.algorithm_code
            if not algorithm_code or not algorithm_code.strip():
                return []

            # 数据大小检查，防止处理过大数据集
            if len(kdata) > 50000:  # 限制最大数据量
                print(
                    f"[DatabaseAlgorithmRecognizer] 数据量过大({len(kdata)})，跳过算法: {self.config.english_name}")
                return []

            # 创建增强的安全执行环境
            safe_globals = self._create_enhanced_safe_globals()
            safe_locals = self._create_enhanced_safe_locals(kdata)

            # 使用超时和资源监控执行算法代码
            return self._execute_algorithm_safely(algorithm_code, safe_globals, safe_locals)

        except Exception as e:
            print(
                f"[DatabaseAlgorithmRecognizer] 执行算法失败 {self.config.english_name}: {e}")
            return []

    def _execute_algorithm_safely(self, algorithm_code: str, safe_globals: dict, safe_locals: dict) -> List[PatternResult]:
        """安全执行算法代码，带超时和资源监控 - 跨平台版本"""
        import threading
        import sys

        # 尝试导入psutil，如果失败则跳过内存监控
        try:
            import psutil
            import os
            memory_monitoring = True
        except ImportError:
            memory_monitoring = False

        class TimeoutException(Exception):
            pass

        def execute_with_timeout():
            """在线程中执行算法代码"""
            try:
                # 将kdata也添加到全局环境中，以兼容可能不规范的算法代码
                safe_globals['kdata'] = safe_locals.get('kdata')
                exec(algorithm_code.strip(), safe_globals, safe_locals)
            except Exception as e:
                safe_locals['_execution_error'] = e

        try:
            # 记录开始时的内存使用
            start_memory = 0
            if memory_monitoring:
                try:
                    process = psutil.Process(os.getpid())
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except:
                    memory_monitoring = False

            # 创建执行线程
            execution_thread = threading.Thread(target=execute_with_timeout)
            execution_thread.daemon = True

            # 开始执行
            start_time = time.time()
            execution_thread.start()

            # 等待执行完成或超时
            timeout_seconds = 30
            execution_thread.join(timeout_seconds)

            # 检查是否超时
            if execution_thread.is_alive():
                print(
                    f"[DatabaseAlgorithmRecognizer] 算法执行超时 {self.config.english_name} (>{timeout_seconds}秒)")
                return []

            # 检查执行过程中是否有错误
            if '_execution_error' in safe_locals:
                error = safe_locals['_execution_error']
                print(
                    f"[DatabaseAlgorithmRecognizer] 算法执行错误 {self.config.english_name}: {error}")
                return []

            # 检查内存使用是否异常增长
            if memory_monitoring:
                try:
                    end_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = end_memory - start_memory

                    if memory_increase > 500:  # 如果内存增长超过500MB
                        print(
                            f"[DatabaseAlgorithmRecognizer] 警告: 算法 {self.config.english_name} 内存使用异常增长 {memory_increase:.1f}MB")
                except:
                    pass

            # 获取结果并转换格式
            raw_results = safe_locals.get('results', [])

            # 限制结果数量，防止内存问题
            if len(raw_results) > 10000:
                print(
                    f"[DatabaseAlgorithmRecognizer] 警告: 算法 {self.config.english_name} 返回结果过多({len(raw_results)})，截取前10000个")
                raw_results = raw_results[:10000]

            execution_time = time.time() - start_time
            if execution_time > 10:  # 如果执行时间超过10秒，给出警告
                print(
                    f"[DatabaseAlgorithmRecognizer] 警告: 算法 {self.config.english_name} 执行时间较长 {execution_time:.1f}秒")

            return self._convert_enhanced_results(raw_results)

        except MemoryError as e:
            print(
                f"[DatabaseAlgorithmRecognizer] 内存不足 {self.config.english_name}: {e}")
            return []
        except RecursionError as e:
            print(
                f"[DatabaseAlgorithmRecognizer] 递归深度超限 {self.config.english_name}: {e}")
            return []
        except Exception as e:
            print(
                f"[DatabaseAlgorithmRecognizer] 算法执行异常 {self.config.english_name}: {e}")
            return []

    @staticmethod
    def safe_calculate_volatility(prices, period=20):
        """安全的波动率计算函数"""
        if len(prices) < period:
            return 0.0

        recent_prices = prices[-period:]
        if len(recent_prices) < 2:
            return 0.0

        try:
            returns = np.diff(recent_prices) / recent_prices[:-1]
            return np.std(returns) if len(returns) > 0 else 0.0
        except:
            return 0.0

    @staticmethod
    def safe_calculate_momentum(prices, period=10):
        """安全的动量计算函数"""
        if len(prices) < period + 1:
            return 0.0

        try:
            current_price = prices[-1]
            past_price = prices[-period-1]
            return (current_price - past_price) / past_price if past_price > 0 else 0.0
        except:
            return 0.0

    @staticmethod
    def safe_calculate_rsi(prices, period=14):
        """安全的RSI计算函数"""
        if len(prices) < period + 1:
            return 50.0

        try:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return 50.0

    @staticmethod
    def safe_calculate_trend_strength(prices, period=20):
        """安全的趋势强度计算函数"""
        if len(prices) < period:
            return 0.0

        recent_prices = prices[-period:]
        if len(recent_prices) < 2:
            return 0.0

        # 计算线性回归斜率作为趋势强度
        x = np.arange(len(recent_prices))
        y = np.array(recent_prices)

        try:
            slope = np.polyfit(x, y, 1)[0]
            return slope / np.mean(y) if np.mean(y) > 0 else 0.0
        except:
            return 0.0

    def _create_enhanced_safe_globals(self) -> Dict[str, Any]:
        """创建增强的安全执行环境 - 性能优化版"""

        # 定义缺失的工具函数
        def safe_find_local_extremes(data, window=5):
            """安全的局部极值查找函数"""
            if len(data) < window * 2 + 1:
                return [], []

            maxima = []
            minima = []

            for i in range(window, len(data) - window):
                # 检查局部最大值
                is_max = True
                for j in range(i - window, i + window + 1):
                    if j != i and data[j] >= data[i]:
                        is_max = False
                        break
                if is_max:
                    maxima.append(i)

                # 检查局部最小值
                is_min = True
                for j in range(i - window, i + window + 1):
                    if j != i and data[j] <= data[i]:
                        is_min = False
                        break
                if is_min:
                    minima.append(i)

            return maxima, minima

        def safe_calculate_body_ratio(open_price, high_price, low_price, close_price):
            """安全的实体比例计算函数"""
            try:
                body_size = abs(close_price - open_price)
                total_range = high_price - low_price
                return body_size / total_range if total_range > 0 else 0.0
            except:
                return 0.0

        def safe_calculate_shadow_ratios(open_price, high_price, low_price, close_price):
            """安全的影线比例计算函数"""
            try:
                total_range = high_price - low_price
                if total_range <= 0:
                    return 0.0, 0.0

                upper_shadow = high_price - max(open_price, close_price)
                lower_shadow = min(open_price, close_price) - low_price

                upper_ratio = upper_shadow / total_range
                lower_ratio = lower_shadow / total_range

                return upper_ratio, lower_ratio
            except:
                return 0.0, 0.0

        def safe_is_bullish_candle(open_price, close_price):
            """安全的阳线判断函数"""
            try:
                return close_price > open_price
            except:
                return False

        def safe_is_bearish_candle(open_price, close_price):
            """安全的阴线判断函数"""
            try:
                return close_price < open_price
            except:
                return False

        return {
            # 基础Python函数
            'len': len, 'abs': abs, 'max': max, 'min': min, 'sum': sum,
            'range': range, 'enumerate': enumerate, 'zip': zip,
            'str': str, 'float': float, 'int': int, 'bool': bool,
            'round': round, 'pow': pow, 'any': any, 'all': all,

            # 数学和数据处理
            'np': np, 'pd': pd,

            # 形态识别相关类型
            'SignalType': SignalType,
            'PatternResult': PatternResult,

            # 安全的工具函数
            'calculate_body_ratio': safe_calculate_body_ratio,
            'calculate_shadow_ratios': safe_calculate_shadow_ratios,
            'is_bullish_candle': safe_is_bullish_candle,
            'is_bearish_candle': safe_is_bearish_candle,
            'find_local_extremes': safe_find_local_extremes,
            'calculate_trend_strength': self.safe_calculate_trend_strength,
            'calculate_volatility': self.safe_calculate_volatility,
            'calculate_momentum': self.safe_calculate_momentum,
            'calculate_rsi': self.safe_calculate_rsi,
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
                'volatility': self.safe_calculate_volatility(closes, 20),
                'momentum_10': self.safe_calculate_momentum(closes, 10),
                'rsi_14': self.safe_calculate_rsi(closes, 14),
                'trend_strength': self.safe_calculate_trend_strength(closes, 20),

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

                # 确保有pattern_type字段
                pattern_type = raw_result.get('pattern_type', self.config.english_name)
                if not pattern_type:
                    pattern_type = self.config.english_name

                # 确保有价格信息
                price = raw_result.get('price', 0.0)
                if not isinstance(price, (int, float)) or price <= 0:
                    # 尝试从K线数据中获取
                    index = raw_result.get('index', -1)
                    if hasattr(self, 'kdata') and self.kdata is not None and index >= 0 and index < len(self.kdata):
                        price = float(self.kdata.iloc[index]['close'])
                    else:
                        price = 0.0

                # 创建结果对象
                result = PatternResult(
                    pattern_type=pattern_type,
                    pattern_name=self.config.name,
                    pattern_category=self.config.category,
                    signal_type=signal_type,
                    confidence=confidence,
                    confidence_level=self.calculate_confidence_level(
                        confidence),
                    index=int(raw_result.get('index', 0)),
                    datetime_val=raw_result.get('datetime_val'),
                    price=float(price),
                    start_index=int(raw_result.get('start_index')) if raw_result.get(
                        'start_index') is not None else None,
                    end_index=int(raw_result.get('end_index')) if raw_result.get(
                        'end_index') is not None else None,
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
        self.metrics['average_processing_time'] = total_time / \
            self.metrics['total_recognitions']

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
        data_hash = hashlib.md5(
            str(kdata.values.tobytes()).encode()).hexdigest()[:16]
        config_hash = hashlib.md5(
            str(sorted(config.items())).encode()).hexdigest()[:16]

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

        oldest_key = min(self.access_times.keys(),
                         key=lambda k: self.access_times[k])
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


# 使用utils.data_preprocessing中的validate_kdata函数


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
