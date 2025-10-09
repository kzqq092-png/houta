"""
TET路由引擎

实现智能的数据源插件路由和选择策略，支持多种路由算法：
- 健康优先策略
- 质量加权策略  
- 轮询策略
- 熔断器策略

作者: FactorWeave-Quant团队
版本: 1.0
日期: 2024-09-19
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import random

from loguru import logger
from core.plugin_types import AssetType, DataType

logger = logger.bind(module=__name__)

class RoutingStrategy(Enum):
    """路由策略枚举"""
    HEALTH_PRIORITY = "health_priority"      # 健康优先
    QUALITY_WEIGHTED = "quality_weighted"    # 质量加权
    ROUND_ROBIN = "round_robin"              # 轮询
    CIRCUIT_BREAKER = "circuit_breaker"      # 熔断器

class TETRouterEngine:
    """
    TET路由引擎 - 增强版

    Transform-Extract-Transform数据流的智能路由引擎，
    负责根据各种策略选择最优的数据源插件。

    增强功能：
    - 智能路由策略选择
    - 动态权重调整
    - 插件性能学习
    - 自适应负载均衡
    """

    def __init__(self, data_source_router=None, tet_pipeline=None):
        """
        初始化TET路由引擎

        Args:
            data_source_router: 数据源路由器（兼容性）
            tet_pipeline: TET数据管道（兼容性）
        """
        self.data_source_router = data_source_router
        self.tet_pipeline = tet_pipeline

        # 插件注册表
        self.registered_plugins: Dict[str, Any] = {}
        self.plugin_health: Dict[str, Dict[str, Any]] = {}

        # 插件性能历史记录
        self.plugin_performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.performance_window_size = 100  # 保留最近100次请求的性能数据

        # 路由策略配置 - 动态权重
        self.default_strategy = RoutingStrategy.HEALTH_PRIORITY
        self.strategy_weights = {
            RoutingStrategy.HEALTH_PRIORITY: 0.4,
            RoutingStrategy.QUALITY_WEIGHTED: 0.3,
            RoutingStrategy.ROUND_ROBIN: 0.2,
            RoutingStrategy.CIRCUIT_BREAKER: 0.1
        }

        # 自适应策略权重调整
        self.adaptive_weights_enabled = True
        self.strategy_performance: Dict[RoutingStrategy, Dict[str, float]] = {
            strategy: {'success_rate': 1.0, 'avg_response_time': 1.0, 'usage_count': 0}
            for strategy in RoutingStrategy
        }

        # 轮询状态 - 支持加权轮询
        self._round_robin_index = 0
        self._weighted_round_robin_state: Dict[str, int] = {}
        self._lock = threading.RLock()

        # 熔断器状态 - 增强配置
        self.circuit_breaker_thresholds = {
            'error_rate': 0.5,        # 错误率阈值
            'min_requests': 10,       # 最小请求数
            'timeout_seconds': 60,    # 熔断超时时间
            'half_open_requests': 3,  # 半开状态测试请求数
            'recovery_threshold': 0.8  # 恢复成功率阈值
        }

        # 插件负载均衡状态
        self.plugin_load_balancing: Dict[str, Dict[str, Any]] = {}

        # 智能路由配置
        self.intelligent_routing_enabled = True
        self.learning_rate = 0.1  # 性能学习率

        # 路由决策缓存
        self.routing_decision_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 缓存5分钟

        logger.info("TET路由引擎增强版初始化完成")

    def register_plugin(self, plugin_id: str, plugin: Any) -> bool:
        """
        注册插件到路由引擎

        Args:
            plugin_id: 插件ID
            plugin: 插件实例

        Returns:
            bool: 注册是否成功
        """
        try:
            with self._lock:
                self.registered_plugins[plugin_id] = plugin

                # 初始化插件健康状态
                self.plugin_health[plugin_id] = {
                    'status': 'healthy',
                    'last_check': datetime.now(),
                    'error_count': 0,
                    'total_requests': 0,
                    'success_requests': 0,
                    'avg_response_time': 0.0,
                    'circuit_breaker_until': None
                }

                logger.info(f"插件注册成功: {plugin_id}")
                return True

        except Exception as e:
            logger.error(f"插件注册失败 {plugin_id}: {e}")
            return False

    def select_optimal_plugin(self, available_plugins: List[str],
                              context, plugin_center) -> Optional[str]:
        """
        选择最优插件 - 增强版

        Args:
            available_plugins: 可用插件列表
            context: 请求上下文
            plugin_center: 插件中心实例

        Returns:
            Optional[str]: 选中的插件ID
        """
        if not available_plugins:
            return None

        if len(available_plugins) == 1:
            return available_plugins[0]

        try:
            # 检查路由决策缓存
            cache_key = self._generate_cache_key(available_plugins, context)
            cached_decision = self._get_cached_decision(cache_key)
            if cached_decision:
                return cached_decision

            # 智能路由策略选择
            if self.intelligent_routing_enabled:
                selected_plugin = self._intelligent_routing_strategy(available_plugins, context, plugin_center)
                if selected_plugin:
                    self._cache_routing_decision(cache_key, selected_plugin)
                    return selected_plugin

            # 传统策略选择
            strategy = self._select_strategy(context, available_plugins)

            # 执行相应的策略
            selected_plugin = None
            if strategy == RoutingStrategy.HEALTH_PRIORITY:
                selected_plugin = self._health_priority_strategy(available_plugins, context, plugin_center)
            elif strategy == RoutingStrategy.QUALITY_WEIGHTED:
                selected_plugin = self._quality_weighted_strategy(available_plugins, context, plugin_center)
            elif strategy == RoutingStrategy.ROUND_ROBIN:
                selected_plugin = self._round_robin_strategy(available_plugins, context, plugin_center)
            elif strategy == RoutingStrategy.CIRCUIT_BREAKER:
                selected_plugin = self._circuit_breaker_strategy(available_plugins, context, plugin_center)
            else:
                # 默认使用健康优先策略
                selected_plugin = self._health_priority_strategy(available_plugins, context, plugin_center)

            # 缓存决策结果
            if selected_plugin:
                self._cache_routing_decision(cache_key, selected_plugin)

            # 记录策略使用情况
            self._record_strategy_usage(strategy, selected_plugin is not None)

            return selected_plugin

        except Exception as e:
            logger.error(f"插件选择失败: {e}")
            # 失败时返回第一个可用插件
            return available_plugins[0]

    def _select_strategy(self, context, available_plugins: List[str]) -> RoutingStrategy:
        """
        根据上下文选择路由策略

        Args:
            context: 请求上下文
            available_plugins: 可用插件列表

        Returns:
            RoutingStrategy: 选择的策略
        """
        # 根据请求优先级和质量要求选择策略
        if hasattr(context, 'priority') and context.priority > 80:
            # 高优先级请求使用健康优先策略
            return RoutingStrategy.HEALTH_PRIORITY
        elif hasattr(context, 'quality_requirement') and context.quality_requirement > 0.9:
            # 高质量要求使用质量加权策略
            return RoutingStrategy.QUALITY_WEIGHTED
        elif len(available_plugins) > 3:
            # 插件较多时使用轮询策略均衡负载
            return RoutingStrategy.ROUND_ROBIN
        else:
            # 默认使用健康优先策略
            return RoutingStrategy.HEALTH_PRIORITY

    def _health_priority_strategy(self, available_plugins: List[str],
                                  context, plugin_center) -> Optional[str]:
        """健康优先策略"""
        best_plugin = None
        best_score = -1

        for plugin_id in available_plugins:
            score = self._calculate_health_score(plugin_id, plugin_center)

            # 考虑熔断器状态
            if self._is_circuit_breaker_open(plugin_id):
                score *= 0.1  # 熔断状态下大幅降低分数

            if score > best_score:
                best_score = score
                best_plugin = plugin_id

        return best_plugin

    def _quality_weighted_strategy(self, available_plugins: List[str],
                                   context, plugin_center) -> Optional[str]:
        """基于质量权重的策略"""
        # 计算每个插件的权重
        weights = []
        plugins = []

        for plugin_id in available_plugins:
            weight = 1.0  # 默认权重

            # 从plugin_center获取指标
            if hasattr(plugin_center, 'plugin_metrics') and plugin_id in plugin_center.plugin_metrics:
                metrics = plugin_center.plugin_metrics[plugin_id]
                weight = metrics.quality_score * metrics.availability_score

            # 考虑响应时间
            health = self.plugin_health.get(plugin_id, {})
            avg_response_time = health.get('avg_response_time', 1.0)
            if avg_response_time > 0:
                # 响应时间越短权重越高
                time_factor = 1.0 / (1.0 + avg_response_time)
                weight *= time_factor

            weights.append(weight)
            plugins.append(plugin_id)

        if not weights:
            return None

        # 加权随机选择
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(plugins)

        r = random.uniform(0, total_weight)
        cumulative_weight = 0

        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return plugins[i]

        return plugins[-1]

    def _round_robin_strategy(self, available_plugins: List[str],
                              context, plugin_center) -> Optional[str]:
        """轮询策略"""
        with self._lock:
            if available_plugins:
                plugin = available_plugins[self._round_robin_index % len(available_plugins)]
                self._round_robin_index += 1
                return plugin

        return None

    def _circuit_breaker_strategy(self, available_plugins: List[str],
                                  context, plugin_center) -> Optional[str]:
        """熔断器策略"""
        # 过滤掉熔断状态的插件
        healthy_plugins = []

        for plugin_id in available_plugins:
            if not self._is_circuit_breaker_open(plugin_id):
                # 检查错误率
                health = self.plugin_health.get(plugin_id, {})
                total_requests = health.get('total_requests', 0)
                success_requests = health.get('success_requests', 0)

                if total_requests >= self.circuit_breaker_thresholds['min_requests']:
                    error_rate = 1.0 - (success_requests / total_requests)
                    if error_rate < self.circuit_breaker_thresholds['error_rate']:
                        healthy_plugins.append(plugin_id)
                else:
                    # 请求数不足，给予机会
                    healthy_plugins.append(plugin_id)

        # 在健康的插件中使用健康优先策略
        if healthy_plugins:
            return self._health_priority_strategy(healthy_plugins, context, plugin_center)

        # 如果没有健康的插件，返回第一个可用的插件
        return available_plugins[0] if available_plugins else None

    def _calculate_health_score(self, plugin_id: str, plugin_center) -> float:
        """计算插件健康分数"""
        score = 1.0

        # 从plugin_center获取指标
        if hasattr(plugin_center, 'plugin_metrics') and plugin_id in plugin_center.plugin_metrics:
            metrics = plugin_center.plugin_metrics[plugin_id]

            # 基于成功率
            if metrics.total_requests > 0:
                success_rate = metrics.success_requests / metrics.total_requests
                score *= success_rate

            # 基于质量分数
            score *= metrics.quality_score

            # 基于可用性分数
            score *= metrics.availability_score

            # 基于响应时间（响应时间越短分数越高）
            if metrics.avg_response_time > 0:
                time_factor = 1.0 / (1.0 + metrics.avg_response_time)
                score *= time_factor

        # 从内部健康状态获取附加信息
        health = self.plugin_health.get(plugin_id, {})
        total_requests = health.get('total_requests', 0)
        success_requests = health.get('success_requests', 0)

        if total_requests > 0:
            success_rate = success_requests / total_requests
            score *= success_rate

        return max(0.0, min(1.0, score))  # 确保分数在0-1之间

    def _is_circuit_breaker_open(self, plugin_id: str) -> bool:
        """检查熔断器是否开启"""
        health = self.plugin_health.get(plugin_id, {})
        circuit_breaker_until = health.get('circuit_breaker_until')

        if circuit_breaker_until and datetime.now() < circuit_breaker_until:
            return True

        return False

    def update_plugin_health(self, plugin_id: str, success: bool,
                             response_time: float = 0.0) -> None:
        """
        更新插件健康状态

        Args:
            plugin_id: 插件ID
            success: 请求是否成功
            response_time: 响应时间
        """
        try:
            with self._lock:
                if plugin_id not in self.plugin_health:
                    self.plugin_health[plugin_id] = {
                        'status': 'healthy',
                        'last_check': datetime.now(),
                        'error_count': 0,
                        'total_requests': 0,
                        'success_requests': 0,
                        'avg_response_time': 0.0,
                        'circuit_breaker_until': None
                    }

                health = self.plugin_health[plugin_id]
                health['last_check'] = datetime.now()
                health['total_requests'] += 1

                if success:
                    health['success_requests'] += 1
                    health['error_count'] = max(0, health['error_count'] - 1)  # 成功时减少错误计数
                else:
                    health['error_count'] += 1

                # 更新平均响应时间
                if response_time > 0:
                    current_avg = health['avg_response_time']
                    total_requests = health['total_requests']
                    health['avg_response_time'] = (current_avg * (total_requests - 1) + response_time) / total_requests

                # 检查是否需要触发熔断器
                self._check_circuit_breaker(plugin_id, health)

        except Exception as e:
            logger.error(f"更新插件健康状态失败 {plugin_id}: {e}")

    def _check_circuit_breaker(self, plugin_id: str, health: Dict[str, Any]) -> None:
        """检查是否需要触发熔断器"""
        total_requests = health['total_requests']
        success_requests = health['success_requests']

        if total_requests >= self.circuit_breaker_thresholds['min_requests']:
            error_rate = 1.0 - (success_requests / total_requests)

            if error_rate >= self.circuit_breaker_thresholds['error_rate']:
                # 触发熔断器
                timeout_seconds = self.circuit_breaker_thresholds['timeout_seconds']
                health['circuit_breaker_until'] = datetime.now() + timedelta(seconds=timeout_seconds)
                health['status'] = 'circuit_breaker'

                logger.warning(f"插件 {plugin_id} 触发熔断器，错误率: {error_rate:.2%}")
            else:
                # 恢复正常状态
                health['circuit_breaker_until'] = None
                health['status'] = 'healthy'

    def get_plugin_status(self, plugin_id: str) -> Dict[str, Any]:
        """
        获取插件状态

        Args:
            plugin_id: 插件ID

        Returns:
            Dict[str, Any]: 插件状态信息
        """
        health = self.plugin_health.get(plugin_id, {})

        return {
            'plugin_id': plugin_id,
            'status': health.get('status', 'unknown'),
            'is_registered': plugin_id in self.registered_plugins,
            'is_circuit_breaker_open': self._is_circuit_breaker_open(plugin_id),
            'health_score': self._calculate_health_score(plugin_id, None),
            'total_requests': health.get('total_requests', 0),
            'success_requests': health.get('success_requests', 0),
            'error_count': health.get('error_count', 0),
            'avg_response_time': health.get('avg_response_time', 0.0),
            'last_check': health.get('last_check')
        }

    def get_all_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有插件状态

        Returns:
            Dict[str, Dict[str, Any]]: 所有插件状态
        """
        return {plugin_id: self.get_plugin_status(plugin_id)
                for plugin_id in self.registered_plugins.keys()}

    # ==================== 新增智能路由功能 ====================

    def _intelligent_routing_strategy(self, available_plugins: List[str],
                                      context, plugin_center) -> Optional[str]:
        """
        智能路由策略 - 基于机器学习的插件选择

        Args:
            available_plugins: 可用插件列表
            context: 请求上下文
            plugin_center: 插件中心实例

        Returns:
            Optional[str]: 选中的插件ID
        """
        try:
            # 计算每个插件的综合评分
            plugin_scores = {}

            for plugin_id in available_plugins:
                score = self._calculate_intelligent_score(plugin_id, context, plugin_center)
                plugin_scores[plugin_id] = score

            # 选择评分最高的插件
            if plugin_scores:
                best_plugin = max(plugin_scores.items(), key=lambda x: x[1])
                logger.debug(f"智能路由选择插件: {best_plugin[0]}, 评分: {best_plugin[1]:.3f}")
                return best_plugin[0]

        except Exception as e:
            logger.error(f"智能路由策略执行失败: {e}")

        return None

    def _calculate_intelligent_score(self, plugin_id: str, context, plugin_center) -> float:
        """
        计算插件的智能评分

        Args:
            plugin_id: 插件ID
            context: 请求上下文
            plugin_center: 插件中心实例

        Returns:
            float: 插件评分 (0.0-1.0)
        """
        score = 0.0

        try:
            # 1. 基础健康分数 (权重: 0.3)
            health_score = self._calculate_health_score(plugin_id, plugin_center)
            score += health_score * 0.3

            # 2. 历史性能分数 (权重: 0.25)
            performance_score = self._calculate_performance_score(plugin_id)
            score += performance_score * 0.25

            # 3. 负载均衡分数 (权重: 0.2)
            load_balance_score = self._calculate_load_balance_score(plugin_id, available_plugins=[plugin_id])
            score += load_balance_score * 0.2

            # 4. 上下文匹配分数 (权重: 0.15)
            context_score = self._calculate_context_match_score(plugin_id, context, plugin_center)
            score += context_score * 0.15

            # 5. 学习调整分数 (权重: 0.1)
            learning_score = self._calculate_learning_adjustment_score(plugin_id, context)
            score += learning_score * 0.1

        except Exception as e:
            logger.error(f"计算智能评分失败 {plugin_id}: {e}")
            score = 0.5  # 默认中等分数

        return max(0.0, min(1.0, score))

    def _calculate_performance_score(self, plugin_id: str) -> float:
        """计算插件历史性能分数"""
        if plugin_id not in self.plugin_performance_history:
            return 0.8  # 新插件给予较高初始分数

        history = self.plugin_performance_history[plugin_id]
        if not history:
            return 0.8

        # 计算最近性能指标
        recent_history = history[-20:]  # 最近20次请求

        success_count = sum(1 for record in recent_history if record.get('success', False))
        success_rate = success_count / len(recent_history)

        avg_response_time = sum(record.get('response_time', 1.0) for record in recent_history) / len(recent_history)
        time_score = max(0.0, 1.0 - avg_response_time / 10.0)  # 10秒为基准

        return (success_rate * 0.7 + time_score * 0.3)

    def _calculate_load_balance_score(self, plugin_id: str, available_plugins: List[str]) -> float:
        """计算负载均衡分数"""
        if plugin_id not in self.plugin_load_balancing:
            self.plugin_load_balancing[plugin_id] = {
                'current_load': 0,
                'last_used': datetime.now() - timedelta(hours=1)
            }

        plugin_load = self.plugin_load_balancing[plugin_id]
        current_load = plugin_load['current_load']

        # 计算所有插件的平均负载
        total_load = sum(
            self.plugin_load_balancing.get(pid, {}).get('current_load', 0)
            for pid in available_plugins
        )
        avg_load = total_load / len(available_plugins) if available_plugins else 0

        # 负载越低分数越高
        if avg_load == 0:
            return 1.0

        load_ratio = current_load / avg_load
        return max(0.0, 1.0 - load_ratio * 0.5)

    def _calculate_context_match_score(self, plugin_id: str, context, plugin_center) -> float:
        """计算上下文匹配分数"""
        score = 1.0

        try:
            # 检查插件能力匹配
            if hasattr(plugin_center, 'plugin_capabilities') and plugin_id in plugin_center.plugin_capabilities:
                capability = plugin_center.plugin_capabilities[plugin_id]

                # 检查资产类型匹配
                if hasattr(context, 'asset_type'):
                    if context.asset_type in capability.supported_asset_types:
                        score += 0.2
                    else:
                        score -= 0.3

                # 检查数据类型匹配
                if hasattr(context, 'data_type'):
                    if context.data_type in capability.supported_data_types:
                        score += 0.2
                    else:
                        score -= 0.3

            # 检查优先级匹配
            if hasattr(context, 'priority'):
                priority = context.priority
                if priority > 80:  # 高优先级
                    # 偏好高质量插件
                    health = self.plugin_health.get(plugin_id, {})
                    success_rate = health.get('success_requests', 0) / max(health.get('total_requests', 1), 1)
                    if success_rate > 0.95:
                        score += 0.1
                elif priority < 30:  # 低优先级
                    # 可以使用负载较高的插件
                    score += 0.05

        except Exception as e:
            logger.error(f"计算上下文匹配分数失败 {plugin_id}: {e}")

        return max(0.0, min(1.0, score))

    def _calculate_learning_adjustment_score(self, plugin_id: str, context) -> float:
        """计算学习调整分数"""
        # 基于历史决策的成功率进行调整
        adjustment = 0.0

        try:
            if plugin_id in self.plugin_performance_history:
                history = self.plugin_performance_history[plugin_id]
                if len(history) >= 10:
                    # 计算趋势
                    recent_10 = history[-10:]
                    older_10 = history[-20:-10] if len(history) >= 20 else []

                    if older_10:
                        recent_success_rate = sum(1 for r in recent_10 if r.get('success', False)) / len(recent_10)
                        older_success_rate = sum(1 for r in older_10 if r.get('success', False)) / len(older_10)

                        # 如果最近表现比之前好，给予奖励
                        trend = recent_success_rate - older_success_rate
                        adjustment = trend * self.learning_rate

        except Exception as e:
            logger.error(f"计算学习调整分数失败 {plugin_id}: {e}")

        return max(-0.2, min(0.2, adjustment))  # 限制调整范围

    def _generate_cache_key(self, available_plugins: List[str], context) -> str:
        """生成路由决策缓存键"""
        plugins_key = "_".join(sorted(available_plugins))
        context_key = ""

        if hasattr(context, 'asset_type'):
            context_key += f"asset_{context.asset_type.value}_"
        if hasattr(context, 'data_type'):
            context_key += f"data_{context.data_type.value}_"
        if hasattr(context, 'priority'):
            context_key += f"priority_{context.priority}_"

        return f"{plugins_key}_{context_key}"

    def _get_cached_decision(self, cache_key: str) -> Optional[str]:
        """获取缓存的路由决策"""
        if cache_key in self.routing_decision_cache:
            cached_data = self.routing_decision_cache[cache_key]
            cache_time = cached_data.get('timestamp', datetime.min)

            # 检查缓存是否过期
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_data.get('plugin_id')
            else:
                # 清理过期缓存
                del self.routing_decision_cache[cache_key]

        return None

    def _cache_routing_decision(self, cache_key: str, plugin_id: str) -> None:
        """缓存路由决策"""
        self.routing_decision_cache[cache_key] = {
            'plugin_id': plugin_id,
            'timestamp': datetime.now()
        }

        # 限制缓存大小
        if len(self.routing_decision_cache) > 1000:
            # 删除最旧的缓存项
            oldest_key = min(
                self.routing_decision_cache.keys(),
                key=lambda k: self.routing_decision_cache[k]['timestamp']
            )
            del self.routing_decision_cache[oldest_key]

    def _record_strategy_usage(self, strategy: RoutingStrategy, success: bool) -> None:
        """记录策略使用情况"""
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {
                'success_rate': 1.0, 'avg_response_time': 1.0, 'usage_count': 0
            }

        perf = self.strategy_performance[strategy]
        perf['usage_count'] += 1

        # 使用指数移动平均更新成功率
        alpha = 0.1
        current_success = 1.0 if success else 0.0
        perf['success_rate'] = alpha * current_success + (1 - alpha) * perf['success_rate']

    def record_plugin_performance(self, plugin_id: str, success: bool,
                                  response_time: float, context=None) -> None:
        """
        记录插件性能数据

        Args:
            plugin_id: 插件ID
            success: 是否成功
            response_time: 响应时间
            context: 请求上下文
        """
        try:
            # 更新基础健康状态
            self.update_plugin_health(plugin_id, success, response_time)

            # 记录详细性能历史
            if plugin_id not in self.plugin_performance_history:
                self.plugin_performance_history[plugin_id] = []

            performance_record = {
                'timestamp': datetime.now(),
                'success': success,
                'response_time': response_time,
                'context': {
                    'asset_type': getattr(context, 'asset_type', None),
                    'data_type': getattr(context, 'data_type', None),
                    'priority': getattr(context, 'priority', None)
                } if context else None
            }

            history = self.plugin_performance_history[plugin_id]
            history.append(performance_record)

            # 限制历史记录大小
            if len(history) > self.performance_window_size:
                history.pop(0)

            # 更新负载均衡状态
            if plugin_id not in self.plugin_load_balancing:
                self.plugin_load_balancing[plugin_id] = {'current_load': 0, 'last_used': datetime.now()}

            self.plugin_load_balancing[plugin_id]['last_used'] = datetime.now()

            # 根据响应时间调整当前负载
            if success:
                # 成功请求，负载逐渐减少
                self.plugin_load_balancing[plugin_id]['current_load'] = max(
                    0, self.plugin_load_balancing[plugin_id]['current_load'] - 1
                )
            else:
                # 失败请求，增加负载
                self.plugin_load_balancing[plugin_id]['current_load'] += 2

        except Exception as e:
            logger.error(f"记录插件性能数据失败 {plugin_id}: {e}")

    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        获取路由统计信息

        Returns:
            Dict[str, Any]: 路由统计信息
        """
        return {
            'registered_plugins': len(self.registered_plugins),
            'strategy_performance': self.strategy_performance.copy(),
            'cache_size': len(self.routing_decision_cache),
            'performance_history_size': {
                plugin_id: len(history)
                for plugin_id, history in self.plugin_performance_history.items()
            },
            'load_balancing_state': self.plugin_load_balancing.copy(),
            'intelligent_routing_enabled': self.intelligent_routing_enabled,
            'adaptive_weights_enabled': self.adaptive_weights_enabled
        }

    def optimize_routing_parameters(self) -> None:
        """
        优化路由参数 - 基于历史性能数据自动调整
        """
        try:
            if not self.adaptive_weights_enabled:
                return

            # 分析策略性能，调整权重
            total_usage = sum(perf['usage_count'] for perf in self.strategy_performance.values())

            if total_usage > 100:  # 有足够的数据进行优化
                for strategy, perf in self.strategy_performance.items():
                    if perf['usage_count'] > 10:
                        # 基于成功率调整权重
                        success_rate = perf['success_rate']
                        current_weight = self.strategy_weights.get(strategy, 0.25)

                        # 成功率高的策略增加权重
                        if success_rate > 0.9:
                            new_weight = min(0.6, current_weight * 1.1)
                        elif success_rate < 0.7:
                            new_weight = max(0.05, current_weight * 0.9)
                        else:
                            new_weight = current_weight

                        self.strategy_weights[strategy] = new_weight

                # 归一化权重
                total_weight = sum(self.strategy_weights.values())
                if total_weight > 0:
                    for strategy in self.strategy_weights:
                        self.strategy_weights[strategy] /= total_weight

                logger.info(f"路由参数优化完成，新权重: {self.strategy_weights}")

        except Exception as e:
            logger.error(f"路由参数优化失败: {e}")

    def enable_intelligent_routing(self, enabled: bool = True) -> None:
        """启用/禁用智能路由"""
        self.intelligent_routing_enabled = enabled
        logger.info(f"智能路由已{'启用' if enabled else '禁用'}")

    def enable_adaptive_weights(self, enabled: bool = True) -> None:
        """启用/禁用自适应权重调整"""
        self.adaptive_weights_enabled = enabled
        logger.info(f"自适应权重调整已{'启用' if enabled else '禁用'}")

    def clear_performance_history(self, plugin_id: Optional[str] = None) -> None:
        """清理性能历史记录"""
        if plugin_id:
            if plugin_id in self.plugin_performance_history:
                del self.plugin_performance_history[plugin_id]
                logger.info(f"已清理插件 {plugin_id} 的性能历史记录")
        else:
            self.plugin_performance_history.clear()
            logger.info("已清理所有插件的性能历史记录")

    def reset_routing_cache(self) -> None:
        """重置路由决策缓存"""
        self.routing_decision_cache.clear()
        logger.info("路由决策缓存已重置")
