import numpy as np
import pandas as pd
from hikyuu import *
from hikyuu.trade_sys import *
from hikyuu.indicator import *
from utils.trading_utils import calculate_atr
from core.take_profit import AdaptiveTakeProfit
from core.market_environment import MarketEnvironment
from core.system_condition import EnhancedSystemCondition


class ComponentFactory:
    """
    交易系统组件工厂，用于集中创建和管理交易系统的各个组件
    """

    @staticmethod
    def create_signal(params=None):
        """
        创建信号组件

        参数:
            params (dict): 信号参数

        返回:
            SignalBase: 信号组件
        """
        def signal_calculate(k, record):
            try:
                # 获取KData的长度
                n = len(k)
                if n == 0:
                    return

                # 获取参数
                n_fast = params.get('n_fast', 12) if params else 12
                n_slow = params.get('n_slow', 26) if params else 26
                n_signal = params.get('n_signal', 9) if params else 9
                rsi_window = params.get('rsi_window', 14) if params else 14
                rsi_buy_threshold = params.get(
                    'rsi_buy_threshold', 30) if params else 30
                rsi_sell_threshold = params.get(
                    'rsi_sell_threshold', 70) if params else 70

                # 计算指标
                # 移动平均线
                ma_fast = MA(CLOSE(k), n=n_fast)
                ma_slow = MA(CLOSE(k), n=n_slow)

                # MACD
                macd = MACD(CLOSE(k), n1=n_fast, n2=n_slow, n3=n_signal)

                # RSI
                rsi = RSI(CLOSE(k), n=rsi_window)

                # KDJ
                kdj = KDJ(k, n=params.get('kdj_n', 9) if params else 9)

                # 生成信号
                for i in range(1, n):
                    # MACD信号
                    if macd.diff[i] > 0 and macd.diff[i-1] <= 0:
                        record.add_buy_signal(k[i].datetime)
                    elif macd.diff[i] < 0 and macd.diff[i-1] >= 0:
                        record.add_sell_signal(k[i].datetime)

                    # 均线交叉信号
                    if ma_fast[i] > ma_slow[i] and ma_fast[i-1] <= ma_slow[i-1]:
                        record.add_buy_signal(k[i].datetime)
                    elif ma_fast[i] < ma_slow[i] and ma_fast[i-1] >= ma_slow[i-1]:
                        record.add_sell_signal(k[i].datetime)

                    # RSI信号
                    if rsi[i] < rsi_buy_threshold and rsi[i-1] >= rsi_buy_threshold:
                        record.add_buy_signal(k[i].datetime)
                    elif rsi[i] > rsi_sell_threshold and rsi[i-1] <= rsi_sell_threshold:
                        record.add_sell_signal(k[i].datetime)

                    # KDJ信号
                    if kdj.k[i] > kdj.d[i] and kdj.k[i-1] <= kdj.d[i-1]:
                        record.add_buy_signal(k[i].datetime)
                    elif kdj.k[i] < kdj.d[i] and kdj.k[i-1] >= kdj.d[i-1]:
                        record.add_sell_signal(k[i].datetime)

            except Exception as e:
                print(f"信号计算错误: {str(e)}")
                return

        return crtSG(signal_calculate, params=params, name='EnhancedSignal')

    @staticmethod
    def create_money_manager(params=None):
        """
        创建资金管理组件

        参数:
            params (dict): 资金管理参数

        返回:
            MoneyManagerBase: 资金管理组件
        """
        def get_buy_num(tm, datetime, stk, price, risk, part_from):
            try:
                cash = tm.current_cash

                # 计算当前总资产
                total_assets = tm.getFunds(datetime)

                # 计算动态仓位比例
                position_ratio = params.get(
                    'position_size', 0.2) if params else 0.2

                # 计算最大可用资金
                max_cash = total_assets * position_ratio

                # 计算每笔交易的风险金额
                risk_amount = total_assets * \
                    (params.get('risk_per_trade', 0.02) if params else 0.02)

                # 获取ATR值
                k = stk.get_kdata(Query(datetime - 30, datetime))
                if len(k) > 0:
                    df = k.to_df()
                    atr = calculate_atr(df, params.get(
                        'atr_period', 14) if params else 14)

                    # 根据ATR计算止损价格
                    stop_loss = price - \
                        atr.iloc[-1] * \
                        (params.get('atr_multiplier', 2) if params else 2)
                    risk_per_share = price - stop_loss

                    # 计算可买入数量
                    num = int(risk_amount /
                              risk_per_share) if risk_per_share > 0 else 0

                    # 确保不超过最大可用资金
                    max_num = int(max_cash / price)
                    num = min(num, max_num)

                    # 确保是100的整数倍
                    num = (num // 100) * 100

                    return num if num >= 100 else 0

                return 0
            except Exception as e:
                print(f"资金管理买入错误: {str(e)}")
                return 0

        def get_sell_num(tm, datetime, stk, price, risk, part_from):
            try:
                # 获取持仓
                position = tm.get_position(datetime, stk)
                total_num = position.number if position else 0

                # 简化实现: 全部卖出
                return total_num
            except Exception as e:
                print(f"资金管理卖出错误: {str(e)}")
                return 0

        return crtMM(get_buy_num, get_sell_num, params=params, name='EnhancedMoneyManager')

    @staticmethod
    def create_stoploss(params=None):
        """
        创建止损组件

        参数:
            params (dict): 止损参数

        返回:
            StoplossBase: 止损组件
        """
        def stoploss_calculate(datetime, stock, price, risk, part_from):
            try:
                # 获取历史数据
                k = stock.get_kdata(Query(datetime - 30, datetime))
                if len(k) > 0:
                    df = k.to_df()

                    # 计算ATR
                    atr = calculate_atr(df, params.get(
                        'atr_period', 14) if params else 14)

                    # 计算动态止损价格
                    atr_multiplier = params.get(
                        'atr_multiplier', 2) if params else 2

                    # ATR止损
                    dynamic_stop = price - atr.iloc[-1] * atr_multiplier

                    # 固定百分比止损
                    fixed_stop_loss = params.get(
                        'fixed_stop_loss', 0.05) if params else 0.05
                    fixed_stop = price * (1 - fixed_stop_loss)

                    # 使用更保守的止损价格
                    stop_price = max(dynamic_stop, fixed_stop)

                    return stop_price

                return price * (1 - (params.get('fixed_stop_loss', 0.05) if params else 0.05))
            except Exception as e:
                print(f"止损计算错误: {str(e)}")
                return price * (1 - (params.get('fixed_stop_loss', 0.05) if params else 0.05))

        return crtST(stoploss_calculate, params=params, name='EnhancedStoploss')

    @staticmethod
    def create_slippage(params=None):
        """
        创建滑点组件

        参数:
            params (dict): 滑点参数

        返回:
            SlippageBase: 滑点组件
        """
        def get_buy_price(datetime, stock, price, risk, part_from):
            # 买入价上浮
            slip = params.get('slippage', 0.001) if params else 0.001
            return price * (1 + slip)

        def get_sell_price(datetime, stock, price, risk, part_from):
            # 卖出价下浮
            slip = params.get('slippage', 0.001) if params else 0.001
            return price * (1 - slip)

        return crtSP(get_buy_price, get_sell_price, params=params, name='EnhancedSlippage')

    @staticmethod
    def create_environment(params=None):
        """
        创建市场环境组件
        """
        return MarketEnvironment(params)

    @staticmethod
    def create_condition(params=None):
        """
        创建系统有效条件组件
        """
        return EnhancedSystemCondition(params)

    @staticmethod
    def create_trade_cost(params=None):
        """
        创建交易成本组件

        参数:
            params (dict): 交易成本参数

        返回:
            TradeCostBase: 交易成本组件
        """
        return TC_FixedA(
            commission=params.get('commission', 0.0003) if params else 0.0003,
            lowest_commission=params.get(
                'lowest_commission', 5.0) if params else 5.0,
            stamptax=params.get('stamptax', 0.001) if params else 0.001,
            transferfee=params.get('transferfee', 0.001) if params else 0.001,
            lowest_transferfee=params.get(
                'lowest_transferfee', 1.0) if params else 1.0
        )

    @staticmethod
    def create_trade_manager(params=None):
        """
        创建交易管理器

        参数:
            params (dict): 交易管理器参数

        返回:
            TradeManager: 交易管理器
        """
        # 创建交易成本算法
        tc = ComponentFactory.create_trade_cost(params)

        # 创建交易管理器
        return crtTM(
            init_cash=params.get(
                'init_cash', 100000.0) if params else 100000.0,
            cost_func=tc,
            name="EnhancedTradeManager"
        )

    @staticmethod
    def create_takeprofit(params=None):
        """
        创建止盈组件
        """
        return AdaptiveTakeProfit(params=params)

    @staticmethod
    def create_system(params=None):
        """
        创建完整的交易系统
        """
        # 创建交易管理器
        tm = ComponentFactory.create_trade_manager(params)

        # 创建各个组件
        mm = ComponentFactory.create_money_manager(params)
        ev = ComponentFactory.create_environment(params)
        cn = ComponentFactory.create_condition(params)
        sg = ComponentFactory.create_signal(params)
        st = ComponentFactory.create_stoploss(params)
        pg = ComponentFactory.create_takeprofit(params)
        sp = ComponentFactory.create_slippage(params)

        # 创建并返回交易系统
        return System(
            tm,      # 交易管理器
            mm,      # 资金管理策略
            ev,      # 市场环境判断策略
            cn,      # 系统有效条件
            sg,      # 信号指示器
            st,      # 止损策略
            pg,      # 止盈策略
            sp,      # 滑点价差算法
            "TradingSystem"  # 系统名称
        )
