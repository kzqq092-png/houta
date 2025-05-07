import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from hikyuu import *
import logging

logger = logging.getLogger(__name__)


class ChartUtils:
    def __init__(self):
        pass

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
            colors = ['red' if c >= o else 'green' for o,
                      c in zip(opens, closes)]

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
            colors = ['red' if c >= o else 'green' for o,
                      c in zip(opens, closes)]

            # 绘制成交量柱状图
            ax.bar(dates, volumes, color=colors, alpha=0.5)

            # 设置x轴格式
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)

        except Exception as e:
            logger.error(f"绘制成交量图失败: {str(e)}")
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

    def plot_trading_signals(self, ax, kdata, signals):
        """绘制交易信号"""
        try:
            dates = kdata.get_datetime_list()
            closes = kdata.get_close()

            # 绘制买入信号
            buy_signals = [i for i, s in enumerate(signals) if s == 1]
            if buy_signals:
                ax.scatter([dates[i] for i in buy_signals],
                           [closes[i] for i in buy_signals],
                           color='red', marker='^', label='买入信号')

            # 绘制卖出信号
            sell_signals = [i for i, s in enumerate(signals) if s == -1]
            if sell_signals:
                ax.scatter([dates[i] for i in sell_signals],
                           [closes[i] for i in sell_signals],
                           color='green', marker='v', label='卖出信号')

            # 添加图例
            ax.legend()

        except Exception as e:
            logger.error(f"绘制交易信号失败: {str(e)}")
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
            buy_dates = [
                t.datetime for t in trades if t.business == BUSINESS.BUY]
            buy_prices = [
                t.price for t in trades if t.business == BUSINESS.BUY]
            if buy_dates:
                ax.scatter(buy_dates, buy_prices, color='red', marker='^',
                           label='买入点', s=100)

            # 绘制卖出点
            sell_dates = [
                t.datetime for t in trades if t.business == BUSINESS.SELL]
            sell_prices = [
                t.price for t in trades if t.business == BUSINESS.SELL]
            if sell_dates:
                ax.scatter(sell_dates, sell_prices, color='green', marker='v',
                           label='卖出点', s=100)

            # 添加图例
            ax.legend()

        except Exception as e:
            logger.error(f"绘制交易点失败: {str(e)}")
            raise


class DataUtils:
    def __init__(self):
        pass

    def get_stock_data(self, stock, query):
        """获取股票数据"""
        try:
            # 统一通过 data_manager 获取
            kdata = data_manager.get_k_data(stock.code, query)
            if kdata is None or len(kdata) == 0:
                raise ValueError("无法获取股票数据")
            return kdata
        except Exception as e:
            logger.error(f"获取股票数据失败: {str(e)}")
            raise

    def get_sector_data(self, sector):
        """获取板块数据"""
        try:
            stocks = sector.get_stocks()
            if len(stocks) == 0:
                raise ValueError("无法获取板块数据")
            return stocks
        except Exception as e:
            logger.error(f"获取板块数据失败: {str(e)}")
            raise
