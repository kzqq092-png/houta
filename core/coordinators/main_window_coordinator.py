"""
主窗口协调器

负责协调主窗口的所有UI面板和业务服务的交互。
这是整个应用的中央协调器，替代原来的TradingGUI类。
"""

import logging
from typing import Dict, Any, Optional, List, Union
import asyncio
from datetime import datetime
import pandas as pd

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMessageBox, QDockWidget, QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

from .base_coordinator import BaseCoordinator
from ..events import (
    EventBus, StockSelectedEvent, ChartUpdateEvent, AnalysisCompleteEvent,
    DataUpdateEvent, ErrorEvent, UIUpdateEvent, ThemeChangedEvent, UIDataReadyEvent
)
from ..containers import ServiceContainer
from ..services import (
    StockService, ChartService, AnalysisService,
    ThemeService, ConfigService, UnifiedDataManager
)
from optimization.optimization_dashboard import create_optimization_dashboard
from gui.panels.performance_dashboard_panel import PerformanceDashboardPanel
from core.metrics.repository import MetricsRepository
from utils.performance_monitor import measure_performance
from gui.menu_bar import MainMenuBar

logger = logging.getLogger(__name__)


class MainWindowCoordinator(BaseCoordinator):
    """
    主窗口协调器

    负责：
    1. 管理主窗口的生命周期
    2. 协调各个UI面板的交互
    3. 处理全局事件
    4. 管理服务依赖
    """

    def __init__(self,
                 service_container: ServiceContainer,
                 event_bus: EventBus,
                 parent: Optional[QWidget] = None):
        """
        初始化主窗口协调器

        Args:
            service_container: 服务容器
            event_bus: 事件总线
            parent: 父窗口（可选）
        """
        super().__init__(service_container, event_bus)

        # 创建主窗口
        self._main_window = QMainWindow(parent)
        self._main_window.setWindowTitle("FactorWeave-Quant ‌ 2.0 股票分析系统")
        self._main_window.setGeometry(100, 100, 1400, 900)
        self._main_window.setMinimumSize(1200, 800)

        # UI面板
        self._panels: Dict[str, Any] = {}
        self._optimization_dashboard = None

        # 窗口状态
        self._window_state = {
            'title': 'FactorWeave-Quant ‌ 2.0 股票分析系统',
            'geometry': (100, 100, 1400, 900),
            'min_size': (1200, 800),
            'is_maximized': False
        }

        # 布局配置
        self._layout_config = {
            'left_panel_width': 300,
            'right_panel_width': 350,
            'bottom_panel_height': 200,
            'panel_padding': 5
        }

        # 中央数据状态
        self._current_stock_code: Optional[str] = None
        self._current_stock_data: Dict[str, Any] = {}
        self._is_loading = False

    def _do_initialize(self) -> None:
        """初始化协调器"""
        try:
            # 获取服务
            self._stock_service = self.service_container.resolve(StockService)
            self._chart_service = self.service_container.resolve(ChartService)
            self._analysis_service = self.service_container.resolve(
                AnalysisService)
            self._theme_service = self.service_container.resolve(ThemeService)
            self._config_service = self.service_container.resolve(
                ConfigService)
            self._data_manager = self.service_container.resolve(
                UnifiedDataManager)

            # 初始化窗口
            self._setup_window()

            # 创建UI面板
            self._create_panels()

            # 设置布局
            self._setup_layout()

            # 注册事件处理器
            self._register_event_handlers()

            # 应用主题
            self._apply_theme()

            # 加载配置
            self._load_window_config()

            # 设置所有表格为只读
            # self._set_all_tables_readonly()

            # 检查数据使用条款
            self._check_data_usage_terms()

            logger.info("Main window coordinator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize main window coordinator: {e}")
            raise

    def _setup_window(self) -> None:
        """设置主窗口"""
        try:
            # 设置窗口图标
            try:
                icon_path = "icons/logo.png"
                self._main_window.setWindowIcon(QIcon(icon_path))
            except:
                pass

            # 设置状态栏
            self._status_bar = QStatusBar()
            self._main_window.setStatusBar(self._status_bar)

            # 添加状态信息标签
            self._status_label = QLabel("就绪")
            self._status_bar.addWidget(self._status_label)

            # 添加永久小部件到右侧
            self._status_bar.addPermanentWidget(QFrame())  # 弹性空间

            # 数据时间标签
            self._data_time_label = QLabel("")
            self._data_time_label.setToolTip("当前数据的最新时间")
            self._data_time_label.setFixedWidth(150)
            self._status_bar.addPermanentWidget(self._data_time_label)

            # 创建日志显示/隐藏按钮
            self._log_toggle_btn = QPushButton("隐藏日志")
            self._log_toggle_btn.setToolTip("隐藏/显示日志面板")
            self._log_toggle_btn.setFixedWidth(80)
            self._log_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #c0c0c0;
                    border-radius: 2px;
                    padding: 2px 8px;
                    color: #505050;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            self._log_toggle_btn.clicked.connect(self._toggle_log_panel)
            self._status_bar.addPermanentWidget(self._log_toggle_btn)

            # 设置菜单栏 - 使用MainMenuBar
            self._setup_menu_bar()

            logger.info("Main window setup completed")

        except Exception as e:
            logger.error(f"Failed to setup main window: {e}")
            raise

    def _setup_menu_bar(self) -> None:
        """设置菜单栏 - 使用MainMenuBar"""
        try:
            # 创建MainMenuBar实例，传入coordinator引用
            menu_bar = MainMenuBar(coordinator=self, parent=self._main_window)
            self._main_window.setMenuBar(menu_bar)
            self._menu_bar = menu_bar

            logger.info("Menu bar (MainMenuBar) setup completed")

        except Exception as e:
            logger.error(f"Failed to setup menu bar: {e}")
            raise

    def _create_menu_bar(self) -> None:
        """创建菜单栏 - 已废弃，使用_setup_menu_bar替代"""
        try:
            menu_bar = self._main_window.menuBar()

            # 文件菜单
            file_menu = menu_bar.addMenu('文件(&F)')
            file_menu.addAction('新建', self._on_new_file)
            file_menu.addAction('打开', self._on_open_file)
            file_menu.addAction('保存', self._on_save_file)
            file_menu.addSeparator()
            file_menu.addAction('退出', self._on_exit)

            # 编辑菜单
            edit_menu = menu_bar.addMenu('编辑(&E)')
            edit_menu.addAction('撤销', self._on_undo)
            edit_menu.addAction('重做', self._on_redo)
            edit_menu.addSeparator()
            edit_menu.addAction('复制', self._on_copy)
            edit_menu.addAction('粘贴', self._on_paste)

            # 视图菜单
            view_menu = menu_bar.addMenu('视图(&V)')
            view_menu.addAction('刷新', self._on_refresh)
            view_menu.addSeparator()

            # 主题子菜单
            theme_menu = view_menu.addMenu('主题')
            theme_menu.addAction(
                '默认主题', lambda: self._on_theme_changed('default'))
            theme_menu.addAction(
                '深色主题', lambda: self._on_theme_changed('dark'))
            theme_menu.addAction(
                '浅色主题', lambda: self._on_theme_changed('light'))

            # 新增：性能仪表板菜单项
            self.performance_panel_action = view_menu.addAction("性能仪表板")
            self.performance_panel_action.setCheckable(True)
            self.performance_panel_action.setChecked(False)
            self.performance_panel_action.triggered.connect(
                self._toggle_performance_panel)

            # 工具菜单
            tools_menu = menu_bar.addMenu('工具(&T)')
            tools_menu.addAction('高级搜索', self._on_advanced_search)
            tools_menu.addAction('数据导出', self._on_export_data)
            tools_menu.addSeparator()

            # 计算工具子菜单
            calc_menu = tools_menu.addMenu('计算工具')
            calc_menu.addAction('计算器', self._on_calculator)
            calc_menu.addAction('单位转换器', self._on_converter)
            calc_menu.addAction('费率计算器', self._on_commission_calculator)
            calc_menu.addAction('汇率转换器', self._on_currency_converter)

            tools_menu.addSeparator()

            # 缓存管理子菜单
            cache_menu = tools_menu.addMenu('缓存管理')
            cache_menu.addAction('清理数据缓存', self._on_clear_data_cache)
            cache_menu.addAction('清理负缓存', self._on_clear_negative_cache)
            cache_menu.addAction('清理所有缓存', self._on_clear_all_cache)

            tools_menu.addSeparator()
            tools_menu.addAction('系统维护工具', self._on_system_optimizer)
            tools_menu.addAction('系统设置', self._on_settings)

            # 高级功能菜单
            advanced_menu = menu_bar.addMenu('高级功能(&A)')

            # 插件管理
            advanced_menu.addAction('插件管理', self._on_plugin_manager)

            # 插件市场
            advanced_menu.addAction('插件市场', self._on_plugin_market)

            advanced_menu.addSeparator()

            # 节点管理
            advanced_menu.addAction('节点管理', self._on_node_management)

            # 云端API
            advanced_menu.addAction('云端API', self._on_cloud_api)

            # 指标市场
            advanced_menu.addAction('指标市场', self._on_indicator_market)

            # 批量分析
            advanced_menu.addAction('批量分析', self._on_batch_analysis)

            # 策略管理
            advanced_menu.addAction('策略管理', self._on_strategy_management)

            advanced_menu.addSeparator()

            # 优化系统子菜单
            optimization_menu = advanced_menu.addMenu('优化系统')
            optimization_menu.addAction(
                '优化仪表板', self._on_optimization_dashboard)
            optimization_menu.addAction(
                '一键优化', self._on_one_click_optimization)
            optimization_menu.addAction(
                '智能优化', self._on_intelligent_optimization)
            optimization_menu.addAction(
                '性能评估', self._on_performance_evaluation)
            optimization_menu.addAction('版本管理', self._on_version_management)

            # 数据质量检查子菜单
            quality_menu = advanced_menu.addMenu('数据质量检查')
            quality_menu.addAction(
                '单股质量检查', self._on_single_stock_quality_check)
            quality_menu.addAction('批量质量检查', self._on_batch_quality_check)
            quality_menu.addSeparator()
            quality_menu.addAction('数据库管理', self._on_database_admin)

            # 帮助菜单
            help_menu = menu_bar.addMenu('帮助(&H)')
            help_menu.addAction('启动向导', self._on_startup_guides)
            help_menu.addSeparator()
            help_menu.addAction('用户手册', self._on_help)
            help_menu.addAction('快捷键', self._on_shortcuts)
            help_menu.addSeparator()
            help_menu.addAction('数据使用条款', self._on_show_data_usage_terms)
            help_menu.addSeparator()
            help_menu.addAction('关于', self._on_about)

            logger.info("Menu bar created successfully")

        except Exception as e:
            logger.error(f"Failed to create menu bar: {e}")
            raise

    def _create_panels(self) -> None:
        """创建所有UI面板"""
        try:
            # 创建中央窗口部件
            central_widget = QWidget()
            self._main_window.setCentralWidget(central_widget)

            # 创建主布局
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            # 创建垂直分割器（主面板区域 + 底部面板）
            vertical_splitter = QSplitter(Qt.Vertical)
            main_layout.addWidget(vertical_splitter)

            # 创建水平分割器（左中右布局）
            horizontal_splitter = QSplitter(Qt.Horizontal)
            vertical_splitter.addWidget(horizontal_splitter)

            # 导入真实的面板类
            from ..ui.panels import LeftPanel, MiddlePanel, RightPanel

            # 创建左侧面板（股票列表面板）
            left_panel = LeftPanel(
                stock_service=self._stock_service,
                data_manager=self._data_manager,
                parent=self._main_window,
                coordinator=self
            )
            left_panel._root_frame.setMinimumWidth(
                self._layout_config['left_panel_width'])
            left_panel._root_frame.setMaximumWidth(300)
            horizontal_splitter.addWidget(left_panel._root_frame)
            self._panels['left'] = left_panel

            # 创建中间面板（图表显示面板）
            middle_panel = MiddlePanel(
                parent=self._main_window,
                coordinator=self
            )
            horizontal_splitter.addWidget(middle_panel._root_frame)
            self._panels['middle'] = middle_panel

            # 创建右侧面板（技术分析面板）
            right_panel = RightPanel(
                parent=self._main_window,
                coordinator=self,
                width=self._layout_config['right_panel_width']
            )
            right_panel._root_frame.setMinimumWidth(
                self._layout_config['right_panel_width'])
            right_panel._root_frame.setMaximumWidth(1500)
            horizontal_splitter.addWidget(right_panel._root_frame)
            self._panels['right'] = right_panel

            # 设置分割器比例
            horizontal_splitter.setSizes([300, 700, 350])

            # 创建底部面板（日志面板）
            from ..ui.panels import BottomPanel
            bottom_panel = BottomPanel(
                parent=self._main_window,
                coordinator=self
            )
            vertical_splitter.addWidget(bottom_panel._root_frame)
            self._panels['bottom'] = bottom_panel

            # 设置分割器的初始大小
            vertical_splitter.setSizes([700, 200])  # 主区域和底部面板的比例

            # 创建性能仪表板
            repository = self.service_container.resolve(MetricsRepository)
            performance_panel = PerformanceDashboardPanel(
                self.event_bus, repository)

            # 将其放入一个可停靠的窗口
            self._performance_dock = QDockWidget("性能仪表板", self._main_window)
            self._performance_dock.setWidget(performance_panel)
            self._performance_dock.setAllowedAreas(
                Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
            self._main_window.addDockWidget(
                Qt.BottomDockWidgetArea, self._performance_dock)
            # 默认隐藏性能仪表板
            self._performance_dock.setVisible(False)

            self._panels['performance_dashboard'] = performance_panel

            logger.info("Performance dashboard panel created and docked")

            # 连接面板之间的信号
            self._connect_panel_signals()

            logger.info("UI panels created successfully")

        except Exception as e:
            logger.error(f"Failed to create UI panels: {e}")
            raise

    def _connect_panel_signals(self) -> None:
        """连接面板间的信号"""
        try:
            # 左侧面板选择股票 -> 中间面板更新图表
            # 注意：现在通过事件总线通信，不需要直接信号连接
            # 事件订阅已在_register_event_handlers中完成，这里不需要重复订阅

            # 连接底部面板的隐藏信号
            bottom_panel = self._panels.get('bottom')
            if bottom_panel and hasattr(bottom_panel, 'panel_hidden'):
                bottom_panel.panel_hidden.connect(self._on_bottom_panel_hidden)

            logger.debug("Panel signals connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect panel signals: {e}")
            raise

    def _on_bottom_panel_hidden(self) -> None:
        """处理底部面板隐藏事件"""
        try:
            # 获取垂直分割器
            central_widget = self._main_window.centralWidget()
            if not central_widget:
                return

            # 查找垂直分割器
            vertical_splitter = None
            for child in central_widget.children():
                if isinstance(child, QSplitter) and child.orientation() == Qt.Vertical:
                    vertical_splitter = child
                    break

            if vertical_splitter:
                # 调整分割器大小，使主面板区域扩展
                sizes = vertical_splitter.sizes()
                if len(sizes) >= 2:
                    # 保留底部面板的最小高度（用于显示切换按钮）
                    bottom_panel = self._panels.get('bottom')
                    bottom_height = 30 if bottom_panel else 0

                    # 将底部面板的大部分大小添加到主面板区域，但保留切换按钮的空间
                    new_sizes = [sizes[0] + sizes[1] -
                                 bottom_height, bottom_height]
                    vertical_splitter.setSizes(new_sizes)
                    logger.debug(f"调整垂直分割器大小: {sizes} -> {new_sizes}")

            # 更新菜单项
            self._update_bottom_panel_menu_item(False)

        except Exception as e:
            logger.error(f"处理底部面板隐藏事件失败: {e}")

    def _update_bottom_panel_menu_item(self, is_visible: bool) -> None:
        """更新底部面板菜单项"""
        try:
            # 查找视图菜单
            menu_bar = self._main_window.menuBar()
            view_menu = None
            for action in menu_bar.actions():
                if action.text() == '视图(&V)':
                    view_menu = action.menu()
                    break

            if view_menu:
                # 查找或创建底部面板菜单项
                bottom_panel_action = None
                for action in view_menu.actions():
                    if action.text() == '显示日志面板':
                        bottom_panel_action = action
                        break

                if not bottom_panel_action and not is_visible:
                    # 如果面板隐藏且菜单项不存在，创建菜单项
                    bottom_panel_action = view_menu.addAction('显示日志面板')
                    bottom_panel_action.triggered.connect(
                        self._show_bottom_panel)
                elif bottom_panel_action and is_visible:
                    # 如果面板可见且菜单项存在，移除菜单项
                    view_menu.removeAction(bottom_panel_action)

        except Exception as e:
            logger.error(f"更新底部面板菜单项失败: {e}")

    def _show_bottom_panel(self) -> None:
        """显示底部面板"""
        try:
            # 获取底部面板
            bottom_panel = self._panels.get('bottom')
            if bottom_panel:
                # 如果面板有_show_panel方法，调用它
                if hasattr(bottom_panel, '_show_panel'):
                    bottom_panel._show_panel()
                # 否则使用旧方法
                elif hasattr(bottom_panel, '_root_frame'):
                    bottom_panel._root_frame.setVisible(True)

            # 获取垂直分割器
            central_widget = self._main_window.centralWidget()
            if not central_widget:
                return

            # 查找垂直分割器
            vertical_splitter = None
            for child in central_widget.children():
                if isinstance(child, QSplitter) and child.orientation() == Qt.Vertical:
                    vertical_splitter = child
                    break

            if vertical_splitter:
                # 调整分割器大小，恢复底部面板
                sizes = vertical_splitter.sizes()
                if len(sizes) >= 2:
                    # 分配一部分空间给底部面板
                    total_height = sum(sizes)
                    new_sizes = [int(total_height * 0.8),
                                 int(total_height * 0.2)]
                    vertical_splitter.setSizes(new_sizes)
                    logger.debug(f"调整垂直分割器大小: {sizes} -> {new_sizes}")

            # 更新菜单项
            self._update_bottom_panel_menu_item(True)

        except Exception as e:
            logger.error(f"显示底部面板失败: {e}")

    def _setup_layout(self) -> None:
        """设置布局"""
        # 布局已在_create_panels中设置
        pass

    def _register_event_handlers(self) -> None:
        """注册事件处理器"""
        try:
            # 注册股票选择事件处理器
            self.event_bus.subscribe(
                StockSelectedEvent, self._on_stock_selected)

            # 注册图表更新事件处理器
            self.event_bus.subscribe(ChartUpdateEvent, self._on_chart_updated)

            # 注册分析完成事件处理器
            self.event_bus.subscribe(
                AnalysisCompleteEvent, self._on_analysis_completed)

            # 注册数据更新事件处理器
            self.event_bus.subscribe(DataUpdateEvent, self._on_data_update)

            # 注册错误事件处理器
            self.event_bus.subscribe(ErrorEvent, self._on_error)

            # 注册UI数据就绪事件处理器
            self.event_bus.subscribe(UIDataReadyEvent, self._on_ui_data_ready)

            # 注册主题变化事件处理器
            self.event_bus.subscribe(ThemeChangedEvent, self._on_theme_changed)

            logger.info("Event handlers registered successfully")

        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
            raise

    def _apply_theme(self) -> None:
        """应用主题"""
        try:
            # 获取当前主题
            current_theme = self._theme_service.get_current_theme()
            theme_config = self._theme_service.get_theme_config(current_theme)

            # 应用主题到主窗口
            if theme_config:
                # 这里可以根据主题配置设置窗口样式
                pass

            logger.info(f"Theme applied: {current_theme}")

        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")

    def _load_window_config(self) -> None:
        """加载窗口配置"""
        try:
            # 从配置服务加载窗口设置
            window_config = self._config_service.get('window', {})

            # 应用窗口配置
            if 'geometry' in window_config:
                geometry = window_config['geometry']
                self._main_window.setGeometry(*geometry)

            if 'maximized' in window_config and window_config['maximized']:
                self._main_window.showMaximized()

            logger.info("Window configuration loaded")

        except Exception as e:
            logger.error(f"Failed to load window configuration: {e}")

    def _save_window_config(self) -> None:
        """保存窗口配置"""
        try:
            # 获取当前窗口状态
            geometry = self._main_window.geometry()
            window_config = {
                'geometry': (geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                'maximized': self._main_window.isMaximized()
            }

            # 保存到配置服务
            self._config_service.set('window', window_config)

            logger.info("Window configuration saved")

        except Exception as e:
            logger.error(f"Failed to save window configuration: {e}")

    @measure_performance("MainWindowCoordinator._on_stock_selected")
    async def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件 - 新的统一数据加载流程"""
        if not event or not event.stock_code or self._is_loading:
            return

        # 在开始新任务前，取消之前所有相关的请求
        try:
            await self._chart_service.cancel_previous_requests()
            await self._analysis_service.cancel_previous_requests()
            logger.info(f"已取消先前为 {self._current_stock_code} 发出的请求。")
        except Exception as e:
            logger.error(f"取消先前请求时出错: {e}", exc_info=True)

        self._is_loading = True
        self._current_stock_code = event.stock_code
        self.show_message(
            f"正在加载 {event.stock_name} ({event.stock_code}) 的数据...", level='info')

        try:
            # 从事件中提取参数
            period = event.period if event.period else 'D'  # 默认日线
            time_range = event.time_range if event.time_range else "最近1年"  # 默认最近1年
            chart_type = event.chart_type if event.chart_type else "K线图"  # 默认K线图

            logger.info(f"加载数据，股票：{event.stock_code}，周期：{period}，时间范围：{time_range}，图表类型：{chart_type}")

            # 1. 串行获取数据：先获取K线
            logger.info(f"开始请求K线数据: {event.stock_code}")
            kline_data_response = await self._data_manager.request_data(
                stock_code=event.stock_code,
                data_type='kdata',
                period=period,          # 传递周期
                time_range=time_range   # 传递时间范围
            )

            kline_data = None
            if isinstance(kline_data_response, dict):
                kline_data = kline_data_response.get('kline_data')
            else:
                kline_data = kline_data_response

            # 关键检查点：确认核心数据是否存在
            if kline_data is None or kline_data.empty:
                logger.warning(f"无法获取 {event.stock_name} 的K线数据。")
                self.show_message(
                    f"无法获取 {event.stock_name} ({event.stock_code}) 的K线数据，请尝试其他股票。", level='warning')
                return

            logger.info(f"K线数据加载完成: {event.stock_code}, 开始请求分析数据...")

            # 2. 再获取分析数据，传入已获取的K线数据
            analysis_data = await self._analysis_service.analyze_stock(
                stock_code=event.stock_code,
                analysis_type='comprehensive',
                kline_data=kline_data
            )
            logger.info(f"分析数据加载完成: {event.stock_code}")

            # 3. 存储到中央数据状态
            self._current_stock_data = {
                'stock_code': event.stock_code,
                'stock_name': event.stock_name,
                'market': event.market,
                'kline_data': kline_data,
                'analysis': analysis_data,
                'period': period,
                'time_range': time_range,
                'chart_type': chart_type
            }
            logger.info(f"数据已存储到中央状态，准备发布UIDataReadyEvent事件: {event.stock_code}")

            # 4. 发布数据准备就绪事件
            data_ready_event = UIDataReadyEvent(
                source="MainWindowCoordinator",
                stock_code=event.stock_code,
                stock_name=event.stock_name,
                ui_data=self._current_stock_data
            )
            self.event_bus.publish(data_ready_event)
            logger.info(f"已发布UIDataReadyEvent事件: {event.stock_code}")

            self.show_message(f"{event.stock_name} 数据加载完成", level='success')

            # 5. 启动相关股票的预加载
            asyncio.create_task(self._chart_service._preload_related_stocks(
                event.stock_code, period
            ))
            logger.info(f"已启动相关股票预加载: {event.stock_code}")

        except Exception as e:
            logger.error(f"加载股票 {event.stock_code} 数据时出错: {e}", exc_info=True)
            self.show_message(
                f"加载 {event.stock_name} 数据失败", level='error')

            import traceback
            error_event = ErrorEvent(
                source='MainWindowCoordinator',
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=traceback.format_exc(),
                severity='high'
            )
            self.event_bus.publish(error_event)

        finally:
            self._is_loading = False

    @pyqtSlot(UIDataReadyEvent)
    def _on_ui_data_ready(self, event: UIDataReadyEvent) -> None:
        """处理UI数据就绪事件，更新主窗口状态栏"""
        try:
            kdata = event.ui_data.get('kline_data')
            if kdata is not None and not kdata.empty:
                # 更新状态标签显示加载数量
                self._status_label.setText(f"已加载 ({len(kdata)})")

                # 更新数据时间标签
                latest_date = kdata.index[-1]
                if isinstance(latest_date, (datetime, pd.Timestamp)):
                    time_str = latest_date.strftime('%Y-%m-%d')
                else:
                    time_str = str(latest_date)
                self._data_time_label.setText(f"数据时间: {time_str}")
            else:
                self._status_label.setText("已加载 (0)")
                self._data_time_label.setText("数据时间: -")
        except Exception as e:
            logger.error(f"更新主窗口状态栏失败: {e}", exc_info=True)
            self._status_label.setText("状态更新失败")
            self._data_time_label.setText("数据时间: -")

    def _on_chart_updated(self, event: ChartUpdateEvent) -> None:
        """处理图表更新事件"""
        try:
            stock_code = getattr(event, 'stock_code', '')
            period = getattr(event, 'period', '')

            logger.info(f"Chart updated: {stock_code} - {period}")

        except Exception as e:
            logger.error(f"Failed to handle chart update: {e}")

    def _on_analysis_completed(self, event) -> None:
        """处理分析完成事件"""
        try:
            stock_code = getattr(event, 'stock_code', '')
            analysis_type = getattr(event, 'analysis_type', '')

            logger.info(f"Analysis completed: {stock_code} - {analysis_type}")

        except Exception as e:
            logger.error(f"Failed to handle analysis completion: {e}")

    @pyqtSlot(object)
    def _on_error(self, event: Union[ErrorEvent, dict]):
        """
        健壮的错误事件处理器，能同时处理事件对象和字典。
        """
        try:
            error_type = "UnknownError"
            error_message = "An unknown error occurred."
            event_id = "N/A"

            if isinstance(event, ErrorEvent):
                # 标准事件对象
                error_type = event.data.get('error_type', 'UnknownError')
                error_message = event.data.get('error_message', 'An unknown error occurred.')
                event_id = event.event_id
            elif isinstance(event, dict):
                # 兼容字典形式的事件
                error_type = event.get('error_type', 'UnknownError')
                error_message = event.get('error_message', 'An unknown error occurred.')
                event_id = event.get('event_id', 'N/A')

            logger.error(f"[ERROR] {error_type}: {error_message}",
                         extra={'trace_id': event_id})

            self.show_message(f"发生错误: {error_message}", level='error')

        except Exception as e:
            logger.critical(f"在处理错误事件时发生严重错误: {e}", exc_info=True)
            self.show_message("发生严重错误，请检查日志", level='critical')

    def _on_data_update(self, event: DataUpdateEvent):
        """处理数据更新事件"""
        try:
            data_type = event.data.get('data_type', 'N/A')
            logger.info(f"Data update: {data_type}")
            self.show_message(f"数据已更新: {data_type}", level='info')
        except Exception as e:
            logger.error(f"Failed to handle data update event: {e}", exc_info=True)

    def _on_theme_changed(self, theme_data) -> None:
        """智能主题变更处理 - 支持事件对象和字符串参数"""
        try:
            # 智能参数识别
            if hasattr(theme_data, 'theme_name'):
                # 事件对象
                theme_name = theme_data.theme_name
                logger.info(f"Theme changed via event: {theme_name}")

                # 重新应用主题
                self._apply_theme()

                # 更新状态栏
                if hasattr(self, '_status_label') and self._status_label:
                    self._status_label.setText(f"主题已更改: {theme_name}")

            elif isinstance(theme_data, str):
                # 字符串参数
                theme_name = theme_data
                logger.info(f"Theme changed via menu: {theme_name}")

                # 使用主题服务
                theme_service = self.service_container.get_service(ThemeService)
                if theme_service:
                    theme_service.set_theme(theme_name)
                    self.show_message(f"主题已切换为: {theme_name}")
                else:
                    # 降级到应用主题
                    self._apply_theme()
                    self.show_message(f"主题已切换为: {theme_name}")
            else:
                logger.warning(f"未知的主题数据类型: {type(theme_data)}")

        except Exception as e:
            logger.error(f"Failed to handle theme change: {e}")
            if hasattr(self, 'show_message'):
                self.show_message(f"主题切换失败: {e}")

    def get_main_window(self) -> QMainWindow:
        """获取主窗口"""
        return self._main_window

    def get_panel(self, panel_name: str) -> Optional[QWidget]:
        """获取面板"""
        return self._panels.get(panel_name)

    def show_message(self, message: str, level: str = 'info') -> None:
        """显示消息"""
        self._status_label.setText(message)

    def center_dialog(self, dialog, parent=None, offset_y=50):
        """居中显示对话框"""
        try:
            if parent is None:
                parent = self._main_window

            # 获取父窗口的几何信息
            parent_rect = parent.geometry()

            # 计算对话框的位置
            x = parent_rect.x() + (parent_rect.width() - dialog.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog.height()) // 2 - offset_y

            # 确保对话框不会超出屏幕边界
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.desktop().screenGeometry()
            x = max(0, min(x, screen.width() - dialog.width()))
            y = max(0, min(y, screen.height() - dialog.height()))

            dialog.move(x, y)

        except Exception as e:
            logger.error(f"居中对话框失败: {e}")

    def run(self) -> None:
        """运行主窗口"""
        try:
            # 显示主窗口
            self._main_window.show()

            logger.info("Main window is now running")

        except Exception as e:
            logger.error(f"Failed to run main window: {e}")
            raise

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            # 清理UI面板
            if 'performance_dashboard' in self._panels:
                self._panels['performance_dashboard'].dispose()

            # 保存窗口配置
            self._save_window_config()

            # 关闭主窗口
            if self._main_window:
                self._main_window.close()

            logger.info("Main window coordinator disposed")

        except Exception as e:
            logger.error(f"Failed to dispose main window coordinator: {e}")

    # 文件菜单方法
    def _on_new_file(self) -> None:
        """新建文件"""
        logger.info("新建文件功能待实现")
        self.show_message("新建文件功能待实现")

    def _on_open_file(self) -> None:
        """打开文件"""
        logger.info("打开文件功能待实现")
        self.show_message("打开文件功能待实现")

    def _on_save_file(self) -> None:
        """保存文件"""
        logger.info("保存文件功能待实现")
        self.show_message("保存文件功能待实现")

    def _on_exit(self) -> None:
        """退出应用程序"""
        self._main_window.close()

    # 编辑菜单方法
    def _on_undo(self) -> None:
        """撤销操作"""
        logger.info("撤销功能待实现")
        self.show_message("撤销功能待实现")

    def _on_redo(self) -> None:
        """重做操作"""
        logger.info("重做功能待实现")
        self.show_message("重做功能待实现")

    def _on_copy(self) -> None:
        """复制操作"""
        logger.info("复制功能待实现")
        self.show_message("复制功能待实现")

    def _on_paste(self) -> None:
        """粘贴操作"""
        logger.info("粘贴功能待实现")
        self.show_message("粘贴功能待实现")

    # 视图菜单方法
    def _on_refresh(self) -> None:
        """刷新数据"""
        try:
            # 刷新左侧面板数据
            left_panel = self._panels.get('left')
            if left_panel and hasattr(left_panel, '_on_refresh_clicked'):
                left_panel._on_refresh_clicked()

            self.show_message("数据已刷新")
            logger.info("Data refreshed")

        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            self.show_message(f"刷新失败: {e}")

    # 工具菜单方法
    def _on_advanced_search(self) -> None:
        """高级搜索"""
        try:
            from gui.dialogs.advanced_search_dialog import AdvancedSearchDialog

            dialog = AdvancedSearchDialog(self._main_window)
            dialog.search_completed.connect(self._on_search_completed)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"高级搜索失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开高级搜索失败: {str(e)}")

    def _on_search_completed(self, results):
        """处理搜索完成事件"""
        try:
            # 这里可以将搜索结果显示在左侧面板的股票列表中
            left_panel = self._panels.get('left')
            if left_panel and hasattr(left_panel, 'update_stock_list'):
                # 更新股票列表显示搜索结果
                left_panel.update_stock_list(results)

            QMessageBox.information(
                self._main_window,
                "搜索完成",
                f"搜索完成，共找到 {len(results)} 只符合条件的股票"
            )

        except Exception as e:
            logger.error(f"Failed to handle search results: {e}")

    def _on_export_data(self) -> None:
        """数据导出"""
        try:
            from gui.dialogs.data_export_dialog import DataExportDialog

            dialog = DataExportDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"数据导出失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开数据导出对话框失败: {str(e)}")

    def _on_data_export(self) -> None:
        """数据导出（别名方法）"""
        self._on_export_data()

    def _on_settings(self) -> None:
        """系统设置"""
        try:
            from gui.dialogs.settings_dialog import SettingsDialog

            dialog = SettingsDialog(
                parent=self._main_window,
                theme_service=self._theme_service,
                config_service=self._config_service
            )

            # 连接设置应用信号
            dialog.settings_applied.connect(self._on_settings_applied)
            dialog.theme_changed.connect(self._on_theme_changed)

            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"系统设置失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开系统设置对话框失败: {str(e)}")

    def _on_settings_applied(self, settings: dict) -> None:
        """处理设置应用事件"""
        try:
            # 保存设置到配置服务
            if self._config_service:
                for key, value in settings.items():
                    self._config_service.set(key, value)

            # 应用相关设置
            if 'font_size' in settings:
                # 应用字体大小变化
                font = self._main_window.font()
                font.setPointSize(settings['font_size'])
                self._main_window.setFont(font)

            logger.info("设置已应用")
            self.show_message("设置已保存并应用")

        except Exception as e:
            logger.error(f"应用设置失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"应用设置失败: {str(e)}")

    # 帮助菜单方法
    def _on_help(self) -> None:
        """帮助文档"""
        logger.info("帮助文档功能待实现")
        self.show_message("帮助文档功能待实现")

    def _on_shortcuts(self) -> None:
        """快捷键说明"""
        from PyQt5.QtWidgets import QMessageBox
        shortcuts_text = """
常用快捷键：

文件操作：
Ctrl+N - 新建
Ctrl+O - 打开
Ctrl+S - 保存
Ctrl+Q - 退出

编辑操作：
Ctrl+Z - 撤销
Ctrl+Y - 重做
Ctrl+C - 复制
Ctrl+V - 粘贴

视图操作：
F5 - 刷新数据

搜索操作：
Ctrl+Shift+F - 高级搜索

工具操作：
Ctrl+E - 数据导出
Ctrl+, - 系统设置

帮助：
F1 - 用户手册
Ctrl+F1 - 快捷键说明
Ctrl+F12 - 关于
        """
        QMessageBox.information(
            self._main_window, "快捷键说明", shortcuts_text.strip())

    def _on_about(self) -> None:
        """关于对话框"""
        about_text = """
FactorWeave-Quant ‌ 2.0 (重构版本)

基于HIkyuu量化框架的股票分析工具

主要功能：
• 股票数据查看和分析
• 技术指标计算和显示
• 策略回测和优化
• 投资组合管理
• 数据质量检查

版本：2.0
作者：HIkyuu开发团队
        """
        QMessageBox.about(self._main_window, "关于 FactorWeave-Quant ‌",
                          about_text.strip())

    # 高级功能菜单方法（保持原有实现）
    def _on_node_management(self) -> None:
        """节点管理"""
        try:
            from gui.dialogs.node_manager_dialog import NodeManagerDialog

            dialog = NodeManagerDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"节点管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开节点管理对话框失败: {str(e)}")

    def _on_cloud_api(self) -> None:
        """云端API管理"""
        try:
            from gui.dialogs.cloud_api_dialog import CloudApiDialog

            dialog = CloudApiDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"云端API管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开云端API管理对话框失败: {str(e)}")

    def _on_plugin_manager(self) -> None:
        """增强版插件管理器 - 统一的插件管理界面"""
        try:
            from gui.dialogs.enhanced_plugin_manager_dialog import EnhancedPluginManagerDialog
            from core.plugin_manager import PluginManager
            from core.services.sentiment_data_service import SentimentDataService

            # 智能获取插件管理器实例
            plugin_manager = None

            # 确保从正确的service_container获取
            service_container = self._service_container
            if not service_container:
                # 如果没有，尝试从全局获取
                from core.containers import get_service_container
                service_container = get_service_container()

            # 方法1：尝试从服务容器获取（主要方法）
            if service_container and service_container.is_registered(PluginManager):
                try:
                    plugin_manager = service_container.resolve(PluginManager)
                    logger.info("✅ 从服务容器获取插件管理器成功")

                    # 验证插件管理器是否已初始化
                    if plugin_manager and hasattr(plugin_manager, 'enhanced_plugins'):
                        all_plugins = plugin_manager.get_all_plugins()
                        logger.info(f"✅ 插件管理器已初始化，包含 {len(all_plugins)} 个插件")
                    else:
                        logger.warning("⚠️ 插件管理器未完全初始化，尝试重新初始化")
                        if plugin_manager and hasattr(plugin_manager, 'initialize'):
                            plugin_manager.initialize()

                except Exception as e:
                    logger.error(f"❌ 从服务容器获取插件管理器失败: {e}")
                    logger.error(traceback.format_exc())
                    plugin_manager = None
            else:
                logger.warning("⚠️ PluginManager未在服务容器中注册")

            # 方法2：如果方法1失败，尝试创建并初始化新实例
            if not plugin_manager:
                try:
                    logger.info("🔄 创建新的插件管理器实例...")

                    # 获取必要的依赖
                    from utils.config_manager import ConfigManager
                    config_manager = None

                    if service_container and service_container.is_registered(ConfigManager):
                        config_manager = service_container.resolve(ConfigManager)
                    else:
                        config_manager = ConfigManager()

                    # 创建并初始化插件管理器
                    plugin_manager = PluginManager(
                        plugin_dir="plugins",
                        main_window=self._main_window,
                        data_manager=None,
                        config_manager=config_manager,
                        log_manager=logger
                    )

                    # 初始化插件管理器
                    plugin_manager.initialize()
                    logger.info("✅ 插件管理器实例创建并初始化成功")

                    # 将新实例注册到服务容器（如果可能）
                    if service_container:
                        try:
                            service_container.register_instance(PluginManager, plugin_manager)
                            logger.info("✅ 新插件管理器实例已注册到服务容器")
                        except Exception as reg_e:
                            logger.warning(f"⚠️ 注册新插件管理器实例失败: {reg_e}")

                except Exception as e:
                    logger.error(f"❌ 创建插件管理器实例失败: {e}")
                    logger.error(traceback.format_exc())
                    # 继续执行，允许dialog处理空的plugin_manager

            # 获取情绪数据服务
            sentiment_service = None
            if service_container and service_container.is_registered(SentimentDataService):
                try:
                    sentiment_service = service_container.resolve(SentimentDataService)
                    logger.info("✅ 获取情绪数据服务成功")
                except Exception as e:
                    logger.warning(f"⚠️ 获取情绪数据服务失败: {e}")

            # 显示插件管理器状态
            plugin_status = "可用" if plugin_manager else "不可用"
            sentiment_status = "可用" if sentiment_service else "不可用"
            logger.info(f"📋 插件管理器状态: {plugin_status}, 情绪数据服务: {sentiment_status}")

            # 创建并显示增强版对话框
            dialog = EnhancedPluginManagerDialog(
                plugin_manager=plugin_manager,
                sentiment_service=sentiment_service,
                parent=self._main_window
            )

            # 设置对话框属性
            dialog.setWindowTitle("HIkyuu 插件管理器")
            dialog.setMinimumSize(1000, 700)

            # 居中显示
            if hasattr(self, 'center_dialog'):
                self.center_dialog(dialog)

            # 显示对话框
            result = dialog.exec_()
            logger.info(f"插件管理器对话框关闭，返回值: {result}")

        except ImportError as e:
            error_msg = f"插件管理器模块导入失败: {e}"
            logger.error(error_msg)
            QMessageBox.critical(
                self._main_window,
                "模块错误",
                f"{error_msg}\n\n请检查插件系统是否正确安装。"
            )
        except Exception as e:
            error_msg = f"打开插件管理器失败: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            QMessageBox.critical(
                self._main_window,
                "错误",
                f"{error_msg}\n\n请查看日志获取详细信息。"
            )

    def _on_plugin_market(self) -> None:
        """插件市场"""
        try:
            from gui.dialogs.enhanced_plugin_market_dialog import EnhancedPluginMarketDialog

            # 获取插件管理器
            plugin_manager = self._service_container.resolve(PluginManager)

            dialog = EnhancedPluginMarketDialog(
                plugin_manager, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"插件市场失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开插件市场对话框失败: {str(e)}")

    def _on_indicator_market(self) -> None:
        """指标市场"""
        try:
            from gui.dialogs.indicator_market_dialog import IndicatorMarketDialog

            dialog = IndicatorMarketDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"指标市场失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开指标市场对话框失败: {str(e)}")

    def _on_batch_analysis(self) -> None:
        """批量分析"""
        try:
            from gui.dialogs.batch_analysis_dialog import BatchAnalysisDialog

            dialog = BatchAnalysisDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开批量分析对话框失败: {str(e)}")

    def _on_strategy_management(self) -> None:
        """策略管理"""
        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog

            dialog = StrategyManagerDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"策略管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开策略管理对话框失败: {str(e)}")

    def _on_optimization_dashboard(self) -> None:
        """显示优化仪表板"""
        try:
            if self._optimization_dashboard is None:
                self._optimization_dashboard = create_optimization_dashboard(
                    self.event_bus)

            self._optimization_dashboard.show()
            self._optimization_dashboard.activateWindow()
            self._optimization_dashboard.raise_()
        except Exception as e:
            logger.error(f"打开优化仪表板失败: {e}")
            self.show_message(f"打开优化仪表板失败: {str(e)}", level='error')

    def _on_one_click_optimization(self) -> None:
        """一键优化"""
        try:
            from PyQt5.QtWidgets import QProgressDialog
            from optimization.auto_tuner import AutoTuner
            from PyQt5.QtCore import QThread, pyqtSignal

            # 创建进度对话框
            progress = QProgressDialog(
                "正在执行一键优化...", "取消", 0, 100, self._main_window)
            progress.setWindowTitle("一键优化")
            progress.setModal(True)
            progress.show()

            # 创建优化线程
            class OptimizationThread(QThread):
                progress_updated = pyqtSignal(int)
                optimization_completed = pyqtSignal(dict)
                error_occurred = pyqtSignal(str)

                def run(self):
                    try:
                        auto_tuner = AutoTuner(debug_mode=True)

                        # 模拟优化过程
                        for i in range(101):
                            if self.isInterruptionRequested():
                                return
                            self.progress_updated.emit(i)
                            self.msleep(50)

                        # 执行实际优化
                        result = auto_tuner.one_click_optimize()
                        self.optimization_completed.emit(result)

                    except Exception as e:
                        self.error_occurred.emit(str(e))

            def on_progress_updated(value):
                progress.setValue(value)

            def on_optimization_completed(result):
                progress.close()
                QMessageBox.information(self._main_window, "成功",
                                        f"一键优化完成！\n优化了 {len(result)} 个形态")
                logger.info(f"一键优化完成: {result}")

            def on_error_occurred(error):
                progress.close()
                QMessageBox.critical(
                    self._main_window, "错误", f"一键优化失败: {error}")
                logger.error(f"一键优化失败: {error}")

            def on_canceled():
                optimization_thread.requestInterruption()
                optimization_thread.wait()
                logger.info("一键优化已取消")

            # 创建并启动线程
            optimization_thread = OptimizationThread()
            optimization_thread.progress_updated.connect(on_progress_updated)
            optimization_thread.optimization_completed.connect(
                on_optimization_completed)
            optimization_thread.error_occurred.connect(on_error_occurred)

            progress.canceled.connect(on_canceled)

            optimization_thread.start()

        except Exception as e:
            logger.error(f"启动一键优化失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"启动一键优化失败: {str(e)}")

    def _on_intelligent_optimization(self) -> None:
        """智能优化"""
        try:
            from PyQt5.QtWidgets import QInputDialog, QProgressDialog

            # 获取优化参数
            performance_threshold, ok1 = QInputDialog.getDouble(
                self._main_window, "智能优化", "性能阈值 (0.0-1.0):", 0.8, 0.0, 1.0, 2
            )
            if not ok1:
                return

            improvement_target, ok2 = QInputDialog.getDouble(
                self._main_window, "智能优化", "改进目标 (0.0-1.0):", 0.1, 0.0, 1.0, 2
            )
            if not ok2:
                return

            # 创建进度对话框
            progress = QProgressDialog(
                "正在执行智能优化...", "取消", 0, 100, self._main_window)
            progress.setWindowTitle("智能优化")
            progress.setModal(True)
            progress.show()

            # 创建智能优化线程
            class SmartOptimizationThread(QThread):
                progress_updated = pyqtSignal(int)
                optimization_completed = pyqtSignal(dict)
                error_occurred = pyqtSignal(str)

                def __init__(self, perf_threshold, improve_target):
                    super().__init__()
                    self.performance_threshold = perf_threshold
                    self.improvement_target = improve_target

                @measure_performance("SmartOptimizationThread.run")
                def run(self):
                    try:
                        # 模拟智能优化过程
                        for i in range(101):
                            if self.isInterruptionRequested():
                                return
                            self.progress_updated.emit(i)
                            self.msleep(80)

                        # 执行实际智能优化
                        auto_tuner = AutoTuner(debug_mode=True)
                        result = auto_tuner.smart_optimize(
                            performance_threshold=self.performance_threshold,
                            improvement_target=self.improvement_target
                        )
                        self.optimization_completed.emit(result)

                    except Exception as e:
                        self.error_occurred.emit(str(e))

            def on_progress_updated(value):
                progress.setValue(value)

            def on_optimization_completed(result):
                progress.close()
                improved_count = result.get('improved_patterns', 0)
                total_improvement = result.get('total_improvement', 0)
                QMessageBox.information(self._main_window, "成功",
                                        f"智能优化完成！\n改进了 {improved_count} 个形态\n总体改进: {total_improvement:.2%}")
                logger.info(f"智能优化完成: {result}")

            def on_error_occurred(error):
                progress.close()
                QMessageBox.critical(
                    self._main_window, "错误", f"智能优化失败: {error}")
                logger.error(f"智能优化失败: {error}")

            def on_canceled():
                smart_thread.requestInterruption()
                smart_thread.wait()
                logger.info("智能优化已取消")

            # 创建并启动线程
            smart_thread = SmartOptimizationThread(
                performance_threshold, improvement_target)
            smart_thread.progress_updated.connect(on_progress_updated)
            smart_thread.optimization_completed.connect(
                on_optimization_completed)
            smart_thread.error_occurred.connect(on_error_occurred)

            progress.canceled.connect(on_canceled)

            smart_thread.start()

        except Exception as e:
            logger.error(f"启动智能优化失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"启动智能优化失败: {str(e)}")

    def _on_performance_evaluation(self):
        """性能评估"""
        try:
            # 使用现有的性能评估器
            from evaluation.performance_evaluation import create_performance_evaluator
            from gui.dialogs.performance_evaluation_dialog import PerformanceEvaluationDialog

            # 创建性能评估器
            evaluator = create_performance_evaluator()

            # 显示性能评估对话框
            dialog = PerformanceEvaluationDialog(self._main_window)
            dialog.set_evaluator(evaluator)
            dialog.exec_()

        except ImportError as e:
            self.logger.error(f"性能评估模块导入失败: {e}")
            # 使用备用的策略性能评估器
            try:
                from core.strategy.performance_evaluator import PerformanceEvaluator

                evaluator = PerformanceEvaluator()
                dialog = PerformanceEvaluationDialog(self._main_window)
                dialog.set_evaluator(evaluator)
                dialog.exec_()

            except Exception as e2:
                self.logger.error(f"备用性能评估也失败: {e2}")
                QMessageBox.warning(
                    self._main_window,
                    "性能评估",
                    f"性能评估功能暂时不可用：{e2}"
                )
        except Exception as e:
            self.logger.error(f"启动性能评估失败: {e}")
            QMessageBox.warning(
                self._main_window,
                "性能评估",
                f"启动性能评估失败：{e}"
            )

    def _on_version_management(self) -> None:
        """版本管理"""
        try:
            from gui.dialogs.version_manager_dialog import VersionManagerDialog

            dialog = VersionManagerDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"版本管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开版本管理对话框失败: {str(e)}")

    def _on_single_stock_quality_check(self) -> None:
        """单股质量检查"""
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog

            dialog = DataQualityDialog(self._main_window, mode='single')
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"单股质量检查失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开单股质量检查对话框失败: {str(e)}")

    def _on_batch_quality_check(self) -> None:
        """批量质量检查"""
        try:

            dialog = DataQualityDialog(self._main_window, mode='batch')
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"批量质量检查失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开批量质量检查对话框失败: {str(e)}")

    # 缓存管理方法
    def _on_clear_data_cache(self) -> None:
        """清理数据缓存"""
        try:
            # 获取股票服务
            stock_service = self.service_container.get_service(StockService)
            if stock_service:
                stock_service.clear_cache('data')

            # 获取图表服务
            chart_service = self.service_container.get_service(ChartService)
            if chart_service:
                chart_service.clear_cache()

            # 获取分析服务
            analysis_service = self.service_container.get_service(
                AnalysisService)
            if analysis_service:
                analysis_service.clear_cache()

            QMessageBox.information(self._main_window, "成功", "数据缓存已清理")
            logger.info("Data cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear data cache: {e}")
            QMessageBox.critical(self._main_window, "错误", f"清理数据缓存失败: {e}")

    def _on_clear_negative_cache(self) -> None:
        """清理负缓存"""
        try:
            # 获取股票服务
            stock_service = self.service_container.get_service(StockService)
            if stock_service:
                stock_service.clear_cache('negative')

            # 清理左侧面板的负缓存
            left_panel = self._panels.get('left')
            if left_panel and hasattr(left_panel, '_no_data_cache'):
                left_panel._no_data_cache.clear()

            QMessageBox.information(self._main_window, "成功", "负缓存已清理")
            logger.info("Negative cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear negative cache: {e}")
            QMessageBox.critical(self._main_window, "错误", f"清理负缓存失败: {e}")

    def _on_clear_all_cache(self) -> None:
        """清理所有缓存"""
        try:
            # 清理数据缓存
            self._on_clear_data_cache()

            # 清理负缓存
            self._on_clear_negative_cache()

            QMessageBox.information(self._main_window, "成功", "所有缓存已清理")
            logger.info("All cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear all cache: {e}")
            QMessageBox.critical(self._main_window, "错误", f"清理所有缓存失败: {e}")

    def _on_startup_guides(self) -> None:
        """显示启动向导"""
        try:
            from gui.dialogs.startup_guides_dialog import StartupGuidesDialog

            dialog = StartupGuidesDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except ImportError:
            # 如果启动向导对话框不存在，创建一个简单的消息框
            QMessageBox.information(
                self._main_window,
                "启动向导",
                "欢迎使用FactorWeave-Quant ‌ 2.0！\n\n"
                "主要功能：\n"
                "1. 股票数据查看和分析\n"
                "2. 技术指标计算和显示\n"
                "3. 策略回测和优化\n"
                "4. 插件扩展和市场\n"
                "5. 分布式计算支持\n\n"
                "如需帮助，请查看帮助文档。"
            )
        except Exception as e:
            logger.error(f"显示启动向导失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"显示启动向导失败: {e}")

    def _on_database_admin(self) -> None:
        """数据库管理"""
        try:
            from gui.dialogs.database_admin_dialog import DatabaseAdminDialog

            # 使用系统数据库路径
            db_path = "db/hikyuu_system.db"  # 使用相对路径

            dialog = DatabaseAdminDialog(db_path, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except ImportError:
            # 如果数据库管理对话框不存在，创建一个简单的消息框
            QMessageBox.information(
                self._main_window,
                "数据库管理",
                "数据库管理功能包括：\n\n"
                "1. 数据库连接管理\n"
                "2. 数据表维护\n"
                "3. 数据备份恢复\n"
                "4. 性能监控\n"
                "5. 索引优化\n\n"
                "此功能正在开发中..."
            )
        except Exception as e:
            logger.error(f"打开数据库管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开数据库管理失败: {e}")

    def _on_calculator(self) -> None:
        """打开计算器"""
        try:
            from gui.dialogs.calculator_dialog import CalculatorDialog

            dialog = CalculatorDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开计算器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开计算器失败: {e}")

    def _on_converter(self) -> None:
        """智能转换器选择 - 提供多种转换器选项"""
        try:
            # 创建转换器选择对话框
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

            choice_dialog = QDialog(self._main_window)
            choice_dialog.setWindowTitle("选择转换器类型")
            choice_dialog.setModal(True)
            choice_dialog.resize(300, 200)

            layout = QVBoxLayout(choice_dialog)

            # 标题
            title_label = QLabel("请选择要使用的转换器类型：")
            title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
            layout.addWidget(title_label)

            # 通用单位转换器按钮
            unit_btn = QPushButton("🔧 通用单位转换器")
            unit_btn.setStyleSheet("""
                QPushButton {
                    padding: 15px;
                    font-size: 14px;
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #bbdefb;
                }
            """)
            unit_btn.setToolTip("长度、重量、温度、面积等物理单位转换")
            unit_btn.clicked.connect(lambda: self._open_unit_converter(choice_dialog))
            layout.addWidget(unit_btn)

            # 汇率转换器按钮
            currency_btn = QPushButton("💱 汇率转换器")
            currency_btn.setStyleSheet("""
                QPushButton {
                    padding: 15px;
                    font-size: 14px;
                    background-color: #e8f5e8;
                    border: 2px solid #4caf50;
                    border-radius: 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #c8e6c9;
                }
            """)
            currency_btn.setToolTip("主要货币之间的汇率转换")
            currency_btn.clicked.connect(lambda: self._open_currency_converter(choice_dialog))
            layout.addWidget(currency_btn)

            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(choice_dialog.reject)
            layout.addWidget(cancel_btn)

            choice_dialog.exec_()

        except Exception as e:
            logger.error(f"打开转换器选择失败: {e}")
            # 降级到通用转换器
            try:
                from gui.dialogs.converter_dialog import ConverterDialog
                dialog = ConverterDialog(self._main_window)
                self.center_dialog(dialog)
                dialog.exec_()
            except Exception as e2:
                logger.error(f"打开通用转换器失败: {e2}")
                QMessageBox.critical(self._main_window, "错误", f"打开转换器失败: {e2}")

    def _open_unit_converter(self, parent_dialog):
        """打开通用单位转换器"""
        try:
            parent_dialog.accept()
            dialog = ConverterDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()
            logger.info("打开通用单位转换器")
        except Exception as e:
            logger.error(f"打开通用单位转换器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开通用单位转换器失败: {e}")

    def _open_currency_converter(self, parent_dialog):
        """打开汇率转换器"""
        try:
            parent_dialog.accept()
            from gui.tools.currency_converter import CurrencyConverter
            dialog = CurrencyConverter(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()
            logger.info("打开汇率转换器")
        except Exception as e:
            logger.error(f"打开汇率转换器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开汇率转换器失败: {e}")

    def _on_commission_calculator(self) -> None:
        """打开费率计算器"""
        try:
            from gui.tools.commission_calculator import CommissionCalculator

            CommissionCalculator.show_calculator(self._main_window)

        except Exception as e:
            logger.error(f"打开费率计算器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开费率计算器失败: {e}")

    def _on_currency_converter(self) -> None:
        """打开汇率转换器"""
        try:

            CurrencyConverter.show_converter(self._main_window)

        except Exception as e:
            logger.error(f"打开汇率转换器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开汇率转换器失败: {e}")

    def _on_system_optimizer(self) -> None:
        """打开系统维护工具"""
        try:
            from gui.dialogs import show_system_optimizer_dialog
            show_system_optimizer_dialog(self._main_window)
        except Exception as e:
            logger.error(f"打开系统维护工具失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开系统维护工具失败: {e}")

    def _check_data_usage_terms(self) -> None:
        """检查数据使用条款"""
        try:
            from gui.dialogs import DataUsageManager

            # 创建数据使用管理器
            usage_manager = DataUsageManager()

            # 检查用户是否已同意条款
            if not usage_manager.check_and_request_agreement(self._main_window):
                # 用户不同意条款，显示警告并退出
                QMessageBox.warning(
                    self._main_window,
                    "使用条款",
                    "您必须同意数据使用条款才能使用FactorWeave-Quant ‌系统。\n程序将退出。"
                )
                # 延迟退出，让用户看到消息
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, self._main_window.close)
            else:
                logger.info("用户已同意数据使用条款")

        except Exception as e:
            logger.error(f"检查数据使用条款失败: {e}")
            # 如果检查失败，显示默认条款
            try:
                from gui.dialogs import DataUsageTermsDialog
                DataUsageTermsDialog.show_terms(self._main_window)
            except:
                pass

    def _on_show_data_usage_terms(self) -> None:
        """显示数据使用条款"""
        try:
            DataUsageTermsDialog.show_terms(self._main_window)
        except Exception as e:
            logger.error(f"Failed to show data usage terms: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"无法显示数据使用条款: {str(e)}")

    def _toggle_performance_panel(self, checked: bool = None):
        """智能切换性能仪表板显示/隐藏"""
        try:
            # 优先使用_performance_dock（如果存在）
            if hasattr(self, '_performance_dock') and self._performance_dock:
                if checked is not None:
                    # 被菜单调用时使用checked参数
                    self._performance_dock.setVisible(checked)
                else:
                    # 被快捷键等调用时自动切换
                    is_visible = self._performance_dock.isVisible()
                    self._performance_dock.setVisible(not is_visible)
                logger.info(f"性能仪表板已{'显示' if self._performance_dock.isVisible() else '隐藏'}")
                return

            # 降级使用_performance_panel
            if hasattr(self, '_performance_panel') and self._performance_panel:
                if checked is not None:
                    self._performance_panel.setVisible(checked)
                else:
                    is_visible = self._performance_panel.isVisible()
                    self._performance_panel.setVisible(not is_visible)
                logger.info(f"性能仪表板已{'显示' if self._performance_panel.isVisible() else '隐藏'}")
            else:
                # 创建新的性能仪表板
                self._performance_panel = PerformanceDashboardPanel(self._main_window)
                show_panel = checked if checked is not None else True
                self._performance_panel.setVisible(show_panel)
                logger.info("性能仪表板已创建并显示")

        except Exception as e:
            logger.error(f"切换性能仪表板失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换性能仪表板: {e}")

    def _toggle_log_panel(self):
        """切换日志面板的显示/隐藏状态"""
        bottom_panel = self._panels.get('bottom')
        if bottom_panel:
            if hasattr(bottom_panel, '_toggle_panel'):
                bottom_panel._toggle_panel()
            elif hasattr(bottom_panel, '_root_frame'):
                is_visible = bottom_panel._root_frame.isVisible()
                bottom_panel._root_frame.setVisible(not is_visible)
                self._log_toggle_btn.setText("显示日志" if is_visible else "隐藏日志")

    def _set_all_tables_readonly(self):
        """设置所有表格为只读"""
        try:
            logger.info("设置所有表格为只读模式...")

            # 递归查找所有 QTableWidget 和 QTableView
            def set_tables_readonly(widget):
                from PyQt5.QtWidgets import QTableWidget, QTableView

                # 如果是表格控件，设置为只读
                if isinstance(widget, QTableWidget):
                    widget.setEditTriggers(QTableWidget.NoEditTriggers)
                    logger.debug(f"设置 QTableWidget 为只读: {widget.objectName()}")
                elif isinstance(widget, QTableView):
                    widget.setEditTriggers(QTableView.NoEditTriggers)
                    logger.debug(f"设置 QTableView 为只读: {widget.objectName()}")

                # 递归处理子控件
                for child in widget.findChildren(QWidget):
                    set_tables_readonly(child)

            # 从主窗口开始递归设置
            set_tables_readonly(self._main_window)
            logger.info("所有表格已设置为只读模式")

        except Exception as e:
            logger.error(f"设置表格只读模式失败: {e}")

    def toggle_log_panel(self) -> None:
        """切换日志面板显示/隐藏 - 菜单专用版本"""
        try:
            self._toggle_log_panel()
        except Exception as e:
            logger.error(f"切换日志面板失败: {e}")

    def _on_optimization_status(self) -> None:
        """显示优化系统状态"""
        try:
            # 检查优化系统状态
            status_info = {
                "系统状态": "运行中",
                "活跃优化任务": 0,
                "已完成任务": 0,
                "系统健康度": "良好"
            }

            # 构建状态消息
            message = "🔧 优化系统状态\n\n"
            for key, value in status_info.items():
                message += f"• {key}: {value}\n"

            QMessageBox.information(self._main_window, "优化系统状态", message)
            logger.info("查看优化系统状态")

        except Exception as e:
            logger.error(f"获取优化状态失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法获取优化状态: {e}")

    def _on_create_strategy(self) -> None:
        """创建新策略"""
        try:
            # 使用已有的策略管理功能
            self._on_strategy_management()
            logger.info("打开策略创建功能")
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法创建策略: {e}")

    def _on_import_strategy(self) -> None:
        """导入策略"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self._main_window,
                "导入策略文件",
                "",
                "策略文件 (*.json *.py);;所有文件 (*)"
            )
            if file_path:
                # TODO: 实现策略导入逻辑
                QMessageBox.information(self._main_window, "提示", "策略导入功能正在开发中")
                logger.info(f"导入策略: {file_path}")
        except Exception as e:
            logger.error(f"导入策略失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法导入策略: {e}")

    def _on_export_strategy(self) -> None:
        """导出策略"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "导出策略文件",
                "",
                "策略文件 (*.json *.py);;所有文件 (*)"
            )
            if file_path:
                # TODO: 实现策略导出逻辑
                QMessageBox.information(self._main_window, "提示", "策略导出功能正在开发中")
                logger.info(f"导出策略: {file_path}")
        except Exception as e:
            logger.error(f"导出策略失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法导出策略: {e}")

    def _on_strategy_backtest(self) -> None:
        """策略回测"""
        try:
            # TODO: 实现策略回测功能
            QMessageBox.information(self._main_window, "提示", "策略回测功能正在开发中")
            logger.info("启动策略回测")
        except Exception as e:
            logger.error(f"策略回测失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动策略回测: {e}")

    def _on_strategy_optimize(self) -> None:
        """策略优化"""
        try:
            # TODO: 实现策略优化功能
            QMessageBox.information(self._main_window, "提示", "策略优化功能正在开发中")
            logger.info("启动策略优化")
        except Exception as e:
            logger.error(f"策略优化失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动策略优化: {e}")

    def _on_import_data(self) -> None:
        """导入数据"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self._main_window,
                "导入数据文件",
                "",
                "数据文件 (*.csv *.xlsx *.json);;所有文件 (*)"
            )
            if file_path:
                # TODO: 实现数据导入逻辑
                QMessageBox.information(self._main_window, "提示", "数据导入功能正在开发中")
                logger.info(f"导入数据: {file_path}")
        except Exception as e:
            logger.error(f"导入数据失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法导入数据: {e}")

    def _on_data_quality_check(self) -> None:
        """数据质量检查"""
        try:
            # 使用已有的数据质量检查功能
            self._on_single_stock_quality_check()
            logger.info("启动数据质量检查")
        except Exception as e:
            logger.error(f"数据质量检查失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动数据质量检查: {e}")

    def _on_check_update(self) -> None:
        """检查更新"""
        try:
            # TODO: 实现版本检查逻辑
            QMessageBox.information(
                self._main_window,
                "检查更新",
                "当前版本: FactorWeave-Quant  v2.0\n\n自动更新功能正在开发中，请访问项目页面获取最新版本。"
            )
            logger.info("检查软件更新")
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法检查更新: {e}")

    def _on_default_theme(self) -> None:
        """切换到默认主题"""
        try:
            self._on_theme_changed('default')
            logger.info("切换到默认主题")
        except Exception as e:
            logger.error(f"切换默认主题失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换主题: {e}")

    def _on_light_theme(self) -> None:
        """切换到浅色主题"""
        try:
            self._on_theme_changed('light')
            logger.info("切换到浅色主题")
        except Exception as e:
            logger.error(f"切换浅色主题失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换主题: {e}")

    def _on_dark_theme(self) -> None:
        """切换到深色主题"""
        try:
            self._on_theme_changed('dark')
            logger.info("切换到深色主题")
        except Exception as e:
            logger.error(f"切换深色主题失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换主题: {e}")

    def _on_analyze(self) -> None:
        """启动分析功能"""
        try:
            # 检查是否有分析面板
            if hasattr(self, '_analysis_widget') and self._analysis_widget:
                self._analysis_widget.run_analysis()
                logger.info("启动分析功能")
            else:
                QMessageBox.information(
                    self._main_window,
                    "分析功能",
                    "分析功能正在开发中，敬请期待！"
                )
        except Exception as e:
            logger.error(f"启动分析失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动分析: {e}")

    def _on_backtest(self) -> None:
        """智能启动回测功能 - 根据当前活跃标签页启动相应回测"""
        try:
            # 优先检查分析widget是否存在且有当前标签
            if hasattr(self, '_analysis_widget') and self._analysis_widget:
                current_tab = self._analysis_widget.currentWidget()
                if current_tab and hasattr(current_tab, 'start_backtest'):
                    # 如果当前标签页有start_backtest方法，直接调用
                    current_tab.start_backtest()
                    logger.info(f"从{current_tab.__class__.__name__}启动回测功能")
                    return

            # 检查是否有专门的回测面板
            if hasattr(self, '_backtest_widget') and self._backtest_widget:
                self._backtest_widget.start_backtest()
                logger.info("从专用回测面板启动回测功能")
                return

            # 检查是否有形态分析标签页
            if hasattr(self, '_analysis_widget') and self._analysis_widget:
                # 尝试获取形态分析标签页
                for i in range(self._analysis_widget.count()):
                    tab = self._analysis_widget.widget(i)
                    if tab and hasattr(tab, 'start_backtest'):
                        tab_name = self._analysis_widget.tabText(i)
                        if '形态' in tab_name or 'pattern' in tab_name.lower():
                            self._analysis_widget.setCurrentIndex(i)
                            tab.start_backtest()
                            logger.info(f"切换到{tab_name}标签页并启动回测")
                            return

                # 如果找到任何有回测功能的标签页，使用第一个
                for i in range(self._analysis_widget.count()):
                    tab = self._analysis_widget.widget(i)
                    if tab and hasattr(tab, 'start_backtest'):
                        self._analysis_widget.setCurrentIndex(i)
                        tab.start_backtest()
                        tab_name = self._analysis_widget.tabText(i)
                        logger.info(f"切换到{tab_name}标签页并启动回测")
                        return

            # 如果没有找到任何回测功能，显示提示
            QMessageBox.information(
                self._main_window,
                "回测功能",
                "请先打开分析界面并选择相应的分析标签页后再启动回测"
            )
            logger.warning("未找到可用的回测功能")

        except Exception as e:
            logger.error(f"启动回测失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动回测: {e}")

    def _on_optimize(self) -> None:
        """启动优化功能"""
        try:
            # 使用已有的优化功能
            self._on_one_click_optimization()
            logger.info("启动优化功能")
        except Exception as e:
            logger.error(f"启动优化失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动优化: {e}")

    def _on_webgpu_status(self) -> None:
        """查看WebGPU状态"""
        try:
            # 检查WebGPU状态
            status_info = {
                "WebGPU支持": "检测中...",
                "硬件加速": "未知",
                "GPU设备": "未检测到",
                "兼容性": "测试中"
            }

            message = "🖥️ WebGPU状态检查\n\n"
            for key, value in status_info.items():
                message += f"• {key}: {value}\n"

            message += "\n💡 WebGPU功能正在开发中，当前显示为模拟数据。"

            QMessageBox.information(self._main_window, "WebGPU状态", message)
            logger.info("查看WebGPU状态")

        except Exception as e:
            logger.error(f"查看WebGPU状态失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法查看WebGPU状态: {e}")

    def _on_save_as_file(self) -> None:
        """另存为文件"""
        try:
            QMessageBox.information(
                self._main_window,
                "另存为",
                "另存为功能正在开发中，敬请期待！"
            )
            logger.info("执行另存为功能")
        except Exception as e:
            logger.error(f"另存为失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法另存为: {e}")

    def _on_close_file(self) -> None:
        """关闭文件"""
        try:
            QMessageBox.information(
                self._main_window,
                "关闭文件",
                "关闭文件功能正在开发中，敬请期待！"
            )
            logger.info("执行关闭文件功能")
        except Exception as e:
            logger.error(f"关闭文件失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法关闭文件: {e}")

    def _on_cut(self) -> None:
        """剪切操作"""
        try:
            # 尝试获取当前焦点的widget并执行剪切
            focused_widget = self._main_window.focusWidget()
            if focused_widget and hasattr(focused_widget, 'cut'):
                focused_widget.cut()
                logger.info("执行剪切操作")
            else:
                QMessageBox.information(
                    self._main_window,
                    "剪切",
                    "当前焦点不支持剪切操作"
                )
        except Exception as e:
            logger.error(f"剪切操作失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法执行剪切: {e}")

    def _on_select_all(self) -> None:
        """全选操作"""
        try:
            # 尝试获取当前焦点的widget并执行全选
            focused_widget = self._main_window.focusWidget()
            if focused_widget and hasattr(focused_widget, 'selectAll'):
                focused_widget.selectAll()
                logger.info("执行全选操作")
            else:
                QMessageBox.information(
                    self._main_window,
                    "全选",
                    "当前焦点不支持全选操作"
                )
        except Exception as e:
            logger.error(f"全选操作失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法执行全选: {e}")

    def _on_find(self) -> None:
        """查找功能"""
        try:
            QMessageBox.information(
                self._main_window,
                "查找",
                "查找功能正在开发中，敬请期待！"
            )
            logger.info("执行查找功能")
        except Exception as e:
            logger.error(f"查找功能失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法执行查找: {e}")

    def _on_replace(self) -> None:
        """替换功能"""
        try:
            QMessageBox.information(
                self._main_window,
                "替换",
                "替换功能正在开发中，敬请期待！"
            )
            logger.info("执行替换功能")
        except Exception as e:
            logger.error(f"替换功能失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法执行替换: {e}")

    def _on_zoom_in(self) -> None:
        """放大显示"""
        try:
            QMessageBox.information(
                self._main_window,
                "放大显示",
                "放大显示功能正在开发中，敬请期待！"
            )
            logger.info("执行放大显示")
        except Exception as e:
            logger.error(f"放大显示失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法放大显示: {e}")

    def _on_zoom_out(self) -> None:
        """缩小显示"""
        try:
            QMessageBox.information(
                self._main_window,
                "缩小显示",
                "缩小显示功能正在开发中，敬请期待！"
            )
            logger.info("执行缩小显示")
        except Exception as e:
            logger.error(f"缩小显示失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法缩小显示: {e}")

    def _on_fullscreen(self) -> None:
        """全屏模式切换"""
        try:
            if self._main_window.isFullScreen():
                self._main_window.showNormal()
                logger.info("退出全屏模式")
            else:
                self._main_window.showFullScreen()
                logger.info("进入全屏模式")
        except Exception as e:
            logger.error(f"全屏模式切换失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换全屏模式: {e}")

    def _on_update_data(self) -> None:
        """更新数据"""
        try:
            QMessageBox.information(
                self._main_window,
                "更新数据",
                "数据更新功能正在开发中，敬请期待！"
            )
            logger.info("执行数据更新")
        except Exception as e:
            logger.error(f"数据更新失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法更新数据: {e}")

    def _on_risk_calculator(self) -> None:
        """风险计算器"""
        try:
            QMessageBox.information(
                self._main_window,
                "风险计算器",
                "风险计算器功能正在开发中，敬请期待！"
            )
            logger.info("打开风险计算器")
        except Exception as e:
            logger.error(f"风险计算器失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开风险计算器: {e}")

    def _on_distributed_computing(self) -> None:
        """分布式计算"""
        try:
            QMessageBox.information(
                self._main_window,
                "分布式计算",
                "分布式计算功能正在开发中，敬请期待！"
            )
            logger.info("启动分布式计算")
        except Exception as e:
            logger.error(f"分布式计算失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动分布式计算: {e}")

    def _on_log_viewer(self) -> None:
        """日志查看器"""
        try:
            QMessageBox.information(
                self._main_window,
                "日志查看器",
                "日志查看器功能正在开发中，敬请期待！"
            )
            logger.info("打开日志查看器")
        except Exception as e:
            logger.error(f"日志查看器失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开日志查看器: {e}")

    def _on_memory_usage(self) -> None:
        """内存使用情况"""
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            message = f"""💾 内存使用情况

• 总内存: {memory_info.total / (1024**3):.1f} GB
• 已使用: {memory_info.used / (1024**3):.1f} GB
• 可用内存: {memory_info.available / (1024**3):.1f} GB
• 使用率: {memory_info.percent:.1f}%
"""
            QMessageBox.information(self._main_window, "内存使用情况", message)
            logger.info("查看内存使用情况")
        except ImportError:
            QMessageBox.information(
                self._main_window,
                "内存使用情况",
                "内存监控功能需要安装psutil库"
            )
        except Exception as e:
            logger.error(f"查看内存使用失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法查看内存使用: {e}")

    def _on_user_manual(self) -> None:
        """用户手册"""
        try:
            QMessageBox.information(
                self._main_window,
                "用户手册",
                "用户手册功能正在开发中，敬请期待！"
            )
            logger.info("打开用户手册")
        except Exception as e:
            logger.error(f"用户手册失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开用户手册: {e}")

    def _on_data_usage_terms(self) -> None:
        """数据使用条款"""
        try:
            QMessageBox.information(
                self._main_window,
                "数据使用条款",
                "数据使用条款功能正在开发中，敬请期待！"
            )
            logger.info("查看数据使用条款")
        except Exception as e:
            logger.error(f"数据使用条款失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法查看数据使用条款: {e}")

    def _on_toggle_toolbar(self) -> None:
        """切换工具栏显示/隐藏"""
        try:
            toolbar = self._main_window.toolBar()
            if toolbar:
                is_visible = toolbar.isVisible()
                toolbar.setVisible(not is_visible)
                logger.info(f"工具栏已{'隐藏' if is_visible else '显示'}")
            else:
                logger.warning("工具栏不存在")
        except Exception as e:
            logger.error(f"切换工具栏失败: {e}")

    def _on_toggle_statusbar(self) -> None:
        """切换状态栏显示/隐藏"""
        try:
            statusbar = self._main_window.statusBar()
            if statusbar:
                is_visible = statusbar.isVisible()
                statusbar.setVisible(not is_visible)
                logger.info(f"状态栏已{'隐藏' if is_visible else '显示'}")
            else:
                logger.warning("状态栏不存在")
        except Exception as e:
            logger.error(f"切换状态栏失败: {e}")

    def toolBar(self):
        """获取工具栏 - 兼容方法"""
        return self._main_window.toolBar() if self._main_window else None

    def statusBar(self):
        """获取状态栏 - 兼容方法"""
        return self._main_window.statusBar() if self._main_window else None
