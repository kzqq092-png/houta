#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动调优标签页
现代化自动调优监控界面
"""

import logging
from typing import Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QGridLayout
from gui.widgets.performance.components.metric_card import ModernMetricCard
from gui.widgets.performance.components.performance_chart import ModernPerformanceChart

logger = logging.getLogger(__name__)


class ModernAutoTuningTab(QWidget):
    """现代化自动调优标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # 调优状态指标 - 紧凑布局靠上显示
        cards_frame = QFrame()
        cards_frame.setMinimumHeight(100)  # 设置最小高度
        cards_frame.setMaximumHeight(120)  # 限制指标卡片区域高度
        cards_layout = QGridLayout(cards_frame)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(2)

        self.cards = {}
        tuning_metrics = [
            ("调优进度", "#3498db", 0, 0),
            ("性能提升", "#27ae60", 0, 1),
            ("参数空间", "#f39c12", 0, 2),
            ("收敛速度", "#9b59b6", 0, 3),
            ("最优解质量", "#1abc9c", 0, 4),
            ("迭代次数", "#e67e22", 0, 5),
            ("稳定性", "#2ecc71", 0, 6),
            ("调优效率", "#e74c3c", 0, 7),
        ]

        for name, color, row, col in tuning_metrics:
            unit = "%" if name in ["调优进度", "性能提升", "稳定性", "调优效率"] else "次" if "次数" in name else ""
            card = ModernMetricCard(name, "0", unit, color)
            self.cards[name] = card
            cards_layout.addWidget(card, row, col)

        layout.addWidget(cards_frame)

        # 调优历史图表 - 适应性显示区域
        self.tuning_chart = ModernPerformanceChart("调优历史", "line")
        self.tuning_chart.setMinimumHeight(250)  # 减少最小高度，避免过多空白
        self.tuning_chart.setMaximumHeight(400)  # 限制最大高度
        layout.addWidget(self.tuning_chart, 1)  # 给图表适当的伸缩权重

    def update_data(self, tuning_metrics: Dict[str, float]):
        """更新自动调优数据"""
        try:
            for name, value in tuning_metrics.items():
                if name in self.cards:
                    # 🔧 修复：确保value是数字类型，处理字符串和非数字值
                    try:
                        # 尝试转换为浮点数
                        if isinstance(value, str):
                            # 如果是字符串，尝试转换
                            if value.lower() in ['nan', 'none', '', 'null']:
                                numeric_value = 0.0
                            else:
                                # 🔧 新增：处理包含百分号的字符串
                                clean_value = value.strip()
                                if clean_value.endswith('%'):
                                    # 移除百分号并转换
                                    numeric_value = float(clean_value[:-1])
                                else:
                                    numeric_value = float(clean_value)
                        else:
                            numeric_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        # 如果转换失败，设为0
                        numeric_value = 0.0
                        logger.warning(f"调优指标 '{name}' 的值 '{value}' 无法转换为数字，设为0")

                    # 如果值为0，显示"暂无数据"
                    if numeric_value == 0:
                        self.cards[name].update_value("暂无数据", "neutral")
                    else:
                        # 大部分调优指标，数值越高越好
                        trend = "up" if numeric_value > 70 else "neutral" if numeric_value > 40 else "down"
                        # 对于迭代次数，显示为整数
                        if name == "迭代次数":
                            self.cards[name].update_value(f"{int(numeric_value)}", trend)
                        else:
                            self.cards[name].update_value(f"{numeric_value:.1f}", trend)

            # 更新图表 - 只有非零值才添加到图表
            for name, value in tuning_metrics.items():
                try:
                    # 🔧 修复：同样处理图表数据的类型转换
                    if isinstance(value, str):
                        if value.lower() in ['nan', 'none', '', 'null']:
                            numeric_value = 0.0
                        else:
                            # 🔧 新增：处理包含百分号的字符串
                            clean_value = value.strip()
                            if clean_value.endswith('%'):
                                # 移除百分号并转换
                                numeric_value = float(clean_value[:-1])
                            else:
                                numeric_value = float(clean_value)
                    else:
                        numeric_value = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    numeric_value = 0.0

                if name in ["调优进度", "性能提升", "最优解质量"] and numeric_value > 0:
                    self.tuning_chart.add_data_point(name, numeric_value)

            self.tuning_chart.update_chart()

        except Exception as e:
            logger.error(f"更新自动调优数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
