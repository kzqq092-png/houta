#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试情绪数据源插件的中文名称显示

验证插件管理器和情绪数据服务是否能正确显示中文名称
"""

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


def test_plugin_manager_sentiment_plugins():
    """测试插件管理器的情绪插件显示"""
    try:
        from core.plugin_manager import PluginManager
        from core.plugin_types import PluginType

        # 创建插件管理器
        plugin_manager = PluginManager()
        plugin_manager.initialize()

        # 获取情绪插件
        sentiment_plugins = plugin_manager.get_plugins_by_type(PluginType.SENTIMENT)

        logger.info(f"🔍 插件管理器中发现 {len(sentiment_plugins)} 个情绪插件:")
        for plugin in sentiment_plugins:
            logger.info(f"  - {plugin}")

        # 获取增强插件信息
        enhanced_plugins = plugin_manager.get_all_enhanced_plugins()
        sentiment_enhanced = {k: v for k, v in enhanced_plugins.items()
                              if v.plugin_type and str(v.plugin_type) == 'sentiment'}

        logger.info(f"🎯 增强插件信息中的情绪插件 ({len(sentiment_enhanced)} 个):")
        for name, info in sentiment_enhanced.items():
            logger.info(f"  - {name}: {info.name} ({info.description})")

        return len(sentiment_enhanced) > 0

    except Exception as e:
        logger.error(f"❌ 测试插件管理器失败: {e}")
        return False


def test_sentiment_data_service():
    """测试情绪数据服务的插件显示"""
    try:
        from core.services.sentiment_data_service import SentimentDataService
        from core.plugin_manager import PluginManager

        # 创建插件管理器
        plugin_manager = PluginManager()
        plugin_manager.initialize()

        # 创建情绪数据服务
        sentiment_service = SentimentDataService(plugin_manager=plugin_manager)
        sentiment_service.initialize()

        # 测试旧方法
        plugins = sentiment_service.get_available_plugins()
        logger.info(f"📋 情绪数据服务中的插件 ({len(plugins)} 个):")
        for plugin_name in plugins:
            logger.info(f"  - {plugin_name}")

        # 测试新方法
        if hasattr(sentiment_service, 'get_available_plugins_info'):
            plugins_info = sentiment_service.get_available_plugins_info()
            logger.info(f"🎨 情绪插件详细信息 ({len(plugins_info)} 个):")
            for plugin_name, info in plugins_info.items():
                display_name = info.get('display_name', plugin_name)
                description = info.get('description', '')
                logger.info(f"  - {plugin_name} -> {display_name}")
                logger.info(f"    描述: {description}")
        else:
            logger.warning("⚠️ 新的get_available_plugins_info方法不可用")
            return False

        return len(plugins) > 0

    except Exception as e:
        logger.error(f"❌ 测试情绪数据服务失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_plugins():
    """测试单个插件的get_plugin_info方法"""
    try:
        from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
        from plugins.sentiment_data_sources.fmp_sentiment_plugin import FMPSentimentPlugin

        plugins_to_test = [
            ('AkShare', AkShareSentimentPlugin),
            ('FMP', FMPSentimentPlugin)
        ]

        logger.info("🧪 测试单个插件的get_plugin_info方法:")

        for name, plugin_class in plugins_to_test:
            try:
                instance = plugin_class()

                if hasattr(instance, 'get_plugin_info'):
                    info = instance.get_plugin_info()
                    logger.info(f"  ✅ {name}插件:")
                    logger.info(f"    名称: {info.name}")
                    logger.info(f"    描述: {info.description}")
                    logger.info(f"    作者: {info.author}")
                    logger.info(f"    版本: {info.version}")
                else:
                    logger.warning(f"  ⚠️ {name}插件没有get_plugin_info方法")

                # 测试metadata属性
                if hasattr(instance, 'metadata'):
                    meta = instance.metadata
                    logger.info(f"    metadata名称: {meta.get('name', 'N/A')}")

            except Exception as e:
                logger.error(f"  ❌ 测试{name}插件失败: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试单个插件失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始测试情绪数据源插件的中文名称显示...")

    # 测试插件管理器
    logger.info("\n" + "="*50)
    logger.info("测试 1: 插件管理器")
    logger.info("="*50)
    test1_ok = test_plugin_manager_sentiment_plugins()

    # 测试情绪数据服务
    logger.info("\n" + "="*50)
    logger.info("测试 2: 情绪数据服务")
    logger.info("="*50)
    test2_ok = test_sentiment_data_service()

    # 测试单个插件
    logger.info("\n" + "="*50)
    logger.info("测试 3: 单个插件")
    logger.info("="*50)
    test3_ok = test_individual_plugins()

    # 总结
    logger.info("\n" + "="*50)
    logger.info("测试结果总结")
    logger.info("="*50)
    logger.info(f"插件管理器: {'✅ 通过' if test1_ok else '❌ 失败'}")
    logger.info(f"情绪数据服务: {'✅ 通过' if test2_ok else '❌ 失败'}")
    logger.info(f"单个插件: {'✅ 通过' if test3_ok else '❌ 失败'}")

    if all([test1_ok, test2_ok, test3_ok]):
        logger.info("🎉 所有测试通过！情绪数据源插件的中文名称显示应该正常")
    else:
        logger.warning("⚠️ 部分测试失败，可能需要进一步调试")


if __name__ == "__main__":
    main()
