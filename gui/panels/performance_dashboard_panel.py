#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能仪表板面板
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDateTimeEdit, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QDateTime
from datetime import datetime, timedelta

from core.events import EventBus
from core.metrics.events import SystemResourceUpdated
from core.metrics.repository import MetricsRepository

# 尝试导入图表库
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False


class QueryThread(QThread):
    """用于在后台执行数据库查询的线程"""
    query_completed = pyqtSignal(list)

    def __init__(self, repository: MetricsRepository, start_time: datetime, end_time: datetime, table: str, operation: str = None):
        super().__init__()
        self._repository = repository
        self._start_time = start_time
        self._end_time = end_time
        self._table = table
        self._operation = operation

    def run(self):
        """执行查询"""
        try:
            data = self._repository.query_historical_data(
                start_time=self._start_time,
                end_time=self._end_time,
                table=self._table,
                operation_name=self._operation
            )
            self.query_completed.emit(data)
        except Exception as e:
            print(f"查询线程错误: {e}")
            self.query_completed.emit([])


class PerformanceDashboardPanel(QWidget):
    """用于展示系统性能和资源指标的UI面板"""
    resource_updated_signal = pyqtSignal(SystemResourceUpdated)

    def __init__(self, event_bus: EventBus, repository: MetricsRepository, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._repository = repository
        self._query_thread = None

        self.init_ui()
        self._subscribe_to_events()

    def init_ui(self):
        """初始化UI布局"""
        main_layout = QVBoxLayout(self)

        # 1. 实时状态区域
        status_group = QGroupBox("实时系统状态")
        status_layout = QGridLayout()
        self.cpu_label = QLabel("CPU: N/A")
        self.mem_label = QLabel("内存: N/A")
        self.disk_label = QLabel("磁盘: N/A")
        status_layout.addWidget(self.cpu_label, 0, 0)
        status_layout.addWidget(self.mem_label, 0, 1)
        status_layout.addWidget(self.disk_label, 0, 2)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # 2. 历史数据查询区域
        history_group = QGroupBox("历史性能趋势")
        history_layout = QVBoxLayout()

        # 查询条件
        query_controls_layout = QGridLayout()
        self.start_time_edit = QDateTimeEdit(
            QDateTime.currentDateTime().addDays(-1))
        self.end_time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.table_combo = QComboBox()
        self.table_combo.addItems(
            ["resource_metrics_summary", "app_metrics_summary"])
        self.query_button = QPushButton("查询历史数据")
        self.query_button.clicked.connect(self.run_query)

        query_controls_layout.addWidget(QLabel("开始时间:"), 0, 0)
        query_controls_layout.addWidget(self.start_time_edit, 0, 1)
        query_controls_layout.addWidget(QLabel("结束时间:"), 0, 2)
        query_controls_layout.addWidget(self.end_time_edit, 0, 3)
        query_controls_layout.addWidget(QLabel("数据表:"), 0, 4)
        query_controls_layout.addWidget(self.table_combo, 0, 5)
        query_controls_layout.addWidget(self.query_button, 0, 6)
        history_layout.addLayout(query_controls_layout)

        # 历史图表
        if CHARTS_AVAILABLE:
            self.history_canvas = FigureCanvas(Figure(figsize=(10, 4)))
            self.history_ax = self.history_canvas.figure.subplots()
            history_layout.addWidget(self.history_canvas)
        else:
            history_layout.addWidget(QLabel("Matplotlib未安装，图表不可用。"))

        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)

        # 3. 性能排行表格
        ranking_group = QGroupBox("应用性能排行 (最近1小时)")
        ranking_layout = QVBoxLayout()
        self.ranking_table = QTableWidget()
        self.ranking_table.setColumnCount(5)
        self.ranking_table.setHorizontalHeaderLabels(
            ["操作名称", "平均耗时(ms)", "最大耗时(ms)", "调用次数", "错误次数"])
        self.ranking_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ranking_layout.addWidget(self.ranking_table)
        ranking_group.setLayout(ranking_layout)
        main_layout.addWidget(ranking_group)

    def _subscribe_to_events(self):
        """订阅事件总线"""
        self.resource_updated_signal.connect(self._update_resource_ui)
        self._event_bus.subscribe(
            SystemResourceUpdated, self.handle_resource_event)

    def handle_resource_event(self, event: SystemResourceUpdated):
        """事件处理器，在非GUI线程被调用，通过信号转发到主线程"""
        self.resource_updated_signal.emit(event)

    def _update_resource_ui(self, event: SystemResourceUpdated):
        """在主线程中安全地更新UI"""
        self.cpu_label.setText(f"CPU: {event.cpu_percent:.1f}%")
        self.mem_label.setText(f"内存: {event.memory_percent:.1f}%")
        self.disk_label.setText(f"磁盘: {event.disk_percent:.1f}%")

    def run_query(self):
        """启动后台线程执行数据库查询"""
        start_time = self.start_time_edit.dateTime().toPyDateTime()
        end_time = self.end_time_edit.dateTime().toPyDateTime()
        table = self.table_combo.currentText()

        self.query_button.setEnabled(False)
        self.query_button.setText("查询中...")

        self._query_thread = QueryThread(
            self._repository, start_time, end_time, table)
        self._query_thread.query_completed.connect(self.on_query_completed)
        self._query_thread.start()

    def on_query_completed(self, data: list):
        """查询完成后的槽函数"""
        self.query_button.setEnabled(True)
        self.query_button.setText("查询历史数据")

        if not data:
            print("未查询到历史数据。")
            return

        if CHARTS_AVAILABLE:
            self._plot_history_data(data)

        # 如果是应用性能数据，更新表格
        if self.table_combo.currentText() == 'app_metrics_summary':
            self.update_ranking_table(data)

    def _plot_history_data(self, data: list):
        """使用Matplotlib绘制历史数据图表"""
        self.history_ax.clear()

        timestamps = [datetime.fromisoformat(row['t_stamp']) for row in data]

        table = self.table_combo.currentText()
        if table == 'resource_metrics_summary':
            self.history_ax.plot(
                timestamps, [row['cpu'] for row in data], label='CPU %')
            self.history_ax.plot(
                timestamps, [row['mem'] for row in data], label='Memory %')
            self.history_ax.plot(
                timestamps, [row['disk'] for row in data], label='Disk %')
            self.history_ax.set_ylabel("Usage (%)")
        elif table == 'app_metrics_summary':
            # 这里可以根据需要绘制不同的性能指标
            self.history_ax.plot(timestamps, [
                                 row['avg_duration'] * 1000 for row in data], label='Avg Duration (ms)')
            self.history_ax.set_ylabel("Duration (ms)")

        self.history_ax.legend()
        self.history_ax.set_xlabel("Time")
        self.history_ax.xaxis.set_major_formatter(
            mdates.DateFormatter('%H:%M:%S'))
        self.history_ax.figure.autofmt_xdate()
        self.history_canvas.draw()

    def update_ranking_table(self, data: list):
        """用查询到的数据更新性能排行表格"""
        self.ranking_table.setRowCount(0)

        # 聚合数据
        aggregated_data = {}
        for row in data:
            op_name = row['operation']
            if op_name not in aggregated_data:
                aggregated_data[op_name] = {
                    'total_duration': 0, 'max_duration': 0, 'call_count': 0, 'error_count': 0}

            agg = aggregated_data[op_name]
            agg['total_duration'] += row['avg_duration'] * row['call_count']
            agg['max_duration'] = max(agg['max_duration'], row['max_duration'])
            agg['call_count'] += row['call_count']
            agg['error_count'] += row['error_count']

        # 排序
        sorted_ops = sorted(aggregated_data.items(),
                            key=lambda item: (
                                item[1]['total_duration'] / item[1]['call_count']) if item[1]['call_count'] > 0 else 0,
                            reverse=True)

        self.ranking_table.setRowCount(len(sorted_ops))
        for i, (op_name, metrics) in enumerate(sorted_ops):
            avg_duration_ms = (
                metrics['total_duration'] / metrics['call_count'] * 1000) if metrics['call_count'] > 0 else 0
            max_duration_ms = metrics['max_duration'] * 1000

            self.ranking_table.setItem(i, 0, QTableWidgetItem(op_name))
            self.ranking_table.setItem(
                i, 1, QTableWidgetItem(f"{avg_duration_ms:.2f}"))
            self.ranking_table.setItem(
                i, 2, QTableWidgetItem(f"{max_duration_ms:.2f}"))
            self.ranking_table.setItem(
                i, 3, QTableWidgetItem(str(metrics['call_count'])))
            self.ranking_table.setItem(
                i, 4, QTableWidgetItem(str(metrics['error_count'])))

    def dispose(self):
        """清理资源"""
        if self._query_thread and self._query_thread.isRunning():
            self._query_thread.quit()
            self._query_thread.wait()
