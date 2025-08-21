"""
重构后的分析控件模块 - 使用模块化标签页组件
"""
from utils.manager_factory import get_config_manager, get_log_manager
from analysis.pattern_manager import PatternManager
from .analysis_tabs import (
    TechnicalAnalysisTab,
    PatternAnalysisTab,
    TrendAnalysisTab,
    SectorFlowTab,
    WaveAnalysisTab,
    SentimentAnalysisTab,
    HotspotAnalysisTab
)
from utils.data_preprocessing import kdata_preprocess as _kdata_preprocess
from PyQt5.QtWidgets import QWidget
from core.risk_exporter import RiskExporter
from data.data_loader import generate_quality_report
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QTimer
from typing import Dict, Any, List, Optional, Callable
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
from datetime import *
import pandas as pd
from PyQt5.QtGui import QColor, QKeySequence

from .matplot_lib_widget import *
import akshare as ak
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 配置中文字体
try:
    from utils.matplotlib_font_config import configure_matplotlib_chinese_font
    configure_matplotlib_chinese_font()
except ImportError:
    print("⚠️ 无法导入字体配置工具，使用默认配置")
import importlib
import traceback
import os
import time
from concurrent.futures import *
import numba
import json
from core.logger import LogManager, LogLevel
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from hikyuu.indicator import *
from hikyuu import sm
from hikyuu import Query
# 替换旧的指标系统导入
from core.indicator_service import calculate_indicator, get_indicator_metadata, get_all_indicators_metadata
from utils.cache import Cache
import requests
from bs4 import BeautifulSoup
from analysis.pattern_recognition import PatternRecognizer
from core.data_manager import data_manager
# 移除旧的形态特征导入
# 定义ALL_PATTERN_TYPES常量
ALL_PATTERN_TYPES = [
    'CDLHAMMER', 'CDLENGULFING', 'CDLDOJI', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR',
    'CDLHARAMI', 'CDLHARAMICROSS', 'CDLMARUBOZU', 'CDLSHOOTINGSTAR', 'CDLINVERTEDHAMMER'
]

# 导入新的模块化标签页组件

# 新增导入形态管理器

# 使用统一的管理器工厂


class AnalysisWidget(QWidget):
    """重构后的分析控件类 - 使用模块化标签页组件"""

    # 定义信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)  # 新增错误信号
    pattern_selected = pyqtSignal(int)  # 新增信号，用于传递信号索引

    data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)

    def __init__(self, config_manager: Optional[ConfigManager] = None, service_container=None):
        """初始化分析控件

        Args:
            config_manager: Optional ConfigManager instance to use
            service_container: 服务容器实例
        """

        super().__init__()

        # 使用统一的管理器工厂
        self.config_manager = config_manager or get_config_manager()
        self.log_manager = get_log_manager()
        self.service_container = service_container

        # 如果没有service_container，尝试获取
        if not self.service_container:
            try:
                from core.containers import get_service_container
                self.service_container = get_service_container()
            except Exception as e:
                self.log_manager.warning(f"无法获取服务容器: {e}")
                self.service_container = None

        # 初始化更新节流器
        self.update_throttler = get_update_throttler()

        # 图表更新防抖
        self.chart_update_timer = QTimer()
        self.chart_update_timer.timeout.connect(self._execute_chart_update)
        self.chart_update_timer.setSingleShot(True)
        self._pending_chart_update = None

        # 初始化形态管理器
        try:
            if PatternManager is not None:
                self.pattern_manager = PatternManager()
            else:
                self.pattern_manager = None
                self.log_manager.warning("PatternManager未能成功导入，形态识别功能将受限")
        except Exception as e:
            self.pattern_manager = None
            self.log_manager.error(f"初始化PatternManager失败: {e}")

        self.current_kdata = None
        self.analysis_futures = []  # 存储分析任务的future对象
        self.loading_overlay = None
        self.progress_bar = None
        self.cancel_button = None
        self.data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)
        self.is_loading = False  # 初始化加载状态

        # 缓存各种信号数据
        self._all_pattern_signals = []
        self._rotation_worker = None  # 板块轮动工作线程

        # 初始化标签页组件
        self.tab_components = {}

        # 初始化UI
        self.init_ui()
        # 设置快捷键
        self.setup_shortcuts()

        # 初始化形态过滤器选项（在所有UI创建完成后）
        QTimer.singleShot(100, self._init_pattern_filters)

    def _init_pattern_filters(self):
        """延迟初始化形态过滤器选项"""
        try:
            if self.pattern_manager is not None:
                self._update_pattern_filter_options()
        except Exception as e:
            self.log_manager.warning(f"初始化形态过滤器选项失败: {e}")

    def show_loading(self, message="正在分析..."):
        """显示加载状态"""
        if self.is_loading:
            return

        self.is_loading = True

        # 创建加载遮罩层
        if not self.loading_overlay:
            self.loading_overlay = QWidget(self)
            self.loading_overlay.setStyleSheet("""
                QWidget {
                    background-color: rgba(0, 0, 0, 0.7);
                    border-radius: 8px;
                }
            """)

            overlay_layout = QVBoxLayout(self.loading_overlay)
            overlay_layout.setAlignment(Qt.AlignCenter)

            # 加载图标（使用文字代替）
            loading_icon = QLabel("⏳")
            loading_icon.setStyleSheet(
                "QLabel { color: white; font-size: 48px; }")
            loading_icon.setAlignment(Qt.AlignCenter)
            overlay_layout.addWidget(loading_icon)

            # 加载文字
            self.loading_label = QLabel(message)
            self.loading_label.setStyleSheet(
                "QLabel { color: white; font-size: 16px; font-weight: bold; }")
            self.loading_label.setAlignment(Qt.AlignCenter)
            overlay_layout.addWidget(self.loading_label)

        # 更新消息
        if self.loading_label:
            self.loading_label.setText(message)

        # 显示遮罩层
        self.loading_overlay.resize(self.size())
        self.loading_overlay.show()
        self.loading_overlay.raise_()

        # 强制刷新界面
        QApplication.processEvents()

    def hide_loading(self):
        """隐藏加载状态"""
        if not self.is_loading:
            return

        self.is_loading = False

        if self.loading_overlay:
            self.loading_overlay.hide()

        # 强制刷新界面
        QApplication.processEvents()

    def update_loading_progress(self, value, message=None):
        """更新加载进度"""
        if not self.is_loading or not self.progress_bar:
            return

        if self.progress_bar.maximum() == 0:
            # 切换到确定进度模式
            self.progress_bar.setRange(0, 100)

        self.progress_bar.setValue(value)

        if message and self.loading_label:
            self.loading_label.setText(message)

        QApplication.processEvents()

    def resizeEvent(self, event):
        """窗口大小改变时调整加载遮罩层大小"""
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.resize(self.size())

    def init_ui(self):
        """初始化用户界面 - 使用模块化标签页组件"""
        layout = QVBoxLayout(self)

        # 创建Tab控件
        self.tab_widget = QTabWidget()

        # 创建并存储各个分析标签页组件
        self._create_tab_components()

        # 添加标签页到Tab控件
        self._add_tabs_to_widget()

        # 连接Tab切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tab_widget)

    def _create_tab_components(self):
        """创建标签页组件"""
        try:
            # 技术分析标签页
            self.technical_tab = TechnicalAnalysisTab(self.config_manager)
            self.technical_tab.parent_widget = self  # 设置父组件引用
            self.tab_components['technical'] = self.technical_tab

            # 形态分析标签页
            self.pattern_tab = PatternAnalysisTab(self.config_manager)
            self.pattern_tab.parent_widget = self  # 设置父组件引用
            self.tab_components['pattern'] = self.pattern_tab

            # 趋势分析标签页
            self.trend_tab = TrendAnalysisTab(self.config_manager)
            self.trend_tab.parent_widget = self
            self.tab_components['trend'] = self.trend_tab

            # 波浪分析标签页
            self.wave_tab = WaveAnalysisTab(self.config_manager)
            self.wave_tab.parent_widget = self
            self.tab_components['wave'] = self.wave_tab

            # 情绪分析标签页 - 使用合并后的专业版（包含实时分析和报告功能）
            try:
                from .analysis_tabs.professional_sentiment_tab import ProfessionalSentimentTab
                self.sentiment_tab = ProfessionalSentimentTab(self.config_manager)
                self.sentiment_tab.parent_widget = self
                self.tab_components['sentiment'] = self.sentiment_tab

                # 情绪报告标签页 - 现在使用同一个类，因为已经包含报告功能
                self.sentiment_report_tab = self.sentiment_tab  # 共享同一个实例
                self.tab_components['sentiment_report'] = self.sentiment_report_tab
            except ImportError as e:
                print(f"⚠️ 专业情绪分析标签页导入失败: {e}")
                # 使用占位符
                self.sentiment_tab = QLabel("情绪分析功能暂不可用")
                self.sentiment_report_tab = QLabel("情绪报告功能暂不可用")
                self.tab_components['sentiment'] = self.sentiment_tab
                self.tab_components['sentiment_report'] = self.sentiment_report_tab

            # 板块资金流标签页
            self.sector_flow_tab = SectorFlowTab(self.config_manager, self.service_container)
            self.sector_flow_tab.parent_widget = self
            self.tab_components['sector_flow'] = self.sector_flow_tab

            # 热点分析标签页
            self.hotspot_tab = HotspotAnalysisTab(self.config_manager)
            self.hotspot_tab.parent_widget = self
            self.tab_components['hotspot'] = self.hotspot_tab

            # K线技术分析标签页 - 重命名删除重复情绪功能
            try:
                from .analysis_tabs.enhanced_kline_sentiment_tab import EnhancedKLineTechnicalTab
                self.kline_technical_tab = EnhancedKLineTechnicalTab(self.config_manager)
                self.kline_technical_tab.parent_widget = self
                self.tab_components['kline_technical'] = self.kline_technical_tab
            except ImportError as e:
                print(f"K线技术分析标签页导入失败: {e}")
                self.kline_technical_tab = None

            # 连接信号
            self._connect_tab_signals()

        except Exception as e:
            self.log_manager.error(f"创建标签页组件失败: {e}")
            # 创建简单的占位标签页
            self._create_placeholder_tabs()

    def _create_placeholder_tabs(self):
        """创建占位标签页（当模块化组件加载失败时）"""
        # 技术分析占位标签页
        self.technical_tab = QWidget()
        layout = QVBoxLayout(self.technical_tab)
        layout.addWidget(QLabel("技术分析功能正在加载中..."))
        self.tab_components['technical'] = self.technical_tab

        # 形态分析占位标签页
        self.pattern_tab = QWidget()
        layout = QVBoxLayout(self.pattern_tab)
        layout.addWidget(QLabel("形态分析功能正在加载中..."))
        self.tab_components['pattern'] = self.pattern_tab

        # 趋势分析占位标签页
        self.trend_tab = QWidget()
        layout = QVBoxLayout(self.trend_tab)
        layout.addWidget(QLabel("趋势分析功能正在加载中..."))
        self.tab_components['trend'] = self.trend_tab

        # 波浪分析占位标签页
        self.wave_tab = QWidget()
        layout = QVBoxLayout(self.wave_tab)
        layout.addWidget(QLabel("波浪分析功能正在加载中..."))
        self.tab_components['wave'] = self.wave_tab

        # 情绪分析占位标签页
        self.sentiment_tab = QWidget()
        layout = QVBoxLayout(self.sentiment_tab)
        layout.addWidget(QLabel("情绪分析功能正在加载中..."))
        self.tab_components['sentiment'] = self.sentiment_tab

        # 板块资金流占位标签页
        self.sector_flow_tab = QWidget()
        layout = QVBoxLayout(self.sector_flow_tab)
        layout.addWidget(QLabel("板块资金流功能正在加载中..."))
        self.tab_components['sector_flow'] = self.sector_flow_tab

        # 热点分析占位标签页
        self.hotspot_tab = QWidget()
        layout = QVBoxLayout(self.hotspot_tab)
        layout.addWidget(QLabel("热点分析功能正在加载中..."))
        self.tab_components['hotspot'] = self.hotspot_tab

        # 情绪报告占位标签页
        self.sentiment_report_tab = QWidget()
        layout = QVBoxLayout(self.sentiment_report_tab)
        layout.addWidget(QLabel("情绪报告功能正在加载中..."))
        self.tab_components['sentiment_report'] = self.sentiment_report_tab

    def _add_tabs_to_widget(self):
        """添加标签页到Tab控件"""
        # 技术分析
        self.tab_widget.addTab(self.technical_tab, "📊 技术分析")

        # 形态识别
        self.tab_widget.addTab(self.pattern_tab, "📈 形态识别")

        # 趋势分析
        self.tab_widget.addTab(self.trend_tab, "📉 趋势分析")

        # 波浪分析
        self.tab_widget.addTab(self.wave_tab, "🌊 波浪分析")

        # 情绪分析
        self.tab_widget.addTab(self.sentiment_tab, "💭 情绪分析")

        # 板块资金流
        self.tab_widget.addTab(self.sector_flow_tab, "💰 板块资金")

        # 热点分析
        self.tab_widget.addTab(self.hotspot_tab, "🔥 热点分析")

        # 情绪报告
        self.tab_widget.addTab(self.sentiment_report_tab, "📊 情绪报告")

        # K线技术分析 - 新增
        if hasattr(self, 'kline_technical_tab') and self.kline_technical_tab:
            self.tab_widget.addTab(self.kline_technical_tab, "📈 K线技术")

    def _connect_tab_signals(self):
        """连接标签页信号 - 修复版"""
        try:
            # 连接技术分析信号
            if hasattr(self.technical_tab, 'analysis_completed'):
                self.technical_tab.analysis_completed.connect(
                    self.analysis_completed)
            if hasattr(self.technical_tab, 'error_occurred'):
                self.technical_tab.error_occurred.connect(self.error_occurred)

            # 连接形态分析信号 - 双向连接
            if hasattr(self.pattern_tab, 'analysis_completed'):
                self.pattern_tab.analysis_completed.connect(
                    self.analysis_completed)
            if hasattr(self.pattern_tab, 'error_occurred'):
                self.pattern_tab.error_occurred.connect(self.error_occurred)
            if hasattr(self.pattern_tab, 'pattern_selected'):
                self.pattern_tab.pattern_selected.connect(
                    self.pattern_selected)

            # 【修复】设置pattern_tab的parent_widget并建立反向连接
            if hasattr(self.pattern_tab, 'set_parent_widget'):
                self.pattern_tab.set_parent_widget(self)
                self.log_manager.info("✅ 已设置pattern_tab的parent_widget")
            elif hasattr(self.pattern_tab, 'parent_widget'):
                self.pattern_tab.parent_widget = self
                # 手动连接信号
                if hasattr(self.pattern_tab, '_connect_parent_signals'):
                    self.pattern_tab._connect_parent_signals()
                self.log_manager.info("✅ 已设置pattern_tab的parent_widget（手动方式）")

        except Exception as e:
            self.log_manager.error(f"连接标签页信号失败: {e}")

    def setup_shortcuts(self):
        """设置快捷键"""
        # 技术分析快捷键
        calc_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        calc_shortcut.activated.connect(self._trigger_current_tab_analysis)

        # 清除快捷键
        clear_shortcut = QShortcut(QKeySequence("Ctrl+Delete"), self)
        clear_shortcut.activated.connect(self._clear_current_tab_data)

        # 帮助快捷键
        help_shortcut = QShortcut(QKeySequence("F1"), self)
        help_shortcut.activated.connect(self.show_help)

    def _trigger_current_tab_analysis(self):
        """触发当前标签页的分析"""
        current_index = self.tab_widget.currentIndex()
        current_widget = self.tab_widget.widget(current_index)

        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def _clear_current_tab_data(self):
        """清除当前标签页的数据"""
        current_index = self.tab_widget.currentIndex()
        current_widget = self.tab_widget.widget(current_index)

        if hasattr(current_widget, 'clear_data'):
            current_widget.clear_data()

    def show_help(self):
        """显示帮助信息"""
        help_text = """
        分析控件帮助信息：
        
        📊 技术分析：
        - 计算各种技术指标（MA、MACD、KDJ、RSI等）
        - 快捷键：Ctrl+Enter 计算指标，Ctrl+Delete 清除指标
        
        📈 形态识别：
        - 自动识别股票价格形态
        - 支持多种经典技术分析形态
        
        📉 趋势分析：
        - 分析价格趋势和趋势强度
        - 识别趋势转折点
        
        🌊 波浪分析：
        - 艾略特波浪理论分析
        - 江恩理论分析
        
        💭 情绪分析：
        - 市场情绪指标分析
        - 投资者情绪监控
        
        快捷键：
        - F1：显示帮助
        - Ctrl+Enter：执行分析
        - Ctrl+Delete：清除数据
        """

        QMessageBox.information(self, "帮助", help_text)

    def on_tab_changed(self, index):
        """标签页切换事件 - 优化版本，避免阻塞UI"""
        try:
            # 取消之前的更新请求，避免重复处理
            if hasattr(self, 'update_throttler'):
                self.update_throttler.cancel_all_updates()

            # 使用节流器处理标签页切换，延迟执行避免频繁切换
            if hasattr(self, 'update_throttler'):
                self.update_throttler.request_update(
                    'tab_changed',
                    self._do_tab_changed,
                    index
                )
            else:
                # 如果没有节流器，直接处理但不立即刷新数据
                self._do_tab_changed_without_refresh(index)

        except Exception as e:
            self.log_manager.error(f"Tab切换处理失败: {e}")

    def _do_tab_changed_without_refresh(self, index):
        """处理标签页切换但不立即刷新数据"""
        try:
            if index < 0 or index >= self.tab_widget.count():
                return

            current_tab = self.tab_widget.widget(index)
            tab_name = self.tab_widget.tabText(index)

            self.log_manager.debug(f"切换到标签页: {tab_name}")

            # 只设置数据，不立即刷新（避免阻塞）
            if (self.current_kdata is not None and
                hasattr(current_tab, 'set_kdata') and
                    hasattr(current_tab, 'current_kdata')):

                # 检查是否需要更新数据
                if not hasattr(current_tab, 'current_kdata') or current_tab.current_kdata is None:
                    # 只有在标签页没有数据时才设置
                    current_tab.set_kdata(self.current_kdata)
                    self.log_manager.debug(f"为 {tab_name} 设置K线数据")

        except Exception as e:
            self.log_manager.error(f"处理标签页切换失败: {str(e)}")

    def _do_tab_changed(self, index):
        """实际处理标签页切换 - 延迟刷新版本"""
        try:
            if index < 0 or index >= self.tab_widget.count():
                return

            current_tab = self.tab_widget.widget(index)
            tab_name = self.tab_widget.tabText(index)

            self.log_manager.debug(f"切换到标签页: {tab_name}")

            # 检查标签页是否需要数据
            if (self.current_kdata is not None and
                    hasattr(current_tab, 'set_kdata')):

                # 检查数据是否已经设置
                data_needs_update = True
                if hasattr(current_tab, 'current_kdata') and current_tab.current_kdata is not None:
                    # 如果标签页已有数据，检查是否为同一份数据
                    if hasattr(current_tab, 'data_hash') and hasattr(self, '_current_data_hash'):
                        data_needs_update = current_tab.data_hash != self._current_data_hash

                if data_needs_update:
                    # 设置数据，let BaseAnalysisTab handle async refresh
                    current_tab.set_kdata(self.current_kdata)
                    self.log_manager.debug(f"为 {tab_name} 更新K线数据")
                else:
                    self.log_manager.debug(f"{tab_name} 数据已是最新，跳过更新")

            # 如果标签页支持延迟刷新且需要刷新
            elif (hasattr(current_tab, 'refresh') and
                  hasattr(current_tab, 'needs_refresh') and
                  getattr(current_tab, 'needs_refresh', False)):

                # 使用更长的延迟来避免频繁切换时的重复计算
                if hasattr(self, 'update_throttler'):
                    self.update_throttler.request_update(
                        f'refresh_current_tab_{tab_name}',
                        current_tab.refresh,
                        delay_ms=300  # 增加延迟到300ms
                    )

        except Exception as e:
            self.log_manager.error(f"处理标签页切换失败: {str(e)}")

    def set_kdata(self, kdata):
        """设置K线数据 - 使用防抖机制

        Args:
            kdata: K线数据
        """
        try:
            # 计算数据哈希用于变化检测
            import hashlib

            if isinstance(kdata, pd.DataFrame) and not kdata.empty:
                data_str = f"{len(kdata)}_{kdata.iloc[-1].to_string() if len(kdata) > 0 else ''}"
                self._current_data_hash = hashlib.md5(data_str.encode()).hexdigest()
            else:
                self._current_data_hash = "empty"

            # 使用更新节流器来控制K线数据更新频率
            if hasattr(self, 'update_throttler'):
                self.update_throttler.request_update(
                    'set_kdata',
                    self._do_set_kdata,
                    kdata
                )
            else:
                self._do_set_kdata(kdata)

        except Exception as e:
            self.log_manager.error(f"设置K线数据失败: {e}")

    def _do_set_kdata(self, kdata):
        """实际执行K线数据设置"""
        try:
            if kdata is None or kdata.empty:
                self.log_manager.warning("传入的K线数据为空")
                return

            # 预处理数据
            processed_kdata = self._kdata_preprocess(kdata, "设置K线数据")
            if processed_kdata is None or processed_kdata.empty:
                self.log_manager.warning("K线数据预处理后为空")
                return

            self.current_kdata = processed_kdata

            # 通知所有标签页更新数据（异步方式）
            for tab_name, tab_component in self.tab_components.items():
                if hasattr(tab_component, 'set_kdata'):
                    try:
                        tab_component.set_kdata(processed_kdata)
                    except Exception as e:
                        self.log_manager.warning(
                            f"标签页 {tab_name} 设置K线数据失败: {str(e)}")

            self.log_manager.info(f"K线数据设置完成，共 {len(processed_kdata)} 条记录")

        except Exception as e:
            self.log_manager.error(f"设置K线数据失败: {str(e)}")
            self.error_occurred.emit(f"设置K线数据失败: {str(e)}")

    def _kdata_preprocess(self, kdata, context="分析"):
        """K线数据预处理 - 为标签页组件提供的接口"""
        try:
            if kdata is None:
                return None

            # 基本数据验证
            if hasattr(kdata, 'empty') and kdata.empty:
                return None

            # 确保必要的列存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if hasattr(kdata, 'columns'):
                missing_columns = [
                    col for col in required_columns if col not in kdata.columns]
                if missing_columns:
                    self.log_manager.warning(
                        f"{context}数据缺少必要列: {missing_columns}")

            return kdata

        except Exception as e:
            self.log_manager.error(f"K线数据预处理失败: {e}")
            return None

    def refresh_current_tab(self):
        """刷新当前标签页 - 优化版本"""
        try:
            current_tab = self.tab_widget.currentWidget()
            if current_tab and hasattr(current_tab, 'refresh'):
                tab_name = self.tab_widget.tabText(
                    self.tab_widget.currentIndex())

                # 使用节流器控制刷新频率
                self.update_throttler.request_update(
                    f'refresh_current_{tab_name}',
                    current_tab.refresh
                )

        except Exception as e:
            self.log_manager.error(f"刷新当前标签页失败: {str(e)}")

    def batch_update_indicators(self, indicators: List[str], delay_ms: int = 300):
        """批量更新指标 - 避免频繁的单个更新

        Args:
            indicators: 指标列表
            delay_ms: 延迟时间
        """
        # 取消之前的指标更新
        for indicator in indicators:
            self.update_throttler.cancel_update(
                f'update_indicator_{indicator}')

        # 批量更新
        self.update_throttler.request_update(
            'batch_update_indicators',
            self._do_batch_update_indicators,
            indicators
        )

    def _do_batch_update_indicators(self, indicators: List[str]):
        """实际执行批量指标更新"""
        try:
            if not self.current_kdata or self.current_kdata.empty:
                return

            self.log_manager.info(f"批量更新指标: {indicators}")

            # 并行计算所有指标
            with ThreadPoolExecutor(max_workers=min(len(indicators), os.cpu_count() * 2)) as executor:
                futures = []
                for indicator in indicators:
                    future = executor.submit(
                        self._calculate_single_indicator, indicator)
                    futures.append((indicator, future))

                # 收集结果
                results = {}
                for indicator, future in futures:
                    try:
                        result = future.result(timeout=10)  # 10秒超时
                        if result is not None:
                            results[indicator] = result
                    except Exception as e:
                        self.log_manager.warning(
                            f"计算指标 {indicator} 失败: {str(e)}")

                # 批量更新UI
                if results:
                    self._batch_update_ui(results)

        except Exception as e:
            self.log_manager.error(f"批量更新指标失败: {str(e)}")

    def _calculate_single_indicator(self, indicator: str):
        """计算单个指标"""
        try:
            # 这里应该调用实际的指标计算逻辑
            # 暂时返回None作为占位符
            return None
        except Exception as e:
            self.log_manager.error(f"计算指标 {indicator} 失败: {str(e)}")
            return None

    def _batch_update_ui(self, indicator_results: Dict[str, Any]):
        """批量更新UI"""
        try:
            # 批量更新当前标签页的指标显示
            current_tab = self.tab_widget.currentWidget()
            if hasattr(current_tab, 'batch_update_indicators'):
                current_tab.batch_update_indicators(indicator_results)
            elif hasattr(current_tab, 'update_indicators'):
                for indicator, result in indicator_results.items():
                    current_tab.update_indicators(indicator, result)

        except Exception as e:
            self.log_manager.error(f"批量更新UI失败: {str(e)}")

    def get_update_stats(self) -> Dict[str, Any]:
        """获取更新统计信息"""
        return {
            'pending_updates': len(self.update_throttler.pending_updates),
            'last_update_time': self.update_throttler.last_update_time,
            'min_interval_ms': self.update_throttler.min_interval_ms,
            'chart_update_pending': self._pending_chart_update is not None,
            'timer_active': self.chart_update_timer.isActive()
        }

    def optimize_update_frequency(self, min_interval_ms: int = 150):
        """优化更新频率设置

        Args:
            min_interval_ms: 最小更新间隔（毫秒）
        """
        self.update_throttler.min_interval_ms = min_interval_ms
        self.log_manager.info(f"更新频率已优化为最小 {min_interval_ms}ms 间隔")


# 保持向后兼容性的函数
def get_indicator_categories():
    """获取指标分类"""
    from core.indicator_service import get_indicator_categories as get_categories
    return get_categories()


# 为了完全向后兼容，添加原有的一些重要方法
class AnalysisWidgetCompat:
    """向后兼容性扩展类"""

    def __init__(self, widget):
        self.widget = widget

    def create_technical_tab(self):
        """创建技术分析标签页 - 兼容原接口"""
        return self.widget.technical_tab

    def create_pattern_tab(self):
        """创建形态分析标签页 - 兼容原接口"""
        return self.widget.pattern_tab

    def create_trend_tab(self):
        """创建趋势分析标签页 - 兼容原接口"""
        return self.widget.trend_tab

    def create_wave_tab(self):
        """创建波浪分析标签页 - 兼容原接口"""
        return self.widget.wave_tab

    def create_sentiment_tab(self):
        """创建情绪分析标签页 - 兼容原接口"""
        return self.widget.sentiment_tab

    def create_sector_flow_tab(self):
        """创建板块资金流标签页 - 兼容原接口"""
        return self.widget.sector_flow_tab

    def create_hotspot_tab(self):
        """创建热点分析标签页 - 兼容原接口"""
        return self.widget.hotspot_tab

    def create_sentiment_report_tab(self):
        """创建情绪报告标签页 - 兼容原接口"""
        return self.widget.sentiment_report_tab


# 扩展AnalysisWidget类，添加向后兼容方法
def _add_compatibility_methods(cls):
    """为AnalysisWidget类添加向后兼容方法"""

    # 添加原有的标签页创建方法
    def create_technical_tab(self):
        return self.technical_tab

    def create_pattern_tab(self):
        return self.pattern_tab

    def create_trend_tab(self):
        return self.trend_tab

    def create_wave_tab(self):
        return self.wave_tab

    def create_sentiment_tab(self):
        return self.sentiment_tab

    def create_sector_flow_tab(self):
        return self.sector_flow_tab

    def create_hotspot_tab(self):
        return self.hotspot_tab

    def create_sentiment_report_tab(self):
        return self.sentiment_report_tab

    # 添加原有的分析方法
    def analyze_trend(self):
        """趋势分析 - 兼容原接口"""
        if hasattr(self.trend_tab, 'analyze_trend'):
            return self.trend_tab.analyze_trend()
        else:
            self.log_manager.warning("趋势分析功能暂未实现")

    def analyze_wave(self):
        """波浪分析 - 兼容原接口"""
        if hasattr(self.wave_tab, 'analyze_wave'):
            return self.wave_tab.analyze_wave()
        else:
            self.log_manager.warning("波浪分析功能暂未实现")

    def analyze_sentiment(self):
        """情绪分析 - 兼容原接口"""
        if hasattr(self.sentiment_tab, 'analyze_sentiment'):
            return self.sentiment_tab.analyze_sentiment()
        else:
            self.log_manager.warning("情绪分析功能暂未实现")

    def analyze_sector_flow(self):
        """板块资金流分析 - 兼容原接口"""
        if hasattr(self.sector_flow_tab, 'analyze_sector_flow'):
            return self.sector_flow_tab.analyze_sector_flow()
        else:
            self.log_manager.warning("板块资金流分析功能暂未实现")

    def analyze_hotspot(self):
        """热点分析 - 兼容原接口"""
        if hasattr(self.hotspot_tab, 'analyze_hotspot'):
            return self.hotspot_tab.analyze_hotspot()
        else:
            self.log_manager.warning("热点分析功能暂未实现")

    # 添加清除方法
    def clear_technical(self):
        """清除技术分析数据 - 兼容原接口"""
        if hasattr(self.technical_tab, 'clear_data'):
            self.technical_tab.clear_data()

    def clear_patterns(self):
        """清除形态分析数据 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'clear_data'):
            self.pattern_tab.clear_data()

    def clear_trend(self):
        """清除趋势分析数据 - 兼容原接口"""
        if hasattr(self.trend_tab, 'clear_data'):
            self.trend_tab.clear_data()

    def clear_wave(self):
        """清除波浪分析数据 - 兼容原接口"""
        if hasattr(self.wave_tab, 'clear_data'):
            self.wave_tab.clear_data()

    def clear_sentiment(self):
        """清除情绪分析数据 - 兼容原接口"""
        if hasattr(self.sentiment_tab, 'clear_data'):
            self.sentiment_tab.clear_data()

    def clear_sector_flow(self):
        """清除板块资金流数据 - 兼容原接口"""
        if hasattr(self.sector_flow_tab, 'clear_data'):
            self.sector_flow_tab.clear_data()

    def clear_hotspot(self):
        """清除热点分析数据 - 兼容原接口"""
        if hasattr(self.hotspot_tab, 'clear_data'):
            self.hotspot_tab.clear_data()

    # 添加原有的事件处理方法
    def on_pattern_selected(self, idx):
        """形态选择事件 - 兼容原接口"""
        self.pattern_selected.emit(idx)

    def _on_pattern_table_selection_changed(self):
        """形态表格选择变化 - 兼容原接口"""
        if hasattr(self.pattern_tab, '_on_pattern_table_selection_changed'):
            self.pattern_tab._on_pattern_table_selection_changed()

    def apply_pattern_filter(self):
        """应用形态过滤器 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'apply_pattern_filter'):
            self.pattern_tab.apply_pattern_filter()

    def refresh_current_tab(self):
        """刷新当前标签页 - 兼容原接口"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    # 添加原有的配置方法
    def show_pattern_config_dialog(self):
        """显示形态配置对话框 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'show_pattern_config_dialog'):
            self.pattern_tab.show_pattern_config_dialog()
        else:
            QMessageBox.information(self, "提示", "形态配置功能暂未实现")

    def show_pattern_statistics_dialog(self):
        """显示形态统计对话框 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'show_pattern_statistics_dialog'):
            self.pattern_tab.show_pattern_statistics_dialog()
        else:
            QMessageBox.information(self, "提示", "形态统计功能暂未实现")

    def auto_identify_patterns(self):
        """自动识别形态 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'auto_identify_patterns'):
            self.pattern_tab.auto_identify_patterns()
        else:
            self.log_manager.warning("自动形态识别功能暂未实现")

    def toggle_auto_refresh(self, state):
        """切换自动刷新 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'toggle_auto_refresh'):
            self.pattern_tab.toggle_auto_refresh(state)

    # 将这些方法添加到类中
    cls.create_technical_tab = create_technical_tab
    cls.create_pattern_tab = create_pattern_tab
    cls.create_trend_tab = create_trend_tab
    cls.create_wave_tab = create_wave_tab
    cls.create_sentiment_tab = create_sentiment_tab
    cls.create_sector_flow_tab = create_sector_flow_tab
    cls.create_hotspot_tab = create_hotspot_tab
    cls.create_sentiment_report_tab = create_sentiment_report_tab

    cls.analyze_trend = analyze_trend
    cls.analyze_wave = analyze_wave
    cls.analyze_sentiment = analyze_sentiment
    cls.analyze_sector_flow = analyze_sector_flow
    cls.analyze_hotspot = analyze_hotspot

    cls.clear_technical = clear_technical
    cls.clear_patterns = clear_patterns
    cls.clear_trend = clear_trend
    cls.clear_wave = clear_wave
    cls.clear_sentiment = clear_sentiment
    cls.clear_sector_flow = clear_sector_flow
    cls.clear_hotspot = clear_hotspot

    cls.on_pattern_selected = on_pattern_selected
    cls._on_pattern_table_selection_changed = _on_pattern_table_selection_changed
    cls.apply_pattern_filter = apply_pattern_filter
    cls.refresh_current_tab = refresh_current_tab

    cls.show_pattern_config_dialog = show_pattern_config_dialog
    cls.show_pattern_statistics_dialog = show_pattern_statistics_dialog
    cls.auto_identify_patterns = auto_identify_patterns
    cls.toggle_auto_refresh = toggle_auto_refresh

    return cls


# 应用向后兼容性扩展
AnalysisWidget = _add_compatibility_methods(AnalysisWidget)
