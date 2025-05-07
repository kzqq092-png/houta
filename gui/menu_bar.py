"""
Menu bar for the trading system

This module contains the menu bar implementation for the trading system.
"""

from PyQt5.QtWidgets import (
    QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
    QInputDialog, QShortcut
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIcon
import traceback


class MainMenuBar(QMenuBar):
    """主菜单栏"""

    def __init__(self, parent=None):
        """初始化菜单栏

        Args:
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 初始化日志管理器
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                from core.logger import LogManager
                self.log_manager = LogManager()

            # 初始化UI
            self.init_ui()

            self.log_manager.info("菜单栏初始化完成")

        except Exception as e:
            print(f"初始化菜单栏失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化菜单栏失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def init_ui(self):
        """初始化菜单栏"""
        self.parent = self.parentWidget()

        # 创建菜单项
        self.file_menu = self.addMenu("文件(&F)")
        self.edit_menu = self.addMenu("编辑(&E)")
        self.view_menu = self.addMenu("视图(&V)")
        self.tools_menu = self.addMenu("工具(&T)")
        self.help_menu = self.addMenu("帮助(&H)")

        self.init_file_menu()
        self.init_edit_menu()
        self.init_view_menu()
        self.init_tools_menu()
        self.init_help_menu()

    def init_file_menu(self):
        """初始化文件菜单"""
        try:
            # 新建
            self.new_action = QAction(QIcon("icons/new.png"), "新建(&N)", self)
            self.new_action.setShortcut("Ctrl+N")
            self.new_action.setStatusTip("创建新的策略")
            self.file_menu.addAction(self.new_action)

            # 打开
            self.open_action = QAction(QIcon("icons/open.png"), "打开(&O)", self)
            self.open_action.setShortcut("Ctrl+O")
            self.open_action.setStatusTip("打开策略文件")
            self.file_menu.addAction(self.open_action)

            # 保存
            self.save_action = QAction(QIcon("icons/save.png"), "保存(&S)", self)
            self.save_action.setShortcut("Ctrl+S")
            self.save_action.setStatusTip("保存当前策略")
            self.file_menu.addAction(self.save_action)

            self.file_menu.addSeparator()

            # 最近打开的文件
            self.recent_menu = self.file_menu.addMenu("最近打开的文件")

            self.file_menu.addSeparator()

            # 退出
            self.exit_action = QAction("退出(&X)", self)
            self.exit_action.setShortcut("Alt+F4")
            self.exit_action.setStatusTip("退出程序")
            self.file_menu.addAction(self.exit_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化文件菜单失败: {str(e)}")

    def init_edit_menu(self):
        """初始化编辑菜单"""
        try:
            # 撤销
            self.undo_action = QAction(QIcon("icons/undo.png"), "撤销(&U)", self)
            self.undo_action.setShortcut("Ctrl+Z")
            self.edit_menu.addAction(self.undo_action)

            # 重做
            self.redo_action = QAction(QIcon("icons/redo.png"), "重做(&R)", self)
            self.redo_action.setShortcut("Ctrl+Y")
            self.edit_menu.addAction(self.redo_action)

            self.edit_menu.addSeparator()

            # 复制
            self.copy_action = QAction("复制(&C)", self)
            self.copy_action.setShortcut("Ctrl+C")
            self.edit_menu.addAction(self.copy_action)

            # 粘贴
            self.paste_action = QAction("粘贴(&V)", self)
            self.paste_action.setShortcut("Ctrl+V")
            self.edit_menu.addAction(self.paste_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化编辑菜单失败: {str(e)}")

    def init_view_menu(self):
        """初始化视图菜单"""
        try:
            # 工具栏
            self.toolbar_action = QAction("工具栏", self)
            self.toolbar_action.setCheckable(True)
            self.toolbar_action.setChecked(True)
            self.view_menu.addAction(self.toolbar_action)

            # 状态栏
            self.statusbar_action = QAction("状态栏", self)
            self.statusbar_action.setCheckable(True)
            self.statusbar_action.setChecked(True)
            self.view_menu.addAction(self.statusbar_action)

            self.view_menu.addSeparator()

            # 主题
            self.theme_menu = self.view_menu.addMenu("主题")
            self.light_theme_action = QAction("浅色", self)
            self.dark_theme_action = QAction("深色", self)
            self.theme_menu.addAction(self.light_theme_action)
            self.theme_menu.addAction(self.dark_theme_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化视图菜单失败: {str(e)}")

    def init_tools_menu(self):
        """初始化工具菜单"""
        try:
            # 分析
            self.analyze_action = QAction(
                QIcon("icons/analyze.png"), "分析", self)
            self.analyze_action.setStatusTip("分析当前股票")
            self.tools_menu.addAction(self.analyze_action)

            # 回测
            self.backtest_action = QAction(
                QIcon("icons/backtest.png"), "回测", self)
            self.backtest_action.setStatusTip("回测当前策略")
            self.tools_menu.addAction(self.backtest_action)

            # 优化
            self.optimize_action = QAction(
                QIcon("icons/optimize.png"), "优化", self)
            self.optimize_action.setStatusTip("优化策略参数")
            self.tools_menu.addAction(self.optimize_action)

            self.tools_menu.addSeparator()

            # 计算器
            self.calculator_action = QAction(
                QIcon("icons/calculator.png"), "计算器", self)
            self.calculator_action.setStatusTip("打开计算器")
            self.tools_menu.addAction(self.calculator_action)

            # 单位转换
            self.converter_action = QAction(
                QIcon("icons/converter.png"), "单位转换", self)
            self.converter_action.setStatusTip("打开单位转换器")
            self.tools_menu.addAction(self.converter_action)

            self.tools_menu.addSeparator()

            # 设置
            self.settings_action = QAction(
                QIcon("icons/settings.png"), "设置", self)
            self.settings_action.setStatusTip("打开设置对话框")
            self.tools_menu.addAction(self.settings_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化工具菜单失败: {str(e)}")

    def init_help_menu(self):
        """初始化帮助菜单"""
        try:
            # 帮助文档
            self.help_action = QAction("帮助文档", self)
            self.help_action.setStatusTip("打开帮助文档")
            self.help_menu.addAction(self.help_action)

            # 检查更新
            self.update_action = QAction("检查更新", self)
            self.update_action.setStatusTip("检查新版本")
            self.help_menu.addAction(self.update_action)

            self.help_menu.addSeparator()

            # 关于
            self.about_action = QAction("关于", self)
            self.about_action.setStatusTip("关于本程序")
            self.help_menu.addAction(self.about_action)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化帮助菜单失败: {str(e)}")

    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志消息，统一调用主窗口或日志管理器"""
        try:
            parent = self.parentWidget()
            if parent and hasattr(parent, 'log_message'):
                parent.log_message(message, level)
            elif hasattr(self, 'log_manager'):
                # 直接用log_manager
                level = level.upper()
                if level == "ERROR":
                    self.log_manager.error(message)
                elif level == "WARNING":
                    self.log_manager.warning(message)
                elif level == "DEBUG":
                    self.log_manager.debug(message)
                else:
                    self.log_manager.info(message)
            else:
                print(f"[LOG][{level}] {message}")
        except Exception as e:
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def new_file(self):
        """Create a new file"""
        # TODO: Implement new file creation
        pass

    def open_file(self):
        """Open a file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "打开文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                # TODO: Implement file opening
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")

    def save_file(self):
        """Save current file"""
        # TODO: Implement file saving
        pass

    def save_file_as(self):
        """Save current file with new name"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "另存为",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                # TODO: Implement file saving
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def import_data(self):
        """Import data"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入数据",
                "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
            )

            if file_path:
                # TODO: Implement data import
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入数据失败: {str(e)}")

    def export_data(self):
        """Export data"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出数据",
                "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
            )

            if file_path:
                # TODO: Implement data export
                pass

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出数据失败: {str(e)}")

    def undo(self):
        """Undo last action"""
        # TODO: Implement undo
        pass

    def redo(self):
        """Redo last undone action"""
        # TODO: Implement redo
        pass

    def cut(self):
        """Cut selected content"""
        # TODO: Implement cut
        pass

    def copy(self):
        """Copy selected content"""
        # TODO: Implement copy
        pass

    def paste(self):
        """Paste content"""
        # TODO: Implement paste
        pass

    def select_all(self):
        """Select all content"""
        # TODO: Implement select all
        pass

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.window().isFullScreen():
            self.window().showNormal()
        else:
            self.window().showFullScreen()

    def analyze(self):
        """Perform analysis"""
        # TODO: Implement analysis
        pass

    def backtest(self):
        """Run backtest"""
        # TODO: Implement backtest
        pass

    def optimize(self):
        """Optimize parameters"""
        # TODO: Implement optimization
        pass

    def pattern_recognition(self):
        """Perform pattern recognition"""
        # TODO: Implement pattern recognition
        pass

    def wave_analysis(self):
        """Perform wave analysis"""
        # TODO: Implement wave analysis
        pass

    def risk_analysis(self):
        """Perform risk analysis"""
        # TODO: Implement risk analysis
        pass

    def show_settings(self):
        """Show settings dialog"""
        # TODO: Implement settings dialog
        pass

    def show_calculator(self):
        """Show calculator"""
        # TODO: Implement calculator
        pass

    def show_converter(self):
        """Show unit converter"""
        # TODO: Implement unit converter
        pass

    def show_documentation(self):
        """Show documentation"""
        # TODO: Implement documentation viewer
        pass

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "关于",
            "交易系统 v1.0.0\n\n"
            "一个基于Python的量化交易系统\n"
            "使用PyQt5构建用户界面\n"
            "使用hikyuu框架进行量化分析"
        )
