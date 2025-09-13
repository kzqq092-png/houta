#!/usr/bin/env python3
"""
测试Qt日志处理器的脚本
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QTimer
from loguru import logger
from gui.loguru_qt_handler import get_qt_handler, get_qt_bridge
from gui.widgets.log_widget_loguru import LoguruLogWidget

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt日志处理器测试")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建日志控件
        self.log_widget = LoguruLogWidget()
        layout.addWidget(self.log_widget)
        
        # 创建测试按钮
        test_btn = QPushButton("测试日志输出")
        test_btn.clicked.connect(self.test_logging)
        layout.addWidget(test_btn)
        
        # 获取Qt日志处理器
        self.qt_handler = get_qt_handler()
        
        # 启动定时器测试
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_test)
        self.timer.start(2000)  # 每2秒自动测试
        
        logger.info("测试窗口初始化完成")
        
    def test_logging(self):
        """测试日志输出"""
        logger.debug("这是一条调试信息")
        logger.info("这是一条信息")
        logger.warning("这是一条警告")
        logger.error("这是一条错误信息")
        logger.critical("这是一条严重错误")
        
    def auto_test(self):
        """自动测试"""
        import random
        messages = [
            ("debug", "自动调试测试"),
            ("info", "自动信息测试"),
            ("warning", "自动警告测试"),
            ("error", "自动错误测试")
        ]
        
        level, msg = random.choice(messages)
        getattr(logger, level)(f"{msg} - {random.randint(1, 100)}")

def main():
    app = QApplication(sys.argv)
    
    # 确保Loguru配置已初始化
    from core.loguru_config import initialize_loguru
    initialize_loguru()
    
    window = TestWindow()
    window.show()
    
    logger.info("Qt日志测试应用启动")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()