import numpy as np
import pandas as pd
from functools import lru_cache

# --- MA ---


def calc_ma(close: pd.Series, n: int) -> pd.Series:
    """计算移动平均线"""
    return close.rolling(n).mean()

# --- MACD ---


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

# --- RSI ---


def calc_rsi(close: pd.Series, n=14):
    """计算RSI指标"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- KDJ ---


def calc_kdj(df: pd.DataFrame, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=m1).mean()
    d = k.ewm(com=m2).mean()
    j = 3 * k - 2 * d
    return k, d, j

# --- BOLL ---


def calc_boll(close: pd.Series, n=20, p=2):
    """计算布林带"""
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    upper = mid + p * std
    lower = mid - p * std
    return mid, upper, lower

# --- ATR ---


def calc_atr(df: pd.DataFrame, n=14):
    """计算ATR指标"""
    high = df['high']
    low = df['low']
    close = df['close']
    tr = np.maximum(high - low, np.abs(high - close.shift()),
                    np.abs(low - close.shift()))
    atr = tr.rolling(n).mean()
    return atr

# --- OBV ---


def calc_obv(df: pd.DataFrame):
    """计算OBV指标"""
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    return obv

# --- CCI ---


def calc_cci(df: pd.DataFrame, n=14):
    """计算CCI指标"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    cci = (tp - ma) / (0.015 * md)
    return cci

# 可选：加lru_cache缓存装饰器提升性能
