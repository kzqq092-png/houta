#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版数据导入UI组件

集成了所有新开发的智能化功能：
- AI预测和参数优化
- 实时性能监控和异常检测
- 多级缓存系统
- 分布式执行
- 自动调优
- 数据质量监控

作者: FactorWeave-Quant团队
版本: 2.0 (集成智能化功能)
"""

import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QApplication, QHeaderView, QComboBox, QLineEdit,
    QDateEdit, QSpinBox, QCheckBox, QListWidget, QListWidgetItem,
    QMessageBox, QMenu, QToolBar, QAction, QStatusBar,
    QDialog, QDialogButtonBox, QFormLayout, QAbstractItemView,
    QSlider, QDoubleSpinBox, QLCDNumber
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QDate, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QIcon, QPixmap, QPainter,
    QLinearGradient, QPen, QBrush
)

# 导入核心组件
try:
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    from core.importdata.import_config_manager import ImportConfigManager, ImportTaskConfig, DataFrequency, ImportMode
    from core.plugin_types import AssetType, DataType, PluginType
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = None
    print(f"导入核心组件失败: {e}")
    CORE_AVAILABLE = False

logger = logger.bind(module=__name__) if logger else None


class EnhancedDataImportWidget(QWidget):
    """增强版数据导入主界面"""

    # 信号定义
    task_started = pyqtSignal(str)  # 任务开始
    task_completed = pyqtSignal(str, object)  # 任务完成
    task_failed = pyqtSignal(str, str)  # 任务失败

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化核心组件
        self.import_engine = None
        self.config_manager = None

        if CORE_AVAILABLE:
            self.config_manager = ImportConfigManager()
            self.import_engine = DataImportExecutionEngine(
                config_manager=self.config_manager,
                max_workers=4,
                enable_ai_optimization=True
            )

        self.setup_ui()
        self.setup_connections()
        self.setup_timers()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题区域
        title_frame = self.create_title_frame()
        layout.addWidget(title_frame)

        # 主要内容区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：配置和控制面板
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：监控和状态面板
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)

        layout.addWidget(main_splitter)

        # 底部状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("增强版数据导入系统就绪")
        layout.addWidget(self.status_bar)

    def create_title_frame(self) -> QFrame:
        """创建标题框架"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90e2, stop:1 #357abd);
                border-radius: 10px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(frame)

        # 标题
        title_label = QLabel("🚀 DuckDB专业数据导入系统 (智能化版本)")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)

        layout.addStretch()

        # 版本信息
        version_label = QLabel("v2.0 - AI增强版")
        version_label.setFont(QFont("Arial", 10))
        layout.addWidget(version_label)

        return frame

    def create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 任务配置区域
        config_group = self.create_task_config_group()
        layout.addWidget(config_group)

        # 智能化功能控制区域
        ai_group = self.create_ai_features_group()
        layout.addWidget(ai_group)

        # 执行控制区域
        control_group = self.create_control_group()
        layout.addWidget(control_group)

        layout.addStretch()
        return widget

    def create_task_config_group(self) -> QGroupBox:
        """创建任务配置组"""
        group = QGroupBox("📋 任务配置")
        group.setFont(QFont("Arial", 10, QFont.Bold))
        layout = QFormLayout(group)

        # 任务名称
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setPlaceholderText("输入任务名称...")
        layout.addRow("任务名称:", self.task_name_edit)

        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["tongdaxin", "eastmoney", "sina", "akshare"])
        layout.addRow("数据源:", self.data_source_combo)

        # 资产类型
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(["股票", "基金", "期货", "债券"])
        layout.addRow("资产类型:", self.asset_type_combo)

        # 频率选择
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["日线", "周线", "月线", "5分钟", "15分钟", "30分钟", "60分钟"])
        layout.addRow("数据频率:", self.frequency_combo)

        # 股票代码输入
        self.symbols_edit = QTextEdit()
        self.symbols_edit.setMaximumHeight(80)
        self.symbols_edit.setPlaceholderText("输入股票代码，每行一个\n例如：000001\n000002")
        layout.addRow("股票代码:", self.symbols_edit)

        return group

    def create_ai_features_group(self) -> QGroupBox:
        """创建AI功能控制组"""
        group = QGroupBox("🤖 智能化功能")
        group.setFont(QFont("Arial", 10, QFont.Bold))
        layout = QVBoxLayout(group)

        # AI优化开关
        self.ai_optimization_cb = QCheckBox("启用AI参数优化")
        self.ai_optimization_cb.setChecked(True)
        self.ai_optimization_cb.setToolTip("使用机器学习算法优化执行参数")
        layout.addWidget(self.ai_optimization_cb)

        # 自动调优开关
        self.auto_tuning_cb = QCheckBox("启用AutoTuner自动调优")
        self.auto_tuning_cb.setChecked(True)
        self.auto_tuning_cb.setToolTip("使用AutoTuner进行参数自动调优")
        layout.addWidget(self.auto_tuning_cb)

        # 分布式执行开关
        self.distributed_cb = QCheckBox("启用分布式执行")
        self.distributed_cb.setChecked(True)
        self.distributed_cb.setToolTip("大任务自动分布式执行")
        layout.addWidget(self.distributed_cb)

        # 智能缓存开关
        self.caching_cb = QCheckBox("启用智能缓存")
        self.caching_cb.setChecked(True)
        self.caching_cb.setToolTip("启用多级缓存加速")
        layout.addWidget(self.caching_cb)

        # 数据质量监控开关
        self.quality_monitoring_cb = QCheckBox("启用数据质量监控")
        self.quality_monitoring_cb.setChecked(True)
        self.quality_monitoring_cb.setToolTip("实时监控数据质量")
        layout.addWidget(self.quality_monitoring_cb)

        return group

    def create_control_group(self) -> QGroupBox:
        """创建执行控制组"""
        group = QGroupBox("🎮 执行控制")
        group.setFont(QFont("Arial", 10, QFont.Bold))
        layout = QVBoxLayout(group)

        # 参数调整区域
        params_layout = QFormLayout()

        # 批次大小
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(100, 10000)
        self.batch_size_spin.setValue(1000)
        self.batch_size_spin.setSuffix(" 条")
        params_layout.addRow("批次大小:", self.batch_size_spin)

        # 工作线程数
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(4)
        self.workers_spin.setSuffix(" 个")
        params_layout.addRow("工作线程:", self.workers_spin)

        layout.addLayout(params_layout)

        # 控制按钮
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("🚀 开始导入")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
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

        layout.addLayout(button_layout)

        return group

    def create_right_panel(self) -> QWidget:
        """创建右侧监控面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建选项卡
        self.monitor_tabs = QTabWidget()

        # 任务管理选项卡（新增 - 放在第一位）
        task_management_tab = self.create_task_management_tab()
        self.monitor_tabs.addTab(task_management_tab, "📋 任务管理")

        # 实时监控选项卡
        monitor_tab = self.create_monitor_tab()
        self.monitor_tabs.addTab(monitor_tab, "📊 实时监控")

        # AI状态选项卡
        ai_tab = self.create_ai_status_tab()
        self.monitor_tabs.addTab(ai_tab, "🤖 AI状态")

        # 缓存状态选项卡
        cache_tab = self.create_cache_status_tab()
        self.monitor_tabs.addTab(cache_tab, "💾 缓存状态")

        # 分布式状态选项卡
        distributed_tab = self.create_distributed_status_tab()
        self.monitor_tabs.addTab(distributed_tab, "🌐 分布式状态")

        # 数据质量选项卡
        quality_tab = self.create_quality_status_tab()
        self.monitor_tabs.addTab(quality_tab, "✅ 数据质量")

        # 增强性能选项卡
        enhanced_performance_tab = self.create_enhanced_performance_tab()
        self.monitor_tabs.addTab(enhanced_performance_tab, "🚀 增强性能")

        layout.addWidget(self.monitor_tabs)

        return widget

    def create_monitor_tab(self) -> QWidget:
        """创建实时监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 进度显示
        progress_group = QGroupBox("执行进度")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("等待开始...")
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # 性能指标
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QGridLayout(metrics_group)

        # 执行时间
        metrics_layout.addWidget(QLabel("执行时间:"), 0, 0)
        self.execution_time_label = QLabel("0秒")
        metrics_layout.addWidget(self.execution_time_label, 0, 1)

        # 处理速度
        metrics_layout.addWidget(QLabel("处理速度:"), 1, 0)
        self.speed_label = QLabel("0条/秒")
        metrics_layout.addWidget(self.speed_label, 1, 1)

        # 成功率
        metrics_layout.addWidget(QLabel("成功率:"), 2, 0)
        self.success_rate_label = QLabel("0%")
        metrics_layout.addWidget(self.success_rate_label, 2, 1)

        layout.addWidget(metrics_group)

        # 日志显示
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return widget

    def create_ai_status_tab(self) -> QWidget:
        """创建AI状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # AI优化统计
        ai_group = QGroupBox("AI优化统计")
        ai_layout = QGridLayout(ai_group)

        ai_layout.addWidget(QLabel("预测次数:"), 0, 0)
        self.predictions_count_label = QLabel("0")
        ai_layout.addWidget(self.predictions_count_label, 0, 1)

        ai_layout.addWidget(QLabel("节省时间:"), 1, 0)
        self.time_saved_label = QLabel("0秒")
        ai_layout.addWidget(self.time_saved_label, 1, 1)

        ai_layout.addWidget(QLabel("准确率:"), 2, 0)
        self.accuracy_label = QLabel("0%")
        ai_layout.addWidget(self.accuracy_label, 2, 1)

        layout.addWidget(ai_group)

        # AutoTuner状态
        tuner_group = QGroupBox("AutoTuner状态")
        tuner_layout = QGridLayout(tuner_group)

        tuner_layout.addWidget(QLabel("活跃任务:"), 0, 0)
        self.active_tuning_label = QLabel("0")
        tuner_layout.addWidget(self.active_tuning_label, 0, 1)

        tuner_layout.addWidget(QLabel("完成任务:"), 1, 0)
        self.completed_tuning_label = QLabel("0")
        tuner_layout.addWidget(self.completed_tuning_label, 1, 1)

        tuner_layout.addWidget(QLabel("总体改进:"), 2, 0)
        self.total_improvement_label = QLabel("0%")
        tuner_layout.addWidget(self.total_improvement_label, 2, 1)

        layout.addWidget(tuner_group)

        layout.addStretch()
        return widget

    def create_cache_status_tab(self) -> QWidget:
        """创建缓存状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 缓存统计
        cache_group = QGroupBox("缓存统计")
        cache_layout = QGridLayout(cache_group)

        cache_layout.addWidget(QLabel("命中率:"), 0, 0)
        self.cache_hit_rate_label = QLabel("0%")
        cache_layout.addWidget(self.cache_hit_rate_label, 0, 1)

        cache_layout.addWidget(QLabel("缓存大小:"), 1, 0)
        self.cache_size_label = QLabel("0MB")
        cache_layout.addWidget(self.cache_size_label, 1, 1)

        cache_layout.addWidget(QLabel("缓存项数:"), 2, 0)
        self.cache_items_label = QLabel("0")
        cache_layout.addWidget(self.cache_items_label, 2, 1)

        layout.addWidget(cache_group)

        layout.addStretch()
        return widget

    def create_distributed_status_tab(self) -> QWidget:
        """创建分布式状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 节点状态
        nodes_group = QGroupBox("节点状态")
        nodes_layout = QGridLayout(nodes_group)

        nodes_layout.addWidget(QLabel("发现节点:"), 0, 0)
        self.discovered_nodes_label = QLabel("0")
        nodes_layout.addWidget(self.discovered_nodes_label, 0, 1)

        nodes_layout.addWidget(QLabel("可用节点:"), 1, 0)
        self.available_nodes_label = QLabel("0")
        nodes_layout.addWidget(self.available_nodes_label, 1, 1)

        nodes_layout.addWidget(QLabel("分布式任务:"), 2, 0)
        self.distributed_tasks_label = QLabel("0")
        nodes_layout.addWidget(self.distributed_tasks_label, 2, 1)

        layout.addWidget(nodes_group)

        # 节点列表
        nodes_list_group = QGroupBox("节点列表")
        nodes_list_layout = QVBoxLayout(nodes_list_group)

        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(4)
        self.nodes_table.setHorizontalHeaderLabels(["节点ID", "地址", "任务数", "状态"])
        self.nodes_table.horizontalHeader().setStretchLastSection(True)
        nodes_list_layout.addWidget(self.nodes_table)

        layout.addWidget(nodes_list_group)

        return widget

    def create_quality_status_tab(self) -> QWidget:
        """创建数据质量状态选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 质量指标
        quality_group = QGroupBox("质量指标")
        quality_layout = QGridLayout(quality_group)

        quality_layout.addWidget(QLabel("整体评分:"), 0, 0)
        self.overall_quality_label = QLabel("0.0")
        quality_layout.addWidget(self.overall_quality_label, 0, 1)

        quality_layout.addWidget(QLabel("完整性:"), 1, 0)
        self.completeness_label = QLabel("0%")
        quality_layout.addWidget(self.completeness_label, 1, 1)

        quality_layout.addWidget(QLabel("准确性:"), 2, 0)
        self.accuracy_quality_label = QLabel("0%")
        quality_layout.addWidget(self.accuracy_quality_label, 2, 1)

        quality_layout.addWidget(QLabel("一致性:"), 3, 0)
        self.consistency_label = QLabel("0%")
        quality_layout.addWidget(self.consistency_label, 3, 1)

        layout.addWidget(quality_group)

        # 质量问题
        issues_group = QGroupBox("质量问题")
        issues_layout = QVBoxLayout(issues_group)

        self.quality_issues_text = QTextEdit()
        self.quality_issues_text.setMaximumHeight(150)
        self.quality_issues_text.setReadOnly(True)
        issues_layout.addWidget(self.quality_issues_text)

        layout.addWidget(issues_group)

        return widget

    def create_enhanced_performance_tab(self) -> QWidget:
        """创建增强性能监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 性能摘要区域
        summary_group = QGroupBox("📈 性能摘要")
        summary_layout = QGridLayout(summary_group)

        # 性能指标显示
        self.enhanced_performance_summary = QTextEdit()
        self.enhanced_performance_summary.setMaximumHeight(120)
        self.enhanced_performance_summary.setReadOnly(True)
        summary_layout.addWidget(QLabel("性能摘要:"), 0, 0)
        summary_layout.addWidget(self.enhanced_performance_summary, 0, 1, 1, 2)

        layout.addWidget(summary_group)

        # 异常检测区域
        anomaly_group = QGroupBox("⚠️ 异常检测")
        anomaly_layout = QVBoxLayout(anomaly_group)

        # 异常列表
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(5)
        self.anomaly_table.setHorizontalHeaderLabels([
            "时间", "类型", "严重程度", "描述", "操作"
        ])
        self.anomaly_table.horizontalHeader().setStretchLastSection(True)
        self.anomaly_table.setMaximumHeight(150)
        anomaly_layout.addWidget(self.anomaly_table)

        # 异常操作按钮
        anomaly_btn_layout = QHBoxLayout()
        self.refresh_anomalies_btn = QPushButton("🔄 刷新异常")
        self.resolve_anomaly_btn = QPushButton("✅ 解决选中异常")
        self.resolve_anomaly_btn.setEnabled(False)
        anomaly_btn_layout.addWidget(self.refresh_anomalies_btn)
        anomaly_btn_layout.addWidget(self.resolve_anomaly_btn)
        anomaly_btn_layout.addStretch()
        anomaly_layout.addLayout(anomaly_btn_layout)

        layout.addWidget(anomaly_group)

        # 性能趋势区域
        trends_group = QGroupBox("📊 性能趋势")
        trends_layout = QVBoxLayout(trends_group)

        self.performance_trends = QTextEdit()
        self.performance_trends.setMaximumHeight(100)
        self.performance_trends.setReadOnly(True)
        trends_layout.addWidget(self.performance_trends)

        layout.addWidget(trends_group)

        # 优化建议区域
        suggestions_group = QGroupBox("💡 优化建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        # 建议列表
        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(4)
        self.suggestions_table.setHorizontalHeaderLabels([
            "优先级", "类型", "建议", "操作"
        ])
        self.suggestions_table.horizontalHeader().setStretchLastSection(True)
        self.suggestions_table.setMaximumHeight(120)
        suggestions_layout.addWidget(self.suggestions_table)

        # 建议操作按钮
        suggestions_btn_layout = QHBoxLayout()
        self.refresh_suggestions_btn = QPushButton("🔄 刷新建议")
        self.apply_suggestion_btn = QPushButton("✅ 应用选中建议")
        self.apply_suggestion_btn.setEnabled(False)
        suggestions_btn_layout.addWidget(self.refresh_suggestions_btn)
        suggestions_btn_layout.addWidget(self.apply_suggestion_btn)
        suggestions_btn_layout.addStretch()
        suggestions_layout.addLayout(suggestions_btn_layout)

        layout.addWidget(suggestions_group)

        # 指标历史区域
        history_group = QGroupBox("📈 指标历史")
        history_layout = QVBoxLayout(history_group)

        # 指标选择
        metric_select_layout = QHBoxLayout()
        metric_select_layout.addWidget(QLabel("选择指标:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "task_execution_time", "memory_usage", "cpu_usage",
            "disk_io", "network_io", "cache_hit_rate"
        ])
        metric_select_layout.addWidget(self.metric_combo)
        self.load_metric_history_btn = QPushButton("📊 加载历史")
        metric_select_layout.addWidget(self.load_metric_history_btn)
        metric_select_layout.addStretch()
        history_layout.addLayout(metric_select_layout)

        # 历史数据显示
        self.metric_history = QTextEdit()
        self.metric_history.setMaximumHeight(100)
        self.metric_history.setReadOnly(True)
        history_layout.addWidget(self.metric_history)

        layout.addWidget(history_group)

        # 连接信号
        self.refresh_anomalies_btn.clicked.connect(self.refresh_performance_anomalies)
        self.resolve_anomaly_btn.clicked.connect(self.resolve_selected_anomaly)
        self.refresh_suggestions_btn.clicked.connect(self.refresh_optimization_suggestions)
        self.apply_suggestion_btn.clicked.connect(self.apply_selected_suggestion)
        self.load_metric_history_btn.clicked.connect(self.load_selected_metric_history)

        # 表格选择变化
        self.anomaly_table.itemSelectionChanged.connect(
            lambda: self.resolve_anomaly_btn.setEnabled(
                len(self.anomaly_table.selectedItems()) > 0
            )
        )
        self.suggestions_table.itemSelectionChanged.connect(
            lambda: self.apply_suggestion_btn.setEnabled(
                len(self.suggestions_table.selectedItems()) > 0
            )
        )

        return widget

    def setup_connections(self):
        """设置信号连接"""
        if not CORE_AVAILABLE:
            return

        # 按钮连接
        self.start_btn.clicked.connect(self.start_import)
        self.stop_btn.clicked.connect(self.stop_import)

        # 引擎信号连接
        if self.import_engine:
            self.import_engine.task_started.connect(self.on_task_started)
            self.import_engine.task_progress.connect(self.on_task_progress)
            self.import_engine.task_completed.connect(self.on_task_completed)
            self.import_engine.task_failed.connect(self.on_task_failed)

    def setup_timers(self):
        """设置定时器"""
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # 每2秒更新一次

        # 任务列表刷新定时器
        self.task_refresh_timer = QTimer()
        self.task_refresh_timer.timeout.connect(self.refresh_task_list)
        self.task_refresh_timer.start(5000)  # 每5秒刷新一次任务列表

    def start_import(self):
        """开始导入"""
        if not CORE_AVAILABLE or not self.import_engine:
            QMessageBox.warning(self, "错误", "核心组件不可用")
            return

        try:
            # 获取配置
            task_name = self.task_name_edit.text() or f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            symbols_text = self.symbols_edit.toPlainText().strip()

            if not symbols_text:
                QMessageBox.warning(self, "警告", "请输入股票代码")
                return

            symbols = [s.strip() for s in symbols_text.split('\n') if s.strip()]

            # 创建任务配置
            # 频率映射
            freq_map = {
                "日线": DataFrequency.DAILY,
                "周线": DataFrequency.WEEKLY,
                "月线": DataFrequency.MONTHLY,
                "5分钟": DataFrequency.MINUTE_5,
                "15分钟": DataFrequency.MINUTE_15,
                "30分钟": DataFrequency.MINUTE_30,
                "60分钟": DataFrequency.HOUR_1
            }

            task_config = ImportTaskConfig(
                task_id=f"task_{int(datetime.now().timestamp())}",
                name=task_name,
                symbols=symbols,
                data_source=self.data_source_combo.currentText(),
                asset_type=self.asset_type_combo.currentText(),
                data_type="K线数据",  # 默认数据类型
                frequency=freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY),
                mode=ImportMode.MANUAL,  # 默认手动模式
                batch_size=self.batch_size_spin.value(),
                max_workers=self.workers_spin.value()
            )

            # 更新引擎配置
            self.import_engine.enable_ai_optimization = self.ai_optimization_cb.isChecked()
            self.import_engine.enable_auto_tuning = self.auto_tuning_cb.isChecked()
            self.import_engine.enable_distributed_execution = self.distributed_cb.isChecked()
            self.import_engine.enable_intelligent_caching = self.caching_cb.isChecked()
            self.import_engine.enable_data_quality_monitoring = self.quality_monitoring_cb.isChecked()

            # 保存配置并启动任务
            self.config_manager.add_import_task(task_config)

            if self.import_engine.start_task(task_config.task_id):
                self.log_message(f"任务启动成功: {task_name}")
            else:
                self.log_message(f"任务启动失败: {task_name}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动任务失败: {str(e)}")
            self.log_message(f"启动任务失败: {str(e)}")

    def stop_import(self):
        """停止导入"""
        if self.import_engine:
            # 这里可以添加停止逻辑
            self.log_message("停止导入请求已发送")

    def on_task_started(self, task_id: str):
        """任务开始回调"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("任务已开始...")
        self.log_message(f"任务开始: {task_id}")

    def on_task_progress(self, task_id: str, progress: float, message: str):
        """任务进度回调"""
        self.progress_bar.setValue(int(progress * 100))
        self.progress_label.setText(message)
        self.log_message(f"进度更新: {progress:.1%} - {message}")

    def on_task_completed(self, task_id: str, result):
        """任务完成回调"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText("任务完成!")
        self.log_message(f"任务完成: {task_id}")

    def on_task_failed(self, task_id: str, error_message: str):
        """任务失败回调"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("任务失败!")
        self.log_message(f"任务失败: {task_id} - {error_message}")

    def update_status(self):
        """更新状态显示"""
        if not CORE_AVAILABLE or not self.import_engine:
            return

        try:
            # 更新AI状态
            ai_stats = self.import_engine.get_ai_optimization_stats()
            self.predictions_count_label.setText(str(ai_stats.get('predictions_made', 0)))
            self.time_saved_label.setText(f"{ai_stats.get('execution_time_saved', 0):.1f}秒")
            self.accuracy_label.setText(f"{ai_stats.get('accuracy_improved', 0):.1%}")

            # 更新AutoTuner状态
            tuner_stats = self.import_engine.get_auto_tuning_status()
            self.active_tuning_label.setText(str(tuner_stats.get('active_tasks', 0)))
            self.completed_tuning_label.setText(str(tuner_stats.get('completed_tasks', 0)))
            self.total_improvement_label.setText(f"{tuner_stats.get('total_improvement', 0):.1%}")

            # 更新缓存状态
            cache_stats = self.import_engine.get_cache_statistics()
            # 这里可以添加缓存统计的显示逻辑

            # 更新分布式状态
            distributed_stats = self.import_engine.get_distributed_status()
            self.discovered_nodes_label.setText(str(distributed_stats.get('discovered_nodes', 0)))
            self.available_nodes_label.setText(str(distributed_stats.get('available_nodes', 0)))

            # 更新节点表格
            self.update_nodes_table(distributed_stats.get('nodes_detail', []))

            # 更新数据质量状态
            quality_stats = self.import_engine.get_data_quality_statistics()
            # 这里可以添加数据质量统计的显示逻辑

            # 更新增强性能状态
            self.update_enhanced_performance_status()

        except Exception as e:
            logger.error(f"更新状态失败: {e}") if logger else None

    def update_nodes_table(self, nodes_data: List[Dict]):
        """更新节点表格"""
        self.nodes_table.setRowCount(len(nodes_data))

        for row, node in enumerate(nodes_data):
            self.nodes_table.setItem(row, 0, QTableWidgetItem(node.get('node_id', '')))
            self.nodes_table.setItem(row, 1, QTableWidgetItem(f"{node.get('address', '')}:{node.get('port', '')}"))
            self.nodes_table.setItem(row, 2, QTableWidgetItem(str(node.get('task_count', 0))))

            status = "可用" if node.get('available', False) else "不可用"
            self.nodes_table.setItem(row, 3, QTableWidgetItem(status))

    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def refresh_performance_anomalies(self):
        """刷新性能异常"""
        try:
            if not self.import_engine:
                return

            anomalies = self.import_engine.get_performance_anomalies(24)  # 最近24小时

            self.anomaly_table.setRowCount(len(anomalies))
            for i, anomaly in enumerate(anomalies):
                self.anomaly_table.setItem(i, 0, QTableWidgetItem(
                    anomaly.get('timestamp', 'N/A')
                ))
                self.anomaly_table.setItem(i, 1, QTableWidgetItem(
                    anomaly.get('type', 'Unknown')
                ))
                self.anomaly_table.setItem(i, 2, QTableWidgetItem(
                    anomaly.get('severity', 'Medium')
                ))
                self.anomaly_table.setItem(i, 3, QTableWidgetItem(
                    anomaly.get('description', 'No description')
                ))

                # 存储异常ID用于解决
                item = QTableWidgetItem(anomaly.get('id', ''))
                item.setData(Qt.UserRole, anomaly.get('id'))
                self.anomaly_table.setItem(i, 4, item)

            logger.info(f"刷新了 {len(anomalies)} 个性能异常") if logger else None

        except Exception as e:
            logger.error(f"刷新性能异常失败: {e}") if logger else None
            QMessageBox.warning(self, "错误", f"刷新性能异常失败: {e}")

    def resolve_selected_anomaly(self):
        """解决选中的异常"""
        try:
            current_row = self.anomaly_table.currentRow()
            if current_row < 0:
                return

            anomaly_id_item = self.anomaly_table.item(current_row, 4)
            if not anomaly_id_item:
                return

            anomaly_id = anomaly_id_item.data(Qt.UserRole)
            if not anomaly_id:
                return

            if self.import_engine and self.import_engine.resolve_performance_anomaly(anomaly_id):
                QMessageBox.information(self, "成功", "异常已标记为已解决")
                self.refresh_performance_anomalies()  # 刷新列表
            else:
                QMessageBox.warning(self, "失败", "解决异常失败")

        except Exception as e:
            logger.error(f"解决异常失败: {e}") if logger else None
            QMessageBox.warning(self, "错误", f"解决异常失败: {e}")

    def refresh_optimization_suggestions(self):
        """刷新优化建议"""
        try:
            if not self.import_engine:
                return

            suggestions = self.import_engine.get_performance_optimization_suggestions('high')

            self.suggestions_table.setRowCount(len(suggestions))
            for i, suggestion in enumerate(suggestions):
                self.suggestions_table.setItem(i, 0, QTableWidgetItem(
                    suggestion.get('priority', 'Medium')
                ))
                self.suggestions_table.setItem(i, 1, QTableWidgetItem(
                    suggestion.get('type', 'General')
                ))
                self.suggestions_table.setItem(i, 2, QTableWidgetItem(
                    suggestion.get('description', 'No description')
                ))

                # 存储建议ID用于应用
                item = QTableWidgetItem(suggestion.get('id', ''))
                item.setData(Qt.UserRole, suggestion.get('id'))
                self.suggestions_table.setItem(i, 3, item)

            logger.info(f"刷新了 {len(suggestions)} 个优化建议") if logger else None

        except Exception as e:
            logger.error(f"刷新优化建议失败: {e}") if logger else None
            QMessageBox.warning(self, "错误", f"刷新优化建议失败: {e}")

    def apply_selected_suggestion(self):
        """应用选中的建议"""
        try:
            current_row = self.suggestions_table.currentRow()
            if current_row < 0:
                return

            suggestion_id_item = self.suggestions_table.item(current_row, 3)
            if not suggestion_id_item:
                return

            suggestion_id = suggestion_id_item.data(Qt.UserRole)
            if not suggestion_id:
                return

            if self.import_engine and self.import_engine.apply_performance_optimization(suggestion_id):
                QMessageBox.information(self, "成功", "优化建议已应用")
                self.refresh_optimization_suggestions()  # 刷新列表
            else:
                QMessageBox.warning(self, "失败", "应用优化建议失败")

        except Exception as e:
            logger.error(f"应用建议失败: {e}") if logger else None
            QMessageBox.warning(self, "错误", f"应用建议失败: {e}")

    def load_selected_metric_history(self):
        """加载选中指标的历史数据"""
        try:
            if not self.import_engine:
                return

            metric_name = self.metric_combo.currentText()
            if not metric_name:
                return

            history = self.import_engine.get_metric_performance_history(metric_name, 24)

            if history:
                history_text = f"指标: {metric_name}\n"
                history_text += f"数据点数量: {len(history)}\n\n"

                for i, point in enumerate(history[-10:]):  # 显示最近10个数据点
                    timestamp = point.get('timestamp', 'N/A')
                    value = point.get('value', 'N/A')
                    history_text += f"{timestamp}: {value}\n"

                if len(history) > 10:
                    history_text += f"\n... 还有 {len(history) - 10} 个数据点"

                self.metric_history.setText(history_text)
            else:
                self.metric_history.setText(f"指标 {metric_name} 暂无历史数据")

        except Exception as e:
            logger.error(f"加载指标历史失败: {e}") if logger else None
            self.metric_history.setText(f"加载失败: {e}")

    def update_enhanced_performance_status(self):
        """更新增强性能状态"""
        try:
            if not self.import_engine:
                return

            # 更新性能摘要
            summary = self.import_engine.get_enhanced_performance_summary()
            if summary.get('enhanced_performance_bridge_enabled'):
                summary_text = "增强性能桥接系统: 已启用\n"
                summary_text += f"监控状态: {summary.get('monitoring_status', 'Unknown')}\n"
                summary_text += f"数据收集间隔: {summary.get('collection_interval', 'N/A')}秒\n"
                summary_text += f"活跃监控器数量: {summary.get('active_monitors', 0)}\n"
                summary_text += f"最后更新: {summary.get('last_update', 'N/A')}"
            else:
                summary_text = "增强性能桥接系统: 未启用"

            self.enhanced_performance_summary.setText(summary_text)

            # 更新性能趋势
            trends = self.import_engine.get_performance_trends()
            if trends:
                trends_text = "性能趋势分析:\n"
                for metric, trend_data in trends.items():
                    direction = trend_data.get('direction', 'stable')
                    change = trend_data.get('change_percent', 0)
                    trends_text += f"{metric}: {direction} ({change:+.1f}%)\n"
            else:
                trends_text = "暂无性能趋势数据"

            self.performance_trends.setText(trends_text)

        except Exception as e:
            logger.error(f"更新增强性能状态失败: {e}") if logger else None

    def create_task_management_tab(self) -> QWidget:
        """创建任务管理选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 工具栏
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)

        # 新建任务按钮
        new_task_btn = QPushButton("📝 新建任务")
        new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_task_btn.clicked.connect(self.create_new_import_task)
        toolbar_layout.addWidget(new_task_btn)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_task_list)
        toolbar_layout.addWidget(refresh_btn)

        # 批量操作按钮
        batch_start_btn = QPushButton("▶️ 批量启动")
        batch_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        batch_start_btn.clicked.connect(self.batch_start_tasks)
        toolbar_layout.addWidget(batch_start_btn)

        batch_stop_btn = QPushButton("⏹️ 批量停止")
        batch_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        batch_stop_btn.clicked.connect(self.batch_stop_tasks)
        toolbar_layout.addWidget(batch_stop_btn)

        toolbar_layout.addStretch()

        # 搜索框
        search_label = QLabel("🔍 搜索:")
        toolbar_layout.addWidget(search_label)

        self.task_search_input = QLineEdit()
        self.task_search_input.setPlaceholderText("输入任务名称或状态...")
        self.task_search_input.setMaximumWidth(200)
        self.task_search_input.textChanged.connect(self.filter_task_list)
        toolbar_layout.addWidget(self.task_search_input)

        layout.addWidget(toolbar_frame)

        # 任务列表表格
        self.task_table = QTableWidget()
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(True)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self.show_task_context_menu)

        # 设置表格列
        columns = [
            "任务名称", "状态", "进度", "数据源", "资产类型", "数据类型",
            "频率", "符号数量", "开始时间", "结束时间", "运行时间", "成功数", "失败数"
        ]
        self.task_table.setColumnCount(len(columns))
        self.task_table.setHorizontalHeaderLabels(columns)

        # 设置表格属性
        header = self.task_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 任务名称列自动拉伸

        # 设置列宽
        column_widths = [200, 80, 100, 100, 80, 80, 80, 80, 140, 140, 100, 60, 60]
        for i, width in enumerate(column_widths[1:], 1):  # 跳过第一列（自动拉伸）
            self.task_table.setColumnWidth(i, width)

        layout.addWidget(self.task_table)

        # 任务详情面板
        details_group = QGroupBox("📄 任务详情")
        details_layout = QVBoxLayout(details_group)

        self.task_details_text = QTextEdit()
        self.task_details_text.setMaximumHeight(120)
        self.task_details_text.setReadOnly(True)
        self.task_details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        details_layout.addWidget(self.task_details_text)

        layout.addWidget(details_group)

        # 连接表格选择信号
        self.task_table.itemSelectionChanged.connect(self.on_task_selection_changed)
        self.task_table.itemDoubleClicked.connect(self._on_task_double_clicked)

        # 初始化任务列表
        self.refresh_task_list()

        return tab

    def create_new_import_task(self):
        """创建新的导入任务"""
        try:
            # 获取当前配置
            task_name = f"导入任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 从symbols_edit获取股票代码
            symbols_text = self.symbols_edit.toPlainText().strip()
            symbols = [s.strip() for s in symbols_text.split('\n') if s.strip()] if symbols_text else []

            data_source = self.data_source_combo.currentText()
            asset_type = self.asset_type_combo.currentText()
            data_type = "K线数据"  # 默认数据类型

            # 频率映射
            freq_map = {
                "日线": DataFrequency.DAILY,
                "周线": DataFrequency.WEEKLY,
                "月线": DataFrequency.MONTHLY,
                "5分钟": DataFrequency.MINUTE_5,
                "15分钟": DataFrequency.MINUTE_15,
                "30分钟": DataFrequency.MINUTE_30,
                "60分钟": DataFrequency.HOUR_1
            }
            frequency = freq_map.get(self.frequency_combo.currentText(), DataFrequency.DAILY)

            if not symbols:
                QMessageBox.warning(self, "警告", "请输入股票代码")
                return

            # 创建任务配置
            task_config = ImportTaskConfig(
                task_id=f"task_{int(datetime.now().timestamp())}",
                name=task_name,
                symbols=symbols,
                data_source=data_source,
                asset_type=asset_type,
                data_type=data_type,
                frequency=frequency,
                mode=ImportMode.MANUAL,
                batch_size=self.batch_size_spin.value(),
                max_workers=self.workers_spin.value()
            )

            # 添加任务到配置管理器
            if self.config_manager:
                self.config_manager.add_import_task(task_config)
                logger.info(f"创建新任务: {task_name}") if logger else None

                # 刷新任务列表
                self.refresh_task_list()

                QMessageBox.information(self, "成功", f"任务 '{task_name}' 创建成功")
            else:
                QMessageBox.warning(self, "错误", "配置管理器未初始化")

        except Exception as e:
            logger.error(f"创建任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def refresh_task_list(self):
        """刷新任务列表"""
        try:
            if not self.config_manager:
                return

            # 获取所有任务
            tasks = self.config_manager.get_import_tasks()

            # 清空表格
            self.task_table.setRowCount(0)

            # 填充任务数据
            for task in tasks:
                row = self.task_table.rowCount()
                self.task_table.insertRow(row)

                # 获取任务状态
                task_status = None
                if self.import_engine:
                    task_status = self.import_engine.get_task_status(task.task_id)

                # 填充列数据
                items = [
                    task.name,
                    task_status.status.value if task_status else "未开始",
                    f"{task_status.progress:.1f}%" if task_status and hasattr(task_status, 'progress') else "0%",
                    task.data_source,
                    task.asset_type,
                    task.data_type,
                    task.frequency.value if hasattr(task.frequency, 'value') else str(task.frequency),
                    str(len(task.symbols)),
                    task_status.start_time.strftime('%Y-%m-%d %H:%M:%S') if task_status and task_status.start_time else "未开始",
                    task_status.end_time.strftime('%Y-%m-%d %H:%M:%S') if task_status and task_status.end_time else "未完成",
                    self.format_duration(task_status.execution_time) if task_status and hasattr(task_status, 'execution_time') else "0s",
                    str(task_status.success_count) if task_status and hasattr(task_status, 'success_count') else "0",
                    str(task_status.error_count) if task_status and hasattr(task_status, 'error_count') else "0"
                ]

                for col, item_text in enumerate(items):
                    item = QTableWidgetItem(str(item_text))

                    # 根据状态设置颜色
                    if col == 1:  # 状态列
                        if "运行中" in item_text:
                            item.setBackground(QColor("#d4edda"))
                        elif "完成" in item_text:
                            item.setBackground(QColor("#cce5ff"))
                        elif "失败" in item_text or "错误" in item_text:
                            item.setBackground(QColor("#f8d7da"))
                        elif "暂停" in item_text:
                            item.setBackground(QColor("#fff3cd"))

                    self.task_table.setItem(row, col, item)

                # 存储任务ID到第一列的数据中
                self.task_table.item(row, 0).setData(Qt.UserRole, task.task_id)

            logger.info(f"刷新任务列表完成，共 {len(tasks)} 个任务") if logger else None

        except Exception as e:
            logger.error(f"刷新任务列表失败: {e}") if logger else None

    def filter_task_list(self):
        """过滤任务列表"""
        try:
            filter_text = self.task_search_input.text().lower()

            for row in range(self.task_table.rowCount()):
                show_row = False

                # 检查任务名称和状态列
                for col in [0, 1]:  # 任务名称和状态
                    item = self.task_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        show_row = True
                        break

                self.task_table.setRowHidden(row, not show_row)

        except Exception as e:
            logger.error(f"过滤任务列表失败: {e}") if logger else None

    def on_task_selection_changed(self):
        """任务选择变化处理"""
        try:
            selected_items = self.task_table.selectedItems()
            if not selected_items:
                self.task_details_text.clear()
                return

            # 获取选中的第一行
            row = selected_items[0].row()
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)

            if not task_id or not self.import_engine:
                return

            # 获取任务详细信息
            task_status = self.import_engine.get_task_status(task_id)
            if task_status:
                details = f"""任务ID: {task_id}
状态: {task_status.status.value}
进度: {task_status.progress:.1f}% ({task_status.processed_count}/{task_status.total_count})
开始时间: {task_status.start_time.strftime('%Y-%m-%d %H:%M:%S') if task_status.start_time else '未开始'}
结束时间: {task_status.end_time.strftime('%Y-%m-%d %H:%M:%S') if task_status.end_time else '未完成'}
运行时间: {self.format_duration(task_status.execution_time) if hasattr(task_status, 'execution_time') else '0s'}
成功数量: {task_status.success_count if hasattr(task_status, 'success_count') else 0}
失败数量: {task_status.error_count if hasattr(task_status, 'error_count') else 0}
最后错误: {task_status.last_error if hasattr(task_status, 'last_error') and task_status.last_error else '无'}"""
            else:
                details = f"任务ID: {task_id}\n状态: 未开始\n详细信息暂不可用"

            self.task_details_text.setPlainText(details)

        except Exception as e:
            logger.error(f"更新任务详情失败: {e}") if logger else None

    def show_task_context_menu(self, position):
        """显示任务右键菜单"""
        try:
            item = self.task_table.itemAt(position)
            if not item:
                return

            menu = QMenu(self)

            # 获取选中的任务
            selected_rows = set()
            for item in self.task_table.selectedItems():
                selected_rows.add(item.row())

            if len(selected_rows) == 1:
                # 单个任务操作
                row = list(selected_rows)[0]
                task_id = self.task_table.item(row, 0).data(Qt.UserRole)
                status = self.task_table.item(row, 1).text()

                start_action = QAction("▶️ 启动任务", self)
                start_action.triggered.connect(lambda: self.start_single_task(task_id))
                start_action.setEnabled("运行中" not in status)
                menu.addAction(start_action)

                stop_action = QAction("⏹️ 停止任务", self)
                stop_action.triggered.connect(lambda: self.stop_single_task(task_id))
                stop_action.setEnabled("运行中" in status)
                menu.addAction(stop_action)

                menu.addSeparator()

                view_action = QAction("👁️ 查看详情", self)
                view_action.triggered.connect(lambda: self.view_task_details(task_id))
                menu.addAction(view_action)

                edit_action = QAction("✏️ 编辑任务", self)
                edit_action.triggered.connect(lambda: self.edit_task(task_id))
                menu.addAction(edit_action)

                menu.addSeparator()

                delete_action = QAction("🗑️ 删除任务", self)
                delete_action.triggered.connect(lambda: self.delete_single_task(task_id))
                menu.addAction(delete_action)

            else:
                # 批量操作
                batch_start_action = QAction(f"▶️ 批量启动 ({len(selected_rows)}个)", self)
                batch_start_action.triggered.connect(self.batch_start_tasks)
                menu.addAction(batch_start_action)

                batch_stop_action = QAction(f"⏹️ 批量停止 ({len(selected_rows)}个)", self)
                batch_stop_action.triggered.connect(self.batch_stop_tasks)
                menu.addAction(batch_stop_action)

                menu.addSeparator()

                batch_delete_action = QAction(f"🗑️ 批量删除 ({len(selected_rows)}个)", self)
                batch_delete_action.triggered.connect(self.batch_delete_tasks)
                menu.addAction(batch_delete_action)

            menu.exec_(self.task_table.mapToGlobal(position))

        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}") if logger else None

    def start_single_task(self, task_id: str):
        """启动单个任务"""
        try:
            if self.import_engine:
                success = self.import_engine.start_task(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务启动成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "失败", "任务启动失败")
        except Exception as e:
            logger.error(f"启动任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"启动任务失败: {e}")

    def stop_single_task(self, task_id: str):
        """停止单个任务"""
        try:
            if self.import_engine:
                success = self.import_engine.stop_task(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务停止成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "失败", "任务停止失败")
        except Exception as e:
            logger.error(f"停止任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"停止任务失败: {e}")

    def delete_single_task(self, task_id: str):
        """删除单个任务"""
        try:
            reply = QMessageBox.question(
                self, "确认删除",
                "确定要删除这个任务吗？\n删除后无法恢复。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                if self.config_manager:
                    self.config_manager.remove_import_task(task_id)
                    QMessageBox.information(self, "成功", "任务删除成功")
                    self.refresh_task_list()
                else:
                    QMessageBox.warning(self, "错误", "配置管理器未初始化")
        except Exception as e:
            logger.error(f"删除任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"删除任务失败: {e}")

    def batch_start_tasks(self):
        """批量启动任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要启动的任务")
                return

            success_count = 0
            for task_id in selected_task_ids:
                if self.import_engine and self.import_engine.start_task(task_id):
                    success_count += 1

            QMessageBox.information(
                self, "批量启动结果",
                f"成功启动 {success_count}/{len(selected_task_ids)} 个任务"
            )
            self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量启动任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量启动任务失败: {e}")

    def batch_stop_tasks(self):
        """批量停止任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要停止的任务")
                return

            success_count = 0
            for task_id in selected_task_ids:
                if self.import_engine and self.import_engine.stop_task(task_id):
                    success_count += 1

            QMessageBox.information(
                self, "批量停止结果",
                f"成功停止 {success_count}/{len(selected_task_ids)} 个任务"
            )
            self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量停止任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量停止任务失败: {e}")

    def batch_delete_tasks(self):
        """批量删除任务"""
        try:
            selected_task_ids = self.get_selected_task_ids()
            if not selected_task_ids:
                QMessageBox.warning(self, "警告", "请选择要删除的任务")
                return

            reply = QMessageBox.question(
                self, "确认批量删除",
                f"确定要删除选中的 {len(selected_task_ids)} 个任务吗？\n删除后无法恢复。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                success_count = 0
                for task_id in selected_task_ids:
                    if self.config_manager:
                        self.config_manager.remove_import_task(task_id)
                        success_count += 1

                QMessageBox.information(
                    self, "批量删除结果",
                    f"成功删除 {success_count}/{len(selected_task_ids)} 个任务"
                )
                self.refresh_task_list()

        except Exception as e:
            logger.error(f"批量删除任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"批量删除任务失败: {e}")

    def get_selected_task_ids(self) -> List[str]:
        """获取选中的任务ID列表"""
        task_ids = []
        selected_rows = set()

        for item in self.task_table.selectedItems():
            selected_rows.add(item.row())

        for row in selected_rows:
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)
            if task_id:
                task_ids.append(task_id)

        return task_ids

    def view_task_details(self, task_id: str):
        """查看任务详情"""
        try:
            # 这里可以打开一个详细的任务信息对话框
            # 暂时使用消息框显示基本信息
            if self.import_engine:
                task_status = self.import_engine.get_task_status(task_id)
                if task_status:
                    details = f"""任务详细信息:
任务ID: {task_id}
状态: {task_status.status.value}
进度: {task_status.progress:.1f}%
开始时间: {task_status.start_time.strftime('%Y-%m-%d %H:%M:%S') if task_status.start_time else '未开始'}
结束时间: {task_status.end_time.strftime('%Y-%m-%d %H:%M:%S') if task_status.end_time else '未完成'}"""
                    QMessageBox.information(self, "任务详情", details)
                else:
                    QMessageBox.information(self, "任务详情", f"任务ID: {task_id}\n状态: 未开始")
        except Exception as e:
            logger.error(f"查看任务详情失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"查看任务详情失败: {e}")

    def edit_task(self, task_id: str):
        """编辑任务"""
        try:
            # 这里可以打开任务编辑对话框
            # 暂时显示提示信息
            QMessageBox.information(self, "编辑任务", f"任务编辑功能开发中...\n任务ID: {task_id}")
        except Exception as e:
            logger.error(f"编辑任务失败: {e}") if logger else None
            QMessageBox.critical(self, "错误", f"编辑任务失败: {e}")

    def format_duration(self, seconds: float) -> str:
        """格式化持续时间"""
        try:
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h"
        except:
            return "0s"

    def _on_task_double_clicked(self, item):
        """任务双击处理"""
        try:
            if not item:
                return

            row = item.row()
            task_id = self.task_table.item(row, 0).data(Qt.UserRole)

            if task_id:
                self.view_task_details(task_id)

        except Exception as e:
            logger.error(f"处理任务双击失败: {e}") if logger else None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTabWidget::pane {
            border: 1px solid #cccccc;
            border-radius: 5px;
        }
        QTabBar::tab {
            background: #f0f0f0;
            border: 1px solid #cccccc;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #4a90e2;
            color: white;
        }
    """)

    widget = EnhancedDataImportWidget()
    widget.show()

    sys.exit(app.exec_())
