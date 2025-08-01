import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def find_peaks_and_troughs(data: pd.Series, prominence: float = 0.02, width: int = 3):
    """
    在时间序列数据中寻找显著的波峰和波谷。

    这个函数是复杂图表模式识别的基础。通过调整参数，可以适应不同波动性的数据。

    :param data: pandas Series, 通常是收盘价或高低价的均值。
    :param prominence: float, 波峰/波谷的突起程度。值越大，找到的峰谷越少，但越显著。
                       这可以理解为一个峰/谷必须比周围的邻居高/低多少（百分比）。
    :param width: int, 峰/谷的最小宽度（单位：数据点）。
    :return: tuple, (peaks, troughs)，两个都是pandas DataFrame，
             包含 'index' 和 'price' 列，分别对应峰/谷在原始数据中的索引和价格。
    """
    # 确保数据是numpy数组
    series_data = data.to_numpy()

    # 突起程度是一个关键参数，我们根据数据的波动范围来动态计算
    # 使用传入的百分比乘以价格范围
    required_prominence = (np.nanmax(series_data) - np.nanmin(series_data)) * prominence

    # 使用scipy.signal.find_peaks寻找波峰
    # prominence参数确保我们只找到重要的波峰
    peak_indices, _ = find_peaks(series_data, prominence=required_prominence, width=width)

    # 寻找波谷，可以通过将数据取反，然后再次使用find_peaks来实现
    trough_indices, _ = find_peaks(-series_data, prominence=required_prominence, width=width)

    # 将索引和价格存入DataFrame
    peaks_df = pd.DataFrame({
        'index': data.index[peak_indices],
        'price': series_data[peak_indices]
    }).set_index('index')

    troughs_df = pd.DataFrame({
        'index': data.index[trough_indices],
        'price': series_data[trough_indices]
    }).set_index('index')

    return peaks_df, troughs_df


if __name__ == '__main__':
    # 为了验证函数的有效性，我们创建一个示例并运行
    print("正在执行 `find_peaks_and_troughs` 函数的单元测试...")

    # 1. 创建一段合成的、包含明显趋势和峰谷的K线数据
    dates = pd.to_datetime(pd.date_range(start='2023-01-01', periods=100))
    # 创建一个类似W底 + M顶的走势
    prices = np.array([
        10.0, 10.2, 10.5, 10.3, 10.1,  # 初始
        9.5, 9.2, 9.0, 9.3, 9.6,      # 第一个谷
        10.0, 10.5, 11.0, 10.8, 10.6,  # 反弹形成颈线点
        9.4, 9.1, 8.9, 9.2, 9.5,      # 第二个谷 (W底)
        10.0, 10.5, 11.0, 11.5, 12.0,  # 上涨
        12.5, 13.0, 12.8, 12.6,       # 第一个顶
        12.0, 11.8, 12.2, 12.5,       # 回调
        13.1, 13.2, 12.9, 12.7,       # 第二个顶 (M顶)
        12.0, 11.5, 11.0, 10.5, 10.0  # 下跌
    ])
    # 填充剩余数据
    full_prices = np.concatenate([prices, np.linspace(10.0, 12.0, 100 - len(prices))])
    close_prices = pd.Series(full_prices, index=dates)

    # 2. 调用函数
    # 优化：降低prominence参数，使其对局部峰谷更敏感
    peaks, troughs = find_peaks_and_troughs(close_prices, prominence=0.01, width=1)

    # 3. 打印结果进行验证
    print("\n合成K线数据预览:")
    print(close_prices.head(10))

    print("\n找到的波峰 (Peaks):")
    if not peaks.empty:
        print(peaks)
    else:
        print("未找到显著波峰。")

    print("\n找到的波谷 (Troughs):")
    if not troughs.empty:
        print(troughs)
    else:
        print("未找到显著波谷。")

    # 4. 可视化（如果可以）
    try:
        import matplotlib.pyplot as plt
        print("\n正在生成可视化图表以供验证...")
        plt.figure(figsize=(15, 7))
        plt.plot(close_prices, label='Close Price', color='blue', alpha=0.6)
        plt.scatter(peaks.index, peaks['price'], color='red', s=100, marker='^', label='Peaks')
        plt.scatter(troughs.index, troughs['price'], color='green', s=100, marker='v', label='Troughs')
        plt.title('Peaks and Troughs Detection Test')
        plt.legend()
        plt.grid(True)
        # 保存到文件而不是显示
        output_path = 'docs/peaks_troughs_test.png'
        plt.savefig(output_path)
        print(f"测试图表已保存到: {output_path}")

    except ImportError:
        print("\nMatplotlib未安装，无法进行可视化验证。请运行 `pip install matplotlib`。")

    print("\n单元测试执行完毕。")
