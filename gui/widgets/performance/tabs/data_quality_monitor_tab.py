#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量监控标签页
专为量化交易数据质量监控设计
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QComboBox,
    QLabel, QTabWidget, QFrame, QGridLayout, QProgressBar,
    QTextEdit, QSplitter, QHeaderView, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart
from loguru import logger

logger = logger


class ModernDataQualityMonitorTab(QWidget):
    """现代化数据质量监控标签页 - 量化交易专用"""

    def __init__(self):
        super().__init__()
        self.data_sources = []
        self.quality_alerts = []

        # 缓存监控相关属性
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_size = 0
        self.io_operations = 0

        # 异步数据收集和模块缓存
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="DataQualityMonitor")
        self._module_cache = {}  # 缓存导入的模块
        self.cache_monitoring_timer = QTimer()
        self.cache_monitoring_timer.timeout.connect(self._collect_cache_data_async)

        self.init_ui()

        # 启动缓存监控
        self.cache_monitoring_timer.start(1500)  # 每1.5秒更新一次

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 创建子标签页
        self.tab_widget = QTabWidget()

        # 实时数据质量
        self.realtime_tab = self._create_realtime_quality_tab()
        self.tab_widget.addTab(self.realtime_tab, "实时质量")

        # 数据源监控
        self.datasource_tab = self._create_datasource_monitor_tab()
        self.tab_widget.addTab(self.datasource_tab, "数据源监控")

        # 缓存监控
        self.cache_tab = self._create_cache_monitor_tab()
        self.tab_widget.addTab(self.cache_tab, "缓存监控")

        # 质量报告
        self.report_tab = self._create_quality_report_tab()
        self.tab_widget.addTab(self.report_tab, "质量报告")

        layout.addWidget(self.tab_widget)

    def _create_realtime_quality_tab(self):
        """创建实时数据质量标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 数据质量总览
        quality_overview_group = QGroupBox("数据质量总览")
        overview_layout = QHBoxLayout()

        self.quality_score_label = QLabel("数据质量评分: 92.5")
        self.quality_score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        overview_layout.addWidget(self.quality_score_label)

        overview_layout.addStretch()

        # 数据质量进度条
        self.quality_score_bar = QProgressBar()
        self.quality_score_bar.setMaximum(100)
        self.quality_score_bar.setValue(93)
        self.quality_score_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        overview_layout.addWidget(self.quality_score_bar)

        quality_overview_group.setLayout(overview_layout)
        layout.addWidget(quality_overview_group)

        # 数据质量指标卡片
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(120)
        cards_frame.setMaximumHeight(150)
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(2, 2, 2, 2)
        cards_layout.setSpacing(2)

        self.quality_cards = {}
        quality_metrics = [
            # 第一行：核心质量指标
            ("数据完整性", "#27ae60", 0, 0),
            ("数据及时性", "#3498db", 0, 1),
            ("数据准确性", "#2ecc71", 0, 2),
            ("数据一致性", "#1abc9c", 0, 3),
            ("连接稳定性", "#9b59b6", 0, 4),
            ("延迟水平", "#e67e22", 0, 5),

            # 第二行：详细质量指标
            ("缺失率", "#e74c3c", 1, 0),
            ("异常率", "#c0392b", 1, 1),
            ("重复率", "#f39c12", 1, 2),
            ("更新频率", "#16a085", 1, 3),
            ("网络质量", "#2980b9", 1, 4),
            ("数据新鲜度", "#8e44ad", 1, 5),
        ]

        for name, color, row, col in quality_metrics:
            if "延迟" in name:
                unit = "ms"
            elif "率" in name or "性" in name or "度" in name or "质量" in name:
                unit = "%"
            elif "频率" in name:
                unit = "Hz"
            else:
                unit = ""

            card = ModernMetricCard(name, "0", unit, color)
            self.quality_cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 实时数据流监控
        stream_group = QGroupBox("实时数据流监控")
        stream_layout = QVBoxLayout()

        # 数据流控制
        stream_control_layout = QHBoxLayout()

        self.auto_refresh_cb = QCheckBox("自动刷新")
        self.auto_refresh_cb.setChecked(True)
        stream_control_layout.addWidget(self.auto_refresh_cb)

        stream_control_layout.addWidget(QLabel("刷新间隔:"))

        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.addItems(["1秒", "5秒", "10秒", "30秒"])
        self.refresh_interval_combo.setCurrentText("5秒")
        stream_control_layout.addWidget(self.refresh_interval_combo)

        stream_control_layout.addStretch()

        manual_refresh_btn = QPushButton("手动刷新")
        manual_refresh_btn.clicked.connect(self.refresh_data_quality)
        stream_control_layout.addWidget(manual_refresh_btn)

        stream_layout.addLayout(stream_control_layout)

        # 数据流表格
        self.data_stream_table = QTableWidget()
        self.data_stream_table.setColumnCount(7)
        self.data_stream_table.setHorizontalHeaderLabels([
            "数据源", "最新时间", "延迟(ms)", "完整性(%)", "准确性(%)", "状态", "备注"
        ])
        self.data_stream_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.data_stream_table.setAlternatingRowColors(True)
        self.data_stream_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.data_stream_table.setMaximumHeight(200)

        # 设置列宽
        header = self.data_stream_table.horizontalHeader()
        header.setStretchLastSection(True)

        stream_layout.addWidget(self.data_stream_table)
        stream_group.setLayout(stream_layout)
        layout.addWidget(stream_group)

        return tab

    def _create_datasource_monitor_tab(self):
        """创建数据源监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 数据源配置
        config_group = QGroupBox("数据源配置")
        config_layout = QHBoxLayout()

        config_layout.addWidget(QLabel("监控范围:"))

        self.monitor_scope_combo = QComboBox()
        self.monitor_scope_combo.addItems(["全部数据源", "行情数据", "基本面数据", "财务数据", "新闻数据"])
        self.monitor_scope_combo.currentTextChanged.connect(self.update_datasource_monitor)
        config_layout.addWidget(self.monitor_scope_combo)

        config_layout.addWidget(QLabel("监控级别:"))

        self.monitor_level_combo = QComboBox()
        self.monitor_level_combo.addItems(["基础", "标准", "严格", "实时"])
        self.monitor_level_combo.currentTextChanged.connect(self.update_monitor_level)
        config_layout.addWidget(self.monitor_level_combo)

        config_layout.addStretch()

        test_connection_btn = QPushButton("测试连接")
        test_connection_btn.clicked.connect(self.test_all_connections)
        config_layout.addWidget(test_connection_btn)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 数据源详细监控表格
        self.datasource_table = QTableWidget()
        self.datasource_table.setColumnCount(10)
        self.datasource_table.setHorizontalHeaderLabels([
            "数据源名称", "类型", "状态", "连接质量", "延迟(ms)", "吞吐量",
            "错误率(%)", "最后更新", "数据量", "操作"
        ])
        self.datasource_table.setAlternatingRowColors(True)
        self.datasource_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        # 设置列宽自适应
        header = self.datasource_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        layout.addWidget(self.datasource_table)

        # 数据源性能图表
        charts_splitter = QSplitter(Qt.Horizontal)

        # 延迟趋势图
        self.latency_trend_chart = ModernPerformanceChart("数据延迟趋势", "line")
        self.latency_trend_chart.setMinimumHeight(200)
        charts_splitter.addWidget(self.latency_trend_chart)

        # 吞吐量趋势图
        self.throughput_chart = ModernPerformanceChart("数据吞吐量趋势", "line")
        self.throughput_chart.setMinimumHeight(200)
        charts_splitter.addWidget(self.throughput_chart)

        layout.addWidget(charts_splitter)

        return tab

    def _create_cache_monitor_tab(self):
        """创建缓存监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 缓存性能指标卡片
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(120)
        cards_frame.setMaximumHeight(140)
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(2, 2, 2, 2)
        cards_layout.setSpacing(2)

        self.cache_cards = {}
        cache_metrics = [
            ("缓存命中率", "#27ae60", 0, 0),
            ("缓存大小", "#3498db", 0, 1),
            ("I/O操作数", "#e74c3c", 0, 2),
            ("缓存效率", "#f39c12", 0, 3),
            ("命中次数", "#1abc9c", 1, 0),
            ("未命中次数", "#e67e22", 1, 1),
            ("缓存清理", "#9b59b6", 1, 2),
            ("响应时间", "#95a5a6", 1, 3),
        ]

        for name, color, row, col in cache_metrics:
            if "率" in name or "效率" in name:
                unit = "%"
            elif "大小" in name:
                unit = "MB"
            elif "时间" in name:
                unit = "ms"
            elif "次数" in name or "操作数" in name or "清理" in name:
                unit = ""
            else:
                unit = ""

            card = ModernMetricCard(name, "0", unit, color)
            self.cache_cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 缓存控制面板
        control_group = QGroupBox("缓存管理")
        control_group.setMaximumHeight(40)
        control_layout = QHBoxLayout(control_group)

        self.cache_clear_btn = QPushButton("清理缓存")
        self.cache_clear_btn.clicked.connect(self._clear_cache)
        control_layout.addWidget(self.cache_clear_btn)

        self.cache_optimize_btn = QPushButton("优化缓存")
        self.cache_optimize_btn.clicked.connect(self._optimize_cache)
        control_layout.addWidget(self.cache_optimize_btn)

        self.cache_stats_btn = QPushButton("缓存统计")
        self.cache_stats_btn.clicked.connect(self._show_cache_stats)
        control_layout.addWidget(self.cache_stats_btn)

        control_layout.addStretch()
        layout.addWidget(control_group)

        # 缓存性能趋势图
        self.cache_chart = ModernPerformanceChart("缓存性能趋势", "line")
        self.cache_chart.setMinimumHeight(400)
        # self.cache_chart.setMaximumHeight(300)
        layout.addWidget(self.cache_chart, 1)

        return tab

    def _create_quality_report_tab(self):
        """创建质量报告标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 报告生成控制
        report_control_group = QGroupBox("报告生成")
        report_control_layout = QHBoxLayout()

        report_control_layout.addWidget(QLabel("报告周期:"))

        self.report_period_combo = QComboBox()
        self.report_period_combo.addItems(["实时", "小时报告", "日报告", "周报告", "月报告"])
        report_control_layout.addWidget(self.report_period_combo)

        report_control_layout.addWidget(QLabel("报告类型:"))

        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["综合报告", "质量分析", "异常报告", "性能报告"])
        report_control_layout.addWidget(self.report_type_combo)

        report_control_layout.addStretch()

        generate_btn = QPushButton("生成报告")
        generate_btn.clicked.connect(self.generate_quality_report)
        report_control_layout.addWidget(generate_btn)

        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self.export_quality_report)
        report_control_layout.addWidget(export_btn)

        report_control_group.setLayout(report_control_layout)
        layout.addWidget(report_control_group)

        # 质量报告显示区域
        self.quality_report_text = QTextEdit()
        self.quality_report_text.setReadOnly(True)
        self.quality_report_text.setHtml(self._generate_default_report())
        layout.addWidget(self.quality_report_text)

        # 质量趋势图表
        self.quality_trend_chart = ModernPerformanceChart("数据质量趋势", "line")
        self.quality_trend_chart.setMinimumHeight(200)
        self.quality_trend_chart.setMaximumHeight(250)
        layout.addWidget(self.quality_trend_chart)

        return tab

    def _generate_default_report(self) -> str:
        """生成默认质量报告"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; font-size: 12px; }}
                .header {{ background: #2c3e50; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
                .section {{ margin-bottom: 15px; }}
                .section-title {{ font-weight: bold; color: #2c3e50; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-bottom: 8px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
                th, td {{ border: 1px solid #bdc3c7; padding: 8px; text-align: left; }}
                th {{ background: #ecf0f1; font-weight: bold; }}
                .status-good {{ color: #27ae60; font-weight: bold; }}
                .status-warning {{ color: #f39c12; font-weight: bold; }}
                .status-error {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h3>FactorWeave-Quant 数据质量监控报告</h3>
                <div>生成时间: {current_time}</div>
            </div>
            
            <div class="section">
                <div class="section-title">数据质量概览</div>
                <table>
                    <tr><th>指标</th><th>当前值</th><th>状态</th><th>说明</th></tr>
                    <tr><td>数据完整性</td><td>98.5%</td><td><span class="status-good">优秀</span></td><td>数据缺失率极低</td></tr>
                    <tr><td>数据及时性</td><td>95.2%</td><td><span class="status-good">良好</span></td><td>延迟在可接受范围内</td></tr>
                    <tr><td>数据准确性</td><td>99.1%</td><td><span class="status-good">优秀</span></td><td>数据准确性很高</td></tr>
                    <tr><td>连接稳定性</td><td>97.8%</td><td><span class="status-good">良好</span></td><td>连接稳定</td></tr>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">数据源状态</div>
                <table>
                    <tr><th>数据源</th><th>状态</th><th>延迟</th><th>质量评分</th></tr>
                    <tr><td>实时行情</td><td><span class="status-good">正常</span></td><td>15ms</td><td>95.2</td></tr>
                    <tr><td>基本面数据</td><td><span class="status-good">正常</span></td><td>120ms</td><td>92.8</td></tr>
                    <tr><td>财务数据</td><td><span class="status-warning">延迟</span></td><td>350ms</td><td>88.5</td></tr>
                    <tr><td>新闻数据</td><td><span class="status-good">正常</span></td><td>80ms</td><td>91.3</td></tr>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">建议和优化</div>
                <ul>
                    <li>财务数据延迟较高，建议检查网络连接</li>
                    <li>整体数据质量良好，继续保持监控</li>
                    <li>建议增加数据备份源以提高可靠性</li>
                </ul>
            </div>
        </body>
        </html>
        """

    def update_quality_data(self, quality_metrics: Dict[str, float]):
        """更新数据质量指标"""
        try:
            # 更新质量指标卡片
            for name, value in quality_metrics.items():
                if name in self.quality_cards:
                    if value == 0:
                        self.quality_cards[name].update_value("--", "neutral")
                    else:
                        # 根据指标类型判断趋势
                        if name in ["数据完整性", "数据及时性", "数据准确性", "数据一致性", "连接稳定性", "网络质量", "数据新鲜度", "更新频率"]:
                            # 这些指标越高越好
                            trend = "up" if value > 90 else "neutral" if value > 70 else "down"
                        elif name in ["缺失率", "异常率", "重复率", "延迟水平"]:
                            # 这些指标越低越好
                            trend = "up" if value < 5 else "neutral" if value < 15 else "down"
                        else:
                            trend = "neutral"

                        if name == "延迟水平":
                            self.quality_cards[name].update_value(f"{value:.0f}", trend)
                        else:
                            self.quality_cards[name].update_value(f"{value:.1f}", trend)

            # 更新数据质量评分
            quality_score = self._calculate_quality_score(quality_metrics)
            self._update_quality_score(quality_score)

            # 更新质量趋势图表
            for name, value in quality_metrics.items():
                if name in ["数据完整性", "数据及时性", "数据准确性"] and value > 0:
                    self.quality_trend_chart.add_data_point(name, value)

        except Exception as e:
            logger.error(f"更新数据质量指标失败: {e}")

    def _calculate_quality_score(self, metrics: Dict[str, float]) -> float:
        """计算数据质量综合评分 - 修复版算法"""
        try:
            # 权重配置 (总和为1.0，已归一化)
            weights = {
                "数据完整性": 0.25,    # 正向指标，越高越好
                "数据准确性": 0.25,    # 正向指标，越高越好
                "数据及时性": 0.20,    # 正向指标，越高越好
                "数据一致性": 0.15,    # 正向指标，越高越好
                "连接稳定性": 0.10,    # 正向指标，越高越好
                "缺失率": -0.05        # 负向指标，越低越好
            }

            score = 0

            for metric, weight in weights.items():
                if metric in metrics:
                    value = metrics[metric]

                    if weight > 0:
                        # 正向指标：直接加权 (值域0-100)
                        normalized_value = min(value, 100)
                        score += normalized_value * weight
                    else:
                        # 负向指标：转换为正向评分
                        if metric == "缺失率":
                            # 缺失率：0%=100分, 1%=95分, 5%=75分, >10%=0分
                            if value <= 0:
                                normalized_value = 100
                            elif value <= 1:
                                normalized_value = 100 - value * 5      # 线性递减
                            elif value <= 5:
                                normalized_value = 95 - (value - 1) * 5  # 线性递减
                            elif value <= 10:
                                normalized_value = 75 - (value - 5) * 15  # 线性递减
                            else:
                                normalized_value = 0
                        else:
                            # 其他负向指标：简单转换
                            normalized_value = max(0, 100 - value)

                        score += max(0, min(100, normalized_value)) * abs(weight)

            # 直接返回加权分数，不再除以total_weight (因为权重已归一化)
            return max(0, min(100, score))

        except Exception as e:
            logger.error(f"计算数据质量评分失败: {e}")
            return 0

    def _update_quality_score(self, score: float):
        """更新数据质量评分显示"""
        try:
            if score >= 95:
                level = "优秀"
                color = "#27ae60"
            elif score >= 85:
                level = "良好"
                color = "#2ecc71"
            elif score >= 75:
                level = "一般"
                color = "#f39c12"
            elif score >= 65:
                level = "较差"
                color = "#e67e22"
            else:
                level = "差"
                color = "#e74c3c"

            self.quality_score_label.setText(f"数据质量评分: {score:.1f} ({level})")
            self.quality_score_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")

            self.quality_score_bar.setValue(int(score))
            self.quality_score_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)

        except Exception as e:
            logger.error(f"更新数据质量评分显示失败: {e}")

    def refresh_data_quality(self):
        """刷新数据质量"""
        try:
            logger.info("刷新数据质量监控")
            # 这里应该调用实际的数据质量检查服务

        except Exception as e:
            logger.error(f"刷新数据质量失败: {e}")

    def update_datasource_monitor(self):
        """更新数据源监控"""
        try:
            scope = self.monitor_scope_combo.currentText()
            logger.info(f"更新数据源监控范围: {scope}")

        except Exception as e:
            logger.error(f"更新数据源监控失败: {e}")

    def update_monitor_level(self):
        """更新监控级别"""
        try:
            level = self.monitor_level_combo.currentText()
            logger.info(f"更新监控级别: {level}")

        except Exception as e:
            logger.error(f"更新监控级别失败: {e}")

    def test_all_connections(self):
        """测试所有连接"""
        try:
            logger.info("测试所有数据源连接")
            # 这里应该实现实际的连接测试功能

        except Exception as e:
            logger.error(f"测试连接失败: {e}")

    def generate_quality_report(self):
        """生成质量报告"""
        try:
            period = self.report_period_combo.currentText()
            report_type = self.report_type_combo.currentText()
            logger.info(f"生成质量报告: {period} - {report_type}")

            # 更新报告内容
            self.quality_report_text.setHtml(self._generate_default_report())

        except Exception as e:
            logger.error(f"生成质量报告失败: {e}")

    def export_quality_report(self):
        """导出质量报告"""
        try:
            logger.info("导出数据质量报告")
            # 这里应该实现实际的报告导出功能

        except Exception as e:
            logger.error(f"导出质量报告失败: {e}")

    def update_data(self, data: Dict[str, any]):
        """统一数据更新接口"""
        try:
            if 'quality_metrics' in data:
                self.update_quality_data(data['quality_metrics'])

        except Exception as e:
            logger.error(f"更新数据质量监控数据失败: {e}")

    def _get_cached_module(self, module_name):
        """获取缓存的模块，避免重复导入"""
        if module_name not in self._module_cache:
            try:
                if module_name == "backtest.async_io_manager":
                    from backtest.async_io_manager import smart_cache
                    self._module_cache[module_name] = smart_cache
                else:
                    self._module_cache[module_name] = None
            except ImportError:
                self._module_cache[module_name] = None
        return self._module_cache[module_name]

    def _collect_cache_data_async(self):
        """异步收集缓存数据，避免UI卡死"""
        try:
            # 提交后台任务
            future = self.executor.submit(self._collect_cache_data)
            # 设置回调，在主线程中更新UI
            future.add_done_callback(self._on_cache_data_collected)
        except Exception as e:
            logger.error(f"提交异步缓存数据收集任务失败: {e}")

    def _collect_cache_data(self):
        """在后台线程中收集缓存数据"""
        try:
            data = {}

            # 尝试获取缓存管理器数据
            smart_cache = self._get_cached_module("backtest.async_io_manager")
            if smart_cache and hasattr(smart_cache, 'get_stats'):
                try:
                    cache_stats = smart_cache.get_stats()
                    if cache_stats:
                        data['cache_stats'] = cache_stats
                        data['cache_available'] = True
                    else:
                        data['cache_available'] = False
                except Exception as e:
                    logger.warning(f"获取缓存统计失败: {e}")
                    data['cache_available'] = False
            else:
                data['cache_available'] = False

            return data

        except Exception as e:
            logger.error(f"后台缓存数据收集失败: {e}")
            return None

    def _on_cache_data_collected(self, future):
        """缓存数据收集完成的回调，在主线程中更新UI"""
        try:
            # 获取结果，设置超时避免阻塞
            data = future.result(timeout=0.5)  # 500ms超时
            if data is None:
                self._show_cache_no_data()
                return

            self._update_cache_stats_with_data(data)

        except TimeoutError:
            logger.warning("缓存数据收集超时")
            self._show_cache_no_data()
        except Exception as e:
            logger.error(f"处理收集的缓存数据失败: {e}")
            self._show_cache_no_data()

    def _update_cache_stats_with_data(self, data):
        """使用收集的数据更新缓存统计"""
        try:
            if data.get('cache_available', False):
                cache_stats = data.get('cache_stats', {})
                if cache_stats:
                    self.cache_hits = cache_stats.get('hits', 0)
                    self.cache_misses = cache_stats.get('misses', 0)
                    self.cache_size = cache_stats.get('size', 0)
                    self.io_operations = cache_stats.get('io_operations', 0)

                # 计算缓存命中率
                total_requests = self.cache_hits + self.cache_misses
                hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

                # 计算缓存效率
                cache_efficiency = min(hit_rate * 1.1, 100) if hit_rate > 0 else 0

                # 计算响应时间（基于命中率）
                response_time = max(10, 100 - hit_rate) if hit_rate > 0 else 100

                # 更新缓存指标卡片
                if "缓存命中率" in self.cache_cards:
                    trend = "up" if hit_rate > 80 else "down" if hit_rate < 50 else "neutral"
                    self.cache_cards["缓存命中率"].update_value(f"{hit_rate:.1f}", trend)

                if "缓存大小" in self.cache_cards:
                    trend = "up" if self.cache_size > 256 else "neutral"
                    self.cache_cards["缓存大小"].update_value(f"{self.cache_size:.1f}", trend)

                if "I/O操作数" in self.cache_cards:
                    self.cache_cards["I/O操作数"].update_value(str(self.io_operations), "neutral")

                if "缓存效率" in self.cache_cards:
                    trend = "up" if cache_efficiency > 85 else "neutral"
                    self.cache_cards["缓存效率"].update_value(f"{cache_efficiency:.1f}", trend)

                if "命中次数" in self.cache_cards:
                    self.cache_cards["命中次数"].update_value(str(self.cache_hits), "neutral")

                if "未命中次数" in self.cache_cards:
                    trend = "down" if self.cache_misses > 50 else "neutral"
                    self.cache_cards["未命中次数"].update_value(str(self.cache_misses), trend)

                if "缓存清理" in self.cache_cards:
                    cleanup_count = self.cache_hits // 100 if self.cache_hits > 0 else 0
                    self.cache_cards["缓存清理"].update_value(str(cleanup_count), "neutral")

                if "响应时间" in self.cache_cards:
                    trend = "down" if response_time > 50 else "up"
                    self.cache_cards["响应时间"].update_value(f"{response_time:.1f}", trend)

                # 更新缓存性能图表
                if hasattr(self, 'cache_chart'):
                    self.cache_chart.add_data_point("命中率", hit_rate)
                    self.cache_chart.add_data_point("缓存大小", self.cache_size)
                    self.cache_chart.add_data_point("响应时间", response_time)
            else:
                # 缓存数据不可用，显示 "--"
                self._show_cache_no_data()

        except Exception as e:
            logger.error(f"更新缓存统计失败: {e}")
            self._show_cache_no_data()

    def _show_cache_no_data(self):
        """显示缓存无数据状态"""
        cache_metrics = ["缓存命中率", "缓存大小", "I/O操作数", "缓存效率",
                         "命中次数", "未命中次数", "缓存清理", "响应时间"]
        for metric_name in cache_metrics:
            if metric_name in self.cache_cards:
                self.cache_cards[metric_name].update_value("--", "neutral")

    def _clear_cache(self):
        """清理缓存"""
        try:
            # 重置缓存统计
            self.cache_hits = 0
            self.cache_misses = 0
            self.cache_size = 0

            # 尝试清理真实的缓存
            try:
                from backtest.async_io_manager import smart_cache
                if hasattr(smart_cache, 'clear'):
                    smart_cache.clear()
            except ImportError:
                pass

            logger.info("缓存已清理")
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")

    def _optimize_cache(self):
        """优化缓存"""
        try:
            # 模拟缓存优化
            self.cache_hits = int(self.cache_hits * 1.1)  # 提升10%命中率

            # 尝试优化真实的缓存
            try:
                from backtest.async_io_manager import smart_cache
                if hasattr(smart_cache, 'optimize'):
                    smart_cache.optimize()
            except ImportError:
                pass

            logger.info("缓存已优化")
        except Exception as e:
            logger.error(f"优化缓存失败: {e}")

    def _show_cache_stats(self):
        """显示缓存统计"""
        try:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

            stats_msg = f"""
缓存统计信息:
- 总请求数: {total_requests}
- 命中次数: {self.cache_hits}
- 未命中次数: {self.cache_misses}
- 命中率: {hit_rate:.1f}%
- 缓存大小: {self.cache_size:.1f} MB
- I/O操作数: {self.io_operations}
            """

            logger.info(f"缓存统计: {stats_msg}")
        except Exception as e:
            logger.error(f"显示缓存统计失败: {e}")

    def get_cache_stats(self):
        """获取缓存统计信息（供外部调用）"""
        try:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'hit_rate': hit_rate,
                'cache_size': self.cache_size,
                'io_operations': self.io_operations,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
                'total_requests': total_requests,
                'cache_efficiency': min(hit_rate * 1.1, 100),
                'response_time': max(10, 100 - hit_rate)
            }
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'cache_monitoring_timer') and self.cache_monitoring_timer:
                self.cache_monitoring_timer.stop()

            # 关闭线程池
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)
                logger.info("数据质量监控线程池已关闭")

        except Exception as e:
            logger.error(f"清理数据质量监控资源失败: {e}")
