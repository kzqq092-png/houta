"""
交易GUI核心初始化模块

包含交易系统GUI的核心初始化逻辑和管理器设置
"""

import os
import traceback
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThreadPool, QStringListModel
from hikyuu import StockManager
from concurrent.futures import ThreadPoolExecutor

from core.plugin_manager import PluginManager
from utils.cache import Cache
from core.data_manager import data_manager
from utils.theme import get_theme_manager
from core.strategy import (
    initialize_strategy_system, list_available_strategies
)


class TradingGUICore:
    """交易GUI核心初始化类"""

    def __init__(self, parent_gui):
        """初始化核心组件

        Args:
            parent_gui: 父GUI实例
        """
        self.parent_gui = parent_gui
        self.log_manager = None

    def setup_application_style(self):
        """设置应用程序全局样式"""
        try:
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
        except Exception as e:
            print(f"设置应用程序样式失败: {str(e)}")

    def initialize_hikyuu(self):
        """初始化HIkyuu框架"""
        try:
            self.parent_gui.sm = StockManager.instance()
            if self.log_manager:
                self.log_manager.info("HIkyuu StockManager初始化完成")
        except Exception as e:
            error_msg = f"HIkyuu初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            raise

    def initialize_managers(self):
        """初始化所有管理器"""
        try:
            # 使用统一的管理器工厂
            from utils.manager_factory import get_config_manager, get_log_manager, get_industry_manager

            # 初始化配置管理器
            self.parent_gui.config_manager = get_config_manager()

            # 从配置中获取日志配置
            logging_config = self.parent_gui.config_manager.logging

            # 初始化日志管理器
            self.parent_gui.log_manager = get_log_manager(logging_config)
            self.log_manager = self.parent_gui.log_manager
            self.log_manager.info("TradingGUI核心初始化开始")

            # 初始化数据管理器
            self.parent_gui.data_manager = data_manager
            self.log_manager.info("数据管理器初始化完成")

            # 初始化缓存管理器
            self.parent_gui.cache_manager = Cache()

            # 初始化行业管理器
            self.parent_gui.industry_manager = get_industry_manager(self.log_manager)
            self.parent_gui.industry_manager.industry_updated.connect(
                self.parent_gui._on_industry_data_updated)
            self.parent_gui.industry_manager.update_error.connect(
                self.parent_gui.handle_error)
            self.log_manager.info("行业管理器初始化完成")

            # 启动行业数据更新
            self.parent_gui.industry_manager.update_industry_data()

            # 初始化主题管理器
            self.parent_gui.theme_manager = get_theme_manager(self.parent_gui.config_manager)

            # 启动时优先从主库读取上次主题
            theme_cfg = self.parent_gui.config_manager.get('theme', {})
            theme_name = theme_cfg.get('theme_name')
            if theme_name:
                self.parent_gui.theme_manager.set_theme(theme_name)

        except Exception as e:
            error_msg = f"管理器初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            raise

    def initialize_threading(self):
        """初始化线程池"""
        try:
            self.parent_gui.thread_pool = QThreadPool()
            self.parent_gui.thread_pool.setMaxThreadCount(os.cpu_count() * 3)

            if self.log_manager:
                self.log_manager.info("线程池初始化完成")
        except Exception as e:
            error_msg = f"线程池初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            raise

    def initialize_models(self):
        """初始化数据模型"""
        try:
            # 初始化股票列表模型
            self.parent_gui.stock_list_model = QStringListModel()

            if self.log_manager:
                self.log_manager.info("数据模型初始化完成")
        except Exception as e:
            error_msg = f"数据模型初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            raise

    def initialize_plugins(self):
        """初始化插件管理器"""
        try:
            self.parent_gui.plugin_manager = PluginManager()
            self.parent_gui.plugin_manager.load_plugins()

            if self.log_manager:
                self.log_manager.info("插件管理器初始化并加载插件完成")
        except Exception as e:
            error_msg = f"插件管理器初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            # 插件初始化失败不应该阻止系统启动

    def initialize_strategy_system(self):
        """初始化策略管理系统"""
        try:
            if self.log_manager:
                self.log_manager.info("初始化策略管理系统...")

            strategy_config = self.parent_gui.config_manager.get('strategy_system', {})
            self.parent_gui.strategy_managers = initialize_strategy_system(strategy_config)

            # 获取策略管理器实例
            self.parent_gui.strategy_registry = self.parent_gui.strategy_managers['registry']
            self.parent_gui.strategy_engine = self.parent_gui.strategy_managers['engine']
            self.parent_gui.strategy_factory = self.parent_gui.strategy_managers['factory']
            self.parent_gui.strategy_database = self.parent_gui.strategy_managers['database']

            # 加载可用策略列表
            self.parent_gui.available_strategies = list_available_strategies()

            if self.log_manager:
                self.log_manager.info(f"策略管理系统初始化完成，加载了 {len(self.parent_gui.available_strategies)} 个策略")

        except Exception as e:
            error_msg = f"策略管理系统初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())

            # 使用默认策略列表作为备用
            self.parent_gui.available_strategies = [
                "均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"
            ]

    def initialize_market_industry_mapping(self):
        """初始化市场和行业映射"""
        try:
            self.parent_gui.init_market_industry_mapping()

            if self.log_manager:
                self.log_manager.info("市场和行业映射初始化完成")
        except Exception as e:
            error_msg = f"市场和行业映射初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            # 映射初始化失败不应该阻止系统启动

    def complete_initialization(self):
        """完成初始化过程"""
        try:
            # 设置拖拽支持
            self.parent_gui.setAcceptDrops(True)

            # 连接信号
            self.parent_gui.connect_signals()

            # 预加载数据
            self.parent_gui.preload_data()

            # 标记初始化完成
            self.parent_gui._is_initializing = False

            # 刷新股票列表
            self.parent_gui.filter_stock_list()

            if self.log_manager:
                self.log_manager.info("TradingGUI核心初始化完成")

        except Exception as e:
            error_msg = f"完成初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            raise

    def initialize_all(self):
        """执行完整的初始化流程"""
        try:
            # 设置应用程序样式
            self.setup_application_style()

            # 初始化HIkyuu框架
            self.initialize_hikyuu()

            # 初始化所有管理器
            self.initialize_managers()

            # 初始化线程池
            self.initialize_threading()

            # 初始化数据模型
            self.initialize_models()

            # 初始化市场和行业映射
            self.initialize_market_industry_mapping()

            # 初始化插件管理器
            self.initialize_plugins()

            # 初始化策略管理系统
            self.initialize_strategy_system()

            return True

        except Exception as e:
            error_msg = f"核心初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            else:
                print(error_msg)
                print(traceback.format_exc())
            return False
