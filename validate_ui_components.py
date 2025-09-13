#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI组件验证脚本

验证数据管理UI组件是否正确创建和导入
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试导入"""
    results = []

    # 测试数据管理主组件
    try:
        from gui.widgets.data_management_widget import (
            DataManagementWidget, DataSourceManagementWidget,
            DownloadTaskWidget, DataQualityMonitorWidget
        )
        results.append("[OK] 数据管理主组件导入成功")
    except Exception as e:
        results.append(f"[ERROR] 数据管理主组件导入失败: {e}")

    # 测试智能数据缺失组件
    try:
        from gui.widgets.smart_data_missing_widget import (
            SmartDataMissingPrompt, SmartDataMissingIntegration
        )
        results.append("[OK] 智能数据缺失组件导入成功")
    except Exception as e:
        results.append(f"[ERROR] 智能数据缺失组件导入失败: {e}")

    # 测试数据管理对话框
    try:
        from gui.dialogs.data_management_dialog import (
            DataManagementDialog, QuickDataCheckDialog
        )
        results.append("[OK] 数据管理对话框导入成功")
    except Exception as e:
        results.append(f"[ERROR] 数据管理对话框导入失败: {e}")

    return results


def test_component_creation():
    """测试组件创建"""
    results = []

    try:
        # 导入PyQt5
        from PyQt5.QtWidgets import QApplication
        app = QApplication([])

        # 测试数据源管理组件创建
        try:
            from gui.widgets.data_management_widget import DataSourceManagementWidget
            widget = DataSourceManagementWidget()
            results.append("[OK] 数据源管理组件创建成功")
            widget.deleteLater()
        except Exception as e:
            results.append(f"[ERROR] 数据源管理组件创建失败: {e}")

        # 测试下载任务组件创建
        try:
            from gui.widgets.data_management_widget import DownloadTaskWidget
            widget = DownloadTaskWidget()
            results.append("[OK] 下载任务组件创建成功")
            widget.deleteLater()
        except Exception as e:
            results.append(f"[ERROR] 下载任务组件创建失败: {e}")

        # 测试数据质量监控组件创建
        try:
            from gui.widgets.data_management_widget import DataQualityMonitorWidget
            widget = DataQualityMonitorWidget()
            results.append("[OK] 数据质量监控组件创建成功")
            widget.deleteLater()
        except Exception as e:
            results.append(f"[ERROR] 数据质量监控组件创建失败: {e}")

        # 测试主数据管理组件创建
        try:
            from gui.widgets.data_management_widget import DataManagementWidget
            widget = DataManagementWidget()
            results.append("[OK] 数据管理主组件创建成功")
            widget.deleteLater()
        except Exception as e:
            results.append(f"[ERROR] 数据管理主组件创建失败: {e}")

        app.quit()

    except Exception as e:
        results.append(f"[ERROR] PyQt5应用创建失败: {e}")

    return results


def test_file_structure():
    """测试文件结构"""
    results = []

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 检查文件是否存在
    files_to_check = [
        "gui/widgets/data_management_widget.py",
        "gui/widgets/smart_data_missing_widget.py",
        "gui/dialogs/data_management_dialog.py"
    ]

    for file_path in files_to_check:
        full_path = os.path.join(script_dir, file_path)
        if os.path.exists(full_path):
            results.append(f"[OK] 文件存在: {file_path}")
        else:
            results.append(f"[ERROR] 文件缺失: {file_path}")

    return results


def main():
    """主函数"""
    print("=" * 60)
    print("FactorWeave-Quant 数据管理UI组件验证")
    print("=" * 60)

    # 测试文件结构
    print("\n[FILE] 文件结构检查:")
    file_results = test_file_structure()
    for result in file_results:
        print(f"  {result}")

    # 测试导入
    print("\n[IMPORT] 组件导入测试:")
    import_results = test_imports()
    for result in import_results:
        print(f"  {result}")

    # 测试组件创建
    print("\n[CREATE] 组件创建测试:")
    creation_results = test_component_creation()
    for result in creation_results:
        print(f"  {result}")

    # 统计结果
    all_results = file_results + import_results + creation_results
    success_count = len([r for r in all_results if "OK" in r])
    total_count = len(all_results)
    success_rate = (success_count / total_count) * 100

    print("\n" + "=" * 60)
    print("[SUMMARY] 验证结果统计:")
    print(f"  总测试项: {total_count}")
    print(f"  成功项目: {success_count}")
    print(f"  失败项目: {total_count - success_count}")
    print(f"  成功率: {success_rate:.1f}%")

    if success_rate >= 80:
        print("  [SUCCESS] 验证通过！UI组件基本可用")
    elif success_rate >= 60:
        print("  [WARNING] 部分通过，存在一些问题")
    else:
        print("  [ERROR] 验证失败，需要修复问题")

    print("=" * 60)


if __name__ == '__main__':
    main()
