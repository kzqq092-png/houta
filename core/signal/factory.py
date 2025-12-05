"""
信号系统工厂类 - 无 hikyuu 依赖

提供统一信号系统创建和管理，完全基于 pandas 和 TA-Lib 实现。
"""

from typing import Dict, Any, Optional, Type
from loguru import logger

from .base import BaseSignal
from .enhanced import EnhancedSignal


class SignalFactory:
    """
    信号系统工厂类 - 无 hikyuu 依赖
    
    提供标准化的信号系统创建和管理，完全替代原有的 hikyuu 依赖实现。
    支持多种信号系统类型的动态创建和管理。
    """

    # 信号系统类型映射
    SIGNAL_REGISTRY = {
        'base': BaseSignal,
        'enhanced': EnhancedSignal
    }

    @classmethod
    def register_signal_type(cls, name: str, signal_class: Type[BaseSignal]):
        """注册新的信号系统类型"""
        if not issubclass(signal_class, BaseSignal):
            raise ValueError(f"信号系统类必须继承自 BaseSignal")
        cls.SIGNAL_REGISTRY[name] = signal_class
        logger.info(f"成功注册信号系统类型: {name}")

    @classmethod
    def get_available_signal_types(cls) -> list:
        """获取所有可用的信号系统类型"""
        return list(cls.SIGNAL_REGISTRY.keys())

    @staticmethod
    def create_signal(signal_type: str, params: Optional[Dict[str, Any]] = None, 
                     name: str = None) -> BaseSignal:
        """
        创建信号系统实例

        Args:
            signal_type: 信号系统类型 ('base', 'enhanced', 等)
            params: 初始化参数
            name: 信号系统名称

        Returns:
            BaseSignal: 信号系统实例

        Raises:
            ValueError: 当不支持的信号系统类型时抛出
        """
        if signal_type not in SignalFactory.SIGNAL_REGISTRY:
            available_types = list(SignalFactory.SIGNAL_REGISTRY.keys())
            raise ValueError(
                f"不支持的信号系统类型: {signal_type}。"
                f"可用类型: {available_types}"
            )

        signal_class = SignalFactory.SIGNAL_REGISTRY[signal_type]
        signal_name = name or signal_type
        
        try:
            if params:
                signal_instance = signal_class(name=signal_name, **params)
            else:
                signal_instance = signal_class(name=signal_name)
            
            logger.info(f"成功创建信号系统: {signal_name} ({signal_type})")
            return signal_instance
            
        except Exception as e:
            logger.error(f"创建信号系统失败 {signal_type}: {str(e)}")
            raise

    @staticmethod
    def create_signal_from_config(config: Dict[str, Any]) -> BaseSignal:
        """
        从配置字典创建信号系统

        Args:
            config: 信号系统配置
                - type: 信号系统类型
                - name: 信号系统名称
                - params: 初始化参数

        Returns:
            BaseSignal: 信号系统实例
        """
        signal_type = config.get('type', 'base')
        signal_name = config.get('name', signal_type)
        params = config.get('params', {})
        
        return SignalFactory.create_signal(signal_type, params, signal_name)

    @staticmethod
    def calculate_signals(signal_type: str, data, symbol: str = "", 
                         params: Optional[Dict[str, Any]] = None) -> list:
        """
        快速计算信号 - 一站式接口

        Args:
            signal_type: 信号系统类型
            data: OHLCV 数据 (DataFrame 或其他格式)
            symbol: 交易标的代码
            params: 信号系统参数

        Returns:
            list: 计算得到的信号列表
        """
        try:
            # 创建信号系统
            signal = SignalFactory.create_signal(signal_type, params)
            
            # 如果是 DataFrame，直接使用新的 calculate 方法
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                return signal.calculate(data, symbol)
            
            # 如果不是 DataFrame，需要先转换为标准格式
            else:
                from core.utils.data_standardizer import DataStandardizer
                data_standardizer = DataStandardizer()
                standardized_data = data_standardizer.standardize_kline_data(
                    data, symbol, "D"
                )
                return signal.calculate(standardized_data, symbol)
                
        except Exception as e:
            logger.error(f"信号计算失败 {signal_type}: {str(e)}")
            return []

    # 兼容性方法 - 为了向后兼容
    # 已废弃：create_signal_with_hikyuu 方法已移除

    @staticmethod
    def get_signal_info(signal_type: str) -> Dict[str, Any]:
        """获取信号系统信息"""
        if signal_type not in SignalFactory.SIGNAL_REGISTRY:
            return {}
            
        signal_class = SignalFactory.SIGNAL_REGISTRY[signal_type]
        
        # 获取信号系统的基本信息
        info = {
            'type': signal_type,
            'class_name': signal_class.__name__,
            'module': signal_class.__module__,
            'docstring': signal_class.__doc__ or "",
            'available': True
        }
        
        return info
