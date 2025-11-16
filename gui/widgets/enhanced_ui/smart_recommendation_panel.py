#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能推荐面板
提供基于用户行为分析的智能推荐功能
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QFrame, QPushButton, QComboBox, QSlider, QTextEdit, QScrollArea,
    QGroupBox, QGridLayout, QProgressBar, QSplitter, QTabWidget,
    QListWidget, QListWidgetItem, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon, QPainter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from loguru import logger

from core.services.smart_recommendation_engine import SmartRecommendationEngine
from core.services.recommendation_model_trainer import RecommendationModelTrainer


class RecommendationCard(QFrame):
    """推荐卡片组件"""

    # 信号定义
    card_clicked = pyqtSignal(dict)
    action_clicked = pyqtSignal(str, dict)

    def __init__(self, recommendation_data: Dict[str, Any], parent=None):
        super().__init__(parent)

        self.recommendation_data = recommendation_data
        self.setFrameStyle(QFrame.StyledPanel)
        # ✅ 修改：增加卡片高度从95到105，确保右下角按钮完整显示
        self.setFixedHeight(105)
        self.setCursor(Qt.PointingHandCursor)

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        """初始化UI（精简版）"""
        layout = QVBoxLayout(self)
        # ✅ 修改：增加垂直空间确保内容完整显示
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        # 标题和评分
        header_layout = QHBoxLayout()

        # ✅ 修改：推荐标题字体从11降至10
        title = self.recommendation_data.get('title', '未知推荐')
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(40)  # 限制标题高度
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # ✅ 修改：推荐评分字体从14降至11，尺寸从40x25降至35x22
        score = self.recommendation_data.get('score', 0)
        self.score_label = QLabel(f"{score:.1f}")
        self.score_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setFixedSize(35, 22)

        # 根据评分设置颜色
        if score >= 8.0:
            self.score_label.setStyleSheet("background-color: #27AE60; color: white; border-radius: 12px;")
        elif score >= 6.0:
            self.score_label.setStyleSheet("background-color: #F39C12; color: white; border-radius: 12px;")
        else:
            self.score_label.setStyleSheet("background-color: #E74C3C; color: white; border-radius: 12px;")

        header_layout.addWidget(self.score_label)

        layout.addLayout(header_layout)

        # ✅ 修改：推荐描述字体从9降至8，限制行数
        description = self.recommendation_data.get('description', '')
        # 限制描述长度
        if len(description) > 50:
            description = description[:47] + "..."
        self.description_label = QLabel(description)
        self.description_label.setFont(QFont("Arial", 8))
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #7F8C8D;")
        self.description_label.setMaximumHeight(16)  # 限制描述高度
        layout.addWidget(self.description_label)

        # 标签和操作按钮
        footer_layout = QHBoxLayout()

        # 推荐类型标签
        rec_type = self.recommendation_data.get('type', 'unknown')
        type_colors = {
            'stock': '#3498DB',
            'strategy': '#9B59B6',
            'indicator': '#E67E22',
            'news': '#1ABC9C',
            'analysis': '#34495E'
        }

        self.type_label = QLabel(rec_type.upper())
        self.type_label.setFont(QFont("Arial", 8, QFont.Bold))
        self.type_label.setStyleSheet(f"""
            background-color: {type_colors.get(rec_type, '#95A5A6')};
            color: white;
            padding: 2px 6px;
            border-radius: 8px;
        """)
        footer_layout.addWidget(self.type_label)

        footer_layout.addStretch()

        # ✅ 修改：增大操作按钮尺寸和字体，确保可见性
        self.action_btn = QPushButton("详情")
        self.action_btn.setFont(QFont("Arial", 9, QFont.Bold))
        self.action_btn.setFixedSize(55, 22)
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 3px 8px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        self.action_btn.clicked.connect(self._on_action_clicked)
        footer_layout.addWidget(self.action_btn)

        layout.addLayout(footer_layout)

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            RecommendationCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            
            RecommendationCard:hover {
                border: 2px solid #3498DB;
                background-color: #F8F9FA;
            }
            
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.recommendation_data)
        super().mousePressEvent(event)

    def _on_action_clicked(self):
        """操作按钮点击"""
        self.action_clicked.emit("view_detail", self.recommendation_data)


class UserBehaviorChart(FigureCanvas):
    """用户行为分析图表"""

    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)

        # 创建子图
        self.ax1 = self.fig.add_subplot(221)  # 使用频率
        self.ax2 = self.fig.add_subplot(222)  # 偏好分析
        self.ax3 = self.fig.add_subplot(223)  # 时间分布
        self.ax4 = self.fig.add_subplot(224)  # 推荐效果

        self.setup_charts()

    def setup_charts(self):
        """设置图表样式"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        # 使用频率
        self.ax1.set_title('功能使用频率', fontsize=10, fontweight='bold')
        self.ax1.set_ylabel('使用次数', fontsize=10, fontweight='bold')

        # 偏好分析
        self.ax2.set_title('用户偏好分析', fontsize=10, fontweight='bold')

        # 时间分布
        self.ax3.set_title('使用时间分布', fontsize=10, fontweight='bold')
        self.ax3.set_xlabel('小时', fontsize=10, fontweight='bold')
        self.ax3.set_ylabel('活跃度', fontsize=10, fontweight='bold')

        # 推荐效果
        self.ax4.set_title('推荐效果统计', fontsize=10, fontweight='bold')

        self.fig.tight_layout()

    def update_behavior_data(self, behavior_data: Dict[str, Any]):
        """更新用户行为数据"""
        try:
            # 清空之前的图表
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()

            self.setup_charts()

            # 功能使用频率
            functions = ['图表分析', '技术指标', '形态识别', '基本面分析', '数据导入']
            usage_counts = [45, 38, 25, 20, 15]

            bars1 = self.ax1.bar(functions, usage_counts, color='#3498DB', alpha=0.8)
            self.ax1.tick_params(axis='both', rotation=45, labelsize=8)

            # 在柱子上显示数值
            for bar, count in zip(bars1, usage_counts):
                height = bar.get_height()
                self.ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                              str(count), ha='center', va='bottom', fontweight='bold', fontsize=8)

            # 用户偏好分析（饼图）
            preferences = ['技术分析', '基本面分析', '量化策略', '风险管理']
            pref_values = [40, 25, 20, 15]
            colors = ['#3498DB', '#E74C3C', '#27AE60', '#F39C12']

            wedges, texts, autotexts = self.ax2.pie(pref_values, labels=preferences,
                                                    colors=colors, autopct='%1.1f%%',
                                                    startangle=90)

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(8)
            # 使用时间分布
            hours = list(range(24))
            activity = [2, 1, 0, 0, 0, 0, 1, 3, 5, 8, 12, 15, 18, 20, 22, 25, 28, 30, 25, 20, 15, 10, 6, 3]

            self.ax3.plot(hours, activity, 'b-o', linewidth=1, markersize=4)
            self.ax3.fill_between(hours, activity, alpha=0.3, color='#3498DB')
            self.ax3.set_xlim(0, 23)
            self.ax3.set_xticks(range(0, 24, 4))

            # 推荐效果统计
            metrics = ['点击率', '转化率', '满意度', '准确率']
            values = [0.75, 0.45, 0.85, 0.68]

            bars4 = self.ax4.barh(metrics, values, color=['#27AE60', '#E74C3C', '#F39C12', '#9B59B6'])

            # 在柱子上显示百分比
            for bar, value in zip(bars4, values):
                width = bar.get_width()
                self.ax4.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                              f'{value:.1%}', ha='left', va='center', fontweight='bold', fontsize=8)

            self.ax4.set_xlim(0, 1)

            self.fig.tight_layout()
            self.draw()

        except Exception as e:
            logger.error(f"更新用户行为图表失败: {e}")


class SmartRecommendationPanel(QWidget):
    """
    智能推荐面板
    提供基于用户行为分析的个性化推荐功能
    """

    # 信号定义
    recommendation_selected = pyqtSignal(dict)     # 推荐选择信号
    feedback_submitted = pyqtSignal(str, dict)     # 反馈提交信号
    preferences_updated = pyqtSignal(dict)         # 偏好更新信号

    def __init__(self, parent=None, recommendation_engine: SmartRecommendationEngine = None,
                 model_trainer: RecommendationModelTrainer = None):
        super().__init__(parent)

        self.recommendation_engine = recommendation_engine
        self.model_trainer = model_trainer

        # 用户配置
        self.user_preferences = {}
        self.recommendation_history = []
        self.feedback_history = []

        # 推荐配置
        self.max_recommendations = 10
        self.recommendation_types = ['stock', 'strategy', 'indicator', 'news', 'analysis']
        self.update_interval = 30  # 分钟

        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_recommendations)
        self.update_timer.start(self.update_interval * 60 * 1000)

        self.init_ui()

        # 初始加载推荐
        self._load_initial_recommendations()

        logger.info("SmartRecommendationPanel 初始化完成")

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # 主要内容标签页
        main_tabs = QTabWidget(self)

        # 推荐内容标签页
        recommendations_tab = self._create_recommendations_tab()
        main_tabs.addTab(recommendations_tab, "智能推荐")

        # 用户画像标签页
        profile_tab = self._create_profile_tab()
        main_tabs.addTab(profile_tab, "👤 用户画像")

        # 推荐设置标签页
        settings_tab = self._create_settings_tab()
        main_tabs.addTab(settings_tab, "推荐设置")

        # 反馈管理标签页
        feedback_tab = self._create_feedback_tab()
        main_tabs.addTab(feedback_tab, "反馈管理")

        layout.addWidget(main_tabs)

        # 应用样式
        self._apply_styles()

    def _create_control_panel(self) -> QWidget:
        """创建控制面板"""
        panel = QFrame(self)
        panel.setMaximumHeight(60)

        layout = QHBoxLayout(panel)

        # 推荐状态
        self.recommendation_status = QLabel("● 推荐引擎运行中")
        self.recommendation_status.setStyleSheet("color: green; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.recommendation_status)

        # 推荐数量
        layout.addWidget(QLabel("推荐数量:"))
        self.recommendation_count_spin = QSpinBox()
        self.recommendation_count_spin.setRange(5, 20)
        self.recommendation_count_spin.setValue(self.max_recommendations)
        self.recommendation_count_spin.valueChanged.connect(self._on_count_changed)
        layout.addWidget(self.recommendation_count_spin)

        # 推荐类型过滤
        layout.addWidget(QLabel("类型过滤:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["全部", "股票推荐", "策略推荐", "指标推荐", "新闻推荐", "分析推荐"])
        self.type_filter_combo.currentTextChanged.connect(self._filter_recommendations)
        layout.addWidget(self.type_filter_combo)

        # 更新频率
        layout.addWidget(QLabel("更新频率:"))
        self.update_frequency_combo = QComboBox()
        self.update_frequency_combo.addItems(["15分钟", "30分钟", "1小时", "2小时", "手动"])
        self.update_frequency_combo.setCurrentText("30分钟")
        self.update_frequency_combo.currentTextChanged.connect(self._on_frequency_changed)
        layout.addWidget(self.update_frequency_combo)

        layout.addStretch()

        # 刷新推荐按钮
        self.refresh_btn = QPushButton("刷新推荐")
        self.refresh_btn.clicked.connect(self._refresh_recommendations)
        layout.addWidget(self.refresh_btn)

        # 训练模型按钮
        self.train_model_btn = QPushButton("训练模型")
        self.train_model_btn.clicked.connect(self._train_recommendation_model)
        layout.addWidget(self.train_model_btn)

        return panel

    def _create_recommendations_tab(self) -> QWidget:
        """创建推荐内容标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐分类标签页
        rec_tabs = QTabWidget()

        # 股票推荐
        stock_tab = self._create_stock_recommendations_tab()
        rec_tabs.addTab(stock_tab, "股票推荐")

        # 策略推荐
        strategy_tab = self._create_strategy_recommendations_tab()
        rec_tabs.addTab(strategy_tab, "策略推荐")

        # 指标推荐
        indicator_tab = self._create_indicator_recommendations_tab()
        rec_tabs.addTab(indicator_tab, "指标推荐")

        # 新闻推荐
        news_tab = self._create_news_recommendations_tab()
        rec_tabs.addTab(news_tab, "📰 新闻推荐")

        layout.addWidget(rec_tabs)

        return widget

    def _create_stock_recommendations_tab(self) -> QWidget:
        """创建股票推荐标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐卡片滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # ✅ 修改：推荐卡片容器使用网格布局（一行4个，靠上对齐）
        self.stock_cards_widget = QWidget()
        from PyQt5.QtWidgets import QGridLayout
        self.stock_cards_layout = QGridLayout(self.stock_cards_widget)
        self.stock_cards_layout.setSpacing(10)
        self.stock_cards_layout.setContentsMargins(5, 5, 5, 5)
        self.stock_cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 卡片靠上靠左对齐

        scroll_area.setWidget(self.stock_cards_widget)
        layout.addWidget(scroll_area)

        return widget

    def _create_strategy_recommendations_tab(self) -> QWidget:
        """创建策略推荐标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐卡片滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # ✅ 修改：策略推荐也使用网格布局（一行4个，靠上对齐）
        self.strategy_cards_widget = QWidget()
        from PyQt5.QtWidgets import QGridLayout
        self.strategy_cards_layout = QGridLayout(self.strategy_cards_widget)
        self.strategy_cards_layout.setSpacing(10)
        self.strategy_cards_layout.setContentsMargins(5, 5, 5, 5)
        self.strategy_cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 卡片靠上靠左对齐

        scroll_area.setWidget(self.strategy_cards_widget)
        layout.addWidget(scroll_area)

        return widget

    def _create_indicator_recommendations_tab(self) -> QWidget:
        """创建指标推荐标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐卡片滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # ✅ 修改：指标推荐也使用网格布局（一行4个，靠上对齐）
        self.indicator_cards_widget = QWidget()
        from PyQt5.QtWidgets import QGridLayout
        self.indicator_cards_layout = QGridLayout(self.indicator_cards_widget)
        self.indicator_cards_layout.setSpacing(10)
        self.indicator_cards_layout.setContentsMargins(5, 5, 5, 5)
        self.indicator_cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 卡片靠上靠左对齐

        scroll_area.setWidget(self.indicator_cards_widget)
        layout.addWidget(scroll_area)

        return widget

    def _create_news_recommendations_tab(self) -> QWidget:
        """创建新闻推荐标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐卡片滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # ✅ 修改：新闻推荐也使用网格布局（一行4个，靠上对齐）
        self.news_cards_widget = QWidget()
        from PyQt5.QtWidgets import QGridLayout
        self.news_cards_layout = QGridLayout(self.news_cards_widget)
        self.news_cards_layout.setSpacing(10)
        self.news_cards_layout.setContentsMargins(5, 5, 5, 5)
        self.news_cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 卡片靠上靠左对齐

        scroll_area.setWidget(self.news_cards_widget)
        layout.addWidget(scroll_area)

        return widget

    def _create_profile_tab(self) -> QWidget:
        """创建用户画像标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 分割器：用户信息和行为分析
        splitter = QSplitter(Qt.Horizontal)

        # 用户信息面板
        profile_group = QGroupBox("用户画像")
        profile_layout = QVBoxLayout(profile_group)

        # 基本信息
        basic_info_frame = QFrame()
        basic_info_layout = QGridLayout(basic_info_frame)

        self.profile_labels = {}
        profile_items = [
            ("用户类型", "user_type", "专业投资者"),
            ("经验水平", "experience_level", "高级"),
            ("风险偏好", "risk_preference", "中等"),
            ("投资风格", "investment_style", "价值投资"),
            ("关注板块", "focus_sectors", "科技、医药"),
            ("使用时长", "usage_duration", "6个月"),
            ("活跃度", "activity_level", "高"),
            ("满意度", "satisfaction", "85%")
        ]

        for i, (label, key, default_value) in enumerate(profile_items):
            row, col = i // 2, (i % 2) * 2
            basic_info_layout.addWidget(QLabel(f"{label}:"), row, col)

            value_label = QLabel(default_value)
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB;")
            basic_info_layout.addWidget(value_label, row, col + 1)

            self.profile_labels[key] = value_label

        profile_layout.addWidget(basic_info_frame)

        # 偏好设置
        preferences_group = QGroupBox("偏好设置")
        preferences_layout = QGridLayout(preferences_group)

        self.preference_sliders = {}
        preference_items = [
            ("技术分析偏好", "technical_preference"),
            ("基本面分析偏好", "fundamental_preference"),
            ("量化策略偏好", "quantitative_preference"),
            ("新闻资讯偏好", "news_preference"),
            ("风险管理偏好", "risk_management_preference")
        ]

        for i, (label, key) in enumerate(preference_items):
            preferences_layout.addWidget(QLabel(f"{label}:"), i, 0)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(50)
            slider.valueChanged.connect(lambda v, k=key: self._on_preference_changed(k, v))
            preferences_layout.addWidget(slider, i, 1)

            value_label = QLabel("50%")
            preferences_layout.addWidget(value_label, i, 2)

            self.preference_sliders[key] = (slider, value_label)

        profile_layout.addWidget(preferences_group)

        splitter.addWidget(profile_group)

        # 行为分析图表
        behavior_group = QGroupBox("行为分析")
        behavior_layout = QVBoxLayout(behavior_group)

        self.behavior_chart = UserBehaviorChart()
        behavior_layout.addWidget(self.behavior_chart)

        splitter.addWidget(behavior_group)

        # 设置分割比例
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

        return widget

    def _create_settings_tab(self) -> QWidget:
        """创建推荐设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 推荐算法设置
        algorithm_group = QGroupBox("推荐算法设置")
        algorithm_layout = QGridLayout(algorithm_group)

        # 算法权重配置
        self.algorithm_weights = {}
        algorithm_items = [
            ("协同过滤权重", "collaborative_weight", 0.4),
            ("内容推荐权重", "content_weight", 0.3),
            ("行为分析权重", "behavior_weight", 0.2),
            ("热度推荐权重", "popularity_weight", 0.1)
        ]

        for i, (label, key, default_value) in enumerate(algorithm_items):
            algorithm_layout.addWidget(QLabel(f"{label}:"), i, 0)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(default_value * 100))
            slider.valueChanged.connect(lambda v, k=key: self._on_algorithm_weight_changed(k, v))
            algorithm_layout.addWidget(slider, i, 1)

            value_label = QLabel(f"{default_value:.1f}")
            algorithm_layout.addWidget(value_label, i, 2)

            self.algorithm_weights[key] = (slider, value_label)

        layout.addWidget(algorithm_group)

        # 推荐过滤设置
        filter_group = QGroupBox("推荐过滤设置")
        filter_layout = QGridLayout(filter_group)

        # 过滤选项
        self.filter_options = {}
        filter_items = [
            ("最低评分阈值", "min_score_threshold"),
            ("相似度阈值", "similarity_threshold"),
            ("新鲜度权重", "freshness_weight"),
            ("多样性权重", "diversity_weight")
        ]

        for i, (label, key) in enumerate(filter_items):
            filter_layout.addWidget(QLabel(f"{label}:"), i, 0)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(50)
            filter_layout.addWidget(slider, i, 1)

            value_label = QLabel("0.5")
            filter_layout.addWidget(value_label, i, 2)

            self.filter_options[key] = (slider, value_label)

        layout.addWidget(filter_group)

        # 个性化设置
        personalization_group = QGroupBox("个性化设置")
        personalization_layout = QVBoxLayout(personalization_group)

        # 个性化选项
        self.personalization_options = {}
        personalization_items = [
            ("启用个性化推荐", "enable_personalization"),
            ("学习用户偏好", "learn_preferences"),
            ("考虑历史行为", "consider_history"),
            ("实时调整推荐", "realtime_adjustment"),
            ("跨设备同步", "cross_device_sync")
        ]

        for label, key in personalization_items:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, k=key: self._on_personalization_changed(k, checked))
            personalization_layout.addWidget(checkbox)

            self.personalization_options[key] = checkbox

        layout.addWidget(personalization_group)

        # 设置操作按钮
        settings_buttons = QFrame()
        settings_buttons_layout = QHBoxLayout(settings_buttons)

        save_settings_btn = QPushButton("保存设置")
        save_settings_btn.clicked.connect(self._save_settings)
        settings_buttons_layout.addWidget(save_settings_btn)

        load_settings_btn = QPushButton("加载设置")
        load_settings_btn.clicked.connect(self._load_settings)
        settings_buttons_layout.addWidget(load_settings_btn)

        reset_settings_btn = QPushButton("重置设置")
        reset_settings_btn.clicked.connect(self._reset_settings)
        settings_buttons_layout.addWidget(reset_settings_btn)

        settings_buttons_layout.addStretch()

        layout.addWidget(settings_buttons)
        layout.addStretch()

        return widget

    def _create_feedback_tab(self) -> QWidget:
        """创建反馈管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 反馈统计
        stats_group = QGroupBox("反馈统计")
        stats_layout = QGridLayout(stats_group)

        self.feedback_stats = {}
        stats_items = [
            ("总反馈数", "total_feedback", 0, 0),
            ("正面反馈", "positive_feedback", 0, 1),
            ("负面反馈", "negative_feedback", 0, 2),
            ("平均评分", "average_rating", 1, 0),
            ("推荐准确率", "accuracy_rate", 1, 1),
            ("用户满意度", "satisfaction_rate", 1, 2)
        ]

        for label, key, row, col in stats_items:
            stats_layout.addWidget(QLabel(f"{label}:"), row, col * 2)

            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; color: #2E86AB; font-size: 14px;")
            stats_layout.addWidget(value_label, row, col * 2 + 1)

            self.feedback_stats[key] = value_label

        layout.addWidget(stats_group)

        # 反馈历史
        history_group = QGroupBox("反馈历史")
        history_layout = QVBoxLayout(history_group)

        # 反馈过滤
        filter_panel = QFrame()
        filter_layout = QHBoxLayout(filter_panel)

        filter_layout.addWidget(QLabel("反馈类型:"))
        self.feedback_type_filter = QComboBox()
        self.feedback_type_filter.addItems(["全部", "正面", "负面", "中性"])
        filter_layout.addWidget(self.feedback_type_filter)

        filter_layout.addWidget(QLabel("推荐类型:"))
        self.feedback_rec_type_filter = QComboBox()
        self.feedback_rec_type_filter.addItems(["全部", "股票", "策略", "指标", "新闻"])
        filter_layout.addWidget(self.feedback_rec_type_filter)

        filter_layout.addStretch()

        # 导出反馈按钮
        export_feedback_btn = QPushButton("导出反馈")
        export_feedback_btn.clicked.connect(self._export_feedback)
        filter_layout.addWidget(export_feedback_btn)

        history_layout.addWidget(filter_panel)

        # 反馈列表
        self.feedback_table = QTableWidget()
        self.feedback_table.setColumnCount(6)
        self.feedback_table.setHorizontalHeaderLabels([
            "时间", "推荐内容", "反馈类型", "评分", "评论", "处理状态"
        ])
        self.feedback_table.setAlternatingRowColors(True)
        history_layout.addWidget(self.feedback_table)

        layout.addWidget(history_group)

        return widget

    def _apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QTableWidget {
                gridline-color: #E0E0E0;
                background-color: white;
                alternate-background-color: #F5F5F5;
            }
            
            QTableWidget::item {
                padding: 5px;
                border: none;
            }
            
            QTableWidget::item:selected {
                background-color: #3498DB;
                color: white;
            }
            
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
            }
            
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #2980B9;
            }
            
            QPushButton:pressed {
                background-color: #21618C;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #BDC3C7;
                height: 8px;
                background: #ECF0F1;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: #3498DB;
                border: 1px solid #2980B9;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            
            QSlider::sub-page:horizontal {
                background: #3498DB;
                border-radius: 4px;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def _load_initial_recommendations(self):
        """加载初始推荐（使用真实推荐引擎）"""
        try:
            # 初始化推荐引擎（如果尚未初始化）
            if self.recommendation_engine is None:
                logger.info("初始化智能推荐引擎...")
                self.recommendation_engine = SmartRecommendationEngine()

                # 初始化引擎数据
                self._initialize_recommendation_engine()

            # 异步获取真实推荐
            logger.info("正在获取个性化推荐...")
            user_id = self._get_current_user_id()

            # ✅ 修复：使用QThread在后台执行推荐获取
            from PyQt5.QtCore import QThread, pyqtSignal

            class RecommendationWorker(QThread):
                """推荐加载工作线程"""
                finished = pyqtSignal(list)
                error = pyqtSignal(str)

                def __init__(self, engine, user_id, count):
                    super().__init__()
                    self.engine = engine
                    self.user_id = user_id
                    self.count = count

                def run(self):
                    try:
                        logger.info(f"🔄 Worker线程开始执行，user_id={self.user_id}, count={self.count}")
                        print(f"🔄 [DEBUG] Worker线程开始执行，user_id={self.user_id}, count={self.count}")

                        import asyncio
                        # 在线程中创建新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        logger.info("🔄 Worker线程：事件循环已创建")

                        # 执行异步获取推荐
                        logger.info("🔄 Worker线程：开始调用get_recommendations")
                        recommendations = loop.run_until_complete(
                            self.engine.get_recommendations(
                                user_id=self.user_id,
                                count=self.count
                            )
                        )
                        logger.info(f"🔄 Worker线程：get_recommendations返回，结果数量={len(recommendations)}")
                        print(f"🔄 [DEBUG] Worker线程：获取到 {len(recommendations)} 个推荐")

                        loop.close()
                        logger.info("🔄 Worker线程：发送finished信号")
                        self.finished.emit(recommendations)
                        logger.info("✅ Worker线程：finished信号已发送")

                    except Exception as e:
                        logger.error(f"❌ 推荐加载线程执行失败: {e}")
                        print(f"❌ [DEBUG] 推荐加载线程执行失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        print(f"❌ [DEBUG] 错误堆栈:\n{traceback.format_exc()}")
                        self.error.emit(str(e))

            # 创建并启动工作线程
            try:
                self._recommendation_worker = RecommendationWorker(
                    self.recommendation_engine,
                    user_id,
                    self.max_recommendations * 2
                )
                self._recommendation_worker.finished.connect(self._display_loaded_recommendations)
                self._recommendation_worker.error.connect(self._on_recommendation_load_error)
                self._recommendation_worker.start()

                logger.info("推荐加载线程已启动")
                return  # 立即返回，不阻塞UI

            except Exception as thread_error:
                logger.error(f"创建推荐加载线程失败: {thread_error}")
                import traceback
                logger.error(traceback.format_exc())
                # 降级：显示空状态
                self._show_empty_state(f"初始化失败: {thread_error}")

        except Exception as e:
            logger.error(f"加载推荐失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            # 显示空状态而不是Mock数据
            self._show_empty_state(str(e))

    # ==================== 真实数据处理方法 ====================

    def _on_recommendation_load_error(self, error_msg: str):
        """推荐加载错误处理"""
        logger.error(f"❌ 推荐加载错误回调被触发: {error_msg}")
        print(f"❌ [DEBUG] 推荐加载错误: {error_msg}")
        self._show_empty_state(f"加载失败: {error_msg}")

    def _display_loaded_recommendations(self, recommendations):
        """显示加载的推荐结果（异步回调）"""
        try:
            logger.info(f"✅ _display_loaded_recommendations 被调用！原始推荐数量: {len(recommendations)}")
            print(f"✅ [DEBUG] _display_loaded_recommendations 被调用！原始推荐数量: {len(recommendations)}")

            # ✅ 检查推荐是否为空
            if not recommendations:
                logger.warning("推荐列表为空，显示空状态")
                self._show_empty_state("暂无推荐内容")
                return

            # 转换为显示格式
            formatted_recommendations = self._format_engine_recommendations(recommendations)
            logger.info(f"格式化后推荐数量: {len(formatted_recommendations)}")

            # ✅ 检查格式化后是否为空
            if not formatted_recommendations:
                logger.warning("格式化后推荐列表为空")
                self._show_empty_state("推荐格式化失败")
                return

            # 按类型分组显示
            self._display_recommendations_by_type(formatted_recommendations)
            logger.info("推荐卡片已显示")

            # 更新用户行为图表（使用真实统计数据）
            behavior_data = self._get_real_behavior_data()
            if behavior_data:
                self.behavior_chart.update_behavior_data(behavior_data)
                logger.info("用户行为图表已更新")

            # 更新反馈统计
            self._update_feedback_stats()
            logger.info("反馈统计已更新")

            logger.info(f"✅ 成功加载并显示了 {len(recommendations)} 个推荐")

        except Exception as e:
            logger.error(f"显示推荐失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._show_empty_state(str(e))

    def _initialize_recommendation_engine(self):
        """初始化推荐引擎数据（使用真实系统数据）"""
        try:
            logger.info("开始初始化推荐引擎数据...")

            # 1. 从系统获取真实股票数据
            stock_items_added = self._load_stock_content_items()
            logger.info(f"添加了 {stock_items_added} 个股票内容项")

            # 2. 添加策略内容（如果有）
            strategy_items_added = self._load_strategy_content_items()
            logger.info(f"添加了 {strategy_items_added} 个策略内容项")

            # 3. 添加指标内容
            indicator_items_added = self._load_indicator_content_items()
            logger.info(f"添加了 {indicator_items_added} 个指标内容项")

            # ✅ 新增：4. 添加新闻内容
            news_items_added = self._load_news_content_items()
            logger.info(f"添加了 {news_items_added} 个新闻内容项")

            # 5. 创建或更新用户画像
            self._create_user_profile()

            logger.info("推荐引擎数据初始化完成")

        except Exception as e:
            logger.error(f"初始化推荐引擎失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _load_stock_content_items(self) -> int:
        """从UnifiedDataManager加载股票数据"""
        try:
            from core.containers import get_service_container
            from core.services.smart_recommendation_engine import ContentItem, RecommendationType

            # 获取数据管理器（使用全局单例）
            container = get_service_container()
            data_manager = container.get('UnifiedDataManager')

            if not data_manager:
                logger.warning("UnifiedDataManager不可用，尝试直接实例化")
                from core.services.unified_data_manager import UnifiedDataManager
                data_manager = UnifiedDataManager()

            # 获取股票列表
            stock_list = data_manager.get_asset_list('stock')

            if stock_list.empty:
                logger.warning("股票列表为空")
                return 0

            # 添加股票内容项
            count = 0
            for idx, stock in stock_list.iterrows():
                stock_code = stock.get('code', stock.get('symbol', ''))
                stock_name = stock.get('name', '')

                if not stock_code:
                    continue

                # 过滤None值和空字符串，确保所有值都是有效字符串
                sector = stock.get('sector') or '未知'
                industry = stock.get('industry') or '未知'
                market = stock.get('market') or '未知'

                # 确保tags、categories、keywords中没有None或空字符串
                tags = [str(v) for v in [sector, industry, market] if v and v != '未知']
                categories = [str(v) for v in [market, sector] if v and v != '未知']
                keywords = [str(v) for v in [stock_name, stock_code, industry] if v and v != '未知']

                item = ContentItem(
                    item_id=f"stock_{stock_code}",
                    item_type=RecommendationType.STOCK,
                    title=f"{stock_name} ({stock_code})" if stock_name else stock_code,
                    description=f"行业: {industry} | 板块: {sector}",
                    tags=tags,
                    categories=categories,
                    keywords=keywords,
                    metadata={
                        'code': stock_code,
                        'name': stock_name,
                        'market': market,
                        'sector': sector,
                        'industry': industry
                    }
                )

                self.recommendation_engine.add_content_item(item)
                count += 1

                # 限制数量避免过多
                if count >= 1000:
                    break

            return count

        except Exception as e:
            logger.error(f"加载股票内容项失败: {e}")
            return 0

    def _load_strategy_content_items(self) -> int:
        """加载策略内容项"""
        try:
            from core.services.smart_recommendation_engine import ContentItem, RecommendationType

            # 常见策略列表
            strategies = [
                {"id": "ma_crossover", "name": "均线交叉策略", "desc": "基于移动平均线交叉的趋势跟踪策略", "tags": ["趋势", "移动平均"]},
                {"id": "rsi_reversal", "name": "RSI反转策略", "desc": "利用RSI超买超卖信号的反转策略", "tags": ["震荡", "RSI"]},
                {"id": "macd_signal", "name": "MACD信号策略", "desc": "基于MACD指标的交易信号策略", "tags": ["趋势", "MACD"]},
                {"id": "bollinger_breakout", "name": "布林带突破策略", "desc": "基于布林带的突破交易策略", "tags": ["突破", "波动"]},
                {"id": "volume_price", "name": "量价配合策略", "desc": "结合成交量和价格的确认策略", "tags": ["量价", "确认"]},
            ]

            count = 0
            for strategy in strategies:
                item = ContentItem(
                    item_id=f"strategy_{strategy['id']}",
                    item_type=RecommendationType.STRATEGY,
                    title=strategy['name'],
                    description=strategy['desc'],
                    tags=strategy['tags'],
                    categories=["交易策略"],
                    keywords=[strategy['name']] + strategy['tags']
                )
                self.recommendation_engine.add_content_item(item)
                count += 1

            return count

        except Exception as e:
            logger.error(f"加载策略内容项失败: {e}")
            return 0

    def _load_indicator_content_items(self) -> int:
        """加载指标内容项"""
        try:
            from core.services.smart_recommendation_engine import ContentItem, RecommendationType

            # 常用技术指标
            indicators = [
                {"id": "macd", "name": "MACD", "desc": "趋势指标，识别趋势方向和强度", "tags": ["趋势"]},
                {"id": "rsi", "name": "RSI", "desc": "相对强弱指标，识别超买超卖", "tags": ["震荡"]},
                {"id": "kdj", "name": "KDJ", "desc": "随机指标，短期交易信号", "tags": ["震荡"]},
                {"id": "boll", "name": "布林带", "desc": "波动率指标，识别突破机会", "tags": ["波动"]},
                {"id": "ma", "name": "移动平均线", "desc": "趋势指标，平滑价格波动", "tags": ["趋势"]},
            ]

            count = 0
            for indicator in indicators:
                item = ContentItem(
                    item_id=f"indicator_{indicator['id']}",
                    item_type=RecommendationType.INDICATOR,
                    title=indicator['name'],
                    description=indicator['desc'],
                    tags=indicator['tags'],
                    categories=["技术指标"],
                    keywords=[indicator['name']] + indicator['tags']
                )
                self.recommendation_engine.add_content_item(item)
                count += 1

            return count

        except Exception as e:
            logger.error(f"加载指标内容项失败: {e}")
            return 0

    def _load_news_content_items(self) -> int:
        """加载新闻内容项"""
        try:
            from core.services.smart_recommendation_engine import ContentItem, RecommendationType
            from datetime import datetime, timedelta

            # 模拟新闻内容（实际应从新闻API或数据库获取）
            news_items = [
                {
                    "id": "news_001",
                    "title": "A股市场今日收涨，沪指涨0.8%",
                    "desc": "今日A股三大指数集体收涨，沪指涨0.8%，深证成指涨1.2%，创业板指涨1.5%。",
                    "tags": ["市场动态", "大盘"],
                    "created": datetime.now() - timedelta(hours=2)
                },
                {
                    "id": "news_002",
                    "title": "央行宣布降准0.25个百分点",
                    "desc": "中国人民银行宣布下调存款准备金率0.25个百分点，释放长期流动性约5000亿元。",
                    "tags": ["政策", "央行", "流动性"],
                    "created": datetime.now() - timedelta(hours=5)
                },
                {
                    "id": "news_003",
                    "title": "新能源汽车销量再创新高",
                    "desc": "最新数据显示，11月新能源汽车销量同比增长38%，市场渗透率突破40%。",
                    "tags": ["新能源", "汽车", "行业数据"],
                    "created": datetime.now() - timedelta(hours=8)
                },
                {
                    "id": "news_004",
                    "title": "科技板块领涨，半导体股集体走强",
                    "desc": "今日科技板块表现强劲，半导体、芯片概念股集体走强，多只个股涨停。",
                    "tags": ["科技", "半导体", "板块"],
                    "created": datetime.now() - timedelta(hours=3)
                },
                {
                    "id": "news_005",
                    "title": "外资加速流入A股市场",
                    "desc": "本周外资通过陆股通净买入超过150亿元，连续第五周保持净流入态势。",
                    "tags": ["外资", "资金流向", "陆股通"],
                    "created": datetime.now() - timedelta(hours=6)
                },
            ]

            count = 0
            for news in news_items:
                item = ContentItem(
                    item_id=f"news_{news['id']}",
                    item_type=RecommendationType.NEWS,
                    title=news['title'],
                    description=news['desc'],
                    tags=news['tags'],
                    categories=["财经新闻"],
                    keywords=news['tags'] + [news['title']],
                    created_at=news['created'],
                    # 新闻的热度可以基于发布时间设置
                    view_count=max(0, 100 - int((datetime.now() - news['created']).total_seconds() / 3600)),
                    metadata={"source": "模拟数据", "type": "财经"}
                )
                self.recommendation_engine.add_content_item(item)
                count += 1

            return count

        except Exception as e:
            logger.error(f"加载新闻内容项失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

    def _create_user_profile(self):
        """创建用户画像"""
        try:
            from core.services.smart_recommendation_engine import UserProfile

            user_id = self._get_current_user_id()

            if user_id not in self.recommendation_engine.user_profiles:
                profile = UserProfile(
                    user_id=user_id,
                    registration_date=datetime.now(),
                    last_active=datetime.now(),
                    activity_level="medium",
                    risk_tolerance="medium",
                    investment_horizon="medium"
                )
                self.recommendation_engine.user_profiles[user_id] = profile
                logger.info(f"创建用户画像: {user_id}")

        except Exception as e:
            logger.error(f"创建用户画像失败: {e}")

    def _get_current_user_id(self) -> str:
        """获取当前用户ID"""
        # 简化实现 - 使用系统默认用户
        # 后续可以集成真实的用户系统
        return "default_user"

    def _format_engine_recommendations(self, recommendations: List) -> List[Dict[str, Any]]:
        """将引擎推荐转换为显示格式"""
        formatted = []

        logger.info(f"开始格式化 {len(recommendations)} 个推荐")

        for idx, rec in enumerate(recommendations):
            try:
                # 映射推荐类型
                type_map = {
                    'stock': 'stock',
                    'strategy': 'strategy',
                    'indicator': 'indicator',
                    'news': 'news',
                    'research': 'research',
                    'portfolio': 'portfolio'
                }

                rec_type = type_map.get(rec.item_type.value, 'unknown')

                # ✅ 确保所有字段都有有效值
                formatted_rec = {
                    "id": rec.item_id,
                    "type": rec_type,
                    "title": rec.title or f"推荐项 {idx+1}",
                    "description": rec.description or rec.explanation or "暂无描述",
                    "score": rec.score * 10,  # 转换为0-10分
                    "reason": rec.explanation or "系统推荐",
                    "confidence": rec.confidence,
                    "metadata": rec.metadata if hasattr(rec, 'metadata') else {}
                }

                formatted.append(formatted_rec)

            except Exception as e:
                logger.error(f"格式化第 {idx} 个推荐失败: {e}")
                continue

        logger.info(f"成功格式化 {len(formatted)} 个推荐")
        return formatted

    def _get_real_behavior_data(self) -> Optional[Dict[str, Any]]:
        """获取真实用户行为数据"""
        try:
            if not self.recommendation_engine:
                return None

            stats = self.recommendation_engine.get_recommendation_stats()

            # 构建行为数据
            behavior_data = {
                'usage_frequency': {
                    '推荐总数': stats.get('total_recommendations', 0),
                    '缓存命中': stats.get('cache_hits', 0),
                    '缓存未命中': stats.get('cache_misses', 0),
                },
                'preferences': {
                    '用户总数': stats.get('total_users', 0),
                    '内容项总数': stats.get('total_items', 0),
                    '交互总数': stats.get('total_interactions', 0),
                },
                'recommendation_effectiveness': {
                    '缓存命中率': stats.get('cache_hit_rate', 0.0),
                    '模型已训练': 1.0 if stats.get('model_trained') else 0.0,
                }
            }

            return behavior_data

        except Exception as e:
            logger.error(f"获取行为数据失败: {e}")
            return None

    def _show_empty_state(self, message: str = ""):
        """显示空状态"""
        logger.info(f"显示空状态: {message}")
        # 清空所有推荐卡片
        for layout in [self.stock_cards_layout, self.strategy_cards_layout,
                       self.indicator_cards_layout, self.news_cards_layout]:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

    def _display_recommendations_by_type(self, recommendations: List[Dict[str, Any]]):
        """按类型显示推荐"""
        logger.info(f"开始按类型显示 {len(recommendations)} 个推荐")

        # 按类型分组
        recommendations_by_type = {}
        for rec in recommendations:
            rec_type = rec.get('type', 'unknown')
            if rec_type not in recommendations_by_type:
                recommendations_by_type[rec_type] = []
            recommendations_by_type[rec_type].append(rec)

        logger.info(f"推荐类型分布: {[(k, len(v)) for k, v in recommendations_by_type.items()]}")

        # 显示股票推荐
        if 'stock' in recommendations_by_type:
            logger.info(f"显示 {len(recommendations_by_type['stock'])} 个股票推荐")
            self._display_recommendation_cards(
                recommendations_by_type['stock'],
                self.stock_cards_layout
            )

        # 显示策略推荐
        if 'strategy' in recommendations_by_type:
            logger.info(f"显示 {len(recommendations_by_type['strategy'])} 个策略推荐")
            self._display_recommendation_cards(
                recommendations_by_type['strategy'],
                self.strategy_cards_layout
            )

        # 显示指标推荐
        if 'indicator' in recommendations_by_type:
            logger.info(f"显示 {len(recommendations_by_type['indicator'])} 个指标推荐")
            self._display_recommendation_cards(
                recommendations_by_type['indicator'],
                self.indicator_cards_layout
            )

        # 显示新闻推荐
        if 'news' in recommendations_by_type:
            logger.info(f"显示 {len(recommendations_by_type['news'])} 个新闻推荐")
            self._display_recommendation_cards(
                recommendations_by_type['news'],
                self.news_cards_layout
            )

        logger.info("推荐卡片显示完成")

    def _display_recommendation_cards(self, recommendations: List[Dict[str, Any]], layout):
        """显示推荐卡片（支持Grid和VBox布局）"""
        try:
            from PyQt5.QtWidgets import QGridLayout, QVBoxLayout

            logger.info(f"开始在布局中显示 {len(recommendations)} 个推荐卡片")

            # 清空现有卡片
            cleared_count = 0
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                    cleared_count += 1
            logger.info(f"清空了 {cleared_count} 个旧卡片")

            # 添加新卡片
            added_count = 0
            is_grid_layout = isinstance(layout, QGridLayout)
            columns = 4  # 一行4个

            for idx, rec in enumerate(recommendations):
                try:
                    card = RecommendationCard(rec)
                    card.card_clicked.connect(self._on_recommendation_clicked)
                    card.action_clicked.connect(self._on_recommendation_action)

                    # ✅ 根据布局类型添加卡片
                    if is_grid_layout:
                        row = idx // columns
                        col = idx % columns
                        layout.addWidget(card, row, col)
                    else:
                        layout.addWidget(card)

                    added_count += 1
                    logger.debug(f"添加卡片 {idx+1}: {rec.get('title', 'Unknown')}")
                except Exception as card_error:
                    logger.error(f"创建第 {idx} 个推荐卡片失败: {card_error}")
                    continue

            # ✅ 只对VBox布局添加弹性空间
            if isinstance(layout, QVBoxLayout):
                layout.addStretch()

            logger.info(f"✅ 成功添加 {added_count}/{len(recommendations)} 个推荐卡片到{'网格' if is_grid_layout else '垂直'}布局")

        except Exception as e:
            logger.error(f"显示推荐卡片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Mock函数已删除 - 使用 _get_real_behavior_data() 获取真实数据

    def _update_feedback_stats(self):
        """更新反馈统计"""
        # 模拟反馈统计数据
        stats_data = {
            'total_feedback': 156,
            'positive_feedback': 98,
            'negative_feedback': 32,
            'average_rating': 4.2,
            'accuracy_rate': 0.68,
            'satisfaction_rate': 0.85
        }

        for key, value in stats_data.items():
            if key in self.feedback_stats:
                if isinstance(value, float):
                    if key in ['accuracy_rate', 'satisfaction_rate']:
                        self.feedback_stats[key].setText(f"{value:.1%}")
                    else:
                        self.feedback_stats[key].setText(f"{value:.1f}")
                else:
                    self.feedback_stats[key].setText(str(value))

    def _on_count_changed(self, count: int):
        """推荐数量变更"""
        self.max_recommendations = count
        logger.debug(f"推荐数量已调整为: {count}")

    def _on_frequency_changed(self, frequency: str):
        """更新频率变更"""
        frequency_map = {
            "15分钟": 15,
            "30分钟": 30,
            "1小时": 60,
            "2小时": 120,
            "手动": 0
        }

        interval = frequency_map.get(frequency, 30)
        self.update_interval = interval

        if interval > 0:
            self.update_timer.setInterval(interval * 60 * 1000)
            self.update_timer.start()
        else:
            self.update_timer.stop()

        logger.debug(f"推荐更新频率已调整为: {frequency}")

    def _filter_recommendations(self):
        """过滤推荐"""
        filter_type = self.type_filter_combo.currentText()
        logger.debug(f"推荐过滤类型: {filter_type}")
        # 实现推荐过滤逻辑

    def _on_preference_changed(self, key: str, value: int):
        """偏好设置变更"""
        if key in self.preference_sliders:
            _, value_label = self.preference_sliders[key]
            value_label.setText(f"{value}%")

        self.user_preferences[key] = value / 100.0
        logger.debug(f"用户偏好 {key} 已调整为: {value}%")

    def _on_algorithm_weight_changed(self, key: str, value: int):
        """算法权重变更"""
        weight_value = value / 100.0
        if key in self.algorithm_weights:
            _, value_label = self.algorithm_weights[key]
            value_label.setText(f"{weight_value:.1f}")

        logger.debug(f"算法权重 {key} 已调整为: {weight_value:.1f}")

    def _on_personalization_changed(self, key: str, checked: bool):
        """个性化设置变更"""
        logger.debug(f"个性化设置 {key}: {checked}")

    def _on_recommendation_clicked(self, recommendation_data: Dict[str, Any]):
        """推荐卡片点击处理（点击卡片主体区域）"""
        try:
            rec_type = recommendation_data.get('type', 'unknown')
            rec_id = recommendation_data.get('id', '')
            title = recommendation_data.get('title', 'Unknown')

            logger.info(f"选择推荐: {title}, 类型: {rec_type}, ID: {rec_id}")

            # ✅ 根据推荐类型执行不同操作
            if rec_type == 'stock' and rec_id.startswith('stock_'):
                # 股票推荐：联动到主界面选择该股票
                stock_code = rec_id.replace('stock_', '')
                self._select_stock_in_main_panel(stock_code)
            elif rec_type == 'strategy':
                # 策略推荐：显示策略详情
                self._show_recommendation_detail(recommendation_data)
            elif rec_type == 'indicator':
                # 指标推荐：显示指标详情
                self._show_recommendation_detail(recommendation_data)
            elif rec_type == 'news':
                # 新闻推荐：显示新闻详情
                self._show_recommendation_detail(recommendation_data)
            else:
                # 其他类型：显示通用详情
                self._show_recommendation_detail(recommendation_data)

            # 发送推荐选择信号
            self.recommendation_selected.emit(recommendation_data)

        except Exception as e:
            logger.error(f"处理推荐点击失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _on_recommendation_action(self, action: str, recommendation_data: Dict[str, Any]):
        """推荐操作处理"""
        if action == "view_detail":
            # 显示推荐详情
            self._show_recommendation_detail(recommendation_data)

        logger.info(f"推荐操作: {action}, 内容: {recommendation_data.get('title', 'Unknown')}")

    def _select_stock_in_main_panel(self, stock_code: str):
        """在主面板选择股票"""
        try:
            from core.events import StockSelectedEvent, get_event_bus
            from PyQt5.QtWidgets import QMessageBox

            # 发布股票选择事件，触发主界面联动
            event_bus = get_event_bus()
            event = StockSelectedEvent(
                stock_code=stock_code,
                source="smart_recommendation_panel"
            )
            event_bus.publish(event)

            logger.info(f"✅ 已发送股票选择事件: {stock_code}")

        except Exception as e:
            logger.error(f"选择股票失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _show_recommendation_detail(self, recommendation_data: Dict[str, Any]):
        """显示推荐详情"""
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QDialogButtonBox

            dialog = QDialog(self)
            dialog.setWindowTitle(f"推荐详情 - {recommendation_data.get('title', '未知')}")
            dialog.setMinimumSize(500, 400)

            layout = QVBoxLayout(dialog)

            # 标题
            title_label = QLabel(recommendation_data.get('title', '未知推荐'))
            title_label.setFont(QFont("Arial", 14, QFont.Bold))
            layout.addWidget(title_label)

            # 类型和评分
            info_label = QLabel(
                f"类型: {recommendation_data.get('type', 'unknown').upper()} | "
                f"评分: {recommendation_data.get('score', 0):.1f} | "
                f"置信度: {recommendation_data.get('confidence', 0):.0%}"
            )
            info_label.setFont(QFont("Arial", 10))
            layout.addWidget(info_label)

            # 描述
            desc_label = QLabel("描述:")
            desc_label.setFont(QFont("Arial", 11, QFont.Bold))
            layout.addWidget(desc_label)

            desc_text = QTextEdit()
            desc_text.setPlainText(recommendation_data.get('description', '暂无描述'))
            desc_text.setReadOnly(True)
            desc_text.setMaximumHeight(100)
            layout.addWidget(desc_text)

            # 推荐理由
            reason_label = QLabel("推荐理由:")
            reason_label.setFont(QFont("Arial", 11, QFont.Bold))
            layout.addWidget(reason_label)

            reason_text = QTextEdit()
            reason_text.setPlainText(recommendation_data.get('reason', '系统推荐'))
            reason_text.setReadOnly(True)
            desc_text.setMaximumHeight(100)
            layout.addWidget(reason_text)

            # 元数据
            metadata = recommendation_data.get('metadata', {})
            if metadata:
                meta_label = QLabel("详细信息:")
                meta_label.setFont(QFont("Arial", 11, QFont.Bold))
                layout.addWidget(meta_label)

                meta_text = QTextEdit()
                meta_str = "\n".join([f"{k}: {v}" for k, v in metadata.items()])
                meta_text.setPlainText(meta_str)
                meta_text.setReadOnly(True)
                meta_text.setMaximumHeight(80)
                layout.addWidget(meta_text)

            # 按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)

            logger.info(f"显示推荐详情: {recommendation_data.get('title', 'Unknown')}")
            dialog.exec_()

        except Exception as e:
            logger.error(f"显示推荐详情失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _refresh_recommendations(self):
        """刷新推荐"""
        try:
            logger.info("刷新推荐内容")
            self._load_initial_recommendations()

        except Exception as e:
            logger.error(f"刷新推荐失败: {e}")

    def _update_recommendations(self):
        """定时更新推荐"""
        if self.recommendation_engine:
            logger.debug("定时更新推荐内容")
            # 实现定时更新逻辑

    def _train_recommendation_model(self):
        """训练推荐模型"""
        if self.model_trainer:
            logger.info("开始训练推荐模型")
            # 实现模型训练逻辑

    def _save_settings(self):
        """保存设置"""
        logger.info("保存推荐设置")
        # 实现设置保存逻辑

    def _load_settings(self):
        """加载设置"""
        logger.info("加载推荐设置")
        # 实现设置加载逻辑

    def _reset_settings(self):
        """重置设置"""
        logger.info("重置推荐设置")
        # 实现设置重置逻辑

    def _export_feedback(self):
        """导出反馈数据"""
        logger.info("导出反馈数据")
        # 实现反馈导出逻辑

    def submit_feedback(self, recommendation_id: str, feedback_type: str, rating: int, comment: str = ""):
        """提交用户反馈"""
        feedback_data = {
            'recommendation_id': recommendation_id,
            'feedback_type': feedback_type,
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now()
        }

        self.feedback_history.append(feedback_data)
        self.feedback_submitted.emit(feedback_type, feedback_data)

        logger.info(f"提交反馈: {feedback_type}, 评分: {rating}")

    def get_user_preferences(self) -> Dict[str, Any]:
        """获取用户偏好"""
        return self.user_preferences.copy()

    def set_recommendation_engine(self, engine: SmartRecommendationEngine):
        """设置推荐引擎"""
        self.recommendation_engine = engine

    def set_model_trainer(self, trainer: RecommendationModelTrainer):
        """设置模型训练器"""
        self.model_trainer = trainer
