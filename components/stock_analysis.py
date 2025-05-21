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
from components.market_sentiment import MarketSentimentWidget
import pandas as pd
from components.custom_stock_manager import CustomStockManagerDialog


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
        # 创建主布局
        self.main_layout = QVBoxLayout(self)

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

        # 新增：市场情绪卡片
        self.create_market_sentiment_card(left_layout)

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
        self.fundamental_table.setStyleSheet("""
            QTableWidget {
                background-color: #f5f5f5;
                alternate-background-color: #e9e9e9;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

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
        self.technical_table.setStyleSheet("""
            QTableWidget {
                background-color: #f5f5f5;
                alternate-background-color: #e9e9e9;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

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

    def create_market_sentiment_card(self, layout):
        """创建市场情绪卡片"""
        group = QGroupBox("市场情绪")
        group_layout = QVBoxLayout(group)

        # 获取市场情绪数据
        sentiment_data = {}
        if self.data_manager and hasattr(self.data_manager, 'get_market_sentiment'):
            try:
                sentiment_data = self.data_manager.get_market_sentiment()
                if self.log_manager:
                    self.log_manager.log(
                        f"[调试] 获取市场情绪数据: {sentiment_data}", LogLevel.DEBUG)
            except Exception as e:
                sentiment_data = {}
                if self.log_manager:
                    self.log_manager.log(f"[调试] 获取市场情绪失败: {e}", LogLevel.ERROR)

        # 展示核心指标
        if not sentiment_data or not sentiment_data.get('sentiment_index'):
            if self.log_manager:
                self.log_manager.log(
                    "[调试] 市场情绪数据为空或无sentiment_index字段", LogLevel.WARNING)
            label = QLabel("暂无市场情绪数据")
            label.setStyleSheet("font-weight: bold; color: #999999;")
            group_layout.addWidget(label)
        else:
            index = sentiment_data.get('sentiment_index', 'N/A')
            heat = sentiment_data.get('volume_ratio', 'N/A')
            advance = sentiment_data.get(
                'advance_decline', {}).get('advance', 'N/A')
            decline = sentiment_data.get(
                'advance_decline', {}).get('decline', 'N/A')

            if self.log_manager:
                self.log_manager.log(
                    f"[调试] 展示市场情绪: index={index}, heat={heat}, advance={advance}, decline={decline}", LogLevel.DEBUG)
            label = QLabel(
                f"情绪指数: {index}   热度: {heat}   涨家: {advance}   跌家: {decline}")
            label.setStyleSheet("font-weight: bold; color: #2196F3;")
            group_layout.addWidget(label)

        # 详情按钮
        btn = QPushButton("查看市场情绪详情")
        btn.clicked.connect(self.show_market_sentiment_dialog)
        group_layout.addWidget(btn)

        layout.addWidget(group)

    def show_market_sentiment_dialog(self):
        """弹出市场情绪分析多级弹窗"""
        if self.log_manager:
            self.log_manager.log("[调试] 打开市场情绪分析弹窗", LogLevel.DEBUG)
        # 一级弹窗：市场情绪主面板
        dlg = QDialog(self)
        dlg.setWindowTitle("市场情绪分析")
        dlg.setMinimumSize(900, 600)
        vbox = QVBoxLayout(dlg)
        sentiment_widget = MarketSentimentWidget(
            parent=dlg, data_manager=self.data_manager, log_manager=self.log_manager)
        vbox.addWidget(sentiment_widget)
        # 二级弹窗按钮
        btn_detail = QPushButton("更多情绪历史与统计")
        vbox.addWidget(btn_detail)

        def show_detail():
            if self.log_manager:
                self.log_manager.log("[调试] 打开市场情绪历史与统计弹窗", LogLevel.DEBUG)
            detail_dlg = QDialog(dlg)
            detail_dlg.setWindowTitle("市场情绪历史与统计")
            detail_dlg.setMinimumSize(1200, 700)
            detail_layout = QVBoxLayout(detail_dlg)
            # 指数/行业/概念/自选股选择下拉框
            index_map = {
                "上证指数": "000001",
                "深证成指": "399001",
                "创业板指": "399006"
            }
            industry_list = []
            if hasattr(self.data_manager, 'get_industries'):
                try:
                    industry_dict = self.data_manager.get_industries()
                    industry_list = list(industry_dict.keys())
                    if self.log_manager:
                        self.log_manager.log(
                            f"[调试] 获取行业列表: {industry_list}", LogLevel.DEBUG)
                except Exception as e:
                    industry_list = []
                    if self.log_manager:
                        self.log_manager.log(
                            f"[调试] 获取行业列表失败: {e}", LogLevel.ERROR)
            concept_list = []
            if hasattr(self.data_manager, 'get_concept_list'):
                try:
                    concept_df = self.data_manager.get_concept_list()
                    if not concept_df.empty and 'name' in concept_df.columns:
                        concept_list = list(concept_df['name'])
                    if self.log_manager:
                        self.log_manager.log(
                            f"[调试] 获取概念列表: {concept_list}", LogLevel.DEBUG)
                except Exception as e:
                    concept_list = []
                    if self.log_manager:
                        self.log_manager.log(
                            f"[调试] 获取概念列表失败: {e}", LogLevel.ERROR)
            # 新增自选股
            select_combo = QComboBox()
            select_combo.addItem("[大盘指数] 上证指数")
            select_combo.addItem("[大盘指数] 深证成指")
            select_combo.addItem("[大盘指数] 创业板指")
            for ind in industry_list:
                select_combo.addItem(f"[行业] {ind}")
            for c in concept_list:
                select_combo.addItem(f"[概念] {c}")
            select_combo.addItem("[自选股] 我的自选")
            detail_layout.addWidget(QLabel("选择指数/行业/概念/自选股："))
            detail_layout.addWidget(select_combo)
            chart_canvas = None
            stat_label = QLabel()
            df = None
            last_extreme = None

            def refresh_chart():
                nonlocal chart_canvas, stat_label, df, last_extreme
                if chart_canvas:
                    detail_layout.removeWidget(chart_canvas)
                    chart_canvas.setParent(None)
                text = select_combo.currentText()
                is_index = text.startswith("[大盘指数]")
                is_industry = text.startswith("[行业]")
                is_concept = text.startswith("[概念]")
                is_custom = text.startswith("[自选股]")
                code, industry, concept, custom = None, None, None, False
                if is_index:
                    for k, v in index_map.items():
                        if k in text:
                            code = v
                            break
                elif is_industry:
                    industry = text.replace("[行业] ", "")
                elif is_concept:
                    concept = text.replace("[概念] ", "")
                elif is_custom:
                    custom = True
                sentiment_history = []
                if hasattr(self.data_manager, 'get_market_sentiment_history'):
                    try:
                        if custom and hasattr(self.data_manager, 'get_custom_stocks'):
                            stock_list = self.data_manager.get_custom_stocks()
                            sentiment_history = self.data_manager.get_market_sentiment_history(
                                days=30, custom_stocks=stock_list)
                        else:
                            sentiment_history = self.data_manager.get_market_sentiment_history(
                                days=30, code=code, industry=industry, concept=concept)
                        if self.log_manager:
                            self.log_manager.log(
                                f"[调试] 获取市场情绪历史: {sentiment_history}", LogLevel.DEBUG)
                    except Exception as e:
                        sentiment_history = []
                        if self.log_manager:
                            self.log_manager.log(
                                f"[调试] 获取市场情绪历史失败: {e}", LogLevel.ERROR)
                if not sentiment_history:
                    current = self.data_manager.get_market_sentiment() if self.data_manager else {}
                    sentiment_history = [{"date": pd.Timestamp.now(
                    ), "sentiment_index": current.get("sentiment_index", 50)}]
                    if self.log_manager:
                        self.log_manager.log(
                            "[调试] 市场情绪历史为空，使用当前数据占位", LogLevel.WARNING)
                df = pd.DataFrame(sentiment_history)
                fig = Figure(figsize=(10, 4))
                chart_canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)
                if not df.empty and "sentiment_index" in df:
                    x = df["date"]
                    y = df["sentiment_index"]
                    ax.plot(x, y, marker="o", color="#2196F3", label="情绪指数")
                    ax.fill_between(x, y, 80, where=(y >= 80),
                                    color="#00C853", alpha=0.3, label="极度乐观")
                    ax.fill_between(x, y, 20, where=(y <= 20),
                                    color="#FF1744", alpha=0.3, label="极度悲观")
                    ax.set_title(f"{text}近30天市场情绪趋势")
                    ax.set_xlabel("日期")
                    ax.set_ylabel("情绪指数")
                    ax.legend()
                    if y.iloc[-1] >= 80 and last_extreme != 'high':
                        QMessageBox.warning(
                            detail_dlg, "市场情绪预警", f"当前情绪指数{y.iloc[-1]:.2f}，已进入极度乐观区间！")
                        last_extreme = 'high'
                    elif y.iloc[-1] <= 20 and last_extreme != 'low':
                        QMessageBox.warning(
                            detail_dlg, "市场情绪预警", f"当前情绪指数{y.iloc[-1]:.2f}，已进入极度悲观区间！")
                        last_extreme = 'low'
                    elif 20 < y.iloc[-1] < 80:
                        last_extreme = None
                else:
                    ax.text(0.5, 0.5, "暂无历史数据", ha="center", va="center")

                def on_click(event):
                    if event.inaxes == ax and not df.empty:
                        ind = int(event.xdata)
                        if 0 <= ind < len(df):
                            row = df.iloc[ind]
                            date = row["date"]
                            # 弹窗显示该日行情表现
                            info = self.data_manager.get_market_day_info(
                                date, code=code, industry=industry, concept=concept, custom_stocks=stock_list if custom else None)
                            msg = f"{date:%Y-%m-%d}行情摘要：\n" + str(info)
                            QMessageBox.information(detail_dlg, "行情联动", msg)
                fig.canvas.mpl_connect('button_press_event', on_click)
                detail_layout.insertWidget(3, chart_canvas)
                if not df.empty and "sentiment_index" in df:
                    min_val = df["sentiment_index"].min()
                    max_val = df["sentiment_index"].max()
                    mean_val = df["sentiment_index"].mean()
                    std_val = df["sentiment_index"].std()
                    q25 = df["sentiment_index"].quantile(0.25)
                    q50 = df["sentiment_index"].quantile(0.5)
                    q75 = df["sentiment_index"].quantile(0.75)
                    min_date = df["date"][df["sentiment_index"] == min_val].iloc[0] if (
                        df["sentiment_index"] == min_val).any() else "-"
                    max_date = df["date"][df["sentiment_index"] == max_val].iloc[0] if (
                        df["sentiment_index"] == max_val).any() else "-"
                    stat_label.setText(
                        f"最低: {min_val:.2f}({min_date:%Y-%m-%d})  最高: {max_val:.2f}({max_date:%Y-%m-%d})  均值: {mean_val:.2f}  波动率: {std_val:.2f}\n"
                        f"分位数: Q25={q25:.2f}  Q50={q50:.2f}  Q75={q75:.2f}"
                    )
                    stat_label.setStyleSheet("font-weight: bold; color: #333;")
                else:
                    stat_label.setText("")
                detail_layout.addWidget(stat_label)
            select_combo.currentIndexChanged.connect(refresh_chart)

            def export_data():
                if df is not None and not df.empty:
                    file_path, _ = QFileDialog.getSaveFileName(
                        detail_dlg, "导出情绪历史数据", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
                    if file_path:
                        if file_path.endswith('.xlsx'):
                            df.to_excel(file_path, index=False)
                        else:
                            df.to_csv(file_path, index=False)
            export_btn = QPushButton("导出数据")
            export_btn.clicked.connect(export_data)
            detail_layout.addWidget(export_btn)
            refresh_chart()
            detail_dlg.exec_()
        btn_detail.clicked.connect(show_detail)
        dlg.exec_()

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
