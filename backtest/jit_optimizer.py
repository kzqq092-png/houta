from loguru import logger
"""
JIT编译优化器
预编译关键函数，提升性能
"""

import numpy as np
import numba
from numba import jit, njit, prange
from typing import Tuple
import os
from pathlib import Path


class JITOptimizer:
    """JIT编译优化器"""

    def __init__(self):
        self._compiled_functions = {}
        self._cache_dir = Path("cache/numba")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 预编译关键函数
        self._precompile_functions()

    def _precompile_functions(self):
        """预编译关键函数"""
        logger.info("开始预编译JIT函数...")

        try:
            # 预编译回测核心函数
            self._precompile_backtest_core()

            # 预编译风险指标计算函数
            self._precompile_risk_metrics()

            # 预编译技术指标函数
            self._precompile_technical_indicators()

            logger.info("JIT函数预编译完成")

        except Exception as e:
            logger.error(f"JIT函数预编译失败: {e}")

    def _precompile_backtest_core(self):
        """预编译回测核心函数"""
        # 使用小数据集触发编译
        test_prices = np.array([100.0, 101.0, 99.0, 102.0, 98.0])
        test_signals = np.array([0, 1, 0, -1, 0])

        # 触发编译
        _ = optimized_backtest_core(
            test_prices, test_signals, 100000.0, 1.0, 0.001, 0.001
        )

        self._compiled_functions['backtest_core'] = optimized_backtest_core

    def _precompile_risk_metrics(self):
        """预编译风险指标计算函数"""
        test_returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005])

        # 触发编译
        _ = calculate_sharpe_ratio_jit(test_returns, 0.02)
        _ = calculate_max_drawdown_jit(test_returns)
        _ = calculate_volatility_jit(test_returns)

        self._compiled_functions.update({
            'sharpe_ratio': calculate_sharpe_ratio_jit,
            'max_drawdown': calculate_max_drawdown_jit,
            'volatility': calculate_volatility_jit
        })

    def _precompile_technical_indicators(self):
        """预编译技术指标函数"""
        test_prices = np.array([100.0, 101.0, 99.0, 102.0, 98.0, 103.0, 97.0])

        # 触发编译
        _ = moving_average_jit(test_prices, 3)
        _ = rsi_jit(test_prices, 5)

        self._compiled_functions.update({
            'moving_average': moving_average_jit,
            'rsi': rsi_jit
        })

    def get_function(self, name: str):
        """获取预编译的函数"""
        return self._compiled_functions.get(name)


# 优化的回测核心函数
@njit(cache=True, fastmath=True, parallel=False)  # 序列依赖，不能并行
def optimized_backtest_core(prices: np.ndarray, signals: np.ndarray,
                            initial_capital: float, position_size: float,
                            commission_pct: float, slippage_pct: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    优化的回测核心计算
    """
    n = len(prices)
    positions = np.zeros(n, dtype=np.float64)
    capital = np.zeros(n, dtype=np.float64)
    returns = np.zeros(n, dtype=np.float64)

    capital[0] = initial_capital
    current_position = 0.0
    current_capital = initial_capital

    for i in range(1, n):
        signal = signals[i]
        price = prices[i]

        # 处理交易信号
        if signal == 1 and current_position == 0:  # 买入信号且无持仓
            trade_cost = price * (commission_pct + slippage_pct)
            shares = (current_capital * position_size) / (price + trade_cost)
            current_position = shares
            current_capital -= shares * (price + trade_cost)
        elif signal == -1 and current_position > 0:  # 卖出信号且有持仓
            trade_cost = price * (commission_pct + slippage_pct)
            current_capital += current_position * (price - trade_cost)
            current_position = 0

        positions[i] = current_position

        # 计算当前权益
        if current_position > 0:
            equity = current_capital + current_position * price
        else:
            equity = current_capital

        capital[i] = equity

        # 计算收益率
        if capital[i-1] != 0:
            returns[i] = (capital[i] - capital[i-1]) / capital[i-1]

    return positions, capital, returns


# 并行优化的风险指标计算
@njit(cache=True, fastmath=True, parallel=True)
def calculate_sharpe_ratio_jit(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """计算夏普比率（JIT优化）"""
    if len(returns) == 0:
        return 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if std_return == 0:
        return 0.0

    # 年化处理
    annualized_return = mean_return * 252
    annualized_std = std_return * np.sqrt(252)

    return (annualized_return - risk_free_rate) / annualized_std


@njit(cache=True, fastmath=True)
def calculate_max_drawdown_jit(returns: np.ndarray) -> float:
    """计算最大回撤（JIT优化）"""
    if len(returns) == 0:
        return 0.0

    cumulative = np.cumprod(1 + returns)

    # 手动实现 accumulate，因为 Numba 不支持 np.maximum.accumulate
    running_max = np.zeros_like(cumulative)
    running_max[0] = cumulative[0]
    for i in range(1, len(cumulative)):
        running_max[i] = max(running_max[i-1], cumulative[i])

    drawdown = (cumulative - running_max) / running_max

    return np.min(drawdown)


@njit(cache=True, fastmath=True, parallel=True)
def calculate_volatility_jit(returns: np.ndarray) -> float:
    """计算波动率（JIT优化）"""
    if len(returns) == 0:
        return 0.0

    return np.std(returns) * np.sqrt(252)


# 技术指标函数
@njit(cache=True, fastmath=True, parallel=True)
def moving_average_jit(prices: np.ndarray, window: int) -> np.ndarray:
    """移动平均（JIT优化）"""
    n = len(prices)
    ma = np.zeros(n)

    for i in prange(window-1, n):
        ma[i] = np.mean(prices[i-window+1:i+1])

    return ma


@njit(cache=True, fastmath=True)
def rsi_jit(prices: np.ndarray, window: int = 14) -> np.ndarray:
    """RSI指标（JIT优化）"""
    n = len(prices)
    rsi = np.zeros(n)

    if n < window + 1:
        return rsi

    # 计算价格变化
    deltas = np.diff(prices)

    # 分离涨跌
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # 计算初始平均涨跌幅
    avg_gain = np.mean(gains[:window])
    avg_loss = np.mean(losses[:window])

    # 计算RSI
    for i in range(window, n-1):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window

        if avg_loss == 0:
            rsi[i+1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i+1] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


# 批量计算优化
@njit(cache=True, fastmath=True, parallel=True)
def batch_calculate_metrics(returns_matrix: np.ndarray) -> np.ndarray:
    """批量计算多个策略的指标（JIT优化）"""
    n_strategies, n_periods = returns_matrix.shape
    metrics = np.zeros((n_strategies, 4))  # sharpe, max_dd, volatility, total_return

    for i in prange(n_strategies):
        returns = returns_matrix[i, :]

        # Sharpe比率
        metrics[i, 0] = calculate_sharpe_ratio_jit(returns)

        # 最大回撤
        metrics[i, 1] = calculate_max_drawdown_jit(returns)

        # 波动率
        metrics[i, 2] = calculate_volatility_jit(returns)

        # 总收益率
        metrics[i, 3] = np.prod(1 + returns) - 1

    return metrics


# 全局JIT优化器实例
jit_optimizer = JITOptimizer()
