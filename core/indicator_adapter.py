#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标适配器
用于将旧的指标计算接口适配到新的指标计算服务
"""

from loguru import logger
from core.unified_indicator_service import (
    get_unified_service,
    calculate_indicator,
    get_indicator_metadata,
    get_all_indicators_metadata,
    get_indicators_by_category,
    INDICATOR_ALIASES
)
from core.indicators.library.trends import calculate_ma
from core.indicators.library.oscillators import calculate_macd, calculate_rsi
import os
import sys
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

# Loguru 日志配置已在全局配置中设置，无需额外配置


def get_indicator_english_name(name: str) -> str:
    """
    根据中文指标名称获取英文名称

    Args:
        name: 中文指标名称

    Returns:
        英文指标名称
    """
    try:
        all_metadata = get_all_indicators_metadata()

        # 检查metadata的数据类型
        if isinstance(all_metadata, list):
            # 如果是列表格式（来自unified_indicator_service）
            for indicator_metadata in all_metadata:
                if indicator_metadata.get('display_name') == name or indicator_metadata.get('name') == name:
                    return indicator_metadata.get('english_name', name)
        elif isinstance(all_metadata, dict):
            # 如果是字典格式（来自indicator_service）
            for indicator_name, indicator_metadata in all_metadata.items():
                if indicator_metadata.get('display_name') == name:
                    return indicator_name
        else:
            logger.info(f"警告：unexpected metadata type: {type(all_metadata)}")

        # 如果没有找到匹配的指标，尝试直接映射
        name_mapping = {
            "移动平均线": "MA",
            "指数移动平均": "EMA",
            "布林带": "BBANDS",
            "相对强弱指标": "RSI",
            "随机指标": "STOCH",
            "MACD指标": "MACD",
            "指数平滑异同移动平均线": "MACD",
            "威廉指标": "WILLR",
            "平均方向指数": "ADX",
            "商品通道指数": "CCI",
            "动量指标": "MOM",
            "变动率": "ROC",
            "平均真实范围": "ATR"
        }

        if name in name_mapping:
            return name_mapping[name]

        # 如果仍然没有找到，返回原名称
        return name

    except Exception as e:
        logger.info(f"获取指标英文名称失败: {e}")
        # 使用备用映射
        backup_mapping = {
            "移动平均线": "MA",
            "相对强弱指标": "RSI",
            "布林带": "BBANDS",
            "MACD指标": "MACD"
        }
        return backup_mapping.get(name, name)


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
    result = calculate_macd(df, fastperiod=fast,
                            slowperiod=slow, signalperiod=signal)

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
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="MACD"),
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="MACD_signal"),
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="MACD_hist")
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
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="BOLL_mid"),
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="BOLL_upper"),
            pd.Series([float('nan')] * len(close),
                      index=close.index, name="BOLL_lower")
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


def get_talib_indicator_list() -> List[str]:
    """
    获取TA-Lib指标列表

    返回:
        List[str]: TA-Lib指标名称列表
    """
    try:
        # 尝试从新的指标系统获取
        all_metadata = get_all_indicators_metadata()

        # 检查返回的数据类型
        if isinstance(all_metadata, list):
            # 如果是列表格式（来自统一指标服务）
            # 获取技术指标，排除形态类
            talib_indicators = []
            for item in all_metadata:
                if item.get('is_builtin', True):
                    # 通过分类判断是否为形态指标
                    category = item.get('category', item.get('category_name', ''))
                    if category != '形态类':
                        indicator_name = item.get('display_name', item.get('name', ''))
                        if indicator_name:
                            talib_indicators.append(indicator_name)
        elif isinstance(all_metadata, dict):
            # 如果是字典格式（来自旧指标服务）
            talib_indicators = [name for name, meta in all_metadata.items()
                                if meta.get('is_builtin', True)]
        else:
            talib_indicators = []

        if talib_indicators:
            return sorted(talib_indicators)

        # 如果没有获取到，返回默认列表
        logger.warning("未获取到TA-Lib指标，使用默认列表")
        return [
            'MA', 'EMA', 'MACD', 'RSI', 'BBANDS', 'KDJ', 'CCI', 'ATR', 'OBV',
            'STOCH', 'WILLR', 'ROC', 'MOM', 'ADX', 'SAR', 'TRIX', 'MFI'
        ]

    except Exception as e:
        logger.error(f"获取TA-Lib指标列表失败: {e}")
        return ['MA', 'EMA', 'MACD', 'RSI', 'BBANDS']


def get_indicator_category_by_name(name: str) -> str:
    """
    根据指标名称获取指标分类

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


def get_talib_chinese_name(english_name: str) -> str:
    """
    获取TA-Lib指标的中文名称

    参数:
        english_name: 指标英文名称

    返回:
        str: 指标中文名称
    """
    # 获取指标元数据
    metadata = get_indicator_metadata(english_name)

    if metadata and 'display_name' in metadata:
        return metadata['display_name']

    # 如果没有找到，使用默认映射
    chinese_name_map = {
        'MA': '移动平均线',
        'EMA': '指数移动平均',
        'MACD': 'MACD指标',
        'RSI': '相对强弱指标',
        'BBANDS': '布林带',
        'KDJ': 'KDJ随机指标',
        'CCI': '商品通道指标',
        'ATR': '平均真实波幅',
        'OBV': '能量潮指标',
        'STOCH': '随机震荡指标',
        'WILLR': '威廉指标',
        'ROC': '变动率指标',
        'MOM': '动量指标',
        'ADX': '平均方向性指标',
        'SAR': '抛物线指标',
        'TRIX': 'TRIX指标',
        'MFI': '资金流量指标',
        'BOLL': '布林带',  # 别名
        'SMA': '简单移动平均',
        'WMA': '加权移动平均',
        'DEMA': '双重指数移动平均',
        'TEMA': '三重指数移动平均'
    }

    return chinese_name_map.get(english_name.upper(), english_name)


def get_indicator_params_config(english_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指标参数配置

    参数:
        english_name: 指标英文名称

    返回:
        Dict[str, Any]: 指标参数配置，如果不存在则返回None
    """
    try:
        # 获取指标元数据
        metadata = get_indicator_metadata(english_name)

        if not metadata:
            return None

        # 构建参数配置
        params_config = {}
        parameters = metadata.get('parameters', [])

        for param in parameters:
            if isinstance(param, dict):
                param_name = param.get('name', '')
                params_config[param_name] = {
                    'desc': param.get('display_name', param_name),
                    'default': param.get('default_value'),
                    'min': param.get('min_value'),
                    'max': param.get('max_value'),
                    'type': param.get('type', 'int')
                }

        return {
            'name': english_name,
            'display_name': metadata.get('display_name', english_name),
            'description': metadata.get('description', ''),
            'params': params_config
        }

    except Exception as e:
        logger.error(f"获取指标 {english_name} 参数配置失败: {e}")

        # 返回一些默认的参数配置
        default_configs = {
            'MA': {
                'name': 'MA',
                'display_name': '移动平均线',
                'description': '简单移动平均线',
                'params': {
                    'timeperiod': {'desc': '周期', 'default': 20, 'min': 1, 'max': 200, 'type': 'int'}
                }
            },
            'MACD': {
                'name': 'MACD',
                'display_name': 'MACD指标',
                'description': '移动平均收敛发散指标',
                'params': {
                    'fastperiod': {'desc': '快速周期', 'default': 12, 'min': 1, 'max': 100, 'type': 'int'},
                    'slowperiod': {'desc': '慢速周期', 'default': 26, 'min': 1, 'max': 100, 'type': 'int'},
                    'signalperiod': {'desc': '信号周期', 'default': 9, 'min': 1, 'max': 50, 'type': 'int'}
                }
            },
            'RSI': {
                'name': 'RSI',
                'display_name': '相对强弱指标',
                'description': '相对强弱指标',
                'params': {
                    'timeperiod': {'desc': '周期', 'default': 14, 'min': 1, 'max': 100, 'type': 'int'}
                }
            }
        }

        return default_configs.get(english_name.upper())


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
    if config:
        for param_name, param_info in config.get("params", {}).items():
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

        db_path = os.path.join(os.path.dirname(
            __file__), '..', 'db', 'indicators.db')
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


def get_all_indicators_by_category(use_chinese: bool = False) -> Dict[str, List[str]]:
    """
    获取按分类组织的所有指标列表，兼容旧接口

    参数:
        use_chinese: 是否使用中文分类名称

    返回:
        Dict[str, List[str]]: 分类名称到指标名称列表的映射
    """
    try:
        # 使用统一服务
        service = get_unified_service()
        categories = service.get_all_categories()

        result = {}
        for category in categories:
            category_key = category['display_name'] if use_chinese else category['name']
            indicators = service.get_indicators_by_category(category['name'])
            result[category_key] = [indicator['name'] for indicator in indicators]

        # 如果没有获取到指标，返回默认分类
        if not any(result.values()):
            logger.warning("未获取到指标数据，使用默认指标分类")
            if use_chinese:
                return {
                    "趋势类": ["MA", "EMA", "BBANDS", "SAR"],
                    "震荡类": ["RSI", "MACD", "STOCH", "CCI", "WILLR"],
                    "成交量类": ["OBV", "AD", "ADOSC"],
                    "波动性类": ["ATR", "NATR", "TRANGE"],
                    "其他": ["ROC", "MOM", "TRIX"]
                }
            else:
                return {
                    "trend": ["MA", "EMA", "BBANDS", "SAR"],
                    "oscillator": ["RSI", "MACD", "STOCH", "CCI", "WILLR"],
                    "volume": ["OBV", "AD", "ADOSC"],
                    "volatility": ["ATR", "NATR", "TRANGE"],
                    "other": ["ROC", "MOM", "TRIX"]
                }

        return result

    except Exception as e:
        logger.error(f"获取指标分类失败: {e}")
        # 返回默认分类
        if use_chinese:
            return {
                "趋势类": ["MA", "EMA", "MACD", "BBANDS"],
                "震荡类": ["RSI", "KDJ", "CCI"],
                "成交量类": ["OBV"],
                "其他": ["ATR", "ROC"]
            }
        else:
            return {
                "trend": ["MA", "EMA", "MACD", "BBANDS"],
                "oscillator": ["RSI", "KDJ", "CCI"],
                "volume": ["OBV"],
                "other": ["ATR", "ROC"]
            }
