"""
现代化系统监控标签页

提供系统资源的实时监控和历史趋势显示
"""

import logging
from typing import Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFrame
from PyQt5.QtCore import Qt

from ..components.metric_card import ModernMetricCard
from ..components.performance_chart import ModernPerformanceChart

logger = logging.getLogger(__name__)


class ModernSystemMonitorTab(QWidget):
    """现代化系统监控标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # 系统资源指标卡片 - 紧凑布局靠上显示
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(100)  # 设置最小高度
        cards_frame.setMaximumHeight(120)  # 限制指标卡片区域高度
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(2)
        cards_layout.setRowStretch(0, 1)
        cards_layout.setColumnStretch(0, 1)

        # 创建12个核心系统指标 - 增加更多必要指标
        self.cards = {}
        system_metrics = [
            ("CPU使用率", "#e74c3c", 0, 0),
            ("内存使用率", "#f39c12", 0, 1),
            ("磁盘使用率", "#9b59b6", 0, 2),
            ("网络吞吐", "#1abc9c", 0, 3),
            ("进程数量", "#3498db", 1, 0),
            ("线程数量", "#2ecc71", 1, 1),
            ("句柄数量", "#e67e22", 1, 2),
            ("响应时间", "#95a5a6", 1, 3),
            ("内存可用", "#16a085", 0, 4),
            ("磁盘可用", "#8e44ad", 0, 5),
            ("网络发送", "#d35400", 1, 4),
            ("网络接收", "#27ae60", 1, 5),
        ]

        for name, color, row, col in system_metrics:
            # 根据指标类型设置单位
            if "率" in name:
                unit = "%"
            elif "时间" in name:
                unit = "ms"
            elif "可用" in name:
                unit = "GB"
            elif "发送" in name or "接收" in name:
                unit = "MB"
            else:
                unit = ""

            card = ModernMetricCard(name, "0", unit, color)
            self.cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 系统资源历史图表 - 适应性显示区域
        self.resource_chart = ModernPerformanceChart("系统资源使用趋势", "line")
        self.resource_chart.setMinimumHeight(250)  # 减少最小高度，避免过多空白
        self.resource_chart.setMaximumHeight(400)  # 限制最大高度
        layout.addWidget(self.resource_chart, 1)  # 给图表适当的伸缩权重

    def update_data(self, system_metrics: Dict[str, float]):
        """更新系统监控数据"""
        try:
            # 检查数据是否有实际变化，避免无意义的更新
            if not system_metrics:
                return

            # 更新指标卡片（只更新有变化的）
            for name, value in system_metrics.items():
                if name in self.cards:
                    # 检查值是否有显著变化（避免微小变化导致的频繁更新）
                    current_text = self.cards[name].value_label.text()
                    new_text = f"{value:.1f}"
                    if current_text != new_text:
                        trend = "up" if value > 70 else "down" if value < 30 else "neutral"
                        if name == "响应时间":
                            trend = "down" if value > 100 else "up" if value < 50 else "neutral"
                        self.cards[name].update_value(new_text, trend)

            # 批量更新图表数据（减少重绘次数）
            chart_metrics = ["CPU使用率", "内存使用率", "磁盘使用率", "网络吞吐", "响应时间"]
            chart_updated = False
            for name, value in system_metrics.items():
                if name in chart_metrics:
                    # 对响应时间进行标准化处理（转换为百分比显示）
                    if name == "响应时间":
                        normalized_value = min(value / 10, 100)  # 将ms转换为百分比显示
                        self.resource_chart.add_data_point(name, normalized_value)
                    else:
                        self.resource_chart.add_data_point(name, value)
                    chart_updated = True

            # 只有数据更新时才重绘图表
            if chart_updated:
                self.resource_chart.update_chart()

        except Exception as e:
            logger.error(f"更新系统监控数据失败: {e}")
