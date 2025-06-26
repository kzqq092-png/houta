"""
图表控件模块 - 基于Mixin模式的重构版本

该模块使用Mixin模式将原有的长文件拆分为多个功能模块，
提高代码的可维护性和可扩展性。
"""

import traceback
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QTimer, QMutex, QMutexLocker, Qt
from PyQt5.QtWidgets import QWidget

# 导入所有Mixin模块
from .chart_mixins import (
    BaseMixin, UIMixin, RenderingMixin, IndicatorMixin, 
    CrosshairMixin, InteractionMixin, ZoomMixin, 
    SignalMixin, ExportMixin, UtilityMixin
)

# 导入依赖
from utils.config_manager import ConfigManager
from utils.theme import get_theme_manager
from core.logger import LogManager
from utils.cache import Cache
from gui.widgets.async_data_processor import AsyncDataProcessor
from gui.widgets.chart_renderer import ChartRenderer


class ChartWidget(QWidget, BaseMixin, UIMixin, RenderingMixin, IndicatorMixin,
                  CrosshairMixin, InteractionMixin, ZoomMixin, SignalMixin,
                  ExportMixin, UtilityMixin):
    """图表控件类 - 使用Mixin模式拆分功能模块"""

    # 定义信号
    period_changed = pyqtSignal(str)  # 周期变更信号
    indicator_changed = pyqtSignal(str)  # 指标变更信号
    chart_updated = pyqtSignal(dict)  # 图表更新信号
    error_occurred = pyqtSignal(str)  # 错误信号
    zoom_changed = pyqtSignal(float)  # 缩放变更信号
    request_indicator_dialog = pyqtSignal()
    request_stat_dialog = pyqtSignal(tuple)  # (start_idx, end_idx)
    pattern_selected = pyqtSignal(int)  # 新增：主图高亮信号，参数为K线索引

    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None, 
                 theme_manager=None, log_manager=None, data_manager=None):
        """初始化图表控件

        Args:
            parent: Parent widget
            config_manager: Optional ConfigManager instance to use
            theme_manager: Optional theme manager to use
            log_manager: Optional log manager to use
            data_manager: Optional data manager to use
        """
        try:
            # 首先初始化QWidget
            QWidget.__init__(self, parent)
            
            # 初始化基础属性（在调用Mixin之前）
            self.setAcceptDrops(True)  # 确保控件能接收拖拽

            # 初始化管理器（必须在Mixin初始化之前）
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = theme_manager or get_theme_manager(self.config_manager)
            self.log_manager = log_manager or LogManager()
            self.data_manager = data_manager

            # 初始化基础变量
            self.current_kdata = None
            self.current_signals = []
            self.current_period = 'D'
            self.current_indicator = None
            self._zoom_level = 1.0
            self._zoom_history = []
            self._max_zoom = 5.0
            self._min_zoom = 0.2
            self.crosshair_enabled = True  # 默认开启十字线
            self.active_indicators = []  # 当前激活的指标列表，初始化为空，仅通过外部信号设置

            # 初始化缓存管理器
            self.cache_manager = Cache()  # 图表最多缓存100个

            # 启用双缓冲
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAutoFillBackground(True)

            # 初始化数据更新锁
            self._update_lock = QMutex()
            self._render_lock = QMutex()

            # 新增：合并指标栏UI引用
            self.indicator_bar = None  # 合并后的指标栏
            self.volume_bar = None     # 成交量栏
            self.macd_bar = None      # MACD栏

            # 初始化更新队列
            self._update_queue = []

            # 初始化所有Mixin（在基础属性初始化之后）
            BaseMixin.__init__(self)
            UIMixin.__init__(self)
            RenderingMixin.__init__(self)
            IndicatorMixin.__init__(self)
            CrosshairMixin.__init__(self)
            InteractionMixin.__init__(self)
            ZoomMixin.__init__(self)
            SignalMixin.__init__(self)
            ExportMixin.__init__(self)
            UtilityMixin.__init__(self)

            # 初始化UI
            self.init_ui()

            # 创建更新定时器
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._process_update_queue)
            self._update_timer.start(100)  # 100ms 间隔

            # 添加渲染优化
            self._optimize_rendering()

            # 初始化异步数据处理器
            self.data_processor = AsyncDataProcessor()
            self.data_processor.calculation_progress.connect(
                self._on_calculation_progress)
            self.data_processor.calculation_complete.connect(
                self._on_calculation_complete)
            self.data_processor.calculation_error.connect(
                self._on_calculation_error)

            # 初始化渲染器
            self.renderer = ChartRenderer()
            self.renderer.render_progress.connect(self._on_render_progress)
            self.renderer.render_complete.connect(self._on_render_complete)
            self.renderer.render_error.connect(self._on_render_error)

            # 应用初始主题
            self._apply_initial_theme()

            self.log_manager.info("图表控件初始化完成")

            self.highlighted_indices = set()  # 高亮K线索引
            self._replay_timer = None         # 回放定时器
            self._replay_index = None         # 回放当前索引

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            # 安全地记录错误
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            else:
                print(f"ChartWidget初始化错误: {error_msg}")
                print(traceback.format_exc())
            
            # 安全地发射信号
            if hasattr(self, 'error_occurred'):
                self.error_occurred.emit(error_msg)

    def _process_update_queue(self):
        """处理更新队列中的任务"""
        try:
            if not self._update_queue:
                return

            with QMutexLocker(self._update_lock):
                while self._update_queue:
                    update_func, args = self._update_queue.pop(0)
                    try:
                        update_func(*args)
                    except Exception as e:
                        if hasattr(self, 'log_manager') and self.log_manager:
                            self.log_manager.error(f"更新任务执行失败: {str(e)}")

        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"处理更新队列失败: {str(e)}")

    def queue_update(self, update_func, *args):
        """将更新任务加入队列

        Args:
            update_func: 更新函数
            *args: 函数参数
        """
        with QMutexLocker(self._update_lock):
            self._update_queue.append((update_func, args))

    def update_loading_progress(self, value: int, message: str = None):
        """更新加载进度，保证数值安全"""
        value = max(0, min(100, int(value)))
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.setValue(value)
            if message:
                self.loading_dialog.setLabelText(message)

    def set_loading_progress_error(self, message="渲染失败"):
        """设置加载进度错误"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.setLabelText(message)

    def close_loading_dialog(self):
        """关闭加载进度对话框"""
        if hasattr(self, 'loading_dialog'):
            self.loading_dialog.close()

    def refresh(self) -> None:
        """刷新图表数据"""
        try:
            if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                # 重新渲染当前数据
                data = {'kdata': self.current_kdata}
                if hasattr(self, 'current_signals'):
                    data['signals'] = self.current_signals
                self.update_chart(data)
            else:
                if hasattr(self, 'log_manager') and self.log_manager:
                    self.log_manager.warning("没有数据可刷新")
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"刷新图表失败: {str(e)}")
                self.error_occurred.emit(f"刷新图表失败: {str(e)}")

    def update(self) -> None:
        """更新图表显示"""
        try:
            super().update()
            if hasattr(self, 'canvas'):
                self.canvas.draw_idle()
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"更新显示失败: {str(e)}")

    def reload(self) -> None:
        """重新加载图表"""
        try:
            self.clear_chart()
            self.refresh()
        except Exception as e:
            if hasattr(self, 'log_manager') and self.log_manager:
                self.log_manager.error(f"重新加载失败: {str(e)}")
                self.error_occurred.emit(f"重新加载失败: {str(e)}")

    def _on_render_progress(self, progress: int, message: str):
        """处理渲染进度"""
        self.update_loading_progress(progress, message)

    def _on_render_complete(self):
        """处理渲染完成"""
        self.close_loading_dialog()

    def _on_render_error(self, error: str):
        """处理渲染错误"""
        self.error_occurred.emit(error)
        self.close_loading_dialog()