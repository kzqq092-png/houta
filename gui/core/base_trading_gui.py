"""
基础交易GUI类

定义交易系统GUI的基础类和信号
"""

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSignal
from utils.theme import Theme
from typing import Dict, Any


class BaseTradingGUI(QMainWindow):
    """交易系统基础GUI类"""

    # 定义信号
    theme_changed = pyqtSignal(Theme)
    data_updated = pyqtSignal(dict)
    analysis_completed = pyqtSignal(dict)
    performance_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        """初始化基础GUI"""
        super().__init__()

        # 初始化标志
        self._is_initializing = True
        self.screener_guide_shown = False

        # 缓存相关属性
        self.stock_list_cache = []
        self.data_cache = {}
        self.chart_cache = {}

        # 当前状态属性
        self.current_period = 'D'
        self.current_chart_type = 'candlestick'
        self.current_stock = None
        self.current_strategy = None
        self.current_time_range = -365
        self.current_analysis_type = 'technical'

        # 收藏列表
        self.favorites = set()

        # 市场和行业映射
        self.market_mapping = {}
        self.industry_mapping = {}

    def connect_signals(self):
        """连接所有信号和槽"""
        try:
            # 连接主题变更信号
            self.theme_changed.connect(self.apply_theme)

            # 连接数据更新信号
            self.data_updated.connect(self.handle_data_update)

            # 连接分析完成信号
            self.analysis_completed.connect(self.handle_analysis_complete)

            # 连接错误信号
            self.error_occurred.connect(self.handle_error)

            if hasattr(self, 'log_manager'):
                self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            if hasattr(self, 'log_manager'):
                self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def handle_data_update(self, data: Dict[str, Any]):
        """处理数据更新信号"""
        try:
            # 更新数据缓存
            self.data_cache.update(data)

            # 更新UI显示
            self.update_ui()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"处理数据更新失败: {str(e)}")

    def handle_analysis_complete(self, results: Dict[str, Any]):
        """处理分析完成信号"""
        try:
            # 更新分析结果
            self.update_metrics(results)

            # 更新图表
            self.update_chart()

        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"处理分析完成失败: {str(e)}")

    def handle_error(self, error_msg: str):
        """处理错误信号"""
        try:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"GUI错误: {error_msg}")
            # 子类可以重写此方法来显示错误消息
        except Exception as e:
            print(f"处理错误失败: {str(e)}")

    def apply_theme(self):
        """应用主题 - 子类实现"""
        pass

    def update_ui(self):
        """更新UI - 子类实现"""
        pass

    def update_metrics(self, metrics: Dict[str, Any]):
        """更新指标 - 子类实现"""
        pass

    def update_chart(self):
        """更新图表 - 子类实现"""
        pass
