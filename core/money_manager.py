from hikyuu import *
from hikyuu.trade_sys import MoneyManagerBase
from hikyuu.indicator import ATR, CLOSE
import numpy as np
import pandas as pd

class EnhancedMoneyManager(MoneyManagerBase):
    """
    增强的资金管理策略
    """
    def __init__(self, params=None):
        super(EnhancedMoneyManager, self).__init__("EnhancedMoneyManager")
        
        # 设置默认参数
        self.params = {
            "max_position": 0.8,      # 最大仓位比例
            "position_size": 0.2,     # 每次建仓比例
            "risk_per_trade": 0.02,   # 每笔交易风险
            "max_drawdown": 0.2,      # 最大回撤限制
            "max_risk_exposure": 0.3, # 最大风险敞口
            "min_position": 0.1,      # 最小仓位比例
            "atr_period": 14,         # ATR周期
            "atr_multiplier": 2,      # ATR倍数
            "volatility_factor": 0.5, # 波动率因子
            "trend_factor": 0.3,      # 趋势因子
            "market_factor": 0.2,     # 市场因子
            "risk_budget": 0.1,       # 风险预算比例
            "position_scale": 0.1,    # 仓位缩放比例
            "max_positions": 5,       # 最大持仓数量
            "correlation_threshold": 0.7 # 相关性阈值
        }
        
        if params is not None and isinstance(params, dict):
            self.params.update(params)
            
        for key, value in self.params.items():
            self.set_param(key, value)
            
        # 初始化风险跟踪变量
        self.current_risk_exposure = 0
        self.positions = {}  # 跟踪所有持仓
        self.peak_equity = 0
        self.current_drawdown = 0
        self.risk_budget_used = 0
        self.position_count = 0
        self.correlation_matrix = {}  # 跟踪股票相关性

    def _reset(self):
        self.current_risk_exposure = 0
        self.positions = {}
        self.peak_equity = 0
        self.current_drawdown = 0
        self.risk_budget_used = 0
        self.position_count = 0
        
    def _clone(self):
        return EnhancedMoneyManager(params=self.params)
        
    def _calculate_position_size(self, price, stop_loss, available_cash):
        """计算头寸大小"""
        try:
            # 1. 计算基础风险金额
            risk_amount = available_cash * self.get_param("risk_per_trade")
            risk_per_share = price - stop_loss
            
            if risk_per_share <= 0:
                return 0
                
            # 2. 计算基础头寸大小
            base_position_size = int(risk_amount / risk_per_share)
            
            # 3. 应用动态调整因子
            position_scale = self._calculate_position_scale()
            adjusted_size = int(base_position_size * position_scale)
            
            # 4. 确保是100的整数倍
            return (adjusted_size // 100) * 100
            
        except Exception as e:
            print(f"头寸大小计算错误: {str(e)}")
            return 0
            
    def _calculate_position_scale(self):
        """计算仓位缩放因子"""
        try:
            # 1. 基础缩放因子
            scale = 1.0
            
            # 2. 根据回撤调整
            if self.current_drawdown > self.get_param("max_drawdown") * 0.5:
                scale *= 0.5
                
            # 3. 根据风险敞口调整
            if self.current_risk_exposure > self.get_param("max_risk_exposure") * 0.7:
                scale *= 0.7
                
            # 4. 根据风险预算调整
            remaining_budget = self.get_param("risk_budget") - self.risk_budget_used
            if remaining_budget < self.get_param("risk_per_trade"):
                scale *= remaining_budget / self.get_param("risk_per_trade")
                
            # 5. 根据持仓数量调整
            if self.position_count >= self.get_param("max_positions"):
                scale *= 0.5
                
            return max(self.get_param("min_position"), min(scale, 1.0))
            
        except Exception as e:
            print(f"仓位缩放因子计算错误: {str(e)}")
            return 1.0
            
    def _update_risk_metrics(self, datetime):
        """更新风险指标"""
        try:
            # 1. 获取当前权益
            current_equity = self.tm.getFunds(datetime)
            
            # 2. 更新峰值权益
            self.peak_equity = max(self.peak_equity, current_equity)
            
            # 3. 计算当前回撤
            self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
            
            # 4. 计算当前风险敞口
            total_risk = 0
            for stock, position in self.positions.items():
                if position['stop_loss'] > 0:
                    risk = (position['price'] - position['stop_loss']) * position['size']
                    total_risk += risk
            
            self.current_risk_exposure = total_risk / current_equity
            
            # 5. 更新风险预算使用情况
            self.risk_budget_used = self.current_risk_exposure / self.get_param("max_risk_exposure")
            
            # 6. 更新持仓数量
            self.position_count = len(self.positions)
            
        except Exception as e:
            print(f"风险指标更新错误: {str(e)}")
            
    def _check_correlation(self, stk, price):
        """检查相关性"""
        try:
            # 1. 获取历史数据
            k = stk.get_kdata(Query(datetime - 30, datetime))
            if len(k) < 20:
                return True
                
            # 2. 计算相关性
            for existing_stk, position in self.positions.items():
                if existing_stk not in self.correlation_matrix:
                    # 计算相关性并缓存
                    existing_k = existing_stk.get_kdata(Query(datetime - 30, datetime))
                    if len(existing_k) >= 20:
                        correlation = self._calculate_correlation(k, existing_k)
                        self.correlation_matrix[existing_stk] = correlation
                        
                # 检查相关性是否超过阈值
                if self.correlation_matrix.get(existing_stk, 0) > self.get_param("correlation_threshold"):
                    return False
                    
            return True
            
        except Exception as e:
            print(f"相关性检查错误: {str(e)}")
            return True
            
    def _calculate_correlation(self, k1, k2):
        """计算两个股票的相关性"""
        try:
            # 计算收益率
            returns1 = np.diff(CLOSE(k1)) / CLOSE(k1)[:-1]
            returns2 = np.diff(CLOSE(k2)) / CLOSE(k2)[:-1]
            
            # 计算相关性
            return np.corrcoef(returns1, returns2)[0, 1]
            
        except Exception as e:
            print(f"相关性计算错误: {str(e)}")
            return 0.0
        
    def _get_buy_num(self, datetime, stk, price, risk, part_from):
        try:
            # 1. 更新风险指标
            self._update_risk_metrics(datetime)
            
            # 2. 检查风险限制
            if self.current_drawdown > self.get_param("max_drawdown"):
                return 0  # 超过最大回撤限制
                
            if self.current_risk_exposure > self.get_param("max_risk_exposure"):
                return 0  # 超过最大风险敞口
                
            # 3. 检查相关性
            if not self._check_correlation(stk, price):
                return 0  # 相关性过高
                
            # 4. 获取可用资金
            tm = self.tm
            available_cash = tm.current_cash
            total_assets = tm.getFunds(datetime)
            
            # 5. 计算动态仓位比例
            position_ratio = self._calculate_position_scale()
            max_cash = total_assets * position_ratio
            
            # 6. 计算ATR和止损价格
            k = stk.get_kdata(Query(datetime - 30, datetime))
            if len(k) > 0:
                df = k.to_df()
                atr = self._calculate_atr(df)
                stop_loss = price - (atr * self.get_param("atr_multiplier"))
                
                # 7. 计算头寸大小
                position_size = self._calculate_position_size(price, stop_loss, max_cash)
                
                # 8. 记录持仓信息
                if position_size > 0:
                    self.positions[stk.market_code] = {
                        'price': price,
                        'stop_loss': stop_loss,
                        'size': position_size,
                        'datetime': datetime
                    }
                
                return position_size
                
            return 0
            
        except Exception as e:
            print(f"买入数量计算错误: {str(e)}")
            return 0
            
    def _get_sell_num(self, datetime, stk, price, risk, part_from):
        try:
            # 1. 获取持仓
            position = self.tm.get_position(datetime, stk)
            total_num = position.number if position else 0
            
            # 2. 根据信号来源决定卖出数量
            if part_from == System.Part.STOPLOSS:
                # 止损卖出全部
                if stk.market_code in self.positions:
                    del self.positions[stk.market_code]
                return total_num
                
            elif part_from == System.Part.TAKEPROFIT:
                # 止盈可以分批卖出
                sell_ratio = self._calculate_sell_ratio(datetime, stk, price, position)
                sell_num = int(total_num * sell_ratio)
                
                # 更新持仓记录
                if stk.market_code in self.positions:
                    self.positions[stk.market_code]['size'] -= sell_num
                    if self.positions[stk.market_code]['size'] <= 0:
                        del self.positions[stk.market_code]
                        
                return sell_num
                
            elif part_from == System.Part.SIGNAL:
                # 信号卖出，考虑当前市场状况
                if self.current_drawdown > self.get_param("max_drawdown") * 0.7:
                    # 接近最大回撤限制，加快卖出
                    return total_num
                    
                sell_ratio = self._calculate_sell_ratio(datetime, stk, price, position)
                return int(total_num * sell_ratio)
                
            return 0
            
        except Exception as e:
            print(f"卖出数量计算错误: {str(e)}")
            return 0
            
    def _calculate_sell_ratio(self, datetime, stk, price, position):
        """计算卖出比例"""
        try:
            if not position or position.number <= 0:
                return 0
                
            # 1. 计算收益率
            profit_ratio = (price - position.buy_price) / position.buy_price
            
            # 2. 基础卖出比例
            base_ratio = 0.5
            
            # 3. 根据收益调整
            if profit_ratio > 0.1:  # 盈利超过10%
                base_ratio = 0.7
            elif profit_ratio < -0.05:  # 亏损超过5%
                base_ratio = 1.0
                
            # 4. 根据回撤调整
            if self.current_drawdown > self.get_param("max_drawdown") * 0.7:
                base_ratio = min(1.0, base_ratio * 1.5)
                
            # 5. 根据风险敞口调整
            if self.current_risk_exposure > self.get_param("max_risk_exposure") * 0.8:
                base_ratio = min(1.0, base_ratio * 1.2)
                
            return base_ratio
            
        except Exception as e:
            print(f"卖出比例计算错误: {str(e)}")
            return 1.0
            
    def _calculate_atr(self, df):
        """计算ATR"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            return true_range.rolling(self.get_param("atr_period")).mean().iloc[-1]
        except Exception as e:
            print(f"ATR计算错误: {str(e)}")
            return 0.0 