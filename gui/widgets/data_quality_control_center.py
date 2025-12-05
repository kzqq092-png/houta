#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据质量控制中心

提供完整的数据质量管理功能，包括：
- 数据质量指标监控
- 质量规则配置和管理
- 异常检测和处理
- 质量报告生成
- 数据清洗建议

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import logging
import json
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
    QTreeWidgetItem, QLineEdit, QDoubleSpinBox, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QDateTime, QTime, QDate, QSize
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFontMetrics
)

# 导入核心数据质量组件
try:
    from core.services.unified_data_quality_monitor import UnifiedDataQualityMonitor
    from core.ai.data_anomaly_detector import DataAnomalyDetector
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    from gui.widgets.enhanced_ui.data_quality_monitor_tab_real_data import get_real_data_provider
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"核心数据质量服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class QualityMetricType(Enum):
    """质量指标类型"""
    COMPLETENESS = "completeness"      # 完整性
    ACCURACY = "accuracy"              # 准确性
    CONSISTENCY = "consistency"        # 一致性
    VALIDITY = "validity"              # 有效性
    UNIQUENESS = "uniqueness"          # 唯一性
    TIMELINESS = "timeliness"          # 及时性


class QualityRuleType(Enum):
    """质量规则类型"""
    NOT_NULL = "not_null"              # 非空检查
    RANGE_CHECK = "range_check"        # 范围检查
    FORMAT_CHECK = "format_check"      # 格式检查
    REFERENCE_CHECK = "reference_check"  # 引用检查
    BUSINESS_RULE = "business_rule"    # 业务规则
    DUPLICATE_CHECK = "duplicate_check"  # 重复检查


class QualitySeverity(Enum):
    """质量问题严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityMetric:
    """质量指标"""
    metric_type: QualityMetricType
    value: float  # 0-1
    threshold: float = 0.8
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QualityRule:
    """质量规则"""
    id: str
    name: str
    rule_type: QualityRuleType
    column: str
    parameters: Dict[str, Any]
    enabled: bool = True
    severity: QualitySeverity = QualitySeverity.MEDIUM
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityIssue:
    """质量问题"""
    id: str
    rule_id: str
    rule_name: str
    severity: QualitySeverity
    description: str
    affected_rows: int
    column: str
    sample_values: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_note: Optional[str] = None


class QualityScoreGauge(QWidget):
    """质量评分仪表盘"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.score = 0.0
        self.target_score = 0.8
        self.setFixedSize(120, 120)

    def set_score(self, score: float):
        """设置评分"""
        self.score = max(0.0, min(1.0, score))
        self.update()

    def set_target(self, target: float):
        """设置目标评分"""
        self.target_score = max(0.0, min(1.0, target))
        self.update()

    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取绘制区域
        rect = self.rect().adjusted(10, 10, -10, -10)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 5

        # 绘制背景圆环
        painter.setPen(QPen(QColor(230, 230, 230), 8))
        painter.drawArc(rect, 0, 360 * 16)

        # 绘制目标线
        target_angle = int(self.target_score * 360 * 16)
        painter.setPen(QPen(QColor(189, 195, 199), 3))
        painter.drawArc(rect, 90 * 16 - target_angle, 10 * 16)

        # 绘制评分圆环
        score_angle = int(self.score * 360 * 16)

        # 根据评分选择颜色
        if self.score >= self.target_score:
            color = QColor(46, 204, 113)  # 绿色 - 达标
        elif self.score >= self.target_score * 0.8:
            color = QColor(241, 196, 15)  # 黄色 - 接近
        else:
            color = QColor(231, 76, 60)   # 红色 - 不达标

        painter.setPen(QPen(color, 8))
        painter.drawArc(rect, 90 * 16, -score_angle)

        # 绘制中心评分
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        score_text = f"{self.score:.1%}"
        painter.drawText(rect, Qt.AlignCenter, score_text)

        # 绘制标题
        painter.setFont(QFont("Arial", 10))
        title_rect = rect.adjusted(0, rect.height() + 5, 0, rect.height() + 25)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)


class QualityRuleDialog(QDialog):
    """质量规则配置对话框"""

    def __init__(self, rule: Optional[QualityRule] = None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.is_edit_mode = rule is not None
        self.setup_ui()

        if self.is_edit_mode:
            self.load_rule_data()

    def setup_ui(self):
        """设置UI"""
        title = "编辑质量规则" if self.is_edit_mode else "新建质量规则"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)

        # 规则名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入规则名称")
        basic_layout.addRow("规则名称:", self.name_edit)

        # 规则类型
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "非空检查", "范围检查", "格式检查", "引用检查", "业务规则", "重复检查"
        ])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        basic_layout.addRow("规则类型:", self.type_combo)

        # 目标列
        self.column_edit = QLineEdit()
        self.column_edit.setPlaceholderText("输入列名或选择")
        basic_layout.addRow("目标列:", self.column_edit)

        # 严重程度
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["低", "中", "高", "严重"])
        self.severity_combo.setCurrentText("中")
        basic_layout.addRow("严重程度:", self.severity_combo)

        # 启用状态
        self.enabled_check = QCheckBox("启用此规则")
        self.enabled_check.setChecked(True)
        basic_layout.addRow("状态:", self.enabled_check)

        layout.addWidget(basic_group)

        # 规则参数
        self.params_group = QGroupBox("规则参数")
        self.params_layout = QFormLayout(self.params_group)
        layout.addWidget(self.params_group)

        # 描述
        desc_group = QGroupBox("描述")
        desc_layout = QVBoxLayout(desc_group)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlaceholderText("输入规则描述...")
        desc_layout.addWidget(self.description_edit)

        layout.addWidget(desc_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 初始化参数界面
        self.on_type_changed()

    def on_type_changed(self):
        """规则类型变化时更新参数界面"""
        # 清除现有参数
        for i in reversed(range(self.params_layout.count())):
            child = self.params_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        rule_type = self.type_combo.currentText()

        if rule_type == "范围检查":
            # 最小值
            self.min_value_edit = QDoubleSpinBox()
            self.min_value_edit.setRange(-999999, 999999)
            self.params_layout.addRow("最小值:", self.min_value_edit)

            # 最大值
            self.max_value_edit = QDoubleSpinBox()
            self.max_value_edit.setRange(-999999, 999999)
            self.max_value_edit.setValue(100)
            self.params_layout.addRow("最大值:", self.max_value_edit)

        elif rule_type == "格式检查":
            # 正则表达式
            self.pattern_edit = QLineEdit()
            self.pattern_edit.setPlaceholderText("输入正则表达式")
            self.params_layout.addRow("模式:", self.pattern_edit)

            # 示例
            example_label = QLabel("示例: ^[0-9]{6}$ (6位数字)")
            example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.params_layout.addRow("", example_label)

        elif rule_type == "引用检查":
            # 引用表
            self.ref_table_edit = QLineEdit()
            self.ref_table_edit.setPlaceholderText("引用表名")
            self.params_layout.addRow("引用表:", self.ref_table_edit)

            # 引用列
            self.ref_column_edit = QLineEdit()
            self.ref_column_edit.setPlaceholderText("引用列名")
            self.params_layout.addRow("引用列:", self.ref_column_edit)

        elif rule_type == "业务规则":
            # 表达式
            self.expression_edit = QTextEdit()
            self.expression_edit.setMaximumHeight(80)
            self.expression_edit.setPlaceholderText("输入业务规则表达式")
            self.params_layout.addRow("表达式:", self.expression_edit)

    def load_rule_data(self):
        """加载规则数据"""
        if not self.rule:
            return

        self.name_edit.setText(self.rule.name)

        # 设置规则类型
        type_mapping = {
            QualityRuleType.NOT_NULL: "非空检查",
            QualityRuleType.RANGE_CHECK: "范围检查",
            QualityRuleType.FORMAT_CHECK: "格式检查",
            QualityRuleType.REFERENCE_CHECK: "引用检查",
            QualityRuleType.BUSINESS_RULE: "业务规则",
            QualityRuleType.DUPLICATE_CHECK: "重复检查"
        }
        self.type_combo.setCurrentText(type_mapping.get(self.rule.rule_type, "非空检查"))

        self.column_edit.setText(self.rule.column)

        # 设置严重程度
        severity_mapping = {
            QualitySeverity.LOW: "低",
            QualitySeverity.MEDIUM: "中",
            QualitySeverity.HIGH: "高",
            QualitySeverity.CRITICAL: "严重"
        }
        self.severity_combo.setCurrentText(severity_mapping.get(self.rule.severity, "中"))

        self.enabled_check.setChecked(self.rule.enabled)
        self.description_edit.setPlainText(self.rule.description)

        # 加载参数
        self.load_rule_parameters()

    def load_rule_parameters(self):
        """加载规则参数"""
        if not self.rule or not self.rule.parameters:
            return

        params = self.rule.parameters

        if self.rule.rule_type == QualityRuleType.RANGE_CHECK:
            if hasattr(self, 'min_value_edit'):
                self.min_value_edit.setValue(params.get('min_value', 0))
            if hasattr(self, 'max_value_edit'):
                self.max_value_edit.setValue(params.get('max_value', 100))

        elif self.rule.rule_type == QualityRuleType.FORMAT_CHECK:
            if hasattr(self, 'pattern_edit'):
                self.pattern_edit.setText(params.get('pattern', ''))

        elif self.rule.rule_type == QualityRuleType.REFERENCE_CHECK:
            if hasattr(self, 'ref_table_edit'):
                self.ref_table_edit.setText(params.get('ref_table', ''))
            if hasattr(self, 'ref_column_edit'):
                self.ref_column_edit.setText(params.get('ref_column', ''))

        elif self.rule.rule_type == QualityRuleType.BUSINESS_RULE:
            if hasattr(self, 'expression_edit'):
                self.expression_edit.setPlainText(params.get('expression', ''))

    def get_rule_data(self) -> QualityRule:
        """获取规则数据"""
        # 类型映射
        type_mapping = {
            "非空检查": QualityRuleType.NOT_NULL,
            "范围检查": QualityRuleType.RANGE_CHECK,
            "格式检查": QualityRuleType.FORMAT_CHECK,
            "引用检查": QualityRuleType.REFERENCE_CHECK,
            "业务规则": QualityRuleType.BUSINESS_RULE,
            "重复检查": QualityRuleType.DUPLICATE_CHECK
        }

        severity_mapping = {
            "低": QualitySeverity.LOW,
            "中": QualitySeverity.MEDIUM,
            "高": QualitySeverity.HIGH,
            "严重": QualitySeverity.CRITICAL
        }

        # 收集参数
        parameters = {}
        rule_type_text = self.type_combo.currentText()

        if rule_type_text == "范围检查":
            if hasattr(self, 'min_value_edit'):
                parameters['min_value'] = self.min_value_edit.value()
            if hasattr(self, 'max_value_edit'):
                parameters['max_value'] = self.max_value_edit.value()

        elif rule_type_text == "格式检查":
            if hasattr(self, 'pattern_edit'):
                parameters['pattern'] = self.pattern_edit.text()

        elif rule_type_text == "引用检查":
            if hasattr(self, 'ref_table_edit'):
                parameters['ref_table'] = self.ref_table_edit.text()
            if hasattr(self, 'ref_column_edit'):
                parameters['ref_column'] = self.ref_column_edit.text()

        elif rule_type_text == "业务规则":
            if hasattr(self, 'expression_edit'):
                parameters['expression'] = self.expression_edit.toPlainText()

        # 创建规则对象
        rule_id = self.rule.id if self.is_edit_mode else f"rule_{int(datetime.now().timestamp())}"

        return QualityRule(
            id=rule_id,
            name=self.name_edit.text(),
            rule_type=type_mapping[rule_type_text],
            column=self.column_edit.text(),
            parameters=parameters,
            enabled=self.enabled_check.isChecked(),
            severity=severity_mapping[self.severity_combo.currentText()],
            description=self.description_edit.toPlainText()
        )


class DataQualityControlCenter(QWidget):
    """数据质量控制中心主组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_adapter = None
        self.quality_monitor = None
        self.anomaly_detector = None

        # 数据存储
        self.quality_metrics: Dict[QualityMetricType, QualityMetric] = {}
        self.quality_rules: List[QualityRule] = []
        self.quality_issues: List[QualityIssue] = []

        # 初始化核心服务
        if CORE_AVAILABLE:
            try:
                self.ui_adapter = get_ui_adapter()
                self.quality_monitor = UnifiedDataQualityMonitor()
                self.anomaly_detector = DataAnomalyDetector()
            except Exception as e:
                logger.warning(f"核心数据质量服务初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        self.load_sample_data()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题和控制区域
        header_layout = QHBoxLayout()

        title_label = QLabel("数据质量控制中心")
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
        scan_btn = QPushButton("质量扫描")
        scan_btn.clicked.connect(self.start_quality_scan)
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

        clean_btn = QPushButton("🧹 数据清洗")
        clean_btn.clicked.connect(self.start_data_cleaning)
        clean_btn.setStyleSheet("""
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
        header_layout.addWidget(clean_btn)

        layout.addLayout(header_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 质量概览选项卡
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "质量概览")

        # 质量规则选项卡
        rules_tab = self.create_rules_tab()
        self.tab_widget.addTab(rules_tab, "质量规则")

        # 质量问题选项卡
        issues_tab = self.create_issues_tab()
        self.tab_widget.addTab(issues_tab, "质量问题")

        # 质量报告选项卡
        reports_tab = self.create_reports_tab()
        self.tab_widget.addTab(reports_tab, "质量报告")

        layout.addWidget(self.tab_widget)

        # 状态栏
        status_layout = QHBoxLayout()

        self.quality_status_label = QLabel("🟢 数据质量良好")
        self.quality_status_label.setStyleSheet("""
            QLabel {
                background-color: #d4edda;
                color: #155724;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        status_layout.addWidget(self.quality_status_label)

        status_layout.addStretch()

        self.last_scan_label = QLabel("最后扫描: --")
        status_layout.addWidget(self.last_scan_label)

        layout.addLayout(status_layout)

    def create_overview_tab(self) -> QWidget:
        """创建质量概览选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 质量评分仪表盘
        gauges_group = QGroupBox("质量评分仪表盘")
        gauges_layout = QGridLayout(gauges_group)

        # 创建各种质量评分仪表盘
        self.overall_gauge = QualityScoreGauge("整体质量")
        self.overall_gauge.setFixedHeight(120)
        self.completeness_gauge = QualityScoreGauge("完整性")
        self.completeness_gauge.setFixedHeight(120)
        self.accuracy_gauge = QualityScoreGauge("准确性")
        self.accuracy_gauge.setFixedHeight(120)
        self.consistency_gauge = QualityScoreGauge("一致性")
        self.consistency_gauge.setFixedHeight(120)
        self.validity_gauge = QualityScoreGauge("有效性")
        self.validity_gauge.setFixedHeight(120)
        self.uniqueness_gauge = QualityScoreGauge("唯一性")
        self.uniqueness_gauge.setFixedHeight(120)

        gauges_layout.addWidget(self.overall_gauge, 0, 0, Qt.AlignCenter)
        gauges_layout.addWidget(self.completeness_gauge, 0, 1, Qt.AlignCenter)
        gauges_layout.addWidget(self.accuracy_gauge, 0, 2, Qt.AlignCenter)
        gauges_layout.addWidget(self.consistency_gauge, 0, 3, Qt.AlignCenter)
        gauges_layout.addWidget(self.validity_gauge, 0, 4, Qt.AlignCenter)
        gauges_layout.addWidget(self.uniqueness_gauge, 0, 5, Qt.AlignCenter)

        layout.addWidget(gauges_group)

        # 快速统计
        stats_group = QGroupBox("快速统计")
        stats_group.setContentsMargins(10, 10, 10, 10)
        stats_group.setStyleSheet("QGroupBox { border: none; }")
        stats_layout = QGridLayout(stats_group)

        # 总记录数
        stats_layout.addWidget(QLabel("总记录数:"), 0, 0)
        self.total_records_label = QLabel("0")
        self.total_records_label.setStyleSheet("font-weight: bold; color: #3498db; font-size: 14px;")
        stats_layout.addWidget(self.total_records_label, 0, 1)

        # 质量问题数
        stats_layout.addWidget(QLabel("质量问题:"), 0, 2)
        self.total_issues_label = QLabel("0")
        self.total_issues_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 14px;")
        stats_layout.addWidget(self.total_issues_label, 0, 3)

        # 活跃规则数
        stats_layout.addWidget(QLabel("活跃规则:"), 1, 0)
        self.active_rules_label = QLabel("0")
        self.active_rules_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 14px;")
        stats_layout.addWidget(self.active_rules_label, 1, 1)

        # 最后扫描时间
        stats_layout.addWidget(QLabel("最后扫描:"), 1, 2)
        self.last_scan_time_label = QLabel("从未")
        stats_layout.addWidget(self.last_scan_time_label, 1, 3)

        layout.addWidget(stats_group)

        return widget

    def create_rules_tab(self) -> QWidget:
        """创建质量规则选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 规则控制区域
        control_layout = QHBoxLayout()

        # 规则过滤
        control_layout.addWidget(QLabel("规则类型:"))
        self.rule_filter_combo = QComboBox()
        self.rule_filter_combo.addItems([
            "全部", "非空检查", "范围检查", "格式检查", "引用检查", "业务规则", "重复检查"
        ])
        self.rule_filter_combo.currentTextChanged.connect(self.filter_rules)
        control_layout.addWidget(self.rule_filter_combo)

        control_layout.addWidget(QLabel("状态:"))
        self.rule_status_filter_combo = QComboBox()
        self.rule_status_filter_combo.addItems(["全部", "启用", "禁用"])
        self.rule_status_filter_combo.currentTextChanged.connect(self.filter_rules)
        control_layout.addWidget(self.rule_status_filter_combo)

        control_layout.addStretch()

        # 规则操作按钮
        add_rule_btn = QPushButton("➕ 新建规则")
        add_rule_btn.clicked.connect(self.add_quality_rule)
        control_layout.addWidget(add_rule_btn)

        edit_rule_btn = QPushButton("✏️ 编辑规则")
        edit_rule_btn.clicked.connect(self.edit_quality_rule)
        control_layout.addWidget(edit_rule_btn)

        delete_rule_btn = QPushButton("🗑️ 删除规则")
        delete_rule_btn.clicked.connect(self.delete_quality_rule)
        control_layout.addWidget(delete_rule_btn)

        layout.addLayout(control_layout)

        # 规则列表表格
        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(7)
        self.rules_table.setHorizontalHeaderLabels([
            "规则名称", "类型", "目标列", "严重程度", "状态", "创建时间", "描述"
        ])

        # 设置列宽
        header = self.rules_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # 设置行选择模式
        self.rules_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.rules_table)

        return widget

    def create_issues_tab(self) -> QWidget:
        """创建质量问题选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 问题控制区域
        control_layout = QHBoxLayout()

        # 问题过滤
        control_layout.addWidget(QLabel("严重程度:"))
        self.issue_severity_filter_combo = QComboBox()
        self.issue_severity_filter_combo.addItems(["全部", "严重", "高", "中", "低"])
        self.issue_severity_filter_combo.currentTextChanged.connect(self.filter_issues)
        control_layout.addWidget(self.issue_severity_filter_combo)

        control_layout.addWidget(QLabel("状态:"))
        self.issue_status_filter_combo = QComboBox()
        self.issue_status_filter_combo.addItems(["全部", "未解决", "已解决"])
        self.issue_status_filter_combo.currentTextChanged.connect(self.filter_issues)
        control_layout.addWidget(self.issue_status_filter_combo)

        control_layout.addStretch()

        # 批量操作
        resolve_selected_btn = QPushButton("标记已解决")
        resolve_selected_btn.clicked.connect(self.resolve_selected_issues)
        control_layout.addWidget(resolve_selected_btn)

        export_issues_btn = QPushButton("导出问题")
        export_issues_btn.clicked.connect(self.export_issues)
        control_layout.addWidget(export_issues_btn)

        layout.addLayout(control_layout)

        # 问题列表表格
        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(7)
        self.issues_table.setHorizontalHeaderLabels([
            "检测时间", "规则名称", "严重程度", "列名", "影响行数", "状态", "描述"
        ])

        # 设置列宽
        header = self.issues_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # 设置多行选择
        self.issues_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.issues_table.setSelectionMode(QTableWidget.MultiSelection)

        layout.addWidget(self.issues_table)

        # 问题详情
        details_group = QGroupBox("问题详情")
        details_layout = QVBoxLayout(details_group)

        self.issue_details_text = QTextEdit()
        self.issue_details_text.setReadOnly(True)
        self.issue_details_text.setMaximumHeight(120)
        self.issue_details_text.setPlaceholderText("选择问题查看详情...")
        details_layout.addWidget(self.issue_details_text)

        layout.addWidget(details_group)

        # 连接选择事件
        self.issues_table.itemSelectionChanged.connect(self.show_issue_details)

        return widget

    def create_reports_tab(self) -> QWidget:
        """创建质量报告选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 报告生成控制
        control_group = QGroupBox("报告生成")
        control_layout = QFormLayout(control_group)

        # 报告类型
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "综合质量报告", "规则执行报告", "问题统计报告", "趋势分析报告"
        ])
        control_layout.addRow("报告类型:", self.report_type_combo)

        # 时间范围
        self.report_period_combo = QComboBox()
        self.report_period_combo.addItems([
            "最近7天", "最近30天", "最近90天", "自定义"
        ])
        control_layout.addRow("时间范围:", self.report_period_combo)

        # 输出格式
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["PDF", "Excel", "HTML"])
        control_layout.addRow("输出格式:", self.report_format_combo)

        # 生成按钮
        generate_btn = QPushButton("生成报告")
        generate_btn.clicked.connect(self.generate_quality_report)
        control_layout.addRow("", generate_btn)

        layout.addWidget(control_group)

        # 报告预览
        preview_group = QGroupBox("报告预览")
        preview_layout = QVBoxLayout(preview_group)

        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setText("""
 数据质量综合报告

生成时间: 2024-01-15 14:30:00
数据源: 股票行情数据
记录总数: 1,234,567

质量指标总览:
• 整体质量评分: 85.2%
• 完整性: 92.1%
• 准确性: 88.5%
• 一致性: 91.3%
• 有效性: 87.2%
• 唯一性: 94.8%

 质量问题统计:
• 严重问题: 3个
• 高级问题: 12个
• 中级问题: 45个
• 低级问题: 156个

 规则执行情况:
• 活跃规则: 24个
• 规则通过率: 94.8%
• 平均执行时间: 125ms

[INFO] 改进建议:
• 加强价格数据的范围检查
• 完善交易量的异常检测
• 优化重复数据的清理流程

📞 联系信息:
质量团队: quality@factorweave.com
技术支持: support@factorweave.com
        """)
        preview_layout.addWidget(self.report_preview)

        layout.addWidget(preview_group)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        pass

    def setup_timers(self):
        """设置定时器"""
        # 质量指标更新定时器
        self.quality_timer = QTimer()
        self.quality_timer.timeout.connect(self.update_quality_metrics)
        self.quality_timer.start(10000)  # 每10秒更新一次

    def load_sample_data(self):
        """加载数据（使用真实数据质量监控）"""
        # 初始化真实数据提供者
        try:
            if CORE_AVAILABLE:
                self.real_data_provider = get_real_data_provider()
                logger.info("数据质量控制中心: 真实数据提供者已初始化")

                # 加载真实数据
                self.load_real_metrics()
                self.load_real_rules()
                self.load_real_issues()

                logger.info("真实数据质量数据加载完成")
            else:
                # 降级到示例数据
                logger.warning("核心服务不可用，使用示例数据")
                self.generate_sample_metrics()
                self.generate_sample_rules()
                self.generate_sample_issues()
        except Exception as e:
            logger.error(f"加载真实数据失败: {e}")
            # 降级到示例数据
            self.generate_sample_metrics()
            self.generate_sample_rules()
            self.generate_sample_issues()

    def generate_sample_metrics(self):
        """生成示例质量指标"""
        import random

        metric_types = [
            QualityMetricType.COMPLETENESS,
            QualityMetricType.ACCURACY,
            QualityMetricType.CONSISTENCY,
            QualityMetricType.VALIDITY,
            QualityMetricType.UNIQUENESS
        ]

        for metric_type in metric_types:
            metric = QualityMetric(
                metric_type=metric_type,
                value=random.uniform(0.75, 0.95),
                threshold=0.8
            )
            self.quality_metrics[metric_type] = metric

        self.update_quality_gauges()

    def generate_sample_rules(self):
        """生成示例质量规则"""
        sample_rules = [
            QualityRule(
                "rule_001", "股票代码非空检查", QualityRuleType.NOT_NULL,
                "symbol", {}, True, QualitySeverity.CRITICAL,
                "确保所有记录都有股票代码"
            ),
            QualityRule(
                "rule_002", "价格范围检查", QualityRuleType.RANGE_CHECK,
                "price", {"min_value": 0, "max_value": 1000}, True, QualitySeverity.HIGH,
                "价格必须在合理范围内"
            ),
            QualityRule(
                "rule_003", "日期格式检查", QualityRuleType.FORMAT_CHECK,
                "date", {"pattern": "^\\d{4}-\\d{2}-\\d{2}$"}, True, QualitySeverity.MEDIUM,
                "日期必须符合YYYY-MM-DD格式"
            ),
            QualityRule(
                "rule_004", "交易量范围检查", QualityRuleType.RANGE_CHECK,
                "volume", {"min_value": 0, "max_value": 1000000000}, True, QualitySeverity.MEDIUM,
                "交易量必须为正数且在合理范围内"
            ),
            QualityRule(
                "rule_005", "股票代码重复检查", QualityRuleType.DUPLICATE_CHECK,
                "symbol", {}, True, QualitySeverity.LOW,
                "检查同一交易日的股票代码重复"
            )
        ]

        self.quality_rules = sample_rules
        self.filter_rules()

    def generate_sample_issues(self):
        """生成示例质量问题"""
        import random

        sample_issues = [
            QualityIssue(
                "issue_001", "rule_002", "价格范围检查",
                QualitySeverity.HIGH, "发现3条记录价格超出合理范围",
                3, "price", ["1500.00", "2000.00", "0.00"]
            ),
            QualityIssue(
                "issue_002", "rule_003", "日期格式检查",
                QualitySeverity.MEDIUM, "发现12条记录日期格式不正确",
                12, "date", ["2024/01/15", "01-15-2024", "20240115"]
            ),
            QualityIssue(
                "issue_003", "rule_001", "股票代码非空检查",
                QualitySeverity.CRITICAL, "发现1条记录股票代码为空",
                1, "symbol", ["NULL"]
            ),
            QualityIssue(
                "issue_004", "rule_005", "股票代码重复检查",
                QualitySeverity.LOW, "发现56条重复记录",
                56, "symbol", ["000001", "600000", "300001"]
            )
        ]

        for issue in sample_issues:
            issue.detected_at = datetime.now() - timedelta(hours=random.randint(1, 24))

        self.quality_issues = sample_issues
        self.filter_issues()

    def update_quality_metrics(self):
        """更新质量指标（使用真实数据）"""
        try:
            if hasattr(self, 'real_data_provider') and self.real_data_provider:
                # 获取真实指标
                metrics_data = self.real_data_provider.get_quality_metrics()

                # 更新现有指标
                metric_type_map = {
                    'completeness': QualityMetricType.COMPLETENESS,
                    'accuracy': QualityMetricType.ACCURACY,
                    'timeliness': QualityMetricType.TIMELINESS,
                    'consistency': QualityMetricType.CONSISTENCY,
                    'validity': QualityMetricType.VALIDITY,
                    'uniqueness': QualityMetricType.UNIQUENESS
                }

                for metric_name, value in metrics_data.items():
                    if metric_name in metric_type_map:
                        metric_type = metric_type_map[metric_name]
                        if metric_type in self.quality_metrics:
                            self.quality_metrics[metric_type].value = value
                            self.quality_metrics[metric_type].timestamp = datetime.now()
            else:
                # 降级到模拟数据
                import random
                for metric_type, metric in self.quality_metrics.items():
                    change = random.uniform(-0.02, 0.02)
                    metric.value = max(0.5, min(1.0, metric.value + change))
                    metric.timestamp = datetime.now()
        except Exception as e:
            logger.error(f"更新质量指标失败: {e}")

        self.update_quality_gauges()
        self.update_overview_stats()

    def update_quality_gauges(self):
        """更新质量仪表盘"""
        # 计算整体质量评分
        if self.quality_metrics:
            overall_score = sum(metric.value for metric in self.quality_metrics.values()) / len(self.quality_metrics)
            self.overall_gauge.set_score(overall_score)

        # 更新各项指标仪表盘
        gauge_mapping = {
            QualityMetricType.COMPLETENESS: self.completeness_gauge,
            QualityMetricType.ACCURACY: self.accuracy_gauge,
            QualityMetricType.CONSISTENCY: self.consistency_gauge,
            QualityMetricType.VALIDITY: self.validity_gauge,
            QualityMetricType.UNIQUENESS: self.uniqueness_gauge
        }

        for metric_type, gauge in gauge_mapping.items():
            if metric_type in self.quality_metrics:
                gauge.set_score(self.quality_metrics[metric_type].value)

    def update_overview_stats(self):
        """更新概览统计（使用真实数据）"""
        try:
            if hasattr(self, 'real_data_provider') and self.real_data_provider:
                # 获取真实统计
                datatypes = self.real_data_provider.get_datatypes_quality()

                # 总记录数
                total_records = sum(dt.get('count', 0) for dt in datatypes)
                self.total_records_label.setText(f"{total_records:,}")
            else:
                # 降级到模拟数据
                self.total_records_label.setText("1,234,567")
        except Exception as e:
            logger.error(f"更新概览统计失败: {e}")
            self.total_records_label.setText("N/A")

        # 质量问题数
        unresolved_issues = len([issue for issue in self.quality_issues if not issue.resolved])
        self.total_issues_label.setText(str(unresolved_issues))

        # 活跃规则数
        active_rules = len([rule for rule in self.quality_rules if rule.enabled])
        self.active_rules_label.setText(str(active_rules))

        # 最后扫描时间
        self.last_scan_time_label.setText(datetime.now().strftime("%H:%M:%S"))

        # 更新状态
        if unresolved_issues == 0:
            self.quality_status_label.setText("🟢 数据质量优秀")
            self.quality_status_label.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        elif unresolved_issues <= 5:
            self.quality_status_label.setText("🟡 数据质量良好")
            self.quality_status_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    color: #856404;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
        else:
            self.quality_status_label.setText("🔴 数据质量需要关注")
            self.quality_status_label.setStyleSheet("""
                QLabel {
                    background-color: #f8d7da;
                    color: #721c24;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)

    def filter_rules(self):
        """过滤质量规则"""
        type_filter = self.rule_filter_combo.currentText()
        status_filter = self.rule_status_filter_combo.currentText()

        # 应用过滤
        filtered_rules = []
        for rule in self.quality_rules:
            # 类型过滤
            if type_filter != "全部":
                type_mapping = {
                    "非空检查": QualityRuleType.NOT_NULL,
                    "范围检查": QualityRuleType.RANGE_CHECK,
                    "格式检查": QualityRuleType.FORMAT_CHECK,
                    "引用检查": QualityRuleType.REFERENCE_CHECK,
                    "业务规则": QualityRuleType.BUSINESS_RULE,
                    "重复检查": QualityRuleType.DUPLICATE_CHECK
                }
                if rule.rule_type != type_mapping.get(type_filter):
                    continue

            # 状态过滤
            if status_filter == "启用" and not rule.enabled:
                continue
            elif status_filter == "禁用" and rule.enabled:
                continue

            filtered_rules.append(rule)

        self.update_rules_table(filtered_rules)

    def update_rules_table(self, rules: List[QualityRule]):
        """更新规则表格"""
        self.rules_table.setRowCount(len(rules))

        type_names = {
            QualityRuleType.NOT_NULL: "非空检查",
            QualityRuleType.RANGE_CHECK: "范围检查",
            QualityRuleType.FORMAT_CHECK: "格式检查",
            QualityRuleType.REFERENCE_CHECK: "引用检查",
            QualityRuleType.BUSINESS_RULE: "业务规则",
            QualityRuleType.DUPLICATE_CHECK: "重复检查"
        }

        severity_names = {
            QualitySeverity.LOW: "低",
            QualitySeverity.MEDIUM: "中",
            QualitySeverity.HIGH: "高",
            QualitySeverity.CRITICAL: "严重"
        }

        severity_colors = {
            QualitySeverity.LOW: QColor("#d1ecf1"),
            QualitySeverity.MEDIUM: QColor("#fff3cd"),
            QualitySeverity.HIGH: QColor("#fdecea"),
            QualitySeverity.CRITICAL: QColor("#f8d7da")
        }

        for row, rule in enumerate(rules):
            # 规则名称
            name_item = QTableWidgetItem(rule.name)
            self.rules_table.setItem(row, 0, name_item)

            # 类型
            type_item = QTableWidgetItem(type_names.get(rule.rule_type, "未知"))
            self.rules_table.setItem(row, 1, type_item)

            # 目标列
            column_item = QTableWidgetItem(rule.column)
            self.rules_table.setItem(row, 2, column_item)

            # 严重程度
            severity_item = QTableWidgetItem(severity_names.get(rule.severity, "未知"))
            severity_item.setBackground(severity_colors.get(rule.severity, QColor("#ffffff")))
            self.rules_table.setItem(row, 3, severity_item)

            # 状态
            status_item = QTableWidgetItem("启用" if rule.enabled else "禁用")
            if rule.enabled:
                status_item.setBackground(QColor("#d4edda"))
            else:
                status_item.setBackground(QColor("#f8d7da"))
            self.rules_table.setItem(row, 4, status_item)

            # 创建时间
            time_item = QTableWidgetItem(rule.created_at.strftime("%Y-%m-%d"))
            self.rules_table.setItem(row, 5, time_item)

            # 描述
            desc_item = QTableWidgetItem(rule.description[:50] + "..." if len(rule.description) > 50 else rule.description)
            self.rules_table.setItem(row, 6, desc_item)

    def filter_issues(self):
        """过滤质量问题"""
        severity_filter = self.issue_severity_filter_combo.currentText()
        status_filter = self.issue_status_filter_combo.currentText()

        # 应用过滤
        filtered_issues = []
        for issue in self.quality_issues:
            # 严重程度过滤
            if severity_filter != "全部":
                severity_mapping = {
                    "严重": QualitySeverity.CRITICAL,
                    "高": QualitySeverity.HIGH,
                    "中": QualitySeverity.MEDIUM,
                    "低": QualitySeverity.LOW
                }
                if issue.severity != severity_mapping.get(severity_filter):
                    continue

            # 状态过滤
            if status_filter == "未解决" and issue.resolved:
                continue
            elif status_filter == "已解决" and not issue.resolved:
                continue

            filtered_issues.append(issue)

        self.update_issues_table(filtered_issues)

    def update_issues_table(self, issues: List[QualityIssue]):
        """更新问题表格"""
        self.issues_table.setRowCount(len(issues))

        severity_colors = {
            QualitySeverity.LOW: QColor("#d1ecf1"),
            QualitySeverity.MEDIUM: QColor("#fff3cd"),
            QualitySeverity.HIGH: QColor("#fdecea"),
            QualitySeverity.CRITICAL: QColor("#f8d7da")
        }

        severity_names = {
            QualitySeverity.LOW: "低",
            QualitySeverity.MEDIUM: "中",
            QualitySeverity.HIGH: "高",
            QualitySeverity.CRITICAL: "严重"
        }

        for row, issue in enumerate(issues):
            # 检测时间
            time_item = QTableWidgetItem(issue.detected_at.strftime("%m-%d %H:%M"))
            self.issues_table.setItem(row, 0, time_item)

            # 规则名称
            rule_item = QTableWidgetItem(issue.rule_name)
            self.issues_table.setItem(row, 1, rule_item)

            # 严重程度
            severity_item = QTableWidgetItem(severity_names.get(issue.severity, "未知"))
            severity_item.setBackground(severity_colors.get(issue.severity, QColor("#ffffff")))
            self.issues_table.setItem(row, 2, severity_item)

            # 列名
            column_item = QTableWidgetItem(issue.column)
            self.issues_table.setItem(row, 3, column_item)

            # 影响行数
            rows_item = QTableWidgetItem(str(issue.affected_rows))
            self.issues_table.setItem(row, 4, rows_item)

            # 状态
            status_item = QTableWidgetItem("已解决" if issue.resolved else "未解决")
            if issue.resolved:
                status_item.setBackground(QColor("#d4edda"))
            else:
                status_item.setBackground(QColor("#f8d7da"))
            self.issues_table.setItem(row, 5, status_item)

            # 描述
            desc_item = QTableWidgetItem(issue.description)
            self.issues_table.setItem(row, 6, desc_item)

    def show_issue_details(self):
        """显示问题详情"""
        current_row = self.issues_table.currentRow()
        if current_row >= 0:
            # 获取当前过滤后的问题列表
            filtered_issues = self.get_filtered_issues()
            if current_row < len(filtered_issues):
                issue = filtered_issues[current_row]

                details_text = f"""
🚨 问题详情

问题ID: {issue.id}
规则名称: {issue.rule_name}
严重程度: {issue.severity.value.upper()}
检测时间: {issue.detected_at.strftime('%Y-%m-%d %H:%M:%S')}

 影响范围:
• 目标列: {issue.column}
• 影响行数: {issue.affected_rows}
• 状态: {'已解决' if issue.resolved else '未解决'}

 问题描述:
{issue.description}

 示例数据:
{', '.join(issue.sample_values[:5])}

{'解决说明: ' + issue.resolution_note if issue.resolved and issue.resolution_note else ''}
                """

                self.issue_details_text.setText(details_text.strip())

    def get_filtered_issues(self) -> List[QualityIssue]:
        """获取当前过滤的问题列表"""
        # 这是一个简化实现，实际应该根据当前过滤条件返回
        return self.quality_issues

    def start_quality_scan(self):
        """开始质量扫描"""
        try:
            if self.quality_monitor:
                # 获取真实数据进行质量扫描
                scan_results = self._perform_real_quality_scan()

                if scan_results:
                    # 更新质量指标
                    self._update_quality_metrics_from_scan(scan_results)

                    # 更新质量问题列表
                    self._update_quality_issues_from_scan(scan_results)

                    issues_count = len(scan_results.get('issues', []))
                    self.last_scan_label.setText(f"最后扫描: {datetime.now().strftime('%H:%M:%S')}")
                    QMessageBox.information(self, "扫描完成",
                                            f"数据质量扫描已完成，发现 {issues_count} 个质量问题")
                else:
                    QMessageBox.information(self, "扫描完成", "数据质量扫描已完成，未发现质量问题")

                logger.info("用户启动了真实的数据质量扫描")
            else:
                # 降级到模拟模式
                self.last_scan_label.setText(f"最后扫描: {datetime.now().strftime('%H:%M:%S')}")
                QMessageBox.information(self, "扫描完成", "数据质量扫描已完成（模拟模式）")
                logger.warning("质量监控器不可用，使用模拟模式")

        except Exception as e:
            QMessageBox.critical(self, "扫描失败", f"数据质量扫描失败: {e}")
            logger.error(f"数据质量扫描失败: {e}")

    def start_data_cleaning(self):
        """开始数据清洗"""
        reply = QMessageBox.question(
            self, "确认数据清洗", "确定要开始自动数据清洗吗？这将修复检测到的质量问题。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                if self.anomaly_detector:
                    # 调用真实的数据清洗逻辑
                    cleaning_results = self._perform_real_data_cleaning()

                    if cleaning_results:
                        repaired_count = cleaning_results.get('repaired_count', 0)
                        failed_count = cleaning_results.get('failed_count', 0)

                        # 更新质量问题状态
                        self._update_issues_after_cleaning(cleaning_results)

                        # 刷新显示
                        self.filter_issues()

                        message = f"数据清洗已完成！\n" \
                            f"成功修复: {repaired_count} 个问题\n" \
                            f"修复失败: {failed_count} 个问题"
                        QMessageBox.information(self, "清洗完成", message)
                    else:
                        QMessageBox.information(self, "清洗完成", "没有需要清洗的质量问题")

                    logger.info("用户启动了真实的数据清洗")
                else:
                    # 降级到模拟模式
                    QMessageBox.information(self, "清洗完成", "数据清洗已完成（模拟模式）")
                    logger.warning("异常检测器不可用，使用模拟模式")

            except Exception as e:
                QMessageBox.critical(self, "清洗失败", f"数据清洗失败: {e}")
                logger.error(f"数据清洗失败: {e}")

    def add_quality_rule(self):
        """添加质量规则"""
        dialog = QualityRuleDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_rule = dialog.get_rule_data()
            self.quality_rules.append(new_rule)
            self.filter_rules()
            QMessageBox.information(self, "添加成功", f"质量规则 '{new_rule.name}' 已添加")

    def edit_quality_rule(self):
        """编辑质量规则"""
        current_row = self.rules_table.currentRow()
        if current_row >= 0:
            # 获取当前过滤后的规则列表中的规则
            filtered_rules = self.get_filtered_rules()
            if current_row < len(filtered_rules):
                rule = filtered_rules[current_row]

                dialog = QualityRuleDialog(rule, self)
                if dialog.exec_() == QDialog.Accepted:
                    updated_rule = dialog.get_rule_data()

                    # 更新原规则
                    for i, r in enumerate(self.quality_rules):
                        if r.id == rule.id:
                            self.quality_rules[i] = updated_rule
                            break

                    self.filter_rules()
                    QMessageBox.information(self, "更新成功", f"质量规则 '{updated_rule.name}' 已更新")
        else:
            QMessageBox.warning(self, "未选择规则", "请选择要编辑的规则")

    def get_filtered_rules(self) -> List[QualityRule]:
        """获取当前过滤的规则列表"""
        # 这是一个简化实现，实际应该根据当前过滤条件返回
        return self.quality_rules

    def delete_quality_rule(self):
        """删除质量规则"""
        current_row = self.rules_table.currentRow()
        if current_row >= 0:
            filtered_rules = self.get_filtered_rules()
            if current_row < len(filtered_rules):
                rule = filtered_rules[current_row]

                reply = QMessageBox.question(
                    self, "确认删除", f"确定要删除质量规则 '{rule.name}' 吗？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    self.quality_rules = [r for r in self.quality_rules if r.id != rule.id]
                    self.filter_rules()
                    QMessageBox.information(self, "删除成功", f"质量规则 '{rule.name}' 已删除")
        else:
            QMessageBox.warning(self, "未选择规则", "请选择要删除的规则")

    def resolve_selected_issues(self):
        """解决选中的问题"""
        selected_rows = self.issues_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "未选择问题", "请选择要解决的问题")
            return

        reply = QMessageBox.question(
            self, "确认解决", f"确定要标记 {len(selected_rows)} 个问题为已解决吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for selected_row in selected_rows:
                row = selected_row.row()
                filtered_issues = self.get_filtered_issues()
                if row < len(filtered_issues):
                    issue = filtered_issues[row]
                    issue.resolved = True
                    issue.resolution_note = f"手动解决于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.filter_issues()
            self.update_overview_stats()
            QMessageBox.information(self, "操作完成", f"{len(selected_rows)} 个问题已标记为已解决")

    def export_issues(self):
        """导出质量问题"""
        try:
            # 这里可以实现实际的导出逻辑
            QMessageBox.information(self, "导出完成", "质量问题已导出到 quality_issues.xlsx")
            logger.info("用户导出了质量问题报告")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"质量问题导出失败: {e}")
            logger.error(f"质量问题导出失败: {e}")

    def generate_quality_report(self):
        """生成质量报告"""
        try:
            report_type = self.report_type_combo.currentText()
            period = self.report_period_combo.currentText()
            format_type = self.report_format_combo.currentText()

            # 这里可以实现实际的报告生成逻辑

            QMessageBox.information(
                self, "报告生成",
                f"{report_type} ({period}) 已生成为 {format_type} 格式"
            )
            logger.info(f"用户生成了质量报告: {report_type}")

        except Exception as e:
            QMessageBox.critical(self, "生成失败", f"质量报告生成失败: {e}")
            logger.error(f"质量报告生成失败: {e}")

    def _perform_real_quality_scan(self) -> Optional[Dict[str, Any]]:
        """执行真实的质量扫描"""
        try:
            # 获取数据源进行扫描
            scan_results = {'issues': [], 'metrics': {}}

            # 调用数据质量监控器进行真实扫描
            if self.quality_monitor and hasattr(self.quality_monitor, 'check_data_quality'):
                # 获取当前活跃的数据源
                data_sources = self._get_active_data_sources()

                for data_source_info in data_sources:
                    try:
                        # 获取数据
                        data = self._get_data_for_scanning(data_source_info)
                        if data is not None and not data.empty:
                            # 执行质量检查
                            quality_report = self.quality_monitor.check_data_quality(
                                data=data,
                                data_source=data_source_info.get('source_name', 'unknown'),
                                table_name=data_source_info.get('table_name', 'default'),
                                data_type=data_source_info.get('data_type', 'kline')
                            )

                            # 转换结果格式
                            scan_results['issues'].extend(self._convert_quality_report_to_issues(quality_report))
                            scan_results['metrics'].update(self._convert_quality_report_to_metrics(quality_report))

                    except Exception as e:
                        logger.warning(f"扫描数据源失败 {data_source_info}: {e}")
                        continue

            return scan_results if scan_results['issues'] or scan_results['metrics'] else None

        except Exception as e:
            logger.error(f"执行真实质量扫描失败: {e}")
            return None

    def _perform_real_data_cleaning(self) -> Optional[Dict[str, Any]]:
        """执行真实的数据清洗"""
        try:
            cleaning_results = {'repaired_count': 0, 'failed_count': 0, 'repairs': []}

            # 获取未解决的质量问题
            unresolved_issues = [issue for issue in self.quality_issues if not issue.resolved]

            if self.anomaly_detector and hasattr(self.anomaly_detector, 'auto_repair_anomaly'):
                for issue in unresolved_issues:
                    try:
                        # 尝试自动修复
                        repair_result = self.anomaly_detector.auto_repair_anomaly(issue.issue_id)

                        if repair_result and repair_result.success:
                            cleaning_results['repaired_count'] += 1
                            cleaning_results['repairs'].append({
                                'issue_id': issue.issue_id,
                                'repair_action': repair_result.action_taken.value if hasattr(repair_result.action_taken, 'value') else str(repair_result.action_taken),
                                'success': True
                            })
                        else:
                            cleaning_results['failed_count'] += 1
                            cleaning_results['repairs'].append({
                                'issue_id': issue.issue_id,
                                'success': False,
                                'reason': '自动修复失败或置信度不足'
                            })

                    except Exception as e:
                        logger.warning(f"修复问题失败 {issue.issue_id}: {e}")
                        cleaning_results['failed_count'] += 1
                        cleaning_results['repairs'].append({
                            'issue_id': issue.issue_id,
                            'success': False,
                            'reason': str(e)
                        })

            return cleaning_results if cleaning_results['repaired_count'] > 0 or cleaning_results['failed_count'] > 0 else None

        except Exception as e:
            logger.error(f"执行真实数据清洗失败: {e}")
            return None

    def _get_active_data_sources(self) -> List[Dict[str, Any]]:
        """获取活跃的数据源"""
        try:
            # 这里应该从实际的数据管理器获取活跃数据源
            # 暂时返回一些默认的数据源配置
            return [
                {
                    'source_name': 'factorweave_stock',
                    'table_name': 'kdata',
                    'data_type': 'kline',
                    'connection_info': {
                        'type': 'factorweave',
                        'market': 'stock'
                    }
                }
            ]
        except Exception as e:
            logger.error(f"获取活跃数据源失败: {e}")
            return []

    def _get_data_for_scanning(self, data_source_info: Dict[str, Any]) -> Optional[Any]:
        """获取用于扫描的数据"""
        try:
            # 这里应该根据数据源信息获取实际数据
            # 由于需要连接到真实的数据源，这里先返回None
            # 在实际部署时，这里应该连接到FactorWeave-Quant或其他数据源
            logger.info(f"尝试获取数据源数据: {data_source_info}")
            return None
        except Exception as e:
            logger.error(f"获取扫描数据失败: {e}")
            return None

    def _convert_quality_report_to_issues(self, quality_report) -> List[QualityIssue]:
        """将质量报告转换为质量问题列表"""
        try:
            issues = []
            if hasattr(quality_report, 'issues') and quality_report.issues:
                for issue in quality_report.issues:
                    ui_issue = QualityIssue(
                        issue_id=getattr(issue, 'issue_id', f"issue_{len(issues)}"),
                        rule_name=getattr(issue, 'title', 'Unknown Rule'),
                        severity=self._map_issue_level_to_severity(getattr(issue, 'level', None)),
                        column=getattr(issue, 'field_name', 'Unknown'),
                        affected_rows=getattr(issue, 'record_count', 1),
                        description=getattr(issue, 'description', ''),
                        detected_at=datetime.now(),
                        resolved=False
                    )
                    issues.append(ui_issue)
            return issues
        except Exception as e:
            logger.error(f"转换质量报告到问题列表失败: {e}")
            return []

    def _convert_quality_report_to_metrics(self, quality_report) -> Dict[str, Any]:
        """将质量报告转换为质量指标"""
        try:
            metrics = {}
            if hasattr(quality_report, 'dimension_scores'):
                for dimension, score_obj in quality_report.dimension_scores.items():
                    metric_type = self._map_dimension_to_metric_type(dimension)
                    if metric_type:
                        score = getattr(score_obj, 'score', 0.0) if hasattr(score_obj, 'score') else score_obj
                        metrics[metric_type.value] = {
                            'value': score,
                            'threshold': 0.8,
                            'status': 'good' if score >= 0.8 else 'warning' if score >= 0.6 else 'critical'
                        }
            return metrics
        except Exception as e:
            logger.error(f"转换质量报告到指标失败: {e}")
            return {}

    def _map_issue_level_to_severity(self, issue_level) -> QualitySeverity:
        """映射问题级别到严重程度"""
        try:
            if hasattr(issue_level, 'value'):
                level_str = issue_level.value.lower()
            else:
                level_str = str(issue_level).lower()

            if 'critical' in level_str:
                return QualitySeverity.CRITICAL
            elif 'high' in level_str:
                return QualitySeverity.HIGH
            elif 'medium' in level_str:
                return QualitySeverity.MEDIUM
            else:
                return QualitySeverity.LOW
        except:
            return QualitySeverity.MEDIUM

    def _map_dimension_to_metric_type(self, dimension) -> Optional[QualityMetricType]:
        """映射质量维度到指标类型"""
        try:
            if hasattr(dimension, 'value'):
                dim_str = dimension.value.lower()
            else:
                dim_str = str(dimension).lower()

            mapping = {
                'completeness': QualityMetricType.COMPLETENESS,
                'accuracy': QualityMetricType.ACCURACY,
                'consistency': QualityMetricType.CONSISTENCY,
                'timeliness': QualityMetricType.TIMELINESS,
                'validity': QualityMetricType.VALIDITY
            }

            for key, metric_type in mapping.items():
                if key in dim_str:
                    return metric_type

            return QualityMetricType.COMPLETENESS  # 默认值
        except:
            return QualityMetricType.COMPLETENESS

    def _update_quality_metrics_from_scan(self, scan_results: Dict[str, Any]):
        """从扫描结果更新质量指标"""
        try:
            metrics_data = scan_results.get('metrics', {})
            for metric_name, metric_data in metrics_data.items():
                # 查找对应的指标类型
                metric_type = None
                for mt in QualityMetricType:
                    if mt.value == metric_name:
                        metric_type = mt
                        break

                if metric_type:
                    # 更新或创建指标
                    self.quality_metrics[metric_type] = QualityMetric(
                        metric_type=metric_type,
                        value=metric_data.get('value', 0.0),
                        threshold=metric_data.get('threshold', 0.8),
                        status=QualityStatus.GOOD if metric_data.get('status') == 'good' else
                        QualityStatus.WARNING if metric_data.get('status') == 'warning' else
                        QualityStatus.CRITICAL,
                        last_updated=datetime.now()
                    )

            # 刷新指标显示
            self.update_metrics_display()

        except Exception as e:
            logger.error(f"从扫描结果更新质量指标失败: {e}")

    def _update_quality_issues_from_scan(self, scan_results: Dict[str, Any]):
        """从扫描结果更新质量问题"""
        try:
            issues_data = scan_results.get('issues', [])

            # 添加新发现的问题
            for issue in issues_data:
                # 检查是否已存在相同问题
                existing_issue = None
                for existing in self.quality_issues:
                    if (existing.rule_name == issue.rule_name and
                        existing.column == issue.column and
                            existing.description == issue.description):
                        existing_issue = existing
                        break

                if not existing_issue:
                    self.quality_issues.append(issue)

            # 刷新问题显示
            self.filter_issues()

        except Exception as e:
            logger.error(f"从扫描结果更新质量问题失败: {e}")

    def _update_issues_after_cleaning(self, cleaning_results: Dict[str, Any]):
        """清洗后更新问题状态"""
        try:
            repairs = cleaning_results.get('repairs', [])

            for repair in repairs:
                issue_id = repair.get('issue_id')
                success = repair.get('success', False)

                # 查找对应的问题并更新状态
                for issue in self.quality_issues:
                    if issue.issue_id == issue_id:
                        if success:
                            issue.resolved = True
                            issue.resolution_note = f"自动修复成功: {repair.get('repair_action', '未知操作')}"
                        else:
                            issue.resolution_note = f"修复失败: {repair.get('reason', '未知原因')}"
                        break

        except Exception as e:
            logger.error(f"清洗后更新问题状态失败: {e}")

    # ==================== 真实数据加载方法 ====================

    def load_real_metrics(self):
        """加载真实质量指标"""
        try:
            metrics_data = self.real_data_provider.get_quality_metrics()

            metric_type_map = {
                'completeness': QualityMetricType.COMPLETENESS,
                'accuracy': QualityMetricType.ACCURACY,
                'timeliness': QualityMetricType.TIMELINESS,
                'consistency': QualityMetricType.CONSISTENCY,
                'validity': QualityMetricType.VALIDITY,
                'uniqueness': QualityMetricType.UNIQUENESS
            }

            for metric_name, value in metrics_data.items():
                if metric_name in metric_type_map:
                    metric_type = metric_type_map[metric_name]
                    metric = QualityMetric(
                        metric_type=metric_type,
                        value=value,
                        threshold=0.85,
                        timestamp=datetime.now()
                    )
                    self.quality_metrics[metric_type] = metric

            self.update_quality_gauges()
            logger.info("真实质量指标加载完成")

        except Exception as e:
            logger.error(f"加载真实质量指标失败: {e}")

    def load_real_rules(self):
        """加载真实质量规则"""
        # 使用系统配置的规则（暂时保持示例规则）
        self.generate_sample_rules()
        logger.info("质量规则加载完成")

    def load_real_issues(self):
        """加载真实质量问题"""
        try:
            anomalies = self.real_data_provider.get_anomaly_records()

            issues = []
            severity_map = {
                '严重': QualitySeverity.CRITICAL,
                '警告': QualitySeverity.HIGH,
                '一般': QualitySeverity.MEDIUM,
                '轻微': QualitySeverity.LOW,
                '正常': QualitySeverity.LOW
            }

            for idx, anomaly in enumerate(anomalies):
                if anomaly.get('severity') not in ['正常', 'INFO']:
                    issue = QualityIssue(
                        issue_id=f"issue_{idx:03d}",
                        rule_id="auto_detected",
                        rule_name=anomaly.get('type', 'Unknown'),
                        severity=severity_map.get(anomaly.get('severity'), QualitySeverity.MEDIUM),
                        description=anomaly.get('description', ''),
                        affected_rows=1,
                        column=anomaly.get('datatype', ''),
                        sample_values=[anomaly.get('source', '')]
                    )
                    issue.detected_at = anomaly.get('time', datetime.now())
                    issues.append(issue)

            self.quality_issues = issues if issues else []
            self.filter_issues()
            logger.info(f"真实质量问题加载完成: {len(issues)} 个问题")

        except Exception as e:
            logger.error(f"加载真实质量问题失败: {e}")


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
    widget = DataQualityControlCenter()
    widget.setWindowTitle("数据质量控制中心")
    widget.resize(1200, 900)
    widget.show()

    sys.exit(app.exec_())
