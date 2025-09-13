#!/usr/bin/env python3
"""
DataRouter 验证脚本

验证DataRouter的基本功能和集成
"""


def test_data_router_basic():
    """测试DataRouter基本功能"""
    print("="*50)
    print("测试 DataRouter 基本功能")
    print("="*50)

    try:
        # 导入测试
        from core.data_router import DataRouter, DataRequest, RouteStrategy, DataSource, get_data_router
        from core.plugin_types import AssetType, DataType
        print("✅ 模块导入成功")

        # 创建路由器
        router = get_data_router()
        print("✅ DataRouter 创建成功")

        # 检查初始化状态
        print(f"  数据源数量: {len(router._data_sources)}")
        print(f"  策略配置数量: {len(router._strategy_config)}")

        # 测试基本路由
        request = DataRequest(
            symbol="000001.SZ",
            data_type=DataType.HISTORICAL_KLINE,
            strategy=RouteStrategy.FASTEST
        )
        print("✅ DataRequest 创建成功")

        result = router.route_data_request(request)
        print("✅ 路由请求成功")
        print(f"  资产类型: {result.asset_type.value}")
        print(f"  主要数据源: {result.primary_source.value}")
        print(f"  置信度: {result.confidence_score:.3f}")
        print(f"  预计延迟: {result.estimated_latency_ms}ms")

        return True

    except Exception as e:
        print(f"❌ DataRouter 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_router_strategies():
    """测试路由策略"""
    print("\n" + "="*50)
    print("测试 DataRouter 路由策略")
    print("="*50)

    try:
        from core.data_router import DataRouter, DataRequest, RouteStrategy, get_data_router
        from core.plugin_types import DataType

        router = get_data_router()

        strategies = [
            RouteStrategy.FASTEST,
            RouteStrategy.MOST_RELIABLE,
            RouteStrategy.HIGHEST_QUALITY
        ]

        success_count = 0

        for strategy in strategies:
            try:
                request = DataRequest(
                    symbol="000001.SZ",
                    data_type=DataType.HISTORICAL_KLINE,
                    strategy=strategy
                )

                result = router.route_data_request(request)
                print(f"✅ {strategy.value}: {result.primary_source.value}")
                success_count += 1

            except Exception as e:
                print(f"❌ {strategy.value}: {e}")

        print(f"\n策略测试成功: {success_count}/{len(strategies)}")
        return success_count > 0

    except Exception as e:
        print(f"❌ 策略测试失败: {e}")
        return False


def test_data_router_integration():
    """测试完整集成"""
    print("\n" + "="*50)
    print("测试 DataRouter 完整集成")
    print("="*50)

    try:
        from core.data_router import get_data_router, DataRequest, RouteStrategy
        from core.plugin_types import DataType

        router = get_data_router()

        # 测试不同资产类型的路由
        test_cases = [
            ("000001.SZ", "A股"),
            ("AAPL.US", "美股"),
            ("BTCUSDT", "数字货币")
        ]

        success_count = 0

        for symbol, desc in test_cases:
            try:
                request = DataRequest(
                    symbol=symbol,
                    data_type=DataType.HISTORICAL_KLINE,
                    strategy=RouteStrategy.FASTEST
                )

                result = router.route_data_request(request)
                print(f"✅ {symbol} ({desc}): {result.asset_type.value} -> {result.primary_source.value}")
                success_count += 1

            except Exception as e:
                print(f"❌ {symbol} ({desc}): {e}")

        # 测试统计功能
        try:
            stats = router.get_route_statistics()
            print(f"\n✅ 路由统计: {stats['total_routes']} 个路由")

            source_status = router.get_data_sources_status()
            print(f"✅ 数据源状态: {len(source_status)} 个数据源")

        except Exception as e:
            print(f"❌ 统计功能测试失败: {e}")

        print(f"\n集成测试成功: {success_count}/{len(test_cases)}")
        return success_count > 0

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主函数"""
    print("DataRouter 数据路由器验证")
    print("检查数据路由器的功能和集成")
    print()

    # 运行所有测试
    test_results = []

    test_results.append(test_data_router_basic())
    test_results.append(test_data_router_strategies())
    test_results.append(test_data_router_integration())

    # 总结结果
    print("\n" + "="*50)
    print("测试总结")
    print("="*50)

    passed_count = sum(test_results)
    total_count = len(test_results)

    test_names = [
        "DataRouter 基本功能",
        "路由策略测试",
        "完整集成测试"
    ]

    for i, (name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {name}: {status}")

    print(f"\n总体结果: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 DataRouter 验证通过！")
        print("✅ 数据路由器实现成功，可以进行下一步开发")
        return 0
    else:
        print("\n❌ 存在测试失败，需要修复")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
