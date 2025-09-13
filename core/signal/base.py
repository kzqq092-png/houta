from hikyuu import *
from hikyuu.trade_sys import SignalBase
from hikyuu.indicator import MA, MACD, RSI, KDJ, CLOSE, VOL, OPEN, HIGH, LOW
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from core.data_manager import data_manager


from core.indicator_adapter import calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci
from core.indicator_service import calculate_indicator, get_indicator_metadata, get_all_indicators_metadata
from loguru import logger


class BaseSignal(SignalBase):
    """信号系统基类"""

    def __init__(self, name: str = "BaseSignal"):
        super(BaseSignal, self).__init__(name)
        self._params = {}
        self._cache = {}

    def _clone(self):
        """克隆方法"""
        return BaseSignal(name=self.name)

    def _calculate(self, k):
        """
        计算方法，生成买入卖出信号，自动兼容DataFrame和KData。
        DataFrame转KData必须通过core.data_manager.data_manager.df_to_kdata唯一入口，禁止自行实例化DataManager。
        """
        try:
            if isinstance(k, pd.DataFrame):
                k = data_manager.df_to_kdata(k)
            if k is None or len(k) == 0:
                logger.info("信号计算收到空KData，直接返回")
                return
            # 计算基础指标
            indicators = self._calculate_indicators(k)
            # 生成信号
            signals = self._generate_signals(k, indicators)
            # 记录信号
            self._record_signals(k, signals)
        except Exception as e:
            logger.info(f"信号计算错误: {str(e)}")
            return

    def _calculate_indicators(self, k) -> Dict[str, Any]:
        """计算技术指标"""
        indicators = {}
        if hasattr(k, 'to_df'):
            df = k.to_df()
            if isinstance(df['close'], pd.Series):
                # 已替换为新的导入
                indicators['ma_fast'] = calc_ma(
                    df['close'], self.get_param("n_fast", 12))
                indicators['ma_slow'] = calc_ma(
                    df['close'], self.get_param("n_slow", 26))
                macd, _, _ = calc_macd(df['close'], self.get_param(
                    "n_fast", 12), self.get_param("n_slow", 26), self.get_param("n_signal", 9))
                indicators['macd'] = macd
                indicators['rsi'] = calc_rsi(
                    df['close'], self.get_param("rsi_window", 14))
                # KDJ等同理
            else:
                from hikyuu.indicator import MA, MACD, RSI, KDJ
                close_ind = CLOSE(k)
                indicators['ma_fast'] = MA(
                    close_ind, n=self.get_param("n_fast", 12))
                indicators['ma_slow'] = MA(
                    close_ind, n=self.get_param("n_slow", 26))
                indicators['macd'] = MACD(close_ind, n1=self.get_param("n_fast", 12),
                                          n2=self.get_param("n_slow", 26), n3=self.get_param("n_signal", 9))
                indicators['rsi'] = RSI(
                    close_ind, n=self.get_param("rsi_window", 14))
                indicators['kdj'] = KDJ(k, n=self.get_param("kdj_n", 9))
        else:
            # 兼容性兜底
            indicators['ma_fast'] = None
            indicators['ma_slow'] = None
            indicators['macd'] = None
            indicators['rsi'] = None
            indicators['kdj'] = None
        return indicators

    def _generate_signals(self, k, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """生成交易信号"""
        signals = {
            'buy': [],
            'sell': []
        }

        n = len(k)
        for i in range(1, n):
            # 生成买入信号
            if self._check_buy_signal(k, indicators, i):
                signals['buy'].append(k[i].datetime)

            # 生成卖出信号
            if self._check_sell_signal(k, indicators, i):
                signals['sell'].append(k[i].datetime)

        return signals

    def _check_buy_signal(self, k, indicators: Dict[str, Any], i: int) -> bool:
        """检查买入信号条件"""
        # 默认实现，子类可以重写
        return False

    def _check_sell_signal(self, k, indicators: Dict[str, Any], i: int) -> bool:
        """检查卖出信号条件"""
        # 默认实现，子类可以重写
        return False

    def _record_signals(self, k, signals: Dict[str, Any]):
        """记录信号"""
        for datetime in signals['buy']:
            self.add_buy_signal(datetime)

        for datetime in signals['sell']:
            self.add_sell_signal(datetime)

    def set_param(self, name: str, value: Any):
        """设置参数"""
        self._params[name] = value

    def get_param(self, name: str, default: Any = None) -> Any:
        """获取参数"""
        return self._params.get(name, default)

    def get_params(self) -> Dict[str, Any]:
        """获取所有参数"""
        return self._params.copy()
