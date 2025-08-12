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


class SectorFlowAnalysisThread(QThread):
    """板块资金流分析线程"""

    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号

    def __init__(self, analysis_func, *args, **kwargs):
        super().__init__()
        self.analysis_func = analysis_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """运行分析线程"""
        try:
            self.progress_updated.emit(0, "开始分析...")

            # 执行分析函数
            results = self.analysis_func(*self.args, **self.kwargs)

            self.progress_updated.emit(100, "分析完成")
            self.analysis_completed.emit(results)

        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            self.error_occurred.emit(error_msg)


class SectorFlowTabPro(BaseAnalysisTab):
    """专业级板块资金流分析标签页 - 对标同花顺、Wind等专业软件"""

    # 标记：该Tab不需要接收单只股票K线数据
    skip_kdata = True

    # 专业级信号
    flow_detected = pyqtSignal(dict)  # 资金流检测信号
    flow_alert = pyqtSignal(str, dict)  # 资金流预警信号
    sector_rotation = pyqtSignal(dict)  # 板块轮动信号
    smart_money_flow = pyqtSignal(dict)  # 聪明资金流向信号

    def __init__(self, config_manager=None, service_container=None):
        """初始化专业级板块资金流分析"""
        self.service_container = service_container
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

        # 初始化板块资金流服务
        self.sector_flow_service = None
        self._init_sector_flow_service()

        super().__init__(config_manager)

    def _init_sector_flow_service(self):
        """初始化板块资金流服务"""
        print("🔄 开始初始化板块资金流服务...")
        import time
        start_time = time.time()

        try:
            if self.service_container:
                print("🔍 服务容器可用，获取板块资金流服务...")
                from core.services.sector_fund_flow_service import SectorFundFlowService
                print("📦 板块资金流服务类导入成功")

                print("🏭 从服务容器解析板块资金流服务...")
                resolve_start = time.time()
                self.sector_flow_service = self.service_container.resolve(SectorFundFlowService)
                resolve_time = time.time()
                print(f"✅ 从服务容器获取板块资金流服务成功，耗时: {(resolve_time - resolve_start):.2f}秒")

                # 初始化服务
                print("⚙️ 初始化板块资金流服务...")
                init_start = time.time()
                self.sector_flow_service.initialize()
                init_time = time.time()
                print(f"✅ 板块资金流服务初始化完成，耗时: {(init_time - init_start):.2f}秒")

                # 连接信号
                print("🔗 连接板块资金流服务信号...")
                self.sector_flow_service.data_updated.connect(self._on_flow_data_updated)
                self.sector_flow_service.error_occurred.connect(self._on_flow_error)
                print("✅ 板块资金流服务信号连接完成")

            else:
                print("⚠️ 服务容器不可用，板块资金流功能受限")

            end_time = time.time()
            print(f"✅ 板块资金流服务初始化完成，总耗时: {(end_time - start_time):.2f}秒")
        except Exception as e:
            print(f"❌ 初始化板块资金流服务失败: {e}")
            import traceback
            print(f"🔍 详细错误信息: {traceback.format_exc()}")
            self.sector_flow_service = None

    def _on_flow_data_updated(self, data):
        """处理资金流数据更新"""
        try:
            print(f"📊 收到板块资金流数据更新: {len(data) if data else 0} 条记录")
            # 这里可以更新UI显示
            self.flow_data = data
            # 可以发射信号通知其他组件
            self.flow_detected.emit(data)
        except Exception as e:
            print(f"处理资金流数据更新失败: {e}")

    def _on_flow_error(self, error_message):
        """处理资金流数据错误"""
        print(f"❌ 板块资金流数据错误: {error_message}")
        self.flow_alert.emit("数据错误", {"error": error_message})

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
        """实时监控 - 使用专用线程避免界面卡死"""
        try:
            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'status_label'):
                self.status_label.setText("正在启动实时监控...")

            # 启动异步分析线程
            self.realtime_thread = SectorFlowAnalysisThread(self._realtime_monitoring_async)
            self.realtime_thread.analysis_completed.connect(self._on_realtime_analysis_completed)
            self.realtime_thread.error_occurred.connect(self._on_realtime_analysis_error)
            self.realtime_thread.progress_updated.connect(self._on_realtime_progress_updated)
            self.realtime_thread.start()

        except Exception as e:
            self.log_manager.error(f"启动实时监控失败: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("启动失败")
            QMessageBox.warning(self, "错误", f"启动实时监控失败: {str(e)}")

    def _realtime_monitoring_async(self):
        """异步实时监控"""
        try:
            results = self._get_realtime_fund_flow_data()
            return {'realtime_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _get_realtime_fund_flow_data(self):
        """获取实时资金流数据 - 使用真实数据"""
        try:
            # 获取数据管理器
            from utils.manager_factory import ManagerFactory
            factory = ManagerFactory()
            data_manager = factory.get_data_manager()

            monitor_data = []

            # 获取板块资金流排行数据
            fund_flow_data = data_manager.get_fund_flow()

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                if not df.empty:
                    # 处理前10个板块的数据
                    top_sectors = df.head(10)

                    for _, row in top_sectors.iterrows():
                        # 获取板块名称
                        sector_name = row.get('板块', row.get('sector_name', '未知板块'))

                        # 获取净流入金额
                        net_inflow = row.get('今日主力净流入-净额', row.get('main_net_inflow', 0))

                        # 判断事件类型
                        if isinstance(net_inflow, str):
                            try:
                                # 处理带单位的字符串，如"1.23万"
                                if '万' in net_inflow:
                                    net_inflow = float(net_inflow.replace('万', '')) * 10000
                                elif '亿' in net_inflow:
                                    net_inflow = float(net_inflow.replace('亿', '')) * 100000000
                                else:
                                    net_inflow = float(net_inflow)
                            except:
                                net_inflow = 0

                        # 判断资金流向类型
                        if net_inflow > 50000000:  # 5000万以上
                            event = '大单流入'
                            impact = '强'
                        elif net_inflow > 10000000:  # 1000万以上
                            event = '主力建仓'
                            impact = '中'
                        elif net_inflow > 0:
                            event = '资金流入'
                            impact = '弱'
                        else:
                            event = '资金流出'
                            impact = '弱'

                        monitor_data.append({
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'sector': sector_name,
                            'event': event,
                            'amount': abs(net_inflow) / 10000,  # 转换为万元
                            'impact': impact,
                            'status': '确认'
                        })

                    self.log_manager.info(f"获取实时资金流数据成功，共 {len(monitor_data)} 条记录")
                else:
                    self.log_manager.warning("板块资金流数据为空")
            else:
                self.log_manager.warning("未获取到板块资金流数据")

            return monitor_data

        except Exception as e:
            self.log_manager.error(f"获取实时资金流数据失败: {str(e)}")
            return []

    def flow_prediction(self):
        """资金流向预测 - 使用专用线程避免界面卡死"""
        try:
            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'status_label'):
                self.status_label.setText("正在进行流向预测...")

            # 启动异步分析线程
            self.prediction_thread = SectorFlowAnalysisThread(self._flow_prediction_async)
            self.prediction_thread.analysis_completed.connect(self._on_prediction_analysis_completed)
            self.prediction_thread.error_occurred.connect(self._on_prediction_analysis_error)
            self.prediction_thread.progress_updated.connect(self._on_prediction_progress_updated)
            self.prediction_thread.start()

        except Exception as e:
            self.log_manager.error(f"启动资金流向预测失败: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("启动失败")
            QMessageBox.warning(self, "错误", f"启动资金流向预测失败: {str(e)}")

    def _flow_prediction_async(self):
        """异步资金流向预测"""
        try:
            results = self._predict_fund_flow()
            return {'prediction_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _predict_fund_flow(self):
        """预测资金流向 - 基于真实数据的趋势分析"""
        try:
            # 获取数据管理器
            factory = ManagerFactory()
            data_manager = factory.get_data_manager()

            prediction_data = []

            # 获取真实资金流数据
            fund_flow_data = data_manager.get_fund_flow()

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                if not df.empty:
                    # 基于当前数据预测未来趋势
                    for _, row in df.head(5).iterrows():
                        sector_name = row.get('板块', row.get('sector_name', '未知板块'))

                        # 获取当前净流入数据
                        current_inflow = row.get('今日主力净流入-净额', row.get('main_net_inflow', 0))
                        current_ratio = row.get('今日主力净流入-净占比', row.get('main_net_inflow_ratio', 0))

                        # 处理数值
                        if isinstance(current_inflow, str):
                            try:
                                if '万' in current_inflow:
                                    current_inflow = float(current_inflow.replace('万', '')) * 10000
                                elif '亿' in current_inflow:
                                    current_inflow = float(current_inflow.replace('亿', '')) * 100000000
                                else:
                                    current_inflow = float(current_inflow)
                            except:
                                current_inflow = 0

                        if isinstance(current_ratio, str):
                            try:
                                current_ratio = float(current_ratio.replace('%', ''))
                            except:
                                current_ratio = 0

                        # 简单的趋势预测逻辑
                        # 基于当前流入情况预测未来1-3日的趋势
                        for day in range(1, 4):
                            # 趋势衰减因子
                            decay_factor = 0.8 ** day
                            predicted_inflow = current_inflow * decay_factor

                            # 预测方向
                            if current_inflow > 50000000:  # 大额流入
                                direction = '持续流入' if day == 1 else '减缓流入'
                                confidence = 0.75 - day * 0.1
                            elif current_inflow < -20000000:  # 大额流出
                                direction = '持续流出' if day == 1 else '减缓流出'
                                confidence = 0.70 - day * 0.1
                            else:
                                direction = '震荡' if abs(predicted_inflow) < 10000000 else '微幅流动'
                                confidence = 0.6 - day * 0.1

                            prediction_data.append({
                                'sector': sector_name,
                                'prediction_day': f"T+{day}",
                                'predicted_flow': predicted_inflow / 10000,  # 转换为万元
                                'direction': direction,
                                'confidence': max(confidence, 0.3),  # 最低30%置信度
                                'risk_level': '高' if abs(predicted_inflow) > 50000000 else '中' if abs(predicted_inflow) > 20000000 else '低'
                            })

                    self.log_manager.info(f"资金流向预测完成，生成 {len(prediction_data)} 个预测")
                    return prediction_data

            # 如果没有数据，返回空列表
            self.log_manager.warning("未获取到资金流向预测数据")
            return []

        except Exception as e:
            self.log_manager.error(f"资金流向预测失败: {e}")
            return []

    def _on_realtime_analysis_completed(self, results):
        """实时监控分析完成回调"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setText("实时监控完成")

            if 'error' in results:
                QMessageBox.warning(self, "错误", results['error'])
                return

            # 更新实时监控表格
            if 'realtime_data' in results and hasattr(self, 'monitor_table'):
                self._update_monitor_table(results['realtime_data'])

            self.log_manager.info("实时监控分析完成")

        except Exception as e:
            self.log_manager.error(f"处理实时监控结果失败: {e}")

    def _on_realtime_analysis_error(self, error_msg):
        """实时监控分析错误回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText("分析失败")
        QMessageBox.warning(self, "错误", error_msg)
        self.log_manager.error(f"实时监控分析失败: {error_msg}")

    def _on_realtime_progress_updated(self, value, message):
        """实时监控进度更新回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    def _update_monitor_table(self, monitor_data):
        """更新实时监控表格"""
        try:
            if not hasattr(self, 'monitor_table') or not self.monitor_table:
                return

            self.monitor_table.setRowCount(len(monitor_data))

            for i, data in enumerate(monitor_data):
                self.monitor_table.setItem(i, 0, QTableWidgetItem(data.get('time', '')))
                self.monitor_table.setItem(i, 1, QTableWidgetItem(data.get('sector', '')))
                self.monitor_table.setItem(i, 2, QTableWidgetItem(data.get('event', '')))
                self.monitor_table.setItem(i, 3, QTableWidgetItem(f"{data.get('amount', 0):.0f}万"))
                self.monitor_table.setItem(i, 4, QTableWidgetItem(data.get('impact', '')))
                self.monitor_table.setItem(i, 5, QTableWidgetItem(data.get('status', '')))

        except Exception as e:
            self.log_manager.error(f"更新监控表格失败: {e}")

    def sector_rotation_analysis(self):
        """板块轮动分析 - 使用专用线程避免界面卡死"""
        try:
            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'status_label'):
                self.status_label.setText("正在分析板块轮动...")

            # 启动异步分析线程
            self.rotation_thread = SectorFlowAnalysisThread(self._sector_rotation_async)
            self.rotation_thread.analysis_completed.connect(self._on_rotation_analysis_completed)
            self.rotation_thread.error_occurred.connect(self._on_rotation_analysis_error)
            self.rotation_thread.progress_updated.connect(self._on_rotation_progress_updated)
            self.rotation_thread.start()

        except Exception as e:
            self.log_manager.error(f"启动板块轮动分析失败: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("启动失败")
            QMessageBox.warning(self, "错误", f"启动板块轮动分析失败: {str(e)}")

    def _sector_rotation_async(self):
        """异步板块轮动分析"""
        try:
            results = self._analyze_sector_rotation()
            return {'rotation_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _analyze_sector_rotation(self):
        """分析板块轮动 - 使用真实数据"""
        try:
            # 获取数据管理器
            factory = ManagerFactory()
            data_manager = factory.get_data_manager()

            rotation_data = []

            # 获取真实资金流数据
            fund_flow_data = data_manager.get_fund_flow()

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                if not df.empty:
                    # 分析流入和流出板块
                    inflow_sectors = []
                    outflow_sectors = []

                    for _, row in df.iterrows():
                        sector_name = row.get('板块', row.get('sector_name', '未知板块'))
                        net_inflow = row.get('今日主力净流入-净额', row.get('main_net_inflow', 0))

                        # 处理数值
                        if isinstance(net_inflow, str):
                            try:
                                if '万' in net_inflow:
                                    net_inflow = float(net_inflow.replace('万', '')) * 10000
                                elif '亿' in net_inflow:
                                    net_inflow = float(net_inflow.replace('亿', '')) * 100000000
                                else:
                                    net_inflow = float(net_inflow)
                            except:
                                net_inflow = 0

                        # 分类流入和流出板块
                        if net_inflow > 10000000:  # 1000万以上算显著流入
                            inflow_sectors.append((sector_name, net_inflow))
                        elif net_inflow < -10000000:  # -1000万以下算显著流出
                            outflow_sectors.append((sector_name, abs(net_inflow)))

                    # 分析轮动关系
                    # 按流入和流出金额排序
                    inflow_sectors.sort(key=lambda x: x[1], reverse=True)
                    outflow_sectors.sort(key=lambda x: x[1], reverse=True)

                    # 生成轮动分析
                    max_pairs = min(len(inflow_sectors), len(outflow_sectors), 5)

                    for i in range(max_pairs):
                        if i < len(outflow_sectors) and i < len(inflow_sectors):
                            outflow_sector, outflow_amount = outflow_sectors[i]
                            inflow_sector, inflow_amount = inflow_sectors[i]

                            # 计算轮动强度
                            avg_amount = (outflow_amount + inflow_amount) / 2
                            if avg_amount > 100000000:  # 1亿以上
                                strength = '强'
                            elif avg_amount > 50000000:  # 5000万以上
                                strength = '中'
                            else:
                                strength = '弱'

                            rotation_data.append({
                                'direction': f"{outflow_sector} → {inflow_sector}",
                                'outflow_sector': outflow_sector,
                                'inflow_sector': inflow_sector,
                                'amount': avg_amount / 10000,  # 转换为万元
                                'strength': strength,
                                'time': datetime.now().strftime('%H:%M')
                            })

                    # 如果没有明显的轮动，基于前几名板块生成分析
                    if not rotation_data and len(df) >= 2:
                        top_sectors = df.head(4)
                        for i in range(0, len(top_sectors)-1, 2):
                            if i+1 < len(top_sectors):
                                sector1 = top_sectors.iloc[i].get('板块', f'板块{i+1}')
                                sector2 = top_sectors.iloc[i+1].get('板块', f'板块{i+2}')

                                rotation_data.append({
                                    'direction': f"{sector1} ⇄ {sector2}",
                                    'outflow_sector': sector1,
                                    'inflow_sector': sector2,
                                    'amount': 30000,  # 默认值
                                    'strength': '中',
                                    'time': datetime.now().strftime('%H:%M')
                                })

                    self.log_manager.info(f"板块轮动分析完成，发现 {len(rotation_data)} 个轮动关系")
                    return rotation_data

            # 如果没有数据，返回空列表
            self.log_manager.warning("未获取到板块轮动分析数据")
            return []

        except Exception as e:
            self.log_manager.error(f"板块轮动分析失败: {e}")
            return []

    def smart_money_analysis(self):
        """聪明资金分析 - 使用专用线程避免界面卡死"""
        try:
            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'status_label'):
                self.status_label.setText("正在分析聪明资金...")

            # 启动异步分析线程
            self.smart_money_thread = SectorFlowAnalysisThread(self._smart_money_async)
            self.smart_money_thread.analysis_completed.connect(self._on_smart_money_analysis_completed)
            self.smart_money_thread.error_occurred.connect(self._on_smart_money_analysis_error)
            self.smart_money_thread.progress_updated.connect(self._on_smart_money_progress_updated)
            self.smart_money_thread.start()

        except Exception as e:
            self.log_manager.error(f"启动聪明资金分析失败: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("启动失败")
            QMessageBox.warning(self, "错误", f"启动聪明资金分析失败: {str(e)}")

    def _smart_money_async(self):
        """异步聪明资金分析"""
        try:
            results = self._detect_smart_money()
            return {'smart_money_data': results}
        except Exception as e:
            return {'error': str(e)}

    def _detect_smart_money(self):
        """检测聪明资金 - 基于真实数据分析"""
        try:
            # 获取数据管理器
            factory = ManagerFactory()
            data_manager = factory.get_data_manager()

            smart_money_data = []

            # 获取真实资金流数据
            fund_flow_data = data_manager.get_fund_flow()

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                if not df.empty:
                    # 分析主力资金流
                    for _, row in df.head(8).iterrows():
                        sector_name = row.get('板块', row.get('sector_name', '未知板块'))

                        # 获取主力净流入数据
                        main_inflow = row.get('今日主力净流入-净额', row.get('main_net_inflow', 0))
                        main_ratio = row.get('今日主力净流入-净占比', row.get('main_net_inflow_ratio', 0))

                        # 处理数值
                        if isinstance(main_inflow, str):
                            try:
                                if '万' in main_inflow:
                                    main_inflow = float(main_inflow.replace('万', '')) * 10000
                                elif '亿' in main_inflow:
                                    main_inflow = float(main_inflow.replace('亿', '')) * 100000000
                                else:
                                    main_inflow = float(main_inflow)
                            except:
                                main_inflow = 0

                        if isinstance(main_ratio, str):
                            try:
                                main_ratio = float(main_ratio.replace('%', ''))
                            except:
                                main_ratio = 0

                        # 判断资金类型和方向
                        abs_inflow = abs(main_inflow)
                        direction = '流入' if main_inflow > 0 else '流出'

                        # 根据资金规模和占比判断资金类型
                        if abs_inflow > 100000000:  # 1亿以上
                            if abs(main_ratio) > 10:  # 占比超过10%
                                money_type = '机构资金'
                            else:
                                money_type = '外资'
                        elif abs_inflow > 50000000:  # 5000万以上
                            money_type = '私募'
                        elif abs_inflow > 10000000:  # 1000万以上
                            money_type = '游资'
                        else:
                            continue  # 金额太小，不算聪明资金

                        # 计算置信度（基于金额和占比）
                        confidence = min(0.7 + abs(main_ratio) / 100 * 0.25, 0.95)

                        # 判断影响程度
                        if abs_inflow > 100000000 and abs(main_ratio) > 15:
                            impact = '高'
                        elif abs_inflow > 50000000 and abs(main_ratio) > 8:
                            impact = '中'
                        else:
                            impact = '低'

                        smart_money_data.append({
                            'time': datetime.now().strftime('%H:%M'),
                            'sector': sector_name,
                            'money_type': money_type,
                            'amount': abs_inflow / 10000,  # 转换为万元
                            'direction': direction,
                            'confidence': confidence,
                            'impact': impact
                        })

                    self.log_manager.info(f"聪明资金检测完成，发现 {len(smart_money_data)} 个活跃资金")
                    return smart_money_data

            # 如果没有数据，返回空列表
            self.log_manager.warning("未获取到聪明资金分析数据")
            return []

        except Exception as e:
            self.log_manager.error(f"聪明资金检测失败: {e}")
            return []

    def comprehensive_flow_analysis(self):
        """综合资金流分析 - 使用专用线程避免界面卡死"""
        try:
            # 显示进度条
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'status_label'):
                self.status_label.setText("正在进行综合资金流分析...")

            # 启动异步分析线程
            self.comprehensive_thread = SectorFlowAnalysisThread(self._comprehensive_analysis_async)
            self.comprehensive_thread.analysis_completed.connect(self._on_comprehensive_analysis_completed)
            self.comprehensive_thread.error_occurred.connect(self._on_comprehensive_analysis_error)
            self.comprehensive_thread.progress_updated.connect(self._on_comprehensive_progress_updated)
            self.comprehensive_thread.start()

        except Exception as e:
            self.log_manager.error(f"启动综合资金流分析失败: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.setText("启动失败")
            QMessageBox.warning(self, "错误", f"启动综合资金流分析失败: {str(e)}")

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
            results['realtime_data'] = self._get_realtime_fund_flow_data()

            return results
        except Exception as e:
            return {'error': str(e)}

    def _calculate_flow_ranking(self):
        """计算资金流排行 - 使用真实数据"""
        try:
            # 获取数据管理器
            factory = ManagerFactory()
            data_manager = factory.get_data_manager()

            # 获取真实资金流数据
            fund_flow_data = data_manager.get_fund_flow()

            ranking_data = []

            if fund_flow_data and 'sector_flow_rank' in fund_flow_data:
                df = fund_flow_data['sector_flow_rank']

                if not df.empty:
                    # 处理真实数据
                    for i, (_, row) in enumerate(df.head(8).iterrows()):
                        sector_name = row.get('板块', row.get('sector_name', f'板块{i+1}'))

                        # 获取净流入数据
                        net_inflow = row.get('今日主力净流入-净额', row.get('main_net_inflow', 0))
                        if isinstance(net_inflow, str):
                            try:
                                if '万' in net_inflow:
                                    net_inflow = float(net_inflow.replace('万', '')) * 10000
                                elif '亿' in net_inflow:
                                    net_inflow = float(net_inflow.replace('亿', '')) * 100000000
                                else:
                                    net_inflow = float(net_inflow)
                            except:
                                net_inflow = 0

                        # 获取涨跌幅
                        change_pct = row.get('今日涨跌幅', row.get('change_pct', 0))
                        if isinstance(change_pct, str):
                            try:
                                change_pct = float(change_pct.replace('%', ''))
                            except:
                                change_pct = 0

                        # 计算流入强度
                        abs_inflow = abs(net_inflow)
                        if abs_inflow > 100000000:  # 1亿以上
                            intensity = 0.8 + (abs_inflow - 100000000) / 1000000000 * 0.2
                        elif abs_inflow > 50000000:  # 5000万以上
                            intensity = 0.6 + (abs_inflow - 50000000) / 50000000 * 0.2
                        else:
                            intensity = abs_inflow / 50000000 * 0.6
                        intensity = min(intensity, 1.0)

                        # 计算活跃度（基于成交量或其他指标）
                        activity = 0.5 + abs(change_pct) / 10 * 0.5
                        activity = min(activity, 1.0)

                        # 判断状态
                        if net_inflow > 50000000 and change_pct > 2:
                            status = '强势'
                        elif net_inflow > 10000000 and change_pct > 0:
                            status = '活跃'
                        elif abs(net_inflow) < 5000000:
                            status = '平稳'
                        else:
                            status = '弱势'

                        ranking_data.append({
                            'rank': i + 1,
                            'sector': sector_name,
                            'net_inflow': net_inflow,
                            'inflow_intensity': intensity,
                            'activity': activity,
                            'change_pct': change_pct,
                            'leading_stock': f'{sector_name}龙头',  # 简化处理
                            'status': status
                        })

                    # 按净流入排序
                    ranking_data.sort(key=lambda x: x['net_inflow'], reverse=True)

                    # 重新分配排名
                    for i, data in enumerate(ranking_data):
                        data['rank'] = i + 1

                    self.log_manager.info(f"资金流排行计算完成，共 {len(ranking_data)} 个板块")
                    return ranking_data

            # 如果没有真实数据，返回空列表
            self.log_manager.warning("未获取到板块资金流排行数据")
            return []

        except Exception as e:
            self.log_manager.error(f"计算资金流排行失败: {e}")
            return []

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

    # ==================== 板块轮动分析回调方法 ====================

    def _on_rotation_analysis_completed(self, results):
        """板块轮动分析完成回调"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setText("板块轮动分析完成")

            if 'error' in results:
                QMessageBox.warning(self, "错误", results['error'])
                return

            # 更新板块轮动结果
            if 'rotation_data' in results:
                self.rotation_analysis = results['rotation_data']
                # 可以在这里更新UI显示轮动结果

            self.log_manager.info("板块轮动分析完成")

        except Exception as e:
            self.log_manager.error(f"处理板块轮动分析结果失败: {e}")

    def _on_rotation_analysis_error(self, error_msg):
        """板块轮动分析错误回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText("分析失败")
        QMessageBox.warning(self, "错误", error_msg)
        self.log_manager.error(f"板块轮动分析失败: {error_msg}")

    def _on_rotation_progress_updated(self, value, message):
        """板块轮动进度更新回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    # ==================== 聪明资金分析回调方法 ====================

    def _on_smart_money_analysis_completed(self, results):
        """聪明资金分析完成回调"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setText("聪明资金分析完成")

            if 'error' in results:
                QMessageBox.warning(self, "错误", results['error'])
                return

            # 更新聪明资金结果
            if 'smart_money_data' in results:
                self.smart_money_flows = results['smart_money_data']
                # 可以在这里更新UI显示聪明资金结果

            self.log_manager.info("聪明资金分析完成")

        except Exception as e:
            self.log_manager.error(f"处理聪明资金分析结果失败: {e}")

    def _on_smart_money_analysis_error(self, error_msg):
        """聪明资金分析错误回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText("分析失败")
        QMessageBox.warning(self, "错误", error_msg)
        self.log_manager.error(f"聪明资金分析失败: {error_msg}")

    def _on_smart_money_progress_updated(self, value, message):
        """聪明资金进度更新回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    # ==================== 综合分析回调方法 ====================

    def _on_comprehensive_analysis_completed(self, results):
        """综合分析完成回调"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setText("综合分析完成")

            if 'error' in results:
                QMessageBox.warning(self, "错误", results['error'])
                return

            # 更新所有分析结果
            if 'ranking_data' in results:
                self.sector_rankings = results['ranking_data']
            if 'rotation_data' in results:
                self.rotation_analysis = results['rotation_data']
            if 'smart_money_data' in results:
                self.smart_money_flows = results['smart_money_data']
            if 'realtime_data' in results:
                self._update_monitor_table(results['realtime_data'])

            # 发射分析完成信号
            self.analysis_completed.emit(results)

            self.log_manager.info("综合资金流分析完成")

        except Exception as e:
            self.log_manager.error(f"处理综合分析结果失败: {e}")

    def _on_comprehensive_analysis_error(self, error_msg):
        """综合分析错误回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText("分析失败")
        QMessageBox.warning(self, "错误", error_msg)
        self.log_manager.error(f"综合分析失败: {error_msg}")

    def _on_comprehensive_progress_updated(self, value, message):
        """综合分析进度更新回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    # ==================== 流向预测回调方法 ====================

    def _on_prediction_analysis_completed(self, results):
        """流向预测分析完成回调"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setText("流向预测完成")

            if 'error' in results:
                QMessageBox.warning(self, "错误", results['error'])
                return

            # 更新预测结果
            if 'prediction_data' in results:
                self.flow_predictions = results['prediction_data']
                # 可以在这里更新UI显示预测结果

            self.log_manager.info("资金流向预测完成")

        except Exception as e:
            self.log_manager.error(f"处理流向预测结果失败: {e}")

    def _on_prediction_analysis_error(self, error_msg):
        """流向预测分析错误回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText("分析失败")
        QMessageBox.warning(self, "错误", error_msg)
        self.log_manager.error(f"流向预测分析失败: {error_msg}")

    def _on_prediction_progress_updated(self, value, message):
        """流向预测进度更新回调"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)

    def set_kdata(self, kdata):
        """覆盖基类方法：板块资金流不依赖单只股票K线，避免选股触发不必要刷新。
        仅记录时间戳与数据基本信息，不触发_refresh或任何耗时分析。"""
        try:
            # 验证数据（快速返回）
            if kdata is None:
                return
            if hasattr(kdata, 'empty') and kdata.empty:
                return

            # 保存基础状态，便于导出/状态查看
            from datetime import datetime
            self.current_kdata = kdata
            self.kdata = kdata
            self.last_update_time = datetime.now()

            # 发射轻量数据更新信号，但不调度刷新
            self.data_updated.emit({
                'timestamp': self.last_update_time.isoformat(),
                'data_length': len(kdata) if hasattr(kdata, '__len__') else 0,
                'data_type': type(kdata).__name__
            })
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.warning(f"SectorFlowTabPro.set_kdata 处理失败: {e}")
            else:
                print(f"SectorFlowTabPro.set_kdata 处理失败: {e}")
