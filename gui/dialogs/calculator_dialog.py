"""
计算器对话框模块
"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from typing import Optional
from loguru import logger

logger = logger


class CalculatorDialog(QDialog):
    """计算器对话框，优化UI和功能"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("计算器")
        self.setStyleSheet("""
            QDialog {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                background-color: #f0f0f0;
            }
            QLineEdit {
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
                font-size: 20px;
                padding: 10px;
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QPushButton {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 16px;
                padding: 10px;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)

        self.setup_ui()
        self.add_shadow()

    def setup_ui(self):
        """设置UI界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建显示框
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet("font-size: 20px;")
        main_layout.addWidget(self.display)

        # 创建按钮网格
        grid = QGridLayout()
        main_layout.addLayout(grid)

        # 按钮文本
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            '0', '.', '=', '+'
        ]

        # 创建按钮
        for i, text in enumerate(buttons):
            button = QPushButton(text)
            button.setStyleSheet("font-size: 16px;")
            button.clicked.connect(
                lambda checked, t=text: self.calculator_button_clicked(t))
            grid.addWidget(button, i // 4, i % 4)

        # 添加清除按钮
        clear_button = QPushButton("C")
        clear_button.setStyleSheet("font-size: 16px;")
        clear_button.clicked.connect(lambda: self.display.clear())
        grid.addWidget(clear_button, 4, 0, 1, 2)

        # 添加退格按钮
        backspace_button = QPushButton("←")
        backspace_button.setStyleSheet("font-size: 16px;")
        backspace_button.clicked.connect(lambda: self.display.backspace())
        grid.addWidget(backspace_button, 4, 2, 1, 2)

    def calculator_button_clicked(self, text: str) -> None:
        """处理计算器按钮点击事件，优化UI刷新机制"""
        try:
            # 使用系统日志组件记录操作
            logger.debug(f"计算器按钮点击: {text}")

            if text == "=":
                # 计算结果
                try:
                    result = eval(self.display.text())
                    self.display.setText(str(result))
                except:
                    self.display.setText("错误")
            elif text == "C":
                # 清除显示
                self.display.clear()
            else:
                # 添加文本
                self.display.insert(text)

        except Exception as e:
            logger.error(f"计算器操作失败: {str(e)}")

    def add_shadow(self):
        """添加阴影效果"""
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(32)
            shadow.setXOffset(0)
            shadow.setYOffset(12)
            shadow.setColor(QColor(0, 0, 0, 80))
            self.setGraphicsEffect(shadow)
        except Exception as e:
            logger.warning(f"添加阴影效果失败: {str(e)}")
