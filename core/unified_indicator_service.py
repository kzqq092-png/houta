#!/usr/bin/env python3
"""
统一指标服务
整合技术指标和形态识别功能，使用 hikyuu_system.db 作为唯一数据源
支持指标计算、形态识别、参数管理等全部功能
"""

import os
import sys
import json
import sqlite3
import logging
import numpy as np
import pandas as pd
import importlib
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from functools import lru_cache
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 设置日志
logger = logging.getLogger('unified_indicator_service')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

# 统一数据库路径
UNIFIED_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'hikyuu_system.db')

# 尝试导入TA-Lib
try:
    talib = importlib.import_module('talib')
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib 未安装或无法导入，将使用自定义实现")


class UnifiedIndicatorService:
    """统一指标服务类 - 支持技术指标和形态识别"""

    def __init__(self, db_path: str = UNIFIED_DB_PATH):
        """
        初始化统一指标服务

        参数:
            db_path: 统一数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._custom_functions = {}  # 存储自定义函数缓存
        self._indicators_cache = {}  # 指标元数据缓存
        self._patterns_cache = {}   # 形态元数据缓存
        self._init_connection()

    def _init_connection(self):
        """初始化数据库连接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 使用字典式访问
            logger.info(f"✅ 连接到统一数据库: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {str(e)}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __del__(self):
        """析构函数"""
        self.close()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()

    # ==================== 基础查询方法 ====================

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有分类"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, display_name, description, parent_id, sort_order
                FROM indicator_categories 
                WHERE is_active = 1 
                ORDER BY sort_order, id
            ''')

            categories = []
            for row in cursor.fetchall():
                categories.append({
                    'id': row['id'],
                    'name': row['name'],
                    'display_name': row['display_name'],
                    'description': row['description'],
                    'parent_id': row['parent_id'],
                    'sort_order': row['sort_order']
                })

            return categories
        except Exception as e:
            logger.error(f"获取分类失败: {str(e)}")
            return []

    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取分类"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, display_name, description, parent_id, sort_order
                FROM indicator_categories 
                WHERE name = ? AND is_active = 1
            ''', (name,))

            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'display_name': row['display_name'],
                    'description': row['description'],
                    'parent_id': row['parent_id'],
                    'sort_order': row['sort_order']
                }
            return None
        except Exception as e:
            logger.error(f"获取分类失败: {str(e)}")
            return None

    # ==================== 技术指标相关方法 ====================

    @lru_cache(maxsize=128)
    def get_indicator(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指标定义"""
        if name in self._indicators_cache:
            return self._indicators_cache[name]

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT i.*, c.name as category_name, c.display_name as category_display_name
                FROM indicator i
                LEFT JOIN indicator_categories c ON i.category_id = c.id
                WHERE i.name = ? AND i.is_active = 1
            ''', (name,))

            row = cursor.fetchone()
            if not row:
                return None

            # 获取参数
            cursor.execute('''
                SELECT name, description, param_type, default_value, min_value, 
                       max_value, step_value, choices, is_required, sort_order
                FROM indicator_parameters 
                WHERE indicator_id = ? 
                ORDER BY sort_order, id
            ''', (row['id'],))

            parameters = []
            for param_row in cursor.fetchall():
                param = {
                    'name': param_row['name'],
                    'description': param_row['description'],
                    'type': param_row['param_type'],
                    'default_value': json.loads(param_row['default_value']),
                    'is_required': bool(param_row['is_required']),
                    'sort_order': param_row['sort_order']
                }

                # 可选字段
                for field in ['min_value', 'max_value', 'step_value', 'choices']:
                    if param_row[field]:
                        param[field] = json.loads(param_row[field])

                parameters.append(param)

            # 获取实现
            cursor.execute('''
                SELECT engine, function_name, implementation_code, is_default, 
                       priority, performance_score, is_active
                FROM indicator_implementations 
                WHERE indicator_id = ? AND is_active = 1
                ORDER BY priority DESC, is_default DESC
            ''', (row['id'],))

            implementations = []
            for impl_row in cursor.fetchall():
                implementations.append({
                    'engine': impl_row['engine'],
                    'function_name': impl_row['function_name'],
                    'code': impl_row['implementation_code'],
                    'is_default': bool(impl_row['is_default']),
                    'priority': impl_row['priority'],
                    'performance_score': impl_row['performance_score']
                })

            indicator = {
                'id': row['id'],
                'name': row['name'],
                'display_name': row['display_name'],
                'category_id': row['category_id'],
                'category_name': row['category_name'],
                'category_display_name': row['category_display_name'],
                'description': row['description'],
                'formula': row['formula'],
                'output_names': json.loads(row['output_names']) if row['output_names'] else [],
                'version': row['version'],
                'is_builtin': bool(row['is_builtin']),
                'parameters': parameters,
                'implementations': implementations,
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

            # 缓存结果
            self._indicators_cache[name] = indicator
            return indicator

        except Exception as e:
            logger.error(f"获取指标 {name} 失败: {str(e)}")
            return None

    def get_all_indicators(self) -> List[Dict[str, Any]]:
        """获取所有指标定义"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name FROM indicator 
                WHERE is_active = 1 
                ORDER BY name
            ''')

            indicators = []
            for row in cursor.fetchall():
                indicator = self.get_indicator(row['name'])
                if indicator:
                    indicators.append(indicator)

            return indicators
        except Exception as e:
            logger.error(f"获取所有指标失败: {str(e)}")
            return []

    def get_indicators_by_category(self, category_name: str) -> List[Dict[str, Any]]:
        """获取指定分类的所有指标"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT i.name
                FROM indicator i
                LEFT JOIN indicator_categories c ON i.category_id = c.id
                WHERE c.name = ? AND i.is_active = 1
                ORDER BY i.name
            ''', (category_name,))

            indicators = []
            for row in cursor.fetchall():
                indicator = self.get_indicator(row['name'])
                if indicator:
                    indicators.append(indicator)

            return indicators
        except Exception as e:
            logger.error(f"获取分类 {category_name} 的指标失败: {str(e)}")
            return []

    def get_indicator_default_params(self, name: str) -> Dict[str, Any]:
        """获取指标默认参数"""
        indicator = self.get_indicator(name)
        if not indicator:
            return {}

        return {
            param['name']: param['default_value']
            for param in indicator['parameters']
        }

    # ==================== 形态识别相关方法 ====================

    def get_pattern(self, name: str) -> Optional[Dict[str, Any]]:
        """获取形态定义 - 支持中文名称和英文名称查询"""
        if name in self._patterns_cache:
            return self._patterns_cache[name]

        try:
            cursor = self.conn.cursor()
            # 同时支持中文名称和英文名称查询
            cursor.execute('''
                SELECT p.*, c.name as category_name, c.display_name as category_display_name
                FROM pattern_types p
                LEFT JOIN indicator_categories c ON p.category_id = c.id
                WHERE (p.name = ? OR p.english_name = ?) AND p.is_active = 1
            ''', (name, name))

            row = cursor.fetchone()
            if not row:
                return None

            pattern = {
                'id': row['id'],
                'name': row['name'],
                'english_name': row['english_name'],
                'category': row['category'],
                'category_id': row['category_id'],
                'category_name': row['category_name'],
                'category_display_name': row['category_display_name'],
                'signal_type': row['signal_type'],
                'description': row['description'],
                'min_periods': row['min_periods'],
                'max_periods': row['max_periods'],
                'confidence_threshold': row['confidence_threshold'],
                'algorithm_code': row['algorithm_code'],
                'parameters': json.loads(row['parameters']) if row['parameters'] else {},
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

            # 缓存结果
            self._patterns_cache[name] = pattern
            return pattern

        except Exception as e:
            logger.error(f"获取形态 {name} 失败: {str(e)}")
            return None

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """获取所有形态定义"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT english_name FROM pattern_types 
                WHERE is_active = 1 
                ORDER BY english_name
            ''')

            patterns = []
            for row in cursor.fetchall():
                pattern = self.get_pattern(row['english_name'])
                if pattern:
                    patterns.append(pattern)

            return patterns
        except Exception as e:
            logger.error(f"获取所有形态失败: {str(e)}")
            return []

    def get_patterns_by_category(self, category: str) -> List[Dict[str, Any]]:
        """获取指定分类的所有形态"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT english_name FROM pattern_types 
                WHERE category = ? AND is_active = 1
                ORDER BY english_name
            ''', (category,))

            patterns = []
            for row in cursor.fetchall():
                pattern = self.get_pattern(row['english_name'])
                if pattern:
                    patterns.append(pattern)

            return patterns
        except Exception as e:
            logger.error(f"获取分类 {category} 的形态失败: {str(e)}")
            return []

    # ==================== 指标计算方法 ====================

    def _get_best_implementation(self, indicator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取最佳实现"""
        implementations = indicator.get('implementations', [])
        if not implementations:
            return None

        # 按优先级和默认标志排序，选择最佳实现
        best_impl = None

        # 1. 首先查找默认实现
        for impl in implementations:
            if impl.get('is_default', False):
                best_impl = impl
                break

        # 2. 如果没有默认实现，根据引擎优先级选择
        if not best_impl:
            # TA-Lib > custom > pandas
            engine_priority = {'talib': 3, 'custom': 2, 'pandas': 1}

            implementations_sorted = sorted(
                implementations,
                key=lambda x: (x.get('priority', 0), engine_priority.get(x['engine'], 0)),
                reverse=True
            )

            # 如果TA-Lib可用，优先选择TA-Lib实现
            if TALIB_AVAILABLE:
                for impl in implementations_sorted:
                    if impl['engine'] == 'talib':
                        best_impl = impl
                        break

            # 否则选择优先级最高的实现
            if not best_impl and implementations_sorted:
                best_impl = implementations_sorted[0]

        return best_impl

    def _compile_custom_function(self, code: str, function_name: str) -> Optional[Callable]:
        """编译自定义函数"""
        cache_key = f"{function_name}_{hash(code)}"

        if cache_key in self._custom_functions:
            return self._custom_functions[cache_key]

        try:
            namespace = {'np': np, 'pd': pd}
            exec(code, namespace)

            if function_name not in namespace:
                logger.error(f"函数 {function_name} 未在代码中定义")
                return None

            func = namespace[function_name]
            self._custom_functions[cache_key] = func
            return func

        except Exception as e:
            logger.error(f"编译自定义函数 {function_name} 失败: {str(e)}")
            return None

    def calculate_indicator(self, name: str, df: pd.DataFrame, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        计算指标（技术指标或形态指标）

        参数:
            name: 指标名称
            df: 输入DataFrame，包含OHLCV数据
            params: 计算参数，如果为None则使用默认参数

        返回:
            DataFrame: 添加了指标列的DataFrame
        """
        # 首先尝试作为技术指标处理
        indicator = self.get_indicator(name)
        if indicator:
            return self._calculate_technical_indicator(name, df, params, indicator)

        # 如果不是技术指标，尝试作为形态指标处理
        pattern = self.get_pattern(name)
        if pattern:
            return self._calculate_pattern_indicator(name, df, params, pattern)

        logger.error(f"指标或形态 {name} 不存在")
        return df.copy()

    def _calculate_technical_indicator(self, name: str, df: pd.DataFrame, params: Optional[Dict[str, Any]], indicator: Dict[str, Any]) -> pd.DataFrame:
        """计算技术指标"""
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
            return df.copy()

        try:
            result = df.copy()

            if impl['engine'] == 'talib':
                # TA-Lib实现
                result = self._calculate_talib_indicator(name, result, impl, params, indicator)
            elif impl['engine'] in ['custom', 'pandas']:
                # 自定义实现
                result = self._calculate_custom_indicator(name, result, impl, params, indicator)
            else:
                logger.error(f"不支持的实现引擎: {impl['engine']}")

            return result

        except Exception as e:
            logger.error(f"计算指标 {name} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df.copy()

    def _calculate_pattern_indicator(self, name: str, df: pd.DataFrame, params: Optional[Dict[str, Any]], pattern: Dict[str, Any]) -> pd.DataFrame:
        """计算形态指标"""
        try:
            result = df.copy()

            # 使用默认参数
            if params is None:
                params = {}

            # 设置形态指标的默认参数
            default_pattern_params = {
                '置信度阈值': pattern.get('confidence_threshold', 0.7),
                '最小周期': pattern.get('min_periods', 5),
                '最大周期': pattern.get('max_periods', 20)
            }

            for key, value in default_pattern_params.items():
                if key not in params:
                    params[key] = value

            # 执行形态识别算法
            pattern_result = self._execute_pattern_algorithm(name, df, params, pattern)

            # 将结果添加到DataFrame
            if isinstance(pattern_result, pd.Series):
                result[name] = pattern_result
            elif isinstance(pattern_result, dict):
                for key, value in pattern_result.items():
                    result[f"{name}_{key}"] = value
            else:
                # 创建一个简单的形态信号
                result[name] = pd.Series(0, index=df.index)  # 默认无信号
                logger.warning(f"形态 {name} 计算结果格式不正确，使用默认值")

            return result

        except Exception as e:
            logger.error(f"计算形态 {name} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return df.copy()

    def _execute_pattern_algorithm(self, name: str, df: pd.DataFrame, params: Dict[str, Any], pattern: Dict[str, Any]) -> Union[pd.Series, Dict[str, pd.Series]]:
        """执行形态识别算法"""
        try:
            # 获取算法代码
            algorithm_code = pattern.get('algorithm_code', '')

            if algorithm_code:
                # 执行自定义算法
                return self._execute_custom_pattern_algorithm(name, df, params, algorithm_code)
            else:
                # 使用内置形态识别
                return self._execute_builtin_pattern_algorithm(name, df, params, pattern)

        except Exception as e:
            logger.error(f"执行形态算法 {name} 失败: {str(e)}")
            # 返回默认的空信号
            return pd.Series(0, index=df.index)

    def _execute_custom_pattern_algorithm(self, name: str, df: pd.DataFrame, params: Dict[str, Any], algorithm_code: str) -> Union[pd.Series, Dict[str, pd.Series]]:
        """执行自定义形态算法"""
        try:
            # 创建执行环境
            namespace = {
                'np': np,
                'pd': pd,
                'df': df,
                'params': params,
                'name': name
            }

            # 执行算法代码
            exec(algorithm_code, namespace)

            # 获取结果 - 约定算法代码应该设置result变量
            if 'result' in namespace:
                return namespace['result']
            else:
                logger.warning(f"形态算法 {name} 没有返回result变量")
                return pd.Series(0, index=df.index)

        except Exception as e:
            logger.error(f"执行自定义形态算法 {name} 失败: {str(e)}")
            return pd.Series(0, index=df.index)

    def _execute_builtin_pattern_algorithm(self, name: str, df: pd.DataFrame, params: Dict[str, Any], pattern: Dict[str, Any]) -> Union[pd.Series, Dict[str, pd.Series]]:
        """执行内置形态算法"""
        try:
            # 这里可以添加内置的形态识别算法
            # 目前返回简单的模拟结果

            confidence_threshold = params.get('置信度阈值', 0.7)
            min_periods = params.get('最小周期', 5)
            max_periods = params.get('最大周期', 20)

            # 创建简单的形态信号
            # 这里是一个示例实现，实际应该根据具体形态实现相应算法
            signal = pd.Series(0, index=df.index)

            # 模拟一些形态信号（基于价格变化）
            if len(df) >= min_periods:
                price_change = df['close'].pct_change(periods=min_periods)

                # 根据形态类型生成不同的信号
                if '锤头' in name or '十字星' in name:
                    # 反转形态
                    signal.loc[price_change > 0.02] = 1  # 买入信号
                    signal.loc[price_change < -0.02] = -1  # 卖出信号
                elif '吞没' in name or '包容' in name:
                    # 包容形态
                    signal.loc[price_change > 0.03] = 1
                    signal.loc[price_change < -0.03] = -1
                else:
                    # 默认处理
                    signal.loc[price_change > 0.025] = 1
                    signal.loc[price_change < -0.025] = -1

            return signal

        except Exception as e:
            logger.error(f"执行内置形态算法 {name} 失败: {str(e)}")
            return pd.Series(0, index=df.index)

    def _calculate_talib_indicator(self, name: str, df: pd.DataFrame, impl: Dict, params: Dict, indicator: Dict) -> pd.DataFrame:
        """使用TA-Lib计算指标"""
        if not TALIB_AVAILABLE:
            logger.error(f"TA-Lib 未安装，无法计算指标 {name}")
            return df

        try:
            talib_func = getattr(talib, impl['function_name'])

            # 准备输入数据
            inputs = self._prepare_talib_inputs(df, impl['function_name'], params)

            # 调用TA-Lib函数
            # 将参数分为数据参数和设置参数
            data_params = {}
            config_params = {}

            for key, value in inputs.items():
                if key in ['close', 'open', 'high', 'low', 'volume']:
                    data_params[key] = value
                else:
                    config_params[key] = value

            # 根据函数特性调用
            if data_params and len(data_params) == 1 and 'close' in data_params:
                # 单一数据列函数
                talib_result = talib_func(data_params['close'], **config_params)
            elif len(data_params) == 3 and all(k in data_params for k in ['high', 'low', 'close']):
                # 三数据列函数
                talib_result = talib_func(data_params['high'], data_params['low'], data_params['close'], **config_params)
            elif len(data_params) == 2 and all(k in data_params for k in ['close', 'volume']):
                # 双数据列函数
                talib_result = talib_func(data_params['close'], data_params['volume'], **config_params)
            else:
                # 通用调用
                talib_result = talib_func(**inputs)

            # 处理返回结果
            output_names = indicator.get('output_names', [])

            if isinstance(talib_result, tuple):
                # 多个输出
                for i, output_name in enumerate(output_names):
                    if i < len(talib_result):
                        df[output_name] = pd.Series(talib_result[i], index=df.index)
            else:
                # 单个输出
                if output_names:
                    df[output_names[0]] = pd.Series(talib_result, index=df.index)
                else:
                    df[name] = pd.Series(talib_result, index=df.index)

            return df

        except Exception as e:
            logger.error(f"TA-Lib计算指标 {name} 失败: {str(e)}")
            return df

    def _prepare_talib_inputs(self, df: pd.DataFrame, function_name: str, params: Dict) -> Dict:
        """准备TA-Lib函数的输入参数"""
        inputs = {}

        # 根据函数名确定需要的输入列
        if function_name in ['MA', 'SMA', 'EMA', 'RSI', 'ROC', 'MOM']:
            inputs['close'] = df['close'].values
        elif function_name in ['MACD']:
            inputs['close'] = df['close'].values
        elif function_name in ['BBANDS']:
            inputs['close'] = df['close'].values
        elif function_name in ['STOCH', 'STOCHF']:
            inputs['high'] = df['high'].values
            inputs['low'] = df['low'].values
            inputs['close'] = df['close'].values
        elif function_name in ['ATR', 'CCI']:
            inputs['high'] = df['high'].values
            inputs['low'] = df['low'].values
            inputs['close'] = df['close'].values
        elif function_name in ['OBV']:
            inputs['close'] = df['close'].values
            inputs['volume'] = df['volume'].values
        elif function_name in ['ADX']:
            inputs['high'] = df['high'].values
            inputs['low'] = df['low'].values
            inputs['close'] = df['close'].values
        else:
            # 默认使用close
            inputs['close'] = df['close'].values

        # 添加参数
        for key, value in params.items():
            if key not in inputs:  # 避免覆盖数据列
                inputs[key] = value

        return inputs

    def _calculate_custom_indicator(self, name: str, df: pd.DataFrame, impl: Dict, params: Dict, indicator: Dict) -> pd.DataFrame:
        """使用自定义实现计算指标"""
        try:
            if impl['engine'] == 'custom' and impl.get('code'):
                # 编译并执行自定义代码
                func = self._compile_custom_function(impl['code'], impl['function_name'])
                if not func:
                    return df
            else:
                # 导入预定义的函数
                try:
                    module_parts = impl['function_name'].split('.')
                    if len(module_parts) > 1:
                        module_path = '.'.join(module_parts[:-1])
                        func_name = module_parts[-1]
                        module = importlib.import_module(module_path)
                        func = getattr(module, func_name)
                    else:
                        # 尝试从全局命名空间获取
                        func = globals().get(impl['function_name'])
                        if not func:
                            logger.error(f"找不到函数: {impl['function_name']}")
                            return df
                except Exception as e:
                    logger.error(f"导入函数 {impl['function_name']} 失败: {str(e)}")
                    return df

            # 准备函数参数
            import inspect
            sig = inspect.signature(func)
            call_args = {}

            for param_name in sig.parameters:
                if param_name == 'df':
                    call_args['df'] = df
                elif param_name in ['close', 'open', 'high', 'low', 'volume']:
                    if param_name in df.columns:
                        call_args[param_name] = df[param_name]
                elif param_name in params:
                    call_args[param_name] = params[param_name]

            # 调用函数
            custom_result = func(**call_args)

            # 处理返回结果
            output_names = indicator.get('output_names', [])

            if isinstance(custom_result, pd.DataFrame):
                # 返回DataFrame，合并结果
                for output_name in output_names:
                    if output_name in custom_result.columns:
                        df[output_name] = custom_result[output_name]
            elif isinstance(custom_result, tuple):
                # 返回多个Series
                for i, output_name in enumerate(output_names):
                    if i < len(custom_result):
                        df[output_name] = custom_result[i]
            elif isinstance(custom_result, pd.Series):
                # 返回单个Series
                if output_names:
                    df[output_names[0]] = custom_result
                else:
                    df[name] = custom_result

            return df

        except Exception as e:
            logger.error(f"自定义计算指标 {name} 失败: {str(e)}")
            return df

    # ==================== 统一查询方法 ====================

    def get_all_indicators_and_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有指标和形态，按分类组织"""
        try:
            categories = self.get_all_categories()
            result = {}

            for category in categories:
                category_name = category['name']
                category_display_name = category['display_name']

                # 初始化分类
                result[category_display_name] = {
                    'category_info': category,
                    'indicators': [],
                    'patterns': []
                }

                # 获取指标
                if category_name != 'pattern':
                    indicators = self.get_indicators_by_category(category_name)
                    result[category_display_name]['indicators'] = indicators

                # 获取形态（只有形态类）
                if category_name == 'pattern':
                    patterns = self.get_all_patterns()
                    result[category_display_name]['patterns'] = patterns

            return result

        except Exception as e:
            logger.error(f"获取所有指标和形态失败: {str(e)}")
            return {}

    def search_indicators_and_patterns(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """搜索指标和形态"""
        query = query.lower()
        result = {'indicators': [], 'patterns': []}

        try:
            # 搜索指标
            indicators = self.get_all_indicators()
            for indicator in indicators:
                if (query in indicator['name'].lower() or
                    query in indicator['display_name'].lower() or
                        query in indicator['description'].lower()):
                    result['indicators'].append(indicator)

            # 搜索形态
            patterns = self.get_all_patterns()
            for pattern in patterns:
                if (query in pattern['english_name'].lower() or
                    query in pattern['name'].lower() or
                        query in pattern['description'].lower()):
                    result['patterns'].append(pattern)

            return result

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return result


# ==================== 全局实例和便捷函数 ====================

# 创建全局实例
_unified_service = None


def get_unified_service() -> UnifiedIndicatorService:
    """获取全局统一服务实例"""
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedIndicatorService()
    return _unified_service


def calculate_indicator(name: str, df: pd.DataFrame, params: Dict[str, Any] = None) -> pd.DataFrame:
    """便捷函数：计算指标"""
    service = get_unified_service()
    return service.calculate_indicator(name, df, params)


def get_indicator_metadata(name: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取指标元数据"""
    service = get_unified_service()
    return service.get_indicator(name)


def get_all_indicators_metadata() -> List[Dict[str, Any]]:
    """便捷函数：获取所有指标元数据"""
    service = get_unified_service()
    return service.get_all_indicators()


def get_indicators_by_category(category_name: str) -> List[Dict[str, Any]]:
    """便捷函数：获取分类指标"""
    service = get_unified_service()
    return service.get_indicators_by_category(category_name)


def get_all_categories() -> List[Dict[str, Any]]:
    """便捷函数：获取所有分类"""
    service = get_unified_service()
    return service.get_all_categories()


# ==================== 向后兼容性支持 ====================

# 指标别名映射
INDICATOR_ALIASES = {
    'SMA': 'MA',
    'STOCH': 'KDJ',
    'BOLL': 'BBANDS',
    '移动平均线': 'MA',
    '指数移动平均': 'EMA',
    '随机指标': 'STOCH',
    '布林带': 'BBANDS',
    'MACD指标': 'MACD',
    '相对强弱指标': 'RSI'
}


def resolve_indicator_alias(name: str) -> str:
    """解析指标别名"""
    return INDICATOR_ALIASES.get(name, name)


if __name__ == '__main__':
    # 测试统一服务
    print("🧪 测试统一指标服务...")

    try:
        service = UnifiedIndicatorService()

        # 测试获取分类
        categories = service.get_all_categories()
        print(f"📂 共有 {len(categories)} 个分类")

        # 测试获取指标
        indicators = service.get_all_indicators()
        print(f"📈 共有 {len(indicators)} 个指标")

        # 测试获取形态
        patterns = service.get_all_patterns()
        print(f"📊 共有 {len(patterns)} 个形态")

        service.close()
        print("✅ 统一指标服务测试通过")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
