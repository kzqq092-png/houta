#!/usr/bin/env python3
"""
诊断数据源插件检测和注册问题的脚本
"""

from core.services.service_bootstrap import ServiceBootstrap
from core.plugin_types import PluginType
from core.plugin_manager import PluginManager
import os
import sys
import logging

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


def diagnose_plugin_detection():
    """诊断插件检测问题"""
    print("=" * 60)
    print("🔍 诊断数据源插件检测问题")
    print("=" * 60)

    try:
        # 1. 初始化服务引导
        print("\n1️⃣ 初始化服务...")
        bootstrap = ServiceBootstrap()
        bootstrap.register_services()

        # 2. 获取插件管理器
        print("\n2️⃣ 获取插件管理器...")
        from core.services.service_bootstrap import get_service
        plugin_manager = get_service(PluginManager)

        if not plugin_manager:
            print("❌ 插件管理器未找到")
            return

        print(f"✅ 插件管理器获取成功: {type(plugin_manager)}")

        # 3. 检查插件目录
        print("\n3️⃣ 检查插件目录...")
        examples_dir = "plugins/examples"
        if os.path.exists(examples_dir):
            plugin_files = [f for f in os.listdir(examples_dir) if f.endswith('_plugin.py')]
            print(f"✅ 找到 {len(plugin_files)} 个插件文件:")
            for file in plugin_files:
                print(f"   - {file}")
        else:
            print(f"❌ 插件目录不存在: {examples_dir}")
            return

        # 4. 初始化插件管理器
        print("\n4️⃣ 初始化插件管理器...")
        plugin_manager.initialize()

        # 5. 检查所有插件
        print("\n5️⃣ 检查所有已加载插件...")
        all_plugins = plugin_manager.get_all_plugins()
        print(f"📊 总计已加载插件: {len(all_plugins)}")

        for plugin_name in all_plugins:
            print(f"   - {plugin_name}")

        # 6. 检查enhanced_plugins
        print("\n6️⃣ 检查enhanced_plugins...")
        if hasattr(plugin_manager, 'enhanced_plugins'):
            enhanced_plugins = plugin_manager.enhanced_plugins
            print(f"📊 Enhanced插件数量: {len(enhanced_plugins)}")

            for plugin_name, plugin_info in enhanced_plugins.items():
                plugin_type = getattr(plugin_info, 'plugin_type', 'Unknown')
                enabled = getattr(plugin_info, 'enabled', 'Unknown')
                print(f"   - {plugin_name}: 类型={plugin_type}, 启用={enabled}")
        else:
            print("⚠️ enhanced_plugins 属性不存在")

        # 7. 检查数据源插件
        print("\n7️⃣ 检查数据源插件...")
        if hasattr(plugin_manager, 'data_source_plugins'):
            ds_plugins = plugin_manager.data_source_plugins
            print(f"📊 数据源插件数量: {len(ds_plugins)}")

            for plugin_name, plugin_info in ds_plugins.items():
                print(f"   - {plugin_name}: {plugin_info.name}")
        else:
            print("⚠️ data_source_plugins 属性不存在")

        # 8. 检查插件实例
        print("\n8️⃣ 检查插件实例...")
        if hasattr(plugin_manager, 'plugin_instances'):
            instances = plugin_manager.plugin_instances
            print(f"📊 插件实例数量: {len(instances)}")

            for plugin_name, instance in instances.items():
                class_name = instance.__class__.__name__
                plugin_type = getattr(instance, 'plugin_type', 'Unknown')
                is_data_source = plugin_manager._is_data_source_plugin(instance, plugin_type)
                print(f"   - {plugin_name}: {class_name}, 类型={plugin_type}, 数据源={is_data_source}")
        else:
            print("⚠️ plugin_instances 属性不存在")

        # 9. 测试数据源插件获取方法
        print("\n9️⃣ 测试数据源插件获取方法...")
        if hasattr(plugin_manager, 'get_data_source_plugins'):
            ds_plugins = plugin_manager.get_data_source_plugins()
            print(f"📊 get_data_source_plugins() 返回: {len(ds_plugins)} 个插件")

            for plugin_name, plugin_info in ds_plugins.items():
                print(f"   - {plugin_name}: {plugin_info.name}")
        else:
            print("⚠️ get_data_source_plugins 方法不存在")

        # 10. 检查数据管理器注册
        print("\n🔟 检查数据管理器注册...")
        if hasattr(plugin_manager, 'data_manager') and plugin_manager.data_manager:
            print(f"✅ 数据管理器存在: {type(plugin_manager.data_manager)}")

            if hasattr(plugin_manager.data_manager, '_plugin_data_sources'):
                registered_plugins = plugin_manager.data_manager._plugin_data_sources
                print(f"📊 已注册到数据管理器的插件: {len(registered_plugins)}")

                for plugin_name in registered_plugins:
                    print(f"   - {plugin_name}")
            else:
                print("⚠️ 数据管理器没有 _plugin_data_sources 属性")
        else:
            print("⚠️ 数据管理器不存在")

    except Exception as e:
        print(f"❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    diagnose_plugin_detection()


if __name__ == "__main__":
    main()
