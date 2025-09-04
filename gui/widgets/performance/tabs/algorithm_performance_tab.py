#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法性能标签页
现代化算法性能监控界面
"""

import logging
from typing import Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QGridLayout
from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart

logger = logging.getLogger(__name__)


class ModernAlgorithmPerformanceTab(QWidget):
    """现代化算法性能标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # 算法性能指标 - 紧凑布局靠上显示
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(100)  # 设置最小高度
        cards_frame.setMaximumHeight(120)  # 限制指标卡片区域高度
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(2)

        self.cards = {}
        algo_metrics = [
            ("执行时间", "#3498db", 0, 0),
            ("计算准确率", "#27ae60", 0, 1),
            ("内存效率", "#f39c12", 0, 2),
            ("并发度", "#9b59b6", 0, 3),
            ("错误率", "#e74c3c", 0, 4),
            ("吞吐量", "#1abc9c", 0, 5),
            ("缓存效率", "#e67e22", 0, 6),
            ("算法复杂度", "#95a5a6", 0, 7),
        ]

        for name, color, row, col in algo_metrics:
            unit = "ms" if "时间" in name else "%" if "率" in name or "效率" in name else "ops/s" if "吞吐量" in name else ""
            card = ModernMetricCard(name, "0", unit, color)
            self.cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 算法性能趋势图 - 适应性显示区域
        self.algo_chart = ModernPerformanceChart("算法性能分析", "line")
        self.algo_chart.setMinimumHeight(250)  # 减少最小高度，避免过多空白
        self.algo_chart.setMaximumHeight(400)  # 限制最大高度
        layout.addWidget(self.algo_chart, 1)  # 给图表适当的伸缩权重

    def update_data(self, algo_metrics: Dict[str, float]):
        """更新算法性能数据"""
        try:
            for name, value in algo_metrics.items():
                if name in self.cards:
                    # 如果值为0，显示"暂无数据"
                    if value == 0:
                        self.cards[name].update_value("暂无数据", "neutral")
                    else:
                        # 根据指标类型判断趋势
                        if name in ["计算准确率", "内存效率", "并发度", "吞吐量", "缓存效率"]:
                            trend = "up" if value > 80 else "neutral" if value > 50 else "down"
                        else:  # 执行时间、错误率等，越低越好
                            trend = "down" if value > 80 else "neutral" if value > 50 else "up"

                        self.cards[name].update_value(f"{value:.1f}", trend)

            # 更新图表 - 只有非零值才添加到图表
            for name, value in algo_metrics.items():
                if name in ["执行时间", "计算准确率", "吞吐量"] and value > 0:
                    self.algo_chart.add_data_point(name, value)

            self.algo_chart.update_chart()

        except Exception as e:
            logger.error(f"更新算法性能数据失败: {e}")
