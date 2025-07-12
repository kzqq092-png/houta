"""
费率计算工具

提供股票交易费率、手续费、印花税等计算功能。
"""

import logging
from typing import Optional, Dict, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QWidget, QLabel, QComboBox,
    QDoubleSpinBox, QGroupBox, QTextEdit, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class CommissionCalculator(QDialog):
    """费率计算器对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化费率计算器

        Args:
            parent: 父窗口组件
        """
        super().__init__(parent)
        self.setWindowTitle("费率计算器")
        self.setFixedSize(500, 600)

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

        # 创建股票交易费率计算标签页
        self._create_stock_tab()

        # 创建费率对比标签页
        self._create_comparison_tab()

        # 创建计算按钮
        button_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("计算费用")
        self.reset_btn = QPushButton("重置")
        button_layout.addWidget(self.calculate_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def _create_stock_tab(self) -> None:
        """创建股票交易费率计算标签页"""
        stock_widget = QWidget()
        stock_layout = QVBoxLayout(stock_widget)
        stock_layout.setSpacing(15)

        # 交易信息组
        trade_group = QGroupBox("交易信息")
        trade_layout = QGridLayout(trade_group)

        # 交易类型
        trade_layout.addWidget(QLabel("交易类型:"), 0, 0)
        self.trade_type = QComboBox()
        self.trade_type.addItems(["买入", "卖出"])
        trade_layout.addWidget(self.trade_type, 0, 1)

        # 股票价格
        trade_layout.addWidget(QLabel("股票价格:"), 1, 0)
        self.stock_price = QDoubleSpinBox()
        self.stock_price.setRange(0.01, 9999.99)
        self.stock_price.setDecimals(2)
        self.stock_price.setSuffix(" 元")
        trade_layout.addWidget(self.stock_price, 1, 1)

        # 交易数量
        trade_layout.addWidget(QLabel("交易数量:"), 2, 0)
        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(100, 999999900)
        self.quantity.setDecimals(0)
        self.quantity.setSuffix(" 股")
        self.quantity.setSingleStep(100)
        trade_layout.addWidget(self.quantity, 2, 1)

        # 交易金额（自动计算）
        trade_layout.addWidget(QLabel("交易金额:"), 3, 0)
        self.trade_amount = QLineEdit()
        self.trade_amount.setReadOnly(True)
        trade_layout.addWidget(self.trade_amount, 3, 1)

        stock_layout.addWidget(trade_group)

        # 费率设置组
        rate_group = QGroupBox("费率设置")
        rate_layout = QGridLayout(rate_group)

        # 佣金费率
        rate_layout.addWidget(QLabel("佣金费率:"), 0, 0)
        self.commission_rate = QDoubleSpinBox()
        self.commission_rate.setRange(0.0001, 0.01)
        self.commission_rate.setDecimals(4)
        self.commission_rate.setSuffix(" %")
        self.commission_rate.setSingleStep(0.0001)
        rate_layout.addWidget(self.commission_rate, 0, 1)

        # 最低佣金
        rate_layout.addWidget(QLabel("最低佣金:"), 1, 0)
        self.min_commission = QDoubleSpinBox()
        self.min_commission.setRange(0.01, 100.0)
        self.min_commission.setDecimals(2)
        self.min_commission.setSuffix(" 元")
        rate_layout.addWidget(self.min_commission, 1, 1)

        # 印花税费率（仅卖出）
        rate_layout.addWidget(QLabel("印花税费率:"), 2, 0)
        self.stamp_tax_rate = QDoubleSpinBox()
        self.stamp_tax_rate.setRange(0.0, 0.01)
        self.stamp_tax_rate.setDecimals(4)
        self.stamp_tax_rate.setSuffix(" %")
        rate_layout.addWidget(self.stamp_tax_rate, 2, 1)

        # 过户费费率
        rate_layout.addWidget(QLabel("过户费费率:"), 3, 0)
        self.transfer_fee_rate = QDoubleSpinBox()
        self.transfer_fee_rate.setRange(0.0, 0.01)
        self.transfer_fee_rate.setDecimals(4)
        self.transfer_fee_rate.setSuffix(" %")
        rate_layout.addWidget(self.transfer_fee_rate, 3, 1)

        stock_layout.addWidget(rate_group)

        # 计算结果组
        result_group = QGroupBox("计算结果")
        result_layout = QGridLayout(result_group)

        # 佣金
        result_layout.addWidget(QLabel("佣金:"), 0, 0)
        self.commission_result = QLineEdit()
        self.commission_result.setReadOnly(True)
        result_layout.addWidget(self.commission_result, 0, 1)

        # 印花税
        result_layout.addWidget(QLabel("印花税:"), 1, 0)
        self.stamp_tax_result = QLineEdit()
        self.stamp_tax_result.setReadOnly(True)
        result_layout.addWidget(self.stamp_tax_result, 1, 1)

        # 过户费
        result_layout.addWidget(QLabel("过户费:"), 2, 0)
        self.transfer_fee_result = QLineEdit()
        self.transfer_fee_result.setReadOnly(True)
        result_layout.addWidget(self.transfer_fee_result, 2, 1)

        # 总费用
        result_layout.addWidget(QLabel("总费用:"), 3, 0)
        self.total_fee_result = QLineEdit()
        self.total_fee_result.setReadOnly(True)
        result_layout.addWidget(self.total_fee_result, 3, 1)

        stock_layout.addWidget(result_group)

        self.tab_widget.addTab(stock_widget, "股票交易费率")

    def _create_comparison_tab(self) -> None:
        """创建费率对比标签页"""
        comparison_widget = QWidget()
        comparison_layout = QVBoxLayout(comparison_widget)

        # 券商费率对比
        broker_group = QGroupBox("主要券商费率对比")
        broker_layout = QVBoxLayout(broker_group)

        self.broker_comparison = QTextEdit()
        self.broker_comparison.setReadOnly(True)
        self.broker_comparison.setMaximumHeight(200)
        broker_layout.addWidget(self.broker_comparison)

        comparison_layout.addWidget(broker_group)

        # 费率计算说明
        help_group = QGroupBox("费率计算说明")
        help_layout = QVBoxLayout(help_group)

        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        help_layout.addWidget(self.help_text)

        comparison_layout.addWidget(help_group)

        self.tab_widget.addTab(comparison_widget, "费率对比")

    def _connect_signals(self) -> None:
        """连接信号"""
        self.stock_price.valueChanged.connect(self._update_trade_amount)
        self.quantity.valueChanged.connect(self._update_trade_amount)
        self.calculate_btn.clicked.connect(self._calculate_fees)
        self.reset_btn.clicked.connect(self._reset_values)

    def _set_default_values(self) -> None:
        """设置默认值"""
        # 设置默认交易参数
        self.stock_price.setValue(10.00)
        self.quantity.setValue(1000)

        # 设置默认费率
        self.commission_rate.setValue(0.03)  # 万分之3
        self.min_commission.setValue(5.0)    # 最低5元
        self.stamp_tax_rate.setValue(0.1)    # 千分之1
        self.transfer_fee_rate.setValue(0.002)  # 万分之0.2

        # 更新交易金额
        self._update_trade_amount()

        # 设置券商对比信息
        self._set_broker_comparison()

        # 设置帮助信息
        self._set_help_text()

    def _update_trade_amount(self) -> None:
        """更新交易金额"""
        try:
            amount = self.stock_price.value() * self.quantity.value()
            self.trade_amount.setText(f"{amount:,.2f} 元")
        except Exception as e:
            logger.error(f"更新交易金额失败: {e}")

    def _calculate_fees(self) -> None:
        """计算费用"""
        try:
            # 获取交易参数
            price = Decimal(str(self.stock_price.value()))
            qty = Decimal(str(self.quantity.value()))
            trade_amount = price * qty

            # 获取费率参数
            commission_rate = Decimal(str(self.commission_rate.value() / 100))
            min_commission = Decimal(str(self.min_commission.value()))
            stamp_tax_rate = Decimal(str(self.stamp_tax_rate.value() / 100))
            transfer_fee_rate = Decimal(
                str(self.transfer_fee_rate.value() / 100))

            # 计算佣金
            commission = max(trade_amount * commission_rate, min_commission)
            commission = commission.quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)

            # 计算印花税（仅卖出时收取）
            if self.trade_type.currentText() == "卖出":
                stamp_tax = trade_amount * stamp_tax_rate
                stamp_tax = stamp_tax.quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                stamp_tax = Decimal('0')

            # 计算过户费
            transfer_fee = trade_amount * transfer_fee_rate
            transfer_fee = transfer_fee.quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)

            # 计算总费用
            total_fee = commission + stamp_tax + transfer_fee

            # 显示结果
            self.commission_result.setText(f"{float(commission):.2f} 元")
            self.stamp_tax_result.setText(f"{float(stamp_tax):.2f} 元")
            self.transfer_fee_result.setText(f"{float(transfer_fee):.2f} 元")
            self.total_fee_result.setText(f"{float(total_fee):.2f} 元")

        except Exception as e:
            logger.error(f"费用计算失败: {e}")

    def _reset_values(self) -> None:
        """重置值"""
        self._set_default_values()
        # 清空结果
        for result_field in [self.commission_result, self.stamp_tax_result,
                             self.transfer_fee_result, self.total_fee_result]:
            result_field.clear()

    def _set_broker_comparison(self) -> None:
        """设置券商费率对比信息"""
        comparison_text = """
主要券商费率对比（仅供参考）：

券商          佣金费率    最低佣金    印花税      过户费
华泰证券      万2.5      5元        千1(卖)     万0.2
中信证券      万2.5      5元        千1(卖)     万0.2  
国泰君安      万2.5      5元        千1(卖)     万0.2
招商证券      万2.5      5元        千1(卖)     万0.2

注：实际费率请以券商最新公布为准
        """
        self.broker_comparison.setText(comparison_text.strip())

    def _set_help_text(self) -> None:
        """设置帮助信息"""
        help_text = """
股票交易费用计算说明：

1. 佣金：由证券公司收取，买卖双向收取
2. 印花税：由国家征收，仅卖出时收取，费率千分之1
3. 过户费：由中国结算收取，买卖双向收取，费率万分之0.2

计算公式：
- 佣金 = max(交易金额 × 佣金费率, 最低佣金)
- 印花税 = 交易金额 × 印花税费率（仅卖出）
- 过户费 = 交易金额 × 过户费费率
        """
        self.help_text.setText(help_text.strip())

    @staticmethod
    def show_calculator(parent: Optional[QWidget] = None) -> None:
        """显示费率计算器对话框"""
        calculator = CommissionCalculator(parent)
        calculator.exec_()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    CommissionCalculator.show_calculator()
    sys.exit(app.exec_())
