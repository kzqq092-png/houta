import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from hikyuu import *
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    def __init__(self):
        pass
        
    def plot_ma(self, ax, kdata, n_list=[5, 10, 20, 60]):
        """绘制移动平均线"""
        try:
            dates = kdata.get_datetime_list()
            
            # 绘制不同周期的均线
            for n in n_list:
                ma = MA(n=n)(kdata)
                ax.plot(dates, ma, label=f'MA{n}', linewidth=1)
                
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制移动平均线失败: {str(e)}")
            raise
            
    def plot_boll(self, ax, kdata, n=20, p=2):
        """绘制布林带"""
        try:
            dates = kdata.get_datetime_list()
            
            # 计算布林带
            boll = BOLL(n=n, p=p)(kdata)
            
            # 绘制中轨
            ax.plot(dates, boll, label='中轨', color='blue')
            
            # 绘制上轨和下轨
            upper = boll + p * boll.get_std()
            lower = boll - p * boll.get_std()
            ax.plot(dates, upper, label='上轨', color='red', linestyle='--')
            ax.plot(dates, lower, label='下轨', color='green', linestyle='--')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制布林带失败: {str(e)}")
            raise
            
    def plot_kdj(self, ax, kdata, n=9, m1=3, m2=3):
        """绘制KDJ指标"""
        try:
            dates = kdata.get_datetime_list()
            
            # 计算KDJ
            kdj = KDJ(n=n, m1=m1, m2=m2)(kdata)
            
            # 绘制K线
            ax.plot(dates, kdj.get_k(), label='K', color='blue')
            
            # 绘制D线
            ax.plot(dates, kdj.get_d(), label='D', color='red')
            
            # 绘制J线
            ax.plot(dates, kdj.get_j(), label='J', color='green')
            
            # 添加超买超卖线
            ax.axhline(y=80, color='r', linestyle='--', label='超买线')
            ax.axhline(y=20, color='g', linestyle='--', label='超卖线')
            
            # 设置y轴范围
            ax.set_ylim(0, 100)
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制KDJ指标失败: {str(e)}")
            raise
            
    def plot_rsi(self, ax, kdata, n=14):
        """绘制RSI指标"""
        try:
            # 计算RSI
            rsi = RSI(n=n)(kdata)
            dates = kdata.get_datetime_list()
            
            # 绘制RSI线
            ax.plot(dates, rsi, label=f'RSI({n})', color='purple')
            
            # 添加超买超卖线
            ax.axhline(y=70, color='r', linestyle='--', label='超买线')
            ax.axhline(y=30, color='g', linestyle='--', label='超卖线')
            
            # 设置y轴范围
            ax.set_ylim(0, 100)
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制RSI指标失败: {str(e)}")
            raise
            
    def plot_macd(self, ax, kdata, fast_n=12, slow_n=26, signal_n=9):
        """绘制MACD指标"""
        try:
            # 计算MACD
            macd = MACD(fast_n=fast_n, slow_n=slow_n, signal_n=signal_n)(kdata)
            dates = kdata.get_datetime_list()
            
            # 绘制MACD线
            ax.plot(dates, macd, label='MACD', color='blue')
            
            # 绘制信号线
            signal = macd.get_signal()
            ax.plot(dates, signal, label='Signal', color='red')
            
            # 绘制柱状图
            hist = macd - signal
            colors = ['red' if h < 0 else 'green' for h in hist]
            ax.bar(dates, hist, color=colors, alpha=0.5, label='Histogram')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制MACD指标失败: {str(e)}")
            raise
            
    def plot_atr(self, ax, kdata, n=14):
        """绘制ATR指标"""
        try:
            dates = kdata.get_datetime_list()
            
            # 计算ATR
            atr = ATR(n=n)(kdata)
            
            # 绘制ATR线
            ax.plot(dates, atr, label=f'ATR({n})', color='blue')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制ATR指标失败: {str(e)}")
            raise
            
    def plot_obv(self, ax, kdata):
        """绘制OBV指标"""
        try:
            dates = kdata.get_datetime_list()
            
            # 计算OBV
            obv = OBV()(kdata)
            
            # 绘制OBV线
            ax.plot(dates, obv, label='OBV', color='purple')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制OBV指标失败: {str(e)}")
            raise
            
    def plot_cci(self, ax, kdata, n=14):
        """绘制CCI指标"""
        try:
            dates = kdata.get_datetime_list()
            
            # 计算CCI
            cci = CCI(n=n)(kdata)
            
            # 绘制CCI线
            ax.plot(dates, cci, label=f'CCI({n})', color='blue')
            
            # 添加超买超卖线
            ax.axhline(y=100, color='r', linestyle='--', label='超买线')
            ax.axhline(y=-100, color='g', linestyle='--', label='超卖线')
            
            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # 添加图例
            ax.legend()
            
        except Exception as e:
            logger.error(f"绘制CCI指标失败: {str(e)}")
            raise 