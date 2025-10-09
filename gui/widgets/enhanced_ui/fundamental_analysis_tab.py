#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面分析标签页
提供财务报表、公司公告、分析师评级等基本面数据的分析和展示
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QTabWidget, QFrame, QPushButton, QComboBox, QDateEdit, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QSplitter, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QDate
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from loguru import logger

from core.services.fundamental_data_manager import FundamentalDataManager
from core.services.announcement_parser import AnnouncementParser
from core.plugin_types import DataType, AssetType


class FinancialReportChart(FigureCanvas):
    """财务报表图表"""

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)

        # 创建子图
        self.ax1 = self.fig.add_subplot(221)  # 营收和利润
        self.ax2 = self.fig.add_subplot(222)  # 资产负债
        self.ax3 = self.fig.add_subplot(223)  # 现金流
        self.ax4 = self.fig.add_subplot(224)  # 财务比率

        self.setup_charts()

    def setup_charts(self):
        """设置图表样式"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        # 营收和利润
        self.ax1.set_title('营收与净利润趋势', fontsize=10, fontweight='bold')
        self.ax1.set_ylabel('金额(万元)')
        self.ax1.grid(True, alpha=0.3)

        # 资产负债
        self.ax2.set_title('资产负债结构', fontsize=10, fontweight='bold')
        self.ax2.set_ylabel('金额(万元)')
        self.ax2.grid(True, alpha=0.3)

        # 现金流
        self.ax3.set_title('现金流量分析', fontsize=10, fontweight='bold')
        self.ax3.set_ylabel('金额(万元)')
        self.ax3.grid(True, alpha=0.3)

        # 财务比率
        self.ax4.set_title('关键财务比率', fontsize=10, fontweight='bold')
        self.ax4.set_ylabel('比率')
        self.ax4.grid(True, alpha=0.3)

        self.fig.tight_layout()

    def update_financial_data(self, financial_data: List[Dict]):
        """更新财务数据图表"""
        try:
            if not financial_data:
                return

            # 清空之前的图表
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()

            self.setup_charts()

            # 准备数据
            periods = [item.get('period', '') for item in financial_data]
            revenues = [item.get('revenue', 0) / 10000 for item in financial_data]  # 转换为万元
            net_profits = [item.get('net_profit', 0) / 10000 for item in financial_data]
            total_assets = [item.get('total_assets', 0) / 10000 for item in financial_data]
            total_liabilities = [item.get('total_liabilities', 0) / 10000 for item in financial_data]
            operating_cash_flow = [item.get('operating_cash_flow', 0) / 10000 for item in financial_data]

            # 绘制营收和利润
            self.ax1.plot(periods, revenues, 'b-o', label='营业收入', linewidth=2)
            self.ax1.plot(periods, net_profits, 'r-s', label='净利润', linewidth=2)
            self.ax1.legend()
            self.ax1.tick_params(axis='x', rotation=45)

            # 绘制资产负债
            self.ax2.bar(periods, total_assets, alpha=0.7, label='总资产', color='#3498DB')
            self.ax2.bar(periods, total_liabilities, alpha=0.7, label='总负债', color='#E74C3C')
            self.ax2.legend()
            self.ax2.tick_params(axis='x', rotation=45)

            # 绘制现金流
            colors = ['#27AE60' if cf >= 0 else '#E74C3C' for cf in operating_cash_flow]
            self.ax3.bar(periods, operating_cash_flow, alpha=0.7, color=colors, label='经营现金流')
            self.ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            self.ax3.legend()
            self.ax3.tick_params(axis='x', rotation=45)

            # 计算并绘制财务比率
            roe = [(np / ta * 100) if ta != 0 else 0 for np, ta in zip(net_profits, total_assets)]
            debt_ratio = [(tl / ta * 100) if ta != 0 else 0 for tl, ta in zip(total_liabilities, total_assets)]

            self.ax4.plot(periods, roe, 'g-o', label='ROE(%)', linewidth=2)
            self.ax4.plot(periods, debt_ratio, 'orange', marker='s', label='资产负债率(%)', linewidth=2)
            self.ax4.legend()
            self.ax4.tick_params(axis='x', rotation=45)

            self.fig.tight_layout()
            self.draw()

        except Exception as e:
            logger.error(f"更新财务数据图表失败: {e}")


class FundamentalAnalysisTab(QWidget):
    """
    基本面分析标签页
    集成财务报表、公司公告、分析师评级等基本面数据分析功能
    """

    # 信号定义
    analysis_completed = pyqtSignal(dict)      # 分析完成信号
    data_updated = pyqtSignal(str, dict)       # 数据更新信号
    error_occurred = pyqtSignal(str)           # 错误信号

    def __init__(self, parent=None, fundamental_manager: FundamentalDataManager = None,
                 announcement_parser: AnnouncementParser = None):
        super().__init__(parent)

        self.fundamental_manager = fundamental_manager
        self.announcement_parser = announcement_parser
        self.current_symbol = None

        # 数据缓存
        self.financial_data_cache = {}
        self.announcement_cache = {}
        self.rating_cache = {}

        # 分析结果
        self.analysis_results = {}

        self.init_ui()

        logger.info("FundamentalAnalysisTab 初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 主要内容标签页
        main_tabs = QTabWidget()

        # 财务报表标签页
        financial_tab = self._create_financial_tab()
        main_tabs.addTab(financial_tab, "财务报表")

        # 公司公告标签页
        announcement_tab = self._create_announcement_tab()
        main_tabs.addTab(announcement_tab, "📢 公司公告")

        # 分析师评级标签页
        rating_tab = self._create_rating_tab()
        main_tabs.addTab(rating_tab, "[STAR] 分析师评级")

        # 综合分析标签页
        analysis_tab = self._create_analysis_tab()
        main_tabs.addTab(analysis_tab, "综合分析")

        layout.addWidget(main_tabs)

        # 应用样式
        self._apply_styles()

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumHeight(60)

        layout = QHBoxLayout(panel)

        # 股票代码
        layout.addWidget(QLabel("股票代码:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.addItems(["000001", "000002", "600000", "600036", "000858"])
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        layout.addWidget(self.symbol_combo)

        # 报告期数
        layout.addWidget(QLabel("报告期数:"))
        self.periods_spin = QSpinBox()
        self.periods_spin.setRange(1, 20)
        self.periods_spin.setValue(8)
        layout.addWidget(self.periods_spin)

        # 日期范围
        layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-2))
        self.start_date.setCalendarPopup(True)
        layout.addWidget(self.start_date)

        layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        layout.addWidget(self.end_date)

        layout.addStretch()

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self._refresh_all_data)
        layout.addWidget(self.refresh_btn)

        # 分析按钮
        self.analyze_btn = QPushButton("综合分析")
        self.analyze_btn.clicked.connect(self._perform_comprehensive_analysis)
        layout.addWidget(self.analyze_btn)

        return panel

    def _create_financial_tab(self) -> QWidget:
        """创建财务报表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 报表类型选择
        report_panel = QFrame()
        report_layout = QHBoxLayout(report_panel)

        report_layout.addWidget(QLabel("报表类型:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "利润表", "资产负债表", "现金流量表", "财务指标"
        ])
        self.report_type_combo.currentTextChanged.connect(self._on_report_type_changed)
        report_layout.addWidget(self.report_type_combo)

        report_layout.addStretch()

        # 导出按钮
        export_btn = QPushButton("导出报表")
        export_btn.clicked.connect(self._export_financial_data)
        report_layout.addWidget(export_btn)

        layout.addWidget(report_panel)

        # 分割器：表格和图表
        splitter = QSplitter(Qt.Vertical)

        # 财务数据表格
        self.financial_table = QTableWidget()
        self.financial_table.setAlternatingRowColors(True)
        splitter.addWidget(self.financial_table)

        # 财务图表
        self.financial_chart = FinancialReportChart()
        splitter.addWidget(self.financial_chart)

        # 设置分割比例
        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        return widget

    def _create_announcement_tab(self) -> QWidget:
        """创建公司公告标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 公告过滤面板
        filter_panel = QFrame()
        filter_layout = QHBoxLayout(filter_panel)

        filter_layout.addWidget(QLabel("公告类型:"))
        self.announcement_type_combo = QComboBox()
        self.announcement_type_combo.addItems([
            "全部", "年报", "分红", "增发", "股权激励", "重大合同", "高管变动"
        ])
        self.announcement_type_combo.currentTextChanged.connect(self._filter_announcements)
        filter_layout.addWidget(self.announcement_type_combo)

        filter_layout.addWidget(QLabel("重要性:"))
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["全部", "重大", "重要", "一般"])
        self.importance_combo.currentTextChanged.connect(self._filter_announcements)
        filter_layout.addWidget(self.importance_combo)

        filter_layout.addStretch()

        # 智能分析按钮
        smart_analysis_btn = QPushButton("智能分析")
        smart_analysis_btn.clicked.connect(self._perform_announcement_analysis)
        filter_layout.addWidget(smart_analysis_btn)

        layout.addWidget(filter_panel)

        # 分割器：公告列表和详情
        splitter = QSplitter(Qt.Horizontal)

        # 公告列表
        announcement_list_group = QGroupBox("公告列表")
        announcement_list_layout = QVBoxLayout(announcement_list_group)

        self.announcement_table = QTableWidget()
        self.announcement_table.setColumnCount(5)
        self.announcement_table.setHorizontalHeaderLabels([
            "日期", "标题", "类型", "重要性", "影响"
        ])
        self.announcement_table.setAlternatingRowColors(True)
        self.announcement_table.itemSelectionChanged.connect(self._on_announcement_selected)
        announcement_list_layout.addWidget(self.announcement_table)

        splitter.addWidget(announcement_list_group)

        # 公告详情
        detail_group = QGroupBox("公告详情")
        detail_layout = QVBoxLayout(detail_group)

        # 公告标题和基本信息
        self.announcement_title = QLabel("选择公告查看详情")
        self.announcement_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.announcement_title.setWordWrap(True)
        detail_layout.addWidget(self.announcement_title)

        # 关键信息提取
        key_info_group = QGroupBox("关键信息")
        key_info_layout = QGridLayout(key_info_group)

        self.key_info_labels = {}
        key_items = [
            ("公告日期", "date"),
            ("公告类型", "category"),
            ("重要性评级", "importance"),
            ("涉及金额", "amount"),
            ("影响评估", "impact")
        ]

        for i, (label, key) in enumerate(key_items):
            key_info_layout.addWidget(QLabel(f"{label}:"), i, 0)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            key_info_layout.addWidget(value_label, i, 1)
            self.key_info_labels[key] = value_label

        detail_layout.addWidget(key_info_group)

        # 公告内容
        self.announcement_content = QTextEdit()
        self.announcement_content.setMaximumHeight(200)
        self.announcement_content.setReadOnly(True)
        detail_layout.addWidget(self.announcement_content)

        splitter.addWidget(detail_group)

        # 设置分割比例
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)

        return widget

    def _create_rating_tab(self) -> QWidget:
        """创建分析师评级标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 评级统计面板
        stats_panel = QFrame()
        stats_layout = QGridLayout(stats_panel)

        # 评级统计标签
        self.rating_stats_labels = {}
        stats_items = [
            ("买入评级", "buy_count", 0, 0),
            ("持有评级", "hold_count", 0, 1),
            ("卖出评级", "sell_count", 0, 2),
            ("平均目标价", "avg_target_price", 1, 0),
            ("最高目标价", "max_target_price", 1, 1),
            ("最低目标价", "min_target_price", 1, 2)
        ]

        for label, key, row, col in stats_items:
            stats_layout.addWidget(QLabel(f"{label}:"), row, col * 2)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            stats_layout.addWidget(value_label, row, col * 2 + 1)
            self.rating_stats_labels[key] = value_label

        layout.addWidget(stats_panel)

        # 评级详情表格
        rating_group = QGroupBox("分析师评级详情")
        rating_layout = QVBoxLayout(rating_group)

        self.rating_table = QTableWidget()
        self.rating_table.setColumnCount(6)
        self.rating_table.setHorizontalHeaderLabels([
            "日期", "机构", "分析师", "评级", "目标价", "理由"
        ])
        self.rating_table.setAlternatingRowColors(True)
        rating_layout.addWidget(self.rating_table)

        layout.addWidget(rating_group)

        return widget

    def _create_analysis_tab(self) -> QWidget:
        """创建综合分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 分析结果概览
        overview_group = QGroupBox("分析概览")
        overview_layout = QGridLayout(overview_group)

        # 综合评分
        self.overall_score_label = QLabel("--")
        self.overall_score_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.overall_score_label.setAlignment(Qt.AlignCenter)
        self.overall_score_label.setStyleSheet("color: #2E86AB; border: 2px solid #2E86AB; border-radius: 10px; padding: 10px;")
        overview_layout.addWidget(QLabel("综合评分:"), 0, 0)
        overview_layout.addWidget(self.overall_score_label, 0, 1)

        # 投资建议
        self.investment_advice_label = QLabel("--")
        self.investment_advice_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.investment_advice_label.setAlignment(Qt.AlignCenter)
        overview_layout.addWidget(QLabel("投资建议:"), 0, 2)
        overview_layout.addWidget(self.investment_advice_label, 0, 3)

        layout.addWidget(overview_group)

        # 详细分析结果
        analysis_tabs = QTabWidget()

        # 财务健康度分析
        financial_health_tab = self._create_financial_health_tab()
        analysis_tabs.addTab(financial_health_tab, "财务健康度")

        # 成长性分析
        growth_tab = self._create_growth_analysis_tab()
        analysis_tabs.addTab(growth_tab, "成长性分析")

        # 估值分析
        valuation_tab = self._create_valuation_analysis_tab()
        analysis_tabs.addTab(valuation_tab, "估值分析")

        # 风险分析
        risk_tab = self._create_risk_analysis_tab()
        analysis_tabs.addTab(risk_tab, "风险分析")

        layout.addWidget(analysis_tabs)

        return widget

    def _create_financial_health_tab(self) -> QWidget:
        """创建财务健康度分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 财务健康度指标
        health_group = QGroupBox("财务健康度指标")
        health_layout = QGridLayout(health_group)

        self.health_indicators = {}
        health_items = [
            ("资产负债率", "debt_ratio"),
            ("流动比率", "current_ratio"),
            ("速动比率", "quick_ratio"),
            ("净资产收益率", "roe"),
            ("总资产收益率", "roa"),
            ("毛利率", "gross_margin"),
            ("净利率", "net_margin"),
            ("现金比率", "cash_ratio")
        ]

        for i, (label, key) in enumerate(health_items):
            row, col = i // 2, (i % 2) * 2
            health_layout.addWidget(QLabel(f"{label}:"), row, col)

            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            health_layout.addWidget(value_label, row, col + 1)

            self.health_indicators[key] = value_label

        layout.addWidget(health_group)

        # 健康度评分
        score_group = QGroupBox("健康度评分")
        score_layout = QHBoxLayout(score_group)

        self.health_score_progress = QProgressBar()
        self.health_score_progress.setRange(0, 100)
        self.health_score_progress.setTextVisible(True)
        score_layout.addWidget(self.health_score_progress)

        layout.addWidget(score_group)

        layout.addStretch()

        return widget

    def _create_growth_analysis_tab(self) -> QWidget:
        """创建成长性分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 成长性指标
        growth_group = QGroupBox("成长性指标")
        growth_layout = QGridLayout(growth_group)

        self.growth_indicators = {}
        growth_items = [
            ("营收增长率", "revenue_growth"),
            ("净利润增长率", "profit_growth"),
            ("总资产增长率", "asset_growth"),
            ("净资产增长率", "equity_growth"),
            ("每股收益增长率", "eps_growth"),
            ("每股净资产增长率", "bps_growth")
        ]

        for i, (label, key) in enumerate(growth_items):
            row, col = i // 2, (i % 2) * 2
            growth_layout.addWidget(QLabel(f"{label}:"), row, col)

            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            growth_layout.addWidget(value_label, row, col + 1)

            self.growth_indicators[key] = value_label

        layout.addWidget(growth_group)

        # 成长性评分
        growth_score_group = QGroupBox("成长性评分")
        growth_score_layout = QHBoxLayout(growth_score_group)

        self.growth_score_progress = QProgressBar()
        self.growth_score_progress.setRange(0, 100)
        self.growth_score_progress.setTextVisible(True)
        growth_score_layout.addWidget(self.growth_score_progress)

        layout.addWidget(growth_score_group)

        layout.addStretch()

        return widget

    def _create_valuation_analysis_tab(self) -> QWidget:
        """创建估值分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 估值指标
        valuation_group = QGroupBox("估值指标")
        valuation_layout = QGridLayout(valuation_group)

        self.valuation_indicators = {}
        valuation_items = [
            ("市盈率(PE)", "pe_ratio"),
            ("市净率(PB)", "pb_ratio"),
            ("市销率(PS)", "ps_ratio"),
            ("企业价值倍数(EV/EBITDA)", "ev_ebitda"),
            ("PEG比率", "peg_ratio"),
            ("股息收益率", "dividend_yield")
        ]

        for i, (label, key) in enumerate(valuation_items):
            row, col = i // 2, (i % 2) * 2
            valuation_layout.addWidget(QLabel(f"{label}:"), row, col)

            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            valuation_layout.addWidget(value_label, row, col + 1)

            self.valuation_indicators[key] = value_label

        layout.addWidget(valuation_group)

        # 估值评分
        valuation_score_group = QGroupBox("估值水平")
        valuation_score_layout = QHBoxLayout(valuation_score_group)

        self.valuation_level_label = QLabel("--")
        self.valuation_level_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.valuation_level_label.setAlignment(Qt.AlignCenter)
        valuation_score_layout.addWidget(self.valuation_level_label)

        layout.addWidget(valuation_score_group)

        layout.addStretch()

        return widget

    def _create_risk_analysis_tab(self) -> QWidget:
        """创建风险分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 风险指标
        risk_group = QGroupBox("风险指标")
        risk_layout = QGridLayout(risk_group)

        self.risk_indicators = {}
        risk_items = [
            ("财务风险", "financial_risk"),
            ("经营风险", "operational_risk"),
            ("市场风险", "market_risk"),
            ("流动性风险", "liquidity_risk"),
            ("信用风险", "credit_risk"),
            ("政策风险", "policy_risk")
        ]

        for i, (label, key) in enumerate(risk_items):
            row, col = i // 2, (i % 2) * 2
            risk_layout.addWidget(QLabel(f"{label}:"), row, col)

            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #E74C3C;")
            risk_layout.addWidget(value_label, row, col + 1)

            self.risk_indicators[key] = value_label

        layout.addWidget(risk_group)

        # 风险等级
        risk_level_group = QGroupBox("综合风险等级")
        risk_level_layout = QHBoxLayout(risk_level_group)

        self.risk_level_label = QLabel("--")
        self.risk_level_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.risk_level_label.setAlignment(Qt.AlignCenter)
        risk_level_layout.addWidget(self.risk_level_label)

        layout.addWidget(risk_level_group)

        layout.addStretch()

        return widget

    def _apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QTableWidget {
                gridline-color: #E0E0E0;
                background-color: white;
                alternate-background-color: #F5F5F5;
            }
            
            QTableWidget::item {
                padding: 5px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #3498DB;
                color: white;
            }
            
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
            }
            
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #2980B9;
            }
            
            QPushButton:pressed {
                background-color: #21618C;
            }
            
            QComboBox, QSpinBox, QDateEdit {
                padding: 5px;
                border: 1px solid #BDC3C7;
                border-radius: 3px;
                min-width: 100px;
            }
            
            QProgressBar {
                border: 2px solid #BDC3C7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: #27AE60;
                border-radius: 3px;
            }
        """)

    def _on_symbol_changed(self, symbol: str):
        """股票代码变更处理"""
        if symbol and symbol != self.current_symbol:
            self.current_symbol = symbol
            self._clear_all_data()
            logger.info(f"基本面分析股票代码已切换到: {symbol}")

    def _on_report_type_changed(self, report_type: str):
        """报表类型变更处理"""
        self._update_financial_table()
        logger.debug(f"财务报表类型已切换到: {report_type}")

    def _refresh_all_data(self):
        """刷新所有数据"""
        if not self.current_symbol:
            self.error_occurred.emit("请先选择股票代码")
            return

        try:
            # 异步获取各类数据
            asyncio.create_task(self._fetch_financial_data())
            asyncio.create_task(self._fetch_announcement_data())
            asyncio.create_task(self._fetch_rating_data())

            logger.info(f"开始刷新 {self.current_symbol} 的基本面数据")

        except Exception as e:
            self.error_occurred.emit(f"刷新数据失败: {str(e)}")
            logger.error(f"刷新基本面数据失败: {e}")

    async def _fetch_financial_data(self):
        """获取财务数据"""
        if not self.fundamental_manager:
            return

        try:
            periods = self.periods_spin.value()

            # 获取利润表数据
            income_data = await self.fundamental_manager.get_financial_statements(
                symbol=self.current_symbol,
                report_type="income_statement",
                periods=periods,
                asset_type=AssetType.STOCK
            )

            if income_data is not None:
                self.financial_data_cache['income_statement'] = income_data
                self._update_financial_table()
                self._update_financial_chart()

                logger.info(f"获取 {self.current_symbol} 财务数据成功")

        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")

    async def _fetch_announcement_data(self):
        """获取公告数据"""
        if not self.fundamental_manager:
            return

        try:
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()

            announcements = await self.fundamental_manager.get_company_announcements(
                symbol=self.current_symbol,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time())
            )

            if announcements:
                self.announcement_cache[self.current_symbol] = announcements
                self._update_announcement_table()

                logger.info(f"获取 {self.current_symbol} 公告数据成功，共 {len(announcements)} 条")

        except Exception as e:
            logger.error(f"获取公告数据失败: {e}")

    async def _fetch_rating_data(self):
        """获取评级数据"""
        if not self.fundamental_manager:
            return

        try:
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()

            ratings = await self.fundamental_manager.get_analyst_ratings(
                symbol=self.current_symbol,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time())
            )

            if ratings is not None:
                self.rating_cache[self.current_symbol] = ratings
                self._update_rating_table()
                self._update_rating_stats()

                logger.info(f"获取 {self.current_symbol} 评级数据成功")

        except Exception as e:
            logger.error(f"获取评级数据失败: {e}")

    def _update_financial_table(self):
        """更新财务报表表格"""
        report_type = self.report_type_combo.currentText()

        if 'income_statement' not in self.financial_data_cache:
            return

        # 模拟财务数据表格更新
        data = self.financial_data_cache['income_statement']

        # 设置表格结构（根据报表类型）
        if report_type == "利润表":
            columns = ["报告期", "营业收入", "营业成本", "毛利润", "净利润", "每股收益"]
        elif report_type == "资产负债表":
            columns = ["报告期", "总资产", "总负债", "净资产", "资产负债率", "流动比率"]
        elif report_type == "现金流量表":
            columns = ["报告期", "经营现金流", "投资现金流", "筹资现金流", "现金净增加", "期末现金"]
        else:  # 财务指标
            columns = ["报告期", "ROE", "ROA", "毛利率", "净利率", "PE", "PB"]

        self.financial_table.setColumnCount(len(columns))
        self.financial_table.setHorizontalHeaderLabels(columns)

        # 模拟数据填充
        self.financial_table.setRowCount(8)  # 8个报告期

        for row in range(8):
            for col, column in enumerate(columns):
                if col == 0:  # 报告期
                    item = QTableWidgetItem(f"2024Q{4-row//2}")
                else:
                    # 模拟数据
                    value = f"{(100 + row * 10) * (col + 1):,.2f}"
                    item = QTableWidgetItem(value)

                    # 设置数字右对齐
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.financial_table.setItem(row, col, item)

        # 调整列宽
        self.financial_table.resizeColumnsToContents()

    def _update_financial_chart(self):
        """更新财务图表"""
        if 'income_statement' not in self.financial_data_cache:
            return

        # 模拟财务数据
        financial_data = []
        for i in range(8):
            financial_data.append({
                'period': f"2024Q{4-i//2}",
                'revenue': 1000000 + i * 50000,
                'net_profit': 100000 + i * 8000,
                'total_assets': 5000000 + i * 200000,
                'total_liabilities': 2000000 + i * 80000,
                'operating_cash_flow': 80000 + i * 6000
            })

        self.financial_chart.update_financial_data(financial_data)

    def _update_announcement_table(self):
        """更新公告表格"""
        if self.current_symbol not in self.announcement_cache:
            return

        announcements = self.announcement_cache[self.current_symbol]

        self.announcement_table.setRowCount(len(announcements))

        for row, announcement in enumerate(announcements):
            # 日期
            date_str = announcement.get('date', '')[:10]  # 只显示日期部分
            self.announcement_table.setItem(row, 0, QTableWidgetItem(date_str))

            # 标题
            title = announcement.get('title', '')[:50] + "..." if len(announcement.get('title', '')) > 50 else announcement.get('title', '')
            self.announcement_table.setItem(row, 1, QTableWidgetItem(title))

            # 类型
            category = announcement.get('parsed_category', '其他')
            self.announcement_table.setItem(row, 2, QTableWidgetItem(category))

            # 重要性
            importance = announcement.get('importance_rating', 5)
            importance_text = "重大" if importance >= 8 else "重要" if importance >= 6 else "一般"
            importance_item = QTableWidgetItem(importance_text)

            # 根据重要性设置颜色
            if importance >= 8:
                importance_item.setForeground(QColor("#E74C3C"))
            elif importance >= 6:
                importance_item.setForeground(QColor("#F39C12"))
            else:
                importance_item.setForeground(QColor("#27AE60"))

            self.announcement_table.setItem(row, 3, importance_item)

            # 影响（模拟）
            impact = "正面" if importance >= 7 else "中性" if importance >= 5 else "负面"
            self.announcement_table.setItem(row, 4, QTableWidgetItem(impact))

        # 调整列宽
        self.announcement_table.resizeColumnsToContents()

    def _filter_announcements(self):
        """过滤公告"""
        # 实现公告过滤逻辑
        logger.debug("公告过滤功能待实现")

    def _on_announcement_selected(self):
        """公告选择处理"""
        current_row = self.announcement_table.currentRow()

        if current_row >= 0 and self.current_symbol in self.announcement_cache:
            announcements = self.announcement_cache[self.current_symbol]

            if current_row < len(announcements):
                announcement = announcements[current_row]

                # 更新公告详情
                self.announcement_title.setText(announcement.get('title', ''))

                # 更新关键信息
                extracted_info = announcement.get('extracted_info', {})
                self.key_info_labels['date'].setText(announcement.get('date', '')[:10])
                self.key_info_labels['category'].setText(announcement.get('parsed_category', ''))
                self.key_info_labels['importance'].setText(str(announcement.get('importance_rating', 0)))
                self.key_info_labels['amount'].setText(extracted_info.get('amount', '--'))
                self.key_info_labels['impact'].setText("待分析")

                # 更新公告内容
                content = announcement.get('content', '')[:1000] + "..." if len(announcement.get('content', '')) > 1000 else announcement.get('content', '')
                self.announcement_content.setText(content)

    def _perform_announcement_analysis(self):
        """执行公告智能分析"""
        logger.info("执行公告智能分析")
        # 实现智能分析逻辑

    def _update_rating_table(self):
        """更新评级表格"""
        if self.current_symbol not in self.rating_cache:
            return

        # 模拟评级数据
        ratings_data = [
            {"date": "2024-01-15", "institution": "中信证券", "analyst": "张三", "rating": "买入", "target_price": 25.50, "reason": "业绩超预期"},
            {"date": "2024-01-10", "institution": "国泰君安", "analyst": "李四", "rating": "持有", "target_price": 23.00, "reason": "估值合理"},
            {"date": "2024-01-05", "institution": "华泰证券", "analyst": "王五", "rating": "买入", "target_price": 26.00, "reason": "行业景气度提升"}
        ]

        self.rating_table.setRowCount(len(ratings_data))

        for row, rating in enumerate(ratings_data):
            self.rating_table.setItem(row, 0, QTableWidgetItem(rating['date']))
            self.rating_table.setItem(row, 1, QTableWidgetItem(rating['institution']))
            self.rating_table.setItem(row, 2, QTableWidgetItem(rating['analyst']))

            # 评级（带颜色）
            rating_item = QTableWidgetItem(rating['rating'])
            if rating['rating'] == "买入":
                rating_item.setForeground(QColor("#E74C3C"))
            elif rating['rating'] == "持有":
                rating_item.setForeground(QColor("#F39C12"))
            else:
                rating_item.setForeground(QColor("#27AE60"))

            self.rating_table.setItem(row, 3, rating_item)

            # 目标价
            target_price_item = QTableWidgetItem(f"{rating['target_price']:.2f}")
            target_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.rating_table.setItem(row, 4, target_price_item)

            # 理由
            self.rating_table.setItem(row, 5, QTableWidgetItem(rating['reason']))

        # 调整列宽
        self.rating_table.resizeColumnsToContents()

    def _update_rating_stats(self):
        """更新评级统计"""
        # 模拟评级统计
        self.rating_stats_labels['buy_count'].setText("5")
        self.rating_stats_labels['hold_count'].setText("3")
        self.rating_stats_labels['sell_count'].setText("1")
        self.rating_stats_labels['avg_target_price'].setText("24.50")
        self.rating_stats_labels['max_target_price'].setText("26.00")
        self.rating_stats_labels['min_target_price'].setText("22.00")

    def _perform_comprehensive_analysis(self):
        """执行综合分析"""
        if not self.current_symbol:
            self.error_occurred.emit("请先选择股票代码")
            return

        try:
            # 执行综合分析
            analysis_result = self._calculate_comprehensive_analysis()

            # 更新分析结果显示
            self._update_analysis_results(analysis_result)

            # 发射分析完成信号
            self.analysis_completed.emit(analysis_result)

            logger.info(f"完成 {self.current_symbol} 的综合基本面分析")

        except Exception as e:
            self.error_occurred.emit(f"综合分析失败: {str(e)}")
            logger.error(f"综合分析失败: {e}")

    def _calculate_comprehensive_analysis(self) -> Dict[str, Any]:
        """计算综合分析结果"""
        # 模拟综合分析计算
        analysis_result = {
            'symbol': self.current_symbol,
            'timestamp': datetime.now(),
            'overall_score': 75,  # 综合评分
            'investment_advice': '买入',
            'financial_health': {
                'score': 80,
                'debt_ratio': 45.2,
                'current_ratio': 1.8,
                'quick_ratio': 1.2,
                'roe': 15.6,
                'roa': 8.9,
                'gross_margin': 32.5,
                'net_margin': 12.8,
                'cash_ratio': 0.8
            },
            'growth_analysis': {
                'score': 85,
                'revenue_growth': 18.5,
                'profit_growth': 22.3,
                'asset_growth': 12.1,
                'equity_growth': 16.8,
                'eps_growth': 20.5,
                'bps_growth': 15.2
            },
            'valuation_analysis': {
                'level': '合理偏低',
                'pe_ratio': 18.5,
                'pb_ratio': 2.1,
                'ps_ratio': 3.2,
                'ev_ebitda': 12.8,
                'peg_ratio': 0.9,
                'dividend_yield': 2.8
            },
            'risk_analysis': {
                'level': '中等',
                'financial_risk': '低',
                'operational_risk': '中',
                'market_risk': '中',
                'liquidity_risk': '低',
                'credit_risk': '低',
                'policy_risk': '中'
            }
        }

        return analysis_result

    def _update_analysis_results(self, analysis_result: Dict[str, Any]):
        """更新分析结果显示"""
        # 更新综合评分
        overall_score = analysis_result.get('overall_score', 0)
        self.overall_score_label.setText(f"{overall_score}")

        # 根据评分设置颜色
        if overall_score >= 80:
            self.overall_score_label.setStyleSheet("color: #27AE60; border: 2px solid #27AE60; border-radius: 10px; padding: 10px;")
        elif overall_score >= 60:
            self.overall_score_label.setStyleSheet("color: #F39C12; border: 2px solid #F39C12; border-radius: 10px; padding: 10px;")
        else:
            self.overall_score_label.setStyleSheet("color: #E74C3C; border: 2px solid #E74C3C; border-radius: 10px; padding: 10px;")

        # 更新投资建议
        investment_advice = analysis_result.get('investment_advice', '--')
        self.investment_advice_label.setText(investment_advice)

        if investment_advice == '买入':
            self.investment_advice_label.setStyleSheet("color: #E74C3C; font-weight: bold;")
        elif investment_advice == '持有':
            self.investment_advice_label.setStyleSheet("color: #F39C12; font-weight: bold;")
        else:
            self.investment_advice_label.setStyleSheet("color: #27AE60; font-weight: bold;")

        # 更新财务健康度
        financial_health = analysis_result.get('financial_health', {})
        for key, value in financial_health.items():
            if key == 'score':
                self.health_score_progress.setValue(value)
            elif key in self.health_indicators:
                if isinstance(value, (int, float)):
                    self.health_indicators[key].setText(f"{value:.2f}")
                else:
                    self.health_indicators[key].setText(str(value))

        # 更新成长性分析
        growth_analysis = analysis_result.get('growth_analysis', {})
        for key, value in growth_analysis.items():
            if key == 'score':
                self.growth_score_progress.setValue(value)
            elif key in self.growth_indicators:
                if isinstance(value, (int, float)):
                    self.growth_indicators[key].setText(f"{value:.2f}%")
                else:
                    self.growth_indicators[key].setText(str(value))

        # 更新估值分析
        valuation_analysis = analysis_result.get('valuation_analysis', {})
        for key, value in valuation_analysis.items():
            if key == 'level':
                self.valuation_level_label.setText(str(value))
            elif key in self.valuation_indicators:
                if isinstance(value, (int, float)):
                    self.valuation_indicators[key].setText(f"{value:.2f}")
                else:
                    self.valuation_indicators[key].setText(str(value))

        # 更新风险分析
        risk_analysis = analysis_result.get('risk_analysis', {})
        for key, value in risk_analysis.items():
            if key == 'level':
                self.risk_level_label.setText(str(value))
                # 根据风险等级设置颜色
                if value == '低':
                    self.risk_level_label.setStyleSheet("color: #27AE60; font-weight: bold;")
                elif value == '中等':
                    self.risk_level_label.setStyleSheet("color: #F39C12; font-weight: bold;")
                else:
                    self.risk_level_label.setStyleSheet("color: #E74C3C; font-weight: bold;")
            elif key in self.risk_indicators:
                self.risk_indicators[key].setText(str(value))

    def _export_financial_data(self):
        """导出财务数据"""
        logger.info("财务数据导出功能待实现")

    def _clear_all_data(self):
        """清空所有数据"""
        # 清空数据缓存
        self.financial_data_cache.clear()
        self.announcement_cache.clear()
        self.rating_cache.clear()
        self.analysis_results.clear()

        # 清空表格
        self.financial_table.setRowCount(0)
        self.announcement_table.setRowCount(0)
        self.rating_table.setRowCount(0)

        # 重置分析结果
        self.overall_score_label.setText("--")
        self.investment_advice_label.setText("--")

        # 重置各项指标
        for label in self.health_indicators.values():
            label.setText("--")
        for label in self.growth_indicators.values():
            label.setText("--")
        for label in self.valuation_indicators.values():
            label.setText("--")
        for label in self.risk_indicators.values():
            label.setText("--")
        for label in self.rating_stats_labels.values():
            label.setText("--")
        for label in self.key_info_labels.values():
            label.setText("--")

        # 重置进度条
        self.health_score_progress.setValue(0)
        self.growth_score_progress.setValue(0)

        # 清空公告详情
        self.announcement_title.setText("选择公告查看详情")
        self.announcement_content.clear()

    def set_symbol(self, symbol: str):
        """设置当前股票代码"""
        self.symbol_combo.setCurrentText(symbol)

    def get_current_symbol(self) -> str:
        """获取当前股票代码"""
        return self.current_symbol

    def get_analysis_results(self) -> Dict[str, Any]:
        """获取分析结果"""
        return self.analysis_results.copy()
