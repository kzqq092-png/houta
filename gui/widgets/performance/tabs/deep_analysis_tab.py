#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析标签页
现代化深度分析工具界面
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit
)
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)

# 检查matplotlib可用性
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ModernDeepAnalysisTab(QWidget):
    """现代化深度分析工具标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 分析工具选择
        tools_group = QGroupBox("🔬 分析工具")
        tools_layout = QGridLayout()

        # 性能瓶颈分析
        self.bottleneck_btn = QPushButton("🐌 性能瓶颈分析")
        self.bottleneck_btn.clicked.connect(self.run_bottleneck_analysis)
        tools_layout.addWidget(self.bottleneck_btn, 0, 0)

        # 操作耗时排行
        self.ranking_btn = QPushButton("⏱️ 操作耗时排行")
        self.ranking_btn.clicked.connect(self.show_operation_ranking)
        tools_layout.addWidget(self.ranking_btn, 0, 1)

        # 性能对比分析
        self.comparison_btn = QPushButton("📊 性能对比分析")
        self.comparison_btn.clicked.connect(self.run_performance_comparison)
        tools_layout.addWidget(self.comparison_btn, 0, 2)

        # 趋势预测
        self.prediction_btn = QPushButton("🔮 趋势预测")
        self.prediction_btn.clicked.connect(self.run_trend_prediction)
        tools_layout.addWidget(self.prediction_btn, 1, 0)

        # 异常检测
        self.anomaly_btn = QPushButton("🚨 异常检测")
        self.anomaly_btn.clicked.connect(self.run_anomaly_detection)
        tools_layout.addWidget(self.anomaly_btn, 1, 1)

        # 优化建议
        self.optimization_btn = QPushButton("💡 优化建议")
        self.optimization_btn.clicked.connect(self.generate_optimization_suggestions)
        tools_layout.addWidget(self.optimization_btn, 1, 2)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # 分析结果显示
        results_group = QGroupBox("📋 分析结果")
        results_layout = QVBoxLayout()

        self.results_tabs = QTabWidget()

        # 图表标签页
        if MATPLOTLIB_AVAILABLE:
            self.chart_widget = QWidget()
            chart_layout = QVBoxLayout(self.chart_widget)
            self.analysis_canvas = FigureCanvas(Figure(figsize=(12, 8)))
            chart_layout.addWidget(self.analysis_canvas)
            self.results_tabs.addTab(self.chart_widget, "📈 图表")

        # 详细数据标签页
        self.data_widget = QWidget()
        data_layout = QVBoxLayout(self.data_widget)
        self.data_table = QTableWidget()
        data_layout.addWidget(self.data_table)
        self.results_tabs.addTab(self.data_widget, "📊 数据")

        # 报告标签页
        self.report_widget = QWidget()
        report_layout = QVBoxLayout(self.report_widget)
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        report_layout.addWidget(self.report_text)
        self.results_tabs.addTab(self.report_widget, "📄 报告")

        results_layout.addWidget(self.results_tabs)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group, 1)

        # 应用样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #9b59b6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background: #9b59b6;
                color: white;
                border: none;
                padding: 12px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #8e44ad;
            }
        """)

    def run_bottleneck_analysis(self):
        """运行性能瓶颈分析"""
        self.report_text.setPlainText("正在分析性能瓶颈...\n\n")

        try:
            from core.services.deep_analysis_service import get_deep_analysis_service

            analysis_service = get_deep_analysis_service()
            bottlenecks = analysis_service.analyze_bottlenecks()

            if not bottlenecks:
                self.report_text.setPlainText("🐌 性能瓶颈分析报告\n\n暂无足够数据进行分析，请等待系统收集更多性能数据。")
                return

            # 生成分析报告
            analysis_result = "🐌 性能瓶颈分析报告\n\n"
            analysis_result += "📊 主要发现：\n"

            total_severe = sum(1 for b in bottlenecks if b.severity == "严重")
            total_moderate = sum(1 for b in bottlenecks if b.severity == "中等")

            if total_severe > 0:
                analysis_result += f"1. 发现 {total_severe} 个严重性能瓶颈\n"
            if total_moderate > 0:
                analysis_result += f"2. 发现 {total_moderate} 个中等性能瓶颈\n"

            analysis_result += f"3. 总共分析了 {len(bottlenecks)} 个性能组件\n\n"

            analysis_result += "🎯 瓶颈排名：\n"
            for i, bottleneck in enumerate(bottlenecks[:5], 1):
                analysis_result += f"{i}. {bottleneck.component} - 平均耗时: {bottleneck.avg_duration:.3f}秒 "
                analysis_result += f"(占比: {bottleneck.percentage:.1f}%, {bottleneck.severity})\n"

            analysis_result += "\n💡 优化建议：\n"
            suggestions = analysis_service.generate_optimization_suggestions()

            for i, suggestion in enumerate(suggestions.get('high_priority', [])[:3], 1):
                analysis_result += f"{i}. {suggestion['suggestion']}\n"

            self.report_text.setPlainText(analysis_result)

        except Exception as e:
            logger.error(f"性能瓶颈分析失败: {e}")
            self.report_text.setPlainText(f"🐌 性能瓶颈分析报告\n\n分析失败: {e}\n\n请检查系统配置和数据收集状态。")

    def show_operation_ranking(self):
        """显示操作耗时排行"""
        try:
            from core.services.deep_analysis_service import get_deep_analysis_service

            analysis_service = get_deep_analysis_service()
            operations = analysis_service.get_operation_ranking()

            if not operations:
                # 如果没有真实数据，显示提示信息
                self.data_table.setRowCount(1)
                self.data_table.setColumnCount(3)
                self.data_table.setHorizontalHeaderLabels(["操作名称", "平均耗时(ms)", "调用次数"])
                self.data_table.setItem(0, 0, QTableWidgetItem("暂无数据"))
                self.data_table.setItem(0, 1, QTableWidgetItem("0"))
                self.data_table.setItem(0, 2, QTableWidgetItem("0"))
            else:
                self.data_table.setRowCount(len(operations))
                self.data_table.setColumnCount(3)
                self.data_table.setHorizontalHeaderLabels(["操作名称", "平均耗时(ms)", "调用次数"])

                for row, (name, duration, count) in enumerate(operations):
                    self.data_table.setItem(row, 0, QTableWidgetItem(name))
                    self.data_table.setItem(row, 1, QTableWidgetItem(f"{duration:.2f}"))
                    self.data_table.setItem(row, 2, QTableWidgetItem(str(count)))

                    # 根据耗时设置颜色
                    if duration > 1000:  # 超过1秒
                        for col in range(3):
                            item = self.data_table.item(row, col)
                            if item:
                                item.setBackground(QColor('#ffebee'))  # 浅红色
                    elif duration > 500:  # 超过500ms
                        for col in range(3):
                            item = self.data_table.item(row, col)
                            if item:
                                item.setBackground(QColor('#fff3e0'))  # 浅橙色

            self.data_table.resizeColumnsToContents()
            self.results_tabs.setCurrentWidget(self.data_widget)

        except Exception as e:
            logger.error(f"获取操作排行失败: {e}")
            # 显示错误信息
            self.data_table.setRowCount(1)
            self.data_table.setColumnCount(3)
            self.data_table.setHorizontalHeaderLabels(["操作名称", "平均耗时(ms)", "调用次数"])
            self.data_table.setItem(0, 0, QTableWidgetItem(f"加载失败: {e}"))
            self.data_table.setItem(0, 1, QTableWidgetItem("0"))
            self.data_table.setItem(0, 2, QTableWidgetItem("0"))

    def run_performance_comparison(self):
        """运行性能对比分析"""
        if MATPLOTLIB_AVAILABLE:
            try:
                from core.services.deep_analysis_service import get_deep_analysis_service

                analysis_service = get_deep_analysis_service()
                comparison_data = analysis_service.get_performance_comparison(days=7)

                ax = self.analysis_canvas.figure.subplots()
                ax.clear()

                if not comparison_data:
                    ax.text(0.5, 0.5, '暂无足够数据进行对比分析\n请等待系统收集更多数据',
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes, fontsize=14)
                    ax.set_title('性能对比分析')
                    self.analysis_canvas.draw()
                    self.results_tabs.setCurrentWidget(self.chart_widget)
                    return

                # 选择主要指标进行对比
                main_metrics = ['cpu_usage', 'memory_usage', 'response_time']
                available_metrics = [m for m in main_metrics if m in comparison_data and comparison_data[m]]

                if not available_metrics:
                    ax.text(0.5, 0.5, '暂无可用的性能指标数据',
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes, fontsize=14)
                    ax.set_title('性能对比分析')
                    self.analysis_canvas.draw()
                    self.results_tabs.setCurrentWidget(self.chart_widget)
                    return

                # 生成时间标签
                days_count = len(comparison_data[available_metrics[0]])
                periods = [f'{i+1}天前' for i in range(days_count-1, -1, -1)]

                x = range(len(periods))
                width = 0.25
                colors = ['#e74c3c', '#f39c12', '#3498db', '#2ecc71', '#9b59b6']

                # 绘制对比图表
                for i, metric in enumerate(available_metrics[:3]):  # 最多显示3个指标
                    values = comparison_data[metric]

                    # 根据指标类型调整显示
                    if metric == 'response_time':
                        # 响应时间转换为毫秒并放大显示
                        values = [v * 1000 for v in values]
                        label = '响应时间(ms)'
                    elif 'usage' in metric:
                        label = f'{metric.replace("_", " ").title()}(%)'
                    else:
                        label = metric.replace('_', ' ').title()

                    offset = (i - 1) * width
                    ax.bar([pos + offset for pos in x], values, width,
                           label=label, color=colors[i % len(colors)])

                ax.set_xlabel('时间周期')
                ax.set_ylabel('性能指标')
                ax.set_title('性能对比分析')
                ax.set_xticks(x)
                ax.set_xticklabels(periods)

                # 🎨 修复：设置图例文本颜色与条形图颜色一致
                legend = ax.legend()
                for i, text in enumerate(legend.get_texts()):
                    if i < len(colors):
                        text.set_color(colors[i % len(colors)])

                ax.grid(True, alpha=0.3)

                self.analysis_canvas.draw()
                self.results_tabs.setCurrentWidget(self.chart_widget)

            except Exception as e:
                logger.error(f"性能对比分析失败: {e}")
                if MATPLOTLIB_AVAILABLE:
                    ax = self.analysis_canvas.figure.subplots()
                    ax.clear()
                    ax.text(0.5, 0.5, f'分析失败: {e}',
                            horizontalalignment='center', verticalalignment='center',
                            transform=ax.transAxes, fontsize=12)
                    ax.set_title('性能对比分析')
                    self.analysis_canvas.draw()
                    self.results_tabs.setCurrentWidget(self.chart_widget)

    def run_trend_prediction(self):
        """运行趋势预测"""
        try:
            from core.services.deep_analysis_service import get_deep_analysis_service

            analysis_service = get_deep_analysis_service()
            trends = analysis_service.predict_trends(hours=24)

            if not trends:
                self.report_text.setPlainText("🔮 性能趋势预测报告\n\n暂无足够数据进行趋势预测，请等待系统收集更多性能数据。")
                return

            report = "🔮 性能趋势预测报告\n\n"

            # 分析各个指标的趋势
            for metric_name, trend_data in trends.items():
                current = trend_data['current']
                next_week = trend_data['next_week']
                next_month = trend_data['next_month']
                trend_rate = trend_data['trend_rate']

                # 格式化指标名称
                display_name = metric_name.replace('_', ' ').title()
                if 'usage' in metric_name.lower():
                    unit = '%'
                    format_str = "{:.1f}{}"
                elif 'time' in metric_name.lower():
                    unit = '秒'
                    format_str = "{:.3f}{}"
                else:
                    unit = ''
                    format_str = "{:.2f}{}"

                report += f"📈 {display_name}趋势：\n"
                report += f"- 当前平均: {format_str.format(current, unit)}\n"

                # 计算变化
                week_change = next_week - current
                month_change = next_month - current

                week_symbol = "↑" if week_change > 0 else "↓" if week_change < 0 else "→"
                month_symbol = "↑" if month_change > 0 else "↓" if month_change < 0 else "→"

                report += f"- 预测下周: {format_str.format(next_week, unit)} ({week_symbol}{abs(week_change):.1f}{unit})\n"
                report += f"- 预测下月: {format_str.format(next_month, unit)} ({month_symbol}{abs(month_change):.1f}{unit})\n\n"

            # 生成关键预测
            report += "🎯 关键预测：\n"
            prediction_count = 0

            for metric_name, trend_data in trends.items():
                if prediction_count >= 3:
                    break

                trend_rate = trend_data['trend_rate']
                display_name = metric_name.replace('_', ' ')

                if abs(trend_rate) > 0.1:  # 显著趋势
                    if trend_rate > 0:
                        report += f"{prediction_count + 1}. {display_name}呈上升趋势，需要关注\n"
                    else:
                        report += f"{prediction_count + 1}. {display_name}呈下降趋势，情况良好\n"
                    prediction_count += 1

            if prediction_count == 0:
                report += "1. 各项指标趋势相对稳定\n"

            # 风险提醒
            report += "\n⚠️ 风险提醒：\n"
            risk_count = 0

            for metric_name, trend_data in trends.items():
                current = trend_data['current']
                next_week = trend_data['next_week']

                if 'cpu' in metric_name.lower() and next_week > 80:
                    report += f"- CPU使用率预测将达到{next_week:.1f}%，建议优化性能\n"
                    risk_count += 1
                elif 'memory' in metric_name.lower() and next_week > 85:
                    report += f"- 内存使用率预测将达到{next_week:.1f}%，建议检查内存泄漏\n"
                    risk_count += 1
                elif 'response_time' in metric_name.lower() and next_week > 3:
                    report += f"- 响应时间预测将达到{next_week:.2f}秒，建议优化查询性能\n"
                    risk_count += 1

            if risk_count == 0:
                report += "- 暂无明显风险，系统运行状态良好\n"

            self.report_text.setPlainText(report)

        except Exception as e:
            logger.error(f"趋势预测失败: {e}")
            self.report_text.setPlainText(f"🔮 性能趋势预测报告\n\n预测失败: {e}\n\n请检查系统配置和数据收集状态。")

    def run_anomaly_detection(self):
        """运行异常检测"""
        try:
            from core.services.deep_analysis_service import get_deep_analysis_service

            analysis_service = get_deep_analysis_service()
            anomalies = analysis_service.detect_anomalies(hours=24)

            report = "🚨 异常检测报告\n\n"

            if not anomalies:
                report += "🔍 检测结果：\n\n✅ 在过去24小时内未检测到明显异常\n\n"
                report += "📊 系统状态：正常运行\n"
                report += "💡 建议：继续保持当前的监控和维护策略"
                self.report_text.setPlainText(report)
                return

            # 按严重程度分组
            severe_anomalies = [a for a in anomalies if a.severity == "严重"]
            moderate_anomalies = [a for a in anomalies if a.severity == "中等"]

            report += "🔍 检测到的异常：\n\n"

            # 显示严重异常
            for i, anomaly in enumerate(severe_anomalies[:3], 1):
                report += f"{i}. 【高优先级】{anomaly.description}\n"
                report += f"   - 时间: {anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                report += f"   - 当前值: {anomaly.value:.2f}\n"
                report += f"   - 阈值: {anomaly.threshold:.2f}\n"
                report += f"   - 指标: {anomaly.metric_name}\n\n"

            # 显示中等异常
            for i, anomaly in enumerate(moderate_anomalies[:2], len(severe_anomalies) + 1):
                report += f"{i}. 【中优先级】{anomaly.description}\n"
                report += f"   - 时间: {anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                report += f"   - 当前值: {anomaly.value:.2f}\n"
                report += f"   - 阈值: {anomaly.threshold:.2f}\n\n"

            # 异常统计
            report += "📊 异常统计：\n"
            report += f"- 过去24小时异常事件: {len(anomalies)}次\n"
            report += f"- 严重异常: {len(severe_anomalies)}次\n"
            report += f"- 中等异常: {len(moderate_anomalies)}次\n\n"

            # 按指标分组统计
            metric_counts = {}
            for anomaly in anomalies:
                metric_counts[anomaly.metric_name] = metric_counts.get(anomaly.metric_name, 0) + 1

            if metric_counts:
                report += "📈 异常分布：\n"
                for metric, count in sorted(metric_counts.items(), key=lambda x: x[1], reverse=True):
                    report += f"- {metric}: {count}次\n"
                report += "\n"

            # 建议措施
            report += "💡 建议措施：\n"
            suggestion_count = 0

            for metric_name in metric_counts.keys():
                if suggestion_count >= 3:
                    break

                if 'cpu' in metric_name.lower():
                    report += f"{suggestion_count + 1}. 优化CPU使用率：检查高耗时操作，优化算法复杂度\n"
                elif 'memory' in metric_name.lower():
                    report += f"{suggestion_count + 1}. 优化内存使用：检查内存泄漏，优化缓存策略\n"
                elif 'response_time' in metric_name.lower():
                    report += f"{suggestion_count + 1}. 优化响应时间：检查数据库查询，减少网络延迟\n"
                else:
                    report += f"{suggestion_count + 1}. 监控{metric_name}指标，分析异常原因\n"

                suggestion_count += 1

            if suggestion_count == 0:
                report += "1. 继续监控系统状态，保持当前配置\n"

            self.report_text.setPlainText(report)

        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            self.report_text.setPlainText(f"🚨 异常检测报告\n\n检测失败: {e}\n\n请检查系统配置和数据收集状态。")

    def generate_optimization_suggestions(self):
        """生成优化建议"""
        try:
            from core.services.deep_analysis_service import get_deep_analysis_service

            analysis_service = get_deep_analysis_service()
            suggestions = analysis_service.generate_optimization_suggestions()

            report = "💡 系统优化建议报告\n\n"

            # 高优先级优化项
            high_priority = suggestions.get('high_priority', [])
            if high_priority:
                report += "🎯 高优先级优化项：\n\n"
                for i, suggestion in enumerate(high_priority, 1):
                    report += f"{i}. 【{suggestion['component']}优化】\n"
                    report += f"   - 问题: {suggestion['issue']}\n"
                    report += f"   - 建议: {suggestion['suggestion']}\n"
                    report += f"   - {suggestion['improvement']}\n\n"

            # 中优先级优化项
            medium_priority = suggestions.get('medium_priority', [])
            if medium_priority:
                report += "🔧 中优先级优化项：\n\n"
                for i, suggestion in enumerate(medium_priority, 1):
                    report += f"{i}. 【{suggestion['component']}优化】\n"
                    report += f"   - 问题: {suggestion['issue']}\n"
                    report += f"   - 建议: {suggestion['suggestion']}\n"
                    report += f"   - {suggestion['improvement']}\n\n"

            # 低优先级优化项
            low_priority = suggestions.get('low_priority', [])
            if low_priority:
                report += "📋 低优先级优化项：\n\n"
                for i, suggestion in enumerate(low_priority[:3], 1):  # 只显示前3个
                    report += f"{i}. 【{suggestion['component']}优化】\n"
                    report += f"   - 建议: {suggestion['suggestion']}\n"
                    report += f"   - {suggestion['improvement']}\n\n"

            # 如果没有具体建议，提供通用建议
            if not high_priority and not medium_priority and not low_priority:
                report += "🎯 通用优化建议：\n\n"
                report += "1. 【性能监控】\n"
                report += "   - 继续收集性能数据\n"
                report += "   - 建立性能基线\n"
                report += "   - 预计监控效果: 显著提升\n\n"

                report += "2. 【系统维护】\n"
                report += "   - 定期清理日志文件\n"
                report += "   - 更新系统依赖\n"
                report += "   - 预计稳定性提升: 良好\n\n"

                report += "3. 【代码优化】\n"
                report += "   - 代码审查和重构\n"
                report += "   - 单元测试覆盖\n"
                report += "   - 预计质量提升: 显著\n\n"

            # 预期收益总结
            report += "📈 预期收益：\n"
            total_suggestions = len(high_priority) + len(medium_priority) + len(low_priority)

            if total_suggestions > 0:
                if len(high_priority) > 2:
                    report += "- 整体性能提升: 50-70%\n"
                    report += "- 系统稳定性: 大幅增强\n"
                elif len(high_priority) > 0:
                    report += "- 整体性能提升: 30-50%\n"
                    report += "- 系统稳定性: 显著增强\n"
                else:
                    report += "- 整体性能提升: 15-30%\n"
                    report += "- 系统稳定性: 适度增强\n"

                report += "- 用户体验改善: 明显提升\n"
                report += "- 维护成本降低: 有效减少\n\n"
            else:
                report += "- 系统当前运行良好\n"
                report += "- 建议保持现有配置\n"
                report += "- 继续监控性能指标\n\n"

            # 实施时间表
            report += "⏰ 实施建议：\n"
            if high_priority:
                report += "- 第1-2周: 优先处理高优先级问题\n"
            if medium_priority:
                report += "- 第3-4周: 处理中优先级优化项\n"
            if low_priority:
                report += "- 第5-6周: 考虑低优先级改进\n"

            if not (high_priority or medium_priority or low_priority):
                report += "- 持续监控: 保持当前良好状态\n"
                report += "- 定期评估: 每月进行性能评估\n"

            self.report_text.setPlainText(report)

        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            self.report_text.setPlainText(f"💡 系统优化建议报告\n\n生成失败: {e}\n\n请检查系统配置和数据收集状态。")
