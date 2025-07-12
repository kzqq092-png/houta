"""
中间面板

负责显示K线图、技术指标图表等核心图表功能。
使用统一图表服务提供高性能图表渲染。
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import numpy as np
from datetime import datetime, timedelta
import time  # Added for loading time tracking

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QSplitter, QFrame, QProgressBar,
    QMessageBox, QToolBar, QAction, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon

from .base_panel import BasePanel
from core.events import StockSelectedEvent, ChartUpdateEvent, IndicatorChangedEvent, UIDataReadyEvent
from core.services.unified_chart_service import get_unified_chart_service, create_chart_widget, ChartDataLoader, ChartWidget
from optimization.progressive_loading_manager import get_progressive_loader, LoadingStage
from optimization.update_throttler import get_update_throttler

logger = logging.getLogger(__name__)

# 导入性能监控
try:
    from utils.performance_monitor import monitor_performance, get_performance_monitor
    PERFORMANCE_MONITORING = True
    logger.info("图表性能监控已启用")
except ImportError:
    PERFORMANCE_MONITORING = False

    def monitor_performance(func):
        return func  # 无监控装饰器

if TYPE_CHECKING:
    from core.services import ChartService


# 移除重复的ChartDataLoader，使用统一图表服务中的实现


class ChartCanvas(QWidget):
    """高性能图表画布 - 基于统一图表服务"""

    # 定义信号
    request_stat_dialog = pyqtSignal(tuple)  # (start_idx, end_idx)
    loading_state_changed = pyqtSignal(bool, str)  # (is_loading, message)
    loading_error = pyqtSignal(str)  # (error_message)
    loading_progress = pyqtSignal(int, str)  # (progress_percent, stage_name)

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
            self.chart_widget = create_chart_widget(
                parent=self, chart_id="middle_panel_chart")
        except:
            logger.warning("无法创建图表控件")
            self.chart_widget = None
        if self.chart_widget:
            layout.addWidget(self.chart_widget)

            # 连接信号
            self.chart_widget.request_stat_dialog.connect(
                self.request_stat_dialog.emit)
            self.chart_widget.error_occurred.connect(self._on_chart_error)

            # 添加进度信号连接
            if hasattr(self.chart_widget, 'loading_progress'):
                self.chart_widget.loading_progress.connect(
                    self.loading_progress.emit)
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

        # 加载状态
        self.is_loading = False
        self.loading_stage = 0
        self.loading_start_time = 0

        # 创建加载骨架屏
        self._create_loading_skeleton()

        # 获取渐进式加载管理器
        try:
            self.progressive_loader = get_progressive_loader()
        except:
            logger.warning("渐进式加载管理器不可用")
            self.progressive_loader = None

        # 获取更新节流器
        try:
            self.update_throttler = get_update_throttler()
        except:
            logger.warning("更新节流器不可用")
            self.update_throttler = None

        # 获取性能监控器
        if PERFORMANCE_MONITORING:
            try:
                self.performance_monitor = get_performance_monitor()
            except:
                logger.warning("性能监控器不可用")
                self.performance_monitor = None
        else:
            self.performance_monitor = None

    def _create_loading_skeleton(self):
        """创建加载骨架屏"""
        # 骨架屏容器
        self.skeleton_frame = QFrame(self)
        self.skeleton_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(245, 245, 245, 0.8);
                border-radius: 5px;
            }
            QLabel {
                color: #666;
                font-size: 14px;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 3px;
                background-color: #f5f5f5;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                width: 10px;
                margin: 0.5px;
            }
        """)
        self.skeleton_frame.setVisible(False)

        # 骨架屏布局
        skeleton_layout = QVBoxLayout(self.skeleton_frame)
        skeleton_layout.setAlignment(Qt.AlignCenter)

        # 标题
        self.loading_title = QLabel("正在加载图表...", self.skeleton_frame)
        self.loading_title.setAlignment(Qt.AlignCenter)
        self.loading_title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #333;")
        skeleton_layout.addWidget(self.loading_title)

        # 加载指示器
        self.loading_indicator = QLabel("正在加载基础数据...", self.skeleton_frame)
        self.loading_indicator.setAlignment(Qt.AlignCenter)
        skeleton_layout.addWidget(self.loading_indicator)

        # 进度条
        self.loading_progress_bar = QProgressBar(self.skeleton_frame)
        self.loading_progress_bar.setRange(0, 100)
        self.loading_progress_bar.setValue(0)
        self.loading_progress_bar.setTextVisible(True)
        self.loading_progress_bar.setMinimumWidth(300)
        self.loading_progress_bar.setMaximumHeight(15)
        skeleton_layout.addWidget(self.loading_progress_bar)

        # 阶段指示器
        self.stage_indicators = []
        stages_layout = QHBoxLayout()
        stages_layout.setAlignment(Qt.AlignCenter)
        stages_layout.setSpacing(10)

        stage_names = ["基础K线", "成交量", "基础指标", "高级指标", "装饰元素"]
        for i, name in enumerate(stage_names):
            indicator = QLabel(name)
            indicator.setStyleSheet("color: #999; font-size: 12px;")
            indicator.setAlignment(Qt.AlignCenter)
            indicator.setMinimumWidth(60)
            stages_layout.addWidget(indicator)
            self.stage_indicators.append(indicator)

        skeleton_layout.addLayout(stages_layout)

        # 错误消息
        self.error_label = QLabel("", self.skeleton_frame)
        self.error_label.setStyleSheet("color: #dc3545;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        skeleton_layout.addWidget(self.error_label)

        # 取消按钮
        self.cancel_button = QPushButton("取消加载", self.skeleton_frame)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px 10px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.cancel_button.setMaximumWidth(100)
        self.cancel_button.clicked.connect(self._cancel_loading)
        skeleton_layout.addWidget(self.cancel_button, 0, Qt.AlignCenter)

        # 添加到主布局
        self.layout().addWidget(self.skeleton_frame)

        # 创建加载计时器
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_time)
        self.loading_time = 0

    def _setup_chart(self):
        """设置图表布局 - 使用统一图表服务"""
        # 图表布局由ChartWidget自动管理
        pass

    @monitor_performance("chart_update")
    def update_chart(self, stock_data: Dict[str, Any]):
        """更新图表数据 - 使用统一图表服务"""
        try:
            self.stock_data = stock_data
            self.current_stock = stock_data.get('stock_code', '')

            # 获取OHLCV数据 - 支持多种数据格式
            kline_data = stock_data.get(
                'kline_data', stock_data.get('kdata', []))

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
                logger.warning(
                    f"Unsupported kline_data type: {type(kline_data)}")
                self._show_no_data_message()
                return

            # 使用渐进式加载管理器更新图表
            if self.progressive_loader and self.chart_widget:
                # 转换数据格式为ChartWidget期望的格式
                chart_data = {
                    'kdata': self.current_kdata,
                    'stock_code': self.current_stock,
                    'indicators': stock_data.get('indicators_data', stock_data.get('indicators', {})),
                    'title': stock_data.get('stock_name', self.current_stock)
                }

                # 启动加载计时器
                self.loading_time = 0
                self.loading_timer.start(100)  # 100ms更新一次
                self.loading_start_time = time.time()

                # 使用渐进式加载
                self.progressive_loader.load_chart_progressive(
                    self.chart_widget, chart_data['kdata'], chart_data['indicators'])

                # 注册加载进度回调
                if hasattr(self.chart_widget, 'set_loading_callback'):
                    self.chart_widget.set_loading_callback(
                        self._on_loading_progress)
            # 回退到普通更新
            elif self.chart_widget:
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

    def _update_loading_time(self):
        """更新加载时间"""
        self.loading_time += 0.1
        if self.loading_time > 10:  # 超过10秒，停止计时
            self.loading_timer.stop()

    def show_loading_skeleton(self):
        """显示加载骨架屏"""
        if hasattr(self, 'skeleton_frame'):
            self.is_loading = True
            self.loading_stage = 0
            self.loading_progress_bar.setValue(0)
            self.loading_indicator.setText("正在加载数据...")
            self.error_label.setVisible(False)
            self.skeleton_frame.setVisible(True)

            # 重置阶段指示器
            for indicator in self.stage_indicators:
                indicator.setStyleSheet("color: #999; font-size: 12px;")

            # 启动加载计时器
            self.loading_time = 0
            self.loading_timer.start(100)  # 100ms更新一次
            self.loading_start_time = time.time()

            self.loading_state_changed.emit(True, "正在加载数据...")

    def hide_loading_skeleton(self):
        """隐藏加载骨架屏"""
        if hasattr(self, 'skeleton_frame'):
            self.is_loading = False
            self.skeleton_frame.setVisible(False)
            self.loading_timer.stop()

            # 记录加载时间
            if PERFORMANCE_MONITORING and self.performance_monitor:
                total_time = time.time() - self.loading_start_time
                self.performance_monitor.record_time(
                    "chart_loading_total", total_time)

            self.loading_state_changed.emit(False, "")

    def update_loading_progress(self, progress: int, message: str = None):
        """更新加载进度"""
        if hasattr(self, 'loading_progress_bar'):
            self.loading_progress_bar.setValue(progress)
            if message:
                self.loading_indicator.setText(message)

            # 发送进度信号
            self.loading_progress.emit(progress, message or "")

            # 更新阶段指示器
            stage = min(len(self.stage_indicators) - 1, progress // 20)
            if stage >= 0:
                # 将当前阶段设为高亮
                for i, indicator in enumerate(self.stage_indicators):
                    if i < stage:
                        indicator.setStyleSheet(
                            "color: #28a745; font-size: 12px; font-weight: bold;")
                    elif i == stage:
                        indicator.setStyleSheet(
                            "color: #007bff; font-size: 12px; font-weight: bold;")
                    else:
                        indicator.setStyleSheet(
                            "color: #999; font-size: 12px;")

                self.loading_stage = stage

    def update_chart_frame(self):
        """更新图表框架（在数据加载前）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_chart_frame'):
            self.chart_widget.update_chart_frame()
        else:
            # 显示骨架屏作为替代
            self.show_loading_skeleton()

    def update_basic_kdata(self, kdata):
        """更新基础K线数据（第一阶段）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_basic_kdata'):
            self.chart_widget.update_basic_kdata(kdata)
            self.update_loading_progress(20, "正在加载K线数据...")

            # 记录性能指标
            if PERFORMANCE_MONITORING and self.performance_monitor:
                self.performance_monitor.record_time("chart_loading_basic_kdata",
                                                     time.time() - self.loading_start_time)
        else:
            # 使用普通更新
            self.update_chart({'kdata': kdata})

    def update_volume(self, kdata):
        """更新成交量数据（第二阶段）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_volume'):
            self.chart_widget.update_volume(kdata)
            self.update_loading_progress(40, "正在加载成交量数据...")

            # 记录性能指标
            if PERFORMANCE_MONITORING and self.performance_monitor:
                self.performance_monitor.record_time("chart_loading_volume",
                                                     time.time() - self.loading_start_time)
        else:
            # 使用普通更新
            self.update_chart({'kdata': kdata})

    def update_indicators(self, kdata, indicators):
        """更新指标数据（第三阶段）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_indicators'):
            self.chart_widget.update_indicators(kdata, indicators)
            self.update_loading_progress(80, "正在加载指标数据...")

            # 记录性能指标
            if PERFORMANCE_MONITORING and self.performance_monitor:
                self.performance_monitor.record_time("chart_loading_indicators",
                                                     time.time() - self.loading_start_time)
        else:
            # 使用普通更新
            chart_data = {'kdata': kdata, 'indicators': indicators}
            self.update_chart(chart_data)

    def _on_loading_progress(self, progress, stage_name):
        """处理加载进度更新"""
        self.update_loading_progress(progress, stage_name)

        # 完成后隐藏骨架屏
        if progress >= 100:
            QTimer.singleShot(500, self.hide_loading_skeleton)

    def _cancel_loading(self):
        """取消加载"""
        if self.chart_widget and hasattr(self.chart_widget, 'cancel_loading'):
            self.chart_widget.cancel_loading()

        self.hide_loading_skeleton()
        self._show_error_message("加载已取消")

    def show_loading_error(self, error_msg: str):
        """显示加载错误"""
        if hasattr(self, 'error_label'):
            self.error_label.setText(error_msg)
            self.error_label.setVisible(True)
            self.loading_indicator.setText("加载失败")
            self.loading_progress_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #dc3545;
                }
            """)

            # 发送错误信号
            self.loading_error.emit(error_msg)

    def _show_no_data_message(self):
        """显示无数据消息"""
        if hasattr(self, 'chart_widget') and self.chart_widget:
            # 清空图表
            if hasattr(self.chart_widget, 'clear_chart'):
                self.chart_widget.clear_chart()

            # 显示无数据消息
            if hasattr(self.chart_widget, 'show_message'):
                self.chart_widget.show_message("没有可用数据")
        else:
            # 显示错误消息
            self.show_loading_error("没有可用数据")

    def _show_error_message(self, error_msg: str):
        """显示错误消息"""
        logger.error(f"图表错误: {error_msg}")

        if hasattr(self, 'chart_widget') and self.chart_widget:
            # 显示错误消息
            if hasattr(self.chart_widget, 'show_error'):
                self.chart_widget.show_error(error_msg)
            elif hasattr(self.chart_widget, 'show_message'):
                self.chart_widget.show_message(f"错误: {error_msg}")

        # 更新骨架屏
        self.show_loading_error(error_msg)

    def _show_loading_message(self):
        """显示加载消息"""
        if hasattr(self, 'chart_widget') and self.chart_widget:
            # 显示加载消息
            if hasattr(self.chart_widget, 'show_loading'):
                self.chart_widget.show_loading()
            elif hasattr(self.chart_widget, 'show_message'):
                self.chart_widget.show_message("正在加载...")

        # 显示骨架屏
        self.show_loading_skeleton()

    def _clear_error_message(self):
        """清除错误消息"""
        if hasattr(self, 'error_label'):
            self.error_label.setText("")
            self.error_label.setVisible(False)

        if hasattr(self, 'loading_progress_bar'):
            self.loading_progress_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #007bff;
                }
            """)

    def _on_chart_error(self, error_msg: str):
        """处理图表错误"""
        self._show_error_message(error_msg)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        super().mousePressEvent(event)
        # 将事件传递给图表控件
        if hasattr(self, 'chart_widget') and self.chart_widget:
            self.chart_widget.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        super().mouseMoveEvent(event)
        # 将事件传递给图表控件
        if hasattr(self, 'chart_widget') and self.chart_widget:
            self.chart_widget.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
        # 将事件传递给图表控件
        if hasattr(self, 'chart_widget') and self.chart_widget:
            self.chart_widget.mouseReleaseEvent(event)

    def _get_selection_indices(self):
        """获取选择区间的索引"""
        if hasattr(self, 'chart_widget') and self.chart_widget:
            return self.chart_widget.get_selection_indices()
        return None


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
                self.chart_service = coordinator.service_container.get_service(
                    ChartService)
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
            self.unified_chart_service = get_unified_chart_service(
                data_source=self.chart_service)
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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分裂器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # 创建图表画布
        self.chart_canvas = ChartCanvas(self._root_frame)
        self.add_widget('chart_canvas', self.chart_canvas)
        splitter.addWidget(self.chart_canvas)

        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        main_layout.addWidget(toolbar)
        self.add_widget('toolbar', toolbar)

        # 股票信息标签
        stock_info_label = QLabel("请选择股票")
        stock_info_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #495057;")
        toolbar.addWidget(stock_info_label)
        self.add_widget('stock_info_label', stock_info_label)

        toolbar.addSeparator()

        # 周期选择
        toolbar.addWidget(QLabel("周期:"))
        period_combo = QComboBox()
        period_combo.addItems(
            ["分时", "5分钟", "15分钟", "30分钟", "60分钟", "日线", "周线", "月线"])
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

        # 连接图表画布的信号
        self.chart_canvas.loading_state_changed.connect(
            self._on_loading_state_changed)
        self.chart_canvas.loading_error.connect(self._on_chart_error)
        self.chart_canvas.loading_progress.connect(self._on_loading_progress)
        self.chart_canvas.request_stat_dialog.connect(self._show_stat_dialog)

        # 创建状态栏
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
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
        data_time_label = QLabel("数据时间:")
        status_layout.addWidget(data_time_label)
        self.add_widget('data_time_label', data_time_label)

    def _create_chart_controls(self, parent: QWidget) -> None:
        """创建图表控制栏"""
        pass

    def _bind_events(self) -> None:
        """绑定事件处理"""
        try:
            # 周期选择变化
            period_combo = self.get_widget('period_combo')
            period_combo.currentTextChanged.connect(self._on_period_changed)

            # 时间范围选择变化
            time_range_combo = self.get_widget('time_range_combo')
            time_range_combo.currentTextChanged.connect(
                self._on_time_range_changed)

            # 回测区间选择变化
            start_date_edit = self.get_widget('start_date_edit')
            start_date_edit.dateChanged.connect(self._on_date_range_changed)

            end_date_edit = self.get_widget('end_date_edit')
            end_date_edit.dateChanged.connect(self._on_date_range_changed)

            # 图表类型选择变化
            chart_type_combo = self.get_widget('chart_type_combo')
            chart_type_combo.currentTextChanged.connect(
                self._on_chart_type_changed)

            # 工具栏按钮
            refresh_action = self.get_widget('refresh_action')
            refresh_action.triggered.connect(self._refresh_chart)

            fullscreen_action = self.get_widget('fullscreen_action')
            fullscreen_action.triggered.connect(self._toggle_fullscreen)

            multi_screen_action = self.get_widget('multi_screen_action')
            multi_screen_action.triggered.connect(self._toggle_multi_screen)

            # 导入安全连接工具
            from utils.qt_helpers import safe_connect

            # 订阅事件总线事件
            if self.event_bus:
                try:
                    from core.events import StockSelectedEvent, IndicatorChangedEvent
                    self.event_bus.subscribe(
                        StockSelectedEvent, self.on_stock_selected)
                    self.event_bus.subscribe(
                        IndicatorChangedEvent, self.on_indicator_changed)
                    self.event_bus.subscribe(
                        UIDataReadyEvent, self._on_ui_data_ready)
                    logger.info(
                        "已订阅StockSelectedEvent, IndicatorChangedEvent, UIDataReadyEvent事件")
                except Exception as e:
                    logger.error(f"订阅事件失败: {e}")

        except Exception as e:
            logger.error(f"绑定事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _initialize_data(self) -> None:
        """初始化数据"""
        self._update_status("请先从左侧选择股票")

    def _on_loading_state_changed(self, is_loading: bool, message: str):
        pass

    def _on_chart_error(self, error_message: str):
        pass

    def _on_loading_progress(self, progress: int, message: str):
        pass

    @pyqtSlot(UIDataReadyEvent)
    def _on_ui_data_ready(self, event: UIDataReadyEvent) -> None:
        """处理数据准备就绪事件，更新图表"""
        data = event.data
        if not data or data.get('kline') is None:
            self._update_status("K线数据为空，无法渲染图表")
            # 可以在这里显示一个空状态或错误信息
            return

        self._current_stock_code = data.get('stock_code')
        self._current_stock_name = data.get('stock_name')

        self._update_status(f"正在渲染 {self._current_stock_name} 的图表...")

        # 准备图表所需的数据包
        chart_data_package = self._prepare_chart_data(data)

        self.chart_canvas.update_chart(chart_data_package)
        self._update_status(f"{self._current_stock_name} 图表渲染完成")

    def _prepare_chart_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将从协调器接收到的统一数据模型转换为图表控件所需的数据格式。
        """
        # technical_analysis 的原始格式: {'MA': {'5': [...], '10': [...]}, 'MACD': {'DIF': [...], ...}}
        raw_indicators = data.get('analysis', {}).get('technical_analysis', {})

        # 转换指标数据格式以匹配图表控件的期望
        # 例如，图表控件可能需要一个更扁平的结构
        formatted_indicators = {}
        if 'MA' in raw_indicators:
            formatted_indicators['MA'] = raw_indicators['MA']
        if 'MACD' in raw_indicators:
            formatted_indicators['MACD'] = raw_indicators['MACD']
        # 可以为其他指标添加更多转换逻辑...

        return {
            'stock_code': data.get('stock_code'),
            'kline_data': data.get('kline'),
            'indicators_data': formatted_indicators
        }

    def _refresh_chart(self) -> None:
        """刷新图表"""
        if self._current_stock_code:
            # 触发协调器重新加载数据
            self._update_status("正在刷新数据...")
            self.event_bus.publish(
                StockSelectedEvent(
                    stock_code=self._current_stock_code,
                    stock_name=self._current_stock_name
                )
            )
        else:
            self._update_status("请先选择股票")

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
        """响应指标变化事件"""
        # 刷新图表以应用新的指标
        self._refresh_chart()

    def on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        # 此方法已废弃，逻辑移至 _on_ui_data_ready
        pass

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
                    logger.warning(
                        "Thread did not quit gracefully, terminating...")
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
