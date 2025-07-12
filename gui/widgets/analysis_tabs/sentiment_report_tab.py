"""
情绪报告标签页模块
"""

from typing import Dict, Any, List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import random
import os

from .base_tab import BaseAnalysisTab
from core.logger import LogManager, LogLevel
from utils.config_manager import ConfigManager


class SentimentReportTab(BaseAnalysisTab):
    """情绪报告标签页"""

    # 定义信号
    sentiment_report_completed = pyqtSignal(dict)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)
        self.report_results = []
        self.report_statistics = {}
        self.scheduled_reports = []
        self.report_templates = []
        self.alert_rules = []

    def create_ui(self):
        """创建情绪报告UI"""
        layout = QVBoxLayout(self)

        # 报告配置区域
        config_group = self.create_config_section()
        layout.addWidget(config_group)

        # 报告控制区域
        control_group = self.create_control_section()
        layout.addWidget(control_group)

        # 结果显示区域
        results_group = self.create_results_section()
        layout.addWidget(results_group)

    def create_config_section(self):
        """创建报告配置区域"""
        config_group = QGroupBox("情绪报告配置")
        layout = QVBoxLayout(config_group)

        # 报告类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("报告类型:"))

        self.daily_report_cb = QCheckBox("日报")
        self.daily_report_cb.setChecked(True)
        type_layout.addWidget(self.daily_report_cb)

        self.weekly_report_cb = QCheckBox("周报")
        self.weekly_report_cb.setChecked(True)
        type_layout.addWidget(self.weekly_report_cb)

        self.monthly_report_cb = QCheckBox("月报")
        self.monthly_report_cb.setChecked(False)
        type_layout.addWidget(self.monthly_report_cb)

        self.custom_report_cb = QCheckBox("自定义报告")
        self.custom_report_cb.setChecked(False)
        type_layout.addWidget(self.custom_report_cb)

        type_layout.addStretch()
        layout.addLayout(type_layout)

        # 报告参数配置
        params_layout = QGridLayout()

        # 数据源选择
        params_layout.addWidget(QLabel("数据源:"), 0, 0)
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["实时数据", "历史数据", "混合数据"])
        params_layout.addWidget(self.data_source_combo, 0, 1)

        # 报告周期
        params_layout.addWidget(QLabel("报告周期:"), 0, 2)
        self.report_period_spin = QSpinBox()
        self.report_period_spin.setRange(1, 30)
        self.report_period_spin.setValue(7)
        self.report_period_spin.setSuffix(" 天")
        params_layout.addWidget(self.report_period_spin, 0, 3)

        # 预警阈值
        params_layout.addWidget(QLabel("预警阈值:"), 1, 0)
        self.alert_threshold_spin = QDoubleSpinBox()
        self.alert_threshold_spin.setRange(0.1, 1.0)
        self.alert_threshold_spin.setValue(0.8)
        self.alert_threshold_spin.setDecimals(2)
        params_layout.addWidget(self.alert_threshold_spin, 1, 1)

        # 报告格式
        params_layout.addWidget(QLabel("报告格式:"), 1, 2)
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["HTML", "PDF", "Word", "Excel"])
        params_layout.addWidget(self.report_format_combo, 1, 3)

        layout.addLayout(params_layout)

        # 定时任务配置
        schedule_group = QGroupBox("定时任务配置")
        schedule_layout = QGridLayout(schedule_group)

        # 启用定时任务
        self.enable_schedule_cb = QCheckBox("启用定时生成报告")
        schedule_layout.addWidget(self.enable_schedule_cb, 0, 0, 1, 2)

        # 生成时间
        schedule_layout.addWidget(QLabel("生成时间:"), 1, 0)
        self.schedule_time = QTimeEdit()
        self.schedule_time.setTime(QTime(9, 0))
        schedule_layout.addWidget(self.schedule_time, 1, 1)

        # 发送邮件
        self.email_report_cb = QCheckBox("自动发送邮件")
        schedule_layout.addWidget(self.email_report_cb, 1, 2)

        # 邮件地址
        schedule_layout.addWidget(QLabel("邮件地址:"), 2, 0)
        self.email_address_edit = QLineEdit()
        self.email_address_edit.setPlaceholderText("example@email.com")
        schedule_layout.addWidget(self.email_address_edit, 2, 1, 1, 2)

        layout.addWidget(schedule_group)
        return config_group

    def create_control_section(self):
        """创建报告控制区域"""
        control_group = QGroupBox("报告生成控制")
        layout = QHBoxLayout(control_group)

        # 生成报告按钮
        generate_btn = QPushButton("生成情绪报告")
        generate_btn.setStyleSheet(
            "QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        generate_btn.clicked.connect(self.generate_report)
        layout.addWidget(generate_btn)

        # 预览报告按钮
        preview_btn = QPushButton("预览报告")
        preview_btn.setStyleSheet(
            "QPushButton { background-color: #17a2b8; color: white; font-weight: bold; }")
        preview_btn.clicked.connect(self.preview_report)
        layout.addWidget(preview_btn)

        # 管理模板按钮
        template_btn = QPushButton("管理模板")
        template_btn.setStyleSheet(
            "QPushButton { background-color: #6f42c1; color: white; }")
        template_btn.clicked.connect(self.manage_templates)
        layout.addWidget(template_btn)

        # 设置预警按钮
        alert_btn = QPushButton("设置预警")
        alert_btn.setStyleSheet(
            "QPushButton { background-color: #fd7e14; color: white; }")
        alert_btn.clicked.connect(self.setup_alerts)
        layout.addWidget(alert_btn)

        # 清除结果按钮
        clear_btn = QPushButton("清除结果")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #dc3545; color: white; }")
        clear_btn.clicked.connect(self.clear_report)
        layout.addWidget(clear_btn)

        layout.addStretch()
        return control_group

    def create_results_section(self):
        """创建结果显示区域"""
        results_group = QGroupBox("情绪报告结果")
        layout = QVBoxLayout(results_group)

        # 报告状态概览
        status_group = QGroupBox("报告状态概览")
        status_layout = QHBoxLayout(status_group)

        # 已生成报告数
        generated_card = QFrame()
        generated_card.setFrameStyle(QFrame.StyledPanel)
        generated_card.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        generated_layout = QVBoxLayout(generated_card)
        generated_layout.addWidget(QLabel("已生成报告"))

        self.generated_count_label = QLabel("0")
        self.generated_count_label.setAlignment(Qt.AlignCenter)
        self.generated_count_label.setStyleSheet(
            "QLabel { font-size: 24px; font-weight: bold; color: #28a745; }")
        generated_layout.addWidget(self.generated_count_label)

        status_layout.addWidget(generated_card)

        # 定时任务数
        scheduled_card = QFrame()
        scheduled_card.setFrameStyle(QFrame.StyledPanel)
        scheduled_card.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        scheduled_layout = QVBoxLayout(scheduled_card)
        scheduled_layout.addWidget(QLabel("定时任务"))

        self.scheduled_count_label = QLabel("0")
        self.scheduled_count_label.setAlignment(Qt.AlignCenter)
        self.scheduled_count_label.setStyleSheet(
            "QLabel { font-size: 24px; font-weight: bold; color: #007bff; }")
        scheduled_layout.addWidget(self.scheduled_count_label)

        status_layout.addWidget(scheduled_card)

        # 预警规则数
        alert_card = QFrame()
        alert_card.setFrameStyle(QFrame.StyledPanel)
        alert_card.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        alert_layout = QVBoxLayout(alert_card)
        alert_layout.addWidget(QLabel("预警规则"))

        self.alert_count_label = QLabel("0")
        self.alert_count_label.setAlignment(Qt.AlignCenter)
        self.alert_count_label.setStyleSheet(
            "QLabel { font-size: 24px; font-weight: bold; color: #dc3545; }")
        alert_layout.addWidget(self.alert_count_label)

        status_layout.addWidget(alert_card)

        # 最近状态
        status_card = QFrame()
        status_card.setFrameStyle(QFrame.StyledPanel)
        status_card.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        status_card_layout = QVBoxLayout(status_card)
        status_card_layout.addWidget(QLabel("最近状态"))

        self.last_status_label = QLabel("等待生成")
        self.last_status_label.setAlignment(Qt.AlignCenter)
        self.last_status_label.setStyleSheet(
            "QLabel { font-size: 18px; font-weight: bold; color: #6c757d; }")
        status_card_layout.addWidget(self.last_status_label)

        status_layout.addWidget(status_card)

        layout.addWidget(status_group)

        # 详细结果标签页
        self.results_tab_widget = QTabWidget()

        # 报告列表标签页
        self.reports_tab = self.create_reports_list_tab()
        self.results_tab_widget.addTab(self.reports_tab, "报告列表")

        # 定时任务标签页
        self.schedule_tab = self.create_schedule_list_tab()
        self.results_tab_widget.addTab(self.schedule_tab, "定时任务")

        # 预警记录标签页
        self.alerts_tab = self.create_alerts_list_tab()
        self.results_tab_widget.addTab(self.alerts_tab, "预警记录")

        # 报告预览标签页
        self.preview_tab = self.create_preview_tab()
        self.results_tab_widget.addTab(self.preview_tab, "报告预览")

        layout.addWidget(self.results_tab_widget)
        return results_group

    def create_reports_list_tab(self):
        """创建报告列表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(7)
        self.reports_table.setHorizontalHeaderLabels([
            "报告名称", "报告类型", "生成时间", "数据周期", "文件大小", "状态", "操作"
        ])
        self.reports_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.reports_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setSortingEnabled(True)

        layout.addWidget(self.reports_table)
        return tab

    def create_schedule_list_tab(self):
        """创建定时任务列表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(6)
        self.schedule_table.setHorizontalHeaderLabels([
            "任务名称", "报告类型", "执行时间", "频率", "状态", "下次执行"
        ])
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.setAlternatingRowColors(True)
        self.schedule_table.setSortingEnabled(True)

        layout.addWidget(self.schedule_table)
        return tab

    def create_alerts_list_tab(self):
        """创建预警记录列表标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(6)
        self.alerts_table.setHorizontalHeaderLabels([
            "预警时间", "预警类型", "触发条件", "情绪指数", "预警级别", "处理状态"
        ])
        self.alerts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.alerts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSortingEnabled(True)

        layout.addWidget(self.alerts_table)
        return tab

    def create_preview_tab(self):
        """创建报告预览标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 预览工具栏
        toolbar_layout = QHBoxLayout()

        refresh_preview_btn = QPushButton("刷新预览")
        refresh_preview_btn.clicked.connect(self.refresh_preview)
        toolbar_layout.addWidget(refresh_preview_btn)

        export_preview_btn = QPushButton("导出预览")
        export_preview_btn.clicked.connect(self.export_preview)
        toolbar_layout.addWidget(export_preview_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # 预览内容
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setHtml(self.get_default_preview_content())
        layout.addWidget(self.preview_text)

        return tab

    def get_default_preview_content(self):
        """获取默认预览内容"""
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
                h2 { color: #34495e; margin-top: 30px; }
                .summary { background-color: #ecf0f1; padding: 15px; border-radius: 5px; }
                .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; }
                .positive { color: #27ae60; }
                .negative { color: #e74c3c; }
                .neutral { color: #7f8c8d; }
            </style>
        </head>
        <body>
            <h1>市场情绪分析报告</h1>
            <p><strong>报告生成时间:</strong> 等待生成...</p>
            <p><strong>数据分析周期:</strong> 等待设置...</p>
            
            <div class="summary">
                <h2>执行摘要</h2>
                <p>本报告将分析市场情绪指标，包括VIX恐慌指数、贪婪恐惧指数、投资者情绪等关键指标，为投资决策提供参考。</p>
            </div>
            
            <h2>情绪指标概览</h2>
            <div class="metric">
                <strong>综合情绪指数:</strong> <span class="neutral">待分析</span>
            </div>
            <div class="metric">
                <strong>VIX恐慌指数:</strong> <span class="neutral">待分析</span>
            </div>
            <div class="metric">
                <strong>贪婪恐惧指数:</strong> <span class="neutral">待分析</span>
            </div>
            
            <h2>趋势分析</h2>
            <p>情绪趋势分析将在报告生成后显示...</p>
            
            <h2>投资建议</h2>
            <p>基于情绪分析的投资建议将在报告生成后提供...</p>
            
            <h2>风险提示</h2>
            <p>市场情绪分析仅供参考，投资决策需结合多方面因素综合考虑。</p>
        </body>
        </html>
        """

    def generate_report(self):
        """生成情绪报告"""
        try:
            self.show_loading("正在生成情绪报告...")

            # 获取配置参数
            data_source = self.data_source_combo.currentText()
            period = self.report_period_spin.value()
            alert_threshold = self.alert_threshold_spin.value()
            report_format = self.report_format_combo.currentText()

            # 模拟报告生成
            report_data = self.collect_sentiment_data(period)
            report_content = self.generate_report_content(report_data)

            # 保存报告
            report_name = f"情绪报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            report_file = self.save_report(
                report_name, report_content, report_format)

            # 添加到报告列表
            self.add_report_to_list(report_name, report_file, period)

            # 检查预警条件
            self.check_alert_conditions(report_data, alert_threshold)

            # 更新显示
            self.update_report_display()
            self.update_report_statistics()

            # 发送完成信号
            self.sentiment_report_completed.emit({
                'report_name': report_name,
                'report_file': report_file,
                'data': report_data
            })

        except Exception as e:
            self.log_manager.error(f"生成情绪报告失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"生成情绪报告失败: {str(e)}")
        finally:
            self.hide_loading()

    def collect_sentiment_data(self, period: int):
        """收集情绪数据"""
        try:
            # 模拟情绪数据收集
            data = {
                'period': period,
                'collection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'vix_index': random.uniform(15, 35),
                'fear_greed_index': random.uniform(20, 80),
                'investor_sentiment': random.uniform(30, 70),
                'technical_sentiment': random.uniform(25, 75),
                'news_sentiment': random.uniform(40, 60),
                'social_sentiment': random.uniform(-1, 1),
                'composite_index': random.uniform(30, 70)
            }

            # 计算情绪状态
            composite = data['composite_index']
            if composite > 70:
                data['sentiment_status'] = '乐观'
            elif composite > 50:
                data['sentiment_status'] = '中性'
            else:
                data['sentiment_status'] = '悲观'

            # 生成历史趋势数据
            data['historical_trend'] = []
            for i in range(period):
                date = (datetime.now() - timedelta(days=i)
                        ).strftime('%Y-%m-%d')
                trend_value = random.uniform(30, 70)
                data['historical_trend'].append({
                    'date': date,
                    'value': trend_value
                })

            return data

        except Exception as e:
            self.log_manager.error(f"收集情绪数据失败: {str(e)}")
            return {}

    def generate_report_content(self, data: dict):
        """生成报告内容"""
        try:
            if not data:
                return "数据收集失败，无法生成报告"

            content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
                    h2 {{ color: #34495e; margin-top: 30px; }}
                    .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; }}
                    .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; }}
                    .positive {{ color: #27ae60; }}
                    .negative {{ color: #e74c3c; }}
                    .neutral {{ color: #7f8c8d; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>市场情绪分析报告</h1>
                <p><strong>报告生成时间:</strong> {data['collection_time']}</p>
                <p><strong>数据分析周期:</strong> {data['period']} 天</p>
                
                <div class="summary">
                    <h2>执行摘要</h2>
                    <p>当前市场情绪状态为<strong>{data['sentiment_status']}</strong>，综合情绪指数为 {data['composite_index']:.1f}。
                    本报告基于 {data['period']} 天的数据分析，涵盖了VIX恐慌指数、贪婪恐惧指数、投资者情绪等多个维度。</p>
                </div>
                
                <h2>情绪指标概览</h2>
                <div class="metric">
                    <strong>综合情绪指数:</strong> <span class="{'positive' if data['composite_index'] > 60 else 'negative' if data['composite_index'] < 40 else 'neutral'}">{data['composite_index']:.1f}</span>
                </div>
                <div class="metric">
                    <strong>VIX恐慌指数:</strong> <span class="{'negative' if data['vix_index'] > 25 else 'positive'}">{data['vix_index']:.1f}</span>
                </div>
                <div class="metric">
                    <strong>贪婪恐惧指数:</strong> <span class="{'positive' if data['fear_greed_index'] > 60 else 'negative' if data['fear_greed_index'] < 40 else 'neutral'}">{data['fear_greed_index']:.1f}</span>
                </div>
                <div class="metric">
                    <strong>投资者情绪:</strong> <span class="{'positive' if data['investor_sentiment'] > 60 else 'negative' if data['investor_sentiment'] < 40 else 'neutral'}">{data['investor_sentiment']:.1f}</span>
                </div>
                
                <h2>详细分析</h2>
                <table>
                    <tr>
                        <th>指标名称</th>
                        <th>当前值</th>
                        <th>状态评估</th>
                        <th>影响分析</th>
                    </tr>
                    <tr>
                        <td>VIX恐慌指数</td>
                        <td>{data['vix_index']:.2f}</td>
                        <td>{'高恐慌' if data['vix_index'] > 25 else '正常' if data['vix_index'] > 15 else '低恐慌'}</td>
                        <td>{'市场恐慌情绪较高，需谨慎投资' if data['vix_index'] > 25 else '市场情绪相对稳定'}</td>
                    </tr>
                    <tr>
                        <td>贪婪恐惧指数</td>
                        <td>{data['fear_greed_index']:.2f}</td>
                        <td>{'贪婪' if data['fear_greed_index'] > 60 else '恐惧' if data['fear_greed_index'] < 40 else '中性'}</td>
                        <td>{'市场情绪偏向贪婪，注意风险' if data['fear_greed_index'] > 60 else '市场情绪偏向恐惧，可能存在机会' if data['fear_greed_index'] < 40 else '市场情绪相对平衡'}</td>
                    </tr>
                    <tr>
                        <td>技术指标情绪</td>
                        <td>{data['technical_sentiment']:.2f}</td>
                        <td>{'乐观' if data['technical_sentiment'] > 60 else '悲观' if data['technical_sentiment'] < 40 else '中性'}</td>
                        <td>{'技术面支持上涨' if data['technical_sentiment'] > 60 else '技术面偏弱' if data['technical_sentiment'] < 40 else '技术面中性'}</td>
                    </tr>
                </table>
                
                <h2>投资建议</h2>
                <p>基于当前情绪分析结果：</p>
                <ul>
            """

            # 根据情绪状态生成投资建议
            if data['sentiment_status'] == '乐观':
                content += """
                    <li>市场情绪偏向乐观，但需注意过度乐观的风险</li>
                    <li>建议适当控制仓位，避免追高</li>
                    <li>关注估值合理的优质标的</li>
                """
            elif data['sentiment_status'] == '悲观':
                content += """
                    <li>市场情绪偏向悲观，可能存在投资机会</li>
                    <li>建议关注基本面良好但被错杀的标的</li>
                    <li>可以考虑分批建仓，但需控制风险</li>
                """
            else:
                content += """
                    <li>市场情绪相对中性，建议保持观望</li>
                    <li>等待明确的趋势信号再做决策</li>
                    <li>可以适当配置防御性资产</li>
                """

            content += """
                </ul>
                
                <h2>风险提示</h2>
                <p>1. 市场情绪分析仅供参考，不构成投资建议</p>
                <p>2. 投资决策需结合基本面、技术面等多方面因素</p>
                <p>3. 市场存在不确定性，请注意风险控制</p>
                <p>4. 过往表现不代表未来收益</p>
                
                <hr>
                <p><small>报告生成时间: {data['collection_time']} | 数据来源: 市场公开数据</small></p>
            </body>
            </html>
            """

            return content

        except Exception as e:
            self.log_manager.error(f"生成报告内容失败: {str(e)}")
            return f"生成报告内容失败: {str(e)}"

    def save_report(self, report_name: str, content: str, format_type: str):
        """保存报告"""
        try:
            # 创建报告目录
            reports_dir = "reports"
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)

            # 根据格式保存文件
            if format_type == "HTML":
                filename = f"{reports_dir}/{report_name}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            elif format_type == "PDF":
                filename = f"{reports_dir}/{report_name}.pdf"
                # 这里可以使用库如reportlab或weasyprint来生成PDF
                # 暂时保存为HTML格式
                with open(filename.replace('.pdf', '.html'), 'w', encoding='utf-8') as f:
                    f.write(content)
                filename = filename.replace('.pdf', '.html')
            else:
                filename = f"{reports_dir}/{report_name}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)

            return filename

        except Exception as e:
            self.log_manager.error(f"保存报告失败: {str(e)}")
            return ""

    def add_report_to_list(self, report_name: str, report_file: str, period: int):
        """添加报告到列表"""
        try:
            file_size = "0 KB"
            if os.path.exists(report_file):
                size_bytes = os.path.getsize(report_file)
                file_size = f"{size_bytes / 1024:.1f} KB"

            report_type = "日报" if period <= 1 else "周报" if period <= 7 else "月报"

            self.report_results.append({
                '报告名称': report_name,
                '报告类型': report_type,
                '生成时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '数据周期': f"{period} 天",
                '文件大小': file_size,
                '状态': "已完成",
                '文件路径': report_file
            })

        except Exception as e:
            self.log_manager.error(f"添加报告到列表失败: {str(e)}")

    def check_alert_conditions(self, data: dict, threshold: float):
        """检查预警条件"""
        try:
            if not data:
                return

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            composite_index = data.get('composite_index', 50)
            vix_index = data.get('vix_index', 20)

            # 检查极端情绪预警
            if composite_index > 80:
                self.add_alert_record(
                    current_time, "极度贪婪预警", f"综合情绪指数 > 80", composite_index, "高风险")
            elif composite_index < 20:
                self.add_alert_record(
                    current_time, "极度恐慌预警", f"综合情绪指数 < 20", composite_index, "高风险")

            # 检查VIX预警
            if vix_index > 30:
                self.add_alert_record(
                    current_time, "VIX恐慌预警", f"VIX指数 > 30", vix_index, "中风险")

        except Exception as e:
            self.log_manager.error(f"检查预警条件失败: {str(e)}")

    def add_alert_record(self, alert_time: str, alert_type: str, condition: str, index_value: float, level: str):
        """添加预警记录"""
        try:
            self.alert_rules.append({
                '预警时间': alert_time,
                '预警类型': alert_type,
                '触发条件': condition,
                '情绪指数': f"{index_value:.1f}",
                '预警级别': level,
                '处理状态': "待处理"
            })

        except Exception as e:
            self.log_manager.error(f"添加预警记录失败: {str(e)}")

    def preview_report(self):
        """预览报告"""
        try:
            # 收集当前数据
            period = self.report_period_spin.value()
            data = self.collect_sentiment_data(period)

            # 生成预览内容
            content = self.generate_report_content(data)

            # 更新预览
            self.preview_text.setHtml(content)

            # 切换到预览标签页
            self.results_tab_widget.setCurrentWidget(self.preview_tab)

        except Exception as e:
            self.log_manager.error(f"预览报告失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"预览报告失败: {str(e)}")

    def manage_templates(self):
        """管理报告模板"""
        try:
            QMessageBox.information(self, "模板管理", "报告模板管理功能开发中...")

        except Exception as e:
            self.log_manager.error(f"管理模板失败: {str(e)}")

    def setup_alerts(self):
        """设置预警规则"""
        try:
            QMessageBox.information(self, "预警设置", "预警规则设置功能开发中...")

        except Exception as e:
            self.log_manager.error(f"设置预警失败: {str(e)}")

    def refresh_preview(self):
        """刷新预览"""
        self.preview_report()

    def export_preview(self):
        """导出预览"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出预览报告", f"preview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                "HTML files (*.html)")

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.preview_text.toHtml())
                QMessageBox.information(self, "成功", f"预览报告已导出到: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出预览失败: {str(e)}")

    def update_report_display(self):
        """更新报告显示"""
        try:
            # 更新报告列表
            self.reports_table.setRowCount(len(self.report_results))
            for i, report in enumerate(self.report_results):
                self.reports_table.setItem(
                    i, 0, QTableWidgetItem(report['报告名称']))
                self.reports_table.setItem(
                    i, 1, QTableWidgetItem(report['报告类型']))
                self.reports_table.setItem(
                    i, 2, QTableWidgetItem(report['生成时间']))
                self.reports_table.setItem(
                    i, 3, QTableWidgetItem(report['数据周期']))
                self.reports_table.setItem(
                    i, 4, QTableWidgetItem(report['文件大小']))

                # 状态带颜色显示
                status_item = QTableWidgetItem(report['状态'])
                if report['状态'] == '已完成':
                    status_item.setForeground(QColor("green"))
                else:
                    status_item.setForeground(QColor("orange"))
                self.reports_table.setItem(i, 5, status_item)

                # 操作按钮
                self.reports_table.setItem(i, 6, QTableWidgetItem("查看/下载"))

            # 更新预警记录
            self.alerts_table.setRowCount(len(self.alert_rules))
            for i, alert in enumerate(self.alert_rules):
                self.alerts_table.setItem(
                    i, 0, QTableWidgetItem(alert['预警时间']))
                self.alerts_table.setItem(
                    i, 1, QTableWidgetItem(alert['预警类型']))
                self.alerts_table.setItem(
                    i, 2, QTableWidgetItem(alert['触发条件']))
                self.alerts_table.setItem(
                    i, 3, QTableWidgetItem(alert['情绪指数']))

                # 预警级别带颜色显示
                level_item = QTableWidgetItem(alert['预警级别'])
                if alert['预警级别'] == '高风险':
                    level_item.setForeground(QColor("red"))
                elif alert['预警级别'] == '中风险':
                    level_item.setForeground(QColor("orange"))
                else:
                    level_item.setForeground(QColor("blue"))
                self.alerts_table.setItem(i, 4, level_item)

                self.alerts_table.setItem(
                    i, 5, QTableWidgetItem(alert['处理状态']))

            # 调整列宽
            self.reports_table.resizeColumnsToContents()
            self.alerts_table.resizeColumnsToContents()

        except Exception as e:
            self.log_manager.error(f"更新报告显示失败: {str(e)}")

    def update_report_statistics(self):
        """更新报告统计"""
        try:
            generated_count = len(self.report_results)
            scheduled_count = 1 if self.enable_schedule_cb.isChecked() else 0
            alert_count = len(self.alert_rules)

            # 更新显示
            self.generated_count_label.setText(str(generated_count))
            self.scheduled_count_label.setText(str(scheduled_count))
            self.alert_count_label.setText(str(alert_count))

            # 更新最近状态
            if generated_count > 0:
                self.last_status_label.setText("报告已生成")
                self.last_status_label.setStyleSheet(
                    "QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")
            else:
                self.last_status_label.setText("等待生成")
                self.last_status_label.setStyleSheet(
                    "QLabel { font-size: 18px; font-weight: bold; color: #6c757d; }")

            # 更新统计数据
            self.report_statistics = {
                'generated_reports': generated_count,
                'scheduled_tasks': scheduled_count,
                'alert_rules': alert_count
            }

        except Exception as e:
            self.log_manager.error(f"更新报告统计失败: {str(e)}")

    def clear_report(self):
        """清除报告结果"""
        self.report_results = []
        self.report_statistics = {}
        self.scheduled_reports = []
        self.alert_rules = []

        self.reports_table.setRowCount(0)
        self.schedule_table.setRowCount(0)
        self.alerts_table.setRowCount(0)

        self.generated_count_label.setText("0")
        self.scheduled_count_label.setText("0")
        self.alert_count_label.setText("0")
        self.last_status_label.setText("等待生成")
        self.last_status_label.setStyleSheet(
            "QLabel { font-size: 18px; font-weight: bold; color: #6c757d; }")

        # 重置预览
        self.preview_text.setHtml(self.get_default_preview_content())

    def refresh_data(self):
        """刷新数据"""
        self.generate_report()

    def clear_data(self):
        """清除数据"""
        self.clear_report()
