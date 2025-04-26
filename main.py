"""
交易系统主窗口模块
"""
import sys
import traceback
import pandas as pd
import numpy as np
import weakref
from typing import Dict, Any, List, Optional
from datetime import datetime
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from core.logger import LogManager
from utils.config_types import LoggingConfig, PerformanceConfig
from utils.theme import ThemeManager, get_theme_manager, Theme
from core.data_manager import DataManager
from utils.config_manager import ConfigManager
from gui.tool_bar import MainToolBar
from gui.menu_bar import MainMenuBar
from utils.performance_monitor import PerformanceMonitor
from utils.exception_handler import ExceptionHandler

# 定义全局样式表
GLOBAL_STYLE = """
QWidget {
    font-family: 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', sans-serif;
    background: #f7f9fa;
}
QGroupBox {
    border: 1.5px solid #e0e0e0;
    border-radius: 10px;
    margin-top: 10px;
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    padding: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 0 6px;
    background: #eaf3fb;
    border-radius: 6px;
    color: #1976d2;
    font-weight: bold;
}
QPushButton {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 13px;
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e3f2fd, stop:1 #bbdefb);
    border: 1px solid #90caf9;
    padding: 6px 16px;
    color: #1565c0;
    transition: background 0.2s;
}
QPushButton:hover {
    background: #90caf9;
    color: #0d47a1;
}
QPushButton:pressed {
    background: #64b5f6;
}
QLabel {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
}
QComboBox {
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 12px;
    border-radius: 6px;
    border: 1px solid #bdbdbd;
    background: #f5faff;
    padding: 2px 8px;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    font-family: 'Consolas', 'Microsoft YaHei', 'SimHei', monospace;
    font-size: 12px;
    border-radius: 6px;
    border: 1px solid #bdbdbd;
    background: #f5faff;
    padding: 4px 8px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QTabWidget::pane {
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    background: #fff;
}
QTabBar::tab {
    background: #e3f2fd;
    border-radius: 6px 6px 0 0;
    padding: 6px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1976d2;
    color: #fff;
}
"""

class TradingGUI(QMainWindow):
    """Trading system main window"""
    
    # Define signals
    theme_changed = pyqtSignal(Theme)
    data_updated = pyqtSignal(dict)
    analysis_completed = pyqtSignal(dict)
    performance_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        """Initialize the trading system GUI"""
        super().__init__()
        self.setWindowTitle("Trading System")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        try:
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            
            # 从配置中获取日志配置
            logging_config = self.config_manager.logging
            
            # 初始化日志管理器
            self.log_manager = LogManager(logging_config)
            self.log_manager.info("TradingGUI初始化开始")

            # 初始化主题管理器
            self.theme_manager = get_theme_manager(self.config_manager)
            self.theme_manager.theme_changed.connect(self.apply_theme)
            
            # 初始化性能监控器
            performance_config = self.config_manager.performance
            self.performance_monitor = PerformanceMonitor(performance_config)
            self.performance_monitor.performance_updated.connect(self.handle_performance_update)
            self.performance_monitor.alert_triggered.connect(self.handle_performance_alert)

            # 初始化线程池
            self.thread_pool = QThreadPool()
            self.thread_pool.setMaxThreadCount(4)

            # 初始化股票列表模型
            self.stock_list_model = QStringListModel()
            self.stock_list_cache = []

            # 初始化收藏列表
            self.favorites = set()

            # 初始化UI
            self.init_ui()
            self.init_data()

            # 连接信号
            self.connect_signals()

            self.log_manager.info("TradingGUI初始化完成")
            
        except Exception as e:
            # 确保即使在初始化失败时也能记录错误
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"TradingGUI初始化失败: {str(e)}")
            else:
                print(f"初始化失败: {str(e)}")
            raise

    def connect_signals(self):
        """连接所有信号和槽"""
        try:
            # 连接主题变更信号
            self.theme_changed.connect(self.apply_theme)
            
            # 连接数据更新信号
            self.data_updated.connect(self.handle_data_update)
            
            # 连接分析完成信号
            self.analysis_completed.connect(self.handle_analysis_complete)
            
            # 连接性能更新信号
            if hasattr(self, 'performance_updated'):
                self.performance_updated.connect(self.update_performance)
            
            # 连接错误信号
            self.error_occurred.connect(self.handle_error)
            
            self.log_manager.info("信号连接完成")
            
        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def handle_data_request(self, request_data: dict):
        """处理数据请求
        
        Args:
            request_data: 请求数据字典
        """
        try:
            if self.data_manager:
                response_data = self.data_manager.get_data(request_data)
                self.data_updated.emit(response_data)
        except Exception as e:
            self.log_manager.error(f"处理数据请求失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def update_data(self, data: dict):
        """更新数据
        
        Args:
            data: 数据字典
        """
        try:
            # 更新数据缓存
            if hasattr(self, 'data_cache'):
                self.data_cache.update(data)
            
            # 更新图表
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_chart(data)
            
            # 更新分析工具面板
            if hasattr(self, 'analysis_tools'):
                self.analysis_tools.update_results(data)
            
            # 更新日志
            self.log_manager.info("数据更新完成")
            
        except Exception as e:
            self.log_manager.error(f"更新数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"更新数据失败: {str(e)}")

    def handle_analysis_error(self, error_msg: str):
        """处理分析错误
        
        Args:
            error_msg: 错误信息
        """
        self.log_manager.error(f"分析错误: {error_msg}")
        QMessageBox.warning(self, "分析错误", error_msg)
        
    def handle_chart_error(self, error_msg: str):
        """处理图表错误
        
        Args:
            error_msg: 错误信息
        """
        self.log_manager.error(f"图表错误: {error_msg}")
        QMessageBox.warning(self, "图表错误", error_msg)
        
    def handle_log_error(self, error_msg: str):
        """处理日志错误
        
        Args:
            error_msg: 错误信息
        """
        self.log_manager.error(f"日志错误: {error_msg}")
        QMessageBox.warning(self, "日志错误", error_msg)
        
    def handle_log_clear(self):
        """处理日志清除"""
        try:
            if self.log_manager:
                self.log_manager.clear()
        except Exception as e:
            self.log_manager.error(f"清除日志失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def update_analysis(self, results):
        """Update analysis results"""
        try:
            if hasattr(self, 'analysis_tools'):
                self.analysis_tools.update_results(results)
                
        except Exception as e:
            self.log_manager.error(f"更新分析结果失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def handle_data_update(self, data: dict):
        """Handle data update signal"""
        try:
            # 更新数据缓存
            self.data_cache.update(data)
            
            # 更新UI显示
            self.update_ui()
            
        except Exception as e:
            self.log_manager.error(f"处理数据更新失败: {str(e)}")
            
    def handle_analysis_complete(self, results: dict):
        """Handle analysis complete signal"""
        try:
            # 更新分析结果
            self.update_metrics(results)
            
            # 更新图表
            self.update_chart()
            
        except Exception as e:
            self.log_manager.error(f"处理分析完成失败: {str(e)}")
            
    def update_ui(self):
        """Update UI components"""
        try:
            # 更新股票列表
            self.update_stock_list()
            
            # 更新指标列表
            self.update_indicators()
            
            # 更新图表
            self.update_chart()
            
            # 更新性能指标
            self.update_performance_metrics()
            
        except Exception as e:
            self.log_manager.error(f"更新UI失败: {str(e)}")
        
    def init_ui(self):
        """Initialize the main window UI
        
        This method:
        1. Sets window title and size
        2. Creates the main layout and splitters
        3. Creates all panels (left, middle, right, bottom)
        4. Creates menu bar, toolbar and status bar
        5. Applies theme to all widgets
        """
        try:
            # 设置窗口标题和大小
            self.setWindowTitle("Hikyuu Trading System")
            self.setGeometry(100, 100, 1200, 800)
            
            # 创建central widget和主布局
            central_widget = QWidget()
            self.main_layout = QVBoxLayout(central_widget)
            self.setCentralWidget(central_widget)
            
            # 创建分割器
            self.top_splitter = QSplitter(Qt.Horizontal)
            self.bottom_splitter = QSplitter(Qt.Horizontal)
            
            # 设置分割器属性
            self.top_splitter.setHandleWidth(1)
            self.bottom_splitter.setHandleWidth(1)
            self.top_splitter.setChildrenCollapsible(False)
            self.bottom_splitter.setChildrenCollapsible(False)
            
            # 添加分割器到主布局
            self.main_layout.addWidget(self.top_splitter, stretch=8)
            self.main_layout.addWidget(self.bottom_splitter, stretch=2)
            
            # 创建面板
            self.create_left_panel()
            self.create_middle_panel()
            self.create_right_panel()
            self.create_bottom_panel()
            
            # 设置分割器初始比例，主图表区最大化
            self.top_splitter.setStretchFactor(0, 1)  # 左侧
            self.top_splitter.setStretchFactor(1, 6)  # 中间更大
            self.top_splitter.setStretchFactor(2, 2)  # 右侧
            self.bottom_splitter.setStretchFactor(0, 1)
            
            # 创建菜单栏和状态栏
            self.create_menubar()
            self.create_statusbar()
            
            # 创建工具栏
            self.create_toolbar()
            
            # 应用主题
            self.apply_theme()
            
            self.log_manager.info("UI初始化完成")
            
        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
        
    def create_menubar(self):
        """创建菜单栏"""
        try:
            self.menu_bar = MainMenuBar(self)
            self.setMenuBar(self.menu_bar)
            
            # 连接菜单动作
            self.menu_bar.new_action.triggered.connect(self.new_file)
            self.menu_bar.open_action.triggered.connect(self.open_file)
            self.menu_bar.save_action.triggered.connect(self.save_file)
            self.menu_bar.exit_action.triggered.connect(self.close)
            
            self.menu_bar.undo_action.triggered.connect(self.undo)
            self.menu_bar.redo_action.triggered.connect(self.redo)
            self.menu_bar.copy_action.triggered.connect(self.copy)
            self.menu_bar.paste_action.triggered.connect(self.paste)
            
            self.menu_bar.toolbar_action.triggered.connect(self.toggle_toolbar)
            self.menu_bar.statusbar_action.triggered.connect(self.toggle_statusbar)
            self.menu_bar.light_theme_action.triggered.connect(lambda: self.change_theme('light'))
            self.menu_bar.dark_theme_action.triggered.connect(lambda: self.change_theme('dark'))
            
            self.menu_bar.analyze_action.triggered.connect(self.analyze)
            self.menu_bar.backtest_action.triggered.connect(self.backtest)
            self.menu_bar.optimize_action.triggered.connect(self.optimize)
            
            self.menu_bar.calculator_action.triggered.connect(self.show_calculator)
            self.menu_bar.converter_action.triggered.connect(self.show_converter)
            self.menu_bar.settings_action.triggered.connect(self.show_settings)
            
            self.menu_bar.help_action.triggered.connect(self.show_help)
            self.menu_bar.update_action.triggered.connect(self.check_update)
            self.menu_bar.about_action.triggered.connect(self.show_about)
            
            self.log_manager.info("菜单栏创建完成")
            
        except Exception as e:
            self.log_manager.error(f"创建菜单栏失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def create_toolbar(self):
        """创建工具栏"""
        try:
            self.toolbar = MainToolBar(self)
            self.addToolBar(self.toolbar)
            
            # 连接工具栏动作
            self.toolbar.new_action.triggered.connect(self.new_file)
            self.toolbar.open_action.triggered.connect(self.open_file)
            self.toolbar.save_action.triggered.connect(self.save_file)
            
            self.toolbar.analyze_action.triggered.connect(self.analyze)
            self.toolbar.backtest_action.triggered.connect(self.backtest)
            self.toolbar.optimize_action.triggered.connect(self.optimize)
            
            self.toolbar.zoom_in_action.triggered.connect(self.zoom_in)
            self.toolbar.zoom_out_action.triggered.connect(self.zoom_out)
            self.toolbar.reset_zoom_action.triggered.connect(self.reset_zoom)
            
            self.toolbar.calculator_action.triggered.connect(self.show_calculator)
            self.toolbar.converter_action.triggered.connect(self.show_converter)
            self.toolbar.settings_action.triggered.connect(self.show_settings)
            
            # 连接搜索框
            self.toolbar.search_box.textChanged.connect(self.filter_stock_list)
            
            self.log_manager.info("工具栏创建完成")
            
        except Exception as e:
            self.log_manager.error(f"创建工具栏失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            
    def toggle_toolbar(self, checked: bool):
        """切换工具栏显示状态
        
        Args:
            checked: 是否显示
        """
        self.toolbar.setVisible(checked)
        
    def toggle_statusbar(self, checked: bool):
        """切换状态栏显示状态
        
        Args:
            checked: 是否显示
        """
        self.statusBar().setVisible(checked)
        
    def change_theme(self, theme: str):
        """切换主题
        
        Args:
            theme: 主题名称
        """
        try:
            self.theme_manager.set_theme(theme)
            self.log_manager.info(f"切换主题: {theme}")
        except Exception as e:
            self.log_manager.error(f"切换主题失败: {str(e)}")
        
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
                
            # 删除这里的线程池初始化，避免重复
            # self.thread_pool = QThreadPool()
            # print("初始化线程池完成")
                
            # Load settings
            self.settings = self.config_manager.get_all()
            print("加载配置完成")
        
        except Exception as e:
            self.log_message(f"初始化数据失败: {str(e)}", "error")
            raise
        
    def apply_theme(self):
        """Apply theme to all widgets (主窗口唯一递归入口)"""
        try:
            if not hasattr(self, 'theme_manager'):
                self.log_manager.warning("主题管理器未初始化")
                return

            # 应用主题到主窗口
            theme = self.theme_manager.current_theme
            colors = self.theme_manager.get_theme_colors(theme)
            
            # 设置主窗口样式
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                }}
            """)

            # 应用主题到所有子部件
            for widget in self.findChildren(QWidget):
                if widget is not self:  # 避免递归调用自身
                    try:
                        self.theme_manager.apply_theme(widget)
                    except Exception as widget_error:
                        self.log_manager.warning(f"应用主题到部件失败: {str(widget_error)}")
                        continue

            self.log_manager.info("主题应用完成")
            
        except Exception as e:
            self.log_manager.error(f"应用主题失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def create_left_panel(self):
        """Create left panel with stock list and indicators"""
        try:
            # 创建左侧面板
            self.left_panel = QWidget()
            self.left_layout = QVBoxLayout(self.left_panel)
            self.left_layout.setContentsMargins(5, 5, 5, 5)
            self.left_layout.setSpacing(5)
            
            # 创建股票列表组
            stock_group = QGroupBox("股票列表")
            stock_layout = QVBoxLayout(stock_group)
            stock_layout.setContentsMargins(5, 15, 5, 5)
            stock_layout.setSpacing(5)
            
            # 创建股票类型选择器
            stock_type_layout = QHBoxLayout()
            stock_type_label = QLabel("市场:")
            self.stock_type_combo = QComboBox()
            self.stock_type_combo.addItems(["全部", "A股", "港股", "美股"])
            self.stock_type_combo.currentTextChanged.connect(self.filter_stock_list)
            stock_type_layout.addWidget(stock_type_label)
            stock_type_layout.addWidget(self.stock_type_combo)
            stock_layout.addLayout(stock_type_layout)
            
            # 创建股票搜索框
            search_layout = QHBoxLayout()
            self.stock_search = QLineEdit()
            self.stock_search.setPlaceholderText("搜索股票...")
            self.stock_search.textChanged.connect(self.filter_stock_list)
            search_layout.addWidget(self.stock_search)
            
            # 添加高级搜索按钮
            advanced_search_btn = QPushButton("高级搜索")
            advanced_search_btn.clicked.connect(self.show_advanced_search_dialog)
            search_layout.addWidget(advanced_search_btn)
            stock_layout.addLayout(search_layout)
            
            # 创建股票列表
            self.stock_list = QListWidget()
            self.stock_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.stock_list.itemSelectionChanged.connect(self.on_stock_selected)
            stock_list_scroll = QScrollArea()
            stock_list_scroll.setWidgetResizable(True)
            stock_list_scroll.setWidget(self.stock_list)
            stock_layout.addWidget(stock_list_scroll)
            
            # 添加收藏按钮
            favorites_btn = QPushButton("收藏")
            favorites_btn.clicked.connect(self.toggle_favorite)
            stock_layout.addWidget(favorites_btn)
            
            # 添加股票列表组到左侧布局
            self.left_layout.addWidget(stock_group)
            
            # 创建指标列表组
            indicator_group = QGroupBox("指标列表")
            indicator_layout = QVBoxLayout(indicator_group)
            indicator_layout.setContentsMargins(5, 15, 5, 5)
            indicator_layout.setSpacing(5)
            
            # 创建指标类型选择器
            indicator_type_layout = QHBoxLayout()
            indicator_type_label = QLabel("类型:")
            self.indicator_type_combo = QComboBox()
            self.indicator_type_combo.addItems(["全部", "趋势类", "震荡类", "成交量类", "自定义"])
            self.indicator_type_combo.currentTextChanged.connect(self.filter_indicator_list)
            indicator_type_layout.addWidget(indicator_type_label)
            indicator_type_layout.addWidget(self.indicator_type_combo)
            indicator_layout.addLayout(indicator_type_layout)
            
            # 创建指标搜索框
            indicator_search = QLineEdit()
            indicator_search.setPlaceholderText("搜索指标...")
            indicator_search.textChanged.connect(self.filter_indicator_list)
            indicator_layout.addWidget(indicator_search)
            
            # 创建指标列表
            self.indicator_list = QListWidget()
            self.indicator_list.setSelectionMode(QAbstractItemView.MultiSelection)
            self.indicator_list.itemSelectionChanged.connect(self.on_indicators_changed)
            indicator_list_scroll = QScrollArea()
            indicator_list_scroll.setWidgetResizable(True)
            indicator_list_scroll.setWidget(self.indicator_list)
            indicator_layout.addWidget(indicator_list_scroll)
            
            # 添加指标操作按钮
            indicator_buttons_layout = QHBoxLayout()
            add_indicator_btn = QPushButton("添加")
            add_indicator_btn.clicked.connect(self.show_indicator_params_dialog)
            save_combination_btn = QPushButton("保存组合")
            save_combination_btn.clicked.connect(self.save_indicator_combination)
            indicator_buttons_layout.addWidget(add_indicator_btn)
            indicator_buttons_layout.addWidget(save_combination_btn)
            indicator_layout.addLayout(indicator_buttons_layout)
            
            # 添加指标列表组到左侧布局
            self.left_layout.addWidget(indicator_group)
            
            # 设置左侧面板的最小宽度
            self.left_panel.setMinimumWidth(200)
            self.left_panel.setMaximumWidth(320)
            
            # 添加左侧面板到顶部分割器
            self.top_splitter.addWidget(self.left_panel)
            
            self.log_manager.info("左侧面板创建完成")
            
        except Exception as e:
            self.log_manager.error(f"创建左侧面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def filter_stock_list(self, text: str):
        """Filter stock list based on search text"""
        try:
            def filter_list():
                try:
                    # 获取原始股票列表
                    original_stocks = self.stock_list_cache
                    self.log_manager.info(f"原始股票列表数量: {len(original_stocks)}")

                    # 过滤股票
                    filtered_stocks = [stock for stock in original_stocks if text.lower() in stock.lower()]
                    self.log_manager.info(f"过滤条件: '{text}'，过滤后股票数量: {len(filtered_stocks)}")

                    # 更新股票列表
                    self.stock_list.clear()
                    for stock in filtered_stocks:
                        item = QListWidgetItem(stock)
                        if stock.split()[0] in self.favorites:
                            item.setText(f"★ {stock}")
                        self.stock_list.addItem(item)

                    # 记录日志
                    self.log_manager.info(f"已过滤股票列表，显示 {len(filtered_stocks)} 只股票")
                except Exception as e:
                    self.log_manager.error(f"过滤股票列表失败: {str(e)}")
                    self.log_manager.error(traceback.format_exc())

            # 使用线程池执行过滤操作
            self.thread_pool.start(filter_list)
        except Exception as e:
            self.log_manager.error(f"启动股票列表过滤线程失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

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
            # 创建中间面板
            self.middle_panel = QWidget()
            self.middle_layout = QVBoxLayout(self.middle_panel)
            self.middle_layout.setContentsMargins(5, 5, 5, 5)
            self.middle_layout.setSpacing(5)
            
            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            
            # 周期选择
            period_label = QLabel("周期:")
            self.period_combo = QComboBox()
            self.period_combo.addItems(["分时", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"])
            self.period_combo.setCurrentText("日线")
            self.period_combo.currentTextChanged.connect(self.on_period_changed)
            toolbar_layout.addWidget(period_label)
            toolbar_layout.addWidget(self.period_combo)
            
            # 图表类型选择
            chart_type_label = QLabel("图表类型:")
            self.chart_type_combo = QComboBox()
            self.chart_type_combo.addItems(["K线图", "分时图", "美国线", "收盘价"])
            self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
            toolbar_layout.addWidget(chart_type_label)
            toolbar_layout.addWidget(self.chart_type_combo)
            
            # 添加缩放按钮
            zoom_in_btn = QPushButton("放大")
            zoom_in_btn.clicked.connect(self.zoom_in)
            zoom_out_btn = QPushButton("缩小")
            zoom_out_btn.clicked.connect(self.zoom_out)
            reset_zoom_btn = QPushButton("重置")
            reset_zoom_btn.clicked.connect(self.reset_zoom)
            
            toolbar_layout.addWidget(zoom_in_btn)
            toolbar_layout.addWidget(zoom_out_btn)
            toolbar_layout.addWidget(reset_zoom_btn)
            
            # 添加工具栏到布局
            self.middle_layout.addLayout(toolbar_layout)
            
            # 创建图表标签页
            self.chart_tabs = QTabWidget()
            self.chart_tabs.setTabPosition(QTabWidget.South)
            
            # 创建主图表标签页
            self.main_chart_tab = QWidget()
            main_chart_layout = QVBoxLayout(self.main_chart_tab)
            
            # 创建主图表
            self.main_figure = Figure(figsize=(8, 6), dpi=100)
            self.main_canvas = FigureCanvas(self.main_figure)
            main_chart_layout.addWidget(self.main_canvas)
            
            # 添加导航工具栏
            self.main_nav_toolbar = NavigationToolbar(self.main_canvas, self)
            main_chart_layout.addWidget(self.main_nav_toolbar)
            
            # 创建成交量图表
            self.volume_figure = Figure(figsize=(8, 2), dpi=100)
            self.volume_canvas = FigureCanvas(self.volume_figure)
            main_chart_layout.addWidget(self.volume_canvas)
            
            self.chart_tabs.addTab(self.main_chart_tab, "主图")
            
            # 创建技术指标标签页
            self.indicator_chart_tab = QWidget()
            indicator_chart_layout = QVBoxLayout(self.indicator_chart_tab)
            
            # 创建技术指标图表
            self.indicator_figure = Figure(figsize=(8, 6), dpi=100)
            self.indicator_canvas = FigureCanvas(self.indicator_figure)
            indicator_chart_layout.addWidget(self.indicator_canvas)
            
            # 添加导航工具栏
            self.indicator_nav_toolbar = NavigationToolbar(self.indicator_canvas, self)
            indicator_chart_layout.addWidget(self.indicator_nav_toolbar)
            
            # 创建信号图表标签页
            self.signals_chart_tab = QWidget()
            self.signals_chart_layout = QVBoxLayout(self.signals_chart_tab)
            
            # 创建信号图表图形和画布
            self.signals_figure = Figure(figsize=(8, 2))
            self.signals_canvas = FigureCanvas(self.signals_figure)
            self.signals_chart_layout.addWidget(self.signals_canvas)
            
            # 添加导航工具栏
            self.signals_nav_toolbar = NavigationToolbar(self.signals_canvas, self)
            self.signals_chart_layout.addWidget(self.signals_nav_toolbar)
            
            # 创建回测图表标签页
            self.backtest_chart_tab = QWidget()
            self.backtest_chart_layout = QVBoxLayout(self.backtest_chart_tab)
            
            # 创建回测图表图形和画布
            self.backtest_figure = Figure(figsize=(8, 4))
            self.backtest_canvas = FigureCanvas(self.backtest_figure)
            self.backtest_chart_layout.addWidget(self.backtest_canvas)
            
            # 添加导航工具栏
            self.backtest_nav_toolbar = NavigationToolbar(self.backtest_canvas, self)
            self.backtest_chart_layout.addWidget(self.backtest_nav_toolbar)
            
            # 添加标签页到图表标签页控件
            self.chart_tabs.addTab(self.main_chart_tab, "主图表")
            self.chart_tabs.addTab(self.indicator_chart_tab, "技术指标")
            self.chart_tabs.addTab(self.signals_chart_tab, "信号图表")
            self.chart_tabs.addTab(self.backtest_chart_tab, "回测图表")
            
            # 添加图表标签页到中间布局
            self.middle_layout.addWidget(self.chart_tabs)
            
            # 添加中间面板到顶部分割器
            self.top_splitter.addWidget(self.middle_panel)
            
            self.log_manager.info("中间面板创建完成")
            
        except Exception as e:
            self.log_manager.error(f"创建中间面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
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
            # 创建右侧面板
            self.right_panel = QWidget()
            self.right_layout = QVBoxLayout(self.right_panel)
            self.right_layout.setContentsMargins(5, 5, 5, 5)
            self.right_layout.setSpacing(5)
            
            # 右侧内容widget（用于滚动）
            right_content = QWidget()
            right_content_layout = QVBoxLayout(right_content)
            right_content_layout.setContentsMargins(0, 0, 0, 0)
            right_content_layout.setSpacing(8)

            # 创建策略组
            strategy_group = QGroupBox("策略设置")
            strategy_layout = QVBoxLayout(strategy_group)
            strategy_layout.setContentsMargins(5, 15, 5, 5)
            # 添加策略选择
            strategy_type_layout = QHBoxLayout()
            strategy_label = QLabel("策略类型:")
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略",
                "KDJ策略", "自定义策略"
            ])
            self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
            strategy_type_layout.addWidget(strategy_label)
            strategy_type_layout.addWidget(self.strategy_combo)
            strategy_layout.addLayout(strategy_type_layout)
            
            # 创建策略参数设置区域
            self.strategy_params_widget = QWidget()
            self.strategy_params_layout = QFormLayout(self.strategy_params_widget)
            strategy_layout.addWidget(self.strategy_params_widget)
            
            # 添加策略组到右侧布局
            right_content_layout.addWidget(strategy_group)
            
            # 创建回测设置组
            backtest_group = QGroupBox("回测设置")
            backtest_layout = QFormLayout(backtest_group)
            backtest_layout.setContentsMargins(5, 15, 5, 5)
            # 初始资金
            self.initial_capital = QDoubleSpinBox()
            self.initial_capital.setFixedHeight(25)
            self.initial_capital.setRange(1000.0, 10000000.0)
            self.initial_capital.setValue(100000.0)
            self.initial_capital.setSuffix(" 元")
            backtest_layout.addRow("初始资金:", self.initial_capital)
            
            # 手续费率
            self.commission_rate = QDoubleSpinBox()
            self.commission_rate.setFixedHeight(25)
            self.commission_rate.setDecimals(4)
            self.commission_rate.setRange(0.0, 0.01)
            self.commission_rate.setValue(0.0003)
            self.commission_rate.setSuffix(" %")
            backtest_layout.addRow("手续费率:", self.commission_rate)
            
            # 滑点设置
            self.slippage = QDoubleSpinBox()
            self.slippage.setFixedHeight(25)
            self.slippage.setDecimals(4)
            self.slippage.setRange(0.0, 0.01)
            self.slippage.setValue(0.0001)
            self.slippage.setSuffix(" %")
            backtest_layout.addRow("滑点:", self.slippage)
            
            # 回测时间范围
            date_range_layout = QHBoxLayout()
            date_range_layout.setContentsMargins(0, 0, 0, 0)
            self.start_date = QDateEdit()
            self.start_date.setFixedHeight(25)
            self.start_date.setCalendarPopup(True)
            self.start_date.setDate(QDate.currentDate().addYears(-1))
            self.end_date = QDateEdit()
            self.end_date.setFixedHeight(25)
            self.end_date.setCalendarPopup(True)
            self.end_date.setDate(QDate.currentDate())
            date_range_layout.addWidget(self.start_date)
            date_range_layout.addWidget(QLabel("至"))
            date_range_layout.addWidget(self.end_date)
            backtest_layout.addRow("回测区间:", date_range_layout)
            
            # 添加回测设置组到右侧布局
            right_content_layout.addWidget(backtest_group)
            
            # 创建风险控制组
            risk_group = QGroupBox("风险控制")
            risk_layout = QFormLayout(risk_group)
            risk_layout.setContentsMargins(5, 15, 5, 5)
            # 止损设置
            self.stop_loss = QDoubleSpinBox()
            self.stop_loss.setFixedHeight(25)
            self.stop_loss.setDecimals(2)
            self.stop_loss.setRange(0.0, 100.0)
            self.stop_loss.setValue(5.0)
            self.stop_loss.setSuffix(" %")
            risk_layout.addRow("止损比例:", self.stop_loss)
            
            # 止盈设置
            self.take_profit = QDoubleSpinBox()
            self.take_profit.setFixedHeight(25)
            self.take_profit.setDecimals(2)
            self.take_profit.setRange(0.0, 100.0)
            self.take_profit.setValue(10.0)
            self.take_profit.setSuffix(" %")
            risk_layout.addRow("止盈比例:", self.take_profit)
            
            # 最大持仓
            self.max_position = QSpinBox()
            self.max_position.setFixedHeight(25)
            self.max_position.setRange(1, 100)
            self.max_position.setValue(5)
            self.max_position.setSuffix(" 只")
            risk_layout.addRow("最大持仓:", self.max_position)
            
            # 添加风险控制组到右侧布局
            right_content_layout.addWidget(risk_group)
            
            # 创建操作按钮组
            button_layout = QHBoxLayout()
            
            # 分析按钮
            analyze_btn = QPushButton("分析")
            analyze_btn.clicked.connect(self.analyze)
            button_layout.addWidget(analyze_btn)
            
            # 回测按钮
            backtest_btn = QPushButton("回测")
            backtest_btn.clicked.connect(self.backtest)
            button_layout.addWidget(backtest_btn)
            
            # 优化按钮
            optimize_btn = QPushButton("优化")
            optimize_btn.clicked.connect(self.optimize)
            button_layout.addWidget(optimize_btn)
            
            # 添加按钮组到右侧布局
            right_content_layout.addLayout(button_layout)
            
            # 滚动区域包裹右侧内容
            right_scroll = QScrollArea()
            right_scroll.setWidgetResizable(True)
            right_scroll.setWidget(right_content)
            self.right_layout.addWidget(right_scroll)

            self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.right_panel.setMinimumWidth(220)
            self.right_panel.setMaximumWidth(350)
            self.top_splitter.addWidget(self.right_panel)
            self.log_manager.info("右侧面板创建完成")
        except Exception as e:
            self.log_manager.error(f"创建右侧面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
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

    def log_message(self, message: str, level: str = "INFO") -> None:
        """记录日志消息
        
        Args:
            message: 日志消息
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
            
            # 如果有日志管理器，也记录到日志管理器
            if hasattr(self, 'log_manager'):
                if level == "ERROR":
                    self.log_manager.error(message)
                elif level == "WARNING":
                    self.log_manager.warning(message)
                elif level == "DEBUG":
                    self.log_manager.debug(message)
                else:
                    self.log_manager.info(message)
            
            # 如果日志级别为错误，显示错误对话框
            if level == "ERROR":
                QMessageBox.critical(self, "错误", message)
                
        except Exception as e:
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")

    def clear_log(self) -> None:
        """清除日志内容
        
        清除日志显示区域的内容，同时清理日志文件，并优化系统性能
        """
        try:
            # 清除日志显示区域
            if hasattr(self, 'log_text'):
                self.log_text.clear()
                
            # 清除日志文件
            if hasattr(self, 'log_manager'):
                self.log_manager.clear()
                
            # 优化系统性能
            self.cleanup_memory()
            
            # 记录清除操作
            self.log_message("日志已清除", "info")
            
            # 更新UI
            QApplication.processEvents()
            
        except Exception as e:
            self.log_message(f"清除日志失败: {str(e)}", "error")
            # 显示错误对话框
            QMessageBox.critical(self, "错误", f"清除日志失败: {str(e)}")

    def handle_performance_alert(self, message: str) -> None:
        """处理性能警告，优化警告处理"""
        try:
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
        """Create bottom panel with logs"""
        try:
            # 创建底部面板
            self.bottom_panel = QWidget()
            self.bottom_layout = QVBoxLayout(self.bottom_panel)
            
            # 创建日志控件组
            log_group = QGroupBox("系统日志")
            log_layout = QVBoxLayout(log_group)
            log_layout.setContentsMargins(5, 15, 5, 5)
            
            # 创建日志控件
            controls_layout = QHBoxLayout()
            
            # 日志级别过滤器
            log_level_label = QLabel("日志级别:")
            self.log_level_combo = QComboBox()
            self.log_level_combo.addItems(["全部", "信息", "警告", "错误"])
            self.log_level_combo.currentTextChanged.connect(self.filter_logs)
            controls_layout.addWidget(log_level_label)
            controls_layout.addWidget(self.log_level_combo)
            
            # 搜索框
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("搜索日志...")
            self.search_box.textChanged.connect(self.search_logs)
            controls_layout.addWidget(self.search_box)
            
            # 清除按钮
            clear_button = QPushButton("清除")
            clear_button.clicked.connect(self.clear_log)
            controls_layout.addWidget(clear_button)
            
            # 导出按钮
            export_button = QPushButton("导出")
            export_button.clicked.connect(self.export_logs)
            controls_layout.addWidget(export_button)
            
            # 添加控件到日志布局
            log_layout.addLayout(controls_layout)
            
            # 创建日志文本区域
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setLineWrapMode(QTextEdit.NoWrap)
            log_text_scroll = QScrollArea()
            log_text_scroll.setWidgetResizable(True)
            log_text_scroll.setWidget(self.log_text)
            log_layout.addWidget(log_text_scroll)
            
            # 添加日志组到底部布局
            self.bottom_layout.addWidget(log_group)
            
            # 添加底部面板到底部分割器
            self.bottom_splitter.addWidget(self.bottom_panel)
            self.bottom_panel.setMinimumHeight(120)
            self.bottom_panel.setMaximumHeight(300)
            self.bottom_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            self.log_manager.info("底部面板创建完成")
            
        except Exception as e:
            self.log_manager.error(f"创建底部面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
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
                    all_stocks = sm.get_stock_list()  # 使用正确的API
                    self.stock_list.clear()
                    self.stock_list_cache.clear()
                    
                    # 更新缓存和列表
                    for stock in all_stocks:
                        stock_text = f"{stock['code']} {stock['name']}"
                        self.stock_list_cache.append(stock_text)
                        item = QListWidgetItem(stock_text)
                        if stock['code'] in self.favorites:
                            item.setText(f"★ {stock_text}")
                        self.stock_list.addItem(item)
                        
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

    def zoom_in(self):
        """放大图表"""
        try:
            if hasattr(self, 'chart_widget'):
                self.chart_widget.zoom_in()
                self.log_message("图表已放大", "info")
        except Exception as e:
            self.log_message(f"放大图表失败: {str(e)}", "error")
            
    def zoom_out(self):
        """缩小图表"""
        try:
            if hasattr(self, 'chart_widget'):
                self.chart_widget.zoom_out()
                self.log_message("图表已缩小", "info")
        except Exception as e:
            self.log_message(f"缩小图表失败: {str(e)}", "error")
            
    def reset_zoom(self):
        """重置图表缩放"""
        try:
            if hasattr(self, 'chart_widget'):
                self.chart_widget.reset_zoom()
                self.log_message("图表缩放已重置", "info")
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
        """启动性能监控"""
        try:
            if self.performance_monitor is None:
                self.log_manager.warning("性能监控未初始化，尝试重新初始化")
                # 使用正确的配置访问方式
                perf_config = self.config_manager.performance
                self.performance_monitor = PerformanceMonitor(
                    cpu_threshold=perf_config.cpu_threshold,
                    memory_threshold=perf_config.memory_threshold,
                    disk_threshold=perf_config.disk_threshold,
                    log_manager=self.log_manager
                )
            
            if not self.performance_monitor.is_monitoring:
                self.performance_monitor.start_monitoring()
                self.log_manager.info("性能监控启动成功")
            else:
                self.log_manager.warning("性能监控已在运行中")
                
        except Exception as e:
            self.log_manager.error(f"启动性能监控失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def handle_performance_update(self, metrics: dict):
        """处理性能指标更新
        
        Args:
            metrics: 性能指标字典
        """
        try:
            # 更新性能显示
            self.update_performance_metrics(metrics)
            
            # 检查性能警告
            self.check_performance(metrics)
            
        except Exception as e:
            self.log_manager.error(f"处理性能更新失败: {str(e)}")
            
    def handle_performance_alert(self, message: str):
        """处理性能告警
        
        Args:
            message: 告警消息
        """
        try:
            # 显示告警消息
            self.log_manager.warning(message)
            
            # 如果有告警面板，显示告警
            if hasattr(self, 'warning_area'):
                current_time = datetime.now().strftime('%H:%M:%S')
                self.warning_area.append(f"[{current_time}] {message}")
                
        except Exception as e:
            self.log_manager.error(f"处理性能告警失败: {str(e)}")
            
    def check_performance(self, metrics: dict):
        """检查性能指标
        
        Args:
            metrics: 性能指标字典
        """
        try:
            # 检查CPU使用率
            if metrics['cpu_usage'] > self.config_manager.performance.cpu_threshold:
                self.handle_performance_alert(
                    f"CPU使用率过高: {metrics['cpu_usage']:.1f}%"
                )
                
            # 检查内存使用率
            if metrics['memory_usage'] > self.config_manager.performance.memory_threshold:
                self.handle_performance_alert(
                    f"内存使用率过高: {metrics['memory_usage']:.1f}%"
                )
                
            # 检查响应时间
            for func, time in metrics['response_times'].items():
                if time > self.config_manager.performance.response_threshold:
                    self.handle_performance_alert(
                        f"函数 {func} 响应时间过长: {time:.2f}秒"
                    )
                    
        except Exception as e:
            self.log_manager.error(f"检查性能指标失败: {str(e)}")
        
    def cleanup_memory(self):
        """清理内存"""
        try:
            # 清理图表缓存
            if hasattr(self, 'chart_widget'):
                self.chart_widget.clear()
                
            # 清理数据缓存
            if hasattr(self, 'data_cache'):
                self.data_cache.clear()
                
            # 清理日志缓存
            if hasattr(self, 'log_cache'):
                self.log_cache.clear()
                
            # 强制垃圾回收
            import gc
            gc.collect()
            
        except Exception as e:
            self.log_manager.error(f"清理内存失败: {str(e)}")

    def update_performance_metrics(self, metrics: dict) -> None:
        """更新性能指标显示"""
        try:
            # 更新总收益率
            self.total_return_label.setText(f"{metrics['total_return']*100:.2f}%")
            
            # 更新年化收益率
            self.annual_return_label.setText(f"{metrics['annual_return']*100:.2f}%")
            
            # 更新最大回撤
            self.max_drawdown_label.setText(f"{metrics['max_drawdown']*100:.2f}%")
            
            # 更新夏普比率
            self.sharpe_ratio_label.setText(f"{metrics['sharpe_ratio']:.2f}")
            
            # 更新胜率
            self.win_rate_label.setText(f"{metrics['win_rate']*100:.2f}%")
            
            # 更新盈亏比
            self.profit_factor_label.setText(f"{metrics['profit_factor']:.2f}")
            
            # 更新总交易次数
            self.total_trades_label.setText(str(metrics['total_trades']))
            
            # 更新平均持仓天数
            self.avg_hold_days_label.setText(f"{metrics['avg_hold_days']:.2f}")
            
            # 更新资金曲线图表
            self.update_trend_chart(metrics['equity_curve'])
            
        except Exception as e:
            error_msg = f"更新性能指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)
            
    def update_trend_chart(self, equity_curve: list) -> None:
        """更新资金曲线图表"""
        try:
            # 创建图表
            fig = go.Figure()
            
            # 添加资金曲线
            fig.add_trace(go.Scatter(
                y=equity_curve,
                mode='lines',
                name='资金曲线',
                line=dict(color='blue')
            ))
            
            # 更新图表布局
            fig.update_layout(
                title='资金曲线',
                xaxis_title='交易日',
                yaxis_title='资金',
                showlegend=True,
                template='plotly_white'
            )
            
            # 更新图表显示
            self.trend_chart.setHtml(fig.to_html(include_plotlyjs='cdn'))
            
        except Exception as e:
            error_msg = f"更新资金曲线失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def preload_data(self):
        """预加载常用数据"""
        try:
            stocks = self.data_manager.get_stock_list()[:100]  # 限制预加载数量
            
            def load_stock_data(stock):
                try:
                    data = self.data_manager.get_k_data(stock, 'D')
                    self.data_cache.set(f"{stock}_D", data)
                except Exception as e:
                    self.log_message(f"预加载数据失败: {str(e)}", "error")
                    
            # 使用线程池并行加载
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                executor.map(load_stock_data, stocks)
                
        except Exception as e:
            self.log_message(f"预加载数据失败: {str(e)}", "error")

    def optimize_chart_rendering(self):
        """优化图表渲染性能"""
        try:
            # 减少重绘
            self.chart_widget.setUpdatesEnabled(False)
            
            # 使用双缓冲
            self.chart_widget.setAttribute(Qt.WA_PaintOnScreen, False)
            self.chart_widget.setAttribute(Qt.WA_NoSystemBackground, False)
            
            # 启用硬件加速
            self.chart_widget.setRenderHint(QPainter.Antialiasing)
            self.chart_widget.setRenderHint(QPainter.SmoothPixmapTransform)
            
        except Exception as e:
            self.log_message(f"优化图表渲染失败: {str(e)}", "error")

    def handle_exception(self, exception: Exception, error_type: str, error_message: str, error_traceback: str) -> None:
        """处理系统异常
        
        Args:
            exception: 异常对象
            error_type: 错误类型
            error_message: 错误消息
            error_traceback: 错误堆栈跟踪
        """
        try:
            # 创建错误对话框
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
            
    def update_performance(self, metrics: dict):
        """Update performance metrics and display
        
        Args:
            metrics: Dictionary containing performance metrics
        """
        try:
            # 更新性能指标
            self.update_metrics(metrics)
            
            # 更新性能显示
            if hasattr(self, 'performance_text'):
                self.performance_text.clear()
                for name, value in metrics.items():
                    if isinstance(value, float):
                        formatted_value = f"{value:.2%}" if "率" in name else f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    self.performance_text.append(f"{name}: {formatted_value}")
            
            # 更新图表
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_performance_chart(metrics)
            
            # 记录日志
            self.log_manager.info("性能指标已更新")
            
        except Exception as e:
            self.log_manager.error(f"更新性能指标失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"更新性能指标失败: {str(e)}")

    def handle_error(self, error_msg: str) -> None:
        """处理错误消息
        
        Args:
            error_msg: 错误消息
        """
        try:
            # 记录错误日志
            self.log_manager.error(error_msg)
            
            # 显示错误对话框
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("错误")
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setText("发生错误")
            error_dialog.setInformativeText(error_msg)
            error_dialog.setDetailedText(traceback.format_exc())
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
            
            # 如果是严重错误，尝试恢复系统状态
            if "MemoryError" in error_msg or "SystemError" in error_msg:
                self.cleanup_memory()
                self.log_manager.info("系统已尝试恢复")
                
        except Exception as e:
            # 如果错误处理本身出错，至少打印到控制台
            print(f"错误处理失败: {str(e)}")
            print(f"原始错误: {error_msg}")

    def init_performance_display(self):
        """初始化性能指标显示面板"""
        try:
            # 创建性能指标面板
            self.performance_panel = QWidget()
            self.performance_panel.setObjectName("performancePanel")
            layout = QVBoxLayout(self.performance_panel)
            
            # 创建性能监控组
            monitor_group = QGroupBox("系统性能监控")
            monitor_layout = QGridLayout()
            monitor_layout.setContentsMargins(5, 15, 5, 5)
            # CPU使用率
            self.cpu_label = QLabel("0%")
            self.cpu_label.setFixedHeight(25)
            self.cpu_progress = QProgressBar()
            self.cpu_progress.setRange(0, 100)
            monitor_layout.addWidget(QLabel("CPU使用率:"), 0, 0)
            monitor_layout.addWidget(self.cpu_label, 0, 1)
            monitor_layout.addWidget(self.cpu_progress, 0, 2)
            
            # 内存使用率
            self.memory_label = QLabel("0%")
            self.memory_label.setFixedHeight(25)
            self.memory_progress = QProgressBar()
            self.memory_progress.setRange(0, 100)
            monitor_layout.addWidget(QLabel("内存使用率:"), 1, 0)
            monitor_layout.addWidget(self.memory_label, 1, 1)
            monitor_layout.addWidget(self.memory_progress, 1, 2)
            
            # 磁盘使用率
            self.disk_label = QLabel("0%")
            self.disk_label.setFixedHeight(25)
            self.disk_progress = QProgressBar()
            self.disk_progress.setRange(0, 100)
            monitor_layout.addWidget(QLabel("磁盘使用率:"), 2, 0)
            monitor_layout.addWidget(self.disk_label, 2, 1)
            monitor_layout.addWidget(self.disk_progress, 2, 2)
            
            # 响应时间
            self.response_label = QLabel("0ms")
            self.response_label.setFixedHeight(25)
            monitor_layout.addWidget(QLabel("响应时间:"), 3, 0)
            monitor_layout.addWidget(self.response_label, 3, 1)

            # 线程池活跃线程数
            self.threadpool_label = QLabel("0")
            self.threadpool_label.setFixedHeight(25)
            monitor_layout.addWidget(QLabel("线程池活跃线程:"), 4, 0)
            monitor_layout.addWidget(self.threadpool_label, 4, 1)
            
            monitor_group.setLayout(monitor_layout)
            layout.addWidget(monitor_group)
            
            # 创建告警区域
            warning_group = QGroupBox("性能告警")
            warning_layout = QVBoxLayout()
            warning_layout.setContentsMargins(5, 15, 5, 5)
            self.warning_area = QTextEdit()
            self.warning_area.setReadOnly(True)
            self.warning_area.setMaximumHeight(100)
            warning_layout.addWidget(self.warning_area)
            warning_group.setLayout(warning_layout)
            layout.addWidget(warning_group)
            
            # 添加到右侧面板
            if not self.right_panel.layout():
                self.right_panel.setLayout(QVBoxLayout())
            self.right_panel.layout().addWidget(self.performance_panel)
            
            # 设置样式
            self.performance_panel.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                }
                QLabel {
                    font-size: 12px;
                }
                QGroupBox {
                    font-weight: bold;
                }
            """)
            
            self.log_manager.info("性能监控面板初始化完成")
            
        except Exception as e:
            self.log_manager.error(f"初始化性能监控面板失败: {str(e)}")

    def update_performance_metrics(self, metrics: dict):
        """更新性能指标显示
        
        Args:
            metrics: 性能指标字典
        """
        try:
            # 更新CPU使用率
            cpu_usage = metrics.get('cpu_usage', 0)
            self.cpu_label.setText(f"{cpu_usage:.1f}%")
            self.cpu_progress.setValue(int(cpu_usage))
            self.cpu_progress.setStyleSheet(self._get_progress_style(cpu_usage))
            
            # 更新内存使用率
            memory_usage = metrics.get('memory_usage', 0)
            self.memory_label.setText(f"{memory_usage:.1f}%")
            self.memory_progress.setValue(int(memory_usage))
            self.memory_progress.setStyleSheet(self._get_progress_style(memory_usage))
            
            # 更新磁盘使用率
            disk_usage = metrics.get('disk_usage', 0)
            self.disk_label.setText(f"{disk_usage:.1f}%")
            self.disk_progress.setValue(int(disk_usage))
            self.disk_progress.setStyleSheet(self._get_progress_style(disk_usage))
            
            # 更新响应时间
            response_time = metrics.get('response_time', 0)
            self.response_label.setText(f"{response_time*1000:.0f}ms")

            # 更新线程池活跃线程数
            if hasattr(self, 'thread_pool') and hasattr(self, 'threadpool_label'):
                self.threadpool_label.setText(str(self.thread_pool.activeThreadCount()))
            
        except Exception as e:
            self.log_manager.error(f"更新性能指标显示失败: {str(e)}")

    def _get_progress_style(self, value: float) -> str:
        """获取进度条样式
        
        Args:
            value: 进度值
            
        Returns:
            样式字符串
        """
        if value >= 90:
            return "QProgressBar::chunk { background-color: #f44336; }"  # 红色
        elif value >= 70:
            return "QProgressBar::chunk { background-color: #ff9800; }"  # 橙色
        else:
            return "QProgressBar::chunk { background-color: #4CAF50; }"  # 绿色

    def export_performance_data(self):
        """导出性能监控数据"""
        try:
            from datetime import datetime
            import pandas as pd
            import os
            
            # 获取性能数据
            data = {
                'CPU使用率(%)': self.performance_history['cpu'],
                '内存使用率(%)': self.performance_history['memory'],
                '磁盘使用率(%)': self.performance_history['disk'],
                '响应时间(ms)': self.performance_history['response']
            }
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 生成文件名
            filename = f"performance_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 获取用户桌面路径
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            filepath = os.path.join(desktop, filename)
            
            # 导出数据
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            self.log_manager.info(f"性能数据已导出到: {filepath}")
            
        except Exception as e:
            self.log_manager.error(f"导出性能数据失败: {str(e)}")

    def on_chart_type_changed(self, index: int):
        """图表类型改变时的处理
        
        Args:
            index: 选中的图表类型索引
        """
        try:
            chart_type = self.chart_type_combo.currentText()
            self.log_manager.info(f"切换图表类型: {chart_type}")
            
            # 更新图表显示
            if hasattr(self, 'figure') and hasattr(self, 'canvas'):
                self.figure.clear()
                
                if chart_type == 'K线图':
                    self._plot_kline()
                elif chart_type == '分时图':
                    self._plot_timeline()
                elif chart_type == '成交量':
                    self._plot_volume()
                elif chart_type == 'MACD':
                    self._plot_macd()
                elif chart_type == 'RSI':
                    self._plot_rsi()
                elif chart_type == '布林带':
                    self._plot_bollinger()
                elif chart_type == 'KDJ':
                    self._plot_kdj()
                    
                self.canvas.draw()
                
            self.log_manager.info("图表类型切换完成")
            
        except Exception as e:
            error_msg = f"切换图表类型失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def update_chart(self) -> None:
        """更新图表显示"""
        try:
            if not hasattr(self, 'current_stock') or not self.current_stock:
                return
                
            # 获取当前股票数据
            k_data = self.data_manager.get_k_data(
                self.current_stock, 
                self.current_period
            )
            
            if k_data.empty:
                self.log_message(f"获取股票数据失败: {self.current_stock}", "error")
                return
                
            # 清除主图
            self.main_figure.clear()
            
            # 创建主图和成交量子图
            if self.current_chart_type == 'candlestick':
                # K线图
                ax_main = self.main_figure.add_subplot(211)
                ax_vol = self.main_figure.add_subplot(212)
                
                # 绘制K线图
                mplfinance.plot(
                    k_data,
                    type='candle',
                    style='charles',
                    ax=ax_main,
                    volume=ax_vol,
                    show_nontrading=False
                )
                
            elif self.current_chart_type == 'line':
                # 分时图
                ax_main = self.main_figure.add_subplot(211)
                ax_vol = self.main_figure.add_subplot(212)
                
                # 绘制分时图
                ax_main.plot(k_data.index, k_data['close'])
                ax_vol.bar(k_data.index, k_data['volume'])
                
            elif self.current_chart_type == 'ohlc':
                # 美国线
                ax_main = self.main_figure.add_subplot(211)
                ax_vol = self.main_figure.add_subplot(212)
                
                # 绘制美国线
                mplfinance.plot(
                    k_data,
                    type='ohlc',
                    style='charles',
                    ax=ax_main,
                    volume=ax_vol,
                    show_nontrading=False
                )
                
            elif self.current_chart_type == 'close':
                # 收盘价
                ax_main = self.main_figure.add_subplot(211)
                ax_vol = self.main_figure.add_subplot(212)
                
                # 绘制收盘价
                ax_main.plot(k_data.index, k_data['close'])
                ax_vol.bar(k_data.index, k_data['volume'])
                
            # 设置标题
            ax_main.set_title(f"{self.current_stock} - {self.period_combo.currentText()}")
            
            # 自动调整布局
            self.main_figure.tight_layout()
            
            # 重绘图表
            self.main_canvas.draw()
            
            # 更新技术指标
            self.update_indicators()
            
            self.log_message("图表更新完成")
            
        except Exception as e:
            self.log_message(f"更新图表失败: {str(e)}", "error")

    def analyze(self):
        """执行分析"""
        try:
            if not self.current_stock:
                self.log_manager.warning("请先选择股票")
                return
                
            # 获取当前策略
            strategy = self.strategy_combo.currentText()
            
            # 获取策略参数
            params = {}
            
            for i in range(self.strategy_params_layout.rowCount()):
                label = self.strategy_params_layout.itemAt(i, QFormLayout.LabelRole).widget().text()
                widget = self.strategy_params_layout.itemAt(i, QFormLayout.FieldRole).widget()
                if isinstance(widget, QSpinBox):
                    params[label] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    params[label] = widget.value()
                    

            # 记录开始分析
            self.log_manager.info(f"开始分析 - 策略: {strategy}")
            
            # 获取股票数据
            data = self.data_manager.get_stock_data(
                self.current_stock,
                self.current_period,
                self.start_date.date().toPyDate(),
                self.end_date.date().toPyDate()
            )
            
            # 执行分析
            results = self._execute_analysis(strategy, data, params)
            
            # 更新图表
            self.update_chart(results)
            
            # 发送分析完成信号
            self.analysis_completed.emit(results)
            
            self.log_manager.info("分析完成")
            
        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def backtest(self):
        """执行回测"""
        try:
            if not self.current_stock:
                self.log_manager.warning("请先选择股票")
                return
                
            # 获取当前策略
            strategy = self.strategy_combo.currentText()
            
            # 获取策略参数
            params = {}
            for i in range(self.strategy_params_layout.rowCount()):
                label = self.strategy_params_layout.itemAt(i, QFormLayout.LabelRole).widget().text()
                widget = self.strategy_params_layout.itemAt(i, QFormLayout.FieldRole).widget()
                if isinstance(widget, QSpinBox):
                    params[label] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    params[label] = widget.value()
                    
            # 记录开始回测
            self.log_manager.info(f"开始回测 - 策略: {strategy}")
            
            # 创建回测实例
            from improved_backtest import ImprovedBacktest
            backtester = ImprovedBacktest(params)
            
            # 运行回测
            backtester.run(
                stock_code=self.current_stock,
                start_date=self.start_date.date().toPyDate(),
                end_date=self.end_date.date().toPyDate()
            )
            
            # 获取回测结果
            metrics = backtester.get_metrics()
            
            # 更新UI显示
            self.update_performance_metrics(metrics)
            
            # 发送回测完成信号
            self.performance_updated.emit(metrics)
            
            self.log_manager.info("回测完成")
            
        except Exception as e:
            error_msg = f"回测失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    


    def _execute_analysis(self, strategy: str, data: pd.DataFrame, params: dict) -> dict:
        """执行分析
        
        Args:
            strategy: 策略名称
            data: 股票数据
            params: 策略参数
            
        Returns:
            分析结果
        """
        try:
            results = {}
            
            if strategy == "均线策略":
                # 计算均线
                ma_short = data['close'].rolling(window=params.get('快线周期', 5)).mean()
                ma_long = data['close'].rolling(window=params.get('慢线周期', 20)).mean()
                
                # 计算信号
                signals = pd.Series(0, index=data.index)
                signals[ma_short > ma_long] = 1
                signals[ma_short < ma_long] = -1
                
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'MA_short': ma_short,
                        'MA_long': ma_long
                    }
                }
                
            elif strategy == "MACD策略":
                # 计算MACD
                exp1 = data['close'].ewm(span=params.get('快线周期', 12), adjust=False).mean()
                exp2 = data['close'].ewm(span=params.get('慢线周期', 26), adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=params.get('信号周期', 9), adjust=False).mean()
                
                # 计算信号
                signals = pd.Series(0, index=data.index)
                signals[macd > signal] = 1
                signals[macd < signal] = -1
                
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'MACD': macd,
                        'Signal': signal
                    }
                }
                
            elif strategy == "RSI策略":
                # 计算RSI
                delta = data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=params.get('周期', 14)).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=params.get('周期', 14)).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                # 计算信号
                signals = pd.Series(0, index=data.index)
                signals[rsi < params.get('超卖阈值', 30)] = 1
                signals[rsi > params.get('超买阈值', 70)] = -1
                
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'RSI': rsi
                    }
                }
                
            elif strategy == "布林带策略":
                # 计算布林带
                ma = data['close'].rolling(window=params.get('周期', 20)).mean()
                std = data['close'].rolling(window=params.get('周期', 20)).std()
                upper = ma + params.get('标准差倍数', 2) * std
                lower = ma - params.get('标准差倍数', 2) * std
                
                # 计算信号
                signals = pd.Series(0, index=data.index)
                signals[data['close'] < lower] = 1
                signals[data['close'] > upper] = -1
                
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'MA': ma,
                        'Upper': upper,
                        'Lower': lower
                    }
                }
                
            elif strategy == "KDJ策略":
                # 计算KDJ
                low_min = data['low'].rolling(window=params.get('周期', 9)).min()
                high_max = data['high'].rolling(window=params.get('周期', 9)).max()
                rsv = (data['close'] - low_min) / (high_max - low_min) * 100
                k = rsv.ewm(com=params.get('K平滑', 2)).mean()
                d = k.ewm(com=params.get('D平滑', 2)).mean()
                j = 3 * k - 2 * d
                
                # 计算信号
                signals = pd.Series(0, index=data.index)
                signals[k < params.get('超卖阈值', 20)] = 1
                signals[k > params.get('超买阈值', 80)] = -1
                
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'K': k,
                        'D': d,
                        'J': j
                    }
                }
                
            return results
            
        except Exception as e:
            self.log_manager.error(f"执行分析失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def new_file(self):
        """创建新文件"""
        try:
            # 重置所有数据
            self.data_cache.clear()
            self.chart_cache.clear()
            self.stock_list_cache.clear()
            
            # 重置UI状态
            self.update_stock_list_ui()
            self.reset_chart_view()
            self.clear_log()
            
            self.log_message("已创建新文件", "info")
        except Exception as e:
            self.log_message(f"创建新文件失败: {str(e)}", "error")

    def open_file(self):
        """打开文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "打开文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # TODO: 处理文件内容
                self.log_message("文件打开成功", "info")
                
        except Exception as e:
            self.log_message(f"打开文件失败: {str(e)}", "error")
            
    def save_file(self):
        """保存文件"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存文件",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt)"
            )
            
            if file_path:
                # TODO: 获取当前内容并保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.log_message("文件保存成功", "info")
                
        except Exception as e:
            self.log_message(f"保存文件失败: {str(e)}", "error")
            
    def undo(self):
        """撤销上一步操作"""
        # TODO: 实现撤销功能
        pass
        
    def redo(self):
        """重做上一步操作"""
        # TODO: 实现重做功能
        pass
        
    def copy(self):
        """复制选中内容"""
        # TODO: 实现复制功能
        pass
        
    def paste(self):
        """粘贴内容"""
        # TODO: 实现粘贴功能
        pass
        
    def show_help(self):
        """显示帮助文档"""
        try:
            # TODO: 实现帮助文档显示
            self.log_message("显示帮助文档", "info")
        except Exception as e:
            self.log_message(f"显示帮助文档失败: {str(e)}", "error")
            
    def check_update(self):
        """检查更新"""
        try:
            # TODO: 实现更新检查
            self.log_message("检查更新", "info")
        except Exception as e:
            self.log_message(f"检查更新失败: {str(e)}", "error")
            
    def show_settings(self):
        """显示设置对话框"""
        try:
            # TODO: 实现设置对话框
            self.log_message("显示设置对话框", "info")
        except Exception as e:
            self.log_message(f"显示设置对话框失败: {str(e)}", "error")

# 添加全局异常处理
def global_exception_handler(exctype, value, traceback):
    """全局异常处理器"""
    try:
        # 记录错误
        self.log_manager.error(f"未捕获的异常: {exctype.__name__}: {value}")
        self.log_manager.error(f"堆栈跟踪:\n{''.join(traceback.format_tb(traceback))}")
        
        # 显示错误对话框
        error_dialog = QErrorMessage(self)
        error_dialog.showMessage(f"发生错误: {value}\n\n请查看日志获取详细信息。")
        
        # 尝试恢复
        self.cleanup_memory()
        self.reset_chart_view()
        
    except Exception as e:
        print(f"错误处理失败: {e}")
        
sys.excepthook = global_exception_handler

def main():
    """Main program entry"""
    logger = None
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Initialize config manager first
        print("初始化配置管理器")
        config_manager = ConfigManager()
        print("初始化配置管理器完成")
        
        # Initialize exception handler
        print("初始化异常处理器")
        exception_handler = ExceptionHandler()
        print("初始化异常处理器完成")
        
        # Initialize log manager with the correct LoggingConfig
        print("初始化日志管理器")
        logger = LogManager(config_manager.logging)
        exception_handler.set_logger(logger)
        print("初始化日志管理器完成")
        
        # Install exception handler
        exception_handler.install()
        
        # Initialize theme manager
        print("初始化主题管理器")
        theme_manager = ThemeManager(config_manager)
        print("初始化主题管理器完成")
        
        # Create main window
        print("创建主窗口")
        window = TradingGUI()
        print("创建主窗口完成")
        
        # Show window
        window.show()
        print("显示主窗口完成")
        
        # Start event loop
        return app.exec_()
        
    except Exception as e:
        # 如果logger已经初始化，使用logger记录错误
        if logger is not None:
            logger.error(f"程序启动失败: {str(e)}")
            logger.error(traceback.format_exc())
        else:
            # 如果logger未初始化，打印到控制台
            print(f"程序启动失败: {str(e)}")
            print(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main()) 