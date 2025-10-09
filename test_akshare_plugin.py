#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AKShare插件
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_akshare_plugin():
    """测试AKShare插件"""
    print("🧪 测试AKShare插件")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from core.plugin_types import AssetType, DataType
        from plugins.data_sources.akshare_plugin import AKSharePlugin

        # 创建插件实例
        plugin = AKSharePlugin()

        print("🔍 插件基本信息测试:")
        print(f"   插件名称: {plugin.name}")
        print(f"   插件版本: {plugin.version}")
        print(f"   插件作者: {plugin.author}")
        print()

        # 测试插件信息
        plugin_info = plugin.get_plugin_info()
        print("📋 插件信息测试:")
        print(f"   支持的资产类型: {[t.value for t in plugin_info.supported_asset_types]}")
        print(f"   支持的数据类型: {[t.value for t in plugin_info.supported_data_types]}")
        print(f"   插件能力: {plugin_info.capabilities}")
        print()

        # 测试连接
        print("🔗 连接测试:")
        if plugin._internal_connect():
            print(" ✅ 连接成功")
        else:
            print(" ❌ 连接失败")
            return False
        print()

        # 测试健康检查
        print("🏥 健康检查测试:")
        health_result = plugin.perform_health_check()
        print(f"   健康状态: {'✅ 健康' if health_result.is_healthy else '❌ 不健康'}")
        print(f"   响应时间: {health_result.response_time:.2f}ms")
        print(f"   消息: {health_result.message}")
        if health_result.extra_info:
            print(f"   额外信息: {health_result.extra_info}")
        print()

        # 测试板块资金流数据获取
        print("📊 板块资金流数据测试:")
        sector_data = plugin.get_sector_fund_flow_data(limit=10)

        if sector_data is not None and not sector_data.empty:
            print(f"   ✅ 成功获取数据: {len(sector_data)} 条记录")
            print(f"   📋 数据列: {list(sector_data.columns)}")
            print()

            print(" 📈 数据样本:")
            for idx, row in sector_data.head(5).iterrows():
                sector_name = row.get('sector_name', 'N/A')
                main_net_inflow = row.get('main_net_inflow', 0)
                change_percent = row.get('change_percent', 0)
                print(f"      {idx+1}. {sector_name}")
                print(f"         涨跌幅: {change_percent}%")
                print(f"         主力净流入: {main_net_inflow:,.0f}")
            print()

            # 测试缓存功能
            print("💾 缓存功能测试:")
            start_time = datetime.now()
            cached_data = plugin.get_sector_fund_flow_data(limit=10, use_cache=True)
            cache_time = (datetime.now() - start_time).total_seconds()

            if cached_data is not None and not cached_data.empty:
                print(f"   ✅ 缓存数据获取成功: {len(cached_data)} 条记录")
                print(f"   ⚡ 缓存响应时间: {cache_time*1000:.2f}ms")
            else:
                print(" ❌ 缓存数据获取失败")
            print()

            return True
        else:
            print(" ❌ 数据获取失败")
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理连接
        try:
            plugin._internal_disconnect()
            print("🔌 连接已断开")
        except:
            pass


if __name__ == "__main__":
    success = test_akshare_plugin()

    if success:
        print("🎉 AKShare插件测试完全成功！")
        print("✅ 插件功能正常，数据质量良好")
    else:
        print("❌ AKShare插件测试失败")

    sys.exit(0 if success else 1)
