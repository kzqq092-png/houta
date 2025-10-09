#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI预测结果展示组件

提供AI预测结果的可视化展示功能，包括：
- 预测结果图表展示
- 置信度可视化
- 历史趋势分析
- 预测准确性统计
- 实时预测监控

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque

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
    QDial, QCalendarWidget, QGraphicsEllipseItem, QGraphicsLineItem
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

# 导入核心AI服务
try:
    from core.services.ai_prediction_service import AIPredictionService
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"AI核心服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class PredictionType(Enum):
    """预测类型"""
    EXECUTION_TIME = "execution_time"
    PERFORMANCE = "performance"
    RESOURCE_USAGE = "resource_usage"
    ANOMALY_DETECTION = "anomaly_detection"
    OPTIMIZATION = "optimization"


@dataclass
class PredictionData:
    """预测数据"""
    id: str
    prediction_type: PredictionType
    timestamp: datetime
    input_features: Dict[str, Any]
    predicted_value: Any
    confidence: float
    actual_value: Optional[Any] = None
    error: Optional[float] = None
    model_version: str = "1.0"
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfidenceIndicator(QWidget):
    """置信度指示器组件"""

    def __init__(self, confidence: float = 0.0, parent=None):
        super().__init__(parent)
        self.confidence = confidence
        self.setFixedSize(100, 20)

    def set_confidence(self, confidence: float):
        """设置置信度"""
        self.confidence = max(0.0, min(1.0, confidence))
        self.update()

    def paintEvent(self, event):
        """绘制置信度指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor(240, 240, 240))

        # 置信度条
        confidence_width = int(rect.width() * self.confidence)
        confidence_rect = QRectF(rect.x(), rect.y(), confidence_width, rect.height())

        # 根据置信度设置颜色
        if self.confidence >= 0.8:
            color = QColor(46, 204, 113)  # 绿色
        elif self.confidence >= 0.6:
            color = QColor(241, 196, 15)  # 黄色
        else:
            color = QColor(231, 76, 60)   # 红色

        painter.fillRect(confidence_rect, color)

        # 边框
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(rect)

        # 文本
        painter.setPen(QPen(Qt.black))
        painter.drawText(rect, Qt.AlignCenter, f"{self.confidence:.1%}")


class PredictionChart(QGraphicsView):
    """预测图表组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # 数据存储
        self.predictions: deque = deque(maxlen=50)  # 最多存储50个数据点
        self.chart_width = 400
        self.chart_height = 200
        self.margin = 30

        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setup_chart()

    def setup_chart(self):
        """设置图表"""
        self.scene.clear()

        # 设置场景大小
        self.scene.setSceneRect(0, 0, self.chart_width + 2 * self.margin,
                                self.chart_height + 2 * self.margin)

        # 绘制坐标轴
        self.draw_axes()

        # 绘制网格
        self.draw_grid()

        # 绘制数据
        self.draw_predictions()

    def draw_axes(self):
        """绘制坐标轴"""
        # X轴
        x_axis = self.scene.addLine(
            self.margin, self.chart_height + self.margin,
            self.chart_width + self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 2)
        )

        # Y轴
        y_axis = self.scene.addLine(
            self.margin, self.margin,
            self.margin, self.chart_height + self.margin,
            QPen(Qt.black, 2)
        )

        # 坐标轴标签
        x_label = self.scene.addText("时间", QFont("Arial", 10))
        x_label.setPos(self.chart_width / 2 + self.margin - 15,
                       self.chart_height + self.margin + 10)

        y_label = self.scene.addText("置信度", QFont("Arial", 10))
        y_label.setPos(5, self.chart_height / 2 + self.margin - 10)

    def draw_grid(self):
        """绘制网格"""
        # 水平网格线
        for i in range(1, 5):
            y = self.margin + (self.chart_height * i / 5)
            line = self.scene.addLine(
                self.margin, y, self.chart_width + self.margin, y,
                QPen(QColor(200, 200, 200), 1, Qt.DashLine)
            )

        # 垂直网格线
        for i in range(1, 10):
            x = self.margin + (self.chart_width * i / 10)
            line = self.scene.addLine(
                x, self.margin, x, self.chart_height + self.margin,
                QPen(QColor(200, 200, 200), 1, Qt.DashLine)
            )

    def add_prediction(self, prediction: PredictionData):
        """添加预测数据"""
        self.predictions.append(prediction)
        self.draw_predictions()

    def draw_predictions(self):
        """绘制预测数据"""
        if len(self.predictions) < 2:
            return

        # 清除之前的预测线
        for item in self.scene.items():
            if hasattr(item, 'prediction_line'):
                self.scene.removeItem(item)

        # 计算数据点位置
        points = []
        for i, prediction in enumerate(self.predictions):
            x = self.margin + (self.chart_width * i / (len(self.predictions) - 1))
            y = self.margin + self.chart_height * (1 - prediction.confidence)
            points.append(QPointF(x, y))

        # 绘制预测线
        for i in range(len(points) - 1):
            line = self.scene.addLine(
                points[i].x(), points[i].y(),
                points[i + 1].x(), points[i + 1].y(),
                QPen(QColor(52, 152, 219), 3)
            )
            line.prediction_line = True

        # 绘制数据点
        for i, (point, prediction) in enumerate(zip(points, self.predictions)):
            # 根据置信度设置颜色
            if prediction.confidence >= 0.8:
                color = QColor(46, 204, 113)
            elif prediction.confidence >= 0.6:
                color = QColor(241, 196, 15)
            else:
                color = QColor(231, 76, 60)

            circle = self.scene.addEllipse(
                point.x() - 3, point.y() - 3, 6, 6,
                QPen(color, 2), QBrush(color)
            )
            circle.prediction_line = True

    def clear_data(self):
        """清除数据"""
        self.predictions.clear()
        self.setup_chart()


class PredictionHistoryWidget(QWidget):
    """预测历史组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.predictions: List[PredictionData] = []
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 控制区域
        control_layout = QHBoxLayout()

        # 预测类型过滤
        control_layout.addWidget(QLabel("预测类型:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["全部", "执行时间", "性能预测", "资源使用", "异常检测", "优化建议"])
        self.type_filter_combo.currentTextChanged.connect(self.filter_predictions)
        control_layout.addWidget(self.type_filter_combo)

        # 时间范围过滤
        control_layout.addWidget(QLabel("时间范围:"))
        self.time_filter_combo = QComboBox()
        self.time_filter_combo.addItems(["最近1小时", "最近24小时", "最近7天", "最近30天", "全部"])
        self.time_filter_combo.currentTextChanged.connect(self.filter_predictions)
        control_layout.addWidget(self.time_filter_combo)

        # 清除历史按钮
        clear_btn = QPushButton("🗑️ 清除历史")
        clear_btn.clicked.connect(self.clear_history)
        control_layout.addWidget(clear_btn)

        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 历史表格
        self.history_table = QTableWidget()
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSortingEnabled(True)

        # 设置表格列
        columns = ["时间", "类型", "预测值", "实际值", "置信度", "准确性", "执行时间"]
        self.history_table.setColumnCount(len(columns))
        self.history_table.setHorizontalHeaderLabels(columns)

        # 设置列宽
        header = self.history_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self.history_table)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout(stats_group)

        # 总预测次数
        stats_layout.addWidget(QLabel("总预测次数:"), 0, 0)
        self.total_predictions_label = QLabel("0")
        stats_layout.addWidget(self.total_predictions_label, 0, 1)

        # 平均置信度
        stats_layout.addWidget(QLabel("平均置信度:"), 0, 2)
        self.avg_confidence_label = QLabel("0%")
        stats_layout.addWidget(self.avg_confidence_label, 0, 3)

        # 预测准确率
        stats_layout.addWidget(QLabel("预测准确率:"), 1, 0)
        self.accuracy_rate_label = QLabel("0%")
        stats_layout.addWidget(self.accuracy_rate_label, 1, 1)

        # 平均执行时间
        stats_layout.addWidget(QLabel("平均执行时间:"), 1, 2)
        self.avg_execution_time_label = QLabel("0ms")
        stats_layout.addWidget(self.avg_execution_time_label, 1, 3)

        layout.addWidget(stats_group)

    def add_prediction(self, prediction: PredictionData):
        """添加预测记录"""
        self.predictions.append(prediction)
        self.filter_predictions()
        self.update_statistics()

    def filter_predictions(self):
        """过滤预测记录"""
        type_filter = self.type_filter_combo.currentText()
        time_filter = self.time_filter_combo.currentText()

        # 时间过滤
        now = datetime.now()
        time_filters = {
            "最近1小时": now - timedelta(hours=1),
            "最近24小时": now - timedelta(days=1),
            "最近7天": now - timedelta(days=7),
            "最近30天": now - timedelta(days=30),
            "全部": datetime.min
        }
        time_threshold = time_filters.get(time_filter, datetime.min)

        # 应用过滤
        filtered_predictions = []
        for prediction in self.predictions:
            # 时间过滤
            if prediction.timestamp < time_threshold:
                continue

            # 类型过滤
            if type_filter != "全部":
                type_mapping = {
                    "执行时间": PredictionType.EXECUTION_TIME,
                    "性能预测": PredictionType.PERFORMANCE,
                    "资源使用": PredictionType.RESOURCE_USAGE,
                    "异常检测": PredictionType.ANOMALY_DETECTION,
                    "优化建议": PredictionType.OPTIMIZATION
                }
                if prediction.prediction_type != type_mapping.get(type_filter):
                    continue

            filtered_predictions.append(prediction)

        self.update_table(filtered_predictions)

    def update_table(self, predictions: List[PredictionData]):
        """更新表格显示"""
        self.history_table.setRowCount(len(predictions))

        for row, prediction in enumerate(predictions):
            # 时间
            time_item = QTableWidgetItem(prediction.timestamp.strftime("%m-%d %H:%M:%S"))
            self.history_table.setItem(row, 0, time_item)

            # 类型
            type_names = {
                PredictionType.EXECUTION_TIME: "执行时间",
                PredictionType.PERFORMANCE: "性能预测",
                PredictionType.RESOURCE_USAGE: "资源使用",
                PredictionType.ANOMALY_DETECTION: "异常检测",
                PredictionType.OPTIMIZATION: "优化建议"
            }
            type_item = QTableWidgetItem(type_names.get(prediction.prediction_type, "未知"))
            self.history_table.setItem(row, 1, type_item)

            # 预测值
            predicted_item = QTableWidgetItem(str(prediction.predicted_value))
            self.history_table.setItem(row, 2, predicted_item)

            # 实际值
            actual_text = str(prediction.actual_value) if prediction.actual_value is not None else "待确认"
            actual_item = QTableWidgetItem(actual_text)
            self.history_table.setItem(row, 3, actual_item)

            # 置信度
            confidence_widget = ConfidenceIndicator(prediction.confidence)
            self.history_table.setCellWidget(row, 4, confidence_widget)

            # 准确性
            if prediction.error is not None:
                accuracy = max(0, 1 - abs(prediction.error))
                accuracy_item = QTableWidgetItem(f"{accuracy:.1%}")
                if accuracy >= 0.8:
                    accuracy_item.setBackground(QColor(212, 237, 218))
                elif accuracy >= 0.6:
                    accuracy_item.setBackground(QColor(255, 243, 205))
                else:
                    accuracy_item.setBackground(QColor(248, 215, 218))
            else:
                accuracy_item = QTableWidgetItem("待评估")
            self.history_table.setItem(row, 5, accuracy_item)

            # 执行时间
            exec_time_item = QTableWidgetItem(f"{prediction.execution_time_ms:.1f}ms")
            self.history_table.setItem(row, 6, exec_time_item)

    def update_statistics(self):
        """更新统计信息"""
        if not self.predictions:
            return

        # 总预测次数
        self.total_predictions_label.setText(str(len(self.predictions)))

        # 平均置信度
        avg_confidence = sum(p.confidence for p in self.predictions) / len(self.predictions)
        self.avg_confidence_label.setText(f"{avg_confidence:.1%}")

        # 预测准确率（有实际值的预测中准确的比例）
        predictions_with_actual = [p for p in self.predictions if p.actual_value is not None]
        if predictions_with_actual:
            accurate_predictions = sum(1 for p in predictions_with_actual
                                       if p.error is not None and abs(p.error) < 0.2)
            accuracy_rate = accurate_predictions / len(predictions_with_actual)
            self.accuracy_rate_label.setText(f"{accuracy_rate:.1%}")

        # 平均执行时间
        avg_exec_time = sum(p.execution_time_ms for p in self.predictions) / len(self.predictions)
        self.avg_execution_time_label.setText(f"{avg_exec_time:.1f}ms")

    def clear_history(self):
        """清除历史记录"""
        reply = QMessageBox.question(
            self, "确认清除", "确定要清除所有预测历史记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.predictions.clear()
            self.filter_predictions()
            self.update_statistics()


class RealTimePredictionWidget(QWidget):
    """实时预测监控组件"""

    prediction_received = pyqtSignal(object)  # PredictionData

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_adapter = None
        self.setup_ui()
        self.setup_timer()

        # 初始化适配器
        if CORE_AVAILABLE:
            try:
                self.ui_adapter = get_ui_adapter()
            except Exception as e:
                logger.warning(f"UI适配器初始化失败: {e}")

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 实时状态区域
        status_group = QGroupBox("🔴 实时监控状态")
        status_layout = QGridLayout(status_group)

        # 监控状态
        self.monitoring_status_label = QLabel("🟢 监控中")
        self.monitoring_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
                background-color: #d4edda;
                color: #155724;
            }
        """)
        status_layout.addWidget(self.monitoring_status_label, 0, 0, 1, 2)

        # 最后预测时间
        status_layout.addWidget(QLabel("最后预测:"), 1, 0)
        self.last_prediction_label = QLabel("无")
        status_layout.addWidget(self.last_prediction_label, 1, 1)

        # 预测频率
        status_layout.addWidget(QLabel("预测频率:"), 2, 0)
        self.prediction_frequency_label = QLabel("0 次/分钟")
        status_layout.addWidget(self.prediction_frequency_label, 2, 1)

        layout.addWidget(status_group)

        # 实时图表
        chart_group = QGroupBox("实时预测图表")
        chart_layout = QVBoxLayout(chart_group)

        self.real_time_chart = PredictionChart()
        self.real_time_chart.setFixedHeight(250)
        chart_layout.addWidget(self.real_time_chart)

        layout.addWidget(chart_group)

        # 最新预测结果
        latest_group = QGroupBox("最新预测结果")
        latest_layout = QFormLayout(latest_group)

        # 预测类型
        self.latest_type_label = QLabel("无")
        latest_layout.addRow("预测类型:", self.latest_type_label)

        # 预测值
        self.latest_value_label = QLabel("无")
        latest_layout.addRow("预测值:", self.latest_value_label)

        # 置信度
        self.latest_confidence_widget = ConfidenceIndicator()
        latest_layout.addRow("置信度:", self.latest_confidence_widget)

        # 执行时间
        self.latest_exec_time_label = QLabel("0ms")
        latest_layout.addRow("执行时间:", self.latest_exec_time_label)

        layout.addWidget(latest_group)

        # 控制按钮
        control_layout = QHBoxLayout()

        # 开始/停止监控
        self.monitor_toggle_btn = QPushButton("⏸️ 暂停监控")
        self.monitor_toggle_btn.clicked.connect(self.toggle_monitoring)
        control_layout.addWidget(self.monitor_toggle_btn)

        # 清除图表
        clear_chart_btn = QPushButton("🗑️ 清除图表")
        clear_chart_btn.clicked.connect(self.real_time_chart.clear_data)
        control_layout.addWidget(clear_chart_btn)

        control_layout.addStretch()

        layout.addLayout(control_layout)

    def setup_timer(self):
        """设置定时器"""
        self.prediction_timer = QTimer()
        self.prediction_timer.timeout.connect(self.simulate_prediction)
        self.prediction_timer.start(5000)  # 每5秒模拟一次预测

        self.monitoring_active = True

    def simulate_prediction(self):
        """模拟预测"""
        if not self.monitoring_active:
            return

        import random

        # 随机生成预测数据
        prediction_types = list(PredictionType)
        prediction_type = random.choice(prediction_types)

        # 生成预测值
        if prediction_type == PredictionType.EXECUTION_TIME:
            predicted_value = f"{random.randint(30, 180)} 分钟"
        elif prediction_type == PredictionType.PERFORMANCE:
            predicted_value = f"{random.randint(1000, 5000)} 条/秒"
        elif prediction_type == PredictionType.RESOURCE_USAGE:
            predicted_value = f"CPU: {random.randint(40, 80)}%"
        elif prediction_type == PredictionType.ANOMALY_DETECTION:
            predicted_value = "正常" if random.random() > 0.2 else "异常"
        else:
            predicted_value = f"优化建议 #{random.randint(1, 10)}"

        # 创建预测数据
        prediction = PredictionData(
            id=f"pred_{datetime.now().timestamp()}",
            prediction_type=prediction_type,
            timestamp=datetime.now(),
            input_features={},
            predicted_value=predicted_value,
            confidence=random.uniform(0.6, 0.95),
            execution_time_ms=random.uniform(50, 200)
        )

        self.add_prediction(prediction)

    def add_prediction(self, prediction: PredictionData):
        """添加预测结果"""
        # 更新图表
        self.real_time_chart.add_prediction(prediction)

        # 更新最新结果显示
        type_names = {
            PredictionType.EXECUTION_TIME: "执行时间预测",
            PredictionType.PERFORMANCE: "性能预测",
            PredictionType.RESOURCE_USAGE: "资源使用预测",
            PredictionType.ANOMALY_DETECTION: "异常检测",
            PredictionType.OPTIMIZATION: "优化建议"
        }

        self.latest_type_label.setText(type_names.get(prediction.prediction_type, "未知"))
        self.latest_value_label.setText(str(prediction.predicted_value))
        self.latest_confidence_widget.set_confidence(prediction.confidence)
        self.latest_exec_time_label.setText(f"{prediction.execution_time_ms:.1f}ms")

        # 更新状态
        self.last_prediction_label.setText(prediction.timestamp.strftime("%H:%M:%S"))

        # 发射信号
        self.prediction_received.emit(prediction)

    def toggle_monitoring(self):
        """切换监控状态"""
        self.monitoring_active = not self.monitoring_active

        if self.monitoring_active:
            self.monitor_toggle_btn.setText("⏸️ 暂停监控")
            self.monitoring_status_label.setText("🟢 监控中")
            self.monitoring_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #d4edda;
                    color: #155724;
                }
            """)
        else:
            self.monitor_toggle_btn.setText("▶️ 开始监控")
            self.monitoring_status_label.setText("🔴 已暂停")
            self.monitoring_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #f8d7da;
                    color: #721c24;
                }
            """)


class AIPredictionDisplay(QWidget):
    """AI预测结果展示主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("AI预测结果展示")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 实时监控选项卡
        self.real_time_widget = RealTimePredictionWidget()
        self.tab_widget.addTab(self.real_time_widget, "🔴 实时监控")

        # 预测历史选项卡
        self.history_widget = PredictionHistoryWidget()
        self.tab_widget.addTab(self.history_widget, "📚 预测历史")

        # 趋势分析选项卡
        trend_tab = self.create_trend_analysis_tab()
        self.tab_widget.addTab(trend_tab, "趋势分析")

        # 模型性能选项卡
        performance_tab = self.create_model_performance_tab()
        self.tab_widget.addTab(performance_tab, "模型性能")

        layout.addWidget(self.tab_widget)

    def create_trend_analysis_tab(self) -> QWidget:
        """创建趋势分析选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 趋势控制区域
        control_group = QGroupBox("趋势分析控制")
        control_layout = QHBoxLayout(control_group)

        # 分析类型
        control_layout.addWidget(QLabel("分析类型:"))
        analysis_type_combo = QComboBox()
        analysis_type_combo.addItems(["置信度趋势", "准确率趋势", "执行时间趋势", "预测频率趋势"])
        control_layout.addWidget(analysis_type_combo)

        # 时间窗口
        control_layout.addWidget(QLabel("时间窗口:"))
        time_window_combo = QComboBox()
        time_window_combo.addItems(["最近1小时", "最近24小时", "最近7天", "最近30天"])
        control_layout.addWidget(time_window_combo)

        # 分析按钮
        analyze_btn = QPushButton("开始分析")
        control_layout.addWidget(analyze_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        # 趋势图表区域
        chart_group = QGroupBox("趋势图表")
        chart_layout = QVBoxLayout(chart_group)

        trend_chart = PredictionChart()
        trend_chart.setFixedHeight(300)
        chart_layout.addWidget(trend_chart)

        layout.addWidget(chart_group)

        # 趋势分析结果
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout(results_group)

        results_text = QTextEdit()
        results_text.setMaximumHeight(150)
        results_text.setReadOnly(True)
        results_text.setText("""
 趋势分析报告：

• 置信度趋势：过去24小时内平均置信度为 84.2%，呈上升趋势
• 预测准确率：当前准确率为 87.5%，较昨日提升 3.2%
• 执行时间：平均执行时间为 125ms，性能稳定
• 预测频率：每分钟平均 2.3 次预测，符合预期

 关键洞察：
• AI模型在上午时段表现最佳
• 执行时间预测的准确率最高（92.1%）
• 异常检测的误报率有所下降
        """)
        results_layout.addWidget(results_text)

        layout.addWidget(results_group)

        return widget

    def create_model_performance_tab(self) -> QWidget:
        """创建模型性能选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 性能指标区域
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QGridLayout(metrics_group)

        # 响应时间
        metrics_layout.addWidget(QLabel("平均响应时间:"), 0, 0)
        response_time_progress = QProgressBar()
        response_time_progress.setRange(0, 1000)
        response_time_progress.setValue(125)
        response_time_progress.setFormat("125ms")
        metrics_layout.addWidget(response_time_progress, 0, 1)

        # 吞吐量
        metrics_layout.addWidget(QLabel("预测吞吐量:"), 1, 0)
        throughput_progress = QProgressBar()
        throughput_progress.setRange(0, 100)
        throughput_progress.setValue(78)
        throughput_progress.setFormat("78 预测/分钟")
        metrics_layout.addWidget(throughput_progress, 1, 1)

        # 内存使用
        metrics_layout.addWidget(QLabel("内存使用:"), 2, 0)
        memory_progress = QProgressBar()
        memory_progress.setRange(0, 100)
        memory_progress.setValue(45)
        memory_progress.setFormat("45%")
        metrics_layout.addWidget(memory_progress, 2, 1)

        # CPU使用
        metrics_layout.addWidget(QLabel("CPU使用:"), 3, 0)
        cpu_progress = QProgressBar()
        cpu_progress.setRange(0, 100)
        cpu_progress.setValue(32)
        cpu_progress.setFormat("32%")
        metrics_layout.addWidget(cpu_progress, 3, 1)

        layout.addWidget(metrics_group)

        # 模型比较区域
        comparison_group = QGroupBox("模型比较")
        comparison_layout = QVBoxLayout(comparison_group)

        comparison_table = QTableWidget()
        comparison_table.setRowCount(4)
        comparison_table.setColumnCount(4)
        comparison_table.setHorizontalHeaderLabels(["模型", "准确率", "响应时间", "置信度"])

        # 填充示例数据
        models_data = [
            ("执行时间预测器 v2.1", "92.1%", "98ms", "89.3%"),
            ("性能优化器 v1.8", "87.5%", "145ms", "84.7%"),
            ("异常检测器 v3.0", "78.9%", "76ms", "91.2%"),
            ("资源预测器 v1.5", "85.3%", "112ms", "86.8%")
        ]

        for row, (model, accuracy, response, confidence) in enumerate(models_data):
            comparison_table.setItem(row, 0, QTableWidgetItem(model))
            comparison_table.setItem(row, 1, QTableWidgetItem(accuracy))
            comparison_table.setItem(row, 2, QTableWidgetItem(response))
            comparison_table.setItem(row, 3, QTableWidgetItem(confidence))

        comparison_table.resizeColumnsToContents()
        comparison_layout.addWidget(comparison_table)

        layout.addWidget(comparison_group)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        # 连接实时预测信号到历史记录
        self.real_time_widget.prediction_received.connect(
            self.history_widget.add_prediction
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
    widget = AIPredictionDisplay()
    widget.setWindowTitle("AI预测结果展示")
    widget.resize(1200, 800)
    widget.show()

    sys.exit(app.exec_())
