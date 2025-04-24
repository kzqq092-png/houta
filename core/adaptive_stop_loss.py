from hikyuu.trade_sys import StoplossBase
from hikyuu import KData, KQuery, MA, REF, ABS, MAX, MIN, CLOSE, HIGH, LOW

class AdaptiveStopLoss(StoplossBase):
    """自适应止损系统"""
    
    def __init__(self, params=None):
        super().__init__()
        self._params = params or {}
        self._atr_period = self._params.get('atr_period', 14)
        self._atr_multiplier = self._params.get('atr_multiplier', 2.0)
        self._volatility_factor = self._params.get('volatility_factor', 0.5)
        self._trend_factor = self._params.get('trend_factor', 0.3)
        self._market_factor = self._params.get('market_factor', 0.2)
        self._min_stop_loss = self._params.get('min_stop_loss', 0.02)
        self._max_stop_loss = self._params.get('max_stop_loss', 0.1)
        self._fixed_stop_loss = self._params.get('fixed_stop_loss', 0.05)
        
    def _clone(self):
        return self.__class__(self._params)
        
    def _calculate(self, kdata):
        """计算止损价格"""
        if len(kdata) < self._atr_period:
            return 0.0
            
        # 计算ATR
        tr = MAX(MAX(HIGH(kdata) - LOW(kdata), 
                     ABS(HIGH(kdata) - REF(CLOSE(kdata), 1))),
                 ABS(LOW(kdata) - REF(CLOSE(kdata), 1)))
        atr = MA(tr, self._atr_period)
        
        # 计算动态止损
        dynamic_stop = self._atr_multiplier * atr[-1]
        
        # 计算波动率因子
        volatility = (HIGH(kdata) - LOW(kdata)) / CLOSE(kdata)
        volatility_factor = MA(volatility, self._atr_period)[-1]
        
        # 计算趋势因子
        ma = MA(CLOSE(kdata), 20)
        trend = (CLOSE(kdata) - ma) / ma
        trend_factor = trend[-1]
        
        # 计算市场因子
        market = (CLOSE(kdata) - REF(CLOSE(kdata), 1)) / REF(CLOSE(kdata), 1)
        market_factor = MA(market, 5)[-1]
        
        # 综合计算止损价格
        stop_price = CLOSE(kdata)[-1] - dynamic_stop * (
            1 + self._volatility_factor * volatility_factor +
            self._trend_factor * trend_factor +
            self._market_factor * market_factor
        )
        
        # 确保止损价格在合理范围内
        min_price = CLOSE(kdata)[-1] * (1 - self._max_stop_loss)
        max_price = CLOSE(kdata)[-1] * (1 - self._min_stop_loss)
        stop_price = MAX(MIN(stop_price, max_price), min_price)
        
        return stop_price 