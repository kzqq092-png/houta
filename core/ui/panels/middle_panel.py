from loguru import logger
"""
中间面板

负责显示K线图、技术指标图表等核心图表功能。
使用统一图表服务提供高性能图表渲染。
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
import numpy as np
from datetime import datetime, timedelta
import time  # Added for loading time tracking
import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QSplitter, QFrame, QProgressBar,
    QMessageBox, QToolBar, QAction, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QDateTime, QDate, QTime
from PyQt5.QtGui import QFont, QIcon
from .base_panel import BasePanel
from core.events import StockSelectedEvent, ChartUpdateEvent, IndicatorChangedEvent, UIDataReadyEvent, MultiScreenToggleEvent
from core.services.unified_chart_service import get_unified_chart_service, create_chart_widget, ChartDataLoader, ChartWidget
from optimization.progressive_loading_manager import get_progressive_loader, LoadingStage
from optimization.update_throttler import get_update_throttler

logger = logger

# 导入性能监控
try:
    from core.performance import measure_performance as monitor_performance, get_performance_monitor, PerformanceCategory
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

    def __init__(self, parent=None, coordinator=None):
        super().__init__(parent)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 获取统一图表服务
        try:
            from core.services.unified_chart_service import get_unified_chart_service
            self.chart_service = get_unified_chart_service()
        except Exception as e:
            logger.warning(f"统一图表服务不可用: {e}")
            self.chart_service = None

        # 创建图表控件
        try:
            from core.services.unified_chart_service import create_chart_widget
            self.chart_widget = create_chart_widget(
                parent=self, chart_id="middle_panel_chart", coordinator=coordinator)

            # 检查是否是真正的ChartWidget实例，而不是错误占位符
            if not isinstance(self.chart_widget, QLabel):
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
                # 如果是错误占位符，创建FallbackChartWidget
                logger.warning("chart_widget是错误占位符，创建FallbackChartWidget")
                self._create_fallback_chart_widget(layout, self.chart_widget.text())
        except Exception as e:
            logger.error(f"创建图表控件失败: {e}")
            self._create_fallback_chart_widget(layout, f"图表控件创建失败: {e}")

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
        except Exception as e:
            logger.warning(f"渐进式加载管理器不可用: {e}")
            self.progressive_loader = None

        # 获取更新节流器
        try:
            self.update_throttler = get_update_throttler()
        except Exception as e:
            logger.warning(f"更新节流器不可用: {e}")
            self.update_throttler = None

        # 获取性能监控器
        if PERFORMANCE_MONITORING:
            try:
                self.performance_monitor = get_performance_monitor()
            except Exception as e:
                logger.warning(f"性能监控器不可用: {e}")
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

    def _create_fallback_chart_widget(self, layout, error_message):
        """创建备用图表控件，确保提供与ChartWidget相同的关键接口"""
        from PyQt5.QtWidgets import QVBoxLayout, QLabel
        from PyQt5.QtCore import pyqtSignal, Qt

        class FallbackChartWidget(QWidget):
            """当ChartWidget创建失败时使用的替代组件"""
            # 模拟ChartWidget的关键信号
            request_stat_dialog = pyqtSignal(tuple)
            error_occurred = pyqtSignal(str)
            loading_progress = pyqtSignal(int, str)

            def __init__(self, parent=None, error_message="图表控件创建失败"):
                super().__init__(parent)
                self.layout = QVBoxLayout(self)
                self.error_label = QLabel(error_message)
                self.error_label.setAlignment(Qt.AlignCenter)
                self.error_label.setStyleSheet("color: #dc3545; font-size: 14px;")
                self.layout.addWidget(self.error_label)

            def update_chart(self, data=None):
                """模拟ChartWidget的update_chart方法"""
                logger.warning(f"FallbackChartWidget.update_chart被调用，但不执行任何操作")
                pass

            def apply_theme(self):
                """模拟ChartWidget的apply_theme方法"""
                pass

            def update_basic_kdata(self, kdata):
                """模拟ChartWidget的update_basic_kdata方法"""
                pass

            def update_volume(self, kdata):
                """模拟ChartWidget的update_volume方法"""
                pass

            def update_indicators(self, kdata, indicators=None):
                """模拟ChartWidget的update_indicators方法"""
                pass

        # 创建并添加FallbackChartWidget
        fallback_widget = FallbackChartWidget(self, error_message)
        layout.addWidget(fallback_widget)
        self.chart_widget = fallback_widget

        # 连接信号
        self.chart_widget.error_occurred.connect(self._on_chart_error)

    def _setup_chart(self):
        """设置图表布局 - 使用统一图表服务"""
        # 图表布局由ChartWidget自动管理
        pass

    @monitor_performance("chart_update")
    def update_chart(self, stock_data: Dict[str, Any]):
        """更新图表数据 - 使用统一图表服务"""
        try:
            # 🔴 性能优化P1.4：降低日志级别，减少I/O和list()转换开销
            logger.debug("=== 开始更新图表数据 ===")
            logger.debug(f"接收到的stock_data键数: {len(stock_data.keys()) if stock_data else 0}")

            self.stock_data = stock_data
            self.current_stock = stock_data.get('stock_code', '')
            logger.debug(f"更新图表: {self.current_stock}")

            # 获取OHLCV数据 - 支持多种数据格式
            kline_data = stock_data.get('kline_data', stock_data.get('kdata', []))
            logger.debug(f"获取到K线数据类型: {type(kline_data)}")

            # 检查数据是否为空
            import pandas as pd
            if kline_data is None:
                logger.error("K线数据为None，无法更新图表")
                self._show_no_data_message()
                return

            # 处理不同类型的K线数据
            if isinstance(kline_data, pd.DataFrame):
                # 处理DataFrame
                if kline_data.empty:
                    logger.error("K线数据为空DataFrame，无法更新图表")
                    self._show_no_data_message()
                    return
                logger.debug(f"K线数据为DataFrame，形状: {kline_data.shape}")
                self.current_kdata = kline_data
            elif isinstance(kline_data, list):
                # 处理列表格式
                if not kline_data:
                    logger.error("K线数据为空列表，无法更新图表")
                    self._show_no_data_message()
                    return
                logger.debug(f"K线数据为列表，长度: {len(kline_data)}")
                try:
                    self.current_kdata = pd.DataFrame(kline_data)
                    if not self.current_kdata.empty and 'date' in self.current_kdata.columns:
                        self.current_kdata.set_index('date', inplace=True)
                    logger.debug(f"列表转换为DataFrame成功，形状: {self.current_kdata.shape}")
                except Exception as e:
                    logger.error(f"列表转换为DataFrame失败: {e}")
                    self._show_error_message(f"数据格式转换失败: {e}")
                    return
            elif isinstance(kline_data, dict):
                # 处理字典格式 - 改进处理逻辑
                logger.debug(f"K线数据为字典")

                # 尝试从字典中提取DataFrame
                df_data = None
                if 'data' in kline_data:
                    df_data = kline_data.get('data')
                elif 'kdata' in kline_data:
                    df_data = kline_data.get('kdata')
                elif 'kline_data' in kline_data:
                    df_data = kline_data.get('kline_data')
                else:
                    # 尝试将整个字典作为数据
                    df_data = kline_data

                if isinstance(df_data, pd.DataFrame):
                    if df_data.empty:
                        logger.error("字典中的DataFrame为空")
                        self._show_no_data_message()
                        return
                    self.current_kdata = df_data
                    logger.debug(f"从字典中获取DataFrame成功，形状: {df_data.shape}")
                elif isinstance(df_data, list) and df_data:
                    try:
                        self.current_kdata = pd.DataFrame(df_data)
                        logger.debug(f"从字典中获取列表并转换为DataFrame成功，长度: {len(df_data)}")
                    except Exception as e:
                        logger.error(f"字典中列表转换为DataFrame失败: {e}")
                        self._show_error_message(f"数据格式转换失败: {e}")
                        return
                else:
                    logger.error(f"字典中的数据格式不支持: {type(df_data)}")
                    self._show_error_message(f"不支持的数据格式: {type(df_data)}")
                    return
            else:
                logger.error(f"不支持的K线数据类型: {type(kline_data)}")
                self._show_error_message(f"不支持的数据类型: {type(kline_data)}")
                return

            # 验证最终的DataFrame
            if self.current_kdata is None or self.current_kdata.empty:
                logger.error("最终的K线数据为空，无法更新图表")
                self._show_no_data_message()
                return

            logger.info(f"数据验证通过，准备更新图表。数据形状: {self.current_kdata.shape}")

            # ✅ 修复：关键任务（K线图）立即执行，不使用渐进式加载
            # 只有非关键任务（指标、装饰）使用渐进式加载
            if self.chart_widget:
                # 转换数据格式为ChartWidget期望的格式
                chart_data = {
                    'kdata': self.current_kdata,
                    'stock_code': self.current_stock,
                    'indicators_data': stock_data.get('indicators_data', stock_data.get('indicators', {})),
                    'title': stock_data.get('stock_name', self.current_stock)
                }

                # ✅ 修复：关键K线图渲染立即执行（不使用渐进式加载）
                logger.info("✅ 关键K线图渲染立即执行（不使用渐进式加载）")
                start_time = time.time()
                self.chart_widget.update_chart(chart_data)
                render_time = (time.time() - start_time) * 1000  # 转换为毫秒
                logger.info(f"✅ K线图渲染完成，耗时: {render_time:.2f}ms")

                # ✅ 非关键任务（指标、装饰）使用渐进式加载（可选）
                # 如果指标数据存在，可以在后台渐进式加载
                indicators = stock_data.get('indicators_data', stock_data.get('indicators', {}))
                if self.progressive_loader and indicators:
                    logger.debug("非关键任务（指标）使用渐进式加载")
                    # 延迟加载指标，不阻塞K线图显示
                    # 这里可以异步加载指标，但不影响K线图显示
                    pass
            else:
                logger.warning("图表控件不可用，无法更新图表")
                self._show_error_message("图表控件不可用")
                return

            logger.info("=== 图表数据更新完成 ===")

        except Exception as e:
            logger.error(f"更新图表失败: {e}", exc_info=True)
            self._show_error_message(str(e))

    def _get_data_summary(self, data):
        """获取数据摘要信息，用于日志记录"""
        try:
            if data is None:
                return "None"
            elif isinstance(data, pd.DataFrame):
                return f"DataFrame({data.shape})"
            elif isinstance(data, list):
                return f"List(len={len(data)})"
            elif isinstance(data, dict):
                return f"Dict(keys={list(data.keys())})"
            else:
                return f"{type(data).__name__}"
        except Exception:
            return "Unknown"

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
                self.performance_monitor.record_timing(
                    "chart_loading_total", total_time, PerformanceCategory.UI)

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
                self.performance_monitor.record_timing("chart_loading_basic_kdata",
                                                       time.time() - self.loading_start_time, PerformanceCategory.UI)
        else:
            # 使用普通更新
            self.update_chart({'kdata': kdata, 'indicators_data': {}})

    def update_volume(self, kdata):
        """更新成交量数据（第二阶段）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_volume'):
            self.chart_widget.update_volume(kdata)
            self.update_loading_progress(40, "正在加载成交量数据...")

            # 记录性能指标
            if PERFORMANCE_MONITORING and self.performance_monitor:
                self.performance_monitor.record_timing("chart_loading_volume",
                                                       time.time() - self.loading_start_time, PerformanceCategory.UI)
        else:
            # 使用普通更新
            self.update_chart({'kdata': kdata, 'indicators_data': {}})

    def update_indicators(self, kdata, indicators):
        """更新指标数据（第三阶段）"""
        if self.chart_widget and hasattr(self.chart_widget, 'update_indicators'):
            self.chart_widget.update_indicators(kdata, indicators)
            self.update_loading_progress(80, "正在加载指标数据...")

            # 记录性能指标
            if PERFORMANCE_MONITORING and self.performance_monitor:
                self.performance_monitor.record_timing("chart_loading_indicators",
                                                       time.time() - self.loading_start_time, PerformanceCategory.UI)
        else:
            # 使用普通更新
            chart_data = {'kdata': kdata, 'indicators_data': {}}  # builtin指标会自动计算
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

    # 移除由ChartCanvas接管的鼠标事件，让底层的matplotlib canvas自行处理
    # def mousePressEvent(self, event):
    #     if event.button() == Qt.LeftButton and self.chart_widget:
    #         self.selecting = True
    #         self.selection_start = event.pos()
    #         self.chart_widget.start_selection(self.selection_start)
    #     super().mousePressEvent(event)

    # def mouseMoveEvent(self, event):
    #     if self.selecting and self.chart_widget:
    #         # 将事件坐标转换为chart_widget的局部坐标
    #         local_pos = self.chart_widget.mapFrom(self, event.pos())
    #
    #         # 这里需要创建一个新的QMouseEvent，因为原始事件的坐标是相对于ChartCanvas的
    #         from PyQt5.QtGui import QMouseEvent
    #         new_event = QMouseEvent(event.type(), local_pos, event.button(), event.buttons(), event.modifiers())
    #
    #         # 直接调用chart_widget的事件处理函数
    #         if hasattr(self.chart_widget, 'mouseMoveEvent'):
    #             self.chart_widget.mouseMoveEvent(new_event)
    #
    # super().mouseMoveEvent(event)

    # def mouseReleaseEvent(self, event):
    #     if event.button() == Qt.LeftButton and self.selecting and self.chart_widget:
    #         self.selecting = False
    #         self.selection_end = event.pos()
    #         # ... (省略)
    #     super().mouseReleaseEvent(event)


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
                #  正确导入并获取图表服务
                from core.services.chart_service import ChartService
                self.chart_service = coordinator.service_container.resolve(ChartService)
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

        # 创建工具栏 - 移动到图表上方
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        main_layout.addWidget(toolbar)
        self.add_widget('toolbar', toolbar)

        # 股票信息标签
        # stock_info_label = QLabel("请选择股票")
        # stock_info_label.setStyleSheet(
        #     "font-size: 12px; font-weight: bold; color: #495057;")
        # toolbar.addWidget(stock_info_label)
        # self.add_widget('stock_info_label', stock_info_label)

        # toolbar.addSeparator()

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

        # 多屏切换按钮
        multi_screen_action = QAction("多屏", self._root_frame)
        multi_screen_action.setStatusTip("切换到多屏模式")
        toolbar.addAction(multi_screen_action)
        self.add_widget('multi_screen_action', multi_screen_action)

        # 创建分裂器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # 创建图表画布
        self.chart_canvas = ChartCanvas(self._root_frame, coordinator=self.coordinator)
        self.add_widget('chart_canvas', self.chart_canvas)
        splitter.addWidget(self.chart_canvas)

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

        # 数据时间标签已移至右下角

    def _create_chart_controls(self, parent: QWidget) -> None:
        """创建图表控制栏"""
        pass

    def _bind_events(self) -> None:
        """绑定事件处理"""
        try:
            # 周期选择变化 - 正确地将currentText作为参数传递
            period_combo = self.get_widget('period_combo')
            period_combo.currentTextChanged.connect(self._on_period_changed)

            # 时间范围选择变化 - 正确地将currentText作为参数传递
            time_range_combo = self.get_widget('time_range_combo')
            time_range_combo.currentTextChanged.connect(self._on_time_range_changed)

            # 图表类型选择变化 - 正确地将currentText作为参数传递
            chart_type_combo = self.get_widget('chart_type_combo')
            chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)

            # 工具栏按钮
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
        """处理UI数据就绪事件，更新图表"""
        try:
            # 🔴 性能优化P1.4：降低日志级别，减少I/O开销
            logger.debug(f"=== MiddlePanel收到UIDataReadyEvent事件 ===")
            logger.debug(f"事件源: {event.source}")
            logger.debug(f"股票代码: {event.stock_code}")
            logger.debug(f"股票名称: {event.stock_name}")

            # 确保从event.ui_data获取数据
            data = event.ui_data
            if not data:
                logger.error("事件中未包含ui_data")
                self._update_status("错误：事件数据为空")
                return

            logger.debug(f"ui_data包含的键: {list(data.keys())}")

            self.current_stock_code = event.stock_code
            self.current_stock_name = event.stock_name

            # 从数据中提取K线数据 - 支持多种键名
            kdata = None
            for key in ['kline_data', 'kdata', 'kline']:
                if key in data:
                    kdata = data.get(key)
                    logger.debug(f"从键'{key}'中获取到K线数据，类型: {type(kdata)}")
                    break

            if kdata is None:
                logger.error("在ui_data中未找到K线数据")
                logger.error(f"可用的键: {list(data.keys())}")
                self._update_status("错误：无法解析K线数据")
                return

            # 检查数据是否为空
            import pandas as pd
            if isinstance(kdata, pd.DataFrame):
                if kdata.empty:
                    logger.warning(f"K线数据为空DataFrame，股票代码: {self.current_stock_code}")
                    self._update_status("无可用K线数据")
                    # 仍然尝试更新图表以显示"无数据"消息
                    chart_data = self._prepare_chart_data(data)
                    self.chart_canvas.update_chart(chart_data)
                    return
                else:
                    logger.debug(f"K线数据验证通过，DataFrame形状: {kdata.shape}")
            elif isinstance(kdata, list):
                if not kdata:
                    logger.warning(f"K线数据为空列表，股票代码: {self.current_stock_code}")
                    self._update_status("无可用K线数据")
                    chart_data = self._prepare_chart_data(data)
                    self.chart_canvas.update_chart(chart_data)
                    return
                else:
                    logger.debug(f"K线数据验证通过，列表长度: {len(kdata)}")
            else:
                logger.debug(f"K线数据类型: {type(kdata)}")

            self.current_kdata = kdata

            # 验证数据量是否与时间范围匹配
            data_count = len(kdata) if hasattr(kdata, '__len__') else 0
            if not self._validate_data_count(kdata, self._current_time_range):
                logger.warning(f"数据量验证失败，时间范围: {self._current_time_range}, 数据条数: {data_count}")
                # 继续处理，但在状态栏显示警告
                self._update_status(f"已加载 {self.current_stock_name} ({data_count} 条数据) - 数据量可能不匹配")
            else:
                self._update_status(f"已加载 {self.current_stock_name} ({data_count} 条数据)")

            # 准备并更新图表
            logger.debug("准备图表数据并更新图表")
            chart_data = self._prepare_chart_data(data)
            logger.debug(f"准备的图表数据键: {list(chart_data.keys())}")

            # 确保chart_canvas存在
            if not hasattr(self, 'chart_canvas') or self.chart_canvas is None:
                logger.error("chart_canvas不存在，无法更新图表")
                self._update_status("错误：图表组件不可用")
                return

            logger.info("调用chart_canvas.update_chart")
            self.chart_canvas.update_chart(chart_data)
            logger.info("=== UIDataReadyEvent处理完成 ===")

        except Exception as e:
            logger.error(f"处理UIDataReadyEvent事件失败: {e}", exc_info=True)
            self._update_status(f"错误: {e}")
            # 尝试显示错误信息给用户
            if hasattr(self, 'chart_canvas') and self.chart_canvas:
                try:
                    self.chart_canvas._show_error_message(f"图表更新失败: {e}")
                except Exception:
                    pass

    def _prepare_chart_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """准备传递给图表控件的数据"""
        try:
            # 🔴 性能优化P1.4：降低日志级别，减少I/O开销
            logger.debug("=== 准备图表数据 ===")
            logger.debug(f"输入数据键: {list(data.keys())}")

            # 创建图表数据副本
            chart_data = data.copy()

            # 添加或更新基本信息
            if hasattr(self, 'current_stock_name') and self.current_stock_name:
                chart_data['title'] = self.current_stock_name
                chart_data['stock_name'] = self.current_stock_name
                logger.debug(f"设置股票名称: {self.current_stock_name}")

            if hasattr(self, 'current_stock_code') and self.current_stock_code:
                chart_data['stock_code'] = self.current_stock_code
                logger.debug(f"设置股票代码: {self.current_stock_code}")

            # 确保K线数据存在且格式正确
            kline_data = None
            for key in ['kline_data', 'kdata', 'kline']:
                if key in chart_data:
                    kline_data = chart_data[key]
                    # 统一使用 'kline_data' 键
                    if key != 'kline_data':
                        chart_data['kline_data'] = kline_data
                        logger.debug(f"将键'{key}'统一为'kline_data'")
                    break

            if kline_data is not None:
                logger.debug(f"K线数据类型: {type(kline_data)}")
                if hasattr(kline_data, 'shape'):
                    logger.debug(f"K线数据形状: {kline_data.shape}")
                elif hasattr(kline_data, '__len__'):
                    logger.debug(f"K线数据长度: {len(kline_data)}")
            else:
                logger.warning("准备的图表数据中没有K线数据")

            # 添加其他必要的字段
            if 'period' not in chart_data and hasattr(self, '_current_period'):
                chart_data['period'] = self._current_period

            if 'time_range' not in chart_data and hasattr(self, '_current_time_range'):
                chart_data['time_range'] = self._current_time_range

            if 'chart_type' not in chart_data and hasattr(self, '_current_chart_type'):
                chart_data['chart_type'] = self._current_chart_type

            logger.debug(f"最终图表数据键: {list(chart_data.keys())}")
            logger.debug("=== 图表数据准备完成 ===")

            return chart_data

        except Exception as e:
            logger.error(f"准备图表数据失败: {e}", exc_info=True)
            # 返回原始数据作为回退
            return data

    def _refresh_chart(self) -> None:
        """刷新图表，使用当前数据"""
        try:
            # 触发协调器重新加载数据
            self._update_status("正在刷新数据...")
            self.event_bus.publish(
                StockSelectedEvent(
                    stock_code=self._current_stock_code,
                    stock_name=self._current_stock_name
                )
            )
        except Exception as e:
            logger.error(f"Failed to refresh chart: {e}")
            self._update_status(f"刷新失败: {e}")

    def _load_chart_data(self) -> None:
        """加载图表数据

        根据当前的股票代码、周期、时间范围和图表类型，创建并发布StockSelectedEvent事件。
        如果没有选择股票，则仅保存当前的参数设置，不加载数据。
        """
        try:
            # 确保股票代码存在
            if not self._current_stock_code:
                # 仅保存参数设置，不发出警告
                # logger.warning("无法加载图表数据：股票代码为空")
                return

            logger.info(f"加载图表数据：{self._current_stock_code}, 周期：{self._current_period}, 时间范围：{self._current_time_range}, 图表类型：{self._current_chart_type}")

            # 创建并发布StockSelectedEvent事件
            event = StockSelectedEvent(
                stock_code=self._current_stock_code,
                stock_name=self._current_stock_name,
                period=self._current_period,
                time_range=self._current_time_range,
                chart_type=self._current_chart_type
            )

            # 发布事件
            self._update_status(f"正在加载 {self._current_stock_name} 数据...")
            self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"加载图表数据失败: {e}", exc_info=True)
            self._update_status(f"加载失败: {e}")

    def _on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件

        当用户选择了一只股票时，更新当前的股票代码和名称，然后加载图表数据。

        Args:
            event: 股票选择事件
        """
        try:
            if not event or not event.stock_code:
                return

            # 更新当前股票信息
            self._current_stock_code = event.stock_code
            self._current_stock_name = event.stock_name

            # 如果事件中包含周期、时间范围和图表类型，则更新当前值
            # 否则使用已有的默认值
            if event.period:
                self._current_period = event.period

            if event.time_range:
                self._current_time_range = event.time_range

            if event.chart_type:
                self._current_chart_type = event.chart_type

            # 更新UI组件显示
            period_combo = self.get_widget('period_combo')
            if period_combo and self._current_period:
                index = period_combo.findText(self._current_period)
                if index >= 0:
                    period_combo.setCurrentIndex(index)

            time_range_combo = self.get_widget('time_range_combo')
            if time_range_combo and self._current_time_range:
                index = time_range_combo.findText(self._current_time_range)
                if index >= 0:
                    time_range_combo.setCurrentIndex(index)

            chart_type_combo = self.get_widget('chart_type_combo')
            if chart_type_combo and self._current_chart_type:
                index = chart_type_combo.findText(self._current_chart_type)
                if index >= 0:
                    chart_type_combo.setCurrentIndex(index)

            logger.info(f"股票选择: {self._current_stock_name} ({self._current_stock_code})")

        except Exception as e:
            logger.error(f"处理股票选择事件失败: {e}", exc_info=True)

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
            from PyQt5.QtWidgets import QVBoxLayout

            # 检查main_chart_frame是否存在，如果不存在则使用chart_canvas的父窗口
            main_chart_frame = self.get_widget('main_chart_frame')
            if main_chart_frame is None:
                # 使用chart_canvas的父窗口作为容器
                main_chart_frame = chart_canvas.parent()
                # 将其添加到widgets中，以便后续可以通过get_widget获取
                self.add_widget('main_chart_frame', main_chart_frame)

            # 确保main_chart_frame有布局
            if main_chart_frame.layout() is None:
                main_chart_layout = QVBoxLayout(main_chart_frame)
                main_chart_layout.setContentsMargins(0, 0, 0, 0)
                main_chart_layout.setSpacing(0)
            else:
                main_chart_layout = main_chart_frame.layout()

            # 创建多屏面板
            self._multi_screen_panel = MultiChartPanel(main_chart_frame)
            main_chart_layout.addWidget(self._multi_screen_panel)

            # 设置数据管理器
            from core.services.unified_data_manager import get_unified_data_manager
            data_manager = get_unified_data_manager()
            if data_manager:
                logger.info("为多屏面板设置数据管理器")
                self._multi_screen_panel.set_data_manager(data_manager)
            else:
                logger.error("无法获取数据管理器")

            # 设置股票列表
            if hasattr(self.coordinator, 'get_stock_list'):
                stock_list = self.coordinator.get_stock_list()
                if stock_list:
                    logger.info(f"为多屏面板设置股票列表，共 {len(stock_list)} 只股票")
                    self._multi_screen_panel.set_stock_list(stock_list)

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

            # 发布多屏模式切换事件
            self.event_bus.publish(MultiScreenToggleEvent(is_multi_screen=True))

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

            # 发布多屏模式切换事件
            self.event_bus.publish(MultiScreenToggleEvent(is_multi_screen=False))

        except Exception as e:
            logger.error(f"Failed to switch to single screen: {e}")
            raise

    def _update_status(self, message: str) -> None:
        """更新状态"""
        status_label = self.get_widget('status_label')
        status_label.setText(message)

    def _on_period_changed(self, period) -> None:
        """处理周期变更事件"""
        try:
            logger.info(f"周期变更: {period}")
            self._current_period = period

            # 加载图表数据
            self._load_chart_data()

        except Exception as e:
            logger.error(f"处理周期变更失败: {e}", exc_info=True)

    def _on_time_range_changed(self, time_range) -> None:
        """处理时间范围变更事件"""
        try:
            logger.info(f"时间范围变更: {time_range}")
            self._current_time_range = time_range

            # 自动更新回测区间
            start_date, end_date = self._parse_time_range_to_dates(time_range)

            # 更新回测区间控件
            start_date_edit = self.get_widget('start_date_edit')
            end_date_edit = self.get_widget('end_date_edit')

            if start_date_edit:
                start_date_edit.setDate(start_date)
            if end_date_edit:
                end_date_edit.setDate(end_date)

            logger.info(f"回测区间已自动更新: {start_date.toString('yyyy-MM-dd')} 至 {end_date.toString('yyyy-MM-dd')}")

            # 验证周期和时间范围的兼容性
            if not self._validate_period_time_range_compatibility(self._current_period, time_range):
                self._update_status(f"警告：{self._current_period} 与 {time_range} 可能不兼容")

            # 加载图表数据
            self._load_chart_data()

        except Exception as e:
            logger.error(f"处理时间范围变更失败: {e}", exc_info=True)

    def _parse_time_range_to_dates(self, time_range: str) -> tuple:
        """将时间范围文本解析为开始和结束日期

        Args:
            time_range: 时间范围文本，如"最近7天"、"最近1年"等

        Returns:
            tuple: (开始日期, 结束日期) 的QDate对象
        """

        end_date = QDate.currentDate()  # 结束日期总是当前日期

        # 时间范围映射（天数）
        time_range_map = {
            "最近7天": 7,
            "最近30天": 30,
            "最近90天": 90,
            "最近180天": 180,
            "最近1年": 365,
            "最近2年": 365 * 2,
            "最近3年": 365 * 3,
            "最近5年": 365 * 5,
            "全部": 365 * 10  # 对于"全部"，我们假设为10年
        }

        days = time_range_map.get(time_range, 365)  # 默认1年
        start_date = end_date.addDays(-days)

        return start_date, end_date

    def _validate_period_time_range_compatibility(self, period: str, time_range: str) -> bool:
        """验证周期和时间范围的兼容性

        Args:
            period: 周期，如"日线"、"5分钟"等
            time_range: 时间范围，如"最近7天"、"最近1年"等

        Returns:
            bool: 是否兼容
        """
        try:
            # 对于分钟级别的数据，时间范围不应该太长
            if period in ['分时', '5分钟', '15分钟', '30分钟', '60分钟']:
                long_ranges = ['最近2年', '最近3年', '最近5年', '全部']
                if time_range in long_ranges:
                    logger.warning(f"分钟级数据 {period} 与长时间范围 {time_range} 可能不兼容，数据量会很大")
                    return False

            # 对于短时间范围，周线和月线可能数据点太少
            if period in ['周线', '月线']:
                short_ranges = ['最近7天', '最近30天']
                if time_range in short_ranges:
                    logger.warning(f"长周期数据 {period} 与短时间范围 {time_range} 可能不兼容，数据点太少")
                    return False

            return True

        except Exception as e:
            logger.error(f"验证周期和时间范围兼容性失败: {e}")
            return True  # 出错时默认返回兼容

    def _validate_data_count(self, data, time_range: str) -> bool:
        """验证数据量是否与时间范围匹配

        Args:
            data: 数据（DataFrame或list）
            time_range: 时间范围文本

        Returns:
            bool: 数据量是否合理
        """
        try:
            # 修复DataFrame验证问题
            if data is None:
                logger.warning("数据为None")
                return False

            # 对于DataFrame，使用.empty检查
            if hasattr(data, 'empty') and data.empty:
                logger.warning("数据为空DataFrame")
                return False

            # 对于list或其他可迭代对象，使用len检查
            if hasattr(data, '__len__') and len(data) == 0:
                logger.warning("数据长度为0")
                return False

            # 获取数据长度
            data_length = len(data) if hasattr(data, '__len__') else 0
            if data_length == 0:
                logger.warning("数据长度为0")
                return False

            # 时间范围映射（预期交易日数量）
            time_range_map = {
                "最近7天": (3, 7),      # 最少3天，最多7天
                "最近30天": (15, 25),   # 最少15天，最多25天
                "最近90天": (45, 70),   # 最少45天，最多70天
                "最近180天": (90, 140),  # 最少90天，最多140天
                "最近1年": (200, 300),  # 最少200天，最多300天
                "最近2年": (400, 600),  # 最少400天，最多600天
                "最近3年": (600, 900),  # 最少600天，最多900天
                "最近5年": (1000, 1500),  # 最少1000天，最多1500天
            }

            if time_range in time_range_map:
                min_expected, max_expected = time_range_map[time_range]

                if data_length < min_expected:
                    logger.warning(f"数据量可能不足：{time_range} 期望至少{min_expected}条数据，实际获得{data_length}条")
                    return False
                elif data_length > max_expected * 2:  # 如果数据量过多也提醒
                    logger.warning(f"数据量可能过多：{time_range} 期望最多{max_expected}条数据，实际获得{data_length}条")
                    # 不返回False，因为数据多不是错误
                else:
                    logger.info(f"数据量正常：{time_range} 获得{data_length}条数据，在预期范围内")

            return True

        except Exception as e:
            logger.error(f"验证数据量失败: {e}")
            return True  # 出错时默认返回正常

    def _on_chart_type_changed(self, chart_type) -> None:
        """处理图表类型变更事件"""
        try:
            logger.info(f"图表类型变更: {chart_type}")
            self._current_chart_type = chart_type

            # 加载图表数据
            self._load_chart_data()

        except Exception as e:
            logger.error(f"处理图表类型变更失败: {e}", exc_info=True)

    @pyqtSlot(object)
    def on_indicator_changed(self, event: IndicatorChangedEvent) -> None:
        """响应指标变化事件"""
        try:
            # 从事件中提取指标列表
            selected_indicators = event.selected_indicators if hasattr(event, 'selected_indicators') else event.data.get('selected_indicators', [])
            logger.info(f"MiddlePanel收到指标变更事件: {selected_indicators}")

            # 获取chart_widget（注意：self.chart_canvas是ChartCanvas容器，其内部有真正的chart_widget）
            chart_canvas = self.get_widget('chart_canvas')
            if not chart_canvas:
                logger.warning("无法获取chart_canvas，跳过指标更新")
                return

            # 从ChartCanvas中获取真正的chart_widget
            if hasattr(chart_canvas, 'chart_widget'):
                chart_widget = chart_canvas.chart_widget
                logger.info(f"✅ 从ChartCanvas中获取到实际的chart_widget")
            else:
                # 如果ChartCanvas没有chart_widget属性，尝试直接使用chart_canvas
                logger.warning("ChartCanvas没有chart_widget属性，尝试直接使用chart_canvas")
                chart_widget = chart_canvas

            if not chart_widget:
                logger.warning("无法获取有效的chart_widget，跳过指标更新")
                return

            # 定义内置指标列表（这些指标在indicator_mixin中有专门处理）
            builtin_indicators = {
                'MA', 'MACD', 'RSI', 'BOLL', 'KDJ', 'CCI', 'OBV'
            }

            # 定义talib指标的默认参数
            talib_default_params = {
                'ADOSC': {'fastperiod': 3, 'slowperiod': 10},
                'AROON': {'timeperiod': 25},
                'AROONOSC': {'timeperiod': 25},
                'ATR': {'timeperiod': 14},
                'BBANDS': {'timeperiod': 5, 'nbdevup': 2, 'nbdevdn': 2},
                'CCI': {'timeperiod': 14},
                'CMO': {'timeperiod': 14},
                'DX': {'timeperiod': 14},
                'KAMA': {'timeperiod': 10},
                'MFI': {'timeperiod': 14},
                'NATR': {'timeperiod': 14},
                'STOCH': {'fastk_period': 5, 'slowk_period': 3, 'slowd_period': 3},
                'STOCHF': {'fastk_period': 5, 'fastd_period': 3},
                'STOCHRSI': {'timeperiod': 14, 'fastk_period': 5, 'fastd_period': 3},
                'TRANGE': {'timeperiod': 14},
                'WILLR': {'timeperiod': 14},
            }

            # 将指标名称转换为完整格式，并根据名称智能判断group
            indicator_list = []
            for ind_name in selected_indicators:
                # 如果已经是字典格式，直接使用
                if isinstance(ind_name, dict):
                    indicator_list.append(ind_name)
                else:
                    # 否则转换为标准格式
                    # 根据指标名称判断group：builtin或talib
                    group = 'builtin' if ind_name in builtin_indicators else 'talib'
                    # 为talib指标提供默认参数
                    params = talib_default_params.get(ind_name, {}) if group == 'talib' else {}
                    indicator_list.append({
                        "name": ind_name,
                        "params": params,
                        "group": group
                    })

            logger.info(f"转换后的指标列表: {[ind['name'] for ind in indicator_list]}")
            logger.info(f"指标分组信息: {[(ind['name'], ind['group']) for ind in indicator_list]}")

            # 更新chart_widget的active_indicators
            if hasattr(chart_widget, 'on_indicator_selected'):
                chart_widget.on_indicator_selected(indicator_list)
                logger.info(f"✅ 已通过on_indicator_selected更新主图指标")
            elif hasattr(chart_widget, 'active_indicators'):
                chart_widget.active_indicators = indicator_list
                # 如果有current_kdata，触发图表更新
                if hasattr(chart_widget, 'current_kdata') and chart_widget.current_kdata is not None:
                    chart_widget.update_chart({
                        'kdata': chart_widget.current_kdata,
                        'indicators_data': {}  # 传递空的indicators_data，因为builtin指标会自己计算
                    })
                    logger.info(f"✅ 已直接设置active_indicators并更新主图")
            else:
                logger.warning("chart_widget没有on_indicator_selected或active_indicators属性")

        except Exception as e:
            logger.error(f"处理指标变更事件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        # 调用内部方法处理股票选择事件
        self._on_stock_selected(event)

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
