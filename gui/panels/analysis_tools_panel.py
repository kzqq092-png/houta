"""
分析工具面板模块

包含右侧分析工具面板的完整实现
"""

import uuid
import traceback
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QComboBox,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QListWidget, QTextEdit,
    QGroupBox, QGridLayout, QProgressBar, QMessageBox, QFileDialog
)
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
from .base_analysis_panel import BaseAnalysisPanel


class AnalysisToolsPanel(BaseAnalysisPanel):
    """Analysis tools panel for the right side of the main window"""

    # 定义信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    data_requested = pyqtSignal(dict)  # 数据请求信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, parent=None):
        """初始化分析工具面板"""
        super().__init__(parent)

        # 初始化属性
        self.current_strategy = "均线策略"
        self.current_params = {}
        self.analysis_results = {}
        self.batch_tasks = []
        self.batch_results = []
        self.last_trace_id = None

        # 初始化UI和数据
        self.init_ui()
        self.init_data()
        self.connect_signals()

    def init_ui(self):
        """初始化用户界面"""
        try:
            # 使用父类已经创建的主布局，而不是重新创建
            # self.main_layout 已经在 BaseAnalysisPanel.init_base_ui() 中创建

            # 创建标签页控件
            self.tab_widget = QTabWidget()
            self.main_layout.addWidget(self.tab_widget)

            # 创建各个标签页
            self.create_strategy_tab()
            self.create_batch_analysis_tab()
            self.create_ai_strategy_tab()
            self.create_ai_optimizer_tab()
            self.create_ai_diagnosis_tab()
            self.create_scheduler_tab()

            # 创建控制按钮
            self.create_control_buttons()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化分析工具面板UI失败: {str(e)}")

    def create_strategy_tab(self):
        """创建策略分析标签页"""
        try:
            strategy_widget = QWidget()
            layout = QVBoxLayout(strategy_widget)

            # 策略选择组
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QGridLayout(strategy_group)

            # 策略下拉框
            strategy_layout.addWidget(QLabel("策略:"), 0, 0)
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"
            ])
            self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
            strategy_layout.addWidget(self.strategy_combo, 0, 1)

            layout.addWidget(strategy_group)

            # 参数设置组
            self.params_group = QGroupBox("参数设置")
            self.params_layout = QGridLayout(self.params_group)
            layout.addWidget(self.params_group)

            # 回测设置组
            backtest_group = QGroupBox("回测设置")
            backtest_layout = QGridLayout(backtest_group)

            backtest_layout.addWidget(QLabel("起始资金:"), 0, 0)
            self.initial_capital = QSpinBox()
            self.initial_capital.setRange(10000, 10000000)
            self.initial_capital.setValue(100000)
            self.initial_capital.setSuffix(" 元")
            backtest_layout.addWidget(self.initial_capital, 0, 1)

            backtest_layout.addWidget(QLabel("手续费率:"), 1, 0)
            self.commission_rate = QDoubleSpinBox()
            self.commission_rate.setRange(0.0001, 0.01)
            self.commission_rate.setValue(0.0003)
            self.commission_rate.setDecimals(4)
            self.commission_rate.setSuffix("%")
            backtest_layout.addWidget(self.commission_rate, 1, 1)

            layout.addWidget(backtest_group)

            # 结果显示区域
            self.results_text = QTextEdit()
            self.results_text.setMaximumHeight(200)
            layout.addWidget(QLabel("分析结果:"))
            layout.addWidget(self.results_text)

            # 更新参数显示
            self.update_parameters()

            self.tab_widget.addTab(strategy_widget, "策略分析")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建策略标签页失败: {str(e)}")

    def create_batch_analysis_tab(self):
        """创建批量分析标签页"""
        try:
            batch_widget = QWidget()
            layout = QVBoxLayout(batch_widget)

            # 批量策略选择
            strategy_group = QGroupBox("批量策略选择")
            strategy_layout = QVBoxLayout(strategy_group)

            self.batch_strategy_list = QListWidget()
            self.batch_strategy_list.setSelectionMode(QListWidget.MultiSelection)
            self.batch_strategy_list.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"
            ])
            strategy_layout.addWidget(self.batch_strategy_list)

            layout.addWidget(strategy_group)

            # 任务队列
            queue_group = QGroupBox("任务队列")
            queue_layout = QVBoxLayout(queue_group)

            self.task_queue_table = QTableWidget()
            self.task_queue_table.setColumnCount(4)
            self.task_queue_table.setHorizontalHeaderLabels(["股票代码", "策略", "状态", "进度"])
            queue_layout.addWidget(self.task_queue_table)

            # 队列控制按钮
            queue_buttons = QHBoxLayout()
            self.start_batch_btn = QPushButton("开始批量分析")
            self.start_batch_btn.clicked.connect(self.start_batch_analysis)
            queue_buttons.addWidget(self.start_batch_btn)

            self.cancel_batch_btn = QPushButton("取消批量分析")
            self.cancel_batch_btn.clicked.connect(self.cancel_batch_backtest)
            queue_buttons.addWidget(self.cancel_batch_btn)

            queue_layout.addLayout(queue_buttons)
            layout.addWidget(queue_group)

            # 结果统计
            stats_group = QGroupBox("结果统计")
            stats_layout = QGridLayout(stats_group)

            self.total_tasks_label = QLabel("总任务数: 0")
            self.completed_tasks_label = QLabel("已完成: 0")
            self.success_rate_label = QLabel("成功率: 0%")

            stats_layout.addWidget(self.total_tasks_label, 0, 0)
            stats_layout.addWidget(self.completed_tasks_label, 0, 1)
            stats_layout.addWidget(self.success_rate_label, 0, 2)

            layout.addWidget(stats_group)

            self.tab_widget.addTab(batch_widget, "批量分析")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建批量分析标签页失败: {str(e)}")

    def create_ai_strategy_tab(self):
        """创建AI策略标签页"""
        try:
            ai_widget = QWidget()
            layout = QVBoxLayout(ai_widget)

            # AI策略推荐
            ai_group = QGroupBox("AI策略推荐")
            ai_layout = QVBoxLayout(ai_group)

            # 推荐按钮
            self.ai_recommend_btn = QPushButton("获取AI策略推荐")
            self.ai_recommend_btn.clicked.connect(self.on_ai_strategy_recommend)
            ai_layout.addWidget(self.ai_recommend_btn)

            # 推荐结果表格
            self.ai_strategy_table = QTableWidget()
            self.ai_strategy_table.setColumnCount(3)
            self.ai_strategy_table.setHorizontalHeaderLabels(["策略", "推荐理由", "置信度"])
            ai_layout.addWidget(self.ai_strategy_table)

            layout.addWidget(ai_group)

            # AI选股
            stock_group = QGroupBox("AI选股")
            stock_layout = QVBoxLayout(stock_group)

            self.ai_stock_btn = QPushButton("AI智能选股")
            self.ai_stock_btn.clicked.connect(self.on_ai_stock_select)
            stock_layout.addWidget(self.ai_stock_btn)

            self.ai_stock_result_table = QTableWidget()
            self.ai_stock_result_table.setColumnCount(3)
            self.ai_stock_result_table.setHorizontalHeaderLabels(["股票代码", "推荐理由", "评分"])
            stock_layout.addWidget(self.ai_stock_result_table)

            layout.addWidget(stock_group)

            self.tab_widget.addTab(ai_widget, "AI策略")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建AI策略标签页失败: {str(e)}")

    def create_ai_optimizer_tab(self):
        """创建AI优化器标签页"""
        try:
            optimizer_widget = QWidget()
            layout = QVBoxLayout(optimizer_widget)

            # 参数优化设置
            optimizer_group = QGroupBox("AI参数优化")
            optimizer_layout = QGridLayout(optimizer_group)

            optimizer_layout.addWidget(QLabel("目标策略:"), 0, 0)
            self.optimizer_strategy_combo = QComboBox()
            self.optimizer_strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"
            ])
            optimizer_layout.addWidget(self.optimizer_strategy_combo, 0, 1)

            optimizer_layout.addWidget(QLabel("优化目标:"), 1, 0)
            self.optimization_target = QComboBox()
            self.optimization_target.addItems(["年化收益率", "夏普比率", "最大回撤", "胜率"])
            optimizer_layout.addWidget(self.optimization_target, 1, 1)

            optimizer_layout.addWidget(QLabel("优化轮数:"), 2, 0)
            self.optimization_rounds = QSpinBox()
            self.optimization_rounds.setRange(10, 1000)
            self.optimization_rounds.setValue(100)
            optimizer_layout.addWidget(self.optimization_rounds, 2, 1)

            # 开始优化按钮
            self.start_optimizer_btn = QPushButton("开始AI优化")
            self.start_optimizer_btn.clicked.connect(self.on_ai_optimizer_run)
            optimizer_layout.addWidget(self.start_optimizer_btn, 3, 0, 1, 2)

            layout.addWidget(optimizer_group)

            # 优化结果
            result_group = QGroupBox("优化结果")
            result_layout = QVBoxLayout(result_group)

            self.optimizer_result_table = QTableWidget()
            self.optimizer_result_table.setColumnCount(4)
            self.optimizer_result_table.setHorizontalHeaderLabels(["参数组合", "年化收益", "最大回撤", "夏普比率"])
            result_layout.addWidget(self.optimizer_result_table)

            layout.addWidget(result_group)

            self.tab_widget.addTab(optimizer_widget, "AI优化器")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建AI优化器标签页失败: {str(e)}")

    def create_ai_diagnosis_tab(self):
        """创建AI诊断标签页"""
        try:
            diagnosis_widget = QWidget()
            layout = QVBoxLayout(diagnosis_widget)

            # 诊断设置
            diagnosis_group = QGroupBox("AI策略诊断")
            diagnosis_layout = QGridLayout(diagnosis_group)

            diagnosis_layout.addWidget(QLabel("诊断策略:"), 0, 0)
            self.diagnosis_strategy_combo = QComboBox()
            self.diagnosis_strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略"
            ])
            diagnosis_layout.addWidget(self.diagnosis_strategy_combo, 0, 1)

            diagnosis_layout.addWidget(QLabel("诊断维度:"), 1, 0)
            self.diagnosis_dimension = QComboBox()
            self.diagnosis_dimension.addItems(["收益分析", "风险分析", "参数敏感性", "市场适应性"])
            diagnosis_layout.addWidget(self.diagnosis_dimension, 1, 1)

            # 开始诊断按钮
            self.start_diagnosis_btn = QPushButton("开始AI诊断")
            self.start_diagnosis_btn.clicked.connect(self.on_ai_diagnosis_run)
            diagnosis_layout.addWidget(self.start_diagnosis_btn, 2, 0, 1, 2)

            layout.addWidget(diagnosis_group)

            # 诊断结果
            result_group = QGroupBox("诊断报告")
            result_layout = QVBoxLayout(result_group)

            self.diagnosis_result_text = QTextEdit()
            self.diagnosis_result_text.setMaximumHeight(300)
            result_layout.addWidget(self.diagnosis_result_text)

            layout.addWidget(result_group)

            self.tab_widget.addTab(diagnosis_widget, "AI诊断")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建AI诊断标签页失败: {str(e)}")

    def create_scheduler_tab(self):
        """创建定时任务标签页"""
        try:
            scheduler_widget = QWidget()
            layout = QVBoxLayout(scheduler_widget)

            # 定时任务设置
            scheduler_group = QGroupBox("定时任务管理")
            scheduler_layout = QVBoxLayout(scheduler_group)

            # 任务列表
            self.scheduler_table = QTableWidget()
            self.scheduler_table.setColumnCount(4)
            self.scheduler_table.setHorizontalHeaderLabels(["任务名称", "执行时间", "状态", "操作"])
            scheduler_layout.addWidget(self.scheduler_table)

            # 任务控制按钮
            scheduler_buttons = QHBoxLayout()

            self.add_job_btn = QPushButton("添加任务")
            self.add_job_btn.clicked.connect(self.add_scheduler_job)
            scheduler_buttons.addWidget(self.add_job_btn)

            self.pause_all_btn = QPushButton("暂停所有")
            self.pause_all_btn.clicked.connect(self.pause_all_tasks)
            scheduler_buttons.addWidget(self.pause_all_btn)

            self.resume_all_btn = QPushButton("恢复所有")
            self.resume_all_btn.clicked.connect(self.resume_all_tasks)
            scheduler_buttons.addWidget(self.resume_all_btn)

            scheduler_layout.addLayout(scheduler_buttons)
            layout.addWidget(scheduler_group)

            self.tab_widget.addTab(scheduler_widget, "定时任务")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建定时任务标签页失败: {str(e)}")

    def create_control_buttons(self):
        """创建控制按钮"""
        try:
            # 创建底部控制按钮布局
            control_layout = QHBoxLayout()

            # 分析按钮
            self.analyze_btn = QPushButton("开始分析")
            self.analyze_btn.clicked.connect(self.on_tools_panel_analyze)
            control_layout.addWidget(self.analyze_btn)

            # 导出按钮
            self.export_btn = QPushButton("导出结果")
            self.export_btn.clicked.connect(self.export_batch_results)
            control_layout.addWidget(self.export_btn)

            # 刷新按钮
            self.refresh_btn = QPushButton("刷新策略")
            self.refresh_btn.clicked.connect(self.refresh_strategy_list)
            control_layout.addWidget(self.refresh_btn)

            # 添加到主布局
            self.layout().addLayout(control_layout)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建控制按钮失败: {str(e)}")

    def init_data(self):
        """初始化数据"""
        try:
            # 初始化策略列表
            self.refresh_strategy_list()

            # 初始化批量任务列表
            self.batch_tasks = []
            self.batch_results = []

            if self.log_manager:
                self.log_manager.info("分析工具面板数据初始化完成")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化分析工具面板数据失败: {str(e)}")

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接策略变化信号
            if hasattr(self, 'strategy_combo'):
                self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)

            # 连接参数变化信号
            if hasattr(self, 'initial_capital'):
                self.initial_capital.valueChanged.connect(self.on_param_changed)
            if hasattr(self, 'commission_rate'):
                self.commission_rate.valueChanged.connect(self.on_param_changed)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"连接信号失败: {str(e)}")

    def on_strategy_changed(self, strategy: str):
        """策略变化处理"""
        try:
            self.current_strategy = strategy
            self.update_parameters()

            if self.log_manager:
                self.log_manager.info(f"策略变更为: {strategy}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理策略变化失败: {str(e)}")

    def on_param_changed(self):
        """参数变化处理"""
        try:
            # 更新当前参数
            self.current_params = self.get_current_parameters()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"处理参数变化失败: {str(e)}")

    def update_parameters(self):
        """更新参数显示"""
        try:
            # 清除现有参数控件
            for i in reversed(range(self.params_layout.count())):
                child = self.params_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)

            # 根据策略添加参数控件
            strategy_params = self.get_strategy_parameters(self.current_strategy)

            row = 0
            for param_name, param_config in strategy_params.items():
                # 添加参数标签
                self.params_layout.addWidget(QLabel(f"{param_name}:"), row, 0)

                # 根据参数类型创建控件
                if param_config['type'] == 'int':
                    widget = QSpinBox()
                    widget.setRange(param_config.get('min', 1), param_config.get('max', 100))
                    widget.setValue(param_config.get('default', 10))
                elif param_config['type'] == 'float':
                    widget = QDoubleSpinBox()
                    widget.setRange(param_config.get('min', 0.1), param_config.get('max', 10.0))
                    widget.setValue(param_config.get('default', 1.0))
                    widget.setDecimals(2)
                else:
                    widget = QComboBox()
                    widget.addItems(param_config.get('options', ['选项1', '选项2']))

                self.params_layout.addWidget(widget, row, 1)
                self.add_param_widget(param_name, widget)

                row += 1

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新参数显示失败: {str(e)}")

    def get_strategy_parameters(self, strategy: str) -> Dict[str, Any]:
        """获取策略参数配置"""
        try:
            # 策略参数配置
            params_config = {
                "均线策略": {
                    "短期均线": {"type": "int", "min": 5, "max": 30, "default": 10},
                    "长期均线": {"type": "int", "min": 20, "max": 100, "default": 30}
                },
                "MACD策略": {
                    "快线周期": {"type": "int", "min": 8, "max": 20, "default": 12},
                    "慢线周期": {"type": "int", "min": 20, "max": 35, "default": 26},
                    "信号线周期": {"type": "int", "min": 5, "max": 15, "default": 9}
                },
                "RSI策略": {
                    "RSI周期": {"type": "int", "min": 10, "max": 30, "default": 14},
                    "超买线": {"type": "int", "min": 70, "max": 90, "default": 80},
                    "超卖线": {"type": "int", "min": 10, "max": 30, "default": 20}
                },
                "布林带策略": {
                    "周期": {"type": "int", "min": 15, "max": 30, "default": 20},
                    "标准差倍数": {"type": "float", "min": 1.5, "max": 3.0, "default": 2.0}
                },
                "KDJ策略": {
                    "K周期": {"type": "int", "min": 5, "max": 15, "default": 9},
                    "D周期": {"type": "int", "min": 2, "max": 5, "default": 3},
                    "J周期": {"type": "int", "min": 2, "max": 5, "default": 3}
                }
            }

            return params_config.get(strategy, {})

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取策略参数失败: {str(e)}")
            return {}

    def get_current_parameters(self) -> Dict[str, Any]:
        """获取当前参数值"""
        try:
            params = {}

            # 获取策略参数
            for param_name, widget in self.param_widgets.items():
                if hasattr(widget, 'value'):
                    params[param_name] = widget.value()
                elif hasattr(widget, 'currentText'):
                    params[param_name] = widget.currentText()

            # 获取回测参数
            if hasattr(self, 'initial_capital'):
                params['initial_capital'] = self.initial_capital.value()
            if hasattr(self, 'commission_rate'):
                params['commission_rate'] = self.commission_rate.value()

            return params

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取当前参数失败: {str(e)}")
            return {}

    def perform_analysis(self):
        """执行分析 - 重写基类方法"""
        try:
            # 获取当前参数
            params = self.get_current_parameters()

            # 模拟分析过程
            self.set_status_message("正在执行策略分析...")

            # 这里应该调用实际的分析逻辑
            # 暂时使用模拟结果
            results = {
                "strategy": self.current_strategy,
                "parameters": params,
                "annual_return": 0.15,
                "max_drawdown": 0.08,
                "sharpe_ratio": 1.2,
                "win_rate": 0.65
            }

            # 更新结果显示
            self.update_results(results)

            # 发送分析完成信号
            self.analysis_completed.emit(results)

            self.set_status_message("策略分析完成")

        except Exception as e:
            error_msg = f"执行分析失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def export_results(self, file_path: str):
        """导出结果 - 重写基类方法"""
        try:
            import json
            import pandas as pd

            # 准备导出数据
            export_data = {
                "strategy": self.current_strategy,
                "parameters": self.current_params,
                "results": self.analysis_results,
                "batch_results": self.batch_results
            }

            # 根据文件扩展名选择导出格式
            if file_path.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            elif file_path.endswith('.xlsx'):
                # 导出为Excel
                with pd.ExcelWriter(file_path) as writer:
                    if self.batch_results:
                        df = pd.DataFrame(self.batch_results)
                        df.to_excel(writer, sheet_name='批量分析结果', index=False)
            else:
                # 默认导出为CSV
                if self.batch_results:
                    df = pd.DataFrame(self.batch_results)
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')

        except Exception as e:
            raise Exception(f"导出结果失败: {str(e)}")

    # 以下是各种事件处理方法的简化实现
    def on_tools_panel_analyze(self):
        """工具面板分析按钮点击"""
        self.perform_analysis()

    def start_batch_analysis(self):
        """开始批量分析"""
        try:
            self.set_status_message("开始批量分析...")
            # 实现批量分析逻辑

        except Exception as e:
            self.error_occurred.emit(f"批量分析失败: {str(e)}")

    def cancel_batch_backtest(self):
        """取消批量回测"""
        try:
            self.set_status_message("取消批量分析")

        except Exception as e:
            self.error_occurred.emit(f"取消批量分析失败: {str(e)}")

    def on_ai_strategy_recommend(self):
        """AI策略推荐"""
        try:
            self.set_status_message("获取AI策略推荐...")
            # 实现AI策略推荐逻辑

        except Exception as e:
            self.error_occurred.emit(f"AI策略推荐失败: {str(e)}")

    def on_ai_stock_select(self):
        """AI选股"""
        try:
            self.set_status_message("执行AI选股...")
            # 实现AI选股逻辑

        except Exception as e:
            self.error_occurred.emit(f"AI选股失败: {str(e)}")

    def on_ai_optimizer_run(self):
        """运行AI优化器"""
        try:
            self.set_status_message("运行AI参数优化...")
            # 实现AI优化逻辑

        except Exception as e:
            self.error_occurred.emit(f"AI优化失败: {str(e)}")

    def on_ai_diagnosis_run(self):
        """运行AI诊断"""
        try:
            self.set_status_message("执行AI策略诊断...")
            # 实现AI诊断逻辑

        except Exception as e:
            self.error_occurred.emit(f"AI诊断失败: {str(e)}")

    def add_scheduler_job(self):
        """添加定时任务"""
        try:
            self.set_status_message("添加定时任务...")
            # 实现添加定时任务逻辑

        except Exception as e:
            self.error_occurred.emit(f"添加定时任务失败: {str(e)}")

    def pause_all_tasks(self):
        """暂停所有任务"""
        try:
            self.set_status_message("暂停所有任务")

        except Exception as e:
            self.error_occurred.emit(f"暂停任务失败: {str(e)}")

    def resume_all_tasks(self):
        """恢复所有任务"""
        try:
            self.set_status_message("恢复所有任务")

        except Exception as e:
            self.error_occurred.emit(f"恢复任务失败: {str(e)}")

    def export_batch_results(self):
        """导出批量结果"""
        try:
            if not self.batch_results:
                QMessageBox.information(self, "提示", "没有可导出的批量分析结果")
                return

            self.on_export()

        except Exception as e:
            self.error_occurred.emit(f"导出批量结果失败: {str(e)}")

    def refresh_strategy_list(self):
        """刷新策略列表"""
        try:
            # 从策略管理系统获取最新策略列表
            from core.strategy import list_available_strategies

            available_strategies = list_available_strategies()

            if available_strategies:
                # 更新策略下拉框
                if hasattr(self, 'strategy_combo'):
                    self.strategy_combo.clear()
                    self.strategy_combo.addItems(available_strategies)

                # 更新批量策略列表
                if hasattr(self, 'batch_strategy_list'):
                    self.batch_strategy_list.clear()
                    self.batch_strategy_list.addItems(available_strategies)

                # 更新AI相关策略下拉框
                for combo in [getattr(self, attr, None) for attr in
                              ['optimizer_strategy_combo', 'diagnosis_strategy_combo']]:
                    if combo:
                        combo.clear()
                        combo.addItems(available_strategies)

                self.set_status_message(f"策略列表已刷新，共 {len(available_strategies)} 个策略")

            else:
                self.set_status_message("未找到可用策略", error=True)

        except Exception as e:
            error_msg = f"刷新策略列表失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def update_results(self, results: Dict[str, Any]):
        """更新结果显示"""
        try:
            self.analysis_results = results

            # 更新结果文本显示
            if hasattr(self, 'results_text'):
                result_text = f"""
策略: {results.get('strategy', 'N/A')}
年化收益率: {results.get('annual_return', 0):.2%}
最大回撤: {results.get('max_drawdown', 0):.2%}
夏普比率: {results.get('sharpe_ratio', 0):.2f}
胜率: {results.get('win_rate', 0):.2%}
                """.strip()
                self.results_text.setPlainText(result_text)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新结果显示失败: {str(e)}")

    def get_selected_strategy(self):
        """获取当前选择的策略"""
        return self.strategy_combo.currentText() if hasattr(self, 'strategy_combo') else None

    def get_selected_batch_strategies(self):
        """获取批量选择的策略列表"""
        if not hasattr(self, 'batch_strategy_list'):
            return []

        selected_items = self.batch_strategy_list.selectedItems()
        return [item.text() for item in selected_items]
