#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
形态类指标
包含K线形态识别的计算函数
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict
import importlib

# 尝试导入TA-Lib
try:
    talib = importlib.import_module('talib')
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False


def calculate_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算K线形态识别

    参数:
        df: 包含open、high、low、close列的DataFrame

    返回:
        DataFrame: 添加了各种K线形态列的DataFrame
    """
    result = df.copy()

    if not TALIB_AVAILABLE:
        print("警告：TA-Lib未安装，无法使用K线形态识别功能")
        return result

    try:
        open_price = df['open']
        high = df['high']
        low = df['low']
        close = df['close']

        # 定义要计算的K线形态及其对应的TA-Lib函数
        pattern_functions = {
            'CDL2CROWS': '两只乌鸦',
            'CDL3BLACKCROWS': '三只黑乌鸦',
            'CDL3INSIDE': '三内部上涨和下跌',
            'CDL3LINESTRIKE': '三线打击',
            'CDL3OUTSIDE': '三外部上涨和下跌',
            'CDL3STARSINSOUTH': '南方三星',
            'CDL3WHITESOLDIERS': '三白兵',
            'CDLABANDONEDBABY': '弃婴',
            'CDLADVANCEBLOCK': '大敌当前',
            'CDLBELTHOLD': '捉腰带线',
            'CDLBREAKAWAY': '脱离',
            'CDLCLOSINGMARUBOZU': '收盘丰城',
            'CDLCONCEALBABYSWALL': '藏婴吞没',
            'CDLCOUNTERATTACK': '反击线',
            'CDLDARKCLOUDCOVER': '乌云盖顶',
            'CDLDOJI': '十字',
            'CDLDOJISTAR': '十字星',
            'CDLDRAGONFLYDOJI': '蜻蜓十字',
            'CDLENGULFING': '吞没模式',
            'CDLEVENINGDOJISTAR': '黄昏十字星',
            'CDLEVENINGSTAR': '黄昏之星',
            'CDLGAPSIDESIDEWHITE': '向上/下跳空并列阳线',
            'CDLGRAVESTONEDOJI': '墓碑十字',
            'CDLHAMMER': '锤头',
            'CDLHANGINGMAN': '上吊线',
            'CDLHARAMI': '母子线',
            'CDLHARAMICROSS': '十字孕线',
            'CDLHIGHWAVE': '风高浪大线',
            'CDLHIKKAKE': '陷阱',
            'CDLHIKKAKEMOD': '修正陷阱',
            'CDLHOMINGPIGEON': '家鸽',
            'CDLIDENTICAL3CROWS': '三胞胎乌鸦',
            'CDLINNECK': '颈内线',
            'CDLINVERTEDHAMMER': '倒锤头',
            'CDLKICKING': '反冲形态',
            'CDLKICKINGBYLENGTH': '由较长缺口反冲形态',
            'CDLLADDERBOTTOM': '梯底',
            'CDLLONGLEGGEDDOJI': '长脚十字',
            'CDLLONGLINE': '长蜡烛',
            'CDLMARUBOZU': '光头光脚/缺影线',
            'CDLMATCHINGLOW': '相同低价',
            'CDLMATHOLD': '铺垫',
            'CDLMORNINGDOJISTAR': '早晨十字星',
            'CDLMORNINGSTAR': '早晨之星',
            'CDLONNECK': '颈上线',
            'CDLPIERCING': '刺透形态',
            'CDLRICKSHAWMAN': '黄包车夫',
            'CDLRISEFALL3METHODS': '上升/下降三法',
            'CDLSEPARATINGLINES': '分离线',
            'CDLSHOOTINGSTAR': '射击之星',
            'CDLSHORTLINE': '短蜡烛',
            'CDLSPINNINGTOP': '纺锤',
            'CDLSTALLEDPATTERN': '停顿形态',
            'CDLSTICKSANDWICH': '条形三明治',
            'CDLTAKURI': '探水竿',
            'CDLTASUKIGAP': '跳空并列阴阳线',
            'CDLTHRUSTING': '插入',
            'CDLTRISTAR': '三星',
            'CDLUNIQUE3RIVER': '奇特三河床',
            'CDLUPSIDEGAP2CROWS': '向上跳空的两只乌鸦',
            'CDLXSIDEGAP3METHODS': '上升/下降跳空三法'
        }

        # 计算所有K线形态
        for pattern_name in pattern_functions:
            if hasattr(talib, pattern_name):
                pattern_func = getattr(talib, pattern_name)
                result[pattern_name] = pd.Series(
                    pattern_func(open_price.values, high.values,
                                 low.values, close.values),
                    index=close.index
                )

    except Exception as e:
        print(f"计算K线形态时发生错误: {str(e)}")

    return result


def calculate_pattern_recognition_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    创建K线形态识别特征

    参数:
        df: 包含open、high、low、close列的DataFrame

    返回:
        DataFrame: 添加了形态识别特征的DataFrame
    """
    result = df.copy()

    try:
        # 计算K线实体长度和影线长度
        result['body_length'] = (result['close'] - result['open']).abs()
        result['upper_shadow'] = result.apply(
            lambda x: x['high'] - max(x['open'], x['close']), axis=1
        )
        result['lower_shadow'] = result.apply(
            lambda x: min(x['open'], x['close']) - x['low'], axis=1
        )

        # 计算K线实体占比
        result['body_percent'] = result['body_length'] / \
            (result['high'] - result['low']).replace(0, 1e-10)

        # 计算上下影线占比
        result['upper_shadow_percent'] = result['upper_shadow'] / \
            (result['high'] - result['low']).replace(0, 1e-10)
        result['lower_shadow_percent'] = result['lower_shadow'] / \
            (result['high'] - result['low']).replace(0, 1e-10)

        # 计算K线方向
        result['candle_direction'] = np.where(
            result['close'] >= result['open'], 1, -1)

        # 识别锤子线
        result['is_hammer'] = ((result['lower_shadow'] > 2 * result['body_length']) &
                               (result['upper_shadow'] < 0.1 * result['body_length']) &
                               (result['body_percent'] < 0.3))

        # 识别上吊线
        result['is_hanging_man'] = ((result['lower_shadow'] > 2 * result['body_length']) &
                                    (result['upper_shadow'] < 0.1 * result['body_length']) &
                                    (result['body_percent'] < 0.3))

        # 识别吞没形态
        result['is_engulfing_bullish'] = ((result['candle_direction'].shift(1) == -1) &
                                          (result['candle_direction'] == 1) &
                                          (result['open'] < result['close'].shift(1)) &
                                          (result['close'] > result['open'].shift(1)))

        result['is_engulfing_bearish'] = ((result['candle_direction'].shift(1) == 1) &
                                          (result['candle_direction'] == -1) &
                                          (result['open'] > result['close'].shift(1)) &
                                          (result['close'] < result['open'].shift(1)))

        # 识别十字星
        result['is_doji'] = (result['body_length'] < 0.1 *
                             (result['high'] - result['low']))

        # 识别启明星
        result['is_morning_star'] = ((result['candle_direction'].shift(2) == -1) &
                                     (result['body_length'].shift(1) < 0.5 * result['body_length'].shift(2)) &
                                     (result['candle_direction'] == 1) &
                                     (result['close'] > (result['open'].shift(2) + result['close'].shift(2)) / 2))

        # 识别黄昏星
        result['is_evening_star'] = ((result['candle_direction'].shift(2) == 1) &
                                     (result['body_length'].shift(1) < 0.5 * result['body_length'].shift(2)) &
                                     (result['candle_direction'] == -1) &
                                     (result['close'] < (result['open'].shift(2) + result['close'].shift(2)) / 2))

        # 识别三白兵
        result['is_three_white_soldiers'] = ((result['candle_direction'] == 1) &
                                             (result['candle_direction'].shift(1) == 1) &
                                             (result['candle_direction'].shift(2) == 1) &
                                             (result['close'] > result['close'].shift(1)) &
                                             (result['close'].shift(1) > result['close'].shift(2)) &
                                             (result['open'] > result['open'].shift(1)) &
                                             (result['open'].shift(1) > result['open'].shift(2)))

        # 识别三只乌鸦
        result['is_three_black_crows'] = ((result['candle_direction'] == -1) &
                                          (result['candle_direction'].shift(1) == -1) &
                                          (result['candle_direction'].shift(2) == -1) &
                                          (result['close'] < result['close'].shift(1)) &
                                          (result['close'].shift(1) < result['close'].shift(2)) &
                                          (result['open'] < result['open'].shift(1)) &
                                          (result['open'].shift(1) < result['open'].shift(2)))

    except Exception as e:
        print(f"创建K线形态识别特征时发生错误: {str(e)}")

    return result
