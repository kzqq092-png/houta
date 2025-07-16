#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标计算服务（重构版）
基于统一数据库hikyuu_system.db的指标计算服务，保持向后兼容性
"""

from core.unified_indicator_service import (
    UnifiedIndicatorService,
    get_unified_service,
    TALIB_AVAILABLE
)
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from functools import lru_cache

# 设置日志
logger = logging.getLogger('indicator_service')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# 统一数据库文件路径
UNIFIED_DB_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'db', 'hikyuu_system.db')


class IndicatorService:
    """指标计算服务类（重构版 - 使用统一数据库）"""

    def __init__(self, db_path: str = UNIFIED_DB_PATH):
        """
        初始化指标计算服务

        参数:
            db_path: 统一数据库文件路径
        """
        self.db_path = db_path
        # 使用统一指标服务
        self.unified_service = UnifiedIndicatorService(db_path)
        self._custom_functions = {}  # 存储自定义函数

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'unified_service') and self.unified_service:
            self.unified_service.close()

    def __del__(self):
        """析构函数，确保数据库连接被关闭"""
        self.close()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()

    @lru_cache(maxsize=128)
    def get_indicator(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指标定义

        参数:
            name: 指标名称

        返回:
            Dict: 指标对象，如果不存在则返回None
        """
        return self.unified_service.get_indicator(name)

    def get_all_indicators(self) -> List[Dict[str, Any]]:
        """
        获取所有指标定义

        返回:
            List[Dict]: 指标对象列表
        """
        return self.unified_service.get_all_indicators()

    def get_indicators_by_category(self, category_name: str) -> List[Dict[str, Any]]:
        """
        获取指定分类的所有指标

        参数:
            category_name: 分类名称

        返回:
            List[Dict]: 指标对象列表
        """
        return self.unified_service.get_indicators_by_category(category_name)

    def get_indicator_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指标元数据

        参数:
            name: 指标名称

        返回:
            Dict: 指标元数据，如果不存在则返回None
        """
        indicator = self.get_indicator(name)
        if not indicator:
            return None

        return {
            'name': indicator['name'],
            'display_name': indicator['display_name'],
            'description': indicator['description'],
            'formula': indicator['formula'],
            'params': [param for param in indicator['parameters']],
            'output_names': indicator['output_names']
        }

    def get_all_indicators_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有指标的元数据

        返回:
            Dict: 指标名称到元数据的映射
        """
        indicators = self.get_all_indicators()
        result = {}

        for indicator in indicators:
            name = indicator['name']
            result[name] = {
                'name': name,
                'display_name': indicator['display_name'],
                'description': indicator['description'],
                'formula': indicator['formula'],
                'params': indicator['parameters'],
                'output_names': indicator['output_names']
            }

        return result

    def get_indicator_default_params(self, name: str) -> Dict[str, Any]:
        """
        获取指标默认参数

        参数:
            name: 指标名称

        返回:
            Dict: 参数名称到默认值的映射，如果指标不存在则返回空字典
        """
        return self.unified_service.get_indicator_default_params(name)

    def calculate_indicator(self, name: str, df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        计算指标

        参数:
            name: 指标名称
            df: 输入DataFrame，包含OHLCV数据
            params: 计算参数，如果为None则使用默认参数

        返回:
            DataFrame: 添加了指标列的DataFrame
        """
        # 使用统一服务计算指标
        return self.unified_service.calculate_indicator(name, df, params)

    def register_indicators(self, indicators_list: List[Dict[str, Any]], source: str) -> List[int]:
        """
        注册指标列表（保留接口兼容性）

        参数:
            indicators_list: 指标定义列表
            source: 指标来源

        返回:
            List[int]: 新增指标的ID列表
        """
        # 这个功能在新系统中暂时不实现，返回空列表
        logger.warning("register_indicators 功能在新系统中暂未实现")
        return []


# 创建全局实例
indicator_service = IndicatorService()


def calculate_indicator(df: pd.DataFrame, indicator_name: str, params: dict = None) -> pd.DataFrame:
    """
    计算指标的便捷函数

    参数:
        df: 包含行情数据的DataFrame
        indicator_name: 指标名称
        params: 指标参数

    返回:
        DataFrame: 添加了指标列的DataFrame
    """
    # 标准化指标名称
    indicator_name = indicator_name.upper()

    # 处理指标别名
    from core.unified_indicator_service import INDICATOR_ALIASES, resolve_indicator_alias
    indicator_name = resolve_indicator_alias(indicator_name)

    # 使用全局服务实例计算指标
    service = get_unified_service()
    return service.calculate_indicator(indicator_name, df, params)


def get_indicator_metadata(name: str) -> Optional[Dict[str, Any]]:
    """
    获取指标元数据的便捷函数

    参数:
        name: 指标名称

    返回:
        Dict: 指标元数据，如果不存在则返回None
    """
    from core.unified_indicator_service import resolve_indicator_alias
    name = resolve_indicator_alias(name)

    service = get_unified_service()
    return service.get_indicator(name)


def get_all_indicators_metadata() -> Dict[str, Dict[str, Any]]:
    """
    获取所有指标的元数据的便捷函数

    返回:
        Dict: 指标名称到元数据的映射
    """
    service = get_unified_service()
    indicators = service.get_all_indicators()

    result = {}
    for indicator in indicators:
        name = indicator['name']
        result[name] = indicator

    # 添加别名指标
    from core.unified_indicator_service import INDICATOR_ALIASES
    for alias, actual_name in INDICATOR_ALIASES.items():
        if actual_name in result and alias not in result:
            result[alias] = result[actual_name].copy()
            result[alias]['name'] = alias
            result[alias]['is_alias'] = True
            result[alias]['alias_of'] = actual_name

    return result


def get_indicators_by_category(category_name: str) -> List[Dict[str, Any]]:
    """
    获取指定分类下的所有指标的元数据

    参数:
        category_name: 分类名称

    返回:
        List[Dict[str, Any]]: 指标元数据列表
    """
    service = get_unified_service()
    return service.get_indicators_by_category(category_name)


def get_indicator_categories() -> List[str]:
    """
    获取所有指标分类

    返回:
        List[str]: 分类名称列表
    """
    service = get_unified_service()
    try:
        categories = service.get_all_categories()
        return [category['name'] for category in categories]
    except Exception as e:
        logger.error(f"获取指标分类失败: {e}")
        return ['trend', 'oscillator', 'volume', 'volatility', 'pattern', 'momentum', 'other']


def get_indicators_by_categories() -> Dict[str, List[Dict[str, Any]]]:
    """
    获取按分类组织的所有指标

    返回:
        Dict[str, List[Dict]]: 分类名称到指标列表的映射
    """
    service = get_unified_service()
    try:
        categories = service.get_all_categories()
        result = {}

        for category in categories:
            category_name = category['name']
            category_display_name = category['display_name']

            indicators = service.get_indicators_by_category(category_name)
            result[category_display_name] = [
                {
                    'name': indicator['name'],
                    'display_name': indicator['display_name'],
                    'description': indicator['description'],
                    'formula': indicator['formula'],
                    'params': indicator['parameters'],
                    'output_names': indicator['output_names']
                }
                for indicator in indicators
            ]

        return result
    except Exception as e:
        logger.error(f"获取分类指标失败: {e}")
        # 返回默认分类结构
        return {
            '趋势类': [],
            '震荡类': [],
            '成交量类': [],
            '波动性类': [],
            '形态类': [],
            '动量类': [],
            '其他': []
        }


def get_talib_category() -> Dict[str, List[str]]:
    """
    获取TA-Lib指标分类

    返回:
        Dict[str, List[str]]: TA-Lib指标分类
    """
    if not TALIB_AVAILABLE:
        return {}

    try:
        # 使用分类系统
        service = get_unified_service()
        categories = service.get_all_categories()
        result = {}

        for category in categories:
            category_name = category['display_name']
            indicators = service.get_indicators_by_category(category['name'])

            # 过滤出有TA-Lib实现的指标
            talib_indicators = []
            for indicator in indicators:
                for impl in indicator.get('implementations', []):
                    if impl['engine'] == 'talib':
                        talib_indicators.append(indicator['name'])
                        break

            if talib_indicators:
                result[category_name] = talib_indicators

        return result
    except Exception as e:
        logger.error(f"获取TA-Lib分类失败: {e}")
        return {}


# 指标别名映射（保持向后兼容）
INDICATOR_ALIASES = {
    'SMA': 'MA',
    'STOCH': 'KDJ',
    'ADX': 'ADX',
    'EMA': 'EMA',
    'WMA': 'WMA',
    'DEMA': 'DEMA',
    'TEMA': 'TEMA',
    'TRIMA': 'TRIMA',
    'KAMA': 'KAMA',
    'MAMA': 'MAMA',
    'T3': 'T3',
    'OBV': 'OBV',
    'CCI': 'CCI',
    'RSI': 'RSI',
    'MACD': 'MACD',
    'MOM': 'MOM',
    'ROC': 'ROC',
    'WILLR': 'WILLR',
    'BBANDS': 'BOLL',
    'BOLL': 'BBANDS',
    'ATR': 'ATR',
    'SAR': 'SAR',
    'TRIX': 'TRIX',
    'CMF': 'CMF',
    'MFI': 'MFI',
    # 添加常见的中文名称映射
    '移动平均线': 'MA',
    '指数移动平均': 'EMA',
    '随机指标': 'STOCH',
    '平均方向性指标': 'ADX',
    '能量潮指标': 'OBV',
    '商品通道指标': 'CCI',
    '相对强弱指标': 'RSI',
    'MACD指标': 'MACD',
    '布林带': 'BBANDS'
}
