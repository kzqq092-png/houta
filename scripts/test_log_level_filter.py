#!/usr/bin/env python3
"""
测试日志级别过滤功能
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer
from loguru import logger
from core.ui.panels.bottom_panel import LogWidget, LogHandler

class TestLogLevelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("日志级别过滤测试")
        self.setGeometry(100, 100, 900, 700)
        
        # 创建中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建日志控件
        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)
        
        # 创建LogHandler，默认INFO级别
        self.log_handler = LogHandler(self.log_widget, level="INFO")
        
        # 创建测试按钮布局
        button_layout = QHBoxLayout()
        
        # 测试不同级别日志的按钮
        debug_btn = QPushButton("发送DEBUG日志")
        debug_btn.clicked.connect(self.send_debug)
        button_layout.addWidget(debug_btn)
        
        info_btn = QPushButton("发送INFO日志")
        info_btn.clicked.connect(self.send_info)
        button_layout.addWidget(info_btn)
        
        warning_btn = QPushButton("发送WARNING日志")
        warning_btn.clicked.connect(self.send_warning)
        button_layout.addWidget(warning_btn)
        
        error_btn = QPushButton("发送ERROR日志")
        error_btn.clicked.connect(self.send_error)
        button_layout.addWidget(error_btn)
        
        # 级别切换按钮
        level_debug_btn = QPushButton("切换到DEBUG级别")
        level_debug_btn.clicked.connect(lambda: self.change_level("DEBUG"))
        button_layout.addWidget(level_debug_btn)
        
        level_info_btn = QPushButton("切换到INFO级别")
        level_info_btn.clicked.connect(lambda: self.change_level("INFO"))
        button_layout.addWidget(level_info_btn)
        
        level_warning_btn = QPushButton("切换到WARNING级别")
        level_warning_btn.clicked.connect(lambda: self.change_level("WARNING"))
        button_layout.addWidget(level_warning_btn)
        
        layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QPushButton(f"当前级别: {self.log_handler.current_level}")
        layout.addWidget(self.status_label)
        
        logger.info("日志级别过滤测试窗口初始化完成")
        
    def send_debug(self):
        logger.debug("这是一条DEBUG级别的日志消息")
        
    def send_info(self):
        logger.info("这是一条INFO级别的日志消息")
        
    def send_warning(self):
        logger.warning("这是一条WARNING级别的日志消息")
        
    def send_error(self):
        logger.error("这是一条ERROR级别的日志消息")
        
    def change_level(self, level):
        """更改日志级别"""
        self.log_handler.update_level(level)
        self.status_label.setText(f"当前级别: {level}")
        logger.info(f"日志级别已切换到: {level}")

def main():
    app = QApplication(sys.argv)
    
    # 确保Loguru配置已初始化
    from core.loguru_config import initialize_loguru
    initialize_loguru()
    
    window = TestLogLevelWindow()
    window.show()
    
    logger.info("日志级别过滤测试应用启动")
    logger.debug("这条DEBUG消息应该在INFO级别时被过滤掉")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()