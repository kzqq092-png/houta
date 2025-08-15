"""
统一数据管理器

负责协调各服务的数据加载请求，避免重复数据加载，提供统一的数据访问接口。
"""

import logging
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

from ..events import EventBus, DataUpdateEvent
from ..containers import ServiceContainer, get_service_container
from ..plugin_types import AssetType, DataType
from ..tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData, create_tet_pipeline

logger = logging.getLogger(__name__)


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
        """向后兼容：股票代码"""
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
    """

    def __init__(self, service_container: ServiceContainer, event_bus: EventBus, max_workers: int = 3):
        """
        初始化统一数据管理器

        Args:
            service_container: 服务容器
            event_bus: 事件总线
            max_workers: 最大工作线程数
        """
        self.service_container = service_container
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

        # 数据缓存
        self._data_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5分钟缓存TTL

        # 去重机制
        self._request_dedup: Dict[str, Set[DataRequest]] = {}  # 请求键 -> 请求ID集合
        self._dedup_lock = threading.Lock()

        # 请求跟踪器 - 用于取消请求
        self.request_tracker: Dict[str, Dict[str, Any]] = {}
        self.request_tracker_lock = threading.Lock()

        # 数据策略
        self.history_data_strategy = HistoryDataStrategy()
        self.realtime_data_strategy = RealtimeDataStrategy()

        # 统计信息
        self._stats = {
            'requests_total': 0,
            'requests_deduplicated': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'requests_cancelled': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        # 数据源路由器
        self.data_source_router = None
        self._initialize_data_source_router()

        # TET数据管道支持
        self.tet_pipeline: Optional[TETDataPipeline] = None
        self.tet_enabled = False
        self._initialize_tet_pipeline()

        logger.info("Unified data manager initialized")

    def _initialize_data_source_router(self):
        """初始化数据源路由器"""
        try:
            from ..data_source_router import DataSourceRouter
            self.data_source_router = DataSourceRouter()
            logger.info("✅ 数据源路由器已初始化")
        except Exception as e:
            logger.warning(f"⚠️ 数据源路由器初始化失败: {e}")
            self.data_source_router = None

    def _initialize_tet_pipeline(self):
        """初始化TET数据管道"""
        try:
            logger.info("🔧 正在初始化TET数据管道...")

            # 尝试获取数据源路由器
            if hasattr(self, 'data_source_router') and self.data_source_router:
                router = self.data_source_router
                logger.info("✅ 使用本地数据源路由器")
            else:
                # 从服务容器获取
                logger.info("🔍 尝试从服务容器获取数据源路由器...")
                from ..data_source_router import DataSourceRouter
                try:
                    router = self.service_container.resolve(DataSourceRouter)
                    logger.info("✅ 从服务容器获取数据源路由器成功")
                except Exception as resolve_error:
                    logger.warning(f"⚠️ 从服务容器获取数据源路由器失败: {resolve_error}")
                    router = None

            if router:
                # 检查路由器中的数据源数量
                source_count = len(router.data_sources) if hasattr(router, 'data_sources') else 0
                logger.info(f"📊 数据源路由器状态: {source_count} 个数据源已注册")

                from ..tet_data_pipeline import create_tet_pipeline
                self.tet_pipeline = create_tet_pipeline(router)
                self.tet_enabled = True
                logger.info("🎉 TET数据管道已成功启用！")
                logger.info(f"🚀 TET模式已激活，支持多资产类型数据处理")
            else:
                logger.warning("❌ 数据源路由器不可用，TET管道未启用")
                logger.warning("💡 建议检查插件管理器和数据源注册")
                self.tet_enabled = False

        except Exception as e:
            logger.error(f"❌ TET数据管道初始化失败: {e}")
            logger.error("🔄 将使用传统数据获取模式")
            import traceback
            logger.debug(traceback.format_exc())
            self.tet_enabled = False

    def get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """
        获取资产列表（TET模式）

        Args:
            asset_type: 资产类型
            market: 市场过滤

        Returns:
            List[Dict]: 标准化的资产列表
        """
        if self.tet_enabled and self.tet_pipeline:
            try:
                query = StandardQuery(
                    symbol="",  # 资产列表查询不需要具体symbol
                    asset_type=asset_type,
                    data_type=DataType.ASSET_LIST,
                    market=market
                )

                result = self.tet_pipeline.process(query)
                return self._format_asset_list(result.data)

            except Exception as e:
                logger.warning(f"TET模式获取资产列表失败: {e}")

        # 降级到传统方式
        return self._legacy_get_asset_list(asset_type, market)

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
                logger.info(f"🚀 使用TET模式获取数据: {symbol} ({asset_type.value})")

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
                    logger.info(f"✅ TET数据获取成功: {symbol} | 数据源: {data_source} | 记录数: {len(result.data) if result.data is not None else 0}")
                else:
                    logger.info(f"✅ TET数据获取成功: {symbol} | 记录数: {len(result.data) if result.data is not None else 0}")

                return result.data

            except Exception as e:
                logger.warning(f"❌ TET模式获取数据失败: {symbol} - {e}")
                logger.info("🔄 降级到传统数据获取模式")

        # 降级到传统方式
        if asset_type == AssetType.STOCK:
            logger.info(f"📊 使用传统模式获取股票数据: {symbol}")
            data = self._legacy_get_stock_data(symbol, period, **kwargs)
            if data is not None:
                logger.info(f"✅ 传统模式数据获取成功: {symbol} | 数据源: HIkyuu/DataAccess | 记录数: {len(data)}")
            else:
                logger.warning(f"❌ 传统模式数据获取失败: {symbol}")
            return data
        else:
            logger.warning(f"❌ 传统模式不支持资产类型: {asset_type.value} | 建议启用TET模式")
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

    def _legacy_get_asset_list(self, asset_type: AssetType, market: str = None) -> List[Dict[str, Any]]:
        """传统方式获取资产列表"""
        try:
            if asset_type == AssetType.STOCK:
                # 使用传统的股票数据获取方式
                from ..data.data_access import DataAccess
                data_access = DataAccess()
                stock_list = data_access.get_stock_list()

                result = []
                for stock in stock_list:
                    result.append({
                        'symbol': stock.get('code', ''),
                        'name': stock.get('name', ''),
                        'asset_type': 'STOCK',
                        'market': stock.get('market', market or ''),
                        'status': 'active'
                    })
                return result
            else:
                logger.warning(f"传统模式不支持资产类型: {asset_type.value}")
                return []

        except Exception as e:
            logger.error(f"传统方式获取资产列表失败: {e}")
            return []

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

            # 如果没有ChartService，尝试使用数据源直接获取
            from core.data_manager import get_data_manager
            data_manager = get_data_manager()

            if data_manager:
                return data_manager.get_kdata(stock_code, period, count)

            logger.error("无法获取K线数据：未找到数据服务")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"获取K线数据失败: {e}", exc_info=True)
            return pd.DataFrame()

    async def _get_financial_data(self, stock_code: str) -> Dict[str, Any]:
        """获取财务数据

        Args:
            stock_code: 股票代码

        Returns:
            财务数据字典
        """
        try:
            logger.info(f"获取财务数据: {stock_code}")

            # 获取财务数据可能需要特定的服务
            # 这里仅作为示例实现，返回空字典
            return {}

        except Exception as e:
            logger.error(f"获取财务数据失败: {e}", exc_info=True)
            return {}

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
                'cache_size': len(self._data_cache)
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
        """从缓存获取数据"""
        with self._cache_lock:
            if cache_key in self._data_cache:
                timestamp = self._cache_timestamps.get(cache_key, 0)
                if time.time() - timestamp < self._cache_ttl:
                    return self._data_cache[cache_key]
                else:
                    # 缓存过期，清理
                    del self._data_cache[cache_key]
                    if cache_key in self._cache_timestamps:
                        del self._cache_timestamps[cache_key]

        return None

    def _put_to_cache(self, cache_key: str, data: Any) -> None:
        """将数据放入缓存"""
        with self._cache_lock:
            self._data_cache[cache_key] = data
            self._cache_timestamps[cache_key] = time.time()

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

# 数据策略类


class HistoryDataStrategy:
    """历史数据加载策略"""

    async def get_data(self, code: str, freq: str, start_date=None, end_date=None):
        """获取历史数据"""
        logger.debug(
            f"Loading historical data for {code} from {start_date} to {end_date}")
        # 实际实现应该调用相应的历史数据服务
        # 这里为示例实现
        try:
            # 模拟异步加载
            await asyncio.sleep(0.1)
            return {'type': 'historical', 'code': code, 'freq': freq, 'data': []}
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return None


class RealtimeDataStrategy:
    """实时数据加载策略"""

    async def get_data(self, code: str, freq: str, start_date=None, end_date=None):
        """获取实时数据"""
        logger.debug(f"Loading realtime data for {code}")
        # 实际实现应该调用实时行情服务
        # 这里为示例实现
        try:
            # 模拟异步加载
            await asyncio.sleep(0.2)
            return {'type': 'realtime', 'code': code, 'freq': freq, 'data': []}
        except Exception as e:
            logger.error(f"Error loading realtime data: {e}")
            return None
