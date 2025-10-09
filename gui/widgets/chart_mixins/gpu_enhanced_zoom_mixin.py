from loguru import logger
"""
GPU增强缩放Mixin模块

提供基于GPU加速的缩放和平移功能：
- 集成GPU交互引擎
- 硬件加速的视口变换
- 平滑动画过渡
- 性能监控和优化
"""

from typing import Optional, Dict, Any, Tuple
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QWheelEvent, QMouseEvent
from PyQt5.QtWidgets import QWidget

logger = logger

class GPUEnhancedZoomMixin:
    """GPU增强缩放功能Mixin"""

    # 新增信号
    gpu_viewport_changed = pyqtSignal(object)  # ViewportState
    gpu_interaction_performance = pyqtSignal(dict)  # 性能统计

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # GPU交互引擎
        self._gpu_interaction_engine = None
        self._gpu_zoom_enabled = True
        self._fallback_to_cpu = True

        # 性能监控
        self._gpu_performance_stats = {
            'gpu_operations': 0,
            'cpu_fallbacks': 0,
            'average_gpu_frame_time': 0.0,
            'average_cpu_frame_time': 0.0
        }

        # 状态管理
        self._last_viewport_state = None
        self._viewport_update_timer = QTimer()
        self._viewport_update_timer.timeout.connect(self._apply_viewport_to_chart)
        self._viewport_update_timer.setSingleShot(True)

        # 初始化GPU交互引擎
        self._initialize_gpu_interaction()

    def _initialize_gpu_interaction(self):
        """初始化GPU交互引擎"""
        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine
            from core.webgpu import get_webgpu_manager

            # 获取WebGPU管理器（如果可用）
            webgpu_manager = None
            try:
                webgpu_manager = get_webgpu_manager()
            except Exception as e:
                logger.warning(f"无法获取WebGPU管理器: {e}")

            # 创建GPU交互引擎
            self._gpu_interaction_engine = GPUInteractionEngine(webgpu_manager)

            # 连接信号
            self._gpu_interaction_engine.viewport_changed.connect(self._on_gpu_viewport_changed)
            self._gpu_interaction_engine.performance_stats.connect(self._on_gpu_performance_stats)
            self._gpu_interaction_engine.interaction_started.connect(self._on_gpu_interaction_started)
            self._gpu_interaction_engine.interaction_finished.connect(self._on_gpu_interaction_finished)

            logger.info("GPU交互引擎初始化成功")

        except ImportError as e:
            logger.warning(f"GPU交互引擎不可用，将使用CPU后备: {e}")
            self._gpu_interaction_engine = None
            self._gpu_zoom_enabled = False
        except Exception as e:
            logger.error(f"GPU交互引擎初始化失败: {e}")
            self._gpu_interaction_engine = None
            self._gpu_zoom_enabled = False

    def _on_gpu_viewport_changed(self, viewport_state):
        """GPU视口变化回调"""
        self._last_viewport_state = viewport_state

        # 延迟应用到图表（避免过于频繁的更新）
        if not self._viewport_update_timer.isActive():
            self._viewport_update_timer.start(16)  # ~60 FPS

        # 发送信号
        self.gpu_viewport_changed.emit(viewport_state)

    def _on_gpu_performance_stats(self, stats: Dict[str, Any]):
        """GPU性能统计回调"""
        self._gpu_performance_stats.update(stats)
        self.gpu_interaction_performance.emit(stats)

    def _on_gpu_interaction_started(self, interaction_type: str):
        """GPU交互开始回调"""
        logger.debug(f"GPU交互开始: {interaction_type}")

    def _on_gpu_interaction_finished(self, interaction_type: str):
        """GPU交互结束回调"""
        logger.debug(f"GPU交互结束: {interaction_type}")

    def _apply_viewport_to_chart(self):
        """应用视口状态到图表"""
        if not self._last_viewport_state:
            return

        try:
            viewport = self._last_viewport_state
            x_min, x_max, y_min, y_max = viewport.get_range()

            # 应用到matplotlib图表
            if hasattr(self, 'figure') and self.figure:
                for ax in self.figure.get_axes():
                    ax.set_xlim(x_min, x_max)
                    ax.set_ylim(y_min, y_max)

                # 刷新画布
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas.draw_idle()

            # 更新缩放状态（如果父类有这些方法）
            if hasattr(self, '_update_zoom_state'):
                self._update_zoom_state(viewport.zoom_level)

        except Exception as e:
            logger.error(f"应用GPU视口状态失败: {e}")

    def wheelEvent(self, event: QWheelEvent):
        """重写滚轮事件处理"""
        if self._gpu_zoom_enabled and self._gpu_interaction_engine:
            # 尝试GPU加速处理
            try:
                if self._gpu_interaction_engine.handle_wheel_event(event, self):
                    self._gpu_performance_stats['gpu_operations'] += 1
                    return
            except Exception as e:
                logger.warning(f"GPU滚轮事件处理失败，降级到CPU: {e}")
                self._gpu_performance_stats['cpu_fallbacks'] += 1

        # CPU后备处理
        if self._fallback_to_cpu and hasattr(super(), 'wheelEvent'):
            super().wheelEvent(event)
        else:
            self._handle_wheel_event_cpu(event)

    def mousePressEvent(self, event: QMouseEvent):
        """重写鼠标按下事件处理"""
        if self._gpu_zoom_enabled and self._gpu_interaction_engine:
            # 尝试GPU加速处理
            try:
                if self._gpu_interaction_engine.handle_mouse_press(event, self):
                    return
            except Exception as e:
                logger.warning(f"GPU鼠标按下事件处理失败，降级到CPU: {e}")
                self._gpu_performance_stats['cpu_fallbacks'] += 1

        # CPU后备处理
        if self._fallback_to_cpu and hasattr(super(), 'mousePressEvent'):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """重写鼠标移动事件处理"""
        if self._gpu_zoom_enabled and self._gpu_interaction_engine:
            # 尝试GPU加速处理
            try:
                if self._gpu_interaction_engine.handle_mouse_move(event, self):
                    return
            except Exception as e:
                logger.warning(f"GPU鼠标移动事件处理失败，降级到CPU: {e}")
                self._gpu_performance_stats['cpu_fallbacks'] += 1

        # CPU后备处理
        if self._fallback_to_cpu and hasattr(super(), 'mouseMoveEvent'):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """重写鼠标释放事件处理"""
        if self._gpu_zoom_enabled and self._gpu_interaction_engine:
            # 尝试GPU加速处理
            try:
                if self._gpu_interaction_engine.handle_mouse_release(event, self):
                    return
            except Exception as e:
                logger.warning(f"GPU鼠标释放事件处理失败，降级到CPU: {e}")
                self._gpu_performance_stats['cpu_fallbacks'] += 1

        # CPU后备处理
        if self._fallback_to_cpu and hasattr(super(), 'mouseReleaseEvent'):
            super().mouseReleaseEvent(event)

    def _handle_wheel_event_cpu(self, event: QWheelEvent):
        """CPU后备滚轮事件处理"""
        import time
        start_time = time.time()

        try:
            # 基础缩放逻辑
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 0.9

            # 应用缩放（简化版本）
            if hasattr(self, 'figure') and self.figure:
                for ax in self.figure.get_axes():
                    # 获取当前范围
                    x_min, x_max = ax.get_xlim()
                    y_min, y_max = ax.get_ylim()

                    # 计算缩放中心
                    rel_x = event.x() / self.width() if self.width() > 0 else 0.5
                    rel_y = event.y() / self.height() if self.height() > 0 else 0.5

                    # 应用缩放
                    x_center = x_min + rel_x * (x_max - x_min)
                    y_center = y_min + rel_y * (y_max - y_min)

                    x_range = (x_max - x_min) / zoom_factor
                    y_range = (y_max - y_min) / zoom_factor

                    new_x_min = x_center - rel_x * x_range
                    new_x_max = x_center + (1 - rel_x) * x_range
                    new_y_min = y_center - rel_y * y_range
                    new_y_max = y_center + (1 - rel_y) * y_range

                    ax.set_xlim(new_x_min, new_x_max)
                    ax.set_ylim(new_y_min, new_y_max)

                # 刷新画布
                if hasattr(self, 'canvas') and self.canvas:
                    self.canvas.draw_idle()

        except Exception as e:
            logger.error(f"CPU滚轮事件处理失败: {e}")

        # 更新性能统计
        frame_time = time.time() - start_time
        current_avg = self._gpu_performance_stats['average_cpu_frame_time']
        cpu_ops = self._gpu_performance_stats['cpu_fallbacks']
        if cpu_ops > 0:
            new_avg = (current_avg * (cpu_ops - 1) + frame_time) / cpu_ops
            self._gpu_performance_stats['average_cpu_frame_time'] = new_avg

    def reset_gpu_zoom(self):
        """重置GPU缩放"""
        if self._gpu_interaction_engine:
            self._gpu_interaction_engine.reset_viewport()

    def zoom_to_fit_gpu(self, data_bounds: Optional[Tuple[float, float, float, float]] = None):
        """GPU加速缩放以适应数据"""
        if not self._gpu_interaction_engine:
            return

        if data_bounds:
            self._gpu_interaction_engine.zoom_to_fit(data_bounds)
        else:
            # 自动计算数据边界
            try:
                if hasattr(self, 'figure') and self.figure:
                    all_x_data = []
                    all_y_data = []

                    for ax in self.figure.get_axes():
                        for line in ax.get_lines():
                            x_data = line.get_xdata()
                            y_data = line.get_ydata()
                            if len(x_data) > 0 and len(y_data) > 0:
                                all_x_data.extend(x_data)
                                all_y_data.extend(y_data)

                    if all_x_data and all_y_data:
                        bounds = (min(all_x_data), max(all_x_data), min(all_y_data), max(all_y_data))
                        self._gpu_interaction_engine.zoom_to_fit(bounds)
            except Exception as e:
                logger.error(f"自动计算数据边界失败: {e}")

    def set_gpu_zoom_enabled(self, enabled: bool):
        """设置GPU缩放启用状态"""
        self._gpu_zoom_enabled = enabled
        logger.info(f"GPU缩放{'启用' if enabled else '禁用'}")

    def set_gpu_animation_enabled(self, enabled: bool):
        """设置GPU动画启用状态"""
        if self._gpu_interaction_engine:
            self._gpu_interaction_engine.set_animation_enabled(enabled)

    def set_gpu_zoom_sensitivity(self, sensitivity: float):
        """设置GPU缩放灵敏度"""
        if self._gpu_interaction_engine:
            self._gpu_interaction_engine.set_config('zoom_sensitivity', sensitivity)

    def set_gpu_pan_sensitivity(self, sensitivity: float):
        """设置GPU平移灵敏度"""
        if self._gpu_interaction_engine:
            self._gpu_interaction_engine.set_config('pan_sensitivity', sensitivity)

    def get_gpu_performance_stats(self) -> Dict[str, Any]:
        """获取GPU性能统计"""
        stats = self._gpu_performance_stats.copy()

        if self._gpu_interaction_engine:
            gpu_stats = self._gpu_interaction_engine.get_performance_stats()
            stats.update(gpu_stats)

        return stats

    def get_current_gpu_viewport(self):
        """获取当前GPU视口状态"""
        if self._gpu_interaction_engine:
            return self._gpu_interaction_engine.get_current_viewport()
        return None

    def set_gpu_viewport(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """设置GPU视口范围"""
        if self._gpu_interaction_engine:
            self._gpu_interaction_engine.set_viewport(x_min, x_max, y_min, y_max)

    def is_gpu_zoom_available(self) -> bool:
        """检查GPU缩放是否可用"""
        return self._gpu_interaction_engine is not None

    def get_gpu_zoom_config(self) -> Dict[str, Any]:
        """获取GPU缩放配置"""
        if self._gpu_interaction_engine:
            return self._gpu_interaction_engine.config.copy()
        return {}

    def update_gpu_zoom_config(self, config: Dict[str, Any]):
        """更新GPU缩放配置"""
        if self._gpu_interaction_engine:
            for key, value in config.items():
                self._gpu_interaction_engine.set_config(key, value)
