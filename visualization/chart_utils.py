import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.gridspec import GridSpec
import seaborn as sns
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import logging
from hikyuu import *

logger = logging.getLogger(__name__)

class ChartUtils:
    """图表工具类，用于创建和绘制各种交易相关的图表"""
    
    def __init__(self):
        """初始化图表工具类"""
        self.fig = None
        self.ax = None
        self.logger = logging.getLogger(__name__)
        
    def create_figure(self, figsize: Tuple[int, int] = (10, 6)) -> Tuple[plt.Figure, plt.Axes]:
        """
        创建新的图表
        
        Args:
            figsize: 图表大小，默认为(10, 6)
            
        Returns:
            Tuple[plt.Figure, plt.Axes]: 图表和坐标轴对象
        """
        try:
            self.fig = plt.figure(figsize=figsize)
            self.ax = self.fig.add_subplot(111)
            return self.fig, self.ax
        except Exception as e:
            self.logger.error(f"创建图表失败: {str(e)}")
            raise
        
    def plot_candlestick(self, data: pd.DataFrame, title: str = "K线图") -> None:
        """
        绘制K线图
        
        Args:
            data: 包含open, high, low, close的DataFrame
            title: 图表标题
            
        Raises:
            ValueError: 如果数据格式不正确或图表未创建
        """
        if not self.fig or not self.ax:
            raise ValueError("必须先调用create_figure创建图表")
            
        try:
            # 数据验证
            required_columns = ['open', 'high', 'low', 'close']
            if not all(col in data.columns for col in required_columns):
                raise ValueError(f"数据必须包含以下列: {required_columns}")
                
            # 绘制K线图
            self.ax.clear()
            self.ax.set_title(title)
            
            # 计算涨跌颜色
            colors = ['red' if close >= open else 'green' 
                     for open, close in zip(data['open'], data['close'])]
                     
            # 绘制K线
            self.ax.bar(data.index, data['high'] - data['low'], 
                       bottom=data['low'], color=colors, alpha=0.3)
            self.ax.bar(data.index, data['close'] - data['open'], 
                       bottom=data['open'], color=colors, alpha=0.7)
                       
            # 设置x轴格式
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            self.fig.autofmt_xdate()
            
            # 添加网格
            self.ax.grid(True, linestyle='--', alpha=0.7)
            
        except Exception as e:
            self.logger.error(f"绘制K线图失败: {str(e)}")
            raise
        
    def plot_indicator(self, data: pd.Series, label: Optional[str] = None, 
                      color: Optional[str] = None) -> None:
        """
        绘制指标线
        
        Args:
            data: 指标数据
            label: 图例标签
            color: 线条颜色
            
        Raises:
            ValueError: 如果图表未创建
        """
        if not self.fig or not self.ax:
            raise ValueError("必须先调用create_figure创建图表")
            
        try:
            if not isinstance(data, pd.Series):
                raise ValueError("数据必须是pandas Series类型")
                
            self.ax.plot(data.index, data, label=label, color=color)
            if label:
                self.ax.legend()
                
        except Exception as e:
            self.logger.error(f"绘制指标线失败: {str(e)}")
            raise
        
    def clear(self) -> None:
        """清除当前图表"""
        try:
            if self.fig:
                plt.close(self.fig)
            self.fig = None
            self.ax = None
        except Exception as e:
            self.logger.error(f"清除图表失败: {str(e)}")
            raise
        
    @staticmethod
    def create_price_chart(figure, data, signals=None):
        """创建价格图表"""
        figure.clear()
        gs = GridSpec(2, 1, height_ratios=[3, 1])
        
        # 主图：价格和均线
        ax1 = figure.add_subplot(gs[0])
        ax1.plot(data.index, data['close'], label='收盘价', color='blue')
        if 'ma_fast' in data.columns:
            ax1.plot(data.index, data['ma_fast'], label='快速均线', color='orange')
        if 'ma_slow' in data.columns:
            ax1.plot(data.index, data['ma_slow'], label='慢速均线', color='red')
            
        # 添加买卖信号
        if signals is not None:
            buy_signals = signals[signals['signal'] == 1]
            sell_signals = signals[signals['signal'] == -1]
            ax1.scatter(buy_signals.index, buy_signals['price'], 
                       marker='^', color='green', s=100, label='买入信号')
            ax1.scatter(sell_signals.index, sell_signals['price'], 
                       marker='v', color='red', s=100, label='卖出信号')
            
        ax1.set_title('价格走势')
        ax1.legend()
        ax1.grid(True)
        
        # 副图：成交量
        ax2 = figure.add_subplot(gs[1])
        ax2.bar(data.index, data['volume'], color='gray', alpha=0.5)
        ax2.set_title('成交量')
        ax2.grid(True)
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_signal_chart(figure, data):
        """创建信号图表"""
        figure.clear()
        gs = GridSpec(3, 1, height_ratios=[1, 1, 1])
        
        # RSI指标
        ax1 = figure.add_subplot(gs[0])
        ax1.plot(data.index, data['rsi'], label='RSI', color='purple')
        ax1.axhline(y=70, color='r', linestyle='--')
        ax1.axhline(y=30, color='g', linestyle='--')
        ax1.set_title('RSI指标')
        ax1.legend()
        ax1.grid(True)
        
        # MACD指标
        ax2 = figure.add_subplot(gs[1])
        ax2.plot(data.index, data['macd'], label='MACD', color='blue')
        ax2.plot(data.index, data['signal'], label='Signal', color='orange')
        ax2.bar(data.index, data['hist'], label='Histogram', color='gray', alpha=0.5)
        ax2.set_title('MACD指标')
        ax2.legend()
        ax2.grid(True)
        
        # 趋势强度
        ax3 = figure.add_subplot(gs[2])
        ax3.plot(data.index, data['trend_strength'], label='趋势强度', color='green')
        ax3.set_title('趋势强度')
        ax3.legend()
        ax3.grid(True)
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_equity_chart(figure, equity_curve, trades=None):
        """创建资金曲线图表"""
        figure.clear()
        gs = GridSpec(2, 1, height_ratios=[3, 1])
        
        # 主图：资金曲线
        ax1 = figure.add_subplot(gs[0])
        ax1.plot(equity_curve.index, equity_curve['equity'], 
                label='资金曲线', color='blue')
        ax1.plot(equity_curve.index, equity_curve['drawdown'], 
                label='回撤', color='red')
        ax1.set_title('资金曲线')
        ax1.legend()
        ax1.grid(True)
        
        # 副图：每日收益率
        ax2 = figure.add_subplot(gs[1])
        ax2.bar(equity_curve.index, equity_curve['returns'], 
               color=np.where(equity_curve['returns'] >= 0, 'g', 'r'))
        ax2.set_title('每日收益率')
        ax2.grid(True)
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_performance_chart(figure, performance):
        """创建绩效分析图表"""
        figure.clear()
        gs = GridSpec(2, 2)
        
        # 月度收益热力图
        ax1 = figure.add_subplot(gs[0, 0])
        monthly_returns = performance['monthly_returns'].unstack()
        sns.heatmap(monthly_returns, ax=ax1, cmap='RdYlGn', 
                   center=0, annot=True, fmt='.1%')
        ax1.set_title('月度收益热力图')
        
        # 收益分布直方图
        ax2 = figure.add_subplot(gs[0, 1])
        sns.histplot(performance['daily_returns'], ax=ax2, 
                    bins=50, kde=True)
        ax2.set_title('收益分布')
        
        # 滚动收益
        ax3 = figure.add_subplot(gs[1, 0])
        ax3.plot(performance['rolling_returns'])
        ax3.set_title('滚动收益')
        
        # 滚动波动率
        ax4 = figure.add_subplot(gs[1, 1])
        ax4.plot(performance['rolling_volatility'])
        ax4.set_title('滚动波动率')
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_risk_chart(figure, risk_metrics):
        """创建风险分析图表"""
        figure.clear()
        gs = GridSpec(2, 2)
        
        # 回撤分析
        ax1 = figure.add_subplot(gs[0, 0])
        ax1.plot(risk_metrics['drawdown'], label='回撤')
        ax1.plot(risk_metrics['max_drawdown'], label='最大回撤', color='red')
        ax1.set_title('回撤分析')
        ax1.legend()
        ax1.grid(True)
        
        # 风险敞口
        ax2 = figure.add_subplot(gs[0, 1])
        ax2.plot(risk_metrics['risk_exposure'], label='风险敞口')
        ax2.set_title('风险敞口')
        ax2.legend()
        ax2.grid(True)
        
        # 持仓数量
        ax3 = figure.add_subplot(gs[1, 0])
        ax3.plot(risk_metrics['position_count'], label='持仓数量')
        ax3.set_title('持仓数量')
        ax3.legend()
        ax3.grid(True)
        
        # 风险预算使用
        ax4 = figure.add_subplot(gs[1, 1])
        ax4.plot(risk_metrics['risk_budget_used'], label='风险预算使用')
        ax4.set_title('风险预算使用')
        ax4.legend()
        ax4.grid(True)
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_correlation_chart(figure, correlation_matrix):
        """创建相关性分析图表"""
        figure.clear()
        
        # 相关性热力图
        ax = figure.add_subplot(111)
        sns.heatmap(correlation_matrix, ax=ax, cmap='RdYlBu_r', 
                   center=0, annot=True, fmt='.2f')
        ax.set_title('相关性分析')
        
        # 调整布局
        figure.tight_layout()
        
    @staticmethod
    def create_trade_analysis_chart(figure, trades):
        """创建交易分析图表"""
        figure.clear()
        gs = GridSpec(2, 2)
        
        # 交易盈亏分布
        ax1 = figure.add_subplot(gs[0, 0])
        sns.histplot(trades['pnl'], ax=ax1, bins=50, kde=True)
        ax1.set_title('交易盈亏分布')
        
        # 持仓时间分布
        ax2 = figure.add_subplot(gs[0, 1])
        sns.histplot(trades['holding_period'], ax=ax2, bins=50, kde=True)
        ax2.set_title('持仓时间分布')
        
        # 月度交易次数
        ax3 = figure.add_subplot(gs[1, 0])
        monthly_trades = trades.groupby(trades['entry_time'].dt.to_period('M')).size()
        ax3.bar(monthly_trades.index.astype(str), monthly_trades.values)
        ax3.set_title('月度交易次数')
        
        # 交易盈亏热力图
        ax4 = figure.add_subplot(gs[1, 1])
        trades['month'] = trades['entry_time'].dt.to_period('M')
        monthly_pnl = trades.groupby('month')['pnl'].sum().unstack()
        sns.heatmap(monthly_pnl, ax=ax4, cmap='RdYlGn', center=0)
        ax4.set_title('月度盈亏热力图')
        
        # 调整布局
        figure.tight_layout()
        
    def plot_kline(self, ax, kdata):
        """绘制K线图"""
        try:
            # 获取K线数据
            dates = kdata.get_datetime_list()
            opens = kdata.get_open()
            closes = kdata.get_close()
            highs = kdata.get_high()
            lows = kdata.get_low()
            
            # 计算涨跌颜色
            colors = ['red' if c >= o else 'green' for o, c in zip(opens, closes)]
            
            # 绘制K线
            for i in range(len(dates)):
                # 绘制实体
                ax.bar(dates[i], closes[i] - opens[i], bottom=opens[i], 
                      width=0.6, color=colors[i])
                
                # 绘制上下影线
                ax.plot([dates[i], dates[i]], [lows[i], highs[i]], 
                       color=colors[i], linewidth=1)
                
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
        except Exception as e:
            logger.error(f"绘制K线图失败: {str(e)}")
            raise
            
    def plot_volume(self, ax, kdata):
        """绘制成交量图"""
        try:
            dates = kdata.get_datetime_list()
            volumes = kdata.get_volume()
            closes = kdata.get_close()
            opens = kdata.get_open()
            
            # 计算涨跌颜色
            colors = ['red' if c >= o else 'green' for o, c in zip(opens, closes)]
            
            # 绘制成交量柱状图
            ax.bar(dates, volumes, color=colors, alpha=0.5)
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
        except Exception as e:
            logger.error(f"绘制成交量图失败: {str(e)}")
            raise
            
    def create_subplots(self, nrows=1, ncols=1, figsize=(12, 8)):
        """创建子图"""
        try:
            fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
            if nrows == 1 and ncols == 1:
                axes = np.array([axes])
            return fig, axes
        except Exception as e:
            logger.error(f"创建子图失败: {str(e)}")
            raise
            
    def set_axis_format(self, ax):
        """设置坐标轴格式"""
        try:
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加网格
            ax.grid(True, linestyle='--', alpha=0.5)
            
        except Exception as e:
            logger.error(f"设置坐标轴格式失败: {str(e)}")
            raise
            
    def add_legend(self, ax):
        """添加图例"""
        try:
            ax.legend()
        except Exception as e:
            logger.error(f"添加图例失败: {str(e)}")
            raise
            
    def adjust_layout(self, fig):
        """调整布局"""
        try:
            plt.tight_layout()
        except Exception as e:
            logger.error(f"调整布局失败: {str(e)}")
            raise 