"""
主程序入口

提供交易系统的GUI界面和主要功能
"""
import sys
import os
import json
import csv
import time
import random
import logging
import traceback
import threading
import weakref
import gc
import psutil
import requests
from datetime import datetime, timedelta
from enum import Enum, auto
import functools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import mplfinance
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

import hikyuu as hku
from hikyuu.interactive import *
from hikyuu.indicator import *

# 导入自定义模块
from utils import (
    Theme,
    ThemeConfig,
    ChartConfig,
    TradingConfig,
    PerformanceConfig,
    DataConfig,
    UIConfig,
    LoggingConfig,
    ConfigManager,
    ThemeManager,
    PerformanceMonitor,
    ExceptionHandler
)
from core.data_manager import DataManager
from core.logger import LogManager, LogLevel
from components.market_sentiment import MarketSentimentWidget
from components.fund_flow import FundFlowWidget
from gui.tool_bar import MainToolBar
from gui.menu_bar import MainMenuBar
from components.stock_screener import StockScreenerWidget

from pylab import mpl
# 设置matplotlib字体
mpl.rcParams["font.sans-serif"] = [
    "SimHei"          # 黑体
]
mpl.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题
mpl.rcParams["font.size"] = 12

# 设置Qt应用程序字体
QApplication.setFont(QFont("Microsoft YaHei", 10))

# 定义全局样式表
GLOBAL_STYLE = """
QWidget {
    font-family: 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', sans-serif;
}

QTextEdit, QPlainTextEdit {
    font-family: 'Consolas', 'Microsoft YaHei', 'SimHei', monospace;
    font-size: 12px;
}

QPushButton {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
}

QLabel {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
}

QComboBox {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
}

QLineEdit {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
}
"""

class TradingGUI(QMainWindow):
    """Trading system main window"""
    
    # Define signals
    theme_changed = pyqtSignal(Theme)
    data_updated = pyqtSignal(dict)
    analysis_completed = pyqtSignal(dict)
    performance_updated = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize trading GUI"""
        super().__init__()
        
        # 设置字体
        font = QFont("Microsoft YaHei", 9)  # 使用微软雅黑字体
        self.setFont(font)
        
        # 设置窗口标题
        self.setWindowTitle("Hikyuu量化交易系统")
        
        # 设置窗口大小
        self.resize(1200, 800)
        
        # Initialize managers
        self.config_manager = ConfigManager()
        self.theme_manager = ThemeManager(self.config_manager)
        self.log_manager = LogManager(self.config_manager.logging)
        self.performance_monitor = PerformanceMonitor(
            config=self.config_manager.performance,
            log_manager=self.log_manager
        )
        self.exception_handler = ExceptionHandler(self.log_manager)
        self.data_manager = DataManager()
        
        # Initialize attributes
        self.current_stock = None
        self.current_period = "D"
        self.current_strategy = None
        self.favorites = set()
        self.param_controls = {}
        self.settings_controls = {}
        
        # Initialize mutexes
        self.data_mutex = QMutex()
        self.chart_mutex = QMutex()
        self.indicator_mutex = QMutex()
        
        # Initialize caches
        self.data_cache = {}
        self.chart_cache = {}
        self.stock_list_cache = []
        
        # Initialize thread pool
        self.thread_pool = QThreadPool()
        
        # Initialize splitters
        self.top_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter = QSplitter(Qt.Vertical)
        
        # Initialize log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        
        # Initialize UI
        self.init_ui()
        
        # Initialize data
        self.init_data()
        
        # Connect log manager signals
        self.log_manager.log_added.connect(self.log_message)
        self.log_manager.log_cleared.connect(self.clear_log)
        self.log_manager.performance_alert.connect(self.handle_performance_alert)
        self.log_manager.exception_occurred.connect(self.handle_exception)
        
        # Initialize exception handler
        sys.excepthook = self.exception_handler.handle_gui_exception
        
        # 应用全局样式表
        self.setStyleSheet(GLOBAL_STYLE)
        
        # Start performance monitoring
        self.start_performance_monitoring()
        
    def init_ui(self):
        """Initialize user interface"""
        try:
            # Create main widget
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            
            # Create main layout
            self.main_layout = QVBoxLayout(self.central_widget)
            
            # Add splitters to main layout
            self.main_layout.addWidget(self.top_splitter)
            self.main_layout.addWidget(self.bottom_splitter)
            
            # Create panels
            self.create_left_panel()
            self.create_middle_panel()
            self.create_right_panel()
            self.create_bottom_panel()
            
            # Create menu bar and status bar
            self.create_menubar()
            self.create_statusbar()
            
            # Create toolbar
            self.create_toolbar()
            
            # Apply theme to all widgets
            self.apply_theme()
            
        except Exception as e:
            self.log_message(f"初始化UI失败: {str(e)}", "error")
            raise
        
    def create_menubar(self):
        """Create menu bar with all necessary actions"""
        try:
            self.menu_bar = MainMenuBar(self)
            self.setMenuBar(self.menu_bar)
            
            # Connect menu actions
            self.menu_bar.file_menu.aboutToShow.connect(self.update_recent_files)
            self.menu_bar.edit_menu.aboutToShow.connect(self.update_edit_menu)
            self.menu_bar.view_menu.aboutToShow.connect(self.update_view_menu)
            self.menu_bar.tools_menu.aboutToShow.connect(self.update_tools_menu)
            self.menu_bar.help_menu.aboutToShow.connect(self.update_help_menu)
            
            # Connect signals
            self.menu_bar.settings_action.triggered.connect(self.show_settings)
            self.menu_bar.calculator_action.triggered.connect(self.show_calculator)
            self.menu_bar.converter_action.triggered.connect(self.show_converter)
            self.menu_bar.about_action.triggered.connect(self.show_about)
            
        except Exception as e:
            self.log_message(f"创建菜单栏失败: {str(e)}", "error")
        
    def create_toolbar(self):
        """Create the main toolbar with all necessary actions"""
        try:
            self.toolbar = MainToolBar(self)
            self.addToolBar(self.toolbar)
            
            # Connect toolbar actions
            self.toolbar.analyze_action.triggered.connect(self.analyze)
            self.toolbar.backtest_action.triggered.connect(self.backtest)
            self.toolbar.optimize_action.triggered.connect(self.optimize)
            self.toolbar.zoom_in_action.triggered.connect(self.zoom_in)
            self.toolbar.zoom_out_action.triggered.connect(self.zoom_out)
            self.toolbar.reset_zoom_action.triggered.connect(self.reset_zoom)
            self.toolbar.settings_action.triggered.connect(self.show_settings)
            self.toolbar.calculator_action.triggered.connect(self.show_calculator)
            self.toolbar.converter_action.triggered.connect(self.show_converter)
            
            # Add separator
            self.toolbar.addSeparator()
            
            # Add stock search
            self.stock_search = QLineEdit()
            self.stock_search.setPlaceholderText("搜索股票...")
            self.stock_search.textChanged.connect(self.filter_stock_list)
            self.toolbar.addWidget(self.stock_search)
            
        except Exception as e:
            self.log_message(f"创建工具栏失败: {str(e)}", "error")
        
    def create_statusbar(self):
        """Create the status bar"""
        try:
            self.statusBar().showMessage("就绪")
        except Exception as e:
            self.log_message(f"显示帮助文档失败: {str(e)}", "error")

    def show_about(self):
        """显示关于对话框"""
        try:
            QMessageBox.about(self, "关于",
                "Hikyuu量化交易系统\n"
                "版本: 1.0.0\n"
                "作者: Your Name\n"
                "版权所有 © 2024"
            )
        except Exception as e:
            self.log_message(f"显示关于对话框失败: {str(e)}", "error")

    def init_data(self):
        """Initialize data"""
        try:
            print("初始化数据")
            # Initialize mutexes
            self.data_mutex = QMutex()
            self.chart_mutex = QMutex()
            self.indicator_mutex = QMutex()
            print("初始化互斥锁完成")   
                
            # Initialize caches
            self.data_cache = {}
            self.chart_cache = {}
            self.stock_list_cache = []
            print("初始化缓存完成")
                
            # Initialize thread pool
            self.thread_pool = QThreadPool()
            print("初始化线程池完成")
                
            # Load settings
            self.settings = self.config_manager.get_all()
            print("加载配置完成")
            
        except Exception as e:
            self.log_message(f"初始化数据失败: {str(e)}", "error")
            raise
        
    def apply_theme(self):
        """Apply theme to all widgets"""
        try:
            # Apply theme to main window
            self.theme_manager.apply_theme(self)
            
            # Apply theme to charts
            for figure in [self.figure, self.signals_figure, self.backtest_figure]:
                if figure is not None:
                    self.theme_manager.apply_chart_theme(figure)
            
            # Apply theme to all child widgets
            for widget in self.findChildren(QWidget):
                if widget is not None and not widget.parent() == self:
                    self.theme_manager.apply_theme(widget)
            
        except Exception as e:
            self.log_message(f"应用主题失败: {str(e)}", "error")
            raise

    def create_left_panel(self):
        """Create left panel with stock list and indicators"""
        try:
            # Create left panel
            self.left_panel = QWidget()
            self.left_layout = QVBoxLayout(self.left_panel)
            
            # Create stock list group
            stock_group = QGroupBox("股票列表")
            stock_layout = QVBoxLayout(stock_group)
            
            # Create stock type selector
            stock_type_layout = QHBoxLayout()
            stock_type_label = QLabel("市场:")
            self.stock_type_combo = QComboBox()
            self.stock_type_combo.addItems(["全部", "A股", "港股", "美股"])
            self.stock_type_combo.currentTextChanged.connect(self.filter_stock_list)
            stock_type_layout.addWidget(stock_type_label)
            stock_type_layout.addWidget(self.stock_type_combo)
            stock_layout.addLayout(stock_type_layout)
            
            # Create stock search box with advanced search
            search_layout = QHBoxLayout()
            self.stock_search = QLineEdit()
            self.stock_search.setPlaceholderText("搜索股票(代码/名称/拼音)...")
            self.stock_search.textChanged.connect(self.filter_stock_list)
            search_layout.addWidget(self.stock_search)
            
            # Add advanced search button
            advanced_search_btn = QPushButton("高级搜索")
            advanced_search_btn.clicked.connect(self.show_advanced_search_dialog)
            search_layout.addWidget(advanced_search_btn)
            stock_layout.addLayout(search_layout)
            
            # Create stock list with custom item widget
            self.stock_list = QListWidget()
            self.stock_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.stock_list.itemSelectionChanged.connect(self.on_stock_selected)
            stock_layout.addWidget(self.stock_list)
            
            # Create stock list controls
            stock_controls = QHBoxLayout()
            refresh_button = QPushButton("刷新")
            refresh_button.clicked.connect(self.update_stock_list)
            stock_controls.addWidget(refresh_button)
            
            # Add favorite button
            favorite_button = QPushButton("收藏")
            favorite_button.clicked.connect(self.toggle_favorite)
            stock_controls.addWidget(favorite_button)
            
            # Add export button
            export_button = QPushButton("导出")
            export_button.clicked.connect(self.export_stock_list)
            stock_controls.addWidget(export_button)
            
            stock_layout.addLayout(stock_controls)
            
            # Add stock group to left layout
            self.left_layout.addWidget(stock_group)
            
            # Create indicators group
            indicators_group = QGroupBox("技术指标")
            indicators_layout = QVBoxLayout(indicators_group)
            
            # Create indicator type selector
            indicator_type_layout = QHBoxLayout()
            indicator_type_label = QLabel("类型:")
            self.indicator_type_combo = QComboBox()
            self.indicator_type_combo.addItems(["全部", "趋势类", "震荡类", "成交量类", "自定义"])
            self.indicator_type_combo.currentTextChanged.connect(self.filter_indicator_list)
            indicator_type_layout.addWidget(indicator_type_label)
            indicator_type_layout.addWidget(self.indicator_type_combo)
            indicators_layout.addLayout(indicator_type_layout)
            
            # Create indicator search box
            self.indicator_search = QLineEdit()
            self.indicator_search.setPlaceholderText("搜索指标...")
            self.indicator_search.textChanged.connect(self.filter_indicator_list)
            indicators_layout.addWidget(self.indicator_search)
            
            # Create indicator list with custom item widget
            self.indicator_list = QListWidget()
            self.indicator_list.setSelectionMode(QAbstractItemView.MultiSelection)
            self.indicator_list.itemSelectionChanged.connect(self.on_indicators_changed)
            indicators_layout.addWidget(self.indicator_list)
            
            # Create indicator controls
            indicator_controls = QHBoxLayout()
            
            # Add parameter button
            param_button = QPushButton("参数设置")
            param_button.clicked.connect(self.show_indicator_params_dialog)
            indicator_controls.addWidget(param_button)
            
            # Add clear button
            clear_button = QPushButton("清除")
            clear_button.clicked.connect(self.indicator_list.clearSelection)
            indicator_controls.addWidget(clear_button)
            
            # Add save button
            save_button = QPushButton("保存组合")
            save_button.clicked.connect(self.save_indicator_combination)
            indicator_controls.addWidget(save_button)
            
            indicators_layout.addLayout(indicator_controls)
            
            # Add indicators group to left layout
            self.left_layout.addWidget(indicators_group)
            
            # Add to top splitter
            self.top_splitter.addWidget(self.left_panel)
            
        except Exception as e:
            self.log_message(f"创建左侧面板失败: {str(e)}", "error")
            raise
            
    def filter_stock_list(self, text: str):
        """Filter stock list based on search text with performance optimization"""
        try:
            # 使用线程池异步过滤
            def filter_list():
                try:
                    # 获取股票列表引用
                    stock_list_ref = weakref.ref(self.stock_list)
                    stock_list_cache_ref = weakref.ref(self.stock_list_cache)
                    
                    if stock_list_ref() and stock_list_cache_ref():
                        # 暂停更新以提高性能
                        stock_list_ref().setUpdatesEnabled(False)
                        
                        # 清空列表
                        stock_list_ref().clear()
                        
                        # 过滤股票
                        for stock_text in stock_list_cache_ref():
                            if text.lower() in stock_text.lower():
                                item = QListWidgetItem(stock_text)
                                if stock_text.split()[0] in self.favorites:
                                    item.setText(f"★ {stock_text}")
                                stock_list_ref().addItem(item)
                                
                        # 恢复更新
                        stock_list_ref().setUpdatesEnabled(True)
                        
                        # 记录日志
                        self.log_message(f"已过滤股票列表，显示 {stock_list_ref().count()} 只股票", "info")
                        
                except Exception as e:
                    self.log_message(f"过滤股票列表失败: {str(e)}", "error")
                    
            # 使用线程池执行过滤
            self.thread_pool.start(filter_list)
            
        except Exception as e:
            self.log_message(f"过滤股票列表失败: {str(e)}", "error")

    def filter_indicator_list(self, text: str) -> None:
        """过滤指标列表
        
        Args:
            text: 过滤文本
        """
        try:
            # 获取指标类型
            indicator_type = self.indicator_type_combo.currentText()
            
            # 遍历指标列表
            for i in range(self.indicator_list.count()):
                item = self.indicator_list.item(i)
                indicator = item.text()
                
                # 检查指标类型
                if indicator_type != "全部":
                    if indicator_type == "趋势类" and not any(x in indicator for x in ["MA", "MACD", "BOLL"]):
                        item.setHidden(True)
                        continue
                    elif indicator_type == "震荡类" and not any(x in indicator for x in ["RSI", "KDJ", "CCI"]):
                        item.setHidden(True)
                        continue
                    elif indicator_type == "成交量类" and not any(x in indicator for x in ["VOL", "OBV"]):
                        item.setHidden(True)
                        continue
                    elif indicator_type == "自定义" and not any(x in indicator for x in ["自定义"]):
                        item.setHidden(True)
                        continue
                
                # 检查搜索文本
                if text and text.lower() not in indicator.lower():
                    item.setHidden(True)
                else:
                    item.setHidden(False)
                    
        except Exception as e:
            self.log_message(f"过滤指标列表失败: {str(e)}", "error")
            
    def on_time_range_changed(self, time_range: str) -> None:
        """处理时间范围变化事件
        
        Args:
            time_range: 时间范围名称
        """
        try:
            # 时间范围映射
            time_range_map = {
                '最近1个月': 30,
                '最近3个月': 90,
                '最近6个月': 180,
                '最近1年': 365,
                '最近2年': 730,
                '最近3年': 1095,
                '最近5年': 1825,
                '全部': 0
            }
            
            if time_range in time_range_map:
                self.current_time_range = time_range_map[time_range]
                self.update_chart()
                self.log_manager.log(f"时间范围已更改为: {time_range}", "INFO")
                
        except Exception as e:
            self.log_manager.log(f"更改时间范围失败: {str(e)}", "ERROR")
            
    def on_analysis_type_changed(self, analysis_type: str) -> None:
        """处理分析类型变化事件
        
        Args:
            analysis_type: 分析类型名称
        """
        try:
            # 分析类型映射
            analysis_type_map = {
                '技术分析': 'technical',
                '基本面分析': 'fundamental',
                '资金流向分析': 'money_flow',
                '行业分析': 'industry',
                '市场情绪分析': 'sentiment'
            }
            
            if analysis_type in analysis_type_map:
                self.current_analysis_type = analysis_type_map[analysis_type]
                self.update_analysis()
                self.log_manager.log(f"分析类型已更改为: {analysis_type}", "INFO")
                
        except Exception as e:
            self.log_manager.log(f"更改分析类型失败: {str(e)}", "ERROR")

    def create_middle_panel(self):
        """Create middle panel with charts"""
        try:
            # Create middle panel
            self.middle_panel = QWidget()
            self.middle_layout = QVBoxLayout(self.middle_panel)
            
            # Create chart toolbar
            self.chart_toolbar = QToolBar("图表工具栏")
            self.chart_toolbar.setMovable(False)
            self.middle_layout.addWidget(self.chart_toolbar)
            
            # Add chart actions
            self.chart_toolbar.addAction("保存图表", self.save_chart)
            self.chart_toolbar.addAction("重置视图", self.reset_chart_view)
            self.chart_toolbar.addAction("切换主题", self.toggle_chart_theme)
            self.chart_toolbar.addSeparator()
            
            # Add chart type selector
            chart_type_label = QLabel("图表类型:")
            self.chart_type_combo = QComboBox()
            self.chart_type_combo.addItems([
                "K线图",
                "分时图",
                "成交量图",
                "MACD图",
                "RSI图",
                "布林带图",
                "波浪分析图",
                "模式识别图",
                "风险分析图"
            ])
            self.chart_toolbar.addWidget(chart_type_label)
            self.chart_toolbar.addWidget(self.chart_type_combo)
            
            # Create tab widget for different chart types
            self.chart_tabs = QTabWidget()
            
            # Create main chart tab
            self.main_chart_tab = QWidget()
            self.main_chart_layout = QVBoxLayout(self.main_chart_tab)
            
            # Create main chart figure and canvas
            self.figure = Figure(figsize=(8, 6))
            self.canvas = FigureCanvas(self.figure)
            self.main_chart_layout.addWidget(self.canvas)
            
            # Add navigation toolbar
            self.nav_toolbar = NavigationToolbar(self.canvas, self)
            self.main_chart_layout.addWidget(self.nav_toolbar)
            
            # Create signals chart tab
            self.signals_chart_tab = QWidget()
            self.signals_chart_layout = QVBoxLayout(self.signals_chart_tab)
            
            # Create signals chart figure and canvas
            self.signals_figure = Figure(figsize=(8, 2))
            self.signals_canvas = FigureCanvas(self.signals_figure)
            self.signals_chart_layout.addWidget(self.signals_canvas)
            
            # Add navigation toolbar
            self.signals_nav_toolbar = NavigationToolbar(self.signals_canvas, self)
            self.signals_chart_layout.addWidget(self.signals_nav_toolbar)
            
            # Create backtest chart tab
            self.backtest_chart_tab = QWidget()
            self.backtest_chart_layout = QVBoxLayout(self.backtest_chart_tab)
            
            # Create backtest chart figure and canvas
            self.backtest_figure = Figure(figsize=(8, 4))
            self.backtest_canvas = FigureCanvas(self.backtest_figure)
            self.backtest_chart_layout.addWidget(self.backtest_canvas)
            
            # Add navigation toolbar
            self.backtest_nav_toolbar = NavigationToolbar(self.backtest_canvas, self)
            self.backtest_chart_layout.addWidget(self.backtest_nav_toolbar)
            
            # Create pattern recognition tab
            self.pattern_tab = QWidget()
            self.pattern_layout = QVBoxLayout(self.pattern_tab)
            
            # Create pattern chart figure and canvas
            self.pattern_figure = Figure(figsize=(8, 4))
            self.pattern_canvas = FigureCanvas(self.pattern_figure)
            self.pattern_layout.addWidget(self.pattern_canvas)
            
            # Add navigation toolbar
            self.pattern_nav_toolbar = NavigationToolbar(self.pattern_canvas, self)
            self.pattern_layout.addWidget(self.pattern_nav_toolbar)
            
            # Create wave analysis tab
            self.wave_tab = QWidget()
            self.wave_layout = QVBoxLayout(self.wave_tab)
            
            # Create wave chart figure and canvas
            self.wave_figure = Figure(figsize=(8, 4))
            self.wave_canvas = FigureCanvas(self.wave_figure)
            self.wave_layout.addWidget(self.wave_canvas)
            
            # Add navigation toolbar
            self.wave_nav_toolbar = NavigationToolbar(self.wave_canvas, self)
            self.wave_layout.addWidget(self.wave_nav_toolbar)
            
            # Create risk analysis tab
            self.risk_tab = QWidget()
            self.risk_layout = QVBoxLayout(self.risk_tab)
            
            # Create risk chart figure and canvas
            self.risk_figure = Figure(figsize=(8, 4))
            self.risk_canvas = FigureCanvas(self.risk_figure)
            self.risk_layout.addWidget(self.risk_canvas)
            
            # Add navigation toolbar
            self.risk_nav_toolbar = NavigationToolbar(self.risk_canvas, self)
            self.risk_layout.addWidget(self.risk_nav_toolbar)
            
            # Add tabs to tab widget
            self.chart_tabs.addTab(self.main_chart_tab, "主图表")
            self.chart_tabs.addTab(self.signals_chart_tab, "信号图表")
            self.chart_tabs.addTab(self.backtest_chart_tab, "回测结果")
            self.chart_tabs.addTab(self.pattern_tab, "模式识别")
            self.chart_tabs.addTab(self.wave_tab, "波浪分析")
            self.chart_tabs.addTab(self.risk_tab, "风险分析")
            
            # Add market sentiment widget
            self.market_sentiment_widget = MarketSentimentWidget(
                data_manager=self.data_manager,
                log_manager=self.log_manager
            )
            self.chart_tabs.addTab(self.market_sentiment_widget, "市场情绪")
            
            # Add fund flow widget
            self.fund_flow_widget = FundFlowWidget(data_manager=self.data_manager)
            self.chart_tabs.addTab(self.fund_flow_widget, "资金流向")
            
            # Add chart tabs to middle layout
            self.middle_layout.addWidget(self.chart_tabs)
            
            # Add to top splitter
            self.top_splitter.addWidget(self.middle_panel)
            
            # Set chart style
            plt.style.use('seaborn-v0_8-whitegrid')
            
        except Exception as e:
            self.log_message(f"创建中间面板失败: {str(e)}", "error")
            raise
            
    def save_chart(self):
        """Save current chart to file"""
        try:
            # Get current tab
            current_tab = self.chart_tabs.currentWidget()
            if not hasattr(current_tab, 'canvas'):
                return
                
            # Get file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存图表",
                "",
                "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)"
            )
            
            if file_path:
                # Save chart
                current_tab.canvas.figure.savefig(file_path)
                self.log_message(f"图表已保存到: {file_path}")
                
        except Exception as e:
            self.log_message(f"保存图表失败: {str(e)}", "error")
            
    def reset_chart_view(self):
        """Reset chart view to default"""
        try:
            # Get current tab
            current_tab = self.chart_tabs.currentWidget()
            if not hasattr(current_tab, 'canvas'):
                return
                
            # Reset view
            current_tab.canvas.figure.tight_layout()
            current_tab.canvas.draw()
            
        except Exception as e:
            self.log_message(f"重置图表视图失败: {str(e)}", "error")
            
    def toggle_chart_theme(self):
        """Toggle between light and dark chart theme"""
        try:
            # Get current style
            current_style = plt.style.available[0] if plt.style.available else 'default'
            
            # Toggle style
            if current_style == 'seaborn':
                plt.style.use('dark_background')
            else:
                plt.style.use('seaborn-v0_8-whitegrid')
                
            # Redraw all charts
            for i in range(self.chart_tabs.count()):
                tab = self.chart_tabs.widget(i)
                if hasattr(tab, 'canvas'):
                    tab.canvas.draw()
                    
        except Exception as e:
            self.log_message(f"切换图表主题失败: {str(e)}", "error")

    def create_right_panel(self):
        """Create right panel with analysis tools"""
        try:
            # Create right panel
            self.right_panel = QWidget()
            self.right_layout = QVBoxLayout(self.right_panel)
            
            # Create right tab widget
            self.right_tab = QTabWidget()
            self.right_layout.addWidget(self.right_tab)
            
            # Create strategy tab
            strategy_tab = QWidget()
            strategy_layout = QVBoxLayout(strategy_tab)
            
            # Add strategy combo
            strategy_label = QLabel("策略:")
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略",
                "KDJ策略", "自定义策略"
            ])
            strategy_layout.addWidget(strategy_label)
            strategy_layout.addWidget(self.strategy_combo)
            
            # Add analysis type combo
            analysis_label = QLabel("分析类型:")
            self.analysis_type_combo = QComboBox()
            self.analysis_type_combo.addItems([
                "技术分析", "基本面分析", "资金流向分析", "市场情绪分析"
            ])
            strategy_layout.addWidget(analysis_label)
            strategy_layout.addWidget(self.analysis_type_combo)
            
            # Add parameter controls
            self.param_controls = {}  # Reuse existing param_controls
            
            # Add backtest parameters
            backtest_group = QGroupBox("回测参数")
            backtest_layout = QFormLayout(backtest_group)
            
            # Initialize backtest controls with proper type conversion
            self.initial_capital = QDoubleSpinBox()
            self.initial_capital.setRange(1000.0, 10000000.0)
            self.initial_capital.setValue(100000.0)
            self.initial_capital.setSuffix(" 元")
            
            self.commission_rate = QDoubleSpinBox()
            self.commission_rate.setRange(0.0, 0.1)
            self.commission_rate.setValue(0.0003)
            self.commission_rate.setSuffix(" %")
            
            self.slippage = QDoubleSpinBox()
            self.slippage.setRange(0.0, 0.1)
            self.slippage.setValue(0.0001)
            self.slippage.setSuffix(" %")
            
            self.position_combo = QComboBox()
            self.position_combo.addItems(["固定仓位", "动态仓位"])
            
            self.position_size = QDoubleSpinBox()
            self.position_size.setRange(0.1, 1.0)
            self.position_size.setValue(0.5)
            self.position_size.setSuffix(" %")
            
            self.stop_loss = QDoubleSpinBox()
            self.stop_loss.setRange(0.0, 0.2)
            self.stop_loss.setValue(0.05)
            self.stop_loss.setSuffix(" %")
            
            self.take_profit = QDoubleSpinBox()
            self.take_profit.setRange(0.0, 0.5)
            self.take_profit.setValue(0.1)
            self.take_profit.setSuffix(" %")
            
            self.max_drawdown = QDoubleSpinBox()
            self.max_drawdown.setRange(0.0, 0.5)
            self.max_drawdown.setValue(0.2)
            self.max_drawdown.setSuffix(" %")
            
            self.risk_free_rate = QDoubleSpinBox()
            self.risk_free_rate.setRange(0.0, 0.1)
            self.risk_free_rate.setValue(0.03)
            self.risk_free_rate.setSuffix(" %")
            
            # Add controls to layout
            backtest_layout.addRow("初始资金:", self.initial_capital)
            backtest_layout.addRow("手续费率:", self.commission_rate)
            backtest_layout.addRow("滑点:", self.slippage)
            backtest_layout.addRow("仓位管理:", self.position_combo)
            backtest_layout.addRow("仓位大小:", self.position_size)
            backtest_layout.addRow("止损:", self.stop_loss)
            backtest_layout.addRow("止盈:", self.take_profit)
            backtest_layout.addRow("最大回撤:", self.max_drawdown)
            backtest_layout.addRow("无风险利率:", self.risk_free_rate)
            
            strategy_layout.addWidget(backtest_group)
            
            # Add stock screener
            self.stock_screener = StockScreenerWidget(
                data_manager=self.data_manager,
                log_manager=self.log_manager
            )
            strategy_layout.addWidget(self.stock_screener)
            
            # Add metric labels
            self.metric_labels = {
                "收益率": QLabel("0.00%"),
                "年化收益率": QLabel("0.00%"),
                "最大回撤": QLabel("0.00%"),
                "夏普比率": QLabel("0.00"),
                "胜率": QLabel("0.00%"),
                "盈亏比": QLabel("0.00")
            }
            
            # Add metrics to layout
            metrics_group = QGroupBox("策略指标")
            metrics_layout = QGridLayout(metrics_group)
            row = 0
            col = 0
            for name, label in self.metric_labels.items():
                metrics_layout.addWidget(QLabel(name), row, col)
                metrics_layout.addWidget(label, row, col + 1)
                col += 2
                if col >= 4:
                    col = 0
                    row += 1
            
            strategy_layout.addWidget(metrics_group)
            
            # Add strategy tab to right tab widget
            self.right_tab.addTab(strategy_tab, "策略")
            
            # Add right panel to top splitter
            self.top_splitter.addWidget(self.right_panel)
            
        except Exception as e:
            self.log_message(f"创建右侧面板失败: {str(e)}", "error")
            raise

    def optimize(self):
        """Optimize strategy parameters"""
        try:
            # Get current strategy and parameters
            strategy = self.strategy_combo.currentText()
            params = {name: control.value() for name, control in self.param_controls.items()}
            
            # Create optimization dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("参数优化")
            layout = QVBoxLayout(dialog)
            
            # Add progress bar
            progress = QProgressBar()
            progress.setRange(0, 100)
            layout.addWidget(progress)
            
            # Add optimization settings
            settings_group = QGroupBox("优化设置")
            settings_layout = QFormLayout(settings_group)
            
            # Add population size
            population_size = QSpinBox()
            population_size.setRange(10, 100)
            population_size.setValue(50)
            settings_layout.addRow("种群大小:", population_size)
            
            # Add generations
            generations = QSpinBox()
            generations.setRange(10, 100)
            generations.setValue(30)
            settings_layout.addRow("迭代次数:", generations)
            
            # Add optimization method
            method_combo = QComboBox()
            method_combo.addItems(["遗传算法", "粒子群", "模拟退火"])
            settings_layout.addRow("优化方法:", method_combo)
            
            layout.addWidget(settings_group)
            
            # Add buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            # Show dialog
            if dialog.exec_() == QDialog.Accepted:
                # Start optimization
                self.log_message("开始参数优化...")
                
                # TODO: Implement optimization logic
                
                self.log_message("参数优化完成")
                
        except Exception as e:
            self.log_message(f"参数优化失败: {str(e)}", "error")

    def update_metrics(self, metrics: dict):
        """Update performance metrics display
        
        Args:
            metrics: Dictionary of metric names and values
        """
        try:
            for name, value in metrics.items():
                if name in self.metric_labels:
                    if isinstance(value, float):
                        self.metric_labels[name].setText(f"{value:.2%}")
                    else:
                        self.metric_labels[name].setText(str(value))
        except Exception as e:
            self.log_message(f"更新性能指标失败: {str(e)}", "error")

    def create_controls(self, layout):
        """Create control buttons"""
        try:
            # Create parameter controls
            self.param_controls = {}
            params = {
                "均线周期": (10, 100, 20),  # 整数
                "MACD快线": (5, 50, 12),    # 整数
                "MACD慢线": (10, 100, 26),  # 整数
                "MACD信号线": (2, 20, 9),   # 整数
                "RSI周期": (5, 30, 14),     # 整数
                "布林带周期": (10, 100, 20), # 整数
                "布林带标准差": (1.0, 3.0, 2.0),  # 浮点数
                "自适应周期": (5, 50, 20),   # 整数
                "自适应阈值": (0.1, 1.0, 0.5),  # 浮点数
                "多因子数量": (3, 20, 5)     # 整数
            }
            
            for name, value in params.items():
                if isinstance(value, tuple):
                    if any(isinstance(x, float) for x in value):
                        spinbox = QDoubleSpinBox()
                        spinbox.setDecimals(2)
                        spinbox.setRange(float(value[0]), float(value[1]))
                        spinbox.setValue(float(value[2]))
                    else:
                        spinbox = QSpinBox()
                        spinbox.setRange(int(value[0]), int(value[1]))
                        spinbox.setValue(int(value[2]))
                    self.param_controls[name] = spinbox
                    layout.addRow(name + ":", spinbox)
                else:
                    combo = QComboBox()
                    combo.addItems(value)
                    self.param_controls[name] = combo
                    layout.addRow(name + ":", combo)
            
            # Create backtest settings
            backtest_group = QGroupBox("回测设置")
            backtest_layout = QFormLayout(backtest_group)
            
            # Add backtest controls with proper type conversion
            self.initial_capital = QDoubleSpinBox()
            self.initial_capital.setDecimals(2)
            self.initial_capital.setRange(1000.0, 1000000.0)
            self.initial_capital.setValue(100000.0)
            self.initial_capital.setSuffix(" 元")
            backtest_layout.addRow("初始资金:", self.initial_capital)
            
            self.commission_rate = QDoubleSpinBox()
            self.commission_rate.setDecimals(4)
            self.commission_rate.setRange(0.0, 0.01)
            self.commission_rate.setValue(0.0003)
            self.commission_rate.setSuffix(" %")
            backtest_layout.addRow("佣金率:", self.commission_rate)
            
            self.slippage = QDoubleSpinBox()
            self.slippage.setDecimals(4)
            self.slippage.setRange(0.0, 0.01)
            self.slippage.setValue(0.0001)
            self.slippage.setSuffix(" %")
            backtest_layout.addRow("滑点:", self.slippage)
            
            # Add position sizing controls
            position_layout = QHBoxLayout()
            position_label = QLabel("仓位管理:")
            self.position_combo = QComboBox()
            self.position_combo.addItems(["固定仓位", "动态仓位", "风险平价", "凯利公式"])
            position_layout.addWidget(position_label)
            position_layout.addWidget(self.position_combo)
            backtest_layout.addRow(position_layout)
            
            self.position_size = QDoubleSpinBox()
            self.position_size.setDecimals(2)
            self.position_size.setRange(0.1, 1.0)
            self.position_size.setValue(0.5)
            self.position_size.setSuffix(" %")
            backtest_layout.addRow("仓位比例:", self.position_size)
            
            layout.addWidget(backtest_group)
            
            # Create risk management group
            risk_group = QGroupBox("风险管理")
            risk_layout = QFormLayout(risk_group)
            
            # Add risk controls with proper type conversion
            self.stop_loss = QDoubleSpinBox()
            self.stop_loss.setDecimals(3)
            self.stop_loss.setRange(0.0, 0.1)
            self.stop_loss.setValue(0.05)
            self.stop_loss.setSuffix(" %")
            risk_layout.addRow("止损比例:", self.stop_loss)
            
            self.take_profit = QDoubleSpinBox()
            self.take_profit.setDecimals(3)
            self.take_profit.setRange(0.0, 0.2)
            self.take_profit.setValue(0.1)
            self.take_profit.setSuffix(" %")
            risk_layout.addRow("止盈比例:", self.take_profit)
            
            self.max_drawdown = QDoubleSpinBox()
            self.max_drawdown.setDecimals(3)
            self.max_drawdown.setRange(0.0, 0.3)
            self.max_drawdown.setValue(0.15)
            self.max_drawdown.setSuffix(" %")
            risk_layout.addRow("最大回撤:", self.max_drawdown)
            
            self.risk_free_rate = QDoubleSpinBox()
            self.risk_free_rate.setDecimals(3)
            self.risk_free_rate.setRange(0.0, 0.1)
            self.risk_free_rate.setValue(0.03)
            self.risk_free_rate.setSuffix(" %")
            risk_layout.addRow("无风险利率:", self.risk_free_rate)
            
            layout.addWidget(risk_group)
            
        except Exception as e:
            self.log_message(f"创建控制按钮失败: {str(e)}", "error")
            raise

    def on_period_changed(self, period: str):
        """处理周期变更事件
        
        Args:
            period: 周期名称
        """
        try:
            # 转换周期
            period_map = {
                '日线': 'D',
                '周线': 'W',
                '月线': 'M',
                '60分钟': '60',
                '30分钟': '30',
                '15分钟': '15',
                '5分钟': '5',
                '分时': '1'
            }
            
            if period in period_map:
                self.current_period = period_map[period]
                # 更新图表
                self.update_chart()
                # 记录日志
                self.log_message(f"已切换周期为: {period}")
                
        except Exception as e:
            self.log_message(f"切换周期失败: {str(e)}", "error")

    def on_strategy_changed(self, strategy: str) -> None:
        """处理策略变化事件
        
        Args:
            strategy: 策略名称
        """
        try:
            # 策略映射
            strategy_map = {
                '均线策略': 'ma_strategy',
                'MACD策略': 'macd_strategy',
                'RSI策略': 'rsi_strategy',
                '布林带策略': 'boll_strategy',
                'KDJ策略': 'kdj_strategy'
            }
            
            if strategy in strategy_map:
                self.current_strategy = strategy_map[strategy]
                self.update_strategy()
                self.log_manager.log(f"策略已更改为: {strategy}", "INFO")
                
        except Exception as e:
            self.log_manager.log(f"更改策略失败: {str(e)}", "ERROR")

    def update_strategy(self) -> None:
        """更新当前策略"""
        try:
            if not self.current_stock:
                return
                
            # 获取当前股票数据
            k_data = self.data_manager.get_k_data(self.current_stock, self.current_period)
            if k_data.empty:
                self.log_manager.log(f"获取股票数据失败: {self.current_stock}", "ERROR")
                return
                
            # 根据当前策略更新图表
            if self.current_strategy == 'ma_strategy':
                self.update_ma_strategy(k_data)
            elif self.current_strategy == 'macd_strategy':
                self.update_macd_strategy(k_data)
            elif self.current_strategy == 'rsi_strategy':
                self.update_rsi_strategy(k_data)
            elif self.current_strategy == 'boll_strategy':
                self.update_boll_strategy(k_data)
            elif self.current_strategy == 'kdj_strategy':
                self.update_kdj_strategy(k_data)
                
            # 更新图表
            self.update_chart()
            
        except Exception as e:
            self.log_manager.log(f"更新策略失败: {str(e)}", "ERROR")

    def load_favorites(self):
        """加载收藏的股票列表"""
        try:
            # 创建配置目录（如果不存在）
            os.makedirs('config', exist_ok=True)
            
            # 尝试从文件加载收藏列表
            favorites_file = 'config/favorites.json'
            if os.path.exists(favorites_file):
                with open(favorites_file, 'r', encoding='utf-8') as f:
                    self.favorites = set(json.load(f))
                self.log_message("已加载收藏列表")
            else:
                self.favorites = set()
                self.log_message("未找到收藏列表，已创建新的收藏集")
                
        except Exception as e:
            self.favorites = set()
            self.log_message(f"加载收藏列表失败: {str(e)}", "error")
            
    def save_favorites(self):
        """保存收藏的股票列表"""
        try:
            # 确保配置目录存在
            os.makedirs('config', exist_ok=True)
            
            # 保存收藏列表到文件
            favorites_file = 'config/favorites.json'
            with open(favorites_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.favorites), f, ensure_ascii=False, indent=2)
            self.log_message("已保存收藏列表")
            
        except Exception as e:
            self.log_message(f"保存收藏列表失败: {str(e)}", "error")
            
    def toggle_favorite(self):
        """切换当前选中股票的收藏状态"""
        try:
            # 获取当前选中的股票
            selected_items = self.stock_list.selectedItems()
            if not selected_items:
                self.log_message("请先选择一只股票", "warning")
                return
                
            stock_item = selected_items[0]
            stock_code = stock_item.text().split()[0]  # 获取股票代码
            
            # 切换收藏状态
            if stock_code in self.favorites:
                self.favorites.remove(stock_code)
                self.log_message(f"已取消收藏: {stock_code}")
            else:
                self.favorites.add(stock_code)
                self.log_message(f"已收藏: {stock_code}")
                
            # 保存收藏列表
            self.save_favorites()
            
            # 更新股票列表显示
            self.update_stock_list_ui()
            
        except Exception as e:
            self.log_message(f"切换收藏状态失败: {str(e)}", "error")
            
    def update_stock_list_ui(self):
        """更新股票列表的显示，包括收藏状态"""
        try:
            # 保存当前选中的股票
            selected_items = self.stock_list.selectedItems()
            selected_stock = selected_items[0].text() if selected_items else None
            
            # 清空列表
            self.stock_list.clear()
            
            # 重新添加所有股票，并标记收藏状态
            for stock in self.stock_list_cache:
                item = QListWidgetItem(stock)
                if stock.split()[0] in self.favorites:
                    item.setText(f"★ {stock}")
                self.stock_list.addItem(item)
                
            # 恢复选中状态
            if selected_stock:
                items = self.stock_list.findItems(selected_stock, Qt.MatchExactly)
                if items:
                    self.stock_list.setCurrentItem(items[0])
                    
        except Exception as e:
            self.log_message(f"更新股票列表显示失败: {str(e)}", "error")

    def log_message(self, message: str, level: str = "info") -> None:
        """处理日志消息
        
        Args:
            message: 日志消息内容
            level: 日志级别，可选值为 "info", "warning", "error", "debug"
        """
        try:
            # 将日志级别转换为大写
            level = level.upper()
            
            # 根据日志级别设置文本颜色
            if level == "ERROR":
                color = "#FF0000"  # 红色
            elif level == "WARNING":
                color = "#FFA500"  # 橙色
            elif level == "DEBUG":
                color = "#808080"  # 灰色
            else:
                color = "#000000"  # 黑色
                
            # 格式化日志消息
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f'<span style="color:{color}">[{timestamp}] [{level}] {message}</span>'
            
            # 将消息添加到日志文本框
            if hasattr(self, 'log_text'):
                self.log_text.append(formatted_message)
                
                # 滚动到底部
                self.log_text.verticalScrollBar().setValue(
                    self.log_text.verticalScrollBar().maximum()
                )
            else:
                print(f"[{timestamp}] [{level}] {message}")
            
            # 如果日志级别为错误，显示错误对话框
            if level == "ERROR":
                QMessageBox.critical(self, "错误", message)
                
        except Exception as e:
            print(f"记录日志失败: {str(e)}")

    def clear_log(self) -> None:
        """清除日志内容"""
        try:
            self.log_text.clear()
            self.log_message("日志已清除", "info")
        except Exception as e:
            self.log_message(f"清除日志失败: {str(e)}", "error")

    def handle_performance_alert(self, message: str) -> None:
        """处理性能警告，优化警告处理"""
        try:
            # 记录警告日志
            self.log_message(message, "warning")
            
            # 显示警告对话框
            alert_dialog = QMessageBox(self)
            alert_dialog.setWindowTitle("性能警告")
            alert_dialog.setIcon(QMessageBox.Warning)
            alert_dialog.setText("性能警告")
            alert_dialog.setInformativeText(message)
            alert_dialog.setStandardButtons(QMessageBox.Ok)
            alert_dialog.exec_()
            
            # 根据警告类型采取相应措施
            if "CPU" in message:
                # 降低更新频率
                if hasattr(self, 'performance_timer'):
                    self.performance_timer.setInterval(2000)  # 降低到2秒
            elif "内存" in message:
                # 清理内存
                self.cleanup_memory()
            elif "响应" in message:
                # 优化UI更新
                self.optimize_ui_updates()
            
        except Exception as e:
            self.log_message(f"处理性能警告失败: {str(e)}", "error")

    def optimize_ui_updates(self):
        """优化UI更新性能"""
        try:
            # 暂停不必要的更新
            if hasattr(self, 'chart_widget'):
                self.chart_widget.setUpdatesEnabled(False)
                
            # 批量更新UI
            QApplication.processEvents()
            
            # 恢复更新
            if hasattr(self, 'chart_widget'):
                self.chart_widget.setUpdatesEnabled(True)
                
            self.log_message("UI更新已优化", "info")
            
        except Exception as e:
            self.log_message(f"优化UI更新失败: {str(e)}", "error")

    def handle_exception(self, exception: Exception) -> None:
        """处理异常，优化错误处理"""
        try:
            # 获取异常详细信息
            error_type = type(exception).__name__
            error_message = str(exception)
            error_traceback = traceback.format_exc()
            
            # 记录错误日志
            self.log_message(f"发生异常: {error_type}", "error")
            self.log_message(f"错误信息: {error_message}", "error")
            self.log_message(f"错误堆栈: {error_traceback}", "error")
            
            # 显示错误对话框
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("错误")
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setText(f"发生错误: {error_type}")
            error_dialog.setInformativeText(error_message)
            error_dialog.setDetailedText(error_traceback)
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
            
            # 如果错误严重，尝试恢复系统状态
            if isinstance(exception, (MemoryError, SystemError)):
                self.cleanup_memory()
                self.log_message("系统已尝试恢复", "info")
            
        except Exception as e:
            # 如果错误处理本身出错，至少打印到控制台
            print(f"错误处理失败: {str(e)}")
            print(f"原始错误: {str(exception)}")

    def show_advanced_search_dialog(self):
        """显示高级搜索对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("高级搜索")
            layout = QVBoxLayout(dialog)
            
            # 创建搜索条件组
            conditions_group = QGroupBox("搜索条件")
            conditions_layout = QFormLayout(conditions_group)
            
            # 添加搜索条件控件
            self.advanced_search_controls = {}
            
            # 股票代码
            code_edit = QLineEdit()
            code_edit.setPlaceholderText("输入股票代码")
            conditions_layout.addRow("股票代码:", code_edit)
            self.advanced_search_controls["code"] = code_edit
            
            # 股票名称
            name_edit = QLineEdit()
            name_edit.setPlaceholderText("输入股票名称")
            conditions_layout.addRow("股票名称:", name_edit)
            self.advanced_search_controls["name"] = name_edit
            
            # 市场
            market_combo = QComboBox()
            market_combo.addItems(["全部", "A股", "港股", "美股"])
            conditions_layout.addRow("市场:", market_combo)
            self.advanced_search_controls["market"] = market_combo
            
            # 行业
            industry_combo = QComboBox()
            industry_combo.addItems(["全部", "金融", "科技", "消费", "医药", "能源", "工业", "地产"])
            conditions_layout.addRow("行业:", industry_combo)
            self.advanced_search_controls["industry"] = industry_combo
            
            # 市值范围
            market_cap_layout = QHBoxLayout()
            min_cap = QDoubleSpinBox()
            min_cap.setRange(0, 1000000)
            min_cap.setSuffix(" 亿")
            max_cap = QDoubleSpinBox()
            max_cap.setRange(0, 1000000)
            max_cap.setSuffix(" 亿")
            market_cap_layout.addWidget(min_cap)
            market_cap_layout.addWidget(QLabel("至"))
            market_cap_layout.addWidget(max_cap)
            conditions_layout.addRow("市值范围:", market_cap_layout)
            self.advanced_search_controls["min_cap"] = min_cap
            self.advanced_search_controls["max_cap"] = max_cap
            
            # 添加条件组到布局
            layout.addWidget(conditions_group)
            
            # 添加按钮
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 获取搜索条件
                search_conditions = {
                    "code": code_edit.text(),
                    "name": name_edit.text(),
                    "market": market_combo.currentText(),
                    "industry": industry_combo.currentText(),
                    "min_cap": min_cap.value(),
                    "max_cap": max_cap.value()
                }
                
                # 执行搜索
                self.perform_advanced_search(search_conditions)
                
        except Exception as e:
            self.log_message(f"显示高级搜索对话框失败: {str(e)}", "error")

    def perform_advanced_search(self, conditions: dict) -> None:
        """执行高级搜索
        
        Args:
            conditions: 搜索条件字典
        """
        try:
            # 清空当前列表
            self.stock_list.clear()
            
            # 获取所有股票
            all_stocks = sm.get_stock_list()
            
            # 过滤股票
            filtered_stocks = []
            for stock in all_stocks:
                # 检查股票代码
                if conditions["code"] and conditions["code"] not in stock["code"]:
                    continue
                    
                # 检查股票名称
                if conditions["name"] and conditions["name"] not in stock["name"]:
                    continue
                    
                # 检查市场
                if conditions["market"] != "全部" and conditions["market"] != stock["market"]:
                    continue
                    
                # 检查行业
                if conditions["industry"] != "全部" and conditions["industry"] != stock["industry"]:
                    continue
                    
                # 检查市值
                if stock["market_cap"] < conditions["min_cap"] or stock["market_cap"] > conditions["max_cap"]:
                    continue
                    
                filtered_stocks.append(stock)
                
            # 更新股票列表
            for stock in filtered_stocks:
                item = QListWidgetItem(f"{stock['code']} {stock['name']}")
                if stock["code"] in self.favorites:
                    item.setText(f"★ {item.text()}")
                self.stock_list.addItem(item)
                
            self.log_message(f"找到 {len(filtered_stocks)} 只符合条件的股票", "info")
            
        except Exception as e:
            self.log_message(f"执行高级搜索失败: {str(e)}", "error")

    def on_stock_selected(self) -> None:
        """处理股票选择事件"""
        try:
            # 获取选中的股票
            selected_items = self.stock_list.selectedItems()
            if not selected_items:
                return
                
            # 获取股票代码
            stock_text = selected_items[0].text()
            if stock_text.startswith("★"):
                stock_text = stock_text[2:]
            stock_code = stock_text.split()[0]
            
            # 更新当前股票
            self.current_stock = stock_code
            
            # 更新图表
            self.update_chart()
            
            # 更新指标
            self.update_indicators()
            
            # 记录日志
            self.log_message(f"已选择股票: {stock_code}")
            
        except Exception as e:
            self.log_message(f"处理股票选择事件失败: {str(e)}", "error")

    def on_indicators_changed(self) -> None:
        """处理指标变化事件"""
        try:
            # 获取选中的指标
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                return
                
            # 更新指标参数
            self.show_indicator_params_dialog()
            
            # 更新图表
            self.update_chart()
            
            # 记录日志
            self.log_message("指标已更新")
            
        except Exception as e:
            self.log_message(f"处理指标变化事件失败: {str(e)}", "error")

    def show_indicator_params_dialog(self) -> None:
        """显示指标参数设置对话框，优化性能和用户体验"""
        try:
            # 获取选中的指标
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                self.log_message("请先选择指标", "warning")
                return
                
            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("指标参数设置")
            dialog.setStyleSheet("""
                QDialog {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    background-color: #f0f0f0;
                }
                QGroupBox {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                    background-color: white;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
                QSpinBox, QDoubleSpinBox {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                    padding: 5px;
                    background-color: white;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                }
                QLabel {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                }
                QPushButton {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                    padding: 5px 10px;
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
            
            layout = QVBoxLayout(dialog)
            
            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            # 存储参数控件
            self.param_controls = {}
            
            # 为每个选中的指标创建参数设置
            for item in selected_items:
                indicator = item.text()
                
                # 创建指标组
                group = QGroupBox(indicator)
                group_layout = QFormLayout(group)
                
                # 根据指标类型添加参数控件
                if "MA" in indicator:
                    # MA参数
                    ma_period = QSpinBox()
                    ma_period.setRange(5, 250)
                    ma_period.setValue(20)
                    group_layout.addRow("周期:", ma_period)
                    self.param_controls[f"{indicator}_period"] = ma_period
                    
                elif "MACD" in indicator:
                    # MACD参数
                    fast_period = QSpinBox()
                    fast_period.setRange(5, 50)
                    fast_period.setValue(12)
                    group_layout.addRow("快线周期:", fast_period)
                    self.param_controls[f"{indicator}_fast"] = fast_period
                    
                    slow_period = QSpinBox()
                    slow_period.setRange(10, 100)
                    slow_period.setValue(26)
                    group_layout.addRow("慢线周期:", slow_period)
                    self.param_controls[f"{indicator}_slow"] = slow_period
                    
                    signal_period = QSpinBox()
                    signal_period.setRange(2, 20)
                    signal_period.setValue(9)
                    group_layout.addRow("信号线周期:", signal_period)
                    self.param_controls[f"{indicator}_signal"] = signal_period
                    
                elif "RSI" in indicator:
                    # RSI参数
                    rsi_period = QSpinBox()
                    rsi_period.setRange(5, 30)
                    rsi_period.setValue(14)
                    group_layout.addRow("周期:", rsi_period)
                    self.param_controls[f"{indicator}_period"] = rsi_period
                    
                elif "BOLL" in indicator:
                    # 布林带参数
                    boll_period = QSpinBox()
                    boll_period.setRange(10, 100)
                    boll_period.setValue(20)
                    group_layout.addRow("周期:", boll_period)
                    self.param_controls[f"{indicator}_period"] = boll_period
                    
                    boll_std = QDoubleSpinBox()
                    boll_std.setRange(1.0, 3.0)
                    boll_std.setValue(2.0)
                    boll_std.setDecimals(1)
                    group_layout.addRow("标准差倍数:", boll_std)
                    self.param_controls[f"{indicator}_std"] = boll_std
                    
                scroll_layout.addWidget(group)
                
            # 设置滚动区域内容
            scroll.setWidget(scroll_content)
            layout.addWidget(scroll)
            
            # 添加按钮
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 更新指标参数
                self.update_indicators()
                
        except Exception as e:
            self.log_message(f"显示指标参数设置对话框失败: {str(e)}", "error")

    def create_bottom_panel(self):
        """Create bottom panel with logs and performance"""
        try:
            # Create bottom panel
            self.bottom_panel = QWidget()
            self.bottom_layout = QVBoxLayout(self.bottom_panel)
            
            # Create log group
            log_group = QGroupBox("日志")
            log_layout = QVBoxLayout(log_group)
            
            # Add log text to layout
            log_layout.addWidget(self.log_text)
            
            # Create log controls
            log_controls = QHBoxLayout()
            
            # Add log level selector
            log_level_label = QLabel("日志级别:")
            self.log_level_combo = QComboBox()
            self.log_level_combo.addItems(["全部", "信息", "警告", "错误", "调试"])
            self.log_level_combo.currentTextChanged.connect(self.filter_logs)
            log_controls.addWidget(log_level_label)
            log_controls.addWidget(self.log_level_combo)
            
            # Add log search
            self.log_search = QLineEdit()
            self.log_search.setPlaceholderText("搜索日志...")
            self.log_search.textChanged.connect(self.search_logs)
            log_controls.addWidget(self.log_search)
            
            # Add clear button
            clear_button = QPushButton("清除")
            clear_button.clicked.connect(self.clear_log)
            log_controls.addWidget(clear_button)
            
            # Add export button
            export_button = QPushButton("导出")
            export_button.clicked.connect(self.export_logs)
            log_controls.addWidget(export_button)
            
            log_layout.addLayout(log_controls)
            
            # Add log group to bottom layout
            self.bottom_layout.addWidget(log_group)
            
            # Create performance group
            performance_group = QGroupBox("性能监控")
            performance_layout = QVBoxLayout(performance_group)
            
            # Add performance metrics
            self.performance_text = QTextEdit()
            self.performance_text.setReadOnly(True)
            self.performance_text.setMaximumHeight(100)
            performance_layout.addWidget(self.performance_text)
            
            # Add performance group to bottom layout
            self.bottom_layout.addWidget(performance_group)
            
            # Add bottom panel to bottom splitter
            self.bottom_splitter.addWidget(self.bottom_panel)
            
        except Exception as e:
            self.log_message(f"创建底部面板失败: {str(e)}", "error")
            raise

    def filter_logs(self, level: str) -> None:
        """根据日志级别过滤日志
        
        Args:
            level: 日志级别
        """
        try:
            # 获取所有日志内容
            all_logs = self.log_text.toPlainText().split('\n')
            
            # 清空日志显示
            self.log_text.clear()
            
            # 根据级别过滤日志
            level_map = {
                "全部": lambda x: True,
                "信息": lambda x: "[INFO]" in x,
                "警告": lambda x: "[WARNING]" in x,
                "错误": lambda x: "[ERROR]" in x,
                "调试": lambda x: "[DEBUG]" in x
            }
            
            # 显示过滤后的日志
            for log in all_logs:
                if level_map[level](log):
                    self.log_text.append(log)
                    
        except Exception as e:
            print(f"过滤日志失败: {str(e)}")
        
    def search_logs(self, text: str) -> None:
        """搜索日志内容
        
        Args:
            text: 搜索文本
        """
        try:
            # 获取所有日志内容
            all_logs = self.log_text.toPlainText().split('\n')
            
            # 清空日志显示
            self.log_text.clear()
            
            # 显示匹配的日志
            for log in all_logs:
                if text.lower() in log.lower():
                    self.log_text.append(log)
                    
        except Exception as e:
            print(f"搜索日志失败: {str(e)}")
        
    def export_logs(self) -> None:
        """导出日志到文件"""
        try:
            # 获取文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                # 获取日志内容
                logs = self.log_text.toPlainText()
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(logs)
                    
                self.log_message(f"日志已导出到: {file_path}")
                
        except Exception as e:
            self.log_message(f"导出日志失败: {str(e)}", "error")

    def update_stock_list(self) -> None:
        """更新股票列表，优化性能"""
        try:
            # 使用线程池异步更新股票列表
            def update_list():
                try:
                    # 获取所有股票
                    all_stocks = sm.get_stock_list()
                    
                    # 使用弱引用避免内存泄漏
                    stock_list_ref = weakref.ref(self.stock_list)
                    stock_list_cache_ref = weakref.ref(self.stock_list_cache)
                    
                    if stock_list_ref() and stock_list_cache_ref():
                        # 清空当前列表
                        stock_list_ref().clear()
                        stock_list_cache_ref().clear()
                        
                        # 添加股票到列表
                        for stock in all_stocks:
                            stock_text = f"{stock['code']} {stock['name']}"
                            stock_list_cache_ref().append(stock_text)
                            
                            # 创建列表项
                            item = QListWidgetItem(stock_text)
                            
                            # 如果是收藏的股票，添加星号标记
                            if stock['code'] in self.favorites:
                                item.setText(f"★ {stock_text}")
                                
                            stock_list_ref().addItem(item)
                            
                        # 更新UI显示
                        self.update_stock_list_ui()
                        
                        # 记录日志
                        self.log_message(f"已更新股票列表，共 {len(all_stocks)} 只股票", "info")
                        
                except Exception as e:
                    self.log_message(f"更新股票列表失败: {str(e)}", "error")
                    
            # 使用线程池执行更新
            self.thread_pool.start(update_list)
            
        except Exception as e:
            self.log_message(f"更新股票列表失败: {str(e)}", "error")

    def export_stock_list(self):
        """导出股票列表到文件"""
        try:
            # 获取保存文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出股票列表",
                "",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;Text Files (*.txt)"
            )
            
            if not file_path:
                return
                
            # 获取股票列表数据
            stocks = []
            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                text = item.text()
                if text.startswith("★"):
                    text = text[2:]  # 移除收藏标记
                code, name = text.split(maxsplit=1)
                is_favorite = "★" in item.text()
                stocks.append({
                    "代码": code,
                    "名称": name,
                    "收藏": "是" if is_favorite else "否"
                })
            
            # 创建DataFrame
            df = pd.DataFrame(stocks)
            
            # 根据文件类型导出
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:  # txt
                with open(file_path, 'w', encoding='utf-8') as f:
                    for stock in stocks:
                        f.write(f"{stock['代码']}\t{stock['名称']}\t{stock['收藏']}\n")
            
            self.log_message(f"股票列表已导出到: {file_path}")
            
        except Exception as e:
            self.log_message(f"导出股票列表失败: {str(e)}", "error")

    def update_indicators(self) -> None:
        """更新指标参数并刷新图表，优化性能"""
        try:
            # 获取选中的指标
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                return
                
            # 使用线程池异步更新指标
            def update_indicators_async():
                try:
                    # 更新每个指标的参数
                    for item in selected_items:
                        indicator = item.text()
                        
                        if "MA" in indicator:
                            # 更新MA参数
                            period = self.param_controls[f"{indicator}_period"].value()
                            self.chart_widget.update_ma(period)
                            
                        elif "MACD" in indicator:
                            # 更新MACD参数
                            fast = self.param_controls[f"{indicator}_fast"].value()
                            slow = self.param_controls[f"{indicator}_slow"].value()
                            signal = self.param_controls[f"{indicator}_signal"].value()
                            self.chart_widget.update_macd(fast, slow, signal)
                            
                        elif "RSI" in indicator:
                            # 更新RSI参数
                            period = self.param_controls[f"{indicator}_period"].value()
                            self.chart_widget.update_rsi(period)
                            
                        elif "BOLL" in indicator:
                            # 更新布林带参数
                            period = self.param_controls[f"{indicator}_period"].value()
                            std = self.param_controls[f"{indicator}_std"].value()
                            self.chart_widget.update_boll(period, std)
                            
                    # 刷新图表
                    self.chart_widget.update_chart()
                    self.log_message("指标参数已更新", "info")
                    
                except Exception as e:
                    self.log_message(f"更新指标参数失败: {str(e)}", "error")
                
            # 使用线程池执行更新
            self.thread_pool.start(update_indicators_async)
            
        except Exception as e:
            self.log_message(f"更新指标参数失败: {str(e)}", "error")

    def save_indicator_combination(self) -> None:
        """保存当前选中的指标组合
        
        将当前选中的指标及其参数保存到配置文件中，方便后续使用
        """
        try:
            # 获取选中的指标
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                self.log_message("请先选择要保存的指标", "warning")
                return
                
            # 获取组合名称
            name, ok = QInputDialog.getText(
                self,
                "保存指标组合",
                "请输入组合名称:",
                QLineEdit.Normal,
                ""
            )
            
            if not ok or not name:
                return
                
            # 收集指标参数
            indicators = []
            for item in selected_items:
                indicator = item.text()
                params = {}
                
                if "MA" in indicator:
                    params = {
                        "type": "MA",
                        "period": self.param_controls[f"{indicator}_period"].value()
                    }
                elif "MACD" in indicator:
                    params = {
                        "type": "MACD",
                        "fast": self.param_controls[f"{indicator}_fast"].value(),
                        "slow": self.param_controls[f"{indicator}_slow"].value(),
                        "signal": self.param_controls[f"{indicator}_signal"].value()
                    }
                elif "RSI" in indicator:
                    params = {
                        "type": "RSI",
                        "period": self.param_controls[f"{indicator}_period"].value()
                    }
                elif "BOLL" in indicator:
                    params = {
                        "type": "BOLL",
                        "period": self.param_controls[f"{indicator}_period"].value(),
                        "std": self.param_controls[f"{indicator}_std"].value()
                    }
                    
                indicators.append({
                    "name": indicator,
                    "params": params
                })
                
            # 创建组合对象
            combination = {
                "name": name,
                "indicators": indicators,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 加载现有组合
            combinations = []
            combinations_file = 'config/indicator_combinations.json'
            if os.path.exists(combinations_file):
                with open(combinations_file, 'r', encoding='utf-8') as f:
                    combinations = json.load(f)
                    
            # 添加新组合
            combinations.append(combination)
            
            # 保存组合
            os.makedirs('config', exist_ok=True)
            with open(combinations_file, 'w', encoding='utf-8') as f:
                json.dump(combinations, f, ensure_ascii=False, indent=2)
                
            self.log_message(f"已保存指标组合: {name}")
            
        except Exception as e:
            self.log_message(f"保存指标组合失败: {str(e)}", "error")

    def zoom_in(self) -> None:
        """放大图表"""
        try:
            # 获取当前图表
            current_tab = self.chart_tabs.currentWidget()
            if not hasattr(current_tab, 'canvas'):
                return
                
            # 获取当前坐标轴
            ax = current_tab.canvas.figure.axes[0]
            
            # 计算新的范围
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # 缩小20%
            x_range = x_max - x_min
            y_range = y_max - y_min
            ax.set_xlim(x_min + x_range * 0.1, x_max - x_range * 0.1)
            ax.set_ylim(y_min + y_range * 0.1, y_max - y_range * 0.1)
            
            # 更新图表
            current_tab.canvas.draw()
            
        except Exception as e:
            self.log_message(f"放大图表失败: {str(e)}", "error")
            
    def zoom_out(self) -> None:
        """缩小图表"""
        try:
            # 获取当前图表
            current_tab = self.chart_tabs.currentWidget()
            if not hasattr(current_tab, 'canvas'):
                return
                
            # 获取当前坐标轴
            ax = current_tab.canvas.figure.axes[0]
            
            # 计算新的范围
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            
            # 放大20%
            x_range = x_max - x_min
            y_range = y_max - y_min
            ax.set_xlim(x_min - x_range * 0.1, x_max + x_range * 0.1)
            ax.set_ylim(y_min - y_range * 0.1, y_max + y_range * 0.1)
            
            # 更新图表
            current_tab.canvas.draw()
            
        except Exception as e:
            self.log_message(f"缩小图表失败: {str(e)}", "error")
            
    def reset_zoom(self) -> None:
        """重置图表缩放"""
        try:
            # 获取当前图表
            current_tab = self.chart_tabs.currentWidget()
            if not hasattr(current_tab, 'canvas'):
                return
                
            # 获取当前坐标轴
            ax = current_tab.canvas.figure.axes[0]
            
            # 重置范围
            ax.relim()
            ax.autoscale_view()
            
            # 更新图表
            current_tab.canvas.draw()
            
        except Exception as e:
            self.log_message(f"重置图表缩放失败: {str(e)}", "error")

    def show_calculator(self) -> None:
        """显示计算器，优化UI和功能"""
        try:
            # 创建计算器对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("计算器")
            dialog.setStyleSheet("""
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
            
            # 创建主布局
            main_layout = QVBoxLayout(dialog)
            
            # 创建显示框
            display = QLineEdit()
            display.setReadOnly(True)
            display.setAlignment(Qt.AlignRight)
            display.setStyleSheet("font-size: 20px;")
            main_layout.addWidget(display)
            
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
                button.clicked.connect(lambda checked, t=text: self.calculator_button_clicked(t, display))
                grid.addWidget(button, i // 4, i % 4)
                
            # 添加清除按钮
            clear_button = QPushButton("C")
            clear_button.setStyleSheet("font-size: 16px;")
            clear_button.clicked.connect(lambda: display.clear())
            grid.addWidget(clear_button, 4, 0, 1, 2)
            
            # 添加退格按钮
            backspace_button = QPushButton("←")
            backspace_button.setStyleSheet("font-size: 16px;")
            backspace_button.clicked.connect(lambda: display.backspace())
            grid.addWidget(backspace_button, 4, 2, 1, 2)
            
            # 显示对话框
            dialog.exec_()
            
        except Exception as e:
            self.log_message(f"显示计算器失败: {str(e)}", "error")

    def calculator_button_clicked(self, text: str, display: QLineEdit) -> None:
        """处理计算器按钮点击事件
        
        Args:
            text: 按钮文本
            display: 显示框
        """
        try:
            if text == '=':
                # 计算结果
                try:
                    result = eval(display.text())
                    display.setText(str(result))
                except:
                    display.setText("错误")
            else:
                # 添加文本
                display.insert(text)
                
        except Exception as e:
            self.log_message(f"计算器操作失败: {str(e)}", "error")
            
    def show_converter(self) -> None:
        """显示单位转换器，优化UI和功能"""
        try:
            # 创建转换器对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("单位转换器")
            dialog.setStyleSheet("""
                QDialog {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    background-color: #f0f0f0;
                }
                QComboBox, QDoubleSpinBox, QLineEdit {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                    padding: 5px;
                    background-color: white;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                }
                QLabel {
                    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
                    font-size: 14px;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # 创建类型选择
            type_combo = QComboBox()
            type_combo.addItems(["长度", "重量", "面积", "体积", "温度"])
            layout.addWidget(type_combo)
            
            # 创建输入区域
            input_layout = QHBoxLayout()
            input_value = QDoubleSpinBox()
            input_value.setRange(-1000000, 1000000)
            input_value.setDecimals(6)
            input_unit = QComboBox()
            input_layout.addWidget(input_value)
            input_layout.addWidget(input_unit)
            layout.addLayout(input_layout)
            
            # 创建输出区域
            output_layout = QHBoxLayout()
            output_value = QLineEdit()
            output_value.setReadOnly(True)
            output_unit = QComboBox()
            output_layout.addWidget(output_value)
            output_layout.addWidget(output_unit)
            layout.addWidget(QLabel("="))
            layout.addLayout(output_layout)
            
            # 更新单位列表
            def update_units():
                units = {
                    "长度": ["米", "千米", "厘米", "毫米", "英寸", "英尺", "码", "英里"],
                    "重量": ["克", "千克", "吨", "磅", "盎司"],
                    "面积": ["平方米", "平方千米", "公顷", "亩", "平方英尺", "平方英里"],
                    "体积": ["立方米", "升", "毫升", "加仑", "品脱", "夸脱"],
                    "温度": ["摄氏度", "华氏度", "开尔文"]
                }
                
                current_type = type_combo.currentText()
                input_unit.clear()
                output_unit.clear()
                input_unit.addItems(units[current_type])
                output_unit.addItems(units[current_type])
                
            type_combo.currentTextChanged.connect(update_units)
            update_units()
            
            # 转换函数
            def convert():
                try:
                    value = input_value.value()
                    from_unit = input_unit.currentText()
                    to_unit = output_unit.currentText()
                    
                    # 转换系数
                    factors = {
                        "长度": {
                            "米": 1,
                            "千米": 1000,
                            "厘米": 0.01,
                            "毫米": 0.001,
                            "英寸": 0.0254,
                            "英尺": 0.3048,
                            "码": 0.9144,
                            "英里": 1609.344
                        },
                        "重量": {
                            "克": 1,
                            "千克": 1000,
                            "吨": 1000000,
                            "磅": 453.59237,
                            "盎司": 28.349523125
                        },
                        "面积": {
                            "平方米": 1,
                            "平方千米": 1000000,
                            "公顷": 10000,
                            "亩": 666.666667,
                            "平方英尺": 0.09290304,
                            "平方英里": 2589988.11
                        },
                        "体积": {
                            "立方米": 1,
                            "升": 0.001,
                            "毫升": 0.000001,
                            "加仑": 0.00378541,
                            "品脱": 0.000473176,
                            "夸脱": 0.000946353
                        },
                        "温度": {
                            "摄氏度": lambda x: x,
                            "华氏度": lambda x: (x * 9/5) + 32,
                            "开尔文": lambda x: x + 273.15
                        }
                    }
                    
                    current_type = type_combo.currentText()
                    if current_type == "温度":
                        # 温度转换
                        from_func = factors[current_type][from_unit]
                        to_func = factors[current_type][to_unit]
                        result = to_func(from_func(value))
                    else:
                        # 其他单位转换
                        from_factor = factors[current_type][from_unit]
                        to_factor = factors[current_type][to_unit]
                        result = value * from_factor / to_factor
                        
                    output_value.setText(f"{result:.6f}")
                    
                except Exception as e:
                    output_value.setText("错误")
                    
            # 连接信号
            input_value.valueChanged.connect(convert)
            input_unit.currentTextChanged.connect(convert)
            output_unit.currentTextChanged.connect(convert)
            
            # 显示对话框
            dialog.exec_()
            
        except Exception as e:
            self.log_message(f"显示单位转换器失败: {str(e)}", "error")

    def start_performance_monitoring(self):
        """Start performance monitoring system with memory leak prevention"""
        try:
            # Initialize performance monitor if not already initialized
            if not hasattr(self, 'performance_monitor'):
                self.performance_monitor = PerformanceMonitor(
                    config=self.config_manager.performance,
                    log_manager=self.log_manager
                )
                
            # Start monitoring with memory leak prevention
            self.performance_monitor.start_monitoring()
            
            # Create performance update timer with weak reference
            self.performance_timer = QTimer()
            self.performance_timer.timeout.connect(self.update_performance_metrics)
            self.performance_timer.start(1000)  # Update every second
            
            # Connect performance signals with weak reference
            self.performance_monitor.performance_updated.connect(self.handle_performance_update)
            
            # Add memory cleanup
            self.cleanup_timer = QTimer()
            self.cleanup_timer.timeout.connect(self.cleanup_memory)
            self.cleanup_timer.start(30000)  # Cleanup every 30 seconds
            
            self.log_message("性能监控系统已启动", "info")
            
        except Exception as e:
            self.log_message(f"启动性能监控系统失败: {str(e)}", "error")

    def cleanup_memory(self):
        """Clean up memory to prevent leaks"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clear unused caches
            if hasattr(self, 'data_cache'):
                self.data_cache.clear()
            if hasattr(self, 'chart_cache'):
                self.chart_cache.clear()
                
            # Log memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            self.log_message(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB", "debug")
            
        except Exception as e:
            self.log_message(f"清理内存失败: {str(e)}", "error")

    def handle_performance_update(self, metrics: dict):
        """Handle performance metrics update
        
        Args:
            metrics: Dictionary containing performance metrics
        """
        try:
            # Check for performance alerts
            if metrics['cpu_usage'] > self.config_manager.performance.cpu_threshold:
                self.log_message(f"CPU使用率过高: {metrics['cpu_usage']:.1f}%", "warning")
                
            if metrics['memory_usage'] > self.config_manager.performance.memory_threshold:
                self.log_message(f"内存使用率过高: {metrics['memory_usage']:.1f}%", "warning")
                
            # Update performance display
            self.update_performance_metrics()
            
        except Exception as e:
            self.log_message(f"处理性能更新失败: {str(e)}", "error")

    def update_performance_metrics(self):
        """Update performance metrics display"""
        try:
            if not hasattr(self, 'performance_monitor'):
                return
                
            # Get current metrics
            metrics = self.performance_monitor.get_metrics()
            
            # Update performance text display
            if hasattr(self, 'performance_text'):
                self.performance_text.clear()
                self.performance_text.append(f"CPU使用率: {metrics['cpu_usage']:.1f}%")
                self.performance_text.append(f"内存使用率: {metrics['memory_usage']:.1f}%")
                
                # Add response times
                if metrics['response_times']:
                    self.performance_text.append("\n响应时间:")
                    for func, time in metrics['response_times'].items():
                        self.performance_text.append(f"{func}: {time:.3f}s")
                        
                # Add exception count
                if metrics['exceptions'] > 0:
                    self.performance_text.append(f"\n异常数量: {metrics['exceptions']}")
                    
        except Exception as e:
            self.log_message(f"更新性能指标失败: {str(e)}", "error")

def main():
    """Main program entry"""
    # Create application
    app = QApplication(sys.argv)
    
    # Initialize log manager
    logger = LogManager(LoggingConfig(
        level="DEBUG",
        save_to_file=True,
        log_file='trading.log',
        max_bytes=10*1024*1024,  # 10MB
        backup_count=5,
        console_output=True,
        auto_compress=True,
        max_logs=1000,
        performance_log=True,
        performance_log_file='performance.log',
        exception_log=True,
        exception_log_file='exceptions.log',
        async_logging=True,
        log_queue_size=1000,
        worker_threads=2
    ))
    
    try:
        print("初始化配置管理器")
        # Initialize config manager
        config_manager = ConfigManager()
        print("初始化配置管理器完成")
        # Initialize theme manager
        theme_manager = ThemeManager(config_manager)
        print("初始化主题管理器完成")
        # Create main window
        window = TradingGUI()
        print("创建主窗口完成")
        window.show()
        print("显示主窗口完成")
        # Start event loop
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 