"""
TET数据管道实现
Transform-Extract-Transform数据处理管道
借鉴OpenBB架构设计，为HIkyuu-UI提供标准化多资产数据支持
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Union
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from .plugin_types import AssetType, DataType
from .data_source_router import DataSourceRouter, RoutingRequest
from .data_source_extensions import IDataSourcePlugin

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

    def __post_init__(self):
        """后处理初始化"""
        if self.extra_params is None:
            self.extra_params = {}


@dataclass
class StandardData:
    """标准化数据输出"""
    data: pd.DataFrame
    metadata: Dict[str, Any]
    source_info: Dict[str, str]
    query: StandardQuery
    processing_time_ms: float


class TETDataPipeline:
    """
    TET数据管道实现
    Transform-Extract-Transform三阶段数据处理
    """

    def __init__(self, data_source_router: DataSourceRouter):
        self.router = data_source_router
        self.logger = logging.getLogger(self.__class__.__name__)

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
                'price': 'price', 'Price': 'price', 'last': 'price', '现价': 'price',
                'bid': 'bid', 'Bid': 'bid', '买价': 'bid',
                'ask': 'ask', 'Ask': 'ask', '卖价': 'ask',
                'volume': 'volume', 'Volume': 'volume', '成交量': 'volume',
                'change': 'change', 'Change': 'change', '涨跌': 'change',
                'change_percent': 'change_percent', 'Change%': 'change_percent', '涨跌幅': 'change_percent'
            },

            # 资金流数据映射
            DataType.FUND_FLOW: {
                'net_inflow': 'net_inflow', '净流入': 'net_inflow', '主力净流入-净额': 'net_inflow',
                'net_inflow_ratio': 'net_inflow_ratio', '净流入占比': 'net_inflow_ratio', '主力净流入-净占比': 'net_inflow_ratio',
                'main_inflow': 'main_inflow', '主力流入': 'main_inflow', '主力资金流入': 'main_inflow',
                'main_outflow': 'main_outflow', '主力流出': 'main_outflow', '主力资金流出': 'main_outflow',
                'retail_inflow': 'retail_inflow', '散户流入': 'retail_inflow', '中小单流入': 'retail_inflow',
                'retail_outflow': 'retail_outflow', '散户流出': 'retail_outflow', '中小单流出': 'retail_outflow'
            },

            # 板块资金流数据映射
            DataType.SECTOR_FUND_FLOW: {
                'sector_name': 'sector_name', '板块': 'sector_name', '板块名称': 'sector_name',
                'net_inflow': 'net_inflow', '今日主力净流入-净额': 'net_inflow', '净流入': 'net_inflow',
                'net_inflow_ratio': 'net_inflow_ratio', '今日主力净流入-净占比': 'net_inflow_ratio', '净流入占比': 'net_inflow_ratio',
                'change_percent': 'change_percent', '涨跌幅': 'change_percent', '板块涨跌幅': 'change_percent',
                'leading_stock': 'leading_stock', '领涨股': 'leading_stock', '龙头股': 'leading_stock'
            },

            # 板块数据映射
            DataType.SECTOR_DATA: {
                'sector_name': 'sector_name', '板块': 'sector_name', '板块名称': 'sector_name',
                'price': 'price', '现价': 'price', '最新价': 'price',
                'change': 'change', '涨跌': 'change', '涨跌额': 'change',
                'change_percent': 'change_percent', '涨跌幅': 'change_percent',
                'volume': 'volume', '成交量': 'volume', '总成交量': 'volume',
                'turnover': 'turnover', '成交额': 'turnover', '总成交额': 'turnover',
                'market_cap': 'market_cap', '总市值': 'market_cap', '流通市值': 'market_cap'
            },

            # 实时资金流数据映射
            DataType.REAL_TIME_FUND_FLOW: {
                'time': 'time', '时间': 'time', 'timestamp': 'time',
                'symbol': 'symbol', '代码': 'symbol', '股票代码': 'symbol',
                'name': 'name', '名称': 'name', '股票名称': 'name',
                'net_inflow': 'net_inflow', '净流入': 'net_inflow', '主力净流入': 'net_inflow',
                'inflow_intensity': 'inflow_intensity', '流入强度': 'inflow_intensity',
                'activity': 'activity', '活跃度': 'activity', '资金活跃度': 'activity'
            },

            # 技术指标数据映射
            DataType.TECHNICAL_INDICATORS: {
                'ma5': 'ma5', 'MA5': 'ma5', '5日均线': 'ma5',
                'ma10': 'ma10', 'MA10': 'ma10', '10日均线': 'ma10',
                'ma20': 'ma20', 'MA20': 'ma20', '20日均线': 'ma20',
                'rsi': 'rsi', 'RSI': 'rsi', '相对强弱指标': 'rsi',
                'macd': 'macd', 'MACD': 'macd', 'MACD指标': 'macd',
                'kdj_k': 'kdj_k', 'KDJ_K': 'kdj_k', 'K值': 'kdj_k',
                'kdj_d': 'kdj_d', 'KDJ_D': 'kdj_d', 'D值': 'kdj_d',
                'kdj_j': 'kdj_j', 'KDJ_J': 'kdj_j', 'J值': 'kdj_j'
            }
        }

        # 空值表示（用于清理数据）
        self.null_values = ['N/A', 'null', 'NULL', '', 'nan', 'NaN', 'None', '--', '-']

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

        try:
            self.logger.info(f"开始TET处理: {query.symbol} ({query.asset_type.value}) - {query.data_type.value}")

            # Stage 1: Transform Query（查询转换）
            provider_query = self.transform_query(query)
            self.logger.debug(f"查询转换完成: provider={provider_query['provider_id']}")

            # Stage 2: Extract Data（数据提取）
            raw_data, provider_info = self.extract_data(provider_query)
            self.logger.debug(f"数据提取完成: {len(raw_data) if raw_data is not None else 0} 条记录")

            # Stage 3: Transform Data（数据标准化）
            standard_data = self.transform_data(raw_data, query)
            self.logger.debug(f"数据标准化完成: {len(standard_data)} 条记录")

            processing_time = (time.time() - start_time) * 1000

            result = StandardData(
                data=standard_data,
                metadata=self._build_metadata(query, raw_data),
                source_info=provider_info,
                query=query,
                processing_time_ms=processing_time
            )

            self.logger.info(f"TET处理完成: {processing_time:.2f}ms")
            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"TET处理失败 ({processing_time:.2f}ms): {e}")
            raise

    def transform_query(self, query: StandardQuery) -> Dict[str, Any]:
        """
        Stage 1: Transform Query
        将标准查询转换为Provider特定格式

        Args:
            query: 标准化查询请求

        Returns:
            Dict: Provider特定的查询信息
        """
        # 选择数据源
        if query.provider:
            provider_id = query.provider
            provider = self.router.get_data_source(provider_id)
            if not provider:
                raise ValueError(f"指定的数据源不存在: {query.provider}")
        else:
            routing_request = RoutingRequest(
                asset_type=query.asset_type,
                data_type=query.data_type,
                symbol=query.symbol,
                metadata={"market": query.market}
            )
            provider_id = self.router.route_request(routing_request)
            if not provider_id:
                raise ValueError(f"没有可用的数据源: {query.asset_type.value}/{query.data_type.value}")

            provider = self.router.get_data_source(provider_id)

        # 构建基础查询参数
        provider_params = {
            'symbol': self._normalize_symbol(query.symbol, query.asset_type),
            'data_type': query.data_type.value,
            'start_date': self._parse_date(query.start_date),
            'end_date': self._parse_date(query.end_date),
            'period': query.period
        }

        # 添加扩展参数
        if query.extra_params:
            provider_params.update(query.extra_params)

        # Provider特定的查询转换
        if hasattr(provider.plugin, 'transform_query_params'):
            provider_params = provider.plugin.transform_query_params(provider_params)
        else:
            # 使用通用转换逻辑
            provider_params = self._generic_query_transform(provider_params, provider_id)

        return {
            'provider_id': provider_id,
            'provider': provider,
            'params': provider_params
        }

    def extract_data(self, provider_query: Dict) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Stage 2: Extract Data
        从实际数据源获取原始数据

        Args:
            provider_query: Provider特定的查询信息

        Returns:
            Tuple[pd.DataFrame, Dict]: 原始数据和Provider信息
        """
        provider = provider_query['provider']
        params = provider_query['params']
        provider_id = provider_query['provider_id']

        try:
            # 记录请求开始
            start_time = time.time()

            # 调用Provider获取数据
            raw_data = provider.plugin.fetch_data(**params)

            # 记录成功
            response_time = (time.time() - start_time) * 1000
            self.router.record_request_result(provider_id, True, response_time)

            provider_info = {
                'provider_id': provider_id,
                'provider_name': getattr(provider.plugin, 'name', provider_id),
                'response_time_ms': response_time,
                'data_points': len(raw_data) if raw_data is not None else 0,
                'request_params': params,
                'timestamp': datetime.now().isoformat()
            }

            return raw_data, provider_info

        except Exception as e:
            # 记录失败
            response_time = (time.time() - start_time) * 1000
            self.router.record_request_result(provider_id, False, response_time, str(e))

            self.logger.error(f"数据提取失败 [{provider_id}]: {e}")
            raise

    def transform_data(self, raw_data: pd.DataFrame, query: StandardQuery) -> pd.DataFrame:
        """
        Stage 3: Transform Data
        标准化数据格式

        Args:
            raw_data: 原始数据
            query: 查询请求

        Returns:
            pd.DataFrame: 标准化后的数据
        """
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()

        # 创建数据副本
        standardized = raw_data.copy()

        # 根据数据类型进行标准化
        if query.data_type == DataType.HISTORICAL_KLINE:
            standardized = self._standardize_ohlcv(standardized)
        elif query.data_type == DataType.REAL_TIME_QUOTE:
            standardized = self._standardize_realtime(standardized)
        elif query.data_type in [DataType.ASSET_LIST, DataType.MARKET_INFO]:
            standardized = self._standardize_asset_list(standardized, query.asset_type)

        # 通用数据清理
        standardized = self._clean_data(standardized)

        # 数据验证
        standardized = self._validate_data(standardized, query.data_type)

        return standardized

    def _normalize_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """标准化交易代码"""
        if not symbol:
            return symbol

        symbol = symbol.upper().strip()

        # 资产类型特定的标准化
        if asset_type == AssetType.STOCK:
            # 股票代码标准化：确保6位数字
            if symbol.isdigit() and len(symbol) < 6:
                symbol = symbol.zfill(6)
        elif asset_type == AssetType.CRYPTO:
            # 加密货币：确保格式统一
            if 'USDT' not in symbol and 'USD' not in symbol and '/' not in symbol:
                symbol = f"{symbol}USDT"  # 默认对USDT

        return symbol

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期字符串"""
        if not date_str:
            return None

        # 支持多种日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y%m%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S'
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        self.logger.warning(f"无法解析日期格式: {date_str}")
        return None

    def _generic_query_transform(self, params: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
        """通用查询参数转换"""
        # 基于Provider ID的特定转换
        if 'binance' in provider_id.lower():
            # Binance特定转换
            if 'period' in params:
                period_map = {
                    'D': '1d', '1D': '1d',
                    'H': '1h', '1H': '1h',
                    'M': '1m', '1M': '1m'
                }
                params['interval'] = period_map.get(params['period'], '1d')
        elif 'yfinance' in provider_id.lower():
            # Yahoo Finance特定转换
            if 'period' in params:
                period_map = {
                    'D': '1d', '1D': '1d',
                    'H': '1h', '1H': '1h'
                }
                params['interval'] = period_map.get(params['period'], '1d')

        return params

    def _standardize_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化OHLCV数据格式"""
        if df.empty:
            return df

        # 字段名映射
        field_mapping = self.field_mappings[DataType.HISTORICAL_KLINE]
        df = df.rename(columns=field_mapping)

        # 确保必要字段存在
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        for field in required_fields:
            if field not in df.columns:
                df[field] = None

        # 数据类型转换
        numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount', 'vwap', 'adj_close']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # 处理日期时间索引
        df = self._standardize_datetime_index(df)

        # 数据完整性检查
        df = self._validate_ohlcv_data(df)

        return df

    def _standardize_realtime(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化实时数据格式"""
        if df.empty:
            return df

        # 字段名映射
        field_mapping = self.field_mappings[DataType.REAL_TIME_QUOTE]
        df = df.rename(columns=field_mapping)

        # 数据类型转换
        numeric_fields = ['price', 'bid', 'ask', 'volume', 'change', 'change_percent']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        return df

    def _standardize_asset_list(self, df: pd.DataFrame, asset_type: AssetType) -> pd.DataFrame:
        """标准化资产列表格式"""
        if df.empty:
            return df

        # 统一字段名
        standard_columns = {
            'code': 'symbol', 'Code': 'symbol', 'symbol': 'symbol', '代码': 'symbol',
            'name': 'name', 'Name': 'name', '名称': 'name',
            'market': 'market', 'Market': 'market', '市场': 'market',
            'status': 'status', 'Status': 'status', '状态': 'status'
        }

        df = df.rename(columns=standard_columns)

        # 确保必要字段存在
        if 'symbol' not in df.columns:
            if 'code' in df.columns:
                df['symbol'] = df['code']
            else:
                df['symbol'] = df.index

        if 'name' not in df.columns:
            df['name'] = df['symbol']

        if 'asset_type' not in df.columns:
            df['asset_type'] = asset_type.value

        if 'status' not in df.columns:
            df['status'] = 'active'

        return df

    def _standardize_datetime_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化日期时间索引"""
        # 查找日期时间列
        datetime_candidates = ['datetime', 'date', 'time', 'timestamp']
        datetime_col = None

        for col in datetime_candidates:
            if col in df.columns:
                datetime_col = col
                break

        if datetime_col:
            # 将日期时间列设为索引
            try:
                df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
                df = df.set_index(datetime_col)
                df.index.name = 'datetime'
            except Exception as e:
                self.logger.warning(f"日期时间索引设置失败: {e}")
        elif not isinstance(df.index, pd.DatetimeIndex):
            # 尝试将索引转换为日期时间
            try:
                df.index = pd.to_datetime(df.index, errors='coerce')
                df.index.name = 'datetime'
            except Exception as e:
                self.logger.debug(f"索引日期时间转换失败: {e}")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理数据：空值处理、异常值检测等"""
        if df.empty:
            return df

        # 替换各种空值表示
        df = df.replace(self.null_values, None)

        # 移除完全为空的行
        df = df.dropna(how='all')

        # 按时间排序
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        return df

    def _validate_ohlcv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证OHLCV数据完整性"""
        if df.empty:
            return df

        # 检查OHLC逻辑关系：Low <= Open,Close <= High
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # 标记异常数据但不删除
            invalid_mask = (
                (df['low'] > df['open']) |
                (df['low'] > df['close']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close'])
            )

            if invalid_mask.any():
                invalid_count = invalid_mask.sum()
                self.logger.warning(f"发现 {invalid_count} 条OHLC数据异常")

                # 可选：修复异常数据
                df.loc[invalid_mask, 'high'] = df.loc[invalid_mask, [
                    'open', 'close', 'high']].max(axis=1)
                df.loc[invalid_mask, 'low'] = df.loc[invalid_mask, [
                    'open', 'close', 'low']].min(axis=1)

        return df

    def _validate_data(self, df: pd.DataFrame, data_type: DataType) -> pd.DataFrame:
        """通用数据验证"""
        if df.empty:
            return df

        # 检查数据量
        if len(df) > 100000:  # 超过10万条数据给出警告
            self.logger.warning(f"数据量较大: {len(df)} 条记录")

        # 检查内存使用
        memory_usage = df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
        if memory_usage > 100:  # 超过100MB给出警告
            self.logger.warning(f"数据内存使用较大: {memory_usage:.2f} MB")

        return df

    def _build_metadata(self, query: StandardQuery, raw_data: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """构建元数据信息"""
        metadata = {
            'query': {
                'symbol': query.symbol,
                'asset_type': query.asset_type.value,
                'data_type': query.data_type.value,
                'period': query.period,
                'market': query.market
            },
            'data_info': {
                'raw_records': len(raw_data) if raw_data is not None else 0,
                'processing_timestamp': datetime.now().isoformat()
            },
            'tet_version': '1.0.0'
        }

        return metadata


# 工厂函数
def create_tet_pipeline(data_source_router: DataSourceRouter) -> TETDataPipeline:
    """
    创建TET数据管道实例

    Args:
        data_source_router: 数据源路由器

    Returns:
        TETDataPipeline: TET管道实例
    """
    return TETDataPipeline(data_source_router)


# 便捷函数
def process_data_request(symbol: str, asset_type: AssetType, data_type: DataType,
                         data_source_router: DataSourceRouter, **kwargs) -> StandardData:
    """
    便捷的数据请求处理函数

    Args:
        symbol: 交易代码
        asset_type: 资产类型
        data_type: 数据类型
        data_source_router: 数据源路由器
        **kwargs: 其他参数

    Returns:
        StandardData: 处理结果
    """
    pipeline = create_tet_pipeline(data_source_router)

    query = StandardQuery(
        symbol=symbol,
        asset_type=asset_type,
        data_type=data_type,
        **kwargs
    )

    return pipeline.process(query)
