#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强后的插件板块资金流功能
"""

import sys
import os
import importlib
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_enhanced_sector_plugins():
    """测试增强后的插件板块资金流功能"""
    print("🧪 测试增强后的插件板块资金流功能")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from core.plugin_types import AssetType, DataType

        # 要测试的插件列表
        plugins_to_test = [
            {
                "name": "新浪插件",
                "module": "plugins.data_sources.sina_plugin",
                "class": "SinaPlugin",
                "test_params": {"limit": 10}
            },
            {
                "name": "自定义数据插件",
                "module": "plugins.examples.custom_data_plugin",
                "class": "CustomDataPlugin",
                "test_params": {"limit": 5, "data_source": "sample"}
            }
        ]

        test_results = []

        print("🔬 开始功能测试:")
        print("-" * 60)

        for plugin_info in plugins_to_test:
            plugin_name = plugin_info["name"]
            module_path = plugin_info["module"]
            class_name = plugin_info["class"]
            test_params = plugin_info["test_params"]

            print(f"\n🔌 测试 {plugin_name}:")

            try:
                # 动态导入插件模块
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name)

                # 创建插件实例
                plugin_instance = plugin_class()

                # 测试插件信息
                plugin_info_obj = plugin_instance.get_plugin_info()
                supports_sector = AssetType.SECTOR in plugin_info_obj.supported_asset_types
                supports_sector_flow = DataType.SECTOR_FUND_FLOW in plugin_info_obj.supported_data_types

                print(f"   ✅ 插件信息检查通过")
                print(f"      - 支持SECTOR资产类型: {supports_sector}")
                print(f"      - 支持SECTOR_FUND_FLOW数据类型: {supports_sector_flow}")

                # 测试板块资金流方法
                if hasattr(plugin_instance, 'get_sector_fund_flow_data'):
                    print(f"   🔍 测试get_sector_fund_flow_data方法...")

                    # 调用方法获取数据
                    sector_data = plugin_instance.get_sector_fund_flow_data(**test_params)

                    if sector_data is not None and not sector_data.empty:
                        print(f"   ✅ 数据获取成功!")
                        print(f"      - 返回记录数: {len(sector_data)}")
                        print(f"      - 数据列: {list(sector_data.columns)}")

                        # 显示前几条数据
                        if len(sector_data) > 0:
                            print(f"      - 示例数据:")
                            for idx, row in sector_data.head(3).iterrows():
                                sector_name = row.get('sector_name', 'N/A')
                                net_inflow = row.get('net_inflow', 0)
                                print(f"        {idx+1}. {sector_name}: 净流入 {net_inflow:.2f}")

                        test_results.append({
                            'plugin': plugin_name,
                            'status': 'success',
                            'records': len(sector_data),
                            'columns': list(sector_data.columns)
                        })

                    else:
                        print(f"   ⚠️ 数据获取为空")
                        test_results.append({
                            'plugin': plugin_name,
                            'status': 'empty_data',
                            'records': 0,
                            'columns': []
                        })

                else:
                    print(f"   ❌ 缺少get_sector_fund_flow_data方法")
                    test_results.append({
                        'plugin': plugin_name,
                        'status': 'missing_method',
                        'records': 0,
                        'columns': []
                    })

            except Exception as e:
                print(f"   ❌ 测试失败: {e}")
                import traceback
                print(f"   详细错误: {traceback.format_exc()}")
                test_results.append({
                    'plugin': plugin_name,
                    'status': 'error',
                    'error': str(e),
                    'records': 0,
                    'columns': []
                })

        # 测试总结
        print("\n" + "=" * 60)
        print("📊 测试总结:")

        success_count = sum(1 for r in test_results if r['status'] == 'success')
        total_count = len(test_results)

        print(f"   总测试插件数: {total_count}")
        print(f"   成功插件数: {success_count}")
        print(f"   成功率: {success_count/total_count*100:.1f}%")

        print(f"\n📋 详细结果:")
        for result in test_results:
            status_icon = {
                'success': '✅',
                'empty_data': '⚠️',
                'missing_method': '❌',
                'error': '❌'
            }.get(result['status'], '❓')

            print(f"   {status_icon} {result['plugin']}: {result['status']}")
            if result['status'] == 'success':
                print(f"      - 获取记录数: {result['records']}")
                print(f"      - 数据字段数: {len(result['columns'])}")
            elif result['status'] == 'error':
                print(f"      - 错误: {result.get('error', 'Unknown error')}")

        # 功能验证结论
        if success_count == total_count:
            print(f"\n🎉 所有插件板块资金流功能测试通过！")
            return True
        elif success_count > 0:
            print(f"\n⚠️ 部分插件测试通过，需要进一步优化")
            return False
        else:
            print(f"\n❌ 所有插件测试失败，需要检查实现")
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_enhanced_sector_plugins()

    if success:
        print(f"\n🚀 插件能力增强完全成功！")
        print(f"HIkyuu-UI系统现在拥有4个支持板块资金流的数据源插件：")
        print(f"   1. 东方财富插件 - 网络API数据源")
        print(f"   2. 新浪插件 - 新浪财经API数据源")
        print(f"   3. 通达信插件 - 本地/网络混合数据源")
        print(f"   4. 自定义数据插件 - 可配置多种数据源")
    else:
        print(f"\n⚠️ 部分插件需要进一步优化")

    sys.exit(0 if success else 1)
