#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
动量类指标
包含EMA、ROC等动量类指标的计算函数
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


def calculate_ema(df: pd.DataFrame, timeperiod: int = 20) -> pd.DataFrame:
    """
    计算指数移动平均线(EMA)

    参数:
        df: 包含close列的DataFrame
        timeperiod: 计算周期

    返回:
        DataFrame: 添加了EMA列的DataFrame
    """
    result = df.copy()
    try:
        close = df['close']

        if TALIB_AVAILABLE:
            ema = talib.EMA(close.values, timeperiod=timeperiod)
            result['EMA'] = pd.Series(ema, index=close.index)
        else:
            # 使用pandas实现
            result['EMA'] = close.ewm(span=timeperiod, adjust=False).mean()

    except Exception as e:
        # 返回全NaN
        result['EMA'] = pd.Series([float('nan')] * len(df), index=df.index)

    return result


def calculate_roc(df: pd.DataFrame, timeperiod: int = 10) -> pd.DataFrame:
    """
    计算变动率(ROC)指标

    参数:
        df: 包含close列的DataFrame
        timeperiod: 计算周期

    返回:
        DataFrame: 添加了ROC列的DataFrame
    """
    result = df.copy()
    try:
        close = df['close']

        if TALIB_AVAILABLE:
            roc = talib.ROC(close.values, timeperiod=timeperiod)
            result['ROC'] = pd.Series(roc, index=close.index)
        else:
            # 使用pandas实现
            result['ROC'] = close.pct_change(timeperiod) * 100

    except Exception as e:
        # 返回全NaN
        result['ROC'] = pd.Series([float('nan')] * len(df), index=df.index)

    return result
