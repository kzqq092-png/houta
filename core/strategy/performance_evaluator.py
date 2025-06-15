"""
策略性能评估器 - 高精度策略性能评估和分析

提供全面的策略性能指标计算，注重准确性和可扩展性
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
import math

from .base_strategy import StrategySignal, SignalType


class PerformanceMetric(Enum):
    """性能指标枚举"""
    TOTAL_RETURN = "total_return"                    # 总收益率
    ANNUAL_RETURN = "annual_return"                  # 年化收益率
    SHARPE_RATIO = "sharpe_ratio"                    # 夏普比率
    SORTINO_RATIO = "sortino_ratio"                  # 索提诺比率
    MAX_DRAWDOWN = "max_drawdown"                    # 最大回撤
    VOLATILITY = "volatility"                        # 波动率
    WIN_RATE = "win_rate"                           # 胜率
    PROFIT_LOSS_RATIO = "profit_loss_ratio"         # 盈亏比
    CALMAR_RATIO = "calmar_ratio"                   # 卡玛比率
    INFORMATION_RATIO = "information_ratio"          # 信息比率
    BETA = "beta"                                   # 贝塔系数
    ALPHA = "alpha"                                 # 阿尔法系数
    TREYNOR_RATIO = "treynor_ratio"                 # 特雷诺比率
    VAR = "value_at_risk"                           # 风险价值
    CVAR = "conditional_var"                        # 条件风险价值


@dataclass
class TradeResult:
    """交易结果"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    signal_type: SignalType
    quantity: float = 1.0
    commission: float = 0.0

    @property
    def return_rate(self) -> float:
        """收益率"""
        if self.signal_type == SignalType.BUY:
            return (self.exit_price - self.entry_price) / self.entry_price
        elif self.signal_type == SignalType.SELL:
            return (self.entry_price - self.exit_price) / self.entry_price
        return 0.0

    @property
    def profit_loss(self) -> float:
        """盈亏金额"""
        base_pnl = (self.exit_price - self.entry_price) * self.quantity
        if self.signal_type == SignalType.SELL:
            base_pnl = -base_pnl
        return base_pnl - self.commission

    @property
    def holding_period(self) -> timedelta:
        """持仓时间"""
        return self.exit_time - self.entry_time

    @property
    def is_profitable(self) -> bool:
        """是否盈利"""
        return self.profit_loss > 0


@dataclass
class StrategyMetrics:
    """策略性能指标"""
    # 基础指标
    total_return: float = 0.0
    annual_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0

    # 交易指标
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    average_return: float = 0.0

    # 风险指标
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    treynor_ratio: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0

    # 时间指标
    evaluation_period: timedelta = field(default_factory=lambda: timedelta(days=0))
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 扩展指标
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (int, float, str, bool)):
                result[field_name] = field_value
            elif isinstance(field_value, datetime):
                result[field_name] = field_value.isoformat()
            elif isinstance(field_value, timedelta):
                result[field_name] = field_value.total_seconds()
            elif isinstance(field_value, dict):
                result[field_name] = field_value
        return result


class StrategyPerformanceEvaluator:
    """策略性能评估器 - 高精度性能分析"""

    def __init__(self, risk_free_rate: float = 0.03, max_workers: int = 4):
        """初始化性能评估器

        Args:
            risk_free_rate: 无风险利率
            max_workers: 最大工作线程数
        """
        self.risk_free_rate = risk_free_rate
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 缓存和统计
        self._evaluation_cache: Dict[str, StrategyMetrics] = {}
        self._cache_lock = threading.RLock()
        self._evaluation_stats = {
            'total_evaluations': 0,
            'cache_hits': 0,
            'evaluation_errors': 0
        }

        # 自定义指标函数
        self._custom_metrics: Dict[str, callable] = {}

    def evaluate_strategy_performance(self, signals: List[StrategySignal],
                                      price_data: pd.DataFrame,
                                      benchmark_data: Optional[pd.DataFrame] = None,
                                      initial_capital: float = 100000.0,
                                      commission_rate: float = 0.001,
                                      use_cache: bool = True) -> StrategyMetrics:
        """评估策略性能

        Args:
            signals: 策略信号列表
            price_data: 价格数据
            benchmark_data: 基准数据
            initial_capital: 初始资金
            commission_rate: 手续费率
            use_cache: 是否使用缓存

        Returns:
            策略性能指标
        """
        # 检查缓存
        cache_key = None
        if use_cache:
            cache_key = self._generate_cache_key(signals, price_data, initial_capital, commission_rate)
            with self._cache_lock:
                if cache_key in self._evaluation_cache:
                    self._evaluation_stats['cache_hits'] += 1
                    return self._evaluation_cache[cache_key]

        self._evaluation_stats['total_evaluations'] += 1

        try:
            # 生成交易记录
            trades = self._generate_trades(signals, price_data, commission_rate)

            # 计算收益序列
            returns_series = self._calculate_returns_series(trades, price_data, initial_capital)

            # 计算基础指标
            metrics = self._calculate_basic_metrics(returns_series, trades)

            # 计算风险指标
            self._calculate_risk_metrics(metrics, returns_series, benchmark_data)

            # 计算交易指标
            self._calculate_trade_metrics(metrics, trades)

            # 计算自定义指标
            self._calculate_custom_metrics(metrics, signals, price_data, trades)

            # 设置时间信息
            if not price_data.empty:
                metrics.start_date = price_data.index[0]
                metrics.end_date = price_data.index[-1]
                metrics.evaluation_period = metrics.end_date - metrics.start_date

            # 缓存结果
            if use_cache and cache_key:
                with self._cache_lock:
                    self._evaluation_cache[cache_key] = metrics

            return metrics

        except Exception as e:
            self._evaluation_stats['evaluation_errors'] += 1
            warnings.warn(f"Performance evaluation failed: {e}")
            return StrategyMetrics()

    def _generate_trades(self, signals: List[StrategySignal],
                         price_data: pd.DataFrame,
                         commission_rate: float) -> List[TradeResult]:
        """生成交易记录"""
        trades = []
        open_positions = {}  # 存储开仓信号

        for signal in signals:
            signal_time = signal.timestamp
            signal_price = signal.price

            if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                # 开仓信号
                position_key = f"{signal.strategy_name}_{signal.signal_type.value}"
                open_positions[position_key] = signal

            elif signal.signal_type in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
                # 平仓信号
                if signal.signal_type == SignalType.CLOSE_LONG:
                    position_key = f"{signal.strategy_name}_buy"
                else:
                    position_key = f"{signal.strategy_name}_sell"

                if position_key in open_positions:
                    entry_signal = open_positions[position_key]

                    # 计算手续费
                    commission = (entry_signal.price + signal_price) * commission_rate

                    # 创建交易记录
                    trade = TradeResult(
                        entry_time=entry_signal.timestamp,
                        exit_time=signal_time,
                        entry_price=entry_signal.price,
                        exit_price=signal_price,
                        signal_type=entry_signal.signal_type,
                        commission=commission
                    )

                    trades.append(trade)
                    del open_positions[position_key]

        # 处理未平仓的信号（使用最后价格平仓）
        if not price_data.empty and open_positions:
            last_price = price_data['close'].iloc[-1]
            last_time = price_data.index[-1]

            for position_key, entry_signal in open_positions.items():
                commission = (entry_signal.price + last_price) * commission_rate

                trade = TradeResult(
                    entry_time=entry_signal.timestamp,
                    exit_time=last_time,
                    entry_price=entry_signal.price,
                    exit_price=last_price,
                    signal_type=entry_signal.signal_type,
                    commission=commission
                )

                trades.append(trade)

        return trades

    def _calculate_returns_series(self, trades: List[TradeResult],
                                  price_data: pd.DataFrame,
                                  initial_capital: float) -> pd.Series:
        """计算收益序列"""
        if price_data.empty:
            return pd.Series(dtype=float)

        # 创建日收益率序列
        returns = pd.Series(0.0, index=price_data.index)
        portfolio_value = initial_capital

        for trade in trades:
            # 计算交易收益
            trade_return = trade.return_rate

            # 找到最接近的交易日期
            try:
                trade_date = returns.index[returns.index.get_indexer([trade.exit_time], method='nearest')[0]]
                returns.loc[trade_date] += trade_return
            except (IndexError, KeyError):
                continue

        # 计算累积收益
        cumulative_returns = (1 + returns).cumprod() - 1

        return returns

    def _calculate_basic_metrics(self, returns_series: pd.Series,
                                 trades: List[TradeResult]) -> StrategyMetrics:
        """计算基础指标"""
        metrics = StrategyMetrics()

        if returns_series.empty:
            return metrics

        # 总收益率
        metrics.total_return = (1 + returns_series).prod() - 1

        # 年化收益率
        if len(returns_series) > 0:
            trading_days = len(returns_series)
            years = trading_days / 252  # 假设一年252个交易日
            if years > 0:
                metrics.annual_return = (1 + metrics.total_return) ** (1 / years) - 1

        # 波动率（年化）
        if len(returns_series) > 1:
            metrics.volatility = returns_series.std() * np.sqrt(252)

        # 夏普比率
        if metrics.volatility > 0:
            excess_return = metrics.annual_return - self.risk_free_rate
            metrics.sharpe_ratio = excess_return / metrics.volatility

        # 最大回撤
        cumulative_returns = (1 + returns_series).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        metrics.max_drawdown = abs(drawdown.min())

        # 索提诺比率
        negative_returns = returns_series[returns_series < 0]
        if len(negative_returns) > 0:
            downside_deviation = negative_returns.std() * np.sqrt(252)
            if downside_deviation > 0:
                excess_return = metrics.annual_return - self.risk_free_rate
                metrics.sortino_ratio = excess_return / downside_deviation

        # 卡玛比率
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annual_return / metrics.max_drawdown

        return metrics

    def _calculate_risk_metrics(self, metrics: StrategyMetrics,
                                returns_series: pd.Series,
                                benchmark_data: Optional[pd.DataFrame] = None):
        """计算风险指标"""
        if returns_series.empty:
            return

        # VaR和CVaR (95%置信度)
        if len(returns_series) > 0:
            sorted_returns = returns_series.sort_values()
            var_index = int(0.05 * len(sorted_returns))
            if var_index < len(sorted_returns):
                metrics.var_95 = abs(sorted_returns.iloc[var_index])
                metrics.cvar_95 = abs(sorted_returns.iloc[:var_index].mean())

        # 与基准的相关指标
        if benchmark_data is not None and not benchmark_data.empty:
            try:
                # 对齐时间序列
                aligned_data = pd.concat([returns_series, benchmark_data['close'].pct_change()],
                                         axis=1, join='inner').dropna()

                if len(aligned_data) > 1:
                    strategy_returns = aligned_data.iloc[:, 0]
                    benchmark_returns = aligned_data.iloc[:, 1]

                    # 贝塔系数
                    covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
                    benchmark_variance = np.var(benchmark_returns)
                    if benchmark_variance > 0:
                        metrics.beta = covariance / benchmark_variance

                    # 阿尔法系数
                    benchmark_annual_return = (1 + benchmark_returns.mean()) ** 252 - 1
                    metrics.alpha = metrics.annual_return - (self.risk_free_rate +
                                                             metrics.beta * (benchmark_annual_return - self.risk_free_rate))

                    # 特雷诺比率
                    if metrics.beta != 0:
                        excess_return = metrics.annual_return - self.risk_free_rate
                        metrics.treynor_ratio = excess_return / metrics.beta

                    # 信息比率
                    active_returns = strategy_returns - benchmark_returns
                    tracking_error = active_returns.std() * np.sqrt(252)
                    if tracking_error > 0:
                        metrics.information_ratio = (metrics.annual_return - benchmark_annual_return) / tracking_error

            except Exception as e:
                warnings.warn(f"Failed to calculate benchmark-related metrics: {e}")

    def _calculate_trade_metrics(self, metrics: StrategyMetrics, trades: List[TradeResult]):
        """计算交易指标"""
        if not trades:
            return

        metrics.total_trades = len(trades)

        # 盈利和亏损交易
        profitable_trades = [t for t in trades if t.is_profitable]
        losing_trades = [t for t in trades if not t.is_profitable]

        metrics.winning_trades = len(profitable_trades)
        metrics.losing_trades = len(losing_trades)

        # 胜率
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades

        # 平均收益率
        if trades:
            metrics.average_return = np.mean([t.return_rate for t in trades])

        # 盈亏比
        if profitable_trades and losing_trades:
            avg_profit = np.mean([t.profit_loss for t in profitable_trades])
            avg_loss = abs(np.mean([t.profit_loss for t in losing_trades]))
            if avg_loss > 0:
                metrics.profit_loss_ratio = avg_profit / avg_loss

    def _calculate_custom_metrics(self, metrics: StrategyMetrics,
                                  signals: List[StrategySignal],
                                  price_data: pd.DataFrame,
                                  trades: List[TradeResult]):
        """计算自定义指标"""
        for metric_name, metric_func in self._custom_metrics.items():
            try:
                value = metric_func(signals, price_data, trades)
                metrics.custom_metrics[metric_name] = float(value)
            except Exception as e:
                warnings.warn(f"Failed to calculate custom metric '{metric_name}': {e}")

    def register_custom_metric(self, name: str, metric_function: callable):
        """注册自定义指标

        Args:
            name: 指标名称
            metric_function: 指标计算函数，接收(signals, price_data, trades)参数
        """
        self._custom_metrics[name] = metric_function

    def compare_strategies(self, strategy_metrics: Dict[str, StrategyMetrics]) -> pd.DataFrame:
        """比较多个策略的性能"""
        if not strategy_metrics:
            return pd.DataFrame()

        comparison_data = {}

        for strategy_name, metrics in strategy_metrics.items():
            metrics_dict = metrics.to_dict()
            comparison_data[strategy_name] = metrics_dict

        df = pd.DataFrame(comparison_data).T

        # 添加排名
        ranking_columns = ['total_return', 'annual_return', 'sharpe_ratio', 'win_rate']
        for col in ranking_columns:
            if col in df.columns:
                df[f'{col}_rank'] = df[col].rank(ascending=False)

        return df

    def _generate_cache_key(self, signals: List[StrategySignal],
                            price_data: pd.DataFrame,
                            initial_capital: float,
                            commission_rate: float) -> str:
        """生成缓存键"""
        import hashlib

        # 创建信号摘要
        signals_summary = f"{len(signals)}_{hash(tuple(s.timestamp for s in signals[:10]))}"

        # 创建数据摘要
        data_summary = f"{len(price_data)}_{price_data['close'].iloc[0] if not price_data.empty else 0}_{price_data['close'].iloc[-1] if not price_data.empty else 0}"

        # 创建参数摘要
        params_summary = f"{initial_capital}_{commission_rate}"

        key_string = f"{signals_summary}_{data_summary}_{params_summary}"
        return hashlib.md5(key_string.encode()).hexdigest()[:16]

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._evaluation_cache.clear()

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """获取评估统计"""
        stats = self._evaluation_stats.copy()
        total = stats['total_evaluations']
        if total > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total
            stats['error_rate'] = stats['evaluation_errors'] / total
        else:
            stats['cache_hit_rate'] = 0.0
            stats['error_rate'] = 0.0

        with self._cache_lock:
            stats['cache_size'] = len(self._evaluation_cache)

        stats['custom_metrics_count'] = len(self._custom_metrics)

        return stats

    def shutdown(self):
        """关闭评估器"""
        self.executor.shutdown(wait=True)
        self.clear_cache()

    def __del__(self):
        """析构函数"""
        try:
            self.shutdown()
        except:
            pass


# 全局性能评估器实例
_performance_evaluator: Optional[StrategyPerformanceEvaluator] = None
_evaluator_lock = threading.RLock()


def get_performance_evaluator() -> StrategyPerformanceEvaluator:
    """获取全局性能评估器实例

    Returns:
        性能评估器实例
    """
    global _performance_evaluator

    with _evaluator_lock:
        if _performance_evaluator is None:
            _performance_evaluator = StrategyPerformanceEvaluator()

        return _performance_evaluator


def initialize_performance_evaluator() -> StrategyPerformanceEvaluator:
    """初始化性能评估器

    Returns:
        性能评估器实例
    """
    global _performance_evaluator

    with _evaluator_lock:
        _performance_evaluator = StrategyPerformanceEvaluator()
        return _performance_evaluator
