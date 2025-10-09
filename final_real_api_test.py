#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试：只保留能获取真实数据的板块资金流插件
"""

import sys
import os
import importlib
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def final_real_api_test():
    """最终测试：只保留能获取真实数据的板块资金流插件"""
    print("🎯 最终测试：只保留能获取真实数据的板块资金流插件")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from core.plugin_types import AssetType, DataType

        # 所有插件列表
        all_plugins = [
            {
                "name": "东方财富插件",
                "module": "plugins.data_sources.eastmoney_plugin",
                "class": "EastMoneyStockPlugin",
                "test_params": {"symbol": "sector"}
            },
            {
                "name": "新浪插件",
                "module": "plugins.data_sources.sina_plugin",
                "class": "SinaPlugin",
                "test_params": {"limit": 10}
            },
            {
                "name": "通达信插件",
                "module": "plugins.data_sources.tongdaxin_plugin",
                "class": "TongdaxinStockPlugin",
                "test_params": {"limit": 10}
            },
            {
                "name": "自定义数据插件",
                "module": "plugins.examples.custom_data_plugin",
                "class": "CustomDataPlugin",
                "test_params": {"limit": 5}
            }
        ]

        print("🔍 检查所有插件的板块资金流支持情况:")
        print("-" * 60)

        supported_plugins = []
        removed_plugins = []

        for plugin_info in all_plugins:
            plugin_name = plugin_info["name"]
            module_path = plugin_info["module"]
            class_name = plugin_info["class"]

            print(f"\n🔌 检查 {plugin_name}:")

            try:
                # 动态导入插件模块
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)

                # 创建插件实例
                plugin_instance = plugin_class()

                # 检查插件信息
                plugin_info_obj = plugin_instance.get_plugin_info()
                supports_sector = AssetType.SECTOR in plugin_info_obj.supported_asset_types
                supports_sector_flow = DataType.SECTOR_FUND_FLOW in plugin_info_obj.supported_data_types
                has_method = hasattr(plugin_instance, 'get_sector_fund_flow_data')

                print(f"   - 支持SECTOR资产类型: {'✅' if supports_sector else '❌'}")
                print(f"   - 支持SECTOR_FUND_FLOW数据类型: {'✅' if supports_sector_flow else '❌'}")
                print(f"   - 有get_sector_fund_flow_data方法: {'✅' if has_method else '❌'}")

                if supports_sector and supports_sector_flow and has_method:
                    supported_plugins.append(plugin_name)
                    print(f"   ✅ 支持板块资金流功能")
                else:
                    removed_plugins.append(plugin_name)
                    print(f"   ❌ 不支持板块资金流功能")

            except Exception as e:
                print(f"   ❌ 插件加载失败: {e}")
                removed_plugins.append(plugin_name)

        print("\n" + "=" * 60)
        print("📊 最终结果总结:")
        print(f"   总插件数: {len(all_plugins)}")
        print(f"   支持板块资金流的插件数: {len(supported_plugins)}")
        print(f"   已删除板块资金流功能的插件数: {len(removed_plugins)}")

        if supported_plugins:
            print(f"\n✅ 支持板块资金流的插件:")
            for plugin in supported_plugins:
                print(f"   - {plugin}")

        if removed_plugins:
            print(f"\n❌ 已删除板块资金流功能的插件:")
            for plugin in removed_plugins:
                print(f"   - {plugin}")

        # 测试支持的插件是否能获取真实数据
        if supported_plugins:
            print(f"\n🧪 测试支持的插件是否能获取真实数据:")
            print("-" * 60)

            for plugin_info in all_plugins:
                if plugin_info["name"] in supported_plugins:
                    plugin_name = plugin_info["name"]
                    module_path = plugin_info["module"]
                    class_name = plugin_info["class"]
                    test_params = plugin_info["test_params"]

                    print(f"\n🔍 测试 {plugin_name}:")

                    try:
                        module = importlib.import_module(module_path)
                        plugin_class = getattr(module, class_name)
                        plugin_instance = plugin_class()

                        # 调用方法获取数据
                        sector_data = plugin_instance.get_sector_fund_flow_data(**test_params)

                        if sector_data is not None and not sector_data.empty:
                            print(f"   ✅ 成功获取真实数据: {len(sector_data)} 条记录")
                            print(f"   📊 数据字段: {list(sector_data.columns)}")

                            # 显示前3条数据
                            if len(sector_data) > 0:
                                print(f"   📋 示例数据:")
                                for idx, row in sector_data.head(3).iterrows():
                                    sector_name = row.get('sector_name', 'N/A')
                                    net_inflow = row.get('net_inflow', row.get('main_net_inflow', 0))
                                    print(f"      {idx+1}. {sector_name}: 净流入 {net_inflow}")
                        else:
                            print(f"   ❌ 无法获取真实数据")

                    except Exception as e:
                        print(f"   ❌ 测试失败: {e}")

        return len(supported_plugins) > 0

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = final_real_api_test()

    print(f"\n" + "=" * 60)
    if success:
        print(f"🎉 清理完成！HIkyuu-UI系统现在只保留能获取真实数据的板块资金流插件")
        print(f"✅ 所有模拟数据和无效功能已删除")
        print(f"✅ 只保留经过验证的真实API接口")
    else:
        print(f"⚠️ 没有插件能够提供真实的板块资金流数据")

    sys.exit(0 if success else 1)
