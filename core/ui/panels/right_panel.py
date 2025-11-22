from loguru import logger
"""
右侧面板 - 修复版

修复问题：
1. 形态分析标签页数据设置问题
2. 基础功能组件NoneType错误
3. 数据更新时的组件访问问题
"""

import traceback
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
from core.performance import get_performance_monitor
from core.events import StockSelectedEvent, AnalysisCompleteEvent, ChartUpdateEvent, UIDataReadyEvent
from core.services.analysis_service import AnalysisService

# 导入完整的技术分析标签页
try:
    from gui.widgets.analysis_tabs.technical_tab import TechnicalAnalysisTab
    TECHNICAL_TAB_AVAILABLE = True
except ImportError as e:
    # ✅ 修复：只记录实际导入失败的情况，忽略内部依赖模块的缺失
    error_msg = str(e)
    # 如果错误信息中包含 enhanced_kline_technical_tab，说明是内部依赖问题，使用 debug 级别
    if 'enhanced_kline_technical_tab' in error_msg:
        logger.debug(f"TechnicalAnalysisTab 内部依赖模块未实现（enhanced_kline_technical_tab），这是正常的: {e}")
    else:
        logger.warning(f"无法导入TechnicalAnalysisTab: {e}")
    TECHNICAL_TAB_AVAILABLE = False

# 导入其他专业分析标签页
try:
    from gui.widgets.analysis_tabs.pattern_tab import PatternAnalysisTab
    from gui.widgets.analysis_tabs.trend_tab import TrendAnalysisTab
    from gui.widgets.analysis_tabs.wave_tab import WaveAnalysisTab
    from gui.widgets.analysis_tabs.sector_flow_tab import SectorFlowTab
    from gui.widgets.analysis_tabs.hotspot_tab import HotspotAnalysisTab
    PROFESSIONAL_TABS_AVAILABLE = True
    ENHANCED_SENTIMENT_AVAILABLE = True
except ImportError as e:
    # ✅ 修复：只记录实际导入失败的情况，忽略内部依赖模块的缺失
    error_msg = str(e)
    # 如果错误信息中包含 enhanced_kline_technical_tab，说明是内部依赖问题，使用 debug 级别
    if 'enhanced_kline_technical_tab' in error_msg:
        logger.debug(f"专业分析标签页内部依赖模块未实现（enhanced_kline_technical_tab），这是正常的: {e}")
    else:
        logger.warning(f"无法导入专业分析标签页: {e}")
    PROFESSIONAL_TABS_AVAILABLE = False
    ENHANCED_SENTIMENT_AVAILABLE = False

# 情绪分析标签页已移除（优化性能，避免不必要的网络请求）
PROFESSIONAL_SENTIMENT_AVAILABLE = False

# 导入K线技术分析标签页
# ✅ 修复：enhanced_kline_technical_tab模块暂未实现，暂时禁用
KLINE_TECHNICAL_AVAILABLE = False
# try:
#     from gui.widgets.analysis_tabs.enhanced_kline_technical_tab import EnhancedKLineTechnicalTab
#     KLINE_TECHNICAL_AVAILABLE = True
# except ImportError as e:
#     logger.warning(f"无法导入K线技术分析标签页: {e}")
#     KLINE_TECHNICAL_AVAILABLE = False

# 导入AnalysisToolsPanel
try:
    from gui.ui_components import AnalysisToolsPanel
    ANALYSIS_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入AnalysisToolsPanel: {e}")
    ANALYSIS_TOOLS_AVAILABLE = False

# 导入TradingPanel
try:
    from gui.widgets.trading_panel import TradingPanel
    TRADING_PANEL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入TradingPanel: {e}")
    TRADING_PANEL_AVAILABLE = False

if TYPE_CHECKING:
    from core.services import AnalysisService

logger = logger


class RightPanel(BasePanel):
    """
    右侧面板 - 修复版

    功能：
    1. 技术指标分析
    2. 买卖信号分析
    3. 风险评估
    4. 历史回测结果
    5. 热点分析与资金流向（情绪分析已优化移除）
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
        if coordinator and hasattr(coordinator, 'service_container') and coordinator.service_container:
            try:
                self.analysis_service = coordinator.service_container.resolve(AnalysisService)
            except Exception as e:
                logger.warning(f"无法获取AnalysisService: {e}")
        self.width = width

        # 当前状态
        self._current_stock_code = ''
        self._current_stock_name = ''
        self._analysis_type = 'comprehensive'  # 默认使用综合分析

        # 分析数据
        self._analysis_data = None

        # 专业标签页列表
        self._professional_tabs = []
        self._has_basic_tabs = False  # 标记是否创建了基础标签页

        # ✅ 优化2：待更新标签页跟踪（懒加载机制）
        self._pending_tab_updates = {}  # {tab_index: kline_data}
        self._tab_stock_code = {}       # {tab_index: stock_code} 跟踪每个标签页的数据

        # 性能优化管理器
        self._performance_manager = None

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
        analysis_time_label.setStyleSheet("font-size: 12px; color: #cc757d;")
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

        # 专业技术分析标签页
        if TECHNICAL_TAB_AVAILABLE:
            config_manager = None
            try:
                if self.coordinator and hasattr(self.coordinator, 'service_container'):
                    from utils.config_manager import ConfigManager
                    config_manager = self.coordinator.service_container.resolve(ConfigManager)
            except Exception as e:
                logger.warning(f"无法获取ConfigManager: {e}")

            self._technical_tab = TechnicalAnalysisTab(config_manager)
            tab_widget.addTab(self._technical_tab, "技术分析")
            self.add_widget('technical_tab', self._technical_tab)
            self._professional_tabs.append(self._technical_tab)

        # 专业分析标签页
        if PROFESSIONAL_TABS_AVAILABLE:
            # 形态分析 - 异步初始化
            try:
                self._pattern_tab = PatternAnalysisTab(config_manager, event_bus=self.coordinator.event_bus)
                tab_widget.addTab(self._pattern_tab, "形态分析")
                self.add_widget('pattern_tab', self._pattern_tab)
                self._professional_tabs.append(self._pattern_tab)
            except Exception as e:
                logger.error(f"创建形态分析标签页失败: {e}")

            # 趋势分析 - 异步初始化
            try:
                self._trend_tab = TrendAnalysisTab(config_manager)
                tab_widget.addTab(self._trend_tab, "趋势分析")
                self.add_widget('trend_tab', self._trend_tab)
                self._professional_tabs.append(self._trend_tab)
            except Exception as e:
                logger.error(f"创建趋势分析标签页失败: {e}")

            # 波浪分析 - 异步初始化
            try:
                self._wave_tab = WaveAnalysisTab(config_manager)
                tab_widget.addTab(self._wave_tab, "波浪分析")
                self.add_widget('wave_tab', self._wave_tab)
                self._professional_tabs.append(self._wave_tab)
            except Exception as e:
                logger.error(f"创建波浪分析标签页失败: {e}")

            # 情绪分析标签页已移除（优化性能，避免不必要的网络请求）
            # 不再创建情绪分析标签页，已被热点分析等功能替代
            logger.info("情绪分析标签页已优化移除，可使用热点分析等功能")
            import time
            # K线技术分析 - 使用服务容器
            if KLINE_TECHNICAL_AVAILABLE:
                try:
                    logger.info("开始创建K线技术分析标签页...")
                    
                    start_time = time.time()

                    logger.info("导入K线技术分析标签页模块...")
                    logger.info("K线技术分析标签页模块导入成功")

                    logger.info("创建K线技术分析标签页实例...")
                    self._kline_technical_tab = EnhancedKLineTechnicalTab(
                        config_manager=config_manager
                    )

                    create_time = time.time()
                    logger.info(f"⏱ K线技术分析标签页实例创建耗时: {(create_time - start_time):.2f}秒")

                    logger.info("添加K线技术分析标签页到UI...")
                    tab_widget.addTab(self._kline_technical_tab, "K线技术")

                    # 注册到组件管理
                    logger.info("注册K线技术分析标签页到组件管理...")
                    self.add_widget('kline_technical_tab', self._kline_technical_tab)
                    self._professional_tabs.append(self._kline_technical_tab)

                    end_time = time.time()
                    logger.info(f" K线技术分析标签页创建完成，总耗时: {(end_time - start_time):.2f}秒")
                except Exception as kline_error:
                    logger.error(f" K线技术分析标签页创建失败: {kline_error}")
                    logger.error(traceback.format_exc())

            # ✅ 修复：板块资金流 - 使用服务容器（缩进修复，应在 if PROFESSIONAL_TABS_AVAILABLE 块内）
            try:
                logger.info("开始创建板块资金流标签页...")
                start_time = time.time()

                logger.info("导入板块资金流标签页模块...")
                logger.info("板块资金流标签页模块导入成功")

                logger.info("创建板块资金流标签页实例...")
                self._sector_flow_tab = SectorFlowTab(
                    config_manager=config_manager,
                    service_container=self.coordinator.service_container
                )

                create_time = time.time()
                logger.info(f"⏱ 板块资金流标签页实例创建耗时: {(create_time - start_time):.2f}秒")

                logger.info("添加板块资金流标签页到UI...")
                tab_widget.addTab(self._sector_flow_tab, "板块资金流")

                # 注册到组件管理
                logger.info("注册板块资金流标签页到组件管理...")
                self.add_widget('sector_flow_tab', self._sector_flow_tab)
                self._professional_tabs.append(self._sector_flow_tab)

                end_time = time.time()
                logger.info(f" 板块资金流标签页创建完成，总耗时: {(end_time - start_time):.2f}秒")
            except Exception as e:
                logger.error(f" 板块资金流标签页创建失败: {e}")
                logger.error(traceback.format_exc())

            # 热点分析 - 使用服务容器
            try:
                self._hotspot_tab = HotspotAnalysisTab(
                    config_manager=config_manager,
                    service_container=self.coordinator.service_container
                )
                tab_widget.addTab(self._hotspot_tab, "热点分析")

                # 注册到组件管理
                self.add_widget('hotspot_tab', self._hotspot_tab)
                self._professional_tabs.append(self._hotspot_tab)

                logger.info("热点分析标签页创建完成")
            except Exception as e:
                logger.error(f" 热点分析标签页创建失败: {e}")
                logger.error(traceback.format_exc())

        # 基础功能标签页（如果专业标签页不可用时的后备方案，或者总是创建）
        # 修复：总是创建基础标签页，但只有在需要时才显示
        self._create_signal_tab(tab_widget)
        self._create_risk_tab(tab_widget)
        self._create_backtest_tab(tab_widget)
        self._create_ai_stock_tab(tab_widget)
        self._create_industry_tab(tab_widget)
        self._has_basic_tabs = True

        # 如果有专业标签页，隐藏基础标签页
        if PROFESSIONAL_TABS_AVAILABLE:
            # 隐藏基础标签页（将它们移到不可见状态，但保持组件存在）
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i) in ["买卖信号", "风险评估", "历史回测", "AI选股", "行业分析"]:
                    tab_widget.removeTab(i)
                    break

        # 批量分析工具标签页
        if ANALYSIS_TOOLS_AVAILABLE:
            # 创建一个继承自QWidget的包装器来传递log_manager
            class AnalysisToolsWrapper(QWidget):
                def __init__(self, parent, logger):
                    super().__init__(parent)
                    # log_manager已迁移到Loguru

            wrapper = AnalysisToolsWrapper(self._root_frame, logger)
            self._analysis_tools_panel = AnalysisToolsPanel(parent=wrapper)
            tab_widget.addTab(self._analysis_tools_panel, "批量分析")
            self.add_widget('analysis_tools_panel', self._analysis_tools_panel)

        # 实盘交易标签页
        if TRADING_PANEL_AVAILABLE:
            try:
                # 从服务容器获取交易服务
                trading_service = None
                if self.coordinator and hasattr(self.coordinator, 'service_container'):
                    from core.services.trading_service import TradingService
                    trading_service = self.coordinator.service_container.resolve(TradingService)

                if trading_service:
                    self._trading_panel = TradingPanel(
                        trading_service=trading_service,
                        event_bus=self.coordinator.event_bus,
                        parent=self._root_frame
                    )
                    tab_widget.addTab(self._trading_panel, "实盘交易")
                    self.add_widget('trading_panel', self._trading_panel)
                    logger.info("实盘交易标签页创建成功")
                else:
                    logger.warning("无法获取TradingService，跳过实盘交易标签页")

            except Exception as e:
                logger.error(f" 创建实盘交易标签页失败: {e}")
                logger.error(traceback.format_exc())

        # 性能监控标签页已删除 - 根据用户要求移除

        # 控制按钮框架
        button_frame = QFrame()
        main_layout.addWidget(button_frame)
        self.add_widget('button_frame', button_frame)

        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 5, 0, 0)
        button_layout.setSpacing(5)

        # 刷新分析按钮
        refresh_btn = QPushButton("刷新分析")
        refresh_btn.clicked.connect(self._refresh_analysis)
        button_layout.addWidget(refresh_btn)
        self.add_widget('refresh_btn', refresh_btn)

        # 导出报告按钮
        export_btn = QPushButton("导出报告")
        export_btn.clicked.connect(self._export_report)
        button_layout.addWidget(export_btn)
        self.add_widget('export_btn', export_btn)

        # 性能监控按钮已删除 - 根据用户要求移除

        # 状态标签
        status_label = QLabel("就绪")
        status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        main_layout.addWidget(status_label)
        self.add_widget('status_label', status_label)

        # 在所有标签页创建完成后，初始化性能管理器
        QTimer.singleShot(100, self._initialize_performance_manager)

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

        # 信号状态标签
        signal_status_label = QLabel("暂无信号")
        signal_status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #6c757d; padding: 20px;")
        signal_status_label.setAlignment(Qt.AlignCenter)
        current_signal_layout.addWidget(signal_status_label)
        self.add_widget('signal_status_label', signal_status_label)

        # 信号历史组
        signal_history_group = QGroupBox("信号历史")
        layout.addWidget(signal_history_group)
        self.add_widget('signal_history_group', signal_history_group)

        signal_history_layout = QVBoxLayout(signal_history_group)

        # 信号历史表格
        signal_table = QTableWidget(0, 5)
        signal_table.setHorizontalHeaderLabels(['时间', '信号', '价格', '强度', '收益'])
        signal_table.horizontalHeader().setStretchLastSection(True)
        signal_table.setAlternatingRowColors(True)
        signal_history_layout.addWidget(signal_table)
        self.add_widget('signal_table', signal_table)

        # 信号统计组
        signal_stats_group = QGroupBox("信号统计")
        layout.addWidget(signal_stats_group)
        self.add_widget('signal_stats_group', signal_stats_group)

        signal_stats_layout = QVBoxLayout(signal_stats_group)

        # 信号统计文本
        signal_stats_text = QTextEdit()
        signal_stats_text.setReadOnly(True)
        signal_stats_text.setMaximumHeight(100)
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

        # 风险等级标签
        risk_level_label = QLabel("未知\n风险评分: --")
        risk_level_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #6c757d; padding: 15px;")
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

        # 风险建议文本
        risk_advice_text = QTextEdit()
        risk_advice_text.setReadOnly(True)
        risk_advice_text.setMaximumHeight(100)
        risk_advice_layout.addWidget(risk_advice_text)
        self.add_widget('risk_advice_text', risk_advice_text)

    def _create_backtest_tab(self, parent: QTabWidget) -> None:
        """创建历史回测标签页"""
        backtest_widget = QWidget()
        parent.addTab(backtest_widget, "历史回测")
        self.add_widget('backtest_widget', backtest_widget)

        layout = QVBoxLayout(backtest_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 回测结果组
        backtest_results_group = QGroupBox("回测结果")
        layout.addWidget(backtest_results_group)
        self.add_widget('backtest_results_group', backtest_results_group)

        backtest_results_layout = QVBoxLayout(backtest_results_group)

        # 回测结果表格
        backtest_table = QTableWidget(0, 2)
        backtest_table.setHorizontalHeaderLabels(['指标', '数值'])
        backtest_table.horizontalHeader().setStretchLastSection(True)
        backtest_table.setAlternatingRowColors(True)
        backtest_table.setMaximumHeight(150)
        backtest_results_layout.addWidget(backtest_table)
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
        self.event_bus.subscribe(UIDataReadyEvent, self._on_ui_data_ready)
        logger.debug("RightPanel已订阅UIDataReadyEvent事件")
        
        # ✅ 优化2：连接标签页切换信号，实现懒加载
        tab_widget = self.get_widget('tab_widget')
        if tab_widget:
            tab_widget.currentChanged.connect(self._on_tab_changed)
            logger.debug("已连接标签页切换信号（懒加载机制）")

    def _initialize_performance_manager(self) -> None:
        """初始化性能管理器"""
        try:
            # 获取标签页组件
            tab_widget = self.get_widget('tab_widget')

            # 使用统一性能监控系统
            self._performance_manager = get_performance_monitor()

            # 标签页性能监控已通过统一系统自动启用
            logger.info("标签页性能监控已启用")

            logger.info("统一性能监控系统已集成")

            # 统一性能监控标签页已自动连接到性能监控系统
            if hasattr(self, '_performance_monitor_tab') and self._performance_monitor_tab:
                logger.info("统一性能监控标签页已就绪")

        except Exception as e:
            logger.error(f" 性能管理器初始化失败: {e}")

    def _register_tabs_with_performance_monitor(self):
        """标签页性能监控已通过统一系统自动处理"""
        logger.info(f" 标签页性能监控已启用，共监控 {len(self._professional_tabs)} 个标签页")

    def _update_tab_with_performance_manager(self, tab, data, progressive=False):
        """更新标签页数据（兼容性方法）"""
        try:
            if hasattr(tab, 'set_kdata'):
                if progressive and hasattr(tab, 'append_kdata'):
                    tab.append_kdata(data)
                else:
                    tab.set_kdata(data)
            logger.debug(f"标签页数据更新完成: {type(tab).__name__}")
        except Exception as e:
            logger.error(f"标签页数据更新失败: {type(tab).__name__}, 错误: {e}")

    def _show_performance_monitor(self):
        """显示性能监控窗口"""
        try:
            from gui.widgets.modern_performance_widget import show_modern_performance_monitor
            self._performance_monitor = show_modern_performance_monitor(self)
            if self._performance_monitor:
                logger.info("性能监控窗口已打开")
            else:
                logger.error("无法打开性能监控窗口")

        except Exception as e:
            logger.error(f"显示性能监控窗口失败: {e}")

    def _initialize_data(self) -> None:
        """初始化数据"""
        # 初始状态下显示提示信息
        self._update_status("请在左侧选择一只股票以开始分析")

    @pyqtSlot(UIDataReadyEvent)
    def _on_ui_data_ready(self, event: UIDataReadyEvent) -> None:
        """处理UI数据就绪事件，使用性能管理器优化加载"""
        try:
            logger.info(f"RightPanel收到UIDataReadyEvent，股票: {event.stock_code}")

            # 检查是否是新股票
            is_new_stock = self._current_stock_code != event.stock_code

            # 更新股票信息
            self._current_stock_code = event.stock_code
            self._current_stock_name = event.stock_name
            self.get_widget('stock_label').setText(
                f"{self._current_stock_name} ({self._current_stock_code})")

            # 如果是新股票，重置性能管理器状态
            if is_new_stock and self._performance_manager:
                self._performance_manager.reset_for_new_stock(event.stock_code)

            # 从事件中直接获取分析数据和K线数据
            analysis_data = event.ui_data.get('analysis')
            kline_data = event.ui_data.get('kline_data')

            # 使用性能管理器更新专业标签页
            if kline_data is not None and not kline_data.empty and self._performance_manager:
                logger.info(f"使用性能管理器更新专业标签页，数据长度: {len(kline_data)}")
                self._update_professional_tabs_with_performance_manager(kline_data)
            elif kline_data is not None and not kline_data.empty:
                # 回退到原有机制（如果性能管理器不可用）
                logger.warning("性能管理器不可用，使用原有更新机制")
                self._async_update_professional_tabs(kline_data)

            # 如果有分析数据，更新基础功能标签页（只有在组件存在时）
            if analysis_data and self._has_basic_tabs:
                self._update_analysis_display(analysis_data)

            # 更新状态为数据加载完成
            self._update_status(f"已加载 {self._current_stock_name} 数据，分析完成")

            logger.info(f"RightPanel已成功更新 {event.stock_code} 的分析数据")

        except Exception as e:
            logger.error(f"处理UIDataReadyEvent失败: {e}")
            logger.error(traceback.format_exc())

    def _update_professional_tabs_with_performance_manager(self, kline_data):
        """✅ 优化2：使用性能管理器更新专业标签页（懒加载机制）"""
        try:
            tab_widget = self.get_widget('tab_widget')
            if not tab_widget:
                logger.warning("标签页组件不存在，跳过更新")
                return
            
            # 获取当前激活的标签页索引
            current_index = tab_widget.currentIndex()
            logger.info(f"当前激活标签页索引: {current_index}/{len(self._professional_tabs)}")
            
            # 为每个标签页更新数据或标记为待更新
            for i, tab in enumerate(self._professional_tabs):
                # 获取标签页类型
                tab_type = type(tab).__name__.lower().replace('tab', '').replace('analysis', '')

                # 检查标签页是否跳过K线数据
                if hasattr(tab, 'skip_kdata') and getattr(tab, 'skip_kdata') is True:
                    logger.debug(f"跳过标签页（skip_kdata=True）: {tab_type}")
                    continue
                
                # ✅ 懒加载：只更新当前激活的标签页
                if i == current_index:
                    logger.info(f"立即更新当前激活标签页: {tab_type} (索引{i})")
                    # 使用性能管理器更新数据
                    self._performance_manager.update_tab_data(
                        stock_code=self._current_stock_code,
                        tab_id=tab_type,
                        tab_widget=tab,  # 传递tab组件本身
                        data=kline_data,
                        use_cache=True
                    )
                    # 记录已更新
                    self._tab_stock_code[i] = self._current_stock_code
                else:
                    # 标记为待更新
                    logger.debug(f"标记标签页为待更新: {tab_type} (索引{i})")
                    self._pending_tab_updates[i] = kline_data
                    # 清除旧的股票代码标记
                    if i in self._tab_stock_code:
                        del self._tab_stock_code[i]

            logger.info(f"✓ 懒加载完成：立即更新1个标签页，待更新{len(self._pending_tab_updates)}个")

        except Exception as e:
            logger.error(f"✗ 性能管理器更新标签页失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 回退到原有机制
            self._async_update_professional_tabs(kline_data)

    def _on_tab_changed(self, index: int):
        """✅ 优化2：标签页切换处理器（懒加载触发）"""
        try:
            logger.info(f"标签页切换到索引: {index}")
            
            # 检查是否有待更新的数据
            if index in self._pending_tab_updates:
                kline_data = self._pending_tab_updates.pop(index)
                logger.info(f"加载待更新标签页数据（索引{index}）")
                
                # 获取对应的标签页
                if index < len(self._professional_tabs):
                    tab = self._professional_tabs[index]
                    tab_type = type(tab).__name__.lower().replace('tab', '').replace('analysis', '')
                    
                    # 使用性能管理器更新数据
                    if self._performance_manager:
                        self._performance_manager.update_tab_data(
                            stock_code=self._current_stock_code,
                            tab_id=tab_type,
                            tab_widget=tab,
                            data=kline_data,
                            use_cache=True
                        )
                        # 记录已更新
                        self._tab_stock_code[index] = self._current_stock_code
                        logger.info(f"✓ 懒加载完成：{tab_type}")
                    else:
                        logger.warning("性能管理器不可用，跳过更新")
                else:
                    logger.warning(f"标签页索引{index}超出范围（总数{len(self._professional_tabs)}）")
            else:
                # 检查是否需要刷新（股票已变更）
                if index in self._tab_stock_code and self._tab_stock_code[index] != self._current_stock_code:
                    logger.debug(f"标签页{index}的股票已变更，但数据已在待更新队列中")
        
        except Exception as e:
            logger.error(f"标签页切换处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _async_update_professional_tabs(self, kline_data):
        """✅ 性能优化：并行更新专业标签页，避免阻塞UI线程"""
        try:
            from PyQt5.QtCore import QTimer
            from concurrent.futures import ThreadPoolExecutor
            import os

            # ✅ 性能优化：使用线程池并行更新标签页
            if not hasattr(self, '_tab_update_executor'):
                self._tab_update_executor = ThreadPoolExecutor(max_workers=min(3, len(self._professional_tabs)))
            
            # 创建一个队列来管理标签页更新
            self._tab_update_queue = list(self._professional_tabs)
            self._current_kline_data = kline_data

            # 使用定时器批量处理标签页更新
            if not hasattr(self, '_tab_update_timer'):
                self._tab_update_timer = QTimer()
                self._tab_update_timer.setSingleShot(True)
                self._tab_update_timer.timeout.connect(self._process_next_tab_update)

            # 延迟开始处理，确保UI渲染完成
            self._tab_update_timer.start(100)  # 100ms后开始处理

        except Exception as e:
            logger.error(f"异步更新专业标签页失败: {e}")
            # 如果异步更新失败，回退到同步更新
            self._sync_update_professional_tabs(kline_data)

    def _process_next_tab_update(self):
        """✅ 性能优化：并行处理多个标签页更新"""
        try:
            if not hasattr(self, '_tab_update_queue') or not self._tab_update_queue:
                logger.debug("所有专业标签页数据更新完成")
                return

            # ✅ 性能优化：并行处理多个标签页（最多3个）
            tabs_to_update = []
            for _ in range(min(3, len(self._tab_update_queue))):
                if self._tab_update_queue:
                    tabs_to_update.append(self._tab_update_queue.pop(0))
            
            if not tabs_to_update:
                return

            # 使用线程池并行更新
            if hasattr(self, '_tab_update_executor'):
                futures = []
                for tab in tabs_to_update:
                    if hasattr(tab, 'skip_kdata') and getattr(tab, 'skip_kdata') is True:
                        logger.debug(f"跳过向{type(tab).__name__}传递K线数据（skip_kdata=True）")
                        continue
                    
                    # 提交更新任务到线程池
                    future = self._tab_update_executor.submit(self._update_single_tab, tab)
                    futures.append(future)
                
                # 等待所有更新完成（可选，也可以不等待）
                # for future in futures:
                #     try:
                #         future.result(timeout=5)  # 5秒超时
                #     except Exception as e:
                #         logger.error(f"标签页更新失败: {e}")
            else:
                # 回退到串行更新
                for tab in tabs_to_update:
                    self._update_single_tab(tab)

            # 如果还有更多标签页需要处理，调度下一次更新
            if self._tab_update_queue:
                self._tab_update_timer.start(50)  # ✅ 优化：减少间隔到50ms，提升并行度

        except Exception as e:
            logger.error(f"处理标签页更新失败: {e}")

    def _update_single_tab(self, tab):
        """更新单个标签页的数据（线程安全）"""
        try:
            if hasattr(tab, 'set_kdata'):
                tab.set_kdata(self._current_kline_data)
                # 如果是形态分析标签页，确保数据正确设置
                if hasattr(tab, 'kdata'):
                    tab.kdata = self._current_kline_data
                logger.debug(f"K线数据已传递到{type(tab).__name__}")
        except Exception as e:
            logger.error(f"传递K线数据到{type(tab).__name__}失败: {e}")

    def _sync_update_professional_tabs(self, kline_data):
        """同步更新专业标签页（作为异步更新的备用方案）"""
        try:
            # 传递到所有专业标签页
            for tab in self._professional_tabs:
                if hasattr(tab, 'set_kdata'):
                    try:
                        tab.set_kdata(kline_data)
                        # 如果是形态分析标签页，确保数据正确设置
                        if hasattr(tab, 'kdata'):
                            tab.kdata = kline_data
                        logger.debug(f"K线数据已传递到{type(tab).__name__}")
                    except Exception as e:
                        logger.error(f"传递K线数据到{type(tab).__name__}失败: {e}")
        except Exception as e:
            logger.error(f"同步更新专业标签页失败: {e}")

    def _update_analysis_display(self, analysis_data: Dict[str, Any]) -> None:
        """更新分析数据显示"""
        try:
            # 更新信号分析（安全检查）
            if 'signals' in analysis_data:
                self._update_signal_analysis_safe(analysis_data['signals'])

            # 更新风险评估（安全检查）
            if 'risk' in analysis_data:
                self._update_risk_analysis_safe(analysis_data['risk'])

            # 更新回测结果（安全检查）
            if 'backtest' in analysis_data:
                self._update_backtest_results_safe(analysis_data['backtest'])

        except Exception as e:
            logger.error(f"更新分析数据显示失败: {e}")

    def _update_signal_analysis_safe(self, signal_data: Dict[str, Any]) -> None:
        """安全更新信号分析"""
        try:
            # 更新当前信号状态
            signal_status_label = self.get_widget('signal_status_label')
            if signal_status_label:
                current_signal = signal_data.get('current', {})
                if current_signal:
                    signal_type = current_signal.get('type', 'unknown')
                    signal_strength = current_signal.get('strength', 0)
                    signal_status_label.setText(
                        f"{signal_type.upper()}\n强度: {signal_strength}")

                    # 设置信号颜色
                    if signal_type == 'buy':
                        signal_status_label.setStyleSheet(
                            "font-size: 18px; font-weight: bold; color: #28a745; padding: 20px;")
                    elif signal_type == 'sell':
                        signal_status_label.setStyleSheet(
                            "font-size: 18px; font-weight: bold; color: #dc3545; padding: 20px;")
                    else:
                        signal_status_label.setStyleSheet(
                            "font-size: 18px; font-weight: bold; color: #6c757d; padding: 20px;")
                else:
                    signal_status_label.setText("暂无信号")

            # 更新信号历史表格
            signal_table = self.get_widget('signal_table')
            if signal_table:
                signal_table.setRowCount(0)

                signals = signal_data.get('history', [])
                for signal in signals[-10:]:  # 只显示最近10个信号
                    row = signal_table.rowCount()
                    signal_table.insertRow(row)
                    signal_table.setItem(row, 0, QTableWidgetItem(signal.get('time', '')))
                    signal_table.setItem(row, 1, QTableWidgetItem(signal.get('type', '')))
                    signal_table.setItem(row, 2, QTableWidgetItem(str(signal.get('price', ''))))
                    signal_table.setItem(row, 3, QTableWidgetItem(str(signal.get('strength', ''))))
                    signal_table.setItem(row, 4, QTableWidgetItem(
                        f"{signal.get('return', 0):.2f}%"))

            # 更新信号统计
            signal_stats_text = self.get_widget('signal_stats_text')
            if signal_stats_text:
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

    def _update_risk_analysis_safe(self, risk_data: Dict[str, Any]) -> None:
        """安全更新风险评估"""
        try:
            # 更新风险等级
            risk_level_label = self.get_widget('risk_level_label')
            if risk_level_label:
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
            if risk_table:
                risk_table.setRowCount(0)

                metrics = risk_data.get('metrics', {})
                for metric_name, metric_value in metrics.items():
                    row = risk_table.rowCount()
                    risk_table.insertRow(row)
                    risk_table.setItem(row, 0, QTableWidgetItem(metric_name))
                    risk_table.setItem(row, 1, QTableWidgetItem(str(metric_value)))

            # 更新风险建议
            risk_advice_text = self.get_widget('risk_advice_text')
            if risk_advice_text:
                advice = risk_data.get('advice', '暂无风险建议')
                risk_advice_text.setPlainText(advice)

        except Exception as e:
            logger.error(f"Failed to update risk analysis: {e}")

    def _update_backtest_results_safe(self, backtest_data: Dict[str, Any]) -> None:
        """安全更新回测结果"""
        try:
            # 更新回测结果表格
            backtest_table = self.get_widget('backtest_table')
            if backtest_table:
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
            if trade_table:
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

    def _update_status(self, message: str) -> None:
        """更新状态"""
        status_label = self.get_widget('status_label')
        if status_label:
            status_label.setText(message)

    def _refresh_analysis(self) -> None:
        """刷新分析数据"""
        if not self._current_stock_code:
            self._update_status("请在左侧选择一只股票以开始分析")
            return

        # 更新状态显示正在刷新
        self._update_status(f"正在刷新 {self._current_stock_name} 的分析数据...")

        try:
            # 发布事件请求重新加载数据
            from core.events import StockSelectedEvent

            if self.coordinator and hasattr(self.coordinator, 'event_bus'):
                self.coordinator.event_bus.publish(StockSelectedEvent(
                    stock_code=self._current_stock_code,
                    stock_name=self._current_stock_name
                ))
                logger.info(f"请求刷新 {self._current_stock_code} 的数据...")
            else:
                self._update_status("无法刷新数据：缺少事件总线")

        except Exception as e:
            logger.error(f"刷新分析数据失败: {e}")
            self._update_status("刷新失败")

    def _export_report(self) -> None:
        """导出分析报告"""
        if not self._current_stock_code:
            self._update_status("请先选择股票再导出报告")
            return

        self._update_status("报告导出功能开发中...")
        # TODO: 实现报告导出功能

    def get_current_stock_info(self) -> Dict[str, str]:
        """获取当前股票信息"""
        return {
            'code': self._current_stock_code,
            'name': self._current_stock_name
        }
