#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI优化标签页
现代化UI优化监控界面
"""

import logging
from typing import Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QGridLayout
from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart

logger = logging.getLogger(__name__)


class ModernUIOptimizationTab(QWidget):
    """现代化UI优化标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # UI性能指标 - 紧凑布局靠上显示
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(100)  # 设置最小高度
        cards_frame.setMaximumHeight(120)  # 限制指标卡片区域高度
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(2, 2, 2, 2)
        cards_layout.setSpacing(2)
        cards_layout.setRowStretch(0, 1)
        cards_layout.setColumnStretch(0, 1)

        self.cards = {}
        ui_metrics = [
            ("渲染帧率", "#27ae60", 0, 0),
            ("响应延迟", "#e74c3c", 0, 1),
            ("缓存命中率", "#3498db", 0, 2),
            ("内存占用", "#f39c12", 0, 3),
            ("加载时间", "#9b59b6", 0, 4),
            ("更新频率", "#1abc9c", 0, 5),
            ("错误率", "#e67e22", 0, 6),
            ("用户满意度", "#2ecc71", 0, 7),
        ]

        for name, color, row, col in ui_metrics:
            unit = "fps" if "帧率" in name else "ms" if "时间" in name or "延迟" in name else "%" if "率" in name or "占用" in name else "Hz" if "频率" in name else ""
            card = ModernMetricCard(name, "0", unit, color)
            self.cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # UI性能趋势图 - 适应性显示区域
        self.ui_chart = ModernPerformanceChart("UI性能趋势", "line")
        self.ui_chart.setMinimumHeight(750)  # 减少最小高度，避免过多空白
        self.ui_chart.setMaximumHeight(900)  # 限制最大高度
        layout.addWidget(self.ui_chart, 1)  # 给图表适当的伸缩权重

    def update_data(self, ui_metrics: Dict[str, float]):
        """更新UI优化数据"""
        try:
            for name, value in ui_metrics.items():
                if name in self.cards:
                    # 根据指标类型判断趋势
                    if name in ["渲染帧率", "缓存命中率", "更新频率", "用户满意度"]:
                        trend = "up" if value > 80 else "neutral" if value > 50 else "down"
                    else:  # 延迟、占用、错误率等，越低越好
                        trend = "down" if value > 80 else "neutral" if value > 50 else "up"

                    self.cards[name].update_value(f"{value:.1f}", trend)

            # 更新图表
            for name, value in ui_metrics.items():
                if name in ["渲染帧率", "响应延迟", "缓存命中率"]:
                    self.ui_chart.add_data_point(name, value)

            self.ui_chart.update_chart()

        except Exception as e:
            logger.error(f"更新UI优化数据失败: {e}")
