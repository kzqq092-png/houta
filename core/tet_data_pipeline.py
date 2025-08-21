"""
TET数据管道实现
Transform-Extract-Transform数据处理管道
借鉴OpenBB架构设计，为HIkyuu-UI提供标准化多资产数据支持

增强版本：支持多数据源路由、故障转移、插件化数据源
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .plugin_types import AssetType, DataType
from .data_source_router import DataSourceRouter, RoutingRequest, RoutingStrategy
from .data_source_extensions import IDataSourcePlugin, DataSourcePluginAdapter, HealthCheckResult

logger = logging.getLogger(__name__)


@dataclass
class StandardQuery:
    """标准化查询请求"""
    symbol: str
    asset_type: AssetType
    data_type: DataType
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period: str = "D"
    market: Optional[str] = None
    provider: Optional[str] = None  # 指定数据源
    extra_params: Dict[str, Any] = field(default_factory=dict)

    # 路由相关参数
    priority: int = 0
    timeout_ms: int = 5000
    retry_count: int = 3
    fallback_enabled: bool = True

    def __post_init__(self):
        """后处理初始化"""
        if self.extra_params is None:
            self.extra_params = {}


@dataclass
class StandardData:
    """标准化数据输出"""
    data: pd.DataFrame
    metadata: Dict[str, Any]
    source_info: Dict[str, Any]
    query: StandardQuery
    processing_time_ms: float = 0.0


@dataclass
class FailoverResult:
    """故障转移结果"""
    success: bool
    attempts: int
    failed_sources: List[str]
    successful_source: Optional[str]
    error_messages: List[str]
    total_time_ms: float


class TETDataPipeline:
    """
    TET数据管道实现
    Transform-Extract-Transform三阶段数据处理

    增强功能：
    - 多数据源路由和负载均衡
    - 智能故障转移
    - 插件化数据源支持
    - 异步并发处理
    - 缓存和性能优化
    """

    def __init__(self, data_source_router: DataSourceRouter):
        self.router = data_source_router
        self.logger = logging.getLogger(self.__class__.__name__)

        # 插件管理
        self._plugins: Dict[str, IDataSourcePlugin] = {}
        self._adapters: Dict[str, DataSourcePluginAdapter] = {}

        # 缓存管理
        self._cache: Dict[str, Tuple[StandardData, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # 缓存5分钟

        # 异步处理
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 性能统计
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "fallback_used": 0,
            "avg_processing_time": 0.0
        }

        # 字段映射表（用于数据标准化）
        self.field_mappings = {
            # OHLCV标准化映射
            DataType.HISTORICAL_KLINE: {
                # 开盘价
                'o': 'open', 'Open': 'open', 'OPEN': 'open', '开盘价': 'open', 'opening': 'open',
                # 最高价
                'h': 'high', 'High': 'high', 'HIGH': 'high', '最高价': 'high', 'highest': 'high',
                # 最低价
                'l': 'low', 'Low': 'low', 'LOW': 'low', '最低价': 'low', 'lowest': 'low',
                # 收盘价
                'c': 'close', 'Close': 'close', 'CLOSE': 'close', '收盘价': 'close', 'closing': 'close',
                # 成交量
                'v': 'volume', 'Volume': 'volume', 'VOLUME': 'volume', '成交量': 'volume', 'vol': 'volume',
                # 成交额
                'amount': 'amount', 'Amount': 'amount', 'AMOUNT': 'amount', '成交额': 'amount', 'turnover': 'amount',
                # 日期/时间
                't': 'datetime', 'time': 'datetime', 'Time': 'datetime', 'timestamp': 'datetime', 'date': 'datetime', '日期': 'datetime',
                # 其他常见字段
                'vwap': 'vwap', 'VWAP': 'vwap', 'adj_close': 'adj_close'
            },

            # 实时数据映射
            DataType.REAL_TIME_QUOTE: {
                # 基础价格字段
                'price': 'current_price', 'current': 'current_price', 'last': 'current_price', '现价': 'current_price',
                'bid': 'bid_price', 'bid_price': 'bid_price', '买一价': 'bid_price',
                'ask': 'ask_price', 'ask_price': 'ask_price', '卖一价': 'ask_price',
                'open': 'open_price', 'open_price': 'open_price', '开盘价': 'open_price',
                'high': 'high_price', 'high_price': 'high_price', '最高价': 'high_price',
                'low': 'low_price', 'low_price': 'low_price', '最低价': 'low_price',
                'close': 'prev_close', 'prev_close': 'prev_close', '昨收价': 'prev_close',

                # 成交量和成交额
                'volume': 'volume', 'vol': 'volume', '成交量': 'volume',
                'amount': 'turnover', 'turnover': 'turnover', '成交额': 'turnover',

                # 涨跌相关
                'change': 'change', 'chg': 'change', '涨跌额': 'change',
                'change_pct': 'change_percent', 'pct_chg': 'change_percent', '涨跌幅': 'change_percent',

                # 时间戳
                'timestamp': 'update_time', 'time': 'update_time', 'update_time': 'update_time', '更新时间': 'update_time'
            }
        }

        # 空值表示（用于清理数据）
        self.null_values = ['N/A', 'null', 'NULL', '', 'nan', 'NaN', 'None', '--', '-']

    def register_plugin(self, plugin_id: str, plugin: IDataSourcePlugin) -> bool:
        """
        注册数据源插件

        Args:
            plugin_id: 插件唯一标识
            plugin: 插件实例

        Returns:
            bool: 注册是否成功
        """
        try:
            # 验证插件接口
            from .data_source_extensions import validate_plugin_interface, create_plugin_adapter

            if not validate_plugin_interface(plugin):
                self.logger.error(f"插件接口验证失败: {plugin_id}")
                return False

            # 创建适配器
            adapter = create_plugin_adapter(plugin, plugin_id)
            if not adapter:
                self.logger.error(f"创建插件适配器失败: {plugin_id}")
                return False

            # 注册到路由器
            self.router.register_data_source(plugin_id, adapter)

            # 保存引用
            self._plugins[plugin_id] = plugin
            self._adapters[plugin_id] = adapter

            self.logger.info(f"数据源插件注册成功: {plugin_id}")
            return True

        except Exception as e:
            self.logger.error(f"注册数据源插件失败 {plugin_id}: {e}")
            return False

    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        注销数据源插件

        Args:
            plugin_id: 插件唯一标识

        Returns:
            bool: 注销是否成功
        """
        try:
            # 从路由器注销
            self.router.unregister_data_source(plugin_id)

            # 断开连接
            if plugin_id in self._adapters:
                self._adapters[plugin_id].disconnect()
                del self._adapters[plugin_id]

            # 清理引用
            if plugin_id in self._plugins:
                del self._plugins[plugin_id]

            self.logger.info(f"数据源插件注销成功: {plugin_id}")
            return True

        except Exception as e:
            self.logger.error(f"注销数据源插件失败 {plugin_id}: {e}")
            return False

    def process(self, query: StandardQuery) -> StandardData:
        """
        完整的TET流程处理

        Args:
            query: 标准化查询请求

        Returns:
            StandardData: 标准化处理结果

        Raises:
            Exception: 处理失败时抛出异常
        """
        start_time = time.time()
        self._stats["total_requests"] += 1

        try:
            self.logger.info(f"开始TET处理: {query.symbol} ({query.asset_type.value}) - {query.data_type.value}")

            # 检查缓存
            cache_key = self._generate_cache_key(query)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self._stats["cache_hits"] += 1
                self.logger.debug(f"缓存命中: {query.symbol}")
                return cached_result

            # Stage 1: Transform Query（查询转换）
            routing_request = self.transform_query(query)
            self.logger.debug(f"查询转换完成: asset_type={routing_request.asset_type.value}")

            # Stage 2: Extract Data（数据提取 - 支持故障转移）
            raw_data, provider_info, failover_result = self.extract_data_with_failover(routing_request, query)

            if failover_result and not failover_result.success:
                self.logger.error(f"所有数据源都失败: {query.symbol}")
                raise Exception(f"数据提取失败: {', '.join(failover_result.error_messages)}")

            self.logger.debug(f"数据提取完成: {len(raw_data) if raw_data is not None else 0} 条记录")

            # Stage 3: Transform Data（数据标准化）
            standard_data = self.transform_data(raw_data, query)
            self.logger.debug(f"数据标准化完成: {len(standard_data)} 条记录")

            processing_time = (time.time() - start_time) * 1000

            result = StandardData(
                data=standard_data,
                metadata=self._build_metadata(query, raw_data, failover_result),
                source_info=provider_info,
                query=query,
                processing_time_ms=processing_time
            )

            # 更新缓存
            self._set_to_cache(cache_key, result)

            # 更新统计
            self._update_stats(processing_time)

            self.logger.info(f"TET处理完成: {processing_time:.2f}ms")
            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"TET处理失败 ({processing_time:.2f}ms): {e}")
            raise

    def transform_query(self, query: StandardQuery) -> RoutingRequest:
        """
        Stage 1: 查询转换
        将标准化查询转换为路由请求

        Args:
            query: 标准化查询

        Returns:
            RoutingRequest: 路由请求
        """
        return RoutingRequest(
            asset_type=query.asset_type,
            data_type=query.data_type,
            symbol=query.symbol,
            priority=query.priority,
            timeout_ms=query.timeout_ms,
            retry_count=query.retry_count,
            metadata={
                'period': query.period,
                'start_date': query.start_date,
                'end_date': query.end_date,
                'market': query.market,
                'provider': query.provider,
                **query.extra_params
            }
        )

    def extract_data_with_failover(self, routing_request: RoutingRequest,
                                   original_query: StandardQuery) -> Tuple[pd.DataFrame, Dict[str, Any], FailoverResult]:
        """
        Stage 2: 数据提取（支持故障转移）

        Args:
            routing_request: 路由请求
            original_query: 原始查询

        Returns:
            Tuple[pd.DataFrame, Dict[str, Any], FailoverResult]: (数据, 提供商信息, 故障转移结果)
        """
        start_time = time.time()
        failed_sources = []
        error_messages = []
        attempts = 0

        # 获取可用数据源列表
        available_sources = self.router.get_available_sources(routing_request)

        if not available_sources:
            failover_result = FailoverResult(
                success=False,
                attempts=0,
                failed_sources=[],
                successful_source=None,
                error_messages=["没有可用的数据源"],
                total_time_ms=(time.time() - start_time) * 1000
            )
            return pd.DataFrame(), {}, failover_result

        # 如果指定了特定提供商，优先使用
        if original_query.provider and original_query.provider in available_sources:
            available_sources = [original_query.provider] + [s for s in available_sources if s != original_query.provider]

        # 尝试每个数据源
        for source_id in available_sources:
            attempts += 1

            try:
                self.logger.debug(f"尝试数据源: {source_id} (第{attempts}次尝试)")

                # 获取数据源适配器
                adapter = self._adapters.get(source_id)
                if not adapter:
                    error_msg = f"数据源适配器不存在: {source_id}"
                    error_messages.append(error_msg)
                    failed_sources.append(source_id)
                    continue

                # 检查连接状态
                if not adapter.is_connected():
                    if not adapter.connect():
                        error_msg = f"数据源连接失败: {source_id}"
                        error_messages.append(error_msg)
                        failed_sources.append(source_id)
                        continue

                # 提取数据
                raw_data = self._extract_from_source(adapter, routing_request, original_query)

                if raw_data is not None and not raw_data.empty:
                    provider_info = {
                        'provider': source_id,
                        'plugin_info': adapter.get_plugin_info(),
                        'extraction_time': datetime.now().isoformat()
                    }

                    failover_result = FailoverResult(
                        success=True,
                        attempts=attempts,
                        failed_sources=failed_sources,
                        successful_source=source_id,
                        error_messages=error_messages,
                        total_time_ms=(time.time() - start_time) * 1000
                    )

                    self.logger.info(f"数据提取成功: {source_id} (尝试{attempts}次)")
                    return raw_data, provider_info, failover_result
                else:
                    error_msg = f"数据源返回空数据: {source_id}"
                    error_messages.append(error_msg)
                    failed_sources.append(source_id)

            except Exception as e:
                error_msg = f"数据源异常 {source_id}: {str(e)}"
                error_messages.append(error_msg)
                failed_sources.append(source_id)
                self.logger.warning(error_msg)

        # 所有数据源都失败
        self._stats["fallback_used"] += 1

        failover_result = FailoverResult(
            success=False,
            attempts=attempts,
            failed_sources=failed_sources,
            successful_source=None,
            error_messages=error_messages,
            total_time_ms=(time.time() - start_time) * 1000
        )

        return pd.DataFrame(), {}, failover_result

    def _extract_from_source(self, adapter: DataSourcePluginAdapter,
                             routing_request: RoutingRequest,
                             original_query: StandardQuery) -> pd.DataFrame:
        """
        从指定数据源提取数据

        Args:
            adapter: 数据源适配器
            routing_request: 路由请求
            original_query: 原始查询

        Returns:
            pd.DataFrame: 提取的数据
        """
        if original_query.data_type == DataType.HISTORICAL_KLINE:
            return adapter.get_kdata(
                symbol=original_query.symbol,
                freq=original_query.period,
                start_date=original_query.start_date,
                end_date=original_query.end_date,
                count=original_query.extra_params.get('count')
            )
        elif original_query.data_type == DataType.REAL_TIME_QUOTE:
            return adapter.get_real_time_quotes([original_query.symbol])
        elif original_query.data_type == DataType.ASSET_LIST:
            # 获取资产列表
            asset_list = adapter.get_asset_list(
                asset_type=original_query.asset_type,
                market=original_query.market
            )
            # 转换为DataFrame
            if asset_list:
                return pd.DataFrame(asset_list)
            else:
                return pd.DataFrame()
        elif original_query.data_type == DataType.SECTOR_FUND_FLOW:
            # 获取板块资金流数据
            plugin = self._plugins.get(adapter.plugin_id)
            if plugin and hasattr(plugin, 'get_sector_fund_flow_data'):
                return plugin.get_sector_fund_flow_data(
                    symbol=original_query.symbol,
                    **original_query.extra_params
                )
            else:
                self.logger.warning(f"插件 {adapter.plugin_id} 不支持板块资金流数据")
                return pd.DataFrame()
        else:
            # 其他数据类型，直接调用插件接口
            plugin = self._plugins.get(adapter.plugin_id)
            if plugin:
                if hasattr(plugin, 'fetch_data'):
                    return plugin.fetch_data(
                        original_query.symbol,
                        original_query.data_type.value,
                        **original_query.extra_params
                    )

        return pd.DataFrame()

    def transform_data(self, raw_data: pd.DataFrame, query: StandardQuery) -> pd.DataFrame:
        """
        Stage 3: 数据标准化

        Args:
            raw_data: 原始数据
            query: 查询对象

        Returns:
            pd.DataFrame: 标准化数据
        """
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()

        try:
            # 获取字段映射
            field_mapping = self.field_mappings.get(query.data_type, {})

            # 应用字段映射
            standardized_data = raw_data.copy()
            if field_mapping:
                standardized_data = standardized_data.rename(columns=field_mapping)

            # 数据清洗
            standardized_data = self._clean_data(standardized_data)

            # 数据类型转换
            standardized_data = self._convert_data_types(standardized_data, query.data_type)

            # 数据验证
            standardized_data = self._validate_data(standardized_data, query.data_type)

            return standardized_data

        except Exception as e:
            self.logger.error(f"数据标准化失败: {e}")
            return raw_data  # 返回原始数据作为降级

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """清洗数据"""
        # 替换空值
        for null_val in self.null_values:
            data = data.replace(null_val, pd.NA)

        # 删除完全空的行
        data = data.dropna(how='all')

        return data

    def _convert_data_types(self, data: pd.DataFrame, data_type: DataType) -> pd.DataFrame:
        """转换数据类型"""
        if data_type == DataType.HISTORICAL_KLINE:
            # K线数据类型转换
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')

            # 处理时间列
            if 'datetime' in data.columns:
                data['datetime'] = pd.to_datetime(data['datetime'], errors='coerce')
                if not isinstance(data.index, pd.DatetimeIndex):
                    data.set_index('datetime', inplace=True)

        elif data_type == DataType.REAL_TIME_QUOTE:
            # 实时数据类型转换
            numeric_columns = ['current_price', 'bid_price', 'ask_price', 'volume', 'turnover', 'change', 'change_percent']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')

        return data

    def _validate_data(self, data: pd.DataFrame, data_type: DataType) -> pd.DataFrame:
        """验证数据完整性"""
        if data_type == DataType.HISTORICAL_KLINE:
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                self.logger.warning(f"K线数据缺少必要列: {missing_columns}")

        return data

    def _generate_cache_key(self, query: StandardQuery) -> str:
        """生成缓存键"""
        key_parts = [
            query.symbol,
            query.asset_type.value,
            query.data_type.value,
            query.period,
            query.start_date or "",
            query.end_date or "",
            str(query.extra_params)
        ]
        return "|".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[StandardData]:
        """从缓存获取数据"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[cache_key]
        return None

    def _set_to_cache(self, cache_key: str, data: StandardData) -> None:
        """设置缓存"""
        self._cache[cache_key] = (data, datetime.now())

    def _build_metadata(self, query: StandardQuery, raw_data: pd.DataFrame,
                        failover_result: Optional[FailoverResult]) -> Dict[str, Any]:
        """构建元数据"""
        metadata = {
            'query_time': datetime.now().isoformat(),
            'data_count': len(raw_data) if raw_data is not None else 0,
            'asset_type': query.asset_type.value,
            'data_type': query.data_type.value,
            'period': query.period
        }

        if failover_result:
            metadata['failover'] = {
                'success': failover_result.success,
                'attempts': failover_result.attempts,
                'failed_sources': failover_result.failed_sources,
                'successful_source': failover_result.successful_source,
                'total_time_ms': failover_result.total_time_ms
            }

        return metadata

    def _update_stats(self, processing_time_ms: float) -> None:
        """更新统计信息"""
        total_requests = self._stats["total_requests"]
        current_avg = self._stats["avg_processing_time"]

        self._stats["avg_processing_time"] = (
            (current_avg * (total_requests - 1) + processing_time_ms) / total_requests
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            'registered_plugins': len(self._plugins),
            'active_adapters': len(self._adapters),
            'cache_size': len(self._cache),
            'cache_hit_rate': self._stats["cache_hits"] / max(self._stats["total_requests"], 1)
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self.logger.info("TET数据管道缓存已清空")

    def health_check_all_sources(self) -> Dict[str, HealthCheckResult]:
        """检查所有数据源的健康状态"""
        results = {}

        for plugin_id, adapter in self._adapters.items():
            try:
                results[plugin_id] = adapter.health_check()
            except Exception as e:
                results[plugin_id] = HealthCheckResult(
                    is_healthy=False,
                    status_code=500,
                    message=f"健康检查异常: {str(e)}",
                    response_time_ms=0.0,
                    last_check_time=datetime.now()
                )

        return results

    async def process_async(self, query: StandardQuery) -> StandardData:
        """异步处理数据请求"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.process, query)

    def cleanup(self) -> None:
        """清理资源"""
        # 断开所有插件连接
        for adapter in self._adapters.values():
            try:
                adapter.disconnect()
            except Exception as e:
                self.logger.error(f"断开插件连接失败: {e}")

        # 关闭线程池
        self._executor.shutdown(wait=True)

        # 清空缓存
        self.clear_cache()

        self.logger.info("TET数据管道已清理完成")


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
