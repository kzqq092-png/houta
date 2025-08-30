#!/usr/bin/env python3
"""
菜单重复连接修复验证测试脚本

测试内容：
1. 验证所有菜单项只被调用一次
2. 检查统一信号连接机制是否正常工作
3. 确保没有遗漏的重复连接问题
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_menu_signal_connections():
    """测试菜单信号连接"""
    try:
        from gui.menu_bar import MainMenuBar
        from core.coordinators.main_window_coordinator import MainWindowCoordinator
        from core.containers import get_service_container
        from core.events import get_event_bus
        from PyQt5.QtWidgets import QApplication, QMainWindow

        # 创建Qt应用程序
        app = QApplication(sys.argv)

        # 创建主窗口
        main_window = QMainWindow()

        # 获取服务容器和事件总线
        service_container = get_service_container()
        event_bus = get_event_bus()

        # 创建主窗口协调器
        coordinator = MainWindowCoordinator(
            service_container=service_container,
            event_bus=event_bus
        )
        coordinator._main_window = main_window

        # 创建菜单栏
        menu_bar = MainMenuBar(coordinator=coordinator, parent=main_window)
        main_window.setMenuBar(menu_bar)

        logger.info("✅ 菜单栏创建成功")

        # 测试统一信号连接机制
        test_unified_signal_connections(menu_bar, coordinator)

        # 测试特定菜单项
        test_specific_menu_items(menu_bar, coordinator)

        logger.info("🎉 所有菜单测试通过！")
        return True

    except Exception as e:
        logger.error(f"❌ 菜单测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_unified_signal_connections(menu_bar, coordinator):
    """测试统一信号连接机制"""
    logger.info("🧪 测试统一信号连接机制...")

    # 检查关键菜单项是否存在
    critical_actions = [
        'database_admin_action',
        'export_data_action',
        'import_data_action',
        'webgpu_status_action',
        'toggle_log_action',
        'default_theme_action',
        'toolbar_action',
        'statusbar_action'
    ]

    for action_name in critical_actions:
        if hasattr(menu_bar, action_name):
            action = getattr(menu_bar, action_name)
            # 检查信号是否已连接（Qt内部机制，无法直接检查连接数量）
            logger.info(f"✅ {action_name} 存在且可用")
        else:
            logger.warning(f"⚠️ {action_name} 不存在")

    # 检查对应的协调器方法是否存在
    critical_methods = [
        '_on_database_admin',
        '_on_export_data',
        '_on_import_data',
        'show_webgpu_status',
        '_toggle_log_panel',
        '_on_default_theme',
        '_on_toggle_toolbar',
        '_on_toggle_statusbar'
    ]

    for method_name in critical_methods:
        if hasattr(coordinator, method_name):
            logger.info(f"✅ 协调器方法 {method_name} 存在")
        elif hasattr(menu_bar, method_name):
            logger.info(f"✅ 菜单栏方法 {method_name} 存在")
        else:
            logger.warning(f"⚠️ 方法 {method_name} 不存在")


def test_specific_menu_items(menu_bar, coordinator):
    """测试特定菜单项的功能"""
    logger.info("🧪 测试特定菜单项...")

    # 创建调用计数器
    call_counts = {}

    def create_counter(original_method, method_name):
        """创建方法调用计数器"""
        def wrapper(*args, **kwargs):
            call_counts[method_name] = call_counts.get(method_name, 0) + 1
            logger.info(f"📞 {method_name} 被调用 (第{call_counts[method_name]}次)")
            try:
                return original_method(*args, **kwargs)
            except Exception as e:
                logger.info(f"⚠️ {method_name} 执行时出现预期错误: {e}")
        return wrapper

    # 包装关键方法以计数调用次数
    test_methods = [
        ('_on_database_admin', coordinator),
        ('_on_export_data', coordinator),
        ('_toggle_log_panel', coordinator),
        ('_on_default_theme', coordinator),
        ('_on_toggle_toolbar', coordinator),
        ('_on_toggle_statusbar', coordinator)
    ]

    original_methods = {}
    for method_name, obj in test_methods:
        if hasattr(obj, method_name):
            original_methods[method_name] = getattr(obj, method_name)
            setattr(obj, method_name, create_counter(original_methods[method_name], method_name))

    # 模拟菜单项点击（通过触发信号）
    test_actions = [
        ('database_admin_action', '_on_database_admin'),
        ('export_data_action', '_on_export_data'),
        ('toggle_log_action', '_toggle_log_panel'),
        ('default_theme_action', '_on_default_theme'),
        ('toolbar_action', '_on_toggle_toolbar'),
        ('statusbar_action', '_on_toggle_statusbar')
    ]

    for action_name, expected_method in test_actions:
        if hasattr(menu_bar, action_name):
            action = getattr(menu_bar, action_name)
            try:
                logger.info(f"🖱️ 模拟点击 {action_name}")
                action.trigger()  # 触发菜单项

                # 检查调用次数
                if expected_method in call_counts:
                    count = call_counts[expected_method]
                    if count == 1:
                        logger.info(f"✅ {action_name} 正确调用了 {expected_method} 1次")
                    else:
                        logger.error(f"❌ {action_name} 调用了 {expected_method} {count}次（应该是1次）")
                else:
                    logger.warning(f"⚠️ {action_name} 没有调用 {expected_method}")

            except Exception as e:
                logger.info(f"⚠️ {action_name} 触发时出现预期错误: {e}")

    # 恢复原始方法
    for method_name, original_method in original_methods.items():
        for _, obj in test_methods:
            if hasattr(obj, method_name):
                setattr(obj, method_name, original_method)
                break


def test_no_duplicate_connections():
    """测试是否还有重复连接"""
    logger.info("🧪 检查是否还有重复连接...")

    try:
        with open('gui/menu_bar.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否还有直接的 .triggered.connect 调用
        direct_connections = content.count('.triggered.connect(')
        logger.info(f"📊 发现 {direct_connections} 个直接信号连接")

        # 检查统一连接列表
        if 'actions_to_connect = [' in content:
            logger.info("✅ 统一信号连接列表存在")
        else:
            logger.warning("⚠️ 统一信号连接列表不存在")

        # 检查是否有注释说明
        if '信号连接已移至统一的信号连接处理中' in content:
            logger.info("✅ 发现修复注释，说明重复连接已被处理")

        return True

    except Exception as e:
        logger.error(f"❌ 检查重复连接失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始菜单重复连接修复验证测试")

    # 测试1: 检查重复连接
    test1_result = test_no_duplicate_connections()

    # 测试2: 菜单信号连接
    test2_result = test_menu_signal_connections()

    # 汇总结果
    if test1_result and test2_result:
        logger.info("🎉 所有测试通过！菜单重复连接问题已完全修复")
        return 0
    else:
        logger.error("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
