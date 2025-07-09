import numpy as np
import pandas as pd
import warnings
from core.indicator_service import calculate_indicator  # 使用新的指标计算服务


def add_basic_indicators(df):
    """
    添加基本技术指标

    参数:
        df: 输入DataFrame

    返回:
        DataFrame: 添加了技术指标的DataFrame
    """
    result = df.copy()

    # 计算移动平均线
    for window in [5, 10, 20, 50, 200]:
        ma_result = calculate_indicator('MA', result, {'timeperiod': window})
        if 'MA' in ma_result.columns:
            result[f'MA{window}'] = ma_result['MA']

    # 计算MACD
    macd_result = calculate_indicator('MACD', result, {
        'fastperiod': 12,
        'slowperiod': 26,
        'signalperiod': 9
    })
    if 'MACD' in macd_result.columns:
        result['macd'] = macd_result['MACD']
        result['signal_line'] = macd_result['MACDSignal']
        result['macd_hist'] = macd_result['MACDHist']

    # 计算RSI
    rsi_result = calculate_indicator('RSI', result, {'timeperiod': 14})
    if 'RSI' in rsi_result.columns:
        result['rsi'] = rsi_result['RSI']

    # 计算布林带
    bbands_result = calculate_indicator('BBANDS', result, {
        'timeperiod': 20,
        'nbdevup': 2.0,
        'nbdevdn': 2.0
    })
    if all(col in bbands_result.columns for col in ['BBUpper', 'BBMiddle', 'BBLower']):
        result['upper_band'] = bbands_result['BBUpper']
        result['lower_band'] = bbands_result['BBLower']

    # 计算变动率指标
    result['roc_5'] = result['close'].pct_change(periods=5) * 100
    result['roc_10'] = result['close'].pct_change(periods=10) * 100
    result['roc_20'] = result['close'].pct_change(periods=20) * 100

    # 计算价格与移动平均线偏离率
    if 'MA5' in result.columns:
        result['bias_5'] = (result['close'] / result['MA5'] - 1) * 100
    if 'MA10' in result.columns:
        result['bias_10'] = (result['close'] / result['MA10'] - 1) * 100
    if 'MA20' in result.columns:
        result['bias_20'] = (result['close'] / result['MA20'] - 1) * 100

    # 计算强弱指标KDJ
    kdj_result = calculate_indicator('KDJ', result, {
        'fastk_period': 9,
        'slowk_period': 3,
        'slowd_period': 3
    })
    if all(col in kdj_result.columns for col in ['K', 'D', 'J']):
        result['k_percent'] = kdj_result['K']
        result['k'] = kdj_result['K']
        result['d'] = kdj_result['D']
        result['j'] = kdj_result['J']

    # 计算成交量指标
    if 'volume' in result.columns:
        result['volume_ma5'] = result['volume'].rolling(window=5).mean()
        result['volume_ma10'] = result['volume'].rolling(window=10).mean()
        result['volume_ratio'] = result['volume'] / result['volume_ma5']

    # 填充NaN值
    result = result.fillna(method='bfill').fillna(method='ffill').fillna(0)

    return result


def calculate_base_indicators(df):
    """
    计算基础技术指标

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了基础指标的DataFrame
    """
    # 确保索引已排序
    df = df.sort_index()

    # 计算移动平均线
    for period in [5, 10, 20, 60]:
        ma_result = calculate_indicator('MA', df, {'timeperiod': period})
        if 'MA' in ma_result.columns:
            df[f'MA{period}'] = ma_result['MA']

    # 计算量价指标
    df['volume_ma5'] = df['volume'].rolling(window=5).mean()
    df['volume_ma10'] = df['volume'].rolling(window=10).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma5']

    # 计算价格相对位置
    df['price_position'] = (df['close'] - df['close'].rolling(window=20).min()) / \
        (df['close'].rolling(window=20).max() -
         df['close'].rolling(window=20).min())

    # 添加简单的价格变动指标
    df['price_change'] = df['close'].pct_change()
    df['price_change_5d'] = df['close'].pct_change(5)
    df['price_change_10d'] = df['close'].pct_change(10)
    df['price_change_20d'] = df['close'].pct_change(20)

    # 添加波动率指标
    df['volatility_5d'] = df['close'].pct_change().rolling(
        window=5).std() * np.sqrt(5)
    df['volatility_10d'] = df['close'].pct_change().rolling(
        window=10).std() * np.sqrt(10)
    df['volatility_20d'] = df['close'].pct_change().rolling(
        window=20).std() * np.sqrt(20)

    # 添加简单的量价关系指标
    df['volume_price_corr_5d'] = df['close'].rolling(
        window=5).corr(df['volume'])
    df['volume_price_corr_10d'] = df['close'].rolling(
        window=10).corr(df['volume'])

    # 添加布林带指标
    bbands_result = calculate_indicator('BBANDS', df, {
        'timeperiod': 20,
        'nbdevup': 2.0,
        'nbdevdn': 2.0
    })
    if all(col in bbands_result.columns for col in ['BBUpper', 'BBMiddle', 'BBLower']):
        df['bbands_middle'] = bbands_result['BBMiddle']
        df['bbands_upper'] = bbands_result['BBUpper']
        df['bbands_lower'] = bbands_result['BBLower']
        df['bbands_width'] = (df['bbands_upper'] - df['bbands_lower']) / df['bbands_middle']

    # 添加移动平均线交叉信号
    if all(col in df.columns for col in ['MA5', 'MA10', 'MA20']):
        df['ma5_cross_ma10'] = ((df['MA5'] > df['MA10']) & (df['MA5'].shift(1) <= df['MA10'].shift(1))).astype(int) - \
                               ((df['MA5'] < df['MA10']) & (df['MA5'].shift(
                                   1) >= df['MA10'].shift(1))).astype(int)

        df['ma5_cross_ma20'] = ((df['MA5'] > df['MA20']) & (df['MA5'].shift(1) <= df['MA20'].shift(1))).astype(int) - \
                               ((df['MA5'] < df['MA20']) & (df['MA5'].shift(
                                   1) >= df['MA20'].shift(1))).astype(int)

    # 添加价格突破指标
    if 'MA20' in df.columns:
        df['price_above_ma20'] = (df['close'] > df['MA20']).astype(int)
    if 'MA60' in df.columns:
        df['price_above_ma60'] = (df['close'] > df['MA60']).astype(int)

    # 添加量能指标
    df['volume_surge'] = (df['volume'] > 1.5 * df['volume_ma5']).astype(int)
    df['volume_shrink'] = (df['volume'] < 0.5 * df['volume_ma5']).astype(int)

    # 计算MACD
    macd_result = calculate_indicator('MACD', df, {
        'fastperiod': 12,
        'slowperiod': 26,
        'signalperiod': 9
    })
    if all(col in macd_result.columns for col in ['MACD', 'MACDSignal', 'MACDHist']):
        df['macd'] = macd_result['MACD']
        df['signal_line'] = macd_result['MACDSignal']
        df['macd_hist'] = macd_result['MACDHist']

    # 添加ATR指标
    atr_result = calculate_indicator('ATR', df, {'timeperiod': 14})
    if 'ATR' in atr_result.columns:
        df['atr'] = atr_result['ATR']

    # 添加OBV指标
    obv_result = calculate_indicator('OBV', df, {})
    if 'OBV' in obv_result.columns:
        df['obv'] = obv_result['OBV']

    # 添加CCI指标
    cci_result = calculate_indicator('CCI', df, {'timeperiod': 14})
    if 'CCI' in cci_result.columns:
        df['cci'] = cci_result['CCI']

    return df


def create_advanced_nonlinear_features(df):
    """
    创建高级非线性特征

    参数:
        df: 输入DataFrame，包含已计算的基础技术指标

    返回:
        DataFrame: 添加了高级非线性特征的DataFrame
    """
    # 价格波动率相关特征
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['log_return_volatility'] = df['log_return'].rolling(window=10).std()

    # 价格与成交量关联特征
    df['price_volume_corr'] = df['close'].rolling(window=20).corr(df['volume'])

    # 指标交叉特征
    if all(col in df.columns for col in ['macd', 'signal_line']):
        df['macd_signal_cross'] = ((df['macd'] > df['signal_line']) &
                                   (df['macd'].shift(1) <= df['signal_line'].shift(1))).astype(int) - \
            ((df['macd'] < df['signal_line']) &
             (df['macd'].shift(1) >= df['signal_line'].shift(1))).astype(int)

    # 价格动量和波动率比率
    df['momentum_volatility_ratio'] = df['price_change_10d'] / \
        (df['volatility_10d'] + 1e-10)  # 避免除以零

    # RSI超买超卖特征
    if 'rsi' in df.columns:
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)

    # 布林带宽度变化率
    if 'bbands_width' in df.columns:
        df['bbands_width_change'] = df['bbands_width'].pct_change(5)

    # 价格与布林带位置关系
    if all(col in df.columns for col in ['bbands_upper', 'bbands_lower', 'bbands_middle']):
        df['price_bb_position'] = (df['close'] - df['bbands_lower']) / \
            (df['bbands_upper'] - df['bbands_lower'] + 1e-10)

    # 指标组合特征
    if all(col in df.columns for col in ['rsi', 'macd']):
        df['rsi_macd_combined'] = df['rsi'] * df['macd']

    # 价格趋势强度
    if 'MA20' in df.columns:
        df['trend_strength'] = np.abs(
            df['close'] / df['MA20'] - 1) * np.sign(df['close'] - df['MA20'])

    # 填充NaN值
    df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)

    return df


def create_time_series_features(df):
    """
    创建时间序列特征

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了时间序列特征的DataFrame
    """
    # 确保索引是日期类型
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            # 尝试将索引转换为日期类型
            df.index = pd.to_datetime(df.index)
        except:
            # 如果无法转换，则跳过时间特征创建
            warnings.warn("无法将索引转换为日期类型，跳过时间特征创建")
            return df

    # 提取日期特征
    df['day_of_week'] = df.index.dayofweek
    df['day_of_month'] = df.index.day
    df['month'] = df.index.month
    df['quarter'] = df.index.quarter
    df['year'] = df.index.year
    df['is_month_start'] = df.index.is_month_start.astype(int)
    df['is_month_end'] = df.index.is_month_end.astype(int)
    df['is_quarter_start'] = df.index.is_quarter_start.astype(int)
    df['is_quarter_end'] = df.index.is_quarter_end.astype(int)
    df['is_year_start'] = df.index.is_year_start.astype(int)
    df['is_year_end'] = df.index.is_year_end.astype(int)

    # 创建周期性特征
    df['sin_day_of_week'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['cos_day_of_week'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['sin_day_of_month'] = np.sin(2 * np.pi * df['day_of_month'] / 31)
    df['cos_day_of_month'] = np.cos(2 * np.pi * df['day_of_month'] / 31)
    df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
    df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)

    return df
