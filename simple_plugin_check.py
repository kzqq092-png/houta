#!/usr/bin/env python3
"""
简化的插件检测脚本
"""

import sys
import os
import importlib.util

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def check_plugin_files():
    """检查插件文件和类定义"""
    print("=" * 50)
    print("🔍 检查插件文件")
    print("=" * 50)

    plugins_dir = "plugins/examples"
    if not os.path.exists(plugins_dir):
        print(f"❌ 插件目录不存在: {plugins_dir}")
        return

    plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('_plugin.py')]
    print(f"📊 找到 {len(plugin_files)} 个插件文件")

    detected_plugins = []

    for plugin_file in plugin_files:
        file_path = os.path.join(plugins_dir, plugin_file)
        module_name = plugin_file[:-3]  # 去掉.py后缀

        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    attr_name.endswith('Plugin') and
                        attr_name != 'IDataSourcePlugin'):
                    plugin_classes.append(attr_name)

            print(f"✅ {plugin_file}:")
            print(f"   - 找到类: {', '.join(plugin_classes)}")

            # 尝试实例化第一个插件类
            if plugin_classes:
                plugin_class = getattr(module, plugin_classes[0])
                try:
                    plugin_instance = plugin_class()

                    # 检查插件类型
                    plugin_type = getattr(plugin_instance, 'plugin_type', 'Unknown')
                    supported_assets = []
                    if hasattr(plugin_instance, 'get_supported_asset_types'):
                        try:
                            supported_assets = plugin_instance.get_supported_asset_types()
                        except:
                            pass

                    # 检查是否实现了必要方法
                    required_methods = ['get_plugin_info', 'initialize', 'shutdown', 'fetch_data', 'get_real_time_data', 'health_check']
                    implemented_methods = [method for method in required_methods if hasattr(plugin_instance, method)]

                    print(f"   - 插件类型: {plugin_type}")
                    print(f"   - 支持资产: {[str(asset) for asset in supported_assets]}")
                    print(f"   - 实现方法: {len(implemented_methods)}/{len(required_methods)}")

                    # 检查是否为数据源插件
                    is_data_source = 'data_source' in str(plugin_type).lower()
                    print(f"   - 数据源插件: {is_data_source}")

                    if is_data_source:
                        detected_plugins.append({
                            'file': plugin_file,
                            'class': plugin_classes[0],
                            'type': plugin_type,
                            'assets': supported_assets,
                            'methods': implemented_methods
                        })

                except Exception as e:
                    print(f"   - ❌ 实例化失败: {e}")

        except Exception as e:
            print(f"❌ {plugin_file}: 导入失败 - {e}")

    print(f"\n📊 检测到的数据源插件: {len(detected_plugins)}")
    for plugin in detected_plugins:
        print(f"   - {plugin['file']}: {plugin['class']} ({plugin['type']})")

    return detected_plugins


def check_plugin_manager():
    """检查插件管理器状态"""
    print("\n" + "=" * 50)
    print("🔍 检查插件管理器")
    print("=" * 50)

    try:
        from core.plugin_manager import PluginManager
        print("✅ PluginManager 导入成功")

        # 创建插件管理器实例
        pm = PluginManager()
        print("✅ PluginManager 实例创建成功")

        # 检查关键属性
        if hasattr(pm, 'data_source_plugins'):
            print(f"✅ data_source_plugins 属性存在 (当前: {len(pm.data_source_plugins)} 个)")
        else:
            print("❌ data_source_plugins 属性不存在")

        if hasattr(pm, 'enhanced_plugins'):
            print(f"✅ enhanced_plugins 属性存在 (当前: {len(pm.enhanced_plugins)} 个)")
        else:
            print("❌ enhanced_plugins 属性不存在")

        if hasattr(pm, 'plugin_instances'):
            print(f"✅ plugin_instances 属性存在 (当前: {len(pm.plugin_instances)} 个)")
        else:
            print("❌ plugin_instances 属性不存在")

        # 检查方法
        methods = ['get_data_source_plugins', '_is_data_source_plugin', 'load_all_plugins']
        for method in methods:
            if hasattr(pm, method):
                print(f"✅ {method} 方法存在")
            else:
                print(f"❌ {method} 方法不存在")

    except Exception as e:
        print(f"❌ 插件管理器检查失败: {e}")


def main():
    """主函数"""
    detected_plugins = check_plugin_files()
    check_plugin_manager()

    print("\n" + "=" * 50)
    print("📋 总结")
    print("=" * 50)
    print(f"✅ 检测到 {len(detected_plugins)} 个数据源插件")
    if detected_plugins:
        print("建议: 插件文件正常，问题可能在加载或注册流程")
    else:
        print("问题: 没有检测到有效的数据源插件")


if __name__ == "__main__":
    main()
