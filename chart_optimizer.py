import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import CheckButtons
from matplotlib.animation import FuncAnimation
from typing import Dict, List, Optional
import mplfinance as mpf


class ChartOptimizer:
    """图表性能优化器"""

    @staticmethod
    def optimize_figure(fig: Figure):
        """优化图表配置

        Args:
            fig: matplotlib图表对象
        """
        # 设置更高效的渲染后端
        plt.style.use('fast')
        fig.set_dpi(100)  # 适中的DPI值平衡清晰度和性能

        # 启用快速绘图模式
        for ax in fig.axes:
            ax.set_adjustable('datalim')
            ax.set_animated(True)

        # 优化内存使用
        fig.set_tight_layout(True)

    @staticmethod
    def create_blitting_canvas(canvas):
        """创建用于blitting优化的背景

        Args:
            canvas: matplotlib画布对象

        Returns:
            background: 背景图像
        """
        canvas.draw()
        return canvas.copy_from_bbox(canvas.figure.bbox)

    @staticmethod
    def apply_theme(fig: Figure, theme: str = 'light'):
        """应用主题样式

        Args:
            fig: matplotlib图表对象
            theme: 主题名称，可选 'light' 或 'dark'
        """
        if theme == 'light':
            plt.style.use('seaborn-v0_8-whitegrid')
            fig.patch.set_facecolor('white')
            for ax in fig.axes:
                ax.set_facecolor('white')
                ax.grid(True, alpha=0.2)
        else:
            plt.style.use('dark_background')
            fig.patch.set_facecolor('#2E2E2E')
            for ax in fig.axes:
                ax.set_facecolor('#2E2E2E')
                ax.grid(True, alpha=0.1)

    @staticmethod
    def create_interactive_legend(ax, alpha=0.5):
        """创建交互式图例

        Args:
            ax: matplotlib轴对象
            alpha: 透明度

        Returns:
            check: 复选框控件
        """
        lines = ax.get_lines()
        labels = []
        for line in lines:
            try:
                label = line.get_label()
                # 如果是Text对象，获取其文本内容
                if hasattr(label, 'get_text'):
                    label = str(label.get_text())
                elif isinstance(label, str):
                    label = label
                else:
                    label = str(label) if label is not None else ""
                labels.append(label)
            except Exception:
                labels.append("")

        # 创建复选框
        rax = plt.axes([0.05, 0.4, 0.1, 0.15])
        check = CheckButtons(rax, labels)

        def func(label):
            # 安全地查找匹配的线条
            matching_lines = []
            for l in lines:
                try:
                    l_label = l.get_label()
                    if hasattr(l_label, 'get_text'):
                        l_label = str(l_label.get_text())
                    elif isinstance(l_label, str):
                        l_label = l_label
                    else:
                        l_label = str(l_label) if l_label is not None else ""

                    if l_label == label:
                        matching_lines.append(l)
                except Exception:
                    continue

            if matching_lines:
                line = matching_lines[0]
            line.set_visible(not line.get_visible())
            ax.figure.canvas.draw_idle()

        check.on_clicked(func)
        return check

    @staticmethod
    def setup_realtime_animation(fig, update_func, interval=1000):
        """设置实时动画更新

        Args:
            fig: matplotlib图表对象
            update_func: 更新函数
            interval: 更新间隔(毫秒)

        Returns:
            anim: 动画对象
        """
        return FuncAnimation(fig, update_func, interval=interval)

    @staticmethod
    def optimize_candlestick_chart(fig, data, style='yahoo'):
        """优化K线图显示

        Args:
            fig: matplotlib图表对象
            data: K线数据
            style: 样式名称
        """
        # 设置K线图样式
        mc = mpf.make_marketcolors(
            up='red', down='green',
            edge='inherit',
            wick='inherit',
            volume='in',
            ohlc='inherit'
        )
        s = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='solid',
            y_on_right=True
        )

        # 使用mplfinance绘制优化的K线图
        mpf.plot(
            data,
            type='candle',
            style=s,
            volume=True,
            panel_ratios=(3, 1),
            figsize=(12, 8),
            tight_layout=True,
            figure=fig
        )

    @staticmethod
    def create_multi_timeframe_chart(fig, data_dict):
        """创建多时间周期图表

        Args:
            fig: matplotlib图表对象
            data_dict: 不同时间周期的数据字典
        """
        n = len(data_dict)
        for i, (period, data) in enumerate(data_dict.items()):
            ax = fig.add_subplot(n, 1, i+1)
            ChartOptimizer.optimize_candlestick_chart(ax, data)
            ax.set_title(f'{period} Chart')

    @staticmethod
    def add_technical_overlay(ax, data, indicator_type, **params):
        """添加技术指标叠加

        Args:
            ax: matplotlib轴对象
            data: 数据
            indicator_type: 指标类型
            params: 指标参数
        """
        if indicator_type == 'MA':
            periods = params.get('periods', [5, 10, 20, 60])
            colors = params.get('colors', ['red', 'blue', 'green', 'purple'])
            for period, color in zip(periods, colors):
                ma = data.close.rolling(period).mean()
                ax.plot(data.index, ma, color=color,
                        label=f'MA{period}', linewidth=0.7)

        elif indicator_type == 'BOLL':
            period = params.get('period', 20)
            std = params.get('std', 2)
            middle = data.close.rolling(period).mean()
            std_dev = data.close.rolling(period).std()
            upper = middle + std * std_dev
            lower = middle - std * std_dev

            ax.plot(data.index, upper, 'r--', label='Upper Band')
            ax.plot(data.index, middle, 'b-', label='Middle Band')
            ax.plot(data.index, lower, 'g--', label='Lower Band')

        # 添加更多指标...

        ax.legend()

    @staticmethod
    def create_volume_profile(ax, data, bins=50):
        """创建成交量分布图

        Args:
            ax: matplotlib轴对象
            data: 数据
            bins: 分箱数量
        """
        # 计算价格范围
        price_range = np.linspace(data.low.min(), data.high.max(), bins)
        volumes = np.zeros(bins-1)

        # 统计每个价格区间的成交量
        for i in range(len(data)):
            idx = np.searchsorted(price_range, data.close.iloc[i]) - 1
            if 0 <= idx < bins-1:
                volumes[idx] += data.volume.iloc[i]

        # 绘制水平直方图
        ax.barh(price_range[:-1], volumes, height=price_range[1]-price_range[0],
                alpha=0.3)

    @staticmethod
    def add_annotations(ax, points, texts):
        """添加图表标注

        Args:
            ax: matplotlib轴对象
            points: 标注点列表
            texts: 标注文本列表
        """
        for point, text in zip(points, texts):
            ax.annotate(text, xy=point, xytext=(10, 10),
                        textcoords='offset points',
                        bbox=dict(boxstyle='round,pad=0.5',
                                  fc='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->'))

    @staticmethod
    def create_correlation_matrix(fig, data_dict):
        """创建相关性矩阵图

        Args:
            fig: matplotlib图表对象
            data_dict: 数据字典
        """
        # 计算相关性矩阵
        corr_matrix = pd.DataFrame(data_dict).corr()

        # 创建热力图
        ax = fig.add_subplot(111)
        im = ax.imshow(corr_matrix, cmap='RdYlBu')

        # 添加颜色条
        fig.colorbar(im)

        # 设置标签
        ax.set_xticks(np.arange(len(corr_matrix.columns)))
        ax.set_yticks(np.arange(len(corr_matrix.columns)))
        ax.set_xticklabels(corr_matrix.columns)
        ax.set_yticklabels(corr_matrix.columns)

        # 旋转x轴标签
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

        # 添加数值标注
        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.3f}',
                               ha='center', va='center')

    @staticmethod
    def create_indicator_dashboard(fig, data):
        """创建指标仪表板

        Args:
            fig: matplotlib图表对象
            data: 数据
        """
        # 创建网格布局
        gs = fig.add_gridspec(3, 3)

        # K线图
        ax1 = fig.add_subplot(gs[0, :])
        ChartOptimizer.optimize_candlestick_chart(ax1, data)

        # RSI
        ax2 = fig.add_subplot(gs[1, 0])
        rsi = data.close.rolling(14).apply(lambda x: 100 - 100/(1 + x.mean()))
        ax2.plot(data.index, rsi)
        ax2.set_title('RSI')

        # MACD
        ax3 = fig.add_subplot(gs[1, 1])
        exp1 = data.close.ewm(span=12).mean()
        exp2 = data.close.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        ax3.plot(data.index, macd, label='MACD')
        ax3.plot(data.index, signal, label='Signal')
        ax3.set_title('MACD')

        # 成交量
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.bar(data.index, data.volume)
        ax4.set_title('Volume')

        # 布林带
        ax5 = fig.add_subplot(gs[2, 0])
        ChartOptimizer.add_technical_overlay(ax5, data, 'BOLL')
        ax5.set_title('Bollinger Bands')

        # 动量
        ax6 = fig.add_subplot(gs[2, 1])
        momentum = data.close - data.close.shift(10)
        ax6.plot(data.index, momentum)
        ax6.set_title('Momentum')

        # 成交量分布
        ax7 = fig.add_subplot(gs[2, 2])
        ChartOptimizer.create_volume_profile(ax7, data)
        ax7.set_title('Volume Profile')

        fig.tight_layout()

    @staticmethod
    def optimize_performance(fig):
        """优化图表性能

        Args:
            fig: matplotlib图表对象
        """
        # 减少绘制的数据点
        for ax in fig.axes:
            for line in ax.lines:
                data = line.get_data()
                if len(data[0]) > 1000:
                    # 使用抽样减少数据点
                    step = len(data[0]) // 1000
                    line.set_data(data[0][::step], data[1][::step])

        # 禁用不必要的交互功能
        for ax in fig.axes:
            ax.set_adjustable('datalim')

        # 优化内存使用
        fig.set_tight_layout(True)

        # 使用快速样式
        plt.style.use('fast')

    @staticmethod
    def create_chart_template(template_name: str) -> Dict:
        """创建图表模板

        Args:
            template_name: 模板名称

        Returns:
            template: 模板配置字典
        """
        templates = {
            'trading': {
                'figsize': (12, 8),
                'dpi': 100,
                'style': 'seaborn-v0_8-whitegrid',
                'layout': {
                    'price': {'height_ratios': 3},
                    'volume': {'height_ratios': 1},
                    'indicator': {'height_ratios': 1}
                }
            },
            'analysis': {
                'figsize': (15, 10),
                'dpi': 100,
                'style': 'seaborn-v0_8-whitegrid',
                'layout': {
                    'main': {'height_ratios': 2},
                    'sub1': {'height_ratios': 1},
                    'sub2': {'height_ratios': 1},
                    'sub3': {'height_ratios': 1}
                }
            },
            'dashboard': {
                'figsize': (16, 12),
                'dpi': 100,
                'style': 'seaborn-v0_8-whitegrid',
                'layout': {
                    'overview': {'grid': (2, 2)},
                    'details': {'grid': (3, 3)},
                    'summary': {'grid': (1, 3)}
                }
            }
        }

        return templates.get(template_name, templates['trading'])
