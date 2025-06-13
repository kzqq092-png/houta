#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版回测引擎

主要修复的bug：
1. 交易成本计算错误
2. 资金管理bug
3. 复利计算错误
4. 性能指标计算错误
5. 信号处理逻辑缺陷
6. 持有期计算错误
7. 数据处理问题
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
from typing import Optional, Dict, List, Any, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FixedStrategyBacktester:
    """
    修复版策略回测引擎，解决了原版本中的多个逻辑bug
    """

    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000,
                 position_size: float = 1.0, commission_pct: float = 0.001,
                 slippage_pct: float = 0.001, min_commission: float = 5.0):
        """
        初始化回测引擎

        参数:
            data: DataFrame，包含价格数据和信号数据
            initial_capital: float，初始资金
            position_size: float，每次交易的仓位大小（占总资金的比例）
            commission_pct: float，交易成本百分比
            slippage_pct: float，滑点百分比
            min_commission: float，最小手续费
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.min_commission = min_commission

        # 预处理数据，确保格式正确
        self.data = self._kdata_preprocess(self.data, context="回测引擎初始化")

        # 确保数据有日期索引
        self._ensure_datetime_index()

        # 验证数据完整性
        self._validate_data()

        # 初始化结果数据
        self.results = None
        self.trades = []
        self.metrics = None

    def _ensure_datetime_index(self):
        """确保数据有正确的日期索引"""
        if not isinstance(self.data.index, pd.DatetimeIndex):
            if 'datetime' in self.data.columns:
                self.data['datetime'] = pd.to_datetime(self.data['datetime'])
                self.data = self.data.set_index('datetime')
            else:
                raise ValueError("数据必须有日期索引或datetime列")

    def _validate_data(self):
        """验证数据完整性"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]

        if missing_columns:
            raise ValueError(f"数据缺少必要列: {missing_columns}")

        if len(self.data) < 2:
            raise ValueError("数据长度不足，至少需要2条记录")

        # 检查价格数据的合理性
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if (self.data[col] <= 0).any():
                logger.warning(f"发现非正价格数据在列 {col}")
                self.data = self.data[self.data[col] > 0]

    def run_backtest(self, signal_col: str = 'signal', price_col: str = 'close',
                     stop_loss_pct: Optional[float] = None,
                     take_profit_pct: Optional[float] = None,
                     max_holding_periods: Optional[int] = None,
                     enable_compound: bool = True) -> pd.DataFrame:
        """
        运行回测

        参数:
            signal_col: str，信号列名
            price_col: str，价格列名
            stop_loss_pct: float，止损百分比，可选
            take_profit_pct: float，止盈百分比，可选
            max_holding_periods: int，最大持有期（交易日），可选
            enable_compound: bool，是否启用复利

        返回:
            DataFrame: 包含回测结果的DataFrame
        """
        # 验证输入参数
        if signal_col not in self.data.columns:
            raise ValueError(f"数据中缺少信号列: {signal_col}")
        if price_col not in self.data.columns:
            raise ValueError(f"数据中缺少价格列: {price_col}")

        logger.info(f"开始回测，数据长度: {len(self.data)}")

        # 复制数据用于回测
        results = self.data.copy()

        # 初始化结果列
        self._initialize_result_columns(results)

        # 初始化交易状态
        trade_state = self._initialize_trade_state()

        # 遍历数据进行回测
        for i in range(len(results)):
            current_row = results.iloc[i]
            current_date = results.index[i]
            current_price = current_row[price_col]
            current_signal = current_row[signal_col]

            # 更新持有期（交易日）
            if trade_state['position'] != 0:
                trade_state['holding_periods'] += 1

            # 检查止损止盈和最大持有期
            exit_triggered, exit_reason = self._check_exit_conditions(
                trade_state, current_price, stop_loss_pct, take_profit_pct, max_holding_periods
            )

            # 处理交易信号
            trade_executed = self._process_trading_signals(
                results, i, trade_state, current_signal, current_price,
                exit_triggered, exit_reason, enable_compound
            )

            # 更新账户状态
            self._update_account_status(results, i, trade_state, current_price)

        # 保存结果
        self.results = results
        logger.info(f"回测完成，总交易次数: {len(self.trades)}")

        return results

    def _initialize_result_columns(self, results: pd.DataFrame):
        """初始化结果列"""
        columns_to_add = [
            'position', 'entry_price', 'entry_date', 'exit_price', 'exit_date',
            'holding_periods', 'exit_reason', 'capital', 'equity', 'returns',
            'trade_profit', 'commission', 'shares', 'trade_value'
        ]

        for col in columns_to_add:
            if col in ['entry_price', 'exit_price', 'trade_profit', 'commission', 'returns']:
                results[col] = 0.0
            elif col in ['entry_date', 'exit_date', 'exit_reason']:
                results[col] = None
            elif col in ['position', 'holding_periods', 'shares']:
                results[col] = 0
            elif col in ['capital', 'equity']:
                results[col] = float(self.initial_capital)  # 确保为float类型
            elif col == 'trade_value':
                results[col] = 0.0

    def _initialize_trade_state(self) -> Dict[str, Any]:
        """初始化交易状态"""
        return {
            'position': 0,
            'entry_price': 0.0,
            'entry_date': None,
            'holding_periods': 0,
            'current_capital': self.initial_capital,
            'current_equity': self.initial_capital,
            'shares': 0,
            'entry_value': 0.0
        }

    def _check_exit_conditions(self, trade_state: Dict[str, Any], current_price: float,
                               stop_loss_pct: Optional[float], take_profit_pct: Optional[float],
                               max_holding_periods: Optional[int]) -> Tuple[bool, str]:
        """检查退出条件"""
        if trade_state['position'] == 0:
            return False, ''

        # 止损检查
        if stop_loss_pct is not None:
            if (trade_state['position'] == 1 and
                    current_price <= trade_state['entry_price'] * (1 - stop_loss_pct)):
                return True, 'Stop Loss'
            elif (trade_state['position'] == -1 and
                  current_price >= trade_state['entry_price'] * (1 + stop_loss_pct)):
                return True, 'Stop Loss'

        # 止盈检查
        if take_profit_pct is not None:
            if (trade_state['position'] == 1 and
                    current_price >= trade_state['entry_price'] * (1 + take_profit_pct)):
                return True, 'Take Profit'
            elif (trade_state['position'] == -1 and
                  current_price <= trade_state['entry_price'] * (1 - take_profit_pct)):
                return True, 'Take Profit'

        # 最大持有期检查
        if (max_holding_periods is not None and
                trade_state['holding_periods'] >= max_holding_periods):
            return True, 'Max Holding Period'

        return False, ''

    def _process_trading_signals(self, results: pd.DataFrame, i: int,
                                 trade_state: Dict[str, Any], signal: float,
                                 price: float, exit_triggered: bool, exit_reason: str,
                                 enable_compound: bool) -> bool:
        """处理交易信号"""
        current_date = results.index[i]
        trade_executed = False

        # 处理平仓（止损止盈或信号平仓）
        if trade_state['position'] != 0 and (exit_triggered or signal == -trade_state['position'] or signal == 0):
            self._execute_close_position(results, i, trade_state, price, exit_reason or 'Signal')
            trade_executed = True

        # 处理开仓
        if trade_state['position'] == 0 and signal != 0:
            self._execute_open_position(results, i, trade_state, signal, price, enable_compound)
            trade_executed = True
        # 处理换仓（从多头换到空头或反之）
        elif trade_state['position'] != 0 and signal != 0 and signal != trade_state['position']:
            # 先平仓
            self._execute_close_position(results, i, trade_state, price, 'Position Change')
            # 再开新仓
            self._execute_open_position(results, i, trade_state, signal, price, enable_compound)
            trade_executed = True

        return trade_executed

    def _execute_open_position(self, results: pd.DataFrame, i: int,
                               trade_state: Dict[str, Any], signal: float,
                               price: float, enable_compound: bool):
        """执行开仓"""
        current_date = results.index[i]

        # 计算滑点后的成交价格
        if signal == 1:  # 买入
            execution_price = price * (1 + self.slippage_pct)
        else:  # 卖出
            execution_price = price * (1 - self.slippage_pct)

        # 计算交易金额和股数
        if enable_compound:
            trade_value = trade_state['current_capital'] * self.position_size
        else:
            trade_value = self.initial_capital * self.position_size

        shares = int(trade_value / execution_price)
        actual_trade_value = shares * execution_price

        # 计算手续费
        commission = max(actual_trade_value * self.commission_pct, self.min_commission)

        # 更新交易状态
        trade_state['position'] = int(signal)
        trade_state['entry_price'] = execution_price
        trade_state['entry_date'] = current_date
        trade_state['holding_periods'] = 0
        trade_state['shares'] = shares
        trade_state['entry_value'] = actual_trade_value

        # 修复：开仓时扣除交易金额和手续费
        if signal == 1:  # 买入：扣除买入金额和手续费
            trade_state['current_capital'] -= (actual_trade_value + commission)
        else:  # 卖空：获得卖出金额，扣除手续费
            trade_state['current_capital'] += (actual_trade_value - commission)

        # 记录到结果中
        results.loc[results.index[i], 'position'] = trade_state['position']
        results.loc[results.index[i], 'entry_price'] = execution_price
        results.loc[results.index[i], 'entry_date'] = current_date
        results.loc[results.index[i], 'commission'] = commission
        results.loc[results.index[i], 'shares'] = shares
        results.loc[results.index[i], 'trade_value'] = actual_trade_value

        # 记录交易
        trade = {
            'entry_date': current_date,
            'entry_price': execution_price,
            'position': trade_state['position'],
            'shares': shares,
            'trade_value': actual_trade_value,
            'commission': commission
        }
        self.trades.append(trade)

        logger.debug(f"开仓: {current_date}, 方向: {signal}, 价格: {execution_price:.2f}, 股数: {shares}")

    def _execute_close_position(self, results: pd.DataFrame, i: int,
                                trade_state: Dict[str, Any], price: float, exit_reason: str):
        """执行平仓"""
        current_date = results.index[i]

        # 计算滑点后的成交价格
        if trade_state['position'] == 1:  # 卖出平多
            execution_price = price * (1 - self.slippage_pct)
        else:  # 买入平空
            execution_price = price * (1 + self.slippage_pct)

        # 计算交易金额
        actual_trade_value = trade_state['shares'] * execution_price

        # 计算手续费
        commission = max(actual_trade_value * self.commission_pct, self.min_commission)

        # 修复：平仓时正确处理资金流
        if trade_state['position'] == 1:  # 平多头：卖出获得资金，扣除手续费
            trade_state['current_capital'] += (actual_trade_value - commission)
            trade_profit = actual_trade_value - trade_state['entry_value'] - commission
        else:  # 平空头：买入需要资金，加上手续费
            trade_state['current_capital'] -= (actual_trade_value + commission)
            trade_profit = trade_state['entry_value'] - actual_trade_value - commission

        # 记录到结果中
        results.loc[results.index[i], 'position'] = 0
        results.loc[results.index[i], 'exit_price'] = execution_price
        results.loc[results.index[i], 'exit_date'] = current_date
        results.loc[results.index[i], 'exit_reason'] = exit_reason
        results.loc[results.index[i], 'trade_profit'] = trade_profit
        results.loc[results.index[i], 'commission'] += commission

        # 更新交易记录
        if self.trades:
            self.trades[-1].update({
                'exit_date': current_date,
                'exit_price': execution_price,
                'exit_reason': exit_reason,
                'profit': trade_profit,
                'return_pct': trade_profit / trade_state['entry_value'] if trade_state['entry_value'] > 0 else 0,
                'holding_periods': trade_state['holding_periods']
            })

        logger.debug(f"平仓: {current_date}, 价格: {execution_price:.2f}, 收益: {trade_profit:.2f}")

        # 重置持仓状态
        trade_state['position'] = 0
        trade_state['entry_price'] = 0.0
        trade_state['entry_date'] = None
        trade_state['holding_periods'] = 0
        trade_state['shares'] = 0
        trade_state['entry_value'] = 0.0

    def _update_account_status(self, results: pd.DataFrame, i: int,
                               trade_state: Dict[str, Any], current_price: float):
        """更新账户状态"""
        # 计算未实现收益
        unrealized_profit = 0.0
        if trade_state['position'] != 0:
            current_value = trade_state['shares'] * current_price
            if trade_state['position'] == 1:  # 多头
                unrealized_profit = current_value - trade_state['entry_value']
            else:  # 空头
                unrealized_profit = trade_state['entry_value'] - current_value

        # 更新权益
        trade_state['current_equity'] = trade_state['current_capital'] + unrealized_profit

        # 记录到结果中（确保数据类型正确）
        results.loc[results.index[i], 'capital'] = float(trade_state['current_capital'])
        results.loc[results.index[i], 'equity'] = float(trade_state['current_equity'])

        # 计算收益率
        if i > 0:
            prev_equity = results.loc[results.index[i-1], 'equity']
            if prev_equity > 0:
                returns = (trade_state['current_equity'] / prev_equity) - 1
                results.loc[results.index[i], 'returns'] = float(returns)

    def calculate_metrics(self, risk_free_rate: float = 0.02, trading_days: int = 252) -> Dict[str, Any]:
        """
        计算回测结果的表现指标（修复版）

        参数:
            risk_free_rate: float，无风险收益率（年化）
            trading_days: int，一年的交易日数量

        返回:
            dict: 包含表现指标的字典
        """
        if self.results is None:
            raise ValueError("请先运行回测")

        # 提取收益序列
        returns = self.results['returns'].dropna()
        equity_curve = self.results['equity']

        # 计算总收益
        total_return = (equity_curve.iloc[-1] / self.initial_capital) - 1

        # 计算年化收益
        years = len(returns) / trading_days
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0

        # 计算年化波动率
        if len(returns) > 1:
            annualized_volatility = returns.std() * np.sqrt(trading_days)
        else:
            annualized_volatility = 0

        # 计算夏普比率（修复公式）
        if annualized_volatility > 0:
            daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days) - 1
            excess_return = returns.mean() - daily_risk_free
            sharpe_ratio = excess_return / returns.std() * np.sqrt(trading_days)
        else:
            sharpe_ratio = 0

        # 计算最大回撤（修复算法）
        cumulative_returns = equity_curve / self.initial_capital
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns / running_max) - 1
        max_drawdown = drawdown.min()

        # 计算卡玛比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 计算交易统计
        trade_stats = self._calculate_trade_statistics()

        # 汇总指标
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            **trade_stats
        }

        self.metrics = metrics
        return metrics

    def _calculate_trade_statistics(self) -> Dict[str, Any]:
        """计算交易统计指标"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_holding_period': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }

        completed_trades = [t for t in self.trades if 'profit' in t]
        total_trades = len(completed_trades)

        if total_trades == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_holding_period': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0
            }

        # 分类交易
        winning_trades = [t for t in completed_trades if t['profit'] > 0]
        losing_trades = [t for t in completed_trades if t['profit'] <= 0]

        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        win_rate = winning_count / total_trades

        # 计算平均收益
        avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['profit'] for t in losing_trades]) if losing_trades else 0

        # 计算盈亏比
        total_win = sum(t['profit'] for t in winning_trades)
        total_loss = abs(sum(t['profit'] for t in losing_trades))
        profit_factor = total_win / total_loss if total_loss > 0 else 0

        # 计算平均持有期
        holding_periods = [t.get('holding_periods', 0) for t in completed_trades]
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0

        # 计算连续盈亏
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades(completed_trades)

        return {
            'total_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_holding_period': avg_holding_period,
            'max_consecutive_wins': consecutive_wins,
            'max_consecutive_losses': consecutive_losses
        }

    def _calculate_consecutive_trades(self, trades: List[Dict]) -> Tuple[int, int]:
        """计算最大连续盈亏次数"""
        if not trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade['profit'] > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _kdata_preprocess(self, df: pd.DataFrame, context: str = "分析") -> pd.DataFrame:
        """K线数据预处理（修复版）"""
        if df is None or df.empty:
            logger.warning(f"{context}: 收到空数据")
            return pd.DataFrame()

        df_copy = df.copy()

        # 确保必要的数值列存在
        required_numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_numeric_cols:
            if col not in df_copy.columns:
                if col == 'volume':
                    df_copy[col] = 0
                else:
                    df_copy[col] = df_copy.get('close', 0)

        # 转换为数值类型并处理异常值
        for col in required_numeric_cols:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
            df_copy[col] = df_copy[col].replace([np.inf, -np.inf], np.nan)

        # 删除包含NaN的行
        df_copy = df_copy.dropna(subset=required_numeric_cols)

        # 验证价格数据的逻辑性
        invalid_rows = (
            (df_copy['high'] < df_copy['low']) |
            (df_copy['high'] < df_copy['open']) |
            (df_copy['high'] < df_copy['close']) |
            (df_copy['low'] > df_copy['open']) |
            (df_copy['low'] > df_copy['close'])
        )

        if invalid_rows.any():
            logger.warning(f"{context}: 发现 {invalid_rows.sum()} 行价格数据不合理，已删除")
            df_copy = df_copy[~invalid_rows]

        # 按时间排序
        if isinstance(df_copy.index, pd.DatetimeIndex):
            df_copy = df_copy.sort_index()

        logger.info(f"{context}: 数据预处理完成，有效数据 {len(df_copy)} 行")
        return df_copy

    def plot_results(self, benchmark_data: Optional[pd.DataFrame] = None,
                     figsize: Tuple[int, int] = (15, 12)) -> plt.Figure:
        """
        绘制回测结果图表（增强版）

        参数:
            benchmark_data: DataFrame，包含基准数据，可选
            figsize: tuple，图形大小

        返回:
            matplotlib.figure.Figure: 图形对象
        """
        if self.results is None:
            raise ValueError("请先运行回测")

        fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True,
                                 gridspec_kw={'height_ratios': [3, 1, 1, 1]})

        # 1. 权益曲线
        axes[0].plot(self.results.index, self.results['equity'],
                     label='Strategy Equity', linewidth=2, color='blue')

        if benchmark_data is not None and 'close' in benchmark_data.columns:
            # 调整基准数据规模与策略相同
            benchmark_scaled = (benchmark_data['close'] / benchmark_data['close'].iloc[0] *
                                self.initial_capital)
            axes[0].plot(benchmark_data.index, benchmark_scaled,
                         label='Benchmark', alpha=0.7, color='gray')

        axes[0].set_title('Backtest Results - Equity Curve', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('Equity')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # 2. 回撤曲线
        cumulative_returns = self.results['equity'] / self.initial_capital
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns / running_max) - 1

        axes[1].fill_between(self.results.index, drawdown, 0,
                             alpha=0.3, color='red', label='Drawdown')
        axes[1].set_ylabel('Drawdown')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        # 3. 持仓状态
        position_colors = ['red' if p == -1 else 'green' if p == 1 else 'gray'
                           for p in self.results['position']]
        axes[2].scatter(self.results.index, self.results['position'],
                        c=position_colors, alpha=0.6, s=10)
        axes[2].set_ylabel('Position')
        axes[2].set_ylim(-1.5, 1.5)
        axes[2].grid(True, alpha=0.3)

        # 4. 收益分布
        returns = self.results['returns'].dropna()
        if len(returns) > 0:
            axes[3].hist(returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
            axes[3].axvline(returns.mean(), color='red', linestyle='--',
                            label=f'Mean: {returns.mean():.4f}')
            axes[3].set_ylabel('Frequency')
            axes[3].set_xlabel('Daily Returns')
            axes[3].legend()
            axes[3].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def get_trade_summary(self) -> pd.DataFrame:
        """获取交易汇总表"""
        if not self.trades:
            return pd.DataFrame()

        completed_trades = [t for t in self.trades if 'profit' in t]
        if not completed_trades:
            return pd.DataFrame()

        df = pd.DataFrame(completed_trades)

        # 添加计算列
        if 'return_pct' not in df.columns and 'profit' in df.columns and 'trade_value' in df.columns:
            df['return_pct'] = df['profit'] / df['trade_value']

        return df

    def save_results(self, file_path: str):
        """保存回测结果"""
        if self.results is None:
            raise ValueError("请先运行回测")

        # 保存主要结果
        self.results.to_csv(f"{file_path}_results.csv")

        # 保存交易记录
        trade_df = self.get_trade_summary()
        if not trade_df.empty:
            trade_df.to_csv(f"{file_path}_trades.csv", index=False)

        # 保存性能指标
        if self.metrics:
            metrics_df = pd.DataFrame([self.metrics])
            metrics_df.to_csv(f"{file_path}_metrics.csv", index=False)

        logger.info(f"回测结果已保存到 {file_path}")


def backtest_strategy_fixed(data: pd.DataFrame, signal_col: str = 'signal',
                            price_col: str = 'close', initial_capital: float = 100000,
                            position_size: float = 1.0, commission_pct: float = 0.001,
                            slippage_pct: float = 0.001, stop_loss_pct: Optional[float] = None,
                            take_profit_pct: Optional[float] = None,
                            max_holding_periods: Optional[int] = None,
                            enable_compound: bool = True) -> FixedStrategyBacktester:
    """
    便捷的回测函数（修复版）

    参数:
        data: DataFrame，包含价格数据和信号数据
        signal_col: str，信号列名
        price_col: str，价格列名
        initial_capital: float，初始资金
        position_size: float，每次交易的仓位大小
        commission_pct: float，交易成本百分比
        slippage_pct: float，滑点百分比
        stop_loss_pct: float，止损百分比，可选
        take_profit_pct: float，止盈百分比，可选
        max_holding_periods: int，最大持有期，可选
        enable_compound: bool，是否启用复利

    返回:
        FixedStrategyBacktester: 回测器对象
    """
    backtester = FixedStrategyBacktester(
        data=data,
        initial_capital=initial_capital,
        position_size=position_size,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct
    )

    backtester.run_backtest(
        signal_col=signal_col,
        price_col=price_col,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        max_holding_periods=max_holding_periods,
        enable_compound=enable_compound
    )

    backtester.calculate_metrics()

    return backtester


if __name__ == "__main__":
    # 示例用法
    import numpy as np

    # 创建示例数据
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(42)

    # 生成模拟价格数据
    returns = np.random.normal(0.001, 0.02, len(dates))
    prices = 100 * np.exp(np.cumsum(returns))

    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates)),
        'signal': np.random.choice([-1, 0, 1], len(dates), p=[0.1, 0.8, 0.1])
    }, index=dates)

    # 运行回测
    backtester = backtest_strategy_fixed(
        data=data,
        initial_capital=100000,
        position_size=0.95,
        commission_pct=0.001,
        slippage_pct=0.001,
        stop_loss_pct=0.05,
        take_profit_pct=0.10,
        enable_compound=True
    )

    # 打印结果
    print("回测结果:")
    for key, value in backtester.metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    # 绘制结果
    fig = backtester.plot_results()
    plt.show()
