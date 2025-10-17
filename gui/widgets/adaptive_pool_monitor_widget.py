#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应连接池监控组件

提供实时监控连接池状态、使用率、调整历史等功能。

作者: AI Assistant
日期: 2025-10-13
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any


class AdaptivePoolMonitorWidget(QWidget):
    """自适应连接池监控组件"""

    # 信号
    status_updated = pyqtSignal(dict)  # 状态更新信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self.adaptive_manager = None
        self.update_timer = None

        self._init_ui()
        self._start_update_timer()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 标题
        title_label = QLabel("🔄 自适应连接池监控")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        main_layout.addWidget(title_label)

        # 状态概览组
        self._create_status_overview(main_layout)

        # 当前指标组
        self._create_current_metrics(main_layout)

        # 调整历史表
        self._create_adjustment_history(main_layout)

        # 操作按钮
        self._create_action_buttons(main_layout)

    def _create_status_overview(self, parent_layout):
        """创建状态概览"""
        group = QGroupBox("运行状态")
        layout = QHBoxLayout(group)

        # 运行状态
        self.status_label = QLabel("状态: 未知")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 调整次数
        self.adjustment_count_label = QLabel("调整次数: 0")
        layout.addWidget(self.adjustment_count_label)

        # 最后调整时间
        self.last_adjustment_label = QLabel("最后调整: -")
        layout.addWidget(self.last_adjustment_label)

        layout.addStretch()
        parent_layout.addWidget(group)

    def _create_current_metrics(self, parent_layout):
        """创建当前指标"""
        group = QGroupBox("当前指标")
        layout = QVBoxLayout(group)

        # Pool Size
        pool_size_layout = QHBoxLayout()
        pool_size_layout.addWidget(QLabel("连接池大小:"))
        self.pool_size_label = QLabel("-")
        self.pool_size_label.setStyleSheet("font-weight: bold; color: #3498db;")
        pool_size_layout.addWidget(self.pool_size_label)
        pool_size_layout.addWidget(QLabel(" / "))
        self.pool_config_label = QLabel("(min: 3, max: 50)")
        pool_size_layout.addWidget(self.pool_config_label)
        pool_size_layout.addStretch()
        layout.addLayout(pool_size_layout)

        # Usage Rate
        usage_layout = QHBoxLayout()
        usage_layout.addWidget(QLabel("使用率:"))
        self.usage_rate_label = QLabel("0%")
        self.usage_rate_label.setStyleSheet("font-weight: bold;")
        usage_layout.addWidget(self.usage_rate_label)

        self.usage_progress = QProgressBar()
        self.usage_progress.setRange(0, 100)
        self.usage_progress.setValue(0)
        self.usage_progress.setTextVisible(True)
        self.usage_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
        """)
        usage_layout.addWidget(self.usage_progress, 1)
        layout.addLayout(usage_layout)

        # Active Connections
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("活跃连接:"))
        self.checked_out_label = QLabel("0")
        active_layout.addWidget(self.checked_out_label)

        active_layout.addWidget(QLabel("  空闲连接:"))
        self.checked_in_label = QLabel("0")
        active_layout.addWidget(self.checked_in_label)

        active_layout.addWidget(QLabel("  溢出连接:"))
        self.overflow_label = QLabel("0")
        active_layout.addWidget(self.overflow_label)
        active_layout.addStretch()
        layout.addLayout(active_layout)

        parent_layout.addWidget(group)

    def _create_adjustment_history(self, parent_layout):
        """创建调整历史表"""
        group = QGroupBox("最近调整记录")
        layout = QVBoxLayout(group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["时间", "调整前", "调整后", "原因"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        layout.addWidget(self.history_table)
        parent_layout.addWidget(group)

    def _create_action_buttons(self, parent_layout):
        """创建操作按钮"""
        button_layout = QHBoxLayout()

        # 刷新按钮
        self.refresh_button = QPushButton("🔄 立即刷新")
        self.refresh_button.clicked.connect(self._update_display)
        button_layout.addWidget(self.refresh_button)

        # 清空历史
        self.clear_button = QPushButton("🗑️ 清空历史")
        self.clear_button.clicked.connect(self._clear_history)
        button_layout.addWidget(self.clear_button)

        # 配置按钮
        self.config_button = QPushButton("⚙️ 配置")
        self.config_button.clicked.connect(self._show_config_dialog)
        button_layout.addWidget(self.config_button)

        button_layout.addStretch()
        parent_layout.addLayout(button_layout)

    def _start_update_timer(self):
        """启动定时更新"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(5000)  # 每5秒更新一次

    def _update_display(self):
        """更新显示"""
        try:
            # 获取自适应管理器
            from core.adaptive_pool_initializer import get_adaptive_manager
            self.adaptive_manager = get_adaptive_manager()

            if not self.adaptive_manager:
                self._show_disabled_state()
                return

            # 获取状态
            status = self.adaptive_manager.get_status()

            # 更新状态概览
            self._update_status_overview(status)

            # 更新当前指标
            self._update_current_metrics(status)

            # 发射信号
            self.status_updated.emit(status)

        except Exception as e:
            logger.error(f"更新显示失败: {e}")

    def _show_disabled_state(self):
        """显示禁用状态"""
        self.status_label.setText("状态: ⏸️ 未启用")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #95a5a6;")

        self.pool_size_label.setText("-")
        self.usage_rate_label.setText("-")
        self.usage_progress.setValue(0)
        self.checked_out_label.setText("-")
        self.checked_in_label.setText("-")
        self.overflow_label.setText("-")

    def _update_status_overview(self, status: Dict[str, Any]):
        """更新状态概览"""
        # 运行状态
        if status['running']:
            self.status_label.setText("状态: ✅ 运行中")
            self.status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #27ae60;")
        else:
            self.status_label.setText("状态: ⏸️ 已停止")
            self.status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #e74c3c;")

        # 调整次数
        count = status.get('adjustment_count', 0)
        self.adjustment_count_label.setText(f"调整次数: {count}")

        # 最后调整时间
        last_adjustment = status.get('last_adjustment')
        if last_adjustment:
            try:
                dt = datetime.fromisoformat(last_adjustment)
                time_str = dt.strftime('%H:%M:%S')
                self.last_adjustment_label.setText(f"最后调整: {time_str}")
            except:
                self.last_adjustment_label.setText("最后调整: -")
        else:
            self.last_adjustment_label.setText("最后调整: -")

    def _update_current_metrics(self, status: Dict[str, Any]):
        """更新当前指标"""
        config = status.get('config', {})

        # Pool Size
        pool_size = status.get('current_pool_size', '-')
        self.pool_size_label.setText(str(pool_size))

        min_size = config.get('min_pool_size', 3)
        max_size = config.get('max_pool_size', 50)
        self.pool_config_label.setText(f"(min: {min_size}, max: {max_size})")

        # Usage Rate
        usage_str = status.get('current_usage_rate', '0%')
        self.usage_rate_label.setText(usage_str)

        try:
            usage_value = float(usage_str.replace('%', ''))
            self.usage_progress.setValue(int(usage_value))

            # 根据使用率设置颜色
            if usage_value > 80:
                color = "#e74c3c"  # 红色
            elif usage_value > 60:
                color = "#f39c12"  # 橙色
            else:
                color = "#27ae60"  # 绿色

            self.usage_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    text-align: center;
                    height: 20px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 5px;
                }}
            """)
            self.usage_rate_label.setStyleSheet(f"font-weight: bold; color: {color};")
        except:
            pass

        # Connections (需要从连接池状态获取)
        if self.adaptive_manager:
            try:
                from core.database.factorweave_analytics_db import get_analytics_db
                db = get_analytics_db()
                pool_status = db.get_pool_status()

                self.checked_out_label.setText(str(pool_status.get('checked_out', 0)))
                self.checked_in_label.setText(str(pool_status.get('checked_in', 0)))
                self.overflow_label.setText(str(pool_status.get('overflow', 0)))
            except:
                pass

    def _clear_history(self):
        """清空历史表"""
        self.history_table.setRowCount(0)

    def _show_config_dialog(self):
        """显示配置对话框"""
        try:
            from gui.dialogs.adaptive_pool_config_dialog import AdaptivePoolConfigDialog

            dialog = AdaptivePoolConfigDialog(self)
            if dialog.exec_():
                # 配置已保存，刷新显示
                self._update_display()
        except Exception as e:
            logger.error(f"打开配置对话框失败: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"无法打开配置对话框: {e}")

    def add_adjustment_record(self, old_size: int, new_size: int, reason: str):
        """添加调整记录"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        # 时间
        time_item = QTableWidgetItem(datetime.now().strftime('%H:%M:%S'))
        self.history_table.setItem(row, 0, time_item)

        # 调整前
        old_item = QTableWidgetItem(str(old_size))
        self.history_table.setItem(row, 1, old_item)

        # 调整后
        new_item = QTableWidgetItem(str(new_size))
        if new_size > old_size:
            new_item.setForeground(QColor("#27ae60"))  # 绿色（扩容）
        else:
            new_item.setForeground(QColor("#e74c3c"))  # 红色（缩容）
        self.history_table.setItem(row, 2, new_item)

        # 原因
        reason_item = QTableWidgetItem(reason)
        self.history_table.setItem(row, 3, reason_item)

        # 保持最多20条记录
        if self.history_table.rowCount() > 20:
            self.history_table.removeRow(0)

    def closeEvent(self, event):
        """关闭事件"""
        if self.update_timer:
            self.update_timer.stop()
        event.accept()
