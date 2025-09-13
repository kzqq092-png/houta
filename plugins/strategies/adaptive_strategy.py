from loguru import logger
#!/usr/bin/env python3
"""
自适应策略模块

使用统一的策略管理系统框架，集成HIkyuu原生组件
"""

from hikyuu import *
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

# 导入统一策略管理系统
from core.strategy.base_strategy import BaseStrategy, StrategySignal, SignalType, StrategyType
from core.strategy import register_strategy
from core.stop_loss import AdaptiveStopLoss
from core.take_profit import AdaptiveTakeProfit


@register_strategy("AdaptiveHikyuu", metadata={
    "description": "基于HIkyuu框架的自适应止损止盈策略",
    "author": "FactorWeave 团队",
    "version": "2.0.0",
    "category": "adaptive"
})
class AdaptiveHikuuStrategy(BaseStrategy):
    """自适应HIkyuu策略"""

    def __init__(self, name: str = "AdaptiveHikyuu"):
        super().__init__(name, StrategyType.CUSTOM)
        self._init_default_parameters()
        self._system = None

    def _init_default_parameters(self):
        """初始化默认参数"""
        # 资金管理参数
        self.add_parameter("init_cash", 100000, int, "初始资金", 10000, 1000000)
        self.add_parameter("fixed_count", 100, int, "固定股数", 10, 1000)

        # 止损参数
        self.add_parameter("atr_period", 14, int, "ATR周期", 5, 30)
        self.add_parameter("atr_multiplier", 2.0, float, "ATR倍数", 1.0, 5.0)
        self.add_parameter("volatility_factor", 0.5, float, "波动率因子", 0.1, 1.0)
        self.add_parameter("trend_factor", 0.3, float, "趋势因子", 0.1, 1.0)
        self.add_parameter("market_factor", 0.2, float, "市场因子", 0.1, 1.0)
        self.add_parameter("min_stop_loss", 0.02, float, "最小止损", 0.01, 0.1)
        self.add_parameter("max_stop_loss", 0.1, float, "最大止损", 0.05, 0.2)
        self.add_parameter("fixed_stop_loss", 0.05, float, "固定止损", 0.02, 0.1)

        # 止盈参数
        self.add_parameter("ma_period", 20, int, "移动平均周期", 5, 50)
        self.add_parameter("volatility_period", 20, int, "波动率周期", 5, 50)
        self.add_parameter("min_take_profit", 0.05, float, "最小止盈", 0.02, 0.2)
        self.add_parameter("max_take_profit", 0.2, float, "最大止盈", 0.1, 0.5)
        self.add_parameter("trailing_profit", 0.03, float, "跟踪止盈", 0.01, 0.1)
        self.add_parameter("profit_lock", 0.05, float, "利润锁定", 0.02, 0.1)

        # 滑点参数
        self.add_parameter("slippage_percent", 0.01,
                           float, "滑点百分比", 0.001, 0.05)

    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        生成交易信号

        注意：这个策略主要用于系统配置，实际信号生成由HIkyuu系统处理
        """
        signals = []

        # 创建HIkyuu系统
        system = self._create_hikyuu_system()

        if system is None:
            return signals

        # 这里可以添加基于HIkyuu系统的信号生成逻辑
        # 由于HIkyuu系统的复杂性，这里提供一个简化的示例

        try:
            # 简化的信号生成逻辑
            if len(data) > 20:
                # 计算简单的移动平均信号
                ma_period = self.get_parameter("ma_period")
                data_copy = data.copy()
                data_copy['ma'] = data_copy['close'].rolling(
                    window=ma_period).mean()

                for i in range(ma_period, len(data_copy)):
                    current = data_copy.iloc[i]
                    prev = data_copy.iloc[i-1]

                    # 简单的金叉死叉信号
                    if current['close'] > current['ma'] and prev['close'] <= prev['ma']:
                        signals.append(StrategySignal(
                            timestamp=data_copy.index[i],
                            signal_type=SignalType.BUY,
                            price=current['close'],
                            confidence=0.7,
                            strategy_name=self.name,
                            reason=f"价格突破{ma_period}日移动平均线",
                            stop_loss=current['close'] *
                            (1 - self.get_parameter("fixed_stop_loss")),
                            take_profit=current['close'] *
                            (1 + self.get_parameter("min_take_profit"))
                        ))

                    elif current['close'] < current['ma'] and prev['close'] >= prev['ma']:
                        signals.append(StrategySignal(
                            timestamp=data_copy.index[i],
                            signal_type=SignalType.SELL,
                            price=current['close'],
                            confidence=0.7,
                            strategy_name=self.name,
                            reason=f"价格跌破{ma_period}日移动平均线",
                            stop_loss=current['close'] *
                            (1 + self.get_parameter("fixed_stop_loss")),
                            take_profit=current['close'] *
                            (1 - self.get_parameter("min_take_profit"))
                        ))

        except Exception as e:
            logger.info(f"HIkyuu自适应策略信号生成失败: {e}")

        return signals

    def _create_hikyuu_system(self):
        """创建HIkyuu交易系统"""
        try:
            # 创建交易管理对象
            tm = crtTM(init_cash=self.get_parameter("init_cash"))

            # 创建资金管理策略
            mm = MM_FixedCount(self.get_parameter("fixed_count"))

            # 创建信号指示器
            ev = EV_Bool(False)

            # 创建系统有效条件
            cn = CN_Bool(True)

            # 创建自适应止损策略
            sl_params = {
                'atr_period': self.get_parameter("atr_period"),
                'atr_multiplier': self.get_parameter("atr_multiplier"),
                'volatility_factor': self.get_parameter("volatility_factor"),
                'trend_factor': self.get_parameter("trend_factor"),
                'market_factor': self.get_parameter("market_factor"),
                'min_stop_loss': self.get_parameter("min_stop_loss"),
                'max_stop_loss': self.get_parameter("max_stop_loss"),
                'fixed_stop_loss': self.get_parameter("fixed_stop_loss")
            }
            sl = AdaptiveStopLoss(params=sl_params)

            # 创建自适应盈利目标策略
            pg_params = {
                'atr_period': self.get_parameter("atr_period"),
                'atr_multiplier': self.get_parameter("atr_multiplier"),
                'ma_period': self.get_parameter("ma_period"),
                'volatility_period': self.get_parameter("volatility_period"),
                'min_take_profit': self.get_parameter("min_take_profit"),
                'max_take_profit': self.get_parameter("max_take_profit"),
                'trailing_profit': self.get_parameter("trailing_profit"),
                'profit_lock': self.get_parameter("profit_lock"),
                'volatility_factor': self.get_parameter("volatility_factor"),
                'trend_factor': self.get_parameter("trend_factor"),
                'market_factor': self.get_parameter("market_factor")
            }
            pg = AdaptiveTakeProfit(params=pg_params)

            # 创建滑点算法
            sp = SP_FixedPercent(self.get_parameter("slippage_percent"))

            # 创建系统
            system = SYS_Simple(tm=tm, mm=mm, ev=ev,
                                cn=cn, sl=sl, pg=pg, sp=sp)

            self._system = system
            return system

        except Exception as e:
            logger.info(f"创建HIkyuu系统失败: {e}")
            return None

    def get_hikyuu_system(self):
        """获取HIkyuu系统实例"""
        if self._system is None:
            self._system = self._create_hikyuu_system()
        return self._system

    def calculate_confidence(self, data: pd.DataFrame, signal_index: int) -> float:
        """计算信号置信度"""
        # 基于系统参数的复杂度计算置信度
        return 0.7  # 固定置信度，可以根据实际情况调整

    def get_required_columns(self) -> List[str]:
        """获取所需的数据列"""
        return ['open', 'high', 'low', 'close', 'volume']

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_strategy_info()
        info.update({
            "hikyuu_system": self._system is not None,
            "system_components": {
                "trade_manager": "crtTM",
                "money_manager": "MM_FixedCount",
                "stop_loss": "AdaptiveStopLoss",
                "take_profit": "AdaptiveTakeProfit",
                "slippage": "SP_FixedPercent"
            }
        })
        return info


def create_adaptive_strategy():
    """创建自适应止损策略（向后兼容函数）"""
    strategy = AdaptiveHikuuStrategy()
    return strategy.get_hikyuu_system()


# 向后兼容的工厂函数
def create_adaptive_hikyuu_strategy(name: str = "AdaptiveHikyuu", **kwargs) -> AdaptiveHikuuStrategy:
    """创建自适应HIkyuu策略实例"""
    strategy = AdaptiveHikuuStrategy(name)

    # 设置参数
    for param_name, param_value in kwargs.items():
        if strategy.get_parameter(param_name) is not None:
            strategy.set_parameter(param_name, param_value)

    return strategy
