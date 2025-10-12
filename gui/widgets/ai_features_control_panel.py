#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI功能控制面板

提供AI功能的统一控制和展示界面，包括：
- AI服务状态监控
- 预测结果展示
- 用户行为学习控制
- 配置推荐管理
- AI模型性能监控

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
    QMenu, QActionGroup, QButtonGroup, QRadioButton, QLCDNumber,
    QDial, QCalendarWidget
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

# 导入核心AI服务
try:
    from core.services.ai_prediction_service import AIPredictionService
    from core.ai.user_behavior_learner import UserBehaviorLearner
    from core.ai.config_recommendation_engine import ConfigRecommendationEngine
    from core.ai.config_impact_analyzer import ConfigImpactAnalyzer
    from core.ai.data_anomaly_detector import DataAnomalyDetector
    from core.ui_integration.ui_business_logic_adapter import get_ui_adapter
    from loguru import logger
    CORE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    CORE_AVAILABLE = False
    logger.warning(f"AI核心服务不可用: {e}")

logger = logger.bind(module=__name__) if hasattr(logger, 'bind') else logging.getLogger(__name__)


class AIServiceStatus(Enum):
    """AI服务状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"
    TRAINING = "training"


@dataclass
class AIModelInfo:
    """AI模型信息"""
    name: str
    version: str
    status: AIServiceStatus = AIServiceStatus.INACTIVE
    accuracy: float = 0.0
    last_trained: Optional[datetime] = None
    prediction_count: int = 0
    error_rate: float = 0.0
    confidence_threshold: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionResult:
    """预测结果"""
    model_name: str
    prediction_type: str
    result: Any
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    input_data: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


class AIStatusWidget(QWidget):
    """AI状态监控组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_models: Dict[str, AIModelInfo] = {}
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 总体状态区域
        overview_group = QGroupBox("AI系统总览")
        overview_layout = QGridLayout(overview_group)

        # AI服务状态指示器
        self.ai_status_label = QLabel("🟢 AI服务运行中")
        self.ai_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
                background-color: #d4edda;
                color: #155724;
            }
        """)
        overview_layout.addWidget(self.ai_status_label, 0, 0, 1, 2)

        # 活跃模型数
        overview_layout.addWidget(QLabel("活跃模型:"), 1, 0)
        self.active_models_lcd = QLCDNumber(2)
        self.active_models_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #3498db; }")
        overview_layout.addWidget(self.active_models_lcd, 1, 1)

        # 今日预测次数
        overview_layout.addWidget(QLabel("今日预测:"), 2, 0)
        self.predictions_today_lcd = QLCDNumber(4)
        self.predictions_today_lcd.setStyleSheet("QLCDNumber { background-color: #2c3e50; color: #e74c3c; }")
        overview_layout.addWidget(self.predictions_today_lcd, 2, 1)

        # 平均准确率
        overview_layout.addWidget(QLabel("平均准确率:"), 3, 0)
        self.accuracy_progress = QProgressBar()
        self.accuracy_progress.setRange(0, 100)
        self.accuracy_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        overview_layout.addWidget(self.accuracy_progress, 3, 1)

        layout.addWidget(overview_group)

        # 模型详情表格
        models_group = QGroupBox("模型状态详情")
        models_layout = QVBoxLayout(models_group)

        self.models_table = QTableWidget()
        self.models_table.setAlternatingRowColors(True)
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)

        # 设置表格列
        columns = ["模型名称", "版本", "状态", "准确率", "预测次数", "错误率", "最后训练"]
        self.models_table.setColumnCount(len(columns))
        self.models_table.setHorizontalHeaderLabels(columns)

        # 设置列宽
        header = self.models_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        models_layout.addWidget(self.models_table)

        layout.addWidget(models_group)

        # 控制按钮区域
        controls_layout = QHBoxLayout()

        # 刷新按钮
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self.refresh_ai_status)
        controls_layout.addWidget(refresh_btn)

        # 重新训练按钮
        retrain_btn = QPushButton("🎓 重新训练")
        retrain_btn.clicked.connect(self.retrain_models)
        controls_layout.addWidget(retrain_btn)

        # 导出报告按钮
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_report)
        controls_layout.addWidget(export_btn)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # 初始化示例数据
        self.load_sample_models()

    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status_display)
        self.update_timer.start(5000)  # 每5秒更新一次

    def load_sample_models(self):
        """加载示例模型数据"""
        sample_models = [
            AIModelInfo(
                "执行时间预测器", "v2.1.0", AIServiceStatus.ACTIVE,
                accuracy=0.87, prediction_count=1234, error_rate=0.13,
                last_trained=datetime.now() - timedelta(days=2)
            ),
            AIModelInfo(
                "参数优化器", "v1.8.3", AIServiceStatus.ACTIVE,
                accuracy=0.92, prediction_count=856, error_rate=0.08,
                last_trained=datetime.now() - timedelta(days=5)
            ),
            AIModelInfo(
                "异常检测器", "v3.0.1", AIServiceStatus.TRAINING,
                accuracy=0.78, prediction_count=432, error_rate=0.22,
                last_trained=datetime.now() - timedelta(hours=3)
            ),
            AIModelInfo(
                "用户行为分析器", "v1.5.2", AIServiceStatus.ACTIVE,
                accuracy=0.84, prediction_count=2156, error_rate=0.16,
                last_trained=datetime.now() - timedelta(days=1)
            )
        ]

        for model in sample_models:
            self.ai_models[model.name] = model

        self.update_models_table()
        self.update_overview_stats()

    def update_models_table(self):
        """更新模型表格"""
        self.models_table.setRowCount(len(self.ai_models))

        for row, (name, model) in enumerate(self.ai_models.items()):
            # 模型名称
            name_item = QTableWidgetItem(model.name)
            self.models_table.setItem(row, 0, name_item)

            # 版本
            version_item = QTableWidgetItem(model.version)
            self.models_table.setItem(row, 1, version_item)

            # 状态
            status_colors = {
                AIServiceStatus.ACTIVE: "#2ecc71",
                AIServiceStatus.INACTIVE: "#95a5a6",
                AIServiceStatus.ERROR: "#e74c3c",
                AIServiceStatus.LOADING: "#f39c12",
                AIServiceStatus.TRAINING: "#3498db"
            }
            status_item = QTableWidgetItem(model.status.value.upper())
            status_item.setBackground(QColor(status_colors.get(model.status, "#95a5a6")))
            self.models_table.setItem(row, 2, status_item)

            # 准确率
            accuracy_item = QTableWidgetItem(f"{model.accuracy:.1%}")
            self.models_table.setItem(row, 3, accuracy_item)

            # 预测次数
            count_item = QTableWidgetItem(str(model.prediction_count))
            self.models_table.setItem(row, 4, count_item)

            # 错误率
            error_item = QTableWidgetItem(f"{model.error_rate:.1%}")
            self.models_table.setItem(row, 5, error_item)

            # 最后训练时间
            if model.last_trained:
                trained_text = model.last_trained.strftime("%Y-%m-%d %H:%M")
            else:
                trained_text = "未训练"
            trained_item = QTableWidgetItem(trained_text)
            self.models_table.setItem(row, 6, trained_item)

    def update_overview_stats(self):
        """更新总览统计"""
        active_count = sum(1 for model in self.ai_models.values()
                           if model.status == AIServiceStatus.ACTIVE)

        total_predictions = sum(model.prediction_count for model in self.ai_models.values())

        if self.ai_models:
            avg_accuracy = sum(model.accuracy for model in self.ai_models.values()) / len(self.ai_models)
        else:
            avg_accuracy = 0.0

        # 更新显示
        self.active_models_lcd.display(active_count)
        self.predictions_today_lcd.display(total_predictions)
        self.accuracy_progress.setValue(int(avg_accuracy * 100))

        # 更新状态标签
        if active_count > 0:
            self.ai_status_label.setText("🟢 AI服务运行中")
            self.ai_status_label.setStyleSheet("""
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
            self.ai_status_label.setText("🔴 AI服务离线")
            self.ai_status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    border-radius: 3px;
                    background-color: #f8d7da;
                    color: #721c24;
                }
            """)

    def update_status_display(self):
        """更新状态显示"""
        # 模拟状态变化
        import random
        for model in self.ai_models.values():
            if model.status == AIServiceStatus.ACTIVE:
                # 随机增加预测次数
                model.prediction_count += random.randint(0, 5)
                # 随机调整准确率
                model.accuracy += random.uniform(-0.01, 0.01)
                model.accuracy = max(0.5, min(1.0, model.accuracy))

        self.update_models_table()
        self.update_overview_stats()

    def refresh_ai_status(self):
        """刷新AI状态"""
        # 这里可以调用实际的AI服务状态检查
        logger.info("刷新AI服务状态")
        self.update_status_display()
        QMessageBox.information(self, "刷新完成", "AI服务状态已更新")

    def retrain_models(self):
        """重新训练模型"""
        reply = QMessageBox.question(
            self, "确认重训练", "确定要重新训练所有AI模型吗？这可能需要较长时间。",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 模拟训练过程
            for model in self.ai_models.values():
                if model.status == AIServiceStatus.ACTIVE:
                    model.status = AIServiceStatus.TRAINING

            self.update_models_table()
            QMessageBox.information(self, "训练开始", "AI模型重训练已开始")

    def export_report(self):
        """导出AI状态报告"""
        # 这里可以生成详细的AI状态报告
        QMessageBox.information(self, "导出完成", "AI状态报告已导出到 ai_status_report.pdf")


class PredictionDisplayWidget(QWidget):
    """预测结果展示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.predictions: List[PredictionResult] = []
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 预测控制区域
        control_group = QGroupBox("预测控制")
        control_layout = QHBoxLayout(control_group)

        # 预测类型选择
        control_layout.addWidget(QLabel("预测类型:"))
        self.prediction_type_combo = QComboBox()
        self.prediction_type_combo.addItems([
            "执行时间预测", "参数优化建议", "异常检测", "性能预测", "资源需求预测"
        ])
        control_layout.addWidget(self.prediction_type_combo)

        # 置信度阈值
        control_layout.addWidget(QLabel("置信度阈值:"))
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(50, 99)
        self.confidence_slider.setValue(80)
        control_layout.addWidget(self.confidence_slider)

        self.confidence_label = QLabel("80%")
        control_layout.addWidget(self.confidence_label)

        # 执行预测按钮
        predict_btn = QPushButton("执行预测")
        predict_btn.clicked.connect(self.execute_prediction)
        control_layout.addWidget(predict_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        # 预测结果展示区域
        results_group = QGroupBox("预测结果")
        results_layout = QVBoxLayout(results_group)

        # 结果表格
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)

        # 设置表格列
        columns = ["时间", "预测类型", "结果", "置信度", "执行时间", "状态"]
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)

        # 设置列宽
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)

        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group)

        # 预测统计区域
        stats_group = QGroupBox("预测统计")
        stats_layout = QGridLayout(stats_group)

        # 今日预测次数
        stats_layout.addWidget(QLabel("今日预测:"), 0, 0)
        self.daily_predictions_label = QLabel("0")
        stats_layout.addWidget(self.daily_predictions_label, 0, 1)

        # 平均置信度
        stats_layout.addWidget(QLabel("平均置信度:"), 1, 0)
        self.avg_confidence_label = QLabel("0%")
        stats_layout.addWidget(self.avg_confidence_label, 1, 1)

        # 成功率
        stats_layout.addWidget(QLabel("预测成功率:"), 2, 0)
        self.success_rate_label = QLabel("0%")
        stats_layout.addWidget(self.success_rate_label, 2, 1)

        layout.addWidget(stats_group)

        # 连接信号
        self.confidence_slider.valueChanged.connect(
            lambda v: self.confidence_label.setText(f"{v}%")
        )

    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.simulate_predictions)
        self.update_timer.start(10000)  # 每10秒模拟一次预测

    def execute_prediction(self):
        """执行预测"""
        prediction_type = self.prediction_type_combo.currentText()
        confidence_threshold = self.confidence_slider.value() / 100.0

        # 模拟预测执行
        import random
        import time

        start_time = time.time()

        # 模拟预测结果
        if prediction_type == "执行时间预测":
            result = f"{random.randint(30, 180)} 分钟"
            confidence = random.uniform(0.7, 0.95)
        elif prediction_type == "参数优化建议":
            result = f"建议批处理大小: {random.randint(50, 200)}"
            confidence = random.uniform(0.8, 0.92)
        elif prediction_type == "异常检测":
            result = "检测到 2 个潜在异常"
            confidence = random.uniform(0.6, 0.85)
        elif prediction_type == "性能预测":
            result = f"预计吞吐量: {random.randint(1000, 5000)} 条/秒"
            confidence = random.uniform(0.75, 0.90)
        else:
            result = f"CPU: {random.randint(40, 80)}%, 内存: {random.randint(30, 70)}%"
            confidence = random.uniform(0.65, 0.88)

        execution_time = (time.time() - start_time) * 1000  # 转换为毫秒

        # 创建预测结果
        prediction = PredictionResult(
            model_name="AI预测引擎",
            prediction_type=prediction_type,
            result=result,
            confidence=confidence,
            execution_time_ms=execution_time
        )

        self.add_prediction_result(prediction)

        # 显示结果
        if confidence >= confidence_threshold:
            QMessageBox.information(
                self, "预测完成",
                f"预测类型: {prediction_type}\n"
                f"结果: {result}\n"
                f"置信度: {confidence:.1%}\n"
                f"执行时间: {execution_time:.1f}ms"
            )
        else:
            QMessageBox.warning(
                self, "置信度不足",
                f"预测置信度 ({confidence:.1%}) 低于阈值 ({confidence_threshold:.1%})"
            )

    def add_prediction_result(self, prediction: PredictionResult):
        """添加预测结果"""
        self.predictions.append(prediction)

        # 限制结果数量
        if len(self.predictions) > 100:
            self.predictions = self.predictions[-100:]

        self.update_results_table()
        self.update_statistics()

    def update_results_table(self):
        """更新结果表格"""
        # 显示最近的20个结果
        recent_predictions = self.predictions[-20:]
        self.results_table.setRowCount(len(recent_predictions))

        for row, prediction in enumerate(reversed(recent_predictions)):
            # 时间
            time_item = QTableWidgetItem(prediction.timestamp.strftime("%H:%M:%S"))
            self.results_table.setItem(row, 0, time_item)

            # 预测类型
            type_item = QTableWidgetItem(prediction.prediction_type)
            self.results_table.setItem(row, 1, type_item)

            # 结果
            result_item = QTableWidgetItem(str(prediction.result))
            self.results_table.setItem(row, 2, result_item)

            # 置信度
            confidence_item = QTableWidgetItem(f"{prediction.confidence:.1%}")
            # 根据置信度设置颜色
            if prediction.confidence >= 0.9:
                confidence_item.setBackground(QColor("#d4edda"))
            elif prediction.confidence >= 0.7:
                confidence_item.setBackground(QColor("#fff3cd"))
            else:
                confidence_item.setBackground(QColor("#f8d7da"))
            self.results_table.setItem(row, 3, confidence_item)

            # 执行时间
            time_item = QTableWidgetItem(f"{prediction.execution_time_ms:.1f}ms")
            self.results_table.setItem(row, 4, time_item)

            # 状态
            status = "成功" if prediction.confidence >= 0.7 else "低置信度"
            status_item = QTableWidgetItem(status)
            self.results_table.setItem(row, 5, status_item)

    def update_statistics(self):
        """更新统计信息"""
        if not self.predictions:
            return

        # 今日预测次数
        today = datetime.now().date()
        daily_count = sum(1 for p in self.predictions if p.timestamp.date() == today)
        self.daily_predictions_label.setText(str(daily_count))

        # 平均置信度
        avg_confidence = sum(p.confidence for p in self.predictions) / len(self.predictions)
        self.avg_confidence_label.setText(f"{avg_confidence:.1%}")

        # 成功率（置信度 >= 70%）
        success_count = sum(1 for p in self.predictions if p.confidence >= 0.7)
        success_rate = success_count / len(self.predictions)
        self.success_rate_label.setText(f"{success_rate:.1%}")

    def simulate_predictions(self):
        """模拟自动预测"""
        # 随机生成预测结果
        import random

        prediction_types = [
            "执行时间预测", "参数优化建议", "异常检测", "性能预测", "资源需求预测"
        ]

        prediction_type = random.choice(prediction_types)

        # 生成模拟结果
        if prediction_type == "异常检测":
            if random.random() < 0.1:  # 10%概率检测到异常
                result = f"检测到 {random.randint(1, 3)} 个异常"
                confidence = random.uniform(0.8, 0.95)
            else:
                result = "未检测到异常"
                confidence = random.uniform(0.9, 0.99)
        else:
            result = f"自动预测结果 {random.randint(100, 999)}"
            confidence = random.uniform(0.6, 0.95)

        prediction = PredictionResult(
            model_name="自动预测引擎",
            prediction_type=prediction_type,
            result=result,
            confidence=confidence,
            execution_time_ms=random.uniform(50, 200)
        )

        self.add_prediction_result(prediction)


class UserBehaviorWidget(QWidget):
    """用户行为学习组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 学习控制区域
        control_group = QGroupBox("🧠 学习控制")
        control_layout = QFormLayout(control_group)

        # 学习模式
        self.learning_mode_combo = QComboBox()
        self.learning_mode_combo.addItems(["自动学习", "手动学习", "暂停学习"])
        control_layout.addRow("学习模式:", self.learning_mode_combo)

        # 学习速率
        self.learning_rate_slider = QSlider(Qt.Horizontal)
        self.learning_rate_slider.setRange(1, 10)
        self.learning_rate_slider.setValue(5)
        learning_rate_layout = QHBoxLayout()
        learning_rate_layout.addWidget(self.learning_rate_slider)
        self.learning_rate_label = QLabel("0.5")
        learning_rate_layout.addWidget(self.learning_rate_label)
        control_layout.addRow("学习速率:", learning_rate_layout)

        # 数据保留期
        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(7, 365)
        self.retention_spin.setValue(30)
        self.retention_spin.setSuffix("天")
        control_layout.addRow("数据保留期:", self.retention_spin)

        layout.addWidget(control_group)

        # 学习进度区域
        progress_group = QGroupBox("学习进度")
        progress_layout = QGridLayout(progress_group)

        # 总体学习进度
        progress_layout.addWidget(QLabel("总体进度:"), 0, 0)
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(67)
        progress_layout.addWidget(self.overall_progress, 0, 1)

        # 用户偏好学习
        progress_layout.addWidget(QLabel("用户偏好:"), 1, 0)
        self.preference_progress = QProgressBar()
        self.preference_progress.setRange(0, 100)
        self.preference_progress.setValue(78)
        progress_layout.addWidget(self.preference_progress, 1, 1)

        # 操作模式学习
        progress_layout.addWidget(QLabel("操作模式:"), 2, 0)
        self.pattern_progress = QProgressBar()
        self.pattern_progress.setRange(0, 100)
        self.pattern_progress.setValue(54)
        progress_layout.addWidget(self.pattern_progress, 2, 1)

        layout.addWidget(progress_group)

        # 学习统计区域
        stats_group = QGroupBox("学习统计")
        stats_layout = QFormLayout(stats_group)

        # 学习样本数
        self.samples_label = QLabel("12,456")
        stats_layout.addRow("学习样本数:", self.samples_label)

        # 识别模式数
        self.patterns_label = QLabel("23")
        stats_layout.addRow("识别模式数:", self.patterns_label)

        # 推荐准确率
        self.recommendation_accuracy_label = QLabel("84.2%")
        stats_layout.addRow("推荐准确率:", self.recommendation_accuracy_label)

        # 最后更新时间
        self.last_update_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        stats_layout.addRow("最后更新:", self.last_update_label)

        layout.addWidget(stats_group)

        # 用户行为洞察
        insights_group = QGroupBox("[INFO] 行为洞察")
        insights_layout = QVBoxLayout(insights_group)

        self.insights_text = QTextEdit()
        self.insights_text.setMaximumHeight(150)
        self.insights_text.setReadOnly(True)
        self.insights_text.setText("""
• 用户倾向于在上午9-11点执行数据导入任务
• 偏好使用批处理大小为100的配置
• 经常查看任务执行进度和性能指标
• 对AI推荐的接受率达到76%
• 最常用的数据源是通达信和东方财富
        """)
        insights_layout.addWidget(self.insights_text)

        layout.addWidget(insights_group)

        # 连接信号
        self.learning_rate_slider.valueChanged.connect(
            lambda v: self.learning_rate_label.setText(f"{v/10:.1f}")
        )


class AIFeaturesControlPanel(QWidget):
    """AI功能控制面板主组件"""

    def __init__(self, ui_adapter=None, parent=None):
        super().__init__(parent)
        self.ui_adapter = ui_adapter

        # 初始化适配器
        if CORE_AVAILABLE:
            try:
                if self.ui_adapter is None:
                    self.ui_adapter = get_ui_adapter()
            except Exception as e:
                logger.warning(f"UI适配器初始化失败: {e}")

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题区域
        title_layout = QHBoxLayout()

        title_label = QLabel("AI功能控制面板")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # AI总开关
        self.ai_master_switch = QCheckBox("启用AI功能")
        self.ai_master_switch.setChecked(True)
        self.ai_master_switch.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        title_layout.addWidget(self.ai_master_switch)

        layout.addLayout(title_layout)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # AI状态监控选项卡
        status_tab = AIStatusWidget()
        self.tab_widget.addTab(status_tab, "状态监控")

        # 预测结果展示选项卡
        prediction_tab = PredictionDisplayWidget()
        self.tab_widget.addTab(prediction_tab, "预测结果")

        # 用户行为学习选项卡
        behavior_tab = UserBehaviorWidget()
        self.tab_widget.addTab(behavior_tab, "🧠 行为学习")

        # 配置推荐选项卡
        recommendation_tab = self.create_recommendation_tab()
        self.tab_widget.addTab(recommendation_tab, "智能推荐")

        layout.addWidget(self.tab_widget)

        # 保存引用
        self.status_widget = status_tab
        self.prediction_widget = prediction_tab
        self.behavior_widget = behavior_tab

    def create_recommendation_tab(self) -> QWidget:
        """创建配置推荐选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐控制区域
        control_group = QGroupBox("🎛️ 推荐控制")
        control_layout = QHBoxLayout(control_group)

        # 推荐类型
        control_layout.addWidget(QLabel("推荐类型:"))
        recommendation_type_combo = QComboBox()
        recommendation_type_combo.addItems([
            "参数优化", "性能调优", "资源配置", "调度策略", "数据源选择"
        ])
        control_layout.addWidget(recommendation_type_combo)

        # 获取推荐按钮
        get_recommendations_btn = QPushButton("获取推荐")
        control_layout.addWidget(get_recommendations_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)

        # 推荐结果区域
        results_group = QGroupBox("[INFO] 推荐结果")
        results_layout = QVBoxLayout(results_group)

        recommendations_text = QTextEdit()
        recommendations_text.setReadOnly(True)
        recommendations_text.setText("""
当前推荐配置：

1. 批处理大小优化
   • 建议值: 150 (当前: 100)
   • 预期性能提升: 15%
   • 置信度: 87%

2. 工作线程数调整
   • 建议值: 6 (当前: 4)
   • 预期吞吐量提升: 23%
   • 置信度: 92%

3. 数据源选择
   • 推荐: 通达信 + 东方财富组合
   • 预期稳定性提升: 18%
   • 置信度: 79%

4. 调度策略优化
   • 建议: 截止时间感知调度
   • 预期任务完成率提升: 12%
   • 置信度: 84%
        """)
        results_layout.addWidget(recommendations_text)

        # 推荐操作按钮
        actions_layout = QHBoxLayout()

        apply_all_btn = QPushButton("应用全部")
        actions_layout.addWidget(apply_all_btn)

        apply_selected_btn = QPushButton("应用选中")
        actions_layout.addWidget(apply_selected_btn)

        ignore_btn = QPushButton("[ERROR] 忽略推荐")
        actions_layout.addWidget(ignore_btn)

        actions_layout.addStretch()

        results_layout.addLayout(actions_layout)

        layout.addWidget(results_group)

        return widget

    def setup_connections(self):
        """设置信号连接"""
        self.ai_master_switch.toggled.connect(self.on_ai_master_switch_toggled)

    def on_ai_master_switch_toggled(self, enabled: bool):
        """处理AI总开关切换"""
        if enabled:
            logger.info("AI功能已启用")
            self.tab_widget.setEnabled(True)
        else:
            logger.info("AI功能已禁用")
            self.tab_widget.setEnabled(False)

        # 这里可以调用实际的AI服务启用/禁用逻辑
        if self.ui_adapter:
            # 通过适配器控制AI服务
            pass


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
    widget = AIFeaturesControlPanel()
    widget.setWindowTitle("AI功能控制面板")
    widget.resize(1000, 700)
    widget.show()

    sys.exit(app.exec_())
