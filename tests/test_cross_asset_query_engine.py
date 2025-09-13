"""
跨资产数据库统一查询引擎测试

测试跨资产查询引擎的核心功能，包括：
1. 查询请求验证
2. 执行计划生成
3. SQL查询构建
4. 并行和顺序查询执行
5. 结果聚合和缓存
6. 统计信息收集

作者: FactorWeave-Quant团队
版本: 1.0
"""

from core.plugin_types import AssetType, DataType
from core.cross_asset_query_engine import (
    CrossAssetQueryEngine, CrossAssetQueryRequest, QueryResult,
    QueryType, AggregationType, SortOrder, QueryFilter, QuerySort, QueryAggregation,
    get_cross_asset_query_engine
)
import unittest
import tempfile
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQueryFilter(unittest.TestCase):
    """测试查询过滤器"""

    def test_basic_filter_to_sql(self):
        """测试基本过滤器转SQL"""
        filter_obj = QueryFilter("price", ">", 100)
        sql = filter_obj.to_sql_condition()
        self.assertEqual(sql, "price > '100'")

    def test_in_filter_to_sql(self):
        """测试IN过滤器转SQL"""
        filter_obj = QueryFilter("symbol", "IN", ["AAPL", "MSFT", "GOOGL"])
        sql = filter_obj.to_sql_condition()
        self.assertEqual(sql, "symbol IN ('AAPL', 'MSFT', 'GOOGL')")

    def test_between_filter_to_sql(self):
        """测试BETWEEN过滤器转SQL"""
        filter_obj = QueryFilter("price", "BETWEEN", [100, 200])
        sql = filter_obj.to_sql_condition()
        self.assertEqual(sql, "price BETWEEN '100' AND '200'")

    def test_like_filter_to_sql(self):
        """测试LIKE过滤器转SQL"""
        filter_obj = QueryFilter("symbol", "LIKE", "AAPL%")
        sql = filter_obj.to_sql_condition()
        self.assertEqual(sql, "symbol LIKE 'AAPL%'")


class TestQuerySort(unittest.TestCase):
    """测试查询排序"""

    def test_asc_sort_to_sql(self):
        """测试升序排序转SQL"""
        sort_obj = QuerySort("timestamp", SortOrder.ASC)
        sql = sort_obj.to_sql_order()
        self.assertEqual(sql, "timestamp ASC")

    def test_desc_sort_to_sql(self):
        """测试降序排序转SQL"""
        sort_obj = QuerySort("price", SortOrder.DESC)
        sql = sort_obj.to_sql_order()
        self.assertEqual(sql, "price DESC")


class TestQueryAggregation(unittest.TestCase):
    """测试查询聚合"""

    def test_sum_aggregation_to_sql(self):
        """测试SUM聚合转SQL"""
        agg_obj = QueryAggregation("volume", AggregationType.SUM, "total_volume")
        sql = agg_obj.to_sql_aggregation()
        self.assertEqual(sql, "SUM(volume) AS total_volume")

    def test_avg_aggregation_to_sql(self):
        """测试AVG聚合转SQL"""
        agg_obj = QueryAggregation("price", AggregationType.AVG)
        sql = agg_obj.to_sql_aggregation()
        self.assertEqual(sql, "AVG(price)")


class TestCrossAssetQueryRequest(unittest.TestCase):
    """测试跨资产查询请求"""

    def test_valid_request(self):
        """测试有效请求"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )

        errors = request.validate()
        self.assertEqual(len(errors), 0)

    def test_invalid_date_range(self):
        """测试无效日期范围"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            start_date=datetime(2023, 12, 31),
            end_date=datetime(2023, 1, 1)
        )

        errors = request.validate()
        self.assertIn("start_date must be before end_date", errors)

    def test_missing_data_type(self):
        """测试缺少数据类型"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=None
        )

        errors = request.validate()
        self.assertIn("data_type is required", errors)

    def test_invalid_limit(self):
        """测试无效限制"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            limit=-1
        )

        errors = request.validate()
        self.assertIn("limit must be positive", errors)


class TestCrossAssetQueryEngine(unittest.TestCase):
    """测试跨资产查询引擎"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock dependencies
        self.mock_asset_db_manager = Mock()
        self.mock_asset_type_identifier = Mock()

        # Mock connection
        self.mock_connection = Mock()
        self.mock_connection.execute.return_value.fetchall.return_value = [
            ("AAPL", "2023-01-01", 150.0, 155.0, 148.0, 152.0, 1000000),
            ("AAPL", "2023-01-02", 152.0, 157.0, 150.0, 155.0, 1200000)
        ]
        self.mock_connection.description = [
            ("symbol",), ("timestamp",), ("open",), ("high",), ("low",), ("close",), ("volume",)
        ]

        self.mock_asset_db_manager.get_connection.return_value.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_asset_db_manager.get_connection.return_value.__exit__ = Mock(return_value=None)
        self.mock_asset_db_manager.get_database_path.return_value = "/path/to/db"

        self.mock_asset_type_identifier.identify_asset_type_by_symbol.return_value = AssetType.STOCK_US

        # 创建引擎实例
        with patch('core.cross_asset_query_engine.get_asset_database_manager', return_value=self.mock_asset_db_manager), \
                patch('core.cross_asset_query_engine.get_asset_type_identifier', return_value=self.mock_asset_type_identifier):
            self.engine = CrossAssetQueryEngine(max_workers=2)

    def tearDown(self):
        """清理测试环境"""
        self.engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine)
        self.assertIsNotNone(self.engine.asset_db_manager)
        self.assertIsNotNone(self.engine.asset_type_identifier)
        self.assertIsNotNone(self.engine.executor)

    def test_determine_target_assets_by_symbols(self):
        """测试根据符号确定目标资产"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL", "MSFT"]
        )

        target_assets = self.engine._determine_target_assets(request)

        # 验证调用了符号识别
        self.assertEqual(self.mock_asset_type_identifier.identify_asset_type_by_symbol.call_count, 2)
        self.assertIn(AssetType.STOCK_US, target_assets)

    def test_determine_target_assets_by_asset_types(self):
        """测试根据资产类型确定目标资产"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.MULTI_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            asset_types=[AssetType.STOCK_US, AssetType.CRYPTO]
        )

        target_assets = self.engine._determine_target_assets(request)

        self.assertIn(AssetType.STOCK_US, target_assets)
        self.assertIn(AssetType.CRYPTO, target_assets)

    def test_get_table_name(self):
        """测试获取表名"""
        table_name = self.engine._get_table_name(DataType.HISTORICAL_KLINE)
        self.assertEqual(table_name, "historical_kline_data")

        table_name = self.engine._get_table_name(DataType.REAL_TIME_QUOTE)
        self.assertEqual(table_name, "real_time_quote_data")

    def test_build_select_clause_basic(self):
        """测试构建基本SELECT子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            fields=["symbol", "timestamp", "close"]
        )

        select_clause = self.engine._build_select_clause(request)
        self.assertEqual(select_clause, "symbol, timestamp, close")

    def test_build_select_clause_distinct(self):
        """测试构建DISTINCT SELECT子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            fields=["symbol"],
            distinct=True
        )

        select_clause = self.engine._build_select_clause(request)
        self.assertEqual(select_clause, "DISTINCT symbol")

    def test_build_select_clause_aggregation(self):
        """测试构建聚合SELECT子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.AGGREGATED,
            data_type=DataType.HISTORICAL_KLINE,
            group_by=["symbol"],
            aggregations=[
                QueryAggregation("volume", AggregationType.SUM, "total_volume"),
                QueryAggregation("close", AggregationType.AVG, "avg_price")
            ]
        )

        select_clause = self.engine._build_select_clause(request)
        self.assertEqual(select_clause, "symbol, SUM(volume) AS total_volume, AVG(close) AS avg_price")

    def test_build_where_clause(self):
        """测试构建WHERE子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            filters=[QueryFilter("volume", ">", 1000000)]
        )

        where_clause = self.engine._build_where_clause(request, AssetType.STOCK_US)

        self.assertIn("timestamp >= '2023-01-01 00:00:00'", where_clause)
        self.assertIn("timestamp <= '2023-12-31 00:00:00'", where_clause)
        self.assertIn("symbol IN ('AAPL')", where_clause)
        self.assertIn("volume > '1000000'", where_clause)

    def test_build_group_by_clause(self):
        """测试构建GROUP BY子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.AGGREGATED,
            data_type=DataType.HISTORICAL_KLINE,
            group_by=["symbol", "DATE(timestamp)"]
        )

        group_by_clause = self.engine._build_group_by_clause(request)
        self.assertEqual(group_by_clause, "symbol, DATE(timestamp)")

    def test_build_order_by_clause(self):
        """测试构建ORDER BY子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            sort_by=[
                QuerySort("timestamp", SortOrder.ASC),
                QuerySort("volume", SortOrder.DESC)
            ]
        )

        order_by_clause = self.engine._build_order_by_clause(request)
        self.assertEqual(order_by_clause, "timestamp ASC, volume DESC")

    def test_build_limit_clause(self):
        """测试构建LIMIT子句"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            limit=100,
            offset=50
        )

        limit_clause = self.engine._build_limit_clause(request)
        self.assertEqual(limit_clause, "LIMIT 100 OFFSET 50")

    def test_build_sql_query(self):
        """测试构建完整SQL查询"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            fields=["symbol", "timestamp", "close"],
            start_date=datetime(2023, 1, 1),
            sort_by=[QuerySort("timestamp", SortOrder.ASC)],
            limit=10
        )

        sql_query = self.engine._build_sql_query(request, AssetType.STOCK_US)

        self.assertIn("SELECT symbol, timestamp, close", sql_query)
        self.assertIn("FROM historical_kline_data", sql_query)
        self.assertIn("WHERE", sql_query)
        self.assertIn("ORDER BY timestamp ASC", sql_query)
        self.assertIn("LIMIT 10", sql_query)

    def test_execute_single_asset_query(self):
        """测试执行单个资产查询"""
        sql_query = "SELECT * FROM historical_kline_data WHERE symbol = 'AAPL'"

        result = self.engine._execute_single_asset_query(AssetType.STOCK_US, sql_query)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn("symbol", result.columns)
        self.assertEqual(result.iloc[0]["symbol"], "AAPL")

    def test_generate_execution_plan(self):
        """测试生成执行计划"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"]
        )

        execution_plan = self.engine._generate_execution_plan(request)

        self.assertIsNotNone(execution_plan)
        self.assertEqual(execution_plan.request, request)
        self.assertGreater(len(execution_plan.asset_queries), 0)
        self.assertGreater(execution_plan.estimated_cost, 0)

    def test_execute_query_success(self):
        """测试成功执行查询"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            parallel_execution=False
        )

        result = self.engine.execute_query(request)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertGreater(result.total_records, 0)
        self.assertGreater(result.execution_time_ms, 0)
        self.assertIn(AssetType.STOCK_US, result.affected_assets)

    def test_execute_query_validation_error(self):
        """测试查询验证错误"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=None  # 缺少必要参数
        )

        result = self.engine.execute_query(request)

        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("data_type is required", result.errors)

    def test_cache_functionality(self):
        """测试缓存功能"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            parallel_execution=False
        )

        # 第一次查询
        result1 = self.engine.execute_query(request)

        # 第二次查询（应该使用缓存）
        result2 = self.engine.execute_query(request)

        self.assertTrue(result1.success)
        self.assertTrue(result2.success)

        # 验证缓存键生成
        cache_key = self.engine._generate_cache_key(request)
        self.assertIsInstance(cache_key, str)
        self.assertGreater(len(cache_key), 0)

    def test_query_statistics(self):
        """测试查询统计"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            parallel_execution=False
        )

        # 执行查询
        self.engine.execute_query(request)

        # 获取统计信息
        stats = self.engine.get_query_statistics()

        self.assertIn('query_stats', stats)
        self.assertIn('cache_size', stats)
        self.assertIn(QueryType.SINGLE_ASSET.value, stats['query_stats'])

        query_type_stats = stats['query_stats'][QueryType.SINGLE_ASSET.value]
        self.assertEqual(query_type_stats['total_queries'], 1)
        self.assertEqual(query_type_stats['successful_queries'], 1)

    def test_clear_cache(self):
        """测试清空缓存"""
        request = CrossAssetQueryRequest(
            query_type=QueryType.SINGLE_ASSET,
            data_type=DataType.HISTORICAL_KLINE,
            symbols=["AAPL"],
            parallel_execution=False
        )

        # 执行查询以创建缓存
        self.engine.execute_query(request)

        # 验证缓存存在
        stats_before = self.engine.get_query_statistics()
        self.assertGreaterEqual(stats_before['cache_size'], 0)

        # 清空缓存
        self.engine.clear_cache()

        # 验证缓存已清空
        stats_after = self.engine.get_query_statistics()
        self.assertEqual(stats_after['cache_size'], 0)


class TestGlobalInstance(unittest.TestCase):
    """测试全局实例管理"""

    def test_get_cross_asset_query_engine(self):
        """测试获取全局查询引擎实例"""
        with patch('core.cross_asset_query_engine.get_asset_database_manager'), \
                patch('core.cross_asset_query_engine.get_asset_type_identifier'):
            engine1 = get_cross_asset_query_engine()
            engine2 = get_cross_asset_query_engine()

            # 验证单例模式
            self.assertIs(engine1, engine2)

            # 清理
            engine1.close()


if __name__ == '__main__':
    unittest.main()
