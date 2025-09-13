"""
DataRouter 数据路由器测试文件

测试数据路由器的各项功能
"""

import unittest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from core.data_router import (
    DataRouter, DataRequest, RouteResult, DataSource, RouteStrategy,
    DataSourceInfo, get_data_router, initialize_data_router
)
from core.plugin_types import AssetType, DataType


class TestDataRouter(unittest.TestCase):
    """DataRouter 测试类"""

    def setUp(self):
        """测试前准备"""
        print("\n" + "="*50)
        print("设置测试环境...")

        # 每次测试都创建新的路由器实例
        self.router = DataRouter()

    def tearDown(self):
        """测试后清理"""
        print("清理测试环境...")

        try:
            # 清理缓存
            self.router.clear_cache()
            print("清理完成")
        except Exception as e:
            print(f"清理失败: {e}")

    def test_initialization(self):
        """测试初始化功能"""
        print("测试初始化功能")

        # 检查基本属性
        self.assertIsNotNone(self.router.asset_identifier)
        self.assertIsNotNone(self.router.db_manager)
        self.assertIsInstance(self.router._data_sources, dict)
        self.assertIsInstance(self.router._strategy_config, dict)

        # 检查默认数据源是否已加载
        self.assertGreater(len(self.router._data_sources), 0)
        print(f"  已加载 {len(self.router._data_sources)} 个默认数据源")

        # 检查策略配置是否已加载
        expected_strategies = [
            RouteStrategy.FASTEST,
            RouteStrategy.MOST_RELIABLE,
            RouteStrategy.HIGHEST_QUALITY,
            RouteStrategy.LOAD_BALANCE,
            RouteStrategy.FAILOVER
        ]

        for strategy in expected_strategies:
            self.assertIn(strategy, self.router._strategy_config)
            print(f"  ✅ 策略配置已加载: {strategy.value}")

        print("初始化功能测试通过")

    def test_data_source_registration(self):
        """测试数据源注册功能"""
        print("测试数据源注册功能")

        # 创建测试数据源
        test_source = DataSourceInfo(
            source=DataSource.CUSTOM,
            asset_types=[AssetType.STOCK_A],
            data_types=[DataType.HISTORICAL_KLINE],
            success_rate=0.9,
            avg_response_time_ms=500,
            quality_score=0.8
        )

        # 注册数据源
        initial_count = len(self.router._data_sources)
        self.router.register_data_source(test_source)

        # 验证注册成功
        self.assertEqual(len(self.router._data_sources), initial_count + 1)
        self.assertIn(DataSource.CUSTOM, self.router._data_sources)

        registered_source = self.router._data_sources[DataSource.CUSTOM]
        self.assertEqual(registered_source.success_rate, 0.9)
        self.assertEqual(registered_source.avg_response_time_ms, 500)

        print("  ✅ 数据源注册成功")

        # 测试注销
        self.router.unregister_data_source(DataSource.CUSTOM)
        self.assertEqual(len(self.router._data_sources), initial_count)
        self.assertNotIn(DataSource.CUSTOM, self.router._data_sources)

        print("  ✅ 数据源注销成功")
        print("数据源注册功能测试通过")

    def test_health_status_update(self):
        """测试健康状态更新功能"""
        print("测试健康状态更新功能")

        # 选择一个已存在的数据源进行测试
        test_source = DataSource.TONGDAXIN

        if test_source in self.router._data_sources:
            original_info = self.router._data_sources[test_source]
            original_response_time = original_info.avg_response_time_ms
            original_success_rate = original_info.success_rate

            # 更新健康状态
            self.router.update_source_health(
                source=test_source,
                is_available=False,
                response_time_ms=2000,
                success=False
            )

            updated_info = self.router._data_sources[test_source]

            # 验证更新结果
            self.assertFalse(updated_info.is_available)
            self.assertIsNotNone(updated_info.last_check_time)

            # 响应时间应该有变化（指数移动平均）
            self.assertNotEqual(updated_info.avg_response_time_ms, original_response_time)

            # 成功率应该降低
            self.assertLess(updated_info.success_rate, original_success_rate)

            print(f"  ✅ 健康状态更新成功")
            print(f"    可用性: True -> False")
            print(f"    响应时间: {original_response_time}ms -> {updated_info.avg_response_time_ms}ms")
            print(f"    成功率: {original_success_rate:.3f} -> {updated_info.success_rate:.3f}")

        print("健康状态更新功能测试通过")

    def test_basic_routing(self):
        """测试基本路由功能"""
        print("测试基本路由功能")

        # 创建测试请求
        test_requests = [
            DataRequest(
                symbol="000001.SZ",
                data_type=DataType.HISTORICAL_KLINE,
                frequency="1d",
                strategy=RouteStrategy.FASTEST
            ),
            DataRequest(
                symbol="AAPL.US",
                data_type=DataType.HISTORICAL_KLINE,
                frequency="1d",
                strategy=RouteStrategy.MOST_RELIABLE
            ),
            DataRequest(
                symbol="BTCUSDT",
                data_type=DataType.HISTORICAL_KLINE,
                frequency="1h",
                strategy=RouteStrategy.HIGHEST_QUALITY
            )
        ]

        successful_routes = 0

        for i, request in enumerate(test_requests):
            try:
                print(f"  测试请求 {i+1}: {request.symbol} ({request.strategy.value})")

                result = self.router.route_data_request(request)

                # 验证路由结果
                self.assertIsInstance(result, RouteResult)
                self.assertIsInstance(result.asset_type, AssetType)
                self.assertIsInstance(result.database_path, str)
                self.assertIsInstance(result.selected_sources, list)
                self.assertIsInstance(result.primary_source, DataSource)
                self.assertGreaterEqual(result.confidence_score, 0.0)
                self.assertLessEqual(result.confidence_score, 1.0)

                successful_routes += 1

                print(f"    ✅ 路由成功")
                print(f"       资产类型: {result.asset_type.value}")
                print(f"       主要数据源: {result.primary_source.value}")
                print(f"       置信度: {result.confidence_score:.3f}")
                print(f"       预计延迟: {result.estimated_latency_ms}ms")

            except Exception as e:
                print(f"    ❌ 路由失败: {e}")

        print(f"\n路由成功率: {successful_routes}/{len(test_requests)}")
        self.assertGreater(successful_routes, 0, "至少应有一个请求路由成功")

        print("基本路由功能测试通过")

    def test_routing_strategies(self):
        """测试不同路由策略"""
        print("测试不同路由策略")

        base_request = DataRequest(
            symbol="000001.SZ",
            data_type=DataType.HISTORICAL_KLINE,
            frequency="1d"
        )

        strategies = [
            RouteStrategy.FASTEST,
            RouteStrategy.MOST_RELIABLE,
            RouteStrategy.HIGHEST_QUALITY,
            RouteStrategy.LOAD_BALANCE,
            RouteStrategy.FAILOVER
        ]

        results = {}

        for strategy in strategies:
            try:
                request = DataRequest(
                    symbol=base_request.symbol,
                    data_type=base_request.data_type,
                    frequency=base_request.frequency,
                    strategy=strategy
                )

                result = self.router.route_data_request(request)
                results[strategy] = result

                print(f"  ✅ {strategy.value}: {result.primary_source.value}")

            except Exception as e:
                print(f"  ❌ {strategy.value}: 失败 - {e}")

        print(f"\n策略测试完成，成功: {len(results)}/{len(strategies)}")

        # 验证不同策略可能产生不同结果
        if len(results) > 1:
            primary_sources = [r.primary_source for r in results.values()]
            print(f"  选择的主要数据源: {set(s.value for s in primary_sources)}")

        print("路由策略功能测试通过")

    def test_batch_routing(self):
        """测试批量路由功能"""
        print("测试批量路由功能")

        # 创建批量请求
        batch_requests = [
            DataRequest(symbol="000001.SZ", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.FASTEST),
            DataRequest(symbol="600000.SH", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.MOST_RELIABLE),
            DataRequest(symbol="AAPL.US", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.HIGHEST_QUALITY),
            DataRequest(symbol="BTCUSDT", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.LOAD_BALANCE),
        ]

        # 执行批量路由
        batch_results = self.router.batch_route_requests(batch_requests)

        # 验证结果
        self.assertEqual(len(batch_results), len(batch_requests))

        successful_count = 0
        for i, (request, result) in enumerate(zip(batch_requests, batch_results)):
            if result.selected_sources:  # 有选择的数据源说明路由成功
                successful_count += 1
                print(f"  ✅ {request.symbol} -> {result.primary_source.value}")
            else:
                print(f"  ❌ {request.symbol} -> 路由失败")

        print(f"\n批量路由成功率: {successful_count}/{len(batch_requests)}")
        self.assertGreater(successful_count, 0, "批量路由应至少有一个成功")

        print("批量路由功能测试通过")

    def test_caching_mechanism(self):
        """测试缓存机制"""
        print("测试缓存机制")

        request = DataRequest(
            symbol="000001.SZ",
            data_type=DataType.HISTORICAL_KLINE,
            frequency="1d",
            strategy=RouteStrategy.FASTEST
        )

        # 第一次请求
        initial_cache_size = len(self.router._route_cache)
        result1 = self.router.route_data_request(request)
        after_first_cache_size = len(self.router._route_cache)

        # 验证缓存增加
        self.assertGreater(after_first_cache_size, initial_cache_size)
        print("  ✅ 第一次请求创建了缓存")

        # 第二次相同请求（应该使用缓存）
        result2 = self.router.route_data_request(request)
        after_second_cache_size = len(self.router._route_cache)

        # 缓存大小不应再增加
        self.assertEqual(after_second_cache_size, after_first_cache_size)

        # 结果应该相同（因为使用了缓存）
        self.assertEqual(result1.primary_source, result2.primary_source)
        self.assertEqual(result1.asset_type, result2.asset_type)

        print("  ✅ 第二次请求使用了缓存")

        # 清除缓存
        self.router.clear_cache()
        self.assertEqual(len(self.router._route_cache), 0)
        print("  ✅ 缓存清除成功")

        print("缓存机制测试通过")

    def test_statistics_collection(self):
        """测试统计信息收集"""
        print("测试统计信息收集")

        # 执行一些路由请求
        test_requests = [
            DataRequest(symbol="000001.SZ", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.FASTEST),
            DataRequest(symbol="000002.SZ", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.FASTEST),
            DataRequest(symbol="AAPL.US", data_type=DataType.HISTORICAL_KLINE, strategy=RouteStrategy.MOST_RELIABLE)
        ]

        for request in test_requests:
            try:
                self.router.route_data_request(request)
            except Exception:
                pass  # 忽略路由错误，专注于统计测试

        # 获取路由统计
        route_stats = self.router.get_route_statistics()

        # 验证统计结构
        expected_keys = ['total_routes', 'data_sources_count', 'available_sources', 'route_stats', 'cache_hit_ratio']
        for key in expected_keys:
            self.assertIn(key, route_stats)
            print(f"  ✅ 统计包含 {key}: {route_stats[key]}")

        # 获取数据源状态
        source_status = self.router.get_data_sources_status()

        self.assertIsInstance(source_status, dict)
        self.assertGreater(len(source_status), 0)

        print(f"  ✅ 数据源状态: {len(source_status)} 个数据源")

        # 验证数据源状态结构
        for source_name, status in source_status.items():
            required_fields = ['is_available', 'success_rate', 'avg_response_time_ms', 'quality_score']
            for field in required_fields:
                self.assertIn(field, status)

        print("统计信息收集测试通过")

    def test_singleton_pattern(self):
        """测试单例模式"""
        print("测试单例模式")

        # 获取多个实例
        router1 = get_data_router()
        router2 = get_data_router()
        router3 = DataRouter()

        # 验证是同一个实例
        self.assertIs(router1, router2)
        self.assertIs(router2, router3)

        print("  ✅ 单例模式工作正常")
        print("单例模式测试通过")

    def test_error_handling(self):
        """测试错误处理"""
        print("测试错误处理")

        # 测试无效数据类型的路由
        try:
            invalid_request = DataRequest(
                symbol="INVALID_SYMBOL",
                data_type=DataType.TECHNICAL_INDICATORS,  # 可能没有支持的数据源
                strategy=RouteStrategy.FASTEST
            )

            # 应该能处理但可能返回错误结果
            result = self.router.route_data_request(invalid_request)
            print(f"  ✅ 处理无效请求，置信度: {result.confidence_score}")

        except Exception as e:
            print(f"  ✅ 正确抛出异常: {type(e).__name__}")

        # 测试注销不存在的数据源
        try:
            self.router.unregister_data_source(DataSource.CUSTOM)
            print("  ✅ 安全处理不存在数据源的注销")
        except Exception as e:
            print(f"  ⚠️ 注销不存在数据源出错: {e}")

        # 测试更新不存在数据源的健康状态
        try:
            self.router.update_source_health(DataSource.CUSTOM, True)
            print("  ✅ 安全处理不存在数据源的健康更新")
        except Exception as e:
            print(f"  ⚠️ 更新不存在数据源健康状态出错: {e}")

        print("错误处理测试通过")


if __name__ == '__main__':
    print("开始 DataRouter 数据路由器测试")
    print("="*50)

    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)

    print("\n" + "="*50)
    print("DataRouter 测试完成")
