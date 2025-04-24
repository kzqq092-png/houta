import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

def calculate_returns(df, position_col='position', price_col='close', 
                      include_commission=True, commission_pct=0.001):
    """
    计算交易策略的收益
    
    参数:
        df: DataFrame，包含持仓数据和价格数据
        position_col: str，持仓列名
        price_col: str，价格列名
        include_commission: bool，是否包含交易成本
        commission_pct: float，交易成本百分比
        
    返回:
        DataFrame: 包含收益数据的DataFrame
    """
    if position_col not in df.columns:
        raise ValueError(f"DataFrame中缺少持仓列: {position_col}")
    if price_col not in df.columns:
        raise ValueError(f"DataFrame中缺少价格列: {price_col}")
    
    # 复制DataFrame避免修改原始数据
    result_df = df.copy()
    
    # 计算价格变化比例
    result_df['price_change_pct'] = result_df[price_col].pct_change()
    
    # 初始化交易成本列
    result_df['commission'] = 0.0
    
    # 计算交易标志（position发生变化意味着有交易）
    if 'trade_signal' not in result_df.columns:
        result_df['trade_signal'] = result_df[position_col].diff().fillna(0) != 0
    
    # 根据持仓计算每日收益
    result_df['daily_return'] = result_df['price_change_pct'] * result_df[position_col].shift(1)
    
    # 处理第一行NaN
    result_df['daily_return'].iloc[0] = 0
    
    # 计算交易成本（如果需要）
    if include_commission:
        # 对于每次交易，计算交易成本
        result_df.loc[result_df['trade_signal'], 'commission'] = commission_pct
        
        # 从收益中减去交易成本
        result_df['daily_return'] = result_df['daily_return'] - result_df['commission']
    
    # 计算累积收益
    result_df['cumulative_return'] = (1 + result_df['daily_return']).cumprod() - 1
    
    return result_df

def calculate_performance_metrics(returns_df, daily_return_col='daily_return', risk_free_rate=0.02,
                                 trading_days=252):
    """
    计算策略表现指标
    
    参数:
        returns_df: DataFrame，包含收益数据
        daily_return_col: str，日收益列名
        risk_free_rate: float，无风险收益率（年化）
        trading_days: int，一年的交易日数量
        
    返回:
        dict: 包含各种表现指标的字典
    """
    if daily_return_col not in returns_df.columns:
        raise ValueError(f"DataFrame中缺少收益列: {daily_return_col}")
    
    # 获取每日收益序列
    daily_returns = returns_df[daily_return_col]
    
    # 转化为日度无风险收益率
    daily_rf = (1 + risk_free_rate) ** (1 / trading_days) - 1
    
    # 计算总收益
    total_return = (1 + daily_returns).prod() - 1
    
    # 计算年化收益
    years = len(daily_returns) / trading_days
    annualized_return = (1 + total_return) ** (1 / years) - 1
    
    # 计算年化波动率
    daily_volatility = daily_returns.std()
    annualized_volatility = daily_volatility * np.sqrt(trading_days)
    
    # 计算下行波动率
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(trading_days) if len(downside_returns) > 0 else 0
    
    # 计算夏普比率
    excess_returns = daily_returns - daily_rf
    sharpe_ratio = (excess_returns.mean() * trading_days) / annualized_volatility if annualized_volatility != 0 else 0
    
    # 计算索提诺比率
    sortino_ratio = (annualized_return - risk_free_rate) / downside_volatility if downside_volatility != 0 else 0
    
    # 计算最大回撤
    cum_returns = (1 + daily_returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    max_drawdown = drawdown.min()
    
    # 计算胜率
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0
    
    # 计算盈亏比
    avg_win = daily_returns[daily_returns > 0].mean() if len(daily_returns[daily_returns > 0]) > 0 else 0
    avg_loss = daily_returns[daily_returns < 0].mean() if len(daily_returns[daily_returns < 0]) > 0 else 0
    profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # 计算日收益率的峰度和偏度
    kurtosis = daily_returns.kurtosis()
    skewness = daily_returns.skew()
    
    # 计算卡玛比率
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # 计算信息比率（这里简化，使用与基准的差异，假设基准为0）
    information_ratio = (daily_returns.mean() * trading_days) / (daily_returns.std() * np.sqrt(trading_days)) if daily_returns.std() != 0 else 0
    
    # 计算Beta和Alpha（这里简化，使用市场收益为risk_free_rate）
    # 在实际应用中应该使用实际的市场收益
    beta = 0  # 简化，实际中需要计算与市场的相关性
    alpha = annualized_return - (risk_free_rate + beta * (0.08 - risk_free_rate))  # 假设市场风险溢价为8%
    
    # 计算VAR（Value at Risk）
    var_95 = np.percentile(daily_returns, 5) * np.sqrt(trading_days)
    
    # 计算CVAR（Conditional Value at Risk）
    cvar_95 = daily_returns[daily_returns <= var_95].mean() * np.sqrt(trading_days) if len(daily_returns[daily_returns <= var_95]) > 0 else 0
    
    # 返回指标字典
    metrics = {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'downside_volatility': downside_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'kurtosis': kurtosis,
        'skewness': skewness,
        'calmar_ratio': calmar_ratio,
        'information_ratio': information_ratio,
        'alpha': alpha,
        'beta': beta,
        'var_95': var_95,
        'cvar_95': cvar_95
    }
    
    return metrics

def plot_equity_curve(returns_df, benchmark_df=None, figsize=(15, 8)):
    """
    绘制权益曲线图
    
    参数:
        returns_df: DataFrame，包含策略收益数据
        benchmark_df: DataFrame，包含基准收益数据，可选
        figsize: tuple，图形大小
    """
    if 'cumulative_return' not in returns_df.columns:
        if 'daily_return' in returns_df.columns:
            returns_df['cumulative_return'] = (1 + returns_df['daily_return']).cumprod() - 1
        else:
            raise ValueError("DataFrame中缺少'cumulative_return'或'daily_return'列")
    
    plt.figure(figsize=figsize)
    
    # 绘制策略收益曲线
    plt.plot(returns_df.index, returns_df['cumulative_return'], label='Strategy', color='blue')
    
    # 如果提供了基准数据，则绘制基准收益曲线
    if benchmark_df is not None:
        if 'cumulative_return' not in benchmark_df.columns:
            if 'daily_return' in benchmark_df.columns:
                benchmark_df['cumulative_return'] = (1 + benchmark_df['daily_return']).cumprod() - 1
            else:
                raise ValueError("基准DataFrame中缺少'cumulative_return'或'daily_return'列")
        
        plt.plot(benchmark_df.index, benchmark_df['cumulative_return'], label='Benchmark', color='red')
    
    # 添加网格和图例
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 添加标题和标签
    plt.title('Equity Curve', fontsize=15)
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return (%)')
    
    # 格式化Y轴为百分比
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.2%}'.format(x)))
    
    # 添加零线
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    
    # 计算最大回撤期间并标注
    if 'cumulative_return' in returns_df.columns:
        cum_returns = (1 + returns_df['cumulative_return'])
        running_max = cum_returns.cummax()
        drawdown = (cum_returns / running_max) - 1
        max_dd = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        # 寻找最大回撤的开始点
        temp_df = returns_df.loc[:max_dd_idx].copy()
        drawdown_begin = temp_df['cumulative_return'].idxmax()
        
        # 在图上标注最大回撤区域
        plt.fill_between(returns_df.index, 0, 1, where=(returns_df.index >= drawdown_begin) & (returns_df.index <= max_dd_idx),
                        color='red', alpha=0.3, transform=plt.gca().get_xaxis_transform())
        
        plt.annotate(f'Max Drawdown: {max_dd:.2%}', 
                    xy=(max_dd_idx, returns_df.loc[max_dd_idx, 'cumulative_return']),
                    xytext=(max_dd_idx, returns_df.loc[max_dd_idx, 'cumulative_return'] - 0.1),
                    arrowprops=dict(facecolor='black', arrowstyle='->'),
                    fontsize=10)
    
    plt.tight_layout()
    
    return plt.gcf()

def plot_drawdown_curve(returns_df, figsize=(15, 8)):
    """
    绘制回撤曲线图
    
    参数:
        returns_df: DataFrame，包含收益数据
        figsize: tuple，图形大小
    """
    if 'daily_return' not in returns_df.columns and 'cumulative_return' not in returns_df.columns:
        raise ValueError("DataFrame中缺少'daily_return'或'cumulative_return'列")
    
    # 计算累积收益（如果尚未计算）
    if 'cumulative_return' not in returns_df.columns:
        returns_df['cumulative_return'] = (1 + returns_df['daily_return']).cumprod() - 1
    
    # 计算回撤
    cum_returns = (1 + returns_df['cumulative_return'])
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    
    plt.figure(figsize=figsize)
    
    # 绘制回撤曲线
    plt.plot(returns_df.index, drawdown, color='red')
    plt.fill_between(returns_df.index, drawdown, 0, color='red', alpha=0.3)
    
    # 添加标题和标签
    plt.title('Drawdown Curve', fontsize=15)
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    
    # 格式化Y轴为百分比
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.2%}'.format(x)))
    
    # 添加网格
    plt.grid(True, alpha=0.3)
    
    # 标注最大回撤
    max_dd = drawdown.min()
    max_dd_idx = drawdown.idxmin()
    
    plt.annotate(f'Max Drawdown: {max_dd:.2%}', 
                xy=(max_dd_idx, max_dd),
                xytext=(max_dd_idx, max_dd / 2),
                arrowprops=dict(facecolor='black', arrowstyle='->'),
                fontsize=10)
    
    plt.tight_layout()
    
    return plt.gcf()

def plot_monthly_returns_heatmap(returns_df, daily_return_col='daily_return', figsize=(15, 8)):
    """
    绘制月度收益热力图
    
    参数:
        returns_df: DataFrame，包含收益数据
        daily_return_col: str，日收益列名
        figsize: tuple，图形大小
    """
    if daily_return_col not in returns_df.columns:
        raise ValueError(f"DataFrame中缺少收益列: {daily_return_col}")
    
    # 确保索引是日期类型
    if not isinstance(returns_df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame的索引必须是日期类型")
    
    # 计算月度收益
    monthly_returns = returns_df[daily_return_col].resample('M').apply(
        lambda x: (1 + x).prod() - 1
    )
    
    # 将月度收益数据重塑为年-月表格
    monthly_returns_table = monthly_returns.unstack(level=0)
    
    plt.figure(figsize=figsize)
    
    # 创建热力图
    cmap = plt.cm.RdYlGn  # 红色表示负收益，绿色表示正收益
    monthly_returns_pivot = monthly_returns.groupby([monthly_returns.index.year, monthly_returns.index.month]).first().unstack()
    
    # 设置颜色映射的中心点为0
    vmin = min(monthly_returns_pivot.min().min(), -0.05)  # 最小值至少为-5%
    vmax = max(monthly_returns_pivot.max().max(), 0.05)   # 最大值至少为5%
    max_abs = max(abs(vmin), abs(vmax))
    
    plt.pcolormesh(monthly_returns_pivot, cmap=cmap, vmin=-max_abs, vmax=max_abs)
    
    # 添加颜色条
    plt.colorbar(label='Monthly Return')
    
    # 设置坐标轴标签
    plt.xticks(np.arange(0.5, 12.5), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    plt.yticks(np.arange(0.5, len(monthly_returns_pivot.index) + 0.5), monthly_returns_pivot.index.tolist())
    
    # 在每个单元格中添加收益百分比文本
    for i in range(len(monthly_returns_pivot.index)):
        for j in range(len(monthly_returns_pivot.columns)):
            if not np.isnan(monthly_returns_pivot.iloc[i, j]):
                plt.text(j + 0.5, i + 0.5, f"{monthly_returns_pivot.iloc[i, j]:.2%}",
                        ha='center', va='center', color='black' if abs(monthly_returns_pivot.iloc[i, j]) < 0.1 else 'white')
    
    # 添加标题
    plt.title('Monthly Returns Heatmap', fontsize=15)
    
    plt.tight_layout()
    
    return plt.gcf()

def create_performance_report(returns_df, benchmark_df=None, file_path=None):
    """
    创建完整的表现报告
    
    参数:
        returns_df: DataFrame，包含策略收益数据
        benchmark_df: DataFrame，包含基准收益数据，可选
        file_path: str，报告保存路径，可选
        
    返回:
        dict: 包含绘图和指标的字典
    """
    # 计算性能指标
    metrics = calculate_performance_metrics(returns_df)
    
    # 如果有基准数据，计算基准指标和相对指标
    if benchmark_df is not None:
        benchmark_metrics = calculate_performance_metrics(benchmark_df)
        
        # 计算相对指标
        relative_metrics = {
            'excess_return': metrics['annualized_return'] - benchmark_metrics['annualized_return'],
            'tracking_error': np.sqrt(((returns_df['daily_return'] - benchmark_df['daily_return'])**2).mean()) * np.sqrt(252),
            'information_ratio': (metrics['annualized_return'] - benchmark_metrics['annualized_return']) / 
                               (np.sqrt(((returns_df['daily_return'] - benchmark_df['daily_return'])**2).mean()) * np.sqrt(252))
                               if np.sqrt(((returns_df['daily_return'] - benchmark_df['daily_return'])**2).mean()) != 0 else 0
        }
    else:
        benchmark_metrics = None
        relative_metrics = None
    
    # 创建绘图
    fig1 = plot_equity_curve(returns_df, benchmark_df)
    fig2 = plot_drawdown_curve(returns_df)
    fig3 = plot_monthly_returns_heatmap(returns_df)
    
    # 创建报告字典
    report = {
        'strategy_metrics': metrics,
        'benchmark_metrics': benchmark_metrics,
        'relative_metrics': relative_metrics,
        'equity_curve': fig1,
        'drawdown_curve': fig2,
        'monthly_returns_heatmap': fig3
    }
    
    # 如果提供了文件路径，保存报告
    if file_path:
        # 保存图表
        fig1.savefig(f"{file_path}_equity_curve.png")
        fig2.savefig(f"{file_path}_drawdown_curve.png")
        fig3.savefig(f"{file_path}_monthly_returns_heatmap.png")
        
        # 创建指标报告
        with open(f"{file_path}_metrics_report.txt", 'w') as f:
            f.write("===== Strategy Performance Metrics =====\n")
            for key, value in metrics.items():
                if isinstance(value, float):
                    if key in ['total_return', 'annualized_return', 'max_drawdown', 'win_rate']:
                        f.write(f"{key}: {value:.2%}\n")
                    else:
                        f.write(f"{key}: {value:.4f}\n")
                else:
                    f.write(f"{key}: {value}\n")
            
            if benchmark_metrics:
                f.write("\n===== Benchmark Performance Metrics =====\n")
                for key, value in benchmark_metrics.items():
                    if isinstance(value, float):
                        if key in ['total_return', 'annualized_return', 'max_drawdown', 'win_rate']:
                            f.write(f"{key}: {value:.2%}\n")
                        else:
                            f.write(f"{key}: {value:.4f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            
            if relative_metrics:
                f.write("\n===== Relative Performance Metrics =====\n")
                for key, value in relative_metrics.items():
                    if isinstance(value, float):
                        if key in ['excess_return']:
                            f.write(f"{key}: {value:.2%}\n")
                        else:
                            f.write(f"{key}: {value:.4f}\n")
                    else:
                        f.write(f"{key}: {value}\n")
    
    return report 