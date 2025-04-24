import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from hikyuu import *
import logging

logger = logging.getLogger(__name__)

class TradeAnalysis:
    def __init__(self):
        pass
        
    def plot_profit_curve(self, ax, tm, dates):
        """绘制收益曲线"""
        try:
            # 获取收益曲线数据
            profit_curve = tm.get_profit_curve(dates)
            
            # 绘制收益曲线
            ax.plot(dates, profit_curve, label='收益曲线', color='blue')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制收益曲线失败: {str(e)}")
            raise
            
    def plot_drawdown(self, ax, tm, dates):
        """绘制回撤曲线"""
        try:
            # 获取回撤数据
            drawdown = tm.get_drawdown(dates)
            
            # 绘制回撤曲线
            ax.plot(dates, drawdown, label='回撤曲线', color='red')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制回撤曲线失败: {str(e)}")
            raise
            
    def plot_position(self, ax, tm, dates):
        """绘制持仓曲线"""
        try:
            # 获取持仓数据
            position = tm.get_position(dates)
            
            # 绘制持仓曲线
            ax.plot(dates, position, label='持仓曲线', color='green')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制持仓曲线失败: {str(e)}")
            raise
            
    def plot_trade_points(self, ax, tm, kdata):
        """绘制交易点"""
        try:
            dates = kdata.get_datetime_list()
            closes = kdata.get_close()
            
            # 获取交易记录
            trades = tm.get_trade_list()
            
            # 绘制买入点
            buy_dates = [t.datetime for t in trades if t.business == BUSINESS.BUY]
            buy_prices = [t.price for t in trades if t.business == BUSINESS.BUY]
            if buy_dates:
                ax.scatter(buy_dates, buy_prices, color='red', marker='^', 
                          label='买入点', s=100)
            
            # 绘制卖出点
            sell_dates = [t.datetime for t in trades if t.business == BUSINESS.SELL]
            sell_prices = [t.price for t in trades if t.business == BUSINESS.SELL]
            if sell_dates:
                ax.scatter(sell_dates, sell_prices, color='green', marker='v', 
                          label='卖出点', s=100)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制交易点失败: {str(e)}")
            raise
            
    def plot_trade_analysis(self, ax, tm, kdata):
        """绘制交易分析图表"""
        try:
            # 创建子图
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
            
            # 绘制收益曲线
            self.plot_profit_curve(ax1, tm, kdata.get_datetime_list())
            
            # 绘制回撤曲线
            self.plot_drawdown(ax2, tm, kdata.get_datetime_list())
            
            # 绘制持仓曲线
            self.plot_position(ax3, tm, kdata.get_datetime_list())
            
            # 调整布局
            plt.tight_layout()
            
        except Exception as e:
            logger.error(f"绘制交易分析图表失败: {str(e)}")
            raise 