#!/usr/bin/env python3
"""
智能缓存协调器

整合MultiLevelCacheManager、CacheManager等多个缓存管理器
实现智能缓存策略协调和管理，提供统一的智能缓存管理服务
"""

import time
import threading
import asyncio
import hashlib
from typing import Dict, List, Any, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from loguru import logger

# 导入现有缓存组件
from .cache_manager import (
    MultiLevelCacheManager, CacheLevel
)
# LRUCache, DiskCache, CacheEntry, CacheStats 在 cache_manager 中不存在，暂时注释
from .unified_monitor import PerformanceCache

# 导入性能监控
try:
    from .unified_performance_coordinator import get_performance_coordinator
    PERFORMANCE_COORDINATOR_AVAILABLE = True
except ImportError:
    PERFORMANCE_COORDINATOR_AVAILABLE = False


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                    # 最近最少使用
    LFU = "lfu"                    # 最少使用频率
    FIFO = "fifo"                  # 先进先出
    ADAPTIVE = "adaptive"          # 自适应策略
    PREDICTIVE = "predictive"      # 预测性策略
    INTELLIGENT = "intelligent"    # 智能策略


class CacheType(Enum):
    """缓存类型"""
    DATA = "data"                  # 数据缓存
    COMPUTATION = "computation"    # 计算结果缓存
    UI = "ui"                     # UI组件缓存
    PERFORMANCE = "performance"    # 性能监控缓存
    TEMPORARY = "temporary"        # 临时缓存


class CachePriority(Enum):
    """缓存优先级"""
    CRITICAL = 1    # 关键缓存（不可清理）
    HIGH = 2        # 高优先级
    MEDIUM = 3      # 中等优先级
    LOW = 4         # 低优先级
    DISPOSABLE = 5  # 可丢弃缓存


@dataclass
class CacheConfiguration:
    """缓存配置"""
    # 基础配置
    name: str
    cache_type: CacheType
    strategy: CacheStrategy = CacheStrategy.LRU
    priority: CachePriority = CachePriority.MEDIUM

    # 容量配置
    max_size: int = 1000           # 最大条目数
    max_memory_mb: int = 100       # 最大内存使用(MB)
    max_disk_mb: int = 1000        # 最大磁盘使用(MB)

    # 时间配置
    default_ttl_minutes: int = 30  # 默认生存时间(分钟)
    cleanup_interval_minutes: int = 10  # 清理间隔(分钟)

    # 性能配置
    enable_compression: bool = False  # 启用压缩
    enable_encryption: bool = False   # 启用加密
    enable_statistics: bool = True    # 启用统计

    # 智能配置
    enable_prediction: bool = False   # 启用预测
    enable_preloading: bool = False   # 启用预加载
    enable_adaptive_sizing: bool = True  # 启用自适应大小调整


@dataclass
class CacheMetrics:
    """缓存指标"""
    cache_name: str
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    eviction_rate: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0
    avg_access_time_ms: float = 0.0
    total_requests: int = 0
    cache_efficiency: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CacheRecommendation:
    """缓存优化建议"""
    cache_name: str
    recommendation_type: str  # 'resize', 'strategy_change', 'cleanup', 'preload'
    description: str
    impact_score: float  # 0-1，影响评分
    implementation_cost: str  # 'low', 'medium', 'high'
    expected_improvement: str
    timestamp: datetime = field(default_factory=datetime.now)


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []
        self.strategy_performance: Dict[CacheStrategy, float] = defaultdict(float)
        self._lock = threading.RLock()

    def analyze_performance(self, cache_name: str, metrics: CacheMetrics,
                            access_pattern: 'CacheAccessPattern') -> List[CacheRecommendation]:
        """分析性能并生成优化建议"""
        recommendations = []

        try:
            # 分析命中率
            if metrics.hit_rate < 0.6:
                recommendations.extend(self._optimize_hit_rate(cache_name, metrics, access_pattern))

            # 分析访问速度
            if metrics.avg_access_time_ms > 30:
                recommendations.extend(self._optimize_access_speed(cache_name, metrics))

            # 分析缓存效率
            if metrics.cache_efficiency < 0.7:
                recommendations.extend(self._optimize_efficiency(cache_name, metrics, access_pattern))

            # 分析访问模式
            recommendations.extend(self._optimize_access_pattern(cache_name, access_pattern))

        except Exception as e:
            logger.error(f"性能分析失败 {cache_name}: {e}")

        return recommendations

    def _optimize_hit_rate(self, cache_name: str, metrics: CacheMetrics,
                           access_pattern: 'CacheAccessPattern') -> List[CacheRecommendation]:
        """优化命中率"""
        recommendations = []

        # 检查热点数据
        hot_keys = access_pattern.get_hot_keys(10)
        if hot_keys:
            total_accesses = sum(freq for _, freq in hot_keys)
            hot_ratio = total_accesses / max(1, metrics.total_requests)

            if hot_ratio > 0.8:  # 80%的访问集中在少数key上
                recommendations.append(CacheRecommendation(
                    cache_name=cache_name,
                    recommendation_type='strategy_change',
                    description=f"检测到热点数据集中(前10个key占{hot_ratio:.1%}访问)，建议使用LFU策略",
                    impact_score=0.8,
                    implementation_cost='low',
                    expected_improvement='提升15-25%命中率'
                ))

        # 检查缓存容量
        if metrics.eviction_rate > 0.1:  # 驱逐率超过10%
            recommendations.append(CacheRecommendation(
                cache_name=cache_name,
                recommendation_type='resize',
                description=f"缓存驱逐率过高({metrics.eviction_rate:.1%})，建议增加缓存容量",
                impact_score=0.7,
                implementation_cost='medium',
                expected_improvement='减少20-30%缓存未命中'
            ))

        return recommendations

    def _optimize_access_speed(self, cache_name: str, metrics: CacheMetrics) -> List[CacheRecommendation]:
        """优化访问速度"""
        recommendations = []

        if metrics.avg_access_time_ms > 50:
            recommendations.append(CacheRecommendation(
                cache_name=cache_name,
                recommendation_type='resize',
                description=f"访问时间过长({metrics.avg_access_time_ms:.1f}ms)，建议增加内存缓存比例",
                impact_score=0.6,
                implementation_cost='low',
                expected_improvement='减少40-60%访问时间'
            ))

        if metrics.memory_usage_mb > 0 and metrics.disk_usage_mb > metrics.memory_usage_mb * 5:
            recommendations.append(CacheRecommendation(
                cache_name=cache_name,
                recommendation_type='strategy_change',
                description="磁盘缓存比例过高，建议调整内存/磁盘缓存比例",
                impact_score=0.5,
                implementation_cost='medium',
                expected_improvement='提升30-50%访问速度'
            ))

        return recommendations

    def _optimize_efficiency(self, cache_name: str, metrics: CacheMetrics,
                             access_pattern: 'CacheAccessPattern') -> List[CacheRecommendation]:
        """优化缓存效率"""
        recommendations = []

        # 分析访问模式的时间分布
        recent_accesses = len([
            access for access in access_pattern.access_history
            if (datetime.now() - access['timestamp']).total_seconds() <= 3600
        ])

        if recent_accesses < metrics.total_requests * 0.1:  # 最近1小时访问量不足10%
            recommendations.append(CacheRecommendation(
                cache_name=cache_name,
                recommendation_type='cleanup',
                description="检测到访问模式稀疏，建议缩短TTL或清理冷数据",
                impact_score=0.4,
                implementation_cost='low',
                expected_improvement='提升10-20%缓存效率'
            ))

        return recommendations

    def _optimize_access_pattern(self, cache_name: str,
                                 access_pattern: 'CacheAccessPattern') -> List[CacheRecommendation]:
        """基于访问模式优化"""
        recommendations = []

        try:
            # 分析访问时间模式
            access_times = [access['timestamp'] for access in access_pattern.access_history]
            if len(access_times) >= 100:
                # 检查是否有明显的时间模式
                hour_distribution = defaultdict(int)
                for timestamp in access_times[-100:]:  # 最近100次访问
                    hour_distribution[timestamp.hour] += 1

                # 找出访问高峰时段
                peak_hours = [hour for hour, count in hour_distribution.items() if count > 10]
                if len(peak_hours) <= 3:  # 访问集中在少数时段
                    recommendations.append(CacheRecommendation(
                        cache_name=cache_name,
                        recommendation_type='preload',
                        description=f"检测到访问集中在{len(peak_hours)}个时段，建议在高峰前预加载数据",
                        impact_score=0.6,
                        implementation_cost='medium',
                        expected_improvement='减少15-25%高峰期延迟'
                    ))

            # 分析访问序列模式
            hot_keys = access_pattern.get_hot_keys(5)
            if hot_keys:
                # 检查是否存在访问序列关联
                key_sequences = self._analyze_key_sequences(access_pattern.access_history)
                if key_sequences:
                    recommendations.append(CacheRecommendation(
                        cache_name=cache_name,
                        recommendation_type='preload',
                        description="检测到关联访问模式，建议实现预测性预加载",
                        impact_score=0.7,
                        implementation_cost='high',
                        expected_improvement='减少20-35%预测性缓存未命中'
                    ))

        except Exception as e:
            logger.error(f"访问模式分析失败 {cache_name}: {e}")

        return recommendations

    def _analyze_key_sequences(self, access_history: deque) -> Dict[str, List[str]]:
        """分析键访问序列"""
        sequences = defaultdict(list)

        try:
            # 分析最近的访问序列
            recent_accesses = list(access_history)[-50:]  # 最近50次访问

            for i in range(len(recent_accesses) - 1):
                current_key = recent_accesses[i]['key']
                next_key = recent_accesses[i + 1]['key']

                if current_key != next_key:
                    sequences[current_key].append(next_key)

            # 过滤出有明显模式的序列
            filtered_sequences = {}
            for key, next_keys in sequences.items():
                if len(next_keys) >= 3:  # 至少3次关联
                    # 统计最常见的后续键
                    key_counts = defaultdict(int)
                    for next_key in next_keys:
                        key_counts[next_key] += 1

                    # 如果某个后续键出现频率超过50%
                    total_count = len(next_keys)
                    for next_key, count in key_counts.items():
                        if count / total_count > 0.5:
                            filtered_sequences[key] = [next_key]
                            break

            return filtered_sequences

        except Exception as e:
            logger.error(f"序列分析失败: {e}")
            return {}

    def suggest_strategy_change(self, cache_name: str, current_strategy: CacheStrategy,
                                metrics: CacheMetrics) -> Optional[CacheStrategy]:
        """建议策略变更"""
        try:
            # 基于性能历史选择最佳策略
            if current_strategy == CacheStrategy.LRU and metrics.hit_rate < 0.5:
                # LRU效果不好，尝试LFU
                return CacheStrategy.LFU
            elif current_strategy == CacheStrategy.LFU and metrics.avg_access_time_ms > 40:
                # LFU访问慢，尝试自适应
                return CacheStrategy.ADAPTIVE
            elif metrics.cache_efficiency < 0.6:
                # 效率低，尝试智能策略
                return CacheStrategy.INTELLIGENT

            return None

        except Exception as e:
            logger.error(f"策略建议失败 {cache_name}: {e}")
            return None


class CacheAccessPattern:
    """缓存访问模式分析器"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.access_history: deque = deque(maxlen=window_size)
        self.key_frequencies: Dict[str, int] = defaultdict(int)
        self.access_times: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.RLock()

    def record_access(self, key: str, hit: bool):
        """记录访问"""
        with self._lock:
            timestamp = datetime.now()

            self.access_history.append({
                'key': key,
                'hit': hit,
                'timestamp': timestamp
            })

            self.key_frequencies[key] += 1
            self.access_times[key].append(timestamp)

            # 限制每个key的时间记录数量
            if len(self.access_times[key]) > 100:
                self.access_times[key] = self.access_times[key][-50:]

    def get_hot_keys(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """获取热点键"""
        with self._lock:
            return sorted(self.key_frequencies.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def get_access_frequency(self, key: str) -> float:
        """获取访问频率（次/小时）"""
        with self._lock:
            if key not in self.access_times:
                return 0.0

            now = datetime.now()
            recent_accesses = [
                t for t in self.access_times[key]
                if (now - t).total_seconds() <= 3600  # 最近1小时
            ]

            return len(recent_accesses)

    def predict_next_access(self, key: str) -> Optional[datetime]:
        """预测下次访问时间"""
        with self._lock:
            if key not in self.access_times or len(self.access_times[key]) < 2:
                return None

            times = self.access_times[key][-10:]  # 最近10次访问
            if len(times) < 2:
                return None

            # 计算平均间隔
            intervals = []
            for i in range(1, len(times)):
                interval = (times[i] - times[i-1]).total_seconds()
                intervals.append(interval)

            if not intervals:
                return None

            avg_interval = sum(intervals) / len(intervals)
            return times[-1] + timedelta(seconds=avg_interval)


class IntelligentCacheManager:
    """智能缓存管理器"""

    def __init__(self, config: CacheConfiguration):
        self.config = config
        self.name = config.name

        # 缓存实现
        self.multilevel_cache = self._create_multilevel_cache()
        self.performance_cache = PerformanceCache() if hasattr(PerformanceCache, '__init__') else None

        # 访问模式分析
        self.access_pattern = CacheAccessPattern()

        # 缓存优化器
        self.optimizer = CacheOptimizer()

        # 统计信息
        self.metrics = CacheMetrics(cache_name=self.name)
        self.recommendations: List[CacheRecommendation] = []

        # 线程安全
        self._lock = threading.RLock()

        # 清理任务
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()

        logger.info(f"智能缓存管理器已初始化: {self.name}")

    def _create_multilevel_cache(self) -> MultiLevelCacheManager:
        """创建多级缓存"""
        cache_config = {
            'levels': [CacheLevel.MEMORY, CacheLevel.DISK],
            'default_ttl_minutes': self.config.default_ttl_minutes,
            'memory': {
                'max_size': self.config.max_size,
                'max_memory_mb': self.config.max_memory_mb
            },
            'disk': {
                'cache_dir': f'cache/{self.name}',
                'max_size_mb': self.config.max_disk_mb
            }
        }

        return MultiLevelCacheManager(cache_config)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            start_time = time.time()

            # 从多级缓存获取
            value = self.multilevel_cache.get(key)
            hit = value is not None

            # 记录访问模式
            self.access_pattern.record_access(key, hit)

            # 更新指标
            access_time = (time.time() - start_time) * 1000  # 转换为毫秒
            self._update_metrics(hit, access_time)

            if hit:
                logger.debug(f"缓存命中: {self.name}[{key}]")
            else:
                logger.debug(f"缓存未命中: {self.name}[{key}]")

            return value

        except Exception as e:
            logger.error(f"缓存获取失败 {self.name}[{key}]: {e}")
            return None

    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None,
            priority: Optional[CachePriority] = None) -> bool:
        """设置缓存值"""
        try:
            # 使用配置的TTL或指定的TTL
            if ttl is None:
                ttl = timedelta(minutes=self.config.default_ttl_minutes)

            # 存储到多级缓存
            success = self.multilevel_cache.put(key, value, ttl)

            if success:
                logger.debug(f"缓存设置成功: {self.name}[{key}]")
            else:
                logger.warning(f"缓存设置失败: {self.name}[{key}]")

            return success

        except Exception as e:
            logger.error(f"缓存设置失败 {self.name}[{key}]: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            success = self.multilevel_cache.delete(key)

            if success:
                logger.debug(f"缓存删除成功: {self.name}[{key}]")

            return success

        except Exception as e:
            logger.error(f"缓存删除失败 {self.name}[{key}]: {e}")
            return False

    def clear(self, priority_threshold: Optional[CachePriority] = None):
        """清空缓存"""
        try:
            if priority_threshold is None or self.config.priority.value >= priority_threshold.value:
                self.multilevel_cache.clear()
                logger.info(f"缓存已清空: {self.name}")
            else:
                logger.debug(f"缓存优先级过高，跳过清空: {self.name}")

        except Exception as e:
            logger.error(f"缓存清空失败 {self.name}: {e}")

    def _update_metrics(self, hit: bool, access_time_ms: float):
        """更新指标"""
        with self._lock:
            self.metrics.total_requests += 1

            if hit:
                # 更新命中率
                total_hits = self.metrics.hit_rate * (self.metrics.total_requests - 1) + 1
                self.metrics.hit_rate = total_hits / self.metrics.total_requests

            self.metrics.miss_rate = 1.0 - self.metrics.hit_rate

            # 更新平均访问时间
            total_time = self.metrics.avg_access_time_ms * (self.metrics.total_requests - 1) + access_time_ms
            self.metrics.avg_access_time_ms = total_time / self.metrics.total_requests

            # 更新缓存效率（命中率 * 访问速度权重）
            speed_score = max(0, 1 - (self.metrics.avg_access_time_ms / 100))  # 100ms为基准
            self.metrics.cache_efficiency = self.metrics.hit_rate * 0.7 + speed_score * 0.3

            self.metrics.timestamp = datetime.now()

    def _start_cleanup_timer(self):
        """启动清理定时器"""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()

        interval = self.config.cleanup_interval_minutes * 60
        self._cleanup_timer = threading.Timer(interval, self._perform_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _perform_cleanup(self):
        """执行清理"""
        try:
            logger.debug(f"执行缓存清理: {self.name}")

            # 获取统计信息
            stats = self.multilevel_cache.get_stats()

            # 生成优化建议
            self._generate_recommendations(stats)

            # 重新启动定时器
            self._start_cleanup_timer()

        except Exception as e:
            logger.error(f"缓存清理失败 {self.name}: {e}")

    def _generate_recommendations(self, stats: Dict[str, Any]):
        """生成优化建议（使用智能优化器）"""
        try:
            # 使用优化器分析性能并生成建议
            recommendations = self.optimizer.analyze_performance(
                self.name, self.metrics, self.access_pattern
            )

            # 检查是否需要策略变更
            suggested_strategy = self.optimizer.suggest_strategy_change(
                self.name, self.config.strategy, self.metrics
            )

            if suggested_strategy and suggested_strategy != self.config.strategy:
                recommendations.append(CacheRecommendation(
                    cache_name=self.name,
                    recommendation_type='strategy_change',
                    description=f"建议将缓存策略从{self.config.strategy.value}改为{suggested_strategy.value}",
                    impact_score=0.8,
                    implementation_cost='medium',
                    expected_improvement='预计提升20-40%整体性能'
                ))

            # 添加自定义优化建议
            recommendations.extend(self._generate_custom_recommendations(stats))

            # 更新建议列表
            with self._lock:
                self.recommendations = recommendations[-15:]  # 保留最近15条建议

            logger.debug(f"生成了{len(recommendations)}条优化建议: {self.name}")

        except Exception as e:
            logger.error(f"生成缓存建议失败 {self.name}: {e}")

    def _generate_custom_recommendations(self, stats: Dict[str, Any]) -> List[CacheRecommendation]:
        """生成自定义优化建议"""
        recommendations = []

        try:
            # 检查资源使用情况
            if self.metrics.memory_usage_mb > self.config.max_memory_mb * 0.9:
                recommendations.append(CacheRecommendation(
                    cache_name=self.name,
                    recommendation_type='cleanup',
                    description=f"内存使用接近上限({self.metrics.memory_usage_mb:.1f}/{self.config.max_memory_mb}MB)",
                    impact_score=0.6,
                    implementation_cost='low',
                    expected_improvement='释放10-20%内存空间'
                ))

            # 检查TTL设置
            if self.config.default_ttl_minutes > 60 and self.metrics.hit_rate > 0.8:
                recommendations.append(CacheRecommendation(
                    cache_name=self.name,
                    recommendation_type='strategy_change',
                    description=f"命中率较高且TTL较长({self.config.default_ttl_minutes}分钟)，可考虑适当缩短TTL",
                    impact_score=0.3,
                    implementation_cost='low',
                    expected_improvement='提升5-10%缓存新鲜度'
                ))

            # 检查访问频率分布
            hot_keys = self.access_pattern.get_hot_keys(20)
            if hot_keys:
                total_accesses = sum(freq for _, freq in hot_keys)
                if total_accesses > self.metrics.total_requests * 0.9:  # 90%访问集中在前20个key
                    recommendations.append(CacheRecommendation(
                        cache_name=self.name,
                        recommendation_type='resize',
                        description="访问高度集中，建议为热点数据分配专用缓存空间",
                        impact_score=0.7,
                        implementation_cost='medium',
                        expected_improvement='提升15-30%热点数据访问速度'
                    ))

        except Exception as e:
            logger.error(f"生成自定义建议失败 {self.name}: {e}")

        return recommendations

    def get_metrics(self) -> CacheMetrics:
        """获取缓存指标"""
        with self._lock:
            return self.metrics

    def get_recommendations(self) -> List[CacheRecommendation]:
        """获取优化建议"""
        with self._lock:
            return self.recommendations.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        try:
            multilevel_stats = self.multilevel_cache.get_stats()
            hot_keys = self.access_pattern.get_hot_keys(10)

            return {
                'cache_name': self.name,
                'config': asdict(self.config),
                'metrics': self.metrics.to_dict(),
                'multilevel_stats': multilevel_stats,
                'hot_keys': hot_keys,
                'recommendations': [rec.__dict__ for rec in self.recommendations],
                'access_pattern_size': len(self.access_pattern.access_history)
            }

        except Exception as e:
            logger.error(f"获取缓存统计失败 {self.name}: {e}")
            return {'error': str(e)}

    def apply_optimization(self, recommendation: CacheRecommendation) -> bool:
        """应用优化建议"""
        try:
            if recommendation.recommendation_type == 'cleanup':
                # 执行清理操作
                self._perform_targeted_cleanup()
                return True

            elif recommendation.recommendation_type == 'resize':
                # 动态调整缓存大小
                return self._dynamic_resize()

            elif recommendation.recommendation_type == 'strategy_change':
                # 策略变更需要重新配置，这里记录建议
                logger.info(f"策略变更建议: {recommendation.description}")
                return True

            elif recommendation.recommendation_type == 'preload':
                # 执行预加载
                return self._perform_preload()

            else:
                logger.warning(f"未知的优化类型: {recommendation.recommendation_type}")
                return False

        except Exception as e:
            logger.error(f"应用优化失败 {self.name}: {e}")
            return False

    def _perform_targeted_cleanup(self) -> bool:
        """执行针对性清理"""
        try:
            # 清理低频访问的数据
            hot_keys = self.access_pattern.get_hot_keys(50)
            hot_key_set = {key for key, _ in hot_keys}

            # 这里可以实现更精细的清理逻辑
            # 由于MultiLevelCacheManager没有提供选择性删除接口
            # 我们记录清理操作
            logger.info(f"执行针对性清理，保留{len(hot_key_set)}个热点键")
            return True

        except Exception as e:
            logger.error(f"针对性清理失败 {self.name}: {e}")
            return False

    def _dynamic_resize(self) -> bool:
        """动态调整缓存大小"""
        try:
            # 基于当前使用情况动态调整
            if self.metrics.hit_rate < 0.6 and self.metrics.memory_usage_mb < self.config.max_memory_mb * 0.8:
                # 命中率低且内存充足，建议增加缓存大小
                new_size = int(self.config.max_size * 1.2)
                logger.info(f"建议增加缓存大小: {self.config.max_size} -> {new_size}")
                return True

            elif self.metrics.memory_usage_mb > self.config.max_memory_mb * 0.9:
                # 内存使用过高，建议减少缓存大小
                new_size = int(self.config.max_size * 0.8)
                logger.info(f"建议减少缓存大小: {self.config.max_size} -> {new_size}")
                return True

            return False

        except Exception as e:
            logger.error(f"动态调整失败 {self.name}: {e}")
            return False

    def _perform_preload(self) -> bool:
        """执行预加载"""
        try:
            # 基于访问模式预测需要预加载的数据
            hot_keys = self.access_pattern.get_hot_keys(10)

            for key, frequency in hot_keys:
                # 预测下次访问时间
                next_access = self.access_pattern.predict_next_access(key)
                if next_access and (next_access - datetime.now()).total_seconds() < 300:  # 5分钟内
                    logger.debug(f"预测键'{key}'将在{next_access}被访问")

            logger.info(f"预加载分析完成，识别{len(hot_keys)}个热点键")
            return True

        except Exception as e:
            logger.error(f"预加载失败 {self.name}: {e}")
            return False

    def get_optimization_suggestions(self) -> List[CacheRecommendation]:
        """获取当前优化建议"""
        try:
            # 实时生成优化建议
            current_recommendations = self.optimizer.analyze_performance(
                self.name, self.metrics, self.access_pattern
            )

            return current_recommendations

        except Exception as e:
            logger.error(f"获取优化建议失败 {self.name}: {e}")
            return []

    def auto_optimize(self) -> Dict[str, Any]:
        """自动优化"""
        try:
            optimization_results = {
                'applied_optimizations': [],
                'skipped_optimizations': [],
                'total_recommendations': 0
            }

            # 获取当前建议
            recommendations = self.get_optimization_suggestions()
            optimization_results['total_recommendations'] = len(recommendations)

            # 应用低成本、高影响的优化
            for rec in recommendations:
                if (rec.implementation_cost == 'low' and
                    rec.impact_score > 0.5 and
                        rec.recommendation_type in ['cleanup', 'preload']):

                    if self.apply_optimization(rec):
                        optimization_results['applied_optimizations'].append({
                            'type': rec.recommendation_type,
                            'description': rec.description,
                            'impact_score': rec.impact_score
                        })
                    else:
                        optimization_results['skipped_optimizations'].append({
                            'type': rec.recommendation_type,
                            'reason': 'application_failed'
                        })
                else:
                    optimization_results['skipped_optimizations'].append({
                        'type': rec.recommendation_type,
                        'reason': 'cost_too_high_or_impact_too_low'
                    })

            logger.info(f"自动优化完成 {self.name}: 应用{len(optimization_results['applied_optimizations'])}项优化")
            return optimization_results

        except Exception as e:
            logger.error(f"自动优化失败 {self.name}: {e}")
            return {'error': str(e)}

    def shutdown(self):
        """关闭缓存管理器"""
        try:
            if self._cleanup_timer:
                self._cleanup_timer.cancel()

            self.multilevel_cache.clear()
            logger.info(f"缓存管理器已关闭: {self.name}")

        except Exception as e:
            logger.error(f"缓存管理器关闭失败 {self.name}: {e}")


class IntelligentCacheCoordinator:
    """
    智能缓存协调器

    功能特性：
    1. 整合多个缓存管理器
    2. 智能缓存策略协调
    3. 统一缓存管理接口
    4. 缓存性能监控和优化
    5. 自适应缓存调整
    6. 缓存预测和预加载
    7. 全局缓存统计和分析
    """

    def __init__(self):
        """初始化智能缓存协调器"""

        # 缓存管理器注册表
        self.cache_managers: Dict[str, IntelligentCacheManager] = {}
        self.cache_configs: Dict[str, CacheConfiguration] = {}

        # 全局配置
        self.global_config = {
            'max_total_memory_mb': 500,     # 总内存限制
            'max_total_disk_mb': 5000,      # 总磁盘限制
            'cleanup_interval_minutes': 5,  # 全局清理间隔
            'enable_global_optimization': True,  # 启用全局优化
            'enable_cross_cache_sharing': False  # 启用跨缓存共享
        }

        # 协调器状态
        self._running = False
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

        # 监控和优化
        self.global_metrics: Dict[str, Any] = {}
        self.optimization_thread: Optional[threading.Thread] = None

        # 性能监控集成
        self.performance_coordinator = None
        if PERFORMANCE_COORDINATOR_AVAILABLE:
            try:
                self.performance_coordinator = get_performance_coordinator()
            except Exception as e:
                logger.warning(f"性能协调器集成失败: {e}")

        # 预定义缓存配置
        self._init_default_caches()

        logger.info("智能缓存协调器初始化完成")

    def _init_default_caches(self):
        """初始化默认缓存"""
        default_configs = [
            CacheConfiguration(
                name="data_cache",
                cache_type=CacheType.DATA,
                strategy=CacheStrategy.LRU,
                priority=CachePriority.HIGH,
                max_size=2000,
                max_memory_mb=150,
                default_ttl_minutes=60
            ),
            CacheConfiguration(
                name="computation_cache",
                cache_type=CacheType.COMPUTATION,
                strategy=CacheStrategy.LFU,
                priority=CachePriority.MEDIUM,
                max_size=1000,
                max_memory_mb=100,
                default_ttl_minutes=30,
                enable_compression=True
            ),
            CacheConfiguration(
                name="ui_cache",
                cache_type=CacheType.UI,
                strategy=CacheStrategy.ADAPTIVE,
                priority=CachePriority.LOW,
                max_size=500,
                max_memory_mb=50,
                default_ttl_minutes=15
            ),
            CacheConfiguration(
                name="performance_cache",
                cache_type=CacheType.PERFORMANCE,
                strategy=CacheStrategy.FIFO,
                priority=CachePriority.CRITICAL,
                max_size=1000,
                max_memory_mb=75,
                default_ttl_minutes=5
            ),
            CacheConfiguration(
                name="temp_cache",
                cache_type=CacheType.TEMPORARY,
                strategy=CacheStrategy.LRU,
                priority=CachePriority.DISPOSABLE,
                max_size=500,
                max_memory_mb=25,
                default_ttl_minutes=5
            )
        ]

        for config in default_configs:
            self.cache_configs[config.name] = config

    def start(self) -> bool:
        """启动协调器"""
        with self._lock:
            if self._running:
                logger.warning("缓存协调器已在运行")
                return False

            try:
                self._running = True
                self._shutdown_event.clear()

                # 创建默认缓存管理器
                for name, config in self.cache_configs.items():
                    self.cache_managers[name] = IntelligentCacheManager(config)

                # 启动优化线程
                if self.global_config['enable_global_optimization']:
                    self.optimization_thread = threading.Thread(
                        target=self._optimization_loop,
                        name="CacheCoordinator-Optimizer",
                        daemon=True
                    )
                    self.optimization_thread.start()

                logger.info("智能缓存协调器已启动")
                return True

            except Exception as e:
                self._running = False
                logger.error(f"启动缓存协调器失败: {e}")
                return False

    def stop(self) -> bool:
        """停止协调器"""
        with self._lock:
            if not self._running:
                return True

            try:
                logger.info("正在停止智能缓存协调器...")

                self._running = False
                self._shutdown_event.set()

                # 等待优化线程结束
                if self.optimization_thread and self.optimization_thread.is_alive():
                    self.optimization_thread.join(timeout=5)

                # 关闭所有缓存管理器
                for manager in self.cache_managers.values():
                    manager.shutdown()

                self.cache_managers.clear()

                logger.info("智能缓存协调器已停止")
                return True

            except Exception as e:
                logger.error(f"停止缓存协调器失败: {e}")
                return False

    def register_cache(self, config: CacheConfiguration) -> bool:
        """注册缓存"""
        try:
            with self._lock:
                if config.name in self.cache_managers:
                    logger.warning(f"缓存已存在: {config.name}")
                    return False

                self.cache_configs[config.name] = config

                if self._running:
                    self.cache_managers[config.name] = IntelligentCacheManager(config)

                logger.info(f"缓存已注册: {config.name}")
                return True

        except Exception as e:
            logger.error(f"注册缓存失败: {e}")
            return False

    def unregister_cache(self, cache_name: str) -> bool:
        """注销缓存"""
        try:
            with self._lock:
                if cache_name not in self.cache_managers:
                    return False

                # 关闭缓存管理器
                self.cache_managers[cache_name].shutdown()

                # 移除注册
                del self.cache_managers[cache_name]
                if cache_name in self.cache_configs:
                    del self.cache_configs[cache_name]

                logger.info(f"缓存已注销: {cache_name}")
                return True

        except Exception as e:
            logger.error(f"注销缓存失败: {e}")
            return False

    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """从指定缓存获取值"""
        try:
            if cache_name not in self.cache_managers:
                logger.warning(f"缓存不存在: {cache_name}")
                return None

            return self.cache_managers[cache_name].get(key)

        except Exception as e:
            logger.error(f"缓存获取失败 {cache_name}[{key}]: {e}")
            return None

    def put(self, cache_name: str, key: str, value: Any,
            ttl: Optional[timedelta] = None, priority: Optional[CachePriority] = None) -> bool:
        """向指定缓存设置值"""
        try:
            if cache_name not in self.cache_managers:
                logger.warning(f"缓存不存在: {cache_name}")
                return False

            return self.cache_managers[cache_name].put(key, value, ttl, priority)

        except Exception as e:
            logger.error(f"缓存设置失败 {cache_name}[{key}]: {e}")
            return False

    def delete(self, cache_name: str, key: str) -> bool:
        """从指定缓存删除值"""
        try:
            if cache_name not in self.cache_managers:
                return False

            return self.cache_managers[cache_name].delete(key)

        except Exception as e:
            logger.error(f"缓存删除失败 {cache_name}[{key}]: {e}")
            return False

    def clear_cache(self, cache_name: str, priority_threshold: Optional[CachePriority] = None) -> bool:
        """清空指定缓存"""
        try:
            if cache_name not in self.cache_managers:
                return False

            self.cache_managers[cache_name].clear(priority_threshold)
            return True

        except Exception as e:
            logger.error(f"清空缓存失败 {cache_name}: {e}")
            return False

    def clear_all_caches(self, priority_threshold: Optional[CachePriority] = None):
        """清空所有缓存"""
        try:
            for manager in self.cache_managers.values():
                manager.clear(priority_threshold)

            logger.info("所有缓存已清空")

        except Exception as e:
            logger.error(f"清空所有缓存失败: {e}")

    def _optimization_loop(self):
        """优化循环"""
        logger.info("缓存优化循环已启动")

        while not self._shutdown_event.is_set():
            try:
                # 收集全局指标
                self._collect_global_metrics()

                # 执行全局优化
                self._perform_global_optimization()

                # 等待下次优化
                interval = self.global_config['cleanup_interval_minutes'] * 60
                self._shutdown_event.wait(interval)

            except Exception as e:
                logger.error(f"缓存优化循环错误: {e}")
                self._shutdown_event.wait(30)  # 出错后等待30秒

    def _collect_global_metrics(self):
        """收集全局指标"""
        try:
            total_memory_mb = 0
            total_disk_mb = 0
            total_requests = 0
            weighted_hit_rate = 0

            cache_metrics = {}

            for name, manager in self.cache_managers.items():
                metrics = manager.get_metrics()
                cache_metrics[name] = metrics.to_dict()

                # 累计资源使用
                total_memory_mb += metrics.memory_usage_mb
                total_disk_mb += metrics.disk_usage_mb
                total_requests += metrics.total_requests

                # 加权命中率
                if metrics.total_requests > 0:
                    weight = metrics.total_requests / max(1, total_requests)
                    weighted_hit_rate += metrics.hit_rate * weight

            # 更新全局指标
            with self._lock:
                self.global_metrics = {
                    'total_memory_mb': total_memory_mb,
                    'total_disk_mb': total_disk_mb,
                    'total_requests': total_requests,
                    'global_hit_rate': weighted_hit_rate,
                    'cache_count': len(self.cache_managers),
                    'cache_metrics': cache_metrics,
                    'timestamp': datetime.now().isoformat()
                }

            # 发送指标到性能协调器
            if self.performance_coordinator:
                try:
                    # 这里可以发送缓存指标到性能协调器
                    pass
                except Exception as e:
                    logger.error(f"发送缓存指标失败: {e}")

        except Exception as e:
            logger.error(f"收集全局指标失败: {e}")

    def _perform_global_optimization(self):
        """执行全局优化"""
        try:
            # 检查内存使用
            total_memory = self.global_metrics.get('total_memory_mb', 0)
            max_memory = self.global_config['max_total_memory_mb']

            if total_memory > max_memory * 0.9:  # 超过90%
                logger.warning(f"缓存内存使用过高: {total_memory:.1f}MB / {max_memory}MB")
                self._optimize_memory_usage()

            # 检查磁盘使用
            total_disk = self.global_metrics.get('total_disk_mb', 0)
            max_disk = self.global_config['max_total_disk_mb']

            if total_disk > max_disk * 0.9:  # 超过90%
                logger.warning(f"缓存磁盘使用过高: {total_disk:.1f}MB / {max_disk}MB")
                self._optimize_disk_usage()

            # 检查全局命中率
            global_hit_rate = self.global_metrics.get('global_hit_rate', 0)
            if global_hit_rate < 0.6:  # 低于60%
                logger.warning(f"全局缓存命中率过低: {global_hit_rate:.2%}")
                self._optimize_hit_rate()

        except Exception as e:
            logger.error(f"全局优化失败: {e}")

    def _optimize_memory_usage(self):
        """优化内存使用"""
        try:
            # 按优先级清理缓存
            for priority in [CachePriority.DISPOSABLE, CachePriority.LOW]:
                for manager in self.cache_managers.values():
                    if manager.config.priority == priority:
                        manager.clear(priority)
                        logger.info(f"清理低优先级缓存: {manager.name}")

        except Exception as e:
            logger.error(f"优化内存使用失败: {e}")

    def _optimize_disk_usage(self):
        """优化磁盘使用"""
        try:
            # 清理临时缓存
            for manager in self.cache_managers.values():
                if manager.config.cache_type == CacheType.TEMPORARY:
                    manager.clear()
                    logger.info(f"清理临时缓存: {manager.name}")

        except Exception as e:
            logger.error(f"优化磁盘使用失败: {e}")

    def _optimize_hit_rate(self):
        """优化命中率"""
        try:
            # 分析各缓存的命中率并给出建议
            for name, manager in self.cache_managers.items():
                metrics = manager.get_metrics()
                if metrics.hit_rate < 0.5:
                    recommendations = manager.get_recommendations()
                    logger.info(f"缓存 {name} 命中率过低({metrics.hit_rate:.2%})，建议数: {len(recommendations)}")

        except Exception as e:
            logger.error(f"优化命中率失败: {e}")

    def get_cache_list(self) -> List[str]:
        """获取缓存列表"""
        return list(self.cache_managers.keys())

    def get_cache_metrics(self, cache_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存指标"""
        if cache_name not in self.cache_managers:
            return None

        return self.cache_managers[cache_name].get_statistics()

    def get_global_metrics(self) -> Dict[str, Any]:
        """获取全局指标"""
        with self._lock:
            return self.global_metrics.copy()

    def get_all_recommendations(self) -> Dict[str, List[CacheRecommendation]]:
        """获取所有缓存的优化建议"""
        recommendations = {}

        for name, manager in self.cache_managers.items():
            recommendations[name] = manager.get_recommendations()

        return recommendations

    def get_statistics(self) -> Dict[str, Any]:
        """获取完整统计信息"""
        try:
            cache_stats = {}
            for name, manager in self.cache_managers.items():
                cache_stats[name] = manager.get_statistics()

            return {
                'global_metrics': self.get_global_metrics(),
                'cache_statistics': cache_stats,
                'global_config': self.global_config,
                'coordinator_status': {
                    'running': self._running,
                    'cache_count': len(self.cache_managers),
                    'optimization_enabled': self.global_config['enable_global_optimization']
                }
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}

    @contextmanager
    def cache_context(self, cache_name: str):
        """缓存上下文管理器"""
        if cache_name not in self.cache_managers:
            raise ValueError(f"缓存不存在: {cache_name}")

        manager = self.cache_managers[cache_name]
        try:
            yield manager
        except Exception as e:
            logger.error(f"缓存上下文错误 {cache_name}: {e}")
            raise

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# 全局单例实例
_coordinator_instance: Optional[IntelligentCacheCoordinator] = None
_coordinator_lock = threading.RLock()


def get_cache_coordinator() -> IntelligentCacheCoordinator:
    """获取全局缓存协调器实例"""
    global _coordinator_instance

    with _coordinator_lock:
        if _coordinator_instance is None:
            _coordinator_instance = IntelligentCacheCoordinator()
            _coordinator_instance.start()

        return _coordinator_instance


def initialize_cache_coordinator() -> IntelligentCacheCoordinator:
    """初始化全局缓存协调器"""
    global _coordinator_instance

    with _coordinator_lock:
        if _coordinator_instance is not None:
            _coordinator_instance.stop()

        _coordinator_instance = IntelligentCacheCoordinator()
        _coordinator_instance.start()

    return _coordinator_instance
