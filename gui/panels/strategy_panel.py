"""
策略管理面板模块

提供完整的策略管理功能，包括：
- 策略列表管理
- 策略配置和参数设置
- 策略回测和优化
- 策略性能评估
- 策略组合管理
"""

import pandas as pd
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.strategy import get_strategy_registry, get_strategy_engine
from gui.components.custom_widgets import add_shadow, safe_strftime
from core.adapters import get_logger


class StrategyManagementPanel(QWidget):
    """策略管理面板"""

    # 定义信号
    strategy_selected = pyqtSignal(str)  # 策略选择信号
    strategy_started = pyqtSignal(str, dict)  # 策略启动信号
    strategy_stopped = pyqtSignal(str)  # 策略停止信号
    backtest_completed = pyqtSignal(str, dict)  # 回测完成信号
    optimization_completed = pyqtSignal(str, dict)  # 优化完成信号

    def __init__(self, parent=None, log_manager=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.log_manager = log_manager or get_logger(__name__)
        self.strategy_registry = get_strategy_registry()
        self.strategy_engine = get_strategy_engine()
        self.current_strategy = None
        self.current_params = {}

        self.init_ui()
        self.load_strategies()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 创建策略选择区域
        self.create_strategy_selection(layout)

        # 创建策略参数配置区域
        self.create_strategy_config(layout)

        # 创建回测控制区域
        self.create_backtest_controls(layout)

        # 创建策略结果显示区域
        self.create_results_display(layout)

    def create_strategy_selection(self, parent_layout):
        """创建策略选择区域"""
        group = QGroupBox("策略选择")
        layout = QVBoxLayout(group)

        # 策略列表
        self.strategy_list = QListWidget()
        self.strategy_list.setMaximumHeight(150)
        self.strategy_list.currentItemChanged.connect(self.on_strategy_selected)
        layout.addWidget(self.strategy_list)

        # 策略操作按钮
        button_layout = QHBoxLayout()
        self.refresh_strategies_btn = QPushButton("刷新策略")
        self.load_strategy_btn = QPushButton("加载策略")
        self.save_strategy_btn = QPushButton("保存配置")

        self.refresh_strategies_btn.clicked.connect(self.load_strategies)
        self.load_strategy_btn.clicked.connect(self.load_strategy_config)
        self.save_strategy_btn.clicked.connect(self.save_strategy_config)

        button_layout.addWidget(self.refresh_strategies_btn)
        button_layout.addWidget(self.load_strategy_btn)
        button_layout.addWidget(self.save_strategy_btn)
        layout.addLayout(button_layout)

        parent_layout.addWidget(group)

    def create_strategy_config(self, parent_layout):
        """创建策略参数配置区域"""
        group = QGroupBox("策略参数")
        layout = QVBoxLayout(group)

        # 参数配置表格
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(3)
        self.params_table.setHorizontalHeaderLabels(["参数名", "当前值", "描述"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.params_table)

        # 参数操作按钮
        param_button_layout = QHBoxLayout()
        self.reset_params_btn = QPushButton("重置参数")
        self.apply_params_btn = QPushButton("应用参数")

        self.reset_params_btn.clicked.connect(self.reset_strategy_params)
        self.apply_params_btn.clicked.connect(self.apply_strategy_params)

        param_button_layout.addWidget(self.reset_params_btn)
        param_button_layout.addWidget(self.apply_params_btn)
        layout.addLayout(param_button_layout)

        parent_layout.addWidget(group)

    def create_backtest_controls(self, parent_layout):
        """创建回测控制区域"""
        group = QGroupBox("回测控制")
        layout = QGridLayout(group)

        # 回测时间范围
        layout.addWidget(QLabel("开始时间:"), 0, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        layout.addWidget(self.start_date, 0, 1)

        layout.addWidget(QLabel("结束时间:"), 0, 2)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        layout.addWidget(self.end_date, 0, 3)

        # 初始资金
        layout.addWidget(QLabel("初始资金:"), 1, 0)
        self.initial_capital = QDoubleSpinBox()
        self.initial_capital.setRange(1000, 10000000)
        self.initial_capital.setValue(100000)
        self.initial_capital.setSuffix(" 元")
        layout.addWidget(self.initial_capital, 1, 1)

        # 手续费率
        layout.addWidget(QLabel("手续费率:"), 1, 2)
        self.commission_rate = QDoubleSpinBox()
        self.commission_rate.setRange(0, 0.01)
        self.commission_rate.setValue(0.0003)
        self.commission_rate.setDecimals(4)
        self.commission_rate.setSuffix("%")
        layout.addWidget(self.commission_rate, 1, 3)

        # 回测按钮
        button_layout = QHBoxLayout()
        self.start_backtest_btn = QPushButton("开始回测")
        self.stop_backtest_btn = QPushButton("停止回测")
        self.optimize_strategy_btn = QPushButton("策略优化")

        self.start_backtest_btn.clicked.connect(self.start_backtest)
        self.stop_backtest_btn.clicked.connect(self.stop_backtest)
        self.optimize_strategy_btn.clicked.connect(self.start_optimization)

        self.stop_backtest_btn.setEnabled(False)

        button_layout.addWidget(self.start_backtest_btn)
        button_layout.addWidget(self.stop_backtest_btn)
        button_layout.addWidget(self.optimize_strategy_btn)

        layout.addLayout(button_layout, 2, 0, 1, 4)
        parent_layout.addWidget(group)

    def create_results_display(self, parent_layout):
        """创建结果显示区域"""
        group = QGroupBox("回测结果")
        layout = QVBoxLayout(group)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 性能指标标签页
        self.metrics_tab = QWidget()
        metrics_layout = QVBoxLayout(self.metrics_tab)
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "值"])
        metrics_layout.addWidget(self.metrics_table)
        self.results_tabs.addTab(self.metrics_tab, "性能指标")

        # 交易记录标签页
        self.trades_tab = QWidget()
        trades_layout = QVBoxLayout(self.trades_tab)
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(6)
        self.trades_table.setHorizontalHeaderLabels(["时间", "股票", "操作", "价格", "数量", "金额"])
        trades_layout.addWidget(self.trades_table)
        self.results_tabs.addTab(self.trades_tab, "交易记录")

        layout.addWidget(self.results_tabs)

        # 结果操作按钮
        result_button_layout = QHBoxLayout()
        self.export_results_btn = QPushButton("导出结果")
        self.clear_results_btn = QPushButton("清空结果")

        self.export_results_btn.clicked.connect(self.export_backtest_results)
        self.clear_results_btn.clicked.connect(self.clear_backtest_results)

        result_button_layout.addWidget(self.export_results_btn)
        result_button_layout.addWidget(self.clear_results_btn)
        layout.addLayout(result_button_layout)

        parent_layout.addWidget(group)

    def load_strategies(self):
        """加载策略列表"""
        try:
            self.strategy_list.clear()
            strategies = self.strategy_registry.get_all_strategies()

            for strategy_name, strategy_class in strategies.items():
                item = QListWidgetItem(strategy_name)
                item.setData(Qt.UserRole, strategy_class)
                self.strategy_list.addItem(item)

            self.log_manager.info(f"已加载 {len(strategies)} 个策略")

        except Exception as e:
            self.log_manager.error(f"加载策略列表失败: {str(e)}")

    def on_strategy_selected(self, current, previous):
        """策略选择事件"""
        if current:
            strategy_name = current.text()
            strategy_class = current.data(Qt.UserRole)

            self.current_strategy = strategy_name
            self.load_strategy_parameters(strategy_class)
            self.strategy_selected.emit(strategy_name)

            self.log_manager.info(f"选择策略: {strategy_name}")

    def load_strategy_parameters(self, strategy_class):
        """加载策略参数"""
        try:
            if not strategy_class:
                return

            # 获取策略默认参数
            default_params = getattr(strategy_class, 'default_params', {})
            param_descriptions = getattr(strategy_class, 'param_descriptions', {})

            self.params_table.setRowCount(len(default_params))

            row = 0
            for param_name, default_value in default_params.items():
                # 参数名
                name_item = QTableWidgetItem(param_name)
                name_item.setFlags(Qt.ItemIsEnabled)
                self.params_table.setItem(row, 0, name_item)

                # 当前值
                value_item = QTableWidgetItem(str(default_value))
                self.params_table.setItem(row, 1, value_item)

                # 描述
                description = param_descriptions.get(param_name, "")
                desc_item = QTableWidgetItem(description)
                desc_item.setFlags(Qt.ItemIsEnabled)
                self.params_table.setItem(row, 2, desc_item)

                row += 1

            self.current_params = default_params.copy()

        except Exception as e:
            self.log_manager.error(f"加载策略参数失败: {str(e)}")

    def reset_strategy_params(self):
        """重置策略参数"""
        try:
            current_item = self.strategy_list.currentItem()
            if current_item:
                strategy_class = current_item.data(Qt.UserRole)
                self.load_strategy_parameters(strategy_class)
                self.log_manager.info("策略参数已重置")

        except Exception as e:
            self.log_manager.error(f"重置策略参数失败: {str(e)}")

    def apply_strategy_params(self):
        """应用策略参数"""
        try:
            params = {}
            for row in range(self.params_table.rowCount()):
                param_name = self.params_table.item(row, 0).text()
                param_value = self.params_table.item(row, 1).text()

                # 尝试转换参数类型
                try:
                    if '.' in param_value:
                        param_value = float(param_value)
                    else:
                        param_value = int(param_value)
                except ValueError:
                    pass  # 保持字符串类型

                params[param_name] = param_value

            self.current_params = params
            self.log_manager.info("策略参数已应用")

        except Exception as e:
            self.log_manager.error(f"应用策略参数失败: {str(e)}")

    def start_backtest(self):
        """开始回测"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "警告", "请先选择策略")
                return

            # 获取回测参数
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            initial_capital = self.initial_capital.value()
            commission_rate = self.commission_rate.value() / 100

            backtest_config = {
                'strategy': self.current_strategy,
                'params': self.current_params,
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'commission_rate': commission_rate
            }

            # 启动回测
            self.start_backtest_btn.setEnabled(False)
            self.stop_backtest_btn.setEnabled(True)

            self.strategy_started.emit(self.current_strategy, backtest_config)
            self.log_manager.info(f"开始回测策略: {self.current_strategy}")

        except Exception as e:
            self.log_manager.error(f"启动回测失败: {str(e)}")
            self.start_backtest_btn.setEnabled(True)
            self.stop_backtest_btn.setEnabled(False)

    def stop_backtest(self):
        """停止回测"""
        try:
            self.strategy_stopped.emit(self.current_strategy)
            self.start_backtest_btn.setEnabled(True)
            self.stop_backtest_btn.setEnabled(False)
            self.log_manager.info("回测已停止")

        except Exception as e:
            self.log_manager.error(f"停止回测失败: {str(e)}")

    def start_optimization(self):
        """开始策略优化"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "警告", "请先选择策略")
                return

            # TODO: 实现策略优化功能
            self.log_manager.info(f"开始优化策略: {self.current_strategy}")

        except Exception as e:
            self.log_manager.error(f"启动策略优化失败: {str(e)}")

    def update_backtest_results(self, results: dict):
        """更新回测结果"""
        try:
            # 更新性能指标
            self.update_metrics_table(results.get('metrics', {}))

            # 更新交易记录
            self.update_trades_table(results.get('trades', []))

            # 回测完成，恢复按钮状态
            self.start_backtest_btn.setEnabled(True)
            self.stop_backtest_btn.setEnabled(False)

            self.backtest_completed.emit(self.current_strategy, results)

        except Exception as e:
            self.log_manager.error(f"更新回测结果失败: {str(e)}")

    def update_metrics_table(self, metrics: dict):
        """更新性能指标表格"""
        try:
            self.metrics_table.setRowCount(len(metrics))

            row = 0
            for metric_name, metric_value in metrics.items():
                name_item = QTableWidgetItem(metric_name)
                value_item = QTableWidgetItem(str(metric_value))

                self.metrics_table.setItem(row, 0, name_item)
                self.metrics_table.setItem(row, 1, value_item)
                row += 1

        except Exception as e:
            self.log_manager.error(f"更新性能指标表格失败: {str(e)}")

    def update_trades_table(self, trades: list):
        """更新交易记录表格"""
        try:
            self.trades_table.setRowCount(len(trades))

            for row, trade in enumerate(trades):
                time_item = QTableWidgetItem(str(trade.get('time', '')))
                stock_item = QTableWidgetItem(trade.get('stock', ''))
                action_item = QTableWidgetItem(trade.get('action', ''))
                price_item = QTableWidgetItem(str(trade.get('price', 0)))
                quantity_item = QTableWidgetItem(str(trade.get('quantity', 0)))
                amount_item = QTableWidgetItem(str(trade.get('amount', 0)))

                self.trades_table.setItem(row, 0, time_item)
                self.trades_table.setItem(row, 1, stock_item)
                self.trades_table.setItem(row, 2, action_item)
                self.trades_table.setItem(row, 3, price_item)
                self.trades_table.setItem(row, 4, quantity_item)
                self.trades_table.setItem(row, 5, amount_item)

        except Exception as e:
            self.log_manager.error(f"更新交易记录表格失败: {str(e)}")

    def export_backtest_results(self):
        """导出回测结果"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "警告", "没有可导出的回测结果")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "导出回测结果",
                f"backtest_{self.current_strategy}_{safe_strftime(datetime.now(), '%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx)"
            )

            if filename:
                # 导出性能指标和交易记录
                with pd.ExcelWriter(filename) as writer:
                    # 导出性能指标
                    metrics_data = []
                    for row in range(self.metrics_table.rowCount()):
                        metric_name = self.metrics_table.item(row, 0).text()
                        metric_value = self.metrics_table.item(row, 1).text()
                        metrics_data.append({'指标': metric_name, '值': metric_value})

                    metrics_df = pd.DataFrame(metrics_data)
                    metrics_df.to_excel(writer, sheet_name='性能指标', index=False)

                    # 导出交易记录
                    trades_data = []
                    for row in range(self.trades_table.rowCount()):
                        trade_data = {}
                        for col in range(self.trades_table.columnCount()):
                            header = self.trades_table.horizontalHeaderItem(col).text()
                            item = self.trades_table.item(row, col)
                            trade_data[header] = item.text() if item else ""
                        trades_data.append(trade_data)

                    trades_df = pd.DataFrame(trades_data)
                    trades_df.to_excel(writer, sheet_name='交易记录', index=False)

                QMessageBox.information(self, "成功", f"回测结果已导出到: {filename}")
                self.log_manager.info(f"回测结果导出成功: {filename}")

        except Exception as e:
            error_msg = f"导出回测结果失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_manager.error(error_msg)

    def clear_backtest_results(self):
        """清空回测结果"""
        try:
            self.metrics_table.setRowCount(0)
            self.trades_table.setRowCount(0)
            self.log_manager.info("回测结果已清空")

        except Exception as e:
            self.log_manager.error(f"清空回测结果失败: {str(e)}")

    def load_strategy_config(self):
        """加载策略配置"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "加载策略配置", "", "JSON Files (*.json)"
            )

            if filename:
                import json
                with open(filename, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 应用配置
                if 'strategy' in config:
                    # 查找并选择策略
                    for i in range(self.strategy_list.count()):
                        item = self.strategy_list.item(i)
                        if item.text() == config['strategy']:
                            self.strategy_list.setCurrentItem(item)
                            break

                if 'params' in config:
                    # 应用参数
                    self.current_params = config['params']
                    self.apply_params_to_table()

                self.log_manager.info(f"策略配置加载成功: {filename}")

        except Exception as e:
            error_msg = f"加载策略配置失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_manager.error(error_msg)

    def save_strategy_config(self):
        """保存策略配置"""
        try:
            if not self.current_strategy:
                QMessageBox.warning(self, "警告", "请先选择策略")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "保存策略配置",
                f"strategy_{self.current_strategy}_{safe_strftime(datetime.now(), '%Y%m%d')}.json",
                "JSON Files (*.json)"
            )

            if filename:
                config = {
                    'strategy': self.current_strategy,
                    'params': self.current_params,
                    'created_time': datetime.now().isoformat()
                }

                import json
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"策略配置已保存到: {filename}")
                self.log_manager.info(f"策略配置保存成功: {filename}")

        except Exception as e:
            error_msg = f"保存策略配置失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_manager.error(error_msg)

    def apply_params_to_table(self):
        """将当前参数应用到参数表格"""
        try:
            for row in range(self.params_table.rowCount()):
                param_name = self.params_table.item(row, 0).text()
                if param_name in self.current_params:
                    value_item = self.params_table.item(row, 1)
                    if value_item:
                        value_item.setText(str(self.current_params[param_name]))

        except Exception as e:
            self.log_manager.error(f"应用参数到表格失败: {str(e)}")
