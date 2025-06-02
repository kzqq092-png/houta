"""
分析控件模块
"""
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
from datetime import *
import pandas as pd
from PyQt5.QtGui import QColor

import akshare as ak
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import importlib
import traceback
import os
import time
from concurrent.futures import *
import numba
import threading
from core.logger import LogManager, LogLevel
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from hikyuu.indicator import *
from hikyuu import sm
from hikyuu import Query
from indicators_algo import get_talib_indicator_list, get_talib_category, calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci, get_all_indicators_by_category, calc_talib_indicator
from utils.cache import Cache
import requests
from bs4 import BeautifulSoup
from analysis.pattern_recognition import PatternRecognizer
from core.data_manager import data_manager
from features.advanced_indicators import create_pattern_recognition_features, ALL_PATTERN_TYPES
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot


class AnalysisWidget(QWidget):
    """分析控件类"""

    # 定义信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)  # 新增错误信号

    data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化分析控件

        Args:
            config_manager: Optional ConfigManager instance to use
        """

        self.log_manager = LogManager()
        self.log_manager.info("初始化分析控件")

        super().__init__()

        # 初始化变量
        self.current_stock = None
        self.current_kdata = None
        self.current_indicators = []
        self.rotation_worker = None
        # 初始化UI
        try:
            self.init_ui()
        except Exception as e:
            msg = f"AnalysisWidget UI初始化失败: {str(e)}"
            self.log_manager.error(msg)
            self.error_occurred.emit(msg)
        try:
            self.log_manager.info("初始化分析控件主题")
            self.theme_manager = get_theme_manager(
                config_manager or ConfigManager())
            self.theme_manager.theme_changed.connect(lambda _: self.theme_manager.apply_theme(self))
            self.theme_manager.apply_theme(self)
            self.log_manager.info("初始化分析控件主题完成")
        except Exception as e:
            msg = f"AnalysisWidget主题应用失败: {str(e)}"
            self.log_manager.error(msg)
            self.error_occurred.emit(msg)
        # 自动连接RotationWorker信号
        self._connect_rotation_worker_signals()

    def init_ui(self):
        """初始化UI"""
        try:
            self.log_manager.info("初始化分析控件UI")
            # 创建主布局
            if self.layout() is None:
                self.main_layout = QVBoxLayout(self)
                self.setLayout(self.main_layout)
            else:
                self.main_layout = self.layout()
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
            # 新增舆情报告Tab
            sentiment_report_tab = self.create_sentiment_report_tab()
            tab_widget.addTab(sentiment_report_tab, "舆情报告")
            # 添加标签页到布局
            if tab_widget.parent() is not self.main_layout:
                self.main_layout.addWidget(tab_widget)
        except Exception as e:
            self.log_manager.log(
                f"初始化分析控件UI失败: {str(e)}", LogLevel.ERROR)
            raise

    def run_button_analysis_async(self, button, analysis_func, *args, **kwargs):
        """
        通用按钮防抖+异步分析工具，点击后按钮文本变为"取消"，再次点击时中断分析，结束后恢复原文本。
        修复：保证分析结束后按钮状态恢复，异常时也能恢复，防止按钮卡死。
        """
        original_text = button.text()
        button.setText("取消")
        button.setEnabled(False)

        def on_cancel():
            button._interrupted = True
            button.setText(original_text)
            button.setEnabled(True)

        # 绑定取消逻辑
        try:
            button.clicked.disconnect()
        except Exception:
            pass
        button.clicked.connect(on_cancel)

        def task():
            try:
                if not getattr(button, '_interrupted', False):
                    analysis_func(*args, **kwargs)
            except Exception as e:
                msg = f"分析异常: {str(e)}"
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(msg)
                self.error_occurred.emit(msg)

        def on_done(future):
            button.setText(original_text)
            button.setEnabled(True)
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda: self.run_button_analysis_async(
                button, analysis_func, *args, **kwargs))
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task)
        future.add_done_callback(
            lambda f: QTimer.singleShot(0, lambda: on_done(f)))

    def create_technical_tab(self) -> QWidget:
        """创建技术分析标签页，仅展示指标分析结果，参数来源于主窗口统一接口"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # 只保留指标分析结果表格
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
            calculate_button = QPushButton("刷新分析")
            calculate_button.clicked.connect(lambda: self.run_button_analysis_async(
                calculate_button, self.calculate_indicators))
            button_layout.addWidget(calculate_button)
            clear_button = QPushButton("清除分析")
            clear_button.clicked.connect(lambda: self.run_button_analysis_async(
                clear_button, self.clear_indicators))
            button_layout.addWidget(clear_button)
            layout.addLayout(button_layout)

            return widget
        except Exception as e:
            self.log_manager.log(
                f"创建技术分析标签页失败: {str(e)}", LogLevel.ERROR)
            raise

    def calculate_indicators(self):
        start_time = time.time()
        self.log_manager.info("[AnalysisWidget.calculate_indicators] 开始")
        try:
            self.indicator_table.setRowCount(0)
            if not self.current_kdata:
                self.indicator_table.setRowCount(1)
                for col in range(self.indicator_table.columnCount()):
                    self.indicator_table.setItem(
                        0, col, QTableWidgetItem("无数据"))
                return
            from indicators_algo import get_talib_indicator_list, get_all_indicators_by_category
            talib_list = get_talib_indicator_list()
            category_map = get_all_indicators_by_category()
            if not talib_list or not category_map:
                self.indicator_table.setRowCount(1)
                for col in range(self.indicator_table.columnCount()):
                    self.indicator_table.setItem(
                        0, col, QTableWidgetItem("无数据"))
                self.log_manager.log(
                    "未检测到任何ta-lib指标，请检查ta-lib安装或数据源！", LogLevel.ERROR)
                return
            main_window = self.parentWidget()
            while main_window and not hasattr(main_window, 'get_current_indicators'):
                main_window = main_window.parentWidget()
            if not main_window or not hasattr(main_window, 'get_current_indicators'):
                self.indicator_table.setRowCount(1)
                for col in range(self.indicator_table.columnCount()):
                    self.indicator_table.setItem(
                        0, col, QTableWidgetItem("无数据"))
                self.log_manager.log("未找到主窗口统一指标接口", LogLevel.ERROR)
                return
            indicators = main_window.get_current_indicators()
            if not indicators:
                self.indicator_table.setRowCount(1)
                for col in range(self.indicator_table.columnCount()):
                    self.indicator_table.setItem(
                        0, col, QTableWidgetItem("无数据"))
                return
            row_idx = 0
            for ind in indicators:
                name = ind.get('name')
                params = ind.get('params', {})
                ind_type = ind.get('type', '')
                value, status, suggestion = "-", "-", "观望"
                try:
                    if name.startswith('MA'):
                        ma = self.calculate_ma(params)
                        if ma is not None and len(ma) > 0:
                            value = f"{ma[-1]:.2f}"
                            close = self.current_kdata['close']
                            if close[-1] > ma[-1]:
                                status = "金叉"
                                suggestion = "买入"
                            else:
                                status = "死叉"
                                suggestion = "卖出"
                    elif name == 'MACD':
                        macd = self.calculate_macd(params)
                        if macd is not None and isinstance(macd, tuple) and len(macd) == 3:
                            dif, dea, hist = macd
                            value = f"DIF:{dif[-1]:.2f} DEA:{dea[-1]:.2f}"
                            if dif[-1] > dea[-1]:
                                status = "金叉"
                                suggestion = "买入"
                            else:
                                status = "死叉"
                                suggestion = "卖出"
                    elif name == 'KDJ':
                        kdj = self.calculate_kdj(params)
                        if kdj is not None and isinstance(kdj, tuple) and len(kdj) == 3:
                            k, d, j = kdj
                            value = f"K:{k[-1]:.2f} D:{d[-1]:.2f} J:{j[-1]:.2f}"
                            if k[-1] > d[-1]:
                                status = "多头"
                                suggestion = "买入"
                            else:
                                status = "空头"
                                suggestion = "卖出"
                    elif name == 'RSI':
                        rsi = self.calculate_rsi(params)
                        if rsi is not None and len(rsi) > 0:
                            value = f"{rsi[-1]:.2f}"
                            if rsi[-1] > 70:
                                status = "超买"
                                suggestion = "卖出"
                            elif rsi[-1] < 30:
                                status = "超卖"
                                suggestion = "买入"
                            else:
                                status = "中性"
                                suggestion = "观望"
                    elif name == 'BOLL':
                        boll = self.calculate_boll(params)
                        if boll is not None and isinstance(boll, tuple) and len(boll) == 3:
                            mid, upper, lower = boll
                            value = f"中轨:{mid[-1]:.2f} 上轨:{upper[-1]:.2f} 下轨:{lower[-1]:.2f}"
                            close = self.current_kdata['close']
                            if close[-1] > upper[-1]:
                                status = "突破上轨"
                                suggestion = "卖出"
                            elif close[-1] < lower[-1]:
                                status = "跌破下轨"
                                suggestion = "买入"
                            else:
                                status = "区间"
                                suggestion = "观望"
                    elif name == 'ATR':
                        atr = self.calculate_atr(params)
                        if atr is not None and len(atr) > 0:
                            value = f"{atr[-1]:.2f}"
                            status = "波动率"
                            suggestion = "观望"
                    elif name == 'OBV':
                        obv = self.calculate_obv(params)
                        if obv is not None and len(obv) > 0:
                            value = f"{obv[-1]:.2f}"
                            status = "量能"
                            suggestion = "观望"
                    elif name == 'CCI':
                        cci = self.calculate_cci(params)
                        if cci is not None and len(cci) > 0:
                            value = f"{cci[-1]:.2f}"
                            if cci[-1] > 100:
                                status = "超买"
                                suggestion = "卖出"
                            elif cci[-1] < -100:
                                status = "超卖"
                                suggestion = "买入"
                            else:
                                status = "中性"
                                suggestion = "观望"
                    # 结果填充
                    self.indicator_table.insertRow(row_idx)
                    self.indicator_table.setItem(
                        row_idx, 0, QTableWidgetItem(name))
                    self.indicator_table.setItem(
                        row_idx, 1, QTableWidgetItem(value))
                    self.indicator_table.setItem(
                        row_idx, 2, QTableWidgetItem(status))
                    self.indicator_table.setItem(
                        row_idx, 3, QTableWidgetItem(suggestion))
                    row_idx += 1
                except Exception as e:
                    self.log_manager.log(
                        f"分析指标{name}异常: {str(e)}", LogLevel.ERROR)
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self, "分析异常", f"分析指标{name}异常: {str(e)}")
            if row_idx == 0:
                self.indicator_table.setRowCount(1)
                for col in range(self.indicator_table.columnCount()):
                    self.indicator_table.setItem(
                        0, col, QTableWidgetItem("无数据"))
            self.indicator_table.resizeColumnsToContents()
        except Exception as e:
            self.log_manager.log(f"计算技术指标失败: {str(e)}", LogLevel.ERROR)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "分析异常", f"计算技术指标失败: {str(e)}")
        finally:
            elapsed = int((time.time() - start_time) * 1000)
            self.log_manager.performance(
                f"[AnalysisWidget.calculate_indicators] 结束，耗时: {elapsed} ms")

    def calculate_ma(self, params=None):
        """计算MA指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            period = params.get('period', 20) if params else 20
            return calc_ma(self.current_kdata['close'], period)
        except Exception as e:
            self.log_manager.log(
                f"计算MA指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_macd(self, params=None):
        """计算MACD指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            fast = params.get('fast', 12) if params else 12
            slow = params.get('slow', 26) if params else 26
            signal = params.get('signal', 9) if params else 9
            return calc_macd(self.current_kdata['close'], fast, slow, signal)
        except Exception as e:
            self.log_manager.log(
                f"计算MACD指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_kdj(self, params=None):
        """计算KDJ指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            n = params.get('n', 9) if params else 9
            m1 = params.get('m1', 3) if params else 3
            m2 = params.get('m2', 3) if params else 3
            return calc_kdj(self.current_kdata, n, m1, m2)
        except Exception as e:
            self.log_manager.log(
                f"计算KDJ指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_rsi(self, params=None):
        """计算RSI指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            period = params.get('period', 14) if params else 14
            return calc_rsi(self.current_kdata['close'], period)
        except Exception as e:
            self.log_manager.log(
                f"计算RSI指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_boll(self, params=None):
        """计算BOLL指标，参数从主窗口统一接口获取"""
        try:
            if self.current_kdata is None:
                return None
            period = params.get('period', 20) if params else 20
            std = params.get('std', 2) if params else 2
            return calc_boll(self.current_kdata['close'], period, std)
        except Exception as e:
            self.log_manager.log(
                f"计算BOLL指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_atr(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            n = params.get('period', 14) if params else 14
            return calc_atr(self.current_kdata, n)
        except Exception as e:
            self.log_manager.log(f"计算ATR指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_obv(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            return calc_obv(self.current_kdata)
        except Exception as e:
            self.log_manager.log(f"计算OBV指标失败: {str(e)}", LogLevel.ERROR)

    def calculate_cci(self, params=None):
        try:
            if self.current_kdata is None:
                return None
            n = params.get('period', 14) if params else 14
            return calc_cci(self.current_kdata, n)
        except Exception as e:
            self.log_manager.log(f"计算CCI指标失败: {str(e)}", LogLevel.ERROR)

    def clear_indicators(self):
        """清除指标"""
        try:
            self.current_stock = None
            self.current_kdata = None
            self.current_indicators = []
            self.indicator_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(
                f"清除指标失败: {str(e)}", LogLevel.ERROR)
            raise

    def on_indicator_changed(self, text):
        """指标变更处理"""
        try:
            self.indicator_changed.emit(text)
        except Exception as e:
            self.log_manager.log(
                f"指标变更处理失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_pattern_tab(self) -> QWidget:
        """创建形态分析Tab，支持形态类型多选、参数自定义、结果表格、可视化联动"""
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QSpinBox, QDoubleSpinBox
        tab = QWidget()
        layout = QVBoxLayout(tab)
        # 形态类型多选区
        pattern_types = [
            ('hammer', '锤头线'),
            ('inverted_hammer', '倒锤头'),
            ('shooting_star', '流星线'),
            ('doji', '十字星'),
            ('marubozu', '光头光脚线'),
            ('spinning_top', '纺锤线'),
            ('engulfing', '吞没形态'),
            ('piercing', '刺透形态'),
            ('dark_cloud_cover', '乌云盖顶'),
            ('morning_star', '早晨之星'),
            ('evening_star', '黄昏之星'),
            ('three_white_soldiers', '三白兵'),
            ('three_black_crows', '三只乌鸦'),
            ('tower_top', '塔形顶'),
            ('tower_bottom', '塔形底'),
            ('flag', '旗形'),
            ('wedge', '楔形'),
            ('rectangle', '矩形整理'),
            ('channel', '通道'),
            ('head_shoulders', '头肩形'),
            ('double_tops_bottoms', '双顶/双底'),
            ('triangles', '三角形'),
        ]
        self.pattern_type_checks = []
        type_layout = QHBoxLayout()
        for key, label in pattern_types:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.pattern_key = key
            self.pattern_type_checks.append(cb)
            type_layout.addWidget(cb)
        layout.addLayout(type_layout)
        # 参数设置按钮
        param_btn = QPushButton("参数设置")

        def show_param_dialog():
            dlg = QDialog(tab)
            dlg.setWindowTitle("形态参数设置")
            form = QFormLayout(dlg)
            self.pattern_param_controls = {}
            # 仅示例部分参数
            for pname, label, default, minv, maxv, step in [
                ('hammer_shadow_ratio', '锤头影线/实体比', 2.0, 1.0, 5.0, 0.1),
                ('doji_body_ratio', '十字星实体/全K比', 0.1, 0.01, 0.3, 0.01),
                ('engulfing_min_body_ratio', '吞没最小实体比', 0.7, 0.3, 1.0, 0.05),
                ('threshold', '价格阈值', 0.02, 0.001, 0.1, 0.001),
            ]:
                spin = QDoubleSpinBox()
                spin.setRange(minv, maxv)
                spin.setSingleStep(step)
                spin.setValue(default)
                form.addRow(label, spin)
                self.pattern_param_controls[pname] = spin
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dlg.accept)
            form.addRow(ok_btn)
            if dlg.exec_() == QDialog.Accepted:
                self.pattern_params = {
                    k: v.value() for k, v in self.pattern_param_controls.items()}
        param_btn.clicked.connect(show_param_dialog)
        layout.addWidget(param_btn)
        # 识别按钮
        analyze_btn = QPushButton("识别形态")
        layout.addWidget(analyze_btn)
        # 结果表格
        self.pattern_table = QTableWidget(0, 7)
        self.pattern_table.setHorizontalHeaderLabels(
            ['形态', '信号', '置信度', '对称性', '建议', 'K线索引', '价格'])
        self.pattern_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pattern_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pattern_table)
        # 统计分析和导出按钮（预留）
        stat_btn = QPushButton("统计分析")
        export_btn = QPushButton("导出结果")
        layout.addWidget(stat_btn)
        layout.addWidget(export_btn)
        # 统计分析弹窗

        def show_stat_dialog():
            from analysis.pattern_recognition import PatternRecognizer
            from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QFormLayout, QTableWidget, QTableWidgetItem
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import numpy as np
            kdata = getattr(self, 'kdata', None)
            if kdata is None or len(kdata) < 10:
                return
            types = [
                cb.pattern_key for cb in self.pattern_type_checks if cb.isChecked()]
            params = getattr(self, 'pattern_params', {})
            recognizer = PatternRecognizer(params)
            stats = recognizer.get_pattern_statistics(
                kdata, pattern_types=types)
            # 回测结果联动
            backtest_stats = getattr(self, 'backtest_stats', None)
            dlg = QDialog(tab)
            dlg.setWindowTitle("形态统计分析")
            tabs = QTabWidget(dlg)
            # 表格Tab
            table_tab = QWidget()
            form = QFormLayout(table_tab)
            table = QTableWidget(len(stats), 4)
            table.setHorizontalHeaderLabels(['形态', '出现次数', '胜率', '平均涨跌幅'])
            for i, (pat, stat) in enumerate(stats.items()):
                table.setItem(i, 0, QTableWidgetItem(pat))
                table.setItem(i, 1, QTableWidgetItem(
                    str(stat.get('count', 0))))
                table.setItem(i, 2, QTableWidgetItem(
                    f"{stat.get('win_rate', 0):.2%}"))
                table.setItem(i, 3, QTableWidgetItem(
                    f"{stat.get('avg_return', 0):.2%}"))
            form.addRow(table)
            tabs.addTab(table_tab, "统计表格")
            # 柱状图Tab
            bar_tab = QWidget()
            bar_layout = QVBoxLayout(bar_tab)
            fig1, ax1 = plt.subplots(figsize=(6, 3))
            patterns = list(stats.keys())
            counts = [v.get('count', 0) for v in stats.values()]
            win_rates = [v.get('win_rate', 0) for v in stats.values()]
            avg_returns = [v.get('avg_return', 0) for v in stats.values()]
            x = np.arange(len(patterns))
            ax1.bar(x, counts, color='#1976d2', alpha=0.7)
            ax1.set_xticks(x)
            ax1.set_xticklabels(patterns, rotation=45, ha='right', fontsize=8)
            ax1.set_ylabel('出现次数')
            ax1.set_title('各形态出现次数')
            bar_layout.addWidget(FigureCanvas(fig1))
            fig2, ax2 = plt.subplots(figsize=(6, 3))
            ax2.bar(x, win_rates, color='#43a047', alpha=0.7)
            ax2.set_xticks(x)
            ax2.set_xticklabels(patterns, rotation=45, ha='right', fontsize=8)
            ax2.set_ylabel('胜率')
            ax2.set_title('各形态胜率')
            bar_layout.addWidget(FigureCanvas(fig2))
            fig3, ax3 = plt.subplots(figsize=(6, 3))
            ax3.bar(x, avg_returns, color='#ff9800', alpha=0.7)
            ax3.set_xticks(x)
            ax3.set_xticklabels(patterns, rotation=45, ha='right', fontsize=8)
            ax3.set_ylabel('平均涨跌幅')
            ax3.set_title('各形态平均涨跌幅')
            bar_layout.addWidget(FigureCanvas(fig3))
            tabs.addTab(bar_tab, "柱状图")
            # 饼图Tab
            pie_tab = QWidget()
            pie_layout = QVBoxLayout(pie_tab)
            fig4, ax4 = plt.subplots(figsize=(5, 4))
            ax4.pie(counts, labels=patterns, autopct='%1.1f%%', startangle=90)
            ax4.set_title('形态出现占比')
            pie_layout.addWidget(FigureCanvas(fig4))
            tabs.addTab(pie_tab, "饼图")
            # 回测联动Tab
            if backtest_stats:
                bt_tab = QWidget()
                bt_layout = QVBoxLayout(bt_tab)
                fig_bt, ax_bt = plt.subplots(figsize=(6, 3))
                bt_patterns = list(backtest_stats.keys())
                bt_win = [backtest_stats[k].get(
                    'win_rate', 0) for k in bt_patterns]
                ax_bt.bar(np.arange(len(bt_patterns)),
                          bt_win, color='#e64a19', alpha=0.7)
                ax_bt.set_xticks(np.arange(len(bt_patterns)))
                ax_bt.set_xticklabels(
                    bt_patterns, rotation=45, ha='right', fontsize=8)
                ax_bt.set_ylabel('回测胜率')
                ax_bt.set_title('各形态回测胜率')
                bt_layout.addWidget(FigureCanvas(fig_bt))
                tabs.addTab(bt_tab, "回测联动")
            vlayout = QVBoxLayout(dlg)
            vlayout.addWidget(tabs)
            ok_btn = QPushButton("关闭")
            ok_btn.clicked.connect(dlg.accept)
            vlayout.addWidget(ok_btn)
            dlg.exec_()
        stat_btn.clicked.connect(show_stat_dialog)
        # 导出功能

        def export_results():
            import pandas as pd
            from PyQt5.QtWidgets import QFileDialog
            kdata = getattr(self, 'kdata', None)
            if kdata is None or len(kdata) < 10:
                return
            # 导出识别结果
            results = []
            for row in range(self.pattern_table.rowCount()):
                row_data = {}
                for col, key in enumerate(['形态', '信号', '置信度', '对称性', '建议', 'K线索引', '价格']):
                    item = self.pattern_table.item(row, col)
                    row_data[key] = item.text() if item else ''
                results.append(row_data)
            df = pd.DataFrame(results)
            fname, _ = QFileDialog.getSaveFileName(
                tab, "导出识别结果", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
            if fname:
                if fname.endswith('.csv'):
                    df.to_csv(fname, index=False)
                else:
                    df.to_excel(fname, index=False)
            # 导出统计分析
            from analysis.pattern_recognition import PatternRecognizer
            types = [
                cb.pattern_key for cb in self.pattern_type_checks if cb.isChecked()]
            params = getattr(self, 'pattern_params', {})
            recognizer = PatternRecognizer(params)
            stats = recognizer.get_pattern_statistics(
                kdata, pattern_types=types)
            stats_df = pd.DataFrame([{**{'形态': k}, **v}
                                    for k, v in stats.items()])
            if not stats_df.empty:
                fname2, _ = QFileDialog.getSaveFileName(
                    tab, "导出统计分析", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
                if fname2:
                    if fname2.endswith('.csv'):
                        stats_df.to_csv(fname2, index=False)
                    else:
                        stats_df.to_excel(fname2, index=False)
        export_btn.clicked.connect(export_results)
        # 识别逻辑

        def do_analyze():
            from analysis.pattern_recognition import PatternRecognizer
            kdata = getattr(self, 'current_kdata', None)
            if kdata is None or (hasattr(kdata, '__len__') and len(kdata) < 10):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "提示", "K线数据为空或不足，无法进行形态分析。请先切换到有数据的股票或调整时间范围。")
                return
            types = [
                cb.pattern_key for cb in self.pattern_type_checks if cb.isChecked()]
            params = getattr(self, 'pattern_params', {})
            recognizer = PatternRecognizer(params)
            results = recognizer.get_pattern_signals(
                kdata, pattern_types=types)
            self.pattern_table.setRowCount(len(results))
            for i, pat in enumerate(results):
                # 形态类型
                self.pattern_table.setItem(i, 0, QTableWidgetItem(
                    pat.get('pattern', pat.get('type', ''))))
                # 信号
                self.pattern_table.setItem(
                    i, 1, QTableWidgetItem(pat.get('signal', '')))
                # 置信度
                self.pattern_table.setItem(i, 2, QTableWidgetItem(
                    f"{pat.get('confidence', 0):.2f}"))
                # 对称性
                self.pattern_table.setItem(
                    i, 3, QTableWidgetItem(f"{pat.get('symmetry', 0):.2f}"))
                # 建议
                advice = pat.get('advice', None)
                if not advice:
                    # 自动推断建议
                    if pat.get('signal', '') == 'buy':
                        advice = '买入'
                    elif pat.get('signal', '') == 'sell':
                        advice = '卖出'
                    else:
                        advice = '观望'
                self.pattern_table.setItem(i, 4, QTableWidgetItem(advice))
                # K线索引
                idx = pat.get('index', None)
                if idx is None:
                    # 兼容头肩顶/底等结构
                    idx = pat.get('head', (None,))[0]
                self.pattern_table.setItem(i, 5, QTableWidgetItem(
                    str(idx) if idx is not None else ''))
                # 价格
                price = pat.get('price', None)
                if price is None:
                    # 兼容头肩顶/底等结构
                    price = pat.get('head', (None, None))[1]
                self.pattern_table.setItem(i, 6, QTableWidgetItem(
                    str(price) if price is not None else ''))
            # 结果传递到主窗口/ChartWidget
            if hasattr(self.parent(), 'parent') and callable(getattr(self.parent(), 'parent', None)):
                mainwin = self.parent().parent()
                if hasattr(mainwin, 'chart_widget'):
                    mainwin.chart_widget.plot_patterns(results)
            # 也可通过信号传递
            if hasattr(self, 'analysis_completed'):
                self.analysis_completed.emit({'pattern_signals': results})
        analyze_btn.clicked.connect(do_analyze)
        # 表格点击定位K线

        def on_table_click(row, col):
            idx = self.pattern_table.item(row, 5)
            if idx:
                idx = int(idx.text())
                if hasattr(self.parent(), 'parent') and callable(getattr(self.parent(), 'parent', None)):
                    mainwin = self.parent().parent()
                    if hasattr(mainwin, 'chart_widget') and hasattr(mainwin.chart_widget, 'price_ax'):
                        ax = mainwin.chart_widget.price_ax
                        ax.axvline(idx, color='#ff1744', lw=2,
                                   ls='--', alpha=0.7, zorder=100)
                        mainwin.chart_widget.canvas.draw_idle()
        self.pattern_table.cellClicked.connect(on_table_click)
        return tab

    def identify_patterns(self):
        """识别形态，支持更多K线形态，结果表格展示新形态"""
        try:
            self.pattern_table.setRowCount(0)
            kdata = self.current_kdata
            if kdata is None:
                self.log_manager.warning("K线数据为空，无法进行形态识别")
                self.pattern_table.setRowCount(1)
                for col in range(self.pattern_table.columnCount()):
                    self.pattern_table.setItem(0, col, QTableWidgetItem("无数据"))
                return
            import pandas as pd
            from core.data_manager import data_manager as global_data_manager
            if isinstance(kdata, pd.DataFrame):
                kdata_for_pattern = kdata.copy()
                if 'code' not in kdata_for_pattern.columns:
                    code = None
                    if hasattr(self, 'current_stock') and self.current_stock:
                        code = getattr(self, 'current_stock', None)
                    if not code and hasattr(self, 'selected_code'):
                        code = getattr(self, 'selected_code', None)
                    if not code and hasattr(self, 'code'):
                        code = getattr(self, 'code', None)
                    if code:
                        kdata_for_pattern['code'] = code
                # 先用高级特征扩展K线形态
                kdata_for_pattern = create_pattern_recognition_features(
                    kdata_for_pattern)
            else:
                kdata_for_pattern = kdata
            from analysis.pattern_recognition import PatternRecognizer
            recognizer = PatternRecognizer()
            found = False
            threshold = self.threshold_spin.value() / 100
            min_size = self.min_size_spin.value()
            # 形态与方法映射
            pattern_map = {
                "头肩顶/底": recognizer.find_head_shoulders,
                "双顶/双底": recognizer.find_double_tops_bottoms,
                "上升/下降三角形": recognizer.find_triangles,
            }
            # 新增K线形态直接用DataFrame特征
            kline_feature_map = {
                "锤子线": lambda df: df[df['is_hammer'] == 1].index.tolist(),
                "吞没形态": lambda df: df[(df['bullish_engulfing'] == 1) | (df['bearish_engulfing'] == 1)].index.tolist(),
                "启明星": lambda df: df[df['morning_star'] == 1].index.tolist(),
                "黄昏星": lambda df: df[df['evening_star'] == 1].index.tolist(),
                "三白兵": lambda df: df[df['three_white_soldiers'] == 1].index.tolist(),
                "三只乌鸦": lambda df: df[df['three_black_crows'] == 1].index.tolist(),
                "十字星": lambda df: df[df['is_doji'] == 1].index.tolist(),
                "星线": lambda df: df[df['is_star'] == 1].index.tolist(),
            }
            for pattern, check in self.pattern_checks.items():
                if not check.isChecked():
                    continue
                func = pattern_map.get(pattern)
                if func is not None:
                    try:
                        results = func(kdata_for_pattern, threshold)
                    except Exception as e:
                        self.log_manager.log(
                            f"{pattern}识别异常: {str(e)}", LogLevel.ERROR)
                        continue
                    if results:
                        found = True
                        for res in results:
                            row = self.pattern_table.rowCount()
                            self.pattern_table.insertRow(row)
                            # 结果展示格式
                            if res.get('type') == 'head_shoulders_top':
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem("头肩顶"))
                            elif res.get('type') == 'head_shoulders_bottom':
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem("头肩底"))
                            elif res.get('type') == 'double_top':
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem("双顶"))
                            elif res.get('type') == 'double_bottom':
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem("双底"))
                            elif 'triangle' in res.get('type', ''):
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem(res.get('type', pattern)))
                            else:
                                self.pattern_table.setItem(
                                    row, 0, QTableWidgetItem(res.get('type', pattern)))
                            # 位置
                            pos = str(res.get('left_shoulder',
                                              res.get('peak1', (None,)))[0])
                            self.pattern_table.setItem(
                                row, 1, QTableWidgetItem(pos))
                            # 可信度
                            conf = f"{res.get('confidence', 0):.2f}"
                            self.pattern_table.setItem(
                                row, 2, QTableWidgetItem(conf))
                            # 建议
                            advice = "买入" if res.get('signal', '') == 'buy' else (
                                "卖出" if res.get('signal', '') == 'sell' else "观望")
                            self.pattern_table.setItem(
                                row, 3, QTableWidgetItem(advice))
                elif pattern in kline_feature_map and isinstance(kdata_for_pattern, pd.DataFrame):
                    idxs = kline_feature_map[pattern](kdata_for_pattern)
                    if idxs:
                        found = True
                        for idx in idxs:
                            row = self.pattern_table.rowCount()
                            self.pattern_table.insertRow(row)
                            self.pattern_table.setItem(
                                row, 0, QTableWidgetItem(pattern))
                            self.pattern_table.setItem(
                                row, 1, QTableWidgetItem(str(idx)))
                            self.pattern_table.setItem(
                                row, 2, QTableWidgetItem("-"))
                            self.pattern_table.setItem(
                                row, 3, QTableWidgetItem("观望"))
            if not found or self.pattern_table.rowCount() == 0:
                self.pattern_table.setRowCount(1)
                for col in range(self.pattern_table.columnCount()):
                    self.pattern_table.setItem(0, col, QTableWidgetItem("无数据"))
                QMessageBox.information(
                    self, "提示", "未识别到任何典型形态，建议尝试其他股票或调整参数。")
        except Exception as e:
            self.log_manager.log(f"形态识别异常: {str(e)}", LogLevel.ERROR)
            QMessageBox.critical(self, "形态识别异常", str(e))

    def clear_patterns(self):
        """清除形态识别结果"""
        try:
            self.pattern_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(
                f"清除形态识别结果失败: {str(e)}", LogLevel.ERROR)
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
            analyze_button.clicked.connect(
                lambda: self.run_button_analysis_async(analyze_button, self.analyze_trend))
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(
                lambda: self.run_button_analysis_async(clear_button, self.clear_trend))
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            self.log_manager.log(
                f"创建趋势分析标签页失败: {str(e)}", LogLevel.ERROR)
            raise

    def analyze_trend(self):
        """分析趋势"""
        try:
            self.trend_table.setRowCount(0)
            if not self.current_kdata:
                self.trend_table.setRowCount(1)
                for col in range(self.trend_table.columnCount()):
                    self.trend_table.setItem(0, col, QTableWidgetItem("无数据"))
                return
            period = self.trend_period.value()
            threshold = self.trend_threshold.value()
            self.analyze_price_trend(period, threshold)
            self.analyze_volume_trend(period, threshold)
            self.analyze_macd_trend(period, threshold)
            self.analyze_kdj_trend(period, threshold)
            self.analyze_rsi_trend(period, threshold)
            if self.trend_table.rowCount() == 0:
                self.trend_table.setRowCount(1)
                for col in range(self.trend_table.columnCount()):
                    self.trend_table.setItem(0, col, QTableWidgetItem("无数据"))
            self.trend_table.resizeColumnsToContents()
        except Exception as e:
            self.log_manager.log(
                f"分析趋势失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(
                f"分析价格趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_volume_trend(self, period: int, threshold: float):
        """分析成交量趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            # 兼容DataFrame和KData
            if hasattr(self.current_kdata, 'volume'):
                volume = self.current_kdata.volume
            elif isinstance(self.current_kdata, dict) and 'volume' in self.current_kdata:
                volume = self.current_kdata['volume']
            elif isinstance(self.current_kdata, pd.DataFrame) and 'volume' in self.current_kdata.columns:
                volume = self.current_kdata['volume']
            else:
                from hikyuu import VOL
                volume = VOL(self.current_kdata)
            from indicators_algo import calc_ma
            ma = calc_ma(volume, period)

            trend = "放量" if float(volume[-1]) > float(ma[-1]) else "缩量"
            strength = abs(float(volume[-1]) -
                           float(ma[-1])) / float(ma[-1]) * 100

            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("成交量"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "放量" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            price_trend = self.trend_table.item(0, 1).text()
            if price_trend == "上升":
                suggestion = "买入" if trend == "放量" else "观望"
            else:
                suggestion = "卖出" if trend == "放量" else "观望"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "买入" else Qt.green if suggestion == "卖出" else Qt.black)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析成交量趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_macd_trend(self, period: int, threshold: float):
        """分析MACD趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            # 兼容DataFrame和KData
            if isinstance(self.current_kdata, pd.DataFrame):
                from indicators_algo import calc_macd
                dif, dea, hist = calc_macd(self.current_kdata['close'])
            else:
                macd = MACD(self.current_kdata)
                # 兼容属性和tuple
                if hasattr(macd, 'dif') and hasattr(macd, 'dea'):
                    dif, dea = macd.dif, macd.dea
                elif isinstance(macd, tuple) and len(macd) >= 2:
                    dif, dea = macd[0], macd[1]
                else:
                    raise ValueError("MACD结果格式不支持")
            trend = "多头" if float(dif[-1]) > float(dea[-1]) else "空头"
            strength = abs(float(dif[-1]) - float(dea[-1])) * 100
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("MACD"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "多头" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "多头" else Qt.green)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析MACD趋势失败: {str(e)}", LogLevel.ERROR)

    def analyze_kdj_trend(self, period: int, threshold: float):
        """分析KDJ趋势

        Args:
            period: 趋势周期
            threshold: 趋势阈值
        """
        try:
            # 兼容DataFrame和KData
            if isinstance(self.current_kdata, pd.DataFrame):
                from indicators_algo import calc_kdj
                k, d, j = calc_kdj(self.current_kdata)
            else:
                kdj = KDJ(self.current_kdata)
                # 兼容属性和tuple
                if hasattr(kdj, 'k') and hasattr(kdj, 'd'):
                    k, d = kdj.k, kdj.d
                elif isinstance(kdj, tuple) and len(kdj) >= 2:
                    k, d = kdj[0], kdj[1]
                else:
                    raise ValueError("KDJ结果格式不支持")
            trend = "多头" if float(k[-1]) > float(d[-1]) else "空头"
            strength = abs(float(k[-1]) - float(d[-1]))
            row = self.trend_table.rowCount()
            self.trend_table.insertRow(row)
            self.trend_table.setItem(row, 0, QTableWidgetItem("KDJ"))
            trend_item = QTableWidgetItem(trend)
            trend_item.setForeground(Qt.red if trend == "多头" else Qt.green)
            self.trend_table.setItem(row, 1, trend_item)
            self.trend_table.setItem(
                row, 2, QTableWidgetItem(f"{strength:.1f}%"))
            suggestion = "买入" if trend == "多头" else "卖出"
            suggestion_item = QTableWidgetItem(suggestion)
            suggestion_item.setForeground(
                Qt.red if suggestion == "多头" else Qt.green)
            self.trend_table.setItem(row, 3, suggestion_item)
        except Exception as e:
            self.log_manager.log(f"分析KDJ趋势失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(
                f"分析RSI趋势失败: {str(e)}", LogLevel.ERROR)

    def clear_trend(self):
        """清除趋势分析结果"""
        try:
            self.trend_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(
                f"清除趋势分析结果失败: {str(e)}", LogLevel.ERROR)
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
            analyze_button.clicked.connect(
                lambda: self.run_button_analysis_async(analyze_button, self.analyze_wave))
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(
                lambda: self.run_button_analysis_async(clear_button, self.clear_wave))
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            self.log_manager.log(
                f"创建波浪分析标签页失败: {str(e)}", LogLevel.ERROR)
            raise

    def analyze_wave(self):
        """分析波浪"""
        try:
            self.wave_table.setRowCount(0)
            if not self.current_kdata:
                self.wave_table.setRowCount(1)
                for col in range(self.wave_table.columnCount()):
                    self.wave_table.setItem(0, col, QTableWidgetItem("无数据"))
                return
            wave_type = self.wave_type.currentText()
            period = self.wave_period.value()
            sensitivity = self.wave_sensitivity.value()
            if wave_type == "艾略特波浪":
                self.analyze_elliott_waves(period, sensitivity)
            elif wave_type == "江恩理论":
                self.analyze_gann(period, sensitivity)
            elif wave_type == "支撑阻力位":
                self.analyze_support_resistance(period, sensitivity)
            if self.wave_table.rowCount() == 0:
                self.wave_table.setRowCount(1)
                for col in range(self.wave_table.columnCount()):
                    self.wave_table.setItem(0, col, QTableWidgetItem("无数据"))
            self.wave_table.resizeColumnsToContents()
        except Exception as e:
            self.log_manager.log(
                f"分析波浪失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(f"分析艾略特波浪失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(f"分析江恩理论失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(f"分析支撑阻力位失败: {str(e)}", LogLevel.ERROR)

    def clear_wave(self):
        """清除波浪分析结果"""
        try:
            self.wave_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除波浪分析结果失败: {str(e)}", LogLevel.ERROR)
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
            analyze_button.clicked.connect(lambda: self.run_button_analysis_async(
                analyze_button, self.analyze_sentiment))
            button_layout.addWidget(analyze_button)

            history_button = QPushButton("历史趋势")
            history_button.clicked.connect(lambda: self.run_button_analysis_async(
                history_button, self.analyze_history))
            button_layout.addWidget(history_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(lambda: self.run_button_analysis_async(
                clear_button, self.clear_sentiment))
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            self.log_manager.log(f"创建市场情绪分析标签页失败: {str(e)}", LogLevel.ERROR)
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
            self.log_manager.log(f"分析市场情绪失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(f"分析历史趋势失败: {str(e)}", LogLevel.ERROR)

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
            self.log_manager.log(f"添加历史趋势行失败: {str(e)}", LogLevel.ERROR)
            raise

    def clear_sentiment(self):
        """清除市场情绪分析结果"""
        try:
            self.sentiment_table.setRowCount(0)
            self.history_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除市场情绪分析结果失败: {str(e)}", LogLevel.ERROR)
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
            analyze_button.clicked.connect(lambda: self.run_button_analysis_async(
                analyze_button, self.analyze_sector_flow))
            button_layout.addWidget(analyze_button)

            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(lambda: self.run_button_analysis_async(
                clear_button, self.clear_sector_flow))
            button_layout.addWidget(clear_button)

            layout.addLayout(button_layout)

            return widget

        except Exception as e:
            self.log_manager.log(f"创建板块资金流向分析标签页失败: {str(e)}", LogLevel.ERROR)
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
            self.log_manager.log(f"分析板块资金流向失败: {str(e)}", LogLevel.ERROR)

    def analyze_industry_flow(self):
        """分析行业资金流向，表格+60日走势图，使用akshare stock_fund_flow_industry"""
        try:
            self.industry_flow_table.setRowCount(0)
            df = ak.stock_fund_flow_industry()
            if df is not None and not df.empty:
                for i, row in df.iterrows():
                    self.industry_flow_table.insertRow(i)
                    self.industry_flow_table.setItem(
                        i, 0, QTableWidgetItem(str(row.get('行业名称', ''))))
                    main_item = QTableWidgetItem(str(row.get('主力净流入', '')))
                    main_item.setForeground(
                        QColor("red" if float(row.get('主力净流入', 0)) > 0 else "green"))
                    self.industry_flow_table.setItem(i, 1, main_item)
                    super_item = QTableWidgetItem(str(row.get('超大单净流入', '')))
                    self.industry_flow_table.setItem(i, 2, super_item)
                    big_item = QTableWidgetItem(str(row.get('大单净流入', '')))
                    self.industry_flow_table.setItem(i, 3, big_item)
                    mid_item = QTableWidgetItem(str(row.get('中单净流入', '')))
                    self.industry_flow_table.setItem(i, 4, mid_item)
            else:
                self.log_manager.log("行业资金流向无数据", LogLevel.WARNING)
        except Exception as e:
            msg = f"行业资金流向分析失败: {str(e)}"
            self.log_manager.log(msg, LogLevel.ERROR)
            self.error_occurred.emit(msg)
        # 60日走势图
        try:
            # 取前5大行业做示例
            if df is not None and not df.empty:
                self.plot_industry_trend(df.head(5))
        except Exception as e:
            msg = f"行业资金流向走势图失败: {str(e)}"
            self.log_manager.log(msg, LogLevel.ERROR)
            self.error_occurred.emit(msg)

    def plot_industry_trend(self, df):
        """行业资金流向60日走势图（示例：主力净流入）"""
        try:
            for _, row in df.iterrows():
                name = row.get('行业名称', '')
                try:
                    # akshare官方接口
                    hist = ak.stock_sector_fund_flow_hist(
                        symbol=name, sector_type="行业资金流")
                    if hist is not None and not hist.empty:
                        fig = Figure(figsize=(5, 3))
                        canvas = FigureCanvas(fig)
                        ax = fig.add_subplot(111)
                        ax.plot(hist['日期'], hist['主力净流入'], label=name)
                        ax.set_title(f"{name}近60日主力净流入")
                        ax.legend()
                        self.industry_trend_layout.addWidget(canvas)
                except Exception as e:
                    self.log_manager.log(
                        f"行业{name}资金流向历史获取失败: {str(e)}", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"行业资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def analyze_concept_flow(self):
        """分析概念资金流向，表格+60日走势图，使用akshare stock_fund_flow_concept"""
        try:
            self.concept_flow_table.setRowCount(0)
            df = ak.stock_fund_flow_concept()
            if df is not None and not df.empty:
                for i, row in df.iterrows():
                    self.concept_flow_table.insertRow(i)
                    self.concept_flow_table.setItem(
                        i, 0, QTableWidgetItem(str(row.get('概念名称', ''))))
                    main_item = QTableWidgetItem(str(row.get('主力净流入', '')))
                    main_item.setForeground(
                        QColor("red" if float(row.get('主力净流入', 0)) > 0 else "green"))
                    self.concept_flow_table.setItem(i, 1, main_item)
                    super_item = QTableWidgetItem(str(row.get('超大单净流入', '')))
                    self.concept_flow_table.setItem(i, 2, super_item)
                    big_item = QTableWidgetItem(str(row.get('大单净流入', '')))
                    self.concept_flow_table.setItem(i, 3, big_item)
                    mid_item = QTableWidgetItem(str(row.get('中单净流入', '')))
                    self.concept_flow_table.setItem(i, 4, mid_item)
            else:
                self.log_manager.log("概念资金流向无数据", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"概念资金流向分析失败: {str(e)}", LogLevel.ERROR)

        # 60日走势图
        try:
            if df is not None and not df.empty:
                self.plot_concept_trend(df.head(5))
        except Exception as e:
            self.log_manager.log(f"概念资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def plot_concept_trend(self, df):
        """概念资金流向60日走势图（示例：主力净流入）"""
        try:
            for _, row in df.iterrows():
                name = row.get('概念名称', '')
                try:
                    # akshare官方接口
                    hist = ak.stock_sector_fund_flow_hist(
                        symbol=name, sector_type="概念资金流")
                    if hist is not None and not hist.empty:
                        fig = Figure(figsize=(5, 3))
                        canvas = FigureCanvas(fig)
                        ax = fig.add_subplot(111)
                        ax.plot(hist['日期'], hist['主力净流入'], label=name)
                        ax.set_title(f"{name}近60日主力净流入")
                        ax.legend()
                        self.concept_trend_layout.addWidget(canvas)
                except Exception as e:
                    self.log_manager.log(
                        f"概念{name}资金流向历史获取失败: {str(e)}", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"概念资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def analyze_north_flow(self):
        """分析北向资金，使用akshare stock_hsgt_north_net_flow_em"""
        try:
            self.north_flow_table.setRowCount(0)
            df = ak.stock_hsgt_north_net_flow_em()
            if df is not None and not df.empty:
                df = df.head(60)
                for i, row in df.iterrows():
                    date = row['日期']
                    sh = row['沪股通(亿元)']
                    sz = row['深股通(亿元)']
                    total = row['北向资金(亿元)']
                    self.north_flow_table.insertRow(i)
                    self.north_flow_table.setItem(
                        i, 0, QTableWidgetItem(str(date)))
                    self.north_flow_table.setItem(
                        i, 1, QTableWidgetItem(f"{sh:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 2, QTableWidgetItem(f"{sz:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 3, QTableWidgetItem(f"{total:+.2f}"))
            else:
                self.log_manager.log("北向资金无数据", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"北向资金分析失败: {str(e)}", LogLevel.ERROR)

    def clear_sector_flow(self):
        """清除板块资金流向分析结果"""
        try:
            self.industry_flow_table.setRowCount(0)
            self.concept_flow_table.setRowCount(0)
            self.north_flow_table.setRowCount(0)
        except Exception as e:
            self.log_manager.log(f"清除板块资金流向分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def create_hotspot_tab(self) -> QWidget:
        """创建热点分析标签页，热点板块、主题机会、热点轮动三表格横向并列，板块资金流向三表格也横向并列"""
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)

            # --- 热点三表格横向并列 ---
            row_layout = QHBoxLayout()
            # 热点板块
            hotspot_group = QGroupBox("热点板块")
            hotspot_layout = QVBoxLayout()
            self.hotspot_table = QTableWidget()
            self.hotspot_table.setColumnCount(7)
            self.hotspot_table.setHorizontalHeaderLabels([
                "板块名称", "涨跌幅", "领涨股", "涨跌幅", "成交额", "换手率", "板块强度"
            ])
            self.hotspot_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            hotspot_layout.addWidget(self.hotspot_table)
            hotspot_group.setLayout(hotspot_layout)
            row_layout.addWidget(hotspot_group, 1)
            row_layout.addSpacing(20)
            # 主题机会
            theme_group = QGroupBox("主题机会")
            theme_layout = QVBoxLayout()
            self.theme_table = QTableWidget()
            self.theme_table.setColumnCount(6)
            self.theme_table.setHorizontalHeaderLabels([
                "主题名称", "相关股票数", "平均涨跌幅", "资金净流入", "热度指数", "轮动指数"
            ])
            self.theme_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            theme_layout.addWidget(self.theme_table)
            theme_group.setLayout(theme_layout)
            row_layout.addWidget(theme_group, 1)
            row_layout.addSpacing(20)
            # 热点轮动
            rotation_group = QGroupBox("热点轮动")
            rotation_layout = QVBoxLayout()
            self.rotation_table = QTableWidget()
            self.rotation_table.setColumnCount(5)
            self.rotation_table.setHorizontalHeaderLabels([
                "轮动板块", "上升趋势", "资金流入", "持续天数", "轮动建议"
            ])
            self.rotation_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            rotation_layout.addWidget(self.rotation_table)
            rotation_group.setLayout(rotation_layout)
            row_layout.addWidget(rotation_group, 1)
            layout.addLayout(row_layout)

            # --- 板块资金流向三表格横向并列 ---
            sector_row_layout = QHBoxLayout()
            # 行业资金流向
            industry_group = QGroupBox("行业资金流向")
            industry_layout = QVBoxLayout()
            self.industry_flow_table = QTableWidget()
            self.industry_flow_table.setColumnCount(5)
            self.industry_flow_table.setHorizontalHeaderLabels([
                "行业", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            industry_layout.addWidget(self.industry_flow_table)
            industry_group.setLayout(industry_layout)
            sector_row_layout.addWidget(industry_group, 1)
            sector_row_layout.addSpacing(20)
            # 概念资金流向
            concept_group = QGroupBox("概念资金流向")
            concept_layout = QVBoxLayout()
            self.concept_flow_table = QTableWidget()
            self.concept_flow_table.setColumnCount(5)
            self.concept_flow_table.setHorizontalHeaderLabels([
                "概念", "主力净流入", "超大单净流入", "大单净流入", "中单净流入"
            ])
            concept_layout.addWidget(self.concept_flow_table)
            concept_group.setLayout(concept_layout)
            sector_row_layout.addWidget(concept_group, 1)
            sector_row_layout.addSpacing(20)
            # 北向资金
            north_group = QGroupBox("北向资金")
            north_layout = QVBoxLayout()
            self.north_flow_table = QTableWidget()
            self.north_flow_table.setColumnCount(4)
            self.north_flow_table.setHorizontalHeaderLabels([
                "时间", "沪股通", "深股通", "合计"
            ])
            north_layout.addWidget(self.north_flow_table)
            north_group.setLayout(north_layout)
            sector_row_layout.addWidget(north_group, 1)
            layout.addLayout(sector_row_layout)

            # 龙头股
            leader_group = QGroupBox("龙头股")
            leader_layout = QVBoxLayout()
            self.leader_table = QTableWidget()
            self.leader_table.setColumnCount(15)
            self.leader_table.setHorizontalHeaderLabels([
                "股票名称", "股票代码", "所属板块", "是否ST", "市值(亿)", "涨跌幅", "近5日涨跌幅", "成交额(亿)", "换手率(%)", "振幅(%)", "量比", "主力净流入(亿)", "主力净流入占比(%)", "涨停状态", "资金流向趋势(5日)", "综合得分"
            ])
            self.leader_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            leader_layout.addWidget(self.leader_table)
            leader_group.setLayout(leader_layout)
            layout.addWidget(leader_group)

            # 按钮区和进度条
            button_layout = QHBoxLayout()
            self.rotation_button = QPushButton("分析轮动")
            self.rotation_button.clicked.connect(self.toggle_rotation_analysis)
            button_layout.addWidget(self.rotation_button)
            clear_button = QPushButton("清除结果")
            clear_button.clicked.connect(
                lambda: self.run_button_analysis_async(clear_button, self.clear_hotspot))
            button_layout.addWidget(clear_button)
            layout.addLayout(button_layout)
            return widget
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"创建热点分析标签页失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"创建热点分析标签页失败: {str(e)}")
            raise

    def toggle_rotation_analysis(self):
        """
        合并分析轮动与中断分析按钮逻辑。
        """
        if self.rotation_button.text() == "分析轮动":
            self._rotation_interrupted = False
            self.rotation_button.setText("中断分析")
            self.start_all_hotspot_analysis()
        else:
            self.interrupt_rotation_analysis()
            self.rotation_button.setText("分析轮动")

    def start_all_hotspot_analysis(self):
        """
        合并所有热点分析功能，点击分析轮动后并发执行所有分析，动态渲染表格，轮动分析用QThread后台执行，避免Qt定时器错误和主界面卡顿。
        """
        if hasattr(self, 'rotation_worker') and self.rotation_worker and self.rotation_worker.isRunning():
            return
        self.rotation_button.setEnabled(False)
        self.rotation_button.setText("分析轮动")

        # 优化：将run_others放到QThread中执行，彻底避免主线程卡顿
        from PyQt5.QtCore import QThread, pyqtSignal
        import types

        class OthersWorker(QThread):
            error = pyqtSignal(str)

            def __init__(self, widget):
                super().__init__()
                self.widget = widget

            def run(self):
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=6) as executor:
                        futures = []
                        futures.append(executor.submit(
                            self.widget.analyze_hotspot_sectors))
                        futures.append(executor.submit(
                            self.widget.analyze_theme_opportunities))
                        futures.append(executor.submit(
                            self.widget.analyze_leading_stocks))
                        futures.append(executor.submit(
                            self.widget.analyze_industry_flow))
                        futures.append(executor.submit(
                            self.widget.analyze_concept_flow))
                        futures.append(executor.submit(
                            self.widget.analyze_north_flow))
                        for f in futures:
                            try:
                                f.result()
                            except Exception as e:
                                if hasattr(self.widget, 'log_manager'):
                                    self.widget.log_manager.log(
                                        f"分析任务异常: {str(e)}", LogLevel.ERROR)
                except Exception as e:
                    self.error.emit(str(e))

        self.others_worker = OthersWorker(self)
        self.others_worker.error.connect(
            lambda msg: self.log_manager.log(f"分析任务异常: {msg}", LogLevel.ERROR))
        self.others_worker.finished.connect(self._start_rotation_worker)
        self.others_worker.start()

    def _start_rotation_worker(self):
        self.rotation_worker = RotationWorker(self)
        self._connect_rotation_worker_signals()
        self.rotation_worker.finished.connect(self._on_rotation_finished)
        self.rotation_worker.error.connect(self._on_rotation_error)
        self.rotation_worker.start()

    def interrupt_rotation_analysis(self):
        """
        中断热点轮动分析
        """
        self._rotation_interrupted = True
        self.log_manager.info("用户请求中断热点轮动分析")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_status("热点轮动分析已中断")
            status_bar.set_progress(0)
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))
        # 按钮状态恢复
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")

    def _on_rotation_finished(self):
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_progress(100)
            status_bar.set_status("热点轮动分析完成")
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))

    def _on_rotation_error(self, msg):
        self.rotation_button.setEnabled(True)
        self.rotation_button.setText("分析轮动")
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_progress_error("热点轮动分析失败")
            status_bar.set_status(msg)
            QTimer.singleShot(2000, lambda: status_bar.show_progress(False))
        if hasattr(self, 'log_manager'):
            self.log_manager.error(f"热点轮动分析异常: {msg}")

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
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"分析市场热点失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析市场热点失败: {str(e)}")

    def analyze_hotspot_sectors(self):
        """多线程分析热点板块"""
        try:
            self.hotspot_table.setRowCount(0)
            sectors = []
            start_time = time.time()
            from concurrent.futures import ThreadPoolExecutor, as_completed

            block_list = [block for block in sm.get_block_list() if not isinstance(
                block, str) and hasattr(block, 'get_stock_list') and block.get_stock_list()]

            def analyze_block(block):
                try:
                    stocks = block.get_stock_list()
                    total_change = 0
                    total_amount = 0
                    total_turnover = 0
                    up_count = 0
                    leading_stock = None
                    leading_change = -100
                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-5))
                        if len(kdata) < 5:
                            continue
                        close = float(kdata[-1].close)
                        pre_close = float(kdata[-2].close)
                        change = (close - pre_close) / pre_close * 100
                        if change > 0:
                            up_count += 1
                        total_change += change
                        total_amount += float(kdata[-1].amount)
                        turnover = self._get_turnover(kdata, stock)
                        total_turnover += turnover
                        if change > leading_change:
                            leading_stock = stock
                            leading_change = change
                    if len(stocks) > 0:
                        strength = (
                            up_count / len(stocks) * 0.3 +
                            abs(total_change / len(stocks)) * 0.4 +
                            (total_turnover / len(stocks)) * 0.3
                        )
                        return {
                            'name': block.name,
                            'change': total_change / len(stocks),
                            'leading_stock': leading_stock,
                            'leading_change': leading_change,
                            'amount': total_amount / 100000000,
                            'turnover': total_turnover / len(stocks),
                            'strength': strength
                        }
                except Exception as e:
                    if hasattr(self, 'log_manager'):
                        self.log_manager.log(
                            f"板块 {getattr(block, 'name', str(block))} 统计失败: {str(e)}", LogLevel.ERROR)
                return None

            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_block = {executor.submit(
                    analyze_block, block): block for block in block_list}
                for future in as_completed(future_to_block):
                    res = future.result()
                    if res:
                        sectors.append(res)

            sectors.sort(key=lambda x: x['strength'], reverse=True)
            self.hotspot_table.setRowCount(len(sectors) if sectors else 1)
            if not sectors:
                for col in range(self.hotspot_table.columnCount()):
                    self.hotspot_table.setItem(0, col, QTableWidgetItem("无数据"))
            else:
                for i, sector in enumerate(sectors):
                    self.hotspot_table.setItem(
                        i, 0, QTableWidgetItem(sector['name']))
                    change_item = QTableWidgetItem(f"{sector['change']:+.2f}%")
                    change_item.setForeground(
                        QColor("red" if sector['change'] > 0 else "green"))
                    self.hotspot_table.setItem(i, 1, change_item)
                    if sector['leading_stock']:
                        self.hotspot_table.setItem(
                            i, 2, QTableWidgetItem(sector['leading_stock'].name))
                        leading_change_item = QTableWidgetItem(
                            f"{sector['leading_change']:+.2f}%")
                        leading_change_item.setForeground(
                            QColor("red" if sector['leading_change'] > 0 else "green"))
                        self.hotspot_table.setItem(i, 3, leading_change_item)
                    self.hotspot_table.setItem(
                        i, 4, QTableWidgetItem(f"{sector['amount']:.2f}"))
                    self.hotspot_table.setItem(
                        i, 5, QTableWidgetItem(f"{sector['turnover']:.2f}%"))
                    strength_item = QTableWidgetItem(
                        f"{sector['strength']:.2f}")
                    if sector['strength'] >= 80:
                        strength_item.setForeground(QColor("red"))
                    elif sector['strength'] >= 50:
                        strength_item.setForeground(QColor("orange"))
                    else:
                        strength_item.setForeground(QColor("green"))
                    self.hotspot_table.setItem(i, 6, strength_item)
            self.hotspot_table.resizeColumnsToContents()
            self.log_manager.log(
                f"热点板块分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.log(f"分析热点板块失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析热点板块失败: {str(e)}")

    def analyze_theme_opportunities(self):
        """分析主题机会（修复表格数据为空/列数不一致/健壮性问题）"""
        try:
            self.theme_table.setRowCount(0)
            start_time = time.time()
            themes = []
            for block in sm.get_block_list():
                block_type = getattr(block, 'type', None) or getattr(
                    block, 'category', None) or getattr(block, 'block_type', None)
                if block_type != "概念":
                    continue
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue
                    total_change = 0
                    total_flow = 0
                    stock_count = len(stocks)
                    valid_count = 0
                    for stock in stocks:
                        try:
                            kdata = stock.get_kdata(Query(-2))
                            if len(kdata) < 2:
                                continue
                            close = float(getattr(kdata[-1], 'close', 0) or 0)
                            pre_close = float(
                                getattr(kdata[-2], 'close', 0) or 0)
                            if pre_close == 0:
                                continue
                            change = (close - pre_close) / pre_close * 100
                            total_change += change
                            volume = float(
                                getattr(kdata[-1], 'volume', 0) or 0)
                            amount = float(
                                getattr(kdata[-1], 'amount', 0) or 0)
                            if volume > 0:
                                avg_price = amount / volume
                                if avg_price > float(getattr(kdata[-1], 'open', 0) or 0):
                                    total_flow += amount
                                else:
                                    total_flow -= amount
                            valid_count += 1
                        except Exception as e:
                            self.log_manager.log(
                                f"主题{block.name}单只股票异常: {str(e)}", LogLevel.WARNING)
                            continue
                    if valid_count == 0:
                        continue
                    heat_index = (
                        abs(total_change / valid_count) * 0.4 +
                        abs(total_flow) / 100000000 * 0.3 +
                        valid_count * 0.3
                    )
                    themes.append({
                        'name': getattr(block, 'name', '-') or '-',
                        'stock_count': valid_count,
                        'avg_change': total_change / valid_count if valid_count else 0,
                        'net_flow': total_flow / 100000000 if valid_count else 0,
                        'heat_index': heat_index,
                        'rotation_index': '-'  # 轮动指数暂无，预留
                    })
                except Exception as e:
                    self.log_manager.log(
                        f"计算主题 {getattr(block, 'name', '-') or '-'} 统计失败: {str(e)}", LogLevel.ERROR)
                    continue
            themes.sort(key=lambda x: x['heat_index'], reverse=True)
            if not themes:
                self.theme_table.setRowCount(1)
                for col in range(6):
                    self.theme_table.setItem(0, col, QTableWidgetItem("无数据"))
            else:
                self.theme_table.setRowCount(len(themes))
                for i, theme in enumerate(themes):
                    self.theme_table.setItem(
                        i, 0, QTableWidgetItem(str(theme['name'])))
                    self.theme_table.setItem(
                        i, 1, QTableWidgetItem(str(theme['stock_count'])))
                    change_item = QTableWidgetItem(
                        f"{theme['avg_change']:+.2f}%")
                    change_item.setForeground(
                        QColor("red") if theme['avg_change'] > 0 else QColor("green"))
                    self.theme_table.setItem(i, 2, change_item)
                    flow_item = QTableWidgetItem(f"{theme['net_flow']:+.2f}")
                    flow_item.setForeground(
                        QColor("red") if theme['net_flow'] > 0 else QColor("green"))
                    self.theme_table.setItem(i, 3, flow_item)
                    self.theme_table.setItem(
                        i, 4, QTableWidgetItem(f"{theme['heat_index']:.2f}"))
                    self.theme_table.setItem(i, 5, QTableWidgetItem(
                        str(theme.get('rotation_index', '-'))))
            self.theme_table.resizeColumnsToContents()
            self.log_manager.log(
                f"主题机会分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            self.log_manager.log(f"分析主题机会失败: {str(e)}", LogLevel.ERROR)

    def analyze_leading_stocks(self):
        """分析龙头股，合并相同股票的所属板块为一行用/分割，修复部分数据为空问题"""
        try:
            # 清空龙头股表格
            self.leader_table.setRowCount(0)
            start_time = time.time()
            # 获取所有股票的统计数据
            leaders_dict = {}
            for block in sm.get_block_list():
                try:
                    stocks = block.get_stock_list()
                    if not stocks:
                        continue
                    for stock in stocks:
                        kdata = stock.get_kdata(Query(-6))  # 取近6日，便于5日涨跌幅
                        if len(kdata) < 6:
                            continue
                        try:
                            name = getattr(stock, 'name', '-') or '-'
                            code = getattr(stock, 'code', '-') or '-'
                            block_name = getattr(block, 'name', '-') or '-'
                            is_st = 'ST' in name.upper() or getattr(stock, 'is_st', False)
                            close = float(getattr(kdata[-1], 'close', 0) or 0)
                            pre_close = float(
                                getattr(kdata[-2], 'close', 0) or 0)
                            change = (close - pre_close) / \
                                pre_close * 100 if pre_close else 0
                            # 近5日涨跌幅
                            close_5 = float(
                                getattr(kdata[-6], 'close', 0) or 0)
                            change_5 = (close - close_5) / \
                                close_5 * 100 if close_5 else 0
                            # 成交额
                            amount = float(
                                getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                            # 换手率
                            turnover = self._get_turnover(kdata, stock)
                            # 市值
                            circulating_shares = getattr(
                                stock, 'circulating_shares', None)
                            market_cap = close * circulating_shares / 1e8 if circulating_shares else '-'
                            # 振幅
                            high = float(getattr(kdata[-1], 'high', 0) or 0)
                            low = float(getattr(kdata[-1], 'low', 0) or 0)
                            amplitude = (high - low) / pre_close * \
                                100 if pre_close else 0
                            # 量比
                            volume_ratio = getattr(
                                kdata[-1], 'volume_ratio', '-')
                            if isinstance(volume_ratio, float):
                                volume_ratio = f"{volume_ratio:.2f}"
                            # 主力净流入
                            volume = float(
                                getattr(kdata[-1], 'volume', 0) or 0)
                            main_flow = 0
                            if volume > 0:
                                avg_price = float(
                                    getattr(kdata[-1], 'amount', 0) or 0) / volume
                                if avg_price > float(getattr(kdata[-1], 'open', 0) or 0):
                                    main_flow = float(
                                        getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                                else:
                                    main_flow = - \
                                        float(
                                            getattr(kdata[-1], 'amount', 0) or 0) / 1e8
                            # 主力净流入占比
                            main_flow_ratio = (
                                main_flow / amount * 100) if amount else '-'
                            if isinstance(main_flow_ratio, float):
                                main_flow_ratio = f"{main_flow_ratio:.2f}"
                            # 涨停状态
                            high_limit = getattr(kdata[-1], 'high_limit', None)
                            is_limit_up = (
                                close >= high_limit) if high_limit else '-'
                            # 资金流向趋势（近5日主力净流入为正天数）
                            flow_trend = 0
                            for i in range(-5, 0):
                                v = float(getattr(kdata[i], 'volume', 0) or 0)
                                if v > 0:
                                    avg_p = float(
                                        getattr(kdata[i], 'amount', 0) or 0) / v
                                    if avg_p > float(getattr(kdata[i], 'open', 0) or 0):
                                        flow_trend += 1
                            # 综合得分
                            score = (
                                abs(change) * 0.2 +
                                (amount if amount != '-' else 0) * 0.15 +
                                (turnover if turnover != '-' else 0) * 0.1 +
                                (abs(main_flow) if main_flow != '-' else 0) * 0.1 +
                                (abs(change_5) if change_5 != '-' else 0) * 0.15 +
                                (abs(amplitude) if amplitude != '-' else 0) * 0.1 +
                                (flow_trend if flow_trend != '-' else 0) * 0.1 +
                                (market_cap if market_cap != '-' else 0) * 0.1
                            )
                            # 合并相同股票代码的板块
                            if code not in leaders_dict:
                                leaders_dict[code] = {
                                    'name': name,
                                    'code': code,
                                    'blocks': set([block_name]),
                                    'is_st': '是' if is_st else '否',
                                    'market_cap': f"{market_cap:.2f}" if isinstance(market_cap, float) else '-',
                                    'change': change,
                                    'change_5': change_5,
                                    'amount': amount,
                                    'turnover': turnover,
                                    'amplitude': amplitude,
                                    'volume_ratio': volume_ratio,
                                    'main_flow': main_flow,
                                    'main_flow_ratio': main_flow_ratio,
                                    'is_limit_up': '涨停' if is_limit_up is True else ('-' if is_limit_up == '-' else '否'),
                                    'flow_trend': flow_trend,
                                    'score': score
                                }
                            else:
                                leaders_dict[code]['blocks'].add(block_name)
                        except Exception as e:
                            if hasattr(self, 'log_manager') and self.log_manager:
                                self.log_manager.log(
                                    f"单只股票统计失败: {str(e)}", LogLevel.ERROR)
                            continue
                except Exception as e:
                    if hasattr(self, 'log_manager') and self.log_manager:
                        self.log_manager.log(
                            f"计算股票统计失败: {str(e)}", LogLevel.ERROR)
                    continue
            # 按综合得分排序
            leaders = list(leaders_dict.values())
            leaders.sort(key=lambda x: x['score'], reverse=True)
            # 只保留前30个龙头股
            leaders = leaders[:30]
            # 更新表格
            self.leader_table.setRowCount(len(leaders))
            for i, leader in enumerate(leaders):
                self.leader_table.setItem(
                    i, 0, QTableWidgetItem(leader['name']))
                self.leader_table.setItem(
                    i, 1, QTableWidgetItem(leader['code']))
                # 合并板块名
                block_str = '/'.join(sorted(leader['blocks']))
                self.leader_table.setItem(i, 2, QTableWidgetItem(block_str))
                self.leader_table.setItem(
                    i, 3, QTableWidgetItem(leader['is_st']))
                self.leader_table.setItem(
                    i, 4, QTableWidgetItem(leader['market_cap']))
                # 涨跌幅
                change_item = QTableWidgetItem(f"{leader['change']:+.2f}%")
                change_item.setForeground(
                    QColor("red") if leader['change'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 5, change_item)
                # 近5日涨跌幅
                change5_item = QTableWidgetItem(f"{leader['change_5']:+.2f}%")
                change5_item.setForeground(
                    QColor("red") if leader['change_5'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 6, change5_item)
                # 成交额
                self.leader_table.setItem(i, 7, QTableWidgetItem(
                    f"{leader['amount']:.2f}" if leader['amount'] != '-' else '-'))
                # 换手率
                self.leader_table.setItem(i, 8, QTableWidgetItem(
                    f"{leader['turnover']:.2f}%" if leader['turnover'] != '-' else '-'))
                # 振幅
                self.leader_table.setItem(i, 9, QTableWidgetItem(
                    f"{leader['amplitude']:.2f}%" if leader['amplitude'] != '-' else '-'))
                # 量比
                self.leader_table.setItem(
                    i, 10, QTableWidgetItem(leader['volume_ratio']))
                # 主力净流入
                main_flow_item = QTableWidgetItem(
                    f"{leader['main_flow']:+.2f}" if leader['main_flow'] != '-' else '-')
                main_flow_item.setForeground(
                    QColor("red") if leader['main_flow'] > 0 else QColor("green"))
                self.leader_table.setItem(i, 11, main_flow_item)
                # 主力净流入占比
                self.leader_table.setItem(
                    i, 12, QTableWidgetItem(leader['main_flow_ratio']))
                # 涨停状态
                self.leader_table.setItem(
                    i, 13, QTableWidgetItem(leader['is_limit_up']))
                # 资金流向趋势
                self.leader_table.setItem(
                    i, 14, QTableWidgetItem(str(leader['flow_trend'])))
                # 综合得分
                self.leader_table.setItem(
                    i, 15, QTableWidgetItem(f"{leader['score']}"))
            self.leader_table.resizeColumnsToContents()
            self.log_manager.log(
                f"龙头股分析成功，用时: {time.time() - start_time:.2f}秒", LogLevel.INFO)
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.log(f"分析龙头股失败: {str(e)}", LogLevel.ERROR)
            else:
                print(f"分析龙头股失败: {str(e)}")

    def clear_hotspot(self):
        """清除热点分析结果"""
        try:
            self.hotspot_table.setRowCount(0)
            self.theme_table.setRowCount(0)
            self.leader_table.setRowCount(0)
            self.rotation_table.setRowCount(0)
            # 无数据提示
            for table in [self.hotspot_table, self.theme_table, self.leader_table, self.rotation_table]:
                if table.rowCount() == 0:
                    table.setRowCount(1)
                    for col in range(table.columnCount()):
                        table.setItem(0, col, QTableWidgetItem("无数据"))
        except Exception as e:
            self.log_manager.log(f"清除热点分析结果失败: {str(e)}", LogLevel.ERROR)
            raise

    def setup_indicator_panel(self):
        """设置指标面板"""
        panel = QWidget()
        if panel.layout() is None:
            layout = QVBoxLayout(panel)
            panel.setLayout(layout)
        else:
            layout = panel.layout()
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
        self.macd_short.setValue(7)
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

    def _get_turnover(self, kdata, stock=None) -> float:
        """
        统一换手率计算方法，兼容KRecord对象、DataFrame和stock对象
        Args:
            kdata: K线数据，支持KRecord序列或DataFrame
            stock: 股票对象（可选，用于获取流通股本）
        Returns:
            float: 换手率（%）
        """
        try:
            if kdata is None or len(kdata) == 0:
                return 0.0
            # 优先用turnover字段
            if hasattr(kdata[-1], 'turnover'):
                return float(getattr(kdata[-1], 'turnover', 0))
            elif isinstance(kdata, pd.DataFrame) and 'turnover' in kdata.columns:
                return float(kdata['turnover'].iloc[-1])
            # 其次用volume/circulating_shares估算
            elif hasattr(kdata[-1], 'volume') and stock and hasattr(stock, 'circulating_shares') and stock.circulating_shares:
                return float(kdata[-1].volume) / float(stock.circulating_shares) * 100
            elif isinstance(kdata, pd.DataFrame) and 'volume' in kdata.columns and stock and hasattr(stock, 'circulating_shares') and stock.circulating_shares:
                return float(kdata['volume'].iloc[-1]) / float(stock.circulating_shares) * 100
            else:
                return 0.0
        except Exception as e:
            self.log_manager.log(f"换手率计算失败: {str(e)}", LogLevel.ERROR)
            return 0.0

    @staticmethod
    def try_import(module_name):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            return None

    def get_industry_fund_flow_hist(self, name):
        """自动轮询数据源获取行业历史资金流向"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_board_industry_hist_em'):
                    return ak.stock_board_industry_hist_em(symbol=name, start_date="20240101", end_date="20240501")
                if hasattr(ak, 'stock_sector_fund_flow_hist'):
                    return ak.stock_sector_fund_flow_hist(symbol=name)
            except Exception as e:
                self.log_manager.log(
                    f"akshare行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_concept_fund_flow_hist(self, name):
        """自动轮询数据源获取概念历史资金流向"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_board_concept_hist_em'):
                    return ak.stock_board_concept_hist_em(symbol=name, start_date="20240101", end_date="20240501")
                if hasattr(ak, 'stock_sector_fund_flow_hist'):
                    return ak.stock_sector_fund_flow_hist(symbol=name)
            except Exception as e:
                self.log_manager.log(
                    f"akshare概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_north_fund_flow_hist(self):
        """自动轮询数据源获取北向资金历史"""
        ak = self.try_import('akshare')
        if ak:
            try:
                if hasattr(ak, 'stock_hsgt_north_net_flow'):
                    return ak.stock_hsgt_north_net_flow()
                if hasattr(ak, 'stock_hsgt_north_cash_flow'):
                    return ak.stock_hsgt_north_cash_flow()
            except Exception as e:
                self.log_manager.log(
                    f"akshare北向资金获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def plot_industry_trend(self, df):
        """行业资金流向60日走势图（自动轮询数据源）"""
        try:
            for _, row in df.iterrows():
                name = row.get('行业名称', '')
                hist = self.get_industry_fund_flow_hist(name)
                if hist is not None and not hist.empty:
                    fig = Figure(figsize=(5, 3))
                    canvas = FigureCanvas(fig)
                    ax = fig.add_subplot(111)
                    ax.plot(hist['日期'], hist.get(
                        '主力净流入', hist.columns[-1]), label=name)
                    ax.set_title(f"{name}近60日主力净流入")
                    ax.legend()
                    self.industry_trend_layout.addWidget(canvas)
                else:
                    self.log_manager.log(
                        f"行业{name}资金流向历史无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"行业资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def plot_concept_trend(self, df):
        """概念资金流向60日走势图（自动轮询数据源）"""
        try:
            for _, row in df.iterrows():
                name = row.get('概念名称', '')
                hist = self.get_concept_fund_flow_hist(name)
                if hist is not None and not hist.empty:
                    fig = Figure(figsize=(5, 3))
                    canvas = FigureCanvas(fig)
                    ax = fig.add_subplot(111)
                    ax.plot(hist['日期'], hist.get(
                        '主力净流入', hist.columns[-1]), label=name)
                    ax.set_title(f"{name}近60日主力净流入")
                    ax.legend()
                    self.concept_trend_layout.addWidget(canvas)
                else:
                    self.log_manager.log(
                        f"概念{name}资金流向历史无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"概念资金流向走势图失败: {str(e)}", LogLevel.ERROR)

    def analyze_north_flow(self):
        """分析北向资金，自动轮询数据源"""
        try:
            self.north_flow_table.setRowCount(0)
            df = self.get_north_fund_flow_hist()
            if df is not None and not df.empty:
                df = df.head(60)
                for i, row in df.iterrows():
                    date = row.get('日期', '')
                    sh = row.get('沪股通(亿元)', row.get('沪股通', 0))
                    sz = row.get('深股通(亿元)', row.get('深股通', 0))
                    total = row.get('北向资金(亿元)', row.get('北向资金', 0))
                    self.north_flow_table.insertRow(i)
                    self.north_flow_table.setItem(
                        i, 0, QTableWidgetItem(str(date)))
                    self.north_flow_table.setItem(
                        i, 1, QTableWidgetItem(f"{sh:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 2, QTableWidgetItem(f"{sz:+.2f}"))
                    self.north_flow_table.setItem(
                        i, 3, QTableWidgetItem(f"{total:+.2f}"))
            else:
                self.log_manager.log("北向资金无可用数据源", LogLevel.WARNING)
        except Exception as e:
            self.log_manager.log(f"北向资金分析失败: {str(e)}", LogLevel.ERROR)

    def get_fund_flow_with_cache(self, key, fetch_func, *args, **kwargs):
        """统一缓存+多数据源自动切换"""
        data = self.data_cache.get(key)
        if data is not None:
            return data
        data = fetch_func(*args, **kwargs)
        if data is not None and not data.empty:
            self.data_cache.set(key, data)
        return data

    def fetch_industry_fund_flow(self, industry_name):
        """轮询东方财富、Sina、同花顺获取行业资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_industry_fund_flow(industry_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺行业资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def fetch_concept_fund_flow(self, concept_name):
        """轮询东方财富、Sina、同花顺获取概念资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_concept_fund_flow(concept_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺概念资金流向获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def fetch_north_fund_flow(self):
        """轮询东方财富、Sina、同花顺获取北向资金流向"""
        try:
            from core.eastmoney_source import EastMoneyDataSource
            em = EastMoneyDataSource()
            df = em.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"东方财富北向资金获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.sina_source import SinaDataSource
            sina = SinaDataSource()
            df = sina.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"Sina北向资金获取失败: {str(e)}", LogLevel.WARNING)
        try:
            from core.tonghuashun_source import TongHuaShunDataSource
            ths = TongHuaShunDataSource()
            df = ths.get_north_fund_flow()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            self.log_manager.log(f"同花顺北向资金获取失败: {str(e)}", LogLevel.WARNING)
        return None

    def get_industry_fund_flow(self, industry_name):
        key = f"industry_fund_flow_{industry_name}"
        return self.get_fund_flow_with_cache(key, self.fetch_industry_fund_flow, industry_name)

    def get_concept_fund_flow(self, concept_name):
        key = f"concept_fund_flow_{concept_name}"
        return self.get_fund_flow_with_cache(key, self.fetch_concept_fund_flow, concept_name)

    def get_north_fund_flow(self):
        key = "north_fund_flow"
        return self.get_fund_flow_with_cache(key, self.fetch_north_fund_flow)

    def create_sentiment_report_tab(self) -> QWidget:
        """创建舆情报告Tab，采集微博、雪球、财联社、炒股吧热度，支持多线程和采集周期设置，股票代码名称真实，分平台分列，趋势和热词着色"""
        import akshare as ak
        try:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            # 采集周期设置
            period_layout = QHBoxLayout()
            period_layout.addWidget(QLabel("采集周期(分钟):"))
            self.sentiment_period_spin = QSpinBox()
            self.sentiment_period_spin.setRange(1, 60)
            self.sentiment_period_spin.setValue(2)
            period_layout.addWidget(self.sentiment_period_spin)
            # 合并按钮
            self.sentiment_toggle_btn = QPushButton("开始采集")
            period_layout.addWidget(self.sentiment_toggle_btn)
            # 倒计时文本
            self.sentiment_countdown_label = QLabel("")
            period_layout.addWidget(self.sentiment_countdown_label)
            layout.addLayout(period_layout)
            # 获取真实A股股票代码和名称
            try:
                stock_df = ak.stock_info_a_code_name()
                stock_list = stock_df.sample(n=10).values.tolist()  # 随机取10只
            except Exception:
                stock_list = [[f"600000", "浦发银行"], [f"000001", "平安银行"], [f"300750", "宁德时代"], [f"601318", "中国平安"], [f"600519", "贵州茅台"], [
                    f"000333", "美的集团"], [f"002594", "比亚迪"], [f"000651", "格力电器"], [f"601166", "兴业银行"], [f"600036", "招商银行"]]
            platforms = ["微博", "雪球", "财联社", "炒股吧"]
            col_labels = ["股票代码", "股票名称"]
            for p in platforms:
                col_labels += [f"{p}热度值", f"{p}热度趋势", f"{p}热词/摘要"]
            col_labels += ["采集时间"]
            self.sentiment_table = QTableWidget()
            self.sentiment_table.setColumnCount(len(col_labels))
            self.sentiment_table.setHorizontalHeaderLabels(col_labels)
            self.sentiment_table.setEditTriggers(
                QAbstractItemView.NoEditTriggers)
            layout.addWidget(self.sentiment_table)
            # 采集定时器
            self.sentiment_timer = QTimer()
            self.sentiment_timer.setInterval(
                self.sentiment_period_spin.value() * 60 * 1000)
            self.sentiment_timer.timeout.connect(self._start_sentiment_collect)
            self.sentiment_period_spin.valueChanged.connect(
                self._update_sentiment_timer)
            self.sentiment_collecting = False
            self._sentiment_stock_list = stock_list
            self._sentiment_platforms = platforms
            # 倒计时定时器
            self.sentiment_countdown_timer = QTimer()
            self.sentiment_countdown_timer.setInterval(1000)
            self.sentiment_countdown_timer.timeout.connect(
                self._update_sentiment_countdown)
            self.sentiment_next_collect_ts = None
            # 按钮事件
            self.sentiment_toggle_btn.clicked.connect(
                self._toggle_sentiment_collect)
            return widget
        except Exception as e:
            self.log_manager.log(f"创建舆情报告Tab失败: {str(e)}", LogLevel.ERROR)
            raise

    def _toggle_sentiment_collect(self):
        if self.sentiment_timer.isActive():
            self._stop_sentiment_timer()
        else:
            self._start_sentiment_timer()

    def _start_sentiment_timer(self):
        self.sentiment_timer.start()
        self.sentiment_toggle_btn.setText("停止采集")
        self._start_sentiment_collect()
        # 启动倒计时
        self.sentiment_next_collect_ts = time.time(
        ) + self.sentiment_period_spin.value() * 60
        self.sentiment_countdown_timer.start()
        self._update_sentiment_countdown()

    def _stop_sentiment_timer(self):
        self.sentiment_timer.stop()
        self.sentiment_toggle_btn.setText("开始采集")
        self.sentiment_countdown_timer.stop()
        self.sentiment_countdown_label.setText("")

    def _update_sentiment_timer(self):
        self.sentiment_timer.setInterval(
            self.sentiment_period_spin.value() * 60 * 1000)
        if self.sentiment_timer.isActive():
            self.sentiment_next_collect_ts = time.time(
            ) + self.sentiment_period_spin.value() * 60

    def _update_sentiment_countdown(self):
        if not self.sentiment_timer.isActive() or not self.sentiment_next_collect_ts:
            self.sentiment_countdown_label.setText("")
            return
        remain = int(self.sentiment_next_collect_ts - time.time())
        if remain < 0:
            remain = 0
        self.sentiment_countdown_label.setText(f"距离下次采集：{remain}秒")
        if remain == 0:
            self.sentiment_next_collect_ts = time.time(
            ) + self.sentiment_period_spin.value() * 60

    def _start_sentiment_collect(self):
        if self.sentiment_collecting:
            return
        self.sentiment_collecting = True
        from datetime import datetime
        import concurrent.futures
        stock_list = getattr(self, '_sentiment_stock_list', [])
        platforms = getattr(self, '_sentiment_platforms',
                            ["微博", "雪球", "财联社", "炒股吧"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table_data = []
        # 采集函数

        def get_xueqiu_hot(code, name):
            try:
                # 雪球页面如 https://xueqiu.com/S/SH600000
                url = f"https://xueqiu.com/S/SH{code}" if code.startswith(
                    '6') else f"https://xueqiu.com/S/SZ{code}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # 雪球热度（讨论数）
                    hot = soup.find("span", class_="stockDiscuss__num")
                    if hot:
                        return int(hot.text.replace(",", "")), "→", "AI"
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_guba_hot(code, name):
            try:
                # 炒股吧页面 https://guba.eastmoney.com/list,600000.html
                url = f"https://guba.eastmoney.com/list,{code}.html"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # 热度：帖子数
                    hot = soup.find("span", class_="total-posts")
                    if hot:
                        return int(hot.text.replace(",", "")), "→", "利好"
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_cls_hot(code, name):
            try:
                # 财联社新闻热度（模拟，实际可用akshare或爬虫）
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'

        def get_weibo_hot(code, name):
            try:
                # 微博热搜榜（模拟，实际可用weibo-search或爬虫）
                return '-', '→', '-'
            except Exception:
                return '-', '→', '-'
        # 多线程采集
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for code, name in stock_list:
                row = [code, name]
                futures = []
                futures.append(executor.submit(get_weibo_hot, code, name))
                futures.append(executor.submit(get_xueqiu_hot, code, name))
                futures.append(executor.submit(get_cls_hot, code, name))
                futures.append(executor.submit(get_guba_hot, code, name))
                for f in futures:
                    hot, trend, keywords = f.result()
                    row += [hot, trend, keywords]
                row += [now]
                table_data.append(row)
        self.sentiment_table.setRowCount(len(table_data))
        # 着色规则
        trend_color = {"↑": QColor("red"), "↓": QColor(
            "green"), "→": QColor("black")}
        keyword_color = {"利好": QColor("red"), "利空": QColor("green"), "涨停": QColor("orange"), "AI": QColor(
            "blue"), "新能源": QColor("blue"), "大盘": QColor("black"), "新高": QColor("purple")}
        for i, row in enumerate(table_data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                # 热度趋势着色
                if j >= 4 and (j-2) % 3 == 0:
                    item.setForeground(trend_color.get(val, QColor("black")))
                # 热词着色
                if j >= 5 and (j-1) % 3 == 0:
                    item.setForeground(keyword_color.get(val, QColor("black")))
                self.sentiment_table.setItem(i, j, item)
        self.sentiment_collecting = False

    def _connect_rotation_worker_signals(self):
        """
        连接rotation_worker的信号到对应的槽函数，确保热点轮动分析进度和结果能正确显示。
        """
        if hasattr(self, 'rotation_worker') and self.rotation_worker:
            try:
                self.rotation_worker.update_progress.connect(
                    self._on_rotation_progress)
                self.rotation_worker.update_table.connect(
                    self._on_rotation_table)
            except Exception as e:
                if hasattr(self, 'log_manager'):
                    self.log_manager.error(f"连接rotation_worker信号失败: {str(e)}")

    def set_kdata(self, kdata):
        """
        设置当前K线数据，供所有分析和形态识别使用。
        Args:
            kdata: K线数据对象（如hikyuu.KData或pandas.DataFrame）
        """
        import pandas as pd
        from core.data_manager import data_manager as global_data_manager
        try:
            if kdata is not None and (not isinstance(kdata, pd.DataFrame) or not kdata.empty):
                if isinstance(kdata, pd.DataFrame):
                    if 'datetime' not in kdata.columns and isinstance(kdata.index, pd.DatetimeIndex):
                        kdata = kdata.copy()
                        kdata['datetime'] = kdata.index
                        kdata = kdata.reset_index(drop=True)
                    # 自动补全 code 字段
                    if 'code' not in kdata.columns:
                        code = None
                        if hasattr(self, 'current_stock') and self.current_stock:
                            code = getattr(self.current_stock, 'code', None)
                        if not code and hasattr(self, 'selected_code'):
                            code = getattr(self, 'selected_code', None)
                        if not code and hasattr(self, 'code'):
                            code = getattr(self, 'code', None)
                        if code:
                            kdata = kdata.copy()
                            kdata['code'] = code
                            self.log_manager.info(
                                f"set_kdata自动补全DataFrame code字段: {code}")
                        else:
                            self.log_manager.error(
                                "set_kdata无法自动补全DataFrame code字段，请确保DataFrame包含股票代码")
                    try:
                        result = global_data_manager.df_to_kdata(kdata)
                        self.log_manager.info(
                            f"df_to_kdata转换后KData长度: {len(result)}")
                        self.current_kdata = result
                        self.kdata = result  # 保证self.kdata同步
                        if len(result) == 0:
                            self.log_manager.warning(
                                "set_kdata: KData长度为0，可能所有数据被过滤，建议检查DataFrame的datetime字段、数据完整性和格式！")
                            self.log_manager.warning(
                                f"DataFrame字段: {list(kdata.columns)}，前5行: {kdata.head()}")
                    except Exception as e:
                        self.log_manager.error(f"K线数据转换KData失败: {str(e)}")
                        self.current_kdata = None
                        self.kdata = None
                else:
                    self.current_kdata = kdata
                    self.kdata = kdata  # 保证self.kdata同步
                    self.log_manager.info(
                        f"set_kdata直接赋值KData长度: {len(kdata) if hasattr(kdata, '__len__') else '未知'}")
                    if hasattr(self.current_kdata, '__len__') and len(self.current_kdata) == 0:
                        self.log_manager.warning(
                            "set_kdata: 直接赋值KData长度为0，数据源可能为空！")
            else:
                self.current_kdata = None
                self.kdata = None
        except Exception as e:
            self.log_manager.error(f"set_kdata异常: {str(e)}")
            self.current_kdata = None
            self.kdata = None

    def refresh(self) -> None:
        """
        刷新分析控件内容，自动刷新所有Tab（如重新计算分析、刷新表格等）。
        """
        try:
            # 依次刷新各Tab内容（如有刷新方法）
            # 技术分析Tab
            if hasattr(self, 'calculate_indicators'):
                self.calculate_indicators()
            # 形态识别Tab
            if hasattr(self, 'do_analyze'):
                self.do_analyze()
            # 趋势分析Tab
            if hasattr(self, 'analyze_trend'):
                self.analyze_trend()
            # 波浪分析Tab
            if hasattr(self, 'analyze_wave'):
                self.analyze_wave()
            # 市场情绪Tab
            if hasattr(self, 'analyze_sentiment'):
                self.analyze_sentiment()
            # 板块资金流向Tab
            if hasattr(self, 'analyze_industry_flow'):
                self.analyze_industry_flow()
            # 热点分析Tab
            if hasattr(self, 'analyze_hotspot'):
                self.analyze_hotspot()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"刷新分析控件失败: {str(e)}")

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()


def get_indicator_categories():
    """获取所有指标分类及其指标列表，确保与ta-lib分类一致"""
    from indicators_algo import get_all_indicators_by_category
    return get_all_indicators_by_category()

# --- 新增：轮动分析后台线程类 ---


class RotationWorker(QThread):

    finished = pyqtSignal()
    error = pyqtSignal(str)
    update_progress = pyqtSignal(int, str)
    update_table = pyqtSignal(list)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self._rotation_interrupted = False

    def run(self):
        try:
            self.widget.log_manager.log("开始热点轮动分析", LogLevel.INFO)
            if hasattr(self.widget, 'interrupt_button'):
                self.widget.interrupt_button.setEnabled(True)
            # 获取主窗口status_bar
            main_window = self.widget.parentWidget()
            while main_window and not hasattr(main_window, 'status_bar'):
                main_window = main_window.parentWidget()
            status_bar = getattr(main_window, 'status_bar', None)
            if status_bar:
                status_bar.set_progress(0)
                status_bar.set_status("热点轮动分析中...")
                status_bar.show_progress(True)
            import concurrent.futures
            import time
            start_time = time.time()
            self.widget.rotation_table.setRowCount(0)
            block_list = sm.get_block_list()
            total_blocks = len(block_list)
            max_workers = min(os.cpu_count() or 4, 8)
            rotations = []
            futures = []
            t_thread = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as block_executor:
                for block in block_list:
                    if self._rotation_interrupted or getattr(self.widget, '_rotation_interrupted', False):
                        self.widget.log_manager.info("热点轮动分析被用户中断，提前结束任务提交")
                        break
                    stocks = block.get_stock_list()
                    stock_codes = []
                    kdata_part = {}
                    for stock in stocks:
                        code = getattr(stock, 'code', None) or getattr(
                            stock, 'name', None)
                        if code:
                            stock_codes.append(code)
                            klist = stock.get_kdata(Query(-11))
                            kdata_arr = {
                                'close': [float(k.close) for k in klist],
                                'volume': [float(k.volume) for k in klist],
                                'amount': [float(k.amount) for k in klist],
                                'open': [float(k.open) for k in klist]
                            }
                            kdata_part[code] = kdata_arr
                    block_data = {
                        'block_name': block.name,
                        'stock_codes': stock_codes,
                        'kdata_part': kdata_part
                    }
                    futures.append(block_executor.submit(
                        self._process_block_safe, block_data))
                # 统一收集结果
                finished = 0
                for i, future in enumerate(concurrent.futures.as_completed(futures, timeout=300)):
                    if self._rotation_interrupted or getattr(self.widget, '_rotation_interrupted', False):
                        self.widget.log_manager.info("热点轮动分析被用户中断，提前结束结果收集")
                        break
                    try:
                        res = future.result(timeout=60)
                        if res:
                            rotations.append(res)
                        finished += 1
                        percent = int(finished / max(1, total_blocks) * 100)
                        self.update_progress.emit(
                            percent, f"热点轮动分析进度: {finished}/{total_blocks}")
                        self.widget.log_manager.info(
                            f"热点轮动进度: {finished}/{total_blocks}")
                    except concurrent.futures.TimeoutError:
                        self.widget.log_manager.error(
                            f"热点轮动子线程超时 {i+1}/{len(futures)}")
                    except Exception as e:
                        self.widget.log_manager.error(
                            f"热点轮动子线程异常: {str(e)}\n{traceback.format_exc()}")
            t_thread_end = time.time()
            self.widget.log_manager.info(
                f"全部板块分析完成，耗时：{t_thread_end-t_thread:.2f}秒")
            rotations.sort(key=lambda x: x['score'], reverse=True)
            self.update_table.emit(rotations)
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"热点轮动分析失败: {str(e)}\n{traceback.format_exc()}")

    def _process_block_safe(self, block_data):
        import numpy as np
        import time
        block_name = block_data['block_name']
        stock_codes = block_data['stock_codes']
        kdata_part = block_data['kdata_part']
        t0 = time.time()
        valid_changes = []
        valid_flows = []
        for code in stock_codes:
            k = kdata_part.get(code)
            if not k or len(k['close']) < 11:
                continue
            try:
                close = np.array(k['close'], dtype=np.float64)
                volume = np.array(k['volume'], dtype=np.float64)
                amount = np.array(k['amount'], dtype=np.float64)
                open_arr = np.array(k['open'], dtype=np.float64)
                change_arr, flow_arr = fast_process_stock(
                    close, volume, amount, open_arr)
                if len(change_arr) == 10 and len(flow_arr) == 10:
                    valid_changes.append(change_arr)
                    valid_flows.append(flow_arr)
            except Exception as e:
                if hasattr(self.widget, 'log_manager'):
                    self.widget.log_manager.error(
                        f"[{block_name}] 股票{code}分析异常: {str(e)}")
        if not valid_changes:
            if hasattr(self.widget, 'log_manager'):
                self.widget.log_manager.warning(f"[{block_name}] 无有效股票结果")
            return None
        change_mat = np.stack(valid_changes)
        flow_mat = np.stack(valid_flows)
        avg_change = np.mean(change_mat, axis=0)
        avg_flow = np.mean(flow_mat, axis=0)
        daily_stats = [
            {'change': avg_change[i], 'flow': avg_flow[i]}
            for i in range(10)
        ]
        trend = sum(1 for i in range(1, len(daily_stats))
                    if daily_stats[i]['change'] > daily_stats[i-1]['change'])
        flow_trend = sum(1 for stat in daily_stats if stat['flow'] > 0)
        duration = 0
        for stat in daily_stats:
            if stat['change'] > 0 and stat['flow'] > 0:
                duration += 1
            else:
                break
        t1 = time.time()
        momentum = np.sum(avg_change)
        flow = np.sum(avg_flow)
        up_days = np.sum(np.array(avg_change) > 0)
        momentum_score = min(max((momentum + 20) / 40, 0), 1)
        flow_score = min(max((flow + 5) / 10, 0), 1)
        active_score = up_days / 10
        score = round(0.5 * momentum_score + 0.3 *
                      flow_score + 0.2 * active_score, 2)
        if hasattr(self.widget, 'log_manager'):
            self.widget.log_manager.info(
                f"[{block_name}] 板块分析完成，股票数：{len(stock_codes)}，耗时：{t1 - t0:.2f}秒")
        return {
            'name': block_name,
            'trend': trend / 9 * 100,
            'trend_raw': trend,
            'flow_trend': flow_trend,
            'duration': duration,
            'flow': float(np.sum(avg_flow)),
            'score': score,
            'momentum': momentum,
            'flow': flow,
            'up_days': up_days
        }

    def _on_rotation_progress(self, percent, msg):
        """
        热点轮动分析进度更新槽函数，负责更新主窗口状态栏进度和状态。
        """
        main_window = self.parentWidget()
        while main_window and not hasattr(main_window, 'status_bar'):
            main_window = main_window.parentWidget()
        status_bar = getattr(main_window, 'status_bar', None)
        if status_bar:
            status_bar.set_progress(percent)
            status_bar.set_status(msg)

    def _on_rotation_table(self, rotations):
        """
        热点轮动分析结果表格更新槽函数，负责将分析结果填充到rotation_table。
        """
        if hasattr(self, 'rotation_table'):
            self.rotation_table.setRowCount(len(rotations))
            for i, rotation in enumerate(rotations):
                self.rotation_table.setItem(
                    i, 0, QTableWidgetItem(rotation['name']))
                trend_item = QTableWidgetItem(f"{rotation['trend']:.1f}%")
                trend_item.setForeground(QColor("red") if rotation['trend'] >= 60 else QColor(
                    "orange") if rotation['trend'] >= 40 else QColor("green"))
                self.rotation_table.setItem(i, 1, trend_item)
                flow_item = QTableWidgetItem(f"{rotation['flow']:+.2f}")
                flow_item.setForeground(
                    QColor("red" if rotation['flow'] > 0 else "green"))
                self.rotation_table.setItem(i, 2, flow_item)
                self.rotation_table.setItem(
                    i, 3, QTableWidgetItem(str(rotation['duration'])))
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
                self.rotation_table.setItem(
                    i, 5, QTableWidgetItem(f"{rotation['score']}"))
            self.rotation_table.resizeColumnsToContents()


# 板块级多进程+股票级多线程+Numba加速


@numba.njit
def fast_process_stock(close, volume, amount, open_arr):
    pre_close = np.roll(close, 1)
    pre_close[0] = close[0]
    change_arr = (close[1:] - pre_close[1:]) / pre_close[1:] * 100
    change_arr = change_arr[-10:]
    flow_arr = np.zeros(10)
    for idx in range(1, 11):
        v = volume[-idx]
        a = amount[-idx]
        o = open_arr[-idx]
        if v > 0:
            avg_p = a / v
            flow_arr[-idx] = a if avg_p > o else -a
        else:
            flow_arr[-idx] = 0
    flow_arr = flow_arr / 1e8
    return change_arr, flow_arr


def process_block_threaded(block_data, log_manager=None):
    import numpy as np
    import time
    from concurrent.futures import ThreadPoolExecutor

    block_name = block_data['block_name']
    stock_codes = block_data['stock_codes']
    kdata_part = block_data['kdata_part']

    t0 = time.time()

    def process_stock(code):
        k = kdata_part.get(code)
        if not k or len(k['close']) < 11:
            return None
        try:
            close = np.array(k['close'], dtype=np.float64)
            volume = np.array(k['volume'], dtype=np.float64)
            amount = np.array(k['amount'], dtype=np.float64)
            open_arr = np.array(k['open'], dtype=np.float64)
            return fast_process_stock(close, volume, amount, open_arr)
        except Exception as e:
            if log_manager:
                log_manager.error(f"[{block_name}] 股票{code}分析异常: {str(e)}")
            return None

    # 股票级多线程
    with ThreadPoolExecutor(max_workers=min(8, len(stock_codes))) as stock_executor:
        stock_results = list(stock_executor.map(process_stock, stock_codes))

    valid_changes = []
    valid_flows = []
    for res in stock_results:
        if res and len(res) == 2:
            change_arr, flow_arr = res
            if len(change_arr) == 10 and len(flow_arr) == 10:
                valid_changes.append(change_arr)
                valid_flows.append(flow_arr)
    if not valid_changes:
        if log_manager:
            log_manager.warning(f"[{block_name}] 无有效股票结果")
        return None
    change_mat = np.stack(valid_changes)
    flow_mat = np.stack(valid_flows)
    avg_change = np.mean(change_mat, axis=0)
    avg_flow = np.mean(flow_mat, axis=0)
    daily_stats = [
        {'change': avg_change[i], 'flow': avg_flow[i]}
        for i in range(10)
    ]
    trend = sum(1 for i in range(1, len(daily_stats))
                if daily_stats[i]['change'] > daily_stats[i-1]['change'])
    flow_trend = sum(1 for stat in daily_stats if stat['flow'] > 0)
    duration = 0
    for stat in daily_stats:
        if stat['change'] > 0 and stat['flow'] > 0:
            duration += 1
        else:
            break
    t1 = time.time()
    # 1. 近10日累计涨幅
    momentum = np.sum(avg_change)  # 或 np.mean(avg_change)
    # 2. 近10日累计资金流入
    flow = np.sum(avg_flow)
    # 3. 近10日上涨天数
    up_days = np.sum(np.array(avg_change) > 0)

    # 归一化（可用全市场最大/最小值，或用经验值如20%涨幅、10亿资金流等）
    momentum_score = min(max((momentum + 20) / 40, 0), 1)  # -20%~+20%归一化到0~1
    flow_score = min(max((flow + 5) / 10, 0), 1)           # -5亿~+5亿归一化到0~1
    active_score = up_days / 10

    score = round(0.5 * momentum_score + 0.3 *
                  flow_score + 0.2 * active_score, 2)
    log_manager.info(
        f"[{block_name}] 板块分析完成，股票数：{len(stock_codes)}，耗时：{t1 - t0:.2f}秒")
    return {
        'name': block_name,
        'trend': trend / 9 * 100,
        'trend_raw': trend,
        'flow_trend': flow_trend,
        'duration': duration,
        'flow': float(np.sum(avg_flow)),
        'score': score,
        'momentum': momentum,
        'flow': flow,
        'up_days': up_days
    }


class PatternRecognitionWorker(QThread):
    result_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, kdata, pattern_types):
        super().__init__()
        self.kdata = kdata
        self.pattern_types = pattern_types

    def run(self):
        try:
            # 只做数据处理，不做任何UI操作
            kdata = create_pattern_recognition_features(self.kdata)
            from analysis.pattern_recognition import PatternRecognizer
            recognizer = PatternRecognizer()
            results = recognizer.get_pattern_signals(
                kdata, pattern_types=self.pattern_types)
            self.result_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))
