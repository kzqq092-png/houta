"""
右侧面板

负责显示技术分析结果、买卖信号、风险评估等功能。
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta
import json
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QMessageBox, QFrame, QScrollArea, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QCheckBox, QSlider, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

from .base_panel import BasePanel
from core.events import StockSelectedEvent, AnalysisCompleteEvent, ChartUpdateEvent, UIDataReadyEvent

# 导入完整的技术分析标签页
try:
    from gui.widgets.analysis_tabs.technical_tab import TechnicalAnalysisTab
    TECHNICAL_TAB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"无法导入TechnicalAnalysisTab: {e}")
    TECHNICAL_TAB_AVAILABLE = False

if TYPE_CHECKING:
    from core.services import AnalysisService

logger = logging.getLogger(__name__)


class RightPanel(BasePanel):
    """
    右侧面板

    功能：
    1. 技术指标分析
    2. 买卖信号分析
    3. 风险评估
    4. 历史回测结果
    5. 市场情绪分析
    """

    # 定义信号
    analysis_completed = pyqtSignal(str, dict)  # 股票代码, 分析结果

    def __init__(self,
                 parent: QWidget,
                 coordinator,
                 width: int = 350,
                 **kwargs):
        """
        初始化右侧面板

        Args:
            parent: 父窗口组件
            coordinator: 主窗口协调器
            width: 面板宽度
            **kwargs: 其他参数
        """
        # 通过服务容器获取分析服务
        self.analysis_service = None
        if coordinator and hasattr(coordinator, 'service_container'):
            from core.services import AnalysisService
            self.analysis_service = coordinator.service_container.get_service(
                AnalysisService)
        self.width = width

        # 当前状态
        self._current_stock_code = ''
        self._current_stock_name = ''
        self._analysis_type = 'comprehensive'  # 默认使用综合分析

        # 数据加载线程 (将被移除)
        # self._loader_thread = None

        # 分析数据
        self._analysis_data = None

        super().__init__(parent, coordinator, **kwargs)

    def _create_widgets(self) -> None:
        """创建UI组件"""
        # 设置面板样式
        self._root_frame.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                border: 1px solid #dee2e6;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: #007bff;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
            }
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                padding: 5px;
            }
        """)

        # 创建主布局
        main_layout = QVBoxLayout(self._root_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # 创建标题
        title_label = QLabel("技术分析")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            "color: #495057; font-size: 14px; font-weight: bold;")
        main_layout.addWidget(title_label)
        self.add_widget('title', title_label)

        # 股票信息框
        stock_info_frame = QFrame()
        stock_info_frame.setFrameStyle(QFrame.StyledPanel)
        stock_info_frame.setStyleSheet(
            "background-color: white; border: 1px solid #dee2e6; border-radius: 4px;")
        main_layout.addWidget(stock_info_frame)
        self.add_widget('stock_info_frame', stock_info_frame)

        stock_info_layout = QHBoxLayout(stock_info_frame)
        stock_info_layout.setContentsMargins(10, 10, 10, 10)
        stock_info_layout.setSpacing(8)

        # 股票代码和名称
        stock_label = QLabel("请选择股票")
        stock_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #495057;")
        stock_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        stock_info_layout.addWidget(stock_label)
        self.add_widget('stock_label', stock_label)

        # 分隔符
        separator = QLabel("当前|股票")
        separator.setStyleSheet(
            "font-size: 14px; color: #2ee2e6; margin: 0 5px;")
        separator.setAlignment(Qt.AlignCenter)
        stock_info_layout.addWidget(separator)

        # 分析时间
        analysis_time_label = QLabel("")
        analysis_time_label.setStyleSheet("font-size: 12px; color: #6c757d;")
        analysis_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        stock_info_layout.addWidget(analysis_time_label)
        self.add_widget('analysis_time_label', analysis_time_label)

        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        progress_bar.setMaximumHeight(3)
        main_layout.addWidget(progress_bar)
        self.add_widget('progress_bar', progress_bar)

        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        self.add_widget('tab_widget', tab_widget)

        # 技术指标标签页
        if TECHNICAL_TAB_AVAILABLE:
            self._technical_tab = TechnicalAnalysisTab(self._root_frame)
            tab_widget.addTab(self._technical_tab, "技术指标")
            self.add_widget('technical_tab', self._technical_tab)
        else:
            self._create_technical_tab(tab_widget)

        # 买卖信号标签页
        self._create_signal_tab(tab_widget)

        # 风险评估标签页
        self._create_risk_tab(tab_widget)

        # 回测结果标签页
        self._create_backtest_tab(tab_widget)

        # AI选股标签页
        self._create_ai_stock_tab(tab_widget)

        # 行业分析标签页
        self._create_industry_tab(tab_widget)

        # 控制按钮框架
        button_frame = QFrame()
        main_layout.addWidget(button_frame)
        self.add_widget('button_frame', button_frame)

        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 5, 0, 0)
        button_layout.setSpacing(5)

        # 刷新分析按钮
        refresh_btn = QPushButton("刷新分析")
        button_layout.addWidget(refresh_btn)
        self.add_widget('refresh_btn', refresh_btn)

        # 导出报告按钮
        export_btn = QPushButton("导出报告")
        button_layout.addWidget(export_btn)
        self.add_widget('export_btn', export_btn)

        # 状态标签
        status_label = QLabel("就绪")
        status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        main_layout.addWidget(status_label)
        self.add_widget('status_label', status_label)

    def _create_technical_tab(self, parent: QTabWidget) -> None:
        """创建技术指标标签页"""
        technical_widget = QWidget()
        parent.addTab(technical_widget, "技术指标")
        self.add_widget('technical_widget', technical_widget)

        layout = QVBoxLayout(technical_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 趋势分析组
        trend_group = QGroupBox("趋势分析")
        layout.addWidget(trend_group)
        self.add_widget('trend_group', trend_group)

        trend_layout = QVBoxLayout(trend_group)

        # 趋势表格
        trend_table = QTableWidget(0, 3)
        trend_table.setHorizontalHeaderLabels(['指标', '数值', '信号'])
        trend_table.horizontalHeader().setStretchLastSection(True)
        trend_table.setAlternatingRowColors(True)
        trend_table.setMaximumHeight(150)
        trend_layout.addWidget(trend_table)
        self.add_widget('trend_table', trend_table)

        # 动量分析组
        momentum_group = QGroupBox("动量分析")
        layout.addWidget(momentum_group)
        self.add_widget('momentum_group', momentum_group)

        momentum_layout = QVBoxLayout(momentum_group)

        # 动量表格
        momentum_table = QTableWidget(0, 3)
        momentum_table.setHorizontalHeaderLabels(['指标', '数值', '信号'])
        momentum_table.horizontalHeader().setStretchLastSection(True)
        momentum_table.setAlternatingRowColors(True)
        momentum_table.setMaximumHeight(150)
        momentum_layout.addWidget(momentum_table)
        self.add_widget('momentum_table', momentum_table)

        # 成交量分析组
        volume_group = QGroupBox("成交量分析")
        layout.addWidget(volume_group)
        self.add_widget('volume_group', volume_group)

        volume_layout = QVBoxLayout(volume_group)

        # 成交量分析文本
        volume_text = QTextEdit()
        volume_text.setMaximumHeight(100)
        volume_text.setReadOnly(True)
        volume_layout.addWidget(volume_text)
        self.add_widget('volume_text', volume_text)

        layout.addStretch()

    def _create_signal_tab(self, parent: QTabWidget) -> None:
        """创建买卖信号标签页"""
        signal_widget = QWidget()
        parent.addTab(signal_widget, "买卖信号")
        self.add_widget('signal_widget', signal_widget)

        layout = QVBoxLayout(signal_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 当前信号组
        current_signal_group = QGroupBox("当前信号")
        layout.addWidget(current_signal_group)
        self.add_widget('current_signal_group', current_signal_group)

        current_signal_layout = QVBoxLayout(current_signal_group)

        # 主要信号显示
        main_signal_label = QLabel("暂无信号")
        main_signal_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #495057; padding: 10px;")
        main_signal_label.setAlignment(Qt.AlignCenter)
        current_signal_layout.addWidget(main_signal_label)
        self.add_widget('main_signal_label', main_signal_label)

        # 信号强度
        signal_strength_label = QLabel("信号强度:")
        current_signal_layout.addWidget(signal_strength_label)
        self.add_widget('signal_strength_label', signal_strength_label)

        signal_strength_bar = QProgressBar()
        signal_strength_bar.setRange(0, 100)
        signal_strength_bar.setValue(0)
        current_signal_layout.addWidget(signal_strength_bar)
        self.add_widget('signal_strength_bar', signal_strength_bar)

        # 历史信号组
        history_signal_group = QGroupBox("历史信号")
        layout.addWidget(history_signal_group)
        self.add_widget('history_signal_group', history_signal_group)

        history_signal_layout = QVBoxLayout(history_signal_group)

        # 历史信号表格
        signal_table = QTableWidget(0, 4)
        signal_table.setHorizontalHeaderLabels(['日期', '信号', '价格', '收益率'])
        signal_table.horizontalHeader().setStretchLastSection(True)
        signal_table.setAlternatingRowColors(True)
        history_signal_layout.addWidget(signal_table)
        self.add_widget('signal_table', signal_table)

        # 信号统计组
        signal_stats_group = QGroupBox("信号统计")
        layout.addWidget(signal_stats_group)
        self.add_widget('signal_stats_group', signal_stats_group)

        signal_stats_layout = QVBoxLayout(signal_stats_group)

        # 统计文本
        signal_stats_text = QTextEdit()
        signal_stats_text.setMaximumHeight(80)
        signal_stats_text.setReadOnly(True)
        signal_stats_layout.addWidget(signal_stats_text)
        self.add_widget('signal_stats_text', signal_stats_text)

    def _create_risk_tab(self, parent: QTabWidget) -> None:
        """创建风险评估标签页"""
        risk_widget = QWidget()
        parent.addTab(risk_widget, "风险评估")
        self.add_widget('risk_widget', risk_widget)

        layout = QVBoxLayout(risk_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 风险等级组
        risk_level_group = QGroupBox("风险等级")
        layout.addWidget(risk_level_group)
        self.add_widget('risk_level_group', risk_level_group)

        risk_level_layout = QVBoxLayout(risk_level_group)

        # 风险等级显示
        risk_level_label = QLabel("未评估")
        risk_level_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #495057; padding: 15px;")
        risk_level_label.setAlignment(Qt.AlignCenter)
        risk_level_layout.addWidget(risk_level_label)
        self.add_widget('risk_level_label', risk_level_label)

        # 风险指标组
        risk_metrics_group = QGroupBox("风险指标")
        layout.addWidget(risk_metrics_group)
        self.add_widget('risk_metrics_group', risk_metrics_group)

        risk_metrics_layout = QVBoxLayout(risk_metrics_group)

        # 风险指标表格
        risk_table = QTableWidget(0, 2)
        risk_table.setHorizontalHeaderLabels(['指标', '数值'])
        risk_table.horizontalHeader().setStretchLastSection(True)
        risk_table.setAlternatingRowColors(True)
        risk_table.setMaximumHeight(200)
        risk_metrics_layout.addWidget(risk_table)
        self.add_widget('risk_table', risk_table)

        # 风险建议组
        risk_advice_group = QGroupBox("风险建议")
        layout.addWidget(risk_advice_group)
        self.add_widget('risk_advice_group', risk_advice_group)

        risk_advice_layout = QVBoxLayout(risk_advice_group)

        # 建议文本
        risk_advice_text = QTextEdit()
        risk_advice_text.setReadOnly(True)
        risk_advice_layout.addWidget(risk_advice_text)
        self.add_widget('risk_advice_text', risk_advice_text)

    def _create_backtest_tab(self, parent: QTabWidget) -> None:
        """创建回测结果标签页"""
        backtest_widget = QWidget()
        parent.addTab(backtest_widget, "回测结果")
        self.add_widget('backtest_widget', backtest_widget)

        layout = QVBoxLayout(backtest_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 回测参数组
        backtest_params_group = QGroupBox("回测参数")
        layout.addWidget(backtest_params_group)
        self.add_widget('backtest_params_group', backtest_params_group)

        params_layout = QHBoxLayout(backtest_params_group)

        # 回测天数
        params_layout.addWidget(QLabel("回测天数:"))
        backtest_days_spin = QSpinBox()
        backtest_days_spin.setRange(30, 365)
        backtest_days_spin.setValue(60)
        params_layout.addWidget(backtest_days_spin)
        self.add_widget('backtest_days_spin', backtest_days_spin)

        # 运行回测按钮
        run_backtest_btn = QPushButton("运行回测")
        params_layout.addWidget(run_backtest_btn)
        self.add_widget('run_backtest_btn', run_backtest_btn)

        # 回测结果组
        backtest_results_group = QGroupBox("回测结果")
        layout.addWidget(backtest_results_group)
        self.add_widget('backtest_results_group', backtest_results_group)

        results_layout = QVBoxLayout(backtest_results_group)

        # 关键指标表格
        backtest_table = QTableWidget(0, 2)
        backtest_table.setHorizontalHeaderLabels(['指标', '数值'])
        backtest_table.horizontalHeader().setStretchLastSection(True)
        backtest_table.setAlternatingRowColors(True)
        backtest_table.setMaximumHeight(200)
        results_layout.addWidget(backtest_table)
        self.add_widget('backtest_table', backtest_table)

        # 交易记录组
        trade_records_group = QGroupBox("交易记录")
        layout.addWidget(trade_records_group)
        self.add_widget('trade_records_group', trade_records_group)

        trade_records_layout = QVBoxLayout(trade_records_group)

        # 交易记录表格
        trade_table = QTableWidget(0, 5)
        trade_table.setHorizontalHeaderLabels(['日期', '操作', '价格', '数量', '收益'])
        trade_table.horizontalHeader().setStretchLastSection(True)
        trade_table.setAlternatingRowColors(True)
        trade_records_layout.addWidget(trade_table)
        self.add_widget('trade_table', trade_table)

    def _create_ai_stock_tab(self, parent: QTabWidget) -> None:
        """创建AI选股标签页"""
        ai_stock_widget = QWidget()
        parent.addTab(ai_stock_widget, "AI选股")
        self.add_widget('ai_stock_widget', ai_stock_widget)

        layout = QVBoxLayout(ai_stock_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 选股条件组
        condition_group = QGroupBox("选股条件")
        layout.addWidget(condition_group)
        self.add_widget('ai_condition_group', condition_group)

        condition_layout = QVBoxLayout(condition_group)

        # 自然语言输入
        condition_text = QTextEdit()
        condition_text.setPlaceholderText("请输入选股需求（如：高ROE、低估值、强势资金流等）")
        condition_text.setMaximumHeight(80)
        condition_layout.addWidget(condition_text)
        self.add_widget('ai_condition_text', condition_text)

        # 选股类型选择
        type_layout = QHBoxLayout()
        condition_layout.addLayout(type_layout)

        type_layout.addWidget(QLabel("选股类型:"))
        type_combo = QComboBox()
        type_combo.addItems([
            "价值投资", "成长投资", "趋势跟踪", "均值回归",
            "动量策略", "技术分析", "基本面分析", "量化选股"
        ])
        type_layout.addWidget(type_combo)
        self.add_widget('ai_type_combo', type_combo)

        # 风险偏好
        risk_layout = QHBoxLayout()
        condition_layout.addLayout(risk_layout)

        risk_layout.addWidget(QLabel("风险偏好:"))
        risk_combo = QComboBox()
        risk_combo.addItems(["保守", "稳健", "积极", "激进"])
        risk_layout.addWidget(risk_combo)
        self.add_widget('ai_risk_combo', risk_combo)

        # 执行按钮
        ai_run_btn = QPushButton("一键AI选股")
        ai_run_btn.setStyleSheet(
            "background-color: #28a745; font-size: 14px; padding: 8px;")
        condition_layout.addWidget(ai_run_btn)
        self.add_widget('ai_run_btn', ai_run_btn)

        # 选股结果组
        result_group = QGroupBox("选股结果")
        layout.addWidget(result_group)
        self.add_widget('ai_result_group', result_group)

        result_layout = QVBoxLayout(result_group)

        # 结果表格
        result_table = QTableWidget(0, 6)
        result_table.setHorizontalHeaderLabels(
            ['股票代码', '股票名称', '推荐理由', '评分', '风险等级', '建议仓位'])
        result_table.horizontalHeader().setStretchLastSection(True)
        result_table.setAlternatingRowColors(True)
        result_layout.addWidget(result_table)
        self.add_widget('ai_result_table', result_table)

        # 导出按钮
        export_ai_btn = QPushButton("导出选股结果")
        result_layout.addWidget(export_ai_btn)
        self.add_widget('export_ai_btn', export_ai_btn)

    def _create_industry_tab(self, parent: QTabWidget) -> None:
        """创建行业分析标签页"""
        industry_widget = QWidget()
        parent.addTab(industry_widget, "行业分析")
        self.add_widget('industry_widget', industry_widget)

        layout = QVBoxLayout(industry_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 行业概况组
        overview_group = QGroupBox("行业概况")
        layout.addWidget(overview_group)
        self.add_widget('industry_overview_group', overview_group)

        overview_layout = QVBoxLayout(overview_group)

        # 行业信息表格
        overview_table = QTableWidget(0, 2)
        overview_table.setHorizontalHeaderLabels(['指标', '数值'])
        overview_table.horizontalHeader().setStretchLastSection(True)
        overview_table.setAlternatingRowColors(True)
        overview_table.setMaximumHeight(120)
        overview_layout.addWidget(overview_table)
        self.add_widget('industry_overview_table', overview_table)

        # 板块表现组
        performance_group = QGroupBox("板块表现")
        layout.addWidget(performance_group)
        self.add_widget('industry_performance_group', performance_group)

        performance_layout = QVBoxLayout(performance_group)

        # 表现表格
        performance_table = QTableWidget(0, 4)
        performance_table.setHorizontalHeaderLabels(
            ['板块', '涨跌幅', '成交额', '领涨股'])
        performance_table.horizontalHeader().setStretchLastSection(True)
        performance_table.setAlternatingRowColors(True)
        performance_layout.addWidget(performance_table)
        self.add_widget('industry_performance_table', performance_table)

        # 热点分析组
        hotspot_group = QGroupBox("热点分析")
        layout.addWidget(hotspot_group)
        self.add_widget('industry_hotspot_group', hotspot_group)

        hotspot_layout = QVBoxLayout(hotspot_group)

        # 热点文本
        hotspot_text = QTextEdit()
        hotspot_text.setReadOnly(True)
        hotspot_text.setMaximumHeight(100)
        hotspot_layout.addWidget(hotspot_text)
        self.add_widget('industry_hotspot_text', hotspot_text)

        # 刷新按钮
        refresh_industry_btn = QPushButton("刷新行业数据")
        layout.addWidget(refresh_industry_btn)
        self.add_widget('refresh_industry_btn', refresh_industry_btn)

        layout.addStretch()

    def _bind_events(self) -> None:
        """注册事件处理器"""
        # 注意：现在通过事件总线进行通信，不需要手动连接信号
        # self.event_bus.subscribe(StockSelectedEvent, self.on_stock_selected)
        # self.event_bus.subscribe(
        #     AnalysisCompleteEvent, self.on_analysis_complete)
        self.event_bus.subscribe(UIDataReadyEvent, self._on_ui_data_ready)
        logger.debug("RightPanel已订阅UIDataReadyEvent事件")

    def _initialize_data(self) -> None:
        """初始化数据"""
        # 初始状态下显示提示信息
        self._update_status("请在左侧选择一只股票以开始分析")

    @pyqtSlot(UIDataReadyEvent)
    def _on_ui_data_ready(self, event: UIDataReadyEvent) -> None:
        """处理UI数据就绪事件，直接使用事件中的数据更新面板"""
        try:
            logger.info(f"RightPanel收到UIDataReadyEvent，股票: {event.stock_code}")
            # 更新股票信息
            self._current_stock_code = event.stock_code
            self._current_stock_name = event.stock_name
            self.get_widget('stock_label').setText(
                f"{self._current_stock_name} ({self._current_stock_code})")

            # 从事件中直接获取分析数据和K线数据
            analysis_data = event.ui_data.get('analysis')
            kline_data = event.ui_data.get('kline_data')

            # 如果有完整的技术分析标签页，传递K线数据
            if TECHNICAL_TAB_AVAILABLE and hasattr(self, '_technical_tab'):
                try:
                    if kline_data is not None and not kline_data.empty:
                        logger.info(f"传递K线数据到技术分析标签页，数据长度: {len(kline_data)}")
                        self._technical_tab.set_kdata(kline_data)
                    else:
                        logger.warning("K线数据为空，无法传递到技术分析标签页")
                        self._technical_tab.clear_data()
                except Exception as e:
                    logger.error(f"传递K线数据到技术分析标签页失败: {e}")

            if analysis_data:
                # 直接使用分析数据更新UI
                self._on_analysis_data_loaded(analysis_data)
            else:
                # 如果没有分析数据，只传递了K线数据也是正常的
                logger.info(f"事件中未包含分析数据，但K线数据已传递到技术分析标签页")
                self._update_status("K线数据已加载，可开始技术分析")

        except Exception as e:
            logger.error(f"处理UI数据就绪事件时发生意外错误: {e}", exc_info=True)
            self._on_analysis_load_error(f"处理事件时发生意外错误: {e}")

    def _on_analysis_data_loaded(self, analysis_data: Dict[str, Any]) -> None:
        """使用分析数据更新UI组件"""
        try:
            self._analysis_data = analysis_data
            self.get_widget('progress_bar').setVisible(False)
            self.get_widget('analysis_time_label').setText(
                f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 更新各个标签页
            if TECHNICAL_TAB_AVAILABLE:
                self._technical_tab.update_analysis(analysis_data)
            else:
                self._update_technical_analysis(
                    analysis_data.get('technical_indicators', {}))
            self._update_signal_analysis(
                analysis_data.get('trading_signals', {}))
            self._update_risk_analysis(
                analysis_data.get('risk_assessment', {}))
            self._update_backtest_results(
                analysis_data.get('backtest_results', {}))

            self._update_status("分析数据已更新")
            logger.info(f"RightPanel已成功更新 {self._current_stock_code} 的分析数据")

        except Exception as e:
            logger.error(f"更新分析UI时出错: {e}", exc_info=True)
            self._on_analysis_load_error(f"更新UI失败: {e}")

    def _on_analysis_load_error(self, error_msg: str) -> None:
        """处理分析数据加载错误"""
        logger.error(f"分析数据加载错误: {error_msg}")
        self.get_widget('progress_bar').setVisible(False)
        self._update_status(f"错误: {error_msg}")
        QMessageBox.warning(self, "分析错误", f"加载分析数据时出错:\n{error_msg}")

    def _refresh_analysis(self) -> None:
        """
        刷新分析数据 - 此方法现在应通过协调器触发数据重新加载
        """
        if not self._current_stock_code:
            self._update_status("请先选择股票")
            return

        # 发布一个事件请求主协调器刷新数据
        # 注意：这里可以定义一个新的事件类型，或者重用StockSelectedEvent
        logger.info(f"请求刷新 {self._current_stock_code} 的数据...")
        self.event_bus.publish(
            StockSelectedEvent(
                stock_code=self._current_stock_code,
                stock_name=self._current_stock_name
            )
        )
        self._update_status(f"正在重新加载 {self._current_stock_name} 的数据...")

    def _update_technical_analysis(self, technical_data: Dict[str, Any]) -> None:
        """更新技术分析标签页"""
        try:
            # 更新趋势分析表格
            trend_table = self.get_widget('trend_table')
            trend_table.setRowCount(0)

            trend_indicators = technical_data.get('trend', {})
            for indicator, data in trend_indicators.items():
                row = trend_table.rowCount()
                trend_table.insertRow(row)
                trend_table.setItem(row, 0, QTableWidgetItem(indicator))
                trend_table.setItem(row, 1, QTableWidgetItem(
                    str(data.get('value', ''))))

                signal = data.get('signal', 'neutral')
                signal_item = QTableWidgetItem(signal)
                if signal == 'buy':
                    signal_item.setBackground(QColor('#d4edda'))
                elif signal == 'sell':
                    signal_item.setBackground(QColor('#f8d7da'))
                trend_table.setItem(row, 2, signal_item)

            # 更新动量分析表格
            momentum_table = self.get_widget('momentum_table')
            momentum_table.setRowCount(0)

            momentum_indicators = technical_data.get('momentum', {})
            for indicator, data in momentum_indicators.items():
                row = momentum_table.rowCount()
                momentum_table.insertRow(row)
                momentum_table.setItem(row, 0, QTableWidgetItem(indicator))
                momentum_table.setItem(
                    row, 1, QTableWidgetItem(str(data.get('value', ''))))

                signal = data.get('signal', 'neutral')
                signal_item = QTableWidgetItem(signal)
                if signal == 'buy':
                    signal_item.setBackground(QColor('#d4edda'))
                elif signal == 'sell':
                    signal_item.setBackground(QColor('#f8d7da'))
                momentum_table.setItem(row, 2, signal_item)

            # 更新成交量分析
            volume_text = self.get_widget('volume_text')
            volume_analysis = technical_data.get('volume', {})
            volume_summary = volume_analysis.get('summary', '暂无成交量分析数据')
            volume_text.setPlainText(volume_summary)

        except Exception as e:
            logger.error(f"Failed to update technical analysis: {e}")

    def _update_signal_analysis(self, signal_data: Dict[str, Any]) -> None:
        """更新买卖信号分析"""
        try:
            # 更新当前信号
            current_signal = signal_data.get('current_signal', {})
            main_signal_label = self.get_widget('main_signal_label')

            signal_type = current_signal.get('type', 'neutral')
            signal_text = current_signal.get('description', '暂无信号')

            main_signal_label.setText(signal_text)

            # 设置信号颜色
            if signal_type == 'buy':
                main_signal_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; color: #28a745; padding: 10px;")
            elif signal_type == 'sell':
                main_signal_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; color: #dc3545; padding: 10px;")
            else:
                main_signal_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; color: #6c757d; padding: 10px;")

            # 更新信号强度
            signal_strength_bar = self.get_widget('signal_strength_bar')
            strength = current_signal.get('strength', 0)
            signal_strength_bar.setValue(int(strength))

            # 更新历史信号表格
            signal_table = self.get_widget('signal_table')
            signal_table.setRowCount(0)

            history_signals = signal_data.get('history', [])
            for signal in history_signals[-10:]:  # 只显示最近10个信号
                row = signal_table.rowCount()
                signal_table.insertRow(row)
                signal_table.setItem(
                    row, 0, QTableWidgetItem(signal.get('date', '')))
                signal_table.setItem(
                    row, 1, QTableWidgetItem(signal.get('type', '')))
                signal_table.setItem(row, 2, QTableWidgetItem(
                    str(signal.get('price', ''))))
                signal_table.setItem(row, 3, QTableWidgetItem(
                    f"{signal.get('return', 0):.2f}%"))

            # 更新信号统计
            signal_stats_text = self.get_widget('signal_stats_text')
            stats = signal_data.get('statistics', {})
            stats_text = f"""
信号总数: {stats.get('total_signals', 0)}
买入信号: {stats.get('buy_signals', 0)}
卖出信号: {stats.get('sell_signals', 0)}
胜率: {stats.get('win_rate', 0):.1f}%
平均收益: {stats.get('avg_return', 0):.2f}%
            """.strip()
            signal_stats_text.setPlainText(stats_text)

        except Exception as e:
            logger.error(f"Failed to update signal analysis: {e}")

    def _update_risk_analysis(self, risk_data: Dict[str, Any]) -> None:
        """更新风险评估"""
        try:
            # 更新风险等级
            risk_level_label = self.get_widget('risk_level_label')
            risk_level = risk_data.get('level', 'unknown')
            risk_score = risk_data.get('score', 0)

            risk_level_label.setText(
                f"{risk_level.upper()}\n风险评分: {risk_score}")

            # 设置风险等级颜色
            if risk_level == 'low':
                risk_level_label.setStyleSheet(
                    "font-size: 18px; font-weight: bold; color: #28a745; padding: 15px;")
            elif risk_level == 'medium':
                risk_level_label.setStyleSheet(
                    "font-size: 18px; font-weight: bold; color: #ffc107; padding: 15px;")
            elif risk_level == 'high':
                risk_level_label.setStyleSheet(
                    "font-size: 18px; font-weight: bold; color: #dc3545; padding: 15px;")
            else:
                risk_level_label.setStyleSheet(
                    "font-size: 18px; font-weight: bold; color: #6c757d; padding: 15px;")

            # 更新风险指标表格
            risk_table = self.get_widget('risk_table')
            risk_table.setRowCount(0)

            metrics = risk_data.get('metrics', {})
            for metric_name, metric_value in metrics.items():
                row = risk_table.rowCount()
                risk_table.insertRow(row)
                risk_table.setItem(row, 0, QTableWidgetItem(metric_name))
                risk_table.setItem(row, 1, QTableWidgetItem(str(metric_value)))

            # 更新风险建议
            risk_advice_text = self.get_widget('risk_advice_text')
            advice = risk_data.get('advice', '暂无风险建议')
            risk_advice_text.setPlainText(advice)

        except Exception as e:
            logger.error(f"Failed to update risk analysis: {e}")

    def _update_backtest_results(self, backtest_data: Dict[str, Any]) -> None:
        """更新回测结果"""
        try:
            # 更新回测结果表格
            backtest_table = self.get_widget('backtest_table')
            backtest_table.setRowCount(0)

            results = backtest_data.get('results', {})
            for metric_name, metric_value in results.items():
                row = backtest_table.rowCount()
                backtest_table.insertRow(row)
                backtest_table.setItem(row, 0, QTableWidgetItem(metric_name))
                backtest_table.setItem(
                    row, 1, QTableWidgetItem(str(metric_value)))

            # 更新交易记录表格
            trade_table = self.get_widget('trade_table')
            trade_table.setRowCount(0)

            trades = backtest_data.get('trades', [])
            for trade in trades[-20:]:  # 只显示最近20笔交易
                row = trade_table.rowCount()
                trade_table.insertRow(row)
                trade_table.setItem(
                    row, 0, QTableWidgetItem(trade.get('date', '')))
                trade_table.setItem(
                    row, 1, QTableWidgetItem(trade.get('action', '')))
                trade_table.setItem(row, 2, QTableWidgetItem(
                    str(trade.get('price', ''))))
                trade_table.setItem(row, 3, QTableWidgetItem(
                    str(trade.get('quantity', ''))))

                profit = trade.get('profit', 0)
                profit_item = QTableWidgetItem(f"{profit:.2f}")
                if profit > 0:
                    profit_item.setBackground(QColor('#d4edda'))
                elif profit < 0:
                    profit_item.setBackground(QColor('#f8d7da'))
                trade_table.setItem(row, 4, profit_item)

        except Exception as e:
            logger.error(f"Failed to update backtest results: {e}")

    def _refresh_analysis(self) -> None:
        """
        刷新分析数据 - 此方法现在应通过协调器触发数据重新加载
        """
        if not self._current_stock_code:
            self._update_status("请先选择股票")
            return

        # 发布一个事件请求主协调器刷新数据
        # 注意：这里可以定义一个新的事件类型，或者重用StockSelectedEvent
        logger.info(f"请求刷新 {self._current_stock_code} 的数据...")
        self.event_bus.publish(
            StockSelectedEvent(
                stock_code=self._current_stock_code,
                stock_name=self._current_stock_name
            )
        )
        self._update_status(f"正在重新加载 {self._current_stock_name} 的数据...")

    def _update_status(self, message: str) -> None:
        """更新状态"""
        status_label = self.get_widget('status_label')
        status_label.setText(message)

    def _run_ai_stock_selection(self) -> None:
        """运行AI选股"""
        try:
            # 获取选股条件
            condition_text = self.get_widget('ai_condition_text')
            type_combo = self.get_widget('ai_type_combo')
            risk_combo = self.get_widget('ai_risk_combo')

            condition = condition_text.toPlainText().strip()
            selection_type = type_combo.currentText()
            risk_preference = risk_combo.currentText()

            if not condition:
                QMessageBox.warning(self._root_frame, "提示", "请输入选股条件！")
                return

            self._update_status("正在执行AI选股...")

            # 模拟AI选股结果
            ai_results = [
                {
                    "code": "000001",
                    "name": "平安银行",
                    "reason": "ROE持续提升，估值合理",
                    "score": 8.5,
                    "risk": "中等",
                    "position": "10%"
                },
                {
                    "code": "600036",
                    "name": "招商银行",
                    "reason": "基本面优秀，资金流入强劲",
                    "score": 9.2,
                    "risk": "低",
                    "position": "15%"
                },
                {
                    "code": "000002",
                    "name": "万科A",
                    "reason": "地产回暖，技术指标向好",
                    "score": 7.8,
                    "risk": "中高",
                    "position": "8%"
                }
            ]

            # 更新结果表格
            result_table = self.get_widget('ai_result_table')
            result_table.setRowCount(len(ai_results))

            for i, result in enumerate(ai_results):
                result_table.setItem(i, 0, QTableWidgetItem(result["code"]))
                result_table.setItem(i, 1, QTableWidgetItem(result["name"]))
                result_table.setItem(i, 2, QTableWidgetItem(result["reason"]))
                result_table.setItem(
                    i, 3, QTableWidgetItem(str(result["score"])))
                result_table.setItem(i, 4, QTableWidgetItem(result["risk"]))
                result_table.setItem(
                    i, 5, QTableWidgetItem(result["position"]))

            self._update_status("AI选股完成")
            QMessageBox.information(
                self._root_frame, "AI选股", f"选股完成，共筛选出 {len(ai_results)} 只股票")

        except Exception as e:
            logger.error(f"AI选股失败: {e}")
            self._update_status("AI选股失败")
            QMessageBox.critical(self._root_frame, "错误", f"AI选股失败: {e}")

    def _export_ai_results(self) -> None:
        """导出AI选股结果"""
        try:
            result_table = self.get_widget('ai_result_table')
            if result_table.rowCount() == 0:
                QMessageBox.warning(self._root_frame, "提示", "没有选股结果可导出！")
                return

            # 这里可以实现导出功能
            QMessageBox.information(self._root_frame, "导出", "AI选股结果导出功能开发中...")

        except Exception as e:
            logger.error(f"导出AI选股结果失败: {e}")
            QMessageBox.critical(self._root_frame, "错误", f"导出失败: {e}")

    def _refresh_industry_data(self) -> None:
        """刷新行业数据"""
        try:
            self._update_status("正在刷新行业数据...")

            # 模拟行业概况数据
            overview_data = [
                ("所属行业", "银行"),
                ("行业排名", "3/42"),
                ("市盈率", "5.2"),
                ("市净率", "0.6"),
                ("ROE", "12.5%"),
                ("行业景气度", "良好")
            ]

            # 更新行业概况表格
            overview_table = self.get_widget('industry_overview_table')
            overview_table.setRowCount(len(overview_data))

            for i, (indicator, value) in enumerate(overview_data):
                overview_table.setItem(i, 0, QTableWidgetItem(indicator))
                overview_table.setItem(i, 1, QTableWidgetItem(value))

            # 模拟板块表现数据
            performance_data = [
                ("银行", "+2.3%", "125.6亿", "招商银行"),
                ("地产", "-1.2%", "89.3亿", "万科A"),
                ("证券", "+3.8%", "156.7亿", "中信证券"),
                ("保险", "+1.5%", "67.2亿", "中国平安")
            ]

            # 更新板块表现表格
            performance_table = self.get_widget('industry_performance_table')
            performance_table.setRowCount(len(performance_data))

            for i, (sector, change, volume, leader) in enumerate(performance_data):
                performance_table.setItem(i, 0, QTableWidgetItem(sector))

                change_item = QTableWidgetItem(change)
                if change.startswith('+'):
                    change_item.setBackground(QColor('#d4edda'))
                elif change.startswith('-'):
                    change_item.setBackground(QColor('#f8d7da'))
                performance_table.setItem(i, 1, change_item)

                performance_table.setItem(i, 2, QTableWidgetItem(volume))
                performance_table.setItem(i, 3, QTableWidgetItem(leader))

            # 更新热点分析
            hotspot_text = self.get_widget('industry_hotspot_text')
            hotspot_analysis = """
当前市场热点分析：
1. 银行板块受益于利率回升预期，估值修复空间较大
2. 科技股在政策支持下持续活跃，关注AI、芯片等细分领域
3. 新能源板块调整充分，优质标的具备投资价值
4. 消费板块复苏趋势明确，关注必选消费和服务消费
            """
            hotspot_text.setPlainText(hotspot_analysis.strip())

            self._update_status("行业数据刷新完成")

        except Exception as e:
            logger.error(f"刷新行业数据失败: {e}")
            self._update_status("刷新行业数据失败")
            QMessageBox.critical(self._root_frame, "错误", f"刷新行业数据失败: {e}")

    @pyqtSlot()
    def _on_backtest_params_changed(self) -> None:
        """回测参数变化处理"""
        # 参数变化时可以自动重新运行回测
        pass

    def on_stock_selected(self, event: StockSelectedEvent) -> None:
        """处理股票选择事件"""
        # 这个方法现在可以被废弃，因为协调器会处理数据加载
        # self.load_stock_analysis(event.stock_code, event.stock_name)
        pass

    def on_analysis_complete(self, event: AnalysisCompleteEvent) -> None:
        """处理分析完成事件"""
        if event.stock_code == self.get_current_stock():
            # 可以在这里进行额外的处理
            pass

    def get_current_stock(self) -> str:
        """获取当前股票代码"""
        return self._current_stock_code

    def get_analysis_data(self) -> Optional[Dict[str, Any]]:
        """获取分析数据"""
        return self._analysis_data

    def _do_dispose(self) -> None:
        """清理资源"""
        try:
            # 停止加载线程
            # if hasattr(self, '_loader_thread') and self._loader_thread and self._loader_thread.isRunning():
            #     logger.info("Stopping analysis data loader thread...")
            #     self._loader_thread.quit()

            #     # 等待线程正常退出
            #     if not self._loader_thread.wait(5000):  # 等待5秒
            #         logger.warning(
            #             "Analysis thread did not quit gracefully, terminating...")
            #         self._loader_thread.terminate()
            #         self._loader_thread.wait()

            #     self._loader_thread.deleteLater()
            #     self._loader_thread = None

            # 清理分析数据
            self._analysis_data = None

            # 调用父类清理
            super()._do_dispose()

            logger.info("Right panel disposed")

        except Exception as e:
            logger.error(f"Failed to dispose right panel: {e}")
