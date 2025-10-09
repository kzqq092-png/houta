from hikyuu import *
from hikyuu.trade_sys import ProfitGoalBase
import numpy as np
import pandas as pd
from loguru import logger

class AdaptiveTakeProfit(ProfitGoalBase):
    """
    自适应止盈策略
    继承Hikyuu的ProfitGoalBase类创建自定义止盈策略
    """

    def __init__(self, params=None):
        super(AdaptiveTakeProfit, self).__init__("AdaptiveTakeProfit")

        # 设置默认参数
        self.set_param("atr_period", 14)         # ATR周期
        self.set_param("atr_multiplier", 2)      # ATR倍数
        self.set_param("ma_period", 20)          # 均线周期
        self.set_param("volatility_period", 20)  # 波动率计算周期
        self.set_param("min_take_profit", 0.02)  # 最小止盈比例
        self.set_param("max_take_profit", 0.2)   # 最大止盈比例
        self.set_param("trailing_profit", 0.03)  # 跟踪止盈比例
        self.set_param("profit_lock", 0.05)      # 盈利锁定比例
        self.set_param("volatility_factor", 0.5)  # 波动率因子
        self.set_param("trend_factor", 0.3)      # 趋势因子
        self.set_param("market_factor", 0.2)     # 市场因子

        # 初始化持仓信息
        self.positions = {}  # 记录每个持仓的止盈信息

    def _reset(self):
        """重置状态"""
        self.positions = {}

    def _clone(self):
        return AdaptiveTakeProfit()

    def _calculate(self, datetime, stock, price, risk, part_from):
        """计算止盈价格"""
        try:
            # 1. 获取持仓信息
            position = self._get_position_info(stock)
            if not position:
                return 0.0

            # 2. 获取市场数据
            k = stock.get_kdata(Query(datetime - 30, datetime))
            if len(k) <= 0:
                return 0.0

            df = k.to_df()

            # 3. 计算技术指标
            atr = self._calculate_atr(df)
            ma = self._calculate_ma(df)
            volatility = self._calculate_volatility(df)
            trend = self._calculate_trend(df)

            # 4. 计算不同类型的止盈价格
            profits = {
                'atr': self._calculate_atr_profit(price, atr, trend),
                'ma': self._calculate_ma_profit(price, ma),
                'trailing': self._calculate_trailing_profit(price, position),
                'volatility': self._calculate_volatility_profit(price, volatility),
                'fixed': self._calculate_fixed_profit(price)
            }

            # 5. 选择最终的止盈价格
            profit_price = self._select_profit_price(
                price, profits, position, trend)

            # 6. 更新持仓信息
            self._update_position_info(stock, price, profit_price, datetime)

            return profit_price

        except Exception as e:
            logger.info(f"止盈价格计算错误: {str(e)}")
            return 0.0

    def _calculate_atr(self, df):
        """计算ATR"""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values

            tr = np.maximum(
                high[1:] - low[1:],
                np.maximum(
                    np.abs(high[1:] - close[:-1]),
                    np.abs(low[1:] - close[:-1])
                )
            )

            return np.mean(tr[-self.get_param("atr_period"):])

        except Exception as e:
            logger.info(f"ATR计算错误: {str(e)}")
            return 0.0

    def _calculate_ma(self, df):
        """计算移动平均"""
        try:
            return df['close'].rolling(window=self.get_param("ma_period")).mean().iloc[-1]
        except Exception as e:
            logger.info(f"MA计算错误: {str(e)}")
            return 0.0

    def _calculate_volatility(self, df):
        """计算波动率"""
        try:
            returns = df['close'].pct_change()
            return returns.rolling(window=self.get_param("volatility_period")).std().iloc[-1]
        except Exception as e:
            logger.info(f"波动率计算错误: {str(e)}")
            return 0.0

    def _calculate_trend(self, df):
        """计算趋势"""
        try:
            ma = df['close'].rolling(window=self.get_param("ma_period")).mean()
            return 1 if df['close'].iloc[-1] > ma.iloc[-1] else -1
        except Exception as e:
            logger.info(f"趋势计算错误: {str(e)}")
            return 0

    def _get_position_info(self, stock):
        """获取持仓信息"""
        try:
            position = self.tm.get_position(stock)
            if not position:
                return None

            if stock.market_code not in self.positions:
                self.positions[stock.market_code] = {
                    'entry_price': position.buy_price,
                    'highest_price': position.buy_price,
                    'lowest_price': position.buy_price,
                    'last_profit_price': 0.0,
                    'last_update': position.buy_datetime
                }

            return self.positions[stock.market_code]

        except Exception as e:
            logger.info(f"获取持仓信息错误: {str(e)}")
            return None

    def _calculate_atr_profit(self, price, atr, trend):
        """计算ATR止盈价格"""
        try:
            profit_distance = atr * self.get_param("atr_multiplier")
            if trend > 0:
                return price + profit_distance
            else:
                return price - profit_distance
        except Exception as e:
            logger.info(f"ATR止盈计算错误: {str(e)}")
            return 0.0

    def _calculate_ma_profit(self, price, ma):
        """计算均线止盈价格"""
        try:
            return ma
        except Exception as e:
            logger.info(f"均线止盈计算错误: {str(e)}")
            return 0.0

    def _calculate_trailing_profit(self, price, position):
        """计算跟踪止盈价格"""
        try:
            if price > position['highest_price']:
                position['highest_price'] = price

            profit_distance = position['highest_price'] * \
                self.get_param("trailing_profit")
            return position['highest_price'] + profit_distance

        except Exception as e:
            logger.info(f"跟踪止盈计算错误: {str(e)}")
            return 0.0

    def _calculate_volatility_profit(self, price, volatility):
        """计算波动率止盈价格"""
        try:
            profit_distance = price * volatility * \
                self.get_param("volatility_factor")
            return price + profit_distance
        except Exception as e:
            logger.info(f"波动率止盈计算错误: {str(e)}")
            return 0.0

    def _calculate_fixed_profit(self, price):
        """计算固定止盈价格"""
        try:
            return price * (1 + self.get_param("min_take_profit"))
        except Exception as e:
            logger.info(f"固定止盈计算错误: {str(e)}")
            return 0.0

    def _select_profit_price(self, price, profits, position, trend):
        """选择最终的止盈价格"""
        try:
            # 1. 根据趋势选择止盈策略
            if trend > 0:
                # 上升趋势，使用较宽松的止盈
                profit_price = max(
                    profits['atr'],
                    profits['ma'],
                    profits['trailing']
                )
            else:
                # 下降趋势，使用较严格的止盈
                profit_price = min(
                    profits['atr'],
                    profits['ma'],
                    profits['volatility']
                )

            # 2. 确保止盈价格在合理范围内
            min_profit = price * (1 + self.get_param("min_take_profit"))
            max_profit = price * (1 + self.get_param("max_take_profit"))
            profit_price = min(max_profit, max(profit_price, min_profit))

            # 3. 如果已经盈利，使用更宽松的止盈
            if price > position['entry_price']:
                profit_ratio = (
                    price - position['entry_price']) / position['entry_price']
                if profit_ratio > self.get_param("profit_lock"):
                    # 锁定部分利润
                    lock_price = position['entry_price'] * \
                        (1 + self.get_param("profit_lock"))
                    profit_price = max(profit_price, lock_price)

            return profit_price

        except Exception as e:
            logger.info(f"选择止盈价格错误: {str(e)}")
            return 0.0

    def _update_position_info(self, stock, price, profit_price, datetime):
        """更新持仓信息"""
        try:
            if stock.market_code in self.positions:
                position = self.positions[stock.market_code]
                position['last_profit_price'] = profit_price
                position['last_update'] = datetime

                if price > position['highest_price']:
                    position['highest_price'] = price
                if price < position['lowest_price']:
                    position['lowest_price'] = price

        except Exception as e:
            logger.info(f"更新持仓信息错误: {str(e)}")
