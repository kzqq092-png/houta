"""
交易控件模块
"""
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                           QLabel, QLineEdit, QComboBox, QPushButton,
                           QSpinBox, QDoubleSpinBox, QTableWidget,
                           QTableWidgetItem, QGroupBox, QFormLayout, QTextEdit)
from PyQt5.QtCore import pyqtSignal, Qt
import traceback

from core.logger import LogManager
from utils.theme import get_theme_manager
from core.trading_system import trading_system
from utils.config_manager import ConfigManager

class TradingWidget(QWidget):
    """交易控件类"""
    
    # 定义信号
    strategy_changed = pyqtSignal(str)  # 策略变更信号
    trade_executed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化交易控件
        
        Args:
            config_manager: Optional ConfigManager instance to use
        """
        super().__init__()
        
        try:
            # 初始化变量
            self.current_stock = None
            self.current_signals = []
            self.current_positions = []
            
            # 初始化日志管理器
            self.log_manager = LogManager()
            
            # 初始化UI
            self.init_ui()
            
            # 连接信号
            self.connect_signals()
            
            # 应用主题
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = get_theme_manager(self.config_manager)
            self.theme_manager.apply_theme(self)
            
            self.log_manager.info("交易控件初始化完成")
            
        except Exception as e:
            error_msg = f"初始化交易控件失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def init_ui(self):
        """初始化UI"""
        try:
            layout = QVBoxLayout(self)
            
            # 创建策略选择组
            strategy_group = QGroupBox("交易策略")
            strategy_layout = QVBoxLayout(strategy_group)
            
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略",
                "KDJ策略", "自定义策略"
            ])
            strategy_layout.addWidget(self.strategy_combo)
            
            # 创建参数设置组
            params_group = QGroupBox("参数设置")
            params_layout = QFormLayout(params_group)
            
            # 添加参数控件
            self.param_controls = {}
            
            # 创建交易按钮
            buttons_layout = QHBoxLayout()
            
            self.buy_button = QPushButton("买入")
            self.buy_button.clicked.connect(self.execute_buy)
            buttons_layout.addWidget(self.buy_button)
            
            self.sell_button = QPushButton("卖出")
            self.sell_button.clicked.connect(self.execute_sell)
            buttons_layout.addWidget(self.sell_button)
            
            self.cancel_button = QPushButton("撤单")
            self.cancel_button.clicked.connect(self.cancel_order)
            buttons_layout.addWidget(self.cancel_button)
            
            # 添加到布局
            layout.addWidget(strategy_group)
            layout.addWidget(params_group)
            layout.addLayout(buttons_layout)
            
            # 创建持仓信息表格
            self.position_table = QTableWidget()
            self.position_table.setColumnCount(6)
            self.position_table.setHorizontalHeaderLabels([
                "股票代码", "股票名称", "持仓数量", "持仓成本", "当前价格", "盈亏比例"
            ])
            layout.addWidget(self.position_table)
            
            # 创建交易记录表格
            self.trade_table = QTableWidget()
            self.trade_table.setColumnCount(7)
            self.trade_table.setHorizontalHeaderLabels([
                "时间", "股票代码", "交易类型", "成交价格", "成交数量", "成交金额", "手续费"
            ])
            layout.addWidget(self.trade_table)
            
            self.log_manager.info("交易控件UI初始化完成")
            
        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def connect_signals(self):
        """连接信号"""
        try:
            # 连接策略选择信号
            self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
            
            # 连接按钮信号
            self.buy_button.clicked.connect(self.execute_buy)
            self.sell_button.clicked.connect(self.execute_sell)
            self.cancel_button.clicked.connect(self.cancel_order)
            
            self.log_manager.info("信号连接完成")
            
        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def execute_buy(self):
        """执行买入操作"""
        try:
            # TODO: 实现买入逻辑
            pass
            
        except Exception as e:
            error_msg = f"买入操作失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def execute_sell(self):
        """执行卖出操作"""
        try:
            # TODO: 实现卖出逻辑
            pass
            
        except Exception as e:
            error_msg = f"卖出操作失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def cancel_order(self):
        """撤销订单"""
        try:
            # TODO: 实现撤单逻辑
            pass
            
        except Exception as e:
            error_msg = f"撤单操作失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
            
    def update_stock(self, stock_info: Dict[str, str]):
        """更新股票信息
        
        Args:
            stock_info: 股票信息字典
        """
        try:
            self.current_stock = stock_info
            
            # 清除现有数据
            self.clear_data()
            
            # 重新计算信号
            self.calculate_signals()
            
        except Exception as e:
            LogManager.log(f"更新股票信息失败: {str(e)}", "error")
            
    def update_signals(self, signals: List[Dict[str, Any]]):
        """更新信号列表
        
        Args:
            signals: 信号列表
        """
        try:
            self.current_signals = signals
            
            # 清空信号表格
            self.signal_table.setRowCount(0)
            
            # 添加信号数据
            for signal in signals:
                row = self.signal_table.rowCount()
                self.signal_table.insertRow(row)
                
                self.signal_table.setItem(
                    row, 0,
                    QTableWidgetItem(signal['time'].strftime('%Y-%m-%d'))
                )
                self.signal_table.setItem(
                    row, 1,
                    QTableWidgetItem(signal['type'])
                )
                self.signal_table.setItem(
                    row, 2,
                    QTableWidgetItem(signal['signal'])
                )
                self.signal_table.setItem(
                    row, 3,
                    QTableWidgetItem(f"{signal['price']:.2f}")
                )
                self.signal_table.setItem(
                    row, 4,
                    QTableWidgetItem(f"{signal['strength']:.4f}")
                )
                
            # 调整列宽
            self.signal_table.resizeColumnsToContents()
            
        except Exception as e:
            LogManager.log(f"更新信号列表失败: {str(e)}", "error")
            
    def update_backtest_results(self, results: Dict[str, Any]):
        """更新回测结果
        
        Args:
            results: 回测结果字典
        """
        try:
            # 更新绩效指标
            self.performance_table.setRowCount(0)
            for name, value in results['performance'].items():
                row = self.performance_table.rowCount()
                self.performance_table.insertRow(row)
                
                self.performance_table.setItem(
                    row, 0,
                    QTableWidgetItem(name)
                )
                self.performance_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"{value:.2%}")
                )
                
            # 更新风险指标
            self.risk_table.setRowCount(0)
            for name, value in results['risk'].items():
                row = self.risk_table.rowCount()
                self.risk_table.insertRow(row)
                
                self.risk_table.setItem(
                    row, 0,
                    QTableWidgetItem(name)
                )
                self.risk_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"{value:.4f}")
                )
                
            # 更新交易记录
            self.trade_table.setRowCount(0)
            for trade in results['trades']:
                row = self.trade_table.rowCount()
                self.trade_table.insertRow(row)
                
                self.trade_table.setItem(
                    row, 0,
                    QTableWidgetItem(trade['time'].strftime('%Y-%m-%d'))
                )
                self.trade_table.setItem(
                    row, 1,
                    QTableWidgetItem(trade['stock'])
                )
                self.trade_table.setItem(
                    row, 2,
                    QTableWidgetItem(trade['business'])
                )
                self.trade_table.setItem(
                    row, 3,
                    QTableWidgetItem(f"{trade['price']:.2f}")
                )
                self.trade_table.setItem(
                    row, 4,
                    QTableWidgetItem(str(trade['quantity']))
                )
                self.trade_table.setItem(
                    row, 5,
                    QTableWidgetItem(f"{trade['cost']:.2f}")
                )
                self.trade_table.setItem(
                    row, 6,
                    QTableWidgetItem(f"{trade['cash']:.2f}")
                )
                
            # 更新持仓信息
            self.position_table.setRowCount(0)
            for pos in results['positions']:
                row = self.position_table.rowCount()
                self.position_table.insertRow(row)
                
                self.position_table.setItem(
                    row, 0,
                    QTableWidgetItem(pos['stock'])
                )
                self.position_table.setItem(
                    row, 1,
                    QTableWidgetItem(str(pos['quantity']))
                )
                self.position_table.setItem(
                    row, 2,
                    QTableWidgetItem(f"{pos['cost']:.2f}")
                )
                self.position_table.setItem(
                    row, 3,
                    QTableWidgetItem(f"{pos['price']:.2f}")
                )
                self.position_table.setItem(
                    row, 4,
                    QTableWidgetItem(f"{pos['profit']:.2f}")
                )
                self.position_table.setItem(
                    row, 5,
                    QTableWidgetItem(f"{pos['stoploss']:.2f}")
                )
                
            # 调整列宽
            self.performance_table.resizeColumnsToContents()
            self.risk_table.resizeColumnsToContents()
            self.trade_table.resizeColumnsToContents()
            self.position_table.resizeColumnsToContents()
            
        except Exception as e:
            LogManager.log(f"更新回测结果失败: {str(e)}", "error")
            
    def clear_data(self):
        """清除数据"""
        try:
            self.signal_table.setRowCount(0)
            self.performance_table.setRowCount(0)
            self.risk_table.setRowCount(0)
            self.trade_table.setRowCount(0)
            self.position_table.setRowCount(0)
            
            self.current_signals = []
            self.current_positions = []
            
        except Exception as e:
            LogManager.log(f"清除数据失败: {str(e)}", "error")
            
    def calculate_signals(self):
        """计算交易信号"""
        try:
            if not self.current_stock:
                return
                
            # 获取当前策略
            strategy = self.strategy_combo.currentText()
            
            # 计算信号
            signals = trading_system.calculate_signals(strategy)
            
            # 更新信号列表
            self.update_signals(signals)
            
        except Exception as e:
            LogManager.log(f"计算交易信号失败: {str(e)}", "error")
            
    def run_backtest(self):
        """运行回测"""
        try:
            if not self.current_stock:
                return
                
            # 获取回测参数
            params = {
                'strategy': self.strategy_combo.currentText(),
                'initial_cash': self.initial_cash_spin.value(),
                'commission_rate': self.commission_spin.value(),
                'slippage': self.slippage_spin.value(),
                'ma_short': self.ma_short_spin.value(),
                'ma_long': self.ma_long_spin.value(),
                'macd_short': self.macd_short_spin.value(),
                'macd_long': self.macd_long_spin.value(),
                'macd_signal': self.macd_signal_spin.value(),
                'kdj_n': self.kdj_n_spin.value(),
                'kdj_m1': self.kdj_m1_spin.value(),
                'kdj_m2': self.kdj_m2_spin.value()
            }
            
            # 运行回测
            results = trading_system.run_backtest(params)
            
            # 更新回测结果
            self.update_backtest_results(results)
            
        except Exception as e:
            LogManager.log(f"运行回测失败: {str(e)}", "error")
            
    def reset_params(self):
        """重置参数"""
        try:
            # 重置策略参数
            self.ma_short_spin.setValue(5)
            self.ma_long_spin.setValue(10)
            self.macd_short_spin.setValue(12)
            self.macd_long_spin.setValue(26)
            self.macd_signal_spin.setValue(9)
            self.kdj_n_spin.setValue(9)
            self.kdj_m1_spin.setValue(3)
            self.kdj_m2_spin.setValue(3)
            
            # 重置回测参数
            self.initial_cash_spin.setValue(100000.0)
            self.commission_spin.setValue(0.0003)
            self.slippage_spin.setValue(0.0001)
            
        except Exception as e:
            LogManager.log(f"重置参数失败: {str(e)}", "error")
            
    def on_strategy_changed(self, strategy: str):
        """处理策略变更事件
        
        Args:
            strategy: 策略名称
        """
        try:
            self.strategy_changed.emit(strategy)
            self.calculate_signals()
            
        except Exception as e:
            LogManager.log(f"处理策略变更失败: {str(e)}", "error") 