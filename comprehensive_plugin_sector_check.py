#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面检查所有插件的板块资金流支持情况
"""

import sys
import os
import importlib
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def comprehensive_plugin_sector_check():
    """全面检查所有插件的板块资金流支持情况"""
    print("🔍 全面检查所有插件的板块资金流支持情况")
    print("=" * 60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from core.plugin_types import AssetType, DataType

        # 定义要检查的插件列表
        plugins_to_check = [
            {
                "name": "东方财富插件",
                "module": "plugins.data_sources.eastmoney_plugin",
                "class": "EastMoneyStockPlugin"
            },
            {
                "name": "新浪插件",
                "module": "plugins.data_sources.sina_plugin",
                "class": "SinaPlugin"
            },
            {
                "name": "通达信插件",
                "module": "plugins.data_sources.tongdaxin_plugin",
                "class": "TongdaxinStockPlugin"
            },
            {
                "name": "自定义数据插件",
                "module": "plugins.examples.custom_data_plugin",
                "class": "CustomDataPlugin"
            },
            {
                "name": "我的钢铁插件",
                "module": "plugins.examples.mysteel_data_plugin",
                "class": "MySteelDataPlugin"
            },
            {
                "name": "文华数据插件",
                "module": "plugins.examples.wenhua_data_plugin",
                "class": "WenhuaDataPlugin"
            },
            {
                "name": "债券数据插件",
                "module": "plugins.examples.bond_data_plugin",
                "class": "BondDataPlugin"
            },
            {
                "name": "外汇数据插件",
                "module": "plugins.examples.forex_data_plugin",
                "class": "ForexDataPlugin"
            }
        ]

        issues_found = []
        plugins_with_sector_method = []
        plugins_needing_fix = []

        print("📋 检查结果:")
        print("-" * 60)

        for plugin_info in plugins_to_check:
            plugin_name = plugin_info["name"]
            module_path = plugin_info["module"]
            class_name = plugin_info["class"]

            try:
                # 动态导入插件模块
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)

                # 创建插件实例
                plugin_instance = plugin_class()

                # 检查是否有板块资金流方法
                has_sector_method = hasattr(plugin_instance, 'get_sector_fund_flow_data')

                if has_sector_method:
                    plugins_with_sector_method.append(plugin_name)

                    # 检查插件信息
                    try:
                        plugin_info_obj = plugin_instance.get_plugin_info()
                        supported_assets = plugin_info_obj.supported_asset_types
                        supported_data = plugin_info_obj.supported_data_types

                        # 检查是否支持SECTOR资产类型
                        supports_sector = AssetType.SECTOR in supported_assets
                        supports_sector_flow = DataType.SECTOR_FUND_FLOW in supported_data

                        print(f"🔌 {plugin_name}:")
                        print(f"   ✅ 有get_sector_fund_flow_data方法")
                        print(f"   {'✅' if supports_sector else '❌'} 支持SECTOR资产类型: {supports_sector}")
                        print(f"   {'✅' if supports_sector_flow else '❌'} 支持SECTOR_FUND_FLOW数据类型: {supports_sector_flow}")

                        if not supports_sector or not supports_sector_flow:
                            plugins_needing_fix.append({
                                'name': plugin_name,
                                'module': module_path,
                                'class': class_name,
                                'needs_sector': not supports_sector,
                                'needs_flow': not supports_sector_flow
                            })
                            issues_found.append(f"{plugin_name}: 缺少正确的类型声明")

                        print(f"   支持的资产类型: {[t.value for t in supported_assets]}")
                        print(f"   支持的数据类型: {[t.value for t in supported_data]}")
                        print()

                    except Exception as e:
                        print(f"🔌 {plugin_name}:")
                        print(f"   ✅ 有get_sector_fund_flow_data方法")
                        print(f"   ❌ 获取插件信息失败: {e}")
                        issues_found.append(f"{plugin_name}: 获取插件信息失败")
                        print()

                else:
                    print(f"🔌 {plugin_name}:")
                    print(f"   ❌ 没有get_sector_fund_flow_data方法")
                    print()

            except Exception as e:
                print(f"🔌 {plugin_name}:")
                print(f"   ❌ 插件加载失败: {e}")
                issues_found.append(f"{plugin_name}: 插件加载失败")
                print()

        # 总结报告
        print("=" * 60)
        print("📊 检查总结:")
        print(f"   总检查插件数: {len(plugins_to_check)}")
        print(f"   有板块资金流方法的插件: {len(plugins_with_sector_method)}")
        print(f"   需要修复的插件: {len(plugins_needing_fix)}")
        print(f"   发现的问题: {len(issues_found)}")

        if plugins_with_sector_method:
            print(f"\n✅ 支持板块资金流的插件:")
            for plugin in plugins_with_sector_method:
                print(f"   - {plugin}")

        if plugins_needing_fix:
            print(f"\n⚠️ 需要修复的插件:")
            for plugin in plugins_needing_fix:
                print(f"   - {plugin['name']}")
                if plugin['needs_sector']:
                    print(f"     需要添加: AssetType.SECTOR")
                if plugin['needs_flow']:
                    print(f"     需要添加: DataType.SECTOR_FUND_FLOW")

        if issues_found:
            print(f"\n❌ 发现的问题:")
            for issue in issues_found:
                print(f"   - {issue}")

        return plugins_needing_fix

    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    plugins_needing_fix = comprehensive_plugin_sector_check()

    if plugins_needing_fix:
        print(f"\n🔧 发现 {len(plugins_needing_fix)} 个插件需要修复")
    else:
        print(f"\n🎉 所有插件的板块资金流支持都正确配置！")

    sys.exit(0)
