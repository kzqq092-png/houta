"""
高级技术指标计算模块
提供各种高级技术指标的计算功能
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.data_preprocessing import kdata_preprocess as _kdata_preprocess, validate_kdata
from core.indicator_service import calculate_indicator  # 使用新的指标计算服务


def calculate_advanced_indicators(df):
    """
    计算高级技术指标

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了高级技术指标的DataFrame
    """
    df = _kdata_preprocess(df, context="高级指标")
    if df is None or df.empty:
        return df

    # MACD
    macd_result = calculate_indicator('MACD', df, {
        'fastperiod': 12,
        'slowperiod': 26,
        'signalperiod': 9
    })
    if all(col in macd_result.columns for col in ['MACD', 'MACDSignal', 'MACDHist']):
        df['macd'] = macd_result['MACD']
        df['signal'] = macd_result['MACDSignal']
        df['macd_hist'] = macd_result['MACDHist']

    # RSI
    rsi_result = calculate_indicator('RSI', df, {'timeperiod': 14})
    if 'RSI' in rsi_result.columns:
        df['rsi'] = rsi_result['RSI']

    # Bollinger Bands
    bbands_result = calculate_indicator('BBANDS', df, {
        'timeperiod': 20,
        'nbdevup': 2.0,
        'nbdevdn': 2.0
    })
    if all(col in bbands_result.columns for col in ['BBUpper', 'BBMiddle', 'BBLower']):
        df['bb_middle'] = bbands_result['BBMiddle']
        df['bb_upper'] = bbands_result['BBUpper']
        df['bb_lower'] = bbands_result['BBLower']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

    # ATR
    atr_result = calculate_indicator('ATR', df, {'timeperiod': 14})
    if 'ATR' in atr_result.columns:
        df['atr'] = atr_result['ATR']

    # Stochastic Oscillator (KDJ)
    kdj_result = calculate_indicator('KDJ', df, {
        'fastk_period': 9,
        'slowk_period': 3,
        'slowd_period': 3
    })
    if all(col in kdj_result.columns for col in ['K', 'D', 'J']):
        df['stoch_k'] = kdj_result['K']
        df['stoch_d'] = kdj_result['D']
        df['kdj_k'] = kdj_result['K']
        df['kdj_d'] = kdj_result['D']
        df['kdj_j'] = kdj_result['J']

    # Chaikin Money Flow
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    clv = clv.replace([np.inf, -np.inf], np.nan).fillna(0)
    df['cmf'] = (clv * df['volume']).rolling(window=20).sum() / df['volume'].rolling(window=20).sum()

    # OBV (On-Balance Volume)
    obv_result = calculate_indicator('OBV', df, {})
    if 'OBV' in obv_result.columns:
        df['obv'] = obv_result['OBV']
    else:
        df['daily_ret'] = df['close'].pct_change()
        df['direction'] = np.where(df['daily_ret'] > 0, 1, np.where(df['daily_ret'] < 0, -1, 0))
        df['direction_volume'] = df['direction'] * df['volume']
        df['obv'] = df['direction_volume'].cumsum()

    # Williams %R
    willr_result = calculate_indicator('WILLR', df, {'timeperiod': 14})
    if 'WILLR' in willr_result.columns:
        df['williams_r'] = willr_result['WILLR']
    else:
        # 如果TA-Lib不可用，使用自定义计算
        high_14 = df['high'].rolling(window=14).max()
        low_14 = df['low'].rolling(window=14).min()
        df['williams_r'] = -100 * (high_14 - df['close']) / (high_14 - low_14)

    # TRIX
    trix_result = calculate_indicator('TRIX', df, {'timeperiod': 9})
    if 'TRIX' in trix_result.columns:
        df['trix'] = trix_result['TRIX']
    else:
        # 如果TA-Lib不可用，使用自定义计算
        ex1 = df['close'].ewm(span=9, adjust=False).mean()
        ex2 = ex1.ewm(span=9, adjust=False).mean()
        ex3 = ex2.ewm(span=9, adjust=False).mean()
        df['trix'] = 100 * (ex3.pct_change(1))

    # CCI (Commodity Channel Index)
    cci_result = calculate_indicator('CCI', df, {'timeperiod': 20})
    if 'CCI' in cci_result.columns:
        df['cci'] = cci_result['CCI']

    # ROC (Rate of Change)
    roc_result = calculate_indicator('ROC', df, {'timeperiod': 10})
    if 'ROC' in roc_result.columns:
        df['roc'] = roc_result['ROC']
    else:
        df['roc'] = 100 * ((df['close'] / df['close'].shift(10)) - 1)

    # Awesome Oscillator
    median_price = (df['high'] + df['low']) / 2
    ao1 = median_price.rolling(window=5).mean()
    ao2 = median_price.rolling(window=34).mean()
    df['awesome_oscillator'] = ao1 - ao2

    # MFI (Money Flow Index)
    mfi_result = calculate_indicator('MFI', df, {'timeperiod': 14})
    if 'MFI' in mfi_result.columns:
        df['mfi'] = mfi_result['MFI']
    else:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']

        # 计算Positive和Negative Money Flow
        money_flow_positive = raw_money_flow.where(typical_price > typical_price.shift(1), 0)
        money_flow_negative = raw_money_flow.where(typical_price < typical_price.shift(1), 0)

        # 计算14天的money flow ratio
        pos_flow_sum = money_flow_positive.rolling(window=14).sum()
        neg_flow_sum = money_flow_negative.rolling(window=14).sum()

        # 防止除以零
        neg_flow_sum = neg_flow_sum.replace(0, 1e-10)
        money_flow_ratio = pos_flow_sum / neg_flow_sum

        # 计算MFI
        df['mfi'] = 100 - (100 / (1 + money_flow_ratio))

    return df


ALL_PATTERN_TYPES = [
    "头肩顶", "头肩底", "双顶", "双底", "三角形", "锤子线", "倒锤头", "吞没形态", "启明星", "黄昏星", "三白兵", "三只乌鸦", "十字星", "流星线", "射击之星"
]


def create_pattern_recognition_features(df):
    """
    创建K线形态识别特征

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了K线形态特征的DataFrame
    """
    df = _kdata_preprocess(df, context="形态特征")
    if df is None or df.empty:
        return df

    # 确保有必要的列
    required_cols = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_cols):
        print("错误: 缺少必要的列 (open, high, low, close)")
        return df

    # 复制DataFrame以避免修改原始数据
    df_new = df.copy()

    # 计算各部分的大小
    df_new['body_size'] = np.abs(df_new['close'] - df_new['open'])
    df_new['upper_shadow'] = df_new['high'] - np.maximum(df_new['open'], df_new['close'])
    df_new['lower_shadow'] = np.minimum(df_new['open'], df_new['close']) - df_new['low']
    df_new['total_range'] = df_new['high'] - df_new['low']

    # 计算相对大小
    df_new['rel_body_size'] = df_new['body_size'] / df_new['total_range']
    df_new['rel_upper_shadow'] = df_new['upper_shadow'] / df_new['total_range']
    df_new['rel_lower_shadow'] = df_new['lower_shadow'] / df_new['total_range']

    # 替换可能的NaN（当极差为0时）
    df_new.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_new.fillna(0, inplace=True)

    # 使用TA-Lib的烛台模式识别功能
    # 锤子线和上吊线
    hammer_result = calculate_indicator('CDLHAMMER', df_new, {})
    if 'CDLHAMMER' in hammer_result.columns:
        df_new['is_hammer'] = (hammer_result['CDLHAMMER'] != 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['is_hammer'] = ((df_new['rel_body_size'] < 0.3) &
                               (df_new['rel_upper_shadow'] < 0.1) &
                               (df_new['rel_lower_shadow'] > 0.6)).astype(int)

    # 十字星
    doji_result = calculate_indicator('CDLDOJI', df_new, {})
    if 'CDLDOJI' in doji_result.columns:
        df_new['is_doji'] = (doji_result['CDLDOJI'] != 0).astype(int)
    else:
        df_new['is_doji'] = (df_new['rel_body_size'] < 0.1).astype(int)

    # 吞没形态 (看跌吞没)
    bearish_engulfing_result = calculate_indicator('CDLENGULFING', df_new, {})
    if 'CDLENGULFING' in bearish_engulfing_result.columns:
        df_new['bearish_engulfing'] = (bearish_engulfing_result['CDLENGULFING'] < 0).astype(int)
        df_new['bullish_engulfing'] = (bearish_engulfing_result['CDLENGULFING'] > 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['bearish_engulfing'] = ((df_new['open'] > df_new['close'].shift(1)) &
                                       (df_new['close'] < df_new['open'].shift(1)) &
                                       (df_new['open'] > df_new['open'].shift(1)) &
                                       (df_new['close'] < df_new['close'].shift(1))).astype(int)

        # 吞没形态 (看涨吞没)
        df_new['bullish_engulfing'] = ((df_new['open'] < df_new['close'].shift(1)) &
                                       (df_new['close'] > df_new['open'].shift(1)) &
                                       (df_new['open'] < df_new['open'].shift(1)) &
                                       (df_new['close'] > df_new['close'].shift(1))).astype(int)

    # 启明星
    morning_star_result = calculate_indicator('CDLMORNINGSTAR', df_new, {})
    if 'CDLMORNINGSTAR' in morning_star_result.columns:
        df_new['morning_star'] = (morning_star_result['CDLMORNINGSTAR'] != 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['morning_star'] = ((df_new['close'].shift(2) < df_new['open'].shift(2)) &  # 第一日阴线
                                  (np.abs(df_new['close'].shift(1) - df_new['open'].shift(1)) <
                                   df_new['body_size'].shift(2) * 0.3) &  # 第二日小实体
                                  (df_new['close'].shift(1) < df_new['close'].shift(2)) &  # 第二日收盘价低于第一日
                                  (df_new['close'] > df_new['open']) &  # 第三日阳线
                                  (df_new['close'] > (df_new['open'].shift(2) + df_new['close'].shift(2)) / 2)  # 第三日收盘价回补第一日部分
                                  ).astype(int)

    # 黄昏星
    evening_star_result = calculate_indicator('CDLEVENINGSTAR', df_new, {})
    if 'CDLEVENINGSTAR' in evening_star_result.columns:
        df_new['evening_star'] = (evening_star_result['CDLEVENINGSTAR'] != 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['evening_star'] = ((df_new['close'].shift(2) > df_new['open'].shift(2)) &  # 第一日阳线
                                  (np.abs(df_new['close'].shift(1) - df_new['open'].shift(1)) <
                                   df_new['body_size'].shift(2) * 0.3) &  # 第二日小实体
                                  (df_new['close'].shift(1) > df_new['close'].shift(2)) &  # 第二日收盘价高于第一日
                                  (df_new['close'] < df_new['open']) &  # 第三日阴线
                                  (df_new['close'] < (df_new['open'].shift(2) + df_new['close'].shift(2)) / 2)  # 第三日收盘价回补第一日部分
                                  ).astype(int)

    # 三白兵
    three_white_soldiers_result = calculate_indicator('CDL3WHITESOLDIERS', df_new, {})
    if 'CDL3WHITESOLDIERS' in three_white_soldiers_result.columns:
        df_new['three_white_soldiers'] = (three_white_soldiers_result['CDL3WHITESOLDIERS'] != 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['three_white_soldiers'] = ((df_new['close'] > df_new['open']) &  # 今日阳线
                                          (df_new['close'].shift(1) > df_new['open'].shift(1)) &  # 昨日阳线
                                          (df_new['close'].shift(2) > df_new['open'].shift(2)) &  # 前日阳线
                                          (df_new['close'] > df_new['close'].shift(1)) &  # 今日收盘价高于昨日
                                          (df_new['close'].shift(1) > df_new['close'].shift(2)) &  # 昨日收盘价高于前日
                                          (df_new['open'] > df_new['open'].shift(1)) &  # 今日开盘价高于昨日
                                          (df_new['open'].shift(1) > df_new['open'].shift(2))  # 昨日开盘价高于前日
                                          ).astype(int)

    # 三只乌鸦
    three_black_crows_result = calculate_indicator('CDL3BLACKCROWS', df_new, {})
    if 'CDL3BLACKCROWS' in three_black_crows_result.columns:
        df_new['three_black_crows'] = (three_black_crows_result['CDL3BLACKCROWS'] != 0).astype(int)
    else:
        # 如果TA-Lib不可用，使用自定义计算
        df_new['three_black_crows'] = ((df_new['close'] < df_new['open']) &  # 今日阴线
                                       (df_new['close'].shift(1) < df_new['open'].shift(1)) &  # 昨日阴线
                                       (df_new['close'].shift(2) < df_new['open'].shift(2)) &  # 前日阴线
                                       (df_new['close'] < df_new['close'].shift(1)) &  # 今日收盘价低于昨日
                                       (df_new['close'].shift(1) < df_new['close'].shift(2)) &  # 昨日收盘价低于前日
                                       (df_new['open'] < df_new['open'].shift(1)) &  # 今日开盘价低于昨日
                                       (df_new['open'].shift(1) < df_new['open'].shift(2))  # 昨日开盘价低于前日
                                       ).astype(int)

    return df_new


def create_market_regime_features(df):
    """
    创建市场状态特征

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了市场状态特征的DataFrame
    """
    df = _kdata_preprocess(df, context="市场状态")
    if df is None or df.empty:
        return df

    # 计算收益率
    df['returns'] = df['close'].pct_change()

    # 波动率 (20日滚动标准差)
    df['volatility_20'] = df['returns'].rolling(window=20).std()

    # 计算趋势强度
    # 使用移动平均线计算趋势
    ma_result = calculate_indicator('MA', df, {'timeperiod': 20})
    if 'MA' in ma_result.columns:
        df['ma20'] = ma_result['MA']
        df['trend_strength'] = (df['close'] - df['ma20']) / df['ma20']
    else:
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['trend_strength'] = (df['close'] - df['ma20']) / df['ma20']

    # 计算市场状态（使用简单的规则）
    df['market_regime'] = 0  # 默认为中性

    # 上升趋势：价格高于20日均线且波动率较低
    df.loc[(df['close'] > df['ma20']) & (df['volatility_20'] < df['volatility_20'].rolling(window=60).mean()), 'market_regime'] = 1

    # 下降趋势：价格低于20日均线且波动率较低
    df.loc[(df['close'] < df['ma20']) & (df['volatility_20'] < df['volatility_20'].rolling(window=60).mean()), 'market_regime'] = -1

    # 震荡市场：波动率高
    df.loc[df['volatility_20'] > df['volatility_20'].rolling(window=60).mean() * 1.5, 'market_regime'] = 2

    # 计算趋势持续时间
    df['regime_change'] = df['market_regime'].diff().abs() > 0
    df['regime_duration'] = df.groupby((df['regime_change'].cumsum())).cumcount() + 1

    # 计算超买超卖指标
    rsi_result = calculate_indicator('RSI', df, {'timeperiod': 14})
    if 'RSI' in rsi_result.columns:
        df['rsi'] = rsi_result['RSI']
        df['overbought'] = (df['rsi'] > 70).astype(int)
        df['oversold'] = (df['rsi'] < 30).astype(int)

    # 计算动量
    df['momentum_10'] = df['close'] - df['close'].shift(10)
    df['momentum_20'] = df['close'] - df['close'].shift(20)

    # 计算相对强度（与大盘相比）
    # 注意：这需要大盘指数数据，此处仅作为示例
    # df['relative_strength'] = df['close'] / df['market_index']

    return df


def add_advanced_indicators(df):
    """
    添加高级技术指标

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了高级技术指标的DataFrame
    """
    # 首先计算基础指标
    df = calculate_advanced_indicators(df)

    # 添加K线形态识别特征
    df = create_pattern_recognition_features(df)

    # 添加市场状态特征
    df = create_market_regime_features(df)

    return df
