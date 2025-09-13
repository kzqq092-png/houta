#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能配置管理UI组件

提供智能配置管理的用户界面：
1. 配置推荐显示和应用
2. 配置冲突检测和解决
3. 配置模板管理
4. 智能优化设置
5. 性能反馈展示
"""

import sys
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar, QFrame, QSplitter,
    QTabWidget, QScrollArea, QGroupBox, QComboBox, QSpinBox,
    QCheckBox, QSlider, QTreeWidget, QTreeWidgetItem, QDialog,
    QDialogButtonBox, QLineEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from loguru import logger

try:
    from core.importdata.intelligent_config_manager import (
        IntelligentConfigManager, ConfigOptimizationLevel,
        ConfigRecommendationType, ConfigRecommendation, ConfigConflict
    )
    from core.importdata.import_config_manager import ImportTaskConfig
    INTELLIGENT_CONFIG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"智能配置组件不可用: {e}")
    INTELLIGENT_CONFIG_AVAILABLE = False


class ConfigRecommendationWorker(QThread):
    """配置推荐生成工作线程"""

    recommendations_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, config_manager: 'IntelligentConfigManager',
                 task_id: str, recommendation_type: 'ConfigRecommendationType'):
        super().__init__()
        self.config_manager = config_manager
        self.task_id = task_id
        self.recommendation_type = recommendation_type

    def run(self):
        try:
            recommendations = self.config_manager.generate_config_recommendations(
                self.task_id, self.recommendation_type
            )
            self.recommendations_ready.emit(recommendations)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ConflictDetectionWorker(QThread):
    """配置冲突检测工作线程"""

    conflicts_detected = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, config_manager: 'IntelligentConfigManager'):
        super().__init__()
        self.config_manager = config_manager

    def run(self):
        try:
            conflicts = self.config_manager.detect_config_conflicts()
            self.conflicts_detected.emit(conflicts)
        except Exception as e:
            self.error_occurred.emit(str(e))


class IntelligentConfigWidget(QWidget):
    """智能配置管理主界面"""

    config_optimized = pyqtSignal(str, dict)  # 配置优化完成信号
    recommendation_applied = pyqtSignal(str, str)  # 推荐应用信号
    conflict_resolved = pyqtSignal(str)  # 冲突解决信号

    def __init__(self, config_manager: Optional['IntelligentConfigManager'] = None, parent=None):
        super().__init__(parent)

        if not INTELLIGENT_CONFIG_AVAILABLE:
            self.setup_unavailable_ui()
            return

        self.config_manager = config_manager or IntelligentConfigManager()
        self.current_task_id = None
        self.recommendations = []
        self.conflicts = []

        self.setup_ui()
        self.setup_connections()
        self.load_initial_data()

        # 定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_statistics)
        self.refresh_timer.start(30000)  # 30秒刷新一次

        logger.info("智能配置管理界面初始化完成")

    def setup_unavailable_ui(self):
        """设置不可用时的UI"""
        layout = QVBoxLayout(self)

        label = QLabel("⚠️ 智能配置功能不可用")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 16))
        label.setStyleSheet("color: #ff6b6b; padding: 50px;")

        layout.addWidget(label)

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("🧠 智能配置管理中心")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_layout.addWidget(title_label)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_all_data)
        title_layout.addWidget(refresh_btn)

        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 1. 智能优化标签页
        self.create_optimization_tab()

        # 2. 配置推荐标签页
        self.create_recommendations_tab()

        # 3. 冲突检测标签页
        self.create_conflicts_tab()

        # 4. 配置模板标签页
        self.create_templates_tab()

        # 5. 统计信息标签页
        self.create_statistics_tab()

        # 状态栏
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; padding: 5px; border-top: 1px solid #ddd;")
        layout.addWidget(self.status_label)

    def create_optimization_tab(self):
        """创建智能优化标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 任务选择区域
        task_group = QGroupBox("任务选择")
        task_layout = QFormLayout(task_group)

        self.task_combo = QComboBox()
        self.task_combo.currentTextChanged.connect(self.on_task_selected)
        task_layout.addRow("选择任务:", self.task_combo)

        layout.addWidget(task_group)

        # 优化设置区域
        optimization_group = QGroupBox("优化设置")
        opt_layout = QGridLayout(optimization_group)

        # 优化级别
        opt_layout.addWidget(QLabel("优化级别:"), 0, 0)
        self.optimization_level_combo = QComboBox()
        self.optimization_level_combo.addItems(["保守", "平衡", "激进"])
        self.optimization_level_combo.setCurrentText("平衡")
        opt_layout.addWidget(self.optimization_level_combo, 0, 1)

        # 目标指标
        opt_layout.addWidget(QLabel("优化目标:"), 1, 0)
        self.optimization_target_combo = QComboBox()
        self.optimization_target_combo.addItems(["性能", "可靠性", "成本", "平衡"])
        self.optimization_target_combo.setCurrentText("平衡")
        opt_layout.addWidget(self.optimization_target_combo, 1, 1)

        # 执行优化按钮
        self.optimize_btn = QPushButton("🚀 执行智能优化")
        self.optimize_btn.clicked.connect(self.execute_optimization)
        opt_layout.addWidget(self.optimize_btn, 2, 0, 1, 2)

        layout.addWidget(optimization_group)

        # 优化结果显示
        result_group = QGroupBox("优化结果")
        result_layout = QVBoxLayout(result_group)

        self.optimization_result_text = QTextEdit()
        self.optimization_result_text.setReadOnly(True)
        self.optimization_result_text.setMaximumHeight(200)
        result_layout.addWidget(self.optimization_result_text)

        layout.addWidget(result_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "智能优化")

    def create_recommendations_tab(self):
        """创建配置推荐标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 控制区域
        control_layout = QHBoxLayout()

        # 推荐类型选择
        control_layout.addWidget(QLabel("推荐类型:"))
        self.recommendation_type_combo = QComboBox()
        self.recommendation_type_combo.addItems(["性能优化", "可靠性优化", "成本优化", "平衡优化"])
        control_layout.addWidget(self.recommendation_type_combo)

        # 生成推荐按钮
        self.generate_recommendations_btn = QPushButton("💡 生成推荐")
        self.generate_recommendations_btn.clicked.connect(self.generate_recommendations)
        control_layout.addWidget(self.generate_recommendations_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 推荐列表
        self.recommendations_table = QTableWidget()
        self.recommendations_table.setColumnCount(6)
        self.recommendations_table.setHorizontalHeaderLabels([
            "推荐类型", "配置变更", "预期改进", "置信度", "原因", "操作"
        ])

        header = self.recommendations_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        layout.addWidget(self.recommendations_table)

        self.tab_widget.addTab(tab, "配置推荐")

    def create_conflicts_tab(self):
        """创建冲突检测标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 控制区域
        control_layout = QHBoxLayout()

        self.detect_conflicts_btn = QPushButton("🔍 检测冲突")
        self.detect_conflicts_btn.clicked.connect(self.detect_conflicts)
        control_layout.addWidget(self.detect_conflicts_btn)

        self.auto_resolve_btn = QPushButton("🔧 自动解决")
        self.auto_resolve_btn.clicked.connect(self.auto_resolve_conflicts)
        control_layout.addWidget(self.auto_resolve_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 冲突列表
        self.conflicts_table = QTableWidget()
        self.conflicts_table.setColumnCount(6)
        self.conflicts_table.setHorizontalHeaderLabels([
            "冲突类型", "影响任务", "严重程度", "描述", "建议解决方案", "操作"
        ])

        header = self.conflicts_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)

        layout.addWidget(self.conflicts_table)

        self.tab_widget.addTab(tab, "冲突检测")

    def create_templates_tab(self):
        """创建配置模板标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 模板列表
        self.templates_tree = QTreeWidget()
        self.templates_tree.setHeaderLabels([
            "模板名称", "数据源", "资产类型", "频率", "成功率", "使用次数"
        ])

        header = self.templates_tree.header()
        header.setStretchLastSection(True)

        layout.addWidget(self.templates_tree)

        # 操作按钮
        button_layout = QHBoxLayout()

        create_template_btn = QPushButton("➕ 创建模板")
        create_template_btn.clicked.connect(self.create_template)
        button_layout.addWidget(create_template_btn)

        apply_template_btn = QPushButton("📋 应用模板")
        apply_template_btn.clicked.connect(self.apply_template)
        button_layout.addWidget(apply_template_btn)

        delete_template_btn = QPushButton("🗑️ 删除模板")
        delete_template_btn.clicked.connect(self.delete_template)
        button_layout.addWidget(delete_template_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "配置模板")

    def create_statistics_tab(self):
        """创建统计信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 统计信息显示
        self.statistics_text = QTextEdit()
        self.statistics_text.setReadOnly(True)
        layout.addWidget(self.statistics_text)

        self.tab_widget.addTab(tab, "统计信息")

    def setup_connections(self):
        """设置信号连接"""
        pass

    def load_initial_data(self):
        """加载初始数据"""
        try:
            # 加载任务列表
            self.refresh_task_list()

            # 加载统计信息
            self.refresh_statistics()

            # 加载配置模板
            self.refresh_templates()

        except Exception as e:
            logger.error(f"加载初始数据失败: {e}")
            self.show_error_message("加载数据失败", str(e))

    def refresh_task_list(self):
        """刷新任务列表"""
        try:
            self.task_combo.clear()

            all_tasks = self.config_manager.get_all_import_tasks()
            for task_id, task_config in all_tasks.items():
                self.task_combo.addItem(f"{task_config.name} ({task_id})", task_id)

        except Exception as e:
            logger.error(f"刷新任务列表失败: {e}")

    def refresh_statistics(self):
        """刷新统计信息"""
        try:
            stats = self.config_manager.get_intelligent_statistics()

            stats_text = "📊 智能配置统计信息\n\n"

            # 基本统计
            basic_stats = stats.get('intelligent_features', {})
            stats_text += "🔧 基本统计:\n"
            stats_text += f"  配置模板数量: {basic_stats.get('config_templates', 0)}\n"
            stats_text += f"  性能历史记录: {basic_stats.get('performance_history_records', 0)}\n"
            stats_text += f"  优化缓存条目: {basic_stats.get('optimization_cache_entries', 0)}\n"
            stats_text += f"  活跃推荐数量: {basic_stats.get('active_recommendations', 0)}\n"
            stats_text += f"  已解决冲突: {basic_stats.get('resolved_conflicts', 0)}\n"
            stats_text += f"  平均优化改进: {basic_stats.get('average_optimization_improvement', 0):.2%}\n\n"

            # 任务统计
            task_stats = stats.get('tasks', {})
            stats_text += "📋 任务统计:\n"
            stats_text += f"  总任务数: {task_stats.get('total', 0)}\n"
            stats_text += f"  启用任务: {task_stats.get('enabled', 0)}\n"
            stats_text += f"  运行中任务: {task_stats.get('running', 0)}\n\n"

            # 数据源统计
            source_stats = stats.get('data_sources', {})
            stats_text += "🔌 数据源统计:\n"
            stats_text += f"  总数据源: {source_stats.get('total', 0)}\n"
            stats_text += f"  启用数据源: {source_stats.get('enabled', 0)}\n\n"

            # 历史统计
            history_stats = stats.get('history_30_days', {})
            stats_text += "📈 30天历史统计:\n"
            stats_text += f"  总运行次数: {history_stats.get('total_runs', 0)}\n"
            stats_text += f"  成功运行: {history_stats.get('successful_runs', 0)}\n"
            stats_text += f"  失败运行: {history_stats.get('failed_runs', 0)}\n"
            stats_text += f"  导入记录总数: {history_stats.get('total_imported', 0)}\n"

            self.statistics_text.setPlainText(stats_text)

        except Exception as e:
            logger.error(f"刷新统计信息失败: {e}")

    def refresh_templates(self):
        """刷新配置模板"""
        try:
            self.templates_tree.clear()

            # 这里需要实现获取模板的方法
            # templates = self.config_manager.get_all_templates()
            # for template in templates:
            #     item = QTreeWidgetItem([
            #         template.name,
            #         template.data_source,
            #         template.asset_type,
            #         template.frequency.value,
            #         f"{template.success_rate:.1%}",
            #         str(template.usage_count)
            #     ])
            #     self.templates_tree.addTopLevelItem(item)

        except Exception as e:
            logger.error(f"刷新配置模板失败: {e}")

    @pyqtSlot(str)
    def on_task_selected(self, task_text: str):
        """任务选择变化"""
        if not task_text:
            return

        # 从文本中提取任务ID
        if "(" in task_text and ")" in task_text:
            self.current_task_id = task_text.split("(")[1].split(")")[0]
        else:
            self.current_task_id = None

    def execute_optimization(self):
        """执行智能优化"""
        if not self.current_task_id:
            self.show_error_message("错误", "请先选择一个任务")
            return

        try:
            # 获取优化级别
            level_map = {
                "保守": ConfigOptimizationLevel.CONSERVATIVE,
                "平衡": ConfigOptimizationLevel.BALANCED,
                "激进": ConfigOptimizationLevel.AGGRESSIVE
            }
            optimization_level = level_map[self.optimization_level_combo.currentText()]

            # 获取任务配置
            task_config = self.config_manager.get_import_task(self.current_task_id)
            if not task_config:
                self.show_error_message("错误", "任务配置不存在")
                return

            self.optimize_btn.setEnabled(False)
            self.optimize_btn.setText("优化中...")

            # 执行优化
            optimized_config = self.config_manager.generate_intelligent_config(
                task_config, optimization_level
            )

            if optimized_config:
                # 显示优化结果
                result_text = f"✅ 智能优化完成\n\n"
                result_text += f"原始配置:\n"
                result_text += f"  批次大小: {task_config.batch_size}\n"
                result_text += f"  工作线程: {task_config.max_workers}\n\n"
                result_text += f"优化后配置:\n"
                result_text += f"  批次大小: {optimized_config.batch_size}\n"
                result_text += f"  工作线程: {optimized_config.max_workers}\n\n"

                # 计算改进
                batch_improvement = ((optimized_config.batch_size - task_config.batch_size) / task_config.batch_size * 100) if task_config.batch_size > 0 else 0
                worker_improvement = ((optimized_config.max_workers - task_config.max_workers) / task_config.max_workers * 100) if task_config.max_workers > 0 else 0

                result_text += f"改进幅度:\n"
                result_text += f"  批次大小: {batch_improvement:+.1f}%\n"
                result_text += f"  工作线程: {worker_improvement:+.1f}%\n"

                self.optimization_result_text.setPlainText(result_text)

                # 询问是否应用优化
                reply = QMessageBox.question(
                    self, "应用优化",
                    "是否将优化后的配置应用到任务中？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # 应用优化配置
                    self.config_manager.update_import_task(
                        self.current_task_id,
                        batch_size=optimized_config.batch_size,
                        max_workers=optimized_config.max_workers
                    )

                    self.show_info_message("成功", "优化配置已应用")
                    self.config_optimized.emit(self.current_task_id, {
                        'batch_size': optimized_config.batch_size,
                        'max_workers': optimized_config.max_workers
                    })
            else:
                self.optimization_result_text.setPlainText("❌ 优化失败，请检查任务配置")

        except Exception as e:
            logger.error(f"执行智能优化失败: {e}")
            self.show_error_message("优化失败", str(e))
            self.optimization_result_text.setPlainText(f"❌ 优化失败: {e}")

        finally:
            self.optimize_btn.setEnabled(True)
            self.optimize_btn.setText("🚀 执行智能优化")

    def generate_recommendations(self):
        """生成配置推荐"""
        if not self.current_task_id:
            self.show_error_message("错误", "请先选择一个任务")
            return

        try:
            # 获取推荐类型
            type_map = {
                "性能优化": ConfigRecommendationType.PERFORMANCE,
                "可靠性优化": ConfigRecommendationType.RELIABILITY,
                "成本优化": ConfigRecommendationType.COST,
                "平衡优化": ConfigRecommendationType.BALANCED
            }
            recommendation_type = type_map[self.recommendation_type_combo.currentText()]

            self.generate_recommendations_btn.setEnabled(False)
            self.generate_recommendations_btn.setText("生成中...")

            # 启动工作线程
            self.recommendation_worker = ConfigRecommendationWorker(
                self.config_manager, self.current_task_id, recommendation_type
            )
            self.recommendation_worker.recommendations_ready.connect(self.on_recommendations_ready)
            self.recommendation_worker.error_occurred.connect(self.on_recommendation_error)
            self.recommendation_worker.start()

        except Exception as e:
            logger.error(f"生成配置推荐失败: {e}")
            self.show_error_message("生成推荐失败", str(e))
            self.generate_recommendations_btn.setEnabled(True)
            self.generate_recommendations_btn.setText("💡 生成推荐")

    @pyqtSlot(list)
    def on_recommendations_ready(self, recommendations):
        """推荐生成完成"""
        self.recommendations = recommendations
        self.update_recommendations_table()

        self.generate_recommendations_btn.setEnabled(True)
        self.generate_recommendations_btn.setText("💡 生成推荐")

        self.status_label.setText(f"生成了 {len(recommendations)} 条推荐")

    @pyqtSlot(str)
    def on_recommendation_error(self, error_message):
        """推荐生成错误"""
        self.show_error_message("生成推荐失败", error_message)

        self.generate_recommendations_btn.setEnabled(True)
        self.generate_recommendations_btn.setText("💡 生成推荐")

    def update_recommendations_table(self):
        """更新推荐表格"""
        self.recommendations_table.setRowCount(len(self.recommendations))

        for row, rec in enumerate(self.recommendations):
            # 推荐类型
            self.recommendations_table.setItem(row, 0, QTableWidgetItem(rec.recommendation_type.value))

            # 配置变更
            changes_text = ", ".join([f"{k}: {v}" for k, v in rec.recommended_changes.items()])
            self.recommendations_table.setItem(row, 1, QTableWidgetItem(changes_text))

            # 预期改进
            improvements_text = ", ".join([f"{k}: {v:.1%}" for k, v in rec.expected_improvement.items()])
            self.recommendations_table.setItem(row, 2, QTableWidgetItem(improvements_text))

            # 置信度
            confidence_item = QTableWidgetItem(f"{rec.confidence_score:.1%}")
            if rec.confidence_score >= 0.8:
                confidence_item.setBackground(QColor("#d4edda"))
            elif rec.confidence_score >= 0.6:
                confidence_item.setBackground(QColor("#fff3cd"))
            else:
                confidence_item.setBackground(QColor("#f8d7da"))
            self.recommendations_table.setItem(row, 3, confidence_item)

            # 原因
            self.recommendations_table.setItem(row, 4, QTableWidgetItem(rec.reasoning))

            # 操作按钮
            apply_btn = QPushButton("应用")
            apply_btn.clicked.connect(lambda checked, r=rec: self.apply_recommendation(r))
            self.recommendations_table.setCellWidget(row, 5, apply_btn)

    def apply_recommendation(self, recommendation: 'ConfigRecommendation'):
        """应用推荐"""
        try:
            reply = QMessageBox.question(
                self, "应用推荐",
                f"是否应用以下推荐？\n\n{recommendation.reasoning}\n\n配置变更: {recommendation.recommended_changes}",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 应用推荐的配置变更
                self.config_manager.update_import_task(
                    recommendation.config_id,
                    **recommendation.recommended_changes
                )

                self.show_info_message("成功", "推荐已应用")
                self.recommendation_applied.emit(recommendation.config_id, recommendation.recommendation_id)

        except Exception as e:
            logger.error(f"应用推荐失败: {e}")
            self.show_error_message("应用推荐失败", str(e))

    def detect_conflicts(self):
        """检测配置冲突"""
        try:
            self.detect_conflicts_btn.setEnabled(False)
            self.detect_conflicts_btn.setText("检测中...")

            # 启动工作线程
            self.conflict_worker = ConflictDetectionWorker(self.config_manager)
            self.conflict_worker.conflicts_detected.connect(self.on_conflicts_detected)
            self.conflict_worker.error_occurred.connect(self.on_conflict_error)
            self.conflict_worker.start()

        except Exception as e:
            logger.error(f"检测配置冲突失败: {e}")
            self.show_error_message("检测冲突失败", str(e))
            self.detect_conflicts_btn.setEnabled(True)
            self.detect_conflicts_btn.setText("🔍 检测冲突")

    @pyqtSlot(list)
    def on_conflicts_detected(self, conflicts):
        """冲突检测完成"""
        self.conflicts = conflicts
        self.update_conflicts_table()

        self.detect_conflicts_btn.setEnabled(True)
        self.detect_conflicts_btn.setText("🔍 检测冲突")

        self.status_label.setText(f"检测到 {len(conflicts)} 个冲突")

    @pyqtSlot(str)
    def on_conflict_error(self, error_message):
        """冲突检测错误"""
        self.show_error_message("检测冲突失败", error_message)

        self.detect_conflicts_btn.setEnabled(True)
        self.detect_conflicts_btn.setText("🔍 检测冲突")

    def update_conflicts_table(self):
        """更新冲突表格"""
        self.conflicts_table.setRowCount(len(self.conflicts))

        for row, conflict in enumerate(self.conflicts):
            # 冲突类型
            self.conflicts_table.setItem(row, 0, QTableWidgetItem(conflict.conflict_type))

            # 影响任务
            tasks_text = ", ".join(conflict.config_ids)
            self.conflicts_table.setItem(row, 1, QTableWidgetItem(tasks_text))

            # 严重程度
            severity_item = QTableWidgetItem(conflict.severity)
            if conflict.severity == "critical":
                severity_item.setBackground(QColor("#dc3545"))
                severity_item.setForeground(QColor("white"))
            elif conflict.severity == "high":
                severity_item.setBackground(QColor("#fd7e14"))
            elif conflict.severity == "medium":
                severity_item.setBackground(QColor("#ffc107"))
            else:
                severity_item.setBackground(QColor("#28a745"))
                severity_item.setForeground(QColor("white"))
            self.conflicts_table.setItem(row, 2, severity_item)

            # 描述
            self.conflicts_table.setItem(row, 3, QTableWidgetItem(conflict.description))

            # 建议解决方案
            resolution_text = str(conflict.suggested_resolution)
            self.conflicts_table.setItem(row, 4, QTableWidgetItem(resolution_text))

            # 操作按钮
            if conflict.auto_resolvable:
                resolve_btn = QPushButton("自动解决")
                resolve_btn.clicked.connect(lambda checked, c=conflict: self.resolve_conflict(c))
                self.conflicts_table.setCellWidget(row, 5, resolve_btn)
            else:
                manual_btn = QPushButton("手动处理")
                manual_btn.clicked.connect(lambda checked, c=conflict: self.manual_resolve_conflict(c))
                self.conflicts_table.setCellWidget(row, 5, manual_btn)

    def resolve_conflict(self, conflict: 'ConfigConflict'):
        """解决单个冲突"""
        try:
            reply = QMessageBox.question(
                self, "解决冲突",
                f"是否自动解决以下冲突？\n\n{conflict.description}\n\n解决方案: {conflict.suggested_resolution}",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                result = self.config_manager.auto_resolve_conflicts([conflict])

                if result['resolved'] > 0:
                    self.show_info_message("成功", "冲突已解决")
                    self.conflict_resolved.emit(conflict.conflict_id)
                    self.detect_conflicts()  # 重新检测
                else:
                    self.show_error_message("解决失败", "无法自动解决此冲突")

        except Exception as e:
            logger.error(f"解决冲突失败: {e}")
            self.show_error_message("解决冲突失败", str(e))

    def manual_resolve_conflict(self, conflict: 'ConfigConflict'):
        """手动处理冲突"""
        # 显示冲突详情对话框
        dialog = ConflictDetailDialog(conflict, self)
        if dialog.exec_() == QDialog.Accepted:
            self.detect_conflicts()  # 重新检测

    def auto_resolve_conflicts(self):
        """自动解决所有冲突"""
        if not self.conflicts:
            self.show_info_message("提示", "没有检测到冲突")
            return

        try:
            auto_resolvable = [c for c in self.conflicts if c.auto_resolvable]

            if not auto_resolvable:
                self.show_info_message("提示", "没有可自动解决的冲突")
                return

            reply = QMessageBox.question(
                self, "自动解决冲突",
                f"发现 {len(auto_resolvable)} 个可自动解决的冲突，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                result = self.config_manager.auto_resolve_conflicts(auto_resolvable)

                self.show_info_message(
                    "解决完成",
                    f"成功解决 {result['resolved']} 个冲突，失败 {result['failed']} 个"
                )

                self.detect_conflicts()  # 重新检测

        except Exception as e:
            logger.error(f"自动解决冲突失败: {e}")
            self.show_error_message("自动解决失败", str(e))

    def create_template(self):
        """创建配置模板"""
        # 实现创建模板的对话框
        self.show_info_message("提示", "配置模板功能开发中...")

    def apply_template(self):
        """应用配置模板"""
        # 实现应用模板的功能
        self.show_info_message("提示", "配置模板功能开发中...")

    def delete_template(self):
        """删除配置模板"""
        # 实现删除模板的功能
        self.show_info_message("提示", "配置模板功能开发中...")

    def refresh_all_data(self):
        """刷新所有数据"""
        self.load_initial_data()
        self.status_label.setText("数据已刷新")

    def show_info_message(self, title: str, message: str):
        """显示信息消息"""
        QMessageBox.information(self, title, message)

    def show_error_message(self, title: str, message: str):
        """显示错误消息"""
        QMessageBox.critical(self, title, message)


class ConflictDetailDialog(QDialog):
    """冲突详情对话框"""

    def __init__(self, conflict: 'ConfigConflict', parent=None):
        super().__init__(parent)
        self.conflict = conflict
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("冲突详情")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # 冲突信息
        info_text = f"""
冲突ID: {self.conflict.conflict_id}
冲突类型: {self.conflict.conflict_type}
严重程度: {self.conflict.severity}
影响任务: {', '.join(self.conflict.config_ids)}

描述:
{self.conflict.description}

建议解决方案:
{self.conflict.suggested_resolution}
        """

        info_label = QTextEdit()
        info_label.setPlainText(info_text.strip())
        info_label.setReadOnly(True)
        layout.addWidget(info_label)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def main():
    """测试智能配置管理界面"""
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    if INTELLIGENT_CONFIG_AVAILABLE:
        config_manager = IntelligentConfigManager()
        widget = IntelligentConfigWidget(config_manager)
    else:
        widget = IntelligentConfigWidget()

    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
