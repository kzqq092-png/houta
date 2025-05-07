"""
图表控件模块
"""
from typing import Optional, List, Dict, Any
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

from core.logger import LogManager
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
import traceback
from core.cache_manager import CacheManager


class ChartWidget(QWidget):
    """图表控件类"""

    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    zoom_changed = pyqtSignal(float)  # 缩放变更信号

    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None):
        """初始化图表控件

        Args:
            parent: Parent widget
            config_manager: Optional ConfigManager instance to use
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
            self.theme_manager = get_theme_manager(self.config_manager)
            self.theme_manager.theme_changed.connect(self.apply_theme)

            # 初始化日志管理器
            self.log_manager = LogManager()

            # 初始化数据更新锁
            self._update_lock = QMutex()
            self._render_lock = QMutex()

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 应用主题
            self.apply_theme()

            # 创建更新定时器
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._process_update_queue)
            self._update_timer.start(100)  # 100ms 间隔

            # 初始化更新队列
            self._update_queue = []

            # 添加渲染优化
            self._optimize_rendering()

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
                    background: #f7fafd;
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

            # 添加工具栏到主布局
            self.layout().addWidget(toolbar_widget)

            # 创建图表
            self.figure = Figure(figsize=(8, 6))
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.canvas.setStyleSheet('''
                background: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            ''')
            self.layout().addWidget(self.canvas)

            # 创建matplotlib工具栏（只创建一次）
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.layout().insertWidget(1, self.toolbar)

            # 创建子图
            self.price_ax = self.figure.add_subplot(211)
            self.volume_ax = self.figure.add_subplot(212)
            self.figure.set_tight_layout(True)
            self.figure.set_constrained_layout(True)

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

    def show_loading_dialog(self, stock_code):
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.close()
        self.loading_dialog = QDialog(self)
        self.loading_dialog.setWindowTitle("数据加载中")
        layout = QVBoxLayout(self.loading_dialog)
        self.loading_label = QLabel(f"正在加载 {stock_code} 的实时数据，请稍候...")
        layout.addWidget(self.loading_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("0%")
        layout.addWidget(self.progress_label)
        close_btn = QPushButton("取消/关闭")
        close_btn.clicked.connect(self.close_loading_dialog)
        layout.addWidget(close_btn)
        self.loading_dialog.setLayout(layout)
        self.loading_dialog.setModal(False)
        self.loading_dialog.setWindowModality(Qt.NonModal)
        self.loading_dialog.setWindowFlags(
            self.loading_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        self.loading_dialog.show()
        QApplication.processEvents()

    def update_loading_progress(self, percent: int, text: str = None):
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setValue(percent)
        if hasattr(self, 'progress_label') and self.progress_label:
            self.progress_label.setText(f"{percent}%")
        if hasattr(self, 'loading_label') and self.loading_label and text:
            self.loading_label.setText(text)

    def close_loading_dialog(self):
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
        if hasattr(self, 'progress_bar'):
            self.progress_bar = None
        if hasattr(self, 'progress_label'):
            self.progress_label = None
        if hasattr(self, 'loading_label'):
            self.loading_label = None

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
        stock_code = data.get('stock_code', 'default')
        time_range = data.get('time_range', '')  # 新增
        self.show_loading_dialog(stock_code)
        try:
            self.figure.clf()  # 清空所有子图，确保刷新
            self.update_loading_progress(5, "准备加载...")
            kdata = data.get('kdata')
            cache_key = self._get_cache_key(data)
            # 优先用缓存的kdata
            if cache_key:
                cached_data = self.cache_manager.get(cache_key)
                if cached_data is not None and 'kdata' in cached_data:
                    self.log_manager.info("使用缓存的K线数据")
                    kdata = cached_data['kdata']
            if kdata is None or kdata.empty:
                ax1 = self.figure.add_subplot(211)
                ax2 = self.figure.add_subplot(212, sharex=ax1)
                ax1.text(0.5, 0.5, "无数据", ha='center', va='center',
                         fontsize=16, color='gray', transform=ax1.transAxes)
                ax2.text(0.5, 0.5, "无数据", ha='center', va='center',
                         fontsize=16, color='gray', transform=ax2.transAxes)
                self.canvas.draw_idle()
                self.close_loading_dialog()
                return
            self.update_loading_progress(15, "校验数据...")
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in kdata.columns for col in required_columns):
                ax1 = self.figure.add_subplot(211)
                ax2 = self.figure.add_subplot(212, sharex=ax1)
                ax1.text(0.5, 0.5, "无数据", ha='center', va='center',
                         fontsize=16, color='gray', transform=ax1.transAxes)
                ax2.text(0.5, 0.5, "无数据", ha='center', va='center',
                         fontsize=16, color='gray', transform=ax2.transAxes)
                self.canvas.draw_idle()
                self.close_loading_dialog()
                return
            self.update_loading_progress(40, "处理K线数据...")
            df = kdata.copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    if hasattr(df.index[0], 'number'):
                        dates = []
                        for dt in df.index:
                            n = int(dt.number)
                            s = str(n)
                            dates.append(f"{s[:4]}-{s[4:6]}-{s[6:8]}")
                        df.index = pd.to_datetime(dates)
                    else:
                        df.index = pd.to_datetime(df.index)
                except Exception as e:
                    self.log_manager.error(f"转换日期失败: {str(e)}")
                    self.close_loading_dialog()
                    return
            self.update_loading_progress(60, "批量绘制K线...")
            plot_df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            plot_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            ax1 = self.figure.add_subplot(211)
            ax2 = self.figure.add_subplot(212, sharex=ax1)
            mpf.plot(
                plot_df,
                type='candle',
                ax=ax1,
                volume=ax2,
                style='yahoo',
                show_nontrading=True
            )
            self.update_loading_progress(95, "刷新画布...")
            self.figure.set_tight_layout(True)
            self.figure.set_constrained_layout(True)
            self.canvas.draw_idle()
            # 只缓存kdata，不缓存figure
            if cache_key:
                self.cache_manager.set(cache_key, {
                    'kdata': kdata,
                    'params': {
                        'stock_code': data.get('stock_code', ''),
                        'period': data.get('period', ''),
                        'chart_type': data.get('chart_type', ''),
                        'time_range': time_range
                    }
                })
            self.log_manager.info("图表更新完成")
            self.chart_updated.emit(data)
            self.update_loading_progress(100, "加载完成！")
            QTimer.singleShot(500, self.close_loading_dialog)
        except Exception as e:
            error_msg = f"更新图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            self.close_loading_dialog()

    def _optimize_rendering(self):
        """优化图表渲染性能"""
        try:
            # 设置更新策略
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)

            # 启用双缓冲
            self.setAutoFillBackground(True)

            # 优化 matplotlib 设置
            plt.style.use('fast')
            self.figure.set_dpi(100)  # 降低DPI以提高性能

            # 禁用不必要的特性
            plt.rcParams['path.simplify'] = True
            plt.rcParams['path.simplify_threshold'] = 1.0
            plt.rcParams['agg.path.chunksize'] = 10000

            # 设置更快的渲染器
            plt.rcParams['figure.facecolor'] = 'white'
            plt.rcParams['figure.edgecolor'] = 'white'
            plt.rcParams['axes.facecolor'] = 'white'
            plt.rcParams['savefig.dpi'] = 100
            plt.rcParams['figure.dpi'] = 100
            plt.rcParams['figure.autolayout'] = False
            plt.rcParams['figure.constrained_layout.use'] = True

            # 优化子图布局
            self.figure.set_tight_layout(False)
            self.figure.set_constrained_layout(True)

            # 设置更高效的动画
            plt.rcParams['animation.html'] = 'jshtml'

            # 优化内存使用
            plt.rcParams['agg.path.chunksize'] = 20000

            self.log_manager.info("图表渲染优化完成")

        except Exception as e:
            self.log_manager.error(f"优化渲染失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _get_cache_key(self, data: dict) -> str:
        """生成缓存键

        Args:
            data: 图表数据字典

        Returns:
            缓存键字符串
        """
        try:
            kdata = data.get('kdata')
            if kdata is None or kdata.empty:
                return None
            key_parts = [
                data.get('stock_code', ''),
                data.get('period', ''),
                data.get('chart_type', ''),
                str(data.get('time_range', '')),  # 新增时间范围参数
                str(getattr(self, '_zoom_level', 1.0))
            ]
            return '_'.join(key_parts)
        except Exception as e:
            self.log_manager.error(f"生成缓存键失败: {str(e)}")
            return None

    def _optimize_chart_update(self, data: dict) -> None:
        """优化图表更新性能

        Args:
            data: 图表数据字典
        """
        try:
            # 禁用自动缩放
            for ax in self.figure.axes:
                ax.autoscale(enable=False)

            # 使用更高效的数据结构
            kdata = data.get('kdata')
            if kdata is not None and not kdata.empty:
                # 转换为numpy数组以提高性能
                dates = kdata.index.values
                prices = kdata[['open', 'high', 'low', 'close']].values
                volumes = kdata['volume'].values

                # 减少数据点数量（如果数据点过多）
                if len(dates) > 1000:
                    step = len(dates) // 1000
                    dates = dates[::step]
                    prices = prices[::step]
                    volumes = volumes[::step]

                # 更新主图数据
                if hasattr(self, 'price_ax') and self.price_ax is not None:
                    self.price_ax.clear()
                    self.price_ax.plot(dates, prices[:, 3], 'b-', linewidth=1)

                # 更新成交量图数据
                if hasattr(self, 'volume_ax') and self.volume_ax is not None:
                    self.volume_ax.clear()
                    self.volume_ax.bar(
                        dates, volumes, width=0.8, color='g', alpha=0.5)

            # 优化绘图
            self.figure.set_constrained_layout(True)
            self.canvas.draw_idle()  # 使用draw_idle代替draw以提高性能

            self.log_manager.info("图表更新优化完成")

        except Exception as e:
            self.log_manager.error(f"优化图表更新失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def _enable_crosshair(self, ax, df):
        if not getattr(self, 'crosshair_enabled', False):
            return
        # 只创建一次 crosshair
        if not hasattr(self, '_crosshair_lines') or not self._crosshair_lines:
            self._crosshair_lines = [
                ax.axhline(color='gray', lw=0.5, ls='--',
                           alpha=0.5, visible=False),
                ax.axvline(color='gray', lw=0.5, ls='--',
                           alpha=0.5, visible=False)
            ]
            self._crosshair_text = ax.text(
                0.02, 0.98, '', transform=ax.transAxes, va='top', ha='left',
                fontsize=9, color='black',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                visible=False
            )

            def on_mouse_move(event):
                if not event.inaxes:
                    for line in self._crosshair_lines:
                        line.set_visible(False)
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
                idx = int(np.clip(round(x), 0, len(df)-1))
                row = df.iloc[idx]
                info = (
                    f"日期: {row.name.strftime('%Y-%m-%d')}\n"
                    f"开:{row['open']:.2f} 收:{row['close']:.2f}\n"
                    f"高:{row['high']:.2f} 低:{row['low']:.2f}\n"
                    f"量:{row['volume']:.0f}"
                )
                self._crosshair_text.set_text(info)
                self.canvas.draw_idle()

            self.canvas.mpl_connect('motion_notify_event', on_mouse_move)
        else:
            # 已有 crosshair，无需重复创建
            pass

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

    def _add_indicator_impl(self, indicator_data):
        """实际的添加指标实现

        Args:
            indicator_data: 指标数据
        """
        try:
            # 保存当前指标
            self.current_indicator = indicator_data

            # 在K线图上绘制指标
            if hasattr(self, 'price_ax'):
                # 获取指标数据
                dates = indicator_data.index
                values = indicator_data.values

                # 绘制指标线
                self.price_ax.plot(range(len(dates)), values,
                                   label=indicator_data.name,
                                   linewidth=1)

                # 更新图例
                self.price_ax.legend(loc='upper left', fontsize=8)

                # 更新画布
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

    def apply_theme(self):
        """应用主题到图表"""
        try:
            # 获取当前主题颜色
            colors = self.theme_manager.get_theme_colors()

            # 设置图表背景色
            self.figure.patch.set_facecolor(
                colors.get('chart_background', '#ffffff'))

            # 设置子图背景色和网格颜色
            for ax in [self.price_ax, self.volume_ax]:
                if ax is None:
                    continue

                # 设置背景色
                ax.set_facecolor(colors.get('chart_background', '#ffffff'))

                # 设置网格
                ax.grid(True, color=colors.get('chart_grid', '#e0e0e0'),
                        linestyle='--', alpha=0.3)

                # 设置轴线颜色
                for spine in ax.spines.values():
                    spine.set_color(colors.get('chart_grid', '#e0e0e0'))

                # 设置文本颜色
                text_color = colors.get('chart_text', '#333333')
                ax.tick_params(colors=text_color)
                ax.xaxis.label.set_color(text_color)
                ax.yaxis.label.set_color(text_color)
                if ax.get_title():
                    ax.title.set_color(text_color)

                # 设置刻度标签颜色
                for label in ax.get_xticklabels() + ax.get_yticklabels():
                    label.set_color(text_color)

            # 设置图例样式
            for ax in [self.price_ax, self.volume_ax]:
                if ax is None:
                    continue
                legend = ax.get_legend()
                if legend:
                    legend.set_facecolor(colors.get(
                        'chart_background', '#ffffff'))
                    for text in legend.get_texts():
                        text.set_color(colors.get('chart_text', '#333333'))

            # 设置工具栏样式
            if hasattr(self, 'toolbar'):
                toolbar_style = f"""
                    QToolBar {{
                        background-color: {colors.get('background', '#ffffff')};
                        border: none;
                        spacing: 5px;
                        padding: 2px;
                    }}
                    QToolButton {{
                        background-color: {colors.get('background', '#ffffff')};
                        border: 1px solid {colors.get('border', '#e0e0e0')};
                        padding: 6px;
                        border-radius: 4px;
                        color: {colors.get('text', '#333333')};
                    }}
                    QToolButton:hover {{
                        background-color: {colors.get('hover', '#f5f5f5')};
                        border-color: {colors.get('primary', '#1976d2')};
                    }}
                    QToolButton:pressed {{
                        background-color: {colors.get('selected', '#e3f2fd')};
                    }}
                    QToolButton:checked {{
                        background-color: {colors.get('selected', '#e3f2fd')};
                        border-color: {colors.get('primary', '#1976d2')};
                    }}
                """
                self.toolbar.setStyleSheet(toolbar_style)

            # 重绘图表
            self.canvas.draw()

            self.log_manager.info("主题应用完成")

        except Exception as e:
            error_msg = f"应用主题失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

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
        pass

    def plot_volume(self, ax, kdata):
        pass

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

    def apply_chart_theme(self, theme: str):
        """根据主题切换图表配色"""
        if theme == 'dark':
            self.figure.patch.set_facecolor('#181c24')
            for ax in [self.price_ax, self.volume_ax]:
                if ax:
                    ax.set_facecolor('#181c24')
                    ax.tick_params(colors='#b0b8c1')
                    ax.xaxis.label.set_color('#b0b8c1')
                    ax.yaxis.label.set_color('#b0b8c1')
                    if ax.get_title():
                        ax.title.set_color('#b0b8c1')
                    for spine in ax.spines.values():
                        spine.set_color('#2c3140')
                    for label in ax.get_xticklabels() + ax.get_yticklabels():
                        label.set_color('#b0b8c1')
                    ax.grid(True, color='#2c3140', linestyle='--', alpha=0.3)
            self.canvas.setStyleSheet(
                'background: #181c24; border-radius: 10px; border: 1px solid #2c3140;')
        else:
            self.figure.patch.set_facecolor('#ffffff')
            for ax in [self.price_ax, self.volume_ax]:
                if ax:
                    ax.set_facecolor('#ffffff')
                    ax.tick_params(colors='#333333')
                    ax.xaxis.label.set_color('#333333')
                    ax.yaxis.label.set_color('#333333')
                    if ax.get_title():
                        ax.title.set_color('#333333')
                    for spine in ax.spines.values():
                        spine.set_color('#e0e0e0')
                    for label in ax.get_xticklabels() + ax.get_yticklabels():
                        label.set_color('#333333')
                    ax.grid(True, color='#e0e0e0', linestyle='--', alpha=0.3)
            self.canvas.setStyleSheet(
                'background: #ffffff; border-radius: 10px; border: 1px solid #e0e0e0;')
        self.canvas.draw()
