import sys
import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal
from typing import Optional
from .logger import LogManager, LogLevel

# Import TradingSystem from the new location
from .trading_system import TradingSystem

# 新建交易控制器（整合原分散的交易控制逻辑）
class TradingController(QObject):
    signal_updated = pyqtSignal(dict)
    log_updated = pyqtSignal(str)
    
    def __init__(self, log_manager: Optional[LogManager] = None):
        super().__init__()
        self.log_manager = log_manager or LogManager()
        self.trading_system = TradingSystem()
        self.current_strategy = None
        self.order_queue = []
        
        # 连接信号
        self.trading_system.signal_updated.connect(self.handle_signal)
        self.trading_system.log_updated.connect(self.handle_log)
        self.trading_system.position_updated.connect(lambda x: self.signal_updated.emit({'type': 'position', 'data': x}))
        self.trading_system.risk_updated.connect(lambda x: self.signal_updated.emit({'type': 'risk', 'data': x}))
        self.trading_system.market_updated.connect(lambda x: self.signal_updated.emit({'type': 'market', 'data': x}))
        self.trading_system.backtest_updated.connect(lambda x: self.signal_updated.emit({'type': 'backtest', 'data': x}))

    def initialize(self):
        """Initialize the trading controller"""
        try:
            self.log_manager.info("Initializing trading controller...")
            # Add initialization code
        except Exception as e:
            self.log_manager.error(f"Failed to initialize trading controller: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up resources"""
        try:
            self.log_manager.info("Cleaning up trading controller...")
            # Add cleanup code
        except Exception as e:
            self.log_manager.error(f"Failed to cleanup trading controller: {str(e)}")

    def handle_signal(self, signal):
        """处理交易信号"""
        # 添加风险控制检查
        if self.check_risk(signal):
            self.order_queue.append(signal)
            self.execute_orders()
            
    def check_risk(self, signal):
        """风险控制检查"""
        # 实现实时风险检查逻辑
        current_risk = self.trading_system.get_current_risk()
        if current_risk['exposure'] > 0.8:
            self.log_updated.emit("风险警告: 仓位超过80%")
            return False
        return True

    def execute_orders(self):
        """执行订单"""
        while self.order_queue:
            order = self.order_queue.pop(0)
            try:
                # 调用交易系统执行订单
                result = self.trading_system.execute_order(order)
                if result['success']:
                    self.signal_updated.emit({'type': 'order', 'data': result})
                else:
                    self.log_updated.emit(result['message'])
            except Exception as e:
                self.log_updated.emit(f"订单执行失败: {str(e)}")

    def handle_log(self, message):
        """处理日志消息"""
        # 转发日志消息
        self.log_updated.emit(message)

    def run_backtest(self, params):
        """运行回测（增强版）"""
        try:
            # 添加参数验证
            if not validate_backtest_params(params):
                raise ValueError("无效的回测参数")
                
            # 确保交易系统已初始化
            if not self.trading_system.initialized:
                self.log_updated.emit("交易系统未初始化，正在初始化...")
                if not self.trading_system.initialize_systems(params):
                    raise ValueError("交易系统初始化失败")
                
            # 获取股票对象
            from hikyuu import Stock
            stock_code = params['stock']  # 现在直接使用stock参数作为代码
            stock = Stock(stock_code)
            
            # 调用交易系统执行回测
            results = self.trading_system.run_backtest(
                stock,
                params['start_date'],
                params['end_date']
            )
            
            # 检查结果是否为None
            if results is None:
                self.log_updated.emit("回测没有产生有效结果")
                return None
                
            # 添加风险指标计算
            try:
                results['risk_metrics'] = self.calculate_risk_metrics(results)
            except Exception as e:
                self.log_updated.emit(f"计算风险指标失败: {str(e)}")
                results['risk_metrics'] = {}
                
            # 发送信号更新UI
            self.signal_updated.emit({'type': 'backtest_complete', 'data': results})
            return results
            
        except Exception as e:
            self.log_updated.emit(f"回测失败: {str(e)}")
            return None

    def calculate_risk_metrics(self, results):
        """计算风险指标（整合原分散的风险计算）"""
        # 实现综合风险指标计算逻辑
        if not results or 'drawdowns' not in results or 'returns' not in results:
            return {
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'var_95': 0
            }
            
        # 检查数据是否为空
        if len(results['drawdowns']) == 0 or len(results['returns']) == 0:
            return {
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'var_95': 0
            }
            
        return {
            'max_drawdown': max(results['drawdowns']),
            'sharpe_ratio': results['returns'].mean() / (results['returns'].std() or 1e-6),  # 避免除零错误
            'var_95': np.percentile(results['returns'], 5)
        }


def validate_backtest_params(params):
    """验证回测参数"""
    required_fields = ['stock', 'start_date', 'end_date']
    
    # 检查必填字段
    for field in required_fields:
        if field not in params:
            return False
            
    # 验证股票代码
    if not params['stock'] or not isinstance(params['stock'], str):
        return False
        
    # 验证日期格式
    try:
        # 这里可以添加日期格式检查的逻辑
        pass
    except:
        return False
        
    return True 