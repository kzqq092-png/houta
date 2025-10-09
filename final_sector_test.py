#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终板块资金流修复验证测试
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def final_sector_test():
    """最终板块资金流修复验证测试"""
    print("🎯 最终板块资金流修复验证测试")
    print("=" * 40)

    try:
        # 1. 验证枚举定义
        print("✅ 步骤 1: 验证枚举定义...")
        from core.plugin_types import AssetType, DataType

        print(f"   AssetType.SECTOR: {AssetType.SECTOR.value}")
        print(f"   DataType.SECTOR_FUND_FLOW: {DataType.SECTOR_FUND_FLOW.value}")

        # 2. 验证东方财富插件支持
        print("\n✅ 步骤 2: 验证东方财富插件支持...")
        from plugins.data_sources.eastmoney_plugin import EastMoneyStockPlugin

        plugin = EastMoneyStockPlugin()
        plugin_info = plugin.get_plugin_info()

        sector_supported = AssetType.SECTOR in plugin_info.supported_asset_types
        flow_supported = DataType.SECTOR_FUND_FLOW in plugin_info.supported_data_types
        has_method = hasattr(plugin, 'get_sector_fund_flow_data')

        print(f"   支持SECTOR资产类型: {sector_supported}")
        print(f"   支持SECTOR_FUND_FLOW数据类型: {flow_supported}")
        print(f"   有get_sector_fund_flow_data方法: {has_method}")

        if sector_supported and flow_supported and has_method:
            print(" ✅ 东方财富插件完全支持板块资金流")
        else:
            print(" ❌ 东方财富插件支持不完整")
            return False

        # 3. 验证TET路由请求
        print("\n✅ 步骤 3: 验证TET路由请求...")
        from core.data_source_extensions import RoutingRequest

        routing_request = RoutingRequest(
            asset_type=AssetType.SECTOR,
            data_type=DataType.SECTOR_FUND_FLOW,
            symbol="sector",
            priority=0,
            timeout_ms=5000
        )

        print(f"   路由请求创建成功: {routing_request.asset_type.value} -> {routing_request.data_type.value}")

        print("\n🎉 所有修复验证通过！")
        print("\n📋 修复总结:")
        print(" 1. ✅ 添加了AssetType.SECTOR枚举")
        print(" 2. ✅ 添加了DataType.SECTOR_FUND_FLOW枚举")
        print(" 3. ✅ 更新了东方财富插件支持的资产类型")
        print(" 4. ✅ 更新了东方财富插件支持的数据类型")
        print(" 5. ✅ 验证了板块资金流方法存在")
        print(" 6. ✅ 验证了TET路由请求可以正确创建")

        print("\n🚀 现在板块资金流服务应该能够找到可用的数据源了！")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = final_sector_test()
    sys.exit(0 if success else 1)
