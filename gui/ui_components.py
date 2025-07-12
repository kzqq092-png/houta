"""
UI components for the trading system

This module contains reusable UI components for the trading system.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QStatusBar, QToolBar, QMenuBar, QMenu, QAction,
    QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QGridLayout, QToolTip, QListWidget, QTableWidget, QTableWidgetItem, QListWidgetItem, QDialog, QCheckBox, QHeaderView, QInputDialog, QAbstractItemView, QTreeWidget, QTreeWidgetItem, QCompleter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QObject, QPointF
from PyQt5.QtGui import QIcon, QColor, QBrush
import pandas as pd
import psutil
from datetime import datetime
import traceback
from core.logger import LogManager
from gui.widgets.trading_widget import TradingWidget
from utils.config_types import LoggingConfig
from typing import Optional, Dict, Any
import csv
import plotly.figure_factory as ff
import plotly.graph_objs as go
from PyQt5.QtWebEngineWidgets import QWebEngineView
import tempfile
import os
import time
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from async_manager import AsyncManager
import threading
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
import matplotlib.pyplot as plt
import io
import base64
import random
import requests
from PyQt5.QtWidgets import QApplication
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid


class BaseAnalysisPanel(QWidget):
    """基础分析面板，统一参数设置、导出、日志、信号、按钮等通用功能"""
    # 通用信号
    analysis_completed = pyqtSignal(dict)
    data_requested = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    # 全局自定义指标注册表（类变量）
    _global_custom_indicators = {}
    # 全局联动信号（类变量）
    custom_signal = pyqtSignal(str, object)  # (事件名, 数据)

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()
        self.param_widgets: Dict[str, Any] = {}
        self.metric_labels: Dict[str, QLabel] = {}
        self.init_base_ui()
        self.init_base_signals()

    @classmethod
    def register_custom_indicator(cls, name: str, func):
        """
        全局注册自定义指标
        Args:
            name: 指标名称
            func: 计算函数
        """
        cls._global_custom_indicators[name] = func

    @classmethod
    def get_custom_indicator(cls, name: str):
        """
        获取全局自定义指标
        Args:
            name: 指标名称
        Returns:
            func: 计算函数或None
        """
        return cls._global_custom_indicators.get(name)

    def emit_custom_signal(self, event: str, data: object):
        """
        发送全局联动信号
        Args:
            event: 事件名
            data: 任意数据
        """
        BaseAnalysisPanel.custom_signal.emit(event, data)

    def connect_custom_signal(self, slot):
        """
        连接全局联动信号
        Args:
            slot: 槽函数，参数(event, data)
        """
        BaseAnalysisPanel.custom_signal.connect(slot)

    def init_base_ui(self):
        """初始化通用UI区域（参数、导出、按钮等）"""
        self.main_layout = QVBoxLayout(self)
        # 参数设置区域（子类可扩展）
        self.params_group = QGroupBox("参数设置")
        self.params_layout = QGridLayout()
        self.params_group.setLayout(self.params_layout)
        self.main_layout.addWidget(self.params_group)
        # 控制按钮区域
        self.button_layout = QHBoxLayout()
        self.analyze_button = QPushButton("开始回测分析")
        self.export_button = QPushButton("导出回测结果")
        self.button_layout.addWidget(self.analyze_button)
        self.button_layout.addWidget(self.export_button)
        self.main_layout.addLayout(self.button_layout)

    def init_base_signals(self):
        self.analyze_button.clicked.connect(self.on_base_panel_analyze)
        self.export_button.clicked.connect(self.on_export)

    def on_base_panel_analyze(self):
        """重定向到trading_widget的标准on_analyze实现，避免重复。"""
        if hasattr(self, 'trading_widget') and isinstance(self.trading_widget, TradingWidget):
            # 若有参数控件，先同步参数
            if hasattr(self, 'param_controls') and hasattr(self.trading_widget, 'set_parameters'):
                params = {k: v.value() if hasattr(v, 'value') else v.currentText() if hasattr(
                    v, 'currentText') else v for k, v in self.param_controls.items()}
                self.trading_widget.set_parameters(params)
            self.trading_widget.on_analyze()
        else:
            # 兼容未集成trading_widget的情况，直接记录错误并安全返回
            if hasattr(self, 'log_manager'):
                self.log_manager.error(
                    "分析启动失败: 未集成trading_widget，无法调用on_analyze()。")
        # 不再尝试super()，避免异常

    def on_export(self):
        """统一导出逻辑，子类可扩展"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            if file_path:
                # 子类实现具体导出内容
                self.log_manager.info(f"结果已导出到: {file_path}")
                QMessageBox.information(self, "导出成功", f"结果已导出到: {file_path}")
        except Exception as e:
            self.log_manager.error(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
            self.error_occurred.emit(f"导出失败: {str(e)}")

    def add_param_widget(self, name: str, widget: QWidget):
        self.param_widgets[name] = widget
        row = self.params_layout.rowCount()
        self.params_layout.addWidget(QLabel(name), row, 0)
        self.params_layout.addWidget(widget, row, 1)
        # 增加实时校验信号
        if hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(self._on_param_widget_changed)
        elif hasattr(widget, 'editingFinished'):
            widget.editingFinished.connect(self._on_param_widget_changed)
        # 增加气泡提示
        widget.setToolTip("")

    def _on_param_widget_changed(self):
        # 仅做UI提示，不做业务校验，参数校验统一由 TradingWidget.on_analyze 实现
        self.set_status_message("参数已变更", error=False)
        for name, widget in self.param_widgets.items():
            widget.setToolTip("")

    def add_metric_label(self, name: str, label: QLabel):
        self.metric_labels[name] = label

    def validate_params(self):
        """
        已废弃：参数校验统一由 TradingWidget.on_analyze 实现。
        """
        return True, ""

    def set_status_message(self, message: str, error: bool = False):
        """
        在主界面状态栏显示提示信息，error为True时高亮显示
        """
        if hasattr(self.parent(), 'statusBar'):
            bar = self.parent().statusBar()
            if error:
                bar.setStyleSheet("color: red;")
            else:
                bar.setStyleSheet("")
            bar.showMessage(message, 5000)
        # 兼容自带status_label
        elif hasattr(self, 'status_label'):
            self.status_label.setText(message)
            if error:
                self.status_label.setStyleSheet("color: red;")
            else:
                self.status_label.setStyleSheet("")

    def __del__(self):
        # 防止QLabel重复删除导致wrapped C/C++ object of type QLabel has been deleted
        if hasattr(self, 'metric_labels'):
            self.metric_labels.clear()


class AnalysisToolsPanel(BaseAnalysisPanel):
    """Analysis tools panel for the right side of the main window"""

    # 定义信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    data_requested = pyqtSignal(dict)  # 数据请求信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, parent=None):
        """初始化UI组件

        Args:
            parent: 父窗口
        """
        # 1. 先置空关键属性，防止部分流程未初始化时报错
        self.strategy_combo = None
        self.performance_metrics = {}
        self.backtest_widgets = {}
        self.data_cache = {}
        self.current_strategy = None
        self.default_params = {}
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.step_list = QListWidget()
        self.step_status = {}
        self.async_manager = AsyncManager(max_workers=8)
        self._batch_futures = []
        self._batch_cancelled = False
        self._batch_pause_events = []
        try:
            # 初始化日志管理器
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                self.log_manager = LogManager()

            self.log_manager.info("初始化策略回测UI组件")
            super().__init__(parent)
            # 集成TradingWidget实例（仅作分析逻辑调用，不显示UI）
            self.trading_widget = TradingWidget()
            # 初始化UI
            try:
                self.init_ui()
            except Exception as e:
                self.log_manager.error(f"init_ui异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            # 初始化数据
            try:
                self.init_data()
            except Exception as e:
                self.log_manager.error(f"init_data异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            # 连接信号
            try:
                self.connect_signals()
            except Exception as e:
                self.log_manager.error(f"connect_signals异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            self.log_manager.info("分析工具面板初始化完成")
            # 监听TradingWidget的analysis_progress信号
            if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'analysis_progress'):
                self.trading_widget.analysis_progress.connect(
                    self.on_analysis_progress)
        except Exception as e:
            print(f"初始化UI组件失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化UI组件失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    def init_ui(self):
        """初始化UI，合并所有功能区，确保所有控件都被正确初始化"""
        try:
            self.log_manager.info("初始化策略回测区域")
            layout = self.main_layout  # 用父类的主布局
            # 策略选择区域
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QVBoxLayout()
            self.strategy_combo = QComboBox()

            # 使用新的策略管理系统获取策略列表
            try:
                from core.strategy import list_available_strategies
                available_strategies = list_available_strategies()
                if available_strategies:
                    self.strategy_combo.addItems(available_strategies)
                    self.log_manager.info(
                        f"从策略管理系统加载了 {len(available_strategies)} 个策略")
                else:
                    # 如果新系统没有策略，使用默认策略列表
                    default_strategies = [
                        '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
                        'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
                        'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                        'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略'
                    ]
                    self.strategy_combo.addItems(default_strategies)
                    self.log_manager.warning("策略管理系统未返回策略，使用默认策略列表")
            except Exception as e:
                # 如果导入失败，使用默认策略列表
                default_strategies = [
                    '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
                    'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
                    'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                    'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略'
                ]
                self.strategy_combo.addItems(default_strategies)
                self.log_manager.error(f"加载策略管理系统失败，使用默认策略列表: {str(e)}")

            strategy_layout.addWidget(self.strategy_combo)
            strategy_group.setLayout(strategy_layout)
            layout.addWidget(strategy_group)
            # 回测设置区域
            backtest_group = QGroupBox("回测设置")
            backtest_layout = QGridLayout()
            self.backtest_widgets = {}
            row = 0
            for setting in ['初始资金', '手续费率', '滑点']:
                label = QLabel(setting)
                spin = QDoubleSpinBox()
                spin.setRange(0, 1000000)
                spin.setValue(100000 if setting == '初始资金' else 0.0003)
                backtest_layout.addWidget(label, row, 0)
                backtest_layout.addWidget(spin, row, 1)
                self.backtest_widgets[setting] = spin
                row += 1
            backtest_group.setLayout(backtest_layout)
            layout.addWidget(backtest_group)
            # 分割线
            line = QLabel()
            line.setFixedHeight(2)
            line.setStyleSheet("background:#e0e0e0;")
            layout.addWidget(line)
            # 批量回测/AI Tab
            self.tab_widget = QTabWidget()
            # 单次回测Tab
            self.single_tab = QWidget()
            single_layout = QVBoxLayout(self.single_tab)
            # 可扩展单次回测内容
            self.tab_widget.addTab(self.single_tab, "单次回测")
            # 批量回测Tab
            self.batch_tab = QWidget()
            batch_layout = QVBoxLayout(self.batch_tab)
            self.batch_stock_input = QLineEdit()
            self.batch_stock_input.setPlaceholderText("输入多个股票代码，用逗号分隔")
            batch_layout.addWidget(QLabel("批量股票代码："))
            batch_layout.addWidget(self.batch_stock_input)
            self.batch_strategy_list = QListWidget()
            self.batch_strategy_list.setSelectionMode(
                QListWidget.MultiSelection)

            # 使用新的策略管理系统获取策略列表
            try:
                available_strategies = list_available_strategies()
                if available_strategies:
                    for strategy in available_strategies:
                        self.batch_strategy_list.addItem(strategy)
                    self.log_manager.info(
                        f"批量策略列表加载了 {len(available_strategies)} 个策略")
                else:
                    # 如果新系统没有策略，使用默认策略列表
                    default_strategies = [
                        '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
                        'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
                        'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                        'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略'
                    ]
                    for strategy in default_strategies:
                        self.batch_strategy_list.addItem(strategy)
            except Exception as e:
                # 如果导入失败，使用默认策略列表
                default_strategies = [
                    '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
                    'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
                    'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                    'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略'
                ]
                for strategy in default_strategies:
                    self.batch_strategy_list.addItem(strategy)
                self.log_manager.error(f"批量策略列表加载失败，使用默认策略: {str(e)}")
            batch_layout.addWidget(QLabel("批量策略选择："))
            batch_layout.addWidget(self.batch_strategy_list)
            self.param_grid_table = QTableWidget(0, 3)
            self.param_grid_table.setHorizontalHeaderLabels(
                ["参数名", "起始值", "终止值"])
            batch_layout.addWidget(QLabel("参数范围设置（可选）："))
            batch_layout.addWidget(self.param_grid_table)
            add_param_btn = QPushButton("添加参数")
            add_param_btn.clicked.connect(
                lambda: self.param_grid_table.insertRow(self.param_grid_table.rowCount()))
            batch_layout.addWidget(add_param_btn)
            self.run_batch_btn = QPushButton("一键批量回测")
            batch_layout.addWidget(self.run_batch_btn)
            self.batch_progress = QProgressBar()
            batch_layout.addWidget(self.batch_progress)
            self.batch_result_table = QTableWidget()
            self.batch_result_table.setColumnCount(12)
            self.batch_result_table.setHorizontalHeaderLabels([
                "股票代码", "策略", "参数组合", "年化收益率", "最大回撤", "夏普比率", "卡玛比率", "索提诺比率", "信息比率", "胜率", "盈亏比", "最优标记"])
            batch_layout.addWidget(self.batch_result_table)
            self.export_batch_btn = QPushButton("导出全部回测结果")
            batch_layout.addWidget(self.export_batch_btn)
            self.export_failed_btn = QPushButton("导出失败日志")
            self.export_failed_btn.clicked.connect(self.export_failed_tasks)
            batch_layout.addWidget(self.export_failed_btn)
            self.export_all_btn = QPushButton("导出全部结果")
            self.export_all_btn.clicked.connect(self.export_all_results)
            batch_layout.addWidget(self.export_all_btn)
            self.group_compare_btn = QPushButton("分组对比")
            self.group_compare_btn.clicked.connect(self.show_group_compare)
            batch_layout.addWidget(self.group_compare_btn)
            self.batch_tab.setLayout(batch_layout)
            self.tab_widget.addTab(self.batch_tab, "批量回测/参数调优")
            # AI Tab
            self.ai_tab_widget = QTabWidget()
            self.ai_stock_tab = QWidget()
            ai_stock_layout = QVBoxLayout(self.ai_stock_tab)
            self.ai_stock_input = QTextEdit()
            self.ai_stock_input.setPlaceholderText(
                "请输入选股需求或因子描述（如：高ROE、低估值、强势资金流等，或直接用自然语言描述）")
            ai_stock_layout.addWidget(QLabel("AI智能选股（支持自然语言/参数化因子输入）："))
            ai_stock_layout.addWidget(self.ai_stock_input)
            self.ai_stock_run_btn = QPushButton("一键AI选股")
            ai_stock_layout.addWidget(self.ai_stock_run_btn)
            self.ai_stock_result_table = QTableWidget()
            ai_stock_layout.addWidget(self.ai_stock_result_table)
            self.ai_stock_export_btn = QPushButton("导出选股结果")
            ai_stock_layout.addWidget(self.ai_stock_export_btn)
            self.ai_tab_widget.addTab(self.ai_stock_tab, "AI智能选股")
            self.ai_strategy_tab = QWidget()
            ai_strategy_layout = QVBoxLayout(self.ai_strategy_tab)
            self.ai_strategy_input = QTextEdit()
            self.ai_strategy_input.setPlaceholderText("请输入策略描述或自然语言需求")
            ai_strategy_layout.addWidget(QLabel("AI策略生成："))
            ai_strategy_layout.addWidget(self.ai_strategy_input)
            self.ai_strategy_run_btn = QPushButton("一键生成策略")
            ai_strategy_layout.addWidget(self.ai_strategy_run_btn)
            self.ai_strategy_result = QTextEdit()
            self.ai_strategy_result.setReadOnly(True)
            ai_strategy_layout.addWidget(self.ai_strategy_result)
            self.ai_tab_widget.addTab(self.ai_strategy_tab, "AI策略生成")
            self.tab_widget.addTab(self.ai_tab_widget, "AI智能功能")
            layout.addWidget(self.tab_widget)

            # 新增：初始化results_area用于展示分析/回测结果
            self.results_area = QTextEdit()
            self.results_area.setReadOnly(True)
            self.results_area.setMinimumHeight(120)
            layout.addWidget(QLabel("分析/回测结果展示："))
            layout.addWidget(self.results_area)

            self.main_layout.addWidget(self.progress_bar)
            self.main_layout.addWidget(self.step_list)

            self.log_manager.info("分析工具面板UI初始化完成")
        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_data(self):
        """初始化数据"""
        try:
            self.log_manager.info("初始化策略回测数据")
            # 初始化数据缓存
            self.data_cache = {}

            # 初始化当前选中的策略
            self.current_strategy = None

            # 初始化参数默认值
            self.default_params = {
                "均线周期": 20,
                "MACD快线": 12,
                "MACD慢线": 26,
                "MACD信号线": 9,
                "RSI周期": 14,
                "布林带周期": 20,
                "布林带标准差": 2.0,
                "自适应周期": 20,
                "自适应阈值": 0.5,
                "多因子数量": 5
            }

            # 初始化性能指标
            self.performance_metrics = {
                "年化收益率": 0.0,
                "最大回撤": 0.0,
                "夏普比率": 0.0,
                "胜率": 0.0,
                "盈亏比": 0.0,
                "波动率": 0.0,
                "信息比率": 0.0,
                "索提诺比率": 0.0,
                "卡玛比率": 0.0,
                "Alpha": 0.0,
                "Beta": 0.0,
                "跟踪误差": 0.0,
                "换手率": 0.0,
                "最大连续亏损": 0,
                "平均持仓时间": 0
            }

            self.log_manager.info("数据初始化完成")

        except Exception as e:
            error_msg = f"初始化数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接信号"""
        try:
            self.log_manager.info("连接策略选择信号")
            # 连接策略选择信号
            if self.strategy_combo is None:
                self.log_manager.error(
                    "connect_signals失败: self.strategy_combo为None，UI未正确初始化，跳过信号连接。")
                return
            self.strategy_combo.currentTextChanged.connect(
                self.on_strategy_changed)

            # 连接按钮信号
            self.analyze_button.clicked.connect(self.on_tools_panel_analyze)
            self.export_button.clicked.connect(self.on_export)

            # 连接参数变化信号
            for widget in self.param_widgets.values():
                widget.valueChanged.connect(self.on_param_changed)

            # 连接回测设置变化信号
            for widget in self.backtest_widgets.values():
                widget.valueChanged.connect(self.on_backtest_setting_changed)

            self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

        # 新增：AI智能选股按钮事件绑定
        if hasattr(self, 'ai_stock_run_btn'):
            self.ai_stock_run_btn.clicked.connect(self.on_ai_stock_select)

    def on_strategy_changed(self, strategy: str):
        """处理策略变更"""
        try:
            self.current_strategy = strategy
            self.update_parameters_visibility()
            self.log_manager.info(f"策略已更改为: {strategy}")
            QMessageBox.information(self, "策略切换", f"已切换到策略: {strategy}")
        except Exception as e:
            error_msg = f"策略变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.warning(self, "策略切换错误", error_msg)
            self.error_occurred.emit(error_msg)

    def on_param_changed(self):
        """处理参数变更，实时同步到trading_widget"""
        try:
            self.update_parameters()
            # 实时同步参数到trading_widget
            params = {k: v.value() if hasattr(v, 'value') else v.currentText() if hasattr(
                v, 'currentText') else v for k, v in self.param_widgets.items()}
            if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'set_parameters'):
                self.trading_widget.set_parameters(params)
            self.log_manager.info("参数已更新并同步到TradingWidget")
            # 不再弹窗，避免频繁打扰
        except Exception as e:
            error_msg = f"参数更新失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def update_parameters_visibility(self):
        """根据当前策略更新参数可见性"""
        try:
            # 获取当前策略的参数配置
            strategy_params = self.get_strategy_parameters(
                self.current_strategy)

            # 更新参数控件的可见性
            for name, control in self.param_widgets.items():
                control.setVisible(name in strategy_params)

            self.log_manager.info("参数可见性已更新")

        except Exception as e:
            error_msg = f"更新参数可见性失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def update_parameters(self):
        """更新参数值"""
        try:
            # 获取当前策略的参数配置
            strategy_params = self.get_strategy_parameters(
                self.current_strategy)

            # 更新参数值
            for name, control in self.param_widgets.items():
                if name in strategy_params:
                    control.setValue(strategy_params[name])

            self.log_manager.info("参数值已更新")

        except Exception as e:
            error_msg = f"更新参数值失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def get_strategy_parameters(self, strategy: str) -> dict:
        """获取策略参数配置"""
        # 这里可以根据实际策略返回对应的参数配置
        return self.default_params.copy()

    def on_tools_panel_analyze(self):
        """
        只做参数收集和同步，所有分析逻辑和参数校验都委托给 TradingWidget.on_analyze。
        TradingWidget.on_analyze 是唯一的分析和参数校验入口，所有分析入口都应调用此方法。
        """
        # 收集参数
        params = {}
        if hasattr(self, 'param_controls') and self.param_controls:
            for k, v in self.param_controls.items():
                if hasattr(v, 'value'):
                    params[k] = v.value()
                elif hasattr(v, 'currentText'):
                    params[k] = v.currentText()
                else:
                    params[k] = v
        # 获取当前策略
        strategy = getattr(self, 'strategy_combo', None).currentText(
        ) if hasattr(self, 'strategy_combo') else ''
        params['strategy'] = strategy
        # 股票代码只用trading_widget.current_stock
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'current_stock'):
            params['stock'] = self.trading_widget.current_stock
        # 同步参数到trading_widget
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'set_parameters'):
            self.trading_widget.set_parameters(params)
        # 调用TradingWidget分析逻辑（无参）
        results = None
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'on_analyze'):
            try:
                results = self.trading_widget.on_analyze()
            except Exception as e:
                self.set_status_message(f"分析失败: {str(e)}", error=True)
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"分析异常: {str(e)}")
                return
        if results:
            self.update_results(results)
            if hasattr(self, 'analysis_completed'):
                self.analysis_completed.emit(results)

    def on_backtest_setting_changed(self):
        """处理回测设置变更"""
        try:
            self.log_manager.info("回测设置已更新")
            QMessageBox.information(self, "回测设置", "回测设置已更新。")
        except Exception as e:
            error_msg = f"回测设置更新失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.warning(self, "回测设置错误", error_msg)
            self.error_occurred.emit(error_msg)

    def update_signals(self, signals):
        """统一更新交易信号显示，便于子类扩展"""
        # 这里可以实现信号表格或图表的更新逻辑，子类可重写
        self.log_manager.info(f"收到{len(signals)}条交易信号")
        # 示例：弹窗提示
        # QMessageBox.information(self, "信号更新", f"收到{len(signals)}条交易信号")

    def update_results(self, results: dict):
        """自动分组展示绩效/风险/交易指标，驱动主图表交互，批量回测分组对比自动生成，复用所有已有逻辑。"""
        # 1. 清空原有结果区
        if hasattr(self, 'results_area') and self.results_area:
            self.results_area.clear()
        # 2. 绩效/风险/交易指标分组展示
        perf = results.get('metrics') or results.get('performance') or {}
        risk = results.get('risk', {})
        trade = results.get('trade', {})

        def show_group(title, data):
            if data:
                text = f"<b>{title}：</b><br>"
                for k, v in data.items():
                    if isinstance(v, float):
                        text += f"{k}: {v:.4f}<br>"
                    else:
                        text += f"{k}: {v}<br>"
                self.results_area.append(text)
        show_group("收益类指标", perf)
        show_group("风险类指标", risk)
        show_group("交易类指标", trade)
        # 3. 资金曲线/回撤/收益分布等交互图表
        parent = self.parent()
        chart_widget = getattr(parent, 'chart_widget', None)
        if chart_widget:
            if 'equity_curve' in results:
                chart_widget.update_chart(
                    {'equity_curve': results['equity_curve']})
            if 'drawdown_curve' in results:
                chart_widget.update_chart(
                    {'drawdown_curve': results['drawdown_curve']})
            if 'returns_histogram' in results:
                chart_widget.update_chart(
                    {'returns_histogram': results['returns_histogram']})
            if 'signals' in results:
                chart_widget.plot_signals(results['signals'])
            if 'pattern_signals' in results:
                chart_widget.plot_patterns(results['pattern_signals'])
        # 4. 批量回测分组对比
        group_results = results.get('group_results', None)
        if group_results:
            self.results_area.append("<b>分组对比：</b><br>")
            for group, group_metric in group_results.items():
                self.results_area.append(f"<u>{group}</u>:<br>")
                for k, v in group_metric.items():
                    if isinstance(v, float):
                        self.results_area.append(f"{k}: {v:.4f}")
                    else:
                        self.results_area.append(f"{k}: {v}")
            # 可选：调用chart_widget绘制分组对比图
            if chart_widget and hasattr(chart_widget, 'plot_group_comparison'):
                chart_widget.plot_group_comparison(group_results)
        # 5. 兼容原有信号/分析结果展示
        if 'signals' in results:
            self.results_area.append(
                "<b>信号明细：</b><br>" + str(results['signals']))
        if 'analysis' in results:
            self.results_area.append(
                "<b>分析结果：</b><br>" + str(results['analysis']))
        # 6. 调用TradingWidget的update_backtest_results以填充表格（如有）
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'update_backtest_results'):
            self.trading_widget.update_backtest_results(results)

    def update_metrics_display(self):
        """统一更新性能指标显示，风格与主界面一致"""
        try:
            if not hasattr(self, 'metric_labels') or not self.metric_labels:
                self.create_metrics_display()
            for name, value in self.performance_metrics.items():
                if name in self.metric_labels:
                    if isinstance(value, float):
                        formatted_value = f"{value:.2%}" if "率" in name else f"{value:.3f}"
                    else:
                        formatted_value = str(value)
                    self.metric_labels[name].setText(formatted_value)
        except Exception as e:
            error_msg = f"更新性能指标显示失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def create_metrics_display(self):
        """统一创建性能指标显示区域，风格与主界面一致"""
        try:
            metrics_group = QGroupBox("性能指标")
            metrics_layout = QFormLayout(metrics_group)
            self.metric_labels = {}
            for name in self.performance_metrics.keys():
                label = QLabel("--")
                metrics_layout.addRow(f"{name}:", label)
                self.metric_labels[name] = label
            self.main_layout.addWidget(metrics_group)
        except Exception as e:
            error_msg = f"创建性能指标显示区域失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def refresh(self) -> None:
        """
        刷新分析工具面板内容，自动刷新回测结果和性能指标。
        """
        try:
            # 重新执行分析和回测（如有方法）
            if hasattr(self, 'on_tools_panel_analyze'):
                self.on_tools_panel_analyze()
            # 刷新性能指标显示
            if hasattr(self, 'update_metrics_display'):
                self.update_metrics_display()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"刷新分析工具面板失败: {str(e)}")

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def init_batch_analysis_ui(self):
        # 新增批量分析Tab
        if not hasattr(self, 'tab_widget'):
            self.tab_widget = QTabWidget()
            self.main_layout.addWidget(self.tab_widget)
        self.batch_tab = QWidget()
        batch_layout = QVBoxLayout(self.batch_tab)
        # 股票输入
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("输入股票代码，逗号分隔")
        batch_layout.addWidget(QLabel("股票代码："))
        batch_layout.addWidget(self.stock_input)
        # 策略选择
        self.strategy_checks = []
        strategy_names = ["均线策略", "MACD策略", "RSI策略", "布林带策略", "KDJ策略", "自定义策略"]
        strat_layout = QHBoxLayout()
        for name in strategy_names:
            cb = QCheckBox(name)
            strat_layout.addWidget(cb)
            self.strategy_checks.append(cb)
        batch_layout.addWidget(QLabel("选择策略："))
        batch_layout.addLayout(strat_layout)
        # 参数输入（可扩展为表格）
        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText(
            "参数组合（如 fast=5,slow=20;fast=10,slow=30）")
        batch_layout.addWidget(QLabel("参数组合："))
        batch_layout.addWidget(self.param_input)
        # 新增：执行模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("执行模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["本地多线程", "Dask分布式"])
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        # 远程节点输入（仅Dask分布式时可见）
        self.remote_nodes_edit = QLineEdit()
        self.remote_nodes_edit.setPlaceholderText(
            "Dask调度器地址，如tcp://127.0.0.1:8786，多个用逗号分隔")
        self.remote_nodes_edit.setVisible(False)
        mode_layout.addWidget(self.remote_nodes_edit)
        self.mode_combo.currentTextChanged.connect(
            lambda text: self.remote_nodes_edit.setVisible(text == "Dask分布式"))
        batch_layout.addLayout(mode_layout)
        # 启动批量分析按钮
        self.start_batch_btn = QPushButton("开始批量分析")
        self.start_batch_btn.clicked.connect(self.start_batch_analysis)
        batch_layout.addWidget(self.start_batch_btn)
        # 新增：全部暂停/恢复按钮
        self.pause_all_btn = QPushButton("全部暂停")
        self.pause_all_btn.clicked.connect(self.pause_all_tasks)
        self.resume_all_btn = QPushButton("全部恢复")
        self.resume_all_btn.clicked.connect(self.resume_all_tasks)
        batch_layout.addWidget(self.pause_all_btn)
        batch_layout.addWidget(self.resume_all_btn)
        # 任务进度表
        self.batch_table = QTableWidget(0, 5)
        self.batch_table.setHorizontalHeaderLabels(
            ["股票", "策略", "参数", "进度", "状态"])
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        batch_layout.addWidget(self.batch_table)
        # 新增：实时进度曲线
        self.progress_chart = QChart()
        self.progress_series = QLineSeries()
        self.progress_chart.addSeries(self.progress_series)
        self.progress_chart.setTitle("批量分析进度曲线")
        self.progress_axis_x = QValueAxis()
        self.progress_axis_x.setTitleText("时间(s)")
        self.progress_axis_y = QValueAxis()
        self.progress_axis_y.setTitleText("完成率%")
        self.progress_axis_y.setRange(0, 100)
        self.progress_chart.addAxis(self.progress_axis_x, Qt.AlignBottom)
        self.progress_chart.addAxis(self.progress_axis_y, Qt.AlignLeft)
        self.progress_series.attachAxis(self.progress_axis_x)
        self.progress_series.attachAxis(self.progress_axis_y)
        self.progress_chart_view = QChartView(self.progress_chart)
        batch_layout.addWidget(self.progress_chart_view)
        # 新增：分组统计区
        self.group_stats_label = QLabel("分组统计：")
        batch_layout.addWidget(self.group_stats_label)
        # 新增：日志区
        self.batch_log_area = QTextEdit()
        self.batch_log_area.setReadOnly(True)
        batch_layout.addWidget(QLabel("批量分析日志："))
        batch_layout.addWidget(self.batch_log_area)
        self.tab_widget.addTab(self.batch_tab, "批量分析")
        # 定时刷新进度曲线
        self.progress_data = []  # (timestamp, percent)
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress_chart)
        self.progress_timer.start(1000)
        self.batch_start_time = None
        # 新增：任务队列区
        self.task_queue_label = QLabel("任务队列：")
        batch_layout.addWidget(self.task_queue_label)
        self.task_queue_list = QListWidget()
        self.task_queue_list.setSelectionMode(
            QAbstractItemView.ExtendedSelection)
        self.task_queue_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.task_queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_queue_list.customContextMenuRequested.connect(
            self.show_task_queue_menu)
        batch_layout.addWidget(self.task_queue_list)
        # 批量操作按钮
        op_layout = QHBoxLayout()
        self.pause_sel_btn = QPushButton("暂停选中")
        self.pause_sel_btn.clicked.connect(self.pause_selected_tasks)
        self.resume_sel_btn = QPushButton("恢复选中")
        self.resume_sel_btn.clicked.connect(self.resume_selected_tasks)
        self.terminate_sel_btn = QPushButton("终止选中")
        self.terminate_sel_btn.clicked.connect(self.terminate_selected_tasks)
        self.retry_sel_btn = QPushButton("重试选中")
        self.retry_sel_btn.clicked.connect(self.retry_selected_tasks)
        op_layout.addWidget(self.pause_sel_btn)
        op_layout.addWidget(self.resume_sel_btn)
        op_layout.addWidget(self.terminate_sel_btn)
        op_layout.addWidget(self.retry_sel_btn)
        batch_layout.addLayout(op_layout)
        # 优先级批量按钮
        pri_layout = QHBoxLayout()
        self.up_sel_btn = QPushButton("上移选中")
        self.up_sel_btn.clicked.connect(self.move_selected_tasks_up)
        self.down_sel_btn = QPushButton("下移选中")
        self.down_sel_btn.clicked.connect(self.move_selected_tasks_down)
        self.top_sel_btn = QPushButton("置顶选中")
        self.top_sel_btn.clicked.connect(self.move_selected_tasks_top)
        self.bottom_sel_btn = QPushButton("置底选中")
        self.bottom_sel_btn.clicked.connect(self.move_selected_tasks_bottom)
        pri_layout.addWidget(self.up_sel_btn)
        pri_layout.addWidget(self.down_sel_btn)
        pri_layout.addWidget(self.top_sel_btn)
        pri_layout.addWidget(self.bottom_sel_btn)
        batch_layout.addLayout(pri_layout)
        # 新增：筛选和分组控件
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选："))
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态")
        self.status_filter.addItems(["等待中", "进行中", "已暂停", "已终止", "已完成", "失败"])
        self.status_filter.currentTextChanged.connect(self.apply_task_filters)
        filter_layout.addWidget(self.status_filter)
        self.strategy_filter = QComboBox()
        self.strategy_filter.addItem("全部策略")
        # 动态填充策略
        self.strategy_filter.addItems(
            sorted(set(t['strategy'] for t in getattr(self, 'batch_tasks', []))))
        self.strategy_filter.currentTextChanged.connect(
            self.apply_task_filters)
        filter_layout.addWidget(self.strategy_filter)
        self.stock_filter = QComboBox()
        self.stock_filter.addItem("全部股票")
        self.stock_filter.addItems(
            sorted(set(t['stock'] for t in getattr(self, 'batch_tasks', []))))
        self.stock_filter.currentTextChanged.connect(self.apply_task_filters)
        filter_layout.addWidget(self.stock_filter)
        filter_layout.addStretch()
        self.batch_tab.layout().insertLayout(0, filter_layout)
        # 新增：表头排序
        self.batch_table.setSortingEnabled(True)
        # 新增：分组显示（按状态分组）
        self.group_by_combo = QComboBox()
        self.group_by_combo.addItems(["不分组", "按状态分组", "按策略分组", "按股票分组"])
        self.group_by_combo.currentTextChanged.connect(
            self.apply_task_grouping)
        filter_layout.addWidget(QLabel("分组："))
        filter_layout.addWidget(self.group_by_combo)
        # 新增：高级筛选控件
        adv_filter_layout = QHBoxLayout()
        adv_filter_layout.addWidget(QLabel("高级筛选："))
        self.status_multi_filter = QComboBox()
        self.status_multi_filter.setEditable(True)
        self.status_multi_filter.setInsertPolicy(QComboBox.NoInsert)
        self.status_multi_filter.addItem("全部状态")
        for s in ["等待中", "进行中", "已暂停", "已终止", "已完成", "失败"]:
            self.status_multi_filter.addItem(s)
        adv_filter_layout.addWidget(self.status_multi_filter)
        self.strategy_multi_filter = QComboBox()
        self.strategy_multi_filter.setEditable(True)
        self.strategy_multi_filter.setInsertPolicy(QComboBox.NoInsert)
        self.strategy_multi_filter.addItem("全部策略")
        self.strategy_multi_filter.addItems(
            sorted(set(t['strategy'] for t in getattr(self, 'batch_tasks', []))))
        adv_filter_layout.addWidget(self.strategy_multi_filter)
        self.stock_multi_filter = QComboBox()
        self.stock_multi_filter.setEditable(True)
        self.stock_multi_filter.setInsertPolicy(QComboBox.NoInsert)
        self.stock_multi_filter.addItem("全部股票")
        self.stock_multi_filter.addItems(
            sorted(set(t['stock'] for t in getattr(self, 'batch_tasks', []))))
        adv_filter_layout.addWidget(self.stock_multi_filter)
        self.keyword_filter = QLineEdit()
        self.keyword_filter.setPlaceholderText("关键字/区间筛选（如股票、策略、状态）")
        adv_filter_layout.addWidget(self.keyword_filter)
        adv_filter_layout.addStretch()
        self.batch_tab.layout().insertLayout(1, adv_filter_layout)
        self.status_multi_filter.currentTextChanged.connect(
            self.apply_advanced_filters)
        self.strategy_multi_filter.currentTextChanged.connect(
            self.apply_advanced_filters)
        self.stock_multi_filter.currentTextChanged.connect(
            self.apply_advanced_filters)
        self.keyword_filter.textChanged.connect(self.apply_advanced_filters)
        # 新增：树状分组控件
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderLabels(["分组", "成功", "失败", "总数", "进度%"])
        self.group_tree.setColumnWidth(0, 120)
        self.group_tree.setVisible(False)
        self.batch_tab.layout().insertWidget(2, self.group_tree)
        # 新增：AI策略推荐Tab
        self.init_ai_strategy_tab()
        # 新增：AI参数优化Tab
        self.init_ai_optimizer_tab()
        # 新增：AI智能诊断Tab
        self.init_ai_diagnosis_tab()
        self.batch_export_trace_btn = QPushButton("导出队列日志")
        self.batch_export_trace_btn.clicked.connect(
            self.export_batch_trace_log)
        layout.addWidget(self.batch_export_trace_btn)

    def init_ai_strategy_tab(self):
        """
        初始化AI策略推荐助手Tab，包含输入区、一键推荐按钮、结果展示。
        """
        self.ai_strategy_tab = QWidget()
        layout = QVBoxLayout(self.ai_strategy_tab)
        # 输入区
        input_layout = QHBoxLayout()
        self.ai_strategy_stock_input = QLineEdit()
        self.ai_strategy_stock_input.setPlaceholderText("输入股票代码（可多只，逗号分隔）")
        input_layout.addWidget(QLabel("股票代码:"))
        input_layout.addWidget(self.ai_strategy_stock_input)
        self.ai_strategy_candidate_input = QLineEdit()
        self.ai_strategy_candidate_input.setPlaceholderText(
            "候选策略（如MA,MACD,RSI，逗号分隔）")
        input_layout.addWidget(QLabel("候选策略:"))
        input_layout.addWidget(self.ai_strategy_candidate_input)
        layout.addLayout(input_layout)
        # 一键推荐按钮
        self.ai_strategy_run_btn = QPushButton("一键推荐策略")
        self.ai_strategy_run_btn.clicked.connect(self.on_ai_strategy_recommend)
        layout.addWidget(self.ai_strategy_run_btn)
        # 结果展示表格
        self.ai_strategy_result_table = QTableWidget()
        self.ai_strategy_result_table.setColumnCount(3)
        self.ai_strategy_result_table.setHorizontalHeaderLabels(
            ["股票代码", "推荐策略", "推荐理由"])
        layout.addWidget(self.ai_strategy_result_table)
        # 一键应用到批量分析按钮
        self.ai_strategy_apply_btn = QPushButton("一键应用到批量分析")
        self.ai_strategy_apply_btn.clicked.connect(
            self.apply_ai_strategy_to_batch)
        layout.addWidget(self.ai_strategy_apply_btn)
        # 加入到TabWidget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.addTab(self.ai_strategy_tab, "AI策略推荐")
        self.init_ai_api_stats(layout, "策略推荐")
        # 股票代码补全
        if hasattr(self, 'get_all_stock_features'):
            codes = [s['code'] for s in self.get_all_stock_features()]
            completer = QCompleter(codes)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.ai_strategy_stock_input.setCompleter(completer)
        # 策略名补全
        strategy_names = ["MA", "MACD", "RSI", "BOLL", "KDJ", "DX"]
        completer2 = QCompleter(strategy_names)
        completer2.setCaseSensitivity(Qt.CaseInsensitive)
        self.ai_strategy_candidate_input.setCompleter(completer2)
        # 可视化按钮
        self.ai_strategy_vis_btn = QPushButton("结果可视化")
        self.ai_strategy_vis_btn.clicked.connect(
            self.visualize_ai_strategy_result)
        layout.addWidget(self.ai_strategy_vis_btn)
        # 导出调用链日志按钮
        self.ai_strategy_export_trace_btn = QPushButton("导出调用链日志")
        self.ai_strategy_export_trace_btn.clicked.connect(
            self.export_last_trace_log)
        layout.addWidget(self.ai_strategy_export_trace_btn)

    def init_ai_api_stats(self, parent_layout, tab_name):
        """
        初始化API调用统计区，tab_name用于区分不同Tab。
        """
        from PyQt5.QtWidgets import QHBoxLayout, QLabel
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(QLabel(f"{tab_name} API调用统计："))
        self.api_stats = getattr(self, 'api_stats', {})
        self.api_stats[tab_name] = {"count": 0,
                                    "success": 0, "fail": 0, "total_time": 0.0}
        self.api_stats_labels = getattr(self, 'api_stats_labels', {})
        self.api_stats_labels[tab_name] = QLabel("调用0次，成功0，失败0，平均耗时0ms")
        stats_layout.addWidget(self.api_stats_labels[tab_name])
        stats_layout.addStretch()
        parent_layout.addLayout(stats_layout)

    def update_api_stats(self, tab_name, success, elapsed):
        """
        更新API调用统计。
        """
        stats = self.api_stats[tab_name]
        stats["count"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["fail"] += 1
        stats["total_time"] += elapsed
        avg = stats["total_time"] / stats["count"] if stats["count"] else 0
        label = self.api_stats_labels[tab_name]
        label.setText(
            f"调用{stats['count']}次，成功{stats['success']}，失败{stats['fail']}，平均耗时{avg:.0f}ms")

    def on_ai_strategy_recommend(self):
        """
        一键推荐策略：自动获取股票特征和历史表现，调用API，展示推荐结果。
        """
        self.ai_strategy_run_btn.setEnabled(False)
        self.ai_strategy_run_btn.setText("推荐中...")
        QApplication.processEvents()
        try:
            codes = self.ai_strategy_stock_input.text().strip()
            if not codes:
                QMessageBox.warning(self, "输入错误", "请输入股票代码")
                return
            code_list = [c.strip() for c in codes.split(',') if c.strip()]
            candidate_str = self.ai_strategy_candidate_input.text().strip()
            candidates = [s.strip() for s in candidate_str.split(
                ',') if s.strip()] or ["MA", "MACD", "RSI"]
            # 自动获取特征和历史表现
            stock_data = self.get_all_stock_features()
            history = self.get_stocks_history(code_list)
            payload = {
                "stock_data": stock_data,
                "history": history,
                "candidate_strategies": candidates
            }
            url = "http://localhost:8000/api/ai/recommend_strategy"
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                # 展示到表格
                self.ai_strategy_result_table.clear()
                self.ai_strategy_result_table.setColumnCount(3)
                self.ai_strategy_result_table.setHorizontalHeaderLabels(
                    ["股票代码", "推荐策略", "推荐理由"])
                self.ai_strategy_result_table.setRowCount(len(code_list))
                for i, code in enumerate(code_list):
                    self.ai_strategy_result_table.setItem(
                        i, 0, QTableWidgetItem(code))
                    self.ai_strategy_result_table.setItem(
                        i, 1, QTableWidgetItem(data.get("recommended", "")))
                    self.ai_strategy_result_table.setItem(
                        i, 2, QTableWidgetItem(data.get("reason", "")))
                if not data.get("recommended"):
                    QMessageBox.information(self, "无结果", "未能推荐出策略")
                self.update_api_stats("策略推荐", True, (time.time()-t0)*1000)
            else:
                QMessageBox.critical(
                    self, "推荐失败", f"API请求失败: {resp.status_code}")
                self.update_api_stats("策略推荐", False, (time.time()-t0)*1000)
        except Exception as e:
            QMessageBox.critical(self, "推荐异常", str(e))
            self.update_api_stats("策略推荐", False, (time.time()-t0)*1000)
        finally:
            self.ai_strategy_run_btn.setEnabled(True)
            self.ai_strategy_run_btn.setText("一键推荐策略")

    def get_stocks_history(self, code_list):
        """
        批量获取股票历史表现，供AI策略推荐API使用。
        """
        try:
            # 假设主窗口/数据管理器可批量获取历史数据
            if hasattr(self, 'parent') and hasattr(self.parent(), 'data_manager'):
                data_manager = self.parent().data_manager
                history = []
                for code in code_list:
                    df = data_manager.get_k_data(code)
                    if not df.empty:
                        history.append(df.to_dict(orient='records'))
                return history
        except Exception as e:
            print(f"获取历史表现失败: {e}")
        return []

    def apply_ai_strategy_to_batch(self):
        """
        一键将推荐策略应用到批量分析/回测。
        """
        try:
            # 取表格中的股票和策略
            codes = []
            strategy = None
            for row in range(self.ai_strategy_result_table.rowCount()):
                code = self.ai_strategy_result_table.item(row, 0).text()
                codes.append(code)
                if not strategy:
                    strategy = self.ai_strategy_result_table.item(
                        row, 1).text()
            # 应用到批量分析输入
            if hasattr(self, 'stock_input') and hasattr(self, 'strategy_checks'):
                self.stock_input.setText(','.join(codes))
                # 勾选推荐策略
                for cb in self.strategy_checks:
                    if cb.text() == strategy:
                        cb.setChecked(True)
                    else:
                        cb.setChecked(False)
                QMessageBox.information(
                    self, "已应用到批量分析", f"已将推荐策略和股票应用到批量分析队列，可直接点击批量回测/分析。")
        except Exception as e:
            print(f"应用到批量分析失败: {e}")

    def apply_task_filters(self):
        # 根据筛选条件刷新表格显示
        status = self.status_filter.currentText()
        strategy = self.strategy_filter.currentText()
        stock = self.stock_filter.currentText()
        for row, task in enumerate(self.batch_tasks):
            show = True
            if status != "全部状态" and task['status'] != status:
                show = False
            if strategy != "全部策略" and task['strategy'] != strategy:
                show = False
            if stock != "全部股票" and task['stock'] != stock:
                show = False
            self.batch_table.setRowHidden(row, not show)

    def apply_task_grouping(self):
        # 简单分组：插入分组标签行（可扩展为树结构）
        group_by = self.group_by_combo.currentText()
        # 先全部显示
        for row in range(self.batch_table.rowCount()):
            self.batch_table.setRowHidden(row, False)
        if group_by == "不分组":
            return
        # 统计分组
        group_map = {}
        for idx, task in enumerate(self.batch_tasks):
            if group_by == "按状态分组":
                key = task['status']
            elif group_by == "按策略分组":
                key = task['strategy']
            elif group_by == "按股票分组":
                key = task['stock']
            else:
                key = "其他"
            if key not in group_map:
                group_map[key] = []
            group_map[key].append(idx)
        # 隐藏所有行，分组时只显示分组内
        for row in range(self.batch_table.rowCount()):
            self.batch_table.setRowHidden(row, True)
        # 依次显示分组
        for group, idxs in group_map.items():
            # 可插入分组标签行（如QTableWidgetItem("【%s】" % group)）
            for idx in idxs:
                self.batch_table.setRowHidden(idx, False)

    def start_batch_analysis(self):
        # 恢复上次任务按钮
        if not hasattr(self, 'restore_batch_btn'):
            self.restore_batch_btn = QPushButton("恢复上次任务")
            self.restore_batch_btn.clicked.connect(
                self.restore_last_batch_tasks)
            self.main_layout.addWidget(self.restore_batch_btn)
        # 解析输入
        stocks = [s.strip()
                  for s in self.stock_input.text().split(',') if s.strip()]
        strategies = [cb.text()
                      for cb in self.strategy_checks if cb.isChecked()]
        param_strs = [p.strip()
                      for p in self.param_input.text().split(';') if p.strip()]
        param_list = []
        for p in param_strs:
            param = {}
            for kv in p.split(','):
                if '=' in kv:
                    k, v = kv.split('=', 1)
                    param[k.strip()] = v.strip()
            if param:
                param_list.append(param)
        if not stocks or not strategies:
            QMessageBox.warning(self, "参数错误", "请至少输入股票代码和选择策略")
            return
        # 生成任务
        self.batch_table.setRowCount(0)
        self.batch_tasks = []
        _task_events = []  # 每个任务一个Event
        _task_threads = []  # 线程句柄
        max_retries = 3  # 可扩展为UI参数
        for stock in stocks:
            for strategy in strategies:
                for params in param_list or [{}]:
                    row = self.batch_table.rowCount()
                    self.batch_table.insertRow(row)
                    self.batch_table.setItem(row, 0, QTableWidgetItem(stock))
                    self.batch_table.setItem(
                        row, 1, QTableWidgetItem(strategy))
                    self.batch_table.setItem(
                        row, 2, QTableWidgetItem(str(params)))
                    self.batch_table.setItem(row, 3, QTableWidgetItem("0%"))
                    self.batch_table.setItem(row, 4, QTableWidgetItem("未开始"))
                    # 新增：进度条控件
                    progress_bar = QProgressBar()
                    progress_bar.setValue(0)
                    self.batch_table.setCellWidget(row, 5, progress_bar)
                    # 新增：剩余时间预测
                    eta_label = QLabel("--")
                    self.batch_table.setCellWidget(row, 6, eta_label)
                    pause_event = threading.Event()
                    terminate_flag = threading.Event()
                    self.batch_tasks.append(dict(stock=stock, strategy=strategy, params=params, row=row, status='等待中', pause_event=pause_event,
                                            terminate_flag=terminate_flag, thread=None, retries=0, max_retries=max_retries, progress_bar=progress_bar, eta_label=eta_label, start_time=None))
        self.update_task_queue()
        self.run_batch_tasks()
        self.save_batch_tasks()

    def save_batch_tasks(self):
        """
        持久化当前批量任务队列到本地JSON
        """
        try:
            tasks = [{k: v for k, v in t.items() if k in ('stock', 'strategy', 'params', 'row', 'status', 'retries', 'max_retries',
                                                          'progress_bar', 'eta_label', 'start_time')} for t in self.batch_tasks]
            for t in tasks:
                t['progress'] = t['progress_bar'].value() if t.get(
                    'progress_bar') else 0
                t['eta'] = t['eta_label'].text() if t.get('eta_label') else '--'
                t.pop('progress_bar', None)
                t.pop('eta_label', None)
            with open('batch_tasks.json', 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存批量任务失败: {e}")

    def restore_last_batch_tasks(self):
        """
        恢复上次未完成的批量任务队列
        """
        if not os.path.exists('batch_tasks.json'):
            QMessageBox.information(self, "恢复任务", "未找到上次任务记录")
            return
        with open('batch_tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        self.batch_table.setRowCount(0)
        self.batch_tasks = []
        for t in tasks:
            row = self.batch_table.rowCount()
            self.batch_table.insertRow(row)
            self.batch_table.setItem(row, 0, QTableWidgetItem(t['stock']))
            self.batch_table.setItem(row, 1, QTableWidgetItem(t['strategy']))
            self.batch_table.setItem(
                row, 2, QTableWidgetItem(str(t['params'])))
            self.batch_table.setItem(
                row, 3, QTableWidgetItem(f"{t.get('progress',0)}%"))
            self.batch_table.setItem(
                row, 4, QTableWidgetItem(t.get('status', '未开始')))
            progress_bar = QProgressBar()
            progress_bar.setValue(t.get('progress', 0))
            self.batch_table.setCellWidget(row, 5, progress_bar)
            eta_label = QLabel(t.get('eta', '--'))
            self.batch_table.setCellWidget(row, 6, eta_label)
            pause_event = threading.Event()
            terminate_flag = threading.Event()
            self.batch_tasks.append(dict(stock=t['stock'], strategy=t['strategy'], params=t['params'], row=row, status=t.get('status', '等待中'), pause_event=pause_event,
                                    terminate_flag=terminate_flag, thread=None, retries=t.get('retries', 0), max_retries=t.get('max_retries', 3), progress_bar=progress_bar, eta_label=eta_label, start_time=t.get('start_time')))
        self.update_task_queue()
        self.run_batch_tasks()

    def run_batch_tasks(self):
        self.batch_task_trace_ids = []

        def worker(task, idx):
            trace_id = str(uuid.uuid4())
            self.batch_task_trace_ids.append(trace_id)
            try:
                self.log_manager.info(f"批量任务开始: {task}", trace_id=trace_id)
                row = task['row']
                task['status'] = '进行中'
                task['start_time'] = time.time()
                self.update_task_queue()
                self.save_batch_tasks()
                self.batch_table.setItem(row, 3, QTableWidgetItem("进行中"))
                self.batch_table.setItem(row, 4, QTableWidgetItem("分析中"))
                progress_bar = task.get('progress_bar')
                eta_label = task.get('eta_label')
                total_steps = 20
                for i in range(total_steps):
                    if task['terminate_flag'].is_set():
                        task['status'] = '已终止'
                        self.batch_table.setItem(
                            row, 3, QTableWidgetItem("已终止"))
                        self.batch_table.setItem(
                            row, 4, QTableWidgetItem("终止"))
                        if progress_bar:
                            progress_bar.setValue(0)
                        if eta_label:
                            eta_label.setText("--")
                        self.update_task_queue()
                        self.save_batch_tasks()
                        return
                    while task['pause_event'].is_set():
                        task['status'] = '已暂停'
                        self.batch_table.setItem(
                            row, 3, QTableWidgetItem("已暂停"))
                        self.batch_table.setItem(
                            row, 4, QTableWidgetItem("暂停"))
                        if eta_label:
                            eta_label.setText("--")
                        self.update_task_queue()
                        self.save_batch_tasks()
                        time.sleep(0.2)
                    percent = int((i+1)/total_steps*100)
                    task['status'] = f'进行中({i+1}/{total_steps})'
                    self.batch_table.setItem(
                        row, 3, QTableWidgetItem(f"{percent}%"))
                    if progress_bar:
                        progress_bar.setValue(percent)
                    # 剩余时间预测
                    elapsed = time.time() - \
                        task['start_time'] if task['start_time'] else 0
                    if eta_label and i > 0:
                        avg_time = elapsed / (i+1)
                        eta = avg_time * (total_steps - (i+1))
                        eta_label.setText(f"{int(eta)}s")
                    elif eta_label:
                        eta_label.setText("--")
                    self.update_task_queue()
                    self.save_batch_tasks()
                    time.sleep(0.2)
                # 模拟失败概率
                if random.random() < 0.2 and task['retries'] < task['max_retries']:
                    task['status'] = '失败'
                    self.batch_table.setItem(row, 3, QTableWidgetItem("失败"))
                    self.batch_table.setItem(
                        row, 4, QTableWidgetItem(f"失败(第{task['retries']+1}次)"))
                    if progress_bar:
                        progress_bar.setValue(0)
                    if eta_label:
                        eta_label.setText("--")
                    self.update_task_queue()
                    self.save_batch_tasks()
                    # 自动重试
                    task['retries'] += 1
                    self.log_manager.info(f"任务{row}失败，自动重试第{task['retries']}次")
                    t = threading.Thread(target=worker, args=(task, idx))
                    task['thread'] = t
                    t.start()
                    self._task_threads.append(t)
                    return
                task['status'] = '已完成'
                self.batch_table.setItem(row, 3, QTableWidgetItem("100%"))
                self.batch_table.setItem(row, 4, QTableWidgetItem("完成"))
                if progress_bar:
                    progress_bar.setValue(100)
                if eta_label:
                    eta_label.setText("0s")
                self.update_task_queue()
                self.save_batch_tasks()
                self.log_manager.info(f"批量任务成功: {task}", trace_id=trace_id)
                return task
            except Exception as e:
                self.log_manager.error(
                    f"批量任务异常: {task} - {str(e)}", trace_id=trace_id)
                self.save_batch_tasks()
                raise
        self._task_threads = []
        for idx, task in enumerate(self.batch_tasks):
            t = threading.Thread(target=worker, args=(task, idx))
            task['thread'] = t
            t.start()
            self._task_threads.append(t)

    def init_scheduler_ui(self):
        # 定时任务管理Tab
        if not hasattr(self, 'tab_widget'):
            self.tab_widget = QTabWidget()
            self.main_layout.addWidget(self.tab_widget)
        self.scheduler_tab = QWidget()
        sched_layout = QVBoxLayout(self.scheduler_tab)
        # 任务列表
        self.sched_table = QTableWidget(0, 5)
        self.sched_table.setHorizontalHeaderLabels(
            ["任务名", "表达式", "下次运行", "状态", "操作"])
        self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sched_layout.addWidget(self.sched_table)
        # 添加任务按钮
        self.add_sched_btn = QPushButton("添加定时任务")
        self.add_sched_btn.clicked.connect(self.add_scheduler_job)
        sched_layout.addWidget(self.add_sched_btn)
        self.tab_widget.addTab(self.scheduler_tab, "定时任务")
        # 初始化调度器
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.sched_jobs = {}

    def add_scheduler_job(self):
        # 简化为弹窗输入cron表达式和任务名
        name, ok = QInputDialog.getText(self, "任务名", "请输入任务名称：")
        if not ok or not name:
            return
        cron, ok = QInputDialog.getText(
            self, "Cron表达式", "请输入cron表达式（如0 2 * * *表示每天2点）：")
        if not ok or not cron:
            return
        try:
            trigger = CronTrigger.from_crontab(cron)
        except Exception as e:
            QMessageBox.warning(self, "表达式错误", f"Cron表达式无效: {e}")
            return
        job = self.scheduler.add_job(
            self.run_scheduled_batch, trigger, name=name)
        self.sched_jobs[job.id] = job
        row = self.sched_table.rowCount()
        self.sched_table.insertRow(row)
        self.sched_table.setItem(row, 0, QTableWidgetItem(name))
        self.sched_table.setItem(row, 1, QTableWidgetItem(cron))
        self.sched_table.setItem(
            row, 2, QTableWidgetItem(str(job.next_run_time)))
        self.sched_table.setItem(row, 3, QTableWidgetItem("运行中"))
        op_btn = QPushButton("删除")
        op_btn.clicked.connect(lambda: self.remove_scheduler_job(job.id, row))
        self.sched_table.setCellWidget(row, 4, op_btn)

    def remove_scheduler_job(self, job_id, row):
        if job_id in self.sched_jobs:
            self.scheduler.remove_job(job_id)
            del self.sched_jobs[job_id]
        self.sched_table.removeRow(row)

    def run_scheduled_batch(self):
        # 这里可调用start_batch_analysis或自定义批量分析逻辑
        self.start_batch_analysis()
        # 可集成邮件通知
        self.send_email_notification("定时批量分析已完成", "请登录系统查看详细结果。")

    def send_email_notification(self, subject, content):
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header
        # 这里用简化的本地SMTP配置
        sender = "your_email@example.com"
        receivers = ["user@example.com"]
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = Header("分析系统", 'utf-8')
        msg['To'] = Header("用户", 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        try:
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail(sender, receivers, msg.as_string())
            smtp.quit()
        except Exception as e:
            print(f"邮件发送失败: {e}")

    def pause_all_tasks(self):
        for event in getattr(self, '_batch_pause_events', []):
            self.async_manager.pause_task(event)

    def resume_all_tasks(self):
        for event in getattr(self, '_batch_pause_events', []):
            self.async_manager.resume_task(event)

    def run_batch_backtest(self):
        try:
            codes = [c.strip()
                     for c in self.batch_stock_input.text().split(',') if c.strip()]
            strategies = [item.text()
                          for item in self.batch_strategy_list.selectedItems()]
            param_grid = []
            for row in range(self.param_grid_table.rowCount()):
                pname = self.param_grid_table.item(row, 0)
                pstart = self.param_grid_table.item(row, 1)
                pend = self.param_grid_table.item(row, 2)
                if pname and pstart and pend:
                    param_grid.append((pname.text(), float(
                        pstart.text()), float(pend.text())))
            if not codes or not strategies:
                QMessageBox.warning(self, "参数错误", "请至少输入股票代码和选择策略")
                return
            # 生成参数组合
            from itertools import product
            param_combos = [{}]
            if param_grid:
                param_ranges = [list(range(int(start), int(end)+1))
                                for _, start, end in param_grid]
                param_names = [name for name, _, _ in param_grid]
                param_combos = [dict(zip(param_names, vals))
                                for vals in product(*param_ranges)]
            # 进度条设置
            total = len(codes) * len(strategies) * len(param_combos)
            self.batch_progress.setMaximum(total)
            self.batch_progress.setValue(0)
            self.batch_result_table.setRowCount(0)
            self._batch_cancelled = False
            self._batch_futures = []
            self.run_batch_btn.setText("取消批量回测")
            self.run_batch_btn.clicked.disconnect()
            self.run_batch_btn.clicked.connect(self.cancel_batch_backtest)
            self.failed_tasks = []  # 记录失败任务
            results = []

            mode = self.mode_combo.currentText()
            distributed_backend = None
            remote_nodes = None
            if mode == "Dask分布式":
                distributed_backend = 'dask'
                remote_nodes = [
                    n.strip() for n in self.remote_nodes_edit.text().split(',') if n.strip()]

            def batch_task(code, strategy, params, pause_event):
                max_retries = 3
                for attempt in range(1, max_retries+1):
                    try:
                        for _ in range(10):
                            if pause_event.is_set():
                                while pause_event.is_set():
                                    time.sleep(0.2)
                        from core.trading_system import run_backtest
                        res = run_backtest(code, strategy, params)
                        return (code, strategy, params, res, None)
                    except Exception as e:
                        if attempt == max_retries:
                            return (code, strategy, params, None, f"{str(e)} (重试{attempt}次后失败)")
                        time.sleep(1)  # 重试间隔
                return (code, strategy, params, None, "未知错误")

            def on_done(future):
                if self._batch_cancelled:
                    return
                code, strategy, params, res, err = future.result()
                row = self.batch_result_table.rowCount()
                self.batch_result_table.insertRow(row)
                items = [code, strategy, str(params)]
                if res:
                    for key in ["annualized_return", "max_drawdown", "sharpe_ratio", "calmar_ratio", "sortino_ratio", "info_ratio", "win_rate", "profit_factor"]:
                        items.append(f"{res.get(key, '-')}")
                else:
                    items += ["异常"]*8
                self.batch_result_table.setItem(row, 0, QTableWidgetItem(code))
                self.batch_result_table.setItem(
                    row, 1, QTableWidgetItem(strategy))
                self.batch_result_table.setItem(
                    row, 2, QTableWidgetItem(str(params)))
                for col, val in enumerate(items[3:], 3):
                    self.batch_result_table.setItem(
                        row, col, QTableWidgetItem(val))
                if err:
                    self.batch_result_table.setItem(
                        row, 11, QTableWidgetItem("异常"))
                    self.failed_tasks.append(
                        {"code": code, "strategy": strategy, "params": params, "error": err})
                self.batch_progress.setValue(self.batch_progress.value()+1)
                if hasattr(self, 'results_area') and self.results_area:
                    self.results_area.append(
                        f"{code}-{strategy}-{params}: {'成功' if not err else '失败'}")
                if self.batch_progress.value() == self.batch_progress.maximum():
                    arr = []
                    for i in range(self.batch_result_table.rowCount()):
                        val = self.batch_result_table.item(i, 3)
                        try:
                            arr.append(float(val.text()) if val else 0)
                        except:
                            arr.append(0)
                    if arr:
                        best_idx = arr.index(max(arr))
                        self.batch_result_table.setItem(
                            best_idx, 11, QTableWidgetItem("最优"))
                    self.run_batch_btn.setText("一键批量回测")
                    self.run_batch_btn.clicked.disconnect()
                    self.run_batch_btn.clicked.connect(self.run_batch_backtest)
                # 日志区实时输出
                msg = f"{code}-{strategy}-{params}: {'成功' if not err else '失败'}"
                if hasattr(self, 'batch_log_area'):
                    self.batch_log_area.append(msg)
                # 状态颜色/动画
                if err:
                    for col in range(self.batch_result_table.columnCount()):
                        item = self.batch_result_table.item(row, col)
                        if item:
                            item.setBackground(Qt.red)
                else:
                    for col in range(self.batch_result_table.columnCount()):
                        item = self.batch_result_table.item(row, col)
                        if item:
                            item.setBackground(Qt.green)
                # 分组统计实时刷新
                self.update_group_stats()

            # 提交所有任务
            for code in codes:
                for strategy in strategies:
                    for params in param_combos:
                        if self._batch_cancelled:
                            break
                        pause_event = threading.Event()
                        self._batch_pause_events.append(pause_event)
                        future = self.async_manager.run_async(
                            batch_task, code, strategy, params, pause_event=pause_event)
                        future.add_done_callback(on_done)
                        self._batch_futures.append(future)

            if distributed_backend == 'dask':
                try:
                    tw = TradingWidget()
                    results = tw.run_batch_analysis(
                        codes, strategies, param_combos, distributed_backend='dask', remote_nodes=remote_nodes)
                    # 结果填充到表格
                    for r in results:
                        row = self.batch_result_table.rowCount()
                        self.batch_result_table.insertRow(row)
                        self.batch_result_table.setItem(
                            row, 0, QTableWidgetItem(r.get('code', '-')))
                        self.batch_result_table.setItem(
                            row, 1, QTableWidgetItem(r.get('strategy', '-')))
                        self.batch_result_table.setItem(
                            row, 2, QTableWidgetItem(str(r.get('params', '-'))))
                        self.batch_result_table.setItem(
                            row, 3, QTableWidgetItem(str(r.get('result', '-'))))
                    self.run_batch_btn.setText("一键批量回测")
                    self.run_batch_btn.clicked.disconnect()
                    self.run_batch_btn.clicked.connect(self.run_batch_backtest)
                    return
                except Exception as e:
                    QMessageBox.critical(self, "分布式批量回测异常", str(e))
                    return
        except Exception as e:
            QMessageBox.critical(self, "批量回测异常", str(e))

    def cancel_batch_backtest(self):
        self._batch_cancelled = True
        for f in self._batch_futures:
            f.cancel()
        self.run_batch_btn.setText("一键批量回测")
        self.run_batch_btn.clicked.disconnect()
        self.run_batch_btn.clicked.connect(self.run_batch_backtest)
        if hasattr(self, 'results_area') and self.results_area:
            self.results_area.append("批量回测已取消")

    def export_batch_results(self, filename=None):
        if not hasattr(self, 'batch_tasks') or not self.batch_tasks:
            QMessageBox.information(self, "无批量结果", "当前无可导出的批量分析结果")
            return
        if not filename:
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出批量分析结果", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
            if not filename:
                return
        # 汇总所有批量任务结果
        rows = []
        for task in self.batch_tasks:
            row = {
                '股票': task['stock'],
                '策略': task['strategy'],
                '参数': str(task['params']),
                '进度': self.batch_table.item(task['row'], 3).text() if self.batch_table.item(task['row'], 3) else '',
                '状态': self.batch_table.item(task['row'], 4).text() if self.batch_table.item(task['row'], 4) else ''
            }
            # 可扩展：流程节点、耗时、日志等
            rows.append(row)
        df = pd.DataFrame(rows)
        if filename.endswith('.xlsx'):
            df.to_excel(filename, index=False)
        else:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        QMessageBox.information(self, "导出成功", f"批量分析结果已导出到：{filename}")

    def get_openai_key(self):
        # TODO: 从配置或环境变量安全获取OpenAI API Key
        return "YOUR_OPENAI_API_KEY"

    def _run_analysis_async(self, button, analysis_func, *args, **kwargs):
        original_text = button.text()
        button.setText("取消")
        button._interrupted = False

        def on_cancel():
            button._interrupted = True
            button.setText(original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self._run_analysis_async(
                button, analysis_func, *args, **kwargs))

        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(on_cancel)

        def task():
            try:
                if not getattr(button, '_interrupted', False):
                    result = analysis_func(*args, **kwargs)
                    return result
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"分析异常: {str(e)}")
                return None
            finally:
                QTimer.singleShot(0, lambda: on_done(None))

        def on_done(future):
            button.setText(original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self._run_analysis_async(
                button, analysis_func, *args, **kwargs))
        from concurrent.futures import ThreadPoolExecutor
        if not hasattr(self, '_thread_pool'):
            self._thread_pool = ThreadPoolExecutor(max_workers=2)
        future = self._thread_pool.submit(task)
        # 只需在finally中恢复，无需重复回调

    def on_analysis_progress(self, info: dict):
        step_id = info.get('step_id')
        status = info.get('status')
        msg = info.get('msg', '')
        # 更新步骤状态
        self.step_status[step_id] = status
        self.refresh_step_list()
        # 更新进度条
        finished = sum(1 for s in self.step_status.values() if s == 'success')
        total = len(self.step_status)
        percent = int(finished / total * 100) if total else 0
        self.progress_bar.setValue(percent)

    def refresh_step_list(self):
        self.step_list.clear()
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            steps = self.trading_widget.process_manager.steps
            for step in steps:
                icon = QIcon()
                if step.status == 'success':
                    color = QColor(46, 204, 113)  # 绿色
                elif step.status == 'failed':
                    color = QColor(231, 76, 60)   # 红色
                elif step.status == 'running':
                    color = QColor(52, 152, 219)  # 蓝色
                else:
                    color = QColor(189, 195, 199)  # 灰色
                item = QListWidgetItem(f"{step.name}（{step.step_id}）")
                item.setBackground(QBrush(color.lighter(180)))
                if step.status == 'success':
                    item.setIcon(QIcon(':/icons/success.png'))
                elif step.status == 'failed':
                    item.setIcon(QIcon(':/icons/fail.png'))
                elif step.status == 'running':
                    item.setIcon(QIcon(':/icons/running.png'))
                else:
                    item.setIcon(QIcon(':/icons/pending.png'))
                if step.duration:
                    item.setText(item.text() + f"  ⏱{step.duration:.3f}s")
                # 鼠标悬停显示日志/错误
                tooltip = step.log or ''
                if step.error:
                    tooltip += f"\n错误: {step.error}"
                if tooltip:
                    item.setToolTip(tooltip)
                self.step_list.addItem(item)

    def show_process_flow_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("分析流程图")
        layout = QVBoxLayout(dialog)
        # 展示当前流程节点、状态、耗时
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            steps = self.trading_widget.process_manager.steps
            for step in steps:
                text = f"{step.name}（{step.step_id}）：{step.status}"
                if step.duration:
                    text += f"，耗时：{step.duration:.3f}s"
                layout.addWidget(QLabel(text))
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        dialog.exec_()

    def show_history_process_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("历史分析流程对比")
        layout = QVBoxLayout(dialog)
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            history = self.trading_widget.process_manager.get_history()
            for idx, steps in enumerate(history):
                layout.addWidget(QLabel(f"第{idx+1}次分析："))
                for step in steps:
                    text = f"  {step.name}（{step.step_id}）：{step.status}"
                    if step.duration:
                        text += f"，耗时：{step.duration:.3f}s"
                    layout.addWidget(QLabel(text))
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        dialog.exec_()

    def export_process_report(self, filename=None):
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出分析流程报告", "", "CSV Files (*.csv);;Text Files (*.txt)")
            if not filename:
                return
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            steps = self.trading_widget.process_manager.steps
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f) if filename.endswith('.csv') else None
                if writer:
                    writer.writerow(["步骤", "状态", "耗时(s)", "日志", "错误"])
                    for step in steps:
                        writer.writerow(
                            [step.name, step.status, f"{step.duration:.3f}" if step.duration else '', step.log, step.error])
                else:
                    for step in steps:
                        f.write(f"{step.name}（{step.step_id}）：{step.status}")
                        if step.duration:
                            f.write(f"，耗时：{step.duration:.3f}s")
                        if step.log:
                            f.write(f"\n日志：{step.log}")
                        if step.error:
                            f.write(f"\n错误：{step.error}")
                        f.write("\n")

    def show_process_flow_chart(self, compare_history=False):
        # 生成流程图，支持历史流程对比
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            if compare_history:
                all_flows = self.trading_widget.process_manager.get_history(
                ) + [self.trading_widget.process_manager.steps]
                fig = go.Figure()
                y_offset = 0
                for idx, steps in enumerate(all_flows):
                    nodes = [step.name for step in steps]
                    status_colors = {
                        'success': 'green',
                        'failed': 'red',
                        'running': 'blue',
                        'pending': 'gray'
                    }
                    node_colors = [status_colors.get(
                        step.status, 'gray') for step in steps]
                    edge_x, edge_y = [], []
                    for i in range(len(nodes)-1):
                        edge_x += [i, i+1, None]
                        edge_y += [y_offset, y_offset, None]
                    node_x = list(range(len(nodes)))
                    node_y = [y_offset]*len(nodes)
                    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(
                        color='black', width=2), showlegend=False))
                    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text',
                                             marker=dict(
                                                 size=40, color=node_colors),
                                             text=[
                                                 f"{step.name}<br>{step.status}<br>{step.duration:.3f}s" if step.duration else f"{step.name}<br>{step.status}" for step in steps],
                                             textposition='bottom center',
                                             customdata=[json.dumps(
                                                 {"日志": step.log, "耗时": step.duration, "错误": step.error}) for step in steps],
                                             hovertemplate='%{text}<br>点击查看详情',
                                             showlegend=False,
                                             name=f'流程{idx+1}'))
                    y_offset -= 1
                fig.update_layout(title='分析流程对比图', xaxis=dict(
                    visible=False), yaxis=dict(visible=False), plot_bgcolor='white')
            else:
                steps = self.trading_widget.process_manager.steps
                nodes = [step.name for step in steps]
                status_colors = {
                    'success': 'green',
                    'failed': 'red',
                    'running': 'blue',
                    'pending': 'gray'
                }
                node_colors = [status_colors.get(
                    step.status, 'gray') for step in steps]
                edge_x, edge_y = [], []
                for i in range(len(nodes)-1):
                    edge_x += [i, i+1, None]
                    edge_y += [0, 0, None]
                node_x = list(range(len(nodes)))
                node_y = [0]*len(nodes)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(
                    color='black', width=2), showlegend=False))
                fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text',
                                         marker=dict(
                                             size=40, color=node_colors),
                                         text=[
                                             f"{step.name}<br>{step.status}<br>{step.duration:.3f}s" if step.duration else f"{step.name}<br>{step.status}" for step in steps],
                                         textposition='bottom center',
                                         customdata=[json.dumps(
                                             {"日志": step.log, "耗时": step.duration, "错误": step.error}) for step in steps],
                                         hovertemplate='%{text}<br>点击查看详情',
                                         showlegend=False))
                fig.update_layout(title='分析流程图', xaxis=dict(
                    visible=False), yaxis=dict(visible=False), plot_bgcolor='white')
            # 展示到弹窗，支持节点点击
            html = fig.to_html(include_plotlyjs='cdn', full_html=False, config={
                               "displayModeBar": True})
            # 注入js监听点击事件，弹窗显示customdata
            html += '''
<script>
document.addEventListener('DOMContentLoaded', function() {
    var plot = document.querySelector('.js-plotly-plot');
    plot.on('plotly_click', function(data) {
        if(data.points && data.points[0] && data.points[0].customdata) {
            var detail = JSON.parse(data.points[0].customdata);
            var msg = '';
            for(var k in detail) { msg += k+': '+detail[k]+'\n'; }
            alert(msg);
        }
    });
});
</script>
'''
            self._show_html_dialog(html, title="分析流程图")

    def show_gantt_chart(self, compare_history=False):
        # 生成甘特图，支持历史流程对比
        if hasattr(self, 'trading_widget') and hasattr(self.trading_widget, 'process_manager'):
            if compare_history:
                all_flows = self.trading_widget.process_manager.get_history(
                ) + [self.trading_widget.process_manager.steps]
                df = []
                for idx, steps in enumerate(all_flows):
                    for step in steps:
                        if step.start_time and step.end_time:
                            df.append(dict(Task=f"流程{idx+1}-{step.name}", Start=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(step.start_time)),
                                           Finish=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(step.end_time)), Resource=step.status))
                if not df:
                    return
                fig = ff.create_gantt(
                    df, index_col='Resource', show_colorbar=True, group_tasks=True, title='多流程甘特图')
            else:
                steps = self.trading_widget.process_manager.steps
                df = []
                for step in steps:
                    if step.start_time and step.end_time:
                        df.append(dict(Task=step.name, Start=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(step.start_time)),
                                       Finish=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(step.end_time)), Resource=step.status))
                if not df:
                    return
                fig = ff.create_gantt(
                    df, index_col='Resource', show_colorbar=True, group_tasks=True, title='分析流程甘特图')
            html = fig.to_html(include_plotlyjs='cdn')
            self._show_html_dialog(html, title="分析流程甘特图")

    def _show_html_dialog(self, html, title="可视化图表"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        view = QWebEngineView()
        # 写入临时html文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
            f.write(html.encode('utf-8'))
            temp_path = f.name
        view.load(QUrl.fromLocalFile(os.path.abspath(temp_path)))
        layout.addWidget(view)
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        dialog.exec_()
        os.remove(temp_path)

    def export_failed_tasks(self):
        if not hasattr(self, 'failed_tasks') or not self.failed_tasks:
            QMessageBox.information(self, "导出失败日志", "当前没有失败任务")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出失败日志", "failed_tasks.csv", "CSV Files (*.csv)")
        if not file_path:
            return
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f, fieldnames=["code", "strategy", "params", "error"])
            writer.writeheader()
            for row in self.failed_tasks:
                writer.writerow(row)
        QMessageBox.information(self, "导出成功", f"失败日志已导出到: {file_path}")

    def update_progress_chart(self):
        if self.batch_start_time is None:
            return
        elapsed = int(time.time() - self.batch_start_time)
        total = self.batch_progress.maximum() if hasattr(self, 'batch_progress') else 100
        current = self.batch_progress.value() if hasattr(self, 'batch_progress') else 0
        percent = int(current / total * 100) if total else 0
        self.progress_data.append((elapsed, percent))
        self.progress_series.clear()
        for t, p in self.progress_data:
            self.progress_series.append(QPointF(t, p))
        self.progress_axis_x.setRange(0, max(10, elapsed))

    def update_group_stats(self):
        # 统计各策略/股票/参数的成功/失败分布
        stats = {}
        for row in range(self.batch_result_table.rowCount()):
            code = self.batch_result_table.item(row, 0).text()
            strategy = self.batch_result_table.item(row, 1).text()
            status = self.batch_result_table.item(row, 11).text(
            ) if self.batch_result_table.item(row, 11) else ""
            key = f"{strategy}-{code}"
            if key not in stats:
                stats[key] = {"成功": 0, "失败": 0}
            if status == "异常":
                stats[key]["失败"] += 1
            else:
                stats[key]["成功"] += 1
        lines = [f"{k}: 成功{v['成功']} 失败{v['失败']}" for k, v in stats.items()]
        self.group_stats_label.setText("分组统计：\n" + "\n".join(lines))

    def export_all_results(self):
        # 导出所有批量分析结果为Excel/CSV
        if self.batch_result_table.rowCount() == 0:
            QMessageBox.information(self, "导出结果", "当前无批量分析结果")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出全部结果", "batch_results.xlsx", "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if not file_path:
            return
        # 收集表格数据
        columns = [self.batch_result_table.horizontalHeaderItem(
            i).text() for i in range(self.batch_result_table.columnCount())]
        data = []
        for row in range(self.batch_result_table.rowCount()):
            data.append([self.batch_result_table.item(row, col).text() if self.batch_result_table.item(
                row, col) else '' for col in range(self.batch_result_table.columnCount())])
        df = pd.DataFrame(data, columns=columns)
        if file_path.endswith('.csv'):
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(file_path, index=False)
        QMessageBox.information(self, "导出成功", f"批量结果已导出到: {file_path}")

    def show_group_compare(self):
        # 分组对比弹窗，支持按策略、股票分组的年化收益/最大回撤等可视化
        if self.batch_result_table.rowCount() == 0:
            QMessageBox.information(self, "分组对比", "当前无批量分析结果")
            return
        columns = [self.batch_result_table.horizontalHeaderItem(
            i).text() for i in range(self.batch_result_table.columnCount())]
        data = []
        for row in range(self.batch_result_table.rowCount()):
            data.append([self.batch_result_table.item(row, col).text() if self.batch_result_table.item(
                row, col) else '' for col in range(self.batch_result_table.columnCount())])
        df = pd.DataFrame(data, columns=columns)
        # 按策略分组，统计年化收益、最大回撤均值
        if '策略' in df.columns and '年化收益率' in df.columns and '最大回撤' in df.columns:
            group = df.groupby('策略').agg(
                {'年化收益率': 'mean', '最大回撤': 'mean'}).reset_index()
            # 可视化
            fig, ax = plt.subplots(figsize=(6, 4))
            group.plot(x='策略', y=['年化收益率', '最大回撤'], kind='bar', ax=ax)
            ax.set_ylabel('均值')
            ax.set_title('策略分组对比')
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode('utf-8')
            html = f'<h3>策略分组对比</h3><img src="data:image/png;base64,{img_b64}"/>'
        else:
            html = '<p>当前结果不包含策略、年化收益率、最大回撤字段，无法分组对比。</p>'
        # 弹窗展示
        dlg = QDialog(self)
        dlg.setWindowTitle("分组对比")
        dlg.setMinimumSize(700, 500)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(html)
        layout.addWidget(text)
        btn = QPushButton("关闭")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec_()

    def update_task_queue(self):
        """
        实时刷新任务队列区，根据self.batch_tasks内容更新显示。
        """
        self.task_queue_list.clear()
        for i, task in enumerate(getattr(self, 'batch_tasks', [])):
            status = task.get('status', '等待中')
            item = QListWidgetItem(
                f"{i+1}. {task['stock']} | {task['strategy']} | {task['params']} | {status}")
            # 颜色高亮
            if status == '进行中':
                item.setBackground(Qt.yellow)
            elif status == '已完成':
                item.setBackground(Qt.green)
            elif status == '失败':
                item.setBackground(Qt.red)
            self.task_queue_list.addItem(item)

    def show_task_queue_menu(self, pos):
        """
        右键菜单：暂停/恢复/终止/重试/优先级调整单个任务
        """
        menu = QMenu()
        pause_action = menu.addAction("暂停任务")
        resume_action = menu.addAction("恢复任务")
        terminate_action = menu.addAction("终止任务")
        retry_action = menu.addAction("重试任务")
        menu.addSeparator()
        move_up_action = menu.addAction("上移")
        move_down_action = menu.addAction("下移")
        move_top_action = menu.addAction("置顶")
        move_bottom_action = menu.addAction("置底")
        item = self.task_queue_list.itemAt(pos)
        if not item:
            return
        row = self.task_queue_list.row(item)
        action = menu.exec_(self.task_queue_list.mapToGlobal(pos))
        if action == pause_action:
            self.pause_task_by_index(row)
        elif action == resume_action:
            self.resume_task_by_index(row)
        elif action == terminate_action:
            self.terminate_task_by_index(row)
        elif action == retry_action:
            self.retry_task_by_index(row)
        elif action == move_up_action:
            self.move_task_up(row)
        elif action == move_down_action:
            self.move_task_down(row)
        elif action == move_top_action:
            self.move_task_top(row)
        elif action == move_bottom_action:
            self.move_task_bottom(row)

    def move_task_up(self, idx):
        """将任务上移一位"""
        if 1 <= idx < len(self.batch_tasks):
            self.batch_tasks[idx -
                             1], self.batch_tasks[idx] = self.batch_tasks[idx], self.batch_tasks[idx-1]
            self.update_task_queue()
            self.task_queue_list.setCurrentRow(idx-1)

    def move_task_down(self, idx):
        """将任务下移一位"""
        if 0 <= idx < len(self.batch_tasks)-1:
            self.batch_tasks[idx], self.batch_tasks[idx +
                                                    1] = self.batch_tasks[idx+1], self.batch_tasks[idx]
            self.update_task_queue()
            self.task_queue_list.setCurrentRow(idx+1)

    def move_task_top(self, idx):
        """将任务置顶"""
        if 0 < idx < len(self.batch_tasks):
            task = self.batch_tasks.pop(idx)
            self.batch_tasks.insert(0, task)
            self.update_task_queue()
            self.task_queue_list.setCurrentRow(0)

    def move_task_bottom(self, idx):
        """将任务置底"""
        if 0 <= idx < len(self.batch_tasks)-1:
            task = self.batch_tasks.pop(idx)
            self.batch_tasks.append(task)
            self.update_task_queue()
            self.task_queue_list.setCurrentRow(len(self.batch_tasks)-1)

    # 批量优先级调整按钮
    def move_selected_tasks_up(self):
        """批量上移选中任务"""
        selected = sorted([self.task_queue_list.row(item)
                          for item in self.task_queue_list.selectedItems()])
        for idx in selected:
            self.move_task_up(idx)

    def move_selected_tasks_down(self):
        """批量下移选中任务"""
        selected = sorted([self.task_queue_list.row(
            item) for item in self.task_queue_list.selectedItems()], reverse=True)
        for idx in selected:
            self.move_task_down(idx)

    def move_selected_tasks_top(self):
        """批量置顶选中任务"""
        selected = sorted([self.task_queue_list.row(item)
                          for item in self.task_queue_list.selectedItems()])
        for idx in selected:
            self.move_task_top(idx)

    def move_selected_tasks_bottom(self):
        """批量置底选中任务"""
        selected = sorted([self.task_queue_list.row(
            item) for item in self.task_queue_list.selectedItems()], reverse=True)
        for idx in selected:
            self.move_task_bottom(idx)

    # 拖拽排序后同步batch_tasks顺序
    def dropEvent(self, event):
        super().dropEvent(event)
        self.sync_task_queue_to_batch_tasks()

    def sync_task_queue_to_batch_tasks(self):
        """根据QListWidget当前顺序同步self.batch_tasks"""
        new_order = []
        for i in range(self.task_queue_list.count()):
            text = self.task_queue_list.item(i).text()
            # 解析出原索引
            idx = int(text.split('.', 1)[0]) - 1
            if 0 <= idx < len(self.batch_tasks):
                new_order.append(self.batch_tasks[idx])
        if len(new_order) == len(self.batch_tasks):
            self.batch_tasks = new_order
        self.update_task_queue()

    def pause_task_by_index(self, idx):
        # 设置任务为暂停（实际挂起线程）
        if 0 <= idx < len(self.batch_tasks):
            self.batch_tasks[idx]['pause_event'].set()
            self.batch_tasks[idx]['status'] = '已暂停'
            self.update_task_queue()

    def resume_task_by_index(self, idx):
        if 0 <= idx < len(self.batch_tasks):
            self.batch_tasks[idx]['pause_event'].clear()
            self.batch_tasks[idx]['status'] = '进行中'
            self.update_task_queue()

    def terminate_task_by_index(self, idx):
        if 0 <= idx < len(self.batch_tasks):
            self.batch_tasks[idx]['terminate_flag'].set()
            self.batch_tasks[idx]['status'] = '已终止'
            self.update_task_queue()

    def retry_task_by_index(self, idx):
        # 终止后可重试，重置状态并重新启动线程
        if 0 <= idx < len(self.batch_tasks):
            task = self.batch_tasks[idx]
            if task['status'] in ['已终止', '失败']:
                # 重置事件和状态
                task['pause_event'] = threading.Event()
                task['terminate_flag'] = threading.Event()
                task['status'] = '等待中'
                self.update_task_queue()
                t = threading.Thread(
                    target=self.run_single_task_worker, args=(task, idx))
                task['thread'] = t
                t.start()
                self._task_threads.append(t)

    def run_single_task_worker(self, task, idx):
        # 单个任务的worker，便于重试
        row = task['row']
        task['status'] = '进行中'
        self.update_task_queue()
        self.batch_table.setItem(row, 3, QTableWidgetItem("进行中"))
        self.batch_table.setItem(row, 4, QTableWidgetItem("分析中"))
        for i in range(10):
            if task['terminate_flag'].is_set():
                task['status'] = '已终止'
                self.batch_table.setItem(row, 3, QTableWidgetItem("已终止"))
                self.batch_table.setItem(row, 4, QTableWidgetItem("终止"))
                self.update_task_queue()
                return
            while task['pause_event'].is_set():
                task['status'] = '已暂停'
                self.batch_table.setItem(row, 3, QTableWidgetItem("已暂停"))
                self.batch_table.setItem(row, 4, QTableWidgetItem("暂停"))
                self.update_task_queue()
                time.sleep(0.2)
            task['status'] = f'进行中({i+1}/10)'
            self.batch_table.setItem(
                row, 3, QTableWidgetItem(f"{int((i+1)/10*100)}%"))
            self.update_task_queue()
            time.sleep(0.3)
        task['status'] = '已完成'
        self.batch_table.setItem(row, 3, QTableWidgetItem("100%"))
        self.batch_table.setItem(row, 4, QTableWidgetItem("完成"))
        self.update_task_queue()

    def pause_selected_tasks(self):
        for item in self.task_queue_list.selectedItems():
            idx = self.task_queue_list.row(item)
            self.pause_task_by_index(idx)

    def resume_selected_tasks(self):
        for item in self.task_queue_list.selectedItems():
            idx = self.task_queue_list.row(item)
            self.resume_task_by_index(idx)

    def terminate_selected_tasks(self):
        for item in self.task_queue_list.selectedItems():
            idx = self.task_queue_list.row(item)
            self.terminate_task_by_index(idx)

    def retry_selected_tasks(self):
        for item in self.task_queue_list.selectedItems():
            idx = self.task_queue_list.row(item)
            self.retry_task_by_index(idx)

    def apply_advanced_filters(self):
        # 多条件组合筛选
        status = self.status_multi_filter.currentText()
        strategy = self.strategy_multi_filter.currentText()
        stock = self.stock_multi_filter.currentText()
        keyword = self.keyword_filter.text().strip().lower()
        for row, task in enumerate(self.batch_tasks):
            show = True
            if status != "全部状态" and task['status'] != status:
                show = False
            if strategy != "全部策略" and task['strategy'] != strategy:
                show = False
            if stock != "全部股票" and task['stock'] != stock:
                show = False
            if keyword:
                if keyword not in str(task['stock']).lower() and keyword not in str(task['strategy']).lower() and keyword not in str(task['status']).lower():
                    show = False
            self.batch_table.setRowHidden(row, not show)
        self.update_group_tree()

    def update_group_tree(self):
        # 树状分组+统计
        self.group_tree.clear()
        group_by = self.group_by_combo.currentText() if hasattr(
            self, 'group_by_combo') else "不分组"
        if group_by == "不分组":
            self.group_tree.setVisible(False)
            return
        group_map = {}
        for idx, task in enumerate(self.batch_tasks):
            if self.batch_table.isRowHidden(idx):
                continue
            if group_by == "按状态分组":
                key = task['status']
            elif group_by == "按策略分组":
                key = task['strategy']
            elif group_by == "按股票分组":
                key = task['stock']
            else:
                key = "其他"
            if key not in group_map:
                group_map[key] = []
            group_map[key].append(idx)
        for group, idxs in group_map.items():
            succ = sum(
                1 for i in idxs if self.batch_tasks[i]['status'] == '已完成')
            fail = sum(
                1 for i in idxs if self.batch_tasks[i]['status'] == '失败')
            total = len(idxs)
            progress = int(succ / total * 100) if total else 0
            group_item = QTreeWidgetItem(
                [str(group), str(succ), str(fail), str(total), f"{progress}%"])
            for i in idxs:
                t = self.batch_tasks[i]
                child = QTreeWidgetItem([f"{t['stock']}|{t['strategy']}", "✔" if t['status'] ==
                                        '已完成' else "✖" if t['status'] == '失败' else "", "", "", t['status']])
                group_item.addChild(child)
            self.group_tree.addTopLevelItem(group_item)
        self.group_tree.setVisible(True)

    def on_ai_stock_select(self):
        """
        一键AI选股：分批异步调用API，防止UI卡顿。
        """
        self.ai_stock_run_btn.setEnabled(False)
        self.ai_stock_run_btn.setText("选股中...")
        QApplication.processEvents()
        try:
            user_input = self.ai_stock_input.toPlainText().strip()
            if not user_input:
                QMessageBox.warning(self, "输入错误", "请输入选股需求或因子描述")
                return
            stock_data = self.get_all_stock_features()
            if not stock_data:
                QMessageBox.warning(self, "数据错误", "未能获取股票特征数据，请检查数据源")
                return
            batch_size = 500
            batches = [stock_data[i:i+batch_size]
                       for i in range(0, len(stock_data), batch_size)]
            criteria = {"query": user_input}
            url = "http://localhost:8000/api/ai/select_stocks"
            all_selected, all_explanations = [], {}
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(requests.post, url, json={"stock_data": batch,
                                           "criteria": criteria, "model_type": "ml"}, timeout=60) for batch in batches]
                for fut in as_completed(futures):
                    resp = fut.result()
                    if resp.status_code == 200:
                        data = resp.json()
                        all_selected.extend(data.get("selected", []))
                        all_explanations.update(data.get("explanations", {}))
            # 展示到表格
            self.ai_stock_result_table.clear()
            self.ai_stock_result_table.setColumnCount(2)
            self.ai_stock_result_table.setHorizontalHeaderLabels(
                ["股票代码", "推荐理由"])
            self.ai_stock_result_table.setRowCount(len(all_selected))
            for i, code in enumerate(all_selected):
                self.ai_stock_result_table.setItem(
                    i, 0, QTableWidgetItem(code))
                self.ai_stock_result_table.setItem(
                    i, 1, QTableWidgetItem(all_explanations.get(code, "")))
            if not all_selected:
                QMessageBox.information(self, "无结果", "未找到符合条件的股票")
            else:
                self.add_ai_selected_to_batch(all_selected)
            self.update_api_stats("智能选股", True, (time.time()-t0)*1000)
        except Exception as e:
            QMessageBox.critical(self, "选股异常", str(e))
            self.update_api_stats("智能选股", False, 0)
        finally:
            self.ai_stock_run_btn.setEnabled(True)
            self.ai_stock_run_btn.setText("一键AI选股")

    def get_all_stock_features(self):
        """
        批量获取全市场股票特征，供AI选股API使用。
        """
        try:
            # 优先用主窗口/数据管理器批量获取
            if hasattr(self, 'parent') and hasattr(self.parent(), 'data_manager'):
                data_manager = self.parent().data_manager
                df = data_manager.get_stock_list()
                if not df.empty:
                    return df.to_dict(orient='records')
            # 兜底：尝试用缓存
            if hasattr(self, 'stock_list_cache'):
                return self.stock_list_cache
        except Exception as e:
            print(f"获取股票特征失败: {e}")
        return []

    def add_ai_selected_to_batch(self, selected_codes):
        """
        一键将AI选股结果加入批量分析/回测队列。
        """
        try:
            # 假设有批量分析Tab和相关输入控件
            if hasattr(self, 'stock_input'):
                self.stock_input.setText(','.join(selected_codes))
                QMessageBox.information(
                    self, "已加入批量分析", f"已将{len(selected_codes)}只股票加入批量分析队列，可直接点击批量回测/分析。")
        except Exception as e:
            print(f"加入批量分析失败: {e}")

    def init_ai_optimizer_tab(self):
        """
        初始化AI参数优化助手Tab，包含输入区、一键优化按钮、结果展示。
        """
        self.ai_optimizer_tab = QWidget()
        layout = QVBoxLayout(self.ai_optimizer_tab)
        # 输入区
        input_layout = QHBoxLayout()
        self.ai_optimizer_strategy_input = QLineEdit()
        self.ai_optimizer_strategy_input.setPlaceholderText("策略名，如MA")
        input_layout.addWidget(QLabel("策略:"))
        input_layout.addWidget(self.ai_optimizer_strategy_input)
        self.ai_optimizer_param_input = QLineEdit()
        self.ai_optimizer_param_input.setPlaceholderText(
            "参数空间，如fast=5,10,20;slow=20,50,100")
        input_layout.addWidget(QLabel("参数空间:"))
        input_layout.addWidget(self.ai_optimizer_param_input)
        self.ai_optimizer_stock_input = QLineEdit()
        self.ai_optimizer_stock_input.setPlaceholderText("股票代码（可多只，逗号分隔）")
        input_layout.addWidget(QLabel("股票代码:"))
        input_layout.addWidget(self.ai_optimizer_stock_input)
        layout.addLayout(input_layout)
        # 一键优化按钮
        self.ai_optimizer_run_btn = QPushButton("一键参数优化")
        self.ai_optimizer_run_btn.clicked.connect(self.on_ai_optimizer_run)
        layout.addWidget(self.ai_optimizer_run_btn)
        # 结果展示表格
        self.ai_optimizer_result_table = QTableWidget()
        self.ai_optimizer_result_table.setColumnCount(3)
        self.ai_optimizer_result_table.setHorizontalHeaderLabels(
            ["股票代码", "最优参数", "优化过程"])
        layout.addWidget(self.ai_optimizer_result_table)
        # 一键应用到批量分析按钮
        self.ai_optimizer_apply_btn = QPushButton("一键应用到批量分析")
        self.ai_optimizer_apply_btn.clicked.connect(
            self.apply_ai_optimizer_to_batch)
        layout.addWidget(self.ai_optimizer_apply_btn)
        # 加入到TabWidget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.addTab(self.ai_optimizer_tab, "AI参数优化")
        self.init_ai_api_stats(layout, "参数优化")
        # 策略名补全
        strategy_names = ["MA", "MACD", "RSI", "BOLL", "KDJ", "DX"]
        completer = QCompleter(strategy_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.ai_optimizer_strategy_input.setCompleter(completer)
        # 股票代码补全
        if hasattr(self, 'get_all_stock_features'):
            codes = [s['code'] for s in self.get_all_stock_features()]
            completer2 = QCompleter(codes)
            completer2.setCaseSensitivity(Qt.CaseInsensitive)
            self.ai_optimizer_stock_input.setCompleter(completer2)
        # 参数模板补全
        param_templates = ["fast=5,10,20;slow=20,50,100",
                           "period=14,20,30", "std=1.5,2.0,2.5"]
        completer3 = QCompleter(param_templates)
        completer3.setCaseSensitivity(Qt.CaseInsensitive)
        self.ai_optimizer_param_input.setCompleter(completer3)
        # 可视化按钮
        self.ai_optimizer_vis_btn = QPushButton("结果可视化")
        self.ai_optimizer_vis_btn.clicked.connect(
            self.visualize_ai_optimizer_result)
        layout.addWidget(self.ai_optimizer_vis_btn)
        # 导出调用链日志按钮
        self.ai_optimizer_export_trace_btn = QPushButton("导出调用链日志")
        self.ai_optimizer_export_trace_btn.clicked.connect(
            self.export_last_trace_log)
        layout.addWidget(self.ai_optimizer_export_trace_btn)

    def on_ai_optimizer_run(self):
        """
        一键参数优化：分批异步调用API，防止UI卡顿。
        """
        self.ai_optimizer_run_btn.setEnabled(False)
        self.ai_optimizer_run_btn.setText("优化中...")
        QApplication.processEvents()
        try:
            strategy = self.ai_optimizer_strategy_input.text().strip()
            if not strategy:
                QMessageBox.warning(self, "输入错误", "请输入策略名")
                return
            param_str = self.ai_optimizer_param_input.text().strip()
            param_space = self.parse_param_space(param_str)
            codes = self.ai_optimizer_stock_input.text().strip()
            code_list = [c.strip() for c in codes.split(',') if c.strip()]
            history = self.get_stocks_history(code_list)
            batch_size = 5
            batches = [code_list[i:i+batch_size]
                       for i in range(0, len(code_list), batch_size)]
            url = "http://localhost:8000/api/ai/optimize_params"
            t0 = time.time()
            all_best_params, all_process = [], []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(requests.post, url, json={
                                           "strategy": strategy, "param_space": param_space, "history": self.get_stocks_history(batch)}, timeout=120) for batch in batches]
                for fut in as_completed(futures):
                    resp = fut.result()
                    if resp.status_code == 200:
                        data = resp.json()
                        all_best_params.append(data.get("best_params", {}))
                        all_process.append(data.get("process", []))
            # 展示到表格
            self.ai_optimizer_result_table.clear()
            self.ai_optimizer_result_table.setColumnCount(3)
            self.ai_optimizer_result_table.setHorizontalHeaderLabels(
                ["股票代码", "最优参数", "优化过程"])
            self.ai_optimizer_result_table.setRowCount(len(code_list))
            for i, code in enumerate(code_list):
                self.ai_optimizer_result_table.setItem(
                    i, 0, QTableWidgetItem(code))
                self.ai_optimizer_result_table.setItem(i, 1, QTableWidgetItem(
                    str(all_best_params[i]) if i < len(all_best_params) else ""))
                self.ai_optimizer_result_table.setItem(i, 2, QTableWidgetItem(
                    str(all_process[i]) if i < len(all_process) else ""))
            if not all_best_params:
                QMessageBox.information(self, "无结果", "未能找到最优参数")
            self.update_api_stats("参数优化", True, (time.time()-t0)*1000)
        except Exception as e:
            QMessageBox.critical(self, "优化异常", str(e))
            self.update_api_stats("参数优化", False, 0)
        finally:
            self.ai_optimizer_run_btn.setEnabled(True)
            self.ai_optimizer_run_btn.setText("一键参数优化")

    def parse_param_space(self, param_str):
        """
        解析参数空间字符串为dict，如fast=5,10,20;slow=20,50,100 -> {'fast': [5,10,20], 'slow': [20,50,100]}
        """
        param_space = {}
        try:
            for part in param_str.split(';'):
                if '=' in part:
                    k, v = part.split('=', 1)
                    values = [float(x) if '.' in x else int(x)
                              for x in v.split(',') if x.strip()]
                    param_space[k.strip()] = values
        except Exception as e:
            print(f"参数空间解析失败: {e}")
        return param_space

    def apply_ai_optimizer_to_batch(self):
        """
        一键将最优参数应用到批量分析/回测。
        """
        try:
            # 取表格中的股票和最优参数
            codes = []
            best_params = None
            for row in range(self.ai_optimizer_result_table.rowCount()):
                code = self.ai_optimizer_result_table.item(row, 0).text()
                codes.append(code)
                if not best_params:
                    best_params = self.ai_optimizer_result_table.item(
                        row, 1).text()
            # 应用到批量分析输入
            if hasattr(self, 'stock_input') and hasattr(self, 'param_input'):
                self.stock_input.setText(','.join(codes))
                self.param_input.setText(best_params)
                QMessageBox.information(
                    self, "已应用到批量分析", f"已将最优参数和股票应用到批量分析队列，可直接点击批量回测/分析。")
        except Exception as e:
            print(f"应用到批量分析失败: {e}")

    def visualize_ai_optimizer_result(self):
        """
        可视化AI参数优化结果，柱状图展示各股票最优参数分布。
        """
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            # 统计最优参数分布
            param_count = {}
            for row in range(self.ai_optimizer_result_table.rowCount()):
                param = self.ai_optimizer_result_table.item(row, 1).text()
                param_count[param] = param_count.get(param, 0) + 1
            fig = go.Figure(
                [go.Bar(x=list(param_count.keys()), y=list(param_count.values()))])
            fig.update_layout(
                title="最优参数分布", xaxis_title="参数", yaxis_title="股票数")
            html = fig.to_html(include_plotlyjs='cdn')
            dlg = QDialog(self)
            dlg.setWindowTitle("AI参数优化结果可视化")
            layout = QVBoxLayout(dlg)
            web = QWebEngineView()
            web.setHtml(html)
            layout.addWidget(web)
            dlg.resize(600, 400)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "可视化失败", str(e))

    def init_ai_diagnosis_tab(self):
        """
        初始化AI智能诊断助手Tab，包含输入区、一键诊断按钮、结果展示。
        """
        self.ai_diagnosis_tab = QWidget()
        layout = QVBoxLayout(self.ai_diagnosis_tab)
        # 输入区
        self.ai_diagnosis_input = QTextEdit()
        self.ai_diagnosis_input.setPlaceholderText("粘贴回测/分析结果JSON，或自动填充")
        layout.addWidget(QLabel("回测/分析结果（JSON）:"))
        layout.addWidget(self.ai_diagnosis_input)
        # 一键诊断按钮
        self.ai_diagnosis_run_btn = QPushButton("一键智能诊断")
        self.ai_diagnosis_run_btn.clicked.connect(self.on_ai_diagnosis_run)
        layout.addWidget(self.ai_diagnosis_run_btn)
        # 结果展示区
        self.ai_diagnosis_result = QTextEdit()
        self.ai_diagnosis_result.setReadOnly(True)
        layout.addWidget(QLabel("AI诊断建议/风险提示："))
        layout.addWidget(self.ai_diagnosis_result)
        # 一键导出报告按钮
        self.ai_diagnosis_export_btn = QPushButton("导出诊断报告")
        self.ai_diagnosis_export_btn.clicked.connect(
            self.export_ai_diagnosis_report)
        layout.addWidget(self.ai_diagnosis_export_btn)
        # 加入到TabWidget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.addTab(self.ai_diagnosis_tab, "AI智能诊断")
        self.init_ai_api_stats(layout, "智能诊断")
        # 自动填充按钮
        self.ai_diagnosis_autofill_btn = QPushButton("自动填充最近回测结果")
        self.ai_diagnosis_autofill_btn.clicked.connect(
            self.autofill_latest_analysis_result)
        layout.addWidget(self.ai_diagnosis_autofill_btn)
        # 导出调用链日志按钮
        self.ai_diagnosis_export_trace_btn = QPushButton("导出调用链日志")
        self.ai_diagnosis_export_trace_btn.clicked.connect(
            self.export_last_trace_log)
        layout.addWidget(self.ai_diagnosis_export_trace_btn)

    def autofill_latest_analysis_result(self):
        """
        自动填充最近回测/分析结果到诊断输入区。
        """
        try:
            # 假设有recent_analysis_result属性或方法
            result = getattr(self, 'recent_analysis_result', None)
            if result is None and hasattr(self.parent(), 'analysis_tools'):
                result = getattr(self.parent().analysis_tools,
                                 'recent_analysis_result', None)
            if result:
                self.ai_diagnosis_input.setPlainText(
                    json.dumps(result, ensure_ascii=False, indent=2))
                QMessageBox.information(self, "已填充", "已自动填充最近回测/分析结果")
            else:
                QMessageBox.warning(self, "无数据", "未找到最近回测/分析结果，请先运行回测/分析")
        except Exception as e:
            QMessageBox.critical(self, "填充失败", str(e))

    def on_ai_diagnosis_run(self):
        """
        一键智能诊断：调用API，展示AI诊断建议和风险提示。
        """
        self.ai_diagnosis_run_btn.setEnabled(False)
        self.ai_diagnosis_run_btn.setText("诊断中...")
        QApplication.processEvents()
        try:
            input_text = self.ai_diagnosis_input.toPlainText().strip()
            if not input_text:
                QMessageBox.warning(self, "输入错误", "请粘贴回测/分析结果JSON")
                return
            try:
                result_data = json.loads(input_text)
            except Exception as e:
                QMessageBox.warning(self, "格式错误", f"JSON解析失败: {e}")
                return
            payload = {"result": result_data}
            url = "http://localhost:8000/api/ai/diagnosis"
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                advice = data.get("advice", "无AI诊断建议")
                risks = data.get("risks", "无风险提示")
                self.ai_diagnosis_result.setPlainText(
                    f"【AI诊断建议】\n{advice}\n\n【风险提示】\n{risks}")
                self.update_api_stats("智能诊断", True, (time.time()-t0)*1000)
            else:
                QMessageBox.critical(
                    self, "诊断失败", f"API请求失败: {resp.status_code}")
                self.update_api_stats("智能诊断", False, (time.time()-t0)*1000)
        except Exception as e:
            QMessageBox.critical(self, "诊断异常", str(e))
            self.update_api_stats("智能诊断", False, (time.time()-t0)*1000)
        finally:
            self.ai_diagnosis_run_btn.setEnabled(True)
            self.ai_diagnosis_run_btn.setText("一键智能诊断")

    def export_ai_diagnosis_report(self):
        """
        导出AI诊断报告为txt文件。
        """
        try:
            text = self.ai_diagnosis_result.toPlainText()
            if not text:
                QMessageBox.warning(self, "无内容", "请先完成AI诊断")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                None, "导出诊断报告", "ai_diagnosis_report.txt", "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "导出成功", f"诊断报告已导出到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def visualize_ai_strategy_result(self):
        """
        可视化AI策略推荐结果，分组柱状图展示各策略推荐数量。
        """
        try:
            # 统计推荐策略分布
            strat_count = {}
            for row in range(self.ai_strategy_result_table.rowCount()):
                strat = self.ai_strategy_result_table.item(row, 1).text()
                strat_count[strat] = strat_count.get(strat, 0) + 1
            fig = go.Figure(
                [go.Bar(x=list(strat_count.keys()), y=list(strat_count.values()))])
            fig.update_layout(
                title="推荐策略分布", xaxis_title="策略", yaxis_title="推荐次数")
            html = fig.to_html(include_plotlyjs='cdn')
            dlg = QDialog(self)
            dlg.setWindowTitle("AI策略推荐结果可视化")
            layout = QVBoxLayout(dlg)
            web = QWebEngineView()
            web.setHtml(html)
            layout.addWidget(web)
            dlg.resize(600, 400)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "可视化失败", str(e))

    def visualize_ai_stock_result(self):
        """
        可视化AI选股结果，饼图展示各推荐理由分布。
        """
        try:
            # 统计推荐理由分布
            reason_count = {}
            for row in range(self.ai_stock_result_table.rowCount()):
                reason = self.ai_stock_result_table.item(row, 1).text()
                reason_count[reason] = reason_count.get(reason, 0) + 1
            fig = go.Figure(
                [go.Pie(labels=list(reason_count.keys()), values=list(reason_count.values()))])
            fig.update_layout(title="推荐理由分布")
            html = fig.to_html(include_plotlyjs='cdn')
            dlg = QDialog(self)
            dlg.setWindowTitle("AI选股结果可视化")
            layout = QVBoxLayout(dlg)
            web = QWebEngineView()
            web.setHtml(html)
            layout.addWidget(web)
            dlg.resize(600, 400)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "可视化失败", str(e))

    def call_ai_api(self, api_func, *args, **kwargs):
        """
        封装AI API调用，自动生成trace_id，日志带trace_id，便于调用链追踪。
        """
        trace_id = str(uuid.uuid4())
        self.last_trace_id = trace_id
        try:
            self.log_manager.info(
                f"开始调用AI API: {api_func.__name__}", trace_id=trace_id)
            result = api_func(*args, trace_id=trace_id, **kwargs)
            self.log_manager.info(
                f"AI API调用成功: {api_func.__name__}", trace_id=trace_id)
            return result
        except Exception as e:
            self.log_manager.error(
                f"AI API调用异常: {api_func.__name__} - {str(e)}", trace_id=trace_id)
            raise

    def export_last_trace_log(self):
        """
        一键导出最近一次trace_id的调用链日志
        """
        if hasattr(self, 'last_trace_id') and self.last_trace_id:
            log_content = self.log_manager.get_last_trace_log(
                self.last_trace_id)
            # 可弹窗显示或保存为文件
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出调用链日志", f"trace_{self.last_trace_id}.log", "Log Files (*.log)")
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)

    def export_batch_trace_log(self):
        """
        导出当前批量任务队列相关trace_id的全部日志
        """
        trace_ids = getattr(self, 'batch_task_trace_ids', [])
        if not trace_ids:
            QMessageBox.information(self, "导出队列日志", "当前无批量任务trace_id记录")
            return
        log_content = ""
        for tid in trace_ids:
            log_content += f"\n--- trace_id={tid} ---\n"
            log_content += self.log_manager.get_last_trace_log(tid)
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出队列日志", "batch_trace.log", "Log Files (*.log)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(log_content)

    def refresh_strategy_list(self):
        """刷新策略列表"""
        try:
            # 清空现有策略
            self.strategy_combo.clear()
            self.batch_strategy_list.clear()

            # 重新加载策略
            available_strategies = list_available_strategies()

            if available_strategies:
                # 更新单个策略选择
                self.strategy_combo.addItems(available_strategies)

                # 更新批量策略选择
                for strategy in available_strategies:
                    self.batch_strategy_list.addItem(strategy)

                self.log_manager.info(
                    f"策略列表已刷新，共 {len(available_strategies)} 个策略")

                # 发送状态更新信号
                if hasattr(self, 'set_status_message'):
                    self.set_status_message(
                        f"策略列表已刷新，共 {len(available_strategies)} 个策略")

            else:
                self.log_manager.warning("策略管理系统未返回任何策略")
                if hasattr(self, 'set_status_message'):
                    self.set_status_message("未找到可用策略", error=True)

        except Exception as e:
            error_msg = f"刷新策略列表失败: {str(e)}"
            self.log_manager.error(error_msg)
            if hasattr(self, 'set_status_message'):
                self.set_status_message(error_msg, error=True)

    def get_selected_strategy(self):
        """获取当前选择的策略"""
        return self.strategy_combo.currentText() if self.strategy_combo else None

    def get_selected_batch_strategies(self):
        """获取批量选择的策略列表"""
        if not self.batch_strategy_list:
            return []

        selected_items = self.batch_strategy_list.selectedItems()
        return [item.text() for item in selected_items]


class StatusBar(QStatusBar):
    """
    自定义状态栏，支持状态信息、进度条、错误提示和永久控件。
    兼容主窗口和各类UI组件的调用。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_label = QLabel("就绪")
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(180)
        self._progress_bar.setMinimumWidth(120)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self.addWidget(self._status_label)
        self.addWidget(self._progress_bar)
        self._error_mode = False

    def set_status(self, message: str, error: bool = False):
        """
        设置状态栏文本，支持高亮错误。
        """
        self._status_label.setText(message)
        if error:
            self._status_label.setStyleSheet("color: red;")
            self._error_mode = True
        else:
            self._status_label.setStyleSheet("")
            self._error_mode = False
        self.showMessage(message, 5000 if not error else 8000)

    def show_progress(self, visible: bool = True):
        """
        显示或隐藏进度条。
        """
        self._progress_bar.setVisible(visible)
        if not visible:
            self._progress_bar.setValue(0)
            self._progress_bar.setStyleSheet("")

    def set_progress(self, value: int):
        """
        设置进度条进度。
        """
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(max(0, min(100, int(value))))
        self._progress_bar.setStyleSheet("")

    def set_progress_error(self, message: str = "发生错误"):
        """
        进度条显示错误状态。
        """
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(100)
        self._progress_bar.setStyleSheet(
            "QProgressBar::chunk {background-color: #FF1744;}")
        self.set_status(message, error=True)

    def addPermanentWidget(self, widget: QWidget, stretch: int = 0):
        """
        添加永久控件（如日志按钮），兼容QStatusBar接口。
        """
        super().addPermanentWidget(widget, stretch)

    def clear_status(self):
        """
        清除状态栏信息和进度。
        """
        self._status_label.setText("")
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet("")
        self._error_mode = False
