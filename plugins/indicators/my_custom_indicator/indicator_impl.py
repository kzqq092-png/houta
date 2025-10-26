#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自定义指标实现
包含自定义指标的计算函数
"""

import pandas as pd
import numpy as np

def calculate_emotion_index(df: pd.DataFrame, timeperiod: int = 14) -> pd.DataFrame:
    """
    计算市场情绪指标

    情绪指标计算公式：
    EMOTION = (CLOSE - OPEN) / (HIGH - LOW) * VOLUME / AVG_VOLUME

    参数:
        df: 输入DataFrame，包含OHLCV数据
        timeperiod: 计算周期，默认为14

    返回:
        DataFrame: 添加了EMOTION列的DataFrame
    """
    # 复制输入数据，避免修改原始数据
    result = df.copy()

    # 确保必要的列存在
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in required_columns:
        if col not in result.columns:
            raise ValueError(f"输入数据缺少必要的列: {col}")

    # 计算价格变化率：(收盘价 - 开盘价) / (最高价 - 最低价)
    # 处理除以零的情况
    price_range = result['high'] - result['low']
    price_range = price_range.replace(0, np.nan)  # 将0替换为NaN，避免除以零
    price_change_ratio = (result['close'] - result['open']) / price_range
    price_change_ratio = price_change_ratio.fillna(0)  # 将NaN替换为0

    # 计算成交量相对于平均成交量的比值
    avg_volume = result['volume'].rolling(window=timeperiod).mean()
    volume_ratio = result['volume'] / avg_volume
    volume_ratio = volume_ratio.fillna(1)  # 将NaN替换为1

    # 计算情绪指标
    result['EMOTION'] = price_change_ratio * volume_ratio

    # 对结果进行标准化，使其范围在-1到1之间
    max_abs_emotion = result['EMOTION'].abs().rolling(
        window=timeperiod*5).max()
    max_abs_emotion = max_abs_emotion.fillna(1)  # 将NaN替换为1
    result['EMOTION'] = result['EMOTION'] / max_abs_emotion
    result['EMOTION'] = result['EMOTION'].clip(-1, 1)  # 限制在-1到1之间

    return result

def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算成交量加权平均价

    VWAP计算公式：
    VWAP = ∑(PRICE * VOLUME) / ∑(VOLUME)

    参数:
        df: 输入DataFrame，包含OHLCV数据

    返回:
        DataFrame: 添加了VWAP列的DataFrame
    """
    # 复制输入数据，避免修改原始数据
    result = df.copy()

    # 确保必要的列存在
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in required_columns:
        if col not in result.columns:
            raise ValueError(f"输入数据缺少必要的列: {col}")

    # 计算典型价格：(高 + 低 + 收) / 3
    typical_price = (result['high'] + result['low'] + result['close']) / 3

    # 计算成交量加权
    volume_sum = result['volume'].cumsum()
    price_volume_sum = (typical_price * result['volume']).cumsum()

    # 计算VWAP
    result['VWAP'] = price_volume_sum / volume_sum
    result['VWAP'] = result['VWAP'].fillna(result['close'])  # 对于第一个值，使用收盘价

    return result
