#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SECTOR资产类型支持情况
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_sector_support():
    """测试SECTOR资产类型支持情况"""
    print("HIkyuu-UI SECTOR资产类型支持测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. 初始化日志系统
        from core.loguru_config import initialize_loguru
        initialize_loguru()

        # 2. 引导服务
        from core.services.service_bootstrap import bootstrap_services
        bootstrap_services()

        # 3. 获取数据管理器
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.services.unified_data_manager import UnifiedDataManager

        container = UnifiedServiceContainer()
        data_manager = container.resolve(UnifiedDataManager)
        router = data_manager.tet_pipeline.router

        # 4. 检查资产类型枚举
        print("🔍 步骤 1: 检查资产类型枚举...")
        from core.data_source_extensions import AssetType, DataType

        print(f"   AssetType.SECTOR 值: {AssetType.SECTOR}")
        print(f"   AssetType.SECTOR 名称: {AssetType.SECTOR.value}")
        print(f"   DataType.SECTOR_FUND_FLOW 值: {DataType.SECTOR_FUND_FLOW}")
        print(f"   DataType.SECTOR_FUND_FLOW 名称: {DataType.SECTOR_FUND_FLOW.value}")

        # 5. 创建路由请求
        print("\n🗺️ 步骤 2: 创建SECTOR路由请求...")
        from core.data_source_extensions import RoutingRequest

        routing_request = RoutingRequest(
            asset_type=AssetType.SECTOR,
            data_type=DataType.SECTOR_FUND_FLOW,
            symbol="sector",
            priority=0,
            timeout_ms=5000
        )

        print(f"   路由请求创建成功: {routing_request}")

        # 6. 获取支持SECTOR的数据源
        print("\n📋 步骤 3: 检查支持SECTOR的数据源...")
        available_sources = router.get_available_sources(routing_request)
        print(f"   支持SECTOR的数据源: {available_sources}")

        if not available_sources:
            print("❌ 没有数据源支持SECTOR资产类型")

            # 详细检查每个数据源
            print("\n🔍 详细检查每个数据源:")
            for source_id, adapter in router.data_sources.items():
                try:
                    plugin_info = adapter.get_plugin_info()
                    supported_types = plugin_info.supported_asset_types
                    print(f"   - {source_id}:")
                    print(f"     支持的资产类型: {[t.value for t in supported_types]}")
                    print(f"     是否支持SECTOR: {AssetType.SECTOR in supported_types}")

                    # 检查是否有板块资金流相关方法
                    if hasattr(adapter, 'plugin') and hasattr(adapter.plugin, 'get_sector_fund_flow_data'):
                        print(f"     有get_sector_fund_flow_data方法: ✅")
                    else:
                        print(f"     有get_sector_fund_flow_data方法: ❌")

                except Exception as e:
                    print(f"   - {source_id}: 检查失败 - {e}")
        else:
            print("✅ 找到支持SECTOR资产类型的数据源")

            # 测试每个支持的数据源
            for source_id in available_sources:
                print(f"\n🧪 测试数据源: {source_id}")
                try:
                    adapter = router.data_sources[source_id]
                    if hasattr(adapter, 'plugin') and hasattr(adapter.plugin, 'get_sector_fund_flow_data'):
                        print(f"   ✅ 支持板块资金流数据获取")

                        # 尝试获取数据
                        try:
                            result = adapter.plugin.get_sector_fund_flow_data()
                            print(f"   数据获取结果: {type(result)} - {len(result) if hasattr(result, '__len__') else 'N/A'}")
                        except Exception as e:
                            print(f"   数据获取失败: {e}")
                    else:
                        print(f"   ❌ 不支持板块资金流数据获取")

                except Exception as e:
                    print(f"   测试失败: {e}")

        # 7. 测试TET数据管道
        print("\n🧪 步骤 4: 测试TET数据管道...")
        from core.data_source_extensions import DataQuery

        query = DataQuery(
            symbol="sector",
            asset_type=AssetType.SECTOR,
            data_type=DataType.SECTOR_FUND_FLOW,
            start_date=None,
            end_date=None
        )

        try:
            result_data, provider_info, failover_result = data_manager.tet_pipeline.process(query)

            if failover_result and failover_result.success:
                print("✅ TET数据管道测试成功")
                print(f"   数据条数: {len(result_data) if result_data is not None else 0}")
                print(f"   数据源: {failover_result.successful_source}")
            else:
                print("❌ TET数据管道测试失败")
                if failover_result:
                    print(f"   错误信息: {failover_result.error_messages}")
                    print(f"   尝试次数: {failover_result.attempts}")
                    print(f"   失败的数据源: {failover_result.failed_sources}")

        except Exception as e:
            print(f"❌ TET数据管道测试异常: {e}")
            import traceback
            traceback.print_exc()

        print("\n🎯 测试完成！")
        return True

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_sector_support()
    if success:
        print("\n✅ SECTOR资产类型支持测试完成")
    else:
        print("\n❌ SECTOR资产类型支持测试失败")

    sys.exit(0 if success else 1)
