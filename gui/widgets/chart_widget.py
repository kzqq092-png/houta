"""
图表控件模块 - 基于Mixin模式的重构版本

该模块使用Mixin模式将原有的长文件拆分为多个功能模块，
提高代码的可维护性和可扩展性。
"""

import traceback
from typing import Optional, List, Dict, Any
from PyQt5.QtCore import pyqtSignal, QTimer, QMutex, QMutexLocker, Qt
from PyQt5.QtWidgets import QWidget

# 导入所有Mixin模块
from .chart_mixins import (
    BaseMixin, UIMixin, RenderingMixin, IndicatorMixin,
    CrosshairMixin, InteractionMixin, ZoomMixin,
    SignalMixin, ExportMixin, UtilityMixin,
    # 直接从chart_mixins导入ChartRenderer相关组件
    ChartRenderer, RenderPriority
)

# 导入依赖
from utils.config_manager import ConfigManager
from utils.theme import get_theme_manager
from core.logger import LogManager
from utils.cache import Cache
from gui.widgets.async_data_processor import AsyncDataProcessor

# 导入新的全局加载器
from optimization.progressive_loading_manager import load_chart_progressive, get_progressive_loader

# 导入指标收集
from core.metrics.app_metrics_service import measure

import time
import pandas as pd
import numpy as np


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

    # 渐进式加载信号
    progressive_loading_progress = pyqtSignal(int, str)  # 进度, 阶段名称
    progressive_loading_complete = pyqtSignal()  # 加载完成

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
            self.theme_manager = theme_manager or get_theme_manager(
                self.config_manager)
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

            # 初始化渐进式加载（不再创建本地实例）
            self.is_progressive_loading_enabled = self.config_manager.get(
                'chart.progressive_loading.enabled', True)

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
            self.renderer.priority_render_complete.connect(
                self._on_priority_render_complete)

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
            self.loading_dialog.setStyleSheet("QProgressBar { color: red; }")

    def close_loading_dialog(self):
        """关闭加载对话框"""
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.close()

    @measure("chart.refresh")
    def refresh(self) -> None:
        """刷新图表"""
        try:
            self.log_manager.info("刷新图表")
            with QMutexLocker(self._render_lock):
                if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                    # 使用update_chart方法而不是直接调用renderer.render
                    self.update_chart({'kdata': self.current_kdata})
                else:
                    self.log_manager.error("刷新图表失败: K线数据不存在")
                    self.error_occurred.emit("刷新图表失败: K线数据不存在")
                    self.show_no_data("无数据")
        except Exception as e:
            self.log_manager.error(f"刷新图表失败: {str(e)}")
            self.error_occurred.emit(f"刷新图表失败: {str(e)}")
            # 确保错误情况下也显示错误提示
            self.show_no_data(f"刷新失败: {str(e)}")

    @measure("chart.update")
    def update(self) -> None:
        """更新图表"""
        try:
            super().update()  # 调用QWidget的update方法
        except Exception as e:
            self.log_manager.error(f"更新图表失败: {str(e)}")
            self.error_occurred.emit(f"更新图表失败: {str(e)}")

    @measure("chart.reload")
    def reload(self) -> None:
        """重新加载图表数据"""
        try:
            self.log_manager.info("重新加载图表数据")
            # 清除缓存
            self.cache_manager.clear()
            # 重新加载数据
            self.load_data(self.current_stock_code, self.current_period)
        except Exception as e:
            self.log_manager.error(f"重新加载图表数据失败: {str(e)}")
            self.error_occurred.emit(f"重新加载图表数据失败: {str(e)}")

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

    def set_kdata(self, kdata, indicators: List[Dict] = None, enable_progressive: bool = None):
        """设置K线数据并触发图表更新

        Args:
            kdata: K线数据
            indicators: 指标列表
            enable_progressive: 是否启用渐进式加载（覆盖全局配置）
        """
        with QMutexLocker(self.update_lock):
            if kdata is None or kdata.empty:
                self.log_manager.warning("set_kdata: kdata为空, 清空图表")
                self.clear_chart()
                return

            self.kdata = kdata
            self.indicators = indicators or []
            self._is_updating = True

            # 确定是否启用渐进式加载
            use_progressive = enable_progressive if enable_progressive is not None else self.is_progressive_loading_enabled

            if use_progressive:
                # 使用新的全局加载器，并明确定义加载阶段
                self.log_manager.info("使用全局渐进式加载器更新图表（带阶段配置）...")

                loading_stages = [
                    {'name': 'K线和主图', 'priority': 'CRITICAL'},
                    {'name': '成交量', 'priority': 'HIGH'},
                    {'name': '技术指标', 'priority': 'NORMAL'},
                ]

                load_chart_progressive(
                    self, self.kdata, self.indicators, stages=loading_stages)
            else:
                # 传统同步加载
                self.log_manager.info("使用同步方式更新图表...")
                self.update()

            self._is_updating = False

    def enable_progressive_loading(self, enabled: bool):
        """启用或禁用渐进式加载

        Args:
            enabled: 是否启用
        """
        self.is_progressive_loading_enabled = enabled
        if not enabled:
            # 如果禁用，取消当前的渐进式加载
            self.cancel_all_loading()

    @measure("chart.update_basic_kdata")
    def update_basic_kdata(self, kdata):
        """更新基础K线数据（第一阶段渐进式加载）

        Args:
            kdata: K线数据DataFrame
        """
        try:
            self.log_manager.info(f"开始更新基础K线数据: 类型={type(kdata)}")

            # 增强对kdata的验证
            if kdata is None:
                self.log_manager.warning("K线数据为空")
                self.show_no_data("无K线数据")
                return

            import pandas as pd
            if not isinstance(kdata, pd.DataFrame):
                self.log_manager.warning(f"K线数据格式错误: {type(kdata)}")
                self.show_no_data("K线数据格式错误")
                return

            self.log_manager.info(
                f"K线数据形状: {kdata.shape}, 列: {list(kdata.columns)}")

            if kdata.empty:
                self.log_manager.warning("K线数据为空DataFrame")
                self.show_no_data("无K线数据")
                return

            # 确保包含必要的列
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [
                col for col in required_columns if col not in kdata.columns]
            if missing_columns:
                self.log_manager.warning(f"K线数据缺少必要列: {missing_columns}")
                self.show_no_data(f"K线数据缺少必要列: {', '.join(missing_columns)}")
                return

            # 更新当前K线数据
            self.current_kdata = kdata
            self.log_manager.info(
                f"已设置current_kdata: {id(self.current_kdata)}")

            # 清除现有图表
            for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                ax.cla()

            self.log_manager.info("已清除图表")

            # 获取样式
            style = self._get_chart_style()
            self.log_manager.info(f"获取样式: {style}")

            # 绘制K线
            try:
                x = np.arange(len(kdata))
                self.log_manager.info(f"创建x轴: 长度={len(x)}")
                self.log_manager.info(
                    f"调用renderer.render_candlesticks: price_ax={self.price_ax}, kdata形状={kdata.shape}")
                self.renderer.render_candlesticks(
                    self.price_ax, kdata, style, x=x)
                self.log_manager.info("K线绘制完成")
            except Exception as e:
                self.log_manager.error(f"绘制K线失败: {str(e)}")
                raise

            # 设置基础显示范围
            if not kdata.empty:
                self._ymin = float(kdata['low'].min())
                self._ymax = float(kdata['high'].max())
                self.log_manager.info(f"设置Y轴范围: {self._ymin} - {self._ymax}")
                for ax in [self.price_ax, self.volume_ax, self.indicator_ax]:
                    ax.set_xlim(0, len(kdata)-1)
                self.price_ax.set_ylim(self._ymin, self._ymax)

            # 更新画布
            self.log_manager.info("更新画布")
            self.canvas.draw_idle()
            self.log_manager.info("基础K线数据更新完成")

        except Exception as e:
            self.log_manager.error(f"更新基础K线数据失败: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"更新基础K线数据失败: {str(e)}")

    @measure("chart.update_volume")
    def update_volume(self, kdata):
        """更新成交量数据（第二阶段渐进式加载）

        Args:
            kdata: K线数据DataFrame
        """
        try:
            # 增强对kdata的验证
            if kdata is None:
                self.log_manager.warning("更新成交量: K线数据为空")
                return

            import pandas as pd
            if not isinstance(kdata, pd.DataFrame):
                self.log_manager.warning(f"更新成交量: K线数据格式错误: {type(kdata)}")
                return

            if kdata.empty or not hasattr(self, 'volume_ax'):
                return

            # 确保包含volume列
            if 'volume' not in kdata.columns:
                self.log_manager.warning("更新成交量: K线数据缺少volume列")
                return

            # 获取样式
            style = self._get_chart_style()

            # 绘制成交量
            x = np.arange(len(kdata))
            self.renderer.render_volume(self.volume_ax, kdata, style, x=x)

            # 更新画布
            self.canvas.draw_idle()

        except Exception as e:
            self.log_manager.error(f"更新成交量数据失败: {str(e)}")
            self.error_occurred.emit(f"更新成交量数据失败: {str(e)}")

    @measure("chart.update_indicators")
    def update_indicators(self, kdata, indicators):
        """更新指标数据（第三和第四阶段渐进式加载）

        Args:
            kdata: K线数据DataFrame
            indicators: 指标数据字典
        """
        try:
            # 增强对kdata的验证
            if kdata is None:
                self.log_manager.warning("更新指标: K线数据为空")
                return

            import pandas as pd
            if not isinstance(kdata, pd.DataFrame):
                self.log_manager.warning(f"更新指标: K线数据格式错误: {type(kdata)}")
                return

            if kdata.empty or not indicators:
                return

            if not hasattr(self, 'indicator_ax'):
                return

            # 获取X轴范围
            x = np.arange(len(kdata))

            # 绘制所有指标
            for name, data in indicators.items():
                try:
                    # 处理不同类型的指标数据
                    if isinstance(data, tuple):
                        # 多线指标（如MACD）
                        for i, series in enumerate(data):
                            if series is not None and not isinstance(series, (pd.Series, np.ndarray)):
                                continue
                            style = self._get_indicator_style(name, i)
                            if len(series) > 0:  # 添加长度检查
                                self.renderer.render_line(
                                    self.indicator_ax, series, style, x=x[-len(series):])
                    elif isinstance(data, (pd.Series, np.ndarray)):
                        # 单线指标
                        style = self._get_indicator_style(name)
                        if len(data) > 0:  # 添加长度检查
                            self.renderer.render_line(
                                self.indicator_ax, data, style, x=x[-len(data):])
                except Exception as e:
                    self.log_manager.warning(f"绘制指标 {name} 失败: {str(e)}")

            # 更新画布
            self.canvas.draw_idle()

        except Exception as e:
            self.log_manager.error(f"更新指标数据失败: {str(e)}")
            self.error_occurred.emit(f"更新指标数据失败: {str(e)}")

    def _on_priority_render_complete(self, task_id: str, result):
        """处理优先级渲染完成事件"""
        self.log_manager.debug(f"接收到优先级渲染完成信号: {task_id}")
        self.update_canvas()

    def cancel_all_loading(self):
        """取消所有加载任务"""
        try:
            # 调用全局加载器的取消功能
            loader = get_progressive_loader()
            if loader:
                loader.cancel_all_tasks()
                self.log_manager.info("已请求取消所有加载任务")

            # 同样取消渲染器中的任务
            if hasattr(self, 'renderer') and hasattr(self.renderer, 'cancel_low_priority_tasks'):
                self.renderer.cancel_low_priority_tasks()
                self.log_manager.info("已请求取消渲染器中的低优先级任务")

        except Exception as e:
            self.log_manager.error(f"取消加载时发生错误: {str(e)}")

    def get_loading_performance_stats(self) -> Dict[str, Any]:
        """获取加载性能统计信息"""
        try:
            loader = get_progressive_loader()
            if loader:
                return loader.get_loading_status()
            else:
                return {"error": "Progressive loader not initialized"}
        except Exception as e:
            self.log_manager.error(f"获取加载状态时出错: {str(e)}")
            return {"error": str(e)}

    def closeEvent(self, event):
        self.log_manager.info("ChartWidget closeEvent 触发")
        self.__del__()
        super().closeEvent(event)
