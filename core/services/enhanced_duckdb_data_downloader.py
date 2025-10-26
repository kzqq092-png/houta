"""
增强DuckDB数据下载服务

专门用于替代HIkyuu的数据下载功能，提供：
1. 历史K线数据下载和存储
2. 基本面数据下载和存储  
3. 实时数据缓存和管理
4. 数据质量验证和清洗
5. 智能增量更新
6. 多数据源聚合

作者: FactorWeave-Quant 开发团队
版本: 1.0.0
日期: 2024
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from loguru import logger
from pathlib import Path

from ..database.duckdb_manager import get_connection_manager
from ..database.duckdb_operations import get_duckdb_operations
from ..database.table_manager import DynamicTableManager
from ..plugin_types import AssetType, DataType
from ..tet_data_pipeline import StandardQuery
from .uni_plugin_data_manager import UniPluginDataManager

logger = logger.bind(module=__name__)


class EnhancedDuckDBDataDownloader:
    """
    增强DuckDB数据下载器

    替代HIkyuu的核心数据获取功能，通过TET框架和插件系统
    实现多数据源的数据下载、存储和管理。
    """

    def __init__(self, uni_plugin_manager: UniPluginDataManager):
        self.uni_plugin_manager = uni_plugin_manager
        self.duckdb_manager = get_connection_manager()
        self.duckdb_operations = get_duckdb_operations()
        self.table_manager = DynamicTableManager()

        # 数据库路径配置
        self.db_paths = {
            'kline': 'data/kline_stock.duckdb',
            'fundamental': 'data/fundamental_data.duckdb',
            'realtime': 'data/realtime_data.duckdb',
            'macro': 'data/macro_economic.duckdb'
        }

        # 确保数据库目录存在
        for db_path in self.db_paths.values():
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info("EnhancedDuckDBDataDownloader 初始化完成")

    async def download_historical_kline_data(self,
                                             symbols: List[str],
                                             period: str = 'D',
                                             start_date: Optional[datetime] = None,
                                             end_date: Optional[datetime] = None,
                                             asset_type: AssetType = AssetType.STOCK_A,
                                             force_update: bool = False) -> Dict[str, pd.DataFrame]:
        """
        下载历史K线数据到DuckDB

        Args:
            symbols: 股票代码列表
            period: 周期 (D, W, M, 1m, 5m, 15m, 30m, 60m)
            start_date: 开始日期
            end_date: 结束日期
            asset_type: 资产类型
            force_update: 强制更新

        Returns:
            Dict[symbol, DataFrame]: 下载的数据
        """
        logger.info(f"开始下载历史K线数据: {len(symbols)}只股票, 周期={period}")

        # 设置默认日期范围
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=365 * 2)  # 默认2年数据

        results = {}

        for symbol in symbols:
            try:
                # 检查是否需要更新
                if not force_update:
                    latest_date = await self._get_latest_data_date(symbol, period, 'kline')
                    if latest_date and (end_date - latest_date).days < 1:
                        logger.debug(f"股票 {symbol} 数据已是最新，跳过下载")
                        continue

                # 通过TET框架获取数据
                query = StandardQuery(
                    symbol=symbol,
                    data_type=DataType.HISTORICAL_KLINE,
                    asset_type=asset_type,
                    start_date=start_date,
                    end_date=end_date,
                    extra_params={'period': period}
                )

                context = await self.uni_plugin_manager.create_request_context(query)
                data = await self.uni_plugin_manager.execute_data_request(context)

                if data is not None and not data.empty:
                    # 数据质量验证
                    cleaned_data = self._validate_and_clean_kline_data(data, symbol)

                    if not cleaned_data.empty:
                        # 存储到DuckDB
                        await self._store_kline_data_to_duckdb(cleaned_data, symbol, period)
                        results[symbol] = cleaned_data
                        logger.info(f"成功下载并存储 {symbol} K线数据: {len(cleaned_data)} 条")
                    else:
                        logger.warning(f"股票 {symbol} 数据质量验证失败")
                else:
                    logger.warning(f"未获取到股票 {symbol} 的K线数据")

            except Exception as e:
                logger.error(f"下载股票 {symbol} K线数据失败: {e}")

        logger.info(f"历史K线数据下载完成: 成功 {len(results)}/{len(symbols)} 只股票")
        return results

    async def download_fundamental_data(self,
                                        symbols: List[str],
                                        data_types: List[str] = None,
                                        asset_type: AssetType = AssetType.STOCK_A) -> Dict[str, Dict[str, Any]]:
        """
        下载基本面数据到DuckDB

        Args:
            symbols: 股票代码列表
            data_types: 数据类型列表 ['financial_statement', 'announcement', 'analyst_rating']
            asset_type: 资产类型

        Returns:
            Dict[symbol, Dict[data_type, data]]: 下载的数据
        """
        if not data_types:
            data_types = ['financial_statement', 'announcement', 'analyst_rating']

        logger.info(f"开始下载基本面数据: {len(symbols)}只股票, 类型={data_types}")

        results = {}

        for symbol in symbols:
            symbol_results = {}

            for data_type in data_types:
                try:
                    # 构建查询
                    if data_type == 'financial_statement':
                        query_data_type = DataType.FINANCIAL_STATEMENT
                    elif data_type == 'announcement':
                        query_data_type = DataType.ANNOUNCEMENT
                    elif data_type == 'analyst_rating':
                        query_data_type = DataType.ANALYST_RATING
                    else:
                        continue

                    query = StandardQuery(
                        symbol=symbol,
                        data_type=query_data_type,
                        asset_type=asset_type,
                        extra_params={'periods': 4}  # 获取最近4期数据
                    )

                    context = await self.uni_plugin_manager.create_request_context(query)
                    data = await self.uni_plugin_manager.execute_data_request(context)

                    if data is not None:
                        # 存储到DuckDB
                        await self._store_fundamental_data_to_duckdb(data, symbol, data_type)
                        symbol_results[data_type] = data
                        logger.debug(f"成功下载 {symbol} {data_type} 数据")

                except Exception as e:
                    logger.error(f"下载 {symbol} {data_type} 数据失败: {e}")

            if symbol_results:
                results[symbol] = symbol_results

        logger.info(f"基本面数据下载完成: 成功 {len(results)}/{len(symbols)} 只股票")
        return results

    async def download_stock_list(self,
                                  market: str = 'all',
                                  asset_type: AssetType = AssetType.STOCK_A) -> pd.DataFrame:
        """
        下载股票列表到DuckDB

        Args:
            market: 市场代码 ('sh', 'sz', 'bj', 'all')
            asset_type: 资产类型

        Returns:
            DataFrame: 股票列表数据
        """
        logger.info(f"开始下载股票列表: 市场={market}")

        try:
            # 通过TET框架获取股票列表
            query = StandardQuery(
                symbol="",  # 股票列表不需要具体代码
                data_type=DataType.ASSET_LIST,
                asset_type=asset_type,
                extra_params={'market': market}
            )

            context = await self.uni_plugin_manager.create_request_context(query)
            data = await self.uni_plugin_manager.execute_data_request(context)

            if data is not None and not data.empty:
                # 数据清洗和标准化
                cleaned_data = self._validate_and_clean_stock_list(data)

                # 存储到DuckDB
                await self._store_stock_list_to_duckdb(cleaned_data, market)

                logger.info(f"成功下载股票列表: {len(cleaned_data)} 只股票")
                return cleaned_data
            else:
                logger.warning("未获取到股票列表数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"下载股票列表失败: {e}")
            return pd.DataFrame()

    async def incremental_update_all_data(self,
                                          symbols: Optional[List[str]] = None,
                                          max_symbols: int = 100) -> Dict[str, Any]:
        """
        增量更新所有数据

        Args:
            symbols: 指定股票列表，None则自动获取
            max_symbols: 最大处理股票数量

        Returns:
            Dict: 更新结果统计
        """
        logger.info("开始增量更新所有数据")

        # 获取股票列表
        if not symbols:
            stock_df = await self.download_stock_list()
            if not stock_df.empty:
                symbols = stock_df['code'].head(max_symbols).tolist()
            else:
                logger.error("无法获取股票列表，增量更新失败")
                return {}

        results = {
            'kline_updated': 0,
            'fundamental_updated': 0,
            'errors': []
        }

        # 更新K线数据
        try:
            kline_results = await self.download_historical_kline_data(
                symbols=symbols,
                period='D',
                start_date=datetime.now() - timedelta(days=7),  # 最近一周
                force_update=False
            )
            results['kline_updated'] = len(kline_results)
        except Exception as e:
            results['errors'].append(f"K线数据更新失败: {e}")

        # 更新基本面数据
        try:
            fundamental_results = await self.download_fundamental_data(
                symbols=symbols[:20],  # 基本面数据更新较慢，限制数量
                data_types=['financial_statement']
            )
            results['fundamental_updated'] = len(fundamental_results)
        except Exception as e:
            results['errors'].append(f"基本面数据更新失败: {e}")

        logger.info(f"增量更新完成: K线={results['kline_updated']}, 基本面={results['fundamental_updated']}")
        return results

    def _validate_and_clean_kline_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """验证和清洗K线数据"""
        try:
            if data.empty:
                return data

            # 必需字段检查
            required_fields = ['open', 'high', 'low', 'close', 'volume']
            missing_fields = [f for f in required_fields if f not in data.columns]
            if missing_fields:
                logger.warning(f"股票 {symbol} K线数据缺少字段: {missing_fields}")
                return pd.DataFrame()

            # 数据类型转换
            for field in required_fields:
                data[field] = pd.to_numeric(data[field], errors='coerce')

            # 异常值过滤
            data = data.dropna(subset=required_fields)
            data = data[(data['high'] >= data['low']) &
                        (data['high'] >= data['open']) &
                        (data['high'] >= data['close']) &
                        (data['low'] <= data['open']) &
                        (data['low'] <= data['close']) &
                        (data['volume'] >= 0)]

            # 添加股票代码
            data['symbol'] = symbol

            return data

        except Exception as e:
            logger.error(f"K线数据验证失败 {symbol}: {e}")
            return pd.DataFrame()

    def _validate_and_clean_stock_list(self, data: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗股票列表数据"""
        try:
            if data.empty:
                return data

            # 必需字段检查
            required_fields = ['code', 'name']
            for field in required_fields:
                if field not in data.columns:
                    logger.warning(f"股票列表缺少字段: {field}")
                    return pd.DataFrame()

            # 去重和清洗
            data = data.drop_duplicates(subset=['code'])
            data = data.dropna(subset=['code', 'name'])

            # 确保必要字段存在
            if 'market' not in data.columns:
                data['market'] = data['code'].str[:2]  # 从代码推断市场
            if 'industry' not in data.columns:
                data['industry'] = '其他'

            return data

        except Exception as e:
            logger.error(f"股票列表数据验证失败: {e}")
            return pd.DataFrame()

    async def _get_latest_data_date(self, symbol: str, period: str, data_category: str) -> Optional[datetime]:
        """获取最新数据日期"""
        try:
            db_path = self.db_paths.get(data_category)
            if not db_path:
                return None

            query = f"""
                SELECT MAX(datetime) as latest_date 
                FROM kline_data_{period.lower()} 
                WHERE symbol = ?
            """

            result = self.duckdb_operations.execute_query(db_path, query, [symbol])
            if not result.empty and result.iloc[0]['latest_date']:
                return pd.to_datetime(result.iloc[0]['latest_date'])

        except Exception as e:
            logger.debug(f"获取最新数据日期失败 {symbol}: {e}")

        return None

    async def _store_kline_data_to_duckdb(self, data: pd.DataFrame, symbol: str, period: str):
        """存储K线数据到DuckDB"""
        try:
            db_path = self.db_paths['kline']
            table_name = f"kline_data_{period.lower()}"

            # 确保表存在
            await self.table_manager.ensure_table_exists(
                db_path, 'kline', 'enhanced_duckdb_downloader', period
            )

            # 插入数据
            result = self.duckdb_operations.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                dataframe=data,
                conflict_resolution='replace'
            )

            if result.get('success'):
                logger.debug(f"K线数据存储成功: {symbol}, {len(data)} 条")
            else:
                logger.warning(f"K线数据存储失败: {symbol}")

        except Exception as e:
            logger.error(f"存储K线数据失败 {symbol}: {e}")

    async def _store_fundamental_data_to_duckdb(self, data: Any, symbol: str, data_type: str):
        """存储基本面数据到DuckDB"""
        try:
            db_path = self.db_paths['fundamental']

            if data_type == 'financial_statement':
                table_name = "financial_statements"
            elif data_type == 'announcement':
                table_name = "company_announcements"
            elif data_type == 'analyst_rating':
                table_name = "analyst_ratings"
            else:
                return

            # 确保表存在
            await self.table_manager.ensure_table_exists(
                db_path, data_type, 'enhanced_duckdb_downloader'
            )

            # 转换数据格式
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            df['symbol'] = symbol
            df['update_time'] = datetime.now()

            # 插入数据
            result = self.duckdb_operations.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                dataframe=df,
                conflict_resolution='replace'
            )

            if result.get('success'):
                logger.debug(f"基本面数据存储成功: {symbol} {data_type}")

        except Exception as e:
            logger.error(f"存储基本面数据失败 {symbol} {data_type}: {e}")

    async def _store_stock_list_to_duckdb(self, data: pd.DataFrame, market: str):
        """存储股票列表到DuckDB"""
        try:
            db_path = self.db_paths['kline']
            table_name = "stock_list"

            # 确保表存在
            await self.table_manager.ensure_table_exists(
                db_path, 'asset_list', 'enhanced_duckdb_downloader'
            )

            # 添加更新时间
            data['update_time'] = datetime.now()
            data['market_filter'] = market

            # 插入数据
            result = self.duckdb_operations.insert_dataframe(
                database_path=db_path,
                table_name=table_name,
                dataframe=data,
                conflict_resolution='replace'
            )

            if result.get('success'):
                logger.debug(f"股票列表存储成功: {len(data)} 只股票")

        except Exception as e:
            logger.error(f"存储股票列表失败: {e}")

    async def get_data_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        stats = {}

        try:
            for category, db_path in self.db_paths.items():
                if Path(db_path).exists():
                    # 获取数据库大小
                    db_size = Path(db_path).stat().st_size / (1024 * 1024)  # MB

                    # 获取表统计
                    tables_query = "SELECT table_name, estimated_size FROM duckdb_tables()"
                    tables_result = self.duckdb_operations.execute_query(db_path, tables_query)

                    stats[category] = {
                        'db_size_mb': round(db_size, 2),
                        'tables': tables_result.to_dict('records') if not tables_result.empty else []
                    }
                else:
                    stats[category] = {'db_size_mb': 0, 'tables': []}

        except Exception as e:
            logger.error(f"获取数据统计失败: {e}")

        return stats


# 全局实例管理
_enhanced_duckdb_downloader: Optional[EnhancedDuckDBDataDownloader] = None


def get_enhanced_duckdb_downloader(uni_plugin_manager: UniPluginDataManager = None) -> EnhancedDuckDBDataDownloader:
    """获取增强DuckDB数据下载器实例"""
    global _enhanced_duckdb_downloader

    if _enhanced_duckdb_downloader is None:
        if uni_plugin_manager is None:
            raise ValueError("首次创建需要提供 uni_plugin_manager")
        _enhanced_duckdb_downloader = EnhancedDuckDBDataDownloader(uni_plugin_manager)

    return _enhanced_duckdb_downloader


def cleanup_enhanced_duckdb_downloader():
    """清理增强DuckDB数据下载器"""
    global _enhanced_duckdb_downloader
    _enhanced_duckdb_downloader = None
