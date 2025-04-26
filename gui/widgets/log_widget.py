"""
日志控件模块

提供日志显示和管理功能
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QLineEdit, QTextEdit,
                           QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
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
    
    def __init__(self, parent=None):
        """初始化日志控件
        
        Args:
            parent: 父窗口
        """
        try:
            super().__init__(parent)
            
            # 初始化日志管理器
            self.log_manager = LogManager()
            
            # 初始化UI
            self.init_ui()
            
            # 连接信号
            self.connect_signals()
            
            self.log_manager.info("日志控件初始化完成")
            
        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            
            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            
            # 日志级别过滤器
            level_label = QLabel("日志级别:")
            self.level_combo = QComboBox()
            self.level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            toolbar_layout.addWidget(level_label)
            toolbar_layout.addWidget(self.level_combo)
            
            # 搜索框
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索日志...")
            toolbar_layout.addWidget(self.search_box)
            
            # 清除按钮
            self.clear_button = QPushButton("清除")
            toolbar_layout.addWidget(self.clear_button)
            
            # 导出按钮
            self.export_button = QPushButton("导出")
            toolbar_layout.addWidget(self.export_button)
            
            layout.addLayout(toolbar_layout)
            
            # 创建日志文本框
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            layout.addWidget(self.log_text)
            
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
            if hasattr(self.log_manager, 'log_added'):
                self.log_manager.log_added.connect(self.add_log)
            if hasattr(self.log_manager, 'log_cleared'):
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
            
    def add_log(self, message: str, level: str = "INFO"):
        """添加日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        try:
            # 格式化日志消息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] [{level}] {message}"
            
            # 根据日志级别设置颜色
            color = {
                "ERROR": "#FF0000",
                "WARNING": "#FFA500",
                "INFO": "#000000",
                "DEBUG": "#808080"
            }.get(level.upper(), "#000000")
            
            # 添加带颜色的日志
            self.log_text.append(
                f'<span style="color: {color}">{formatted_message}</span>'
            )
            
            # 滚动到底部
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
            # 发送日志添加信号
            self.log_added.emit(message, level)
            
        except Exception as e:
            error_msg = f"添加日志失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
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