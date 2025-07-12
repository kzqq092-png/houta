#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标数据库初始化脚本
用于初始化指标数据库，导入内置指标
"""

from db.models.indicator_models import (
    IndicatorDatabase,
    Indicator,
    IndicatorParameter,
    IndicatorImplementation,
    IndicatorCategory
)
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


# 指标数据库文件路径
INDICATOR_DB_PATH = os.path.join(os.path.dirname(__file__), 'indicators.db')

# 内置指标分类
DEFAULT_CATEGORIES = [
    IndicatorCategory(id=1, name='trend', display_name='趋势类',
                      description='用于判断市场趋势的指标'),
    IndicatorCategory(id=2, name='oscillator',
                      display_name='震荡类', description='用于判断市场超买超卖的指标'),
    IndicatorCategory(id=3, name='volume',
                      display_name='成交量类', description='基于成交量的指标'),
    IndicatorCategory(id=4, name='volatility',
                      display_name='波动性类', description='用于衡量市场波动性的指标'),
    IndicatorCategory(id=5, name='pattern',
                      display_name='形态类', description='K线形态识别指标'),
    IndicatorCategory(id=6, name='other', display_name='其他',
                      description='其他类型的指标')
]


def create_ma_indicator() -> Indicator:
    """创建MA(移动平均线)指标"""
    return Indicator(
        id=1,
        name='MA',
        display_name='移动平均线',
        category_id=1,  # 趋势类
        description='移动平均线是最基本的技术分析工具之一，用于平滑价格数据以识别趋势。',
        formula='MA(n) = (P1 + P2 + ... + Pn) / n',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=20,
                min_value=1,
                max_value=500,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='MA',  # 使用MA，与TA-Lib保持一致
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='core.indicators.library.trends.calculate_ma',
                code='from core.indicators.library.trends import calculate_ma'
            )
        ],
        output_names=['MA']
    )


def create_macd_indicator() -> Indicator:
    """创建MACD(指数平滑异同移动平均线)指标"""
    return Indicator(
        id=2,
        name='MACD',
        display_name='指数平滑异同移动平均线',
        category_id=2,  # 震荡类
        description='MACD是由两条不同速度的指数移动平均线的差值所形成，用于判断多空力量的强弱和转变。',
        formula='MACD = EMA(close, fast) - EMA(close, slow)\nSignal = EMA(MACD, signal)\nHistogram = MACD - Signal',
        parameters=[
            IndicatorParameter(
                name='fastperiod',
                description='快速EMA周期',
                type='int',
                default_value=12,
                min_value=2,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowperiod',
                description='慢速EMA周期',
                type='int',
                default_value=26,
                min_value=2,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='signalperiod',
                description='信号线周期',
                type='int',
                default_value=9,
                min_value=1,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='MACD',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_macd',
                code='from core.indicators.library.oscillators import calculate_macd'
            )
        ],
        output_names=['MACD', 'MACDSignal', 'MACDHist']
    )


def create_rsi_indicator() -> Indicator:
    """创建RSI(相对强弱指标)指标"""
    return Indicator(
        id=3,
        name='RSI',
        display_name='相对强弱指标',
        category_id=2,  # 震荡类
        description='RSI是一种动量指标，用于衡量价格变动的速度和变化，判断市场是否超买或超卖。',
        formula='RSI = 100 - (100 / (1 + RS))\nRS = 平均上涨幅度 / 平均下跌幅度',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=14,
                min_value=1,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='RSI',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_rsi',
                code='from core.indicators.library.oscillators import calculate_rsi'
            )
        ],
        output_names=['RSI']
    )


def create_bollinger_bands_indicator() -> Indicator:
    """创建布林带指标"""
    return Indicator(
        id=4,
        name='BBANDS',
        display_name='布林带',
        category_id=4,  # 波动性类
        description='布林带是一种波动性指标，由中轨（移动平均线）和上下轨（标准差的倍数）组成，用于判断价格波动范围。',
        formula='中轨 = MA(close, n)\n上轨 = 中轨 + k * σ\n下轨 = 中轨 - k * σ\n其中 σ 为标准差',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=20,
                min_value=2,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='nbdevup',
                description='上轨标准差倍数',
                type='float',
                default_value=2.0,
                min_value=0.1,
                max_value=10.0,
                step=0.1
            ),
            IndicatorParameter(
                name='nbdevdn',
                description='下轨标准差倍数',
                type='float',
                default_value=2.0,
                min_value=0.1,
                max_value=10.0,
                step=0.1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='BBANDS',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_bbands',
                code='from core.indicators.library.trends import calculate_bbands'
            )
        ],
        output_names=['BBUpper', 'BBMiddle', 'BBLower']
    )


def create_atr_indicator() -> Indicator:
    """创建ATR(平均真实波幅)指标"""
    return Indicator(
        id=5,
        name='ATR',
        display_name='平均真实波幅',
        category_id=4,  # 波动性类
        description='ATR是一种波动性指标，用于衡量市场波动的程度，不关注价格方向。',
        formula='TR = max(high - low, |high - close_prev|, |low - close_prev|)\nATR = MA(TR, n)',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=14,
                min_value=1,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='ATR',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_atr',
                code='from core.indicators.library.volatility import calculate_atr'
            )
        ],
        output_names=['ATR']
    )


def create_obv_indicator() -> Indicator:
    """创建OBV(能量潮)指标"""
    return Indicator(
        id=6,
        name='OBV',
        display_name='能量潮',
        category_id=3,  # 成交量类
        description='OBV是一种成交量指标，通过累计成交量来确认价格趋势。',
        formula='若当日收盘价 > 前日收盘价，OBV = 前日OBV + 当日成交量\n若当日收盘价 < 前日收盘价，OBV = 前日OBV - 当日成交量\n若当日收盘价 = 前日收盘价，OBV = 前日OBV',
        parameters=[],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='OBV',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_obv',
                code='from core.indicators.library.volumes import calculate_obv'
            )
        ],
        output_names=['OBV']
    )


def create_kdj_indicator() -> Indicator:
    """创建KDJ指标"""
    return Indicator(
        id=7,
        name='KDJ',
        display_name='随机指标',
        category_id=2,  # 震荡类
        description='KDJ是一种超买超卖指标，根据价格在一段时间内的最高价、最低价及收盘价计算，用于判断市场超买超卖状态。',
        formula='K = 2/3 * 前日K + 1/3 * RSV\nD = 2/3 * 前日D + 1/3 * K\nJ = 3 * K - 2 * D\n其中RSV = (收盘价 - 最低价) / (最高价 - 最低价) * 100',
        parameters=[
            IndicatorParameter(
                name='fastk_period',
                description='RSV周期',
                type='int',
                default_value=9,
                min_value=1,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowk_period',
                description='K值平滑周期',
                type='int',
                default_value=3,
                min_value=1,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowd_period',
                description='D值平滑周期',
                type='int',
                default_value=3,
                min_value=1,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='STOCH',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_kdj',
                code='from core.indicators.library.oscillators import calculate_kdj'
            )
        ],
        output_names=['K', 'D', 'J']
    )


def create_cci_indicator() -> Indicator:
    """创建CCI(顺势指标)指标"""
    return Indicator(
        id=8,
        name='CCI',
        display_name='顺势指标',
        category_id=2,  # 震荡类
        description='CCI是一种超买超卖指标，通过测量价格偏离移动平均线的程度来判断市场超买超卖状态。',
        formula='CCI = (TP - SMA(TP, n)) / (0.015 * MD)\n其中TP为典型价格，MD为平均偏差',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=14,
                min_value=1,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='CCI',
                is_default=True
            ),
            IndicatorImplementation(
                engine='custom',
                function_name='calculate_cci',
                code='from core.indicators.library.oscillators import calculate_cci'
            )
        ],
        output_names=['CCI']
    )


def create_stoch_indicator() -> Indicator:
    """创建STOCH(随机指标)指标"""
    return Indicator(
        id=9,
        name='STOCH',
        display_name='随机指标',
        category_id=2,  # 震荡类
        description='随机指标是一种动量指标，用于判断市场超买超卖状态。',
        formula='K = (收盘价 - 最低价) / (最高价 - 最低价) * 100\nD = K的移动平均',
        parameters=[
            IndicatorParameter(
                name='fastk_period',
                description='K值周期',
                type='int',
                default_value=5,
                min_value=1,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowk_period',
                description='K值平滑周期',
                type='int',
                default_value=3,
                min_value=1,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowk_matype',
                description='K值平滑类型',
                type='int',
                default_value=0,
                min_value=0,
                max_value=8,
                step=1
            ),
            IndicatorParameter(
                name='slowd_period',
                description='D值周期',
                type='int',
                default_value=3,
                min_value=1,
                max_value=100,
                step=1
            ),
            IndicatorParameter(
                name='slowd_matype',
                description='D值平滑类型',
                type='int',
                default_value=0,
                min_value=0,
                max_value=8,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='STOCH',
                is_default=True
            )
        ],
        output_names=['SlowK', 'SlowD']
    )


def create_adx_indicator() -> Indicator:
    """创建ADX(平均方向指数)指标"""
    return Indicator(
        id=10,
        name='ADX',
        display_name='平均方向指数',
        category_id=1,  # 趋势类
        description='ADX是一种趋势强度指标，用于判断趋势的强弱，不关注趋势方向。',
        formula='ADX = SMA(|+DI - -DI| / (+DI + -DI) * 100, n)',
        parameters=[
            IndicatorParameter(
                name='timeperiod',
                description='计算周期',
                type='int',
                default_value=14,
                min_value=2,
                max_value=100,
                step=1
            )
        ],
        implementations=[
            IndicatorImplementation(
                engine='talib',
                function_name='ADX',
                is_default=True
            )
        ],
        output_names=['ADX']
    )


def initialize_indicators_db():
    """初始化指标数据库"""
    try:
        # 如果数据库文件已存在，先删除
        if os.path.exists(INDICATOR_DB_PATH):
            try:
                os.remove(INDICATOR_DB_PATH)
            except PermissionError:
                print(f"警告: 无法删除数据库文件 {INDICATOR_DB_PATH}，可能被其他进程锁定")
                print("将尝试使用现有数据库文件")
    except Exception as e:
        print(f"警告: 初始化数据库时发生错误: {str(e)}")

    # 创建数据库
    db = IndicatorDatabase(INDICATOR_DB_PATH)

    try:
        # 添加分类
        for category in DEFAULT_CATEGORIES:
            try:
                # 检查分类是否已存在
                existing_category = db.get_category_by_name(category.name)
                if not existing_category:
                    db.add_category(category)
            except Exception as e:
                print(f"警告: 添加分类 {category.name} 时发生错误: {str(e)}")

        # 添加内置指标
        indicators = [
            create_ma_indicator(),
            create_macd_indicator(),
            create_rsi_indicator(),
            create_bollinger_bands_indicator(),
            create_atr_indicator(),
            create_obv_indicator(),
            create_kdj_indicator(),
            create_cci_indicator(),
            create_stoch_indicator(),
            create_adx_indicator()
        ]

        for indicator in indicators:
            try:
                # 检查指标是否已存在
                existing_indicator = db.get_indicator_by_name(indicator.name)
                if not existing_indicator:
                    db.add_indicator(indicator)
                else:
                    print(f"指标 {indicator.name} 已存在，跳过添加")
            except Exception as e:
                print(f"警告: 添加指标 {indicator.name} 时发生错误: {str(e)}")

        print(f"指标数据库初始化完成，共添加 {len(indicators)} 个内置指标")
    except Exception as e:
        print(f"初始化指标数据库时发生错误: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        # 关闭数据库连接
        db.close()


if __name__ == "__main__":
    initialize_indicators_db()
