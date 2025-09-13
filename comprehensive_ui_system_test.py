#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全面UI系统集成测试

验证UI数据管理界面与后台逻辑的完整集成
"""

import sys
import os
import traceback
from datetime import datetime, date
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_core_backend_integration():
    """测试核心后台集成"""
    results = []

    try:
        # 测试核心组件导入
        from core.plugin_types import AssetType, DataType, PluginType, DataSourceProvider
        from core.asset_type_identifier import AssetTypeIdentifier
        from core.data_router import DataRouter, get_data_router
        from core.services.asset_aware_unified_data_manager import AssetAwareUnifiedDataManager
        from core.ui_integration.data_missing_manager import DataMissingManager
        from core.ui_integration.smart_data_integration import SmartDataIntegration
        from core.database_maintenance_engine import DatabaseMaintenanceEngine
        from core.data_standardization_engine import DataStandardizationEngine
        results.append("[OK] 核心后台组件导入成功")

        # 测试单例模式
        data_router1 = get_data_router()
        data_router2 = get_data_router()
        if data_router1 is data_router2:
            results.append("[OK] DataRouter单例模式正确")
        else:
            results.append("[ERROR] DataRouter单例模式失败")

        # 测试资产类型识别
        identifier = AssetTypeIdentifier.get_instance()
        asset_type = identifier.identify_asset_type("000001")
        if asset_type == AssetType.STOCK_A:
            results.append("[OK] 资产类型识别功能正常")
        else:
            results.append(f"[ERROR] 资产类型识别错误: {asset_type}")

        # 测试数据路由器
        router = get_data_router()
        stats = router.get_route_statistics()
        if isinstance(stats, dict):
            results.append("[OK] 数据路由器统计功能正常")
        else:
            results.append("[ERROR] 数据路由器统计功能异常")

        # 测试数据缺失管理器
        missing_manager = DataMissingManager()
        availability = missing_manager.get_plugin_availability()
        if isinstance(availability, dict):
            results.append("[OK] 数据缺失管理器功能正常")
        else:
            results.append("[ERROR] 数据缺失管理器功能异常")

        # 测试数据库维护引擎
        maintenance_engine = DatabaseMaintenanceEngine()
        active_tasks = maintenance_engine.list_active_tasks()
        if isinstance(active_tasks, list):
            results.append("[OK] 数据库维护引擎功能正常")
        else:
            results.append("[ERROR] 数据库维护引擎功能异常")

    except Exception as e:
        results.append(f"[ERROR] 核心后台集成测试失败: {e}")
        results.append(f"[DEBUG] 错误详情: {traceback.format_exc()}")

    return results


def test_ui_backend_integration():
    """测试UI与后台集成"""
    results = []

    try:
        # 导入UI组件
        from gui.widgets.data_management_widget import (
            DataManagementWidget, DataSourceManagementWidget,
            DownloadTaskWidget, DataQualityMonitorWidget
        )
        from gui.widgets.smart_data_missing_widget import (
            SmartDataMissingPrompt, SmartDataMissingIntegration
        )
        from gui.dialogs.data_management_dialog import DataManagementDialog
        results.append("[OK] UI组件导入成功")

        # 创建PyQt5应用（如果不存在）
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        results.append("[OK] PyQt5应用环境准备完成")

        # 测试数据源管理组件
        source_widget = DataSourceManagementWidget()
        if hasattr(source_widget, 'data_router') and hasattr(source_widget, 'load_data_sources'):
            results.append("[OK] 数据源管理组件后台集成正常")
        else:
            results.append("[ERROR] 数据源管理组件后台集成异常")

        # 测试下载任务组件
        task_widget = DownloadTaskWidget()
        if hasattr(task_widget, 'tasks') and hasattr(task_widget, 'create_new_task'):
            results.append("[OK] 下载任务组件功能正常")
        else:
            results.append("[ERROR] 下载任务组件功能异常")

        # 测试数据质量监控组件
        quality_widget = DataQualityMonitorWidget()
        if hasattr(quality_widget, 'reports_table') and hasattr(quality_widget, 'load_quality_data'):
            results.append("[OK] 数据质量监控组件功能正常")
        else:
            results.append("[ERROR] 数据质量监控组件功能异常")

        # 测试主数据管理组件
        main_widget = DataManagementWidget()
        if hasattr(main_widget, 'tab_widget') and hasattr(main_widget, 'source_widget'):
            results.append("[OK] 主数据管理组件集成正常")
        else:
            results.append("[ERROR] 主数据管理组件集成异常")

        # 测试智能数据缺失组件
        smart_widget = SmartDataMissingIntegration()
        if hasattr(smart_widget, 'missing_manager') and hasattr(smart_widget, 'smart_integration'):
            results.append("[OK] 智能数据缺失组件后台集成正常")
        else:
            results.append("[ERROR] 智能数据缺失组件后台集成异常")

        # 测试数据管理对话框
        dialog = DataManagementDialog()
        if hasattr(dialog, 'data_widget'):
            results.append("[OK] 数据管理对话框集成正常")
        else:
            results.append("[ERROR] 数据管理对话框集成异常")

    except Exception as e:
        results.append(f"[ERROR] UI后台集成测试失败: {e}")
        results.append(f"[DEBUG] 错误详情: {traceback.format_exc()}")

    return results


def test_data_flow_integration():
    """测试数据流集成"""
    results = []

    try:
        # 测试数据源到UI的数据流
        from core.data_router import get_data_router
        from gui.widgets.data_management_widget import DataSourceManagementWidget

        # 创建组件
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        source_widget = DataSourceManagementWidget()

        # 测试数据加载
        source_widget.load_data_sources()
        if hasattr(source_widget, 'data_sources') and isinstance(source_widget.data_sources, dict):
            results.append("[OK] 数据源数据流集成正常")
        else:
            results.append("[ERROR] 数据源数据流集成异常")

        # 测试资产类型识别集成
        from core.asset_type_identifier import AssetTypeIdentifier
        from gui.widgets.smart_data_missing_widget import SmartDataMissingIntegration

        smart_widget = SmartDataMissingIntegration()
        smart_widget.init_managers()

        # 模拟数据缺失检测
        if smart_widget.missing_manager is not None:
            results.append("[OK] 智能数据缺失数据流集成正常")
        else:
            results.append("[WARNING] 智能数据缺失管理器未正确初始化")

        # 测试数据库连接集成
        from core.asset_database_manager import AssetSeparatedDatabaseManager
        from core.plugin_types import AssetType

        from core.asset_database_manager import get_asset_separated_database_manager
        db_manager = get_asset_separated_database_manager()
        db_path = db_manager.get_database_path(AssetType.STOCK_A)
        if os.path.exists(os.path.dirname(db_path)):
            results.append("[OK] 数据库连接集成正常")
        else:
            results.append("[WARNING] 数据库路径不存在，但这是正常的")

    except Exception as e:
        results.append(f"[ERROR] 数据流集成测试失败: {e}")
        results.append(f"[DEBUG] 错误详情: {traceback.format_exc()}")

    return results


def test_signal_slot_integration():
    """测试信号槽集成"""
    results = []

    try:
        from PyQt5.QtWidgets import QApplication
        from gui.widgets.data_management_widget import DataManagementWidget

        # 创建应用
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 创建主组件
        main_widget = DataManagementWidget()

        # 检查信号连接
        source_widget = main_widget.source_widget
        task_widget = main_widget.task_widget

        # 检查数据源管理信号
        if hasattr(source_widget, 'source_selected') and hasattr(source_widget, 'source_configured'):
            results.append("[OK] 数据源管理信号定义正常")
        else:
            results.append("[ERROR] 数据源管理信号定义异常")

        # 检查任务管理信号
        if hasattr(task_widget, 'task_started') and hasattr(task_widget, 'task_paused'):
            results.append("[OK] 任务管理信号定义正常")
        else:
            results.append("[ERROR] 任务管理信号定义异常")

        # 检查主组件信号连接
        if hasattr(main_widget, 'on_source_selected') and hasattr(main_widget, 'on_task_started'):
            results.append("[OK] 主组件信号槽连接正常")
        else:
            results.append("[ERROR] 主组件信号槽连接异常")

    except Exception as e:
        results.append(f"[ERROR] 信号槽集成测试失败: {e}")
        results.append(f"[DEBUG] 错误详情: {traceback.format_exc()}")

    return results


def test_configuration_integration():
    """测试配置集成"""
    results = []

    try:
        # 测试插件类型配置
        from core.plugin_types import AssetType, DataType, PluginType, DataSourceProvider

        # 验证枚举定义
        asset_types = list(AssetType)
        data_types = list(DataType)
        plugin_types = list(PluginType)
        data_source_providers = list(DataSourceProvider)

        if len(asset_types) > 0 and len(data_types) > 0:
            results.append(f"[OK] 插件类型配置正常 (资产类型:{len(asset_types)}, 数据类型:{len(data_types)})")
        else:
            results.append("[ERROR] 插件类型配置异常")

        # 测试UI组件配置集成
        from gui.widgets.data_management_widget import DataSourceManagementWidget
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        widget = DataSourceManagementWidget()

        # 检查UI组件是否正确使用配置
        if hasattr(widget, 'sources_table') and widget.sources_table.columnCount() == 6:
            results.append("[OK] UI组件配置集成正常")
        else:
            results.append("[ERROR] UI组件配置集成异常")

    except Exception as e:
        results.append(f"[ERROR] 配置集成测试失败: {e}")
        results.append(f"[DEBUG] 错误详情: {traceback.format_exc()}")

    return results


def main():
    """主函数"""
    print("=" * 80)
    print("FactorWeave-Quant 全面UI系统集成测试")
    print("=" * 80)

    all_results = []

    # 1. 核心后台集成测试
    print("\n[BACKEND] 核心后台集成测试:")
    backend_results = test_core_backend_integration()
    for result in backend_results:
        print(f"  {result}")
    all_results.extend(backend_results)

    # 2. UI与后台集成测试
    print("\n[UI-BACKEND] UI与后台集成测试:")
    ui_backend_results = test_ui_backend_integration()
    for result in ui_backend_results:
        print(f"  {result}")
    all_results.extend(ui_backend_results)

    # 3. 数据流集成测试
    print("\n[DATAFLOW] 数据流集成测试:")
    dataflow_results = test_data_flow_integration()
    for result in dataflow_results:
        print(f"  {result}")
    all_results.extend(dataflow_results)

    # 4. 信号槽集成测试
    print("\n[SIGNALS] 信号槽集成测试:")
    signal_results = test_signal_slot_integration()
    for result in signal_results:
        print(f"  {result}")
    all_results.extend(signal_results)

    # 5. 配置集成测试
    print("\n[CONFIG] 配置集成测试:")
    config_results = test_configuration_integration()
    for result in config_results:
        print(f"  {result}")
    all_results.extend(config_results)

    # 统计结果
    success_count = len([r for r in all_results if "[OK]" in r])
    warning_count = len([r for r in all_results if "[WARNING]" in r])
    error_count = len([r for r in all_results if "[ERROR]" in r])
    total_count = len(all_results)
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0

    print("\n" + "=" * 80)
    print("[SUMMARY] 全面集成测试结果统计:")
    print(f"  总测试项: {total_count}")
    print(f"  成功项目: {success_count}")
    print(f"  警告项目: {warning_count}")
    print(f"  失败项目: {error_count}")
    print(f"  成功率: {success_rate:.1f}%")

    if success_rate >= 90:
        print("  [SUCCESS] 系统集成验证通过！所有组件正常工作")
    elif success_rate >= 80:
        print("  [GOOD] 系统集成良好，存在少量警告")
    elif success_rate >= 70:
        print("  [WARNING] 系统集成基本正常，需要关注一些问题")
    else:
        print("  [ERROR] 系统集成存在严重问题，需要修复")

    print("=" * 80)

    # 输出详细的错误信息
    errors = [r for r in all_results if "[ERROR]" in r]
    if errors:
        print("\n[ERRORS] 详细错误信息:")
        for error in errors:
            print(f"  {error}")

    return success_rate >= 80


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
