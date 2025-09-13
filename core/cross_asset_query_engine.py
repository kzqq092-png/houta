"""
跨资产数据库统一查询引擎

提供统一的查询接口，支持跨越不同资产类型数据库的数据检索、聚合和分析。
实现高效的跨资产数据查询、联合查询、数据聚合等功能。

作者: FactorWeave-Quant团队
版本: 1.0
"""

import threading
from typing import Dict, Any, Optional, List, Union, Callable, Tuple, Set
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from loguru import logger
from .plugin_types import AssetType, DataType
from .asset_database_manager import get_asset_database_manager
from .asset_type_identifier import get_asset_type_identifier
from .data_router import DataSource

logger = logger.bind(module=__name__)


class QueryType(Enum):
    """查询类型枚举"""
    SINGLE_ASSET = "single_asset"           # 单资产查询
    MULTI_ASSET = "multi_asset"             # 多资产查询
    CROSS_ASSET = "cross_asset"             # 跨资产查询
    AGGREGATED = "aggregated"               # 聚合查询
    TIME_SERIES = "time_series"             # 时间序列查询
    STATISTICAL = "statistical"             # 统计查询


class AggregationType(Enum):
    """聚合类型枚举"""
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    MEDIAN = "median"
    STD = "std"
    VAR = "var"
    FIRST = "first"
    LAST = "last"


class SortOrder(Enum):
    """排序顺序枚举"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryFilter:
    """查询过滤器"""
    field: str
    operator: str  # =, !=, >, <, >=, <=, IN, NOT IN, LIKE, BETWEEN
    value: Any
    logic_operator: str = "AND"  # AND, OR

    def to_sql_condition(self) -> str:
        """转换为SQL条件"""
        if self.operator == "IN":
            if isinstance(self.value, (list, tuple)):
                values = "', '".join(str(v) for v in self.value)
                return f"{self.field} IN ('{values}')"
            else:
                return f"{self.field} IN ('{self.value}')"
        elif self.operator == "NOT IN":
            if isinstance(self.value, (list, tuple)):
                values = "', '".join(str(v) for v in self.value)
                return f"{self.field} NOT IN ('{values}')"
            else:
                return f"{self.field} NOT IN ('{self.value}')"
        elif self.operator == "LIKE":
            return f"{self.field} LIKE '{self.value}'"
        elif self.operator == "BETWEEN":
            if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                return f"{self.field} BETWEEN '{self.value[0]}' AND '{self.value[1]}'"
            else:
                raise ValueError("BETWEEN operator requires a list/tuple with 2 values")
        else:
            return f"{self.field} {self.operator} '{self.value}'"


@dataclass
class QuerySort:
    """查询排序"""
    field: str
    order: SortOrder = SortOrder.ASC

    def to_sql_order(self) -> str:
        """转换为SQL排序"""
        return f"{self.field} {self.order.value.upper()}"


@dataclass
class QueryAggregation:
    """查询聚合"""
    field: str
    aggregation_type: AggregationType
    alias: Optional[str] = None

    def to_sql_aggregation(self) -> str:
        """转换为SQL聚合"""
        agg_func = self.aggregation_type.value.upper()
        if agg_func == "AVG":
            agg_func = "AVG"
        elif agg_func == "STD":
            agg_func = "STDDEV"
        elif agg_func == "VAR":
            agg_func = "VARIANCE"

        sql_agg = f"{agg_func}({self.field})"
        if self.alias:
            sql_agg += f" AS {self.alias}"

        return sql_agg


@dataclass
class CrossAssetQueryRequest:
    """跨资产查询请求"""
    # 基本查询参数
    query_type: QueryType
    data_type: DataType
    symbols: Optional[List[str]] = None
    asset_types: Optional[List[AssetType]] = None

    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 查询字段
    fields: Optional[List[str]] = None

    # 过滤条件
    filters: List[QueryFilter] = field(default_factory=list)

    # 排序
    sort_by: List[QuerySort] = field(default_factory=list)

    # 聚合
    aggregations: List[QueryAggregation] = field(default_factory=list)
    group_by: Optional[List[str]] = None

    # 分页
    limit: Optional[int] = None
    offset: Optional[int] = 0

    # 其他选项
    distinct: bool = False
    include_metadata: bool = False
    parallel_execution: bool = True

    def validate(self) -> List[str]:
        """验证查询请求"""
        errors = []

        # 验证必要参数
        if not self.data_type:
            errors.append("data_type is required")

        # 验证时间范围
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors.append("start_date must be before end_date")

        # 验证聚合查询
        if self.aggregations and not self.group_by:
            # 如果有聚合但没有group_by，检查是否是全局聚合
            if self.query_type != QueryType.AGGREGATED:
                errors.append("Aggregations require group_by fields or AGGREGATED query type")

        # 验证分页参数
        if self.limit is not None and self.limit <= 0:
            errors.append("limit must be positive")

        if self.offset < 0:
            errors.append("offset must be non-negative")

        return errors


@dataclass
class QueryExecutionPlan:
    """查询执行计划"""
    request: CrossAssetQueryRequest
    asset_queries: Dict[AssetType, str]  # 每个资产类型的SQL查询
    execution_order: List[AssetType]
    estimated_cost: float
    parallel_execution: bool

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'query_type': self.request.query_type.value,
            'asset_queries': {asset.value: query for asset, query in self.asset_queries.items()},
            'execution_order': [asset.value for asset in self.execution_order],
            'estimated_cost': self.estimated_cost,
            'parallel_execution': self.parallel_execution
        }


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    total_records: int = 0
    affected_assets: List[AssetType] = field(default_factory=list)
    execution_plan: Optional[QueryExecutionPlan] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'success': self.success,
            'total_records': self.total_records,
            'execution_time_ms': self.execution_time_ms,
            'affected_assets': [asset.value for asset in self.affected_assets],
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }

        if self.execution_plan:
            result['execution_plan'] = self.execution_plan.to_dict()

        return result


class CrossAssetQueryEngine:
    """
    跨资产数据库统一查询引擎

    核心功能：
    1. 跨资产类型数据查询
    2. 多数据库联合查询
    3. 数据聚合和统计分析
    4. 查询优化和执行计划
    5. 并行查询执行
    """

    def __init__(self, max_workers: int = 4):
        """初始化跨资产查询引擎"""
        # 核心组件
        self.asset_db_manager = get_asset_database_manager()
        self.asset_type_identifier = get_asset_type_identifier()

        # 执行器
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 查询统计
        self._query_stats: Dict[str, Dict[str, Any]] = {}

        # 缓存
        self._query_cache: Dict[str, QueryResult] = {}
        self._cache_ttl_seconds = 300  # 5分钟缓存

        # 线程锁
        self._engine_lock = threading.RLock()

        logger.info("CrossAssetQueryEngine 初始化完成")

    def execute_query(self, request: CrossAssetQueryRequest) -> QueryResult:
        """
        执行跨资产查询

        Args:
            request: 查询请求

        Returns:
            查询结果
        """
        start_time = datetime.now()

        try:
            # 验证请求
            validation_errors = request.validate()
            if validation_errors:
                return QueryResult(
                    success=False,
                    errors=validation_errors,
                    execution_time_ms=0.0
                )

            # 检查缓存
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"返回缓存查询结果: {cache_key}")
                return cached_result

            # 生成执行计划
            execution_plan = self._generate_execution_plan(request)

            # 执行查询
            if request.parallel_execution and len(execution_plan.asset_queries) > 1:
                result = self._execute_parallel_query(execution_plan)
            else:
                result = self._execute_sequential_query(execution_plan)

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            result.execution_plan = execution_plan

            # 更新统计
            self._update_query_stats(request.query_type.value, True, execution_time)

            # 缓存结果
            self._cache_result(cache_key, result)

            logger.info(f"跨资产查询完成: {request.query_type.value}, {result.total_records} 条记录, {execution_time:.2f}ms")

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"跨资产查询失败: {e}")

            # 更新失败统计
            self._update_query_stats(request.query_type.value, False, execution_time)

            return QueryResult(
                success=False,
                errors=[str(e)],
                execution_time_ms=execution_time
            )

    def _generate_execution_plan(self, request: CrossAssetQueryRequest) -> QueryExecutionPlan:
        """生成查询执行计划"""
        asset_queries = {}
        execution_order = []
        estimated_cost = 0.0

        # 确定涉及的资产类型
        target_assets = self._determine_target_assets(request)

        # 为每个资产类型生成查询
        for asset_type in target_assets:
            sql_query = self._build_sql_query(request, asset_type)
            asset_queries[asset_type] = sql_query
            execution_order.append(asset_type)

            # 估算查询成本（简化版本）
            estimated_cost += self._estimate_query_cost(sql_query, asset_type)

        return QueryExecutionPlan(
            request=request,
            asset_queries=asset_queries,
            execution_order=execution_order,
            estimated_cost=estimated_cost,
            parallel_execution=request.parallel_execution and len(asset_queries) > 1
        )

    def _determine_target_assets(self, request: CrossAssetQueryRequest) -> List[AssetType]:
        """确定目标资产类型"""
        target_assets = []

        if request.asset_types:
            # 明确指定的资产类型
            target_assets = request.asset_types
        elif request.symbols:
            # 根据交易符号识别资产类型
            asset_types_set = set()
            for symbol in request.symbols:
                asset_type = self.asset_type_identifier.identify_asset_type_by_symbol(symbol)
                asset_types_set.add(asset_type)
            target_assets = list(asset_types_set)
        else:
            # 查询所有资产类型
            target_assets = list(AssetType)

        # 过滤掉没有数据库的资产类型
        available_assets = []
        for asset_type in target_assets:
            try:
                # 检查数据库是否存在
                if self.asset_db_manager.get_database_path(asset_type):
                    available_assets.append(asset_type)
            except Exception:
                continue

        return available_assets

    def _build_sql_query(self, request: CrossAssetQueryRequest, asset_type: AssetType) -> str:
        """构建SQL查询"""
        # 确定表名
        table_name = self._get_table_name(request.data_type)

        # 构建SELECT子句
        select_clause = self._build_select_clause(request)

        # 构建FROM子句
        from_clause = f"FROM {table_name}"

        # 构建WHERE子句
        where_clause = self._build_where_clause(request, asset_type)

        # 构建GROUP BY子句
        group_by_clause = self._build_group_by_clause(request)

        # 构建ORDER BY子句
        order_by_clause = self._build_order_by_clause(request)

        # 构建LIMIT子句
        limit_clause = self._build_limit_clause(request)

        # 组装完整查询
        query_parts = [f"SELECT {select_clause}", from_clause]

        if where_clause:
            query_parts.append(f"WHERE {where_clause}")

        if group_by_clause:
            query_parts.append(f"GROUP BY {group_by_clause}")

        if order_by_clause:
            query_parts.append(f"ORDER BY {order_by_clause}")

        if limit_clause:
            query_parts.append(limit_clause)

        return " ".join(query_parts)

    def _get_table_name(self, data_type: DataType) -> str:
        """获取表名"""
        table_mapping = {
            DataType.HISTORICAL_KLINE: "historical_kline_data",
            DataType.REAL_TIME_QUOTE: "real_time_quote_data",
            DataType.TRADE_TICK: "trade_tick_data",
            DataType.FUNDAMENTAL: "fundamental_data",
            DataType.TECHNICAL_INDICATORS: "technical_indicator_data"
        }

        return table_mapping.get(data_type, "historical_kline_data")

    def _build_select_clause(self, request: CrossAssetQueryRequest) -> str:
        """构建SELECT子句"""
        if request.aggregations:
            # 聚合查询
            select_parts = []

            # 添加GROUP BY字段
            if request.group_by:
                select_parts.extend(request.group_by)

            # 添加聚合字段
            for agg in request.aggregations:
                select_parts.append(agg.to_sql_aggregation())

            return ", ".join(select_parts)

        elif request.fields:
            # 指定字段
            if request.distinct:
                return f"DISTINCT {', '.join(request.fields)}"
            else:
                return ", ".join(request.fields)

        else:
            # 所有字段
            if request.distinct:
                return "DISTINCT *"
            else:
                return "*"

    def _build_where_clause(self, request: CrossAssetQueryRequest, asset_type: AssetType) -> str:
        """构建WHERE子句"""
        conditions = []

        # 时间范围条件
        if request.start_date:
            conditions.append(f"timestamp >= '{request.start_date}'")

        if request.end_date:
            conditions.append(f"timestamp <= '{request.end_date}'")

        # 交易符号条件
        if request.symbols:
            # 过滤属于当前资产类型的符号
            asset_symbols = []
            for symbol in request.symbols:
                symbol_asset_type = self.asset_type_identifier.identify_asset_type_by_symbol(symbol)
                if symbol_asset_type == asset_type:
                    asset_symbols.append(symbol)

            if asset_symbols:
                symbols_str = "', '".join(asset_symbols)
                conditions.append(f"symbol IN ('{symbols_str}')")

        # 自定义过滤条件
        for i, filter_obj in enumerate(request.filters):
            if i > 0:
                conditions.append(filter_obj.logic_operator)
            conditions.append(filter_obj.to_sql_condition())

        return " ".join(conditions) if conditions else ""

    def _build_group_by_clause(self, request: CrossAssetQueryRequest) -> str:
        """构建GROUP BY子句"""
        if request.group_by:
            return ", ".join(request.group_by)
        return ""

    def _build_order_by_clause(self, request: CrossAssetQueryRequest) -> str:
        """构建ORDER BY子句"""
        if request.sort_by:
            order_parts = [sort_obj.to_sql_order() for sort_obj in request.sort_by]
            return ", ".join(order_parts)
        return ""

    def _build_limit_clause(self, request: CrossAssetQueryRequest) -> str:
        """构建LIMIT子句"""
        if request.limit is not None:
            if request.offset > 0:
                return f"LIMIT {request.limit} OFFSET {request.offset}"
            else:
                return f"LIMIT {request.limit}"
        return ""

    def _estimate_query_cost(self, sql_query: str, asset_type: AssetType) -> float:
        """估算查询成本"""
        # 简化的成本估算
        base_cost = 1.0

        # 根据查询复杂度调整
        if "GROUP BY" in sql_query.upper():
            base_cost *= 2.0

        if "ORDER BY" in sql_query.upper():
            base_cost *= 1.5

        if "JOIN" in sql_query.upper():
            base_cost *= 3.0

        # 根据资产类型调整（某些资产类型数据量更大）
        asset_multiplier = {
            AssetType.STOCK_A: 1.0,
            AssetType.CRYPTO: 0.8,
            AssetType.FUTURES: 1.2,
            AssetType.INDEX: 0.6
        }

        return base_cost * asset_multiplier.get(asset_type, 1.0)

    def _execute_parallel_query(self, execution_plan: QueryExecutionPlan) -> QueryResult:
        """并行执行查询"""
        logger.debug(f"并行执行查询，涉及 {len(execution_plan.asset_queries)} 个资产类型")

        futures = {}
        results = []
        affected_assets = []

        # 提交并行任务
        for asset_type, sql_query in execution_plan.asset_queries.items():
            future = self.executor.submit(self._execute_single_asset_query, asset_type, sql_query)
            futures[future] = asset_type

        # 收集结果
        for future in as_completed(futures):
            asset_type = futures[future]
            try:
                asset_result = future.result()
                if asset_result is not None and not asset_result.empty:
                    # 添加资产类型标识
                    asset_result['asset_type'] = asset_type.value
                    results.append(asset_result)
                    affected_assets.append(asset_type)
            except Exception as e:
                logger.error(f"资产 {asset_type.value} 查询失败: {e}")

        # 合并结果
        if results:
            combined_data = pd.concat(results, ignore_index=True)
            return QueryResult(
                success=True,
                data=combined_data,
                total_records=len(combined_data),
                affected_assets=affected_assets
            )
        else:
            return QueryResult(
                success=True,
                data=pd.DataFrame(),
                total_records=0,
                affected_assets=affected_assets
            )

    def _execute_sequential_query(self, execution_plan: QueryExecutionPlan) -> QueryResult:
        """顺序执行查询"""
        logger.debug(f"顺序执行查询，涉及 {len(execution_plan.asset_queries)} 个资产类型")

        results = []
        affected_assets = []

        for asset_type in execution_plan.execution_order:
            sql_query = execution_plan.asset_queries[asset_type]
            try:
                asset_result = self._execute_single_asset_query(asset_type, sql_query)
                if asset_result is not None and not asset_result.empty:
                    # 添加资产类型标识
                    asset_result['asset_type'] = asset_type.value
                    results.append(asset_result)
                    affected_assets.append(asset_type)
            except Exception as e:
                logger.error(f"资产 {asset_type.value} 查询失败: {e}")

        # 合并结果
        if results:
            combined_data = pd.concat(results, ignore_index=True)
            return QueryResult(
                success=True,
                data=combined_data,
                total_records=len(combined_data),
                affected_assets=affected_assets
            )
        else:
            return QueryResult(
                success=True,
                data=pd.DataFrame(),
                total_records=0,
                affected_assets=affected_assets
            )

    def _execute_single_asset_query(self, asset_type: AssetType, sql_query: str) -> Optional[pd.DataFrame]:
        """执行单个资产的查询"""
        try:
            with self.asset_db_manager.get_connection(asset_type) as conn:
                result = conn.execute(sql_query).fetchall()

                if result:
                    # 获取列名
                    columns = [description[0] for description in conn.description]

                    # 创建DataFrame
                    df = pd.DataFrame(result, columns=columns)
                    return df
                else:
                    return pd.DataFrame()

        except Exception as e:
            logger.error(f"执行资产 {asset_type.value} 查询失败: {e}")
            logger.error(f"SQL: {sql_query}")
            raise

    def _generate_cache_key(self, request: CrossAssetQueryRequest) -> str:
        """生成缓存键"""
        # 简化的缓存键生成
        key_parts = [
            request.query_type.value,
            request.data_type.value,
            str(sorted(request.symbols) if request.symbols else ""),
            str(sorted([at.value for at in request.asset_types]) if request.asset_types else ""),
            str(request.start_date),
            str(request.end_date),
            str(sorted(request.fields) if request.fields else ""),
            str(request.limit),
            str(request.offset)
        ]

        return "|".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> Optional[QueryResult]:
        """获取缓存结果"""
        with self._engine_lock:
            if cache_key in self._query_cache:
                cached_result, timestamp = self._query_cache[cache_key]

                # 检查缓存是否过期
                if (datetime.now() - timestamp).total_seconds() < self._cache_ttl_seconds:
                    return cached_result
                else:
                    # 删除过期缓存
                    del self._query_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, result: QueryResult):
        """缓存查询结果"""
        with self._engine_lock:
            self._query_cache[cache_key] = (result, datetime.now())

            # 限制缓存大小
            if len(self._query_cache) > 100:
                # 删除最旧的缓存项
                oldest_key = min(self._query_cache.keys(),
                                 key=lambda k: self._query_cache[k][1])
                del self._query_cache[oldest_key]

    def _update_query_stats(self, query_type: str, success: bool, execution_time_ms: float):
        """更新查询统计"""
        with self._engine_lock:
            if query_type not in self._query_stats:
                self._query_stats[query_type] = {
                    'total_queries': 0,
                    'successful_queries': 0,
                    'failed_queries': 0,
                    'avg_execution_time_ms': 0.0,
                    'last_executed': None
                }

            stats = self._query_stats[query_type]
            stats['total_queries'] += 1

            if success:
                stats['successful_queries'] += 1

                # 更新平均执行时间（指数移动平均）
                alpha = 0.1
                stats['avg_execution_time_ms'] = (
                    alpha * execution_time_ms +
                    (1 - alpha) * stats['avg_execution_time_ms']
                )
            else:
                stats['failed_queries'] += 1

            stats['last_executed'] = datetime.now().isoformat()

    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        with self._engine_lock:
            return {
                'query_stats': dict(self._query_stats),
                'cache_size': len(self._query_cache),
                'cache_hit_rate': self._calculate_cache_hit_rate()
            }

    def _calculate_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        # 简化实现，实际应该跟踪缓存命中和未命中次数
        return 0.0

    def clear_cache(self):
        """清空查询缓存"""
        with self._engine_lock:
            self._query_cache.clear()
            logger.info("查询缓存已清空")

    def close(self):
        """关闭查询引擎"""
        self.executor.shutdown(wait=True)
        self.clear_cache()
        logger.info("CrossAssetQueryEngine 已关闭")


# 全局实例
_cross_asset_query_engine: Optional[CrossAssetQueryEngine] = None
_engine_lock = threading.Lock()


def get_cross_asset_query_engine() -> CrossAssetQueryEngine:
    """获取全局跨资产查询引擎实例"""
    global _cross_asset_query_engine

    with _engine_lock:
        if _cross_asset_query_engine is None:
            _cross_asset_query_engine = CrossAssetQueryEngine()

        return _cross_asset_query_engine


def initialize_cross_asset_query_engine(max_workers: int = 4) -> CrossAssetQueryEngine:
    """初始化跨资产查询引擎"""
    global _cross_asset_query_engine

    with _engine_lock:
        if _cross_asset_query_engine:
            _cross_asset_query_engine.close()

        _cross_asset_query_engine = CrossAssetQueryEngine(max_workers=max_workers)
        logger.info("CrossAssetQueryEngine 已初始化")

        return _cross_asset_query_engine
