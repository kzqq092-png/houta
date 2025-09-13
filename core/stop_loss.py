from hikyuu import *
from hikyuu.trade_sys import StoplossBase
import numpy as np
import pandas as pd
from loguru import logger


class AdaptiveStopLoss(StoplossBase):
    """
    自适应止损策略
    继承Hikyuu的StoplossBase类创建自定义止损策略
    """

    def __init__(self, params=None):
        super(AdaptiveStopLoss, self).__init__("AdaptiveStopLoss")

        # 设置默认参数
        self.set_param("atr_period", 14)         # ATR周期
        self.set_param("atr_multiplier", 2)      # ATR倍数
        self.set_param("ma_period", 20)          # 均线周期
        self.set_param("volatility_period", 20)  # 波动率计算周期
        self.set_param("min_stop_loss", 0.02)    # 最小止损比例
        self.set_param("max_stop_loss", 0.1)     # 最大止损比例
        self.set_param("trailing_stop", 0.03)    # 跟踪止损比例
        self.set_param("profit_lock", 0.05)      # 盈利锁定比例
        self.set_param("volatility_factor", 0.5)  # 波动率因子
        self.set_param("trend_factor", 0.3)      # 趋势因子
        self.set_param("market_factor", 0.2)     # 市场因子

        # 初始化持仓信息
        self.positions = {}  # 记录每个持仓的止损信息

    def _reset(self):
        """重置状态"""
        self.positions = {}

    def _clone(self):
        return AdaptiveStopLoss()

    def _calculate(self, datetime, stock, price, risk, part_from):
        """计算止损价格"""
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

            # 4. 计算不同类型的止损价格
            stops = {
                'atr': self._calculate_atr_stop(price, atr, trend),
                'ma': self._calculate_ma_stop(price, ma),
                'trailing': self._calculate_trailing_stop(price, position),
                'volatility': self._calculate_volatility_stop(price, volatility),
                'fixed': self._calculate_fixed_stop(price)
            }

            # 5. 选择最终的止损价格
            stop_price = self._select_stop_price(price, stops, position, trend)

            # 6. 更新持仓信息
            self._update_position_info(stock, price, stop_price, datetime)

            return stop_price

        except Exception as e:
            logger.info(f"止损价格计算错误: {str(e)}")
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
                    'last_stop_price': 0.0,
                    'last_update': position.buy_datetime
                }

            return self.positions[stock.market_code]

        except Exception as e:
            logger.info(f"获取持仓信息错误: {str(e)}")
            return None

    def _calculate_atr_stop(self, price, atr, trend):
        """计算ATR止损价格"""
        try:
            stop_distance = atr * self.get_param("atr_multiplier")
            if trend > 0:
                return price - stop_distance
            else:
                return price + stop_distance
        except Exception as e:
            logger.info(f"ATR止损计算错误: {str(e)}")
            return 0.0

    def _calculate_ma_stop(self, price, ma):
        """计算均线止损价格"""
        try:
            return ma
        except Exception as e:
            logger.info(f"均线止损计算错误: {str(e)}")
            return 0.0

    def _calculate_trailing_stop(self, price, position):
        """计算跟踪止损价格"""
        try:
            if price > position['highest_price']:
                position['highest_price'] = price

            stop_distance = position['highest_price'] * \
                self.get_param("trailing_stop")
            return position['highest_price'] - stop_distance

        except Exception as e:
            logger.info(f"跟踪止损计算错误: {str(e)}")
            return 0.0

    def _calculate_volatility_stop(self, price, volatility):
        """计算波动率止损价格"""
        try:
            stop_distance = price * volatility * \
                self.get_param("volatility_factor")
            return price - stop_distance
        except Exception as e:
            logger.info(f"波动率止损计算错误: {str(e)}")
            return 0.0

    def _calculate_fixed_stop(self, price):
        """计算固定止损价格"""
        try:
            return price * (1 - self.get_param("min_stop_loss"))
        except Exception as e:
            logger.info(f"固定止损计算错误: {str(e)}")
            return 0.0

    def _select_stop_price(self, price, stops, position, trend):
        """选择最终的止损价格"""
        try:
            # 1. 根据趋势选择止损策略
            if trend > 0:
                # 上升趋势，使用较宽松的止损
                stop_price = min(
                    stops['atr'],
                    stops['ma'],
                    stops['trailing']
                )
            else:
                # 下降趋势，使用较严格的止损
                stop_price = max(
                    stops['atr'],
                    stops['ma'],
                    stops['volatility']
                )

            # 2. 确保止损价格在合理范围内
            min_stop = price * (1 - self.get_param("max_stop_loss"))
            max_stop = price * (1 - self.get_param("min_stop_loss"))
            stop_price = max(min_stop, min(stop_price, max_stop))

            # 3. 如果已经盈利，使用更宽松的止损
            if price > position['entry_price']:
                profit_ratio = (
                    price - position['entry_price']) / position['entry_price']
                if profit_ratio > self.get_param("profit_lock"):
                    # 锁定部分利润
                    lock_price = position['entry_price'] * \
                        (1 + self.get_param("profit_lock"))
                    stop_price = max(stop_price, lock_price)

            return stop_price

        except Exception as e:
            logger.info(f"选择止损价格错误: {str(e)}")
            return 0.0

    def _update_position_info(self, stock, price, stop_price, datetime):
        """更新持仓信息"""
        try:
            if stock.market_code in self.positions:
                position = self.positions[stock.market_code]
                position['last_stop_price'] = stop_price
                position['last_update'] = datetime

                if price > position['highest_price']:
                    position['highest_price'] = price
                if price < position['lowest_price']:
                    position['lowest_price'] = price

        except Exception as e:
            logger.info(f"更新持仓信息错误: {str(e)}")
