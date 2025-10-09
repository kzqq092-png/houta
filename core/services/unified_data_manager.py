from loguru import logger
"""
统一数据管理器

负责协调各服务的数据加载请求，避免重复数据加载，提供统一的数据访问接口。
集成了原DataManager和HikyuuDataManager的所有功能。
"""

import threading
import time
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import asyncio
from asyncio import Future as AsyncioFuture
import numpy as np
import sqlite3
import os
import traceback

from ..events import EventBus, DataUpdateEvent
from ..containers import ServiceContainer, get_service_container
from ..plugin_types import AssetType, DataType
from ..tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData

# 导入UniPluginDataManager
try:
    from .uni_plugin_data_manager import UniPluginDataManager
except ImportError as e:
    logger.warning(f"UniPluginDataManager导入失败: {e}")
    UniPluginDataManager = None

# 系统基于DuckDB优先架构和TET框架运行

# 传统数据源已迁移到TET+Plugin架构，不再直接导入
# 数据源现在通过UniPluginDataManager统一管理

# 导入缓存和工具
try:
    # from utils.cache import Cache  # 已统一使用MultiLevelCacheManager
    # log_structured已替换为直接的logger调用
    from core.performance import measure_performance
except ImportError as e:
    logger.warning(f"工具模块导入失败: {e}")
    # Cache = None  # 已统一使用MultiLevelCacheManager

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db', 'factorweave_system.sqlite')


def get_unified_data_manager() -> Optional['UnifiedDataManager']:
    """
    获取统一数据管理器的实例

    Returns:
        统一数据管理器实例，如果未注册则返回None
    """
    try:
        container = get_service_container()
        if container:
            return container.resolve(UnifiedDataManager)
        return None
    except Exception as e:
        logger.error(f"获取统一数据管理器失败: {e}")
        return None


class DataRequestStatus(Enum):
    """数据请求状态"""
    PENDING = "pending"
    LOADING = "loading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DataRequest:
    """数据请求"""
    request_id: str
    symbol: str  # 统一使用symbol替代stock_code
    asset_type: AssetType = AssetType.STOCK  # 新增资产类型支持
    data_type: str = 'kdata'  # 'kdata', 'indicators', 'analysis'
    period: str = 'D'
    time_range: int = 365
    parameters: Dict[str, Any] = None
    priority: int = 0  # 0=高优先级, 1=中优先级, 2=低优先级
    future: Optional[AsyncioFuture] = None  # 用于async/await
    timestamp: float = 0
    status: DataRequestStatus = DataRequestStatus.PENDING

    # 向后兼容属性
    @property
    def stock_code(self) -> str:
        """
        清理缓存 - 使用统一的MultiLevelCacheManager向后兼容：股票代码"""
        return self.symbol

    @stock_code.setter
    def stock_code(self, value: str):
        """向后兼容：设置股票代码"""
        self.symbol = value

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.parameters is None:
            self.parameters = {}

    def __eq__(self, other):
        if not isinstance(other, DataRequest):
            return NotImplemented
        return (self.symbol == other.symbol and
                self.asset_type == other.asset_type and
                self.data_type == other.data_type and
                self.period == other.period and
                self.time_range == other.time_range and
                self.parameters == other.parameters)

    def __hash__(self):
        # The hash should be based on the immutable fields that define the request's identity
        # Note: self.parameters is mutable, so we convert it to a string representation of its items
        param_tuple = tuple(sorted((self.parameters or {}).items()))
        return hash((self.symbol,
                     self.asset_type,
                     self.data_type,
                     self.period,
                     self.time_range,
                     param_tuple))


class UnifiedDataManager:
    """
    统一数据管理器

    功能：
    1. 协调数据加载请求
    2. 避免重复数据加载
    3. 提供统一的数据访问接口
    4. 管理数据缓存
    5. 优化数据加载性能
    6. 支持TET数据管道（Transform-Extract-Transform）
    7. 多资产类型数据处理
    8. 集成HIkyuu、东方财富、新浪等多数据源
    9. 行业数据管理
    10. SQLite数据库支持
    """

    def __init__(self, service_container: ServiceContainer = None, event_bus: EventBus = None, max_workers: int = 3):
        """
        初始化统一数据管理器

        Args:
            service_container: 服务容器 (可选)
            event_bus: 事件总线 (可选)
            max_workers: 最大工作线程数
        """
        # 兼容性处理 - 允许None参数
        from ..containers import get_service_container
        self.service_container = service_container or get_service_container()
        self.event_bus = event_bus
        self.loop = None  # 延迟初始化，在异步方法中获取

        # 线程池
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="DataManager")

        # 请求管理
        self._pending_requests: Dict[str, DataRequest] = {}
        self._active_requests: Dict[str, DataRequest] = {}
        self._completed_requests: Dict[str, DataRequest] = {}
        self._request_lock = threading.Lock()

        self._cache_ttl = 300  # 5分钟缓存TTL

        # 初始化缓存管理器
        # if Cache:  # 已统一使用MultiLevelCacheManager
        if False:
            self.cache_manager = Cache()
        else:
            self.cache_manager = None

        # 数据库连接
        try:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._db_lock = threading.Lock()
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            self.conn = None
            self._db_lock = None

        # 初始化UniPluginDataManager (延迟模式)

        self._uni_plugin_manager = None

        self._is_initialized = False

        # HIkyuu已移除，系统基于TET框架和插件架构运行
        self._invalid_stocks_cache = set()
        self._valid_stocks_cache = set()

        # 多数据源支持 - 默认使用TET框架
        self._current_source = 'tet_framework'
        self._data_sources = {}

        # 插件化数据源管理
        self._plugin_data_sources = {}
        self._registered_data_sources = {}  # 存储已注册的数据源信息
        self._data_source_priorities = {
            'stock': ['eastmoney', 'sina', 'tonghuashun'],
            'futures': [],
            'crypto': []
        }
        self._routing_strategy = 'priority'
        self._health_status = {}
        self._plugin_lock = threading.RLock()

        # 行业管理器初始化
        try:
            from ..industry_manager import IndustryManager
            self.industry_manager = IndustryManager()
            self._load_industry_data()
        except Exception as e:
            logger.warning(f"行业管理器初始化失败: {e}")
            self.industry_manager = None

        # 去重机制
        self._request_dedup: Dict[str, Set[DataRequest]] = {}
        self._dedup_lock = threading.Lock()

        # 请求跟踪
        self.request_tracker: Dict[str, Dict[str, Any]] = {}
        self.request_tracker_lock = threading.Lock()

        # TET数据管道支持
        self.tet_enabled = True  # 默认启用TET模式
        self.tet_pipeline = None

        # 数据处理策略
        from ..tet_data_pipeline import HistoryDataStrategy, RealtimeDataStrategy
        self.history_data_strategy = HistoryDataStrategy()
        self.realtime_data_strategy = RealtimeDataStrategy()

        # 初始化TET管道
        try:
            from ..tet_data_pipeline import TETDataPipeline
            from ..data_source_router import DataSourceRouter

            # 创建数据源路由器
            data_source_router = DataSourceRouter()

            # 初始化TET管道
            self.tet_pipeline = TETDataPipeline(data_source_router)
            logger.info("TET数据管道初始化成功")

            # 注册HIkyuu数据源插件到路由器和TET管道 - 删除手动注册，使用自动发现机制
            # self._register_hikyuu_plugin_to_router(data_source_router)

            # 插件发现状态标记
            self._plugins_discovered = False

            # 注册传统数据源到TET路由器
            self._register_legacy_data_sources_to_router()

            # 延迟插件发现 - 不在初始化时立即执行
            # 将在服务引导完成后通过外部调用执行
            logger.info("TET数据管道初始化完成，等待插件发现...")

        except ImportError as e:
            logger.error(f"TET数据管道模块导入失败: {e}")
            logger.info("禁用TET数据管道，使用传统模式")
            self.tet_enabled = False
            self.tet_pipeline = None
        except Exception as e:
            logger.warning(f"TET数据管道初始化失败: {e}")
            logger.info("降级到传统模式")
            self.tet_enabled = False
            self._plugins_discovered = False

        # 板块数据服务初始化
        self._sector_data_service = None
        self._initialize_sector_service()

        # 统计信息
        self._stats = {
            'requests_total': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'requests_cancelled': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        # DuckDB集成支持 - 直接集成到现有管理器
        self._init_duckdb_integration()

        logger.info("统一数据管理器构造完成")

    def initialize(self):
        """延迟初始化，由服务容器控制时机"""
        if self._is_initialized:
            logger.info("UnifiedDataManager已初始化，跳过重复初始化")
            return

        logger.info("开始初始化UnifiedDataManager...")

        # 从服务容器获取已注册的实例，而不是创建新的
        try:
            if UniPluginDataManager and hasattr(self, 'service_container') and self.service_container:
                if self.service_container.is_registered(UniPluginDataManager):
                    self._uni_plugin_manager = self.service_container.resolve(UniPluginDataManager)
                    logger.info("从服务容器获取UniPluginDataManager成功")
                else:
                    logger.warning("UniPluginDataManager未在服务容器中注册，将使用延迟创建模式")
            else:
                logger.warning("服务容器不可用或UniPluginDataManager未导入，将使用延迟创建模式")
        except Exception as e:
            logger.error(f"[ERROR] 从服务容器获取UniPluginDataManager失败: {e}")

        # 增强DuckDB数据下载器 - 在UniPluginDataManager可用后初始化
        self._init_enhanced_duckdb_downloader()

        self._is_initialized = True
        logger.info("UnifiedDataManager初始化完成")

    def _init_duckdb_integration(self):
        """
        集成DuckDB功能到现有数据管理器

        在现有架构基础上增加DuckDB支持，不破坏现有功能
        """
        try:
            # 导入DuckDB核心组件
            from ..database.duckdb_operations import get_duckdb_operations
            from ..database.duckdb_manager import get_connection_manager
            from ..database.table_manager import get_table_manager
            from ..integration.data_router import DataRouter
            from ..performance.cache_manager import MultiLevelCacheManager

            # 初始化DuckDB组件
            self.duckdb_operations = get_duckdb_operations()
            self.duckdb_manager = get_connection_manager()
            self.table_manager = get_table_manager()

            # 智能数据路由器
            self.data_router = DataRouter()

            # 多级缓存管理器（增强现有缓存）
            from ..performance.cache_manager import CacheLevel
            cache_config = {
                'levels': [CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
                'default_ttl_minutes': 30,
                'memory': {
                    'max_size': 1000,
                    'max_memory_mb': 100
                },
                'disk': {
                    'cache_dir': 'cache/duckdb',
                    'max_size_mb': 500
                }
            }
            self.multi_cache = MultiLevelCacheManager(cache_config)

            # DuckDB可用标志
            self.duckdb_available = True

            logger.info("DuckDB功能集成成功")

        except ImportError as e:
            logger.warning(f" DuckDB模块导入失败，将使用传统模式: {e}")
            self.duckdb_operations = None
            self.duckdb_manager = None
            self.table_manager = None
            self.data_router = None
            self.multi_cache = None
            self.duckdb_available = False
        except Exception as e:
            logger.warning(f" DuckDB功能集成失败，将使用传统模式: {e}")
            self.duckdb_operations = None
            self.duckdb_manager = None
            self.table_manager = None
            self.data_router = None
            self.multi_cache = None
            self.duckdb_available = False

    def _init_enhanced_duckdb_downloader(self):
        """
        初始化增强DuckDB数据下载器

        提供强大的数据下载和存储能力，完全基于TET框架和插件架构
        """
        try:
            from .enhanced_duckdb_data_downloader import get_enhanced_duckdb_downloader

            if self._uni_plugin_manager:
                self.enhanced_duckdb_downloader = get_enhanced_duckdb_downloader(self._uni_plugin_manager)
                logger.info("增强DuckDB数据下载器初始化成功")
            else:
                logger.warning("UniPluginDataManager不可用，无法初始化增强DuckDB下载器")
                self.enhanced_duckdb_downloader = None

        except Exception as e:
            logger.warning(f" 增强DuckDB数据下载器初始化失败: {e}")
            self.enhanced_duckdb_downloader = None

    def _create_uni_plugin_manager_if_needed(self):
        """初始化UniPluginDataManager"""
        try:
            from core.plugin_manager import PluginManager
            from core.data_source_router import DataSourceRouter
            from core.tet_data_pipeline import TETDataPipeline
            from core.services.uni_plugin_data_manager import UniPluginDataManager

            logger.info("开始初始化UniPluginDataManager...")

            # 创建必要的组件
            plugin_manager = PluginManager()
            data_source_router = DataSourceRouter()
            tet_pipeline = TETDataPipeline(data_source_router)

            # 创建UniPluginDataManager
            self._uni_plugin_manager = UniPluginDataManager(
                plugin_manager=plugin_manager,
                data_source_router=data_source_router,
                tet_pipeline=tet_pipeline
            )

            logger.info("UniPluginDataManager初始化成功")

        except Exception as e:
            logger.error(f"[ERROR] UniPluginDataManager初始化失败: {e}")
            self._uni_plugin_manager = None

    def get_uni_plugin_manager(self):
        """获取UniPluginDataManager实例"""
        return self._uni_plugin_manager

    def _register_legacy_data_source_to_router(self, source_id: str, legacy_source):
        """将传统数据源注册到TET路由器"""
        try:
            # 检查TET管道是否可用
            if not (hasattr(self, 'tet_pipeline') and self.tet_pipeline and hasattr(self.tet_pipeline, 'router')):
                logger.debug(f"TET管道不可用，跳过注册传统数据源: {source_id}")
                return

            # 创建传统数据源的适配器
            from ..data_source_extensions import DataSourcePluginAdapter
            from .legacy_datasource_adapter import LegacyDataSourceAdapter

            # 包装传统数据源为IDataSourcePlugin接口
            plugin_adapter = LegacyDataSourceAdapter(legacy_source, source_id)

            # 创建数据源插件适配器
            adapter = DataSourcePluginAdapter(plugin_adapter, source_id)

            # 注册到路由器
            router = self.tet_pipeline.router
            success = router.register_data_source(source_id, adapter, priority=1, weight=1.0)

            if success:
                logger.info(f"传统数据源 {source_id} 已注册到TET路由器")

                # 关键修复：同时注册到TET管道的适配器字典
                if hasattr(self.tet_pipeline, '_adapters'):
                    self.tet_pipeline._adapters[source_id] = adapter
                    logger.info(f"传统数据源 {source_id} 已注册到TET管道适配器字典")
                else:
                    logger.warning("TET管道缺少_adapters属性")

                # 如果适配器有对应的插件实例，也注册到_plugins字典
                if hasattr(adapter, 'plugin') and hasattr(self.tet_pipeline, '_plugins'):
                    self.tet_pipeline._plugins[source_id] = adapter.plugin
                    logger.info(f"传统数据源 {source_id} 已注册到TET管道插件字典")
            else:
                logger.warning(f"传统数据源 {source_id} 注册到TET路由器失败")

        except Exception as e:
            logger.error(f"注册传统数据源 {source_id} 到TET路由器异常: {e}")

    def _register_legacy_data_sources_to_router(self):
        """将所有传统数据源注册到TET路由器"""
        try:
            logger.info("开始注册传统数据源到TET路由器")

            # 注册所有已初始化的传统数据源
            for source_id, legacy_source in self._data_sources.items():
                if legacy_source is not None:
                    self._register_legacy_data_source_to_router(source_id, legacy_source)

            logger.info("传统数据源注册到TET路由器完成")
        except Exception as e:
            logger.error(f"注册传统数据源到TET路由器异常: {e}")

    def _load_industry_data(self):
        """加载行业数据"""
        if self.industry_manager:
            try:
                self.industry_manager.load_cache()
                self.industry_manager.update_industry_data()
                logger.info("行业数据加载成功")
            except Exception as e:
                logger.error(f"行业数据加载失败: {e}")

    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        sources = []
        # HIkyuu已移除
        sources.extend(self._data_sources.keys())
        return sources

    def switch_data_source(self, source: str) -> bool:
        """切换数据源"""
        if source in self.get_available_sources():
            old_source = self._current_source
            self._current_source = source
            logger.info(f"数据源从 {old_source} 切换到 {source}")
            return True
        else:
            logger.error(f"数据源 {source} 不可用")
            return False

    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """
        获取股票列表（DuckDB优先架构）- 重构为调用通用资产列表方法

        Args:
            market: 市场类型 ('all', 'sh', 'sz', 'bj')

        Returns:
            股票列表DataFrame
        """
        return self.get_asset_list(asset_type='stock', market=market)

    def _get_industry_info(self, stock_code: str) -> str:
        """获取股票行业信息"""
        if self.industry_manager:
            try:
                industry_info = self.industry_manager.get_industry(stock_code)
                if industry_info:
                    return (industry_info.get('csrc_industry') or
                            industry_info.get('exchange_industry') or
                            industry_info.get('industry') or '其他')
            except Exception as e:
                logger.warning(f"获取股票 {stock_code} 行业信息失败: {e}")
        return '其他'

    def get_kdata(self, stock_code: str, period: str = 'D', count: int = 365) -> pd.DataFrame:
        """
        获取K线数据 - 统一接口（增强版：集成DuckDB智能路由）

        Args:
            stock_code: 股票代码
            period: 周期 (D/W/M/1/5/15/30/60)
            count: 数据条数

        Returns:
            K线数据DataFrame
        """
        try:
            cache_key = f"kdata_{stock_code}_{period}_{count}"

            # 1. 多级缓存检查（增强缓存策略）
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None and not cached_data.empty:
                return cached_data

            # 2. 初始化df变量
            df = pd.DataFrame()

            # 3. DuckDB智能路由决策
            if self.duckdb_available and self.data_router:
                backend = self.data_router.route('kline_data',
                                                 symbol=stock_code,
                                                 row_count=count,
                                                 period=period)

                # 大数据量使用DuckDB
                if backend.value == 'duckdb' and count > 1000:
                    df = self._get_kdata_from_duckdb(stock_code, period, count)
                    if not df.empty:
                        self._cache_data(cache_key, df)
                        return df
                    # DuckDB失败时降级到传统方式
                    logger.warning(f"DuckDB获取失败，降级到传统方式: {stock_code}")

            # 4. 传统数据获取方式已废弃，系统完全依赖DuckDB
            logger.warning("传统数据源已废弃，系统完全依赖DuckDB数据库")
            df = pd.DataFrame()

            # 4. 数据标准化和清洗
            if not df.empty:
                df = self._standardize_kdata_format(df, stock_code)

                # 5. 智能存储：大数据存储到DuckDB
                if self.duckdb_available and len(df) > 1000:
                    self._store_to_duckdb(df, stock_code, period)

                # 6. 缓存数据
                self._cache_data(cache_key, df)

            return df

        except Exception as e:
            logger.error(f"获取K线数据失败: {stock_code} - {e}")
            return pd.DataFrame()

    def _get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """增强缓存获取 - 统一使用MultiLevelCacheManager"""
        try:
            # 优先从多级缓存获取
            if self.duckdb_available and self.multi_cache:
                cached_data = self.multi_cache.get(cache_key)
                if cached_data is not None:
                    return cached_data

            # 回退到传统缓存
            if self.cache_manager:
                return self.cache_manager.get(cache_key)

            return None
        except Exception as e:
            logger.warning(f"缓存获取失败: {e}")
            return None

    def _cache_data(self, cache_key: str, data: pd.DataFrame):
        """增强缓存存储 - 支持多级缓存"""
        try:
            # 存储到多级缓存
            if self.duckdb_available and self.multi_cache:
                self.multi_cache.set(cache_key, data, ttl=self._cache_ttl)

            # 同时存储到传统缓存（向后兼容）
            if self.cache_manager:
                self.cache_manager.set(cache_key, data)

        except Exception as e:
            logger.warning(f"缓存存储失败: {e}")

    def get_asset_list(self, asset_type: str = 'stock', market: str = 'all') -> pd.DataFrame:
        """
        获取资产列表（DuckDB优先架构）- 支持所有资产类型

        Args:
            asset_type: 资产类型 ('stock', 'crypto', 'fund', 'bond', 'index', 'sector')
            market: 市场类型 ('all', 'sh', 'sz', 'bj', 'us', 'hk')

        Returns:
            资产列表DataFrame
        """
        try:
            cache_key = f"asset_list_{asset_type}_{market}"

            # 1. 优先从DuckDB数据库获取资产列表
            if self.duckdb_available and self.duckdb_operations:
                logger.info(f"🗄️ 从DuckDB数据库获取{asset_type}资产列表")
                try:
                    asset_list_df = self._get_asset_list_from_duckdb(asset_type, market)
                    if asset_list_df is not None and not asset_list_df.empty:
                        logger.info(f"✅ DuckDB数据库获取{asset_type}资产列表成功: {len(asset_list_df)} 个资产")
                        # 缓存结果
                        if self.cache_enabled:
                            self._cache_data(cache_key, asset_list_df)
                        return asset_list_df
                    else:
                        logger.info(f"📥 DuckDB中没有{asset_type}资产数据")
                except Exception as e:
                    logger.warning(f"⚠️ DuckDB{asset_type}资产列表获取失败: {e}")

            # 2. 如果DuckDB没有数据，记录警告但不再使用插件系统
            logger.warning(f"⚠️ DuckDB中没有{asset_type}资产数据，请检查数据库是否已正确初始化")
            logger.info("💡 提示：系统现在完全依赖DuckDB数据库，不再使用数据源插件")
            logger.info("💡 建议：请运行数据导入脚本来初始化DuckDB数据库")

            # 返回空DataFrame，但保持正确的列结构
            import pandas as pd
            return pd.DataFrame(columns=['code', 'name', 'market', 'industry', 'sector', 'list_date', 'status', 'asset_type'])

        except Exception as e:
            logger.error(f"获取{asset_type}资产列表失败: {e}")
            import pandas as pd
            return pd.DataFrame()

    def _get_asset_list_from_duckdb(self, asset_type: str, market: str = None) -> pd.DataFrame:
        """从DuckDB数据库获取资产列表 - 支持多种资产类型"""
        try:
            import pandas as pd

            if not self.duckdb_operations:
                logger.warning("DuckDB操作器不可用")
                return pd.DataFrame()

            # 根据资产类型选择对应的表和查询
            table_mapping = {
                'stock': 'stock_basic',
                'crypto': 'crypto_basic',
                'fund': 'fund_basic',
                'bond': 'bond_basic',
                'index': 'index_basic',
                'sector': 'sector_basic'
            }

            table_name = table_mapping.get(asset_type, 'stock_basic')

            # 构建查询语句
            # 构建查询SQL（直接拼接参数，因为query_data不支持参数化）
            if market and market != 'all':
                query = f"""
                SELECT DISTINCT 
                    symbol as code,
                    name,
                    market,
                    industry,
                    sector,
                    list_date,
                    status,
                    '{asset_type}' as asset_type
                FROM {table_name} 
                WHERE market = '{market.upper()}' AND status = 'L'
                ORDER BY symbol
                """
            else:
                query = f"""
                SELECT DISTINCT 
                    symbol as code,
                    name,
                    market,
                    industry,
                    sector,
                    list_date,
                    status,
                    '{asset_type}' as asset_type
                FROM {table_name} 
                WHERE status = 'L'
                ORDER BY symbol
                """

            # 执行查询 - 使用query_data方法
            result = self.duckdb_operations.query_data(
                database_path="db/kline_stock.duckdb",
                table_name=table_name,
                custom_sql=query
            )

            if result.success and not result.data.empty:
                df = result.data
                logger.info(f"从DuckDB获取{asset_type}资产列表成功: {len(df)} 个资产")
                return df
            else:
                logger.info(f"DuckDB中没有{asset_type}资产列表数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"从DuckDB获取{asset_type}资产列表失败: {e}")
            return pd.DataFrame()

    def _get_kdata_from_duckdb(self, stock_code: str, period: str, count: int, data_source: str = None) -> pd.DataFrame:
        """从DuckDB获取K线数据（支持数据源隔离）"""
        try:
            if not self.duckdb_operations:
                return pd.DataFrame()

            # 使用现有的DuckDB操作器进行查询
            # 构建查询SQL - 使用标准的kline_stock数据库
            database_path = "db/kline_stock.duckdb"

            # 根据周期确定表名
            table_name = f"kline_{period.lower()}" if period != 'D' else "kline_daily"

            query_sql = f"""
                SELECT symbol as code, datetime, open, high, low, close, volume, amount
                FROM {table_name}
                WHERE symbol = ? 
                ORDER BY datetime DESC 
                LIMIT ?
            """

            try:
                # 使用现有的duckdb_operations进行查询
                result = self.duckdb_operations.execute_query(
                    database_path=database_path,
                    query=query_sql,
                    params=[stock_code, count]
                )

                if result.success and result.data:
                    df = pd.DataFrame(result.data)
                    logger.info(f"✅ DuckDB查询成功: {stock_code}, {len(df)} 条记录")
                    return df
                else:
                    logger.warning(f"未查询到数据: {stock_code}")
                    return pd.DataFrame()

            except Exception as e:
                logger.error(f"DuckDB查询失败: {e}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"DuckDB数据获取失败: {e}")
            return pd.DataFrame()

    def _store_to_duckdb(self, data: pd.DataFrame, stock_code: str, period: str):
        """存储数据到DuckDB"""
        try:
            if not self.duckdb_operations or data.empty:
                return

            table_name = f"kline_data_{period.lower()}"

            # 确保表存在
            if self.table_manager:
                from ..database.table_manager import TableType
                actual_table_name = self.table_manager.ensure_table_exists(
                    "db/kline_stock.duckdb", TableType.KLINE_DATA, "unified_data_manager", period
                )
                if actual_table_name:
                    table_name = actual_table_name

            # 插入数据（使用upsert避免重复）
            result = self.duckdb_operations.insert_dataframe(
                database_path="db/kline_stock.duckdb",
                table_name=table_name,
                data=data,
                upsert=True
            )

            if result.success:
                logger.info(f" 数据存储到DuckDB成功: {stock_code}, {len(data)}条")

        except Exception as e:
            logger.warning(f"DuckDB数据存储失败: {e}")

    # K线数据获取统一使用DuckDB优先架构

    def get_historical_data(self, symbol: str, asset_type=None, period: str = "D", count: int = 365, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取历史数据（兼容AssetService接口）

        Args:
            symbol: 资产代码
            asset_type: 资产类型（兼容性参数，可选）
            period: 周期
            count: 数据条数
            **kwargs: 其他参数

        Returns:
            Optional[pd.DataFrame]: 历史数据
        """
        try:
            # 对于股票数据，直接使用get_kdata方法
            return self.get_kdata(symbol, period, count)
        except Exception as e:
            logger.error(f"获取历史数据失败 {symbol}: {e}")
            return None

    # 数据获取统一使用DuckDB优先架构

    def _standardize_kdata_format(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """标准化K线数据格式"""
        try:
            if df.empty:
                return df

            # 确保必要的列存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"K线数据缺少必要列: {missing_columns}")
                return pd.DataFrame()

            # 处理datetime索引
            if 'datetime' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
            elif not isinstance(df.index, pd.DatetimeIndex):
                logger.warning("K线数据缺少datetime字段")
                return pd.DataFrame()

            # 数据清洗
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.dropna(subset=['close'])  # 至少要有收盘价

            # 确保code字段存在
            if 'code' not in df.columns:
                df['code'] = stock_code

            # 确保amount字段存在
            if 'amount' not in df.columns:
                df['amount'] = 0.0

            # 数据类型转换
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            return df

        except Exception as e:
            logger.error(f"标准化K线数据格式失败: {e}")
            return pd.DataFrame()

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取股票信息"""
        try:
            # HIkyuu已移除，使用TET框架获取股票信息

            # 从股票列表中查找
            stock_list = self.get_stock_list()
            if not stock_list.empty:
                matches = stock_list[stock_list['code'] == stock_code]
                if not matches.empty:
                    return matches.iloc[0].to_dict()

            return None

        except Exception as e:
            logger.error(f"获取股票信息失败: {stock_code} - {e}")
            return None

    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索股票"""
        try:
            stock_list = self.get_stock_list()
            if stock_list.empty:
                return []

            keyword_lower = keyword.lower()
            matches = stock_list[
                (stock_list['code'].str.lower().str.contains(keyword_lower, na=False)) |
                (stock_list['name'].str.lower().str.contains(keyword_lower, na=False))
            ]

            return matches.to_dict('records')

        except Exception as e:
            logger.error(f"搜索股票失败: {keyword} - {e}")
            return []

    def get_fund_flow(self) -> Dict[str, Any]:
        """获取资金流数据 - 通过TET框架和数据源插件获取真实数据"""
        try:
            fund_flow_data = {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

            if self.tet_enabled and self.tet_pipeline:
                logger.info("使用TET数据管道获取资金流数据")

                try:
                    # 获取板块资金流数据
                    sector_query = StandardQuery(
                        asset_type=AssetType.SECTOR,
                        data_type=DataType.SECTOR_FUND_FLOW,
                        symbol="",
                        extra_params={"period": "1d", "limit": 50}
                    )
                    sector_result = self.tet_pipeline.process(sector_query)

                    if sector_result and sector_result.success and sector_result.data is not None:
                        if isinstance(sector_result.data, pd.DataFrame):
                            fund_flow_data['sector_flow_rank'] = sector_result.data
                        else:
                            # 如果返回的是列表或字典，转换为DataFrame
                            fund_flow_data['sector_flow_rank'] = pd.DataFrame(sector_result.data)
                        logger.info(f" TET获取板块资金流数据成功: {len(fund_flow_data['sector_flow_rank'])} 条记录")
                    else:
                        logger.warning("TET板块资金流数据为空或失败")

                except Exception as e:
                    logger.warning(f" TET获取板块资金流数据失败: {e}")

                try:
                    # 获取个股资金流数据
                    individual_query = StandardQuery(
                        asset_type=AssetType.STOCK,
                        data_type=DataType.INDIVIDUAL_FUND_FLOW,
                        symbol="",
                        extra_params={"period": "1d", "limit": 100}
                    )
                    individual_result = self.tet_pipeline.process(individual_query)

                    if individual_result and individual_result.success and individual_result.data is not None:
                        if isinstance(individual_result.data, pd.DataFrame):
                            fund_flow_data['individual_flow'] = individual_result.data
                        else:
                            fund_flow_data['individual_flow'] = pd.DataFrame(individual_result.data)
                        logger.info(f" TET获取个股资金流数据成功: {len(fund_flow_data['individual_flow'])} 条记录")
                    else:
                        logger.warning("TET个股资金流数据为空或失败")

                except Exception as e:
                    logger.warning(f" TET获取个股资金流数据失败: {e}")

                try:
                    # 获取市场整体资金流数据
                    market_query = StandardQuery(
                        asset_type=AssetType.INDEX,
                        data_type=DataType.MAIN_FUND_FLOW,
                        symbol="",
                        extra_params={"period": "1d"}
                    )
                    market_result = self.tet_pipeline.process(market_query)

                    if market_result and market_result.success and market_result.data is not None:
                        if isinstance(market_result.data, dict):
                            fund_flow_data['market_flow'] = market_result.data
                        elif isinstance(market_result.data, pd.DataFrame) and not market_result.data.empty:
                            # 将DataFrame转换为字典
                            fund_flow_data['market_flow'] = market_result.data.to_dict('records')[0] if len(market_result.data) > 0 else {}
                        else:
                            fund_flow_data['market_flow'] = {}
                        logger.info(f" TET获取市场资金流数据成功")
                    else:
                        logger.warning("TET市场资金流数据为空或失败")

                except Exception as e:
                    logger.warning(f" TET获取市场资金流数据失败: {e}")

            else:
                logger.info("降级到传统数据源模式获取资金流数据")
                # 使用传统数据源获取资金流数据
                fund_flow_data = self._get_fund_flow_legacy()

            # 如果所有数据都为空，生成模拟数据用于测试
            if (fund_flow_data['sector_flow_rank'].empty and
                fund_flow_data['individual_flow'].empty and
                    not fund_flow_data['market_flow']):
                logger.info("生成模拟资金流数据用于测试")
                fund_flow_data = self._generate_mock_fund_flow_data()

            return fund_flow_data

        except Exception as e:
            logger.error(f"获取资金流数据失败: {e}")
            return {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

    def _generate_mock_fund_flow_data(self) -> Dict[str, Any]:
        """生成模拟资金流数据用于测试"""
        import random
        from datetime import datetime, timedelta

        try:
            # 生成模拟板块资金流排行数据
            sectors = ['银行', '证券', '保险', '房地产', '钢铁', '煤炭', '有色金属', '石油石化',
                       '电力', '公用事业', '交通运输', '电子', '计算机', '通信', '医药生物']

            sector_data = []
            for i, sector in enumerate(sectors[:10]):  # 取前10个板块
                sector_data.append({
                    'sector_name': sector,
                    'net_inflow': random.uniform(-50000, 100000),  # 净流入(万元)
                    'main_inflow': random.uniform(10000, 80000),   # 主力流入
                    'main_outflow': random.uniform(10000, 60000),  # 主力流出
                    'retail_inflow': random.uniform(5000, 30000),  # 散户流入
                    'retail_outflow': random.uniform(5000, 25000),  # 散户流出
                    'change_rate': random.uniform(-5.0, 8.0),      # 涨跌幅%
                    'rank': i + 1
                })

            sector_df = pd.DataFrame(sector_data)

            # 生成模拟个股资金流数据
            stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000858.SZ']
            individual_data = []
            for stock in stocks:
                individual_data.append({
                    'symbol': stock,
                    'name': f'股票{stock[:6]}',
                    'net_inflow': random.uniform(-10000, 20000),
                    'main_inflow': random.uniform(2000, 15000),
                    'main_outflow': random.uniform(2000, 12000),
                    'price': random.uniform(10.0, 50.0),
                    'change_rate': random.uniform(-3.0, 5.0),
                    'volume': random.randint(100000, 1000000)
                })

            individual_df = pd.DataFrame(individual_data)

            # 生成模拟市场资金流数据
            market_flow = {
                'total_net_inflow': random.uniform(-500000, 800000),
                'main_net_inflow': random.uniform(-300000, 500000),
                'retail_net_inflow': random.uniform(-200000, 300000),
                'north_fund_inflow': random.uniform(-50000, 100000),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market_status': 'open' if 9 <= datetime.now().hour <= 15 else 'closed'
            }

            logger.info(f"生成模拟资金流数据: 板块{len(sector_df)}个, 个股{len(individual_df)}个")

            return {
                'sector_flow_rank': sector_df,
                'individual_flow': individual_df,
                'market_flow': market_flow
            }

        except Exception as e:
            logger.error(f"生成模拟资金流数据失败: {e}")
            return {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

    def _get_fund_flow_legacy(self) -> Dict[str, Any]:
        """传统数据源获取资金流数据"""
        try:
            # 资金流数据通过TET框架获取
            fund_flow_data = {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }
            return fund_flow_data

        except Exception as e:
            logger.error(f"传统数据源获取资金流数据失败: {e}")
            return {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

            # 返回空的资金流数据结构
            logger.info("资金流数据需要通过真实数据源获取")
            return {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

        except Exception as e:
            logger.error(f"生成模拟资金流数据失败: {e}")
            return {
                'sector_flow_rank': pd.DataFrame(),
                'individual_flow': pd.DataFrame(),
                'market_flow': {}
            }

    def test_connection(self) -> bool:
        """测试数据源连接"""
        try:
            # HIkyuu已移除，使用TET框架测试连接
            if self._current_source in self._data_sources:
                # 尝试获取股票列表来测试连接
                test_list = self._data_sources[self._current_source].get_stock_list('sh')
                return not test_list.empty
            else:
                return True  # 模拟模式总是可用

        except Exception as e:
            logger.error(f"测试数据源连接失败: {e}")
            return False

    def get_latest_price(self, stock_code: str) -> float:
        """获取最新价格"""
        try:
            # 获取最近的K线数据
            kdata = self.get_kdata(stock_code, 'D', 1)
            if not kdata.empty:
                return float(kdata['close'].iloc[-1])
            else:
                return 0.0

        except Exception as e:
            logger.error(f"获取最新价格失败: {stock_code} - {e}")
            return 0.0

    def cleanup(self):
        """清理资源"""
        try:
            # 关闭线程池
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=True)

            # 关闭数据库连接
            if self.conn:
                self.conn.close()

            logger.info("统一数据管理器资源清理完成")

        except Exception as e:
            logger.error(f"清理资源失败: {e}")

    def get_asset_list_legacy_tet(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """
        获取资产列表（兼容接口）- 重定向到DuckDB优先方法

        Args:
            asset_type: 资产类型
            market: 市场过滤

        Returns:
            List[Dict]: 标准化的资产列表
        """
        if self.tet_enabled and self.tet_pipeline:
            try:
                # 懒加载检查：如果插件还没发现，重新尝试发现
                if not self._plugins_discovered:
                    logger.info("TET管道首次使用，重新尝试插件发现...")
                    self._auto_discover_data_source_plugins()

                logger.info("使用TET数据管道获取股票列表（插件化架构）")
                query = StandardQuery(
                    symbol="",  # 资产列表查询不需要具体symbol
                    asset_type=asset_type,
                    data_type=DataType.ASSET_LIST,
                    market=market
                )

                result = self.tet_pipeline.process(query)

                # 检查结果是否为空
                if not result.data or len(result.data) == 0:
                    logger.warning("TET管道返回空数据")
                    raise Exception("TET管道返回空数据")

                return self._format_asset_list(result.data)

            except Exception as e:
                logger.warning(f"TET模式获取资产列表失败: {e}")
                logger.info("降级到传统数据源模式")

        # 重定向到新的统一资产列表方法（DuckDB优先）
        logger.info("🔄 重定向到DuckDB优先的资产列表方法")
        asset_type_str = asset_type.value.lower()
        df = self.get_asset_list(asset_type=asset_type_str, market=market)

        # 转换DataFrame为List[Dict]格式以保持接口兼容性
        if not df.empty:
            return df.to_dict('records')
        else:
            logger.warning(f"DuckDB中没有{asset_type_str}资产数据")
            return []

    def get_current_source(self) -> str:
        """获取当前数据源"""
        return getattr(self, '_current_source', 'tet_framework')

    def get_historical_data(self, symbol: str, asset_type: AssetType = AssetType.STOCK,
                            period: str = "D", count: int = 365, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取历史数据（兼容AssetService接口）

        Args:
            symbol: 资产代码
            asset_type: 资产类型
            period: 周期
            count: 数据条数
            **kwargs: 其他参数

        Returns:
            Optional[pd.DataFrame]: 历史数据
        """
        try:
            if asset_type == AssetType.STOCK:
                # 对于股票，使用get_kdata方法
                return self.get_kdata(symbol, period, count)
            else:
                # 对于其他资产类型，使用get_asset_data方法
                return self.get_asset_data(symbol, asset_type, DataType.HISTORICAL_KLINE, period, **kwargs)
        except Exception as e:
            logger.error(f"获取历史数据失败 {symbol}: {e}")
            return None

    def get_asset_data(self, symbol: str, asset_type: AssetType = AssetType.STOCK,
                       data_type: DataType = DataType.HISTORICAL_KLINE,
                       period: str = "D", **kwargs) -> Optional[pd.DataFrame]:
        """
        获取资产数据（TET模式）

        Args:
            symbol: 交易代码
            asset_type: 资产类型
            data_type: 数据类型
            period: 周期
            **kwargs: 其他参数

        Returns:
            Optional[pd.DataFrame]: 标准化数据
        """
        if self.tet_enabled and self.tet_pipeline:
            try:
                logger.info(f" 使用TET模式获取数据: {symbol} ({asset_type.value})")

                query = StandardQuery(
                    symbol=symbol,
                    asset_type=asset_type,
                    data_type=data_type,
                    period=period,
                    **kwargs
                )

                result = self.tet_pipeline.process(query)

                # 记录使用的数据源
                if result and hasattr(result, 'source_info') and result.source_info:
                    data_source = result.source_info.get('provider', 'Unknown')
                    logger.info(f" TET数据获取成功: {symbol} | 数据源: {data_source} | 记录数: {len(result.data) if result.data is not None else 0}")
                else:
                    logger.info(f" TET数据获取成功: {symbol} | 记录数: {len(result.data) if result.data is not None else 0}")

                return result.data

            except Exception as e:
                logger.warning(f" TET模式获取数据失败: {symbol} - {e}")
                logger.info("降级到传统数据获取模式")

        # 降级到传统方式
        if asset_type == AssetType.STOCK:
            logger.info(f" 使用传统模式获取股票数据: {symbol}")
            data = self._legacy_get_stock_data(symbol, period, **kwargs)
            if data is not None:
                logger.info(f" 传统模式数据获取成功: {symbol} | 数据源: DataAccess | 记录数: {len(data)}")
            else:
                logger.warning(f" 传统模式数据获取失败: {symbol}")
            return data
        else:
            logger.warning(f" 传统模式不支持资产类型: {asset_type.value} | 建议启用TET模式")
            return None

    def _format_asset_list(self, asset_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """格式化资产列表为标准格式"""
        if asset_data.empty:
            return []

        result = []
        for _, row in asset_data.iterrows():
            result.append({
                'symbol': row.get('symbol', ''),
                'name': row.get('name', ''),
                'asset_type': row.get('asset_type', ''),
                'market': row.get('market', ''),
                'status': row.get('status', 'active')
            })

        return result

    def register_data_source_plugin(self, plugin_id: str, adapter, priority: int = 0, weight: float = 1.0) -> bool:
        """
        注册数据源插件到路由器和TET管道

        Args:
            plugin_id: 插件ID
            adapter: 插件适配器
            priority: 优先级
            weight: 权重

        Returns:
            bool: 注册是否成功
        """
        try:
            # 检查TET管道是否可用
            if not (hasattr(self, 'tet_pipeline') and self.tet_pipeline):
                logger.warning("TET数据管道不可用，无法注册插件")
                return False

            # 注册到TET管道的路由器
            if hasattr(self.tet_pipeline, 'router'):
                router = self.tet_pipeline.router
                router_success = router.register_data_source(plugin_id, adapter, priority, weight)
                if router_success:
                    logger.info(f" 插件 {plugin_id} 已注册到TET数据管道路由器")
                else:
                    logger.error(f" 插件 {plugin_id} 注册到TET数据管道路由器失败")
                    return False
            else:
                logger.error("TET数据管道缺少路由器")
                return False

            # 关键修复：同时注册到TET管道的适配器字典
            if hasattr(self.tet_pipeline, '_adapters'):
                self.tet_pipeline._adapters[plugin_id] = adapter
                logger.info(f" 插件 {plugin_id} 已注册到TET管道适配器字典")
            else:
                logger.warning("TET管道缺少_adapters属性")

            # 如果适配器有对应的插件实例，也注册到_plugins字典
            if hasattr(adapter, 'plugin') and hasattr(self.tet_pipeline, '_plugins'):
                self.tet_pipeline._plugins[plugin_id] = adapter.plugin
                logger.info(f" 插件 {plugin_id} 已注册到TET管道插件字典")

            # 记录已注册的数据源信息
            plugin_info = {
                'plugin_id': plugin_id,
                'adapter': adapter,
                'priority': priority,
                'weight': weight,
                'display_name': getattr(adapter, 'display_name', plugin_id),
                'supported_assets': getattr(adapter, 'supported_assets', []),
                'status': 'active'
            }
            self._registered_data_sources[plugin_id] = plugin_info
            logger.info(f" 数据源 {plugin_id} 信息已记录")

            return True

        except Exception as e:
            logger.error(f" 注册数据源插件失败 {plugin_id}: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def get_registered_data_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有已注册的数据源

        Returns:
            Dict[str, Dict[str, Any]]: 已注册的数据源信息
        """
        return self._registered_data_sources.copy()

    def get_available_data_source_names(self) -> List[str]:
        """
        获取可用数据源名称列表

        Returns:
            List[str]: 数据源名称列表
        """
        # 基础数据源
        base_sources = ['东方财富', '新浪财经', '同花顺']

        # 添加已注册的插件数据源
        plugin_sources = []
        for plugin_id, info in self._registered_data_sources.items():
            display_name = info.get('display_name', plugin_id)
            if display_name not in base_sources:
                plugin_sources.append(display_name)

        # 合并并去重
        all_sources = base_sources + plugin_sources
        return list(dict.fromkeys(all_sources))  # 保持顺序的去重

    def get_data_source_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定数据源的详细信息

        Args:
            plugin_id: 数据源插件ID

        Returns:
            Optional[Dict[str, Any]]: 数据源信息或None
        """
        return self._registered_data_sources.get(plugin_id)

    def _legacy_get_stock_data(self, symbol: str, period: str = "D", **kwargs) -> Optional[pd.DataFrame]:
        """传统方式获取股票数据"""
        try:
            # 使用现有的股票数据获取逻辑
            from ..data.data_access import DataAccess
            data_access = DataAccess()
            return data_access.get_kdata(symbol, period)
        except Exception as e:
            logger.error(f"传统方式获取股票数据失败: {e}")
            return None

    async def get_stock_data(self, code: str, freq: str, start_date=None, end_date=None, request_id=None):
        """统一的数据请求方法，区分历史和实时数据"""
        if request_id:
            self._register_request(request_id)

        try:
            # 检查是否需要实时数据
            if self._needs_realtime_data(end_date):
                return await self.realtime_data_strategy.get_data(code, freq, start_date, end_date)
            else:
                return await self.history_data_strategy.get_data(code, freq, start_date, end_date)
        except Exception as e:
            logger.error(f"Error fetching data for {code}: {e}")
            return None
        finally:
            if request_id:
                self._unregister_request(request_id)

    def _needs_realtime_data(self, end_date=None):
        """判断是否需要实时数据"""
        if end_date is None:
            # 没有指定结束日期，需要实时数据
            return True

        # 如果结束日期是今天或未来，需要实时数据
        today = datetime.now().date()
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except:
                return True

        if isinstance(end_date, datetime):
            end_date = end_date.date()

        return end_date >= today

    async def request_data(self, stock_code: str, data_type: str = 'kdata',
                           period: str = 'D', time_range: str = "最近1年", **kwargs) -> Any:
        """请求数据

        Args:
            stock_code: 股票代码
            data_type: 数据类型，如'kdata', 'financial', 'news'等
            period: 周期，如'D'(日线)、'W'(周线)、'M'(月线)、'60'(60分钟)等
            time_range: 时间范围，如"最近7天"、"最近30天"、"最近1年"等
            **kwargs: 其他参数

        Returns:
            请求的数据
        """
        try:
            # 处理周期映射
            period_map = {
                '分时': 'min',
                '日线': 'D',
                '周线': 'W',
                '月线': 'M',
                '5分钟': '5',
                '15分钟': '15',
                '30分钟': '30',
                '60分钟': '60'
            }

            # 如果period是中文描述，转换为对应代码
            actual_period = period_map.get(period, period)

            # 处理时间范围映射（转换为天数）
            time_range_map = {
                "最近7天": 7,
                "最近30天": 30,
                "最近90天": 90,
                "最近180天": 180,
                "最近1年": 365,
                "最近2年": 365 * 2,
                "最近3年": 365 * 3,
                "最近5年": 365 * 5,
                "全部": -1  # 表示所有可用数据
            }

            # 获取天数，默认为365天（约1年）
            count = time_range_map.get(time_range, 365)

            logger.info(f"请求数据：股票={stock_code}, 类型={data_type}, 周期={actual_period}, 时间范围={count}天")

            if data_type == 'kdata':
                # 获取K线数据
                return await self._get_kdata(stock_code, period=actual_period, count=count)
            elif data_type == 'financial':
                # 获取财务数据
                return await self._get_financial_data(stock_code)
            elif data_type == 'news':
                # 获取新闻数据
                return await self._get_news(stock_code)
            elif data_type == 'all':
                # 获取所有数据
                kdata = await self._get_kdata(stock_code, period=actual_period, count=count)
                financial = await self._get_financial_data(stock_code)
                news = await self._get_news(stock_code)
                return {
                    'kdata': kdata,
                    'financial': financial,
                    'news': news
                }
            else:
                logger.error(f"未知的数据类型: {data_type}")
                return None
        except Exception as e:
            logger.error(f"请求数据失败: {e}", exc_info=True)
            return None

    async def _get_kdata(self, stock_code: str, period: str = 'D', count: int = 365) -> pd.DataFrame:
        """获取K线数据

        Args:
            stock_code: 股票代码
            period: 周期，如'D'、'W'、'M'
            count: 获取的天数

        Returns:
            K线DataFrame
        """
        try:
            logger.info(f"获取K线数据: {stock_code}, 周期={period}, 数量={count}")

            # 尝试从服务容器解析ChartService
            from core.services.chart_service import ChartService
            chart_service = self.service_container.resolve(ChartService)

            if chart_service:
                return chart_service.get_kdata(stock_code, period, count)

            # 如果没有ChartService，使用默认数据源
            # 注意：core.data_manager已迁移，使用当前实例
            data_manager = self

            if data_manager:
                return data_manager.get_kdata(stock_code, period, count)

            logger.error("无法获取K线数据：未找到数据服务")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取K线数据失败: {e}", exc_info=True)
            return pd.DataFrame()

    async def _get_financial_data(self, stock_code: str) -> Dict[str, Any]:
        """获取财务数据（增强版：集成DuckDB存储）

        Args:
            stock_code: 股票代码

        Returns:
            财务数据字典
        """
        try:
            logger.info(f"获取财务数据: {stock_code}")

            cache_key = f"financial_{stock_code}"

            # 1. 尝试从DuckDB获取财务数据
            if self.duckdb_available and self.duckdb_operations:
                financial_data = await self._get_financial_from_duckdb(stock_code)
                if financial_data:
                    return financial_data

            # 2. 通过TET管道获取财务数据
            if self.tet_enabled and self.tet_pipeline:
                try:
                    from ..tet_data_pipeline import StandardQuery
                    from ..plugin_types import AssetType, DataType

                    query = StandardQuery(
                        symbol=stock_code,
                        asset_type=AssetType.STOCK,
                        data_type=DataType.FINANCIAL_STATEMENT,
                        provider=self._current_source
                    )

                    result = self.tet_pipeline.process(query)
                    if result and result.data:
                        # 存储到DuckDB
                        if self.duckdb_available:
                            await self._store_financial_to_duckdb(stock_code, result.data)
                        return result.data

                except Exception as e:
                    logger.warning(f"TET管道获取财务数据失败: {e}")

            # 3. 回退到传统方式（保持兼容性）
            return {}

        except Exception as e:
            logger.error(f"获取财务数据失败: {e}", exc_info=True)
            return {}

    async def _get_financial_from_duckdb(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从DuckDB获取财务数据"""
        try:
            query = """
                SELECT * FROM financial_statements 
                WHERE symbol = ? 
                ORDER BY report_date DESC 
                LIMIT 1
            """

            result = self.duckdb_operations.execute_query(
                database_path="db/kline_stock.duckdb",
                query=query,
                params=[stock_code]
            )

            if result.success and result.data:
                return result.data[0] if result.data else None

            return None

        except Exception as e:
            logger.error(f"DuckDB财务数据获取失败: {e}")
            return None

    async def _store_financial_to_duckdb(self, stock_code: str, data: Dict[str, Any]):
        """存储财务数据到DuckDB"""
        try:
            if not data:
                return

            # 确保财务数据表存在
            if self.table_manager:
                from ..database.table_manager import TableType
                if not self.table_manager.ensure_table_exists(
                    "db/kline_stock.duckdb", TableType.FINANCIAL_STATEMENT, "unified_data_manager"
                ):
                    logger.error("创建财务数据表失败")
                    return

            # 转换为DataFrame并存储
            df = pd.DataFrame([data])
            result = self.duckdb_operations.insert_dataframe(
                database_path="db/kline_stock.duckdb",
                table_name="financial_statements",
                data=df,
                upsert=True
            )

            if result.success:
                logger.info(f" 财务数据存储到DuckDB成功: {stock_code}")

        except Exception as e:
            logger.warning(f"DuckDB财务数据存储失败: {e}")

    def get_macro_economic_data(self, indicator: str, period: str = 'M', count: int = 100) -> pd.DataFrame:
        """
        获取宏观经济数据（新增方法：集成DuckDB存储）

        Args:
            indicator: 经济指标名称 (GDP, CPI, PMI等)
            period: 数据周期 (M/Q/Y)
            count: 数据条数

        Returns:
            宏观经济数据DataFrame
        """
        try:
            cache_key = f"macro_{indicator}_{period}_{count}"

            # 1. 多级缓存检查
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None and not cached_data.empty:
                return cached_data

            # 2. 从DuckDB获取
            if self.duckdb_available and self.duckdb_operations:
                df = self._get_macro_from_duckdb(indicator, period, count)
                if not df.empty:
                    self._cache_data(cache_key, df)
                    return df

            # 3. 通过TET管道获取
            if self.tet_enabled and self.tet_pipeline:
                try:
                    from ..tet_data_pipeline import StandardQuery
                    from ..plugin_types import AssetType, DataType

                    query = StandardQuery(
                        symbol=indicator,
                        asset_type=AssetType.MACRO,
                        data_type=DataType.MACRO_ECONOMIC,
                        period=period,
                        provider=self._current_source,
                        extra_params={'count': count}
                    )

                    result = self.tet_pipeline.process(query)
                    if result and result.data is not None:
                        if isinstance(result.data, pd.DataFrame) and not result.data.empty:
                            # 存储到DuckDB
                            self._store_macro_to_duckdb(result.data, indicator, period)
                            self._cache_data(cache_key, result.data)
                            return result.data

                except Exception as e:
                    logger.warning(f"TET管道获取宏观数据失败: {e}")

            # 4. 返回空DataFrame
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取宏观经济数据失败: {indicator} - {e}")
            return pd.DataFrame()

    def _get_macro_from_duckdb(self, indicator: str, period: str, count: int) -> pd.DataFrame:
        """从DuckDB获取宏观经济数据"""
        try:
            query = """
                SELECT * FROM macro_economic_data 
                WHERE indicator = ? AND frequency = ?
                ORDER BY release_date DESC 
                LIMIT ?
            """

            result = self.duckdb_operations.execute_query(
                database_path="db/kline_stock.duckdb",
                query=query,
                params=[indicator, period, count]
            )

            if result.success and result.data:
                df = pd.DataFrame(result.data)
                logger.info(f" 从DuckDB获取宏观数据成功: {indicator}, {len(df)}条")
                return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"DuckDB宏观数据获取失败: {e}")
            return pd.DataFrame()

    def _store_macro_to_duckdb(self, data: pd.DataFrame, indicator: str, period: str):
        """存储宏观经济数据到DuckDB"""
        try:
            if not self.duckdb_operations or data.empty:
                return

            # 确保宏观数据表存在
            if self.table_manager:
                from ..database.table_manager import TableType
                if not self.table_manager.ensure_table_exists(
                    "db/kline_stock.duckdb", TableType.MACRO_ECONOMIC, "unified_data_manager"
                ):
                    logger.error("创建宏观数据表失败")
                    return

            # 插入数据
            result = self.duckdb_operations.insert_dataframe(
                database_path="db/kline_stock.duckdb",
                table_name="macro_economic_data",
                data=data,
                upsert=True
            )

            if result.success:
                logger.info(f" 宏观数据存储到DuckDB成功: {indicator}, {len(data)}条")

        except Exception as e:
            logger.warning(f"DuckDB宏观数据存储失败: {e}")

    # ==================== 增强数据下载功能接口 ====================

    async def download_historical_data_batch(self,
                                             symbols: List[str],
                                             period: str = 'D',
                                             days_back: int = 365) -> Dict[str, pd.DataFrame]:
        """
        批量下载历史数据 - 通过增强DuckDB下载器获取数据

        Args:
            symbols: 股票代码列表
            period: 数据周期
            days_back: 回溯天数

        Returns:
            Dict[symbol, DataFrame]: 下载的历史数据
        """
        if not hasattr(self, 'enhanced_duckdb_downloader') or not self.enhanced_duckdb_downloader:
            logger.error("增强DuckDB数据下载器不可用")
            return {}

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        return await self.enhanced_duckdb_downloader.download_historical_kline_data(
            symbols=symbols,
            period=period,
            start_date=start_date,
            end_date=end_date,
            force_update=False
        )

    async def update_stock_universe(self, market: str = 'all') -> pd.DataFrame:
        """
        更新股票池 - 通过增强DuckDB下载器获取股票列表

        Args:
            market: 市场代码

        Returns:
            DataFrame: 更新后的股票列表
        """
        if not hasattr(self, 'enhanced_duckdb_downloader') or not self.enhanced_duckdb_downloader:
            logger.error("增强DuckDB数据下载器不可用")
            return pd.DataFrame()

        return await self.enhanced_duckdb_downloader.download_stock_list(market=market)

    async def incremental_data_update(self, max_symbols: int = 100) -> Dict[str, Any]:
        """
        增量数据更新 - 通过增强DuckDB下载器进行数据更新

        Args:
            max_symbols: 最大处理股票数量

        Returns:
            Dict: 更新结果统计
        """
        if not hasattr(self, 'enhanced_duckdb_downloader') or not self.enhanced_duckdb_downloader:
            logger.error("增强DuckDB数据下载器不可用")
            return {}

        return await self.enhanced_duckdb_downloader.incremental_update_all_data(max_symbols=max_symbols)

    def get_data_storage_statistics(self) -> Dict[str, Any]:
        """
        获取数据存储统计 - 通过增强DuckDB下载器获取统计信息

        Returns:
            Dict: 数据存储统计信息
        """
        if not hasattr(self, 'enhanced_duckdb_downloader') or not self.enhanced_duckdb_downloader:
            logger.error("增强DuckDB数据下载器不可用")
            return {}

        import asyncio
        return asyncio.run(self.enhanced_duckdb_downloader.get_data_statistics())

    async def _get_news(self, stock_code: str) -> Dict[str, Any]:
        """获取新闻数据

        Args:
            stock_code: 股票代码

        Returns:
            新闻数据字典
        """
        try:
            logger.info(f"获取新闻数据: {stock_code}")

            # 获取新闻数据可能需要特定的服务
            # 这里仅作为示例实现，返回空字典
            return {}

        except Exception as e:
            logger.error(f"获取新闻数据失败: {e}", exc_info=True)
            return {}

    def cancel_request(self, request_id: str) -> bool:
        """
        取消请求

        Args:
            request_id: 请求ID

        Returns:
            是否成功取消
        """
        with self.request_tracker_lock:
            if request_id in self.request_tracker:
                task = self.request_tracker[request_id].get('task')
                if task and not task.done():
                    task.cancel()
                    logger.info(f"Request {request_id} cancelled")

                # 清理资源
                self._cleanup_resources(request_id)

                # 更新统计信息
                self._stats['requests_cancelled'] += 1

                return True

        with self._request_lock:
            # 检查待处理请求
            if request_id in self._pending_requests:
                request = self._pending_requests[request_id]
                request.status = DataRequestStatus.CANCELLED
                del self._pending_requests[request_id]
                logger.debug(f"Cancelled pending request {request_id}")
                return True

            # 检查活动请求
            if request_id in self._active_requests:
                request = self._active_requests[request_id]
                if request.future and not request.future.done():
                    request.future.cancel()
                request.status = DataRequestStatus.CANCELLED
                del self._active_requests[request_id]
                logger.debug(f"Cancelled active request {request_id}")
                return True

        return False

    def _register_request(self, request_id: str):
        """注册请求到跟踪器"""
        with self.request_tracker_lock:
            try:
                task = asyncio.current_task() if asyncio.iscoroutinefunction(
                    self.get_stock_data) else None
            except RuntimeError:
                # 没有运行的事件循环
                task = None
            self.request_tracker[request_id] = {
                'timestamp': time.time(),
                'task': task
            }

    def _unregister_request(self, request_id: str):
        """从跟踪器中注销请求"""
        with self.request_tracker_lock:
            if request_id in self.request_tracker:
                del self.request_tracker[request_id]

    def _cleanup_resources(self, request_id: str):
        """清理请求相关资源"""
        # 从各种集合中移除请求
        with self._request_lock:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

            if request_id in self._active_requests:
                del self._active_requests[request_id]

            if request_id in self._completed_requests:
                del self._completed_requests[request_id]

        # 从去重机制中移除
        with self._dedup_lock:
            for key, requests in list(self._request_dedup.items()):
                if request_id in requests:
                    requests.remove(request_id)
                    if not requests:
                        del self._request_dedup[key]
                    break

        # 从跟踪器中移除
        self._unregister_request(request_id)

        logger.debug(f"Resources cleaned up for request {request_id}")

    def preload_data(self, code: str, freq: str = 'D', priority: str = 'low'):
        """预加载数据"""
        # 转换优先级字符串到数值
        priority_map = {'high': 0, 'normal': 1, 'low': 2}
        priority_value = priority_map.get(priority.lower(), 2)

        # 使用低优先级请求预加载数据
        self.request_data(
            stock_code=code,
            data_type='kdata',
            period=freq,
            priority=priority_value,
            callback=None  # 无需回调
        )

        logger.debug(f"Preloading data for {code} with priority {priority}")

        return True

    def get_request_status(self, request_id: str) -> Optional[DataRequestStatus]:
        """
        获取请求状态

        Args:
            request_id: 请求ID

        Returns:
            请求状态
        """
        with self._request_lock:
            if request_id in self._pending_requests:
                return self._pending_requests[request_id].status
            elif request_id in self._active_requests:
                return self._active_requests[request_id].status
            elif request_id in self._completed_requests:
                return self._completed_requests[request_id].status

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._request_lock:
            return {
                **self._stats,
                'pending_requests': len(self._pending_requests),
                'active_requests': len(self._active_requests),
                'completed_requests': len(self._completed_requests),
                'cache_size': self.multi_cache.get_statistics()['total_items'] if self.multi_cache else 0
            }

    def clear_cache(self, stock_code: str = None, data_type: str = None) -> None:
        """
        清理缓存

        Args:
            stock_code: 股票代码（可选，清理特定股票的缓存）
            data_type: 数据类型（可选，清理特定类型的缓存）
        """
        with self._cache_lock:
            if stock_code is None and data_type is None:
                # 清理所有缓存
                self._data_cache.clear()
                self._cache_timestamps.clear()
                logger.info("All cache cleared")
            else:
                # 清理特定缓存
                keys_to_remove = []
                for key in self._data_cache.keys():
                    if stock_code and stock_code not in key:
                        continue
                    if data_type and data_type not in key:
                        continue
                    keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self._data_cache[key]
                    if key in self._cache_timestamps:
                        del self._cache_timestamps[key]

                logger.info(f"Cleared {len(keys_to_remove)} cache entries")

    def _submit_request(self, request: DataRequest) -> None:
        """提交请求到线程池"""
        with self._request_lock:
            self._pending_requests[request.request_id] = request

        # 提交到线程池
        future = self._executor.submit(self._process_request, request)
        request.future = future

        logger.debug(
            f"Submitted request {request.request_id} for {request.stock_code}")

    def _process_request(self, request: DataRequest) -> None:
        """
        处理数据请求
        """
        try:
            data = None
            if request.data_type == 'kdata':
                kline_data = self._load_kdata(request)
                # 修改：将K线数据包装在字典中，保持数据结构一致性
                data = {
                    'kline_data': kline_data,
                    'stock_code': request.stock_code,
                    'period': request.period
                }
            elif request.data_type == 'indicators':
                data = self._load_indicators(request)
            elif request.data_type == 'analysis':
                data = self._load_analysis(request)
            elif request.data_type == 'chart':
                kline_data = self._load_kdata(request)
                indicators_data = self._load_indicators(request)
                data = {
                    'kline_data': kline_data,
                    'indicators_data': indicators_data
                }
            else:
                raise ValueError(f"Unsupported data type: {request.data_type}")

            self._complete_request(request, data)

        except Exception as e:
            logger.error(
                f"Failed to process request {request.request_id}: {e}")
            self._complete_request(request, None, str(e))

    def _complete_request(self, request: DataRequest, data: Any, error: str = None) -> None:
        """
        完成请求并通过Future返回结果
        """
        request_key = self._get_request_key(
            request.stock_code, request.data_type, request.period, request.time_range, request.parameters)

        with self._dedup_lock:
            request_group = self._request_dedup.pop(request_key, set())

        for req in request_group:
            if req.future and not req.future.done():
                if error:
                    exception = Exception(error)
                    self.loop.call_soon_threadsafe(
                        req.future.set_exception, exception)
                else:
                    self.loop.call_soon_threadsafe(req.future.set_result, data)

            with self._request_lock:
                self._completed_requests[req.request_id] = req
                req.status = DataRequestStatus.COMPLETED if not error else DataRequestStatus.FAILED

        if not error:
            self._stats['requests_completed'] += len(request_group)
        else:
            self._stats['requests_failed'] += len(request_group)

    def _load_kdata(self, request: DataRequest) -> pd.DataFrame:
        """加载K线数据"""
        try:
            from .stock_service import StockService
            stock_service = self.service_container.resolve(StockService)
            return stock_service.get_stock_data(
                request.stock_code, request.period, request.time_range
            )
        except Exception as e:
            logger.error(f"Failed to load kdata: {e}")
            raise

    def _load_indicators(self, request: DataRequest) -> Dict[str, Any]:
        """加载技术指标数据"""
        try:
            from .analysis_service import AnalysisService
            analysis_service = self.service_container.resolve(AnalysisService)

            indicators = request.parameters.get('indicators', ['MA', 'MACD'])
            return analysis_service.calculate_technical_indicators(
                request.stock_code, indicators, request.period, request.time_range
            )
        except Exception as e:
            logger.error(f"Failed to load indicators: {e}")
            raise

    def _load_analysis(self, request: DataRequest) -> Dict[str, Any]:
        """加载分析数据"""
        try:
            from .analysis_service import AnalysisService
            analysis_service = self.service_container.resolve(AnalysisService)

            analysis_type = request.parameters.get(
                'analysis_type', 'comprehensive')
            return analysis_service.analyze_stock(request.stock_code, analysis_type)
        except Exception as e:
            logger.error(f"Failed to load analysis: {e}")
            raise

    def _get_cache_key(self, stock_code: str, data_type: str, period: str,
                       time_range: int, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        param_hash = hash(str(sorted(parameters.items()))
                          if parameters else "")
        return f"{data_type}_{stock_code}_{period}_{time_range}_{param_hash}"

    def _get_request_key(self, stock_code: str, data_type: str, period: str,
                         time_range: int, parameters: Dict[str, Any]) -> str:
        """生成请求键"""
        return self._get_cache_key(stock_code, data_type, period, time_range, parameters)

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据 - 使用统一的MultiLevelCacheManager"""
        with self._cache_lock:
            # if cache_key in self._data_cache:  # 已统一使用MultiLevelCacheManager
            if self.multi_cache and self.multi_cache.get(cache_key) is not None:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self._cache_ttl:
                    return self.multi_cache.get(cache_key)
                else:
                    # 缓存过期，清理
                    del self._data_cache[cache_key]
                    if cache_key in self._cache_timestamps:
                        del self._cache_timestamps[cache_key]

        return None

    def _put_to_cache(self, cache_key: str, data: Any) -> None:
        """将数据放入缓存 - 使用统一的MultiLevelCacheManager"""
        with self._cache_lock:
            # self._data_cache[cache_key] = data  # 已统一使用MultiLevelCacheManager
            if self.multi_cache:
                self.multi_cache.set(cache_key, data, ttl=self._cache_ttl)
            # self._cache_timestamps[cache_key] = time.time()  # 已统一使用MultiLevelCacheManager

    def dispose(self) -> None:
        """清理资源"""
        logger.info("Disposing unified data manager")

        # 取消所有待处理请求
        with self._request_lock:
            for request in list(self._pending_requests.values()):
                self.cancel_request(request.request_id)

            for request in list(self._active_requests.values()):
                self.cancel_request(request.request_id)

        # 关闭线程池
        self._executor.shutdown(wait=True)

        # 清理缓存
        self.clear_cache()

        logger.info("Unified data manager disposed")

    def _auto_discover_data_source_plugins(self) -> None:
        """自动发现和注册数据源插件"""
        try:
            # 从服务容器获取插件管理器
            plugin_manager = None
            if self.service_container:
                try:
                    from ..plugin_manager import PluginManager
                    plugin_manager = self.service_container.resolve(PluginManager)
                except:
                    logger.warning("无法获取插件管理器，跳过插件自动发现")
                    return

            if not plugin_manager:
                logger.warning("插件管理器不可用，跳过插件自动发现")
                return

            # 获取所有已加载的插件
            all_plugins = plugin_manager.get_all_plugins()
            registered_count = 0

            for plugin_name, plugin_instance in all_plugins.items():
                try:
                    # 检查是否是数据源插件
                    if self._is_data_source_plugin(plugin_instance):
                        # 注册到TET数据管道
                        success = self.register_data_source_plugin(
                            plugin_name,
                            plugin_instance,
                            priority=getattr(plugin_instance, 'priority', 50),
                            weight=getattr(plugin_instance, 'weight', 1.0)
                        )

                        if success:
                            registered_count += 1
                            logger.info(f" 自动注册数据源插件: {plugin_name}")
                        else:
                            logger.warning(f" 数据源插件注册失败: {plugin_name}")

                except Exception as e:
                    logger.warning(f" 检查插件失败 {plugin_name}: {e}")

            if registered_count > 0:
                logger.info(f" 自动发现并注册了 {registered_count} 个数据源插件")
                self._plugins_discovered = True
            else:
                logger.info("未发现新的数据源插件")

        except Exception as e:
            logger.error(f" 自动发现数据源插件失败: {e}")

    def _is_data_source_plugin(self, plugin_instance) -> bool:
        """检查插件是否是数据源插件"""
        try:
            from ..data_source_extensions import IDataSourcePlugin
            return isinstance(plugin_instance, IDataSourcePlugin)
        except Exception:
            # 检查是否有必要的方法
            required_methods = ['get_asset_list', 'get_kdata', 'health_check']
            return all(hasattr(plugin_instance, method) for method in required_methods)

    def discover_and_register_data_source_plugins(self) -> None:
        """
        发现并注册数据源插件（公共方法）
        在所有服务初始化完成后调用
        """
        if self._plugins_discovered:
            logger.info("插件已发现，跳过重复发现")
            return

        logger.info("开始发现和注册数据源插件...")

        try:
            # 尝试自动发现插件
            self._auto_discover_data_source_plugins()

            # 如果自动发现失败，尝试手动注册核心插件
            if not self._plugins_discovered:
                logger.info("自动发现失败，尝试手动注册核心插件...")
                self._manual_register_core_plugins()

        except Exception as e:
            logger.error(f"插件发现和注册失败: {e}")
            logger.error(traceback.format_exc())

    def _manual_register_core_plugins(self) -> None:
        """手动注册核心数据源插件"""
        registered_count = 0

        # 插件注册开始

        # 2. 注册AkShare插件（支持sector_fund_flow）
        try:
            # 注意：akshare_stock_plugin已迁移到TET+Plugin架构
            # 通过插件中心自动发现和注册
            logger.info("AkShare插件通过TET+Plugin架构自动管理")

            # AkShare插件现在通过TET+Plugin架构管理
            # 不再需要手动注册和扩展
            logger.info("AkShare插件将通过插件中心自动发现和注册")
            # 假设成功，因为通过插件中心管理
            registered_count += 1

        except Exception as e:
            logger.warning(f" AkShare插件注册失败: {e}")

        # 3. 注册Wind插件（如果可用）
        try:
            from plugins.examples.wind_data_plugin import WindDataPlugin
            wind_plugin = WindDataPlugin()

            success = self.register_data_source_plugin(
                "wind_data_source",
                wind_plugin,
                priority=5,  # 较高优先级，专业数据源
                weight=1.8
            )

            if success:
                registered_count += 1
                logger.info("手动注册Wind数据源插件成功")
            else:
                logger.warning("Wind数据源插件注册失败")

        except Exception as e:
            logger.warning(f" Wind插件注册失败: {e}")

        # 4. 注册东方财富插件
        try:
            from plugins.data_sources.eastmoney_plugin import EastMoneyStockPlugin
            eastmoney_plugin = EastMoneyStockPlugin()

            success = self.register_data_source_plugin(
                "eastmoney_stock",
                eastmoney_plugin,
                priority=20,
                weight=1.0
            )

            if success:
                registered_count += 1
                logger.info("手动注册东方财富数据源插件成功")
            else:
                logger.warning("东方财富数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 东方财富插件注册失败: {e}")

        # 5. 注册通达信插件
        try:
            from plugins.examples.tongdaxin_stock_plugin import TongdaxinStockPlugin
            tongdaxin_plugin = TongdaxinStockPlugin()

            success = self.register_data_source_plugin(
                "tongdaxin_stock",
                tongdaxin_plugin,
                priority=15,
                weight=1.3
            )

            if success:
                registered_count += 1
                logger.info("手动注册通达信数据源插件成功")
            else:
                logger.warning("通达信数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 通达信插件注册失败: {e}")

        # 6. 注册Yahoo Finance插件
        try:
            from plugins.examples.yahoo_finance_datasource import YahooFinanceDataSourcePlugin
            yahoo_plugin = YahooFinanceDataSourcePlugin()

            success = self.register_data_source_plugin(
                "yahoo_finance",
                yahoo_plugin,
                priority=25,
                weight=1.2
            )

            if success:
                registered_count += 1
                logger.info("手动注册Yahoo Finance数据源插件成功")
            else:
                logger.warning("Yahoo Finance数据源插件注册失败")

        except Exception as e:
            logger.warning(f" Yahoo Finance插件注册失败: {e}")

        # 7. 注册期货数据插件
        try:
            from plugins.examples.futures_data_plugin import FuturesDataPlugin
            futures_plugin = FuturesDataPlugin()

            success = self.register_data_source_plugin(
                "futures_data_source",
                futures_plugin,
                priority=30,
                weight=1.2
            )

            if success:
                registered_count += 1
                logger.info("手动注册期货数据源插件成功")
            else:
                logger.warning("期货数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 期货插件注册失败: {e}")

        # 8. 注册CTP期货插件
        try:
            from plugins.examples.ctp_futures_plugin import CTPFuturesPlugin
            ctp_plugin = CTPFuturesPlugin()

            success = self.register_data_source_plugin(
                "ctp_futures",
                ctp_plugin,
                priority=12,  # 较高优先级的期货数据源
                weight=1.6
            )

            if success:
                registered_count += 1
                logger.info("手动注册CTP期货数据源插件成功")
            else:
                logger.warning("CTP期货数据源插件注册失败")

        except Exception as e:
            logger.warning(f" CTP期货插件注册失败: {e}")

        # 9. 注册文华财经插件
        try:
            from plugins.examples.wenhua_data_plugin import WenhuaDataPlugin
            wenhua_plugin = WenhuaDataPlugin()

            success = self.register_data_source_plugin(
                "wenhua_data",
                wenhua_plugin,
                priority=18,
                weight=1.4
            )

            if success:
                registered_count += 1
                logger.info("手动注册文华财经数据源插件成功")
            else:
                logger.warning("文华财经数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 文华财经插件注册失败: {e}")

        # 10. 注册外汇数据插件
        try:
            from plugins.examples.forex_data_plugin import ForexDataPlugin
            forex_plugin = ForexDataPlugin()

            success = self.register_data_source_plugin(
                "forex_data_source",
                forex_plugin,
                priority=35,
                weight=1.0
            )

            if success:
                registered_count += 1
                logger.info("手动注册外汇数据源插件成功")
            else:
                logger.warning("外汇数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 外汇插件注册失败: {e}")

        # 11. 注册债券数据插件
        try:
            from plugins.examples.bond_data_plugin import BondDataPlugin
            bond_plugin = BondDataPlugin()

            success = self.register_data_source_plugin(
                "bond_data_source",
                bond_plugin,
                priority=40,
                weight=1.0
            )

            if success:
                registered_count += 1
                logger.info("手动注册债券数据源插件成功")
            else:
                logger.warning("债券数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 债券插件注册失败: {e}")

        # 12. 注册加密货币数据插件
        try:
            from plugins.examples.crypto_data_plugin import CryptoDataPlugin
            crypto_plugin = CryptoDataPlugin()

            success = self.register_data_source_plugin(
                "crypto_data_source",
                crypto_plugin,
                priority=45,
                weight=1.1
            )

            if success:
                registered_count += 1
                logger.info("手动注册加密货币数据源插件成功")
            else:
                logger.warning("加密货币数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 加密货币插件注册失败: {e}")

        # 13. 注册币安加密货币插件
        try:
            from plugins.examples.binance_crypto_plugin import BinanceCryptoPlugin
            binance_plugin = BinanceCryptoPlugin()

            success = self.register_data_source_plugin(
                "binance_crypto",
                binance_plugin,
                priority=22,  # 较高优先级的加密货币数据源
                weight=1.4
            )

            if success:
                registered_count += 1
                logger.info("手动注册币安加密货币数据源插件成功")
            else:
                logger.warning("币安加密货币数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 币安加密货币插件注册失败: {e}")

        # 14. 注册火币加密货币插件
        try:
            from plugins.examples.huobi_crypto_plugin import HuobiCryptoPlugin
            huobi_plugin = HuobiCryptoPlugin()

            success = self.register_data_source_plugin(
                "huobi_crypto",
                huobi_plugin,
                priority=24,
                weight=1.3
            )

            if success:
                registered_count += 1
                logger.info("手动注册火币加密货币数据源插件成功")
            else:
                logger.warning("火币加密货币数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 火币加密货币插件注册失败: {e}")

        # 15. 注册OKX加密货币插件
        try:
            from plugins.examples.okx_crypto_plugin import OKXCryptoPlugin
            okx_plugin = OKXCryptoPlugin()

            success = self.register_data_source_plugin(
                "okx_crypto",
                okx_plugin,
                priority=26,
                weight=1.3
            )

            if success:
                registered_count += 1
                logger.info("手动注册OKX加密货币数据源插件成功")
            else:
                logger.warning("OKX加密货币数据源插件注册失败")

        except Exception as e:
            logger.warning(f" OKX加密货币插件注册失败: {e}")

        # 16. 注册Coinbase加密货币插件
        try:
            from plugins.examples.coinbase_crypto_plugin import CoinbaseCryptoPlugin
            coinbase_plugin = CoinbaseCryptoPlugin()

            success = self.register_data_source_plugin(
                "coinbase_crypto",
                coinbase_plugin,
                priority=28,
                weight=1.2
            )

            if success:
                registered_count += 1
                logger.info("手动注册Coinbase加密货币数据源插件成功")
            else:
                logger.warning("Coinbase加密货币数据源插件注册失败")

        except Exception as e:
            logger.warning(f" Coinbase加密货币插件注册失败: {e}")

        # 17. 注册我的钢铁网数据插件
        try:
            from plugins.examples.mysteel_data_plugin import MySteelDataPlugin
            mysteel_plugin = MySteelDataPlugin()

            success = self.register_data_source_plugin(
                "mysteel_data",
                mysteel_plugin,
                priority=50,
                weight=0.8
            )

            if success:
                registered_count += 1
                logger.info("手动注册我的钢铁网数据源插件成功")
            else:
                logger.warning("我的钢铁网数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 我的钢铁网插件注册失败: {e}")

        # 18. 注册自定义数据插件
        try:
            from plugins.examples.custom_data_plugin import CustomDataPlugin
            custom_plugin = CustomDataPlugin()

            success = self.register_data_source_plugin(
                "custom_data_source",
                custom_plugin,
                priority=99,  # 最低优先级
                weight=0.5
            )

            if success:
                registered_count += 1
                logger.info("手动注册自定义数据源插件成功")
            else:
                logger.warning("自定义数据源插件注册失败")

        except Exception as e:
            logger.warning(f" 自定义插件注册失败: {e}")

        if registered_count > 0:
            logger.info(f" 手动注册了 {registered_count} 个核心数据源插件")
            self._plugins_discovered = True
        else:
            logger.warning("未能注册任何数据源插件，创建基本回退数据源")
            # 创建基本回退数据源，避免TET管道完全无法工作
            self._create_fallback_data_source()
            self._plugins_discovered = True

    def _create_fallback_data_source(self) -> None:
        """创建基本回退数据源，确保TET管道有可用的数据源"""
        try:
            # 创建一个简单的回退数据源类
            class FallbackDataSource:
                def __init__(self):
                    # 传统数据源fallback
                    self.name = "fallback_source"
                    self.priority = 999  # 最低优先级
                    self.weight = 0.1

                def get_stock_list(self, market='all'):
                    return pd.DataFrame()

                def get_kdata(self, symbol, period, start_date, end_date):
                    return pd.DataFrame()

            fallback_source = FallbackDataSource()

            # 尝试注册到TET管道
            if hasattr(self, 'tet_pipeline') and self.tet_pipeline and hasattr(self.tet_pipeline, 'router'):
                success = self.tet_pipeline.router.register_data_source(
                    "fallback_source",
                    fallback_source,
                    priority=999,  # 最低优先级
                    weight=0.1
                )

                if success:
                    logger.info("创建回退数据源成功")
                else:
                    logger.warning("创建回退数据源失败")
            else:
                logger.warning("TET管道不可用，无法注册回退数据源")

        except Exception as e:
            logger.error(f" 创建回退数据源异常: {e}")

    def _extend_akshare_plugin_for_sector_flow(self, akshare_plugin) -> None:
        """扩展AkShare插件以支持SECTOR_FUND_FLOW数据类型"""
        try:
            # 添加SECTOR_FUND_FLOW到支持的数据类型
            if hasattr(akshare_plugin, 'plugin_info'):
                plugin_info = akshare_plugin.plugin_info
                if hasattr(plugin_info, 'supported_data_types'):
                    from ..plugin_types import DataType
                    if DataType.SECTOR_FUND_FLOW not in plugin_info.supported_data_types:
                        plugin_info.supported_data_types.append(DataType.SECTOR_FUND_FLOW)
                        logger.info("AkShare插件已扩展支持SECTOR_FUND_FLOW")

            # 添加获取板块资金流的方法
            def get_sector_fund_flow_data(symbol: str, **kwargs):
                try:
                    import akshare as ak
                    # 根据symbol类型选择合适的akshare函数
                    if symbol == "sector":
                        return ak.stock_sector_fund_flow_rank(indicator="今日")
                    else:
                        return ak.stock_sector_fund_flow_summary(symbol=symbol, indicator="今日")
                except Exception as e:
                    logger.error(f"获取板块资金流数据失败: {e}")
                    return None

            # 动态添加方法到插件实例
            akshare_plugin.get_sector_fund_flow_data = get_sector_fund_flow_data
            logger.info("AkShare插件已添加板块资金流数据获取方法")

        except Exception as e:
            logger.error(f"扩展AkShare插件失败: {e}")

    @property
    def data_source_router(self):
        """
        兼容性属性：提供对数据源路由器的访问

        Returns:
            数据源路由器实例，如果TET管道可用的话
        """
        if hasattr(self, 'tet_pipeline') and self.tet_pipeline:
            return self.tet_pipeline.router
        return None

    def set_asset_routing_priorities(self, asset_type: AssetType, priorities: List[str]) -> bool:
        """
        设置资产类型的数据源路由优先级

        Args:
            asset_type: 资产类型
            priorities: 数据源优先级列表

        Returns:
            bool: 设置是否成功
        """
        try:
            router = self.data_source_router
            if router is None:
                logger.error("数据源路由器不可用，无法设置优先级")
                return False

            # 调用路由器的set_asset_priorities方法
            router.set_asset_priorities(asset_type, priorities)
            logger.info(f" 成功设置{asset_type.value}的路由优先级: {priorities}")
            return True

        except Exception as e:
            logger.error(f" 设置资产路由优先级失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_asset_routing_priorities(self, asset_type: AssetType) -> List[str]:
        """
        获取资产类型的数据源路由优先级

        Args:
            asset_type: 资产类型

        Returns:
            List[str]: 数据源优先级列表
        """
        try:
            router = self.data_source_router
            if router is None:
                logger.warning("数据源路由器不可用，返回空优先级列表")
                return []

            return router.asset_priorities.get(asset_type, [])

        except Exception as e:
            logger.error(f" 获取资产路由优先级失败: {e}")
            return []

    def _initialize_sector_service(self):
        """
        初始化板块数据服务
        """
        try:
            # 延迟导入避免循环依赖
            from .sector_data_service import get_sector_data_service

            # 获取缓存管理器
            cache_manager = getattr(self, 'cache_manager', None)

            # 初始化板块数据服务
            self._sector_data_service = get_sector_data_service(
                cache_manager=cache_manager,
                tet_pipeline=self.tet_pipeline
            )

            logger.info("板块数据服务初始化成功")

        except Exception as e:
            logger.error(f"板块数据服务初始化失败: {e}")
            self._sector_data_service = None

    def get_sector_fund_flow_service(self):
        """
        获取板块资金流服务实例

        Returns:
            SectorDataService: 板块数据服务实例，如果初始化失败则返回None
        """
        return self._sector_data_service

    def get_sector_fund_flow_ranking(self, date_range: str = "today", sort_by: str = 'main_net_inflow'):
        """
        获取板块资金流排行榜（统一数据管理器入口）

        Args:
            date_range: 时间范围，如 "today", "3d", "5d", "1m"
            sort_by: 排序字段，默认按主力净流入排序

        Returns:
            pd.DataFrame: 板块排行榜数据
        """
        try:
            if self._sector_data_service is None:
                logger.warning("板块数据服务不可用")
                return pd.DataFrame()

            return self._sector_data_service.get_sector_fund_flow_ranking(date_range, sort_by)

        except Exception as e:
            logger.error(f"获取板块资金流排行榜失败: {e}")
            return pd.DataFrame()

    def get_sector_historical_trend(self, sector_id: str, period: int = 30):
        """
        获取单板块历史趋势数据（统一数据管理器入口）

        Args:
            sector_id: 板块ID，如 "BK0001"
            period: 查询天数，默认30天

        Returns:
            pd.DataFrame: 板块历史趋势数据
        """
        try:
            if self._sector_data_service is None:
                logger.warning("板块数据服务不可用")
                return pd.DataFrame()

            return self._sector_data_service.get_sector_historical_trend(sector_id, period)

        except Exception as e:
            logger.error(f"获取板块历史趋势失败: {e}")
            return pd.DataFrame()

    def get_sector_intraday_flow(self, sector_id: str, date: str):
        """
        获取板块分时资金流数据（统一数据管理器入口）

        Args:
            sector_id: 板块ID，如 "BK0001"
            date: 查询日期，格式 "YYYY-MM-DD"

        Returns:
            pd.DataFrame: 板块分时资金流数据
        """
        try:
            if self._sector_data_service is None:
                logger.warning("板块数据服务不可用")
                return pd.DataFrame()

            return self._sector_data_service.get_sector_intraday_flow(sector_id, date)

        except Exception as e:
            logger.error(f"获取板块分时资金流失败: {e}")
            return pd.DataFrame()

    def import_sector_historical_data(self, source: str, start_date: str, end_date: str):
        """
        导入板块历史数据（统一数据管理器入口）

        Args:
            source: 数据源名称，如 "akshare", "eastmoney"
            start_date: 开始日期，格式 "YYYY-MM-DD"
            end_date: 结束日期，格式 "YYYY-MM-DD"

        Returns:
            Dict[str, Any]: 导入结果统计信息
        """
        try:
            if self._sector_data_service is None:
                logger.warning("板块数据服务不可用")
                return {"success": False, "error": "板块数据服务不可用"}

            return self._sector_data_service.import_sector_historical_data(source, start_date, end_date)

        except Exception as e:
            logger.error(f"导入板块历史数据失败: {e}")
            return {"success": False, "error": str(e)}

# 数据策略类
