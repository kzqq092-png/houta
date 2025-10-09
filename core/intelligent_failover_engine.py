#!/usr/bin/env python3
"""
智能故障转移引擎

实现基于机器学习的智能故障转移策略
作者: FactorWeave-Quant团队
版本: 2.0 (专业化优化版本)
"""

import asyncio
import time
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import statistics

from loguru import logger


class FailoverStrategy(Enum):
    """故障转移策略"""
    INTELLIGENT = "intelligent"  # 智能选择
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接
    FASTEST_RESPONSE = "fastest_response"  # 最快响应
    GEOGRAPHIC_AFFINITY = "geographic_affinity"  # 地理亲和性


class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 断开状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class PluginPerformanceMetrics:
    """插件性能指标"""
    plugin_id: str
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_breaker_open_time: Optional[datetime] = None
    geographic_region: Optional[str] = None
    current_load: int = 0
    capacity_score: float = 1.0
    reliability_score: float = 1.0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests

    @property
    def failure_rate(self) -> float:
        """失败率"""
        return 1.0 - self.success_rate


@dataclass
class FailoverContext:
    """故障转移上下文"""
    request_id: str
    data_type: str
    asset_type: str
    market: Optional[str] = None
    priority: int = 1  # 1-10, 10为最高优先级
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    preferred_regions: List[str] = field(default_factory=list)
    excluded_plugins: Set[str] = field(default_factory=set)
    start_time: datetime = field(default_factory=datetime.now)


@dataclass
class FailoverResult:
    """故障转移结果"""
    selected_plugin: str
    strategy_used: FailoverStrategy
    selection_time: float  # 选择耗时(毫秒)
    confidence_score: float  # 选择置信度 0.0-1.0
    backup_plugins: List[str] = field(default_factory=list)
    selection_reasons: List[str] = field(default_factory=list)


class IntelligentFailoverEngine:
    """智能故障转移引擎"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.plugin_metrics: Dict[str, PluginPerformanceMetrics] = {}

        # 配置参数
        self.circuit_breaker_failure_threshold = self.config.get('circuit_breaker_failure_threshold', 5)
        self.circuit_breaker_timeout = self.config.get('circuit_breaker_timeout', 60)  # 秒
        self.circuit_breaker_success_threshold = self.config.get('circuit_breaker_success_threshold', 3)

        # 权重配置
        self.strategy_weights = {
            'success_rate': 0.3,
            'response_time': 0.25,
            'current_load': 0.2,
            'reliability': 0.15,
            'geographic_affinity': 0.1
        }

        # 指数退避配置
        self.base_retry_delay = self.config.get('base_retry_delay', 1.0)  # 秒
        self.max_retry_delay = self.config.get('max_retry_delay', 30.0)  # 秒
        self.backoff_multiplier = self.config.get('backoff_multiplier', 2.0)

        # 学习参数
        self.learning_rate = self.config.get('learning_rate', 0.1)
        self.time_decay_factor = self.config.get('time_decay_factor', 0.95)

        logger.info("智能故障转移引擎初始化完成")

    async def select_optimal_plugin(
        self,
        available_plugins: List[str],
        context: FailoverContext,
        strategy: FailoverStrategy = FailoverStrategy.INTELLIGENT
    ) -> FailoverResult:
        """选择最优插件"""
        start_time = time.time()

        logger.info(f"开始智能插件选择 - 可用插件: {len(available_plugins)}, 策略: {strategy.value}")

        # 过滤掉被排除的插件
        filtered_plugins = [p for p in available_plugins if p not in context.excluded_plugins]

        if not filtered_plugins:
            raise RuntimeError("没有可用的插件进行选择")

        # 更新断路器状态
        await self._update_circuit_breakers()

        # 过滤掉断路器打开的插件
        healthy_plugins = [
            p for p in filtered_plugins
            if self._get_plugin_metrics(p).circuit_breaker_state != CircuitBreakerState.OPEN
        ]

        if not healthy_plugins:
            # 如果所有插件的断路器都打开了，尝试半开状态的插件
            half_open_plugins = [
                p for p in filtered_plugins
                if self._get_plugin_metrics(p).circuit_breaker_state == CircuitBreakerState.HALF_OPEN
            ]

            if half_open_plugins:
                healthy_plugins = half_open_plugins[:1]  # 只选择一个进行测试
                logger.warning(f" 所有插件断路器已打开，尝试半开状态插件: {healthy_plugins}")
            else:
                raise RuntimeError("所有插件的断路器都已打开，无法提供服务")

        # 根据策略选择插件
        if strategy == FailoverStrategy.INTELLIGENT:
            result = await self._intelligent_selection(healthy_plugins, context)
        elif strategy == FailoverStrategy.WEIGHTED_ROUND_ROBIN:
            result = await self._weighted_round_robin_selection(healthy_plugins, context)
        elif strategy == FailoverStrategy.LEAST_CONNECTIONS:
            result = await self._least_connections_selection(healthy_plugins, context)
        elif strategy == FailoverStrategy.FASTEST_RESPONSE:
            result = await self._fastest_response_selection(healthy_plugins, context)
        elif strategy == FailoverStrategy.GEOGRAPHIC_AFFINITY:
            result = await self._geographic_affinity_selection(healthy_plugins, context)
        else:
            result = await self._intelligent_selection(healthy_plugins, context)

        result.selection_time = (time.time() - start_time) * 1000
        result.strategy_used = strategy

        # 更新插件负载
        selected_metrics = self._get_plugin_metrics(result.selected_plugin)
        selected_metrics.current_load += 1

        logger.info(f"插件选择完成 - 选中: {result.selected_plugin}, "
                    f"置信度: {result.confidence_score:.3f}, 耗时: {result.selection_time:.1f}ms")

        return result

    async def _intelligent_selection(self, plugins: List[str], context: FailoverContext) -> FailoverResult:
        """智能选择算法"""
        plugin_scores = {}
        selection_reasons = []

        for plugin_id in plugins:
            metrics = self._get_plugin_metrics(plugin_id)

            # 计算各维度分数
            success_score = self._calculate_success_score(metrics)
            response_score = self._calculate_response_score(metrics)
            load_score = self._calculate_load_score(metrics)
            reliability_score = self._calculate_reliability_score(metrics)
            geographic_score = self._calculate_geographic_score(metrics, context)

            # 加权综合分数
            total_score = (
                success_score * self.strategy_weights['success_rate'] +
                response_score * self.strategy_weights['response_time'] +
                load_score * self.strategy_weights['current_load'] +
                reliability_score * self.strategy_weights['reliability'] +
                geographic_score * self.strategy_weights['geographic_affinity']
            )

            # 应用时间衰减
            time_factor = self._calculate_time_decay_factor(metrics)
            final_score = total_score * time_factor

            plugin_scores[plugin_id] = final_score

            logger.debug(f"插件 {plugin_id} 评分详情: "
                         f"成功率={success_score:.3f}, 响应时间={response_score:.3f}, "
                         f"负载={load_score:.3f}, 可靠性={reliability_score:.3f}, "
                         f"地理={geographic_score:.3f}, 时间衰减={time_factor:.3f}, "
                         f"最终分数={final_score:.3f}")

        # 选择最高分的插件
        sorted_plugins = sorted(plugin_scores.items(), key=lambda x: x[1], reverse=True)
        selected_plugin = sorted_plugins[0][0]
        confidence_score = sorted_plugins[0][1]

        # 准备备选插件列表
        backup_plugins = [plugin for plugin, _ in sorted_plugins[1:3]]  # 取前2个作为备选

        selection_reasons.append(f"综合评分最高: {confidence_score:.3f}")
        selection_reasons.append(f"成功率: {self._get_plugin_metrics(selected_plugin).success_rate:.2%}")

        return FailoverResult(
            selected_plugin=selected_plugin,
            strategy_used=FailoverStrategy.INTELLIGENT,
            selection_time=0.0,  # 将在外部设置
            confidence_score=confidence_score,
            backup_plugins=backup_plugins,
            selection_reasons=selection_reasons
        )

    async def _weighted_round_robin_selection(self, plugins: List[str], context: FailoverContext) -> FailoverResult:
        """加权轮询选择"""
        weights = []
        for plugin_id in plugins:
            metrics = self._get_plugin_metrics(plugin_id)
            # 基于成功率和响应时间计算权重
            weight = metrics.success_rate * (1.0 / max(0.001, metrics.avg_response_time))
            weights.append(weight)

        # 加权随机选择
        total_weight = sum(weights)
        if total_weight == 0:
            selected_plugin = random.choice(plugins)
        else:
            r = random.uniform(0, total_weight)
            cumulative_weight = 0
            selected_plugin = plugins[0]

            for i, weight in enumerate(weights):
                cumulative_weight += weight
                if r <= cumulative_weight:
                    selected_plugin = plugins[i]
                    break

        return FailoverResult(
            selected_plugin=selected_plugin,
            strategy_used=FailoverStrategy.WEIGHTED_ROUND_ROBIN,
            selection_time=0.0,
            confidence_score=0.8,
            backup_plugins=[p for p in plugins if p != selected_plugin][:2],
            selection_reasons=["加权轮询选择"]
        )

    async def _least_connections_selection(self, plugins: List[str], context: FailoverContext) -> FailoverResult:
        """最少连接选择"""
        min_load = float('inf')
        selected_plugin = plugins[0]

        for plugin_id in plugins:
            metrics = self._get_plugin_metrics(plugin_id)
            if metrics.current_load < min_load:
                min_load = metrics.current_load
                selected_plugin = plugin_id

        return FailoverResult(
            selected_plugin=selected_plugin,
            strategy_used=FailoverStrategy.LEAST_CONNECTIONS,
            selection_time=0.0,
            confidence_score=0.7,
            backup_plugins=[p for p in plugins if p != selected_plugin][:2],
            selection_reasons=[f"当前负载最低: {min_load}"]
        )

    async def _fastest_response_selection(self, plugins: List[str], context: FailoverContext) -> FailoverResult:
        """最快响应选择"""
        min_response_time = float('inf')
        selected_plugin = plugins[0]

        for plugin_id in plugins:
            metrics = self._get_plugin_metrics(plugin_id)
            if metrics.avg_response_time < min_response_time:
                min_response_time = metrics.avg_response_time
                selected_plugin = plugin_id

        return FailoverResult(
            selected_plugin=selected_plugin,
            strategy_used=FailoverStrategy.FASTEST_RESPONSE,
            selection_time=0.0,
            confidence_score=0.8,
            backup_plugins=[p for p in plugins if p != selected_plugin][:2],
            selection_reasons=[f"平均响应时间最快: {min_response_time:.3f}s"]
        )

    async def _geographic_affinity_selection(self, plugins: List[str], context: FailoverContext) -> FailoverResult:
        """地理亲和性选择"""
        if not context.preferred_regions:
            # 如果没有偏好地区，回退到智能选择
            return await self._intelligent_selection(plugins, context)

        # 按地理亲和性排序
        scored_plugins = []
        for plugin_id in plugins:
            metrics = self._get_plugin_metrics(plugin_id)
            geo_score = self._calculate_geographic_score(metrics, context)
            scored_plugins.append((plugin_id, geo_score))

        scored_plugins.sort(key=lambda x: x[1], reverse=True)
        selected_plugin = scored_plugins[0][0]

        return FailoverResult(
            selected_plugin=selected_plugin,
            strategy_used=FailoverStrategy.GEOGRAPHIC_AFFINITY,
            selection_time=0.0,
            confidence_score=scored_plugins[0][1],
            backup_plugins=[plugin for plugin, _ in scored_plugins[1:3]],
            selection_reasons=["地理位置最匹配"]
        )

    def _calculate_success_score(self, metrics: PluginPerformanceMetrics) -> float:
        """计算成功率分数"""
        base_score = metrics.success_rate

        # 考虑连续失败的惩罚
        if metrics.consecutive_failures > 0:
            penalty = min(0.5, metrics.consecutive_failures * 0.1)
            base_score *= (1.0 - penalty)

        # 考虑连续成功的奖励
        if metrics.consecutive_successes > 5:
            bonus = min(0.2, (metrics.consecutive_successes - 5) * 0.02)
            base_score = min(1.0, base_score + bonus)

        return base_score

    def _calculate_response_score(self, metrics: PluginPerformanceMetrics) -> float:
        """计算响应时间分数"""
        if metrics.avg_response_time <= 0:
            return 1.0

        # 响应时间越短分数越高，使用指数衰减
        # 1秒内为满分，10秒为0分
        return max(0.0, math.exp(-metrics.avg_response_time / 3.0))

    def _calculate_load_score(self, metrics: PluginPerformanceMetrics) -> float:
        """计算负载分数"""
        # 负载越低分数越高
        max_load = 100  # 假设最大负载为100
        load_ratio = min(1.0, metrics.current_load / max_load)
        return 1.0 - load_ratio

    def _calculate_reliability_score(self, metrics: PluginPerformanceMetrics) -> float:
        """计算可靠性分数"""
        base_score = metrics.reliability_score

        # 考虑最近的表现
        if metrics.last_failure_time:
            time_since_failure = (datetime.now() - metrics.last_failure_time).total_seconds()
            if time_since_failure < 300:  # 5分钟内有失败
                base_score *= 0.7
            elif time_since_failure < 3600:  # 1小时内有失败
                base_score *= 0.9

        return base_score

    def _calculate_geographic_score(self, metrics: PluginPerformanceMetrics, context: FailoverContext) -> float:
        """计算地理亲和性分数"""
        if not context.preferred_regions or not metrics.geographic_region:
            return 0.5  # 中性分数

        if metrics.geographic_region in context.preferred_regions:
            # 计算优先级权重
            region_index = context.preferred_regions.index(metrics.geographic_region)
            return 1.0 - (region_index * 0.2)  # 第一优先级1.0，第二0.8，以此类推

        return 0.1  # 不在偏好地区的低分

    def _calculate_time_decay_factor(self, metrics: PluginPerformanceMetrics) -> float:
        """计算时间衰减因子"""
        if not metrics.last_success_time:
            return 0.5

        time_since_success = (datetime.now() - metrics.last_success_time).total_seconds()
        # 1小时内为满分，24小时后衰减到50%
        decay_hours = 24
        decay_rate = time_since_success / (decay_hours * 3600)
        return max(0.5, 1.0 - (decay_rate * 0.5))

    async def _update_circuit_breakers(self):
        """更新断路器状态"""
        current_time = datetime.now()

        for plugin_id, metrics in self.plugin_metrics.items():
            if metrics.circuit_breaker_state == CircuitBreakerState.OPEN:
                # 检查是否可以转为半开状态
                if (metrics.circuit_breaker_open_time and
                        (current_time - metrics.circuit_breaker_open_time).total_seconds() >= self.circuit_breaker_timeout):
                    metrics.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"插件 {plugin_id} 断路器转为半开状态")

            elif metrics.circuit_breaker_state == CircuitBreakerState.CLOSED:
                # 检查是否需要打开断路器
                if metrics.consecutive_failures >= self.circuit_breaker_failure_threshold:
                    metrics.circuit_breaker_state = CircuitBreakerState.OPEN
                    metrics.circuit_breaker_open_time = current_time
                    logger.warning(f" 插件 {plugin_id} 断路器已打开 - 连续失败 {metrics.consecutive_failures} 次")

            elif metrics.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                # 检查是否可以关闭断路器
                if metrics.consecutive_successes >= self.circuit_breaker_success_threshold:
                    metrics.circuit_breaker_state = CircuitBreakerState.CLOSED
                    logger.info(f"插件 {plugin_id} 断路器已关闭 - 连续成功 {metrics.consecutive_successes} 次")

    def record_plugin_performance(self, plugin_id: str, success: bool, response_time: float, context: FailoverContext):
        """记录插件性能"""
        metrics = self._get_plugin_metrics(plugin_id)

        # 更新基础统计
        metrics.total_requests += 1
        if success:
            metrics.success_count += 1
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
            metrics.last_success_time = datetime.now()

            # 在半开状态下成功，可能关闭断路器
            if metrics.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                if metrics.consecutive_successes >= self.circuit_breaker_success_threshold:
                    metrics.circuit_breaker_state = CircuitBreakerState.CLOSED
                    logger.info(f"插件 {plugin_id} 断路器已关闭")
        else:
            metrics.failure_count += 1
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0
            metrics.last_failure_time = datetime.now()

            # 检查是否需要打开断路器
            if (metrics.circuit_breaker_state == CircuitBreakerState.CLOSED and
                    metrics.consecutive_failures >= self.circuit_breaker_failure_threshold):
                metrics.circuit_breaker_state = CircuitBreakerState.OPEN
                metrics.circuit_breaker_open_time = datetime.now()
                logger.warning(f" 插件 {plugin_id} 断路器已打开")

        # 更新平均响应时间（使用指数移动平均）
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            alpha = self.learning_rate
            metrics.avg_response_time = alpha * response_time + (1 - alpha) * metrics.avg_response_time

        # 更新可靠性分数
        self._update_reliability_score(metrics)

        # 减少当前负载
        metrics.current_load = max(0, metrics.current_load - 1)

        logger.debug(f" 插件 {plugin_id} 性能记录更新 - "
                     f"成功: {success}, 响应时间: {response_time:.3f}s, "
                     f"成功率: {metrics.success_rate:.2%}, 连续{'成功' if success else '失败'}: "
                     f"{metrics.consecutive_successes if success else metrics.consecutive_failures}")

    def _update_reliability_score(self, metrics: PluginPerformanceMetrics):
        """更新可靠性分数"""
        # 基于成功率和稳定性计算可靠性
        base_reliability = metrics.success_rate

        # 考虑连续失败的影响
        if metrics.consecutive_failures > 0:
            failure_penalty = min(0.5, metrics.consecutive_failures * 0.1)
            base_reliability *= (1.0 - failure_penalty)

        # 考虑历史稳定性
        if metrics.total_requests > 10:
            stability_bonus = min(0.2, (metrics.total_requests - 10) * 0.01)
            base_reliability = min(1.0, base_reliability + stability_bonus)

        metrics.reliability_score = base_reliability

    def _get_plugin_metrics(self, plugin_id: str) -> PluginPerformanceMetrics:
        """获取插件指标"""
        if plugin_id not in self.plugin_metrics:
            self.plugin_metrics[plugin_id] = PluginPerformanceMetrics(plugin_id=plugin_id)
        return self.plugin_metrics[plugin_id]

    def get_plugin_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件统计信息"""
        stats = {}
        for plugin_id, metrics in self.plugin_metrics.items():
            stats[plugin_id] = {
                'success_rate': metrics.success_rate,
                'failure_rate': metrics.failure_rate,
                'avg_response_time': metrics.avg_response_time,
                'total_requests': metrics.total_requests,
                'current_load': metrics.current_load,
                'circuit_breaker_state': metrics.circuit_breaker_state.value,
                'consecutive_failures': metrics.consecutive_failures,
                'consecutive_successes': metrics.consecutive_successes,
                'reliability_score': metrics.reliability_score
            }
        return stats

    def reset_plugin_metrics(self, plugin_id: str):
        """重置插件指标"""
        if plugin_id in self.plugin_metrics:
            del self.plugin_metrics[plugin_id]
            logger.info(f"插件 {plugin_id} 的性能指标已重置")

    def calculate_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟（指数退避）"""
        delay = self.base_retry_delay * (self.backoff_multiplier ** retry_count)
        # 添加随机抖动避免雷群效应
        jitter = random.uniform(0.1, 0.3) * delay
        final_delay = min(self.max_retry_delay, delay + jitter)
        return final_delay
