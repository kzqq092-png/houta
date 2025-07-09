#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指标计算服务
作为新的指标计算核心引擎，从数据库中获取指标定义并进行计算
"""

from db.models.indicator_models import (
    IndicatorDatabase,
    Indicator,
    IndicatorParameter,
    IndicatorImplementation
)
import os
import sys
import json
import importlib
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from functools import lru_cache

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# 指标数据库文件路径
INDICATOR_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'indicators.db')

# 设置日志
logger = logging.getLogger('indicator_service')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# 尝试导入TA-Lib
try:
    talib = importlib.import_module('talib')
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib 未安装或无法导入，将使用 pandas 实现")


class IndicatorService:
    """指标计算服务类"""

    def __init__(self, db_path: str = INDICATOR_DB_PATH):
        """
        初始化指标计算服务

        参数:
            db_path: 指标数据库文件路径
        """
        self.db_path = db_path
        self.db = IndicatorDatabase(db_path)
        self._custom_functions = {}  # 存储自定义函数

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

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
    def get_indicator(self, name: str) -> Optional[Indicator]:
        """
        获取指标定义

        参数:
            name: 指标名称

        返回:
            Indicator: 指标对象，如果不存在则返回None
        """
        return self.db.get_indicator_by_name(name)

    def get_all_indicators(self) -> List[Indicator]:
        """
        获取所有指标定义

        返回:
            List[Indicator]: 指标对象列表
        """
        return self.db.get_all_indicators()

    def get_indicators_by_category(self, category_name: str) -> List[Indicator]:
        """
        获取指定分类的所有指标

        参数:
            category_name: 分类名称

        返回:
            List[Indicator]: 指标对象列表
        """
        category = self.db.get_category_by_name(category_name)
        if not category:
            return []
        return self.db.get_indicators_by_category(category.id)

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
            'name': indicator.name,
            'display_name': indicator.display_name,
            'description': indicator.description,
            'formula': indicator.formula,
            'params': [param.to_dict() for param in indicator.parameters],
            'output_names': indicator.output_names
        }

    def get_all_indicators_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有指标的元数据

        返回:
            Dict: 指标名称到元数据的映射
        """
        indicators = self.get_all_indicators()
        return {
            indicator.name: self.get_indicator_metadata(indicator.name)
            for indicator in indicators
        }

    def get_indicator_default_params(self, name: str) -> Dict[str, Any]:
        """
        获取指标默认参数

        参数:
            name: 指标名称

        返回:
            Dict: 参数名称到默认值的映射，如果指标不存在则返回空字典
        """
        indicator = self.get_indicator(name)
        if not indicator:
            return {}

        return {
            param.name: param.default_value
            for param in indicator.parameters
        }

    def _get_best_implementation(self, indicator: Indicator) -> Optional[IndicatorImplementation]:
        """
        获取最佳实现

        参数:
            indicator: 指标对象

        返回:
            IndicatorImplementation: 指标实现对象，如果没有可用的实现则返回None
        """
        if not indicator.implementations:
            return None

        # 首先尝试获取默认实现
        default_impl = next((impl for impl in indicator.implementations if impl.is_default), None)
        if default_impl:
            return default_impl

        # 如果没有默认实现，根据可用性选择实现
        if TALIB_AVAILABLE:
            talib_impl = next((impl for impl in indicator.implementations if impl.engine == 'talib'), None)
            if talib_impl:
                return talib_impl

        # 如果没有TA-Lib或没有TA-Lib实现，尝试pandas实现
        pandas_impl = next((impl for impl in indicator.implementations if impl.engine == 'pandas'), None)
        if pandas_impl:
            return pandas_impl

        # 如果还没有找到，返回第一个实现
        return indicator.implementations[0]

    def _compile_custom_function(self, code: str, function_name: str) -> Callable:
        """
        编译自定义函数

        参数:
            code: 函数代码
            function_name: 函数名称

        返回:
            Callable: 编译后的函数
        """
        # 如果已经编译过，直接返回
        if function_name in self._custom_functions:
            return self._custom_functions[function_name]

        # 编译代码
        namespace = {'np': np, 'pd': pd}
        exec(code, namespace)

        # 获取函数
        if function_name not in namespace:
            raise ValueError(f"函数 {function_name} 未在代码中定义")

        # 缓存函数
        self._custom_functions[function_name] = namespace[function_name]

        return namespace[function_name]

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
        # 获取指标定义
        indicator = self.get_indicator(name)
        if not indicator:
            logger.error(f"指标 {name} 不存在")
            return df

        # 获取参数
        if params is None:
            params = self.get_indicator_default_params(name)
        else:
            # 合并默认参数
            default_params = self.get_indicator_default_params(name)
            for key, value in default_params.items():
                if key not in params:
                    params[key] = value

        # 获取最佳实现
        impl = self._get_best_implementation(indicator)
        if not impl:
            logger.error(f"指标 {name} 没有可用的实现")
            return df

        try:
            # 创建结果的副本，避免修改原始数据
            result = df.copy()

            # 根据实现引擎计算指标
            if impl.engine == 'talib':
                if not TALIB_AVAILABLE:
                    logger.warning(f"TA-Lib 未安装，无法计算指标 {name}")
                    return result

                # 获取TA-Lib函数
                talib_func = getattr(talib, impl.function_name)

                # 准备输入参数
                call_args = {}

                # 检查函数签名，确定需要哪些输入列
                import inspect
                try:
                    sig = inspect.signature(talib_func)

                    for param_name in sig.parameters:
                        # 如果是OHLCV列，从DataFrame中获取
                        if param_name.lower() in ['open', 'high', 'low', 'close', 'volume']:
                            col_name = param_name.lower()
                            if col_name in result.columns:
                                call_args[param_name] = result[col_name].values
                            else:
                                logger.warning(f"指标 {name} 需要列 {col_name}，但DataFrame中不存在")
                                return result
                        # 如果是计算参数，从params中获取
                        elif param_name in params:
                            call_args[param_name] = params[param_name]
                except:
                    # 如果无法获取函数签名，使用默认参数
                    pass

                # 如果没有参数，尝试使用默认调用方式
                if not call_args or ('close' not in call_args and impl.function_name in ['MA', 'SMA']):
                    if 'close' in result.columns:
                        call_args['close'] = result['close'].values
                        for key, value in params.items():
                            call_args[key] = value
                    else:
                        logger.error(f"无法确定指标 {name} 的输入参数")
                        return result

                # 执行计算
                try:
                    # 确保我们有close数据
                    if 'close' not in call_args and 'close' in result.columns:
                        call_args['close'] = result['close'].values

                    # 根据指标类型选择调用方式
                    if impl.function_name in ['MA', 'SMA', 'RSI', 'MACD', 'OBV', 'ADX']:
                        # 这些函数第一个参数是close
                        if 'close' not in call_args:
                            logger.error(f"调用TA-Lib函数 {impl.function_name} 时缺少close参数")
                            return result

                        # 提取close参数和其他参数
                        close_data = call_args['close']
                        other_params = {}
                        for k, v in params.items():
                            if k != 'close':
                                other_params[k] = v

                        # 调用函数
                        talib_result = talib_func(close_data, **other_params)

                    elif impl.function_name in ['BBANDS', 'ATR', 'CCI', 'STOCH']:
                        # 这些函数可能需要high, low, close等多个输入
                        if impl.function_name == 'BBANDS':
                            if 'close' not in call_args:
                                logger.error(f"调用TA-Lib函数 {impl.function_name} 时缺少close参数")
                                return result
                            talib_result = talib_func(
                                call_args['close'],
                                timeperiod=params.get('timeperiod', 20),
                                nbdevup=params.get('nbdevup', 2.0),
                                nbdevdn=params.get('nbdevdn', 2.0)
                            )

                        elif impl.function_name == 'ATR':
                            if not all(k in call_args for k in ['high', 'low', 'close']):
                                logger.error(f"调用TA-Lib函数 {impl.function_name} 时缺少必要参数")
                                return result
                            talib_result = talib_func(
                                call_args['high'],
                                call_args['low'],
                                call_args['close'],
                                timeperiod=params.get('timeperiod', 14)
                            )

                        elif impl.function_name == 'CCI':
                            if not all(k in call_args for k in ['high', 'low', 'close']):
                                logger.error(f"调用TA-Lib函数 {impl.function_name} 时缺少必要参数")
                                return result
                            talib_result = talib_func(
                                call_args['high'],
                                call_args['low'],
                                call_args['close'],
                                timeperiod=params.get('timeperiod', 14)
                            )

                        elif impl.function_name == 'STOCH':
                            if not all(k in call_args for k in ['high', 'low', 'close']):
                                logger.error(f"调用TA-Lib函数 {impl.function_name} 时缺少必要参数")
                                return result
                            talib_result = talib_func(
                                call_args['high'],
                                call_args['low'],
                                call_args['close'],
                                fastk_period=params.get('fastk_period', 5),
                                slowk_period=params.get('slowk_period', 3),
                                slowk_matype=params.get('slowk_matype', 0),
                                slowd_period=params.get('slowd_period', 3),
                                slowd_matype=params.get('slowd_matype', 0)
                            )

                            # 特殊处理KDJ指标
                            if name == 'KDJ' and isinstance(talib_result, tuple) and len(talib_result) == 2:
                                k, d = talib_result
                                j = 3 * k - 2 * d  # 计算J值
                                result['K'] = pd.Series(k, index=result.index)
                                result['D'] = pd.Series(d, index=result.index)
                                result['J'] = pd.Series(j, index=result.index)
                                # 跳过后面的处理
                                return result

                    else:
                        # 对于其他不常见的函数，尝试使用通用方法
                        talib_result = talib_func(**call_args)

                except Exception as e:
                    logger.error(f"调用TA-Lib函数 {impl.function_name} 时发生错误: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return result

                # 处理返回结果
                if isinstance(talib_result, tuple):
                    # 如果返回多个值，使用output_names命名
                    for i, output_name in enumerate(indicator.output_names):
                        if i < len(talib_result):
                            result[output_name] = talib_result[i]
                else:
                    # 如果只返回一个值，使用第一个output_name命名
                    if indicator.output_names:
                        result[indicator.output_names[0]] = talib_result

            elif impl.engine == 'pandas' or impl.engine == 'custom':
                # 编译自定义函数或导入自定义模块
                if impl.engine == 'pandas':
                    # 编译自定义函数
                    func = self._compile_custom_function(impl.code, impl.function_name)
                else:  # custom
                    # 导入自定义模块
                    try:
                        # 执行导入代码
                        exec(impl.code, globals())

                        # 尝试直接导入函数
                        module_parts = impl.function_name.split('.')
                        if len(module_parts) > 1:
                            # 如果是模块路径，如'core.indicators.library.trends.calculate_ma'
                            module_path = '.'.join(module_parts[:-1])
                            func_name = module_parts[-1]
                            module = importlib.import_module(module_path)
                            func = getattr(module, func_name)
                        else:
                            # 如果只是函数名，尝试从globals()中获取
                            if impl.function_name in globals():
                                func = globals()[impl.function_name]
                            else:
                                # 尝试从locals()中获取
                                func = locals()[impl.function_name]
                    except Exception as e:
                        logger.error(f"导入自定义模块时发生错误: {str(e)}")
                        logger.error(f"代码: {impl.code}")
                        logger.error(f"函数名: {impl.function_name}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return result

                # 准备输入参数
                call_args = {}

                # 检查函数签名，确定需要哪些输入列
                import inspect
                sig = inspect.signature(func)

                for param_name in sig.parameters:
                    # 如果是df参数，传入整个DataFrame
                    if param_name == 'df':
                        call_args[param_name] = result
                    # 如果是OHLCV列，从DataFrame中获取
                    elif param_name.lower() in ['open', 'high', 'low', 'close', 'volume']:
                        col_name = param_name.lower()
                        if col_name in result.columns:
                            call_args[param_name] = result[col_name]
                        else:
                            logger.warning(f"指标 {name} 需要列 {col_name}，但DataFrame中不存在")
                            return result
                    # 如果是计算参数，从params中获取
                    elif param_name in params:
                        call_args[param_name] = params[param_name]

                # 调用自定义函数计算指标
                if not call_args and 'df' not in sig.parameters:
                    # 如果没有参数，尝试使用默认调用方式
                    if 'close' in result.columns:
                        call_args['close'] = result['close']
                        for key, value in params.items():
                            call_args[key] = value
                    else:
                        logger.error(f"无法确定指标 {name} 的输入参数")
                        return result

                # 执行计算
                custom_result = func(**call_args)

                # 处理返回结果
                if isinstance(custom_result, pd.DataFrame):
                    # 如果返回的是DataFrame，合并到结果中
                    for output_name in indicator.output_names:
                        if output_name in custom_result.columns:
                            result[output_name] = custom_result[output_name]
                elif isinstance(custom_result, tuple):
                    # 如果返回多个值，使用output_names命名
                    for i, output_name in enumerate(indicator.output_names):
                        if i < len(custom_result):
                            result[output_name] = custom_result[i]
                else:
                    # 如果只返回一个值，使用第一个output_name命名
                    if indicator.output_names:
                        result[indicator.output_names[0]] = custom_result

            else:
                logger.error(f"不支持的实现引擎: {impl.engine}")

            return result

        except Exception as e:
            logger.error(f"计算指标 {name} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df

    def register_indicators(self, indicators_list: List[Dict[str, Any]], source: str) -> List[int]:
        """
        注册指标列表

        参数:
            indicators_list: 指标定义列表
            source: 指标来源（通常是插件名称）

        返回:
            List[int]: 新增指标的ID列表
        """
        indicator_ids = []

        for indicator_dict in indicators_list:
            try:
                # 创建指标对象
                indicator = Indicator(
                    id=None,  # 自动分配ID
                    name=indicator_dict.get('name'),
                    display_name=indicator_dict.get('display_name'),
                    category_id=indicator_dict.get('category_id', 6),  # 默认为"其他"类别
                    description=indicator_dict.get('description', ''),
                    formula=indicator_dict.get('formula', ''),
                    is_builtin=False,  # 插件指标不是内置的
                    source=source
                )

                # 处理参数
                if 'parameters' in indicator_dict:
                    for param_dict in indicator_dict['parameters']:
                        param = IndicatorParameter(
                            name=param_dict.get('name'),
                            description=param_dict.get('description', ''),
                            type=param_dict.get('type', 'int'),
                            default_value=param_dict.get('default_value'),
                            min_value=param_dict.get('min_value'),
                            max_value=param_dict.get('max_value'),
                            step=param_dict.get('step'),
                            choices=param_dict.get('choices')
                        )
                        indicator.parameters.append(param)

                # 处理实现
                if 'implementations' in indicator_dict:
                    for impl_dict in indicator_dict['implementations']:
                        impl = IndicatorImplementation(
                            engine=impl_dict.get('engine', 'custom'),
                            function_name=impl_dict.get('function_name'),
                            is_default=impl_dict.get('is_default', True)
                        )
                        indicator.implementations.append(impl)

                # 处理输出列名
                if 'output_names' in indicator_dict:
                    indicator.output_names = indicator_dict['output_names']

                # 添加到数据库
                indicator_id = self.db.add_indicator(indicator)
                indicator_ids.append(indicator_id)
                logger.info(f"成功注册指标: {indicator.name} (ID: {indicator_id})")

            except Exception as e:
                logger.error(f"注册指标 {indicator_dict.get('name', 'unknown')} 时发生错误: {str(e)}")

        return indicator_ids


# 创建全局实例
indicator_service = IndicatorService()


def calculate_indicator(df: pd.DataFrame, indicator_name: str, params: dict = None) -> pd.DataFrame:
    """
    计算指标

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
    if indicator_name in INDICATOR_ALIASES:
        original_name = indicator_name
        indicator_name = INDICATOR_ALIASES[indicator_name]
        logger.info(f"使用别名: {original_name} -> {indicator_name}")

    # 如果没有提供参数，使用默认参数
    if params is None:
        from core.indicator_adapter import get_indicator_default_params
        params = get_indicator_default_params(indicator_name)

    # 根据指标名称调用相应的计算函数
    if indicator_name == 'MA':
        from core.indicators.library.trends import calculate_ma
        return calculate_ma(df, **params)
    elif indicator_name == 'MACD':
        from core.indicators.library.oscillators import calculate_macd
        return calculate_macd(df, **params)
    elif indicator_name == 'RSI':
        from core.indicators.library.oscillators import calculate_rsi
        return calculate_rsi(df, **params)
    elif indicator_name == 'BBANDS' or indicator_name == 'BOLL':
        from core.indicators.library.trends import calculate_bbands
        return calculate_bbands(df, **params)
    elif indicator_name == 'KDJ':
        from core.indicators.library.oscillators import calculate_kdj
        return calculate_kdj(df, **params)
    elif indicator_name == 'ADX':
        from core.indicators.library.trends import calculate_adx
        return calculate_adx(df, **params)
    elif indicator_name == 'OBV':
        from core.indicators.library.volumes import calculate_obv
        return calculate_obv(df)
    elif indicator_name == 'CCI':
        from core.indicators.library.oscillators import calculate_cci
        return calculate_cci(df, **params)
    elif indicator_name == 'STOCH':
        from core.indicators.library.oscillators import calculate_stoch
        return calculate_stoch(df, **params)
    elif indicator_name == 'EMA':
        from core.indicators.library.momentum import calculate_ema
        return calculate_ema(df, **params)
    elif indicator_name == 'ROC':
        from core.indicators.library.momentum import calculate_roc
        return calculate_roc(df, **params)
    else:
        # 尝试使用TA-Lib
        try:
            if TALIB_AVAILABLE:
                func = getattr(talib, indicator_name)
                result = df.copy()

                # 根据指标的输入需求选择合适的数据列
                from core.indicator_adapter import get_indicator_inputs
                required_inputs = get_indicator_inputs(indicator_name)
                input_data = []

                for input_name in required_inputs:
                    if input_name.lower() in df.columns:
                        input_data.append(df[input_name.lower()].values)
                    else:
                        raise ValueError(f"指标 {indicator_name} 需要 {input_name} 数据，但在DataFrame中找不到")

                # 计算指标
                outputs = func(*input_data, **params)

                # 如果输出是元组，说明指标有多个输出
                if isinstance(outputs, tuple):
                    for i, output in enumerate(outputs):
                        output_name = f"{indicator_name}_{i}"
                        result[output_name] = pd.Series(output, index=df.index)
                else:
                    result[indicator_name] = pd.Series(outputs, index=df.index)

                return result
            else:
                raise ValueError(f"找不到指标计算方法: {indicator_name}")
        except (AttributeError, ValueError) as e:
            logger.warning(f"找不到指标计算方法: {indicator_name}")
            raise ValueError(f"找不到指标计算方法: {indicator_name}")


def get_indicator_metadata(name: str) -> Optional[Dict[str, Any]]:
    """
    获取指标元数据的便捷函数

    参数:
        name: 指标名称

    返回:
        Dict: 指标元数据，如果不存在则返回None
    """
    # 检查指标别名
    if name in INDICATOR_ALIASES:
        actual_name = INDICATOR_ALIASES[name]
        logger.debug(f"使用别名获取元数据: {name} -> {actual_name}")
        name = actual_name

    return indicator_service.get_indicator_metadata(name)


def get_all_indicators_metadata() -> Dict[str, Dict[str, Any]]:
    """
    获取所有指标的元数据的便捷函数

    返回:
        Dict: 指标名称到元数据的映射
    """
    service = IndicatorService()
    indicators = service.get_all_indicators()
    result = {indicator.name: indicator.to_dict() for indicator in indicators}

    # 添加别名指标
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
    service = IndicatorService()
    indicators = service.get_indicators_by_category(category_name)
    return [indicator.to_dict() for indicator in indicators]


# 添加对常用指标的别名支持
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
