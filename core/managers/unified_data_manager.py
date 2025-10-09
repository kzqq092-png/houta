"""
统一数据管理器实现

本模块实现了HIkyuu-UI系统的统一数据管理器，
替代现有的UnifiedDataManager和UniPluginDataManager双重架构。
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..interfaces.data_source import (
    IDataSource, ConnectionConfig, DataRequest, DataResponse,
    HealthStatus, DataType, ConnectionStatus, DataSourceError
)
from .data_router import DataRouter

logger = logging.getLogger(__name__)

class UnifiedDataManager:
    """统一数据管理器

    替代现有的双重管理器架构，提供统一的数据访问接口。
    """

    def __init__(self,
                 cache_manager: Optional[ICacheManager] = None,
                 circuit_breaker_manager: Optional[ICircuitBreakerManager] = None):
        """初始化统一数据管理器

        Args:
            cache_manager: 缓存管理器
            circuit_breaker_manager: 熔断器管理器
        """
        # 核心组件
        self._data_sources: Dict[str, IDataSource] = {}
        self._router = DataRouter()
        self._cache_manager = cache_manager
        self._circuit_breaker_manager = circuit_breaker_manager
        self._performance_monitor = None  
        # 状态管理
        self._initialized = False
        self._running = False
        self._lock = asyncio.Lock()

        # 统计信息
        self._request_count = 0
        self._success_count = 0
        self._error_count = 0
        self._start_time = datetime.now()

        logger.info("UnifiedDataManager initialized")

    async def initialize(self) -> bool:
        """初始化数据管理器

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            logger.warning("UnifiedDataManager already initialized")
            return True

        try:
            # 初始化路由器
            await self._router.initialize()

            # 启动性能监控
            await self._performance_monitor.start()

            self._initialized = True
            self._running = True

            logger.info("UnifiedDataManager initialization completed")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize UnifiedDataManager: {e}")
            return False

    async def shutdown(self) -> bool:
        """关闭数据管理器

        Returns:
            bool: 关闭是否成功
        """
        if not self._running:
            return True

        try:
            self._running = False

            # 断开所有数据源连接
            for name, source in self._data_sources.items():
                try:
                    await source.disconnect()
                    logger.info(f"Disconnected data source: {name}")
                except Exception as e:
                    logger.error(f"Failed to disconnect data source {name}: {e}")

            # 停止性能监控
            await self._performance_monitor.stop()

            logger.info("UnifiedDataManager shutdown completed")
            return True

        except Exception as e:
            logger.error(f"Failed to shutdown UnifiedDataManager: {e}")
            return False

    async def register_data_source(self, name: str, source: IDataSource,
                                   config: Optional[ConnectionConfig] = None) -> bool:
        """注册数据源

        Args:
            name: 数据源名称
            source: 数据源实例
            config: 连接配置

        Returns:
            bool: 注册是否成功
        """
        async with self._lock:
            if name in self._data_sources:
                logger.warning(f"Data source {name} already registered")
                return False

            try:
                # 连接数据源
                if config:
                    success = await source.connect(config)
                    if not success:
                        logger.error(f"Failed to connect data source: {name}")
                        return False

                # 注册到路由器
                await self._router.register_data_source(name, source)

                # 注册熔断器
                if self._circuit_breaker_manager:
                    from ..interfaces.circuit_breaker import CircuitBreakerConfig
                    cb_config = CircuitBreakerConfig()
                    await self._circuit_breaker_manager.create_circuit_breaker(name, cb_config)

                # 添加到数据源字典
                self._data_sources[name] = source

                logger.info(f"Successfully registered data source: {name}")
                return True

            except Exception as e:
                logger.error(f"Failed to register data source {name}: {e}")
                return False

    async def unregister_data_source(self, name: str) -> bool:
        """注销数据源

        Args:
            name: 数据源名称

        Returns:
            bool: 注销是否成功
        """
        async with self._lock:
            if name not in self._data_sources:
                logger.warning(f"Data source {name} not found")
                return False

            try:
                source = self._data_sources[name]

                # 断开连接
                await source.disconnect()

                # 从路由器注销
                await self._router.unregister_data_source(name)

                # 移除熔断器
                if self._circuit_breaker_manager:
                    await self._circuit_breaker_manager.remove_circuit_breaker(name)

                # 从字典中移除
                del self._data_sources[name]

                logger.info(f"Successfully unregistered data source: {name}")
                return True

            except Exception as e:
                logger.error(f"Failed to unregister data source {name}: {e}")
                return False

    async def get_data(self, request: DataRequest) -> DataResponse:
        """获取数据

        Args:
            request: 数据请求对象

        Returns:
            DataResponse: 数据响应对象
        """
        if not self._running:
            return DataResponse(
                success=False,
                message="UnifiedDataManager is not running",
                error_code="MANAGER_NOT_RUNNING"
            )

        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            self._request_count += 1

            # 1. 验证请求
            validation_errors = await self._validate_request(request)
            if validation_errors:
                return DataResponse(
                    success=False,
                    message=f"Request validation failed: {', '.join(validation_errors)}",
                    error_code="VALIDATION_ERROR",
                    request_id=request_id
                )

            # 2. 检查缓存
            if request.use_cache and self._cache_manager:
                cached_response = await self._get_from_cache(request)
                if cached_response:
                    cached_response.request_id = request_id
                    cached_response.response_time = time.time() - start_time
                    return cached_response

            # 3. 路由决策
            source_name = await self._router.route(request)
            if not source_name or source_name not in self._data_sources:
                return DataResponse(
                    success=False,
                    message=f"No available data source for request",
                    error_code="NO_DATA_SOURCE",
                    request_id=request_id,
                    response_time=time.time() - start_time
                )

            # 4. 熔断器检查
            if self._circuit_breaker_manager:
                circuit_breaker = await self._circuit_breaker_manager.get_circuit_breaker(source_name)
                if not await circuit_breaker.can_execute():
                    return await self._handle_fallback(request, request_id, start_time)

            # 5. 执行数据获取
            source = self._data_sources[source_name]

            if self._circuit_breaker_manager:
                circuit_breaker = await self._circuit_breaker_manager.get_circuit_breaker(source_name)
                response = await circuit_breaker.execute(source.get_data, request)
            else:
                response = await source.get_data(request)

            # 6. 处理响应
            response.source = source_name  # 使用注册时的键名
            response.request_id = request_id
            response.response_time = time.time() - start_time

            # 7. 缓存响应
            if response.success and request.use_cache and self._cache_manager:
                await self._cache_response(request, response)

            # 8. 记录性能指标
            await self._performance_monitor.record_request(
                source_name, request.data_type.value, response.response_time, response.success
            )

            if response.success:
                self._success_count += 1
            else:
                self._error_count += 1

            return response

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error processing data request: {e}")

            return DataResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                error_code="INTERNAL_ERROR",
                request_id=request_id,
                response_time=time.time() - start_time
            )

    async def get_data_source_status(self, name: str) -> Optional[HealthStatus]:
        """获取数据源状态

        Args:
            name: 数据源名称

        Returns:
            Optional[HealthStatus]: 健康状态，不存在时返回None
        """
        if name not in self._data_sources:
            return None

        try:
            source = self._data_sources[name]
            return await source.health_check()
        except Exception as e:
            logger.error(f"Failed to get status for data source {name}: {e}")
            return HealthStatus(
                is_healthy=False,
                status_message=f"Health check failed: {str(e)}",
                connection_status=ConnectionStatus.ERROR
            )

    async def get_all_data_sources_status(self) -> Dict[str, HealthStatus]:
        """获取所有数据源状态

        Returns:
            Dict[str, HealthStatus]: 数据源状态字典
        """
        status_dict = {}

        for name in self._data_sources.keys():
            status = await self.get_data_source_status(name)
            if status:
                status_dict[name] = status

        return status_dict

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "total_requests": self._request_count,
            "successful_requests": self._success_count,
            "failed_requests": self._error_count,
            "success_rate": self._success_count / self._request_count if self._request_count > 0 else 0.0,
            "registered_data_sources": len(self._data_sources),
            "data_source_names": list(self._data_sources.keys()),
            "is_running": self._running
        }

    async def _validate_request(self, request: DataRequest) -> List[str]:
        """验证数据请求

        Args:
            request: 数据请求对象

        Returns:
            List[str]: 验证错误列表
        """
        errors = []

        if not request.symbol:
            errors.append("Symbol is required")

        if request.data_type not in DataType:
            errors.append("Invalid data type")

        if request.start_time and request.end_time:
            if request.start_time > request.end_time:
                errors.append("Start time must be before end time")

        if request.limit is not None and request.limit <= 0:
            errors.append("Limit must be positive")

        return errors

    async def _get_from_cache(self, request: DataRequest) -> Optional[DataResponse]:
        """从缓存获取数据

        Args:
            request: 数据请求对象

        Returns:
            Optional[DataResponse]: 缓存的响应，不存在时返回None
        """
        if not self._cache_manager:
            return None

        try:
            cache_key = self._generate_cache_key(request)
            cached_data = await self._cache_manager.get_multi_level(cache_key)

            if cached_data:
                response = DataResponse.from_dict(cached_data) if isinstance(cached_data, dict) else cached_data
                response.from_cache = True
                response.cache_key = cache_key
                return response

        except Exception as e:
            logger.warning(f"Failed to get data from cache: {e}")

        return None

    async def _cache_response(self, request: DataRequest, response: DataResponse) -> None:
        """缓存响应数据

        Args:
            request: 数据请求对象
            response: 数据响应对象
        """
        if not self._cache_manager:
            return

        try:
            cache_key = self._generate_cache_key(request)
            ttl = request.cache_ttl if request.cache_ttl > 0 else None

            await self._cache_manager.set_multi_level(cache_key, response.to_dict(), ttl)

        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    def _generate_cache_key(self, request: DataRequest) -> str:
        """生成缓存键

        Args:
            request: 数据请求对象

        Returns:
            str: 缓存键
        """
        import hashlib

        key_parts = [
            request.data_type.value,
            request.symbol,
            request.frequency or "",
            str(request.start_time) if request.start_time else "",
            str(request.end_time) if request.end_time else "",
            str(request.limit) if request.limit else "",
            str(sorted(request.fields)) if request.fields else "",
            str(sorted(request.filters.items())) if request.filters else ""
        ]

        key_string = "|".join(key_parts)
        return f"data:{hashlib.md5(key_string.encode()).hexdigest()}"

    async def _handle_fallback(self, request: DataRequest, request_id: str, start_time: float) -> DataResponse:
        """处理降级逻辑

        Args:
            request: 数据请求对象
            request_id: 请求ID
            start_time: 开始时间

        Returns:
            DataResponse: 降级响应
        """
        # 尝试从其他数据源获取数据
        alternative_sources = await self._router.get_alternative_sources(request)

        for source_name in alternative_sources:
            if source_name in self._data_sources:
                try:
                    source = self._data_sources[source_name]
                    response = await source.get_data(request)

                    response.source = f"{source_name}(fallback)"
                    response.request_id = request_id
                    response.response_time = time.time() - start_time

                    if response.success:
                        logger.info(f"Fallback successful using {source_name}")
                        return response

                except Exception as e:
                    logger.warning(f"Fallback failed for {source_name}: {e}")
                    continue

        # 所有降级方案都失败
        return DataResponse(
            success=False,
            message="All data sources unavailable",
            error_code="ALL_SOURCES_UNAVAILABLE",
            request_id=request_id,
            response_time=time.time() - start_time
        )
