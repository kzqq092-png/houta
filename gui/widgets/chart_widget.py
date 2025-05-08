"""
图表控件模块
"""
from typing import Optional, List, Dict, Any, Tuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import seaborn as sns
import numpy as np
import pandas as pd
import mplfinance as mpf
import mplcursors
from datetime import datetime
import matplotlib.dates as mdates

from core.logger import LogManager
from utils.theme import get_theme_manager, Theme
from utils.config_manager import ConfigManager
import traceback
from core.cache_manager import CacheManager
from indicators_algo import calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci
from concurrent.futures import ThreadPoolExecutor
from .async_data_processor import AsyncDataProcessor
from .chart_renderer import ChartRenderer


class ChartWidget(QWidget):
    """图表控件类"""

    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    zoom_changed = pyqtSignal(float)  # 缩放变更信号

    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None, theme_manager=None, log_manager=None):
        """初始化图表控件

        Args:
            parent: Parent widget
            config_manager: Optional ConfigManager instance to use
            theme_manager: Optional theme manager to use
            log_manager: Optional log manager to use
        """
        try:
            super().__init__(parent)

            # 初始化变量
            self.current_kdata = None
            self.current_signals = []
            self.current_period = 'D'
            self.current_indicator = None
            self._zoom_level = 1.0
            self._zoom_history = []
            self._max_zoom = 5.0
            self._min_zoom = 0.2
            self.crosshair_enabled = True  # 默认关闭十字线

            # 初始化缓存管理器
            self.cache_manager = CacheManager(max_size=100)  # 图表最多缓存100个

            # 启用双缓冲
            self.setAttribute(Qt.WA_PaintOnScreen, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.setAutoFillBackground(True)

            # 初始化管理器
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = theme_manager or get_theme_manager(
                self.config_manager)

            # 初始化日志管理器
            self.log_manager = log_manager or LogManager()

            # 初始化数据更新锁
            self._update_lock = QMutex()
            self._render_lock = QMutex()

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 创建更新定时器
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._process_update_queue)
            self._update_timer.start(100)  # 100ms 间隔

            # 初始化更新队列
            self._update_queue = []

            # 添加渲染优化
            self._optimize_rendering()

            # 初始化异步数据处理器
            self.data_processor = AsyncDataProcessor()
            self.data_processor.calculation_progress.connect(
                self._on_calculation_progress)
            self.data_processor.calculation_complete.connect(
                self._on_calculation_complete)
            self.data_processor.calculation_error.connect(
                self._on_calculation_error)

            # 初始化渲染器
            self.renderer = ChartRenderer()
            self.renderer.render_progress.connect(self._on_render_progress)
            self.renderer.render_complete.connect(self._on_render_complete)
            self.renderer.render_error.connect(self._on_render_error)

            # 应用初始主题
            self._apply_initial_theme()

            self.log_manager.info("图表控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI"""
        try:
            self.setLayout(QVBoxLayout())
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.layout().setSpacing(0)

            # 创建工具栏
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setSpacing(12)
            toolbar_widget = QWidget()
            toolbar_widget.setLayout(toolbar_layout)
            toolbar_widget.setStyleSheet('''
                QWidget {
                    background: transparent;
                }
                QLabel {
                    font-family: 'Microsoft YaHei', 'Arial', sans-serif;
                    font-size: 14px;
                    color: #1976d2;
                }
                QComboBox {
                    font-family: 'Microsoft YaHei', 'Arial', sans-serif;
                    font-size: 14px;
                    border-radius: 6px;
                    border: 1px solid #bdbdbd;
                    background: #ffffff;
                    padding: 4px 16px 4px 8px;
                    min-width: 90px;
                }
                QComboBox:hover {
                    border: 1.5px solid #1976d2;
                    background: #e3f2fd;
                }
                QComboBox QAbstractItemView {
                    font-size: 14px;
                    selection-background-color: #e3f2fd;
                }
                QPushButton {
                    font-family: 'Microsoft YaHei', 'Arial', sans-serif;
                    font-size: 14px;
                    border-radius: 8px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e3f2fd, stop:1 #bbdefb);
                    border: 1px solid #90caf9;
                    padding: 6px 18px;
                    color: #1565c0;
                }
                QPushButton:hover {
                    background: #90caf9;
                    color: #0d47a1;
                }
                QPushButton:pressed {
                    background: #64b5f6;
                }
            ''')

            # 添加周期选择
            toolbar_layout.addWidget(QLabel("周期:"))
            self.period_combo = QComboBox()
            self.period_combo.addItems(
                ['日线', '周线', '月线', '60分钟', '30分钟', '15分钟', '5分钟'])
            toolbar_layout.addWidget(self.period_combo)

            # 添加指标选择
            toolbar_layout.addWidget(QLabel("指标:"))
            self.indicator_combo = QComboBox()
            self.indicator_combo.addItems([
                'MA', 'MACD', 'KDJ', 'RSI', 'BOLL', 'CCI', 'ATR', 'OBV',
                'WR', 'DMI', 'SAR', 'ROC', 'TRIX', 'MFI', 'ADX', 'BBW',
                'AD', 'CMO', 'DX', '综合指标'
            ])
            toolbar_layout.addWidget(self.indicator_combo)

            # 添加清除按钮
            self.clear_button = QPushButton("清除指标")
            toolbar_layout.addWidget(self.clear_button)

            # 添加主题切换按钮
            theme_label = QLabel("主题:")
            self.theme_button = QPushButton()
            self.theme_button.setFixedSize(32, 32)
            self.theme_button.setIconSize(QSize(24, 24))
            self.theme_button.clicked.connect(self._toggle_theme)
            self._update_theme_button()
            toolbar_layout.addWidget(theme_label)
            toolbar_layout.addWidget(self.theme_button)

            # 添加工具栏到主布局
            self.layout().addWidget(toolbar_widget)

            # 初始化图表布局
            self._init_figure_layout()

            # 创建matplotlib工具栏（只创建一次）
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.layout().insertWidget(1, self.toolbar)

            self.log_manager.info("图表控件UI初始化完成")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接周期选择信号
            self.period_combo.currentTextChanged.connect(
                self.on_period_changed)

            # 连接指标选择信号
            self.indicator_combo.currentTextChanged.connect(
                self.on_indicator_changed)

            # 连接清除按钮信号
            self.clear_button.clicked.connect(self.clear_indicators)

            self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _process_update_queue(self):
        """处理更新队列中的任务"""
        try:
            if not self._update_queue:
                return

            with QMutexLocker(self._update_lock):
                while self._update_queue:
                    update_func, args = self._update_queue.pop(0)
                    try:
                        update_func(*args)
                    except Exception as e:
                        self.log_manager.error(f"更新任务执行失败: {str(e)}")

        except Exception as e:
            self.log_manager.error(f"处理更新队列失败: {str(e)}")

    def queue_update(self, update_func, *args):
        """将更新任务加入队列

        Args:
            update_func: 更新函数
            *args: 函数参数
        """
        with QMutexLocker(self._update_lock):
            self._update_queue.append((update_func, args))

    def show_loading_dialog(self):
        """显示加载进度对话框"""
        # if not hasattr(self, 'loading_dialog'):
        #     self.loading_dialog = QProgressDialog(self)
        #     self.loading_dialog.setWindowTitle("正在加载")
        #     self.loading_dialog.setLabelText("正在更新图表...")
        #     self.loading_dialog.setRange(0, 100)
        #     self.loading_dialog.setWindowModality(Qt.WindowModal)
        #     self.loading_dialog.setAutoClose(True)
        # self.loading_dialog.show()

    def update_loading_progress(self, value: int, message: str = None):
        """更新加载进度"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.setValue(value)
            if message:
                self.loading_dialog.setLabelText(message)

    def close_loading_dialog(self):
        """关闭加载进度对话框"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.close()

    def get_stock_theme(self, stock_code):
        """根据股票代码返回专属配色"""
        # 可扩展为从配置或数据库读取
        color_map = {
            'sz301566': {
                'main': '#1976d2', 'line': '#ff9800', 'ma': '#bdbdbd', 'bg': '#f7fafd', 'vol': '#90caf9', 'indicator': '#e53935'
            },
            'default': {
                'main': '#1976d2', 'line': '#43a047', 'ma': '#fbc02d', 'bg': '#f7fafd', 'vol': '#90caf9', 'indicator': '#e53935'
            }
        }
        return color_map.get(stock_code, color_map['default'])

    def update_chart(self, data: dict):
        """更新图表"""
        try:
            if not data or 'kdata' not in data:
                return

            kdata = data['kdata']
            self.current_kdata = kdata

            # 显示加载进度
            self.show_loading_dialog()

            # 清除现有图表内容
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.clear()

            # 获取主题样式
            style = self._get_chart_style()

            # 渲染K线图
            self.renderer.render_candlesticks(self.price_ax, kdata, style)

            # 渲染成交量
            self.renderer.render_volume(self.volume_ax, kdata, style)

            # 渲染指标
            self._render_indicators(kdata)

            # 优化显示
            self._optimize_display()

            # 更新画布
            self.canvas.draw_idle()

            # 关闭加载进度
            self.close_loading_dialog()

        except Exception as e:
            self.error_occurred.emit(f"更新图表失败: {str(e)}")
            self.close_loading_dialog()

    def _render_indicators(self, kdata: pd.DataFrame):
        """渲染技术指标"""
        try:
            # 获取当前选中的指标
            indicators = self._get_active_indicators()
            if not indicators:
                return

            # 计算并渲染每个指标
            for indicator in indicators:
                style = self._get_indicator_style(indicator)

                if indicator.startswith('MA'):
                    period = int(indicator[2:])
                    ma = kdata['close'].rolling(period).mean()
                    self.renderer.render_line(self.price_ax, ma, style)

                elif indicator == 'MACD':
                    macd, signal, hist = self._calculate_macd(kdata)
                    self.renderer.render_line(self.indicator_ax, macd,
                                              self._get_indicator_style('MACD', 0))
                    self.renderer.render_line(self.indicator_ax, signal,
                                              self._get_indicator_style('MACD', 1))
                    # 绘制柱状图
                    dates = mdates.date2num(kdata.index.to_pydatetime())
                    colors = ['red' if h >= 0 else 'green' for h in hist]
                    self.indicator_ax.bar(dates, hist, color=colors, alpha=0.5)

                elif indicator == 'RSI':
                    rsi = self._calculate_rsi(kdata)
                    self.renderer.render_line(self.indicator_ax, rsi, style)

                elif indicator == 'BOLL':
                    mid, upper, lower = self._calculate_boll(kdata)
                    self.renderer.render_line(self.price_ax, mid,
                                              self._get_indicator_style('BOLL', 0))
                    self.renderer.render_line(self.price_ax, upper,
                                              self._get_indicator_style('BOLL', 1))
                    self.renderer.render_line(self.price_ax, lower,
                                              self._get_indicator_style('BOLL', 2))

        except Exception as e:
            self.error_occurred.emit(f"渲染指标失败: {str(e)}")

    def _get_chart_style(self) -> Dict[str, Any]:
        """获取图表样式"""
        try:
            colors = self.theme_manager.get_theme_colors()

            return {
                'up_color': colors.get('k_up', '#e60000'),
                'down_color': colors.get('k_down', '#1dbf60'),
                'edge_color': colors.get('k_edge', '#2c3140'),
                'volume_up_color': colors.get('volume_up', '#e60000'),
                'volume_down_color': colors.get('volume_down', '#1dbf60'),
                'volume_alpha': 0.5,
                'grid_color': colors.get('chart_grid', '#2c3140'),
                'background_color': colors.get('chart_background', '#181c24'),
                'text_color': colors.get('chart_text', '#b0b8c1'),
                'axis_color': colors.get('chart_grid', '#2c3140'),
                'label_color': colors.get('chart_text', '#b0b8c1'),
                'border_color': colors.get('chart_grid', '#2c3140'),
            }

        except Exception as e:
            self.log_manager.error(f"获取图表样式失败: {str(e)}")
            return {}

    def _get_indicator_style(self, name: str, index: int = 0) -> Dict[str, Any]:
        """获取指标样式"""
        colors = ['#fbc02d', '#ab47bc', '#1976d2', '#43a047',
                  '#e53935', '#00bcd4', '#ff9800']
        return {
            'color': colors[index % len(colors)],
            'linewidth': 1.2,
            'alpha': 0.85,
            'label': name
        }

    def _optimize_rendering(self):
        """优化渲染性能"""
        try:
            # 启用双缓冲
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAutoFillBackground(True)

            # 优化matplotlib设置
            plt.style.use('fast')
            self.figure.set_dpi(100)

            # 禁用不必要的特性
            plt.rcParams['path.simplify'] = True
            plt.rcParams['path.simplify_threshold'] = 1.0
            plt.rcParams['agg.path.chunksize'] = 20000

            # 优化布局
            self.figure.set_tight_layout(False)
            self.figure.set_constrained_layout(True)

        except Exception as e:
            self.error_occurred.emit(f"优化渲染失败: {str(e)}")

    def _on_render_progress(self, progress: int, message: str):
        """处理渲染进度"""
        self.update_loading_progress(progress, message)

    def _on_render_complete(self):
        """处理渲染完成"""
        self.close_loading_dialog()

    def _on_render_error(self, error: str):
        """处理渲染错误"""
        self.error_occurred.emit(error)
        self.close_loading_dialog()

    def _calculate_macd(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        close = data['close']
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_boll(self, data: pd.DataFrame, n: int = 20, k: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带指标"""
        mid = data['close'].rolling(n).mean()
        std = data['close'].rolling(n).std()
        upper = mid + k * std
        lower = mid - k * std
        return mid, upper, lower

    def _get_active_indicators(self) -> List[str]:
        """获取当前激活的指标列表"""
        active = []
        if hasattr(self, 'indicator_list'):
            for item in self.indicator_list.selectedItems():
                active.append(item.text())
        return active

    def _on_calculation_progress(self, progress: int, message: str):
        """处理计算进度"""
        self.update_loading_progress(progress, message)

    def _on_calculation_complete(self, results: dict):
        """处理计算完成"""
        try:
            # 更新图表数据
            self._update_chart_with_results(results)

        except Exception as e:
            self.error_occurred.emit(f"更新图表数据失败: {str(e)}")

    def _on_calculation_error(self, error: str):
        """处理计算错误"""
        self.error_occurred.emit(error)
        self.close_loading_dialog()

    def _update_chart_with_results(self, results: dict):
        """使用计算结果更新图表"""
        try:
            if not hasattr(self, 'figure') or not hasattr(self, 'canvas'):
                return

            # 清除现有图表
            self.figure.clear()

            # 创建子图
            gs = self.figure.add_gridspec(
                3, 1, height_ratios=[3, 1, 1], hspace=0.05)
            price_ax = self.figure.add_subplot(gs[0])
            volume_ax = self.figure.add_subplot(gs[1], sharex=price_ax)
            indicator_ax = self.figure.add_subplot(gs[2], sharex=price_ax)

            # 使用优化的渲染器绘制图表
            self.renderer.render_candlesticks(
                price_ax, self.current_kdata, self._get_style())
            self.renderer.render_volume(
                volume_ax, self.current_kdata, self._get_style())

            # 绘制指标
            for name, data in results.items():
                if isinstance(data, tuple):
                    for i, series in enumerate(data):
                        self.renderer.render_line(
                            indicator_ax,
                            series,
                            self._get_indicator_style(name, i)
                        )
                else:
                    self.renderer.render_line(
                        indicator_ax,
                        data,
                        self._get_indicator_style(name)
                    )

            # 优化布局
            self.figure.tight_layout(rect=[0, 0, 1, 1])
            self.figure.subplots_adjust(
                left=0.01, right=0.99, top=0.99, bottom=0.06, hspace=0.00
            )

            # 更新画布
            self.canvas.draw_idle()

            # 关闭加载对话框
            self.close_loading_dialog()

        except Exception as e:
            self.error_occurred.emit(f"更新图表显示失败: {str(e)}")

    def _get_style(self) -> Dict[str, Any]:
        """获取当前主题样式"""
        theme_colors = self.theme_manager.get_theme_colors()
        return {
            'up_color': theme_colors.get('k_up', '#e60000'),
            'down_color': theme_colors.get('k_down', '#1dbf60'),
            'edge_color': theme_colors.get('k_edge', '#2c3140'),
            'volume_alpha': 0.5,
            'grid_color': theme_colors.get('chart_grid', '#2c3140'),
            'background_color': theme_colors.get('chart_background', '#181c24')
        }

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
                '5分钟': '5'
            }

            if period in period_map:
                self.current_period = period_map[period]
                self.period_changed.emit(self.current_period)

        except Exception as e:
            error_msg = f"处理周期变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_indicator_changed(self, indicator: str):
        """处理指标变更事件

        Args:
            indicator: 指标名称
        """
        try:
            self.indicator_changed.emit(indicator)
            self.add_indicator(indicator)

        except Exception as e:
            error_msg = f"处理指标变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def clear_chart(self):
        """Clear chart data"""
        try:
            # 清除图表数据
            if hasattr(self, 'figure'):
                self.figure.clear()

            # 重置当前数据
            self.current_kdata = None
            self.current_signals = []
            self.current_indicator = None

            # 重新创建子图
            if hasattr(self, 'figure'):
                self.price_ax = self.figure.add_subplot(211)  # K线图
                self.volume_ax = self.figure.add_subplot(212)  # 成交量图

                # 调整布局
                self.figure.tight_layout()

                # 更新画布
                QTimer.singleShot(0, self.canvas.draw)

            self.log_manager.info("图表已清除")

        except Exception as e:
            error_msg = f"清除图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _apply_initial_theme(self):
        """应用初始主题"""
        try:
            theme = self.theme_manager.current_theme
            colors = self.theme_manager.get_theme_colors(theme)

            # 设置图表背景色
            self.figure.patch.set_facecolor(
                colors.get('chart_background', '#181c24'))

            # 设置子图样式
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                if ax is not None:
                    ax.set_facecolor(colors.get('chart_background', '#181c24'))
                    ax.grid(True, color=colors.get('chart_grid',
                            '#2c3140'), linestyle='--', alpha=0.3)
                    ax.tick_params(colors=colors.get('chart_text', '#b0b8c1'))

                    for spine in ax.spines.values():
                        spine.set_color(colors.get('chart_grid', '#2c3140'))

            # 设置画布样式
            self.canvas.setStyleSheet(
                f"background: {colors.get('chart_background', '#181c24')}; "
                f"border-radius: 10px; "
                f"border: 1px solid {colors.get('chart_grid', '#2c3140')};"
            )

            # 设置工具栏样式
            if hasattr(self, 'toolbar'):
                self.toolbar.setStyleSheet(
                    f"background: {colors.get('chart_background', '#181c24')}; "
                    f"color: {colors.get('chart_text', '#b0b8c1')}; "
                    f"border: none;"
                )

            # 更新布局
            self.figure.subplots_adjust(
                left=0.08, right=0.92,
                top=0.95, bottom=0.05,
                hspace=0.1
            )

            # 刷新画布
            self.canvas.draw_idle()

        except Exception as e:
            self.log_manager.error(f"应用初始主题失败: {str(e)}")

    def _toggle_theme(self):
        """切换主题"""
        try:
            # 获取当前主题
            current_theme = self.theme_manager.current_theme

            # 切换主题
            new_theme = Theme.DEEPBLUE if current_theme == Theme.LIGHT else Theme.LIGHT

            # 更新主题
            self._update_chart_theme(new_theme)

            # 更新按钮图标
            self._update_theme_button()

            self.log_manager.info(f"主题已切换为: {new_theme.name}")

        except Exception as e:
            self.log_manager.error(f"切换主题失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _update_theme_button(self):
        """更新主题按钮图标"""
        try:
            current_theme = self.theme_manager.current_theme
            icon_path = "icons/theme_dark.png" if current_theme == Theme.LIGHT else "icons/theme_light.png"
            self.theme_button.setIcon(QIcon(icon_path))
            self.theme_button.setToolTip(
                "切换到深色主题" if current_theme == Theme.LIGHT else "切换到浅色主题")
        except Exception as e:
            self.log_manager.error(f"更新主题按钮失败: {str(e)}")

    def _update_chart_theme(self, theme: Theme):
        """更新图表主题样式

        Args:
            theme: 主题枚举值
        """
        try:
            # 设置主题
            self.theme_manager.set_theme(theme)

            # 获取主题颜色
            colors = self.theme_manager.get_theme_colors(theme)

            # 更新图表背景色
            self.figure.patch.set_facecolor(
                colors.get('chart_background', '#181c24'))

            # 更新子图样式
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                if ax is not None:
                    # 设置背景色和网格
                    ax.set_facecolor(colors.get('chart_background', '#181c24'))
                    ax.grid(True, color=colors.get('chart_grid',
                            '#2c3140'), linestyle='--', alpha=0.3)

                    # 设置刻度颜色
                    ax.tick_params(colors=colors.get('chart_text', '#b0b8c1'))

                    # 设置边框颜色
                    for spine in ax.spines.values():
                        spine.set_color(colors.get('chart_grid', '#2c3140'))

            # 更新画布样式
            self.canvas.setStyleSheet(
                f"background: {colors.get('chart_background', '#181c24')}; "
                f"border-radius: 10px; "
                f"border: 1px solid {colors.get('chart_grid', '#2c3140')};"
            )

            # 更新工具栏样式
            if hasattr(self, 'toolbar'):
                self.toolbar.setStyleSheet(
                    f"background: {colors.get('chart_background', '#181c24')}; "
                    f"color: {colors.get('chart_text', '#b0b8c1')}; "
                    f"border: none;"
                )

            # 更新布局
            self.figure.subplots_adjust(
                left=0.08, right=0.92,
                top=0.95, bottom=0.05,
                hspace=0.1
            )

            # 刷新画布
            self.canvas.draw_idle()

        except Exception as e:
            self.log_manager.error(f"更新图表主题失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def update_performance_chart(self, metrics: dict):
        """更新性能图表

        Args:
            metrics: 性能指标字典
        """
        try:
            # 清除现有图表
            self.figure.clear()

            # 创建子图
            gs = self.figure.add_gridspec(2, 2)

            # 月度收益热力图
            ax1 = self.figure.add_subplot(gs[0, 0])
            if 'monthly_returns' in metrics:
                monthly_returns = metrics['monthly_returns']
                sns.heatmap(monthly_returns, ax=ax1, cmap='RdYlGn',
                            center=0, annot=True, fmt='.1%')
                ax1.set_title('月度收益热力图')

            # 收益分布直方图
            ax2 = self.figure.add_subplot(gs[0, 1])
            if 'daily_returns' in metrics:
                sns.histplot(metrics['daily_returns'], ax=ax2,
                             bins=50, kde=True)
                ax2.set_title('收益分布')

            # 滚动收益
            ax3 = self.figure.add_subplot(gs[1, 0])
            if 'rolling_returns' in metrics:
                ax3.plot(metrics['rolling_returns'])
                ax3.set_title('滚动收益')

            # 滚动波动率
            ax4 = self.figure.add_subplot(gs[1, 1])
            if 'rolling_volatility' in metrics:
                ax4.plot(metrics['rolling_volatility'])
                ax4.set_title('滚动波动率')

            # 调整布局
            self.figure.tight_layout()

            # 更新画布
            self.canvas.draw()

            self.log_manager.info("性能图表更新完成")

        except Exception as e:
            error_msg = f"更新性能图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            # 停止更新定时器
            if hasattr(self, '_update_timer'):
                self._update_timer.stop()

            # 清理资源
            self.clear_indicators()
            self.figure.clear()

            super().closeEvent(event)

        except Exception as e:
            self.log_manager.error(f"关闭事件处理失败: {str(e)}")

    def plot_kline(self, ax, kdata):
        """绘制K线图（支持hikyuu KData或DataFrame）"""
        try:
            if hasattr(kdata, 'get_datetime_list'):
                dates = kdata.get_datetime_list()
                opens = kdata.get_open()
                closes = kdata.get_close()
                highs = kdata.get_high()
                lows = kdata.get_low()
            else:
                dates = kdata.index
                opens = kdata['open']
                closes = kdata['close']
                highs = kdata['high']
                lows = kdata['low']
            colors = ['red' if c >= o else 'green' for o,
                      c in zip(opens, closes)]
            for i in range(len(dates)):
                ax.bar(dates[i], closes[i] - opens[i],
                       bottom=opens[i], width=0.6, color=colors[i])
                ax.plot([dates[i], dates[i]], [lows[i], highs[i]],
                        color=colors[i], linewidth=1)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.grid(True, linestyle='--', alpha=0.5)
        except Exception as e:
            print(f"绘制K线图失败: {str(e)}")

    def plot_volume(self, ax, kdata):
        try:
            if hasattr(kdata, 'get_datetime_list'):
                dates = kdata.get_datetime_list()
                volumes = kdata.get_volume()
                closes = kdata.get_close()
                opens = kdata.get_open()
            else:
                dates = kdata.index
                volumes = kdata['volume']
                closes = kdata['close']
                opens = kdata['open']
            colors = ['red' if c >= o else 'green' for o,
                      c in zip(opens, closes)]
            ax.bar(dates, volumes, color=colors, alpha=0.5)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.grid(True, linestyle='--', alpha=0.5)
        except Exception as e:
            print(f"绘制成交量图失败: {str(e)}")

    def plot_ma(self, ax, kdata, n_list=[5, 10, 20, 60]):
        try:
            close = kdata['close'] if isinstance(
                kdata, pd.DataFrame) else kdata.get_close()
            idx = kdata.index if isinstance(
                kdata, pd.DataFrame) else kdata.get_datetime_list()
            with ThreadPoolExecutor() as pool:
                results = list(
                    pool.map(lambda n: (n, calc_ma(close, n)), n_list))
            for n, ma in results:
                ax.plot(idx, ma, label=f'MA{n}', linewidth=1)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制MA失败: {str(e)}")

    def plot_macd(self, ax, kdata, fast_n=12, slow_n=26, signal_n=9):
        try:
            close = kdata['close'] if isinstance(
                kdata, pd.DataFrame) else kdata.get_close()
            idx = kdata.index if isinstance(
                kdata, pd.DataFrame) else kdata.get_datetime_list()
            macd, signal, hist = calc_macd(close, fast_n, slow_n, signal_n)
            ax.plot(idx, macd, label='MACD', color='blue')
            ax.plot(idx, signal, label='Signal', color='red')
            colors = ['red' if h < 0 else 'green' for h in hist]
            ax.bar(idx, hist, color=colors, alpha=0.5, label='Histogram')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制MACD失败: {str(e)}")

    def plot_rsi(self, ax, kdata, n=14):
        try:
            close = kdata['close'] if isinstance(
                kdata, pd.DataFrame) else kdata.get_close()
            idx = kdata.index if isinstance(
                kdata, pd.DataFrame) else kdata.get_datetime_list()
            rsi = calc_rsi(close, n)
            ax.plot(idx, rsi, label=f'RSI({n})', color='purple')
            ax.axhline(y=70, color='r', linestyle='--', label='超买线')
            ax.axhline(y=30, color='g', linestyle='--', label='超卖线')
            ax.set_ylim(0, 100)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制RSI失败: {str(e)}")

    def plot_kdj(self, ax, kdata, n=9, m1=3, m2=3):
        try:
            df = kdata if isinstance(kdata, pd.DataFrame) else kdata.to_df()
            idx = df.index
            k, d, j = calc_kdj(df, n, m1, m2)
            ax.plot(idx, k, label='K', color='blue')
            ax.plot(idx, d, label='D', color='red')
            ax.plot(idx, j, label='J', color='green')
            ax.axhline(y=80, color='r', linestyle='--', label='超买线')
            ax.axhline(y=20, color='g', linestyle='--', label='超卖线')
            ax.set_ylim(0, 100)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制KDJ失败: {str(e)}")

    def plot_boll(self, ax, kdata, n=20, p=2):
        try:
            close = kdata['close'] if isinstance(
                kdata, pd.DataFrame) else kdata.get_close()
            idx = kdata.index if isinstance(
                kdata, pd.DataFrame) else kdata.get_datetime_list()
            mid, upper, lower = calc_boll(close, n, p)
            ax.plot(idx, mid, label='中轨', color='blue')
            ax.plot(idx, upper, label='上轨', color='red', linestyle='--')
            ax.plot(idx, lower, label='下轨', color='green', linestyle='--')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制布林带失败: {str(e)}")

    def plot_atr(self, ax, kdata, n=14):
        try:
            df = kdata if isinstance(kdata, pd.DataFrame) else kdata.to_df()
            idx = df.index
            atr = calc_atr(df, n)
            ax.plot(idx, atr, label=f'ATR({n})', color='blue')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制ATR失败: {str(e)}")

    def plot_obv(self, ax, kdata):
        try:
            df = kdata if isinstance(kdata, pd.DataFrame) else kdata.to_df()
            idx = df.index
            obv = calc_obv(df)
            ax.plot(idx, obv, label='OBV', color='purple')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制OBV失败: {str(e)}")

    def plot_cci(self, ax, kdata, n=14):
        try:
            df = kdata if isinstance(kdata, pd.DataFrame) else kdata.to_df()
            idx = df.index
            cci = calc_cci(df, n)
            ax.plot(idx, cci, label=f'CCI({n})', color='blue')
            ax.axhline(y=100, color='r', linestyle='--', label='超买线')
            ax.axhline(y=-100, color='g', linestyle='--', label='超卖线')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制CCI失败: {str(e)}")

    def plot_profit_curve(self, ax, tm, dates):
        try:
            profit_curve = tm.get_profit_curve(dates)
            ax.plot(dates, profit_curve, label='收益曲线', color='blue')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制收益曲线失败: {str(e)}")

    def plot_drawdown(self, ax, tm, dates):
        try:
            drawdown = tm.get_drawdown(dates)
            ax.plot(dates, drawdown, label='回撤曲线', color='red')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制回撤曲线失败: {str(e)}")

    def plot_position(self, ax, tm, dates):
        try:
            position = tm.get_position(dates)
            ax.plot(dates, position, label='持仓曲线', color='green')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.legend()
        except Exception as e:
            print(f"绘制持仓曲线失败: {str(e)}")

    def plot_trade_points(self, ax, tm, kdata):
        try:
            dates = kdata.get_datetime_list() if hasattr(
                kdata, 'get_datetime_list') else kdata.index
            closes = kdata.get_close() if hasattr(
                kdata, 'get_close') else kdata['close']
            trades = tm.get_trade_list()
            buy_dates = [
                t.datetime for t in trades if t.business == BUSINESS.BUY]
            buy_prices = [
                t.price for t in trades if t.business == BUSINESS.BUY]
            if buy_dates:
                ax.scatter(buy_dates, buy_prices, color='red',
                           marker='^', label='买入点', s=100)
            sell_dates = [
                t.datetime for t in trades if t.business == BUSINESS.SELL]
            sell_prices = [
                t.price for t in trades if t.business == BUSINESS.SELL]
            if sell_dates:
                ax.scatter(sell_dates, sell_prices, color='green',
                           marker='v', label='卖出点', s=100)
            ax.legend()
        except Exception as e:
            print(f"绘制交易点失败: {str(e)}")

    def zoom_in(self):
        """放大图表"""
        try:
            if not hasattr(self, 'figure') or not hasattr(self, 'canvas'):
                return
            ax = self.figure.gca()
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            self._zoom_history.append((xlim, ylim))
            # 放大10%
            ax.set_xlim(xlim[0] + (xlim[1] - xlim[0]) * 0.1,
                        xlim[1] - (xlim[1] - xlim[0]) * 0.1)
            ax.set_ylim(ylim[0] + (ylim[1] - ylim[0]) * 0.1,
                        ylim[1] - (ylim[1] - ylim[0]) * 0.1)
            self.canvas.draw()
            self._zoom_level = min(self._zoom_level * 1.1, self._max_zoom)
            self.zoom_changed.emit(self._zoom_level)
            self.log_manager.info(f"图表已放大，当前缩放级别: {self._zoom_level:.2f}")
        except Exception as e:
            error_msg = f"放大图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def zoom_out(self):
        """缩小图表"""
        try:
            if not hasattr(self, 'figure') or not hasattr(self, 'canvas'):
                return
            ax = self.figure.gca()
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            self._zoom_history.append((xlim, ylim))
            # 缩小10%
            ax.set_xlim(xlim[0] - (xlim[1] - xlim[0]) * 0.1,
                        xlim[1] + (xlim[1] - xlim[0]) * 0.1)
            ax.set_ylim(ylim[0] - (ylim[1] - ylim[0]) * 0.1,
                        ylim[1] + (ylim[1] - ylim[0]) * 0.1)
            self.canvas.draw()
            self._zoom_level = max(self._zoom_level / 1.1, self._min_zoom)
            self.zoom_changed.emit(self._zoom_level)
            self.log_manager.info(f"图表已缩小，当前缩放级别: {self._zoom_level:.2f}")
        except Exception as e:
            error_msg = f"缩小图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def reset_zoom(self):
        """重置图表缩放"""
        try:
            if not hasattr(self, 'figure') or not hasattr(self, 'canvas'):
                return
            self._zoom_level = 1.0
            self._zoom_history.clear()
            self.zoom_changed.emit(self._zoom_level)
            self.figure.tight_layout(rect=[0, 0, 1, 1])
            for ax in self.figure.axes:
                ax.autoscale()
            self.canvas.draw()
            self.log_manager.info("图表缩放已重置")
        except Exception as e:
            error_msg = f"重置图表缩放失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def undo_zoom(self):
        """撤销上一次缩放操作"""
        try:
            if not self._zoom_history:
                return
            xlim, ylim = self._zoom_history.pop()
            ax = self.figure.gca()
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            self._zoom_level = max(self._zoom_level / 1.1, self._min_zoom)
            self.zoom_changed.emit(self._zoom_level)
            self.canvas.draw()
            self.log_manager.info("已撤销上一次缩放操作")
        except Exception as e:
            error_msg = f"撤销缩放操作失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def resizeEvent(self, event):
        """处理窗口大小变化"""
        super().resizeEvent(event)
        if hasattr(self, 'canvas'):
            self.canvas.resize(self.size())
            # 重新设置固定边距
            self.figure.subplots_adjust(
                left=0.08, right=0.92,
                top=0.95, bottom=0.05,
                hspace=0.1
            )
            self.canvas.draw_idle()

    def add_indicator(self, indicator_data):
        """添加技术指标

        Args:
            indicator_data: 指标数据
        """
        try:
            if indicator_data is None:
                self.log_manager.warning("指标数据为空")
                return

            # 将添加指标任务加入队列
            self.queue_update(self._add_indicator_impl, indicator_data)

        except Exception as e:
            error_msg = f"添加指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _add_indicator_impl(self, indicator_data, indicator_colors: list = None):
        try:
            self.current_indicator = indicator_data
            if hasattr(self, 'price_ax'):
                color_map = indicator_colors or [
                    '#fbc02d', '#ab47bc', '#1976d2', '#43a047', '#e53935', '#00bcd4', '#ff9800']
                for i, (name, series) in enumerate(indicator_data.items()):
                    self.price_ax.plot(
                        series.index, series.values,
                        color=color_map[i % len(color_map)],
                        linewidth=2.2, alpha=0.85, label=name, solid_capstyle='round'
                    )
                self.price_ax.legend(
                    loc='upper left', fontsize=9, frameon=False)
                QTimer.singleShot(0, self.canvas.draw)
            self.log_manager.info(f"添加指标 {indicator_data.name} 完成")
        except Exception as e:
            error_msg = f"添加指标实现失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def plot_signals(self, signals):
        """绘制交易信号

        Args:
            signals: 信号数据列表
        """
        try:
            if not signals:
                self.log_manager.warning("信号数据为空")
                return

            # 将绘制信号任务加入队列
            self.queue_update(self._plot_signals_impl, signals)

        except Exception as e:
            error_msg = f"绘制信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _plot_signals_impl(self, signals):
        """实际的绘制信号实现

        Args:
            signals: 信号数据列表
        """
        try:
            # 保存当前信号
            self.current_signals = signals

            if hasattr(self, 'price_ax') and self.current_kdata is not None:
                # 获取当前K线数据的时间索引
                dates = self.current_kdata.index
                dates_dict = {str(date): i for i, date in enumerate(dates)}

                # 绘制信号
                for signal in signals:
                    if str(signal['date']) in dates_dict:
                        idx = dates_dict[str(signal['date'])]
                        price = signal['price']

                        if signal['type'] == 'buy':
                            marker = '^'
                            color = 'r'
                            label = '买入'
                        else:
                            marker = 'v'
                            color = 'g'
                            label = '卖出'

                        self.price_ax.plot(idx, price, marker=marker,
                                           color=color, markersize=8,
                                           label=label)

                # 更新图例
                handles, labels = self.price_ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                self.price_ax.legend(by_label.values(), by_label.keys(),
                                     loc='upper left', fontsize=8)

                # 更新画布
                QTimer.singleShot(0, self.canvas.draw)

            self.log_manager.info("绘制信号完成")

        except Exception as e:
            error_msg = f"绘制信号实现失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def clear_indicators(self):
        """清除所有指标"""
        try:
            self.current_indicator = None
            if hasattr(self, 'price_ax'):
                # 保留主图K线，清除其他线条
                # 只需注释或删除相关行即可
                # lines = self.price_ax.get_lines()
                # if len(lines) > 0:
                #     for line in lines[1:]:  # 跳过第一条K线
                #         line.remove()

                # 更新图例
                self.price_ax.legend(loc='upper left', fontsize=8)

                # 更新画布
                QTimer.singleShot(0, self.canvas.draw)

            self.log_manager.info("清除指标完成")

        except Exception as e:
            error_msg = f"清除指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _init_figure_layout(self):
        """初始化图表布局"""
        try:
            # 创建图表和画布，禁用所有自动布局
            self.figure = Figure(figsize=(8, 6), dpi=100,
                                 constrained_layout=False,
                                 tight_layout=False)
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)

            # 创建子图，使用 GridSpec
            self.gs = self.figure.add_gridspec(3, 1, height_ratios=[3, 1, 1])
            self.price_ax = self.figure.add_subplot(self.gs[0])
            self.volume_ax = self.figure.add_subplot(
                self.gs[1], sharex=self.price_ax)
            self.indicator_ax = self.figure.add_subplot(
                self.gs[2], sharex=self.price_ax)

            # 隐藏不需要的刻度标签
            self.volume_ax.set_xticklabels([])
            self.price_ax.set_xticklabels([])

            # 设置固定边距
            self.figure.subplots_adjust(
                left=0.08, right=0.92,
                top=0.95, bottom=0.05,
                hspace=0.1
            )

            # 添加到布局
            self.layout().addWidget(self.canvas)

        except Exception as e:
            self.log_manager.error(f"初始化图表布局失败: {str(e)}")

    def _optimize_display(self):
        """优化显示"""
        try:
            # 优化matplotlib设置
            plt.style.use('fast')
            self.figure.set_dpi(100)

            # 禁用不必要的特性
            plt.rcParams['path.simplify'] = True
            plt.rcParams['path.simplify_threshold'] = 1.0
            plt.rcParams['agg.path.chunksize'] = 20000

            # 统一使用 subplots_adjust 进行布局管理
            self.figure.set_tight_layout(False)
            self.figure.set_constrained_layout(False)

            # 设置固定边距
            self.figure.subplots_adjust(
                left=0.08, right=0.92,
                top=0.95, bottom=0.05,
                hspace=0.1
            )

            # 优化网格显示
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.grid(True, linestyle='--', alpha=0.3)
                ax.tick_params(axis='both', which='major', labelsize=8)

        except Exception as e:
            self.error_occurred.emit(f"优化显示失败: {str(e)}")
