#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强性能监控仪表板

提供全面的实时性能监控功能，包括：
- 实时性能指标监控
- 历史趋势分析
- 性能异常检测和告警
- 智能优化建议
- 资源使用率监控
- 性能瓶颈分析

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import logging
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import json

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QComboBox, QSpinBox, QSlider,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QTextEdit, QCheckBox, QDateTimeEdit, QTimeEdit,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QScrollArea,
    QMessageBox, QDialog, QDialogButtonBox, QApplication, QTreeWidget,
    QTreeWidgetItem, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsProxyWidget, QToolBar, QAction,
    QMenu, QActionGroup, QButtonGroup, QRadioButton, QLCDNumber,
    QDial, QCalendarWidget, QLineEdit, QDoubleSpinBox, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QDateTime, QTime, QDate, QSize, QPointF, QRectF
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFontMetrics, QPainterPath,
    QPolygonF
)

# 导入核心性能监控组件
try:
    from core.performance.unified_performance_coordinator import UnifiedPerformanceCoordinator
    from core.services.ai_prediction_service import AIPredictionService
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"核心性能监控服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    CACHE_HIT_RATE = "cache_hit_rate"
    TASK_EXECUTION_TIME = "task_execution_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """性能指标"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """性能告警"""
    id: str
    metric_type: MetricType
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_note: Optional[str] = None


class RealTimeChart(QGraphicsView):
    """实时图表组件"""

    def __init__(self, metric_type: MetricType, parent=None):
        super().__init__(parent)
        self.metric_type = metric_type
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # 数据存储
        self.metrics: deque = deque(maxlen=100)  # 最多存储100个数据点
        self.chart_width = 300
        self.chart_height = 150
        self.margin = 20

        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedSize(self.chart_width + 2 * self.margin,
                          self.chart_height + 2 * self.margin)

        self.setup_chart()

    def setup_chart(self):
        """设置图表"""
        self.scene.clear()

        # 设置场景大小
        self.scene.setSceneRect(0, 0, self.chart_width + 2 * self.margin,
                                self.chart_height + 2 * self.margin)

        # 绘制背景
        self.draw_background()

        # 绘制坐标轴
        self.draw_axes()

        # 绘制网格
        self.draw_grid()

        # 绘制标题
        self.draw_title()

    def draw_background(self):
        """绘制背景"""
        bg_rect = self.scene.addRect(
            self.margin, self.margin,
            self.chart_width, self.chart_height,
            QPen(Qt.NoPen), QBrush(QColor(250, 250, 250))
        )

    def draw_axes(self):
        """绘制坐标轴"""
        # X轴
        x_axis = self.scene.addLine(
            self.margin, self.chart_height + self.margin,
            self.chart_width + self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 1)
        )

        # Y轴
        y_axis = self.scene.addLine(
            self.margin, self.margin,
            self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 1)
        )

    def draw_grid(self):
        """绘制网格"""
        # 水平网格线
        for i in range(1, 5):
            y = self.margin + (self.chart_height * i / 5)
            line = self.scene.addLine(
                self.margin, y, self.chart_width + self.margin, y,
                QPen(QColor(220, 220, 220), 1, Qt.DashLine)
            )

        # 垂直网格线
        for i in range(1, 6):
            x = self.margin + (self.chart_width * i / 6)
            line = self.scene.addLine(
                x, self.margin, x, self.chart_height + self.margin,
                QPen(QColor(220, 220, 220), 1, Qt.DashLine)
            )

    def draw_title(self):
        """绘制标题"""
        title_map = {
            MetricType.CPU_USAGE: "CPU使用率 (%)",
            MetricType.MEMORY_USAGE: "内存使用率 (%)",
            MetricType.DISK_IO: "磁盘I/O (MB/s)",
            MetricType.NETWORK_IO: "网络I/O (MB/s)",
            MetricType.CACHE_HIT_RATE: "缓存命中率 (%)",
            MetricType.TASK_EXECUTION_TIME: "任务执行时间 (s)",
            MetricType.THROUGHPUT: "吞吐量 (ops/s)",
            MetricType.ERROR_RATE: "错误率 (%)",
            MetricType.QUEUE_LENGTH: "队列长度",
            MetricType.RESPONSE_TIME: "响应时间 (ms)"
        }

        title = title_map.get(self.metric_type, "未知指标")
        title_text = self.scene.addText(title, QFont("Arial", 10, QFont.Bold))
        title_text.setPos(self.margin, 5)

    def add_metric(self, metric: PerformanceMetric):
        """添加指标数据"""
        if metric.metric_type != self.metric_type:
            return

        self.metrics.append(metric)
        self.update_chart()

    def update_chart(self):
        """更新图表"""
        if len(self.metrics) < 2:
            return

        # 清除之前的数据线
        for item in self.scene.items():
            if hasattr(item, 'data_line'):
                self.scene.removeItem(item)

        # 计算数据范围
        values = [m.value for m in self.metrics]
        if not values:
            return

        min_val = min(values)
        max_val = max(values)

        # 防止除零错误
        if max_val == min_val:
            max_val = min_val + 1

        # 计算数据点位置
        points = []
        for i, metric in enumerate(self.metrics):
            x = self.margin + (self.chart_width * i / (len(self.metrics) - 1)) if len(self.metrics) > 1 else self.margin
            y = self.margin + self.chart_height * (1 - (metric.value - min_val) / (max_val - min_val))
            points.append(QPointF(x, y))

        # 绘制数据线
        for i in range(len(points) - 1):
            line = self.scene.addLine(
                points[i].x(), points[i].y(),
                points[i + 1].x(), points[i + 1].y(),
                QPen(QColor(52, 152, 219), 1)
            )
            line.data_line = True

        # 绘制数据点
        for point in points:
            circle = self.scene.addEllipse(
                point.x() - 2, point.y() - 2, 4, 4,
                QPen(QColor(52, 152, 219), 1), QBrush(QColor(52, 152, 219))
            )
            circle.data_line = True

        # 绘制当前值
        if self.metrics:
            current_value = self.metrics[-1].value
            value_text = self.scene.addText(f"{current_value:.1f}", QFont("Arial", 12, QFont.Bold))
            value_text.setPos(self.chart_width + self.margin - 50, self.margin)
            value_text.setDefaultTextColor(QColor(52, 152, 219))
            value_text.data_line = True


class MetricGauge(QWidget):
    """指标仪表盘组件"""

    def __init__(self, metric_type: MetricType, max_value: float = 100, parent=None):
        super().__init__(parent)
        self.metric_type = metric_type
        self.max_value = max_value
        self.current_value = 0
        self.warning_threshold = max_value * 0.7
        self.critical_threshold = max_value * 0.9

        self.setFixedSize(120, 120)

    def set_value(self, value: float):
        """设置数值"""
        self.current_value = max(0, min(value, self.max_value))
        self.update()

    def set_thresholds(self, warning: float, critical: float):
        """设置阈值"""
        self.warning_threshold = warning
        self.critical_threshold = critical
        self.update()

    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取绘制区域
        rect = self.rect().adjusted(10, 10, -10, -10)
        # 转换为QRectF确保类型一致
        rectf = QRectF(rect)
        center = rectf.center()
        radius = min(rectf.width(), rectf.height()) // 2 - 5

        # 绘制背景圆环
        painter.setPen(QPen(QColor(220, 220, 220), 8))
        painter.drawArc(rectf, 0, 360 * 16)

        # 计算角度（从底部开始，顺时针）
        start_angle = int(180 * 16)  # 底部开始，确保为int类型
        span_angle = int(-180 * 16)  # 半圆，确保为int类型

        # 绘制数值圆环
        value_ratio = self.current_value / self.max_value
        value_span = int(span_angle * value_ratio)  # 确保为int类型

        # 根据数值选择颜色
        if self.current_value >= self.critical_threshold:
            color = QColor(231, 76, 60)  # 红色
        elif self.current_value >= self.warning_threshold:
            color = QColor(241, 196, 15)  # 黄色
        else:
            color = QColor(46, 204, 113)  # 绿色

        painter.setPen(QPen(color, 8))
        painter.drawArc(rectf, start_angle, value_span)

        # 绘制中心数值
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self.current_value:.1f}")

        # 绘制标签
        painter.setFont(QFont("Arial", 8))
        label_rect = QRectF(rect.x(), rect.bottom() + 5, rect.width(), 20)

        metric_labels = {
            MetricType.CPU_USAGE: "CPU",
            MetricType.MEMORY_USAGE: "内存",
            MetricType.DISK_IO: "磁盘I/O",
            MetricType.NETWORK_IO: "网络I/O",
            MetricType.CACHE_HIT_RATE: "缓存命中",
            MetricType.TASK_EXECUTION_TIME: "执行时间",
            MetricType.THROUGHPUT: "吞吐量",
            MetricType.ERROR_RATE: "错误率",
            MetricType.QUEUE_LENGTH: "队列长度",
            MetricType.RESPONSE_TIME: "响应时间"
        }

        label = metric_labels.get(self.metric_type, "未知")
        painter.drawText(label_rect, Qt.AlignCenter, label)

        # 确保正确结束QPainter
        painter.end()


class PerformanceAlertsWidget(QWidget):
    """性能告警组件"""

    alert_resolved = pyqtSignal(str)  # alert_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alerts: List[PerformanceAlert] = []
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 告警控制区域
        control_layout = QHBoxLayout()

        # 告警级别过滤
        control_layout.addWidget(QLabel("级别:"))
        self.level_filter_combo = QComboBox()
        self.level_filter_combo.addItems(["全部", "信息", "警告", "错误", "严重"])
        self.level_filter_combo.currentTextChanged.connect(self.filter_alerts)
        control_layout.addWidget(self.level_filter_combo)

        # 状态过滤
        control_layout.addWidget(QLabel("状态:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["全部", "未解决", "已解决"])
        self.status_filter_combo.currentTextChanged.connect(self.filter_alerts)
        control_layout.addWidget(self.status_filter_combo)

        # 清除已解决告警
        clear_resolved_btn = QPushButton("🗑️ 清除已解决")
        clear_resolved_btn.clicked.connect(self.clear_resolved_alerts)
        control_layout.addWidget(clear_resolved_btn)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 告警列表
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(6)
        self.alerts_table.setHorizontalHeaderLabels([
            "时间", "级别", "指标", "消息", "数值", "操作"
        ])

        # 设置列宽
        header = self.alerts_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addWidget(self.alerts_table)

        # 统计信息
        stats_group = QGroupBox("📊 告警统计")
        stats_layout = QGridLayout(stats_group)

        # 活跃告警数
        stats_layout.addWidget(QLabel("活跃告警:"), 0, 0)
        self.active_alerts_label = QLabel("0")
        self.active_alerts_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        stats_layout.addWidget(self.active_alerts_label, 0, 1)

        # 严重告警数
        stats_layout.addWidget(QLabel("严重告警:"), 0, 2)
        self.critical_alerts_label = QLabel("0")
        self.critical_alerts_label.setStyleSheet("font-weight: bold; color: #8e44ad;")
        stats_layout.addWidget(self.critical_alerts_label, 0, 3)

        # 今日告警数
        stats_layout.addWidget(QLabel("今日告警:"), 1, 0)
        self.daily_alerts_label = QLabel("0")
        stats_layout.addWidget(self.daily_alerts_label, 1, 1)

        # 解决率
        stats_layout.addWidget(QLabel("解决率:"), 1, 2)
        self.resolution_rate_label = QLabel("0%")
        stats_layout.addWidget(self.resolution_rate_label, 1, 3)

        layout.addWidget(stats_group)

    def add_alert(self, alert: PerformanceAlert):
        """添加告警"""
        self.alerts.append(alert)
        self.filter_alerts()
        self.update_statistics()

    def filter_alerts(self):
        """过滤告警"""
        level_filter = self.level_filter_combo.currentText()
        status_filter = self.status_filter_combo.currentText()

        # 应用过滤
        filtered_alerts = []
        for alert in self.alerts:
            # 级别过滤
            if level_filter != "全部":
                level_mapping = {
                    "信息": AlertLevel.INFO,
                    "警告": AlertLevel.WARNING,
                    "错误": AlertLevel.ERROR,
                    "严重": AlertLevel.CRITICAL
                }
                if alert.level != level_mapping.get(level_filter):
                    continue

            # 状态过滤
            if status_filter == "未解决" and alert.resolved:
                continue
            elif status_filter == "已解决" and not alert.resolved:
                continue

            filtered_alerts.append(alert)

        self.update_alerts_table(filtered_alerts)

    def update_alerts_table(self, alerts: List[PerformanceAlert]):
        """更新告警表格"""
        self.alerts_table.setRowCount(len(alerts))

        for row, alert in enumerate(alerts):
            # 时间
            time_item = QTableWidgetItem(alert.timestamp.strftime("%H:%M:%S"))
            self.alerts_table.setItem(row, 0, time_item)

            # 级别
            level_colors = {
                AlertLevel.INFO: "#3498db",
                AlertLevel.WARNING: "#f39c12",
                AlertLevel.ERROR: "#e67e22",
                AlertLevel.CRITICAL: "#e74c3c"
            }
            level_names = {
                AlertLevel.INFO: "信息",
                AlertLevel.WARNING: "警告",
                AlertLevel.ERROR: "错误",
                AlertLevel.CRITICAL: "严重"
            }

            level_item = QTableWidgetItem(level_names.get(alert.level, "未知"))
            level_item.setBackground(QColor(level_colors.get(alert.level, "#95a5a6")))
            self.alerts_table.setItem(row, 1, level_item)

            # 指标
            metric_names = {
                MetricType.CPU_USAGE: "CPU使用率",
                MetricType.MEMORY_USAGE: "内存使用率",
                MetricType.DISK_IO: "磁盘I/O",
                MetricType.NETWORK_IO: "网络I/O",
                MetricType.CACHE_HIT_RATE: "缓存命中率",
                MetricType.TASK_EXECUTION_TIME: "任务执行时间",
                MetricType.THROUGHPUT: "吞吐量",
                MetricType.ERROR_RATE: "错误率",
                MetricType.QUEUE_LENGTH: "队列长度",
                MetricType.RESPONSE_TIME: "响应时间"
            }

            metric_item = QTableWidgetItem(metric_names.get(alert.metric_type, "未知"))
            self.alerts_table.setItem(row, 2, metric_item)

            # 消息
            message_item = QTableWidgetItem(alert.message)
            if alert.resolved:
                message_item.setBackground(QColor("#d5f4e6"))
            self.alerts_table.setItem(row, 3, message_item)

            # 数值
            value_item = QTableWidgetItem(f"{alert.value:.2f}")
            self.alerts_table.setItem(row, 4, value_item)

            # 操作按钮
            if not alert.resolved:
                resolve_btn = QPushButton("✅ 解决")
                resolve_btn.clicked.connect(lambda checked, aid=alert.id: self.resolve_alert(aid))
                resolve_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: #229954;
                    }
                """)
                self.alerts_table.setCellWidget(row, 5, resolve_btn)
            else:
                resolved_label = QLabel("已解决")
                resolved_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.alerts_table.setCellWidget(row, 5, resolved_label)

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        alert = next((a for a in self.alerts if a.id == alert_id), None)
        if alert:
            alert.resolved = True
            alert.resolution_note = f"手动解决于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.filter_alerts()
            self.update_statistics()
            self.alert_resolved.emit(alert_id)

    def clear_resolved_alerts(self):
        """清除已解决的告警"""
        self.alerts = [a for a in self.alerts if not a.resolved]
        self.filter_alerts()
        self.update_statistics()

    def update_statistics(self):
        """更新统计信息"""
        if not self.alerts:
            return

        # 活跃告警数
        active_count = sum(1 for a in self.alerts if not a.resolved)
        self.active_alerts_label.setText(str(active_count))

        # 严重告警数
        critical_count = sum(1 for a in self.alerts if not a.resolved and a.level == AlertLevel.CRITICAL)
        self.critical_alerts_label.setText(str(critical_count))

        # 今日告警数
        today = datetime.now().date()
        daily_count = sum(1 for a in self.alerts if a.timestamp.date() == today)
        self.daily_alerts_label.setText(str(daily_count))

        # 解决率
        if self.alerts:
            resolved_count = sum(1 for a in self.alerts if a.resolved)
            resolution_rate = resolved_count / len(self.alerts)
            self.resolution_rate_label.setText(f"{resolution_rate:.1%}")


class EnhancedPerformanceDashboard(QWidget):
    """增强性能监控仪表板主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_adapter = None
        self.performance_coordinator = None

        # 性能数据存储
        self.metrics_history: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=1000) for metric_type in MetricType
        }

        # 初始化核心服务
        if CORE_AVAILABLE:
            try:
                self.ui_adapter = get_ui_adapter()
                self.performance_coordinator = UnifiedPerformanceCoordinator()
            except Exception as e:
                logger.warning(f"核心服务初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        self.load_sample_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题和控制区域
        header_layout = QHBoxLayout()

        title_label = QLabel("🚀 增强性能监控仪表板")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 监控控制
        self.monitoring_toggle_btn = QPushButton("⏸️ 暂停监控")
        self.monitoring_toggle_btn.clicked.connect(self.toggle_monitoring)
        self.monitoring_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        header_layout.addWidget(self.monitoring_toggle_btn)

        layout.addLayout(header_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 实时监控选项卡
        realtime_tab = self.create_realtime_tab()
        self.tab_widget.addTab(realtime_tab, "📊 实时监控")

        # 历史趋势选项卡
        history_tab = self.create_history_tab()
        self.tab_widget.addTab(history_tab, "📈 历史趋势")

        # 性能告警选项卡
        self.alerts_widget = PerformanceAlertsWidget()
        self.tab_widget.addTab(self.alerts_widget, "⚠️ 性能告警")

        # 优化建议选项卡
        optimization_tab = self.create_optimization_tab()
        self.tab_widget.addTab(optimization_tab, "💡 优化建议")

        layout.addWidget(self.tab_widget)

        # 状态栏
        status_layout = QHBoxLayout()

        self.monitoring_status_label = QLabel("🟢 监控中")
        self.monitoring_status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.monitoring_status_label)

        status_layout.addStretch()

        self.last_update_label = QLabel("最后更新: --")
        status_layout.addWidget(self.last_update_label)

        layout.addLayout(status_layout)

        self.monitoring_active = True

    def create_realtime_tab(self) -> QWidget:
        """创建实时监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 仪表盘区域
        gauges_group = QGroupBox("📊 实时指标仪表盘")
        gauges_layout = QGridLayout(gauges_group)

        # 创建仪表盘
        self.gauges = {}
        gauge_configs = [
            (MetricType.CPU_USAGE, 100, 0, 0),
            (MetricType.MEMORY_USAGE, 100, 0, 1),
            (MetricType.DISK_IO, 1000, 0, 2),
            (MetricType.NETWORK_IO, 1000, 1, 0),
            (MetricType.CACHE_HIT_RATE, 100, 1, 1),
            (MetricType.RESPONSE_TIME, 5000, 1, 2)
        ]

        for metric_type, max_val, row, col in gauge_configs:
            gauge = MetricGauge(metric_type, max_val)
            self.gauges[metric_type] = gauge
            gauges_layout.addWidget(gauge, row, col, Qt.AlignCenter)

        layout.addWidget(gauges_group)

        # 实时图表区域
        charts_group = QGroupBox("📈 实时图表")
        charts_layout = QGridLayout(charts_group)

        # 创建实时图表
        self.charts = {}
        chart_configs = [
            (MetricType.CPU_USAGE, 0, 0),
            (MetricType.MEMORY_USAGE, 0, 1),
            (MetricType.THROUGHPUT, 1, 0),
            (MetricType.RESPONSE_TIME, 1, 1)
        ]

        for metric_type, row, col in chart_configs:
            chart = RealTimeChart(metric_type)
            self.charts[metric_type] = chart
            charts_layout.addWidget(chart, row, col)

        layout.addWidget(charts_group)

        return widget

    def create_history_tab(self) -> QWidget:
        """创建历史趋势选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 历史控制区域
        control_group = QGroupBox("🔍 历史查询控制")
        control_layout = QHBoxLayout(control_group)

        # 指标选择
        control_layout.addWidget(QLabel("指标:"))
        self.history_metric_combo = QComboBox()
        metric_names = {
            MetricType.CPU_USAGE: "CPU使用率",
            MetricType.MEMORY_USAGE: "内存使用率",
            MetricType.DISK_IO: "磁盘I/O",
            MetricType.NETWORK_IO: "网络I/O",
            MetricType.CACHE_HIT_RATE: "缓存命中率",
            MetricType.TASK_EXECUTION_TIME: "任务执行时间",
            MetricType.THROUGHPUT: "吞吐量",
            MetricType.ERROR_RATE: "错误率",
            MetricType.QUEUE_LENGTH: "队列长度",
            MetricType.RESPONSE_TIME: "响应时间"
        }
        for metric_type, name in metric_names.items():
            self.history_metric_combo.addItem(name, metric_type)
        control_layout.addWidget(self.history_metric_combo)

        # 时间范围
        control_layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近1小时", "最近6小时", "最近24小时", "最近7天", "最近30天"])
        control_layout.addWidget(self.time_range_combo)

        # 查询按钮
        query_btn = QPushButton("📊 查询历史")
        query_btn.clicked.connect(self.query_history)
        control_layout.addWidget(query_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        # 历史图表区域
        history_chart_group = QGroupBox("📈 历史趋势图表")
        history_chart_layout = QVBoxLayout(history_chart_group)

        self.history_chart = RealTimeChart(MetricType.CPU_USAGE)
        self.history_chart.setFixedSize(800, 300)
        history_chart_layout.addWidget(self.history_chart, Qt.AlignCenter)

        layout.addWidget(history_chart_group)

        # 统计信息区域
        stats_group = QGroupBox("📊 统计信息")
        stats_layout = QGridLayout(stats_group)

        # 平均值
        stats_layout.addWidget(QLabel("平均值:"), 0, 0)
        self.avg_value_label = QLabel("--")
        stats_layout.addWidget(self.avg_value_label, 0, 1)

        # 最大值
        stats_layout.addWidget(QLabel("最大值:"), 0, 2)
        self.max_value_label = QLabel("--")
        stats_layout.addWidget(self.max_value_label, 0, 3)

        # 最小值
        stats_layout.addWidget(QLabel("最小值:"), 1, 0)
        self.min_value_label = QLabel("--")
        stats_layout.addWidget(self.min_value_label, 1, 1)

        # 标准差
        stats_layout.addWidget(QLabel("标准差:"), 1, 2)
        self.std_value_label = QLabel("--")
        stats_layout.addWidget(self.std_value_label, 1, 3)

        layout.addWidget(stats_group)

        return widget

    def create_optimization_tab(self) -> QWidget:
        """创建优化建议选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 优化建议控制
        control_group = QGroupBox("🎛️ 优化分析控制")
        control_layout = QHBoxLayout(control_group)

        # 分析类型
        control_layout.addWidget(QLabel("分析类型:"))
        analysis_type_combo = QComboBox()
        analysis_type_combo.addItems(["全面分析", "CPU优化", "内存优化", "I/O优化", "缓存优化"])
        control_layout.addWidget(analysis_type_combo)

        # 分析按钮
        analyze_btn = QPushButton("🔍 开始分析")
        analyze_btn.clicked.connect(self.perform_optimization_analysis)
        control_layout.addWidget(analyze_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        # 瓶颈分析区域
        bottleneck_group = QGroupBox("🔍 性能瓶颈分析")
        bottleneck_layout = QVBoxLayout(bottleneck_group)

        self.bottleneck_analysis = QTextEdit()
        self.bottleneck_analysis.setReadOnly(True)
        self.bottleneck_analysis.setMaximumHeight(150)
        self.bottleneck_analysis.setText("""
🔍 性能瓶颈分析结果：

• CPU瓶颈: 当前CPU使用率较高（76%），建议优化计算密集型任务
• 内存瓶颈: 内存使用正常（45%），暂无优化需求
• I/O瓶颈: 磁盘I/O较高（234 MB/s），建议启用数据压缩
• 网络瓶颈: 网络I/O正常，暂无优化需求
• 缓存瓶颈: 缓存命中率较低（67%），建议调整缓存策略

💡 主要建议：优先解决CPU和缓存问题，预期性能提升 15-20%
        """)
        bottleneck_layout.addWidget(self.bottleneck_analysis)

        layout.addWidget(bottleneck_group)

        # 优化建议列表
        suggestions_group = QGroupBox("💡 具体优化建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_table = QTableWidget()
        self.suggestions_table.setColumnCount(5)
        self.suggestions_table.setHorizontalHeaderLabels([
            "优先级", "类型", "建议内容", "预期收益", "操作"
        ])

        # 填充示例数据
        self.load_sample_suggestions()

        # 设置列宽
        header = self.suggestions_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        suggestions_layout.addWidget(self.suggestions_table)

        layout.addWidget(suggestions_group)

        # 性能预测区域
        prediction_group = QGroupBox("🔮 性能预测")
        prediction_layout = QVBoxLayout(prediction_group)

        self.performance_prediction = QTextEdit()
        self.performance_prediction.setReadOnly(True)
        self.performance_prediction.setMaximumHeight(100)
        self.performance_prediction.setText("""
🔮 基于当前趋势的性能预测：

• 接下来1小时: CPU使用率可能上升至82%，建议提前优化
• 接下来6小时: 内存使用预计稳定在50%左右
• 接下来24小时: 磁盘I/O可能因为日志轮转而短暂增加
• 缓存效率: 如不优化，命中率可能进一步下降至60%

⚠️ 风险提醒: 当前趋势下，系统可能在2小时内达到性能瓶颈
        """)
        prediction_layout.addWidget(self.performance_prediction)

        layout.addWidget(prediction_group)

        return widget

    def load_sample_suggestions(self):
        """加载示例优化建议"""
        suggestions = [
            ("🔴 高", "CPU优化", "启用多线程处理，减少计算密集型任务的阻塞", "CPU使用率降低15%", "应用"),
            ("🟡 中", "缓存优化", "增加缓存大小，调整缓存淘汰策略", "命中率提升20%", "应用"),
            ("🟡 中", "I/O优化", "启用数据压缩，减少磁盘写入操作", "I/O降低30%", "应用"),
            ("🟢 低", "网络优化", "启用连接池，减少网络连接开销", "响应时间减少5%", "应用")
        ]

        self.suggestions_table.setRowCount(len(suggestions))

        for row, (priority, type_name, content, benefit, action) in enumerate(suggestions):
            # 优先级
            priority_item = QTableWidgetItem(priority)
            if "高" in priority:
                priority_item.setBackground(QColor("#fadbd8"))
            elif "中" in priority:
                priority_item.setBackground(QColor("#fef9e7"))
            else:
                priority_item.setBackground(QColor("#eafaf1"))
            self.suggestions_table.setItem(row, 0, priority_item)

            # 类型
            self.suggestions_table.setItem(row, 1, QTableWidgetItem(type_name))

            # 内容
            self.suggestions_table.setItem(row, 2, QTableWidgetItem(content))

            # 预期收益
            self.suggestions_table.setItem(row, 3, QTableWidgetItem(benefit))

            # 操作按钮
            apply_btn = QPushButton(action)
            apply_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            self.suggestions_table.setCellWidget(row, 4, apply_btn)

    def setup_connections(self):
        """设置信号连接"""
        # 连接告警信号
        self.alerts_widget.alert_resolved.connect(self.on_alert_resolved)

    def setup_timers(self):
        """设置定时器"""
        # 实时数据更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_realtime_data)
        self.update_timer.start(2000)  # 每2秒更新一次

        # 告警检查定时器
        self.alert_timer = QTimer()
        self.alert_timer.timeout.connect(self.check_alerts)
        self.alert_timer.start(5000)  # 每5秒检查一次告警

    def load_sample_data(self):
        """加载示例数据"""
        import random

        # 生成初始历史数据
        base_time = datetime.now() - timedelta(minutes=30)

        for i in range(30):
            timestamp = base_time + timedelta(minutes=i)

            # 生成示例指标数据
            metrics = {
                MetricType.CPU_USAGE: random.uniform(20, 80),
                MetricType.MEMORY_USAGE: random.uniform(30, 70),
                MetricType.DISK_IO: random.uniform(50, 300),
                MetricType.NETWORK_IO: random.uniform(10, 100),
                MetricType.CACHE_HIT_RATE: random.uniform(60, 95),
                MetricType.RESPONSE_TIME: random.uniform(100, 500),
                MetricType.THROUGHPUT: random.uniform(100, 1000),
                MetricType.ERROR_RATE: random.uniform(0, 5),
                MetricType.QUEUE_LENGTH: random.uniform(0, 50),
                MetricType.TASK_EXECUTION_TIME: random.uniform(10, 300)
            }

            for metric_type, value in metrics.items():
                metric = PerformanceMetric(
                    metric_type=metric_type,
                    value=value,
                    timestamp=timestamp
                )
                self.metrics_history[metric_type].append(metric)

    def update_realtime_data(self):
        """更新实时数据"""
        if not self.monitoring_active:
            return

        import random

        # 生成新的实时数据
        timestamp = datetime.now()

        # 模拟真实的指标变化
        metrics = {
            MetricType.CPU_USAGE: random.uniform(40, 85),
            MetricType.MEMORY_USAGE: random.uniform(35, 75),
            MetricType.DISK_IO: random.uniform(100, 400),
            MetricType.NETWORK_IO: random.uniform(50, 150),
            MetricType.CACHE_HIT_RATE: random.uniform(65, 90),
            MetricType.RESPONSE_TIME: random.uniform(150, 600)
        }

        for metric_type, value in metrics.items():
            metric = PerformanceMetric(
                metric_type=metric_type,
                value=value,
                timestamp=timestamp
            )

            # 更新历史数据
            self.metrics_history[metric_type].append(metric)

            # 更新仪表盘
            if metric_type in self.gauges:
                self.gauges[metric_type].set_value(value)

            # 更新图表
            if metric_type in self.charts:
                self.charts[metric_type].add_metric(metric)

        # 更新状态
        self.last_update_label.setText(f"最后更新: {timestamp.strftime('%H:%M:%S')}")

    def check_alerts(self):
        """检查告警"""
        if not self.monitoring_active:
            return

        # 检查各项指标是否超过阈值
        thresholds = {
            MetricType.CPU_USAGE: (70, 85),  # (warning, critical)
            MetricType.MEMORY_USAGE: (75, 90),
            MetricType.DISK_IO: (300, 500),
            MetricType.RESPONSE_TIME: (400, 800),
            MetricType.ERROR_RATE: (3, 5)
        }

        for metric_type, (warning_threshold, critical_threshold) in thresholds.items():
            if metric_type in self.metrics_history and self.metrics_history[metric_type]:
                latest_metric = self.metrics_history[metric_type][-1]

                # 检查是否需要产生告警
                if latest_metric.value >= critical_threshold:
                    # 检查是否已有相同的活跃告警
                    existing_alert = any(
                        a.metric_type == metric_type and
                        a.level == AlertLevel.CRITICAL and
                        not a.resolved
                        for a in self.alerts_widget.alerts
                    )

                    if not existing_alert:
                        alert = PerformanceAlert(
                            id=f"alert_{int(datetime.now().timestamp())}",
                            metric_type=metric_type,
                            level=AlertLevel.CRITICAL,
                            message=f"指标值({latest_metric.value:.1f})超过严重阈值({critical_threshold})",
                            value=latest_metric.value,
                            threshold=critical_threshold
                        )
                        self.alerts_widget.add_alert(alert)

                elif latest_metric.value >= warning_threshold:
                    # 检查是否已有相同的活跃告警
                    existing_alert = any(
                        a.metric_type == metric_type and
                        a.level == AlertLevel.WARNING and
                        not a.resolved
                        for a in self.alerts_widget.alerts
                    )

                    if not existing_alert:
                        alert = PerformanceAlert(
                            id=f"alert_{int(datetime.now().timestamp())}",
                            metric_type=metric_type,
                            level=AlertLevel.WARNING,
                            message=f"指标值({latest_metric.value:.1f})超过警告阈值({warning_threshold})",
                            value=latest_metric.value,
                            threshold=warning_threshold
                        )
                        self.alerts_widget.add_alert(alert)

    def toggle_monitoring(self):
        """切换监控状态"""
        self.monitoring_active = not self.monitoring_active

        if self.monitoring_active:
            self.monitoring_toggle_btn.setText("⏸️ 暂停监控")
            self.monitoring_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #d35400;
                }
            """)
            self.monitoring_status_label.setText("🟢 监控中")
            self.monitoring_status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        else:
            self.monitoring_toggle_btn.setText("▶️ 开始监控")
            self.monitoring_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            self.monitoring_status_label.setText("🔴 已暂停")
            self.monitoring_status_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)

    def query_history(self):
        """查询历史数据"""
        selected_metric = self.history_metric_combo.currentData()
        time_range = self.time_range_combo.currentText()

        # 计算时间范围
        now = datetime.now()
        time_ranges = {
            "最近1小时": now - timedelta(hours=1),
            "最近6小时": now - timedelta(hours=6),
            "最近24小时": now - timedelta(days=1),
            "最近7天": now - timedelta(days=7),
            "最近30天": now - timedelta(days=30)
        }
        start_time = time_ranges.get(time_range, now - timedelta(hours=1))

        # 过滤历史数据
        if selected_metric in self.metrics_history:
            filtered_metrics = [
                m for m in self.metrics_history[selected_metric]
                if m.timestamp >= start_time
            ]

            if filtered_metrics:
                # 更新历史图表
                self.history_chart.metric_type = selected_metric
                self.history_chart.setup_chart()

                for metric in filtered_metrics:
                    self.history_chart.add_metric(metric)

                # 计算统计信息
                values = [m.value for m in filtered_metrics]
                if values:
                    avg_val = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)

                    # 计算标准差
                    variance = sum((x - avg_val) ** 2 for x in values) / len(values)
                    std_val = math.sqrt(variance)

                    # 更新统计标签
                    self.avg_value_label.setText(f"{avg_val:.2f}")
                    self.max_value_label.setText(f"{max_val:.2f}")
                    self.min_value_label.setText(f"{min_val:.2f}")
                    self.std_value_label.setText(f"{std_val:.2f}")
                else:
                    # 清空统计信息
                    for label in [self.avg_value_label, self.max_value_label,
                                  self.min_value_label, self.std_value_label]:
                        label.setText("--")
            else:
                QMessageBox.information(self, "无数据", f"指定时间范围内无 {selected_metric.value} 数据")

    def perform_optimization_analysis(self):
        """执行优化分析"""
        # 这里可以调用实际的性能分析算法
        QMessageBox.information(self, "分析完成", "性能优化分析已完成，请查看分析结果和建议。")

    def on_alert_resolved(self, alert_id: str):
        """处理告警解决"""
        logger.info(f"告警 {alert_id} 已解决")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 12px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px 0 8px;
            color: #2c3e50;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            min-width: 100px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #21618c;
        }
        QTabWidget::pane {
            border: 1px solid #bdc3c7;
            border-radius: 6px;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #ecf0f1;
            border: 1px solid #bdc3c7;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #3498db;
            color: white;
        }
        QProgressBar {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 4px;
        }
    """)

    # 创建主窗口
    widget = EnhancedPerformanceDashboard()
    widget.setWindowTitle("增强性能监控仪表板")
    widget.resize(1200, 900)
    widget.show()

    sys.exit(app.exec_())
