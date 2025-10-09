from loguru import logger
"""
WebGPU交互引擎模块

实现基于GPU加速的图表交互功能：
- 硬件加速缩放和平移
- 实时视口变换
- 平滑动画过渡
- 手势识别和响应
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
import math

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QWheelEvent, QMouseEvent
from PyQt5.QtWidgets import QWidget

logger = logger

class InteractionType(Enum):
    """交互类型"""
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    RESET = "reset"

@dataclass
class ViewportState:
    """视口状态"""
    x_min: float = 0.0
    x_max: float = 100.0
    y_min: float = 0.0
    y_max: float = 100.0
    zoom_level: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def copy(self) -> 'ViewportState':
        """创建副本"""
        return ViewportState(
            self.x_min, self.x_max, self.y_min, self.y_max,
            self.zoom_level, self.pan_x, self.pan_y
        )

    def get_range(self) -> Tuple[float, float, float, float]:
        """获取视口范围"""
        width = self.x_max - self.x_min
        height = self.y_max - self.y_min

        # 应用缩放
        zoomed_width = width / self.zoom_level
        zoomed_height = height / self.zoom_level

        # 应用平移
        center_x = (self.x_min + self.x_max) / 2 + self.pan_x
        center_y = (self.y_min + self.y_max) / 2 + self.pan_y

        return (
            center_x - zoomed_width / 2,
            center_x + zoomed_width / 2,
            center_y - zoomed_height / 2,
            center_y + zoomed_height / 2
        )

@dataclass
class InteractionEvent:
    """交互事件"""
    event_type: InteractionType
    timestamp: float
    position: Tuple[float, float]
    delta: Tuple[float, float]
    modifiers: int = 0

    @classmethod
    def from_wheel_event(cls, event: QWheelEvent) -> 'InteractionEvent':
        """从滚轮事件创建"""
        delta_y = event.angleDelta().y()
        event_type = InteractionType.ZOOM_IN if delta_y > 0 else InteractionType.ZOOM_OUT

        return cls(
            event_type=event_type,
            timestamp=time.time(),
            position=(event.x(), event.y()),
            delta=(0, delta_y),
            modifiers=int(event.modifiers())
        )

    @classmethod
    def from_mouse_event(cls, event: QMouseEvent, event_type: InteractionType,
                         delta: Tuple[float, float] = (0, 0)) -> 'InteractionEvent':
        """从鼠标事件创建"""
        return cls(
            event_type=event_type,
            timestamp=time.time(),
            position=(event.x(), event.y()),
            delta=delta,
            modifiers=int(event.modifiers())
        )

class GPUInteractionEngine(QObject):
    """GPU加速交互引擎"""

    # 信号
    viewport_changed = pyqtSignal(object)  # ViewportState
    interaction_started = pyqtSignal(str)  # 交互类型
    interaction_finished = pyqtSignal(str)  # 交互类型
    performance_stats = pyqtSignal(dict)  # 性能统计

    def __init__(self, webgpu_manager=None):
        super().__init__()

        self.webgpu_manager = webgpu_manager
        self._current_viewport = ViewportState()
        self._target_viewport = ViewportState()
        self._animation_enabled = True
        self._animation_duration = 300  # ms

        # 交互配置
        self.config = {
            'zoom_sensitivity': 0.1,
            'pan_sensitivity': 1.0,
            'min_zoom': 0.1,
            'max_zoom': 100.0,
            'smooth_animation': True,
            'animation_easing': QEasingCurve.OutCubic,
            'momentum_decay': 0.95,
            'gesture_threshold': 10.0
        }

        # 状态管理
        self._is_dragging = False
        self._last_mouse_pos = None
        self._drag_start_pos = None
        self._drag_start_viewport = None
        self._momentum_velocity = [0.0, 0.0]

        # 动画管理
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_start_time = 0
        self._animation_start_viewport = None

        # 性能监控
        self._performance_stats = {
            'total_interactions': 0,
            'zoom_operations': 0,
            'pan_operations': 0,
            'animation_frames': 0,
            'average_frame_time': 0.0,
            'gpu_acceleration_enabled': bool(webgpu_manager)
        }

        # 手势识别
        self._gesture_buffer = []
        self._gesture_threshold = 5

        logger.info(f"GPU交互引擎初始化完成 - GPU加速: {self._performance_stats['gpu_acceleration_enabled']}")

    def set_viewport(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """设置视口范围"""
        self._current_viewport.x_min = x_min
        self._current_viewport.x_max = x_max
        self._current_viewport.y_min = y_min
        self._current_viewport.y_max = y_max
        self._target_viewport = self._current_viewport.copy()

        self.viewport_changed.emit(self._current_viewport)

    def handle_wheel_event(self, event: QWheelEvent, widget: QWidget) -> bool:
        """处理滚轮事件（缩放）"""
        try:
            interaction_event = InteractionEvent.from_wheel_event(event)
            return self._handle_zoom_interaction(interaction_event, widget)
        except Exception as e:
            logger.error(f"处理滚轮事件失败: {e}")
            return False

    def handle_mouse_press(self, event: QMouseEvent, widget: QWidget) -> bool:
        """处理鼠标按下事件"""
        try:
            if event.button() == 1:  # 左键
                self._start_drag(event, widget)
                return True
            return False
        except Exception as e:
            logger.error(f"处理鼠标按下事件失败: {e}")
            return False

    def handle_mouse_move(self, event: QMouseEvent, widget: QWidget) -> bool:
        """处理鼠标移动事件"""
        try:
            if self._is_dragging:
                return self._handle_drag(event, widget)
            return False
        except Exception as e:
            logger.error(f"处理鼠标移动事件失败: {e}")
            return False

    def handle_mouse_release(self, event: QMouseEvent, widget: QWidget) -> bool:
        """处理鼠标释放事件"""
        try:
            if self._is_dragging:
                self._end_drag(event, widget)
                return True
            return False
        except Exception as e:
            logger.error(f"处理鼠标释放事件失败: {e}")
            return False

    def _handle_zoom_interaction(self, event: InteractionEvent, widget: QWidget) -> bool:
        """处理缩放交互"""
        start_time = time.time()

        # 计算缩放因子
        zoom_delta = event.delta[1] * self.config['zoom_sensitivity'] / 120.0
        zoom_factor = 1.0 + zoom_delta

        # 限制缩放范围
        new_zoom = self._current_viewport.zoom_level * zoom_factor
        new_zoom = max(self.config['min_zoom'], min(self.config['max_zoom'], new_zoom))
        zoom_factor = new_zoom / self._current_viewport.zoom_level

        # 计算缩放中心（相对于数据坐标）
        widget_width = widget.width()
        widget_height = widget.height()

        if widget_width > 0 and widget_height > 0:
            # 将鼠标位置转换为数据坐标
            rel_x = event.position[0] / widget_width
            rel_y = event.position[1] / widget_height

            current_range = self._current_viewport.get_range()
            data_x = current_range[0] + rel_x * (current_range[1] - current_range[0])
            data_y = current_range[2] + rel_y * (current_range[3] - current_range[2])

            # 更新目标视口
            self._target_viewport.zoom_level = new_zoom

            # 调整平移以保持缩放中心
            if zoom_factor != 1.0:
                zoom_offset_x = (data_x - (self._current_viewport.x_min + self._current_viewport.x_max) / 2) * (1 - 1/zoom_factor)
                zoom_offset_y = (data_y - (self._current_viewport.y_min + self._current_viewport.y_max) / 2) * (1 - 1/zoom_factor)

                self._target_viewport.pan_x += zoom_offset_x
                self._target_viewport.pan_y += zoom_offset_y
        else:
            self._target_viewport.zoom_level = new_zoom

        # 启动动画或直接更新
        if self._animation_enabled:
            self._start_animation()
        else:
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)

        # 更新性能统计
        self._performance_stats['zoom_operations'] += 1
        self._performance_stats['total_interactions'] += 1

        frame_time = time.time() - start_time
        self._update_performance_stats(frame_time)

        self.interaction_started.emit(event.event_type.value)

        return True

    def _start_drag(self, event: QMouseEvent, widget: QWidget):
        """开始拖拽"""
        self._is_dragging = True
        self._last_mouse_pos = (event.x(), event.y())
        self._drag_start_pos = (event.x(), event.y())
        self._drag_start_viewport = self._current_viewport.copy()
        self._momentum_velocity = [0.0, 0.0]

        self.interaction_started.emit("pan")

    def _handle_drag(self, event: QMouseEvent, widget: QWidget) -> bool:
        """处理拖拽"""
        if not self._last_mouse_pos:
            return False

        start_time = time.time()

        # 计算鼠标移动距离
        current_pos = (event.x(), event.y())
        delta_x = current_pos[0] - self._last_mouse_pos[0]
        delta_y = current_pos[1] - self._last_mouse_pos[1]

        # 转换为数据坐标的偏移
        widget_width = widget.width()
        widget_height = widget.height()

        if widget_width > 0 and widget_height > 0:
            current_range = self._current_viewport.get_range()
            data_width = current_range[1] - current_range[0]
            data_height = current_range[3] - current_range[2]

            pan_delta_x = -delta_x * data_width / widget_width * self.config['pan_sensitivity']
            pan_delta_y = delta_y * data_height / widget_height * self.config['pan_sensitivity']

            # 更新平移
            self._target_viewport.pan_x = self._current_viewport.pan_x + pan_delta_x
            self._target_viewport.pan_y = self._current_viewport.pan_y + pan_delta_y

            # 更新动量
            self._momentum_velocity[0] = pan_delta_x * 0.1
            self._momentum_velocity[1] = pan_delta_y * 0.1

            # 直接更新（平移不需要动画）
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)

        self._last_mouse_pos = current_pos

        # 更新性能统计
        self._performance_stats['pan_operations'] += 1
        self._performance_stats['total_interactions'] += 1

        frame_time = time.time() - start_time
        self._update_performance_stats(frame_time)

        return True

    def _end_drag(self, event: QMouseEvent, widget: QWidget):
        """结束拖拽"""
        self._is_dragging = False

        # 启动动量滚动
        if abs(self._momentum_velocity[0]) > 0.1 or abs(self._momentum_velocity[1]) > 0.1:
            self._start_momentum_animation()

        self._last_mouse_pos = None
        self._drag_start_pos = None
        self._drag_start_viewport = None

        self.interaction_finished.emit("pan")

    def _start_animation(self):
        """启动动画"""
        if not self._animation_enabled:
            return

        self._animation_start_time = time.time()
        self._animation_start_viewport = self._current_viewport.copy()

        if not self._animation_timer.isActive():
            self._animation_timer.start(16)  # ~60 FPS

    def _start_momentum_animation(self):
        """启动动量动画"""
        if not self._animation_enabled:
            return

        # 创建动量动画定时器
        momentum_timer = QTimer()

        def update_momentum():
            # 应用动量
            self._target_viewport.pan_x += self._momentum_velocity[0]
            self._target_viewport.pan_y += self._momentum_velocity[1]

            # 衰减动量
            self._momentum_velocity[0] *= self.config['momentum_decay']
            self._momentum_velocity[1] *= self.config['momentum_decay']

            # 更新视口
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)

            # 检查是否停止
            if abs(self._momentum_velocity[0]) < 0.01 and abs(self._momentum_velocity[1]) < 0.01:
                momentum_timer.stop()
                momentum_timer.deleteLater()

        momentum_timer.timeout.connect(update_momentum)
        momentum_timer.start(16)  # ~60 FPS

    def _update_animation(self):
        """更新动画"""
        if not self._animation_start_viewport:
            self._animation_timer.stop()
            return

        current_time = time.time()
        elapsed = (current_time - self._animation_start_time) * 1000  # ms

        if elapsed >= self._animation_duration:
            # 动画完成
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)
            self._animation_timer.stop()
            self._animation_start_viewport = None
            return

        # 计算插值进度
        progress = elapsed / self._animation_duration

        # 应用缓动曲线
        if self.config['animation_easing'] == QEasingCurve.OutCubic:
            progress = 1 - (1 - progress) ** 3
        elif self.config['animation_easing'] == QEasingCurve.InOutCubic:
            if progress < 0.5:
                progress = 4 * progress ** 3
            else:
                progress = 1 - (-2 * progress + 2) ** 3 / 2

        # 插值视口状态
        start = self._animation_start_viewport
        target = self._target_viewport

        self._current_viewport.zoom_level = start.zoom_level + (target.zoom_level - start.zoom_level) * progress
        self._current_viewport.pan_x = start.pan_x + (target.pan_x - start.pan_x) * progress
        self._current_viewport.pan_y = start.pan_y + (target.pan_y - start.pan_y) * progress

        self.viewport_changed.emit(self._current_viewport)

        # 更新性能统计
        self._performance_stats['animation_frames'] += 1

    def _update_performance_stats(self, frame_time: float):
        """更新性能统计"""
        # 更新平均帧时间
        current_avg = self._performance_stats['average_frame_time']
        total_frames = self._performance_stats['animation_frames'] + self._performance_stats['total_interactions']

        if total_frames > 0:
            new_avg = (current_avg * (total_frames - 1) + frame_time) / total_frames
            self._performance_stats['average_frame_time'] = new_avg

        # 定期发送性能统计
        if self._performance_stats['total_interactions'] % 10 == 0:
            self.performance_stats.emit(self._performance_stats.copy())

    def reset_viewport(self):
        """重置视口"""
        self._target_viewport.zoom_level = 1.0
        self._target_viewport.pan_x = 0.0
        self._target_viewport.pan_y = 0.0

        if self._animation_enabled:
            self._start_animation()
        else:
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)

        self.interaction_started.emit("reset")

    def zoom_to_fit(self, data_bounds: Tuple[float, float, float, float]):
        """缩放以适应数据"""
        x_min, x_max, y_min, y_max = data_bounds

        # 重置视口
        self._target_viewport.x_min = x_min
        self._target_viewport.x_max = x_max
        self._target_viewport.y_min = y_min
        self._target_viewport.y_max = y_max
        self._target_viewport.zoom_level = 1.0
        self._target_viewport.pan_x = 0.0
        self._target_viewport.pan_y = 0.0

        if self._animation_enabled:
            self._start_animation()
        else:
            self._current_viewport = self._target_viewport.copy()
            self.viewport_changed.emit(self._current_viewport)

    def get_current_viewport(self) -> ViewportState:
        """获取当前视口状态"""
        return self._current_viewport.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self._performance_stats.copy()

    def set_animation_enabled(self, enabled: bool):
        """设置动画启用状态"""
        self._animation_enabled = enabled
        if not enabled and self._animation_timer.isActive():
            self._animation_timer.stop()

    def set_config(self, key: str, value: Any):
        """设置配置项"""
        if key in self.config:
            self.config[key] = value
            logger.debug(f"交互引擎配置更新: {key} = {value}")
