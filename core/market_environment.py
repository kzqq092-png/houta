from hikyuu import *
from hikyuu.trade_sys import EnvironmentBase
import numpy as np
import pandas as pd


class MarketEnvironment(EnvironmentBase):
    """
    市场环境判断模块
    继承Hikyuu的EnvironmentBase类，实现市场环境分析
    """

    def __init__(self, params=None):
        super(MarketEnvironment, self).__init__("MarketEnvironment")

        # 设置默认参数
        self.set_param("ma_short", 5)           # 短期均线周期
        self.set_param("ma_mid", 20)            # 中期均线周期
        self.set_param("ma_long", 60)           # 长期均线周期
        self.set_param("volatility_window", 20)  # 波动率计算窗口
        self.set_param("trend_window", 50)      # 趋势计算窗口
        self.set_param("volume_ma", 20)         # 成交量均线周期
        self.set_param("rsi_period", 14)        # RSI周期
        self.set_param("macd_fast", 12)         # MACD快线周期
        self.set_param("macd_slow", 26)         # MACD慢线周期
        self.set_param("macd_signal", 9)        # MACD信号线周期
        self.set_param("boll_period", 20)       # 布林带周期
        self.set_param("boll_width", 2)         # 布林带宽度
        self.set_param("volatility_threshold", 0.02)  # 波动率阈值
        self.set_param("trend_threshold", 0.02)       # 趋势强度阈值
        self.set_param("volume_threshold", 1.5)       # 成交量阈值

        # 初始化市场状态
        self.market_state = {
            'trend': 'neutral',      # 趋势状态：up/down/neutral
            'volatility': 'normal',  # 波动率状态：high/normal/low
            'volume': 'normal',      # 成交量状态：high/normal/low
            'strength': 0.0,         # 趋势强度
            'regime': 'normal'       # 市场状态：bull/bear/neutral
        }

    def _reset(self):
        """重置状态"""
        self.market_state = {
            'trend': 'neutral',
            'volatility': 'normal',
            'volume': 'normal',
            'strength': 0.0,
            'regime': 'normal'
        }

    def _clone(self):
        return MarketEnvironment()

    def _calculate(self, k):
        """计算市场环境"""
        try:
            # 1. 计算技术指标
            indicators = self._calculate_indicators(k)

            # 2. 分析市场状态
            self._analyze_trend(indicators)
            self._analyze_volatility(indicators)
            self._analyze_volume(indicators)
            self._analyze_market_regime(indicators)

            # 3. 综合判断市场环境
            return self._judge_market_environment()

        except Exception as e:
            print(f"市场环境分析错误: {str(e)}")
            return True

    def _calculate_indicators(self, k):
        """计算技术指标"""
        try:
            df = k.to_df()
            # 计算移动平均线
            if isinstance(df['close'], pd.Series):
                from core.indicators_algo import calc_ma, calc_macd, calc_rsi
                ma_short = calc_ma(df['close'], self.get_param("ma_short"))
                ma_mid = calc_ma(df['close'], self.get_param("ma_mid"))
                ma_long = calc_ma(df['close'], self.get_param("ma_long"))
                macd, _, _ = calc_macd(df['close'], self.get_param("macd_fast"), self.get_param("macd_slow"), self.get_param("macd_signal"))
                rsi = calc_rsi(df['close'], self.get_param("rsi_period"))
                # 布林带、波动率等同理
                returns = df['close'].pct_change()
                volatility = returns.rolling(window=self.get_param("volatility_window")).std()
                volume_ma = df['volume'].rolling(window=self.get_param("volume_ma")).mean()
                close = df['close']
                volume = df['volume']
            else:
                from hikyuu.indicator import MA, MACD, RSI, BOLL, VOL
                close_ind = CLOSE(k)
                ma_short = MA(close_ind, n=self.get_param("ma_short"))
                ma_mid = MA(close_ind, n=self.get_param("ma_mid"))
                ma_long = MA(close_ind, n=self.get_param("ma_long"))
                macd = MACD(close_ind, n1=self.get_param("macd_fast"), n2=self.get_param("macd_slow"), n3=self.get_param("macd_signal"))
                rsi = RSI(close_ind, n=self.get_param("rsi_period"))
                boll = BOLL(close_ind, n=self.get_param("boll_period"), width=self.get_param("boll_width"))
                # 波动率
                returns = None  # hikyuu Indicator不直接支持pct_change
                volatility = None
                volume_ma = MA(VOL(k), n=self.get_param("volume_ma"))
                close = close_ind
                volume = VOL(k)
            # --- 类型安全指标计算 ---
            if isinstance(df['close'], pd.Series):
                from core.indicators_algo import calc_boll, calc_atr, calc_obv, calc_cci
                boll = calc_boll(df['close'], self.get_param("boll_period"), self.get_param("boll_width"))
                atr = calc_atr(df, self.get_param("atr_period"))
                obv = calc_obv(df)
                cci = calc_cci(df, self.get_param("cci_period"))
            else:
                from hikyuu.indicator import BOLL, ATR, OBV, CCI, CLOSE
                close_ind = CLOSE(k)
                boll = BOLL(close_ind, n=self.get_param("boll_period"), width=self.get_param("boll_width"))
                atr = ATR(k, n=self.get_param("atr_period"))
                obv = OBV(k)
                cci = CCI(k, n=self.get_param("cci_period"))
            return {
                'ma_short': ma_short,
                'ma_mid': ma_mid,
                'ma_long': ma_long,
                'macd': macd,
                'rsi': rsi,
                'boll': boll if 'boll' in locals() else None,
                'volatility': volatility,
                'volume_ma': volume_ma,
                'close': close,
                'volume': volume
            }
        except Exception as e:
            print(f"技术指标计算错误: {str(e)}")
            return {}

    def _analyze_trend(self, indicators):
        """分析趋势"""
        try:
            # 1. 计算趋势强度
            ma_short = indicators['ma_short']
            ma_mid = indicators['ma_mid']
            ma_long = indicators['ma_long']

            # 短期趋势
            short_trend = (ma_short[-1] - ma_short[-5]) / ma_short[-5]
            # 中期趋势
            mid_trend = (ma_mid[-1] - ma_mid[-5]) / ma_mid[-5]
            # 长期趋势
            long_trend = (ma_long[-1] - ma_long[-5]) / ma_long[-5]

            # 综合趋势强度
            trend_strength = (short_trend + mid_trend + long_trend) / 3

            # 判断趋势方向
            if trend_strength > self.get_param("trend_threshold"):
                self.market_state['trend'] = 'up'
            elif trend_strength < -self.get_param("trend_threshold"):
                self.market_state['trend'] = 'down'
            else:
                self.market_state['trend'] = 'neutral'

            self.market_state['strength'] = abs(trend_strength)

        except Exception as e:
            print(f"趋势分析错误: {str(e)}")

    def _analyze_volatility(self, indicators):
        """分析波动率"""
        try:
            volatility = indicators['volatility'].iloc[-1]

            if volatility > self.get_param("volatility_threshold") * 1.5:
                self.market_state['volatility'] = 'high'
            elif volatility < self.get_param("volatility_threshold") * 0.5:
                self.market_state['volatility'] = 'low'
            else:
                self.market_state['volatility'] = 'normal'

        except Exception as e:
            print(f"波动率分析错误: {str(e)}")

    def _analyze_volume(self, indicators):
        """分析成交量"""
        try:
            volume = indicators['volume'][-1]
            volume_ma = indicators['volume_ma'][-1]
            volume_ratio = volume / volume_ma

            if volume_ratio > self.get_param("volume_threshold"):
                self.market_state['volume'] = 'high'
            elif volume_ratio < 1/self.get_param("volume_threshold"):
                self.market_state['volume'] = 'low'
            else:
                self.market_state['volume'] = 'normal'

        except Exception as e:
            print(f"成交量分析错误: {str(e)}")

    def _analyze_market_regime(self, indicators):
        """分析市场状态"""
        try:
            # 1. 获取各项指标
            rsi = indicators['rsi'][-1]
            macd = indicators['macd']
            boll = indicators['boll']
            close = indicators['close'][-1]

            # 2. 计算市场状态得分
            score = 0

            # RSI得分
            if rsi > 70:
                score -= 1
            elif rsi < 30:
                score += 1

            # MACD得分
            if macd.diff[-1] > 0 and macd.dea[-1] > 0:
                score += 1
            elif macd.diff[-1] < 0 and macd.dea[-1] < 0:
                score -= 1

            # 布林带得分
            if close > boll.upper[-1]:
                score -= 1
            elif close < boll.lower[-1]:
                score += 1

            # 3. 判断市场状态
            if score >= 2:
                self.market_state['regime'] = 'bull'
            elif score <= -2:
                self.market_state['regime'] = 'bear'
            else:
                self.market_state['regime'] = 'neutral'

        except Exception as e:
            print(f"市场状态分析错误: {str(e)}")

    def _judge_market_environment(self):
        """综合判断市场环境"""
        try:
            # 1. 获取市场状态
            trend = self.market_state['trend']
            volatility = self.market_state['volatility']
            volume = self.market_state['volume']
            regime = self.market_state['regime']

            # 2. 判断是否适合交易
            if regime == 'bull' and trend == 'up' and volatility == 'normal' and volume == 'normal':
                return True  # 适合做多
            elif regime == 'bear' and trend == 'down' and volatility == 'normal' and volume == 'normal':
                return True  # 适合做空
            elif regime == 'neutral' and volatility == 'low' and volume == 'normal':
                return True  # 适合震荡交易
            else:
                return False  # 不适合交易

        except Exception as e:
            print(f"市场环境判断错误: {str(e)}")
            return True

    def get_market_state(self):
        """获取当前市场状态"""
        return self.market_state

    def is_bull_market(self):
        """判断是否为牛市"""
        return self.market_state['regime'] == 'bull'

    def is_bear_market(self):
        """判断是否为熊市"""
        return self.market_state['regime'] == 'bear'

    def is_high_volatility(self):
        """判断是否为高波动率"""
        return self.market_state['volatility'] == 'high'

    def is_high_volume(self):
        """判断是否为高成交量"""
        return self.market_state['volume'] == 'high'

    def get_trend_strength(self):
        """获取趋势强度"""
        return self.market_state['strength']
