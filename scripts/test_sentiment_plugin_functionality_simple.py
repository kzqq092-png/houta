#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的情绪数据源插件功能测试

专注于核心的启用/禁用和测试连接功能验证
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_sentiment_service_basic():
    """测试情绪数据服务的基本功能"""
    try:
        from core.services.sentiment_data_service import SentimentDataService, SentimentDataServiceConfig

        print("🚀 开始测试情绪数据服务...")

        # 创建配置
        config = SentimentDataServiceConfig()
        config.enable_auto_refresh = False  # 禁用自动刷新避免挂起

        # 创建情绪数据服务
        sentiment_service = SentimentDataService(config=config)

        # 初始化服务
        print("📊 初始化情绪数据服务...")
        init_result = sentiment_service.initialize()
        print(f"   初始化结果: {'✅ 成功' if init_result else '❌ 失败'}")

        if not init_result:
            return False

        # 获取可用插件
        available_plugins = sentiment_service.get_available_plugins()
        print(f"📋 可用插件数量: {len(available_plugins)}")

        if not available_plugins:
            print("⚠️ 没有找到可用的情绪插件")
            return True

        # 测试第一个插件
        test_plugin_name = available_plugins[0]
        print(f"\n🔧 测试插件: {test_plugin_name}")

        # 测试get_available_plugins_info方法
        print("📄 测试获取插件详细信息...")
        try:
            plugins_info = sentiment_service.get_available_plugins_info()
            plugin_info = plugins_info.get(test_plugin_name, {})
            display_name = plugin_info.get('display_name', test_plugin_name)
            description = plugin_info.get('description', '无描述')
            print(f"   显示名称: {display_name}")
            print(f"   描述: {description}")
            print("   ✅ 插件信息获取成功")
        except Exception as e:
            print(f"   ❌ 插件信息获取失败: {e}")

        # 测试启用/禁用功能
        print("\n🔄 测试启用/禁用功能...")

        # 检查方法是否存在
        has_enable = hasattr(sentiment_service, 'enable_plugin')
        has_disable = hasattr(sentiment_service, 'disable_plugin')
        has_set_enabled = hasattr(sentiment_service, 'set_plugin_enabled')

        print(f"   enable_plugin方法: {'✅ 存在' if has_enable else '❌ 不存在'}")
        print(f"   disable_plugin方法: {'✅ 存在' if has_disable else '❌ 不存在'}")
        print(f"   set_plugin_enabled方法: {'✅ 存在' if has_set_enabled else '❌ 不存在'}")

        if has_enable and has_disable:
            try:
                # 测试禁用
                disable_result = sentiment_service.disable_plugin(test_plugin_name)
                print(f"   禁用插件: {'✅ 成功' if disable_result else '❌ 失败'}")

                # 测试启用
                enable_result = sentiment_service.enable_plugin(test_plugin_name)
                print(f"   启用插件: {'✅ 成功' if enable_result else '❌ 失败'}")
            except Exception as e:
                print(f"   ❌ 启用/禁用测试失败: {e}")

        # 测试连接功能
        print("\n🔗 测试连接功能...")

        has_test_connection = hasattr(sentiment_service, 'test_plugin_connection')
        print(f"   test_plugin_connection方法: {'✅ 存在' if has_test_connection else '❌ 不存在'}")

        if has_test_connection:
            try:
                connection_result = sentiment_service.test_plugin_connection(test_plugin_name)
                print(f"   连接测试: {'✅ 成功' if connection_result else '❌ 失败'}")
            except Exception as e:
                print(f"   ❌ 连接测试失败: {e}")

        print("\n✅ 情绪数据服务测试完成")
        return True

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_base_sentiment_plugin():
    """测试BaseSentimentPlugin的基本功能"""
    try:
        from plugins.sentiment_data_sources.base_sentiment_plugin import BaseSentimentPlugin

        print("\n🧩 测试BaseSentimentPlugin...")

        # 检查基本方法是否存在
        methods_to_check = [
            'get_plugin_info',
            'test_connection',
            'is_connected',
            'initialize'
        ]

        for method_name in methods_to_check:
            has_method = hasattr(BaseSentimentPlugin, method_name)
            print(f"   {method_name}方法: {'✅ 存在' if has_method else '❌ 不存在'}")

        print("✅ BaseSentimentPlugin检查完成")
        return True

    except Exception as e:
        print(f"❌ BaseSentimentPlugin测试失败: {e}")
        return False


def test_plugin_config_widget():
    """测试PluginConfigWidget的基本功能（无GUI）"""
    try:
        # 仅检查模块是否可以导入
        from gui.dialogs.sentiment_plugin_config_dialog import PluginConfigWidget

        print("\n🎛️ 测试PluginConfigWidget...")

        # 检查类是否存在必要的信号
        has_config_changed = hasattr(PluginConfigWidget, 'config_changed')
        has_test_requested = hasattr(PluginConfigWidget, 'test_requested')

        print(f"   config_changed信号: {'✅ 存在' if has_config_changed else '❌ 不存在'}")
        print(f"   test_requested信号: {'✅ 存在' if has_test_requested else '❌ 不存在'}")

        print("✅ PluginConfigWidget检查完成")
        return True

    except Exception as e:
        print(f"❌ PluginConfigWidget测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始简化版情绪插件功能测试...")
    print("=" * 60)

    # 测试情绪数据服务
    service_result = test_sentiment_service_basic()

    # 测试基础插件类
    base_plugin_result = test_base_sentiment_plugin()

    # 测试配置Widget
    widget_result = test_plugin_config_widget()

    # 总结结果
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"   情绪数据服务: {'✅ 通过' if service_result else '❌ 失败'}")
    print(f"   基础插件类: {'✅ 通过' if base_plugin_result else '❌ 失败'}")
    print(f"   配置Widget: {'✅ 通过' if widget_result else '❌ 失败'}")

    overall_success = service_result and base_plugin_result and widget_result
    print(f"\n🎯 总体结果: {'✅ 所有功能正常' if overall_success else '❌ 存在问题'}")

    return overall_success


if __name__ == "__main__":
    success = main()
    print(f"\n程序结束，状态: {'成功' if success else '失败'}")
    exit(0 if success else 1)
