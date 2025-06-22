import numpy as np
import pandas as pd
from hikyuu import *
from hikyuu.trade_sys import SignalBase
from hikyuu.indicator import MA, MACD, RSI, KDJ, CLOSE, VOL, ATR, CCI, OBV, DMI
from core.services.indicator_ui_adapter import IndicatorUIAdapter


class EnhancedSignal(SignalBase):
    """
    增强的交易信号系统（唯一实现）
    支持多因子、机器学习、信号权重、技术/基本面/量价等多维度因子
    """

    def __init__(self, params=None):
        super(EnhancedSignal, self).__init__("EnhancedSignal")
        # 获取统一指标管理器
        self.indicator_adapter = IndicatorUIAdapter()

        # 默认参数
        self.params = {
            "n_fast": 12,              # 快速均线周期
            "n_slow": 26,              # 慢速均线周期
            "n_signal": 9,             # 信号线周期
            "rsi_window": 14,          # RSI计算窗口
            "rsi_buy_threshold": 30,   # RSI买入阈值
            "rsi_sell_threshold": 70,  # RSI卖出阈值
            "volume_ma": 20,           # 成交量均线周期
            "trend_strength": 0.02,    # 趋势强度阈值
            "signal_confirm_window": 3,  # 信号确认窗口
            "min_signal_strength": 2,   # 最小信号强度要求
            "kdj_n": 9,                # KDJ周期
            "boll_n": 20,              # 布林带周期
            "boll_width": 2,           # 布林带宽度
            "atr_period": 14,          # ATR周期
            "atr_multiplier": 2,       # ATR倍数
            "cci_period": 20,          # CCI周期
            "cci_threshold": 100,      # CCI阈值
            "obv_ma": 20,              # OBV均线周期
            "dmi_period": 14,          # DMI周期
            "dmi_threshold": 25,       # DMI阈值
            "volume_ratio": 1.5,       # 成交量比率阈值
            "volatility_threshold": 1.5,  # 波动率阈值
            "enable_ml": False,        # 是否启用机器学习
            "ml_model_path": None,     # 机器学习模型路径
            "ml_features": [],         # 机器学习特征列表
            "ml_threshold": 0.6,       # 机器学习信号阈值
            "signal_weights": {        # 信号权重
                "trend": 0.3,
                "momentum": 0.2,
                "volume": 0.15,
                "volatility": 0.15,
                "ml": 0.2
            }
        }
        if params is not None and isinstance(params, dict):
            self.params.update(params)
        for key, value in self.params.items():
            self.set_param(key, value)
        self.signal_history = []  # 用于存储历史信号
        self.last_signal = 0      # 上一个信号
        self.market_regime = "neutral"  # 市场状态
        self.volatility = 0.0     # 市场波动率
        self.ml_model = None      # 机器学习模型
        if self.get_param("enable_ml") and self.get_param("ml_model_path"):
            self._load_ml_model()

    def _load_ml_model(self):
        """加载机器学习模型"""
        try:
            import joblib
            self.ml_model = joblib.load(self.get_param("ml_model_path"))
        except Exception as e:
            print(f"加载机器学习模型失败: {str(e)}")
            self.ml_model = None

    def _calculate_ml_signal(self, k):
        """计算机器学习信号"""
        if not self.ml_model or not self.get_param("enable_ml"):
            return 0
        try:
            features = self._prepare_ml_features(k)
            if features is None:
                return 0
            prediction = self.ml_model.predict_proba(features)[:, 1]
            return prediction[-1] if prediction[-1] > self.get_param("ml_threshold") else 0
        except Exception as e:
            print(f"机器学习信号计算错误: {str(e)}")
            return 0

    def _prepare_ml_features(self, k):
        """准备机器学习特征"""
        try:
            features = []
            for feature_name in self.get_param("ml_features"):
                if feature_name == "close":
                    features.append(CLOSE(k))
                elif feature_name == "volume":
                    features.append(VOL(k))
                elif feature_name == "rsi":
                    features.append(
                        RSI(CLOSE(k), n=self.get_param("rsi_window")))
                # 可扩展更多特征
            if not features:
                return None
            return np.column_stack(features)
        except Exception as e:
            print(f"准备机器学习特征失败: {str(e)}")
            return None

    def _clone(self):
        return EnhancedSignal(params=self.params)

    def _calculate(self, k, record):
        try:
            # 使用统一指标管理器计算所有指标
            indicators = {}

            # 获取K线数据
            if hasattr(k, 'to_df'):
                kdata = k.to_df()
            else:
                kdata = k

            # 计算基础指标
            n_fast = self.get_param("n_fast")
            n_slow = self.get_param("n_slow")

            try:
                # 移动平均线
                ma_fast_resp = self.indicator_adapter.calculate_indicator('MA', kdata, period=n_fast)
                ma_fast = ma_fast_resp.get('data') if ma_fast_resp and ma_fast_resp.get('success') else None

                ma_slow_resp = self.indicator_adapter.calculate_indicator('MA', kdata, period=n_slow)
                ma_slow = ma_slow_resp.get('data') if ma_slow_resp and ma_slow_resp.get('success') else None

                # MACD
                macd_resp = self.indicator_adapter.calculate_indicator('MACD', kdata,
                                                                       fast_period=n_fast,
                                                                       slow_period=n_slow,
                                                                       signal_period=self.get_param("n_signal"))
                macd_result = macd_resp.get('data') if macd_resp and macd_resp.get('success') else None
                if isinstance(macd_result, dict):
                    macd = macd_result.get('main', macd_result.get('macd'))
                else:
                    macd = macd_result

                # RSI
                rsi_resp = self.indicator_adapter.calculate_indicator('RSI', kdata, period=self.get_param("rsi_window"))
                rsi = rsi_resp.get('data') if rsi_resp and rsi_resp.get('success') else None

                # KDJ
                kdj_resp = self.indicator_adapter.calculate_indicator('KDJ', kdata, k_period=self.get_param("kdj_n"))
                kdj_result = kdj_resp.get('data') if kdj_resp and kdj_resp.get('success') else None

                # 布林带
                boll_resp = self.indicator_adapter.calculate_indicator('BOLL', kdata,
                                                                       period=self.get_param("boll_n"),
                                                                       std_dev=self.get_param("boll_width"))
                boll_result = boll_resp.get('data') if boll_resp and boll_resp.get('success') else None

                # ATR
                atr_resp = self.indicator_adapter.calculate_indicator('ATR', kdata, period=self.get_param("atr_period"))
                atr = atr_resp.get('data') if atr_resp and atr_resp.get('success') else None

                # CCI
                cci_resp = self.indicator_adapter.calculate_indicator('CCI', kdata, period=self.get_param("cci_period"))
                cci = cci_resp.get('data') if cci_resp and cci_resp.get('success') else None

                # OBV
                obv_resp = self.indicator_adapter.calculate_indicator('OBV', kdata)
                obv = obv_resp.get('data') if obv_resp and obv_resp.get('success') else None

                # 成交量均线
                if 'volume' in kdata.columns:
                    volume_ma = kdata['volume'].rolling(window=self.get_param("volume_ma")).mean()
                else:
                    volume_ma = None

            except Exception as e:
                # 回退到hikyuu指标
                print(f"统一指标管理器计算失败，回退到hikyuu指标: {str(e)}")
                close_ind = CLOSE(k)
                ma_fast = MA(close_ind, n=n_fast)
                ma_slow = MA(close_ind, n=n_slow)
                macd = MACD(close_ind, n1=n_fast, n2=n_slow, n3=self.get_param("n_signal"))
                rsi = RSI(close_ind, n=self.get_param("rsi_window"))
                volume_ma = MA(VOL(k), n=self.get_param("volume_ma"))
                atr = ATR(k, n=self.get_param("atr_period"))
                cci = CCI(k, n=self.get_param("cci_period"))
                obv = OBV(k)

            # DMI (继续使用hikyuu)
            dmi = DMI(k, n=self.get_param("dmi_period"))

            # 计算市场状态和波动率
            self.market_regime = self._detect_market_regime(k, ma_fast, ma_slow)
            self.volatility = self._calculate_volatility(k, atr)

            # 机器学习信号
            ml_signal = self._calculate_ml_signal(k)

            n = len(k)
            for i in range(2, n):
                signal_strength = {
                    "trend": 0,
                    "momentum": 0,
                    "volume": 0,
                    "volatility": 0,
                    "ml": ml_signal
                }

                # 趋势信号
                if hasattr(ma_fast, '__getitem__') and hasattr(ma_slow, '__getitem__'):
                    trend_up = ma_fast[i] > ma_slow[i] and ma_fast[i-1] <= ma_slow[i-1]
                    trend_down = ma_fast[i] < ma_slow[i] and ma_fast[i-1] >= ma_slow[i-1]
                elif hasattr(ma_fast, 'iloc') and hasattr(ma_slow, 'iloc'):
                    trend_up = ma_fast.iloc[i] > ma_slow.iloc[i] and ma_fast.iloc[i-1] <= ma_slow.iloc[i-1]
                    trend_down = ma_fast.iloc[i] < ma_slow.iloc[i] and ma_fast.iloc[i-1] >= ma_slow.iloc[i-1]
                else:
                    trend_up = False
                    trend_down = False

                if trend_up:
                    signal_strength["trend"] += 1
                elif trend_down:
                    signal_strength["trend"] -= 1

                # 动量信号
                macd_up = macd[i] > 0 and macd[i-1] <= 0
                macd_down = macd[i] < 0 and macd[i-1] >= 0
                if macd_up:
                    signal_strength["momentum"] += 1
                elif macd_down:
                    signal_strength["momentum"] -= 1

                # 成交量信号
                volume_confirm = VOL(k)[i] > volume_ma[i] * self.get_param("volume_ratio")
                if volume_confirm:
                    signal_strength["volume"] += 1

                # 波动率信号
                if self.volatility > self.get_param("volatility_threshold"):
                    signal_strength["volatility"] -= 1

                # 机器学习信号
                signal_strength["ml"] = ml_signal

                total_strength = sum(
                    strength * self.get_param("signal_weights")[category]
                    for category, strength in signal_strength.items()
                )

                if self.market_regime == "bullish":
                    total_strength *= 1.2
                elif self.market_regime == "bearish":
                    total_strength *= 0.8

                if total_strength >= self.get_param("min_signal_strength"):
                    if self.last_signal <= 0:
                        record.add_buy_signal(k[i].datetime)
                        self.last_signal = 1
                        self.signal_history.append((k[i].datetime, 1))
                elif total_strength <= -self.get_param("min_signal_strength"):
                    if self.last_signal >= 0:
                        record.add_sell_signal(k[i].datetime)
                        self.last_signal = -1
                        self.signal_history.append((k[i].datetime, -1))

                if len(self.signal_history) > self.get_param("signal_confirm_window"):
                    self.signal_history.pop(0)
        except Exception as e:
            print(f"信号计算错误: {str(e)}")
            return

    def _detect_market_regime(self, k, ma_fast, ma_slow):
        """检测市场状态"""
        try:
            trend_strength = (ma_fast[-1] - ma_slow[-1]) / ma_slow[-1]
            if trend_strength > self.get_param("trend_strength"):
                return "bullish"
            elif trend_strength < -self.get_param("trend_strength"):
                return "bearish"
            else:
                return "neutral"
        except Exception as e:
            print(f"市场状态检测错误: {str(e)}")
            return "neutral"

    def _calculate_volatility(self, k, atr):
        """计算市场波动率"""
        try:
            return atr[-1] / CLOSE(k)[-1]
        except Exception as e:
            print(f"波动率计算错误: {str(e)}")
            return 0.0
