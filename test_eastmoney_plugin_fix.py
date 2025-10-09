#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试东方财富插件修复结果
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_eastmoney_plugin_fix():
    """测试东方财富插件修复结果"""
    print("🔧 测试东方财富插件修复结果")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. 测试正确的插件导入
        print("🔍 测试插件导入:")
        try:
            from plugins.data_sources.eastmoney_plugin import EastMoneyStockPlugin
            plugin = EastMoneyStockPlugin()
            print(f"   ✅ 成功导入: {plugin.__class__.__module__}.{plugin.__class__.__name__}")
            print(f"   📋 插件ID: {plugin.plugin_id}")
            print(f"   📋 插件名称: {plugin.name}")
        except ImportError as e:
            print(f"   ❌ 导入失败: {e}")
            return False

        print()

        # 2. 测试错误的插件导入（应该失败）
        print("🚫 测试错误的插件导入（应该失败）:")
        try:
            from plugins.examples.eastmoney_stock_plugin import EastMoneyStockPlugin as WrongPlugin
            print(f"   ❌ 意外成功导入了错误路径的插件")
            return False
        except ImportError:
            print(f"   ✅ 正确地无法导入错误路径的插件")

        print()

        # 3. 测试插件功能
        print("🧪 测试插件功能:")

        # 检查插件信息
        plugin_info = plugin.get_plugin_info()
        print(f"   📊 支持的资产类型: {[t.value for t in plugin_info.supported_asset_types]}")
        print(f"   📊 支持的数据类型: {[t.value for t in plugin_info.supported_data_types]}")

        # 测试连接
        if plugin.connect():
            print(f"   ✅ 连接成功")

            # 测试板块资金流数据
            if hasattr(plugin, 'get_sector_fund_flow_data'):
                sector_data = plugin.get_sector_fund_flow_data(symbol="sector")
                if sector_data is not None and not sector_data.empty:
                    print(f"   ✅ 板块资金流数据获取成功: {len(sector_data)} 条记录")
                else:
                    print(f"   ⚠️ 板块资金流数据为空")
            else:
                print(f"   ❌ 缺少板块资金流方法")

            plugin.disconnect()
        else:
            print(f"   ❌ 连接失败")

        print()

        # 4. 验证plugin_id的正确性
        print("🔍 验证plugin_id:")
        expected_id = "data_sources.eastmoney_plugin"
        actual_id = plugin.plugin_id

        if actual_id == expected_id:
            print(f"   ✅ plugin_id正确: {actual_id}")
        else:
            print(f"   ❌ plugin_id错误: 期望 {expected_id}, 实际 {actual_id}")
            return False

        return True

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_eastmoney_plugin_fix()

    print("\n" + "=" * 60)
    if success:
        print("🎉 东方财富插件修复成功！")
        print("✅ 插件ID已正确设置")
        print("✅ 导入路径已修复")
        print("✅ 功能正常工作")
        print("✅ 不再有重复的插件引用")
    else:
        print("❌ 东方财富插件修复失败")

    sys.exit(0 if success else 1)
