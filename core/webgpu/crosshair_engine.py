from loguru import logger
"""
GPU加速十字光标引擎模块

实现基于GPU加速的十字光标功能：
- 硬件加速的十字光标渲染
- 实时鼠标跟踪
- 价格和时间信息显示
- 平滑动画效果
- 性能优化
"""

import time
import threading
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QPointF, QRectF
from PyQt5.QtGui import QMouseEvent, QPainter, QPen, QColor, QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget

logger = logger


class CrosshairStyle(Enum):
    """十字光标样式"""
    SOLID = "solid"           # 实线
    DASHED = "dashed"         # 虚线
    DOTTED = "dotted"         # 点线
    CROSS_ONLY = "cross_only"  # 仅十字
    GRID = "grid"             # 网格


@dataclass
class CrosshairState:
    """十字光标状态"""
    x: float = 0.0
    y: float = 0.0
    visible: bool = False
    data_x: Optional[float] = None  # 数据坐标X
    data_y: Optional[float] = None  # 数据坐标Y
    timestamp: float = 0.0

    def copy(self) -> 'CrosshairState':
        """创建副本"""
        return CrosshairState(
            self.x, self.y, self.visible,
            self.data_x, self.data_y, self.timestamp
        )


@dataclass
class CrosshairConfig:
    """十字光标配置"""
    # 基础配置
    enabled: bool = True
    style: CrosshairStyle = CrosshairStyle.SOLID
    line_width: float = 1.0
    line_color: str = "#FFFFFF"
    line_alpha: float = 0.8

    # 动画配置
    smooth_animation: bool = True
    animation_duration: float = 100.0  # ms
    fade_duration: float = 200.0  # ms

    # 响应配置
    follow_mouse: bool = True
    snap_to_data: bool = True
    update_threshold: float = 2.0  # 像素

    # 标签配置
    show_labels: bool = True
    label_font_size: int = 10
    label_background: str = "#000000"
    label_text_color: str = "#FFFFFF"
    label_padding: int = 4

    # 性能配置
    max_fps: float = 60.0
    use_gpu_rendering: bool = True
    cache_labels: bool = True


class GPUCrosshairEngine(QObject):
    """GPU加速十字光标引擎"""

    # 信号
    crosshair_moved = pyqtSignal(object)  # CrosshairState
    crosshair_visibility_changed = pyqtSignal(bool)
    performance_stats = pyqtSignal(dict)  # 性能统计

    def __init__(self, webgpu_manager=None):
        super().__init__()

        self.webgpu_manager = webgpu_manager
        self._config = CrosshairConfig()
        self._current_state = CrosshairState()
        self._target_state = CrosshairState()

        # 渲染状态
        self._is_rendering = False
        self._last_render_time = 0.0
        self._render_cache = {}

        # 动画管理
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_start_time = 0.0
        self._animation_start_state = None

        # 性能监控
        self._performance_stats = {
            'total_updates': 0,
            'gpu_renders': 0,
            'cpu_fallbacks': 0,
            'average_render_time': 0.0,
            'fps': 0.0,
            'gpu_acceleration_enabled': bool(webgpu_manager)
        }

        # 数据转换缓存
        self._coord_transform_cache = {}
        self._label_cache = {}

        logger.info(f"GPU十字光标引擎初始化完成 - GPU加速: {self._performance_stats['gpu_acceleration_enabled']}")

    def update_mouse_position(self, x: float, y: float, widget: QWidget) -> bool:
        """更新鼠标位置"""
        try:
            current_time = time.time()

            # 检查更新阈值
            if self._config.update_threshold > 0:
                dx = abs(x - self._current_state.x)
                dy = abs(y - self._current_state.y)
                if dx < self._config.update_threshold and dy < self._config.update_threshold:
                    return False

            # 更新目标状态
            self._target_state.x = x
            self._target_state.y = y
            self._target_state.visible = True
            self._target_state.timestamp = current_time

            # 转换为数据坐标
            data_coords = self._convert_to_data_coordinates(x, y, widget)
            if data_coords:
                self._target_state.data_x, self._target_state.data_y = data_coords

            # 捕捉到数据点
            if self._config.snap_to_data:
                snapped_coords = self._snap_to_nearest_data_point(x, y, widget)
                if snapped_coords:
                    self._target_state.x, self._target_state.y = snapped_coords

            # 启动动画或直接更新
            if self._config.smooth_animation:
                self._start_animation()
            else:
                self._current_state = self._target_state.copy()
                self.crosshair_moved.emit(self._current_state)

            # 更新性能统计
            self._performance_stats['total_updates'] += 1
            self._update_fps_stats(current_time)

            return True

        except Exception as e:
            logger.error(f"更新鼠标位置失败: {e}")
            return False

    def set_visibility(self, visible: bool):
        """设置十字光标可见性"""
        if self._current_state.visible != visible:
            self._current_state.visible = visible
            self._target_state.visible = visible

            if visible:
                self._start_animation()
            else:
                self._start_fade_animation()

            self.crosshair_visibility_changed.emit(visible)

    def render_crosshair(self, painter: QPainter, widget: QWidget) -> bool:
        """渲染十字光标"""
        if not self._current_state.visible:
            return True

        start_time = time.time()

        try:
            # 尝试GPU渲染
            if self._config.use_gpu_rendering and self.webgpu_manager:
                if self._render_crosshair_gpu(painter, widget):
                    self._performance_stats['gpu_renders'] += 1
                    render_time = time.time() - start_time
                    self._update_performance_stats(render_time)
                    return True

            # CPU后备渲染
            self._render_crosshair_cpu(painter, widget)
            self._performance_stats['cpu_fallbacks'] += 1

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"渲染十字光标失败: {e}")
            return False

    def _render_crosshair_gpu(self, painter: QPainter, widget: QWidget) -> bool:
        """GPU加速渲染十字光标"""
        try:
            # 准备GPU渲染数据
            render_data = {
                'x': self._current_state.x,
                'y': self._current_state.y,
                'width': widget.width(),
                'height': widget.height(),
                'style': self._config.style.value,
                'line_width': self._config.line_width,
                'color': self._config.line_color,
                'alpha': self._config.line_alpha
            }

            # 检查缓存
            cache_key = self._generate_cache_key(render_data)
            if cache_key in self._render_cache:
                cached_result = self._render_cache[cache_key]
                # 使用缓存的GPU渲染结果
                self._apply_cached_render(painter, cached_result)
                return True

            # 调用WebGPU渲染器
            if self.webgpu_manager:
                # 模拟GPU渲染（实际项目中这里会调用WebGPU着色器）
                gpu_result = self._simulate_gpu_crosshair_render(render_data)

                # 缓存结果
                if self._config.cache_labels:
                    self._render_cache[cache_key] = gpu_result

                # 应用GPU渲染结果到QPainter
                self._apply_gpu_render_result(painter, gpu_result)
                return True

            return False

        except Exception as e:
            logger.warning(f"GPU十字光标渲染失败: {e}")
            return False

    def _render_crosshair_cpu(self, painter: QPainter, widget: QWidget):
        """CPU后备渲染十字光标"""
        state = self._current_state

        # 设置画笔
        pen = QPen()
        pen.setColor(QColor(self._config.line_color))
        pen.setWidthF(self._config.line_width)

        # 设置样式
        if self._config.style == CrosshairStyle.DASHED:
            pen.setStyle(2)  # Qt.DashLine
        elif self._config.style == CrosshairStyle.DOTTED:
            pen.setStyle(3)  # Qt.DotLine

        painter.setPen(pen)
        painter.setOpacity(self._config.line_alpha)

        # 绘制十字光标
        if self._config.style in [CrosshairStyle.SOLID, CrosshairStyle.DASHED, CrosshairStyle.DOTTED]:
            # 绘制垂直线
            painter.drawLine(int(state.x), 0, int(state.x), widget.height())
            # 绘制水平线
            painter.drawLine(0, int(state.y), widget.width(), int(state.y))

        elif self._config.style == CrosshairStyle.CROSS_ONLY:
            # 绘制十字（限制长度）
            cross_size = 20
            painter.drawLine(
                int(state.x - cross_size), int(state.y),
                int(state.x + cross_size), int(state.y)
            )
            painter.drawLine(
                int(state.x), int(state.y - cross_size),
                int(state.x), int(state.y + cross_size)
            )

        elif self._config.style == CrosshairStyle.GRID:
            # 绘制网格（简化版本）
            self._draw_grid(painter, widget)

        # 绘制标签
        if self._config.show_labels:
            self._draw_labels(painter, widget)

        painter.setOpacity(1.0)

    def _draw_grid(self, painter: QPainter, widget: QWidget):
        """绘制网格"""
        grid_spacing = 50  # 网格间距

        # 绘制垂直网格线
        for x in range(0, widget.width(), grid_spacing):
            painter.drawLine(x, 0, x, widget.height())

        # 绘制水平网格线
        for y in range(0, widget.height(), grid_spacing):
            painter.drawLine(0, y, widget.width(), y)

    def _draw_labels(self, painter: QPainter, widget: QWidget):
        """绘制标签"""
        state = self._current_state

        if not (state.data_x is not None and state.data_y is not None):
            return

        # 设置字体
        font = QFont()
        font.setPointSize(self._config.label_font_size)
        painter.setFont(font)

        # 准备标签文本
        x_label = f"X: {state.data_x:.2f}" if state.data_x else "X: --"
        y_label = f"Y: {state.data_y:.2f}" if state.data_y else "Y: --"

        # 计算标签尺寸
        fm = QFontMetrics(font)
        x_label_rect = fm.boundingRect(x_label)
        y_label_rect = fm.boundingRect(y_label)

        padding = self._config.label_padding

        # X轴标签位置
        x_label_x = state.x - x_label_rect.width() / 2
        x_label_y = widget.height() - x_label_rect.height() - padding

        # Y轴标签位置
        y_label_x = padding
        y_label_y = state.y - y_label_rect.height() / 2

        # 绘制标签背景
        painter.fillRect(
            QRectF(x_label_x - padding, x_label_y - padding,
                   x_label_rect.width() + 2 * padding,
                   x_label_rect.height() + 2 * padding),
            QColor(self._config.label_background)
        )

        painter.fillRect(
            QRectF(y_label_x - padding, y_label_y - padding,
                   y_label_rect.width() + 2 * padding,
                   y_label_rect.height() + 2 * padding),
            QColor(self._config.label_background)
        )

        # 绘制标签文本
        painter.setPen(QColor(self._config.label_text_color))
        painter.drawText(QPointF(x_label_x, x_label_y + x_label_rect.height()), x_label)
        painter.drawText(QPointF(y_label_x, y_label_y + y_label_rect.height()), y_label)

    def _simulate_gpu_crosshair_render(self, render_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟GPU十字光标渲染"""
        # 在实际项目中，这里会调用WebGPU着色器进行渲染
        # 现在返回模拟的GPU渲染结果
        return {
            'render_type': 'gpu_crosshair',
            'lines': [
                # 垂直线
                {'x1': render_data['x'], 'y1': 0, 'x2': render_data['x'], 'y2': render_data['height']},
                # 水平线
                {'x1': 0, 'y1': render_data['y'], 'x2': render_data['width'], 'y2': render_data['y']}
            ],
            'style': render_data['style'],
            'color': render_data['color'],
            'line_width': render_data['line_width'],
            'alpha': render_data['alpha']
        }

    def _apply_gpu_render_result(self, painter: QPainter, gpu_result: Dict[str, Any]):
        """应用GPU渲染结果到QPainter"""
        # 将GPU渲染结果转换为QPainter绘制命令
        pen = QPen()
        pen.setColor(QColor(gpu_result['color']))
        pen.setWidthF(gpu_result['line_width'])

        painter.setPen(pen)
        painter.setOpacity(gpu_result['alpha'])

        for line in gpu_result['lines']:
            painter.drawLine(
                int(line['x1']), int(line['y1']),
                int(line['x2']), int(line['y2'])
            )

        painter.setOpacity(1.0)

    def _apply_cached_render(self, painter: QPainter, cached_result: Dict[str, Any]):
        """应用缓存的渲染结果"""
        self._apply_gpu_render_result(painter, cached_result)

    def _convert_to_data_coordinates(self, x: float, y: float, widget: QWidget) -> Optional[Tuple[float, float]]:
        """转换屏幕坐标到数据坐标"""
        try:
            # 这里需要根据实际的图表坐标系统进行转换
            # 现在返回模拟的数据坐标

            # 假设图表范围
            data_x_min, data_x_max = 0, 100
            data_y_min, data_y_max = 0, 50

            # 转换坐标
            rel_x = x / widget.width() if widget.width() > 0 else 0
            rel_y = (widget.height() - y) / widget.height() if widget.height() > 0 else 0

            data_x = data_x_min + rel_x * (data_x_max - data_x_min)
            data_y = data_y_min + rel_y * (data_y_max - data_y_min)

            return (data_x, data_y)

        except Exception as e:
            logger.warning(f"坐标转换失败: {e}")
            return None

    def _snap_to_nearest_data_point(self, x: float, y: float, widget: QWidget) -> Optional[Tuple[float, float]]:
        """捕捉到最近的数据点"""
        try:
            # 这里需要根据实际的数据点进行捕捉
            # 现在返回原始坐标（不捕捉）
            return None

        except Exception as e:
            logger.warning(f"数据点捕捉失败: {e}")
            return None

    def _start_animation(self):
        """启动动画"""
        if not self._config.smooth_animation:
            return

        self._animation_start_time = time.time()
        self._animation_start_state = self._current_state.copy()

        if not self._animation_timer.isActive():
            frame_interval = int(1000 / self._config.max_fps)  # ms
            self._animation_timer.start(frame_interval)

    def _start_fade_animation(self):
        """启动淡出动画"""
        if not self._config.smooth_animation:
            self._current_state.visible = False
            return

        # 实现淡出逻辑
        self._start_animation()

    def _update_animation(self):
        """更新动画"""
        if not self._animation_start_state:
            self._animation_timer.stop()
            return

        current_time = time.time()
        elapsed = (current_time - self._animation_start_time) * 1000  # ms

        if elapsed >= self._config.animation_duration:
            # 动画完成
            self._current_state = self._target_state.copy()
            self.crosshair_moved.emit(self._current_state)
            self._animation_timer.stop()
            self._animation_start_state = None
            return

        # 计算插值进度
        progress = elapsed / self._config.animation_duration
        progress = min(1.0, max(0.0, progress))

        # 应用缓动函数（ease-out）
        progress = 1 - (1 - progress) ** 2

        # 插值位置
        start = self._animation_start_state
        target = self._target_state

        self._current_state.x = start.x + (target.x - start.x) * progress
        self._current_state.y = start.y + (target.y - start.y) * progress
        self._current_state.visible = target.visible

        # 插值数据坐标
        if start.data_x is not None and target.data_x is not None:
            self._current_state.data_x = start.data_x + (target.data_x - start.data_x) * progress
        else:
            self._current_state.data_x = target.data_x

        if start.data_y is not None and target.data_y is not None:
            self._current_state.data_y = start.data_y + (target.data_y - start.data_y) * progress
        else:
            self._current_state.data_y = target.data_y

        self.crosshair_moved.emit(self._current_state)

    def _generate_cache_key(self, render_data: Dict[str, Any]) -> str:
        """生成缓存键"""
        key_parts = [
            f"x:{render_data['x']:.1f}",
            f"y:{render_data['y']:.1f}",
            f"w:{render_data['width']}",
            f"h:{render_data['height']}",
            f"s:{render_data['style']}",
            f"lw:{render_data['line_width']}",
            f"c:{render_data['color']}",
            f"a:{render_data['alpha']:.2f}"
        ]
        return "|".join(key_parts)

    def _update_performance_stats(self, render_time: float):
        """更新性能统计"""
        # 更新平均渲染时间
        total_renders = self._performance_stats['gpu_renders'] + self._performance_stats['cpu_fallbacks']
        if total_renders > 0:
            current_avg = self._performance_stats['average_render_time']
            new_avg = (current_avg * (total_renders - 1) + render_time) / total_renders
            self._performance_stats['average_render_time'] = new_avg

        # 定期发送性能统计
        if total_renders % 30 == 0:  # 每30次渲染发送一次
            self.performance_stats.emit(self._performance_stats.copy())

    def _update_fps_stats(self, current_time: float):
        """更新FPS统计"""
        if self._last_render_time > 0:
            frame_time = current_time - self._last_render_time
            if frame_time > 0:
                fps = 1.0 / frame_time
                # 平滑FPS计算
                current_fps = self._performance_stats['fps']
                if current_fps > 0:
                    self._performance_stats['fps'] = current_fps * 0.9 + fps * 0.1
                else:
                    self._performance_stats['fps'] = fps

        self._last_render_time = current_time

    def get_current_state(self) -> CrosshairState:
        """获取当前状态"""
        return self._current_state.copy()

    def get_config(self) -> CrosshairConfig:
        """获取配置"""
        return self._config

    def update_config(self, config: CrosshairConfig):
        """更新配置"""
        self._config = config
        # 清除缓存
        self._render_cache.clear()
        self._coord_transform_cache.clear()
        self._label_cache.clear()

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self._performance_stats.copy()

    def clear_cache(self):
        """清除缓存"""
        self._render_cache.clear()
        self._coord_transform_cache.clear()
        self._label_cache.clear()

    def reset(self):
        """重置引擎状态"""
        self._current_state = CrosshairState()
        self._target_state = CrosshairState()
        self._animation_timer.stop()
        self._animation_start_state = None
        self.clear_cache()
