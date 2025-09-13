#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化的UI测试脚本

测试数据管理UI组件的基本功能
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SimpleUITest(QMainWindow):
    """简化UI测试"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("数据管理UI简化测试")
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 标题
        title = QLabel("FactorWeave-Quant 数据管理UI测试")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 测试按钮
        test_basic_btn = QPushButton("测试基础UI组件")
        test_basic_btn.clicked.connect(self.test_basic_components)
        layout.addWidget(test_basic_btn)

        test_data_mgmt_btn = QPushButton("测试数据管理组件")
        test_data_mgmt_btn.clicked.connect(self.test_data_management)
        layout.addWidget(test_data_mgmt_btn)

        # 状态标签
        self.status_label = QLabel("测试系统就绪")
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #f0f0f0; }")
        layout.addWidget(self.status_label)

    def test_basic_components(self):
        """测试基础组件"""
        try:
            from gui.widgets.data_management_widget import DataSourceManagementWidget

            widget = DataSourceManagementWidget()
            widget.setWindowTitle("数据源管理测试")
            widget.resize(800, 600)
            widget.show()

            self.status_label.setText("✅ 基础组件测试通过")

        except Exception as e:
            self.status_label.setText(f"❌ 基础组件测试失败: {str(e)}")
            QMessageBox.critical(self, "测试失败", f"基础组件测试失败:\n{str(e)}")

    def test_data_management(self):
        """测试数据管理组件"""
        try:
            from gui.widgets.data_management_widget import DataManagementWidget

            widget = DataManagementWidget()
            widget.setWindowTitle("数据管理测试")
            widget.resize(1000, 700)
            widget.show()

            self.status_label.setText("✅ 数据管理组件测试通过")

        except Exception as e:
            self.status_label.setText(f"❌ 数据管理组件测试失败: {str(e)}")
            QMessageBox.critical(self, "测试失败", f"数据管理组件测试失败:\n{str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    test_window = SimpleUITest()
    test_window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
