#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应连接池系统初始化器

在系统启动时自动初始化并启动自适应连接池管理。

作者: AI Assistant
日期: 2025-10-13
"""

from loguru import logger
from typing import Optional

from .database.factorweave_analytics_db import get_analytics_db
from .database.adaptive_connection_pool import (
    AdaptiveConnectionPoolManager,
    AdaptivePoolConfig,
    start_adaptive_management
)
from .database.connection_pool_config import ConnectionPoolConfigManager
from .containers import get_service_container
from .services.config_service import ConfigService


# 全局管理器引用
_adaptive_manager: Optional[AdaptiveConnectionPoolManager] = None


def initialize_adaptive_pool() -> Optional[AdaptiveConnectionPoolManager]:
    """
    初始化自适应连接池管理

    此函数应在系统启动时调用，会：
    1. 从ConfigService加载配置
    2. 创建AdaptiveConnectionPoolManager
    3. 启动自适应管理

    Returns:
        AdaptiveConnectionPoolManager实例或None（如果禁用或失败）
    """
    global _adaptive_manager

    try:
        logger.info("🔄 初始化自适应连接池管理...")

        # 获取ConfigService
        try:
            container = get_service_container()
            config_service = container.resolve(ConfigService)
            config_manager = ConnectionPoolConfigManager(config_service)
        except Exception as e:
            logger.warning(f"无法获取ConfigService，使用默认配置: {e}")
            config_manager = None

        # 检查是否启用
        if config_manager and not config_manager.is_adaptive_enabled():
            logger.info("⏸️ 自适应连接池已禁用")
            return None

        # 加载配置
        if config_manager:
            adaptive_config_dict = config_manager.load_adaptive_config()
            adaptive_config = AdaptivePoolConfig(**adaptive_config_dict)
            logger.info(f"📋 已加载自适应配置: min={adaptive_config.min_pool_size}, max={adaptive_config.max_pool_size}")
        else:
            adaptive_config = AdaptivePoolConfig()  # 使用默认配置
            logger.info("📋 使用默认自适应配置")

        # 获取数据库实例
        db = get_analytics_db()

        # 创建并启动自适应管理器
        _adaptive_manager = AdaptiveConnectionPoolManager(db, adaptive_config)
        _adaptive_manager.start()

        logger.info("✅ 自适应连接池管理已成功初始化并启动")
        return _adaptive_manager

    except Exception as e:
        logger.error(f"❌ 初始化自适应连接池失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_adaptive_manager() -> Optional[AdaptiveConnectionPoolManager]:
    """获取全局自适应管理器实例"""
    return _adaptive_manager


def stop_adaptive_pool():
    """停止自适应连接池管理"""
    global _adaptive_manager

    if _adaptive_manager:
        try:
            _adaptive_manager.stop()
            logger.info("⏸️ 自适应连接池管理已停止")
        except Exception as e:
            logger.error(f"停止自适应管理失败: {e}")
        finally:
            _adaptive_manager = None
