import numpy as np
import pandas as pd
from hikyuu import *


def calculate_atr(df, period=14):
    """
    计算ATR (Average True Range)

    参数:
        df (DataFrame): 包含'high', 'low', 'close'列的DataFrame
        period (int): ATR计算周期

    返回:
        Series: ATR值
    """
    df = _kdata_preprocess(df, context="ATR计算")
    if df is None or df.empty:
        return pd.Series(dtype=float)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()


def calculate_drawdown(equity_curve):
    """
    计算回撤

    参数:
        equity_curve (array-like): 资金曲线数据

    返回:
        array: 回撤序列
        float: 最大回撤值
    """
    # 转换为numpy数组
    equity = np.array(equity_curve)

    # 计算累计最大值
    running_max = np.maximum.accumulate(equity)

    # 计算回撤
    drawdown = (equity - running_max) / running_max

    # 最大回撤
    max_drawdown = np.min(drawdown)

    return drawdown, max_drawdown


def calculate_sharpe_ratio(returns, risk_free_rate=0.0, periods_per_year=252):
    """
    计算夏普比率

    参数:
        returns (array-like): 收益率序列
        risk_free_rate (float): 无风险利率
        periods_per_year (int): 每年的周期数 (日=252, 周=52, 月=12)

    返回:
        float: 年化夏普比率
    """
    returns = np.array(returns)
    excess_returns = returns - risk_free_rate

    if len(excess_returns) == 0 or np.std(excess_returns) == 0:
        return 0

    sharpe = np.mean(excess_returns) / np.std(excess_returns)
    annual_sharpe = sharpe * np.sqrt(periods_per_year)

    return annual_sharpe


def calculate_performance_metrics(trades, equity_curve):
    """
    计算交易系统性能指标

    参数:
        trades (list): 交易记录列表
        equity_curve (array-like): 资金曲线数据

    返回:
        dict: 包含各种性能指标的字典
    """
    # 计算收益率序列
    returns = np.diff(equity_curve) / equity_curve[:-1]

    # 计算总收益率
    total_return = (equity_curve[-1] / equity_curve[0]) - 1

    # 计算年化收益率
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1

    # 计算最大回撤
    _, max_drawdown = calculate_drawdown(equity_curve)

    # 计算夏普比率
    sharpe_ratio = calculate_sharpe_ratio(returns)

    # 交易统计
    winning_trades = sum(1 for trade in trades if trade.profit > 0)
    losing_trades = sum(1 for trade in trades if trade.profit < 0)
    total_trades = len(trades)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    # 计算盈亏比
    profits = [trade.profit for trade in trades if trade.profit > 0]
    losses = [abs(trade.profit) for trade in trades if trade.profit < 0]
    profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else float('inf')

    # 平均持仓时间
    avg_hold_days = np.mean([trade.days for trade in trades]) if trades else 0

    # 最大连胜和连败
    max_consecutive_wins = 0
    max_consecutive_losses = 0

    current_wins = 0
    current_losses = 0

    for trade in trades:
        if trade.profit > 0:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        elif trade.profit < 0:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)

    # 创建结果字典
    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'avg_hold_days': avg_hold_days,
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses
    }

    return metrics


def get_optimal_position_size(capital, risk_per_trade, entry_price, stop_loss):
    """
    计算最优仓位大小（基于固定风险）

    参数:
        capital (float): 可用资金
        risk_per_trade (float): 每笔交易的风险比例
        entry_price (float): 入场价格
        stop_loss (float): 止损价格

    返回:
        int: 计算得到的仓位大小（股数）
    """
    # 计算每股风险
    risk_per_share = abs(entry_price - stop_loss)
    if risk_per_share <= 0:
        return 0

    # 计算风险金额
    risk_amount = capital * risk_per_trade

    # 计算可买入数量
    position_size = risk_amount / risk_per_share

    # 向下取整到100的倍数
    position_size = (int(position_size) // 100) * 100

    return position_size if position_size >= 100 else 0


def _kdata_preprocess(df, context="分析"):
    required_cols = ['high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"[{context}] 缺少字段: {missing_cols}，自动补全为默认值")
        for col in missing_cols:
            df[col] = 0.0
    for col in ['high', 'low', 'close', 'volume']:
        before = len(df)
        df = df[df[col].notna() & (df[col] >= 0)]
        after = len(df)
        if after < before:
            print(f"[{context}] 已过滤{before-after}行{col}异常数据")
    if df.empty:
        print(f"[{context}] 数据全部无效，返回空")
    return df.reset_index(drop=True)
