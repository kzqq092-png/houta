"""
指标计算引擎抽象基类

该模块定义了所有指标计算引擎必须实现的接口规范，
确保不同引擎之间的兼容性和可替换性。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Union, Any, Optional
import pandas as pd


class IndicatorEngine(ABC):
    """指标计算引擎抽象基类

    所有具体的指标计算引擎都必须继承此类并实现其抽象方法。
    这样可以确保引擎之间的一致性和可替换性。
    """

    def __init__(self, name: str):
        """初始化引擎

        Args:
            name: 引擎名称
        """
        self.name = name
        self._supported_indicators: List[str] = []
        self._available = True

    @property
    def supported_indicators(self) -> List[str]:
        """获取支持的指标列表

        Returns:
            支持的指标名称列表
        """
        return self._supported_indicators.copy()

    @property
    def available(self) -> bool:
        """检查引擎是否可用

        Returns:
            引擎是否可用
        """
        return self._available

    @abstractmethod
    def supports_indicator(self, indicator_name: str) -> bool:
        """检查是否支持指定指标

        Args:
            indicator_name: 指标名称

        Returns:
            是否支持该指标
        """
        pass

    @abstractmethod
    def calculate(self,
                  indicator_name: str,
                  data: Union[pd.DataFrame, Dict[str, pd.Series]],
                  **params) -> Union[pd.Series, Dict[str, pd.Series]]:
        """计算指标

        Args:
            indicator_name: 指标名称
            data: 输入数据，可以是DataFrame或Series字典
            **params: 指标参数

        Returns:
            计算结果，可以是单个Series或Series字典

        Raises:
            NotImplementedError: 不支持的指标
            ValueError: 参数错误
            RuntimeError: 计算失败
        """
        pass

    def get_indicator_info(self, indicator_name: str) -> Optional[Dict[str, Any]]:
        """获取指标信息

        Args:
            indicator_name: 指标名称

        Returns:
            指标信息字典，包含描述、参数、输出等信息
        """
        return None

    def validate_data(self, data: Union[pd.DataFrame, Dict[str, pd.Series]]) -> bool:
        """验证输入数据格式

        Args:
            data: 输入数据

        Returns:
            数据是否有效
        """
        if isinstance(data, pd.DataFrame):
            required_columns = ['open', 'high', 'low', 'close']
            return all(col in data.columns for col in required_columns)
        elif isinstance(data, dict):
            required_keys = ['open', 'high', 'low', 'close']
            return all(key in data for key in required_keys)
        return False

    def normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """标准化参数

        子类可以重写此方法来处理特定的参数映射

        Args:
            params: 原始参数

        Returns:
            标准化后的参数
        """
        return params.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.name}Engine(available={self.available}, indicators={len(self.supported_indicators)})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"available={self.available}, "
                f"supported_indicators={self.supported_indicators})")


class EngineError(Exception):
    """引擎相关异常"""
    pass


class IndicatorNotSupportedError(EngineError):
    """指标不支持异常"""
    pass


class DataValidationError(EngineError):
    """数据验证异常"""
    pass


class CalculationError(EngineError):
    """计算异常"""
    pass
