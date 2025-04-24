import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QPushButton,
                           QFrame, QGridLayout, QProgressBar, QFileDialog, QApplication)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QPainter, QFont
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QBarSeries, QBarSet
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import time
import logging

from core.stock_screener import DataManager,StockScreener
from components.stock_screener import StockScreenerWidget
from pylab import mpl

# 设置matplotlib中文字体
mpl.rcParams["font.sans-serif"] = [
    "SimHei"        # 黑体
]
mpl.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题
mpl.rcParams["font.size"] = 12

# 设置Qt全局字体
QApplication.setFont(QFont("Microsoft YaHei", 10))

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

class FundFlowWidget(QWidget):
    """资金流向分析组件"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self._data_cache = {}
        self._cache_time = {}
        self._custom_indicators = {}
        self._alerts = {}
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建资金流向概览卡片
        self.create_overview_cards(layout)
        
        # 创建北向资金流向图表
        self.create_north_flow_chart(layout)
        
        # 创建行业资金流向表格和图表
        self.create_industry_flow_section(layout)
        
        # 创建概念资金流向表格和图表
        self.create_concept_flow_section(layout)
        
        # 创建主力资金分析
        self.create_main_force_analysis(layout)
        
        # 创建控制按钮
        self.create_control_buttons(layout)
        
        # 启动数据更新线程
        if self.data_manager:
            self.update_thread = DataUpdateThread(self.data_manager)
            self.update_thread.data_updated.connect(self.update_all)
            self.update_thread.start()
            
    def create_control_buttons(self, layout):
        """创建控制按钮"""
        button_layout = QHBoxLayout()
        
        # 导出数据按钮
        export_button = QPushButton("导出数据")
        export_button.clicked.connect(self.export_data)
        button_layout.addWidget(export_button)
        
        # 添加自定义指标按钮
        add_indicator_button = QPushButton("添加指标")
        add_indicator_button.clicked.connect(self.show_add_indicator_dialog)
        button_layout.addWidget(add_indicator_button)
        
        # 设置预警按钮
        alert_button = QPushButton("设置预警")
        alert_button.clicked.connect(self.show_alert_dialog)
        button_layout.addWidget(alert_button)
        
        layout.addLayout(button_layout)
        
    def create_overview_cards(self, layout):
        """创建资金流向概览卡片"""
        cards_layout = QGridLayout()
        
        # 定义概览指标
        indicators = [
            ("今日净流入", "+28.5亿", "↑", "#4CAF50"),
            ("北向资金", "-12.3亿", "↓", "#F44336"),
            ("融资余额", "9856.7亿", "→", "#2196F3"),
            ("融券余额", "123.4亿", "↑", "#4CAF50"),
            ("大单成交额", "456.7亿", "↑", "#4CAF50"),
            ("成交活跃度", "85%", "↑", "#4CAF50")
        ]
        
        for i, (name, value, trend, color) in enumerate(indicators):
            card = QFrame()
            card.setFrameStyle(QFrame.Box | QFrame.Raised)
            card.setLineWidth(2)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border-radius: 10px;
                    padding: 10px;
                    border: 2px solid {color};
                }}
            """)
            
            card_layout = QVBoxLayout(card)
            
            # 指标名称
            name_label = QLabel(name)
            name_label.setStyleSheet("font-weight: bold; color: #333333;")
            card_layout.addWidget(name_label)
            
            # 数值和趋势
            value_layout = QHBoxLayout()
            value_label = QLabel(value)
            value_label.setStyleSheet(f"font-size: 18px; color: {color};")
            trend_label = QLabel(trend)
            trend_label.setStyleSheet(f"font-size: 18px; color: {color};")
            value_layout.addWidget(value_label)
            value_layout.addWidget(trend_label)
            card_layout.addLayout(value_layout)
            
            cards_layout.addWidget(card, i // 3, i % 3)
            
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
        self.industry_table.setHorizontalHeaderLabels(["行业", "净流入(亿)", "流入(亿)", "流出(亿)", "强度"])
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
        self.concept_table.setHorizontalHeaderLabels(["概念", "净流入(亿)", "流入(亿)", "流出(亿)", "强度"])
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
        
    def export_data(self):
        """导出资金流向数据"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "", "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            if filename:
                data = pd.DataFrame(self._data_cache)
                if filename.endswith('.xlsx'):
                    data.to_excel(filename)
                else:
                    data.to_csv(filename)
                logging.info(f"数据已导出到: {filename}")
        except Exception as e:
            logging.error(f"导出数据失败: {e}")
            
    def show_add_indicator_dialog(self):
        """显示添加指标对话框"""
        # TODO: 实现添加指标对话框
        pass
        
    def show_alert_dialog(self):
        """显示预警设置对话框"""
        # TODO: 实现预警设置对话框
        pass
        
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
                        value_label = card.findChild(QLabel, "", Qt.FindChildrenRecursively)
                        if value_label and value_label != name_label:
                            value_label.setText(str(value_data['value']))
                            trend_label = value_label.parent().findChild(QLabel, "", Qt.FindChildrenRecursively)
                            if trend_label and trend_label != value_label:
                                trend_label.setText(value_data['trend'])
                                trend_label.setStyleSheet(f"color: {value_data['color']};")
                                value_label.setStyleSheet(f"color: {value_data['color']};")
                                
        except Exception as e:
            logging.error(f"更新概览卡片失败: {str(e)}")
            
    def update_all(self, data=None):
        """更新所有组件数据
        
        Args:
            data: 资金流向数据
        """
        try:
            if data is None:
                data = self._get_cached_data('fund_flow')
                if data is None:
                    return
                    
            # 更新概览卡片
            self._update_overview_cards(data)
            
            # 更新北向资金流向
            self._update_north_flow(data)
            
            # 更新行业资金流向
            self.update_industry_flow()
            
            # 更新概念资金流向
            self.update_concept_flow()
            
            # 更新主力资金分析
            self.update_main_force_analysis()
            
            # 检查预警
            self._check_alerts(data)
            
        except Exception as e:
            logging.error(f"更新资金流向数据失败: {str(e)}")
            
    def _update_north_flow(self, data):
        """更新北向资金流向图表"""
        self.north_chart.removeAllSeries()
        
        # 创建流入流出柱状图
        bar_set_in = QBarSet("流入")
        bar_set_out = QBarSet("流出")
        
        # 添加数据
        for date, values in data.get('north_flow', {}).items():
            bar_set_in.append(values['inflow'])
            bar_set_out.append(values['outflow'])
            
        series = QBarSeries()
        series.append(bar_set_in)
        series.append(bar_set_out)
        
        self.north_chart.addSeries(series)
        self.north_chart.createDefaultAxes()
        
    def _check_alerts(self, data):
        """检查预警条件"""
        for indicator, alert in self._alerts.items():
            value = data.get(indicator, 0)
            if value >= alert['threshold']:
                alert['callback'](indicator, value)
                
    def closeEvent(self, event):
        """关闭事件处理"""
        if hasattr(self, 'update_thread'):
            self.update_thread.stop()
            self.update_thread.wait()
        super().closeEvent(event)

    def update_industry_flow(self):
        """更新行业资金流向"""
        try:
            # 生成模拟数据
            industries = [
                "医药生物", "计算机", "电子", "通信", "传媒",
                "电气设备", "机械设备", "汽车", "食品饮料", "银行"
            ]
            inflows = np.random.uniform(10, 100, 10)
            outflows = np.random.uniform(10, 100, 10)
            net_flows = inflows - outflows
            strengths = np.random.uniform(0, 100, 10)  # 资金强度指标
            
            # 按净流入排序
            sorted_indices = np.argsort(-net_flows)
            
            # 更新表格
            for i, idx in enumerate(sorted_indices):
                items = [
                    QTableWidgetItem(industries[idx]),
                    QTableWidgetItem(f"{net_flows[idx]:.2f}"),
                    QTableWidgetItem(f"{inflows[idx]:.2f}"),
                    QTableWidgetItem(f"{outflows[idx]:.2f}"),
                    QTableWidgetItem(f"{strengths[idx]:.1f}%")
                ]
                
                # 设置对齐方式和颜色
                for j, item in enumerate(items):
                    if j > 0:  # 数值列右对齐
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if j == 1:  # 净流入列设置颜色
                        item.setForeground(QColor("#4CAF50" if net_flows[idx] >= 0 else "#F44336"))
                    self.industry_table.setItem(i, j, item)
                    
            # 更新行业资金流向图表
            self.industry_figure.clear()
            ax = self.industry_figure.add_subplot(111)
            
            # 获取前5个行业的数据
            top5_idx = sorted_indices[:5]
            top5_industries = [industries[i] for i in top5_idx]
            top5_net_flows = [net_flows[i] for i in top5_idx]
            
            # 绘制水平条形图
            bars = ax.barh(top5_industries, top5_net_flows)
            
            # 设置条形图颜色
            for i, bar in enumerate(bars):
                bar.set_color('#4CAF50' if top5_net_flows[i] >= 0 else '#F44336')
                
            # 添加数值标签
            for i, v in enumerate(top5_net_flows):
                ax.text(v + (1 if v >= 0 else -1), i, f'{v:.1f}亿',
                       va='center', ha='left' if v >= 0 else 'right')
                
            ax.set_title('行业资金流向TOP5')
            ax.grid(True, alpha=0.3)
            
            # 调整布局
            self.industry_figure.tight_layout()
            self.industry_canvas.draw()
            
        except Exception as e:
            print(f"更新行业资金流向失败: {str(e)}")
            
    def update_concept_flow(self):
        """更新概念资金流向"""
        try:
            # 生成模拟数据
            concepts = [
                "人工智能", "新能源", "半导体", "5G", "云计算",
                "区块链", "生物医药", "新材料", "智能驾驶", "元宇宙"
            ]
            inflows = np.random.uniform(10, 100, 10)
            outflows = np.random.uniform(10, 100, 10)
            net_flows = inflows - outflows
            strengths = np.random.uniform(0, 100, 10)  # 资金强度指标
            
            # 按净流入排序
            sorted_indices = np.argsort(-net_flows)
            
            # 更新表格
            for i, idx in enumerate(sorted_indices):
                items = [
                    QTableWidgetItem(concepts[idx]),
                    QTableWidgetItem(f"{net_flows[idx]:.2f}"),
                    QTableWidgetItem(f"{inflows[idx]:.2f}"),
                    QTableWidgetItem(f"{outflows[idx]:.2f}"),
                    QTableWidgetItem(f"{strengths[idx]:.1f}%")
                ]
                
                # 设置对齐方式和颜色
                for j, item in enumerate(items):
                    if j > 0:  # 数值列右对齐
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if j == 1:  # 净流入列设置颜色
                        item.setForeground(QColor("#4CAF50" if net_flows[idx] >= 0 else "#F44336"))
                    self.concept_table.setItem(i, j, item)
                    
            # 更新概念资金流向图表
            self.concept_figure.clear()
            ax = self.concept_figure.add_subplot(111)
            
            # 获取前5个概念的数据
            top5_idx = sorted_indices[:5]
            top5_concepts = [concepts[i] for i in top5_idx]
            top5_net_flows = [net_flows[i] for i in top5_idx]
            
            # 绘制水平条形图
            bars = ax.barh(top5_concepts, top5_net_flows)
            
            # 设置条形图颜色
            for i, bar in enumerate(bars):
                bar.set_color('#4CAF50' if top5_net_flows[i] >= 0 else '#F44336')
                
            # 添加数值标签
            for i, v in enumerate(top5_net_flows):
                ax.text(v + (1 if v >= 0 else -1), i, f'{v:.1f}亿',
                       va='center', ha='left' if v >= 0 else 'right')
                
            ax.set_title('概念资金流向TOP5')
            ax.grid(True, alpha=0.3)
            
            # 调整布局
            self.concept_figure.tight_layout()
            self.concept_canvas.draw()
            
        except Exception as e:
            print(f"更新概念资金流向失败: {str(e)}")
            
    def update_main_force_analysis(self):
        """更新主力资金分析"""
        try:
            self.main_force_figure.clear()
            
            # 创建网格布局
            gs = self.main_force_figure.add_gridspec(1, 3)
            ax1 = self.main_force_figure.add_subplot(gs[0])  # 主力净流入
            ax2 = self.main_force_figure.add_subplot(gs[1])  # 资金规模分布
            ax3 = self.main_force_figure.add_subplot(gs[2])  # 主力活跃度
            
            # 生成模拟数据
            dates = pd.date_range(end=pd.Timestamp.now(), periods=10, freq='D')
            main_force_flow = np.random.normal(0, 50, 10)
            
            # 1. 主力净流入趋势
            bars = ax1.bar(dates, main_force_flow)
            for i, bar in enumerate(bars):
                bar.set_color('#4CAF50' if main_force_flow[i] >= 0 else '#F44336')
            ax1.set_title('主力净流入趋势')
            ax1.tick_params(axis='x', rotation=45)
            
            # 2. 资金规模分布
            sizes = ['超大单', '大单', '中单', '小单']
            values = np.random.uniform(20, 40, 4)
            colors = ['#2196F3', '#4CAF50', '#FFC107', '#FF5722']
            ax2.pie(values, labels=sizes, colors=colors, autopct='%1.1f%%')
            ax2.set_title('资金规模分布')
            
            # 3. 主力活跃度热力图
            activity_data = np.random.uniform(0, 1, (5, 5))
            times = ['09:30', '10:30', '11:30', '14:00', '15:00']
            types = ['买入', '卖出', '净买入', '净卖出', '成交额']
            
            sns.heatmap(activity_data, annot=True, fmt='.2f', cmap='RdYlGn',
                       xticklabels=times, yticklabels=types, ax=ax3)
            ax3.set_title('主力活跃度分析')
            
            # 调整布局
            self.main_force_figure.tight_layout()
            self.main_force_canvas.draw()
            
        except Exception as e:
            print(f"更新主力资金分析失败: {str(e)}") 