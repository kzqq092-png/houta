#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIkyuu-UI 重构后系统快速测试脚本

用于验证重构后的模块化系统是否正常工作
"""

import sys
import traceback
from datetime import datetime


def test_module_imports():
    """测试模块导入"""
    print("=" * 60)
    print("🧪 测试模块导入...")

    try:
        # 测试核心模块
        from gui.core import BaseTradingGUI, TradingGUICore
        print("✅ 核心模块导入成功")

        # 测试处理器模块
        from gui.handlers import MenuHandler, EventHandler, ChartHandler
        print("✅ 处理器模块导入成功")

        # 测试组件模块
        from gui.components import StatusBar, StockListWidget, GlobalExceptionHandler
        print("✅ 组件模块导入成功")

        # 测试面板模块
        from gui.panels import (
            BaseAnalysisPanel, AnalysisToolsPanel,
            LeftPanel, MiddlePanel, BottomPanel
        )
        print("✅ 面板模块导入成功")

        # 测试布局模块
        from gui.layouts import MainLayout
        print("✅ 布局模块导入成功")

        # 测试功能模块
        from gui.features import OptimizationFeatures
        print("✅ 功能模块导入成功")

        # 测试统一导入
        from gui.ui_components import (
            print_module_info, get_available_components,
            create_component, get_component_info
        )
        print("✅ 统一导入模块成功")

        return True

    except Exception as e:
        print(f"❌ 模块导入失败: {str(e)}")
        traceback.print_exc()
        return False


def test_component_factory():
    """测试组件工厂功能"""
    print("\n" + "=" * 60)
    print("🏭 测试组件工厂功能...")

    try:
        from gui.ui_components import (
            get_available_components, get_component_info,
            create_component
        )

        # 获取可用组件
        components = get_available_components()
        print(f"✅ 获取到 {len(components)} 类组件")

        # 测试组件信息查询
        info = get_component_info('StatusBar')
        if info:
            print(f"✅ 组件信息查询成功: {info['name']}")
        else:
            print("⚠️ 组件信息查询返回空")

        return True

    except Exception as e:
        print(f"❌ 组件工厂测试失败: {str(e)}")
        traceback.print_exc()
        return False


def test_module_info():
    """测试模块信息功能"""
    print("\n" + "=" * 60)
    print("📋 测试模块信息功能...")

    try:
        from gui.ui_components import print_module_info, MODULE_INFO

        print(f"✅ 模块版本: {MODULE_INFO['version']}")
        print(f"✅ 重构日期: {MODULE_INFO['refactored_date']}")
        print(f"✅ 组件总数: {MODULE_INFO['total_components']}")

        return True

    except Exception as e:
        print(f"❌ 模块信息测试失败: {str(e)}")
        traceback.print_exc()
        return False


def test_hikyuu_integration():
    """测试HIkyuu框架集成"""
    print("\n" + "=" * 60)
    print("🔗 测试HIkyuu框架集成...")

    try:
        # 这里只做基本的导入测试，避免完整初始化
        import hikyuu as hku
        print("✅ HIkyuu框架导入成功")

        # 测试策略系统
        from core.strategy.strategy_registry import StrategyRegistry
        print("✅ 策略系统导入成功")

        return True

    except Exception as e:
        print(f"❌ HIkyuu框架集成测试失败: {str(e)}")
        # 这里不打印完整traceback，因为HIkyuu初始化可能很长
        return False


def test_gui_components():
    """测试GUI组件创建（不显示窗口）"""
    print("\n" + "=" * 60)
    print("🖼️ 测试GUI组件创建...")

    try:
        from PyQt5.QtWidgets import QApplication
        from gui.components import StatusBar

        # 创建应用实例（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 测试状态栏创建
        status_bar = StatusBar()
        status_bar.set_status("测试状态")
        print("✅ 状态栏组件创建成功")

        # 清理
        status_bar.deleteLater()

        return True

    except Exception as e:
        print(f"❌ GUI组件测试失败: {str(e)}")
        traceback.print_exc()
        return False


def run_performance_test():
    """运行性能测试"""
    print("\n" + "=" * 60)
    print("⚡ 运行性能测试...")

    try:
        import time

        # 测试导入性能
        start_time = time.time()
        from gui.ui_components import get_available_components
        components = get_available_components()
        import_time = time.time() - start_time

        print(f"✅ 模块导入耗时: {import_time:.3f}秒")
        print(f"✅ 组件总数: {sum(len(items) for items in components.values())}")

        # 测试组件创建性能
        start_time = time.time()
        from gui.components import StatusBar
        for i in range(10):
            status_bar = StatusBar()
            status_bar.deleteLater()
        creation_time = time.time() - start_time

        print(f"✅ 10个组件创建耗时: {creation_time:.3f}秒")

        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 HIkyuu-UI 重构后系统测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 运行所有测试
    tests = [
        ("模块导入测试", test_module_imports),
        ("组件工厂测试", test_component_factory),
        ("模块信息测试", test_module_info),
        ("HIkyuu集成测试", test_hikyuu_integration),
        ("GUI组件测试", test_gui_components),
        ("性能测试", run_performance_test),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}执行异常: {str(e)}")
            results.append((test_name, False))

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1

    print("=" * 60)
    print(f"总计: {passed}/{total} 个测试通过")

    if passed == total:
        print("🎉 所有测试通过！重构后的系统运行正常！")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试执行异常: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
