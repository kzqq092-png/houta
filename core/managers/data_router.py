"""
数据路由器实现

本模块实现智能数据路由功能，根据请求特征和数据源性能选择最佳数据源。
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..interfaces.data_source import IDataSource, DataRequest, DataType

logger = logging.getLogger(__name__)


@dataclass
class RoutingRule:
    """路由规则"""

    name: str
    priority: int = 0

    # 匹配条件
    data_types: Optional[List[DataType]] = None
    symbols: Optional[List[str]] = None
    symbol_patterns: Optional[List[str]] = None

    # 目标数据源
    target_sources: List[str] = field(default_factory=list)

    # 条件表达式
    condition_expr: Optional[str] = None

    # 规则状态
    enabled: bool = True

    def matches(self, request: DataRequest) -> bool:
        """检查请求是否匹配此规则

        Args:
            request: 数据请求对象

        Returns:
            bool: 是否匹配
        """
        if not self.enabled:
            return False

        # 检查数据类型
        if self.data_types and request.data_type not in self.data_types:
            return False

        # 检查股票代码
        if self.symbols and request.symbol not in self.symbols:
            return False

        # 检查股票代码模式
        if self.symbol_patterns:
            import re
            matched = False
            for pattern in self.symbol_patterns:
                if re.match(pattern, request.symbol):
                    matched = True
                    break
            if not matched:
                return False

        # 检查条件表达式
        if self.condition_expr:
            try:
                # 创建安全的执行环境
                context = {
                    'request': request,
                    'symbol': request.symbol,
                    'data_type': request.data_type.value,
                    'frequency': request.frequency,
                    'start_time': request.start_time,
                    'end_time': request.end_time,
                    'limit': request.limit
                }

                # 执行条件表达式
                result = eval(self.condition_expr, {"__builtins__": {}}, context)
                return bool(result)

            except Exception as e:
                logger.warning(f"Failed to evaluate condition expression: {e}")
                return False

        return True


@dataclass
class DataSourceMetrics:
    """数据源性能指标"""

    name: str

    # 响应时间统计
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0

    # 成功率统计
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # 数据质量评分
    data_quality_score: float = 1.0

    # 最近更新时间
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0

    @property
    def failure_rate(self) -> float:
        """失败率"""
        return self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0

    def update_response_time(self, response_time: float) -> None:
        """更新响应时间统计

        Args:
            response_time: 响应时间(秒)
        """
        if self.total_requests == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (
                (self.avg_response_time * self.total_requests + response_time) /
                (self.total_requests + 1)
            )

        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        self.last_updated = datetime.now()

    def record_success(self, response_time: float) -> None:
        """记录成功请求

        Args:
            response_time: 响应时间(秒)
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.update_response_time(response_time)

    def record_failure(self, response_time: float = 0.0) -> None:
        """记录失败请求

        Args:
            response_time: 响应时间(秒)
        """
        self.total_requests += 1
        self.failed_requests += 1
        if response_time > 0:
            self.update_response_time(response_time)
        self.last_updated = datetime.now()

    def get_performance_score(self) -> float:
        """计算性能评分 (0-1)

        Returns:
            float: 性能评分
        """
        if self.total_requests == 0:
            return 1.0

        # 成功率权重 40%
        success_score = self.success_rate * 0.4

        # 响应时间权重 40% (假设1秒以内为满分)
        time_score = max(0, 1 - (self.avg_response_time - 1.0) * 0.1) * 0.4 if self.avg_response_time > 1.0 else 0.4

        # 数据质量权重 20%
        quality_score = self.data_quality_score * 0.2

        return success_score + time_score + quality_score


class DataRouter:
    """数据路由器

    根据路由规则和数据源性能选择最佳数据源。
    """

    def __init__(self):
        """初始化数据路由器"""
        self._data_sources: Dict[str, IDataSource] = {}
        self._routing_rules: List[RoutingRule] = []
        self._metrics: Dict[str, DataSourceMetrics] = {}
        self._default_source: Optional[str] = None
        self._initialized = False

        logger.info("DataRouter initialized")

    async def initialize(self) -> bool:
        """初始化路由器

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            return True

        try:
            # 加载默认路由规则
            await self._load_default_rules()

            self._initialized = True
            logger.info("DataRouter initialization completed")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize DataRouter: {e}")
            return False

    async def register_data_source(self, name: str, source: IDataSource) -> bool:
        """注册数据源

        Args:
            name: 数据源名称
            source: 数据源实例

        Returns:
            bool: 注册是否成功
        """
        if name in self._data_sources:
            logger.warning(f"Data source {name} already registered")
            return False

        self._data_sources[name] = source
        self._metrics[name] = DataSourceMetrics(name=name)

        # 如果是第一个数据源，设为默认
        if not self._default_source:
            self._default_source = name

        logger.info(f"Registered data source: {name}")
        return True

    async def unregister_data_source(self, name: str) -> bool:
        """注销数据源

        Args:
            name: 数据源名称

        Returns:
            bool: 注销是否成功
        """
        if name not in self._data_sources:
            logger.warning(f"Data source {name} not found")
            return False

        del self._data_sources[name]
        del self._metrics[name]

        # 如果删除的是默认数据源，选择新的默认数据源
        if self._default_source == name:
            self._default_source = next(iter(self._data_sources.keys()), None)

        logger.info(f"Unregistered data source: {name}")
        return True

    async def route(self, request: DataRequest) -> Optional[str]:
        """路由决策

        Args:
            request: 数据请求对象

        Returns:
            Optional[str]: 选中的数据源名称，无可用数据源时返回None
        """
        if not self._data_sources:
            logger.warning("No data sources available for routing")
            return None

        # 1. 应用路由规则
        matched_sources = []

        # 按优先级排序规则
        sorted_rules = sorted(self._routing_rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if rule.matches(request):
                # 检查目标数据源是否可用
                available_sources = [
                    source for source in rule.target_sources
                    if source in self._data_sources
                ]
                matched_sources.extend(available_sources)

                if matched_sources:
                    break  # 使用第一个匹配的规则

        # 2. 如果没有匹配的规则，使用所有可用数据源
        if not matched_sources:
            matched_sources = list(self._data_sources.keys())

        # 3. 如果只有一个数据源，直接返回
        if len(matched_sources) == 1:
            return matched_sources[0]

        # 4. 多个数据源时，选择最佳数据源
        return await self._select_best_source(matched_sources, request)

    async def get_alternative_sources(self, request: DataRequest) -> List[str]:
        """获取备选数据源列表

        Args:
            request: 数据请求对象

        Returns:
            List[str]: 备选数据源列表
        """
        all_sources = []

        # 收集所有匹配的数据源
        for rule in self._routing_rules:
            if rule.matches(request):
                available_sources = [
                    source for source in rule.target_sources
                    if source in self._data_sources
                ]
                all_sources.extend(available_sources)

        # 去重并按性能排序
        unique_sources = list(set(all_sources))

        if not unique_sources:
            unique_sources = list(self._data_sources.keys())

        # 按性能评分排序
        scored_sources = []
        for source_name in unique_sources:
            metrics = self._metrics.get(source_name)
            score = metrics.get_performance_score() if metrics else 0.0
            scored_sources.append((source_name, score))

        scored_sources.sort(key=lambda x: x[1], reverse=True)
        return [source for source, _ in scored_sources]

    async def add_routing_rule(self, rule: RoutingRule) -> bool:
        """添加路由规则

        Args:
            rule: 路由规则

        Returns:
            bool: 添加是否成功
        """
        # 检查规则名称是否重复
        if any(r.name == rule.name for r in self._routing_rules):
            logger.warning(f"Routing rule {rule.name} already exists")
            return False

        self._routing_rules.append(rule)
        logger.info(f"Added routing rule: {rule.name}")
        return True

    async def remove_routing_rule(self, rule_name: str) -> bool:
        """移除路由规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 移除是否成功
        """
        for i, rule in enumerate(self._routing_rules):
            if rule.name == rule_name:
                del self._routing_rules[i]
                logger.info(f"Removed routing rule: {rule_name}")
                return True

        logger.warning(f"Routing rule {rule_name} not found")
        return False

    async def update_metrics(self, source_name: str, response_time: float, success: bool) -> None:
        """更新数据源性能指标

        Args:
            source_name: 数据源名称
            response_time: 响应时间(秒)
            success: 是否成功
        """
        if source_name not in self._metrics:
            self._metrics[source_name] = DataSourceMetrics(name=source_name)

        metrics = self._metrics[source_name]

        if success:
            metrics.record_success(response_time)
        else:
            metrics.record_failure(response_time)

    async def get_metrics(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """获取性能指标

        Args:
            source_name: 数据源名称，None表示获取所有指标

        Returns:
            Dict[str, Any]: 性能指标
        """
        if source_name:
            if source_name not in self._metrics:
                return {}

            metrics = self._metrics[source_name]
            return {
                "name": metrics.name,
                "avg_response_time": metrics.avg_response_time,
                "success_rate": metrics.success_rate,
                "total_requests": metrics.total_requests,
                "performance_score": metrics.get_performance_score(),
                "last_updated": metrics.last_updated.isoformat()
            }
        else:
            return {
                name: {
                    "name": metrics.name,
                    "avg_response_time": metrics.avg_response_time,
                    "success_rate": metrics.success_rate,
                    "total_requests": metrics.total_requests,
                    "performance_score": metrics.get_performance_score(),
                    "last_updated": metrics.last_updated.isoformat()
                }
                for name, metrics in self._metrics.items()
            }

    async def _select_best_source(self, sources: List[str], request: DataRequest) -> str:
        """选择最佳数据源

        Args:
            sources: 候选数据源列表
            request: 数据请求对象

        Returns:
            str: 最佳数据源名称
        """
        if not sources:
            return self._default_source or ""

        if len(sources) == 1:
            return sources[0]

        # 计算每个数据源的综合评分
        scored_sources = []

        for source_name in sources:
            metrics = self._metrics.get(source_name)
            if not metrics:
                # 新数据源给予中等评分
                score = 0.5
            else:
                score = metrics.get_performance_score()

            scored_sources.append((source_name, score))

        # 按评分排序，选择最高分的
        scored_sources.sort(key=lambda x: x[1], reverse=True)

        best_source = scored_sources[0][0]
        logger.debug(f"Selected best source: {best_source} (score: {scored_sources[0][1]:.3f})")

        return best_source

    async def _load_default_rules(self) -> None:
        """加载默认路由规则"""
        # K线数据路由规则
        kline_rule = RoutingRule(
            name="kline_routing",
            priority=100,
            data_types=[DataType.HISTORICAL_KLINE],
            target_sources=["hikyuu", "eastmoney", "joinquant"]
        )

        # 实时数据路由规则
        tick_rule = RoutingRule(
            name="tick_routing",
            priority=90,
            data_types=[DataType.TICK_DATA],
            target_sources=["eastmoney", "hikyuu"]
        )

        # 财务数据路由规则
        financial_rule = RoutingRule(
            name="financial_routing",
            priority=80,
            data_types=[DataType.FINANCIAL],
            target_sources=["joinquant", "eastmoney"]
        )

        # 默认规则
        default_rule = RoutingRule(
            name="default_routing",
            priority=0,
            target_sources=list(self._data_sources.keys()) if self._data_sources else []
        )

        self._routing_rules = [kline_rule, tick_rule, financial_rule, default_rule]
        logger.info("Loaded default routing rules")
