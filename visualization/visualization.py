from utils.imports import get_plotly
import sys
import os
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Union
from matplotlib.figure import Figure

# 使用统一的导入管理模块
from utils.imports import (
    pd, np, plt, mdates, sns, go, FigureCanvas,
    sklearn_metrics
)

from hikyuu import *

from .chart_utils import ChartUtils
# 导入新的指标计算服务
from core.services.indicator_service import get_indicator_service
from core.services.indicator_ui_adapter import IndicatorUIAdapter
# from .trade_analysis import TradeAnalysis  # 暂时注释掉，模块不存在
from .risk_analysis import RiskAnalysis
from .model_analysis import ModelAnalysis
from .common_visualization import CommonVisualization

logger = logging.getLogger(__name__)

# 获取sklearn.metrics中的具体函数
confusion_matrix = getattr(sklearn_metrics, 'confusion_matrix', None) if sklearn_metrics else None

# 获取plotly子模块
_plotly_modules = get_plotly()
make_subplots = getattr(_plotly_modules.get('subplots'), 'make_subplots', None) if _plotly_modules.get('subplots') else None


class Visualization:
    def __init__(self):
        self.chart_utils = ChartUtils()
        # 使用新的指标计算服务
        self.indicator_service = get_indicator_service()
        # self.trade_analysis = TradeAnalysis()  # 暂时注释掉，模块不存在
        self.model_analysis = ModelAnalysis()
        self.risk_analysis = RiskAnalysis()

    def plot_technical_indicators(self, kdata, figure, canvas,
                                  fast_ma=None, slow_ma=None):
        """绘制技术指标"""
        try:
            # 创建子图
            fig, axes = self.chart_utils.create_subplots(
                4, 1, figsize=(12, 12))

            # 绘制K线图
            self.chart_utils.plot_kline(axes[0], kdata)
            if fast_ma and slow_ma:
                # 使用新服务计算均线并绘制
                ma_fast_response = self.indicator_service.calculate_indicator('MA', kdata, period=fast_ma.n)
                ma_slow_response = self.indicator_service.calculate_indicator('MA', kdata, period=slow_ma.n)
                if ma_fast_response.success and ma_slow_response.success:
                    ma_fast = ma_fast_response.result
                    ma_slow = ma_slow_response.result
                    axes[0].plot(ma_fast.index, ma_fast.values, label=f'MA{fast_ma.n}')
                    axes[0].plot(ma_slow.index, ma_slow.values, label=f'MA{slow_ma.n}')

            # 绘制成交量
            self.chart_utils.plot_volume(axes[1], kdata)

            # 绘制MACD
            try:
                macd_response = self.indicator_service.calculate_indicator('MACD', kdata)
                if macd_response.success:
                    macd_result = macd_response.result
                    if isinstance(macd_result, dict):
                        axes[2].plot(macd_result['macd'].index, macd_result['macd'].values, label='MACD')
                        axes[2].plot(macd_result['signal'].index, macd_result['signal'].values, label='Signal')
                        axes[2].bar(macd_result['histogram'].index, macd_result['histogram'].values, label='Histogram')
                axes[2].set_title('MACD')
            except Exception as e:
                logger.warning(f"MACD绘制失败: {e}")

            # 绘制RSI
            try:
                rsi_response = self.indicator_service.calculate_indicator('RSI', kdata)
                if rsi_response.success:
                    rsi_result = rsi_response.result
                    axes[3].plot(rsi_result.index, rsi_result.values, label='RSI')
                    axes[3].axhline(y=70, color='r', linestyle='--', alpha=0.5)
                    axes[3].axhline(y=30, color='g', linestyle='--', alpha=0.5)
                axes[3].set_title('RSI')
            except Exception as e:
                logger.warning(f"RSI绘制失败: {e}")

            # 设置坐标轴格式
            for ax in axes:
                self.chart_utils.set_axis_format(ax)
                self.chart_utils.add_legend(ax)

            # 调整布局
            self.chart_utils.adjust_layout(fig)

            # 更新画布
            canvas.draw()

        except Exception as e:
            logger.error(f"绘制技术指标失败: {str(e)}")
            raise

    def plot_sector_analysis(self, stock, figure, canvas):
        """绘制板块分析"""
        try:
            # 获取板块数据
            sector = stock.get_sector()
            if not sector:
                raise ValueError("无法获取板块数据")

            # 获取板块内所有股票
            stocks = sector.get_stocks()
            if len(stocks) == 0:
                raise ValueError("板块内没有股票")

            # 计算板块平均收益率
            returns = []
            for s in stocks:
                try:
                    kdata = s.get_kdata(Query(-30))
                    if len(kdata) > 0:
                        returns.append(
                            (kdata[-1].close - kdata[0].close) / kdata[0].close)
                except:
                    continue

            if not returns:
                raise ValueError("无法计算板块收益率")

            # 创建图表
            fig, ax = self.chart_utils.create_subplots()

            # 绘制收益率直方图
            ax.hist(returns, bins=20, color='blue', alpha=0.5)
            ax.axvline(x=np.mean(returns), color='red', linestyle='--',
                       label=f'平均收益率: {np.mean(returns):.2%}')
            # 顶部显示最大、最小、均值
            ax.text(0.5, 1.05, f"最大: {max(returns):.2%}  最小: {min(returns):.2%}  均值: {np.mean(returns):.2%}",
                    transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='blue')
            # 设置坐标轴格式
            self.chart_utils.set_axis_format(ax)
            self.chart_utils.add_legend(ax)

            # 调整布局
            self.chart_utils.adjust_layout(fig)

            # 更新画布
            canvas.draw()

        except Exception as e:
            logger.error(f"绘制板块分析失败: {str(e)}")
            raise

    def plot_trade_analysis(self, tm, kdata, figure, canvas):
        """绘制交易分析"""
        try:
            # 暂时使用简单的实现，因为trade_analysis模块不存在
            import matplotlib.pyplot as plt

            # 清除现有图形
            figure.clear()

            # 创建子图
            axes = figure.subplots(2, 2, figsize=(12, 10))

            # 简单的占位图表
            axes[0, 0].plot([1, 2, 3, 4, 5], [1, 4, 2, 5, 3])
            axes[0, 0].set_title("交易点位（待实现）")
            axes[0, 0].grid(True)

            axes[0, 1].plot([1, 2, 3, 4, 5], [100, 102, 105, 103, 108])
            axes[0, 1].set_title("收益曲线（待实现）")
            axes[0, 1].grid(True)

            axes[1, 0].plot([1, 2, 3, 4, 5], [0, -1, -0.5, -2, -1])
            axes[1, 0].set_title("回撤分析（待实现）")
            axes[1, 0].grid(True)

            axes[1, 1].bar([1, 2, 3, 4, 5], [10, 20, 15, 25, 18])
            axes[1, 1].set_title("持仓分析（待实现）")
            axes[1, 1].grid(True)

            # 调整布局
            figure.tight_layout()

            # 更新画布
            canvas.draw()

        except Exception as e:
            print(f"绘制交易分析失败: {str(e)}")
            # 创建一个简单的错误提示图
            figure.clear()
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, f"交易分析功能暂不可用\n错误: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title("交易分析")
            canvas.draw()


def plot_feature_importance_comparison(feature_importances_list, model_names, feature_names, top_n=15, figsize=(12, 10)):
    """
    比较多个模型的特征重要性

    参数:
        feature_importances_list: list，多个模型的特征重要性数组列表
        model_names: list，模型名称列表
        feature_names: list，特征名称列表
        top_n: int，显示前N个重要特征
        figsize: tuple，图形大小
    """
    if len(feature_importances_list) != len(model_names):
        raise ValueError("特征重要性列表和模型名称列表长度不匹配")

    # 创建特征重要性DataFrame
    dfs = []
    for i, importances in enumerate(feature_importances_list):
        if len(importances) != len(feature_names):
            raise ValueError(f"模型 {model_names[i]} 的特征重要性长度与特征名称不匹配")

        df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances,
            'Model': model_names[i]
        })
        dfs.append(df)

    combined_df = pd.concat(dfs)

    # 获取每个模型的前N个重要特征
    top_features = set()
    for model in model_names:
        model_df = combined_df[combined_df['Model'] == model]
        top_model_features = model_df.nlargest(
            top_n, 'Importance')['Feature'].values
        top_features.update(top_model_features)

    # 过滤数据只包含前N个特征
    filtered_df = combined_df[combined_df['Feature'].isin(top_features)]

    # 创建图形
    plt.figure(figsize=figsize)

    # 使用seaborn绘制条形图
    ax = sns.barplot(x='Importance', y='Feature',
                     hue='Model', data=filtered_df)

    # 设置标题和标签
    plt.title('Feature Importance Comparison Across Models', fontsize=15)
    plt.xlabel('Importance')
    plt.ylabel('Feature')

    # 调整图例位置
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()

    return plt.gcf()


def plot_signal_over_time(df, signal_col='signal', figsize=(15, 8)):
    """
    绘制信号随时间变化的热力图

    参数:
        df: DataFrame，包含信号数据
        signal_col: str，信号列名
        figsize: tuple，图形大小
    """
    if signal_col not in df.columns:
        raise ValueError(f"DataFrame中缺少信号列: {signal_col}")

    # 确保索引是日期类型
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame的索引必须是日期类型")

    # 创建包含年月信息的DataFrame
    signal_df = pd.DataFrame({
        'year': df.index.year,
        'month': df.index.month,
        'signal': df[signal_col]
    })

    # 按年月分组统计信号数量
    pivot_buy = signal_df[signal_df['signal'] == 1].groupby(
        ['year', 'month']).size().unstack(fill_value=0)
    pivot_sell = signal_df[signal_df['signal'] == -
                           1].groupby(['year', 'month']).size().unstack(fill_value=0)

    # 计算信号比例（买-卖）/总量
    pivot_ratio = (pivot_buy - pivot_sell) / \
        (pivot_buy + pivot_sell + 1e-10)  # 添加小数避免除零

    # 创建图形
    fig, ax = plt.subplots(figsize=figsize)

    # 绘制热力图
    cmap = plt.cm.RdYlGn  # 红色表示多卖出，绿色表示多买入
    im = ax.imshow(pivot_ratio, cmap=cmap, aspect='auto', vmin=-1, vmax=1)

    # 设置坐标轴标签
    ax.set_xticks(np.arange(len(pivot_ratio.columns)))
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    ax.set_yticks(np.arange(len(pivot_ratio.index)))
    ax.set_yticklabels(pivot_ratio.index)

    # 添加标题
    plt.title('Signal Distribution Over Time', fontsize=15)

    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Signal Ratio (Buy - Sell) / Total')

    # 在每个单元格添加文本
    for i in range(len(pivot_ratio.index)):
        for j in range(len(pivot_ratio.columns)):
            buy_count = pivot_buy.iloc[i, j]
            sell_count = pivot_sell.iloc[i, j]
            text = f"{buy_count}-{sell_count}"
            ax.text(j, i, text, ha="center", va="center", color="black")

    plt.tight_layout()

    return plt.gcf()


class ChartVisualizer:
    """图表可视化器"""

    def __init__(self, theme: str = 'default'):
        """初始化图表可视化器

        Args:
            theme: 主题名称
        """
        self.theme = theme
        # 使用新的指标UI适配器
        self.indicator_adapter = IndicatorUIAdapter()

        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

        # 设置主题样式
        self._setup_theme()

    def _setup_theme(self):
        """设置主题样式"""
        if self.theme == 'dark':
            plt.style.use('dark_background')
            self.colors = {
                'up': '#00ff88',
                'down': '#ff4444',
                'background': '#1e1e1e',
                'text': '#ffffff',
                'grid': '#444444'
            }
        else:
            plt.style.use('default')
            self.colors = {
                'up': '#ff4444',
                'down': '#00aa00',
                'background': '#ffffff',
                'text': '#000000',
                'grid': '#cccccc'
            }

    def plot_candlestick(self, data: pd.DataFrame, title: str = "K线图",
                         indicators: Optional[List[str]] = None,
                         figsize: Tuple[int, int] = (12, 8)) -> Figure:
        """绘制K线图

        Args:
            data: K线数据，包含open, high, low, close, volume列
            title: 图表标题
            indicators: 要显示的指标列表
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            fig, axes = plt.subplots(2, 1, figsize=figsize, height_ratios=[3, 1])

            # 主图：K线图
            self._plot_kline(axes[0], data, title)

            # 添加指标
            if indicators:
                self._add_indicators(axes[0], data, indicators)

            # 副图：成交量
            self._plot_volume(axes[1], data)

            # 设置整体样式
            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制K线图失败: {str(e)}")
            # 返回空图表
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig

    def _plot_kline(self, ax, data: pd.DataFrame, title: str):
        """绘制K线"""
        try:
            # 确保数据有日期索引
            if not isinstance(data.index, pd.DatetimeIndex):
                if 'date' in data.columns:
                    data = data.set_index('date')
                else:
                    data.index = pd.to_datetime(data.index)

            # 绘制K线
            for i, (idx, row) in enumerate(data.iterrows()):
                color = self.colors['up'] if row['close'] >= row['open'] else self.colors['down']

                # 绘制影线
                ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)

                # 绘制实体
                height = abs(row['close'] - row['open'])
                bottom = min(row['open'], row['close'])
                ax.bar(i, height, bottom=bottom, color=color, width=0.8, alpha=0.8)

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_ylabel('价格', fontsize=12)
            ax.grid(True, alpha=0.3)

            # 设置x轴标签
            step = max(1, len(data) // 10)
            ticks = range(0, len(data), step)
            labels = [data.index[i].strftime('%Y-%m-%d') if i < len(data) else '' for i in ticks]
            ax.set_xticks(ticks)
            ax.set_xticklabels(labels, rotation=45)

        except Exception as e:
            print(f"绘制K线失败: {str(e)}")
            ax.text(0.5, 0.5, f"绘制K线失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)

    def _plot_volume(self, ax, data: pd.DataFrame):
        """绘制成交量"""
        try:
            if 'volume' not in data.columns:
                ax.text(0.5, 0.5, '无成交量数据', ha='center', va='center', transform=ax.transAxes)
                return

            colors = [self.colors['up'] if data.iloc[i]['close'] >= data.iloc[i]['open']
                      else self.colors['down'] for i in range(len(data))]

            ax.bar(range(len(data)), data['volume'], color=colors, alpha=0.7)
            ax.set_ylabel('成交量', fontsize=12)
            ax.grid(True, alpha=0.3)

            # 设置x轴标签
            step = max(1, len(data) // 10)
            ticks = range(0, len(data), step)
            labels = [data.index[i].strftime('%Y-%m-%d') if i < len(data) else '' for i in ticks]
            ax.set_xticks(ticks)
            ax.set_xticklabels(labels, rotation=45)

        except Exception as e:
            print(f"绘制成交量失败: {str(e)}")
            ax.text(0.5, 0.5, f"绘制成交量失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)

    def _add_indicators(self, ax, data: pd.DataFrame, indicators: List[str]):
        """添加技术指标"""
        try:
            for indicator in indicators:
                self._plot_single_indicator(ax, data, indicator)
        except Exception as e:
            print(f"添加指标失败: {str(e)}")

    def _plot_single_indicator(self, ax, data: pd.DataFrame, indicator: str):
        """绘制单个指标"""
        try:
            indicator_lower = indicator.lower()

            if indicator_lower == 'ma5':
                ma_result = self.indicator_adapter.calculate_indicator('MA', data, period=5)
                if ma_result and ma_result.get('success'):
                    values = ma_result.get('data')
                    if values is not None:
                        ax.plot(range(len(data)), values, label='MA5', linewidth=1)

            elif indicator_lower == 'ma10':
                ma_result = self.indicator_adapter.calculate_indicator('MA', data, period=10)
                if ma_result and ma_result.get('success'):
                    values = ma_result.get('data')
                    if values is not None:
                        ax.plot(range(len(data)), values, label='MA10', linewidth=1)

            elif indicator_lower == 'ma20':
                ma_result = self.indicator_adapter.calculate_indicator('MA', data, period=20)
                if ma_result and ma_result.get('success'):
                    values = ma_result.get('data')
                    if values is not None:
                        ax.plot(range(len(data)), values, label='MA20', linewidth=1)

            elif indicator_lower == 'ma60':
                ma_result = self.indicator_adapter.calculate_indicator('MA', data, period=60)
                if ma_result and ma_result.get('success'):
                    values = ma_result.get('data')
                    if values is not None:
                        ax.plot(range(len(data)), values, label='MA60', linewidth=1)

            elif indicator_lower == 'boll':
                boll_result = self.indicator_adapter.calculate_indicator('BOLL', data, period=20, std_dev=2)
                if boll_result and boll_result.get('success'):
                    boll_data = boll_result.get('data')
                    if boll_data and isinstance(boll_data, dict):
                        if 'upper' in boll_data:
                            ax.plot(range(len(data)), boll_data['upper'], label='BOLL上轨', linewidth=1, alpha=0.7)
                        if 'middle' in boll_data:
                            ax.plot(range(len(data)), boll_data['middle'], label='BOLL中轨', linewidth=1, alpha=0.7)
                        if 'lower' in boll_data:
                            ax.plot(range(len(data)), boll_data['lower'], label='BOLL下轨', linewidth=1, alpha=0.7)

            # 如果统一指标管理器失败，尝试使用兼容层
            else:
                self._plot_indicator_fallback(ax, data, indicator)

        except Exception as e:
            print(f"绘制指标 {indicator} 失败: {str(e)}")
            # 尝试使用兼容层
            self._plot_indicator_fallback(ax, data, indicator)

    def _plot_indicator_fallback(self, ax, data: pd.DataFrame, indicator: str):
        """使用兼容层绘制指标"""
        try:
            indicator_lower = indicator.lower()

            if indicator_lower in ['ma5', 'ma10', 'ma20', 'ma60']:
                period = int(indicator_lower[2:])
                ma_result = self.compat_manager.calc_ma(data, period=period)
                if ma_result is not None:
                    ax.plot(range(len(data)), ma_result, label=f'MA{period}', linewidth=1)

            elif indicator_lower == 'boll':
                boll_result = self.compat_manager.calc_boll(data, period=20, std_dev=2)
                if boll_result is not None:
                    if isinstance(boll_result, tuple) and len(boll_result) >= 3:
                        _, upper, lower = boll_result[:3]
                        ax.plot(range(len(data)), upper, label='BOLL上轨', linewidth=1, alpha=0.7)
                        ax.plot(range(len(data)), lower, label='BOLL下轨', linewidth=1, alpha=0.7)
                    elif isinstance(boll_result, dict):
                        if 'upper' in boll_result:
                            ax.plot(range(len(data)), boll_result['upper'], label='BOLL上轨', linewidth=1, alpha=0.7)
                        if 'lower' in boll_result:
                            ax.plot(range(len(data)), boll_result['lower'], label='BOLL下轨', linewidth=1, alpha=0.7)

        except Exception as e:
            print(f"兼容层绘制指标 {indicator} 失败: {str(e)}")

    def plot_indicator_comparison(self, data: pd.DataFrame, indicators: List[str],
                                  title: str = "指标对比", figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """绘制指标对比图

        Args:
            data: 数据
            indicators: 指标列表
            title: 图表标题
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)

            for indicator in indicators:
                self._plot_single_indicator(ax, data, indicator)

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_ylabel('数值', fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制指标对比图失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig

    def plot_correlation_heatmap(self, data: pd.DataFrame,
                                 title: str = "相关性热力图",
                                 figsize: Tuple[int, int] = (10, 8)) -> Figure:
        """绘制相关性热力图

        Args:
            data: 数据
            title: 图表标题
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            # 计算相关性矩阵
            corr_matrix = data.corr()

            fig, ax = plt.subplots(figsize=figsize)

            # 绘制热力图
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                        square=True, ax=ax, cbar_kws={'shrink': 0.8})

            ax.set_title(title, fontsize=14, fontweight='bold')
            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制相关性热力图失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig

    def plot_distribution(self, data: pd.Series, title: str = "数据分布",
                          figsize: Tuple[int, int] = (10, 6)) -> Figure:
        """绘制数据分布图

        Args:
            data: 数据序列
            title: 图表标题
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

            # 直方图
            ax1.hist(data.dropna(), bins=50, alpha=0.7, edgecolor='black')
            ax1.set_title(f'{title} - 直方图', fontsize=12)
            ax1.set_xlabel('数值')
            ax1.set_ylabel('频次')
            ax1.grid(True, alpha=0.3)

            # 箱线图
            ax2.boxplot(data.dropna())
            ax2.set_title(f'{title} - 箱线图', fontsize=12)
            ax2.set_ylabel('数值')
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制数据分布图失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig


class IndicatorVisualizer:
    """指标可视化器"""

    def __init__(self):
        """初始化指标可视化器"""
        # 使用新的指标计算服务
        self.indicator_service = get_indicator_service()

    def plot_macd(self, data: pd.DataFrame, figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """绘制MACD指标

        Args:
            data: K线数据
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            # 使用新架构计算MACD
            macd_response = self.indicator_adapter.calculate_indicator(
                'MACD', data, fast_period=12, slow_period=26, signal_period=9
            )
            macd_result = macd_response.get('data') if macd_response and macd_response.get('success') else None

            if macd_result is None:
                # 使用兼容层作为备用
                macd_result = self.compat_manager.calc_macd(data)

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])

            # 绘制价格
            ax1.plot(data['close'], label='收盘价', linewidth=1)
            ax1.set_title('MACD指标', fontsize=14, fontweight='bold')
            ax1.set_ylabel('价格')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 绘制MACD
            if macd_result is not None:
                if isinstance(macd_result, dict):
                    if 'main' in macd_result:
                        ax2.plot(macd_result['main'], label='MACD', linewidth=1)
                    if 'signal' in macd_result:
                        ax2.plot(macd_result['signal'], label='Signal', linewidth=1)
                    if 'histogram' in macd_result:
                        ax2.bar(range(len(macd_result['histogram'])), macd_result['histogram'],
                                label='Histogram', alpha=0.7)
                elif isinstance(macd_result, tuple) and len(macd_result) >= 3:
                    macd_line, signal_line, histogram = macd_result[:3]
                    ax2.plot(macd_line, label='MACD', linewidth=1)
                    ax2.plot(signal_line, label='Signal', linewidth=1)
                    ax2.bar(range(len(histogram)), histogram, label='Histogram', alpha=0.7)

            ax2.set_ylabel('MACD')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制MACD指标失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制MACD失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig

    def plot_rsi(self, data: pd.DataFrame, period: int = 14,
                 figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """绘制RSI指标

        Args:
            data: K线数据
            period: RSI周期
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            # 使用新架构计算RSI
            rsi_response = self.indicator_adapter.calculate_indicator('RSI', data, period=period)
            rsi_result = rsi_response.get('data') if rsi_response and rsi_response.get('success') else None

            if rsi_result is None:
                # 使用兼容层作为备用
                rsi_result = self.compat_manager.calc_rsi(data, period=period)

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, height_ratios=[2, 1])

            # 绘制价格
            ax1.plot(data['close'], label='收盘价', linewidth=1)
            ax1.set_title('RSI指标', fontsize=14, fontweight='bold')
            ax1.set_ylabel('价格')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 绘制RSI
            if rsi_result is not None:
                ax2.plot(rsi_result, label=f'RSI({period})', linewidth=1)
                ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超买线(70)')
                ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超卖线(30)')
                ax2.set_ylim(0, 100)

            ax2.set_ylabel('RSI')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制RSI指标失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制RSI失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig

    def plot_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: float = 2,
                             figsize: Tuple[int, int] = (12, 6)) -> Figure:
        """绘制布林带指标

        Args:
            data: K线数据
            period: 均线周期
            std_dev: 标准差倍数
            figsize: 图表大小

        Returns:
            matplotlib Figure对象
        """
        try:
            # 使用新架构计算布林带
            boll_response = self.indicator_adapter.calculate_indicator(
                'BOLL', data, period=period, std_dev=std_dev
            )
            boll_result = boll_response.get('data') if boll_response and boll_response.get('success') else None

            if boll_result is None:
                # 使用兼容层作为备用
                boll_result = self.compat_manager.calc_boll(data, period=period, std_dev=std_dev)

            fig, ax = plt.subplots(figsize=figsize)

            # 绘制价格
            ax.plot(data['close'], label='收盘价', linewidth=1, color='black')

            # 绘制布林带
            if boll_result is not None:
                if isinstance(boll_result, dict):
                    if 'upper' in boll_result:
                        ax.plot(boll_result['upper'], label='上轨', linewidth=1, alpha=0.7)
                    if 'middle' in boll_result:
                        ax.plot(boll_result['middle'], label='中轨', linewidth=1, alpha=0.7)
                    if 'lower' in boll_result:
                        ax.plot(boll_result['lower'], label='下轨', linewidth=1, alpha=0.7)

                    # 填充上下轨之间的区域
                    if 'upper' in boll_result and 'lower' in boll_result:
                        ax.fill_between(range(len(boll_result['upper'])),
                                        boll_result['upper'], boll_result['lower'],
                                        alpha=0.1, label='布林带区域')

                elif isinstance(boll_result, tuple) and len(boll_result) >= 3:
                    middle, upper, lower = boll_result[:3]
                    ax.plot(upper, label='上轨', linewidth=1, alpha=0.7)
                    ax.plot(middle, label='中轨', linewidth=1, alpha=0.7)
                    ax.plot(lower, label='下轨', linewidth=1, alpha=0.7)
                    ax.fill_between(range(len(upper)), upper, lower, alpha=0.1, label='布林带区域')

            ax.set_title('布林带指标', fontsize=14, fontweight='bold')
            ax.set_ylabel('价格')
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except Exception as e:
            print(f"绘制布林带指标失败: {str(e)}")
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"绘制布林带失败: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            return fig


# 便捷函数
def create_chart_visualizer(theme: str = 'default') -> ChartVisualizer:
    """创建图表可视化器

    Args:
        theme: 主题名称

    Returns:
        ChartVisualizer实例
    """
    return ChartVisualizer(theme)


def create_indicator_visualizer() -> IndicatorVisualizer:
    """创建指标可视化器

    Returns:
        IndicatorVisualizer实例
    """
    return IndicatorVisualizer()


# 向后兼容的别名
def get_chart_visualizer(theme: str = 'default') -> ChartVisualizer:
    """获取图表可视化器（向后兼容）"""
    return create_chart_visualizer(theme)


def get_indicator_visualizer() -> IndicatorVisualizer:
    """获取指标可视化器（向后兼容）"""
    return create_indicator_visualizer()
