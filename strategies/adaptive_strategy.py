from hikyuu import *
from core.stop_loss import AdaptiveStopLoss
from core.take_profit import AdaptiveTakeProfit


def create_adaptive_strategy():
    """创建自适应止损策略"""
    # 创建交易管理对象
    tm = crtTM(init_cash=100000)

    # 创建资金管理策略
    mm = MM_FixedCount(100)

    # 创建信号指示器
    ev = EV_Bool(False)

    # 创建系统有效条件
    cn = CN_Bool(True)

    # 创建止损策略
    sl = AdaptiveStopLoss(params={
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'volatility_factor': 0.5,
        'trend_factor': 0.3,
        'market_factor': 0.2,
        'min_stop_loss': 0.02,
        'max_stop_loss': 0.1,
        'fixed_stop_loss': 0.05
    })

    # 创建盈利目标策略
    pg = AdaptiveTakeProfit(params={
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'ma_period': 20,
        'volatility_period': 20,
        'min_take_profit': 0.05,
        'max_take_profit': 0.2,
        'trailing_profit': 0.03,
        'profit_lock': 0.05,
        'volatility_factor': 0.5,
        'trend_factor': 0.3,
        'market_factor': 0.2
    })

    # 创建滑点算法
    sp = SP_FixedPercent(0.01)

    # 创建系统
    sys = SYS_Simple(tm=tm, mm=mm, ev=ev, cn=cn, sl=sl, pg=pg, sp=sp)

    return sys
