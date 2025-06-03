import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


class StrategyBacktester:
    """
    策略回测引擎，用于回测交易策略的表现
    """

    def __init__(self, data, initial_capital=100000, position_size=1.0,
                 commission_pct=0.001, slippage_pct=0.001):
        """
        初始化回测引擎

        参数:
            data: DataFrame，包含价格数据和信号数据
            initial_capital: float，初始资金
            position_size: float，每次交易的仓位大小（占总资金的比例）
            commission_pct: float，交易成本百分比
            slippage_pct: float，滑点百分比
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

        # 确保数据有日期索引
        if not isinstance(self.data.index, pd.DatetimeIndex):
            raise ValueError("数据必须有日期索引")

        # 初始化结果数据
        self.results = None

        # 交易日志
        self.trades = []

    def run_backtest(self, signal_col='signal', price_col='close', stop_loss_pct=None,
                     take_profit_pct=None, max_holding_periods=None):
        """
        运行回测

        参数:
            signal_col: str，信号列名
            price_col: str，价格列名
            stop_loss_pct: float，止损百分比，可选
            take_profit_pct: float，止盈百分比，可选
            max_holding_periods: int，最大持有期，可选

        返回:
            DataFrame: 包含回测结果的DataFrame
        """
        if signal_col not in self.data.columns:
            raise ValueError(f"数据中缺少信号列: {signal_col}")
        if price_col not in self.data.columns:
            raise ValueError(f"数据中缺少价格列: {price_col}")

        # 复制数据用于回测
        results = self.data.copy()

        # 初始化列
        results['position'] = 0
        results['entry_price'] = np.nan
        results['entry_date'] = None
        results['exit_price'] = np.nan
        results['exit_date'] = None
        results['holding_periods'] = 0
        results['exit_reason'] = ''
        results['capital'] = self.initial_capital
        results['equity'] = self.initial_capital
        results['returns'] = 0.0
        results['trade_profit'] = 0.0
        results['commission'] = 0.0

        # 当前持仓状态
        current_position = 0
        entry_price = 0
        entry_date = None

        # 当前账户状态
        current_capital = self.initial_capital
        current_equity = self.initial_capital

        # 遍历数据进行回测
        for i in range(len(results)):
            current_row = results.iloc[i]
            current_date = results.index[i]
            current_price = current_row[price_col]
            current_signal = current_row[signal_col]

            # 更新持有期
            if current_position != 0:
                results.loc[results.index[i], 'holding_periods'] = (
                    current_date - entry_date).days

            # 检查是否需要根据止损止盈平仓
            exit_triggered = False
            exit_reason = ''

            if current_position != 0:
                # 止损检查
                if stop_loss_pct is not None:
                    if (current_position == 1 and
                            current_price <= entry_price * (1 - stop_loss_pct)):
                        exit_triggered = True
                        exit_reason = 'Stop Loss'
                    elif (current_position == -1 and
                          current_price >= entry_price * (1 + stop_loss_pct)):
                        exit_triggered = True
                        exit_reason = 'Stop Loss'

                # 止盈检查
                if not exit_triggered and take_profit_pct is not None:
                    if (current_position == 1 and
                            current_price >= entry_price * (1 + take_profit_pct)):
                        exit_triggered = True
                        exit_reason = 'Take Profit'
                    elif (current_position == -1 and
                          current_price <= entry_price * (1 - take_profit_pct)):
                        exit_triggered = True
                        exit_reason = 'Take Profit'

                # 最大持有期检查
                if not exit_triggered and max_holding_periods is not None:
                    if results.loc[results.index[i], 'holding_periods'] >= max_holding_periods:
                        exit_triggered = True
                        exit_reason = 'Max Holding Period'

            # 处理信号或触发平仓
            if (current_position == 0 and current_signal != 0) or (current_position != 0 and
                                                                   (current_signal == -current_position or exit_triggered)):
                # 计算交易成本和滑点
                commission = current_price * self.commission_pct
                slippage = current_price * self.slippage_pct

                # 更新账户状态
                if current_position == 0:  # 开仓
                    # 多头开仓
                    if current_signal == 1:
                        current_position = 1
                        entry_price = current_price + slippage
                        entry_date = current_date
                    # 空头开仓
                    elif current_signal == -1:
                        current_position = -1
                        entry_price = current_price - slippage
                        entry_date = current_date

                    # 记录开仓信息
                    results.loc[results.index[i],
                                'position'] = current_position
                    results.loc[results.index[i], 'entry_price'] = entry_price
                    results.loc[results.index[i], 'entry_date'] = entry_date
                    results.loc[results.index[i], 'commission'] += commission

                    # 记录交易
                    trade = {
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'position': current_position,
                        'size': current_capital * self.position_size,
                        'commission': commission
                    }
                    self.trades.append(trade)

                else:  # 平仓
                    exit_price = current_price
                    if current_position == 1:  # 多头平仓
                        exit_price = current_price - slippage
                    elif current_position == -1:  # 空头平仓
                        exit_price = current_price + slippage

                    # 计算交易收益
                    if current_position == 1:
                        trade_profit = (exit_price / entry_price - 1) * \
                            self.position_size * current_capital
                    else:
                        trade_profit = (1 - exit_price / entry_price) * \
                            self.position_size * current_capital

                    # 减去交易成本
                    trade_profit -= commission * current_capital * self.position_size

                    # 更新资金
                    current_capital += trade_profit

                    # 记录平仓信息
                    results.loc[results.index[i], 'position'] = 0
                    results.loc[results.index[i], 'exit_price'] = exit_price
                    results.loc[results.index[i], 'exit_date'] = current_date
                    results.loc[results.index[i],
                                'exit_reason'] = exit_reason if exit_triggered else 'Signal'
                    results.loc[results.index[i],
                                'trade_profit'] = trade_profit
                    results.loc[results.index[i], 'commission'] += commission

                    # 更新交易记录
                    if self.trades:
                        self.trades[-1]['exit_date'] = current_date
                        self.trades[-1]['exit_price'] = exit_price
                        self.trades[-1]['exit_reason'] = exit_reason if exit_triggered else 'Signal'
                        self.trades[-1]['profit'] = trade_profit
                        self.trades[-1]['return'] = trade_profit / \
                            (self.trades[-1]['size'])

                    # 重置持仓状态
                    current_position = 0
                    entry_price = 0
                    entry_date = None

            else:
                # 保持当前持仓
                results.loc[results.index[i], 'position'] = current_position

                if current_position != 0:
                    results.loc[results.index[i], 'entry_price'] = entry_price
                    results.loc[results.index[i], 'entry_date'] = entry_date

            # 更新权益，考虑未实现收益
            if current_position != 0:
                if current_position == 1:
                    unrealized_profit = (
                        current_price / entry_price - 1) * self.position_size * current_capital
                else:
                    unrealized_profit = (
                        1 - current_price / entry_price) * self.position_size * current_capital
                current_equity = current_capital + unrealized_profit
            else:
                current_equity = current_capital

            results.loc[results.index[i], 'capital'] = current_capital
            results.loc[results.index[i], 'equity'] = current_equity

            # 计算收益率
            if i > 0:
                results.loc[results.index[i], 'returns'] = results.loc[results.index[i],
                                                                       'equity'] / results.loc[results.index[i-1], 'equity'] - 1

        # 保存结果
        self.results = results

        return results

    def calculate_metrics(self, risk_free_rate=0.02, trading_days=252):
        """
        计算回测结果的表现指标

        参数:
            risk_free_rate: float，无风险收益率（年化）
            trading_days: int，一年的交易日数量

        返回:
            dict: 包含表现指标的字典
        """
        if self.results is None:
            raise ValueError("请先运行回测")

        # 提取收益序列
        returns = self.results['returns']

        # 计算总收益
        total_return = (
            self.results['equity'].iloc[-1] / self.initial_capital) - 1

        # 计算年化收益
        years = len(returns) / trading_days
        annualized_return = (1 + total_return) ** (1 / years) - 1

        # 计算年化波动率
        annualized_volatility = returns.std() * np.sqrt(trading_days)

        # 计算夏普比率
        daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days) - 1
        sharpe_ratio = (returns.mean() - daily_risk_free) * \
            trading_days / annualized_volatility

        # 计算最大回撤
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns / running_max) - 1
        max_drawdown = drawdown.min()

        # 计算卡玛比率
        calmar_ratio = annualized_return / \
            abs(max_drawdown) if max_drawdown != 0 else 0

        # 计算交易统计
        if self.trades:
            total_trades = len(self.trades)
            winning_trades = sum(
                1 for trade in self.trades if trade.get('profit', 0) > 0)
            losing_trades = sum(
                1 for trade in self.trades if trade.get('profit', 0) <= 0)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            winning_returns = [trade['return']
                               for trade in self.trades if trade.get('profit', 0) > 0]
            losing_returns = [trade['return']
                              for trade in self.trades if trade.get('profit', 0) <= 0]

            avg_win = np.mean(winning_returns) if winning_returns else 0
            avg_loss = np.mean(losing_returns) if losing_returns else 0

            profit_factor = abs(
                sum(winning_returns) / sum(losing_returns)) if sum(losing_returns) != 0 else 0

            # 计算平均持有期
            holding_periods = []
            for trade in self.trades:
                if 'entry_date' in trade and 'exit_date' in trade:
                    holding_period = (
                        trade['exit_date'] - trade['entry_date']).days
                    holding_periods.append(holding_period)

            avg_holding_period = np.mean(
                holding_periods) if holding_periods else 0

        else:
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            avg_holding_period = 0

        # 汇总指标
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_holding_period': avg_holding_period
        }

        return metrics

    def plot_results(self, benchmark_data=None, figsize=(15, 10)):
        """
        绘制回测结果图表

        参数:
            benchmark_data: DataFrame，包含基准数据，可选
            figsize: tuple，图形大小

        返回:
            matplotlib.figure.Figure: 图形对象
        """
        if self.results is None:
            raise ValueError("请先运行回测")

        fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True,
                                 gridspec_kw={'height_ratios': [2, 1, 1]})

        # 绘制权益曲线
        axes[0].plot(self.results.index, self.results['equity'],
                     label='Strategy Equity')
        axes[0].set_title('Backtest Results', fontsize=15)
        axes[0].set_ylabel('Equity')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # 如果有基准数据，同时绘制
        if benchmark_data is not None:
            if 'close' in benchmark_data.columns:
                # 调整基准数据规模与策略相同
                benchmark_scaled = benchmark_data['close'] / \
                    benchmark_data['close'].iloc[0] * self.initial_capital
                axes[0].plot(benchmark_data.index, benchmark_scaled,
                             label='Benchmark', alpha=0.7)
                axes[0].legend()

        # 绘制持仓
        axes[1].plot(self.results.index,
                     self.results['position'], label='Position')
        axes[1].set_ylabel('Position\n(1=Long, -1=Short, 0=Flat)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        # 绘制回撤
        equity_series = self.results['equity']
        running_max = equity_series.cummax()
        drawdown = (equity_series / running_max) - 1

        axes[2].fill_between(self.results.index, drawdown,
                             0, color='red', alpha=0.3)
        axes[2].plot(self.results.index, drawdown,
                     color='red', label='Drawdown')
        axes[2].set_ylabel('Drawdown')
        axes[2].set_xlabel('Date')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        # 设置刻度格式
        import matplotlib.ticker as mtick
        axes[2].yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        # 标注交易点
        for trade in self.trades:
            if 'entry_date' in trade and trade['position'] == 1:  # 多头开仓
                axes[0].scatter(trade['entry_date'], self.results.loc[trade['entry_date'], 'equity'],
                                color='green', marker='^', s=50)
            elif 'entry_date' in trade and trade['position'] == -1:  # 空头开仓
                axes[0].scatter(trade['entry_date'], self.results.loc[trade['entry_date'], 'equity'],
                                color='red', marker='v', s=50)

            if 'exit_date' in trade:
                color = 'green' if trade.get('profit', 0) > 0 else 'red'
                axes[0].scatter(trade['exit_date'], self.results.loc[trade['exit_date'], 'equity'],
                                color=color, marker='o', s=30)

        plt.tight_layout()

        return fig

    def save_results(self, file_path):
        """
        保存回测结果

        参数:
            file_path: str，文件保存路径（不含扩展名）
        """
        if self.results is None:
            raise ValueError("请先运行回测")

        # 保存回测数据
        df = self.results.copy()
        # 添加统计行
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        mean_row = df[numeric_cols].mean().to_dict()
        max_row = df[numeric_cols].max().to_dict()
        min_row = df[numeric_cols].min().to_dict()
        mean_row.update({c: '' for c in df.columns if c not in numeric_cols})
        max_row.update({c: '' for c in df.columns if c not in numeric_cols})
        min_row.update({c: '' for c in df.columns if c not in numeric_cols})
        mean_row['备注'] = '均值'
        max_row['备注'] = '最大'
        min_row['备注'] = '最小'
        df['备注'] = ''
        df = pd.concat([df, pd.DataFrame([mean_row, max_row, min_row], columns=df.columns)], ignore_index=True)
        df.to_csv(f"{file_path}_results.csv", index=False)
        # 保存交易记录
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(f"{file_path}_trades.csv")
        # 计算并保存指标
        metrics = self.calculate_metrics()
        with open(f"{file_path}_metrics.txt", 'w') as f:
            f.write("===== Backtest Results =====\n")
            for key, value in metrics.items():
                if isinstance(value, float):
                    if key in ['total_return', 'annualized_return', 'max_drawdown', 'win_rate', 'avg_win', 'avg_loss']:
                        f.write(f"{key}: {value:.2%}\n")
                    else:
                        f.write(f"{key}: {value:.4f}\n")
                else:
                    f.write(f"{key}: {value}\n")
        # 保存图表
        fig = self.plot_results()
        fig.savefig(f"{file_path}_chart.png")
        plt.close(fig)


def backtest_strategy(data, signal_col='signal', price_col='close',
                      initial_capital=100000, position_size=1.0,
                      commission_pct=0.001, slippage_pct=0.001,
                      stop_loss_pct=None, take_profit_pct=None,
                      max_holding_periods=None):
    """
    快速回测交易策略

    参数:
        data: DataFrame，包含价格数据和信号数据
        signal_col: str，信号列名
        price_col: str，价格列名
        initial_capital: float，初始资金
        position_size: float，每次交易的仓位大小（占总资金的比例）
        commission_pct: float，交易成本百分比
        slippage_pct: float，滑点百分比
        stop_loss_pct: float，止损百分比，可选
        take_profit_pct: float，止盈百分比，可选
        max_holding_periods: int，最大持有期，可选

    返回:
        tuple: (DataFrame: 回测结果, dict: 表现指标, matplotlib.figure.Figure: 图形对象)
    """
    # 创建回测引擎
    backtester = StrategyBacktester(
        data=data,
        initial_capital=initial_capital,
        position_size=position_size,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct
    )

    # 运行回测
    results = backtester.run_backtest(
        signal_col=signal_col,
        price_col=price_col,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        max_holding_periods=max_holding_periods
    )

    # 计算指标
    metrics = backtester.calculate_metrics()

    # 绘制结果
    fig = backtester.plot_results()

    return results, metrics, fig, backtester
