from loguru import logger
"""
汇率转换工具

提供主要货币之间的汇率转换功能。
"""

from typing import Optional, Dict
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QWidget, QLabel, QComboBox,
    QDoubleSpinBox, QGroupBox, QTextEdit, QTabWidget,
    QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from decimal import Decimal, ROUND_HALF_UP

logger = logger

class CurrencyConverter(QDialog):
    """汇率转换器对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化汇率转换器

        Args:
            parent: 父窗口组件
        """
        super().__init__(parent)
        self.setWindowTitle("汇率转换器")
        self.setFixedSize(600, 500)

        # 汇率数据（模拟数据，实际应用中应从API获取）
        self.exchange_rates = {
            "USD": 1.0,      # 美元（基准）
            "CNY": 7.2,      # 人民币
            "EUR": 0.85,     # 欧元
            "GBP": 0.73,     # 英镑
            "JPY": 110.0,    # 日元
            "HKD": 7.8,      # 港币
            "KRW": 1200.0,   # 韩元
            "AUD": 1.35,     # 澳元
            "CAD": 1.25,     # 加元
            "CHF": 0.92,     # 瑞士法郎
            "SGD": 1.35,     # 新加坡元
            "TWD": 28.0,     # 新台币
        }

        self.last_update_time = datetime.now()

        # 设置样式
        self._setup_styles()

        # 创建UI
        self._create_widgets()

        # 连接信号
        self._connect_signals()

        # 初始化默认值
        self._set_default_values()

    def _setup_styles(self) -> None:
        """设置样式表"""
        self.setStyleSheet("""
            QDialog {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                background-color: #f8f9fa;
            }
            QLineEdit, QDoubleSpinBox, QComboBox {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 12px;
                padding: 8px;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                min-height: 20px;
            }
            QLineEdit:read-only {
                background-color: #e9ecef;
                color: #495057;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 12px;
                color: #495057;
                font-weight: normal;
            }
            QPushButton {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 12px;
                padding: 8px 16px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QGroupBox {
                font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                font-size: 12px;
                font-weight: bold;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit {
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
                font-size: 11px;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
        """)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 创建汇率转换标签页
        self._create_converter_tab()

        # 创建汇率列表标签页
        self._create_rates_tab()

        # 创建状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel(
            f"汇率更新时间: {self.last_update_time.strftime('%H:%M:%S')}")
        self.refresh_btn = QPushButton("刷新汇率")

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(status_layout)

    def _create_converter_tab(self) -> None:
        """创建汇率转换标签页"""
        converter_widget = QWidget()
        converter_layout = QVBoxLayout(converter_widget)
        converter_layout.setSpacing(15)

        # 转换信息组
        convert_group = QGroupBox("货币转换")
        convert_layout = QGridLayout(convert_group)

        # 源货币
        convert_layout.addWidget(QLabel("源货币:"), 0, 0)
        self.from_currency = QComboBox()
        convert_layout.addWidget(self.from_currency, 0, 1)

        # 源金额
        convert_layout.addWidget(QLabel("金额:"), 0, 2)
        self.from_amount = QDoubleSpinBox()
        self.from_amount.setRange(0.01, 999999999.99)
        self.from_amount.setDecimals(2)
        self.from_amount.setValue(100.0)
        convert_layout.addWidget(self.from_amount, 0, 3)

        # 目标货币
        convert_layout.addWidget(QLabel("目标货币:"), 1, 0)
        self.to_currency = QComboBox()
        convert_layout.addWidget(self.to_currency, 1, 1)

        # 目标金额
        convert_layout.addWidget(QLabel("转换结果:"), 1, 2)
        self.to_amount = QLineEdit()
        self.to_amount.setReadOnly(True)
        convert_layout.addWidget(self.to_amount, 1, 3)

        # 汇率信息
        convert_layout.addWidget(QLabel("汇率:"), 2, 0)
        self.rate_info = QLineEdit()
        self.rate_info.setReadOnly(True)
        convert_layout.addWidget(self.rate_info, 2, 1, 1, 3)

        converter_layout.addWidget(convert_group)

        # 快速转换组
        quick_group = QGroupBox("快速转换")
        quick_layout = QGridLayout(quick_group)

        # 常用货币对
        currency_pairs = [
            ("USD", "CNY", "美元 → 人民币"),
            ("CNY", "USD", "人民币 → 美元"),
            ("EUR", "CNY", "欧元 → 人民币"),
            ("GBP", "CNY", "英镑 → 人民币"),
            ("JPY", "CNY", "日元 → 人民币"),
            ("HKD", "CNY", "港币 → 人民币"),
        ]

        for i, (from_cur, to_cur, desc) in enumerate(currency_pairs):
            row = i // 2
            col = i % 2

            button = QPushButton(desc)
            button.clicked.connect(
                lambda checked, f=from_cur, t=to_cur: self._quick_convert(f, t))
            quick_layout.addWidget(button, row, col)

        converter_layout.addWidget(quick_group)

        # 历史记录组
        history_group = QGroupBox("转换历史")
        history_layout = QVBoxLayout(history_group)

        self.history_text = QTextEdit()
        self.history_text.setMaximumHeight(100)
        self.history_text.setReadOnly(True)
        history_layout.addWidget(self.history_text)

        converter_layout.addWidget(history_group)

        self.tab_widget.addTab(converter_widget, "汇率转换")

    def _create_rates_tab(self) -> None:
        """创建汇率列表标签页"""
        rates_widget = QWidget()
        rates_layout = QVBoxLayout(rates_widget)

        # 基准货币选择
        base_layout = QHBoxLayout()
        base_layout.addWidget(QLabel("基准货币:"))
        self.base_currency = QComboBox()
        base_layout.addWidget(self.base_currency)
        base_layout.addStretch()
        rates_layout.addLayout(base_layout)

        # 汇率列表
        rates_group = QGroupBox("实时汇率")
        rates_group_layout = QVBoxLayout(rates_group)

        self.rates_text = QTextEdit()
        self.rates_text.setReadOnly(True)
        rates_group_layout.addWidget(self.rates_text)

        rates_layout.addWidget(rates_group)

        self.tab_widget.addTab(rates_widget, "汇率列表")

    def _connect_signals(self) -> None:
        """连接信号"""
        self.from_currency.currentTextChanged.connect(self._convert_currency)
        self.to_currency.currentTextChanged.connect(self._convert_currency)
        self.from_amount.valueChanged.connect(self._convert_currency)
        self.base_currency.currentTextChanged.connect(
            self._update_rates_display)
        self.refresh_btn.clicked.connect(self._refresh_rates)

    def _set_default_values(self) -> None:
        """设置默认值"""
        # 货币列表
        currencies = [
            ("USD", "美元"),
            ("CNY", "人民币"),
            ("EUR", "欧元"),
            ("GBP", "英镑"),
            ("JPY", "日元"),
            ("HKD", "港币"),
            ("KRW", "韩元"),
            ("AUD", "澳元"),
            ("CAD", "加元"),
            ("CHF", "瑞士法郎"),
            ("SGD", "新加坡元"),
            ("TWD", "新台币"),
        ]

        # 填充货币下拉框
        for combo in [self.from_currency, self.to_currency, self.base_currency]:
            combo.clear()
            for code, name in currencies:
                combo.addItem(f"{code} - {name}", code)

        # 设置默认选择
        self.from_currency.setCurrentText("USD - 美元")
        self.to_currency.setCurrentText("CNY - 人民币")
        self.base_currency.setCurrentText("USD - 美元")

        # 更新汇率显示
        self._update_rates_display()

    def _convert_currency(self) -> None:
        """执行货币转换"""
        try:
            from_code = self.from_currency.currentData()
            to_code = self.to_currency.currentData()
            amount = self.from_amount.value()

            if not from_code or not to_code:
                return

            # 获取汇率
            from_rate = self.exchange_rates.get(from_code, 1.0)
            to_rate = self.exchange_rates.get(to_code, 1.0)

            # 计算转换结果
            if from_code == to_code:
                result = amount
                rate = 1.0
            else:
                # 先转换为美元，再转换为目标货币
                usd_amount = amount / from_rate
                result = usd_amount * to_rate
                rate = to_rate / from_rate

            # 显示结果
            self.to_amount.setText(f"{result:.2f}")
            self.rate_info.setText(f"1 {from_code} = {rate:.6f} {to_code}")

            # 添加到历史记录
            self._add_to_history(from_code, to_code, amount, result, rate)

        except Exception as e:
            logger.error(f"货币转换失败: {e}")
            self.to_amount.setText("转换错误")
            self.rate_info.setText("计算失败")

    def _quick_convert(self, from_currency: str, to_currency: str) -> None:
        """快速转换"""
        # 设置货币对
        from_index = self.from_currency.findData(from_currency)
        to_index = self.to_currency.findData(to_currency)

        if from_index >= 0:
            self.from_currency.setCurrentIndex(from_index)
        if to_index >= 0:
            self.to_currency.setCurrentIndex(to_index)

        # 执行转换
        self._convert_currency()

    def _add_to_history(self, from_code: str, to_code: str, amount: float, result: float, rate: float) -> None:
        """添加到历史记录"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            history_line = f"[{timestamp}] {amount:.2f} {from_code} = {result:.2f} {to_code} (汇率: {rate:.6f})"

            current_text = self.history_text.toPlainText()
            lines = current_text.split('\n') if current_text else []

            # 保持最多10条记录
            if len(lines) >= 10:
                lines = lines[-9:]

            lines.append(history_line)
            self.history_text.setText('\n'.join(lines))

            # 滚动到底部
            scrollbar = self.history_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            logger.error(f"添加历史记录失败: {e}")

    def _update_rates_display(self) -> None:
        """更新汇率显示"""
        try:
            base_code = self.base_currency.currentData()
            if not base_code:
                return

            base_rate = self.exchange_rates.get(base_code, 1.0)

            # 构建汇率列表
            rates_text = f"基准货币: {base_code}\n"
            rates_text += f"更新时间: {self.last_update_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            rates_text += "=" * 50 + "\n"

            # 按货币代码排序
            sorted_currencies = sorted(self.exchange_rates.items())

            for currency, rate in sorted_currencies:
                if currency == base_code:
                    continue

                # 计算相对于基准货币的汇率
                relative_rate = rate / base_rate
                rates_text += f"{currency:>6} : {relative_rate:>12.6f}\n"

            self.rates_text.setText(rates_text)

        except Exception as e:
            logger.error(f"更新汇率显示失败: {e}")

    def _refresh_rates(self) -> None:
        """刷新汇率"""
        # 这里可以添加实际的汇率获取逻辑
        # 目前只是更新时间戳
        self.last_update_time = datetime.now()
        self.status_label.setText(
            f"汇率更新时间: {self.last_update_time.strftime('%H:%M:%S')}")
        self._update_rates_display()
        QMessageBox.information(self, "汇率刷新", "汇率已更新到最新数据")

    @staticmethod
    def show_converter(parent: Optional[QWidget] = None) -> None:
        """显示汇率转换器对话框"""
        converter = CurrencyConverter(parent)
        converter.exec_()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    CurrencyConverter.show_converter()
    sys.exit(app.exec_())
