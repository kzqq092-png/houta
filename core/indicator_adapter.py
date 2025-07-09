#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标适配器
用于将旧的指标计算接口适配到新的指标计算服务
"""

from core.indicator_service import (
    calculate_indicator,
    get_indicator_metadata,
    get_all_indicators_metadata,
    get_indicators_by_category
)
from core.indicators.library import *
import os
import sys
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# 设置日志
logger = logging.getLogger('indicator_adapter')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def get_indicator_english_name(name: str) -> str:
    """
    获取指标英文名称

    参数:
        name: 指标名称（可能是中文或英文）

    返回:
        str: 指标英文名称
    """
    # 获取指标元数据
    metadata = get_indicator_metadata(name)

    # 如果指标不存在，尝试查找中文名匹配的指标
    if not metadata:
        # 获取所有指标元数据
        all_metadata = get_all_indicators_metadata()

        # 查找display_name匹配的指标
        for indicator_name, indicator_metadata in all_metadata.items():
            if indicator_metadata.get('display_name') == name:
                return indicator_name

        # 如果没有找到匹配的指标，返回原名称
        return name

    # 返回指标英文名称（即指标ID）
    return metadata.get('name', name)


def calc_talib_indicator(name: str, df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    计算指标的适配函数，兼容旧的 calc_talib_indicator 接口

    参数:
        name: 指标名称
        df: 输入DataFrame，包含OHLCV数据
        params: 计算参数，如果为None则使用默认参数

    返回:
        DataFrame: 添加了指标列的DataFrame
    """
    try:
        return calculate_indicator(name, df, params)
    except Exception as e:
        logger.error(f"计算指标 {name} 时发生错误: {str(e)}")
        return df


def calc_ma(close: pd.Series, n: int) -> pd.Series:
    """
    计算MA指标的适配函数，兼容旧的 calc_ma 接口

    参数:
        close: 收盘价序列
        n: 周期

    返回:
        Series: MA序列
    """
    # 构造一个临时DataFrame
    df = pd.DataFrame({'close': close})

    # 直接使用新的指标算法库
    from core.indicators.library.trends import calculate_ma
    result = calculate_ma(df, timeperiod=n)

    # 返回MA序列
    if 'MA' in result.columns:
        return result['MA']
    else:
        return pd.Series([float('nan')] * len(close), index=close.index, name=f"MA{n}")


def calc_macd(close: pd.Series, fast=12, slow=26, signal=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算MACD指标的适配函数，兼容旧的 calc_macd 接口

    参数:
        close: 收盘价序列
        fast: 快速EMA周期
        slow: 慢速EMA周期
        signal: 信号线周期

    返回:
        Tuple[Series, Series, Series]: MACD, Signal, Histogram
    """
    # 构造一个临时DataFrame
    df = pd.DataFrame({'close': close})

    # 直接使用新的指标算法库
    from core.indicators.library.oscillators import calculate_macd
    result = calculate_macd(df, fastperiod=fast, slowperiod=slow, signalperiod=signal)

    # 返回MACD序列
    if 'MACD' in result.columns and 'MACDSignal' in result.columns and 'MACDHist' in result.columns:
        return (
            result['MACD'],
            result['MACDSignal'],
            result['MACDHist']
        )
    else:
        # 返回全NaN序列
        return (
            pd.Series([float('nan')] * len(close), index=close.index, name="MACD"),
            pd.Series([float('nan')] * len(close), index=close.index, name="MACD_signal"),
            pd.Series([float('nan')] * len(close), index=close.index, name="MACD_hist")
        )


def calc_rsi(close: pd.Series, n=14) -> pd.Series:
    """
    计算RSI指标的适配函数，兼容旧的 calc_rsi 接口

    参数:
        close: 收盘价序列
        n: 周期

    返回:
        Series: RSI序列
    """
    # 构造一个临时DataFrame
    df = pd.DataFrame({'close': close})

    # 直接使用新的指标算法库
    from core.indicators.library.oscillators import calculate_rsi
    result = calculate_rsi(df, timeperiod=n)

    # 返回RSI序列
    if 'RSI' in result.columns:
        return result['RSI']
    else:
        return pd.Series([float('nan')] * len(close), index=close.index, name=f"RSI{n}")


def calc_kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算KDJ指标的适配函数，兼容旧的 calc_kdj 接口

    参数:
        df: 输入DataFrame，包含high, low, close列
        n: K值周期
        m1: K值平滑周期
        m2: D值平滑周期

    返回:
        Tuple[Series, Series, Series]: K, D, J
    """
    # 调用新的指标计算服务
    result = calculate_indicator('KDJ', df, {
        'fastk_period': n,
        'slowk_period': m1,
        'slowd_period': m2
    })

    # 返回KDJ序列
    if 'K' in result.columns and 'D' in result.columns and 'J' in result.columns:
        return (
            result['K'],
            result['D'],
            result['J']
        )
    else:
        # 返回全NaN序列
        idx = df.index
        return (
            pd.Series([float('nan')] * len(df), index=idx, name="K"),
            pd.Series([float('nan')] * len(df), index=idx, name="D"),
            pd.Series([float('nan')] * len(df), index=idx, name="J")
        )


def calc_boll(close: pd.Series, n=20, p=2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带指标的适配函数，兼容旧的 calc_boll 接口

    参数:
        close: 收盘价序列
        n: 周期
        p: 标准差倍数

    返回:
        Tuple[Series, Series, Series]: 中轨, 上轨, 下轨
    """
    # 构造一个临时DataFrame
    df = pd.DataFrame({'close': close})

    # 调用新的指标计算服务
    result = calculate_indicator('BBANDS', df, {
        'timeperiod': n,
        'nbdevup': p,
        'nbdevdn': p
    })

    # 返回布林带序列
    if 'BBMiddle' in result.columns and 'BBUpper' in result.columns and 'BBLower' in result.columns:
        return (
            result['BBMiddle'],
            result['BBUpper'],
            result['BBLower']
        )
    else:
        # 返回全NaN序列
        return (
            pd.Series([float('nan')] * len(close), index=close.index, name="BOLL_mid"),
            pd.Series([float('nan')] * len(close), index=close.index, name="BOLL_upper"),
            pd.Series([float('nan')] * len(close), index=close.index, name="BOLL_lower")
        )


def calc_atr(df: pd.DataFrame, n=14) -> pd.Series:
    """
    计算ATR指标的适配函数，兼容旧的 calc_atr 接口

    参数:
        df: 输入DataFrame，包含high, low, close列
        n: 周期

    返回:
        Series: ATR序列
    """
    # 调用新的指标计算服务
    result = calculate_indicator('ATR', df, {'timeperiod': n})

    # 返回ATR序列
    if 'ATR' in result.columns:
        return result['ATR']
    else:
        return pd.Series([float('nan')] * len(df), index=df.index, name=f"ATR{n}")


def calc_obv(df: pd.DataFrame) -> pd.Series:
    """
    计算OBV指标的适配函数，兼容旧的 calc_obv 接口

    参数:
        df: 输入DataFrame，包含close, volume列

    返回:
        Series: OBV序列
    """
    # 调用新的指标计算服务
    result = calculate_indicator('OBV', df, {})

    # 返回OBV序列
    if 'OBV' in result.columns:
        return result['OBV']
    else:
        return pd.Series([float('nan')] * len(df), index=df.index, name="OBV")


def calc_cci(df: pd.DataFrame, n=14) -> pd.Series:
    """
    计算CCI指标的适配函数，兼容旧的 calc_cci 接口

    参数:
        df: 输入DataFrame，包含high, low, close列
        n: 周期

    返回:
        Series: CCI序列
    """
    # 调用新的指标计算服务
    result = calculate_indicator('CCI', df, {'timeperiod': n})

    # 返回CCI序列
    if 'CCI' in result.columns:
        return result['CCI']
    else:
        return pd.Series([float('nan')] * len(df), index=df.index, name=f"CCI{n}")


def get_talib_indicator_list() -> list:
    """
    获取所有支持的指标名称列表，兼容旧的 get_talib_indicator_list 接口

    返回:
        List[str]: 指标名称列表
    """
    # 获取所有指标的元数据
    all_metadata = get_all_indicators_metadata()

    # 返回指标名称列表
    return list(all_metadata.keys())


def get_talib_category(name: str) -> str:
    """
    获取指标分类，兼容旧的 get_talib_category 接口

    参数:
        name: 指标名称

    返回:
        str: 指标分类
    """
    # 获取指标元数据
    metadata = get_indicator_metadata(name)

    # 如果指标不存在，返回"其他"
    if not metadata:
        return "其他"

    # 根据分类ID获取分类名称
    category_id = metadata.get('category_id', 6)  # 默认为"其他"

    # 分类ID到中文名称的映射
    category_map = {
        1: "趋势类",
        2: "震荡类",
        3: "成交量类",
        4: "波动性类",
        5: "形态类",
        6: "其他"
    }

    return category_map.get(category_id, "其他")


def get_talib_chinese_name(name: str) -> str:
    """
    获取指标中文名称，兼容旧的 get_talib_chinese_name 接口

    参数:
        name: 指标名称

    返回:
        str: 指标中文名称
    """
    # 获取指标元数据
    metadata = get_indicator_metadata(name)

    # 如果指标不存在，返回原名称
    if not metadata:
        return name

    return metadata.get('display_name', name)


def get_indicator_params_config(indicator_name: str) -> dict:
    """
    获取指标参数配置

    参数:
        indicator_name: 指标名称

    返回:
        dict: 参数配置字典
    """
    # 获取指标元数据
    metadata = get_indicator_metadata(indicator_name)

    # 如果指标不存在，返回空配置
    if not metadata:
        return {"parameters": {}, "inputs": ["close"]}

    # 从元数据中提取参数配置
    params_config = {}
    params = metadata.get('parameters', {})

    # 转换为旧格式
    for param_name, param_info in params.items():
        params_config[param_name] = {
            "default": param_info.get('default'),
            "min": param_info.get('min'),
            "max": param_info.get('max'),
            "step": param_info.get('step', 1),
            "type": param_info.get('type', 'int')
        }

    # 获取输入列
    inputs = metadata.get('inputs', ["close"])

    return {
        "parameters": params_config,
        "inputs": inputs
    }


def get_indicator_default_params(indicator_name: str) -> dict:
    """
    获取指标默认参数

    参数:
        indicator_name: 指标名称

    返回:
        dict: 默认参数字典
    """
    # 获取参数配置
    config = get_indicator_params_config(indicator_name)

    # 提取默认值
    default_params = {}
    for param_name, param_info in config.get("parameters", {}).items():
        default_params[param_name] = param_info.get("default")

    return default_params


def get_indicator_inputs(indicator_name: str) -> list:
    """
    获取指标所需的输入列

    参数:
        indicator_name: 指标名称

    返回:
        list: 输入列名列表
    """
    indicator_name = indicator_name.upper()

    # 处理指标别名
    if 'INDICATOR_ALIASES' in globals() and indicator_name in INDICATOR_ALIASES:
        indicator_name = INDICATOR_ALIASES[indicator_name]
    else:
        # 导入INDICATOR_ALIASES
        try:
            from core.indicator_service import INDICATOR_ALIASES
            if indicator_name in INDICATOR_ALIASES:
                indicator_name = INDICATOR_ALIASES[indicator_name]
        except ImportError:
            pass

    # 预定义的输入映射
    input_mapping = {
        'MA': ['close'],
        'SMA': ['close'],
        'EMA': ['close'],
        'MACD': ['close'],
        'RSI': ['close'],
        'BBANDS': ['close'],
        'BOLL': ['close'],
        'KDJ': ['high', 'low', 'close'],
        'STOCH': ['high', 'low', 'close'],
        'ADX': ['high', 'low', 'close'],
        'CCI': ['high', 'low', 'close'],
        'OBV': ['close', 'volume'],
        'ROC': ['close'],
        'ATR': ['high', 'low', 'close'],
        'SAR': ['high', 'low'],
        'WILLR': ['high', 'low', 'close'],
        'MOM': ['close'],
        'TRIX': ['close'],
        'CMF': ['high', 'low', 'close', 'volume'],
        'MFI': ['high', 'low', 'close', 'volume']
    }

    if indicator_name in input_mapping:
        return input_mapping[indicator_name]

    # 尝试从数据库获取指标定义
    try:
        from db.models.indicator_models import IndicatorDatabase
        import os

        db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'indicators.db')
        if os.path.exists(db_path):
            db = IndicatorDatabase(db_path)
            indicator = db.get_indicator_by_name(indicator_name)
            db.close()

            if indicator:
                # 根据指标实现判断输入
                for impl in indicator.implementations:
                    if impl.engine == 'talib':
                        # 大多数TA-Lib函数使用close
                        return ['close']
                    elif 'trends.calculate_' in impl.function_name:
                        if 'adx' in impl.function_name:
                            return ['high', 'low', 'close']
                        else:
                            return ['close']
                    elif 'oscillators.calculate_' in impl.function_name:
                        if 'kdj' in impl.function_name or 'stoch' in impl.function_name:
                            return ['high', 'low', 'close']
                        else:
                            return ['close']
                    elif 'volumes.calculate_' in impl.function_name:
                        return ['close', 'volume']
    except Exception as e:
        logger.warning(f"获取指标输入列失败: {str(e)}")

    # 默认返回close
    return ['close']
