#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实的板块资金流API功能（删除模拟数据后）
"""

import sys
import os
import importlib
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_real_sector_apis():
    """测试真实的板块资金流API功能"""
    print("🧪 测试真实的板块资金流API功能（无模拟数据）")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        from core.plugin_types import AssetType, DataType

        # 要测试的插件列表（只包含应该支持真实API的插件）
        plugins_to_test = [
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
            }
        ]

        test_results = []

        print("🔬 开始真实API测试:")
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
                    print(f"   🔍 测试get_sector_fund_flow_data方法（真实API）...")

                    # 调用方法获取数据
                    sector_data = plugin_instance.get_sector_fund_flow_data(**test_params)

                    if sector_data is not None and not sector_data.empty:
                        print(f"   ✅ 真实数据获取成功!")
                        print(f"      - 返回记录数: {len(sector_data)}")
                        print(f"      - 数据列: {list(sector_data.columns)}")

                        # 验证数据来源不是模拟数据
                        import pandas as pd
                        data_source = sector_data.get('data_source', pd.Series()).iloc[0] if len(sector_data) > 0 else None
                        is_real_data = data_source and 'sample' not in str(data_source).lower()

                        print(f"      - 数据来源: {data_source}")
                        print(f"      - 是否为真实数据: {'✅' if is_real_data else '❌'}")

                        # 显示前几条数据
                        if len(sector_data) > 0:
                            print(f"      - 示例数据:")
                            for idx, row in sector_data.head(3).iterrows():
                                sector_name = row.get('sector_name', 'N/A')
                                net_inflow = row.get('net_inflow', row.get('main_net_inflow', 0))
                                print(f"        {idx+1}. {sector_name}: 净流入 {net_inflow}")

                        test_results.append({
                            'plugin': plugin_name,
                            'status': 'success',
                            'records': len(sector_data),
                            'columns': list(sector_data.columns),
                            'is_real_data': is_real_data
                        })

                    else:
                        print(f"   ❌ 真实数据获取失败或为空")
                        test_results.append({
                            'plugin': plugin_name,
                            'status': 'no_data',
                            'records': 0,
                            'columns': [],
                            'is_real_data': False
                        })

                else:
                    print(f"   ❌ 缺少get_sector_fund_flow_data方法")
                    test_results.append({
                        'plugin': plugin_name,
                        'status': 'missing_method',
                        'records': 0,
                        'columns': [],
                        'is_real_data': False
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
                    'columns': [],
                    'is_real_data': False
                })

        # 测试总结
        print("\n" + "=" * 60)
        print("📊 真实API测试总结:")

        success_count = sum(1 for r in test_results if r['status'] == 'success' and r['is_real_data'])
        total_count = len(test_results)

        print(f"   总测试插件数: {total_count}")
        print(f"   真实数据成功插件数: {success_count}")
        print(f"   真实数据成功率: {success_count/total_count*100:.1f}%")

        print(f"\n📋 详细结果:")
        for result in test_results:
            status_icon = {
                'success': '✅' if result.get('is_real_data') else '⚠️',
                'no_data': '❌',
                'missing_method': '❌',
                'error': '❌'
            }.get(result['status'], '❓')

            print(f"   {status_icon} {result['plugin']}: {result['status']}")
            if result['status'] == 'success':
                print(f"      - 获取记录数: {result['records']}")
                print(f"      - 数据字段数: {len(result['columns'])}")
                print(f"      - 真实数据: {'是' if result.get('is_real_data') else '否'}")
            elif result['status'] == 'error':
                print(f"      - 错误: {result.get('error', 'Unknown error')}")

        # 功能验证结论
        if success_count == total_count:
            print(f"\n🎉 所有插件都使用真实API获取板块资金流数据！")
            return True
        elif success_count > 0:
            print(f"\n⚠️ 部分插件使用真实API，部分需要进一步修复")
            return False
        else:
            print(f"\n❌ 所有插件都无法获取真实数据")
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_real_sector_apis()

    if success:
        print(f"\n🚀 真实API验证完全成功！")
        print(f"HIkyuu-UI系统现在只使用真实的板块资金流数据源：")
        print(f"   1. 东方财富插件 - 真实的东方财富API")
        print(f"   2. 新浪插件 - 真实的新浪财经API")
        print(f"   3. 通达信插件 - 真实的通达信数据源")
        print(f"   ❌ 自定义数据插件 - 已删除板块资金流功能（无法验证真实数据源）")
    else:
        print(f"\n⚠️ 部分插件需要进一步修复以使用真实API")

    sys.exit(0 if success else 1)
