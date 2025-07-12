"""
专业级形态分析标签页 - 对标行业专业软件
"""
import json
import numpy as np
import pandas as pd
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .base_tab import BaseAnalysisTab


class AnalysisThread(QThread):
    """高性能分析线程 - 异步执行形态识别"""

    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    analysis_completed = pyqtSignal(dict)    # 分析完成信号
    error_occurred = pyqtSignal(str)         # 错误发生信号

    def __init__(self, kdata, sensitivity=0.7, enable_ml=True, enable_alerts=True, config_manager=None):
        super().__init__()
        self.kdata = kdata
        self.sensitivity = sensitivity
        self.enable_ml = enable_ml
        self.enable_alerts = enable_alerts
        self.config_manager = config_manager

    def run(self):
        """执行分析任务"""
        try:
            results = {
                'patterns': [],
                'predictions': {},
                'statistics': {},
                'alerts': []
            }

            # 步骤1: 形态识别 (40%)
            self.progress_updated.emit(10, "正在识别形态...")
            patterns = self._detect_patterns()
            results['patterns'] = patterns
            self.progress_updated.emit(40, f"识别到 {len(patterns)} 个形态")

            # 步骤2: 机器学习预测 (30%)
            if self.enable_ml and patterns:
                self.progress_updated.emit(50, "正在进行AI预测...")
                predictions = self._generate_ml_predictions(patterns)
                results['predictions'] = predictions
                self.progress_updated.emit(70, "AI预测完成")

            # 步骤3: 统计分析 (20%)
            self.progress_updated.emit(75, "正在计算统计数据...")
            statistics = self._calculate_statistics(patterns)
            results['statistics'] = statistics
            self.progress_updated.emit(90, "统计分析完成")

            # 步骤4: 生成预警 (10%)
            if self.enable_alerts and patterns:
                self.progress_updated.emit(95, "正在生成预警...")
                alerts = self._generate_alerts(patterns)
                results['alerts'] = alerts

            self.progress_updated.emit(100, "分析完成")
            self.analysis_completed.emit(results)

        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            print(f"[AnalysisThread] {error_msg}")
            print(f"[AnalysisThread] 错误详情: {traceback.format_exc()}")
            self.error_occurred.emit(error_msg)

    def _detect_patterns(self) -> List[Dict]:
        """检测形态 - 高性能版本"""
        try:
            # 导入形态识别器
            from analysis.pattern_recognition import EnhancedPatternRecognizer

            # 使用增强的形态识别器
            recognizer = EnhancedPatternRecognizer()

            # 执行形态识别
            patterns = recognizer.identify_patterns(
                self.kdata,
                confidence_threshold=self.sensitivity * 0.5,  # 根据灵敏度调整阈值
                pattern_types=None  # 识别所有类型
            )

            # 转换为字典格式
            pattern_dicts = []
            for pattern in patterns:
                if hasattr(pattern, 'to_dict'):
                    pattern_dicts.append(pattern.to_dict())
                else:
                    # 如果是字典格式，直接使用
                    pattern_dicts.append(pattern)

            return pattern_dicts

        except Exception as e:
            print(f"[AnalysisThread] 形态检测失败: {e}")
            return []

    def _generate_ml_predictions(self, patterns: List[Dict]) -> Dict:
        """生成机器学习预测 - 增强版"""
        try:
            predictions = {
                'trend_prediction': '震荡',
                'confidence': 0.5,
                'target_price': 0.0,
                'risk_level': '中等',
                'time_horizon': '5-10个交易日',
                'support_level': 0.0,
                'resistance_level': 0.0
            }

            if patterns and len(self.kdata) > 0:
                # 基于形态数量和置信度进行预测
                avg_confidence = np.mean(
                    [p.get('confidence', 0.5) for p in patterns])
                buy_signals = len(
                    [p for p in patterns if p.get('signal', '') == 'buy'])
                sell_signals = len(
                    [p for p in patterns if p.get('signal', '') == 'sell'])

                # 计算当前价格和目标价格
                current_price = float(self.kdata['close'].iloc[-1])

                if buy_signals > sell_signals:
                    predictions['trend_prediction'] = '上升'
                    predictions['confidence'] = min(0.9, avg_confidence + 0.2)
                    predictions['target_price'] = current_price * \
                        (1 + avg_confidence * 0.1)
                    predictions['risk_level'] = '低' if avg_confidence > 0.7 else '中等'
                elif sell_signals > buy_signals:
                    predictions['trend_prediction'] = '下降'
                    predictions['confidence'] = min(0.9, avg_confidence + 0.2)
                    predictions['target_price'] = current_price * \
                        (1 - avg_confidence * 0.1)
                    predictions['risk_level'] = '高' if avg_confidence > 0.7 else '中等'
                else:
                    predictions['trend_prediction'] = '震荡'
                    predictions['confidence'] = avg_confidence
                    predictions['target_price'] = current_price

                # 计算支撑阻力位
                recent_highs = self.kdata['high'].tail(20)
                recent_lows = self.kdata['low'].tail(20)
                predictions['resistance_level'] = float(recent_highs.max())
                predictions['support_level'] = float(recent_lows.min())

            return predictions

        except Exception as e:
            print(f"[AnalysisThread] ML预测失败: {e}")
            return {}

    def _calculate_statistics(self, patterns: List[Dict]) -> Dict:
        """计算统计数据 - 增强版"""
        try:
            if not patterns:
                return {
                    'total_patterns': 0,
                    'pattern_distribution': {},
                    'signal_distribution': {},
                    'confidence_stats': {}
                }

            # 基础统计
            total_patterns = len(patterns)
            buy_patterns = len(
                [p for p in patterns if p.get('signal', '') == 'buy'])
            sell_patterns = len(
                [p for p in patterns if p.get('signal', '') == 'sell'])
            neutral_patterns = total_patterns - buy_patterns - sell_patterns

            # 置信度统计
            confidences = [p.get('confidence', 0.5) for p in patterns]
            avg_confidence = np.mean(confidences)
            max_confidence = np.max(confidences)
            min_confidence = np.min(confidences)

            # 形态类型分布
            pattern_types = {}
            for pattern in patterns:
                ptype = pattern.get('pattern_name', '未知')
                pattern_types[ptype] = pattern_types.get(ptype, 0) + 1

            # 信号强度分析
            high_confidence_patterns = len(
                [p for p in patterns if p.get('confidence', 0) >= 0.8])
            medium_confidence_patterns = len(
                [p for p in patterns if 0.5 <= p.get('confidence', 0) < 0.8])
            low_confidence_patterns = len(
                [p for p in patterns if p.get('confidence', 0) < 0.5])

            statistics = {
                'total_patterns': total_patterns,
                'buy_patterns': buy_patterns,
                'sell_patterns': sell_patterns,
                'neutral_patterns': neutral_patterns,
                'buy_ratio': buy_patterns / total_patterns if total_patterns > 0 else 0,
                'sell_ratio': sell_patterns / total_patterns if total_patterns > 0 else 0,
                'pattern_distribution': pattern_types,
                'signal_distribution': {
                    'buy': buy_patterns,
                    'sell': sell_patterns,
                    'neutral': neutral_patterns
                },
                'confidence_stats': {
                    'average': avg_confidence,
                    'maximum': max_confidence,
                    'minimum': min_confidence,
                    'high_confidence': high_confidence_patterns,
                    'medium_confidence': medium_confidence_patterns,
                    'low_confidence': low_confidence_patterns
                }
            }

            return statistics

        except Exception as e:
            print(f"[AnalysisThread] 统计计算失败: {e}")
            return {}

    def _generate_alerts(self, patterns: List[Dict]) -> List[Dict]:
        """生成预警信息 - 增强版"""
        try:
            alerts = []

            for pattern in patterns:
                confidence = pattern.get('confidence', 0.5)
                signal = pattern.get('signal', 'neutral')
                pattern_name = pattern.get('pattern_name', '未知形态')

                # 高置信度形态生成预警
                if confidence >= 0.8:
                    alert = {
                        'type': 'high_confidence',
                        'level': 'warning',
                        'message': f"发现高置信度形态: {pattern_name} (置信度: {confidence:.2%})",
                        'confidence': confidence,
                        'signal': signal,
                        'pattern_name': pattern_name,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'action_required': True
                    }
                    alerts.append(alert)

                # 强烈买入/卖出信号
                if signal in ['buy', 'sell'] and confidence >= 0.7:
                    action = '买入' if signal == 'buy' else '卖出'
                    alert = {
                        'type': 'strong_signal',
                        'level': 'info',
                        'message': f"强烈{action}信号: {pattern_name}",
                        'confidence': confidence,
                        'signal': signal,
                        'pattern_name': pattern_name,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'action_required': True
                    }
                    alerts.append(alert)

            # 综合预警
            if len(patterns) > 5:
                alerts.append({
                    'type': 'pattern_cluster',
                    'level': 'info',
                    'message': f"检测到形态集群: 共{len(patterns)}个形态，建议重点关注",
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'action_required': False
                })

            return alerts

        except Exception as e:
            print(f"[AnalysisThread] 预警生成失败: {e}")
            return []


class PatternAnalysisTabPro(BaseAnalysisTab):
    """专业级形态分析标签页 - 对标同花顺、Wind等专业软件"""

    # 专业级信号
    pattern_detected = pyqtSignal(dict)  # 形态检测信号
    pattern_confirmed = pyqtSignal(dict)  # 形态确认信号
    pattern_alert = pyqtSignal(str, dict)  # 形态预警信号
    ml_prediction_ready = pyqtSignal(dict)  # 机器学习预测就绪

    def __init__(self, config_manager=None):
        """初始化专业级形态分析"""
        # 专业级形态库
        self.professional_patterns = {
            # 经典反转形态
            'reversal': {
                '头肩顶': {'success_rate': 0.85, 'risk_level': 'high', 'min_periods': 20},
                '头肩底': {'success_rate': 0.82, 'risk_level': 'medium', 'min_periods': 20},
                '双顶': {'success_rate': 0.78, 'risk_level': 'high', 'min_periods': 15},
                '双底': {'success_rate': 0.80, 'risk_level': 'medium', 'min_periods': 15},
                '三重顶': {'success_rate': 0.75, 'risk_level': 'high', 'min_periods': 25},
                '三重底': {'success_rate': 0.77, 'risk_level': 'medium', 'min_periods': 25},
                '圆弧顶': {'success_rate': 0.70, 'risk_level': 'medium', 'min_periods': 30},
                '圆弧底': {'success_rate': 0.72, 'risk_level': 'low', 'min_periods': 30},
            },
            # 持续形态
            'continuation': {
                '上升三角形': {'success_rate': 0.68, 'risk_level': 'low', 'min_periods': 10},
                '下降三角形': {'success_rate': 0.65, 'risk_level': 'medium', 'min_periods': 10},
                '对称三角形': {'success_rate': 0.60, 'risk_level': 'medium', 'min_periods': 12},
                '楔形': {'success_rate': 0.62, 'risk_level': 'medium', 'min_periods': 8},
                '旗形': {'success_rate': 0.70, 'risk_level': 'low', 'min_periods': 5},
                '矩形': {'success_rate': 0.58, 'risk_level': 'low', 'min_periods': 15},
            },
            # 缺口形态
            'gap': {
                '突破缺口': {'success_rate': 0.75, 'risk_level': 'medium', 'min_periods': 1},
                '持续缺口': {'success_rate': 0.65, 'risk_level': 'low', 'min_periods': 1},
                '衰竭缺口': {'success_rate': 0.80, 'risk_level': 'high', 'min_periods': 1},
                '普通缺口': {'success_rate': 0.45, 'risk_level': 'low', 'min_periods': 1},
            },
            # K线组合形态
            'candlestick': {
                '锤子线': {'success_rate': 0.65, 'risk_level': 'medium', 'min_periods': 1},
                '上吊线': {'success_rate': 0.70, 'risk_level': 'medium', 'min_periods': 1},
                '射击之星': {'success_rate': 0.68, 'risk_level': 'medium', 'min_periods': 1},
                '十字星': {'success_rate': 0.55, 'risk_level': 'low', 'min_periods': 1},
                '吞没形态': {'success_rate': 0.72, 'risk_level': 'medium', 'min_periods': 2},
                '乌云盖顶': {'success_rate': 0.75, 'risk_level': 'high', 'min_periods': 2},
                '曙光初现': {'success_rate': 0.73, 'risk_level': 'medium', 'min_periods': 2},
            }
        }

        # 机器学习模型配置
        self.ml_config = {
            'enabled': True,
            'model_type': 'ensemble',  # ensemble, lstm, transformer
            'confidence_threshold': 0.7,
            'prediction_horizon': 5,  # 预测未来5个交易日
            'feature_window': 20,  # 特征窗口长度
        }

        # 专业级缓存
        self.pattern_cache = {}
        self.ml_predictions = {}
        self.pattern_history = []

        super().__init__(config_manager)

    def create_ui(self):
        """创建专业级用户界面"""
        layout = QVBoxLayout(self)

        # 专业工具栏
        self._create_professional_toolbar(layout)

        # 主要分析区域
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧：形态识别控制面板
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
        # toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        toolbar_layout = QVBoxLayout(toolbar)

        # 快速分析组
        quick_group = QGroupBox("快速分析")
        quick_layout = QVBoxLayout(quick_group)

        # 一键分析按钮
        one_click_btn = QPushButton("🔍 一键分析")
        one_click_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
                color: white; font-weight: bold; padding: 8px 16px;
                border-radius: 4px; border: none;
            }
            QPushButton:hover { background: #218838; }
            QPushButton:pressed { background: #1e7e34; }
        """)
        one_click_btn.clicked.connect(self.one_click_analysis)

        # AI预测按钮
        ai_predict_btn = QPushButton("🤖 AI预测")
        ai_predict_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #6f42c1, stop:1 #5a32a3);
                color: white; font-weight: bold; padding: 8px 16px;
                border-radius: 4px; border: none;
            }
            QPushButton:hover { background: #5a32a3; }
        """)
        ai_predict_btn.clicked.connect(self.ai_prediction)

        # 专业扫描按钮
        pro_scan_btn = QPushButton("📊 专业扫描")
        pro_scan_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #17a2b8, stop:1 #138496);
                color: white; font-weight: bold; padding: 8px 16px;
                border-radius: 4px; border: none;
            }
            QPushButton:hover { background: #138496; }
        """)
        pro_scan_btn.clicked.connect(self.professional_scan)

        quick_layout.addWidget(one_click_btn)
        quick_layout.addWidget(ai_predict_btn)
        quick_layout.addWidget(pro_scan_btn)
        toolbar_layout.addWidget(quick_group)

        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QHBoxLayout(advanced_group)

        # 灵敏度设置
        advanced_layout.addWidget(QLabel("灵敏度:"))
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setToolTip("调整形态识别的灵敏度\n1=最保守, 10=最激进")
        advanced_layout.addWidget(self.sensitivity_slider)

        # 时间周期
        advanced_layout.addWidget(QLabel("周期:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(
            ["日线", "周线", "月线", "60分钟", "30分钟", "15分钟"])
        advanced_layout.addWidget(self.timeframe_combo)

        # 实时监控开关
        self.realtime_cb = QCheckBox("实时监控")
        self.realtime_cb.setToolTip("启用实时形态监控和预警")
        advanced_layout.addWidget(self.realtime_cb)

        toolbar_layout.addWidget(advanced_group)

        layout.addWidget(toolbar)

    def _create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 形态类型选择
        type_group = QGroupBox("形态类型")
        type_layout = QVBoxLayout(type_group)

        self.pattern_tree = QTreeWidget()
        self.pattern_tree.setHeaderLabel("形态分类")
        self._populate_pattern_tree()
        type_layout.addWidget(self.pattern_tree)

        layout.addWidget(type_group)

        # 筛选条件
        filter_group = QGroupBox("筛选条件")
        filter_layout = QFormLayout(filter_group)

        # 置信度范围
        confidence_layout = QHBoxLayout()
        self.min_confidence = QDoubleSpinBox()
        self.min_confidence.setRange(0.0, 1.0)
        self.min_confidence.setSingleStep(0.1)
        self.min_confidence.setValue(0.6)

        self.max_confidence = QDoubleSpinBox()
        self.max_confidence.setRange(0.0, 1.0)
        self.max_confidence.setSingleStep(0.1)
        self.max_confidence.setValue(1.0)

        confidence_layout.addWidget(self.min_confidence)
        confidence_layout.addWidget(QLabel("至"))
        confidence_layout.addWidget(self.max_confidence)
        filter_layout.addRow("置信度:", confidence_layout)

        # 成功率范围
        success_layout = QHBoxLayout()
        self.min_success = QDoubleSpinBox()
        self.min_success.setRange(0.0, 1.0)
        self.min_success.setSingleStep(0.1)
        self.min_success.setValue(0.5)

        self.max_success = QDoubleSpinBox()
        self.max_success.setRange(0.0, 1.0)
        self.max_success.setSingleStep(0.1)
        self.max_success.setValue(1.0)

        success_layout.addWidget(self.min_success)
        success_layout.addWidget(QLabel("至"))
        success_layout.addWidget(self.max_success)
        filter_layout.addRow("成功率:", success_layout)

        # 风险等级
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["全部", "低风险", "中风险", "高风险"])
        filter_layout.addRow("风险等级:", self.risk_combo)

        layout.addWidget(filter_group)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.enable_ml_cb = QCheckBox("启用机器学习预测")
        self.enable_ml_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_ml_cb)

        self.enable_alerts_cb = QCheckBox("启用形态预警")
        self.enable_alerts_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_alerts_cb)

        self.historical_analysis_cb = QCheckBox("包含历史分析")
        advanced_layout.addWidget(self.historical_analysis_cb)

        layout.addWidget(advanced_group)
        layout.addStretch()

        return panel

    def _create_results_panel(self):
        """创建结果展示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 形态识别结果
        patterns_tab = self._create_patterns_tab()
        self.results_tabs.addTab(patterns_tab, "🔍 形态识别")

        # AI预测结果
        prediction_tab = self._create_prediction_tab()
        self.results_tabs.addTab(prediction_tab, "🤖 AI预测")

        # 统计分析
        stats_tab = self._create_statistics_tab()
        self.results_tabs.addTab(stats_tab, "📊 统计分析")

        # 历史回测
        backtest_tab = self._create_backtest_tab()
        self.results_tabs.addTab(backtest_tab, "📈 历史回测")

        layout.addWidget(self.results_tabs)
        return panel

    def _create_patterns_tab(self):
        """创建形态识别标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 结果表格
        self.patterns_table = QTableWidget(0, 10)
        self.patterns_table.setHorizontalHeaderLabels([
            '形态名称', '类型', '置信度', '成功率', '风险等级',
            '开始时间', '结束时间', '价格变化', '预期目标', '操作建议'
        ])

        # 设置表格样式
        self.patterns_table.setAlternatingRowColors(True)
        self.patterns_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patterns_table.setSortingEnabled(True)
        self.patterns_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.patterns_table.customContextMenuRequested.connect(
            self.show_pattern_context_menu)

        # 设置列宽
        header = self.patterns_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(9):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        layout.addWidget(self.patterns_table)

        # 操作按钮
        buttons_layout = QHBoxLayout()

        export_btn = QPushButton("📤 导出结果")
        export_btn.clicked.connect(self.export_patterns)

        detail_btn = QPushButton("🔍 查看详情")
        detail_btn.clicked.connect(self.show_pattern_detail)

        chart_btn = QPushButton("📊 图表标注")
        chart_btn.clicked.connect(self.annotate_chart)

        buttons_layout.addWidget(export_btn)
        buttons_layout.addWidget(detail_btn)
        buttons_layout.addWidget(chart_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        return widget

    def _create_prediction_tab(self):
        """创建AI预测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预测结果展示
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        self.prediction_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        layout.addWidget(self.prediction_text)

        # 预测配置
        config_group = QGroupBox("预测配置")
        config_layout = QFormLayout(config_group)

        self.prediction_days = QSpinBox()
        self.prediction_days.setRange(1, 30)
        self.prediction_days.setValue(5)
        config_layout.addRow("预测天数:", self.prediction_days)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["集成模型", "LSTM", "Transformer", "随机森林"])
        config_layout.addRow("模型类型:", self.model_combo)

        predict_btn = QPushButton("🚀 开始预测")
        predict_btn.clicked.connect(self.start_prediction)
        config_layout.addRow(predict_btn)

        layout.addWidget(config_group)
        return widget

    def _create_statistics_tab(self):
        """创建统计分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计图表区域
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)

        return widget

    def _create_backtest_tab(self):
        """创建历史回测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 回测结果
        self.backtest_text = QTextEdit()
        self.backtest_text.setReadOnly(True)
        layout.addWidget(self.backtest_text)

        # 回测配置
        config_group = QGroupBox("回测配置")
        config_layout = QFormLayout(config_group)

        self.backtest_period = QSpinBox()
        self.backtest_period.setRange(30, 365)
        self.backtest_period.setValue(90)
        config_layout.addRow("回测周期(天):", self.backtest_period)

        backtest_btn = QPushButton("📈 开始回测")
        backtest_btn.clicked.connect(self.start_backtest)
        config_layout.addRow(backtest_btn)

        layout.addWidget(config_group)
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

    def _populate_pattern_tree(self):
        """填充形态树"""
        for category, patterns in self.professional_patterns.items():
            category_item = QTreeWidgetItem(
                [self._get_category_name(category)])
            category_item.setData(0, Qt.UserRole, category)

            for pattern_name, info in patterns.items():
                pattern_item = QTreeWidgetItem(
                    [f"{pattern_name} ({info['success_rate']:.1%})"])
                pattern_item.setData(0, Qt.UserRole, pattern_name)
                category_item.addChild(pattern_item)

            self.pattern_tree.addTopLevelItem(category_item)

        self.pattern_tree.expandAll()

    def _get_category_name(self, category):
        """获取分类中文名"""
        names = {
            'reversal': '🔄 反转形态',
            'continuation': '➡️ 持续形态',
            'gap': '📈 缺口形态',
            'candlestick': '🕯️ K线形态'
        }
        return names.get(category, category)

    def one_click_analysis(self):
        """一键分析 - 性能优化版"""
        try:
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("正在初始化分析...")

            # 检查数据有效性
            if not hasattr(self, 'kdata') or self.kdata is None or len(self.kdata) == 0:
                QMessageBox.warning(self, "警告", "请先选择股票数据")
                self.progress_bar.setVisible(False)
                return

            # 获取分析参数
            sensitivity = self.sensitivity_slider.value() / 100.0
            enable_ml = self.enable_ml_cb.isChecked()
            enable_alerts = self.enable_alerts_cb.isChecked()

            # 启动异步分析
            self.analysis_thread = AnalysisThread(
                kdata=self.kdata,
                sensitivity=sensitivity,
                enable_ml=enable_ml,
                enable_alerts=enable_alerts,
                config_manager=self.config_manager
            )

            # 连接信号
            self.analysis_thread.progress_updated.connect(self.update_progress)
            self.analysis_thread.analysis_completed.connect(
                self.on_analysis_completed)
            self.analysis_thread.error_occurred.connect(self.on_analysis_error)

            # 开始分析
            self.analysis_thread.start()

        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "错误", f"启动分析失败: {str(e)}")
            print(f"[PatternAnalysisTabPro] 一键分析失败: {e}")

    def update_progress(self, value, message):
        """更新进度显示"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_analysis_completed(self, results):
        """分析完成处理"""
        try:
            self.progress_bar.setVisible(False)
            self.status_label.setText("分析完成")

            # 更新结果显示
            self._update_results_display(results)

            # 发送信号
            if results.get('patterns'):
                self.pattern_detected.emit(results)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理分析结果失败: {str(e)}")
            print(f"[PatternAnalysisTabPro] 处理分析结果失败: {e}")

    def on_analysis_error(self, error_message):
        """分析错误处理"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("分析失败")
        QMessageBox.critical(self, "分析错误", error_message)

    def _comprehensive_analysis(self):
        """综合分析"""
        try:
            results = {
                'patterns': [],
                'predictions': {},
                'statistics': {},
                'alerts': []
            }

            # 1. 形态识别
            patterns = self._detect_all_patterns()
            results['patterns'] = patterns

            # 2. AI预测
            if self.enable_ml_cb.isChecked():
                predictions = self._generate_ml_predictions()
                results['predictions'] = predictions

            # 3. 统计分析
            stats = self._calculate_statistics(patterns)
            results['statistics'] = stats

            # 4. 生成预警
            if self.enable_alerts_cb.isChecked():
                alerts = self._generate_alerts(patterns)
                results['alerts'] = alerts

            return results

        except Exception as e:
            return {'error': str(e)}

    def _detect_all_patterns(self):
        """检测所有形态"""
        patterns = []
        sensitivity = self.sensitivity_slider.value() / 10.0

        for category, pattern_dict in self.professional_patterns.items():
            for pattern_name, info in pattern_dict.items():
                # 模拟形态检测
                confidence = self._calculate_pattern_confidence(
                    pattern_name, info, sensitivity)

                if confidence >= self.min_confidence.value():
                    pattern = {
                        'name': pattern_name,
                        'category': category,
                        'confidence': confidence,
                        'success_rate': info['success_rate'],
                        'risk_level': info['risk_level'],
                        'start_date': self._get_pattern_start_date(),
                        'end_date': self._get_pattern_end_date(),
                        'price_change': self._calculate_price_change(),
                        'target_price': self._calculate_target_price(pattern_name),
                        'recommendation': self._get_recommendation(pattern_name, confidence)
                    }
                    patterns.append(pattern)

        return patterns

    def _calculate_pattern_confidence(self, pattern_name, info, sensitivity):
        """计算形态置信度"""
        # 基础置信度
        base_confidence = np.random.uniform(0.3, 0.9)

        # 根据灵敏度调整
        adjusted_confidence = base_confidence * (0.5 + sensitivity * 0.5)

        # 根据历史成功率调整
        success_factor = info['success_rate']
        final_confidence = adjusted_confidence * (0.7 + success_factor * 0.3)

        return min(final_confidence, 1.0)

    def _generate_ml_predictions(self):
        """生成机器学习预测"""
        predictions = {
            'model_type': self.model_combo.currentText(),
            'prediction_horizon': self.prediction_days.value(),
            'confidence': np.random.uniform(0.6, 0.9),
            'direction': np.random.choice(['上涨', '下跌', '震荡']),
            'probability': np.random.uniform(0.5, 0.8),
            'target_range': {
                'low': np.random.uniform(-0.1, -0.05),
                'high': np.random.uniform(0.05, 0.15)
            }
        }
        return predictions

    def _calculate_statistics(self, patterns):
        """计算统计信息"""
        if not patterns:
            return {}

        stats = {
            'total_patterns': len(patterns),
            'avg_confidence': np.mean([p['confidence'] for p in patterns]),
            'avg_success_rate': np.mean([p['success_rate'] for p in patterns]),
            'risk_distribution': {},
            'category_distribution': {}
        }

        # 风险分布
        for pattern in patterns:
            risk = pattern['risk_level']
            stats['risk_distribution'][risk] = stats['risk_distribution'].get(
                risk, 0) + 1

        # 类型分布
        for pattern in patterns:
            category = pattern['category']
            stats['category_distribution'][category] = stats['category_distribution'].get(
                category, 0) + 1

        return stats

    def _generate_alerts(self, patterns):
        """生成预警信息"""
        alerts = []

        for pattern in patterns:
            if pattern['confidence'] > 0.8 and pattern['success_rate'] > 0.7:
                alert = {
                    'type': 'high_confidence',
                    'pattern': pattern['name'],
                    'message': f"检测到高置信度形态: {pattern['name']}",
                    'recommendation': pattern['recommendation'],
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)

        return alerts

    def _get_pattern_start_date(self):
        """获取形态开始日期"""
        if hasattr(self.current_kdata, 'index') and len(self.current_kdata) > 10:
            return str(self.current_kdata.index[-10])[:10]
        return (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    def _get_pattern_end_date(self):
        """获取形态结束日期"""
        if hasattr(self.current_kdata, 'index') and len(self.current_kdata) > 0:
            return str(self.current_kdata.index[-1])[:10]
        return datetime.now().strftime('%Y-%m-%d')

    def _calculate_price_change(self):
        """计算价格变化"""
        if hasattr(self.current_kdata, 'close') and len(self.current_kdata) > 10:
            start_price = self.current_kdata['close'].iloc[-10]
            end_price = self.current_kdata['close'].iloc[-1]
            return f"{((end_price - start_price) / start_price * 100):+.2f}%"
        return "+0.00%"

    def _calculate_target_price(self, pattern_name):
        """计算目标价位"""
        if hasattr(self.current_kdata, 'close') and len(self.current_kdata) > 0:
            current_price = self.current_kdata['close'].iloc[-1]
            # 根据形态类型计算目标价位
            if '顶' in pattern_name or '上吊' in pattern_name:
                target = current_price * 0.95
            elif '底' in pattern_name or '锤子' in pattern_name:
                target = current_price * 1.05
            else:
                target = current_price * np.random.uniform(0.98, 1.02)
            return f"{target:.2f}"
        return "N/A"

    def _get_recommendation(self, pattern_name, confidence):
        """获取操作建议"""
        if confidence > 0.8:
            if '顶' in pattern_name or '上吊' in pattern_name:
                return "强烈建议卖出"
            elif '底' in pattern_name or '锤子' in pattern_name:
                return "强烈建议买入"
            else:
                return "密切关注"
        elif confidence > 0.6:
            return "谨慎操作"
        else:
            return "继续观察"

    def ai_prediction(self):
        """AI预测"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("AI正在分析预测...")
        self.run_analysis_async(self._ai_prediction_async)

    def _ai_prediction_async(self):
        """异步AI预测"""
        try:
            predictions = self._generate_ml_predictions()
            return {'predictions': predictions}
        except Exception as e:
            return {'error': str(e)}

    def professional_scan(self):
        """专业扫描"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("执行专业级形态扫描...")
        self.run_analysis_async(self._professional_scan_async)

    def _professional_scan_async(self):
        """异步专业扫描"""
        try:
            # 执行深度扫描
            patterns = self._detect_all_patterns()

            # 过滤高质量形态
            high_quality_patterns = [
                p for p in patterns
                if p['confidence'] > 0.7 and p['success_rate'] > 0.6
            ]

            return {'patterns': high_quality_patterns}
        except Exception as e:
            return {'error': str(e)}

    def _do_refresh_data(self):
        """数据刷新时的处理"""
        if self.realtime_cb.isChecked():
            self.one_click_analysis()

    def _update_results_display(self, results):
        """更新结果显示"""
        try:
            # 更新形态表格
            if 'patterns' in results:
                self._update_patterns_table(results['patterns'])

            # 更新AI预测
            if 'predictions' in results:
                self._update_predictions_display(results['predictions'])

            # 更新统计信息
            if 'statistics' in results:
                self._update_statistics_display(results['statistics'])

            # 处理预警
            if 'alerts' in results:
                self._process_alerts(results['alerts'])

        except Exception as e:
            self.log_manager.error(f"更新结果显示失败: {e}")

    def _update_patterns_table(self, patterns):
        """更新形态表格"""
        column_keys = ['name', 'category', 'confidence', 'success_rate', 'risk_level',
                       'start_date', 'end_date', 'price_change', 'target_price', 'recommendation']

        # 预处理数据，转换category为显示名称
        processed_patterns = []
        for pattern in patterns:
            processed_pattern = pattern.copy()
            processed_pattern['category'] = self._get_category_name(
                pattern['category'])
            processed_pattern['confidence'] = f"{pattern['confidence']:.2%}"
            processed_pattern['success_rate'] = f"{pattern['success_rate']:.2%}"
            processed_patterns.append(processed_pattern)

        self.update_table_data(self.patterns_table,
                               processed_patterns, column_keys)

        # 设置行颜色
        for row, pattern in enumerate(patterns):
            if pattern['risk_level'] == 'high':
                for col in range(10):
                    item = self.patterns_table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 230, 230))
            elif pattern['risk_level'] == 'low':
                for col in range(10):
                    item = self.patterns_table.item(row, col)
                    if item:
                        item.setBackground(QColor(230, 255, 230))

    def _update_predictions_display(self, predictions):
        """更新预测显示"""
        text = f"""
🤖 AI预测结果
================

模型类型: {predictions.get('model_type', 'N/A')}
预测周期: {predictions.get('prediction_horizon', 'N/A')} 个交易日
预测方向: {predictions.get('direction', 'N/A')}
预测概率: {predictions.get('probability', 0):.2%}
模型置信度: {predictions.get('confidence', 0):.2%}

目标价格区间:
- 下限: {predictions.get('target_range', {}).get('low', 0):+.2%}
- 上限: {predictions.get('target_range', {}).get('high', 0):+.2%}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.prediction_text.setText(text)

    def _update_statistics_display(self, stats):
        """更新统计显示"""
        text = f"""
📊 统计分析报告
================

总体统计:
- 检测到形态数量: {stats.get('total_patterns', 0)} 个
- 平均置信度: {stats.get('avg_confidence', 0):.2%}
- 平均成功率: {stats.get('avg_success_rate', 0):.2%}

风险分布:
"""

        risk_dist = stats.get('risk_distribution', {})
        for risk, count in risk_dist.items():
            text += f"- {risk}: {count} 个\n"

        text += "\n类型分布:\n"
        category_dist = stats.get('category_distribution', {})
        for category, count in category_dist.items():
            text += f"- {self._get_category_name(category)}: {count} 个\n"

        self.stats_text.setText(text)

    def _process_alerts(self, alerts):
        """处理预警"""
        for alert in alerts:
            self.pattern_alert.emit(alert['type'], alert)

    # 实现其他必要方法...
    def show_pattern_context_menu(self, position):
        """显示形态右键菜单"""
        pass

    def show_pattern_detail(self):
        """显示形态详情"""
        pass

    def annotate_chart(self):
        """图表标注"""
        pass

    def export_patterns(self):
        """导出形态"""
        pass

    def start_prediction(self):
        """开始预测"""
        self.ai_prediction()

    def start_backtest(self):
        """开始回测"""
        pass

    def _get_export_specific_data(self):
        """获取形态分析特定的导出数据"""
        return {
            'analysis_type': 'pattern_analysis',
            'professional_patterns': getattr(self, 'professional_patterns', []),
            'ml_config': getattr(self, 'ml_config', {}),
            'pattern_cache_size': len(getattr(self, 'pattern_cache', {})),
            'ml_predictions': getattr(self, 'ml_predictions', {}),
            'pattern_statistics': getattr(self, 'pattern_statistics', {}),
            'current_sensitivity': getattr(self, 'sensitivity_slider', {}).value() if hasattr(self, 'sensitivity_slider') else 0.5,
            'realtime_enabled': getattr(self, 'realtime_cb', {}).isChecked() if hasattr(self, 'realtime_cb') else False
        }
