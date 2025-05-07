"""
日志控件模块

提供日志显示和管理功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QLineEdit, QTextEdit,
                             QFileDialog, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QTextCursor
from datetime import datetime
from core.logger import LogManager, LogLevel
import traceback


class LogWidget(QWidget):
    """日志控件类"""

    # 定义信号
    log_added = pyqtSignal(str, str)  # 日志消息, 级别
    log_cleared = pyqtSignal()
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, log_manager: LogManager = None, parent=None):
        """初始化日志控件

        Args:
            log_manager: 日志管理器实例
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 使用传入的日志管理器或创建新的
            self.log_manager = log_manager or LogManager()

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 设置样式
            self.apply_style()

            self.log_manager.info("日志控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)

            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setSpacing(8)

            # 日志级别过滤器
            level_label = QLabel("日志级别:")
            self.level_combo = QComboBox()
            self.level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            self.level_combo.setFixedWidth(100)
            toolbar_layout.addWidget(level_label)
            toolbar_layout.addWidget(self.level_combo)

            # 搜索框
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索日志...")
            self.search_box.setFixedWidth(200)
            toolbar_layout.addWidget(self.search_box)

            # 添加弹性空间
            toolbar_layout.addStretch()

            # 清除按钮
            self.clear_button = QPushButton("清除")
            self.clear_button.setFixedWidth(80)
            toolbar_layout.addWidget(self.clear_button)

            # 导出按钮
            self.export_button = QPushButton("导出")
            self.export_button.setFixedWidth(80)
            toolbar_layout.addWidget(self.export_button)

            layout.addLayout(toolbar_layout)

            # 创建日志文本框
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.NoWrap)

            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidget(self.log_text)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)

            self.log_manager.info("日志控件UI初始化完成")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接日志管理器信号
            self.log_manager.log_message.connect(self.add_log)
            self.log_manager.log_cleared.connect(self.clear_logs)

            # 连接控件信号
            self.level_combo.currentTextChanged.connect(self.filter_logs)
            self.search_box.textChanged.connect(self.search_logs)
            self.clear_button.clicked.connect(self.clear_logs)
            self.export_button.clicked.connect(self.export_logs)

            self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def apply_style(self):
        """应用样式"""
        try:
            self.setStyleSheet("""
                QWidget {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 12px;
                }
                QLabel {
                    color: #1976d2;
                }
                QComboBox {
                    border: 1px solid #bdbdbd;
                    border-radius: 4px;
                    padding: 4px;
                    background: white;
                }
                QComboBox:hover {
                    border-color: #1976d2;
                }
                QLineEdit {
                    border: 1px solid #bdbdbd;
                    border-radius: 4px;
                    padding: 4px;
                    background: white;
                }
                QLineEdit:focus {
                    border-color: #1976d2;
                }
                QPushButton {
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    background: #1976d2;
                    color: white;
                }
                QPushButton:hover {
                    background: #1565c0;
                }
                QPushButton:pressed {
                    background: #0d47a1;
                }
                QTextEdit {
                    border: 1px solid #bdbdbd;
                    border-radius: 4px;
                    background: white;
                    font-family: 'Consolas', 'Microsoft YaHei', monospace;
                }
                QScrollArea {
                    border: none;
                }
            """)

        except Exception as e:
            error_msg = f"应用样式失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def add_log(self, message: str, level: str = "INFO"):
        """添加日志

        Args:
            message: 日志消息
            level: 日志级别
        """
        try:
            # 格式化日志消息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 根据日志级别设置颜色
            color = {
                "ERROR": "#FF0000",
                "WARNING": "#FFA500",
                "INFO": "#000000",
                "DEBUG": "#808080"
            }.get(level.upper(), "#000000")

            # 添加带颜色的日志
            formatted_message = f'<span style="color: {color}">[{timestamp}] [{level}] {message}</span>'
            self.log_text.append(formatted_message)

            # 滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            # 如果是错误消息，闪烁提示
            if level.upper() == "ERROR":
                self.flash_error()

            # 发送日志添加信号
            self.log_added.emit(message, level)

        except Exception as e:
            error_msg = f"添加日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def flash_error(self):
        """闪烁错误提示"""
        try:
            def flash():
                self.setStyleSheet("""
                    QWidget {
                        background-color: #ffebee;
                    }
                """)
                QTimer.singleShot(500, lambda: self.apply_style())

            flash()
            QTimer.singleShot(1000, flash)

        except Exception as e:
            self.log_manager.error(f"闪烁错误提示失败: {str(e)}")

    def filter_logs(self, level: str):
        """根据级别过滤日志

        Args:
            level: 日志级别
        """
        try:
            # 获取所有日志
            all_logs = self.log_text.toPlainText().split('\n')

            # 清空日志显示
            self.log_text.clear()

            # 过滤并显示日志
            for log in all_logs:
                if level == "全部" or f"[{level.upper()}]" in log:
                    self.log_text.append(log)

            # 滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            error_msg = f"过滤日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def search_logs(self, text: str):
        """搜索日志

        Args:
            text: 搜索文本
        """
        try:
            # 获取所有日志
            all_logs = self.log_text.toPlainText().split('\n')

            # 清空日志显示
            self.log_text.clear()

            # 搜索并显示日志
            for log in all_logs:
                if text.lower() in log.lower():
                    self.log_text.append(log)

            # 滚动到底部
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            error_msg = f"搜索日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def clear_logs(self):
        """清除日志"""
        try:
            self.log_text.clear()
            self.log_cleared.emit()
            self.log_manager.info("日志已清除")

        except Exception as e:
            error_msg = f"清除日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def export_logs(self):
        """导出日志到文件"""
        try:
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "Text Files (*.txt);;Log Files (*.log)"
            )

            if file_path:
                # 保存日志
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())

                self.log_manager.info(f"日志已导出到: {file_path}")

        except Exception as e:
            error_msg = f"导出日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
