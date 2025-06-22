"""
图表工具模块
提供可视化组件的基础图表功能
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from typing import Tuple, List, Optional, Any

# 尝试导入candlestick函数，如果失败则使用替代方案
try:
    from matplotlib.finance import candlestick_ohlc
except ImportError:
    try:
        from mplfinance.original_flavor import candlestick_ohlc
    except ImportError:
        candlestick_ohlc = None


class ChartUtils:
    """图表工具类"""

    def __init__(self):
        """初始化图表工具"""
        self.default_style = {
            'figure.figsize': (12, 8),
            'axes.grid': True,
            'grid.alpha': 0.3,
            'font.size': 10
        }

    def create_subplots(self, nrows: int = 1, ncols: int = 1,
                        figsize: Optional[Tuple[float, float]] = None,
                        **kwargs) -> Tuple[plt.Figure, Any]:
        """
        创建子图

        Args:
            nrows: 行数
            ncols: 列数
            figsize: 图形大小
            **kwargs: 其他参数

        Returns:
            图形对象和轴对象
        """
        if figsize is None:
            figsize = self.default_style['figure.figsize']

        fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                                 figsize=figsize, **kwargs)
        return fig, axes

    def plot_kline(self, ax: plt.Axes, kdata: pd.DataFrame) -> None:
        """
        绘制K线图

        Args:
            ax: 轴对象
            kdata: K线数据
        """
        if candlestick_ohlc is not None:
            try:
                # 准备数据
                if 'datetime' in kdata.columns:
                    dates = mdates.date2num(pd.to_datetime(kdata['datetime']))
                else:
                    dates = np.arange(len(kdata))

                # 创建OHLC数据
                ohlc_data = list(zip(dates, kdata['open'], kdata['high'],
                                     kdata['low'], kdata['close']))

                # 绘制K线
                candlestick_ohlc(ax, ohlc_data, width=0.6, colorup='red',
                                 colordown='green', alpha=0.8)

                # 设置标题
                ax.set_title('K线图', fontsize=12)
                ax.set_ylabel('价格', fontsize=10)
                return

            except Exception:
                pass

        # 如果candlestick_ohlc不可用，使用简单的线图
        ax.plot(kdata['close'], label='收盘价', color='blue', linewidth=1)
        ax.set_title('价格走势', fontsize=12)
        ax.set_ylabel('价格', fontsize=10)

    def plot_volume(self, ax: plt.Axes, kdata: pd.DataFrame) -> None:
        """
        绘制成交量图

        Args:
            ax: 轴对象
            kdata: K线数据
        """
        if 'volume' not in kdata.columns:
            return

        volume = kdata['volume']
        x = np.arange(len(volume))

        # 根据涨跌着色
        colors = ['red' if c >= o else 'green'
                  for c, o in zip(kdata['close'], kdata['open'])]

        ax.bar(x, volume, color=colors, alpha=0.6, width=0.8)
        ax.set_title('成交量', fontsize=12)
        ax.set_ylabel('成交量', fontsize=10)

    def plot_indicator(self, ax: plt.Axes, data: pd.Series,
                       label: str, color: str = 'blue') -> None:
        """
        绘制指标线

        Args:
            ax: 轴对象
            data: 指标数据
            label: 标签
            color: 颜色
        """
        x = np.arange(len(data))
        ax.plot(x, data, label=label, color=color, linewidth=1.2)

    def set_axis_format(self, ax: plt.Axes) -> None:
        """
        设置轴格式

        Args:
            ax: 轴对象
        """
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', which='major', labelsize=8)

        # 如果是时间轴，设置时间格式
        try:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        except:
            pass

    def add_legend(self, ax: plt.Axes) -> None:
        """
        添加图例

        Args:
            ax: 轴对象
        """
        handles, labels = ax.get_legend_handles_labels()
        if handles and labels:
            ax.legend(loc='upper left', fontsize=8, frameon=True,
                      fancybox=True, shadow=True, framealpha=0.8)

    def adjust_layout(self, fig: plt.Figure) -> None:
        """
        调整布局

        Args:
            fig: 图形对象
        """
        fig.tight_layout()

    def save_chart(self, fig: plt.Figure, filename: str,
                   dpi: int = 300, bbox_inches: str = 'tight') -> None:
        """
        保存图表

        Args:
            fig: 图形对象
            filename: 文件名
            dpi: 分辨率
            bbox_inches: 边界设置
        """
        fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches)

    def clear_axes(self, axes: Any) -> None:
        """
        清空轴

        Args:
            axes: 轴对象或轴对象列表
        """
        if hasattr(axes, '__iter__'):
            for ax in axes:
                ax.clear()
        else:
            axes.clear()

    def set_style(self, style_dict: dict) -> None:
        """
        设置样式

        Args:
            style_dict: 样式字典
        """
        plt.rcParams.update(style_dict)
