"""
AssetSeparatedDatabaseManager 测试文件

测试资产分数据库管理器的各项功能
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import threading

from core.asset_database_manager import (
    AssetSeparatedDatabaseManager,
    AssetDatabaseConfig,
    get_asset_database_manager,
    initialize_asset_database_manager,
    cleanup_asset_database_manager
)
from core.plugin_types import AssetType


class TestAssetSeparatedDatabaseManager(unittest.TestCase):
    """AssetSeparatedDatabaseManager 测试类"""

    def setUp(self):
        """测试前准备"""
        print("\n" + "="*50)
        print("设置测试环境...")

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="asset_db_test_")
        print(f"临时目录: {self.temp_dir}")

        # 创建测试配置
        self.config = AssetDatabaseConfig(
            base_path=self.temp_dir,
            pool_size=2,
            auto_create=True,
            memory_limit="1GB"
        )

        # 初始化管理器
        self.manager = AssetSeparatedDatabaseManager(self.config)

    def tearDown(self):
        """测试后清理"""
        print("清理测试环境...")

        try:
            # 关闭所有连接
            self.manager.close_all_connections()

            # 删除临时目录
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("清理完成")

        except Exception as e:
            print(f"清理失败: {e}")

    def test_initialization(self):
        """测试初始化功能"""
        print("测试初始化功能")

        # 检查目录结构
        base_path = Path(self.temp_dir)
        self.assertTrue(base_path.exists())

        # 检查各资产类型目录是否创建
        for asset_type in AssetType:
            asset_dir = base_path / asset_type.value.lower()
            self.assertTrue(asset_dir.exists(), f"资产目录不存在: {asset_type.value}")

        print("初始化功能测试通过")

    def test_database_creation_by_asset_type(self):
        """测试按资产类型创建数据库"""
        print("测试按资产类型创建数据库")

        # 测试各种资产类型
        test_asset_types = [AssetType.STOCK_A, AssetType.CRYPTO, AssetType.FUTURES]

        for asset_type in test_asset_types:
            print(f"  测试资产类型: {asset_type.value}")

            # 获取数据库路径
            db_path = self.manager.get_database_for_asset_type(asset_type)
            self.assertTrue(Path(db_path).exists(), f"数据库文件不存在: {db_path}")

            # 测试数据库连接
            with self.manager.get_connection(asset_type) as conn:
                result = conn.execute("SELECT 1 as test").fetchone()
                self.assertEqual(result[0], 1)

                # 检查标准表是否存在
                tables_result = conn.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'main'
                """).fetchall()

                table_names = [row[0] for row in tables_result]
                expected_tables = ['historical_kline_data', 'data_source_records',
                                   'data_quality_monitor', 'metadata']

                for expected_table in expected_tables:
                    self.assertIn(expected_table, table_names,
                                  f"缺少表: {expected_table}")

        print("按资产类型创建数据库测试通过")

    def test_database_creation_by_symbol(self):
        """测试按交易符号创建数据库"""
        print("测试按交易符号创建数据库")

        test_symbols = [
            ("000001.SZ", AssetType.STOCK_A),
            ("AAPL.US", AssetType.STOCK_US),
            ("BTCUSDT", AssetType.CRYPTO),
            ("IF2401", AssetType.FUTURES)
        ]

        for symbol, expected_asset_type in test_symbols:
            print(f"  测试符号: {symbol} -> {expected_asset_type.value}")

            # 获取数据库路径和资产类型
            db_path, asset_type = self.manager.get_database_for_symbol(symbol)

            self.assertEqual(asset_type, expected_asset_type,
                             f"资产类型识别错误: {symbol}")
            self.assertTrue(Path(db_path).exists(), f"数据库文件不存在: {db_path}")

            # 测试连接
            with self.manager.get_connection_by_symbol(symbol) as conn:
                result = conn.execute("SELECT 1").fetchone()
                self.assertEqual(result[0], 1)

        print("按交易符号创建数据库测试通过")

    def test_data_insertion_and_query(self):
        """测试数据插入和查询"""
        print("测试数据插入和查询")

        # 测试数据
        test_data = [
            {
                'symbol': '000001.SZ',
                'data_source': 'tongdaxin',
                'timestamp': '2024-01-01 09:30:00',
                'open': 10.50,
                'high': 11.20,
                'low': 10.30,
                'close': 11.00,
                'volume': 1000000,
                'amount': 10500000.00,
                'frequency': '1d'
            },
            {
                'symbol': 'BTCUSDT',
                'data_source': 'binance',
                'timestamp': '2024-01-01 00:00:00',
                'open': 45000.50,
                'high': 46000.00,
                'low': 44500.00,
                'close': 45800.00,
                'volume': 100,
                'amount': 4580000.00,
                'frequency': '1d'
            }
        ]

        for data in test_data:
            print(f"  插入数据: {data['symbol']}")

            # 获取对应的连接
            with self.manager.get_connection_by_symbol(data['symbol']) as conn:
                # 插入数据
                conn.execute("""
                    INSERT INTO historical_kline_data 
                    (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    data['symbol'], data['data_source'], data['timestamp'],
                    data['open'], data['high'], data['low'], data['close'],
                    data['volume'], data['amount'], data['frequency']
                ])

                # 查询验证
                result = conn.execute("""
                    SELECT symbol, data_source, open, close, volume 
                    FROM historical_kline_data 
                    WHERE symbol = ?
                """, [data['symbol']]).fetchone()

                self.assertIsNotNone(result)
                self.assertEqual(result[0], data['symbol'])
                self.assertEqual(result[1], data['data_source'])
                self.assertEqual(float(result[2]), data['open'])
                self.assertEqual(float(result[3]), data['close'])
                self.assertEqual(result[4], data['volume'])

        print("数据插入和查询测试通过")

    def test_health_check(self):
        """测试健康检查功能"""
        print("测试健康检查功能")

        # 创建几个数据库
        test_asset_types = [AssetType.STOCK_A, AssetType.CRYPTO]

        for asset_type in test_asset_types:
            self.manager.get_database_for_asset_type(asset_type)

        # 执行健康检查
        health_results = self.manager.health_check_all()

        self.assertIsInstance(health_results, dict)
        self.assertGreater(len(health_results), 0)

        for asset_type_name, result in health_results.items():
            print(f"  {asset_type_name}: {result['status']}")
            self.assertIn('status', result)
            self.assertEqual(result['status'], 'healthy')
            self.assertIn('database_info', result)

        print("健康检查功能测试通过")

    def test_database_statistics(self):
        """测试数据库统计功能"""
        print("测试数据库统计功能")

        # 创建数据库并插入一些数据
        with self.manager.get_connection_by_symbol("000001.SZ") as conn:
            conn.execute("""
                INSERT INTO historical_kline_data 
                (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                VALUES ('000001.SZ', 'test', '2024-01-01', 10, 11, 9, 10.5, 1000, 10500, '1d')
            """)

        # 获取统计信息
        stats = self.manager.get_database_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_databases', stats)
        self.assertIn('total_size_mb', stats)
        self.assertIn('total_records', stats)
        self.assertIn('asset_breakdown', stats)

        print(f"  数据库总数: {stats['total_databases']}")
        print(f"  总大小: {stats['total_size_mb']:.2f} MB")
        print(f"  总记录数: {stats['total_records']}")

        self.assertGreater(stats['total_databases'], 0)

        print("数据库统计功能测试通过")

    def test_backup_and_restore(self):
        """测试备份和恢复功能"""
        print("测试备份和恢复功能")

        asset_type = AssetType.STOCK_A
        test_symbol = "000001.SZ"

        # 创建数据库并插入测试数据
        with self.manager.get_connection(asset_type) as conn:
            conn.execute("""
                INSERT INTO historical_kline_data 
                (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                VALUES (?, 'test', '2024-01-01', 10, 11, 9, 10.5, 1000, 10500, '1d')
            """, [test_symbol])

        # 备份数据库
        backup_path = self.manager.backup_database(asset_type)
        self.assertTrue(Path(backup_path).exists(), "备份文件不存在")
        print(f"  备份路径: {backup_path}")

        # 修改原数据
        with self.manager.get_connection(asset_type) as conn:
            conn.execute("DELETE FROM historical_kline_data WHERE symbol = ?", [test_symbol])

            # 验证数据已删除
            result = conn.execute(
                "SELECT COUNT(*) FROM historical_kline_data WHERE symbol = ?",
                [test_symbol]
            ).fetchone()
            self.assertEqual(result[0], 0)

        # 恢复数据库
        self.manager.restore_database(asset_type, backup_path, force=True)

        # 验证数据已恢复
        with self.manager.get_connection(asset_type) as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM historical_kline_data WHERE symbol = ?",
                [test_symbol]
            ).fetchone()
            self.assertEqual(result[0], 1)

        print("备份和恢复功能测试通过")

    def test_singleton_pattern(self):
        """测试单例模式"""
        print("测试单例模式")

        # 创建多个实例
        manager1 = get_asset_database_manager()
        manager2 = get_asset_database_manager()

        # 验证是同一个实例
        self.assertIs(manager1, manager2)

        print("单例模式测试通过")

    def test_thread_safety(self):
        """测试线程安全性"""
        print("测试线程安全性")

        results = []
        errors = []

        def worker_thread(thread_id):
            try:
                symbol = f"TEST{thread_id:03d}.SZ"

                # 获取连接并插入数据
                with self.manager.get_connection_by_symbol(symbol) as conn:
                    conn.execute("""
                        INSERT INTO historical_kline_data 
                        (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                        VALUES (?, 'test', '2024-01-01', ?, 11, 9, 10.5, 1000, 10500, '1d')
                    """, [symbol, 10 + thread_id])

                    # 查询验证
                    result = conn.execute(
                        "SELECT open FROM historical_kline_data WHERE symbol = ?",
                        [symbol]
                    ).fetchone()

                    results.append((thread_id, result[0] if result else None))

            except Exception as e:
                errors.append((thread_id, str(e)))

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        self.assertEqual(len(errors), 0, f"线程执行出错: {errors}")
        self.assertEqual(len(results), 5)

        for thread_id, open_price in results:
            self.assertEqual(open_price, 10 + thread_id)
            print(f"  线程 {thread_id}: 成功")

        print("线程安全性测试通过")


if __name__ == '__main__':
    print("开始 AssetSeparatedDatabaseManager 测试")
    print("="*50)

    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)

    print("\n" + "="*50)
    print("AssetSeparatedDatabaseManager 测试完成")
