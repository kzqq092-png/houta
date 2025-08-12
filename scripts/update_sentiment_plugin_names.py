#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新情绪数据源插件的中文名称和描述

此脚本将重新扫描所有情绪数据源插件，获取它们的中文名称和描述，
并将这些信息更新到数据库中，确保插件管理界面能正确显示中文信息。
"""

from importlib import import_module
from typing import Dict, List, Any
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def discover_sentiment_plugins() -> List[tuple]:
    """发现所有情绪数据源插件"""
    discovered = []

    try:
        from plugins.sentiment_data_sources.base_sentiment_plugin import BaseSentimentPlugin

        # 扫描sentiment_data_sources目录
        sentiment_dir = project_root / "plugins" / "sentiment_data_sources"

        if not sentiment_dir.exists():
            logger.warning(f"情绪数据源目录不存在: {sentiment_dir}")
            return []

        # 查找所有Python插件文件
        for plugin_file in sentiment_dir.glob("*_plugin.py"):
            if plugin_file.name.startswith("__") or plugin_file.name == "base_sentiment_plugin.py":
                continue

            plugin_name = plugin_file.stem
            module_name = f"plugins.sentiment_data_sources.{plugin_name}"

            try:
                # 导入模块
                module = import_module(module_name)

                # 查找插件类
                plugin_cls = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    try:
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseSentimentPlugin) and
                                attr is not BaseSentimentPlugin):
                            plugin_cls = attr
                            break
                    except Exception:
                        continue

                if plugin_cls:
                    discovered.append((plugin_name, module_name, plugin_cls))
                    logger.info(f"发现情绪数据源插件: {plugin_name}")
                else:
                    logger.warning(f"在模块 {module_name} 中未找到插件类")

            except Exception as e:
                logger.error(f"加载插件模块失败 {module_name}: {e}")
                continue

    except Exception as e:
        logger.error(f"发现插件失败: {e}")

    return discovered


def update_plugin_database():
    """更新插件数据库信息"""
    try:
        # 导入数据库服务
        from db.models.plugin_models import PluginDatabaseManager, PluginRecord, PluginType, PluginStatus

        # 初始化数据库管理器
        db_path = project_root / "db" / "hikyuu_system.db"
        db_manager = PluginDatabaseManager(str(db_path))

        # 发现所有情绪数据源插件
        plugins = discover_sentiment_plugins()

        if not plugins:
            logger.warning("未发现任何情绪数据源插件")
            return

        updated_count = 0

        for plugin_name, module_name, plugin_cls in plugins:
            try:
                # 创建插件实例获取信息
                instance = plugin_cls()

                # 获取插件信息
                if hasattr(instance, 'get_plugin_info'):
                    plugin_info = instance.get_plugin_info()
                    display_name = plugin_info.name
                    description = plugin_info.description
                    author = plugin_info.author
                    version = plugin_info.version
                    tags = plugin_info.tags
                else:
                    # 后备方案：使用metadata属性
                    metadata = getattr(instance, 'metadata', {})
                    display_name = metadata.get('name', plugin_name)
                    description = metadata.get('description', '')
                    author = metadata.get('author', '')
                    version = metadata.get('version', '1.0.0')
                    tags = metadata.get('tags', [])

                # 创建插件记录
                plugin_record = PluginRecord(
                    name=module_name,  # 使用模块名作为唯一标识
                    display_name=display_name,  # 中文显示名称
                    version=version,
                    plugin_type=PluginType.SENTIMENT.value,
                    status=PluginStatus.LOADED.value,  # 默认为已加载状态
                    description=description,
                    author=author,
                    install_path=f"plugins/sentiment_data_sources/{plugin_name}.py",
                    entry_point=f"{module_name}:{plugin_cls.__name__}",
                    tags=str(tags) if isinstance(tags, list) else tags,
                    dependencies="[]"
                )

                # 注册到数据库
                plugin_id = db_manager.register_plugin(plugin_record)
                logger.info(f"✅ 更新插件: {display_name} (ID: {plugin_id})")
                updated_count += 1

            except Exception as e:
                logger.error(f"❌ 更新插件失败 {plugin_name}: {e}")
                continue

        logger.info(f"🎉 成功更新 {updated_count} 个情绪数据源插件")

    except Exception as e:
        logger.error(f"更新数据库失败: {e}")
        raise


def main():
    """主函数"""
    logger.info("开始更新情绪数据源插件的中文名称...")

    try:
        update_plugin_database()
        logger.info("✅ 更新完成")
    except Exception as e:
        logger.error(f"❌ 更新失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
