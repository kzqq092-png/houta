"""
诊断插件加载问题

分析为什么只有4个插件被发现和加载

作者: FactorWeave-Quant团队
日期: 2024-09-30
"""

import sys
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def simulate_plugin_loading():
    """模拟插件加载过程"""
    logger.info("="*80)
    logger.info("模拟插件加载过程")
    logger.info("="*80)

    project_root = Path(__file__).parent
    plugins_dir = project_root / "plugins"

    # 导入必要的模块
    sys.path.insert(0, str(project_root))

    from core.plugin_manager import PluginManager
    from core.data_source_router import DataSourceRouter
    from core.tet_data_pipeline import TETDataPipeline
    from core.services.uni_plugin_data_manager import UniPluginDataManager

    logger.info("\n步骤1: 创建PluginManager并加载插件...")
    plugin_manager = PluginManager(plugin_dir=str(plugins_dir))
    plugin_manager.load_all_plugins()

    all_plugins = plugin_manager.get_all_plugins()
    logger.info(f"PluginManager加载的插件总数: {len(all_plugins)}")

    # 显示所有加载的插件
    logger.info("\n已加载的插件列表:")
    for plugin_name in sorted(all_plugins.keys()):
        plugin_instance = all_plugins[plugin_name]
        class_name = plugin_instance.__class__.__name__ if plugin_instance else "None"
        logger.info(f"  - {plugin_name} ({class_name})")

    logger.info("\n步骤2: 创建UniPluginDataManager并初始化...")
    data_source_router = DataSourceRouter()
    tet_pipeline = TETDataPipeline(data_source_router)

    uni_data_manager = UniPluginDataManager(
        plugin_manager=plugin_manager,
        data_source_router=data_source_router,
        tet_pipeline=tet_pipeline
    )

    # 初始化会触发插件注册
    uni_data_manager.initialize()

    logger.info("\n步骤3: 检查PluginCenter发现的数据源插件...")
    plugin_center = uni_data_manager.plugin_center
    data_source_plugins = plugin_center.data_source_plugins

    logger.info(f"PluginCenter发现的数据源插件数: {len(data_source_plugins)}")
    logger.info("\n数据源插件列表:")
    for plugin_id in sorted(data_source_plugins.keys()):
        plugin_info = plugin_center.get_plugin_info(plugin_id)
        logger.info(f"  - {plugin_id}")
        if 'config' in plugin_info:
            config = plugin_info['config']
            logger.info(f"    名称: {config.get('name', 'Unknown')}")
            logger.info(f"    支持的数据类型: {config.get('supported_data_types', [])}")

    logger.info("\n步骤4: 检查TET路由器中注册的数据源...")
    router_sources = data_source_router.data_sources
    logger.info(f"TET路由器中的数据源数: {len(router_sources)}")
    for source_id in sorted(router_sources.keys()):
        logger.info(f"  - {source_id}")

    logger.info("\n步骤5: 分析差异原因...")
    logger.info(f"PluginManager加载: {len(all_plugins)} 个插件")
    logger.info(f"PluginCenter识别: {len(data_source_plugins)} 个数据源插件")
    logger.info(f"TET路由器注册: {len(router_sources)} 个数据源")

    # 找出被过滤掉的插件
    filtered_out = set(all_plugins.keys()) - set(data_source_plugins.keys())
    logger.info(f"\n被过滤掉的插件 ({len(filtered_out)} 个):")
    for plugin_name in sorted(filtered_out):
        plugin_instance = all_plugins[plugin_name]
        class_name = plugin_instance.__class__.__name__ if plugin_instance else "None"

        # 检查为什么被过滤
        reasons = []

        # 检查接口实现
        from plugins.plugin_interface import IDataSourcePlugin
        if not isinstance(plugin_instance, IDataSourcePlugin):
            reasons.append("未实现IDataSourcePlugin接口")

        # 检查必要方法
        if not hasattr(plugin_instance, 'get_supported_data_types'):
            reasons.append("缺少get_supported_data_types方法")
        if not hasattr(plugin_instance, 'fetch_data'):
            reasons.append("缺少fetch_data方法")

        # 检查plugin_info
        if hasattr(plugin_instance, 'get_plugin_info'):
            try:
                info = plugin_instance.get_plugin_info()
                if hasattr(info, 'plugin_type'):
                    from core.plugin_types import PluginType
                    if info.plugin_type != PluginType.DATA_SOURCE:
                        reasons.append(f"插件类型不是DATA_SOURCE: {info.plugin_type}")
            except Exception as e:
                reasons.append(f"调用get_plugin_info失败: {e}")

        logger.warning(f"  - {plugin_name} ({class_name})")
        for reason in reasons:
            logger.warning(f"      原因: {reason}")

    logger.info("\n步骤6: 详细检查几个关键的data_sources插件...")
    critical_plugins = [
        'data_sources.eastmoney_plugin',
        'data_sources.akshare_plugin',
        'data_sources.tongdaxin_plugin',
        'data_sources.sina_plugin'
    ]

    for plugin_name in critical_plugins:
        if plugin_name in all_plugins:
            plugin_instance = all_plugins[plugin_name]
            logger.info(f"\n检查插件: {plugin_name}")
            logger.info(f"  类名: {plugin_instance.__class__.__name__}")
            logger.info(f"  实现IDataSourcePlugin: {isinstance(plugin_instance, IDataSourcePlugin)}")
            logger.info(f"  有get_supported_data_types: {hasattr(plugin_instance, 'get_supported_data_types')}")
            logger.info(f"  有fetch_data: {hasattr(plugin_instance, 'fetch_data')}")
            logger.info(f"  有get_plugin_info: {hasattr(plugin_instance, 'get_plugin_info')}")

            if hasattr(plugin_instance, 'get_plugin_info'):
                try:
                    info = plugin_instance.get_plugin_info()
                    logger.info(f"  plugin_info.name: {info.name}")
                    logger.info(f"  plugin_info.plugin_type: {info.plugin_type if hasattr(info, 'plugin_type') else 'N/A'}")
                except Exception as e:
                    logger.error(f"  获取plugin_info失败: {e}")

            if hasattr(plugin_instance, 'get_supported_data_types'):
                try:
                    data_types = plugin_instance.get_supported_data_types()
                    logger.info(f"  支持的数据类型: {data_types}")
                except Exception as e:
                    logger.error(f"  获取支持的数据类型失败: {e}")

            # 检查是否被PluginCenter识别为数据源插件
            if plugin_name in data_source_plugins:
                logger.success(f"  ✓ 已被PluginCenter识别为数据源插件")
            else:
                logger.error(f"  ✗ 未被PluginCenter识别为数据源插件")
        else:
            logger.warning(f"\n插件未被PluginManager加载: {plugin_name}")


def main():
    """主函数"""
    try:
        simulate_plugin_loading()
    except Exception as e:
        logger.error(f"诊断过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
