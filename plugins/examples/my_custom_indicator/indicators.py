#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
示例插件的指标实现模块
实现自定义指标的计算函数
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


def calculate_sentiment(df: pd.DataFrame, timeperiod: int = 14) -> pd.DataFrame:
    """
    计算情绪指标

    情绪指标是一个基于价格波动计算市场情绪的指标，计算公式为：
    Sentiment = (Close - Open) / Range * 100

    其中，Range = High - Low

    参数:
        df: 输入DataFrame，包含OHLCV数据
        timeperiod: 计算周期

    返回:
        DataFrame: 添加了情绪指标列的DataFrame
    """
    # 复制输入数据
    result = df.copy()

    # 计算价格范围
    price_range = df['high'] - df['low']

    # 计算价格变化
    price_change = df['close'] - df['open']

    # 计算情绪值
    sentiment = price_change / price_range * 100

    # 使用移动平均平滑结果
    sentiment = sentiment.rolling(window=timeperiod).mean()

    # 添加到结果DataFrame
    result['Sentiment'] = sentiment

    return result


def calculate_volatility(df: pd.DataFrame, timeperiod: int = 10, smooth_type: str = 'SMA') -> pd.DataFrame:
    """
    计算波动率指标

    波动率指标是一个基于高低价差计算市场波动性的指标，计算公式为：
    Volatility = (High - Low) / Close * 100

    参数:
        df: 输入DataFrame，包含OHLCV数据
        timeperiod: 计算周期
        smooth_type: 平滑类型，可选值为'SMA'、'EMA'、'WMA'

    返回:
        DataFrame: 添加了波动率指标列的DataFrame
    """
    # 复制输入数据
    result = df.copy()

    # 计算波动率
    volatility = (df['high'] - df['low']) / df['close'] * 100

    # 根据平滑类型进行平滑处理
    if smooth_type == 'SMA':
        # 简单移动平均
        volatility = volatility.rolling(window=timeperiod).mean()
    elif smooth_type == 'EMA':
        # 指数移动平均
        volatility = volatility.ewm(span=timeperiod, adjust=False).mean()
    elif smooth_type == 'WMA':
        # 加权移动平均
        weights = np.arange(1, timeperiod + 1)
        volatility = volatility.rolling(window=timeperiod).apply(
            lambda x: np.sum(weights * x) / np.sum(weights), raw=True
        )
    else:
        # 默认使用简单移动平均
        volatility = volatility.rolling(window=timeperiod).mean()

    # 添加到结果DataFrame
    result['Volatility'] = volatility

    return result


def demo_usage():
    """
    演示如何使用自定义指标
    """
    # 创建示例数据
    dates = pd.date_range(start='2020-01-01', periods=100)
    np.random.seed(42)

    # 模拟价格数据
    close = np.random.random(100) * 100 + 100
    for i in range(1, len(close)):
        close[i] = close[i-1] * (1 + (np.random.random() - 0.5) * 0.05)

    high = close * (1 + np.random.random(100) * 0.03)
    low = close * (1 - np.random.random(100) * 0.03)
    open_price = low + np.random.random(100) * (high - low)
    volume = np.random.random(100) * 1000000 + 500000

    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    # 计算情绪指标
    df_sentiment = calculate_sentiment(df, timeperiod=14)
    print("情绪指标:")
    print(df_sentiment[['close', 'Sentiment']].head())

    # 计算波动率指标
    df_volatility = calculate_volatility(
        df_sentiment, timeperiod=10, smooth_type='EMA')
    print("\n波动率指标:")
    print(df_volatility[['close', 'Sentiment', 'Volatility']].head())


if __name__ == '__main__':
    demo_usage()
