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
import time
from datetime import datetime, timedelta
import matplotlib.dates as mdates

from core.logger import LogManager

from utils.theme import get_theme_manager, Theme
from utils.config_manager import ConfigManager
import traceback

# 使用新的指标服务架构
from core.services.indicator_ui_adapter import IndicatorUIAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from .async_data_processor import AsyncDataProcessor
from .chart_renderer import ChartRenderer
from utils.cache import Cache


class ChartWidget(QWidget):
    """图表控件类"""

    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    zoom_changed = pyqtSignal(float)  # 缩放变更信号
    request_indicator_dialog = pyqtSignal()
    request_stat_dialog = pyqtSignal(tuple)  # (start_idx, end_idx)
    pattern_selected = pyqtSignal(int)  # 新增：主图高亮信号，参数为K线索引

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
            self.active_indicators = []  # 当前激活的指标列表，初始化为空，仅通过外部信号设置

            # 初始化缓存管理器
            self.cache_manager = Cache()  # 图表最多缓存100个

            # 启用双缓冲
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAutoFillBackground(True)

            # 初始化管理器
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = theme_manager or get_theme_manager(
                self.config_manager)

            # 初始化日志管理器
            self.log_manager = log_manager or LogManager()

            # 初始化数据管理器
            self.data_manager = data_manager

            # 使用新的指标服务架构
            self.indicator_adapter = IndicatorUIAdapter()
            self.log_manager.info("使用新的指标服务架构")

            # 初始化数据更新锁
            self._update_lock = QMutex()
            self._render_lock = QMutex()

            # 新增：合并指标栏UI引用
            self.indicator_bar = None  # 合并后的指标栏
            self.volume_bar = None     # 成交量栏
            self.macd_bar = None      # MACD栏

            # 初始化UI
            self.init_ui()

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

            self.highlighted_indices = set()  # 高亮K线索引
            self._replay_timer = None         # 回放定时器
            self._replay_index = None         # 回放当前索引

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_ui(self):
        """初始化UI，移除十字光标按钮，默认开启十字光标。主图类型下拉框由主窗口统一管理，不在ChartWidget中定义。"""
        try:
            # 先设置主布局，确保self.layout()不为None
            if self.layout() is None:
                layout = QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
                self.setLayout(layout)
            else:
                layout = self.layout()
            # 图表区
            self._init_figure_layout()
            # 移除底部指标栏（indicator_bar）相关代码
            # self.indicator_bar = None
            # layout.addWidget(self.indicator_bar)
            self._init_zoom_interaction()  # 新增：自定义缩放交互
            self._optimize_display()  # 保证初始化后也显示网格和刻度

        except Exception as e:
            self.log_manager.error(f"初始化UI失败: {str(e)}")

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

    def update_loading_progress(self, value: int, message: str = None):
        """更新加载进度，保证数值安全"""
        value = max(0, min(100, int(value)))
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.setValue(value)
            if message:
                self.loading_dialog.setLabelText(message)

    def set_loading_progress_error(self, message="渲染失败"):
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.setStyleSheet(
                "QProgressBar::chunk {background-color: #FF0000;}")
            self.loading_dialog.setLabelText(message)

    def close_loading_dialog(self):
        """关闭加载进度对话框"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.close()

    def _downsample_kdata(self, kdata, max_points=1200):
        """对K线数据做降采样，提升渲染性能"""
        if len(kdata) <= max_points:
            return kdata
        idx = np.linspace(0, len(kdata)-1, max_points).astype(int)
        return kdata.iloc[idx]

    def _safe_format_date(self, row, idx, kdata):
        """安全地格式化日期，处理数值索引和datetime索引的情况"""
        try:
            # 优先从kdata的实际索引获取datetime
            if hasattr(kdata.index[idx], 'strftime'):
                return kdata.index[idx].strftime('%Y-%m-%d')
            elif hasattr(row.name, 'strftime'):
                # 如果索引本身是datetime
                return row.name.strftime('%Y-%m-%d')
            else:
                # 如果都不是datetime，检查是否有datetime列
                if 'datetime' in kdata.columns:
                    try:
                        date_val = pd.to_datetime(kdata.iloc[idx]['datetime'])
                        return date_val.strftime('%Y-%m-%d')
                    except:
                        pass

                # 尝试转换索引
                try:
                    date_val = pd.to_datetime(kdata.index[idx])
                    return date_val.strftime('%Y-%m-%d')
                except:
                    # 最后的兜底方案：使用索引位置生成相对日期
                    base_date = datetime(2024, 1, 1)
                    actual_date = base_date + timedelta(days=idx)
                    return actual_date.strftime('%Y-%m-%d')
        except Exception:
            return f"第{idx}根K线"

    def update_chart(self, data: dict = None):
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
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.cla()
            style = self._get_chart_style()
            x = np.arange(len(kdata))  # 用等距序号做X轴
            self.renderer.render_candlesticks(self.price_ax, kdata, style, x=x)
            self.renderer.render_volume(self.volume_ax, kdata, style, x=x)
            # 修复：自动同步主窗口指标
            if hasattr(self, 'parentWidget') and callable(getattr(self, 'parentWidget', None)):
                main_window = self.parentWidget()
                while main_window and not hasattr(main_window, 'get_current_indicators'):
                    main_window = main_window.parentWidget() if hasattr(
                        main_window, 'parentWidget') else None
                if main_window and hasattr(main_window, 'get_current_indicators'):
                    self.active_indicators = main_window.get_current_indicators()
            self._render_indicators(kdata, x=x)
            # --- 新增：形态信号可视化 ---
            pattern_signals = data.get('pattern_signals', None)
            if pattern_signals:
                self.plot_patterns(pattern_signals)
            self._optimize_display()
            if not kdata.empty:
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    ax.set_xlim(0, len(kdata)-1)
                self.price_ax.set_ylim(self._ymin, self._ymax)
                # 设置X轴刻度和标签（间隔显示，防止过密）
                step = max(1, len(kdata)//8)
                xticks = np.arange(0, len(kdata), step)
                xticklabels = [self._safe_format_date(kdata.iloc[i], i, kdata) for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                # 修复：确保tick数量和label数量一致
                if len(xticks) == len(xticklabels):
                    self.indicator_ax.set_xticklabels(xticklabels, rotation=30, fontsize=8)
                else:
                    # 自动补齐或截断
                    min_len = min(len(xticks), len(xticklabels))
                    self.indicator_ax.set_xticks(xticks[:min_len])
                    self.indicator_ax.set_xticklabels(xticklabels[:min_len], rotation=30, fontsize=8)
            self.close_loading_dialog()
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.yaxis.set_tick_params(direction='in', pad=0)
                ax.yaxis.set_label_position('left')
                ax.tick_params(axis='y', direction='in', pad=0)
            self.crosshair_enabled = True
            self.enable_crosshair(force_rebind=True)
            # 左上角显示股票名称和代码
            if hasattr(self, '_stock_info_text') and self._stock_info_text:
                self._safe_remove_artist(self._stock_info_text, self.price_ax)
                self._stock_info_text = None
            stock_name = data.get('title') or getattr(
                self, 'current_stock', '')
            stock_code = data.get('stock_code') or getattr(
                self, 'current_stock', '')
            if stock_name and stock_code and stock_code not in stock_name:
                info_str = f"{stock_name} ({stock_code})"
            elif stock_name:
                info_str = stock_name
            elif stock_code:
                info_str = stock_code
            else:
                info_str = ''
            colors = self.theme_manager.get_theme_colors()
            text_color = colors.get('chart_text', '#222b45')
            bg_color = colors.get('chart_background', '#ffffff')
            self._stock_info_text = self.price_ax.text(
                0.01, 0.99, info_str,  # y坐标0.98
                transform=self.price_ax.transAxes,
                va='top', ha='left',
                fontsize=8,
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
            self._optimize_display()
            # --- 十字光标X轴日期标签固定在X轴下方 ---
            # 在 on_mouse_move 事件中，x_text 固定为X轴下方边界
            # ...找到 on_mouse_move ...

            def on_mouse_move(event):
                now = int(time.time() * 1000)
                if hasattr(self, '_last_crosshair_update_time') and now - self._last_crosshair_update_time < 16:
                    return
                self._last_crosshair_update_time = now
                colors = self.theme_manager.get_theme_colors(
                ) if hasattr(self, 'theme_manager') else {}
                primary_color = colors.get('primary', '#1976d2')
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
                date_str = self._safe_format_date(row, idx, kdata)
                info = (
                    f"日期: {date_str}\n"
                    f"开盘: {row.open:.3f}  收盘: {row.close:.3f}\n"
                    f"最高: {row.high:.3f}  最低: {row.low:.3f}\n"
                    f"成交量: {row.volume:.0f}"
                )

                # 增加形态信息显示（如果当前K线有形态信号）
                if hasattr(self, '_pattern_info') and idx in self._pattern_info:
                    pattern_info = self._pattern_info[idx]
                    info += (
                        f"\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"形态: {pattern_info['pattern_name']}\n"
                        f"信号: {pattern_info['signal_cn']}\n"
                        f"置信度: {pattern_info['confidence']:.1%}\n"
                        f"价格: {pattern_info['price']:.3f}"
                    )

                # 计算涨跌幅和涨跌额（相对前一日）
                if idx > 0:
                    prev_close = kdata.iloc[idx-1]['close']
                    change = row.close - prev_close
                    change_pct = (change / prev_close) * 100
                    change_color = "↑" if change > 0 else "↓" if change < 0 else "→"
                    info += f"\n{change_color} 涨跌: {change:+.2f} ({change_pct:+.2f}%)"

                # 计算振幅
                amplitude = ((row.high - row.low) / row.close) * 100
                info += f"\n振幅: {amplitude:.3f}%"

                # 计算换手率（如果有流通股本数据）
                if hasattr(row, 'amount') and row.amount > 0:
                    turnover = (row.volume / 100000000) * 100  # 简化计算，实际需要流通股本
                    info += f"\n换手: {turnover:.3f}%"

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
                # 固定在X轴上方，不随窗口缩放
                date_text = self._safe_format_date(row, idx, kdata)
                if not hasattr(self, '_crosshair_xtext') or self._crosshair_xtext is None:
                    self._crosshair_xtext = self.indicator_ax.text(
                        x_val, self.indicator_ax.get_ylim(
                        )[1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]),
                        date_text,
                        ha='center', va='top', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_xtext.set_x(x_val)
                    self._crosshair_xtext.set_text(date_text)
                    self._crosshair_xtext.set_visible(True)
                    self._crosshair_xtext.set_y(self.indicator_ax.get_ylim()[
                                                1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]))
                self._crosshair_xtext.set_color(primary_color)
                self._crosshair_xtext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                # --- Y轴交点数字覆盖 ---
                # 在price_ax左侧动态覆盖当前y_val位置的Y轴刻度（半透明白底，数字在上方）
                if not hasattr(self, '_crosshair_ytext') or self._crosshair_ytext is None:
                    self._crosshair_ytext = self.price_ax.text(
                        -0.5, y_val, f'{y_val:.3f}',
                        ha='right', va='center', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_ytext.set_y(y_val)
                    self._crosshair_ytext.set_text(f'{y_val:.3f}')
                    self._crosshair_ytext.set_visible(True)
                self._crosshair_ytext.set_color(primary_color)
                self._crosshair_ytext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                self.canvas.draw_idle()
            self._crosshair_cid = self.canvas.mpl_connect(
                'motion_notify_event', on_mouse_move)
            self._crosshair_initialized = True
            # --- 图例左对齐固定在主图X轴下方，支持点击隐藏/显示 ---
            lines = self.price_ax.get_lines()
            labels = [self._safe_get_label(l) for l in lines]
            if lines and labels and any(l.get_visible() for l in lines):
                self.price_ax.legend(loc='upper left', fontsize=8)
            if not self.current_kdata.empty:
                step = max(1, len(self.current_kdata)//8)
                xticks = np.arange(0, len(self.current_kdata), step)
                xticklabels = [self._safe_format_date(self.current_kdata.iloc[i], i, self.current_kdata) for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                self.indicator_ax.set_xticklabels(
                    xticklabels, rotation=0, fontsize=7)

            # 绘制高亮K线
            try:
                if self.current_kdata is not None and hasattr(self, 'price_ax'):
                    for idx in self.highlighted_indices:
                        if 0 <= idx < len(self.current_kdata):
                            candle = self.current_kdata.iloc[idx]
                            self.price_ax.axvline(
                                idx, color='#ffd600', linestyle='--', linewidth=1.5, alpha=0.7, zorder=1000)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"高亮K线绘制失败: {str(e)}")

            # 左上角显示技术指标名称（下移到0.95）
            if hasattr(self, '_indicator_info_text') and self._indicator_info_text:
                self._safe_remove_artist(self._indicator_info_text, self.price_ax)
                self._indicator_info_text = None
            indicator_names = []
            if hasattr(self, 'active_indicators') and self.active_indicators:
                for ind in self.active_indicators:
                    name = ind.get('name', '')
                    if name:
                        indicator_names.append(name)
            indicator_str = ', '.join(indicator_names)
            if indicator_str:
                self._indicator_info_text = self.price_ax.text(
                    0.01, 0.9, indicator_str,
                    transform=self.price_ax.transAxes,
                    va='top', ha='left',
                    fontsize=8,
                    color=text_color,
                    bbox=dict(facecolor=bg_color, alpha=0.7,
                              edgecolor='none', boxstyle='round,pad=0.2'),
                    zorder=200
                )

        except Exception as e:
            self.log_manager.error(f"更新图表失败: {str(e)}")
            self.close_loading_dialog()

    def _render_indicators(self, kdata: pd.DataFrame, x=None):
        """
        渲染技术指标，确保主图指标显示在主图上，副图指标显示在副图上
        """
        try:
            indicators = getattr(self, 'active_indicators', [])
            if not indicators:
                # 如果没有激活的指标，尝试从主窗口获取
                indicators = self._get_active_indicators()

            if not indicators:
                return

            if x is None:
                x = np.arange(len(kdata))

            # 分类指标：主图指标 vs 副图指标
            main_chart_indicators = []  # 在主图显示的指标（如MA, BOLL等）
            sub_chart_indicators = []   # 在副图显示的指标（如MACD, RSI等）

            for indicator in indicators:
                name = indicator.get('name', '').upper()

                # 判断指标应该显示在主图还是副图
                if (name.startswith('MA') or name.startswith('EMA') or name.startswith('SMA') or
                        name.startswith('WMA') or name in ['BOLL', 'BBANDS', 'SAR', 'KAMA']):
                    main_chart_indicators.append(indicator)
                else:
                    sub_chart_indicators.append(indicator)

            # 渲染主图指标
            for i, indicator in enumerate(main_chart_indicators):
                try:
                    name = indicator.get('name', '').upper()
                    group = indicator.get('group', '')
                    params = indicator.get('params', {})
                    style = self._get_indicator_style(name, i)

                    # 处理均线类指标（应该显示在主图上）
                    if name.startswith('MA') and (group == 'builtin' or name[2:].isdigit()):
                        period = int(params.get('n', name[2:]) or 5)
                        if period > 0 and period <= len(kdata):
                            ma = kdata['close'].rolling(period).mean().dropna()
                            if not ma.empty:
                                self.price_ax.plot(x[-len(ma):], ma.values,
                                                   color=style['color'], linewidth=style['linewidth'],
                                                   alpha=style['alpha'], label=f'{name}({period})')

                    # 处理EMA指标
                    elif name.startswith('EMA'):
                        period = int(params.get('n', name[3:]) or 12)
                        if period > 0:
                            ema = kdata['close'].ewm(span=period).mean().dropna()
                            if not ema.empty:
                                self.price_ax.plot(x[-len(ema):], ema.values,
                                                   color=style['color'], linewidth=style['linewidth'],
                                                   alpha=style['alpha'], label=f'{name}({period})')

                    # 处理布林带指标（应该显示在主图上）
                    elif name in ['BOLL', 'BBANDS']:
                        period = int(params.get('period', 20))
                        std_dev = float(params.get('std_dev', params.get('std', 2.0)))
                        mid, upper, lower = self._calculate_boll(kdata, period=period, std_dev=std_dev)
                        if not mid.empty:
                            # 布林带中线
                            self.price_ax.plot(x[-len(mid):], mid.values,
                                               color=style['color'], linewidth=0.8, alpha=0.7,
                                               label=f'BOLL-MID({period})')
                            # 布林带上轨
                            upper_color = self._get_indicator_style(f'{name}-UPPER', i+1)['color']
                            self.price_ax.plot(x[-len(upper):], upper.values,
                                               color=upper_color, linewidth=0.6, alpha=0.6,
                                               label=f'BOLL-UPPER({period})')
                            # 布林带下轨
                            lower_color = self._get_indicator_style(f'{name}-LOWER', i+2)['color']
                            self.price_ax.plot(x[-len(lower):], lower.values,
                                               color=lower_color, linewidth=0.6, alpha=0.6,
                                               label=f'BOLL-LOWER({period})')
                            # 填充区域
                            self.price_ax.fill_between(x[-len(upper):], upper.values, lower.values,
                                                       alpha=0.1, color=style['color'])

                    # 处理ta-lib指标（主图部分）
                    elif group == 'ta-lib':
                        try:
                            import talib
                            # 获取英文名称
                            english_name = indicator.get('name', name)

                            # 准备ta-lib计算所需的数组
                            high = kdata['high'].values
                            low = kdata['low'].values
                            close = kdata['close'].values
                            open_price = kdata['open'].values
                            volume = kdata['volume'].values

                            # 根据指标类型计算
                            if english_name in ['SMA', 'EMA', 'WMA', 'DEMA', 'TEMA', 'TRIMA', 'KAMA', 'MAMA']:
                                # 移动平均类指标 - 统一使用period参数
                                period = int(params.get('period', params.get('timeperiod', params.get('n', 20))))
                                if english_name == 'SMA':
                                    result = talib.SMA(close, timeperiod=period)
                                elif english_name == 'EMA':
                                    result = talib.EMA(close, timeperiod=period)
                                elif english_name == 'WMA':
                                    result = talib.WMA(close, timeperiod=period)
                                elif english_name == 'DEMA':
                                    result = talib.DEMA(close, timeperiod=period)
                                elif english_name == 'TEMA':
                                    result = talib.TEMA(close, timeperiod=period)
                                elif english_name == 'TRIMA':
                                    result = talib.TRIMA(close, timeperiod=period)
                                elif english_name == 'KAMA':
                                    result = talib.KAMA(close, timeperiod=period)
                                elif english_name == 'MAMA':
                                    mama, fama = talib.MAMA(close)
                                    result = mama

                                # 绘制单线指标
                                if isinstance(result, np.ndarray) and not np.all(np.isnan(result)):
                                    valid_data = pd.Series(result).dropna()
                                    if not valid_data.empty:
                                        x_data = x[-len(valid_data):]
                                        display_name = f"{english_name}({period})"
                                        self.price_ax.plot(x_data, valid_data.values,
                                                           color=style['color'], linewidth=0.8, alpha=0.9,
                                                           label=display_name)

                            elif english_name == 'BBANDS':
                                # 布林带 - 统一使用period参数
                                period = int(params.get('period', params.get('timeperiod', 20)))
                                nbdevup = float(params.get('nbdevup', params.get('std_dev', 2)))
                                nbdevdn = float(params.get('nbdevdn', params.get('std_dev', 2)))
                                upperband, middleband, lowerband = talib.BBANDS(close, timeperiod=period,
                                                                                nbdevup=nbdevup, nbdevdn=nbdevdn)

                                # 绘制布林带三条线
                                if not np.all(np.isnan(middleband)):
                                    valid_mid = pd.Series(middleband).dropna()
                                    if not valid_mid.empty:
                                        self.price_ax.plot(x[-len(valid_mid):], valid_mid.values,
                                                           color=style['color'], linewidth=0.8, alpha=0.8,
                                                           label=f'BB-MID({period})')

                                if not np.all(np.isnan(upperband)):
                                    valid_upper = pd.Series(upperband).dropna()
                                    if not valid_upper.empty:
                                        upper_color = self._get_indicator_style(f'{english_name}-UPPER', i+1)['color']
                                        self.price_ax.plot(x[-len(valid_upper):], valid_upper.values,
                                                           color=upper_color, linewidth=0.6, alpha=0.6,
                                                           label=f'BB-UPPER({period})')

                                if not np.all(np.isnan(lowerband)):
                                    valid_lower = pd.Series(lowerband).dropna()
                                    if not valid_lower.empty:
                                        lower_color = self._get_indicator_style(f'{english_name}-LOWER', i+2)['color']
                                        self.price_ax.plot(x[-len(valid_lower):], valid_lower.values,
                                                           color=lower_color, linewidth=0.6, alpha=0.6,
                                                           label=f'BB-LOWER({period})')

                            elif english_name == 'SAR':
                                # 抛物线SAR
                                acceleration = float(params.get('acceleration', 0.02))
                                maximum = float(params.get('maximum', 0.2))
                                result = talib.SAR(high, low, acceleration=acceleration, maximum=maximum)

                                if not np.all(np.isnan(result)):
                                    valid_data = pd.Series(result).dropna()
                                    if not valid_data.empty:
                                        self.price_ax.scatter(x[-len(valid_data):], valid_data.values,
                                                              color=style['color'], s=8, alpha=0.8,
                                                              label=f'SAR({acceleration:.2f})')

                        except ImportError:
                            self.log_manager.warning("ta-lib库未安装，跳过ta-lib指标渲染")
                        except Exception as e:
                            self.log_manager.warning(f"ta-lib主图指标 {english_name} 计算失败: {str(e)}")

                except Exception as e:
                    self.log_manager.warning(f"渲染主图指标 {name} 失败: {str(e)}")

            # 渲染副图指标
            for i, indicator in enumerate(sub_chart_indicators):
                try:
                    name = indicator.get('name', '').upper()
                    group = indicator.get('group', '')
                    params = indicator.get('params', {})
                    formula = indicator.get('formula', None)
                    style = self._get_indicator_style(name, i)

                    # 处理内置MACD指标
                    if name == 'MACD' and group == 'builtin':
                        macd, sig, hist = self._calculate_macd(kdata)
                        macd = macd.dropna()
                        sig = sig.dropna()
                        hist = hist.dropna()

                        if not macd.empty:
                            self.indicator_ax.plot(x[-len(macd):], macd.values,
                                                   color=self._get_indicator_style('MACD', i)['color'],
                                                   linewidth=0.7, alpha=0.85, label='MACD')
                        if not sig.empty:
                            self.indicator_ax.plot(x[-len(sig):], sig.values,
                                                   color=self._get_indicator_style('MACD-Signal', i+1)['color'],
                                                   linewidth=0.7, alpha=0.85, label='Signal')
                        if not hist.empty:
                            colors = ['red' if h >= 0 else 'green' for h in hist]
                            self.indicator_ax.bar(x[-len(hist):], hist.values, color=colors, alpha=0.5)

                    # 处理内置RSI指标
                    elif name == 'RSI' and group == 'builtin':
                        period = int(params.get('period', 14))
                        rsi = self._calculate_rsi(kdata, period).dropna()
                        if not rsi.empty:
                            self.indicator_ax.plot(x[-len(rsi):], rsi.values,
                                                   color=style['color'], linewidth=0.8, alpha=0.9,
                                                   label=f'RSI({period})')
                            # 添加RSI参考线
                            self.indicator_ax.axhline(y=70, color='red', linestyle='--', alpha=0.5)
                            self.indicator_ax.axhline(y=30, color='green', linestyle='--', alpha=0.5)
                            self.indicator_ax.set_ylim(0, 100)

                    # 处理ta-lib副图指标
                    elif group == 'ta-lib':
                        try:
                            import talib
                            english_name = indicator.get('name', name)

                            # 准备数据
                            high = kdata['high'].values
                            low = kdata['low'].values
                            close = kdata['close'].values
                            open_price = kdata['open'].values
                            volume = kdata['volume'].values

                            # 根据指标类型计算和渲染
                            if english_name == 'MACD':
                                # MACD指标 - 统一使用标准参数名
                                fast_period = int(params.get('fast_period', params.get('fastperiod', 12)))
                                slow_period = int(params.get('slow_period', params.get('slowperiod', 26)))
                                signal_period = int(params.get('signal_period', params.get('signalperiod', 9)))
                                macd, macdsignal, macdhist = talib.MACD(close, fastperiod=fast_period,
                                                                        slowperiod=slow_period, signalperiod=signal_period)

                                if not np.all(np.isnan(macd)):
                                    valid_macd = pd.Series(macd).dropna()
                                    if not valid_macd.empty:
                                        self.indicator_ax.plot(x[-len(valid_macd):], valid_macd.values,
                                                               color=style['color'], linewidth=0.8, alpha=0.9,
                                                               label=f'MACD({fast_period},{slow_period},{signal_period})')

                                if not np.all(np.isnan(macdsignal)):
                                    valid_signal = pd.Series(macdsignal).dropna()
                                    if not valid_signal.empty:
                                        signal_color = self._get_indicator_style('MACD-Signal', i+1)['color']
                                        self.indicator_ax.plot(x[-len(valid_signal):], valid_signal.values,
                                                               color=signal_color, linewidth=0.8, alpha=0.9,
                                                               label='MACD-Signal')

                                if not np.all(np.isnan(macdhist)):
                                    valid_hist = pd.Series(macdhist).dropna()
                                    if not valid_hist.empty:
                                        colors = ['red' if h >= 0 else 'green' for h in valid_hist]
                                        self.indicator_ax.bar(x[-len(valid_hist):], valid_hist.values,
                                                              color=colors, alpha=0.5)

                            elif english_name == 'RSI':
                                # RSI指标 - 统一使用period参数
                                period = int(params.get('period', params.get('timeperiod', 14)))
                                result = talib.RSI(close, timeperiod=period)

                                if not np.all(np.isnan(result)):
                                    valid_data = pd.Series(result).dropna()
                                    if not valid_data.empty:
                                        self.indicator_ax.plot(x[-len(valid_data):], valid_data.values,
                                                               color=style['color'], linewidth=0.8, alpha=0.9,
                                                               label=f'RSI({period})')
                                        # 添加RSI参考线
                                        self.indicator_ax.axhline(y=70, color='red', linestyle='--', alpha=0.5)
                                        self.indicator_ax.axhline(y=30, color='green', linestyle='--', alpha=0.5)
                                        self.indicator_ax.set_ylim(0, 100)

                            elif english_name in ['STOCH', 'STOCHF']:
                                # 随机指标KDJ
                                fastk_period = int(params.get('fastk_period', 9))
                                slowk_period = int(params.get('slowk_period', 3))
                                slowd_period = int(params.get('slowd_period', 3))

                                if english_name == 'STOCH':
                                    slowk, slowd = talib.STOCH(high, low, close, fastk_period=fastk_period,
                                                               slowk_period=slowk_period, slowd_period=slowd_period)
                                else:
                                    fastk, fastd = talib.STOCHF(high, low, close, fastk_period=fastk_period,
                                                                fastd_period=slowd_period)
                                    slowk, slowd = fastk, fastd

                                if not np.all(np.isnan(slowk)):
                                    valid_k = pd.Series(slowk).dropna()
                                    if not valid_k.empty:
                                        self.indicator_ax.plot(x[-len(valid_k):], valid_k.values,
                                                               color=style['color'], linewidth=0.8, alpha=0.9,
                                                               label=f'K({fastk_period})')

                                if not np.all(np.isnan(slowd)):
                                    valid_d = pd.Series(slowd).dropna()
                                    if not valid_d.empty:
                                        d_color = self._get_indicator_style('KDJ-D', i+1)['color']
                                        self.indicator_ax.plot(x[-len(valid_d):], valid_d.values,
                                                               color=d_color, linewidth=0.8, alpha=0.9,
                                                               label=f'D({slowd_period})')

                            # 其他通用ta-lib指标
                            else:
                                # 动态调用ta-lib函数
                                if hasattr(talib, english_name):
                                    func = getattr(talib, english_name)

                                    # 尝试不同的参数组合
                                    try:
                                        # 只需要close价格的指标 - 统一使用period参数
                                        if english_name in ['CCI', 'WILLR', 'ROC', 'MOM', 'CMO', 'TRIX']:
                                            period = int(params.get('period', params.get('timeperiod', 14)))
                                            if english_name == 'CCI':
                                                result = func(high, low, close, timeperiod=period)
                                            elif english_name == 'WILLR':
                                                result = func(high, low, close, timeperiod=period)
                                            else:
                                                result = func(close, timeperiod=period)

                                        # 需要成交量的指标
                                        elif english_name in ['OBV', 'AD', 'ADOSC']:
                                            if english_name == 'OBV':
                                                result = func(close, volume)
                                            elif english_name == 'AD':
                                                result = func(high, low, close, volume)
                                            elif english_name == 'ADOSC':
                                                # ADOSC指标 - 统一使用标准参数名
                                                fast_period = int(params.get('fast_period', params.get('fastperiod', 3)))
                                                slow_period = int(params.get('slow_period', params.get('slowperiod', 10)))
                                                result = func(high, low, close, volume,
                                                              fastperiod=fast_period,
                                                              slow_period=slow_period)
                                        else:
                                            # 默认尝试close价格
                                            result = func(close)

                                        # 渲染结果
                                        if isinstance(result, tuple):
                                            # 多返回值的指标
                                            for j, single_result in enumerate(result):
                                                if not np.all(np.isnan(single_result)):
                                                    valid_data = pd.Series(single_result).dropna()
                                                    if not valid_data.empty:
                                                        display_name = f"{english_name}-{j+1}"
                                                        color = self._get_indicator_style(display_name, i+j)['color']
                                                        self.indicator_ax.plot(x[-len(valid_data):], valid_data.values,
                                                                               color=color, linewidth=0.8, alpha=0.9,
                                                                               label=display_name)
                                        elif isinstance(result, np.ndarray):
                                            # 单返回值的指标
                                            if not np.all(np.isnan(result)):
                                                valid_data = pd.Series(result).dropna()
                                                if not valid_data.empty:
                                                    self.indicator_ax.plot(x[-len(valid_data):], valid_data.values,
                                                                           color=style['color'], linewidth=0.8, alpha=0.9,
                                                                           label=english_name)

                                    except Exception as param_error:
                                        self.log_manager.warning(f"ta-lib指标 {english_name} 参数错误: {str(param_error)}")

                        except ImportError:
                            self.log_manager.warning("ta-lib库未安装，无法使用ta-lib指标")
                        except Exception as e:
                            self.log_manager.error(f"ta-lib副图指标 {english_name} 渲染失败: {str(e)}")

                    # 处理自定义指标
                    elif group == 'custom' and formula:
                        try:
                            # 安全地用pandas.eval计算表达式
                            local_vars = {col: kdata[col] for col in kdata.columns}
                            arr = pd.eval(formula, local_dict=local_vars)
                            arr = arr.dropna()
                            if not arr.empty:
                                self.indicator_ax.plot(x[-len(arr):], arr.values, color=style['color'],
                                                       linewidth=style['linewidth'], alpha=style['alpha'], label=name)
                        except Exception as e:
                            self.log_manager.error(f"自定义指标渲染失败: {str(e)}")

                except Exception as e:
                    self.log_manager.warning(f"渲染副图指标 {name} 失败: {str(e)}")

            # 设置图例 - 修复警告：只有当确实有带标签的对象时才创建图例
            if main_chart_indicators:
                # 检查主图是否有带标签的艺术家对象
                handles, labels = self.price_ax.get_legend_handles_labels()
                if handles and labels:
                    self.price_ax.legend(loc='upper left', fontsize=8)

            if sub_chart_indicators:
                # 检查副图是否有带标签的艺术家对象
                handles, labels = self.indicator_ax.get_legend_handles_labels()
                if handles and labels:
                    self.indicator_ax.legend(loc='upper left', fontsize=8)

        except Exception as e:
            self.log_manager.error(f"渲染指标失败: {str(e)}")
            import traceback
            self.log_manager.error(traceback.format_exc())

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
            'linewidth': 0.7,
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
        try:
            response = self.indicator_adapter.calculate_indicator('MACD', data)
            if response.success:
                result = response.result
                if isinstance(result, dict):
                    return result.get('macd'), result.get('signal'), result.get('histogram')
                return result, None, None
            else:
                self.log_manager.error(f"计算MACD失败: {response.error}")
                return None, None, None
        except Exception as e:
            self.log_manager.error(f"计算MACD失败: {str(e)}")
            return None, None, None

    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        try:
            response = self.indicator_adapter.calculate_indicator('RSI', data, period=period)
            if response.success:
                return response.result
            else:
                self.log_manager.error(f"计算RSI失败: {response.error}")
                return None
        except Exception as e:
            self.log_manager.error(f"计算RSI失败: {str(e)}")
            return None

    def _calculate_boll(self, data: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带指标"""
        try:
            response = self.indicator_adapter.calculate_indicator('BOLL', data, period=period, std_dev=std_dev)
            if response.success:
                result = response.result
                if isinstance(result, dict):
                    return result.get('middle'), result.get('upper'), result.get('lower')
                return result, None, None
            else:
                self.log_manager.error(f"计算布林带失败: {response.error}")
                return None, None, None
        except Exception as e:
            self.log_manager.error(f"计算布林带失败: {str(e)}")
            return None, None, None

    def _get_active_indicators(self) -> list:
        """
        统一通过主窗口接口获取当前激活的所有指标及参数
        Returns:
            List[dict]: [{"name": 指标名, "params": 参数字典}, ...]
        """
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'get_current_indicators'):
            main_window = main_window.parentWidget() if hasattr(
                main_window, 'parentWidget') else None
        if main_window and hasattr(main_window, 'get_current_indicators'):
            return main_window.get_current_indicators()
        # 兜底：如果未找到主窗口接口，返回默认指标
        return [
            {"name": "MA20", "params": {"period": 20}},
            {"name": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}},
            {"name": "RSI", "params": {"period": 14}},
            {"name": "BOLL", "params": {"period": 20, "std": 2.0}}
        ]

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

            # --- 十字光标X轴日期标签固定在X轴下方 ---
            # 在 on_mouse_move 事件中，x_text 固定为X轴下方边界
            # ...找到 on_mouse_move ...
            def on_mouse_move(event):
                now = int(time.time() * 1000)
                if hasattr(self, '_last_crosshair_update_time') and now - self._last_crosshair_update_time < 16:
                    return
                self._last_crosshair_update_time = now
                colors = self.theme_manager.get_theme_colors(
                ) if hasattr(self, 'theme_manager') else {}
                primary_color = colors.get('primary', '#1976d2')
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
                date_str = self._safe_format_date(row, idx, kdata)
                info = (
                    f"日期: {date_str}\n"
                    f"开盘: {row.open:.3f}  收盘: {row.close:.3f}\n"
                    f"最高: {row.high:.3f}  最低: {row.low:.3f}\n"
                    f"成交量: {row.volume:.0f}"
                )

                # 增加形态信息显示（如果当前K线有形态信号）
                if hasattr(self, '_pattern_info') and idx in self._pattern_info:
                    pattern_info = self._pattern_info[idx]
                    info += (
                        f"\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"形态: {pattern_info['pattern_name']}\n"
                        f"信号: {pattern_info['signal_cn']}\n"
                        f"置信度: {pattern_info['confidence']:.1%}\n"
                        f"价格: {pattern_info['price']:.3f}"
                    )

                # 计算涨跌幅和涨跌额（相对前一日）
                if idx > 0:
                    prev_close = kdata.iloc[idx-1]['close']
                    change = row.close - prev_close
                    change_pct = (change / prev_close) * 100
                    change_color = "↑" if change > 0 else "↓" if change < 0 else "→"
                    info += f"\n{change_color} 涨跌: {change:+.2f} ({change_pct:+.2f}%)"

                # 计算振幅
                amplitude = ((row.high - row.low) / row.close) * 100
                info += f"\n振幅: {amplitude:.3f}%"

                # 计算换手率（如果有流通股本数据）
                if hasattr(row, 'amount') and row.amount > 0:
                    turnover = (row.volume / 100000000) * 100  # 简化计算，实际需要流通股本
                    info += f"\n换手: {turnover:.3f}%"

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
                # 固定在X轴上方，不随窗口缩放
                date_text = self._safe_format_date(row, idx, kdata)
                if not hasattr(self, '_crosshair_xtext') or self._crosshair_xtext is None:
                    self._crosshair_xtext = self.indicator_ax.text(
                        x_val, self.indicator_ax.get_ylim(
                        )[1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]),
                        date_text,
                        ha='center', va='top', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_xtext.set_x(x_val)
                    self._crosshair_xtext.set_text(date_text)
                    self._crosshair_xtext.set_visible(True)
                    self._crosshair_xtext.set_y(self.indicator_ax.get_ylim()[
                                                1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]))
                self._crosshair_xtext.set_color(primary_color)
                self._crosshair_xtext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                # --- Y轴交点数字覆盖 ---
                # 在price_ax左侧动态覆盖当前y_val位置的Y轴刻度（半透明白底，数字在上方）
                if not hasattr(self, '_crosshair_ytext') or self._crosshair_ytext is None:
                    self._crosshair_ytext = self.price_ax.text(
                        -0.5, y_val, f'{y_val:.3f}',
                        ha='right', va='center', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_ytext.set_y(y_val)
                    self._crosshair_ytext.set_text(f'{y_val:.3f}')
                    self._crosshair_ytext.set_visible(True)
                self._crosshair_ytext.set_color(primary_color)
                self._crosshair_ytext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                self.canvas.draw_idle()
            self._crosshair_cid = self.canvas.mpl_connect(
                'motion_notify_event', on_mouse_move)
            self._crosshair_initialized = True
            # --- 图例左对齐固定在主图X轴下方，支持点击隐藏/显示 ---
            lines = self.price_ax.get_lines()
            labels = [self._safe_get_label(l) for l in lines]
            if lines and labels and any(l.get_visible() for l in lines):
                self.price_ax.legend(loc='upper left', fontsize=8)
            if not self.current_kdata.empty:
                step = max(1, len(self.current_kdata)//8)
                xticks = np.arange(0, len(self.current_kdata), step)
                xticklabels = [self._safe_format_date(self.current_kdata.iloc[i], i, self.current_kdata) for i in xticks]
                self.indicator_ax.set_xticks(xticks)
                self.indicator_ax.set_xticklabels(
                    xticklabels, rotation=0, fontsize=7)

            # 绘制高亮K线
            try:
                if self.current_kdata is not None and hasattr(self, 'price_ax'):
                    for idx in self.highlighted_indices:
                        if 0 <= idx < len(self.current_kdata):
                            candle = self.current_kdata.iloc[idx]
                            self.price_ax.axvline(
                                idx, color='#ffd600', linestyle='--', linewidth=1.5, alpha=0.7, zorder=1000)
            except Exception as e:
                if self.log_manager:
                    self.log_manager.error(f"高亮K线绘制失败: {str(e)}")

            # 左上角显示技术指标名称（下移到0.95）
            if hasattr(self, '_indicator_info_text') and self._indicator_info_text:
                self._safe_remove_artist(self._indicator_info_text, self.price_ax)
                self._indicator_info_text = None
            indicator_names = []
            if hasattr(self, 'active_indicators') and self.active_indicators:
                for ind in self.active_indicators:
                    name = ind.get('name', '')
                    if name:
                        indicator_names.append(name)
            indicator_str = ', '.join(indicator_names)
            if indicator_str:
                self._indicator_info_text = self.price_ax.text(
                    0.01, 0.9, indicator_str,
                    transform=self.price_ax.transAxes,
                    va='top', ha='left',
                    fontsize=8,
                    color=text_color,
                    bbox=dict(facecolor=bg_color, alpha=0.7,
                              edgecolor='none', boxstyle='round,pad=0.2'),
                    zorder=200
                )

        except Exception as e:
            self.log_manager.error(f"更新图表失败: {str(e)}")
            self.close_loading_dialog()

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
                QTimer.singleShot(0, lambda: self.canvas.draw_idle() if hasattr(self, 'canvas') and self.canvas is not None else None)

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
                now = int(time.time() * 1000)
                if hasattr(self, '_last_crosshair_update_time') and now - self._last_crosshair_update_time < 16:
                    return
                self._last_crosshair_update_time = now
                colors = self.theme_manager.get_theme_colors(
                ) if hasattr(self, 'theme_manager') else {}
                primary_color = colors.get('primary', '#1976d2')
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
                date_str = self._safe_format_date(row, idx, kdata)
                info = (
                    f"日期: {date_str}\n"
                    f"开盘: {row.open:.3f}  收盘: {row.close:.3f}\n"
                    f"最高: {row.high:.3f}  最低: {row.low:.3f}\n"
                    f"成交量: {row.volume:.0f}"
                )

                # 增加形态信息显示（如果当前K线有形态信号）
                if hasattr(self, '_pattern_info') and idx in self._pattern_info:
                    pattern_info = self._pattern_info[idx]
                    info += (
                        f"\n━━━━━━━━━━━━━━━━━━━━\n"
                        f"形态: {pattern_info['pattern_name']}\n"
                        f"信号: {pattern_info['signal_cn']}\n"
                        f"置信度: {pattern_info['confidence']:.1%}\n"
                        f"价格: {pattern_info['price']:.3f}"
                    )

                # 计算涨跌幅和涨跌额（相对前一日）
                if idx > 0:
                    prev_close = kdata.iloc[idx-1]['close']
                    change = row.close - prev_close
                    change_pct = (change / prev_close) * 100
                    change_color = "↑" if change > 0 else "↓" if change < 0 else "→"
                    info += f"\n{change_color} 涨跌: {change:+.2f} ({change_pct:+.2f}%)"

                # 计算振幅
                amplitude = ((row.high - row.low) / row.close) * 100
                info += f"\n振幅: {amplitude:.3f}%"

                # 计算换手率（如果有流通股本数据）
                if hasattr(row, 'amount') and row.amount > 0:
                    turnover = (row.volume / 100000000) * 100  # 简化计算，实际需要流通股本
                    info += f"\n换手: {turnover:.3f}%"

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
                # 固定在X轴上方，不随窗口缩放
                date_text = self._safe_format_date(row, idx, kdata)
                if not hasattr(self, '_crosshair_xtext') or self._crosshair_xtext is None:
                    self._crosshair_xtext = self.indicator_ax.text(
                        x_val, self.indicator_ax.get_ylim(
                        )[1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]),
                        date_text,
                        ha='center', va='top', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_xtext.set_x(x_val)
                    self._crosshair_xtext.set_text(date_text)
                    self._crosshair_xtext.set_visible(True)
                    self._crosshair_xtext.set_y(self.indicator_ax.get_ylim()[
                                                1] + 0.08 * (self.indicator_ax.get_ylim()[1] - self.indicator_ax.get_ylim()[0]))
                self._crosshair_xtext.set_color(primary_color)
                self._crosshair_xtext.set_bbox(dict(
                    facecolor='#fff', edgecolor='none', alpha=0.85, boxstyle='round,pad=0.15', linewidth=0))
                # --- Y轴交点数字覆盖 ---
                # 在price_ax左侧动态覆盖当前y_val位置的Y轴刻度（半透明白底，数字在上方）
                if not hasattr(self, '_crosshair_ytext') or self._crosshair_ytext is None:
                    self._crosshair_ytext = self.price_ax.text(
                        -0.5, y_val, f'{y_val:.3f}',
                        ha='right', va='center', fontsize=8, color=primary_color,
                        bbox=dict(facecolor='#fff', edgecolor='none',
                                  alpha=0.85, boxstyle='round,pad=0.15', linewidth=0),
                        zorder=350, clip_on=False
                    )
                else:
                    self._crosshair_ytext.set_y(y_val)
                    self._crosshair_ytext.set_text(f'{y_val:.3f}')
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
                left=0.05, right=0.98, top=0.98, bottom=0.06, hspace=0.03)
            # 修正：只有在self.layout()存在时才addWidget
            if self.layout() is not None:
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
        """添加技术指标 - 增强版本，支持指标计算和显示

        Args:
            indicator_data: 指标数据，可以是字符串名称或字典格式
        """
        try:
            if indicator_data is None:
                self.log_manager.warning("指标数据为空")
                return

            # 标准化指标数据格式
            if isinstance(indicator_data, str):
                # 如果是字符串，转换为标准格式
                indicator_info = {
                    'name': indicator_data,
                    'chinese_name': indicator_data,
                    'type': 'builtin',
                    'params': {}
                }
            elif isinstance(indicator_data, dict):
                indicator_info = indicator_data
            else:
                self.log_manager.warning(f"不支持的指标数据类型: {type(indicator_data)}")
                return

            # 检查是否有K线数据
            if not hasattr(self, 'current_kdata') or self.current_kdata is None or self.current_kdata.empty:
                self.log_manager.warning("没有K线数据，无法计算指标")
                # 发送错误信号，让UI显示友好提示
                self.error_occurred.emit("请先选择股票数据后再添加指标")
                return

            # 检查指标是否已存在，避免重复添加
            indicator_name = indicator_info.get('name', '')
            if hasattr(self, 'active_indicators') and indicator_name in self.active_indicators:
                self.log_manager.info(f"指标 {indicator_name} 已存在，跳过重复添加")
                return

            # 初始化活跃指标列表
            if not hasattr(self, 'active_indicators'):
                self.active_indicators = []

            # 同步执行指标添加，避免异步队列导致的时序问题
            success = self._add_indicator_impl_sync(indicator_info)

            if success:
                # 添加到活跃指标列表
                self.active_indicators.append(indicator_name)
                self.log_manager.info(f"指标 {indicator_name} 添加成功")

                # 发送指标变化信号
                self.indicator_changed.emit(indicator_name)
            else:
                self.log_manager.error(f"指标 {indicator_name} 添加失败")
                self.error_occurred.emit(f"指标 {indicator_name} 添加失败，请检查数据完整性")

        except Exception as e:
            error_msg = f"添加指标失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _add_indicator_impl_sync(self, indicator_info, indicator_colors: list = None) -> bool:
        """同步添加指标的具体实现 - 避免异步队列问题

        Returns:
            bool: 添加是否成功
        """
        try:
            if not hasattr(self, 'current_kdata') or self.current_kdata is None or self.current_kdata.empty:
                self.log_manager.warning("没有K线数据，跳过指标计算")
                return False

            # 安全获取指标信息，支持IndicatorInfo对象和字典
            if hasattr(indicator_info, 'name'):
                indicator_name = indicator_info.name
                indicator_params = getattr(indicator_info, 'parameters', {})
                chinese_name = getattr(indicator_info, 'chinese_name', indicator_name)
            elif isinstance(indicator_info, dict):
                indicator_name = indicator_info.get('name', '')
                indicator_params = indicator_info.get('params', {})
                chinese_name = indicator_info.get('chinese_name', indicator_name)
            else:
                self.log_manager.error(f"不支持的指标信息格式: {type(indicator_info)}")
                return False

            self.log_manager.info(f"开始添加指标: {chinese_name} ({indicator_name})")
            self.log_manager.debug(f"指标参数: {indicator_params}")
            self.log_manager.debug(f"K线数据形状: {self.current_kdata.shape}")
            self.log_manager.debug(f"K线数据列: {list(self.current_kdata.columns)}")

            # 验证K线数据完整性
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in self.current_kdata.columns]
            if missing_columns:
                self.log_manager.error(f"K线数据缺少必要列: {missing_columns}")
                return False

            # 检查数据是否有足够的行数
            if len(self.current_kdata) < 20:
                self.log_manager.warning(f"K线数据行数不足({len(self.current_kdata)}行)，可能影响指标计算")

            # 计算指标值
            indicator_values = self._calculate_indicator_enhanced(indicator_name, self.current_kdata, indicator_params)

            if indicator_values is None:
                self.log_manager.error(f"指标计算失败: {indicator_name}")
                return False

            if not indicator_values:
                self.log_manager.error(f"指标计算结果为空: {indicator_name}")
                return False

            self.log_manager.info(f"指标计算成功: {chinese_name}, 结果包含 {len(indicator_values)} 个序列")
            for key, series in indicator_values.items():
                if hasattr(series, '__len__'):
                    self.log_manager.debug(f"  {key}: {len(series)} 个数据点")

            # 绘制指标
            plot_success = self._plot_indicator_enhanced(indicator_name, indicator_values, chinese_name, indicator_colors)

            if not plot_success:
                self.log_manager.error(f"指标绘制失败: {indicator_name}")
                return False

            # 更新图例
            self._update_legend()

            # 立即刷新图表显示
            if hasattr(self, 'canvas') and self.canvas is not None:
                self.canvas.draw_idle()

            self.log_manager.info(f"成功添加指标: {chinese_name} ({indicator_name})")
            return True

        except Exception as e:
            error_msg = f"添加指标实现失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            return False

    def _calculate_indicator_enhanced(self, indicator_name: str, kdata: pd.DataFrame, params: dict):
        """增强的指标计算方法 - 使用新的指标服务架构"""
        try:
            # 优先使用新的指标UI适配器
            if self.indicator_ui_adapter is not None:
                self.log_manager.debug(f"使用新的指标UI适配器计算指标: {indicator_name}")

                result = self.indicator_ui_adapter.calculate_indicator_for_ui(
                    indicator_name, kdata, **params
                )

                if result is not None and result.get('success', False):
                    self.log_manager.info(f"新指标服务计算成功: {indicator_name}")
                    return result.get('data', {})
                else:
                    error_msg = result.get('error', '未知错误') if result else "未知错误"
                    self.log_manager.warning(f"新指标服务计算失败: {indicator_name}, 错误: {error_msg}")

            # 回退到兼容层
            return self._calculate_indicator_fallback(indicator_name, kdata, params)

        except Exception as e:
            self.log_manager.error(f"指标计算异常 {indicator_name}: {str(e)}")
            # 如果所有方法都失败，回退到兼容层
            return self._calculate_indicator_fallback(indicator_name, kdata, params)

    def _calculate_indicator_fallback(self, indicator_name: str, kdata: pd.DataFrame, params: dict):
        """指标计算回退方法 - 使用兼容层"""
        try:
            from core.indicator_manager import get_indicator_manager

            self.log_manager.debug(f"使用兼容层计算指标: {indicator_name}")

            # 获取兼容层指标管理器
            compat_manager = get_indicator_manager()

            # 确保数据格式正确
            if 'close' not in kdata.columns:
                self.log_manager.error("K线数据缺少close列")
                return None

            # 检查数据有效性
            if kdata['close'].isna().all():
                self.log_manager.error("收盘价数据全部为空")
                return None

            indicator_name_upper = indicator_name.upper()

            # 使用兼容层的方法
            if indicator_name_upper in ['MA', 'SMA']:
                period = params.get('period', 20)
                result = compat_manager.calc_ma(kdata, period=period)
                return {'MA': result} if result is not None else None

            elif indicator_name_upper == 'MACD':
                fast = params.get('fast', params.get('fastperiod', 12))
                slow = params.get('slow', params.get('slowperiod', 26))
                signal = params.get('signal', params.get('signalperiod', 9))
                result = compat_manager.calc_macd(kdata, fast_period=fast, slow_period=slow, signal_period=signal)
                if result and isinstance(result, dict):
                    return {
                        'macd': result.get('macd'),
                        'macdsignal': result.get('macdsignal'),
                        'macdhist': result.get('macdhist')
                    }
                return None

            elif indicator_name_upper == 'RSI':
                period = params.get('period', params.get('timeperiod', 14))
                result = compat_manager.calc_rsi(kdata, period=period)
                return {'RSI': result} if result is not None else None

            elif indicator_name_upper == 'KDJ':
                k_period = params.get('k_period', params.get('fastk_period', 14))
                d_period = params.get('d_period', params.get('slowk_period', 3))
                result = compat_manager.calc_kdj(kdata, k_period=k_period, d_period=d_period)
                return result if result else None

            elif indicator_name_upper in ['BOLL', 'BBANDS']:
                period = params.get('period', params.get('timeperiod', 20))
                std_dev = params.get('std', params.get('std_dev', params.get('nbdevup', 2)))
                result = compat_manager.calc_boll(kdata, period=period, std_dev=std_dev)
                return result if result else None

            elif indicator_name_upper == 'ATR':
                period = params.get('period', params.get('timeperiod', 14))
                result = compat_manager.calc_atr(kdata, period=period)
                return {'ATR': result} if result is not None else None

            elif indicator_name_upper == 'OBV':
                if 'volume' not in kdata.columns:
                    self.log_manager.error("计算OBV需要成交量数据")
                    return None
                result = compat_manager.calc_obv(kdata)
                return {'OBV': result} if result is not None else None

            elif indicator_name_upper == 'CCI':
                period = params.get('period', params.get('timeperiod', 14))
                result = compat_manager.calc_cci(kdata, period=period)
                return {'CCI': result} if result is not None else None

            else:
                self.log_manager.warning(f"不支持的指标: {indicator_name}")
                return None

        except Exception as e:
            self.log_manager.error(f"兼容层计算指标失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            return None

    def _plot_indicator_enhanced(self, indicator_name: str, indicator_values: dict, chinese_name: str, colors: list = None):
        """增强的指标绘制方法 - 支持多种指标类型和布局

        Returns:
            bool: 绘制是否成功
        """
        try:
            if not indicator_values:
                self.log_manager.error(f"指标值为空，无法绘制: {indicator_name}")
                return False

            indicator_name_upper = indicator_name.upper()
            self.log_manager.debug(f"开始绘制指标: {indicator_name_upper}")

            # 获取默认颜色
            if colors is None:
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

            # 根据指标类型选择绘制位置和方式
            if indicator_name_upper in ['MA', 'SMA', 'EMA', 'BOLL', 'BBANDS']:
                # 主图指标（与K线同一图表）
                return self._plot_main_chart_indicator(indicator_name_upper, indicator_values, chinese_name, colors)

            elif indicator_name_upper in ['MACD']:
                # MACD特殊处理（需要柱状图和线条）
                return self._plot_macd_indicator(indicator_values, chinese_name, colors)

            elif indicator_name_upper in ['RSI', 'KDJ', 'CCI', 'STOCH']:
                # 子图指标（独立子图）
                return self._plot_subplot_indicator(indicator_name_upper, indicator_values, chinese_name, colors)

            else:
                # 通用指标处理
                return self._plot_generic_indicator(indicator_name_upper, indicator_values, chinese_name, colors)

        except Exception as e:
            error_msg = f"绘制指标失败 {indicator_name}: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            return False

    def _plot_main_chart_indicator(self, indicator_name: str, indicator_values: dict, chinese_name: str, colors: list) -> bool:
        """绘制主图指标（与K线在同一图表）"""
        try:
            if not hasattr(self, 'price_ax') or self.price_ax is None:
                self.log_manager.error("主图轴不存在")
                return False

            color_index = 0
            for key, values in indicator_values.items():
                if values is None or (hasattr(values, 'empty') and values.empty):
                    self.log_manager.warning(f"指标序列 {key} 为空，跳过绘制")
                    continue

                try:
                    # 确保索引对齐
                    if hasattr(values, 'index') and hasattr(self.current_kdata, 'index'):
                        # 对齐索引
                        aligned_values = values.reindex(self.current_kdata.index)
                        x_data = np.arange(len(self.current_kdata))
                        y_data = aligned_values.values
                    else:
                        x_data = np.arange(len(values))
                        y_data = values if isinstance(values, np.ndarray) else values.values

                    # 过滤有效数据
                    valid_mask = ~np.isnan(y_data)
                    if not np.any(valid_mask):
                        self.log_manager.warning(f"指标序列 {key} 全部为NaN，跳过绘制")
                        continue

                    x_valid = x_data[valid_mask]
                    y_valid = y_data[valid_mask]

                    # 选择颜色和标签
                    color = colors[color_index % len(colors)]
                    label = f"{chinese_name}_{key}" if len(indicator_values) > 1 else chinese_name

                    # 绘制线条
                    self.price_ax.plot(x_valid, y_valid, color=color, label=label, linewidth=1.5, alpha=0.8)

                    color_index += 1
                    self.log_manager.debug(f"成功绘制主图指标线条: {label}")

                except Exception as e:
                    self.log_manager.error(f"绘制指标序列 {key} 失败: {str(e)}")
                    continue

            return True

        except Exception as e:
            self.log_manager.error(f"绘制主图指标失败: {str(e)}")
            return False

    def _plot_subplot_indicator(self, indicator_name: str, indicator_values: dict, chinese_name: str, colors: list) -> bool:
        """绘制子图指标（独立子图）"""
        try:
            if not hasattr(self, 'indicator_ax') or self.indicator_ax is None:
                self.log_manager.error("指标子图轴不存在")
                return False

            color_index = 0
            for key, values in indicator_values.items():
                if values is None or (hasattr(values, 'empty') and values.empty):
                    self.log_manager.warning(f"指标序列 {key} 为空，跳过绘制")
                    continue

                try:
                    # 确保索引对齐
                    if hasattr(values, 'index') and hasattr(self.current_kdata, 'index'):
                        aligned_values = values.reindex(self.current_kdata.index)
                        x_data = np.arange(len(self.current_kdata))
                        y_data = aligned_values.values
                    else:
                        x_data = np.arange(len(values))
                        y_data = values if isinstance(values, np.ndarray) else values.values

                    # 过滤有效数据
                    valid_mask = ~np.isnan(y_data)
                    if not np.any(valid_mask):
                        self.log_manager.warning(f"指标序列 {key} 全部为NaN，跳过绘制")
                        continue

                    x_valid = x_data[valid_mask]
                    y_valid = y_data[valid_mask]

                    # 选择颜色和标签
                    color = colors[color_index % len(colors)]
                    label = f"{chinese_name}_{key}" if len(indicator_values) > 1 else chinese_name

                    # 绘制线条
                    self.indicator_ax.plot(x_valid, y_valid, color=color, label=label, linewidth=1.5, alpha=0.8)

                    color_index += 1
                    self.log_manager.debug(f"成功绘制子图指标线条: {label}")

                except Exception as e:
                    self.log_manager.error(f"绘制指标序列 {key} 失败: {str(e)}")
                    continue

            # 添加参考线（如RSI的30和70线）
            if indicator_name == 'RSI':
                self.indicator_ax.axhline(y=30, color='gray', linestyle='--', alpha=0.5)
                self.indicator_ax.axhline(y=70, color='gray', linestyle='--', alpha=0.5)
            elif indicator_name in ['KDJ', 'STOCH']:
                self.indicator_ax.axhline(y=20, color='gray', linestyle='--', alpha=0.5)
                self.indicator_ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5)

            return True

        except Exception as e:
            self.log_manager.error(f"绘制子图指标失败: {str(e)}")
            return False

    def _plot_macd_indicator(self, indicator_values: dict, chinese_name: str, colors: list) -> bool:
        """绘制MACD指标（特殊处理）"""
        try:
            if not hasattr(self, 'indicator_ax') or self.indicator_ax is None:
                self.log_manager.error("指标子图轴不存在")
                return False

            # MACD需要绘制线条和柱状图
            macd_line = indicator_values.get('MACD')
            signal_line = indicator_values.get('Signal')
            histogram = indicator_values.get('Histogram')

            x_data = np.arange(len(self.current_kdata))

            # 绘制MACD线
            if macd_line is not None:
                try:
                    if hasattr(macd_line, 'index'):
                        aligned_macd = macd_line.reindex(self.current_kdata.index)
                        y_macd = aligned_macd.values
                    else:
                        y_macd = macd_line

                    valid_mask = ~np.isnan(y_macd)
                    if np.any(valid_mask):
                        self.indicator_ax.plot(x_data[valid_mask], y_macd[valid_mask],
                                               color=colors[0], label=f'{chinese_name}_MACD', linewidth=1.5)
                except Exception as e:
                    self.log_manager.error(f"绘制MACD线失败: {str(e)}")

            # 绘制Signal线
            if signal_line is not None:
                try:
                    if hasattr(signal_line, 'index'):
                        aligned_signal = signal_line.reindex(self.current_kdata.index)
                        y_signal = aligned_signal.values
                    else:
                        y_signal = signal_line

                    valid_mask = ~np.isnan(y_signal)
                    if np.any(valid_mask):
                        self.indicator_ax.plot(x_data[valid_mask], y_signal[valid_mask],
                                               color=colors[1], label=f'{chinese_name}_Signal', linewidth=1.5)
                except Exception as e:
                    self.log_manager.error(f"绘制Signal线失败: {str(e)}")

            # 绘制Histogram柱状图
            if histogram is not None:
                try:
                    if hasattr(histogram, 'index'):
                        aligned_hist = histogram.reindex(self.current_kdata.index)
                        y_hist = aligned_hist.values
                    else:
                        y_hist = histogram

                    valid_mask = ~np.isnan(y_hist)
                    if np.any(valid_mask):
                        # 根据正负值设置颜色
                        pos_mask = y_hist > 0
                        neg_mask = y_hist <= 0

                        if np.any(pos_mask & valid_mask):
                            self.indicator_ax.bar(x_data[pos_mask & valid_mask], y_hist[pos_mask & valid_mask],
                                                  color='red', alpha=0.6, width=0.8)
                        if np.any(neg_mask & valid_mask):
                            self.indicator_ax.bar(x_data[neg_mask & valid_mask], y_hist[neg_mask & valid_mask],
                                                  color='green', alpha=0.6, width=0.8)
                except Exception as e:
                    self.log_manager.error(f"绘制Histogram柱状图失败: {str(e)}")

            # 添加零线
            self.indicator_ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

            return True

        except Exception as e:
            self.log_manager.error(f"绘制MACD指标失败: {str(e)}")
            return False

    def _plot_generic_indicator(self, indicator_name: str, indicator_values: dict, chinese_name: str, colors: list) -> bool:
        """绘制通用指标"""
        try:
            # 默认绘制到子图
            return self._plot_subplot_indicator(indicator_name, indicator_values, chinese_name, colors)
        except Exception as e:
            self.log_manager.error(f"绘制通用指标失败: {str(e)}")
            return False

    def _update_legend(self):
        """更新图例显示"""
        try:
            # 更新主图图例
            if hasattr(self, 'price_ax'):
                handles, labels = self.price_ax.get_legend_handles_labels()
                if handles and labels:
                    self.price_ax.legend(loc='upper left', fontsize=8, frameon=True,
                                         fancybox=True, shadow=True, framealpha=0.8)

            # 更新指标图图例
            if hasattr(self, 'indicator_ax') and self.indicator_ax:
                handles, labels = self.indicator_ax.get_legend_handles_labels()
                if handles and labels:
                    self.indicator_ax.legend(loc='upper left', fontsize=8, frameon=True,
                                             fancybox=True, shadow=True, framealpha=0.8)

        except Exception as e:
            self.log_manager.error(f"更新图例失败: {str(e)}")

    def plot_signals(self, signals, visible_range=None, signal_filter=None):
        """绘制信号，支持密度自适应、聚合展示、气泡提示"""
        try:
            if not hasattr(self, 'main_ax') or not self.main_ax:
                return

            # 安全清除旧信号
            signal_artists = getattr(self, '_signal_artists', [])
            if signal_artists:
                parent_ax = getattr(self, 'main_ax', None) or getattr(self, 'price_ax', None)
                self._safe_remove_artists_list(signal_artists, parent_ax)
            self._signal_artists = []

            if not signals:
                self.canvas.draw()
                return

            # 获取当前可见区间
            if visible_range is None:
                visible_range = self.get_visible_range()

            # 筛选可见区间内的信号
            visible_signals = []
            if visible_range:
                start_idx, end_idx = visible_range
                for signal in signals:
                    sig_idx = signal.get('index', 0)
                    if start_idx <= sig_idx <= end_idx:
                        visible_signals.append(signal)
            else:
                visible_signals = signals

            # 信号密度自适应
            max_signals_per_screen = 20  # 每屏最多显示信号数
            if len(visible_signals) > max_signals_per_screen:
                # 聚合展示：仅显示重要信号，其余用统计标记
                important_signals = self._select_important_signals(visible_signals, max_signals_per_screen)
                aggregated_count = len(visible_signals) - len(important_signals)
                visible_signals = important_signals

                # 在角落显示聚合信息
                if aggregated_count > 0:
                    agg_text = self.main_ax.text(0.02, 0.98, f"+ {aggregated_count} 个信号",
                                                 transform=self.main_ax.transAxes,
                                                 bbox=dict(boxstyle="round,pad=0.3", facecolor="orange", alpha=0.7),
                                                 fontsize=9, verticalalignment='top')
                    self._signal_artists.append(agg_text)

            # 绘制可见信号
            for signal in visible_signals:
                self._plot_single_signal(signal)

            # 启用气泡提示
            self._enable_signal_tooltips(visible_signals)

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"绘制信号失败: {str(e)}")

    def _select_important_signals(self, signals, max_count):
        """选择重要信号，基于置信度、类型优先级等"""
        # 按置信度排序，优先显示高置信度信号
        sorted_signals = sorted(signals, key=lambda x: x.get('confidence', 0), reverse=True)
        return sorted_signals[:max_count]

    def _plot_single_signal(self, signal):
        """绘制单个信号标记"""
        try:
            idx = signal.get('index', 0)
            signal_type = signal.get('type', 'unknown')
            confidence = signal.get('confidence', 0)
            price = signal.get('price', 0)

            # 根据信号类型设置颜色和标记
            if signal_type == 'double_top':
                color = 'red'
                marker = 'v'
                label = 'DT'
            elif signal_type == 'double_bottom':
                color = 'green'
                marker = '^'
                label = 'DB'
            else:
                color = 'blue'
                marker = 'o'
                label = signal_type[:2].upper()

            # 信号标记
            scatter = self.main_ax.scatter(idx, price, c=color, marker=marker, s=80,
                                           alpha=0.8, edgecolors='white', linewidth=1)
            self._signal_artists.append(scatter)

            # 简洁文字标注（仅高置信度显示）
            if confidence > 0.7:
                text = self.main_ax.text(idx, price * 1.01, label,
                                         fontsize=8, ha='center', va='bottom',
                                         color=color, fontweight='bold',
                                         bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
                self._signal_artists.append(text)

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"绘制单个信号失败: {str(e)}")

    def _enable_signal_tooltips(self, signals):
        """启用信号气泡提示"""
        try:
            # 创建信号索引映射
            signal_map = {signal.get('index', 0): signal for signal in signals}

            def on_hover(event):
                if event.inaxes != self.main_ax:
                    return

                # 查找最近的信号
                x_data = event.xdata
                if x_data is None:
                    return

                nearest_idx = int(round(x_data))
                if nearest_idx in signal_map:
                    signal = signal_map[nearest_idx]

                    # 显示气泡提示
                    tooltip_text = f"类型: {signal.get('type', 'unknown')}\\n"
                    tooltip_text += f"置信度: {signal.get('confidence', 0):.3f}\\n"
                    tooltip_text += f"价格: {signal.get('price', 0):.3f}\\n"
                    tooltip_text += f"时间: {signal.get('datetime', '')}"

                    # 安全清除旧提示
                    tooltip_artists = getattr(self, '_tooltip_artists', [])
                    if tooltip_artists:
                        parent_ax = getattr(self, 'main_ax', None) or getattr(self, 'price_ax', None)
                        self._safe_remove_artists_list(tooltip_artists, parent_ax)

                    # 新提示
                    tooltip = self.main_ax.annotate(tooltip_text,
                                                    xy=(nearest_idx, signal.get('price', 0)),
                                                    xytext=(20, 20), textcoords='offset points',
                                                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.9),
                                                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                                                    fontsize=9)
                    self._tooltip_artists = [tooltip]
                    self.canvas.draw()

            # 绑定鼠标事件
            if hasattr(self, 'canvas'):
                self.canvas.mpl_connect('motion_notify_event', on_hover)

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"启用信号提示失败: {str(e)}")

    def clear_indicators(self):
        """清除所有指标 - 增强版本，正确清除指标线条和图例"""
        try:
            self.current_indicator = None

            # 清除活跃指标列表
            if hasattr(self, 'active_indicators'):
                self.active_indicators.clear()
                self.log_manager.debug("已清除活跃指标列表")

            # 清除主图上的指标线条（保留K线数据）
            if hasattr(self, 'price_ax') and self.price_ax:
                # 获取所有线条
                lines = self.price_ax.get_lines()
                # 获取所有柱状图
                indicator_keywords = ['MA', 'EMA', 'BOLL', 'MACD', '移动平均', '指数平均', '布林', 'RSI', 'KDJ']
                bars = [child for child in self.price_ax.get_children()
                        if hasattr(child, 'get_label') and
                        any(indicator in self._safe_get_label(child) for indicator in indicator_keywords)]

                # 移除指标线条（跳过K线相关的线条）
                indicator_lines = []
                for line in lines:
                    label = self._safe_get_label(line)
                    # 只移除指标线条，保留K线相关线条
                    if (label and label != '_nolegend_' and
                        any(indicator in label for indicator in
                            ['MA', 'EMA', 'BOLL', 'MACD', 'Signal', 'Histogram',
                             '移动平均', '指数平均', '布林', 'RSI', 'KDJ', 'CCI', 'ATR', 'ADX'])):
                        indicator_lines.append(line)

                # 安全移除指标线条
                self._safe_remove_artists_list(indicator_lines, self.price_ax)

                # 安全移除指标柱状图
                self._safe_remove_artists_list(bars, self.price_ax)

                # 清除图例中的指标项
                handles, labels = self.price_ax.get_legend_handles_labels()
                if handles and labels:
                    # 过滤掉指标相关的图例项
                    filtered_handles = []
                    filtered_labels = []
                    for handle, label in zip(handles, labels):
                        if not any(indicator in label for indicator in
                                   ['MA', 'EMA', 'BOLL', 'MACD', 'Signal', 'Histogram',
                                    '移动平均', '指数平均', '布林', 'RSI', 'KDJ', 'CCI', 'ATR', 'ADX']):
                            filtered_handles.append(handle)
                            filtered_labels.append(label)

                    # 更新图例
                    if filtered_handles and filtered_labels:
                        self.price_ax.legend(filtered_handles, filtered_labels,
                                             loc='upper left', fontsize=8, frameon=True,
                                             fancybox=True, shadow=True, framealpha=0.8)
                    else:
                        # 如果没有图例项，移除图例
                        legend = self.price_ax.get_legend()
                        if legend:
                            self._safe_remove_artist(legend, self.price_ax)

            # 清除指标子图上的所有内容
            if hasattr(self, 'indicator_ax') and self.indicator_ax:
                # 安全清除所有线条
                indicator_lines = list(self.indicator_ax.get_lines())
                self._safe_remove_artists_list(indicator_lines, self.indicator_ax)

                # 安全清除所有柱状图和其他子对象
                children_to_remove = []
                for child in self.indicator_ax.get_children():
                    if hasattr(child, 'remove') and hasattr(child, 'get_label'):
                        children_to_remove.append(child)
                self._safe_remove_artists_list(children_to_remove, self.indicator_ax)

                # 安全清除图例
                legend = self.indicator_ax.get_legend()
                if legend:
                    self._safe_remove_artist(legend, self.indicator_ax)

                # 安全清除参考线
                reference_lines = []
                for line in self.indicator_ax.lines:
                    if hasattr(line, 'get_linestyle') and line.get_linestyle() == '--':
                        reference_lines.append(line)
                self._safe_remove_artists_list(reference_lines, self.indicator_ax)

            # 清除成交量图上的指标（如果有）
            if hasattr(self, 'volume_ax') and self.volume_ax:
                # 只清除指标线条，保留成交量柱状图
                lines_to_remove = []
                for line in self.volume_ax.get_lines():
                    label = self._safe_get_label(line)
                    if (label and label != '_nolegend_' and
                        any(indicator in label for indicator in
                            ['MA', 'EMA', 'BOLL', 'MACD', 'RSI', 'KDJ'])):
                        lines_to_remove.append(line)

                # 安全移除指标线条
                self._safe_remove_artists_list(lines_to_remove, self.volume_ax)

            # 重新绘制图表
            QTimer.singleShot(0, lambda: self.canvas.draw_idle() if hasattr(self, 'canvas') and self.canvas is not None else None)

            self.log_manager.info("成功清除所有指标")

            # 发送指标清除信号
            self.indicator_changed.emit("clear_all")

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
            # 新增：主题切换时同步刷新指标栏颜色
            if self.current_kdata is not None:
                self._update_combined_indicator_bar(self.current_kdata)
                self._update_volume_bar(self.current_kdata)
                self._update_macd_bar(self.current_kdata)
        except Exception as e:
            self.log_manager.error(f"应用主题到主图和缩略图失败: {str(e)}")

    def _init_zoom_interaction(self):
        """自定义鼠标缩放交互，支持多级缩放、右键还原、滚轮缩放，优化流畅性"""
        self._zoom_press_x = None
        self._zoom_rect = None
        self._zoom_history = []  # 多级缩放历史
        self._last_motion_time = 0
        self._motion_interval_ms = 100  # 约60fps
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
        # 安全删除旧的rect，重新创建新的
        if self._zoom_rect is not None:
            self._safe_remove_artist(self._zoom_rect, self.price_ax)
            self._zoom_rect = None
        self._zoom_rect = self.price_ax.axvspan(
            event.xdata, event.xdata, color='blue', alpha=0.18)
        self.canvas.draw_idle()

    def _on_zoom_motion(self, event):
        if self._zoom_press_x is None or event.inaxes != self.price_ax or event.button != 1:
            return
        now = int(time.time() * 1000)
        if now - self._last_motion_time < self._motion_interval_ms:
            return
        self._last_motion_time = now
        x0, x1 = self._zoom_press_x, event.xdata
        # 安全删除旧的rect，重新创建新的
        if self._zoom_rect is not None:
            self._safe_remove_artist(self._zoom_rect, self.price_ax)
            self._zoom_rect = None
        self._zoom_rect = self.price_ax.axvspan(
            x0, x1, color='blue', alpha=0.18)
        self.canvas.draw_idle()

    def _on_zoom_release(self, event):
        if self._zoom_press_x is None or event.inaxes != self.price_ax or event.button != 1:
            return
        x0, x1 = self._zoom_press_x, event.xdata
        if self._zoom_rect:
            self._safe_remove_artist(self._zoom_rect, self.price_ax)
            self._zoom_rect = None
        if abs(x1 - x0) < 1:  # 拖动太短不缩放
            self._zoom_press_x = None
            self.canvas.draw_idle()
            return
        if x1 > x0:
            # 左→右：放大
            self._zoom_history.append(self.price_ax.get_xlim())
            self.price_ax.set_xlim(x0, x1)
            # 新增：缩放后纵向自适应（不超出边界，自动居中）
            ymin = getattr(self, '_ymin', None)
            ymax = getattr(self, '_ymax', None)
            if ymin is not None and ymax is not None:
                kdata = self.current_kdata
                left_idx = int(max(0, round(x0)))
                right_idx = int(min(len(kdata)-1, round(x1)))
                if right_idx > left_idx:
                    sub = kdata.iloc[left_idx:right_idx+1]
                    y1 = float(sub['low'].min())
                    y2 = float(sub['high'].max())
                    pad = (y2 - y1) * 0.08
                    self.price_ax.set_ylim(y1 - pad, y2 + pad)
                else:
                    self.price_ax.set_ylim(ymin, ymax)
        else:
            # 右→左：还原到上一级
            if self._zoom_history:
                prev_xlim = self._zoom_history.pop()
                self.price_ax.set_xlim(prev_xlim)
            else:
                self.price_ax.set_xlim(auto=True)
            # 新增：还原后纵向自适应
            ymin = getattr(self, '_ymin', None)
            ymax = getattr(self, '_ymax', None)
            if ymin is not None and ymax is not None:
                self.price_ax.set_ylim(ymin, ymax)
        self._limit_xlim()
        self._zoom_press_x = None
        self.canvas.draw_idle()
        self._optimize_display()  # 保证缩放后也恢复网格和刻度

    def _on_zoom_right_click(self, event):
        # 右键单击支持K线拖拽和平移，右键双击还原初始状态
        if event.inaxes == self.price_ax and event.button == 3:
            if not hasattr(self, '_last_right_click_time'):
                self._last_right_click_time = 0
            now = time.time()
            # 双击判定（0.35秒内两次）
            if hasattr(self, '_last_right_click_pos') and abs(event.x - self._last_right_click_pos) < 5 and (now - self._last_right_click_time) < 0.35:
                # 右键双击：还原初始状态
                self.price_ax.set_xlim(0, len(self.current_kdata)-1)
                ymin = getattr(self, '_ymin', None)
                ymax = getattr(self, '_ymax', None)
                if ymin is not None and ymax is not None:
                    self.price_ax.set_ylim(ymin, ymax)
                self._zoom_history.clear()
                self.canvas.draw_idle()
                self._optimize_display()
                self._last_right_click_time = 0
                return
            # 记录本次点击
            self._last_right_click_time = now
            self._last_right_click_pos = event.x
            # 右键单击：拖拽平移
            if not hasattr(self, '_drag_start_x') or self._drag_start_x is None:
                self._drag_start_x = event.xdata
                self._drag_start_xlim = self.price_ax.get_xlim()
                self.canvas.mpl_connect(
                    'motion_notify_event', self._on_drag_move)
            else:
                self._drag_start_x = None
                self._drag_start_xlim = None

    def _on_drag_move(self, event):
        if event.inaxes != self.price_ax or event.button != 3:
            return
        if not hasattr(self, '_drag_start_x') or self._drag_start_x is None:
            return
        dx = event.xdata - self._drag_start_x
        left, right = self._drag_start_xlim
        self.price_ax.set_xlim(left - dx, right - dx)
        self._limit_xlim()
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
        self._limit_xlim()
        self.canvas.draw_idle()
        self._optimize_display()  # 保证滚轮缩放后也恢复网格和刻度

    def async_update_chart(self, data: dict, n_segments: int = 20):
        """唯一K线多线程分段预处理实现，最后仍调用update_chart。优化为渲染前显示进度，分段处理时实时更新进度，渲染后关闭进度对话框。"""
        if not data or 'kdata' not in data:
            return
        kdata = data['kdata']
        if len(kdata) <= 100 or n_segments <= 1:
            QTimer.singleShot(0, lambda: self.update_chart({'kdata': kdata}) if hasattr(self, 'update_chart') else None)
            return

        # 分段
        segments = np.array_split(kdata, n_segments)
        results = [None] * n_segments
        progress_step = int(100 / n_segments) if n_segments > 0 else 100

        def process_segment(segment, idx):
            # 这里可以做降采样、指标等预处理
            res = self._downsample_kdata(segment, max_points=1200)
            # 实时更新进度
            QTimer.singleShot(0, lambda: self.update_loading_progress(
                min((idx+1)*progress_step, 100), f"正在处理第{idx+1}/{n_segments}段...") if hasattr(self, 'update_loading_progress') else None)
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
        # 新增：补充 title 和 stock_code 字段，优先从 data 拷贝
        title = data.get('title', '')
        stock_code = data.get('stock_code', '')
        QTimer.singleShot(0, lambda: self.update_chart(
            {'kdata': merged_df, 'title': title, 'stock_code': stock_code}) if hasattr(self, 'update_chart') else None)

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
        # 只在尺寸变化幅度较大时重绘
        if event.oldSize().width() > 0 and event.oldSize().height() > 0:
            if abs(event.oldSize().width() - event.size().width()) < 10 and abs(event.oldSize().height() - event.size().height()) < 10:
                return  # 跳过微小变化
        QTimer.singleShot(0, self.canvas.draw_idle)
        self._optimize_display()

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

    def on_indicator_selected(self, indicators: list):
        """接收指标选择结果，更新active_indicators并刷新图表"""
        self.active_indicators = indicators
        self.update_chart()

    def _on_indicator_changed(self, indicators):
        """多屏同步所有激活指标，仅同步选中项（已废弃，自动同步主窗口get_current_indicators）"""
        self.update_chart()

    def refresh(self) -> None:
        """
        刷新当前图表内容，异常只记录日志不抛出。
        若有数据则重绘K线图，否则显示"无数据"提示。
        """
        try:
            # 这里假设有self.current_kdata等数据
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                self.update_chart({'kdata': self.current_kdata})
            else:
                self.show_no_data("无数据")
        except Exception as e:
            error_msg = f"刷新图表失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            # 发射异常信号，主窗口可捕获弹窗
            self.error_occurred.emit(error_msg)

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def plot_patterns(self, pattern_signals: list, highlight_index: int = None):
        """
        专业化形态信号显示：使用彩色箭头标记，默认隐藏浮窗，集成到十字光标显示
        Args:
            pattern_signals: List[dict]，每个dict至少包含 'index', 'pattern', 'signal', 'confidence' 等字段
        """
        import matplotlib.patches as mpatches

        if not hasattr(self, 'price_ax') or self.current_kdata is None or not pattern_signals:
            return

        ax = self.price_ax
        kdata = self.current_kdata
        x = np.arange(len(kdata))

        # 专业化颜色配置 - 参考同花顺、东方财富等软件
        signal_colors = {
            'buy': '#FF4444',      # 买入信号 - 红色箭头向上
            'sell': '#00AA00',     # 卖出信号 - 绿色箭头向下
            'neutral': '#FFB000'   # 中性信号 - 橙色圆点
        }

        # 置信度透明度映射
        def get_alpha(confidence):
            if confidence >= 0.8:
                return 1.0
            elif confidence >= 0.6:
                return 0.8
            else:
                return 0.6

        # 存储形态信息供十字光标使用
        self._pattern_info = {}

        # 统计有效和无效的形态信号
        valid_patterns = 0
        invalid_patterns = 0

        for pat in pattern_signals:
            idx = pat.get('index')
            if idx is None:
                invalid_patterns += 1
                continue

            # 修复：严格的索引边界检查
            if not isinstance(idx, (int, float)) or idx < 0 or idx >= len(kdata):
                if hasattr(self, 'log_manager') and self.log_manager:
                    self.log_manager.warning(f"形态信号索引超出范围: {idx}, 数据长度: {len(kdata)}")
                invalid_patterns += 1
                continue

            # 确保索引为整数
            idx = int(idx)
            valid_patterns += 1

            pattern_name = pat.get('pattern_name', pat.get('pattern', 'Unknown'))
            signal = pat.get('signal', 'neutral')
            confidence = pat.get('confidence', 0)
            price = kdata.iloc[idx]['high'] if signal == 'buy' else kdata.iloc[idx]['low']

            # 获取颜色和透明度
            color = signal_colors.get(signal, signal_colors['neutral'])
            alpha = get_alpha(confidence)

            # 绘制专业箭头标记
            if signal == 'buy':
                # 买入信号：空心向上三角，位于K线下方
                arrow_y = kdata.iloc[idx]['low'] - (kdata.iloc[idx]['high'] - kdata.iloc[idx]['low']) * 0.15
                ax.scatter(idx, arrow_y, marker='^', s=80, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)
            elif signal == 'sell':
                # 卖出信号：空心向下三角，位于K线上方
                arrow_y = kdata.iloc[idx]['high'] + (kdata.iloc[idx]['high'] - kdata.iloc[idx]['low']) * 0.15
                ax.scatter(idx, arrow_y, marker='v', s=80, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)
            else:
                # 中性信号：空心圆点，位于收盘价位置
                ax.scatter(idx, kdata.iloc[idx]['close'], marker='o', s=60, facecolors='none',
                           edgecolors=color, linewidths=0.8, alpha=alpha, zorder=100)

            # 存储形态信息供十字光标显示
            self._pattern_info[idx] = {
                'pattern_name': pattern_name,
                'signal': signal,
                'confidence': confidence,
                'signal_cn': {'buy': '买入', 'sell': '卖出', 'neutral': '中性'}.get(signal, signal),
                'price': kdata.iloc[idx]['close'],
                'datetime': kdata.index[idx].strftime('%Y-%m-%d') if hasattr(kdata.index[idx], 'strftime') else str(kdata.index[idx])
            }

        # 记录绘制结果
        if hasattr(self, 'log_manager') and self.log_manager:
            self.log_manager.info(f"形态信号绘制完成: 有效 {valid_patterns} 个, 无效 {invalid_patterns} 个")

        # 高亮特定形态（如果指定）
        if highlight_index is not None and highlight_index in self._pattern_info:
            # 添加高亮背景
            ax.axvspan(highlight_index-0.4, highlight_index+0.4,
                       color='yellow', alpha=0.2, zorder=50)

        self.canvas.draw_idle()
        self._current_pattern_signals = pattern_signals
        self._highlight_index = highlight_index

    def highlight_pattern(self, idx: int):
        """外部调用高亮指定K线索引的形态"""
        if hasattr(self, '_current_pattern_signals'):
            self.plot_patterns(self._current_pattern_signals, highlight_index=idx)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        save_action = menu.addAction("保存图表为图片")
        export_action = menu.addAction("导出K线/指标数据")
        indicator_action = menu.addAction("添加/隐藏指标")
        stat_action = menu.addAction("区间统计")
        highlight_action = menu.addAction("标记/高亮K线")
        replay_action = menu.addAction("历史回看/回放")
        copy_action = menu.addAction("复制图表到剪贴板")
        refresh_action = menu.addAction("刷新图表")
        clear_highlight_action = menu.addAction("清空高亮")
        action = menu.exec_(event.globalPos())
        if action == save_action:
            self.save_chart_image()
        elif action == export_action:
            self.export_kline_and_indicators()
        elif action == indicator_action:
            self.request_indicator_dialog.emit()
        elif action == stat_action:
            self.trigger_stat_dialog()
        elif action == highlight_action:
            self.mark_highlight_candle(event)
        elif action == replay_action:
            self.toggle_replay()
        elif action == copy_action:
            self.copy_chart_to_clipboard()
        elif action == refresh_action:
            self.refresh()
        elif action == clear_highlight_action:
            self.clear_highlighted_candles()

    def save_chart_image(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存图表", "", "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)")
            if file_path:
                self.figure.savefig(file_path)
                if self.log_manager:
                    self.log_manager.info(f"图表已保存到: {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"保存图表失败: {str(e)}")

    def export_kline_and_indicators(self):
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                QMessageBox.warning(self, "提示", "当前无K线数据可导出！")
                return
            df = self.current_kdata.copy()
            # 合并所有已绘制指标（假设指标已添加为df列）
            # 可扩展：遍历self.active_indicators，合并指标数据
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出K线/指标数据", "", "CSV Files (*.csv)")
            if file_path:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                if self.log_manager:
                    self.log_manager.info(f"K线/指标数据已导出到: {file_path}")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出K线/指标数据失败: {str(e)}")

    def trigger_stat_dialog(self):
        # 统计当前缩放区间或鼠标选区
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                QMessageBox.warning(self, "提示", "当前无K线数据可统计！")
                return
            # 取当前X轴可见范围
            xlim = self.price_ax.get_xlim()
            start_idx = int(max(0, round(xlim[0])))
            end_idx = int(min(len(self.current_kdata)-1, round(xlim[1])))
            self.request_stat_dialog.emit((start_idx, end_idx))
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"区间统计失败: {str(e)}")

    def mark_highlight_candle(self, event):
        # 标记鼠标所在K线为高亮
        try:
            if self.current_kdata is None or self.current_kdata.empty:
                return
            # 计算鼠标在axes中的xdata
            pos = self.price_ax.transData.inverted().transform((event.x(), event.y()))
            x_idx = int(round(pos[0]))
            if 0 <= x_idx < len(self.current_kdata):
                self.highlighted_indices.add(x_idx)
                self.refresh()
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"标记高亮K线失败: {str(e)}")

    def clear_highlighted_candles(self):
        self.highlighted_indices.clear()
        self.refresh()

    def toggle_replay(self):
        # 历史回看/回放动画
        try:
            if self._replay_timer and self._replay_timer.isActive():
                self._replay_timer.stop()
                self._replay_timer = None
                self._replay_index = None
                return
            if self.current_kdata is None or self.current_kdata.empty:
                return
            from PyQt5.QtCore import QTimer
            self._replay_index = 10  # 从第10根K线开始
            self._replay_timer = QTimer(self)
            self._replay_timer.timeout.connect(self._replay_step)
            self._replay_timer.start(100)
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"历史回看/回放启动失败: {str(e)}")

    def _replay_step(self):
        if self._replay_index is None or self.current_kdata is None:
            return
        if self._replay_index >= len(self.current_kdata):
            self._replay_timer.stop()
            self._replay_index = None
            return
        # 只显示前self._replay_index根K线
        self.update_chart(
            {'kdata': self.current_kdata.iloc[:self._replay_index]})
        self._replay_index += 1

    def copy_chart_to_clipboard(self):
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QPixmap
            import io
            buf = io.BytesIO()
            self.figure.savefig(buf, format='png')
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read(), 'PNG')
            QApplication.clipboard().setPixmap(pixmap)
            if self.log_manager:
                self.log_manager.info("图表已复制到剪贴板")
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"复制图表到剪贴板失败: {str(e)}")

    def get_visible_range(self):
        # 获取当前主图可见区间的K线索引范围（伪代码，需结合xlim等）
        try:
            xlim = self.indicator_ax.get_xlim()
            return int(xlim[0]), int(xlim[1])
        except Exception:
            return None

    def highlight_signals(self, signals):
        """高亮指定信号"""
        try:
            # 清除旧高亮
            self.clear_signal_highlight()

            if not signals or not hasattr(self, 'main_ax') or not self.main_ax:
                return

            # 绘制高亮效果
            highlight_artists = []
            for signal in signals:
                idx = signal.get('index', 0)
                price = signal.get('price', 0)

                # 高亮圆圈
                highlight_circle = self.main_ax.scatter(idx, price, s=200,
                                                        facecolors='none', edgecolors='yellow',
                                                        linewidths=3, alpha=0.8, zorder=30)
                highlight_artists.append(highlight_circle)

                # 高亮文字
                highlight_text = self.main_ax.text(idx, price * 1.03, f"选中: {signal.get('type', '')}",
                                                   fontsize=10, ha='center', va='bottom',
                                                   color='yellow', fontweight='bold',
                                                   bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
                highlight_artists.append(highlight_text)

            # 保存高亮对象用于清除
            self._highlight_artists = highlight_artists

            # 自动调整视图范围至高亮信号
            if len(signals) == 1:
                signal = signals[0]
                idx = signal.get('index', 0)
                current_xlim = self.main_ax.get_xlim()
                window_size = current_xlim[1] - current_xlim[0]
                new_center = idx
                self.main_ax.set_xlim(new_center - window_size/2, new_center + window_size/2)

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"高亮信号失败: {str(e)}")

    def clear_signal_highlight(self):
        """清除信号高亮"""
        try:
            # 安全移除高亮对象
            highlight_artists = getattr(self, '_highlight_artists', [])
            if highlight_artists:
                # 尝试确定父axes（通常是main_ax或price_ax）
                parent_ax = getattr(self, 'main_ax', None) or getattr(self, 'price_ax', None)
                self._safe_remove_artists_list(highlight_artists, parent_ax)
            self._highlight_artists = []

            # 安全清除气泡提示
            tooltip_artists = getattr(self, '_tooltip_artists', [])
            if tooltip_artists:
                parent_ax = getattr(self, 'main_ax', None) or getattr(self, 'price_ax', None)
                self._safe_remove_artists_list(tooltip_artists, parent_ax)
            self._tooltip_artists = []

            self.canvas.draw()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"清除信号高亮失败: {str(e)}")

    def _safe_get_label(self, obj):
        """安全地获取matplotlib对象的标签，确保返回字符串类型

        Args:
            obj: matplotlib对象（Line2D, Text等）

        Returns:
            str: 标签字符串，如果无法获取则返回空字符串
        """
        try:
            if hasattr(obj, 'get_label'):
                label = obj.get_label()
                # 如果是Text对象，获取其文本内容
                if hasattr(label, 'get_text'):
                    return str(label.get_text())
                # 如果已经是字符串，直接返回
                elif isinstance(label, str):
                    return label
                # 其他情况，尝试转换为字符串
                else:
                    return str(label) if label is not None else ""
            else:
                return ""
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"获取标签失败: {str(e)}")
            return ""

    def _safe_remove_artist(self, artist, parent_ax=None):
        """安全移除matplotlib artist对象，避免'list.remove(x): x not in list'错误

        Args:
            artist: 要移除的matplotlib artist对象
            parent_ax: 父axes对象，用于检查对象是否仍在容器中

        Returns:
            bool: 移除是否成功（包括对象已不存在的情况）
        """
        try:
            if artist is None:
                return True

            if not hasattr(artist, 'remove'):
                return True

            # 检查对象是否仍在父容器中
            if parent_ax is not None and hasattr(parent_ax, 'get_children'):
                try:
                    if artist not in parent_ax.get_children():
                        if hasattr(self, 'log_manager'):
                            self.log_manager.debug("Artist已不在父容器中，跳过移除")
                        return True  # 已经不在容器中，无需移除
                except (ValueError, TypeError):
                    # 容器可能已被修改，继续尝试移除
                    pass

            # 尝试移除
            artist.remove()
            if hasattr(self, 'log_manager'):
                self.log_manager.debug("Artist移除成功")
            return True

        except ValueError as e:
            if "not in list" in str(e):
                # 对象已经被移除，这是预期的情况
                if hasattr(self, 'log_manager'):
                    self.log_manager.debug(f"Artist已被移除: {str(e)}")
                return True
            else:
                if hasattr(self, 'log_manager'):
                    self.log_manager.warning(f"移除artist时出现ValueError: {str(e)}")
                return False
        except AttributeError as e:
            # 对象可能已经被销毁
            if hasattr(self, 'log_manager'):
                self.log_manager.debug(f"Artist对象已销毁: {str(e)}")
            return True
        except Exception as e:
            # 其他未预期的错误
            if hasattr(self, 'log_manager'):
                self.log_manager.warning(f"移除artist时出现未预期错误: {str(e)}")
            return False

    def _safe_remove_artists_list(self, artists_list, parent_ax=None):
        """安全移除一组matplotlib artist对象

        Args:
            artists_list: artist对象列表
            parent_ax: 父axes对象

        Returns:
            tuple: (成功移除数量, 总数量)
        """
        if not artists_list:
            return 0, 0

        success_count = 0
        total_count = len(artists_list)

        for artist in artists_list:
            if self._safe_remove_artist(artist, parent_ax):
                success_count += 1

        if hasattr(self, 'log_manager'):
            self.log_manager.debug(f"批量移除完成: {success_count}/{total_count}")
        return success_count, total_count

    def _add_indicator_impl(self, indicator_info, indicator_colors: list = None):
        """添加指标的具体实现 - 保持向后兼容"""
        try:
            if not hasattr(self, 'current_kdata') or self.current_kdata is None or self.current_kdata.empty:
                self.log_manager.warning("没有K线数据，跳过指标计算")
                return

            # 安全获取指标信息，支持IndicatorInfo对象和字典
            if hasattr(indicator_info, 'name'):
                indicator_name = indicator_info.name
                indicator_params = getattr(indicator_info, 'parameters', {})
                chinese_name = getattr(indicator_info, 'chinese_name', indicator_name)
            elif isinstance(indicator_info, dict):
                indicator_name = indicator_info.get('name', '')
                indicator_params = indicator_info.get('params', {})
                chinese_name = indicator_info.get('chinese_name', indicator_name)
            else:
                self.log_manager.error(f"不支持的指标信息格式: {type(indicator_info)}")
                return

            # 计算指标值
            indicator_values = self._calculate_indicator(indicator_name, self.current_kdata, indicator_params)

            if indicator_values is None:
                self.log_manager.warning(f"无法计算指标: {indicator_name}")
                return

            # 绘制指标
            self._plot_indicator(indicator_name, indicator_values, chinese_name, indicator_colors)

            # 更新图例
            self._update_legend()

            # 重新绘制图表
            QTimer.singleShot(0, lambda: self.canvas.draw_idle() if hasattr(self, 'canvas') and self.canvas is not None else None)

            self.log_manager.info(f"成功添加指标: {chinese_name} ({indicator_name})")

        except Exception as e:
            error_msg = f"添加指标实现失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
