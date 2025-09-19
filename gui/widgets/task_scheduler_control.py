#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务调度控制组件

提供任务优先级设置和调度策略配置界面，包括：
- 任务优先级管理
- 调度策略配置
- 资源分配控制
- 调度队列监控

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox, QSlider,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTextEdit, QCheckBox, QDateTimeEdit, QTimeEdit,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QScrollArea,
    QMessageBox, QDialog, QDialogButtonBox, QApplication, QTreeWidget,
    QTreeWidgetItem, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsProxyWidget, QToolBar, QAction,
    QMenu, QActionGroup, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QDateTime, QTime, QDate
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient
)

# 导入核心服务
try:
    from core.services.import_orchestration_service import ImportOrchestrationService
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"核心服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    DEFERRED = 5


class SchedulingStrategy(Enum):
    """调度策略"""
    PRIORITY_FIRST = "priority_first"
    FIFO = "fifo"
    SHORTEST_JOB_FIRST = "shortest_job_first"
    ROUND_ROBIN = "round_robin"
    FAIR_SHARE = "fair_share"
    DEADLINE_AWARE = "deadline_aware"


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    DISK_IO = "disk_io"
    THREAD_POOL = "thread_pool"


@dataclass
class TaskScheduleInfo:
    """任务调度信息"""
    task_id: str
    name: str
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: int = 0  # 分钟
    deadline: Optional[datetime] = None
    resource_requirements: Dict[ResourceType, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    created_time: datetime = field(default_factory=datetime.now)
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchedulerConfig:
    """调度器配置"""
    strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIRST
    max_concurrent_tasks: int = 4
    resource_limits: Dict[ResourceType, float] = field(default_factory=dict)
    time_slice_ms: int = 1000  # 时间片（毫秒）
    priority_boost_interval: int = 300  # 优先级提升间隔（秒）
    enable_preemption: bool = False
    enable_load_balancing: bool = True
    queue_timeout_minutes: int = 60
    retry_delay_seconds: int = 30


class PriorityControlWidget(QWidget):
    """优先级控制组件"""

    priority_changed = pyqtSignal(str, int)  # task_id, priority

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 优先级设置区域
        priority_group = QGroupBox("⭐ 任务优先级设置")
        priority_layout = QGridLayout(priority_group)

        # 优先级级别
        priority_layout.addWidget(QLabel("优先级级别:"), 0, 0)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems([
            "🔴 紧急 (Critical)",
            "🟠 高 (High)",
            "🟡 普通 (Normal)",
            "🟢 低 (Low)",
            "🔵 延迟 (Deferred)"
        ])
        self.priority_combo.setCurrentIndex(2)  # 默认普通
        priority_layout.addWidget(self.priority_combo, 0, 1)

        # 优先级滑块
        priority_layout.addWidget(QLabel("优先级数值:"), 1, 0)
        self.priority_slider = QSlider(Qt.Horizontal)
        self.priority_slider.setRange(1, 5)
        self.priority_slider.setValue(3)
        self.priority_slider.setTickPosition(QSlider.TicksBelow)
        self.priority_slider.setTickInterval(1)
        priority_layout.addWidget(self.priority_slider, 1, 1)

        # 优先级标签
        self.priority_label = QLabel("普通 (3)")
        priority_layout.addWidget(self.priority_label, 1, 2)

        # 截止时间
        priority_layout.addWidget(QLabel("截止时间:"), 2, 0)
        self.deadline_edit = QDateTimeEdit()
        self.deadline_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.deadline_edit.setCalendarPopup(True)
        priority_layout.addWidget(self.deadline_edit, 2, 1)

        # 预估时长
        priority_layout.addWidget(QLabel("预估时长:"), 3, 0)
        duration_layout = QHBoxLayout()
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1440)  # 1分钟到24小时
        self.duration_spin.setValue(60)
        self.duration_spin.setSuffix(" 分钟")
        duration_layout.addWidget(self.duration_spin)
        priority_layout.addLayout(duration_layout, 3, 1)

        layout.addWidget(priority_group)

        # 资源需求区域
        resource_group = QGroupBox("💻 资源需求")
        resource_layout = QFormLayout(resource_group)

        # CPU需求
        self.cpu_slider = QSlider(Qt.Horizontal)
        self.cpu_slider.setRange(1, 100)
        self.cpu_slider.setValue(50)
        self.cpu_label = QLabel("50%")
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(self.cpu_slider)
        cpu_layout.addWidget(self.cpu_label)
        resource_layout.addRow("CPU:", cpu_layout)

        # 内存需求
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setRange(1, 100)
        self.memory_slider.setValue(30)
        self.memory_label = QLabel("30%")
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(self.memory_slider)
        memory_layout.addWidget(self.memory_label)
        resource_layout.addRow("内存:", memory_layout)

        # 网络需求
        self.network_slider = QSlider(Qt.Horizontal)
        self.network_slider.setRange(1, 100)
        self.network_slider.setValue(20)
        self.network_label = QLabel("20%")
        network_layout = QHBoxLayout()
        network_layout.addWidget(self.network_slider)
        network_layout.addWidget(self.network_label)
        resource_layout.addRow("网络:", network_layout)

        layout.addWidget(resource_group)

        # 高级选项
        advanced_group = QGroupBox("⚙️ 高级选项")
        advanced_layout = QFormLayout(advanced_group)

        # 最大重试次数
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        advanced_layout.addRow("最大重试:", self.retry_spin)

        # 允许抢占
        self.preemption_check = QCheckBox("允许被抢占")
        advanced_layout.addRow("抢占设置:", self.preemption_check)

        # 负载均衡
        self.load_balance_check = QCheckBox("启用负载均衡")
        self.load_balance_check.setChecked(True)
        advanced_layout.addRow("负载均衡:", self.load_balance_check)

        layout.addWidget(advanced_group)

        # 连接信号
        self.setup_connections()

    def setup_connections(self):
        """设置信号连接"""
        self.priority_slider.valueChanged.connect(self.update_priority_display)
        self.priority_combo.currentIndexChanged.connect(self.sync_priority_controls)
        self.cpu_slider.valueChanged.connect(lambda v: self.cpu_label.setText(f"{v}%"))
        self.memory_slider.valueChanged.connect(lambda v: self.memory_label.setText(f"{v}%"))
        self.network_slider.valueChanged.connect(lambda v: self.network_label.setText(f"{v}%"))

    def update_priority_display(self, value):
        """更新优先级显示"""
        priority_names = ["", "紧急", "高", "普通", "低", "延迟"]
        if 1 <= value <= 5:
            self.priority_label.setText(f"{priority_names[value]} ({value})")
            self.priority_combo.setCurrentIndex(value - 1)

    def sync_priority_controls(self, index):
        """同步优先级控件"""
        self.priority_slider.setValue(index + 1)

    def get_task_config(self) -> Dict[str, Any]:
        """获取任务配置"""
        return {
            'priority': self.priority_slider.value(),
            'deadline': self.deadline_edit.dateTime().toPyDateTime(),
            'estimated_duration': self.duration_spin.value(),
            'resource_requirements': {
                'cpu': self.cpu_slider.value() / 100.0,
                'memory': self.memory_slider.value() / 100.0,
                'network': self.network_slider.value() / 100.0
            },
            'max_retries': self.retry_spin.value(),
            'allow_preemption': self.preemption_check.isChecked(),
            'enable_load_balancing': self.load_balance_check.isChecked()
        }

    def set_task_config(self, config: Dict[str, Any]):
        """设置任务配置"""
        if 'priority' in config:
            self.priority_slider.setValue(config['priority'])

        if 'deadline' in config and config['deadline']:
            self.deadline_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(config['deadline'].timestamp())))

        if 'estimated_duration' in config:
            self.duration_spin.setValue(config['estimated_duration'])

        if 'resource_requirements' in config:
            reqs = config['resource_requirements']
            if 'cpu' in reqs:
                self.cpu_slider.setValue(int(reqs['cpu'] * 100))
            if 'memory' in reqs:
                self.memory_slider.setValue(int(reqs['memory'] * 100))
            if 'network' in reqs:
                self.network_slider.setValue(int(reqs['network'] * 100))

        if 'max_retries' in config:
            self.retry_spin.setValue(config['max_retries'])

        if 'allow_preemption' in config:
            self.preemption_check.setChecked(config['allow_preemption'])

        if 'enable_load_balancing' in config:
            self.load_balance_check.setChecked(config['enable_load_balancing'])


class SchedulingConfigWidget(QWidget):
    """调度配置组件"""

    config_changed = pyqtSignal(dict)  # 配置变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 调度策略
        strategy_group = QGroupBox("📋 调度策略")
        strategy_layout = QVBoxLayout(strategy_group)

        # 策略选择
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "优先级优先 (Priority First)",
            "先进先出 (FIFO)",
            "最短作业优先 (Shortest Job First)",
            "轮转调度 (Round Robin)",
            "公平共享 (Fair Share)",
            "截止时间感知 (Deadline Aware)"
        ])
        strategy_layout.addWidget(self.strategy_combo)

        # 策略描述
        self.strategy_desc = QLabel()
        self.strategy_desc.setWordWrap(True)
        self.strategy_desc.setStyleSheet("color: #666; font-style: italic;")
        strategy_layout.addWidget(self.strategy_desc)

        layout.addWidget(strategy_group)

        # 并发控制
        concurrency_group = QGroupBox("🔄 并发控制")
        concurrency_layout = QFormLayout(concurrency_group)

        # 最大并发任务数
        self.max_tasks_spin = QSpinBox()
        self.max_tasks_spin.setRange(1, 32)
        self.max_tasks_spin.setValue(4)
        concurrency_layout.addRow("最大并发任务:", self.max_tasks_spin)

        # 时间片大小
        self.time_slice_spin = QSpinBox()
        self.time_slice_spin.setRange(100, 10000)
        self.time_slice_spin.setValue(1000)
        self.time_slice_spin.setSuffix(" ms")
        concurrency_layout.addRow("时间片大小:", self.time_slice_spin)

        # 优先级提升间隔
        self.priority_boost_spin = QSpinBox()
        self.priority_boost_spin.setRange(60, 3600)
        self.priority_boost_spin.setValue(300)
        self.priority_boost_spin.setSuffix(" 秒")
        concurrency_layout.addRow("优先级提升间隔:", self.priority_boost_spin)

        layout.addWidget(concurrency_group)

        # 资源限制
        resource_group = QGroupBox("💾 资源限制")
        resource_layout = QFormLayout(resource_group)

        # CPU限制
        self.cpu_limit_spin = QSpinBox()
        self.cpu_limit_spin.setRange(10, 100)
        self.cpu_limit_spin.setValue(80)
        self.cpu_limit_spin.setSuffix("%")
        resource_layout.addRow("CPU限制:", self.cpu_limit_spin)

        # 内存限制
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(10, 100)
        self.memory_limit_spin.setValue(70)
        self.memory_limit_spin.setSuffix("%")
        resource_layout.addRow("内存限制:", self.memory_limit_spin)

        # 网络限制
        self.network_limit_spin = QSpinBox()
        self.network_limit_spin.setRange(10, 100)
        self.network_limit_spin.setValue(60)
        self.network_limit_spin.setSuffix("%")
        resource_layout.addRow("网络限制:", self.network_limit_spin)

        layout.addWidget(resource_group)

        # 高级设置
        advanced_group = QGroupBox("🔧 高级设置")
        advanced_layout = QFormLayout(advanced_group)

        # 启用抢占
        self.preemption_check = QCheckBox("启用任务抢占")
        advanced_layout.addRow("抢占控制:", self.preemption_check)

        # 启用负载均衡
        self.load_balancing_check = QCheckBox("启用负载均衡")
        self.load_balancing_check.setChecked(True)
        advanced_layout.addRow("负载均衡:", self.load_balancing_check)

        # 队列超时
        self.queue_timeout_spin = QSpinBox()
        self.queue_timeout_spin.setRange(5, 240)
        self.queue_timeout_spin.setValue(60)
        self.queue_timeout_spin.setSuffix(" 分钟")
        advanced_layout.addRow("队列超时:", self.queue_timeout_spin)

        # 重试延迟
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(5, 300)
        self.retry_delay_spin.setValue(30)
        self.retry_delay_spin.setSuffix(" 秒")
        advanced_layout.addRow("重试延迟:", self.retry_delay_spin)

        layout.addWidget(advanced_group)

        # 连接信号
        self.setup_connections()
        self.update_strategy_description()

    def setup_connections(self):
        """设置信号连接"""
        self.strategy_combo.currentIndexChanged.connect(self.update_strategy_description)
        self.strategy_combo.currentIndexChanged.connect(self.emit_config_changed)
        self.max_tasks_spin.valueChanged.connect(self.emit_config_changed)
        self.preemption_check.toggled.connect(self.emit_config_changed)
        self.load_balancing_check.toggled.connect(self.emit_config_changed)

    def update_strategy_description(self):
        """更新策略描述"""
        descriptions = [
            "根据任务优先级进行调度，高优先级任务优先执行",
            "按照任务到达顺序进行调度，先到先服务",
            "优先执行预估时间最短的任务",
            "为每个任务分配固定时间片，轮流执行",
            "根据资源使用情况公平分配执行时间",
            "考虑任务截止时间，优先执行即将到期的任务"
        ]

        index = self.strategy_combo.currentIndex()
        if 0 <= index < len(descriptions):
            self.strategy_desc.setText(descriptions[index])

    def emit_config_changed(self):
        """发射配置变更信号"""
        config = self.get_scheduler_config()
        self.config_changed.emit(config)

    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        strategies = [
            SchedulingStrategy.PRIORITY_FIRST,
            SchedulingStrategy.FIFO,
            SchedulingStrategy.SHORTEST_JOB_FIRST,
            SchedulingStrategy.ROUND_ROBIN,
            SchedulingStrategy.FAIR_SHARE,
            SchedulingStrategy.DEADLINE_AWARE
        ]

        return {
            'strategy': strategies[self.strategy_combo.currentIndex()].value,
            'max_concurrent_tasks': self.max_tasks_spin.value(),
            'time_slice_ms': self.time_slice_spin.value(),
            'priority_boost_interval': self.priority_boost_spin.value(),
            'resource_limits': {
                'cpu': self.cpu_limit_spin.value() / 100.0,
                'memory': self.memory_limit_spin.value() / 100.0,
                'network': self.network_limit_spin.value() / 100.0
            },
            'enable_preemption': self.preemption_check.isChecked(),
            'enable_load_balancing': self.load_balancing_check.isChecked(),
            'queue_timeout_minutes': self.queue_timeout_spin.value(),
            'retry_delay_seconds': self.retry_delay_spin.value()
        }


class ScheduleQueueWidget(QWidget):
    """调度队列组件"""

    task_selected = pyqtSignal(str)  # 任务选中信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks: Dict[str, TaskScheduleInfo] = {}
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_queue)
        toolbar.addWidget(refresh_btn)

        # 清空队列按钮
        clear_btn = QPushButton("🗑️ 清空队列")
        clear_btn.clicked.connect(self.clear_queue)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        # 队列统计
        self.stats_label = QLabel("队列统计: 0 个任务")
        toolbar.addWidget(self.stats_label)

        layout.addLayout(toolbar)

        # 队列表格
        self.queue_table = QTableWidget()
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setSortingEnabled(True)

        # 设置列
        columns = [
            "任务名称", "优先级", "状态", "预估时长", "截止时间",
            "资源需求", "依赖数", "创建时间", "等待时间"
        ]
        self.queue_table.setColumnCount(len(columns))
        self.queue_table.setHorizontalHeaderLabels(columns)

        # 设置列宽
        header = self.queue_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(self.queue_table)

        # 连接信号
        self.queue_table.itemSelectionChanged.connect(self.on_selection_changed)

    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waiting_times)
        self.update_timer.start(1000)  # 每秒更新一次

    def add_task(self, task_info: TaskScheduleInfo):
        """添加任务到队列"""
        self.tasks[task_info.task_id] = task_info
        self.refresh_queue()

    def remove_task(self, task_id: str):
        """从队列移除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.refresh_queue()

    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.refresh_queue()

    def refresh_queue(self):
        """刷新队列显示"""
        # 清空表格
        self.queue_table.setRowCount(0)

        # 按优先级和创建时间排序
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: (t.priority.value, t.created_time)
        )

        # 填充表格
        for row, task in enumerate(sorted_tasks):
            self.queue_table.insertRow(row)

            # 任务名称
            name_item = QTableWidgetItem(task.name)
            name_item.setData(Qt.UserRole, task.task_id)
            self.queue_table.setItem(row, 0, name_item)

            # 优先级
            priority_colors = {
                TaskPriority.CRITICAL: "#e74c3c",
                TaskPriority.HIGH: "#f39c12",
                TaskPriority.NORMAL: "#3498db",
                TaskPriority.LOW: "#2ecc71",
                TaskPriority.DEFERRED: "#95a5a6"
            }
            priority_item = QTableWidgetItem(task.priority.name)
            priority_item.setBackground(QColor(priority_colors.get(task.priority, "#3498db")))
            self.queue_table.setItem(row, 1, priority_item)

            # 状态
            status_item = QTableWidgetItem(task.status)
            self.queue_table.setItem(row, 2, status_item)

            # 预估时长
            duration_item = QTableWidgetItem(f"{task.estimated_duration} 分钟")
            self.queue_table.setItem(row, 3, duration_item)

            # 截止时间
            deadline_text = task.deadline.strftime("%Y-%m-%d %H:%M") if task.deadline else "无"
            deadline_item = QTableWidgetItem(deadline_text)
            self.queue_table.setItem(row, 4, deadline_item)

            # 资源需求
            resource_text = ", ".join([
                f"{k.value}: {v:.0%}" for k, v in task.resource_requirements.items()
            ])
            resource_item = QTableWidgetItem(resource_text)
            self.queue_table.setItem(row, 5, resource_item)

            # 依赖数
            deps_item = QTableWidgetItem(str(len(task.dependencies)))
            self.queue_table.setItem(row, 6, deps_item)

            # 创建时间
            created_item = QTableWidgetItem(task.created_time.strftime("%H:%M:%S"))
            self.queue_table.setItem(row, 7, created_item)

            # 等待时间
            waiting_time = datetime.now() - task.created_time
            waiting_item = QTableWidgetItem(self.format_duration(waiting_time))
            self.queue_table.setItem(row, 8, waiting_item)

        # 更新统计
        self.update_statistics()

    def update_waiting_times(self):
        """更新等待时间"""
        for row in range(self.queue_table.rowCount()):
            name_item = self.queue_table.item(row, 0)
            if name_item:
                task_id = name_item.data(Qt.UserRole)
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    waiting_time = datetime.now() - task.created_time
                    waiting_item = QTableWidgetItem(self.format_duration(waiting_time))
                    self.queue_table.setItem(row, 8, waiting_item)

    def update_statistics(self):
        """更新统计信息"""
        total_tasks = len(self.tasks)
        pending_tasks = sum(1 for t in self.tasks.values() if t.status == "pending")
        running_tasks = sum(1 for t in self.tasks.values() if t.status == "running")

        stats_text = f"队列统计: {total_tasks} 个任务 (等待: {pending_tasks}, 运行: {running_tasks})"
        self.stats_label.setText(stats_text)

    def format_duration(self, duration: timedelta) -> str:
        """格式化持续时间"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def on_selection_changed(self):
        """处理选择变更"""
        current_item = self.queue_table.currentItem()
        if current_item:
            row = current_item.row()
            name_item = self.queue_table.item(row, 0)
            if name_item:
                task_id = name_item.data(Qt.UserRole)
                self.task_selected.emit(task_id)

    def clear_queue(self):
        """清空队列"""
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有队列任务吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.tasks.clear()
            self.refresh_queue()


class TaskSchedulerControl(QWidget):
    """任务调度控制主组件"""

    def __init__(self, ui_adapter=None, parent=None):
        super().__init__(parent)
        self.ui_adapter = ui_adapter
        self.orchestration_service = None

        # 初始化服务
        if CORE_AVAILABLE:
            try:
                if self.ui_adapter is None:
                    self.ui_adapter = get_ui_adapter()
                # 这里可以初始化ImportOrchestrationService
                # self.orchestration_service = ImportOrchestrationService()
            except Exception as e:
                logger.warning(f"服务初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.load_sample_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 优先级控制选项卡
        priority_tab = PriorityControlWidget()
        self.tab_widget.addTab(priority_tab, "⭐ 优先级控制")

        # 调度配置选项卡
        config_tab = SchedulingConfigWidget()
        self.tab_widget.addTab(config_tab, "📋 调度配置")

        # 调度队列选项卡
        queue_tab = ScheduleQueueWidget()
        self.tab_widget.addTab(queue_tab, "📊 调度队列")

        # 监控面板选项卡
        monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(monitor_tab, "📈 监控面板")

        layout.addWidget(self.tab_widget)

        # 保存引用
        self.priority_widget = priority_tab
        self.config_widget = config_tab
        self.queue_widget = queue_tab

    def create_monitor_tab(self) -> QWidget:
        """创建监控面板选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 实时统计
        stats_group = QGroupBox("📊 实时统计")
        stats_layout = QGridLayout(stats_group)

        # 任务统计
        self.total_tasks_label = QLabel("总任务数: 0")
        stats_layout.addWidget(self.total_tasks_label, 0, 0)

        self.running_tasks_label = QLabel("运行中: 0")
        stats_layout.addWidget(self.running_tasks_label, 0, 1)

        self.pending_tasks_label = QLabel("等待中: 0")
        stats_layout.addWidget(self.pending_tasks_label, 1, 0)

        self.completed_tasks_label = QLabel("已完成: 0")
        stats_layout.addWidget(self.completed_tasks_label, 1, 1)

        layout.addWidget(stats_group)

        # 资源使用情况
        resource_group = QGroupBox("💻 资源使用")
        resource_layout = QFormLayout(resource_group)

        # CPU使用率
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        resource_layout.addRow("CPU:", self.cpu_progress)

        # 内存使用率
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        resource_layout.addRow("内存:", self.memory_progress)

        # 网络使用率
        self.network_progress = QProgressBar()
        self.network_progress.setRange(0, 100)
        resource_layout.addRow("网络:", self.network_progress)

        layout.addWidget(resource_group)

        # 调度器状态
        scheduler_group = QGroupBox("⚙️ 调度器状态")
        scheduler_layout = QFormLayout(scheduler_group)

        self.scheduler_status_label = QLabel("运行中")
        scheduler_layout.addRow("状态:", self.scheduler_status_label)

        self.current_strategy_label = QLabel("优先级优先")
        scheduler_layout.addRow("当前策略:", self.current_strategy_label)

        self.queue_length_label = QLabel("0")
        scheduler_layout.addRow("队列长度:", self.queue_length_label)

        layout.addWidget(scheduler_group)

        layout.addStretch()

        return widget

    def setup_connections(self):
        """设置信号连接"""
        # 优先级控制信号
        if hasattr(self, 'priority_widget'):
            self.priority_widget.priority_changed.connect(self.on_priority_changed)

        # 配置变更信号
        if hasattr(self, 'config_widget'):
            self.config_widget.config_changed.connect(self.on_config_changed)

        # 队列选择信号
        if hasattr(self, 'queue_widget'):
            self.queue_widget.task_selected.connect(self.on_task_selected)

    def load_sample_data(self):
        """加载示例数据"""
        # 创建示例任务
        sample_tasks = [
            TaskScheduleInfo(
                "task1", "数据获取任务", TaskPriority.HIGH,
                estimated_duration=30,
                deadline=datetime.now() + timedelta(hours=2),
                resource_requirements={
                    ResourceType.CPU: 0.6,
                    ResourceType.MEMORY: 0.4,
                    ResourceType.NETWORK: 0.8
                }
            ),
            TaskScheduleInfo(
                "task2", "数据处理任务", TaskPriority.NORMAL,
                estimated_duration=60,
                resource_requirements={
                    ResourceType.CPU: 0.8,
                    ResourceType.MEMORY: 0.6
                }
            ),
            TaskScheduleInfo(
                "task3", "报告生成任务", TaskPriority.LOW,
                estimated_duration=15,
                deadline=datetime.now() + timedelta(days=1),
                resource_requirements={
                    ResourceType.CPU: 0.3,
                    ResourceType.MEMORY: 0.2
                }
            )
        ]

        # 添加到队列
        for task in sample_tasks:
            self.queue_widget.add_task(task)

        # 更新监控数据
        self.update_monitor_data()

    def on_priority_changed(self, task_id: str, priority: int):
        """处理优先级变更"""
        logger.info(f"任务 {task_id} 优先级变更为 {priority}")
        # 这里可以调用实际的优先级更新逻辑

    def on_config_changed(self, config: Dict[str, Any]):
        """处理配置变更"""
        logger.info(f"调度配置变更: {config}")
        # 更新调度器配置
        if self.orchestration_service:
            # self.orchestration_service.update_config(config)
            pass

        # 更新监控显示
        self.current_strategy_label.setText(config.get('strategy', '未知'))

    def on_task_selected(self, task_id: str):
        """处理任务选择"""
        if task_id in self.queue_widget.tasks:
            task = self.queue_widget.tasks[task_id]

            # 在优先级控制面板中显示任务信息
            config = {
                'priority': task.priority.value,
                'deadline': task.deadline,
                'estimated_duration': task.estimated_duration,
                'resource_requirements': {
                    rt.value: req for rt, req in task.resource_requirements.items()
                },
                'max_retries': task.max_retries
            }

            self.priority_widget.set_task_config(config)

    def update_monitor_data(self):
        """更新监控数据"""
        # 更新任务统计
        total_tasks = len(self.queue_widget.tasks)
        running_tasks = sum(1 for t in self.queue_widget.tasks.values() if t.status == "running")
        pending_tasks = sum(1 for t in self.queue_widget.tasks.values() if t.status == "pending")
        completed_tasks = sum(1 for t in self.queue_widget.tasks.values() if t.status == "completed")

        self.total_tasks_label.setText(f"总任务数: {total_tasks}")
        self.running_tasks_label.setText(f"运行中: {running_tasks}")
        self.pending_tasks_label.setText(f"等待中: {pending_tasks}")
        self.completed_tasks_label.setText(f"已完成: {completed_tasks}")

        # 更新队列长度
        self.queue_length_label.setText(str(pending_tasks))

        # 模拟资源使用情况
        import random
        self.cpu_progress.setValue(random.randint(30, 80))
        self.memory_progress.setValue(random.randint(20, 70))
        self.network_progress.setValue(random.randint(10, 60))


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
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 5px 10px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 2px;
        }
    """)

    # 创建主窗口
    widget = TaskSchedulerControl()
    widget.setWindowTitle("任务调度控制")
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec_())
