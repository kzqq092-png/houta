from hikyuu import *
from hikyuu.trade_sys import SignalBase
from hikyuu.indicator import MA, MACD, RSI, KDJ, CLOSE, VOL, OPEN, HIGH, LOW, ATR
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

class EnhancedSignal(SignalBase):
    """
    增强的交易信号系统
    """
    def __init__(self, params=None):
        super(EnhancedSignal, self).__init__("EnhancedSignal")
        
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
            "signal_confirm_window": 3, # 信号确认窗口
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
            "volatility_threshold": 1.5 # 波动率阈值
        }
        
        if params is not None and isinstance(params, dict):
            self.params.update(params)
        
        for key, value in self.params.items():
            self.set_param(key, value)
        
        self.signal_history = []  # 用于存储历史信号
        self.last_signal = 0      # 上一个信号
        self.market_regime = "neutral"  # 市场状态
        self.volatility = 0.0     # 市场波动率

    def _clone(self):
        return EnhancedSignal(params=self.params)

    def _calculate(self, k, record):
        try:
            # 1. 计算核心指标
            ma_fast = MA(CLOSE(k), n=self.get_param("n_fast"))
            ma_slow = MA(CLOSE(k), n=self.get_param("n_slow"))
            macd = MACD(CLOSE(k), n1=self.get_param("n_fast"), 
                       n2=self.get_param("n_slow"), 
                       n3=self.get_param("n_signal"))
            rsi = RSI(CLOSE(k), n=self.get_param("rsi_window"))
            volume_ma = MA(VOL(k), n=self.get_param("volume_ma"))
            
            # 2. 计算市场状态和波动率
            self.market_regime = self._detect_market_regime(k, ma_fast, ma_slow)
            self.volatility = self._calculate_volatility(k)
            
            n = len(k)
            for i in range(2, n):
                # 初始化信号强度
                signal_strength = {
                    "trend": 0,
                    "momentum": 0,
                    "volume": 0,
                    "volatility": 0
                }
                
                # 3. 趋势确认
                trend_up = ma_fast[i] > ma_slow[i] and ma_fast[i-1] <= ma_slow[i-1]
                trend_down = ma_fast[i] < ma_slow[i] and ma_fast[i-1] >= ma_slow[i-1]
                
                if trend_up:
                    signal_strength["trend"] += 1
                elif trend_down:
                    signal_strength["trend"] -= 1
                
                # 4. 动量确认
                macd_up = macd[i] > 0 and macd[i-1] <= 0
                macd_down = macd[i] < 0 and macd[i-1] >= 0
                
                if macd_up:
                    signal_strength["momentum"] += 1
                elif macd_down:
                    signal_strength["momentum"] -= 1
                
                # 5. 成交量确认
                volume_confirm = VOL(k)[i] > volume_ma[i] * self.get_param("volume_ratio")
                if volume_confirm:
                    signal_strength["volume"] += 1
                
                # 6. 波动率确认
                if self.volatility > self.get_param("volatility_threshold"):
                    signal_strength["volatility"] -= 1
                
                # 7. 计算综合信号强度
                total_strength = sum(signal_strength.values())
                
                # 8. 根据市场状态调整信号强度
                if self.market_regime == "bullish":
                    total_strength *= 1.2
                elif self.market_regime == "bearish":
                    total_strength *= 0.8
                
                # 9. 生成信号
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
                
                # 10. 清理历史信号
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
            
    def _calculate_volatility(self, k):
        """计算市场波动率"""
        try:
            # 使用ATR计算波动率
            atr = ATR(k, n=self.get_param("atr_period"))
            return atr[-1] / CLOSE(k)[-1]
        except Exception as e:
            print(f"波动率计算错误: {str(e)}")
            return 0.0 

class TradingSystem(QObject):
    """交易系统控制器"""
    # 定义信号
    signal_updated = pyqtSignal(dict)
    position_updated = pyqtSignal(dict)
    risk_updated = pyqtSignal(dict)
    market_updated = pyqtSignal(dict)
    backtest_updated = pyqtSignal(dict)
    log_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.signal_system = None
        self.money_manager = None
        self.risk_monitor = None
        self.current_positions = {}
        
        # 初始化系统组件
        self.initialize_systems()
        
    def initialize_systems(self, signal_params=None, money_params=None):
        """初始化交易系统组件"""
        try:
            # 创建交易管理器
            self.tm = crtTM(init_cash=1000000)
            
            # 创建系统组件
            self.ev = crtEV("EV_Simple")
            self.cn = crtCN("CN_NoLimit")
            
            # 获取默认参数
            money_size = 100 if not money_params or "position_size" not in money_params else money_params["position_size"]
            self.mm = crtMM("MM_FixedCount", money_size)
            
            # 创建信号系统
            try:
                # 使用默认参数创建信号系统
                self.sg = EnhancedSignal(signal_params)
            except Exception as e:
                self.log_updated.emit(f"创建信号系统失败: {str(e)}，使用默认SG_Cross")
                # 使用简单的均线交叉作为备用
                self.sg = crtSG("SG_Cross", MA(n=12), MA(n=26))
            
            # 创建止损和止盈
            self.sp = crtSP("SP_FixedPercent", 0.05)  # 默认5%止损
            self.pg = crtPG("PG_FixedPercent", 0.1)   # 默认10%止盈
            
            # 创建滑点系统
            self.tc = crtTC("TC_Zero")
            
            # 创建交易系统
            self.sys = crtSYS("SYS_Simple", self.tm, self.mm, self.ev, 
                            self.cn, self.sg, self.sp, self.pg, self.tc)
            
            if not self.sys:
                raise ValueError("交易系统创建失败")
                
            self.log_updated.emit("交易系统初始化完成")
            return True
            
        except Exception as e:
            self.log_updated.emit(f"系统初始化错误: {str(e)}")
            return False
    
    def run_backtest(self, stock, start_date, end_date):
        """运行回测"""
        try:
            if not self.sys:
                raise ValueError("交易系统未初始化")
                
            # 创建查询对象
            query = Query(start_date, end_date, Query.DAY)
            
            # 获取K线数据
            if isinstance(stock, dict):
                # 如果传入字典，需要获取实际的股票对象
                stock_code = stock.get('code', '')
                stock_obj = sm[stock_code]
                if stock_obj is None:
                    raise ValueError(f"无法获取股票: {stock_code}")
                stock = stock_obj
                
            kdata = stock.get_kdata(query)
            if not kdata or len(kdata) == 0:
                raise ValueError(f"无法获取K线数据或数据为空: {stock.code}")
                
            # 运行回测
            self.sys.run(kdata)
            
            # 处理回测结果
            trades = self.tm.getTradeList()
            funds_list = self.tm.getFundsList()
            
            # 计算回撤序列
            equity_curve = [fund.value for fund in funds_list]
            dates = [fund.datetime for fund in funds_list]
            
            if len(equity_curve) > 1:
                returns = np.diff(equity_curve) / equity_curve[:-1]
                running_max = np.maximum.accumulate(equity_curve)
                drawdowns = (equity_curve - running_max) / running_max
            else:
                returns = np.array([])
                drawdowns = np.array([])
            
            # 获取回测结果
            results = {
                'kdata': kdata,
                'tm': self.tm,
                'sys': self.sys,
                'trades': trades,
                'equity_curve': equity_curve,
                'dates': dates,
                'returns': returns,
                'drawdowns': drawdowns
            }
            
            self.backtest_updated.emit(results)
            return results
            
        except Exception as e:
            self.log_updated.emit(f"回测运行错误: {str(e)}")
            return None
    
    def get_current_risk(self):
        """获取当前风险状态"""
        return {
            'exposure': 0.5,  # 示例值，实际应该根据持仓计算
            'volatility': 0.02,
            'drawdown': 0.03
        }
        
    def execute_order(self, order):
        """执行订单"""
        # 这里实现订单执行逻辑
        return {
            'status': 'success',
            'order_id': 'order123',
            'price': order.get('price', 0),
            'quantity': order.get('quantity', 0)
        } 