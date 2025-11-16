from loguru import logger
"""
图表控件模块 - 基于Mixin模式的重构版本

该模块使用Mixin模式将原有的长文件拆分为多个功能模块，
提高代码的可维护性和可扩展性。
"""

import numpy as np
import pandas as pd
import time
from core.metrics.app_metrics_service import measure
from optimization.progressive_loading_manager import load_chart_progressive, get_progressive_loader
from gui.widgets.async_data_processor import AsyncDataProcessor
from utils.cache import Cache
from utils.theme import get_theme_manager
from utils.config_manager import ConfigManager
from .chart_mixins import (
    BaseMixin, UIMixin, RenderingMixin, IndicatorMixin,
    CrosshairMixin, InteractionMixin, ZoomMixin,
    SignalMixin, ExportMixin, UtilityMixin
)
from core.events import PatternSignalsDisplayEvent
# 从专门的文件导入ChartRenderer相关组件
from .chart_renderer import ChartRenderer
try:
    from .chart_renderer import RenderPriority
except ImportError:
    # 如果没有RenderPriority，创建一个简单的枚举
    from enum import IntEnum

    class RenderPriority(IntEnum):
        LOW = 1
        NORMAL = 2
        HIGH = 3
import traceback
from typing import Optional, List, Dict, Any
from PyQt5.QtCore import pyqtSignal, QTimer, QMutex, QMutexLocker, Qt
from PyQt5.QtWidgets import QWidget

logger = logger

# 导入所有Mixin模块

# 导入依赖

# 导入新的全局加载器

# 导入指标收集


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
    chart_type_changed = pyqtSignal(str)  # 新增：图表类型变更信号
    time_range_changed = pyqtSignal(str)  # 新增：时间范围变更信号

    # 渐进式加载信号
    progressive_loading_progress = pyqtSignal(int, str)  # 进度, 阶段名称
    progressive_loading_complete = pyqtSignal()  # 加载完成

    def __init__(self, parent=None, coordinator=None, config_manager: Optional[ConfigManager] = None,
                 theme_manager=None, data_manager=None, chart_id: str = None):
        """初始化图表控件

        Args:
            parent: Parent widget
            coordinator: The application coordinator
            config_manager: Optional ConfigManager instance to use
            theme_manager: Optional theme manager to use
            data_manager: Optional data manager to use
            chart_id: 唯一的图表ID
        """
        try:
            # 1. 初始化父类和基础属性
            super().__init__(parent)
            self.setAcceptDrops(True)  # 确保控件能接收拖拽

            # 2. 初始化管理器
            self.coordinator = coordinator
            self.event_bus = coordinator.event_bus if coordinator else None
            self.config_manager = config_manager or ConfigManager()
            self.theme_manager = theme_manager or get_theme_manager(self.config_manager)
            # 纯Loguru架构，移除log_manager依赖
            logger.info("ChartWidget __init__: 开始初始化...")

            self.data_manager = data_manager
            self.chart_id = chart_id or f"chart_{int(time.time() * 1000)}"

            # 3. 初始化非UI的核心变量
            self.current_kdata = None
            self.current_signals = []
            self.current_period = 'D'
            self._update_lock = QMutex()
            self._render_lock = QMutex()
            self.crosshair_enabled = True
            logger.info(f"ChartWidget __init__: crosshair_enabled 设置为 {self.crosshair_enabled}")

            # 4. 初始化UI (调用UIMixin中的init_ui)
            # 这一步会创建 self.canvas, self.figure, self.price_ax 等
            logger.info("ChartWidget __init__: 即将调用 init_ui()...")
            self.init_ui()
            logger.info("ChartWidget __init__: init_ui() 调用完成。")

            # 5. 在UI元素创建后，再初始化依赖它们的Mixin
            # 直接调用Mixin的__init__是错误的，应该由super()自动处理
            # CrosshairMixin.__init__(self)
            # InteractionMixin.__init__(self)
            # ZoomMixin.__init__(self)

            # 正确的做法是，在UI初始化后，调用需要设置的Mixin方法
            logger.info(f"ChartWidget __init__: 准备检查是否启用十字光标，值为: {self.crosshair_enabled}")
            if self.crosshair_enabled:
                logger.info("ChartWidget __init__: 条件满足，即将调用 enable_crosshair()...")
                self.enable_crosshair()
                logger.info("ChartWidget __init__: enable_crosshair() 调用完成。")
            else:
                logger.warning("ChartWidget __init__: 十字光标未启用，跳过调用 enable_crosshair()")

            # 6. 初始化其余组件和状态
            self.cache_manager = Cache()
            self.setAttribute(Qt.WA_OpaquePaintEvent)
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAutoFillBackground(True)

            # 使用统一的WebGPU渲染器（自动包含降级功能）
            try:
                from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer
                self.renderer = get_webgpu_chart_renderer()
                logger.info("使用WebGPU图表渲染器")

                # 连接WebGPU特有信号
                if hasattr(self.renderer, 'webgpu_status_changed'):
                    self.renderer.webgpu_status_changed.connect(self._on_webgpu_status_changed)
                if hasattr(self.renderer, 'backend_switched'):
                    self.renderer.backend_switched.connect(self._on_backend_switched)

            except (ImportError, Exception) as e:
                # 降级到传统渲染器（从优化的全局获取）
                logger.warning(f"WebGPU渲染器不可用，使用传统渲染器: {e}")
                try:
                    from optimization.chart_renderer import get_chart_renderer
                    self.renderer = get_chart_renderer()
                except (ImportError, Exception) as fallback_error:
                    # 最后降级方案：创建基础渲染器
                    logger.error(f"全局渲染器也不可用，创建基础实例: {fallback_error}")
                    from optimization.chart_renderer import ChartRenderer
                    self.renderer = ChartRenderer(max_workers=4, enable_progressive=True)

            # 连接通用信号
            self.renderer.render_progress.connect(self._on_render_progress)
            self.renderer.render_complete.connect(self._on_render_complete)
            self.renderer.render_error.connect(self._on_render_error)

            # 7. 应用初始主题
            self._apply_initial_theme()

            # 8. 绑定事件
            self._bind_events()

            logger.info("图表控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            if True:  # 使用Loguru日志
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
            else:
                logger.info(f"ChartWidget初始化错误: {error_msg}\n{traceback.format_exc()}")
            if hasattr(self, 'error_occurred'):
                self.error_occurred.emit(error_msg)

    def _bind_events(self):
        """绑定所有事件监听"""
        try:
            if hasattr(self, 'event_bus') and self.event_bus:
                self.event_bus.subscribe(PatternSignalsDisplayEvent, self._handle_pattern_signals_display)
                logger.info("成功订阅 PatternSignalsDisplayEvent")
            else:
                logger.debug("event_bus 不可用，跳过事件订阅（独立模式运行）")
                # 在独立模式下，不需要事件总线
        except Exception as e:
            logger.debug(f"事件订阅失败（独立模式下正常）: {e}")

    def _handle_pattern_signals_display(self, event: PatternSignalsDisplayEvent):
        """处理形态信号显示事件"""
        try:
            logger.info(f"收到 PatternSignalsDisplayEvent: {event.pattern_name}, "
                        f"高亮索引: {event.highlighted_signal_index}, "
                        f"共 {len(event.all_signal_indices)} 个信号")

            # 调用SignalMixin中的方法来绘制信号
            if hasattr(self, 'draw_pattern_signals'):
                self.draw_pattern_signals(
                    event.all_signal_indices,
                    event.highlighted_signal_index,
                    event.pattern_name
                )
            else:
                logger.warning("ChartWidget 中缺少 draw_pattern_signals 方法，无法绘制形态信号。")

        except Exception as e:
            logger.error(f"处理 PatternSignalsDisplayEvent 失败: {e}")
            logger.error(traceback.format_exc())

    # 删除mouseMoveEvent，因为matplotlib的canvas会自动处理事件
    # def mouseMoveEvent(self, event):
    #     """处理鼠标移动事件，用于触发十字光标"""
    #     # Manually trigger the 'motion_notify_event' for the crosshair
    #     if hasattr(self, 'canvas') and hasattr(self.canvas, 'callbacks'):
    #         self.canvas.callbacks.process('motion_notify_event', event)
    #     super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

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
                        if True:  # 使用Loguru日志
                            logger.error(f"更新任务执行失败: {str(e)}")

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"处理更新队列失败: {str(e)}")

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
            logger.info("刷新图表")
            with QMutexLocker(self._render_lock):
                if hasattr(self, 'current_kdata') and self.current_kdata is not None:
                    # 使用update_chart方法而不是直接调用renderer.render
                    self.update_chart({'kdata': self.current_kdata})
                else:
                    logger.error("刷新图表失败: K线数据不存在")
                    self.error_occurred.emit("刷新图表失败: K线数据不存在")
                    self.show_no_data("无数据")
        except Exception as e:
            logger.error(f"刷新图表失败: {str(e)}")
            self.error_occurred.emit(f"刷新图表失败: {str(e)}")
            # 确保错误情况下也显示错误提示
            self.show_no_data(f"刷新失败: {str(e)}")

    @measure("chart.update")
    def update_chart(self, data: dict = None) -> None:
        """更新图表数据

        Args:
            data: 图表数据字典
        """
        try:
            # 调用RenderingMixin中的update_chart方法
            super().update_chart(data)
            logger.debug("✅ 十字光标重置已由rendering_mixin统一处理（性能优化）")

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"更新图表失败: {e}")
            self.error_occurred.emit(f"更新图表失败: {e}")

    @measure("chart.update")
    def update(self) -> None:
        """更新图表"""
        try:
            if self.canvas:
                self.canvas.draw_idle()

            # ✅ 性能优化：延迟十字光标重置 - 避免重复调用
            # 十字光标重置已在rendering_mixin中统一处理
            # if hasattr(self, 'reset_crosshair'):
            #     self.reset_crosshair()
            #     logger.info("已重置十字光标状态")
            logger.debug("✅ 十字光标重置已由rendering_mixin统一处理（性能优化）")
        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"更新图表失败: {e}")
            self.error_occurred.emit(f"更新图表失败: {e}")

    @measure("chart.reload")
    def reload(self) -> None:
        """重新加载图表数据"""
        try:
            logger.info("重新加载图表数据")
            # 清除缓存
            self.cache_manager.clear()
            # 重新加载数据
            self.load_data(self.current_stock_code, self.current_period)
        except Exception as e:
            logger.error(f"重新加载图表数据失败: {str(e)}")
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

    def _on_webgpu_status_changed(self, status: str, details: dict):
        """处理WebGPU状态变化"""
        if True:  # 使用Loguru日志
            logger.info(f"WebGPU状态变化: {status}")

        # 可以在这里添加UI状态指示
        if status == "error":
            self.error_occurred.emit(f"WebGPU错误: {details.get('error', '未知错误')}")
        elif status == "fallback":
            if True:  # 使用Loguru日志
                logger.info("WebGPU已降级，继续使用后备渲染")

    def _on_backend_switched(self, old_backend: str, new_backend: str):
        """处理后端切换"""
        if True:  # 使用Loguru日志
            logger.info(f"渲染后端切换: {old_backend} → {new_backend}")

        # 可以在这里添加UI提示用户后端已切换

    def set_kdata(self, kdata, indicators: List[Dict] = None, enable_progressive: bool = None):
        """设置K线数据并触发图表更新

        Args:
            kdata: K线数据
            indicators: 指标列表
            enable_progressive: 是否启用渐进式加载（覆盖全局配置）
        """
        with QMutexLocker(self.update_lock):
            if kdata is None or kdata.empty:
                logger.warning("set_kdata: kdata为空, 清空图表")
                self.clear_chart()
                return

            self.kdata = kdata
            self.indicators = indicators or []
            self._is_updating = True

            # 确定是否启用渐进式加载
            use_progressive = enable_progressive if enable_progressive is not None else self.is_progressive_loading_enabled

            if use_progressive:
                # 使用新的全局加载器，并明确定义加载阶段
                logger.info("使用全局渐进式加载器更新图表（带阶段配置）...")

                loading_stages = [
                    {'name': 'K线和主图', 'priority': 'CRITICAL'},
                    {'name': '成交量', 'priority': 'HIGH'},
                    {'name': '技术指标', 'priority': 'NORMAL'},
                ]

                load_chart_progressive(
                    self, self.kdata, self.indicators, stages=loading_stages)
            else:
                # 传统同步加载
                logger.info("使用同步方式更新图表...")
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
        """更新基础K线数据 - 高性能实现

        Args:
            kdata: K线数据，可以是DataFrame或字典
        """
        try:
            if True:  # 使用Loguru日志
                logger.info(f"开始更新基础K线数据: 类型={type(kdata)}")

            # 清除图表
            self.clear_chart()
            if True:  # 使用Loguru日志
                logger.info("已清除图表")

            # 处理不同的数据类型
            if isinstance(kdata, pd.DataFrame):
                # DataFrame直接使用
                if kdata.empty:
                    if True:  # 使用Loguru日志
                        logger.warning("K线数据为空DataFrame")
                    return

                # ✅ 修复：验证数据顺序（确保按时间升序排列）
                if 'datetime' in kdata.columns:
                    try:
                        datetime_series = pd.to_datetime(kdata['datetime'])
                        # 检查是否已排序
                        is_sorted = datetime_series.is_monotonic_increasing
                        if not is_sorted:
                            logger.warning("⚠️ K线数据未按时间升序排列，正在自动排序...")
                            kdata = kdata.sort_values(by='datetime', ascending=True).reset_index(drop=True)
                            datetime_series = pd.to_datetime(kdata['datetime'])
                            logger.info("✅ K线数据已按时间升序排序")

                        # ✅ 修复：输出数据时间范围日志
                        time_min = datetime_series.min()
                        time_max = datetime_series.max()
                        time_span = time_max - time_min
                        logger.info(f"📊 K线数据时间范围: {time_min.strftime('%Y-%m-%d %H:%M:%S')} ~ {time_max.strftime('%Y-%m-%d %H:%M:%S')} (跨度: {time_span.days}天)")

                        # ✅ 修复：验证数据完整性
                        missing_count = datetime_series.isna().sum()
                        if missing_count > 0:
                            logger.warning(f"⚠️ K线数据包含 {missing_count} 个缺失的datetime值")
                    except Exception as e:
                        logger.warning(f"⚠️ datetime列验证失败: {e}")

                self.current_kdata = kdata
                if True:  # 使用Loguru日志
                    logger.info(
                        f"K线数据形状: {kdata.shape}, 列: {list(kdata.columns)}")
            elif isinstance(kdata, dict):
                # 字典格式，尝试转换
                if 'data' in kdata and isinstance(kdata['data'], pd.DataFrame):
                    self.current_kdata = kdata['data']
                else:
                    # 尝试将整个字典转换为DataFrame
                    try:
                        self.current_kdata = pd.DataFrame([kdata])
                    except Exception as e:
                        if True:  # 使用Loguru日志
                            logger.error(f"无法将字典转换为DataFrame: {e}")
                        return
            elif isinstance(kdata, list):
                # 列表格式，转换为DataFrame
                if not kdata:
                    if True:  # 使用Loguru日志
                        logger.warning("K线数据为空列表")
                    return
                self.current_kdata = pd.DataFrame(kdata)
            else:
                if True:  # 使用Loguru日志
                    logger.error(f"不支持的K线数据类型: {type(kdata)}")
                return

            # 获取样式
            style = self._get_chart_style()
            if True:  # 使用Loguru日志
                logger.info(f"获取样式: {style}")

            # ✅ 修复：使用datetime作为X轴（如果数据包含datetime列）
            use_datetime_axis = False
            x = None

            if 'datetime' in self.current_kdata.columns:
                try:
                    # 验证datetime列是否有效
                    datetime_series = pd.to_datetime(self.current_kdata['datetime'])
                    if datetime_series.notna().any():
                        use_datetime_axis = True
                        logger.info("✅ 使用datetime作为X轴")
                    else:
                        logger.warning("⚠️ datetime列全部为空，回退到数字索引X轴")
                except Exception as e:
                    logger.warning(f"⚠️ datetime列无效: {e}，回退到数字索引X轴")
            else:
                logger.info("ℹ️ 数据不包含datetime列，使用数字索引X轴（向后兼容）")

            # 渲染K线图（传递use_datetime_axis参数）
            if True:  # 使用Loguru日志
                logger.info(
                    f"调用renderer.render_candlesticks: price_ax={self.price_ax}, kdata形状={self.current_kdata.shape}, use_datetime_axis={use_datetime_axis}")
            self.renderer.render_candlesticks(
                self.price_ax, self.current_kdata, style, x=x, use_datetime_axis=use_datetime_axis)
            if True:  # 使用Loguru日志
                logger.info("K线绘制完成")

            # 设置Y轴范围
            ymin = float(self.current_kdata['low'].min())
            ymax = float(self.current_kdata['high'].max())
            margin = (ymax - ymin) * 0.05  # 5% 边距
            self.price_ax.set_ylim(ymin - margin, ymax + margin)
            if True:  # 使用Loguru日志
                logger.info(f"设置Y轴范围: {ymin - margin} - {ymax + margin}")

            # ✅ 修复：X轴范围设置
            if not use_datetime_axis:
                # 数字索引X轴：手动设置范围
                self.price_ax.set_xlim(0, len(self.current_kdata) - 1)
            else:
                # datetime X轴：显式设置X轴范围，确保K线图正确显示
                try:
                    # 导入matplotlib.dates
                    import matplotlib.dates as mdates
                    datetime_series = pd.to_datetime(self.current_kdata['datetime'])
                    x_min = mdates.date2num(datetime_series.min())
                    x_max = mdates.date2num(datetime_series.max())
                    # 添加2%边距，确保K线图完全可见
                    margin = (x_max - x_min) * 0.04 if x_max > x_min else 1.0
                    self.price_ax.set_xlim(x_min - margin, x_max + margin)
                    logger.debug(f"✅ datetime X轴范围已设置: {datetime_series.min()} ~ {datetime_series.max()}")
                except Exception as e:
                    logger.warning(f"⚠️ 设置datetime X轴范围失败: {e}，使用autoscale_view()")
                    # 失败时使用autoscale_view()作为后备
                    self.price_ax.autoscale_view()

            # 更新画布
            if True:  # 使用Loguru日志
                logger.info("更新画布")
            self.canvas.draw_idle()

            # ✅ 性能优化：延迟十字光标重置 - 已在rendering_mixin中处理
            # 不再在这里重复重置，避免重复调用开销
            # if hasattr(self, 'reset_crosshair'):
            #     self.reset_crosshair()
            #     logger.info("已重置十字光标状态")
            logger.debug("✅ 十字光标重置已由rendering_mixin统一处理（性能优化）")

            if True:  # 使用Loguru日志
                logger.info("基础K线数据更新完成")

        except Exception as e:
            if True:  # 使用Loguru日志
                logger.error(f"更新基础K线数据失败: {str(e)}", exc_info=True)
            else:
                logger.info(f"更新基础K线数据失败: {str(e)}")

    @measure("chart.update_volume")
    def update_volume(self, kdata):
        """更新成交量数据（第二阶段渐进式加载）

        Args:
            kdata: K线数据DataFrame
        """
        try:
            # 增强对kdata的验证
            if kdata is None:
                logger.warning("更新成交量: K线数据为空")
                return

            if not isinstance(kdata, pd.DataFrame):
                logger.warning(f"更新成交量: K线数据格式错误: {type(kdata)}")
                return

            if kdata.empty or not hasattr(self, 'volume_ax'):
                return

            # 确保包含volume列
            if 'volume' not in kdata.columns:
                logger.warning("更新成交量: K线数据缺少volume列")
                return

            # 获取样式
            style = self._get_chart_style()

            # ✅ 修复：使用datetime作为X轴（与K线图保持一致）
            use_datetime_axis = False
            x = None

            if 'datetime' in kdata.columns:
                try:
                    datetime_series = pd.to_datetime(kdata['datetime'])
                    if datetime_series.notna().any():
                        use_datetime_axis = True
                        logger.debug("✅ 成交量使用datetime作为X轴")
                except Exception as e:
                    logger.warning(f"⚠️ 成交量datetime列无效: {e}，回退到数字索引X轴")
            else:
                logger.debug("ℹ️ 成交量数据不包含datetime列，使用数字索引X轴（向后兼容）")

            # 绘制成交量（传递use_datetime_axis参数）
            self.renderer.render_volume(self.volume_ax, kdata, style, x=x, use_datetime_axis=use_datetime_axis)

            # 更新画布
            self.canvas.draw_idle()

        except Exception as e:
            logger.error(f"更新成交量数据失败: {str(e)}")
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
                logger.warning("更新指标: K线数据为空")
                return

            if not isinstance(kdata, pd.DataFrame):
                logger.warning(f"更新指标: K线数据格式错误: {type(kdata)}")
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
                    logger.warning(f"绘制指标 {name} 失败: {str(e)}")

            # 更新画布
            self.canvas.draw_idle()

        except Exception as e:
            logger.error(f"更新指标数据失败: {str(e)}")
            self.error_occurred.emit(f"更新指标数据失败: {str(e)}")

    def _on_priority_render_complete(self, task_id: str, result):
        """处理优先级渲染完成事件"""
        logger.debug(f"接收到优先级渲染完成信号: {task_id}")
        self.update_canvas()

    def cancel_all_loading(self):
        """取消所有加载任务"""
        try:
            # 调用全局加载器的取消功能
            loader = get_progressive_loader()
            if loader:
                loader.cancel_all_tasks()
                logger.info("已请求取消所有加载任务")

            # 同样取消渲染器中的任务
            if hasattr(self, 'renderer') and hasattr(self.renderer, 'cancel_low_priority_tasks'):
                self.renderer.cancel_low_priority_tasks()
                logger.info("已请求取消渲染器中的低优先级任务")

        except Exception as e:
            logger.error(f"取消加载时发生错误: {str(e)}")

    def get_loading_performance_stats(self) -> Dict[str, Any]:
        """获取加载性能统计信息"""
        try:
            loader = get_progressive_loader()
            if loader:
                return loader.get_loading_status()
            else:
                return {"error": "Progressive loader not initialized"}
        except Exception as e:
            logger.error(f"获取加载状态时出错: {str(e)}")
            return {"error": str(e)}

    def set_chart_type(self, chart_type: str):
        """设置图表类型"""
        try:
            # 存储图表类型
            self.chart_type = chart_type

            # 发射信号
            self.chart_type_changed.emit(chart_type)

            # 根据图表类型调整显示
            if chart_type == 'multi_panel':
                logger.debug("设置为多面板图表模式")
            elif chart_type == 'single_panel':
                logger.debug("设置为单面板图表模式")
            elif chart_type == 'candlestick':
                logger.debug("设置为K线图模式")
            else:
                logger.debug(f"设置图表类型为: {chart_type}")

        except Exception as e:
            logger.error(f"设置图表类型失败: {e}")

    def get_chart_type(self) -> str:
        """获取当前图表类型"""
        return getattr(self, 'chart_type', 'candlestick')

    def enable_real_time_update(self, enabled: bool):
        """启用/禁用实时更新"""
        try:
            self.real_time_update_enabled = enabled
            if enabled:
                logger.debug("启用实时更新")
            else:
                logger.debug("禁用实时更新")
        except Exception as e:
            logger.error(f"设置实时更新失败: {e}")

    def update_data(self, data):
        """更新图表数据

        Args:
            data: 数据，可以是DataFrame或其他格式
        """
        try:
            if data is not None and not data.empty:
                # 如果数据是DataFrame，尝试更新K线数据
                if hasattr(data, 'columns'):
                    # 检查是否包含K线数据的必要列
                    required_columns = ['open', 'high', 'low', 'close']
                    if all(col in data.columns for col in required_columns):
                        self.update_basic_kdata(data)
                        logger.debug(f"更新K线数据成功，数据行数: {len(data)}")
                    else:
                        # 如果不是K线数据，使用通用更新方式
                        self.update()
                        logger.debug(f"更新图表数据成功，数据类型: {type(data)}")
                else:
                    # 非DataFrame数据，使用通用更新方法
                    self.update()
                    logger.debug("使用通用方法更新图表")
            else:
                logger.debug("数据为空，跳过图表更新")
        except Exception as e:
            logger.error(f"更新图表数据失败: {e}")
            # 降级到基础更新
            try:
                self.update()
            except Exception as fallback_e:
                logger.error(f"降级更新也失败: {fallback_e}")

    def add_data(self, data):
        """添加实时数据到图表（专业回测监控使用）

        Args:
            data: 监控数据字典，包含timestamp和各种指标
        """
        try:
            if isinstance(data, dict):
                # 处理监控数据
                timestamp = data.get('timestamp')
                if timestamp:
                    logger.debug(f"添加监控数据: {timestamp}, 指标数量: {len(data)}")

                    # 这里可以根据需要实现具体的图表更新逻辑
                    # 目前先使用通用更新方式
                    self.update()

                    # 可以在这里添加具体的实时图表绘制逻辑
                    # 比如绘制收益率曲线、回撤曲线等

                else:
                    logger.warning("监控数据缺少timestamp字段")
            else:
                logger.warning(f"add_data期望字典类型数据，收到: {type(data)}")

        except Exception as e:
            logger.error(f"添加图表数据失败: {e}")
            # 降级处理
            try:
                self.update()
            except Exception as fallback_e:
                logger.error(f"降级更新失败: {fallback_e}")

    def closeEvent(self, event):
        logger.info("ChartWidget closeEvent 触发")
        self.__del__()
        super().closeEvent(event)
