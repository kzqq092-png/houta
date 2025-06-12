import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class RiskAnalysis:
    def __init__(self):
        pass

    def plot_risk_metrics(self, returns, figsize=(12, 8)):
        """
        绘制风险指标分析图

        参数:
            returns: array-like，收益率序列
            figsize: tuple，图形大小
        """
        try:
            # 创建子图
            fig, axes = plt.subplots(2, 2, figsize=figsize)
            axes = axes.flatten()

            # 计算风险指标
            daily_returns = pd.Series(returns)
            cumulative_returns = (1 + daily_returns).cumprod() - 1
            rolling_volatility = daily_returns.rolling(window=20).std() * np.sqrt(252)
            rolling_sharpe = daily_returns.rolling(window=20).mean() / daily_returns.rolling(window=20).std() * np.sqrt(252)
            drawdown = (cumulative_returns - cumulative_returns.cummax()) / cumulative_returns.cummax()

            # 绘制累计收益率
            axes[0].plot(cumulative_returns.index, cumulative_returns.values)
            axes[0].set_title('累计收益率')
            axes[0].grid(True)

            # 绘制波动率
            axes[1].plot(rolling_volatility.index, rolling_volatility.values)
            axes[1].set_title('滚动波动率')
            axes[1].grid(True)

            # 绘制夏普比率
            axes[2].plot(rolling_sharpe.index, rolling_sharpe.values)
            axes[2].set_title('滚动夏普比率')
            axes[2].grid(True)

            # 绘制回撤
            axes[3].fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
            axes[3].set_title('回撤')
            axes[3].grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制风险指标分析图失败: {str(e)}")
            raise

    def plot_value_at_risk(self, returns, confidence_levels=[0.95, 0.99],
                           figsize=(10, 6)):
        """
        绘制VaR分析图

        参数:
            returns: array-like，收益率序列
            confidence_levels: list，置信水平列表
            figsize: tuple，图形大小
        """
        try:
            # 计算VaR
            var_values = {}
            for conf in confidence_levels:
                var = np.percentile(returns, (1 - conf) * 100)
                var_values[conf] = var

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制收益率分布
            sns.histplot(returns, kde=True, color='blue', alpha=0.5)

            # 绘制VaR线
            for conf, var in var_values.items():
                plt.axvline(x=var, color='red', linestyle='--',
                            label=f'{conf*100}% VaR: {var:.2%}')

            plt.title('Value at Risk Analysis')
            plt.xlabel('Returns')
            plt.ylabel('Frequency')
            plt.legend()
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制VaR分析图失败: {str(e)}")
            raise

    def plot_correlation_heatmap(self, returns_df, figsize=(12, 10)):
        """
        绘制相关性热力图

        参数:
            returns_df: DataFrame，收益率数据框
            figsize: tuple，图形大小
        """
        try:
            # 计算相关性矩阵
            corr_matrix = returns_df.corr()

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制热力图
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm',
                        center=0, fmt='.2f', square=True)

            plt.title('Correlation Heatmap')

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制相关性热力图失败: {str(e)}")
            raise

    def plot_risk_contribution(self, weights, cov_matrix, figsize=(10, 6)):
        """
        绘制风险贡献分析图

        参数:
            weights: array-like，投资组合权重
            cov_matrix: array-like，协方差矩阵
            figsize: tuple，图形大小
        """
        try:
            # 计算风险贡献
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            risk_contrib = weights * marginal_contrib

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制风险贡献
            plt.bar(range(len(weights)), risk_contrib, color='blue', alpha=0.5)

            plt.title('Risk Contribution Analysis')
            plt.xlabel('Assets')
            plt.ylabel('Risk Contribution')
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制风险贡献分析图失败: {str(e)}")
            raise

    def plot_rolling_beta(self, returns, market_returns, window=60,
                          figsize=(10, 6)):
        """
        绘制滚动Beta分析图

        参数:
            returns: array-like，资产收益率序列
            market_returns: array-like，市场收益率序列
            window: int，滚动窗口大小
            figsize: tuple，图形大小
        """
        try:
            # 计算滚动Beta
            beta = pd.Series(returns).rolling(window=window).cov(pd.Series(market_returns)) / \
                pd.Series(market_returns).rolling(window=window).var()

            # 创建图形
            plt.figure(figsize=figsize)

            # 绘制Beta
            plt.plot(beta.index, beta.values, color='blue')
            plt.axhline(y=1, color='red', linestyle='--', label='Market Beta = 1')

            plt.title('Rolling Beta Analysis')
            plt.xlabel('Date')
            plt.ylabel('Beta')
            plt.legend()
            plt.grid(True)

            plt.tight_layout()

            return plt.gcf()

        except Exception as e:
            logger.error(f"绘制滚动Beta分析图失败: {str(e)}")
            raise

    def update_risk_table(self, df):
        if not hasattr(self, 'risk_table') or not isinstance(df, pd.DataFrame) or df.empty:
            return
        self.risk_table.setRowCount(len(df) + 3)
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.risk_table.setItem(i, j, item)
        mean_vals = df.mean(numeric_only=True)
        max_vals = df.max(numeric_only=True)
        min_vals = df.min(numeric_only=True)
        col_count = df.shape[1]
        for j in range(col_count):
            item = QTableWidgetItem(f"{mean_vals.iloc[j]:.3f}" if pd.api.types.is_number(mean_vals.iloc[j]) else "")
            item.setBackground(QColor("#fffde7"))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.risk_table.setItem(len(df), j, item)
        for j in range(col_count):
            item = QTableWidgetItem(f"{max_vals.iloc[j]:.3f}" if pd.api.types.is_number(max_vals.iloc[j]) else "")
            item.setBackground(QColor("#ffe082"))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.risk_table.setItem(len(df)+1, j, item)
        for j in range(col_count):
            item = QTableWidgetItem(f"{min_vals.iloc[j]:.3f}" if pd.api.types.is_number(min_vals.iloc[j]) else "")
            item.setBackground(QColor("#ffccbc"))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.risk_table.setItem(len(df)+2, j, item)
        for j in range(col_count):
            max_idx = df.iloc[:, j].idxmax() if pd.api.types.is_numeric_dtype(df.iloc[:, j]) else None
            min_idx = df.iloc[:, j].idxmin() if pd.api.types.is_numeric_dtype(df.iloc[:, j]) else None
            if max_idx is not None:
                self.risk_table.item(max_idx, j).setBackground(QColor("#b2ff59"))
            if min_idx is not None:
                self.risk_table.item(min_idx, j).setBackground(QColor("#ffcdd2"))
