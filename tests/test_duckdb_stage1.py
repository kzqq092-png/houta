"""
第一阶段DuckDB数据库存储基础架构单元测试

测试覆盖：
- DuckDB连接管理器测试
- 动态表管理器测试
- 数据操作测试
- SQLite扩展测试

作者: FactorWeave-Quant团队
版本: 1.0
"""

import unittest
import tempfile
import shutil
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, date
from unittest.mock import patch, MagicMock

# 导入待测试的模块
from core.database.duckdb_manager import (
    DuckDBConnectionManager, DuckDBConfig, DuckDBConnectionPool,
    get_connection_manager, initialize_duckdb_manager, cleanup_duckdb_manager
)
from core.database.table_manager import (
    DynamicTableManager, TableType, TableSchema, TableSchemaRegistry,
    get_table_manager
)
from core.database.duckdb_operations import (
    DuckDBOperations, QueryFilter, QueryResult, InsertResult,
    get_duckdb_operations
)
from core.database.sqlite_extensions import (
    SQLiteExtensionManager, PluginTableMapping, DataSourceConfig, PerformanceStatistic,
    get_sqlite_extension_manager
)


class TestDuckDBConnectionManager(unittest.TestCase):
    """DuckDB连接管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.config = DuckDBConfig(
            memory_limit='1GB',
            threads='2'
        )

    def tearDown(self):
        """测试后清理"""
        cleanup_duckdb_manager()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_duckdb_config(self):
        """测试DuckDB配置"""
        config = DuckDBConfig()
        config_dict = config.to_dict()

        self.assertIn('memory_limit', config_dict)
        self.assertIn('threads', config_dict)
        self.assertIn('compression', config_dict)
        self.assertEqual(config_dict['compression'], 'zstd')

    def test_connection_pool_creation(self):
        """测试连接池创建"""
        pool = DuckDBConnectionPool(str(self.db_path), pool_size=3, config=self.config)

        self.assertEqual(pool.pool_size, 3)
        self.assertEqual(pool.database_path, str(self.db_path))
        self.assertIsNotNone(pool.config)

    def test_connection_pool_get_connection(self):
        """测试连接池获取连接"""
        pool = DuckDBConnectionPool(str(self.db_path), pool_size=2, config=self.config)

        with pool.get_connection() as conn:
            self.assertIsNotNone(conn)
            # 测试简单查询
            result = conn.execute("SELECT 1 as test").fetchone()
            self.assertEqual(result[0], 1)

    def test_connection_pool_health_check(self):
        """测试连接池健康检查"""
        pool = DuckDBConnectionPool(str(self.db_path), pool_size=2, config=self.config)

        health_status = pool.health_check()

        self.assertEqual(health_status['status'], 'healthy')
        self.assertEqual(health_status['pool_size'], 2)
        self.assertIn('total_connections', health_status)

    def test_connection_manager(self):
        """测试连接管理器"""
        manager = DuckDBConnectionManager()

        # 获取连接池
        pool = manager.get_pool(str(self.db_path), pool_size=2, config=self.config)
        self.assertIsNotNone(pool)

        # 测试获取连接
        with manager.get_connection(str(self.db_path)) as conn:
            result = conn.execute("SELECT 2 as test").fetchone()
            self.assertEqual(result[0], 2)

    def test_connection_manager_health_check(self):
        """测试连接管理器健康检查"""
        manager = DuckDBConnectionManager()

        # 创建连接池
        manager.get_pool(str(self.db_path), pool_size=2)

        # 健康检查
        health_results = manager.health_check_all()

        self.assertIn(str(self.db_path), health_results)
        self.assertEqual(health_results[str(self.db_path)]['status'], 'healthy')

    def test_global_connection_manager(self):
        """测试全局连接管理器"""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        # 应该是同一个实例
        self.assertIs(manager1, manager2)


class TestDynamicTableManager(unittest.TestCase):
    """动态表管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # 初始化连接管理器
        self.connection_manager = DuckDBConnectionManager()
        self.table_manager = DynamicTableManager(self.connection_manager)

    def tearDown(self):
        """测试后清理"""
        cleanup_duckdb_manager()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_table_schema_registry(self):
        """测试表结构注册表"""
        registry = TableSchemaRegistry()

        # 测试获取默认结构
        kline_schema = registry.get_schema(TableType.KLINE_DATA)
        self.assertIsNotNone(kline_schema)
        self.assertIn('symbol', kline_schema.columns)
        self.assertIn('datetime', kline_schema.columns)
        self.assertIn('open', kline_schema.columns)

        # 测试获取所有结构
        all_schemas = registry.get_all_schemas()
        self.assertIn(TableType.KLINE_DATA, all_schemas)
        self.assertIn(TableType.STOCK_BASIC_INFO, all_schemas)

    def test_generate_table_name(self):
        """测试表名生成"""
        # 基础表名
        table_name = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test_plugin"
        )
        self.assertEqual(table_name, "kline_data_test_plugin")

        # 带周期的表名
        table_name_with_period = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test_plugin", "1d"
        )
        self.assertEqual(table_name_with_period, "kline_data_test_plugin_1d")

        # 特殊字符处理
        table_name_special = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test-plugin@123"
        )
        self.assertEqual(table_name_special, "kline_data_test_plugin_123")

    def test_create_table(self):
        """测试创建表"""
        success = self.table_manager.create_table(
            str(self.db_path), TableType.KLINE_DATA, "test_plugin", "1d"
        )

        self.assertTrue(success)

        # 检查表是否存在
        table_name = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test_plugin", "1d"
        )
        exists = self.table_manager.table_exists(str(self.db_path), table_name)
        self.assertTrue(exists)

    def test_create_multiple_tables(self):
        """测试创建多个表"""
        # 创建K线表
        success1 = self.table_manager.create_table(
            str(self.db_path), TableType.KLINE_DATA, "plugin1", "1d"
        )

        # 创建股票信息表
        success2 = self.table_manager.create_table(
            str(self.db_path), TableType.STOCK_BASIC_INFO, "plugin1"
        )

        self.assertTrue(success1)
        self.assertTrue(success2)

        # 列出表
        tables = self.table_manager.list_tables(str(self.db_path), "plugin1")
        self.assertEqual(len(tables), 2)

    def test_get_table_info(self):
        """测试获取表信息"""
        # 创建表
        self.table_manager.create_table(
            str(self.db_path), TableType.KLINE_DATA, "test_plugin"
        )

        table_name = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test_plugin"
        )

        # 获取表信息
        table_info = self.table_manager.get_table_info(str(self.db_path), table_name)

        self.assertIsNotNone(table_info)
        self.assertEqual(table_info['table_name'], table_name)
        self.assertIn('columns', table_info)
        self.assertIn('row_count', table_info)

    def test_drop_table(self):
        """测试删除表"""
        # 创建表
        self.table_manager.create_table(
            str(self.db_path), TableType.KLINE_DATA, "test_plugin"
        )

        table_name = self.table_manager.generate_table_name(
            TableType.KLINE_DATA, "test_plugin"
        )

        # 确认表存在
        self.assertTrue(self.table_manager.table_exists(str(self.db_path), table_name))

        # 删除表
        success = self.table_manager.drop_table(
            str(self.db_path), TableType.KLINE_DATA, "test_plugin"
        )

        self.assertTrue(success)
        self.assertFalse(self.table_manager.table_exists(str(self.db_path), table_name))


class TestDuckDBOperations(unittest.TestCase):
    """DuckDB数据操作测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # 初始化组件
        self.connection_manager = DuckDBConnectionManager()
        self.table_manager = DynamicTableManager(self.connection_manager)
        self.operations = DuckDBOperations(self.connection_manager, self.table_manager)

        # 创建测试表
        self.table_name = "kline_data_test_plugin_1d"
        self.table_manager.create_table(
            str(self.db_path), TableType.KLINE_DATA, "test_plugin", "1d"
        )

    def tearDown(self):
        """测试后清理"""
        cleanup_duckdb_manager()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_data(self, rows: int = 100) -> pd.DataFrame:
        """创建测试数据"""
        data = []
        base_date = datetime(2024, 1, 1)

        for i in range(rows):
            data.append({
                'symbol': f'000{i % 10:03d}',
                'datetime': base_date.replace(day=1 + i % 28),
                'open': 10.0 + i * 0.1,
                'high': 10.5 + i * 0.1,
                'low': 9.5 + i * 0.1,
                'close': 10.2 + i * 0.1,
                'volume': 1000000 + i * 1000,
                'amount': 10000000.0 + i * 10000,
                'adj_close': 10.2 + i * 0.1,
                'adj_factor': 1.0,
                'vwap': 10.1 + i * 0.1,
                'bid_price': 10.0 + i * 0.1,
                'ask_price': 10.3 + i * 0.1,
                'bid_volume': 500000 + i * 500,
                'ask_volume': 500000 + i * 500,
                'rsi_14': 50.0 + (i % 50),
                'macd_dif': 0.1 + i * 0.01,
                'macd_dea': 0.05 + i * 0.005,
                'macd_histogram': 0.05 + i * 0.005,
                'kdj_k': 50.0 + (i % 50),
                'kdj_d': 50.0 + (i % 50),
                'kdj_j': 50.0 + (i % 50),
                'bollinger_upper': 11.0 + i * 0.1,
                'bollinger_middle': 10.0 + i * 0.1,
                'bollinger_lower': 9.0 + i * 0.1,
                'turnover_rate': 0.05 + (i % 10) * 0.01,
                'net_inflow_large': 1000000.0 + i * 10000,
                'net_inflow_medium': 500000.0 + i * 5000,
                'net_inflow_small': 100000.0 + i * 1000,
                'plugin_specific_data': '{}',
                'data_source': 'test_plugin',
                'created_at': datetime.now(),
                'data_quality_score': 0.95
            })

        return pd.DataFrame(data)

    def test_insert_dataframe(self):
        """测试DataFrame插入"""
        test_data = self._create_test_data(50)

        result = self.operations.insert_dataframe(
            str(self.db_path), self.table_name, test_data, batch_size=20
        )

        self.assertTrue(result.success)
        self.assertEqual(result.rows_inserted, 50)
        self.assertEqual(result.batch_count, 3)  # 50/20 = 3批次
        self.assertGreater(result.execution_time, 0)

    def test_insert_empty_dataframe(self):
        """测试插入空DataFrame"""
        empty_data = pd.DataFrame()

        result = self.operations.insert_dataframe(
            str(self.db_path), self.table_name, empty_data
        )

        self.assertTrue(result.success)
        self.assertEqual(result.rows_inserted, 0)
        self.assertEqual(result.batch_count, 0)

    def test_query_data(self):
        """测试数据查询"""
        # 先插入测试数据
        test_data = self._create_test_data(30)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 查询所有数据
        result = self.operations.query_data(str(self.db_path), self.table_name)

        self.assertTrue(result.success)
        self.assertEqual(result.row_count, 30)
        self.assertGreater(result.execution_time, 0)
        self.assertIn('symbol', result.columns)

    def test_query_with_filter(self):
        """测试带过滤条件的查询"""
        # 插入测试数据
        test_data = self._create_test_data(50)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 创建查询过滤条件
        query_filter = QueryFilter(
            symbols=['000001', '000002'],
            start_date='2024-01-01',
            end_date='2024-01-15',
            limit=10
        )

        result = self.operations.query_data(
            str(self.db_path), self.table_name, query_filter
        )

        self.assertTrue(result.success)
        self.assertLessEqual(result.row_count, 10)  # 受limit限制

    def test_custom_sql_query(self):
        """测试自定义SQL查询"""
        # 插入测试数据
        test_data = self._create_test_data(20)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 自定义SQL查询
        custom_sql = f"SELECT symbol, COUNT(*) as count FROM {self.table_name} GROUP BY symbol"

        result = self.operations.query_data(
            str(self.db_path), self.table_name, custom_sql=custom_sql
        )

        self.assertTrue(result.success)
        self.assertIn('symbol', result.columns)
        self.assertIn('count', result.columns)

    def test_update_data(self):
        """测试数据更新"""
        # 插入测试数据
        test_data = self._create_test_data(10)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 更新数据
        update_data = {'data_quality_score': 0.99}
        where_conditions = ["symbol = '000001'"]

        success = self.operations.update_data(
            str(self.db_path), self.table_name, update_data, where_conditions
        )

        self.assertTrue(success)

    def test_delete_data(self):
        """测试数据删除"""
        # 插入测试数据
        test_data = self._create_test_data(10)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 删除数据
        where_conditions = ["symbol = '000001'"]

        success = self.operations.delete_data(
            str(self.db_path), self.table_name, where_conditions
        )

        self.assertTrue(success)

    def test_transaction(self):
        """测试事务管理"""
        test_data = self._create_test_data(5)

        try:
            with self.operations.transaction(str(self.db_path)) as conn:
                # 在事务中插入数据
                conn.register('temp_data', test_data)
                conn.execute(f"INSERT INTO {self.table_name} SELECT * FROM temp_data")
                conn.unregister('temp_data')

                # 查询验证
                result = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}").fetchone()
                self.assertEqual(result[0], 5)

        except Exception as e:
            self.fail(f"事务执行失败: {e}")

    def test_get_table_statistics(self):
        """测试获取表统计信息"""
        # 插入测试数据
        test_data = self._create_test_data(15)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)

        # 获取统计信息
        stats = self.operations.get_table_statistics(str(self.db_path), self.table_name)

        self.assertIn('table_name', stats)
        self.assertIn('row_count', stats)
        self.assertIn('columns', stats)
        self.assertEqual(stats['row_count'], 15)

    def test_performance_stats(self):
        """测试性能统计"""
        # 执行一些操作
        test_data = self._create_test_data(10)
        self.operations.insert_dataframe(str(self.db_path), self.table_name, test_data)
        self.operations.query_data(str(self.db_path), self.table_name)

        # 获取性能统计
        stats = self.operations.get_performance_stats()

        self.assertIn('query_stats', stats)
        self.assertIn('insert_stats', stats)


class TestSQLiteExtensions(unittest.TestCase):
    """SQLite扩展测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_sqlite.db"
        self.extension_manager = SQLiteExtensionManager(str(self.db_path))

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_table_mapping(self):
        """测试插件表映射"""
        # 创建映射
        mapping = PluginTableMapping(
            plugin_name="test_plugin",
            table_type="kline_data",
            table_name="kline_data_test_plugin_1d",
            database_path="/path/to/db",
            period="1d",
            row_count=1000
        )

        # 添加映射
        success = self.extension_manager.add_table_mapping(mapping)
        self.assertTrue(success)

        # 获取映射
        mappings = self.extension_manager.get_table_mappings(plugin_name="test_plugin")
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].plugin_name, "test_plugin")
        self.assertEqual(mappings[0].table_type, "kline_data")

        # 更新统计
        success = self.extension_manager.update_table_mapping_stats(
            "test_plugin", "kline_data", 2000, "1d"
        )
        self.assertTrue(success)

        # 验证更新
        updated_mappings = self.extension_manager.get_table_mappings(plugin_name="test_plugin")
        self.assertEqual(updated_mappings[0].row_count, 2000)

    def test_data_source_config(self):
        """测试数据源配置"""
        # 创建配置
        config = DataSourceConfig(
            plugin_name="test_plugin",
            config_name="duckdb_config",
            config_data={
                "memory_limit": "2GB",
                "threads": 4,
                "compression": "zstd"
            },
            config_type="duckdb"
        )

        # 保存配置
        success = self.extension_manager.save_config(config)
        self.assertTrue(success)

        # 获取配置
        retrieved_config = self.extension_manager.get_config(
            "test_plugin", "duckdb_config", "duckdb"
        )

        self.assertIsNotNone(retrieved_config)
        self.assertEqual(retrieved_config.plugin_name, "test_plugin")
        self.assertEqual(retrieved_config.config_data["memory_limit"], "2GB")

        # 获取所有配置
        all_configs = self.extension_manager.get_all_configs(plugin_name="test_plugin")
        self.assertEqual(len(all_configs), 1)

    def test_performance_statistics(self):
        """测试性能统计"""
        # 记录性能统计
        stat = PerformanceStatistic(
            plugin_name="test_plugin",
            table_name="test_table",
            operation_type="insert",
            execution_time=1.5,
            row_count=1000,
            success=True,
            timestamp=datetime.now()
        )

        success = self.extension_manager.record_performance(stat)
        self.assertTrue(success)

        # 获取性能统计
        stats = self.extension_manager.get_performance_stats(
            plugin_name="test_plugin", hours=1
        )

        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0].plugin_name, "test_plugin")
        self.assertEqual(stats[0].operation_type, "insert")

        # 获取性能摘要
        summary = self.extension_manager.get_performance_summary(
            plugin_name="test_plugin", hours=1
        )

        self.assertIn("insert", summary)
        self.assertEqual(summary["insert"]["count"], 1)
        self.assertEqual(summary["insert"]["total_rows"], 1000)

    def test_cleanup_old_stats(self):
        """测试清理旧统计"""
        # 记录一些统计
        for i in range(5):
            stat = PerformanceStatistic(
                plugin_name=f"plugin_{i}",
                table_name=f"table_{i}",
                operation_type="query",
                execution_time=0.5,
                row_count=100,
                success=True
            )
            self.extension_manager.record_performance(stat)

        # 清理（这里设置0天，实际上不会删除刚插入的数据）
        success = self.extension_manager.cleanup_old_stats(days=0)
        self.assertTrue(success)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.duckdb_path = Path(self.temp_dir) / "test.db"
        self.sqlite_path = Path(self.temp_dir) / "test_sqlite.db"

        # 初始化所有组件
        self.connection_manager = DuckDBConnectionManager()
        self.table_manager = DynamicTableManager(self.connection_manager)
        self.operations = DuckDBOperations(self.connection_manager, self.table_manager)
        self.sqlite_manager = SQLiteExtensionManager(str(self.sqlite_path))

    def tearDown(self):
        """测试后清理"""
        cleanup_duckdb_manager()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        plugin_name = "integration_test_plugin"
        table_type = TableType.KLINE_DATA
        period = "1d"

        # 1. 创建表
        success = self.table_manager.create_table(
            str(self.duckdb_path), table_type, plugin_name, period
        )
        self.assertTrue(success)

        table_name = self.table_manager.generate_table_name(table_type, plugin_name, period)

        # 2. 记录表映射到SQLite
        mapping = PluginTableMapping(
            plugin_name=plugin_name,
            table_type=table_type.value,
            table_name=table_name,
            database_path=str(self.duckdb_path),
            period=period
        )

        success = self.sqlite_manager.add_table_mapping(mapping)
        self.assertTrue(success)

        # 3. 插入数据
        test_data = self._create_test_data(100)
        insert_result = self.operations.insert_dataframe(
            str(self.duckdb_path), table_name, test_data
        )
        self.assertTrue(insert_result.success)

        # 4. 记录性能统计
        perf_stat = PerformanceStatistic(
            plugin_name=plugin_name,
            table_name=table_name,
            operation_type="insert",
            execution_time=insert_result.execution_time,
            row_count=insert_result.rows_inserted,
            success=True
        )

        success = self.sqlite_manager.record_performance(perf_stat)
        self.assertTrue(success)

        # 5. 查询数据
        query_result = self.operations.query_data(str(self.duckdb_path), table_name)
        self.assertTrue(query_result.success)
        self.assertEqual(query_result.row_count, 100)

        # 6. 更新表映射统计
        success = self.sqlite_manager.update_table_mapping_stats(
            plugin_name, table_type.value, query_result.row_count, period
        )
        self.assertTrue(success)

        # 7. 验证完整性
        mappings = self.sqlite_manager.get_table_mappings(plugin_name=plugin_name)
        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].row_count, 100)

        stats = self.sqlite_manager.get_performance_stats(plugin_name=plugin_name)
        self.assertEqual(len(stats), 1)

    def _create_test_data(self, rows: int) -> pd.DataFrame:
        """创建测试数据"""
        data = []
        base_date = datetime(2024, 1, 1)

        for i in range(rows):
            data.append({
                'symbol': f'000{i % 10:03d}',
                'datetime': base_date.replace(day=1 + i % 28),
                'open': 10.0 + i * 0.1,
                'high': 10.5 + i * 0.1,
                'low': 9.5 + i * 0.1,
                'close': 10.2 + i * 0.1,
                'volume': 1000000 + i * 1000,
                'amount': 10000000.0 + i * 10000,
                'adj_close': 10.2 + i * 0.1,
                'adj_factor': 1.0,
                'vwap': 10.1 + i * 0.1,
                'bid_price': 10.0 + i * 0.1,
                'ask_price': 10.3 + i * 0.1,
                'bid_volume': 500000 + i * 500,
                'ask_volume': 500000 + i * 500,
                'rsi_14': 50.0 + (i % 50),
                'macd_dif': 0.1 + i * 0.01,
                'macd_dea': 0.05 + i * 0.005,
                'macd_histogram': 0.05 + i * 0.005,
                'kdj_k': 50.0 + (i % 50),
                'kdj_d': 50.0 + (i % 50),
                'kdj_j': 50.0 + (i % 50),
                'bollinger_upper': 11.0 + i * 0.1,
                'bollinger_middle': 10.0 + i * 0.1,
                'bollinger_lower': 9.0 + i * 0.1,
                'turnover_rate': 0.05 + (i % 10) * 0.01,
                'net_inflow_large': 1000000.0 + i * 10000,
                'net_inflow_medium': 500000.0 + i * 5000,
                'net_inflow_small': 100000.0 + i * 1000,
                'plugin_specific_data': '{}',
                'data_source': 'integration_test_plugin',
                'created_at': datetime.now(),
                'data_quality_score': 0.95
            })

        return pd.DataFrame(data)


if __name__ == '__main__':
    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加测试类
    test_suite.addTest(unittest.makeSuite(TestDuckDBConnectionManager))
    test_suite.addTest(unittest.makeSuite(TestDynamicTableManager))
    test_suite.addTest(unittest.makeSuite(TestDuckDBOperations))
    test_suite.addTest(unittest.makeSuite(TestSQLiteExtensions))
    test_suite.addTest(unittest.makeSuite(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试结果
    print(f"\n测试结果:")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
