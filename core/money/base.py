from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

class BaseMoneyManager(ABC):
    """资金管理系统基类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化资金管理系统

        Args:
            params: 参数
        """
        self._params = params or {}
        self._cache = {}
        self._portfolio_value = 100000.0  # 默认初始资金
        self._position = 0.0  # 当前持仓
        
        if params and 'initial_capital' in params:
            self._portfolio_value = params['initial_capital']

    def _clone(self):
        """克隆对象"""
        new_instance = self.__class__(params=self._params.copy())
        new_instance._portfolio_value = self._portfolio_value
        new_instance._position = self._position
        return new_instance

    def calculate(self, market_data: pd.DataFrame, price: float, timestamp) -> Dict[str, Any]:
        """
        计算资金管理

        Args:
            market_data: 市场数据 DataFrame
            price: 当前价格
            timestamp: 时间戳

        Returns:
            Dict: 资金管理结果
        """
        try:
            # 计算资金管理
            result = self._calculate_money_management(market_data, price, timestamp)
            return result

        except Exception as e:
            logger.error(f"资金管理计算错误: {str(e)}")
            return {
                'position_size': 0.0,
                'stop_loss_price': 0.0,
                'take_profit_price': 0.0,
                'portfolio_value': self._portfolio_value
            }

    @abstractmethod
    def _calculate_money_management(self, market_data: pd.DataFrame, price: float, timestamp) -> Dict[str, Any]:
        """
        计算资金管理

        Args:
            market_data: 市场数据 DataFrame
            price: 当前价格
            timestamp: 时间戳

        Returns:
            Dict: 包含持仓数量、止损价格、止盈价格等信息的字典
        """
        pass

    def get_position_size(self, market_data: pd.DataFrame, price: float, timestamp) -> float:
        """
        获取持仓数量

        Args:
            market_data: 市场数据 DataFrame
            price: 价格
            timestamp: 时间戳

        Returns:
            float: 持仓数量
        """
        try:
            result = self.calculate(market_data, price, timestamp)
            return result.get('position_size', 0.0)
        except Exception as e:
            logger.error(f"获取持仓数量错误: {str(e)}")
            return 0.0

    def get_stop_loss_price(self, market_data: pd.DataFrame, price: float, timestamp) -> float:
        """
        获取止损价格

        Args:
            market_data: 市场数据 DataFrame
            price: 价格
            timestamp: 时间戳

        Returns:
            float: 止损价格
        """
        try:
            result = self.calculate(market_data, price, timestamp)
            return result.get('stop_loss_price', 0.0)
        except Exception as e:
            logger.error(f"获取止损价格错误: {str(e)}")
            return 0.0

    def get_take_profit_price(self, market_data: pd.DataFrame, price: float, timestamp) -> float:
        """
        获取止盈价格

        Args:
            market_data: 市场数据 DataFrame
            price: 价格
            timestamp: 时间戳

        Returns:
            float: 止盈价格
        """
        try:
            result = self.calculate(market_data, price, timestamp)
            return result.get('take_profit_price', 0.0)
        except Exception as e:
            logger.error(f"获取止盈价格错误: {str(e)}")
            return 0.0

    def update_portfolio_value(self, value: float):
        """更新投资组合价值"""
        self._portfolio_value = value
        
    def get_portfolio_value(self) -> float:
        """获取投资组合价值"""
        return self._portfolio_value
        
    def set_position(self, position: float):
        """设置当前持仓"""
        self._position = position
        
    def get_position(self) -> float:
        """获取当前持仓"""
        return self._position
