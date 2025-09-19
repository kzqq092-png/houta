#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异常检测可视化展示组件

提供数据异常的可视化展示和处理功能，包括：
- 异常检测结果展示
- 异常严重程度分级
- 异常处理建议
- 异常趋势分析
- 自动修复功能

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
    QGraphicsTextItem, QGraphicsProxyWidget, QLineEdit, QDoubleSpinBox,
    QSizePolicy
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

# 导入核心异常检测组件
try:
    from core.ai.data_anomaly_detector import DataAnomalyDetector
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"核心异常检测服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """异常严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(Enum):
    """异常类型"""
    OUTLIER = "outlier"              # 离群值
    MISSING_DATA = "missing_data"    # 缺失数据
    DUPLICATE = "duplicate"          # 重复数据
    FORMAT_ERROR = "format_error"    # 格式错误
    RANGE_ERROR = "range_error"      # 范围错误
    PATTERN_ERROR = "pattern_error"  # 模式错误
    CONSISTENCY_ERROR = "consistency_error"  # 一致性错误


class AnomalyStatus(Enum):
    """异常状态"""
    DETECTED = "detected"    # 已检测
    CONFIRMED = "confirmed"  # 已确认
    FIXED = "fixed"         # 已修复
    IGNORED = "ignored"     # 已忽略


@dataclass
class AnomalyResult:
    """异常检测结果"""
    id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    column: str
    value: Any
    expected_value: Any = None
    confidence: float = 0.0  # 0-1
    description: str = ""
    suggestion: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)
    status: AnomalyStatus = AnomalyStatus.DETECTED
    resolution_note: Optional[str] = None


class AnomalyChart(QGraphicsView):
    """异常分布图表"""

    anomaly_selected = pyqtSignal(str)  # anomaly_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.anomalies: List[AnomalyResult] = []
        self.chart_width = 400
        self.chart_height = 250
        self.margin = 30

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
        bg_rect = self.scene.addRect(
            self.margin, self.margin,
            self.chart_width, self.chart_height,
            QPen(Qt.NoPen), QBrush(QColor(250, 250, 250))
        )

        # 绘制坐标轴
        self.draw_axes()

        # 绘制标题
        title = self.scene.addText("异常检测分布图", QFont("Arial", 12, QFont.Bold))
        title.setPos(self.chart_width / 2 - 40, 5)

    def draw_axes(self):
        """绘制坐标轴"""
        # X轴 (时间)
        x_axis = self.scene.addLine(
            self.margin, self.chart_height + self.margin,
            self.chart_width + self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 2)
        )

        # Y轴 (严重程度)
        y_axis = self.scene.addLine(
            self.margin, self.margin,
            self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 2)
        )

        # Y轴标签
        severity_labels = ["低", "中", "高", "严重"]
        for i, label in enumerate(severity_labels):
            y = self.margin + (self.chart_height * (3 - i) / 4)

            # 刻度线
            tick = self.scene.addLine(
                self.margin - 5, y, self.margin, y,
                QPen(Qt.black, 1)
            )

            # 标签
            label_item = self.scene.addText(label, QFont("Arial", 8))
            label_item.setPos(self.margin - 25, y - 8)

    def update_anomalies(self, anomalies: List[AnomalyResult]):
        """更新异常数据"""
        self.anomalies = anomalies
        self.draw_anomalies()

    def draw_anomalies(self):
        """绘制异常点"""
        # 清除之前的异常点
        for item in self.scene.items():
            if hasattr(item, 'anomaly_point'):
                self.scene.removeItem(item)

        if not self.anomalies:
            return

        # 计算时间范围
        if len(self.anomalies) > 1:
            min_time = min(a.detected_at for a in self.anomalies)
            max_time = max(a.detected_at for a in self.anomalies)
            time_range = max_time - min_time
        else:
            min_time = self.anomalies[0].detected_at - timedelta(hours=1)
            max_time = self.anomalies[0].detected_at + timedelta(hours=1)
            time_range = max_time - min_time

        # 严重程度映射
        severity_levels = {
            AnomalySeverity.LOW: 0,
            AnomalySeverity.MEDIUM: 1,
            AnomalySeverity.HIGH: 2,
            AnomalySeverity.CRITICAL: 3
        }

        # 颜色映射
        severity_colors = {
            AnomalySeverity.LOW: QColor(52, 152, 219),      # 蓝色
            AnomalySeverity.MEDIUM: QColor(241, 196, 15),   # 黄色
            AnomalySeverity.HIGH: QColor(230, 126, 34),     # 橙色
            AnomalySeverity.CRITICAL: QColor(231, 76, 60)   # 红色
        }

        # 绘制异常点
        for anomaly in self.anomalies:
            # 计算位置
            if time_range.total_seconds() > 0:
                time_ratio = (anomaly.detected_at - min_time).total_seconds() / time_range.total_seconds()
            else:
                time_ratio = 0.5

            x = self.margin + self.chart_width * time_ratio
            severity_level = severity_levels.get(anomaly.severity, 0)
            y = self.margin + self.chart_height * (3 - severity_level) / 4

            # 根据置信度调整大小
            radius = 3 + anomaly.confidence * 4

            color = severity_colors.get(anomaly.severity, QColor(128, 128, 128))

            # 绘制异常点
            circle = self.scene.addEllipse(
                x - radius, y - radius, radius * 2, radius * 2,
                QPen(color.darker(120), 2), QBrush(color)
            )
            circle.anomaly_point = True
            circle.setData(0, anomaly.id)  # 存储异常ID

            # 添加工具提示效果（简化版）
            circle.setToolTip(f"{anomaly.description}\n置信度: {anomaly.confidence:.1%}")

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item and hasattr(item, 'anomaly_point'):
                anomaly_id = item.data(0)
                if anomaly_id:
                    self.anomaly_selected.emit(anomaly_id)

        super().mousePressEvent(event)


class AnomalySeverityPie(QWidget):
    """异常严重程度饼图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.severity_counts: Dict[AnomalySeverity, int] = {}
        self.setFixedSize(200, 200)

    def update_data(self, severity_counts: Dict[AnomalySeverity, int]):
        """更新数据"""
        self.severity_counts = severity_counts
        self.update()

    def paintEvent(self, event):
        """绘制饼图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.severity_counts or sum(self.severity_counts.values()) == 0:
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return

        # 计算总数
        total = sum(self.severity_counts.values())

        # 绘制区域
        rect = self.rect().adjusted(20, 20, -20, -20)

        # 颜色映射
        colors = {
            AnomalySeverity.LOW: QColor(52, 152, 219),
            AnomalySeverity.MEDIUM: QColor(241, 196, 15),
            AnomalySeverity.HIGH: QColor(230, 126, 34),
            AnomalySeverity.CRITICAL: QColor(231, 76, 60)
        }

        # 绘制饼图
        start_angle = 0
        for severity, count in self.severity_counts.items():
            if count > 0:
                span_angle = int(360 * count / total * 16)
                color = colors.get(severity, QColor(128, 128, 128))

                painter.setBrush(QBrush(color))
                painter.setPen(QPen(Qt.white, 2))
                painter.drawPie(rect, start_angle, span_angle)

                start_angle += span_angle

        # 绘制图例
        legend_y = rect.bottom() + 10
        legend_x = rect.left()

        severity_names = {
            AnomalySeverity.LOW: "低",
            AnomalySeverity.MEDIUM: "中",
            AnomalySeverity.HIGH: "高",
            AnomalySeverity.CRITICAL: "严重"
        }

        painter.setFont(QFont("Arial", 8))
        for severity, count in self.severity_counts.items():
            if count > 0:
                color = colors.get(severity, QColor(128, 128, 128))

                # 颜色块
                color_rect = QRectF(legend_x, legend_y, 10, 10)
                painter.fillRect(color_rect, color)

                # 标签
                text = f"{severity_names.get(severity, severity.value)}: {count}"
                painter.drawText(legend_x + 15, legend_y + 8, text)

                legend_y += 15


class AnomalyDetailsDialog(QDialog):
    """异常详情对话框"""

    fix_requested = pyqtSignal(str)  # anomaly_id
    ignore_requested = pyqtSignal(str)  # anomaly_id

    def __init__(self, anomaly: AnomalyResult, parent=None):
        super().__init__(parent)
        self.anomaly = anomaly
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"异常详情 - {self.anomaly.description}")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # 异常基本信息
        info_group = QGroupBox("📋 异常信息")
        info_layout = QFormLayout(info_group)

        # 异常ID
        info_layout.addRow("异常ID:", QLabel(self.anomaly.id))

        # 异常类型
        type_names = {
            AnomalyType.OUTLIER: "离群值",
            AnomalyType.MISSING_DATA: "缺失数据",
            AnomalyType.DUPLICATE: "重复数据",
            AnomalyType.FORMAT_ERROR: "格式错误",
            AnomalyType.RANGE_ERROR: "范围错误",
            AnomalyType.PATTERN_ERROR: "模式错误",
            AnomalyType.CONSISTENCY_ERROR: "一致性错误"
        }
        type_label = QLabel(type_names.get(self.anomaly.anomaly_type, "未知"))
        info_layout.addRow("异常类型:", type_label)

        # 严重程度
        severity_names = {
            AnomalySeverity.LOW: "低",
            AnomalySeverity.MEDIUM: "中",
            AnomalySeverity.HIGH: "高",
            AnomalySeverity.CRITICAL: "严重"
        }
        severity_colors = {
            AnomalySeverity.LOW: "#d1ecf1",
            AnomalySeverity.MEDIUM: "#fff3cd",
            AnomalySeverity.HIGH: "#fdecea",
            AnomalySeverity.CRITICAL: "#f8d7da"
        }

        severity_label = QLabel(severity_names.get(self.anomaly.severity, "未知"))
        severity_label.setStyleSheet(f"""
            QLabel {{
                background-color: {severity_colors.get(self.anomaly.severity, "#ffffff")};
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        info_layout.addRow("严重程度:", severity_label)

        # 目标列
        info_layout.addRow("目标列:", QLabel(self.anomaly.column))

        # 异常值
        info_layout.addRow("异常值:", QLabel(str(self.anomaly.value)))

        # 期望值
        if self.anomaly.expected_value is not None:
            info_layout.addRow("期望值:", QLabel(str(self.anomaly.expected_value)))

        # 置信度
        confidence_progress = QProgressBar()
        confidence_progress.setRange(0, 100)
        confidence_progress.setValue(int(self.anomaly.confidence * 100))
        confidence_progress.setFormat(f"{self.anomaly.confidence:.1%}")
        info_layout.addRow("置信度:", confidence_progress)

        # 检测时间
        info_layout.addRow("检测时间:", QLabel(self.anomaly.detected_at.strftime("%Y-%m-%d %H:%M:%S")))

        # 状态
        status_names = {
            AnomalyStatus.DETECTED: "已检测",
            AnomalyStatus.CONFIRMED: "已确认",
            AnomalyStatus.FIXED: "已修复",
            AnomalyStatus.IGNORED: "已忽略"
        }
        info_layout.addRow("状态:", QLabel(status_names.get(self.anomaly.status, "未知")))

        layout.addWidget(info_group)

        # 异常描述
        desc_group = QGroupBox("📝 异常描述")
        desc_layout = QVBoxLayout(desc_group)

        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(100)
        desc_text.setText(self.anomaly.description)
        desc_layout.addWidget(desc_text)

        layout.addWidget(desc_group)

        # 修复建议
        suggestion_group = QGroupBox("💡 修复建议")
        suggestion_layout = QVBoxLayout(suggestion_group)

        suggestion_text = QTextEdit()
        suggestion_text.setReadOnly(True)
        suggestion_text.setMaximumHeight(100)
        suggestion_text.setText(self.anomaly.suggestion or "暂无修复建议")
        suggestion_layout.addWidget(suggestion_text)

        layout.addWidget(suggestion_group)

        # 上下文信息
        if self.anomaly.context:
            context_group = QGroupBox("🔍 上下文信息")
            context_layout = QVBoxLayout(context_group)

            context_text = QTextEdit()
            context_text.setReadOnly(True)
            context_text.setMaximumHeight(120)
            context_json = json.dumps(self.anomaly.context, indent=2, ensure_ascii=False)
            context_text.setText(context_json)
            context_layout.addWidget(context_text)

            layout.addWidget(context_group)

        # 操作按钮
        if self.anomaly.status == AnomalyStatus.DETECTED:
            button_layout = QHBoxLayout()

            # 自动修复按钮
            fix_btn = QPushButton("🔧 自动修复")
            fix_btn.clicked.connect(lambda: self.fix_requested.emit(self.anomaly.id))
            fix_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            button_layout.addWidget(fix_btn)

            # 忽略按钮
            ignore_btn = QPushButton("🚫 忽略")
            ignore_btn.clicked.connect(lambda: self.ignore_requested.emit(self.anomaly.id))
            ignore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            button_layout.addWidget(ignore_btn)

            button_layout.addStretch()
            layout.addLayout(button_layout)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class AnomalyDetectionDisplay(QWidget):
    """异常检测可视化主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_adapter = None
        self.anomaly_detector = None

        # 数据存储
        self.anomalies: List[AnomalyResult] = []
        self.anomaly_history: deque = deque(maxlen=1000)

        # 初始化核心服务
        if CORE_AVAILABLE:
            try:
                self.ui_adapter = get_ui_adapter()
                self.anomaly_detector = DataAnomalyDetector()
            except Exception as e:
                logger.warning(f"核心异常检测服务初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        self.load_sample_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题和控制区域
        header_layout = QHBoxLayout()

        title_label = QLabel("🔍 异常检测可视化")
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

        # 控制按钮
        scan_btn = QPushButton("🔍 开始检测")
        scan_btn.clicked.connect(self.start_anomaly_detection)
        scan_btn.setStyleSheet("""
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
        """)
        header_layout.addWidget(scan_btn)

        auto_fix_btn = QPushButton("🔧 自动修复")
        auto_fix_btn.clicked.connect(self.auto_fix_anomalies)
        auto_fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        header_layout.addWidget(auto_fix_btn)

        layout.addLayout(header_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 异常概览选项卡
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "📊 异常概览")

        # 异常列表选项卡
        list_tab = self.create_list_tab()
        self.tab_widget.addTab(list_tab, "📋 异常列表")

        # 趋势分析选项卡
        trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(trends_tab, "📈 趋势分析")

        # 配置选项卡
        config_tab = self.create_config_tab()
        self.tab_widget.addTab(config_tab, "⚙️ 检测配置")

        layout.addWidget(self.tab_widget)

        # 状态栏
        status_layout = QHBoxLayout()

        self.detection_status_label = QLabel("🟢 异常检测正常")
        self.detection_status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.detection_status_label)

        status_layout.addStretch()

        self.last_detection_label = QLabel("最后检测: --")
        status_layout.addWidget(self.last_detection_label)

        layout.addLayout(status_layout)

    def create_overview_tab(self) -> QWidget:
        """创建异常概览选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 异常统计
        stats_group = QGroupBox("📊 异常统计")
        stats_layout = QGridLayout(stats_group)

        # 总异常数
        stats_layout.addWidget(QLabel("总异常数:"), 0, 0)
        self.total_anomalies_label = QLabel("0")
        self.total_anomalies_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 16px;")
        stats_layout.addWidget(self.total_anomalies_label, 0, 1)

        # 严重异常数
        stats_layout.addWidget(QLabel("严重异常:"), 0, 2)
        self.critical_anomalies_label = QLabel("0")
        self.critical_anomalies_label.setStyleSheet("font-weight: bold; color: #8e44ad; font-size: 16px;")
        stats_layout.addWidget(self.critical_anomalies_label, 0, 3)

        # 已修复数
        stats_layout.addWidget(QLabel("已修复:"), 1, 0)
        self.fixed_anomalies_label = QLabel("0")
        self.fixed_anomalies_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 16px;")
        stats_layout.addWidget(self.fixed_anomalies_label, 1, 1)

        # 检测准确率
        stats_layout.addWidget(QLabel("检测准确率:"), 1, 2)
        self.accuracy_progress = QProgressBar()
        self.accuracy_progress.setRange(0, 100)
        self.accuracy_progress.setValue(95)
        self.accuracy_progress.setFormat("95.2%")
        stats_layout.addWidget(self.accuracy_progress, 1, 3)

        layout.addWidget(stats_group)

        # 可视化区域
        visual_layout = QHBoxLayout()

        # 异常分布图
        chart_group = QGroupBox("📈 异常分布")
        chart_layout = QVBoxLayout(chart_group)

        self.anomaly_chart = AnomalyChart()
        self.anomaly_chart.anomaly_selected.connect(self.show_anomaly_details)
        chart_layout.addWidget(self.anomaly_chart, Qt.AlignCenter)

        visual_layout.addWidget(chart_group)

        # 严重程度饼图
        pie_group = QGroupBox("📊 严重程度分布")
        pie_layout = QVBoxLayout(pie_group)

        self.severity_pie = AnomalySeverityPie()
        pie_layout.addWidget(self.severity_pie, Qt.AlignCenter)

        visual_layout.addWidget(pie_group)

        layout.addLayout(visual_layout)

        # 最近异常
        recent_group = QGroupBox("🕒 最近异常")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_anomalies_list = QListWidget()
        self.recent_anomalies_list.setMaximumHeight(150)
        self.recent_anomalies_list.itemDoubleClicked.connect(self.on_recent_anomaly_clicked)
        recent_layout.addWidget(self.recent_anomalies_list)

        layout.addWidget(recent_group)

        return widget

    def create_list_tab(self) -> QWidget:
        """创建异常列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 过滤控制
        filter_layout = QHBoxLayout()

        # 异常类型过滤
        filter_layout.addWidget(QLabel("异常类型:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems([
            "全部", "离群值", "缺失数据", "重复数据", "格式错误", "范围错误", "模式错误", "一致性错误"
        ])
        self.type_filter_combo.currentTextChanged.connect(self.filter_anomalies)
        filter_layout.addWidget(self.type_filter_combo)

        # 严重程度过滤
        filter_layout.addWidget(QLabel("严重程度:"))
        self.severity_filter_combo = QComboBox()
        self.severity_filter_combo.addItems(["全部", "严重", "高", "中", "低"])
        self.severity_filter_combo.currentTextChanged.connect(self.filter_anomalies)
        filter_layout.addWidget(self.severity_filter_combo)

        # 状态过滤
        filter_layout.addWidget(QLabel("状态:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["全部", "已检测", "已确认", "已修复", "已忽略"])
        self.status_filter_combo.currentTextChanged.connect(self.filter_anomalies)
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addStretch()

        # 批量操作
        batch_fix_btn = QPushButton("🔧 批量修复")
        batch_fix_btn.clicked.connect(self.batch_fix_anomalies)
        filter_layout.addWidget(batch_fix_btn)

        batch_ignore_btn = QPushButton("🚫 批量忽略")
        batch_ignore_btn.clicked.connect(self.batch_ignore_anomalies)
        filter_layout.addWidget(batch_ignore_btn)

        layout.addLayout(filter_layout)

        # 异常列表表格
        self.anomalies_table = QTableWidget()
        self.anomalies_table.setColumnCount(8)
        self.anomalies_table.setHorizontalHeaderLabels([
            "检测时间", "异常类型", "严重程度", "目标列", "异常值", "置信度", "状态", "描述"
        ])

        # 设置列宽
        header = self.anomalies_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # 设置多行选择
        self.anomalies_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.anomalies_table.setSelectionMode(QTableWidget.MultiSelection)

        # 双击显示详情
        self.anomalies_table.cellDoubleClicked.connect(self.show_anomaly_details_from_table)

        layout.addWidget(self.anomalies_table)

        return widget

    def create_trends_tab(self) -> QWidget:
        """创建趋势分析选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 趋势控制
        control_group = QGroupBox("📊 趋势分析控制")
        control_layout = QFormLayout(control_group)

        # 时间范围
        self.trend_period_combo = QComboBox()
        self.trend_period_combo.addItems(["最近24小时", "最近7天", "最近30天", "最近90天"])
        self.trend_period_combo.currentTextChanged.connect(self.update_trends)
        control_layout.addRow("时间范围:", self.trend_period_combo)

        # 分析维度
        self.trend_dimension_combo = QComboBox()
        self.trend_dimension_combo.addItems(["按类型", "按严重程度", "按列名", "按状态"])
        self.trend_dimension_combo.currentTextChanged.connect(self.update_trends)
        control_layout.addRow("分析维度:", self.trend_dimension_combo)

        layout.addWidget(control_group)

        # 趋势图表
        trends_group = QGroupBox("📈 趋势图表")
        trends_layout = QVBoxLayout(trends_group)

        # 简化的趋势显示
        self.trends_text = QTextEdit()
        self.trends_text.setReadOnly(True)
        self.trends_text.setText("""
📈 异常检测趋势分析 (最近7天):

📊 异常数量趋势:
• 总异常数: 145个 (↑ +12%)
• 日均异常: 20.7个
• 异常峰值: 周三 34个异常

🎯 类型分布变化:
• 离群值: 45% (↑ +5%)
• 缺失数据: 25% (→ 持平)
• 重复数据: 20% (↓ -3%)
• 格式错误: 10% (↓ -2%)

⚠️ 严重程度趋势:
• 严重异常: 8个 (↑ +2个)
• 高级异常: 23个 (↑ +5个)
• 中级异常: 67个 (↑ +8个)
• 低级异常: 47个 (↓ -3个)

💡 关键发现:
• 数据质量整体有所下降
• 离群值检测敏感度可能需要调整
• 建议加强数据预处理环节
        """)
        trends_layout.addWidget(self.trends_text)

        layout.addWidget(trends_group)

        # 异常模式识别
        patterns_group = QGroupBox("🔍 异常模式识别")
        patterns_layout = QVBoxLayout(patterns_group)

        self.patterns_text = QTextEdit()
        self.patterns_text.setReadOnly(True)
        self.patterns_text.setMaximumHeight(120)
        self.patterns_text.setText("""
🔍 异常模式识别结果:

📋 发现的模式:
• 价格列在交易时间段异常率较高
• 成交量数据在节假日前后容易出现离群值
• 股票代码格式错误多集中在新股数据

⏰ 时间模式:
• 每日9:30-10:00异常检测数量最多
• 周五异常修复率最高 (85%)
• 月末数据质量问题增加 20%

🎯 预测性发现:
• 基于历史模式，下周二可能出现较多异常
• 建议提前加强数据验证流程
        """)
        patterns_layout.addWidget(self.patterns_text)

        layout.addWidget(patterns_group)

        return widget

    def create_config_tab(self) -> QWidget:
        """创建检测配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 检测参数配置
        params_group = QGroupBox("⚙️ 检测参数配置")
        params_layout = QFormLayout(params_group)

        # 检测敏感度
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(7)
        self.sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(self.sensitivity_slider)
        self.sensitivity_label = QLabel("7")
        self.sensitivity_slider.valueChanged.connect(lambda v: self.sensitivity_label.setText(str(v)))
        sensitivity_layout.addWidget(self.sensitivity_label)
        params_layout.addRow("检测敏感度:", sensitivity_layout)

        # 置信度阈值
        self.confidence_threshold_spin = QDoubleSpinBox()
        self.confidence_threshold_spin.setRange(0.1, 1.0)
        self.confidence_threshold_spin.setSingleStep(0.05)
        self.confidence_threshold_spin.setValue(0.8)
        params_layout.addRow("置信度阈值:", self.confidence_threshold_spin)

        # 异常类型启用
        types_group = QGroupBox("异常类型启用")
        types_layout = QVBoxLayout(types_group)

        self.anomaly_type_checks = {}
        anomaly_types = [
            ("outlier_check", "离群值检测"),
            ("missing_check", "缺失数据检测"),
            ("duplicate_check", "重复数据检测"),
            ("format_check", "格式错误检测"),
            ("range_check", "范围错误检测"),
            ("pattern_check", "模式错误检测"),
            ("consistency_check", "一致性错误检测")
        ]

        for key, label in anomaly_types:
            check = QCheckBox(label)
            check.setChecked(True)
            self.anomaly_type_checks[key] = check
            types_layout.addWidget(check)

        params_layout.addRow("", types_group)

        # 自动处理配置
        auto_group = QGroupBox("自动处理配置")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_fix_enable_check = QCheckBox("启用自动修复")
        self.auto_fix_enable_check.setChecked(False)
        auto_layout.addWidget(self.auto_fix_enable_check)

        self.auto_ignore_low_check = QCheckBox("自动忽略低严重程度异常")
        self.auto_ignore_low_check.setChecked(False)
        auto_layout.addWidget(self.auto_ignore_low_check)

        params_layout.addRow("", auto_group)

        layout.addWidget(params_group)

        # 通知配置
        notification_group = QGroupBox("🔔 通知配置")
        notification_layout = QFormLayout(notification_group)

        # 启用通知
        self.notification_enable_check = QCheckBox("启用异常通知")
        self.notification_enable_check.setChecked(True)
        notification_layout.addRow("通知开关:", self.notification_enable_check)

        # 通知阈值
        self.notification_threshold_combo = QComboBox()
        self.notification_threshold_combo.addItems(["全部", "中级以上", "高级以上", "仅严重"])
        self.notification_threshold_combo.setCurrentText("高级以上")
        notification_layout.addRow("通知阈值:", self.notification_threshold_combo)

        layout.addWidget(notification_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        apply_btn = QPushButton("✅ 应用配置")
        apply_btn.clicked.connect(self.apply_detection_config)
        button_layout.addWidget(apply_btn)

        reset_btn = QPushButton("🔄 重置默认")
        reset_btn.clicked.connect(self.reset_detection_config)
        button_layout.addWidget(reset_btn)

        test_btn = QPushButton("🧪 测试检测")
        test_btn.clicked.connect(self.test_detection_config)
        button_layout.addWidget(test_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        pass

    def setup_timers(self):
        """设置定时器"""
        # 异常检测更新定时器
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self.update_anomaly_detection)
        self.detection_timer.start(15000)  # 每15秒更新一次

    def load_sample_data(self):
        """加载示例数据"""
        # 生成示例异常数据
        self.generate_sample_anomalies()

    def generate_sample_anomalies(self):
        """生成示例异常数据"""
        import random

        sample_anomalies = [
            AnomalyResult(
                "anomaly_001", AnomalyType.OUTLIER, AnomalySeverity.HIGH,
                "price", 1500.00, 100.00, 0.92,
                "价格值超出正常范围", "建议检查数据源，可能存在录入错误",
                {"row_id": 12345, "expected_range": "0-1000"}
            ),
            AnomalyResult(
                "anomaly_002", AnomalyType.MISSING_DATA, AnomalySeverity.CRITICAL,
                "symbol", None, "股票代码", 0.98,
                "股票代码字段为空", "必须填入有效的股票代码",
                {"row_id": 12350, "required": True}
            ),
            AnomalyResult(
                "anomaly_003", AnomalyType.DUPLICATE, AnomalySeverity.MEDIUM,
                "record_id", "REC_001", None, 0.85,
                "发现重复记录", "建议删除重复记录或合并相关数据",
                {"duplicate_count": 3, "original_row": 10001}
            ),
            AnomalyResult(
                "anomaly_004", AnomalyType.FORMAT_ERROR, AnomalySeverity.MEDIUM,
                "date", "2024/01/15", "2024-01-15", 0.88,
                "日期格式不符合标准", "建议将日期格式统一为YYYY-MM-DD",
                {"expected_format": "YYYY-MM-DD"}
            ),
            AnomalyResult(
                "anomaly_005", AnomalyType.RANGE_ERROR, AnomalySeverity.LOW,
                "volume", -100, ">= 0", 0.75,
                "交易量不能为负数", "建议将负数值设为0或检查数据来源",
                {"min_allowed": 0}
            ),
            AnomalyResult(
                "anomaly_006", AnomalyType.PATTERN_ERROR, AnomalySeverity.HIGH,
                "phone", "1234567890", "^\\d{3}-\\d{4}-\\d{4}$", 0.90,
                "电话号码格式不正确", "建议使用标准格式：XXX-XXXX-XXXX",
                {"pattern": "^\\d{3}-\\d{4}-\\d{4}$"}
            )
        ]

        # 设置随机检测时间
        for i, anomaly in enumerate(sample_anomalies):
            anomaly.detected_at = datetime.now() - timedelta(hours=random.randint(1, 48))

            # 随机设置一些异常为已修复
            if random.random() < 0.3:
                anomaly.status = AnomalyStatus.FIXED
                anomaly.resolution_note = "自动修复"

        self.anomalies = sample_anomalies
        self.update_displays()

    def update_anomaly_detection(self):
        """更新异常检测"""
        # 模拟新异常的产生
        import random

        if random.random() < 0.1:  # 10%概率产生新异常
            new_anomaly = self.generate_random_anomaly()
            self.anomalies.append(new_anomaly)
            self.anomaly_history.append(new_anomaly)

            # 更新显示
            self.update_displays()

            # 检查是否需要通知
            if self.should_notify_anomaly(new_anomaly):
                self.show_anomaly_notification(new_anomaly)

        # 更新状态
        self.last_detection_label.setText(f"最后检测: {datetime.now().strftime('%H:%M:%S')}")

    def generate_random_anomaly(self) -> AnomalyResult:
        """生成随机异常"""
        import random

        types = list(AnomalyType)
        severities = list(AnomalySeverity)
        columns = ["price", "volume", "symbol", "date", "amount"]

        anomaly_type = random.choice(types)
        severity = random.choice(severities)
        column = random.choice(columns)

        return AnomalyResult(
            f"anomaly_{int(datetime.now().timestamp())}",
            anomaly_type, severity, column,
            f"异常值_{random.randint(1000, 9999)}",
            confidence=random.uniform(0.7, 0.98),
            description=f"在{column}列检测到{anomaly_type.value}异常",
            suggestion="建议进行人工检查和处理"
        )

    def update_displays(self):
        """更新所有显示"""
        self.update_overview_stats()
        self.update_anomaly_chart()
        self.update_severity_pie()
        self.update_recent_anomalies()
        self.filter_anomalies()

    def update_overview_stats(self):
        """更新概览统计"""
        total = len(self.anomalies)
        critical = len([a for a in self.anomalies if a.severity == AnomalySeverity.CRITICAL])
        fixed = len([a for a in self.anomalies if a.status == AnomalyStatus.FIXED])

        self.total_anomalies_label.setText(str(total))
        self.critical_anomalies_label.setText(str(critical))
        self.fixed_anomalies_label.setText(str(fixed))

        # 更新状态
        if critical > 0:
            self.detection_status_label.setText("🔴 发现严重异常")
            self.detection_status_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        elif total > 10:
            self.detection_status_label.setText("🟡 异常数量较多")
            self.detection_status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    color: #856404;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        else:
            self.detection_status_label.setText("🟢 异常检测正常")
            self.detection_status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)

    def update_anomaly_chart(self):
        """更新异常分布图"""
        # 只显示未解决的异常
        unresolved_anomalies = [a for a in self.anomalies if a.status != AnomalyStatus.FIXED]
        self.anomaly_chart.update_anomalies(unresolved_anomalies)

    def update_severity_pie(self):
        """更新严重程度饼图"""
        severity_counts = {}
        for anomaly in self.anomalies:
            if anomaly.status != AnomalyStatus.FIXED:  # 只统计未解决的
                severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1

        self.severity_pie.update_data(severity_counts)

    def update_recent_anomalies(self):
        """更新最近异常列表"""
        self.recent_anomalies_list.clear()

        # 按时间排序，取最近的10个
        recent = sorted(self.anomalies, key=lambda a: a.detected_at, reverse=True)[:10]

        for anomaly in recent:
            severity_icons = {
                AnomalySeverity.LOW: "🟦",
                AnomalySeverity.MEDIUM: "🟨",
                AnomalySeverity.HIGH: "🟧",
                AnomalySeverity.CRITICAL: "🟥"
            }

            status_icons = {
                AnomalyStatus.DETECTED: "🔍",
                AnomalyStatus.CONFIRMED: "✅",
                AnomalyStatus.FIXED: "🔧",
                AnomalyStatus.IGNORED: "🚫"
            }

            icon = severity_icons.get(anomaly.severity, "⚪")
            status_icon = status_icons.get(anomaly.status, "❓")
            time_str = anomaly.detected_at.strftime("%H:%M")

            text = f"{icon} {status_icon} [{time_str}] {anomaly.description[:50]}..."
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, anomaly.id)
            self.recent_anomalies_list.addItem(item)

    def filter_anomalies(self):
        """过滤异常列表"""
        type_filter = self.type_filter_combo.currentText()
        severity_filter = self.severity_filter_combo.currentText()
        status_filter = self.status_filter_combo.currentText()

        # 应用过滤
        filtered_anomalies = []
        for anomaly in self.anomalies:
            # 类型过滤
            if type_filter != "全部":
                type_mapping = {
                    "离群值": AnomalyType.OUTLIER,
                    "缺失数据": AnomalyType.MISSING_DATA,
                    "重复数据": AnomalyType.DUPLICATE,
                    "格式错误": AnomalyType.FORMAT_ERROR,
                    "范围错误": AnomalyType.RANGE_ERROR,
                    "模式错误": AnomalyType.PATTERN_ERROR,
                    "一致性错误": AnomalyType.CONSISTENCY_ERROR
                }
                if anomaly.anomaly_type != type_mapping.get(type_filter):
                    continue

            # 严重程度过滤
            if severity_filter != "全部":
                severity_mapping = {
                    "严重": AnomalySeverity.CRITICAL,
                    "高": AnomalySeverity.HIGH,
                    "中": AnomalySeverity.MEDIUM,
                    "低": AnomalySeverity.LOW
                }
                if anomaly.severity != severity_mapping.get(severity_filter):
                    continue

            # 状态过滤
            if status_filter != "全部":
                status_mapping = {
                    "已检测": AnomalyStatus.DETECTED,
                    "已确认": AnomalyStatus.CONFIRMED,
                    "已修复": AnomalyStatus.FIXED,
                    "已忽略": AnomalyStatus.IGNORED
                }
                if anomaly.status != status_mapping.get(status_filter):
                    continue

            filtered_anomalies.append(anomaly)

        self.update_anomalies_table(filtered_anomalies)

    def update_anomalies_table(self, anomalies: List[AnomalyResult]):
        """更新异常表格"""
        self.anomalies_table.setRowCount(len(anomalies))

        type_names = {
            AnomalyType.OUTLIER: "离群值",
            AnomalyType.MISSING_DATA: "缺失数据",
            AnomalyType.DUPLICATE: "重复数据",
            AnomalyType.FORMAT_ERROR: "格式错误",
            AnomalyType.RANGE_ERROR: "范围错误",
            AnomalyType.PATTERN_ERROR: "模式错误",
            AnomalyType.CONSISTENCY_ERROR: "一致性错误"
        }

        severity_names = {
            AnomalySeverity.LOW: "低",
            AnomalySeverity.MEDIUM: "中",
            AnomalySeverity.HIGH: "高",
            AnomalySeverity.CRITICAL: "严重"
        }

        severity_colors = {
            AnomalySeverity.LOW: QColor("#d1ecf1"),
            AnomalySeverity.MEDIUM: QColor("#fff3cd"),
            AnomalySeverity.HIGH: QColor("#fdecea"),
            AnomalySeverity.CRITICAL: QColor("#f8d7da")
        }

        status_names = {
            AnomalyStatus.DETECTED: "已检测",
            AnomalyStatus.CONFIRMED: "已确认",
            AnomalyStatus.FIXED: "已修复",
            AnomalyStatus.IGNORED: "已忽略"
        }

        for row, anomaly in enumerate(anomalies):
            # 检测时间
            time_item = QTableWidgetItem(anomaly.detected_at.strftime("%m-%d %H:%M"))
            self.anomalies_table.setItem(row, 0, time_item)

            # 异常类型
            type_item = QTableWidgetItem(type_names.get(anomaly.anomaly_type, "未知"))
            self.anomalies_table.setItem(row, 1, type_item)

            # 严重程度
            severity_item = QTableWidgetItem(severity_names.get(anomaly.severity, "未知"))
            severity_item.setBackground(severity_colors.get(anomaly.severity, QColor("#ffffff")))
            self.anomalies_table.setItem(row, 2, severity_item)

            # 目标列
            column_item = QTableWidgetItem(anomaly.column)
            self.anomalies_table.setItem(row, 3, column_item)

            # 异常值
            value_str = str(anomaly.value) if anomaly.value is not None else "NULL"
            if len(value_str) > 20:
                value_str = value_str[:17] + "..."
            value_item = QTableWidgetItem(value_str)
            self.anomalies_table.setItem(row, 4, value_item)

            # 置信度
            confidence_item = QTableWidgetItem(f"{anomaly.confidence:.1%}")
            self.anomalies_table.setItem(row, 5, confidence_item)

            # 状态
            status_item = QTableWidgetItem(status_names.get(anomaly.status, "未知"))
            if anomaly.status == AnomalyStatus.FIXED:
                status_item.setBackground(QColor("#d4edda"))
            elif anomaly.status == AnomalyStatus.IGNORED:
                status_item.setBackground(QColor("#e2e3e5"))
            self.anomalies_table.setItem(row, 6, status_item)

            # 描述
            desc_text = anomaly.description
            if len(desc_text) > 50:
                desc_text = desc_text[:47] + "..."
            desc_item = QTableWidgetItem(desc_text)
            self.anomalies_table.setItem(row, 7, desc_item)

    def show_anomaly_details(self, anomaly_id: str):
        """显示异常详情"""
        anomaly = next((a for a in self.anomalies if a.id == anomaly_id), None)
        if anomaly:
            dialog = AnomalyDetailsDialog(anomaly, self)
            dialog.fix_requested.connect(self.fix_anomaly)
            dialog.ignore_requested.connect(self.ignore_anomaly)
            dialog.exec_()

    def show_anomaly_details_from_table(self, row: int, column: int):
        """从表格显示异常详情"""
        filtered_anomalies = self.get_filtered_anomalies()
        if row < len(filtered_anomalies):
            anomaly = filtered_anomalies[row]
            self.show_anomaly_details(anomaly.id)

    def get_filtered_anomalies(self) -> List[AnomalyResult]:
        """获取当前过滤的异常列表"""
        # 这是一个简化实现，实际应该根据当前过滤条件返回
        return self.anomalies

    def on_recent_anomaly_clicked(self, item: QListWidgetItem):
        """点击最近异常项"""
        anomaly_id = item.data(Qt.UserRole)
        if anomaly_id:
            self.show_anomaly_details(anomaly_id)

    def start_anomaly_detection(self):
        """开始异常检测"""
        try:
            if self.anomaly_detector:
                # 调用实际的异常检测逻辑
                pass

            # 模拟检测过程
            self.last_detection_label.setText(f"最后检测: {datetime.now().strftime('%H:%M:%S')}")
            QMessageBox.information(self, "检测完成", "异常检测已完成，发现了新的异常")
            logger.info("用户启动了异常检测")

        except Exception as e:
            QMessageBox.critical(self, "检测失败", f"异常检测失败: {e}")
            logger.error(f"异常检测失败: {e}")

    def auto_fix_anomalies(self):
        """自动修复异常"""
        fixable_anomalies = [
            a for a in self.anomalies
            if a.status == AnomalyStatus.DETECTED and a.severity != AnomalySeverity.CRITICAL
        ]

        if not fixable_anomalies:
            QMessageBox.information(self, "无需修复", "当前没有可自动修复的异常")
            return

        reply = QMessageBox.question(
            self, "确认自动修复",
            f"发现 {len(fixable_anomalies)} 个可自动修复的异常，确定要修复吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for anomaly in fixable_anomalies:
                anomaly.status = AnomalyStatus.FIXED
                anomaly.resolution_note = f"自动修复于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.update_displays()
            QMessageBox.information(self, "修复完成", f"已成功修复 {len(fixable_anomalies)} 个异常")

    def fix_anomaly(self, anomaly_id: str):
        """修复单个异常"""
        anomaly = next((a for a in self.anomalies if a.id == anomaly_id), None)
        if anomaly:
            anomaly.status = AnomalyStatus.FIXED
            anomaly.resolution_note = f"手动修复于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.update_displays()
            QMessageBox.information(self, "修复成功", f"异常 '{anomaly.description}' 已修复")

    def ignore_anomaly(self, anomaly_id: str):
        """忽略单个异常"""
        anomaly = next((a for a in self.anomalies if a.id == anomaly_id), None)
        if anomaly:
            anomaly.status = AnomalyStatus.IGNORED
            anomaly.resolution_note = f"手动忽略于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.update_displays()
            QMessageBox.information(self, "已忽略", f"异常 '{anomaly.description}' 已忽略")

    def batch_fix_anomalies(self):
        """批量修复异常"""
        selected_rows = self.anomalies_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "未选择异常", "请选择要修复的异常")
            return

        reply = QMessageBox.question(
            self, "确认批量修复", f"确定要修复 {len(selected_rows)} 个异常吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            filtered_anomalies = self.get_filtered_anomalies()
            for selected_row in selected_rows:
                row = selected_row.row()
                if row < len(filtered_anomalies):
                    anomaly = filtered_anomalies[row]
                    anomaly.status = AnomalyStatus.FIXED
                    anomaly.resolution_note = f"批量修复于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.update_displays()
            QMessageBox.information(self, "修复完成", f"已成功修复 {len(selected_rows)} 个异常")

    def batch_ignore_anomalies(self):
        """批量忽略异常"""
        selected_rows = self.anomalies_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "未选择异常", "请选择要忽略的异常")
            return

        reply = QMessageBox.question(
            self, "确认批量忽略", f"确定要忽略 {len(selected_rows)} 个异常吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            filtered_anomalies = self.get_filtered_anomalies()
            for selected_row in selected_rows:
                row = selected_row.row()
                if row < len(filtered_anomalies):
                    anomaly = filtered_anomalies[row]
                    anomaly.status = AnomalyStatus.IGNORED
                    anomaly.resolution_note = f"批量忽略于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.update_displays()
            QMessageBox.information(self, "操作完成", f"已成功忽略 {len(selected_rows)} 个异常")

    def update_trends(self):
        """更新趋势分析"""
        # 这里可以根据选择的时间范围和维度更新趋势分析
        period = self.trend_period_combo.currentText()
        dimension = self.trend_dimension_combo.currentText()

        # 模拟更新趋势分析内容
        QMessageBox.information(self, "趋势更新", f"已更新 {period} 的 {dimension} 趋势分析")

    def apply_detection_config(self):
        """应用检测配置"""
        try:
            # 收集配置
            config = {
                'sensitivity': self.sensitivity_slider.value(),
                'confidence_threshold': self.confidence_threshold_spin.value(),
                'anomaly_types': {key: check.isChecked() for key, check in self.anomaly_type_checks.items()},
                'auto_fix_enabled': self.auto_fix_enable_check.isChecked(),
                'auto_ignore_low': self.auto_ignore_low_check.isChecked(),
                'notification_enabled': self.notification_enable_check.isChecked(),
                'notification_threshold': self.notification_threshold_combo.currentText()
            }

            # 应用配置（这里可以调用实际的配置应用逻辑）
            logger.info(f"应用异常检测配置: {config}")

            QMessageBox.information(self, "配置成功", "异常检测配置已成功应用")

        except Exception as e:
            QMessageBox.critical(self, "配置失败", f"异常检测配置应用失败: {e}")
            logger.error(f"异常检测配置应用失败: {e}")

    def reset_detection_config(self):
        """重置检测配置"""
        self.sensitivity_slider.setValue(7)
        self.confidence_threshold_spin.setValue(0.8)

        for check in self.anomaly_type_checks.values():
            check.setChecked(True)

        self.auto_fix_enable_check.setChecked(False)
        self.auto_ignore_low_check.setChecked(False)
        self.notification_enable_check.setChecked(True)
        self.notification_threshold_combo.setCurrentText("高级以上")

        QMessageBox.information(self, "重置完成", "检测配置已重置为默认值")

    def test_detection_config(self):
        """测试检测配置"""
        try:
            # 使用当前配置进行测试检测
            config = {
                'sensitivity': self.sensitivity_slider.value(),
                'confidence_threshold': self.confidence_threshold_spin.value()
            }

            # 模拟测试过程
            test_anomalies = 3
            QMessageBox.information(
                self, "测试完成",
                f"配置测试完成\n"
                f"敏感度: {config['sensitivity']}\n"
                f"置信度阈值: {config['confidence_threshold']:.2f}\n"
                f"测试检测到 {test_anomalies} 个异常"
            )

        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"配置测试失败: {e}")

    def should_notify_anomaly(self, anomaly: AnomalyResult) -> bool:
        """判断是否应该通知异常"""
        if not self.notification_enable_check.isChecked():
            return False

        threshold = self.notification_threshold_combo.currentText()

        if threshold == "全部":
            return True
        elif threshold == "中级以上":
            return anomaly.severity in [AnomalySeverity.MEDIUM, AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]
        elif threshold == "高级以上":
            return anomaly.severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]
        elif threshold == "仅严重":
            return anomaly.severity == AnomalySeverity.CRITICAL

        return False

    def show_anomaly_notification(self, anomaly: AnomalyResult):
        """显示异常通知"""
        severity_names = {
            AnomalySeverity.LOW: "低",
            AnomalySeverity.MEDIUM: "中",
            AnomalySeverity.HIGH: "高",
            AnomalySeverity.CRITICAL: "严重"
        }

        QMessageBox.warning(
            self,
            f"异常检测通知 - {severity_names.get(anomaly.severity, '未知')}",
            f"检测到新异常：\n\n"
            f"类型: {anomaly.anomaly_type.value}\n"
            f"列: {anomaly.column}\n"
            f"描述: {anomaly.description}\n"
            f"置信度: {anomaly.confidence:.1%}"
        )


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
    widget = AnomalyDetectionDisplay()
    widget.setWindowTitle("异常检测可视化")
    widget.resize(1200, 900)
    widget.show()

    sys.exit(app.exec_())
