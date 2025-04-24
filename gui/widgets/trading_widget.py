"""
交易控件模块
"""
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                           QLabel, QLineEdit, QComboBox, QPushButton,
                           QSpinBox, QDoubleSpinBox, QTableWidget,
                           QTableWidgetItem, QGroupBox, QFormLayout, QTextEdit)
from PyQt5.QtCore import pyqtSignal, Qt

from core.logger import LogManager
from utils.theme import get_theme_manager
from core.trading_system import trading_system
from utils.config_manager import ConfigManager

class TradingWidget(QWidget):
    """交易控件类"""
    
    # 定义信号
    strategy_changed = pyqtSignal(str)  # 策略变更信号
    trade_executed = pyqtSignal(dict)
    
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
            
            # 初始化UI
            self.init_ui()
            
            # 应用主题
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = get_theme_manager(self.config_manager)
            self.theme_manager.apply_theme(self)
            
        except Exception as e:
            LogManager.log(f"初始化交易控件失败: {str(e)}", "error")
            raise
            
    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            
            # 创建标签页
            tab_widget = QTabWidget()
            
            # 添加策略标签页
            strategy_tab = self.create_strategy_tab()
            tab_widget.addTab(strategy_tab, "策略")
            
            # 添加回测标签页
            backtest_tab = self.create_backtest_tab()
            tab_widget.addTab(backtest_tab, "回测")
            
            # 添加持仓标签页
            position_tab = self.create_position_tab()
            tab_widget.addTab(position_tab, "持仓")
            
            # 添加交易记录标签页
            trade_tab = self.create_trade_tab()
            tab_widget.addTab(trade_tab, "交易记录")
            
            # 添加标签页到布局
            layout.addWidget(tab_widget)
            
        except Exception as e:
            LogManager.log(f"初始化交易控件UI失败: {str(e)}", "error")
            raise
            
    def create_strategy_tab(self) -> QWidget:
        """创建策略标签页
        
        Returns:
            策略标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # 创建策略选择组
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QFormLayout()
            
            # 添加策略选择
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems(['MA', 'MACD', 'KDJ'])
            self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
            strategy_layout.addRow("策略:", self.strategy_combo)
            
            # 添加MA参数
            ma_layout = QHBoxLayout()
            self.ma_short_spin = QSpinBox()
            self.ma_short_spin.setRange(1, 120)
            ma_layout.addWidget(QLabel("短期:"))
            ma_layout.addWidget(self.ma_short_spin)
            
            self.ma_long_spin = QSpinBox()
            self.ma_long_spin.setRange(1, 250)
            ma_layout.addWidget(QLabel("长期:"))
            ma_layout.addWidget(self.ma_long_spin)
            strategy_layout.addRow("MA:", ma_layout)
            
            # 添加MACD参数
            macd_layout = QHBoxLayout()
            self.macd_short_spin = QSpinBox()
            self.macd_short_spin.setRange(1, 120)
            macd_layout.addWidget(QLabel("快线:"))
            macd_layout.addWidget(self.macd_short_spin)
            
            self.macd_long_spin = QSpinBox()
            self.macd_long_spin.setRange(1, 250)
            macd_layout.addWidget(QLabel("慢线:"))
            macd_layout.addWidget(self.macd_long_spin)
            
            self.macd_signal_spin = QSpinBox()
            self.macd_signal_spin.setRange(1, 120)
            macd_layout.addWidget(QLabel("信号:"))
            macd_layout.addWidget(self.macd_signal_spin)
            strategy_layout.addRow("MACD:", macd_layout)
            
            # 添加KDJ参数
            kdj_layout = QHBoxLayout()
            self.kdj_n_spin = QSpinBox()
            self.kdj_n_spin.setRange(1, 90)
            kdj_layout.addWidget(QLabel("N:"))
            kdj_layout.addWidget(self.kdj_n_spin)
            
            self.kdj_m1_spin = QSpinBox()
            self.kdj_m1_spin.setRange(1, 30)
            self.kdj_m1_spin.setValue(3)
            strategy_layout.addRow("KDJ M1:", self.kdj_m1_spin)
            
            self.kdj_m2_spin = QSpinBox()
            self.kdj_m2_spin.setRange(1, 30)
            self.kdj_m2_spin.setValue(3)
            strategy_layout.addRow("KDJ M2:", self.kdj_m2_spin)
            
            strategy_group.setLayout(strategy_layout)
            layout.addWidget(strategy_group)
            
            # 创建信号列表组
            signal_group = QGroupBox("信号列表")
            signal_layout = QVBoxLayout()
            
            self.signal_table = QTableWidget()
            self.signal_table.setColumnCount(5)
            self.signal_table.setHorizontalHeaderLabels([
                "时间", "类型", "信号", "价格", "强度"
            ])
            signal_layout.addWidget(self.signal_table)
            
            signal_group.setLayout(signal_layout)
            layout.addWidget(signal_group)
            
            return widget
            
        except Exception as e:
            LogManager.log(f"创建策略标签页失败: {str(e)}", "error")
            raise
            
    def create_backtest_tab(self) -> QWidget:
        """创建回测标签页
        
        Returns:
            回测标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # 创建参数设置组
            param_group = QGroupBox("参数设置")
            param_layout = QFormLayout()
            
            # 添加初始资金
            self.initial_cash_spin = QDoubleSpinBox()
            self.initial_cash_spin.setDecimals(2)
            self.initial_cash_spin.setRange(1000.0, 10000000.0)
            self.initial_cash_spin.setValue(100000.0)
            self.initial_cash_spin.setSingleStep(1000.0)
            self.initial_cash_spin.setSuffix(" 元")
            param_layout.addRow("初始资金:", self.initial_cash_spin)
            
            # 添加手续费率
            self.commission_spin = QDoubleSpinBox()
            self.commission_spin.setDecimals(4)
            self.commission_spin.setRange(0.0, 0.01)
            self.commission_spin.setValue(0.0003)
            self.commission_spin.setSingleStep(0.0001)
            self.commission_spin.setSuffix(" %")
            param_layout.addRow("手续费率:", self.commission_spin)
            
            # 添加滑点率
            self.slippage_spin = QDoubleSpinBox()
            self.slippage_spin.setDecimals(4)
            self.slippage_spin.setRange(0.0, 0.01)
            self.slippage_spin.setValue(0.0001)
            self.slippage_spin.setSingleStep(0.0001)
            self.slippage_spin.setSuffix(" %")
            param_layout.addRow("滑点率:", self.slippage_spin)
            
            param_group.setLayout(param_layout)
            layout.addWidget(param_group)
            
            # 创建回测结果组
            result_group = QGroupBox("回测结果")
            result_layout = QVBoxLayout()
            
            # 添加绩效指标表格
            self.performance_table = QTableWidget()
            self.performance_table.setColumnCount(2)
            self.performance_table.setHorizontalHeaderLabels(["指标", "值"])
            result_layout.addWidget(self.performance_table)
            
            # 添加风险指标表格
            self.risk_table = QTableWidget()
            self.risk_table.setColumnCount(2)
            self.risk_table.setHorizontalHeaderLabels(["指标", "值"])
            result_layout.addWidget(self.risk_table)
            
            result_group.setLayout(result_layout)
            layout.addWidget(result_group)
            
            # 添加按钮
            button_layout = QHBoxLayout()
            
            run_button = QPushButton("运行回测")
            run_button.clicked.connect(self.run_backtest)
            button_layout.addWidget(run_button)
            
            reset_button = QPushButton("重置参数")
            reset_button.clicked.connect(self.reset_params)
            button_layout.addWidget(reset_button)
            
            layout.addLayout(button_layout)
            
            return widget
            
        except Exception as e:
            LogManager.log(f"创建回测标签页失败: {str(e)}", "error")
            raise
            
    def create_position_tab(self) -> QWidget:
        """创建持仓标签页
        
        Returns:
            持仓标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # 创建持仓列表
            self.position_table = QTableWidget()
            self.position_table.setColumnCount(6)
            self.position_table.setHorizontalHeaderLabels([
                "股票", "数量", "成本", "现价", "盈亏", "止损价"
            ])
            layout.addWidget(self.position_table)
            
            return widget
            
        except Exception as e:
            LogManager.log(f"创建持仓标签页失败: {str(e)}", "error")
            raise
            
    def create_trade_tab(self) -> QWidget:
        """创建交易记录标签页
        
        Returns:
            交易记录标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # 创建交易记录列表
            self.trade_table = QTableWidget()
            self.trade_table.setColumnCount(7)
            self.trade_table.setHorizontalHeaderLabels([
                "时间", "股票", "方向", "价格", "数量", "成本", "剩余资金"
            ])
            layout.addWidget(self.trade_table)
            
            return widget
            
        except Exception as e:
            LogManager.log(f"创建交易记录标签页失败: {str(e)}", "error")
            raise
            
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