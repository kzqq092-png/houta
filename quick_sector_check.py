#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查SECTOR资产类型支持情况
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def quick_sector_check():
    """快速检查SECTOR资产类型支持情况"""
    print("快速SECTOR支持检查")
    print("=" * 30)

    try:
        # 1. 检查资产类型枚举
        from core.plugin_types import AssetType, DataType

        print(f"AssetType.SECTOR: {AssetType.SECTOR.value}")
        print(f"DataType.SECTOR_FUND_FLOW: {DataType.SECTOR_FUND_FLOW.value}")

        # 2. 检查东方财富插件是否支持板块资金流
        print("\n检查东方财富插件...")
        try:
            from plugins.data_sources.eastmoney_plugin import EastMoneyStockPlugin
            plugin = EastMoneyStockPlugin()

            # 检查插件信息
            plugin_info = plugin.get_plugin_info()
            print(f"支持的资产类型: {[t.value for t in plugin_info.supported_asset_types]}")
            print(f"是否支持SECTOR: {AssetType.SECTOR in plugin_info.supported_asset_types}")

            # 检查是否有板块资金流方法
            has_sector_method = hasattr(plugin, 'get_sector_fund_flow_data')
            print(f"有get_sector_fund_flow_data方法: {has_sector_method}")

            if has_sector_method:
                print("✅ 东方财富插件支持板块资金流")
            else:
                print("❌ 东方财富插件不支持板块资金流")

        except Exception as e:
            print(f"❌ 东方财富插件检查失败: {e}")

        # 3. 检查其他插件
        print("\n检查其他插件...")
        plugin_classes = [
            ("新浪插件", "plugins.data_sources.sina_plugin", "SinaPlugin"),
            ("通达信插件", "plugins.data_sources.tongdaxin_plugin", "TongdaxinStockPlugin"),
        ]

        for name, module_path, class_name in plugin_classes:
            try:
                module = __import__(module_path, fromlist=[class_name])
                plugin_class = getattr(module, class_name)
                plugin = plugin_class()

                has_sector_method = hasattr(plugin, 'get_sector_fund_flow_data')
                print(f"{name}: {'✅' if has_sector_method else '❌'} get_sector_fund_flow_data")

            except Exception as e:
                print(f"{name}: ❌ 检查失败 - {e}")

        print("\n🎯 检查完成！")
        return True

    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = quick_sector_check()
    sys.exit(0 if success else 1)
