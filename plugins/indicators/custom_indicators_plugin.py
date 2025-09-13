from loguru import logger
"""
自定义指标插件框架

支持用户自定义指标开发的插件框架。
提供指标开发模板、动态加载机制和指标管理功能。
"""

import pandas as pd
import numpy as np
import time
import importlib
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.indicator_extensions import (
    IIndicatorPlugin, IndicatorMetadata, ParameterDef, ParameterType,
    IndicatorCategory, StandardKlineData, StandardIndicatorResult,
    IndicatorCalculationContext
)

logger = logger


class CustomIndicatorFunction:
    """自定义指标函数包装器"""

    def __init__(self, name: str, func: Callable, metadata: IndicatorMetadata):
        self.name = name
        self.func = func
        self.metadata = metadata
        self.call_count = 0
        self.total_time = 0.0
        self.error_count = 0

    def calculate(self, kline_data: StandardKlineData, params: Dict[str, Any],
                  context: IndicatorCalculationContext) -> StandardIndicatorResult:
        """执行指标计算"""
        start_time = time.time()
        self.call_count += 1

        try:
            # 调用用户定义的指标函数
            result_data = self.func(kline_data, params, context)

            # 确保结果是DataFrame格式
            if isinstance(result_data, pd.Series):
                result_df = pd.DataFrame({'value': result_data})
            elif isinstance(result_data, pd.DataFrame):
                result_df = result_data
            elif isinstance(result_data, (list, tuple, np.ndarray)):
                result_df = pd.DataFrame({'value': result_data}, index=kline_data.datetime)
            else:
                raise ValueError(f"不支持的指标返回类型: {type(result_data)}")

            calculation_time = (time.time() - start_time) * 1000
            self.total_time += calculation_time

            return StandardIndicatorResult(
                indicator_name=self.name,
                data=result_df,
                metadata={
                    'backend': 'Custom',
                    'calculation_time_ms': calculation_time,
                    'symbol': context.symbol,
                    'timeframe': context.timeframe,
                    'parameters': params.copy(),
                    'data_points': len(result_df),
                    'custom_function': True
                }
            )

        except Exception as e:
            self.error_count += 1
            logger.error(f"自定义指标计算失败 {self.name}: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """获取指标统计信息"""
        avg_time = self.total_time / self.call_count if self.call_count > 0 else 0.0
        return {
            'call_count': self.call_count,
            'total_time_ms': self.total_time,
            'average_time_ms': avg_time,
            'error_count': self.error_count,
            'error_rate': (self.error_count / max(self.call_count, 1)) * 100
        }


class CustomIndicatorsPlugin(IIndicatorPlugin):
    """
    自定义指标插件

    支持用户自定义指标的动态加载和管理。
    提供指标开发框架和运行时环境。
    """

    def __init__(self, custom_indicators_dir: str = "plugins/indicators/custom"):
        self._plugin_info = {
            "id": "custom_indicators",
            "name": "自定义指标插件",
            "version": "1.0.0",
            "description": "支持用户自定义指标开发和动态加载的插件框架",
            "author": "HIkyuu-UI Team",
            "backend": "Custom Python",
            "performance_level": "variable"
        }

        # 自定义指标目录
        self.custom_indicators_dir = Path(custom_indicators_dir)
        self.custom_indicators_dir.mkdir(parents=True, exist_ok=True)

        # 注册的自定义指标
        self._custom_indicators: Dict[str, CustomIndicatorFunction] = {}

        # 内置示例指标
        self._builtin_indicators = {}
        self._initialize_builtin_indicators()

        # 统计信息
        self._total_calculation_count = 0
        self._total_calculation_time = 0.0
        self._total_error_count = 0

        # 自动加载自定义指标
        self._load_custom_indicators()

        logger.info(f"自定义指标插件初始化完成，加载了 {len(self._custom_indicators)} 个自定义指标")

    @property
    def plugin_info(self) -> Dict[str, Any]:
        """获取插件基本信息"""
        return self._plugin_info.copy()

    def get_supported_indicators(self) -> List[str]:
        """获取支持的指标列表"""
        return list(self._custom_indicators.keys()) + list(self._builtin_indicators.keys())

    def get_indicator_metadata(self, indicator_name: str) -> Optional[IndicatorMetadata]:
        """获取指标元数据"""
        indicator = self._custom_indicators.get(indicator_name.upper())
        if indicator:
            return indicator.metadata

        builtin = self._builtin_indicators.get(indicator_name.upper())
        if builtin:
            return builtin.metadata

        return None

    def calculate_indicator(self, indicator_name: str, kline_data: StandardKlineData,
                            params: Dict[str, Any], context: IndicatorCalculationContext) -> StandardIndicatorResult:
        """计算单个指标"""
        self._total_calculation_count += 1
        start_time = time.time()

        try:
            # 查找自定义指标
            indicator = self._custom_indicators.get(indicator_name.upper())
            if indicator:
                result = indicator.calculate(kline_data, params, context)
                self._total_calculation_time += (time.time() - start_time) * 1000
                return result

            # 查找内置指标
            builtin = self._builtin_indicators.get(indicator_name.upper())
            if builtin:
                result = builtin.calculate(kline_data, params, context)
                self._total_calculation_time += (time.time() - start_time) * 1000
                return result

            raise ValueError(f"未找到自定义指标: {indicator_name}")

        except Exception as e:
            self._total_error_count += 1
            logger.error(f"自定义指标计算失败 {indicator_name}: {e}")
            raise

    def register_indicator(self, name: str, func: Callable, metadata: IndicatorMetadata) -> bool:
        """注册自定义指标"""
        try:
            custom_indicator = CustomIndicatorFunction(name.upper(), func, metadata)
            self._custom_indicators[name.upper()] = custom_indicator
            logger.info(f"成功注册自定义指标: {name}")
            return True
        except Exception as e:
            logger.error(f"注册自定义指标失败 {name}: {e}")
            return False

    def unregister_indicator(self, name: str) -> bool:
        """注销自定义指标"""
        try:
            if name.upper() in self._custom_indicators:
                del self._custom_indicators[name.upper()]
                logger.info(f"成功注销自定义指标: {name}")
                return True
            else:
                logger.warning(f"未找到要注销的自定义指标: {name}")
                return False
        except Exception as e:
            logger.error(f"注销自定义指标失败 {name}: {e}")
            return False

    def reload_custom_indicators(self) -> int:
        """重新加载所有自定义指标"""
        try:
            # 清除现有的自定义指标
            self._custom_indicators.clear()

            # 重新加载
            count = self._load_custom_indicators()
            logger.info(f"重新加载了 {count} 个自定义指标")
            return count
        except Exception as e:
            logger.error(f"重新加载自定义指标失败: {e}")
            return 0

    def _load_custom_indicators(self) -> int:
        """从目录加载自定义指标"""
        count = 0

        try:
            # 扫描自定义指标目录
            for py_file in self.custom_indicators_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    count += self._load_indicator_from_file(py_file)
                except Exception as e:
                    logger.error(f"加载指标文件失败 {py_file}: {e}")
                    continue

            return count
        except Exception as e:
            logger.error(f"加载自定义指标目录失败: {e}")
            return 0

    def _load_indicator_from_file(self, file_path: Path) -> int:
        """从文件加载指标"""
        try:
            # 动态导入模块
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            count = 0

            # 查找指标定义
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # 查找指标函数（约定：以 indicator_ 开头的函数）
                if callable(attr) and attr_name.startswith("indicator_"):
                    indicator_name = attr_name[10:].upper()  # 去掉 indicator_ 前缀

                    # 获取指标元数据
                    metadata = self._extract_indicator_metadata(attr, indicator_name)
                    if metadata:
                        self.register_indicator(indicator_name, attr, metadata)
                        count += 1

            return count
        except Exception as e:
            logger.error(f"从文件加载指标失败 {file_path}: {e}")
            return 0

    def _extract_indicator_metadata(self, func: Callable, indicator_name: str) -> Optional[IndicatorMetadata]:
        """从函数中提取指标元数据"""
        try:
            # 检查函数是否有元数据属性
            if hasattr(func, 'metadata') and isinstance(func.metadata, IndicatorMetadata):
                return func.metadata

            # 从函数文档字符串解析元数据
            if func.__doc__:
                return self._parse_metadata_from_docstring(func.__doc__, indicator_name)

            # 创建默认元数据
            return IndicatorMetadata(
                name=indicator_name,
                display_name=indicator_name.replace('_', ' ').title(),
                description=f"自定义指标: {indicator_name}",
                category=IndicatorCategory.CUSTOM,
                parameters=[],
                output_columns=['value'],
                tags=['custom'],
                author='User'
            )
        except Exception as e:
            logger.error(f"提取指标元数据失败 {indicator_name}: {e}")
            return None

    def _parse_metadata_from_docstring(self, docstring: str, indicator_name: str) -> IndicatorMetadata:
        """从文档字符串解析元数据"""
        # 这里可以实现更复杂的解析逻辑
        # 目前简化处理
        lines = docstring.strip().split('\n')
        description = lines[0] if lines else f"自定义指标: {indicator_name}"

        return IndicatorMetadata(
            name=indicator_name,
            display_name=indicator_name.replace('_', ' ').title(),
            description=description,
            category=IndicatorCategory.CUSTOM,
            parameters=[],
            output_columns=['value'],
            tags=['custom'],
            author='User'
        )

    def _initialize_builtin_indicators(self):
        """初始化内置示例指标"""
        # 简单移动平均线示例
        def simple_ma_example(kline_data: StandardKlineData, params: Dict[str, Any],
                              context: IndicatorCalculationContext) -> pd.Series:
            """简单移动平均线示例"""
            period = params.get('period', 20)
            return kline_data.close.rolling(window=period).mean()

        simple_ma_metadata = IndicatorMetadata(
            name='SIMPLE_MA_EXAMPLE',
            display_name='简单移动平均线示例',
            description='自定义指标示例：简单移动平均线',
            category=IndicatorCategory.TREND,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 20, '周期', 1, 200)
            ],
            output_columns=['value'],
            tags=['example', 'trend', 'moving_average'],
            author='HIkyuu-UI Team'
        )

        self._builtin_indicators['SIMPLE_MA_EXAMPLE'] = CustomIndicatorFunction(
            'SIMPLE_MA_EXAMPLE', simple_ma_example, simple_ma_metadata
        )

        # 价格动量示例
        def price_momentum_example(kline_data: StandardKlineData, params: Dict[str, Any],
                                   context: IndicatorCalculationContext) -> pd.Series:
            """价格动量示例"""
            period = params.get('period', 10)
            return kline_data.close.pct_change(periods=period) * 100

        momentum_metadata = IndicatorMetadata(
            name='PRICE_MOMENTUM_EXAMPLE',
            display_name='价格动量示例',
            description='自定义指标示例：价格动量',
            category=IndicatorCategory.MOMENTUM,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 10, '周期', 1, 100)
            ],
            output_columns=['value'],
            tags=['example', 'momentum'],
            author='HIkyuu-UI Team'
        )

        self._builtin_indicators['PRICE_MOMENTUM_EXAMPLE'] = CustomIndicatorFunction(
            'PRICE_MOMENTUM_EXAMPLE', price_momentum_example, momentum_metadata
        )

        # 成交量加权价格示例
        def vwap_example(kline_data: StandardKlineData, params: Dict[str, Any],
                         context: IndicatorCalculationContext) -> pd.Series:
            """成交量加权价格示例"""
            period = params.get('period', 20)
            typical_price = (kline_data.high + kline_data.low + kline_data.close) / 3
            return (typical_price * kline_data.volume).rolling(window=period).sum() / kline_data.volume.rolling(window=period).sum()

        vwap_metadata = IndicatorMetadata(
            name='VWAP_EXAMPLE',
            display_name='成交量加权价格示例',
            description='自定义指标示例：成交量加权平均价格',
            category=IndicatorCategory.VOLUME,
            parameters=[
                ParameterDef('period', ParameterType.INTEGER, 20, '周期', 1, 200)
            ],
            output_columns=['value'],
            tags=['example', 'volume', 'vwap'],
            author='HIkyuu-UI Team'
        )

        self._builtin_indicators['VWAP_EXAMPLE'] = CustomIndicatorFunction(
            'VWAP_EXAMPLE', vwap_example, vwap_metadata
        )

    def create_indicator_template(self, indicator_name: str, category: IndicatorCategory = IndicatorCategory.CUSTOM) -> str:
        """创建指标开发模板"""
        template = f'''"""
自定义指标: {indicator_name}

这是一个自定义指标模板，请根据需要修改实现逻辑。
"""

import pandas as pd
import numpy as np
from core.indicator_extensions import (
    IndicatorMetadata, ParameterDef, ParameterType, IndicatorCategory,
    StandardKlineData, IndicatorCalculationContext
)

def indicator_{indicator_name.lower()}(kline_data: StandardKlineData, params: dict, 
                                      context: IndicatorCalculationContext) -> pd.Series:
    """
    {indicator_name} 指标计算函数
    
    Args:
        kline_data: 标准K线数据
        params: 指标参数
        context: 计算上下文
    
    Returns:
        pd.Series: 指标计算结果
    """
    # 获取参数
    period = params.get('period', 20)
    
    # 指标计算逻辑（示例：简单移动平均）
    result = kline_data.close.rolling(window=period).mean()
    
    return result

# 指标元数据定义
indicator_{indicator_name.lower()}.metadata = IndicatorMetadata(
    name='{indicator_name.upper()}',
    display_name='{indicator_name.replace("_", " ").title()}',
    description='{indicator_name} 自定义指标',
    category=IndicatorCategory.{category.name},
    parameters=[
        ParameterDef('period', ParameterType.INTEGER, 20, '周期', 1, 200)
    ],
    output_columns=['value'],
    tags=['custom', '{category.value}'],
    author='User'
)
'''
        return template

    def save_indicator_template(self, indicator_name: str, category: IndicatorCategory = IndicatorCategory.CUSTOM) -> bool:
        """保存指标模板到文件"""
        try:
            template = self.create_indicator_template(indicator_name, category)
            file_path = self.custom_indicators_dir / f"{indicator_name.lower()}.py"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)

            logger.info(f"指标模板已保存到: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存指标模板失败: {e}")
            return False

    def get_indicator_statistics(self, indicator_name: str) -> Optional[Dict[str, Any]]:
        """获取指标统计信息"""
        indicator = self._custom_indicators.get(indicator_name.upper())
        if indicator:
            return indicator.get_statistics()

        builtin = self._builtin_indicators.get(indicator_name.upper())
        if builtin:
            return builtin.get_statistics()

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        avg_time = (self._total_calculation_time / self._total_calculation_count
                    if self._total_calculation_count > 0 else 0.0)

        # 收集所有指标的统计信息
        indicator_stats = {}
        for name, indicator in {**self._custom_indicators, **self._builtin_indicators}.items():
            indicator_stats[name] = indicator.get_statistics()

        return {
            'total_calculation_count': self._total_calculation_count,
            'total_calculation_time_ms': self._total_calculation_time,
            'average_calculation_time_ms': avg_time,
            'total_error_count': self._total_error_count,
            'error_rate': (self._total_error_count / max(self._total_calculation_count, 1)) * 100,
            'custom_indicators_count': len(self._custom_indicators),
            'builtin_indicators_count': len(self._builtin_indicators),
            'total_indicators_count': len(self._custom_indicators) + len(self._builtin_indicators),
            'custom_indicators_dir': str(self.custom_indicators_dir),
            'indicator_statistics': indicator_stats
        }
