"""
计算器工具模块
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import traceback


class Calculator(QDialog):
    """计算器对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("计算器")
        self.setFixedSize(300, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        # 计算相关属性
        self.current_value = 0
        self.pending_value = 0
        self.pending_operation = None
        self.waiting_for_operand = True

        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # 显示屏
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setText("0")
        self.display.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.display)

        # 按钮网格
        button_layout = QGridLayout()
        button_layout.setSpacing(5)

        # 定义按钮
        buttons = [
            ('C', 0, 0, 1, 2), ('±', 0, 2), ('÷', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('×', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('0', 4, 0, 1, 2), ('.', 4, 2), ('=', 4, 3)
        ]

        self.buttons = {}
        for button_info in buttons:
            text = button_info[0]
            row = button_info[1]
            col = button_info[2]
            row_span = button_info[3] if len(button_info) > 3 else 1
            col_span = button_info[4] if len(button_info) > 4 else 1

            button = QPushButton(text)
            button.setMinimumSize(60, 60)
            button.setStyleSheet(self.get_button_style(text))
            button.clicked.connect(lambda checked, t=text: self.button_clicked(t))

            button_layout.addWidget(button, row, col, row_span, col_span)
            self.buttons[text] = button

        layout.addLayout(button_layout)

    def get_button_style(self, text):
        """获取按钮样式"""
        if text in ['C', '±']:
            # 功能按钮
            return """
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                    background-color: #ff9500;
                    color: white;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #ffad33;
                }
                QPushButton:pressed {
                    background-color: #e6851a;
                }
            """
        elif text in ['+', '-', '×', '÷', '=']:
            # 运算符按钮
            return """
                QPushButton {
                    font-size: 20px;
                    font-weight: bold;
                    background-color: #007aff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #3395ff;
                }
                QPushButton:pressed {
                    background-color: #0056b3;
                }
            """
        else:
            # 数字按钮
            return """
                QPushButton {
                    font-size: 18px;
                    font-weight: bold;
                    background-color: #e0e0e0;
                    color: black;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """

    def button_clicked(self, text):
        """处理按钮点击事件"""
        try:
            if text.isdigit():
                self.digit_clicked(text)
            elif text == '.':
                self.decimal_clicked()
            elif text == 'C':
                self.clear_clicked()
            elif text == '±':
                self.sign_clicked()
            elif text == '=':
                self.equals_clicked()
            elif text in ['+', '-', '×', '÷']:
                self.operation_clicked(text)

        except Exception as e:
            self.display.setText("错误")
            print(f"计算器错误: {str(e)}")
            print(traceback.format_exc())

    def digit_clicked(self, digit):
        """处理数字按钮点击"""
        if self.waiting_for_operand:
            self.display.setText(digit)
            self.waiting_for_operand = False
        else:
            current_text = self.display.text()
            if current_text == "0":
                self.display.setText(digit)
            else:
                self.display.setText(current_text + digit)

    def decimal_clicked(self):
        """处理小数点按钮点击"""
        current_text = self.display.text()
        if self.waiting_for_operand:
            self.display.setText("0.")
            self.waiting_for_operand = False
        elif '.' not in current_text:
            self.display.setText(current_text + '.')

    def clear_clicked(self):
        """处理清除按钮点击"""
        self.display.setText("0")
        self.current_value = 0
        self.pending_value = 0
        self.pending_operation = None
        self.waiting_for_operand = True

    def sign_clicked(self):
        """处理正负号按钮点击"""
        current_text = self.display.text()
        if current_text != "0":
            if current_text.startswith('-'):
                self.display.setText(current_text[1:])
            else:
                self.display.setText('-' + current_text)

    def operation_clicked(self, operation):
        """处理运算符按钮点击"""
        current_value = float(self.display.text())

        if self.pending_operation is not None and not self.waiting_for_operand:
            result = self.calculate(self.pending_value, current_value, self.pending_operation)
            self.display.setText(str(result))
            current_value = result

        self.pending_value = current_value
        self.pending_operation = operation
        self.waiting_for_operand = True

    def equals_clicked(self):
        """处理等号按钮点击"""
        if self.pending_operation is not None:
            current_value = float(self.display.text())
            result = self.calculate(self.pending_value, current_value, self.pending_operation)
            self.display.setText(str(result))
            self.pending_operation = None
            self.waiting_for_operand = True

    def calculate(self, left_operand, right_operand, operation):
        """执行计算"""
        if operation == '+':
            return left_operand + right_operand
        elif operation == '-':
            return left_operand - right_operand
        elif operation == '×':
            return left_operand * right_operand
        elif operation == '÷':
            if right_operand == 0:
                return float('inf')
            return left_operand / right_operand
        else:
            return right_operand

    @staticmethod
    def show_calculator(parent=None):
        """显示计算器对话框"""
        calculator = Calculator(parent)
        calculator.exec_()
        return calculator
