import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from loguru import logger


def detect_market_regime(df, price_col='close', window=200, threshold=0.1, regime_window=20):
    """
    检测市场状态（牛市、熊市或震荡市）

    参数:
        df: DataFrame，含有价格数据
        price_col: str，价格列名
        window: int，用于计算长期趋势的窗口大小
        threshold: float，判断牛熊市的阈值
        regime_window: int，用于平滑市场状态的窗口大小

    返回:
        DataFrame: 包含市场状态的DataFrame
    """
    # 复制数据，避免修改原始数据
    result_df = df.copy()

    # 计算移动平均线
    result_df['ma_long'] = result_df[price_col].rolling(window=window).mean()

    # 计算价格相对于长期均线的偏离程度
    result_df['price_dev'] = (result_df[price_col] / result_df['ma_long'] - 1)

    # 计算趋势强度（斜率）
    result_df['slope'] = result_df['ma_long'].rolling(window=20).apply(
        lambda x: stats.linregress(np.arange(len(x)), x)[0] / x.mean(),
        raw=False
    ).fillna(0)

    # 确定原始市场状态
    # 1: 牛市, -1: 熊市, 0: 震荡市
    result_df['raw_market_state'] = 0

    # 牛市条件：价格高于长期均线且斜率为正
    bull_condition = (result_df['price_dev'] > threshold) & (
        result_df['slope'] > 0)
    result_df.loc[bull_condition, 'raw_market_state'] = 1

    # 熊市条件：价格低于长期均线且斜率为负
    bear_condition = (result_df['price_dev'] < -
                      threshold) & (result_df['slope'] < 0)
    result_df.loc[bear_condition, 'raw_market_state'] = -1

    # 震荡市
    # 默认已经设置为0

    # 平滑市场状态，避免频繁切换
    result_df['market_state'] = result_df['raw_market_state'].rolling(
        window=regime_window
    ).mean().round(0).astype(int)

    # 填充NaN值
    result_df['market_state'] = result_df['market_state'].fillna(0)

    return result_df


def detect_market_volatility(df, price_col='close', window=20, high_vol_percentile=0.8):
    """
    检测市场波动率状态

    参数:
        df: DataFrame，含有价格数据
        price_col: str，价格列名
        window: int，计算波动率的窗口
        high_vol_percentile: float，高波动率的百分位数阈值

    返回:
        DataFrame: 包含波动率状态的DataFrame
    """
    # 复制数据
    result_df = df.copy()

    # 计算日收益率
    result_df['returns'] = result_df[price_col].pct_change()

    # 计算滚动波动率（标准差）
    result_df['volatility'] = result_df['returns'].rolling(window=window).std()

    # 保存波动率列名以便于其他函数引用
    vol_col = f'volatility_{window}d'
    result_df[vol_col] = result_df['volatility']

    # 计算波动率的历史分位数（使用较长的回溯期）
    lookback = min(len(result_df), 252)  # 使用约一年的数据
    result_df['vol_percentile'] = result_df['volatility'].rolling(window=lookback).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1]
    ).fillna(0.5)

    # 确定波动率状态
    # 1: 高波动率, 0: 正常波动率
    result_df['high_volatility'] = 0
    result_df.loc[result_df['vol_percentile'] >
                  high_vol_percentile, 'high_volatility'] = 1

    return result_df


def identify_trend_reversal(df, price_col='close', short_window=20, long_window=50, signal_threshold=0.02):
    """
    识别市场趋势反转点

    参数:
        df: DataFrame，含有价格数据
        price_col: str，价格列名
        short_window: int，短期移动平均线窗口
        long_window: int，长期移动平均线窗口
        signal_threshold: float，确认反转信号的阈值

    返回:
        DataFrame: 包含趋势反转信号的DataFrame
    """
    # 复制数据
    result_df = df.copy()

    # 计算短期和长期移动平均线
    result_df['short_ma'] = result_df[price_col].rolling(
        window=short_window).mean()
    result_df['long_ma'] = result_df[price_col].rolling(
        window=long_window).mean()

    # 计算相对强度指标 (RSI)
    delta = result_df[price_col].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    # 避免除零错误
    avg_loss_nonzero = avg_loss.replace(0, 1e-10)
    rs = avg_gain / avg_loss_nonzero
    result_df['rsi'] = 100 - (100 / (1 + rs))

    # 初始化趋势反转信号
    result_df['trend_reversal'] = 0  # 0: 无信号, 1: 看涨反转, -1: 看跌反转

    # 找出潜在的趋势反转点
    for i in range(long_window, len(result_df)):
        # 看涨反转条件
        bullish_ma_crossover = (result_df['short_ma'].iloc[i-1] <= result_df['long_ma'].iloc[i-1]) and \
            (result_df['short_ma'].iloc[i] > result_df['long_ma'].iloc[i])

        rsi_oversold = result_df['rsi'].iloc[i -
                                             1] < 30 and result_df['rsi'].iloc[i] > 30

        price_higher_low = all(
            result_df[price_col].iloc[i-3:i] > result_df[price_col].iloc[i-4])

        # 看跌反转条件
        bearish_ma_crossover = (result_df['short_ma'].iloc[i-1] >= result_df['long_ma'].iloc[i-1]) and \
            (result_df['short_ma'].iloc[i] < result_df['long_ma'].iloc[i])

        rsi_overbought = result_df['rsi'].iloc[i -
                                               1] > 70 and result_df['rsi'].iloc[i] < 70

        price_lower_high = all(
            result_df[price_col].iloc[i-3:i] < result_df[price_col].iloc[i-4])

        # 判断看涨反转
        if (bullish_ma_crossover or rsi_oversold) and price_higher_low:
            result_df.loc[result_df.index[i], 'trend_reversal'] = 1

        # 判断看跌反转
        if (bearish_ma_crossover or rsi_overbought) and price_lower_high:
            result_df.loc[result_df.index[i], 'trend_reversal'] = -1

    # 确认反转信号
    # 看涨反转后价格需要上涨超过阈值才确认
    for i in range(1, len(result_df)):
        if result_df['trend_reversal'].iloc[i-1] == 1:
            # 检查后续5个交易日价格是否上涨超过阈值
            if i+5 < len(result_df):
                future_return = result_df[price_col].iloc[i +
                                                          5] / result_df[price_col].iloc[i] - 1
                if future_return < signal_threshold:
                    result_df.loc[result_df.index[i-1], 'trend_reversal'] = 0

        # 看跌反转后价格需要下跌超过阈值才确认
        elif result_df['trend_reversal'].iloc[i-1] == -1:
            # 检查后续5个交易日价格是否下跌超过阈值
            if i+5 < len(result_df):
                future_return = result_df[price_col].iloc[i +
                                                          5] / result_df[price_col].iloc[i] - 1
                if future_return > -signal_threshold:
                    result_df.loc[result_df.index[i-1], 'trend_reversal'] = 0

    return result_df


def plot_market_regimes(df, price_col='close', figsize=(15, 10)):
    """
    绘制市场状态和价格走势

    参数:
        df: DataFrame，包含价格和市场状态数据
        price_col: str，价格列名
        figsize: tuple，图形大小
    """
    if 'market_state' not in df.columns:
        logger.info("DataFrame中缺少'market_state'列，请先运行detect_market_regime函数")
        return

    plt.figure(figsize=figsize)

    # 创建三个子图
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=figsize, sharex=True,
                                        gridspec_kw={'height_ratios': [3, 1, 1]})

    # 绘制价格和移动平均线
    ax1.plot(df.index, df[price_col], label=price_col, color='blue')

    if 'ma_long' in df.columns:
        ax1.plot(df.index, df['ma_long'],
                 label='Long MA', color='orange', alpha=0.7)

    if 'short_ma' in df.columns and 'long_ma' in df.columns:
        ax1.plot(df.index, df['short_ma'],
                 label='Short MA', color='green', alpha=0.7)
        ax1.plot(df.index, df['long_ma'],
                 label='Long MA', color='red', alpha=0.7)

    # 标记牛市区域
    bull_periods = df[df['market_state'] == 1]
    for i in range(len(bull_periods)):
        if i == 0 or bull_periods.index[i] > bull_periods.index[i-1] + pd.Timedelta(days=1):
            start_idx = bull_periods.index[i]

            # 寻找这段牛市的结束
            j = i
            while j < len(bull_periods) - 1 and bull_periods.index[j+1] == bull_periods.index[j] + pd.Timedelta(days=1):
                j += 1

            end_idx = bull_periods.index[j]

            # 绘制牛市区域
            ax1.axvspan(start_idx, end_idx, alpha=0.2, color='green')

    # 标记熊市区域
    bear_periods = df[df['market_state'] == -1]
    for i in range(len(bear_periods)):
        if i == 0 or bear_periods.index[i] > bear_periods.index[i-1] + pd.Timedelta(days=1):
            start_idx = bear_periods.index[i]

            # 寻找这段熊市的结束
            j = i
            while j < len(bear_periods) - 1 and bear_periods.index[j+1] == bear_periods.index[j] + pd.Timedelta(days=1):
                j += 1

            end_idx = bear_periods.index[j]

            # 绘制熊市区域
            ax1.axvspan(start_idx, end_idx, alpha=0.2, color='red')

    # 标记趋势反转点
    if 'trend_reversal' in df.columns:
        bullish_reversals = df[df['trend_reversal'] == 1]
        bearish_reversals = df[df['trend_reversal'] == -1]

        ax1.scatter(bullish_reversals.index, bullish_reversals[price_col],
                    marker='^', color='lime', s=100, label='Bullish Reversal')
        ax1.scatter(bearish_reversals.index, bearish_reversals[price_col],
                    marker='v', color='darkred', s=100, label='Bearish Reversal')

    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True)

    # 绘制市场状态
    ax2.plot(df.index, df['market_state'],
             color='purple', label='Market State')
    ax2.axhline(y=0, color='gray', linestyle='--')
    ax2.set_ylabel('Market State\n(1=Bull, -1=Bear, 0=Sideways)')
    ax2.legend(loc='upper left')
    ax2.grid(True)

    # 绘制波动率
    if 'volatility' in df.columns and 'high_volatility' in df.columns:
        ax3.plot(df.index, df['volatility'],
                 color='orange', label='Volatility')

        high_vol_periods = df[df['high_volatility'] == 1]
        for i in range(len(high_vol_periods)):
            if i == 0 or high_vol_periods.index[i] > high_vol_periods.index[i-1] + pd.Timedelta(days=1):
                start_idx = high_vol_periods.index[i]

                # 寻找这段高波动率的结束
                j = i
                while j < len(high_vol_periods) - 1 and high_vol_periods.index[j+1] == high_vol_periods.index[j] + pd.Timedelta(days=1):
                    j += 1

                end_idx = high_vol_periods.index[j]

                # 绘制高波动率区域
                ax3.axvspan(start_idx, end_idx, alpha=0.2, color='orange')

        ax3.set_ylabel('Volatility')
        ax3.legend(loc='upper left')
        ax3.grid(True)

    plt.tight_layout()
    plt.xlabel('Date')
    plt.suptitle('Market Regimes, States and Volatility Analysis', fontsize=16)
    plt.subplots_adjust(top=0.95)

    plt.show()

    return plt.gcf()  # 返回图形对象以便保存
