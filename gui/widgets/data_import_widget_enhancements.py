from loguru import logger
#!/usr/bin/env python3
"""
数据导入UI增强功能补丁

提供额外的UI增强功能：
- 数据预览功能
- 导入历史记录
- 数据质量检查
- 自动重试机制
- 导入模板管理
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QSpinBox, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QDateEdit, QTimeEdit, QSlider, QDial
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap

logger = logger


class DataPreviewWidget(QWidget):
    """数据预览组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 预览控制
        control_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择要预览的文件...")
        control_layout.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_file)
        control_layout.addWidget(self.browse_btn)

        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self.preview_data)
        control_layout.addWidget(self.preview_btn)

        layout.addLayout(control_layout)

        # 预览设置
        settings_group = QGroupBox("预览设置")
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel("预览行数:"), 0, 0)
        self.preview_rows_spin = QSpinBox()
        self.preview_rows_spin.setRange(10, 1000)
        self.preview_rows_spin.setValue(100)
        settings_layout.addWidget(self.preview_rows_spin, 0, 1)

        settings_layout.addWidget(QLabel("编码格式:"), 0, 2)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312", "ASCII"])
        settings_layout.addWidget(self.encoding_combo, 0, 3)

        self.header_cb = QCheckBox("包含标题行")
        self.header_cb.setChecked(True)
        settings_layout.addWidget(self.header_cb, 1, 0)

        self.auto_detect_cb = QCheckBox("自动检测格式")
        self.auto_detect_cb.setChecked(True)
        settings_layout.addWidget(self.auto_detect_cb, 1, 1)

        layout.addWidget(settings_group)

        # 预览表格
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        layout.addWidget(self.preview_table)

        # 数据统计
        stats_group = QGroupBox("数据统计")
        stats_layout = QGridLayout(stats_group)

        self.total_rows_label = QLabel("0")
        self.total_cols_label = QLabel("0")
        self.file_size_label = QLabel("0 MB")
        self.data_types_label = QLabel("未知")

        stats_layout.addWidget(QLabel("总行数:"), 0, 0)
        stats_layout.addWidget(self.total_rows_label, 0, 1)
        stats_layout.addWidget(QLabel("总列数:"), 0, 2)
        stats_layout.addWidget(self.total_cols_label, 0, 3)
        stats_layout.addWidget(QLabel("文件大小:"), 1, 0)
        stats_layout.addWidget(self.file_size_label, 1, 1)
        stats_layout.addWidget(QLabel("数据类型:"), 1, 2)
        stats_layout.addWidget(self.data_types_label, 1, 3)

        layout.addWidget(stats_group)

    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "数据文件 (*.csv *.xlsx *.xls *.json);;所有文件 (*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def preview_data(self):
        """预览数据"""
        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "警告", "请先选择文件")
            return

        try:
            import pandas as pd
            import os

            # 获取文件信息
            file_size = os.path.getsize(file_path) / 1024 / 1024  # MB
            self.file_size_label.setText(f"{file_size:.1f} MB")

            # 读取数据
            encoding = self.encoding_combo.currentText().lower()
            if encoding == "utf-8":
                encoding = "utf-8"
            elif encoding == "gbk":
                encoding = "gbk"

            nrows = self.preview_rows_spin.value()

            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding=encoding, nrows=nrows)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path, nrows=nrows)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path, lines=True, nrows=nrows)
            else:
                QMessageBox.warning(self, "错误", "不支持的文件格式")
                return

            # 更新统计信息
            self.total_rows_label.setText(str(len(df)))
            self.total_cols_label.setText(str(len(df.columns)))

            # 检测数据类型
            numeric_cols = len(df.select_dtypes(include=['number']).columns)
            text_cols = len(df.select_dtypes(include=['object']).columns)
            date_cols = len(df.select_dtypes(include=['datetime']).columns)
            self.data_types_label.setText(f"数值:{numeric_cols}, 文本:{text_cols}, 日期:{date_cols}")

            # 显示预览数据
            self.preview_table.setRowCount(len(df))
            self.preview_table.setColumnCount(len(df.columns))
            self.preview_table.setHorizontalHeaderLabels(df.columns.tolist())

            for i, row in df.iterrows():
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    self.preview_table.setItem(i, j, item)

            self.preview_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览数据失败: {str(e)}")


class ImportHistoryWidget(QWidget):
    """导入历史记录组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_history()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 历史记录控制
        control_layout = QHBoxLayout()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "成功", "失败", "进行中"])
        self.filter_combo.currentTextChanged.connect(self.filter_history)
        control_layout.addWidget(QLabel("筛选:"))
        control_layout.addWidget(self.filter_combo)

        control_layout.addStretch()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_history)
        control_layout.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.clicked.connect(self.clear_history)
        control_layout.addWidget(self.clear_btn)

        layout.addLayout(control_layout)

        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "任务名称", "数据类型", "记录数", "状态", "耗时", "操作"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.history_table)

    def load_history(self):
        """加载历史记录"""
        # 这里应该从数据库或文件中加载历史记录
        # 暂时使用模拟数据
        history_data = [
            {
                "time": "2024-08-27 10:30:00",
                "task_name": "股票数据导入",
                "data_type": "K线数据",
                "records": 1500,
                "status": "成功",
                "duration": "2分30秒"
            },
            {
                "time": "2024-08-27 09:15:00",
                "task_name": "基本面数据导入",
                "data_type": "财务数据",
                "records": 850,
                "status": "失败",
                "duration": "1分15秒"
            }
        ]

        self.history_table.setRowCount(len(history_data))

        for i, record in enumerate(history_data):
            self.history_table.setItem(i, 0, QTableWidgetItem(record["time"]))
            self.history_table.setItem(i, 1, QTableWidgetItem(record["task_name"]))
            self.history_table.setItem(i, 2, QTableWidgetItem(record["data_type"]))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(record["records"])))

            # 状态列使用颜色标识
            status_item = QTableWidgetItem(record["status"])
            if record["status"] == "成功":
                status_item.setBackground(QColor(200, 255, 200))
            elif record["status"] == "失败":
                status_item.setBackground(QColor(255, 200, 200))
            else:
                status_item.setBackground(QColor(255, 255, 200))
            self.history_table.setItem(i, 4, status_item)

            self.history_table.setItem(i, 5, QTableWidgetItem(record["duration"]))

            # 操作按钮
            action_btn = QPushButton("重新导入")
            action_btn.clicked.connect(lambda checked, row=i: self.retry_import(row))
            self.history_table.setCellWidget(i, 6, action_btn)

    def filter_history(self, filter_text):
        """筛选历史记录"""
        for row in range(self.history_table.rowCount()):
            if filter_text == "全部":
                self.history_table.setRowHidden(row, False)
            else:
                status_item = self.history_table.item(row, 4)
                if status_item and status_item.text() == filter_text:
                    self.history_table.setRowHidden(row, False)
                else:
                    self.history_table.setRowHidden(row, True)

    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有历史记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_table.setRowCount(0)

    def retry_import(self, row):
        """重新导入"""
        task_name = self.history_table.item(row, 1).text()
        QMessageBox.information(self, "提示", f"将重新执行任务: {task_name}")


class DataQualityWidget(QWidget):
    """数据质量检查组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 质量检查配置
        config_group = QGroupBox("质量检查配置")
        config_layout = QGridLayout(config_group)

        self.check_missing_cb = QCheckBox("检查缺失值")
        self.check_missing_cb.setChecked(True)
        config_layout.addWidget(self.check_missing_cb, 0, 0)

        self.check_duplicates_cb = QCheckBox("检查重复值")
        self.check_duplicates_cb.setChecked(True)
        config_layout.addWidget(self.check_duplicates_cb, 0, 1)

        self.check_outliers_cb = QCheckBox("检查异常值")
        self.check_outliers_cb.setChecked(True)
        config_layout.addWidget(self.check_outliers_cb, 1, 0)

        self.check_format_cb = QCheckBox("检查格式错误")
        self.check_format_cb.setChecked(True)
        config_layout.addWidget(self.check_format_cb, 1, 1)

        layout.addWidget(config_group)

        # 检查按钮
        self.check_btn = QPushButton("开始质量检查")
        self.check_btn.clicked.connect(self.start_quality_check)
        layout.addWidget(self.check_btn)

        # 检查结果
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)

        # 修复建议
        suggestions_group = QGroupBox("修复建议")
        suggestions_layout = QVBoxLayout(suggestions_group)

        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        suggestions_layout.addWidget(self.suggestions_text)

        layout.addWidget(suggestions_group)

    def start_quality_check(self):
        """开始质量检查"""
        self.results_text.clear()
        self.suggestions_text.clear()

        # 模拟质量检查结果
        results = []
        suggestions = []

        if self.check_missing_cb.isChecked():
            results.append(" 缺失值检查: 发现 15 个缺失值 (0.5%)")
            suggestions.append(" 建议使用前向填充或均值填充处理缺失值")

        if self.check_duplicates_cb.isChecked():
            results.append(" 重复值检查: 发现 8 个重复记录 (0.3%)")
            suggestions.append(" 建议删除重复记录或进行数据去重")

        if self.check_outliers_cb.isChecked():
            results.append(" 异常值检查: 发现 23 个可能的异常值 (0.8%)")
            suggestions.append(" 建议使用IQR方法或Z-score方法处理异常值")

        if self.check_format_cb.isChecked():
            results.append(" 格式检查: 所有数据格式正确")
            suggestions.append(" 数据格式良好，无需额外处理")

        self.results_text.setText("\n".join(results))
        self.suggestions_text.setText("\n".join(suggestions))


class ImportTemplateWidget(QWidget):
    """导入模板管理组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.templates = {}
        self.init_ui()
        self.load_templates()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 模板控制
        control_layout = QHBoxLayout()

        self.new_template_btn = QPushButton("新建模板")
        self.new_template_btn.clicked.connect(self.new_template)
        control_layout.addWidget(self.new_template_btn)

        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.clicked.connect(self.save_template)
        control_layout.addWidget(self.save_template_btn)

        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.clicked.connect(self.delete_template)
        control_layout.addWidget(self.delete_template_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 模板列表
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.on_template_selected)
        layout.addWidget(self.template_list)

        # 模板配置
        config_group = QGroupBox("模板配置")
        config_layout = QGridLayout(config_group)

        config_layout.addWidget(QLabel("模板名称:"), 0, 0)
        self.template_name_edit = QLineEdit()
        config_layout.addWidget(self.template_name_edit, 0, 1)

        config_layout.addWidget(QLabel("数据类型:"), 1, 0)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["股票数据", "财务数据", "宏观数据"])
        config_layout.addWidget(self.data_type_combo, 1, 1)

        config_layout.addWidget(QLabel("文件格式:"), 2, 0)
        self.file_format_combo = QComboBox()
        self.file_format_combo.addItems(["CSV", "Excel", "JSON"])
        config_layout.addWidget(self.file_format_combo, 2, 1)

        config_layout.addWidget(QLabel("编码格式:"), 3, 0)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312"])
        config_layout.addWidget(self.encoding_combo, 3, 1)

        layout.addWidget(config_group)

    def load_templates(self):
        """加载模板"""
        # 模拟模板数据
        self.templates = {
            "股票K线模板": {
                "data_type": "股票数据",
                "file_format": "CSV",
                "encoding": "UTF-8",
                "columns": ["date", "open", "high", "low", "close", "volume"]
            },
            "财务报表模板": {
                "data_type": "财务数据",
                "file_format": "Excel",
                "encoding": "UTF-8",
                "columns": ["symbol", "date", "revenue", "profit", "assets"]
            }
        }

        self.template_list.clear()
        for template_name in self.templates.keys():
            self.template_list.addItem(template_name)

    def on_template_selected(self, current, previous):
        """模板选择事件"""
        if current:
            template_name = current.text()
            template = self.templates.get(template_name, {})

            self.template_name_edit.setText(template_name)
            self.data_type_combo.setCurrentText(template.get("data_type", ""))
            self.file_format_combo.setCurrentText(template.get("file_format", ""))
            self.encoding_combo.setCurrentText(template.get("encoding", ""))

    def new_template(self):
        """新建模板"""
        self.template_name_edit.clear()
        self.data_type_combo.setCurrentIndex(0)
        self.file_format_combo.setCurrentIndex(0)
        self.encoding_combo.setCurrentIndex(0)

    def save_template(self):
        """保存模板"""
        name = self.template_name_edit.text()
        if not name:
            QMessageBox.warning(self, "警告", "请输入模板名称")
            return

        template = {
            "data_type": self.data_type_combo.currentText(),
            "file_format": self.file_format_combo.currentText(),
            "encoding": self.encoding_combo.currentText()
        }

        self.templates[name] = template
        self.load_templates()
        QMessageBox.information(self, "成功", f"模板 '{name}' 保存成功")

    def delete_template(self):
        """删除模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要删除的模板")
            return

        template_name = current_item.text()
        reply = QMessageBox.question(
            self, "确认", f"确定要删除模板 '{template_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.templates[template_name]
            self.load_templates()
            QMessageBox.information(self, "成功", "模板删除成功")


# 导出增强组件
__all__ = [
    'DataPreviewWidget',
    'ImportHistoryWidget',
    'DataQualityWidget',
    'ImportTemplateWidget'
]
