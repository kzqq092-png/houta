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

from ..events import EventBus, DataUpdateEvent
from ..containers import ServiceContainer

logger = logging.getLogger(__name__)


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
    stock_code: str
    data_type: str  # 'kdata', 'indicators', 'analysis'
    period: str = 'D'
    time_range: int = 365
    parameters: Dict[str, Any] = None
    priority: int = 0  # 0=高优先级, 1=中优先级, 2=低优先级
    callback: Optional[Callable] = None
    timestamp: float = 0
    status: DataRequestStatus = DataRequestStatus.PENDING
    future: Optional[Future] = None

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.parameters is None:
            self.parameters = {}


class UnifiedDataManager:
    """
    统一数据管理器

    功能：
    1. 协调数据加载请求
    2. 避免重复数据加载
    3. 提供统一的数据访问接口
    4. 管理数据缓存
    5. 优化数据加载性能
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

        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="DataManager")

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
        self._request_dedup: Dict[str, Set[str]] = {}  # 请求键 -> 请求ID集合
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

        logger.info("Unified data manager initialized")

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

    def request_data(self, stock_code: str, data_type: str, period: str = 'D',
                     time_range: int = 365, parameters: Dict[str, Any] = None,
                     priority: int = 1, callback: Optional[Callable] = None) -> str:
        """
        请求数据

        Args:
            stock_code: 股票代码
            data_type: 数据类型 ('kdata', 'indicators', 'analysis')
            period: 周期
            time_range: 时间范围
            parameters: 额外参数
            priority: 优先级 (0=高, 1=中, 2=低)
            callback: 回调函数

        Returns:
            请求ID
        """
        # 生成请求ID
        request_id = f"{data_type}_{stock_code}_{period}_{time_range}_{hash(str(parameters or {}))}"

        # 检查缓存
        cache_key = self._get_cache_key(stock_code, data_type, period, time_range, parameters)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            self._stats['cache_hits'] += 1
            logger.debug(f"Cache hit for {cache_key}")

            # 立即回调
            if callback:
                try:
                    callback(cached_data)
                except Exception as e:
                    logger.error(f"Error in callback for cached data: {e}")

            return request_id

        self._stats['cache_misses'] += 1

        # 创建数据请求
        request = DataRequest(
            request_id=request_id,
            stock_code=stock_code,
            data_type=data_type,
            period=period,
            time_range=time_range,
            parameters=parameters or {},
            priority=priority,
            callback=callback
        )

        # 注册请求到跟踪器
        self._register_request(request_id)

        # 检查是否有重复请求
        request_key = self._get_request_key(stock_code, data_type, period, time_range, parameters)

        with self._dedup_lock:
            if request_key in self._request_dedup:
                # 有重复请求，添加到现有请求组
                self._request_dedup[request_key].add(request_id)
                self._stats['requests_deduplicated'] += 1
                logger.debug(f"Deduplicated request {request_id} with key {request_key}")
            else:
                # 新请求
                self._request_dedup[request_key] = {request_id}

                # 提交请求
                self._submit_request(request)

        self._stats['requests_total'] += 1
        return request_id

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
                task = asyncio.current_task() if asyncio.iscoroutinefunction(self.get_stock_data) else None
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

        logger.debug(f"Submitted request {request.request_id} for {request.stock_code}")

    def _process_request(self, request: DataRequest) -> None:
        """处理数据请求"""
        try:
            # 移动到活动请求
            with self._request_lock:
                if request.request_id in self._pending_requests:
                    del self._pending_requests[request.request_id]
                    self._active_requests[request.request_id] = request
                    request.status = DataRequestStatus.LOADING

            logger.debug(f"Processing request {request.request_id}")

            # 根据数据类型加载数据
            if request.data_type == 'kdata':
                data = self._load_kdata(request)
            elif request.data_type == 'indicators':
                data = self._load_indicators(request)
            elif request.data_type == 'analysis':
                data = self._load_analysis(request)
            else:
                raise ValueError(f"Unknown data type: {request.data_type}")

            # 缓存数据
            cache_key = self._get_cache_key(
                request.stock_code, request.data_type, request.period,
                request.time_range, request.parameters
            )
            self._put_to_cache(cache_key, data)

            # 处理完成
            request.status = DataRequestStatus.COMPLETED
            self._complete_request(request, data)

            logger.debug(f"Completed request {request.request_id}")

        except Exception as e:
            logger.error(f"Failed to process request {request.request_id}: {e}")
            request.status = DataRequestStatus.FAILED
            self._complete_request(request, None, str(e))

    def _complete_request(self, request: DataRequest, data: Any, error: str = None) -> None:
        """完成请求处理"""
        # 移动到完成请求
        with self._request_lock:
            if request.request_id in self._active_requests:
                del self._active_requests[request.request_id]
                self._completed_requests[request.request_id] = request

        # 更新统计
        if request.status == DataRequestStatus.COMPLETED:
            self._stats['requests_completed'] += 1
        elif request.status == DataRequestStatus.FAILED:
            self._stats['requests_failed'] += 1

        # 处理重复请求
        request_key = self._get_request_key(
            request.stock_code, request.data_type, request.period,
            request.time_range, request.parameters
        )

        with self._dedup_lock:
            if request_key in self._request_dedup:
                request_ids = self._request_dedup[request_key]

                # 通知所有相关请求
                for req_id in request_ids:
                    if req_id in self._completed_requests:
                        req = self._completed_requests[req_id]
                        if req.callback:
                            try:
                                if error:
                                    req.callback(None, error)
                                else:
                                    req.callback(data)
                            except Exception as e:
                                logger.error(f"Error in callback for request {req_id}: {e}")

                # 清理去重记录
                del self._request_dedup[request_key]

        # 发布数据更新事件
        if data is not None:
            self.event_bus.publish(DataUpdateEvent(
                data_type=f"{request.data_type}_{request.stock_code}",
                stock_code=request.stock_code,
                update_info=data
            ))

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

            analysis_type = request.parameters.get('analysis_type', 'comprehensive')
            return analysis_service.analyze_stock(request.stock_code, analysis_type)
        except Exception as e:
            logger.error(f"Failed to load analysis: {e}")
            raise

    def _get_cache_key(self, stock_code: str, data_type: str, period: str,
                       time_range: int, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        param_hash = hash(str(sorted(parameters.items())) if parameters else "")
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
        logger.debug(f"Loading historical data for {code} from {start_date} to {end_date}")
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
