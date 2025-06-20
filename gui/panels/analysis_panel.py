"""
分析面板模块

负责股票分析、策略回测、性能评估等功能
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import numpy as np
import traceback
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import json


class AnalysisPanel(QWidget):
    """分析面板"""

    # 信号定义
    analysis_started = pyqtSignal(str)  # 分析开始信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    analysis_error = pyqtSignal(str)  # 分析错误信号
    strategy_changed = pyqtSignal(str)  # 策略变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化属性
        self.current_stock = None
        self.current_strategy = "均线策略"
        self.analysis_results = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 获取父窗口的管理器
        if parent:
            self.log_manager = getattr(parent, 'log_manager', None)
            self.data_manager = getattr(parent, 'data_manager', None)
            self.sm = getattr(parent, 'sm', None)

        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 创建策略选择区域
        self.create_strategy_selection(layout)

        # 创建分析控制区域
        self.create_analysis_controls(layout)

        # 创建结果显示区域
        self.create_results_display(layout)

    def create_strategy_selection(self, layout):
        """创建策略选择区域"""
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QVBoxLayout(strategy_group)

        # 策略选择
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("分析策略:"))

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "均线策略", "MACD策略", "RSI策略", "KDJ策略",
            "布林带策略", "动量策略", "趋势跟踪", "均值回归",
            "多因子模型", "技术面分析", "基本面分析", "量化选股"
        ])
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        selection_layout.addWidget(self.strategy_combo)

        selection_layout.addStretch()

        # 策略说明按钮
        explain_btn = QPushButton("策略说明")
        explain_btn.clicked.connect(self.show_strategy_explanation)
        selection_layout.addWidget(explain_btn)

        strategy_layout.addLayout(selection_layout)

        # 策略参数设置
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("参数设置:"))

        self.params_btn = QPushButton("参数配置")
        self.params_btn.clicked.connect(self.show_strategy_params)
        params_layout.addWidget(self.params_btn)

        params_layout.addStretch()

        # 保存/加载配置
        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self.save_strategy_config)
        params_layout.addWidget(save_config_btn)

        load_config_btn = QPushButton("加载配置")
        load_config_btn.clicked.connect(self.load_strategy_config)
        params_layout.addWidget(load_config_btn)

        strategy_layout.addLayout(params_layout)
        layout.addWidget(strategy_group)

    def create_analysis_controls(self, layout):
        """创建分析控制区域"""
        controls_group = QGroupBox("分析控制")
        controls_layout = QVBoxLayout(controls_group)

        # 分析类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("分析类型:"))

        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "单股分析", "批量分析", "行业分析", "市场分析",
            "策略回测", "风险评估", "收益分析", "相关性分析"
        ])
        type_layout.addWidget(self.analysis_type_combo)

        type_layout.addStretch()
        controls_layout.addLayout(type_layout)

        # 时间范围设置
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("分析周期:"))

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        time_layout.addWidget(self.start_date)

        time_layout.addWidget(QLabel("至"))

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        time_layout.addWidget(self.end_date)

        time_layout.addStretch()
        controls_layout.addLayout(time_layout)

        # 分析按钮
        button_layout = QHBoxLayout()

        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.analyze_btn)

        self.stop_btn = QPushButton("停止分析")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)

        controls_layout.addLayout(button_layout)
        layout.addWidget(controls_group)

    def create_results_display(self, layout):
        """创建结果显示区域"""
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout(results_group)

        # 创建标签页
        self.results_tabs = QTabWidget()

        # 概览标签页
        self.create_overview_tab()

        # 详细结果标签页
        self.create_details_tab()

        # 图表标签页
        self.create_charts_tab()

        # 报告标签页
        self.create_report_tab()

        results_layout.addWidget(self.results_tabs)

        # 结果操作按钮
        action_layout = QHBoxLayout()

        export_btn = QPushButton("导出结果")
        export_btn.clicked.connect(self.export_results)
        action_layout.addWidget(export_btn)

        save_report_btn = QPushButton("保存报告")
        save_report_btn.clicked.connect(self.save_report)
        action_layout.addWidget(save_report_btn)

        clear_btn = QPushButton("清空结果")
        clear_btn.clicked.connect(self.clear_results)
        action_layout.addWidget(clear_btn)

        action_layout.addStretch()

        results_layout.addLayout(action_layout)
        layout.addWidget(results_group)

    def create_overview_tab(self):
        """创建概览标签页"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)

        # 关键指标显示
        metrics_layout = QGridLayout()

        # 收益率
        metrics_layout.addWidget(QLabel("总收益率:"), 0, 0)
        self.total_return_label = QLabel("--")
        self.total_return_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        metrics_layout.addWidget(self.total_return_label, 0, 1)

        # 年化收益率
        metrics_layout.addWidget(QLabel("年化收益率:"), 0, 2)
        self.annual_return_label = QLabel("--")
        self.annual_return_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        metrics_layout.addWidget(self.annual_return_label, 0, 3)

        # 最大回撤
        metrics_layout.addWidget(QLabel("最大回撤:"), 1, 0)
        self.max_drawdown_label = QLabel("--")
        self.max_drawdown_label.setStyleSheet("font-weight: bold; color: #f44336;")
        metrics_layout.addWidget(self.max_drawdown_label, 1, 1)

        # 夏普比率
        metrics_layout.addWidget(QLabel("夏普比率:"), 1, 2)
        self.sharpe_ratio_label = QLabel("--")
        self.sharpe_ratio_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        metrics_layout.addWidget(self.sharpe_ratio_label, 1, 3)

        # 胜率
        metrics_layout.addWidget(QLabel("胜率:"), 2, 0)
        self.win_rate_label = QLabel("--")
        self.win_rate_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        metrics_layout.addWidget(self.win_rate_label, 2, 1)

        # 盈亏比
        metrics_layout.addWidget(QLabel("盈亏比:"), 2, 2)
        self.profit_loss_ratio_label = QLabel("--")
        self.profit_loss_ratio_label.setStyleSheet("font-weight: bold; color: #9C27B0;")
        metrics_layout.addWidget(self.profit_loss_ratio_label, 2, 3)

        layout.addLayout(metrics_layout)

        # 分析摘要
        summary_group = QGroupBox("分析摘要")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setPlainText("请先进行分析...")
        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_group)

        self.results_tabs.addTab(overview_widget, "概览")

    def create_details_tab(self):
        """创建详细结果标签页"""
        details_widget = QWidget()
        layout = QVBoxLayout(details_widget)

        # 详细数据表格
        self.details_table = QTableWidget()
        self.details_table.setAlternatingRowColors(True)
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.details_table)

        self.results_tabs.addTab(details_widget, "详细数据")

    def create_charts_tab(self):
        """创建图表标签页"""
        charts_widget = QWidget()
        layout = QVBoxLayout(charts_widget)

        # 图表占位符
        self.charts_placeholder = QLabel("分析完成后将显示相关图表")
        self.charts_placeholder.setAlignment(Qt.AlignCenter)
        self.charts_placeholder.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self.charts_placeholder)

        self.results_tabs.addTab(charts_widget, "图表分析")

    def create_report_tab(self):
        """创建报告标签页"""
        report_widget = QWidget()
        layout = QVBoxLayout(report_widget)

        # 报告文本
        self.report_text = QTextEdit()
        self.report_text.setPlainText("分析报告将在分析完成后生成...")
        layout.addWidget(self.report_text)

        self.results_tabs.addTab(report_widget, "分析报告")

    def on_strategy_changed(self, strategy: str):
        """策略改变事件"""
        try:
            self.current_strategy = strategy
            self.strategy_changed.emit(strategy)

            if self.log_manager:
                self.log_manager.info(f"策略已切换为: {strategy}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"策略切换失败: {str(e)}")

    def show_strategy_explanation(self):
        """显示策略说明"""
        try:
            strategy = self.current_strategy
            explanation = self.get_strategy_explanation(strategy)

            dialog = QDialog(self)
            dialog.setWindowTitle(f"{strategy} - 策略说明")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout(dialog)

            text_edit = QTextEdit()
            text_edit.setPlainText(explanation)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            button_layout.addStretch()
            button_layout.addWidget(ok_btn)
            layout.addLayout(button_layout)

            dialog.exec_()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示策略说明失败: {str(e)}")

    def get_strategy_explanation(self, strategy: str) -> str:
        """获取策略说明"""
        explanations = {
            "均线策略": """
均线策略是最经典的技术分析策略之一。

原理：
- 使用移动平均线判断趋势方向
- 短期均线上穿长期均线时买入（金叉）
- 短期均线下穿长期均线时卖出（死叉）

参数：
- 短期均线周期（默认5日）
- 长期均线周期（默认20日）

适用场景：
- 趋势明显的市场
- 中长期投资

风险提示：
- 在震荡市场中可能产生频繁的假信号
- 存在滞后性，可能错过最佳买卖点
            """,
            "MACD策略": """
MACD（指数平滑移动平均线）策略基于价格的动量变化。

原理：
- MACD线上穿信号线时买入
- MACD线下穿信号线时卖出
- 结合MACD柱状图判断动量强弱

参数：
- 快线周期（默认12）
- 慢线周期（默认26）
- 信号线周期（默认9）

适用场景：
- 趋势跟踪
- 动量交易

风险提示：
- 在横盘市场中效果较差
- 需要结合其他指标确认信号
            """,
            # 可以继续添加其他策略的说明...
        }

        return explanations.get(strategy, f"{strategy}策略说明暂未完善，请参考相关技术分析资料。")

    def show_strategy_params(self):
        """显示策略参数设置对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{self.current_strategy} - 参数设置")
            dialog.setMinimumSize(400, 300)

            layout = QVBoxLayout(dialog)

            # 根据策略类型创建参数设置界面
            params_widget = self.create_strategy_params_widget(self.current_strategy)
            layout.addWidget(params_widget)

            # 按钮
            button_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            if dialog.exec_() == QDialog.Accepted:
                # TODO: 保存参数设置
                pass

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"显示策略参数对话框失败: {str(e)}")

    def create_strategy_params_widget(self, strategy: str) -> QWidget:
        """创建策略参数设置控件"""
        widget = QWidget()
        layout = QFormLayout(widget)

        if strategy == "均线策略":
            short_period = QSpinBox()
            short_period.setRange(1, 50)
            short_period.setValue(5)
            layout.addRow("短期均线周期:", short_period)

            long_period = QSpinBox()
            long_period.setRange(10, 200)
            long_period.setValue(20)
            layout.addRow("长期均线周期:", long_period)

        elif strategy == "MACD策略":
            fast_period = QSpinBox()
            fast_period.setRange(1, 50)
            fast_period.setValue(12)
            layout.addRow("快线周期:", fast_period)

            slow_period = QSpinBox()
            slow_period.setRange(10, 100)
            slow_period.setValue(26)
            layout.addRow("慢线周期:", slow_period)

            signal_period = QSpinBox()
            signal_period.setRange(1, 20)
            signal_period.setValue(9)
            layout.addRow("信号线周期:", signal_period)

        # TODO: 添加其他策略的参数设置

        return widget

    def start_analysis(self):
        """开始分析"""
        try:
            if not self.current_stock:
                QMessageBox.warning(self, "警告", "请先选择要分析的股票")
                return

            # 更新UI状态
            self.analyze_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 发送分析开始信号
            self.analysis_started.emit(self.current_strategy)

            # 在线程池中执行分析
            future = self.executor.submit(self._execute_analysis)

            # 使用QTimer定期检查分析进度
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(lambda: self._check_analysis_progress(future))
            self.check_timer.start(100)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"开始分析失败: {str(e)}")
            self.analysis_error.emit(str(e))

    def _execute_analysis(self) -> dict:
        """执行分析（在后台线程中运行）"""
        try:
            # 模拟分析过程
            results = {
                "stock_code": self.current_stock,
                "strategy": self.current_strategy,
                "start_date": self.start_date.date().toString("yyyy-MM-dd"),
                "end_date": self.end_date.date().toString("yyyy-MM-dd"),
                "total_return": 0.15,  # 15%收益率
                "annual_return": 0.12,  # 12%年化收益率
                "max_drawdown": -0.08,  # -8%最大回撤
                "sharpe_ratio": 1.25,
                "win_rate": 0.65,  # 65%胜率
                "profit_loss_ratio": 1.8,
                "trades": 25,
                "summary": f"使用{self.current_strategy}对{self.current_stock}进行分析，获得了较好的收益表现。"
            }

            return results

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"执行分析失败: {str(e)}")
            raise

    def _check_analysis_progress(self, future):
        """检查分析进度"""
        try:
            if future.done():
                self.check_timer.stop()

                try:
                    results = future.result()
                    self._on_analysis_completed(results)
                except Exception as e:
                    self._on_analysis_error(str(e))
            else:
                # 更新进度条（模拟进度）
                current_value = self.progress_bar.value()
                if current_value < 90:
                    self.progress_bar.setValue(current_value + 1)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"检查分析进度失败: {str(e)}")

    def _on_analysis_completed(self, results: dict):
        """分析完成处理"""
        try:
            self.analysis_results = results

            # 更新UI状态
            self.analyze_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)

            # 更新结果显示
            self.update_results_display(results)

            # 发送完成信号
            self.analysis_completed.emit(results)

            if self.log_manager:
                self.log_manager.info(f"分析完成: {results['stock_code']} - {results['strategy']}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"分析完成处理失败: {str(e)}")

    def _on_analysis_error(self, error_msg: str):
        """分析错误处理"""
        try:
            # 更新UI状态
            self.analyze_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)

            # 发送错误信号
            self.analysis_error.emit(error_msg)

            QMessageBox.critical(self, "分析错误", f"分析过程中发生错误:\n{error_msg}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"分析错误处理失败: {str(e)}")

    def stop_analysis(self):
        """停止分析"""
        try:
            # TODO: 实现停止分析逻辑
            self.analyze_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)

            if hasattr(self, 'check_timer'):
                self.check_timer.stop()

            if self.log_manager:
                self.log_manager.info("分析已停止")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"停止分析失败: {str(e)}")

    def update_results_display(self, results: dict):
        """更新结果显示"""
        try:
            # 更新概览标签页
            self.total_return_label.setText(f"{results['total_return']:.2%}")
            self.annual_return_label.setText(f"{results['annual_return']:.2%}")
            self.max_drawdown_label.setText(f"{results['max_drawdown']:.2%}")
            self.sharpe_ratio_label.setText(f"{results['sharpe_ratio']:.2f}")
            self.win_rate_label.setText(f"{results['win_rate']:.2%}")
            self.profit_loss_ratio_label.setText(f"{results['profit_loss_ratio']:.2f}")

            self.summary_text.setPlainText(results['summary'])

            # TODO: 更新详细数据表格
            # TODO: 更新图表
            # TODO: 更新报告

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新结果显示失败: {str(e)}")

    def save_strategy_config(self):
        """保存策略配置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存策略配置",
                f"{self.current_strategy}_config.json",
                "JSON Files (*.json)"
            )

            if file_path:
                config = {
                    "strategy": self.current_strategy,
                    "analysis_type": self.analysis_type_combo.currentText(),
                    "start_date": self.start_date.date().toString("yyyy-MM-dd"),
                    "end_date": self.end_date.date().toString("yyyy-MM-dd"),
                    # TODO: 添加策略参数
                }

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"配置已保存到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"保存策略配置失败: {str(e)}")

    def load_strategy_config(self):
        """加载策略配置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "加载策略配置",
                "",
                "JSON Files (*.json)"
            )

            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 应用配置
                if "strategy" in config:
                    index = self.strategy_combo.findText(config["strategy"])
                    if index >= 0:
                        self.strategy_combo.setCurrentIndex(index)

                if "analysis_type" in config:
                    index = self.analysis_type_combo.findText(config["analysis_type"])
                    if index >= 0:
                        self.analysis_type_combo.setCurrentIndex(index)

                # TODO: 应用其他配置

                QMessageBox.information(self, "成功", "配置加载完成")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"加载策略配置失败: {str(e)}")

    def export_results(self):
        """导出分析结果"""
        try:
            if not self.analysis_results:
                QMessageBox.warning(self, "警告", "没有可导出的分析结果")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                f"{self.current_stock}_analysis_results.json",
                "JSON Files (*.json);;CSV Files (*.csv)"
            )

            if file_path:
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.analysis_results, f, ensure_ascii=False, indent=2)
                elif file_path.endswith('.csv'):
                    # TODO: 导出为CSV格式
                    pass

                QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出结果失败: {str(e)}")

    def save_report(self):
        """保存分析报告"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存分析报告",
                f"{self.current_stock}_analysis_report.txt",
                "Text Files (*.txt);;HTML Files (*.html)"
            )

            if file_path:
                report_content = self.report_text.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                QMessageBox.information(self, "成功", f"报告已保存到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"保存报告失败: {str(e)}")

    def clear_results(self):
        """清空分析结果"""
        try:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要清空所有分析结果吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.analysis_results = {}

                # 重置显示
                self.total_return_label.setText("--")
                self.annual_return_label.setText("--")
                self.max_drawdown_label.setText("--")
                self.sharpe_ratio_label.setText("--")
                self.win_rate_label.setText("--")
                self.profit_loss_ratio_label.setText("--")

                self.summary_text.setPlainText("请先进行分析...")
                self.details_table.clear()
                self.report_text.setPlainText("分析报告将在分析完成后生成...")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清空结果失败: {str(e)}")

    def set_stock(self, stock_code: str):
        """设置当前分析的股票"""
        try:
            self.current_stock = stock_code

            if self.log_manager:
                self.log_manager.info(f"分析面板已设置股票: {stock_code}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"设置股票失败: {str(e)}")

    def get_current_strategy(self) -> str:
        """获取当前策略"""
        return self.current_strategy

    def set_strategy(self, strategy: str):
        """设置当前策略"""
        try:
            index = self.strategy_combo.findText(strategy)
            if index >= 0:
                self.strategy_combo.setCurrentIndex(index)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"设置策略失败: {str(e)}")

    def get_analysis_results(self) -> dict:
        """获取分析结果"""
        return self.analysis_results.copy()

    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 停止线程池
            self.executor.shutdown(wait=False)
            event.accept()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"关闭分析面板失败: {str(e)}")
            event.accept()
