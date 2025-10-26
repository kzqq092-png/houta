#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TET Framework Optimization
TET框架优化

基于原有TET框架的插件管理功能，优化数据获取流程。
移除不必要的重复管理器，直接使用原有的PluginCenter和UniPluginDataManager。

作者: FactorWeave-Quant Team
版本: 1.0.0
日期: 2024
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from core.services.uni_plugin_data_manager import UniPluginDataManager, RequestContext
from core.plugin_center import PluginCenter
from core.tet_data_pipeline import StandardQuery, StandardData
from core.plugin_types import DataType, AssetType

logger = logger.bind(module=__name__)


class TETFrameworkOptimizer:
    """
    TET框架优化器

    基于原有TET框架功能，提供优化的数据获取接口。
    不重复造轮子，直接使用现有的PluginCenter和UniPluginDataManager。
    """

    def __init__(self, uni_plugin_manager: UniPluginDataManager):
        self.uni_plugin_manager = uni_plugin_manager
        self.plugin_center = uni_plugin_manager.plugin_center
        logger.info("TET框架优化器初始化完成，基于原有TET框架")

    async def get_data_via_tet(self, query: StandardQuery) -> Any:
        """
        通过TET框架获取数据

        直接使用原有的UniPluginDataManager，无需额外的管理器
        """
        logger.info(f"通过原有TET框架获取数据: {query.symbol} - {query.data_type.value}")

        try:
            # 使用原有的TET框架创建请求上下文
            context = await self.uni_plugin_manager.create_request_context(query)

            # 通过原有的TET框架执行数据请求
            result = await self.uni_plugin_manager.execute_data_request(context)

            logger.info(f"TET框架数据获取成功: {query.symbol} - {query.data_type.value}")
            return result

        except Exception as e:
            logger.error(f"TET框架数据获取失败: {e}")
            return None

    def get_plugin_capabilities(self) -> Dict[str, Any]:
        """
        获取插件能力信息

        使用原有PluginCenter的能力索引功能
        """
        return {
            'registered_plugins': len(self.plugin_center.data_source_plugins),
            'plugin_capabilities': self.plugin_center.plugin_capabilities,
            'capability_index': dict(self.plugin_center._capability_index),
            'health_status': self.plugin_center.plugin_health
        }

    async def refresh_plugin_registry(self) -> Dict[str, str]:
        """
        刷新插件注册

        使用原有PluginCenter的自动发现功能
        """
        logger.info("刷新插件注册...")
        return self.plugin_center.discover_and_register_plugins()

    def get_plugins_for_data_type(self, data_type: DataType, asset_type: AssetType) -> List[str]:
        """
        根据数据类型获取支持的插件

        使用原有PluginCenter的能力索引
        """
        capability_key = (data_type, asset_type)
        return self.plugin_center._capability_index.get(capability_key, [])

    async def health_check_all_plugins(self) -> Dict[str, Any]:
        """
        检查所有插件健康状态

        使用原有PluginCenter的健康检查功能
        """
        logger.info("执行全插件健康检查...")

        # 触发健康检查
        await self.plugin_center.perform_health_checks()

        return {
            'health_results': self.plugin_center.plugin_health,
            'plugin_metrics': self.plugin_center.plugin_metrics,
            'last_check_time': self.plugin_center.last_health_check
        }

# 正确的使用方式示例


async def correct_usage_example():
    """
    正确使用原有TET框架的示例
    """
    # 1. 使用原有的UniPluginDataManager
    # uni_plugin_manager = get_existing_uni_plugin_manager()

    # 2. 创建优化器（可选，主要用于便捷接口）
    # optimizer = TETFrameworkOptimizer(uni_plugin_manager)

    # 3. 直接通过TET框架获取数据
    query = StandardQuery(
        symbol="000001",
        data_type=DataType.REAL_TIME_QUOTE,
        asset_type=AssetType.STOCK_A
    )

    # 方式1：直接使用UniPluginDataManager（推荐）
    # context = await uni_plugin_manager.create_request_context(query)
    # result = await uni_plugin_manager.execute_data_request(context)

    # 方式2：通过优化器（可选的便捷接口）
    # result = await optimizer.get_data_via_tet(query)

    logger.info("正确使用原有TET框架获取数据")


def remove_unnecessary_components():
    """
    移除不必要的重复组件

    应该删除的文件：
    - core/services/unified_broker_plugin_manager.py (重复功能)
    - 各种自定义的插件管理器 (如果有的话)

    应该保留和使用的原有组件：
    - core/plugin_center.py (插件中心)
    - core/services/uni_plugin_data_manager.py (统一插件数据管理器)
    - core/tet_router_engine.py (TET路由引擎)
    - core/tet_data_pipeline.py (TET数据管道)
    """
    logger.info("建议移除重复的插件管理组件，使用原有TET框架")


if __name__ == "__main__":
    import asyncio

    # 运行正确使用示例
    asyncio.run(correct_usage_example())

    # 提示移除重复组件
    remove_unnecessary_components()
