#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
趋势类指标
包含MA、BOLL等趋势类指标的计算函数
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
import importlib

# 尝试导入TA-Lib
try:
    talib = importlib.import_module('talib')
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False

def calculate_ma(df: pd.DataFrame, timeperiod: int = 20) -> pd.DataFrame:
    """
    计算移动平均线

    参数:
        df: 包含close列的DataFrame
        timeperiod: 计算周期

    返回:
        DataFrame: 添加了MA列的DataFrame
    """
    result = df.copy()
    try:
        close = df['close']

        if TALIB_AVAILABLE:
            result['MA'] = pd.Series(
                talib.SMA(close.values, timeperiod=timeperiod),
                index=close.index
            )
        else:
            result['MA'] = close.rolling(window=timeperiod).mean()

    except Exception as e:
        # 返回全NaN
        result['MA'] = pd.Series([float('nan')] * len(df), index=df.index)

    return result

def calculate_bbands(df: pd.DataFrame, timeperiod: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0) -> pd.DataFrame:
    """
    计算布林带

    参数:
        df: 包含close列的DataFrame
        timeperiod: 计算周期
        nbdevup: 上轨标准差倍数
        nbdevdn: 下轨标准差倍数

    返回:
        DataFrame: 添加了BBUpper、BBMiddle、BBLower列的DataFrame
    """
    result = df.copy()
    try:
        close = df['close']

        if TALIB_AVAILABLE:
            upper, middle, lower = talib.BBANDS(
                close.values,
                timeperiod=timeperiod,
                nbdevup=nbdevup,
                nbdevdn=nbdevdn
            )
            result['BBUpper'] = pd.Series(upper, index=close.index)
            result['BBMiddle'] = pd.Series(middle, index=close.index)
            result['BBLower'] = pd.Series(lower, index=close.index)
        else:
            # 使用pandas实现
            middle = close.rolling(window=timeperiod).mean()
            std = close.rolling(window=timeperiod).std()
            upper = middle + nbdevup * std
            lower = middle - nbdevdn * std

            result['BBUpper'] = upper
            result['BBMiddle'] = middle
            result['BBLower'] = lower

    except Exception as e:
        # 返回全NaN
        for col in ['BBUpper', 'BBMiddle', 'BBLower']:
            result[col] = pd.Series([float('nan')] * len(df), index=df.index)

    return result

def calculate_adx(df: pd.DataFrame, timeperiod: int = 14) -> pd.DataFrame:
    """
    计算平均趋向指数(ADX)

    参数:
        df: 包含high、low、close列的DataFrame
        timeperiod: 计算周期

    返回:
        DataFrame: 添加了ADX列的DataFrame
    """
    result = df.copy()
    try:
        high = df['high']
        low = df['low']
        close = df['close']

        if TALIB_AVAILABLE:
            # 使用TA-Lib计算ADX
            adx = talib.ADX(high.values, low.values,
                            close.values, timeperiod=timeperiod)
            result['ADX'] = pd.Series(adx, index=close.index)
        else:
            # 使用pandas实现ADX
            # 注意：这是一个简化版本，完整的ADX计算比较复杂
            # 计算真实范围(TR)
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
            atr = tr.rolling(window=timeperiod).mean()

            # 计算方向运动(DM)
            up_move = high - high.shift(1)
            down_move = low.shift(1) - low

            # 正方向运动(+DM)
            plus_dm = np.where((up_move > down_move) &
                               (up_move > 0), up_move, 0)
            plus_dm = pd.Series(plus_dm, index=close.index)

            # 负方向运动(-DM)
            minus_dm = np.where((down_move > up_move) &
                                (down_move > 0), down_move, 0)
            minus_dm = pd.Series(minus_dm, index=close.index)

            # 平滑化+DM和-DM
            plus_di = 100 * (plus_dm.rolling(window=timeperiod).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=timeperiod).mean() / atr)

            # 计算方向指数(DX)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

            # 计算ADX
            result['ADX'] = dx.rolling(window=timeperiod).mean()

    except Exception as e:
        # 返回全NaN
        result['ADX'] = pd.Series([float('nan')] * len(df), index=df.index)

    return result
