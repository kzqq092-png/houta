#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型训练管理对话框

提供完整的模型训练管理功能，包括：
- 创建训练任务
- 监控训练进度
- 管理模型版本
- 查看训练日志
"""

from loguru import logger
from typing import Dict, Any, List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QSplitter,
    QScrollArea, QFrame, QCheckBox, QDateEdit, QTimeEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ModelTrainingDialog(QDialog):
    """模型训练管理对话框"""

    training_started = pyqtSignal(str)  # 训练任务ID
    training_completed = pyqtSignal(str)  # 训练任务ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logger.bind(module=__name__)

        # 服务引用
        self.training_service = None
        self.service_container = None

        # 初始化服务
        self.init_services()

        # 数据
        self.tasks = []
        self.versions = []
        self.current_task_id = None

        # 定时器用于刷新数据
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(2000)  # 每2秒刷新一次

        # 初始化UI
        self.setup_ui()

        # 加载数据
        self.load_tasks()
        self.load_versions()
        self.load_governance_data()

    def init_services(self):
        """初始化服务"""
        try:
            from core.containers import get_service_container
            from core.services.model_training_service import ModelTrainingService

            self.service_container = get_service_container()
            self.training_service = self.service_container.resolve(ModelTrainingService)

            if not self.training_service:
                raise ValueError("无法获取训练服务")

            self.logger.info("训练服务初始化成功")
        except Exception as e:
            self.logger.error(f"初始化训练服务失败: {e}")
            QMessageBox.critical(self, "错误", f"无法初始化训练服务: {e}")

    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("模型训练管理")
        self.setMinimumSize(1200, 800)
        self.setModal(False)

        # 主布局
        main_layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("模型训练管理系统")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 训练任务标签页
        self.tasks_tab = self.create_tasks_tab()
        self.tabs.addTab(self.tasks_tab, "训练任务")

        # 模型版本标签页
        self.versions_tab = self.create_versions_tab()
        self.tabs.addTab(self.versions_tab, "模型版本")

        # 训练日志标签页
        self.logs_tab = self.create_logs_tab()
        self.tabs.addTab(self.logs_tab, "训练日志")

        # 模型治理标签页
        self.governance_tab = self.create_governance_tab()
        self.tabs.addTab(self.governance_tab, "模型治理")

        # 底部按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

    def create_tasks_tab(self) -> QWidget:
        """创建训练任务标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 工具栏
        toolbar = QHBoxLayout()
        create_btn = QPushButton("创建训练任务")
        create_btn.clicked.connect(self.create_training_task)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_tasks)
        toolbar.addWidget(create_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 任务列表
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(9)
        self.tasks_table.setHorizontalHeaderLabels([
            "任务ID", "任务名称", "模型类型", "状态", "进度", "创建时间", "开始时间", "验证Loss", "操作"
        ])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.doubleClicked.connect(self.view_task_details)
        layout.addWidget(self.tasks_table)

        return widget

    def create_versions_tab(self) -> QWidget:
        """创建模型版本标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 工具栏
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_versions)
        compare_btn = QPushButton("对比版本")
        compare_btn.clicked.connect(self.compare_versions)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(compare_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 版本列表
        self.versions_table = QTableWidget()
        self.versions_table.setColumnCount(8)
        self.versions_table.setHorizontalHeaderLabels([
            "版本号", "模型类型", "训练任务", "性能指标", "成本收益", "创建时间", "当前版本", "操作"
        ])
        self.versions_table.horizontalHeader().setStretchLastSection(True)
        self.versions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.versions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.versions_table.doubleClicked.connect(self.view_version_details)
        layout.addWidget(self.versions_table)

        return widget

    def create_logs_tab(self) -> QWidget:
        """创建训练日志标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 筛选工具栏
        filter_toolbar = QHBoxLayout()
        self.task_filter = QComboBox()
        self.task_filter.setEditable(True)
        self.task_filter.setPlaceholderText("筛选任务ID")
        self.task_filter.currentIndexChanged.connect(self.load_logs)
        self.task_filter.editTextChanged.connect(self.load_logs)
        filter_toolbar.addWidget(QLabel("任务ID:"))
        filter_toolbar.addWidget(self.task_filter)
        filter_toolbar.addStretch()
        layout.addLayout(filter_toolbar)

        # 日志显示
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.logs_text)

        return widget

    def create_governance_tab(self) -> QWidget:
        """创建模型治理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel("根据净收益与Sharpe指标推荐模型，可直接上线")
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        self.governance_table = QTableWidget()
        self.governance_table.setColumnCount(6)
        self.governance_table.setHorizontalHeaderLabels([
            "模型类型", "当前版本", "推荐版本", "净收益", "Sharpe", "上线操作"
        ])
        self.governance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.governance_table, 1)

        refresh_btn = QPushButton("刷新推荐")
        refresh_btn.clicked.connect(self.load_governance_data)
        layout.addWidget(refresh_btn, alignment=Qt.AlignRight)

        return widget

    def create_training_task(self):
        """创建训练任务"""
        dialog = CreateTrainingTaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            task_data = dialog.get_task_data()
            try:
                task_id = self.training_service.create_training_task(
                    task_name=task_data['task_name'],
                    model_type=task_data['model_type'],
                    config=task_data['config'],
                    task_description=task_data.get('description', '')
                )
                QMessageBox.information(self, "成功", f"训练任务创建成功: {task_id}")
                self.load_tasks()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建训练任务失败: {e}")
                self.logger.error(f"创建训练任务失败: {e}")

    def load_tasks(self):
        """加载训练任务列表"""
        try:
            if not self.training_service:
                return

            self.tasks = self.training_service.get_all_tasks()
            self.tasks_table.setRowCount(len(self.tasks))

            for row, task in enumerate(self.tasks):
                # 任务ID
                self.tasks_table.setItem(row, 0, QTableWidgetItem(task.get('task_id', '')))
                # 任务名称
                self.tasks_table.setItem(row, 1, QTableWidgetItem(task.get('task_name', '')))
                # 模型类型
                self.tasks_table.setItem(row, 2, QTableWidgetItem(task.get('model_type', '')))
                # 状态
                status_item = QTableWidgetItem(task.get('status', ''))
                status = task.get('status', '')
                if status == 'completed':
                    status_item.setForeground(QColor(0, 128, 0))
                elif status == 'failed':
                    status_item.setForeground(QColor(255, 0, 0))
                elif status == 'training':
                    status_item.setForeground(QColor(0, 0, 255))
                self.tasks_table.setItem(row, 3, status_item)
                # 进度
                progress = task.get('progress', 0.0)
                progress_item = QTableWidgetItem(f"{progress:.1f}%")
                self.tasks_table.setItem(row, 4, progress_item)
                # 创建时间
                created_at = task.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                self.tasks_table.setItem(row, 5, QTableWidgetItem(created_at))
                # 开始时间
                started_at = task.get('started_at', '')
                if started_at:
                    try:
                        dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                        started_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                self.tasks_table.setItem(row, 6, QTableWidgetItem(started_at))
                # 验证Loss
                metadata = task.get('training_metadata', {})
                latest_val_loss = metadata.get('latest_val_loss')
                val_text = f"{latest_val_loss:.4f}" if latest_val_loss is not None else "--"
                self.tasks_table.setItem(row, 7, QTableWidgetItem(val_text))

                # 操作按钮
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)

                if status == 'pending':
                    start_btn = QPushButton("启动")
                    start_btn.clicked.connect(lambda checked, tid=task['task_id']: self.start_training(tid))
                    action_layout.addWidget(start_btn)
                elif status == 'training':
                    cancel_btn = QPushButton("取消")
                    cancel_btn.clicked.connect(lambda checked, tid=task['task_id']: self.cancel_training(tid))
                    action_layout.addWidget(cancel_btn)

                view_btn = QPushButton("查看")
                view_btn.clicked.connect(lambda checked, tid=task['task_id']: self.view_task_details(tid))
                action_layout.addWidget(view_btn)
                curve_btn = QPushButton("曲线")
                curve_btn.clicked.connect(lambda checked, tid=task['task_id']: self.show_validation_curve(tid))
                action_layout.addWidget(curve_btn)
                action_layout.addStretch()

                self.tasks_table.setCellWidget(row, 8, action_widget)

            self.tasks_table.resizeColumnsToContents()
            self._update_log_task_filter()

        except Exception as e:
            self.logger.error(f"加载训练任务失败: {e}")

    def load_versions(self):
        """加载模型版本列表"""
        try:
            if not self.training_service:
                return

            self.versions = self.training_service.get_all_versions()
            self.versions_table.setRowCount(len(self.versions))

            for row, version in enumerate(self.versions):
                # 版本号
                self.versions_table.setItem(row, 0, QTableWidgetItem(version.get('version_number', '')))
                # 模型类型
                self.versions_table.setItem(row, 1, QTableWidgetItem(version.get('model_type', '')))
                # 训练任务
                self.versions_table.setItem(row, 2, QTableWidgetItem(version.get('training_task_id', '')))
                # 性能指标
                metrics = version.get('performance_metrics', {})
                metrics_str = "N/A"
                if metrics:
                    metrics_parts = []
                    if 'accuracy' in metrics:
                        metrics_parts.append(f"准确率: {metrics['accuracy']:.2%}")
                    if 'mse' in metrics:
                        metrics_parts.append(f"MSE: {metrics['mse']:.4f}")
                    metrics_str = " | ".join(metrics_parts) if metrics_parts else "N/A"
                self.versions_table.setItem(row, 3, QTableWidgetItem(metrics_str))
                cost_text = "N/A"
                if metrics:
                    net_return = metrics.get('net_return')
                    if net_return is not None:
                        cost_text = f"{net_return:.4%}"
                self.versions_table.setItem(row, 4, QTableWidgetItem(cost_text))
                # 创建时间
                created_at = version.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                self.versions_table.setItem(row, 5, QTableWidgetItem(created_at))
                # 当前版本
                is_current = "是" if version.get('is_current', False) else "否"
                current_item = QTableWidgetItem(is_current)
                if version.get('is_current', False):
                    current_item.setForeground(QColor(0, 128, 0))
                self.versions_table.setItem(row, 6, current_item)
                # 操作按钮
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)

                if not version.get('is_current', False):
                    set_current_btn = QPushButton("设为当前")
                    set_current_btn.clicked.connect(lambda checked, vid=version['version_id']: self.set_current_version(vid))
                    action_layout.addWidget(set_current_btn)

                view_btn = QPushButton("查看")
                view_btn.clicked.connect(lambda checked, vid=version['version_id']: self.view_version_details(vid))
                action_layout.addWidget(view_btn)
                curve_btn = QPushButton("曲线")
                curve_btn.clicked.connect(lambda checked, vid=version['version_id']: self.show_version_curve(vid))
                action_layout.addWidget(curve_btn)
                action_layout.addStretch()

                self.versions_table.setCellWidget(row, 7, action_widget)

            self.versions_table.resizeColumnsToContents()

        except Exception as e:
            self.logger.error(f"加载模型版本失败: {e}")

    def load_governance_data(self):
        """加载模型治理推荐数据"""
        try:
            if not self.training_service or not hasattr(self, 'governance_table'):
                return

            versions = self.training_service.get_all_versions()
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for version in versions:
                grouped.setdefault(version.get('model_type', 'unknown'), []).append(version)

            self.governance_table.setRowCount(len(grouped))
            for row, (model_type, version_list) in enumerate(grouped.items()):
                current_version = next((v for v in version_list if v.get('is_current')), None)
                best_version = max(
                    version_list,
                    key=lambda v: v.get('performance_metrics', {}).get('net_return', float('-inf'))
                )

                self.governance_table.setItem(row, 0, QTableWidgetItem(model_type))
                current_text = current_version.get('version_number') if current_version else "--"
                self.governance_table.setItem(row, 1, QTableWidgetItem(current_text))

                best_text = best_version.get('version_number') if best_version else "--"
                self.governance_table.setItem(row, 2, QTableWidgetItem(best_text))

                net_return = best_version.get('performance_metrics', {}).get('net_return')
                sharpe = best_version.get('performance_metrics', {}).get('walk_forward', {}).get('sharpe')
                self.governance_table.setItem(row, 3, QTableWidgetItem(
                    f"{net_return:.4%}" if net_return is not None else "--"))
                self.governance_table.setItem(row, 4, QTableWidgetItem(
                    f"{sharpe:.2f}" if sharpe is not None else "--"))

                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                promote_btn = QPushButton("上线推荐")
                promote_btn.setEnabled(best_version is not None)
                if best_version:
                    promote_btn.clicked.connect(
                        lambda checked, vid=best_version['version_id']: self.set_current_version(vid)
                    )
                action_layout.addWidget(promote_btn)
                action_layout.addStretch()
                self.governance_table.setCellWidget(row, 5, action_widget)

        except Exception as e:
            self.logger.error(f"加载模型治理数据失败: {e}")

    def start_training(self, task_id: str):
        """启动训练任务"""
        try:
            if self.training_service.start_training(task_id):
                QMessageBox.information(self, "成功", "训练任务已启动")
                self.training_started.emit(task_id)
                self.load_tasks()
            else:
                QMessageBox.warning(self, "警告", "启动训练任务失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动训练任务失败: {e}")
            self.logger.error(f"启动训练任务失败: {e}")

    def cancel_training(self, task_id: str):
        """取消训练任务"""
        try:
            reply = QMessageBox.question(self, "确认", "确定要取消训练任务吗？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                if self.training_service.cancel_training(task_id):
                    QMessageBox.information(self, "成功", "训练任务已取消")
                    self.load_tasks()
                else:
                    QMessageBox.warning(self, "警告", "取消训练任务失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"取消训练任务失败: {e}")
            self.logger.error(f"取消训练任务失败: {e}")

    def view_task_details(self, task_id: str = None):
        """查看任务详情"""
        if task_id is None:
            current_row = self.tasks_table.currentRow()
            if current_row < 0:
                return
            task_id = self.tasks_table.item(current_row, 0).text()

        task = self.training_service.get_training_task(task_id)
        if not task:
            QMessageBox.warning(self, "警告", "任务不存在")
            return

        dialog = TaskDetailsDialog(task, self)
        dialog.exec_()

    def show_validation_curve(self, task_id: str):
        """显示指定任务的验证曲线"""
        task = self.training_service.get_training_task(task_id) if self.training_service else None
        metadata = task.get('training_metadata') if task else None
        if not metadata or not metadata.get('val_history'):
            QMessageBox.information(self, "提示", "该任务暂无验证曲线数据")
            return
        dialog = ValidationCurveDialog(metadata, parent=self)
        dialog.exec_()

    def view_version_details(self, version_id: str = None):
        """查看版本详情"""
        if version_id is None:
            current_row = self.versions_table.currentRow()
            if current_row < 0:
                return
            # 需要从版本数据中获取version_id
            version = self.versions[current_row]
            version_id = version.get('version_id')

        version = self.training_service.get_model_version(version_id)
        if not version:
            QMessageBox.warning(self, "警告", "版本不存在")
            return

        dialog = VersionDetailsDialog(version, self)
        dialog.exec_()

    def show_version_curve(self, version_id: str):
        """查看模型版本的验证曲线"""
        version = self.training_service.get_model_version(version_id) if self.training_service else None
        metadata = None
        if version:
            metadata = version.get('training_metadata') or version.get('performance_metrics', {}).get('training_metadata')
        if not metadata or not metadata.get('val_history'):
            QMessageBox.information(self, "提示", "该版本暂无验证曲线数据")
            return
        dialog = ValidationCurveDialog(metadata, parent=self)
        dialog.exec_()

    def set_current_version(self, version_id: str):
        """设置当前版本"""
        try:
            reply = QMessageBox.question(self, "确认", "确定要设置此版本为当前版本吗？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.training_service.set_current_version(version_id)
                QMessageBox.information(self, "成功", "已设置当前版本")
                self.load_versions()
                self.load_governance_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置当前版本失败: {e}")
            self.logger.error(f"设置当前版本失败: {e}")

    def compare_versions(self):
        """对比版本"""
        selected_items = self.versions_table.selectedItems()
        if len(selected_items) < 2:
            QMessageBox.warning(self, "警告", "请选择两个版本进行对比")
            return

        # 获取选中的版本ID
        rows = set(item.row() for item in selected_items)
        if len(rows) != 2:
            QMessageBox.warning(self, "警告", "请选择两个不同的版本")
            return

        row_list = list(rows)
        version1 = self.versions[row_list[0]]
        version2 = self.versions[row_list[1]]

        try:
            comparison = self.training_service.compare_versions(
                version1['version_id'],
                version2['version_id']
            )
            dialog = VersionComparisonDialog(comparison, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"对比版本失败: {e}")
            self.logger.error(f"对比版本失败: {e}")

    def load_logs(self):
        """加载训练日志"""
        try:
            if not self.training_service or not self.logs_text:
                return

            task_id = self._get_selected_log_task_id()
            logs = self.training_service.get_training_logs(task_id=task_id, limit=200)

            log_lines = []
            for entry in logs:
                created_at = entry.get('created_at') or ''
                level = entry.get('log_level', 'INFO')
                task = entry.get('training_task_id', '')
                message = entry.get('log_message', '')
                log_lines.append(f"[{created_at}] [{level}] ({task}) {message}")
            self.logs_text.setPlainText("\n".join(log_lines))
        except Exception as e:
            self.logger.error(f"加载训练日志失败: {e}")

    def _update_log_task_filter(self):
        """更新日志筛选下拉框"""
        if not hasattr(self, 'task_filter') or not self.task_filter:
            return

        current_data = self.task_filter.currentData()
        current_text = self.task_filter.currentText()

        self.task_filter.blockSignals(True)
        self.task_filter.clear()
        self.task_filter.addItem("全部任务", None)

        for task in self.tasks:
            task_id = task.get('task_id')
            if not task_id:
                continue
            task_name = task.get('task_name', task_id)
            display_text = f"{task_name} ({task_id[:8]})"
            self.task_filter.addItem(display_text, task_id)

        if current_data:
            idx = self.task_filter.findData(current_data)
            if idx >= 0:
                self.task_filter.setCurrentIndex(idx)
            else:
                self.task_filter.setCurrentIndex(0)
        elif current_text:
            idx = self.task_filter.findText(current_text)
            if idx >= 0:
                self.task_filter.setCurrentIndex(idx)
            else:
                self.task_filter.setCurrentIndex(0)
        else:
            self.task_filter.setCurrentIndex(0)
        self.task_filter.blockSignals(False)

    def _get_selected_log_task_id(self) -> Optional[str]:
        """获取日志筛选选择的任务ID"""
        if not hasattr(self, 'task_filter') or not self.task_filter:
            return None
        data = self.task_filter.currentData()
        if data:
            return data
        text = self.task_filter.currentText().strip()
        if text and text != "全部任务":
            return text
        return None

    def refresh_data(self):
        """刷新数据"""
        current_index = self.tabs.currentIndex()
        if current_index == 0:  # 训练任务标签页
            self.load_tasks()
        elif current_index == 1:  # 模型版本标签页
            self.load_versions()
        elif current_index == 2:  # 训练日志标签页
            self.load_logs()
        elif current_index == 3:  # 模型治理
            self.load_governance_data()

    def closeEvent(self, event):
        """关闭事件"""
        self.refresh_timer.stop()
        super().closeEvent(event)


class CreateTrainingTaskDialog(QDialog):
    """创建训练任务对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建训练任务")
        self.setMinimumSize(700, 600)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 添加说明标签
        info_label = QLabel(
            "💡 提示：填写股票代码（如sh600000）获取真实K线数据进行训练。\n"
            "如果不填写股票代码，系统将使用合成数据进行训练。"
        )
        info_label.setStyleSheet("background-color: #e3f2fd; padding: 8px; border-radius: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 表单
        form = QFormLayout()

        # 任务名称
        self.task_name_edit = QLineEdit()
        form.addRow("任务名称:", self.task_name_edit)

        # 模型类型
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["pattern", "trend", "price", "sentiment", "risk", "volatility"])
        form.addRow("模型类型:", self.model_type_combo)

        # 任务描述
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form.addRow("任务描述:", self.description_edit)

        # 数据配置
        data_group = QGroupBox("数据配置")
        data_layout = QFormLayout()

        # Symbol
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("例如: sh600000, sz000001")
        data_layout.addRow("股票代码:", self.symbol_edit)

        # Start Date
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        from datetime import datetime, timedelta
        self.start_date_edit.setDate(datetime.now().date() - timedelta(days=365))
        data_layout.addRow("开始日期:", self.start_date_edit)

        # End Date
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(datetime.now().date())
        data_layout.addRow("结束日期:", self.end_date_edit)

        # Prediction Horizon
        self.horizon_spin = QSpinBox()
        self.horizon_spin.setMinimum(1)
        self.horizon_spin.setMaximum(100)
        self.horizon_spin.setValue(5)
        data_layout.addRow("预测视窗:", self.horizon_spin)

        data_group.setLayout(data_layout)
        form.addRow(data_group)

        # 训练配置
        config_group = QGroupBox("训练配置")
        config_layout = QFormLayout()

        # Epochs
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setMinimum(1)
        self.epochs_spin.setMaximum(1000)
        self.epochs_spin.setValue(10)
        config_layout.addRow("训练轮数:", self.epochs_spin)

        # Batch Size
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setMinimum(1)
        self.batch_size_spin.setMaximum(1024)
        self.batch_size_spin.setValue(32)
        config_layout.addRow("批次大小:", self.batch_size_spin)

        # Learning Rate
        self.learning_rate_spin = QDoubleSpinBox()
        self.learning_rate_spin.setMinimum(0.0001)
        self.learning_rate_spin.setMaximum(1.0)
        self.learning_rate_spin.setSingleStep(0.0001)
        self.learning_rate_spin.setValue(0.001)
        self.learning_rate_spin.setDecimals(4)
        config_layout.addRow("学习率:", self.learning_rate_spin)

        config_group.setLayout(config_layout)
        form.addRow(config_group)

        layout.addLayout(form)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def validate_and_accept(self):
        """验证输入并接受"""
        # 验证任务名称
        if not self.task_name_edit.text().strip():
            QMessageBox.warning(self, "验证错误", "请输入任务名称")
            return

        # 验证股票代码
        symbol = self.symbol_edit.text().strip()
        if not symbol:
            reply = QMessageBox.question(
                self, "确认",
                "未提供股票代码，训练将使用合成数据。是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # 验证日期范围
        if self.start_date_edit.date() >= self.end_date_edit.date():
            QMessageBox.warning(self, "验证错误", "开始日期必须早于结束日期")
            return

        self.accept()

    def get_task_data(self) -> Dict[str, Any]:
        """获取任务数据"""
        return {
            'task_name': self.task_name_edit.text(),
            'model_type': self.model_type_combo.currentText(),
            'description': self.description_edit.toPlainText(),
            'config': {
                'data': {
                    'symbol': self.symbol_edit.text().strip(),
                    'start_date': self.start_date_edit.date().toString("yyyy-MM-dd"),
                    'end_date': self.end_date_edit.date().toString("yyyy-MM-dd"),
                    'prediction_horizon': self.horizon_spin.value()
                },
                'epochs': self.epochs_spin.value(),
                'batch_size': self.batch_size_spin.value(),
                'learning_rate': self.learning_rate_spin.value(),
                'prediction_horizon': self.horizon_spin.value()
            }
        }


class TaskDetailsDialog(QDialog):
    """任务详情对话框"""

    def __init__(self, task: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle(f"任务详情: {task.get('task_name', '')}")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 任务信息
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Consolas", 9))

        import json
        task_info = json.dumps(self.task, indent=2, ensure_ascii=False)
        info_text.setPlainText(task_info)

        layout.addWidget(info_text)

        metadata = self.task.get('training_metadata')
        if metadata and metadata.get('val_history'):
            curve_btn = QPushButton("查看验证曲线")
            curve_btn.clicked.connect(lambda: ValidationCurveDialog(metadata, self).exec_())
            layout.addWidget(curve_btn)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)


class VersionDetailsDialog(QDialog):
    """版本详情对话框"""

    def __init__(self, version: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.version = version
        self.setWindowTitle(f"版本详情: {version.get('version_number', '')}")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 版本信息
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Consolas", 9))

        import json
        version_info = json.dumps(self.version, indent=2, ensure_ascii=False)
        info_text.setPlainText(version_info)

        layout.addWidget(info_text)

        metadata = self.version.get('training_metadata') or self.version.get('performance_metrics', {}).get('training_metadata')
        if metadata and metadata.get('val_history'):
            curve_btn = QPushButton("查看验证曲线")
            curve_btn.clicked.connect(lambda: ValidationCurveDialog(metadata, self).exec_())
            layout.addWidget(curve_btn)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)


class VersionComparisonDialog(QDialog):
    """版本对比对话框"""

    def __init__(self, comparison: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.comparison = comparison
        self.setWindowTitle("版本对比")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 对比信息
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Consolas", 9))

        import json
        comparison_info = json.dumps(self.comparison, indent=2, ensure_ascii=False)
        info_text.setPlainText(comparison_info)

        layout.addWidget(info_text)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)


class ValidationCurveDialog(QDialog):
    """验证曲线展示"""

    def __init__(self, metadata: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.metadata = metadata or {}
        self.setWindowTitle("验证损失曲线")
        self.setMinimumSize(700, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        history = self.metadata.get('val_history', [])

        if history:
            figure = Figure(figsize=(5, 3))
            canvas = FigureCanvas(figure)
            ax = figure.add_subplot(111)
            epochs = [entry.get('epoch') for entry in history]
            losses = [entry.get('loss') for entry in history]
            ax.plot(epochs, losses, marker='o', color='#1e88e5', linewidth=0.8, markersize=3)
            ax.set_title("验证集Loss")
            ax.set_xlabel("Epoch", fontsize=8)
            ax.set_ylabel("Loss", fontsize=8)
            ax.tick_params(axis='both', which='major', labelsize=8)
            ax.grid(True, linestyle='--', alpha=0.4)
            layout.addWidget(canvas)

            history_text = QTextEdit()
            history_text.setReadOnly(True)
            lines = [
                f"Epoch {entry.get('epoch')}: Loss={entry.get('loss'):.5f}"
                for entry in history
            ]
            history_text.setPlainText("\n".join(lines))
            layout.addWidget(history_text)
        else:
            layout.addWidget(QLabel("暂无验证记录"))

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
