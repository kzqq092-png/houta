from matplotlib.patches import Rectangle


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
