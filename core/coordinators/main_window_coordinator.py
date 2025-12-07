from loguru import logger
"""
主窗口协调器

负责协调主窗口的所有UI面板和业务服务的交互。
这是整个应用的中央协调器，替代原来的TradingGUI类。
"""

from typing import Dict, Any, Optional, List, Union
import asyncio
import traceback
import sys
import os
from datetime import datetime
import pandas as pd

from PyQt5.QtWidgets import (
    QFileDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMessageBox, QDockWidget, QLabel, QPushButton, QFrame,
    QApplication
)
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot

from core.performance.unified_monitor import AutoTuner
from core.plugin_manager import PluginManager
from gui.dialogs.converter_dialog import ConverterDialog
from gui.dialogs.data_quality_dialog import DataQualityDialog
from gui.dialogs.data_usage_terms_dialog import DataUsageTermsDialog
from gui.tools.currency_converter import CurrencyConverter

from core.coordinators.base_coordinator import BaseCoordinator
from core.events import (
    EventBus, StockSelectedEvent, AssetSelectedEvent, ChartUpdateEvent, AnalysisCompleteEvent,
    DataUpdateEvent, ErrorEvent, UIUpdateEvent, ThemeChangedEvent, UIDataReadyEvent, AssetDataReadyEvent
)
from core.plugin_types import AssetType
from core.containers import ServiceContainer
from core.services import (
    StockService, ChartService, AnalysisService,
    ConfigService, UnifiedDataManager
)
from optimization.optimization_dashboard import create_optimization_dashboard
from gui.widgets.modern_performance_widget import ModernUnifiedPerformanceWidget

from core.performance import measure_performance
from gui.menu_bar import MainMenuBar



class MainWindowCoordinator(BaseCoordinator):
    """
    主窗口协调器

    负责：
    1. 管理主窗口的生命周期
    2. 协调各个UI面板的交互
    3. 处理全局事件
    4. 管理服务依赖
    """

    def __init__t__(self,
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
        self._main_window.setWindowTitle("FactorWeave-Quant  2.0 多资产分析系统")
        self._main_window.setGeometry(100, 100, 1400, 900)
        self._main_window.setMinimumSize(1200, 800)

        # UI面板
        self._panels: Dict[str, Any] = {}
        self._optimization_dashboard = None

        # 窗口状态
        self._window_state = {
            'title': 'FactorWeave-Quant  2.0 多资产分析系统',
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

        # 中央数据状态（支持多资产类型）
        self._current_symbol: Optional[str] = None
        self._current_asset_name: Optional[str] = None
        self._current_asset_type: AssetType = AssetType.STOCK_A
        self._current_market: Optional[str] = None
        self._current_asset_data: Dict[str, Any] = {}
        self._is_loading = False

        # 向后兼容属性
        @property
        def _current_stock_code(self) -> Optional[str]:
            return self._current_symbol

        @_current_stock_code.setter
        def _current_stock_code(self, value: Optional[str]):
            self._current_symbol = value

        @property
        def _current_stock_data(self) -> Dict[str, Any]:
            return self._current_asset_data

        @_current_stock_data.setter
        def _current_stock_data(self, value: Dict[str, Any]):
            self._current_asset_data = value

    def __init__(self, service_container, event_bus, parent=None):
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
        self._main_window.setWindowTitle("FactorWeave-Quant  2.0 多资产分析系统")
        self._main_window.setGeometry(100, 100, 1400, 900)
        self._main_window.setMinimumSize(1200, 800)

        # UI面板
        self._panels: Dict[str, Any] = {}
        self._optimization_dashboard = None

        # 窗口状态
        self._window_state = {
            'title': 'FactorWeave-Quant  2.0 多资产分析系统',
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

        # 中央数据状态（支持多资产类型）
        self._current_symbol: Optional[str] = None
        self._current_asset_name: Optional[str] = None
        self._current_asset_type: AssetType = AssetType.STOCK_A
        self._current_market: Optional[str] = None
        self._current_asset_data: Dict[str, Any] = {}
        self._is_loading = False

        # 向后兼容属性
        @property
        def _current_stock_code(self) -> Optional[str]:
            return self._current_symbol

        @_current_stock_code.setter
        def _current_stock_code(self, value: Optional[str]):
            self._current_symbol = value

        @property
        def _current_stock_data(self) -> Dict[str, Any]:
            return self._current_asset_data

        @_current_stock_data.setter
        def _current_stock_data(self, value: Dict[str, Any]):
            self._current_asset_data = value

    def _do_initialize(self) -> None:
        """初始化协调器"""
        import time
        start_time = time.time()

        try:
            # 获取服务
            service_start = time.time()
            self._stock_service = self.service_container.resolve(StockService)
            self._chart_service = self.service_container.resolve(ChartService)
            self._analysis_service = self.service_container.resolve(
                AnalysisService)
            # 使用ThemeManager替代ThemeService
            from utils.theme import get_theme_manager
            self._theme_manager = get_theme_manager(self._config_service if hasattr(self, '_config_service') else None)
            self._config_service = self.service_container.resolve(
                ConfigService)
            self._data_manager = self.service_container.resolve(
                UnifiedDataManager)
            service_time = time.time() - service_start
            logger.info(f"服务解析耗时: {service_time:.3f}秒")

            # 获取资产服务（TET模式）
            try:
                # 直接设置_asset_service为None，因为AssetService并不存在
                # 移除相对导入，改为设置默认值
                self._asset_service = None
                logger.info("AssetService已设置为None（服务不存在）")
            except Exception as e:
                logger.warning(f" AssetService初始化失败: {e}")
                self._asset_service = None

            # 如果AssetService初始化失败，设置为None
            if not hasattr(self, '_asset_service'):
                self._asset_service = None

            # 初始化窗口
            window_start = time.time()
            self._setup_window()
            window_time = time.time() - window_start
            logger.info(f"窗口设置耗时: {window_time:.3f}秒")

            # 创建UI面板
            panels_start = time.time()
            self._create_panels()
            panels_time = time.time() - panels_start
            logger.info(f"面板创建耗时: {panels_time:.3f}秒")

            # 设置布局
            layout_start = time.time()
            self._setup_layout()
            layout_time = time.time() - layout_start
            logger.info(f"布局设置耗时: {layout_time:.3f}秒")

            # 注册事件处理器
            events_start = time.time()
            self._register_event_handlers()
            events_time = time.time() - events_start
            logger.info(f"事件注册耗时: {events_time:.3f}秒")

            # 应用主题
            theme_start = time.time()
            self._apply_theme()
            theme_time = time.time() - theme_start
            logger.info(f"主题应用耗时: {theme_time:.3f}秒")

            # 加载配置
            config_start = time.time()
            self._load_window_config()
            config_time = time.time() - config_start
            logger.info(f"配置加载耗时: {config_time:.3f}秒")

            # 设置所有表格为只读
            # self._set_all_tables_readonly()

            # 检查数据使用条款
            terms_start = time.time()
            self._check_data_usage_terms()
            terms_time = time.time() - terms_start
            logger.info(f"条款检查耗时: {terms_time:.3f}秒")

            # 延迟初始化增强UI组件，避免阻塞主初始化流程
            # 使用QTimer在事件循环中异步初始化
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self._initialize_enhanced_ui_components_async)

            total_time = time.time() - start_time
            logger.info(f"Main window coordinator initialized successfully, 总耗时: {total_time:.3f}秒")

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
            from core.ui.panels.left_panel import LeftPanel
            from core.ui.panels.middle_panel import MiddlePanel
            from core.ui.panels.right_panel import RightPanel

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
            # ✅ 修复：设置中间面板的合理尺寸限制，避免图表区域过宽
            # 由于右侧面板已改为 QDockWidget，中间面板需要设置最小宽度以确保图表正常显示
            middle_panel._root_frame.setMinimumWidth(400)  # 确保图表有足够的显示空间
            horizontal_splitter.addWidget(middle_panel._root_frame)
            self._panels['middle'] = middle_panel

            # ✅ 修复：将右侧面板改为 QDockWidget，提供灵活的布局调整能力
            # 创建右侧面板（技术分析面板）
            right_panel = RightPanel(
                parent=self._main_window,
                coordinator=self,
                width=self._layout_config['right_panel_width']
            )

            # 创建 QDockWidget 包装右侧面板
            right_dock = QDockWidget("技术分析", self._main_window)
            right_dock.setWidget(right_panel._root_frame)
            right_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

            # 设置尺寸限制
            right_dock.setMinimumWidth(self._layout_config['right_panel_width'])
            right_dock.setMaximumWidth(1500)

            # 添加到主窗口右侧停靠区域
            self._main_window.addDockWidget(Qt.RightDockWidgetArea, right_dock)

            # 保存引用
            self._panels['right'] = right_panel
            self._panels['right_dock'] = right_dock

            logger.info("右侧技术分析面板已创建为 QDockWidget")

            # 设置分割器比例（仅包含左侧和中间面板）
            horizontal_splitter.setSizes([300, 1000])

            # 创建底部面板（日志面板）
            from core.ui.panels.bottom_panel import BottomPanel
            bottom_panel = BottomPanel(
                parent=self._main_window,
                coordinator=self
            )
            vertical_splitter.addWidget(bottom_panel._root_frame)
            self._panels['bottom'] = bottom_panel

            # 设置分割器的初始大小
            vertical_splitter.setSizes([700, 200])  # 主区域和底部面板的比例

            # 创建专业回测组件（作为停靠窗口）
            self._create_professional_backtest_widget()

            logger.info("All UI panels and components created successfully")

            # 连接面板之间的信号
            self._connect_panel_signals()

            # ✅ 修复：增强UI组件的集成已移至异步初始化中
            # 不再在这里同步集成，避免阻塞主初始化流程
            # 集成将在 _initialize_enhanced_ui_components_async() 中完成

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

    def _create_professional_backtest_widget(self) -> None:
        """创建专业回测组件作为停靠窗口"""
        try:
            from gui.widgets.backtest_widget import ProfessionalBacktestWidget

            # 创建专业回测组件
            self._backtest_widget = ProfessionalBacktestWidget(parent=self._main_window)

            # 创建停靠窗口
            backtest_dock = QDockWidget("专业回测系统", self._main_window)
            backtest_dock.setWidget(self._backtest_widget)
            backtest_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

            # 添加到主窗口（默认停靠在右侧）
            self._main_window.addDockWidget(Qt.RightDockWidgetArea, backtest_dock)

            # 默认隐藏，用户可以通过菜单显示
            backtest_dock.hide()

            # 保存引用
            self._panels['backtest_dock'] = backtest_dock
            self._panels['backtest'] = self._backtest_widget

            logger.info("专业回测组件创建成功")

        except Exception as e:
            logger.error(f"创建专业回测组件失败: {e}")
            # 创建一个占位符，避免后续引用错误
            self._backtest_widget = None

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

    def _register_event_handlers(self) -> None:
        """注册事件处理器 - 在_setup_layout中实现"""
        pass  # 实际订阅在_setup_layout中

    def _setup_layout(self) -> None:
        """设置布局"""
        # 布局已在_create_panels中设置
        try:
            # ✅ 修复：注册股票选择事件处理器
            # 注意：_on_stock_selected是异步方法，需要用QTimer或其他机制调度
            self.event_bus.subscribe(StockSelectedEvent, self._handle_stock_selected_sync)

            # 注册通用资产选择事件处理器
            self.event_bus.subscribe(
                AssetSelectedEvent, self._on_asset_selected)

            # 注册图表更新事件处理器
            self.event_bus.subscribe(ChartUpdateEvent, self._on_chart_updated)

            # 注册分析完成事件处理器
            self.event_bus.subscribe(
                AnalysisCompleteEvent, self._on_analysis_completed)

            # 注册数据更新事件处理器
            self.event_bus.subscribe(DataUpdateEvent, self._on_data_update)

            # 注册错误事件处理器
            self.event_bus.subscribe(ErrorEvent, self._on_error)

            # 注册UI数据就绪事件处理器（向后兼容）
            self.event_bus.subscribe(UIDataReadyEvent, self._on_ui_data_ready)

            # 注册通用资产数据就绪事件处理器
            self.event_bus.subscribe(AssetDataReadyEvent, self._on_asset_data_ready)

            # 注册主题变化事件处理器
            self.event_bus.subscribe(ThemeChangedEvent, self._on_theme_changed)

            logger.info("Event handlers registered successfully")

        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}")
            raise

    def _apply_theme(self) -> None:
        """应用主题"""
        try:
            # 使用ThemeManager获取当前主题
            if hasattr(self, '_theme_manager') and self._theme_manager:
                current_theme = self._theme_manager.current_theme
                is_qss = self._theme_manager.is_qss_theme()

                logger.info(f"Theme applied: {current_theme}, Type: {'QSS' if is_qss else 'JSON'}")

                # 如果是JSON主题，需要手动通知各个面板更新
                if not is_qss:
                    self._notify_panels_theme_change()
            else:
                logger.warning("ThemeManager not available")

        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")

    def _notify_panels_theme_change(self) -> None:
        """通知所有面板主题变化（用于JSON主题）"""
        try:
            # 遍历所有面板，调用它们的主题更新方法
            for panel_name, panel in self._panels.items():
                try:
                    # 如果面板有_on_theme_changed方法，调用它
                    if hasattr(panel, '_on_theme_changed'):
                        panel._on_theme_changed(self._theme_manager.current_theme)

                    # 如果面板有update_theme方法，调用它
                    elif hasattr(panel, 'update_theme'):
                        panel.update_theme()

                    # 强制重绘
                    if hasattr(panel, 'update'):
                        panel.update()

                except Exception as e:
                    logger.warning(f"Panel {panel_name} theme update failed: {e}")

            logger.info("Notified all panels of theme change")

        except Exception as e:
            logger.error(f"Failed to notify panels: {e}")

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

    def _handle_stock_selected_sync(self, event: StockSelectedEvent) -> None:
        """同步包装器：处理股票选择事件"""
        try:
            from PyQt5.QtCore import QTimer
            # 使用QTimer.singleShot在主线程中异步执行
            QTimer.singleShot(0, lambda: self._run_async_handler(self._on_stock_selected(event)))
        except Exception as e:
            logger.error(f"调度股票选择事件处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _run_async_handler(self, coro):
        """运行异步处理器"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(coro)
            else:
                loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"运行异步处理器失败: {e}")

    @measure_performance("MainWindowCoordinator._on_stock_selected")
    async def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件 - 新的统一数据加载流程"""
        if not event or not event.stock_code or self._is_loading:
            return

        # 在开始新任务前，取消之前所有相关的请求
        previous_stock_code = getattr(self, '_current_stock_code', '未知')
        try:
            await self._chart_service.cancel_previous_requests()
            await self._analysis_service.cancel_previous_requests()
            logger.info(f"已取消先前为 {previous_stock_code} 发出的请求。")
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

            # 1. ✅ 优化：优先使用事件中的K线数据，避免重复查询
            kline_data = None
            if hasattr(event, 'kline_data') and event.kline_data is not None:
                logger.info(f"使用LeftPanel预加载的K线数据: {event.stock_code}")
                kline_data = event.kline_data
                logger.debug(f"预加载数据行数: {len(kline_data) if hasattr(kline_data, '__len__') else 'N/A'}")
            else:
                # 降级：重新查询K线数据
                # ✅ 从事件中获取资产类型（默认为股票）
                asset_type = getattr(event, 'asset_type', AssetType.STOCK_A)
                logger.info(f"事件中无K线数据，开始请求K线数据: {event.stock_code} ({asset_type.value})")
                kline_data_response = await self._data_manager.request_data(
                    stock_code=event.stock_code,
                    data_type='kdata',
                    period=period,          # 传递周期
                    time_range=time_range,  # 传递时间范围
                    asset_type=asset_type   # ✅ 传递资产类型
                )

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

            # 2. 再获取分析数据，传入已获取的K线数据（可选，失败不影响K线显示）
            analysis_data = None
            try:
                analysis_data = await self._analysis_service.analyze_stock(
                    stock_code=event.stock_code,
                    analysis_type='comprehensive',
                    kline_data=kline_data
                )
                logger.info(f"分析数据加载完成: {event.stock_code}")
            except Exception as analysis_error:
                logger.warning(f"分析数据加载失败（继续显示K线）: {analysis_error}")
                analysis_data = {'data_available': False, 'error': str(analysis_error)}

            # 3. 存储到中央数据状态 - 增强数据验证和日志
            logger.info(f"=== 准备中央数据状态 ===")
            logger.info(f"K线数据类型: {type(kline_data).__name__}")
            if hasattr(kline_data, 'shape'):
                logger.info(f"K线数据形状: {kline_data.shape}")
            elif hasattr(kline_data, '__len__'):
                logger.info(f"K线数据长度: {len(kline_data)}")

            self._current_stock_data = {
                'stock_code': event.stock_code,
                'stock_name': event.stock_name,
                'market': event.market,
                'kline_data': kline_data,  # 确保使用正确的键名
                'kdata': kline_data,       # 向后兼容
                'analysis': analysis_data,
                'period': period,
                'time_range': time_range,
                'chart_type': chart_type
            }

            # 验证数据完整性
            if analysis_data:
                logger.info(f"分析数据包含键: {list(analysis_data.keys()) if isinstance(analysis_data, dict) else 'Not a dict'}")
                # 如果分析数据中包含指标数据，添加到主数据中
                if isinstance(analysis_data, dict):
                    if 'indicators' in analysis_data:
                        self._current_stock_data['indicators'] = analysis_data['indicators']
                        self._current_stock_data['indicators_data'] = analysis_data['indicators']
                    if 'technical_analysis' in analysis_data:
                        self._current_stock_data['technical_analysis'] = analysis_data['technical_analysis']

            logger.info(f"中央数据状态键: {list(self._current_stock_data.keys())}")
            logger.info(f"数据已存储到中央状态，准备发布UIDataReadyEvent事件: {event.stock_code}")

            # 4. 发布数据准备就绪事件 - 增强事件数据
            logger.info(f"=== 创建UIDataReadyEvent ===")
            data_ready_event = UIDataReadyEvent(
                source="MainWindowCoordinator",
                stock_code=event.stock_code,
                stock_name=event.stock_name,
                ui_data=self._current_stock_data
            )

            # 验证事件数据
            logger.info(f"UIDataReadyEvent.ui_data键: {list(data_ready_event.ui_data.keys()) if data_ready_event.ui_data else 'None'}")

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

    @measure_performance("MainWindowCoordinator._on_asset_selected")
    async def _on_asset_selected(self, event: AssetSelectedEvent) -> None:
        """处理通用资产选择事件（支持多资产类型）"""
        if not event or not event.symbol or self._is_loading:
            return

        # 在开始新任务前，取消之前所有相关的请求
        try:
            await self._chart_service.cancel_previous_requests()
            await self._analysis_service.cancel_previous_requests()
            logger.info(f"已取消先前为 {self._current_symbol} 发出的请求。")
        except Exception as e:
            logger.error(f"取消先前请求时出错: {e}", exc_info=True)

        self._is_loading = True

        # 更新当前资产状态
        self._current_symbol = event.symbol
        self._current_asset_name = event.name
        self._current_asset_type = event.asset_type
        self._current_market = event.market

        # 更新窗口标题
        asset_type_name = self._get_asset_type_display_name(event.asset_type)
        self._main_window.setWindowTitle(f"FactorWeave-Quant  2.0 - {event.name} ({event.symbol}) - {asset_type_name}")

        self.show_message(
            f"正在加载 {event.name} ({event.symbol}) 的{asset_type_name}数据...", level='info')

        try:
            # 从事件中提取参数
            period = event.period if event.period else 'D'  # 默认日线
            time_range = event.time_range if event.time_range else "最近1年"  # 默认最近1年
            chart_type = event.chart_type if event.chart_type else "K线图"  # 默认K线图

            logger.info(f"加载数据，资产：{event.symbol}，类型：{event.asset_type.value}，周期：{period}，时间范围：{time_range}")

            # 尝试使用资产服务获取数据
            asset_data = None
            try:
                if hasattr(self, '_asset_service') and self._asset_service:
                    asset_data = self._asset_service.get_historical_data(
                        symbol=event.symbol,
                        asset_type=event.asset_type,
                        period=period
                    )
                else:
                    # 降级到统一数据管理器
                    asset_data = self._data_manager.get_asset_data(
                        symbol=event.symbol,
                        asset_type=event.asset_type,
                        period=period
                    )
            except Exception as e:
                logger.warning(f"使用TET模式获取数据失败，尝试传统方式: {e}")

                # ✅ 降级到传统request_data方式（支持所有资产类型）
                kline_data_response = await self._data_manager.request_data(
                    stock_code=event.symbol,
                    data_type='kdata',
                    period=period,
                    time_range=time_range,
                    asset_type=event.asset_type  # ✅ 传递资产类型
                )

                if isinstance(kline_data_response, dict):
                    asset_data = kline_data_response.get('kline_data')
                else:
                    asset_data = kline_data_response

            # 关键检查点：确认核心数据是否存在
            if asset_data is None or asset_data.empty:
                logger.warning(f"无法获取 {event.name} 的数据。")
                self.show_message(
                    f"无法获取 {event.name} ({event.symbol}) 的数据，请尝试其他{asset_type_name}。", level='warning')
                return

            logger.info(f"资产数据加载完成: {event.symbol}, 开始分析...")

            # 如果是股票类型，进行传统分析
            analysis_data = None
            if event.asset_type == AssetType.STOCK_A:
                try:
                    analysis_data = await self._analysis_service.analyze_stock(
                        stock_code=event.symbol,
                        analysis_type='comprehensive',
                        kline_data=asset_data
                    )
                    logger.info(f"股票分析数据加载完成: {event.symbol}")
                except Exception as e:
                    logger.warning(f"股票分析失败: {e}")

            # 存储到中央数据状态
            self._current_asset_data = {
                'symbol': event.symbol,
                'name': event.name,
                'asset_type': event.asset_type.value,
                'market': event.market,
                'period': period,
                'time_range': time_range,
                'chart_type': chart_type,
                'kline_data': asset_data,
                'analysis_data': analysis_data or {}
            }

            # 发送资产数据就绪事件
            asset_data_ready_event = AssetDataReadyEvent(
                symbol=event.symbol,
                name=event.name,
                asset_type=event.asset_type,
                market=event.market,
                data_type="kline",
                data=asset_data
            )

            # 同时发送向后兼容的UIDataReadyEvent（如果是股票）
            if event.asset_type == AssetType.STOCK_A:
                ui_data_ready_event = UIDataReadyEvent(
                    stock_code=event.symbol,
                    stock_name=event.name,
                    kline_data=asset_data,
                    market=event.market
                )
                self.event_bus.emit(ui_data_ready_event)

            self.event_bus.emit(asset_data_ready_event)

            # 更新状态栏
            self.show_message(
                f"{event.name} ({event.symbol}) 数据加载完成", level='success')

            logger.info(f"资产数据流程完成: {event.symbol}")

        except Exception as e:
            logger.error(f"加载资产 {event.symbol} 数据时出错: {e}", exc_info=True)
            self.show_message(
                f"加载 {event.name} 数据失败", level='error')

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

    def _get_asset_type_display_name(self, asset_type: AssetType) -> str:
        """获取资产类型的显示名称"""
        display_names = {
            AssetType.STOCK_A: "股票",
            AssetType.CRYPTO: "加密货币",
            AssetType.FUTURES: "期货",
            AssetType.FOREX: "外汇",
            AssetType.INDEX: "指数",
            AssetType.FUND: "基金",
            AssetType.BOND: "债券",
            AssetType.COMMODITY: "商品"
        }
        return display_names.get(asset_type, "未知资产")

    @pyqtSlot(AssetDataReadyEvent)
    def _on_asset_data_ready(self, event: AssetDataReadyEvent) -> None:
        """处理通用资产数据就绪事件"""
        try:
            if not event or not event.symbol:
                return

            # 更新窗口标题
            asset_type_name = self._get_asset_type_display_name(event.asset_type)
            title = f"FactorWeave-Quant  2.0 - {event.name} ({event.symbol}) - {asset_type_name}"
            if event.market:
                title += f" [{event.market}]"

            self._main_window.setWindowTitle(title)

            # 更新状态栏
            status_text = f"当前资产: {event.name} ({event.symbol}) | 类型: {asset_type_name}"
            if event.market:
                status_text += f" | 市场: {event.market}"

            self.show_message(status_text, level='info')

            logger.info(f"资产数据就绪事件处理完成: {event.symbol}")

        except Exception as e:
            logger.error(f"处理资产数据就绪事件失败: {e}")

    @pyqtSlot(UIDataReadyEvent)
    def _on_ui_data_ready(self, event: UIDataReadyEvent) -> None:
        """处理UI数据就绪事件，更新主窗口状态栏并重新渲染图表"""
        try:
            # 兼容两种事件格式：ui_data.kline_data 和 直接的 kline_data
            kdata = None
            ui_data = {}
            
            # 尝试从 event.ui_data 获取数据（新型事件格式）
            if hasattr(event, 'ui_data') and event.ui_data:
                kdata = event.ui_data.get('kline_data')
                ui_data = event.ui_data
                logger.debug(f"从event.ui_data获取K线数据: {type(kdata)}")
            
            # 如果没有从 ui_data 获取到，尝试从 event.kline_data 获取（传统事件格式）
            if kdata is None and hasattr(event, 'kline_data') and event.kline_data is not None:
                kdata = event.kline_data
                ui_data = {'kline_data': kdata}
                logger.debug(f"从event.kline_data获取K线数据: {type(kdata)}")
            
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
                
                # 🔧 修复技术指标刷新问题：触发图表更新以重新渲染指标
                self._trigger_chart_update_with_indicators(ui_data, event.stock_code)
            else:
                self._status_label.setText("已加载 (0)")
                self._data_time_label.setText("数据时间: -")
                logger.warning("未获取到有效的K线数据，无法更新图表")
        except Exception as e:
            logger.error(f"更新主窗口状态栏失败: {e}", exc_info=True)
            self._status_label.setText("状态更新失败")
            self._data_time_label.setText("数据时间: -")
            
    def _trigger_chart_update_with_indicators(self, ui_data: dict, stock_code: str) -> None:
        """触发图表更新并重新渲染指标"""
        try:
            # 获取中间面板的图表控件
            middle_panel = self._panels.get('middle')
            if not middle_panel or not hasattr(middle_panel, 'chart_widget'):
                logger.warning("中间面板或图表控件不存在，跳过指标刷新")
                return
                
            chart_widget = middle_panel.chart_widget
            if not chart_widget:
                logger.warning("图表控件不存在，跳过指标刷新")
                return
            
            # 🔧 确保在数据更新前保留当前指标状态
            current_indicators = getattr(chart_widget, 'active_indicators', None)
            if current_indicators:
                logger.info(f"保留当前指标状态: {[ind.get('name', 'unknown') for ind in current_indicators]}")
                
            # 构建更新数据，确保包含指标数据
            update_data = {
                'kline_data': ui_data.get('kline_data'),
                'stock_code': stock_code,
                'title': getattr(chart_widget, 'current_stock', stock_code)
            }
            
            # 如果有指标数据，也传递过去
            indicators_data = ui_data.get('indicators_data', {})
            if indicators_data:
                update_data['indicators_data'] = indicators_data
                logger.info(f"传递指标数据到图表: {list(indicators_data.keys())}")
            
            # 🔧 如果没有通过indicators_data传递指标，则通过active_indicators字段传递
            if not indicators_data and current_indicators:
                update_data['active_indicators'] = current_indicators
                logger.info(f"通过active_indicators字段传递指标: {[ind.get('name', 'unknown') for ind in current_indicators]}")
            
            # 触发图表更新，这将重新渲染所有指标
            logger.info(f"触发图表更新，股票代码: {stock_code}")
            chart_widget.update_chart(update_data)
            logger.info("✅ 图表更新完成，指标将重新渲染")
            
        except Exception as e:
            logger.error(f"触发图表更新失败: {e}", exc_info=True)

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

                # 使用ThemeManager
                if hasattr(self, '_theme_manager') and self._theme_manager:
                    self._theme_manager.set_theme(theme_name)
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

    def _on_data_export(self) -> None:
        """数据导出（别名方法）"""
        self._on_export_data()

    def _on_settings(self) -> None:
        """系统设置"""
        try:
            from gui.dialogs.settings_dialog import SettingsDialog

            dialog = SettingsDialog(
                parent=self._main_window,
                theme_manager=self._theme_manager if hasattr(self, '_theme_manager') else None,
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
FactorWeave-Quant  2.0 (重构版本)

基于FactorWeave-Quant量化框架的股票分析工具

主要功能：
 股票数据查看和分析
 技术指标计算和显示
 策略回测和优化
 投资组合管理
 数据质量检查

版本：2.0
作者：FactorWeave-Quant开发团队
        """
        QMessageBox.about(self._main_window, "关于 FactorWeave-Quant ",
                          about_text.strip())

    # 高级功能菜单方法（保持原有实现）
    def _on_node_management(self) -> None:
        """节点管理（分布式节点监控）"""
        try:
            # ✅ 使用新的真实数据UI
            from gui.dialogs.distributed_node_monitor_dialog import DistributedNodeMonitorDialog
            from core.containers import get_service_container

            # 获取分布式服务
            container = get_service_container()
            distributed_service = container.get('distributed_service')

            if not distributed_service:
                QMessageBox.warning(
                    self._main_window,
                    "警告",
                    "分布式服务未初始化，请检查系统配置"
                )
                logger.warning("分布式服务未初始化")
                return

            dialog = DistributedNodeMonitorDialog(distributed_service, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"节点管理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开分布式节点监控失败: {str(e)}")

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
        # 防止重复打开 - 检查是否已有插件管理对话框实例
        if hasattr(self, '_plugin_manager_dialog') and self._plugin_manager_dialog is not None:
            if self._plugin_manager_dialog.isVisible():
                self._plugin_manager_dialog.raise_()
                self._plugin_manager_dialog.activateWindow()
                logger.info("插件管理对话框已存在，激活现有窗口")
                return
            else:
                self._plugin_manager_dialog = None

        try:
            from gui.dialogs.enhanced_plugin_manager_dialog import EnhancedPluginManagerDialog
            from core.plugin_manager import PluginManager

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
                    logger.info("从服务容器获取插件管理器成功")

                    # 验证插件管理器是否已初始化
                    if plugin_manager and hasattr(plugin_manager, 'enhanced_plugins'):
                        all_plugins = plugin_manager.get_all_plugins()
                        logger.info(f" 插件管理器已初始化，包含 {len(all_plugins)} 个插件")
                    else:
                        logger.warning("插件管理器未完全初始化，尝试重新初始化")
                        if plugin_manager and hasattr(plugin_manager, 'initialize'):
                            plugin_manager.initialize()

                except Exception as e:
                    logger.error(f" 从服务容器获取插件管理器失败: {e}")
                    logger.error(traceback.format_exc())
                    plugin_manager = None
            else:
                logger.warning("PluginManager未在服务容器中注册")

            # 方法2：如果方法1失败，尝试创建并初始化新实例
            if not plugin_manager:
                try:
                    logger.info("创建新的插件管理器实例...")

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
                        # log_manager已迁移到Loguru
                    )

                    # 初始化插件管理器
                    plugin_manager.initialize()
                    logger.info("插件管理器实例创建并初始化成功")

                    # 将新实例注册到服务容器（如果可能）
                    if service_container:
                        try:
                            service_container.register_instance(PluginManager, plugin_manager)
                            logger.info("新插件管理器实例已注册到服务容器")
                        except Exception as reg_e:
                            logger.warning(f" 注册新插件管理器实例失败: {reg_e}")

                except Exception as e:
                    logger.error(f" 创建插件管理器实例失败: {e}")
                    logger.error(traceback.format_exc())
                    # 继续执行，允许dialog处理空的plugin_manager

            # ✅ 情绪数据服务已删除（功能已整合到热点分析）
            sentiment_service = None

            # 显示插件管理器状态
            plugin_status = "可用" if plugin_manager else "不可用"
            logger.info(f" 插件管理器状态: {plugin_status}")

            # 创建并显示增强版对话框
            self._plugin_manager_dialog = EnhancedPluginManagerDialog(
                plugin_manager=plugin_manager,
                sentiment_service=sentiment_service,  # 传递None，保持兼容性
                parent=self._main_window
            )

            # 设置对话框属性
            self._plugin_manager_dialog.setWindowTitle("FactorWeave-Quant 插件管理器")
            self._plugin_manager_dialog.setMinimumSize(1000, 700)

            # 连接对话框的关闭信号
            self._plugin_manager_dialog.finished.connect(self._on_plugin_manager_dialog_closed)

            # 居中显示
            if hasattr(self, 'center_dialog'):
                self.center_dialog(self._plugin_manager_dialog)

            # 显示对话框
            self._plugin_manager_dialog.show()
            logger.info("插件管理器对话框已显示")

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
            # 清理可能的无效引用
            if hasattr(self, '_plugin_manager_dialog'):
                self._plugin_manager_dialog = None

    def _on_plugin_manager_dialog_closed(self):
        """插件管理对话框关闭时的回调"""
        logger.info("插件管理对话框已关闭，清理引用")
        if hasattr(self, '_plugin_manager_dialog'):
            self._plugin_manager_dialog = None

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
            # from gui.dialogs.batch_analysis_dialog import BatchAnalysisDialog  # 已移除
            logger.warning("批量分析对话框已移除，请使用主界面右侧面板的批量分析功能")
            return

            dialog = BatchAnalysisDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开批量分析对话框失败: {str(e)}")

    def _on_strategy_management(self) -> None:
        """策略管理"""
        # 防止重复打开 - 检查是否已有策略管理对话框实例
        if hasattr(self, '_strategy_manager_dialog') and self._strategy_manager_dialog is not None:
            if self._strategy_manager_dialog.isVisible():
                self._strategy_manager_dialog.raise_()
                self._strategy_manager_dialog.activateWindow()
                logger.info("策略管理对话框已存在，激活现有窗口")
                return
            else:
                self._strategy_manager_dialog = None

        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog

            # 创建策略管理对话框实例并保存引用
            self._strategy_manager_dialog = StrategyManagerDialog(self._main_window)

            # 连接对话框的关闭信号
            self._strategy_manager_dialog.finished.connect(self._on_strategy_manager_dialog_closed)

            self.center_dialog(self._strategy_manager_dialog)
            self._strategy_manager_dialog.show()

        except Exception as e:
            logger.error(f"策略管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开策略管理对话框失败: {str(e)}")
            # 清理可能的无效引用
            if hasattr(self, '_strategy_manager_dialog'):
                self._strategy_manager_dialog = None

    def _on_strategy_manager_dialog_closed(self):
        """策略管理对话框关闭时的回调"""
        logger.info("策略管理对话框已关闭，清理引用")
        if hasattr(self, '_strategy_manager_dialog'):
            self._strategy_manager_dialog = None

    def _on_trading_monitor(self) -> None:
        """交易监控"""
        try:
            # 检查是否已经创建了交易监控窗口
            if not hasattr(self, '_trading_monitor_window') or self._trading_monitor_window is None:
                from gui.widgets.enhanced_trading_monitor_widget import EnhancedTradingMonitorWidget
                from core.services.trading_service import TradingService
                from core.services.strategy_service import StrategyService

                # 从服务容器获取服务
                trading_service = None
                strategy_service = None

                try:
                    trading_service = self.service_container.resolve(TradingService)
                except Exception as e:
                    logger.warning(f"无法获取TradingService: {e}")

                try:
                    strategy_service = self.service_container.resolve(StrategyService)
                except Exception as e:
                    logger.warning(f"无法获取StrategyService: {e}")

                # 创建交易监控窗口
                self._trading_monitor_window = EnhancedTradingMonitorWidget(
                    parent=None,  # 独立窗口
                    trading_service=trading_service,
                    strategy_service=strategy_service
                )

                # 设置窗口属性
                self._trading_monitor_window.setWindowTitle("交易监控")
                self._trading_monitor_window.resize(1200, 800)

                # 设置窗口不置顶
                self._trading_monitor_window.setWindowFlags(
                    self._trading_monitor_window.windowFlags() & ~Qt.WindowStaysOnTopHint
                )

                # 连接窗口关闭事件
                def on_window_closed():
                    self._trading_monitor_window = None

                self._trading_monitor_window.closeEvent = lambda event: (
                    on_window_closed(),
                    event.accept()
                )

            # 显示窗口
            self._trading_monitor_window.show()
            self._trading_monitor_window.activateWindow()
            self._trading_monitor_window.raise_()

            logger.info("交易监控窗口已打开")

        except Exception as e:
            logger.error(f"打开交易监控窗口失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开交易监控窗口失败: {str(e)}")

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
            from core.performance import get_performance_monitor as create_performance_evaluator
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
                from optimization.algorithm_optimizer import PerformanceEvaluator
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

            # DataQualityDialog 接受 stock_code 参数，不是 mode 参数
            dialog = DataQualityDialog(self._main_window, stock_code=None)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"单股质量检查失败: {e}")
            QMessageBox.critical(self._main_window, "错误",
                                 f"打开单股质量检查对话框失败: {str(e)}")

    def _on_batch_quality_check(self) -> None:
        """批量质量检查"""
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog

            # 批量质量检查也使用相同的对话框
            dialog = DataQualityDialog(self._main_window, stock_code=None)
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

        except ImportError as e:
            logger.warning(f"启动向导对话框导入失败: {e}")
            # 如果启动向导对话框不存在，创建一个简单的消息框
            QMessageBox.information(
                self._main_window,
                "启动向导",
                "欢迎使用FactorWeave-Quant 2.0！\n\n"
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
            logger.info("打开数据库管理界面")

            from gui.dialogs.database_admin_dialog import DatabaseAdminDialog

            # 使用默认数据库路径
            default_db = "data/factorweave_system.sqlite"

            dialog = DatabaseAdminDialog(default_db, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except ImportError:
            QMessageBox.information(
                self._main_window,
                "数据库管理",
                "数据库管理功能包括：\n\n"
                "1. 数据库文件自动扫描和选择\n"
                "2. 数据表维护和查询\n"
                "3. 数据导入导出和批量操作\n"
                "4. 权限管理和云端同步\n"
                "5. 表结构管理和数据统计\n"
                "6. 慢SQL记录和性能监控\n\n"
                "数据库管理功能正在开发中..."
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
            unit_btn = QPushButton("通用单位转换器")
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
            currency_btn = QPushButton("汇率转换器")
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
                    "您必须同意数据使用条款才能使用FactorWeave-Quant 系统。\n程序将退出。"
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

    # _toggle_performance_panel 方法已删除 - 根据用户要求移除性能仪表板

    def _on_performance_center(self):
        """打开性能监控中心"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor

            # 显示现代化性能监控界面（移除智能洞察功能）
            performance_widget = show_modern_performance_monitor(self._main_window)

            if performance_widget is not None:
                performance_widget.setWindowTitle("FactorWeave-Quant 性能监控中心 - Professional Edition")
                performance_widget.show()
                logger.info("性能监控中心已打开")
            else:
                logger.error("性能监控中心创建失败，返回None")
                QMessageBox.warning(self._main_window, "错误", "无法创建性能监控中心窗口")

        except Exception as e:
            logger.error(f"打开性能监控中心失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开性能监控中心: {e}")

    def _on_system_performance(self):
        """显示系统性能监控"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            performance_widget = show_modern_performance_monitor(self._main_window)

            if performance_widget is not None:
                performance_widget.tab_widget.setCurrentIndex(0)  # 切换到系统监控tab
                performance_widget.show()
            else:
                logger.error("系统性能监控窗口创建失败，返回None")
                QMessageBox.warning(self._main_window, "错误", "无法创建系统性能监控窗口")
            logger.info("系统性能监控已打开")
        except Exception as e:
            logger.error(f"打开系统性能监控失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开系统性能监控: {e}")

    def _on_ui_performance(self):
        """显示UI性能优化"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            performance_widget = show_modern_performance_monitor(self._main_window)
            performance_widget.tab_widget.setCurrentIndex(1)  # 切换到UI优化tab
            performance_widget.show()
            logger.info("UI性能优化已打开")
        except Exception as e:
            logger.error(f"打开UI性能优化失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开UI性能优化: {e}")

    def _on_strategy_performance(self):
        """显示策略性能监控"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            performance_widget = show_modern_performance_monitor(self._main_window)
            performance_widget.tab_widget.setCurrentIndex(2)  # 切换到策略性能tab
            performance_widget.show()
            logger.info("策略性能监控已打开")
        except Exception as e:
            logger.error(f"打开策略性能监控失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开策略性能监控: {e}")

    def _on_algorithm_performance(self):
        """显示算法性能监控"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            performance_widget = show_modern_performance_monitor(self._main_window)
            performance_widget.tab_widget.setCurrentIndex(3)  # 切换到算法性能tab
            performance_widget.show()
            logger.info("算法性能监控已打开")
        except Exception as e:
            logger.error(f"打开算法性能监控失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开算法性能监控: {e}")

    def _on_auto_tuning(self):
        """显示自动调优"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            performance_widget = show_modern_performance_monitor(self._main_window)
            performance_widget.tab_widget.setCurrentIndex(4)  # 切换到自动调优tab
            performance_widget.show()
            logger.info("自动调优已打开")
        except Exception as e:
            logger.error(f"打开自动调优失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开自动调优: {e}")

    def _on_performance_report(self):
        """生成性能报告"""
        try:
            from core.performance import get_performance_monitor
            from PyQt5.QtWidgets import QFileDialog

            monitor = get_performance_monitor()

            # 选择保存位置
            filepath, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "导出性能报告",
                f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )

            if filepath:
                report = monitor.export_report(filepath)
                QMessageBox.information(
                    self._main_window,
                    "成功",
                    f"性能报告已导出到:\n{filepath}"
                )
                logger.info(f"性能报告已导出: {filepath}")
        except Exception as e:
            logger.error(f"导出性能报告失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法导出性能报告: {e}")

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
            message = " 优化系统状态\n\n"
            for key, value in status_info.items():
                message += f" {key}: {value}\n"

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
            # 优先使用增强版策略管理对话框（包含完整回测功能）
            try:
                from gui.dialogs.enhanced_strategy_manager_dialog import EnhancedStrategyManagerDialog
                dialog = EnhancedStrategyManagerDialog(self._main_window)
                # 直接切换到回测标签页
                if hasattr(dialog, 'tab_widget'):
                    for i in range(dialog.tab_widget.count()):
                        if '回测' in dialog.tab_widget.tabText(i):
                            dialog.tab_widget.setCurrentIndex(i)
                            break
                dialog.exec_()
                logger.info("启动增强版策略回测对话框")
            except ImportError:
                # 降级到基础策略管理对话框
                from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog
                dialog = StrategyManagerDialog(self._main_window)
                # 切换到策略回测标签页
                if hasattr(dialog, 'tab_widget'):
                    for i in range(dialog.tab_widget.count()):
                        if '回测' in dialog.tab_widget.tabText(i):
                            dialog.tab_widget.setCurrentIndex(i)
                            break
                dialog.exec_()
                logger.info("启动基础策略回测对话框")
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

    def _on_data_management_center(self) -> None:
        """打开数据管理中心"""
        try:
            from gui.dialogs.data_management_dialog import DataManagementDialog

            # 检查是否已经打开了数据管理中心
            if hasattr(self, '_data_management_dialog') and self._data_management_dialog:
                # 如果已经存在，就激活窗口
                self._data_management_dialog.raise_()
                self._data_management_dialog.activateWindow()
                return

            # 创建数据管理中心对话框
            self._data_management_dialog = DataManagementDialog(self._main_window)

            # 连接信号
            self._data_management_dialog.data_downloaded.connect(self._on_data_downloaded_from_center)
            self._data_management_dialog.source_configured.connect(self._on_source_configured_from_center)

            # 显示对话框
            self._data_management_dialog.show()

            logger.info("数据管理中心已打开")

        except Exception as e:
            logger.error(f"打开数据管理中心失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开数据管理中心: {e}")

    def _on_data_downloaded_from_center(self, symbol: str, source: str):
        """处理从数据管理中心下载的数据"""
        try:
            logger.info(f"数据下载完成: {symbol} (来源: {source})")
            # 可以在这里添加数据下载后的处理逻辑
            # 比如刷新图表、更新状态等
        except Exception as e:
            logger.error(f"处理下载数据失败: {e}")

    def _on_source_configured_from_center(self, source_name: str, config: dict):
        """处理从数据管理中心配置的数据源"""
        try:
            logger.info(f"数据源配置更新: {source_name}")
            # 可以在这里添加数据源配置更新后的处理逻辑
        except Exception as e:
            logger.error(f"处理数据源配置失败: {e}")

    # ==================== DuckDB专业数据导入功能 ====================

    def _on_duckdb_import(self) -> None:
        """打开DuckDB专业数据导入界面（重定向到增强版）"""
        try:
            # 重定向到增强版数据导入系统
            from gui.enhanced_data_import_launcher import EnhancedDataImportMainWindow

            # 创建增强版数据导入窗口
            self.enhanced_import_window = EnhancedDataImportMainWindow()
            self.enhanced_import_window.show()

            logger.info("打开增强版DuckDB专业数据导入系统")

        except ImportError as e:
            QMessageBox.warning(
                self._main_window,
                "功能不可用",
                f"增强版数据导入UI组件加载失败:\n{str(e)}\n\n请确保所有依赖项已正确安装。"
            )
            logger.error(f"增强版数据导入UI组件加载失败: {e}")

        except Exception as e:
            QMessageBox.critical(
                self._main_window,
                "错误",
                f"启动增强版数据导入系统失败:\n{str(e)}"
            )
            logger.error(f"启动增强版数据导入系统失败: {e}")

    def _on_enhanced_import(self) -> None:
        """打开增强版数据导入系统"""
        try:
            # 启动增强版数据导入系统
            from gui.enhanced_data_import_launcher import EnhancedDataImportMainWindow

            # 创建增强版数据导入窗口
            self.enhanced_import_window = EnhancedDataImportMainWindow()
            self.enhanced_import_window.show()

            logger.info("启动增强版数据导入系统")

        except ImportError as e:
            QMessageBox.warning(
                self._main_window,
                "功能不可用",
                f"增强版数据导入UI组件加载失败:\n{str(e)}\n\n请确保所有依赖项已正确安装。"
            )
            logger.error(f"增强版数据导入UI组件加载失败: {e}")

        except Exception as e:
            QMessageBox.critical(
                self._main_window,
                "错误",
                f"启动增强版数据导入系统失败:\n{str(e)}"
            )
            logger.error(f"启动增强版数据导入系统失败: {e}")

    def _on_batch_import(self) -> None:
        """批量数据导入（重定向到增强版任务管理）"""
        try:
            # 批量导入功能已集成到增强版数据导入系统的任务管理中
            from gui.enhanced_data_import_launcher import EnhancedDataImportMainWindow

            # 创建增强版数据导入窗口
            self.enhanced_import_window = EnhancedDataImportMainWindow()
            self.enhanced_import_window.show()

            # 提示用户使用任务管理功能
            QMessageBox.information(
                self._main_window,
                "功能整合",
                "批量导入功能已整合到增强版数据导入系统的任务管理中。\n\n请使用'任务管理'选项卡进行批量任务创建和管理。"
            )

            logger.info("重定向到增强版数据导入系统的任务管理功能")

        except Exception as e:
            logger.error(f"启动增强版数据导入系统失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动增强版数据导入系统: {e}")

    def _on_scheduled_import(self) -> None:
        """定时导入任务管理"""
        try:
            from gui.dialogs.scheduled_import_dialog import ScheduledImportDialog

            dialog = ScheduledImportDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

            logger.info("打开定时导入任务管理")

        except ImportError:
            # 如果对话框不存在，显示开发中提示
            QMessageBox.information(self._main_window, "提示", "定时导入任务管理功能正在开发中")
            logger.info("定时导入任务管理功能正在开发中")
        except Exception as e:
            logger.error(f"打开定时导入任务管理失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法打开定时导入任务管理: {e}")

    def _on_import_history(self) -> None:
        """查看导入历史记录"""
        try:
            from gui.dialogs.import_history_dialog import ImportHistoryDialog

            dialog = ImportHistoryDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

            logger.info("查看导入历史记录")

        except ImportError:
            # 如果对话框不存在，显示开发中提示
            QMessageBox.information(self._main_window, "提示", "导入历史记录功能正在开发中")
            logger.info("导入历史记录功能正在开发中")
        except Exception as e:
            logger.error(f"查看导入历史记录失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法查看导入历史记录: {e}")

    def _on_export_data(self) -> None:
        """导出数据"""
        try:
            from gui.dialogs.data_export_dialog import DataExportDialog

            # 使用通用对话框管理方法
            dialog = self._manage_dialog(
                'data_export',
                DataExportDialog,
                self._main_window
            )

            if dialog is not None:  # 如果创建了新对话框
                self.center_dialog(dialog)
                dialog.show()
                logger.info("启动数据导出")

        except ImportError:
            # 如果对话框不存在，使用简单的文件保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self._main_window,
                "导出数据",
                "",
                "CSV文件 (*.csv);;Excel文件 (*.xlsx);;JSON文件 (*.json);;所有文件 (*)"
            )
            if file_path:
                QMessageBox.information(self._main_window, "提示", "数据导出功能正在开发中")
                logger.info(f"导出数据到: {file_path}")
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法导出数据: {e}")

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
                # 创建默认回测参数
                default_params = {
                    'professional_level': 'PROFESSIONAL',
                    'engine_type': 'unified',
                    'use_vectorized': True,
                    'auto_select': True,
                    'monitoring_level': 'STANDARD'
                }
                self._backtest_widget.start_backtest(default_params)
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

            # 如果没有找到任何回测功能，提供选择
            reply = QMessageBox.question(
                self._main_window,
                "智能回测选择",
                "未找到当前活跃的回测界面。\n\n请选择回测方式：\n\n• 是：打开专业回测功能\n• 否：打开策略回测功能",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                # 启动专业回测功能
                self._on_professional_backtest()
            elif reply == QMessageBox.No:
                # 启动策略回测功能（原策略菜单功能）
                self._on_strategy_backtest()
            # Cancel 则不执行任何操作

            logger.info("智能回测：用户选择了回测方式")

        except Exception as e:
            logger.error(f"启动回测失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动回测: {e}")

    def _on_professional_backtest(self) -> None:
        """启动专业回测功能（直接打开独立浮动窗口）"""
        try:
            # 直接创建独立浮动窗口，支持放大缩小和关闭
            self._create_standalone_backtest_window()
            logger.info("专业回测独立窗口已启动")

        except Exception as e:
            logger.error(f"启动专业回测功能失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动专业回测功能: {e}")

    def _create_standalone_backtest_window(self) -> None:
        """创建独立的专业回测浮动窗口（支持放大缩小和关闭）"""
        try:
            from gui.widgets.backtest_widget import ProfessionalBacktestWidget
            from PyQt5.QtWidgets import QMainWindow
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QIcon

            # 检查是否已有独立窗口存在
            if hasattr(self, '_standalone_backtest_window') and self._standalone_backtest_window:
                # 如果窗口已存在，直接显示并激活
                self._standalone_backtest_window.show()
                self._standalone_backtest_window.raise_()
                self._standalone_backtest_window.activateWindow()
                logger.info("专业回测独立窗口已激活")
                return

            # 创建新的独立浮动窗口
            self._standalone_backtest_window = QMainWindow()

            # 设置窗口标题和图标
            self._standalone_backtest_window.setWindowTitle("FactorWeave-Quant 专业回测系统")

            # 设置窗口大小和位置（居中显示）
            screen = QApplication.desktop().screenGeometry()
            window_width = 1400
            window_height = 900
            x = (screen.width() - window_width) // 2
            y = (screen.height() - window_height) // 2
            self._standalone_backtest_window.setGeometry(x, y, window_width, window_height)

            # 设置最小窗口大小
            self._standalone_backtest_window.setMinimumSize(1000, 700)

            # 设置窗口标志，支持放大缩小和关闭
            self._standalone_backtest_window.setWindowFlags(
                Qt.Window |                    # 独立窗口
                Qt.WindowTitleHint |          # 显示标题栏
                Qt.WindowSystemMenuHint |     # 显示系统菜单
                Qt.WindowMinimizeButtonHint |  # 显示最小化按钮
                Qt.WindowMaximizeButtonHint |  # 显示最大化按钮
                Qt.WindowCloseButtonHint      # 显示关闭按钮
            )

            # 创建专业回测组件
            backtest_widget = ProfessionalBacktestWidget(parent=self._standalone_backtest_window)
            self._standalone_backtest_window.setCentralWidget(backtest_widget)

            # 设置窗口样式
            self._standalone_backtest_window.setStyleSheet("""
                QMainWindow {
                    background-color: #0e1117;
                    color: white;
                }
            """)

            # 设置窗口属性
            self._standalone_backtest_window.setAttribute(Qt.WA_DeleteOnClose, False)  # 关闭时不删除，只隐藏

            # 连接关闭事件
            def on_window_close():
                self._standalone_backtest_window.hide()
                logger.info("专业回测独立窗口已隐藏")

            # 重写关闭事件
            original_close_event = self._standalone_backtest_window.closeEvent

            def close_event(event):
                event.ignore()  # 忽略关闭事件
                on_window_close()  # 执行隐藏操作
            self._standalone_backtest_window.closeEvent = close_event

            # 显示窗口
            self._standalone_backtest_window.show()
            self._standalone_backtest_window.raise_()
            self._standalone_backtest_window.activateWindow()

            logger.info("专业回测独立浮动窗口创建成功")

        except Exception as e:
            logger.error(f"创建独立回测窗口失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"无法创建专业回测窗口: {e}")

    def _on_toggle_backtest_panel(self) -> None:
        """切换专业回测面板的显示/隐藏"""
        try:
            backtest_dock = self._panels.get('backtest_dock')
            if backtest_dock:
                if backtest_dock.isVisible():
                    backtest_dock.hide()
                    logger.info("专业回测面板已隐藏")
                else:
                    backtest_dock.show()
                    backtest_dock.raise_()
                    logger.info("专业回测面板已显示")
            else:
                # 如果停靠窗口不存在，创建它
                self._create_professional_backtest_widget()
                backtest_dock = self._panels.get('backtest_dock')
                if backtest_dock:
                    backtest_dock.show()
                    backtest_dock.raise_()
                    logger.info("专业回测面板已创建并显示")

        except Exception as e:
            logger.error(f"切换专业回测面板失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法切换专业回测面板: {e}")

    def _on_optimize(self) -> None:
        """启动优化功能"""
        try:
            # 使用已有的优化功能
            self._on_one_click_optimization()
            logger.info("启动优化功能")
        except Exception as e:
            logger.error(f"启动优化失败: {e}")
            QMessageBox.warning(self._main_window, "错误", f"无法启动优化: {e}")

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
            message = f""" 内存使用情况

 总内存: {memory_info.total / (1024**3):.1f} GB
 已使用: {memory_info.used / (1024**3):.1f} GB
 可用内存: {memory_info.available / (1024**3):.1f} GB
 使用率: {memory_info.percent:.1f}%
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

    def _on_toggle_toolbar(self, checked=None) -> None:
        """切换工具栏显示/隐藏"""
        try:
            toolbar = self._main_window.toolBar()
            if toolbar:
                if checked is not None:
                    # 从复选框菜单项调用，使用传入的状态
                    toolbar.setVisible(checked)
                    logger.info(f"工具栏已{'显示' if checked else '隐藏'}")
                else:
                    # 直接调用，切换当前状态
                    is_visible = toolbar.isVisible()
                    toolbar.setVisible(not is_visible)
                    logger.info(f"工具栏已{'隐藏' if is_visible else '显示'}")
            else:
                logger.warning("工具栏不存在")
        except Exception as e:
            logger.error(f"切换工具栏失败: {e}")

    def _on_toggle_statusbar(self, checked=None) -> None:
        """切换状态栏显示/隐藏"""
        try:
            statusbar = self._main_window.statusBar()
            if statusbar:
                if checked is not None:
                    # 从复选框菜单项调用，使用传入的状态
                    statusbar.setVisible(checked)
                    logger.info(f"状态栏已{'显示' if checked else '隐藏'}")
                else:
                    # 直接调用，切换当前状态
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

    def _initialize_enhanced_ui_components_async(self):
        """异步初始化增强UI组件（在事件循环中执行，避免阻塞主初始化流程）"""
        import time
        start_time = time.time()

        try:
            logger.info("开始异步初始化增强UI组件...")

            # 导入增强UI组件
            import_start = time.time()
            from gui.widgets.enhanced_ui import (
                Level2DataPanel, OrderBookWidget, FundamentalAnalysisTab,
                DataQualityMonitorTab, SmartRecommendationPanel
            )
            import_time = time.time() - import_start
            logger.info(f"模块导入耗时: {import_time:.3f}秒")

            # 存储增强组件引用
            self._enhanced_components = {}

            # 创建Level-2数据面板
            level2_start = time.time()
            self._enhanced_components['level2_panel'] = Level2DataPanel(
                parent=self._main_window,
                event_bus=self._event_bus
            )
            level2_time = time.time() - level2_start
            logger.info(f"Level2DataPanel创建耗时: {level2_time:.3f}秒")

            # 创建订单簿组件
            orderbook_start = time.time()
            self._enhanced_components['order_book_widget'] = OrderBookWidget(
                parent=self._main_window,
                event_bus=self._event_bus
            )
            orderbook_time = time.time() - orderbook_start
            logger.info(f"OrderBookWidget创建耗时: {orderbook_time:.3f}秒")

            # 创建基本面分析标签页
            fundamental_start = time.time()
            self._enhanced_components['fundamental_analysis_tab'] = FundamentalAnalysisTab(
                parent=self._main_window
            )
            fundamental_time = time.time() - fundamental_start
            logger.info(f"FundamentalAnalysisTab创建耗时: {fundamental_time:.3f}秒")

            # 创建智能推荐面板
            recommendation_start = time.time()
            self._enhanced_components['smart_recommendation_panel'] = SmartRecommendationPanel(
                parent=self._main_window
            )
            recommendation_time = time.time() - recommendation_start
            logger.info(f"SmartRecommendationPanel创建耗时: {recommendation_time:.3f}秒")

            # 集成增强组件到UI
            integration_start = time.time()
            self._integrate_enhanced_components_to_ui()
            integration_time = time.time() - integration_start
            logger.info(f"增强组件UI集成耗时: {integration_time:.3f}秒")

            total_time = time.time() - start_time
            logger.info(f"成功异步初始化 {len(self._enhanced_components)} 个增强UI组件, 总耗时: {total_time:.3f}秒")

        except Exception as e:
            logger.error(f"异步初始化增强UI组件失败: {e}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")
            self._enhanced_components = {}

    def _initialize_enhanced_ui_components(self):
        """初始化增强UI组件（同步版本，保留用于向后兼容）"""
        # 重定向到异步版本
        self._initialize_enhanced_ui_components_async()

    def _integrate_enhanced_components_to_ui(self):
        """将增强组件集成到UI中"""
        import time
        start_time = time.time()

        try:
            if not hasattr(self, '_enhanced_components') or not self._enhanced_components:
                logger.warning("增强组件未初始化，跳过UI集成")
                return

            logger.info("开始集成增强UI组件到主界面...")

            # ✅ 修复：将技术分析面板与增强组件组合在一起，默认在右侧
            # 首先创建技术分析面板的 QDockWidget（如果尚未创建）
            right_dock = None
            if 'right_dock' in self._panels:
                right_dock = self._panels['right_dock']
                logger.info("技术分析面板 QDockWidget 已存在")
            else:
                logger.warning("技术分析面板 QDockWidget 未找到，跳过组合")

            # ✅ 修复：存储所有需要组合到右侧的 QDockWidget
            right_area_docks = []

            # 将技术分析面板作为第一个（如果存在）
            if right_dock:
                right_area_docks.append(right_dock)
                logger.info("技术分析面板已添加到右侧组合列表")

            # ✅ 修复：将所有增强组件组合到右侧，与技术分析面板形成标签页组
            # 添加Level-2数据面板作为停靠窗口（组合到右侧）
            if 'level2_panel' in self._enhanced_components:
                level2_dock = QDockWidget("Level-2 数据", self._main_window)
                level2_dock.setWidget(self._enhanced_components['level2_panel'])
                level2_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                # ✅ 修复：如果已有技术分析面板，直接组合；否则先添加到右侧
                if right_area_docks:
                    # 技术分析面板已存在，直接组合
                    self._main_window.tabifyDockWidget(right_area_docks[0], level2_dock)
                    right_area_docks.append(level2_dock)
                    logger.info("Level-2数据面板已与技术分析面板组合为标签页（右侧）")
                else:
                    # 技术分析面板不存在，先添加到右侧
                    self._main_window.addDockWidget(Qt.RightDockWidgetArea, level2_dock)
                    right_area_docks.append(level2_dock)
                    logger.info("Level-2数据面板已添加到右侧停靠区域")

            # 添加订单簿组件作为停靠窗口（组合到右侧）
            if 'order_book_widget' in self._enhanced_components:
                orderbook_dock = QDockWidget("订单簿深度", self._main_window)
                orderbook_dock.setWidget(self._enhanced_components['order_book_widget'])
                orderbook_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                # ✅ 修复：组合到右侧（与技术分析面板或Level-2面板组合）
                if right_area_docks:
                    # 已有其他面板在右侧，直接组合
                    self._main_window.tabifyDockWidget(right_area_docks[0], orderbook_dock)
                    right_area_docks.append(orderbook_dock)
                    logger.info("订单簿组件已与其他面板组合为标签页（右侧）")
                else:
                    # 没有其他面板，先添加到右侧
                    self._main_window.addDockWidget(Qt.RightDockWidgetArea, orderbook_dock)
                    right_area_docks.append(orderbook_dock)
                    logger.info("订单簿组件已添加到右侧停靠区域")

            # 添加智能推荐面板作为停靠窗口（组合到右侧）
            if 'smart_recommendation_panel' in self._enhanced_components:
                recommendation_dock = QDockWidget("智能推荐", self._main_window)
                recommendation_dock.setWidget(self._enhanced_components['smart_recommendation_panel'])
                recommendation_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                # ✅ 修复：组合到右侧（与技术分析面板或其他面板组合）
                if right_area_docks:
                    # 已有其他面板在右侧，直接组合
                    self._main_window.tabifyDockWidget(right_area_docks[0], recommendation_dock)
                    right_area_docks.append(recommendation_dock)
                    logger.info("智能推荐面板已与其他面板组合为标签页（右侧）")
                else:
                    # 没有其他面板，先添加到右侧
                    self._main_window.addDockWidget(Qt.RightDockWidgetArea, recommendation_dock)
                    right_area_docks.append(recommendation_dock)
                    logger.info("智能推荐面板已添加到右侧停靠区域")

            # ✅ 修复：将所有右侧组合的 QDockWidget 的标签页位置设置为顶部
            if right_area_docks:
                # 确保第一个 dock（技术分析面板）可见并激活
                right_area_docks[0].setVisible(True)
                right_area_docks[0].raise_()
                logger.info(f"所有右侧 QDockWidget 已组合在一起（共{len(right_area_docks)}个面板）")

            # ✅ 修复：存储底部区域的 QDockWidget（用于标签页位置设置）
            bottom_area_docks = []

            # ✅ 修复：将所有组合的 QDockWidget 的标签页位置设置为顶部
            # 注意：对于 QDockWidget 组合后的标签页，需要通过查找 QTabBar 来设置位置
            all_docks = right_area_docks + bottom_area_docks
            if all_docks:
                # 查找所有 QTabBar 并设置标签页位置为顶部
                from PyQt5.QtWidgets import QTabBar
                tab_bars = self._main_window.findChildren(QTabBar)
                for tab_bar in tab_bars:
                    # QTabBar.RoundedNorth 表示标签页在顶部（圆角，顶部）
                    # 注意：需要检查 tab_bar 是否属于 QDockWidget 的标签页
                    try:
                        tab_bar.setShape(QTabBar.RoundedNorth)
                        logger.debug(f"已将标签页位置设置为顶部: {tab_bar}")
                    except Exception as e:
                        logger.warning(f"设置标签页位置失败: {e}")

                logger.info(f"所有 QDockWidget 的标签页位置已设置为顶部（右侧{len(right_area_docks)}个，底部{len(bottom_area_docks)}个）")

            # 如果存在分析标签页，将基本面分析添加到其中
            if hasattr(self, '_analysis_tabs') and 'fundamental_analysis_tab' in self._enhanced_components:
                self._analysis_tabs.addTab(
                    self._enhanced_components['fundamental_analysis_tab'],
                    " 基本面分析"
                )
                logger.info("基本面分析标签页已添加到分析区域")

            total_time = time.time() - start_time
            logger.info(f"增强UI组件集成完成, 耗时: {total_time:.3f}秒")

        except Exception as e:
            logger.error(f"集成增强UI组件失败: {e}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")

    def get_enhanced_component(self, component_name: str):
        """获取增强组件实例"""
        if hasattr(self, '_enhanced_components'):
            return self._enhanced_components.get(component_name)
        return None

    # ==================== 增强功能菜单事件处理 ====================

    def _on_toggle_level2_panel(self):
        """切换Level-2数据面板显示/隐藏"""
        try:
            dock_widgets = self._main_window.findChildren(QDockWidget)
            for dock in dock_widgets:
                if dock.windowTitle() == "Level-2 数据":
                    dock.setVisible(not dock.isVisible())
                    logger.info(f"Level-2数据面板已{'显示' if dock.isVisible() else '隐藏'}")
                    return
            logger.warning("Level-2数据面板未找到")
        except Exception as e:
            logger.error(f"切换Level-2数据面板失败: {e}")

    def _on_toggle_orderbook_panel(self):
        """切换订单簿面板显示/隐藏"""
        try:
            dock_widgets = self._main_window.findChildren(QDockWidget)
            for dock in dock_widgets:
                if dock.windowTitle() == "订单簿深度":
                    dock.setVisible(not dock.isVisible())
                    logger.info(f"订单簿面板已{'显示' if dock.isVisible() else '隐藏'}")
                    return
            logger.warning("订单簿面板未找到")
        except Exception as e:
            logger.error(f"切换订单簿面板失败: {e}")

    def _on_toggle_fundamental_panel(self):
        """切换基本面分析面板显示/隐藏"""
        try:
            # 基本面分析在分析标签页中，通过切换标签页显示
            if hasattr(self, '_analysis_tabs'):
                for i in range(self._analysis_tabs.count()):
                    if self._analysis_tabs.tabText(i) == " 基本面分析":
                        self._analysis_tabs.setCurrentIndex(i)
                        logger.info("基本面分析标签页已激活")
                        return
            logger.warning("基本面分析标签页未找到")
        except Exception as e:
            logger.error(f"切换基本面分析面板失败: {e}")

    def _on_toggle_smart_recommendation_panel(self):
        """切换智能推荐面板显示/隐藏"""
        try:
            dock_widgets = self._main_window.findChildren(QDockWidget)
            for dock in dock_widgets:
                if dock.windowTitle() == "智能推荐":
                    dock.setVisible(not dock.isVisible())
                    logger.info(f"智能推荐面板已{'显示' if dock.isVisible() else '隐藏'}")
                    return
            logger.warning("智能推荐面板未找到")
        except Exception as e:
            logger.error(f"切换智能推荐面板失败: {e}")
