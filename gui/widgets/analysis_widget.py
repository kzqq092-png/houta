"""
分析控件模块
"""
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QComboBox, QPushButton, QSpinBox,
                             QDoubleSpinBox, QTableWidget, QTableWidgetItem,
                             QGroupBox, QFormLayout, QCheckBox, QColor)
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np
import random
from datetime import datetime, timedelta

from utils.logger import log_manager
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from hikyuu.indicator import (
    MA, MACD, KDJ, RSI, BOLL, CCI, ATR, OBV, WILLR, DMI, SAR,
    ROC, TRIX, MFI, ADX, BBANDS, AD, CMO, DX
)
from hikyuu.stock.sm.sm_block import sm
from hikyuu.query import Query


class AnalysisWidget(QWidget):
    """分析控件类"""

    # 定义信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    analysis_completed = pyqtSignal(dict)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化分析控件

        Args:
            config_manager: Optional ConfigManager instance to use
        """
        super().__init__()

        # 初始化变量
        self.current_stock = None
        self.current_kdata = None
        self.current_indicators = []

        # 初始化UI
        self.init_ui()

        # 应用主题
        self.theme_manager = get_theme_manager(
            config_manager or ConfigManager())
        self.theme_manager.apply_theme(self)

    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)

            # 创建标签页
            tab_widget = QTabWidget()

            # 添加技术分析标签页
            technical_tab = self.create_technical_tab()
            tab_widget.addTab(technical_tab, "技术分析")

            # 添加形态识别标签页
            pattern_tab = self.create_pattern_tab()
            tab_widget.addTab(pattern_tab, "形态识别")

            # 添加趋势分析标签页
            trend_tab = self.create_trend_tab()
            tab_widget.addTab(trend_tab, "趋势分析")

            # 添加波浪分析标签页
            wave_tab = self.create_wave_tab()
            tab_widget.addTab(wave_tab, "波浪分析")

            # 添加市场情绪标签页
            sentiment_tab = self.create_sentiment_tab()
            tab_widget.addTab(sentiment_tab, "市场情绪")

            # 添加板块资金流向分析标签页
            sector_flow_tab = self.create_sector_flow_tab()
            tab_widget.addTab(sector_flow_tab, "板块资金流向")

            # 添加热点分析标签页
            hotspot_tab = self.create_hotspot_tab()
            tab_widget.addTab(hotspot_tab, "热点分析")

            # 添加标签页到布局
            layout.addWidget(tab_widget)

        except Exception as e:
            log_manager.log(f"初始化分析控件UI失败: {str(e)}", "error")
            raise

    def create_technical_tab(self) -> QWidget:
        """创建技术分析标签页

        Returns:
            技术分析标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建指标选择组
            indicator_group = QGroupBox("指标选择")
            indicator_layout = QFormLayout()

            # 添加指标选择
            self.indicator_combo = QComboBox()
            self.indicator_combo.addItems([
                'MA', 'MACD', 'KDJ', 'RSI', 'BOLL', 'CCI', 'ATR', 'OBV',
                'WR', 'DMI', 'SAR', 'ROC', 'TRIX', 'MFI', 'ADX', 'BBW',
                'AD', 'CMO', 'DX', '综合分析'
            ])
            self.indicator_combo.currentTextChanged.connect(
                self.on_indicator_changed)
            indicator_layout.addRow("指标:", self.indicator_combo)

            # 添加MA参数
            self.ma_periods = []
            for i, period in enumerate([5, 10, 20, 30, 60, 120]):
                spin = QSpinBox()
                spin.setRange(1, 250)
                spin.setValue(period)
                self.ma_periods.append(spin)
                indicator_layout.addRow(f"MA{i+1}周期:", spin)

            # 添加MACD参数
            self.macd_short = QSpinBox()
            self.macd_short.setRange(1, 50)
            self.macd_short.setValue(12)
            indicator_layout.addRow("MACD快线:", self.macd_short)

            self.macd_long = QSpinBox()
            self.macd_long.setRange(1, 100)
            self.macd_long.setValue(26)
            indicator_layout.addRow("MACD慢线:", self.macd_long)

            self.macd_signal = QSpinBox()
            self.macd_signal.setRange(1, 50)
            self.macd_signal.setValue(9)
            indicator_layout.addRow("MACD信号:", self.macd_signal)

            # 添加KDJ参数
            self.kdj_n = QSpinBox()
            self.kdj_n.setRange(1, 90)
            self.kdj_n.setValue(9)
            indicator_layout.addRow("KDJ N:", self.kdj_n)

            self.kdj_m1 = QSpinBox()
            self.kdj_m1.setRange(1, 30)
            self.kdj_m1.setValue(3)
            indicator_layout.addRow("KDJ M1:", self.kdj_m1)

            self.kdj_m2 = QSpinBox()
            self.kdj_m2.setRange(1, 30)
            self.kdj_m2.setValue(3)
            indicator_layout.addRow("KDJ M2:", self.kdj_m2)

            # 添加RSI参数
            self.rsi_periods = []
            for i, period in enumerate([6, 12, 24]):
                spin = QSpinBox()
                spin.setRange(1, 100)
                spin.setValue(period)
                self.rsi_periods.append(spin)
                indicator_layout.addRow(f"RSI{i+1}周期:", spin)

            indicator_group.setLayout(indicator_layout)
            layout.addWidget(indicator_group)

            # 创建指标结果组
            result_group = QGroupBox("指标分析")
            result_layout = QVBoxLayout()

            # 添加指标结果表格
            self.indicator_table = QTableWidget()
            self.indicator_table.setColumnCount(4)
            self.indicator_table.setHorizontalHeaderLabels([
                "指标", "数值", "状态", "建议"
            ])
            result_layout.addWidget(self.indicator_table)

            result_group.setLayout(result_layout)
            layout.addWidget(result_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            calculate_button = QPushButton("计算指标")
            calculate_button.clicked.connect(self.calculate_indicators)
            button_layout.addWidget(calculate_button)

            clear_button = QPushButton("清除指标")
            clear_button.clicked.connect(self.clear_indicators)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建技术分析标签页失败: {str(e)}", "error")
            raise

    def calculate_indicators(self):
        """计算技术指标"""
        try:
            if not self.current_kdata:
                return

            # 获取当前指标
            indicator = self.indicator_combo.currentText()

            # 清空结果表格
            self.indicator_table.setRowCount(0)

            if indicator == 'MA':
                self.calculate_ma()
            elif indicator == 'MACD':
                self.calculate_macd()
            elif indicator == 'KDJ':
                self.calculate_kdj()
            elif indicator == 'RSI':
                self.calculate_rsi()
            elif indicator == 'BOLL':
                self.calculate_boll()
            elif indicator == '综合分析':
                self.calculate_comprehensive()

            # 调整列宽
            self.indicator_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"计算技术指标失败: {str(e)}", "error")

    def calculate_ma(self):
        """计算MA指标"""
        try:
            close = self.current_kdata.close
            last_close = float(close[-1])

            # 计算各周期MA
            for i, spin in enumerate(self.ma_periods):
                period = spin.value()
                ma = MA(close, period)
                last_ma = float(ma[-1])

                # 添加结果
                row = self.indicator_table.rowCount()
                self.indicator_table.insertRow(row)

                self.indicator_table.setItem(
                    row, 0,
                    QTableWidgetItem(f"MA{period}")
                )
                self.indicator_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"{last_ma:.2f}")
                )

                # 判断状态
                if last_close > last_ma:
                    status = "多头"
                    suggestion = "可以买入"
                    color = "red"
                else:
                    status = "空头"
                    suggestion = "可以卖出"
                    color = "green"

                status_item = QTableWidgetItem(status)
                status_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(row, 2, status_item)

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算MA指标失败: {str(e)}", "error")

    def calculate_macd(self):
        """计算MACD指标"""
        try:
            close = self.current_kdata.close

            # 计算MACD
            short = self.macd_short.value()
            long = self.macd_long.value()
            signal = self.macd_signal.value()

            macd = MACD(close, short, long, signal)
            last_dif = float(macd.dif[-1])
            last_dea = float(macd.dea[-1])
            last_macd = float(macd.macd[-1])

            # 添加DIF结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("DIF")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_dif:.4f}")
            )

            # 添加DEA结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("DEA")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_dea:.4f}")
            )

            # 添加MACD结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("MACD")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_macd:.4f}")
            )

            # 判断状态
            if last_dif > last_dea:
                status = "多头"
                suggestion = "可以买入"
                color = "red"
            else:
                status = "空头"
                suggestion = "可以卖出"
                color = "green"

            for i in range(3):
                status_item = QTableWidgetItem(status)
                status_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(i, 2, status_item)

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(i, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算MACD指标失败: {str(e)}", "error")

    def calculate_kdj(self):
        """计算KDJ指标"""
        try:
            # 计算KDJ
            n = self.kdj_n.value()
            m1 = self.kdj_m1.value()
            m2 = self.kdj_m2.value()

            kdj = KDJ(self.current_kdata, n, m1, m2)
            last_k = float(kdj.k[-1])
            last_d = float(kdj.d[-1])
            last_j = float(kdj.j[-1])

            # 添加K值结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("K")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_k:.2f}")
            )

            # 添加D值结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("D")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_d:.2f}")
            )

            # 添加J值结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("J")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_j:.2f}")
            )

            # 判断状态
            if last_k > last_d:
                status = "多头"
                suggestion = "可以买入"
                color = "red"
            else:
                status = "空头"
                suggestion = "可以卖出"
                color = "green"

            for i in range(3):
                status_item = QTableWidgetItem(status)
                status_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(i, 2, status_item)

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(
                    Qt.red if color == "red" else Qt.green)
                self.indicator_table.setItem(i, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算KDJ指标失败: {str(e)}", "error")

    def calculate_rsi(self):
        """计算RSI指标"""
        try:
            close = self.current_kdata.close

            # 计算各周期RSI
            for i, spin in enumerate(self.rsi_periods):
                period = spin.value()
                rsi = RSI(close, period)
                last_rsi = float(rsi[-1])

                # 添加结果
                row = self.indicator_table.rowCount()
                self.indicator_table.insertRow(row)

                self.indicator_table.setItem(
                    row, 0,
                    QTableWidgetItem(f"RSI{period}")
                )
                self.indicator_table.setItem(
                    row, 1,
                    QTableWidgetItem(f"{last_rsi:.2f}")
                )

                # 判断状态
                if last_rsi > 70:
                    status = "超买"
                    suggestion = "可以卖出"
                    color = "green"
                elif last_rsi < 30:
                    status = "超卖"
                    suggestion = "可以买入"
                    color = "red"
                else:
                    status = "中性"
                    suggestion = "观望"
                    color = "black"

                status_item = QTableWidgetItem(status)
                status_item.setForeground(
                    Qt.red if color == "red" else
                    Qt.green if color == "green" else Qt.black
                )
                self.indicator_table.setItem(row, 2, status_item)

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(
                    Qt.red if color == "red" else
                    Qt.green if color == "green" else Qt.black
                )
                self.indicator_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算RSI指标失败: {str(e)}", "error")

    def calculate_boll(self):
        """计算BOLL指标"""
        try:
            close = self.current_kdata.close
            last_close = float(close[-1])

            # 计算BOLL
            boll = BBANDS(close)
            last_upper = float(boll.upper[-1])
            last_middle = float(boll.middle[-1])
            last_lower = float(boll.lower[-1])

            # 添加上轨结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("BOLL上轨")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_upper:.2f}")
            )

            # 添加中轨结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("BOLL中轨")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_middle:.2f}")
            )

            # 添加下轨结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("BOLL下轨")
            )
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(f"{last_lower:.2f}")
            )

            # 判断状态
            if last_close > last_upper:
                status = "超买"
                suggestion = "可以卖出"
                color = "green"
            elif last_close < last_lower:
                status = "超卖"
                suggestion = "可以买入"
                color = "red"
            else:
                status = "震荡"
                suggestion = "观望"
                color = "black"

            for i in range(3):
                status_item = QTableWidgetItem(status)
                status_item.setForeground(
                    Qt.red if color == "red" else
                    Qt.green if color == "green" else Qt.black
                )
                self.indicator_table.setItem(i, 2, status_item)

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(
                    Qt.red if color == "red" else
                    Qt.green if color == "green" else Qt.black
                )
                self.indicator_table.setItem(i, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算BOLL指标失败: {str(e)}", "error")

    def calculate_comprehensive(self):
        """计算综合分析"""
        try:
            close = self.current_kdata.close
            last_close = float(close[-1])

            # 计算各项指标
            ma = MA(close, 20)
            macd = MACD(close)
            kdj = KDJ(self.current_kdata)
            rsi = RSI(close)
            boll = BBANDS(close)

            # 判断MA趋势
            ma_trend = "多头" if last_close > float(ma[-1]) else "空头"

            # 判断MACD趋势
            macd_trend = "多头" if float(
                macd.dif[-1]) > float(macd.dea[-1]) else "空头"

            # 判断KDJ趋势
            kdj_trend = "多头" if float(kdj.k[-1]) > float(kdj.d[-1]) else "空头"

            # 判断RSI状态
            last_rsi = float(rsi[-1])
            if last_rsi > 70:
                rsi_trend = "超买"
            elif last_rsi < 30:
                rsi_trend = "超卖"
            else:
                rsi_trend = "中性"

            # 判断BOLL状态
            if last_close > float(boll.upper[-1]):
                boll_trend = "超买"
            elif last_close < float(boll.lower[-1]):
                boll_trend = "超卖"
            else:
                boll_trend = "震荡"

            # 统计多空指标数
            bull_count = sum(1 for trend in [ma_trend, macd_trend, kdj_trend]
                             if trend == "多头")
            bear_count = sum(1 for trend in [ma_trend, macd_trend, kdj_trend]
                             if trend == "空头")

            # 添加综合结果
            row = self.indicator_table.rowCount()
            self.indicator_table.insertRow(row)

            self.indicator_table.setItem(
                row, 0,
                QTableWidgetItem("综合分析")
            )

            strength = f"多头:{bull_count} 空头:{bear_count}"
            self.indicator_table.setItem(
                row, 1,
                QTableWidgetItem(strength)
            )

            # 判断综合状态
            if bull_count > bear_count:
                status = "多头占优"
                suggestion = "偏向买入"
                color = "red"
            elif bull_count < bear_count:
                status = "空头占优"
                suggestion = "偏向卖出"
                color = "green"
            else:
                status = "势均力敌"
                suggestion = "建议观望"
                color = "black"

            status_item = QTableWidgetItem(status)
            status_item.setForeground(
                Qt.red if color == "red" else
                Qt.green if color == "green" else Qt.black
            )
            self.indicator_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if color == "red" else
                Qt.green if color == "green" else Qt.black
            )
            self.indicator_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"计算综合分析失败: {str(e)}", "error")

    def clear_indicators(self):
        """清除指标"""
        try:
            self.current_stock = None
            self.current_kdata = None
            self.current_indicators = []
            self.indicator_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除指标失败: {str(e)}", "error")
            raise

    def on_indicator_changed(self, text):
        """指标变更处理"""
        try:
            self.indicator_changed.emit(text)
        except Exception as e:
            log_manager.log(f"指标变更处理失败: {str(e)}", "error")
            raise

    def create_pattern_tab(self) -> QWidget:
        """创建形态识别标签页

        Returns:
            形态识别标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建形态选择组
            pattern_group = QGroupBox("形态选择")
            pattern_layout = QVBoxLayout()

            # 添加形态复选框
            self.pattern_checks = {}
            patterns = [
                "头肩顶/底", "双顶/双底", "三重顶/底",
                "上升/下降三角形", "旗形/三角旗", "楔形",
                "突破形态", "缺口形态", "岛型反转"
            ]

            for pattern in patterns:
                check = QCheckBox(pattern)
                self.pattern_checks[pattern] = check
                pattern_layout.addWidget(check)

            pattern_group.setLayout(pattern_layout)
            layout.addWidget(pattern_group)

            # 创建参数设置组
            param_group = QGroupBox("参数设置")
            param_layout = QFormLayout()

            # 添加识别阈值
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(60, 100)
            self.threshold_spin.setValue(80)
            self.threshold_spin.setSingleStep(1)
            param_layout.addRow("识别阈值(%):", self.threshold_spin)

            # 添加最小形态大小
            self.min_size_spin = QSpinBox()
            self.min_size_spin.setRange(5, 100)
            self.min_size_spin.setValue(20)
            param_layout.addRow("最小形态大小:", self.min_size_spin)

            param_group.setLayout(param_layout)
            layout.addWidget(param_group)

            # 创建识别结果组
            result_group = QGroupBox("识别结果")
            result_layout = QVBoxLayout()

            # 添加结果表格
            self.pattern_table = QTableWidget()
            self.pattern_table.setColumnCount(4)
            self.pattern_table.setHorizontalHeaderLabels([
                "形态", "位置", "可信度", "建议"
            ])
            result_layout.addWidget(self.pattern_table)

            result_group.setLayout(result_layout)
            layout.addWidget(result_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            identify_button = QPushButton("识别形态")
            identify_button.clicked.connect(self.identify_patterns)
            button_layout.addWidget(identify_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_patterns)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建形态识别标签页失败: {str(e)}", "error")
            raise

    def identify_patterns(self):
        """识别形态"""
        try:
            if not self.current_kdata:
                return

            # 清空结果表格
            self.pattern_table.setRowCount(0)

            # 获取参数
            threshold = self.threshold_spin.value() / 100
            min_size = self.min_size_spin.value()

            # 识别选中的形态
            for pattern, check in self.pattern_checks.items():
                if not check.isChecked():
                    continue

                if pattern == "头肩顶/底":
                    self.find_head_shoulders(threshold, min_size)
                elif pattern == "双顶/双底":
                    self.find_double_tops_bottoms(threshold, min_size)
                elif pattern == "三重顶/底":
                    self.find_triple_tops_bottoms(threshold, min_size)
                elif pattern == "上升/下降三角形":
                    self.find_triangles(threshold, min_size)
                elif pattern == "旗形/三角旗":
                    self.find_flags(threshold, min_size)
                elif pattern == "楔形":
                    self.find_wedges(threshold, min_size)
                elif pattern == "突破形态":
                    self.find_breakouts(threshold, min_size)
                elif pattern == "缺口形态":
                    self.find_gaps(threshold, min_size)
                elif pattern == "岛型反转":
                    self.find_island_reversals(threshold, min_size)

            # 调整列宽
            self.pattern_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"识别形态失败: {str(e)}", "error")

    def find_head_shoulders(self, threshold: float, min_size: int):
        """识别头肩顶/底形态

        Args:
            threshold: 识别阈值
            min_size: 最小形态大小
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low

            # 寻找局部极值点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 识别头肩顶形态
            for i in range(len(peaks)-4):
                # 获取连续5个峰顶点
                p1, p2, p3, p4, p5 = peaks[i:i+5]

                # 检查是否满足头肩顶特征
                if (abs(p1[1] - p5[1])/p1[1] < 0.1 and  # 左右肩高度相近
                    p3[1] > p1[1] and p3[1] > p5[1] and  # 头部最高
                    p2[1] < p3[1] and p4[1] < p3[1] and  # 颈部低于头部
                        p2[1] - p1[1] > 0 and p4[1] - p5[1] > 0):  # 颈线向上倾斜

                    # 计算可信度
                    confidence = min(
                        1.0,
                        (p3[1] - p1[1])/p1[1] * threshold
                    ) * 100

                    if confidence >= threshold * 100:
                        # 添加识别结果
                        row = self.pattern_table.rowCount()
                        self.pattern_table.insertRow(row)

                        self.pattern_table.setItem(
                            row, 0,
                            QTableWidgetItem("头肩顶")
                        )

                        position = f"{p1[0]}-{p5[0]}"
                        self.pattern_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        self.pattern_table.setItem(
                            row, 2,
                            QTableWidgetItem(f"{confidence:.1f}%")
                        )

                        suggestion = "卖出"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.green)
                        self.pattern_table.setItem(row, 3, suggestion_item)

            # 识别头肩底形态
            for i in range(len(troughs)-4):
                # 获取连续5个谷底点
                t1, t2, t3, t4, t5 = troughs[i:i+5]

                # 检查是否满足头肩底特征
                if (abs(t1[1] - t5[1])/t1[1] < 0.1 and  # 左右肩高度相近
                    t3[1] < t1[1] and t3[1] < t5[1] and  # 头部最低
                    t2[1] > t3[1] and t4[1] > t3[1] and  # 颈部高于头部
                        t2[1] - t1[1] < 0 and t4[1] - t5[1] < 0):  # 颈线向下倾斜

                    # 计算可信度
                    confidence = min(
                        1.0,
                        (t1[1] - t3[1])/t3[1] * threshold
                    ) * 100

                    if confidence >= threshold * 100:
                        # 添加识别结果
                        row = self.pattern_table.rowCount()
                        self.pattern_table.insertRow(row)

                        self.pattern_table.setItem(
                            row, 0,
                            QTableWidgetItem("头肩底")
                        )

                        position = f"{t1[0]}-{t5[0]}"
                        self.pattern_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        self.pattern_table.setItem(
                            row, 2,
                            QTableWidgetItem(f"{confidence:.1f}%")
                        )

                        suggestion = "买入"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.red)
                        self.pattern_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"识别头肩顶/底形态失败: {str(e)}", "error")

    def find_double_tops_bottoms(self, threshold: float, min_size: int):
        """识别双顶/双底形态

        Args:
            threshold: 识别阈值
            min_size: 最小形态大小
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low

            # 寻找局部极值点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 识别双顶形态
            for i in range(len(peaks)-1):
                p1, p2 = peaks[i:i+2]

                # 检查两个顶点之间的距离
                if p2[0] - p1[0] < min_size:
                    continue

                # 检查是否满足双顶特征
                if abs(p1[1] - p2[1])/p1[1] < 0.05:  # 两个顶点高度相近
                    # 寻找中间的谷底
                    middle_trough = None
                    for t in troughs:
                        if p1[0] < t[0] < p2[0]:
                            if middle_trough is None or t[1] < middle_trough[1]:
                                middle_trough = t

                    if middle_trough and middle_trough[1] < min(p1[1], p2[1]):
                        # 计算可信度
                        height_diff = min(p1[1], p2[1]) - middle_trough[1]
                        confidence = min(
                            1.0,
                            height_diff/middle_trough[1] * threshold
                        ) * 100

                        if confidence >= threshold * 100:
                            # 添加识别结果
                            row = self.pattern_table.rowCount()
                            self.pattern_table.insertRow(row)

                            self.pattern_table.setItem(
                                row, 0,
                                QTableWidgetItem("双顶")
                            )

                            position = f"{p1[0]}-{p2[0]}"
                            self.pattern_table.setItem(
                                row, 1,
                                QTableWidgetItem(position)
                            )

                            self.pattern_table.setItem(
                                row, 2,
                                QTableWidgetItem(f"{confidence:.1f}%")
                            )

                            suggestion = "卖出"
                            suggestion_item = QTableWidgetItem(suggestion)
                            suggestion_item.setForeground(Qt.green)
                            self.pattern_table.setItem(row, 3, suggestion_item)

            # 识别双底形态
            for i in range(len(troughs)-1):
                t1, t2 = troughs[i:i+2]

                # 检查两个底点之间的距离
                if t2[0] - t1[0] < min_size:
                    continue

                # 检查是否满足双底特征
                if abs(t1[1] - t2[1])/t1[1] < 0.05:  # 两个底点高度相近
                    # 寻找中间的峰顶
                    middle_peak = None
                    for p in peaks:
                        if t1[0] < p[0] < t2[0]:
                            if middle_peak is None or p[1] > middle_peak[1]:
                                middle_peak = p

                    if middle_peak and middle_peak[1] > max(t1[1], t2[1]):
                        # 计算可信度
                        height_diff = middle_peak[1] - max(t1[1], t2[1])
                        confidence = min(
                            1.0,
                            height_diff/middle_peak[1] * threshold
                        ) * 100

                        if confidence >= threshold * 100:
                            # 添加识别结果
                            row = self.pattern_table.rowCount()
                            self.pattern_table.insertRow(row)

                            self.pattern_table.setItem(
                                row, 0,
                                QTableWidgetItem("双底")
                            )

                            position = f"{t1[0]}-{t2[0]}"
                            self.pattern_table.setItem(
                                row, 1,
                                QTableWidgetItem(position)
                            )

                            self.pattern_table.setItem(
                                row, 2,
                                QTableWidgetItem(f"{confidence:.1f}%")
                            )

                            suggestion = "买入"
                            suggestion_item = QTableWidgetItem(suggestion)
                            suggestion_item.setForeground(Qt.red)
                            self.pattern_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"识别双顶/双底形态失败: {str(e)}", "error")

    def clear_patterns(self):
        """清除形态识别结果"""
        try:
            self.pattern_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除形态识别结果失败: {str(e)}", "error")
            raise

    def create_trend_tab(self) -> QWidget:
        """创建趋势分析标签页

        Returns:
            趋势分析标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建趋势参数组
            param_group = QGroupBox("趋势参数")
            param_layout = QFormLayout()

            # 添加趋势周期
            self.trend_period = QSpinBox()
            self.trend_period.setRange(5, 120)
            self.trend_period.setValue(20)
            param_layout.addRow("趋势周期:", self.trend_period)

            # 添加趋势阈值
            self.trend_threshold = QDoubleSpinBox()
            self.trend_threshold.setDecimals(2)
            self.trend_threshold.setRange(0.1, 10.0)
            self.trend_threshold.setValue(1.0)
            self.trend_threshold.setSingleStep(0.1)
            param_layout.addRow("趋势阈值:", self.trend_threshold)

            param_group.setLayout(param_layout)
            layout.addWidget(param_group)

            # 创建趋势结果组
            result_group = QGroupBox("趋势分析")
            result_layout = QVBoxLayout()

            # 添加结果表格
            self.trend_table = QTableWidget()
            self.trend_table.setColumnCount(4)
            self.trend_table.setHorizontalHeaderLabels([
                "指标", "趋势", "强度", "建议"
            ])
            result_layout.addWidget(self.trend_table)

            result_group.setLayout(result_layout)
            layout.addWidget(result_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            analyze_button = QPushButton("分析趋势")
            analyze_button.clicked.connect(self.analyze_trend)
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_trend)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建趋势分析标签页失败: {str(e)}", "error")
            raise

    def analyze_trend(self):
        """分析趋势"""
        try:
            if not self.current_kdata:
                return

            # 清空结果表格
            self.trend_table.setRowCount(0)

            # 获取参数
            period = self.trend_period.value()
            threshold = self.trend_threshold.value()

            # 分析各指标趋势
            self.analyze_price_trend(period, threshold)
            self.analyze_volume_trend(period, threshold)
            self.analyze_macd_trend(period, threshold)
            self.analyze_kdj_trend(period, threshold)
            self.analyze_rsi_trend(period, threshold)

            # 调整列宽
            self.trend_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析趋势失败: {str(e)}", "error")

    def analyze_price_trend(self, period: int, threshold: float):
        """分析价格趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            close = self.current_kdata.close
            ma = MA(close, period)

            # 计算趋势
            trend = "上升" if float(close[-1]) > float(ma[-1]) else "下降"

            # 计算趋势强度
            strength = abs(float(close[-1]) -
                           float(ma[-1])) / float(ma[-1]) * 100

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("价格")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "上升" else Qt.green
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "上升" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if trend == "上升" else Qt.green
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析价格趋势失败: {str(e)}", "error")

    def analyze_volume_trend(self, period: int, threshold: float):
        """分析成交量趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            volume = self.current_kdata.volume
            ma = MA(volume, period)

            # 计算趋势
            trend = "放量" if float(volume[-1]) > float(ma[-1]) else "缩量"

            # 计算趋势强度
            strength = abs(float(volume[-1]) -
                           float(ma[-1])) / float(ma[-1]) * 100

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("成交量")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "放量" else Qt.green
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            # 根据价格趋势给出建议
            price_trend = self.trend_table.item(0, 1).text()
            if price_trend == "上升":
                suggestion = "买入" if trend == "放量" else "观望"
            else:
                suggestion = "卖出" if trend == "放量" else "观望"

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "买入" else
                Qt.green if suggestion == "卖出" else Qt.black
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析成交量趋势失败: {str(e)}", "error")

    def analyze_macd_trend(self, period: int, threshold: float):
        """分析MACD趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            close = self.current_kdata.close
            macd = MACD(close)

            # 计算趋势
            trend = "多头" if float(macd.dif[-1]) > float(macd.dea[-1]) else "空头"

            # 计算趋势强度
            strength = abs(float(macd.dif[-1]) - float(macd.dea[-1])) * 100

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("MACD")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "多头" else Qt.green
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if trend == "多头" else Qt.green
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析MACD趋势失败: {str(e)}", "error")

    def analyze_kdj_trend(self, period: int, threshold: float):
        """分析KDJ趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            kdj = KDJ(self.current_kdata)

            # 计算趋势
            trend = "多头" if float(kdj.k[-1]) > float(kdj.d[-1]) else "空头"

            # 计算趋势强度
            strength = abs(float(kdj.k[-1]) - float(kdj.d[-1]))

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("KDJ")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "多头" else Qt.green
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if trend == "多头" else Qt.green
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析KDJ趋势失败: {str(e)}", "error")

    def analyze_rsi_trend(self, period: int, threshold: float):
        """分析RSI趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            close = self.current_kdata.close
            rsi = RSI(close)
            last_rsi = float(rsi[-1])

            # 计算趋势
            if last_rsi > 70:
                trend = "超买"
            elif last_rsi < 30:
                trend = "超卖"
            else:
                trend = "中性"

            # 计算趋势强度
            if trend == "超买":
                strength = (last_rsi - 70) / 30 * 100
            elif trend == "超卖":
                strength = (30 - last_rsi) / 30 * 100
            else:
                strength = 0

            # 添加结果
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)

            self.trend_table.setItem(
                row, 0,
                QTableWidgetItem("RSI")
            )

            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(
                Qt.red if trend == "超卖" else
                Qt.green if trend == "超买" else Qt.black
            )
            self.trend_table.setItem(row, 1, trend_item)

            self.trend_table.setItem(
                row, 2,
                QTableWidgetItem(f"{strength:.1f}%")
            )

            suggestion = "买入" if trend == "超卖" else "卖出" if trend == "超买" else "观望"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "买入" else
                Qt.green if suggestion == "卖出" else Qt.black
            )
            self.trend_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析RSI趋势失败: {str(e)}", "error")

    def clear_trend(self):
        """清除趋势分析结果"""
        try:
            self.trend_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除趋势分析结果失败: {str(e)}", "error")
            raise

    def create_wave_tab(self) -> QWidget:
        """创建波浪分析标签页

        Returns:
            波浪分析标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建波浪参数组
            param_group = QGroupBox("波浪参数")
            param_layout = QFormLayout()

            # 添加波浪类型选择
            self.wave_type = QComboBox()
            self.wave_type.addItems([
                "艾略特波浪", "江恩理论", "支撑阻力位"
            ])
            param_layout.addRow("波浪类型:", self.wave_type)

            # 添加波浪周期
            self.wave_period = QSpinBox()
            self.wave_period.setRange(5, 120)
            self.wave_period.setValue(20)
            param_layout.addRow("波浪周期:", self.wave_period)

            # 添加灵敏度
            self.wave_sensitivity = QDoubleSpinBox()
            self.wave_sensitivity.setRange(0.1, 5)
            self.wave_sensitivity.setValue(1)
            self.wave_sensitivity.setSingleStep(0.1)
            param_layout.addRow("灵敏度:", self.wave_sensitivity)

            param_group.setLayout(param_layout)
            layout.addWidget(param_group)

            # 创建波浪结果组
            result_group = QGroupBox("波浪分析")
            result_layout = QVBoxLayout()

            # 添加结果表格
            self.wave_table = QTableWidget()
            self.wave_table.setColumnCount(4)
            self.wave_table.setHorizontalHeaderLabels([
                "波浪", "位置", "特征", "建议"
            ])
            result_layout.addWidget(self.wave_table)

            result_group.setLayout(result_layout)
            layout.addWidget(result_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            analyze_button = QPushButton("分析波浪")
            analyze_button.clicked.connect(self.analyze_wave)
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_wave)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建波浪分析标签页失败: {str(e)}", "error")
            raise

    def analyze_wave(self):
        """分析波浪"""
        try:
            if not self.current_kdata:
                return

            # 清空结果表格
            self.wave_table.setRowCount(0)

            # 获取参数
            wave_type = self.wave_type.currentText()
            period = self.wave_period.value()
            sensitivity = self.wave_sensitivity.value()

            # 根据选择的波浪类型进行分析
            if wave_type == "艾略特波浪":
                self.analyze_elliott_waves(period, sensitivity)
            elif wave_type == "江恩理论":
                self.analyze_gann(period, sensitivity)
            elif wave_type == "支撑阻力位":
                self.analyze_support_resistance(period, sensitivity)

            # 调整列宽
            self.wave_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析波浪失败: {str(e)}", "error")

    def analyze_elliott_waves(self, period: int, sensitivity: float):
        """分析艾略特波浪

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 寻找关键转折点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 识别推动浪
            for i in range(len(peaks)-2):
                # 获取连续3个峰顶点
                p1, p2, p3 = peaks[i:i+3]

                # 检查是否满足推动浪特征
                if (p2[1] > p1[1] and p3[1] > p2[1] and  # 价格逐步上升
                    p2[0] - p1[0] >= period and  # 波浪间隔满足周期要求
                        p3[0] - p2[0] >= period):

                    # 计算波浪强度
                    strength = (p3[1] - p1[1]) / p1[1] * 100

                    if strength >= sensitivity:
                        # 添加识别结果
                        row = self.wave_table.rowCount()
                        self.wave_table.insertRow(row)

                        self.wave_table.setItem(
                            row, 0,
                            QTableWidgetItem("推动浪")
                        )

                        position = f"{p1[0]}-{p3[0]}"
                        self.wave_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        feature = f"上升{strength:.1f}%"
                        self.wave_table.setItem(
                            row, 2,
                            QTableWidgetItem(feature)
                        )

                        suggestion = "买入"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.red)
                        self.wave_table.setItem(row, 3, suggestion_item)

            # 识别调整浪
            for i in range(len(troughs)-2):
                # 获取连续3个谷底点
                t1, t2, t3 = troughs[i:i+3]

                # 检查是否满足调整浪特征
                if (t2[1] < t1[1] and t3[1] < t2[1] and  # 价格逐步下降
                    t2[0] - t1[0] >= period and  # 波浪间隔满足周期要求
                        t3[0] - t2[0] >= period):

                    # 计算波浪强度
                    strength = (t1[1] - t3[1]) / t1[1] * 100

                    if strength >= sensitivity:
                        # 添加识别结果
                        row = self.wave_table.rowCount()
                        self.wave_table.insertRow(row)

                        self.wave_table.setItem(
                            row, 0,
                            QTableWidgetItem("调整浪")
                        )

                        position = f"{t1[0]}-{t3[0]}"
                        self.wave_table.setItem(
                            row, 1,
                            QTableWidgetItem(position)
                        )

                        feature = f"下降{strength:.1f}%"
                        self.wave_table.setItem(
                            row, 2,
                            QTableWidgetItem(feature)
                        )

                        suggestion = "卖出"
                        suggestion_item = QTableWidgetItem(suggestion)
                        suggestion_item.setForeground(Qt.green)
                        self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析艾略特波浪失败: {str(e)}", "error")

    def analyze_gann(self, period: int, sensitivity: float):
        """分析江恩理论

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 计算江恩角度线
            last_close = float(close[-1])
            angles = [
                (45, last_close * (1 + 1/1)),   # 1:1线
                (63.75, last_close * (1 + 2/1)),  # 2:1线
                (26.25, last_close * (1 + 1/2)),  # 1:2线
                (71.25, last_close * (1 + 3/1)),  # 3:1线
                (18.75, last_close * (1 + 1/3))  # 1:3线
            ]

            # 检查价格与角度线的关系
            for angle, target in angles:
                # 计算当前价格偏离角度线的百分比
                deviation = abs(target - last_close) / last_close * 100

                if deviation <= sensitivity:
                    # 添加识别结果
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem(f"{angle}°角度线")
                    )

                    position = "当前"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    feature = f"偏离{deviation:.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if last_close < target:
                        suggestion = "买入"
                        color = Qt.red
                    else:
                        suggestion = "卖出"
                        color = Qt.green

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 计算江恩时间周期
            key_dates = [
                (90, "季度周期"),
                (180, "半年周期"),
                (360, "年度周期")
            ]

            current_index = len(close) - 1
            for days, cycle_name in key_dates:
                if current_index % days <= sensitivity * 10:
                    # 添加识别结果
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem(cycle_name)
                    )

                    position = "当前"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    feature = f"周期拐点"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    suggestion = "关注"
                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(Qt.black)
                    self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析江恩理论失败: {str(e)}", "error")

    def analyze_support_resistance(self, period: int, sensitivity: float):
        """分析支撑阻力位

        Args:
            period: 波浪周期
            sensitivity: 灵敏度
        """
        try:
            high = self.current_kdata.high
            low = self.current_kdata.low
            close = self.current_kdata.close

            # 寻找局部极值点
            peaks = []
            troughs = []

            for i in range(1, len(high)-1):
                # 寻找峰顶
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append((i, float(high[i])))

                # 寻找谷底
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    troughs.append((i, float(low[i])))

            # 聚类相近的价格水平
            def cluster_levels(levels, sensitivity):
                if not levels:
                    return []

                # 按价格排序
                sorted_levels = sorted(levels, key=lambda x: x[1])
                clusters = [[sorted_levels[0]]]

                for level in sorted_levels[1:]:
                    last_cluster = clusters[-1]
                    last_price = last_cluster[-1][1]

                    # 如果价格相近，加入同一个簇
                    if abs(level[1] - last_price) / last_price * 100 <= sensitivity:
                        last_cluster.append(level)
                    else:
                        clusters.append([level])

                # 计算每个簇的平均价格
                return [(
                    sum(x[0] for x in cluster) // len(cluster),
                    sum(x[1] for x in cluster) / len(cluster)
                ) for cluster in clusters]

            # 聚类支撑位和阻力位
            resistance_levels = cluster_levels(peaks, sensitivity)
            support_levels = cluster_levels(troughs, sensitivity)

            # 计算趋势线
            def calculate_trend_lines(points, is_resistance=True):
                if len(points) < 2:
                    return []

                trend_lines = []
                last_close = float(close[-1])

                for i in range(len(points)-1):
                    for j in range(i+1, len(points)):
                        p1, p2 = points[i], points[j]

                        # 计算斜率
                        slope = (p2[1] - p1[1]) / (p2[0] - p1[0])

                        # 延伸到当前
                        current_value = p1[1] + slope * (len(close)-1 - p1[0])

                        # 如果当前价格接近趋势线，记录该趋势线
                        if abs(current_value - last_close) / last_close * 100 <= sensitivity:
                            trend_lines.append((p1, p2, current_value))

                return trend_lines

            # 计算支撑和阻力趋势线
            resistance_lines = calculate_trend_lines(resistance_levels, True)
            support_lines = calculate_trend_lines(support_levels, False)

            # 添加水平支撑位结果
            last_close = float(close[-1])
            for level in support_levels:
                if abs(level[1] - last_close) / last_close * 100 <= sensitivity:
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem("水平支撑位")
                    )

                    position = f"{level[0]}"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    deviation = (last_close - level[1]) / level[1] * 100
                    feature = f"价格{deviation:+.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if deviation < 0:
                        suggestion = "买入"
                        color = Qt.red
                    else:
                        suggestion = "观望"
                        color = Qt.black

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 添加水平阻力位结果
            for level in resistance_levels:
                if abs(level[1] - last_close) / last_close * 100 <= sensitivity:
                    row = self.wave_table.rowCount()
                    self.wave_table.insertRow(row)

                    self.wave_table.setItem(
                        row, 0,
                        QTableWidgetItem("水平阻力位")
                    )

                    position = f"{level[0]}"
                    self.wave_table.setItem(
                        row, 1,
                        QTableWidgetItem(position)
                    )

                    deviation = (last_close - level[1]) / level[1] * 100
                    feature = f"价格{deviation:+.1f}%"
                    self.wave_table.setItem(
                        row, 2,
                        QTableWidgetItem(feature)
                    )

                    if deviation > 0:
                        suggestion = "卖出"
                        color = Qt.green
                    else:
                        suggestion = "观望"
                        color = Qt.black

                    suggestion_item = QTableWidgetItem(suggestion)
                    suggestion_item.setForeground(color)
                    self.wave_table.setItem(row, 3, suggestion_item)

            # 添加趋势支撑线结果
            for p1, p2, current_value in support_lines:
                row = self.wave_table.rowCount()
                self.wave_table.insertRow(row)

                self.wave_table.setItem(
                    row, 0,
                    QTableWidgetItem("趋势支撑线")
                )

                position = f"{p1[0]}-{p2[0]}"
                self.wave_table.setItem(
                    row, 1,
                    QTableWidgetItem(position)
                )

                deviation = (last_close - current_value) / current_value * 100
                feature = f"价格{deviation:+.1f}%"
                self.wave_table.setItem(
                    row, 2,
                    QTableWidgetItem(feature)
                )

                if deviation < 0:
                    suggestion = "买入"
                    color = Qt.red
                else:
                    suggestion = "观望"
                    color = Qt.black

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(color)
                self.wave_table.setItem(row, 3, suggestion_item)

            # 添加趋势阻力线结果
            for p1, p2, current_value in resistance_lines:
                row = self.wave_table.rowCount()
                self.wave_table.insertRow(row)

                self.wave_table.setItem(
                    row, 0,
                    QTableWidgetItem("趋势阻力线")
                )

                position = f"{p1[0]}-{p2[0]}"
                self.wave_table.setItem(
                    row, 1,
                    QTableWidgetItem(position)
                )

                deviation = (last_close - current_value) / current_value * 100
                feature = f"价格{deviation:+.1f}%"
                self.wave_table.setItem(
                    row, 2,
                    QTableWidgetItem(feature)
                )

                if deviation > 0:
                    suggestion = "卖出"
                    color = Qt.green
                else:
                    suggestion = "观望"
                    color = Qt.black

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(color)
                self.wave_table.setItem(row, 3, suggestion_item)

        except Exception as e:
            log_manager.log(f"分析支撑阻力位失败: {str(e)}", "error")

    def clear_wave(self):
        """清除波浪分析结果"""
        try:
            self.wave_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除波浪分析结果失败: {str(e)}", "error")
            raise

    def create_sentiment_tab(self) -> QWidget:
        """创建市场情绪分析标签页

        Returns:
            市场情绪分析标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建情绪指标组
            indicator_group = QGroupBox("情绪指标")
            indicator_layout = QFormLayout()

            # 添加恐慌指数
            self.fear_greed_spin = QSpinBox()
            self.fear_greed_spin.setRange(0, 100)
            self.fear_greed_spin.setValue(50)
            indicator_layout.addRow("恐慌指数:", self.fear_greed_spin)

            # 添加市场强度
            self.market_strength_spin = QSpinBox()
            self.market_strength_spin.setRange(0, 100)
            self.market_strength_spin.setValue(50)
            indicator_layout.addRow("市场强度:", self.market_strength_spin)

            # 添加资金流向
            self.fund_flow_spin = QSpinBox()
            self.fund_flow_spin.setRange(-100, 100)
            self.fund_flow_spin.setValue(0)
            indicator_layout.addRow("资金流向:", self.fund_flow_spin)

            # 添加北向资金
            self.north_flow_spin = QSpinBox()
            self.north_flow_spin.setRange(-100, 100)
            self.north_flow_spin.setValue(0)
            indicator_layout.addRow("北向资金:", self.north_flow_spin)

            # 添加历史周期选择
            self.history_period = QComboBox()
            self.history_period.addItems([
                "5日", "10日", "20日", "30日", "60日"
            ])
            indicator_layout.addRow("历史周期:", self.history_period)

            indicator_group.setLayout(indicator_layout)
            layout.addWidget(indicator_group)

            # 创建情绪分析组
            sentiment_group = QGroupBox("情绪分析")
            sentiment_layout = QVBoxLayout()

            # 添加结果表格
            self.sentiment_table = QTableWidget()
            self.sentiment_table.setColumnCount(4)
            self.sentiment_table.setHorizontalHeaderLabels([
                "指标", "数值", "状态", "建议"
            ])
            sentiment_layout.addWidget(self.sentiment_table)

            sentiment_group.setLayout(sentiment_layout)
            layout.addWidget(sentiment_group)

            # 创建历史趋势组
            history_group = QGroupBox("历史趋势")
            history_layout = QVBoxLayout()

            # 添加历史趋势表格
            self.history_table = QTableWidget()
            self.history_table.setColumnCount(5)
            self.history_table.setHorizontalHeaderLabels([
                "周期", "最高值", "最低值", "均值", "趋势"
            ])
            history_layout.addWidget(self.history_table)

            history_group.setLayout(history_layout)
            layout.addWidget(history_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            analyze_button = QPushButton("分析情绪")
            analyze_button.clicked.connect(self.analyze_sentiment)
            button_layout.addWidget(analyze_button)

            history_button = QPushButton("历史趋势")
            history_button.clicked.connect(self.analyze_history)
            button_layout.addWidget(history_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_sentiment)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建市场情绪分析标签页失败: {str(e)}", "error")
            raise

    def analyze_sentiment(self):
        """分析市场情绪"""
        try:
            if not self.current_kdata:
                return

            # 清空结果表格
            self.sentiment_table.setRowCount(0)

            # 分析恐慌指数
            fear_greed = self.fear_greed_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("恐慌指数")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{fear_greed}")
            )

            if fear_greed <= 20:
                status = "极度恐慌"
                suggestion = "逢低买入"
                color = Qt.red
            elif fear_greed <= 40:
                status = "恐慌"
                suggestion = "可以买入"
                color = Qt.red
            elif fear_greed <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif fear_greed <= 80:
                status = "贪婪"
                suggestion = "可以卖出"
                color = Qt.green
            else:
                status = "极度贪婪"
                suggestion = "逢高卖出"
                color = Qt.green

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 分析市场强度
            strength = self.market_strength_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("市场强度")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{strength}")
            )

            if strength <= 20:
                status = "极弱"
                suggestion = "观望"
                color = Qt.black
            elif strength <= 40:
                status = "偏弱"
                suggestion = "谨慎"
                color = Qt.black
            elif strength <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif strength <= 80:
                status = "偏强"
                suggestion = "买入"
                color = Qt.red
            else:
                status = "极强"
                suggestion = "积极买入"
                color = Qt.red

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 分析资金流向
            flow = self.fund_flow_spin.value()
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("资金流向")
            )
            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{flow:+}")
            )

            if flow <= -50:
                status = "大幅流出"
                suggestion = "观望"
                color = Qt.black
            elif flow < 0:
                status = "小幅流出"
                suggestion = "谨慎"
                color = Qt.black
            elif flow == 0:
                status = "持平"
                suggestion = "观望"
                color = Qt.black
            elif flow < 50:
                status = "小幅流入"
                suggestion = "买入"
                color = Qt.red
            else:
                status = "大幅流入"
                suggestion = "积极买入"
                color = Qt.red

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 计算综合情绪
            row = self.sentiment_table.rowCount()
            self.sentiment_table.insertRow(row)

            self.sentiment_table.setItem(
                row, 0,
                QTableWidgetItem("综合情绪")
            )

            # 计算综合得分
            score = (
                (100 - fear_greed) * 0.4 +  # 恐慌指数反向计分
                strength * 0.3 +  # 市场强度
                (flow + 100) / 2 * 0.3  # 资金流向归一化
            )

            self.sentiment_table.setItem(
                row, 1,
                QTableWidgetItem(f"{score:.1f}")
            )

            if score <= 20:
                status = "极度悲观"
                suggestion = "逢低买入"
                color = Qt.red
            elif score <= 40:
                status = "偏悲观"
                suggestion = "可以买入"
                color = Qt.red
            elif score <= 60:
                status = "中性"
                suggestion = "观望"
                color = Qt.black
            elif score <= 80:
                status = "偏乐观"
                suggestion = "可以卖出"
                color = Qt.green
            else:
                status = "极度乐观"
                suggestion = "逢高卖出"
                color = Qt.green

            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            self.sentiment_table.setItem(row, 2, status_item)

            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(color)
            self.sentiment_table.setItem(row, 3, suggestion_item)

            # 调整列宽
            self.sentiment_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析市场情绪失败: {str(e)}", "error")

    def analyze_history(self):
        """分析历史趋势"""
        try:
            if not self.current_kdata:
                return

            # 清空历史趋势表格
            self.history_table.setRowCount(0)

            # 获取历史周期
            period_text = self.history_period.currentText()
            period = int(period_text.replace("日", ""))

            # 获取历史数据
            fear_greed_history = []
            strength_history = []
            fund_flow_history = []
            north_flow_history = []

            # 模拟生成历史数据
            for i in range(period):
                fear_greed_history.append(
                    max(0, min(100, self.fear_greed_spin.value() +
                               np.random.normal(0, 10)))
                )
                strength_history.append(
                    max(0, min(100, self.market_strength_spin.value() +
                               np.random.normal(0, 10)))
                )
                fund_flow_history.append(
                    max(-100, min(100, self.fund_flow_spin.value() +
                                  np.random.normal(0, 20)))
                )
                north_flow_history.append(
                    max(-100, min(100, self.north_flow_spin.value() +
                                  np.random.normal(0, 20)))
                )

            # 分析恐慌指数历史
            self.add_history_row(
                "恐慌指数",
                fear_greed_history,
                lambda x: "上升" if x > 0 else "下降" if x < 0 else "持平"
            )

            # 分析市场强度历史
            self.add_history_row(
                "市场强度",
                strength_history,
                lambda x: "增强" if x > 0 else "减弱" if x < 0 else "持平"
            )

            # 分析资金流向历史
            self.add_history_row(
                "资金流向",
                fund_flow_history,
                lambda x: "净流入" if x > 0 else "净流出" if x < 0 else "持平"
            )

            # 分析北向资金历史
            self.add_history_row(
                "北向资金",
                north_flow_history,
                lambda x: "净流入" if x > 0 else "净流出" if x < 0 else "持平"
            )

            # 调整列宽
            self.history_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析历史趋势失败: {str(e)}", "error")

    def add_history_row(self, name: str, data: List[float],
                        trend_func: Callable[[float], str]):
        """添加历史趋势行

        Args:
            name: 指标名称
            data: 历史数据
            trend_func: 趋势判断函数
        """
        try:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            # 添加指标名称
            self.history_table.setItem(
                row, 0,
                QTableWidgetItem(name)
            )

            # 添加最高值
            max_value = max(data)
            self.history_table.setItem(
                row, 1,
                QTableWidgetItem(f"{max_value:.1f}")
            )

            # 添加最低值
            min_value = min(data)
            self.history_table.setItem(
                row, 2,
                QTableWidgetItem(f"{min_value:.1f}")
            )

            # 添加均值
            mean_value = sum(data) / len(data)
            self.history_table.setItem(
                row, 3,
                QTableWidgetItem(f"{mean_value:.1f}")
            )

            # 计算趋势
            trend = trend_func(data[-1] - data[0])
            trend_item = QTableWidgetItem(trend)

            # 设置趋势颜色
            if "上升" in trend or "增强" in trend or "净流入" in trend:
                trend_item.setForeground(Qt.red)
            elif "下降" in trend or "减弱" in trend or "净流出" in trend:
                trend_item.setForeground(Qt.green)
            else:
                trend_item.setForeground(Qt.black)

            self.history_table.setItem(row, 4, trend_item)

        except Exception as e:
            log_manager.log(f"添加历史趋势行失败: {str(e)}", "error")
            raise

    def clear_sentiment(self):
        """清除市场情绪分析结果"""
        try:
            self.sentiment_table.setRowCount(0)
            self.history_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除市场情绪分析结果失败: {str(e)}", "error")
            raise

    def create_sector_flow_tab(self) -> QWidget:
        """创建板块资金流向分析标签页

        Returns:
            板块资金流向分析标签页控件
        """
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建行业资金流向组
            industry_group = QGroupBox("行业资金流向")
            industry_layout = QVBoxLayout()

            # 添加行业资金流向表格
            self.industry_flow_table = QTableWidget()
            self.industry_flow_table.setColumnCount(5)
            self.industry_flow_table.setHorizontalHeaderLabels([
                "行业", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            industry_layout.addWidget(self.industry_flow_table)

            industry_group.setLayout(industry_layout)
            layout.addWidget(industry_group)

            # 创建概念资金流向组
            concept_group = QGroupBox("概念资金流向")
            concept_layout = QVBoxLayout()

            # 添加概念资金流向表格
            self.concept_flow_table = QTableWidget()
            self.concept_flow_table.setColumnCount(5)
            self.concept_flow_table.setHorizontalHeaderLabels([
                "概念", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            concept_layout.addWidget(self.concept_flow_table)

            concept_group.setLayout(concept_layout)
            layout.addWidget(concept_group)

            # 创建北向资金组
            north_group = QGroupBox("北向资金")
            north_layout = QVBoxLayout()

            # 添加北向资金表格
            self.north_flow_table = QTableWidget()
            self.north_flow_table.setColumnCount(4)
            self.north_flow_table.setHorizontalHeaderLabels([
                "时间", "沪股通", "深股通", "合计"
            ])
            north_layout.addWidget(self.north_flow_table)

            north_group.setLayout(north_layout)
            layout.addWidget(north_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            analyze_button = QPushButton("分析资金流向")
            analyze_button.clicked.connect(self.analyze_sector_flow)
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_sector_flow)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建板块资金流向分析标签页失败: {str(e)}", "error")
            raise

    def analyze_sector_flow(self):
        """分析板块资金流向"""
        try:
            # 分析行业资金流向
            self.analyze_industry_flow()

            # 分析概念资金流向
            self.analyze_concept_flow()

            # 分析北向资金
            self.analyze_north_flow()

        except Exception as e:
            log_manager.log(f"分析板块资金流向失败: {str(e)}", "error")

    def analyze_industry_flow(self):
        """分析行业资金流向"""
        try:
            # 清空行业资金流向表格
            self.industry_flow_table.setRowCount(0)

            # 获取所有行业板块
            industries = [block for block in sm.get_block_list()
                          if block.type == "行业"]

            # 计算每个行业的资金流向
            industry_flows = []
            for industry in industries:
                try:
                    stocks = industry.get_stock_list()
                    if not stocks:
                        continue

                    # 计算行业资金流向
                    main_flow = 0
                    super_flow = 0
                    big_flow = 0
                    mid_flow = 0

                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-1))
                        if len(kdata) == 0:
                            continue

                        # 根据成交量和金额估算资金流向
                        volume = float(kdata[-1].volume)
                        amount = float(kdata[-1].amount)

                        if volume > 0:
                            avg_price = amount / volume
                            if avg_price > float(kdata[-1].open):
                                flow = amount
                            else:
                                flow = -amount

                            # 按成交量大小分类
                            if volume >= 1000000:  # 超大单
                                super_flow += flow
                            elif volume >= 100000:  # 大单
                                big_flow += flow
                            elif volume >= 10000:  # 中单
                                mid_flow += flow

                            main_flow = super_flow + big_flow

                    industry_flows.append({
                        'name': industry.name,
                        'main_flow': main_flow / 100000000,  # 转换为亿元
                        'super_flow': super_flow / 100000000,
                        'big_flow': big_flow / 100000000,
                        'mid_flow': mid_flow / 100000000
                    })

                except Exception as e:
                    log_manager.log(
                        f"计算行业 {industry.name} 资金流向失败: {str(e)}", "error")
                    continue

            # 按主力净流入排序
            industry_flows.sort(key=lambda x: x['main_flow'], reverse=True)

            # 更新表格
            self.industry_flow_table.setRowCount(len(industry_flows))
            for i, flow in enumerate(industry_flows):
                self.industry_flow_table.setItem(
                    i, 0, QTableWidgetItem(flow['name']))

                main_flow_item = QTableWidgetItem(f"{flow['main_flow']:+.2f}")
                main_flow_item.setForeground(
                    QColor("red" if flow['main_flow'] > 0 else "green"))
                self.industry_flow_table.setItem(i, 1, main_flow_item)

                super_flow_item = QTableWidgetItem(
                    f"{flow['super_flow']:+.2f}")
                super_flow_item.setForeground(
                    QColor("red" if flow['super_flow'] > 0 else "green"))
                self.industry_flow_table.setItem(i, 2, super_flow_item)

                big_flow_item = QTableWidgetItem(f"{flow['big_flow']:+.2f}")
                big_flow_item.setForeground(
                    QColor("red" if flow['big_flow'] > 0 else "green"))
                self.industry_flow_table.setItem(i, 3, big_flow_item)

                mid_flow_item = QTableWidgetItem(f"{flow['mid_flow']:+.2f}")
                mid_flow_item.setForeground(
                    QColor("red" if flow['mid_flow'] > 0 else "green"))
                self.industry_flow_table.setItem(i, 4, mid_flow_item)

            # 调整列宽
            self.industry_flow_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析行业资金流向失败: {str(e)}", "error")

    def analyze_concept_flow(self):
        """分析概念资金流向"""
        try:
            # 清空概念资金流向表格
            self.concept_flow_table.setRowCount(0)

            # 获取所有概念板块
            concepts = [block for block in sm.get_block_list()
                        if block.type == "概念"]

            # 计算每个概念的资金流向
            concept_flows = []
            for concept in concepts:
                try:
                    stocks = concept.get_stock_list()
                    if not stocks:
                        continue

                    # 计算概念资金流向
                    main_flow = 0
                    super_flow = 0
                    big_flow = 0
                    mid_flow = 0

                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-1))
                        if len(kdata) == 0:
                            continue

                        # 根据成交量和金额估算资金流向
                        volume = float(kdata[-1].volume)
                        amount = float(kdata[-1].amount)

                        if volume > 0:
                            avg_price = amount / volume
                            if avg_price > float(kdata[-1].open):
                                flow = amount
                            else:
                                flow = -amount

                            # 按成交量大小分类
                            if volume >= 1000000:  # 超大单
                                super_flow += flow
                            elif volume >= 100000:  # 大单
                                big_flow += flow
                            elif volume >= 10000:  # 中单
                                mid_flow += flow

                            main_flow = super_flow + big_flow

                    concept_flows.append({
                        'name': concept.name,
                        'main_flow': main_flow / 100000000,  # 转换为亿元
                        'super_flow': super_flow / 100000000,
                        'big_flow': big_flow / 100000000,
                        'mid_flow': mid_flow / 100000000
                    })

                except Exception as e:
                    log_manager.log(
                        f"计算概念 {concept.name} 资金流向失败: {str(e)}", "error")
                    continue

            # 按主力净流入排序
            concept_flows.sort(key=lambda x: x['main_flow'], reverse=True)

            # 更新表格
            self.concept_flow_table.setRowCount(len(concept_flows))
            for i, flow in enumerate(concept_flows):
                self.concept_flow_table.setItem(
                    i, 0, QTableWidgetItem(flow['name']))

                main_flow_item = QTableWidgetItem(f"{flow['main_flow']:+.2f}")
                main_flow_item.setForeground(
                    QColor("red" if flow['main_flow'] > 0 else "green"))
                self.concept_flow_table.setItem(i, 1, main_flow_item)

                super_flow_item = QTableWidgetItem(
                    f"{flow['super_flow']:+.2f}")
                super_flow_item.setForeground(
                    QColor("red" if flow['super_flow'] > 0 else "green"))
                self.concept_flow_table.setItem(i, 2, super_flow_item)

                big_flow_item = QTableWidgetItem(f"{flow['big_flow']:+.2f}")
                big_flow_item.setForeground(
                    QColor("red" if flow['big_flow'] > 0 else "green"))
                self.concept_flow_table.setItem(i, 3, big_flow_item)

                mid_flow_item = QTableWidgetItem(f"{flow['mid_flow']:+.2f}")
                mid_flow_item.setForeground(
                    QColor("red" if flow['mid_flow'] > 0 else "green"))
                self.concept_flow_table.setItem(i, 4, mid_flow_item)

            # 调整列宽
            self.concept_flow_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析概念资金流向失败: {str(e)}", "error")

    def analyze_north_flow(self):
        """分析北向资金"""
        try:
            # 清空北向资金表格
            self.north_flow_table.setRowCount(0)

            # 获取最近5个交易日的北向资金数据
            dates = []
            sh_flows = []
            sz_flows = []
            total_flows = []

            # 这里使用随机数据模拟，实际应该从数据源获取
            for i in range(5):
                date = datetime.now() - timedelta(days=i)
                dates.append(date.strftime('%Y-%m-%d'))

                sh_flow = random.uniform(-50, 50)  # 沪股通资金流向
                sz_flow = random.uniform(-30, 30)  # 深股通资金流向
                total_flow = sh_flow + sz_flow  # 北向资金合计

                sh_flows.append(sh_flow)
                sz_flows.append(sz_flow)
                total_flows.append(total_flow)

            # 更新表格
            self.north_flow_table.setRowCount(len(dates))
            for i in range(len(dates)):
                self.north_flow_table.setItem(i, 0, QTableWidgetItem(dates[i]))

                sh_flow_item = QTableWidgetItem(f"{sh_flows[i]:+.2f}")
                sh_flow_item.setForeground(
                    QColor("red" if sh_flows[i] > 0 else "green"))
                self.north_flow_table.setItem(i, 1, sh_flow_item)

                sz_flow_item = QTableWidgetItem(f"{sz_flows[i]:+.2f}")
                sz_flow_item.setForeground(
                    QColor("red" if sz_flows[i] > 0 else "green"))
                self.north_flow_table.setItem(i, 2, sz_flow_item)

                total_flow_item = QTableWidgetItem(f"{total_flows[i]:+.2f}")
                total_flow_item.setForeground(
                    QColor("red" if total_flows[i] > 0 else "green"))
                self.north_flow_table.setItem(i, 3, total_flow_item)

            # 调整列宽
            self.north_flow_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析北向资金失败: {str(e)}", "error")

    def clear_sector_flow(self):
        """清除板块资金流向分析结果"""
        try:
            self.industry_flow_table.setRowCount(0)
            self.concept_flow_table.setRowCount(0)
            self.north_flow_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除板块资金流向分析结果失败: {str(e)}", "error")
            raise

    def create_hotspot_tab(self) -> QWidget:
        """创建热点分析标签页"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 创建热点板块组
            hotspot_group = QGroupBox("热点板块")
            hotspot_layout = QVBoxLayout()

            # 添加热点板块表格
            self.hotspot_table = QTableWidget()
            self.hotspot_table.setColumnCount(7)  # 增加一列用于显示板块强度
            self.hotspot_table.setHorizontalHeaderLabels([
                "板块名称", "涨跌幅", "领涨股", "涨跌幅", "成交额", "换手率", "板块强度"
            ])
            hotspot_layout.addWidget(self.hotspot_table)

            hotspot_group.setLayout(hotspot_layout)
            layout.addWidget(hotspot_group)

            # 创建主题机会组
            theme_group = QGroupBox("主题机会")
            theme_layout = QVBoxLayout()

            # 添加主题机会表格
            self.theme_table = QTableWidget()
            self.theme_table.setColumnCount(6)  # 增加一列用于显示轮动指数
            self.theme_table.setHorizontalHeaderLabels([
                "主题名称", "相关股票数", "平均涨跌幅", "资金净流入", "热度指数", "轮动指数"
            ])
            theme_layout.addWidget(self.theme_table)

            theme_group.setLayout(theme_layout)
            layout.addWidget(theme_group)

            # 创建热点轮动组
            rotation_group = QGroupBox("热点轮动")
            rotation_layout = QVBoxLayout()

            # 添加热点轮动表格
            self.rotation_table = QTableWidget()
            self.rotation_table.setColumnCount(5)
            self.rotation_table.setHorizontalHeaderLabels([
                "轮动板块", "上升趋势", "资金流入", "持续天数", "轮动建议"
            ])
            rotation_layout.addWidget(self.rotation_table)

            rotation_group.setLayout(rotation_layout)
            layout.addWidget(rotation_group)

            # 添加按钮
            button_layout = QHBoxLayout()

            analyze_button = QPushButton("分析热点")
            analyze_button.clicked.connect(self.analyze_hotspot)
            button_layout.addWidget(analyze_button)

            rotation_button = QPushButton("分析轮动")
            rotation_button.clicked.connect(self.analyze_rotation)
            button_layout.addWidget(rotation_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(self.clear_hotspot)
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            log_manager.log(f"创建热点分析标签页失败: {str(e)}", "error")
            raise

    def analyze_hotspot(self):
        """分析市场热点"""
        try:
            # 分析热点板块
            self.analyze_hotspot_sectors()

            # 分析主题机会
            self.analyze_theme_opportunities()

            # 分析龙头股
            self.analyze_leading_stocks()

        except Exception as e:
            log_manager.log(f"分析市场热点失败: {str(e)}", "error")

    def analyze_hotspot_sectors(self):
        """分析热点板块"""
        try:
            # 清空热点板块表格
            self.hotspot_table.setRowCount(0)

            # 获取所有板块
            sectors = []
            for block in sm.get_block_list():
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue

                    # 计算板块统计
                    total_change = 0
                    total_amount = 0
                    total_turnover = 0
                    up_count = 0
                    leading_stock = None
                    leading_change = -100

                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-5))  # 获取最近5天数据用于计算板块强度
                        if len(kdata) < 5:
                            continue

                        # 计算涨跌幅
                        close = float(kdata[-1].close)
                        pre_close = float(kdata[-2].close)
                        change = (close - pre_close) / pre_close * 100

                        # 统计上涨家数
                        if change > 0:
                            up_count += 1

                        # 更新板块统计
                        total_change += change
                        total_amount += float(kdata[-1].amount)
                        total_turnover += float(kdata[-1].turnover)

                        # 更新领涨股
                        if change > leading_change:
                            leading_stock = stock
                            leading_change = change

                        # 计算5日涨跌幅
                        five_day_change = (
                            close - float(kdata[0].close)) / float(kdata[0].close) * 100

                    if len(stocks) > 0:
                        # 计算板块强度
                        strength = (
                            up_count / len(stocks) * 0.3 +  # 上涨家数占比
                            abs(total_change / len(stocks)) * 0.4 +  # 平均涨跌幅
                            (total_turnover / len(stocks)) * 0.3  # 平均换手率
                        )

                        sectors.append({
                            'name': block.name,
                            'change': total_change / len(stocks),
                            'leading_stock': leading_stock,
                            'leading_change': leading_change,
                            'amount': total_amount / 100000000,  # 转换为亿元
                            'turnover': total_turnover / len(stocks),
                            'strength': strength
                        })

                except Exception as e:
                    log_manager.log(
                        f"计算板块 {block.name} 统计失败: {str(e)}", "error")
                    continue

            # 按板块强度排序
            sectors.sort(key=lambda x: x['strength'], reverse=True)

            # 更新表格
            self.hotspot_table.setRowCount(len(sectors))
            for i, sector in enumerate(sectors):
                # 添加板块名称
                self.hotspot_table.setItem(
                    i, 0, QTableWidgetItem(sector['name']))

                # 添加板块涨跌幅
                change_item = QTableWidgetItem(f"{sector['change']:+.2f}%")
                change_item.setForeground(
                    QColor("red" if sector['change'] > 0 else "green"))
                self.hotspot_table.setItem(i, 1, change_item)

                # 添加领涨股
                if sector['leading_stock']:
                    self.hotspot_table.setItem(
                        i, 2,
                        QTableWidgetItem(sector['leading_stock'].name)
                    )

                    # 添加领涨股涨跌幅
                    leading_change_item = QTableWidgetItem(
                        f"{sector['leading_change']:+.2f}%")
                    leading_change_item.setForeground(
                        QColor(
                            "red" if sector['leading_change'] > 0 else "green")
                    )
                    self.hotspot_table.setItem(i, 3, leading_change_item)

                # 添加成交额
                self.hotspot_table.setItem(
                    i, 4,
                    QTableWidgetItem(f"{sector['amount']:.2f}")
                )

                # 添加换手率
                self.hotspot_table.setItem(
                    i, 5,
                    QTableWidgetItem(f"{sector['turnover']:.2f}%")
                )

                # 添加板块强度
                strength_item = QTableWidgetItem(f"{sector['strength']:.2f}")
                if sector['strength'] >= 80:
                    strength_item.setForeground(QColor("red"))
                elif sector['strength'] >= 50:
                    strength_item.setForeground(QColor("orange"))
                else:
                    strength_item.setForeground(QColor("green"))
                self.hotspot_table.setItem(i, 6, strength_item)

            # 调整列宽
            self.hotspot_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析热点板块失败: {str(e)}", "error")

    def analyze_theme_opportunities(self):
        """分析主题机会"""
        try:
            # 清空主题机会表格
            self.theme_table.setRowCount(0)

            # 获取所有概念板块
            themes = []
            for block in sm.get_block_list():
                if block.type != "概念":
                    continue

                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue

                    # 计算主题统计
                    total_change = 0
                    total_flow = 0
                    stock_count = len(stocks)

                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-2))
                        if len(kdata) < 2:
                            continue

                        # 计算涨跌幅
                        close = float(kdata[-1].close)
                        pre_close = float(kdata[-2].close)
                        change = (close - pre_close) / pre_close * 100
                        total_change += change

                        # 计算资金流向
                        volume = float(kdata[-1].volume)
                        amount = float(kdata[-1].amount)
                        if volume > 0:
                            avg_price = amount / volume
                            if avg_price > float(kdata[-1].open):
                                total_flow += amount
                            else:
                                total_flow -= amount

                    # 计算热度指数
                    heat_index = (
                        abs(total_change / stock_count) * 0.4 +  # 涨跌幅权重
                        abs(total_flow) / 100000000 * 0.3 +  # 资金流向权重
                        stock_count * 0.3  # 相关股票数权重
                    )

                    themes.append({
                        'name': block.name,
                        'stock_count': stock_count,
                        'avg_change': total_change / stock_count,
                        'net_flow': total_flow / 100000000,  # 转换为亿元
                        'heat_index': heat_index
                    })

                except Exception as e:
                    log_manager.log(
                        f"计算主题 {block.name} 统计失败: {str(e)}", "error")
                    continue

            # 按热度指数排序
            themes.sort(key=lambda x: x['heat_index'], reverse=True)

            # 更新表格
            self.theme_table.setRowCount(len(themes))
            for i, theme in enumerate(themes):
                # 添加主题名称
                self.theme_table.setItem(i, 0, QTableWidgetItem(theme['name']))

                # 添加相关股票数
                self.theme_table.setItem(
                    i, 1,
                    QTableWidgetItem(str(theme['stock_count']))
                )

                # 添加平均涨跌幅
                change_item = QTableWidgetItem(f"{theme['avg_change']:+.2f}%")
                change_item.setForeground(
                    QColor("red" if theme['avg_change'] > 0 else "green")
                )
                self.theme_table.setItem(i, 2, change_item)

                # 添加资金净流入
                flow_item = QTableWidgetItem(f"{theme['net_flow']:+.2f}")
                flow_item.setForeground(
                    QColor("red" if theme['net_flow'] > 0 else "green")
                )
                self.theme_table.setItem(i, 3, flow_item)

                # 添加热度指数
                self.theme_table.setItem(
                    i, 4,
                    QTableWidgetItem(f"{theme['heat_index']:.2f}")
                )

            # 调整列宽
            self.theme_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析主题机会失败: {str(e)}", "error")

    def analyze_leading_stocks(self):
        """分析龙头股"""
        try:
            # 清空龙头股表格
            self.leader_table.setRowCount(0)

            # 获取所有股票的统计数据
            leaders = []
            for block in sm.get_block_list():
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue

                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-2))
                        if len(kdata) < 2:
                            continue

                        # 计算涨跌幅
                        close = float(kdata[-1].close)
                        pre_close = float(kdata[-2].close)
                        change = (close - pre_close) / pre_close * 100

                        # 计算成交额和换手率
                        amount = float(kdata[-1].amount) / 100000000  # 转换为亿元
                        turnover = float(kdata[-1].turnover)

                        # 计算主力净流入
                        volume = float(kdata[-1].volume)
                        if volume > 0:
                            avg_price = float(kdata[-1].amount) / volume
                            if avg_price > float(kdata[-1].open):
                                main_flow = amount
                            else:
                                main_flow = -amount
                        else:
                            main_flow = 0

                        # 计算综合得分
                        score = (
                            abs(change) * 0.3 +  # 涨跌幅权重
                            amount * 0.3 +  # 成交额权重
                            turnover * 0.2 +  # 换手率权重
                            abs(main_flow) * 0.2  # 主力净流入权重
                        )

                        leaders.append({
                            'name': stock.name,
                            'block': block.name,
                            'change': change,
                            'amount': amount,
                            'turnover': turnover,
                            'main_flow': main_flow,
                            'score': score
                        })

                except Exception as e:
                    log_manager.log(f"计算股票统计失败: {str(e)}", "error")
                    continue

            # 按综合得分排序
            leaders.sort(key=lambda x: x['score'], reverse=True)

            # 只保留前30个龙头股
            leaders = leaders[:30]

            # 更新表格
            self.leader_table.setRowCount(len(leaders))
            for i, leader in enumerate(leaders):
                # 添加股票名称
                self.leader_table.setItem(
                    i, 0, QTableWidgetItem(leader['name']))

                # 添加所属板块
                self.leader_table.setItem(
                    i, 1, QTableWidgetItem(leader['block']))

                # 添加涨跌幅
                change_item = QTableWidgetItem(f"{leader['change']:+.2f}%")
                change_item.setForeground(
                    QColor("red" if leader['change'] > 0 else "green")
                )
                self.leader_table.setItem(i, 2, change_item)

                # 添加成交额
                self.leader_table.setItem(
                    i, 3,
                    QTableWidgetItem(f"{leader['amount']:.2f}")
                )

                # 添加换手率
                self.leader_table.setItem(
                    i, 4,
                    QTableWidgetItem(f"{leader['turnover']:.2f}%")
                )

                # 添加主力净流入
                flow_item = QTableWidgetItem(f"{leader['main_flow']:+.2f}")
                flow_item.setForeground(
                    QColor("red" if leader['main_flow'] > 0 else "green")
                )
                self.leader_table.setItem(i, 5, flow_item)

            # 调整列宽
            self.leader_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析龙头股失败: {str(e)}", "error")

    def analyze_rotation(self):
        """分析热点轮动"""
        try:
            # 清空热点轮动表格
            self.rotation_table.setRowCount(0)

            # 获取所有板块的历史数据
            rotations = []
            for block in sm.get_block_list():
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue

                    # 获取最近10个交易日的数据
                    daily_stats = []
                    for i in range(10):
                        total_change = 0
                        total_flow = 0
                        valid_stocks = 0

                        for stock in stocks:
                            kdata = stock.get_kdata(Query(-10))
                            if len(kdata) < 10:
                                continue

                            # 计算涨跌幅
                            close = float(kdata[-(i+1)].close)
                            pre_close = float(kdata[-(i+2)].close)
                            change = (close - pre_close) / pre_close * 100
                            total_change += change

                            # 计算资金流向
                            volume = float(kdata[-(i+1)].volume)
                            amount = float(kdata[-(i+1)].amount)
                            if volume > 0:
                                avg_price = amount / volume
                                if avg_price > float(kdata[-(i+1)].open):
                                    total_flow += amount
                                else:
                                    total_flow -= amount

                            valid_stocks += 1

                        if valid_stocks > 0:
                            daily_stats.append({
                                'change': total_change / valid_stocks,
                                'flow': total_flow / 100000000  # 转换为亿元
                            })

                    if len(daily_stats) == 10:
                        # 计算上升趋势
                        trend = sum(1 for i in range(1, len(daily_stats))
                                    if daily_stats[i]['change'] > daily_stats[i-1]['change'])

                        # 计算资金流入趋势
                        flow_trend = sum(
                            1 for stat in daily_stats if stat['flow'] > 0)

                        # 计算持续天数
                        duration = 0
                        for stat in daily_stats:
                            if stat['change'] > 0 and stat['flow'] > 0:
                                duration += 1
                            else:
                                break

                        rotations.append({
                            'name': block.name,
                            'trend': trend / 9 * 100,  # 转换为百分比
                            'flow': sum(stat['flow'] for stat in daily_stats),
                            'duration': duration,
                            'score': trend / 9 * 0.4 + flow_trend / 10 * 0.4 + duration / 10 * 0.2
                        })

                except Exception as e:
                    log_manager.log(
                        f"计算板块 {block.name} 轮动分析失败: {str(e)}", "error")
                    continue

            # 按综合得分排序
            rotations.sort(key=lambda x: x['score'], reverse=True)

            # 更新表格
            self.rotation_table.setRowCount(len(rotations))
            for i, rotation in enumerate(rotations):
                # 添加板块名称
                self.rotation_table.setItem(
                    i, 0, QTableWidgetItem(rotation['name']))

                # 添加上升趋势
                trend_item = QTableWidgetItem(f"{rotation['trend']:.1f}%")
                trend_item.setForeground(
                    QColor("red") if rotation['trend'] >= 60 else
                    QColor("orange") if rotation['trend'] >= 40 else
                    QColor("green")
                )
                self.rotation_table.setItem(i, 1, trend_item)

                # 添加资金流入
                flow_item = QTableWidgetItem(f"{rotation['flow']:+.2f}")
                flow_item.setForeground(
                    QColor("red" if rotation['flow'] > 0 else "green"))
                self.rotation_table.setItem(i, 2, flow_item)

                # 添加持续天数
                self.rotation_table.setItem(
                    i, 3,
                    QTableWidgetItem(str(rotation['duration']))
                )

                # 添加轮动建议
                if rotation['score'] >= 0.8:
                    suggestion = "积极参与"
                    color = QColor("red")
                elif rotation['score'] >= 0.6:
                    suggestion = "可以参与"
                    color = QColor("orange")
                elif rotation['score'] >= 0.4:
                    suggestion = "保持关注"
                    color = QColor("black")
                else:
                    suggestion = "暂不参与"
                    color = QColor("green")

                suggestion_item = QTableWidgetItem(suggestion)
                suggestion_item.setForeground(color)
                self.rotation_table.setItem(i, 4, suggestion_item)

            # 调整列宽
            self.rotation_table.resizeColumnsToContents()

        except Exception as e:
            log_manager.log(f"分析热点轮动失败: {str(e)}", "error")

    def clear_hotspot(self):
        """清除热点分析结果"""
        try:
            self.hotspot_table.setRowCount(0)
            self.theme_table.setRowCount(0)
            self.leader_table.setRowCount(0)
            self.rotation_table.setRowCount(0)
        except Exception as e:
            log_manager.log(f"清除热点分析结果失败: {str(e)}", "error")
            raise

    def setup_indicator_panel(self):
        """设置指标面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 技术指标设置
        tech_group = QGroupBox("技术指标")
        tech_layout = QFormLayout()

        # MA设置
        ma_layout = QHBoxLayout()
        self.ma_period = QSpinBox()
        self.ma_period.setRange(1, 250)
        self.ma_period.setValue(20)
        ma_layout.addWidget(QLabel("周期:"))
        ma_layout.addWidget(self.ma_period)
        tech_layout.addRow("MA:", ma_layout)

        # MACD设置
        macd_layout = QHBoxLayout()
        self.macd_short = QSpinBox()
        self.macd_short.setRange(1, 50)
        self.macd_short.setValue(12)
        macd_layout.addWidget(QLabel("快线:"))
        macd_layout.addWidget(self.macd_short)

        self.macd_long = QSpinBox()
        self.macd_long.setRange(1, 100)
        self.macd_long.setValue(26)
        macd_layout.addWidget(QLabel("慢线:"))
        macd_layout.addWidget(self.macd_long)

        self.macd_signal = QSpinBox()
        self.macd_signal.setRange(1, 50)
        self.macd_signal.setValue(9)
        macd_layout.addWidget(QLabel("信号:"))
        macd_layout.addWidget(self.macd_signal)
        tech_layout.addRow("MACD:", macd_layout)

        # KDJ设置
        kdj_layout = QHBoxLayout()
        self.kdj_n = QSpinBox()
        self.kdj_n.setRange(1, 90)
        self.kdj_n.setValue(9)
        kdj_layout.addWidget(QLabel("N:"))
        kdj_layout.addWidget(self.kdj_n)

        self.kdj_m1 = QSpinBox()
        self.kdj_m1.setRange(1, 30)
        self.kdj_m1.setValue(3)
        kdj_layout.addWidget(QLabel("M1:"))
        kdj_layout.addWidget(self.kdj_m1)

        self.kdj_m2 = QSpinBox()
        self.kdj_m2.setRange(1, 30)
        self.kdj_m2.setValue(3)
        kdj_layout.addWidget(QLabel("M2:"))
        kdj_layout.addWidget(self.kdj_m2)
        tech_layout.addRow("KDJ:", kdj_layout)

        tech_group.setLayout(tech_layout)
        layout.addWidget(tech_group)

        # 趋势分析设置
        trend_group = QGroupBox("趋势分析")
        trend_layout = QFormLayout()

        # 趋势周期
        trend_period_layout = QHBoxLayout()
        self.trend_period = QSpinBox()
        self.trend_period.setRange(5, 120)
        self.trend_period.setValue(20)
        trend_period_layout.addWidget(QLabel("周期:"))
        trend_period_layout.addWidget(self.trend_period)
        trend_layout.addRow("趋势周期:", trend_period_layout)

        # 趋势阈值
        trend_threshold_layout = QHBoxLayout()
        self.trend_threshold = QSpinBox()  # 改为整数，使用百分比
        self.trend_threshold.setRange(1, 100)
        self.trend_threshold.setValue(10)
        trend_threshold_layout.addWidget(QLabel("阈值(%):"))
        trend_threshold_layout.addWidget(self.trend_threshold)
        trend_layout.addRow("趋势阈值:", trend_threshold_layout)

        trend_group.setLayout(trend_layout)
        layout.addWidget(trend_group)

        # 波动分析设置
        wave_group = QGroupBox("波动分析")
        wave_layout = QFormLayout()

        # 波动周期
        wave_period_layout = QHBoxLayout()
        self.wave_period = QSpinBox()
        self.wave_period.setRange(5, 120)
        self.wave_period.setValue(20)
        wave_period_layout.addWidget(QLabel("周期:"))
        wave_period_layout.addWidget(self.wave_period)
        wave_layout.addRow("波动周期:", wave_period_layout)

        # 波动灵敏度
        wave_sensitivity_layout = QHBoxLayout()
        self.wave_sensitivity = QSpinBox()  # 改为整数，使用百分比
        self.wave_sensitivity.setRange(1, 50)
        self.wave_sensitivity.setValue(10)
        wave_sensitivity_layout.addWidget(QLabel("灵敏度(%):"))
        wave_sensitivity_layout.addWidget(self.wave_sensitivity)
        wave_layout.addRow("波动灵敏度:", wave_sensitivity_layout)

        wave_group.setLayout(wave_layout)
        layout.addWidget(wave_group)

        # 市场情绪设置
        sentiment_group = QGroupBox("市场情绪")
        sentiment_layout = QFormLayout()

        # 恐慌贪婪指数
        fear_greed_layout = QHBoxLayout()
        self.fear_greed_spin = QSpinBox()
        self.fear_greed_spin.setRange(0, 100)
        self.fear_greed_spin.setValue(50)
        fear_greed_layout.addWidget(QLabel("指数:"))
        fear_greed_layout.addWidget(self.fear_greed_spin)
        sentiment_layout.addRow("恐慌贪婪:", fear_greed_layout)

        # 市场强弱指数
        market_strength_layout = QHBoxLayout()
        self.market_strength_spin = QSpinBox()
        self.market_strength_spin.setRange(0, 100)
        self.market_strength_spin.setValue(50)
        market_strength_layout.addWidget(QLabel("指数:"))
        market_strength_layout.addWidget(self.market_strength_spin)
        sentiment_layout.addRow("市场强弱:", market_strength_layout)

        # 资金流向指数
        fund_flow_layout = QHBoxLayout()
        self.fund_flow_spin = QSpinBox()
        self.fund_flow_spin.setRange(-100, 100)
        self.fund_flow_spin.setValue(0)
        fund_flow_layout.addWidget(QLabel("指数:"))
        fund_flow_layout.addWidget(self.fund_flow_spin)
        sentiment_layout.addRow("资金流向:", fund_flow_layout)

        # 北向资金指数
        north_flow_layout = QHBoxLayout()
        self.north_flow_spin = QSpinBox()
        self.north_flow_spin.setRange(-100, 100)
        self.north_flow_spin.setValue(0)
        north_flow_layout.addWidget(QLabel("指数:"))
        north_flow_layout.addWidget(self.north_flow_spin)
        sentiment_layout.addRow("北向资金:", north_flow_layout)

        sentiment_group.setLayout(sentiment_layout)
        layout.addWidget(sentiment_group)

        return panel
