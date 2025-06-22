"""
重构后的分析控件模块 - 使用模块化标签页组件
"""
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
import importlib
import traceback
import os
import time
from concurrent.futures import *
import numba
import json
from core.logger import LogManager, LogLevel

# 更新：优先使用新的指标服务架构
try:
    from core.services import get_indicator_ui_adapter
    _use_new_architecture = True
except ImportError:
    get_indicator_ui_adapter = None
    _use_new_architecture = False
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from hikyuu.indicator import *
from hikyuu import sm
from hikyuu import Query
# 移除旧的indicators_algo导入，使用统一指标管理器
from utils.cache import Cache
import requests
from bs4 import BeautifulSoup
from analysis.pattern_recognition import PatternRecognizer
from core.data_manager import data_manager
from features.advanced_indicators import create_pattern_recognition_features, ALL_PATTERN_TYPES
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from data.data_loader import generate_quality_report
from core.risk_exporter import RiskExporter
from PyQt5.QtWidgets import QWidget
from utils.data_preprocessing import kdata_preprocess as _kdata_preprocess

# 导入新的模块化标签页组件
from .analysis_tabs import (
    TechnicalAnalysisTab,
    PatternAnalysisTab,
    TrendAnalysisTab,
    SectorFlowTab,
    WaveAnalysisTab,
    SentimentAnalysisTab,
    HotspotAnalysisTab,
    SentimentReportTab
)

# 新增导入形态管理器
from analysis.pattern_manager import PatternManager

# 使用统一的管理器工厂
from utils.manager_factory import get_config_manager, get_log_manager

# 使用新的指标服务架构
from core.services.indicator_ui_adapter import IndicatorUIAdapter


class AnalysisWidget(QWidget):
    """重构后的分析控件类 - 使用模块化标签页组件"""

    # 定义信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)  # 新增错误信号
    pattern_selected = pyqtSignal(int)  # 新增信号，用于传递信号索引

    data_cache = Cache(cache_dir=".cache/data", default_ttl=30*60)

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化分析控件

        Args:
            config_manager: Optional ConfigManager instance to use
        """

        super().__init__()

        # 使用统一的管理器工厂
        self.config_manager = config_manager or get_config_manager()
        self.log_manager = get_log_manager()

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

        # 使用新的指标服务架构
        self.indicator_adapter = IndicatorUIAdapter()
        self.log_manager.info("AnalysisWidget: 使用新的指标服务架构")

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
        QTimer.singleShot(100, lambda: self._init_pattern_filters() if hasattr(self, '_init_pattern_filters') else None)

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
            loading_icon.setStyleSheet("QLabel { color: white; font-size: 48px; }")
            loading_icon.setAlignment(Qt.AlignCenter)
            overlay_layout.addWidget(loading_icon)

            # 加载文字
            self.loading_label = QLabel(message)
            self.loading_label.setStyleSheet("QLabel { color: white; font-size: 16px; font-weight: bold; }")
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

            # 情绪分析标签页
            self.sentiment_tab = SentimentAnalysisTab(self.config_manager)
            self.sentiment_tab.parent_widget = self
            self.tab_components['sentiment'] = self.sentiment_tab

            # 板块资金流标签页
            self.sector_flow_tab = SectorFlowTab(self.config_manager)
            self.sector_flow_tab.parent_widget = self
            self.tab_components['sector_flow'] = self.sector_flow_tab

            # 热点分析标签页
            self.hotspot_tab = HotspotAnalysisTab(self.config_manager)
            self.hotspot_tab.parent_widget = self
            self.tab_components['hotspot'] = self.hotspot_tab

            # 情绪报告标签页
            self.sentiment_report_tab = SentimentReportTab(self.config_manager)
            self.sentiment_report_tab.parent_widget = self
            self.tab_components['sentiment_report'] = self.sentiment_report_tab

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

    def _connect_tab_signals(self):
        """连接标签页信号"""
        try:
            # 连接技术分析信号
            if hasattr(self.technical_tab, 'analysis_completed'):
                self.technical_tab.analysis_completed.connect(self.analysis_completed)
            if hasattr(self.technical_tab, 'error_occurred'):
                self.technical_tab.error_occurred.connect(self.error_occurred)

            # 连接形态分析信号
            if hasattr(self.pattern_tab, 'analysis_completed'):
                self.pattern_tab.analysis_completed.connect(self.analysis_completed)
            if hasattr(self.pattern_tab, 'error_occurred'):
                self.pattern_tab.error_occurred.connect(self.error_occurred)
            if hasattr(self.pattern_tab, 'pattern_selected'):
                self.pattern_tab.pattern_selected.connect(self.pattern_selected)

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
        """Tab切换事件处理"""
        try:
            current_widget = self.tab_widget.widget(index)
            tab_name = self.tab_widget.tabText(index)

            self.log_manager.info(f"切换到标签页: {tab_name}")

            # 如果有数据，自动刷新当前标签页
            if self.current_kdata is not None and hasattr(current_widget, 'set_kdata'):
                current_widget.set_kdata(self.current_kdata)

        except Exception as e:
            self.log_manager.error(f"Tab切换处理失败: {e}")

    def set_kdata(self, kdata):
        """设置K线数据并同步到所有标签页"""
        try:
            self.current_kdata = kdata

            # 同步数据到所有标签页组件
            for tab_name, tab_component in self.tab_components.items():
                if hasattr(tab_component, 'set_kdata'):
                    tab_component.set_kdata(kdata)

            self.log_manager.info("K线数据已同步到所有标签页")

        except Exception as e:
            self.log_manager.error(f"设置K线数据失败: {e}")
            self.error_occurred.emit(f"设置K线数据失败: {str(e)}")

    def refresh_all_tabs(self):
        """刷新所有标签页"""
        try:
            for tab_name, tab_component in self.tab_components.items():
                if hasattr(tab_component, 'refresh_data'):
                    tab_component.refresh_data()

            self.log_manager.info("所有标签页已刷新")

        except Exception as e:
            self.log_manager.error(f"刷新标签页失败: {e}")

    def refresh(self) -> None:
        """刷新当前标签页"""
        current_index = self.tab_widget.currentIndex()
        current_widget = self.tab_widget.widget(current_index)

        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def run_button_analysis_async(self, button, analysis_func, *args, **kwargs):
        """异步运行分析函数 - 为标签页组件提供的接口"""
        try:
            # 显示加载状态
            self.show_loading("正在分析...")

            # 使用线程池执行任务
            from concurrent.futures import ThreadPoolExecutor

            def task():
                try:
                    return analysis_func(*args, **kwargs)
                except Exception as e:
                    return {"error": str(e)}

            def on_done(future):
                try:
                    result = future.result()
                    self.hide_loading()
                    if isinstance(result, dict) and "error" in result:
                        self.error_occurred.emit(result["error"])
                    else:
                        self.analysis_completed.emit(result if isinstance(result, dict) else {"result": result})
                except Exception as e:
                    self.hide_loading()
                    self.error_occurred.emit(f"分析执行失败: {str(e)}")

            # 在线程池中执行任务
            if not hasattr(self, '_executor'):
                self._executor = ThreadPoolExecutor(max_workers=2)

            future = self._executor.submit(task)
            future.add_done_callback(on_done)

            return future

        except Exception as e:
            self.hide_loading()
            self.log_manager.error(f"异步分析执行失败: {e}")
            self.error_occurred.emit(f"异步分析执行失败: {str(e)}")

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
                missing_columns = [col for col in required_columns if col not in kdata.columns]
                if missing_columns:
                    self.log_manager.warning(f"{context}数据缺少必要列: {missing_columns}")

            return kdata

        except Exception as e:
            self.log_manager.error(f"K线数据预处理失败: {e}")
            return None

    def _update_pattern_filter_options(self):
        """更新形态过滤器选项 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'pattern_type_combo'):
            try:
                # 添加形态类型选项
                for pattern_type in ALL_PATTERN_TYPES[:10]:  # 限制显示数量
                    self.pattern_tab.pattern_type_combo.addItem(pattern_type)
            except Exception as e:
                self.log_manager.warning(f"更新形态过滤器选项失败: {e}")

    # 兼容性方法 - 保持原有接口
    def refresh_technical_data(self):
        """刷新技术分析数据 - 兼容原接口"""
        if hasattr(self.technical_tab, 'refresh_data'):
            self.technical_tab.refresh_data()

    def refresh_pattern_data(self):
        """刷新形态分析数据 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'refresh_data'):
            self.pattern_tab.refresh_data()

    def identify_patterns(self):
        """识别形态 - 兼容原接口"""
        if hasattr(self.pattern_tab, 'identify_patterns'):
            self.pattern_tab.identify_patterns()

    def calculate_indicators(self):
        """计算技术指标 - 兼容原接口"""
        if hasattr(self.technical_tab, 'calculate_indicators'):
            self.technical_tab.calculate_indicators()

    def _connect_chart_widget_signals(self):
        """连接图表组件信号 - 兼容原接口"""
        try:
            if hasattr(self, 'chart_widget') and self.chart_widget:
                # 连接图表数据更新信号到分析组件
                if hasattr(self.chart_widget, 'data_updated'):
                    self.chart_widget.data_updated.connect(self.set_kdata)

                # 连接其他可能的图表信号
                if hasattr(self.chart_widget, 'stock_changed'):
                    self.chart_widget.stock_changed.connect(self._on_stock_changed)

                self.log_manager.info("图表组件信号连接成功")
            else:
                self.log_manager.warning("图表组件未设置，跳过信号连接")

        except Exception as e:
            self.log_manager.error(f"连接图表组件信号失败: {e}")

    def _on_stock_changed(self, stock_code):
        """股票切换事件处理 - 兼容原接口"""
        try:
            self.log_manager.info(f"股票切换到: {stock_code}")
            # 这里可以添加股票切换时的处理逻辑

        except Exception as e:
            self.log_manager.error(f"处理股票切换事件失败: {e}")


# 保持向后兼容性的函数
def get_indicator_categories():
    """获取指标分类（全局函数）"""
    try:
        # 优先使用新的指标服务架构
        if _use_new_architecture and get_indicator_ui_adapter:
            adapter = get_indicator_ui_adapter()
            return adapter.get_indicators_by_category(use_chinese=True)
        else:
            # 备用方案：返回默认分类
            return {
                "趋势指标": ["MA", "EMA", "SMA"],
                "动量指标": ["RSI", "MACD", "KDJ"],
                "波动率指标": ["BOLL", "ATR"],
                "成交量指标": ["OBV", "VOL"]
            }
    except Exception as e:
        # 最终备用方案
        return {
            "重叠研究": ["SMA", "EMA", "WMA", "BBANDS", "SAR"],
            "动量指标": ["MACD", "RSI", "STOCH", "WILLR", "CCI"],
            "成交量": ["OBV", "AD", "ADOSC"],
            "波动率": ["ATR", "NATR"],
            "其他": ["DMI", "BIAS", "PSY"]
        }


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
