"""
GPU增强十字光标Mixin模块

提供基于GPU加速的十字光标功能：
- 集成GPU十字光标引擎
- 硬件加速的十字光标渲染
- 实时鼠标跟踪
- 价格和时间信息显示
- 性能监控和优化
"""

import logging
from typing import Optional, Dict, Any, Tuple
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtGui import QMouseEvent, QPainter
from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class GPUEnhancedCrosshairMixin:
    """GPU增强十字光标功能Mixin"""

    # 新增信号
    gpu_crosshair_moved = pyqtSignal(object)  # CrosshairState
    gpu_crosshair_performance = pyqtSignal(dict)  # 性能统计

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # GPU十字光标引擎
        self._gpu_crosshair_engine = None
        self._gpu_crosshair_enabled = True
        self._fallback_to_cpu = True

        # 性能监控
        self._gpu_crosshair_stats = {
            'gpu_renders': 0,
            'cpu_fallbacks': 0,
            'average_gpu_render_time': 0.0,
            'average_cpu_render_time': 0.0,
            'fps': 0.0
        }

        # 状态管理
        self._crosshair_visible = False
        self._last_mouse_position = None
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._delayed_crosshair_update)
        self._update_timer.setSingleShot(True)

        # 初始化GPU十字光标引擎
        self._initialize_gpu_crosshair()

    def _initialize_gpu_crosshair(self):
        """初始化GPU十字光标引擎"""
        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine
            from core.webgpu import get_webgpu_manager

            # 获取WebGPU管理器（如果可用）
            webgpu_manager = None
            try:
                webgpu_manager = get_webgpu_manager()
            except Exception as e:
                logger.warning(f"无法获取WebGPU管理器: {e}")

            # 创建GPU十字光标引擎
            self._gpu_crosshair_engine = GPUCrosshairEngine(webgpu_manager)

            # 连接信号
            self._gpu_crosshair_engine.crosshair_moved.connect(self._on_gpu_crosshair_moved)
            self._gpu_crosshair_engine.crosshair_visibility_changed.connect(self._on_gpu_crosshair_visibility_changed)
            self._gpu_crosshair_engine.performance_stats.connect(self._on_gpu_crosshair_performance)

            logger.info("GPU十字光标引擎初始化成功")

        except ImportError as e:
            logger.warning(f"GPU十字光标引擎不可用，将使用CPU后备: {e}")
            self._gpu_crosshair_engine = None
            self._gpu_crosshair_enabled = False
        except Exception as e:
            logger.error(f"GPU十字光标引擎初始化失败: {e}")
            self._gpu_crosshair_engine = None
            self._gpu_crosshair_enabled = False

    def _on_gpu_crosshair_moved(self, crosshair_state):
        """GPU十字光标移动回调"""
        # 触发重绘
        if hasattr(self, 'update'):
            self.update()

        # 发送信号
        self.gpu_crosshair_moved.emit(crosshair_state)

    def _on_gpu_crosshair_visibility_changed(self, visible: bool):
        """GPU十字光标可见性变化回调"""
        self._crosshair_visible = visible

        # 触发重绘
        if hasattr(self, 'update'):
            self.update()

    def _on_gpu_crosshair_performance(self, stats: Dict[str, Any]):
        """GPU十字光标性能统计回调"""
        self._gpu_crosshair_stats.update(stats)
        self.gpu_crosshair_performance.emit(stats)

    def mouseMoveEvent(self, event: QMouseEvent):
        """重写鼠标移动事件处理"""
        # 处理GPU十字光标
        if self._gpu_crosshair_enabled and self._gpu_crosshair_engine and self._crosshair_visible:
            try:
                x, y = event.x(), event.y()
                self._last_mouse_position = (x, y)

                # 延迟更新以减少频繁调用
                if not self._update_timer.isActive():
                    self._update_timer.start(16)  # ~60 FPS

                self._gpu_crosshair_stats['gpu_renders'] += 1

            except Exception as e:
                logger.warning(f"GPU十字光标鼠标移动处理失败: {e}")
                self._gpu_crosshair_stats['cpu_fallbacks'] += 1

        # 调用父类处理
        if hasattr(super(), 'mouseMoveEvent'):
            super().mouseMoveEvent(event)

    def paintEvent(self, event):
        """重写绘制事件"""
        # 调用父类绘制
        if hasattr(super(), 'paintEvent'):
            super().paintEvent(event)

        # 绘制GPU十字光标
        if self._gpu_crosshair_enabled and self._gpu_crosshair_engine and self._crosshair_visible:
            painter = QPainter(self)
            try:
                self._gpu_crosshair_engine.render_crosshair(painter, self)
            except Exception as e:
                logger.warning(f"GPU十字光标绘制失败: {e}")
                # CPU后备绘制
                self._render_crosshair_cpu_fallback(painter)
            finally:
                painter.end()

    def _delayed_crosshair_update(self):
        """延迟的十字光标更新"""
        if self._last_mouse_position and self._gpu_crosshair_engine:
            x, y = self._last_mouse_position
            self._gpu_crosshair_engine.update_mouse_position(x, y, self)

    def _render_crosshair_cpu_fallback(self, painter: QPainter):
        """CPU后备十字光标渲染"""
        import time
        start_time = time.time()

        try:
            if not self._last_mouse_position:
                return

            x, y = self._last_mouse_position

            # 简单的十字光标绘制
            from PyQt5.QtGui import QPen, QColor

            pen = QPen(QColor("#FFFFFF"))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setOpacity(0.8)

            # 绘制垂直线
            painter.drawLine(int(x), 0, int(x), self.height())
            # 绘制水平线
            painter.drawLine(0, int(y), self.width(), int(y))

            painter.setOpacity(1.0)

        except Exception as e:
            logger.error(f"CPU后备十字光标渲染失败: {e}")

        # 更新性能统计
        render_time = time.time() - start_time
        current_avg = self._gpu_crosshair_stats['average_cpu_render_time']
        cpu_fallbacks = self._gpu_crosshair_stats['cpu_fallbacks']
        if cpu_fallbacks > 0:
            new_avg = (current_avg * (cpu_fallbacks - 1) + render_time) / cpu_fallbacks
            self._gpu_crosshair_stats['average_cpu_render_time'] = new_avg

    def enable_gpu_crosshair(self):
        """启用GPU十字光标"""
        if self._gpu_crosshair_engine:
            self._gpu_crosshair_engine.set_visibility(True)
            self._crosshair_visible = True
            logger.info("GPU十字光标已启用")
        else:
            logger.warning("GPU十字光标引擎不可用")

    def disable_gpu_crosshair(self):
        """禁用GPU十字光标"""
        if self._gpu_crosshair_engine:
            self._gpu_crosshair_engine.set_visibility(False)
            self._crosshair_visible = False
            logger.info("GPU十字光标已禁用")

    def toggle_gpu_crosshair(self):
        """切换GPU十字光标状态"""
        if self._crosshair_visible:
            self.disable_gpu_crosshair()
        else:
            self.enable_gpu_crosshair()

    def set_gpu_crosshair_style(self, style: str):
        """设置GPU十字光标样式"""
        if self._gpu_crosshair_engine:
            from core.webgpu.crosshair_engine import CrosshairStyle
            try:
                style_enum = CrosshairStyle(style.lower())
                config = self._gpu_crosshair_engine.get_config()
                config.style = style_enum
                self._gpu_crosshair_engine.update_config(config)
                logger.info(f"GPU十字光标样式已设置为: {style}")
            except ValueError:
                logger.error(f"无效的十字光标样式: {style}")

    def set_gpu_crosshair_color(self, color: str):
        """设置GPU十字光标颜色"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.line_color = color
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标颜色已设置为: {color}")

    def set_gpu_crosshair_width(self, width: float):
        """设置GPU十字光标线宽"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.line_width = width
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标线宽已设置为: {width}")

    def set_gpu_crosshair_alpha(self, alpha: float):
        """设置GPU十字光标透明度"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.line_alpha = max(0.0, min(1.0, alpha))
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标透明度已设置为: {alpha}")

    def set_gpu_crosshair_animation(self, enabled: bool):
        """设置GPU十字光标动画"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.smooth_animation = enabled
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标动画{'启用' if enabled else '禁用'}")

    def set_gpu_crosshair_labels(self, enabled: bool):
        """设置GPU十字光标标签显示"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.show_labels = enabled
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标标签{'启用' if enabled else '禁用'}")

    def set_gpu_crosshair_snap_to_data(self, enabled: bool):
        """设置GPU十字光标数据捕捉"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            config.snap_to_data = enabled
            self._gpu_crosshair_engine.update_config(config)
            logger.info(f"GPU十字光标数据捕捉{'启用' if enabled else '禁用'}")

    def get_gpu_crosshair_state(self):
        """获取GPU十字光标当前状态"""
        if self._gpu_crosshair_engine:
            return self._gpu_crosshair_engine.get_current_state()
        return None

    def get_gpu_crosshair_config(self) -> Dict[str, Any]:
        """获取GPU十字光标配置"""
        if self._gpu_crosshair_engine:
            config = self._gpu_crosshair_engine.get_config()
            return {
                'enabled': config.enabled,
                'style': config.style.value,
                'line_width': config.line_width,
                'line_color': config.line_color,
                'line_alpha': config.line_alpha,
                'smooth_animation': config.smooth_animation,
                'show_labels': config.show_labels,
                'snap_to_data': config.snap_to_data,
                'use_gpu_rendering': config.use_gpu_rendering
            }
        return {}

    def get_gpu_crosshair_performance_stats(self) -> Dict[str, Any]:
        """获取GPU十字光标性能统计"""
        stats = self._gpu_crosshair_stats.copy()

        if self._gpu_crosshair_engine:
            engine_stats = self._gpu_crosshair_engine.get_performance_stats()
            stats.update(engine_stats)

        return stats

    def reset_gpu_crosshair_stats(self):
        """重置GPU十字光标统计"""
        self._gpu_crosshair_stats = {
            'gpu_renders': 0,
            'cpu_fallbacks': 0,
            'average_gpu_render_time': 0.0,
            'average_cpu_render_time': 0.0,
            'fps': 0.0
        }

        if self._gpu_crosshair_engine:
            # 重置引擎统计（如果引擎支持的话）
            pass

    def is_gpu_crosshair_available(self) -> bool:
        """检查GPU十字光标是否可用"""
        return self._gpu_crosshair_engine is not None

    def is_gpu_crosshair_visible(self) -> bool:
        """检查GPU十字光标是否可见"""
        return self._crosshair_visible

    def clear_gpu_crosshair_cache(self):
        """清除GPU十字光标缓存"""
        if self._gpu_crosshair_engine:
            self._gpu_crosshair_engine.clear_cache()

    def reset_gpu_crosshair(self):
        """重置GPU十字光标"""
        if self._gpu_crosshair_engine:
            self._gpu_crosshair_engine.reset()
            self._crosshair_visible = False
            self._last_mouse_position = None

    def update_gpu_crosshair_config(self, config_dict: Dict[str, Any]):
        """批量更新GPU十字光标配置"""
        if not self._gpu_crosshair_engine:
            return

        config = self._gpu_crosshair_engine.get_config()

        # 更新配置项
        if 'style' in config_dict:
            from core.webgpu.crosshair_engine import CrosshairStyle
            try:
                config.style = CrosshairStyle(config_dict['style'].lower())
            except ValueError:
                logger.error(f"无效的十字光标样式: {config_dict['style']}")

        if 'line_width' in config_dict:
            config.line_width = float(config_dict['line_width'])

        if 'line_color' in config_dict:
            config.line_color = str(config_dict['line_color'])

        if 'line_alpha' in config_dict:
            config.line_alpha = max(0.0, min(1.0, float(config_dict['line_alpha'])))

        if 'smooth_animation' in config_dict:
            config.smooth_animation = bool(config_dict['smooth_animation'])

        if 'show_labels' in config_dict:
            config.show_labels = bool(config_dict['show_labels'])

        if 'snap_to_data' in config_dict:
            config.snap_to_data = bool(config_dict['snap_to_data'])

        if 'use_gpu_rendering' in config_dict:
            config.use_gpu_rendering = bool(config_dict['use_gpu_rendering'])

        # 应用配置
        self._gpu_crosshair_engine.update_config(config)
        logger.info("GPU十字光标配置已批量更新")
