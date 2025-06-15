"""
情绪分析标签页模块
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


class SentimentAnalysisTab(BaseAnalysisTab):
    """情绪分析标签页"""

    # 定义信号
    sentiment_analysis_completed = pyqtSignal(dict)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)
        self.sentiment_results = []
        self.sentiment_statistics = {}
        self.sentiment_history = []

    def create_ui(self):
        """创建情绪分析UI"""
        layout = QVBoxLayout(self)

        # 情绪指标选择区域
        indicators_group = self.create_indicators_section()
        layout.addWidget(indicators_group)

        # 参数配置区域
        params_group = self.create_params_section()
        layout.addWidget(params_group)

        # 分析控制区域
        control_group = self.create_control_section()
        layout.addWidget(control_group)

        # 结果显示区域
        results_group = self.create_results_section()
        layout.addWidget(results_group)

    def create_indicators_section(self):
        """创建情绪指标选择区域"""
        indicators_group = QGroupBox("情绪指标选择")
        layout = QGridLayout(indicators_group)

        # VIX恐慌指数
        self.vix_cb = QCheckBox("VIX恐慌指数")
        self.vix_cb.setChecked(True)
        self.vix_cb.setToolTip("衡量市场恐慌程度的指标")
        layout.addWidget(self.vix_cb, 0, 0)

        # 贪婪恐惧指数
        self.fear_greed_cb = QCheckBox("贪婪恐惧指数")
        self.fear_greed_cb.setChecked(True)
        self.fear_greed_cb.setToolTip("综合多个指标的市场情绪指数")
        layout.addWidget(self.fear_greed_cb, 0, 1)

        # 投资者情绪指数
        self.investor_sentiment_cb = QCheckBox("投资者情绪指数")
        self.investor_sentiment_cb.setChecked(True)
        self.investor_sentiment_cb.setToolTip("基于调查数据的投资者情绪")
        layout.addWidget(self.investor_sentiment_cb, 0, 2)

        # 新闻情绪分析
        self.news_sentiment_cb = QCheckBox("新闻情绪分析")
        self.news_sentiment_cb.setChecked(False)
        self.news_sentiment_cb.setToolTip("基于新闻文本的情绪分析")
        layout.addWidget(self.news_sentiment_cb, 1, 0)

        # 社交媒体情绪
        self.social_sentiment_cb = QCheckBox("社交媒体情绪")
        self.social_sentiment_cb.setChecked(False)
        self.social_sentiment_cb.setToolTip("基于社交媒体的情绪分析")
        layout.addWidget(self.social_sentiment_cb, 1, 1)

        # 技术指标情绪
        self.technical_sentiment_cb = QCheckBox("技术指标情绪")
        self.technical_sentiment_cb.setChecked(True)
        self.technical_sentiment_cb.setToolTip("基于技术指标的情绪判断")
        layout.addWidget(self.technical_sentiment_cb, 1, 2)

        return indicators_group

    def create_params_section(self):
        """创建参数配置区域"""
        params_group = QGroupBox("情绪分析参数")
        layout = QGridLayout(params_group)

        # 分析周期
        layout.addWidget(QLabel("分析周期:"), 0, 0)
        self.period_spin = QSpinBox()
        self.period_spin.setRange(5, 250)
        self.period_spin.setValue(30)
        self.period_spin.setSuffix(" 天")
        layout.addWidget(self.period_spin, 0, 1)

        # 情绪敏感度
        layout.addWidget(QLabel("情绪敏感度:"), 0, 2)
        self.sensitivity_spin = QDoubleSpinBox()
        self.sensitivity_spin.setRange(0.1, 3.0)
        self.sensitivity_spin.setValue(1.0)
        self.sensitivity_spin.setDecimals(1)
        layout.addWidget(self.sensitivity_spin, 0, 3)

        # 情绪阈值
        layout.addWidget(QLabel("极端情绪阈值:"), 1, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 0.9)
        self.threshold_spin.setValue(0.7)
        self.threshold_spin.setDecimals(2)
        layout.addWidget(self.threshold_spin, 1, 1)

        # 平滑参数
        layout.addWidget(QLabel("平滑参数:"), 1, 2)
        self.smooth_spin = QSpinBox()
        self.smooth_spin.setRange(1, 20)
        self.smooth_spin.setValue(5)
        layout.addWidget(self.smooth_spin, 1, 3)

        return params_group

    def create_control_section(self):
        """创建分析控制区域"""
        control_group = QGroupBox("情绪分析控制")
        layout = QHBoxLayout(control_group)

        # 开始分析按钮
        analyze_btn = QPushButton("开始情绪分析")
        analyze_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        analyze_btn.clicked.connect(self.analyze_sentiment)
        layout.addWidget(analyze_btn)

        # 历史分析按钮
        history_btn = QPushButton("历史情绪分析")
        history_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; }")
        history_btn.clicked.connect(self.analyze_history)
        layout.addWidget(history_btn)

        # 清除结果按钮
        clear_btn = QPushButton("清除结果")
        clear_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        clear_btn.clicked.connect(self.clear_sentiment)
        layout.addWidget(clear_btn)

        # 导出结果按钮
        export_btn = QPushButton("导出情绪分析")
        export_btn.setStyleSheet("QPushButton { background-color: #6f42c1; color: white; }")
        export_btn.clicked.connect(self.export_sentiment_analysis)
        layout.addWidget(export_btn)

        layout.addStretch()
        return control_group

    def create_results_section(self):
        """创建结果显示区域"""
        results_group = QGroupBox("情绪分析结果")
        layout = QVBoxLayout(results_group)

        # 当前情绪状态
        current_group = QGroupBox("当前市场情绪")
        current_layout = QHBoxLayout(current_group)

        # 情绪指数
        sentiment_card = QFrame()
        sentiment_card.setFrameStyle(QFrame.StyledPanel)
        sentiment_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        sentiment_layout = QVBoxLayout(sentiment_card)
        sentiment_layout.addWidget(QLabel("情绪指数"))

        self.sentiment_index_label = QLabel("50")
        self.sentiment_index_label.setAlignment(Qt.AlignCenter)
        self.sentiment_index_label.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; color: #007bff; }")
        sentiment_layout.addWidget(self.sentiment_index_label)

        current_layout.addWidget(sentiment_card)

        # 情绪状态
        status_card = QFrame()
        status_card.setFrameStyle(QFrame.StyledPanel)
        status_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        status_layout = QVBoxLayout(status_card)
        status_layout.addWidget(QLabel("情绪状态"))

        self.sentiment_status_label = QLabel("中性")
        self.sentiment_status_label.setAlignment(Qt.AlignCenter)
        self.sentiment_status_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #6c757d; }")
        status_layout.addWidget(self.sentiment_status_label)

        current_layout.addWidget(status_card)

        # 变化趋势
        trend_card = QFrame()
        trend_card.setFrameStyle(QFrame.StyledPanel)
        trend_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.addWidget(QLabel("变化趋势"))

        self.sentiment_trend_label = QLabel("稳定")
        self.sentiment_trend_label.setAlignment(Qt.AlignCenter)
        self.sentiment_trend_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")
        trend_layout.addWidget(self.sentiment_trend_label)

        current_layout.addWidget(trend_card)

        # 预警等级
        alert_card = QFrame()
        alert_card.setFrameStyle(QFrame.StyledPanel)
        alert_card.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }")
        alert_layout = QVBoxLayout(alert_card)
        alert_layout.addWidget(QLabel("预警等级"))

        self.sentiment_alert_label = QLabel("正常")
        self.sentiment_alert_label.setAlignment(Qt.AlignCenter)
        self.sentiment_alert_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")
        alert_layout.addWidget(self.sentiment_alert_label)

        current_layout.addWidget(alert_card)

        layout.addWidget(current_group)

        # 详细分析结果
        details_group = QGroupBox("详细分析结果")
        details_layout = QVBoxLayout(details_group)

        self.sentiment_table = QTableWidget()
        self.sentiment_table.setColumnCount(6)
        self.sentiment_table.setHorizontalHeaderLabels([
            "指标名称", "当前值", "历史均值", "情绪状态", "变化趋势", "影响权重"
        ])
        self.sentiment_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sentiment_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sentiment_table.setAlternatingRowColors(True)
        self.sentiment_table.setSortingEnabled(True)

        details_layout.addWidget(self.sentiment_table)
        layout.addWidget(details_group)

        return results_group

    def analyze_sentiment(self):
        """执行情绪分析"""
        if self.current_kdata is None:
            QMessageBox.warning(self, "警告", "请先设置K线数据")
            return

        try:
            self.show_loading("正在进行情绪分析...")

            # 获取参数
            period = self.period_spin.value()
            sensitivity = self.sensitivity_spin.value()
            threshold = self.threshold_spin.value()
            smooth = self.smooth_spin.value()

            # 执行分析
            self.sentiment_results = []
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 分析各种情绪指标
            if self.vix_cb.isChecked():
                self.analyze_vix_sentiment(period, sensitivity)

            if self.fear_greed_cb.isChecked():
                self.analyze_fear_greed_sentiment(period, sensitivity)

            if self.investor_sentiment_cb.isChecked():
                self.analyze_investor_sentiment(period, sensitivity)

            if self.technical_sentiment_cb.isChecked():
                self.analyze_technical_sentiment(period, sensitivity)

            if self.news_sentiment_cb.isChecked():
                self.analyze_news_sentiment(period, sensitivity)

            if self.social_sentiment_cb.isChecked():
                self.analyze_social_sentiment(period, sensitivity)

            # 计算综合情绪指数
            self.calculate_composite_sentiment()

            # 更新显示
            self.update_sentiment_display()
            self.update_sentiment_statistics()

            # 发送完成信号
            self.sentiment_analysis_completed.emit({
                'results': self.sentiment_results,
                'statistics': self.sentiment_statistics
            })

        except Exception as e:
            self.log_manager.error(f"情绪分析失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"情绪分析失败: {str(e)}")
        finally:
            self.hide_loading()

    def analyze_vix_sentiment(self, period: int, sensitivity: float):
        """分析VIX恐慌指数"""
        try:
            # 模拟VIX数据（实际应用中应从数据源获取）
            current_vix = random.uniform(15, 35)
            historical_avg = 20.0

            # 判断情绪状态
            if current_vix > 30:
                status = "极度恐慌"
                trend = "恐慌上升"
            elif current_vix > 25:
                status = "恐慌"
                trend = "恐慌"
            elif current_vix < 15:
                status = "极度贪婪"
                trend = "贪婪上升"
            else:
                status = "正常"
                trend = "稳定"

            self.sentiment_results.append({
                '指标名称': 'VIX恐慌指数',
                '当前值': f"{current_vix:.2f}",
                '历史均值': f"{historical_avg:.2f}",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "25%"
            })

        except Exception as e:
            self.log_manager.error(f"VIX情绪分析失败: {str(e)}")

    def analyze_fear_greed_sentiment(self, period: int, sensitivity: float):
        """分析贪婪恐惧指数"""
        try:
            # 模拟贪婪恐惧指数
            current_index = random.uniform(0, 100)

            if current_index > 75:
                status = "极度贪婪"
                trend = "贪婪"
            elif current_index > 55:
                status = "贪婪"
                trend = "乐观"
            elif current_index < 25:
                status = "极度恐惧"
                trend = "恐慌"
            elif current_index < 45:
                status = "恐惧"
                trend = "悲观"
            else:
                status = "中性"
                trend = "稳定"

            self.sentiment_results.append({
                '指标名称': '贪婪恐惧指数',
                '当前值': f"{current_index:.0f}",
                '历史均值': "50",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "30%"
            })

        except Exception as e:
            self.log_manager.error(f"贪婪恐惧指数分析失败: {str(e)}")

    def analyze_investor_sentiment(self, period: int, sensitivity: float):
        """分析投资者情绪指数"""
        try:
            # 模拟投资者情绪调查数据
            bullish_pct = random.uniform(20, 80)
            bearish_pct = random.uniform(20, 80)
            neutral_pct = 100 - bullish_pct - bearish_pct

            if bullish_pct > 60:
                status = "过度乐观"
                trend = "看涨情绪高涨"
            elif bearish_pct > 60:
                status = "过度悲观"
                trend = "看跌情绪浓厚"
            else:
                status = "理性"
                trend = "情绪平衡"

            self.sentiment_results.append({
                '指标名称': '投资者情绪指数',
                '当前值': f"看涨{bullish_pct:.0f}%",
                '历史均值': "看涨50%",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "20%"
            })

        except Exception as e:
            self.log_manager.error(f"投资者情绪分析失败: {str(e)}")

    def analyze_technical_sentiment(self, period: int, sensitivity: float):
        """分析技术指标情绪"""
        try:
            if self.current_kdata is None:
                return

            close_prices = self.current_kdata['close']
            volume = self.current_kdata['volume']

            # 计算技术指标情绪
            # RSI情绪
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]

            # MACD情绪
            exp1 = close_prices.ewm(span=12).mean()
            exp2 = close_prices.ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            current_macd = macd.iloc[-1] - signal.iloc[-1]

            # 综合技术情绪
            if current_rsi > 70 and current_macd > 0:
                status = "技术超买"
                trend = "技术看涨但需谨慎"
            elif current_rsi < 30 and current_macd < 0:
                status = "技术超卖"
                trend = "技术看跌但可能反弹"
            elif current_macd > 0:
                status = "技术乐观"
                trend = "技术向好"
            elif current_macd < 0:
                status = "技术悲观"
                trend = "技术走弱"
            else:
                status = "技术中性"
                trend = "技术震荡"

            self.sentiment_results.append({
                '指标名称': '技术指标情绪',
                '当前值': f"RSI:{current_rsi:.1f}",
                '历史均值': "RSI:50",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "15%"
            })

        except Exception as e:
            self.log_manager.error(f"技术指标情绪分析失败: {str(e)}")

    def analyze_news_sentiment(self, period: int, sensitivity: float):
        """分析新闻情绪"""
        try:
            # 模拟新闻情绪分析结果
            positive_news = random.uniform(0, 100)
            negative_news = random.uniform(0, 100)
            neutral_news = 100 - positive_news - negative_news

            if positive_news > 60:
                status = "新闻乐观"
                trend = "正面消息较多"
            elif negative_news > 60:
                status = "新闻悲观"
                trend = "负面消息较多"
            else:
                status = "新闻中性"
                trend = "消息面平衡"

            self.sentiment_results.append({
                '指标名称': '新闻情绪分析',
                '当前值': f"正面{positive_news:.0f}%",
                '历史均值': "正面50%",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "5%"
            })

        except Exception as e:
            self.log_manager.error(f"新闻情绪分析失败: {str(e)}")

    def analyze_social_sentiment(self, period: int, sensitivity: float):
        """分析社交媒体情绪"""
        try:
            # 模拟社交媒体情绪分析结果
            social_score = random.uniform(-1, 1)

            if social_score > 0.5:
                status = "社交乐观"
                trend = "网络情绪积极"
            elif social_score < -0.5:
                status = "社交悲观"
                trend = "网络情绪消极"
            else:
                status = "社交中性"
                trend = "网络情绪平稳"

            self.sentiment_results.append({
                '指标名称': '社交媒体情绪',
                '当前值': f"{social_score:.2f}",
                '历史均值': "0.00",
                '情绪状态': status,
                '变化趋势': trend,
                '影响权重': "5%"
            })

        except Exception as e:
            self.log_manager.error(f"社交媒体情绪分析失败: {str(e)}")

    def calculate_composite_sentiment(self):
        """计算综合情绪指数"""
        try:
            if not self.sentiment_results:
                return

            # 权重映射
            weights = {
                'VIX恐慌指数': 0.25,
                '贪婪恐惧指数': 0.30,
                '投资者情绪指数': 0.20,
                '技术指标情绪': 0.15,
                '新闻情绪分析': 0.05,
                '社交媒体情绪': 0.05
            }

            # 情绪状态评分映射
            status_scores = {
                '极度恐慌': 10, '恐慌': 25, '悲观': 35, '过度悲观': 20,
                '中性': 50, '正常': 50, '理性': 50, '技术中性': 50, '新闻中性': 50, '社交中性': 50,
                '乐观': 65, '技术乐观': 65, '新闻乐观': 65, '社交乐观': 65,
                '贪婪': 75, '过度乐观': 80, '极度贪婪': 90,
                '技术超买': 85, '技术超卖': 15
            }

            total_score = 0
            total_weight = 0

            for result in self.sentiment_results:
                indicator = result['指标名称']
                status = result['情绪状态']
                weight = weights.get(indicator, 0.1)

                score = status_scores.get(status, 50)
                total_score += score * weight
                total_weight += weight

            # 计算综合情绪指数
            if total_weight > 0:
                composite_index = total_score / total_weight
            else:
                composite_index = 50

            # 更新显示
            self.sentiment_index_label.setText(f"{composite_index:.0f}")

            # 设置情绪状态
            if composite_index > 80:
                status = "极度贪婪"
                color = "#dc3545"
            elif composite_index > 65:
                status = "贪婪"
                color = "#fd7e14"
            elif composite_index > 55:
                status = "乐观"
                color = "#28a745"
            elif composite_index < 20:
                status = "极度恐慌"
                color = "#6f42c1"
            elif composite_index < 35:
                status = "恐慌"
                color = "#dc3545"
            elif composite_index < 45:
                status = "悲观"
                color = "#ffc107"
            else:
                status = "中性"
                color = "#6c757d"

            self.sentiment_status_label.setText(status)
            self.sentiment_status_label.setStyleSheet(f"QLabel {{ font-size: 18px; font-weight: bold; color: {color}; }}")

            # 设置预警等级
            if composite_index > 85 or composite_index < 15:
                alert = "高风险"
                alert_color = "#dc3545"
            elif composite_index > 75 or composite_index < 25:
                alert = "中风险"
                alert_color = "#ffc107"
            else:
                alert = "正常"
                alert_color = "#28a745"

            self.sentiment_alert_label.setText(alert)
            self.sentiment_alert_label.setStyleSheet(f"QLabel {{ font-size: 18px; font-weight: bold; color: {alert_color}; }}")

        except Exception as e:
            self.log_manager.error(f"计算综合情绪指数失败: {str(e)}")

    def analyze_history(self):
        """分析历史情绪"""
        try:
            self.show_loading("正在分析历史情绪...")

            # 模拟历史情绪数据
            self.sentiment_history = []

            for i in range(30):  # 30天历史数据
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                sentiment_index = random.uniform(20, 80)

                self.sentiment_history.append({
                    'date': date,
                    'sentiment_index': sentiment_index,
                    'vix': random.uniform(15, 35),
                    'fear_greed': random.uniform(20, 80)
                })

            QMessageBox.information(self, "完成", "历史情绪分析完成")

        except Exception as e:
            self.log_manager.error(f"历史情绪分析失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"历史情绪分析失败: {str(e)}")
        finally:
            self.hide_loading()

    def update_sentiment_display(self):
        """更新情绪分析显示"""
        try:
            self.sentiment_table.setRowCount(len(self.sentiment_results))

            for i, result in enumerate(self.sentiment_results):
                self.sentiment_table.setItem(i, 0, QTableWidgetItem(result['指标名称']))
                self.sentiment_table.setItem(i, 1, QTableWidgetItem(result['当前值']))
                self.sentiment_table.setItem(i, 2, QTableWidgetItem(result['历史均值']))

                # 情绪状态带颜色显示
                status_item = QTableWidgetItem(result['情绪状态'])
                if '恐慌' in result['情绪状态'] or '悲观' in result['情绪状态']:
                    status_item.setForeground(QColor("red"))
                elif '贪婪' in result['情绪状态'] or '乐观' in result['情绪状态']:
                    status_item.setForeground(QColor("green"))
                else:
                    status_item.setForeground(QColor("gray"))

                self.sentiment_table.setItem(i, 3, status_item)
                self.sentiment_table.setItem(i, 4, QTableWidgetItem(result['变化趋势']))
                self.sentiment_table.setItem(i, 5, QTableWidgetItem(result['影响权重']))

            self.sentiment_table.resizeColumnsToContents()

        except Exception as e:
            self.log_manager.error(f"更新情绪分析显示失败: {str(e)}")

    def update_sentiment_statistics(self):
        """更新情绪分析统计"""
        try:
            indicator_count = len(self.sentiment_results)

            # 统计各种情绪状态
            positive_count = sum(1 for r in self.sentiment_results
                                 if '乐观' in r['情绪状态'] or '贪婪' in r['情绪状态'])
            negative_count = sum(1 for r in self.sentiment_results
                                 if '悲观' in r['情绪状态'] or '恐慌' in r['情绪状态'])
            neutral_count = indicator_count - positive_count - negative_count

            self.sentiment_statistics = {
                'total_indicators': indicator_count,
                'positive_indicators': positive_count,
                'negative_indicators': negative_count,
                'neutral_indicators': neutral_count
            }

            # 设置变化趋势
            if positive_count > negative_count:
                trend = "上升"
                trend_color = "#28a745"
            elif negative_count > positive_count:
                trend = "下降"
                trend_color = "#dc3545"
            else:
                trend = "稳定"
                trend_color = "#6c757d"

            self.sentiment_trend_label.setText(trend)
            self.sentiment_trend_label.setStyleSheet(f"QLabel {{ font-size: 18px; font-weight: bold; color: {trend_color}; }}")

        except Exception as e:
            self.log_manager.error(f"更新情绪分析统计失败: {str(e)}")

    def clear_sentiment(self):
        """清除情绪分析结果"""
        self.sentiment_results = []
        self.sentiment_statistics = {}
        self.sentiment_history = []

        self.sentiment_table.setRowCount(0)
        self.sentiment_index_label.setText("50")
        self.sentiment_status_label.setText("中性")
        self.sentiment_trend_label.setText("稳定")
        self.sentiment_alert_label.setText("正常")

        # 重置样式
        self.sentiment_status_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #6c757d; }")
        self.sentiment_trend_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")
        self.sentiment_alert_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #28a745; }")

    def export_sentiment_analysis(self):
        """导出情绪分析结果"""
        try:
            if not self.sentiment_results:
                QMessageBox.warning(self, "警告", "没有可导出的情绪分析数据")
                return

            # 获取保存文件路径
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出情绪分析数据", f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON files (*.json)")

            if not filename:
                return

            # 导出数据
            export_data = {
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_type': '情绪分析',
                'stock_code': getattr(self.current_kdata, 'stock', {}).get('code', 'N/A') if self.current_kdata else 'N/A',
                'statistics': self.sentiment_statistics,
                'current_sentiment': {
                    'index': self.sentiment_index_label.text(),
                    'status': self.sentiment_status_label.text(),
                    'trend': self.sentiment_trend_label.text(),
                    'alert': self.sentiment_alert_label.text()
                },
                'indicators': self.sentiment_results,
                'history': self.sentiment_history
            }

            import json
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "成功", f"情绪分析数据已导出到: {filename}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def refresh_data(self):
        """刷新数据"""
        if self.current_kdata is not None:
            self.analyze_sentiment()

    def clear_data(self):
        """清除数据"""
        self.clear_sentiment()
