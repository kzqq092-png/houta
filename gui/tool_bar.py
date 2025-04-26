"""
Tool bar for the trading system

This module contains the tool bar implementation for the trading system.
"""

from PyQt5.QtWidgets import (
    QToolBar, QAction, QToolButton, QMenu,
    QFileDialog, QMessageBox, QDialog, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QComboBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QKeySequence
import os

class MainToolBar(QToolBar):
    """Main tool bar for the trading system"""
    
    def __init__(self, parent=None):
        """初始化主工具栏
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.parent = parent
        self.logger = parent.log_manager if hasattr(parent, 'log_manager') else None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        try:
            # 设置工具栏属性
            self.setMovable(False)
            self.setIconSize(QSize(24, 24))
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            
            # File actions
            self.new_action = QAction(QIcon("icons/new.png"), "新建", self)
            self.new_action.setStatusTip("创建新的策略")
            self.new_action.setShortcut(QKeySequence.New)
            self.addAction(self.new_action)
            
            self.open_action = QAction(QIcon("icons/open.png"), "打开", self)
            self.open_action.setStatusTip("打开策略文件")
            self.open_action.setShortcut(QKeySequence.Open)
            self.addAction(self.open_action)
            
            self.save_action = QAction(QIcon("icons/save.png"), "保存", self)
            self.save_action.setStatusTip("保存当前策略")
            self.save_action.setShortcut(QKeySequence.Save)
            self.addAction(self.save_action)
            
            self.addSeparator()
            
            # Edit actions
            self.undo_action = QAction(QIcon("icons/undo.png"), "撤销", self)
            self.undo_action.setShortcut(QKeySequence.Undo)
            self.addAction(self.undo_action)
            
            self.redo_action = QAction(QIcon("icons/redo.png"), "重做", self)
            self.redo_action.setShortcut(QKeySequence.Redo)
            self.addAction(self.redo_action)
            
            self.addSeparator()
            
            # Analysis actions
            self.analyze_action = QAction(QIcon("icons/analyze.png"), "分析", self)
            self.analyze_action.setStatusTip("分析当前股票")
            self.addAction(self.analyze_action)
            
            self.backtest_action = QAction(QIcon("icons/backtest.png"), "回测", self)
            self.backtest_action.setStatusTip("回测当前策略")
            self.addAction(self.backtest_action)
            
            self.optimize_action = QAction(QIcon("icons/optimize.png"), "优化", self)
            self.optimize_action.setStatusTip("优化策略参数")
            self.addAction(self.optimize_action)
            
            self.addSeparator()
            
            # View actions
            self.zoom_in_action = QAction(QIcon("icons/zoom_in.png"), "放大", self)
            self.zoom_in_action.setStatusTip("放大图表")
            self.addAction(self.zoom_in_action)
            
            self.zoom_out_action = QAction(QIcon("icons/zoom_out.png"), "缩小", self)
            self.zoom_out_action.setStatusTip("缩小图表")
            self.addAction(self.zoom_out_action)
            
            self.reset_zoom_action = QAction(QIcon("icons/reset_zoom.png"), "重置", self)
            self.reset_zoom_action.setStatusTip("重置图表缩放")
            self.addAction(self.reset_zoom_action)
            
            self.addSeparator()
            
            # Tools actions
            self.settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
            self.settings_action.setStatusTip("打开设置对话框")
            self.addAction(self.settings_action)
            
            self.calculator_action = QAction(QIcon("icons/calculator.png"), "计算器", self)
            self.calculator_action.setStatusTip("打开计算器")
            self.addAction(self.calculator_action)
            
            self.converter_action = QAction(QIcon("icons/converter.png"), "单位转换", self)
            self.converter_action.setStatusTip("打开单位转换器")
            self.addAction(self.converter_action)
            
            # 添加搜索框
            self.addSeparator()
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索股票...")
            self.search_box.setMaximumWidth(200)
            self.addWidget(self.search_box)
            
            # 添加主题选择器
            self.theme_combo = QComboBox()
            self.theme_combo.addItems(["浅色", "深色", "蓝色"])
            self.theme_combo.setMaximumWidth(100)
            self.addWidget(self.theme_combo)
            
            self.log_message("工具栏初始化完成")
            
        except Exception as e:
            self.log_message(f"初始化工具栏失败: {str(e)}", "error")
        
    def log_message(self, message: str, level: str = "info"):
        """记录日志消息
        
        Args:
            message: 日志消息
            level: 日志级别，可选值为 info、warning、error
        """
        if self.logger:
            if level == "error":
                self.logger.error(message)
            elif level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)
        
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
            
    def undo(self):
        """Undo last action"""
        # TODO: Implement undo functionality
        pass
        
    def redo(self):
        """Redo last undone action"""
        # TODO: Implement redo functionality
        pass
        
    def analyze(self):
        """Perform analysis"""
        # TODO: Implement analysis functionality
        pass
        
    def backtest(self):
        """Run backtest"""
        # TODO: Implement backtest functionality
        pass
        
    def optimize(self):
        """Optimize parameters"""
        # TODO: Implement optimization functionality
        pass
        
    def zoom_in(self):
        """Zoom in"""
        # TODO: Implement zoom in functionality
        pass
        
    def zoom_out(self):
        """Zoom out"""
        # TODO: Implement zoom out functionality
        pass
        
    def reset_zoom(self):
        """Reset zoom level"""
        # TODO: Implement reset zoom functionality
        pass
        
    def show_settings(self):
        """Show settings dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        layout = QVBoxLayout(dialog)
        
        # Add settings widgets
        layout.addWidget(QLabel("主题设置"))
        theme_combo = QComboBox()
        theme_combo.addItems(["浅色", "深色", "系统"])
        layout.addWidget(theme_combo)
        
        layout.addWidget(QLabel("字体大小"))
        font_size = QSpinBox()
        font_size.setRange(8, 24)
        font_size.setValue(12)
        layout.addWidget(font_size)
        
        # Add buttons
        buttons = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        # Connect signals
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            # TODO: Apply settings
            pass
            
    def show_calculator(self):
        """Show calculator"""
        dialog = QDialog(self)
        dialog.setWindowTitle("计算器")
        layout = QVBoxLayout(dialog)
        
        # Add calculator display
        display = QLineEdit()
        display.setReadOnly(True)
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
                button_row.addWidget(button)
            layout.addLayout(button_row)
            
        dialog.exec_()
        
    def show_converter(self):
        """Show unit converter"""
        dialog = QDialog(self)
        dialog.setWindowTitle("单位转换器")
        layout = QVBoxLayout(dialog)
        
        # Add input fields
        input_layout = QHBoxLayout()
        input_value = QLineEdit()
        input_unit = QComboBox()
        input_unit.addItems(["元", "美元", "欧元", "英镑"])
        input_layout.addWidget(input_value)
        input_layout.addWidget(input_unit)
        layout.addLayout(input_layout)
        
        # Add output fields
        output_layout = QHBoxLayout()
        output_value = QLineEdit()
        output_value.setReadOnly(True)
        output_unit = QComboBox()
        output_unit.addItems(["元", "美元", "欧元", "英镑"])
        output_layout.addWidget(output_value)
        output_layout.addWidget(output_unit)
        layout.addLayout(output_layout)
        
        # Add convert button
        convert_button = QPushButton("转换")
        layout.addWidget(convert_button)
        
        dialog.exec_() 