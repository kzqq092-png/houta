#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试菜单集成
验证增强版数据导入是否正确集成到主菜单中
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_menu_integration():
    """测试菜单集成"""
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        from gui.menu_bar import MainMenuBar

        app = QApplication(sys.argv)

        # 创建主窗口
        main_window = QMainWindow()
        main_window.setWindowTitle("菜单集成测试")
        main_window.setGeometry(100, 100, 800, 600)

        # 创建菜单栏
        menu_bar = MainMenuBar(parent=main_window)
        main_window.setMenuBar(menu_bar)

        # 检查增强版数据导入菜单项是否存在
        if hasattr(menu_bar, 'enhanced_import_action'):
            print("✅ 增强版数据导入菜单项已成功添加")
            print(f"   菜单文本: {menu_bar.enhanced_import_action.text()}")
            print(f"   快捷键: {menu_bar.enhanced_import_action.shortcut().toString()}")
            print(f"   状态提示: {menu_bar.enhanced_import_action.statusTip()}")
        else:
            print("❌ 增强版数据导入菜单项未找到")

        # 检查处理方法是否存在
        if hasattr(menu_bar, '_on_enhanced_import'):
            print("✅ 增强版数据导入处理方法已添加")
        else:
            print("❌ 增强版数据导入处理方法未找到")

        # 显示主窗口
        main_window.show()

        print("\n🚀 菜单集成测试完成！")
        print("请在菜单栏中查看：数据 -> 数据导入 -> 🚀 增强版智能导入")
        print("快捷键：Ctrl+Alt+I")

        # 运行应用程序
        sys.exit(app.exec_())

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保所有依赖项已正确安装")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_menu_integration()
