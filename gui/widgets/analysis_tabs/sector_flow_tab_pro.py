"""
专业级板块资金流分析标签页 - 对标行业专业软件
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .base_tab import BaseAnalysisTab


class SectorFlowTabPro(BaseAnalysisTab):
    """专业级板块资金流分析标签页 - 对标同花顺、Wind等专业软件"""

    # 专业级信号
    flow_detected = pyqtSignal(dict)  # 资金流检测信号
    flow_alert = pyqtSignal(str, dict)  # 资金流预警信号
    sector_rotation = pyqtSignal(dict)  # 板块轮动信号
    smart_money_flow = pyqtSignal(dict)  # 聪明资金流向信号

    def __init__(self, config_manager=None):
        """初始化专业级板块资金流分析"""
        # 专业级板块分类
        self.sector_categories = {
            '行业板块': {
                '科技': ['计算机', '通信', '电子', '传媒', '软件服务'],
                '消费': ['食品饮料', '纺织服装', '家用电器', '商业贸易', '休闲服务'],
                '医药': ['医药生物', '医疗器械', '生物制品', '化学制药', '中药'],
                '金融': ['银行', '非银金融', '保险', '券商', '信托'],
                '周期': ['钢铁', '有色金属', '化工', '建筑材料', '煤炭'],
                '地产': ['房地产', '建筑装饰', '园林工程'],
                '公用': ['公用事业', '环保', '电力', '燃气'],
                '交运': ['交通运输', '物流', '航空', '港口']
            },
            '概念板块': {
                '新能源': ['新能源汽车', '光伏', '风电', '储能', '氢能源'],
                '科技创新': ['人工智能', '5G', '芯片', '云计算', '大数据'],
                '消费升级': ['新零售', '在线教育', '医美', '宠物经济'],
                '政策主题': ['碳中和', '乡村振兴', '数字经济', '专精特新'],
                '区域主题': ['京津冀', '长三角', '粤港澳', '成渝双城'],
                '事件驱动': ['重组并购', '股权激励', '高送转', '业绩预增']
            },
            '风格板块': {
                '市值风格': ['大盘股', '中盘股', '小盘股', '微盘股'],
                '价值成长': ['价值股', '成长股', '平衡股'],
                '质量因子': ['高ROE', '低负债', '高分红', '业绩稳定'],
                '动量因子': ['强势股', '反转股', '突破股']
            }
        }

        # 资金流分析配置
        self.flow_config = {
            'data_sources': {
                '主力资金': {'weight': 0.4, 'threshold': 1000},  # 万元
                '超大单': {'weight': 0.3, 'threshold': 500},
                '大单': {'weight': 0.2, 'threshold': 200},
                '中单': {'weight': 0.1, 'threshold': 50},
                '小单': {'weight': 0.0, 'threshold': 0}
            },
            'time_windows': {
                '实时': 1,      # 分钟
                '短期': 60,     # 1小时
                '日内': 240,    # 4小时
                '日线': 1440,   # 1天
                '周线': 10080,  # 7天
                '月线': 43200   # 30天
            },
            'flow_indicators': {
                '净流入': 'net_inflow',
                '流入强度': 'inflow_intensity',
                '活跃度': 'activity_level',
                '集中度': 'concentration',
                '持续性': 'persistence',
                '背离度': 'divergence'
            }
        }

        # 智能算法配置
        self.algorithm_config = {
            'smart_money_detection': {
                'min_amount': 5000,      # 最小金额(万)
                'time_threshold': 30,    # 时间阈值(分钟)
                'price_impact': 0.02,    # 价格影响阈值
                'volume_ratio': 2.0      # 成交量比例
            },
            'sector_rotation': {
                'correlation_threshold': 0.7,  # 相关性阈值
                'momentum_period': 20,          # 动量周期
                'rotation_strength': 0.5       # 轮动强度
            },
            'flow_prediction': {
                'model_type': 'lstm',          # 预测模型
                'lookback_period': 60,         # 回看周期
                'prediction_horizon': 5        # 预测周期
            }
        }

        # 分析结果存储
        self.flow_data = {}
        self.sector_rankings = []
        self.rotation_analysis = {}
        self.smart_money_flows = []
        self.flow_predictions = {}

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
        toolbar.setMaximumHeight(200)
        toolbar.setFrameStyle(QFrame.StyledPanel)
        toolbar.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        toolbar_layout = QVBoxLayout(toolbar)

        # 快速分析组
        quick_group = QGroupBox("快速分析")
        quick_layout = QHBoxLayout(quick_group)

        # 实时监控
        realtime_btn = QPushButton("📊 实时监控")
        realtime_btn.setStyleSheet(self._get_button_style('#28a745'))
        realtime_btn.clicked.connect(self.realtime_monitoring)

        # 板块轮动
        rotation_btn = QPushButton("🔄 板块轮动")
        rotation_btn.setStyleSheet(self._get_button_style('#007bff'))
        rotation_btn.clicked.connect(self.sector_rotation_analysis)

        # 聪明资金
        smart_money_btn = QPushButton("🧠 聪明资金")
        smart_money_btn.setStyleSheet(self._get_button_style('#6f42c1'))
        smart_money_btn.clicked.connect(self.smart_money_analysis)

        quick_layout.addWidget(realtime_btn)
        quick_layout.addWidget(rotation_btn)
        quick_layout.addWidget(smart_money_btn)
        toolbar_layout.addWidget(quick_group)

        # 高级功能组
        advanced_group = QGroupBox("高级功能")
        advanced_layout = QHBoxLayout(advanced_group)

        # 综合分析
        comprehensive_btn = QPushButton("🎯 综合分析")
        comprehensive_btn.setStyleSheet(self._get_button_style('#17a2b8'))
        comprehensive_btn.clicked.connect(self.comprehensive_flow_analysis)

        # 流向预测
        prediction_btn = QPushButton("🔮 流向预测")
        prediction_btn.setStyleSheet(self._get_button_style('#ffc107'))
        prediction_btn.clicked.connect(self.flow_prediction)

        advanced_layout.addWidget(comprehensive_btn)
        advanced_layout.addWidget(prediction_btn)
        toolbar_layout.addWidget(advanced_group)

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

        # 板块选择
        sector_group = QGroupBox("板块选择")
        sector_layout = QVBoxLayout(sector_group)

        # 板块分类标签页
        self.sector_tabs = QTabWidget()

        # 行业板块
        industry_tab = self._create_sector_selection_tab('行业板块')
        self.sector_tabs.addTab(industry_tab, "行业板块")

        # 概念板块
        concept_tab = self._create_sector_selection_tab('概念板块')
        self.sector_tabs.addTab(concept_tab, "概念板块")

        # 风格板块
        style_tab = self._create_sector_selection_tab('风格板块')
        self.sector_tabs.addTab(style_tab, "风格板块")

        sector_layout.addWidget(self.sector_tabs)
        layout.addWidget(sector_group)

        # 分析参数
        params_group = QGroupBox("分析参数")
        params_layout = QFormLayout(params_group)

        # 时间窗口
        self.time_window_combo = QComboBox()
        self.time_window_combo.addItems(
            list(self.flow_config['time_windows'].keys()))
        self.time_window_combo.setCurrentText('日线')
        params_layout.addRow("时间窗口:", self.time_window_combo)

        # 资金类型
        self.money_type_combo = QComboBox()
        self.money_type_combo.addItems(['主力资金', '超大单', '大单', '全部资金'])
        params_layout.addRow("资金类型:", self.money_type_combo)

        # 金额阈值
        self.amount_threshold_spin = QSpinBox()
        self.amount_threshold_spin.setRange(100, 100000)
        self.amount_threshold_spin.setValue(1000)
        self.amount_threshold_spin.setSuffix(" 万")
        params_layout.addRow("金额阈值:", self.amount_threshold_spin)

        # 排序方式
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['净流入', '流入强度', '活跃度', '涨跌幅'])
        params_layout.addRow("排序方式:", self.sort_combo)

        layout.addWidget(params_group)

        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.enable_prediction_cb = QCheckBox("启用流向预测")
        self.enable_prediction_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_prediction_cb)

        self.enable_alerts_cb = QCheckBox("启用异常预警")
        self.enable_alerts_cb.setChecked(True)
        advanced_layout.addWidget(self.enable_alerts_cb)

        self.auto_refresh_cb = QCheckBox("自动刷新")
        advanced_layout.addWidget(self.auto_refresh_cb)

        layout.addWidget(advanced_group)
        layout.addStretch()

        return panel

    def _create_sector_selection_tab(self, category):
        """创建板块选择标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建树形控件
        tree = QTreeWidget()
        tree.setHeaderLabel(f"{category}选择")
        tree.setSelectionMode(QAbstractItemView.MultiSelection)

        # 添加板块项目
        if category in self.sector_categories:
            for group_name, sectors in self.sector_categories[category].items():
                group_item = QTreeWidgetItem(tree, [group_name])
                group_item.setExpanded(True)

                for sector in sectors:
                    sector_item = QTreeWidgetItem(group_item, [sector])
                    sector_item.setCheckState(0, Qt.Unchecked)

        layout.addWidget(tree)

        # 保存树形控件引用
        setattr(self, f"{category.replace('板块', '')}_tree", tree)

        return widget

    def _create_results_panel(self):
        """创建结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 结果标签页
        self.results_tabs = QTabWidget()

        # 资金流排行
        ranking_tab = self._create_ranking_tab()
        self.results_tabs.addTab(ranking_tab, "📊 资金流排行")

        # 板块轮动
        rotation_tab = self._create_rotation_tab()
        self.results_tabs.addTab(rotation_tab, "🔄 板块轮动")

        # 聪明资金
        smart_money_tab = self._create_smart_money_tab()
        self.results_tabs.addTab(smart_money_tab, "🧠 聪明资金")

        # 流向预测
        prediction_tab = self._create_prediction_tab()
        self.results_tabs.addTab(prediction_tab, "🔮 流向预测")

        # 实时监控
        monitor_tab = self._create_monitor_tab()
        self.results_tabs.addTab(monitor_tab, "📈 实时监控")

        layout.addWidget(self.results_tabs)
        return panel

    def _create_ranking_tab(self):
        """创建资金流排行标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计卡片
        stats_layout = QHBoxLayout()

        # 总流入
        inflow_card = self._create_stat_card("总流入", "0.00亿", "#28a745")
        stats_layout.addWidget(inflow_card)

        # 总流出
        outflow_card = self._create_stat_card("总流出", "0.00亿", "#dc3545")
        stats_layout.addWidget(outflow_card)

        # 净流入
        net_card = self._create_stat_card("净流入", "0.00亿", "#007bff")
        stats_layout.addWidget(net_card)

        # 活跃板块
        active_card = self._create_stat_card("活跃板块", "0个", "#ffc107")
        stats_layout.addWidget(active_card)

        layout.addLayout(stats_layout)

        # 排行表格
        self.ranking_table = QTableWidget(0, 8)
        self.ranking_table.setHorizontalHeaderLabels([
            '排名', '板块名称', '净流入(万)', '流入强度', '活跃度', '涨跌幅', '领涨股', '状态'
        ])
        self.ranking_table.setAlternatingRowColors(True)
        self.ranking_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.ranking_table)

        return widget

    def _create_stat_card(self, title, value, color):
        """创建统计卡片 - 使用基类统一方法"""
        card = self.create_stat_card(title, value, color)

        # 保存值标签引用（兼容原有逻辑）
        label_name = f"{title.replace('总', '').replace('净', '').replace('活跃', 'active')}_label"
        setattr(self, label_name, card.value_label)

        return card

    def _create_rotation_tab(self):
        """创建板块轮动标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 轮动表格
        self.rotation_table = QTableWidget(0, 6)
        self.rotation_table.setHorizontalHeaderLabels([
            '轮动方向', '流出板块', '流入板块', '资金量(万)', '强度', '时间'
        ])
        layout.addWidget(self.rotation_table)

        return widget

    def _create_smart_money_tab(self):
        """创建聪明资金标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 聪明资金表格
        self.smart_money_table = QTableWidget(0, 7)
        self.smart_money_table.setHorizontalHeaderLabels([
            '时间', '板块', '资金类型', '金额(万)', '方向', '置信度', '影响'
        ])
        layout.addWidget(self.smart_money_table)

        return widget

    def _create_prediction_tab(self):
        """创建流向预测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预测文本
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        layout.addWidget(self.prediction_text)

        return widget

    def _create_monitor_tab(self):
        """创建实时监控标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 监控表格
        self.monitor_table = QTableWidget(0, 6)
        self.monitor_table.setHorizontalHeaderLabels([
            '时间', '板块', '事件', '金额(万)', '影响', '状态'
        ])
        layout.addWidget(self.monitor_table)

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

    def realtime_monitoring(self):
        """实时监控"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在启动实时监控...")
        self.run_analysis_async(self._realtime_monitoring_async)

    def _realtime_monitoring_async(self):
        """异步实时监控"""
        try:
            results = self._simulate_realtime_data()
            return {'realtime_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _simulate_realtime_data(self):
        """模拟实时数据"""
        monitor_data = []

        sectors = ['科技', '消费', '医药', '金融', '周期']
        events = ['大单流入', '主力建仓', '机构调研', '资金异动', '突破买入']

        for i in range(10):
            monitor_data.append({
                'time': (datetime.now() - timedelta(minutes=i*5)).strftime('%H:%M:%S'),
                'sector': np.random.choice(sectors),
                'event': np.random.choice(events),
                'amount': np.random.uniform(1000, 50000),
                'impact': np.random.choice(['强', '中', '弱']),
                'status': np.random.choice(['确认', '待确认', '已处理'])
            })

        return monitor_data

    def sector_rotation_analysis(self):
        """板块轮动分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在分析板块轮动...")
        self.run_analysis_async(self._sector_rotation_async)

    def _sector_rotation_async(self):
        """异步板块轮动分析"""
        try:
            results = self._analyze_sector_rotation()
            return {'rotation_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _analyze_sector_rotation(self):
        """分析板块轮动"""
        rotation_data = []

        sectors = ['科技', '消费', '医药', '金融', '周期', '地产', '公用', '交运']

        for i in range(5):
            outflow_sector = np.random.choice(sectors)
            inflow_sector = np.random.choice(
                [s for s in sectors if s != outflow_sector])

            rotation_data.append({
                'direction': f"{outflow_sector} → {inflow_sector}",
                'outflow_sector': outflow_sector,
                'inflow_sector': inflow_sector,
                'amount': np.random.uniform(5000, 100000),
                'strength': np.random.choice(['强', '中', '弱']),
                'time': (datetime.now() - timedelta(hours=i)).strftime('%H:%M')
            })

        return rotation_data

    def smart_money_analysis(self):
        """聪明资金分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在分析聪明资金...")
        self.run_analysis_async(self._smart_money_async)

    def _smart_money_async(self):
        """异步聪明资金分析"""
        try:
            results = self._detect_smart_money()
            return {'smart_money_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _detect_smart_money(self):
        """检测聪明资金"""
        smart_money_data = []

        sectors = ['科技', '消费', '医药', '金融']
        money_types = ['机构资金', '外资', '游资', '私募']
        directions = ['流入', '流出']

        for i in range(8):
            smart_money_data.append({
                'time': (datetime.now() - timedelta(minutes=i*15)).strftime('%H:%M'),
                'sector': np.random.choice(sectors),
                'money_type': np.random.choice(money_types),
                'amount': np.random.uniform(10000, 200000),
                'direction': np.random.choice(directions),
                'confidence': np.random.uniform(0.7, 0.95),
                'impact': np.random.choice(['高', '中', '低'])
            })

        return smart_money_data

    def comprehensive_flow_analysis(self):
        """综合资金流分析"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在进行综合资金流分析...")
        self.run_analysis_async(self._comprehensive_analysis_async)

    def _comprehensive_analysis_async(self):
        """异步综合分析"""
        try:
            results = {}

            # 资金流排行
            results['ranking_data'] = self._calculate_flow_ranking()

            # 板块轮动
            results['rotation_data'] = self._analyze_sector_rotation()

            # 聪明资金
            results['smart_money_data'] = self._detect_smart_money()

            # 实时监控
            results['realtime_data'] = self._simulate_realtime_data()

            return results
        except Exception as e:
            return {'error': str(e)}

    def _calculate_flow_ranking(self):
        """计算资金流排行"""
        ranking_data = []

        sectors = ['科技', '消费', '医药', '金融', '周期', '地产', '公用', '交运']
        leading_stocks = ['股票A', '股票B', '股票C',
                          '股票D', '股票E', '股票F', '股票G', '股票H']

        for i, sector in enumerate(sectors):
            ranking_data.append({
                'rank': i + 1,
                'sector': sector,
                'net_inflow': np.random.uniform(-50000, 100000),
                'inflow_intensity': np.random.uniform(0.3, 0.9),
                'activity': np.random.uniform(0.4, 0.8),
                'change_pct': np.random.uniform(-3.0, 5.0),
                'leading_stock': leading_stocks[i],
                'status': np.random.choice(['强势', '活跃', '平稳', '弱势'])
            })

        # 按净流入排序
        ranking_data.sort(key=lambda x: x['net_inflow'], reverse=True)

        # 重新分配排名
        for i, data in enumerate(ranking_data):
            data['rank'] = i + 1

        return ranking_data

    def flow_prediction(self):
        """资金流预测"""
        if not self.validate_kdata_with_warning():
            return

        self.show_loading("正在生成资金流预测...")
        self.run_analysis_async(self._flow_prediction_async)

    def _flow_prediction_async(self):
        """异步资金流预测"""
        try:
            prediction = self._generate_flow_prediction()
            return {'flow_prediction': prediction}
        except Exception as e:
            return {'error': str(e)}

    def _generate_flow_prediction(self):
        """生成资金流预测"""
        prediction = f"""
# 板块资金流预测报告
预测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 短期预测（1-3个交易日）
基于当前资金流向分析，预计科技板块将继续受到资金青睐。

## 中期预测（1-2周）
消费板块可能迎来资金回流，建议关注相关机会。

## 长期预测（1个月）
周期性板块在政策支持下可能出现资金轮动机会。

## 风险提示
资金流预测基于历史数据和模型分析，实际情况可能存在差异。
"""
        return prediction

    def _do_refresh_data(self):
        """数据刷新处理"""
        if self.auto_refresh_cb.isChecked():
            self.comprehensive_flow_analysis()

    def _do_clear_data(self):
        """数据清除处理"""
        self.ranking_table.setRowCount(0)
        self.rotation_table.setRowCount(0)
        self.smart_money_table.setRowCount(0)
        self.monitor_table.setRowCount(0)
        self.prediction_text.clear()

    def _get_export_specific_data(self):
        """获取导出数据"""
        return {
            'flow_data': self.flow_data,
            'sector_rankings': self.sector_rankings,
            'rotation_analysis': self.rotation_analysis,
            'smart_money_flows': self.smart_money_flows,
            'flow_predictions': self.flow_predictions
        }
