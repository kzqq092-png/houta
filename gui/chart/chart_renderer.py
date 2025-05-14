from matplotlib.patches import Rectangle
import pandas as pd
from typing import Dict, Any
import matplotlib.dates as mdates
import numpy as np
from matplotlib.collections import PolyCollection, LineCollection


def render_candlesticks(self, ax, kdata, style):
    """
    绘制K线图，K线颜色alpha强制为1.0，保证大数据量下颜色依然明亮。
    :param ax: matplotlib Axes
    :param kdata: K线数据
    :param style: 颜色样式
    """
    opens = kdata['open']
    closes = kdata['close']
    highs = kdata['high']
    lows = kdata['low']
    x = range(len(opens))
    color_up = style['up_color']
    color_down = style['down_color']
    # 强制alpha为1.0
    if len(color_up) == 4:
        color_up = (color_up[0], color_up[1], color_up[2], 1.0)
    if len(color_down) == 4:
        color_down = (color_down[0], color_down[1], color_down[2], 1.0)
    for i in x:
        color = color_up if closes[i] >= opens[i] else color_down
        ax.plot([i, i], [lows[i], highs[i]],
                color=color, linewidth=1.0, zorder=1)
        rect = Rectangle(
            (i - 0.3, min(opens[i], closes[i])),
            0.6,
            abs(opens[i] - closes[i]),
            color=color,
            zorder=2
        )
        ax.add_patch(rect)

    def render_candlesticks(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None):
        """高性能K线绘制，使用collections批量渲染，x轴用DatetimeIndex，节假日无数据自动跳过"""
        try:
            # 获取当前视图范围内的数据
            view_data = self._get_view_data(data)
            # 降采样
            plot_data = self._downsample_data(view_data)
            # 用kdata.index驱动x轴，节假日无数据自动跳过
            self._render_candlesticks_efficient(ax, plot_data, style or {})
            # 优化显示
            self._optimize_display(ax)
        except Exception as e:
            self.render_error.emit(f"绘制K线失败: {str(e)}")

    def _render_candlesticks_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any]):
        """使用collections高效渲染K线，x轴用DatetimeIndex，节假日无数据自动跳过"""
        # 获取样式
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('alpha', 1.0)
        # 转换日期为数值
        dates = mdates.date2num(data.index.to_pydatetime())
        # 创建K线实体
        verts_up = []
        verts_down = []
        # 创建影线
        segments_up = []
        segments_down = []
        for i, date in enumerate(dates):
            open_ = data['open'].iloc[i]
            close = data['close'].iloc[i]
            high = data['high'].iloc[i]
            low = data['low'].iloc[i]
            color = up_color if close >= open_ else down_color
            # 主体
            if close >= open_:
                verts_up.append([
                    (date - 0.3, open_),
                    (date - 0.3, close),
                    (date + 0.3, close),
                    (date + 0.3, open_)
                ])
            else:
                verts_down.append([
                    (date - 0.3, open_),
                    (date - 0.3, close),
                    (date + 0.3, close),
                    (date + 0.3, open_)
                ])
            # 影线
            if close >= open_:
                segments_up.append([(date, low), (date, high)])
            else:
                segments_down.append([(date, low), (date, high)])
        # 绘制上涨K线
        if verts_up:
            collection_up = PolyCollection(
                verts_up,
                facecolor=up_color,
                edgecolor='none',
                alpha=alpha
            )
            ax.add_collection(collection_up)
        # 绘制下跌K线
        if verts_down:
            collection_down = PolyCollection(
                verts_down,
                facecolor=down_color,
                edgecolor='none',
                alpha=alpha
            )
            ax.add_collection(collection_down)
        # 绘制上涨影线
        if segments_up:
            collection_shadow_up = LineCollection(
                segments_up,
                colors=up_color,
                linewidth=0.5,
                alpha=alpha
            )
            ax.add_collection(collection_shadow_up)
        # 绘制下跌影线
        if segments_down:
            collection_shadow_down = LineCollection(
                segments_down,
                colors=down_color,
                linewidth=0.5,
                alpha=alpha
            )
            ax.add_collection(collection_shadow_down)
        # 设置轴范围
        ax.autoscale_view()

    def render_volume(self, ax, data: pd.DataFrame, style: Dict[str, Any] = None):
        """高性能成交量绘制，x轴用DatetimeIndex，节假日无数据自动跳过"""
        try:
            # 获取当前视图范围内的数据
            view_data = self._get_view_data(data)
            # 降采样
            plot_data = self._downsample_data(view_data)
            # 用kdata.index驱动x轴，节假日无数据自动跳过
            self._render_volume_efficient(ax, plot_data, style or {})
            # 优化显示
            self._optimize_display(ax)
        except Exception as e:
            self.render_error.emit(f"绘制成交量失败: {str(e)}")

    def _render_volume_efficient(self, ax, data: pd.DataFrame, style: Dict[str, Any]):
        """使用collections高效渲染成交量，x轴用DatetimeIndex，节假日无数据自动跳过"""
        up_color = style.get('up_color', '#ff0000')
        down_color = style.get('down_color', '#00ff00')
        alpha = style.get('volume_alpha', 0.5)
        dates = mdates.date2num(data.index.to_pydatetime())
        verts_up = []
        verts_down = []
        for i, date in enumerate(dates):
            volume = data['volume'].iloc[i]
            close = data['close'].iloc[i]
            open_price = data['open'].iloc[i]
            left = date - 0.3
            right = date + 0.3
            if close >= open_price:
                verts_up.append([
                    (left, 0),
                    (left, volume),
                    (right, volume),
                    (right, 0)
                ])
            else:
                verts_down.append([
                    (left, 0),
                    (left, volume),
                    (right, volume),
                    (right, 0)
                ])
        if verts_up:
            collection_up = PolyCollection(
                verts_up,
                facecolor=up_color,
                edgecolor='none',
                alpha=alpha
            )
            ax.add_collection(collection_up)
        if verts_down:
            collection_down = PolyCollection(
                verts_down,
                facecolor=down_color,
                edgecolor='none',
                alpha=alpha
            )
            ax.add_collection(collection_down)
        ax.autoscale_view()

    def render_line(self, ax, data: pd.Series, style: Dict[str, Any] = None):
        """高性能线图绘制，x轴用DatetimeIndex，节假日无数据自动跳过"""
        try:
            # 获取当前视图范围内的数据
            view_data = self._get_view_data(data)
            # 降采样
            plot_data = self._downsample_data(view_data)
            # 用kdata.index驱动x轴，节假日无数据自动跳过
            self._render_line_efficient(ax, plot_data, style or {})
            # 优化显示
            self._optimize_display(ax)
        except Exception as e:
            self.render_error.emit(f"绘制线图失败: {str(e)}")

    def _render_line_efficient(self, ax, data: pd.Series, style: Dict[str, Any]):
        """使用LineCollection高效渲染线图，x轴用DatetimeIndex，节假日无数据自动跳过"""
        color = style.get('color', 'blue')
        linewidth = style.get('linewidth', 1.0)
        alpha = style.get('alpha', 0.8)
        label = style.get('label', '')
        if isinstance(data.index, pd.DatetimeIndex):
            x = mdates.date2num(data.index.to_pydatetime())
        else:
            x = np.arange(len(data))
        points = np.column_stack((x, data.values))
        segments = np.column_stack((points[:-1], points[1:]))
        collection = LineCollection(
            segments,
            colors=color,
            linewidth=linewidth,
            alpha=alpha,
            label=label
        )
        ax.add_collection(collection)
        ax.autoscale_view()
        if label:
            ax.legend()
