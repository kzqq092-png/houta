"""
Tool bar for the trading system

This module contains the tool bar implementation for the trading system.
"""

from PyQt5.QtWidgets import (
    QToolBar, QAction, QToolButton, QMenu,
    QFileDialog, QMessageBox, QDialog, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox,
    QHBoxLayout, QGroupBox, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QKeySequence
import os
import traceback
from gui.widgets.log_widget import LogWidget
from utils.theme import get_theme_manager
from utils.log_util import log_structured
from .tools import Calculator, UnitConverter


class MainToolBar(QToolBar):
    """主工具栏"""

    def __init__(self, parent=None):
        """初始化工具栏

        Args:
            parent: 父窗口
        """
        try:
            super().__init__(parent)
            self.setWindowTitle("主工具栏")
            self.setObjectName("MainToolBar")

            # 初始化日志管理器
            self.log_manager = None
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                from core.logger import LogManager
                self.log_manager = LogManager()

            # 初始化主题管理器
            self.theme_manager = get_theme_manager()

            # 初始化UI
            self.init_ui()

            log_structured(self.log_manager, "toolbar_init", level="info", status="success")

        except Exception as e:
            print(f"初始化工具栏失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化工具栏失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def init_ui(self):
        """Initialize the UI"""
        try:
            # 设置工具栏属性
            self.setMovable(True)
            self.setFloatable(True)
            self.setIconSize(QSize(32, 32))
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

            # 创建工具栏按钮
            self.create_actions()

        except Exception as e:
            self.log_manager.error(f"初始化工具栏失败: {str(e)}")

    def create_actions(self):
        """创建工具栏按钮"""
        # 文件操作
        self.new_action = QAction(QIcon("icons/new.png"), "新建", self)
        self.new_action.setStatusTip("创建新文件")
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.new_file)
        self.addAction(self.new_action)

        self.open_action = QAction(QIcon("icons/open.png"), "打开", self)
        self.open_action.setStatusTip("打开文件")
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)
        self.addAction(self.open_action)

        self.save_action = QAction(QIcon("icons/save.png"), "保存", self)
        self.save_action.setStatusTip("保存文件")
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_file)
        self.addAction(self.save_action)

        self.addSeparator()

        # 分析工具
        self.analyze_action = QAction(QIcon("icons/analyze.png"), "分析", self)
        self.analyze_action.setStatusTip("执行技术分析")
        self.analyze_action.setShortcut("F5")
        if hasattr(self.parent(), 'analyze'):
            self.analyze_action.triggered.connect(self.parent().analyze)
        self.addAction(self.analyze_action)

        self.backtest_action = QAction(QIcon("icons/backtest.png"), "回测", self)
        self.backtest_action.setStatusTip("执行策略回测")
        self.backtest_action.setShortcut("F6")
        if hasattr(self.parent(), 'backtest'):
            self.backtest_action.triggered.connect(self.parent().backtest)
        self.addAction(self.backtest_action)

        self.optimize_action = QAction(QIcon("icons/optimize.png"), "优化", self)
        self.optimize_action.setStatusTip("参数优化")
        self.optimize_action.setShortcut("F7")
        if hasattr(self.parent(), 'optimize'):
            self.optimize_action.triggered.connect(self.parent().optimize)
        self.addAction(self.optimize_action)

        self.addSeparator()

        # 缩放工具
        self.zoom_in_action = QAction(QIcon("icons/zoom_in.png"), "放大", self)
        self.zoom_in_action.setStatusTip("放大图表")
        self.zoom_in_action.setShortcut("Ctrl++")
        self.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction(QIcon("icons/zoom_out.png"), "缩小", self)
        self.zoom_out_action.setStatusTip("缩小图表")
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.addAction(self.zoom_out_action)

        self.reset_zoom_action = QAction(
            QIcon("icons/reset_zoom.png"), "重置缩放", self)
        self.reset_zoom_action.setStatusTip("重置图表缩放")
        self.reset_zoom_action.setShortcut("Ctrl+0")
        self.addAction(self.reset_zoom_action)

        self.undo_zoom_action = QAction(QIcon("icons/undo.png"), "撤销缩放", self)
        self.undo_zoom_action.setStatusTip("撤销上一次缩放操作")
        self.undo_zoom_action.setShortcut("Ctrl+Z")
        self.addAction(self.undo_zoom_action)

        self.addSeparator()

        # 常用工具
        self.calculator_action = QAction(QIcon("icons/calculator.png"), "计算器", self)
        self.calculator_action.setStatusTip("打开计算器")
        self.calculator_action.setShortcut("Ctrl+Shift+C")
        self.calculator_action.triggered.connect(self.show_calculator)
        self.addAction(self.calculator_action)

        self.converter_action = QAction(QIcon("icons/converter.png"), "单位转换", self)
        self.converter_action.setStatusTip("打开单位转换器")
        self.converter_action.setShortcut("Ctrl+U")
        self.converter_action.triggered.connect(self.show_converter)
        self.addAction(self.converter_action)

        self.settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        self.settings_action.setStatusTip("打开设置对话框")
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self.show_settings)
        self.addAction(self.settings_action)

        # 搜索框
        self.addSeparator()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索股票代码或名称...")
        self.search_box.setMaximumWidth(200)
        self.addWidget(self.search_box)

    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志消息，统一调用主窗口或日志管理器"""
        try:
            parent = self.parentWidget()
            if parent and hasattr(parent, 'log_message'):
                parent.log_message(message, level)
            elif hasattr(self, 'log_manager'):
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
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "新建文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                QMessageBox.information(self, "成功", "文件创建成功")
                self.log_message(f"创建文件成功: {file_path}")

        except Exception as e:
            error_msg = f"创建文件失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_message(error_msg, "error")

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
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                QMessageBox.information(self, "成功", "文件打开成功")
                self.log_message(f"打开文件成功: {file_path}")

        except Exception as e:
            error_msg = f"打开文件失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_message(error_msg, "error")

    def save_file(self):
        """Save current file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                QMessageBox.information(self, "成功", "文件保存成功")
                self.log_message(f"保存文件成功: {file_path}")

        except Exception as e:
            error_msg = f"保存文件失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_message(error_msg, "error")

    def show_settings(self):
        """Show settings dialog"""
        try:
            if hasattr(self.parent(), 'show_settings'):
                self.parent().show_settings()
            else:
                self.log_message("设置功能暂未实现", "warning")
        except Exception as e:
            error_msg = f"显示设置对话框失败: {str(e)}"
            self.log_message(error_msg, "error")

    def show_calculator(self):
        """Show calculator using the new Calculator tool"""
        try:
            Calculator.show_calculator(self)
            self.log_message("打开计算器")
        except Exception as e:
            error_msg = f"显示计算器失败: {str(e)}"
            self.log_message(error_msg, "error")

    def show_converter(self):
        """Show unit converter using the new UnitConverter tool"""
        try:
            UnitConverter.show_converter(self)
            self.log_message("打开单位转换器")
        except Exception as e:
            error_msg = f"显示单位转换器失败: {str(e)}"
            self.log_message(error_msg, "error")
