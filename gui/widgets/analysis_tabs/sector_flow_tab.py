"""
板块资金流分析标签页 - 专业版升级
"""
import json
from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QColor, QKeySequence
from datetime import datetime
from .sector_flow_tab_pro import SectorFlowTabPro


class SectorFlowTab(SectorFlowTabPro):
    """板块资金流分析标签页 - 继承专业版功能，保持向后兼容"""

    def __init__(self, config_manager=None):
        """初始化板块资金流分析标签页"""
        super().__init__(config_manager)

        # 保持向后兼容的属性
        self.flow_results = {}
        self.flow_statistics = {}

        # 连接信号以保持兼容性
        self.analysis_completed.connect(self._on_analysis_completed)

    def _on_analysis_completed(self, results):
        """分析完成处理 - 兼容原有接口"""
        try:
            self.hide_loading()
            self.status_label.setText("分析完成")

            if 'error' in results:
                self.error_occurred.emit(results['error'])
                return

            # 更新显示
            self._update_flow_display(results)

            # 发射兼容信号
            if 'ranking_data' in results:
                self.sector_flow_completed.emit(results)

        except Exception as e:
            self.log_manager.error(f"分析完成处理失败: {e}")

    def _update_flow_display(self, results):
        """更新资金流显示"""
        # 更新排行表格
        if 'ranking_data' in results:
            self._update_ranking_table(results['ranking_data'])

        # 更新轮动表格
        if 'rotation_data' in results:
            self._update_rotation_table(results['rotation_data'])

        # 更新聪明资金表格
        if 'smart_money_data' in results:
            self._update_smart_money_table(results['smart_money_data'])

        # 更新实时监控表格
        if 'realtime_data' in results:
            self._update_monitor_table(results['realtime_data'])

        # 更新预测显示
        if 'flow_prediction' in results:
            self.prediction_text.setText(results['flow_prediction'])

        # 更新统计数据
        if 'ranking_data' in results:
            self._update_statistics(results['ranking_data'])

    def _update_ranking_table(self, ranking_data):
        """更新排行表格"""
        column_keys = ['rank', 'sector', 'net_inflow', 'inflow_intensity', 'activity', 'change_pct', 'leading_stock', 'status']

        # 预处理数据
        processed_data = []
        for data in ranking_data:
            processed_item = {
                'rank': str(data.get('rank', '')),
                'sector': str(data.get('sector', '')),
                'net_inflow': f"{data.get('net_inflow', 0):.0f}",
                'inflow_intensity': f"{data.get('inflow_intensity', 0):.2f}",
                'activity': f"{data.get('activity', 0):.2f}",
                'change_pct': f"{data.get('change_pct', 0):.2f}%",
                'leading_stock': str(data.get('leading_stock', '')),
                'status': str(data.get('status', ''))
            }
            processed_data.append(processed_item)

        self.update_table_data(self.ranking_table, processed_data, column_keys)

    def _update_rotation_table(self, rotation_data):
        """更新轮动表格"""
        column_keys = ['direction', 'outflow_sector', 'inflow_sector', 'amount', 'strength', 'time']

        # 预处理数据
        processed_data = []
        for data in rotation_data:
            processed_item = {
                'direction': str(data.get('direction', '')),
                'outflow_sector': str(data.get('outflow_sector', '')),
                'inflow_sector': str(data.get('inflow_sector', '')),
                'amount': f"{data.get('amount', 0):.0f}",
                'strength': str(data.get('strength', '')),
                'time': str(data.get('time', ''))
            }
            processed_data.append(processed_item)

        self.update_table_data(self.rotation_table, processed_data, column_keys)

    def _update_smart_money_table(self, smart_money_data):
        """更新聪明资金表格"""
        column_keys = ['time', 'sector', 'money_type', 'amount', 'direction', 'confidence', 'impact']

        # 预处理数据
        processed_data = []
        for data in smart_money_data:
            processed_item = {
                'time': str(data.get('time', '')),
                'sector': str(data.get('sector', '')),
                'money_type': str(data.get('money_type', '')),
                'amount': f"{data.get('amount', 0):.0f}",
                'direction': str(data.get('direction', '')),
                'confidence': f"{data.get('confidence', 0):.2f}",
                'impact': str(data.get('impact', ''))
            }
            processed_data.append(processed_item)

        self.update_table_data(self.smart_money_table, processed_data, column_keys)

    def _update_monitor_table(self, monitor_data):
        """更新监控表格"""
        column_keys = ['time', 'sector', 'event', 'amount', 'impact', 'status']

        # 预处理数据
        processed_data = []
        for data in monitor_data:
            processed_item = {
                'time': str(data.get('time', '')),
                'sector': str(data.get('sector', '')),
                'event': str(data.get('event', '')),
                'amount': f"{data.get('amount', 0):.0f}",
                'impact': str(data.get('impact', '')),
                'status': str(data.get('status', ''))
            }
            processed_data.append(processed_item)

        self.update_table_data(self.monitor_table, processed_data, column_keys)

    def _update_statistics(self, ranking_data):
        """更新统计数据"""
        if not ranking_data:
            return

        # 计算统计数据
        total_inflow = sum(max(0, data.get('net_inflow', 0)) for data in ranking_data)
        total_outflow = sum(abs(min(0, data.get('net_inflow', 0))) for data in ranking_data)
        net_inflow = total_inflow - total_outflow
        active_sectors = len([data for data in ranking_data if data.get('activity', 0) > 0.6])

        # 更新显示
        if hasattr(self, 'inflow_label'):
            self.inflow_label.setText(f"{total_inflow/10000:.2f}亿")
        if hasattr(self, 'outflow_label'):
            self.outflow_label.setText(f"{total_outflow/10000:.2f}亿")
        if hasattr(self, 'net_label'):
            self.net_label.setText(f"{net_inflow/10000:.2f}亿")
        if hasattr(self, 'active_label'):
            self.active_label.setText(f"{active_sectors}个")

    # 保持向后兼容的方法
    def analyze_sector_flow(self):
        """执行板块资金流分析 - 兼容原接口"""
        self.comprehensive_flow_analysis()

    def simulate_flow_analysis(self, sectors, flow_type, period, threshold):
        """模拟资金流分析 - 兼容原接口"""
        # 调用专业版的综合分析
        self.comprehensive_flow_analysis()

    def update_flow_display(self):
        """更新资金流显示 - 兼容原接口"""
        # 如果有最新的分析结果，更新显示
        if hasattr(self, 'latest_results') and self.latest_results:
            self._update_flow_display(self.latest_results)

    def update_flow_statistics(self):
        """更新资金流统计 - 兼容原接口"""
        # 计算统计信息
        self.flow_statistics = {
            'total_sectors': len(self.sector_rankings),
            'active_sectors': len([s for s in self.sector_rankings if s.get('activity', 0) > 0.6]),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def clear_sector_flow(self):
        """清除板块资金流 - 兼容原接口"""
        self._do_clear_data()

    def export_fund_flow(self):
        """导出资金流 - 兼容原接口"""
        self.export_results()

    def show_advanced_analysis(self):
        """显示高级分析 - 兼容原接口"""
        # 切换到综合分析
        self.comprehensive_flow_analysis()

    def toggle_real_time_monitor(self):
        """切换实时监控 - 兼容原接口"""
        self.realtime_monitoring()

    def refresh_data(self):
        """刷新数据 - 兼容原接口"""
        self._do_refresh_data()

    def clear_data(self):
        """清除数据 - 兼容原接口"""
        self._do_clear_data()

    # 向后兼容的方法 - 创建UI组件
    def create_control_section(self):
        """创建控制区域 - 兼容原接口"""
        return self._create_control_panel()

    def create_statistics_section(self):
        """创建统计区域 - 兼容原接口"""
        # 返回一个简化的统计区域
        stats_group = QGroupBox("资金流向统计")
        stats_layout = QHBoxLayout(stats_group)

        # 总流入
        self.total_inflow_label = QLabel("0.00亿")
        stats_layout.addWidget(QLabel("总流入:"))
        stats_layout.addWidget(self.total_inflow_label)

        # 总流出
        self.total_outflow_label = QLabel("0.00亿")
        stats_layout.addWidget(QLabel("总流出:"))
        stats_layout.addWidget(self.total_outflow_label)

        # 净流入
        self.net_flow_label = QLabel("0.00亿")
        stats_layout.addWidget(QLabel("净流入:"))
        stats_layout.addWidget(self.net_flow_label)

        # 活跃度
        self.activity_label = QLabel("中等")
        stats_layout.addWidget(QLabel("活跃度:"))
        stats_layout.addWidget(self.activity_label)

        return stats_group

    def create_details_section(self):
        """创建详情区域 - 兼容原接口"""
        return self._create_results_panel()

    def create_industry_flow_tab(self):
        """创建行业资金流标签页 - 兼容原接口"""
        return self._create_ranking_tab()

    def create_concept_flow_tab(self):
        """创建概念资金流标签页 - 兼容原接口"""
        return self._create_rotation_tab()

    def create_north_flow_tab(self):
        """创建北向资金标签页 - 兼容原接口"""
        return self._create_smart_money_tab()

    # 向后兼容的信号
    sector_flow_completed = pyqtSignal(dict)
