"""
底部面板模块

包含日志显示、状态信息和系统监控功能
"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QSplitter, QCheckBox, QComboBox, QPlainTextEdit
)
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont, QColor
import psutil
import time
from datetime import datetime
from core.logger import LogManager
import traceback


class BottomPanel(QWidget):
    """底部面板 - 日志、状态和监控"""

    # 定义信号
    log_cleared = pyqtSignal()  # 日志清除信号
    log_exported = pyqtSignal(str)  # 日志导出信号
    system_alert = pyqtSignal(str)  # 系统警报信号

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.log_manager = log_manager or LogManager()

        # 初始化属性
        self.log_entries = []
        self.max_log_entries = 1000
        self.system_monitor_enabled = True

        # 初始化UI
        self.init_ui()
        self.init_system_monitor()
        self.connect_signals()

    def init_ui(self):
        """初始化用户界面"""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)

            # 创建标签页控件
            self.tab_widget = QTabWidget()
            layout.addWidget(self.tab_widget)

            # 创建各个标签页
            self.create_log_tab()
            self.create_system_monitor_tab()
            self.create_performance_tab()

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化底部面板UI失败: {str(e)}")

    def create_log_tab(self):
        """创建日志标签页"""
        try:
            log_widget = QWidget()
            layout = QVBoxLayout(log_widget)

            # 日志控制区域
            control_layout = QHBoxLayout()

            # 日志级别筛选
            control_layout.addWidget(QLabel("日志级别:"))
            self.log_level_combo = QComboBox()
            self.log_level_combo.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
            self.log_level_combo.currentTextChanged.connect(self.filter_logs)
            control_layout.addWidget(self.log_level_combo)

            # 自动滚动选项
            self.auto_scroll_checkbox = QCheckBox("自动滚动")
            self.auto_scroll_checkbox.setChecked(True)
            control_layout.addWidget(self.auto_scroll_checkbox)

            control_layout.addStretch()

            # 控制按钮
            self.clear_log_btn = QPushButton("清除日志")
            self.clear_log_btn.clicked.connect(self.clear_logs)
            control_layout.addWidget(self.clear_log_btn)

            self.export_log_btn = QPushButton("导出日志")
            control_layout.addWidget(self.export_log_btn)

            layout.addLayout(control_layout)

            # 日志显示区域
            self.log_text = QPlainTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumBlockCount(self.max_log_entries)

            # 设置等宽字体
            font = QFont("Consolas", 9)
            font.setStyleHint(QFont.Monospace)
            self.log_text.setFont(font)

            layout.addWidget(self.log_text)

            self.tab_widget.addTab(log_widget, "日志")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建日志标签页失败: {str(e)}")

    def create_system_monitor_tab(self):
        """创建系统监控标签页"""
        try:
            monitor_widget = QWidget()
            layout = QVBoxLayout(monitor_widget)

            # 系统信息组
            system_group = QGroupBox("系统信息")
            system_layout = QGridLayout(system_group)

            # CPU使用率
            system_layout.addWidget(QLabel("CPU使用率:"), 0, 0)
            self.cpu_label = QLabel("0%")
            system_layout.addWidget(self.cpu_label, 0, 1)

            self.cpu_progress = QProgressBar()
            self.cpu_progress.setMaximum(100)
            system_layout.addWidget(self.cpu_progress, 0, 2)

            # 内存使用率
            system_layout.addWidget(QLabel("内存使用率:"), 1, 0)
            self.memory_label = QLabel("0%")
            system_layout.addWidget(self.memory_label, 1, 1)

            self.memory_progress = QProgressBar()
            self.memory_progress.setMaximum(100)
            system_layout.addWidget(self.memory_progress, 1, 2)

            # 磁盘使用率
            system_layout.addWidget(QLabel("磁盘使用率:"), 2, 0)
            self.disk_label = QLabel("0%")
            system_layout.addWidget(self.disk_label, 2, 1)

            self.disk_progress = QProgressBar()
            self.disk_progress.setMaximum(100)
            system_layout.addWidget(self.disk_progress, 2, 2)

            layout.addWidget(system_group)

            # 进程信息组
            process_group = QGroupBox("进程信息")
            process_layout = QVBoxLayout(process_group)

            self.process_table = QTableWidget()
            self.process_table.setColumnCount(4)
            self.process_table.setHorizontalHeaderLabels(["进程名", "PID", "CPU%", "内存%"])
            process_layout.addWidget(self.process_table)

            layout.addWidget(process_group)

            self.tab_widget.addTab(monitor_widget, "系统监控")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建系统监控标签页失败: {str(e)}")

    def create_performance_tab(self):
        """创建性能监控标签页"""
        try:
            perf_widget = QWidget()
            layout = QVBoxLayout(perf_widget)

            # 应用性能组
            app_group = QGroupBox("应用性能")
            app_layout = QGridLayout(app_group)

            # 响应时间
            app_layout.addWidget(QLabel("平均响应时间:"), 0, 0)
            self.response_time_label = QLabel("0ms")
            app_layout.addWidget(self.response_time_label, 0, 1)

            # 数据处理速度
            app_layout.addWidget(QLabel("数据处理速度:"), 1, 0)
            self.processing_speed_label = QLabel("0 条/秒")
            app_layout.addWidget(self.processing_speed_label, 1, 1)

            # 错误率
            app_layout.addWidget(QLabel("错误率:"), 2, 0)
            self.error_rate_label = QLabel("0%")
            app_layout.addWidget(self.error_rate_label, 2, 1)

            layout.addWidget(app_group)

            # 数据库性能组
            db_group = QGroupBox("数据库性能")
            db_layout = QGridLayout(db_group)

            # 查询时间
            db_layout.addWidget(QLabel("平均查询时间:"), 0, 0)
            self.query_time_label = QLabel("0ms")
            db_layout.addWidget(self.query_time_label, 0, 1)

            # 连接数
            db_layout.addWidget(QLabel("活跃连接数:"), 1, 0)
            self.connection_count_label = QLabel("0")
            db_layout.addWidget(self.connection_count_label, 1, 1)

            layout.addWidget(db_group)

            self.tab_widget.addTab(perf_widget, "性能监控")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"创建性能监控标签页失败: {str(e)}")

    def init_system_monitor(self):
        """初始化系统监控定时器"""
        try:
            self.monitor_timer = QTimer()
            self.monitor_timer.timeout.connect(self.update_system_info)
            self.monitor_timer.start(2000)  # 每2秒更新一次

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化系统监控失败: {str(e)}")

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接按钮信号
            if hasattr(self, 'export_log_btn'):
                self.export_log_btn.clicked.connect(self.export_logs)

            self.log_manager.info("底部面板信号连接完成")

        except Exception as e:
            self.log_manager.error(f"连接底部面板信号失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())

    def add_log_entry(self, level: str, message: str, timestamp: str = None):
        """添加日志条目"""
        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 创建日志条目
            log_entry = {
                'timestamp': timestamp,
                'level': level,
                'message': message
            }

            self.log_entries.append(log_entry)

            # 限制日志条目数量
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries.pop(0)

            # 更新显示
            self.update_log_display()

        except Exception as e:
            print(f"添加日志条目失败: {str(e)}")

    def update_log_display(self):
        """更新日志显示"""
        try:
            current_level = self.log_level_combo.currentText()

            # 清空当前显示
            self.log_text.clear()

            # 过滤并显示日志
            for entry in self.log_entries:
                if current_level == "全部" or entry['level'] == current_level:
                    # 格式化日志条目（不使用HTML）
                    formatted_entry = f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}"
                    self.log_text.appendPlainText(formatted_entry)

            # 自动滚动到底部
            if self.auto_scroll_checkbox.isChecked():
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.End)
                self.log_text.setTextCursor(cursor)

        except Exception as e:
            print(f"更新日志显示失败: {str(e)}")

    def get_log_color(self, level: str) -> str:
        """获取日志级别对应的颜色"""
        colors = {
            'DEBUG': '#808080',
            'INFO': '#000000',
            'WARNING': '#FFA500',
            'ERROR': '#FF0000',
            'CRITICAL': '#8B0000'
        }
        return colors.get(level, '#000000')

    def filter_logs(self, level: str):
        """过滤日志"""
        self.update_log_display()

    def clear_logs(self):
        """清除日志"""
        try:
            self.log_entries.clear()
            self.log_text.clear()
            self.log_cleared.emit()

            if self.log_manager:
                self.log_manager.info("日志已清除")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"清除日志失败: {str(e)}")

    def export_logs(self):
        """导出日志 - 委托给LogWidget处理"""
        try:
            # 如果有LogWidget实例，委托给它处理（功能更完整）
            if hasattr(self.parent(), 'log_widget') and self.parent().log_widget:
                self.parent().log_widget.export_logs()
                return

            # 备用方案：简单导出
            from PyQt5.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt);;All Files (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for entry in self.log_entries:
                        f.write(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n")

                self.log_exported.emit(file_path)

                if self.log_manager:
                    self.log_manager.info(f"日志已导出到: {file_path}")

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"导出日志失败: {str(e)}")

    def update_system_info(self):
        """更新系统信息"""
        try:
            if not self.system_monitor_enabled:
                return

            # 更新CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_label.setText(f"{cpu_percent:.1f}%")
            self.cpu_progress.setValue(int(cpu_percent))

            # 更新内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.memory_label.setText(f"{memory_percent:.1f}%")
            self.memory_progress.setValue(int(memory_percent))

            # 更新磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_label.setText(f"{disk_percent:.1f}%")
            self.disk_progress.setValue(int(disk_percent))

            # 更新进程信息
            self.update_process_info()

            # 检查系统警报
            self.check_system_alerts(cpu_percent, memory_percent, disk_percent)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新系统信息失败: {str(e)}")

    def update_process_info(self):
        """更新进程信息"""
        try:
            # 检查process_table是否存在且未被删除
            if not hasattr(self, 'process_table') or self.process_table is None:
                return

            # 检查对象是否仍然有效
            try:
                # 尝试访问对象的一个简单属性来检查是否有效
                _ = self.process_table.rowCount()
            except RuntimeError:
                # 对象已被删除，直接返回
                return

            # 获取当前进程信息
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # 按CPU使用率排序，取前10个
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            top_processes = processes[:10]

            # 更新表格
            self.process_table.setRowCount(len(top_processes))
            for i, proc in enumerate(top_processes):
                self.process_table.setItem(i, 0, QTableWidgetItem(proc['name'] or 'N/A'))
                self.process_table.setItem(i, 1, QTableWidgetItem(str(proc['pid'])))
                self.process_table.setItem(i, 2, QTableWidgetItem(f"{proc['cpu_percent'] or 0:.1f}%"))
                self.process_table.setItem(i, 3, QTableWidgetItem(f"{proc['memory_percent'] or 0:.1f}%"))

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"更新进程信息失败: {str(e)}")

    def check_system_alerts(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """检查系统警报"""
        try:
            alerts = []

            if cpu_percent > 90:
                alerts.append(f"CPU使用率过高: {cpu_percent:.1f}%")

            if memory_percent > 90:
                alerts.append(f"内存使用率过高: {memory_percent:.1f}%")

            if disk_percent > 90:
                alerts.append(f"磁盘使用率过高: {disk_percent:.1f}%")

            for alert in alerts:
                self.system_alert.emit(alert)
                if self.log_manager:
                    self.log_manager.warning(alert)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"检查系统警报失败: {str(e)}")

    def set_system_monitor_enabled(self, enabled: bool):
        """设置系统监控开关"""
        self.system_monitor_enabled = enabled
        if enabled:
            self.monitor_timer.start(2000)
        else:
            self.monitor_timer.stop()

    def get_log_count(self) -> int:
        """获取日志条目数量"""
        return len(self.log_entries)

    def get_system_status(self) -> dict:
        """获取系统状态信息"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=None),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                'log_count': len(self.log_entries)
            }
        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"获取系统状态失败: {str(e)}")
            return {}