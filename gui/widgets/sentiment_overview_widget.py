#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级情绪概览组件
用于在技术分析界面显示关键情绪指标
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QProgressBar, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
from typing import Dict, Any, Optional
import json


class SentimentIndicatorWidget(QFrame):
    """单个情绪指标显示组件"""

    def __init__(self, name: str, value: float = 0, max_value: float = 100):
        super().__init__()
        self.name = name
        self.value = value
        self.max_value = max_value
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMaximumHeight(60)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # 指标名称
        self.name_label = QLabel(self.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self.name_label.setFont(font)

        # 数值显示
        self.value_label = QLabel(f"{self.value:.1f}")
        self.value_label.setAlignment(Qt.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(11)
        value_font.setBold(True)
        self.value_label.setFont(value_font)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(int(self.max_value))
        self.progress_bar.setValue(int(self.value))
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setTextVisible(False)

        layout.addWidget(self.name_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.update_colors()

    def update_value(self, value: float):
        """更新数值"""
        self.value = value
        self.value_label.setText(f"{value:.1f}")
        self.progress_bar.setValue(int(value))
        self.update_colors()

    def update_colors(self):
        """根据数值更新颜色"""
        if self.value >= 80:
            color = "color: #e74c3c;"  # 红色 - 极端
            progress_color = "QProgressBar::chunk { background-color: #e74c3c; }"
        elif self.value >= 60:
            color = "color: #f39c12;"  # 橙色 - 偏高
            progress_color = "QProgressBar::chunk { background-color: #f39c12; }"
        elif self.value >= 40:
            color = "color: #27ae60;"  # 绿色 - 正常
            progress_color = "QProgressBar::chunk { background-color: #27ae60; }"
        elif self.value >= 20:
            color = "color: #3498db;"  # 蓝色 - 偏低
            progress_color = "QProgressBar::chunk { background-color: #3498db; }"
        else:
            color = "color: #9b59b6;"  # 紫色 - 极端
            progress_color = "QProgressBar::chunk { background-color: #9b59b6; }"

        self.value_label.setStyleSheet(color)
        self.progress_bar.setStyleSheet(progress_color)


class SentimentOverviewWidget(QWidget):
    """轻量级情绪概览组件"""

    # 信号
    sentiment_updated = pyqtSignal(dict)  # 情绪数据更新信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sentiment_indicators = {}
        self.raw_sentiment_data = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel(" 市场情绪概览")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 5px;")

        # 指标网格
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)

        # 创建默认指标
        self.create_default_indicators()

        # 状态标签
        self.status_label = QLabel("等待数据...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")

        layout.addWidget(title_label)
        layout.addLayout(self.grid_layout)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setLayout(layout)
        self.setMaximumWidth(300)

    def create_default_indicators(self):
        """创建默认情绪指标"""
        default_indicators = [
            ("恐贪指数", 50, 100),
            ("新闻情绪", 50, 100),
            ("资金流向", 50, 100),
            ("VIX指数", 20, 50)
        ]

        row = 0
        col = 0
        for name, default_value, max_value in default_indicators:
            indicator = SentimentIndicatorWidget(name, default_value, max_value)
            self.sentiment_indicators[name] = indicator
            self.grid_layout.addWidget(indicator, row, col)

            col += 1
            if col >= 2:  # 每行2个指标
                col = 0
                row += 1

    def update_sentiment_data(self, sentiment_data: Dict[str, Any]):
        """更新情绪数据"""
        try:
            self.raw_sentiment_data = sentiment_data

            # 更新各个指标
            updates = 0

            # 恐贪指数
            if 'fear_greed_index' in sentiment_data:
                value = float(sentiment_data['fear_greed_index'])
                self.sentiment_indicators['恐贪指数'].update_value(value)
                updates += 1

            # 新闻情绪
            if 'news_sentiment' in sentiment_data:
                value = float(sentiment_data['news_sentiment']) * 100  # 转换为0-100
                self.sentiment_indicators['新闻情绪'].update_value(value)
                updates += 1

            # 资金流向
            if 'money_flow' in sentiment_data:
                value = float(sentiment_data['money_flow'])
                # 转换为0-100范围，50为中性
                normalized_value = max(0, min(100, value * 50 + 50))
                self.sentiment_indicators['资金流向'].update_value(normalized_value)
                updates += 1

            # VIX指数
            if 'vix_index' in sentiment_data:
                value = float(sentiment_data['vix_index'])
                self.sentiment_indicators['VIX指数'].update_value(value)
                updates += 1

            # 更新状态
            if updates > 0:
                self.status_label.setText(f"已更新 {updates} 个指标")
                self.status_label.setStyleSheet("color: #27ae60;")
            else:
                self.status_label.setText("无有效数据")
                self.status_label.setStyleSheet("color: #e74c3c;")

            # 发射更新信号
            self.sentiment_updated.emit(self.raw_sentiment_data)

        except Exception as e:
            self.status_label.setText(f"数据更新失败: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c;")

    def get_current_sentiment_summary(self) -> Dict[str, Any]:
        """获取当前情绪摘要"""
        summary = {
            'fear_greed_level': self.sentiment_indicators['恐贪指数'].value,
            'news_sentiment_level': self.sentiment_indicators['新闻情绪'].value,
            'money_flow_level': self.sentiment_indicators['资金流向'].value,
            'vix_level': self.sentiment_indicators['VIX指数'].value,
            'overall_sentiment': 'neutral'
        }

        # 计算整体情绪
        avg_sentiment = (summary['fear_greed_level'] + summary['news_sentiment_level'] +
                         summary['money_flow_level']) / 3

        if avg_sentiment >= 70:
            summary['overall_sentiment'] = 'extremely_bullish'
        elif avg_sentiment >= 55:
            summary['overall_sentiment'] = 'bullish'
        elif avg_sentiment >= 45:
            summary['overall_sentiment'] = 'neutral'
        elif avg_sentiment >= 30:
            summary['overall_sentiment'] = 'bearish'
        else:
            summary['overall_sentiment'] = 'extremely_bearish'

        return summary

    def add_custom_indicator(self, name: str, value: float, max_value: float = 100):
        """添加自定义指标"""
        if name not in self.sentiment_indicators:
            indicator = SentimentIndicatorWidget(name, value, max_value)
            self.sentiment_indicators[name] = indicator

            # 重新排列布局
            self.rearrange_layout()

    def rearrange_layout(self):
        """重新排列布局"""
        # 清除现有布局
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        # 重新添加所有指标
        row = 0
        col = 0
        for indicator in self.sentiment_indicators.values():
            self.grid_layout.addWidget(indicator, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1
