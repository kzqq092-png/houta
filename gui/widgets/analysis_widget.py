"""
分析控件模块
"""
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
from datetime import *
import pandas as pd
from PyQt5.QtGui import QColor, QKeySequence

import akshare as ak
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import importlib
import traceback
import os
import time
from concurrent.futures import *
import numba
import json
from core.logger import LogManager, LogLevel
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from hikyuu.indicator import *
from hikyuu import sm
from hikyuu import Query
from indicators_algo import get_talib_indicator_list, get_talib_category, calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci, get_all_indicators_by_category, calc_talib_indicator
from utils.cache import Cache
import requests
from bs4 import BeautifulSoup
from analysis.pattern_recognition import PatternRecognizer
from core.data_manager import data_manager
from features.advanced_indicators import create_pattern_recognition_features, ALL_PATTERN_TYPES
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from data.data_loader import generate_quality_report
from core.risk_exporter import RiskExporter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget

# 新增导入形态管理器
from analysis.pattern_manager import PatternManager


class AnalysisWidget(QWidget):
    """分析控件类"""

    # 定义信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)  # 新增错误信号
    pattern_selected = pyqtSignal(int)  # 新增信号，用于传递信号索引

    data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化分析控件

        Args:
            config_manager: Optional ConfigManager instance to use
        """

        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.log_manager = LogManager()

        # 初始化形态管理器
        try:
            if PatternManager is not None:
                self.pattern_manager = PatternManager()
            else:
                self.pattern_manager = None
                self.log_manager.warning("PatternManager未能成功导入，形态识别功能将受限")
        except Exception as e:
            self.pattern_manager = None
            self.log_manager.error(f"初始化PatternManager失败: {e}")

        self.current_kdata = None
        self.analysis_futures = []  # 存储分析任务的future对象
        self.loading_overlay = None
        self.progress_bar = None
        self.cancel_button = None
        self.data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)
        self.is_loading = False  # 初始化加载状态

        # 缓存各种信号数据
        self._all_pattern_signals = []
        self._rotation_worker = None  # 板块轮动工作线程

        # 初始化UI
        self.init_ui()
        # 设置快捷键
        self.setup_shortcuts()

        # 初始化形态过滤器选项（在所有UI创建完成后）
        QTimer.singleShot(100, self._init_pattern_filters)

    def _init_pattern_filters(self):
        """延迟初始化形态过滤器选项"""
        try:
            if self.pattern_manager is not None:
                self._update_pattern_filter_options()
        except Exception as e:
            self.log_manager.warning(f"初始化形态过滤器选项失败: {e}")

    def show_loading(self, message="正在分析..."):
        """显示加载状态"""
        if self.is_loading:
            return

        self.is_loading = True

        # 创建加载遮罩层
        if not self.loading_overlay:
            self.loading_overlay = QWidget(self)
            self.loading_overlay.setStyleSheet("""
                QWidget {
                    background-color: rgba(0, 0, 0, 0.7);
                    border-radius: 8px;
                }
            """)

            overlay_layout = QVBoxLayout(self.loading_overlay)
            overlay_layout.setAlignment(Qt.AlignCenter)

            # 加载图标（使用文字代替）
            loading_icon = QLabel("⏳")
            loading_icon.setStyleSheet("QLabel { color: white; font-size: 48px; }")
            loading_icon.setAlignment(Qt.AlignCenter)
            overlay_layout.addWidget(loading_icon)

            # 加载文字
            self.loading_label = QLabel(message)
            self.loading_label.setStyleSheet("QLabel { color: white; font-size: 16px; font-weight: bold; }")
            self.loading_label.setAlignment(Qt.AlignCenter)
            overlay_layout.addWidget(self.loading_label)

        # 更新消息
        if self.loading_label:
            self.loading_label.setText(message)

        # 显示遮罩层
        self.loading_overlay.resize(self.size())
        self.loading_overlay.show()
        self.loading_overlay.raise_()

        # 强制刷新界面
        QApplication.processEvents()

    def hide_loading(self):
        """隐藏加载状态"""
        if not self.is_loading:
            return

        self.is_loading = False

        if self.loading_overlay:
            self.loading_overlay.hide()

        # 强制刷新界面
        QApplication.processEvents()

    def update_loading_progress(self, value, message=None):
        """更新加载进度"""
        if not self.is_loading or not self.progress_bar:
            return

        if self.progress_bar.maximum() == 0:
            # 切换到确定进度模式
            self.progress_bar.setRange(0, 100)

        self.progress_bar.setValue(value)

        if message and self.loading_label:
            self.loading_label.setText(message)

        QApplication.processEvents()

    def resizeEvent(self, event):
        """窗口大小改变时调整加载遮罩层大小"""
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.resize(self.size())

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建Tab控件
        self.tab_widget = QTabWidget()

        # 创建并存储各个分析标签页
        self.technical_tab = self.create_technical_tab()
        self.pattern_tab = self.create_pattern_tab()
        self.trend_tab = self.create_trend_tab()
        self.wave_tab = self.create_wave_tab()
        self.sentiment_tab = self.create_sentiment_tab()
        self.sector_flow_tab = self.create_sector_flow_tab()
        self.hotspot_tab = self.create_hotspot_tab()
        self.sentiment_report_tab = self.create_sentiment_report_tab()

        # 添加各个分析标签页
        self.tab_widget.addTab(self.technical_tab, "技术分析")
        self.tab_widget.addTab(self.pattern_tab, "形态识别")
        self.tab_widget.addTab(self.trend_tab, "趋势分析")
        self.tab_widget.addTab(self.wave_tab, "波浪分析")
        self.tab_widget.addTab(self.sentiment_tab, "市场情绪")
        self.tab_widget.addTab(self.sector_flow_tab, "板块资金流向")
        self.tab_widget.addTab(self.hotspot_tab, "热点分析")
        self.tab_widget.addTab(self.sentiment_report_tab, "情绪报告")

        # 连接Tab切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tab_widget)

        # 设置快捷键
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """设置快捷键"""
        # 形态识别相关快捷键
        identify_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        identify_shortcut.activated.connect(self.identify_patterns)

        filter_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        filter_shortcut.activated.connect(self.apply_pattern_filter)

        # 技术分析相关快捷键
        calc_indicators_shortcut = QShortcut(QKeySequence("Ctrl+Enter"), self)
        calc_indicators_shortcut.activated.connect(self.calculate_indicators)

        clear_indicators_shortcut = QShortcut(QKeySequence("Ctrl+Delete"), self)
        clear_indicators_shortcut.activated.connect(self.clear_indicators)

        # 趋势分析相关快捷键
        analyze_trend_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        analyze_trend_shortcut.activated.connect(self.analyze_trend)

        # 波浪分析相关快捷键
        analyze_wave_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        analyze_wave_shortcut.activated.connect(self.analyze_wave)

        # 市场情绪分析相关快捷键
        analyze_sentiment_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        analyze_sentiment_shortcut.activated.connect(self.analyze_sentiment)

        # 板块资金流向分析相关快捷键
        analyze_flow_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        analyze_flow_shortcut.activated.connect(self.analyze_sector_flow)

        # 通用快捷键
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self.refresh_current_tab)

        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self.show_help)

        # Tab切换快捷键
        for i in range(8):  # 8个Tab
            tab_shortcut = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            tab_shortcut.activated.connect(lambda checked, index=i: self.tab_widget.setCurrentIndex(index))

    def _connect_chart_widget_signals(self):
        """连接图表控件信号"""
        # 连接pattern_selected信号到图表更新
        self.pattern_selected.connect(self.on_pattern_selected)

        # 连接indicator_changed信号
        self.indicator_changed.connect(self.on_indicator_changed)

        # 连接analysis_completed信号
        self.analysis_completed.connect(lambda result: self.log_manager.info(f"分析完成: {result}"))

        # 连接error_occurred信号
        self.error_occurred.connect(lambda error: self.log_manager.error(f"分析错误: {error}"))

    def apply_pattern_filter(self):
        """应用形态筛选条件"""
        if self.tab_widget.currentIndex() == 1:  # 形态识别Tab
            # 触发筛选逻辑
            all_signals = getattr(self, '_all_pattern_signals', [])
            if hasattr(self, 'pattern_type_filter'):
                # 执行筛选逻辑（这里简化处理）
                self._show_pattern_table(all_signals)

    def refresh_current_tab(self):
        """刷新当前标签页数据"""
        try:
            current_index = self.tab_widget.currentIndex()
            tab_names = ["技术分析", "形态识别", "趋势分析", "波浪分析", "市场情绪", "板块资金流向", "热点分析", "情绪报告"]

            if current_index < len(tab_names):
                self.log_manager.info(f"正在刷新{tab_names[current_index]}数据...")

                # 根据当前标签页执行相应的刷新操作
                if current_index == 0:  # 技术分析
                    self.refresh_technical_data()
                elif current_index == 1:  # 形态识别
                    self.refresh_pattern_data()
                elif current_index == 2:  # 趋势分析
                    self.refresh_trend_data()
                elif current_index == 3:  # 波浪分析
                    self.refresh_wave_data()
                elif current_index == 4:  # 市场情绪
                    self.refresh_sentiment_data()

                self.log_manager.info(f"{tab_names[current_index]}数据刷新完成")
        except Exception as e:
            self.log_manager.error(f"刷新当前标签页失败: {str(e)}")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
        <h3>分析工具快捷键帮助</h3>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr><th>功能</th><th>快捷键</th><th>说明</th></tr>
        <tr><td>识别形态</td><td>Ctrl+R</td><td>开始K线形态识别</td></tr>
        <tr><td>筛选结果</td><td>Ctrl+F</td><td>应用筛选条件</td></tr>
        <tr><td>计算指标</td><td>Ctrl+Enter</td><td>计算技术指标</td></tr>
        <tr><td>清除指标</td><td>Ctrl+Delete</td><td>清除所有指标</td></tr>
        <tr><td>趋势分析</td><td>Ctrl+T</td><td>开始趋势分析</td></tr>
        <tr><td>波浪分析</td><td>Ctrl+W</td><td>开始波浪分析</td></tr>
        <tr><td>情绪分析</td><td>Ctrl+S</td><td>开始情绪分析</td></tr>
        <tr><td>资金流向</td><td>Ctrl+M</td><td>分析资金流向</td></tr>
        <tr><td>刷新数据</td><td>F5</td><td>刷新当前Tab数据</td></tr>
        <tr><td>显示帮助</td><td>F1</td><td>显示此帮助信息</td></tr>
        <tr><td>切换Tab</td><td>Ctrl+1~8</td><td>快速切换到指定Tab</td></tr>
        </table>
        <p><b>提示：</b>将鼠标悬停在按钮上可查看详细说明</p>
        """

        QMessageBox.information(self, "快捷键帮助", help_text)

    def on_tab_changed(self, index):
        """Tab切换时只刷新当前Tab内容，且异步运行分析，主界面不卡顿"""
        tab_text = self.tab_widget.tabText(index)
        if tab_text == "技术分析":
            btn = self.technical_tab.findChild(QPushButton, "刷新分析")
            if btn:
                self.run_button_analysis_async(btn, self.calculate_indicators)
        elif tab_text == "形态识别":
            btn = self.pattern_tab.findChild(QPushButton, "识别形态")
            if btn:
                self.run_button_analysis_async(btn, self.identify_patterns)
        elif tab_text == "趋势分析":
            btn = self.trend_tab.findChild(QPushButton, "分析趋势")
            if btn:
                self.run_button_analysis_async(btn, self.analyze_trend)
        elif tab_text == "波浪分析":
            btn = self.wave_tab.findChild(QPushButton, "分析波浪")
            if btn:
                self.run_button_analysis_async(btn, self.analyze_wave)
        elif tab_text == "市场情绪":
            btn = self.sentiment_tab.findChild(QPushButton, "分析情绪")
            if btn:
                self.run_button_analysis_async(btn, self.analyze_sentiment)
        elif tab_text == "板块资金流向":
            btn = self.sector_flow_tab.findChild(QPushButton, "分析板块")
            if btn:
                self.run_button_analysis_async(btn, self.analyze_sector_flow)
        elif tab_text == "热点分析":
            btn = self.hotspot_tab.findChild(QPushButton, "分析轮动")
            if btn:
                self.run_button_analysis_async(btn, self.analyze_hotspot)

    def refresh(self) -> None:
        """
        只刷新当前Tab内容，避免全量分析导致卡顿。
        """
        index = self.tab_widget.currentIndex()
        self.on_tab_changed(index)

    def run_button_analysis_async(self, button, analysis_func, *args, **kwargs):
        """
        通用按钮防抖+异步分析工具，点击后按钮文本变为"取消"，再次点击时中断分析，结束后恢复原文本。
        修复：保证分析结束后按钮状态恢复，异常时也能恢复，防止按钮卡死。
        优化：线程池全局唯一，防止多线程泄漏。
        """
        from concurrent.futures import ThreadPoolExecutor
        from PyQt5.QtCore import QTimer
        if not hasattr(self, '_thread_pool'):
            self._thread_pool = ThreadPoolExecutor(max_workers=2)
        # 只有按钮处于初始分析状态时才记录原始文本，防止多次点击时被覆盖
        if not hasattr(button, '_original_text') or button._original_text is None or button.text() not in ["取消", "处理中", "中断", "取消分析"]:
            button._original_text = button.text()
        original_text = button._original_text
        button.setText("取消")
        button._interrupted = False

        def on_cancel():
            button._interrupted = True
            button.setText(original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self.run_button_analysis_async(button, analysis_func, *args, **kwargs))

        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(on_cancel)

        def task():
            try:
                if not getattr(button, '_interrupted', False):
                    analysis_func(*args, **kwargs)
            except Exception as e:
                msg = f"分析异常: {str(e)}"
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(msg)
                self.error_occurred.emit(msg)
            finally:
                # 保证无论如何都恢复按钮
                QTimer.singleShot(0, lambda: on_done(None))

        def on_done(future):
            # 自动恢复为原始文本
            button.setText(button._original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self.run_button_analysis_async(button, analysis_func, *args, **kwargs))
        future = self._thread_pool.submit(task)
        # 只需在finally中恢复，无需重复回调

    def create_technical_tab(self) -> QWidget:
        """创建技术分析Tab，采用卡片式布局，分区展示指标选择、参数设置、结果展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 指标选择和控制区域
        control_group = QGroupBox("指标控制")
        control_layout = QHBoxLayout(control_group)

        # 左侧：指标选择
        indicator_card = QFrame()
        indicator_card.setFrameStyle(QFrame.StyledPanel)
        indicator_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        indicator_layout = QVBoxLayout(indicator_card)
        indicator_layout.addWidget(QLabel("技术指标"))

        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(['移动平均线(MA)', 'MACD', 'KDJ', 'RSI', '布林带(BOLL)', 'ATR', 'OBV', 'CCI'])
        self.indicator_combo.currentTextChanged.connect(self.on_indicator_changed)
        self.indicator_combo.setToolTip(
            "选择要计算的技术指标\n• MA：移动平均线，趋势跟踪指标\n• MACD：指数平滑移动平均线，动量指标\n• KDJ：随机指标，超买超卖指标\n• RSI：相对强弱指数，动量震荡指标\n• BOLL：布林带，波动性指标\n• ATR：平均真实波幅，波动性指标\n• OBV：能量潮，成交量指标\n• CCI：商品通道指数，动量指标")
        indicator_layout.addWidget(self.indicator_combo)

        # 计算按钮
        calc_btn = QPushButton("计算指标")
        calc_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; }")
        calc_btn.clicked.connect(self.calculate_indicators)
        calc_btn.setToolTip("根据当前设置计算选定的技术指标\n快捷键：Ctrl+Enter")

        clear_indicators_btn = QPushButton("清除指标")
        clear_indicators_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; }")
        clear_indicators_btn.clicked.connect(self.clear_indicators)
        clear_indicators_btn.setToolTip("清除所有已计算的技术指标\n快捷键：Ctrl+Delete")

        indicator_layout.addWidget(calc_btn)
        indicator_layout.addWidget(clear_indicators_btn)
        control_layout.addWidget(indicator_card, stretch=2)

        # 右侧：参数设置
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        params_layout = QVBoxLayout(params_card)
        params_layout.addWidget(QLabel("参数设置"))

        # MA参数
        ma_layout = QHBoxLayout()
        ma_layout.addWidget(QLabel("MA周期:"))
        self.ma_period_spin = QSpinBox()
        self.ma_period_spin.setRange(1, 250)
        self.ma_period_spin.setValue(20)
        self.ma_period_spin.setToolTip("移动平均线的计算周期\n• 短期：5-10日\n• 中期：20-30日\n• 长期：60-250日\n常用：5、10、20、60日")
        ma_layout.addWidget(self.ma_period_spin)
        params_layout.addLayout(ma_layout)

        # MACD参数
        macd_layout = QHBoxLayout()
        macd_layout.addWidget(QLabel("MACD参数:"))
        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setRange(1, 50)
        self.macd_fast_spin.setValue(12)
        self.macd_fast_spin.setToolTip("MACD快线周期\n默认：12日\n范围：1-50日")

        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setRange(1, 100)
        self.macd_slow_spin.setValue(26)
        self.macd_slow_spin.setToolTip("MACD慢线周期\n默认：26日\n范围：1-100日")

        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setRange(1, 50)
        self.macd_signal_spin.setValue(9)
        self.macd_signal_spin.setToolTip("MACD信号线周期\n默认：9日\n范围：1-50日")

        macd_layout.addWidget(self.macd_fast_spin)
        macd_layout.addWidget(self.macd_slow_spin)
        macd_layout.addWidget(self.macd_signal_spin)
        params_layout.addLayout(macd_layout)

        control_layout.addWidget(params_card, stretch=2)
        layout.addWidget(control_group)

        # 结果展示区域
        results_group = QGroupBox("计算结果")
        results_layout = QVBoxLayout(results_group)

        # 结果表格
        self.technical_table = QTableWidget(0, 6)
        self.technical_table.setHorizontalHeaderLabels(['日期', '指标', '数值', '信号', '强度', '备注'])
        self.technical_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.technical_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 表格样式美化
        self.technical_table.setAlternatingRowColors(True)
        self.technical_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.technical_table.setSortingEnabled(True)

        results_layout.addWidget(self.technical_table)

        # 导出按钮
        export_layout = QHBoxLayout()
        export_format_combo = QComboBox()
        export_format_combo.addItems(["Excel", "CSV", "JSON"])
        export_tech_btn = QPushButton("导出技术分析结果")
        export_tech_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")

        export_layout.addWidget(QLabel("导出格式:"))
        export_layout.addWidget(export_format_combo)
        export_layout.addWidget(export_tech_btn)
        export_layout.addStretch()

        results_layout.addLayout(export_layout)
        layout.addWidget(results_group)

        return tab

    def refresh_technical_data(self):
        """强制刷新技术分析Tab缓存和数据，异步执行分析"""
        self.current_kdata = None
        # 清理其他相关缓存（如有）
        self.calculate_indicators()

    def calculate_indicators(self):
        """技术指标分析，自动补全K线数据，支持主图/主窗口数据同步"""
        try:
            kdata = self.current_kdata
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                pass
            kdata = self._kdata_preprocess(kdata, context="技术分析")
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                self.log_manager.warning("无K线数据，无法进行技术分析")
                QMessageBox.warning(self, "提示", "无K线数据，无法进行技术分析")
                return
            start_time = time.time()
            self.log_manager.info("[AnalysisWidget.calculate_indicators] 开始")
            try:
                self.technical_table.setRowCount(0)
                # 修复DataFrame布尔判断错误
                if self.current_kdata is None or (hasattr(self.current_kdata, 'empty') and self.current_kdata.empty):
                    self.technical_table.setRowCount(1)
                    for col in range(self.technical_table.columnCount()):
                        self.technical_table.setItem(
                            0, col, QTableWidgetItem("无数据"))
                    return
                from indicators_algo import get_talib_indicator_list, get_all_indicators_by_category
                talib_list = get_talib_indicator_list()
                category_map = get_all_indicators_by_category()
                if not talib_list or not category_map:
                    self.technical_table.setRowCount(1)
                    for col in range(self.technical_table.columnCount()):
                        self.technical_table.setItem(
                            0, col, QTableWidgetItem("无数据"))
                    self.log_manager.log(
                        "未检测到任何ta-lib指标，请检查ta-lib安装或数据源！", LogLevel.ERROR)
                    return
                main_window = self.parentWidget()
                while main_window and not hasattr(main_window, 'get_current_indicators'):
                    main_window = main_window.parentWidget()
                if not main_window or not hasattr(main_window, 'get_current_indicators'):
                    self.technical_table.setRowCount(1)
                    for col in range(self.technical_table.columnCount()):
                        self.technical_table.setItem(
                            0, col, QTableWidgetItem("无数据"))
                    self.log_manager.log("未找到主窗口统一指标接口", LogLevel.ERROR)
                    return
                indicators = main_window.get_current_indicators()
                if not indicators:
                    self.technical_table.setRowCount(1)
                    for col in range(self.technical_table.columnCount()):
                        self.technical_table.setItem(
                            0, col, QTableWidgetItem("无数据"))
                    return
                row_idx = 0
                for ind in indicators:
                    name = ind.get('name')
                    params = ind.get('params', {})
                    ind_type = ind.get('type', '')
                    value, status, suggestion = "-", "-", "观望"
                    try:
                        if name.startswith('MA'):
                            ma = self.calculate_ma(params)
                            if ma is not None and len(ma) > 0:
                                value = f"{ma[-1]:.2f}"
                                close = self.current_kdata['close']
                                if close[-1] > ma[-1]:
                                    status = "金叉"
                                    suggestion = "买入"
                                else:
                                    status = "死叉"
                                    suggestion = "卖出"
                        elif name == 'MACD':
                            macd = self.calculate_macd(params)
                            if macd is not None and isinstance(macd, tuple) and len(macd) == 3:
                                dif, dea, hist = macd
                                value = f"DIF:{dif[-1]:.2f} DEA:{dea[-1]:.2f}"
                                if dif[-1] > dea[-1]:
                                    status = "金叉"
                                    suggestion = "买入"
                                else:
                                    status = "死叉"
                                    suggestion = "卖出"
                        elif name == 'KDJ':
                            kdj = self.calculate_kdj(params)
                            if kdj is not None and isinstance(kdj, tuple) and len(kdj) == 3:
                                k, d, j = kdj
                                value = f"K:{k[-1]:.2f} D:{d[-1]:.2f} J:{j[-1]:.2f}"
                                if k[-1] > d[-1]:
                                    status = "多头"
                                    suggestion = "买入"
                                else:
                                    status = "空头"
                                    suggestion = "卖出"
                        elif name == 'RSI':
                            rsi = self.calculate_rsi(params)
                            if rsi is not None and len(rsi) > 0:
                                value = f"{rsi[-1]:.2f}"
                                if rsi[-1] > 70:
                                    status = "超买"
                                    suggestion = "卖出"
                                elif rsi[-1] < 30:
                                    status = "超卖"
                                    suggestion = "买入"
                                else:
                                    status = "中性"
                                    suggestion = "观望"
                        elif name == 'BOLL':
                            boll = self.calculate_boll(params)
                            if boll is not None and isinstance(boll, tuple) and len(boll) == 3:
                                mid, upper, lower = boll
                                value = f"中轨:{mid[-1]:.2f} 上轨:{upper[-1]:.2f} 下轨:{lower[-1]:.2f}"
                                close = self.current_kdata['close']
                                if close[-1] > upper[-1]:
                                    status = "突破上轨"
                                    suggestion = "卖出"
                                elif close[-1] < lower[-1]:
                                    status = "跌破下轨"
                                    suggestion = "买入"
                                else:
                                    status = "区间"
                                    suggestion = "观望"
                        elif name == 'ATR':
                            atr = self.calculate_atr(params)
                            if atr is not None and len(atr) > 0:
                                value = f"{atr[-1]:.2f}"
                                status = "波动率"
                                suggestion = "观望"
                        elif name == 'OBV':
                            obv = self.calculate_obv(params)
                            if obv is not None and len(obv) > 0:
                                value = f"{obv[-1]:.2f}"
                                status = "量能"
                                suggestion = "观望"
                        elif name == 'CCI':
                            cci = self.calculate_cci(params)
                            if cci is not None and len(cci) > 0:
                                value = f"{cci[-1]:.2f}"
                                if cci[-1] > 100:
                                    status = "超买"
                                    suggestion = "卖出"
                                elif cci[-1] < -100:
                                    status = "超卖"
                                    suggestion = "买入"
                                else:
                                    status = "中性"
                                    suggestion = "观望"
                        # 结果填充
                        self.technical_table.insertRow(row_idx)
                        self.technical_table.setItem(
                            row_idx, 0, QTableWidgetItem(name))
                        self.technical_table.setItem(
                            row_idx, 1, QTableWidgetItem(value))
                        self.technical_table.setItem(
                            row_idx, 2, QTableWidgetItem(status))
                        self.technical_table.setItem(
                            row_idx, 3, QTableWidgetItem(suggestion))
                        row_idx += 1
                    except Exception as e:
                        self.log_manager.log(
                            f"分析指标{name}异常: {str(e)}", LogLevel.ERROR)
                        from PyQt5.QtWidgets import QMessageBox
                        QMessageBox.warning(
                            self, "分析异常", f"分析指标{name}异常: {str(e)}")
                if row_idx == 0:
                    self.technical_table.setRowCount(1)
                    for col in range(self.technical_table.columnCount()):
                        self.technical_table.setItem(
                            0, col, QTableWidgetItem("无数据"))
                self.technical_table.resizeColumnsToContents()
            except Exception as e:
                self.log_manager.log(f"计算技术指标失败: {str(e)}", LogLevel.ERROR)
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "分析异常", f"计算技术指标失败: {str(e)}")
            finally:
                elapsed = int((time.time() - start_time) * 1000)
                self.log_manager.performance(
                    f"[AnalysisWidget.calculate_indicators] 结束，耗时: {elapsed} ms")
        except Exception as e:
            self.log_manager.error(f"技术分析异常: {str(e)}")
            QMessageBox.warning(self, "错误", f"技术分析异常: {str(e)}")

    def calculate_ma(self, params=None):
        """计算MA指标，参数从主窗口统一接口获取"""
        try:
            import pandas as pd
            if self.current_kdata is None or (isinstance(self.current_kdata, pd.DataFrame) and self.current_kdata.empty):
                return None
            period = params.get('period', 20) if params else 20
            close = self.current_kdata['close'] if isinstance(self.current_kdata, pd.DataFrame) else getattr(self.current_kdata, 'close', None)
            if close is None or len(close) == 0:
                return None
            if isinstance(close, pd.Series):
                return calc_ma(close, period)
            else:
                from hikyuu.indicator import MA
                return MA(close, n=period)
        except Exception as e:
            self.log_manager.log(f"计算MA指标失败: {str(e)}", LogLevel.ERROR)
            return None

    def calculate_macd(self, params=None):
        """计算MACD指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            fast = params.get('fast', 12) if params else 12
            slow = params.get('slow', 26) if params else 26
            signal = params.get('signal', 9) if params else 9
            close = self.current_kdata['close'] if isinstance(self.current_kdata, pd.DataFrame) else getattr(self.current_kdata, 'close', None)
            if isinstance(close, pd.Series):
                return calc_macd(close, fast, slow, signal)
            else:
                from hikyuu.indicator import MACD
                macd = MACD(close, n1=fast, n2=slow, n3=signal)
                # 返回tuple，兼容pandas
                return (macd.dif if hasattr(macd, 'dif') else macd,
                        macd.dea if hasattr(macd, 'dea') else None,
                        macd.bar if hasattr(macd, 'bar') else None)
        except Exception as e:
            self.log_manager.log(
                f"计算MACD指标失败: {str(e)}", LogLevel.ERROR)
            return None

    def calculate_kdj(self, params=None):
        """计算KDJ指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            n = params.get('n', 9) if params else 9
            m1 = params.get('m1', 3) if params else 3
            m2 = params.get('m2', 3) if params else 3
            return calc_kdj(self.current_kdata, n, m1, m2)
        except Exception as e:
            self.log_manager.log(
                f"计算KDJ指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_rsi(self, params=None):
        """计算RSI指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            period = params.get('period', 14) if params else 14
            return calc_rsi(self.current_kdata['close'], period)
        except Exception as e:
            self.log_manager.log(
                f"计算RSI指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_boll(self, params=None):
        """计算BOLL指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            close = self.current_kdata['close'] if isinstance(self.current_kdata, pd.DataFrame) else getattr(self.current_kdata, 'close', None)
            period = params.get('period', 20) if params else 20
            std = params.get('std', 2) if params else 2
            if isinstance(close, pd.Series):
                return calc_boll(close, period, std)
            else:
                from hikyuu.indicator import BOLL
                return BOLL(close, n=period, width=std)
        except Exception as e:
            self.log_manager.log(
                f"计算BOLL指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_atr(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            n = params.get('period', 14) if params else 14
            if isinstance(self.current_kdata, pd.DataFrame):
                return calc_atr(self.current_kdata, n)
            else:
                from hikyuu.indicator import ATR
                return ATR(self.current_kdata, n=n)
        except Exception as e:
            self.log_manager.log(f"计算ATR指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_obv(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            if isinstance(self.current_kdata, pd.DataFrame):
                return calc_obv(self.current_kdata)
            else:
                from hikyuu.indicator import OBV
                return OBV(self.current_kdata)
        except Exception as e:
            self.log_manager.log(f"计算OBV指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_cci(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            n = params.get('period', 14) if params else 14
            if isinstance(self.current_kdata, pd.DataFrame):
                return calc_cci(self.current_kdata, n)
            else:
                from hikyuu.indicator import CCI
                return CCI(self.current_kdata, n=n)
        except Exception as e:
            self.log_manager.log(f"计算CCI指标失败: {str(e)}", LogLevel.ERROR)

    def clear_indicators(self):
        """清除指标"""
        try:
            self.current_stock = None
            self.current_kdata = None
            self.current_indicators = []
            self.indicator_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(
                f"清除指标失败: {str(e)}", LogLevel.ERROR)
            raise

    def on_indicator_changed(self, text):
        """指标变更处理"""
        try:
            self.indicator_changed.emit(text)
        except Exception as e:
            self.log_manager.log(
                f"指标变更处理失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_pattern_tab(self) -> QWidget:
        """创建形态分析Tab，支持多条件组合筛选、分组统计、导出自定义格式、价格区间自定义和统计可视化"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 多条件筛选控件区 - 重新设计布局
        filter_main_layout = QHBoxLayout()

        # 左侧：类型多选
        type_group = QGroupBox("形态类型")
        type_layout = QVBoxLayout(type_group)
        self.pattern_type_filter = QListWidget()
        self.pattern_type_filter.setSelectionMode(QAbstractItemView.MultiSelection)
        self.pattern_type_filter.setMaximumHeight(150)
        type_layout.addWidget(self.pattern_type_filter)
        filter_main_layout.addWidget(type_group, stretch=2)

        # 中间：置信度区间、时间区间、筛选识别按钮垂直布局
        middle_group = QGroupBox("筛选条件")
        middle_layout = QVBoxLayout(middle_group)

        # 置信度区间
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度区间:"))
        self.conf_min_spin = QDoubleSpinBox()
        self.conf_min_spin.setRange(0, 1)
        self.conf_min_spin.setSingleStep(0.05)
        self.conf_min_spin.setValue(0)
        self.conf_min_spin.setToolTip("设置形态识别的最小置信度阈值\n范围：0.0-1.0\n建议：0.6以上为高置信度形态")

        self.conf_max_spin = QDoubleSpinBox()
        self.conf_max_spin.setRange(0, 1)
        self.conf_max_spin.setSingleStep(0.05)
        self.conf_max_spin.setValue(1)
        self.conf_max_spin.setToolTip("设置形态识别的最大置信度阈值\n范围：0.0-1.0\n通常设置为1.0以包含所有形态")

        conf_layout.addWidget(self.conf_min_spin)
        conf_layout.addWidget(QLabel("-"))
        conf_layout.addWidget(self.conf_max_spin)
        middle_layout.addLayout(conf_layout)

        # 时间区间
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("时间区间:"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(-365))  # 默认一年前
        self.date_start.setToolTip("设置形态识别的开始日期\n点击可打开日历选择器\n建议选择有足够数据的时间段")

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())  # 默认当前日期
        self.date_end.setToolTip("设置形态识别的结束日期\n点击可打开日历选择器\n默认为当前日期")

        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("-"))
        date_layout.addWidget(self.date_end)
        middle_layout.addLayout(date_layout)

        # 按钮区域
        btn_layout = QVBoxLayout()
        filter_btn = QPushButton("筛选")
        filter_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        filter_btn.setToolTip("根据设置的条件筛选形态识别结果\n快捷键：Ctrl+F")

        identify_btn = QPushButton("识别形态")
        identify_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        identify_btn.clicked.connect(self.identify_patterns)
        identify_btn.setToolTip("开始识别K线形态\n支持双顶、双底等经典形态\n快捷键：Ctrl+R")

        btn_layout.addWidget(filter_btn)
        btn_layout.addWidget(identify_btn)
        middle_layout.addLayout(btn_layout)

        filter_main_layout.addWidget(middle_group, stretch=2)

        # 右侧：信号多选
        signal_group = QGroupBox("交易信号")
        signal_layout = QVBoxLayout(signal_group)
        self.signal_filter = QListWidget()
        self.signal_filter.setSelectionMode(QAbstractItemView.MultiSelection)
        self.signal_filter.setMaximumHeight(150)
        signal_layout.addWidget(self.signal_filter)
        filter_main_layout.addWidget(signal_group, stretch=2)

        layout.addLayout(filter_main_layout)

        # 数据状态显示区域
        status_group = QGroupBox("数据状态")
        status_layout = QHBoxLayout(status_group)

        self.data_status_label = QLabel("等待数据...")
        self.data_status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        status_layout.addWidget(self.data_status_label)

        # 添加刷新数据按钮
        refresh_data_btn = QPushButton("刷新数据状态")
        refresh_data_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")
        refresh_data_btn.clicked.connect(self._update_data_status)
        status_layout.addWidget(refresh_data_btn)

        layout.addWidget(status_group)

        # 统计区
        self.pattern_stat_label = QLabel()
        layout.addWidget(self.pattern_stat_label)

        # 结果表格
        self.pattern_table = QTableWidget(0, 10)
        self.pattern_table.setHorizontalHeaderLabels([
            "序号", "形态名称", "形态类别", "信号类型", "置信度", "置信度等级",
            "K线索引", "出现时间", "价格", "描述"
        ])
        self.pattern_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pattern_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pattern_table)

        # 导出按钮和格式选择
        export_layout = QHBoxLayout()
        self.export_format = QComboBox()
        self.export_format.addItems(["Excel", "CSV", "JSON"])
        export_btn = QPushButton("导出")
        export_layout.addWidget(QLabel("导出格式:"))
        export_layout.addWidget(self.export_format)
        export_layout.addWidget(export_btn)

        # 新增：清除结果按钮
        clear_btn = QPushButton("清除结果")
        clear_btn.clicked.connect(self.clear_patterns)
        export_layout.addWidget(clear_btn)
        layout.addLayout(export_layout)

        # 筛选逻辑
        def do_filter():
            all_signals = getattr(self, '_all_pattern_signals', [])
            # 类型多选
            types = [item.text() for item in self.pattern_type_filter.selectedItems()]
            # 信号多选
            signals = [item.text() for item in self.signal_filter.selectedItems()]
            conf_min = self.conf_min_spin.value()
            conf_max = self.conf_max_spin.value()
            date_start = self.date_start.date().toPyDate()
            date_end = self.date_end.date().toPyDate()
            filtered = []
            for pat in all_signals:
                if types and str(pat.get('type')) not in types:
                    continue
                if signals and pat.get('signal') not in signals:
                    continue
                if not (conf_min <= pat.get('confidence', 0) <= conf_max):
                    continue
                dt = pat.get('datetime', None)
                if dt:
                    try:
                        dt_val = pd.to_datetime(dt).date()
                        if dt_val < date_start or dt_val > date_end:
                            continue
                    except Exception:
                        pass
                filtered.append(pat)
            self._show_pattern_table(filtered)

        filter_btn.clicked.connect(do_filter)
        self.conf_min_spin.valueChanged.connect(do_filter)
        self.conf_max_spin.valueChanged.connect(do_filter)
        self.date_start.dateChanged.connect(do_filter)
        self.date_end.dateChanged.connect(do_filter)

        # 导出逻辑
        def do_export():
            import pandas as pd
            filtered = []
            for row in range(self.pattern_table.rowCount()):
                row_data = {}
                for col in range(self.pattern_table.columnCount()):
                    header = self.pattern_table.horizontalHeaderItem(col).text()
                    item = self.pattern_table.item(row, col)
                    row_data[header] = item.text() if item else ''
                filtered.append(row_data)
            df = pd.DataFrame(filtered)
            fmt = self.export_format.currentText()
            from PyQt5.QtWidgets import QFileDialog
            fname, _ = QFileDialog.getSaveFileName(tab, "导出文件", "pattern_signals."+fmt.lower(), f"*.{fmt.lower()}")
            if not fname:
                return
            if fmt == "Excel":
                df.to_excel(fname, index=False)
            elif fmt == "CSV":
                df.to_csv(fname, index=False)
            elif fmt == "JSON":
                df.to_json(fname, orient='records', force_ascii=False)

        export_btn.clicked.connect(do_export)

        # 信号控制区域
        signal_control_group = QGroupBox("信号控制")
        signal_control_layout = QHBoxLayout(signal_control_group)

        self.signal_type_filter = QComboBox()
        self.signal_type_filter.addItems(["全部", "double_top", "double_bottom"])
        self.signal_type_filter.currentTextChanged.connect(self.refresh_pattern_data)

        self.signal_visible_checkbox = QCheckBox("显示信号标记")
        self.signal_visible_checkbox.setChecked(True)
        self.signal_visible_checkbox.stateChanged.connect(self.refresh_pattern_data)

        signal_control_layout.addWidget(QLabel("信号类型:"))
        signal_control_layout.addWidget(self.signal_type_filter)
        signal_control_layout.addWidget(self.signal_visible_checkbox)

        layout.addWidget(signal_control_group)

        # 统计图表区域
        stats_group = QGroupBox("统计分析")
        stats_layout = QHBoxLayout(stats_group)

        # 创建图表组件实例
        self.pattern_type_pie = MatplotlibWidget()
        self.price_dist_bar = MatplotlibWidget()

        # 类型分布饼图
        pie_card = QFrame()
        pie_card.setFrameStyle(QFrame.StyledPanel)
        pie_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        pie_layout = QVBoxLayout(pie_card)
        pie_layout.addWidget(QLabel("类型分布"))
        pie_layout.addWidget(self.pattern_type_pie)
        stats_layout.addWidget(pie_card, stretch=2)

        # 价格区间分布柱状图
        bar_card = QFrame()
        bar_card.setFrameStyle(QFrame.StyledPanel)
        bar_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        bar_layout = QVBoxLayout(bar_card)
        bar_layout.addWidget(QLabel("价格区间分布"))
        bar_layout.addWidget(self.price_dist_bar)
        stats_layout.addWidget(bar_card, stretch=3)

        layout.addWidget(stats_group)

        # 价格区间自定义控件
        price_bin_layout = QHBoxLayout()
        price_bin_layout.addWidget(QLabel("价格区间自定义（逗号分隔）:"))
        self.price_bins_edit = QLineEdit()
        self.price_bins_edit.setPlaceholderText("如: 0,10,20,50,100")
        price_bin_layout.addWidget(self.price_bins_edit)
        price_bin_btn = QPushButton("应用区间")
        price_bin_layout.addWidget(price_bin_btn)
        layout.addLayout(price_bin_layout)

        # 刷新和质量报告按钮
        bottom_btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.refresh_pattern_data)
        refresh_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")

        export_quality_btn = QPushButton("导出数据质量报告")
        export_quality_btn.setStyleSheet("QPushButton { background-color: #ffc107; color: black; }")

        def do_export_quality():
            if hasattr(self, 'quality_report') and self.quality_report:
                from PyQt5.QtWidgets import QFileDialog, QMessageBox
                file_path, fmt = QFileDialog.getSaveFileName(self, "导出数据质量报告", "quality_report.xlsx",
                                                             "Excel Files (*.xlsx);;CSV Files (*.csv);;HTML Files (*.html)")
                if file_path:
                    try:
                        # 简化导出逻辑，直接保存为JSON格式
                        import json
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(self.quality_report, f, ensure_ascii=False, indent=2)
                        QMessageBox.information(self, "导出成功", f"数据质量报告已导出到：{file_path}")
                    except Exception as e:
                        QMessageBox.warning(self, "导出失败", f"导出失败：{str(e)}")
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "无数据", "当前无可用数据质量报告，请先运行分析！")

        export_quality_btn.clicked.connect(do_export_quality)

        bottom_btn_layout.addWidget(refresh_btn)
        bottom_btn_layout.addWidget(export_quality_btn)
        layout.addLayout(bottom_btn_layout)

        # 表格样式美化
        self.pattern_table.setAlternatingRowColors(True)
        self.pattern_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.pattern_table.setSortingEnabled(True)
        self.pattern_table.itemSelectionChanged.connect(self._on_pattern_table_selection_changed)

        return tab

    def refresh_pattern_data(self):
        """强制刷新形态识别Tab缓存和数据，异步执行分析"""
        self.current_kdata = None
        # 清理pattern_cache等相关缓存（如有）
        self.identify_patterns()
        # 根据筛选和显隐状态过滤信号
        if hasattr(self, 'signal_type_filter'):
            filter_type = self.signal_type_filter.currentText()
        else:
            filter_type = "全部"

        if hasattr(self, 'signal_visible_checkbox'):
            visible = self.signal_visible_checkbox.isChecked()
        else:
            visible = True

        signals = getattr(self, '_all_pattern_signals', [])
        if filter_type != "全部":
            signals = [s for s in signals if s.get('type') == filter_type]

        # 主图信号联动
        if hasattr(self, 'chart_widget') and self.chart_widget:
            if visible:
                visible_range = getattr(self.chart_widget, 'get_visible_range', lambda: None)()
                self.chart_widget.plot_signals(signals, visible_range=visible_range,
                                               signal_filter={filter_type} if filter_type != "全部" else None)
            else:
                self.chart_widget.plot_signals([])

        # 统计图表可视化优化
        if hasattr(self, 'pattern_type_pie') and signals:
            self.pattern_type_pie.plot_pie([s['type'] for s in signals])
        if hasattr(self, 'price_dist_bar') and signals:
            self.price_dist_bar.plot_bar([s.get('price', 0) for s in signals])

    def _show_pattern_table(self, pattern_signals):
        """显示形态识别结果表格 - 增强版"""
        try:
            if not pattern_signals:
                self.pattern_table.setRowCount(0)
                return

            # 设置表格列数和表头
            self.pattern_table.setColumnCount(10)
            self.pattern_table.setHorizontalHeaderLabels([
                "序号", "形态名称", "形态类别", "信号类型", "置信度", "置信度等级",
                "K线索引", "出现时间", "价格", "描述"
            ])

            self.pattern_table.setRowCount(len(pattern_signals))

            for i, sig in enumerate(pattern_signals):
                # 序号
                self.pattern_table.setItem(i, 0, QTableWidgetItem(str(i+1)))

                # 形态名称（优先使用中文名称）
                pattern_name = sig.get('pattern_name', sig.get('type', '未知'))
                name_item = QTableWidgetItem(pattern_name)
                name_item.setToolTip(sig.get('pattern_description', ''))
                self.pattern_table.setItem(i, 1, name_item)

                # 形态类别
                category = sig.get('pattern_category', sig.get('category', '未分类'))
                self.pattern_table.setItem(i, 2, QTableWidgetItem(category))

                # 信号类型（转换为中文）
                signal_type = sig.get('signal', 'neutral')
                signal_cn = {
                    'buy': '买入',
                    'sell': '卖出',
                    'neutral': '中性'
                }.get(signal_type, signal_type)

                signal_item = QTableWidgetItem(signal_cn)
                # 根据信号类型设置颜色
                if signal_type == 'buy':
                    signal_item.setForeground(QColor(0, 150, 0))  # 绿色
                elif signal_type == 'sell':
                    signal_item.setForeground(QColor(200, 0, 0))  # 红色
                else:
                    signal_item.setForeground(QColor(128, 128, 128))  # 灰色
                self.pattern_table.setItem(i, 3, signal_item)

                # 置信度
                confidence = sig.get('confidence', 0)
                confidence_item = QTableWidgetItem(f"{confidence:.3f}")
                # 根据置信度设置背景色
                if confidence >= 0.8:
                    confidence_item.setBackground(QColor(144, 238, 144))  # 浅绿
                elif confidence >= 0.6:
                    confidence_item.setBackground(QColor(255, 255, 144))  # 浅黄
                else:
                    confidence_item.setBackground(QColor(255, 182, 193))  # 浅红
                self.pattern_table.setItem(i, 4, confidence_item)

                # 置信度等级
                if confidence >= 0.8:
                    confidence_level = "高"
                elif confidence >= 0.6:
                    confidence_level = "中"
                elif confidence >= 0.4:
                    confidence_level = "低"
                else:
                    confidence_level = "极低"

                level_item = QTableWidgetItem(confidence_level)
                level_item.setToolTip(f"置信度: {confidence:.3f}")
                self.pattern_table.setItem(i, 5, level_item)

                # K线索引
                index = sig.get('index', '-')
                self.pattern_table.setItem(i, 6, QTableWidgetItem(str(index)))

                # 出现时间
                datetime_str = sig.get('datetime', '')
                if datetime_str:
                    try:
                        # 尝试格式化时间
                        if isinstance(datetime_str, str) and len(datetime_str) > 10:
                            datetime_str = datetime_str[:10]  # 只显示日期部分
                    except:
                        pass
                self.pattern_table.setItem(i, 7, QTableWidgetItem(str(datetime_str)))

                # 价格
                price = sig.get('price', 0)
                price_item = QTableWidgetItem(f"{price:.2f}" if isinstance(price, (int, float)) else str(price))
                self.pattern_table.setItem(i, 8, price_item)

                # 描述
                description = sig.get('pattern_description', sig.get('description', ''))
                if len(description) > 30:
                    description = description[:30] + "..."
                desc_item = QTableWidgetItem(description)
                desc_item.setToolTip(sig.get('pattern_description', ''))
                self.pattern_table.setItem(i, 9, desc_item)

            # 启用排序
            self.pattern_table.setSortingEnabled(True)

            # 调整列宽
            self.pattern_table.resizeColumnsToContents()

            # 确保表格可见
            self.pattern_table.setVisible(True)

        except Exception as e:
            self.log_manager.error(f"显示形态表格失败: {e}")
            # 显示基本表格
            self.pattern_table.setColumnCount(5)
            self.pattern_table.setHorizontalHeaderLabels(["序号", "形态", "K线索引", "出现时间", "价格"])
            self.pattern_table.setRowCount(len(pattern_signals))
            for i, sig in enumerate(pattern_signals):
                self.pattern_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                self.pattern_table.setItem(i, 1, QTableWidgetItem(str(sig.get('type', '未知'))))
                self.pattern_table.setItem(i, 2, QTableWidgetItem(str(sig.get('index', ''))))
                self.pattern_table.setItem(i, 3, QTableWidgetItem(str(sig.get('datetime', ''))))
                self.pattern_table.setItem(i, 4, QTableWidgetItem(str(sig.get('price', ''))))
            self.pattern_table.setSortingEnabled(True)

    def identify_patterns(self):
        """识别K线形态 - 使用新的形态管理器"""
        # 检查形态管理器
        if self.pattern_manager is None:
            QMessageBox.warning(self, "警告", "形态管理器未初始化，无法进行形态识别")
            return

        # 检查数据有效性
        if self.current_kdata is None or (hasattr(self.current_kdata, 'empty') and self.current_kdata.empty) or len(self.current_kdata) == 0:
            QMessageBox.warning(self, "警告", "请先选择股票数据")
            return

        try:
            self.log_manager.info("开始识别K线形态...")

            # 预处理K线数据，确保格式正确
            processed_kdata = self._kdata_preprocess(self.current_kdata.copy(), "形态识别")
            if processed_kdata.empty:
                QMessageBox.warning(self, "警告", "K线数据预处理失败")
                return

            self.log_manager.info(f"K线数据预处理完成，数据长度: {len(processed_kdata)}, 字段: {list(processed_kdata.columns)}")

            # 获取置信度阈值
            confidence_threshold = self.conf_min_spin.value()

            # 获取时间范围
            start_date = self.date_start.date().toPyDate()
            end_date = self.date_end.date().toPyDate()

            # 修复的时间过滤逻辑 - 基于datetime列而不是index
            filtered_kdata = processed_kdata
            if 'datetime' in processed_kdata.columns:
                try:
                    # 确保datetime列是时间格式
                    datetime_col = pd.to_datetime(processed_kdata['datetime'])

                    # 基于datetime列进行过滤
                    mask = (datetime_col.dt.date >= start_date) & (datetime_col.dt.date <= end_date)
                    filtered_kdata = processed_kdata[mask].copy()

                    self.log_manager.info(f"时间过滤完成，从 {len(processed_kdata)} 条数据过滤到 {len(filtered_kdata)} 条")
                except Exception as e:
                    self.log_manager.warning(f"时间过滤失败: {e}，使用全部数据进行分析")
                    filtered_kdata = processed_kdata
            else:
                self.log_manager.warning("数据中没有datetime字段，跳过时间过滤")

            if len(filtered_kdata) == 0:
                QMessageBox.warning(self, "警告", "指定时间范围内无数据")
                return

            # 获取选中的形态类型（如果有多选功能）
            selected_patterns = None
            if hasattr(self, 'pattern_type_filter'):
                selected_items = self.pattern_type_filter.selectedItems()
                if selected_items:
                    # 将中文名称转换为英文名称
                    selected_patterns = []
                    for item in selected_items:
                        pattern_name = item.text()
                        pattern_config = self.pattern_manager.get_pattern_by_name(pattern_name)
                        if pattern_config:
                            selected_patterns.append(pattern_config.english_name)

            self.log_manager.info(f"开始形态识别，数据长度: {len(filtered_kdata)}, 置信度阈值: {confidence_threshold}")
            if selected_patterns:
                self.log_manager.info(f"选中的形态类型: {selected_patterns}")

            # 使用形态管理器识别形态
            patterns = self.pattern_manager.identify_all_patterns(
                filtered_kdata,
                selected_patterns=selected_patterns,
                confidence_threshold=confidence_threshold
            )

            # 缓存所有形态信号供筛选使用
            self._all_pattern_signals = patterns

            # 显示结果
            self._show_pattern_table(patterns)

            # 更新形态类型和信号过滤器选项
            self._update_pattern_filter_options()

            self.log_manager.info(f"形态识别完成，共识别出 {len(patterns)} 个形态")

            # 显示统计信息
            if patterns:
                stats = self.pattern_manager.get_pattern_statistics(filtered_kdata)
                self._update_pattern_statistics(stats)
            else:
                # 如果没有识别到形态，显示提示信息
                if hasattr(self, 'pattern_stat_label'):
                    self.pattern_stat_label.setText(f"数据长度: {len(filtered_kdata)}, 置信度阈值: {confidence_threshold}, 识别结果: 0 个形态")

        except Exception as e:
            error_msg = f"形态识别失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(f"错误详情: {traceback.format_exc()}")
            QMessageBox.critical(self, "错误", error_msg)

    def _update_pattern_filter_options(self):
        """更新形态过滤器选项"""
        try:
            # 更新形态类型选项
            if hasattr(self, 'pattern_type_filter'):
                self.pattern_type_filter.clear()
                pattern_configs = self.pattern_manager.get_pattern_configs()
                for config in pattern_configs:
                    item = QListWidgetItem(config.name)
                    item.setToolTip(config.description)
                    self.pattern_type_filter.addItem(item)

            # 更新信号类型选项
            if hasattr(self, 'signal_filter'):
                self.signal_filter.clear()
                signal_types = self.pattern_manager.get_signal_types()
                for signal_type in signal_types:
                    signal_name = {
                        'buy': '买入',
                        'sell': '卖出',
                        'neutral': '中性'
                    }.get(signal_type, signal_type)
                    item = QListWidgetItem(signal_name)
                    item.setData(Qt.UserRole, signal_type)  # 存储原始值
                    self.signal_filter.addItem(item)

        except Exception as e:
            self.log_manager.error(f"更新过滤器选项失败: {e}")

    def _update_pattern_statistics(self, stats: dict):
        """更新形态统计显示"""
        try:
            # 构建统计信息文本
            stat_text = f"总计: {stats['total_patterns']} 个形态"

            if stats['by_category']:
                category_info = ", ".join([f"{k}: {v}" for k, v in stats['by_category'].items()])
                stat_text += f" | 分类: {category_info}"

            if stats['by_signal']:
                signal_info = ", ".join([f"{k}: {v}" for k, v in stats['by_signal'].items()])
                stat_text += f" | 信号: {signal_info}"

            confidence_dist = stats['confidence_distribution']
            stat_text += f" | 置信度: 高({confidence_dist['high']}) 中({confidence_dist['medium']}) 低({confidence_dist['low']})"

            # 更新统计标签
            if hasattr(self, 'pattern_stat_label'):
                self.pattern_stat_label.setText(stat_text)

        except Exception as e:
            self.log_manager.error(f"更新统计信息失败: {e}")

    def clear_patterns(self):
        """清除形态识别结果"""
        try:
            self.pattern_table.setRowCount(0)
            self._all_pattern_signals = []
            if hasattr(self, 'pattern_stat_label'):
                self.pattern_stat_label.setText("尚未进行形态识别")
        except Exception as e:
            self.log_manager.log(
                f"清除形态识别结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_trend_tab(self) -> QWidget:
        """创建趋势分析Tab，采用卡片式布局，分区展示参数控制、分析类型、结果展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 参数控制区域
        control_group = QGroupBox("趋势分析控制")
        control_layout = QHBoxLayout(control_group)

        # 左侧：分析类型选择
        type_card = QFrame()
        type_card.setFrameStyle(QFrame.StyledPanel)
        type_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        type_layout = QVBoxLayout(type_card)
        type_layout.addWidget(QLabel("分析类型"))

        self.trend_type_combo = QComboBox()
        self.trend_type_combo.addItems(['价格趋势', '成交量趋势', 'MACD趋势', 'KDJ趋势', 'RSI趋势'])
        type_layout.addWidget(self.trend_type_combo)

        # 分析按钮
        analyze_btn = QPushButton("开始分析")
        analyze_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        analyze_btn.clicked.connect(self.analyze_trend)

        clear_trend_btn = QPushButton("清除结果")
        clear_trend_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        clear_trend_btn.clicked.connect(self.clear_trend)

        type_layout.addWidget(analyze_btn)
        type_layout.addWidget(clear_trend_btn)
        control_layout.addWidget(type_card, stretch=2)

        # 右侧：参数设置
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        params_layout = QVBoxLayout(params_card)
        params_layout.addWidget(QLabel("参数设置"))

        # 周期参数
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("分析周期:"))
        self.trend_period_spin = QSpinBox()
        self.trend_period_spin.setRange(5, 100)
        self.trend_period_spin.setValue(20)
        period_layout.addWidget(self.trend_period_spin)
        params_layout.addLayout(period_layout)

        # 阈值参数
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("趋势阈值:"))
        self.trend_threshold_spin = QDoubleSpinBox()
        self.trend_threshold_spin.setRange(0.01, 1.0)
        self.trend_threshold_spin.setSingleStep(0.01)
        self.trend_threshold_spin.setValue(0.05)
        threshold_layout.addWidget(self.trend_threshold_spin)
        params_layout.addLayout(threshold_layout)

        # 敏感度参数
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("敏感度:"))
        self.trend_sensitivity_spin = QDoubleSpinBox()
        self.trend_sensitivity_spin.setRange(0.1, 2.0)
        self.trend_sensitivity_spin.setSingleStep(0.1)
        self.trend_sensitivity_spin.setValue(1.0)
        sensitivity_layout.addWidget(self.trend_sensitivity_spin)
        params_layout.addLayout(sensitivity_layout)

        control_layout.addWidget(params_card, stretch=2)
        layout.addWidget(control_group)

        # 趋势统计区域
        stats_group = QGroupBox("趋势统计")
        stats_layout = QHBoxLayout(stats_group)

        # 趋势强度指示器
        strength_card = QFrame()
        strength_card.setFrameStyle(QFrame.StyledPanel)
        strength_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        strength_layout = QVBoxLayout(strength_card)
        strength_layout.addWidget(QLabel("趋势强度"))

        self.trend_strength_label = QLabel("未分析")
        self.trend_strength_label.setAlignment(Qt.AlignCenter)
        self.trend_strength_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #007bff; }")
        strength_layout.addWidget(self.trend_strength_label)

        stats_layout.addWidget(strength_card, stretch=1)

        # 趋势方向指示器
        direction_card = QFrame()
        direction_card.setFrameStyle(QFrame.StyledPanel)
        direction_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        direction_layout = QVBoxLayout(direction_card)
        direction_layout.addWidget(QLabel("趋势方向"))

        self.trend_direction_label = QLabel("未分析")
        self.trend_direction_label.setAlignment(Qt.AlignCenter)
        self.trend_direction_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #28a745; }")
        direction_layout.addWidget(self.trend_direction_label)

        stats_layout.addWidget(direction_card, stretch=1)

        # 置信度指示器
        confidence_card = QFrame()
        confidence_card.setFrameStyle(QFrame.StyledPanel)
        confidence_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        confidence_layout = QVBoxLayout(confidence_card)
        confidence_layout.addWidget(QLabel("分析置信度"))

        self.trend_confidence_label = QLabel("未分析")
        self.trend_confidence_label.setAlignment(Qt.AlignCenter)
        self.trend_confidence_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #ffc107; }")
        confidence_layout.addWidget(self.trend_confidence_label)

        stats_layout.addWidget(confidence_card, stretch=1)

        layout.addWidget(stats_group)

        # 结果展示区域
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout(results_group)

        # 结果表格
        self.trend_table = QTableWidget(0, 6)
        self.trend_table.setHorizontalHeaderLabels(['时间', '类型', '趋势', '强度', '置信度', '建议'])
        self.trend_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trend_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 表格样式美化
        self.trend_table.setAlternatingRowColors(True)
        self.trend_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.trend_table.setSortingEnabled(True)

        results_layout.addWidget(self.trend_table)

        # 导出和刷新按钮
        bottom_layout = QHBoxLayout()

        export_trend_format = QComboBox()
        export_trend_format.addItems(["Excel", "CSV", "JSON"])
        export_trend_btn = QPushButton("导出趋势分析")
        export_trend_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")

        refresh_trend_btn = QPushButton("刷新数据")
        refresh_trend_btn.clicked.connect(self.refresh_trend_data)
        refresh_trend_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")

        bottom_layout.addWidget(QLabel("导出格式:"))
        bottom_layout.addWidget(export_trend_format)
        bottom_layout.addWidget(export_trend_btn)
        bottom_layout.addWidget(refresh_trend_btn)
        bottom_layout.addStretch()

        results_layout.addLayout(bottom_layout)
        layout.addWidget(results_group)

        return tab

    def refresh_trend_data(self):
        """强制刷新趋势分析Tab缓存和数据，异步执行分析"""
        self.current_kdata = None
        self.analyze_trend()

    def analyze_trend(self):
        """趋势分析，自动补全K线数据，支持主图/主窗口数据同步"""
        try:
            kdata = self.current_kdata
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                pass
            kdata = self._kdata_preprocess(kdata, context="趋势分析")
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                self.log_manager.warning("无K线数据，无法进行趋势分析")
                QMessageBox.warning(self, "提示", "无K线数据，无法进行趋势分析")
                return
            self.trend_table.setRowCount(0)
            # 修复DataFrame布尔判断错误
            if self.current_kdata is None or (hasattr(self.current_kdata, 'empty') and self.current_kdata.empty):
                self.trend_table.setRowCount(1)
                for col in range(self.trend_table.columnCount()):
                    self.trend_table.setItem(0, col, QTableWidgetItem("无数据"))
                return
            period = self.trend_period_spin.value()
            threshold = self.trend_threshold_spin.value()
            sensitivity = self.trend_sensitivity_spin.value()
            self.analyze_price_trend(period, threshold, sensitivity)
            self.analyze_volume_trend(period, threshold, sensitivity)
            self.analyze_macd_trend(period, threshold, sensitivity)
            self.analyze_kdj_trend(period, threshold, sensitivity)
            self.analyze_rsi_trend(period, threshold, sensitivity)
            if self.trend_table.rowCount() == 0:
                self.trend_table.setRowCount(1)
                for col in range(self.trend_table.columnCount()):
                    self.trend_table.setItem(0, col, QTableWidgetItem("无数据"))
            self.trend_table.resizeColumnsToContents()
        except Exception as e:
            self.log_manager.error(f"趋势分析异常: {str(e)}")
            QMessageBox.warning(self, "错误", f"趋势分析异常: {str(e)}")

    def analyze_price_trend(self, period: int, threshold: float, sensitivity: float):
        """分析价格趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
            sensitivity: 敏感度
        """
        try:
            close = self.current_kdata.close
            ma = MA(close, period)

            # 计算趋势
            trend = "上升" if float(close[-1]) > float(ma[-1]) else "下降"

            # 计算趋势强度
            strength = abs(float(close[-1]) -
                           float(ma[-1])) / float(ma[-1]) * 100

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("价格")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "上升" else Qt.green
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "上升" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if trend == "上升" else Qt.green
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            self.log_manager.log(
                f"分析价格趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_volume_trend(self, period: int, threshold: float, sensitivity: float):
        """分析成交量趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
            sensitivity: 敏感度
        """
        try:
            # 兼容DataFrame和KData
            if hasattr(self.current_kdata, 'volume'):
                volume = self.current_kdata.volume
            elif isinstance(self.current_kdata, dict) and 'volume' in self.current_kdata:
                volume = self.current_kdata['volume']
            elif isinstance(self.current_kdata, pd.DataFrame) and 'volume' in self.current_kdata.columns:
                volume = self.current_kdata['volume']
            else:
                from hikyuu import VOL
                volume = VOL(self.current_kdata)
            from indicators_algo import calc_ma
            ma = calc_ma(volume, period)

            trend = "放量" if float(volume[-1]) > float(ma[-1]) else "缩量"
            strength = abs(float(volume[-1]) -
                           float(ma[-1])) / float(ma[-1]) * 100

            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("成交量"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "放量" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            price_trend = self.trend_table.item(0, 1).text()
            if price_trend == "上升":
                suggestion = "买入" if trend == "放量" else "观望"
            else:
                suggestion = "卖出" if trend == "放量" else "观望"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "买入" else Qt.green if suggestion == "卖出" else Qt.black)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析成交量趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_macd_trend(self, period: int, threshold: float, sensitivity: float):
        """分析MACD趋势"""
        try:
            # 兼容DataFrame和KData
            close = self.current_kdata['close'] if isinstance(self.current_kdata, pd.DataFrame) else getattr(self.current_kdata, 'close', None)
            if isinstance(close, pd.Series):
                from indicators_algo import calc_macd
                dif, dea, hist = calc_macd(close)
            else:
                from hikyuu.indicator import MACD
                macd = MACD(close)
                if hasattr(macd, 'dif') and hasattr(macd, 'dea'):
                    dif, dea = macd.dif, macd.dea
                elif isinstance(macd, tuple) and len(macd) >= 2:
                    dif, dea = macd[0], macd[1]
                else:
                    raise ValueError("MACD结果格式不支持")
            trend = "多头" if float(dif[-1]) > float(dea[-1]) else "空头"
            strength = abs(float(dif[-1]) - float(dea[-1])) * 100
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("MACD"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "多头" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "多头" else Qt.green)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析MACD趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_kdj_trend(self, period: int, threshold: float, sensitivity: float):
        """分析KDJ趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
            sensitivity: 敏感度
        """
        try:
            # 兼容DataFrame和KData
            if isinstance(self.current_kdata, pd.DataFrame):
                from indicators_algo import calc_kdj
                k, d, j = calc_kdj(self.current_kdata)
            else:
                kdj = KDJ(self.current_kdata)
                # 兼容属性和tuple
                if hasattr(kdj, 'k') and hasattr(kdj, 'd'):
                    k, d = kdj.k, kdj.d
                elif isinstance(kdj, tuple) and len(kdj) >= 2:
                    k, d = kdj[0], kdj[1]
                else:
                    raise ValueError("KDJ结果格式不支持")
            trend = "多头" if float(k[-1]) > float(d[-1]) else "空头"
            strength = abs(float(k[-1]) - float(d[-1]))
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("KDJ"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "多头" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "多头" else Qt.green)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析KDJ趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_rsi_trend(self, period: int, threshold: float, sensitivity: float):
        """分析RSI趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
            sensitivity: 敏感度
        """
        try:
            period = period if period else 14
            if isinstance(self.current_kdata, pd.DataFrame):
                close = self.current_kdata['close']
                from indicators_algo import calc_rsi
                rsi = calc_rsi(close, period)
                last_rsi = float(rsi.iloc[-1]) if not rsi.empty else float('nan')
            else:
                from hikyuu.indicator import RSI, CLOSE
                close_ind = CLOSE(self.current_kdata)
                rsi = RSI(close_ind, n=period)
                last_rsi = float(rsi[-1]) if len(rsi) > 0 else float('nan')

            # 计算趋势
            if last_rsi > 70:
                trend = "超买"
            elif last_rsi < 30:
                trend = "超卖"
            else:
                trend = "中性"

            # 计算趋势强度
            if trend == "超买":
                strength = (last_rsi - 70) / 30 * 100
            elif trend == "超卖":
                strength = (30 - last_rsi) / 30 * 100
            else:
                strength = 0

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("RSI")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "超卖" else
                Qt.green if trend == "超买" else Qt.black
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "超卖" else "卖出" if trend == "超买" else "观望"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "买入" else
                Qt.green if suggestion == "卖出" else Qt.black
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            self.log_manager.log(
                f"分析RSI趋势失败: {str(e)}", LogLevel.ERROR)

    def clear_trend(self):
        """清除趋势分析结果"""
        try:
            self.trend_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(
                f"清除趋势分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_wave_tab(self) -> QWidget:
        """创建波浪分析Tab，采用卡片式布局，分区展示波浪类型、参数控制、结果展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 波浪分析控制区域
        control_group = QGroupBox("波浪分析控制")
        control_layout = QHBoxLayout(control_group)

        # 左侧：波浪类型选择
        type_card = QFrame()
        type_card.setFrameStyle(QFrame.StyledPanel)
        type_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        type_layout = QVBoxLayout(type_card)
        type_layout.addWidget(QLabel("波浪类型"))

        self.wave_type_combo = QComboBox()
        self.wave_type_combo.addItems(['艾略特波浪', '江恩理论', '支撑阻力'])
        type_layout.addWidget(self.wave_type_combo)

        # 分析按钮
        analyze_wave_btn = QPushButton("开始分析")
        analyze_wave_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        analyze_wave_btn.clicked.connect(self.analyze_wave)

        clear_wave_btn = QPushButton("清除结果")
        clear_wave_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        clear_wave_btn.clicked.connect(self.clear_wave)

        type_layout.addWidget(analyze_wave_btn)
        type_layout.addWidget(clear_wave_btn)
        control_layout.addWidget(type_card, stretch=2)

        # 右侧：参数设置
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        params_layout = QVBoxLayout(params_card)
        params_layout.addWidget(QLabel("参数设置"))

        # 波浪周期
        wave_period_layout = QHBoxLayout()
        wave_period_layout.addWidget(QLabel("波浪周期:"))
        self.wave_period_spin = QSpinBox()
        self.wave_period_spin.setRange(10, 200)
        self.wave_period_spin.setValue(50)
        wave_period_layout.addWidget(self.wave_period_spin)
        params_layout.addLayout(wave_period_layout)

        # 敏感度
        wave_sensitivity_layout = QHBoxLayout()
        wave_sensitivity_layout.addWidget(QLabel("敏感度:"))
        self.wave_sensitivity_spin = QDoubleSpinBox()
        self.wave_sensitivity_spin.setRange(0.1, 3.0)
        self.wave_sensitivity_spin.setSingleStep(0.1)
        self.wave_sensitivity_spin.setValue(1.0)
        wave_sensitivity_layout.addWidget(self.wave_sensitivity_spin)
        params_layout.addLayout(wave_sensitivity_layout)

        # 最小波幅
        min_amplitude_layout = QHBoxLayout()
        min_amplitude_layout.addWidget(QLabel("最小波幅:"))
        self.min_amplitude_spin = QDoubleSpinBox()
        self.min_amplitude_spin.setRange(0.01, 0.5)
        self.min_amplitude_spin.setSingleStep(0.01)
        self.min_amplitude_spin.setValue(0.05)
        min_amplitude_layout.addWidget(self.min_amplitude_spin)
        params_layout.addLayout(min_amplitude_layout)

        control_layout.addWidget(params_card, stretch=2)
        layout.addWidget(control_group)

        # 波浪统计区域
        stats_group = QGroupBox("波浪统计")
        stats_layout = QHBoxLayout(stats_group)

        # 波浪数量统计
        count_card = QFrame()
        count_card.setFrameStyle(QFrame.StyledPanel)
        count_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        count_layout = QVBoxLayout(count_card)
        count_layout.addWidget(QLabel("识别波浪数"))

        self.wave_count_label = QLabel("0")
        self.wave_count_label.setAlignment(Qt.AlignCenter)
        self.wave_count_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #007bff; }")
        count_layout.addWidget(self.wave_count_label)

        stats_layout.addWidget(count_card, stretch=1)

        # 当前波浪阶段
        stage_card = QFrame()
        stage_card.setFrameStyle(QFrame.StyledPanel)
        stage_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        stage_layout = QVBoxLayout(stage_card)
        stage_layout.addWidget(QLabel("当前阶段"))

        self.wave_stage_label = QLabel("未分析")
        self.wave_stage_label.setAlignment(Qt.AlignCenter)
        self.wave_stage_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #28a745; }")
        stage_layout.addWidget(self.wave_stage_label)

        stats_layout.addWidget(stage_card, stretch=1)

        # 预测方向
        prediction_card = QFrame()
        prediction_card.setFrameStyle(QFrame.StyledPanel)
        prediction_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        prediction_layout = QVBoxLayout(prediction_card)
        prediction_layout.addWidget(QLabel("预测方向"))

        self.wave_prediction_label = QLabel("未分析")
        self.wave_prediction_label.setAlignment(Qt.AlignCenter)
        self.wave_prediction_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #ffc107; }")
        prediction_layout.addWidget(self.wave_prediction_label)

        stats_layout.addWidget(prediction_card, stretch=1)

        layout.addWidget(stats_group)

        # 结果展示区域
        results_group = QGroupBox("波浪分析结果")
        results_layout = QVBoxLayout(results_group)

        # 结果表格
        self.wave_table = QTableWidget(0, 7)
        self.wave_table.setHorizontalHeaderLabels(['波浪', '类型', '起点', '终点', '幅度', '周期', '置信度'])
        self.wave_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.wave_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 表格样式美化
        self.wave_table.setAlternatingRowColors(True)
        self.wave_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.wave_table.setSortingEnabled(True)

        results_layout.addWidget(self.wave_table)

        # 导出和刷新按钮
        bottom_layout = QHBoxLayout()

        export_wave_format = QComboBox()
        export_wave_format.addItems(["Excel", "CSV", "JSON"])
        export_wave_btn = QPushButton("导出波浪分析")
        export_wave_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")

        refresh_wave_btn = QPushButton("刷新数据")
        refresh_wave_btn.clicked.connect(self.refresh_wave_data)
        refresh_wave_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")

        # 高级功能按钮
        advanced_analysis_btn = QPushButton("高级波浪分析")
        advanced_analysis_btn.setStyleSheet("QPushButton { background-color: #6f42c1; color: white; }")

        bottom_layout.addWidget(QLabel("导出格式:"))
        bottom_layout.addWidget(export_wave_format)
        bottom_layout.addWidget(export_wave_btn)
        bottom_layout.addWidget(refresh_wave_btn)
        bottom_layout.addWidget(advanced_analysis_btn)
        bottom_layout.addStretch()

        results_layout.addLayout(bottom_layout)
        layout.addWidget(results_group)

        return tab

    def refresh_wave_data(self):
        """强制刷新波浪分析Tab缓存和数据，异步执行分析"""
        self.current_kdata = None
        self.analyze_wave()

    def analyze_wave(self):
        """波浪分析，自动补全K线数据，支持主图/主窗口数据同步"""
        try:
            kdata = self.current_kdata
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                pass
            kdata = self._kdata_preprocess(kdata, context="波浪分析")
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                self.log_manager.warning("无K线数据，无法进行波浪分析")
                QMessageBox.warning(self, "提示", "无K线数据，无法进行波浪分析")
                return
            wave_type = self.wave_type_combo.currentText()
            period = self.wave_period_spin.value()
            sensitivity = self.wave_sensitivity_spin.value()
            if wave_type == "艾略特波浪":
                self.analyze_elliott_waves(period, sensitivity)
            elif wave_type == "江恩理论":
                self.analyze_gann(period, sensitivity)
            elif wave_type == "支撑阻力":
                self.analyze_support_resistance(period, sensitivity)
            if self.wave_table.rowCount() == 0:
                self.wave_table.setRowCount(1)
                for col in range(self.wave_table.columnCount()):
                    self.wave_table.setItem(0, col, QTableWidgetItem("无数据"))
            self.wave_table.resizeColumnsToContents()
        except Exception as e:
            self.log_manager.error(f"波浪分析异常: {str(e)}")
            QMessageBox.warning(self, "错误", f"波浪分析异常: {str(e)}")

    def analyze_elliott_waves(self, period: int, sensitivity: float):
        """分析艾略特波浪

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 寻找关键转折点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 识别推动浪
            for i in range(len(peaks)-2):
                # 获取连续3个峰顶点
                p1, p2, p3 = peaks[i:i+3]

                # 检查是否满足推动浪特征
                if (p2[1] > p1[1] and p3[1] > p2[1] and  # 价格逐步上升
                    p2[0] - p1[0] >= period and  # 波浪间隔满足周期要求
                        p3[0] - p2[0] >= period):

                    # 计算波浪强度
                    strength = (p3[1] - p1[1]) / p1[1] * 100

                    if strength >= sensitivity:
                        # 添加识别结果
                        row = self.wave_table.rowCount()
                        self.wave_table.insertRow(row)

                        self.wave_table.setItem(
                            row, 0,
                            QTableWidgetItem("推动浪")
                        )

                        position = f"{p1[0]}-{p3[0]}"
                        self.wave_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        feature = f"上升{strength:.1f}%"
                        self.wave_table.setItem(
                            row, 2,
                            QTableWidgetItem(feature)
                        )

                        suggestion = "买入"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.red)
                        self.wave_table.setItem(row, 3, suggestion_item)

            # 识别调整浪
            for i in range(len(troughs)-2):
                # 获取连续3个谷底点
                t1, t2, t3 = troughs[i:i+3]

                # 检查是否满足调整浪特征
                if (t2[1] < t1[1] and t3[1] < t2[1] and  # 价格逐步下降
                    t2[0] - t1[0] >= period and  # 波浪间隔满足周期要求
                        t3[0] - t2[0] >= period):

                    # 计算波浪强度
                    strength = (t1[1] - t3[1]) / t1[1] * 100

                    if strength >= sensitivity:
                        # 添加识别结果
                        row = self.wave_table.rowCount()
                        self.wave_table.insertRow(row)

                        self.wave_table.setItem(
                            row, 0,
                            QTableWidgetItem("调整浪")
                        )

                        position = f"{t1[0]}-{t3[0]}"
                        self.wave_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        feature = f"下降{strength:.1f}%"
                        self.wave_table.setItem(
                            row, 2,
                            QTableWidgetItem(feature)
                        )

                        suggestion = "卖出"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.green)
                        self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            self.log_manager.log(f"分析艾略特波浪失败: {str(e)}", LogLevel.ERROR)

    def analyze_gann(self, period: int, sensitivity: float):
        """分析江恩理论

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 计算江恩角度线
            last_close = float(close[-1])
            angles = [
                (45, last_close * (1 + 1/1)),   # 1:1线
                (63.75, last_close * (1 + 2/1)),  # 2:1线
                (26.25, last_close * (1 + 1/2)),  # 1:2线
                (71.25, last_close * (1 + 3/1)),  # 3:1线
                (18.75, last_close * (1 + 1/3))  # 1:3线
            ]

            # 检查价格与角度线的关系
            for angle, target in angles:
                # 计算当前价格偏离角度线的百分比
                deviation = abs(target - last_close) / last_close * 100

                if deviation <= sensitivity:
                    # 添加识别结果
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem(f"{angle}°角度线")
                    )

                    position = "当前"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    feature = f"偏离{deviation:.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if last_close < target:
                        suggestion = "买入"
                        color = Qt.red
                    else:
                        suggestion = "卖出"
                        color = Qt.green

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 计算江恩时间周期
            key_dates = [
                (90, "季度周期"),
                (180, "半年周期"),
                (360, "年度周期")
            ]

            current_index = len(close) - 1
            for days, cycle_name in key_dates:
                if current_index % days <= sensitivity * 10:
                    # 添加识别结果
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem(cycle_name)
                    )

                    position = "当前"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    feature = f"周期拐点"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    suggestion = "关注"
                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(Qt.black)
                    self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            self.log_manager.log(f"分析江恩理论失败: {str(e)}", LogLevel.ERROR)

    def analyze_support_resistance(self, period: int, sensitivity: float):
        """分析支撑阻力位

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 寻找局部极值点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 聚类相近的价格水平
            def cluster_levels(levels, sensitivity):
                if not levels:
                    return []

                # 按价格排序
                sorted_levels = sorted(levels, key=lambda x: x[1])
                clusters = [[sorted_levels[0]]]

                for level in sorted_levels[1:]:
                    last_cluster = clusters[-1]
                    last_price = last_cluster[-1][1]

                    # 如果价格相近，加入同一个簇
                    if abs(level[1] - last_price) / last_price * 100 <= sensitivity:
                        last_cluster.append(level)
                    else:
                        clusters.append([level])

                # 计算每个簇的平均价格
                return [(
                    sum(x[0] for x in cluster) // len(cluster),
                    sum(x[1] for x in cluster) / len(cluster)
                ) for cluster in clusters]

            # 聚类支撑位和阻力位
            resistance_levels = cluster_levels(peaks, sensitivity)
            support_levels = cluster_levels(troughs, sensitivity)

            # 计算趋势线
            def calculate_trend_lines(points, is_resistance=True):
                if len(points) < 2:
                    return []

                trend_lines = []
                last_close = float(close[-1])

                for i in range(len(points)-1):
                    for j in range(i+1, len(points)):
                        p1, p2 = points[i], points[j]

                        # 计算斜率
                        slope = (p2[1] - p1[1]) / (p2[0] - p1[0])

                        # 延伸到当前
                        current_value = p1[1] + slope * (len(close)-1 - p1[0])

                        # 如果当前价格接近趋势线，记录该趋势线
                        if abs(current_value - last_close) / last_close * 100 <= sensitivity:
                            trend_lines.append((p1, p2, current_value))

                return trend_lines

            # 计算支撑和阻力趋势线
            resistance_lines = calculate_trend_lines(resistance_levels, True)
            support_lines = calculate_trend_lines(support_levels, False)

            # 添加水平支撑位结果
            last_close = float(close[-1])
            for level in support_levels:
                if abs(level[1] - last_close) / last_close * 100 <= sensitivity:
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem("水平支撑位")
                    )

                    position = f"{level[0]}"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    deviation = (last_close - level[1]) / level[1] * 100
                    feature = f"价格{deviation:+.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if deviation < 0:
                        suggestion = "买入"
                        color = Qt.red
                    else:
                        suggestion = "观望"
                        color = Qt.black

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 添加水平阻力位结果
            for level in resistance_levels:
                if abs(level[1] - last_close) / last_close * 100 <= sensitivity:
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem("水平阻力位")
                    )

                    position = f"{level[0]}"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    deviation = (last_close - level[1]) / level[1] * 100
                    feature = f"价格{deviation:+.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if deviation > 0:
                        suggestion = "卖出"
                        color = Qt.green
                    else:
                        suggestion = "观望"
                        color = Qt.black

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 添加趋势支撑线结果
            for p1, p2, current_value in support_lines:
                row = self.wave_table.rowCount()
                self.wave_table.insertRow(row)

                self.wave_table.setItem(
                    row, 0,
                    QTableWidgetItem("趋势支撑线")
                )

                position = f"{p1[0]}-{p2[0]}"
                self.wave_table.setItem(
                    row, 1,
                    QTableWidgetItem(position)
                )

                deviation = (last_close - current_value) / current_value * 100
                feature = f"价格{deviation:+.1f}%"
                self.wave_table.setItem(
                    row, 2,
                    QTableWidgetItem(feature)
                )

                if deviation < 0:
                    suggestion = "买入"
                    color = Qt.red
                else:
                    suggestion = "观望"
                    color = Qt.black

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(color)
                self.wave_table.setItem(row, 3, suggestion_item)

            # 添加趋势阻力线结果
            for p1, p2, current_value in resistance_lines:
                row = self.wave_table.rowCount()
                self.wave_table.insertRow(row)

                self.wave_table.setItem(
                    row, 0,
                    QTableWidgetItem("趋势阻力线")
                )

                position = f"{p1[0]}-{p2[0]}"
                self.wave_table.setItem(
                    row, 1,
                    QTableWidgetItem(position)
                )

                deviation = (last_close - current_value) / current_value * 100
                feature = f"价格{deviation:+.1f}%"
                self.wave_table.setItem(
                    row, 2,
                    QTableWidgetItem(feature)
                )

                if deviation > 0:
                    suggestion = "卖出"
                    color = Qt.green
                else:
                    suggestion = "观望"
                    color = Qt.black

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(color)
                self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            self.log_manager.log(f"分析支撑阻力位失败: {str(e)}", LogLevel.ERROR)

    def clear_wave(self):
        """清除波浪分析结果"""
        try:
            self.wave_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除波浪分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_sentiment_tab(self) -> QWidget:
        """创建市场情绪Tab，采用卡片式布局，分区展示情绪指标、时间控制、结果展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 情绪分析控制区域
        control_group = QGroupBox("市场情绪分析控制")
        control_layout = QHBoxLayout(control_group)

        # 左侧：情绪指标选择
        indicator_card = QFrame()
        indicator_card.setFrameStyle(QFrame.StyledPanel)
        indicator_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        indicator_layout = QVBoxLayout(indicator_card)
        indicator_layout.addWidget(QLabel("情绪指标"))

        self.sentiment_indicators = QListWidget()
        self.sentiment_indicators.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sentiment_indicators.setMaximumHeight(120)
        sentiment_items = ['恐慌贪婪指数', 'VIX指数', '涨跌比', '成交量比', '资金流向', '舆情指数']
        for item in sentiment_items:
            self.sentiment_indicators.addItem(item)
        indicator_layout.addWidget(self.sentiment_indicators)

        # 分析按钮
        analyze_sentiment_btn = QPushButton("开始分析")
        analyze_sentiment_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        analyze_sentiment_btn.clicked.connect(self.analyze_sentiment)

        clear_sentiment_btn = QPushButton("清除结果")
        clear_sentiment_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        clear_sentiment_btn.clicked.connect(self.clear_sentiment)

        indicator_layout.addWidget(analyze_sentiment_btn)
        indicator_layout.addWidget(clear_sentiment_btn)
        control_layout.addWidget(indicator_card, stretch=2)

        # 右侧：时间范围和参数设置
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        params_layout = QVBoxLayout(params_card)
        params_layout.addWidget(QLabel("参数设置"))

        # 时间范围
        time_range_layout = QHBoxLayout()
        time_range_layout.addWidget(QLabel("时间范围:"))
        self.sentiment_time_range = QComboBox()
        self.sentiment_time_range.addItems(['1天', '3天', '1周', '1月', '3月', '6月', '1年'])
        self.sentiment_time_range.setCurrentText('1月')
        time_range_layout.addWidget(self.sentiment_time_range)
        params_layout.addLayout(time_range_layout)

        # 敏感度
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("敏感度:"))
        self.sentiment_sensitivity = QDoubleSpinBox()
        self.sentiment_sensitivity.setRange(0.1, 2.0)
        self.sentiment_sensitivity.setSingleStep(0.1)
        self.sentiment_sensitivity.setValue(1.0)
        sensitivity_layout.addWidget(self.sentiment_sensitivity)
        params_layout.addLayout(sensitivity_layout)

        # 数据源选择
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("数据源:"))
        self.sentiment_source = QComboBox()
        self.sentiment_source.addItems(['综合数据', '交易所数据', '社交媒体', '新闻舆情'])
        source_layout.addWidget(self.sentiment_source)
        params_layout.addLayout(source_layout)

        control_layout.addWidget(params_card, stretch=2)
        layout.addWidget(control_group)

        # 情绪统计区域
        stats_group = QGroupBox("市场情绪统计")
        stats_layout = QHBoxLayout(stats_group)

        # 整体情绪指数
        overall_card = QFrame()
        overall_card.setFrameStyle(QFrame.StyledPanel)
        overall_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        overall_layout = QVBoxLayout(overall_card)
        overall_layout.addWidget(QLabel("整体情绪指数"))

        self.overall_sentiment_label = QLabel("50")
        self.overall_sentiment_label.setAlignment(Qt.AlignCenter)
        self.overall_sentiment_label.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; color: #007bff; }")
        overall_layout.addWidget(self.overall_sentiment_label)

        self.sentiment_level_label = QLabel("中性")
        self.sentiment_level_label.setAlignment(Qt.AlignCenter)
        self.sentiment_level_label.setStyleSheet("QLabel { font-size: 14px; color: #6c757d; }")
        overall_layout.addWidget(self.sentiment_level_label)

        stats_layout.addWidget(overall_card, stretch=1)

        # 恐慌贪婪指数
        fear_greed_card = QFrame()
        fear_greed_card.setFrameStyle(QFrame.StyledPanel)
        fear_greed_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        fear_greed_layout = QVBoxLayout(fear_greed_card)
        fear_greed_layout.addWidget(QLabel("恐慌贪婪指数"))

        self.fear_greed_label = QLabel("50")
        self.fear_greed_label.setAlignment(Qt.AlignCenter)
        self.fear_greed_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #ffc107; }")
        fear_greed_layout.addWidget(self.fear_greed_label)

        stats_layout.addWidget(fear_greed_card, stretch=1)

        # 市场热度
        heat_card = QFrame()
        heat_card.setFrameStyle(QFrame.StyledPanel)
        heat_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        heat_layout = QVBoxLayout(heat_card)
        heat_layout.addWidget(QLabel("市场热度"))

        self.market_heat_label = QLabel("温和")
        self.market_heat_label.setAlignment(Qt.AlignCenter)
        self.market_heat_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #28a745; }")
        heat_layout.addWidget(self.market_heat_label)

        stats_layout.addWidget(heat_card, stretch=1)

        # 投资者情绪
        investor_card = QFrame()
        investor_card.setFrameStyle(QFrame.StyledPanel)
        investor_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        investor_layout = QVBoxLayout(investor_card)
        investor_layout.addWidget(QLabel("投资者情绪"))

        self.investor_sentiment_label = QLabel("乐观")
        self.investor_sentiment_label.setAlignment(Qt.AlignCenter)
        self.investor_sentiment_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #17a2b8; }")
        investor_layout.addWidget(self.investor_sentiment_label)

        stats_layout.addWidget(investor_card, stretch=1)

        layout.addWidget(stats_group)

        # 历史数据分析区域
        history_group = QGroupBox("历史情绪分析")
        history_layout = QVBoxLayout(history_group)

        # 历史数据表格
        self.sentiment_table = QTableWidget(0, 6)
        self.sentiment_table.setHorizontalHeaderLabels(['日期', '情绪指数', '恐慌贪婪', '市场热度', '变化趋势', '建议'])
        self.sentiment_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sentiment_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 表格样式美化
        self.sentiment_table.setAlternatingRowColors(True)
        self.sentiment_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.sentiment_table.setSortingEnabled(True)

        history_layout.addWidget(self.sentiment_table)

        # 历史分析按钮
        history_btn_layout = QHBoxLayout()

        analyze_history_btn = QPushButton("分析历史数据")
        analyze_history_btn.setStyleSheet("QPushButton { background-color: #6f42c1; color: white; }")
        analyze_history_btn.clicked.connect(self.analyze_history)

        export_sentiment_format = QComboBox()
        export_sentiment_format.addItems(["Excel", "CSV", "JSON"])
        export_sentiment_btn = QPushButton("导出情绪分析")
        export_sentiment_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")

        refresh_sentiment_btn = QPushButton("刷新数据")
        refresh_sentiment_btn.clicked.connect(self.refresh_sentiment_data)
        refresh_sentiment_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")

        history_btn_layout.addWidget(analyze_history_btn)
        history_btn_layout.addWidget(QLabel("导出格式:"))
        history_btn_layout.addWidget(export_sentiment_format)
        history_btn_layout.addWidget(export_sentiment_btn)
        history_btn_layout.addWidget(refresh_sentiment_btn)
        history_btn_layout.addStretch()

        history_layout.addLayout(history_btn_layout)
        layout.addWidget(history_group)

        return tab

    def refresh_sentiment_data(self):
        """强制刷新情绪分析Tab缓存和数据，异步执行分析"""
        self.current_kdata = None
        self.analyze_sentiment()

    def analyze_sentiment(self):
        """情绪分析，自动补全K线数据，支持主图/主窗口数据同步"""
        try:
            kdata = self.current_kdata
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                pass
            kdata = self._kdata_preprocess(kdata, context="情绪分析")
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                self.log_manager.warning("无K线数据，无法进行情绪分析")
                QMessageBox.warning(self, "提示", "无K线数据，无法进行情绪分析")
                return

            # 清空结果表格
            self.sentiment_table.setRowCount(0)

            # 分析恐慌指数
            fear_greed = self.fear_greed_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("恐慌指数")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{fear_greed}")
            )

            if fear_greed <= 20:
                status = "极度恐慌"
                suggestion = "逢低买入"
                color = Qt.red
            elif fear_greed <= 40:
                status = "恐慌"
                suggestion = "可以买入"
                color = Qt.red
            elif fear_greed <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif fear_greed <= 80:
                status = "贪婪"
                suggestion = "可以卖出"
                color = Qt.green
            else:
                status = "极度贪婪"
                suggestion = "逢高卖出"
                color = Qt.green

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 分析市场强度
            strength = self.market_strength_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("市场强度")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{strength}")
            )

            if strength <= 20:
                status = "极弱"
                suggestion = "观望"
                color = Qt.black
            elif strength <= 40:
                status = "偏弱"
                suggestion = "谨慎"
                color = Qt.black
            elif strength <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif strength <= 80:
                status = "偏强"
                suggestion = "买入"
                color = Qt.red
            else:
                status = "极强"
                suggestion = "积极买入"
                color = Qt.red

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 分析资金流向
            flow = self.fund_flow_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("资金流向")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{flow:+}")
            )

            if flow <= -50:
                status = "大幅流出"
                suggestion = "观望"
                color = Qt.black
            elif flow < 0:
                status = "小幅流出"
                suggestion = "谨慎"
                color = Qt.black
            elif flow == 0:
                status = "持平"
                suggestion = "观望"
                color = Qt.black
            elif flow < 50:
                status = "小幅流入"
                suggestion = "买入"
                color = Qt.red
            else:
                status = "大幅流入"
                suggestion = "积极买入"
                color = Qt.red

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 计算综合情绪
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("综合情绪")
            )

            # 计算综合得分
            score = (
                (100 - fear_greed) * 0.4 +  # 恐慌指数反向计分
                strength * 0.3 +  # 市场强度
                (flow + 100) / 2 * 0.3  # 资金流向归一化
            )

            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{score:.1f}")
            )

            if score <= 20:
                status = "极度悲观"
                suggestion = "逢低买入"
                color = Qt.red
            elif score <= 40:
                status = "偏悲观"
                suggestion = "可以买入"
                color = Qt.red
            elif score <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif score <= 80:
                status = "偏乐观"
                suggestion = "可以卖出"
                color = Qt.green
            else:
                status = "极度乐观"
                suggestion = "逢高卖出"
                color = Qt.green

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 调整列宽
            self.sentiment_table.resizeColumnsToContents()

        except Exception as e:
            self.log_manager.error(f"情绪分析异常: {str(e)}")
            QMessageBox.warning(self, "错误", f"情绪分析异常: {str(e)}")

    def analyze_history(self):
        """分析历史趋势"""
        try:
            # 修复DataFrame布尔判断错误
            if self.current_kdata is None or (hasattr(self.current_kdata, 'empty') and self.current_kdata.empty):
                return

            # 清空历史趋势表格
            self.history_table.setRowCount(0)

            # 获取历史周期
            period_text = self.history_period.currentText()
            period = int(period_text.replace("日", ""))

            # 获取历史数据
            fear_greed_history = []
            strength_history = []
            fund_flow_history = []
            north_flow_history = []

            # 模拟生成历史数据
            for i in range(period):
                fear_greed_history.append(
                    max(0, min(100, self.fear_greed_spin.value() +
                               np.random.normal(0, 10)))
                )
                strength_history.append(
                    max(0, min(100, self.market_strength_spin.value() +
                               np.random.normal(0, 10)))
                )
                fund_flow_history.append(
                    max(-100, min(100, self.fund_flow_spin.value() +
                                  np.random.normal(0, 20)))
                )
                north_flow_history.append(
                    max(-100, min(100, self.north_flow_spin.value() +
                                  np.random.normal(0, 20)))
                )

            # 分析恐慌指数历史
            self.add_history_row(
                "恐慌指数",
                fear_greed_history,
                lambda x: "上升" if x > 0 else "下降" if x < 0 else "持平"
            )

            # 分析市场强度历史
            self.add_history_row(
                "市场强度",
                strength_history,
                lambda x: "增强" if x > 0 else "减弱" if x < 0 else "持平"
            )

            # 分析资金流向历史
            self.add_history_row(
                "资金流向",
                fund_flow_history,
                lambda x: "净流入" if x > 0 else "净流出" if x < 0 else "持平"
            )

            # 分析北向资金历史
            self.add_history_row(
                "北向资金",
                north_flow_history,
                lambda x: "净流入" if x > 0 else "净流出" if x < 0 else "持平"
            )

            # 调整列宽
            self.history_table.resizeColumnsToContents()

        except Exception as e:
            self.log_manager.log(f"分析历史趋势失败: {str(e)}", LogLevel.ERROR)

    def add_history_row(self, name: str, data: List[float],
                        trend_func: Callable[[float], str]):
        """添加历史趋势行

        Args:
            name: 指标名称
            data: 历史数据
            trend_func: 趋势判断函数
        """
        try:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            # 添加指标名称
            self.history_table.setItem(
                row, 0,
                QTableWidgetItem(name)
            )

            # 添加最高值
            max_value = max(data)
            self.history_table.setItem(
                row, 1,
                QTableWidgetItem(f"{max_value:.1f}")
            )

            # 添加最低值
            min_value = min(data)
            self.history_table.setItem(
                row, 2,
                QTableWidgetItem(f"{min_value:.1f}")
            )

            # 添加均值
            mean_value = sum(data) / len(data)
            self.history_table.setItem(
                row, 3,
                QTableWidgetItem(f"{mean_value:.1f}")
            )

            # 计算趋势
            trend = trend_func(data[-1] - data[0])
            trend_item = QTableWidgetItem(trend)

            # 设置趋势颜色
            if "上升" in trend or "增强" in trend or "净流入" in trend:
                trend_item.setForeground(Qt.red)
            elif "下降" in trend or "减弱" in trend or "净流出" in trend:
                trend_item.setForeground(Qt.green)
            else:
                trend_item.setForeground(Qt.black)

            self.history_table.setItem(row, 4, trend_item)

        except Exception as e:
            self.log_manager.log(f"添加历史趋势行失败: {str(e)}", LogLevel.ERROR)
            raise

    def clear_sentiment(self):
        """清除市场情绪分析结果"""
        try:
            self.sentiment_table.setRowCount(0)
            self.history_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除市场情绪分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_sector_flow_tab(self) -> QWidget:
        """创建板块资金流向Tab，采用卡片式布局，分区展示板块选择、流向类型、结果展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 板块资金流向控制区域
        control_group = QGroupBox("板块资金流向分析控制")
        control_layout = QHBoxLayout(control_group)

        # 左侧：板块选择
        sector_card = QFrame()
        sector_card.setFrameStyle(QFrame.StyledPanel)
        sector_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        sector_layout = QVBoxLayout(sector_card)
        sector_layout.addWidget(QLabel("板块选择"))

        self.sector_list = QListWidget()
        self.sector_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sector_list.setMaximumHeight(120)
        sector_items = ['科技股', '金融股', '医药股', '消费股', '地产股', '能源股', '工业股', '材料股']
        for item in sector_items:
            self.sector_list.addItem(item)
        sector_layout.addWidget(self.sector_list)

        # 分析按钮
        analyze_flow_btn = QPushButton("开始分析")
        analyze_flow_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        analyze_flow_btn.clicked.connect(self.analyze_sector_flow)

        clear_flow_btn = QPushButton("清除结果")
        clear_flow_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        clear_flow_btn.clicked.connect(self.clear_sector_flow)

        sector_layout.addWidget(analyze_flow_btn)
        sector_layout.addWidget(clear_flow_btn)
        control_layout.addWidget(sector_card, stretch=2)

        # 右侧：流向类型和参数设置
        params_card = QFrame()
        params_card.setFrameStyle(QFrame.StyledPanel)
        params_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        params_layout = QVBoxLayout(params_card)
        params_layout.addWidget(QLabel("参数设置"))

        # 资金流向类型
        flow_type_layout = QHBoxLayout()
        flow_type_layout.addWidget(QLabel("流向类型:"))
        self.flow_type_combo = QComboBox()
        self.flow_type_combo.addItems(['主力资金', '散户资金', '机构资金', '外资流向', '综合流向'])
        flow_type_layout.addWidget(self.flow_type_combo)
        params_layout.addLayout(flow_type_layout)

        # 时间周期
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("时间周期:"))
        self.flow_period_combo = QComboBox()
        self.flow_period_combo.addItems(['实时', '日线', '周线', '月线'])
        period_layout.addWidget(self.flow_period_combo)
        params_layout.addLayout(period_layout)

        # 金额阈值
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("金额阈值(万):"))
        self.flow_threshold_spin = QSpinBox()
        self.flow_threshold_spin.setRange(100, 100000)
        self.flow_threshold_spin.setValue(1000)
        self.flow_threshold_spin.setSuffix(" 万")
        threshold_layout.addWidget(self.flow_threshold_spin)
        params_layout.addLayout(threshold_layout)

        control_layout.addWidget(params_card, stretch=2)
        layout.addWidget(control_group)

        # 资金流向统计区域
        stats_group = QGroupBox("资金流向统计")
        stats_layout = QHBoxLayout(stats_group)

        # 总流入
        inflow_card = QFrame()
        inflow_card.setFrameStyle(QFrame.StyledPanel)
        inflow_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        inflow_layout = QVBoxLayout(inflow_card)
        inflow_layout.addWidget(QLabel("总流入"))

        self.total_inflow_label = QLabel("0.00亿")
        self.total_inflow_label.setAlignment(Qt.AlignCenter)
        self.total_inflow_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")
        inflow_layout.addWidget(self.total_inflow_label)

        stats_layout.addWidget(inflow_card, stretch=1)

        # 总流出
        outflow_card = QFrame()
        outflow_card.setFrameStyle(QFrame.StyledPanel)
        outflow_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        outflow_layout = QVBoxLayout(outflow_card)
        outflow_layout.addWidget(QLabel("总流出"))

        self.total_outflow_label = QLabel("0.00亿")
        self.total_outflow_label.setAlignment(Qt.AlignCenter)
        self.total_outflow_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #dc3545; }")
        outflow_layout.addWidget(self.total_outflow_label)

        stats_layout.addWidget(outflow_card, stretch=1)

        # 净流入
        net_flow_card = QFrame()
        net_flow_card.setFrameStyle(QFrame.StyledPanel)
        net_flow_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        net_flow_layout = QVBoxLayout(net_flow_card)
        net_flow_layout.addWidget(QLabel("净流入"))

        self.net_flow_label = QLabel("0.00亿")
        self.net_flow_label.setAlignment(Qt.AlignCenter)
        self.net_flow_label.setStyleSheet("QLabel { font-size: 20px; font-weight: bold; color: #007bff; }")
        net_flow_layout.addWidget(self.net_flow_label)

        stats_layout.addWidget(net_flow_card, stretch=1)

        # 活跃度
        activity_card = QFrame()
        activity_card.setFrameStyle(QFrame.StyledPanel)
        activity_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.addWidget(QLabel("板块活跃度"))

        self.activity_label = QLabel("中等")
        self.activity_label.setAlignment(Qt.AlignCenter)
        self.activity_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; color: #ffc107; }")
        activity_layout.addWidget(self.activity_label)

        stats_layout.addWidget(activity_card, stretch=1)

        layout.addWidget(stats_group)

        # 板块资金流向详情区域
        details_group = QGroupBox("板块资金流向详情")
        details_layout = QVBoxLayout(details_group)

        # 详情表格
        self.sector_flow_table = QTableWidget(0, 7)
        self.sector_flow_table.setHorizontalHeaderLabels(['板块', '流入(亿)', '流出(亿)', '净流入(亿)', '涨跌幅', '活跃度', '建议'])
        self.sector_flow_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sector_flow_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 表格样式美化
        self.sector_flow_table.setAlternatingRowColors(True)
        self.sector_flow_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #495057;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.sector_flow_table.setSortingEnabled(True)

        details_layout.addWidget(self.sector_flow_table)

        # 操作按钮区域
        bottom_layout = QHBoxLayout()

        # 导出功能
        export_flow_format = QComboBox()
        export_flow_format.addItems(["Excel", "CSV", "JSON"])
        export_flow_btn = QPushButton("导出资金流向")
        export_flow_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; }")
        export_flow_btn.clicked.connect(self.export_fund_flow)

        # 刷新功能
        refresh_flow_btn = QPushButton("刷新数据")
        refresh_flow_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; }")

        # 高级分析
        advanced_flow_btn = QPushButton("高级流向分析")
        advanced_flow_btn.setStyleSheet("QPushButton { background-color: #6f42c1; color: white; }")

        # 实时监控
        monitor_btn = QPushButton("实时监控")
        monitor_btn.setStyleSheet("QPushButton { background-color: #fd7e14; color: white; }")

        bottom_layout.addWidget(QLabel("导出格式:"))
        bottom_layout.addWidget(export_flow_format)
        bottom_layout.addWidget(export_flow_btn)
        bottom_layout.addWidget(refresh_flow_btn)
        bottom_layout.addWidget(advanced_flow_btn)
        bottom_layout.addWidget(monitor_btn)
        bottom_layout.addStretch()

        details_layout.addLayout(bottom_layout)
        layout.addWidget(details_group)

        return tab

    def analyze_sector_flow(self):
        """分析板块资金流向，统一调用后端接口，支持多源、历史、极值高亮"""
        try:
            from core.trading_system import trading_system
            fund_flow = trading_system.get_fund_flow()
            # 行业资金流
            industry = fund_flow.get('industry_flow', [])
            self.industry_flow_table.setRowCount(0)
            for i, row in enumerate(industry):
                self.industry_flow_table.insertRow(i)
                self.industry_flow_table.setItem(i, 0, QTableWidgetItem(str(row.get('行业', ''))))
                main_item = QTableWidgetItem(str(row.get('主力净流入', '')))
                main_item.setForeground(QColor("red" if float(row.get('主力净流入', 0)) > 0 else "green"))
                self.industry_flow_table.setItem(i, 1, main_item)
                self.industry_flow_table.setItem(i, 2, QTableWidgetItem(str(row.get('超大单净流入', ''))))
                self.industry_flow_table.setItem(i, 3, QTableWidgetItem(str(row.get('大单净流入', ''))))
                self.industry_flow_table.setItem(i, 4, QTableWidgetItem(str(row.get('中单净流入', ''))))
            # 概念资金流
            concept = fund_flow.get('concept_flow', [])
            self.concept_flow_table.setRowCount(0)
            for i, row in enumerate(concept):
                self.concept_flow_table.insertRow(i)
                self.concept_flow_table.setItem(i, 0, QTableWidgetItem(str(row.get('概念', ''))))
                main_item = QTableWidgetItem(str(row.get('主力净流入', '')))
                main_item.setForeground(QColor("red" if float(row.get('主力净流入', 0)) > 0 else "green"))
                self.concept_flow_table.setItem(i, 1, main_item)
                self.concept_flow_table.setItem(i, 2, QTableWidgetItem(str(row.get('超大单净流入', ''))))
                self.concept_flow_table.setItem(i, 3, QTableWidgetItem(str(row.get('大单净流入', ''))))
                self.concept_flow_table.setItem(i, 4, QTableWidgetItem(str(row.get('中单净流入', ''))))
            # 北向资金
            north = fund_flow.get('north_flow', [])
            self.north_flow_table.setRowCount(0)
            for i, row in enumerate(north):
                self.north_flow_table.insertRow(i)
                self.north_flow_table.setItem(i, 0, QTableWidgetItem(str(row.get('时间', ''))))
                self.north_flow_table.setItem(i, 1, QTableWidgetItem(str(row.get('沪股通', ''))))
                self.north_flow_table.setItem(i, 2, QTableWidgetItem(str(row.get('深股通', ''))))
                self.north_flow_table.setItem(i, 3, QTableWidgetItem(str(row.get('合计', ''))))
            # 极值高亮、历史对比等可扩展
        except Exception as e:
            self.log_manager.log(f"板块资金流向分析失败: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "错误", f"板块资金流向分析失败: {str(e)}")

    def export_fund_flow(self):
        """一键导出全部资金流数据"""
        try:
            import pandas as pd
            file_path, _ = QFileDialog.getSaveFileName(self, "导出资金流数据", "资金流数据", "Excel Files (*.xlsx);;CSV Files (*.csv)")
            if not file_path:
                return
            # 导出行业、概念、北向资金流
            industry_data = [[self.industry_flow_table.item(i, j).text() for j in range(
                self.industry_flow_table.columnCount())] for i in range(self.industry_flow_table.rowCount())]
            concept_data = [[self.concept_flow_table.item(i, j).text() for j in range(
                self.concept_flow_table.columnCount())] for i in range(self.concept_flow_table.rowCount())]
            north_data = [[self.north_flow_table.item(i, j).text() for j in range(self.north_flow_table.columnCount())]
                          for i in range(self.north_flow_table.rowCount())]
            with pd.ExcelWriter(file_path) as writer:
                pd.DataFrame(industry_data, columns=["行业", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"]).to_excel(writer, sheet_name="行业资金流", index=False)
                pd.DataFrame(concept_data, columns=["概念", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"]).to_excel(writer, sheet_name="概念资金流", index=False)
                pd.DataFrame(north_data, columns=["时间", "沪股通", "深股通", "合计"]).to_excel(writer, sheet_name="北向资金", index=False)
            QMessageBox.information(self, "导出成功", "资金流数据已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出资金流数据失败: {str(e)}")

    def clear_sector_flow(self):
        """清除板块资金流向分析结果"""
        try:
            self.industry_flow_table.setRowCount(0)
            self.concept_flow_table.setRowCount(0)
            self.north_flow_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除板块资金流向分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_hotspot_tab(self) -> QWidget:
        """创建热点分析标签页，热点板块、主题机会、热点轮动三表格横向并列，板块资金流向三表格也横向并列"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # --- 热点三表格横向并列 ---
            row_layout = QHBoxLayout()
            # 热点板块
            hotspot_group = QGroupBox("热点板块")
            hotspot_layout = QVBoxLayout()
            self.hotspot_table = QTableWidget()
            self.hotspot_table.setColumnCount(7)
            self.hotspot_table.setHorizontalHeaderLabels([
                "板块名称", "涨跌幅", "领涨股", "涨跌幅", "成交额", "换手率", "板块强度"
            ])
            self.hotspot_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            hotspot_layout.addWidget(self.hotspot_table)
            hotspot_group.setLayout(hotspot_layout)
            row_layout.addWidget(hotspot_group, 1)
            row_layout.addSpacing(20)
            # 主题机会
            theme_group = QGroupBox("主题机会")
            theme_layout = QVBoxLayout()
            self.theme_table = QTableWidget()
            self.theme_table.setColumnCount(6)
            self.theme_table.setHorizontalHeaderLabels([
                "主题名称", "相关股票数", "平均涨跌幅", "资金净流入", "热度指数", "轮动指数"
            ])
            self.theme_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            theme_layout.addWidget(self.theme_table)
            theme_group.setLayout(theme_layout)
            row_layout.addWidget(theme_group, 1)
            row_layout.addSpacing(20)
            # 热点轮动
            rotation_group = QGroupBox("热点轮动")
            rotation_layout = QVBoxLayout()
            self.rotation_table = QTableWidget()
            self.rotation_table.setColumnCount(5)
            self.rotation_table.setHorizontalHeaderLabels([
                "轮动板块", "上升趋势", "资金流入", "持续天数", "轮动建议"
            ])
            self.rotation_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            rotation_layout.addWidget(self.rotation_table)
            rotation_group.setLayout(rotation_layout)
            row_layout.addWidget(rotation_group, 1)
            layout.addLayout(row_layout)

            # --- 板块资金流向三表格横向并列 ---
            sector_row_layout = QHBoxLayout()
            # 行业资金流向
            industry_group = QGroupBox("行业资金流向")
            industry_layout = QVBoxLayout()
            self.industry_flow_table = QTableWidget()
            self.industry_flow_table.setColumnCount(5)
            self.industry_flow_table.setHorizontalHeaderLabels([
                "行业", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            industry_layout.addWidget(self.industry_flow_table)
            industry_group.setLayout(industry_layout)
            sector_row_layout.addWidget(industry_group, 1)
            sector_row_layout.addSpacing(20)
            # 概念资金流向
            concept_group = QGroupBox("概念资金流向")
            concept_layout = QVBoxLayout()
            self.concept_flow_table = QTableWidget()
            self.concept_flow_table.setColumnCount(5)
            self.concept_flow_table.setHorizontalHeaderLabels([
                "概念", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            concept_layout.addWidget(self.concept_flow_table)
            concept_group.setLayout(concept_layout)
            sector_row_layout.addWidget(concept_group, 1)
            sector_row_layout.addSpacing(20)
            # 北向资金
            north_group = QGroupBox("北向资金")
            north_layout = QVBoxLayout()
            self.north_flow_table = QTableWidget()
            self.north_flow_table.setColumnCount(4)
            self.north_flow_table.setHorizontalHeaderLabels([
                "时间", "沪股通", "深股通", "合计"
            ])
            north_layout.addWidget(self.north_flow_table)
            north_group.setLayout(north_layout)
            sector_row_layout.addWidget(north_group, 1)
            layout.addLayout(sector_row_layout)

            # 龙头股
            leader_group = QGroupBox("龙头股")
            leader_layout = QVBoxLayout()
            self.leader_table = QTableWidget()
            self.leader_table.setColumnCount(15)
            self.leader_table.setHorizontalHeaderLabels([
                "股票名称", "股票代码", "所属板块", "是否ST", "市值(亿)", "涨跌幅", "近5日涨跌幅", "成交额(亿)", "换手率(%)", "振幅(%)", "量比", "主力净流入(亿)", "主力净流入占比(%)", "涨停状态", "资金流向趋势(5日)", "综合得分"
            ])
            self.leader_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            leader_layout.addWidget(self.leader_table)
            leader_group.setLayout(leader_layout)
            layout.addWidget(leader_group)

            # 按钮区和进度条
            button_layout = QHBoxLayout()
            self.rotation_button = QPushButton("分析轮动")
            self.rotation_button.clicked.connect(self.toggle_rotation_analysis)
            button_layout.addWidget(self.rotation_button)
            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(
                lambda: self.run_button_analysis_async(clear_button, self.clear_hotspot))
            button_layout.addWidget(clear_button)
            layout.addLayout(button_layout)
            return widget
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"创建热点分析标签页失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"创建热点分析标签页失败: {str(e)}")
            raise

    def toggle_rotation_analysis(self):
        """
        合并分析轮动与中断分析按钮逻辑。
        """
        if self.rotation_button.text() == "分析轮动":
            self._rotation_interrupted = False
            self.rotation_button.setText("中断分析")
            self.start_all_hotspot_analysis()
        else:
            self.interrupt_rotation_analysis()
            self.rotation_button.setText("分析轮动")

    def start_all_hotspot_analysis(self):
        """
        合并所有热点分析功能，点击分析轮动后并发执行所有分析，动态渲染表格，轮动分析用QThread后台执行，避免Qt定时器错误和主界面卡顿。
        """
        if hasattr(self, 'rotation_worker') and self.rotation_worker and self.rotation_worker.isRunning():
            return
        self.rotation_button.setEnabled(False)
        self.rotation_button.setText("分析轮动")

        # 优化：将run_others放到QThread中执行，彻底避免主线程卡顿
        from PyQt5.QtCore import QThread, pyqtSignal
        import types

        class OthersWorker(QThread):
            error = pyqtSignal(str)

            def __init__(self, widget):
                super().__init__()
                self.widget = widget

            def run(self):
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=6) as executor:
                        futures = []
                        futures.append(executor.submit(
                            self.widget.analyze_hotspot_sectors))
                        futures.append(executor.submit(
                            self.widget.analyze_theme_opportunities))
                        futures.append(executor.submit(
                            self.widget.analyze_leading_stocks))
                        futures.append(executor.submit(
                            self.widget.analyze_industry_flow))
                        futures.append(executor.submit(
                            self.widget.analyze_concept_flow))
                        futures.append(executor.submit(
                            self.widget.analyze_north_flow))
                        for f in futures:
                            try:
                                f.result()
                            except Exception as e:
                                if hasattr(self.widget, 'log_manager'):
                                    self.widget.log_manager.log(
                                        f"分析任务异常: {str(e)}", LogLevel.ERROR)
                except Exception as e:
                    self.error.emit(str(e))

        self.others_worker = OthersWorker(self)
        self.others_worker.error.connect(
            lambda msg: self.log_manager.log(f"分析任务异常: {msg}", LogLevel.ERROR))
        self.others_worker.finished.connect(self._start_rotation_worker)
        self.others_worker.start()

    def _start_rotation_worker(self):
        self.rotation_worker = RotationWorker(self)
        self._connect_rotation_worker_signals()
        self.rotation_worker.finished.connect(self._on_rotation_finished)
        self.rotation_worker.error.connect(self._on_rotation_error)
        self.rotation_worker.start()

    def interrupt_rotation_analysis(self):
        """
        中断热点轮动分析
        """
        self._rotation_interrupted = True
        self.log_manager.info("用户请求中断热点轮动分析")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_status("热点轮动分析已中断")
            status_bar.set_progress(0)
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))
        # 按钮状态恢复
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")

    def _on_rotation_finished(self):
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_progress(100)
            status_bar.set_status("热点轮动分析完成")
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))

    def _on_rotation_error(self, msg):
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_progress_error("热点轮动分析失败")
            status_bar.set_status(msg)
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))
        if hasattr(self, 'log_manager'):
            self.log_manager.error(f"热点轮动分析异常: {msg}")

    def analyze_hotspot(self):
        """分析市场热点"""
        try:
            # 分析热点板块
            self.analyze_hotspot_sectors()

            # 分析主题机会
            self.analyze_theme_opportunities()

            # 分析龙头股
            self.analyze_leading_stocks()

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"分析市场热点失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析市场热点失败: {str(e)}")

    def analyze_hotspot_sectors(self):
        """多线程分析热点板块"""
        try:
            self.hotspot_table.setRowCount(0)
            sectors = []
            start_time = time.time()
            from concurrent.futures import ThreadPoolExecutor, as_completed

            block_list = [block for block in sm.get_block_list() if not isinstance(
                block, str) and hasattr(block, 'get_stock_list') and block.get_stock_list()]

            def analyze_block(block):
                try:
                    stocks = block.get_stock_list()
                    total_change = 0
                    total_amount = 0
                    total_turnover = 0
                    up_count = 0
                    leading_stock = None
                    leading_change = -100
                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-5))
                        if len(kdata) < 5:
                            continue
                        close = float(kdata[-1].close)
                        pre_close = float(kdata[-2].close)
                        change = (close - pre_close) / pre_close * 100
                        if change > 0:
                            up_count += 1
                        total_change += change
                        total_amount += float(kdata[-1].amount)
                        turnover = self._get_turnover(kdata, stock)
                        total_turnover += turnover
                        if change > leading_change:
                            leading_stock = stock
                            leading_change = change
                    if len(stocks) > 0:
                        strength = (
                            up_count / len(stocks) * 0.3 +
                            abs(total_change / len(stocks)) * 0.4 +
                            (total_turnover / len(stocks)) * 0.3
                        )
                        return {
                            'name': block.name,
                            'change': total_change / len(stocks),
                            'leading_stock': leading_stock,
                            'leading_change': leading_change,
                            'amount': total_amount / 100000000,
                            'turnover': total_turnover / len(stocks),
                            'strength': strength
                        }
                except Exception as e:
                    if hasattr(self, 'log_manager'):
                        self.log_manager.log(
                            f"板块 {getattr(block, 'name', str(block))} 统计失败: {str(e)}", LogLevel.ERROR)
                return None

            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_block = {executor.submit(
                    analyze_block, block): block for block in block_list}
                for future in as_completed(future_to_block):
                    res = future.result()
                    if res:
                        sectors.append(res)

            sectors.sort(key=lambda x: x['strength'], reverse=True)
            self.hotspot_table.setRowCount(len(sectors) if sectors else 1)
            if not sectors:
                for col in range(self.hotspot_table.columnCount()):
                    self.hotspot_table.setItem(0, col, QTableWidgetItem("无数据"))
            else:
                for i, sector in enumerate(sectors):
                    self.hotspot_table.setItem(
                        i, 0, QTableWidgetItem(sector['name']))
                    change_item = QTableWidgetItem(f"{sector['change']:+.2f}%")
                    change_item.setForeground(
                        QColor("red" if sector['change'] > 0 else "green"))
                    self.hotspot_table.setItem(i, 1, change_item)
                    if sector['leading_stock']:
                        self.hotspot_table.setItem(
                            i, 2, QTableWidgetItem(sector['leading_stock'].name))
                        leading_change_item = QTableWidgetItem(
                            f"{sector['leading_change']:+.2f}%")
                        leading_change_item.setForeground(
                            QColor("red" if sector['leading_change'] > 0 else "green"))
                        self.hotspot_table.setItem(i, 3, leading_change_item)
                    self.hotspot_table.setItem(
                        i, 4, QTableWidgetItem(f"{sector['amount']:.2f}"))
                    self.hotspot_table.setItem(
                        i, 5, QTableWidgetItem(f"{sector['turnover']:.2f}%"))
                    strength_item = QTableWidgetItem(
                        f"{sector['strength']:.2f}")
                    if sector['strength'] >= 80:
                        strength_item.setForeground(QColor("red"))
                    elif sector['strength'] >= 50:
                        strength_item.setForeground(QColor("orange"))
                    else:
                        strength_item.setForeground(QColor("green"))
                    self.hotspot_table.setItem(i, 6, strength_item)
            self.hotspot_table.resizeColumnsToContents()
            self.log_manager.log(
                f"热点板块分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.log(f"分析热点板块失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析热点板块失败: {str(e)}")

    def analyze_theme_opportunities(self):
        """分析主题机会（修复表格数据为空/列数不一致/健壮性问题）"""
        try:
            self.theme_table.setRowCount(0)
            start_time = time.time()
            themes = []
            for block in sm.get_block_list():
                block_type = getattr(block, 'type', None) or getattr(
                    block, 'category', None) or getattr(block, 'block_type', None)
                if block_type != "概念":
                    continue
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue
                    total_change = 0
                    total_flow = 0
                    stock_count = len(stocks)
                    valid_count = 0
                    for stock in stocks:
                        try:
                            kdata = stock.get_kdata(Query(-2))
                            if len(kdata) < 2:
                                continue
                            close = float(getattr(kdata[-1], 'close', 0) or 0)
                            pre_close = float(
                                getattr(kdata[-2], 'close', 0) or 0)
                            if pre_close == 0:
                                continue
                            change = (close - pre_close) / pre_close * 100
                            total_change += change
                            volume = float(
                                getattr(kdata[-1], 'volume', 0) or 0)
                            amount = float(
                                getattr(kdata[-1], 'amount', 0) or 0)
                            if volume > 0:
                                avg_price = amount / volume
                                if avg_price > float(getattr(kdata[-1], 'open', 0) or 0):
                                    total_flow += amount
                                else:
                                    total_flow -= amount
                            valid_count += 1
                        except Exception as e:
                            self.log_manager.log(
                                f"主题{block.name}单只股票异常: {str(e)}", LogLevel.WARNING)
                            continue
                    if valid_count == 0:
                        continue
                    heat_index = (
                        abs(total_change / valid_count) * 0.4 +
                        abs(total_flow) / 100000000 * 0.3 +
                        valid_count * 0.3
                    )
                    themes.append({
                        'name': getattr(block, 'name', '-') or '-',
                        'stock_count': valid_count,
                        'avg_change': total_change / valid_count if valid_count else 0,
                        'net_flow': total_flow / 100000000 if valid_count else 0,
                        'heat_index': heat_index,
                        'rotation_index': '-'  # 轮动指数暂无，预留
                    })
                except Exception as e:
                    self.log_manager.log(
                        f"计算主题 {getattr(block, 'name', '-') or '-'} 统计失败: {str(e)}", LogLevel.ERROR)
                    continue
            themes.sort(key=lambda x: x['heat_index'], reverse=True)
            if not themes:
                self.theme_table.setRowCount(1)
                for col in range(6):
                    self.theme_table.setItem(0, col, QTableWidgetItem("无数据"))
            else:
                self.theme_table.setRowCount(len(themes))
                for i, theme in enumerate(themes):
                    self.theme_table.setItem(
                        i, 0, QTableWidgetItem(str(theme['name'])))
                    self.theme_table.setItem(
                        i, 1, QTableWidgetItem(str(theme['stock_count'])))
                    change_item = QTableWidgetItem(
                        f"{theme['avg_change']:+.2f}%")
                    change_item.setForeground(
                        QColor("red") if theme['avg_change'] > 0 else QColor("green"))
                    self.theme_table.setItem(i, 2, change_item)
                    flow_item = QTableWidgetItem(f"{theme['net_flow']:+.2f}")
                    flow_item.setForeground(
                        QColor("red") if theme['net_flow'] > 0 else QColor("green"))
                    self.theme_table.setItem(i, 3, flow_item)
                    self.theme_table.setItem(
                        i, 4, QTableWidgetItem(f"{theme['heat_index']:.2f}"))
                    self.theme_table.setItem(i, 5, QTableWidgetItem(
                        str(theme.get('rotation_index', '-'))))
            self.theme_table.resizeColumnsToContents()
            self.log_manager.log(
                f"主题机会分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            self.log_manager.log(f"分析主题机会失败: {str(e)}", LogLevel.ERROR)

    def analyze_leading_stocks(self):
        """分析龙头股，合并相同股票的所属板块为一行用/分割，修复部分数据为空问题"""
        try:
            # 清空龙头股表格
            self.leader_table.setRowCount(0)
            start_time = time.time()
            # 获取所有股票的统计数据
            leaders_dict = {}
            for block in sm.get_block_list():
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue
                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-6))  # 取近6日，便于5日涨跌幅
                        if len(kdata) < 6:
                            continue
                        try:
                            name = getattr(stock, 'name', '-') or '-'
                            code = getattr(stock, 'code', '-') or '-'
                            block_name = getattr(block, 'name', '-') or '-'
                            is_st = 'ST' in name.upper() or getattr(stock, 'is_st', False)
                            close = float(getattr(kdata[-1], 'close', 0) or 0)
                            pre_close = float(
                                getattr(kdata[-2], 'close', 0) or 0)
                            change = (close - pre_close) / \
                                pre_close * 100 if pre_close else 0
                            # 近5日涨跌幅
                            close_5 = float(
                                getattr(kdata[-6], 'close', 0) or 0)
                            change_5 = (close - close_5) / \
                                close_5 * 100 if close_5 else 0
                            # 成交额
                            amount = float(
                                getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                            # 换手率
                            turnover = self._get_turnover(kdata, stock)
                            # 市值
                            circulating_shares = getattr(
                                stock, 'circulating_shares', None)
                            market_cap = close * circulating_shares / 1e8 if circulating_shares else '-'
                            # 振幅
                            high = float(getattr(kdata[-1], 'high', 0) or 0)
                            low = float(getattr(kdata[-1], 'low', 0) or 0)
                            amplitude = (high - low) / pre_close * \
                                100 if pre_close else 0
                            # 量比
                            volume_ratio = getattr(
                                kdata[-1], 'volume_ratio', '-')
                            if isinstance(volume_ratio, float):
                                volume_ratio = f"{volume_ratio:.2f}"
                            # 主力净流入
                            volume = float(
                                getattr(kdata[-1], 'volume', 0) or 0)
                            main_flow = 0
                            if volume > 0:
                                avg_price = float(
                                    getattr(kdata[-1], 'amount', 0) or 0) / volume
                                if avg_price > float(getattr(kdata[-1], 'open', 0) or 0):
                                    main_flow = float(
                                        getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                                else:
                                    main_flow = - \
                                        float(
                                            getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                            # 主力净流入占比
                            main_flow_ratio = (
                                main_flow / amount * 100) if amount else '-'
                            if isinstance(main_flow_ratio, float):
                                main_flow_ratio = f"{main_flow_ratio:.2f}"
                            # 涨停状态
                            high_limit = getattr(kdata[-1], 'high_limit', None)
                            is_limit_up = (
                                close >= high_limit) if high_limit else '-'
                            # 资金流向趋势（近5日主力净流入为正天数）
                            flow_trend = 0
                            for i in range(-5, 0):
                                v = float(getattr(kdata[i], 'volume', 0) or 0)
                                if v > 0:
                                    avg_p = float(
                                        getattr(kdata[i], 'amount', 0) or 0) / v
                                    if avg_p > float(getattr(kdata[i], 'open', 0) or 0):
                                        flow_trend += 1
                            # 综合得分
                            score = (
                                abs(change) * 0.2 +
                                (amount if amount != '-' else 0) * 0.15 +
                                (turnover if turnover != '-' else 0) * 0.1 +
                                (abs(main_flow) if main_flow != '-' else 0) * 0.1 +
                                (abs(change_5) if change_5 != '-' else 0) * 0.15 +
                                (abs(amplitude) if amplitude != '-' else 0) * 0.1 +
                                (flow_trend if flow_trend != '-' else 0) * 0.1 +
                                (market_cap if market_cap != '-' else 0) * 0.1
                            )
                            # 合并相同股票代码的板块
                            if code not in leaders_dict:
                                leaders_dict[code] = {
                                    'name': name,
                                    'code': code,
                                    'blocks': set([block_name]),
                                    'is_st': '是' if is_st else '否',
                                    'market_cap': f"{market_cap:.2f}" if isinstance(market_cap, float) else '-',
                                    'change': change,
                                    'change_5': change_5,
                                    'amount': amount,
                                    'turnover': turnover,
                                    'amplitude': amplitude,
                                    'volume_ratio': volume_ratio,
                                    'main_flow': main_flow,
                                    'main_flow_ratio': main_flow_ratio,
                                    'is_limit_up': '涨停' if is_limit_up is True else ('-' if is_limit_up == '-' else '否'),
                                    'flow_trend': flow_trend,
                                    'score': score
                                }
                            else:
                                leaders_dict[code]['blocks'].add(block_name)
                        except Exception as e:
                            if hasattr(self, 'log_manager') and self.log_manager:
                                self.log_manager.log(
                                    f"单只股票统计失败: {str(e)}", LogLevel.ERROR)
                            continue
                except Exception as e:
                    if hasattr(self, 'log_manager') and self.log_manager:
                        self.log_manager.log(
                            f"计算股票统计失败: {str(e)}", LogLevel.ERROR)
                    continue
            # 按综合得分排序
            leaders = list(leaders_dict.values())
            leaders.sort(key=lambda x: x['score'], reverse=True)
            # 只保留前30个龙头股
            leaders = leaders[:30]
            # 更新表格
            self.leader_table.setRowCount(len(leaders))
            for i, leader in enumerate(leaders):
                self.leader_table.setItem(
                    i, 0, QTableWidgetItem(leader['name']))
                self.leader_table.setItem(
                    i, 1, QTableWidgetItem(leader['code']))
                # 合并板块名
                block_str = '/'.join(sorted(leader['blocks']))
                self.leader_table.setItem(i, 2, QTableWidgetItem(block_str))
                self.leader_table.setItem(
                    i, 3, QTableWidgetItem(leader['is_st']))
                self.leader_table.setItem(
                    i, 4, QTableWidgetItem(leader['market_cap']))
                # 涨跌幅
                change_item = QTableWidgetItem(f"{leader['change']:+.2f}%")
                change_item.setForeground(
                    QColor("red") if leader['change'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 5, change_item)
                # 近5日涨跌幅
                change5_item = QTableWidgetItem(f"{leader['change_5']:+.2f}%")
                change5_item.setForeground(
                    QColor("red") if leader['change_5'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 6, change5_item)
                # 成交额
                self.leader_table.setItem(i, 7, QTableWidgetItem(
                    f"{leader['amount']:.2f}" if leader['amount'] != '-' else '-'))
                # 换手率
                self.leader_table.setItem(i, 8, QTableWidgetItem(
                    f"{leader['turnover']:.2f}%" if leader['turnover'] != '-' else '-'))
                # 振幅
                self.leader_table.setItem(i, 9, QTableWidgetItem(
                    f"{leader['amplitude']:.2f}%" if leader['amplitude'] != '-' else '-'))
                # 量比
                self.leader_table.setItem(
                    i, 10, QTableWidgetItem(leader['volume_ratio']))
                # 主力净流入
                main_flow_item = QTableWidgetItem(
                    f"{leader['main_flow']:+.2f}" if leader['main_flow'] != '-' else '-')
                main_flow_item.setForeground(
                    QColor("red") if leader['main_flow'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 11, main_flow_item)
                # 主力净流入占比
                self.leader_table.setItem(
                    i, 12, QTableWidgetItem(leader['main_flow_ratio']))
                # 涨停状态
                self.leader_table.setItem(
                    i, 13, QTableWidgetItem(leader['is_limit_up']))
                # 资金流向趋势
                self.leader_table.setItem(
                    i, 14, QTableWidgetItem(str(leader['flow_trend'])))
                # 综合得分
                self.leader_table.setItem(
                    i, 15, QTableWidgetItem(f"{leader['score']}"))
            self.leader_table.resizeColumnsToContents()
            self.log_manager.log(
                f"龙头股分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"分析龙头股失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析龙头股失败: {str(e)}")

    def clear_hotspot(self):
        """清除热点分析结果"""
        try:
            self.hotspot_table.setRowCount(0)
            self.theme_table.setRowCount(0)
            self.leader_table.setRowCount(0)
            self.rotation_table.setRowCount(0)
            # 无数据提示
            for table in [self.hotspot_table, self.theme_table, self.leader_table, self.rotation_table]:
                if table.rowCount() == 0:
                    table.setRowCount(1)
                    for col in range(table.columnCount()):
                        table.setItem(0, col, QTableWidgetItem("无数据"))
        except Exception as e:
            self.log_manager.log(f"清除热点分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def setup_indicator_panel(self):
        """设置指标面板"""
        panel = QWidget()
        if panel.layout() is None:
            layout = QVBoxLayout(panel)
            panel.setLayout(layout)
        else:
            layout = panel.layout()
        # 技术指标设置
        tech_group = QGroupBox("技术指标")
        tech_layout = QFormLayout()

        # MA设置
        ma_layout = QHBoxLayout()
        self.ma_period = QSpinBox()
        self.ma_period.setRange(1, 250)
        self.ma_period.setValue(20)
        ma_layout.addWidget(QLabel("周期:"))
        ma_layout.addWidget(self.ma_period)
        tech_layout.addRow("MA:", ma_layout)

        # MACD设置
        macd_layout = QHBoxLayout()
        self.macd_short = QSpinBox()
        self.macd_short.setRange(1, 50)
        self.macd_short.setValue(7)
        macd_layout.addWidget(QLabel("快线:"))
        macd_layout.addWidget(self.macd_short)

        self.macd_long = QSpinBox()
        self.macd_long.setRange(1, 100)
        self.macd_long.setValue(26)
        macd_layout.addWidget(QLabel("慢线:"))
        macd_layout.addWidget(self.macd_long)

        self.macd_signal = QSpinBox()
        self.macd_signal.setRange(1, 50)
        self.macd_signal.setValue(9)
        macd_layout.addWidget(QLabel("信号:"))
        macd_layout.addWidget(self.macd_signal)
        tech_layout.addRow("MACD:", macd_layout)

        # KDJ设置
        kdj_layout = QHBoxLayout()
        self.kdj_n = QSpinBox()
        self.kdj_n.setRange(1, 90)
        self.kdj_n.setValue(9)
        kdj_layout.addWidget(QLabel("N:"))
        kdj_layout.addWidget(self.kdj_n)

        self.kdj_m1 = QSpinBox()
        self.kdj_m1.setRange(1, 30)
        self.kdj_m1.setValue(3)
        kdj_layout.addWidget(QLabel("M1:"))
        kdj_layout.addWidget(self.kdj_m1)

        self.kdj_m2 = QSpinBox()
        self.kdj_m2.setRange(1, 30)
        self.kdj_m2.setValue(3)
        kdj_layout.addWidget(QLabel("M2:"))
        kdj_layout.addWidget(self.kdj_m2)
        tech_layout.addRow("KDJ:", kdj_layout)

        tech_group.setLayout(tech_layout)
        layout.addWidget(tech_group)

        # 趋势分析设置
        trend_group = QGroupBox("趋势分析")
        trend_layout = QFormLayout()

        # 趋势周期
        trend_period_layout = QHBoxLayout()
        self.trend_period = QSpinBox()
        self.trend_period.setRange(5, 120)
        self.trend_period.setValue(20)
        trend_period_layout.addWidget(QLabel("周期:"))
        trend_period_layout.addWidget(self.trend_period)
        trend_layout.addRow("趋势周期:", trend_period_layout)

        # 趋势阈值
        trend_threshold_layout = QHBoxLayout()
        self.trend_threshold = QSpinBox()  # 改为整数，使用百分比
        self.trend_threshold.setRange(1, 100)
        self.trend_threshold.setValue(10)
        trend_threshold_layout.addWidget(QLabel("阈值(%):"))
        trend_threshold_layout.addWidget(self.trend_threshold)
        trend_layout.addRow("趋势阈值:", trend_threshold_layout)

        trend_group.setLayout(trend_layout)
        layout.addWidget(trend_group)

        # 波动分析设置
        wave_group = QGroupBox("波动分析")
        wave_layout = QFormLayout()

        # 波动周期
        wave_period_layout = QHBoxLayout()
        self.wave_period = QSpinBox()
        self.wave_period.setRange(5, 120)
        self.wave_period.setValue(20)
        wave_period_layout.addWidget(QLabel("周期:"))
        wave_period_layout.addWidget(self.wave_period)
        wave_layout.addRow("波动周期:", wave_period_layout)

        # 波动灵敏度
        wave_sensitivity_layout = QHBoxLayout()
        self.wave_sensitivity = QSpinBox()  # 改为整数，使用百分比
        self.wave_sensitivity.setRange(1, 50)
        self.wave_sensitivity.setValue(10)
        wave_sensitivity_layout.addWidget(QLabel("灵敏度(%):"))
        wave_sensitivity_layout.addWidget(self.wave_sensitivity)
        wave_layout.addRow("波动灵敏度:", wave_sensitivity_layout)

        wave_group.setLayout(wave_layout)
        layout.addWidget(wave_group)

        # 市场情绪设置
        sentiment_group = QGroupBox("市场情绪")
        sentiment_layout = QFormLayout()

        # 恐慌贪婪指数
        fear_greed_layout = QHBoxLayout()
        self.fear_greed_spin = QSpinBox()
        self.fear_greed_spin.setRange(0, 100)
        self.fear_greed_spin.setValue(50)
        fear_greed_layout.addWidget(QLabel("指数:"))
        fear_greed_layout.addWidget(self.fear_greed_spin)
        sentiment_layout.addRow("恐慌贪婪:", fear_greed_layout)

        # 市场强弱指数
        market_strength_layout = QHBoxLayout()
        self.market_strength_spin = QSpinBox()
        self.market_strength_spin.setRange(0, 100)
        self.market_strength_spin.setValue(50)
        market_strength_layout.addWidget(QLabel("指数:"))
        market_strength_layout.addWidget(self.market_strength_spin)
        sentiment_layout.addRow("市场强弱:", market_strength_layout)

        # 资金流向指数
        fund_flow_layout = QHBoxLayout()
        self.fund_flow_spin = QSpinBox()
        self.fund_flow_spin.setRange(-100, 100)
        self.fund_flow_spin.setValue(0)
        fund_flow_layout.addWidget(QLabel("指数:"))
        fund_flow_layout.addWidget(self.fund_flow_spin)
        sentiment_layout.addRow("资金流向:", fund_flow_layout)

        # 北向资金指数
        north_flow_layout = QHBoxLayout()
        self.north_flow_spin = QSpinBox()
        self.north_flow_spin.setRange(-100, 100)
        self.north_flow_spin.setValue(0)
        north_flow_layout.addWidget(QLabel("指数:"))
        north_flow_layout.addWidget(self.north_flow_spin)
        sentiment_layout.addRow("北向资金:", north_flow_layout)

        sentiment_group.setLayout(sentiment_layout)
        layout.addWidget(sentiment_group)

        return panel

    def _get_turnover(self, kdata, stock=None) -> float:
        """
        统一换手率计算方法，兼容KRecord对象、DataFrame和stock对象
        Args:
            kdata: K线数据，支持KRecord序列或DataFrame
            stock: 股票对象（可选，用于获取流通股本）
        Returns:
            float: 换手率（%）
        """
        try:
            if kdata is None or len(kdata) == 0:
                return 0.0
            # 优先用turnover字段
            if hasattr(kdata[-1], 'turnover'):
                return float(getattr(kdata[-1], 'turnover', 0))
            elif isinstance(kdata, pd.DataFrame) and 'turnover' in kdata.columns:
                return float(kdata['turnover'].iloc[-1])
            # 其次用volume/circulating_shares估算
            elif hasattr(kdata[-1], 'volume') and stock and hasattr(stock, 'circulating_shares') and stock.circulating_shares:
                return float(kdata[-1].volume) / float(stock.circulating_shares) * 100
            elif isinstance(kdata, pd.DataFrame) and 'volume' in kdata.columns and stock and hasattr(stock, 'circulating_shares') and stock.circulating_shares:
                return float(kdata['volume'].iloc[-1]) / float(stock.circulating_shares) * 100
            else:
                return 0.0
        except Exception as e:
            self.log_manager.log(f"换手率计算失败: {str(e)}", LogLevel.ERROR)
            return 0.0

    @staticmethod
    def try_import(module_name):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            return None

    def get_industry_fund_flow_hist(self, name):
        """自动轮询数据源获取行业历史资金流向"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_board_industry_hist_em'):
                    return ak.stock_board_industry_hist_em(symbol=name, start_date="20240101", end_date="20240501")
                if hasattr(ak, 'stock_sector_fund_flow_hist'):
                    return ak.stock_sector_fund_flow_hist(symbol=name)
            except Exception as e:
                self.log_manager.log(
                    f"akshare行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_concept_fund_flow_hist(self, name):
        """自动轮询数据源获取概念历史资金流向"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_board_concept_hist_em'):
                    return ak.stock_board_concept_hist_em(symbol=name, start_date="20240101", end_date="20240501")
                if hasattr(ak, 'stock_sector_fund_flow_hist'):
                    return ak.stock_sector_fund_flow_hist(symbol=name)
            except Exception as e:
                self.log_manager.log(
                    f"akshare概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_north_fund_flow_hist(self):
        """自动轮询数据源获取北向资金历史"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_hsgt_north_net_flow'):
                    return ak.stock_hsgt_north_net_flow()
                if hasattr(ak, 'stock_hsgt_north_cash_flow'):
                    return ak.stock_hsgt_north_cash_flow()
            except Exception as e:
                self.log_manager.log(
                    f"akshare北向资金获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def plot_industry_trend(self, df):
        """行业资金流向60日走势图（自动轮询数据源）"""
        try:
            for _, row in df.iterrows():
                name = row.get('行业名称', '')
                hist = self.get_industry_fund_flow_hist(name)
                if hist is not None and not hist.empty:
                    fig = Figure(figsize=(5, 3))
                    canvas = FigureCanvas(fig)
                    ax = fig.add_subplot(111)
                    ax.plot(hist['日期'], hist.get(
                        '主力净流入', hist.columns[-1]), label=name)
                    ax.set_title(f"{name}近60日主力净流入")
                    ax.legend()
                    self.industry_trend_layout.addWidget(canvas)
                else:
                    self.log_manager.log(
                        f"行业{name}资金流向历史无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"行业资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def plot_concept_trend(self, df):
        """概念资金流向60日走势图（自动轮询数据源）"""
        try:
            for _, row in df.iterrows():
                name = row.get('概念名称', '')
                hist = self.get_concept_fund_flow_hist(name)
                if hist is not None and not hist.empty:
                    fig = Figure(figsize=(5, 3))
                    canvas = FigureCanvas(fig)
                    ax = fig.add_subplot(111)
                    ax.plot(hist['日期'], hist.get(
                        '主力净流入', hist.columns[-1]), label=name)
                    ax.set_title(f"{name}近60日主力净流入")
                    ax.legend()
                    self.concept_trend_layout.addWidget(canvas)
                else:
                    self.log_manager.log(
                        f"概念{name}资金流向历史无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"概念资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def analyze_north_flow(self):
        """分析北向资金，自动轮询数据源"""
        try:
            self.north_flow_table.setRowCount(0)
            df = self.get_north_fund_flow_hist()
            if df is not None and not df.empty:
                df = df.head(60)
                for i, row in df.iterrows():
                    date = row.get('日期', '')
                    sh = row.get('沪股通(亿元)', row.get('沪股通', 0))
                    sz = row.get('深股通(亿元)', row.get('深股通', 0))
                    total = row.get('北向资金(亿元)', row.get('北向资金', 0))
                    self.north_flow_table.insertRow(i)
                    self.north_flow_table.setItem(
                        i, 0, QTableWidgetItem(str(date)))
                    self.north_flow_table.setItem(
                        i, 1, QTableWidgetItem(f"{sh:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 2, QTableWidgetItem(f"{sz:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 3, QTableWidgetItem(f"{total:+.2f}"))
            else:
                self.log_manager.log("北向资金无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"北向资金分析失败: {str(e)}", LogLevel.ERROR)

    def get_fund_flow_with_cache(self, key, fetch_func, *args, **kwargs):
        """统一缓存+多数据源自动切换"""
        data = self.data_cache.get(key)
        if data is not None:
            return data
        data = fetch_func(*args, **kwargs)
        if data is not None and not data.empty:
            self.data_cache.set(key, data)
        return data

    def fetch_industry_fund_flow(self, industry_name):
        """轮询东方财富、Sina、同花顺获取行业资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def fetch_concept_fund_flow(self, concept_name):
        """轮询东方财富、Sina、同花顺获取概念资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def fetch_north_fund_flow(self):
        """轮询东方财富、Sina、同花顺获取北向资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富北向资金获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina北向资金获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺北向资金获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_industry_fund_flow(self, industry_name):
        key = f"industry_fund_flow_{industry_name}"
        return self.get_fund_flow_with_cache(key, self.fetch_industry_fund_flow, industry_name)

    def get_concept_fund_flow(self, concept_name):
        key = f"concept_fund_flow_{concept_name}"
        return self.get_fund_flow_with_cache(key, self.fetch_concept_fund_flow, concept_name)

    def get_north_fund_flow(self):
        key = "north_fund_flow"
        return self.get_fund_flow_with_cache(key, self.fetch_north_fund_flow)

    def create_sentiment_report_tab(self) -> QWidget:
        """创建舆情报告Tab，采集微博、雪球、财联社、炒股吧热度，支持多线程和采集周期设置，股票代码名称真实，分平台分列，趋势和热词着色"""
        import akshare as ak
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            # 采集周期设置
            period_layout = QHBoxLayout()
            period_layout.addWidget(QLabel("采集周期(分钟):"))
            self.sentiment_period_spin = QSpinBox()
            self.sentiment_period_spin.setRange(1, 60)
            self.sentiment_period_spin.setValue(2)
            period_layout.addWidget(self.sentiment_period_spin)
            # 合并按钮
            self.sentiment_toggle_btn = QPushButton("开始采集")
            period_layout.addWidget(self.sentiment_toggle_btn)
            # 倒计时文本
            self.sentiment_countdown_label = QLabel("")
            period_layout.addWidget(self.sentiment_countdown_label)
            layout.addLayout(period_layout)
            # 获取真实A股股票代码和名称
            try:
                stock_df = ak.stock_info_a_code_name()
                stock_list = stock_df.sample(n=10).values.tolist()  # 随机取10只
            except Exception:
                stock_list = [[f"600000", "浦发银行"], [f"000001", "平安银行"], [f"300750", "宁德时代"], [f"601318", "中国平安"], [f"600519", "贵州茅台"], [
                    f"000333", "美的集团"], [f"002594", "比亚迪"], [f"000651", "格力电器"], [f"601166", "兴业银行"], [f"600036", "招商银行"]]
            platforms = ["微博", "雪球", "财联社", "炒股吧"]
            col_labels = ["股票代码", "股票名称"]
            for p in platforms:
                col_labels += [f"{p}热度值", f"{p}热度趋势", f"{p}热词/摘要"]
            col_labels += ["采集时间"]
            self.sentiment_table = QTableWidget()
            self.sentiment_table.setColumnCount(len(col_labels))
            self.sentiment_table.setHorizontalHeaderLabels(col_labels)
            self.sentiment_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            layout.addWidget(self.sentiment_table)
            # 采集定时器
            self.sentiment_timer = QTimer()
            self.sentiment_timer.setInterval(
                self.sentiment_period_spin.value() * 60 * 1000)
            self.sentiment_timer.timeout.connect(self._start_sentiment_collect)
            self.sentiment_period_spin.valueChanged.connect(
                self._update_sentiment_timer)
            self.sentiment_collecting = False
            self._sentiment_stock_list = stock_list
            self._sentiment_platforms = platforms
            # 倒计时定时器
            self.sentiment_countdown_timer = QTimer()
            self.sentiment_countdown_timer.setInterval(1000)
            self.sentiment_countdown_timer.timeout.connect(
                self._update_sentiment_countdown)
            self.sentiment_next_collect_ts = None
            # 按钮事件
            self.sentiment_toggle_btn.clicked.connect(
                self._toggle_sentiment_collect)
            return widget
        except Exception as e:
            self.log_manager.log(f"创建舆情报告Tab失败: {str(e)}", LogLevel.ERROR)
            raise

    def _toggle_sentiment_collect(self):
        if self.sentiment_timer.isActive():
            self._stop_sentiment_timer()
        else:
            self._start_sentiment_timer()

    def _start_sentiment_timer(self):
        self.sentiment_timer.start()
        self.sentiment_toggle_btn.setText("停止采集")
        self._start_sentiment_collect()
        # 启动倒计时
        self.sentiment_next_collect_ts = time.time(
        ) + self.sentiment_period_spin.value() * 60
        self.sentiment_countdown_timer.start()
        self._update_sentiment_countdown()

    def _stop_sentiment_timer(self):
        self.sentiment_timer.stop()
        self.sentiment_toggle_btn.setText("开始采集")
        self.sentiment_countdown_timer.stop()
        self.sentiment_countdown_label.setText("")

    def _update_sentiment_timer(self):
        self.sentiment_timer.setInterval(
            self.sentiment_period_spin.value() * 60 * 1000)
        if self.sentiment_timer.isActive():
            self.sentiment_next_collect_ts = time.time(
            ) + self.sentiment_period_spin.value() * 60

    def _update_sentiment_countdown(self):
        if not self.sentiment_timer.isActive() or not self.sentiment_next_collect_ts:
            self.sentiment_countdown_label.setText("")
            return
        remain = int(self.sentiment_next_collect_ts - time.time())
        if remain < 0:
            remain = 0
        self.sentiment_countdown_label.setText(f"距离下次采集：{remain}秒")
        if remain == 0:
            self.sentiment_next_collect_ts = time.time(
            ) + self.sentiment_period_spin.value() * 60

    def _start_sentiment_collect(self):
        if self.sentiment_collecting:
            return
        self.sentiment_collecting = True
        from datetime import datetime
        import concurrent.futures
        stock_list = getattr(self, '_sentiment_stock_list', [])
        platforms = getattr(self, '_sentiment_platforms',
                            ["微博", "雪球", "财联社", "炒股吧"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table_data = []
        # 采集函数

        def get_xueqiu_hot(code, name):
            try:
                # 雪球页面如 https://xueqiu.com/S/SH600000
                url = f"https://xueqiu.com/S/SH{code}" if code.startswith(
                    '6') else f"https://xueqiu.com/S/SZ{code}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # 雪球热度（讨论数）
                    hot = soup.find("span", class_="stockDiscuss__num")
                    if hot:
                        return int(hot.text.replace(",", "")), "→", "AI"
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_guba_hot(code, name):
            try:
                # 炒股吧页面 https://guba.eastmoney.com/list,600000.html
                url = f"https://guba.eastmoney.com/list,{code}.html"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # 热度：帖子数
                    hot = soup.find("span", class_="total-posts")
                    if hot:
                        return int(hot.text.replace(",", "")), "→", "利好"
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_cls_hot(code, name):
            try:
                # 财联社新闻热度（模拟，实际可用akshare或爬虫）
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_weibo_hot(code, name):
            try:
                # 微博热搜榜（模拟，实际可用weibo-search或爬虫）
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'
        # 多线程采集
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for code, name in stock_list:
                row = [code, name]
                futures = []
                futures.append(executor.submit(get_weibo_hot, code, name))
                futures.append(executor.submit(get_xueqiu_hot, code, name))
                futures.append(executor.submit(get_cls_hot, code, name))
                futures.append(executor.submit(get_guba_hot, code, name))
                for f in futures:
                    hot, trend, keywords = f.result()
                    row += [hot, trend, keywords]
                row += [now]
                table_data.append(row)
        self.sentiment_table.setRowCount(len(table_data))
        # 着色规则
        trend_color = {"↑": QColor("red"), "↓": QColor(
            "green"), "→": QColor("black")}
        keyword_color = {"利好": QColor("red"), "利空": QColor("green"), "涨停": QColor("orange"), "AI": QColor(
            "blue"), "新能源": QColor("blue"), "大盘": QColor("black"), "新高": QColor("purple")}
        for i, row in enumerate(table_data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                # 热度趋势着色
                if j >= 4 and (j-2) % 3 == 0:
                    item.setForeground(trend_color.get(val, QColor("black")))
                # 热词着色
                if j >= 5 and (j-1) % 3 == 0:
                    item.setForeground(keyword_color.get(val, QColor("black")))
                self.sentiment_table.setItem(i, j, item)
        self.sentiment_collecting = False

    def _connect_rotation_worker_signals(self):
        """
        连接rotation_worker的信号到对应的槽函数，确保热点轮动分析进度和结果能正确显示。
        """
        if hasattr(self, 'rotation_worker') and self.rotation_worker:
            try:
                self.rotation_worker.update_progress.connect(
                    self._on_rotation_progress)
                self.rotation_worker.update_table.connect(
                    self._on_rotation_table)
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"连接rotation_worker信号失败: {str(e)}")

    def set_kdata(self, kdata):
        """同步主窗口K线数据到AnalysisWidget，自动兜底多渠道同步，结构化日志输出"""
        import json
        try:
            log_info = {"event": "set_kdata", "source": "外部调用", "len": None, "fields": None, "from": None, "status": "init"}
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                log_info["status"] = "empty"
                # 兜底：主图
                if hasattr(self, 'chart_widget') and hasattr(self.chart_widget, 'current_kdata'):
                    chart_kdata = self.chart_widget.current_kdata
                    if chart_kdata is not None and (not hasattr(chart_kdata, 'empty') or not chart_kdata.empty):
                        kdata = chart_kdata
                        log_info["from"] = "chart_widget"
                        log_info["len"] = len(kdata)
                        log_info["fields"] = list(kdata.columns)
                        log_info["status"] = "fallback_chart"
                # 兜底：主窗口
                if (kdata is None or (hasattr(kdata, 'empty') and kdata.empty)) and hasattr(self, 'parentWidget'):
                    main_window = self.parentWidget()
                    while main_window and not hasattr(main_window, 'get_kdata'):
                        main_window = main_window.parentWidget() if hasattr(main_window, 'parentWidget') else None
                    code = getattr(self, 'current_stock', None) or getattr(self, 'selected_code', None) or getattr(self, 'code', None)
                    if main_window and hasattr(main_window, 'get_kdata') and code:
                        main_kdata = main_window.get_kdata(code)
                        if main_kdata is not None and (not hasattr(main_kdata, 'empty') or not main_kdata.empty):
                            kdata = main_kdata
                            log_info["from"] = "main_window"
                            log_info["len"] = len(kdata)
                            log_info["fields"] = list(kdata.columns)
                            log_info["status"] = "fallback_main"
                # 兜底：缓存
                if (kdata is None or (hasattr(kdata, 'empty') and kdata.empty)) and hasattr(self, 'data_cache'):
                    cache_kdata = self.data_cache.get(getattr(self, 'current_stock', None))
                    if cache_kdata is not None and (not hasattr(cache_kdata, 'empty') or not cache_kdata.empty):
                        kdata = cache_kdata
                        log_info["from"] = "data_cache"
                        log_info["len"] = len(kdata)
                        log_info["fields"] = list(kdata.columns)
                        log_info["status"] = "fallback_cache"
            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty):
                log_info["status"] = "fail"
                self.current_kdata = None
                if hasattr(self, 'log_manager'):
                    self.log_manager.warning(json.dumps(log_info, ensure_ascii=False))
                if hasattr(self, 'pattern_table'):
                    self.pattern_table.setRowCount(0)
                return
            import pandas as pd
            if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                kdata = kdata.copy()
                kdata['code'] = getattr(self, 'current_stock', None) or '未知'
                log_info["status"] = "add_code"
            self.current_kdata = kdata
            log_info["status"] = "success"
            log_info["len"] = len(kdata)
            log_info["fields"] = list(kdata.columns)
            if hasattr(self, 'log_manager'):
                self.log_manager.info(json.dumps(log_info, ensure_ascii=False))

            # 自动更新数据状态显示
            if hasattr(self, '_update_data_status'):
                QTimer.singleShot(100, self._update_data_status)  # 延迟执行，确保UI已初始化

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(json.dumps({"event": "set_kdata", "error": str(e)}))
            self.current_kdata = None
            if hasattr(self, 'pattern_table'):
                self.pattern_table.setRowCount(0)
            return

    def _on_pattern_table_selection_changed(self):
        """表格选择变化时，主图高亮对应信号"""
        try:
            selected_rows = self.pattern_table.selectionModel().selectedRows()
            if not selected_rows:
                # 清除主图高亮
                if hasattr(self, 'chart_widget') and self.chart_widget:
                    self.chart_widget.clear_signal_highlight()
                return

            # 获取选中的信号信息
            selected_signals = []
            for row_index in selected_rows:
                row = row_index.row()

                # 从表格中提取信号信息
                pattern_item = self.pattern_table.item(row, 1)  # 形态列
                index_item = self.pattern_table.item(row, 2)    # K线索引列
                price_item = self.pattern_table.item(row, 4)    # 价格列

                if pattern_item and index_item and price_item:
                    signal_info = {
                        'type': pattern_item.text(),
                        'index': int(index_item.text()),
                        'price': float(price_item.text()),
                        'row': row
                    }
                    selected_signals.append(signal_info)

            # 主图高亮选中信号
            if hasattr(self, 'chart_widget') and self.chart_widget and selected_signals:
                self.chart_widget.highlight_signals(selected_signals)

                # 发送高亮信号（供其他组件使用）
                for signal in selected_signals:
                    self.pattern_selected.emit(signal['index'])

        except Exception as e:
            self.log_manager.error(f"表格选择变化处理失败: {str(e)}")

    def on_pattern_selected(self, idx):
        """响应主图信号选择，同步高亮表格对应行"""
        try:
            # 查找对应的表格行
            for row in range(self.pattern_table.rowCount()):
                index_item = self.pattern_table.item(row, 2)  # K线索引列
                if index_item and int(index_item.text()) == idx:
                    # 高亮表格行
                    self.pattern_table.selectRow(row)
                    self.pattern_table.scrollToItem(index_item, QAbstractItemView.PositionAtCenter)
                    break

        except Exception as e:
            self.log_manager.error(f"响应信号选择失败: {str(e)}")

    def refresh_all_tabs(self):
        """一键刷新所有分析Tab数据，供主窗口切换数据源时调用"""
        self.refresh_technical_data()
        self.refresh_pattern_data()
        self.refresh_trend_data()
        self.refresh_wave_data()
        self.refresh_sentiment_data()

    def _kdata_preprocess(self, kdata, context="分析"):
        """K线数据预处理：检查并修正所有关键字段，遇到异常自动补全、填充或过滤，详细日志和友好提示"""
        import pandas as pd
        from datetime import datetime
        if not isinstance(kdata, pd.DataFrame):
            return kdata
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'code']
        missing_cols = [col for col in required_cols if col not in kdata.columns]
        if missing_cols:
            self.log_manager.warning(f"{context}收到K线数据缺少字段: {missing_cols}，自动补全/填充")
            for col in missing_cols:
                if col == 'datetime':
                    kdata['datetime'] = pd.to_datetime(datetime.now()).strftime('%Y-%m-%d')
                elif col == 'code':
                    code = getattr(self, 'current_stock', None) or getattr(self, 'code', None) or ''
                    kdata['code'] = code
                else:
                    kdata[col] = 0.0
        # 修正datetime字段

        def fix_datetime(val, prev):
            try:
                if pd.isna(val) or val is None:
                    return prev if prev else None
                return pd.to_datetime(val).strftime('%Y-%m-%d')
            except Exception as e:
                self.log_manager.warning(f"修正datetime异常: {val}, 错误: {str(e)}")
                return prev if prev else None
        # 优先用索引推断datetime
        if 'datetime' not in kdata.columns:
            if isinstance(kdata.index, pd.DatetimeIndex):
                kdata = kdata.copy()
                kdata['datetime'] = kdata.index
            else:
                QMessageBox.warning(self, f"{context}数据异常", "K线数据缺少datetime字段且无法推断，请检查数据源！")
                return pd.DataFrame()
        prev_dt = None
        dt_list = []
        for v in kdata['datetime']:
            fixed = fix_datetime(v, prev_dt)
            dt_list.append(fixed)
            prev_dt = fixed
        kdata['datetime'] = dt_list
        # 过滤无效datetime
        before = len(kdata)
        kdata = kdata[kdata['datetime'].notna() & (kdata['datetime'] != '')]
        after = len(kdata)
        if after < before:
            self.log_manager.warning(f"{context}已过滤{before-after}行无效datetime数据")
        if len(kdata) == 0:
            QMessageBox.warning(self, f"{context}数据异常", "K线数据全部无效，无法进行分析。请检查数据源或时间区间！")
            return pd.DataFrame()
        # 检查数值字段异常
        for col in ['open', 'high', 'low', 'close', 'volume']:
            before = len(kdata)
            kdata = kdata[kdata[col].notna() & (kdata[col] >= 0)]
            after = len(kdata)
            if after < before:
                self.log_manager.warning(f"{context}已过滤{before-after}行{col}字段异常数据")
        return kdata.reset_index(drop=True)

    def _update_data_status(self):
        """更新数据状态显示"""
        try:
            if self.current_kdata is None or (hasattr(self.current_kdata, 'empty') and self.current_kdata.empty):
                status_text = "❌ 无数据"
            else:
                data_len = len(self.current_kdata)
                columns = list(self.current_kdata.columns) if hasattr(self.current_kdata, 'columns') else []

                # 检查关键字段
                required_fields = ['open', 'high', 'low', 'close', 'volume']
                missing_fields = [f for f in required_fields if f not in columns]
                has_datetime = 'datetime' in columns

                status_text = f"✅ 数据长度: {data_len}"
                if missing_fields:
                    status_text += f" | ❌ 缺少字段: {missing_fields}"
                if not has_datetime:
                    status_text += " | ⚠️ 缺少datetime"
                else:
                    status_text += " | ✅ 含datetime"

                # 检查数据时间范围
                if has_datetime:
                    try:
                        datetime_col = pd.to_datetime(self.current_kdata['datetime'])
                        start_date = datetime_col.min().strftime('%Y-%m-%d')
                        end_date = datetime_col.max().strftime('%Y-%m-%d')
                        status_text += f" | 时间范围: {start_date} 至 {end_date}"
                    except Exception as e:
                        status_text += f" | ⚠️ datetime格式异常: {str(e)[:20]}"

            if hasattr(self, 'data_status_label'):
                self.data_status_label.setText(status_text)

        except Exception as e:
            if hasattr(self, 'data_status_label'):
                self.data_status_label.setText(f"❌ 状态检查失败: {str(e)[:30]}")
            self.log_manager.error(f"更新数据状态失败: {e}")


def get_indicator_categories():
    """获取所有指标分类及其指标列表，确保与ta-lib分类一致"""
    from indicators_algo import get_all_indicators_by_category
    return get_all_indicators_by_category()


class MatplotlibWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(2, 2))
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_pie(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        from collections import Counter
        counter = Counter(data)
        labels, sizes = zip(*counter.items()) if counter else ([], [])
        if sizes:
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title('类型分布')
        self.canvas.draw()

    def plot_bar(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        from collections import Counter
        counter = Counter(data)
        labels, sizes = zip(*sorted(counter.items())) if counter else ([], [])
        if sizes:
            ax.bar(labels, sizes)
        ax.set_title('价格区间分布')
        self.canvas.draw()
