"""
数据路由器

智能数据路由器，负责根据资产类型、数据类型、数据源等条件，
将数据请求路由到合适的数据库和数据源插件。

作者: FactorWeave-Quant团队
版本: 1.0
"""

import threading
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import json

from loguru import logger
from core.asset_type_identifier import get_asset_type_identifier
from core.asset_database_manager import get_asset_database_manager
from core.plugin_types import AssetType, DataType, PluginType

logger = logger.bind(module=__name__)


class DataSource(Enum):
    """数据源枚举"""
    TONGDAXIN = "tongdaxin"
    EASTMONEY = "eastmoney"
    SINA = "sina"
    TENCENT = "tencent"
    TONGHUASHUN = "tonghuashun"
    BINANCE = "binance"
    WIND = "wind"
    BLOOMBERG = "bloomberg"
    YAHOO = "yahoo"
    AKSHARE = "akshare"
    CUSTOM = "custom"


class RouteStrategy(Enum):
    """路由策略枚举"""
    FASTEST = "fastest"          # 最快响应
    MOST_RELIABLE = "most_reliable"  # 最可靠
    HIGHEST_QUALITY = "highest_quality"  # 最高质量
    LOAD_BALANCE = "load_balance"     # 负载均衡
    FAILOVER = "failover"        # 故障转移
    CUSTOM = "custom"            # 自定义策略


@dataclass
class DataRequest:
    """数据请求结构"""
    symbol: str
    data_type: DataType
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    frequency: str = "1d"
    fields: Optional[List[str]] = None
    limit: Optional[int] = None
    preferred_sources: Optional[List[DataSource]] = None
    strategy: RouteStrategy = RouteStrategy.FASTEST
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'symbol': self.symbol,
            'data_type': self.data_type.value if self.data_type else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'frequency': self.frequency,
            'fields': self.fields,
            'limit': self.limit,
            'preferred_sources': [s.value for s in self.preferred_sources] if self.preferred_sources else None,
            'strategy': self.strategy.value,
            'metadata': self.metadata
        }


@dataclass
class RouteResult:
    """路由结果结构"""
    asset_type: AssetType
    database_path: str
    selected_sources: List[DataSource]
    primary_source: DataSource
    fallback_sources: List[DataSource]
    route_reason: str
    confidence_score: float = 0.0
    estimated_latency_ms: int = 0
    cache_available: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'asset_type': self.asset_type.value,
            'database_path': self.database_path,
            'selected_sources': [s.value for s in self.selected_sources],
            'primary_source': self.primary_source.value,
            'fallback_sources': [s.value for s in self.fallback_sources],
            'route_reason': self.route_reason,
            'confidence_score': self.confidence_score,
            'estimated_latency_ms': self.estimated_latency_ms,
            'cache_available': self.cache_available,
            'metadata': self.metadata
        }


@dataclass
class DataSourceInfo:
    """数据源信息"""
    source: DataSource
    asset_types: List[AssetType]
    data_types: List[DataType]
    is_available: bool = True
    last_check_time: Optional[datetime] = None
    success_rate: float = 1.0
    avg_response_time_ms: int = 1000
    quality_score: float = 0.8
    cost_per_request: float = 0.0
    rate_limit: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataRouter:
    """
    数据路由器

    根据资产类型、数据类型、数据源健康状态等因素，
    智能选择最适合的数据源和数据库路径。
    """

    _instance: Optional['DataRouter'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化数据路由器"""
        if self._initialized:
            return

        # 核心组件
        self.asset_identifier = get_asset_type_identifier()
        self.db_manager = get_asset_database_manager()

        # 数据源信息注册表
        self._data_sources: Dict[DataSource, DataSourceInfo] = {}

        # 路由策略配置
        self._strategy_config: Dict[RouteStrategy, Dict[str, Any]] = {}

        # 缓存和统计
        self._route_cache: Dict[str, RouteResult] = {}
        self._route_stats: Dict[str, Dict[str, Any]] = {}

        # 线程锁
        self._router_lock = threading.RLock()

        # 初始化默认配置
        self._initialize_default_sources()
        self._initialize_strategy_config()

        self._initialized = True
        logger.info("DataRouter 初始化完成")

    def _initialize_default_sources(self):
        """初始化默认数据源配置"""
        default_sources = [
            # 股票数据源
            DataSourceInfo(
                source=DataSource.TONGDAXIN,
                asset_types=[AssetType.STOCK_A, AssetType.STOCK_B, AssetType.INDEX],
                data_types=[DataType.HISTORICAL_KLINE, DataType.TRADE_TICK, DataType.REAL_TIME_QUOTE],
                success_rate=0.95,
                avg_response_time_ms=500,
                quality_score=0.9
            ),
            DataSourceInfo(
                source=DataSource.EASTMONEY,
                asset_types=[AssetType.STOCK_A, AssetType.STOCK_HK, AssetType.FUND],
                data_types=[DataType.HISTORICAL_KLINE, DataType.FUNDAMENTAL, DataType.NEWS],
                success_rate=0.92,
                avg_response_time_ms=800,
                quality_score=0.85
            ),
            DataSourceInfo(
                source=DataSource.SINA,
                asset_types=[AssetType.STOCK_A, AssetType.STOCK_US, AssetType.STOCK_HK],
                data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE],
                success_rate=0.88,
                avg_response_time_ms=600,
                quality_score=0.75
            ),
            DataSourceInfo(
                source=DataSource.TENCENT,
                asset_types=[AssetType.STOCK_A, AssetType.STOCK_HK],
                data_types=[DataType.HISTORICAL_KLINE, DataType.REAL_TIME_QUOTE, DataType.NEWS],
                success_rate=0.90,
                avg_response_time_ms=700,
                quality_score=0.80
            ),

            # 数字货币数据源
            DataSourceInfo(
                source=DataSource.BINANCE,
                asset_types=[AssetType.CRYPTO],
                data_types=[DataType.HISTORICAL_KLINE, DataType.TRADE_TICK, DataType.MARKET_DEPTH],
                success_rate=0.98,
                avg_response_time_ms=300,
                quality_score=0.95
            ),

            # 美股数据源
            DataSourceInfo(
                source=DataSource.YAHOO,
                asset_types=[AssetType.STOCK_US, AssetType.INDEX],
                data_types=[DataType.HISTORICAL_KLINE, DataType.FUNDAMENTAL],
                success_rate=0.85,
                avg_response_time_ms=1200,
                quality_score=0.82
            ),

            # 期货数据源
            DataSourceInfo(
                source=DataSource.TONGHUASHUN,
                asset_types=[AssetType.FUTURES, AssetType.OPTION],
                data_types=[DataType.HISTORICAL_KLINE, DataType.TRADE_TICK],
                success_rate=0.87,
                avg_response_time_ms=900,
                quality_score=0.78
            )
        ]

        for source_info in default_sources:
            self._data_sources[source_info.source] = source_info

        logger.debug(f"初始化了 {len(default_sources)} 个默认数据源")

    def _initialize_strategy_config(self):
        """初始化路由策略配置"""
        self._strategy_config = {
            RouteStrategy.FASTEST: {
                'weight_response_time': 0.7,
                'weight_success_rate': 0.2,
                'weight_quality': 0.1,
                'max_response_time_ms': 2000
            },
            RouteStrategy.MOST_RELIABLE: {
                'weight_response_time': 0.1,
                'weight_success_rate': 0.8,
                'weight_quality': 0.1,
                'min_success_rate': 0.9
            },
            RouteStrategy.HIGHEST_QUALITY: {
                'weight_response_time': 0.1,
                'weight_success_rate': 0.2,
                'weight_quality': 0.7,
                'min_quality_score': 0.8
            },
            RouteStrategy.LOAD_BALANCE: {
                'enable_round_robin': True,
                'consider_load': True,
                'balance_threshold': 0.1
            },
            RouteStrategy.FAILOVER: {
                'primary_weight': 0.9,
                'fallback_weight': 0.1,
                'switch_threshold': 0.7
            }
        }

        logger.debug("路由策略配置初始化完成")

    def register_data_source(self, source_info: DataSourceInfo):
        """注册数据源"""
        with self._router_lock:
            self._data_sources[source_info.source] = source_info

        logger.info(f"注册数据源: {source_info.source.value}")

    def unregister_data_source(self, source: DataSource):
        """注销数据源"""
        with self._router_lock:
            if source in self._data_sources:
                del self._data_sources[source]
                logger.info(f"注销数据源: {source.value}")

    def update_source_health(self, source: DataSource, is_available: bool,
                             response_time_ms: Optional[int] = None,
                             success: Optional[bool] = None):
        """更新数据源健康状态"""
        with self._router_lock:
            if source not in self._data_sources:
                return

            source_info = self._data_sources[source]
            source_info.is_available = is_available
            source_info.last_check_time = datetime.now()

            if response_time_ms is not None:
                # 使用指数移动平均更新响应时间
                alpha = 0.3
                source_info.avg_response_time_ms = int(
                    alpha * response_time_ms + (1 - alpha) * source_info.avg_response_time_ms
                )

            if success is not None:
                # 使用指数移动平均更新成功率
                alpha = 0.1
                new_success_rate = 1.0 if success else 0.0
                source_info.success_rate = (
                    alpha * new_success_rate + (1 - alpha) * source_info.success_rate
                )

        logger.debug(f"更新数据源健康状态: {source.value}, 可用: {is_available}")

    def route_data_request(self, request: DataRequest) -> RouteResult:
        """
        路由数据请求

        Args:
            request: 数据请求

        Returns:
            路由结果
        """
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(request)

            # 检查缓存
            if cache_key in self._route_cache:
                cached_result = self._route_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"使用缓存路由结果: {request.symbol}")
                    return cached_result

            # 识别资产类型
            asset_type = self.asset_identifier.identify_asset_type_by_symbol(request.symbol)

            # 获取数据库路径
            db_path, _ = self.db_manager.get_database_for_symbol(request.symbol)

            # 筛选合适的数据源
            candidate_sources = self._filter_candidate_sources(asset_type, request.data_type)

            if not candidate_sources:
                raise ValueError(f"没有找到支持 {asset_type.value} 和 {request.data_type.value} 的数据源")

            # 根据策略选择数据源
            selected_sources = self._select_sources_by_strategy(candidate_sources, request.strategy)

            # 构建路由结果
            route_result = RouteResult(
                asset_type=asset_type,
                database_path=db_path,
                selected_sources=selected_sources,
                primary_source=selected_sources[0],
                fallback_sources=selected_sources[1:] if len(selected_sources) > 1 else [],
                route_reason=f"策略: {request.strategy.value}, 资产: {asset_type.value}",
                confidence_score=self._calculate_confidence_score(selected_sources),
                estimated_latency_ms=self._estimate_latency(selected_sources[0]),
                cache_available=self._check_cache_availability(request)
            )

            # 缓存结果
            self._route_cache[cache_key] = route_result

            # 更新统计
            self._update_route_stats(request, route_result)

            logger.debug(f"路由完成: {request.symbol} -> {route_result.primary_source.value}")
            return route_result

        except Exception as e:
            logger.error(f"数据路由失败: {request.symbol}, {e}")
            raise

    def _generate_cache_key(self, request: DataRequest) -> str:
        """生成缓存键"""
        key_parts = [
            request.symbol,
            request.data_type.value if request.data_type else "none",
            request.frequency,
            request.strategy.value,
            str(hash(tuple(request.preferred_sources) if request.preferred_sources else ()))
        ]
        return "|".join(key_parts)

    def _is_cache_valid(self, result: RouteResult, ttl_seconds: int = 300) -> bool:
        """检查缓存是否有效"""
        if 'created_at' not in result.metadata:
            return False

        created_at = datetime.fromisoformat(result.metadata['created_at'])
        return (datetime.now() - created_at).total_seconds() < ttl_seconds

    def _filter_candidate_sources(self, asset_type: AssetType,
                                  data_type: DataType) -> List[DataSource]:
        """筛选候选数据源"""
        candidates = []

        with self._router_lock:
            for source, info in self._data_sources.items():
                if (info.is_available and
                    asset_type in info.asset_types and
                        data_type in info.data_types):
                    candidates.append(source)

        return candidates

    def _select_sources_by_strategy(self, candidates: List[DataSource],
                                    strategy: RouteStrategy) -> List[DataSource]:
        """根据策略选择数据源"""
        if not candidates:
            return []

        if strategy == RouteStrategy.FASTEST:
            return self._select_fastest_sources(candidates)
        elif strategy == RouteStrategy.MOST_RELIABLE:
            return self._select_most_reliable_sources(candidates)
        elif strategy == RouteStrategy.HIGHEST_QUALITY:
            return self._select_highest_quality_sources(candidates)
        elif strategy == RouteStrategy.LOAD_BALANCE:
            return self._select_load_balanced_sources(candidates)
        elif strategy == RouteStrategy.FAILOVER:
            return self._select_failover_sources(candidates)
        else:
            # 默认返回第一个候选源
            return [candidates[0]]

    def _select_fastest_sources(self, candidates: List[DataSource]) -> List[DataSource]:
        """选择最快的数据源"""
        with self._router_lock:
            sorted_sources = sorted(
                candidates,
                key=lambda s: self._data_sources[s].avg_response_time_ms
            )
        return sorted_sources

    def _select_most_reliable_sources(self, candidates: List[DataSource]) -> List[DataSource]:
        """选择最可靠的数据源"""
        with self._router_lock:
            sorted_sources = sorted(
                candidates,
                key=lambda s: self._data_sources[s].success_rate,
                reverse=True
            )
        return sorted_sources

    def _select_highest_quality_sources(self, candidates: List[DataSource]) -> List[DataSource]:
        """选择质量最高的数据源"""
        with self._router_lock:
            sorted_sources = sorted(
                candidates,
                key=lambda s: self._data_sources[s].quality_score,
                reverse=True
            )
        return sorted_sources

    def _select_load_balanced_sources(self, candidates: List[DataSource]) -> List[DataSource]:
        """选择负载均衡的数据源"""
        # 简单的轮询实现
        if not hasattr(self, '_lb_counter'):
            self._lb_counter = 0

        if candidates:
            selected_index = self._lb_counter % len(candidates)
            self._lb_counter += 1
            return [candidates[selected_index]] + [c for i, c in enumerate(candidates) if i != selected_index]

        return candidates

    def _select_failover_sources(self, candidates: List[DataSource]) -> List[DataSource]:
        """选择故障转移数据源"""
        # 按可靠性排序，作为故障转移序列
        return self._select_most_reliable_sources(candidates)

    def _calculate_confidence_score(self, sources: List[DataSource]) -> float:
        """计算路由置信度"""
        if not sources:
            return 0.0

        primary_source = sources[0]
        with self._router_lock:
            if primary_source in self._data_sources:
                source_info = self._data_sources[primary_source]
                return (source_info.success_rate * 0.6 +
                        source_info.quality_score * 0.4)

        return 0.5  # 默认值

    def _estimate_latency(self, source: DataSource) -> int:
        """估算延迟"""
        with self._router_lock:
            if source in self._data_sources:
                return self._data_sources[source].avg_response_time_ms

        return 1000  # 默认值

    def _check_cache_availability(self, request: DataRequest) -> bool:
        """检查缓存可用性"""
        # 简单实现：历史数据有缓存，实时数据无缓存
        if request.data_type in [DataType.REAL_TIME_QUOTE, DataType.TRADE_TICK]:
            return False

        return request.end_date is None or request.end_date < date.today()

    def _update_route_stats(self, request: DataRequest, result: RouteResult):
        """更新路由统计"""
        route_key = f"{result.asset_type.value}_{request.data_type.value}_{request.strategy.value}"

        if route_key not in self._route_stats:
            self._route_stats[route_key] = {
                'total_requests': 0,
                'source_usage': {},
                'avg_confidence': 0.0,
                'last_updated': datetime.now().isoformat()
            }

        stats = self._route_stats[route_key]
        stats['total_requests'] += 1

        # 更新数据源使用统计
        primary_source = result.primary_source.value
        if primary_source not in stats['source_usage']:
            stats['source_usage'][primary_source] = 0
        stats['source_usage'][primary_source] += 1

        # 更新平均置信度
        alpha = 0.1
        stats['avg_confidence'] = (
            alpha * result.confidence_score +
            (1 - alpha) * stats['avg_confidence']
        )

        stats['last_updated'] = datetime.now().isoformat()

    def get_route_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        with self._router_lock:
            return {
                'total_routes': len(self._route_cache),
                'data_sources_count': len(self._data_sources),
                'available_sources': sum(1 for info in self._data_sources.values() if info.is_available),
                'route_stats': dict(self._route_stats),
                'cache_hit_ratio': self._calculate_cache_hit_ratio()
            }

    def _calculate_cache_hit_ratio(self) -> float:
        """计算缓存命中率"""
        # 简单实现，实际应该跟踪命中和未命中次数
        return 0.8 if self._route_cache else 0.0

    def get_data_sources_status(self) -> Dict[str, Dict[str, Any]]:
        """获取数据源状态"""
        with self._router_lock:
            return {
                source.value: {
                    'is_available': info.is_available,
                    'success_rate': info.success_rate,
                    'avg_response_time_ms': info.avg_response_time_ms,
                    'quality_score': info.quality_score,
                    'supported_assets': [at.value for at in info.asset_types],
                    'supported_data_types': [dt.value for dt in info.data_types],
                    'last_check_time': info.last_check_time.isoformat() if info.last_check_time else None
                }
                for source, info in self._data_sources.items()
            }

    def clear_cache(self):
        """清除路由缓存"""
        with self._router_lock:
            self._route_cache.clear()

        logger.info("路由缓存已清除")

    def batch_route_requests(self, requests: List[DataRequest]) -> List[RouteResult]:
        """批量路由请求"""
        results = []

        for request in requests:
            try:
                result = self.route_data_request(request)
                results.append(result)
            except Exception as e:
                logger.error(f"批量路由失败: {request.symbol}, {e}")
                # 创建失败结果
                error_result = RouteResult(
                    asset_type=AssetType.STOCK_A,  # 默认值
                    database_path="",
                    selected_sources=[],
                    primary_source=DataSource.CUSTOM,
                    fallback_sources=[],
                    route_reason=f"路由失败: {str(e)}",
                    confidence_score=0.0
                )
                results.append(error_result)

        logger.info(f"批量路由完成: {len(requests)} 个请求")
        return results


# 全局实例
_data_router: Optional[DataRouter] = None
_router_lock = threading.Lock()


def get_data_router() -> DataRouter:
    """获取全局数据路由器实例"""
    global _data_router

    with _router_lock:
        if _data_router is None:
            _data_router = DataRouter()

        return _data_router


def initialize_data_router() -> DataRouter:
    """初始化数据路由器"""
    global _data_router

    with _router_lock:
        _data_router = DataRouter()
        logger.info("DataRouter 已初始化")

        return _data_router
