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


class MainToolBar(QToolBar):
    """主工具栏"""

    def __init__(self, parent=None):
        """初始化工具栏

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

            self.log_manager.info("工具栏初始化完成")

        except Exception as e:
            print(f"初始化工具栏失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化工具栏失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def init_ui(self):
        """Initialize the UI"""
        try:
            # 设置工具栏属性
            self.setMovable(False)
            self.setIconSize(QSize(24, 24))
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

            # 创建工具栏按钮
            self.create_actions()

        except Exception as e:
            self.log_manager.error(f"初始化工具栏失败: {str(e)}")

    def create_actions(self):
        """创建工具栏按钮"""
        # 文件操作
        self.new_action = QAction(QIcon("icons/new.png"), "新建", self)
        self.new_action.setStatusTip("创建新的策略")
        self.new_action.setShortcut("Ctrl+N")
        self.addAction(self.new_action)

        self.open_action = QAction(QIcon("icons/open.png"), "打开", self)
        self.open_action.setStatusTip("打开策略文件")
        self.open_action.setShortcut("Ctrl+O")
        self.addAction(self.open_action)

        self.save_action = QAction(QIcon("icons/save.png"), "保存", self)
        self.save_action.setStatusTip("保存当前策略")
        self.save_action.setShortcut("Ctrl+S")
        self.addAction(self.save_action)

        self.addSeparator()

        # 分析工具
        self.analyze_action = QAction(QIcon("icons/analyze.png"), "分析", self)
        self.analyze_action.setStatusTip("分析当前股票")
        self.analyze_action.setShortcut("F5")
        self.addAction(self.analyze_action)

        self.backtest_action = QAction(QIcon("icons/backtest.png"), "回测", self)
        self.backtest_action.setStatusTip("回测当前策略")
        self.backtest_action.setShortcut("F6")
        self.addAction(self.backtest_action)

        self.optimize_action = QAction(QIcon("icons/optimize.png"), "优化", self)
        self.optimize_action.setStatusTip("优化策略参数")
        self.optimize_action.setShortcut("F7")
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
        self.calculator_action = QAction(
            QIcon("icons/calculator.png"), "计算器", self)
        self.calculator_action.setStatusTip("打开计算器")
        self.calculator_action.setShortcut("Ctrl+K")
        self.addAction(self.calculator_action)

        self.converter_action = QAction(
            QIcon("icons/converter.png"), "单位转换", self)
        self.converter_action.setStatusTip("打开单位转换器")
        self.converter_action.setShortcut("Ctrl+U")
        self.addAction(self.converter_action)

        self.settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        self.settings_action.setStatusTip("打开设置对话框")
        self.settings_action.setShortcut("Ctrl+,")
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
            # Create a new empty file
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

        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建文件失败: {str(e)}")

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
                # TODO: Process file content
                QMessageBox.information(self, "成功", "文件打开成功")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")

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
                # TODO: Get current content and save
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                QMessageBox.information(self, "成功", "文件保存成功")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中到父窗口或屏幕，并尽量靠近上部

        Args:
            dialog: 要居中的对话框
            parent: 父窗口，如果为None则使用屏幕
            offset_y: 距离顶部的偏移量
        """
        try:
            if parent and parent.isVisible():
                # 相对于父窗口居中
                parent_geom = parent.geometry()
                dialog_geom = dialog.frameGeometry()
                x = parent_geom.center().x() - dialog_geom.width() // 2
                y = parent_geom.top() + offset_y

                # 确保弹窗不会超出父窗口边界
                x = max(parent_geom.left(), min(
                    x, parent_geom.right() - dialog_geom.width()))
                y = max(parent_geom.top(), min(
                    y, parent_geom.bottom() - dialog_geom.height()))
            else:
                # 相对于屏幕居中
                screen = dialog.screen() or dialog.parentWidget().screen()
                if screen:
                    screen_geom = screen.geometry()
                    dialog_geom = dialog.frameGeometry()
                    x = screen_geom.center().x() - dialog_geom.width() // 2
                    y = screen_geom.top() + offset_y

                    # 确保弹窗不会超出屏幕边界
                    x = max(screen_geom.left(), min(
                        x, screen_geom.right() - dialog_geom.width()))
                    y = max(screen_geom.top(), min(
                        y, screen_geom.bottom() - dialog_geom.height()))

            dialog.move(x, y)
        except Exception as e:
            self.log_manager.error(f"设置弹窗位置失败: {str(e)}")

    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("设置")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # Add settings widgets
            settings_group = QGroupBox("基本设置")
            settings_layout = QFormLayout(settings_group)

            # 主题设置
            theme_combo = QComboBox()
            theme_combo.addItems(["浅色", "深色", "系统"])
            settings_layout.addRow("主题:", theme_combo)

            # 字体大小
            font_size = QSpinBox()
            font_size.setRange(8, 24)
            font_size.setValue(12)
            settings_layout.addRow("字体大小:", font_size)

            layout.addWidget(settings_group)

            # Add buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)

            if dialog.exec_() == QDialog.Accepted:
                # TODO: Apply settings
                pass

        except Exception as e:
            self.log_manager.error(f"显示设置对话框失败: {str(e)}")

    def show_calculator(self):
        """Show calculator"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("计算器")
            dialog.setMinimumSize(300, 400)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # Add calculator display
            display = QLineEdit()
            display.setReadOnly(True)
            display.setAlignment(Qt.AlignRight)
            display.setStyleSheet("""
                QLineEdit {
                    font-size: 20px;
                    padding: 5px;
                    background: #f5f5f5;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
            """)
            layout.addWidget(display)

            # Add calculator buttons
            buttons = [
                ['7', '8', '9', '/'],
                ['4', '5', '6', '*'],
                ['1', '2', '3', '-'],
                ['0', '.', '=', '+']
            ]

            for row in buttons:
                button_row = QHBoxLayout()
                for text in row:
                    button = QPushButton(text)
                    button.setMinimumSize(50, 50)
                    button.setStyleSheet("""
                        QPushButton {
                            font-size: 18px;
                            border-radius: 25px;
                            background: #e0e0e0;
                        }
                        QPushButton:hover {
                            background: #d0d0d0;
                        }
                    """)
                    button_row.addWidget(button)
                layout.addLayout(button_row)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示计算器失败: {str(e)}")

    def show_converter(self):
        """Show unit converter"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("单位转换器")
            dialog.setMinimumSize(400, 300)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            # Add input fields
            input_group = QGroupBox("输入")
            input_layout = QFormLayout(input_group)

            input_value = QLineEdit()
            input_value.setAlignment(Qt.AlignRight)
            input_unit = QComboBox()
            input_unit.addItems(["元", "美元", "欧元", "英镑"])
            input_layout.addRow("数值:", input_value)
            input_layout.addRow("单位:", input_unit)

            layout.addWidget(input_group)

            # Add output fields
            output_group = QGroupBox("输出")
            output_layout = QFormLayout(output_group)

            output_value = QLineEdit()
            output_value.setReadOnly(True)
            output_value.setAlignment(Qt.AlignRight)
            output_unit = QComboBox()
            output_unit.addItems(["元", "美元", "欧元", "英镑"])
            output_layout.addRow("数值:", output_value)
            output_layout.addRow("单位:", output_unit)

            layout.addWidget(output_group)

            # Add convert button
            convert_button = QPushButton("转换")
            convert_button.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    padding: 8px;
                    background: #2196F3;
                    color: white;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background: #1976D2;
                }
            """)
            layout.addWidget(convert_button)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示单位转换器失败: {str(e)}")
