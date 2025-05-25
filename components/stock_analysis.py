"""
个股分析组件

提供个股的详细分析功能，包括基本面分析、技术指标分析、K线图展示等
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtChart import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import time
import logging
from typing import Dict, Any, Optional, List, Union
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel
from gui.ui_components import BaseAnalysisPanel
from components.template_manager import TemplateManager
from components.custom_stock_manager import CustomStockManagerDialog

try:
    from PyQt5.QtCore import qRegisterMetaType, QVector
    qRegisterMetaType(QVector[int], "QVector<int>")
except Exception:
    pass


class StockAnalysisWidget(BaseAnalysisPanel):
    """个股分析组件，继承统一分析面板基类"""

    def __init__(self, parent=None, data_manager=None, log_manager=None):
        """初始化个股分析组件

        Args:
            parent: 父窗口
            data_manager: 数据管理器实例
            log_manager: 日志管理器实例
        """
        super().__init__(parent, log_manager=log_manager)
        self.data_manager = data_manager
        self.template_manager = TemplateManager(
            template_dir="templates/stock_analysis")
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.main_layout = self.layout()

        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(splitter)

        # 创建左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 创建基本信息卡片
        self.create_basic_info_cards(left_layout)

        # 创建基本面分析表格
        self.create_fundamental_table(left_layout)

        # 创建技术指标表格
        self.create_technical_table(left_layout)

        # 添加左侧面板到分割器
        splitter.addWidget(left_panel)

        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 创建K线图
        self.create_kline_chart(right_layout)

        # 创建技术指标图表
        self.create_technical_charts(right_layout)

        # 添加右侧面板到分割器
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setSizes([300, 700])

        # 创建控制按钮
        self.create_control_buttons(self.main_layout)

        # 增加分析周期参数
        self.period_spin = QSpinBox()
        self.period_spin.setRange(1, 365)
        self.period_spin.setValue(30)
        self.add_param_widget("分析周期(天)", self.period_spin)

        # 增加指标选择
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(
            ["MA", "MACD", "RSI", "KDJ", "BOLL", "ATR"])
        self.add_param_widget("分析指标", self.indicator_combo)

        # 模板管理按钮
        btn = QPushButton("模板管理")
        btn.clicked.connect(self.show_template_manager_dialog)
        self.main_layout.addWidget(btn)

    def create_basic_info_cards(self, layout):
        """创建基本信息卡片"""
        cards_layout = QGridLayout()

        # 定义基本信息
        info_items = [
            ("代码", "000001"),
            ("名称", "平安银行"),
            ("行业", "银行"),
            ("地区", "深圳"),
            ("上市日期", "1991-04-03"),
            ("总股本", "194.06亿"),
            ("流通股本", "194.06亿"),
            ("市盈率", "8.23"),
            ("市净率", "0.89"),
            ("每股收益", "1.23元"),
            ("每股净资产", "15.67元"),
            ("ROE", "15.23%")
        ]

        for i, (name, value) in enumerate(info_items):
            card = QFrame()
            card.setFrameStyle(QFrame.Box | QFrame.Raised)
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)

            card_layout = QVBoxLayout(card)

            # 名称标签
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #666666;")
            card_layout.addWidget(name_label)

            # 值标签
            value_label = QLabel(value)
            value_label.setStyleSheet("font-weight: bold;")
            card_layout.addWidget(value_label)

            cards_layout.addWidget(card, i // 3, i % 3)

        layout.addLayout(cards_layout)

    def create_fundamental_table(self, layout):
        """创建基本面分析表格"""
        group = QGroupBox("基本面分析")
        group_layout = QVBoxLayout(group)

        self.fundamental_table = QTableWidget()
        self.fundamental_table.setColumnCount(4)
        self.fundamental_table.setRowCount(10)
        self.fundamental_table.setHorizontalHeaderLabels(
            ["指标", "数值", "同比", "行业平均"])

        # 设置表格样式
        self.fundamental_table.setStyleSheet('''
            QTableWidget {border: 1px solid #b0b0b0; border-radius: 2px; background: #fff; font-size: 13px;}
            QHeaderView::section {background: #444; color: #fff; font-weight: bold; border: 1px solid #b0b0b0; height: 28px; padding-left: 8px;}
            QTableWidget::item {border: 1px solid #b0b0b0; background: #fff;}
            QTableWidget::item:selected {background: #e3f2fd; color: #1976d2;}
            QTableWidget::item:hover {background: #f5f5f5;}
        ''')
        self.fundamental_table.setAlternatingRowColors(True)

        group_layout.addWidget(self.fundamental_table)
        layout.addWidget(group)

    def create_technical_table(self, layout):
        """创建技术指标表格"""
        group = QGroupBox("技术指标")
        group_layout = QVBoxLayout(group)

        self.technical_table = QTableWidget()
        self.technical_table.setColumnCount(4)
        self.technical_table.setRowCount(10)
        self.technical_table.setHorizontalHeaderLabels(
            ["指标", "数值", "信号", "状态"])

        # 设置表格样式
        self.technical_table.setStyleSheet('''
            QTableWidget {border: 1px solid #b0b0b0; border-radius: 2px; background: #fff; font-size: 13px;}
            QHeaderView::section {background: #444; color: #fff; font-weight: bold; border: 1px solid #b0b0b0; height: 28px; padding-left: 8px;}
            QTableWidget::item {border: 1px solid #b0b0b0; background: #fff;}
            QTableWidget::item:selected {background: #e3f2fd; color: #1976d2;}
            QTableWidget::item:hover {background: #f5f5f5;}
        ''')
        self.technical_table.setAlternatingRowColors(True)

        group_layout.addWidget(self.technical_table)
        layout.addWidget(group)

    def create_kline_chart(self, layout):
        """创建K线图"""
        group = QGroupBox("K线图")
        group_layout = QVBoxLayout(group)

        # 创建图表
        self.kline_figure = Figure(figsize=(8, 4))
        self.kline_canvas = FigureCanvas(self.kline_figure)
        group_layout.addWidget(self.kline_canvas)

        layout.addWidget(group)

    def create_technical_charts(self, layout):
        """创建技术指标图表"""
        group = QGroupBox("技术指标图表")
        group_layout = QVBoxLayout(group)

        # 创建图表
        self.technical_figure = Figure(figsize=(8, 4))
        self.technical_canvas = FigureCanvas(self.technical_figure)
        group_layout.addWidget(self.technical_canvas)

        layout.addWidget(group)

    def create_control_buttons(self, layout):
        """创建控制按钮"""
        button_layout = QHBoxLayout()

        # 导出数据按钮
        export_button = QPushButton("导出数据")
        export_button.clicked.connect(self.export_data)
        button_layout.addWidget(export_button)

        # 设置预警按钮
        alert_button = QPushButton("设置预警")
        alert_button.clicked.connect(self.show_alert_dialog)
        button_layout.addWidget(alert_button)

        # 自选股管理按钮
        custom_btn = QPushButton("自选股管理")
        custom_btn.clicked.connect(self.show_custom_stock_manager)
        button_layout.addWidget(custom_btn)

        layout.addLayout(button_layout)

    def export_data(self):
        """导出数据"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出数据",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if file_path:
                # TODO: 实现数据导出逻辑
                self.log_manager.log("数据导出成功", LogLevel.INFO)

        except Exception as e:
            self.log_manager.log(f"导出数据失败: {str(e)}", LogLevel.ERROR)

    def show_alert_dialog(self):
        """显示预警设置对话框"""
        # TODO: 实现预警设置对话框
        pass

    def show_template_manager_dialog(self):
        # 复用StockScreenerWidget的模板管理对话框逻辑
        QMessageBox.information(
            self, "模板管理", "此处可集成批量模板管理UI，支持导入、导出、删除、重命名、应用等功能。")

    def validate_params(self) -> tuple[bool, str]:
        """校验所有参数控件的输入，支持QSpinBox等"""
        valid = True
        error_msgs = []
        for name, widget in self.param_widgets.items():
            widget.setStyleSheet("")
            value = widget.value() if hasattr(widget, 'value') else None
            if value is not None:
                if value < widget.minimum() or value > widget.maximum():
                    valid = False
                    error_msgs.append(
                        f"{name} 超出允许范围 [{widget.minimum()}, {widget.maximum()}]")
                    widget.setStyleSheet("border: 2px solid red;")
        return valid, "\n".join(error_msgs)

    def show_custom_stock_manager(self):
        dlg = CustomStockManagerDialog(self)
        dlg.exec_()
        # 刷新自选股相关UI（如有）

    def create_sentiment_signal_card(self, layout):
        """情绪与信号联动卡片"""
        group = QGroupBox("情绪与信号联动")
        group_layout = QVBoxLayout(group)
        # 获取市场情绪
        sentiment = self.data_manager.get_market_sentiment() if self.data_manager else {}
        index = sentiment.get('sentiment_index', 50)
        # 获取个股信号（如MACD、RSI等）
        # TODO: 这里用演示数据，实际应调用信号计算逻辑
        signal = "买入" if index > 80 else ("卖出" if index < 20 else "观望")
        label = QLabel(f"当前市场情绪: {index}，个股信号: {signal}")
        label.setStyleSheet("font-weight: bold; color: #FF9800;")
        group_layout.addWidget(label)
        # 联动提示
        if index >= 80 and signal == "买入":
            tip = "顺势买入信号！"
        elif index <= 20 and signal == "卖出":
            tip = "风险提示，建议谨慎！"
        else:
            tip = "信号中性，建议观望。"
        tip_label = QLabel(tip)
        tip_label.setStyleSheet("color: #2196F3;")
        group_layout.addWidget(tip_label)
        layout.addWidget(group)
