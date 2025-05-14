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
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None, theme_manager=None, log_manager=None, data_manager=None):
        """初始化图表控件

        Args:
            parent: Parent widget
            config_manager: Optional ConfigManager instance to use
            theme_manager: Optional theme manager to use
            log_manager: Optional log manager to use
            data_manager: Optional data manager to use
        """
        try:
            super().__init__(parent)
            self.setAcceptDrops(True)  # 确保控件能接收拖拽

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

            # 初始化数据管理器
            self.data_manager = data_manager

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
            self._init_figure_layout()
            self._init_zoom_interaction()  # 新增：自定义缩放交互
            self._optimize_display()  # 保证初始化后也显示网格和刻度
        except Exception as e:
            self.log_manager.error(f"初始化UI失败: {str(e)}")

    def connect_signals(self):
        """连接信号（ChartWidget只负责自身信号定义和发射，不直接连接外部UI控件）"""
        # 此处不再连接period_combo、indicator_combo、clear_button等UI控件的信号
        # 这些控件应由主窗口负责创建和信号连接
        self.log_manager.info("ChartWidget信号连接完成（无UI控件连接）")

    def _process_update_queue(self):
        """处理更新队列中的任务"""
        try:
            if self._update_queue:
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

    def _downsample_kdata(self, kdata, max_points=1200):
        """对K线数据做降采样，提升渲染性能"""
        if len(kdata) <= max_points:
            return kdata
        idx = np.linspace(0, len(kdata)-1, max_points).astype(int)
        return kdata.iloc[idx]

    def update_chart(self, data: dict):
        """唯一K线渲染实现，X轴为等距序号，彻底消除节假日断层。"""
        try:
            if not data or 'kdata' not in data:
                return
            kdata = data['kdata']
            kdata = self._downsample_kdata(kdata)
            kdata = kdata.dropna(how='any')
            kdata = kdata.loc[~kdata.index.duplicated(keep='first')]
            self.current_kdata = kdata
            if not kdata.empty:
                self._ymin = float(kdata['low'].min())
                self._ymax = float(kdata['high'].max())
            else:
                self._ymin = 0
                self._ymax = 1
            self.show_loading_dialog()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.cla()
            style = self._get_chart_style()
            x = np.arange(len(kdata))  # 用等距序号做X轴
            self.renderer.render_candlesticks(self.price_ax, kdata, style, x=x)
            self.renderer.render_volume(self.volume_ax, kdata, style, x=x)
            self._render_indicators(kdata, x=x)
            self._optimize_display()
            if not kdata.empty:
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    ax.set_xlim(0, len(kdata)-1)
                self.price_ax.set_ylim(self._ymin, self._ymax)
                # 设置X轴刻度和标签（间隔显示，防止过密）
                step = max(1, len(kdata)//8)
                xticks = np.arange(0, len(kdata), step)
                xticklabels = [kdata.index[i].strftime(
                    '%Y-%m-%d') for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                self.indicator_ax.set_xticklabels(
                    xticklabels, rotation=30, fontsize=8)
            self.close_loading_dialog()
            # 移除清空X轴刻度的代码，始终显示
            # self.price_ax.set_xticklabels([])
            # self.volume_ax.set_xticklabels([])
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.yaxis.set_tick_params(direction='in', pad=0)
                ax.yaxis.set_label_position('left')
                ax.tick_params(axis='y', direction='in', pad=0)
            self.crosshair_enabled = True
            self.enable_crosshair(force_rebind=True)
            # 左上角显示股票名称和代码
            if hasattr(self, '_stock_info_text') and self._stock_info_text:
                self._stock_info_text.remove()
                self._stock_info_text = None
            stock_name = data.get('title', '')
            stock_code = data.get('stock_code', '')
            info_str = f"{stock_name} ({stock_code})" if stock_code else stock_name
            colors = self.theme_manager.get_theme_colors()
            text_color = colors.get('chart_text', '#222b45')
            bg_color = colors.get('chart_background', '#ffffff')
            self._stock_info_text = self.price_ax.text(
                0.01, 0.98, info_str,
                transform=self.price_ax.transAxes,
                va='top', ha='left',
                fontsize=7,
                color=text_color,
                bbox=dict(facecolor=bg_color, alpha=0.7,
                          edgecolor='none', boxstyle='round,pad=0.2'),
                zorder=200
            )
            self.canvas.draw()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                    label.set_fontsize(8)
                ax.title.set_fontsize(8)
                ax.xaxis.label.set_fontsize(8)
                ax.yaxis.label.set_fontsize(8)
            self._optimize_display()  # 保证每次刷新后都恢复网格和刻度
        except Exception as e:
            self.error_occurred.emit(f"更新图表失败: {str(e)}")
            self.close_loading_dialog()

    def _render_indicators(self, kdata: pd.DataFrame, x=None):
        """渲染技术指标，所有指标与K线对齐，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            indicators = self._get_active_indicators()
            if not indicators:
                return
            if x is None:
                x = np.arange(len(kdata))
            for indicator in indicators:
                style = self._get_indicator_style(indicator)
                if indicator.startswith('MA'):
                    period = int(indicator[2:])
                    ma = kdata['close'].rolling(period).mean().dropna()
                    self.price_ax.plot(x[-len(ma):], ma.values, color=style['color'],
                                       linewidth=style['linewidth'], alpha=style['alpha'], label=indicator)
                elif indicator == 'MACD':
                    macd, signal, hist = self._calculate_macd(kdata)
                    macd = macd.dropna()
                    signal = signal.dropna()
                    hist = hist.dropna()
                    self.indicator_ax.plot(x[-len(macd):], macd.values, color=self._get_indicator_style(
                        'MACD', 0)['color'], linewidth=1.2, alpha=0.85, label='MACD')
                    self.indicator_ax.plot(x[-len(signal):], signal.values, color=self._get_indicator_style(
                        'MACD', 1)['color'], linewidth=1.2, alpha=0.85, label='Signal')
                    if not hist.empty:
                        colors = ['red' if h >= 0 else 'green' for h in hist]
                        self.indicator_ax.bar(
                            x[-len(hist):], hist.values, color=colors, alpha=0.5)
                elif indicator == 'RSI':
                    rsi = self._calculate_rsi(kdata).dropna()
                    self.indicator_ax.plot(x[-len(rsi):], rsi.values, color=style['color'],
                                           linewidth=style['linewidth'], alpha=style['alpha'], label='RSI')
                elif indicator == 'BOLL':
                    mid, upper, lower = self._calculate_boll(kdata)
                    mid = mid.dropna()
                    upper = upper.dropna()
                    lower = lower.dropna()
                    self.price_ax.plot(x[-len(mid):], mid.values, color=self._get_indicator_style(
                        'BOLL', 0)['color'], linewidth=1.2, alpha=0.85, label='BOLL-Mid')
                    self.price_ax.plot(x[-len(upper):], upper.values, color=self._get_indicator_style(
                        'BOLL', 1)['color'], linewidth=1.2, alpha=0.85, label='BOLL-Upper')
                    self.price_ax.plot(x[-len(lower):], lower.values, color=self._get_indicator_style(
                        'BOLL', 2)['color'], linewidth=1.2, alpha=0.85, label='BOLL-Lower')
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

            # 只保留subplots_adjust，不再设置tight_layout或constrained_layout
            self.figure.subplots_adjust(
                left=0.05, right=0.98, top=0.98, bottom=0.06, hspace=0.08)

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
                self._optimize_display()  # 保证清除后也显示网格和刻度

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
            self._optimize_display()  # 保证清除后也显示网格和刻度

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
                    ax.yaxis.set_ticks_position('none')
                    ax.xaxis.set_label_position('bottom')
            self.canvas.setStyleSheet(
                f"background: {colors.get('chart_background', '#181c24')}; border-radius: 10px; border: 1px solid {colors.get('chart_grid', '#2c3140')};")
            if hasattr(self, 'toolbar'):
                self.toolbar.setStyleSheet(
                    f"background: {colors.get('chart_background', '#181c24')}; color: {colors.get('chart_text', '#b0b8c1')}; border: none;")
            self.figure.subplots_adjust(
                left=0.04, right=0.99, top=0.99, bottom=0.06, hspace=0.00)
            self.canvas.draw_idle()
        except Exception as e:
            self.log_manager.error(f"应用初始主题失败: {str(e)}")

    def enable_crosshair(self, force_rebind=False):
        """自动启用十字线，竖线、横线、信息框随鼠标移动，且每次都可强制重新绑定事件，x轴与K线对齐，y轴同步动态显示"""
        import matplotlib.dates as mdates
        theme_colors = self.theme_manager.get_theme_colors()
        primary_color = theme_colors.get('primary', '#1976d2')
        if force_rebind or not hasattr(self, '_crosshair_initialized') or not self._crosshair_initialized:
            # 解绑旧事件
            if hasattr(self, '_crosshair_cid'):
                self.canvas.mpl_disconnect(self._crosshair_cid)
            # 创建竖线、横线
            self._crosshair_lines = [
                self.price_ax.axvline(
                    color=primary_color, lw=1.2, ls='--', alpha=0.55, visible=False, zorder=100),
                self.price_ax.axhline(
                    color=primary_color, lw=1.2, ls='--', alpha=0.55, visible=False, zorder=100)
            ]
            # 信息框（浮窗）
            self._crosshair_text = self.price_ax.text(
                0, 0, '', transform=self.price_ax.transData, va='top', ha='left',
                fontsize=8, color='#23293a',
                bbox=dict(facecolor='#fff', alpha=0.5, edgecolor=primary_color,
                          boxstyle='round,pad=0.5', linewidth=0.8),
                visible=False, zorder=200
            )
            # 保存原始X/Y轴刻度和样式
            self._orig_xticks = None
            self._orig_xticklabels = None
            self._orig_xtick_fontsize = None
            self._orig_xtick_color = None
            self._orig_yticks = None
            self._orig_yticklabels = None
            self._orig_ytick_fontsize = None
            self._orig_ytick_color = None

            def on_mouse_move(event):
                if not event.inaxes or self.current_kdata is None or len(self.current_kdata) == 0 or event.xdata is None:
                    for line in self._crosshair_lines:
                        line.set_visible(False)
                    self._crosshair_text.set_visible(False)
                    # 清除indicator_ax上的十字线覆盖（如果有）
                    if hasattr(self, '_crosshair_xtext') and self._crosshair_xtext:
                        self._crosshair_xtext.set_visible(False)
                    if hasattr(self, '_crosshair_ytext') and self._crosshair_ytext:
                        self._crosshair_ytext.set_visible(False)
                    self.canvas.draw_idle()
                    return
                kdata = self.current_kdata
                x_array = np.arange(len(kdata))  # 等距序号X轴
                idx = int(np.clip(round(event.xdata), 0, len(kdata)-1))
                row = kdata.iloc[idx]
                x_val = x_array[idx]
                y_val = row.close
                # 竖线x，横线y
                # 让竖线穿透所有子图
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    vlines = [l for l in getattr(
                        self, '_crosshair_lines', []) if l.axes == ax and l.get_linestyle() == '--']
                    if not vlines:
                        vline = ax.axvline(
                            x_val, color=primary_color, lw=1.2, ls='--', alpha=0.55, visible=True, zorder=100)
                        self._crosshair_lines.append(vline)
                    else:
                        vlines[0].set_xdata([x_val, x_val])
                        vlines[0].set_visible(True)
                # 横线只在主图
                self._crosshair_lines[1].set_ydata([y_val, y_val])
                self._crosshair_lines[1].set_visible(True)
                # 信息内容（多行详细信息）
                info = (
                    f"日期: {row.name.strftime('%Y-%m-%d')}\n"
                    f"开盘: {row.open:.2f}  收盘: {row.close:.2f}\n"
                    f"最高: {row.high:.2f}  最低: {row.low:.2f}\n"
                    f"成交量: {row.volume:.0f}"
                )
                # 信息框位置：在十字点右上角偏移一点
                ax = event.inaxes
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                dx = 0.03 * (xlim[1] - xlim[0])
                dy = 0.03 * (ylim[1] - ylim[0])
                x_text = x_val + \
                    dx if x_val < (xlim[0] + xlim[1]) / 2 else x_val - dx
                y_text = y_val + \
                    dy if y_val < (ylim[0] + ylim[1]) / 2 else y_val - dy
                x_text = min(max(x_text, xlim[0] + dx), xlim[1] - dx)
                y_text = min(max(y_text, ylim[0] + dy), ylim[1] - dy)
                self._crosshair_text.set_position((x_text, y_text))
                self._crosshair_text.set_ha('left' if x_val < (
                    xlim[0] + xlim[1]) / 2 else 'right')
                self._crosshair_text.set_va(
                    'bottom' if y_val < (ylim[0] + ylim[1]) / 2 else 'top')
                self._crosshair_text.set_text(info)
                self._crosshair_text.set_visible(True)
                # --- X轴交点数字覆盖 ---
                # 保证X轴刻度水平显示
                self.indicator_ax.set_xticklabels(
                    [label.get_text()
                     for label in self.indicator_ax.get_xticklabels()],
                    rotation=0, fontsize=8
                )
                # 在indicator_ax底部动态覆盖当前x_val位置的X轴刻度（半透明白底，数字在上方）
                if not hasattr(self, '_crosshair_xtext') or self._crosshair_xtext is None:
                    self._crosshair_xtext = self.indicator_ax.text(
                        x_val, -0.05, row.name.strftime('%Y-%m-%d'),
                        ha='center', va='top', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_xtext.set_x(x_val)
                    self._crosshair_xtext.set_text(
                        row.name.strftime('%Y-%m-%d'))
                    self._crosshair_xtext.set_visible(True)
                self._crosshair_xtext.set_color(primary_color)
                self._crosshair_xtext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                # --- Y轴交点数字覆盖 ---
                # 在price_ax左侧动态覆盖当前y_val位置的Y轴刻度（半透明白底，数字在上方）
                if not hasattr(self, '_crosshair_ytext') or self._crosshair_ytext is None:
                    self._crosshair_ytext = self.price_ax.text(
                        -0.5, y_val, f'{y_val:.2f}',
                        ha='right', va='center', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_ytext.set_y(y_val)
                    self._crosshair_ytext.set_text(f'{y_val:.2f}')
                    self._crosshair_ytext.set_visible(True)
                self._crosshair_ytext.set_color(primary_color)
                self._crosshair_ytext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                self.canvas.draw_idle()
            self._crosshair_cid = self.canvas.mpl_connect(
                'motion_notify_event', on_mouse_move)
            self._crosshair_initialized = True
        else:
            for line in self._crosshair_lines:
                line.set_visible(True)
            self._crosshair_text.set_visible(True)
        self._optimize_display()  # 保证十字线交互后也恢复网格和刻度

    def _limit_xlim(self):
        """限制x轴范围在数据区间内，防止拖动/缩放出现空白（等距序号X轴专用）"""
        if self.current_kdata is None or len(self.current_kdata) == 0:
            return
        xmin = 0
        xmax = len(self.current_kdata) - 1
        cur_xlim = self.price_ax.get_xlim()
        new_left = max(cur_xlim[0], xmin)
        new_right = min(cur_xlim[1], xmax)
        # 保证区间不反转
        if new_right - new_left < 1:
            new_left = xmin
            new_right = xmax
        self.price_ax.set_xlim(new_left, new_right)

    def _init_figure_layout(self):
        """初始化图表布局"""
        try:
            self.figure = Figure(figsize=(15, 8), dpi=100,
                                 constrained_layout=False)
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.gs = self.figure.add_gridspec(3, 1, height_ratios=[3, 1, 1])
            self.price_ax = self.figure.add_subplot(self.gs[0])
            self.volume_ax = self.figure.add_subplot(
                self.gs[1], sharex=self.price_ax)
            self.indicator_ax = self.figure.add_subplot(
                self.gs[2], sharex=self.price_ax)
            # 只保留indicator_ax的X轴刻度和标签
            self.price_ax.set_xticklabels([])
            self.price_ax.tick_params(
                axis='x', which='both', bottom=False, top=False, labelbottom=False)
            self.volume_ax.set_xticklabels([])
            self.volume_ax.tick_params(
                axis='x', which='both', bottom=False, top=False, labelbottom=False)
            # indicator_ax保留X轴
            self.figure.subplots_adjust(
                left=0.05, right=0.98,
                top=0.98, bottom=0.06,
                hspace=0.03  # 缩小子图间距
            )
            self.layout().addWidget(self.canvas)
            self._optimize_display()  # 保证布局初始化后也显示网格和刻度
        except Exception as e:
            self.log_manager.error(f"初始化图表布局失败: {str(e)}")

    def _optimize_display(self):
        """优化显示效果，所有坐标轴字体统一为8号，始终显示网格和XY轴刻度（任何操作都不隐藏）"""
        # 只优化indicator_ax的X轴刻度，其他子图不显示X轴
        for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
            ax.grid(True, linestyle='--', alpha=0.5)  # 始终显示网格
            ax.tick_params(axis='y', which='major',
                           labelsize=8, labelleft=True)  # Y轴刻度
            for label in (ax.get_yticklabels()):
                label.set_fontsize(8)
            ax.title.set_fontsize(8)
            ax.xaxis.label.set_fontsize(8)
            ax.yaxis.label.set_fontsize(8)
        # 只设置indicator_ax的X轴刻度样式
        self.indicator_ax.tick_params(
            axis='x', which='major', labelsize=7, labelbottom=True)
        for label in self.indicator_ax.get_xticklabels():
            label.set_fontsize(8)

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
        """实际的绘制信号实现，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            if hasattr(self, 'price_ax') and self.current_kdata is not None:
                kdata = self.current_kdata
                x = np.arange(len(kdata))
                date_to_idx = {str(date): i for i,
                               date in enumerate(kdata.index)}
                ymin = getattr(self, '_ymin', None)
                ymax = getattr(self, '_ymax', None)
                for signal in signals:
                    idx = date_to_idx.get(str(signal['date']))
                    if idx is None:
                        continue
                    price = signal['price']
                    if ymin is not None and ymax is not None:
                        price = max(ymin, min(price, ymax))
                    marker = '^' if signal['type'] == 'buy' else 'v'
                    color = 'r' if signal['type'] == 'buy' else 'g'
                    label = '买入' if signal['type'] == 'buy' else '卖出'
                    self.price_ax.plot(
                        idx, price, marker=marker, color=color, markersize=8, label=label)
                handles, labels = self.price_ax.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                self.price_ax.legend(
                    by_label.values(), by_label.keys(), loc='upper left', fontsize=8)
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
            self._optimize_display()  # 保证清除后也显示网格和刻度

        except Exception as e:
            error_msg = f"清除指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def draw_overview(self, ax, kdata):
        """绘制缩略图（mini map/overview），所有K线与主图对齐，节假日无数据自动跳过，X轴为等距序号。"""
        try:
            colors = self.theme_manager.get_theme_colors()
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
            x = np.arange(len(kdata))
            for i in range(len(kdata)):
                color = k_up if closes.iloc[i] >= opens.iloc[i] else k_down
                ax.plot([x[i], x[i]], [lows.iloc[i], highs.iloc[i]],
                        color=color, linewidth=2.0, alpha=1.0, zorder=1)
            self._optimize_display()  # 保证缩略图也显示网格和刻度
        except Exception as e:
            self.log_manager.error(f"绘制缩略图失败: {str(e)}")

    def apply_theme(self):
        """应用主题到主图和缩略图，确保K线颜色和UI实时刷新"""
        try:
            # 原有主题应用逻辑
            self._apply_initial_theme()
            self._optimize_display()  # 保证主题切换后也显示网格和刻度
        except Exception as e:
            self.log_manager.error(f"应用主题到主图和缩略图失败: {str(e)}")

    def _init_zoom_interaction(self):
        """自定义鼠标缩放交互，支持多级缩放、右键还原、滚轮缩放，优化流畅性"""
        self._zoom_press_x = None
        self._zoom_rect = None
        self._zoom_history = []  # 多级缩放历史
        self._last_motion_time = 0
        self._motion_interval_ms = 16  # 约60fps
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
        # 删除旧的rect，重新创建新的
        if self._zoom_rect is not None:
            self._zoom_rect.remove()
            self._zoom_rect = None
        self._zoom_rect = self.price_ax.axvspan(
            event.xdata, event.xdata, color='blue', alpha=0.18)
        self.canvas.draw_idle()

    def _on_zoom_motion(self, event):
        import time
        if self._zoom_press_x is None or event.inaxes != self.price_ax or event.button != 1:
            return
        now = int(time.time() * 1000)
        if now - self._last_motion_time < self._motion_interval_ms:
            return
        self._last_motion_time = now
        x0, x1 = self._zoom_press_x, event.xdata
        # 删除旧的rect，重新创建新的
        if self._zoom_rect is not None:
            self._zoom_rect.remove()
            self._zoom_rect = None
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
            # 新增：缩放后强制y轴范围
            ymin = getattr(self, '_ymin', None)
            ymax = getattr(self, '_ymax', None)
            if ymin is not None and ymax is not None:
                self.price_ax.set_ylim(ymin, ymax)
        else:
            # 右→左：还原到上一级
            if self._zoom_history:
                prev_xlim = self._zoom_history.pop()
                self.price_ax.set_xlim(prev_xlim)
            else:
                self.price_ax.set_xlim(auto=True)
            # 新增：还原后强制y轴范围
            ymin = getattr(self, '_ymin', None)
            ymax = getattr(self, '_ymax', None)
            if ymin is not None and ymax is not None:
                self.price_ax.set_ylim(ymin, ymax)
        self._limit_xlim()
        self._zoom_press_x = None
        self.canvas.draw_idle()
        self._optimize_display()  # 保证缩放后也恢复网格和刻度

    def _on_zoom_right_click(self, event):
        # 右键单击还原到上一级
        if event.inaxes == self.price_ax and event.button == 3:
            if self._zoom_history:
                prev_xlim = self._zoom_history.pop()
                self.price_ax.set_xlim(prev_xlim)
            else:
                self.price_ax.set_xlim(auto=True)
            self._limit_xlim()
            self.canvas.draw_idle()
            self._optimize_display()  # 保证还原后也恢复网格和刻度

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
        self._limit_xlim()
        self.canvas.draw_idle()
        self._optimize_display()  # 保证滚轮缩放后也恢复网格和刻度

    def async_update_chart(self, data: dict, n_segments: int = 20):
        """唯一K线多线程分段预处理实现，最后仍调用update_chart。优化为渲染前显示进度，分段处理时实时更新进度，渲染后关闭进度对话框。"""
        if not data or 'kdata' not in data:
            return
        kdata = data['kdata']
        if len(kdata) <= 100 or n_segments <= 1:
            QTimer.singleShot(0, lambda: self.update_chart({'kdata': kdata}))
            return
        # 渲染前显示加载进度
        self.show_loading_dialog()
        # 分段
        segments = np.array_split(kdata, n_segments)
        results = [None] * n_segments
        progress_step = int(100 / n_segments) if n_segments > 0 else 100

        def process_segment(segment, idx):
            # 这里可以做降采样、指标等预处理
            res = self._downsample_kdata(segment, max_points=1200)
            # 实时更新进度
            QTimer.singleShot(0, lambda: self.update_loading_progress(
                min((idx+1)*progress_step, 100), f"正在处理第{idx+1}/{n_segments}段..."))
            return res

        with ThreadPoolExecutor(max_workers=n_segments) as executor:
            futures = {executor.submit(
                process_segment, seg, i): i for i, seg in enumerate(segments)}
            for f in as_completed(futures):
                idx = futures[f]
                results[idx] = f.result()
        merged = np.concatenate(results)
        merged_df = kdata.iloc[merged] if isinstance(
            merged[0], (int, np.integer)) else pd.concat(results)
        # 渲染后关闭进度对话框由update_chart内部完成
        QTimer.singleShot(0, lambda: self.update_chart({'kdata': merged_df}))

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            code, raw_text = self.parse_dragged_stock_code(event)
            if not code:
                self.show_no_data("拖拽内容无效")
                return
            data_manager = getattr(self, 'data_manager', None)
            if not data_manager:
                parent = self.parent()
                p = parent
                while p is not None:
                    if hasattr(p, 'data_manager') and getattr(p, 'data_manager', None):
                        data_manager = p.data_manager
                        break
                    p = getattr(p, 'parent', lambda: None)()
            if data_manager:
                kdata = data_manager.get_k_data(code=code, freq='D')
                if hasattr(self, 'log_manager'):
                    self.log_manager.info(
                        f"[ChartWidget拖拽] 股票: {code}, kdata行数: {len(kdata) if kdata is not None else 'None'}")
                if kdata is not None and not kdata.empty:
                    data = {'stock_code': code, 'kdata': kdata, 'title': raw_text,
                            'period': 'D', 'chart_type': 'candlestick'}
                    self.update_chart(data)
                else:
                    self.show_no_data("当前股票无数据")
                event.acceptProposedAction()
            else:
                QMessageBox.warning(self, "数据错误", "未能获取数据管理器，无法加载股票数据。请联系管理员。")
                if hasattr(self, 'log_manager'):
                    self.log_manager.error("ChartWidget拖拽失败：未找到data_manager")
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"ChartWidget拖拽渲染失败: {str(e)}")

    def handle_external_drop_event(self, event):
        self.dropEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("text/plain"):
            event.acceptProposedAction()

    @staticmethod
    def parse_dragged_stock_code(event):
        """解析拖拽事件中的股票代码"""
        raw_text = ""
        if event.mimeData().hasText():
            raw_text = event.mimeData().text().strip()
        elif event.mimeData().hasFormat("text/plain"):
            raw_text = str(event.mimeData().data(
                "text/plain"), encoding="utf-8").strip()
        if raw_text.startswith("★"):
            raw_text = raw_text[1:].strip()
        code = raw_text.split()[0] if raw_text else ""
        return code, raw_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        min_margin = 0.01  # 最小边距比例，防止极端情况
        if w <= 0 or h <= 0:
            return
        left = max(30 / w, min_margin)
        right = min(1 - 10 / w, 1 - min_margin)
        top = min(1 - 10 / h, 1 - min_margin)
        bottom = max(20 / h, min_margin)
        if bottom >= top:
            bottom = max(top - min_margin, min_margin)
            top = min(top, 0.99)
        if left >= right:
            left = max(right - min_margin, min_margin)
            right = min(right, 0.99)
        try:
            self.figure.subplots_adjust(
                left=left, right=right, top=top, bottom=bottom, hspace=0.08)
        except Exception as e:
            self.figure.subplots_adjust(
                left=0.03, right=0.98, top=0.98, bottom=0.04, hspace=0.08)
        self.canvas.draw()
        self._optimize_display()  # 保证每次缩放后都恢复网格和刻度

    def show_no_data(self, message: str = "无数据"):
        """无数据时清空图表并显示提示信息，所有字体统一为8号，健壮处理异常，始终显示网格和XY轴刻度"""
        try:
            if hasattr(self, 'figure'):
                self.figure.clear()
                # 重新创建子图，防止后续渲染异常
                self.price_ax = self.figure.add_subplot(211)
                self.volume_ax = self.figure.add_subplot(212)
                # 清空其他内容
                self.price_ax.cla()
                self.volume_ax.cla()
                # 在主图中央显示提示文本
                self.price_ax.text(0.5, 0.5, message,
                                   transform=self.price_ax.transAxes,
                                   fontsize=16, color='#888',
                                   ha='center', va='center', alpha=0.85)
                # 设置默认XY轴刻度和网格
                self.price_ax.set_xlim(0, 1)
                self.price_ax.set_ylim(0, 1)
                self.volume_ax.set_xlim(0, 1)
                self.volume_ax.set_ylim(0, 1)
                self._optimize_display()  # 保证无数据时也显示网格和刻度
                self.figure.tight_layout()
                self.canvas.draw()
                # 统一字体大小（全部设为8号）
                for ax in [self.price_ax, self.volume_ax]:
                    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                        label.set_fontsize(8)
                    ax.title.set_fontsize(8)
                    ax.xaxis.label.set_fontsize(8)
                    ax.yaxis.label.set_fontsize(8)
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"显示无数据提示失败: {str(e)}")
