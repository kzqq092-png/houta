from hikyuu import *
from hikyuu.trade_sys import SignalBase
from hikyuu.indicator import MA, MACD, RSI, KDJ, CLOSE, VOL, OPEN, HIGH, LOW
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

class BaseSignal(SignalBase):
    """信号系统基类"""
    
    def __init__(self, name: str = "BaseSignal"):
        super(BaseSignal, self).__init__(name)
        self._params = {}
        self._cache = {}
        
    def _clone(self):
        """克隆方法"""
        return BaseSignal(name=self.name)
        
    def _calculate(self, k):
        """计算方法，生成买入卖出信号"""
        try:
            # 计算基础指标
            indicators = self._calculate_indicators(k)
            
            # 生成信号
            signals = self._generate_signals(k, indicators)
            
            # 记录信号
            self._record_signals(k, signals)
            
        except Exception as e:
            print(f"信号计算错误: {str(e)}")
            return
            
    def _calculate_indicators(self, k) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        
        # 计算移动平均线
        indicators['ma_fast'] = MA(CLOSE(k), n=self.get_param("n_fast", 12))
        indicators['ma_slow'] = MA(CLOSE(k), n=self.get_param("n_slow", 26))
        
        # 计算MACD
        indicators['macd'] = MACD(CLOSE(k), 
                                n1=self.get_param("n_fast", 12),
                                n2=self.get_param("n_slow", 26),
                                n3=self.get_param("n_signal", 9))
        
        # 计算RSI
        indicators['rsi'] = RSI(CLOSE(k), n=self.get_param("rsi_window", 14))
        
        # 计算KDJ
        indicators['kdj'] = KDJ(k, n=self.get_param("kdj_n", 9))
        
        return indicators
        
    def _generate_signals(self, k, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """生成交易信号"""
        signals = {
            'buy': [],
            'sell': []
        }
        
        n = len(k)
        for i in range(1, n):
            # 生成买入信号
            if self._check_buy_signal(k, indicators, i):
                signals['buy'].append(k[i].datetime)
                
            # 生成卖出信号
            if self._check_sell_signal(k, indicators, i):
                signals['sell'].append(k[i].datetime)
                
        return signals
        
    def _check_buy_signal(self, k, indicators: Dict[str, Any], i: int) -> bool:
        """检查买入信号条件"""
        # 默认实现，子类可以重写
        return False
        
    def _check_sell_signal(self, k, indicators: Dict[str, Any], i: int) -> bool:
        """检查卖出信号条件"""
        # 默认实现，子类可以重写
        return False
        
    def _record_signals(self, k, signals: Dict[str, Any]):
        """记录信号"""
        for datetime in signals['buy']:
            self.add_buy_signal(datetime)
            
        for datetime in signals['sell']:
            self.add_sell_signal(datetime)
            
    def set_param(self, name: str, value: Any):
        """设置参数"""
        self._params[name] = value
        
    def get_param(self, name: str, default: Any = None) -> Any:
        """获取参数"""
        return self._params.get(name, default)
        
    def get_params(self) -> Dict[str, Any]:
        """获取所有参数"""
        return self._params.copy() 