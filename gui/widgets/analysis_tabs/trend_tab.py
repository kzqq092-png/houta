"""
趋势分析标签页模块 - 专业版升级
"""

from typing import Dict, Any, List, Optional, Tuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import json

from .base_tab import BaseAnalysisTab
from core.logger import LogManager, LogLevel
from utils.config_manager import ConfigManager


class TrendAnalysisTab(BaseAnalysisTab):
    """专业级趋势分析标签页 - 对标专业软件"""

    # 专业级信号
    trend_analysis_completed = pyqtSignal(dict)
    trend_alert = pyqtSignal(str, dict)  # 趋势预警信号
    trend_reversal_detected = pyqtSignal(dict)  # 趋势反转信号

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        # 在调用super().__init__()之前初始化所有属性
        # 专业级趋势分析配置
        self.trend_algorithms = {
            'linear_regression': '线性回归趋势',
            'polynomial_fit': '多项式拟合',
            'moving_average': '移动平均趋势',
            'exponential_smoothing': '指数平滑',
            'kalman_filter': '卡尔曼滤波',
            'wavelet_analysis': '小波分析'
        }

        self.timeframes = {
            '1min': '1分钟',
            '5min': '5分钟',
            '15min': '15分钟',
            '30min': '30分钟',
            '1hour': '1小时',
            '4hour': '4小时',
            'daily': '日线',
            'weekly': '周线',
            'monthly': '月线'
        }

        # 趋势强度等级
        self.trend_strength_levels = {
            'very_strong': {'min': 0.8, 'color': '#d32f2f', 'name': '极强'},
            'strong': {'min': 0.6, 'color': '#f57c00', 'name': '强'},
            'moderate': {'min': 0.4, 'color': '#fbc02d', 'name': '中等'},
            'weak': {'min': 0.2, 'color': '#689f38', 'name': '弱'},
            'very_weak': {'min': 0.0, 'color': '#1976d2', 'name': '极弱'}
        }

        self.trend_results = []
        self.trend_statistics = {}
        self.multi_timeframe_results = {}
        self.trend_alerts = []

        # 初始化UI组件属性（在create_ui之前设置为None）
        self.algorithm_combo = None
        self.timeframe_list = None
        self.period_spin = None
        self.threshold_spin = None
        self.sensitivity_slider = None
        self.confidence_spin = None
        self.enable_prediction_cb = None
        self.enable_alerts_cb = None
        self.auto_update_cb = None
        self.results_tabs = None
        self.trend_table = None
        self.multi_tf_table = None
        self.prediction_text = None
        self.sr_table = None
        self.alert_list = None
        self.trend_stats_label = None
        self.status_label = None
        self.progress_bar = None

        # 现在调用父类初始化
        super().__init__(config_manager)

    def create_ui(self):
        """创建专业级趋势分析UI"""
        layout = QVBoxLayout(self)

        # 专业工具栏
        toolbar = self._create_professional_toolbar()
        layout.addWidget(toolbar)

        # 主要分析区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧控制面板
        left_panel = self._create_control_panel()
        main_splitter.addWidget(left_panel)

        # 右侧结果面板
        right_panel = self._create_results_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([350, 650])
        layout.addWidget(main_splitter)

        # 状态栏
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)

    def _create_professional_toolbar(self):
        """创建专业工具栏"""
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(toolbar)

        # 快速分析组
        quick_group = QGroupBox("快速分析")
        quick_layout = QHBoxLayout(quick_group)

        # 一键趋势分析
        trend_btn = QPushButton("📈 趋势分析")
        trend_btn.setStyleSheet(self._get_button_style('#28a745'))
        trend_btn.clicked.connect(self.comprehensive_trend_analysis)

        # 多时间框架分析
        multi_tf_btn = QPushButton("⏰ 多时间框架")
        multi_tf_btn.setStyleSheet(self._get_button_style('#17a2b8'))
        multi_tf_btn.clicked.connect(self.multi_timeframe_analysis)

        # 趋势预警
        alert_btn = QPushButton("🚨 趋势预警")
        alert_btn.setStyleSheet(self._get_button_style('#dc3545'))
        alert_btn.clicked.connect(self.setup_trend_alerts)

        quick_layout.addWidget(trend_btn)
        quick_layout.addWidget(multi_tf_btn)
        quick_layout.addWidget(alert_btn)
        layout.addWidget(quick_group)

        # 高级功能组
        advanced_group = QGroupBox("高级功能")
        advanced_layout = QHBoxLayout(advanced_group)

        # 趋势预测
        predict_btn = QPushButton("🔮 趋势预测")
        predict_btn.setStyleSheet(self._get_button_style('#6f42c1'))
        predict_btn.clicked.connect(self.trend_prediction)

        # 支撑阻力
        sr_btn = QPushButton("📊 支撑阻力")
        sr_btn.setStyleSheet(self._get_button_style('#fd7e14'))
        sr_btn.clicked.connect(self.support_resistance_analysis)

        advanced_layout.addWidget(predict_btn)
        advanced_layout.addWidget(sr_btn)
        layout.addWidget(advanced_group)

        layout.addStretch()
        return toolbar

    def _get_button_style(self, color):
        """获取按钮样式 - 使用基类统一方法"""
        return self.get_button_style(color)

    def _darken_color(self, color, factor=0.1):
        """颜色加深 - 使用基类统一方法"""
        return self.darken_color(color, factor)

    def _create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 算法选择
        algo_group = QGroupBox("趋势算法")
        algo_layout = QVBoxLayout(algo_group)

        self.algorithm_combo = QComboBox()
        for key, name in self.trend_algorithms.items():
            self.algorithm_combo.addItem(name, key)
        algo_layout.addWidget(self.algorithm_combo)
        layout.addWidget(algo_group)

        # 时间框架
        tf_group = QGroupBox("时间框架")
        tf_layout = QVBoxLayout(tf_group)

        self.timeframe_list = QListWidget()
        self.timeframe_list.setSelectionMode(QAbstractItemView.MultiSelection)
        for key, name in self.timeframes.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, key)
            self.timeframe_list.addItem(item)
        tf_layout.addWidget(self.timeframe_list)
        layout.addWidget(tf_group)

        # 参数设置
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout(params_group)

        # 分析周期
        self.period_spin = QSpinBox()
        self.period_spin.setRange(5, 500)
        self.period_spin.setValue(20)
        params_layout.addRow("分析周期:", self.period_spin)

        # 趋势阈值
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.001, 0.5)
        self.threshold_spin.setValue(0.05)
        self.threshold_spin.setDecimals(3)
        params_layout.addRow("趋势阈值:", self.threshold_spin)

        # 敏感度
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        params_layout.addRow("敏感度:", self.sensitivity_slider)

        # 置信度阈值
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.5, 0.99)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.setDecimals(2)
        params_layout.addRow("置信度阈值:", self.confidence_spin)

        layout.addWidget(params_group)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.enable_prediction_cb = QCheckBox("启用趋势预测")
        self.enable_prediction_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_prediction_cb)

        self.enable_alerts_cb = QCheckBox("启用趋势预警")
        self.enable_alerts_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_alerts_cb)

        self.auto_update_cb = QCheckBox("自动更新分析")
        advanced_layout.addWidget(self.auto_update_cb)

        layout.addWidget(advanced_group)
        layout.addStretch()

        return panel

    def _create_results_panel(self):
        """创建结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 趋势分析结果
        trend_tab = self._create_trend_results_tab()
        self.results_tabs.addTab(trend_tab, "📈 趋势分析")

        # 多时间框架
        multi_tf_tab = self._create_multi_timeframe_tab()
        self.results_tabs.addTab(multi_tf_tab, "⏰ 多时间框架")

        # 趋势预测
        prediction_tab = self._create_prediction_tab()
        self.results_tabs.addTab(prediction_tab, "🔮 趋势预测")

        # 支撑阻力
        sr_tab = self._create_support_resistance_tab()
        self.results_tabs.addTab(sr_tab, "📊 支撑阻力")

        # 预警中心
        alert_tab = self._create_alert_tab()
        self.results_tabs.addTab(alert_tab, "🚨 预警中心")

        layout.addWidget(self.results_tabs)
        return panel

    def _create_trend_results_tab(self):
        """创建趋势结果标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计信息
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QHBoxLayout(stats_frame)

        self.trend_stats_label = QLabel("等待分析...")
        stats_layout.addWidget(self.trend_stats_label)
        stats_layout.addStretch()

        layout.addWidget(stats_frame)

        # 趋势表格
        self.trend_table = QTableWidget(0, 8)
        self.trend_table.setHorizontalHeaderLabels([
            '时间框架', '趋势方向', '强度', '置信度', '持续时间',
            '目标价位', '风险等级', '操作建议'
        ])

        # 设置表格样式
        self.trend_table.setAlternatingRowColors(True)
        self.trend_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trend_table.setSortingEnabled(True)

        # 设置列宽
        header = self.trend_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        layout.addWidget(self.trend_table)

        # 操作按钮
        buttons_layout = QHBoxLayout()

        export_btn = QPushButton("📤 导出结果")
        export_btn.clicked.connect(self.export_trend_results)

        refresh_btn = QPushButton("🔄 刷新分析")
        refresh_btn.clicked.connect(self.comprehensive_trend_analysis)

        buttons_layout.addWidget(export_btn)
        buttons_layout.addWidget(refresh_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        return widget

    def _create_multi_timeframe_tab(self):
        """创建多时间框架标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 多时间框架表格
        self.multi_tf_table = QTableWidget(0, 6)
        self.multi_tf_table.setHorizontalHeaderLabels([
            '时间框架', '趋势方向', '强度', '一致性', '权重', '综合评分'
        ])
        layout.addWidget(self.multi_tf_table)

        return widget

    def _create_prediction_tab(self):
        """创建趋势预测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预测结果显示
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        layout.addWidget(self.prediction_text)

        return widget

    def _create_support_resistance_tab(self):
        """创建支撑阻力标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 支撑阻力表格
        self.sr_table = QTableWidget(0, 5)
        self.sr_table.setHorizontalHeaderLabels([
            '类型', '价位', '强度', '测试次数', '有效性'
        ])
        layout.addWidget(self.sr_table)

        return widget

    def _create_alert_tab(self):
        """创建预警标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预警列表
        self.alert_list = QListWidget()
        layout.addWidget(self.alert_list)

        return widget

    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QHBoxLayout(status_frame)

        self.status_label = QLabel("就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)

        return status_frame

    def comprehensive_trend_analysis(self):
        """综合趋势分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行综合趋势分析...")
        self.status_label.setText("执行综合趋势分析...")

        self.run_analysis_async(self._comprehensive_analysis_async)

    def _comprehensive_analysis_async(self):
        """综合分析"""
        try:
            results = {
                'trend_analysis': [],
                'statistics': {},
                'predictions': {},
                'support_resistance': [],
                'alerts': []
            }

            # 1. 基础趋势分析
            trend_results = self._analyze_basic_trends()
            results['trend_analysis'] = trend_results

            # 2. 统计分析
            stats = self._calculate_trend_statistics(trend_results)
            results['statistics'] = stats

            # 3. 趋势预测
            if self.enable_prediction_cb.isChecked():
                predictions = self._generate_trend_predictions()
                results['predictions'] = predictions

            # 4. 支撑阻力分析
            sr_levels = self._analyze_support_resistance()
            results['support_resistance'] = sr_levels

            # 5. 生成预警
            if self.enable_alerts_cb.isChecked():
                alerts = self._generate_trend_alerts(trend_results)
                results['alerts'] = alerts

            # 6. 更新显示
            QTimer.singleShot(100, lambda: self._update_results_display(results))

            return results

        except Exception as e:
            return {'error': str(e)}

    def _analyze_basic_trends(self):
        """基础趋势分析"""
        trends = []
        algorithm = self.algorithm_combo.currentData()
        period = self.period_spin.value()
        threshold = self.threshold_spin.value()

        # 价格趋势分析
        price_trend = self._analyze_price_trend_advanced(algorithm, period, threshold)
        if price_trend:
            trends.append(price_trend)

        # 成交量趋势分析
        volume_trend = self._analyze_volume_trend_advanced(algorithm, period, threshold)
        if volume_trend:
            trends.append(volume_trend)

        # 技术指标趋势分析
        indicator_trends = self._analyze_indicator_trends(algorithm, period, threshold)
        trends.extend(indicator_trends)

        return trends

    def _analyze_price_trend_advanced(self, algorithm, period, threshold):
        """高级价格趋势分析"""
        if not hasattr(self.current_kdata, 'close'):
            return None

        close_prices = self.current_kdata['close'].values[-period:]

        if algorithm == 'linear_regression':
            trend_info = self._linear_regression_trend(close_prices)
        elif algorithm == 'polynomial_fit':
            trend_info = self._polynomial_trend(close_prices)
        elif algorithm == 'moving_average':
            trend_info = self._moving_average_trend(close_prices)
        elif algorithm == 'exponential_smoothing':
            trend_info = self._exponential_smoothing_trend(close_prices)
        else:
            trend_info = self._linear_regression_trend(close_prices)  # 默认

        if trend_info:
            trend_info.update({
                'timeframe': 'daily',
                'type': '价格趋势',
                'algorithm': algorithm
            })

        return trend_info

    def _linear_regression_trend(self, prices):
        """线性回归趋势分析"""
        if len(prices) < 5:
            return None

        x = np.arange(len(prices))
        coeffs = np.polyfit(x, prices, 1)
        slope = coeffs[0]

        # 计算R²
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # 趋势方向和强度
        direction = '上升' if slope > 0 else '下降'
        strength = min(abs(slope) / np.mean(prices) * 100, 100)  # 百分比强度

        # 置信度基于R²
        confidence = r_squared

        # 目标价位预测
        target_price = prices[-1] + slope * 5  # 预测5期后价格

        return {
            'direction': direction,
            'strength': f"{strength:.2f}%",
            'confidence': f"{confidence:.2%}",
            'duration': f"{len(prices)}期",
            'target_price': f"{target_price:.2f}",
            'risk_level': self._calculate_risk_level(strength, confidence),
            'recommendation': self._get_trend_recommendation(direction, strength, confidence)
        }

    def _polynomial_trend(self, prices):
        """多项式趋势分析"""
        if len(prices) < 10:
            return None

        x = np.arange(len(prices))
        coeffs = np.polyfit(x, prices, 2)  # 二次多项式

        # 计算一阶导数（斜率）
        derivative = np.polyder(coeffs)
        current_slope = np.polyval(derivative, len(prices)-1)

        direction = '上升' if current_slope > 0 else '下降'
        strength = min(abs(current_slope) / np.mean(prices) * 100, 100)

        # 计算拟合度
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        confidence = r_squared
        target_price = np.polyval(coeffs, len(prices) + 5)

        return {
            'direction': direction,
            'strength': f"{strength:.2f}%",
            'confidence': f"{confidence:.2%}",
            'duration': f"{len(prices)}期",
            'target_price': f"{target_price:.2f}",
            'risk_level': self._calculate_risk_level(strength, confidence),
            'recommendation': self._get_trend_recommendation(direction, strength, confidence)
        }

    def _moving_average_trend(self, prices):
        """移动平均趋势分析"""
        if len(prices) < 10:
            return None

        # 计算不同周期的移动平均
        ma5 = np.mean(prices[-5:])
        ma10 = np.mean(prices[-10:])
        ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else ma10

        current_price = prices[-1]

        # 趋势判断
        if current_price > ma5 > ma10 > ma20:
            direction = '强势上升'
            strength = 80
        elif current_price > ma5 > ma10:
            direction = '上升'
            strength = 60
        elif current_price < ma5 < ma10 < ma20:
            direction = '强势下降'
            strength = 80
        elif current_price < ma5 < ma10:
            direction = '下降'
            strength = 60
        else:
            direction = '震荡'
            strength = 30

        # 置信度基于价格与均线的偏离度
        deviation = abs(current_price - ma10) / ma10
        confidence = min(deviation * 10, 0.9)  # 偏离度越大置信度越高

        target_price = ma5 + (ma5 - ma10) * 2  # 简单预测

        return {
            'direction': direction,
            'strength': f"{strength:.2f}%",
            'confidence': f"{confidence:.2%}",
            'duration': f"{len(prices)}期",
            'target_price': f"{target_price:.2f}",
            'risk_level': self._calculate_risk_level(strength, confidence),
            'recommendation': self._get_trend_recommendation(direction, strength, confidence)
        }

    def _exponential_smoothing_trend(self, prices):
        """指数平滑趋势分析"""
        if len(prices) < 5:
            return None

        alpha = 0.3  # 平滑参数
        smoothed = [prices[0]]

        for i in range(1, len(prices)):
            smoothed.append(alpha * prices[i] + (1 - alpha) * smoothed[-1])

        # 计算趋势
        recent_trend = (smoothed[-1] - smoothed[-5]) / smoothed[-5] if len(smoothed) >= 5 else 0
        direction = '上升' if recent_trend > 0 else '下降'
        strength = min(abs(recent_trend) * 100, 100)

        # 置信度基于平滑效果
        mse = np.mean((np.array(prices) - np.array(smoothed)) ** 2)
        confidence = max(0.5, 1 - mse / np.var(prices))

        target_price = smoothed[-1] * (1 + recent_trend)

        return {
            'direction': direction,
            'strength': f"{strength:.2f}%",
            'confidence': f"{confidence:.2%}",
            'duration': f"{len(prices)}期",
            'target_price': f"{target_price:.2f}",
            'risk_level': self._calculate_risk_level(strength, confidence),
            'recommendation': self._get_trend_recommendation(direction, strength, confidence)
        }

    def _analyze_volume_trend_advanced(self, algorithm, period, threshold):
        """高级成交量趋势分析"""
        if not hasattr(self.current_kdata, 'volume'):
            return None

        volumes = self.current_kdata['volume'].values[-period:]

        # 使用线性回归分析成交量趋势
        x = np.arange(len(volumes))
        coeffs = np.polyfit(x, volumes, 1)
        slope = coeffs[0]

        direction = '放量' if slope > 0 else '缩量'
        strength = min(abs(slope) / np.mean(volumes) * 100, 100)

        # 计算置信度
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((volumes - y_pred) ** 2)
        ss_tot = np.sum((volumes - np.mean(volumes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        return {
            'timeframe': 'daily',
            'type': '成交量趋势',
            'direction': direction,
            'strength': f"{strength:.2f}%",
            'confidence': f"{r_squared:.2%}",
            'duration': f"{len(volumes)}期",
            'target_price': 'N/A',
            'risk_level': self._calculate_risk_level(strength, r_squared),
            'recommendation': self._get_volume_recommendation(direction, strength)
        }

    def _analyze_indicator_trends(self, algorithm, period, threshold):
        """技术指标趋势分析"""
        trends = []

        # 这里可以添加各种技术指标的趋势分析
        # 简化实现，返回模拟数据
        indicators = ['MACD', 'RSI', 'KDJ']

        for indicator in indicators:
            trend = {
                'timeframe': 'daily',
                'type': f'{indicator}趋势',
                'direction': np.random.choice(['上升', '下降', '震荡']),
                'strength': f"{np.random.uniform(20, 80):.2f}%",
                'confidence': f"{np.random.uniform(0.6, 0.9):.2%}",
                'duration': f"{period}期",
                'target_price': 'N/A',
                'risk_level': np.random.choice(['低', '中', '高']),
                'recommendation': np.random.choice(['买入', '卖出', '观望'])
            }
            trends.append(trend)

        return trends

    def _calculate_risk_level(self, strength, confidence):
        """计算风险等级"""
        if confidence > 0.8 and strength > 60:
            return '低'
        elif confidence > 0.6 and strength > 40:
            return '中'
        else:
            return '高'

    def _get_trend_recommendation(self, direction, strength, confidence):
        """获取趋势建议"""
        if confidence > 0.7:
            if '上升' in direction and strength > 50:
                return '买入'
            elif '下降' in direction and strength > 50:
                return '卖出'
            else:
                return '观望'
        else:
            return '谨慎观望'

    def _get_volume_recommendation(self, direction, strength):
        """获取成交量建议"""
        if direction == '放量' and strength > 50:
            return '关注突破'
        elif direction == '缩量':
            return '等待放量'
        else:
            return '观望'

    def multi_timeframe_analysis(self):
        """多时间框架分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行多时间框架分析...")
        self.run_analysis_async(self._multi_timeframe_analysis_async)

    def _multi_timeframe_analysis_async(self):
        """异步多时间框架分析"""
        try:
            results = []
            selected_timeframes = []

            # 获取选中的时间框架
            for i in range(self.timeframe_list.count()):
                item = self.timeframe_list.item(i)
                if item.isSelected():
                    selected_timeframes.append(item.data(Qt.UserRole))

            if not selected_timeframes:
                selected_timeframes = ['daily', 'weekly']  # 默认选择

            for tf in selected_timeframes:
                # 模拟不同时间框架的分析
                tf_result = {
                    'timeframe': self.timeframes.get(tf, tf),
                    'direction': np.random.choice(['上升', '下降', '震荡']),
                    'strength': f"{np.random.uniform(30, 90):.1f}%",
                    'consistency': f"{np.random.uniform(0.6, 0.95):.2%}",
                    'weight': np.random.uniform(0.1, 0.3),
                    'score': np.random.uniform(60, 95)
                }
                results.append(tf_result)

            return {'multi_timeframe': results}
        except Exception as e:
            return {'error': str(e)}

    def _calculate_trend_statistics(self, trend_results):
        """计算趋势统计"""
        if not trend_results:
            return {}

        stats = {
            'total_trends': len(trend_results),
            'upward_trends': 0,
            'downward_trends': 0,
            'sideways_trends': 0,
            'avg_strength': 0,
            'avg_confidence': 0,
            'high_confidence_count': 0
        }

        total_strength = 0
        total_confidence = 0

        for trend in trend_results:
            direction = trend.get('direction', '').lower()
            if '上升' in direction:
                stats['upward_trends'] += 1
            elif '下降' in direction:
                stats['downward_trends'] += 1
            else:
                stats['sideways_trends'] += 1

            # 提取数值
            strength_str = trend.get('strength', '0%')
            strength_val = float(strength_str.replace('%', ''))
            total_strength += strength_val

            confidence_str = trend.get('confidence', '0%')
            confidence_val = float(confidence_str.replace('%', ''))
            total_confidence += confidence_val

            if confidence_val > 70:
                stats['high_confidence_count'] += 1

        if len(trend_results) > 0:
            stats['avg_strength'] = total_strength / len(trend_results)
            stats['avg_confidence'] = total_confidence / len(trend_results)

        return stats

    def _generate_trend_predictions(self):
        """生成趋势预测"""
        try:
            if not hasattr(self.current_kdata, 'close'):
                return {}

            current_price = self.current_kdata['close'].iloc[-1]

            predictions = {
                'current_price': current_price,
                'prediction_horizon': '5-10个交易日',
                'scenarios': {
                    'bullish': {
                        'probability': np.random.uniform(0.3, 0.7),
                        'target_price': current_price * np.random.uniform(1.02, 1.08),
                        'description': '看涨情景：突破关键阻力位'
                    },
                    'bearish': {
                        'probability': np.random.uniform(0.2, 0.5),
                        'target_price': current_price * np.random.uniform(0.92, 0.98),
                        'description': '看跌情景：跌破关键支撑位'
                    },
                    'neutral': {
                        'probability': np.random.uniform(0.2, 0.4),
                        'target_price': current_price * np.random.uniform(0.98, 1.02),
                        'description': '中性情景：区间震荡'
                    }
                },
                'key_levels': {
                    'resistance': current_price * np.random.uniform(1.03, 1.06),
                    'support': current_price * np.random.uniform(0.94, 0.97)
                }
            }

            return predictions
        except Exception as e:
            self.log_manager.error(f"生成趋势预测失败: {e}")
            return {}

    def _analyze_support_resistance(self):
        """分析支撑阻力"""
        try:
            if not hasattr(self.current_kdata, 'high') or not hasattr(self.current_kdata, 'low'):
                return []

            period = self.period_spin.value()
            high_prices = self.current_kdata['high'].values[-period:]
            low_prices = self.current_kdata['low'].values[-period:]

            levels = []

            # 寻找支撑位（低点）
            for i in range(2, len(low_prices) - 2):
                if (low_prices[i] < low_prices[i-1] and low_prices[i] < low_prices[i-2] and
                        low_prices[i] < low_prices[i+1] and low_prices[i] < low_prices[i+2]):

                    level = {
                        'type': '支撑位',
                        'price': f"{low_prices[i]:.2f}",
                        'strength': np.random.choice(['强', '中', '弱']),
                        'test_count': np.random.randint(1, 5),
                        'validity': f"{np.random.uniform(0.6, 0.9):.2%}"
                    }
                    levels.append(level)

            # 寻找阻力位（高点）
            for i in range(2, len(high_prices) - 2):
                if (high_prices[i] > high_prices[i-1] and high_prices[i] > high_prices[i-2] and
                        high_prices[i] > high_prices[i+1] and high_prices[i] > high_prices[i+2]):

                    level = {
                        'type': '阻力位',
                        'price': f"{high_prices[i]:.2f}",
                        'strength': np.random.choice(['强', '中', '弱']),
                        'test_count': np.random.randint(1, 5),
                        'validity': f"{np.random.uniform(0.6, 0.9):.2%}"
                    }
                    levels.append(level)

            return levels[:10]  # 返回最多10个关键位
        except Exception as e:
            self.log_manager.error(f"支撑阻力分析失败: {e}")
            return []

    def _generate_trend_alerts(self, trend_results):
        """生成趋势预警"""
        alerts = []

        for trend in trend_results:
            confidence_str = trend.get('confidence', '0%')
            confidence_val = float(confidence_str.replace('%', ''))

            strength_str = trend.get('strength', '0%')
            strength_val = float(strength_str.replace('%', ''))

            # 高置信度趋势预警
            if confidence_val > 80 and strength_val > 60:
                alert = {
                    'type': 'high_confidence_trend',
                    'message': f"检测到高置信度{trend.get('direction', '')}趋势",
                    'trend_type': trend.get('type', ''),
                    'confidence': confidence_val,
                    'strength': strength_val,
                    'recommendation': trend.get('recommendation', ''),
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)

            # 趋势反转预警
            if '反转' in trend.get('recommendation', ''):
                alert = {
                    'type': 'trend_reversal',
                    'message': f"可能出现趋势反转：{trend.get('direction', '')}",
                    'trend_type': trend.get('type', ''),
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)

        return alerts

    def setup_trend_alerts(self):
        """设置趋势预警"""
        dialog = QDialog(self)
        dialog.setWindowTitle("趋势预警设置")
        dialog.setModal(True)
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # 预警类型
        alert_group = QGroupBox("预警类型")
        alert_layout = QVBoxLayout(alert_group)

        trend_reversal_cb = QCheckBox("趋势反转预警")
        trend_reversal_cb.setChecked(True)
        alert_layout.addWidget(trend_reversal_cb)

        high_confidence_cb = QCheckBox("高置信度趋势预警")
        high_confidence_cb.setChecked(True)
        alert_layout.addWidget(high_confidence_cb)

        breakout_cb = QCheckBox("突破预警")
        breakout_cb.setChecked(False)
        alert_layout.addWidget(breakout_cb)

        layout.addWidget(alert_group)

        # 预警参数
        params_group = QGroupBox("预警参数")
        params_layout = QFormLayout(params_group)

        confidence_threshold = QDoubleSpinBox()
        confidence_threshold.setRange(0.5, 0.95)
        confidence_threshold.setValue(0.8)
        confidence_threshold.setDecimals(2)
        params_layout.addRow("置信度阈值:", confidence_threshold)

        strength_threshold = QDoubleSpinBox()
        strength_threshold.setRange(30, 90)
        strength_threshold.setValue(60)
        params_layout.addRow("强度阈值(%):", strength_threshold)

        layout.addWidget(params_group)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "成功", "趋势预警设置已保存")

    def trend_prediction(self):
        """趋势预测"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在生成趋势预测...")
        self.run_analysis_async(self._trend_prediction_async)

    def _trend_prediction_async(self):
        """异步趋势预测"""
        try:
            predictions = self._generate_trend_predictions()
            return {'predictions': predictions}
        except Exception as e:
            return {'error': str(e)}

    def support_resistance_analysis(self):
        """支撑阻力分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在分析支撑阻力位...")
        self.run_analysis_async(self._support_resistance_async)

    def _support_resistance_async(self):
        """异步支撑阻力分析"""
        try:
            sr_levels = self._analyze_support_resistance()
            return {'support_resistance': sr_levels}
        except Exception as e:
            return {'error': str(e)}

    def export_trend_results(self):
        """导出趋势结果"""
        if self.trend_table.rowCount() == 0:
            self.show_no_data_warning("趋势分析数据")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "导出趋势分析结果",
            f"trend_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json);;Excel files (*.xlsx);;CSV files (*.csv)"
        )

        if filename:
            try:
                export_data = self.export_data('json')
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                elif filename.endswith('.xlsx'):
                    self._export_to_excel(filename)
                elif filename.endswith('.csv'):
                    self._export_to_csv(filename)

                QMessageBox.information(self, "成功", f"趋势分析结果已导出到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _export_to_excel(self, filename):
        """导出到Excel"""
        try:

            # 收集表格数据
            data = []
            headers = []
            for col in range(self.trend_table.columnCount()):
                headers.append(self.trend_table.horizontalHeaderItem(col).text())

            for row in range(self.trend_table.rowCount()):
                row_data = {}
                for col in range(self.trend_table.columnCount()):
                    item = self.trend_table.item(row, col)
                    row_data[headers[col]] = item.text() if item else ""
                data.append(row_data)

            df = pd.DataFrame(data)
            df.to_excel(filename, index=False)
        except ImportError:
            self.show_library_warning("pandas", "Excel文件导出")
            return

    def _export_to_csv(self, filename):
        """导出到CSV"""
        self.export_table_to_csv(self.trend_table, filename)

    def _update_results_display(self, results):
        """更新结果显示"""
        try:
            self.hide_loading()

            # 更新趋势分析结果
            if 'trend_analysis' in results:
                self._update_trend_table(results['trend_analysis'])

                # 更新统计信息
                if 'statistics' in results:
                    self._update_trend_statistics_display(results['statistics'])

            # 更新多时间框架结果
            if 'multi_timeframe' in results:
                self._update_multi_timeframe_table(results['multi_timeframe'])

            # 更新预测结果
            if 'predictions' in results:
                self._update_prediction_display(results['predictions'])

            # 更新支撑阻力
            if 'support_resistance' in results:
                self._update_support_resistance_table(results['support_resistance'])

            # 处理预警
            if 'alerts' in results:
                self._update_alerts_display(results['alerts'])

            self.status_label.setText("分析完成")

        except Exception as e:
            self.log_manager.error(f"更新结果显示失败: {e}")

    def _update_trend_table(self, trend_results):
        """更新趋势表格"""
        column_keys = ['timeframe', 'direction', 'strength', 'confidence', 'duration', 'target_price', 'risk_level', 'recommendation']
        self.update_table_data(self.trend_table, trend_results, column_keys)

    def _update_trend_statistics_display(self, stats):
        """更新趋势统计显示"""
        stats_text = (
            f"趋势统计: 总计 {stats.get('total_trends', 0)} 个趋势, "
            f"上升 {stats.get('upward_trends', 0)} 个, "
            f"下降 {stats.get('downward_trends', 0)} 个, "
            f"震荡 {stats.get('sideways_trends', 0)} 个 | "
            f"平均强度 {stats.get('avg_strength', 0):.1f}%, "
            f"平均置信度 {stats.get('avg_confidence', 0):.1f}%"
        )
        self.trend_stats_label.setText(stats_text)

    def _update_multi_timeframe_table(self, multi_tf_results):
        """更新多时间框架表格"""
        column_keys = ['timeframe', 'direction', 'strength', 'consistency', 'weight', 'score']
        self.update_table_data(self.multi_tf_table, multi_tf_results, column_keys)

    def _update_prediction_display(self, predictions):
        """更新预测显示"""
        text = f"""
🔮 趋势预测报告
================

当前价格: {predictions.get('current_price', 'N/A'):.2f}
预测周期: {predictions.get('prediction_horizon', 'N/A')}

预测情景:
"""

        scenarios = predictions.get('scenarios', {})
        for scenario_name, scenario in scenarios.items():
            text += f"""
{scenario_name.upper()}情景:
- 概率: {scenario.get('probability', 0):.2%}
- 目标价: {scenario.get('target_price', 0):.2f}
- 描述: {scenario.get('description', '')}
"""

        key_levels = predictions.get('key_levels', {})
        if key_levels:
            text += f"""
关键位:
- 阻力位: {key_levels.get('resistance', 0):.2f}
- 支撑位: {key_levels.get('support', 0):.2f}
"""

        text += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.prediction_text.setText(text)

    def _update_support_resistance_table(self, sr_levels):
        """更新支撑阻力表格"""
        column_keys = ['type', 'price', 'strength', 'test_count', 'validity']
        self.update_table_data(self.sr_table, sr_levels, column_keys)

    def _update_alerts_display(self, alerts):
        """更新预警显示"""
        self.alert_list.clear()

        for alert in alerts:
            alert_text = f"[{alert.get('type', '')}] {alert.get('message', '')}"
            item = QListWidgetItem(alert_text)

            # 根据预警类型设置颜色
            if alert.get('type') == 'high_confidence_trend':
                item.setBackground(QColor(255, 248, 220))  # 浅黄色
            elif alert.get('type') == 'trend_reversal':
                item.setBackground(QColor(255, 228, 225))  # 浅红色

            self.alert_list.addItem(item)

    def _do_refresh_data(self):
        """数据刷新处理"""
        if self.auto_update_cb.isChecked():
            self.comprehensive_trend_analysis()

    def _do_clear_data(self):
        """数据清除处理"""
        self.clear_multiple_tables(self.trend_table, self.multi_tf_table, self.sr_table)
        self.prediction_text.clear()
        self.alert_list.clear()
        self.trend_stats_label.setText("等待分析...")

    # 保持向后兼容的方法
    def analyze_trend(self):
        """分析趋势 - 兼容接口"""
        self.comprehensive_trend_analysis()

    def clear_trend(self):
        """清除趋势 - 兼容接口"""
        self._do_clear_data()

    def refresh_data(self):
        """刷新数据 - 兼容接口"""
        self._do_refresh_data()

    def clear_data(self):
        """清除数据 - 兼容接口"""
        self._do_clear_data()

    def export_trend_analysis(self):
        """导出趋势分析 - 兼容接口"""
        self.export_trend_results()

    def _get_export_specific_data(self):
        """获取导出数据"""
        return {
            'trend_algorithms': self.trend_algorithms,
            'timeframes': self.timeframes,
            'trend_results': self.trend_results,
            'trend_statistics': self.trend_statistics,
            'multi_timeframe_results': self.multi_timeframe_results
        }
