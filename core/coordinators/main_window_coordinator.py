"""
主窗口协调器

负责协调主窗口的所有UI面板和业务服务的交互。
这是整个应用的中央协调器，替代原来的TradingGUI类。
"""

import logging
from typing import Dict, Any, Optional, List

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon

from .base_coordinator import BaseCoordinator
from ..events import (
    EventBus, StockSelectedEvent, ChartUpdateEvent, AnalysisCompleteEvent,
    DataUpdateEvent, ErrorEvent, UIUpdateEvent, ThemeChangedEvent
)
from ..containers import ServiceContainer
from ..services import (
    StockService, ChartService, AnalysisService,
    ThemeService, ConfigService
)

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
        self._main_window.setWindowTitle("HIkyuu-UI 2.0 股票分析系统")
        self._main_window.setGeometry(100, 100, 1400, 900)
        self._main_window.setMinimumSize(1200, 800)

        # UI面板
        self._panels: Dict[str, Any] = {}

        # 窗口状态
        self._window_state = {
            'title': 'HIkyuu-UI 2.0 股票分析系统',
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

    def _do_initialize(self) -> None:
        """初始化协调器"""
        try:
            # 获取服务
            self._stock_service = self.service_container.resolve(StockService)
            self._chart_service = self.service_container.resolve(ChartService)
            self._analysis_service = self.service_container.resolve(AnalysisService)
            self._theme_service = self.service_container.resolve(ThemeService)
            self._config_service = self.service_container.resolve(ConfigService)

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
            self._status_bar.showMessage("就绪")

            # 设置菜单栏
            self._menu_bar = QMenuBar()
            self._main_window.setMenuBar(self._menu_bar)
            self._create_menu_bar()

            logger.info("Main window setup completed")

        except Exception as e:
            logger.error(f"Failed to setup main window: {e}")
            raise

    def _create_menu_bar(self) -> None:
        """创建菜单栏"""
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
            theme_menu.addAction('默认主题', lambda: self._on_theme_changed('default'))
            theme_menu.addAction('深色主题', lambda: self._on_theme_changed('dark'))
            theme_menu.addAction('浅色主题', lambda: self._on_theme_changed('light'))

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
            optimization_menu.addAction('优化仪表板', self._on_optimization_dashboard)
            optimization_menu.addAction('一键优化', self._on_one_click_optimization)
            optimization_menu.addAction('智能优化', self._on_intelligent_optimization)
            optimization_menu.addAction('性能评估', self._on_performance_evaluation)
            optimization_menu.addAction('版本管理', self._on_version_management)

            # 数据质量检查子菜单
            quality_menu = advanced_menu.addMenu('数据质量检查')
            quality_menu.addAction('单股质量检查', self._on_single_stock_quality_check)
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
        """创建UI面板"""
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
                parent=self._main_window,
                coordinator=self,
                stock_service=self._stock_service,
                width=self._layout_config['left_panel_width']
            )
            left_panel._root_frame.setMinimumWidth(self._layout_config['left_panel_width'])
            left_panel._root_frame.setMaximumWidth(400)
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
            right_panel._root_frame.setMinimumWidth(self._layout_config['right_panel_width'])
            right_panel._root_frame.setMaximumWidth(450)
            horizontal_splitter.addWidget(right_panel._root_frame)
            self._panels['right'] = right_panel

            # 设置分割器比例
            horizontal_splitter.setSizes([300, 700, 350])

            # 创建底部面板（日志显示面板）
            from core.ui.panels import BottomPanel
            bottom_panel = BottomPanel(
                parent=self._main_window,
                coordinator=self
            )
            vertical_splitter.addWidget(bottom_panel._root_frame)
            self._panels['bottom'] = bottom_panel

            # 设置垂直分割器比例（主面板区域 80%, 底部面板 20%）
            vertical_splitter.setSizes([600, 150])

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

            logger.debug("Panel signals connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect panel signals: {e}")
            raise

    def _setup_layout(self) -> None:
        """设置布局"""
        # 布局已在_create_panels中设置
        pass

    def _register_event_handlers(self) -> None:
        """注册事件处理器"""
        try:
            # 注册股票选择事件处理器
            self.event_bus.subscribe(StockSelectedEvent, self._on_stock_selected)

            # 注册图表更新事件处理器
            self.event_bus.subscribe(ChartUpdateEvent, self._on_chart_updated)

            # 注册分析完成事件处理器
            self.event_bus.subscribe(AnalysisCompleteEvent, self._on_analysis_completed)

            # 注册数据更新事件处理器
            self.event_bus.subscribe(DataUpdateEvent, self._on_data_update)

            # 注册错误事件处理器
            self.event_bus.subscribe(ErrorEvent, self._on_error)

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

    def _on_stock_selected(self, event) -> None:
        """处理股票选择事件"""
        try:
            stock_code = getattr(event, 'stock_code', '')
            stock_name = getattr(event, 'stock_name', '')

            logger.info(f"Stock selected: {stock_code} - {stock_name}")

            # 通知中间面板更新图表
            middle_panel = self._panels.get('middle')
            if middle_panel and hasattr(middle_panel, 'load_stock_chart'):
                middle_panel.load_stock_chart(stock_code, stock_name)

            # 通知右侧面板更新分析
            right_panel = self._panels.get('right')
            if right_panel and hasattr(right_panel, 'load_stock_analysis'):
                right_panel.load_stock_analysis(stock_code, stock_name)

        except Exception as e:
            logger.error(f"Failed to handle stock selection: {e}")

    def _on_chart_updated(self, event) -> None:
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

    def _on_data_update(self, event: DataUpdateEvent) -> None:
        """处理数据更新事件"""
        try:
            logger.info(f"Data update: {event.data_type}")

            # 更新状态栏
            self._status_bar.showMessage(f"数据已更新: {event.data_type}")

        except Exception as e:
            logger.error(f"Failed to handle data update event: {e}")

    def _on_error(self, event: ErrorEvent) -> None:
        """处理错误事件"""
        try:
            logger.error(f"Error occurred: {event.error_type} - {event.error_message}")

            # 显示错误消息
            if event.severity == 'error':
                QMessageBox.critical(self._main_window, event.error_type, event.error_message)
            elif event.severity == 'warning':
                QMessageBox.warning(self._main_window, event.error_type, event.error_message)
            else:
                QMessageBox.information(self._main_window, event.error_type, event.error_message)

            # 更新状态栏
            self._status_bar.showMessage(f"错误: {event.error_message}")

        except Exception as e:
            logger.error(f"Failed to handle error event: {e}")

    def _on_theme_changed(self, event: ThemeChangedEvent) -> None:
        """处理主题变更事件"""
        try:
            logger.info(f"Theme changed: {event.theme_name}")

            # 重新应用主题
            self._apply_theme()

            # 更新状态栏
            self._status_bar.showMessage(f"主题已更改: {event.theme_name}")

        except Exception as e:
            logger.error(f"Failed to handle theme changed event: {e}")

    def get_main_window(self) -> QMainWindow:
        """获取主窗口"""
        return self._main_window

    def get_panel(self, panel_name: str) -> Optional[QWidget]:
        """获取面板"""
        return self._panels.get(panel_name)

    def show_message(self, message: str, level: str = 'info') -> None:
        """显示消息"""
        self._status_bar.showMessage(message)

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

    def _on_theme_changed(self, theme_name: str) -> None:
        """主题变化处理"""
        try:
            theme_service = self.service_container.get_service(ThemeService)
            if theme_service:
                theme_service.set_theme(theme_name)
                self.show_message(f"主题已切换为: {theme_name}")
                logger.info(f"Theme changed to: {theme_name}")

        except Exception as e:
            logger.error(f"Failed to change theme: {e}")
            self.show_message(f"主题切换失败: {e}")

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
            QMessageBox.critical(self._main_window, "错误", f"打开高级搜索失败: {str(e)}")

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
            QMessageBox.critical(self._main_window, "错误", f"打开数据导出对话框失败: {str(e)}")

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
            QMessageBox.critical(self._main_window, "错误", f"打开系统设置对话框失败: {str(e)}")

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
        QMessageBox.information(self._main_window, "快捷键说明", shortcuts_text.strip())

    def _on_about(self) -> None:
        """关于对话框"""
        from PyQt5.QtWidgets import QMessageBox
        about_text = """
HIkyuu-UI 2.0 (重构版本)

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
        QMessageBox.about(self._main_window, "关于 HIkyuu-UI", about_text.strip())

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
            QMessageBox.critical(self._main_window, "错误", f"打开节点管理对话框失败: {str(e)}")

    def _on_cloud_api(self) -> None:
        """云端API管理"""
        try:
            from gui.dialogs.cloud_api_dialog import CloudApiDialog

            dialog = CloudApiDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"云端API管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开云端API管理对话框失败: {str(e)}")

    def _on_plugin_manager(self) -> None:
        """插件管理器"""
        try:
            from gui.dialogs.plugin_manager_dialog import PluginManagerDialog
            from core.plugin_manager import PluginManager

            # 获取插件管理器
            plugin_manager = self._service_container.resolve(PluginManager)

            dialog = PluginManagerDialog(plugin_manager, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"插件管理器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开插件管理器对话框失败: {str(e)}")

    def _on_plugin_market(self) -> None:
        """插件市场"""
        try:
            from gui.dialogs.enhanced_plugin_market_dialog import EnhancedPluginMarketDialog
            from core.plugin_manager import PluginManager

            # 获取插件管理器
            plugin_manager = self._service_container.resolve(PluginManager)

            dialog = EnhancedPluginMarketDialog(plugin_manager, self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"插件市场失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开插件市场对话框失败: {str(e)}")

    def _on_indicator_market(self) -> None:
        """指标市场"""
        try:
            from gui.dialogs.indicator_market_dialog import IndicatorMarketDialog

            dialog = IndicatorMarketDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"指标市场失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开指标市场对话框失败: {str(e)}")

    def _on_batch_analysis(self) -> None:
        """批量分析"""
        try:
            from gui.dialogs.batch_analysis_dialog import BatchAnalysisDialog

            dialog = BatchAnalysisDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开批量分析对话框失败: {str(e)}")

    def _on_strategy_management(self) -> None:
        """策略管理"""
        try:
            from gui.dialogs.strategy_manager_dialog import StrategyManagerDialog

            dialog = StrategyManagerDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"策略管理失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开策略管理对话框失败: {str(e)}")

    def _on_optimization_dashboard(self) -> None:
        """优化仪表板"""
        try:
            from optimization.optimization_dashboard import OptimizationDashboard

            # 创建优化仪表板
            dashboard = OptimizationDashboard()
            dashboard.show()

            logger.info("优化仪表板已打开")

        except Exception as e:
            logger.error(f"打开优化仪表板失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开优化仪表板失败: {str(e)}")

    def _on_one_click_optimization(self) -> None:
        """一键优化"""
        try:
            from PyQt5.QtWidgets import QProgressDialog
            from optimization.auto_tuner import AutoTuner
            from PyQt5.QtCore import QThread, pyqtSignal

            # 创建进度对话框
            progress = QProgressDialog("正在执行一键优化...", "取消", 0, 100, self._main_window)
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
                QMessageBox.critical(self._main_window, "错误", f"一键优化失败: {error}")
                logger.error(f"一键优化失败: {error}")

            def on_canceled():
                optimization_thread.requestInterruption()
                optimization_thread.wait()
                logger.info("一键优化已取消")

            # 创建并启动线程
            optimization_thread = OptimizationThread()
            optimization_thread.progress_updated.connect(on_progress_updated)
            optimization_thread.optimization_completed.connect(on_optimization_completed)
            optimization_thread.error_occurred.connect(on_error_occurred)

            progress.canceled.connect(on_canceled)

            optimization_thread.start()

        except Exception as e:
            logger.error(f"启动一键优化失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"启动一键优化失败: {str(e)}")

    def _on_intelligent_optimization(self) -> None:
        """智能优化"""
        try:
            from PyQt5.QtWidgets import QInputDialog, QProgressDialog
            from optimization.auto_tuner import AutoTuner
            from PyQt5.QtCore import QThread, pyqtSignal

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
            progress = QProgressDialog("正在执行智能优化...", "取消", 0, 100, self._main_window)
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
                QMessageBox.critical(self._main_window, "错误", f"智能优化失败: {error}")
                logger.error(f"智能优化失败: {error}")

            def on_canceled():
                smart_thread.requestInterruption()
                smart_thread.wait()
                logger.info("智能优化已取消")

            # 创建并启动线程
            smart_thread = SmartOptimizationThread(performance_threshold, improvement_target)
            smart_thread.progress_updated.connect(on_progress_updated)
            smart_thread.optimization_completed.connect(on_optimization_completed)
            smart_thread.error_occurred.connect(on_error_occurred)

            progress.canceled.connect(on_canceled)

            smart_thread.start()

        except Exception as e:
            logger.error(f"启动智能优化失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"启动智能优化失败: {str(e)}")

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
                from gui.dialogs.performance_evaluation_dialog import PerformanceEvaluationDialog

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
            QMessageBox.critical(self._main_window, "错误", f"打开版本管理对话框失败: {str(e)}")

    def _on_single_stock_quality_check(self) -> None:
        """单股质量检查"""
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog

            dialog = DataQualityDialog(self._main_window, mode='single')
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"单股质量检查失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开单股质量检查对话框失败: {str(e)}")

    def _on_batch_quality_check(self) -> None:
        """批量质量检查"""
        try:
            from gui.dialogs.data_quality_dialog import DataQualityDialog

            dialog = DataQualityDialog(self._main_window, mode='batch')
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"批量质量检查失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开批量质量检查对话框失败: {str(e)}")

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
            analysis_service = self.service_container.get_service(AnalysisService)
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
                "欢迎使用HIkyuu-UI 2.0！\n\n"
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

            dialog = DatabaseAdminDialog(self._main_window)
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
        """打开单位转换器"""
        try:
            from gui.dialogs.converter_dialog import ConverterDialog

            dialog = ConverterDialog(self._main_window)
            self.center_dialog(dialog)
            dialog.exec_()

        except Exception as e:
            logger.error(f"打开单位转换器失败: {e}")
            QMessageBox.critical(self._main_window, "错误", f"打开单位转换器失败: {e}")

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
            from gui.tools.currency_converter import CurrencyConverter

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
                    "您必须同意数据使用条款才能使用HIkyuu-UI系统。\n程序将退出。"
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
            from gui.dialogs import DataUsageTermsDialog
            DataUsageTermsDialog.show_terms(self._main_window)
        except Exception as e:
            logger.error(f"Failed to show data usage terms: {e}")
            QMessageBox.critical(self._main_window, "错误", f"无法显示数据使用条款: {str(e)}")
