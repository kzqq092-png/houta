import numpy as np
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtGui import QColor, QPalette, QPainter, QFont
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QBarSeries, QBarSet
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from core.stock_screener import DataManager, StockScreener
from components.stock_screener import StockScreenerWidget
from pylab import mpl
from gui.ui_components import BaseAnalysisPanel
from utils.template_manager import TemplateManager
from utils.config_manager import ConfigManager
from core.logger import LogManager
from gui.widgets.analysis_tabs.base_tab import BaseAnalysisTab

# 使用统一的matplotlib中文字体配置
try:
    from utils.matplotlib_font_config import configure_matplotlib_chinese_font
    configure_matplotlib_chinese_font(font_size=12)
except ImportError:
    # 后备配置
    mpl.rcParams["font.sans-serif"] = ["SimHei"]
    mpl.rcParams["axes.unicode_minus"] = False
    mpl.rcParams["font.size"] = 12

# 设置Qt全局字体
QApplication.setFont(QFont("Microsoft YaHei", 10))


class FlowDataCalculationWorker(QThread):
    """资金流数据计算工作线程"""

    # 信号定义
    industry_flow_calculated = pyqtSignal(dict)  # 行业资金流计算完成
    concept_flow_calculated = pyqtSignal(dict)   # 概念资金流计算完成
    main_force_calculated = pyqtSignal(dict)     # 主力资金分析计算完成
    north_flow_calculated = pyqtSignal(dict)     # 北向资金流计算完成
    calculation_error = pyqtSignal(str)          # 计算错误
    calculation_progress = pyqtSignal(int, str)  # 计算进度

    def __init__(self, calculation_type: str, data: dict, parent=None):
        super().__init__(parent)
        self.calculation_type = calculation_type
        self.data = data
        self._mutex = QMutex()

    def run(self):
        """运行数据计算"""
        try:
            with QMutexLocker(self._mutex):
                if self.calculation_type == "industry_flow":
                    result = self._calculate_industry_flow()
                    self.industry_flow_calculated.emit(result)
                elif self.calculation_type == "concept_flow":
                    result = self._calculate_concept_flow()
                    self.concept_flow_calculated.emit(result)
                elif self.calculation_type == "main_force":
                    result = self._calculate_main_force_analysis()
                    self.main_force_calculated.emit(result)
                elif self.calculation_type == "north_flow":
                    result = self._calculate_north_flow()
                    self.north_flow_calculated.emit(result)

        except Exception as e:
            self.calculation_error.emit(f"{self.calculation_type}计算失败: {str(e)}")

    def _calculate_industry_flow(self) -> dict:
        """计算行业资金流向数据"""
        self.calculation_progress.emit(10, "正在生成行业数据...")

        # 生成模拟数据
        industries = [
            "医药生物", "计算机", "电子", "通信", "传媒",
            "电气设备", "机械设备", "汽车", "食品饮料", "银行"
        ]

        self.calculation_progress.emit(30, "正在计算资金流向...")
        inflows = np.random.uniform(10, 100, 10)
        outflows = np.random.uniform(10, 100, 10)
        net_flows = inflows - outflows
        strengths = np.random.uniform(0, 100, 10)

        self.calculation_progress.emit(60, "正在排序数据...")
        sorted_indices = np.argsort(-net_flows)

        self.calculation_progress.emit(90, "正在生成图表数据...")
        # 获取前5个行业的数据用于图表
        top5_idx = sorted_indices[:5]
        top5_industries = [industries[i] for i in top5_idx]
        top5_net_flows = [net_flows[i] for i in top5_idx]

        self.calculation_progress.emit(100, "计算完成")

        return {
            'table_data': {
                'industries': industries,
                'inflows': inflows,
                'outflows': outflows,
                'net_flows': net_flows,
                'strengths': strengths,
                'sorted_indices': sorted_indices
            },
            'chart_data': {
                'industries': top5_industries,
                'net_flows': top5_net_flows
            }
        }

    def _calculate_concept_flow(self) -> dict:
        """计算概念资金流向数据"""
        self.calculation_progress.emit(10, "正在生成概念数据...")

        concepts = [
            "人工智能", "新能源", "半导体", "5G", "云计算",
            "区块链", "生物医药", "新材料", "智能驾驶", "元宇宙"
        ]

        self.calculation_progress.emit(30, "正在计算资金流向...")
        inflows = np.random.uniform(10, 100, 10)
        outflows = np.random.uniform(10, 100, 10)
        net_flows = inflows - outflows
        strengths = np.random.uniform(0, 100, 10)

        self.calculation_progress.emit(60, "正在排序数据...")
        sorted_indices = np.argsort(-net_flows)

        self.calculation_progress.emit(90, "正在生成图表数据...")
        top5_idx = sorted_indices[:5]
        top5_concepts = [concepts[i] for i in top5_idx]
        top5_net_flows = [net_flows[i] for i in top5_idx]

        self.calculation_progress.emit(100, "计算完成")

        return {
            'table_data': {
                'concepts': concepts,
                'inflows': inflows,
                'outflows': outflows,
                'net_flows': net_flows,
                'strengths': strengths,
                'sorted_indices': sorted_indices
            },
            'chart_data': {
                'concepts': top5_concepts,
                'net_flows': top5_net_flows
            }
        }

    def _calculate_main_force_analysis(self) -> dict:
        """计算主力资金分析数据"""
        self.calculation_progress.emit(20, "正在生成主力资金数据...")

        # 生成模拟数据
        dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq='D')
        main_force_flow = np.random.normal(0, 50, 10)

        self.calculation_progress.emit(50, "正在计算资金规模分布...")
        sizes = ['超大单', '大单', '中单', '小单']
        values = np.random.uniform(20, 40, 4)

        self.calculation_progress.emit(80, "正在计算活跃度数据...")
        activity_data = np.random.uniform(0, 1, (5, 5))
        times = ['09:30', '10:30', '11:30', '14:00', '15:00']
        types = ['买入', '卖出', '净买入', '净卖出', '成交额']

        self.calculation_progress.emit(100, "计算完成")

        return {
            'flow_data': {
                'dates': dates,
                'flow': main_force_flow
            },
            'size_data': {
                'sizes': sizes,
                'values': values
            },
            'activity_data': {
                'data': activity_data,
                'times': times,
                'types': types
            }
        }

    def _calculate_north_flow(self) -> dict:
        """计算北向资金流数据"""
        self.calculation_progress.emit(30, "正在生成北向资金数据...")

        # 生成模拟北向资金数据
        dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq='D')
        inflows = np.random.uniform(50, 200, 10)
        outflows = np.random.uniform(30, 180, 10)

        self.calculation_progress.emit(100, "计算完成")

        return {
            'dates': dates,
            'inflows': inflows,
            'outflows': outflows
        }


class ChartRenderingWorker(QThread):
    """图表渲染工作线程"""

    chart_rendered = pyqtSignal(str, object)  # 图表类型，渲染结果
    rendering_error = pyqtSignal(str)
    rendering_progress = pyqtSignal(int, str)

    def __init__(self, chart_type: str, data: dict, figure: Figure, parent=None):
        super().__init__(parent)
        self.chart_type = chart_type
        self.data = data
        self.figure = figure
        self._mutex = QMutex()

    def run(self):
        """运行图表渲染"""
        try:
            with QMutexLocker(self._mutex):
                if self.chart_type == "industry_chart":
                    self._render_industry_chart()
                elif self.chart_type == "concept_chart":
                    self._render_concept_chart()
                elif self.chart_type == "main_force_chart":
                    self._render_main_force_chart()

                self.chart_rendered.emit(self.chart_type, None)

        except Exception as e:
            self.rendering_error.emit(f"{self.chart_type}渲染失败: {str(e)}")

    def _render_industry_chart(self):
        """渲染行业资金流图表"""
        self.rendering_progress.emit(20, "正在清理图表...")
        self.figure.clear()

        self.rendering_progress.emit(50, "正在绘制图表...")
        ax = self.figure.add_subplot(111)

        chart_data = self.data['chart_data']
        industries = chart_data['industries']
        net_flows = chart_data['net_flows']

        # 绘制水平条形图
        bars = ax.barh(industries, net_flows)

        # 设置条形图颜色
        for i, bar in enumerate(bars):
            bar.set_color('#4CAF50' if net_flows[i] >= 0 else '#F44336')

        # 添加数值标签
        for i, v in enumerate(net_flows):
            ax.text(v + (1 if v >= 0 else -1), i, f'{v:.1f}亿',
                    va='center', ha='left' if v >= 0 else 'right')

        self.rendering_progress.emit(80, "正在添加统计信息...")

        # 添加统计信息
        table_data = self.data['table_data']
        net_flows_full = table_data['net_flows']
        net_max = net_flows_full.max()
        net_min = net_flows_full.min()
        net_mean = net_flows_full.mean()
        net_sum = net_flows_full.sum()

        ax.text(0.5, 1.05, f"净流入  最大: {net_max:.3f}亿  最小: {net_min:.3f}亿  均值: {net_mean:.3f}亿  合计: {net_sum:.3f}亿",
                transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#1976d2')

        ax.set_title('行业资金流向TOP5')
        ax.grid(True, alpha=0.3)

        self.rendering_progress.emit(100, "图表渲染完成")
        self.figure.tight_layout()

    def _render_concept_chart(self):
        """渲染概念资金流图表"""
        self.rendering_progress.emit(20, "正在清理图表...")
        self.figure.clear()

        self.rendering_progress.emit(50, "正在绘制图表...")
        ax = self.figure.add_subplot(111)

        chart_data = self.data['chart_data']
        concepts = chart_data['concepts']
        net_flows = chart_data['net_flows']

        # 绘制水平条形图
        bars = ax.barh(concepts, net_flows)

        # 设置条形图颜色
        for i, bar in enumerate(bars):
            bar.set_color('#4CAF50' if net_flows[i] >= 0 else '#F44336')

        # 添加数值标签
        for i, v in enumerate(net_flows):
            ax.text(v + (1 if v >= 0 else -1), i, f'{v:.1f}亿',
                    va='center', ha='left' if v >= 0 else 'right')

        self.rendering_progress.emit(80, "正在添加统计信息...")

        # 添加统计信息
        table_data = self.data['table_data']
        net_flows_full = table_data['net_flows']
        net_max = net_flows_full.max()
        net_min = net_flows_full.min()
        net_mean = net_flows_full.mean()
        net_sum = net_flows_full.sum()

        ax.text(0.5, 1.05, f"净流入  最大: {net_max:.3f}亿  最小: {net_min:.3f}亿  均值: {net_mean:.3f}亿  合计: {net_sum:.3f}亿",
                transform=ax.transAxes, ha='center', va='bottom', fontsize=11, color='#1976d2')

        ax.set_title('概念资金流向TOP5')
        ax.grid(True, alpha=0.3)

        self.rendering_progress.emit(100, "图表渲染完成")
        self.figure.tight_layout()

    def _render_main_force_chart(self):
        """渲染主力资金分析图表"""
        self.rendering_progress.emit(10, "正在清理图表...")
        self.figure.clear()

        self.rendering_progress.emit(30, "正在创建图表布局...")
        gs = self.figure.add_gridspec(1, 3)
        ax1 = self.figure.add_subplot(gs[0])  # 主力净流入
        ax2 = self.figure.add_subplot(gs[1])  # 资金规模分布
        ax3 = self.figure.add_subplot(gs[2])  # 主力活跃度

        # 1. 主力净流入趋势
        self.rendering_progress.emit(50, "正在绘制主力净流入...")
        flow_data = self.data['flow_data']
        dates = flow_data['dates']
        main_force_flow = flow_data['flow']

        bars = ax1.bar(dates, main_force_flow)
        for i, bar in enumerate(bars):
            bar.set_color('#4CAF50' if main_force_flow[i] >= 0 else '#F44336')

        ax1.set_title('主力净流入趋势')
        ax1.tick_params(axis='x', rotation=45)

        # 添加统计信息
        mf_max = main_force_flow.max()
        mf_min = main_force_flow.min()
        mf_mean = main_force_flow.mean()
        mf_sum = main_force_flow.sum()
        ax1.text(0.5, 1.05, f"最大: {mf_max:.3f}  最小: {mf_min:.3f}  均值: {mf_mean:.3f}  合计: {mf_sum:.3f}",
                 transform=ax1.transAxes, ha='center', va='bottom', fontsize=11, color='#1976d2')

        # 2. 资金规模分布
        self.rendering_progress.emit(70, "正在绘制资金规模分布...")
        size_data = self.data['size_data']
        sizes = size_data['sizes']
        values = size_data['values']
        colors = ['#2196F3', '#4CAF50', '#FFC107', '#FF5722']

        ax2.pie(values, labels=sizes, colors=colors, autopct='%1.1f%%')
        ax2.set_title('资金规模分布')

        # 添加总金额
        total_value = values.sum()
        ax2.text(0.5, 1.08, f"总金额: {total_value:.3f}", transform=ax2.transAxes,
                 ha='center', va='bottom', fontsize=11, color='#2196F3')

        # 3. 主力活跃度热力图
        self.rendering_progress.emit(90, "正在绘制活跃度热力图...")
        activity_data = self.data['activity_data']
        activity_matrix = activity_data['data']
        times = activity_data['times']
        types = activity_data['types']

        sns.heatmap(activity_matrix, annot=True, fmt='.2f', cmap='RdYlGn',
                    xticklabels=times, yticklabels=types, ax=ax3)
        ax3.set_title('主力活跃度分析')

        # 添加均值
        act_mean = activity_matrix.mean()
        ax3.text(0.5, 1.05, f"均值: {act_mean:.3f}", transform=ax3.transAxes,
                 ha='center', va='bottom', fontsize=11, color='#f57c00')

        self.rendering_progress.emit(100, "图表渲染完成")
        self.figure.tight_layout()


class DataUpdateThread(QThread):
    """数据更新线程"""
    data_updated = pyqtSignal(dict)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self._running = True

    def run(self):
        while self._running:
            try:
                data = self._fetch_market_data()
                # 自动补全所有DataFrame中的code字段
                for k, v in data.items():
                    if isinstance(v, pd.DataFrame) and 'code' not in v.columns and hasattr(self.data_manager, 'current_stock'):
                        v = v.copy()
                        v['code'] = getattr(
                            self.data_manager, 'current_stock', None)
                        data[k] = v
                self.data_updated.emit(data)
            except Exception as e:
                logging.error(f"数据更新错误: {e}")
            self.msleep(300000)  # 休眠5分钟

    def _fetch_market_data(self):
        """获取市场数据"""
        return self.data_manager.get_fund_flow()

    def stop(self):
        """停止线程"""
        self._running = False


class FundFlowWidget(BaseAnalysisTab):
    """资金流向分析组件，继承统一分析面板基类"""

    def __init__(self, parent=None, data_manager=None, log_manager=None, chart_widget=None):
        super().__init__(parent, log_manager=log_manager)
        self.data_manager = data_manager
        self.chart_widget = chart_widget
        self._data_cache = {}
        self._cache_time = {}
        self._custom_indicators = {}
        self._alerts = {}
        self.template_manager = TemplateManager(
            template_dir="templates/fund_flow")
        self.main_layout = QVBoxLayout(self)

        # 异步处理相关属性
        self._calculation_worker = None
        self._rendering_worker = None
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._update_mutex = QMutex()

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建资金流向概览卡片
        self.create_overview_cards(self.main_layout)

        # 创建北向资金流向图表
        self.create_north_flow_chart(self.main_layout)

        # 创建行业资金流向表格和图表
        self.create_industry_flow_section(self.main_layout)

        # 创建概念资金流向表格和图表
        self.create_concept_flow_section(self.main_layout)

        # 创建主力资金分析
        self.create_main_force_analysis(self.main_layout)

        # 创建控制按钮
        self.create_control_buttons(self.main_layout)

        # 增加资金流参数输入
        self.inflow_threshold = QDoubleSpinBox()
        self.inflow_threshold.setRange(0, 1e8)
        self.inflow_threshold.setValue(1e6)
        self.add_param_widget("流入阈值", self.inflow_threshold)

        self.outflow_threshold = QDoubleSpinBox()
        self.outflow_threshold.setRange(0, 1e8)
        self.outflow_threshold.setValue(1e6)
        self.add_param_widget("流出阈值", self.outflow_threshold)

        # 主力净流入阈值
        self.main_inflow_threshold = QDoubleSpinBox()
        self.main_inflow_threshold.setRange(-1e8, 1e8)
        self.main_inflow_threshold.setValue(1000000)
        self.add_param_widget("主力净流入阈值", self.main_inflow_threshold)
        # 统计周期
        self.period = QSpinBox()
        self.period.setRange(1, 120)
        self.period.setValue(5)
        self.add_param_widget("统计周期", self.period)

        # 模板管理按钮
        self.template_button = QPushButton("模板管理")
        self.template_button.clicked.connect(self.show_template_manager_dialog)
        self.main_layout.addWidget(self.template_button)

        # 使用统一的数据更新线程
        if self.data_manager:
            self.update_thread = self.create_data_update_thread(
                data_fetcher=self._fetch_fund_flow_data,
                update_interval=300,  # 5分钟更新间隔
                max_retries=3,
                retry_interval=5
            )
            self.update_thread.start()

    def _fetch_fund_flow_data(self) -> dict:
        """获取资金流数据 - 使用真实数据源"""
        try:
            # 确保数据管理器存在
            if not self.data_manager:
                self.log_manager.warning("数据管理器未初始化，无法获取资金流数据")
                return self._get_empty_fund_flow_data()

            # 获取真实资金流数据
            data = self.data_manager.get_fund_flow()

            # 验证数据结构
            if not isinstance(data, dict):
                self.log_manager.warning("资金流数据格式不正确")
                return self._get_empty_fund_flow_data()

            # 数据预处理和格式化
            processed_data = {}

            # 处理板块资金流排行数据
            if 'sector_flow_rank' in data and not data['sector_flow_rank'].empty:
                sector_df = data['sector_flow_rank']
                # 标准化列名
                if '板块' in sector_df.columns:
                    sector_df = sector_df.rename(columns={'板块': 'industry'})
                if '今日主力净流入-净额' in sector_df.columns:
                    sector_df = sector_df.rename(columns={'今日主力净流入-净额': 'net_inflow'})
                elif '主力净流入-净额' in sector_df.columns:
                    sector_df = sector_df.rename(columns={'主力净流入-净额': 'net_inflow'})

                processed_data['industry_flow'] = sector_df
                self.log_manager.info(f"板块资金流数据获取成功，共 {len(sector_df)} 条记录")
            else:
                processed_data['industry_flow'] = pd.DataFrame()

            # 处理大盘资金流数据
            if 'market_fund_flow' in data and not data['market_fund_flow'].empty:
                market_df = data['market_fund_flow']
                processed_data['north_flow'] = market_df
                self.log_manager.info(f"大盘资金流数据获取成功，共 {len(market_df)} 条记录")
            else:
                processed_data['north_flow'] = pd.DataFrame()

            # 处理主力资金流数据
            if 'main_fund_flow' in data and not data['main_fund_flow'].empty:
                main_df = data['main_fund_flow']
                processed_data['main_force'] = main_df
                self.log_manager.info(f"主力资金流数据获取成功，共 {len(main_df)} 条记录")
            else:
                processed_data['main_force'] = pd.DataFrame()

            # 自动补全所有DataFrame中的code字段
            for k, v in processed_data.items():
                if isinstance(v, pd.DataFrame) and 'code' not in v.columns and hasattr(self.data_manager, 'current_stock'):
                    v = v.copy()
                    v['code'] = getattr(self.data_manager, 'current_stock', None)
                    processed_data[k] = v

            self.log_manager.info("资金流数据获取和处理完成")
            return processed_data

        except Exception as e:
            self.log_manager.error(f"获取资金流数据失败: {str(e)}")
            return self._get_empty_fund_flow_data()

    def _get_empty_fund_flow_data(self) -> dict:
        """获取空的资金流数据结构"""
        return {
            'north_flow': pd.DataFrame(),
            'industry_flow': pd.DataFrame(),
            'main_force': pd.DataFrame()
        }

    def create_control_buttons(self, layout):
        """创建控制按钮 - 使用基类统一方法"""
        # 使用基类的统一控制按钮布局创建方法
        control_layout = self.create_control_buttons_layout(
            include_export=True,
            include_alert=True,
            custom_buttons=None
        )
        layout.addLayout(control_layout)

    def create_overview_cards(self, layout):
        """创建资金流向概览卡片 - 使用基类统一方法"""
        # 定义概览指标数据
        indicators_data = [
            ("今日净流入", "+28.5亿", "#4CAF50", "↑"),
            ("北向资金", "-12.3亿", "#F44336", "↓"),
            ("融资余额", "9856.7亿", "#2196F3", "→"),
            ("融券余额", "123.4亿", "#4CAF50", "↑"),
            ("大单成交额", "456.7亿", "#4CAF50", "↑"),
            ("成交活跃度", "85%", "#4CAF50", "↑")
        ]

        # 使用基类的统一卡片布局创建方法
        cards_layout = self.create_cards_layout(indicators_data, columns=3)
        layout.addLayout(cards_layout)

    def create_north_flow_chart(self, layout):
        """创建北向资金流向图表"""
        group = QFrame()
        group.setFrameStyle(QFrame.Box | QFrame.Raised)
        group.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        group_layout = QVBoxLayout(group)

        title = QLabel("北向资金流向")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        group_layout.addWidget(title)

        self.north_chart = QChart()
        self.north_chart.setTitle("北向资金流向趋势")
        self.north_chart.setAnimationOptions(QChart.SeriesAnimations)

        self.north_chart_view = QChartView(self.north_chart)
        self.north_chart_view.setRenderHint(QPainter.Antialiasing)
        group_layout.addWidget(self.north_chart_view)

        if layout is not None:
            layout.addWidget(group)

    def create_industry_flow_section(self, layout):
        """创建行业资金流向区域"""
        group = QFrame()
        group.setFrameStyle(QFrame.Box | QFrame.Raised)
        group.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        group_layout = QVBoxLayout(group)

        # 标题
        title = QLabel("行业资金流向")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        group_layout.addWidget(title)

        # 创建表格和图表的水平布局
        content_layout = QHBoxLayout()

        # 表格部分
        self.industry_table = QTableWidget()
        self.industry_table.setColumnCount(5)
        self.industry_table.setRowCount(10)
        self.industry_table.setHorizontalHeaderLabels(
            ["行业", "净流入(亿)", "流入(亿)", "流出(亿)", "强度"])
        self.industry_table.setStyleSheet("""
            QTableWidget {
                background-color: #f5f5f5;
                alternate-background-color: #e9e9e9;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        content_layout.addWidget(self.industry_table)

        # 图表部分
        self.industry_figure = Figure(figsize=(6, 4))
        self.industry_canvas = FigureCanvas(self.industry_figure)
        content_layout.addWidget(self.industry_canvas)

        group_layout.addLayout(content_layout)
        if layout is not None:
            layout.addWidget(group)

    def create_concept_flow_section(self, layout):
        """创建概念资金流向区域"""
        group = QFrame()
        group.setFrameStyle(QFrame.Box | QFrame.Raised)
        group.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        group_layout = QVBoxLayout(group)

        # 标题
        title = QLabel("概念资金流向")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        group_layout.addWidget(title)

        # 创建表格和图表的水平布局
        content_layout = QHBoxLayout()

        # 表格部分
        self.concept_table = QTableWidget()
        self.concept_table.setColumnCount(5)
        self.concept_table.setRowCount(10)
        self.concept_table.setHorizontalHeaderLabels(
            ["概念", "净流入(亿)", "流入(亿)", "流出(亿)", "强度"])
        self.concept_table.setStyleSheet("""
            QTableWidget {
                background-color: #f5f5f5;
                alternate-background-color: #e9e9e9;
            }
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        content_layout.addWidget(self.concept_table)

        # 图表部分
        self.concept_figure = Figure(figsize=(6, 4))
        self.concept_canvas = FigureCanvas(self.concept_figure)
        content_layout.addWidget(self.concept_canvas)

        group_layout.addLayout(content_layout)
        if layout is not None:
            layout.addWidget(group)

    def create_main_force_analysis(self, layout):
        """创建主力资金分析区域"""
        group = QFrame()
        group.setFrameStyle(QFrame.Box | QFrame.Raised)
        group.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        group_layout = QVBoxLayout(group)

        # 标题
        title = QLabel("主力资金分析")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        group_layout.addWidget(title)

        # 创建主力资金分析图表
        self.main_force_figure = Figure(figsize=(10, 4))
        self.main_force_canvas = FigureCanvas(self.main_force_figure)
        group_layout.addWidget(self.main_force_canvas)

        layout.addWidget(group)

    def _get_cached_data(self, key, max_age=300):
        """获取缓存数据"""
        if key in self._data_cache:
            if time.time() - self._cache_time[key] < max_age:
                return self._data_cache[key]
        return None

    def add_custom_indicator(self, name, calculator):
        """添加自定义指标"""
        self._custom_indicators[name] = calculator
        self._refresh_indicators()

    def set_alert(self, indicator, threshold, callback):
        """设置指标预警"""
        self._alerts[indicator] = {
            'threshold': threshold,
            'callback': callback
        }

    def _run_analysis_async(self, button, analysis_func, *args, **kwargs):
        original_text = button.text()
        button.setText("取消")
        button._interrupted = False

        def on_cancel():
            button._interrupted = True
            button.setText(original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self._run_analysis_async(
                button, analysis_func, *args, **kwargs))

        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(on_cancel)

        def task():
            try:
                if not getattr(button, '_interrupted', False):
                    result = analysis_func(*args, **kwargs)
                    return result
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"分析异常: {str(e)}")
                return None
            finally:
                QTimer.singleShot(0, lambda: on_done(None))

        def on_done(future):
            button.setText(original_text)
            button.setEnabled(True)
            # 重新绑定分析逻辑
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self._run_analysis_async(
                button, analysis_func, *args, **kwargs))
        if not hasattr(self, '_thread_pool'):
            self._thread_pool = ThreadPoolExecutor(max_workers=2)
        future = self._thread_pool.submit(task)
        # 只需在finally中恢复，无需重复回调

    def analyze_fund_flow(self):
        self._run_analysis_async(
            self.fund_flow_btn, self._analyze_fund_flow_impl)

    def export_data(self):
        self._run_analysis_async(self.export_btn, self._export_data_impl)

    def refresh_data(self):
        self._run_analysis_async(self.refresh_btn, self._refresh_data_impl)

    def run_backtest(self):
        self._run_analysis_async(self.backtest_btn, self._run_backtest_impl)

    def _update_overview_cards(self, data):
        """更新概览卡片数据

        Args:
            data: 资金流向数据
        """
        try:
            # 获取概览数据
            overview_data = data.get('overview', {})

            # 更新卡片数据
            cards = self.findChildren(QFrame)
            for card in cards:
                name_label = card.findChild(QLabel)
                if name_label:
                    name = name_label.text()
                    if name in overview_data:
                        value_data = overview_data[name]
                        value_label = card.findChild(
                            QLabel, "", Qt.FindChildrenRecursively)
                        if value_label and value_label != name_label:
                            value_label.setText(str(value_data['value']))
                            trend_label = value_label.parent().findChild(
                                QLabel, "", Qt.FindChildrenRecursively)
                            if trend_label and trend_label != value_label:
                                trend_label.setText(value_data['trend'])
                                trend_label.setStyleSheet(
                                    f"color: {value_data['color']};")
                                value_label.setStyleSheet(
                                    f"color: {value_data['color']};")

        except Exception as e:
            logging.error(f"更新概览卡片失败: {str(e)}")

    def update_fund_flow_data(self, data: dict):
        """更新资金流向数据

        Args:
            data: 资金流向数据字典
        """
        try:
            # 使用QTimer.singleShot确保在主线程中更新UI
            QTimer.singleShot(0, lambda: self._update_ui_safely(data))

        except Exception as e:
            self.log_manager.log(f"更新资金流向数据失败: {e}", LogLevel.ERROR)

    def _update_ui_safely(self, data: dict):
        """在主线程中安全地更新UI

        Args:
            data: 资金流向数据字典
        """
        try:
            # 更新数据缓存
            self._data_cache.update(data)
            self._cache_time[datetime.now()] = data

            # 更新各个指标
            self._update_flow_indicators(data)
            self._update_flow_charts(data)
            self._update_flow_tables(data)

            # 检查预警条件
            self._check_flow_alerts(data)

        except Exception as e:
            self.log_manager.log(f"更新UI失败: {e}", LogLevel.ERROR)

    def _update_north_flow(self, data):
        """异步更新北向资金流向图表"""
        try:
            # 使用QTimer.singleShot确保在主线程中执行UI更新
            QTimer.singleShot(0, lambda: self._update_north_flow_ui(data))
        except Exception as e:
            self.log_manager.error(f"更新北向资金流向图表失败: {str(e)}")

    def _update_north_flow_ui(self, data):
        """在主线程中更新北向资金流向图表UI"""
        try:
            self.north_chart.removeAllSeries()

            # 创建流入流出柱状图
            bar_set_in = QBarSet("流入")
            bar_set_out = QBarSet("流出")

            # 添加数据
            north_flow_data = data.get('north_flow', {})
            if isinstance(north_flow_data, dict):
                for date, values in north_flow_data.items():
                    if isinstance(values, dict):
                        bar_set_in.append(values.get('inflow', 0))
                        bar_set_out.append(values.get('outflow', 0))

            series = QBarSeries()
            series.append(bar_set_in)
            series.append(bar_set_out)

            self.north_chart.addSeries(series)
            self.north_chart.createDefaultAxes()

        except Exception as e:
            self.log_manager.error(f"北向资金流向图表UI更新失败: {str(e)}")

    def _check_alerts(self, data):
        """检查预警条件"""
        for indicator, alert in self._alerts.items():
            value = data.get(indicator, 0)
            if value >= alert['threshold']:
                alert['callback'](indicator, value)

    def update_industry_flow(self):
        """异步更新行业资金流向"""
        try:
            with QMutexLocker(self._update_mutex):
                # 停止现有的计算工作线程
                if self._calculation_worker and self._calculation_worker.isRunning():
                    self._calculation_worker.quit()
                    self._calculation_worker.wait()

                # 创建新的计算工作线程
                self._calculation_worker = FlowDataCalculationWorker("industry_flow", {})
                self._calculation_worker.industry_flow_calculated.connect(self._on_industry_flow_calculated)
                self._calculation_worker.calculation_error.connect(self._on_calculation_error)
                self._calculation_worker.calculation_progress.connect(self._on_calculation_progress)

                # 启动异步计算
                self._calculation_worker.start()

                # 显示加载状态
                self._show_loading_status("正在更新行业资金流向...")

        except Exception as e:
            self.log_manager.error(f"启动行业资金流向更新失败: {str(e)}")

    def _on_industry_flow_calculated(self, result: dict):
        """处理行业资金流计算结果"""
        try:
            table_data = result['table_data']

            # 更新表格数据
            self._update_industry_table(table_data)

            # 异步渲染图表
            if self._rendering_worker and self._rendering_worker.isRunning():
                self._rendering_worker.quit()
                self._rendering_worker.wait()

            self._rendering_worker = ChartRenderingWorker("industry_chart", result, self.industry_figure)
            self._rendering_worker.chart_rendered.connect(self._on_industry_chart_rendered)
            self._rendering_worker.rendering_error.connect(self._on_rendering_error)
            self._rendering_worker.start()

        except Exception as e:
            self.log_manager.error(f"处理行业资金流计算结果失败: {str(e)}")

    def _update_industry_table(self, table_data: dict):
        """更新行业资金流表格（在主线程中执行）"""
        try:
            industries = table_data['industries']
            inflows = table_data['inflows']
            outflows = table_data['outflows']
            net_flows = table_data['net_flows']
            strengths = table_data['strengths']
            sorted_indices = table_data['sorted_indices']

            # 更新表格
            for i, idx in enumerate(sorted_indices):
                items = [
                    QTableWidgetItem(industries[idx]),
                    QTableWidgetItem(f"{net_flows[idx]:.3f}"),
                    QTableWidgetItem(f"{inflows[idx]:.3f}"),
                    QTableWidgetItem(f"{outflows[idx]:.3f}"),
                    QTableWidgetItem(f"{strengths[idx]:.1f}%")
                ]
                for j, item in enumerate(items):
                    if j > 0:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if j == 1:
                        item.setForeground(
                            QColor("#4CAF50" if net_flows[idx] >= 0 else "#F44336"))
                    self.industry_table.setItem(i, j, item)

            # 添加合计、均值行
            row_count = len(industries)
            self.industry_table.setRowCount(row_count + 2)

            # 合计行
            sum_items = [QTableWidgetItem("合计"),
                         QTableWidgetItem(f"{net_flows.sum():.3f}"),
                         QTableWidgetItem(f"{inflows.sum():.3f}"),
                         QTableWidgetItem(f"{outflows.sum():.3f}"),
                         QTableWidgetItem("")]
            for j, item in enumerate(sum_items):
                item.setBackground(QColor("#e3f2fd"))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.industry_table.setItem(row_count, j, item)

            # 均值行
            mean_items = [QTableWidgetItem("均值"),
                          QTableWidgetItem(f"{net_flows.mean():.3f}"),
                          QTableWidgetItem(f"{inflows.mean():.3f}"),
                          QTableWidgetItem(f"{outflows.mean():.3f}"),
                          QTableWidgetItem(f"{strengths.mean():.1f}%")]
            for j, item in enumerate(mean_items):
                item.setBackground(QColor("#fffde7"))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.industry_table.setItem(row_count + 1, j, item)

            # 极值高亮
            max_net_idx = np.argmax(net_flows)
            min_net_idx = np.argmin(net_flows)
            max_str_idx = np.argmax(strengths)
            min_str_idx = np.argmin(strengths)
            self.industry_table.item(max_net_idx, 1).setBackground(QColor("#ffe082"))
            self.industry_table.item(min_net_idx, 1).setBackground(QColor("#ffccbc"))
            self.industry_table.item(max_str_idx, 4).setBackground(QColor("#b2ff59"))
            self.industry_table.item(min_str_idx, 4).setBackground(QColor("#ffcdd2"))

        except Exception as e:
            self.log_manager.error(f"更新行业资金流表格失败: {str(e)}")

    def _on_industry_chart_rendered(self, chart_type: str, result):
        """处理行业图表渲染完成"""
        try:
            self.industry_canvas.draw()
            self._hide_loading_status()
            self.log_manager.info("行业资金流向更新完成")
        except Exception as e:
            self.log_manager.error(f"行业图表渲染完成处理失败: {str(e)}")

    def update_concept_flow(self):
        """异步更新概念资金流向"""
        try:
            with QMutexLocker(self._update_mutex):
                # 停止现有的计算工作线程
                if self._calculation_worker and self._calculation_worker.isRunning():
                    self._calculation_worker.quit()
                    self._calculation_worker.wait()

                # 创建新的计算工作线程
                self._calculation_worker = FlowDataCalculationWorker("concept_flow", {})
                self._calculation_worker.concept_flow_calculated.connect(self._on_concept_flow_calculated)
                self._calculation_worker.calculation_error.connect(self._on_calculation_error)
                self._calculation_worker.calculation_progress.connect(self._on_calculation_progress)

                # 启动异步计算
                self._calculation_worker.start()

                # 显示加载状态
                self._show_loading_status("正在更新概念资金流向...")

        except Exception as e:
            self.log_manager.error(f"启动概念资金流向更新失败: {str(e)}")

    def _on_concept_flow_calculated(self, result: dict):
        """处理概念资金流计算结果"""
        try:
            table_data = result['table_data']

            # 更新表格数据
            self._update_concept_table(table_data)

            # 异步渲染图表
            if self._rendering_worker and self._rendering_worker.isRunning():
                self._rendering_worker.quit()
                self._rendering_worker.wait()

            self._rendering_worker = ChartRenderingWorker("concept_chart", result, self.concept_figure)
            self._rendering_worker.chart_rendered.connect(self._on_concept_chart_rendered)
            self._rendering_worker.rendering_error.connect(self._on_rendering_error)
            self._rendering_worker.start()

        except Exception as e:
            self.log_manager.error(f"处理概念资金流计算结果失败: {str(e)}")

    def _update_concept_table(self, table_data: dict):
        """更新概念资金流表格（在主线程中执行）"""
        try:
            concepts = table_data['concepts']
            inflows = table_data['inflows']
            outflows = table_data['outflows']
            net_flows = table_data['net_flows']
            strengths = table_data['strengths']
            sorted_indices = table_data['sorted_indices']

            # 更新表格
            for i, idx in enumerate(sorted_indices):
                items = [
                    QTableWidgetItem(concepts[idx]),
                    QTableWidgetItem(f"{net_flows[idx]:.3f}"),
                    QTableWidgetItem(f"{inflows[idx]:.3f}"),
                    QTableWidgetItem(f"{outflows[idx]:.3f}"),
                    QTableWidgetItem(f"{strengths[idx]:.1f}%")
                ]
                for j, item in enumerate(items):
                    if j > 0:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if j == 1:
                        item.setForeground(
                            QColor("#4CAF50" if net_flows[idx] >= 0 else "#F44336"))
                    self.concept_table.setItem(i, j, item)

            # 添加合计、均值行
            row_count = len(concepts)
            self.concept_table.setRowCount(row_count + 2)

            # 合计行
            sum_items = [QTableWidgetItem("合计"),
                         QTableWidgetItem(f"{net_flows.sum():.3f}"),
                         QTableWidgetItem(f"{inflows.sum():.3f}"),
                         QTableWidgetItem(f"{outflows.sum():.3f}"),
                         QTableWidgetItem("")]
            for j, item in enumerate(sum_items):
                item.setBackground(QColor("#e3f2fd"))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.concept_table.setItem(row_count, j, item)

            # 均值行
            mean_items = [QTableWidgetItem("均值"),
                          QTableWidgetItem(f"{net_flows.mean():.3f}"),
                          QTableWidgetItem(f"{inflows.mean():.3f}"),
                          QTableWidgetItem(f"{outflows.mean():.3f}"),
                          QTableWidgetItem(f"{strengths.mean():.1f}%")]
            for j, item in enumerate(mean_items):
                item.setBackground(QColor("#fffde7"))
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.concept_table.setItem(row_count + 1, j, item)

            # 极值高亮
            max_net_idx = np.argmax(net_flows)
            min_net_idx = np.argmin(net_flows)
            max_str_idx = np.argmax(strengths)
            min_str_idx = np.argmin(strengths)
            self.concept_table.item(max_net_idx, 1).setBackground(QColor("#ffe082"))
            self.concept_table.item(min_net_idx, 1).setBackground(QColor("#ffccbc"))
            self.concept_table.item(max_str_idx, 4).setBackground(QColor("#b2ff59"))
            self.concept_table.item(min_str_idx, 4).setBackground(QColor("#ffcdd2"))

        except Exception as e:
            self.log_manager.error(f"更新概念资金流表格失败: {str(e)}")

    def _on_concept_chart_rendered(self, chart_type: str, result):
        """处理概念图表渲染完成"""
        try:
            self.concept_canvas.draw()
            self._hide_loading_status()
            self.log_manager.info("概念资金流向更新完成")
        except Exception as e:
            self.log_manager.error(f"概念图表渲染完成处理失败: {str(e)}")

    def update_main_force_analysis(self):
        """异步更新主力资金分析"""
        try:
            with QMutexLocker(self._update_mutex):
                # 停止现有的计算工作线程
                if self._calculation_worker and self._calculation_worker.isRunning():
                    self._calculation_worker.quit()
                    self._calculation_worker.wait()

                # 创建新的计算工作线程
                self._calculation_worker = FlowDataCalculationWorker("main_force", {})
                self._calculation_worker.main_force_calculated.connect(self._on_main_force_calculated)
                self._calculation_worker.calculation_error.connect(self._on_calculation_error)
                self._calculation_worker.calculation_progress.connect(self._on_calculation_progress)

                # 启动异步计算
                self._calculation_worker.start()

                # 显示加载状态
                self._show_loading_status("正在更新主力资金分析...")

        except Exception as e:
            self.log_manager.error(f"启动主力资金分析更新失败: {str(e)}")

    def _on_main_force_calculated(self, result: dict):
        """处理主力资金分析计算结果"""
        try:
            # 异步渲染图表
            if self._rendering_worker and self._rendering_worker.isRunning():
                self._rendering_worker.quit()
                self._rendering_worker.wait()

            self._rendering_worker = ChartRenderingWorker("main_force_chart", result, self.main_force_figure)
            self._rendering_worker.chart_rendered.connect(self._on_main_force_chart_rendered)
            self._rendering_worker.rendering_error.connect(self._on_rendering_error)
            self._rendering_worker.start()

        except Exception as e:
            self.log_manager.error(f"处理主力资金分析计算结果失败: {str(e)}")

    def _on_main_force_chart_rendered(self, chart_type: str, result):
        """处理主力资金分析图表渲染完成"""
        try:
            self.main_force_canvas.draw()
            self._hide_loading_status()
            self.log_manager.info("主力资金分析更新完成")
        except Exception as e:
            self.log_manager.error(f"主力资金分析图表渲染完成处理失败: {str(e)}")

    # 添加辅助方法
    def _show_loading_status(self, message: str):
        """显示加载状态"""
        try:
            # 可以在这里添加加载状态的UI显示
            if hasattr(self, 'log_manager'):
                self.log_manager.info(message)
        except Exception as e:
            print(f"显示加载状态失败: {str(e)}")

    def _hide_loading_status(self):
        """隐藏加载状态"""
        try:
            # 可以在这里隐藏加载状态的UI显示
            pass
        except Exception as e:
            print(f"隐藏加载状态失败: {str(e)}")

    def _on_calculation_error(self, error_message: str):
        """处理计算错误"""
        try:
            self._hide_loading_status()
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"资金流数据计算错误: {error_message}")
            else:
                print(f"资金流数据计算错误: {error_message}")
        except Exception as e:
            print(f"处理计算错误失败: {str(e)}")

    def _on_rendering_error(self, error_message: str):
        """处理渲染错误"""
        try:
            self._hide_loading_status()
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"图表渲染错误: {error_message}")
            else:
                print(f"图表渲染错误: {error_message}")
        except Exception as e:
            print(f"处理渲染错误失败: {str(e)}")

    def _on_calculation_progress(self, progress: int, message: str):
        """处理计算进度"""
        try:
            # 可以在这里更新进度显示
            if hasattr(self, 'log_manager'):
                self.log_manager.debug(f"计算进度 {progress}%: {message}")
        except Exception as e:
            print(f"处理计算进度失败: {str(e)}")

    def closeEvent(self, event):
        """关闭事件处理 - 清理资源"""
        try:
            # 停止所有工作线程
            if self._calculation_worker and self._calculation_worker.isRunning():
                self._calculation_worker.quit()
                self._calculation_worker.wait()

            if self._rendering_worker and self._rendering_worker.isRunning():
                self._rendering_worker.quit()
                self._rendering_worker.wait()

            # 关闭线程池
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=True)

            # 停止数据更新线程
            if hasattr(self, 'update_thread'):
                self.update_thread.stop()
                self.update_thread.wait()

        except Exception as e:
            print(f"关闭资源时出错: {str(e)}")
        finally:
            super().closeEvent(event)

    def show_template_manager_dialog(self):
        """显示模板管理对话框 - 使用基类统一方法"""
        # 使用基类的统一对话框创建方法
        dialog = self.create_standard_dialog("模板管理", 800, 600)

        # 创建对话框内容
        layout = self.create_standard_layout("vbox", spacing=15)

        # 添加模板列表
        template_list = QListWidget()
        template_list.addItems(["默认模板", "资金流模板1", "资金流模板2"])
        layout.addWidget(QLabel("可用模板:"))
        layout.addWidget(template_list)

        # 创建按钮布局
        button_layout = self.create_button_layout([
            ("应用模板", lambda: self._apply_template(
                template_list, dialog), '#4CAF50'),
            ("删除模板", lambda: self._delete_template(template_list), '#F44336'),
            ("新建模板", self._create_new_template, '#2196F3')
        ])
        layout.addLayout(button_layout)

        # 创建对话框按钮
        button_box = self.create_dialog_button_box("ok_cancel")
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        self.center_dialog(dialog)

        return dialog.exec_()

    def _apply_template(self, list_widget, dialog):
        """应用模板"""
        current_item = list_widget.currentItem()
        if current_item:
            template_name = current_item.text()
            self.show_info_message("模板应用", f"已应用模板: {template_name}")
            dialog.accept()
        else:
            self.show_warning_message("选择模板", "请先选择一个模板")

    def _delete_template(self, list_widget):
        """删除模板"""
        current_item = list_widget.currentItem()
        if current_item:
            template_name = current_item.text()
            if template_name == "默认模板":
                self.show_warning_message("删除失败", "默认模板不能删除")
                return

            result = self.show_question_message(
                "确认删除", f"确定要删除模板 '{template_name}' 吗？")
            if result == QMessageBox.Yes:
                row = list_widget.row(current_item)
                list_widget.takeItem(row)
                self.show_info_message("删除成功", f"模板 '{template_name}' 已删除")
        else:
            self.show_warning_message("选择模板", "请先选择要删除的模板")

    def _create_new_template(self):
        """创建新模板"""
        self.show_info_message("新建模板", "新建模板功能正在开发中")

    def validate_params(self) -> (bool, str):
        """校验所有参数控件的输入，支持QDoubleSpinBox等"""
        valid = True
        error_msgs = []
        for name, widget in self.param_widgets.items():
            widget.setStyleSheet("")
            value = widget.value() if hasattr(widget, 'value') else None
            if value is not None:
                if value < widget.minimum() or value > widget.maximum():
                    valid = False
                    error_msgs.append(
                        f"{name} 超出允许范围 [{widget.minimum()}, {widget.maximum()}]")
                    widget.setStyleSheet("border: 2px solid red;")
        return valid, "\n".join(error_msgs)

    def on_fundflow_analyze(self):
        """资金流向分析入口，参数校验、日志、调用主分析逻辑，自动适配所有策略和UI刷新。"""
        valid, msg = self.validate_params()
        if not valid:
            self.set_status_message(msg, error=True)
            return
        self.set_status_message("参数校验通过，正在分析...", error=False)
        try:
            self.log_manager.info("on_fundflow_analyze 开始分析 - 资金流向")
            if hasattr(self.data_manager, 'get_fund_flow'):
                data = self.data_manager.get_fund_flow()
                if data:
                    self.update_fund_flow_data(data)
                    self.set_status_message("分析完成", error=False)
                else:
                    self.set_status_message("未获取到资金流向数据", error=True)
                    self.log_manager.warning("分析未获取到数据")
            else:
                self.set_status_message("数据管理器未实现get_fund_flow", error=True)
        except Exception as e:
            self.set_status_message(f"分析失败: {str(e)}", error=True)
            self.log_manager.error(f"分析失败: {str(e)}")
