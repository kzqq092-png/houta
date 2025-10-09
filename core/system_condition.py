from hikyuu import *
from hikyuu.trade_sys import ConditionBase
import numpy as np
import pandas as pd
from core.indicator_adapter import get_talib_indicator_list, calc_talib_indicator
# 已替换为新的导入

from core.indicator_service import calculate_indicator, get_indicator_metadata, get_all_indicators_metadata
from loguru import logger

class EnhancedSystemCondition(ConditionBase):
    """
    增强的系统有效条件判断
    继承Hikyuu的ConditionBase类创建自定义系统有效条件
    """

    def __init__(self, params=None):
        super(EnhancedSystemCondition, self).__init__(
            "EnhancedSystemCondition")

        # 设置默认参数
        self.set_param("ma_period", 20)          # 均线周期
        self.set_param("volume_ma_period", 20)   # 成交量均线周期
        self.set_param("volatility_period", 20)  # 波动率计算周期
        self.set_param("trend_period", 50)       # 趋势判断周期
        self.set_param("volume_ratio", 1.5)      # 成交量比率阈值
        self.set_param("trend_threshold", 0.02)  # 趋势强度阈值
        self.set_param("volatility_threshold", 0.02)  # 波动率阈值
        self.set_param("min_price", 5.0)         # 最小价格限制
        self.set_param("max_price", 500.0)       # 最大价格限制
        self.set_param("min_volume", 1000000)    # 最小成交量限制
        self.set_param("enable_ml", False)       # 是否启用机器学习
        self.set_param("ml_model_path", None)    # 机器学习模型路径

        # 初始化状态
        self.market_regime = "neutral"  # 市场状态
        self.volatility = 0.0          # 市场波动率
        self.trend_strength = 0.0      # 趋势强度
        self.volume_ratio = 0.0        # 成交量比率

    def _reset(self):
        """重置状态"""
        self.market_regime = "neutral"
        self.volatility = 0.0
        self.trend_strength = 0.0
        self.volume_ratio = 0.0

    def _clone(self):
        return EnhancedSystemCondition()

    def _calculate(self, k):
        """计算系统是否有效"""
        try:
            # 1. 基础数据检查
            if not self._check_basic_conditions(k):
                return False

            # 2. 计算技术指标
            indicators = self._calculate_indicators(k)

            # 3. 判断市场状态
            self.market_regime = self._detect_market_regime(k, indicators)

            # 4. 计算波动率
            self.volatility = self._calculate_volatility(k)

            # 5. 计算趋势强度
            self.trend_strength = self._calculate_trend_strength(k)

            # 6. 计算成交量比率
            self.volume_ratio = self._calculate_volume_ratio(k)

            # 7. 综合判断
            return self._make_decision(k, indicators)

        except Exception as e:
            logger.info(f"系统条件判断错误: {str(e)}")
            return False

    def _check_basic_conditions(self, k):
        """检查基础条件"""
        try:
            # 检查数据长度
            if len(k) < self.get_param("ma_period"):
                return False

            # 检查价格范围
            current_price = CLOSE(k)[-1]
            if current_price < self.get_param("min_price") or current_price > self.get_param("max_price"):
                return False

            # 检查成交量
            current_volume = VOL(k)[-1]
            if current_volume < self.get_param("min_volume"):
                return False

            return True

        except Exception as e:
            logger.info(f"基础条件检查错误: {str(e)}")
            return False

    def _calculate_indicators(self, k):
        """计算技术指标，全部用ta-lib封装，自动适配参数，兼容Series/DataFrame，分类与主界面一致，修复无指标问题"""
        try:
            indicators = {}
            talib_list = get_talib_indicator_list()
            category_map = get_all_indicators_by_category()
            visible_count = {cat: len(names)
                             for cat, names in category_map.items() if names}
            for cat, count in visible_count.items():
                logger.info(f"系统条件-分类: {cat}，可见指标数: {count}")
            if not talib_list or not category_map:
                logger.info("未检测到任何ta-lib指标，请检查ta-lib安装或数据源！")
                return {}
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
            return indicators
        except Exception as e:
            logger.info(f"指标计算错误: {str(e)}")
            return {}

    def _detect_market_regime(self, k, indicators):
        """检测市场状态"""
        try:
            # 获取价格和均线
            close = CLOSE(k)
            ma = indicators.get(
                'ma', MA(CLOSE(k), n=self.get_param("ma_period")))

            # 计算趋势
            trend = (close[-1] - ma[-1]) / ma[-1]

            # 判断市场状态
            if trend > self.get_param("trend_threshold"):
                return "bullish"
            elif trend < -self.get_param("trend_threshold"):
                return "bearish"
            else:
                return "neutral"

        except Exception as e:
            logger.info(f"市场状态检测错误: {str(e)}")
            return "neutral"

    def _calculate_volatility(self, k):
        """计算波动率"""
        try:
            returns = CLOSE(k).pct_change()
            volatility = returns.rolling(
                window=self.get_param("volatility_period")).std()
            return volatility[-1]
        except Exception as e:
            logger.info(f"波动率计算错误: {str(e)}")
            return 0.0

    def _calculate_trend_strength(self, k):
        """计算趋势强度"""
        try:
            ma_short = MA(CLOSE(k), n=self.get_param("ma_period"))
            ma_long = MA(CLOSE(k), n=self.get_param("trend_period"))

            trend = (ma_short[-1] - ma_long[-1]) / ma_long[-1]
            return trend

        except Exception as e:
            logger.info(f"趋势强度计算错误: {str(e)}")
            return 0.0

    def _calculate_volume_ratio(self, k):
        """计算成交量比率"""
        try:
            volume = VOL(k)
            volume_ma = MA(volume, n=self.get_param("volume_ma_period"))
            return volume[-1] / volume_ma[-1]
        except Exception as e:
            logger.info(f"成交量比率计算错误: {str(e)}")
            return 0.0

    def _make_decision(self, k, indicators):
        """综合判断系统是否有效"""
        try:
            # 1. 检查市场状态
            if self.market_regime == "bearish" and self.trend_strength < -self.get_param("trend_threshold"):
                return False

            # 2. 检查波动率
            if self.volatility > self.get_param("volatility_threshold"):
                return False

            # 3. 检查成交量
            if self.volume_ratio < self.get_param("volume_ratio"):
                return False

            # 4. 检查技术指标
            macd = indicators.get('macd', MACD(CLOSE(k)))
            rsi = indicators.get('rsi', RSI(CLOSE(k)))

            # MACD在零轴下方
            if macd.diff[-1] < 0 and macd.dea[-1] < 0:
                return False

            # RSI超买
            if rsi[-1] > 70:
                return False

            # 5. 如果启用机器学习，使用模型预测
            if self.get_param("enable_ml") and self.get_param("ml_model_path"):
                if not self._ml_predict(k, indicators):
                    return False

            return True

        except Exception as e:
            logger.info(f"综合判断错误: {str(e)}")
            return False

    def _ml_predict(self, k, indicators):
        """使用机器学习模型预测"""
        try:
            # 准备特征数据
            features = self._prepare_ml_features(k, indicators)

            # 加载模型并预测
            import joblib
            model = joblib.load(self.get_param("ml_model_path"))
            prediction = model.predict(features)

            return prediction[0] > 0.5

        except Exception as e:
            logger.info(f"机器学习预测错误: {str(e)}")
            return False

    def _prepare_ml_features(self, k, indicators):
        """准备机器学习特征"""
        try:
            features = []

            # 添加价格特征
            features.append(CLOSE(k)[-1])
            features.append(CLOSE(k)[-1] / CLOSE(k)[-2] - 1)  # 收益率

            # 添加技术指标特征
            ma = indicators.get(
                'ma', MA(CLOSE(k), n=self.get_param("ma_period")))
            features.append(ma[-1])
            features.append(CLOSE(k)[-1] / ma[-1] - 1)  # 价格偏离度

            macd = indicators.get('macd', MACD(CLOSE(k)))
            features.append(macd.diff[-1])
            features.append(macd.dea[-1])

            rsi = indicators.get('rsi', RSI(CLOSE(k)))
            features.append(rsi[-1])

            # 添加成交量特征
            features.append(VOL(k)[-1])
            features.append(self.volume_ratio)

            # 添加波动率特征
            features.append(self.volatility)

            # 添加趋势特征
            features.append(self.trend_strength)

            return np.array(features).reshape(1, -1)

        except Exception as e:
            logger.info(f"特征准备错误: {str(e)}")
            return None

def get_indicator_categories():
    """获取所有指标分类及其指标列表，确保与ta-lib分类一致"""
    # 已替换为新的导入
    return get_all_indicators_by_category()
