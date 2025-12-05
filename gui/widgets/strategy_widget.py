#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略执行UI组件

功能：
1. 显示所有可用策略
2. 配置策略参数
3. 执行策略并显示结果
4. 策略回测功能

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox,
    QDoubleSpinBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QSplitter, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from loguru import logger
import pandas as pd
from typing import List, Dict, Any

from strategies.strategy_manager import get_strategy_manager


class StrategyWidget(QWidget):
    """策略执行UI组件"""

    strategy_executed = pyqtSignal(dict)  # 策略执行完成信号

    def __init__(self, parent=None):
        """初始化策略组件"""
        super().__init__(parent)

        # 获取策略管理器
        self.strategy_manager = get_strategy_manager()

        # 当前选中的策略
        self.current_strategy_id = None

        # 初始化UI
        self._init_ui()

        # 加载策略列表
        self._load_strategies()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)

        # 策略选择和配置区域
        config_widget = self._create_config_widget()
        splitter.addWidget(config_widget)

        # 结果显示区域
        results_widget = self._create_results_widget()
        splitter.addWidget(results_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        layout.addWidget(splitter)

    def _create_config_widget(self) -> QWidget:
        """创建配置区域"""
        widget = QGroupBox("策略配置")
        layout = QVBoxLayout()

        # 策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("选择策略:"))

        self.strategy_combo = QComboBox()
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)

        strategy_layout.addStretch()
        layout.addLayout(strategy_layout)

        # 策略描述
        self.strategy_desc_label = QLabel("")
        self.strategy_desc_label.setWordWrap(True)
        self.strategy_desc_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.strategy_desc_label)

        # 股票列表输入
        stocks_layout = QHBoxLayout()
        stocks_layout.addWidget(QLabel("股票列表:"))

        self.stocks_input = QLineEdit()
        self.stocks_input.setPlaceholderText("例如: 000001,600519,000858")
        stocks_layout.addWidget(self.stocks_input)

        layout.addLayout(stocks_layout)

        # 策略参数区域
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        layout.addWidget(self.params_widget)

        # 执行按钮
        button_layout = QHBoxLayout()

        self.execute_btn = QPushButton("执行策略")
        self.execute_btn.clicked.connect(self._execute_strategy)
        button_layout.addWidget(self.execute_btn)

        self.backtest_btn = QPushButton("策略回测")
        self.backtest_btn.clicked.connect(self._backtest_strategy)
        button_layout.addWidget(self.backtest_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def _create_results_widget(self) -> QWidget:
        """创建结果显示区域"""
        widget = QGroupBox("策略结果")
        layout = QVBoxLayout()

        # 结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "股票代码", "信号数量", "买入信号", "卖出信号", "最新信号", "信号时间"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.results_table)

        # 详细日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(QLabel("执行日志:"))
        layout.addWidget(self.log_text)

        widget.setLayout(layout)
        return widget

    def _load_strategies(self):
        """加载策略列表"""
        try:
            strategies = self.strategy_manager.list_strategies()

            self.strategy_combo.clear()
            for strategy_info in strategies:
                self.strategy_combo.addItem(
                    strategy_info['name'],
                    strategy_info['id']
                )

            logger.info(f"已加载 {len(strategies)} 个策略")

        except Exception as e:
            logger.error(f"加载策略列表失败: {e}")
            self._log_message(f"加载策略失败: {e}", is_error=True)

    def _on_strategy_changed(self, strategy_name: str):
        """策略选择变化"""
        # 获取策略ID
        strategy_id = self.strategy_combo.currentData()
        if not strategy_id:
            return

        self.current_strategy_id = strategy_id

        # 获取策略信息
        strategies = self.strategy_manager.list_strategies()
        strategy_info = next(
            (s for s in strategies if s['id'] == strategy_id),
            None
        )

        if not strategy_info:
            return

        # 更新描述
        self.strategy_desc_label.setText(strategy_info['description'])

        # 更新参数配置UI
        self._update_params_ui(strategy_info['parameters'])

    def _update_params_ui(self, parameters: Dict[str, Any]):
        """更新参数配置UI"""
        # 清除旧的参数控件
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 存储参数控件的引用
        self.param_widgets = {}

        # 为每个参数创建输入控件
        for param_name, default_value in parameters.items():
            param_layout = QHBoxLayout()

            # 参数名称（格式化）
            display_name = param_name.replace('_', ' ').title()
            param_layout.addWidget(QLabel(f"{display_name}:"))

            # 根据类型创建不同的输入控件
            if isinstance(default_value, int):
                widget = QSpinBox()
                widget.setRange(1, 10000)
                widget.setValue(default_value)
            elif isinstance(default_value, float):
                widget = QDoubleSpinBox()
                widget.setRange(0.0, 100.0)
                widget.setDecimals(4)
                widget.setSingleStep(0.01)
                widget.setValue(default_value)
            else:
                widget = QLineEdit()
                widget.setText(str(default_value))

            self.param_widgets[param_name] = widget
            param_layout.addWidget(widget)
            param_layout.addStretch()

            self.params_layout.addLayout(param_layout)

    def _get_strategy_params(self) -> Dict[str, Any]:
        """获取当前策略参数"""
        params = {}

        for param_name, widget in self.param_widgets.items():
            if isinstance(widget, QSpinBox):
                params[param_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                params[param_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                try:
                    # 尝试转换为数字
                    value = float(widget.text())
                    if value.is_integer():
                        value = int(value)
                    params[param_name] = value
                except ValueError:
                    params[param_name] = widget.text()

        return params

    def _execute_strategy(self):
        """执行策略"""
        try:
            # 验证输入
            if not self.current_strategy_id:
                QMessageBox.warning(self, "错误", "请先选择策略")
                return

            stocks_text = self.stocks_input.text().strip()
            if not stocks_text:
                QMessageBox.warning(self, "错误", "请输入股票代码")
                return

            # 解析股票列表
            symbols = [s.strip() for s in stocks_text.split(',') if s.strip()]

            # 获取策略参数
            strategy_params = self._get_strategy_params()

            self._log_message(f"正在执行策略: {self.strategy_combo.currentText()}")
            self._log_message(f"股票列表: {symbols}")
            self._log_message(f"策略参数: {strategy_params}")

            # 执行策略
            results = self.strategy_manager.execute_strategy(
                strategy_id=self.current_strategy_id,
                symbols=symbols,
                **strategy_params
            )

            # 显示结果
            self._display_results(results)

            # 发送信号
            self.strategy_executed.emit({
                'strategy_id': self.current_strategy_id,
                'symbols': symbols,
                'results': results
            })

            self._log_message(f"✅ 策略执行完成！成功: {len(results)}/{len(symbols)}", is_success=True)

        except Exception as e:
            logger.error(f"执行策略失败: {e}")
            self._log_message(f"❌ 执行失败: {e}", is_error=True)
            QMessageBox.critical(self, "错误", f"执行策略失败:\n{str(e)}")

    def _backtest_strategy(self):
        """策略回测"""
        try:
            # 验证输入
            if not self.current_strategy_id:
                QMessageBox.warning(self, "错误", "请先选择策略")
                return

            stocks_text = self.stocks_input.text().strip()
            if not stocks_text:
                QMessageBox.warning(self, "错误", "请输入股票代码")
                return

            # 解析股票列表
            symbols = [s.strip() for s in stocks_text.split(',') if s.strip()]

            # 获取策略参数
            strategy_params = self._get_strategy_params()

            self._log_message(f"正在回测策略: {self.strategy_combo.currentText()}")

            # 回测
            backtest_results = self.strategy_manager.backtest_strategy(
                strategy_id=self.current_strategy_id,
                symbols=symbols,
                initial_capital=1000000.0,
                **strategy_params
            )

            # 显示回测结果
            self._display_backtest_results(backtest_results)

            self._log_message("✅ 回测完成！", is_success=True)

        except Exception as e:
            logger.error(f"回测失败: {e}")
            self._log_message(f"❌ 回测失败: {e}", is_error=True)
            QMessageBox.critical(self, "错误", f"策略回测失败:\n{str(e)}")

    def _display_results(self, results: Dict[str, pd.DataFrame]):
        """显示策略执行结果"""
        self.results_table.setRowCount(0)

        for symbol, signal_data in results.items():
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            # 股票代码
            self.results_table.setItem(row, 0, QTableWidgetItem(symbol))

            # 信号数量
            total_signals = len(signal_data)
            self.results_table.setItem(row, 1, QTableWidgetItem(str(total_signals)))

            # 买入信号数
            buy_signals = signal_data['buy_signal'].sum() if 'buy_signal' in signal_data.columns else 0
            self.results_table.setItem(row, 2, QTableWidgetItem(str(buy_signals)))

            # 卖出信号数
            sell_signals = signal_data['sell_signal'].sum() if 'sell_signal' in signal_data.columns else 0
            self.results_table.setItem(row, 3, QTableWidgetItem(str(sell_signals)))

            # 最新信号
            if not signal_data.empty:
                latest_signal = "买入" if signal_data.iloc[-1].get('buy_signal', 0) else \
                    "卖出" if signal_data.iloc[-1].get('sell_signal', 0) else "无"
                self.results_table.setItem(row, 4, QTableWidgetItem(latest_signal))

                # 信号时间
                signal_time = str(signal_data.iloc[-1].get('datetime', ''))
                self.results_table.setItem(row, 5, QTableWidgetItem(signal_time))

    def _display_backtest_results(self, results: Dict[str, Any]):
        """显示回测结果 - 支持专业级回测指标"""
        if not results:
            return

        # 基础信息
        strategy_name = results.get('strategy_name', self.strategy_combo.currentText())
        symbols = results.get('symbols', [])
        initial_capital = results.get('initial_capital', 0)
        engine_info = results.get('backtest_engine', 'Unknown')
        calculation_time = results.get('calculation_time', 'N/A')
        level = results.get('level', 'Unknown')

        # 收益指标
        total_return = results.get('total_return', 0)
        annualized_return = results.get('annualized_return', 0)

        # 风险指标
        volatility = results.get('volatility', 0)
        max_drawdown = results.get('max_drawdown', 0)
        max_drawdown_duration = results.get('max_drawdown_duration', 0)

        # 风险调整收益
        sharpe_ratio = results.get('sharpe_ratio', 0)
        sortino_ratio = results.get('sortino_ratio', 0)
        calmar_ratio = results.get('calmar_ratio', 0)

        # 风险度量
        var_95 = results.get('var_95', 0)
        var_99 = results.get('var_99', 0)

        # 交易统计
        total_trades = results.get('total_trades', 0)
        win_trades = results.get('win_trades', 0)
        loss_trades = results.get('loss_trades', 0)
        win_rate = results.get('win_rate', 0)
        profit_factor = results.get('profit_factor', 0)

        # Alpha/Beta
        alpha = results.get('alpha', 0)
        beta = results.get('beta', 1.0)
        information_ratio = results.get('information_ratio', 0)

        # 信号统计
        signal_summary = results.get('signal_summary', {})
        note = results.get('note', '')

        # 构建详细消息
        message = f"""
专业回测结果：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 回测引擎: {engine_info} | 级别: {level} | 计算时间: {calculation_time}
🎯 策略: {strategy_name}
📈 股票数量: {len(symbols)} | 股票列表: {', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''}
💰 初始资金: ¥{initial_capital:,.2f}

📈 收益指标
   总收益率: {total_return:+.2%}     年化收益率: {annualized_return:+.2%}
   
📉 风险指标  
   波动率: {volatility:.2%}        最大回撤: {max_drawdown:.2%}
   回撤持续: {max_drawdown_duration}天
   
🎯 风险调整收益
   夏普比率: {sharpe_ratio:.3f}     Sortino比率: {sortino_ratio:.3f}     Calmar比率: {calmar_ratio:.3f}
   
⚠️ 风险度量
   VaR(95%): {var_95:.2%}        VaR(99%): {var_99:.2%}
   
📊 交易统计
   总交易: {total_trades}次        盈利交易: {win_trades}次        亏损交易: {loss_trades}次
   胜率: {win_rate:.1%}          盈亏比: {profit_factor:.2f}:1
   
🎯 基准表现
   Alpha: {alpha:.3f}            Beta: {beta:.3f}            信息比率: {information_ratio:.3f}
   
📋 信号分析
   总信号: {signal_summary.get('total_signals', 0)}个       买入信号: {signal_summary.get('buy_signals', 0)}个
   卖出信号: {signal_summary.get('sell_signals', 0)}个       信号密度: {signal_summary.get('signal_density', 0):.3f}

{note if note else ''}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """

        self._log_message(message, is_success=True)

        # 在日志中显示成功完成的回测结果
        QMessageBox.information(self, "专业回测结果", message)

    def _log_message(self, message: str, is_error: bool = False, is_success: bool = False):
        """记录日志"""
        if is_error:
            color = "red"
        elif is_success:
            color = "green"
        else:
            color = "black"

        self.log_text.append(f'<span style="color: {color}">{message}</span>')


# 使用示例
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    widget = StrategyWidget()
    widget.setWindowTitle("FactorWeave-Quant 策略执行")
    widget.resize(1000, 700)
    widget.show()

    sys.exit(app.exec_())
