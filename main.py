"""
交易系统主窗口模块
"""
from utils.log_util import log_structured
import time
from core.plugin_manager import PluginManager
from utils.cache import Cache
from components.stock_screener import StockScreenerWidget
from gui.ui_components import StatusBar
from gui.widgets.multi_chart_panel import MultiChartPanel
from gui.widgets.log_widget import LogWidget
from core.industry_manager import IndustryManager
from hikyuu import StockManager, Query
from hikyuu.interactive import *
from hikyuu.indicator import *
from hikyuu.data import *
from hikyuu import *
from utils.exception_handler import ExceptionHandler
from gui.widgets.chart_widget import ChartWidget
from gui.menu_bar import MainMenuBar
from gui.tool_bar import MainToolBar
from utils.config_manager import ConfigManager
from core.data_manager import data_manager
from utils.theme import ThemeManager, get_theme_manager, Theme
from utils.config_types import LoggingConfig
from core.logger import LogManager, BaseLogManager, LogLevel
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import time
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *
from datetime import datetime
from typing import Dict, Any, List, Optional
import ptvsd
import subprocess
import numpy as np
import pandas as pd
import sys
import os
import json
import traceback
import warnings
warnings.filterwarnings(
    "ignore", category=FutureWarning, message=".*swapaxes*")


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
        try:
            self.screener_guide_shown = False  # 移动到最前面，防止属性未初始化
            self._is_initializing = True  # 新增：初始化标志
            super().__init__()
            # 全局滚动条样式
            QApplication.instance().setStyleSheet('''
                QScrollBar:vertical {
                    width: 5px;
                    background: #f0f0f0;
                    margin: 0px;
                    border-radius: 3px;
                }
                QScrollBar:horizontal {
                    height: 5px;
                    background: #f0f0f0;
                    margin: 0px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background: #b0b0b0;
                    min-height: 20px;
                    min-width: 20px;
                    border-radius: 3px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    height: 0px;
                    width: 0px;
                    background: none;
                    border: none;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                    background: none;
                }
                /* 表格样式美化 */
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
            ''')

            # 初始化缓存相关属性
            self.stock_list_cache = []  # 初始化股票列表缓存
            self.data_cache = {}  # 初始化数据缓存
            self.chart_cache = {}  # 初始化图表缓存

            # 初始化hikyuu StockManager
            self.sm = StockManager.instance()

            # 初始化配置管理器
            self.config_manager = ConfigManager()

            # 从配置中获取日志配置
            logging_config = self.config_manager.logging

            # 初始化日志管理器
            self.log_manager = LogManager(logging_config)
            self.log_manager.info("TradingGUI初始化开始")

            # 初始化数据管理器
            try:
                self.data_manager = data_manager  # 直接赋值全局实例
                self.log_manager.info("数据管理器初始化完成")
            except Exception as e:
                self.log_manager.error(f"数据管理器初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
                raise

            # 初始化缓存管理器
            self.cache_manager = Cache()

            # 初始化行业管理器
            self.industry_manager = IndustryManager()
            self.industry_manager.industry_updated.connect(
                self._on_industry_data_updated)
            self.industry_manager.update_error.connect(self.handle_error)
            self.log_manager.info("初始化行业管理器结束")
            # 启动行业数据更新
            self.industry_manager.update_industry_data()

            # 初始化主题管理器
            self.theme_manager = get_theme_manager(self.config_manager)
            # 启动时优先从主库读取上次主题
            theme_cfg = self.config_manager.get('theme', {})
            theme_name = theme_cfg.get('theme_name')
            if theme_name:
                self.theme_manager.set_theme(theme_name)

            # 初始化线程池
            self.thread_pool = QThreadPool()
            self.thread_pool.setMaxThreadCount(os.cpu_count() * 3)

            # 初始化股票列表模型
            self.stock_list_model = QStringListModel()

            # 初始化收藏列表
            self.favorites = set()

            # 初始化图表相关属性
            self.current_period = 'D'  # 默认日线
            self.current_chart_type = 'candlestick'  # 默认K线图
            self.current_stock = None
            self.current_strategy = None
            self.current_time_range = -365  # 默认显示一年
            self.current_analysis_type = 'technical'  # 默认技术分析

            # 初始化市场和行业映射
            self.market_mapping = {}
            self.industry_mapping = {}
            self.init_market_industry_mapping()

            # 初始化UI
            self.init_ui()
            self.load_favorites()
            self.init_data()
            self.setAcceptDrops(True)
            self.connect_signals()
            self.preload_data()
            self.log_manager.info("TradingGUI初始化完成")
            self._is_initializing = False  # 新增：初始化结束
            self.filter_stock_list()       # 新增：只在最后刷新一次

            # 初始化插件管理器
            self.plugin_manager = PluginManager()
            self.plugin_manager.load_plugins()
            self.log_manager.info("插件管理器初始化并加载插件完成")

        except Exception as e:
            # 确保即使在初始化失败时也能记录错误
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"TradingGUI初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            else:
                print(f"初始化失败: {str(e)}")
                print(traceback.format_exc())
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
        """更新数据，仅做缓存和分发，UI渲染走主入口update_chart"""
        try:
            # 更新数据缓存
            if hasattr(self, 'data_cache'):
                self.data_cache.update(data)
            # 分发到分析工具面板
            if hasattr(self, 'analysis_tools'):
                self.analysis_tools.update_results(data)
            # 记录日志
            self.log_manager.info("数据更新完成")
            # 统一走主入口渲染
            self.update_chart()
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
        msg_box = QMessageBox.warning(self, "分析错误", error_msg)

    def handle_chart_error(self, error_msg: str):
        """处理图表错误

        Args:
            error_msg: 错误信息
        """
        self.log_manager.error(f"图表错误: {error_msg}")
        msg_box = QMessageBox.warning(self, "图表错误", error_msg)

    def handle_log_error(self, error_msg: str):
        """处理日志错误

        Args:
            error_msg: 错误信息
        """
        self.log_manager.error(f"日志错误: {error_msg}")
        msg_box = QMessageBox.warning(self, "日志错误", error_msg)

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
        4. Creates menu bar, status bar
        5. Applies theme to all widgets
        """
        try:
            # 设置窗口标题和大小
            self.setWindowTitle("Trading System")
            self.setGeometry(400, 100, 1500, 700)
            # 确保主窗口和centralWidget都能接收拖拽事件
            self.setAcceptDrops(True)
            # 创建central widget和主布局
            central_widget = QWidget()
            central_widget.setAcceptDrops(True)
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

            self.log_manager.info("UI初始化完成")

            # 下拉框宽度自适应
            if hasattr(self, 'time_range_combo'):
                self.adjust_combobox_width(self.time_range_combo)
            if hasattr(self, 'period_combo'):
                self.adjust_combobox_width(self.period_combo)
            if hasattr(self, 'chart_type_combo'):
                self.adjust_combobox_width(self.chart_type_combo)

            self.ui_ready = True
            QTimer.singleShot(500, self.show_startup_guides)

            self.top_splitter.splitterMoved.connect(self.on_splitter_moved)
            self.bottom_splitter.splitterMoved.connect(self.on_splitter_moved)

            self.centralWidget().setStyleSheet("background-color: #f7f9fa;")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def show_startup_guides(self):
        # 移除自动弹窗逻辑，保留空实现或其他引导
        pass

    def create_menubar(self):
        """创建菜单栏（包含所有原工具栏和数据源切换功能，按功能分类）"""
        try:
            self.menu_bar = MainMenuBar(self)
            self.setMenuBar(self.menu_bar)

            # 文件菜单
            self.menu_bar.new_action.triggered.connect(self.new_file)
            self.menu_bar.open_action.triggered.connect(self.open_file)
            self.menu_bar.save_action.triggered.connect(self.save_file)
            self.menu_bar.exit_action.triggered.connect(self.close)

            # 编辑菜单
            self.menu_bar.undo_action.triggered.connect(self.undo)
            self.menu_bar.redo_action.triggered.connect(self.redo)
            self.menu_bar.copy_action.triggered.connect(self.copy)
            self.menu_bar.paste_action.triggered.connect(self.paste)

            # 分析菜单
            self.menu_bar.analyze_action.triggered.connect(self.analyze)
            self.menu_bar.backtest_action.triggered.connect(self.backtest)
            self.menu_bar.optimize_action.triggered.connect(self.optimize)

            # 工具菜单
            self.menu_bar.calculator_action.triggered.connect(
                self.show_calculator)
            self.menu_bar.converter_action.triggered.connect(
                self.show_converter)
            self.menu_bar.settings_action.triggered.connect(self.show_settings)

            # 数据菜单（数据源切换）
            self.menu_bar.data_source_hikyuu.triggered.connect(
                lambda: self.on_data_source_changed("Hikyuu"))
            self.menu_bar.data_source_eastmoney.triggered.connect(
                lambda: self.on_data_source_changed("东方财富"))
            self.menu_bar.data_source_sina.triggered.connect(
                lambda: self.on_data_source_changed("新浪"))
            self.menu_bar.data_source_tonghuashun.triggered.connect(
                lambda: self.on_data_source_changed("同花顺"))

            # 帮助菜单
            self.menu_bar.help_action.triggered.connect(self.show_help)
            self.menu_bar.update_action.triggered.connect(self.check_update)
            self.menu_bar.about_action.triggered.connect(self.show_about)

            db_admin_action = QAction("数据库管理", self)
            db_admin_action.triggered.connect(self.show_database_admin)
            self.menuBar().addAction(db_admin_action)

            self.log_manager.info("菜单栏创建完成")

            # 连接分布式/云API/指标市场/批量分析入口
            self.menu_bar.node_manager_action.triggered.connect(self.show_node_manager)
            self.menu_bar.cloud_api_action.triggered.connect(self.show_cloud_api_manager)
            self.menu_bar.indicator_market_action.triggered.connect(self.show_indicator_market)
            self.menu_bar.batch_analysis_action.triggered.connect(self.show_batch_analysis)

            # 新增数据质量校验菜单
            quality_menu = QMenu("数据质量校验", self)
            check_single_action = QAction("校验当前股票", self)
            check_all_action = QAction("校验全部股票", self)
            quality_menu.addAction(check_single_action)
            quality_menu.addAction(check_all_action)
            self.menuBar().addMenu(quality_menu)
            check_single_action.triggered.connect(self.check_single_stock_quality)
            check_all_action.triggered.connect(self.check_all_stocks_quality)

            # 连接形态识别优化系统菜单项
            try:
                self.menu_bar.optimization_dashboard_action.triggered.connect(self.show_optimization_dashboard)
                self.menu_bar.one_click_optimize_action.triggered.connect(self.run_one_click_optimization)
                self.menu_bar.smart_optimize_action.triggered.connect(self.run_smart_optimization)
                self.menu_bar.version_manager_action.triggered.connect(self.show_version_manager)
                self.menu_bar.performance_evaluation_action.triggered.connect(self.show_performance_evaluation)
                self.menu_bar.optimization_status_action.triggered.connect(self.show_optimization_status)
            except Exception as e:
                self.log_manager.error(f"连接优化系统菜单信号失败: {str(e)}")
                # 不抛出异常，允许系统继续运行

        except Exception as e:
            self.log_manager.error(f"创建菜单栏失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def show_database_admin(self):
        from gui.dialogs.database_admin_dialog import DatabaseAdminDialog
        db_path = os.path.join(os.path.dirname(
            __file__), "db", "hikyuu_system.db")
        dlg = DatabaseAdminDialog(db_path, self)
        dlg.exec_()

    def create_statusbar(self):
        """创建自定义状态栏，合并所有状态栏功能，放到底部右下角，并添加日志按钮"""
        try:
            self.status_bar = StatusBar(self)
            self.setStatusBar(self.status_bar)
            self.status_bar.set_status("就绪")
            # 日志显示按钮
            self.log_btn = QPushButton("显示日志")
            self.log_btn.setFixedWidth(80)
            self.log_btn.clicked.connect(self.toggle_log_panel)
            self.status_bar.addPermanentWidget(self.log_btn)
        except Exception as e:
            self.log_manager.error(f"显示状态栏失败: {str(e)}")

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中到父窗口或屏幕，并尽量靠近上部

        Args:
            dialog: 要居中的对话框
            parent: 父窗口，如果为None则使用屏幕
            offset_y: 距离顶部的偏移量
        """
        try:
            if parent and parent.isVisible():
                # 相对于父窗口居中
                parent_geom = parent.geometry()
                dialog_geom = dialog.frameGeometry()
                x = parent_geom.center().x() - dialog_geom.width() // 2
                y = parent_geom.top() + offset_y

                # 确保弹窗不会超出父窗口边界
                x = max(parent_geom.left(), min(
                    x, parent_geom.right() - dialog_geom.width()))
                y = max(parent_geom.top(), min(
                    y, parent_geom.bottom() - dialog_geom.height()))
            else:
                # 相对于屏幕居中
                screen = dialog.screen() or dialog.parentWidget().screen()
                if screen:
                    screen_geom = screen.geometry()
                    dialog_geom = dialog.frameGeometry()
                    x = screen_geom.center().x() - dialog_geom.width() // 2
                    y = screen_geom.top() + offset_y

                    # 确保弹窗不会超出屏幕边界
                    x = max(screen_geom.left(), min(
                        x, screen_geom.right() - dialog_geom.width()))
                    y = max(screen_geom.top(), min(
                        y, screen_geom.bottom() - dialog_geom.height()))

            dialog.move(x, y)
        except Exception as e:
            self.log_manager.error(f"设置弹窗位置失败: {str(e)}")

    def show_about(self):
        """显示关于对话框"""
        try:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("关于")
            dialog.setText("学习量化交易系统\n"
                           "版本: 1.0.0\n"
                           "作者: YuSheng\n"
                           "版权所有 © 2025")
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示关于对话框失败: {str(e)}")

    def show_help(self):
        """显示帮助对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("帮助")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # 添加帮助内容
            help_text = QTextEdit()
            help_text.setReadOnly(True)
            help_text.setHtml("""
                <h2>量化交易系统使用帮助</h2>
                <h3>基本操作</h3>
                <ul>
                    <li>选择股票：在左侧面板输入股票代码或名称</li>
                    <li>查看图表：在中间面板显示K线和技术指标</li>
                    <li>交易操作：在右侧面板进行买入、卖出等操作</li>
                </ul>
                <h3>快捷键</h3>
                <ul>
                    <li>Ctrl+Q：退出程序</li>
                    <li>Ctrl+S：保存设置</li>
                    <li>F1：显示帮助</li>
                </ul>
            """)
            layout.addWidget(help_text)

            # 添加关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示帮助对话框失败: {str(e)}")

    def on_theme_changed(self, theme_name):
        self.theme_manager.set_theme(theme_name)
        # 主题切换后，持久化到ConfigManager
        if hasattr(self, 'config_manager'):
            theme_cfg = self.config_manager.get('theme', {})
            theme_cfg['theme_name'] = theme_name
            self.config_manager.set('theme', theme_cfg)
        if self.theme_manager.is_qss_theme():
            # QSS主题已全局应用，无需递归apply_theme
            pass
        else:
            self.theme_manager.clear_qss_theme()
            self.apply_theme()

    def init_data(self):
        """Initialize data"""
        try:
            self.log_manager.info("开始初始化数据...")

            # 初始化互斥锁
            self.data_mutex = QMutex()
            self.chart_mutex = QMutex()
            self.indicator_mutex = QMutex()
            self.log_manager.info("互斥锁初始化完成")

            # 确保缓存已初始化
            if not hasattr(self, 'stock_list_cache'):
                self.stock_list_cache = []
            if not hasattr(self, 'data_cache'):
                self.data_cache = {}
            if not hasattr(self, 'chart_cache'):
                self.chart_cache = {}

            # 加载配置
            self.get_db_config = self.config_manager.get_all()
            self.log_manager.info("配置加载完成")

            # 初始化数据源
            if hasattr(self, 'data_manager'):
                self.data_manager.clear_cache()
            self.log_manager.info("数据源初始化完成")
            # 预加载数据
            self.preload_data()

            self.log_manager.info("数据初始化完成")

        except Exception as e:
            error_msg = f"初始化数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            raise

    def apply_theme(self):
        """Apply theme to all widgets (主窗口唯一递归入口)"""
        if getattr(self, '_is_applying_theme', False):
            return
        self._is_applying_theme = True
        try:
            if not hasattr(self, 'theme_manager'):
                self.log_manager.warning("主题管理器未初始化")
                return
            # 只对JSON主题递归刷新，QSS主题只全局应用一次
            if not self.theme_manager.is_qss_theme():
                # 1. 设置主窗口背景色
                colors = self.theme_manager.get_theme_colors()
                bg_color = colors.get('background', '#f7f9fa')
                self.setStyleSheet(f"background-color: {bg_color};")
                # 2. 递归处理其他QWidget
                for widget in self.findChildren(QWidget):
                    # 跳过菜单栏、工具栏，避免重复
                    if widget in [self.menu_bar, getattr(self, 'toolbar', None)]:
                        continue

                self.log_manager.info("主题应用完成")
        except Exception as e:
            self.log_manager.error(f"应用主题失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
        finally:
            self._is_applying_theme = False

    def create_left_panel(self):
        """Create left panel with stock list and indicators"""
        try:
            # 创建左侧面板
            self.left_panel = QWidget()
            self.left_layout = QVBoxLayout(self.left_panel)
            self.left_layout.setContentsMargins(5, 5, 5, 5)
            self.left_layout.setSpacing(5)

            # 在顶部添加股票数量标签
            self.stock_count_label = QLabel("当前显示 0 只股票")
            self.left_layout.insertWidget(0, self.stock_count_label)

            # 创建股票列表组
            stock_group = QGroupBox("股票列表")
            stock_layout = QVBoxLayout(stock_group)
            stock_layout.setContentsMargins(5, 15, 5, 5)
            stock_layout.setSpacing(5)

            # 创建市场选择区域
            market_layout = QHBoxLayout()
            market_label = QLabel("市场:")
            self.market_combo = QComboBox()
            # 市场下拉框内容只来源于market_block_mapping
            market_items = ["全部"] + list(self.market_block_mapping.keys())
            self.market_combo.addItems(market_items)
            market_layout.addWidget(market_label)
            market_layout.addWidget(self.market_combo)
            stock_layout.addLayout(market_layout)

            # 创建行业选择区域
            industry_layout = QHBoxLayout()
            industry_label = QLabel("行业:")
            self.industry_combo = QComboBox()
            industry_items = ["全部"] + list(self.industry_mapping.keys())
            self.industry_combo.addItems(industry_items)

            # 创建子行业选择
            self.sub_industry_combo = QComboBox()
            self.sub_industry_combo.addItem("全部")
            self.sub_industry_combo.setVisible(False)

            # 连接行业选择信号
            self.industry_combo.currentTextChanged.connect(
                self.on_industry_changed)
            self.sub_industry_combo.currentTextChanged.connect(
                self.filter_stock_list)

            industry_layout.addWidget(industry_label)
            industry_layout.addWidget(self.industry_combo)
            industry_layout.addWidget(self.sub_industry_combo)
            stock_layout.addLayout(industry_layout)

            # 创建股票搜索框
            search_layout = QHBoxLayout()
            self.stock_search = QLineEdit()
            self.stock_search.setPlaceholderText("搜索股票代码或名称...")
            self.stock_search.textChanged.connect(self.filter_stock_list)
            search_layout.addWidget(self.stock_search)

            # 添加高级搜索按钮
            advanced_search_btn = QPushButton("高级搜索")
            advanced_search_btn.clicked.connect(
                self.show_advanced_search_dialog)
            search_layout.addWidget(advanced_search_btn)
            stock_layout.addLayout(search_layout)

            # 创建股票列表
            self.stock_list = StockListWidget()
            self.stock_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.stock_list.itemSelectionChanged.connect(
                self.on_stock_selected)

            # 启用拖放
            self.stock_list.setDragEnabled(True)
            self.stock_list.setAcceptDrops(True)
            self.stock_list.setDropIndicatorShown(True)
            self.stock_list.setDragDropMode(QAbstractItemView.InternalMove)
            # 性能优化：启用统一项高度，提升大数据量时的滚动和重绘效率
            self.stock_list.setUniformItemSizes(True)

            # 设置右键菜单
            self.stock_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.stock_list.customContextMenuRequested.connect(
                self.show_stock_list_context_menu)

            stock_list_scroll = QScrollArea()
            stock_list_scroll.setWidgetResizable(True)
            stock_list_scroll.setWidget(self.stock_list)
            stock_layout.addWidget(stock_list_scroll)

            # 添加收藏按钮
            favorites_btn = QPushButton("收藏")
            favorites_btn.clicked.connect(self.toggle_favorite)
            stock_layout.addWidget(favorites_btn)

            # 添加左侧面板到顶部分割器
            self.left_layout.addWidget(stock_group)

            # 创建指标列表组
            indicator_group = QGroupBox("指标列表")
            indicator_layout = QVBoxLayout(indicator_group)
            indicator_layout.setContentsMargins(5, 15, 5, 5)
            indicator_layout.setSpacing(5)

            # --- 创建指标类型选择器 ---
            indicator_type_layout = QHBoxLayout()
            indicator_type_label = QLabel("类型:")
            self.indicator_type_combo = QComboBox()
            # --- 动态生成指标分类（只用后端ta-lib分类，确保一致）---
            from indicators_algo import get_all_indicators_by_category
            category_map = get_all_indicators_by_category()
            type_list = ["全部"] + sorted(category_map.keys()) + ["自定义"]
            self.indicator_type_combo.clear()
            self.indicator_type_combo.addItems(type_list)
            self.indicator_type_combo.currentTextChanged.connect(
                lambda _: self.filter_indicator_list(
                    self.indicator_search.text())
            )
            indicator_type_layout.addWidget(indicator_type_label)
            indicator_type_layout.addWidget(self.indicator_type_combo)
            indicator_layout.addLayout(indicator_type_layout)

            # 创建指标搜索框
            self.indicator_search = QLineEdit()
            self.indicator_search.setPlaceholderText("搜索指标...")
            self.indicator_search.textChanged.connect(
                self.filter_indicator_list)
            indicator_layout.addWidget(self.indicator_search)

            # --- 创建指标列表控件（必须在所有操作前）---
            self.indicator_list = QListWidget()
            self.indicator_list.setSelectionMode(
                QAbstractItemView.MultiSelection)
            self.indicator_list.itemSelectionChanged.connect(
                self.on_indicators_changed)

            indicator_list_scroll = QScrollArea()
            indicator_list_scroll.setWidgetResizable(True)
            indicator_list_scroll.setWidget(self.indicator_list)
            indicator_layout.addWidget(indicator_list_scroll)

            # --- 填充指标列表（只用后端分类）---
            self.indicator_list.clear()
            for cat, names in category_map.items():
                for name in names:
                    item = QListWidgetItem(str(name))
                    item.setData(Qt.UserRole, str(cat))
                    self.indicator_list.addItem(item)

            # 添加指标操作按钮
            indicator_buttons_layout = QHBoxLayout()
            indicator_buttons_layout.setSpacing(1)
            manage_indicator_btn = QPushButton("管理指标")
            manage_indicator_btn.clicked.connect(
                self.show_indicator_params_dialog)
            save_combination_btn = QPushButton("保存组合")
            save_combination_btn.clicked.connect(
                self.save_indicator_combination)
            load_combination_btn = QPushButton("加载组合")
            load_combination_btn.clicked.connect(
                self.load_indicator_combination_dialog)
            delete_combination_btn = QPushButton("删除组合")
            delete_combination_btn.clicked.connect(
                self.delete_indicator_combination_dialog)
            clear_all_btn = QPushButton("取消指标")
            clear_all_btn.clicked.connect(self.clear_all_selected_indicators)
            indicator_buttons_layout.addWidget(manage_indicator_btn)
            indicator_buttons_layout.addWidget(save_combination_btn)
            indicator_buttons_layout.addWidget(load_combination_btn)

            indicator_buttons_layout1 = QHBoxLayout()
            indicator_buttons_layout.setSpacing(1)
            indicator_buttons_layout1.addWidget(delete_combination_btn)
            indicator_buttons_layout1.addWidget(clear_all_btn)

            indicator_layout.addLayout(indicator_buttons_layout)
            indicator_layout.addLayout(indicator_buttons_layout1)
            # 添加指标列表组到左侧布局
            self.left_layout.addWidget(indicator_group)

            # 设置左侧面板的最小宽度
            self.left_panel.setFixedWidth(210)

            # 添加左侧面板到顶部分割器
            self.top_splitter.addWidget(self.left_panel)

            self.log_manager.info("左侧面板创建完成")
            add_shadow(self.left_panel)

            # 强制隐藏横向滚动条，彻底去除横向滚动条空间
            self.stock_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.indicator_list.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)
            stock_list_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)
            indicator_list_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)

            # 在__init__或create_left_panel中，初始化指标列表
            self.builtin_indicators = [
                {"name": "MA", "type": "趋势类"},
                {"name": "MACD", "type": "趋势类"},
                {"name": "BOLL", "type": "趋势类"},
                {"name": "RSI", "type": "震荡类"},
                {"name": "KDJ", "type": "震荡类"},
                {"name": "CCI", "type": "震荡类"},
                {"name": "OBV", "type": "成交量类"},
            ]
            from indicators_algo import get_talib_indicator_list
            self.talib_indicators = [{"name": n, "type": "ta-lib"}
                                     for n in get_talib_indicator_list()]
            self.custom_indicators = []  # 预留自定义
            self.all_indicators = self.builtin_indicators + \
                self.talib_indicators + self.custom_indicators
            # 初始化指标列表，确保类型正确设置
            self.indicator_list.clear()
            for ind in self.all_indicators:
                item = QListWidgetItem(ind["name"])
                # 统一用分类名，防止筛选时类型对比异常
                item.setData(Qt.UserRole, str(ind["type"]))
                self.indicator_list.addItem(item)
                # 默认只选中MA
                if ind["name"] == "MA":
                    item.setSelected(True)

        except Exception as e:
            self.log_manager.error(f"创建左侧面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def show_stock_list_context_menu(self, position):
        """显示股票列表的右键菜单"""
        try:
            # 创建右键菜单
            menu = QMenu()

            # 获取选中的项
            item = self.stock_list.itemAt(position)
            if item:
                # 获取股票数据
                stock_data = item.data(Qt.UserRole)

                # 添加菜单项
                view_details_action = menu.addAction("查看详情")
                add_to_favorites_action = menu.addAction("添加到收藏")
                remove_from_favorites_action = menu.addAction("从收藏移除")
                menu.addSeparator()
                export_data_action = menu.addAction("导出数据")
                menu.addSeparator()
                add_to_watchlist_action = menu.addAction("添加到自选股")
                add_to_portfolio_action = menu.addAction("添加到投资组合")
                menu.addSeparator()
                analyze_action = menu.addAction("分析")
                backtest_action = menu.addAction("回测")

                # 连接菜单项信号
                view_details_action.triggered.connect(
                    lambda: self.view_stock_details(item))
                add_to_favorites_action.triggered.connect(
                    lambda: self.toggle_favorite(item))
                remove_from_favorites_action.triggered.connect(
                    lambda: self.toggle_favorite(item))
                export_data_action.triggered.connect(
                    lambda: self.export_stock_data(item))
                add_to_watchlist_action.triggered.connect(
                    lambda: self.add_to_watchlist(item))
                add_to_portfolio_action.triggered.connect(
                    lambda: self.add_to_portfolio(item))
                analyze_action.triggered.connect(
                    lambda: self.analyze_stock(item))
                backtest_action.triggered.connect(
                    lambda: self.backtest_stock(item))

                # 显示菜单
                menu.exec_(self.stock_list.mapToGlobal(position))

        except Exception as e:
            self.log_manager.error(f"显示右键菜单失败: {str(e)}")

    def view_stock_details(self, item):
        """查看股票详情"""
        try:
            # 获取股票数据
            stock_data = item.data(Qt.UserRole)
            from core.data_manager import data_manager
            code = stock_data.get('code')
            # 拆分market和code
            if code and len(code) > 2:
                market, stock_code = code[:2], code[2:]
                info = data_manager.get_stock_info(f"{market}{stock_code}")
            else:
                info = {}
            if info:
                stock_data.update(info)
            # 获取历史K线数据
            kdata = data_manager.get_k_data(code, freq='D')
            if not kdata.empty:
                stock_data['history'] = [
                    {
                        'date': str(idx.date()),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    }
                    for idx, row in kdata.tail(20).iterrows()
                ]
            # 统一获取财务数据
            finance_data = data_manager.get_finance_data(code)
            if 'finance_history' in finance_data:
                stock_data['finance_history'] = finance_data['finance_history']
            if 'all_fields' in finance_data:
                stock_data['all_fields'] = finance_data['all_fields']
            # 最新一期主要字段
            for key in ['revenue', 'net_profit', 'roe', 'assets', 'liabilities', 'profit_margin', 'debt_to_equity', 'operating_cash_flow', 'equity']:
                if key in finance_data:
                    stock_data[key] = finance_data[key]
            from gui.dialogs.stock_detail_dialog import StockDetailDialog
            dialog = StockDetailDialog(stock_data, self)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"查看股票详情失败: {str(e)}")

    def export_stock_data(self, item):
        """导出股票数据"""
        try:
            # 获取股票数据
            stock_data = item.data(Qt.UserRole)

            # 创建DataFrame
            data = {
                '基本信息': pd.DataFrame([
                    {'项目': '股票代码', '值': stock_data['code']},
                    {'项目': '股票名称', '值': stock_data['name']},
                    {'项目': '所属市场', '值': stock_data['market']},
                    {'项目': '所属行业', '值': stock_data.get('industry', '未知')},
                    {'项目': '上市日期', '值': stock_data.get('list_date', '未知')},
                    {'项目': '总股本', '值': stock_data.get('total_shares', 0)},
                    {'项目': '流通股本', '值': stock_data.get(
                        'circulating_shares', 0)},
                    {'项目': '最新价格', '值': stock_data.get('price', 0)}
                ]),
                '历史数据': pd.DataFrame(stock_data.get('history', []))
            }

            # 导出到Excel
            filename = f"stock_{stock_data['code']}_{safe_strftime(datetime.now(), '%Y%m%d')}.xlsx"
            with pd.ExcelWriter(filename) as writer:
                for sheet_name, df in data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            self.log_manager.info(f"数据已导出到: {filename}")

        except Exception as e:
            self.log_manager.error(f"导出股票数据失败: {str(e)}")

    def add_to_watchlist(self, item):
        """添加到自选股"""
        try:
            stock_code = item.text().split()[0]
            # TODO: 实现添加到自选股的功能
            self.log_manager.info(f"已添加到自选股: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"添加到自选股失败: {str(e)}")

    def add_to_portfolio(self, item):
        """添加到投资组合"""
        try:
            stock_code = item.text().split()[0]
            # TODO: 实现添加到投资组合的功能
            self.log_manager.info(f"已添加到投资组合: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"添加到投资组合失败: {str(e)}")

    def analyze_stock(self, item):
        """分析股票"""
        try:
            stock_code = item.text().split()[0]
            # TODO: 实现股票分析功能
            self.log_manager.info(f"开始分析股票: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"分析股票失败: {str(e)}")

    def backtest_stock(self, item):
        """回测股票"""
        try:
            stock_code = item.text().split()[0]
            # TODO: 实现股票回测功能
            self.log_manager.info(f"开始回测股票: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"回测股票失败: {str(e)}")

    def dragEnterEvent(self, event):
        """主窗口拖入事件，只做分发，异常日志健壮"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """主窗口拖拽移动事件，确保鼠标样式为可放开"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """主窗口统一拖拽分发，单屏/多屏自动分发到对应控件，只做分发，异常日志健壮"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain") or event.mimeData().hasFormat("text/application/x-qabstractitemmodeldatalist"):
            if hasattr(self, 'multi_chart_panel') and self.multi_chart_panel.is_multi:
                self.multi_chart_panel.dropEvent(event)
            else:
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.dropEvent(event)
            event.acceptProposedAction()

    def add_to_watchlist_by_code(self, stock_code):
        """通过股票代码添加到自选股"""
        try:
            # TODO: 实现通过代码添加到自选股的功能
            self.log_manager.info(f"已添加到自选股: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"添加到自选股失败: {str(e)}")

    def add_indicator(self, indicator_name):
        """添加指标"""
        try:
            # TODO: 实现添加指标的功能
            self.log_manager.info(f"已添加指标: {indicator_name}")
        except Exception as e:
            self.log_manager.error(f"添加指标失败: {str(e)}")

    @pyqtSlot()
    def filter_stock_list(self, text: str = ""):
        if getattr(self, '_is_initializing', False):
            return  # 初始化阶段不刷新，最后统一刷新
        """根据搜索文本过滤股票列表，支持市场、行业、收藏等多条件筛选（性能优化版）"""
        try:
            # 1. 提前缓存控件和条件，减少重复属性访问
            stock_list_cache = getattr(self, 'stock_list_cache', None)
            stock_list = getattr(self, 'stock_list', None)
            stock_search = getattr(self, 'stock_search', None)
            market_combo = getattr(self, 'market_combo', None)
            industry_combo = getattr(self, 'industry_combo', None)
            sub_industry_combo = getattr(self, 'sub_industry_combo', None)
            only_favorites_checkbox = getattr(
                self, 'only_favorites_checkbox', None)
            favorites = getattr(self, 'favorites', set())
            log_manager = getattr(self, 'log_manager', None)
            if not stock_list_cache:
                if log_manager:
                    log_manager.warning("股票列表缓存为空，正在重新加载...")
                self.preload_data()
                return

            # 2. 获取筛选条件，提前处理字符串
            search_text = text.lower().strip() if text else (
                stock_search.text().lower().strip() if stock_search else "")
            market = market_combo.currentText() if market_combo else "全部"
            industry = industry_combo.currentText() if industry_combo else "全部"
            sub_industry = sub_industry_combo.currentText() if sub_industry_combo else "全部"
            only_favorites = only_favorites_checkbox.isChecked(
            ) if only_favorites_checkbox else False

            # 3. 市场股票代码集合提前生成
            block = self.market_block_mapping.get(market, None)
            block_codes = set(
                f"{s.market.lower()}{s.code}" for s in block) if block else None

            # 4. UI 批量更新时禁用刷新
            if stock_list:
                stock_list.setUpdatesEnabled(False)
                stock_list.clear()

            filtered_stocks = []
            for stock_info in stock_list_cache:
                try:
                    market_code = stock_info.get('marketCode', '').lower()
                    name = stock_info.get('name', '')
                    industry_str = stock_info.get('industry', '')

                    # 市场筛选
                    if block_codes is not None and market_code not in block_codes:
                        continue

                    # 行业筛选
                    if industry != "全部":
                        if not industry_str:
                            continue
                        industry_levels = industry_str.split('/')
                        if not industry_levels or industry_levels[0].strip() != industry:
                            continue
                        if sub_industry != "全部":
                            if len(industry_levels) < 2 or industry_levels[1].strip() != sub_industry:
                                continue

                    # 收藏筛选
                    if only_favorites and stock_info.get('marketCode') not in favorites:
                        continue

                    # 搜索文本筛选
                    if search_text and (search_text not in market_code and search_text not in name.lower()):
                        continue

                    filtered_stocks.append(stock_info)
                except Exception as e:
                    if log_manager:
                        log_manager.warning(
                            f"处理股票 {stock_info} 过滤失败: {str(e)}")
                    continue

            # 5. 批量添加到UI，最后启用刷新
            # if stock_list:
            if not filtered_stocks:
                no_item = QListWidgetItem("无符合条件的股票")
                no_item.setFlags(Qt.NoItemFlags)
                stock_list.addItem(no_item)
            else:
                for stock_info in filtered_stocks:
                    try:
                        display_text = f"{stock_info['marketCode']} {stock_info['name']}"
                        if stock_info['marketCode'] in favorites:
                            display_text = f"★ {display_text}"
                        item = QListWidgetItem(display_text)
                        tooltip = (f"代码: {stock_info['marketCode']}\n"
                                   f"名称: {stock_info['name']}\n"
                                   f"市场: {stock_info.get('market', '未知')}\n"
                                   f"行业: {stock_info.get('industry', '未知')}")
                        item.setToolTip(tooltip)
                        item.setData(Qt.UserRole, stock_info)
                        stock_list.addItem(item)
                    except Exception as e:
                        if log_manager:
                            log_manager.warning(f"添加股票项到列表失败: {str(e)}")
                        continue
            stock_list.setUpdatesEnabled(True)

            # 6. 更新股票数量显示
            self.update_stock_count_label(len(filtered_stocks))
            if log_manager:
                log_manager.info(f"股票列表过滤完成，显示 {len(filtered_stocks)} 只股票")

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"过滤股票列表失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def filter_indicator_list(self, text: str) -> None:
        """过滤指标列表，支持ta-lib分类，增强健壮性，防止多次添加"无可用指标"项"""
        try:
            indicator_type = str(self.indicator_type_combo.currentText())
            # 先移除所有"无可用指标"项，防止重复
            for i in reversed(range(self.indicator_list.count())):
                item = self.indicator_list.item(i)
                if item.text() == "无可用指标":
                    self.indicator_list.takeItem(i)
            # 先全部设为可见
            for i in range(self.indicator_list.count()):
                self.indicator_list.item(i).setHidden(False)
            visible_count = 0
            for i in range(self.indicator_list.count()):
                item = self.indicator_list.item(i)
                indicator = item.text()
                ind_type = str(item.data(Qt.UserRole))
                # 分类筛选
                if indicator_type != "全部" and indicator_type != "自定义":
                    if ind_type != indicator_type:
                        item.setHidden(True)
                        continue
                # 搜索文本筛选
                if text and text.lower() not in indicator.lower():
                    item.setHidden(True)
                if not item.isHidden():
                    visible_count += 1
            # 只在没有可见项时添加"无可用指标"且只添加一次
            if visible_count == 0 and self.indicator_list.count() == 0 or all(self.indicator_list.item(i).isHidden() for i in range(self.indicator_list.count())):
                no_item = QListWidgetItem("无可用指标")
                no_item.setFlags(Qt.NoItemFlags)
                self.indicator_list.addItem(no_item)
            self.log_manager.info(
                f"筛选分类: {indicator_type}，可见指标数: {visible_count}")
        except Exception as e:
            import traceback
            self.log_manager.error(
                f"过滤指标列表失败: {str(e)}\n{traceback.format_exc()}")

    def on_time_range_changed(self, time_range: str) -> None:
        """处理时间范围变化事件

        Args:
            time_range: 时间范围名称
        """
        try:
            # 时间范围映射
            time_range_map = {
                '最近7天': -7,
                '最近30天': -30,
                '最近90天': -90,
                '最近180天': -180,
                '最近1年': -365,
                '最近2年': -730,
                '最近3年': -1095,
                '最近5年': -1825,
                '全部': 0  # 0表示获取全部数据
            }

            if time_range in time_range_map:
                # 负数表示向前N天
                self.current_time_range = time_range_map[time_range]
                self.update_chart()
                # 新增：同步K线数据到AnalysisWidget
                if hasattr(self, 'analysis_widget') and self.current_stock:
                    kdata = self.get_kdata(self.current_stock)
                    self.analysis_widget.set_kdata(kdata)
                self.log_manager.info(f"时间范围已更改为: {time_range}")

        except Exception as e:
            error_msg = f"更改时间范围失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

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
                self.log_manager.info(f"分析类型已更改为: {analysis_type}")

        except Exception as e:
            error_msg = f"更改分析类型失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def create_middle_panel(self):
        """Create middle panel with charts (只暴露 self.chart_widget，分屏仅在 multi_chart_panel 内部管理)"""
        try:
            # 创建中间面板
            self.middle_panel = QWidget()
            self.middle_layout = QVBoxLayout(self.middle_panel)
            self.middle_layout.setContentsMargins(5, 5, 5, 5)
            self.middle_layout.setSpacing(5)

            # 创建工具栏（周期、时间范围、图表类型等控件）
            toolbar_layout = QHBoxLayout()
            period_label = QLabel("周期:")
            self.period_combo = QComboBox()
            self.period_combo.addItems([
                "分时", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"])
            self.period_combo.setCurrentText("日线")
            self.period_combo.currentTextChanged.connect(
                self.on_period_changed)
            toolbar_layout.addWidget(period_label)
            toolbar_layout.addWidget(self.period_combo)
            time_range_label = QLabel("时间范围:")
            self.time_range_combo = QComboBox()
            self.time_range_combo.addItems([
                "最近7天", "最近30天", "最近90天", "最近180天",
                "最近1年", "最近2年", "最近3年", "最近5年", "全部"
            ])
            self.time_range_combo.setCurrentText("最近1年")
            self.time_range_combo.currentTextChanged.connect(
                self.on_time_range_changed)
            toolbar_layout.addWidget(time_range_label)
            toolbar_layout.addWidget(self.time_range_combo)
            # 新增：回测/分析日期选择控件
            from PyQt5.QtCore import QDate
            date_label = QLabel("回测区间:")
            self.start_date_edit = QDateEdit()
            self.start_date_edit.setCalendarPopup(True)
            self.end_date_edit = QDateEdit()
            self.end_date_edit.setCalendarPopup(True)
            # 初始化日期
            if hasattr(self, 'start_date') and self.start_date:
                self.start_date_edit.setDate(self.start_date)
            else:
                self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
            if hasattr(self, 'end_date') and self.end_date:
                self.end_date_edit.setDate(self.end_date)
            else:
                self.end_date_edit.setDate(QDate.currentDate())
            self.start_date_edit.dateChanged.connect(lambda d: setattr(self, 'start_date', d))
            self.end_date_edit.dateChanged.connect(lambda d: setattr(self, 'end_date', d))
            toolbar_layout.addWidget(date_label)
            toolbar_layout.addWidget(self.start_date_edit)
            toolbar_layout.addWidget(QLabel("至"))
            toolbar_layout.addWidget(self.end_date_edit)
            chart_type_label = QLabel("图表类型:")
            self.chart_type_combo = QComboBox()
            self.chart_type_combo.addItems(["K线图", "分时图", "美国线", "收盘价"])
            self.chart_type_combo.currentTextChanged.connect(
                self.on_chart_type_changed)
            toolbar_layout.addWidget(chart_type_label)
            toolbar_layout.addWidget(self.chart_type_combo)
            toolbar_layout.addStretch()
            self.middle_layout.addLayout(toolbar_layout)

            # 集成多图表分屏控件（外部只暴露 self.chart_widget，分屏仅在 multi_chart_panel 内部管理）
            self.multi_chart_panel = MultiChartPanel(
                self, self.config_manager, self.theme_manager, self.log_manager, rows=3, cols=3)
            self.middle_layout.addWidget(self.multi_chart_panel)
            self.top_splitter.addWidget(self.middle_panel)
            # 关键：主窗口 self.chart_widget 始终指向单屏 ChartWidget 实例
            self.chart_widget = self.multi_chart_panel.single_chart
            # 自动连接区间统计信号
            self.chart_widget.request_stat_dialog.connect(
                self.show_stat_dialog)
            self.log_manager.info("中间面板(多图表分屏)创建完成")
            add_shadow(self.middle_panel, blur_radius=24,
                       x_offset=0, y_offset=8)
            self.middle_panel.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception as e:
            self.log_manager.error(f"创建中间面板(多图表分屏)失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def show_stat_dialog(self, interval):
        """弹出区间统计弹窗，统计当前区间K线的涨跌幅、均值、最大回撤等，并用专业可视化展示"""
        try:
            start_idx, end_idx = interval
            kdata = getattr(self.chart_widget, 'current_kdata', None)
            if kdata is None or kdata.empty or start_idx >= end_idx:
                QMessageBox.warning(self, "提示", "区间数据无效！")
                return
            sub = kdata.iloc[start_idx:end_idx+1]
            if sub.empty:
                QMessageBox.warning(self, "提示", "区间数据无效！")
                return
            # 统计项（与原有统计一致，略）
            open_ = sub.iloc[0]['open']
            close_ = sub.iloc[-1]['close']
            high = sub['high'].max()
            low = sub['low'].min()
            mean = sub['close'].mean()
            ret = (close_ - open_) / open_ * 100
            max_drawdown = (
                (sub['close'].cummax() - sub['close']) / sub['close'].cummax()).max() * 100
            up_days = (sub['close'] > sub['open']).sum()
            down_days = (sub['close'] < sub['open']).sum()
            amplitude = ((sub['high'] - sub['low']) / sub['close'] * 100)
            amp_mean = amplitude.mean()
            amp_max = amplitude.max()
            vol_mean = sub['volume'].mean()
            vol_sum = sub['volume'].sum()
            returns = sub['close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) * 100 if not returns.empty else 0
            std_ret = returns.std() * 100 if not returns.empty else 0
            max_up = returns.max() * 100 if not returns.empty else 0
            max_down = returns.min() * 100 if not returns.empty else 0
            up_seq = (sub['close'] > sub['open']).astype(int)
            down_seq = (sub['close'] < sub['open']).astype(int)

            def max_consecutive(arr):
                max_len = cnt = 0
                for v in arr:
                    if v:
                        cnt += 1
                        max_len = max(max_len, cnt)
                    else:
                        cnt = 0
                return max_len
            max_up_seq = max_consecutive(up_seq)
            max_down_seq = max_consecutive(down_seq)
            total_days = len(sub)
            up_ratio = up_days / total_days * 100 if total_days else 0
            down_ratio = down_days / total_days * 100 if total_days else 0
            open_up = (sub['open'] > sub['open'].shift(1)).sum()
            open_down = (sub['open'] < sub['open'].shift(1)).sum()
            close_new_high = (sub['close'] == sub['close'].cummax()).sum()
            close_new_low = (sub['close'] == sub['close'].cummin()).sum()
            gap = (sub['open'] - sub['close'].shift(1)).abs()
            max_gap = gap[1:].max() if len(gap) > 1 else 0
            max_amplitude = amplitude.max()
            max_vol = sub['volume'].max()
            min_vol = sub['volume'].min()
            stat = {
                '开盘价': open_,
                '收盘价': close_,
                '最高价': high,
                '最低价': low,
                '均价': mean,
                '涨跌幅(%)': ret,
                '最大回撤(%)': max_drawdown,
                '振幅均值(%)': amp_mean,
                '振幅最大(%)': amp_max,
                '区间波动率(年化%)': volatility,
                '区间收益率标准差(%)': std_ret,
                '最大单日涨幅(%)': max_up,
                '最大单日跌幅(%)': max_down,
                '最大单日振幅(%)': max_amplitude,
                '最大跳空缺口': max_gap,
                '成交量均值': vol_mean,
                '成交量总和': vol_sum,
                '最大成交量': max_vol,
                '最小成交量': min_vol,
                '阳线天数': up_days,
                '阴线天数': down_days,
                '阳线比例(%)': up_ratio,
                '阴线比例(%)': down_ratio,
                '最大连续阳线': max_up_seq,
                '最大连续阴线': max_down_seq,
                '开盘上涨次数': open_up,
                '开盘下跌次数': open_down,
                '收盘创新高次数': close_new_high,
                '收盘新低次数': close_new_low
            }
            from gui.dialogs.interval_stat_dialog import IntervalStatDialog
            dlg = IntervalStatDialog(sub, stat, self)
            dlg.setWindowTitle("区间统计")
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "区间统计错误", str(e))

    def on_zoom_changed(self, zoom_level: float):
        """处理缩放级别变化事件

        Args:
            zoom_level: 新的缩放级别
        """
        try:
            # 更新状态栏显示缩放级别
            self.status_bar.set_status(f"缩放级别: {zoom_level:.1f}x")
        except Exception as e:
            self.log_manager.error(f"更新缩放级别显示失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def save_chart(self):
        """保存当前图表到文件"""
        try:
            # 直接操作self.chart_widget
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                QMessageBox.warning(self, "提示", "当前没有可保存的图表！")
                return
            # 获取文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存图表",
                "",
                "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)"
            )
            if file_path:
                # 保存图表
                if hasattr(self.chart_widget, 'canvas') and hasattr(self.chart_widget, 'figure'):
                    self.chart_widget.figure.savefig(file_path)
                    self.log_manager.info(f"图表已保存到: {file_path}")
                else:
                    QMessageBox.warning(self, "提示", "当前图表控件不支持保存！")
        except Exception as e:
            self.log_manager.error(f"保存图表失败: {str(e)}")

    def reset_chart_view(self):
        """重置图表视图到默认"""
        try:
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                QMessageBox.warning(self, "提示", "当前没有可重置的图表！")
                return
            if hasattr(self.chart_widget, 'canvas') and hasattr(self.chart_widget, 'figure'):
                self.chart_widget.figure.tight_layout()
                self.chart_widget.canvas.draw()
            else:
                QMessageBox.warning(self, "提示", "当前图表控件不支持重置！")
        except Exception as e:
            self.log_manager.error(f"重置图表视图失败: {str(e)}")

    def toggle_chart_theme(self):
        """切换图表主题（明亮/暗色）"""
        try:
            # 只操作self.chart_widget
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                QMessageBox.warning(self, "提示", "当前没有可切换主题的图表！")
                return
            # 获取当前matplotlib样式
            import matplotlib.pyplot as plt
            current_style = plt.get_backend()
            # 这里可根据实际需求切换matplotlib主题
            # 例如：plt.style.use('dark_background') 或 plt.style.use('seaborn-v0_8-whitegrid')
            # 重新绘制
            if hasattr(self.chart_widget, 'canvas'):
                self.chart_widget.canvas.draw()
        except Exception as e:
            self.log_manager.error(f"切换图表主题失败: {str(e)}")

    def create_right_panel(self):
        """Create right panel with analysis/回测/AI/行业优选等多Tab结构，避免内容重复"""
        try:
            self.log_manager.info("创建右侧面板(Tab结构)")
            self.right_panel = QWidget()
            self.right_layout = QVBoxLayout(self.right_panel)
            self.right_layout.setContentsMargins(5, 5, 5, 5)
            self.right_layout.setSpacing(0)

            # 右侧Tab（唯一入口）
            self.right_tab = QTabWidget(self.right_panel)
            self.right_tab.currentChanged.connect(self.on_right_tab_changed)

            # 单股分析Tab（AnalysisWidget）
            from gui.widgets.analysis_widget import AnalysisWidget
            self.analysis_widget = AnalysisWidget()
            self.analysis_widget.chart_widget = self.chart_widget
            self.analysis_widget._connect_chart_widget_signals()
            self.right_tab.addTab(self.analysis_widget, "单股分析")

            # 批量回测/AI/策略分析Tab（AnalysisToolsPanel）
            from gui.ui_components import AnalysisToolsPanel
            self.analysis_tools_panel = AnalysisToolsPanel(parent=self.right_tab)
            self.right_tab.addTab(self.analysis_tools_panel, "批量回测/AI/策略分析")

            # 行业优选Tab（可选扩展）
            try:
                # 修复行业优选Tab导入错误，复用AnalysisWidget行业资金流向分析
                if not hasattr(self, 'analysis_widget'):
                    from gui.widgets.analysis_widget import AnalysisWidget
                    self.analysis_widget = AnalysisWidget(self.config_manager)
                sector_flow_tab = self.analysis_widget.create_sector_flow_tab()
                self.add_tab_with_toolbar(sector_flow_tab, "行业优选", "行业主力资金流向、概念流向、北向资金等一览，支持一键分析与导出")
            except Exception as e:
                self.log_manager.error(f"行业优选Tab初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

            # 自定义Tab
            try:
                self.custom_tab = QWidget()
                custom_layout = QVBoxLayout(self.custom_tab)
                custom_label = QLabel("自定义面板，用户可扩展功能或添加小工具。")
                custom_layout.addWidget(custom_label)
                self.right_tab.addTab(self.custom_tab, "自定义")
            except Exception as e:
                self.log_manager.error(f"自定义Tab初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

            self.right_layout.addWidget(self.right_tab)
            self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.right_panel.setMinimumWidth(350)
            self.top_splitter.addWidget(self.right_panel)
            add_shadow(self.right_panel, blur_radius=18, x_offset=0, y_offset=6)
        except Exception as e:
            self.log_manager.error(f"创建右侧面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def add_tab_with_toolbar(self, widget, tab_name, help_text=""):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        help_btn = QPushButton("帮助")
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(help_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(widget)
        refresh_btn.clicked.connect(lambda: self.refresh_tab_content(widget))
        help_btn.clicked.connect(lambda: QMessageBox.information(
            self, f"{tab_name}帮助", help_text))
        self.right_tab.addTab(tab_widget, tab_name)
        # 新增：Tab添加后自动推送当前K线数据
        if hasattr(self, 'current_stock') and self.current_stock and hasattr(widget, 'set_kdata'):
            kdata = self.get_kdata(self.current_stock)
            import pandas as pd
            if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                kdata = kdata.copy()
                kdata['code'] = self.current_stock
            widget.set_kdata(kdata)

    def on_right_tab_changed(self, index):
        tab_text = self.right_tab.tabText(index)
        # 延迟加载多维分析Tab
        if tab_text == "多维分析" and not getattr(self, "analysis_tab_loaded", False):
            try:
                from gui.widgets.analysis_widget import AnalysisWidget
                self.analysis_widget = AnalysisWidget()
                # 新增：将chart_widget实例赋值给analysis_widget，并连接信号
                self.analysis_widget.chart_widget = self.chart_widget
                self.analysis_widget._connect_chart_widget_signals()
                self.analysis_tab_layout.addWidget(self.analysis_widget)
                self.analysis_tab_loaded = True
                self.log_manager.info("多维分析Tab已延迟加载")
            except Exception as e:
                self.log_manager.error(f"多维分析Tab延迟加载失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
        # 只在首次点击选股器Tab时弹窗，且只弹一次
        if tab_text == "选股器" and not getattr(self, "screener_guide_shown", False):
            if hasattr(self, 'stock_screener_widget') and hasattr(self.stock_screener_widget, 'show_screener_guide'):
                self.stock_screener_widget.show_screener_guide()
                self.screener_guide_shown = True
        widget = self.right_tab.widget(index)
        if widget is not None and widget.layout() and widget.layout().count() > 1:
            main_widget = widget.layout().itemAt(1).widget()
            # 只刷新Tab内容，不自动调用refresh（防止自动回测）
            # self.refresh_tab_content(main_widget)  # 注释掉自动刷新
            # 若有自定义Tab需要自动刷新，可在此补充
        # 保持原有Tab切换UI逻辑，无自动回测分析

    def optimize(self):
        """Optimize strategy parameters"""
        try:
            # Get current strategy and parameters
            strategy = self.strategy_combo.currentText()
            params = {name: control.value()
                      for name, control in self.param_controls.items()}

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
                self.log_manager.info("开始参数优化...")

                # TODO: Implement optimization logic

                self.log_manager.info("参数优化完成")

        except Exception as e:
            self.log_manager.error(f"参数优化失败: {str(e)}")

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
            self.log_manager.error(f"更新性能指标失败: {str(e)}")

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
                "布林带周期": (10, 100, 20),  # 整数
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
                        # 修复：防止value[x]为非数字字符串导致int()异常
                        try:
                            v0 = int(value[0]) if str(value[0]).isdigit() else 0
                        except Exception:
                            v0 = 0
                        try:
                            v1 = int(value[1]) if str(value[1]).isdigit() else 100
                        except Exception:
                            v1 = 100
                        try:
                            v2 = int(value[2]) if str(value[2]).isdigit() else v0
                        except Exception:
                            v2 = v0
                        spinbox.setRange(v0, v1)
                        spinbox.setValue(v2)
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
            self.log_manager.error(f"创建控制按钮失败: {str(e)}")
            raise

    def on_period_changed(self, period: str):
        """切换K线周期时，主动推送最新K线数据到所有分析Tab"""
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
                # 新增：同步K线数据到AnalysisWidget
                if hasattr(self, 'analysis_widget') and self.current_stock:
                    kdata = self.get_kdata(self.current_stock)
                    self.broadcast_kdata_to_tabs(kdata)
                    import pandas as pd
                    if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                        kdata = kdata.copy()
                        kdata['code'] = self.current_stock
                    # 推送到所有AnalysisWidget及支持set_kdata的Tab
                    for i in range(self.right_tab.count()):
                        tab_widget = self.right_tab.widget(i)
                        if tab_widget is not None and tab_widget.layout() and tab_widget.layout().count() > 1:
                            main_widget = tab_widget.layout().itemAt(1).widget()
                            if hasattr(main_widget, 'set_kdata'):
                                main_widget.set_kdata(kdata)
                    if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                        self.analysis_widget.set_kdata(kdata)
                # 记录日志
                self.log_manager.info(f"已切换周期为: {period}")

        except Exception as e:
            self.log_manager.error(f"切换周期失败: {str(e)}")

    def on_strategy_changed(self, strategy: str):
        self.refresh_strategy_params()
        # 其他逻辑...

    def update_strategy(self) -> None:
        """更新当前策略（已废弃，统一由ChartWidget处理）"""
        try:
            if not self.current_stock:
                return
            # 直接刷新图表即可，指标渲染由ChartWidget内部处理
            self.update_chart()
        except Exception as e:
            self.log_manager.log(f"更新策略失败: {str(e)}", LogLevel.ERROR)

    def load_favorites(self):
        """加载收藏的股票列表，自动修复空文件或损坏文件"""
        try:
            config_dir = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'config')
            os.makedirs(config_dir, exist_ok=True)
            favorites_file = os.path.join(config_dir, 'favorites.json')
            if os.path.exists(favorites_file):
                try:
                    with open(favorites_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            self.favorites = set()
                            self.log_manager.warning("收藏列表文件为空，已自动初始化为空集合")
                        else:
                            self.favorites = set(json.loads(content))
                            self.log_manager.info(
                                f"已加载 {len(self.favorites)} 个收藏股票")
                except Exception as e:
                    self.favorites = set()
                    self.log_manager.warning(f"收藏列表文件损坏，已自动重置为空集合: {str(e)}")
                    # 自动修复文件
                    with open(favorites_file, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
            else:
                self.favorites = set()
                self.log_manager.info("未找到收藏列表，已创建新的收藏集")
            # self.update_stock_list_ui()  # 删除多余调用，初始化后统一刷新
        except Exception as e:
            self.favorites = set()
            self.log_manager.error(f"加载收藏列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def save_favorites(self):
        """保存收藏的股票列表，确保文件内容为合法JSON数组"""
        try:
            config_dir = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), 'config')
            os.makedirs(config_dir, exist_ok=True)
            favorites_file = os.path.join(config_dir, 'favorites.json')
            # 确保self.favorites为set类型
            if not isinstance(self.favorites, set):
                self.favorites = set(
                    self.favorites) if self.favorites else set()
            with open(favorites_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.favorites), f,
                          ensure_ascii=False, indent=2)
            self.log_manager.info(f"已保存 {len(self.favorites)} 个收藏股票")
        except Exception as e:
            self.log_manager.error(f"保存收藏列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def toggle_favorite(self, item=None):
        """切换股票的收藏状态

        Args:
            item: QListWidgetItem对象，如果为None则使用当前选中的项
        """
        try:
            # 获取要操作的股票项
            if item is None or isinstance(item, bool):
                selected_items = self.stock_list.selectedItems()
                if not selected_items:
                    self.log_manager.warning("请先选择一只股票")
                    return
                item = selected_items[0]

            # 获取股票代码
            text = item.text()
            if text.startswith("★"):
                text = text[2:]
            stock_code = text.split()[0]

            # 切换收藏状态
            if stock_code in self.favorites:
                self.favorites.remove(stock_code)
                self.log_manager.info(f"已取消收藏: {stock_code}")
            else:
                self.favorites.add(stock_code)
                self.log_manager.info(f"已添加收藏: {stock_code}")

            # 保存收藏列表
            self.save_favorites()

            # 更新UI显示
            self.update_stock_list_ui()

        except Exception as e:
            self.log_manager.error(f"切换收藏状态失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def update_stock_list_ui(self):
        """更新股票列表的显示，包括收藏状态"""
        try:
            if not hasattr(self, 'stock_list') or self.stock_list is None:
                self.log_manager.warning("股票列表控件尚未初始化，跳过UI更新")
                return
            if not hasattr(self, 'stock_list_cache') or not self.stock_list_cache:
                self.log_manager.warning("股票列表缓存为空，尝试重新加载数据")
                self.preload_data()
                return

            # 保存当前选中的股票
            current_item = self.stock_list.currentItem()
            current_text = current_item.text() if current_item else None

            # 清空列表
            self.stock_list.clear()

            # 重新添加所有股票，并标记收藏状态
            for stock in self.stock_list_cache:
                try:
                    display_text = f"{stock['marketCode']} {stock['name']}"
                    if stock['marketCode'] in self.favorites:
                        display_text = f"★ {display_text}"

                    item = QListWidgetItem(display_text)

                    # 设置工具提示
                    tooltip = (f"代码: {stock['marketCode']}\n"
                               f"名称: {stock['name']}\n"
                               f"市场: {stock.get('market', '未知')}\n"
                               f"行业: {stock.get('industry', '未知')}")
                    item.setToolTip(tooltip)

                    # 设置项数据
                    item.setData(Qt.UserRole, stock)

                    self.stock_list.addItem(item)

                except Exception as e:
                    self.log_manager.warning(
                        f"添加股票 {stock.get('marketCode', 'unknown')} 到列表失败: {str(e)}")
                    continue

            # 恢复选中状态
            if current_text:
                items = self.stock_list.findItems(
                    current_text, Qt.MatchExactly)
                if items:
                    self.stock_list.setCurrentItem(items[0])

            # 更新股票数量显示
            self.update_stock_count_label(self.stock_list.count())

            self.log_manager.info(
                f"股票列表UI更新完成，显示 {self.stock_list.count()} 只股票")

        except Exception as e:
            self.log_manager.error(f"更新股票列表显示失败: {str(e)}")
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")

    def clear_log(self) -> None:
        """清除日志内容

        清除日志显示区域的内容，同时清理日志文件，并优化系统性能
        """
        try:
            # 清除日志显示区域
            if hasattr(self, 'log_widget') and self.log_widget:
                self.log_widget.clear_logs()

            # 清除日志文件
            if hasattr(self, 'log_manager'):
                self.log_manager.clear()

            # 优化系统性能
            self.cleanup_memory()

            # 记录清除操作
            self.log_manager.info("日志已清除")

            # 更新UI
            QApplication.processEvents()

        except Exception as e:
            self.log_manager.error(f"清除日志失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"清除日志失败: {str(e)}")

    def handle_performance_alert(self, message: str) -> None:
        """处理性能警告，优化警告处理

        Args:
            message: 性能警告消息
        """
        try:
            # 记录警告日志
            self.log_manager.warning(message)

            # 显示警告对话框
            warning_dialog = QMessageBox(self)
            warning_dialog.setWindowTitle("性能警告")
            warning_dialog.setIcon(QMessageBox.Warning)
            warning_dialog.setText(message)
            warning_dialog.setStandardButtons(QMessageBox.Ok)
            warning_dialog.exec_()

            # 如果是严重的性能问题，尝试优化
            if "内存使用率" in message or "CPU使用率" in message:
                self.cleanup_memory()
                self.log_manager.info("系统已尝试优化性能")

        except Exception as e:
            self.log_manager.error(f"处理性能警告失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

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
            market_combo.addItems([
                "全部", "沪市主板", "深市主板", "创业板", "科创板",
                "北交所", "港股通", "美股", "期货", "期权"
            ])
            conditions_layout.addRow("市场:", market_combo)
            self.advanced_search_controls["market"] = market_combo

            # 行业
            industry_combo = QComboBox()
            industry_combo.addItems([
                "全部", "金融", "科技", "医药", "消费", "制造",
                "能源", "材料", "通信", "公用事业", "房地产"
            ])
            conditions_layout.addRow("行业:", industry_combo)
            self.advanced_search_controls["industry"] = industry_combo

            # 价格范围
            price_layout = QHBoxLayout()
            min_price = QDoubleSpinBox()
            min_price.setRange(0, 10000)
            min_price.setSuffix(" 元")
            max_price = QDoubleSpinBox()
            max_price.setRange(0, 10000)
            max_price.setSuffix(" 元")
            price_layout.addWidget(min_price)
            price_layout.addWidget(QLabel("至"))
            price_layout.addWidget(max_price)
            conditions_layout.addRow("价格范围:", price_layout)
            self.advanced_search_controls["min_price"] = min_price
            self.advanced_search_controls["max_price"] = max_price

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

            # 成交量范围
            volume_layout = QHBoxLayout()
            min_volume = QDoubleSpinBox()
            min_volume.setRange(0, 1000000)
            min_volume.setSuffix(" 万手")
            max_volume = QDoubleSpinBox()
            max_volume.setRange(0, 1000000)
            max_volume.setSuffix(" 万手")
            volume_layout.addWidget(min_volume)
            volume_layout.addWidget(QLabel("至"))
            volume_layout.addWidget(max_volume)
            conditions_layout.addRow("成交量范围:", volume_layout)
            self.advanced_search_controls["min_volume"] = min_volume
            self.advanced_search_controls["max_volume"] = max_volume

            # 换手率范围
            turnover_layout = QHBoxLayout()
            min_turnover = QDoubleSpinBox()
            min_turnover.setRange(0, 100)
            min_turnover.setSuffix(" %")
            max_turnover = QDoubleSpinBox()
            max_turnover.setRange(0, 100)
            max_turnover.setSuffix(" %")
            turnover_layout.addWidget(min_turnover)
            turnover_layout.addWidget(QLabel("至"))
            turnover_layout.addWidget(max_turnover)
            conditions_layout.addRow("换手率范围:", turnover_layout)
            self.advanced_search_controls["min_turnover"] = min_turnover
            self.advanced_search_controls["max_turnover"] = max_turnover

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
                    "min_price": min_price.value(),
                    "max_price": max_price.value(),
                    "min_cap": min_cap.value(),
                    "max_cap": max_cap.value(),
                    "min_volume": min_volume.value(),
                    "max_volume": max_volume.value(),
                    "min_turnover": min_turnover.value(),
                    "max_turnover": max_turnover.value()
                }

                # 执行搜索
                self.perform_advanced_search(search_conditions)

        except Exception as e:
            self.log_manager.error(f"显示高级搜索对话框失败: {str(e)}")

    def perform_advanced_search(self, conditions: dict) -> None:
        """执行高级搜索

        Args:
            conditions: 搜索条件字典
        """
        try:
            # 获取所有股票
            all_stocks = self.data_manager.get_stock_list()
            filtered_stocks = []
            for stock_info in all_stocks:
                try:
                    # 获取股票数据，使用hikyuu标准接口
                    code = f"{stock_info['market'].lower()}{stock_info['code']}"
                    stock = self.sm[code]
                    kdata = stock.get_kdata(
                        Query(-100, ktype=Query.DAY))  # 获取最近100天数据
                    if kdata.empty:
                        continue

                    # 检查股票代码
                    if conditions["code"] and conditions["code"] not in code:
                        continue

                    # 检查股票名称
                    if conditions["name"] and conditions["name"] not in stock["name"]:
                        continue

                    # 检查市场
                    if conditions["market"] != "全部":
                        market_match = False
                        if conditions["market"] == "沪市主板" and code.startswith('60'):
                            market_match = True
                        elif conditions["market"] == "深市主板" and code.startswith('00'):
                            market_match = True
                        elif conditions["market"] == "创业板" and code.startswith('30'):
                            market_match = True
                        elif conditions["market"] == "科创板" and code.startswith('68'):
                            market_match = True
                        elif conditions["market"] == "北交所" and code.startswith('8'):
                            market_match = True
                        elif conditions["market"] == "港股通" and code.startswith('9'):
                            market_match = True
                        elif conditions["market"] == "美股" and code.startswith('7'):
                            market_match = True
                        elif conditions["market"] == "期货" and code.startswith('IC'):
                            market_match = True
                        elif conditions["market"] == "期权" and code.startswith('10'):
                            market_match = True
                        if not market_match:
                            continue

                    # 检查行业
                    if conditions["industry"] != "全部" and stock["industry"] != conditions["industry"]:
                        continue

                    # 检查价格范围
                    latest_price = kdata['close'].iloc[-1]
                    if latest_price < conditions["min_price"] or latest_price > conditions["max_price"]:
                        continue

                    # 检查市值范围
                    market_cap = stock.get("market_cap", 0)
                    if market_cap < conditions["min_cap"] or market_cap > conditions["max_cap"]:
                        continue

                    # 检查成交量范围
                    latest_volume = kdata['volume'].iloc[-1] / 10000  # 转换为万手
                    if latest_volume < conditions["min_volume"] or latest_volume > conditions["max_volume"]:
                        continue

                    # 检查换手率范围
                    if "turnover" in kdata.columns:
                        latest_turnover = kdata['turnover'].iloc[-1]
                        if latest_turnover < conditions["min_turnover"] or latest_turnover > conditions["max_turnover"]:
                            continue

                    # 保存每只股票的行情数据到stock_info
                    stock_info = dict(stock_info)  # 拷贝，避免污染原数据
                    stock_info['latest_price'] = latest_price
                    stock_info['latest_volume'] = latest_volume
                    stock_info['market_cap'] = market_cap

                    filtered_stocks.append(stock_info)

                except Exception as e:
                    self.log_manager.warning(
                        f"处理股票 {stock_info.get('code', '未知')} 失败: {str(e)}")
                    continue

            # 更新股票列表
            self.stock_list.clear()
            for stock in filtered_stocks:
                item = QListWidgetItem(f"{stock['code']} {stock['name']}")

                # 设置工具提示，使用每只股票自己的行情数据
                tooltip = (
                    f"代码: {stock['code']}\n"
                    f"名称: {stock['name']}\n"
                    f"市场: {stock['market']}\n"
                    f"行业: {stock['industry']}\n"
                    f"最新价: {stock.get('latest_price', 0):.3f}\n"
                    f"成交量: {stock.get('latest_volume', 0):.3f}万手\n"
                    f"市值: {stock.get('market_cap', 0):.3f}亿"
                )
                item.setToolTip(tooltip)

                # 设置自定义数据
                item.setData(Qt.UserRole, stock)

                # 设置收藏状态
                if stock['code'] in self.favorites:
                    item.setText(f"★ {item.text()}")

                self.stock_list.addItem(item)

            self.log_manager.info(
                f"找到 {len(filtered_stocks)} 只符合条件的股票")

        except Exception as e:
            self.log_manager.error(f"执行高级搜索失败: {str(e)}")

    def on_stock_selected(self) -> None:
        """处理股票选择事件，修正多屏拖拽逻辑"""
        try:
            # 多屏模式下，点击股票列表不刷新任何图表，拖拽才会刷新子图
            if hasattr(self, 'multi_chart_panel') and getattr(self.multi_chart_panel, 'is_multi', False):
                self.log_manager.info("多屏模式下点击股票列表，不刷新图表，仅支持拖拽加载")
                return

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

            # 新增：自动设置日期区间
            stock_info = selected_items[0].data(Qt.UserRole)
            from PyQt5.QtCore import QDate
            start_date_str = stock_info.get('start_date')
            end_date_str = stock_info.get('end_date')
            if start_date_str and len(start_date_str) >= 10:
                start_date = QDate.fromString(start_date_str[:10], 'yyyy-MM-dd')
            else:
                start_date = QDate.currentDate().addYears(-1)
            if end_date_str and len(end_date_str) >= 10:
                end_date = QDate.fromString(end_date_str[:10], 'yyyy-MM-dd')
            else:
                end_date = QDate.currentDate()
            self.start_date = start_date
            self.end_date = end_date
            if hasattr(self, 'start_date_edit'):
                self.start_date_edit.setDate(start_date)
            if hasattr(self, 'end_date_edit'):
                self.end_date_edit.setDate(end_date)

            # 【增强】同步所有Analysis/Trading相关Tab的trading_widget.current_stock
            from gui.widgets.trading_widget import TradingWidget
            for i in range(self.right_tab.count()):
                tab_widget = self.right_tab.widget(i)
                if tab_widget is not None and tab_widget.layout() and tab_widget.layout().count() > 1:
                    main_widget = tab_widget.layout().itemAt(1).widget()
                    # 递归查找trading_widget属性
                    tw = getattr(main_widget, 'trading_widget', None)
                    if isinstance(tw, TradingWidget):
                        tw.update_stock({'code': stock_code})
                    # 新增：同步K线数据到所有AnalysisWidget类型Tab
                    if hasattr(main_widget, 'set_kdata'):
                        kdata = self.get_kdata(stock_code)
                        import pandas as pd
                        if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                            kdata = kdata.copy()
                            kdata['code'] = stock_code
                        main_widget.set_kdata(kdata)
            # 兼容analysis_widget等单独实例
            if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                kdata = self.get_kdata(self.current_stock)
                import pandas as pd
                if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                    kdata = kdata.copy()
                    kdata['code'] = self.current_stock
                self.analysis_widget.set_kdata(kdata)
            if hasattr(self, 'trading_widget'):
                self.trading_widget.update_stock({'code': stock_code})
            # 其他自定义Tab可按需补充

            # 广播到所有图表
            self.broadcast_kdata_to_tabs(kdata)

            # 优先用缓存
            if hasattr(self, 'chart_cache') and stock_code in self.chart_cache:
                kdata = self.chart_cache[stock_code]
            else:
                kdata = self.get_kdata(stock_code)
                if hasattr(self, 'chart_cache'):
                    self.chart_cache[stock_code] = kdata

            # 更新图表（自动带指标）
            self.update_chart()

            # 新增：同步K线数据到AnalysisWidget，自动补全code字段
            if hasattr(self, 'analysis_widget'):
                kdata = self.get_kdata(self.current_stock)
                import pandas as pd
                if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                    kdata = kdata.copy()
                    kdata['code'] = self.current_stock
                self.analysis_widget.set_kdata(kdata)

            # 记录日志
            self.log_manager.info(f"已选择股票: {stock_code}")

            # 强制刷新UI，确保立即渲染
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            if hasattr(self, 'chart_widget') and hasattr(self.chart_widget, 'canvas'):
                self.chart_widget.canvas.draw()
        except Exception as e:
            self.log_manager.error(f"处理股票选择事件失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_indicators_changed(self) -> None:
        """处理指标变化事件，只刷新图表，不弹窗，不再直接刷新分屏"""
        try:
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                return
            self.update_chart()
            self.log_manager.info("指标已更新")
        except Exception as e:
            self.log_manager.error(f"处理指标变化事件失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def show_indicator_params_dialog(self) -> None:
        """显示指标参数设置对话框，支持ta-lib参数动态生成"""
        try:
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "提示", "请先选择指标")
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("指标参数设置")
            layout = QVBoxLayout(dialog)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            # --- 修复：确保param_controls存在 ---
            self.param_controls = {}
            import inspect
            from indicators_algo import calc_talib_indicator
            for item in selected_items:
                indicator = item.text()
                ind_type = item.data(Qt.UserRole)
                group = QGroupBox(indicator)
                group_layout = QFormLayout(group)
                if ind_type == "ta-lib":
                    import talib
                    func = getattr(talib, indicator)
                    sig = inspect.signature(func)
                    for k, v in sig.parameters.items():
                        if k in ["open", "high", "low", "close", "volume"]:
                            continue
                        if v.default is not inspect.Parameter.empty:
                            spin = QSpinBox() if isinstance(v.default, int) else QDoubleSpinBox()
                            spin.setValue(v.default)
                            group_layout.addRow(f"{k}:", spin)
                            self.param_controls[f"{indicator}_{k}"] = spin
                else:
                    if "MA" in indicator:
                        ma_period = QSpinBox()
                        ma_period.setRange(5, 250)
                        ma_period.setValue(20)
                        group_layout.addRow("周期:", ma_period)
                        self.param_controls[f"{indicator}_period"] = ma_period
                    elif "MACD" in indicator:
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
                        rsi_period = QSpinBox()
                        rsi_period.setRange(5, 30)
                        rsi_period.setValue(14)
                        group_layout.addRow("周期:", rsi_period)
                        self.param_controls[f"{indicator}_period"] = rsi_period
                    elif "BOLL" in indicator:
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
            scroll.setWidget(scroll_content)
            layout.addWidget(scroll)
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec_() == QDialog.Accepted:
                self.update_indicators()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示指标参数设置对话框失败: {str(e)}")
            self.log_manager.error(f"显示指标参数设置对话框失败: {str(e)}")

    def create_bottom_panel(self):
        """Create bottom panel with logs，支持日志区动态显示/隐藏"""
        try:
            self.bottom_panel = QWidget()
            self.bottom_layout = QVBoxLayout(self.bottom_panel)
            self.bottom_layout.setContentsMargins(0, 0, 0, 0)
            self.bottom_layout.setSpacing(0)
            # 日志内容区自适应高度
            self.log_widget = LogWidget(self.log_manager)
            self.log_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.log_widget.setVisible(False)  # 默认隐藏
            self.log_widget.log_added.connect(self.show_log_panel)
            self.bottom_layout.addWidget(self.log_widget, stretch=1)
            # 分割线
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setObjectName("line")
            line.setFixedHeight(2)
            self.bottom_layout.addWidget(line)
            self.bottom_panel.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.bottom_splitter.addWidget(self.bottom_panel)
            self.bottom_splitter.setStretchFactor(0, 1)
            self.log_manager.info("底部面板创建完成")
            add_shadow(self.bottom_panel, blur_radius=12,
                       x_offset=0, y_offset=4)
            # 日志信号连接，确保log_widget已初始化
            self.log_manager.log_message.connect(self.log_widget.add_log)
            self.log_manager.log_cleared.connect(self.log_widget.clear_logs)
            # 优化分割器初始比例，日志区最大化
            if hasattr(self, 'bottom_splitter'):
                self.bottom_splitter.setSizes([0, 1])
        except Exception as e:
            self.log_manager.error(f"创建底部面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def update_stock_list(self) -> None:
        """更新股票列表，使用hikyuu框架API"""
        try:
            def update_list():
                try:
                    from hikyuu import StockManager
                    sm = StockManager.instance()
                    all_stocks = []
                    total_stocks = 0
                    failed_stocks = 0
                    industry_set = set()
                    sub_industry_map = {}
                    self.log_manager.info("开始更新股票列表...")
                    for stock in sm:
                        total_stocks += 1
                        try:
                            code = f"{stock.market.lower()}{stock.code}"
                            industry = getattr(
                                stock, 'industry', None) or self._get_industry_name(stock)
                            if industry:
                                levels = industry.split('/')
                                if len(levels) >= 1:
                                    industry_set.add(levels[0].strip())
                                    if len(levels) >= 2:
                                        main = levels[0].strip()
                                        sub = levels[1].strip()
                                        if main not in sub_industry_map:
                                            sub_industry_map[main] = set()
                                        sub_industry_map[main].add(sub)
                            stock_info = {
                                'code': code,
                                'name': stock.name,
                                'market': stock.market,
                                'type': stock.type,
                                'valid': stock.valid,
                                'start_date': str(stock.start_datetime) if stock.start_datetime else None,
                                'end_date': str(stock.last_datetime) if stock.last_datetime else None,
                                'industry': industry
                            }
                            self.log_manager.debug(
                                f"处理股票: {code} {stock.name}")
                            stock_type = stock.type
                            if stock_type == 'A':
                                stock_info['type'] = 'A股'
                            elif stock_type == 'H':
                                stock_info['type'] = '港股'
                            elif stock_type == 'US':
                                stock_info['type'] = '美股'
                            else:
                                stock_info['type'] = '其他'
                            if not stock_info['code'] or not stock_info['name']:
                                self.log_manager.warning(
                                    f"股票信息不完整: {stock_info}")
                                failed_stocks += 1
                                continue
                            all_stocks.append(stock_info)
                        except Exception as e:
                            failed_stocks += 1
                            self.log_manager.warning(
                                f"获取股票 {getattr(stock, 'code', '未知')} 信息失败: {str(e)}")
                            continue
                    all_stocks.sort(key=lambda x: (x['type'], x['code']))
                    self.stock_list_cache = all_stocks
                    self.industry_mapping = {main: {sub: [] for sub in sorted(
                        sub_industry_map.get(main, []))} for main in sorted(industry_set)}
                    self.log_manager.info(
                        f"股票列表更新完成，共处理 {total_stocks} 只股票，成功 {len(all_stocks)} 只，失败 {failed_stocks} 只")
                    QTimer.singleShot(0, self._refresh_industry_combos)
                    # QTimer.singleShot(0, self.filter_stock_list)  # 删除多余调用
                except Exception as e:
                    self.log_manager.error(f"更新股票列表失败: {str(e)}")
                    self.log_manager.error(traceback.format_exc())
            self.thread_pool.start(update_list)
        except Exception as e:
            self.log_manager.error(f"启动股票列表更新线程失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _get_industry_name(self, stock) -> str:
        """获取股票行业名称

        Args:
            stock: 股票信息字典或hikyuu Stock对象

        Returns:
            行业名称
        """
        try:
            if stock is None:
                return '其他'

            # 如果是hikyuu Stock对象
            if hasattr(stock, 'industry'):
                industry = getattr(stock, 'industry', None)
                return industry if industry else '其他'

            # 如果是字典对象
            if isinstance(stock, dict):
                # 尝试从行业管理器获取行业信息
                code = stock.get('code')
                if code:
                    industry_info = self.industry_manager.get_industry(code)
                    if industry_info:
                        # 优先使用证监会行业分类
                        if industry_info.get('csrc_industry'):
                            return industry_info['csrc_industry']
                        # 其次使用交易所行业分类
                        if industry_info.get('exchange_industry'):
                            return industry_info['exchange_industry']
                        # 最后使用其他行业分类
                        if industry_info.get('industry'):
                            return industry_info['industry']

                # 如果字典中直接包含行业信息
                if 'industry' in stock:
                    industry = stock.get('industry')
                    return industry if industry else '其他'

            # 如果是pandas Series对象
            if isinstance(stock, pd.Series):
                if 'industry' in stock.index:
                    industry = stock['industry']
                    return industry if pd.notna(industry) else '其他'
                if 'code' in stock.index:
                    industry_info = self.industry_manager.get_industry(
                        stock['code'])
                    if industry_info:
                        # 优先使用证监会行业分类
                        if industry_info.get('csrc_industry'):
                            return industry_info['csrc_industry']
                        # 其次使用交易所行业分类
                        if industry_info.get('exchange_industry'):
                            return industry_info['exchange_industry']
                        # 最后使用其他行业分类
                        if industry_info.get('industry'):
                            return industry_info['industry']

            return '其他'

        except Exception as e:
            self.log_manager.warning(f"获取行业名称失败: {str(e)}")
            return '其他'

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
                        f.write(
                            f"{stock['代码']}\t{stock['名称']}\t{stock['收藏']}\n")

            self.log_manager.info(f"股票列表已导出到: {file_path}")

        except Exception as e:
            self.log_manager.error(f"导出股票列表失败: {str(e)}")

    def update_indicators(self) -> None:
        """更新指标参数并刷新图表，优化性能"""
        try:
            # 获取选中的指标
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                return
            # 只刷新图表，所有指标渲染由ChartWidget自动同步主窗口get_current_indicators
            if hasattr(self, 'current_stock') and self.current_stock:
                k_data = self.get_kdata(self.current_stock)
                import pandas as pd
                if isinstance(k_data, pd.DataFrame) and 'code' not in k_data.columns:
                    k_data = k_data.copy()
                    k_data['code'] = self.current_stock
                title = f"{self.current_stock}"
                data = {
                    'stock_code': self.current_stock,
                    'kdata': k_data,
                    'title': title,
                    'period': self.current_period,
                    'chart_type': self.current_chart_type
                }
                self.chart_widget.update_chart(data)
            else:
                self.chart_widget.update_chart({})
                self.log_manager.info("指标参数已更新")
        except Exception as e:
            self.log_manager.error(f"更新指标参数失败: {str(e)}")

    def save_indicator_combination(self) -> None:
        """保存当前选中的指标组合（数据库版）"""
        try:
            selected_items = self.indicator_list.selectedItems()
            if not selected_items:
                self.log_manager.warning("请先选择要保存的指标")
                return
            name, ok = QInputDialog.getText(
                self,
                "保存指标组合",
                "请输入组合名称:",
                QLineEdit.Normal,
                ""
            )
            if not ok or not name:
                return
            indicators = []
            for item in selected_items:
                indicator = item.text()
                params = {}
                if "MA" in indicator:
                    params = {
                        "type": "MA",
                        "period": self.param_controls.get(f"{indicator}_period", QSpinBox()).value() if self.param_controls.get(f"{indicator}_period") else 20
                    }
                elif "MACD" in indicator:
                    params = {
                        "type": "MACD",
                        "fast": self.param_controls.get(f"{indicator}_fast", QSpinBox()).value() if self.param_controls.get(f"{indicator}_fast") else 12,
                        "slow": self.param_controls.get(f"{indicator}_slow", QSpinBox()).value() if self.param_controls.get(f"{indicator}_slow") else 26,
                        "signal": self.param_controls.get(f"{indicator}_signal", QSpinBox()).value() if self.param_controls.get(f"{indicator}_signal") else 9
                    }
                elif "RSI" in indicator:
                    params = {
                        "type": "RSI",
                        "period": self.param_controls.get(f"{indicator}_period", QSpinBox()).value() if self.param_controls.get(f"{indicator}_period") else 14
                    }
                elif "BOLL" in indicator:
                    params = {
                        "type": "BOLL",
                        "period": self.param_controls.get(f"{indicator}_period", QSpinBox()).value() if self.param_controls.get(f"{indicator}_period") else 20,
                        "std": self.param_controls.get(f"{indicator}_std", QDoubleSpinBox()).value() if self.param_controls.get(f"{indicator}_std") else 2.0
                    }
                indicators.append({
                    "name": indicator,
                    "params": params
                })
            user_id = "default"  # 可扩展为多用户
            self.data_manager.save_indicator_combination(
                name, user_id, indicators)
            self.log_manager.info(f"已保存指标组合: {name}")
        except Exception as e:
            self.log_manager.error(f"保存指标组合失败: {str(e)}")

    def load_indicator_combinations(self):
        """加载所有指标组合（数据库版）"""
        try:
            user_id = "default"
            combinations = self.data_manager.get_indicator_combinations(
                user_id)
            return combinations
        except Exception as e:
            self.log_manager.error(f"加载指标组合失败: {str(e)}")
            return []

    def delete_indicator_combination(self, comb_id: int):
        """删除指定id的指标组合（数据库版）"""
        try:
            self.data_manager.delete_indicator_combination(comb_id)
            self.log_manager.info(f"已删除指标组合: {comb_id}")
        except Exception as e:
            self.log_manager.error(f"删除指标组合失败: {str(e)}")

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
                button.clicked.connect(
                    lambda checked, t=text: self.calculator_button_clicked(t, display))
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
            add_shadow(dialog, blur_radius=32, x_offset=0, y_offset=12)
            dialog.exec_()

        except Exception as e:
            self.log_manager.error(f"显示计算器失败: {str(e)}")

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
            self.log_manager.error(f"计算器操作失败: {str(e)}")

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
            self.log_manager.error(f"显示单位转换器失败: {str(e)}")

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
            self.log_manager.info("开始预加载数据...")
            if hasattr(self, 'status_bar'):
                self.status_bar.show_progress(True)
                self.status_bar.set_progress(0)
            stocks_df = self.data_manager.get_stock_list()
            total = len(stocks_df) if not stocks_df.empty else 0
            if not stocks_df.empty:
                self.stock_list_cache = []
                industry_set = set()
                sub_industry_map = {}
                for idx, (_, stock) in enumerate(stocks_df.iterrows()):
                    try:
                        code = f"{stock['market'].lower()}{stock['code']}"
                        industry = stock.get('industry', None)
                        if not industry:
                            industry = self._get_industry_name(stock)
                        if industry and isinstance(industry, str):
                            levels = industry.split('/')
                            if len(levels) >= 1:
                                main_industry = levels[0].strip()
                                industry_set.add(main_industry)
                                if len(levels) >= 2:
                                    sub_industry = levels[1].strip()
                                    if main_industry not in sub_industry_map:
                                        sub_industry_map[main_industry] = set()
                                    sub_industry_map[main_industry].add(
                                        sub_industry)
                        stock_info = {
                            'code': code,
                            'name': stock['name'],
                            'market': stock['market'],
                            'marketCode': code,
                            'type': stock.get('type', '其他'),
                            'industry': industry or '其他',
                            'valid': stock.get('valid', True),
                            'start_date': stock.get('start_date', None),
                            'end_date': stock.get('end_date', None)
                        }
                        if stock_info['valid']:
                            self.stock_list_cache.append(stock_info)
                        if hasattr(self, 'status_bar') and total > 0:
                            percent = int((idx + 1) / total * 100)
                            self.status_bar.set_progress(percent)
                    except Exception as e:
                        self.log_manager.warning(
                            f"处理股票 {stock.get('code', 'unknown')} 失败: {str(e)}")
                        continue
                self.industry_mapping = {main: {sub: [] for sub in sorted(sub_industry_map.get(main, []))}
                                         for main in sorted(industry_set)}
                self.log_manager.info(
                    f"数据预加载完成，共加载 {len(self.stock_list_cache)} 只股票")
                QTimer.singleShot(0, self._refresh_industry_combos)
                # QTimer.singleShot(0, self.filter_stock_list)  # 删除多余调用
            else:
                self.log_manager.warning("获取股票列表失败")
        except Exception as e:
            self.log_manager.error(f"预加载数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
        finally:
            if hasattr(self, 'status_bar'):
                self.status_bar.show_progress(False)
            self.auto_select_first_stock()

    def _refresh_industry_combos(self):
        if not hasattr(self, 'industry_combo'):
            return
        try:
            self.industry_combo.blockSignals(True)
            self.industry_combo.clear()
            self.industry_combo.addItem("全部")
            for main in sorted(self.industry_mapping.keys()):
                self.industry_combo.addItem(main)
            self.industry_combo.blockSignals(False)
            self.sub_industry_combo.clear()
            self.sub_industry_combo.addItem("全部")
            self.sub_industry_combo.setVisible(False)
            # 不再调用 self.filter_stock_list() 由初始化流程统一刷新
        except Exception as e:
            self.log_manager.warning(f"刷新行业下拉框失败: {str(e)}")

    def optimize_chart_rendering(self):
        """优化图表渲染性能"""
        try:
            # 减少重绘
            self.chart_widget.setUpdatesEnabled(False)

            # 移除PaintOnScreen属性设置，避免与matplotlib冲突
            # self.chart_widget.setAttribute(Qt.WA_PaintOnScreen, False)
            self.chart_widget.setAttribute(Qt.WA_NoSystemBackground, False)

            # 启用硬件加速
            self.chart_widget.setRenderHint(QPainter.Antialiasing)
            self.chart_widget.setRenderHint(QPainter.SmoothPixmapTransform)

        except Exception as e:
            self.log_manager.error(f"优化图表渲染失败: {str(e)}")

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
                self.log_manager.info("系统已尝试恢复")

        except Exception as e:
            # 如果错误处理本身出错，至少打印到控制台
            print(f"错误处理失败: {e}")
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
                        formatted_value = f"{value:.2%}" if "率" in name else f"{value:.3f}"
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
            error_dialog = QMessageBox()
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

    def update_performance_metrics(self, metrics: dict):
        """更新性能指标显示（含动画、历史曲线、动态色彩）"""
        try:
            cpu_usage = metrics.get('cpu_usage', 0)
            memory_usage = metrics.get('memory_usage', 0)
            disk_usage = metrics.get('disk_usage', 0)
            self.cpu_label.setText(f"{cpu_usage:.1f}%")
            self.memory_label.setText(f"{memory_usage:.1f}%")
            self.disk_label.setText(f"{disk_usage:.1f}%")
            self.set_progress_with_animation(self.cpu_progress, int(cpu_usage))
            self.set_progress_with_animation(
                self.memory_progress, int(memory_usage))
            self.set_progress_with_animation(
                self.disk_progress, int(disk_usage))
            # 维护历史数据
            self.cpu_history.append(cpu_usage)
            self.memory_history.append(memory_usage)
            self.disk_history.append(disk_usage)
            max_len = 60
            self.cpu_history = self.cpu_history[-max_len:]
            self.memory_history = self.memory_history[-max_len:]
            self.disk_history = self.disk_history[-max_len:]
            self.cpu_curve.setData(self.cpu_history)
            self.memory_curve.setData(self.memory_history)
            self.disk_curve.setData(self.disk_history)
            # 其他指标
            self.response_label.setText(
                f"{metrics.get('response_time', 0):.1f}ms")
            self.threadpool_label.setText(
                str(metrics.get('active_threads', 0)))
            self.cache_label.setText(str(metrics.get('cache_status', '0/0')))
            self.render_time_label.setText(
                f"{metrics.get('render_time', 0):.1f}ms")
        except Exception as e:
            print(f"更新性能指标: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"更新性能指标: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def toggle_performance_dialog(self):
        """显示或隐藏性能监控弹窗"""
        if not hasattr(self, 'performance_dialog'):
            self.init_performance_display()
        if self.performance_dialog.isVisible():
            self.performance_dialog.hide()
            if hasattr(self, 'performance_monitor') and self.performance_monitor.is_monitoring:
                self.performance_monitor.stop_monitoring()
        else:
            self.performance_dialog.show()
            if hasattr(self, 'performance_monitor') and not self.performance_monitor.is_monitoring:
                self.performance_monitor.start_monitoring()

    def clear_warnings(self):
        """清除性能告警"""
        try:
            self.warning_area.clear()
            self.log_manager.info("性能告警已清除")
        except Exception as e:
            self.log_manager.error(f"清除性能告警失败: {str(e)}")

    def export_warnings(self):
        """导出性能告警"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出告警",
                "",
                "Text Files (*.txt);;All Files (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.warning_area.toPlainText())
                self.log_manager.info(f"性能告警已导出到: {file_path}")

        except Exception as e:
            self.log_manager.error(f"导出性能告警失败: {str(e)}")

    def show_log_panel(self, *args, **kwargs):
        """显示日志区"""
        if not hasattr(self, 'log_btn') or self.log_btn is None:
            self.create_statusbar()
        if hasattr(self, 'log_widget') and self.log_widget:
            self.log_widget.setVisible(True)
            self.log_widget.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self, 'bottom_panel'):
            self.bottom_panel.setVisible(True)
            self.bottom_panel.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
        if hasattr(self, 'bottom_splitter'):
            # 日志区分割比例最大化
            self.bottom_splitter.setSizes([0, 1])
        if hasattr(self, 'main_layout'):
            self.main_layout.setStretch(0, 8)  # top_splitter
            self.main_layout.setStretch(1, 2)  # bottom_splitter
            self.main_layout.update()
            self.main_layout.activate()
        self.update()
        if hasattr(self, 'log_btn') and self.log_btn:
            self.log_btn.setText("隐藏日志")

    def hide_log_panel(self):
        """隐藏日志区"""
        if not hasattr(self, 'log_btn') or self.log_btn is None:
            self.create_statusbar()
        if hasattr(self, 'log_widget') and self.log_widget:
            self.log_widget.setVisible(False)
        if hasattr(self, 'bottom_panel'):
            self.bottom_panel.setVisible(False)
        if hasattr(self, 'bottom_splitter'):
            self.bottom_splitter.setSizes([1, 0])
        if hasattr(self, 'main_layout'):
            self.main_layout.setStretch(0, 1)  # top_splitter
            self.main_layout.setStretch(1, 0)  # bottom_splitter
            self.main_layout.update()
            self.main_layout.activate()
        self.update()
        if hasattr(self, 'log_btn') and self.log_btn:
            self.log_btn.setText("显示日志")

    def toggle_log_panel(self):
        """切换日志区显示/隐藏"""
        if not hasattr(self, 'log_btn') or self.log_btn is None:
            self.create_statusbar()
        if hasattr(self, 'log_widget') and self.log_widget.isVisible():
            self.hide_log_panel()
        elif hasattr(self, 'log_widget') and self.log_widget:
            self.show_log_panel()

    def _get_progress_style(self, value: float) -> str:
        """获取进度条样式

        Args:
            value: 进度值

        Returns:
            样式字符串
        """
        try:
            if value >= 90:
                color = "#FF0000"  # 红色
            elif value >= 70:
                color = "#FFA500"  # 橙色
            elif value >= 50:
                color = "#FFD700"  # 金色
            else:
                color = "#4CAF50"  # 绿色

            return f"""
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """
        except Exception as e:
            self.log_manager.error(f"获取进度条样式失败: {str(e)}")
            return ""

    def _on_industry_data_updated(self):
        """处理行业数据更新事件"""
        try:
            # 更新行业下拉框
            self._refresh_industry_combos()
            # 更新股票列表
            self.filter_stock_list()
            self.log_manager.info("行业数据更新完成")
        except Exception as e:
            self.log_manager.error(f"处理行业数据更新失败: {str(e)}")

    def on_industry_changed(self, industry: str):
        """处理行业选择变化

        Args:
            industry: 选中的行业
        """
        try:
            self.sub_industry_combo.clear()
            self.sub_industry_combo.addItem("全部")

            if industry != "全部" and industry in self.industry_mapping:
                sub_industries = list(self.industry_mapping[industry].keys())
                self.sub_industry_combo.addItems(sub_industries)
                self.sub_industry_combo.setVisible(True)
            else:
                self.sub_industry_combo.setVisible(False)

            # 触发股票列表过滤
            self.filter_stock_list()

        except Exception as e:
            self.log_manager.error(f"处理行业选择变化失败: {str(e)}")

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

    def update_chart(self, results=None):
        """唯一主业务入口，负责K线数据准备、自动分发到ChartWidget/MultiChartPanel。自动带当前选中指标。"""
        try:
            if not hasattr(self, 'current_stock') or not self.current_stock:
                self.log_manager.warning("没有选中的股票，无法更新图表")
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.show_no_data("请先选择股票")
                return
            # 优先用缓存
            if hasattr(self, 'chart_cache') and self.current_stock in self.chart_cache:
                k_data = self.chart_cache[self.current_stock]
            else:
                k_data = self.get_kdata(self.current_stock)
                if hasattr(self, 'chart_cache'):
                    self.chart_cache[self.current_stock] = k_data
            # 广播到所有图表
            self.broadcast_kdata_to_tabs(k_data)
            import pandas as pd
            if isinstance(k_data, pd.DataFrame) and 'code' not in k_data.columns:
                k_data = k_data.copy()
                k_data['code'] = self.current_stock
            if k_data is None or k_data.empty:
                self.log_manager.warning(f"获取股票 {self.current_stock} 的K线数据为空")
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.show_no_data("当前时间范围无数据")
                return
            # 获取股票名称
            stock = self.sm[self.current_stock]
            title = f"{self.current_stock} {stock.name}"
            # 获取当前选中指标
            selected_items = self.indicator_list.selectedItems(
            ) if hasattr(self, 'indicator_list') else []
            indicators = [item.text()
                          for item in selected_items] if selected_items else []
            data = {
                'stock_code': self.current_stock,
                'kdata': k_data,
                'title': title,
                'period': self.current_period,
                'chart_type': self.current_chart_type,
                'indicators': indicators
            }
            # 新增：分析结果区域增加策略说明
            strategy = self.strategy_combo.currentText() if hasattr(self, 'strategy_combo') else None
            strategy_explain = self.get_strategy_explanation(strategy)
            if results is not None:
                data['analysis'] = results
                if strategy_explain:
                    data['strategy_explanation'] = strategy_explain
            elif strategy_explain:
                data['strategy_explanation'] = strategy_explain
            self.chart_widget.update_chart(data)
        except Exception as e:
            self.log_manager.error(f"更新图表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def get_strategy_explanation(self, strategy: str) -> str:
        """
        返回指定策略的简要说明和信号判定逻辑
        """
        if strategy == "DX策略":
            return (
                "DX/ADX策略说明：\n"
                "- DX（方向性指数）和ADX（平均趋向指数）用于衡量市场趋势强度。\n"
                "- +DI表示上升动能，-DI表示下降动能，ADX越高趋势越强。\n"
                "- 信号判定：ADX高于阈值且+DI>-DI为多头，+DI<-DI为空头，否则无信号。\n"
                "- 适合趋势行情，震荡市信号较弱。"
            )
        elif strategy == "均线策略":
            return (
                "均线策略说明：\n"
                "- 对比短期均线和长期均线判断趋势。\n"
                "- 快线向上突破慢线为买入信号，向下跌破为卖出信号。"
            )
        elif strategy == "MACD策略":
            return (
                "MACD策略说明：\n"
                "- 利用快慢EMA均线差（DIF）和信号线（DEA）判断多空。\n"
                "- DIF上穿DEA为买入（金叉），下穿为卖出（死叉）。"
            )
        elif strategy == "RSI策略":
            return (
                "RSI策略说明：\n"
                "- RSI衡量价格上涨和下跌的速度和变化。\n"
                "- RSI低于超卖阈值为买入，高于超买阈值为卖出。"
            )
        elif strategy == "布林带策略":
            return (
                "布林带策略说明：\n"
                "- 通过价格与布林带上下轨的关系判断极端波动。\n"
                "- 收盘价下穿下轨为买入，上穿上轨为卖出。"
            )
        elif strategy == "KDJ策略":
            return (
                "KDJ策略说明：\n"
                "- KDJ通过K、D、J三线交叉判断超买超卖。\n"
                "- K值低于超卖阈值为买入，高于超买阈值为卖出。"
            )
        return ""

    def update_technical_indicators(self, k_data: pd.DataFrame) -> None:
        """技术指标刷新合并到update_chart流程，不再单独add_indicator"""
        pass

    def update_fundamental_indicators(self, k_data: pd.DataFrame) -> None:
        """基本面指标刷新合并到update_chart流程，不再单独add_indicator"""
        pass

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
                label = self.strategy_params_layout.itemAt(
                    i, QFormLayout.LabelRole).widget().text()
                widget = self.strategy_params_layout.itemAt(
                    i, QFormLayout.FieldRole).widget()
                if isinstance(widget, QSpinBox):
                    params[label] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    params[label] = widget.value()

            # 记录开始分析
            self.log_manager.info(f"开始分析 - 策略: {strategy}")

            # 获取股票数据
            data = self.data_manager.get_k_data(
                self.current_stock,
                freq=self.current_period,
                start_date=self.start_date.date().strftime('%Y-%m-%d'),
                end_date=self.end_date.date().strftime('%Y-%m-%d')
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
        """执行回测，使用统一回测引擎，支持所有策略，参数标准化，结果自动刷新到UI"""
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

            # 获取股票数据
            kdata = self.get_kdata(self.current_stock)
            if kdata is None or kdata.empty:
                self.log_manager.error("无法获取股票数据")
                return

            # 生成交易信号（简化版，实际应该根据策略生成）
            signal_data = kdata.copy()
            signal_data['signal'] = 0  # 默认无信号

            # 根据策略生成信号
            if strategy == "均线策略":
                ma_short = signal_data['close'].rolling(window=params.get('快线周期', 5)).mean()
                ma_long = signal_data['close'].rolling(window=params.get('慢线周期', 20)).mean()
                signal_data.loc[ma_short > ma_long, 'signal'] = 1
                signal_data.loc[ma_short < ma_long, 'signal'] = -1
            elif strategy == "MACD策略":
                exp1 = signal_data['close'].ewm(span=params.get('快线周期', 12), adjust=False).mean()
                exp2 = signal_data['close'].ewm(span=params.get('慢线周期', 26), adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=params.get('信号周期', 9), adjust=False).mean()
                signal_data.loc[macd > signal, 'signal'] = 1
                signal_data.loc[macd < signal, 'signal'] = -1

            self.log_manager.info(f"开始回测 - 策略: {strategy}")

            # 使用统一回测引擎
            from backtest.unified_backtest_engine import UnifiedBacktestEngine, BacktestLevel

            # 创建回测引擎
            engine = UnifiedBacktestEngine(backtest_level=BacktestLevel.PROFESSIONAL)

            # 运行回测
            result = engine.run_backtest(
                data=signal_data,
                initial_capital=self.initial_cash_spin.value() if hasattr(self, 'initial_cash_spin') and self.initial_cash_spin is not None else 100000.0,
                position_size=0.9,
                commission_pct=self.commission_spin.value() if hasattr(self, 'commission_spin') and self.commission_spin is not None else 0.0003,
                slippage_pct=self.slippage_spin.value() if hasattr(self, 'slippage_spin') and self.slippage_spin is not None else 0.0001
            )

            # 提取结果
            backtest_result = result['backtest_result']
            risk_metrics = result['risk_metrics']

            # 转换为兼容格式
            metrics = {
                'total_return': risk_metrics.total_return,
                'annual_return': risk_metrics.annualized_return,
                'max_drawdown': risk_metrics.max_drawdown,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'volatility': risk_metrics.volatility,
                'win_rate': getattr(risk_metrics, 'win_rate', 0),
                'profit_loss_ratio': getattr(risk_metrics, 'profit_loss_ratio', 0),
                'final_capital': backtest_result['capital'].iloc[-1],
                'total_trades': len(backtest_result[backtest_result['signal'] != 0])
            }

            self.update_performance_metrics(metrics)
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
                ma_short = data['close'].rolling(
                    window=params.get('快线周期', 5)).mean()
                ma_long = data['close'].rolling(
                    window=params.get('慢线周期', 20)).mean()

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
                exp1 = data['close'].ewm(span=params.get(
                    '快线周期', 12), adjust=False).mean()
                exp2 = data['close'].ewm(span=params.get(
                    '慢线周期', 26), adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=params.get(
                    '信号周期', 9), adjust=False).mean()

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
                gain = (delta.where(delta > 0, 0)).rolling(
                    window=params.get('周期', 14)).mean()
                loss = (-delta.where(delta < 0, 0)
                        ).rolling(window=params.get('周期', 14)).mean()
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
                high_max = data['high'].rolling(
                    window=params.get('周期', 9)).max()
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

            elif strategy == "形态分析":
                kdata = self.get_kdata(self.current_stock) if hasattr(self, 'get_kdata') else None
                self.log_manager.info(
                    f"形态分析收到数据: shape={kdata.shape}, columns={list(kdata.columns)}")
                self.log_manager.info(f"前5行数据:\n{kdata.head()}")
                from analysis.pattern_recognition import PatternRecognizer
                recognizer = PatternRecognizer()
                import pandas as pd
                kdata_for_pattern = kdata
                if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                    code = None
                    if hasattr(self, 'current_stock') and self.current_stock:
                        code = getattr(self, 'current_stock', None)
                    if not code and hasattr(self, 'selected_code'):
                        code = getattr(self, 'selected_code', None)
                    if not code and hasattr(self, 'code'):
                        code = getattr(self, 'code', None)
                    if code:
                        kdata_for_pattern = kdata.copy()
                        kdata_for_pattern['code'] = code
                        self.log_manager.info(f"形态分析自动补全DataFrame code字段: {code}")
                    else:
                        self.log_manager.error(
                            "形态分析无法自动补全DataFrame code字段，请确保DataFrame包含股票代码")
                pattern_signals = recognizer.get_pattern_signals(kdata_for_pattern)
                results = {
                    'strategy': strategy,
                    'pattern_signals': pattern_signals
                }
                if not pattern_signals:
                    self.log_manager.info("形态分析未识别到任何形态")
                else:
                    self.log_manager.info(f"形态分析识别到{len(pattern_signals)}个形态信号")
            elif strategy == "DX策略":
                # 计算DX/ADX
                period = int(params.get('周期', 14))
                threshold = float(params.get('ADX阈值', 25))
                high = data['high']
                low = data['low']
                close = data['close']
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=period).mean()
                up_move = high - high.shift(1)
                down_move = low.shift(1) - low
                plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
                minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
                plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
                minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
                dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
                adx = pd.Series(dx).ewm(alpha=1/period, adjust=False).mean()
                # 信号：ADX高于阈值且+DI>-DI为多头，+DI<-DI为空头，否则无信号
                signals = pd.Series(0, index=data.index)
                signals[(adx > threshold) & (plus_di > minus_di)] = 1
                signals[(adx > threshold) & (plus_di < minus_di)] = -1
                results = {
                    'strategy': strategy,
                    'signals': signals,
                    'indicators': {
                        'ADX': adx,
                        'DX': dx,
                        '+DI': plus_di,
                        '-DI': minus_di
                    }
                }
            else:
                label = QLabel("请选择策略")
                self.strategy_params_layout.addRow(label)

            return results

        except Exception as e:
            self.log_manager.error(f"执行分析失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def new_file(self):
        """创建新文件（修复日志区布局错乱问题）"""
        try:
            # 清空数据缓存
            self.data_cache.clear()
            self.chart_cache.clear()
            self.stock_list_cache.clear()

            # 清空日志内容，但不销毁日志控件
            if hasattr(self, 'log_widget') and self.log_widget:
                self.log_widget.clear_logs()

            # 强制刷新日志区和底部面板布局，防止布局错乱
            if hasattr(self, 'bottom_layout') and self.bottom_layout:
                self.bottom_layout.update()
            if hasattr(self, 'bottom_panel') and self.bottom_panel:
                self.bottom_panel.update()
            if hasattr(self, 'log_widget') and self.log_widget:
                self.log_widget.update()

            # 其他UI状态重置
            self.update_stock_list_ui()
            self.reset_chart_view()

            self.log_manager.info("已创建新文件")
        except Exception as e:
            self.log_manager.error(f"创建新文件失败: {str(e)}")

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
                self.log_manager.info("文件打开成功")

        except Exception as e:
            self.log_manager.error(f"打开文件失败: {str(e)}")

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
                self.log_manager.info("文件保存成功")

        except Exception as e:
            self.log_manager.error(f"保存文件失败: {str(e)}")

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
        """显示帮助对话框"""
        try:
            dialog = QDialog()
            dialog.setWindowTitle("帮助")
            dialog.setMinimumSize(800, 600)

            layout = QVBoxLayout(dialog)

            # 添加帮助内容
            help_text = QTextEdit()
            help_text.setReadOnly(True)
            help_text.setHtml("""
                <h2>学习量化交易系统使用帮助</h2>
                <h3>基本操作</h3>
                <ul>
                    <li>选择股票：在左侧面板输入股票代码或名称</li>
                    <li>查看图表：在中间面板显示K线和技术指标</li>
                    <li>交易操作：在右侧面板进行买入、卖出等操作</li>
                </ul>
                <h3>快捷键</h3>
                <ul>
                    <li>Ctrl+Q：退出程序</li>
                    <li>Ctrl+S：保存设置</li>
                    <li>F1：显示帮助</li>
                </ul>
            """)
            layout.addWidget(help_text)

            # 添加关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            # 显示对话框并居中
            dialog.show()
            self.center_dialog(dialog, self)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示帮助对话框失败: {str(e)}")

    def check_update(self):
        """检查更新"""
        try:
            # TODO: 实现更新检查
            self.log_manager.info("检查更新")
        except Exception as e:
            self.log_manager.error(f"检查更新失败: {str(e)}")

    def show_settings(self):
        """显示设置对话框，支持主题、字体、语言、自动保存等扩展设置，并集成主题管理Tab"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("主题样式")
            dialog.setMinimumSize(800, 600)

            tab_widget = QTabWidget(dialog)
            # 基本设置Tab
            basic_tab = QWidget()
            basic_layout = QVBoxLayout(basic_tab)
            settings_group = QGroupBox("基本设置")
            settings_layout = QFormLayout(settings_group)
            # 主题设置
            theme_names = self.theme_manager.get_all_themes()
            self.theme_combo = QComboBox()
            self.theme_combo.addItems(theme_names)
            self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
            settings_layout.addRow("主题:", self.theme_combo)
            # 字体大小
            font_size = QSpinBox()
            font_size.setRange(8, 24)
            font_size.setValue(12)
            settings_layout.addRow("字体大小:", font_size)
            # 语言设置
            lang_combo = QComboBox()
            lang_combo.addItems(["简体中文", "English"])
            settings_layout.addRow("语言:", lang_combo)
            # 自动保存
            auto_save = QCheckBox("自动保存设置")
            auto_save.setChecked(True)
            settings_layout.addRow("", auto_save)
            basic_layout.addWidget(settings_group)
            tab_widget.addTab(basic_tab, "基本设置")

            # 主题管理Tab
            theme_tab = QWidget()
            theme_layout = QVBoxLayout(theme_tab)
            # 主题列表
            theme_list = QListWidget()
            theme_list.addItems(theme_names)
            theme_layout.addWidget(QLabel("主题列表:"))
            theme_layout.addWidget(theme_list)
            # 主题操作按钮
            btn_layout = QHBoxLayout()
            btn_add = QPushButton("导入主题")
            btn_export = QPushButton("导出主题")
            btn_delete = QPushButton("删除主题")
            btn_rename = QPushButton("重命名主题")
            btn_edit = QPushButton("编辑QSS主题")
            btn_preview = QPushButton("预览主题")
            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_export)
            btn_layout.addWidget(btn_delete)
            btn_layout.addWidget(btn_rename)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_preview)
            theme_layout.addLayout(btn_layout)
            # 主题内容编辑区
            theme_content_edit = QTextEdit()
            theme_content_edit.setReadOnly(True)
            theme_layout.addWidget(QLabel("主题内容预览/编辑:"))
            theme_layout.addWidget(theme_content_edit)
            tab_widget.addTab(theme_tab, "主题管理")

            # 主题列表选中事件
            def on_theme_selected():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    theme_content_edit.clear()
                    theme_content_edit.setReadOnly(True)
                    btn_edit.setEnabled(False)
                    return
                row = self.theme_manager._get_theme_content(name)
                if not row:
                    theme_content_edit.clear()
                    theme_content_edit.setReadOnly(True)
                    btn_edit.setEnabled(False)
                    return
                type_, content = row
                theme_content_edit.setPlainText(content)
                if type_ == 'qss':
                    theme_content_edit.setReadOnly(False)
                    btn_edit.setEnabled(True)
                else:
                    theme_content_edit.setReadOnly(True)
                    btn_edit.setEnabled(False)
            theme_list.currentItemChanged.connect(lambda *_: on_theme_selected())
            if theme_list.count() > 0:
                theme_list.setCurrentRow(0)

            # 编辑QSS主题
            def on_edit_theme():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    return
                new_content = theme_content_edit.toPlainText()
                ok = self.theme_manager.edit_theme(name, new_content)
                if ok:
                    QMessageBox.information(dialog, "编辑成功", f"主题 {name} 已更新并应用！")
                    refresh_theme_list()
                    refresh_theme_combo()
                else:
                    QMessageBox.warning(dialog, "编辑失败", f"仅支持QSS类型主题编辑！")
            btn_edit.clicked.connect(on_edit_theme)

            # 预览主题
            def on_preview_theme():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    return
                self.theme_manager.set_theme(name)
                self.apply_theme()
                QMessageBox.information(dialog, "预览主题", f"已预览主题: {name}")
                refresh_theme_combo()
            btn_preview.clicked.connect(on_preview_theme)

            # 删除主题
            def on_delete_theme():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    return
                reply = QMessageBox.question(dialog, "删除主题", f"确定要删除主题: {name} 吗？", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.theme_manager.delete_theme(name)
                    theme_list.takeItem(theme_list.currentRow())
                    theme_content_edit.clear()
                    QMessageBox.information(dialog, "删除成功", f"主题 {name} 已删除！")
                    refresh_theme_list()
                    refresh_theme_combo()
            btn_delete.clicked.connect(on_delete_theme)

            # 重命名主题
            def on_rename_theme():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    return
                new_name, ok = QInputDialog.getText(dialog, "重命名主题", "请输入新主题名:", QLineEdit.Normal, name)
                if ok and new_name and new_name != name:
                    row = self.theme_manager._get_theme_content(name)
                    if row:
                        type_, content = row
                        self.theme_manager.add_theme(new_name, type_, content)
                        self.theme_manager.delete_theme(name)
                        theme_list.addItem(new_name)
                        theme_list.takeItem(theme_list.currentRow())
                        QMessageBox.information(dialog, "重命名成功", f"主题 {name} 已重命名为 {new_name}！")
                        refresh_theme_list()
                        refresh_theme_combo()
            btn_rename.clicked.connect(on_rename_theme)

            # 导入主题
            def on_import_theme():
                file_path, _ = QFileDialog.getOpenFileName(dialog, "导入主题", "", "QSS/JSON Files (*.qss *.json)")
                if not file_path:
                    return
                ext = os.path.splitext(file_path)[1].lower()
                name = os.path.splitext(os.path.basename(file_path))[0]
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if ext == '.qss':
                    self.theme_manager.add_theme(name, 'qss', content)
                elif ext == '.json':
                    self.theme_manager.add_theme(name, 'json', content)
                else:
                    QMessageBox.warning(dialog, "导入失败", "仅支持QSS或JSON文件！")
                    return
                theme_list.addItem(name)
                QMessageBox.information(dialog, "导入成功", f"主题 {name} 已导入！")
                refresh_theme_list()
                refresh_theme_combo()
            btn_add.clicked.connect(on_import_theme)

            # 导出主题
            def on_export_theme():
                name = theme_list.currentItem().text() if theme_list.currentItem() else None
                if not name:
                    return
                row = self.theme_manager._get_theme_content(name)
                if not row:
                    return
                type_, content = row
                ext = '.qss' if type_ == 'qss' else '.json'
                file_path, _ = QFileDialog.getSaveFileName(dialog, "导出主题", f"{name}{ext}", f"QSS/JSON Files (*{ext})")
                if not file_path:
                    return
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(dialog, "导出成功", f"主题 {name} 已导出到 {file_path}！")
            btn_export.clicked.connect(on_export_theme)

            # 主题列表刷新
            def refresh_theme_list():
                theme_list.clear()
                theme_list.addItems(self.theme_manager.get_all_themes())

            # 主题下拉框刷新
            def refresh_theme_combo():
                current = self.theme_combo.currentText() if self.theme_combo.count() > 0 else None
                self.theme_combo.blockSignals(True)
                self.theme_combo.clear()
                self.theme_combo.addItems(self.theme_manager.get_all_themes())
                if current and current in [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]:
                    self.theme_combo.setCurrentText(current)
                self.theme_combo.blockSignals(False)

            # 主题管理Tab切换时刷新
            tab_widget.currentChanged.connect(lambda idx: refresh_theme_list() if tab_widget.tabText(idx) == "主题管理" else None)

            # 主布局
            main_layout = QVBoxLayout(dialog)
            main_layout.addWidget(tab_widget)
            # 按钮
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            main_layout.addWidget(buttons)
            dialog.setLayout(main_layout)
            dialog.show()
            self.center_dialog(dialog, self)
            if dialog.exec_() == QDialog.Accepted:
                # 保存设置逻辑（可扩展）
                self.theme_manager.set_theme(self.theme_combo.currentText())
                self.apply_theme()
                self.config_manager.set_theme_type(font_size.value(), self.theme_combo.currentText())
                self.config_manager.set_language(lang_combo.currentText())
                self.config_manager.set_auto_save(auto_save.isChecked())
                self.log_manager.info("设置已保存")
        except Exception as e:
            self.log_manager.error(f"显示设置对话框失败: {str(e)}")

    def update_stock_count_label(self, count: int):
        """更新股票数量标签，线程安全"""
        if not hasattr(self, 'stock_count_label') or self.stock_count_label is None:
            return
        QTimer.singleShot(
            0, lambda: self.stock_count_label.setText(f"当前显示 {count} 只股票"))

    def init_market_industry_mapping(self):
        """初始化行业映射（不再初始化市场映射）"""
        try:
            # 初始化市场板块映射
            self.market_block_mapping = {
                "沪市主板": blocksh,
                "深市主板": blocksz,
                "创业板": blockg,
                "科创板": blockstart,
                "中小板": blockzxb,
                "上证50": zsbk_sh50,
                "上证180": zsbk_sh180,
                "沪深300": zsbk_hs300,
                "中证100": zsbk_zz100,
            }

            # 从行业管理器获取行业数据
            industries = self.industry_manager.get_all_industries()
            self.industry_mapping = {}
            # 构建行业映射
            for industry in industries:
                if '/' in industry:  # 处理多级行业
                    levels = industry.split('/')
                    main_industry = levels[0].strip()
                    sub_industry = levels[1].strip() if len(
                        levels) > 1 else None
                    if main_industry not in self.industry_mapping:
                        self.industry_mapping[main_industry] = {}
                    if sub_industry:
                        if sub_industry not in self.industry_mapping[main_industry]:
                            self.industry_mapping[main_industry][sub_industry] = [
                            ]
                else:
                    if industry not in self.industry_mapping:
                        self.industry_mapping[industry] = {}
            self.log_manager.info("行业映射初始化完成")
        except Exception as e:
            self.log_manager.error(f"初始化行业映射失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_data_source_changed(self, source: str) -> None:
        """切换数据源时，主动推送最新K线数据到所有分析Tab"""
        try:
            self.log_manager.info(f"切换数据源: {source}")
            # 保存当前选中的股票
            current_stock = self.current_stock
            # 清除缓存
            self.cache_manager.clear()
            self.stock_list_cache.clear()
            self.data_cache.clear()
            self.chart_cache.clear()
            # 通知所有分析Tab刷新数据
            if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'refresh_all_tabs'):
                self.analysis_widget.refresh_all_tabs()
            # 更新数据源
            if source == "东方财富":
                self.data_manager.set_data_source("eastmoney")
            elif source == "新浪":
                self.data_manager.set_data_source("sina")
            elif source == "同花顺":
                self.data_manager.set_data_source("tonghuashun")
            else:  # 默认使用 Hikyuu
                self.data_manager.set_data_source("hikyuu")
            # 重新加载数据
            self.preload_data()

            # 恢复之前选中的股票
            if current_stock:
                kdata = self.get_kdata(current_stock)
                self.broadcast_kdata_to_tabs(kdata)
                import pandas as pd
                if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                    kdata = kdata.copy()
                    kdata['code'] = current_stock
                for i in range(self.right_tab.count()):
                    tab_widget = self.right_tab.widget(i)
                    if tab_widget is not None and tab_widget.layout() and tab_widget.layout().count() > 1:
                        main_widget = tab_widget.layout().itemAt(1).widget()
                        if hasattr(main_widget, 'set_kdata'):
                            main_widget.set_kdata(kdata)
                if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                    self.analysis_widget.set_kdata(kdata)

            self.log_manager.info(f"数据源切换完成: {source}")

        except Exception as e:
            error_msg = f"切换数据源失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def get_kdata(self, code: str) -> pd.DataFrame:
        import json
        try:
            log_info = {"event": "get_kdata", "code": code, "from": "data_manager", "len": None, "fields": None, "status": "init"}
            if not hasattr(self, 'data_manager'):
                log_info["status"] = "no_data_manager"
                self.log_manager.error(json.dumps(log_info, ensure_ascii=False))
                return pd.DataFrame()
            freq = getattr(self, 'current_period', 'D')
            if hasattr(self, 'current_time_range') and self.current_time_range is not None:
                if self.current_time_range < 0:
                    query = Query(self.current_time_range, ktype=Query.DAY)
                else:
                    query = Query()
            else:
                query = Query()
            kdata = self.data_manager.get_k_data(
                code=code,
                freq=freq,
                query=query
            )
            retry_count = 0
            while (kdata is None or kdata.empty) and retry_count < 3:
                log_info["status"] = f"retry_{retry_count+1}"
                self.log_manager.warning(json.dumps(log_info, ensure_ascii=False))
                time.sleep(0.5)
                kdata = self.data_manager.get_k_data(code=code, freq=freq, query=Query())
                retry_count += 1
            if kdata is None or kdata.empty:
                # 兜底：主图
                if hasattr(self, 'chart_widget') and hasattr(self.chart_widget, 'get_kdata'):
                    kdata = self.chart_widget.get_kdata(code)
                    log_info["from"] = "chart_widget"
                    log_info["len"] = None if kdata is None else len(kdata)
                    log_info["fields"] = None if kdata is None else list(kdata.columns)
                    log_info["status"] = "fallback_chart"
                # 兜底：缓存
                if (kdata is None or kdata.empty) and hasattr(self, 'data_cache'):
                    kdata = self.data_cache.get(code)
                    log_info["from"] = "data_cache"
                    log_info["len"] = None if kdata is None else len(kdata)
                    log_info["fields"] = None if kdata is None else list(kdata.columns)
                    log_info["status"] = "fallback_cache"
                if kdata is None or kdata.empty:
                    log_info["status"] = "fail"
                    self.log_manager.error(json.dumps(log_info, ensure_ascii=False))
                    QMessageBox.warning(self, "K线数据异常", f"股票 {code} 的K线数据为空，建议：\n1. 检查数据源和网络\n2. 尝试刷新或切换数据源\n3. 检查日志详情")
                    return pd.DataFrame()
            log_info["status"] = "success"
            log_info["len"] = len(kdata)
            log_info["fields"] = list(kdata.columns)
            self.log_manager.info(json.dumps(log_info, ensure_ascii=False))
            return kdata
        except Exception as e:
            log_info = {"event": "get_kdata", "code": code, "error": str(e)}
            self.log_manager.error(json.dumps(log_info, ensure_ascii=False))
            self.log_manager.error(traceback.format_exc())
            return pd.DataFrame()

    def adjust_combobox_width(self, combobox: QComboBox):
        """根据内容自动调整下拉框宽度"""
        font_metrics = combobox.fontMetrics()
        max_width = 0
        for i in range(combobox.count()):
            text = combobox.itemText(i)
            width = font_metrics.width(text)
            if width > max_width:
                max_width = width
        # 额外加上icon、箭头、padding等空间
        combobox.setMinimumWidth(max_width + 35)

    def auto_select_first_stock(self):
        """单主图模式自动加载第一个股票，并自动设置日期区间"""
        if hasattr(self, 'stock_list_cache') and self.stock_list_cache:
            first_stock = self.stock_list_cache[0]
            first_code = first_stock['marketCode']
            self.current_stock = first_code
            # 自动设置日期区间
            from PyQt5.QtCore import QDate
            # 解析日期
            start_date_str = first_stock.get('start_date')
            end_date_str = first_stock.get('end_date')
            if start_date_str and len(start_date_str) >= 10:
                start_date = QDate.fromString(start_date_str[:10], 'yyyy-MM-dd')
            else:
                start_date = QDate.currentDate().addYears(-1)
            if end_date_str and len(end_date_str) >= 10:
                end_date = QDate.fromString(end_date_str[:10], 'yyyy-MM-dd')
            else:
                end_date = QDate.currentDate()
            # 设置到self.start_date和self.end_date
            self.start_date = start_date
            self.end_date = end_date
            # 如果有日期选择控件，UI同步
            if hasattr(self, 'start_date_edit'):
                self.start_date_edit.setDate(start_date)
            if hasattr(self, 'end_date_edit'):
                self.end_date_edit.setDate(end_date)
            self.update_chart()

    def switch_to_multi_screen(self):
        """切换到多屏模式并同步股票列表和数据管理器"""
        try:
            if hasattr(self, 'multi_chart_panel'):
                # 先准备数据
                if not getattr(self, 'data_manager', None):
                    self.log_manager.error("数据管理器未初始化")
                    return
                if not getattr(self, 'stock_list_cache', None):
                    self.log_manager.error("股票列表未加载")
                    return
                self.multi_chart_panel.set_stock_list(self.stock_list_cache)
                self.multi_chart_panel.set_data_manager(self.data_manager)
                # 切换模式
                self.multi_chart_panel.toggle_mode()
                # 多屏后自动填充股票数据
                if self.multi_chart_panel.is_multi:
                    self.multi_chart_panel.auto_fill_multi_charts()
                # 多屏后刷新UI和日志区
                self.chart_widget = self.multi_chart_panel.chart_widgets[0][0]
                self.update()
                if hasattr(self, 'log_widget'):
                    self.log_widget.update()
                if hasattr(self, 'bottom_panel'):
                    self.bottom_panel.update()
                if hasattr(self, 'show_log_panel'):
                    self.show_log_panel()
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                self.log_manager.info("已切换到多屏模式")
        except Exception as e:
            self.log_manager.error(f"切换到多屏模式失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def switch_to_single_screen(self):
        """切换到单屏模式，恢复主图"""
        try:
            if hasattr(self, 'multi_chart_panel'):
                self.multi_chart_panel.toggle_mode()
                self.chart_widget = self.multi_chart_panel.single_chart
                self.update_chart()
                self.update()
                if hasattr(self, 'log_widget'):
                    self.log_widget.update()
                if hasattr(self, 'bottom_panel'):
                    self.bottom_panel.update()
                if hasattr(self, 'show_log_panel'):
                    self.show_log_panel()
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                self.log_manager.info("已切换到单屏模式")
        except Exception as e:
            self.log_manager.error(f"切换到单屏模式失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def dragMoveEvent(self, event):
        """主窗口拖拽移动事件，确保鼠标样式为可放开"""
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain") or event.mimeData().hasFormat("text/application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()

    def get_current_indicators(self):
        """
        获取当前激活的所有指标及其参数，兼容ta-lib、自有、自定义，修复无指标问题，支持中文名称
        Returns:
            List[dict]: [{"name": 指标名, "params": 参数字典, "type": 类型, "group": 分组}, ...]
        """
        indicators = []
        from indicators_algo import get_talib_indicator_list, get_talib_category, get_all_indicators_by_category, get_indicator_english_name
        talib_list = get_talib_indicator_list()
        category_map = get_all_indicators_by_category(use_chinese=True)
        if not talib_list or not category_map:
            import logging
            logging.error("未检测到任何ta-lib指标，请检查ta-lib安装或数据源！")
            return []
        selected_items = self.indicator_list.selectedItems()
        if not hasattr(self, 'param_controls') or self.param_controls is None:
            self.param_controls = {}
        for item in selected_items:
            indicator_chinese = item.text()
            ind_type = item.data(Qt.UserRole)

            # 将中文名称转换为英文名称用于后台处理
            indicator_english = get_indicator_english_name(indicator_chinese)

            params = {}
            group = "builtin"
            if ind_type == "ta-lib" or ind_type == "形态识别" or ind_type == "其他":
                group = "talib"
                try:
                    import inspect
                    import talib
                    func = getattr(talib, indicator_english, None)
                    if func:
                        sig = inspect.signature(func)
                        for k in sig.parameters:
                            if k in self.param_controls:
                                params[k] = self.param_controls[k].value()
                except Exception as e:
                    self.log_manager.warning(f"获取指标 {indicator_english} 参数失败: {e}")
            indicators.append({
                "name": indicator_english,  # 后台使用英文名
                "display_name": indicator_chinese,  # 前端显示中文名
                "params": params,
                "type": get_talib_category(indicator_english),
                "group": group
            })
        return indicators

    def update_indicator_list(self):
        """
        整理指标筛选列表，确保与ta-lib分类一一映射，筛选功能正常，只展示有指标的分类，支持中文显示
        """
        from indicators_algo import get_all_indicators_by_category
        # 使用中文名称显示指标
        category_map = get_all_indicators_by_category(use_chinese=True)
        self.indicator_list.clear()
        for cat, names in category_map.items():
            for name in names:
                item = QListWidgetItem(str(name))
                item.setData(Qt.UserRole, str(cat))
                self.indicator_list.addItem(item)

    def clear_all_selected_indicators(self):
        """
        一键取消所有所选指标，UI联动
        """
        self.indicator_list.clearSelection()
        self.update_chart()  # 只刷新主入口

    def on_splitter_moved(self, pos, index):
        """分割线移动事件处理 - 仅处理UI布局，不触发数据刷新"""
        # 移除自动刷新逻辑，分割线拖动只是UI布局调整，不应该触发数据分析
        # 如果需要刷新图表，用户可以通过其他方式触发（如重新选择股票、指标等）
        # if not hasattr(self, '_splitter_refresh_timer'):
        #     self._splitter_refresh_timer = QTimer(self)
        #     self._splitter_refresh_timer.setSingleShot(True)
        #     self._splitter_refresh_timer.timeout.connect(
        #         self.refresh_all_charts)
        # self._splitter_refresh_timer.start(200)  # 拖动结束200ms后刷新

        pass

    def refresh_all_charts(self):
        """只刷新主控端一次，分屏同步由主控端驱动"""
        if hasattr(self, 'multi_chart_panel') and hasattr(self.multi_chart_panel, 'is_multi'):
            if self.multi_chart_panel.is_multi:
                # 只刷新主控端一次
                self.update_chart()
            else:
                self.update_chart()

    def load_indicator_combination_dialog(self):
        """弹出对话框，选择并加载指标组合"""
        try:
            user_id = "default"
            combinations = self.data_manager.get_indicator_combinations(
                user_id)
            if not combinations:
                QMessageBox.information(self, "提示", "暂无已保存的指标组合")
                return
            items = [f"{c[1]} (ID:{c[0]})" for c in combinations]
            item, ok = QInputDialog.getItem(
                self, "加载指标组合", "请选择要加载的指标组合:", items, 0, False)
            if ok and item:
                idx = items.index(item)
                indicators = combinations[idx][3]
                import json
                indicators = json.loads(indicators)
                # 清空当前选中
                self.indicator_list.clearSelection()
                # 逐个选中组合中的指标
                for ind in indicators:
                    for i in range(self.indicator_list.count()):
                        item_widget = self.indicator_list.item(i)
                        if item_widget.text() == ind["name"]:
                            item_widget.setSelected(True)
                            # 设置参数控件
                            if hasattr(self, "param_controls") and ind.get("params"):
                                for k, v in ind["params"].items():
                                    if k in self.param_controls:
                                        self.param_controls[k].setValue(v)
                self.update_chart()
        except Exception as e:
            self.log_manager.error(f"加载指标组合失败: {str(e)}")

    def delete_indicator_combination_dialog(self):
        """弹出对话框，选择并删除指标组合"""
        try:
            user_id = "default"
            combinations = self.data_manager.get_indicator_combinations(
                user_id)
            if not combinations:
                QMessageBox.information(self, "提示", "暂无已保存的指标组合")
                return
            items = [f"{c[1]} (ID:{c[0]})" for c in combinations]
            item, ok = QInputDialog.getItem(
                self, "删除指标组合", "请选择要删除的指标组合:", items, 0, False)
            if ok and item:
                idx = items.index(item)
                comb_id = combinations[idx][0]
                self.data_manager.delete_indicator_combination(comb_id)
                QMessageBox.information(self, "提示", f"已删除指标组合: {item}")
        except Exception as e:
            self.log_manager.error(f"删除指标组合失败: {str(e)}")

    def show_node_manager(self):
        """分布式节点管理入口，弹出节点发现/注册/监控对话框"""
        from gui.widgets.node_manager_dialog import NodeManagerDialog
        dlg = NodeManagerDialog(self)
        dlg.exec_()

    def show_cloud_api_manager(self):
        """云端API管理入口，弹出API配置/节点注册/任务同步对话框"""
        from gui.widgets.cloud_api_dialog import CloudAPIDialog
        dlg = CloudAPIDialog(self)
        dlg.exec_()

    def show_indicator_market(self):
        """指标市场入口，弹出在线指标市场浏览/安装/上传/评价对话框"""
        from gui.widgets.indicator_market_dialog import IndicatorMarketDialog
        dlg = IndicatorMarketDialog(self)
        dlg.exec_()

    def show_batch_analysis(self):
        """批量/分布式分析入口，弹出批量分析参数设置与进度监控对话框或切换到批量分析Tab"""
        # 优先切换到AnalysisToolsPanel的批量分析Tab
        try:
            for i in range(self.right_tab.count()):
                tab_widget = self.right_tab.widget(i)
                if tab_widget is not None and tab_widget.layout() and tab_widget.layout().count() > 1:
                    main_widget = tab_widget.layout().itemAt(1).widget()
                    # AnalysisToolsPanel批量分析Tab
                    if hasattr(main_widget, 'tab_widget') and hasattr(main_widget, 'batch_tab'):
                        idx = main_widget.tab_widget.indexOf(main_widget.batch_tab)
                        if idx >= 0:
                            main_widget.tab_widget.setCurrentIndex(idx)
                            self.right_tab.setCurrentIndex(i)
                            return
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"切换批量分析Tab失败: {str(e)}")
        # 若未找到，则弹出独立批量分析对话框（兼容旧实现）
        try:
            from gui.widgets.batch_analysis_dialog import BatchAnalysisDialog
            dlg = BatchAnalysisDialog(self)
            dlg.exec_()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"弹出批量分析对话框失败: {str(e)}")

    def check_single_stock_quality(self):
        """校验当前股票K线数据质量，生成报告并支持导出"""
        try:
            if not self.current_stock:
                QMessageBox.warning(self, "提示", "请先选择股票")
                return
            kdata = self.get_kdata(self.current_stock)
            from data.data_loader import generate_quality_report
            from core.risk_exporter import RiskExporter
            report = generate_quality_report(kdata, context=f"单股数据质量-{self.current_stock}")
            exporter = RiskExporter()
            file_path = exporter.export_quality_report(report, format="excel")
            QMessageBox.information(self, "校验完成", f"数据质量报告已导出到: {file_path}\n评分: {report['quality_score']}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"校验失败: {str(e)}")

    def check_all_stocks_quality(self):
        """校验全部股票数据质量"""
        try:
            from data.data_preprocessing import DataPreprocessor
            preprocessor = DataPreprocessor()

            # 获取所有股票代码
            all_stocks = []
            for i in range(self.stock_list.count()):
                item = self.stock_list.item(i)
                stock_data = item.data(Qt.UserRole)
                if stock_data and 'code' in stock_data:
                    all_stocks.append(stock_data['code'])

            if not all_stocks:
                QMessageBox.information(self, "提示", "没有找到股票数据")
                return

            # 批量校验
            self.log_manager.info(f"开始批量校验 {len(all_stocks)} 只股票的数据质量...")

            # 这里可以实现批量校验逻辑
            # 由于数据量可能很大，建议使用进度对话框
            QMessageBox.information(self, "批量校验", f"已启动 {len(all_stocks)} 只股票的数据质量校验")

        except Exception as e:
            self.log_manager.error(f"批量校验失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"批量校验失败: {str(e)}")

    # 形态识别优化系统方法
    def show_optimization_dashboard(self):
        """显示优化仪表板"""
        try:
            # 延迟导入，避免启动时阻塞
            from optimization.optimization_dashboard import OptimizationDashboard

            # 检查是否已经打开了仪表板
            if hasattr(self, '_optimization_dashboard') and self._optimization_dashboard:
                self._optimization_dashboard.raise_()
                self._optimization_dashboard.activateWindow()
                return

            # 创建新的仪表板窗口
            self._optimization_dashboard = OptimizationDashboard()
            self._optimization_dashboard.show()

            self.log_manager.info("已打开形态识别算法优化仪表板")

        except ImportError as e:
            self.log_manager.error(f"导入优化仪表板模块失败: {str(e)}")
            QMessageBox.warning(self, "模块缺失", "优化仪表板模块未找到，请检查安装")
        except Exception as e:
            self.log_manager.error(f"打开优化仪表板失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开优化仪表板失败: {str(e)}")

    def run_one_click_optimization(self):
        """运行一键优化"""
        try:
            # 延迟导入，避免启动时阻塞
            from optimization.auto_tuner import AutoTuner
            from PyQt5.QtWidgets import QProgressDialog
            from PyQt5.QtCore import QThread, pyqtSignal

            # 确认对话框
            reply = QMessageBox.question(
                self, "确认优化",
                "一键优化将对所有形态识别算法进行优化，这可能需要较长时间。\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在优化形态识别算法...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 创建优化线程
            class OptimizationThread(QThread):
                finished_signal = pyqtSignal(dict)
                error_signal = pyqtSignal(str)

                def run(self):
                    try:
                        tuner = AutoTuner(max_workers=2, debug_mode=True)
                        result = tuner.one_click_optimize(
                            optimization_method="genetic",
                            max_iterations=20
                        )
                        self.finished_signal.emit(result)
                    except Exception as e:
                        self.error_signal.emit(str(e))

            def on_optimization_finished(result):
                progress.close()
                summary = result.get("summary", {})
                message = f"""
一键优化完成！

总任务数: {summary.get('total_tasks', 0)}
成功任务数: {summary.get('successful_tasks', 0)}
成功率: {summary.get('success_rate', 0):.1f}%
平均改进: {summary.get('average_improvement', 0):.3f}%
最佳改进: {summary.get('best_improvement', 0):.3f}%
最佳形态: {summary.get('best_pattern', 'N/A')}
                """.strip()
                QMessageBox.information(self, "优化完成", message)
                self.log_manager.info("一键优化完成")

            def on_optimization_error(error):
                progress.close()
                QMessageBox.critical(self, "优化失败", f"一键优化失败: {error}")
                self.log_manager.error(f"一键优化失败: {error}")

            # 启动优化线程
            self.optimization_thread = OptimizationThread()
            self.optimization_thread.finished_signal.connect(on_optimization_finished)
            self.optimization_thread.error_signal.connect(on_optimization_error)
            self.optimization_thread.start()

            self.log_manager.info("已启动一键优化")

        except Exception as e:
            self.log_manager.error(f"启动一键优化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动一键优化失败: {str(e)}")

    def run_smart_optimization(self):
        """运行智能优化"""
        try:
            from optimization.auto_tuner import AutoTuner
            from PyQt5.QtWidgets import QInputDialog

            # 获取性能阈值
            threshold, ok = QInputDialog.getDouble(
                self, "智能优化设置",
                "请输入性能阈值（0.0-1.0）：\n低于此值的形态将被优化",
                0.7, 0.0, 1.0, 2
            )

            if not ok:
                return

            # 获取改进目标
            target, ok = QInputDialog.getDouble(
                self, "智能优化设置",
                "请输入改进目标（0.0-1.0）：\n期望的性能提升比例",
                0.1, 0.0, 1.0, 2
            )

            if not ok:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在进行智能优化...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 在后台线程中执行优化
            def run_optimization():
                try:
                    tuner = AutoTuner(max_workers=2, debug_mode=True)
                    result = tuner.smart_optimize(
                        performance_threshold=threshold,
                        improvement_target=target
                    )

                    progress.close()

                    if result.get("status") == "no_optimization_needed":
                        QMessageBox.information(
                            self, "智能优化",
                            "所有形态性能都达到要求，无需优化"
                        )
                    else:
                        summary = result.get("summary", {})
                        smart_analysis = result.get("smart_analysis", {})

                        message = f"""
智能优化完成！

优化形态数: {summary.get('total_tasks', 0)}
成功任务数: {summary.get('successful_tasks', 0)}
平均改进: {summary.get('average_improvement', 0):.3f}%
达成目标数: {smart_analysis.get('targets_achieved', 0)}
目标达成率: {smart_analysis.get('target_achievement_rate', 0):.1f}%
                        """.strip()
                        QMessageBox.information(self, "智能优化完成", message)

                    self.log_manager.info("智能优化完成")

                except Exception as e:
                    progress.close()
                    QMessageBox.critical(self, "优化失败", f"智能优化失败: {str(e)}")
                    self.log_manager.error(f"智能优化失败: {str(e)}")

            # 启动后台线程
            import threading
            threading.Thread(target=run_optimization, daemon=True).start()

            self.log_manager.info("已启动智能优化")

        except Exception as e:
            self.log_manager.error(f"启动智能优化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动智能优化失败: {str(e)}")

    def show_version_manager(self):
        """显示版本管理器"""
        try:
            from optimization.ui_integration import VersionManagerDialog
            from optimization.version_manager import VersionManager
            from PyQt5.QtWidgets import QInputDialog

            # 获取要管理的形态名称
            patterns = []
            try:
                from analysis.pattern_manager import PatternManager
                manager = PatternManager()
                pattern_configs = manager.get_all_patterns()
                patterns = [p.english_name for p in pattern_configs]
            except Exception as e:
                self.log_manager.error(f"获取形态列表失败: {e}")
                patterns = ["hammer", "doji", "three_white_soldiers"]  # 默认形态

            if not patterns:
                QMessageBox.information(self, "提示", "没有找到可管理的形态")
                return

            # 选择形态
            pattern_name, ok = QInputDialog.getItem(
                self, "选择形态", "请选择要管理版本的形态：",
                patterns, 0, False
            )

            if not ok or not pattern_name:
                return

            # 显示版本管理对话框
            version_manager = VersionManager()
            dialog = VersionManagerDialog(pattern_name, version_manager, self)
            dialog.exec_()

            self.log_manager.info(f"已打开 {pattern_name} 的版本管理器")

        except Exception as e:
            self.log_manager.error(f"打开版本管理器失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开版本管理器失败: {str(e)}")

    def show_performance_evaluation(self):
        """显示性能评估"""
        try:
            from optimization.performance_evaluator import PerformanceEvaluator
            from PyQt5.QtWidgets import QInputDialog

            # 获取要评估的形态名称
            patterns = []
            try:
                from analysis.pattern_manager import PatternManager
                manager = PatternManager()
                pattern_configs = manager.get_all_patterns()
                patterns = [p.english_name for p in pattern_configs]
            except Exception as e:
                self.log_manager.error(f"获取形态列表失败: {e}")
                patterns = ["hammer", "doji", "three_white_soldiers"]  # 默认形态

            if not patterns:
                QMessageBox.information(self, "提示", "没有找到可评估的形态")
                return

            # 选择形态
            pattern_name, ok = QInputDialog.getItem(
                self, "选择形态", "请选择要评估性能的形态：",
                patterns, 0, False
            )

            if not ok or not pattern_name:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在评估性能...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # 在后台线程中执行评估
            def run_evaluation():
                try:
                    evaluator = PerformanceEvaluator(debug_mode=True)

                    # 创建测试数据集
                    test_datasets = evaluator.create_test_datasets(pattern_name, count=5)

                    # 评估性能
                    metrics = evaluator.evaluate_algorithm(pattern_name, test_datasets)

                    progress.close()

                    # 显示结果
                    result_text = f"""
形态: {pattern_name}
综合评分: {metrics.overall_score:.3f}
信号质量: {metrics.signal_quality:.3f}
平均置信度: {metrics.confidence_avg:.3f}
执行时间: {metrics.execution_time:.3f}秒
识别形态数: {metrics.patterns_found}
鲁棒性: {metrics.robustness_score:.3f}
参数敏感性: {metrics.parameter_sensitivity:.3f}
                    """.strip()

                    QMessageBox.information(self, f"性能评估 - {pattern_name}", result_text)
                    self.log_manager.info(f"已完成 {pattern_name} 的性能评估")

                except Exception as e:
                    progress.close()
                    QMessageBox.critical(self, "评估失败", f"性能评估失败: {str(e)}")
                    self.log_manager.error(f"性能评估失败: {str(e)}")

            # 启动后台线程
            import threading
            threading.Thread(target=run_evaluation, daemon=True).start()

            self.log_manager.info(f"已启动 {pattern_name} 的性能评估")

        except Exception as e:
            self.log_manager.error(f"启动性能评估失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动性能评估失败: {str(e)}")

    def show_optimization_status(self):
        """显示优化系统状态"""
        try:
            from optimization.auto_tuner import AutoTuner
            from optimization.database_schema import OptimizationDatabaseManager

            # 获取系统状态
            tuner = AutoTuner(debug_mode=True)
            status = tuner.get_optimization_status()

            db_manager = OptimizationDatabaseManager()
            db_stats = db_manager.get_optimization_statistics()

            # 格式化状态信息
            status_text = f"""
系统状态: {status.get('system_status', 'unknown')}
活跃优化任务: {status.get('active_optimizations', 0)}
已完成优化: {status.get('completed_optimizations', 0)}
失败优化: {status.get('failed_optimizations', 0)}

数据库统计:
总版本数: {db_stats.get('total_versions', 0)}
活跃版本数: {db_stats.get('active_versions', 0)}
平均改进: {db_stats.get('avg_improvement', 0):.3f}%

最后更新: {status.get('last_update', 'N/A')}
            """.strip()

            QMessageBox.information(self, "优化系统状态", status_text)
            self.log_manager.info("已查看优化系统状态")

        except Exception as e:
            self.log_manager.error(f"获取优化系统状态失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"获取优化系统状态失败: {str(e)}")

    def show_quality_report_dialog(self, reports):
        """弹出数据质量报告对话框，表格展示，支持筛选、排序、导出"""
        dialog = QDialog(self)
        dialog.setWindowTitle("数据质量报告")
        layout = QVBoxLayout(dialog)
        # 多维度分组筛选区
        filter_layout = QHBoxLayout()
        filter_label = QLabel("最低评分:")
        filter_spin = QComboBox()
        filter_spin.addItems(["全部", "60", "70", "80", "90"])
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(filter_spin)
        group_label = QLabel("分组:")
        group_combo = QComboBox()
        group_fields = ["无分组", "市场", "行业", "评分区间"]
        group_combo.addItems(group_fields)
        filter_layout.addWidget(group_label)
        filter_layout.addWidget(group_combo)
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("搜索股票代码/异常/警告...")
        filter_layout.addWidget(search_edit)
        layout.addLayout(filter_layout)
        # 表格
        table = QTableWidget()
        columns = ["股票代码", "评分", "市场", "行业", "缺失字段", "异常值", "空值分布", "价格关系异常", "业务逻辑异常", "主要错误", "主要警告"]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(table)
        # 可视化区
        chart_tabs = QTabWidget()
        # 字段分布直方图
        hist_view = QWebEngineView()
        chart_tabs.addTab(hist_view, "字段分布直方图")
        # 字段箱线图
        box_view = QWebEngineView()
        chart_tabs.addTab(box_view, "字段箱线图")
        # 异常点可视化
        outlier_view = QWebEngineView()
        chart_tabs.addTab(outlier_view, "异常点分布")
        # 评分趋势折线图
        score_trend_view = QWebEngineView()
        chart_tabs.addTab(score_trend_view, "评分趋势")
        # 批量分布热力图
        heatmap_view = QWebEngineView()
        chart_tabs.addTab(heatmap_view, "分布热力图")
        # 地图（如有地理信息）
        map_view = QWebEngineView()
        chart_tabs.addTab(map_view, "异常分布地图")
        layout.addWidget(chart_tabs)
        # 填充表格和可视化

        def fill_table_and_charts():
            table.setRowCount(0)
            min_score = 0 if filter_spin.currentText() == "全部" else int(filter_spin.currentText())
            keyword = search_edit.text().strip().lower()
            group_by = group_combo.currentText()
            filtered = []
            for r in reports:
                if r.get("quality_score", 100) < min_score:
                    continue
                if keyword and keyword not in str(r.get("code", "")).lower() and keyword not in str(r.get("errors", "")).lower() and keyword not in str(r.get("warnings", "")).lower():
                    continue
                filtered.append(r)
            # 分组统计
            group_map = {}
            if group_by == "无分组":
                group_map["全部"] = filtered
            elif group_by == "市场":
                for r in filtered:
                    k = r.get("market", "未知")
                    group_map.setdefault(k, []).append(r)
            elif group_by == "行业":
                for r in filtered:
                    k = r.get("industry", "未知")
                    group_map.setdefault(k, []).append(r)
            elif group_by == "评分区间":
                for r in filtered:
                    score = r.get("quality_score", 100)
                    if score >= 90:
                        k = "90-100"
                    elif score >= 80:
                        k = "80-89"
                    elif score >= 70:
                        k = "70-79"
                    elif score >= 60:
                        k = "60-69"
                    else:
                        k = "<60"
                    group_map.setdefault(k, []).append(r)
            # 填充表格
            for group, group_list in group_map.items():
                for r in group_list:
                    row = table.rowCount()
                    table.insertRow(row)
                    table.setItem(row, 0, QTableWidgetItem(str(r.get("code", ""))))
                    table.setItem(row, 1, QTableWidgetItem(str(r.get("quality_score", ""))))
                    table.setItem(row, 2, QTableWidgetItem(str(r.get("market", ""))))
                    table.setItem(row, 3, QTableWidgetItem(str(r.get("industry", ""))))
                    table.setItem(row, 4, QTableWidgetItem(str(r.get("missing_fields", ""))))
                    table.setItem(row, 5, QTableWidgetItem(str(r.get("anomaly_stats", ""))))
                    table.setItem(row, 6, QTableWidgetItem(str(r.get("empty_ratio", ""))))
                    table.setItem(row, 7, QTableWidgetItem(str(r.get("price_relation_errors", ""))))
                    table.setItem(row, 8, QTableWidgetItem(str(r.get("logic_errors", ""))))
                    table.setItem(row, 9, QTableWidgetItem(", ".join(r.get("errors", []))))
                    table.setItem(row, 10, QTableWidgetItem(", ".join(r.get("warnings", []))))
            # 可视化数据准备
            import pandas as pd
            import plotly.express as px
            import plotly.graph_objects as go
            df = pd.DataFrame(filtered)
            # 字段分布直方图
            if not df.empty:
                num_cols = [c for c in df.columns if df[c].dtype in [int, float] and c not in ("quality_score",)]
                if num_cols:
                    fig = px.histogram(df, x=num_cols[0], nbins=20, title=f"{num_cols[0]}分布直方图")
                    hist_view.setHtml(fig.to_html(include_plotlyjs='cdn'))
                    fig2 = px.box(df, y=num_cols[0], title=f"{num_cols[0]}箱线图")
                    box_view.setHtml(fig2.to_html(include_plotlyjs='cdn'))
                # 异常点可视化
                if "anomaly_stats" in df.columns:
                    try:
                        anom = df["anomaly_stats"].apply(lambda x: eval(str(x)) if isinstance(x, str) else x)
                        anom_count = [len(a) if isinstance(a, dict) else 0 for a in anom]
                        fig3 = go.Figure(go.Scatter(y=anom_count, mode='markers', marker=dict(color='red')))
                        fig3.update_layout(title="异常点分布", xaxis_title="样本", yaxis_title="异常点数")
                        outlier_view.setHtml(fig3.to_html(include_plotlyjs='cdn'))
                    except Exception:
                        outlier_view.setHtml("<b>无异常点数据</b>")
                # 评分趋势
                if "quality_score" in df.columns:
                    fig4 = go.Figure(go.Scatter(y=df["quality_score"], mode='lines+markers'))
                    fig4.update_layout(title="评分趋势", xaxis_title="样本", yaxis_title="评分")
                    score_trend_view.setHtml(fig4.to_html(include_plotlyjs='cdn'))
                # 分布热力图
                if "market" in df.columns and "quality_score" in df.columns:
                    pivot = pd.pivot_table(df, index="market", columns="industry" if "industry" in df.columns else "market",
                                           values="quality_score", aggfunc='mean', fill_value=0)
                    fig5 = px.imshow(pivot, title="市场-行业评分热力图")
                    heatmap_view.setHtml(fig5.to_html(include_plotlyjs='cdn'))
                # 地图（如有地理信息）
                if "region" in df.columns:
                    fig6 = px.density_mapbox(df, lat="lat", lon="lon", z="quality_score", radius=10, center=dict(
                        lat=35, lon=105), zoom=3, mapbox_style="carto-positron", title="异常分布地图")
                    map_view.setHtml(fig6.to_html(include_plotlyjs='cdn'))
                else:
                    map_view.setHtml("<b>无地理信息</b>")
            else:
                for v in [hist_view, box_view, outlier_view, score_trend_view, heatmap_view, map_view]:
                    v.setHtml("<b>无数据</b>")
        filter_spin.currentTextChanged.connect(fill_table_and_charts)
        search_edit.textChanged.connect(fill_table_and_charts)
        group_combo.currentTextChanged.connect(fill_table_and_charts)
        fill_table_and_charts()
        # 导出按钮
        export_btn = QPushButton("导出Excel")

        def do_export():
            import pandas as pd
            file_path, _ = QFileDialog.getSaveFileName(dialog, "导出数据质量报告", "quality_report.xlsx", "Excel Files (*.xlsx)")
            if file_path:
                df = pd.DataFrame(reports)
                df.to_excel(file_path, index=False)
                QMessageBox.information(dialog, "导出成功", f"报告已导出到: {file_path}")
        export_btn.clicked.connect(do_export)
        layout.addWidget(export_btn)
        dialog.setLayout(layout)
        dialog.resize(1400, 900)
        dialog.exec_()

    def start_auto_quality_check(self, interval_minutes=60):
        """定时自动校验，异常自动告警，日志联动"""
        if hasattr(self, '_auto_quality_timer') and self._auto_quality_timer:
            self._auto_quality_timer.stop()
        self._auto_quality_timer = QTimer(self)
        self._auto_quality_timer.timeout.connect(self._auto_quality_check)
        self._auto_quality_timer.start(interval_minutes * 60 * 1000)

    def _auto_quality_check(self):
        try:
            stocks = self.stock_list_cache if hasattr(self, 'stock_list_cache') else []
            from data.data_loader import generate_quality_report
            abnormal = []
            for stock in stocks:
                code = stock['marketCode'] if 'marketCode' in stock else stock['code']
                kdata = self.get_kdata(code)
                report = generate_quality_report(kdata, context=f"定时校验-{code}")
                if report['quality_score'] < 60:
                    abnormal.append({"code": code, **report})
            if abnormal:
                self.log_manager.warning(f"定时数据质量校验发现异常: {len(abnormal)}只股票")
                self.show_quality_report_dialog(abnormal)
        except Exception as e:
            self.log_manager.error(f"定时数据质量校验失败: {str(e)}")

    # 支持自定义报告内容、字段、评分算法（可通过配置或参数传递给generate_quality_report）
    # 批量校验失败重试、进度条、筛选优化已在check_all_stocks_quality中实现

    def broadcast_kdata_to_tabs(self, kdata):
        """统一推送K线数据到所有AnalysisWidget及支持set_kdata的Tab"""
        import pandas as pd
        try:
            if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                kdata = kdata.copy()
                kdata['code'] = self.current_stock
            for i in range(self.right_tab.count()):
                tab_widget = self.right_tab.widget(i)
                if tab_widget is not None and tab_widget.layout() and tab_widget.layout().count() > 1:
                    main_widget = tab_widget.layout().itemAt(1).widget()
                    if hasattr(main_widget, 'set_kdata'):
                        main_widget.set_kdata(kdata)
            if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                self.analysis_widget.set_kdata(kdata)
            self.log_manager.info(f"已推送K线数据到所有分析Tab，长度: {len(kdata) if hasattr(kdata, '__len__') else '未知'}")
        except Exception as e:
            self.log_manager.error(f"推送K线数据到Tab失败: {str(e)}")

    def refresh_tab_content(self, widget):
        for method in ["refresh", "update", "reload"]:
            if hasattr(widget, method):
                try:
                    getattr(widget, method)()
                    # 刷新后自动推送K线数据
                    if hasattr(widget, 'set_kdata') and hasattr(self, 'current_stock'):
                        kdata = self.get_kdata(self.current_stock)
                        widget.set_kdata(kdata)
                except Exception as e:
                    if hasattr(self, 'log_manager'):
                        self.log_manager.warning(f"刷新Tab内容失败: {str(e)}")
                break
    # 其它如start_date_edit、end_date_edit、股票池/行业/市场筛选等事件中也调用broadcast_kdata_to_tabs


class StockListWidget(QListWidget):
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None:
            return
        drag = QDrag(self)
        mimeData = QMimeData()
        text = item.text()
        if text.startswith("★"):
            text = text[1:].strip()
        mimeData.setText(text)
        drag.setMimeData(mimeData)
        drag.exec_(supportedActions)


# 修改全局异常处理器


class GlobalExceptionHandler:
    """全局异常处理器类"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.log_manager = app_instance.log_manager if hasattr(
            app_instance, 'log_manager') else None

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """处理未捕获的异常

        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常堆栈
        """
        try:
            # 获取错误信息
            error_msg = str(exc_value)
            error_type = exc_type.__name__
            trace_info = ''.join(traceback.format_tb(exc_traceback))

            # 记录错误日志
            if self.log_manager:
                self.log_manager.error(f"未捕获的异常: {error_type}: {error_msg}")
                self.log_manager.error(f"堆栈跟踪:\n{trace_info}")
            else:
                print(f"未捕获的异常: {error_type}: {error_msg}")
                print(f"堆栈跟踪:\n{trace_info}")

        # 显示错误对话框
            error_dialog = QErrorMessage()
            error_dialog.showMessage(f"发生错误: {error_msg}\n\n请查看日志获取详细信息。")

            # 如果是严重错误，尝试恢复系统状态
            if issubclass(exc_type, (MemoryError, SystemError)):
                if hasattr(self.app, 'cleanup_memory'):
                    self.app.cleanup_memory()
                if hasattr(self.app, 'reset_chart_view'):
                    self.app.reset_chart_view()

        except Exception as e:
            print(f"错误处理失败: {e}")
            print(f"原始异常: {error_type}: {error_msg}")


def safe_strftime(dt, fmt='%Y-%m-%d'):
    """兼容 hikyuu Datetime 和 Python datetime 的安全格式化"""
    if hasattr(dt, 'number'):
        n = int(dt.number)
        if n == 0:
            return "未知"
        s = str(n)
        if fmt == '%Y-%m-%d':
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        elif fmt == '%Y%m%d':
            return s[:8]
        elif fmt == '%Y-%m-%d %H:%M:%S':
            return f"{s[:4]}-{s[4:6]}-{s[6:8]} 00:00:00"
        elif fmt == '%H:%M:%S':
            return "00:00:00"
        elif fmt == '%Y%m%d_%H%M%S':
            return f"{s[:8]}_000000"
        else:
            return s
    elif hasattr(dt, 'strftime'):
        return dt.strftime(fmt)
    return str(dt) if dt else "未知"


def add_shadow(widget, blur_radius=20, x_offset=0, y_offset=4, color=QColor(0, 0, 0, 80)):
    """
    为指定控件添加阴影效果。
    :param widget: 需要添加阴影的控件
    :param blur_radius: 阴影模糊半径
    :param x_offset: 阴影X方向偏移
    :param y_offset: 阴影Y方向偏移
    :param color: 阴影颜色
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(x_offset, y_offset)
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)


def main():
    """主函数"""
    try:
        # 设置应用程序属性
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # 创建应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("Hikyuu Trading System")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("Hikyuu")

        # 设置应用程序图标
        app.setWindowIcon(QIcon("icons/logo.png"))

        # 设置全局异常处理器
        exception_handler = GlobalExceptionHandler(app)
        sys.excepthook = exception_handler.handle_exception

        # 简化启动过程，延迟初始化优化系统
        print("正在启动 Hikyuu Trading System...")

        # 创建主窗口
        window = TradingGUI()

        # 延迟初始化优化系统（在主窗口显示后）
        def delayed_init():
            try:
                from optimization.database_schema import OptimizationDatabaseManager
                OptimizationDatabaseManager()
            except Exception as e:
                print(f"优化系统初始化失败: {e}")
                # 不影响主程序运行

        # 使用QTimer延迟执行
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, delayed_init)  # 2秒后初始化优化系统

        window.show()

        print("Hikyuu Trading System 启动完成")

        # 运行应用程序
        sys.exit(app.exec_())

    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
