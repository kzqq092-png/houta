"""
资产感知统一数据管理器

扩展UnifiedDataManager，支持按资产类型分数据库的数据管理。
集成AssetSeparatedDatabaseManager和DataRouter，提供统一的数据访问接口。

作者: FactorWeave-Quant团队
版本: 1.0
"""

import threading
import time
from typing import Dict, Any, Optional, List, Callable, Set, Union, Tuple
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import asyncio
from asyncio import Future as AsyncioFuture
import numpy as np
import sqlite3
import os
import traceback

from loguru import logger
from ..events import EventBus, DataUpdateEvent
from ..containers import ServiceContainer, get_service_container
from ..plugin_types import AssetType, DataType
from ..tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData
from ..asset_database_manager import get_asset_database_manager, AssetDatabaseConfig
from ..data_router import get_data_router, DataRequest as RouteDataRequest, RouteStrategy
from .unified_data_manager import UnifiedDataManager, DataRequest

logger = logger.bind(module=__name__)


@dataclass
class AssetAwareDataRequest(DataRequest):
    """资产感知数据请求"""
    asset_type: Optional[AssetType] = None
    preferred_sources: Optional[List[str]] = None
    route_strategy: RouteStrategy = RouteStrategy.FASTEST
    enable_cross_asset_query: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_route_request(self) -> RouteDataRequest:
        """转换为路由请求"""
        # 映射数据类型
        data_type_mapping = {
            'stock_list': DataType.ASSET_LIST,
            'kline': DataType.HISTORICAL_KLINE,
            'real_time': DataType.REAL_TIME_QUOTE,
            'fundamental': DataType.FUNDAMENTAL,
            'news': DataType.NEWS
        }

        route_data_type = data_type_mapping.get(self.data_type, DataType.HISTORICAL_KLINE)

        return RouteDataRequest(
            symbol=self.symbol,
            data_type=route_data_type,
            start_date=self.time_range[0] if self.time_range else None,
            end_date=self.time_range[1] if self.time_range else None,
            frequency=self.parameters.get('frequency', '1d'),
            strategy=self.route_strategy,
            metadata=self.metadata
        )


class AssetAwareUnifiedDataManager(UnifiedDataManager):
    """
    资产感知统一数据管理器

    在UnifiedDataManager基础上扩展，支持：
    1. 按资产类型分数据库存储
    2. 智能数据源路由
    3. 跨资产类型数据查询
    4. 资产感知的缓存策略
    5. 数据质量管理
    """

    def __init__(self, service_container: ServiceContainer = None,
                 event_bus: EventBus = None, max_workers: int = 3,
                 asset_db_config: Optional[AssetDatabaseConfig] = None):
        """
        初始化资产感知统一数据管理器

        Args:
            service_container: 服务容器
            event_bus: 事件总线
            max_workers: 最大工作线程数
            asset_db_config: 资产数据库配置
        """
        # 调用父类初始化
        super().__init__(service_container, event_bus, max_workers)

        # 初始化资产感知组件
        self.asset_db_manager = get_asset_database_manager(asset_db_config)
        self.data_router = get_data_router()

        # 资产感知缓存
        self._asset_cache: Dict[AssetType, Dict[str, Any]] = {}
        self._asset_cache_timestamps: Dict[AssetType, Dict[str, float]] = {}
        self._asset_cache_lock = threading.RLock()

        # 跨资产查询支持
        self._cross_asset_queries: Dict[str, List[AssetType]] = {}
        self._cross_asset_lock = threading.RLock()

        # 数据质量管理
        self._quality_scores: Dict[str, Dict[str, float]] = {}
        self._quality_lock = threading.RLock()

        # 资产路由统计
        self._asset_route_stats: Dict[AssetType, Dict[str, Any]] = {}
        self._route_stats_lock = threading.RLock()

        logger.info("AssetAwareUnifiedDataManager 初始化完成")

    def get_asset_aware_data(self, request: AssetAwareDataRequest) -> Optional[Any]:
        """
        获取资产感知数据

        Args:
            request: 资产感知数据请求

        Returns:
            数据结果
        """
        try:
            # 生成请求键
            request_key = self._generate_asset_request_key(request)

            # 检查缓存
            cached_data = self._get_asset_cache(request, request_key)
            if cached_data is not None:
                logger.debug(f"使用缓存数据: {request.symbol}")
                return cached_data

            # 路由数据请求
            route_request = request.to_route_request()
            route_result = self.data_router.route_data_request(route_request)

            # 更新请求的资产类型信息
            if request.asset_type is None:
                request.asset_type = route_result.asset_type

            # 根据路由结果获取数据
            data = self._fetch_data_from_route(request, route_result)

            # 数据质量评估和存储
            if data is not None:
                quality_score = self._assess_data_quality(data, request)
                self._store_data_with_quality(data, request, route_result, quality_score)

                # 更新缓存
                self._set_asset_cache(request, request_key, data)

                # 更新路由统计
                self._update_route_statistics(request, route_result, quality_score)

            return data

        except Exception as e:
            logger.error(f"获取资产感知数据失败: {request.symbol}, {e}")
            return None

    def _generate_asset_request_key(self, request: AssetAwareDataRequest) -> str:
        """生成资产请求键"""
        key_parts = [
            str(request.asset_type.value) if request.asset_type else "auto",
            request.symbol,
            request.data_type,
            str(request.time_range) if request.time_range else "none",
            str(hash(frozenset(request.parameters.items()) if request.parameters else frozenset())),
            str(request.route_strategy.value)
        ]
        return "|".join(key_parts)

    def _get_asset_cache(self, request: AssetAwareDataRequest, cache_key: str) -> Optional[Any]:
        """获取资产缓存"""
        if not request.asset_type:
            return None

        with self._asset_cache_lock:
            asset_cache = self._asset_cache.get(request.asset_type, {})
            asset_timestamps = self._asset_cache_timestamps.get(request.asset_type, {})

            if cache_key in asset_cache and cache_key in asset_timestamps:
                # 检查缓存是否过期
                cache_age = time.time() - asset_timestamps[cache_key]
                if cache_age < self._cache_ttl:
                    return asset_cache[cache_key]
                else:
                    # 清除过期缓存
                    del asset_cache[cache_key]
                    del asset_timestamps[cache_key]

        return None

    def _set_asset_cache(self, request: AssetAwareDataRequest, cache_key: str, data: Any):
        """设置资产缓存"""
        if not request.asset_type:
            return

        with self._asset_cache_lock:
            if request.asset_type not in self._asset_cache:
                self._asset_cache[request.asset_type] = {}
                self._asset_cache_timestamps[request.asset_type] = {}

            self._asset_cache[request.asset_type][cache_key] = data
            self._asset_cache_timestamps[request.asset_type][cache_key] = time.time()

    def _fetch_data_from_route(self, request: AssetAwareDataRequest, route_result) -> Optional[Any]:
        """根据路由结果获取数据"""
        try:
            # 获取对应的数据库连接
            with self.asset_db_manager.get_connection(route_result.asset_type) as conn:
                # 根据数据类型执行不同的查询
                if request.data_type == 'kline':
                    return self._fetch_kline_data(conn, request, route_result)
                elif request.data_type == 'stock_list':
                    return self._fetch_stock_list(conn, request, route_result)
                elif request.data_type == 'real_time':
                    return self._fetch_realtime_data(conn, request, route_result)
                elif request.data_type == 'fundamental':
                    return self._fetch_fundamental_data(conn, request, route_result)
                else:
                    # 使用父类的通用方法
                    return super().get_data(request)

        except Exception as e:
            logger.error(f"从路由结果获取数据失败: {e}")
            # 降级到父类方法
            return super().get_data(request)

    def _fetch_kline_data(self, conn, request: AssetAwareDataRequest, route_result) -> Optional[pd.DataFrame]:
        """获取K线数据"""
        try:
            # 构建查询条件
            where_conditions = ["symbol = ?"]
            params = [request.symbol]

            # 添加时间范围条件
            if request.time_range:
                start_date, end_date = request.time_range
                if start_date:
                    where_conditions.append("timestamp >= ?")
                    params.append(start_date)
                if end_date:
                    where_conditions.append("timestamp <= ?")
                    params.append(end_date)

            # 添加数据源条件（使用路由结果的主要数据源）
            if route_result.primary_source:
                where_conditions.append("data_source = ?")
                params.append(route_result.primary_source.value)

            # 构建查询语句
            query = f"""
                SELECT timestamp, open, high, low, close, volume, amount, data_source, frequency
                FROM historical_kline_data
                WHERE {' AND '.join(where_conditions)}
                ORDER BY timestamp
            """

            # 执行查询
            result = conn.execute(query, params).fetchall()

            if result:
                # 转换为DataFrame
                columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount', 'data_source', 'frequency']
                df = pd.DataFrame(result, columns=columns)

                # 数据类型转换
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return None

    def _fetch_stock_list(self, conn, request: AssetAwareDataRequest, route_result) -> Optional[List[Dict[str, Any]]]:
        """获取股票列表"""
        try:
            # 查询该资产类型的所有股票
            query = """
                SELECT DISTINCT symbol, data_source
                FROM historical_kline_data
                ORDER BY symbol
            """

            result = conn.execute(query).fetchall()

            if result:
                return [{'symbol': row[0], 'data_source': row[1]} for row in result]
            else:
                return []

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return None

    def _fetch_realtime_data(self, conn, request: AssetAwareDataRequest, route_result) -> Optional[Dict[str, Any]]:
        """获取实时数据"""
        # 实时数据通常不存储在历史数据库中，需要调用实时数据源
        # 这里实现一个简单的最新数据查询
        try:
            query = """
                SELECT timestamp, open, high, low, close, volume, amount
                FROM historical_kline_data
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """

            result = conn.execute(query, [request.symbol]).fetchone()

            if result:
                return {
                    'symbol': request.symbol,
                    'timestamp': result[0],
                    'open': float(result[1]),
                    'high': float(result[2]),
                    'low': float(result[3]),
                    'close': float(result[4]),
                    'volume': int(result[5]),
                    'amount': float(result[6]),
                    'source': 'database'
                }
            else:
                return None

        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return None

    def _fetch_fundamental_data(self, conn, request: AssetAwareDataRequest, route_result) -> Optional[Dict[str, Any]]:
        """获取基本面数据"""
        # 基本面数据需要专门的表结构，这里返回模拟数据
        return {
            'symbol': request.symbol,
            'pe_ratio': 15.5,
            'pb_ratio': 2.1,
            'market_cap': 1000000000,
            'total_shares': 100000000,
            'source': 'simulated'
        }

    def _assess_data_quality(self, data: Any, request: AssetAwareDataRequest) -> float:
        """评估数据质量"""
        try:
            if isinstance(data, pd.DataFrame):
                # DataFrame质量评估
                if data.empty:
                    return 0.0

                # 基础质量指标
                completeness = 1.0 - data.isnull().sum().sum() / (data.shape[0] * data.shape[1])

                # 数据一致性检查（针对K线数据）
                consistency = 1.0
                if 'high' in data.columns and 'low' in data.columns and 'close' in data.columns:
                    # 检查高低价的合理性
                    invalid_rows = (data['high'] < data['low']).sum()
                    consistency = 1.0 - invalid_rows / len(data)

                # 综合质量分数
                quality_score = (completeness * 0.6 + consistency * 0.4)

            elif isinstance(data, (list, dict)):
                # 其他数据类型的简单质量评估
                if not data:
                    return 0.0
                quality_score = 0.8  # 默认质量分数
            else:
                quality_score = 0.5  # 未知类型的默认分数

            return max(0.0, min(1.0, quality_score))

        except Exception as e:
            logger.error(f"数据质量评估失败: {e}")
            return 0.5

    def _store_data_with_quality(self, data: Any, request: AssetAwareDataRequest,
                                 route_result, quality_score: float):
        """存储数据并记录质量信息"""
        try:
            with self._quality_lock:
                if request.symbol not in self._quality_scores:
                    self._quality_scores[request.symbol] = {}

                self._quality_scores[request.symbol][route_result.primary_source.value] = {
                    'quality_score': quality_score,
                    'timestamp': datetime.now().isoformat(),
                    'data_type': request.data_type,
                    'record_count': len(data) if hasattr(data, '__len__') else 1
                }

            # 如果数据质量较高，可以考虑存储到数据库
            if quality_score > 0.7 and isinstance(data, pd.DataFrame) and not data.empty:
                self._store_quality_data_to_db(data, request, route_result, quality_score)

        except Exception as e:
            logger.error(f"存储数据质量信息失败: {e}")

    def _store_quality_data_to_db(self, data: pd.DataFrame, request: AssetAwareDataRequest,
                                  route_result, quality_score: float):
        """将高质量数据存储到数据库"""
        try:
            if request.data_type == 'kline' and request.asset_type:
                with self.asset_db_manager.get_connection(request.asset_type) as conn:
                    # 记录数据质量监控信息
                    monitor_id = f"{request.symbol}_{route_result.primary_source.value}_{date.today().isoformat()}"

                    conn.execute("""
                        INSERT OR REPLACE INTO data_quality_monitor 
                        (monitor_id, symbol, data_source, check_date, quality_score, 
                         missing_count, completeness_score, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        monitor_id,
                        request.symbol,
                        route_result.primary_source.value,
                        date.today().isoformat(),
                        quality_score,
                        data.isnull().sum().sum(),
                        1.0 - data.isnull().sum().sum() / (data.shape[0] * data.shape[1]),
                        f"Records: {len(data)}, Columns: {list(data.columns)}"
                    ])

        except Exception as e:
            logger.error(f"存储质量数据到数据库失败: {e}")

    def _update_route_statistics(self, request: AssetAwareDataRequest, route_result, quality_score: float):
        """更新路由统计信息"""
        try:
            with self._route_stats_lock:
                asset_type = request.asset_type or route_result.asset_type

                if asset_type not in self._asset_route_stats:
                    self._asset_route_stats[asset_type] = {
                        'total_requests': 0,
                        'successful_requests': 0,
                        'average_quality': 0.0,
                        'source_usage': {},
                        'last_updated': datetime.now().isoformat()
                    }

                stats = self._asset_route_stats[asset_type]
                stats['total_requests'] += 1

                if quality_score > 0:
                    stats['successful_requests'] += 1

                    # 更新平均质量（指数移动平均）
                    alpha = 0.1
                    stats['average_quality'] = (
                        alpha * quality_score + (1 - alpha) * stats['average_quality']
                    )

                # 更新数据源使用统计
                source_name = route_result.primary_source.value
                if source_name not in stats['source_usage']:
                    stats['source_usage'][source_name] = 0
                stats['source_usage'][source_name] += 1

                stats['last_updated'] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"更新路由统计失败: {e}")

    def get_cross_asset_data(self, symbols: List[str], data_type: str = 'kline',
                             time_range: Optional[Tuple] = None,
                             **kwargs) -> Dict[AssetType, Any]:
        """
        获取跨资产类型数据

        Args:
            symbols: 交易符号列表
            data_type: 数据类型
            time_range: 时间范围
            **kwargs: 其他参数

        Returns:
            按资产类型分组的数据字典
        """
        result = {}

        try:
            # 按资产类型分组符号
            asset_groups = {}
            for symbol in symbols:
                asset_type = self.asset_db_manager.asset_identifier.identify_asset_type_by_symbol(symbol)
                if asset_type not in asset_groups:
                    asset_groups[asset_type] = []
                asset_groups[asset_type].append(symbol)

            # 并发获取各资产类型的数据
            with ThreadPoolExecutor(max_workers=len(asset_groups)) as executor:
                futures = {}

                for asset_type, asset_symbols in asset_groups.items():
                    future = executor.submit(
                        self._get_asset_group_data,
                        asset_type, asset_symbols, data_type, time_range, kwargs
                    )
                    futures[future] = asset_type

                # 收集结果
                for future in futures:
                    asset_type = futures[future]
                    try:
                        asset_data = future.result(timeout=30)
                        if asset_data:
                            result[asset_type] = asset_data
                    except Exception as e:
                        logger.error(f"获取{asset_type.value}数据失败: {e}")

            return result

        except Exception as e:
            logger.error(f"获取跨资产数据失败: {e}")
            return {}

    def _get_asset_group_data(self, asset_type: AssetType, symbols: List[str],
                              data_type: str, time_range: Optional[Tuple], kwargs: Dict) -> Optional[Any]:
        """获取特定资产类型的数据组"""
        try:
            group_data = {}

            for symbol in symbols:
                request = AssetAwareDataRequest(
                    request_id=f"cross_asset_{symbol}_{int(time.time())}",
                    symbol=symbol,
                    data_type=data_type,
                    time_range=time_range,
                    parameters=kwargs,
                    asset_type=asset_type,
                    enable_cross_asset_query=True
                )

                data = self.get_asset_aware_data(request)
                if data is not None:
                    group_data[symbol] = data

            return group_data if group_data else None

        except Exception as e:
            logger.error(f"获取{asset_type.value}组数据失败: {e}")
            return None

    def get_asset_statistics(self) -> Dict[str, Any]:
        """获取资产数据统计信息"""
        try:
            # 获取数据库统计
            db_stats = self.asset_db_manager.get_database_statistics()

            # 获取路由统计
            route_stats = self.data_router.get_route_statistics()

            # 获取数据源状态
            source_status = self.data_router.get_data_sources_status()

            # 获取资产路由统计
            with self._route_stats_lock:
                asset_route_stats = dict(self._asset_route_stats)

            # 获取质量统计
            with self._quality_lock:
                quality_stats = {
                    'symbols_monitored': len(self._quality_scores),
                    'average_quality': 0.0,
                    'quality_distribution': {}
                }

                if self._quality_scores:
                    all_scores = []
                    for symbol_scores in self._quality_scores.values():
                        for source_quality in symbol_scores.values():
                            all_scores.append(source_quality['quality_score'])

                    if all_scores:
                        quality_stats['average_quality'] = sum(all_scores) / len(all_scores)

                        # 质量分布
                        for score in all_scores:
                            if score >= 0.8:
                                quality_stats['quality_distribution']['high'] = quality_stats['quality_distribution'].get('high', 0) + 1
                            elif score >= 0.6:
                                quality_stats['quality_distribution']['medium'] = quality_stats['quality_distribution'].get('medium', 0) + 1
                            else:
                                quality_stats['quality_distribution']['low'] = quality_stats['quality_distribution'].get('low', 0) + 1

            return {
                'database_statistics': db_stats,
                'route_statistics': route_stats,
                'data_source_status': source_status,
                'asset_route_statistics': asset_route_stats,
                'data_quality_statistics': quality_stats,
                'cache_statistics': {
                    'asset_cache_size': sum(len(cache) for cache in self._asset_cache.values()),
                    'total_cache_size': len(self._data_cache) + sum(len(cache) for cache in self._asset_cache.values())
                }
            }

        except Exception as e:
            logger.error(f"获取资产统计信息失败: {e}")
            return {}

    def clear_asset_cache(self, asset_type: Optional[AssetType] = None):
        """清除资产缓存"""
        with self._asset_cache_lock:
            if asset_type:
                # 清除特定资产类型的缓存
                self._asset_cache.pop(asset_type, None)
                self._asset_cache_timestamps.pop(asset_type, None)
                logger.info(f"已清除{asset_type.value}缓存")
            else:
                # 清除所有资产缓存
                self._asset_cache.clear()
                self._asset_cache_timestamps.clear()
                logger.info("已清除所有资产缓存")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 基础健康检查
            base_health = super().health_check() if hasattr(super(), 'health_check') else {'status': 'unknown'}

            # 资产数据库健康检查
            asset_db_health = self.asset_db_manager.health_check_all()

            # 数据路由器健康检查
            router_health = self.data_router.get_route_statistics()

            # 综合健康状态
            healthy_dbs = sum(1 for result in asset_db_health.values() if result.get('status') == 'healthy')
            total_dbs = len(asset_db_health)

            overall_status = 'healthy' if healthy_dbs == total_dbs else 'degraded' if healthy_dbs > 0 else 'unhealthy'

            return {
                'status': overall_status,
                'asset_database_health': asset_db_health,
                'router_health': router_health,
                'base_health': base_health,
                'summary': {
                    'healthy_databases': healthy_dbs,
                    'total_databases': total_dbs,
                    'available_data_sources': router_health.get('available_sources', 0),
                    'total_data_sources': router_health.get('data_sources_count', 0)
                }
            }

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


# 全局实例
_asset_aware_manager: Optional[AssetAwareUnifiedDataManager] = None
_manager_lock = threading.Lock()


def get_asset_aware_unified_data_manager(
    service_container: ServiceContainer = None,
    event_bus: EventBus = None,
    max_workers: int = 3,
    asset_db_config: Optional[AssetDatabaseConfig] = None
) -> AssetAwareUnifiedDataManager:
    """获取全局资产感知统一数据管理器实例"""
    global _asset_aware_manager

    with _manager_lock:
        if _asset_aware_manager is None:
            _asset_aware_manager = AssetAwareUnifiedDataManager(
                service_container, event_bus, max_workers, asset_db_config
            )

        return _asset_aware_manager


def initialize_asset_aware_unified_data_manager(
    service_container: ServiceContainer = None,
    event_bus: EventBus = None,
    max_workers: int = 3,
    asset_db_config: Optional[AssetDatabaseConfig] = None
) -> AssetAwareUnifiedDataManager:
    """初始化资产感知统一数据管理器"""
    global _asset_aware_manager

    with _manager_lock:
        _asset_aware_manager = AssetAwareUnifiedDataManager(
            service_container, event_bus, max_workers, asset_db_config
        )
        logger.info("AssetAwareUnifiedDataManager 已初始化")

        return _asset_aware_manager
