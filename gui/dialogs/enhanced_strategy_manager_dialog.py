"""
增强策略管理对话框

与重构后的StrategyService和TradingService完全集成，提供：
1. 策略列表显示和管理
2. 策略创建向导
3. 策略参数配置
4. 策略状态监控
5. 策略性能展示
6. 回测和优化功能
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import asdict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QTextEdit, QLineEdit,
    QGroupBox, QFormLayout, QPushButton, QScrollArea, QSplitter,
    QHeaderView, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QProgressDialog, QInputDialog,
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QFrame, QGridLayout, QSlider, QDateEdit,
    QApplication, QMenu, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor, QPalette

# 导入服务和数据结构
from core.services.strategy_service import StrategyService, StrategyConfig, BacktestStatus, OptimizationStatus
from core.services.trading_service import TradingService, StrategyState
from core.strategy_extensions import (
    StrategyContext, StandardMarketData, TimeFrame, AssetType,
    StrategyType, RiskLevel, ParameterDef
)

logger = logging.getLogger(__name__)


class StrategyCreationWizard(QDialog):
    """策略创建向导"""

    strategy_created = pyqtSignal(dict)

    def __init__(self, parent=None, strategy_service=None):
        super().__init__(parent)
        self.strategy_service = strategy_service
        self.setWindowTitle("策略创建向导")
        self.setModal(True)
        self.resize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 步骤1: 选择策略类型
        step1_group = QGroupBox("步骤1: 选择策略框架")
        step1_layout = QFormLayout(step1_group)

        self.plugin_type_combo = QComboBox()
        if self.strategy_service:
            plugin_types = self.strategy_service.get_available_plugin_types()
            self.plugin_type_combo.addItems(plugin_types)

        step1_layout.addRow("策略框架:", self.plugin_type_combo)
        layout.addWidget(step1_group)

        # 步骤2: 基本信息
        step2_group = QGroupBox("步骤2: 基本信息")
        step2_layout = QFormLayout(step2_group)

        self.strategy_id_edit = QLineEdit()
        self.strategy_name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)

        step2_layout.addRow("策略ID:", self.strategy_id_edit)
        step2_layout.addRow("策略名称:", self.strategy_name_edit)
        step2_layout.addRow("描述:", self.description_edit)
        layout.addWidget(step2_group)

        # 步骤3: 参数配置
        step3_group = QGroupBox("步骤3: 参数配置")
        self.params_layout = QFormLayout(step3_group)
        self.param_widgets = {}

        # 根据选择的插件类型动态更新参数
        self.plugin_type_combo.currentTextChanged.connect(self._update_parameters)
        self._update_parameters()

        layout.addWidget(step3_group)

        # 按钮
        button_layout = QHBoxLayout()

        create_button = QPushButton("创建策略")
        create_button.clicked.connect(self._create_strategy)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(create_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _update_parameters(self):
        """根据选择的插件类型更新参数配置"""
        # 清除现有参数控件
        for i in reversed(range(self.params_layout.count())):
            self.params_layout.itemAt(i).widget().setParent(None)
        self.param_widgets.clear()

        plugin_type = self.plugin_type_combo.currentText()
        if not plugin_type or not self.strategy_service:
            return

        # 获取插件信息
        plugin_info = self.strategy_service.get_strategy_plugin_info(plugin_type)
        if not plugin_info:
            return

        # 创建插件实例获取策略信息
        plugin = self.strategy_service.create_strategy_plugin(plugin_type)
        if not plugin:
            return

        strategy_info = plugin.get_strategy_info()

        # 为每个参数创建控件
        for param_def in strategy_info.parameters:
            widget = self._create_parameter_widget(param_def)
            if widget:
                self.param_widgets[param_def.name] = widget
                self.params_layout.addRow(f"{param_def.display_name}:", widget)

    def _create_parameter_widget(self, param_def: ParameterDef):
        """为参数定义创建对应的控件"""
        if param_def.type == int:
            widget = QSpinBox()
            if param_def.min_value is not None:
                widget.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                widget.setMaximum(param_def.max_value)
            if param_def.default_value is not None:
                widget.setValue(param_def.default_value)
            return widget

        elif param_def.type == float:
            widget = QDoubleSpinBox()
            widget.setDecimals(4)
            if param_def.min_value is not None:
                widget.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                widget.setMaximum(param_def.max_value)
            if param_def.default_value is not None:
                widget.setValue(param_def.default_value)
            return widget

        elif param_def.type == str:
            if hasattr(param_def, 'choices') and param_def.choices:
                widget = QComboBox()
                widget.addItems(param_def.choices)
                if param_def.default_value:
                    widget.setCurrentText(str(param_def.default_value))
                return widget
            else:
                widget = QLineEdit()
                if param_def.default_value:
                    widget.setText(str(param_def.default_value))
                return widget

        elif param_def.type == bool:
            widget = QCheckBox()
            if param_def.default_value is not None:
                widget.setChecked(param_def.default_value)
            return widget

        return None

    def _create_strategy(self):
        """创建策略"""
        try:
            # 验证输入
            strategy_id = self.strategy_id_edit.text().strip()
            if not strategy_id:
                QMessageBox.warning(self, "警告", "请输入策略ID")
                return

            plugin_type = self.plugin_type_combo.currentText()
            if not plugin_type:
                QMessageBox.warning(self, "警告", "请选择策略框架")
                return

            # 收集参数
            parameters = {}
            for param_name, widget in self.param_widgets.items():
                if isinstance(widget, QSpinBox):
                    parameters[param_name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    parameters[param_name] = widget.value()
                elif isinstance(widget, QLineEdit):
                    parameters[param_name] = widget.text()
                elif isinstance(widget, QComboBox):
                    parameters[param_name] = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    parameters[param_name] = widget.isChecked()

            # 创建策略配置
            metadata = {
                'name': self.strategy_name_edit.text().strip(),
                'description': self.description_edit.toPlainText().strip(),
                'created_by': 'user',
                'created_at': datetime.now().isoformat()
            }

            success = self.strategy_service.create_strategy_config(
                strategy_id=strategy_id,
                plugin_type=plugin_type,
                parameters=parameters,
                metadata=metadata
            )

            if success:
                QMessageBox.information(self, "成功", f"策略 '{strategy_id}' 创建成功")
                self.strategy_created.emit({
                    'strategy_id': strategy_id,
                    'plugin_type': plugin_type,
                    'parameters': parameters,
                    'metadata': metadata
                })
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "策略创建失败")

        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            QMessageBox.critical(self, "错误", f"创建策略失败: {e}")


class BacktestProgressDialog(QDialog):
    """回测进度对话框"""

    def __init__(self, parent=None, strategy_service=None, task_id=None):
        super().__init__(parent)
        self.strategy_service = strategy_service
        self.task_id = task_id
        self.setWindowTitle("回测进行中")
        self.setModal(True)
        self.resize(400, 200)
        self._setup_ui()

        # 定时器更新进度
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(1000)  # 每秒更新一次

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        self.status_label = QLabel("正在初始化回测...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        layout.addWidget(self.details_text)

        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._cancel_backtest)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _update_progress(self):
        """更新进度"""
        if not self.strategy_service or not self.task_id:
            return

        status = self.strategy_service.get_backtest_status(self.task_id)
        if not status:
            return

        # 更新进度条
        progress = int(status['progress'] * 100)
        self.progress_bar.setValue(progress)

        # 更新状态文本
        status_text = {
            'pending': '等待中...',
            'running': f'运行中... ({progress}%)',
            'completed': '完成',
            'failed': '失败',
            'cancelled': '已取消'
        }.get(status['status'], '未知状态')

        self.status_label.setText(status_text)

        # 更新详细信息
        if status.get('error_message'):
            self.details_text.setText(f"错误: {status['error_message']}")
        else:
            self.details_text.setText(f"任务ID: {self.task_id}\n开始时间: {status.get('started_at', 'N/A')}")

        # 如果完成或失败，关闭对话框
        if status['status'] in ['completed', 'failed', 'cancelled']:
            self.timer.stop()
            if status['status'] == 'completed':
                self.accept()
            else:
                self.reject()

    def _cancel_backtest(self):
        """取消回测"""
        if self.strategy_service and self.task_id:
            self.strategy_service.cancel_backtest(self.task_id)
        self.reject()


class EnhancedStrategyManagerDialog(QDialog):
    """增强策略管理对话框"""

    # 信号
    strategy_selected = pyqtSignal(str)  # 策略ID
    strategy_started = pyqtSignal(str)   # 策略ID
    strategy_stopped = pyqtSignal(str)   # 策略ID

    def __init__(self, parent=None, strategy_service=None, trading_service=None):
        """
        初始化增强策略管理对话框

        Args:
            parent: 父窗口
            strategy_service: 策略服务
            trading_service: 交易服务
        """
        super().__init__(parent)
        self.strategy_service = strategy_service
        self.trading_service = trading_service
        self.current_strategy_id = None

        self.setWindowTitle("策略管理器")
        self.setModal(False)  # 非模态对话框，允许与主窗口交互
        self.resize(1200, 800)

        self._setup_ui()
        self._setup_timers()
        self._load_strategies()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 左侧：策略列表和操作
        left_widget = self._create_left_panel()
        splitter.addWidget(left_widget)

        # 右侧：策略详情和监控
        right_widget = self._create_right_panel()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([400, 800])

    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 策略列表
        list_group = QGroupBox("策略列表")
        list_layout = QVBoxLayout(list_group)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        create_button = QPushButton("创建策略")
        create_button.clicked.connect(self._create_strategy)

        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self._load_strategies)

        import_button = QPushButton("导入")
        import_button.clicked.connect(self._import_strategy)

        toolbar_layout.addWidget(create_button)
        toolbar_layout.addWidget(refresh_button)
        toolbar_layout.addWidget(import_button)
        toolbar_layout.addStretch()

        list_layout.addLayout(toolbar_layout)

        # 策略列表表格
        self.strategy_table = QTableWidget()
        self.strategy_table.setColumnCount(5)
        self.strategy_table.setHorizontalHeaderLabels([
            "策略ID", "框架", "状态", "性能", "操作"
        ])

        # 设置表格属性
        header = self.strategy_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.strategy_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.strategy_table.setSelectionMode(QTableWidget.SingleSelection)
        self.strategy_table.itemSelectionChanged.connect(self._on_strategy_selected)

        list_layout.addWidget(self.strategy_table)
        layout.addWidget(list_group)

        return widget

    def _create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 策略详情选项卡
        self._create_details_tab()

        # 参数配置选项卡
        self._create_config_tab()

        # 回测选项卡
        self._create_backtest_tab()

        # 优化选项卡
        self._create_optimization_tab()

        # 监控选项卡
        self._create_monitoring_tab()

        return widget

    def _create_details_tab(self):
        """创建策略详情选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)

        self.strategy_id_label = QLabel("未选择")
        self.plugin_type_label = QLabel("未选择")
        self.created_at_label = QLabel("未选择")
        self.status_label = QLabel("未选择")

        info_layout.addRow("策略ID:", self.strategy_id_label)
        info_layout.addRow("框架类型:", self.plugin_type_label)
        info_layout.addRow("创建时间:", self.created_at_label)
        info_layout.addRow("当前状态:", self.status_label)

        layout.addWidget(info_group)

        # 描述信息
        desc_group = QGroupBox("描述信息")
        desc_layout = QVBoxLayout(desc_group)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)

        desc_layout.addWidget(self.description_text)
        layout.addWidget(desc_group)

        # 性能统计
        perf_group = QGroupBox("性能统计")
        perf_layout = QFormLayout(perf_group)

        self.total_return_label = QLabel("N/A")
        self.sharpe_ratio_label = QLabel("N/A")
        self.max_drawdown_label = QLabel("N/A")
        self.win_rate_label = QLabel("N/A")

        perf_layout.addRow("总收益率:", self.total_return_label)
        perf_layout.addRow("夏普比率:", self.sharpe_ratio_label)
        perf_layout.addRow("最大回撤:", self.max_drawdown_label)
        perf_layout.addRow("胜率:", self.win_rate_label)

        layout.addWidget(perf_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("启动策略")
        self.start_button.clicked.connect(self._start_strategy)
        self.start_button.setEnabled(False)

        self.stop_button = QPushButton("停止策略")
        self.stop_button.clicked.connect(self._stop_strategy)
        self.stop_button.setEnabled(False)

        self.delete_button = QPushButton("删除策略")
        self.delete_button.clicked.connect(self._delete_strategy)
        self.delete_button.setEnabled(False)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        layout.addStretch()

        self.tab_widget.addTab(tab, "策略详情")

    def _create_config_tab(self):
        """创建参数配置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 参数配置区域
        config_group = QGroupBox("参数配置")
        self.config_layout = QFormLayout(config_group)
        self.config_widgets = {}

        layout.addWidget(config_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        save_button = QPushButton("保存配置")
        save_button.clicked.connect(self._save_config)

        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self._reset_config)

        button_layout.addWidget(save_button)
        button_layout.addWidget(reset_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        layout.addStretch()

        self.tab_widget.addTab(tab, "参数配置")

    def _create_backtest_tab(self):
        """创建回测选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 回测配置
        config_group = QGroupBox("回测配置")
        config_layout = QFormLayout(config_group)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDateTime.currentDateTime().addDays(-365).date())
        self.start_date_edit.setCalendarPopup(True)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDateTime.currentDateTime().date())
        self.end_date_edit.setCalendarPopup(True)

        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(1000, 10000000)
        self.initial_capital_spin.setValue(100000)
        self.initial_capital_spin.setSuffix(" 元")

        self.commission_rate_spin = QDoubleSpinBox()
        self.commission_rate_spin.setRange(0, 0.01)
        self.commission_rate_spin.setValue(0.0003)
        self.commission_rate_spin.setDecimals(4)
        self.commission_rate_spin.setSuffix("%")

        config_layout.addRow("开始日期:", self.start_date_edit)
        config_layout.addRow("结束日期:", self.end_date_edit)
        config_layout.addRow("初始资金:", self.initial_capital_spin)
        config_layout.addRow("手续费率:", self.commission_rate_spin)

        layout.addWidget(config_group)

        # 回测结果
        result_group = QGroupBox("回测结果")
        result_layout = QVBoxLayout(result_group)

        self.backtest_result_text = QTextEdit()
        self.backtest_result_text.setReadOnly(True)

        result_layout.addWidget(self.backtest_result_text)
        layout.addWidget(result_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.run_backtest_button = QPushButton("运行回测")
        self.run_backtest_button.clicked.connect(self._run_backtest)
        self.run_backtest_button.setEnabled(False)

        export_result_button = QPushButton("导出结果")
        export_result_button.clicked.connect(self._export_backtest_result)

        button_layout.addWidget(self.run_backtest_button)
        button_layout.addWidget(export_result_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "回测")

    def _create_optimization_tab(self):
        """创建优化选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 优化配置
        config_group = QGroupBox("优化配置")
        config_layout = QFormLayout(config_group)

        self.optimization_algorithm_combo = QComboBox()
        self.optimization_algorithm_combo.addItems([
            "grid_search", "random_search", "bayesian"
        ])

        self.target_metric_combo = QComboBox()
        self.target_metric_combo.addItems([
            "total_return", "sharpe_ratio", "max_drawdown", "win_rate"
        ])

        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(10, 1000)
        self.max_iterations_spin.setValue(100)

        config_layout.addRow("优化算法:", self.optimization_algorithm_combo)
        config_layout.addRow("目标指标:", self.target_metric_combo)
        config_layout.addRow("最大迭代:", self.max_iterations_spin)

        layout.addWidget(config_group)

        # 参数范围配置
        range_group = QGroupBox("参数范围")
        self.range_layout = QVBoxLayout(range_group)

        layout.addWidget(range_group)

        # 优化结果
        result_group = QGroupBox("优化结果")
        result_layout = QVBoxLayout(result_group)

        self.optimization_result_text = QTextEdit()
        self.optimization_result_text.setReadOnly(True)

        result_layout.addWidget(self.optimization_result_text)
        layout.addWidget(result_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.run_optimization_button = QPushButton("运行优化")
        self.run_optimization_button.clicked.connect(self._run_optimization)
        self.run_optimization_button.setEnabled(False)

        button_layout.addWidget(self.run_optimization_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "优化")

    def _create_monitoring_tab(self):
        """创建监控选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 实时状态
        status_group = QGroupBox("实时状态")
        status_layout = QFormLayout(status_group)

        self.runtime_status_label = QLabel("未运行")
        self.last_signal_label = QLabel("无")
        self.position_count_label = QLabel("0")
        self.total_pnl_label = QLabel("0.00")

        status_layout.addRow("运行状态:", self.runtime_status_label)
        status_layout.addRow("最后信号:", self.last_signal_label)
        status_layout.addRow("持仓数量:", self.position_count_label)
        status_layout.addRow("总盈亏:", self.total_pnl_label)

        layout.addWidget(status_group)

        # 信号历史
        signal_group = QGroupBox("信号历史")
        signal_layout = QVBoxLayout(signal_group)

        self.signal_table = QTableWidget()
        self.signal_table.setColumnCount(5)
        self.signal_table.setHorizontalHeaderLabels([
            "时间", "股票", "信号类型", "价格", "强度"
        ])

        signal_layout.addWidget(self.signal_table)
        layout.addWidget(signal_group)

        # 交易历史
        trade_group = QGroupBox("交易历史")
        trade_layout = QVBoxLayout(trade_group)

        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(6)
        self.trade_table.setHorizontalHeaderLabels([
            "时间", "股票", "操作", "数量", "价格", "状态"
        ])

        trade_layout.addWidget(self.trade_table)
        layout.addWidget(trade_group)

        self.tab_widget.addTab(tab, "监控")

    def _setup_timers(self):
        """设置定时器"""
        # 策略状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_strategy_status)
        self.status_timer.start(5000)  # 每5秒更新一次

        # 监控数据更新定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_monitoring_data)
        self.monitor_timer.start(2000)  # 每2秒更新一次

    def _load_strategies(self):
        """加载策略列表"""
        if not self.strategy_service:
            return

        try:
            configs = self.strategy_service.get_all_strategy_configs()

            self.strategy_table.setRowCount(len(configs))

            for row, config in enumerate(configs):
                # 策略ID
                self.strategy_table.setItem(row, 0, QTableWidgetItem(config.strategy_id))

                # 框架类型
                self.strategy_table.setItem(row, 1, QTableWidgetItem(config.plugin_type))

                # 状态
                status = "已配置"
                if self.trading_service:
                    trading_status = self.trading_service.get_strategy_status(config.strategy_id)
                    if trading_status:
                        status = trading_status['state']

                status_item = QTableWidgetItem(status)
                if status == "running":
                    status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                elif status == "error":
                    status_item.setBackground(QColor(255, 182, 193))  # 浅红色

                self.strategy_table.setItem(row, 2, status_item)

                # 性能（简化显示）
                performance = self.strategy_service.evaluate_strategy_performance(config.strategy_id)
                perf_text = "N/A"
                if performance:
                    avg_return = performance['performance_stats']['avg_total_return']
                    perf_text = f"{avg_return:.2%}"

                self.strategy_table.setItem(row, 3, QTableWidgetItem(perf_text))

                # 操作按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(2, 2, 2, 2)

                edit_button = QPushButton("编辑")
                edit_button.setMaximumSize(50, 25)
                edit_button.clicked.connect(lambda checked, sid=config.strategy_id: self._edit_strategy(sid))

                delete_button = QPushButton("删除")
                delete_button.setMaximumSize(50, 25)
                delete_button.clicked.connect(lambda checked, sid=config.strategy_id: self._delete_strategy_from_table(sid))

                button_layout.addWidget(edit_button)
                button_layout.addWidget(delete_button)

                self.strategy_table.setCellWidget(row, 4, button_widget)

        except Exception as e:
            logger.error(f"加载策略列表失败: {e}")
            QMessageBox.warning(self, "错误", f"加载策略列表失败: {e}")

    def _on_strategy_selected(self):
        """策略选择事件"""
        current_row = self.strategy_table.currentRow()
        if current_row >= 0:
            strategy_id_item = self.strategy_table.item(current_row, 0)
            if strategy_id_item:
                self.current_strategy_id = strategy_id_item.text()
                self._update_strategy_details()
                self.strategy_selected.emit(self.current_strategy_id)

    def _update_strategy_details(self):
        """更新策略详情"""
        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            config = self.strategy_service.get_strategy_config(self.current_strategy_id)
            if not config:
                return

            # 更新基本信息
            self.strategy_id_label.setText(config.strategy_id)
            self.plugin_type_label.setText(config.plugin_type)
            self.created_at_label.setText(config.created_at.strftime("%Y-%m-%d %H:%M:%S"))

            # 更新状态
            status = "已配置"
            if self.trading_service:
                trading_status = self.trading_service.get_strategy_status(config.strategy_id)
                if trading_status:
                    status = trading_status['state']

            self.status_label.setText(status)

            # 更新描述
            description = config.metadata.get('description', '无描述')
            self.description_text.setText(description)

            # 更新性能统计
            performance = self.strategy_service.evaluate_strategy_performance(config.strategy_id)
            if performance:
                stats = performance['performance_stats']
                self.total_return_label.setText(f"{stats['avg_total_return']:.2%}")
                self.sharpe_ratio_label.setText(f"{stats['avg_sharpe_ratio']:.2f}")
                self.max_drawdown_label.setText(f"{stats['avg_max_drawdown']:.2%}")
                self.win_rate_label.setText(f"{stats['avg_win_rate']:.2%}")
            else:
                self.total_return_label.setText("N/A")
                self.sharpe_ratio_label.setText("N/A")
                self.max_drawdown_label.setText("N/A")
                self.win_rate_label.setText("N/A")

            # 更新按钮状态
            self._update_button_states()

            # 更新参数配置
            self._update_config_widgets()

            # 更新优化参数范围
            self._update_optimization_ranges()

        except Exception as e:
            logger.error(f"更新策略详情失败: {e}")

    def _update_button_states(self):
        """更新按钮状态"""
        has_strategy = self.current_strategy_id is not None

        # 详情页按钮
        self.start_button.setEnabled(has_strategy)
        self.stop_button.setEnabled(has_strategy)
        self.delete_button.setEnabled(has_strategy)

        # 回测按钮
        self.run_backtest_button.setEnabled(has_strategy)

        # 优化按钮
        self.run_optimization_button.setEnabled(has_strategy)

    def _update_config_widgets(self):
        """更新参数配置控件"""
        # 清除现有控件
        for i in reversed(range(self.config_layout.count())):
            item = self.config_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.config_widgets.clear()

        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            config = self.strategy_service.get_strategy_config(self.current_strategy_id)
            if not config:
                return

            # 获取策略插件信息
            plugin = self.strategy_service.create_strategy_plugin(config.plugin_type)
            if not plugin:
                return

            strategy_info = plugin.get_strategy_info()

            # 为每个参数创建控件
            for param_def in strategy_info.parameters:
                widget = self._create_parameter_widget_for_config(param_def, config.parameters)
                if widget:
                    self.config_widgets[param_def.name] = widget
                    self.config_layout.addRow(f"{param_def.display_name}:", widget)

        except Exception as e:
            logger.error(f"更新参数配置控件失败: {e}")

    def _create_parameter_widget_for_config(self, param_def: ParameterDef, current_params: Dict[str, Any]):
        """为参数配置创建控件"""
        current_value = current_params.get(param_def.name, param_def.default_value)

        if param_def.type == int:
            widget = QSpinBox()
            if param_def.min_value is not None:
                widget.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                widget.setMaximum(param_def.max_value)
            if current_value is not None:
                widget.setValue(current_value)
            return widget

        elif param_def.type == float:
            widget = QDoubleSpinBox()
            widget.setDecimals(4)
            if param_def.min_value is not None:
                widget.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                widget.setMaximum(param_def.max_value)
            if current_value is not None:
                widget.setValue(current_value)
            return widget

        elif param_def.type == str:
            if hasattr(param_def, 'choices') and param_def.choices:
                widget = QComboBox()
                widget.addItems(param_def.choices)
                if current_value:
                    widget.setCurrentText(str(current_value))
                return widget
            else:
                widget = QLineEdit()
                if current_value:
                    widget.setText(str(current_value))
                return widget

        elif param_def.type == bool:
            widget = QCheckBox()
            if current_value is not None:
                widget.setChecked(current_value)
            return widget

        return None

    def _update_optimization_ranges(self):
        """更新优化参数范围"""
        # 清除现有控件
        for i in reversed(range(self.range_layout.count())):
            item = self.range_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            config = self.strategy_service.get_strategy_config(self.current_strategy_id)
            if not config:
                return

            plugin = self.strategy_service.create_strategy_plugin(config.plugin_type)
            if not plugin:
                return

            strategy_info = plugin.get_strategy_info()

            # 为数值参数创建范围控件
            for param_def in strategy_info.parameters:
                if param_def.type in [int, float]:
                    self._create_range_widget(param_def)

        except Exception as e:
            logger.error(f"更新优化参数范围失败: {e}")

    def _create_range_widget(self, param_def: ParameterDef):
        """创建参数范围控件"""
        group = QGroupBox(param_def.display_name)
        layout = QFormLayout(group)

        if param_def.type == int:
            min_spin = QSpinBox()
            max_spin = QSpinBox()
            step_spin = QSpinBox()

            if param_def.min_value is not None:
                min_spin.setMinimum(param_def.min_value)
                max_spin.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                min_spin.setMaximum(param_def.max_value)
                max_spin.setMaximum(param_def.max_value)

            # 设置默认值
            default_val = param_def.default_value or 1
            min_spin.setValue(max(1, default_val - 5))
            max_spin.setValue(default_val + 5)
            step_spin.setValue(1)

        else:  # float
            min_spin = QDoubleSpinBox()
            max_spin = QDoubleSpinBox()
            step_spin = QDoubleSpinBox()

            min_spin.setDecimals(4)
            max_spin.setDecimals(4)
            step_spin.setDecimals(4)

            if param_def.min_value is not None:
                min_spin.setMinimum(param_def.min_value)
                max_spin.setMinimum(param_def.min_value)
            if param_def.max_value is not None:
                min_spin.setMaximum(param_def.max_value)
                max_spin.setMaximum(param_def.max_value)

            # 设置默认值
            default_val = param_def.default_value or 0.1
            min_spin.setValue(default_val * 0.5)
            max_spin.setValue(default_val * 1.5)
            step_spin.setValue(default_val * 0.1)

        layout.addRow("最小值:", min_spin)
        layout.addRow("最大值:", max_spin)
        layout.addRow("步长:", step_spin)

        # 保存控件引用
        setattr(self, f"{param_def.name}_min_widget", min_spin)
        setattr(self, f"{param_def.name}_max_widget", max_spin)
        setattr(self, f"{param_def.name}_step_widget", step_spin)

        self.range_layout.addWidget(group)

    def _update_strategy_status(self):
        """更新策略状态"""
        if not self.current_strategy_id:
            return

        # 更新策略列表中的状态
        for row in range(self.strategy_table.rowCount()):
            strategy_id_item = self.strategy_table.item(row, 0)
            if strategy_id_item and strategy_id_item.text() == self.current_strategy_id:
                # 更新状态列
                status = "已配置"
                if self.trading_service:
                    trading_status = self.trading_service.get_strategy_status(self.current_strategy_id)
                    if trading_status:
                        status = trading_status['state']

                status_item = self.strategy_table.item(row, 2)
                if status_item:
                    status_item.setText(status)

                    # 更新颜色
                    if status == "running":
                        status_item.setBackground(QColor(144, 238, 144))
                    elif status == "error":
                        status_item.setBackground(QColor(255, 182, 193))
                    else:
                        status_item.setBackground(QColor(255, 255, 255))

                break

        # 更新详情页状态
        if self.current_strategy_id == self.strategy_id_label.text():
            status = "已配置"
            if self.trading_service:
                trading_status = self.trading_service.get_strategy_status(self.current_strategy_id)
                if trading_status:
                    status = trading_status['state']

            self.status_label.setText(status)
            self.runtime_status_label.setText(status)

    def _update_monitoring_data(self):
        """更新监控数据"""
        if not self.current_strategy_id or not self.trading_service:
            return

        try:
            # 更新交易统计
            stats = self.trading_service.get_performance_stats()

            # 更新持仓信息
            portfolio = self.trading_service.get_portfolio()
            self.position_count_label.setText(str(len(portfolio.positions)))
            self.total_pnl_label.setText(f"{portfolio.total_profit_loss:.2f}")

            # 更新交易历史
            trades = self.trading_service.get_trade_history(limit=50, strategy_id=self.current_strategy_id)

            self.trade_table.setRowCount(len(trades))
            for row, trade in enumerate(trades):
                self.trade_table.setItem(row, 0, QTableWidgetItem(trade.timestamp.strftime("%H:%M:%S")))
                self.trade_table.setItem(row, 1, QTableWidgetItem(trade.stock_code))
                self.trade_table.setItem(row, 2, QTableWidgetItem(trade.action))
                self.trade_table.setItem(row, 3, QTableWidgetItem(str(trade.quantity)))
                self.trade_table.setItem(row, 4, QTableWidgetItem(f"{trade.price:.2f}"))
                self.trade_table.setItem(row, 5, QTableWidgetItem(trade.status))

        except Exception as e:
            logger.error(f"更新监控数据失败: {e}")

    # 事件处理方法
    def _create_strategy(self):
        """创建策略"""
        wizard = StrategyCreationWizard(self, self.strategy_service)
        wizard.strategy_created.connect(self._on_strategy_created)
        wizard.exec_()

    def _on_strategy_created(self, strategy_data):
        """策略创建完成"""
        self._load_strategies()
        QMessageBox.information(self, "成功", f"策略 '{strategy_data['strategy_id']}' 创建成功")

    def _start_strategy(self):
        """启动策略"""
        if not self.current_strategy_id or not self.trading_service:
            return

        try:
            # 获取策略配置
            config = self.strategy_service.get_strategy_config(self.current_strategy_id)
            if not config:
                QMessageBox.warning(self, "错误", "策略配置不存在")
                return

            # 创建策略插件
            plugin = self.strategy_service.create_strategy_plugin(config.plugin_type)
            if not plugin:
                QMessageBox.warning(self, "错误", "无法创建策略插件")
                return

            # 创建策略上下文
            context = StrategyContext(
                symbol="000001",  # 简化处理
                timeframe=TimeFrame.DAY_1,
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                initial_capital=100000.0,
                commission_rate=0.0003
            )

            # 注册到交易服务
            success = self.trading_service.register_strategy(
                self.current_strategy_id,
                plugin,
                context,
                config.parameters
            )

            if success:
                # 启动策略
                success = self.trading_service.start_strategy(self.current_strategy_id)
                if success:
                    QMessageBox.information(self, "成功", f"策略 '{self.current_strategy_id}' 启动成功")
                    self.strategy_started.emit(self.current_strategy_id)
                else:
                    QMessageBox.warning(self, "错误", "策略启动失败")
            else:
                QMessageBox.warning(self, "错误", "策略注册失败")

        except Exception as e:
            logger.error(f"启动策略失败: {e}")
            QMessageBox.critical(self, "错误", f"启动策略失败: {e}")

    def _stop_strategy(self):
        """停止策略"""
        if not self.current_strategy_id or not self.trading_service:
            return

        try:
            success = self.trading_service.stop_strategy(self.current_strategy_id)
            if success:
                QMessageBox.information(self, "成功", f"策略 '{self.current_strategy_id}' 停止成功")
                self.strategy_stopped.emit(self.current_strategy_id)
            else:
                QMessageBox.warning(self, "错误", "策略停止失败")

        except Exception as e:
            logger.error(f"停止策略失败: {e}")
            QMessageBox.critical(self, "错误", f"停止策略失败: {e}")

    def _delete_strategy(self):
        """删除策略"""
        if not self.current_strategy_id:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除策略 '{self.current_strategy_id}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 先停止策略
                if self.trading_service:
                    self.trading_service.stop_strategy(self.current_strategy_id)
                    self.trading_service.unregister_strategy(self.current_strategy_id)

                # 删除配置
                success = self.strategy_service.delete_strategy_config(self.current_strategy_id)
                if success:
                    QMessageBox.information(self, "成功", f"策略 '{self.current_strategy_id}' 删除成功")
                    self.current_strategy_id = None
                    self._load_strategies()
                    self._update_strategy_details()
                else:
                    QMessageBox.warning(self, "错误", "策略删除失败")

            except Exception as e:
                logger.error(f"删除策略失败: {e}")
                QMessageBox.critical(self, "错误", f"删除策略失败: {e}")

    def _delete_strategy_from_table(self, strategy_id: str):
        """从表格删除策略"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除策略 '{strategy_id}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 先停止策略
                if self.trading_service:
                    self.trading_service.stop_strategy(strategy_id)
                    self.trading_service.unregister_strategy(strategy_id)

                # 删除配置
                success = self.strategy_service.delete_strategy_config(strategy_id)
                if success:
                    QMessageBox.information(self, "成功", f"策略 '{strategy_id}' 删除成功")
                    if self.current_strategy_id == strategy_id:
                        self.current_strategy_id = None
                        self._update_strategy_details()
                    self._load_strategies()
                else:
                    QMessageBox.warning(self, "错误", "策略删除失败")

            except Exception as e:
                logger.error(f"删除策略失败: {e}")
                QMessageBox.critical(self, "错误", f"删除策略失败: {e}")

    def _edit_strategy(self, strategy_id: str):
        """编辑策略"""
        # 选择策略并切换到配置选项卡
        for row in range(self.strategy_table.rowCount()):
            item = self.strategy_table.item(row, 0)
            if item and item.text() == strategy_id:
                self.strategy_table.selectRow(row)
                self.tab_widget.setCurrentIndex(1)  # 切换到参数配置选项卡
                break

    def _save_config(self):
        """保存配置"""
        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            # 收集参数
            parameters = {}
            for param_name, widget in self.config_widgets.items():
                if isinstance(widget, QSpinBox):
                    parameters[param_name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    parameters[param_name] = widget.value()
                elif isinstance(widget, QLineEdit):
                    parameters[param_name] = widget.text()
                elif isinstance(widget, QComboBox):
                    parameters[param_name] = widget.currentText()
                elif isinstance(widget, QCheckBox):
                    parameters[param_name] = widget.isChecked()

            # 更新配置
            success = self.strategy_service.update_strategy_config(
                self.current_strategy_id,
                parameters=parameters
            )

            if success:
                QMessageBox.information(self, "成功", "配置保存成功")
            else:
                QMessageBox.warning(self, "错误", "配置保存失败")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def _reset_config(self):
        """重置配置"""
        self._update_config_widgets()

    def _run_backtest(self):
        """运行回测"""
        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            # 创建市场数据（简化处理）
            import pandas as pd
            import numpy as np

            start_date = self.start_date_edit.date().toPyDate()
            end_date = self.end_date_edit.date().toPyDate()

            # 生成模拟数据
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            np.random.seed(42)
            prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)

            df = pd.DataFrame({
                'open': prices * (1 + np.random.randn(len(dates)) * 0.001),
                'high': prices * (1 + abs(np.random.randn(len(dates))) * 0.002),
                'low': prices * (1 - abs(np.random.randn(len(dates))) * 0.002),
                'close': prices,
                'volume': np.random.randint(1000, 10000, len(dates))
            }, index=dates)

            market_data = StandardMarketData.from_dataframe(df, symbol="000001")

            # 创建策略上下文
            context = StrategyContext(
                symbol="000001",
                timeframe=TimeFrame.DAY_1,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.min.time()),
                initial_capital=self.initial_capital_spin.value(),
                commission_rate=self.commission_rate_spin.value()
            )

            # 启动回测
            async def run_backtest_async():
                task_id = await self.strategy_service.run_backtest(
                    self.current_strategy_id, market_data, context
                )
                return task_id

            # 使用事件循环运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task_id = loop.run_until_complete(run_backtest_async())
            loop.close()

            if task_id:
                # 显示进度对话框
                progress_dialog = BacktestProgressDialog(self, self.strategy_service, task_id)
                if progress_dialog.exec_() == QDialog.Accepted:
                    # 回测完成，显示结果
                    result = self.strategy_service.get_backtest_result(task_id)
                    if result:
                        self._display_backtest_result(result)

        except Exception as e:
            logger.error(f"运行回测失败: {e}")
            QMessageBox.critical(self, "错误", f"运行回测失败: {e}")

    def _display_backtest_result(self, result):
        """显示回测结果"""
        result_text = f"""
回测结果:
总收益率: {result.total_return:.2%}
年化收益率: {result.annual_return:.2%}
夏普比率: {result.sharpe_ratio:.2f}
最大回撤: {result.max_drawdown:.2%}
胜率: {result.win_rate:.2%}
盈亏比: {result.profit_factor:.2f}
总交易次数: {result.total_trades}
盈利交易: {result.winning_trades}
亏损交易: {result.losing_trades}
平均盈利: {result.avg_win:.2f}
平均亏损: {result.avg_loss:.2f}
"""
        self.backtest_result_text.setText(result_text)

    def _export_backtest_result(self):
        """导出回测结果"""
        if not self.backtest_result_text.toPlainText():
            QMessageBox.warning(self, "警告", "没有回测结果可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出回测结果",
            f"backtest_result_{self.current_strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.backtest_result_text.toPlainText())
                QMessageBox.information(self, "成功", f"回测结果已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _run_optimization(self):
        """运行优化"""
        if not self.current_strategy_id or not self.strategy_service:
            return

        try:
            # 收集优化参数
            optimization_params = {
                'algorithm': self.optimization_algorithm_combo.currentText(),
                'target_metric': self.target_metric_combo.currentText(),
                'max_iterations': self.max_iterations_spin.value(),
                'parameter_ranges': {}
            }

            # 收集参数范围
            config = self.strategy_service.get_strategy_config(self.current_strategy_id)
            if config:
                plugin = self.strategy_service.create_strategy_plugin(config.plugin_type)
                if plugin:
                    strategy_info = plugin.get_strategy_info()

                    for param_def in strategy_info.parameters:
                        if param_def.type in [int, float]:
                            min_widget = getattr(self, f"{param_def.name}_min_widget", None)
                            max_widget = getattr(self, f"{param_def.name}_max_widget", None)
                            step_widget = getattr(self, f"{param_def.name}_step_widget", None)

                            if min_widget and max_widget and step_widget:
                                optimization_params['parameter_ranges'][param_def.name] = {
                                    'min': min_widget.value(),
                                    'max': max_widget.value(),
                                    'step': step_widget.value()
                                }

            # 创建市场数据（简化处理）
            import pandas as pd
            import numpy as np

            dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
            np.random.seed(42)
            prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)

            df = pd.DataFrame({
                'open': prices * (1 + np.random.randn(len(dates)) * 0.001),
                'high': prices * (1 + abs(np.random.randn(len(dates))) * 0.002),
                'low': prices * (1 - abs(np.random.randn(len(dates))) * 0.002),
                'close': prices,
                'volume': np.random.randint(1000, 10000, len(dates))
            }, index=dates)

            market_data = StandardMarketData.from_dataframe(df, symbol="000001")

            # 创建策略上下文
            context = StrategyContext(
                symbol="000001",
                timeframe=TimeFrame.DAY_1,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                initial_capital=100000.0,
                commission_rate=0.0003
            )

            # 启动优化
            async def run_optimization_async():
                task_id = await self.strategy_service.run_optimization(
                    self.current_strategy_id, optimization_params, market_data, context
                )
                return task_id

            # 使用事件循环运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task_id = loop.run_until_complete(run_optimization_async())
            loop.close()

            if task_id:
                QMessageBox.information(self, "成功", f"优化任务已启动，任务ID: {task_id}")

                # 可以添加优化进度监控

        except Exception as e:
            logger.error(f"运行优化失败: {e}")
            QMessageBox.critical(self, "错误", f"运行优化失败: {e}")

    def _import_strategy(self):
        """导入策略"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入策略", "", "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    strategy_data = json.load(f)

                # 验证策略数据格式
                required_fields = ['strategy_id', 'plugin_type', 'parameters']
                if not all(field in strategy_data for field in required_fields):
                    QMessageBox.warning(self, "错误", "策略文件格式不正确")
                    return

                # 创建策略配置
                success = self.strategy_service.create_strategy_config(
                    strategy_id=strategy_data['strategy_id'],
                    plugin_type=strategy_data['plugin_type'],
                    parameters=strategy_data['parameters'],
                    metadata=strategy_data.get('metadata', {})
                )

                if success:
                    QMessageBox.information(self, "成功", f"策略 '{strategy_data['strategy_id']}' 导入成功")
                    self._load_strategies()
                else:
                    QMessageBox.warning(self, "错误", "策略导入失败")

            except Exception as e:
                logger.error(f"导入策略失败: {e}")
                QMessageBox.critical(self, "错误", f"导入策略失败: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        # 停止定时器
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        if hasattr(self, 'monitor_timer'):
            self.monitor_timer.stop()

        event.accept()
