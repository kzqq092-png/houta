"""
中间面板

负责显示K线图、技术指标图表等核心图表功能。
使用统一图表服务提供高性能图表渲染。
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import numpy as np
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QSplitter, QFrame, QProgressBar,
    QMessageBox, QToolBar, QAction, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon

from .base_panel import BasePanel
from core.events import StockSelectedEvent, ChartUpdateEvent, IndicatorChangedEvent
from core.services.unified_chart_service import get_unified_chart_service, create_chart_widget, ChartDataLoader, ChartWidget

logger = logging.getLogger(__name__)

# 导入性能监控
try:
    from monitor_chart_performance import chart_monitor, monitor_chart_load
    PERFORMANCE_MONITORING = True
    logger.info("图表性能监控已启用")
except ImportError:
    PERFORMANCE_MONITORING = False

    def monitor_chart_load(func):
        return func  # 无监控装饰器

if TYPE_CHECKING:
    from core.services import ChartService


# 移除重复的ChartDataLoader，使用统一图表服务中的实现


class ChartCanvas(QWidget):
    """高性能图表画布 - 基于统一图表服务"""

    # 定义信号
    request_stat_dialog = pyqtSignal(tuple)  # (start_idx, end_idx)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 获取统一图表服务
        try:
            self.chart_service = get_unified_chart_service()
        except:
            logger.warning("统一图表服务不可用")
            self.chart_service = None

        # 创建图表控件
        try:
            self.chart_widget = create_chart_widget(parent=self, chart_id="middle_panel_chart")
        except:
            logger.warning("无法创建图表控件")
            self.chart_widget = None
        if self.chart_widget:
            layout.addWidget(self.chart_widget)

            # 连接信号
            self.chart_widget.request_stat_dialog.connect(self.request_stat_dialog.emit)
            self.chart_widget.error_occurred.connect(self._on_chart_error)
        else:
            # 创建错误占位符
            placeholder = QLabel("图表控件创建失败")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #dc3545; font-size: 14px;")
            layout.addWidget(placeholder)

        # 数据
        self.stock_data = None
        self.current_stock = None
        self.current_kdata = None  # 保存当前K线数据

        # 区间选择相关
        self.selection_start = None
        self.selection_end = None
        self.selecting = False

    def _setup_chart(self):
        """设置图表布局 - 使用统一图表服务"""
        # 图表布局由ChartWidget自动管理
        pass

    @monitor_chart_load
    def update_chart(self, stock_data: Dict[str, Any]):
        """更新图表数据 - 使用统一图表服务"""
        try:
            self.stock_data = stock_data
            self.current_stock = stock_data.get('stock_code', '')

            # 获取OHLCV数据 - 支持多种数据格式
            kline_data = stock_data.get('kline_data', stock_data.get('kdata', []))

            # 检查数据是否为空
            import pandas as pd
            if kline_data is None:
                self._show_no_data_message()
                return

            # 处理DataFrame
            if isinstance(kline_data, pd.DataFrame):
                if kline_data.empty:
                    self._show_no_data_message()
                    return
                self.current_kdata = kline_data
            # 处理列表格式
            elif isinstance(kline_data, list):
                if not kline_data:
                    self._show_no_data_message()
                    return
                self.current_kdata = pd.DataFrame(kline_data)
                if not self.current_kdata.empty and 'date' in self.current_kdata.columns:
                    self.current_kdata.set_index('date', inplace=True)
            else:
                logger.warning(f"Unsupported kline_data type: {type(kline_data)}")
                self._show_no_data_message()
                return

            # 使用统一图表服务更新图表
            if self.chart_widget:
                # 转换数据格式为ChartWidget期望的格式
                chart_data = {
                    'kdata': self.current_kdata,
                    'stock_code': self.current_stock,
                    'indicators_data': stock_data.get('indicators_data', stock_data.get('indicators', {})),
                    'title': stock_data.get('stock_name', self.current_stock)
                }
                self.chart_widget.update_chart(chart_data)
            else:
                logger.warning("图表控件不可用，无法更新图表")

        except Exception as e:
            logger.error(f"Failed to update chart: {e}")
            self._show_error_message(str(e))

    # 移除旧的matplotlib绘制方法，使用统一图表服务

    def _show_no_data_message(self):
        """显示无数据消息"""
        if self.chart_widget:
            # 通过图表控件显示无数据消息
            self.chart_widget.show_message("暂无数据", "info")
        else:
            logger.warning("无数据显示")

    def _show_error_message(self, error_msg: str):
        """显示错误消息"""
        try:
            if hasattr(self.chart_widget, 'show_message'):
                self.chart_widget.show_message(f"错误: {error_msg}", "error")
            elif hasattr(self.chart_widget, 'set_title'):
                # 降级：使用标题显示错误
                self.chart_widget.set_title(f"错误: {error_msg}")
            else:
                # 最后降级：在控制台输出
                print(f"图表错误: {error_msg}")

        except Exception as e:
            print(f"显示错误消息失败: {e}")
            print(f"原始错误: {error_msg}")

    def _show_loading_message(self):
        """显示加载消息"""
        try:
            if hasattr(self.chart_widget, 'show_message'):
                self.chart_widget.show_message("正在加载数据...", "info")
            elif hasattr(self.chart_widget, 'set_title'):
                # 降级：使用标题显示加载状态
                self.chart_widget.set_title("正在加载数据...")
            else:
                # 最后降级：在控制台输出
                print("正在加载图表数据...")

        except Exception as e:
            print(f"显示加载消息失败: {e}")

    def _clear_error_message(self):
        """清除错误消息"""
        try:
            if hasattr(self.chart_widget, 'clear_message'):
                self.chart_widget.clear_message()
            elif hasattr(self.chart_widget, 'set_title'):
                # 降级：恢复默认标题
                self.chart_widget.set_title("")

        except Exception as e:
            print(f"清除错误消息失败: {e}")

    def _on_chart_error(self, error_msg: str):
        """处理图表错误"""
        logger.error(f"图表错误: {error_msg}")
        self._show_error_message(error_msg)

    def mousePressEvent(self, event):
        """鼠标按下事件 - 委托给图表控件"""
        if self.chart_widget:
            self.chart_widget.mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 委托给图表控件"""
        if self.chart_widget:
            self.chart_widget.mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 委托给图表控件"""
        if self.chart_widget:
            self.chart_widget.mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def _get_selection_indices(self):
        """获取选择区间的数据索引 - 委托给图表控件"""
        if self.chart_widget and hasattr(self.chart_widget, '_get_selection_indices'):
            return self.chart_widget._get_selection_indices()
        return None, None


class MiddlePanel(BasePanel):
    """
    中间面板

    功能：
    1. K线图显示
    2. 技术指标图表
    3. 图表控制工具
    4. 多周期切换
    """

    # 定义信号
    chart_updated = pyqtSignal(str, str)  # 股票代码, 周期

    def __init__(self,
                 parent: QWidget,
                 coordinator,
                 **kwargs):
        """
        初始化中间面板

        Args:
            parent: 父窗口组件
            coordinator: 主窗口协调器
            **kwargs: 其他参数
        """
        # 通过服务容器获取图表服务
        self.chart_service = None
        if coordinator and hasattr(coordinator, 'service_container') and coordinator.service_container:
            try:
                from core.services import ChartService
                self.chart_service = coordinator.service_container.get_service(ChartService)
            except Exception as e:
                logger.warning(f"无法获取图表服务: {e}")
                self.chart_service = None

        # 当前状态
        self._current_stock_code = ''
        self._current_stock_name = ''
        self._current_period = '日线'  # 日线
        self._current_time_range = '最近1年'  # 时间范围
        self._current_chart_type = 'K线图'  # 图表类型
        self._current_indicators = ['MA', 'MACD']

        # 回测区间
        from PyQt5.QtCore import QDate
        self._start_date = QDate.currentDate().addYears(-1)
        self._end_date = QDate.currentDate()

        # 数据加载线程
        self._loader_thread = None

        # 获取统一图表服务
        try:
            from core.services.unified_chart_service import get_unified_chart_service
            self.unified_chart_service = get_unified_chart_service(data_source=self.chart_service)
        except ImportError:
            logger.warning("统一图表服务不可用，使用原有图表实现")
            self.unified_chart_service = None

        # 图表数据
        self._chart_data = None

        # 多屏面板
        self._multi_screen_panel = None

        super().__init__(parent, coordinator, **kwargs)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 设置面板样式
        self._root_frame.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
            QComboBox, QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QPushButton {
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: #007bff;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QToolBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #f8f9fa;
                spacing: 5px;
            }
        """)

        # 创建主布局
        main_layout = QVBoxLayout(self._root_frame)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        main_layout.addWidget(toolbar)
        self.add_widget('toolbar', toolbar)

        # 股票信息标签
        stock_info_label = QLabel("请选择股票")
        stock_info_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #495057;")
        toolbar.addWidget(stock_info_label)
        self.add_widget('stock_info_label', stock_info_label)

        toolbar.addSeparator()

        # 周期选择
        toolbar.addWidget(QLabel("周期:"))
        period_combo = QComboBox()
        period_combo.addItems(["分时", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"])
        period_combo.setCurrentText("日线")
        toolbar.addWidget(period_combo)
        self.add_widget('period_combo', period_combo)

        # 时间范围选择
        toolbar.addWidget(QLabel("时间范围:"))
        time_range_combo = QComboBox()
        time_range_combo.addItems([
            "最近7天", "最近30天", "最近90天", "最近180天",
            "最近1年", "最近2年", "最近3年", "最近5年", "全部"
        ])
        time_range_combo.setCurrentText("最近1年")
        toolbar.addWidget(time_range_combo)
        self.add_widget('time_range_combo', time_range_combo)

        # 回测区间选择
        from PyQt5.QtWidgets import QDateEdit
        from PyQt5.QtCore import QDate
        toolbar.addWidget(QLabel("回测区间:"))
        start_date_edit = QDateEdit()
        start_date_edit.setCalendarPopup(True)
        start_date_edit.setDate(QDate.currentDate().addYears(-1))
        toolbar.addWidget(start_date_edit)
        self.add_widget('start_date_edit', start_date_edit)

        toolbar.addWidget(QLabel("至"))
        end_date_edit = QDateEdit()
        end_date_edit.setCalendarPopup(True)
        end_date_edit.setDate(QDate.currentDate())
        toolbar.addWidget(end_date_edit)
        self.add_widget('end_date_edit', end_date_edit)

        # 图表类型选择
        toolbar.addWidget(QLabel("图表类型:"))
        chart_type_combo = QComboBox()
        chart_type_combo.addItems(["K线图", "分时图", "美国线", "收盘价"])
        chart_type_combo.setCurrentText("K线图")
        toolbar.addWidget(chart_type_combo)
        self.add_widget('chart_type_combo', chart_type_combo)

        toolbar.addSeparator()

        # 刷新按钮
        refresh_action = QAction("刷新", self._root_frame)
        refresh_action.setStatusTip("刷新图表数据")
        toolbar.addAction(refresh_action)
        self.add_widget('refresh_action', refresh_action)

        # 全屏按钮
        fullscreen_action = QAction("全屏", self._root_frame)
        fullscreen_action.setStatusTip("全屏显示图表")
        toolbar.addAction(fullscreen_action)
        self.add_widget('fullscreen_action', fullscreen_action)

        # 多屏切换按钮
        multi_screen_action = QAction("多屏", self._root_frame)
        multi_screen_action.setStatusTip("切换到多屏模式")
        toolbar.addAction(multi_screen_action)
        self.add_widget('multi_screen_action', multi_screen_action)

        # 创建进度条
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setMaximumHeight(8)
        main_layout.addWidget(progress_bar)
        self.add_widget('progress_bar', progress_bar)

        # 创建图表区域
        chart_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(chart_splitter)
        self.add_widget('chart_splitter', chart_splitter)

        # 主图表
        main_chart_frame = QFrame()
        main_chart_frame.setFrameStyle(QFrame.StyledPanel)
        chart_splitter.addWidget(main_chart_frame)
        self.add_widget('main_chart_frame', main_chart_frame)

        # 创建图表画布
        main_chart_layout = QVBoxLayout(main_chart_frame)
        main_chart_layout.setContentsMargins(0, 0, 0, 0)

        chart_canvas = ChartCanvas(main_chart_frame)
        main_chart_layout.addWidget(chart_canvas)
        self.add_widget('chart_canvas', chart_canvas)

        # 连接区间统计信号
        chart_canvas.request_stat_dialog.connect(self._show_stat_dialog)

        # 连接统一图表服务信号
        if hasattr(self, 'unified_chart_service') and self.unified_chart_service:
            self.unified_chart_service.chart_updated.connect(self._on_unified_chart_updated)
            self.unified_chart_service.error_occurred.connect(self._on_chart_load_error)
            self.unified_chart_service.loading_progress.connect(self._on_loading_progress)

        # 状态栏
        status_frame = QFrame()
        status_frame.setMaximumHeight(30)
        status_frame.setStyleSheet("background-color: #f8f9fa; border-top: 1px solid #dee2e6;")
        main_layout.addWidget(status_frame)
        self.add_widget('status_frame', status_frame)

        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)

        # 状态标签
        status_label = QLabel("就绪")
        status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        status_layout.addWidget(status_label)
        self.add_widget('status_label', status_label)

        status_layout.addStretch()

        # 数据时间标签
        data_time_label = QLabel("")
        data_time_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        status_layout.addWidget(data_time_label)
        self.add_widget('data_time_label', data_time_label)

    def _bind_events(self) -> None:
        """绑定事件"""
        # 周期选择变化
        period_combo = self.get_widget('period_combo')
        period_combo.currentTextChanged.connect(self._on_period_changed)

        # 时间范围选择变化
        time_range_combo = self.get_widget('time_range_combo')
        time_range_combo.currentTextChanged.connect(self._on_time_range_changed)

        # 回测区间选择变化
        start_date_edit = self.get_widget('start_date_edit')
        start_date_edit.dateChanged.connect(self._on_date_range_changed)

        end_date_edit = self.get_widget('end_date_edit')
        end_date_edit.dateChanged.connect(self._on_date_range_changed)

        # 图表类型选择变化
        chart_type_combo = self.get_widget('chart_type_combo')
        chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)

        # 工具栏按钮
        refresh_action = self.get_widget('refresh_action')
        refresh_action.triggered.connect(self._refresh_chart)

        fullscreen_action = self.get_widget('fullscreen_action')
        fullscreen_action.triggered.connect(self._toggle_fullscreen)

        multi_screen_action = self.get_widget('multi_screen_action')
        multi_screen_action.triggered.connect(self._toggle_multi_screen)

        # 订阅事件总线事件
        if self.event_bus:
            try:
                from core.events import StockSelectedEvent, IndicatorChangedEvent
                self.event_bus.subscribe(StockSelectedEvent, self.on_stock_selected)
                self.event_bus.subscribe(IndicatorChangedEvent, self.on_indicator_changed)
                logger.info("已订阅StockSelectedEvent和IndicatorChangedEvent事件")
            except Exception as e:
                logger.error(f"订阅事件失败: {e}")

        # 连接统一图表服务信号
        if hasattr(self, 'unified_chart_service') and self.unified_chart_service:
            try:
                self.unified_chart_service.chart_updated.connect(self._on_unified_chart_updated)
                self.unified_chart_service.loading_progress.connect(self._on_loading_progress)
                logger.info("已连接统一图表服务信号")
            except Exception as e:
                logger.warning(f"连接统一图表服务信号失败: {e}")

    def _initialize_data(self) -> None:
        """初始化数据"""
        self._update_status("就绪")

    def load_stock_chart(self, stock_code: str, stock_name: str = '') -> None:
        """加载股票图表"""
        try:
            self._current_stock_code = stock_code
            self._current_stock_name = stock_name or stock_code

            # 更新股票信息显示
            stock_info_label = self.get_widget('stock_info_label')
            stock_info_label.setText(f"{self._current_stock_code} - {self._current_stock_name}")

            # 加载图表数据
            self._load_chart_data()

        except Exception as e:
            logger.error(f"Failed to load stock chart: {e}")
            self._update_status(f"加载失败: {e}")

    def _load_chart_data(self, skip_indicators_update: bool = False) -> None:
        """加载图表数据"""
        try:
            if not self._current_stock_code:
                return

            # 停止之前的加载线程
            if hasattr(self, '_loader_thread') and self._loader_thread and self._loader_thread.isRunning():
                self._loader_thread.quit()
                self._loader_thread.wait(3000)  # 等待最多3秒
                if self._loader_thread.isRunning():
                    self._loader_thread.terminate()
                    self._loader_thread.wait()

            # 显示进度条
            progress_bar = self.get_widget('progress_bar')
            progress_bar.setVisible(True)
            progress_bar.setRange(0, 0)  # 无限进度条

            # 更新状态
            self._update_status("正在加载图表数据...")

            # 获取当前选择的指标
            if not skip_indicators_update:
                self._update_current_indicators()
            else:
                logger.debug(f"跳过指标更新，使用当前指标: {self._current_indicators}")

            # 记录当前指标列表
            logger.info(f"加载图表数据，股票代码: {self._current_stock_code}, 周期: {self._current_period}, 指标: {self._current_indicators}")

            # 使用统一图表服务加载数据
            if hasattr(self, 'unified_chart_service') and self.unified_chart_service:
                # 转换周期格式
                period_map = {
                    '分时': '1',
                    '5分钟': '5',
                    '15分钟': '15',
                    '30分钟': '30',
                    '60分钟': '60',
                    '日线': 'D',
                    '周线': 'W',
                    '月线': 'M'
                }
                period = period_map.get(self._current_period, 'D')

                self.unified_chart_service.load_chart_data(
                    stock_code=self._current_stock_code,
                    period=period,
                    indicators=self._current_indicators,
                    chart_id="middle_panel_chart"
                )
            else:
                # 回退到原有的加载方式
                # 验证ChartService是否可用
                if not self.chart_service:
                    logger.error("ChartService not available")
                    self._update_status("图表服务不可用")
                    return

                # 验证get_kdata方法是否存在
                if not hasattr(self.chart_service, 'get_kdata'):
                    logger.error(f"ChartService {type(self.chart_service)} has no get_kdata method")
                    self._update_status("图表服务缺少get_kdata方法")
                    return

                # 尝试初始化ChartService
                try:
                    if hasattr(self.chart_service, '_ensure_initialized'):
                        self.chart_service._ensure_initialized()
                    logger.info(f"ChartService type: {type(self.chart_service)}")
                    logger.info(f"ChartService has get_kdata: {hasattr(self.chart_service, 'get_kdata')}")
                except Exception as e:
                    logger.error(f"Failed to initialize ChartService: {e}")
                    self._update_status(f"图表服务初始化失败: {e}")
                    return

                self._loader_thread = ChartDataLoader(
                    self.chart_service,
                    self._current_stock_code,
                    self._current_period,
                    self._current_indicators
                )
                self._loader_thread.data_loaded.connect(self._on_chart_data_loaded)
                self._loader_thread.error_occurred.connect(self._on_chart_load_error)
                self._loader_thread.finished.connect(self._on_thread_finished)
                self._loader_thread.start()

        except Exception as e:
            logger.error(f"Failed to load chart data: {e}")
            self._update_status(f"加载失败: {e}")

    def _update_current_indicators(self) -> None:
        """更新当前选择的指标"""
        # 尝试从左侧面板获取选中的指标
        try:
            if hasattr(self, 'coordinator') and self.coordinator:
                # 尝试从左侧面板获取指标选择
                left_panel = getattr(self.coordinator, 'left_panel', None)
                if left_panel and hasattr(left_panel, 'get_selected_indicators'):
                    selected_indicators = left_panel.get_selected_indicators()
                    if selected_indicators:
                        self._current_indicators = selected_indicators
                        logger.debug(f"Updated indicators from left panel: {selected_indicators}")
                        return

                # 尝试从配置管理器获取指标设置
                config_manager = getattr(self.coordinator, 'config_manager', None)
                if config_manager:
                    indicators_config = config_manager.get('chart.indicators', ['MA', 'MACD'])
                    self._current_indicators = indicators_config
                    logger.debug(f"Updated indicators from config: {indicators_config}")
                    return
        except Exception as e:
            logger.warning(f"Failed to get indicators from left panel or config: {e}")

        # 使用默认指标配置作为后备
        if not hasattr(self, '_current_indicators') or not self._current_indicators:
            self._current_indicators = ['MA', 'MACD']  # 默认启用MA和MACD指标
            logger.debug(f"Using default indicators: {self._current_indicators}")

    def _on_chart_data_loaded(self, chart_data: Dict[str, Any]) -> None:
        """处理图表数据加载完成"""
        try:
            self._chart_data = chart_data

            # 隐藏进度条
            progress_bar = self.get_widget('progress_bar')
            progress_bar.setVisible(False)

            # 更新图表
            chart_canvas = self.get_widget('chart_canvas')
            chart_canvas.update_chart(chart_data)

            # 更新状态
            data_count = len(chart_data.get('kline_data', []))
            self._update_status(f"数据加载完成，共 {data_count} 条记录")

            # 更新数据时间
            if chart_data.get('kline_data'):
                last_date = chart_data['kline_data'][-1].get('date', '')
                data_time_label = self.get_widget('data_time_label')
                data_time_label.setText(f"数据更新时间: {last_date}")

            # 发出图表更新信号
            self.chart_updated.emit(self._current_stock_code, self._current_period)

            # 发布事件
            if self.coordinator and self.coordinator.event_bus:
                event = ChartUpdateEvent(
                    stock_code=self._current_stock_code,
                    chart_type='candlestick',
                    period=self._current_period,
                    indicators=self._current_indicators
                )
                self.coordinator.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Failed to process chart data: {e}")
            self._update_status(f"处理数据失败: {e}")

    def _on_chart_load_error(self, error_msg: str) -> None:
        """处理图表加载错误"""
        try:
            # 隐藏进度条
            progress_bar = self.get_widget('progress_bar')
            if progress_bar:
                progress_bar.setVisible(False)

            self._update_status(f"加载失败: {error_msg}")
            logger.error(f"Chart data load error: {error_msg}")

            # 显示错误消息
            chart_canvas = self.get_widget('chart_canvas')
            if chart_canvas and hasattr(chart_canvas, '_show_error_message'):
                chart_canvas._show_error_message(error_msg)
            else:
                # 降级处理：在状态栏显示错误
                self._update_status(f"图表加载错误: {error_msg}")

        except Exception as e:
            logger.error(f"Failed to handle chart load error: {e}")
            print(f"图表加载错误处理失败: {e}")

    def _on_unified_chart_updated(self, stock_code: str, chart_data: Dict[str, Any]) -> None:
        """处理统一图表服务的图表更新"""
        try:
            if stock_code == self._current_stock_code:
                self._chart_data = chart_data

                # 记录图表更新信息
                indicators_data = chart_data.get('indicators_data', {})
                logger.info(f"图表更新，股票代码: {stock_code}, 指标数据: {list(indicators_data.keys())}")

                # 隐藏进度条
                progress_bar = self.get_widget('progress_bar')
                progress_bar.setVisible(False)

                # 更新状态
                kline_data = chart_data.get('kline_data', [])
                if hasattr(kline_data, '__len__'):
                    data_count = len(kline_data)
                else:
                    data_count = 0
                self._update_status(f"数据加载完成，共 {data_count} 条记录")

                # 更新图表显示
                chart_canvas = self.get_widget('chart_canvas')
                if chart_canvas:
                    chart_canvas.update_chart(chart_data)

                # 更新数据时间
                if (hasattr(kline_data, '__len__') and len(kline_data) > 0) or (hasattr(kline_data, 'empty') and not kline_data.empty):
                    try:
                        last_item = kline_data.iloc[-1] if hasattr(kline_data, 'iloc') else kline_data[-1]
                        if hasattr(last_item, 'name'):
                            last_date = str(last_item.name)
                        elif isinstance(last_item, dict):
                            last_date = last_item.get('date', '')
                        else:
                            last_date = str(last_item)

                        data_time_label = self.get_widget('data_time_label')
                        data_time_label.setText(f"数据更新时间: {last_date}")
                    except Exception as e:
                        logger.warning(f"Failed to update data time: {e}")

                # 发出图表更新信号
                self.chart_updated.emit(self._current_stock_code, self._current_period)

                # 发布事件
                if self.coordinator and self.coordinator.event_bus:
                    event = ChartUpdateEvent(
                        stock_code=self._current_stock_code,
                        chart_type='candlestick',
                        period=self._current_period,
                        indicators=self._current_indicators
                    )
                    self.coordinator.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Failed to handle unified chart update: {e}")

    def _on_loading_progress(self, progress: int, message: str) -> None:
        """处理加载进度更新"""
        try:
            progress_bar = self.get_widget('progress_bar')
            if progress_bar:
                if progress_bar.maximum() == 0:  # 无限进度条
                    progress_bar.setRange(0, 100)
                progress_bar.setValue(progress)

            self._update_status(message)

        except Exception as e:
            logger.error(f"Failed to handle loading progress: {e}")

    def _on_thread_finished(self) -> None:
        """线程完成处理"""
        try:
            # 清理线程引用
            if hasattr(self, '_loader_thread') and self._loader_thread is not None:
                self._loader_thread.deleteLater()
                self._loader_thread = None
        except Exception as e:
            logger.error(f"Failed to handle thread finished: {e}")

    def _refresh_chart(self) -> None:
        """刷新图表"""
        try:
            if self._current_stock_code:
                self._update_status("正在刷新...")
                self._load_chart_data()
            else:
                QMessageBox.information(self._root_frame, "提示", "请先选择股票")

        except Exception as e:
            logger.error(f"Failed to refresh chart: {e}")
            self._update_status(f"刷新失败: {e}")

    def _toggle_fullscreen(self) -> None:
        """切换全屏显示"""
        try:
            # 这里可以实现全屏功能
            # 暂时显示提示信息
            QMessageBox.information(self._root_frame, "提示", "全屏功能开发中...")

        except Exception as e:
            logger.error(f"Failed to toggle fullscreen: {e}")

    def _toggle_multi_screen(self) -> None:
        """切换多屏显示"""
        try:
            # 检查是否已经有多屏面板
            if hasattr(self, '_multi_screen_panel') and self._multi_screen_panel:
                # 切换回单屏模式
                self._switch_to_single_screen()
            else:
                # 切换到多屏模式
                self._switch_to_multi_screen()

        except Exception as e:
            logger.error(f"Failed to toggle multi screen: {e}")
            QMessageBox.critical(self._root_frame, "错误", f"多屏切换失败: {e}")

    def _switch_to_multi_screen(self) -> None:
        """切换到多屏模式"""
        try:
            # 隐藏当前单屏图表
            chart_canvas = self.get_widget('chart_canvas')
            chart_canvas.setVisible(False)

            # 创建多屏面板
            from gui.widgets.multi_chart_panel import MultiChartPanel
            main_chart_frame = self.get_widget('main_chart_frame')

            self._multi_screen_panel = MultiChartPanel(main_chart_frame)
            main_chart_layout = main_chart_frame.layout()
            main_chart_layout.addWidget(self._multi_screen_panel)

            # 更新按钮文本
            multi_screen_action = self.get_widget('multi_screen_action')
            multi_screen_action.setText("单屏")
            multi_screen_action.setStatusTip("切换到单屏模式")

            # 如果有当前股票数据，在多屏中显示
            if self._chart_data and self._current_stock_code:
                self._multi_screen_panel.load_stock_data(
                    self._current_stock_code,
                    self._current_stock_name,
                    self._chart_data
                )

            self._update_status("已切换到多屏模式")

        except Exception as e:
            logger.error(f"Failed to switch to multi screen: {e}")
            raise

    def _switch_to_single_screen(self) -> None:
        """切换到单屏模式"""
        try:
            # 移除多屏面板
            if hasattr(self, '_multi_screen_panel') and self._multi_screen_panel:
                self._multi_screen_panel.setParent(None)
                self._multi_screen_panel.deleteLater()
                self._multi_screen_panel = None

            # 显示单屏图表
            chart_canvas = self.get_widget('chart_canvas')
            chart_canvas.setVisible(True)

            # 更新按钮文本
            multi_screen_action = self.get_widget('multi_screen_action')
            multi_screen_action.setText("多屏")
            multi_screen_action.setStatusTip("切换到多屏模式")

            self._update_status("已切换到单屏模式")

        except Exception as e:
            logger.error(f"Failed to switch to single screen: {e}")
            raise

    def _update_status(self, message: str) -> None:
        """更新状态"""
        status_label = self.get_widget('status_label')
        status_label.setText(message)

    @pyqtSlot()
    def _on_period_changed(self) -> None:
        """周期变化处理"""
        try:
            period_combo = self.get_widget('period_combo')
            self._current_period = period_combo.currentText()

            # 如果有选择的股票，重新加载数据
            if self._current_stock_code:
                self._load_chart_data()

        except Exception as e:
            logger.error(f"Failed to handle period change: {e}")

    @pyqtSlot()
    def _on_time_range_changed(self) -> None:
        """时间范围变化处理"""
        try:
            time_range_combo = self.get_widget('time_range_combo')
            self._current_time_range = time_range_combo.currentText()

            # 如果有选择的股票，重新加载数据
            if self._current_stock_code:
                self._load_chart_data()

        except Exception as e:
            logger.error(f"Failed to handle time range change: {e}")

    @pyqtSlot()
    def _on_date_range_changed(self) -> None:
        """回测区间变化处理"""
        try:
            start_date_edit = self.get_widget('start_date_edit')
            end_date_edit = self.get_widget('end_date_edit')

            self._start_date = start_date_edit.date()
            self._end_date = end_date_edit.date()

            # 如果有选择的股票，重新加载数据
            if self._current_stock_code:
                self._load_chart_data()

        except Exception as e:
            logger.error(f"Failed to handle date range change: {e}")

    @pyqtSlot()
    def _on_chart_type_changed(self) -> None:
        """图表类型变化处理"""
        try:
            chart_type_combo = self.get_widget('chart_type_combo')
            self._current_chart_type = chart_type_combo.currentText()

            # 如果有选择的股票，重新加载数据
            if self._current_stock_code:
                self._load_chart_data()

        except Exception as e:
            logger.error(f"Failed to handle chart type change: {e}")

    @pyqtSlot(object)
    def on_indicator_changed(self, event: IndicatorChangedEvent) -> None:
        """处理指标变化事件"""
        try:
            # 记录接收到的指标变化事件
            if hasattr(event, 'selected_indicators') and event.selected_indicators:
                logger.info(f"Middle panel received indicator change: {event.selected_indicators}")
                # 更新当前指标列表
                self._current_indicators = event.selected_indicators
                # 加载图表数据，跳过指标更新
                self._load_chart_data(skip_indicators_update=True)
            elif hasattr(event, 'data') and 'selected_indicators' in event.data and event.data['selected_indicators']:
                # 从event.data中获取指标列表
                logger.info(f"Middle panel received indicator change from data: {event.data['selected_indicators']}")
                self._current_indicators = event.data['selected_indicators']
                # 加载图表数据，跳过指标更新
                self._load_chart_data(skip_indicators_update=True)
            else:
                logger.warning("收到的指标变化事件没有指标数据或为空")
        except Exception as e:
            logger.error(f"处理指标变化事件失败: {e}", exc_info=True)

    def on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        try:
            logger.info(f"Middle panel received stock selection: {event.stock_code}")
            self.load_stock_chart(event.stock_code, event.stock_name)

        except Exception as e:
            logger.error(f"Failed to handle stock selection in middle panel: {e}")

    def get_current_stock(self) -> str:
        """获取当前股票代码"""
        return self._current_stock_code

    def get_current_period(self) -> str:
        """获取当前周期"""
        return self._current_period

    def get_chart_data(self) -> Optional[Dict[str, Any]]:
        """获取图表数据"""
        return self._chart_data

    def _show_stat_dialog(self, interval):
        """显示区间统计对话框"""
        try:
            start_idx, end_idx = interval
            chart_canvas = self.get_widget('chart_canvas')
            kdata = getattr(chart_canvas, 'current_kdata', None)

            if kdata is None or (hasattr(kdata, 'empty') and kdata.empty) or (hasattr(kdata, '__len__') and len(kdata) == 0) or start_idx >= end_idx:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self._root_frame, "提示", "区间数据无效！")
                return

            # 获取子区间数据
            sub = kdata.iloc[start_idx:end_idx+1]
            if sub.empty:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self._root_frame, "提示", "区间数据无效！")
                return

            # 计算统计指标（完全按照原版逻辑）
            open_ = sub.iloc[0]['open']
            close_ = sub.iloc[-1]['close']
            high = sub['high'].max()
            low = sub['low'].min()
            mean = sub['close'].mean()
            ret = (close_ - open_) / open_ * 100
            max_drawdown = ((sub['close'].cummax() - sub['close']) / sub['close'].cummax()).max() * 100
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

            # 连续涨跌计算
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

            # 构建统计数据
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

            # 显示统计对话框
            from gui.dialogs.interval_stat_dialog import IntervalStatDialog
            dlg = IntervalStatDialog(sub, stat, self._root_frame)
            dlg.setWindowTitle("区间统计")
            dlg.exec_()

        except Exception as e:
            logger.error(f"Failed to show stat dialog: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self._root_frame, "区间统计错误", str(e))

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            # 停止加载线程
            if hasattr(self, '_loader_thread') and self._loader_thread and self._loader_thread.isRunning():
                logger.info("Stopping chart data loader thread...")
                self._loader_thread.quit()

                # 等待线程正常退出
                if not self._loader_thread.wait(5000):  # 等待5秒
                    logger.warning("Thread did not quit gracefully, terminating...")
                    self._loader_thread.terminate()
                    self._loader_thread.wait()

                self._loader_thread.deleteLater()
                self._loader_thread = None

            # 清理图表数据
            self._chart_data = None

            # 调用父类清理
            super()._do_dispose()

            logger.info("Middle panel disposed")

        except Exception as e:
            logger.error(f"Failed to dispose middle panel: {e}")
