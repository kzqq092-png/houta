#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块资金流数据源诊断脚本
全面分析为什么TET框架找不到可用的数据源
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def diagnose_sector_data_sources():
    """诊断板块资金流数据源问题"""
    print("HIkyuu-UI 板块资金流数据源诊断")
    print("=" * 60)
    print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. 初始化日志系统
        print("📝 步骤 1: 初始化日志系统...")
        from core.loguru_config import initialize_loguru
        initialize_loguru()

        # 2. 引导服务
        print("🚀 步骤 2: 引导服务...")
        from core.services.service_bootstrap import bootstrap_services
        bootstrap_success = bootstrap_services()
        if not bootstrap_success:
            print("❌ 服务引导失败")
            return False

        # 3. 获取服务容器和数据管理器
        print("📦 步骤 3: 获取服务容器和数据管理器...")
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.services.unified_data_manager import UnifiedDataManager

        container = UnifiedServiceContainer()
        data_manager = container.resolve(UnifiedDataManager)

        if not data_manager:
            print("❌ 无法获取UnifiedDataManager")
            return False

        print("✅ UnifiedDataManager获取成功")

        # 4. 检查TET数据管道
        print("\n🔍 步骤 4: 检查TET数据管道...")
        tet_pipeline = data_manager.tet_pipeline
        if not tet_pipeline:
            print("❌ TET数据管道不可用")
            return False

        print("✅ TET数据管道可用")

        # 5. 检查数据源路由器
        print("\n🗺️ 步骤 5: 检查数据源路由器...")
        router = tet_pipeline.router
        if not router:
            print("❌ 数据源路由器不可用")
            return False

        print("✅ 数据源路由器可用")

        # 6. 检查注册的数据源
        print("\n📋 步骤 6: 检查注册的数据源...")
        print(f"   注册的数据源总数: {len(router.data_sources)}")

        for source_id, adapter in router.data_sources.items():
            print(f"   - {source_id}: {type(adapter).__name__}")

        # 7. 检查SECTOR资产类型支持
        print("\n🏢 步骤 7: 检查SECTOR资产类型支持...")
        from core.data_source_extensions import AssetType

        # 创建SECTOR类型的路由请求
        from core.data_source_extensions import RoutingRequest, DataType
        routing_request = RoutingRequest(
            asset_type=AssetType.SECTOR,
            data_type=DataType.SECTOR_FUND_FLOW,
            symbol="sector",
            priority=0,
            timeout_ms=5000
        )

        # 获取支持SECTOR的数据源
        available_sources = router.get_available_sources(routing_request)
        print(f"   支持SECTOR资产类型的数据源: {available_sources}")

        if not available_sources:
            print("❌ 没有数据源支持SECTOR资产类型")

            # 详细检查每个数据源
            print("\n🔍 详细检查每个数据源的支持情况:")
            for source_id, adapter in router.data_sources.items():
                try:
                    plugin_info = adapter.get_plugin_info()
                    supported_types = plugin_info.supported_asset_types
                    print(f"   - {source_id}:")
                    print(f"     支持的资产类型: {[t.value for t in supported_types]}")
                    print(f"     是否支持SECTOR: {AssetType.SECTOR in supported_types}")
                except Exception as e:
                    print(f"   - {source_id}: 获取插件信息失败 - {e}")
        else:
            print("✅ 找到支持SECTOR资产类型的数据源")

        # 8. 检查板块资金流服务
        print("\n💰 步骤 8: 检查板块资金流服务...")
        try:
            from core.services.sector_fund_flow_service import SectorFundFlowService
            sector_service = container.resolve(SectorFundFlowService)

            if sector_service:
                print("✅ 板块资金流服务可用")

                # 检查服务的数据源信息
                sources_info = sector_service.get_available_sources_info()
                print(f"   可用数据源: {sources_info.get('available_sources', {})}")
                print(f"   最优数据源: {sources_info.get('optimal_sources', [])}")
                print(f"   当前数据源: {sources_info.get('current_source', 'unknown')}")
            else:
                print("❌ 板块资金流服务不可用")

        except Exception as e:
            print(f"❌ 板块资金流服务检查失败: {e}")

        # 9. 检查插件状态
        print("\n🔌 步骤 9: 检查相关插件状态...")
        try:
            from core.plugin_manager import PluginManager
            plugin_manager = container.resolve(PluginManager)

            if plugin_manager:
                print("✅ 插件管理器可用")

                # 检查数据源插件
                data_source_plugins = []
                for plugin_name, plugin_instance in plugin_manager.plugins.items():
                    if hasattr(plugin_instance, 'get_sector_fund_flow_data'):
                        data_source_plugins.append(plugin_name)
                        print(f"   - {plugin_name}: 支持板块资金流数据")

                if not data_source_plugins:
                    print("⚠️ 没有插件支持板块资金流数据")
            else:
                print("❌ 插件管理器不可用")

        except Exception as e:
            print(f"❌ 插件状态检查失败: {e}")

        # 10. 测试实际数据获取
        print("\n🧪 步骤 10: 测试实际数据获取...")
        try:
            # 尝试通过TET框架获取板块资金流数据
            from core.data_source_extensions import DataQuery

            query = DataQuery(
                symbol="sector",
                asset_type=AssetType.SECTOR,
                data_type=DataType.SECTOR_FUND_FLOW,
                start_date=None,
                end_date=None
            )

            result_data, provider_info, failover_result = tet_pipeline.process(query)

            if failover_result and failover_result.success:
                print("✅ TET框架数据获取成功")
                print(f"   数据条数: {len(result_data) if result_data is not None else 0}")
                print(f"   数据源: {failover_result.successful_source}")
            else:
                print("❌ TET框架数据获取失败")
                if failover_result:
                    print(f"   错误信息: {failover_result.error_messages}")
                    print(f"   尝试次数: {failover_result.attempts}")
                    print(f"   失败的数据源: {failover_result.failed_sources}")

        except Exception as e:
            print(f"❌ 数据获取测试失败: {e}")
            import traceback
            traceback.print_exc()

        print("\n🎯 诊断完成！")
        return True

    except Exception as e:
        print(f"❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = diagnose_sector_data_sources()
    if success:
        print("\n✅ 板块资金流数据源诊断完成")
    else:
        print("\n❌ 板块资金流数据源诊断失败")

    sys.exit(0 if success else 1)
