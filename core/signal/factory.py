from hikyuu import crtSG
from .base import BaseSignal
from .enhanced import EnhancedSignal
from typing import Dict, Any, Optional, Type

class SignalFactory:
    """信号系统工厂类"""
    
    @staticmethod
    def create_signal(signal_type: str, params: Optional[Dict[str, Any]] = None) -> BaseSignal:
        """
        创建信号系统
        
        Args:
            signal_type: 信号系统类型
            params: 参数
            
        Returns:
            BaseSignal: 信号系统实例
        """
        signal_map = {
            'base': BaseSignal,
            'enhanced': EnhancedSignal
        }
        
        signal_class = signal_map.get(signal_type)
        if signal_class is None:
            raise ValueError(f"不支持的信号系统类型: {signal_type}")
            
        return signal_class(params=params)
        
    @staticmethod
    def create_signal_with_hikyuu(signal_type: str, params: Optional[Dict[str, Any]] = None):
        """
        使用Hikyuu创建信号系统
        
        Args:
            signal_type: 信号系统类型
            params: 参数
            
        Returns:
            SignalBase: Hikyuu信号系统实例
        """
        def signal_calculate(k, record):
            try:
                # 创建信号系统
                signal = SignalFactory.create_signal(signal_type, params)
                
                # 计算信号
                signal._calculate(k)
                
                # 记录信号
                for datetime in signal.get_buy_signals():
                    record.add_buy_signal(datetime)
                    
                for datetime in signal.get_sell_signals():
                    record.add_sell_signal(datetime)
                    
            except Exception as e:
                print(f"信号计算错误: {str(e)}")
                return
                
        return crtSG(signal_calculate, params=params, name=signal_type) 