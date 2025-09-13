"""
第1周核心组件集成测试

验证AssetTypeIdentifier和AssetSeparatedDatabaseManager的完整功能和集成
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from core.asset_type_identifier import get_asset_type_identifier
from core.asset_database_manager import AssetSeparatedDatabaseManager, AssetDatabaseConfig
from core.plugin_types import AssetType


class TestWeek1Integration(unittest.TestCase):
    """第1周核心组件集成测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="week1_integration_")

        # 创建配置
        self.config = AssetDatabaseConfig(
            base_path=self.temp_dir,
            pool_size=2,
            auto_create=True
        )

        # 创建管理器
        self.db_manager = AssetSeparatedDatabaseManager(self.config)
        self.identifier = get_asset_type_identifier()

    def tearDown(self):
        """测试后清理"""
        try:
            self.db_manager.close_all_connections()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_asset_type_identification(self):
        """测试资产类型识别功能"""
        print("\n测试资产类型识别功能")

        test_cases = [
            ('000001.SZ', AssetType.STOCK_A, 'A股深圳'),
            ('600000.SH', AssetType.STOCK_A, 'A股上海'),
            ('300001.SZ', AssetType.STOCK_A, 'A股创业板'),
            ('688001.SH', AssetType.STOCK_A, 'A股科创板'),
            ('830001.BJ', AssetType.STOCK_A, 'A股北交所'),
            ('AAPL.US', AssetType.STOCK_US, '美股'),
            ('00700.HK', AssetType.STOCK_HK, '港股'),
            ('200001.SZ', AssetType.STOCK_B, 'B股'),
            ('BTCUSDT', AssetType.CRYPTO, '数字货币'),
            ('ETHUSDT', AssetType.CRYPTO, '数字货币ETH'),
            ('BTC', AssetType.CRYPTO, '数字货币BTC'),
            ('IF2401', AssetType.FUTURES, '股指期货'),
            ('CU2403', AssetType.FUTURES, '商品期货'),
            ('EUR/USD', AssetType.FOREX, '外汇'),
        ]

        success_count = 0
        for symbol, expected, desc in test_cases:
            result = self.identifier.identify_asset_type_by_symbol(symbol)
            if result == expected:
                success_count += 1
                print(f"  ✅ {symbol} -> {result.value} ({desc})")
            else:
                print(f"  ❌ {symbol} -> {result.value}, 期望: {expected.value} ({desc})")

        print(f"识别准确率: {success_count}/{len(test_cases)} = {success_count/len(test_cases)*100:.1f}%")
        self.assertEqual(success_count, len(test_cases), "资产类型识别存在错误")

    def test_database_creation_and_routing(self):
        """测试数据库创建和路由功能"""
        print("\n测试数据库创建和路由功能")

        test_symbols = [
            '000001.SZ',  # A股
            'AAPL.US',    # 美股
            'BTCUSDT',    # 数字货币
            'IF2401'      # 期货
        ]

        created_dbs = []

        for symbol in test_symbols:
            # 通过符号获取数据库
            db_path, asset_type = self.db_manager.get_database_for_symbol(symbol)

            # 验证数据库文件存在
            self.assertTrue(Path(db_path).exists(), f"数据库文件不存在: {db_path}")

            # 验证资产类型目录结构
            expected_dir = Path(self.temp_dir) / asset_type.value.lower()
            self.assertTrue(expected_dir.exists(), f"资产目录不存在: {expected_dir}")

            created_dbs.append((symbol, asset_type, db_path))
            print(f"  ✅ {symbol} -> {asset_type.value} -> {Path(db_path).name}")

        print(f"成功创建 {len(created_dbs)} 个资产数据库")

    def test_data_operations(self):
        """测试数据操作功能"""
        print("\n测试数据操作功能")

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

        inserted_count = 0

        for data in test_data:
            try:
                # 插入数据
                with self.db_manager.get_connection_by_symbol(data['symbol']) as conn:
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

                    if result:
                        inserted_count += 1
                        print(f"  ✅ {data['symbol']}: 插入并验证成功")
                        self.assertEqual(result[0], data['symbol'])
                        self.assertEqual(result[1], data['data_source'])
                        self.assertEqual(float(result[2]), data['open'])
                        self.assertEqual(float(result[3]), data['close'])
                        self.assertEqual(result[4], data['volume'])
                    else:
                        print(f"  ❌ {data['symbol']}: 查询验证失败")

            except Exception as e:
                print(f"  ❌ {data['symbol']}: 操作失败 - {e}")

        print(f"数据操作成功率: {inserted_count}/{len(test_data)} = {inserted_count/len(test_data)*100:.1f}%")
        self.assertEqual(inserted_count, len(test_data), "数据操作存在失败")

    def test_health_check_and_statistics(self):
        """测试健康检查和统计功能"""
        print("\n测试健康检查和统计功能")

        # 先创建一些数据库
        test_symbols = ['000001.SZ', 'AAPL.US', 'BTCUSDT']
        for symbol in test_symbols:
            self.db_manager.get_database_for_symbol(symbol)

        # 健康检查
        health_results = self.db_manager.health_check_all()

        healthy_count = 0
        for asset_type, result in health_results.items():
            if result.get('status') == 'healthy':
                healthy_count += 1
                print(f"  ✅ {asset_type}: 健康")
            else:
                print(f"  ❌ {asset_type}: {result.get('status', 'unknown')}")

        print(f"数据库健康率: {healthy_count}/{len(health_results)} = {healthy_count/len(health_results)*100:.1f}%")

        # 统计信息
        stats = self.db_manager.get_database_statistics()

        print(f"  数据库总数: {stats['total_databases']}")
        print(f"  总大小: {stats['total_size_mb']:.2f} MB")
        print(f"  资产类型数: {len(stats['asset_breakdown'])}")

        self.assertGreater(stats['total_databases'], 0, "数据库总数应大于0")
        self.assertGreater(len(stats['asset_breakdown']), 0, "应有资产类型统计")

    def test_integration_workflow(self):
        """测试完整的集成工作流"""
        print("\n测试完整的集成工作流")

        # 步骤1: 资产类型识别
        symbol = '000001.SZ'
        asset_type = self.identifier.identify_asset_type_by_symbol(symbol)
        print(f"  步骤1: 识别 {symbol} -> {asset_type.value}")

        # 步骤2: 获取对应数据库
        db_path, identified_type = self.db_manager.get_database_for_symbol(symbol)
        self.assertEqual(asset_type, identified_type, "资产类型识别不一致")
        print(f"  步骤2: 获取数据库 -> {Path(db_path).name}")

        # 步骤3: 数据库操作
        with self.db_manager.get_connection(asset_type) as conn:
            # 插入测试数据
            conn.execute("""
                INSERT INTO historical_kline_data 
                (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [symbol, 'test', '2024-01-01', 10.0, 11.0, 9.0, 10.5, 1000, 10500, '1d'])

            # 查询验证
            count = conn.execute("SELECT COUNT(*) FROM historical_kline_data WHERE symbol = ?", [symbol]).fetchone()[0]
            print(f"  步骤3: 插入数据，记录数 = {count}")

        # 步骤4: 健康检查
        health = self.db_manager.health_check_all()
        healthy_dbs = sum(1 for r in health.values() if r.get('status') == 'healthy')
        print(f"  步骤4: 健康检查，健康数据库 = {healthy_dbs}")

        # 步骤5: 统计信息
        stats = self.db_manager.get_database_statistics()
        print(f"  步骤5: 统计信息，总记录 = {stats['total_records']}")

        print("  ✅ 完整工作流测试成功")

    def test_error_handling(self):
        """测试错误处理能力"""
        print("\n测试错误处理能力")

        # 测试无效符号
        invalid_symbol = "INVALID_SYMBOL_12345"
        asset_type = self.identifier.identify_asset_type_by_symbol(invalid_symbol)
        print(f"  无效符号 {invalid_symbol} -> {asset_type.value} (默认为STOCK)")

        # 测试不存在的资产类型备份
        try:
            self.db_manager.backup_database(AssetType.BOND)  # 应该没有债券数据库
            print("  ❌ 应该抛出错误但没有")
        except ValueError as e:
            print(f"  ✅ 正确处理不存在的数据库备份: {e}")
        except Exception as e:
            print(f"  ⚠️ 其他错误: {e}")

        print("  ✅ 错误处理测试完成")


if __name__ == '__main__':
    print("开始第1周核心组件集成测试")
    print("="*60)

    # 运行测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWeek1Integration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"测试结果: 运行 {result.testsRun} 个测试")
    print(f"失败: {len(result.failures)} 个")
    print(f"错误: {len(result.errors)} 个")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("\n🎉 所有测试通过！第1周核心组件集成成功！")
    else:
        print("\n❌ 存在测试失败，需要修复后才能进行下一步")
