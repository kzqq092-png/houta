"""
数据源智能路由模块

实现高可用的数据源路由策略，包括健康检查、负载均衡、故障切换等功能。
基于Circuit Breaker模式设计，确保系统的稳定性和高可用性。

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import time
import threading
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import pandas as pd
from collections import defaultdict, deque

# 导入项目模块
from .plugin_types import AssetType, DataType
from .data_source_extensions import DataSourcePluginAdapter, HealthCheckResult

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """路由策略枚举"""
    PRIORITY = "priority"                    # 优先级路由
    ROUND_ROBIN = "round_robin"              # 轮询路由
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    HEALTH_BASED = "health_based"            # 基于健康状态路由
    LEAST_CONNECTIONS = "least_connections"  # 最少连接数路由
    RANDOM = "random"                        # 随机路由
    CIRCUIT_BREAKER = "circuit_breaker"      # 熔断器路由


class CircuitBreakerState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"        # 关闭状态，正常工作
    OPEN = "open"            # 开启状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，试探性请求


@dataclass
class DataSourceMetrics:
    """数据源性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    current_connections: int = 0
    health_score: float = 1.0        # 健康分数 0.0-1.0
    weight: float = 1.0              # 权重

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def failure_rate(self) -> float:
        """失败率"""
        return 1.0 - self.success_rate


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5           # 失败阈值
    failure_rate_threshold: float = 0.5  # 失败率阈值
    recovery_timeout_ms: int = 60000     # 恢复超时时间（毫秒）
    half_open_max_calls: int = 3         # 半开状态最大调用次数
    sliding_window_size: int = 10        # 滑动窗口大小
    timeout_ms: int = 5000               # 请求超时时间


@dataclass
class RoutingRequest:
    """路由请求"""
    asset_type: AssetType
    data_type: DataType
    symbol: str
    priority: int = 0
    timeout_ms: int = 5000
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IRoutingStrategy(ABC):
    """路由策略接口"""

    @abstractmethod
    def select_data_source(self,
                           available_sources: List[str],
                           request: RoutingRequest,
                           metrics: Dict[str, DataSourceMetrics]) -> Optional[str]:
        """
        选择数据源

        Args:
            available_sources: 可用数据源列表
            request: 路由请求
            metrics: 数据源指标

        Returns:
            选中的数据源ID，如果没有可用数据源则返回None
        """
        pass


class PriorityRoutingStrategy(IRoutingStrategy):
    """优先级路由策略"""

    def __init__(self, priorities: Dict[str, int]):
        """
        初始化优先级路由策略

        Args:
            priorities: 数据源优先级映射 {source_id: priority}，数字越小优先级越高
        """
        self.priorities = priorities

    def select_data_source(self,
                           available_sources: List[str],
                           request: RoutingRequest,
                           metrics: Dict[str, DataSourceMetrics]) -> Optional[str]:
        if not available_sources:
            return None

        # 按优先级排序，考虑健康状态
        sorted_sources = sorted(
            available_sources,
            key=lambda x: (
                self.priorities.get(x, 999),  # 优先级（越小越优先）
                -metrics.get(x, DataSourceMetrics()).health_score  # 健康分数（越大越好）
            )
        )

        return sorted_sources[0]


class RoundRobinRoutingStrategy(IRoutingStrategy):
    """轮询路由策略"""

    def __init__(self):
        self._current_index = 0
        self._lock = threading.Lock()

    def select_data_source(self,
                           available_sources: List[str],
                           request: RoutingRequest,
                           metrics: Dict[str, DataSourceMetrics]) -> Optional[str]:
        if not available_sources:
            return None

        with self._lock:
            # 过滤健康的数据源
            healthy_sources = [
                source for source in available_sources
                if metrics.get(source, DataSourceMetrics()).health_score > 0.5
            ]

            if not healthy_sources:
                healthy_sources = available_sources  # 如果没有健康的，使用所有可用的

            source = healthy_sources[self._current_index % len(healthy_sources)]
            self._current_index += 1
            return source


class WeightedRoundRobinRoutingStrategy(IRoutingStrategy):
    """加权轮询路由策略"""

    def __init__(self, weights: Dict[str, float]):
        """
        初始化加权轮询策略

        Args:
            weights: 数据源权重映射 {source_id: weight}
        """
        self.weights = weights
        self._current_weights = {}
        self._lock = threading.Lock()

    def select_data_source(self,
                           available_sources: List[str],
                           request: RoutingRequest,
                           metrics: Dict[str, DataSourceMetrics]) -> Optional[str]:
        if not available_sources:
            return None

        with self._lock:
            # 更新当前权重
            total_weight = 0
            for source in available_sources:
                weight = self.weights.get(source, 1.0)
                health_score = metrics.get(source, DataSourceMetrics()).health_score
                effective_weight = weight * health_score

                self._current_weights[source] = self._current_weights.get(source, 0) + effective_weight
                total_weight += effective_weight

            if total_weight == 0:
                return available_sources[0]

            # 选择当前权重最大的数据源
            selected = max(available_sources, key=lambda x: self._current_weights.get(x, 0))

            # 减少选中数据源的当前权重
            self._current_weights[selected] -= total_weight

            return selected


class HealthBasedRoutingStrategy(IRoutingStrategy):
    """基于健康状态的路由策略"""

    def select_data_source(self,
                           available_sources: List[str],
                           request: RoutingRequest,
                           metrics: Dict[str, DataSourceMetrics]) -> Optional[str]:
        if not available_sources:
            return None

        # 根据健康分数和响应时间选择最佳数据源
        def scoring_function(source_id: str) -> float:
            metric = metrics.get(source_id, DataSourceMetrics())
            # 综合健康分数、成功率和响应时间
            health_score = metric.health_score * 0.4
            success_rate_score = metric.success_rate * 0.4
            # 响应时间越低越好，转换为分数
            response_time_score = max(0, 1 - metric.avg_response_time_ms / 10000) * 0.2

            return health_score + success_rate_score + response_time_score

        return max(available_sources, key=scoring_function)


class CircuitBreaker:
    """熔断器实现"""

    def __init__(self, source_id: str, config: CircuitBreakerConfig):
        self.source_id = source_id
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.request_history = deque(maxlen=config.sliding_window_size)
        self._lock = threading.RLock()

    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            elif self.state == CircuitBreakerState.OPEN:
                # 检查是否应该进入半开状态
                if (self.last_failure_time and
                        (datetime.now() - self.last_failure_time).total_seconds() * 1000 > self.config.recovery_timeout_ms):
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"熔断器 {self.source_id} 进入半开状态")
                    return True
                return False
            else:  # HALF_OPEN
                return self.half_open_calls < self.config.half_open_max_calls

    def record_success(self):
        """记录成功请求"""
        with self._lock:
            self.request_history.append(True)

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls >= self.config.half_open_max_calls:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info(f"熔断器 {self.source_id} 恢复到关闭状态")

            self._update_failure_count()

    def record_failure(self):
        """记录失败请求"""
        with self._lock:
            self.request_history.append(False)
            self.last_failure_time = datetime.now()

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"熔断器 {self.source_id} 重新开启")

            self._update_failure_count()

            # 检查是否应该开启熔断器
            if (self.state == CircuitBreakerState.CLOSED and
                    self._should_trip()):
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"熔断器 {self.source_id} 开启，失败次数: {self.failure_count}")

    def _update_failure_count(self):
        """更新失败计数"""
        recent_failures = sum(1 for success in self.request_history if not success)
        self.failure_count = recent_failures

    def _should_trip(self) -> bool:
        """判断是否应该开启熔断器"""
        if len(self.request_history) < self.config.sliding_window_size:
            return False

        failure_rate = self.failure_count / len(self.request_history)
        return (self.failure_count >= self.config.failure_threshold or
                failure_rate >= self.config.failure_rate_threshold)


class DataSourceRouter:
    """
    数据源智能路由器

    实现多种路由策略，支持健康检查、负载均衡、故障切换等功能。
    基于Circuit Breaker模式确保系统高可用性。
    """

    def __init__(self,
                 default_strategy: RoutingStrategy = RoutingStrategy.PRIORITY,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 health_check_interval: int = 30):
        """
        初始化数据源路由器

        Args:
            default_strategy: 默认路由策略
            circuit_breaker_config: 熔断器配置
            health_check_interval: 健康检查间隔（秒）
        """
        self.default_strategy = default_strategy
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.health_check_interval = health_check_interval

        # 数据源管理
        self.data_sources: Dict[str, DataSourcePluginAdapter] = {}
        self.metrics: Dict[str, DataSourceMetrics] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # 路由策略
        self.routing_strategies: Dict[RoutingStrategy, IRoutingStrategy] = {}
        self._init_default_strategies()

        # 数据源优先级配置
        self.asset_priorities: Dict[AssetType, List[str]] = {}

        # 线程安全
        self._lock = threading.RLock()

        # 健康检查线程
        self._health_check_thread = None
        self._health_check_stop_event = threading.Event()

        # 事件回调
        self.on_source_health_changed: Optional[Callable[[str, bool], None]] = None
        self.on_routing_failed: Optional[Callable[[RoutingRequest, str], None]] = None

        logger.info("DataSourceRouter初始化完成")

    def _init_default_strategies(self):
        """初始化默认路由策略"""
        self.routing_strategies[RoutingStrategy.ROUND_ROBIN] = RoundRobinRoutingStrategy()
        self.routing_strategies[RoutingStrategy.HEALTH_BASED] = HealthBasedRoutingStrategy()

    def register_data_source(self,
                             source_id: str,
                             adapter: DataSourcePluginAdapter,
                             priority: int = 0,
                             weight: float = 1.0) -> bool:
        """
        注册数据源

        Args:
            source_id: 数据源ID
            adapter: 数据源适配器
            priority: 优先级（数字越小优先级越高）
            weight: 权重

        Returns:
            bool: 注册是否成功
        """
        try:
            with self._lock:
                if source_id in self.data_sources:
                    logger.warning(f"数据源 {source_id} 已存在，将被覆盖")

                self.data_sources[source_id] = adapter
                self.metrics[source_id] = DataSourceMetrics(weight=weight)
                self.circuit_breakers[source_id] = CircuitBreaker(source_id, self.circuit_breaker_config)

                # 创建优先级策略（如果不存在）
                if RoutingStrategy.PRIORITY not in self.routing_strategies:
                    priorities = {sid: 0 for sid in self.data_sources.keys()}
                    self.routing_strategies[RoutingStrategy.PRIORITY] = PriorityRoutingStrategy(priorities)

                # 创建加权轮询策略（如果不存在）
                if RoutingStrategy.WEIGHTED_ROUND_ROBIN not in self.routing_strategies:
                    weights = {sid: metrics.weight for sid, metrics in self.metrics.items()}
                    self.routing_strategies[RoutingStrategy.WEIGHTED_ROUND_ROBIN] = WeightedRoundRobinRoutingStrategy(weights)

                logger.info(f"数据源 {source_id} 注册成功，优先级: {priority}, 权重: {weight}")

                # 启动健康检查线程（如果尚未启动）
                if not self._health_check_thread or not self._health_check_thread.is_alive():
                    self._start_health_check()

                return True

        except Exception as e:
            logger.error(f"注册数据源 {source_id} 失败: {str(e)}")
            return False

    def unregister_data_source(self, source_id: str) -> bool:
        """
        注销数据源

        Args:
            source_id: 数据源ID

        Returns:
            bool: 注销是否成功
        """
        try:
            with self._lock:
                if source_id not in self.data_sources:
                    logger.warning(f"数据源 {source_id} 不存在")
                    return False

                # 移除数据源
                del self.data_sources[source_id]
                del self.metrics[source_id]
                del self.circuit_breakers[source_id]

                # 从优先级配置中移除
                for asset_type in self.asset_priorities:
                    if source_id in self.asset_priorities[asset_type]:
                        self.asset_priorities[asset_type].remove(source_id)

                logger.info(f"数据源 {source_id} 注销成功")
                return True

        except Exception as e:
            logger.error(f"注销数据源 {source_id} 失败: {str(e)}")
            return False

    def set_asset_priorities(self, asset_type: AssetType, priorities: List[str]) -> None:
        """
        设置资产类型的数据源优先级

        Args:
            asset_type: 资产类型
            priorities: 数据源ID列表，按优先级排序
        """
        with self._lock:
            # 验证数据源是否存在
            valid_priorities = [sid for sid in priorities if sid in self.data_sources]
            self.asset_priorities[asset_type] = valid_priorities

            # 更新优先级策略
            if RoutingStrategy.PRIORITY in self.routing_strategies:
                priority_map = {}
                for i, source_id in enumerate(valid_priorities):
                    priority_map[source_id] = i
                self.routing_strategies[RoutingStrategy.PRIORITY] = PriorityRoutingStrategy(priority_map)

            logger.info(f"设置 {asset_type.value} 数据源优先级: {valid_priorities}")

    def route_request(self,
                      request: RoutingRequest,
                      strategy: Optional[RoutingStrategy] = None) -> Optional[str]:
        """
        路由请求到合适的数据源

        Args:
            request: 路由请求
            strategy: 路由策略（可选，默认使用配置的策略）

        Returns:
            选中的数据源ID，如果没有可用数据源则返回None
        """
        try:
            with self._lock:
                # 获取支持该资产类型的数据源
                available_sources = self._get_available_sources(request.asset_type)

                if not available_sources:
                    logger.warning(f"没有支持 {request.asset_type.value} 的数据源")
                    return None

                # 过滤通过熔断器检查的数据源
                healthy_sources = [
                    source_id for source_id in available_sources
                    if self.circuit_breakers[source_id].can_execute()
                ]

                if not healthy_sources:
                    logger.warning(f"所有支持 {request.asset_type.value} 的数据源都不可用")
                    return None

                # 选择路由策略
                routing_strategy = strategy or self.default_strategy
                strategy_impl = self.routing_strategies.get(routing_strategy)

                if not strategy_impl:
                    # 回退到优先级策略
                    strategy_impl = self.routing_strategies.get(RoutingStrategy.PRIORITY)
                    if not strategy_impl:
                        # 简单选择第一个可用的
                        return healthy_sources[0]

                # 执行路由选择
                selected_source = strategy_impl.select_data_source(
                    healthy_sources, request, self.metrics
                )

                if selected_source:
                    logger.debug(f"路由策略 {routing_strategy.value} 选择数据源: {selected_source}")

                return selected_source

        except Exception as e:
            logger.error(f"路由请求失败: {str(e)}")
            if self.on_routing_failed:
                self.on_routing_failed(request, str(e))
            return None

    def record_request_result(self,
                              source_id: str,
                              success: bool,
                              response_time_ms: float = 0,
                              error: Optional[str] = None) -> None:
        """
        记录请求结果

        Args:
            source_id: 数据源ID
            success: 是否成功
            response_time_ms: 响应时间（毫秒）
            error: 错误信息（可选）
        """
        try:
            with self._lock:
                if source_id not in self.metrics:
                    return

                metrics = self.metrics[source_id]
                circuit_breaker = self.circuit_breakers[source_id]

                # 更新指标
                metrics.total_requests += 1
                metrics.last_request_time = datetime.now()

                if success:
                    metrics.successful_requests += 1
                    circuit_breaker.record_success()
                else:
                    metrics.failed_requests += 1
                    circuit_breaker.record_failure()
                    logger.warning(f"数据源 {source_id} 请求失败: {error}")

                # 更新平均响应时间
                if response_time_ms > 0:
                    current_avg = metrics.avg_response_time_ms
                    total_success = metrics.successful_requests
                    if total_success > 0:
                        metrics.avg_response_time_ms = (
                            (current_avg * (total_success - 1) + response_time_ms) / total_success
                        )

                # 更新健康分数
                self._update_health_score(source_id)

        except Exception as e:
            logger.error(f"记录请求结果失败: {str(e)}")

    def get_source_metrics(self, source_id: str) -> Optional[DataSourceMetrics]:
        """获取数据源指标"""
        with self._lock:
            return self.metrics.get(source_id)

    def get_all_metrics(self) -> Dict[str, DataSourceMetrics]:
        """获取所有数据源指标"""
        with self._lock:
            return self.metrics.copy()

    def get_circuit_breaker_state(self, source_id: str) -> Optional[CircuitBreakerState]:
        """获取熔断器状态"""
        with self._lock:
            circuit_breaker = self.circuit_breakers.get(source_id)
            return circuit_breaker.state if circuit_breaker else None

    def _get_available_sources(self, asset_type: AssetType) -> List[str]:
        """获取支持指定资产类型的数据源"""
        available = []

        # 首先尝试使用配置的优先级
        if asset_type in self.asset_priorities:
            available.extend(self.asset_priorities[asset_type])

        # 然后检查其他支持该资产类型的数据源
        for source_id, adapter in self.data_sources.items():
            if source_id not in available:
                try:
                    plugin_info = adapter.get_plugin_info()
                    if asset_type in plugin_info.supported_asset_types:
                        available.append(source_id)
                except Exception as e:
                    logger.error(f"检查数据源 {source_id} 支持的资产类型失败: {str(e)}")

        return available

    def _update_health_score(self, source_id: str) -> None:
        """更新健康分数"""
        metrics = self.metrics[source_id]
        circuit_breaker = self.circuit_breakers[source_id]

        # 基于成功率和熔断器状态计算健康分数
        success_rate_score = metrics.success_rate

        # 熔断器状态影响
        if circuit_breaker.state == CircuitBreakerState.OPEN:
            circuit_breaker_score = 0.0
        elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            circuit_breaker_score = 0.5
        else:
            circuit_breaker_score = 1.0

        # 响应时间影响（响应时间越短越好）
        response_time_score = max(0, 1 - metrics.avg_response_time_ms / 10000)

        # 综合计算健康分数
        metrics.health_score = (
            success_rate_score * 0.5 +
            circuit_breaker_score * 0.3 +
            response_time_score * 0.2
        )

    def _start_health_check(self) -> None:
        """启动健康检查线程"""
        if self._health_check_thread and self._health_check_thread.is_alive():
            return

        self._health_check_stop_event.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_worker,
            name="DataSourceRouter-HealthCheck",
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("健康检查线程已启动")

    def _health_check_worker(self) -> None:
        """健康检查工作线程"""
        while not self._health_check_stop_event.wait(self.health_check_interval):
            try:
                with self._lock:
                    for source_id, adapter in self.data_sources.items():
                        try:
                            # 执行健康检查
                            start_time = time.time()
                            health_result = adapter.health_check()
                            response_time = (time.time() - start_time) * 1000

                            # 记录结果
                            self.record_request_result(
                                source_id,
                                health_result.is_healthy,
                                response_time,
                                health_result.error_message
                            )

                            # 触发健康状态变化事件
                            if self.on_source_health_changed:
                                self.on_source_health_changed(source_id, health_result.is_healthy)

                        except Exception as e:
                            logger.error(f"数据源 {source_id} 健康检查失败: {str(e)}")
                            self.record_request_result(source_id, False, 0, str(e))

            except Exception as e:
                logger.error(f"健康检查工作线程异常: {str(e)}")

    def stop_health_check(self) -> None:
        """停止健康检查"""
        if self._health_check_thread:
            self._health_check_stop_event.set()
            self._health_check_thread.join(timeout=5)
            logger.info("健康检查线程已停止")

    def shutdown(self) -> None:
        """关闭路由器"""
        logger.info("DataSourceRouter正在关闭...")
        self.stop_health_check()

        with self._lock:
            self.data_sources.clear()
            self.metrics.clear()
            self.circuit_breakers.clear()

        logger.info("DataSourceRouter已关闭")


# 导出的公共接口
__all__ = [
    'DataSourceRouter',
    'RoutingStrategy',
    'CircuitBreakerState',
    'CircuitBreakerConfig',
    'RoutingRequest',
    'DataSourceMetrics',
    'IRoutingStrategy',
    'PriorityRoutingStrategy',
    'RoundRobinRoutingStrategy',
    'WeightedRoundRobinRoutingStrategy',
    'HealthBasedRoutingStrategy',
    'CircuitBreaker'
]
