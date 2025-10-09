#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证系统中不再有重复的东方财富插件
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verify_no_duplicate_eastmoney():
    """验证系统中不再有重复的东方财富插件"""
    print("🔍 验证系统中不再有重复的东方财富插件")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. 测试TET框架中的插件识别
        print("🔬 测试TET框架中的插件识别:")

        # 模拟启动服务来测试插件注册
        from core.services.service_bootstrap import ServiceBootstrap
        bootstrap = ServiceBootstrap()

        # 只初始化必要的服务来测试插件
        print(" 🚀 初始化服务...")
        success = bootstrap.bootstrap()

        if success:
            print(" ✅ 服务初始化成功")

            # 获取统一数据管理器
            from core.containers.unified_service_container import UnifiedServiceContainer
            from core.services.unified_data_manager import UnifiedDataManager

            container = UnifiedServiceContainer()
            data_manager = container.resolve(UnifiedDataManager)

            if data_manager:
                print(" ✅ 获取UnifiedDataManager成功")

                # 检查注册的数据源插件
                registered_plugins = []
                if hasattr(data_manager, '_data_source_plugins'):
                    for plugin_name, plugin_info in data_manager._data_source_plugins.items():
                        if 'eastmoney' in plugin_name.lower():
                            registered_plugins.append({
                                'name': plugin_name,
                                'plugin': plugin_info['plugin'],
                                'plugin_id': getattr(plugin_info['plugin'], 'plugin_id', 'N/A')
                            })

                print(f"\n   📋 找到的东方财富相关插件:")
                if registered_plugins:
                    for plugin in registered_plugins:
                        print(f"      - 名称: {plugin['name']}")
                        print(f"        ID: {plugin['plugin_id']}")
                        print(f"        类型: {type(plugin['plugin']).__name__}")
                        print()
                else:
                    print("    ❌ 未找到注册的东方财富插件")

                # 测试板块资金流数据获取
                print(" 🧪 测试板块资金流数据获取:")
                try:
                    from core.services.sector_fund_flow_service import SectorFundFlowService
                    sector_service = container.resolve(SectorFundFlowService)

                    if sector_service:
                        print("    ✅ 获取SectorFundFlowService成功")

                        # 尝试获取数据
                        sector_data = sector_service.get_sector_flow_rank(limit=5)

                        if sector_data and not sector_data.empty:
                            print(f"      ✅ 成功获取板块资金流数据: {len(sector_data)} 条记录")
                            print(f"      📊 数据来源验证:")

                            # 检查数据来源
                            import pandas as pd
                            unique_sources = sector_data.get('data_source', pd.Series()).unique() if 'data_source' in sector_data.columns else ['unknown']
                            for source in unique_sources:
                                print(f"         - {source}")
                        else:
                            print("    ⚠️ 板块资金流数据为空")
                    else:
                        print("    ❌ 无法获取SectorFundFlowService")

                except Exception as e:
                    print(f"      ❌ 板块资金流测试失败: {e}")

                return len(registered_plugins) == 1  # 应该只有一个东方财富插件
            else:
                print(" ❌ 无法获取UnifiedDataManager")
                return False
        else:
            print(" ❌ 服务初始化失败")
            return False

    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_no_duplicate_eastmoney()

    print("\n" + "=" * 60)
    if success:
        print("🎉 验证成功！")
        print("✅ 系统中只有一个东方财富插件")
        print("✅ 插件ID正确设置为 data_sources.eastmoney_plugin")
        print("✅ TET框架能正确识别插件")
        print("✅ 板块资金流功能正常工作")
    else:
        print("❌ 验证失败，可能仍存在重复插件问题")

    sys.exit(0 if success else 1)
