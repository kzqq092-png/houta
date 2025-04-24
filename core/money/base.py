from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from hikyuu import MoneyManagerBase

class BaseMoneyManager(MoneyManagerBase):
    """资金管理系统基类"""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化资金管理系统
        
        Args:
            params: 参数
        """
        super().__init__()
        self._params = params or {}
        self._cache = {}
        
    def _clone(self):
        """克隆对象"""
        return self.__class__(params=self._params)
        
    def _calculate(self, k):
        """
        计算资金管理
        
        Args:
            k: K线数据
        """
        try:
            # 计算资金管理
            self._calculate_money_management(k)
            
        except Exception as e:
            print(f"资金管理计算错误: {str(e)}")
            return
            
    @abstractmethod
    def _calculate_money_management(self, k):
        """
        计算资金管理
        
        Args:
            k: K线数据
        """
        pass
        
    def get_position_size(self, k, price: float) -> float:
        """
        获取持仓数量
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 持仓数量
        """
        try:
            return self._get_position_size(k, price)
        except Exception as e:
            print(f"获取持仓数量错误: {str(e)}")
            return 0.0
            
    @abstractmethod
    def _get_position_size(self, k, price: float) -> float:
        """
        获取持仓数量
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 持仓数量
        """
        pass
        
    def get_stop_loss_price(self, k, price: float) -> float:
        """
        获取止损价格
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 止损价格
        """
        try:
            return self._get_stop_loss_price(k, price)
        except Exception as e:
            print(f"获取止损价格错误: {str(e)}")
            return 0.0
            
    @abstractmethod
    def _get_stop_loss_price(self, k, price: float) -> float:
        """
        获取止损价格
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 止损价格
        """
        pass
        
    def get_take_profit_price(self, k, price: float) -> float:
        """
        获取止盈价格
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 止盈价格
        """
        try:
            return self._get_take_profit_price(k, price)
        except Exception as e:
            print(f"获取止盈价格错误: {str(e)}")
            return 0.0
            
    @abstractmethod
    def _get_take_profit_price(self, k, price: float) -> float:
        """
        获取止盈价格
        
        Args:
            k: K线数据
            price: 价格
            
        Returns:
            float: 止盈价格
        """
        pass 