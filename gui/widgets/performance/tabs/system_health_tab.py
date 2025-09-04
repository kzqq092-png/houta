#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统健康检查标签页
现代化系统健康监控界面
"""

import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QCheckBox, QLabel, QGridLayout, QTextEdit, QListWidget,
    QFrame, QMessageBox
)
from PyQt5.QtCore import pyqtSlot
from gui.widgets.performance.workers.async_workers import SystemHealthCheckThread

logger = logging.getLogger(__name__)


class ModernSystemHealthTab(QWidget):
    """现代化系统健康检查标签页"""

    def __init__(self, health_checker=None):
        super().__init__()
        self._health_checker = health_checker
        self._check_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 健康检查控制面板
        control_group = QGroupBox("🏥 系统健康检查")
        control_layout = QHBoxLayout()

        self.check_button = QPushButton("🔍 开始健康检查")
        self.check_button.clicked.connect(self.run_health_check)
        control_layout.addWidget(self.check_button)

        self.auto_check_cb = QCheckBox("自动检查")
        control_layout.addWidget(self.auto_check_cb)

        control_layout.addStretch()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 健康状态总览
        overview_group = QGroupBox("📊 健康状态总览")
        overview_layout = QGridLayout()

        self.overall_status_label = QLabel("总体状态: 未检查")
        self.overall_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        overview_layout.addWidget(self.overall_status_label, 0, 0, 1, 2)

        # 各子系统状态卡片
        self.status_cards = {}
        subsystems = [
            ("系统信息", "system_info"),
            ("形态识别", "pattern_recognition"),
            ("性能指标", "performance_metrics"),
            ("缓存系统", "cache_system"),
            ("内存使用", "memory_usage"),
            ("依赖检查", "dependencies"),
            ("数据库连接", "database_connectivity"),
            ("UI组件", "ui_components")
        ]

        for i, (name, key) in enumerate(subsystems):
            card = self._create_status_card(name, "未检查")
            self.status_cards[key] = card
            overview_layout.addWidget(card, (i // 4) + 1, i % 4)

        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group)

        # 详细报告
        report_group = QGroupBox("📋 详细报告")
        report_layout = QVBoxLayout()

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setMaximumHeight(200)
        report_layout.addWidget(self.report_text)

        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # 建议和操作
        recommendations_group = QGroupBox("💡 建议和操作")
        recommendations_layout = QVBoxLayout()

        self.recommendations_list = QListWidget()
        recommendations_layout.addWidget(self.recommendations_list)

        recommendations_group.setLayout(recommendations_layout)
        layout.addWidget(recommendations_group)

        # 应用样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #27ae60;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)

    def _create_status_card(self, name: str, status: str) -> QFrame:
        """创建状态卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                background: #ecf0f1;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(name_label)

        status_label = QLabel(status)
        status_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(status_label)

        card.status_label = status_label  # 保存引用以便更新
        return card

    def run_health_check(self):
        """执行健康检查"""
        if not self._health_checker:
            QMessageBox.warning(self, "错误", "健康检查器未初始化")
            return

        self.check_button.setEnabled(False)
        self.check_button.setText("🔄 检查中...")

        self._check_thread = SystemHealthCheckThread(self._health_checker)
        self._check_thread.health_check_completed.connect(self.on_check_completed)
        self._check_thread.health_check_error.connect(self.on_check_error)
        self._check_thread.start()

    @pyqtSlot(dict)
    def on_check_completed(self, report: dict):
        """健康检查完成处理"""
        self.check_button.setEnabled(True)
        self.check_button.setText("🔍 开始健康检查")

        # 更新总体状态
        overall_health = report.get('overall_health', 'unknown')
        status_colors = {
            'healthy': '#27ae60',
            'warning': '#f39c12',
            'critical': '#e74c3c',
            'unknown': '#7f8c8d'
        }
        color = status_colors.get(overall_health, '#7f8c8d')
        self.overall_status_label.setText(f"总体状态: {overall_health.upper()}")
        self.overall_status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")

        # 更新各子系统状态
        for key, card in self.status_cards.items():
            subsystem_data = report.get(key, {})
            status = subsystem_data.get('status', 'unknown')
            card.status_label.setText(status)
            card.status_label.setStyleSheet(f"color: {status_colors.get(status, '#7f8c8d')}; font-size: 11px;")

        # 更新详细报告
        report_text = json.dumps(report, indent=2, ensure_ascii=False)
        self.report_text.setPlainText(report_text)

        # 更新建议
        self.recommendations_list.clear()
        recommendations = report.get('recommendations', [])
        for rec in recommendations:
            self.recommendations_list.addItem(rec)

    @pyqtSlot(str)
    def on_check_error(self, error: str):
        """健康检查错误处理"""
        self.check_button.setEnabled(True)
        self.check_button.setText("🔍 开始健康检查")

        # 🔧 修复：更好的错误显示和日志
        logger.error(f"健康检查失败: {error}")

        # 在报告区域显示错误信息
        error_report = f"""❌ 健康检查失败

错误信息: {error}

请检查：
1. 系统依赖是否完整
2. 相关服务是否正常运行
3. 查看日志获取更多详细信息

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.report_text.setPlainText(error_report)

        # 更新总体状态
        self.overall_status_label.setText("总体状态: 检查失败")
        self.overall_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")

        # 也显示弹窗
        QMessageBox.critical(self, "检查错误", f"健康检查失败：{error}")
