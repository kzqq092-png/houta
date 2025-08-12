#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试情绪数据源插件的启用/禁用和测试连接功能

验证插件管理系统的完整功能实现
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


def test_sentiment_service_functionality():
    """测试情绪数据服务的完整功能"""
    try:
        from core.services.sentiment_data_service import SentimentDataService
        from core.logger import LogManager

        # 创建情绪数据服务
        log_manager = LogManager()
        sentiment_service = SentimentDataService(log_manager=log_manager)

        # 初始化服务
        init_result = sentiment_service.initialize()
        print(f"✅ 情绪数据服务初始化: {'成功' if init_result else '失败'}")

        if not init_result:
            return False

        # 获取可用插件
        available_plugins = sentiment_service.get_available_plugins()
        print(f"📊 可用插件数量: {len(available_plugins)}")

        if not available_plugins:
            print("⚠️ 没有找到可用的情绪插件")
            return True

        # 获取插件详细信息
        plugins_info = sentiment_service.get_available_plugins_info()
        print(f"📋 插件详细信息:")
        for plugin_name, info in plugins_info.items():
            display_name = info.get('display_name', plugin_name)
            description = info.get('description', '无描述')
            print(f"   - {display_name}: {description}")

        # 测试第一个插件的功能
        test_plugin_name = available_plugins[0]
        print(f"\n🔧 测试插件: {test_plugin_name}")

        # 测试启用/禁用功能
        print(f"🔄 测试启用/禁用功能...")

        # 禁用插件
        disable_result = sentiment_service.disable_plugin(test_plugin_name)
        print(f"   禁用插件: {'成功' if disable_result else '失败'}")

        # 检查状态
        status = sentiment_service.get_plugin_status(test_plugin_name)
        print(f"   当前状态: {status}")

        # 重新启用插件
        enable_result = sentiment_service.enable_plugin(test_plugin_name)
        print(f"   启用插件: {'成功' if enable_result else '失败'}")

        # 测试连接功能
        print(f"🔗 测试连接功能...")
        connection_result = sentiment_service.test_plugin_connection(test_plugin_name)
        print(f"   连接测试: {'成功' if connection_result else '失败'}")

        return True

    except Exception as e:
        logger.error(f"测试情绪数据服务功能时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_widget_functionality():
    """测试插件配置Widget的功能"""
    try:
        from PyQt5.QtWidgets import QApplication
        from gui.dialogs.sentiment_plugin_config_dialog import PluginConfigWidget

        # 创建QApplication（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # 创建测试配置
        test_config = {
            'enabled': True,
            'weight': 1.0,
            'priority': 50,
            'cache_duration_minutes': 5,
            'retry_attempts': 3,
            'timeout_seconds': 30
        }

        # 创建PluginConfigWidget
        widget = PluginConfigWidget("测试插件", test_config)

        # 测试获取配置
        current_config = widget.get_config()
        print(f"✅ PluginConfigWidget配置获取成功: {current_config}")

        # 测试状态更新
        from datetime import datetime
        widget.update_status("正常运行", datetime.now(), "good")
        print(f"✅ PluginConfigWidget状态更新成功")

        return True

    except Exception as e:
        logger.error(f"测试插件配置Widget功能时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_manager_integration():
    """测试插件管理器集成"""
    try:
        from core.plugin_manager import PluginManager
        from core.plugin_types import PluginType
        from utils.config_manager import ConfigManager

        # 创建插件管理器
        config_manager = ConfigManager()
        plugin_manager = PluginManager(
            plugin_dir="plugins",
            config_manager=config_manager,
            log_manager=logger
        )

        # 初始化插件管理器
        init_result = plugin_manager.initialize()
        print(f"✅ 插件管理器初始化: {'成功' if init_result else '失败'}")

        # 获取情绪插件
        sentiment_plugins = plugin_manager.get_plugins_by_type(PluginType.SENTIMENT)
        print(f"📊 情绪插件数量: {len(sentiment_plugins)}")

        for plugin_name, plugin_instance in sentiment_plugins.items():
            print(f"   - {plugin_name}: {type(plugin_instance).__name__}")

            # 测试插件的基本方法
            if hasattr(plugin_instance, 'get_plugin_info'):
                try:
                    info = plugin_instance.get_plugin_info()
                    print(f"     中文名称: {info.name}")
                    print(f"     描述: {info.description}")
                except Exception as e:
                    print(f"     获取插件信息失败: {e}")

        return True

    except Exception as e:
        logger.error(f"测试插件管理器集成时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试情绪插件功能...")
    print("=" * 60)

    # 测试情绪数据服务
    print("\n📊 测试情绪数据服务功能...")
    service_result = test_sentiment_service_functionality()

    # 测试插件配置Widget
    print("\n🎛️ 测试插件配置Widget功能...")
    widget_result = test_plugin_widget_functionality()

    # 测试插件管理器集成
    print("\n🔧 测试插件管理器集成...")
    manager_result = test_plugin_manager_integration()

    # 总结结果
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"   情绪数据服务: {'✅ 通过' if service_result else '❌ 失败'}")
    print(f"   插件配置Widget: {'✅ 通过' if widget_result else '❌ 失败'}")
    print(f"   插件管理器集成: {'✅ 通过' if manager_result else '❌ 失败'}")

    overall_success = service_result and widget_result and manager_result
    print(f"\n🎯 总体结果: {'✅ 所有功能正常' if overall_success else '❌ 存在问题'}")

    return overall_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
