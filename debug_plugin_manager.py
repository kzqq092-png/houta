#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试PluginManager，查看插件加载情况
"""

from core.plugin_manager import PluginManager
from core.containers import get_service_container

print("=" * 80)
print("调试PluginManager插件加载")
print("=" * 80)

# 方法1: 从容器获取
print("\n方法1: 从ServiceContainer获取")
try:
    container = get_service_container()
    if container:
        plugin_manager = container.get('plugin_manager')
        if plugin_manager:
            print(f"✅ 从容器获取成功: {type(plugin_manager)}")
            print(f"   插件数量: {len(plugin_manager.plugins) if hasattr(plugin_manager, 'plugins') else '未知'}")
        else:
            print("❌ 容器中没有plugin_manager")
    else:
        print("❌ ServiceContainer不可用")
except Exception as e:
    print(f"❌ 获取失败: {e}")

# 方法2: 全局实例
print("\n方法2: 获取PluginManager全局实例")
try:
    # 通过ServiceContainer获取PluginManager实例
    from core.containers import get_service_container
    container = get_service_container()
    plugin_manager = container.resolve(PluginManager) if container else None
    if plugin_manager:
        print(f"✅ 全局实例获取成功: {type(plugin_manager)}")
        print(f"   插件数量: {len(plugin_manager.plugins) if hasattr(plugin_manager, 'plugins') else '未知'}")

        if hasattr(plugin_manager, 'plugins'):
            print(f"\n已加载的插件 ({len(plugin_manager.plugins)} 个):")

            # 统计分类
            data_sources = []
            indicators = []
            strategies = []
            others = []

            for plugin_name in plugin_manager.plugins.keys():
                if 'data_sources' in plugin_name or 'data_source' in plugin_name.lower():
                    data_sources.append(plugin_name)
                elif 'indicator' in plugin_name.lower():
                    indicators.append(plugin_name)
                elif 'strateg' in plugin_name.lower():
                    strategies.append(plugin_name)
                else:
                    others.append(plugin_name)

            print(f"\n📊 数据源插件 ({len(data_sources)} 个):")
            for name in sorted(data_sources):
                plugin_info = plugin_manager.plugins[name]

                # 尝试获取name
                display_name = "未知"
                if hasattr(plugin_info, 'name'):
                    display_name = plugin_info.name
                elif isinstance(plugin_info, dict):
                    display_name = plugin_info.get('name', plugin_info.get('display_name', '未知'))

                print(f"  - {name}")
                print(f"    显示名称: {display_name}")
                print(f"    类型: {type(plugin_info)}")

            print(f"\n📈 指标插件 ({len(indicators)} 个):")
            for name in sorted(indicators):
                print(f"  - {name}")

            print(f"\n📉 策略插件 ({len(strategies)} 个):")
            for name in sorted(strategies):
                print(f"  - {name}")

            print(f"\n🔧 其他插件 ({len(others)} 个):")
            for name in sorted(others):
                print(f"  - {name}")

    else:
        print("❌ 全局实例为None")
except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
