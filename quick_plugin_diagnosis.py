#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速插件诊断脚本
识别为什么只有1个插件可用而不是8个
"""

from loguru import logger
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主诊断函数"""
    try:
        logger.info("=== 快速插件诊断开始 ===")

        # 1. 获取统一数据管理器
        from core.services.unified_data_manager import get_unified_data_manager
        unified_manager = get_unified_data_manager()

        if not unified_manager:
            logger.error("❌ 无法获取统一数据管理器")
            return

        logger.info("✅ 统一数据管理器获取成功")

        # 2. 获取UniPluginDataManager
        if hasattr(unified_manager, '_uni_plugin_manager'):
            uni_plugin_manager = unified_manager._uni_plugin_manager
            logger.info("✅ UniPluginDataManager获取成功")
        else:
            logger.error("❌ 无法获取UniPluginDataManager")
            return

        # 3. 获取插件中心
        if hasattr(uni_plugin_manager, 'plugin_center'):
            plugin_center = uni_plugin_manager.plugin_center
            logger.info("✅ PluginCenter获取成功")
        else:
            logger.error("❌ 无法获取PluginCenter")
            return

        # 4. 检查注册的插件
        if hasattr(plugin_center, 'data_source_plugins'):
            registered_plugins = plugin_center.data_source_plugins
            logger.info(f"📊 已注册的数据源插件数量: {len(registered_plugins)}")

            for plugin_id in registered_plugins.keys():
                logger.info(f"   - {plugin_id}")
        else:
            logger.warning("⚠️ PluginCenter没有data_source_plugins属性")

        # 5. 测试插件发现机制
        from core.plugin_types import DataType, AssetType

        logger.info("\n🔍 测试插件发现机制...")
        available_plugins = plugin_center.get_available_plugins(
            DataType.ASSET_LIST, AssetType.STOCK
        )

        logger.info(f"📈 可用插件数量: {len(available_plugins)}")
        for plugin_id in available_plugins:
            logger.info(f"   ✅ {plugin_id}")

        # 6. 分析为什么其他插件不可用
        logger.info(f"\n🔎 分析插件过滤原因...")

        if hasattr(plugin_center, '_is_plugin_available'):
            for plugin_id in registered_plugins.keys():
                if plugin_id not in available_plugins:
                    try:
                        is_available = plugin_center._is_plugin_available(plugin_id)
                        logger.warning(f"   ❌ {plugin_id}: 可用性检查={is_available}")

                        # 检查插件状态
                        if hasattr(plugin_center, 'plugin_status'):
                            status = plugin_center.plugin_status.get(plugin_id, "UNKNOWN")
                            logger.info(f"      状态: {status}")

                        # 检查健康状态
                        if hasattr(plugin_center, 'plugin_health'):
                            health = plugin_center.plugin_health.get(plugin_id)
                            if health:
                                logger.info(f"      健康: {health.is_healthy}, 消息: {health.message}")
                            else:
                                logger.warning(f"      健康: 无健康检查结果")

                    except Exception as e:
                        logger.error(f"   ❌ {plugin_id}: 检查失败 - {e}")

        # 7. 测试连接状态
        logger.info(f"\n🔗 测试插件连接状态...")

        if hasattr(uni_plugin_manager, '_get_connected_plugins'):
            try:
                from core.services.uni_plugin_data_manager import RequestContext
                context = RequestContext(
                    data_type=DataType.ASSET_LIST,
                    asset_type=AssetType.STOCK
                )
                connected_plugins = uni_plugin_manager._get_connected_plugins(available_plugins)
                logger.info(f"📡 已连接插件数量: {len(connected_plugins)}")
                for plugin_id in connected_plugins:
                    logger.info(f"   🔗 {plugin_id}")

            except Exception as e:
                logger.error(f"连接状态检查失败: {e}")

        logger.info("\n=== 快速插件诊断完成 ===")

    except Exception as e:
        logger.error(f"诊断过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
