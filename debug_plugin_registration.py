#!/usr/bin/env python3
"""
插件注册调试脚本
详细诊断为什么插件没有注册到路由器
"""

import sys
import traceback
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def debug_plugin_registration():
    """调试插件注册过程"""
    print("🔍 开始调试插件注册过程...")

    try:
        # 1. 导入必要的模块
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers.service_container import ServiceContainer
        from core.services.unified_data_manager import UnifiedDataManager
        from core.plugin_manager import PluginManager

        print("✅ 模块导入成功")

        # 2. 创建服务容器
        container = ServiceContainer()
        print("✅ 服务容器创建成功")

        # 3. 创建服务引导器
        bootstrap = ServiceBootstrap(container)
        print("✅ 服务引导器创建成功")

        # 4. 执行服务引导
        print("\n🔄 开始执行服务引导...")
        success = bootstrap.bootstrap()

        if success:
            print("✅ 服务引导成功")
        else:
            print("❌ 服务引导失败")
            return False

        # 5. 检查服务注册状态
        print("\n🔍 检查服务注册状态...")

        # 检查UnifiedDataManager
        if container.is_registered(UnifiedDataManager):
            data_manager = container.resolve(UnifiedDataManager)
            print(f"✅ UnifiedDataManager已注册: {type(data_manager).__name__}")

            # 检查数据源路由器
            if hasattr(data_manager, 'tet_pipeline') and data_manager.tet_pipeline:
                tet_pipeline = data_manager.tet_pipeline
                if hasattr(tet_pipeline, 'router'):
                    router = tet_pipeline.router
                    if router and hasattr(router, 'data_sources'):
                        print(f"✅ 数据源路由器可用，当前数据源数量: {len(router.data_sources)}")

                        if router.data_sources:
                            print("已注册的数据源:")
                            for name, source in router.data_sources.items():
                                print(f"  - {name}: {type(source).__name__}")
                        else:
                            print("📝 路由器中没有注册的数据源")
                    else:
                        print("❌ 数据源路由器不可用或没有data_sources属性")
                else:
                    print("❌ TET管道没有router属性")
            else:
                print("❌ UnifiedDataManager没有tet_pipeline或为None")
        else:
            print("❌ UnifiedDataManager未注册")

        # 检查PluginManager
        if container.is_registered(PluginManager):
            plugin_manager = container.resolve(PluginManager)
            print(f"✅ PluginManager已注册: {type(plugin_manager).__name__}")

            # 检查插件管理器的data_manager连接
            if hasattr(plugin_manager, 'data_manager') and plugin_manager.data_manager:
                print(f"✅ PluginManager已连接到数据管理器: {type(plugin_manager.data_manager).__name__}")
            else:
                print("❌ PluginManager未连接到数据管理器")

            # 检查加载的插件
            if hasattr(plugin_manager, 'plugin_instances'):
                print(f"✅ 插件实例数量: {len(plugin_manager.plugin_instances)}")

                if plugin_manager.plugin_instances:
                    print("已加载的插件实例:")
                    for name, instance in plugin_manager.plugin_instances.items():
                        is_data_source = plugin_manager._is_data_source_plugin_instance(instance)
                        print(f"  - {name}: {type(instance).__name__} (数据源: {is_data_source})")
                else:
                    print("📝 没有加载的插件实例")

            if hasattr(plugin_manager, 'enhanced_plugins'):
                print(f"✅ 增强插件信息数量: {len(plugin_manager.enhanced_plugins)}")

        else:
            print("❌ PluginManager未注册")

        # 6. 手动测试插件注册
        print("\n🔄 手动测试插件注册...")

        if container.is_registered(PluginManager) and container.is_registered(UnifiedDataManager):
            plugin_manager = container.resolve(PluginManager)
            data_manager = container.resolve(UnifiedDataManager)

            # 获取注册前的数据源数量
            if hasattr(data_manager, 'tet_pipeline') and data_manager.tet_pipeline:
                router = data_manager.tet_pipeline.router
                before_count = len(router.data_sources) if router and hasattr(router, 'data_sources') else 0
                print(f"注册前数据源数量: {before_count}")

                # 手动调用数据源插件注册
                plugin_manager._register_data_source_plugins_to_manager()

                # 获取注册后的数据源数量
                after_count = len(router.data_sources) if router and hasattr(router, 'data_sources') else 0
                print(f"注册后数据源数量: {after_count}")

                if after_count > before_count:
                    print(f"✅ 成功注册了 {after_count - before_count} 个数据源")

                    # 显示新注册的数据源
                    if router and hasattr(router, 'data_sources'):
                        print("当前所有数据源:")
                        for name, source in router.data_sources.items():
                            print(f"  - {name}: {type(source).__name__}")

                    return True
                else:
                    print("❌ 没有新的数据源被注册")

                    # 调试为什么没有注册
                    print("\n🔍 调试插件注册失败原因...")

                    # 检查插件实例
                    for name, instance in plugin_manager.plugin_instances.items():
                        is_data_source = plugin_manager._is_data_source_plugin_instance(instance)
                        print(f"插件 {name}: 是数据源={is_data_source}")

                        if is_data_source:
                            # 尝试手动注册这个插件
                            try:
                                success = data_manager.register_data_source_plugin(
                                    name, instance, priority=50, weight=1.0
                                )
                                print(f"  手动注册结果: {success}")
                            except Exception as e:
                                print(f"  手动注册失败: {e}")

                    return False
            else:
                print("❌ UnifiedDataManager没有tet_pipeline，无法测试")
                return False
        else:
            print("❌ 缺少必要的服务，无法测试")
            return False

    except Exception as e:
        print(f"❌ 调试过程失败: {e}")
        print(traceback.format_exc())
        return False


def main():
    """主函数"""
    print("🚀 开始插件注册调试...")
    print("=" * 60)

    success = debug_plugin_registration()

    print("\n" + "=" * 60)
    if success:
        print("🎉 插件注册调试完成，发现并解决了问题！")
    else:
        print("⚠️ 插件注册调试完成，但仍存在问题需要进一步检查")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
