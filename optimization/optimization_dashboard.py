#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化仪表板
提供实时监控、性能对比、历史记录和系统状态的可视化界面
"""

from analysis.pattern_manager import PatternManager
from optimization.database_schema import OptimizationDatabaseManager
from optimization.performance_evaluator import PerformanceEvaluator
from optimization.version_manager import VersionManager
from optimization.auto_tuner import AutoTuner
import sys
import os
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import threading
import time

# GUI和图表库导入
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
        QGroupBox, QFormLayout, QProgressBar, QTextEdit, QSplitter,
        QTreeWidget, QTreeWidgetItem, QHeaderView, QComboBox, QSpinBox,
        QCheckBox, QSlider, QFrame, QScrollArea, QGridLayout, QMessageBox
    )
    from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QColor, QPalette

    # 核心组件导入
    from core.events import EventBus
    from core.metrics.events import SystemResourceUpdated
    from core.containers import get_service_container
    from core.services import ConfigService

    # 图表库
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        import matplotlib.dates as mdates
        CHARTS_AVAILABLE = True
    except ImportError:
        print("⚠️  matplotlib 未安装，图表功能将受限")
        CHARTS_AVAILABLE = False

    GUI_AVAILABLE = True
except ImportError:
    print("⚠️  PyQt5 未安装，仪表板功能将受限")
    GUI_AVAILABLE = False
    CHARTS_AVAILABLE = False

# 再次确保核心事件类型在全局范围内可用
from core.metrics.events import SystemResourceUpdated

# 导入优化系统组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceChart(QWidget):
    """性能对比图表 - 基于统一图表服务的高性能实现"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 尝试使用统一图表服务
        try:
            from core.services.unified_chart_service import get_unified_chart_service
            from gui.widgets.chart_widget import ChartWidget

            # 创建图表控件
            self.chart_widget = ChartWidget(self)
            layout.addWidget(self.chart_widget)

            # 配置图表
            self.setup_chart()

            self.unified_chart_available = True

        except ImportError:
            # 降级到matplotlib实现
            if CHARTS_AVAILABLE:
                self.figure = Figure(figsize=(10, 6))
                self.canvas = FigureCanvas(self.figure)
                layout.addWidget(self.canvas)
                self.axes = self.figure.add_subplot(111)
                self.figure.tight_layout()
                self.unified_chart_available = False
            else:
                # 完全降级
                self.fallback_label = QLabel("图表服务不可用")
                self.fallback_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(self.fallback_label)
                self.unified_chart_available = False

    def setup_chart(self):
        """设置图表配置"""
        if not hasattr(self, 'chart_widget'):
            return

        try:
            # 获取统一图表服务
            chart_service = get_unified_chart_service()

            # 配置图表类型
            self.chart_widget.set_chart_type('line')

            # 应用主题
            chart_service.apply_theme(self.chart_widget, 'dark')

            # 启用优化
            self.chart_widget.enable_cache(True)
            self.chart_widget.enable_async_rendering(True)

        except Exception as e:
            print(f"图表配置失败: {e}")

    def plot_performance_history(self, pattern_name: str, history_data: List[Dict]):
        """绘制性能历史图表"""
        if self.unified_chart_available and hasattr(self, 'chart_widget'):
            # 使用统一图表服务
            self._plot_with_unified_service(
                pattern_name, history_data, 'history')
        elif hasattr(self, 'axes'):
            # 使用matplotlib降级实现
            self._plot_with_matplotlib(pattern_name, history_data, 'history')
        else:
            # 完全降级
            print(f"无法绘制性能历史图表: {pattern_name}")

    def _plot_with_unified_service(self, pattern_name: str, data: any, chart_type: str):
        """使用统一图表服务绘制"""
        try:
            if chart_type == 'history':
                self._plot_history_with_unified_service(pattern_name, data)
            elif chart_type == 'comparison':
                self._plot_comparison_with_unified_service(data)
            else:
                print(f"未知的图表类型: {chart_type}")

        except Exception as e:
            print(f"统一图表服务绘制失败: {e}")
            # 降级到matplotlib
            if hasattr(self, 'axes'):
                if chart_type == 'history':
                    self._plot_with_matplotlib(pattern_name, data, chart_type)
                elif chart_type == 'comparison':
                    self._plot_comparison_with_matplotlib(data)

    def _plot_history_with_unified_service(self, pattern_name: str, history_data: List[Dict]):
        """使用统一图表服务绘制历史数据"""
        if not history_data:
            # 显示无数据提示
            self.chart_widget.show_message(f"暂无 {pattern_name} 的性能数据")
            return

        # 提取数据
        timestamps = []
        scores = []

        for item in history_data:
            if item.get('test_time'):
                try:
                    timestamp = datetime.fromisoformat(
                        item['test_time'].replace('Z', '+00:00'))
                    timestamps.append(timestamp)
                    scores.append(item.get('overall_score', 0))
                except Exception as e:
                    print(f"解析时间戳失败: {e}")
                    continue

        if not timestamps or not scores:
            self.chart_widget.show_message("数据格式错误")
            return

        # 创建DataFrame
        import pandas as pd
        df = pd.DataFrame({
            'timestamp': timestamps,
            'score': scores
        })
        df.set_index('timestamp', inplace=True)

        # 更新图表数据
        self.chart_widget.update_data(df)
        self.chart_widget.set_title(f'{pattern_name} 性能历史')

        # 添加标注
        if timestamps and scores:
            latest_score = scores[-1]
            self.chart_widget.add_annotation(
                timestamps[-1], latest_score,
                f'最新: {latest_score:.3f}'
            )

    def _plot_comparison_with_unified_service(self, comparison_data: Dict[str, List[float]]):
        """使用统一图表服务绘制对比数据"""
        if not comparison_data:
            self.chart_widget.show_message("暂无对比数据")
            return

        # 提取数据
        patterns = list(comparison_data.keys())
        scores = [comparison_data[pattern][-1] if comparison_data[pattern] else 0
                  for pattern in patterns]

        # 创建DataFrame
        import pandas as pd
        df = pd.DataFrame({
            'pattern': patterns,
            'score': scores
        })

        # 设置图表类型为柱状图
        self.chart_widget.set_chart_type('bar')

        # 更新图表数据
        self.chart_widget.update_data(df)
        self.chart_widget.set_title('形态性能对比')

        # 添加数值标签
        for pattern, score in zip(patterns, scores):
            self.chart_widget.add_annotation(
                pattern, score, f'{score:.3f}'
            )

    def _plot_with_matplotlib(self, pattern_name: str, history_data: List[Dict], chart_type: str):
        """使用matplotlib降级实现"""
        if not hasattr(self, 'axes'):
            return

        self.axes.clear()

        if not history_data:
            self.axes.text(0.5, 0.5, f"暂无 {pattern_name} 的性能数据",
                           ha='center', va='center', transform=self.axes.transAxes)
            if hasattr(self, 'canvas'):
                self.canvas.draw()
            return

        # 提取数据
        timestamps = [datetime.fromisoformat(item['test_time'].replace('Z', '+00:00'))
                      for item in history_data if item.get('test_time')]
        scores = [item.get('overall_score', 0) for item in history_data]

        if not timestamps or not scores:
            self.axes.text(0.5, 0.5, "数据格式错误",
                           ha='center', va='center', transform=self.axes.transAxes)
            if hasattr(self, 'canvas'):
                self.canvas.draw()
            return

        # 绘制折线图
        self.axes.plot(timestamps, scores, 'b-o', linewidth=2, markersize=6)
        self.axes.set_title(f'{pattern_name} 性能历史',
                            fontsize=14, fontweight='bold')
        self.axes.set_xlabel('时间')
        self.axes.set_ylabel('综合评分')
        self.axes.grid(True, alpha=0.3)

        # 格式化x轴
        if CHARTS_AVAILABLE:
            self.axes.xaxis.set_major_formatter(
                mdates.DateFormatter('%m-%d %H:%M'))
            self.axes.xaxis.set_major_locator(mdates.HourLocator(interval=6))
            self.figure.autofmt_xdate()

        # 添加最新分数标注
        if timestamps and scores:
            latest_score = scores[-1]
            self.axes.annotate(f'最新: {latest_score:.3f}',
                               xy=(timestamps[-1], latest_score),
                               xytext=(10, 10), textcoords='offset points',
                               bbox=dict(boxstyle='round,pad=0.3',
                                         facecolor='yellow', alpha=0.7),
                               arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

        if hasattr(self, 'canvas'):
            self.canvas.draw()

    def plot_comparison(self, comparison_data: Dict[str, List[float]]):
        """绘制多形态性能对比"""
        if self.unified_chart_available and hasattr(self, 'chart_widget'):
            # 使用统一图表服务
            self._plot_with_unified_service(
                'comparison', comparison_data, 'comparison')
        elif hasattr(self, 'axes'):
            # 使用matplotlib降级实现
            self._plot_comparison_with_matplotlib(comparison_data)
        else:
            # 完全降级
            print("无法绘制性能对比图表")

    def _plot_comparison_with_matplotlib(self, comparison_data: Dict[str, List[float]]):
        """使用matplotlib绘制对比图表"""
        if not hasattr(self, 'axes'):
            return

        self.axes.clear()

        patterns = list(comparison_data.keys())
        scores = [comparison_data[pattern][-1] if comparison_data[pattern] else 0
                  for pattern in patterns]

        # 创建柱状图
        bars = self.axes.bar(patterns, scores, color='skyblue', alpha=0.7)

        # 添加数值标签
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            self.axes.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                           f'{score:.3f}', ha='center', va='bottom')

        self.axes.set_title('形态性能对比', fontsize=14, fontweight='bold')
        self.axes.set_ylabel('综合评分')
        self.axes.set_ylim(0, 1.0)
        self.axes.grid(True, alpha=0.3)

        # 旋转x轴标签
        self.axes.tick_params(axis='x', rotation=45)

        if hasattr(self, 'canvas'):
            self.canvas.draw()


class OptimizationDashboard(QMainWindow if GUI_AVAILABLE else object):
    """优化仪表板主窗口"""

    # 添加一个信号，用于跨线程安全地更新UI
    stats_updated = pyqtSignal(dict)

    def __init__(self, event_bus: EventBus):
        """初始化"""
        if not GUI_AVAILABLE:
            print("GUI不可用，仪表板将以命令行模式运行")
            return

        super().__init__()

        # 核心组件
        self.auto_tuner = AutoTuner(debug_mode=True)
        self.version_manager = VersionManager()
        self.evaluator = PerformanceEvaluator(debug_mode=True)
        self.pattern_manager = PatternManager()
        self.db_manager = OptimizationDatabaseManager()

        self._event_bus = event_bus
        self._optimization_thread = None

        # 数据
        self.current_pattern = None
        self.performance_history = {}

        self.setWindowTitle("HiKyuu 形态识别优化仪表板")
        self.setGeometry(100, 100, 1400, 900)
        self.init_ui()
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """订阅所有需要的事件。"""
        # 订阅系统资源更新事件
        self._event_bus.subscribe(
            SystemResourceUpdated, self.handle_resource_update)
        # 连接本地信号到UI更新槽
        self.stats_updated.connect(self._update_ui_with_stats)

    def handle_resource_update(self, event: SystemResourceUpdated):
        """
        处理从EventBus收到的SystemResourceUpdated事件。
        在非GUI线程中被调用，通过发射信号来安全更新UI。
        """
        stats = {
            "cpu_percent": event.cpu_percent,
            "memory_percent": event.memory_percent,
        }
        self.stats_updated.emit(stats)

    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # 左侧面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # 右侧面板
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 3)

        # 初始化时刷新所有数据
        self.refresh_all_data()

    def create_left_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QFormLayout()

        self.cpu_label = QLabel("N/A")
        self.memory_label = QLabel("N/A")
        self.active_tasks_label = QLabel("0")
        self.total_versions_label = QLabel("0")

        status_layout.addRow("CPU使用率:", self.cpu_label)
        status_layout.addRow("内存使用率:", self.memory_label)
        status_layout.addRow("活跃任务:", self.active_tasks_label)
        status_layout.addRow("总版本数:", self.total_versions_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 快速操作组
        actions_group = QGroupBox("快速操作")
        actions_layout = QVBoxLayout()

        self.one_click_btn = QPushButton("🚀 一键优化所有形态")
        self.one_click_btn.clicked.connect(self.one_click_optimize)
        actions_layout.addWidget(self.one_click_btn)

        self.smart_optimize_btn = QPushButton("🧠 智能优化")
        self.smart_optimize_btn.clicked.connect(self.smart_optimize)
        actions_layout.addWidget(self.smart_optimize_btn)

        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_all_data)
        actions_layout.addWidget(self.refresh_btn)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # 形态选择组
        pattern_group = QGroupBox("形态选择")
        pattern_layout = QVBoxLayout()

        self.pattern_combo = QComboBox()
        self.pattern_combo.currentTextChanged.connect(self.on_pattern_changed)
        pattern_layout.addWidget(self.pattern_combo)

        self.pattern_optimize_btn = QPushButton("优化选中形态")
        self.pattern_optimize_btn.clicked.connect(
            self.optimize_selected_pattern)
        pattern_layout.addWidget(self.pattern_optimize_btn)

        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)

        # 优化进度组
        progress_group = QGroupBox("优化进度")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        progress_layout.addWidget(self.progress_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        layout.addStretch()
        return panel

    def create_right_panel(self) -> QWidget:
        """创建右侧主面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 性能监控标签页
        self.performance_tab = self.create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "性能监控")

        # 优化历史标签页
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "📋 优化历史")

        # 版本管理标签页
        self.version_tab = self.create_version_tab()
        self.tab_widget.addTab(self.version_tab, "版本管理")

        # 系统日志标签页
        self.log_tab = self.create_log_tab()
        self.tab_widget.addTab(self.log_tab, "📝 系统日志")

        return panel

    def create_performance_tab(self) -> QWidget:
        """创建性能监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 性能图表
        if CHARTS_AVAILABLE:
            self.performance_chart = PerformanceChart()
            layout.addWidget(self.performance_chart)
        else:
            chart_placeholder = QLabel("图表功能需要安装 matplotlib")
            chart_placeholder.setAlignment(Qt.AlignCenter)
            layout.addWidget(chart_placeholder)

        # 性能指标表格
        metrics_group = QGroupBox("当前性能指标")
        metrics_layout = QVBoxLayout()

        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        metrics_layout.addWidget(self.metrics_table)

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        return tab

    def create_history_tab(self) -> QWidget:
        """创建优化历史标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "形态名称", "开始时间", "结束时间", "优化方法",
            "状态", "性能提升", "最佳评分", "迭代次数"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)

        return tab

    def create_version_tab(self) -> QWidget:
        """创建版本管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 版本统计
        stats_group = QGroupBox("版本统计")
        stats_layout = QGridLayout()

        self.total_patterns_label = QLabel("0")
        self.active_versions_label = QLabel("0")
        self.avg_improvement_label = QLabel("0%")

        stats_layout.addWidget(QLabel("总形态数:"), 0, 0)
        stats_layout.addWidget(self.total_patterns_label, 0, 1)
        stats_layout.addWidget(QLabel("活跃版本:"), 0, 2)
        stats_layout.addWidget(self.active_versions_label, 0, 3)
        stats_layout.addWidget(QLabel("平均提升:"), 1, 0)
        stats_layout.addWidget(self.avg_improvement_label, 1, 1)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 版本列表
        self.version_table = QTableWidget()
        self.version_table.setColumnCount(6)
        self.version_table.setHorizontalHeaderLabels([
            "形态名称", "版本号", "创建时间", "优化方法", "性能评分", "状态"
        ])
        self.version_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.version_table)

        return tab

    def create_log_tab(self) -> QWidget:
        """创建系统日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 日志控制
        control_layout = QHBoxLayout()

        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        control_layout.addWidget(self.auto_scroll_check)

        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_log_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        return tab

    def _update_ui_with_stats(self, stats: Dict[str, Any]):
        """使用收集到的统计信息更新UI标签 (槽函数)"""
        cpu_percent = stats.get("cpu_percent", 0)
        self.cpu_label.setText(f"{cpu_percent:.2f}%")

        mem_percent = stats.get("memory_percent", 0)
        self.memory_label.setText(f"{mem_percent:.2f}%")

        # 优化统计数据现在从数据库中定期刷新，而不是从监控线程获取
        # 可以在 refresh_all_data 中更新

    def refresh_all_data(self):
        """刷新所有数据"""
        self.refresh_pattern_list()
        self.refresh_optimization_history()
        self.refresh_version_info()

        # 更新优化统计
        try:
            opt_stats = self.db_manager.get_optimization_statistics()
            self.total_versions_label.setText(
                str(opt_stats.get('total_versions', 'N/A')))
            self.active_tasks_label.setText(
                str(len(self.auto_tuner.running_tasks)))
            self.total_patterns_label.setText(str(len(self.pattern_combo)))
            self.active_versions_label.setText(
                str(opt_stats.get('active_versions', 'N/A')))
            self.avg_improvement_label.setText(
                f"{opt_stats.get('avg_improvement', 'N/A')}%")
        except Exception as e:
            self.log_message(f"刷新优化统计失败: {e}", "error")

    def refresh_pattern_list(self):
        """刷新形态列表"""
        try:
            patterns = self.pattern_manager.get_all_patterns()
            pattern_names = [p.english_name for p in patterns if p.is_active]

            current_text = self.pattern_combo.currentText()
            self.pattern_combo.clear()
            self.pattern_combo.addItems(pattern_names)

            # 恢复之前的选择
            if current_text in pattern_names:
                self.pattern_combo.setCurrentText(current_text)
            elif pattern_names:
                self.pattern_combo.setCurrentIndex(0)

        except Exception as e:
            self.log_message(f"❌ 刷新形态列表失败: {e}")

    def refresh_optimization_history(self):
        """刷新优化历史"""
        try:
            # 获取所有优化日志
            conn = self.db_manager.db_path

            db_conn = sqlite3.connect(conn)
            cursor = db_conn.cursor()

            cursor.execute('''
                SELECT pattern_name, start_time, end_time, optimization_method,
                       status, improvement_percentage, best_score, iterations
                FROM optimization_logs
                ORDER BY start_time DESC
                LIMIT 100
            ''')

            records = cursor.fetchall()
            db_conn.close()

            # 更新表格
            self.history_table.setRowCount(len(records))

            for i, record in enumerate(records):
                for j, value in enumerate(record):
                    if value is None:
                        value = "N/A"
                    # 性能提升和最佳评分
                    elif j in [5, 6] and isinstance(value, (int, float)):
                        value = f"{value:.3f}"

                    self.history_table.setItem(
                        i, j, QTableWidgetItem(str(value)))

        except Exception as e:
            self.log_message(f"❌ 刷新优化历史失败: {e}")

    def refresh_version_info(self):
        """刷新版本信息"""
        try:
            # 获取版本统计
            stats = self.db_manager.get_optimization_statistics()

            self.total_patterns_label.setText(str(len(self.pattern_combo)))
            self.active_versions_label.setText(
                str(stats.get('active_versions', 0)))

            avg_improvement = stats.get('avg_improvement', 0)
            self.avg_improvement_label.setText(f"{avg_improvement:.3f}%")

            # 获取所有版本信息
            conn = self.db_manager.db_path

            db_conn = sqlite3.connect(conn)
            cursor = db_conn.cursor()

            cursor.execute('''
                SELECT av.pattern_name, av.version_number, av.created_time,
                       av.optimization_method, pm.overall_score, av.is_active
                FROM algorithm_versions av
                LEFT JOIN performance_metrics pm ON av.id = pm.version_id
                ORDER BY av.created_time DESC
                LIMIT 50
            ''')

            records = cursor.fetchall()
            db_conn.close()

            # 更新版本表格
            self.version_table.setRowCount(len(records))

            for i, record in enumerate(records):
                for j, value in enumerate(record):
                    if j == 4 and value is not None:  # 性能评分
                        value = f"{value:.3f}"
                    elif j == 5:  # 状态
                        value = "✓ 激活" if value else "未激活"
                    elif value is None:
                        value = "N/A"

                    self.version_table.setItem(
                        i, j, QTableWidgetItem(str(value)))

        except Exception as e:
            self.log_message(f"❌ 刷新版本信息失败: {e}")

    def refresh_performance_data(self, pattern_name: str):
        """刷新性能数据"""
        try:
            # 获取性能历史
            history = self.db_manager.get_performance_history(
                pattern_name, limit=20)

            # 更新图表
            if CHARTS_AVAILABLE and hasattr(self, 'performance_chart'):
                self.performance_chart.plot_performance_history(
                    pattern_name, history)

            # 更新性能指标表格
            if history:
                latest = history[0]
                metrics = [
                    ("综合评分", f"{latest.get('overall_score', 0):.3f}"),
                    ("信号质量", f"{latest.get('signal_quality', 0):.3f}"),
                    ("平均置信度", f"{latest.get('confidence_avg', 0):.3f}"),
                    ("执行时间", f"{latest.get('execution_time', 0):.3f}秒"),
                    ("识别形态数", str(latest.get('patterns_found', 0))),
                    ("鲁棒性", f"{latest.get('robustness_score', 0):.3f}"),
                    ("参数敏感性", f"{latest.get('parameter_sensitivity', 0):.3f}")
                ]

                self.metrics_table.setRowCount(len(metrics))
                for i, (name, value) in enumerate(metrics):
                    self.metrics_table.setItem(i, 0, QTableWidgetItem(name))
                    self.metrics_table.setItem(i, 1, QTableWidgetItem(value))

        except Exception as e:
            self.log_message(f"❌ 刷新性能数据失败: {e}")

    def on_pattern_changed(self, pattern_name: str):
        """形态选择改变"""
        if pattern_name:
            self.current_pattern = pattern_name
            self.refresh_performance_data(pattern_name)
            self.log_message(f"切换到形态: {pattern_name}")

    def one_click_optimize(self):
        """一键优化所有形态"""
        self.log_message("🚀 启动一键优化...")
        self.progress_label.setText("正在优化...")
        self.progress_bar.setValue(0)

        # 在后台线程中执行优化
        def run_optimization():
            try:
                result = self.auto_tuner.one_click_optimize(
                    optimization_method="genetic",
                    max_iterations=20
                )

                summary = result.get("summary", {})
                self.log_message(f"✅ 一键优化完成！")
                self.log_message(f"   总任务数: {summary.get('total_tasks', 0)}")
                self.log_message(
                    f"   成功任务数: {summary.get('successful_tasks', 0)}")
                self.log_message(
                    f"   平均改进: {summary.get('average_improvement', 0):.3f}%")

                self.progress_bar.setValue(100)
                self.progress_label.setText("优化完成")

            except Exception as e:
                self.log_message(f"❌ 一键优化失败: {e}")
                self.progress_label.setText("优化失败")

        # 启动后台线程
        threading.Thread(target=run_optimization, daemon=True).start()

    def smart_optimize(self):
        """智能优化"""
        self.log_message("🧠 启动智能优化...")
        self.progress_label.setText("智能分析中...")

        def run_smart_optimization():
            try:
                result = self.auto_tuner.smart_optimize(
                    performance_threshold=0.7,
                    improvement_target=0.1
                )

                if result.get("status") == "no_optimization_needed":
                    self.log_message("✅ 所有形态性能都达到要求，无需优化")
                else:
                    summary = result.get("summary", {})
                    self.log_message(f"✅ 智能优化完成！")
                    self.log_message(
                        f"   优化形态数: {summary.get('total_tasks', 0)}")
                    self.log_message(
                        f"   平均改进: {summary.get('average_improvement', 0):.3f}%")

                self.progress_label.setText("智能优化完成")

            except Exception as e:
                self.log_message(f"❌ 智能优化失败: {e}")
                self.progress_label.setText("优化失败")

        threading.Thread(target=run_smart_optimization, daemon=True).start()

    def optimize_selected_pattern(self):
        """优化选中的形态"""
        pattern_name = self.pattern_combo.currentText()
        if not pattern_name:
            self.log_message("⚠️  请先选择要优化的形态")
            return

        self.log_message(f"🚀 开始优化形态: {pattern_name}")
        self.progress_label.setText(f"正在优化 {pattern_name}...")

        def run_single_optimization():
            try:
                from optimization.algorithm_optimizer import OptimizationConfig

                config = OptimizationConfig(
                    method="genetic",
                    max_iterations=30,
                    population_size=15
                )

                result = self.auto_tuner.optimizer.optimize_algorithm(
                    pattern_name=pattern_name,
                    config=config
                )

                improvement = result.get("improvement_percentage", 0)
                self.log_message(
                    f"✅ {pattern_name} 优化完成！性能提升: {improvement:.3f}%")
                self.progress_label.setText("优化完成")

                # 刷新数据
                self.refresh_performance_data(pattern_name)

            except Exception as e:
                self.log_message(f"❌ {pattern_name} 优化失败: {e}")
                self.progress_label.setText("优化失败")

        threading.Thread(target=run_single_optimization, daemon=True).start()

    def log_message(self, message: str):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        self.log_text.append(formatted_message)

        # 自动滚动到底部
        if self.auto_scroll_check.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        # 同时输出到控制台
        print(formatted_message)

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_message("📝 日志已清空")

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        self.log_message("正在关闭优化仪表板...")
        if self._optimization_thread and self._optimization_thread.isRunning():
            reply = QMessageBox.question(self, '确认退出',
                                         "优化仍在进行中，确定要退出吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._optimization_thread.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# 全局仪表板实例，确保只有一个
_dashboard_instance = None


def create_optimization_dashboard(event_bus: EventBus) -> OptimizationDashboard:
    """创建并返回优化仪表板的单例"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = OptimizationDashboard(event_bus)
    return _dashboard_instance


def run_dashboard():
    """运行仪表板应用"""
    if not GUI_AVAILABLE:
        print("❌ GUI不可用，无法启动仪表板")
        return

    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 创建仪表板
    dashboard = create_optimization_dashboard(MockEventBus())
    dashboard.show()

    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_dashboard()
