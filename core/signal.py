from hikyuu import *
from hikyuu.trade_sys import SignalBase
from hikyuu.indicator import (
    MA, MACD, RSI, KDJ, CLOSE, VOL, BOLL, ATR, CCI, OBV, DMI
)
import numpy as np
import joblib
from indicators_algo import calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci, get_talib_indicator_list, get_talib_category, get_all_indicators_by_category, calc_talib_indicator
import pandas as pd


class EnhancedTradingSignal(SignalBase):
    """
    增强的交易信号生成器
    继承Hikyuu的SignalBase类创建自定义交易信号
    """

    def __init__(self, params=None):
        super(EnhancedTradingSignal, self).__init__("EnhancedTradingSignal")

        # 设置默认参数
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

        # 初始化机器学习模型
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
            # 准备特征数据
            features = self._prepare_ml_features(k)
            if features is None:
                return 0

            # 预测信号
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
                # 添加更多特征...

            if not features:
                return None

            return np.column_stack(features)

        except Exception as e:
            print(f"准备机器学习特征失败: {str(e)}")
            return None

    def _clone(self):
        return EnhancedTradingSignal(params=self.params)

    def _calculate(self, k, record):
        try:
            indicators = {}
            talib_list = get_talib_indicator_list()
            category_map = get_all_indicators_by_category()
            # 只输出有指标的分类
            visible_count = {cat: len(names)
                             for cat, names in category_map.items() if names}
            for cat, count in visible_count.items():
                print(f"信号-分类: {cat}，可见指标数: {count}")
            if not talib_list or not category_map:
                print("未检测到任何ta-lib指标，请检查ta-lib安装或数据源！")
                return
            for name in talib_list:
                try:
                    val = calc_talib_indicator(name, k)
                    if isinstance(val, pd.DataFrame):
                        for col in val.columns:
                            indicators[f"{name}_{col}".upper()] = val[col]
                    else:
                        indicators[name.upper()] = val
                except Exception:
                    continue
            # 其余信号逻辑保持不变，可根据indicators字典灵活取用
            ma_fast = indicators.get('MA', calc_ma(
                k['close'], self.get_param("n_fast")))
            ma_slow = indicators.get('EMA', calc_ma(
                k['close'], self.get_param("n_slow")))
            macd = indicators.get(
                'MACD_1', None) or indicators.get('MACD', None)
            rsi = indicators.get('RSI', None) or calc_rsi(
                k['close'], self.get_param("rsi_window"))
            volume_ma = MA(VOL(k), n=self.get_param("volume_ma"))

            # 2. 计算额外技术指标
            kdj = calc_kdj(k, self.get_param("kdj_n"))
            boll = calc_boll(k['close'], self.get_param(
                "boll_n"), self.get_param("boll_width"))
            atr = calc_atr(k, self.get_param("atr_period"))
            cci = calc_cci(k, self.get_param("cci_period"))
            obv = calc_obv(k)
            obv_ma = MA(obv, n=self.get_param("obv_ma"))
            dmi = DMI(k, n=self.get_param("dmi_period"))

            # 3. 计算市场状态和波动率
            self.market_regime = self._detect_market_regime(
                k, ma_fast, ma_slow)
            self.volatility = self._calculate_volatility(k, atr)

            # 4. 计算机器学习信号
            ml_signal = self._calculate_ml_signal(k)

            n = len(k)
            for i in range(2, n):
                # 初始化信号强度
                signal_strength = {
                    "trend": 0,
                    "momentum": 0,
                    "volume": 0,
                    "volatility": 0,
                    "ml": ml_signal
                }

                # 5. 趋势确认
                trend_up = ma_fast[i] > ma_slow[i] and ma_fast[i -
                                                               1] <= ma_slow[i-1]
                trend_down = ma_fast[i] < ma_slow[i] and ma_fast[i -
                                                                 1] >= ma_slow[i-1]

                if trend_up:
                    signal_strength["trend"] += 1
                elif trend_down:
                    signal_strength["trend"] -= 1

                # 6. 动量确认
                macd_up = macd[i] > 0 and macd[i-1] <= 0
                macd_down = macd[i] < 0 and macd[i-1] >= 0

                if macd_up:
                    signal_strength["momentum"] += 1
                elif macd_down:
                    signal_strength["momentum"] -= 1

                # 7. 成交量确认
                volume_confirm = VOL(k)[i] > volume_ma[i] * \
                    self.get_param("volume_ratio")
                if volume_confirm:
                    signal_strength["volume"] += 1

                # 8. 波动率确认
                if self.volatility > self.get_param("volatility_threshold"):
                    signal_strength["volatility"] -= 1

                # 9. 计算综合信号强度
                total_strength = sum(
                    strength * self.get_param("signal_weights")[category]
                    for category, strength in signal_strength.items()
                )

                # 10. 根据市场状态调整信号强度
                if self.market_regime == "bullish":
                    total_strength *= 1.2
                elif self.market_regime == "bearish":
                    total_strength *= 0.8

                # 11. 生成信号
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

                # 12. 清理历史信号
                if len(self.signal_history) > self.get_param("signal_confirm_window"):
                    self.signal_history.pop(0)

        except Exception as e:
            print(f"信号计算错误: {str(e)}")
            return

    def _detect_market_regime(self, k, ma_fast, ma_slow):
        """检测市场状态"""
        try:
            # 计算趋势强度
            trend_strength = (ma_fast[-1] - ma_slow[-1]) / ma_slow[-1]

            # 根据趋势强度判断市场状态
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
            # 使用ATR计算波动率
            return atr[-1] / CLOSE(k)[-1]
        except Exception as e:
            print(f"波动率计算错误: {str(e)}")
            return 0.0


def get_indicator_categories():
    """获取所有指标分类及其指标列表，确保与ta-lib分类一致"""
    from indicators_algo import get_all_indicators_by_category
    return get_all_indicators_by_category()
