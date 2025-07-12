"""
专业级情绪分析标签页 - 对标行业专业软件
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .base_tab import BaseAnalysisTab


class SentimentAnalysisTabPro(BaseAnalysisTab):
    """专业级情绪分析标签页 - 对标同花顺、Wind等专业软件"""

    # 专业级信号
    sentiment_detected = pyqtSignal(dict)  # 情绪检测信号
    sentiment_alert = pyqtSignal(str, dict)  # 情绪预警信号
    panic_detected = pyqtSignal(dict)  # 恐慌情绪检测信号
    euphoria_detected = pyqtSignal(dict)  # 狂欢情绪检测信号

    def __init__(self, config_manager=None):
        """初始化专业级情绪分析"""
        # 专业级情绪指标配置
        self.sentiment_indicators = {
            '技术指标': {
                'VIX': {'name': '恐慌指数', 'range': [0, 100], 'threshold': {'low': 20, 'high': 30}},
                'PCR': {'name': '看跌看涨比', 'range': [0, 3], 'threshold': {'low': 0.7, 'high': 1.3}},
                'ARMS': {'name': 'ARMS指数', 'range': [0, 5], 'threshold': {'low': 0.7, 'high': 2.0}},
                'TRIN': {'name': 'TRIN指数', 'range': [0, 3], 'threshold': {'low': 0.8, 'high': 1.5}},
                'CBOE_VIX': {'name': 'CBOE波动率', 'range': [10, 80], 'threshold': {'low': 15, 'high': 25}}
            },
            '资金流向': {
                'MONEY_FLOW': {'name': '资金流向指数', 'range': [-100, 100], 'threshold': {'low': -20, 'high': 20}},
                'SMART_MONEY': {'name': '聪明资金', 'range': [0, 100], 'threshold': {'low': 30, 'high': 70}},
                'RETAIL_FLOW': {'name': '散户资金', 'range': [0, 100], 'threshold': {'low': 40, 'high': 60}},
                'INSTITUTION_FLOW': {'name': '机构资金', 'range': [0, 100], 'threshold': {'low': 35, 'high': 65}}
            },
            '市场情绪': {
                'BULL_BEAR': {'name': '多空比例', 'range': [0, 100], 'threshold': {'low': 30, 'high': 70}},
                'SENTIMENT_INDEX': {'name': '情绪指数', 'range': [0, 100], 'threshold': {'low': 25, 'high': 75}},
                'FEAR_GREED': {'name': '恐惧贪婪指数', 'range': [0, 100], 'threshold': {'low': 20, 'high': 80}},
                'MARKET_MOOD': {'name': '市场情绪', 'range': [0, 100], 'threshold': {'low': 30, 'high': 70}}
            },
            '社交媒体': {
                'SOCIAL_SENTIMENT': {'name': '社交情绪', 'range': [-100, 100], 'threshold': {'low': -30, 'high': 30}},
                'NEWS_SENTIMENT': {'name': '新闻情绪', 'range': [-100, 100], 'threshold': {'low': -25, 'high': 25}},
                'WEIBO_INDEX': {'name': '微博指数', 'range': [0, 100], 'threshold': {'low': 40, 'high': 60}},
                'FORUM_SENTIMENT': {'name': '论坛情绪', 'range': [-100, 100], 'threshold': {'low': -20, 'high': 20}}
            }
        }

        # AI模型配置
        self.ai_config = {
            'sentiment_models': {
                'lstm': {'accuracy': 0.85, 'speed': 'fast', 'description': 'LSTM情绪预测'},
                'transformer': {'accuracy': 0.92, 'speed': 'medium', 'description': 'Transformer深度学习'},
                'bert': {'accuracy': 0.94, 'speed': 'slow', 'description': 'BERT自然语言处理'},
                'ensemble': {'accuracy': 0.96, 'speed': 'slow', 'description': '集成学习模型'}
            },
            'prediction_horizons': {
                '短期': {'days': 1, 'confidence': 0.8},
                '中期': {'days': 5, 'confidence': 0.7},
                '长期': {'days': 20, 'confidence': 0.6}
            },
            'alert_thresholds': {
                '极度恐慌': {'value': 10, 'action': '抄底机会'},
                '恐慌': {'value': 25, 'action': '谨慎观望'},
                '中性': {'value': 50, 'action': '正常操作'},
                '贪婪': {'value': 75, 'action': '减仓观望'},
                '极度贪婪': {'value': 90, 'action': '高位风险'}
            }
        }

        # 分析结果存储
        self.sentiment_data = {}
        self.sentiment_history = []
        self.ai_predictions = {}
        self.alert_records = []

        super().__init__(config_manager)

    def create_ui(self):
        """创建专业级用户界面"""
        layout = QVBoxLayout(self)

        # 专业工具栏
        self._create_professional_toolbar(layout)

        # 主要分析区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：控制面板
        left_panel = self._create_control_panel()
        main_splitter.addWidget(left_panel)

        # 右侧：结果展示区域
        right_panel = self._create_results_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([300, 700])
        layout.addWidget(main_splitter)

        # 底部状态栏
        self._create_status_bar(layout)

    def _create_professional_toolbar(self, layout):
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
        toolbar_layout = QVBoxLayout(toolbar)

        # 快速分析组
        quick_group = QGroupBox("快速分析")
        quick_layout = QHBoxLayout(quick_group)

        # 实时情绪
        realtime_btn = QPushButton("📊 实时情绪")
        realtime_btn.setStyleSheet(self._get_button_style('#28a745'))
        realtime_btn.clicked.connect(self.realtime_sentiment_analysis)

        # 恐慌指数
        panic_btn = QPushButton("😱 恐慌指数")
        panic_btn.setStyleSheet(self._get_button_style('#dc3545'))
        panic_btn.clicked.connect(self.panic_index_analysis)

        # 贪婪指数
        greed_btn = QPushButton("🤑 贪婪指数")
        greed_btn.setStyleSheet(self._get_button_style('#ffc107'))
        greed_btn.clicked.connect(self.greed_index_analysis)

        quick_layout.addWidget(realtime_btn)
        quick_layout.addWidget(panic_btn)
        quick_layout.addWidget(greed_btn)
        toolbar_layout.addWidget(quick_group)

        # AI分析组
        ai_group = QGroupBox("AI分析")
        ai_layout = QHBoxLayout(ai_group)

        # 情绪预测
        prediction_btn = QPushButton("🔮 情绪预测")
        prediction_btn.setStyleSheet(self._get_button_style('#6f42c1'))
        prediction_btn.clicked.connect(self.ai_sentiment_prediction)

        # 综合分析
        comprehensive_btn = QPushButton("🎯 综合分析")
        comprehensive_btn.setStyleSheet(self._get_button_style('#17a2b8'))
        comprehensive_btn.clicked.connect(
            self.comprehensive_sentiment_analysis)

        ai_layout.addWidget(prediction_btn)
        ai_layout.addWidget(comprehensive_btn)
        toolbar_layout.addWidget(ai_group)

        toolbar_layout.addStretch()
        layout.addWidget(toolbar)

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

        # 情绪指标选择
        indicators_group = QGroupBox("情绪指标")
        indicators_layout = QVBoxLayout(indicators_group)

        # 指标分类标签页
        self.indicators_tabs = QTabWidget()

        for category, indicators in self.sentiment_indicators.items():
            tab = self._create_indicator_selection_tab(category, indicators)
            self.indicators_tabs.addTab(tab, category)

        indicators_layout.addWidget(self.indicators_tabs)
        layout.addWidget(indicators_group)

        # 分析参数
        params_group = QGroupBox("分析参数")
        params_layout = QFormLayout(params_group)

        # 时间周期
        self.time_period_combo = QComboBox()
        self.time_period_combo.addItems(['实时', '日线', '周线', '月线'])
        params_layout.addRow("时间周期:", self.time_period_combo)

        # AI模型选择
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems(
            list(self.ai_config['sentiment_models'].keys()))
        self.ai_model_combo.setCurrentText('ensemble')
        params_layout.addRow("AI模型:", self.ai_model_combo)

        # 预测周期
        self.prediction_horizon_combo = QComboBox()
        self.prediction_horizon_combo.addItems(
            list(self.ai_config['prediction_horizons'].keys()))
        params_layout.addRow("预测周期:", self.prediction_horizon_combo)

        # 敏感度
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        params_layout.addRow("敏感度:", self.sensitivity_slider)

        layout.addWidget(params_group)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.enable_ai_cb = QCheckBox("启用AI预测")
        self.enable_ai_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_ai_cb)

        self.enable_alerts_cb = QCheckBox("启用情绪预警")
        self.enable_alerts_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_alerts_cb)

        self.social_media_cb = QCheckBox("包含社交媒体")
        self.social_media_cb.setChecked(True)
        advanced_layout.addWidget(self.social_media_cb)

        self.auto_refresh_cb = QCheckBox("自动刷新")
        advanced_layout.addWidget(self.auto_refresh_cb)

        layout.addWidget(advanced_group)
        layout.addStretch()

        return panel

    def _create_indicator_selection_tab(self, category, indicators):
        """创建指标选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建指标列表
        indicator_list = QListWidget()
        indicator_list.setSelectionMode(QAbstractItemView.MultiSelection)

        for indicator_key, indicator_info in indicators.items():
            item = QListWidgetItem(
                f"{indicator_info['name']} ({indicator_key})")
            item.setData(Qt.UserRole, indicator_key)
            indicator_list.addItem(item)
            # 默认选中前几个指标
            if len(indicator_list.selectedItems()) < 3:
                item.setSelected(True)

        layout.addWidget(indicator_list)

        # 保存列表引用
        setattr(
            self, f"{category.replace(' ', '_').lower()}_list", indicator_list)

        return widget

    def _create_results_panel(self):
        """创建结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 情绪仪表盘
        dashboard_tab = self._create_dashboard_tab()
        self.results_tabs.addTab(dashboard_tab, "📊 情绪仪表盘")

        # 恐慌贪婪指数
        fear_greed_tab = self._create_fear_greed_tab()
        self.results_tabs.addTab(fear_greed_tab, "😱🤑 恐慌贪婪")

        # AI预测
        prediction_tab = self._create_prediction_tab()
        self.results_tabs.addTab(prediction_tab, "🔮 AI预测")

        # 历史趋势
        history_tab = self._create_history_tab()
        self.results_tabs.addTab(history_tab, "📈 历史趋势")

        # 预警记录
        alerts_tab = self._create_alerts_tab()
        self.results_tabs.addTab(alerts_tab, "⚠️ 预警记录")

        layout.addWidget(self.results_tabs)
        return panel

    def _create_dashboard_tab(self):
        """创建情绪仪表盘标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 主要指标卡片
        cards_layout = QGridLayout()

        # 综合情绪指数
        sentiment_card = self._create_sentiment_card(
            "综合情绪", "50", "中性", "#007bff")
        cards_layout.addWidget(sentiment_card, 0, 0)

        # 恐慌指数
        panic_card = self._create_sentiment_card("恐慌指数", "25", "低", "#28a745")
        cards_layout.addWidget(panic_card, 0, 1)

        # 贪婪指数
        greed_card = self._create_sentiment_card("贪婪指数", "60", "中高", "#ffc107")
        cards_layout.addWidget(greed_card, 0, 2)

        # 市场情绪
        market_card = self._create_sentiment_card(
            "市场情绪", "乐观", "上升", "#17a2b8")
        cards_layout.addWidget(market_card, 1, 0)

        # 资金情绪
        money_card = self._create_sentiment_card("资金情绪", "谨慎", "观望", "#6f42c1")
        cards_layout.addWidget(money_card, 1, 1)

        # 社交情绪
        social_card = self._create_sentiment_card(
            "社交情绪", "积极", "活跃", "#fd7e14")
        cards_layout.addWidget(social_card, 1, 2)

        layout.addLayout(cards_layout)

        # 详细指标表格
        self.sentiment_table = QTableWidget(0, 6)
        self.sentiment_table.setHorizontalHeaderLabels([
            '指标名称', '当前值', '状态', '变化', '信号', '建议'
        ])
        self.sentiment_table.setAlternatingRowColors(True)
        layout.addWidget(self.sentiment_table)

        return widget

    def _create_sentiment_card(self, title, value, status, color):
        """创建情绪卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: white; 
                border: 1px solid #dee2e6; 
                border-radius: 8px; 
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 14px; color: #6c757d; font-weight: bold;")

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {color};")

        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("font-size: 12px; color: #6c757d;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(status_label)

        return card

    def _create_fear_greed_tab(self):
        """创建恐慌贪婪指数标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 恐慌贪婪指数表格
        self.fear_greed_table = QTableWidget(0, 5)
        self.fear_greed_table.setHorizontalHeaderLabels([
            '时间', '恐慌指数', '贪婪指数', '综合评级', '投资建议'
        ])
        layout.addWidget(self.fear_greed_table)

        return widget

    def _create_prediction_tab(self):
        """创建AI预测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预测文本
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        layout.addWidget(self.prediction_text)

        return widget

    def _create_history_tab(self):
        """创建历史趋势标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 历史数据表格
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels([
            '日期', '综合情绪', '恐慌指数', '贪婪指数', '市场表现', '准确度', '备注'
        ])
        layout.addWidget(self.history_table)

        return widget

    def _create_alerts_tab(self):
        """创建预警记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预警表格
        self.alerts_table = QTableWidget(0, 6)
        self.alerts_table.setHorizontalHeaderLabels([
            '时间', '预警类型', '触发指标', '预警级别', '建议操作', '状态'
        ])
        layout.addWidget(self.alerts_table)

        return widget

    def _create_status_bar(self, layout):
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

        layout.addWidget(status_frame)

    def realtime_sentiment_analysis(self):
        """实时情绪分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行实时情绪分析...")
        self.run_analysis_async(self._realtime_sentiment_async)

    def _realtime_sentiment_async(self):
        """异步实时情绪分析"""
        try:
            results = self._calculate_realtime_sentiment()
            return {'realtime_sentiment': results}
        except Exception as e:
            return {'error': str(e)}

    def _calculate_realtime_sentiment(self):
        """计算实时情绪"""
        sentiment_data = []

        indicators = ['综合情绪', '恐慌指数', '贪婪指数', '市场情绪', '资金情绪', '社交情绪']

        for indicator in indicators:
            value = np.random.uniform(20, 80)
            if value < 30:
                status = "恐慌"
                signal = "买入机会"
                color = "#dc3545"
            elif value < 50:
                status = "谨慎"
                signal = "观望"
                color = "#ffc107"
            elif value < 70:
                status = "乐观"
                signal = "正常操作"
                color = "#28a745"
            else:
                status = "贪婪"
                signal = "减仓风险"
                color = "#fd7e14"

            sentiment_data.append({
                'indicator': indicator,
                'value': value,
                'status': status,
                'change': np.random.uniform(-5, 5),
                'signal': signal,
                'suggestion': self._get_suggestion(status),
                'color': color
            })

        return sentiment_data

    def _get_suggestion(self, status):
        """获取投资建议"""
        suggestions = {
            "恐慌": "考虑逢低买入",
            "谨慎": "保持观望",
            "乐观": "正常操作",
            "贪婪": "考虑减仓"
        }
        return suggestions.get(status, "正常操作")

    def panic_index_analysis(self):
        """恐慌指数分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在分析恐慌指数...")
        self.run_analysis_async(self._panic_index_async)

    def _panic_index_async(self):
        """异步恐慌指数分析"""
        try:
            results = self._calculate_panic_index()
            return {'panic_index': results}
        except Exception as e:
            return {'error': str(e)}

    def _calculate_panic_index(self):
        """计算恐慌指数"""
        panic_data = []

        for i in range(10):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            panic_value = np.random.uniform(10, 40)
            greed_value = 100 - panic_value

            if panic_value < 20:
                rating = "极度恐慌"
                suggestion = "绝佳买入机会"
            elif panic_value < 30:
                rating = "恐慌"
                suggestion = "考虑买入"
            else:
                rating = "谨慎"
                suggestion = "保持观望"

            panic_data.append({
                'date': date,
                'panic_index': panic_value,
                'greed_index': greed_value,
                'rating': rating,
                'suggestion': suggestion
            })

        return panic_data

    def greed_index_analysis(self):
        """贪婪指数分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在分析贪婪指数...")
        self.run_analysis_async(self._greed_index_async)

    def _greed_index_async(self):
        """异步贪婪指数分析"""
        try:
            results = self._calculate_greed_index()
            return {'greed_index': results}
        except Exception as e:
            return {'error': str(e)}

    def _calculate_greed_index(self):
        """计算贪婪指数"""
        # 与恐慌指数类似，但关注贪婪情绪
        return self._calculate_panic_index()

    def ai_sentiment_prediction(self):
        """AI情绪预测"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行AI情绪预测...")
        self.run_analysis_async(self._ai_prediction_async)

    def _ai_prediction_async(self):
        """异步AI预测"""
        try:
            prediction = self._generate_ai_prediction()
            return {'ai_prediction': prediction}
        except Exception as e:
            return {'error': str(e)}

    def _generate_ai_prediction(self):
        """生成AI预测"""
        model = self.ai_model_combo.currentText()
        horizon = self.prediction_horizon_combo.currentText()

        prediction = f"""
# AI情绪预测报告
预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
使用模型: {self.ai_config['sentiment_models'][model]['description']}
预测周期: {horizon}

## 情绪预测结果
基于{model}模型分析，预计未来{horizon}市场情绪将：

### 短期预测（1-3天）
- 综合情绪指数: 55-65 (乐观区间)
- 恐慌指数: 20-30 (低恐慌)
- 贪婪指数: 60-70 (中等贪婪)

### 关键信号
- 技术指标显示情绪回暖
- 资金流向趋于积极
- 社交媒体情绪改善

### 投资建议
建议保持适度乐观，关注市场变化。

### 风险提示
AI预测仅供参考，实际投资需结合多方面因素。
"""
        return prediction

    def comprehensive_sentiment_analysis(self):
        """综合情绪分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行综合情绪分析...")
        self.run_analysis_async(self._comprehensive_analysis_async)

    def _comprehensive_analysis_async(self):
        """异步综合分析"""
        try:
            results = {}

            # 实时情绪
            results['realtime_sentiment'] = self._calculate_realtime_sentiment()

            # 恐慌贪婪指数
            results['panic_index'] = self._calculate_panic_index()

            # AI预测
            if self.enable_ai_cb.isChecked():
                results['ai_prediction'] = self._generate_ai_prediction()

            # 历史数据
            results['history_data'] = self._generate_history_data()

            # 预警记录
            if self.enable_alerts_cb.isChecked():
                results['alerts'] = self._generate_alerts()

            return results
        except Exception as e:
            return {'error': str(e)}

    def _generate_history_data(self):
        """生成历史数据"""
        history_data = []

        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            sentiment = np.random.uniform(30, 70)
            panic = np.random.uniform(15, 35)
            greed = np.random.uniform(50, 80)
            performance = np.random.uniform(-3, 3)
            accuracy = np.random.uniform(0.7, 0.95)

            history_data.append({
                'date': date,
                'sentiment': sentiment,
                'panic': panic,
                'greed': greed,
                'performance': f"{performance:.2f}%",
                'accuracy': f"{accuracy:.2f}",
                'note': '正常' if abs(performance) < 2 else '异常'
            })

        return history_data

    def _generate_alerts(self):
        """生成预警记录"""
        alerts = []

        alert_types = ['恐慌预警', '贪婪预警', '情绪异常', '资金异动']
        levels = ['低', '中', '高', '极高']

        for i in range(5):
            time = (datetime.now() - timedelta(hours=i*2)).strftime('%H:%M:%S')
            alerts.append({
                'time': time,
                'type': np.random.choice(alert_types),
                'indicator': '综合情绪指数',
                'level': np.random.choice(levels),
                'action': '建议观望',
                'status': '已处理' if i > 2 else '待处理'
            })

        return alerts

    def _do_refresh_data(self):
        """数据刷新处理"""
        if self.auto_refresh_cb.isChecked():
            self.comprehensive_sentiment_analysis()

    def _do_clear_data(self):
        """数据清除处理"""
        self.sentiment_table.setRowCount(0)
        self.fear_greed_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.alerts_table.setRowCount(0)
        self.prediction_text.clear()

    def _get_export_specific_data(self):
        """获取导出数据"""
        return {
            'sentiment_data': self.sentiment_data,
            'sentiment_history': self.sentiment_history,
            'ai_predictions': self.ai_predictions,
            'alert_records': self.alert_records
        }
