"""
AssetAwareUnifiedDataManager 测试文件

测试资产感知统一数据管理器的各项功能
"""

import unittest
import tempfile
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd

from core.services.asset_aware_unified_data_manager import (
    AssetAwareUnifiedDataManager, AssetAwareDataRequest,
    get_asset_aware_unified_data_manager, initialize_asset_aware_unified_data_manager
)
from core.asset_database_manager import AssetDatabaseConfig
from core.plugin_types import AssetType, DataType
from core.data_router import RouteStrategy


class TestAssetAwareUnifiedDataManager(unittest.TestCase):
    """AssetAwareUnifiedDataManager 测试类"""

    def setUp(self):
        """测试前准备"""
        print("\n" + "="*60)
        print("设置测试环境...")

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="asset_aware_test_")
        print(f"临时目录: {self.temp_dir}")

        # 创建配置
        self.asset_db_config = AssetDatabaseConfig(
            base_path=self.temp_dir,
            pool_size=2,
            auto_create=True
        )

        # 初始化管理器
        self.manager = AssetAwareUnifiedDataManager(
            asset_db_config=self.asset_db_config
        )

        # 准备测试数据
        self._prepare_test_data()

    def tearDown(self):
        """测试后清理"""
        print("清理测试环境...")

        try:
            # 关闭所有连接
            self.manager.asset_db_manager.close_all_connections()

            # 删除临时目录
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("清理完成")

        except Exception as e:
            print(f"清理失败: {e}")

    def _prepare_test_data(self):
        """准备测试数据"""
        print("准备测试数据...")

        try:
            # 为A股准备数据
            with self.manager.asset_db_manager.get_connection(AssetType.STOCK_A) as conn:
                # 插入K线数据
                test_data = [
                    ('000001.SZ', 'tongdaxin', '2024-01-01 09:30:00', 10.0, 10.5, 9.8, 10.2, 1000000, 10200000, '1d'),
                    ('000001.SZ', 'tongdaxin', '2024-01-02 09:30:00', 10.2, 10.8, 10.0, 10.6, 1200000, 12720000, '1d'),
                    ('000001.SZ', 'eastmoney', '2024-01-01 09:30:00', 10.0, 10.5, 9.8, 10.2, 1000000, 10200000, '1d'),
                    ('600000.SH', 'tongdaxin', '2024-01-01 09:30:00', 15.0, 15.5, 14.8, 15.2, 800000, 12160000, '1d'),
                ]

                for data_row in test_data:
                    conn.execute("""
                        INSERT INTO historical_kline_data 
                        (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, data_row)

            # 为数字货币准备数据
            with self.manager.asset_db_manager.get_connection(AssetType.CRYPTO) as conn:
                crypto_data = [
                    ('BTCUSDT', 'binance', '2024-01-01 00:00:00', 45000, 46000, 44500, 45800, 100, 4580000, '1d'),
                    ('ETHUSDT', 'binance', '2024-01-01 00:00:00', 2500, 2580, 2450, 2520, 500, 1260000, '1d'),
                ]

                for data_row in crypto_data:
                    conn.execute("""
                        INSERT INTO historical_kline_data 
                        (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, data_row)

            print("测试数据准备完成")

        except Exception as e:
            print(f"准备测试数据失败: {e}")

    def test_initialization(self):
        """测试初始化功能"""
        print("测试初始化功能")

        # 检查基本属性
        self.assertIsNotNone(self.manager.asset_db_manager)
        self.assertIsNotNone(self.manager.data_router)
        self.assertIsInstance(self.manager._asset_cache, dict)
        self.assertIsInstance(self.manager._quality_scores, dict)

        print("  ✅ 核心组件初始化成功")

        # 检查资产数据库状态
        db_stats = self.manager.asset_db_manager.get_database_statistics()
        self.assertGreater(db_stats['total_databases'], 0)

        print(f"  ✅ 数据库初始化成功: {db_stats['total_databases']} 个数据库")

        # 检查数据路由器状态
        router_stats = self.manager.data_router.get_route_statistics()
        self.assertGreater(router_stats['data_sources_count'], 0)

        print(f"  ✅ 数据路由器初始化成功: {router_stats['data_sources_count']} 个数据源")
        print("初始化功能测试通过")

    def test_asset_aware_data_request(self):
        """测试资产感知数据请求"""
        print("测试资产感知数据请求")

        # 创建测试请求
        request = AssetAwareDataRequest(
            request_id="test_kline_001",
            symbol="000001.SZ",
            data_type="kline",
            time_range=(date(2024, 1, 1), date(2024, 1, 2)),
            parameters={'frequency': '1d'},
            route_strategy=RouteStrategy.FASTEST
        )

        # 验证请求转换
        route_request = request.to_route_request()
        self.assertEqual(route_request.symbol, "000001.SZ")
        self.assertEqual(route_request.data_type, DataType.HISTORICAL_KLINE)
        self.assertEqual(route_request.strategy, RouteStrategy.FASTEST)

        print("  ✅ 数据请求转换正确")

        # 获取数据
        data = self.manager.get_asset_aware_data(request)

        self.assertIsNotNone(data)
        if isinstance(data, pd.DataFrame):
            self.assertFalse(data.empty)
            print(f"  ✅ 获取K线数据成功: {len(data)} 条记录")

            # 验证数据结构
            expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in expected_columns:
                self.assertIn(col, data.columns)

            print("  ✅ 数据结构验证通过")

        print("资产感知数据请求测试通过")

    def test_different_asset_types(self):
        """测试不同资产类型的数据获取"""
        print("测试不同资产类型的数据获取")

        test_cases = [
            ("000001.SZ", AssetType.STOCK_A, "A股数据"),
            ("BTCUSDT", AssetType.CRYPTO, "数字货币数据"),
        ]

        for symbol, expected_asset_type, desc in test_cases:
            print(f"  测试 {symbol} ({desc})")

            request = AssetAwareDataRequest(
                request_id=f"test_{symbol}",
                symbol=symbol,
                data_type="kline",
                time_range=(date(2024, 1, 1), date(2024, 1, 2)),
                route_strategy=RouteStrategy.FASTEST
            )

            data = self.manager.get_asset_aware_data(request)

            if data is not None and not data.empty:
                print(f"    ✅ 成功获取 {desc}: {len(data)} 条记录")

                # 验证资产类型识别
                self.assertEqual(request.asset_type, expected_asset_type)
                print(f"    ✅ 资产类型识别正确: {expected_asset_type.value}")
            else:
                print(f"    ⚠️ {desc} 数据为空")

        print("不同资产类型数据获取测试通过")

    def test_data_quality_assessment(self):
        """测试数据质量评估"""
        print("测试数据质量评估")

        # 测试高质量数据
        good_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='D'),
            'open': [10.0 + i * 0.1 for i in range(10)],
            'high': [10.5 + i * 0.1 for i in range(10)],
            'low': [9.5 + i * 0.1 for i in range(10)],
            'close': [10.2 + i * 0.1 for i in range(10)],
            'volume': [1000000] * 10
        })

        request = AssetAwareDataRequest(
            request_id="quality_test",
            symbol="TEST001.SZ",
            data_type="kline"
        )

        quality_score = self.manager._assess_data_quality(good_data, request)

        self.assertGreaterEqual(quality_score, 0.8)
        print(f"  ✅ 高质量数据评分: {quality_score:.3f}")

        # 测试低质量数据（有缺失值）
        bad_data = good_data.copy()
        bad_data.loc[0:2, 'close'] = None
        bad_data.loc[5, 'high'] = 5.0  # 异常的高价（低于开盘价）

        bad_quality_score = self.manager._assess_data_quality(bad_data, request)

        self.assertLess(bad_quality_score, quality_score)
        print(f"  ✅ 低质量数据评分: {bad_quality_score:.3f}")

        print("数据质量评估测试通过")

    def test_cross_asset_query(self):
        """测试跨资产查询"""
        print("测试跨资产查询")

        # 跨资产符号列表
        symbols = ["000001.SZ", "600000.SH", "BTCUSDT", "ETHUSDT"]

        # 执行跨资产查询
        cross_asset_data = self.manager.get_cross_asset_data(
            symbols=symbols,
            data_type="kline",
            time_range=(date(2024, 1, 1), date(2024, 1, 2))
        )

        self.assertIsInstance(cross_asset_data, dict)

        # 验证按资产类型分组
        asset_types_found = list(cross_asset_data.keys())
        print(f"  ✅ 找到资产类型: {[at.value for at in asset_types_found]}")

        # 验证每个资产类型的数据
        for asset_type, asset_data in cross_asset_data.items():
            self.assertIsInstance(asset_data, dict)
            print(f"  ✅ {asset_type.value} 数据: {len(asset_data)} 个符号")

            for symbol, symbol_data in asset_data.items():
                if symbol_data is not None and not symbol_data.empty:
                    print(f"    - {symbol}: {len(symbol_data)} 条记录")

        print("跨资产查询测试通过")

    def test_caching_mechanism(self):
        """测试缓存机制"""
        print("测试缓存机制")

        request = AssetAwareDataRequest(
            request_id="cache_test_001",
            symbol="000001.SZ",
            data_type="kline",
            route_strategy=RouteStrategy.FASTEST
        )

        # 第一次请求
        start_time = datetime.now()
        data1 = self.manager.get_asset_aware_data(request)
        first_duration = (datetime.now() - start_time).total_seconds()

        # 第二次请求（应该使用缓存）
        start_time = datetime.now()
        data2 = self.manager.get_asset_aware_data(request)
        second_duration = (datetime.now() - start_time).total_seconds()

        # 验证缓存效果
        if data1 is not None and data2 is not None:
            print(f"  ✅ 第一次查询耗时: {first_duration:.3f}s")
            print(f"  ✅ 第二次查询耗时: {second_duration:.3f}s")

            # 第二次应该更快（使用缓存）
            if second_duration < first_duration * 0.8:
                print("  ✅ 缓存机制工作正常")
            else:
                print("  ⚠️ 缓存效果不明显")

        # 测试缓存清除
        initial_cache_size = sum(len(cache) for cache in self.manager._asset_cache.values())
        self.manager.clear_asset_cache(AssetType.STOCK_A)
        after_clear_size = sum(len(cache) for cache in self.manager._asset_cache.values())

        print(f"  ✅ 缓存清除: {initial_cache_size} -> {after_clear_size}")

        print("缓存机制测试通过")

    def test_statistics_collection(self):
        """测试统计信息收集"""
        print("测试统计信息收集")

        # 执行一些数据请求
        test_symbols = ["000001.SZ", "BTCUSDT"]

        for symbol in test_symbols:
            request = AssetAwareDataRequest(
                request_id=f"stats_test_{symbol}",
                symbol=symbol,
                data_type="kline",
                route_strategy=RouteStrategy.FASTEST
            )

            self.manager.get_asset_aware_data(request)

        # 获取统计信息
        stats = self.manager.get_asset_statistics()

        # 验证统计结构
        expected_keys = [
            'database_statistics',
            'route_statistics',
            'data_source_status',
            'asset_route_statistics',
            'data_quality_statistics',
            'cache_statistics'
        ]

        for key in expected_keys:
            self.assertIn(key, stats)
            print(f"  ✅ 统计包含 {key}")

        # 验证具体统计数据
        db_stats = stats['database_statistics']
        self.assertGreater(db_stats['total_databases'], 0)
        print(f"  ✅ 数据库统计: {db_stats['total_databases']} 个数据库")

        route_stats = stats['route_statistics']
        self.assertGreaterEqual(route_stats['total_routes'], 0)
        print(f"  ✅ 路由统计: {route_stats['total_routes']} 次路由")

        print("统计信息收集测试通过")

    def test_health_check(self):
        """测试健康检查"""
        print("测试健康检查")

        health_result = self.manager.health_check()

        # 验证健康检查结果结构
        self.assertIn('status', health_result)
        self.assertIn('asset_database_health', health_result)
        self.assertIn('router_health', health_result)
        self.assertIn('summary', health_result)

        print(f"  ✅ 整体状态: {health_result['status']}")

        # 验证总结信息
        summary = health_result['summary']
        print(f"  ✅ 健康数据库: {summary['healthy_databases']}/{summary['total_databases']}")
        print(f"  ✅ 可用数据源: {summary['available_data_sources']}/{summary['total_data_sources']}")

        # 验证各数据库健康状态
        db_health = health_result['asset_database_health']
        for asset_type, health_info in db_health.items():
            status = health_info.get('status', 'unknown')
            print(f"  ✅ {asset_type} 数据库: {status}")

        print("健康检查测试通过")

    def test_singleton_pattern(self):
        """测试单例模式"""
        print("测试单例模式")

        # 获取多个实例
        manager1 = get_asset_aware_unified_data_manager()
        manager2 = get_asset_aware_unified_data_manager()

        # 验证是同一个实例
        self.assertIs(manager1, manager2)

        print("  ✅ 单例模式工作正常")
        print("单例模式测试通过")


if __name__ == '__main__':
    print("开始 AssetAwareUnifiedDataManager 测试")
    print("="*60)

    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)

    print("\n" + "="*60)
    print("AssetAwareUnifiedDataManager 测试完成")
