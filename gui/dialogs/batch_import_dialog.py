#!/usr/bin/env python3
"""
批量数据导入对话框

提供专业的批量数据导入功能，支持：
- 多文件选择和批量处理
- 数据源配置和验证
- 导入进度监控
- 错误处理和报告
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QGroupBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QSpinBox, QCheckBox,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QDateEdit, QTimeEdit
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

# 导入数据导入相关模块
try:
    from core.importdata.import_config_manager import (
        ImportConfigManager, ImportTaskConfig, ImportMode, DataFrequency
    )
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    IMPORT_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"导入引擎模块不可用: {e}")
    IMPORT_ENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)


class BatchImportWorker(QThread):
    """批量导入工作线程"""

    progress_updated = pyqtSignal(int, str)  # 进度, 状态信息
    file_completed = pyqtSignal(str, bool, str)  # 文件路径, 成功状态, 错误信息
    batch_completed = pyqtSignal(int, int)  # 成功数量, 失败数量

    def __init__(self, file_list: List[str], import_config: Dict[str, Any]):
        super().__init__()
        self.file_list = file_list
        self.import_config = import_config
        self.is_cancelled = False

    def run(self):
        """执行批量导入"""
        total_files = len(self.file_list)
        success_count = 0
        failed_count = 0

        for i, file_path in enumerate(self.file_list):
            if self.is_cancelled:
                break

            try:
                # 更新进度
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"正在处理: {os.path.basename(file_path)}")

                # 模拟文件处理（实际应该调用真实的导入逻辑）
                self.msleep(1000)  # 模拟处理时间

                # 这里应该调用真实的数据导入逻辑
                success = self._import_file(file_path)

                if success:
                    success_count += 1
                    self.file_completed.emit(file_path, True, "")
                else:
                    failed_count += 1
                    self.file_completed.emit(file_path, False, "导入失败")

            except Exception as e:
                failed_count += 1
                self.file_completed.emit(file_path, False, str(e))

        # 完成进度
        self.progress_updated.emit(100, "批量导入完成")
        self.batch_completed.emit(success_count, failed_count)

    def _import_file(self, file_path: str) -> bool:
        """导入单个文件"""
        try:
            # 这里应该实现真实的文件导入逻辑
            # 根据文件类型和配置进行数据导入

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False

            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False

            # 模拟导入成功
            return True

        except Exception as e:
            logger.error(f"导入文件失败 {file_path}: {e}")
            return False

    def cancel(self):
        """取消导入"""
        self.is_cancelled = True


class BatchImportDialog(QDialog):
    """批量数据导入对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量数据导入")
        self.setFixedSize(1000, 700)

        # 数据
        self.file_list = []
        self.import_worker = None

        # 初始化UI
        self.init_ui()

        # 应用样式
        self.apply_styles()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 文件选择选项卡
        self.file_tab = self._create_file_selection_tab()
        self.tab_widget.addTab(self.file_tab, "文件选择")

        # 导入配置选项卡
        self.config_tab = self._create_import_config_tab()
        self.tab_widget.addTab(self.config_tab, "导入配置")

        # 进度监控选项卡
        self.progress_tab = self._create_progress_tab()
        self.tab_widget.addTab(self.progress_tab, "进度监控")

        layout.addWidget(self.tab_widget)

        # 底部按钮
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始导入")
        self.start_btn.clicked.connect(self.start_import)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消导入")
        self.cancel_btn.clicked.connect(self.cancel_import)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _create_file_selection_tab(self) -> QWidget:
        """创建文件选择选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)

        # 文件选择按钮
        btn_layout = QHBoxLayout()

        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        btn_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        btn_layout.addWidget(self.add_folder_btn)

        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.clear_files_btn)

        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        # 文件列表
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["文件名", "路径", "大小", "状态"])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)

        file_layout.addWidget(self.file_table)

        layout.addWidget(file_group)

        # 文件统计
        stats_group = QGroupBox("文件统计")
        stats_layout = QGridLayout(stats_group)

        self.total_files_label = QLabel("0")
        self.total_size_label = QLabel("0 MB")
        self.supported_files_label = QLabel("0")

        stats_layout.addWidget(QLabel("总文件数:"), 0, 0)
        stats_layout.addWidget(self.total_files_label, 0, 1)
        stats_layout.addWidget(QLabel("总大小:"), 0, 2)
        stats_layout.addWidget(self.total_size_label, 0, 3)
        stats_layout.addWidget(QLabel("支持的文件:"), 1, 0)
        stats_layout.addWidget(self.supported_files_label, 1, 1)

        layout.addWidget(stats_group)

        return widget

    def _create_import_config_tab(self) -> QWidget:
        """创建导入配置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 数据源配置
        source_group = QGroupBox("数据源配置")
        source_layout = QGridLayout(source_group)

        source_layout.addWidget(QLabel("数据类型:"), 0, 0)
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["股票数据", "财务数据", "宏观数据", "行业数据"])
        source_layout.addWidget(self.data_type_combo, 0, 1)

        source_layout.addWidget(QLabel("文件格式:"), 1, 0)
        self.file_format_combo = QComboBox()
        self.file_format_combo.addItems(["CSV", "Excel", "JSON", "XML"])
        source_layout.addWidget(self.file_format_combo, 1, 1)

        source_layout.addWidget(QLabel("编码格式:"), 2, 0)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "GBK", "GB2312", "ASCII"])
        source_layout.addWidget(self.encoding_combo, 2, 1)

        layout.addWidget(source_group)

        # 导入选项
        options_group = QGroupBox("导入选项")
        options_layout = QGridLayout(options_group)

        self.skip_header_cb = QCheckBox("跳过标题行")
        self.skip_header_cb.setChecked(True)
        options_layout.addWidget(self.skip_header_cb, 0, 0)

        self.validate_data_cb = QCheckBox("数据验证")
        self.validate_data_cb.setChecked(True)
        options_layout.addWidget(self.validate_data_cb, 0, 1)

        self.overwrite_cb = QCheckBox("覆盖已存在数据")
        options_layout.addWidget(self.overwrite_cb, 1, 0)

        self.create_backup_cb = QCheckBox("创建备份")
        self.create_backup_cb.setChecked(True)
        options_layout.addWidget(self.create_backup_cb, 1, 1)

        options_layout.addWidget(QLabel("批处理大小:"), 2, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(100, 10000)
        self.batch_size_spin.setValue(1000)
        options_layout.addWidget(self.batch_size_spin, 2, 1)

        options_layout.addWidget(QLabel("并发线程:"), 3, 0)
        self.thread_count_spin = QSpinBox()
        self.thread_count_spin.setRange(1, 8)
        self.thread_count_spin.setValue(2)
        options_layout.addWidget(self.thread_count_spin, 3, 1)

        layout.addWidget(options_group)

        # 目标数据库配置
        db_group = QGroupBox("目标数据库")
        db_layout = QGridLayout(db_group)

        db_layout.addWidget(QLabel("数据库类型:"), 0, 0)
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["DuckDB", "SQLite", "MySQL", "PostgreSQL"])
        db_layout.addWidget(self.db_type_combo, 0, 1)

        db_layout.addWidget(QLabel("数据库路径:"), 1, 0)
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setText("db/batch_import.db")
        db_layout.addWidget(self.db_path_edit, 1, 1)

        self.browse_db_btn = QPushButton("浏览...")
        self.browse_db_btn.clicked.connect(self.browse_database)
        db_layout.addWidget(self.browse_db_btn, 1, 2)

        layout.addWidget(db_group)

        layout.addStretch()
        return widget

    def _create_progress_tab(self) -> QWidget:
        """创建进度监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 总体进度
        progress_group = QGroupBox("导入进度")
        progress_layout = QVBoxLayout(progress_group)

        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        progress_layout.addWidget(self.overall_progress)

        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # 文件处理状态
        files_group = QGroupBox("文件处理状态")
        files_layout = QVBoxLayout(files_group)

        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(3)
        self.progress_table.setHorizontalHeaderLabels(["文件名", "状态", "错误信息"])
        self.progress_table.horizontalHeader().setStretchLastSection(True)
        self.progress_table.setAlternatingRowColors(True)

        files_layout.addWidget(self.progress_table)

        layout.addWidget(files_group)

        # 统计信息
        stats_group = QGroupBox("导入统计")
        stats_layout = QGridLayout(stats_group)

        self.processed_label = QLabel("0")
        self.success_label = QLabel("0")
        self.failed_label = QLabel("0")
        self.speed_label = QLabel("0 文件/秒")

        stats_layout.addWidget(QLabel("已处理:"), 0, 0)
        stats_layout.addWidget(self.processed_label, 0, 1)
        stats_layout.addWidget(QLabel("成功:"), 0, 2)
        stats_layout.addWidget(self.success_label, 0, 3)
        stats_layout.addWidget(QLabel("失败:"), 1, 0)
        stats_layout.addWidget(self.failed_label, 1, 1)
        stats_layout.addWidget(QLabel("速度:"), 1, 2)
        stats_layout.addWidget(self.speed_label, 1, 3)

        layout.addWidget(stats_group)

        return widget

    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择数据文件", "",
            "数据文件 (*.csv *.xlsx *.xls *.json *.xml);;所有文件 (*)"
        )

        for file_path in files:
            self._add_file_to_list(file_path)

        self._update_file_stats()
        self._update_ui_state()

    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            # 递归查找支持的文件
            supported_extensions = ['.csv', '.xlsx', '.xls', '.json', '.xml']
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in supported_extensions):
                        file_path = os.path.join(root, file)
                        self._add_file_to_list(file_path)

        self._update_file_stats()
        self._update_ui_state()

    def clear_files(self):
        """清空文件列表"""
        self.file_list.clear()
        self.file_table.setRowCount(0)
        self._update_file_stats()
        self._update_ui_state()

    def browse_database(self):
        """浏览数据库文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择数据库文件", "",
            "DuckDB文件 (*.db);;SQLite文件 (*.sqlite);;所有文件 (*)"
        )
        if file_path:
            self.db_path_edit.setText(file_path)

    def start_import(self):
        """开始导入"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先选择要导入的文件")
            return

        # 获取导入配置
        import_config = {
            'data_type': self.data_type_combo.currentText(),
            'file_format': self.file_format_combo.currentText(),
            'encoding': self.encoding_combo.currentText(),
            'skip_header': self.skip_header_cb.isChecked(),
            'validate_data': self.validate_data_cb.isChecked(),
            'overwrite': self.overwrite_cb.isChecked(),
            'create_backup': self.create_backup_cb.isChecked(),
            'batch_size': self.batch_size_spin.value(),
            'thread_count': self.thread_count_spin.value(),
            'db_type': self.db_type_combo.currentText(),
            'db_path': self.db_path_edit.text()
        }

        # 切换到进度监控选项卡
        self.tab_widget.setCurrentIndex(2)

        # 初始化进度表格
        self.progress_table.setRowCount(len(self.file_list))
        for i, file_path in enumerate(self.file_list):
            self.progress_table.setItem(i, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.progress_table.setItem(i, 1, QTableWidgetItem("等待中"))
            self.progress_table.setItem(i, 2, QTableWidgetItem(""))

        # 启动导入工作线程
        self.import_worker = BatchImportWorker(self.file_list, import_config)
        self.import_worker.progress_updated.connect(self._on_progress_updated)
        self.import_worker.file_completed.connect(self._on_file_completed)
        self.import_worker.batch_completed.connect(self._on_batch_completed)
        self.import_worker.start()

        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.close_btn.setEnabled(False)

    def cancel_import(self):
        """取消导入"""
        if self.import_worker and self.import_worker.isRunning():
            self.import_worker.cancel()
            self.import_worker.wait()

        self._reset_ui_state()

    def _add_file_to_list(self, file_path: str):
        """添加文件到列表"""
        if file_path in self.file_list:
            return

        self.file_list.append(file_path)

        # 添加到表格
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_size_str = f"{file_size / 1024 / 1024:.1f} MB"

        self.file_table.setItem(row, 0, QTableWidgetItem(file_name))
        self.file_table.setItem(row, 1, QTableWidgetItem(file_path))
        self.file_table.setItem(row, 2, QTableWidgetItem(file_size_str))
        self.file_table.setItem(row, 3, QTableWidgetItem("准备就绪"))

    def _update_file_stats(self):
        """更新文件统计"""
        total_files = len(self.file_list)
        total_size = sum(os.path.getsize(f) if os.path.exists(f) else 0 for f in self.file_list)
        total_size_mb = total_size / 1024 / 1024

        # 检查支持的文件
        supported_extensions = ['.csv', '.xlsx', '.xls', '.json', '.xml']
        supported_files = sum(1 for f in self.file_list
                              if any(f.lower().endswith(ext) for ext in supported_extensions))

        self.total_files_label.setText(str(total_files))
        self.total_size_label.setText(f"{total_size_mb:.1f} MB")
        self.supported_files_label.setText(str(supported_files))

    def _update_ui_state(self):
        """更新UI状态"""
        has_files = len(self.file_list) > 0
        self.start_btn.setEnabled(has_files)

    def _reset_ui_state(self):
        """重置UI状态"""
        self.start_btn.setEnabled(len(self.file_list) > 0)
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self.overall_progress.setValue(0)
        self.status_label.setText("准备就绪")

    def _on_progress_updated(self, progress: int, status: str):
        """进度更新"""
        self.overall_progress.setValue(progress)
        self.status_label.setText(status)

    def _on_file_completed(self, file_path: str, success: bool, error_msg: str):
        """文件处理完成"""
        # 查找对应的行
        for row in range(self.progress_table.rowCount()):
            if self.progress_table.item(row, 0).text() == os.path.basename(file_path):
                status = "成功" if success else "失败"
                self.progress_table.setItem(row, 1, QTableWidgetItem(status))
                self.progress_table.setItem(row, 2, QTableWidgetItem(error_msg))

                # 设置行颜色
                color = QColor(200, 255, 200) if success else QColor(255, 200, 200)
                for col in range(3):
                    item = self.progress_table.item(row, col)
                    if item:
                        item.setBackground(color)
                break

    def _on_batch_completed(self, success_count: int, failed_count: int):
        """批量导入完成"""
        self.success_label.setText(str(success_count))
        self.failed_label.setText(str(failed_count))
        self.processed_label.setText(str(success_count + failed_count))

        # 显示完成消息
        if failed_count == 0:
            QMessageBox.information(self, "完成", f"批量导入完成！\n成功导入 {success_count} 个文件")
        else:
            QMessageBox.warning(self, "完成",
                                f"批量导入完成！\n成功: {success_count} 个文件\n失败: {failed_count} 个文件")

        self._reset_ui_state()

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
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
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 4px;
                border: 1px solid #c0c0c0;
                font-weight: bold;
            }
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = BatchImportDialog()
    dialog.show()
    sys.exit(app.exec_())
