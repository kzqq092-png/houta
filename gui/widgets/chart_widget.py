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
            self.crosshair_enabled = True  # 默认开启十字线

            # 初始化缓存管理器
            self.cache_manager = CacheManager(max_size=100)  # 图表最多缓存100个

            # 启用双缓冲
            # self.setAttribute(Qt.WA_PaintOnScreen, True)
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
        """初始化UI，移除十字光标按钮，默认开启十字光标"""
        try:
            self.setLayout(QVBoxLayout())
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.layout().setSpacing(0)
            # 不再添加matplotlib工具栏
            # toolbar_layout = QHBoxLayout()
            # ... 省略 ...
            # self.toolbar = NavigationToolbar(self.canvas, self)
            # self.layout().addWidget(self.toolbar)
            # ... 省略 ...
            # 只添加canvas
            self._init_figure_layout()
            self._init_zoom_interaction()  # 新增：自定义缩放交互
        except Exception as e:
            self.log_manager.error(f"初始化UI失败: {str(e)}")

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
        """更新图表，自动开启十字光标"""
        try:
            if not data or 'kdata' not in data:
                return
            kdata = data['kdata']
            self.current_kdata = kdata
            self.show_loading_dialog()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.clear()
            style = self._get_chart_style()
            self.renderer.render_candlesticks(self.price_ax, kdata, style)
            self.renderer.render_volume(self.volume_ax, kdata, style)
            self._render_indicators(kdata)
            self._optimize_display()
            # 自动设置x轴边界，防止超出数据范围
            if not kdata.empty:
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    ax.set_xlim(kdata.index[0], kdata.index[-1])
            self.canvas.draw_idle()
            self.close_loading_dialog()
            # 自动开启十字光标
            self.crosshair_enabled = True
            self.enable_crosshair()
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
        """获取图表样式，所有颜色从theme_manager.get_theme_colors获取"""
        try:
            colors = self.theme_manager.get_theme_colors()
            return {
                'up_color': colors.get('k_up', '#e74c3c'),
                'down_color': colors.get('k_down', '#27ae60'),
                'edge_color': colors.get('k_edge', '#2c3140'),
                'volume_up_color': colors.get('volume_up', '#e74c3c'),
                'volume_down_color': colors.get('volume_down', '#27ae60'),
                'volume_alpha': colors.get('volume_alpha', 0.5),
                'grid_color': colors.get('chart_grid', '#e0e0e0'),
                'background_color': colors.get('chart_background', '#ffffff'),
                'text_color': colors.get('chart_text', '#222b45'),
                'axis_color': colors.get('chart_grid', '#e0e0e0'),
                'label_color': colors.get('chart_text', '#222b45'),
                'border_color': colors.get('chart_grid', '#e0e0e0'),
            }
        except Exception as e:
            self.log_manager.error(f"获取图表样式失败: {str(e)}")
            return {}

    def _get_indicator_style(self, name: str, index: int = 0) -> Dict[str, Any]:
        """获取指标样式，颜色从theme_manager.get_theme_colors获取"""
        colors = self.theme_manager.get_theme_colors()
        indicator_colors = colors.get('indicator_colors', [
            '#fbc02d', '#ab47bc', '#1976d2', '#43a047', '#e53935', '#00bcd4', '#ff9800'])
        return {
            'color': indicator_colors[index % len(indicator_colors)],
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

            # 优化布局（只保留subplots_adjust，去除set_tight_layout和set_constrained_layout）
            # self.figure.set_tight_layout(False)
            # self.figure.set_constrained_layout(True)

            # 设置固定边距
            self.figure.subplots_adjust(
                left=0.02, right=0.98,
                top=0.98, bottom=0.02,
                hspace=0.1
            )

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
        """应用初始主题，并优化坐标轴贴边和刻度方向"""
        try:
            theme = self.theme_manager.current_theme
            colors = self.theme_manager.get_theme_colors(theme)
            self.figure.patch.set_facecolor(
                colors.get('chart_background', '#181c24'))
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                if ax is not None:
                    ax.set_facecolor(colors.get('chart_background', '#181c24'))
                    ax.grid(True, color=colors.get('chart_grid',
                            '#2c3140'), linestyle='--', alpha=0.3)
                    ax.tick_params(colors=colors.get(
                        'chart_text', '#b0b8c1'), direction='in', length=6)
                    # 让坐标轴贴边
                    ax.spines['left'].set_position(('outward', 0))
                    ax.spines['bottom'].set_position(('outward', 0))
                    ax.spines['right'].set_visible(False)
                    ax.spines['top'].set_visible(False)
                    # 标签靠近边界
                    ax.yaxis.set_label_position('left')
                    ax.xaxis.set_label_position('bottom')
            self.canvas.setStyleSheet(
                f"background: {colors.get('chart_background', '#181c24')}; border-radius: 10px; border: 1px solid {colors.get('chart_grid', '#2c3140')};")
            if hasattr(self, 'toolbar'):
                self.toolbar.setStyleSheet(
                    f"background: {colors.get('chart_background', '#181c24')}; color: {colors.get('chart_text', '#b0b8c1')}; border: none;")
            self.figure.subplots_adjust(
                left=0.01, right=0.99, top=0.99, bottom=0.06, hspace=0.00)
            self.canvas.draw_idle()
        except Exception as e:
            self.log_manager.error(f"应用初始主题失败: {str(e)}")

    def enable_crosshair(self):
        """启用十字光标和详细信息显示，alpha始终为1.0"""
        if not hasattr(self, 'canvas') or not hasattr(self, 'price_ax'):
            return
        if not hasattr(self, '_crosshair_cid') or self._crosshair_cid is None:
            self._crosshair_cid = self.canvas.mpl_connect(
                'motion_notify_event', self._on_mouse_move_crosshair)
        if not hasattr(self, '_crosshair_lines') or not self._crosshair_lines:
            self._crosshair_lines = [
                self.price_ax.axhline(
                    color='gray', lw=0.5, ls='--', alpha=1.0, visible=False),
                self.price_ax.axvline(
                    color='gray', lw=0.5, ls='--', alpha=1.0, visible=False)
            ]
            self._crosshair_text = self.price_ax.text(
                0.02, 0.98, '', transform=self.price_ax.transAxes, va='top', ha='left',
                fontsize=9, color='black',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                visible=False
            )

    def _on_mouse_move_crosshair(self, event):
        if not self.crosshair_enabled or not event.inaxes:
            if hasattr(self, '_crosshair_lines'):
                for line in self._crosshair_lines:
                    line.set_visible(False)
            if hasattr(self, '_crosshair_text'):
                self._crosshair_text.set_visible(False)
            self.canvas.draw_idle()
            return
        x, y = event.xdata, event.ydata
        for line in self._crosshair_lines:
            line.set_visible(True)
        self._crosshair_lines[0].set_ydata([y, y])
        self._crosshair_lines[1].set_xdata([x, x])
        self._crosshair_text.set_visible(True)
        # 找到最近的索引
        if self.current_kdata is not None and len(self.current_kdata) > 0:
            idx = int(np.clip(round(x), 0, len(self.current_kdata)-1))
            row = self.current_kdata.iloc[idx]
            info = f"日期: {row.name.strftime('%Y-%m-%d')}\n开:{row.open:.2f} 收:{row.close:.2f}\n高:{row.high:.2f} 低:{row.low:.2f}\n量:{row.volume:.0f}"
            self._crosshair_text.set_text(info)
        self.canvas.draw_idle()

    def _init_figure_layout(self):
        """初始化图表布局"""
        try:
            # 创建图表和画布，禁用所有自动布局
            self.figure = Figure(figsize=(15, 8), dpi=100,
                                 constrained_layout=False)
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
                left=0.02, right=0.98,
                top=0.98, bottom=0.02,
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
            # self.figure.set_tight_layout(True)
            self.figure.set_constrained_layout(True)

            # 设置固定边距（已禁用，避免与constrained_layout冲突）
            # self.figure.subplots_adjust(
            #     left=0.02, right=0.98,
            #     top=0.98, bottom=0.02,
            #     hspace=0.1
            # )

            # 优化网格显示
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.grid(True, linestyle='--', alpha=0.5)
                ax.tick_params(axis='both', which='major', labelsize=8)

        except Exception as e:
            self.error_occurred.emit(f"优化显示失败: {str(e)}")

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

    def draw_overview(self, ax, kdata):
        """绘制缩略图（mini map/overview），自动适配主题色并高对比"""
        try:
            colors = self.theme_manager.get_theme_colors()
            # 高对比兜底色
            k_up = colors.get('overview_k_up', colors.get('k_up', '#d32f2f'))
            k_down = colors.get('overview_k_down',
                                colors.get('k_down', '#388e3c'))
            bg = colors.get('overview_background', colors.get(
                'chart_background', '#fafdff'))
            ax.set_facecolor(bg)
            opens = kdata['open']
            closes = kdata['close']
            highs = kdata['high']
            lows = kdata['low']
            x = range(len(opens))
            for i in x:
                color = k_up if closes[i] >= opens[i] else k_down
                # 加粗K线
                ax.plot([i, i], [lows[i], highs[i]], color=color,
                        linewidth=2.0, alpha=1.0, zorder=1)
                ax.bar(i, closes[i] - opens[i], bottom=min(opens[i],
                       closes[i]), width=0.9, color=color, alpha=1.0, zorder=2)
            ax.grid(False)
            ax.set_xticks([])
            ax.set_yticks([])
        except Exception as e:
            self.log_manager.error(f"绘制缩略图失败: {str(e)}")

    def apply_theme(self):
        """应用主题到主图和缩略图，确保K线颜色和UI实时刷新"""
        try:
            # 原有主题应用逻辑
            self._apply_initial_theme()
            # 强制刷新主图
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})
            # 强制刷新缩略图（如有）
            if hasattr(self, 'overview_ax') and self.current_kdata is not None:
                self.draw_overview(self.overview_ax, self.current_kdata)
        except Exception as e:
            self.log_manager.error(f"应用主题到主图和缩略图失败: {str(e)}")

    def _init_zoom_interaction(self):
        """自定义鼠标缩放交互，支持多级缩放、右键还原、滚轮缩放"""
        self._zoom_press_x = None
        self._zoom_rect = None
        self._zoom_history = []  # 多级缩放历史
        self.canvas.mpl_connect('button_press_event', self._on_zoom_press)
        self.canvas.mpl_connect('motion_notify_event', self._on_zoom_motion)
        self.canvas.mpl_connect('button_release_event', self._on_zoom_release)
        self.canvas.mpl_connect('button_press_event',
                                self._on_zoom_right_click)
        self.canvas.mpl_connect('scroll_event', self._on_zoom_scroll)

    def _on_zoom_press(self, event):
        if event.inaxes != self.price_ax or event.button != 1:
            return
        self._zoom_press_x = event.xdata
        if self._zoom_rect:
            self._zoom_rect.remove()
        self._zoom_rect = self.price_ax.axvspan(
            event.xdata, event.xdata, color='blue', alpha=0.18)
        self.canvas.draw_idle()

    def _on_zoom_motion(self, event):
        if self._zoom_press_x is None or event.inaxes != self.price_ax or event.button != 1:
            return
        x0, x1 = self._zoom_press_x, event.xdata
        if self._zoom_rect:
            self._zoom_rect.remove()
        self._zoom_rect = self.price_ax.axvspan(
            x0, x1, color='blue', alpha=0.18)
        self.canvas.draw_idle()

    def _on_zoom_release(self, event):
        if self._zoom_press_x is None or event.inaxes != self.price_ax or event.button != 1:
            return
        x0, x1 = self._zoom_press_x, event.xdata
        if self._zoom_rect:
            self._zoom_rect.remove()
            self._zoom_rect = None
        if abs(x1 - x0) < 1:  # 拖动太短不缩放
            self._zoom_press_x = None
            self.canvas.draw_idle()
            return
        if x1 > x0:
            # 左→右：放大
            self._zoom_history.append(self.price_ax.get_xlim())
            self.price_ax.set_xlim(x0, x1)
        else:
            # 右→左：还原到上一级
            if self._zoom_history:
                prev_xlim = self._zoom_history.pop()
                self.price_ax.set_xlim(prev_xlim)
            else:
                self.price_ax.set_xlim(auto=True)
        self._zoom_press_x = None
        self.canvas.draw_idle()

    def _on_zoom_right_click(self, event):
        # 右键单击还原到上一级
        if event.inaxes == self.price_ax and event.button == 3:
            if self._zoom_history:
                prev_xlim = self._zoom_history.pop()
                self.price_ax.set_xlim(prev_xlim)
            else:
                self.price_ax.set_xlim(auto=True)
            self.canvas.draw_idle()

    def _on_zoom_scroll(self, event):
        # 滚轮缩放，鼠标为中心放大/缩小
        if event.inaxes != self.price_ax:
            return
        cur_xlim = self.price_ax.get_xlim()
        xdata = event.xdata
        scale_factor = 0.8 if event.button == 'up' else 1.25
        left = xdata - (xdata - cur_xlim[0]) * scale_factor
        right = xdata + (cur_xlim[1] - xdata) * scale_factor
        self._zoom_history.append(cur_xlim)
        self.price_ax.set_xlim(left, right)
        self.canvas.draw_idle()
