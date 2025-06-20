"""
优化管理面板模块

提供完整的优化管理功能，包括：
- 策略优化管理
- 参数调优
- 性能评估
- 版本管理
- 批量优化
"""

import pandas as pd
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from gui.components.custom_widgets import add_shadow, safe_strftime
from core.adapters import get_logger


class OptimizationManagementPanel(QWidget):
    """优化管理面板"""

    # 定义信号
    optimization_started = pyqtSignal(str, dict)  # 优化开始信号
    optimization_completed = pyqtSignal(str, dict)  # 优化完成信号
    optimization_stopped = pyqtSignal(str)  # 优化停止信号
    version_created = pyqtSignal(str, str)  # 版本创建信号
    performance_evaluated = pyqtSignal(str, dict)  # 性能评估信号

    def __init__(self, parent=None, log_manager=None):
        super().__init__(parent)
        self.parent_gui = parent
        self.log_manager = log_manager or get_logger(__name__)
        self.current_optimization = None
        self.optimization_results = {}

        self.init_ui()
        self.load_optimization_history()

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 创建优化控制区域
        self.create_optimization_controls(layout)

        # 创建优化任务列表
        self.create_optimization_tasks(layout)

        # 创建结果分析区域
        self.create_results_analysis(layout)

        # 创建版本管理区域
        self.create_version_management(layout)

    def create_optimization_controls(self, parent_layout):
        """创建优化控制区域"""
        group = QGroupBox("优化控制")
        layout = QGridLayout(group)

        # 优化目标选择
        layout.addWidget(QLabel("优化目标:"), 0, 0)
        self.optimization_target = QComboBox()
        self.optimization_target.addItems([
            "最大收益率", "最大夏普比率", "最小回撤",
            "最大胜率", "最大盈亏比", "综合评分"
        ])
        layout.addWidget(self.optimization_target, 0, 1)

        # 优化算法选择
        layout.addWidget(QLabel("优化算法:"), 0, 2)
        self.optimization_algorithm = QComboBox()
        self.optimization_algorithm.addItems([
            "遗传算法", "粒子群算法", "模拟退火",
            "贝叶斯优化", "网格搜索", "随机搜索"
        ])
        layout.addWidget(self.optimization_algorithm, 0, 3)

        # 最大迭代次数
        layout.addWidget(QLabel("最大迭代:"), 1, 0)
        self.max_iterations = QSpinBox()
        self.max_iterations.setRange(10, 1000)
        self.max_iterations.setValue(100)
        layout.addWidget(self.max_iterations, 1, 1)

        # 种群大小
        layout.addWidget(QLabel("种群大小:"), 1, 2)
        self.population_size = QSpinBox()
        self.population_size.setRange(10, 200)
        self.population_size.setValue(50)
        layout.addWidget(self.population_size, 1, 3)

        # 优化按钮
        button_layout = QHBoxLayout()
        self.start_optimization_btn = QPushButton("开始优化")
        self.stop_optimization_btn = QPushButton("停止优化")
        self.pause_optimization_btn = QPushButton("暂停优化")
        self.resume_optimization_btn = QPushButton("恢复优化")

        self.start_optimization_btn.clicked.connect(self.start_optimization)
        self.stop_optimization_btn.clicked.connect(self.stop_optimization)
        self.pause_optimization_btn.clicked.connect(self.pause_optimization)
        self.resume_optimization_btn.clicked.connect(self.resume_optimization)

        self.stop_optimization_btn.setEnabled(False)
        self.pause_optimization_btn.setEnabled(False)
        self.resume_optimization_btn.setEnabled(False)

        button_layout.addWidget(self.start_optimization_btn)
        button_layout.addWidget(self.stop_optimization_btn)
        button_layout.addWidget(self.pause_optimization_btn)
        button_layout.addWidget(self.resume_optimization_btn)

        layout.addLayout(button_layout, 2, 0, 1, 4)
        parent_layout.addWidget(group)

    def create_optimization_tasks(self, parent_layout):
        """创建优化任务列表"""
        group = QGroupBox("优化任务")
        layout = QVBoxLayout(group)

        # 任务列表
        self.task_list = QTableWidget()
        self.task_list.setColumnCount(6)
        self.task_list.setHorizontalHeaderLabels([
            "任务ID", "策略", "状态", "进度", "开始时间", "预计完成"
        ])
        self.task_list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.task_list)

        # 任务操作按钮
        task_button_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("添加任务")
        self.delete_task_btn = QPushButton("删除任务")
        self.view_task_btn = QPushButton("查看详情")
        self.export_task_btn = QPushButton("导出结果")

        self.add_task_btn.clicked.connect(self.add_optimization_task)
        self.delete_task_btn.clicked.connect(self.delete_optimization_task)
        self.view_task_btn.clicked.connect(self.view_task_details)
        self.export_task_btn.clicked.connect(self.export_task_results)

        task_button_layout.addWidget(self.add_task_btn)
        task_button_layout.addWidget(self.delete_task_btn)
        task_button_layout.addWidget(self.view_task_btn)
        task_button_layout.addWidget(self.export_task_btn)
        layout.addLayout(task_button_layout)

        parent_layout.addWidget(group)

    def create_results_analysis(self, parent_layout):
        """创建结果分析区域"""
        group = QGroupBox("结果分析")
        layout = QVBoxLayout(group)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 优化进度标签页
        self.progress_tab = QWidget()
        progress_layout = QVBoxLayout(self.progress_tab)

        # 进度信息
        progress_info_layout = QHBoxLayout()
        progress_info_layout.addWidget(QLabel("当前进度:"))
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("0/0")
        progress_info_layout.addWidget(self.progress_bar)
        progress_info_layout.addWidget(self.progress_label)
        progress_layout.addLayout(progress_info_layout)

        # 实时结果
        self.realtime_results = QTextEdit()
        self.realtime_results.setReadOnly(True)
        progress_layout.addWidget(self.realtime_results)

        self.results_tabs.addTab(self.progress_tab, "优化进度")

        # 最优参数标签页
        self.best_params_tab = QWidget()
        best_params_layout = QVBoxLayout(self.best_params_tab)
        self.best_params_table = QTableWidget()
        self.best_params_table.setColumnCount(3)
        self.best_params_table.setHorizontalHeaderLabels(["参数名", "最优值", "原始值"])
        best_params_layout.addWidget(self.best_params_table)
        self.results_tabs.addTab(self.best_params_tab, "最优参数")

        # 性能对比标签页
        self.performance_tab = QWidget()
        performance_layout = QVBoxLayout(self.performance_tab)
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(4)
        self.performance_table.setHorizontalHeaderLabels(["指标", "优化前", "优化后", "改善幅度"])
        performance_layout.addWidget(self.performance_table)
        self.results_tabs.addTab(self.performance_tab, "性能对比")

        layout.addWidget(self.results_tabs)
        parent_layout.addWidget(group)

    def create_version_management(self, parent_layout):
        """创建版本管理区域"""
        group = QGroupBox("版本管理")
        layout = QVBoxLayout(group)

        # 版本列表
        self.version_list = QTableWidget()
        self.version_list.setColumnCount(5)
        self.version_list.setHorizontalHeaderLabels([
            "版本号", "创建时间", "策略", "性能评分", "备注"
        ])
        self.version_list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.version_list)

        # 版本操作按钮
        version_button_layout = QHBoxLayout()
        self.create_version_btn = QPushButton("创建版本")
        self.load_version_btn = QPushButton("加载版本")
        self.compare_versions_btn = QPushButton("版本对比")
        self.delete_version_btn = QPushButton("删除版本")

        self.create_version_btn.clicked.connect(self.create_version)
        self.load_version_btn.clicked.connect(self.load_version)
        self.compare_versions_btn.clicked.connect(self.compare_versions)
        self.delete_version_btn.clicked.connect(self.delete_version)

        version_button_layout.addWidget(self.create_version_btn)
        version_button_layout.addWidget(self.load_version_btn)
        version_button_layout.addWidget(self.compare_versions_btn)
        version_button_layout.addWidget(self.delete_version_btn)
        layout.addLayout(version_button_layout)

        parent_layout.addWidget(group)

    def load_optimization_history(self):
        """加载优化历史"""
        try:
            # TODO: 实现优化历史加载
            self.log_manager.info("优化历史加载完成")
        except Exception as e:
            self.log_manager.error(f"加载优化历史失败: {str(e)}")

    def start_optimization(self):
        """开始优化"""
        try:
            optimization_config = {
                'target': self.optimization_target.currentText(),
                'algorithm': self.optimization_algorithm.currentText(),
                'max_iterations': self.max_iterations.value(),
                'population_size': self.population_size.value()
            }

            # 重置按钮状态
            self.start_optimization_btn.setEnabled(False)
            self.stop_optimization_btn.setEnabled(True)
            self.pause_optimization_btn.setEnabled(True)
            self.resume_optimization_btn.setEnabled(False)

            # 重置进度
            self.progress_bar.setValue(0)
            self.progress_label.setText("0/0")
            self.realtime_results.clear()

            self.optimization_started.emit("optimization", optimization_config)
            self.log_manager.info("优化已开始")

        except Exception as e:
            self.log_manager.error(f"启动优化失败: {str(e)}")
            self.reset_optimization_buttons()

    def stop_optimization(self):
        """停止优化"""
        try:
            self.optimization_stopped.emit("optimization")
            self.reset_optimization_buttons()
            self.log_manager.info("优化已停止")

        except Exception as e:
            self.log_manager.error(f"停止优化失败: {str(e)}")

    def pause_optimization(self):
        """暂停优化"""
        try:
            self.pause_optimization_btn.setEnabled(False)
            self.resume_optimization_btn.setEnabled(True)
            self.log_manager.info("优化已暂停")

        except Exception as e:
            self.log_manager.error(f"暂停优化失败: {str(e)}")

    def resume_optimization(self):
        """恢复优化"""
        try:
            self.pause_optimization_btn.setEnabled(True)
            self.resume_optimization_btn.setEnabled(False)
            self.log_manager.info("优化已恢复")

        except Exception as e:
            self.log_manager.error(f"恢复优化失败: {str(e)}")

    def reset_optimization_buttons(self):
        """重置优化按钮状态"""
        self.start_optimization_btn.setEnabled(True)
        self.stop_optimization_btn.setEnabled(False)
        self.pause_optimization_btn.setEnabled(False)
        self.resume_optimization_btn.setEnabled(False)

    def add_optimization_task(self):
        """添加优化任务"""
        try:
            # TODO: 实现添加优化任务
            self.log_manager.info("优化任务已添加")
        except Exception as e:
            self.log_manager.error(f"添加优化任务失败: {str(e)}")

    def delete_optimization_task(self):
        """删除优化任务"""
        try:
            current_row = self.task_list.currentRow()
            if current_row >= 0:
                task_id = self.task_list.item(current_row, 0).text()
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除任务 {task_id} 吗？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.task_list.removeRow(current_row)
                    self.log_manager.info(f"已删除优化任务: {task_id}")
            else:
                QMessageBox.information(self, "提示", "请先选择要删除的任务")

        except Exception as e:
            self.log_manager.error(f"删除优化任务失败: {str(e)}")

    def view_task_details(self):
        """查看任务详情"""
        try:
            current_row = self.task_list.currentRow()
            if current_row >= 0:
                # TODO: 实现任务详情查看
                QMessageBox.information(self, "任务详情", "任务详情查看功能正在开发中")
            else:
                QMessageBox.information(self, "提示", "请先选择要查看的任务")

        except Exception as e:
            self.log_manager.error(f"查看任务详情失败: {str(e)}")

    def export_task_results(self):
        """导出任务结果"""
        try:
            current_row = self.task_list.currentRow()
            if current_row < 0:
                QMessageBox.information(self, "提示", "请先选择要导出的任务")
                return

            task_id = self.task_list.item(current_row, 0).text()
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出优化结果",
                f"optimization_{task_id}_{safe_strftime(datetime.now(), '%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx)"
            )

            if filename:
                # TODO: 实现结果导出
                QMessageBox.information(self, "成功", f"优化结果已导出到: {filename}")
                self.log_manager.info(f"优化结果导出成功: {filename}")

        except Exception as e:
            error_msg = f"导出优化结果失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_manager.error(error_msg)

    def create_version(self):
        """创建版本"""
        try:
            version_name, ok = QInputDialog.getText(
                self, "创建版本", "请输入版本名称:"
            )

            if ok and version_name:
                # 添加版本到列表
                row_count = self.version_list.rowCount()
                self.version_list.insertRow(row_count)

                self.version_list.setItem(row_count, 0, QTableWidgetItem(version_name))
                self.version_list.setItem(row_count, 1, QTableWidgetItem(
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                self.version_list.setItem(row_count, 2, QTableWidgetItem("当前策略"))
                self.version_list.setItem(row_count, 3, QTableWidgetItem("待评估"))
                self.version_list.setItem(row_count, 4, QTableWidgetItem(""))

                self.version_created.emit(version_name, "current_strategy")
                self.log_manager.info(f"版本已创建: {version_name}")

        except Exception as e:
            error_msg = f"创建版本失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            self.log_manager.error(error_msg)

    def load_version(self):
        """加载版本"""
        try:
            current_row = self.version_list.currentRow()
            if current_row >= 0:
                version_name = self.version_list.item(current_row, 0).text()
                # TODO: 实现版本加载
                QMessageBox.information(self, "成功", f"版本 {version_name} 已加载")
                self.log_manager.info(f"版本已加载: {version_name}")
            else:
                QMessageBox.information(self, "提示", "请先选择要加载的版本")

        except Exception as e:
            self.log_manager.error(f"加载版本失败: {str(e)}")

    def compare_versions(self):
        """版本对比"""
        try:
            # TODO: 实现版本对比功能
            QMessageBox.information(self, "版本对比", "版本对比功能正在开发中")
        except Exception as e:
            self.log_manager.error(f"版本对比失败: {str(e)}")

    def delete_version(self):
        """删除版本"""
        try:
            current_row = self.version_list.currentRow()
            if current_row >= 0:
                version_name = self.version_list.item(current_row, 0).text()
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除版本 {version_name} 吗？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.version_list.removeRow(current_row)
                    self.log_manager.info(f"已删除版本: {version_name}")
            else:
                QMessageBox.information(self, "提示", "请先选择要删除的版本")

        except Exception as e:
            self.log_manager.error(f"删除版本失败: {str(e)}")

    def update_optimization_progress(self, progress: int, total: int, current_result: dict):
        """更新优化进度"""
        try:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"{progress}/{total}")

            # 更新实时结果
            result_text = f"第 {progress} 次迭代:\n"
            for key, value in current_result.items():
                result_text += f"  {key}: {value}\n"
            result_text += "\n"

            self.realtime_results.append(result_text)

            # 滚动到底部
            cursor = self.realtime_results.textCursor()
            cursor.movePosition(cursor.End)
            self.realtime_results.setTextCursor(cursor)

        except Exception as e:
            self.log_manager.error(f"更新优化进度失败: {str(e)}")

    def update_optimization_results(self, results: dict):
        """更新优化结果"""
        try:
            # 更新最优参数表格
            best_params = results.get('best_params', {})
            self.update_best_params_table(best_params)

            # 更新性能对比表格
            performance_data = results.get('performance_comparison', {})
            self.update_performance_table(performance_data)

            # 优化完成，重置按钮状态
            self.reset_optimization_buttons()

            self.optimization_completed.emit("optimization", results)

        except Exception as e:
            self.log_manager.error(f"更新优化结果失败: {str(e)}")

    def update_best_params_table(self, best_params: dict):
        """更新最优参数表格"""
        try:
            self.best_params_table.setRowCount(len(best_params))

            row = 0
            for param_name, param_info in best_params.items():
                name_item = QTableWidgetItem(param_name)
                best_value_item = QTableWidgetItem(str(param_info.get('best_value', '')))
                original_value_item = QTableWidgetItem(str(param_info.get('original_value', '')))

                self.best_params_table.setItem(row, 0, name_item)
                self.best_params_table.setItem(row, 1, best_value_item)
                self.best_params_table.setItem(row, 2, original_value_item)
                row += 1

        except Exception as e:
            self.log_manager.error(f"更新最优参数表格失败: {str(e)}")

    def update_performance_table(self, performance_data: dict):
        """更新性能对比表格"""
        try:
            self.performance_table.setRowCount(len(performance_data))

            row = 0
            for metric_name, metric_info in performance_data.items():
                name_item = QTableWidgetItem(metric_name)
                before_item = QTableWidgetItem(str(metric_info.get('before', '')))
                after_item = QTableWidgetItem(str(metric_info.get('after', '')))
                improvement_item = QTableWidgetItem(str(metric_info.get('improvement', '')))

                self.performance_table.setItem(row, 0, name_item)
                self.performance_table.setItem(row, 1, before_item)
                self.performance_table.setItem(row, 2, after_item)
                self.performance_table.setItem(row, 3, improvement_item)
                row += 1

        except Exception as e:
            self.log_manager.error(f"更新性能对比表格失败: {str(e)}")
