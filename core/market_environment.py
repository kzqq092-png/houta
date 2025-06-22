from hikyuu import *
from hikyuu.trade_sys import EnvironmentBase
import numpy as np
import pandas as pd
from hikyuu.indicator import MA, MACD, RSI, BOLL, VOL, CLOSE, ATR, OBV, CCI
from core.services.indicator_ui_adapter import IndicatorUIAdapter


class MarketEnvironment(EnvironmentBase):
    """
    市场环境判断系统
    根据技术指标、市场情绪、宏观经济等因素判断市场环境
    """

    def __init__(self, params=None):
        super(MarketEnvironment, self).__init__("MarketEnvironment")
        # 获取统一指标管理器
        self.indicator_adapter = IndicatorUIAdapter()

        # 默认参数
        self.params = {
            "ma_short": 5,              # 短期均线
            "ma_mid": 20,               # 中期均线
            "ma_long": 60,              # 长期均线
            "macd_fast": 12,            # MACD快线
            "macd_slow": 26,            # MACD慢线
            "macd_signal": 9,           # MACD信号线
            "rsi_period": 14,           # RSI周期
            "rsi_overbought": 70,       # RSI超买阈值
            "rsi_oversold": 30,         # RSI超卖阈值
            "boll_period": 20,          # 布林带周期
            "boll_width": 2,            # 布林带宽度
            "volatility_window": 20,    # 波动率窗口
            "volume_ma": 20,            # 成交量均线
            "atr_period": 14,           # ATR周期
            "cci_period": 20,           # CCI周期
            "trend_threshold": 0.02,    # 趋势阈值
            "volatility_threshold": 0.05,  # 波动率阈值
            "volume_threshold": 1.5,    # 成交量阈值
        }
        if params is not None and isinstance(params, dict):
            self.params.update(params)
        for key, value in self.params.items():
            self.set_param(key, value)

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
        return MarketEnvironment(params=self.params)

    def _calculate(self, k, record):
        """计算市场环境"""
        try:
            # 获取K线数据
            if hasattr(k, 'to_df'):
                kdata = k.to_df()
            else:
                kdata = k

            # 计算技术指标
            indicators = self._calculate_indicators(kdata)

            # 判断市场环境
            environment = self._analyze_environment(indicators, kdata)

            # 记录环境变化
            record.set_environment(environment)

        except Exception as e:
            print(f"市场环境计算错误: {str(e)}")
            record.set_environment("neutral")

    def _calculate_indicators(self, k):
        """计算技术指标"""
        try:
            # 使用统一指标管理器计算指标
            try:
                # 移动平均线
                ma_short_resp = self.indicator_adapter.calculate_indicator('MA', k, period=self.get_param("ma_short"))
                ma_short = ma_short_resp.get('data') if ma_short_resp and ma_short_resp.get('success') else None

                ma_mid_resp = self.indicator_adapter.calculate_indicator('MA', k, period=self.get_param("ma_mid"))
                ma_mid = ma_mid_resp.get('data') if ma_mid_resp and ma_mid_resp.get('success') else None

                ma_long_resp = self.indicator_adapter.calculate_indicator('MA', k, period=self.get_param("ma_long"))
                ma_long = ma_long_resp.get('data') if ma_long_resp and ma_long_resp.get('success') else None

                # MACD
                macd_resp = self.indicator_adapter.calculate_indicator('MACD', k,
                                                                       fast_period=self.get_param("macd_fast"),
                                                                       slow_period=self.get_param("macd_slow"),
                                                                       signal_period=self.get_param("macd_signal"))
                macd_result = macd_resp.get('data') if macd_resp and macd_resp.get('success') else None

                # RSI
                rsi_resp = self.indicator_adapter.calculate_indicator('RSI', k, period=self.get_param("rsi_period"))
                rsi = rsi_resp.get('data') if rsi_resp and rsi_resp.get('success') else None

                # 布林带
                boll_resp = self.indicator_adapter.calculate_indicator('BOLL', k,
                                                                       period=self.get_param("boll_period"),
                                                                       std_dev=self.get_param("boll_width"))
                boll_result = boll_resp.get('data') if boll_resp and boll_resp.get('success') else None

                # ATR
                atr_resp = self.indicator_adapter.calculate_indicator('ATR', k, period=self.get_param("atr_period"))
                atr = atr_resp.get('data') if atr_resp and atr_resp.get('success') else None

                # OBV
                obv_resp = self.indicator_adapter.calculate_indicator('OBV', k)
                obv = obv_resp.get('data') if obv_resp and obv_resp.get('success') else None

                # CCI
                cci_resp = self.indicator_adapter.calculate_indicator('CCI', k, period=self.get_param("cci_period"))
                cci = cci_resp.get('data') if cci_resp and cci_resp.get('success') else None

                # 计算波动率和成交量均线
                if isinstance(k, pd.DataFrame) and 'close' in k.columns:
                    returns = k['close'].pct_change()
                    volatility = returns.rolling(window=self.get_param("volatility_window")).std()
                    volume_ma = k['volume'].rolling(window=self.get_param("volume_ma")).mean()
                    close = k['close']
                    volume = k['volume']
                else:
                    volatility = None
                    volume_ma = None
                    close = None
                    volume = None

            except Exception as e:
                # 回退到hikyuu指标
                print(f"统一指标管理器计算失败，回退到hikyuu指标: {str(e)}")
                close_ind = CLOSE(k)
                ma_short = MA(close_ind, n=self.get_param("ma_short"))
                ma_mid = MA(close_ind, n=self.get_param("ma_mid"))
                ma_long = MA(close_ind, n=self.get_param("ma_long"))
                macd_result = MACD(close_ind, n1=self.get_param("macd_fast"),
                                   n2=self.get_param("macd_slow"),
                                   n3=self.get_param("macd_signal"))
                rsi = RSI(close_ind, n=self.get_param("rsi_period"))
                boll_result = BOLL(close_ind, n=self.get_param("boll_period"), width=self.get_param("boll_width"))
                atr = ATR(k, n=self.get_param("atr_period"))
                obv = OBV(k)
                cci = CCI(k, n=self.get_param("cci_period"))

                # hikyuu Indicator不直接支持pct_change
                returns = None
                volatility = None
                volume_ma = MA(VOL(k), n=self.get_param("volume_ma"))
                close = close_ind
                volume = VOL(k)

            return {
                'ma_short': ma_short,
                'ma_mid': ma_mid,
                'ma_long': ma_long,
                'macd': macd_result,
                'rsi': rsi,
                'boll': boll_result,
                'volatility': volatility,
                'volume_ma': volume_ma,
                'close': close,
                'volume': volume,
                'atr': atr,
                'obv': obv,
                'cci': cci
            }
        except Exception as e:
            print(f"技术指标计算错误: {str(e)}")
            return {}

    def _analyze_environment(self, indicators, k):
        """分析市场环境"""
        try:
            environment_score = 0
            factors = []

            # 趋势分析
            trend_score = self._analyze_trend(indicators)
            environment_score += trend_score * 0.3
            factors.append(f"趋势: {trend_score}")

            # 动量分析
            momentum_score = self._analyze_momentum(indicators)
            environment_score += momentum_score * 0.25
            factors.append(f"动量: {momentum_score}")

            # 波动率分析
            volatility_score = self._analyze_volatility(indicators)
            environment_score += volatility_score * 0.2
            factors.append(f"波动率: {volatility_score}")

            # 成交量分析
            volume_score = self._analyze_volume(indicators)
            environment_score += volume_score * 0.15
            factors.append(f"成交量: {volume_score}")

            # 超买超卖分析
            overbought_score = self._analyze_overbought(indicators)
            environment_score += overbought_score * 0.1
            factors.append(f"超买超卖: {overbought_score}")

            # 根据综合得分判断环境
            if environment_score > 2:
                return "bullish"
            elif environment_score < -2:
                return "bearish"
            else:
                return "neutral"

        except Exception as e:
            print(f"市场环境分析错误: {str(e)}")
            return "neutral"

    def _analyze_trend(self, indicators):
        """分析趋势"""
        try:
            ma_short = indicators.get('ma_short')
            ma_mid = indicators.get('ma_mid')
            ma_long = indicators.get('ma_long')

            if ma_short is None or ma_mid is None or ma_long is None:
                return 0

            # 获取最新值
            if hasattr(ma_short, 'iloc'):
                short_val = ma_short.iloc[-1]
                mid_val = ma_mid.iloc[-1]
                long_val = ma_long.iloc[-1]
            else:
                short_val = ma_short[-1]
                mid_val = ma_mid[-1]
                long_val = ma_long[-1]

            score = 0
            if short_val > mid_val > long_val:
                score = 3  # 强多头趋势
            elif short_val > mid_val:
                score = 1  # 弱多头趋势
            elif short_val < mid_val < long_val:
                score = -3  # 强空头趋势
            elif short_val < mid_val:
                score = -1  # 弱空头趋势

            return score
        except Exception:
            return 0

    def _analyze_momentum(self, indicators):
        """分析动量"""
        try:
            macd = indicators.get('macd')
            rsi = indicators.get('rsi')

            score = 0

            # MACD分析
            if macd is not None:
                if hasattr(macd, 'iloc'):
                    macd_val = macd.iloc[-1]
                elif isinstance(macd, dict):
                    macd_val = macd.get('main', 0)
                else:
                    macd_val = macd[-1] if hasattr(macd, '__getitem__') else 0

                if macd_val > 0:
                    score += 1
                elif macd_val < 0:
                    score -= 1

            # RSI分析
            if rsi is not None:
                if hasattr(rsi, 'iloc'):
                    rsi_val = rsi.iloc[-1]
                else:
                    rsi_val = rsi[-1] if hasattr(rsi, '__getitem__') else 50

                if rsi_val > 50:
                    score += 1
                elif rsi_val < 50:
                    score -= 1

            return score
        except Exception:
            return 0

    def _analyze_volatility(self, indicators):
        """分析波动率"""
        try:
            volatility = indicators.get('volatility')
            atr = indicators.get('atr')

            score = 0

            # 波动率分析
            if volatility is not None:
                if hasattr(volatility, 'iloc'):
                    vol_val = volatility.iloc[-1]
                else:
                    vol_val = volatility[-1] if hasattr(volatility, '__getitem__') else 0

                if vol_val > self.get_param("volatility_threshold"):
                    score -= 1  # 高波动率不利
                else:
                    score += 1  # 低波动率有利

            return score
        except Exception:
            return 0

    def _analyze_volume(self, indicators):
        """分析成交量"""
        try:
            volume = indicators.get('volume')
            volume_ma = indicators.get('volume_ma')

            if volume is None or volume_ma is None:
                return 0

            # 获取最新值
            if hasattr(volume, 'iloc'):
                vol_val = volume.iloc[-1]
                vol_ma_val = volume_ma.iloc[-1]
            else:
                vol_val = volume[-1]
                vol_ma_val = volume_ma[-1]

            if vol_val > vol_ma_val * self.get_param("volume_threshold"):
                return 1  # 成交量放大
            else:
                return 0  # 成交量正常

        except Exception:
            return 0

    def _analyze_overbought(self, indicators):
        """分析超买超卖"""
        try:
            rsi = indicators.get('rsi')
            cci = indicators.get('cci')

            score = 0

            # RSI超买超卖
            if rsi is not None:
                if hasattr(rsi, 'iloc'):
                    rsi_val = rsi.iloc[-1]
                else:
                    rsi_val = rsi[-1] if hasattr(rsi, '__getitem__') else 50

                if rsi_val > self.get_param("rsi_overbought"):
                    score -= 2  # 超买
                elif rsi_val < self.get_param("rsi_oversold"):
                    score += 2  # 超卖

            # CCI超买超卖
            if cci is not None:
                if hasattr(cci, 'iloc'):
                    cci_val = cci.iloc[-1]
                else:
                    cci_val = cci[-1] if hasattr(cci, '__getitem__') else 0

                if cci_val > 100:
                    score -= 1  # 超买
                elif cci_val < -100:
                    score += 1  # 超卖

            return score
        except Exception:
            return 0

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
