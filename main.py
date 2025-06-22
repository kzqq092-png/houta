"""
交易系统主窗口模块
"""
import time
from core.plugin_manager import PluginManager
from utils.cache import Cache
from components.stock_screener import StockScreenerWidget
from gui.ui_components import StatusBar, GlobalExceptionHandler, add_shadow
from gui.widgets.multi_chart_panel import MultiChartPanel
from gui.widgets.log_widget import LogWidget
from core.industry_manager import IndustryManager
# 导入新的策略管理系统
from core.strategy import (
    initialize_strategy_system, get_strategy_registry, get_strategy_engine,
    get_strategy_factory, get_strategy_database_manager, list_available_strategies,
    execute_strategy, get_strategy_info
)
# 导入新的面板模块
from gui.panels import StockManagementPanel, ChartAnalysisPanel, AnalysisPanel
# 导入新的工具模块
from gui.tools import Calculator, UnitConverter
# 导入新的管理器模块
from gui.managers import StrategyManager, OptimizationManager, QualityManager
# 导入菜单处理器、UI工厂和辅助工具
from gui.handlers.menu_handler import MenuHandler
from gui.factories.ui_factory import UIFactory
from gui.utils.main_helper import MainWindowHelper
# 导入对话框模块
from gui.dialogs import AdvancedSearchDialog, IndicatorParamsDialog, DatabaseAdminDialog
# 导入自定义组件辅助类
from gui.components.custom_widgets import ComboBoxHelper
# 导入国际化模块
from utils.i18n import get_i18n_manager, _, set_language

from hikyuu import StockManager, Query
from hikyuu.interactive import *
from hikyuu.indicator import *
from hikyuu.data import *
from hikyuu import *
from gui.widgets.chart_widget import ChartWidget
from gui.menu_bar import MainMenuBar
from utils.config_manager import ConfigManager
from utils.exception_handler import ExceptionHandler
from core.data_manager import data_manager
from utils.theme import ThemeManager, get_theme_manager, Theme
from utils.config_types import LoggingConfig
from core.logger import LogManager, BaseLogManager, LogLevel
from core.adapters import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *
from datetime import datetime
from typing import Dict, Any, List, Optional
from optimization.database_schema import *
import numpy as np
import pandas as pd
import sys
import os
import traceback
import warnings
import functools  # 新增：用于修复lambda闭包问题
warnings.filterwarnings(
    "ignore", category=FutureWarning, message=".*swapaxes*")

# 在文件开头添加random模块导入


class TradingGUI(QMainWindow):
    """Trading system main window"""

    # Define signals
    theme_changed = pyqtSignal(Theme)
    data_updated = pyqtSignal(dict)
    analysis_completed = pyqtSignal(dict)
    performance_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    language_changed = pyqtSignal(str)  # 新增：语言变更信号

    def __init__(self):
        """Initialize the trading system GUI"""
        super().__init__()
        # 在构造函数最开始就初始化日志管理器
        from utils.manager_factory import get_log_manager
        self.log_manager = get_log_manager()
        self.log_manager.info("TradingGUI 开始初始化...")

        # 初始化语言切换防护标志
        self._language_changing = False

        # 集成统一性能管理器
        from core.unified_performance_manager import get_performance_manager, performance_monitor
        self.performance_manager = get_performance_manager()

        # 核心管理器初始化
        self.init_managers()

        # 界面初始化
        self.init_ui()

        # 数据预加载
        self.init_data()

        # 性能监控回调
        self.performance_manager.register_performance_callback(self._on_performance_update)

        self.log_manager.info("交易系统初始化完成")

    def init_managers(self):
        """Initialize core managers"""
        try:
            self.log_manager.info("开始初始化核心管理器...")
            # 创建主窗口辅助类
            self.main_helper = MainWindowHelper(self)

            # 创建菜单处理器
            self.menu_handler = MenuHandler(self)

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

            # 使用统一的管理器工厂
            from utils.manager_factory import get_config_manager, get_log_manager, get_industry_manager

            # 初始化配置管理器
            self.config_manager = get_config_manager()

            # 从配置中获取日志配置
            logging_config = self.config_manager.logging

            # 初始化日志管理器 - 确保在这里再次获取，以应用最新配置
            self.log_manager = get_log_manager(logging_config)
            self.log_manager.info("配置与日志管理器初始化完成")

            # 初始化国际化管理器
            self.i18n_manager = get_i18n_manager()
            # 从配置中获取语言设置
            ui_config = self.config_manager.get('ui', {})
            saved_language = ui_config.get('language', 'zh_CN')
            self.i18n_manager.set_language(saved_language)
            self.log_manager.info(f"国际化管理器初始化完成，当前语言: {saved_language}")

            # 初始化语言切换管理器 - 新增
            from utils.language_manager import get_language_switch_manager
            self.language_switch_manager = get_language_switch_manager(
                self.i18n_manager, self.config_manager, self.log_manager
            )
            # 连接语言切换信号
            self.language_switch_manager.language_switch_completed.connect(self._on_language_switch_completed)
            self.language_switch_manager.language_switch_failed.connect(self._on_language_switch_failed)
            self.log_manager.info("语言切换管理器初始化完成")

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
            self.industry_manager = get_industry_manager(self.log_manager)
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
            # 设置插件上下文
            self.plugin_manager.set_context(
                app_instance=self,
                config_manager=self.config_manager,
                log_manager=self.log_manager
            )
            self.plugin_manager.load_plugins()
            self.log_manager.info("插件管理器初始化并加载插件完成")

            # 初始化策略管理系统
            try:
                self.log_manager.info("初始化策略管理系统...")
                strategy_config = self.config_manager.get('strategy_system', {})
                self.strategy_managers = initialize_strategy_system(strategy_config)

                # 获取策略管理器实例
                self.strategy_registry = self.strategy_managers['registry']
                self.strategy_engine = self.strategy_managers['engine']
                self.strategy_factory = self.strategy_managers['factory']
                self.strategy_database = self.strategy_managers['database']

                # 加载可用策略列表
                self.available_strategies = list_available_strategies()
                self.log_manager.info(f"策略管理系统初始化完成，加载了 {len(self.available_strategies)} 个策略")

            except Exception as e:
                self.log_manager.error(f"策略管理系统初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
                # 使用默认策略列表作为备用
                self.available_strategies = ["均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"]

            # 初始化功能面板
            self.init_panels()

            self.log_manager.info("核心管理器初始化成功")

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
            self.log_manager.info("开始连接信号...")
            # 连接主题变更信号
            self.theme_changed.connect(self.apply_theme)

            # 连接数据更新信号
            self.data_updated.connect(self.handle_data_update)

            # 连接分析完成信号
            self.analysis_completed.connect(self.handle_analysis_complete)

            # 连接错误信号
            self.error_occurred.connect(self.handle_error)

            # 连接语言变更信号
            self.language_changed.connect(self.on_language_changed)

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
            self.log_manager.debug(f"收到数据请求: {request_data}")
            if self.data_manager:
                response_data = self.data_manager.get_data(request_data)
                self.data_updated.emit(response_data)
        except Exception as e:
            self.log_manager.error(f"处理数据请求失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def update_data(self, data: dict):
        """更新数据，仅做缓存和分发，UI渲染走主入口update_chart"""
        try:
            self.log_manager.debug(f"接收到数据更新: {list(data.keys())}")
            # 更新数据缓存
            if hasattr(self, 'data_cache'):
                self.data_cache.update(data)
            # 分发到分析工具面板
            if hasattr(self, 'analysis_tools'):
                self.analysis_tools.update_results(data)
            # 记录日志
            self.log_manager.info("数据更新完成，即将刷新图表")
            # 统一走主入口渲染
            self.update_chart()
        except Exception as e:
            self.log_manager.error(f"更新数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"更新数据失败: {str(e)}")

    def handle_analysis_error(self, error_msg: str):
        """处理分析错误"""
        try:
            self.log_manager.error(f"捕获到分析错误: {error_msg}")
            # 使用统一的错误消息框
            self.show_error_message("分析错误", error_msg)
        except Exception as e:
            self.log_manager.error(f"处理分析错误失败: {str(e)}")

    def handle_chart_error(self, error_msg: str):
        """处理图表错误"""
        try:
            self.log_manager.error(f"捕获到图表错误: {error_msg}")
            # 使用统一的警告消息框
            self.show_warning_message("图表错误", error_msg)
        except Exception as e:
            self.log_manager.error(f"处理图表错误失败: {str(e)}")

    def handle_log_error(self, error_msg: str):
        """处理日志错误"""
        try:
            self.log_manager.error(f"捕获到日志系统错误: {error_msg}")
            # 使用统一的警告消息框
            self.show_warning_message("日志错误", error_msg)
        except Exception as e:
            print(f"处理日志错误失败: {str(e)}")  # 避免循环错误

    def handle_log_clear(self):
        """处理日志清除"""
        try:
            self.log_manager.info("请求清除日志")
            if self.log_manager:
                self.log_manager.clear()
        except Exception as e:
            self.log_manager.error(f"清除日志失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def update_analysis(self):
        """更新分析结果"""
        try:
            self.log_manager.info("请求更新分析结果...")
            if hasattr(self, 'analysis_widget'):
                # 触发分析更新
                if hasattr(self.analysis_widget, 'update_analysis'):
                    self.analysis_widget.update_analysis()

            # 更新其他分析相关组件
            if hasattr(self, 'analysis_tools_panel'):
                if hasattr(self.analysis_tools_panel, 'refresh'):
                    self.analysis_tools_panel.refresh()

            self.log_manager.info("分析结果已更新")
        except Exception as e:
            self.log_manager.error(f"更新分析结果失败: {str(e)}")

    def handle_data_update(self, data: dict):
        """Handle data update signal"""
        try:
            self.log_manager.debug(f"处理数据更新信号: {list(data.keys())}")
            # 更新数据缓存
            self.data_cache.update(data)

            # 更新UI显示
            self.update_ui()

        except Exception as e:
            self.log_manager.error(f"处理数据更新失败: {str(e)}")

    def handle_analysis_complete(self, results: dict):
        """Handle analysis complete signal"""
        try:
            self.log_manager.debug(f"处理分析完成信号: {results}")
            # 更新分析结果
            self.update_metrics(results)

            # 更新图表
            self.update_chart()

        except Exception as e:
            self.log_manager.error(f"处理分析完成失败: {str(e)}")

    def update_ui(self):
        """Update UI components"""
        try:
            self.log_manager.info("请求刷新UI组件...")
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
            self.log_manager.info("开始初始化UI...")
            # 设置窗口标题和大小
            self.setWindowTitle("Trading System")
            self.setGeometry(400, 100, 1500, 700)
            # 确保主窗口和centralWidget都能接收拖拽事件
            self.setAcceptDrops(True)

            # 先创建菜单栏，确保布局计算正确
            self.create_menubar()

            # 创建central widget和主布局
            central_widget = QWidget()
            central_widget.setAcceptDrops(True)
            self.main_layout = QVBoxLayout(central_widget)
            # 增加上边距，确保不与菜单栏重叠
            self.main_layout.setContentsMargins(0, 5, 0, 0)  # 上边距增加到5px
            self.main_layout.setSpacing(2)  # 减少间距
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

            # 创建状态栏
            self.create_statusbar()

            self.log_manager.info("UI初始化完成")

            # 下拉框宽度自适应
            if hasattr(self, 'time_range_combo'):
                ComboBoxHelper.adjust_combobox_width(self.time_range_combo)
            if hasattr(self, 'period_combo'):
                ComboBoxHelper.adjust_combobox_width(self.period_combo)
            if hasattr(self, 'chart_type_combo'):
                ComboBoxHelper.adjust_combobox_width(self.chart_type_combo)

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
            self.menu_bar.new_action.triggered.connect(self.menu_handler.new_file)
            self.menu_bar.open_action.triggered.connect(self.menu_handler.open_file)
            self.menu_bar.save_action.triggered.connect(self.menu_handler.save_file)
            self.menu_bar.exit_action.triggered.connect(self.close)

            # 编辑菜单
            self.menu_bar.undo_action.triggered.connect(self.menu_handler.undo)
            self.menu_bar.redo_action.triggered.connect(self.menu_handler.redo)
            self.menu_bar.copy_action.triggered.connect(self.menu_handler.copy)
            self.menu_bar.paste_action.triggered.connect(self.menu_handler.paste)

            # 分析菜单
            self.menu_bar.analyze_action.triggered.connect(self.menu_handler.analyze)
            self.menu_bar.backtest_action.triggered.connect(self.menu_handler.backtest)
            self.menu_bar.optimize_action.triggered.connect(self.menu_handler.optimize)

            # 工具菜单
            self.menu_bar.calculator_action.triggered.connect(self.menu_handler.show_calculator)
            self.menu_bar.converter_action.triggered.connect(self.menu_handler.show_converter)

            # 插件管理器
            self.menu_bar.plugin_manager_action.triggered.connect(self.show_plugin_manager)

            # 语言设置菜单项 - 连接到动作组的信号
            if hasattr(self.menu_bar, 'language_group'):
                self.menu_bar.language_group.triggered.connect(self._on_language_action_triggered)

            # 设置当前语言为选中状态
            current_language = self.i18n_manager.get_current_language()
            if current_language in self.menu_bar.language_actions:
                self.menu_bar.language_actions[current_language].setChecked(True)

            self.menu_bar.settings_action.triggered.connect(self.menu_handler.show_settings)

            # 数据菜单（数据源切换）
            self.menu_bar.data_source_hikyuu.triggered.connect(
                lambda: self.menu_handler.on_data_source_changed("Hikyuu"))
            self.menu_bar.data_source_eastmoney.triggered.connect(
                lambda: self.menu_handler.on_data_source_changed("东方财富"))
            self.menu_bar.data_source_sina.triggered.connect(
                lambda: self.menu_handler.on_data_source_changed("新浪"))
            self.menu_bar.data_source_tonghuashun.triggered.connect(
                lambda: self.menu_handler.on_data_source_changed("同花顺"))

            # 帮助菜单
            self.menu_bar.help_action.triggered.connect(self.menu_handler.show_help)
            self.menu_bar.update_action.triggered.connect(self.menu_handler.check_update)
            self.menu_bar.about_action.triggered.connect(self.menu_handler.show_about)

            db_admin_action = QAction("数据库管理", self)
            db_admin_action.triggered.connect(self.show_database_admin)
            self.menuBar().addAction(db_admin_action)

            self.log_manager.info("菜单栏创建完成")

            # 连接分布式/云API/指标市场/批量分析入口
            self.menu_bar.node_manager_action.triggered.connect(self.menu_handler.show_node_manager)
            self.menu_bar.cloud_api_action.triggered.connect(self.menu_handler.show_cloud_api_manager)
            self.menu_bar.indicator_market_action.triggered.connect(self.menu_handler.show_indicator_market)
            self.menu_bar.batch_analysis_action.triggered.connect(self.menu_handler.show_batch_analysis)

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
                self.menu_bar.optimization_dashboard_action.triggered.connect(self.menu_handler.show_optimization_dashboard)
                self.menu_bar.one_click_optimize_action.triggered.connect(self.menu_handler.run_one_click_optimization)
                self.menu_bar.smart_optimize_action.triggered.connect(self.menu_handler.run_smart_optimization)
                self.menu_bar.version_manager_action.triggered.connect(self.show_version_management)
                self.menu_bar.performance_evaluation_action.triggered.connect(self.show_performance_evaluation)
                self.menu_bar.optimization_status_action.triggered.connect(self.menu_handler.show_optimization_status)
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
        self.log_manager.info(f"打开数据库管理工具，数据库路径: {db_path}")
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
            self.log_manager.info("状态栏创建完成")
        except Exception as e:
            self.log_manager.error(f"显示状态栏失败: {str(e)}")

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """将弹窗居中 - 委托给MainWindowHelper"""
        self.main_helper.center_dialog(dialog, offset_y)

    def show_about(self):
        """显示关于对话框 - 已移至 gui/handlers/menu_handler.py"""
        self.log_manager.info("请求显示'关于'对话框")
        return self.menu_handler.show_about()

    def show_help(self):
        """显示帮助对话框 - 已移至 gui/handlers/menu_handler.py"""
        self.log_manager.info("请求显示'帮助'对话框")
        return self.menu_handler.show_help()

    def on_theme_changed(self, theme_name):
        self.log_manager.info(f"主题已变更为: {theme_name}")
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
            self.log_manager.info("开始应用主题...")
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
        """创建左侧面板 - 使用新的股票管理面板"""
        try:
            # 创建股票管理面板
            self.stock_panel = StockManagementPanel(parent=self, log_manager=self.log_manager)

            # 连接信号
            self.stock_panel.stock_selected.connect(self.on_stock_selected_from_panel)
            self.stock_panel.indicator_changed.connect(self.on_indicator_changed_from_panel)
            self.stock_panel.export_completed.connect(lambda filename:
                                                      self.show_message("成功", f"数据已导出到: {filename}", "info"))

            # 添加到顶部分割器
            self.top_splitter.addWidget(self.stock_panel)

            self.log_manager.info("左侧面板(股票管理)创建完成")

        except Exception as e:
            self.log_manager.error(f"创建左侧面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

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

    # 注意: add_to_watchlist_by_code 和 add_indicator 方法已移至股票管理面板处理

    @pyqtSlot()
    def filter_stock_list(self, text: str = ""):
        """过滤股票列表 - 委托给股票管理面板"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理
                self.stock_panel.filter_stock_list(text)
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"过滤股票列表失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def filter_indicator_list(self, text: str) -> None:
        """过滤指标列表 - 委托给股票管理面板"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理
                self.stock_panel.filter_indicator_list(text)
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            self.log_manager.error(f"过滤指标列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_time_range_changed(self, time_range: str) -> None:
        """处理时间范围变化事件

        Args:
            time_range: 时间范围名称
        """
        try:
            self.log_manager.info(f"时间范围变更为: {time_range}")
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
            self.log_manager.info(f"分析类型变更为: {analysis_type}")
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

            # 使用UI工厂创建工具栏
            (toolbar_layout, self.period_combo, self.time_range_combo,
             self.start_date_edit, self.end_date_edit, self.chart_type_combo) = UIFactory.create_chart_toolbar()

            # 连接信号
            self.period_combo.currentTextChanged.connect(self.on_period_changed)
            self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
            self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
            self.start_date_edit.dateChanged.connect(lambda d: setattr(self, 'start_date', d))
            self.end_date_edit.dateChanged.connect(lambda d: setattr(self, 'end_date', d))

            self.middle_layout.addLayout(toolbar_layout)

            # 集成多图表分屏控件（外部只暴露 self.chart_widget，分屏仅在 multi_chart_panel 内部管理）
            self.multi_chart_panel = MultiChartPanel(
                self, self.config_manager, self.theme_manager, self.log_manager, rows=3, cols=3)
            self.middle_layout.addWidget(self.multi_chart_panel)
            self.top_splitter.addWidget(self.middle_panel)

            # 关键：主窗口 self.chart_widget 始终指向单屏 ChartWidget 实例
            self.chart_widget = self.multi_chart_panel.single_chart

            # 自动连接区间统计信号
            self.chart_widget.request_stat_dialog.connect(self.show_stat_dialog)

            self.log_manager.info("中间面板(多图表分屏)创建完成")
            add_shadow(self.middle_panel, blur_radius=24, x_offset=0, y_offset=8)
            self.middle_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        except Exception as e:
            self.log_manager.error(f"创建中间面板(多图表分屏)失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            raise

    def show_stat_dialog(self, interval):
        """弹出区间统计弹窗，统计当前区间K线的涨跌幅、均值、最大回撤等，并用专业可视化展示"""
        try:
            self.log_manager.info(f"请求显示区间统计，区间: {interval}")
            start_idx, end_idx = interval
            kdata = getattr(self.chart_widget, 'current_kdata', None)
            if kdata is None or kdata.empty or start_idx >= end_idx:
                self.show_message("提示", "区间数据无效！", "warning")
                return
            sub = kdata.iloc[start_idx:end_idx+1]
            if sub.empty:
                self.show_message("提示", "区间数据无效！", "warning")
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
            self.log_manager.debug(f"图表缩放级别变更为: {zoom_level:.1f}x")
            # 更新状态栏显示缩放级别
            self.status_bar.set_status(f"缩放级别: {zoom_level:.1f}x")
        except Exception as e:
            self.log_manager.error(f"更新缩放级别显示失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def save_chart(self):
        """保存当前图表到文件"""
        try:
            self.log_manager.info("请求保存图表")
            # 直接操作self.chart_widget
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                self.show_message("提示", "当前没有可保存的图表！", "warning")
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
                    self.show_message("提示", "当前图表控件不支持保存！", "warning")
        except Exception as e:
            self.log_manager.error(f"保存图表失败: {str(e)}")

    def reset_chart_view(self):
        """重置图表视图到默认"""
        try:
            self.log_manager.info("请求重置图表视图")
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                self.show_message("提示", "当前没有可重置的图表！", "warning")
                return
            if hasattr(self.chart_widget, 'canvas') and hasattr(self.chart_widget, 'figure'):
                self.chart_widget.figure.tight_layout()
                self.chart_widget.canvas.draw()
            else:
                self.show_message("提示", "当前图表控件不支持重置！", "warning")
        except Exception as e:
            self.log_manager.error(f"重置图表视图失败: {str(e)}")

    def toggle_chart_theme(self):
        """切换图表主题（明亮/暗色）"""
        try:
            self.log_manager.info("请求切换图表主题")
            # 只操作self.chart_widget
            if not hasattr(self, 'chart_widget') or self.chart_widget is None:
                self.show_message("提示", "当前没有可切换主题的图表！", "warning")
                return
            # 获取当前matplotlib样式
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
            # 增加顶部边距，避免与菜单栏重叠，并优化其他边距
            self.right_layout.setContentsMargins(8, 10, 8, 8)  # 左,上,右,下
            self.right_layout.setSpacing(3)  # 稍微增加间距

            # 右侧Tab（唯一入口）
            self.right_tab = QTabWidget(self.right_panel)
            self.right_tab.currentChanged.connect(self.on_right_tab_changed)

            # 设置Tab样式，确保不会与顶部重叠
            self.right_tab.setStyleSheet("""
                QTabWidget {
                    background-color: #ffffff;
                    border: 1px solid #e9ecef;
                    border-radius: 2px;
                    margin-top: 1px;  /* 增加顶部边距 */
                }
                QTabWidget::pane {
                    border: 1px solid #dee2e6;
                    border-radius: 2px;
                    background-color: #ffffff;
                    margin-top: 0px;
                }
                QTabBar::tab {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-bottom: none;
                    padding: 8px 12px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    min-width: 80px;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-color: #1976d2;
                    color: #1976d2;
                    font-weight: bold;
                }
                QTabBar::tab:hover {
                    background-color: #e9ecef;
                }
            """)

            # 单股分析Tab（AnalysisWidget）
            from gui.widgets.analysis_widget import AnalysisWidget
            self.analysis_widget = AnalysisWidget(self.config_manager)
            self.analysis_widget.chart_widget = self.chart_widget
            self.analysis_widget._connect_chart_widget_signals()
            self.right_tab.addTab(self.analysis_widget, "单股分析")

            # 批量回测/AI/策略分析Tab（AnalysisToolsPanel）
            self.analysis_tools_panel = AnalysisPanel(parent=self.right_tab)
            self.right_tab.addTab(self.analysis_tools_panel, "批量回测/AI/策略分析")

            # 行业优选Tab（可选扩展）
            try:
                # 使用已创建的analysis_widget的sector_flow功能
                sector_flow_tab = self.analysis_widget.create_sector_flow_tab()
                self.add_tab_with_toolbar(sector_flow_tab, "行业优选", "行业主力资金流向、概念流向、北向资金等一览，支持一键分析与导出")
            except Exception as e:
                self.log_manager.error(f"行业优选Tab初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

            # 自定义Tab
            try:
                self.custom_tab = QWidget()
                custom_layout = QVBoxLayout(self.custom_tab)
                custom_layout.setContentsMargins(10, 10, 10, 10)  # 增加内边距
                custom_label = QLabel("自定义面板，用户可扩展功能或添加小工具。")
                custom_label.setStyleSheet("""
                    QLabel {
                        color: #666;
                        font-size: 14px;
                        padding: 20px;
                        text-align: center;
                        background-color: #f8f9fa;
                        border-radius: 5px;
                        border: 1px solid #e9ecef;
                    }
                """)
                custom_layout.addWidget(custom_label)
                self.right_tab.addTab(self.custom_tab, "自定义")
            except Exception as e:
                self.log_manager.error(f"自定义Tab初始化失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

            self.right_layout.addWidget(self.right_tab)

            # 优化右侧面板的整体样式设置
            self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.right_panel.setMinimumWidth(350)
            self.right_panel.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border-left: 1px solid #e9ecef;
                }
            """)

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
            if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                kdata = kdata.copy()
                kdata['code'] = self.current_stock
            widget.set_kdata(kdata)

    def on_right_tab_changed(self, index):
        tab_text = self.right_tab.tabText(index)
        self.log_manager.info(f"右侧Tab已切换到: '{tab_text}' (索引: {index})")
        # 延迟加载多维分析Tab
        if tab_text == "多维分析" and not getattr(self, "analysis_tab_loaded", False):
            try:
                # 使用已创建的analysis_widget，而不是重新创建
                if hasattr(self, 'analysis_widget') and self.analysis_widget:
                    self.analysis_tab_layout.addWidget(self.analysis_widget)
                    self.analysis_tab_loaded = True
                    self.log_manager.info("多维分析Tab已延迟加载")
                else:
                    # 如果没有analysis_widget，则创建一个
                    self.analysis_widget = AnalysisWidget(self.config_manager)
                    self.analysis_widget.chart_widget = self.chart_widget
                    self.analysis_widget._connect_chart_widget_signals()
                    self.analysis_tab_layout.addWidget(self.analysis_widget)
                    self.analysis_tab_loaded = True
                    self.log_manager.info("多维分析Tab已延迟加载（新创建）")
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

    # 注意: optimize 方法已移至 gui/handlers/menu_handler.py 的 MenuHandler 类中

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
            # 使用UI工厂创建标准参数控件
            self.param_controls = UIFactory.create_standard_parameter_controls()

            # 添加参数控件到布局
            for name, control in self.param_controls.items():
                layout.addRow(name + ":", control)

            # 使用UI工厂创建回测设置组
            backtest_group = UIFactory.create_backtest_controls()
            layout.addWidget(backtest_group)

            # 使用UI工厂创建风险管理组
            risk_group = UIFactory.create_risk_controls()
            layout.addWidget(risk_group)

            # 为了向后兼容，获取控件引用
            self._extract_control_references(backtest_group, risk_group)

        except Exception as e:
            self.log_manager.error(f"创建控制按钮失败: {str(e)}")
            raise

    def _extract_control_references(self, backtest_group, risk_group):
        """提取控件引用，用于向后兼容"""
        try:
            # 获取回测组件引用
            backtest_layout = backtest_group.layout()
            self.initial_capital = self._find_control_by_row(backtest_layout, "初始资金")
            self.commission_rate = self._find_control_by_row(backtest_layout, "佣金率")
            self.slippage = self._find_control_by_row(backtest_layout, "滑点")
            self.position_combo = self._find_control_by_row(backtest_layout, "仓位管理")
            self.position_size = self._find_control_by_row(backtest_layout, "仓位比例")

            # 获取风险管理组件引用
            risk_layout = risk_group.layout()
            self.stop_loss = self._find_control_by_row(risk_layout, "止损比例")
            self.take_profit = self._find_control_by_row(risk_layout, "止盈比例")
            self.max_drawdown = self._find_control_by_row(risk_layout, "最大回撤")
            self.risk_free_rate = self._find_control_by_row(risk_layout, "无风险利率")
        except Exception as e:
            self.log_manager.warning(f"提取控件引用失败: {str(e)}")

    def _find_control_by_row(self, layout, label_text):
        """根据标签文本查找控件"""
        try:
            for i in range(layout.rowCount()):
                label_item = layout.itemAt(i, QFormLayout.LabelRole)
                if label_item and hasattr(label_item.widget(), 'text'):
                    if label_text in label_item.widget().text():
                        field_item = layout.itemAt(i, QFormLayout.FieldRole)
                        return field_item.widget() if field_item else None
            return None
        except Exception:
            return None

    def on_period_changed(self, period: str):
        """切换K线周期时，主动推送最新K线数据到所有分析Tab"""
        try:
            self.log_manager.info(f"K线周期变更为: {period}")
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
        self.log_manager.info(f"策略变更为: {strategy}")
        self.refresh_strategy_params()
        # 其他逻辑...

    def update_strategy(self) -> None:
        """更新当前策略（已废弃，统一由ChartWidget处理）"""
        try:
            if not self.current_stock:
                return
            self.log_manager.debug(f"请求更新策略显示，当前股票: {self.current_stock}")
            # 直接刷新图表即可，指标渲染由ChartWidget内部处理
            self.update_chart()
        except Exception as e:
            self.log_manager.log(f"更新策略失败: {str(e)}", LogLevel.ERROR)

    def load_favorites(self):
        """加载收藏夹 - 委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                self.stock_panel.load_favorites()
            else:
                self.log_manager.warning("股票管理面板未初始化，无法加载收藏夹")
        except Exception as e:
            self.log_manager.error(f"加载收藏夹失败: {str(e)}")

    def save_favorites(self):
        """保存收藏夹 - 委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                self.stock_panel.save_favorites()
            else:
                self.log_manager.warning("股票管理面板未初始化，无法保存收藏夹")
        except Exception as e:
            self.log_manager.error(f"保存收藏夹失败: {str(e)}")

    def toggle_favorite(self, item=None):
        """切换股票的收藏状态，委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理
                self.stock_panel.toggle_favorite(item)
                # 同步收藏列表
                self.favorites = self.stock_panel.favorites
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            self.log_manager.error(f"切换收藏状态失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def update_stock_list_ui(self):
        """更新股票列表的显示，委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel'):
                # 委托给股票管理面板处理
                self.stock_panel.update_stock_list_display()
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            self.log_manager.error(f"更新股票列表显示失败: {str(e)}")
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")

    def clear_log(self) -> None:
        """清除日志内容，优化UI刷新机制"""
        try:
            self.log_manager.info("请求清除日志内容")
            # 使用系统日志组件记录操作
            from utils.ui_optimizer import schedule_ui_update

            logger = get_logger(__name__)
            logger.info("开始清除日志操作")

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
            logger.info("日志清除操作完成")

            # 使用优化的UI更新机制，替换QApplication.processEvents()
            schedule_ui_update(callback=self._update_ui_after_log_clear, delay=0)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"清除日志失败: {str(e)}")
            self.log_manager.error(f"清除日志失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"清除日志失败: {str(e)}")

    def _update_ui_after_log_clear(self):
        """日志清除后的UI更新回调"""
        try:
            logger = get_logger(__name__)

            # 更新状态栏
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("日志已清除", 2000)

            logger.debug("日志清除后UI更新完成")
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"日志清除后UI更新失败: {str(e)}")

    def handle_performance_alert(self, message: str) -> None:
        """处理性能警告，优化警告处理

        Args:
            message: 性能警告消息
        """
        try:
            self.log_manager.warning(f"性能警告: {message}")
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
            self.log_manager.info("请求显示高级搜索对话框")
            dialog = AdvancedSearchDialog(self, self.data_manager, self.log_manager)
            dialog.search_completed.connect(self._handle_search_results)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示高级搜索对话框失败: {str(e)}")

    def _handle_search_results(self, filtered_stocks):
        """处理搜索结果"""
        try:
            self.log_manager.info(f"高级搜索完成，找到 {len(filtered_stocks)} 只符合条件的股票")
            # 委托给股票管理面板处理搜索结果
            if hasattr(self, 'stock_panel'):
                self.stock_panel.update_search_results(filtered_stocks)
            else:
                # 备用处理方式
                self._update_stock_list_with_results(filtered_stocks)

            self.log_manager.info(f"找到 {len(filtered_stocks)} 只符合条件的股票")
        except Exception as e:
            self.log_manager.error(f"处理搜索结果失败: {str(e)}")

    def _update_stock_list_with_results(self, filtered_stocks):
        """更新股票列表显示搜索结果（备用方法）"""
        try:
            if hasattr(self, 'stock_list'):
                self.stock_list.clear()
                for stock in filtered_stocks:
                    item = QListWidgetItem(f"{stock['code']} {stock['name']}")

                    # 设置工具提示
                    tooltip = (
                        f"代码: {stock['code']}\n"
                        f"名称: {stock['name']}\n"
                        f"市场: {stock.get('market', '未知')}\n"
                        f"行业: {stock.get('industry', '未知')}"
                    )
                    item.setToolTip(tooltip)
                    item.setData(Qt.UserRole, stock)

                    # 设置收藏状态
                    if stock['code'] in self.favorites:
                        item.setText(f"★ {item.text()}")

                    self.stock_list.addItem(item)
        except Exception as e:
            self.log_manager.error(f"更新股票列表失败: {str(e)}")

    def perform_advanced_search(self, conditions: dict) -> None:
        """执行高级搜索 - 已移至对话框模块处理"""
        # 该方法已废弃，功能移至AdvancedSearchDialog
        pass

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
                        if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns:
                            kdata = kdata.copy()
                            kdata['code'] = stock_code
                        main_widget.set_kdata(kdata)
            # 兼容analysis_widget等单独实例
            if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                kdata = self.get_kdata(self.current_stock)
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
        """处理指标变化事件，委托给股票管理面板处理"""
        try:
            self.log_manager.info("指标列表发生变化，请求刷新")
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理指标变化
                self.stock_panel.on_indicators_changed()
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            self.log_manager.error(f"处理指标变化事件失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def show_indicator_params_dialog(self) -> None:
        """显示指标参数设置对话框，委托给股票管理面板处理"""
        try:
            self.log_manager.info("请求显示指标参数设置对话框")
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理
                if hasattr(self.stock_panel, 'show_indicator_params_dialog'):
                    self.stock_panel.show_indicator_params_dialog()
                else:
                    self.show_message("提示", "指标参数设置功能正在开发中", "info")
            else:
                self.show_message("提示", "股票管理面板未初始化", "warning")
        except Exception as e:
            self.log_manager.error(f"显示指标参数设置对话框失败: {str(e)}")
            self.show_message("错误", f"显示指标参数设置对话框失败: {str(e)}", "error")

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
        """更新股票列表，委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel'):
                # 委托给股票管理面板处理
                self.stock_panel.refresh_stock_list()
                # 同时更新显示
                self.stock_panel.update_stock_list_display()
            else:
                self.log_manager.warning("股票管理面板未初始化")
        except Exception as e:
            self.log_manager.error(f"更新股票列表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")

    # 为了向后兼容，保留别名
    def update_stock_list_ui(self):
        """更新股票列表的显示，委托给update_stock_list处理"""
        self.update_stock_list()

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
        """导出股票列表到文件，委托给股票管理面板处理"""
        try:
            if hasattr(self, 'stock_panel') and self.stock_panel:
                # 委托给股票管理面板处理
                self.stock_panel.export_stock_list()
            else:
                self.log_manager.warning("股票管理面板未初始化")
                self.show_message("警告", "股票管理面板未初始化，无法导出", "warning")
        except Exception as e:
            self.log_manager.error(f"导出股票列表失败: {str(e)}")
            self.show_message("错误", f"导出股票列表失败: {str(e)}", "error")

    def init_panels(self):
        """初始化功能面板"""
        try:
            self.log_manager.info("初始化功能面板...")

            # 创建股票管理面板
            self.stock_panel = StockManagementPanel(self)

            # 创建图表分析面板
            self.chart_panel = ChartAnalysisPanel(self)

            # 创建分析面板
            self.analysis_panel = AnalysisPanel(self)

            # 创建策略管理器
            self.strategy_manager = StrategyManager(self)

            # 创建优化管理器
            self.optimization_manager = OptimizationManager(self)

            # 创建质量管理器
            self.quality_manager = QualityManager(self)

            # 连接面板信号
            self.connect_panel_signals()

            self.log_manager.info("功能面板初始化完成")

        except Exception as e:
            self.log_manager.error(f"功能面板初始化失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def connect_panel_signals(self):
        """连接面板信号"""
        try:
            # 连接股票管理面板信号
            if hasattr(self, 'stock_panel'):
                self.stock_panel.stock_selected.connect(self.on_stock_selected_from_panel)

            # 连接图表分析面板信号
            if hasattr(self, 'chart_panel'):
                self.chart_panel.chart_updated.connect(self.on_chart_updated)
                self.chart_panel.indicator_changed.connect(self.on_indicator_changed_from_panel)

            # 连接分析面板信号
            if hasattr(self, 'analysis_panel'):
                self.analysis_panel.analysis_started.connect(self.on_analysis_started)

            # 连接策略管理器信号
            if hasattr(self, 'strategy_manager'):
                self.strategy_manager.strategy_created.connect(lambda name: self.log_manager.info(f"策略已创建: {name}"))
                self.strategy_manager.backtest_started.connect(lambda name: self.log_manager.info(f"回测已开始: {name}"))

            # 连接优化管理器信号
            if hasattr(self, 'optimization_manager'):
                self.optimization_manager.optimization_started.connect(lambda name: self.log_manager.info(f"优化已开始: {name}"))

            # 连接质量管理器信号
            if hasattr(self, 'quality_manager'):
                self.quality_manager.quality_check_started.connect(lambda name: self.log_manager.info(f"质量检查已开始: {name}"))

            self.log_manager.info("面板信号连接完成")

        except Exception as e:
            self.log_manager.error(f"连接面板信号失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_stock_selected_from_panel(self, stock_code: str):
        """处理从面板选择的股票"""
        try:
            self.current_stock = stock_code
            self.update_chart()
            self.log_manager.info(f"从面板选择股票: {stock_code}")
        except Exception as e:
            self.log_manager.error(f"处理面板股票选择失败: {str(e)}")

    def on_chart_updated(self, chart_data: dict):
        """处理图表更新"""
        try:
            # 更新主图表
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_chart(chart_data)
            self.log_manager.info("图表已更新")
        except Exception as e:
            self.log_manager.error(f"处理图表更新失败: {str(e)}")

    def on_indicator_changed_from_panel(self, indicator_name: str, params: dict):
        """处理从面板变化的指标 - 修复版本，支持清除指标和多指标处理"""
        try:
            if indicator_name == "clear_all":
                # 清除所有指标
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.clear_indicators()
                    self.update_chart()
                self.log_manager.info("已清除所有指标")

            elif indicator_name == "multiple" and "indicators" in params:
                # 处理多个指标选择
                indicators = params["indicators"]

                # 先清除现有指标
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.clear_indicators()

                # 添加新选择的指标
                for indicator_info in indicators:
                    if hasattr(self, 'chart_widget'):
                        try:
                            self.chart_widget.add_indicator(indicator_info)
                        except Exception as e:
                            indicator_name = getattr(indicator_info, 'name', indicator_info.get(
                                'name', 'unknown') if isinstance(indicator_info, dict) else 'unknown')
                            self.log_manager.error(f"添加指标 {indicator_name} 失败: {str(e)}")

                # 更新图表显示
                self.update_chart()

                indicator_names = []
                for ind in indicators:
                    if hasattr(ind, 'chinese_name'):
                        indicator_names.append(ind.chinese_name)
                    elif hasattr(ind, 'name'):
                        indicator_names.append(ind.name)
                    elif isinstance(ind, dict):
                        indicator_names.append(ind.get('chinese_name', ind.get('name', '')))
                    else:
                        indicator_names.append(str(ind))
                self.log_manager.info(f"已更新多个指标: {', '.join(indicator_names)}")

            else:
                # 处理单个指标
                if hasattr(self, 'chart_widget'):
                    try:
                        self.chart_widget.add_indicator({
                            'name': indicator_name,
                            'params': params
                        })
                        self.update_chart()
                        self.log_manager.info(f"已更新指标: {indicator_name}")
                    except Exception as e:
                        self.log_manager.error(f"添加单个指标 {indicator_name} 失败: {str(e)}")

        except Exception as e:
            self.log_manager.error(f"处理面板指标变化失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_analysis_started(self, analysis_type: str):
        """处理分析开始"""
        try:
            self.log_manager.info(f"分析已开始: {analysis_type}")
            # 可以在这里添加进度显示等
        except Exception as e:
            self.log_manager.error(f"处理分析开始失败: {str(e)}")

    def check_single_stock_quality(self):
        """检查单只股票的数据质量"""
        try:
            self.log_manager.info("请求检查单只股票数据质量")
            if hasattr(self, 'quality_manager'):
                self.quality_manager.check_single_stock_quality()
            else:
                self.log_manager.warning("质量管理器未初始化")
        except Exception as e:
            self.log_manager.error(f"检查单只股票质量失败: {str(e)}")
            self.handle_error(f"检查单只股票质量失败: {str(e)}")

    def check_all_stocks_quality(self):
        """检查所有股票的数据质量"""
        try:
            self.log_manager.info("请求检查所有股票数据质量")
            if hasattr(self, 'quality_manager'):
                self.quality_manager.check_all_stocks_quality()
            else:
                self.log_manager.warning("质量管理器未初始化")
        except Exception as e:
            self.log_manager.error(f"检查所有股票质量失败: {str(e)}")
            self.handle_error(f"检查所有股票质量失败: {str(e)}")

    def show_performance_evaluation(self):
        """显示性能评估 - 委托给优化管理器处理"""
        try:
            self.log_manager.info("请求显示性能评估")
            if hasattr(self, 'optimization_manager'):
                self.optimization_manager.show_performance_evaluation()
            else:
                self.show_message("信息", "性能评估功能正在开发中...", "info")
        except Exception as e:
            self.handle_error(f"显示性能评估失败: {str(e)}")

    def show_version_management(self):
        """显示版本管理"""
        try:
            self.log_manager.info("请求显示版本管理")
            if hasattr(self, 'optimization_manager'):
                self.optimization_manager.show_version_management()
            else:
                self.log_manager.warning("优化管理器未初始化")
        except Exception as e:
            self.log_manager.error(f"显示版本管理失败: {str(e)}")
            self.handle_error(f"显示版本管理失败: {str(e)}")

    def handle_error(self, error_msg: str):
        """统一错误处理 - 委托给MainWindowHelper"""
        self.main_helper.handle_error(error_msg)

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """统一消息显示 - 委托给MainWindowHelper"""
        self.main_helper.show_message(title, message, msg_type)

    def cleanup_memory(self):
        """清理内存 - 委托给MainWindowHelper"""
        self.main_helper.cleanup_memory()

    def show_log_panel(self):
        """显示日志面板"""
        try:
            if hasattr(self, 'log_widget'):
                self.log_widget.setVisible(True)
        except Exception as e:
            self.log_manager.error(f"显示日志面板失败: {str(e)}")

    def toggle_log_panel(self):
        """切换日志面板的显示/隐藏状态"""
        try:
            if hasattr(self, 'bottom_panel'):
                current_visible = self.bottom_panel.isVisible()
                self.bottom_panel.setVisible(not current_visible)

                # 调整分割器的大小分配
                if hasattr(self, 'main_layout') and hasattr(self, 'top_splitter') and hasattr(self, 'bottom_splitter'):
                    if current_visible:
                        # 隐藏日志面板时，将所有空间给top_splitter
                        self.main_layout.setStretchFactor(self.top_splitter, 1)
                        self.main_layout.setStretchFactor(self.bottom_splitter, 0)
                        # 设置bottom_splitter的最小和最大高度为0
                        self.bottom_splitter.setMaximumHeight(0)
                        self.bottom_splitter.setMinimumHeight(0)
                    else:
                        # 显示日志面板时，恢复原有比例
                        self.main_layout.setStretchFactor(self.top_splitter, 8)
                        self.main_layout.setStretchFactor(self.bottom_splitter, 2)
                        # 恢复bottom_splitter的高度限制
                        self.bottom_splitter.setMaximumHeight(16777215)  # Qt的默认最大值
                        self.bottom_splitter.setMinimumHeight(100)

                # 更新按钮文本
                if hasattr(self, 'log_btn'):
                    if current_visible:
                        self.log_btn.setText("显示日志")
                        self.log_manager.info("日志面板已隐藏")
                    else:
                        self.log_btn.setText("隐藏日志")
                        self.log_manager.info("日志面板已显示")

                # 如果显示日志面板，确保日志控件也可见
                if not current_visible and hasattr(self, 'log_widget'):
                    self.log_widget.setVisible(True)

                # 强制更新布局
                if hasattr(self, 'main_layout'):
                    self.main_layout.update()
                if hasattr(self, 'centralWidget'):
                    self.centralWidget().updateGeometry()
                self.update()

            elif hasattr(self, 'log_widget'):
                # 备用方案：如果没有底部面板，直接控制日志控件
                current_visible = self.log_widget.isVisible()
                self.log_widget.setVisible(not current_visible)

                # 更新按钮文本
                if hasattr(self, 'log_btn'):
                    if current_visible:
                        self.log_btn.setText("显示日志")
                    else:
                        self.log_btn.setText("隐藏日志")

                self.log_manager.info(f"日志面板已{'隐藏' if current_visible else '显示'}")
            else:
                self.log_manager.warning("日志面板未初始化")
        except Exception as e:
            self.log_manager.error(f"切换日志面板失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def refresh_tab_content(self, widget):
        """刷新标签页内容"""
        try:
            if widget is None:
                return

            # 检查是否有refresh方法
            if hasattr(widget, 'refresh'):
                widget.refresh()
            elif hasattr(widget, 'update'):
                widget.update()
            elif hasattr(widget, 'reload'):
                widget.reload()
            else:
                self.log_manager.info(f"标签页控件 {type(widget).__name__} 没有刷新方法")

        except Exception as e:
            self.log_manager.error(f"刷新标签页内容失败: {str(e)}")

    def show_error_message(self, title: str, message: str):
        """显示错误消息"""
        try:
            QMessageBox.critical(self, title, message)
        except Exception as e:
            self.log_manager.error(f"显示错误消息失败: {str(e)}")

    def show_warning_message(self, title: str, message: str):
        """显示警告消息"""
        try:
            QMessageBox.warning(self, title, message)
        except Exception as e:
            self.log_manager.error(f"显示警告消息失败: {str(e)}")

    def refresh_strategy_params(self):
        """刷新策略参数"""
        try:
            # 这里可以根据需要实现策略参数刷新逻辑
            self.log_manager.info("策略参数已刷新")
        except Exception as e:
            self.log_manager.error(f"刷新策略参数失败: {str(e)}")

    def update_analysis(self):
        """更新分析结果"""
        try:
            if hasattr(self, 'analysis_widget'):
                # 触发分析更新
                if hasattr(self.analysis_widget, 'update_analysis'):
                    self.analysis_widget.update_analysis()

            # 更新其他分析相关组件
            if hasattr(self, 'analysis_tools_panel'):
                if hasattr(self.analysis_tools_panel, 'refresh'):
                    self.analysis_tools_panel.refresh()

            self.log_manager.info("分析结果已更新")
        except Exception as e:
            self.log_manager.error(f"更新分析结果失败: {str(e)}")

    def update_performance_metrics(self):
        """更新性能指标 - 已移至性能管理器"""
        pass

    def update_indicators(self):
        """更新指标，委托给图表控件和股票管理面板处理"""
        try:
            # 更新图表中的指标显示
            if hasattr(self, 'chart_widget'):
                self.update_chart()

            # 通知股票管理面板指标已更新
            if hasattr(self, 'stock_panel') and self.stock_panel:
                if hasattr(self.stock_panel, 'on_indicators_changed'):
                    self.stock_panel.on_indicators_changed()

            self.log_manager.info("指标更新完成")
        except Exception as e:
            self.log_manager.error(f"更新指标失败: {str(e)}")

    def update_chart(self):
        """更新图表"""
        try:
            if hasattr(self, 'chart_widget') and self.current_stock:
                # 获取当前股票的K线数据
                kdata = self.get_kdata(self.current_stock)
                if kdata is not None and not kdata.empty:
                    # 构造数据字典并传递给图表控件
                    chart_data = {
                        'kdata': kdata,
                        'stock_code': self.current_stock,
                        'title': f"{self.current_stock}",
                        'period': getattr(self, 'current_period', 'D'),
                        'chart_type': getattr(self, 'current_chart_type', 'candlestick')
                    }
                    self.chart_widget.update_chart(chart_data)
                    self.log_manager.info(f"图表更新完成: {self.current_stock}")
                else:
                    # 没有数据时显示无数据提示
                    self.chart_widget.show_no_data(f"无法获取 {self.current_stock} 的数据")
                    self.log_manager.warning(f"update_chart无法获取股票数据: {self.current_stock}")
        except Exception as e:
            self.log_manager.error(f"更新图表失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            # 显示错误信息到图表
            if hasattr(self, 'chart_widget'):
                self.chart_widget.show_no_data(f"更新图表失败: {str(e)}")

    def get_kdata(self, stock_code: str):
        """获取K线数据，委托给股票管理面板或数据管理器处理"""
        try:
            # 优先使用股票管理面板的方法（带缓存）
            if hasattr(self, 'stock_panel') and self.stock_panel:
                return self.stock_panel.get_kdata(stock_code)
            # 备用方案：直接使用数据管理器
            elif hasattr(self, 'data_manager'):
                return self.data_manager.get_k_data(stock_code)
            else:
                self.log_manager.warning("无法获取K线数据：股票面板和数据管理器都未初始化")
                return None
        except Exception as e:
            self.log_manager.error(f"获取K线数据失败: {str(e)}")
            return None

    def broadcast_kdata_to_tabs(self, kdata):
        """广播K线数据到标签页"""
        try:
            if kdata is None:
                return

            # 确保K线数据包含股票代码
            if isinstance(kdata, pd.DataFrame) and 'code' not in kdata.columns and hasattr(self, 'current_stock'):
                kdata = kdata.copy()
                kdata['code'] = self.current_stock

            # 广播到analysis_widget
            if hasattr(self, 'analysis_widget') and hasattr(self.analysis_widget, 'set_kdata'):
                self.analysis_widget.set_kdata(kdata)

            # 广播到右侧标签页中的分析组件
            if hasattr(self, 'right_tab'):
                for i in range(self.right_tab.count()):
                    try:
                        tab_widget = self.right_tab.widget(i)
                        if tab_widget is not None:
                            # 检查是否有直接的set_kdata方法
                            if hasattr(tab_widget, 'set_kdata'):
                                tab_widget.set_kdata(kdata)

                            # 检查布局中的子控件
                            if hasattr(tab_widget, 'layout') and tab_widget.layout():
                                for j in range(tab_widget.layout().count()):
                                    item = tab_widget.layout().itemAt(j)
                                    if item and item.widget():
                                        widget = item.widget()
                                        if hasattr(widget, 'set_kdata'):
                                            widget.set_kdata(kdata)
                    except Exception as e:
                        self.log_manager.warning(f"广播K线数据到标签页{i}失败: {str(e)}")
                        continue

            # 广播到其他需要K线数据的组件
            components_with_kdata = [
                'trading_widget',
                'analysis_tools_panel',
                'stock_screener_widget'
            ]

            for component_name in components_with_kdata:
                if hasattr(self, component_name):
                    component = getattr(self, component_name)
                    if hasattr(component, 'set_kdata'):
                        try:
                            component.set_kdata(kdata)
                        except Exception as e:
                            self.log_manager.warning(f"广播K线数据到{component_name}失败: {str(e)}")

            self.log_manager.debug("K线数据广播完成")

        except Exception as e:
            self.log_manager.error(f"广播K线数据失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def on_chart_type_changed(self, chart_type: str):
        """图表类型变化处理"""
        try:
            self.log_manager.info(f"图表类型变更为: {chart_type}")
            self.current_chart_type = chart_type.lower()
            self.update_chart()
            self.log_manager.info(f"图表类型已切换为: {chart_type}")
        except Exception as e:
            self.log_manager.error(f"切换图表类型失败: {str(e)}")

    def on_industry_changed(self, industry: str):
        """行业变化处理"""
        try:
            self.log_manager.info(f"行业筛选变更为: {industry}")
            self.current_industry = industry
            self.filter_stock_list()
            self.log_manager.info(f"行业筛选已切换为: {industry}")
        except Exception as e:
            self.log_manager.error(f"切换行业筛选失败: {str(e)}")

    def _on_industry_data_updated(self, data):
        """行业数据更新处理"""
        try:
            # 更新行业下拉框
            if hasattr(self, 'industry_combo'):
                current_text = self.industry_combo.currentText()
                self.industry_combo.clear()
                self.industry_combo.addItem("全部")
                if isinstance(data, dict):
                    self.industry_combo.addItems(list(data.keys()))
                self.industry_combo.setCurrentText(current_text)
        except Exception as e:
            self.log_manager.error(f"更新行业数据失败: {str(e)}")

    def init_market_industry_mapping(self):
        """初始化市场和行业映射"""
        try:
            # 市场映射
            self.market_block_mapping = {
                "沪市": ["sh"],
                "深市": ["sz"],
                "创业板": ["sz"],
                "科创板": ["sh"]
            }

            # 行业映射（示例）
            self.industry_mapping = {
                "银行": "银行业",
                "证券": "证券业",
                "保险": "保险业",
                "房地产": "房地产业",
                "医药": "医药制造业",
                "汽车": "汽车制造业",
                "电子": "电子信息业",
                "钢铁": "钢铁业",
                "煤炭": "煤炭业",
                "有色": "有色金属业"
            }

            self.log_manager.info("市场和行业映射初始化完成")
        except Exception as e:
            self.log_manager.error(f"初始化市场和行业映射失败: {str(e)}")

    def preload_data(self):
        """预加载常用数据，委托给面板和数据管理器处理"""
        try:
            self.log_manager.info("开始预加载数据...")
            if hasattr(self, 'stock_panel'):
                self.stock_panel.refresh_stock_list()
            if hasattr(self, 'data_manager'):
                stocks_df = self.data_manager.get_stock_list()
                if not stocks_df.empty:
                    self.log_manager.info(f"数据预加载完成，共加载 {len(stocks_df)} 只股票")
        except Exception as e:
            self.log_manager.error(f"预加载数据失败: {str(e)}")

    def _on_performance_update(self, operation_name: str, metrics):
        """性能更新回调"""
        try:
            # 如果操作时间过长，记录警告
            if metrics.execution_time > 5.0:  # 超过5秒
                self.log_manager.warning(f"操作 '{operation_name}' 执行时间过长: {metrics.execution_time:.2f}秒")

            # 如果内存使用过多，触发清理
            if metrics.memory_usage_mb > 100:  # 超过100MB
                self.log_manager.warning(f"操作 '{operation_name}' 内存使用过多: {metrics.memory_usage_mb:.2f}MB")

        except Exception as e:
            self.log_manager.error(f"性能回调处理失败: {e}")

    def get_performance_stats(self) -> dict:
        """获取系统性能统计"""
        try:
            return self.performance_manager.get_performance_stats()
        except Exception as e:
            self.log_manager.error(f"获取性能统计失败: {e}")
            return {}

    def cleanup_system_memory(self):
        """清理系统内存"""
        try:
            collected = self.performance_manager.cleanup_memory(force=True)
            self.log_manager.info(f"系统内存清理完成，回收对象: {collected}")
            return collected
        except Exception as e:
            self.log_manager.error(f"系统内存清理失败: {e}")
            return 0

    def on_splitter_moved(self, pos: int, index: int):
        """处理分割器移动事件"""
        try:
            # 记录分割器位置变化
            sender = self.sender()
            if sender == self.top_splitter:
                self.log_manager.debug(f"顶部分割器移动: 位置={pos}, 索引={index}")
            elif sender == self.bottom_splitter:
                self.log_manager.debug(f"底部分割器移动: 位置={pos}, 索引={index}")

            # 可以在这里添加布局保存逻辑

        except Exception as e:
            self.log_manager.error(f"处理分割器移动事件失败: {str(e)}")

    def on_language_changed(self, language_code: str):
        """处理语言变更事件 - 使用新的语言切换管理器"""
        try:
            self.log_manager.info(f"接收到语言变更请求: {language_code}")
            # 使用新的语言切换管理器
            if hasattr(self, 'language_switch_manager'):
                success = self.language_switch_manager.switch_language(
                    language_code,
                    ui_update_callback=self._update_minimal_ui_text
                )
                if not success:
                    self.log_manager.warning(f"语言切换请求被拒绝: {language_code}")
            else:
                # 备用方案：使用原有逻辑（向后兼容）
                self.log_manager.warning("语言切换管理器未初始化，使用备用方案")
                self._fallback_language_change(language_code)

        except Exception as e:
            self.log_manager.error(f"处理语言变更事件失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            # 显示错误信息到状态栏，避免弹窗阻塞
            if hasattr(self, 'status_bar'):
                self.status_bar.set_status(f"语言切换失败: {str(e)}", timeout=3000)

    def _on_language_switch_completed(self, language_code: str):
        """语言切换完成的处理"""
        try:
            self.log_manager.info(f"语言切换已完成: {language_code}")

            # 更新菜单栏选中状态
            self._update_menu_language_selection_safe(language_code)

            # 更新状态栏
            if hasattr(self, 'status_bar'):
                self.status_bar.set_status(_("language_switched", "语言已切换"), timeout=2000)

            # 发送语言变更信号给其他组件
            self.language_changed.emit(language_code)

        except Exception as e:
            self.log_manager.error(f"处理语言切换完成事件失败: {str(e)}")

    def _on_language_switch_failed(self, language_code: str, error_msg: str):
        """语言切换失败的处理"""
        try:
            self.log_manager.error(f"语言切换失败: {language_code} - {error_msg}")

            # 显示错误信息到状态栏
            if hasattr(self, 'status_bar'):
                self.status_bar.set_status(f"语言切换失败: {error_msg}", timeout=5000)

            # 可以在这里添加其他错误处理逻辑

        except Exception as e:
            self.log_manager.error(f"处理语言切换失败事件失败: {str(e)}")

    def _fallback_language_change(self, language_code: str):
        """备用的语言切换方案（向后兼容）"""
        try:
            # 检查语言代码有效性
            if not language_code or not isinstance(language_code, str):
                self.log_manager.warning(f"无效的语言代码: {language_code}")
                return

            # 检查是否需要切换
            current_language = self.i18n_manager.get_current_language()
            if language_code == current_language:
                self.log_manager.debug(f"语言未变化，跳过切换: {language_code}")
                return

            # 设置语言
            self.i18n_manager.set_language(language_code)

            # 异步保存配置
            ui_config = self.config_manager.get('ui', {})
            ui_config['language'] = language_code
            self.config_manager.set_async('ui', ui_config)

            # 更新UI
            self._update_minimal_ui_text(language_code)

            # 更新菜单
            self._update_menu_language_selection_safe(language_code)

            self.log_manager.info(f"备用语言切换完成: {language_code}")

        except Exception as e:
            self.log_manager.error(f"备用语言切换失败: {str(e)}")

    def _save_language_config_truly_async(self, language_code: str):
        """真正异步保存语言配置，使用QThread避免阻塞主线程 - 已移至语言切换管理器"""
        self.log_manager.warning("_save_language_config_truly_async已废弃，请使用语言切换管理器")
        if hasattr(self, 'language_switch_manager'):
            self.language_switch_manager.switch_language(language_code)

    def _update_minimal_ui_text(self, language_code: str):
        """最小化UI文本更新，只更新关键元素，避免大量刷新"""
        try:
            # 只更新窗口标题
            self.setWindowTitle(_("main_window_title", "HIkyuu量化交易系统"))

            # 只更新状态栏
            if hasattr(self, 'status_bar'):
                self.status_bar.set_status(_("ready", "就绪"))

            # 不进行全面的UI刷新，避免卡死
            self.log_manager.debug("最小化UI文本更新完成")

        except Exception as e:
            self.log_manager.warning(f"更新UI文本失败: {str(e)}")

    def _update_menu_language_selection_safe(self, language_code: str):
        """安全更新菜单栏语言选择状态，防止信号循环"""
        try:
            if hasattr(self, 'menu_bar') and hasattr(self.menu_bar, 'language_actions'):
                # 临时断开信号连接，防止循环触发
                if hasattr(self.menu_bar, 'language_group'):
                    try:
                        self.menu_bar.language_group.triggered.disconnect()
                    except TypeError:
                        # 信号可能已经断开，忽略错误
                        pass

                # 更新选中状态
                for lang_code, action in self.menu_bar.language_actions.items():
                    action.setChecked(lang_code == language_code)

                # 重新连接信号
                if hasattr(self.menu_bar, 'language_group'):
                    self.menu_bar.language_group.triggered.connect(self._on_language_action_triggered)

                self.log_manager.debug(f"菜单语言选择状态已更新: {language_code}")

        except Exception as e:
            self.log_manager.warning(f"更新菜单语言选择状态失败: {str(e)}")

    def _clear_language_changing_flag(self):
        """清除语言切换防护标志 - 已废弃，由语言切换管理器处理"""
        self.log_manager.debug("_clear_language_changing_flag已废弃，由语言切换管理器处理")

    def _on_language_action_triggered(self, action):
        """处理语言动作组信号 - 优化版本"""
        try:
            # 检查是否正在切换语言
            if hasattr(self, 'language_switch_manager') and self.language_switch_manager.is_switching():
                self.log_manager.debug("语言切换中，忽略菜单信号")
                return

            language_code = action.data()
            if language_code:
                # 使用QTimer延迟执行，避免信号处理中的阻塞
                QTimer.singleShot(50, lambda: self.on_language_changed(language_code))
            else:
                self.log_manager.warning("菜单动作缺少语言代码数据")

        except Exception as e:
            self.log_manager.error(f"处理语言动作组信号失败: {str(e)}")

    def _save_language_config_async(self, language_code: str):
        """废弃的方法，保留以防兼容性问题"""
        self.log_manager.warning("使用了废弃的_save_language_config_async方法")
        if hasattr(self, 'language_switch_manager'):
            self.language_switch_manager.switch_language(language_code)
        else:
            self._fallback_language_change(language_code)

    def _update_critical_ui_text(self):
        """废弃的方法，保留以防兼容性问题"""
        self.log_manager.warning("使用了废弃的_update_critical_ui_text方法")
        if hasattr(self, 'i18n_manager'):
            current_language = self.i18n_manager.get_current_language()
            self._update_minimal_ui_text(current_language)

    def show_plugin_manager(self):
        """显示插件管理器对话框"""
        try:
            self.log_manager.info("请求显示插件管理器")
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            dialog = PluginManagerDialog(self.plugin_manager, self)
            dialog.exec_()
        except Exception as e:
            self.log_manager.error(f"显示插件管理器失败: {str(e)}")
            self.show_message("错误", f"显示插件管理器失败: {str(e)}", "error")

    def show_language_settings(self):
        """显示语言设置对话框"""
        try:
            self.log_manager.info("请求显示语言设置对话框")
            from gui.dialogs.language_settings_dialog import LanguageSettingsDialog
            dialog = LanguageSettingsDialog(self.i18n_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_language = dialog.get_selected_language()
                if selected_language:
                    self.language_changed.emit(selected_language)
        except Exception as e:
            self.log_manager.error(f"显示语言设置失败: {str(e)}")
            self.show_message("错误", f"显示语言设置失败: {str(e)}", "error")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            self.log_manager.info("正在关闭主窗口...")

            # 清理语言切换管理器
            if hasattr(self, 'language_switch_manager'):
                self.language_switch_manager.cleanup()
                self.log_manager.debug("语言切换管理器已清理")

            # 清理其他资源
            if hasattr(self, 'plugin_manager'):
                self.plugin_manager.cleanup()

            if hasattr(self, 'performance_manager'):
                self.performance_manager.cleanup()

            if hasattr(self, 'thread_pool'):
                self.thread_pool.waitForDone(3000)

            # 清理全局语言切换管理器
            from utils.language_manager import cleanup_language_switch_manager
            cleanup_language_switch_manager()

            self.log_manager.info("主窗口关闭完成")
            event.accept()

        except Exception as e:
            self.log_manager.error(f"关闭主窗口时出错: {str(e)}")
            event.accept()  # 即使出错也要关闭窗口


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

        # Initialize base logger first
        print("初始化基础日志管理器")
        base_logger = BaseLogManager()
        print("初始化基础日志管理器完成")

        # Initialize log manager with the correct LoggingConfig
        print("初始化日志管理器")
        logger = LogManager(config_manager.logging)
        exception_handler.set_logger(logger)
        print("初始化日志管理器完成")

        # Create main window
        logger.info("创建主窗口")
        window = TradingGUI()
        logger.info("创建主窗口完成")

        # Install global exception handler
        global_handler = GlobalExceptionHandler(window)
        sys.excepthook = global_handler.handle_exception

        # Show window
        window.show()
        logger.info("显示主窗口完成")

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
