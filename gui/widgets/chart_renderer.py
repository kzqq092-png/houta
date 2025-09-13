from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import to_rgba
import mplfinance as mpf
from typing import List, Dict, Any, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import warnings
from loguru import logger

# 配置中文字体
try:
    from utils.matplotlib_font_config import configure_matplotlib_chinese_font
    configure_matplotlib_chinese_font()
except ImportError:
    logger.info(" 无法导入字体配置工具，使用默认配置")


class ChartRenderer(QObject):
    """高性能图表渲染器，优化大数据渲染性能"""

    render_progress = pyqtSignal(int, str)  # 渲染进度信号
    render_complete = pyqtSignal()  # 渲染完成信号
    render_error = pyqtSignal(str)  # 错误信号

    def __init__(self):
        super().__init__()
        self._view_range = None  # 当前视图范围
        self._downsampling_threshold = 5000  # 降采样阈值
        self._last_layout = None  # 缓存上一次布局参数

    def setup_figure(self, figure: Figure) -> Tuple[GridSpec, List]:
        """设置图表布局，避免tight_layout警告

        Args:
            figure: matplotlib图表对象

        Returns:
            Tuple[GridSpec, List[Axes]]: 网格布局和轴对象列表
        """
        # 清除现有内容
        figure.clear()

        # 创建网格布局
        gs = GridSpec(3, 1, figure=figure, height_ratios=[
                      3, 1, 1], hspace=0.05)

        # 创建子图，共享x轴
        price_ax = figure.add_subplot(gs[0])
        volume_ax = figure.add_subplot(gs[1], sharex=price_ax)
        indicator_ax = figure.add_subplot(gs[2], sharex=price_ax)

        # 隐藏不需要的刻度标签
        volume_ax.set_xticklabels([])
        price_ax.set_xticklabels([])

        # 设置边距
        figure.subplots_adjust(
            left=0.05, right=0.95,
            top=0.95, bottom=0.05,
            hspace=0.1
        )

        return gs, [price_ax, volume_ax, indicator_ax]

    def render_candlesticks(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None, x: np.ndarray = None):
        """高性能K线绘制，支持等距序号X轴
        Args:
            ax: matplotlib轴对象
            data: K线数据
            style: 样式字典
            x: 可选，等距序号X轴
        """
        try:
            view_data = self._get_view_data(data)
            plot_data = self._downsample_data(view_data)
            self._render_candlesticks_efficient(ax, plot_data, style or {}, x)
            self._optimize_display(ax)
        except Exception as e:
            self.render_error.emit(f"绘制K线失败: {str(e)}")

    def _render_candlesticks_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any], x: np.ndarray = None):
        """使用collections高效渲染K线，支持等距序号X轴，空心样式"""
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('alpha', 1.0)
        # 横坐标
        if x is not None:
            xvals = x
        else:
            xvals = mdates.date2num(data.index.to_pydatetime())
        verts_up, verts_down, segments_up, segments_down = [], [], [], []
        for i, (idx, row) in enumerate(data.iterrows()):
            open_price = row['open']
            close = row['close']
            high = row['high']
            low = row['low']
            left = xvals[i] - 0.3
            right = xvals[i] + 0.3
            if close >= open_price:
                verts_up.append([
                    (left, open_price), (left, close), (right,
                                                        close), (right, open_price)
                ])
                segments_up.append([(xvals[i], low), (xvals[i], high)])
            else:
                verts_down.append([
                    (left, open_price), (left, close), (right,
                                                        close), (right, open_price)
                ])
                segments_down.append([(xvals[i], low), (xvals[i], high)])
        # 修改：空心蜡烛图样式，只有边框无填充
        if verts_up:
            collection_up = PolyCollection(
                verts_up, facecolor=up_color, edgecolor=up_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_up)
        if verts_down:
            collection_down = PolyCollection(
                verts_down, facecolor=down_color, edgecolor=down_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_down)
        if segments_up:  # 影线
            collection_shadow_up = LineCollection(
                segments_up, colors=up_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_shadow_up)
        if segments_down:
            collection_shadow_down = LineCollection(
                segments_down, colors=down_color, linewidth=0.5, alpha=alpha)
            ax.add_collection(collection_shadow_down)
        ax.autoscale_view()

    def render_volume(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None, x: np.ndarray = None):
        """高性能成交量绘制，支持等距序号X轴
        Args:
            ax: matplotlib轴对象
            data: 成交量数据
            style: 样式字典
            x: 可选，等距序号X轴
        """
        try:
            view_data = self._get_view_data(data)
            plot_data = self._downsample_data(view_data)
            self._render_volume_efficient(ax, plot_data, style or {}, x)
            self._optimize_display(ax)
        except Exception as e:
            self.render_error.emit(f"绘制成交量失败: {str(e)}")

    def _render_volume_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any], x: np.ndarray = None):
        """使用collections高效渲染成交量，支持等距序号X轴"""
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('volume_alpha', 0.5)
        if x is not None:
            xvals = x
        else:
            xvals = mdates.date2num(data.index.to_pydatetime())
        verts_up, verts_down = [], []
        for i, (idx, row) in enumerate(data.iterrows()):
            volume = row['volume']
            close = row['close']
            open_price = row['open']
            left = xvals[i] - 0.3
            right = xvals[i] + 0.3
            if close >= open_price:
                verts_up.append([
                    (left, 0), (left, volume), (right, volume), (right, 0)
                ])
            else:
                verts_down.append([
                    (left, 0), (left, volume), (right, volume), (right, 0)
                ])
        if verts_up:
            collection_up = PolyCollection(
                verts_up, facecolor=up_color, edgecolor='none', alpha=alpha)
            ax.add_collection(collection_up)
        if verts_down:
            collection_down = PolyCollection(
                verts_down, facecolor=down_color, edgecolor='none', alpha=alpha)
            ax.add_collection(collection_down)
        ax.autoscale_view()

    def render_line(self, ax, data: pd.Series, style: Dict[str, Any] = None):
        """高性能线图绘制

        Args:
            ax: matplotlib轴对象
            data: 线图数据
            style: 样式字典
        """
        try:
            # 获取当前视图范围内的数据
            view_data = self._get_view_data(data)

            # 降采样
            plot_data = self._downsample_data(view_data)

            # 使用LineCollection批量渲染
            self._render_line_efficient(ax, plot_data, style or {})

            # 优化显示
            self._optimize_display(ax)

        except Exception as e:
            self.render_error.emit(f"绘制线图失败: {str(e)}")

    def _render_line_efficient(self, ax, data: pd.Series, style: Dict[str, Any]):
        """使用LineCollection高效渲染线图

        Args:
            ax: matplotlib轴对象
            data: 线图数据
            style: 样式字典
        """
        # 获取样式
        color = style.get('color', 'blue')
        linewidth = style.get('linewidth', 1.0)
        alpha = style.get('alpha', 0.8)
        label = style.get('label', '')

        # 转换日期为数值
        if isinstance(data.index, pd.DatetimeIndex):
            x = mdates.date2num(data.index.to_pydatetime())
        else:
            x = np.arange(len(data))

        # 创建线段
        points = np.column_stack((x, data.values))
        segments = np.column_stack((points[:-1], points[1:]))

        # 创建LineCollection
        collection = LineCollection(
            segments,
            colors=color,
            linewidth=linewidth,
            alpha=alpha,
            label=label
        )

        # 添加到轴
        ax.add_collection(collection)

        # 设置轴范围
        ax.autoscale_view()

        # 添加图例
        if label:
            ax.legend()

    def _get_view_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """获取当前视图范围内的数据

        Args:
            data: 原始数据

        Returns:
            视图范围内的数据
        """
        if self._view_range is None:
            return data

        start, end = self._view_range
        return data.loc[start:end]

    def _downsample_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """智能降采样，保持关键特征

        Args:
            data: 原始数据

        Returns:
            降采样后的数据
        """
        if len(data) <= self._downsampling_threshold:
            return data

        # 使用 OHLCV 保持降采样
        sample_size = len(data) // self._downsampling_threshold

        # 创建结果DataFrame
        result = pd.DataFrame(index=data.index[::sample_size])

        # 处理OHLC数据
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            result['open'] = data['open'].iloc[::sample_size]
            result['high'] = data['high'].rolling(
                sample_size, min_periods=1).max()
            result['low'] = data['low'].rolling(
                sample_size, min_periods=1).min()
            result['close'] = data['close'].iloc[::sample_size]

        # 处理成交量
        if 'volume' in data.columns:
            result['volume'] = data['volume'].rolling(
                sample_size, min_periods=1).sum()

        # 处理其他列（使用平均值）
        other_cols = [col for col in data.columns if col not in [
            'open', 'high', 'low', 'close', 'volume']]
        for col in other_cols:
            result[col] = data[col].rolling(sample_size, min_periods=1).mean()

        return result

    def _optimize_display(self, ax):
        """优化显示效果

        Args:
            ax: matplotlib轴对象
        """
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

        # 优化刻度
        ax.tick_params(axis='both', which='major', labelsize=8)

        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.3)

    def set_view_range(self, start: pd.Timestamp, end: pd.Timestamp):
        """设置视图范围

        Args:
            start: 起始时间
            end: 结束时间
        """
        self._view_range = (start, end)

    def clear_view_range(self):
        """清除视图范围限制"""
        self._view_range = None
