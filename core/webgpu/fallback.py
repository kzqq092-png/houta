from loguru import logger
"""
多层降级渲染器模块

提供完整的渲染后备方案：
WebGPU → OpenGL → Canvas 2D → matplotlib

确保在任何环境下都能正常工作
"""

import time
from typing import Dict, Any, Optional, Protocol, List
from abc import ABC, abstractmethod
from enum import Enum
import numpy as np
import pandas as pd

from .environment import GPUSupportLevel
from .compatibility import CompatibilityReport

logger = logger


class RenderBackend(Enum):
    """渲染后端类型"""
    WEBGPU = "webgpu"
    OPENGL = "opengl"
    WEBGL = "webgl"
    CANVAS2D = "canvas2d"
    MATPLOTLIB = "matplotlib"


class ChartRenderer(Protocol):
    """图表渲染器协议"""

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        ...

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        ...

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        ...

    def clear(self) -> None:
        """清空渲染内容"""
        ...

    def get_performance_info(self) -> Dict[str, Any]:
        """获取性能信息"""
        ...


class BaseRenderer(ABC):
    """渲染器基类"""

    def __init__(self, backend: RenderBackend):
        self.backend = backend
        self._initialized = False
        self._performance_stats = {
            'render_count': 0,
            'total_render_time': 0.0,
            'average_render_time': 0.0,
            'last_render_time': 0.0,
            'memory_usage_mb': 0.0
        }

    @abstractmethod
    def initialize(self, context: Optional[Any] = None) -> bool:
        """初始化渲染器"""
        pass

    @abstractmethod
    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        pass

    @abstractmethod
    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        pass

    @abstractmethod
    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空渲染内容"""
        pass

    def get_performance_info(self) -> Dict[str, Any]:
        """获取性能信息"""
        return {
            'backend': self.backend.value,
            'initialized': self._initialized,
            **self._performance_stats
        }

    def _update_performance_stats(self, render_time: float):
        """更新性能统计"""
        self._performance_stats['render_count'] += 1
        self._performance_stats['total_render_time'] += render_time
        self._performance_stats['last_render_time'] = render_time
        self._performance_stats['average_render_time'] = (
            self._performance_stats['total_render_time'] /
            self._performance_stats['render_count']
        )


class WebGPURenderer(BaseRenderer):
    """WebGPU渲染器"""

    def __init__(self):
        super().__init__(RenderBackend.WEBGPU)
        self._device = None
        self._context = None
        self._pipeline = None

    def initialize(self, context: Optional[Any] = None) -> bool:
        """初始化WebGPU渲染器"""
        try:
            logger.info("初始化WebGPU渲染器...")

            # 实际项目中这里会初始化WebGPU设备和上下文
            # 现在使用模拟实现
            self._context = context or {"type": "webgpu"}

            # 模拟WebGPU设备创建
            self._device = {"type": "webgpu_device"}

            # 创建渲染管道
            self._pipeline = self._create_render_pipeline()

            self._initialized = True
            logger.info("WebGPU渲染器初始化成功")
            return True

        except Exception as e:
            logger.error(f"WebGPU渲染器初始化失败: {e}")
            return False

    def _create_render_pipeline(self) -> Dict[str, Any]:
        """创建渲染管道"""
        # 模拟WebGPU渲染管道创建
        return {
            "vertex_shader": "webgpu_vertex_shader",
            "fragment_shader": "webgpu_fragment_shader",
            "buffer_layout": "webgpu_buffer_layout"
        }

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        if not self._initialized:
            return False

        try:
            import time
            start_time = time.time()

            # 模拟WebGPU K线渲染
            logger.debug(f"WebGPU渲染K线图: {len(data)}个数据点")

            # 实际项目中这里会：
            # 1. 准备顶点数据
            # 2. 创建顶点缓冲区
            # 3. 设置渲染管道
            # 4. 执行绘制命令

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"WebGPU K线渲染失败: {e}")
            return False

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"WebGPU渲染成交量: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"WebGPU成交量渲染失败: {e}")
            return False

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"WebGPU渲染线图: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"WebGPU线图渲染失败: {e}")
            return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._initialized:
            logger.debug("WebGPU清空渲染内容")


class OpenGLRenderer(BaseRenderer):
    """OpenGL渲染器"""

    def __init__(self):
        super().__init__(RenderBackend.OPENGL)
        self._gl_context = None

    def initialize(self, context: Optional[Any] = None) -> bool:
        """初始化OpenGL渲染器"""
        try:
            logger.info("初始化OpenGL渲染器...")

            # 尝试导入OpenGL
            try:
                import OpenGL.GL as gl
                self._gl_context = gl
                self._initialized = True
                logger.info("OpenGL渲染器初始化成功")
                return True
            except ImportError:
                logger.warning("OpenGL库未安装")
                return False

        except Exception as e:
            logger.error(f"OpenGL渲染器初始化失败: {e}")
            return False

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"OpenGL渲染K线图: {len(data)}个数据点")

            # 实际项目中这里会使用OpenGL API绘制

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"OpenGL K线渲染失败: {e}")
            return False

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"OpenGL渲染成交量: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"OpenGL成交量渲染失败: {e}")
            return False

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"OpenGL渲染线图: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"OpenGL线图渲染失败: {e}")
            return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._initialized:
            logger.debug("OpenGL清空渲染内容")


class Canvas2DRenderer(BaseRenderer):
    """Canvas 2D渲染器"""

    def __init__(self):
        super().__init__(RenderBackend.CANVAS2D)
        self._canvas = None

    def initialize(self, context: Optional[Any] = None) -> bool:
        """初始化Canvas 2D渲染器"""
        try:
            logger.info("初始化Canvas 2D渲染器...")

            # 模拟Canvas 2D上下文创建
            self._canvas = {"type": "canvas2d", "context": context}

            self._initialized = True
            logger.info("Canvas 2D渲染器初始化成功")
            return True

        except Exception as e:
            logger.error(f"Canvas 2D渲染器初始化失败: {e}")
            return False

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Canvas 2D渲染K线图: {len(data)}个数据点")

            # 实际项目中这里会使用Canvas 2D API绘制

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Canvas 2D K线渲染失败: {e}")
            return False

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Canvas 2D渲染成交量: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Canvas 2D成交量渲染失败: {e}")
            return False

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Canvas 2D渲染线图: {len(data)}个数据点")

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Canvas 2D线图渲染失败: {e}")
            return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._initialized:
            logger.debug("Canvas 2D清空渲染内容")


class MatplotlibRenderer(BaseRenderer):
    """Matplotlib渲染器（最终后备方案）"""

    def __init__(self):
        super().__init__(RenderBackend.MATPLOTLIB)
        self._figure = None
        self._axes = None

    def initialize(self, context: Optional[Any] = None) -> bool:
        """初始化Matplotlib渲染器"""
        try:
            logger.info("初始化Matplotlib渲染器...")

            # 使用现有的图表组件
            if context and hasattr(context, 'figure'):
                self._figure = context.figure
                if hasattr(context, 'price_ax'):
                    self._axes = {
                        'price': context.price_ax,
                        'volume': getattr(context, 'volume_ax', None),
                        'indicator': getattr(context, 'indicator_ax', None)
                    }

            self._initialized = True
            logger.info("Matplotlib渲染器初始化成功")
            return True

        except Exception as e:
            logger.error(f"Matplotlib渲染器初始化失败: {e}")
            return False

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Matplotlib渲染K线图: {len(data)}个数据点")

            # 使用现有的ChartRenderer实现
            if self._axes and 'price' in self._axes:
                ax = self._axes['price']
                x = np.arange(len(data))

                # 简化的K线绘制
                for i, (idx, row) in enumerate(data.iterrows()):
                    color = 'red' if row['close'] >= row['open'] else 'green'
                    ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.5)
                    ax.plot([i, i], [row['open'], row['close']], color=color, linewidth=2)

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Matplotlib K线渲染失败: {e}")
            return False

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Matplotlib渲染成交量: {len(data)}个数据点")

            if self._axes and 'volume' in self._axes and self._axes['volume']:
                ax = self._axes['volume']
                x = np.arange(len(data))
                ax.bar(x, data['volume'], width=0.8)

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Matplotlib成交量渲染失败: {e}")
            return False

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        if not self._initialized:
            return False

        try:
            start_time = time.time()

            logger.debug(f"Matplotlib渲染线图: {len(data)}个数据点")

            if self._axes and 'indicator' in self._axes and self._axes['indicator']:
                ax = self._axes['indicator']
                x = np.arange(len(data))
                color = style.get('color', 'blue')
                ax.plot(x, data, color=color, linewidth=1.0)

            render_time = time.time() - start_time
            self._update_performance_stats(render_time)

            return True

        except Exception as e:
            logger.error(f"Matplotlib线图渲染失败: {e}")
            return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._initialized and self._axes:
            for ax in self._axes.values():
                if ax:
                    ax.clear()
            logger.debug("Matplotlib清空渲染内容")


class FallbackRenderer:
    """多层降级渲染器"""

    def __init__(self):
        self._renderers = {}
        self._current_renderer = None
        self._fallback_chain = []
        self._failure_count = {}

        # 创建所有渲染器实例
        self._create_renderers()

    def _create_renderers(self):
        """创建所有渲染器实例"""
        self._renderers = {
            RenderBackend.WEBGPU: WebGPURenderer(),
            RenderBackend.OPENGL: OpenGLRenderer(),
            RenderBackend.CANVAS2D: Canvas2DRenderer(),
            RenderBackend.MATPLOTLIB: MatplotlibRenderer()
        }

        # 初始化失败计数
        for backend in RenderBackend:
            self._failure_count[backend] = 0

    def initialize(self, compatibility_report: CompatibilityReport, context: Optional[Any] = None) -> bool:
        """
        根据兼容性报告初始化渲染器

        Args:
            compatibility_report: 兼容性报告
            context: 渲染上下文

        Returns:
            是否初始化成功
        """
        logger.info("初始化多层降级渲染器...")

        # 确定降级链
        self._fallback_chain = self._determine_fallback_chain(compatibility_report)

        # 尝试按照降级链初始化渲染器
        for backend in self._fallback_chain:
            renderer = self._renderers[backend]

            logger.info(f"尝试初始化 {backend.value} 渲染器...")

            if renderer.initialize(context):
                self._current_renderer = renderer
                logger.info(f"使用 {backend.value} 渲染器")
                return True
            else:
                logger.warning(f"{backend.value} 渲染器初始化失败")
                self._failure_count[backend] += 1

        logger.error("所有渲染器初始化失败")
        return False

    def _determine_fallback_chain(self, compatibility_report: CompatibilityReport) -> List[RenderBackend]:
        """确定降级链"""

        # 根据推荐后端确定起始点
        recommended = compatibility_report.recommended_backend

        if recommended == GPUSupportLevel.WEBGPU:
            return [RenderBackend.WEBGPU, RenderBackend.OPENGL,
                    RenderBackend.CANVAS2D, RenderBackend.MATPLOTLIB]
        elif recommended == GPUSupportLevel.WEBGL:
            return [RenderBackend.CANVAS2D, RenderBackend.OPENGL,
                    RenderBackend.MATPLOTLIB]
        elif recommended == GPUSupportLevel.NATIVE:
            return [RenderBackend.OPENGL, RenderBackend.CANVAS2D,
                    RenderBackend.MATPLOTLIB]
        else:  # BASIC
            return [RenderBackend.MATPLOTLIB]

    def render_candlesticks(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染K线图"""
        return self._render_with_fallback('render_candlesticks', data, style)

    def render_volume(self, data: pd.DataFrame, style: Dict[str, Any]) -> bool:
        """渲染成交量"""
        return self._render_with_fallback('render_volume', data, style)

    def render_line(self, data: pd.Series, style: Dict[str, Any]) -> bool:
        """渲染线图"""
        return self._render_with_fallback('render_line', data, style)

    def _render_with_fallback(self, method_name: str, *args, **kwargs) -> bool:
        """带降级的渲染"""
        if not self._current_renderer:
            logger.error("没有可用的渲染器")
            return False

        try:
            # 尝试使用当前渲染器
            method = getattr(self._current_renderer, method_name)
            if method(*args, **kwargs):
                return True
            else:
                logger.warning(f"当前渲染器 {self._current_renderer.backend.value} 渲染失败")
                return self._try_fallback(method_name, *args, **kwargs)

        except Exception as e:
            logger.error(f"渲染器 {self._current_renderer.backend.value} 渲染异常: {e}")
            self._failure_count[self._current_renderer.backend] += 1
            return self._try_fallback(method_name, *args, **kwargs)

    def _try_fallback(self, method_name: str, *args, **kwargs) -> bool:
        """尝试降级渲染"""
        current_backend = self._current_renderer.backend

        # 在降级链中找到当前渲染器的位置
        try:
            current_index = self._fallback_chain.index(current_backend)
        except ValueError:
            current_index = -1

        # 尝试后续的渲染器
        for i in range(current_index + 1, len(self._fallback_chain)):
            backend = self._fallback_chain[i]
            renderer = self._renderers[backend]

            logger.info(f"降级到 {backend.value} 渲染器")

            # 如果渲染器未初始化，尝试初始化
            if not renderer._initialized:
                if not renderer.initialize():
                    continue

            try:
                method = getattr(renderer, method_name)
                if method(*args, **kwargs):
                    self._current_renderer = renderer
                    logger.info(f"降级到 {backend.value} 渲染器成功")
                    return True
            except Exception as e:
                logger.warning(f"降级渲染器 {backend.value} 也失败: {e}")
                self._failure_count[backend] += 1
                continue

        logger.error("所有降级渲染器都失败")
        return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._current_renderer:
            self._current_renderer.clear()

    def get_current_backend(self) -> Optional[RenderBackend]:
        """获取当前使用的渲染后端"""
        return self._current_renderer.backend if self._current_renderer else None

    def get_performance_info(self) -> Dict[str, Any]:
        """获取性能信息"""
        info = {
            'current_backend': self.get_current_backend().value if self.get_current_backend() else None,
            'fallback_chain': [backend.value for backend in self._fallback_chain],
            'failure_counts': {backend.value: count for backend, count in self._failure_count.items()},
            'renderers': {}
        }

        # 收集各个渲染器的性能信息
        for backend, renderer in self._renderers.items():
            info['renderers'][backend.value] = renderer.get_performance_info()

        return info

    def force_fallback(self, target_backend: RenderBackend = None) -> bool:
        """强制降级到指定后端"""
        if target_backend is None:
            # 降级到下一个后端
            current_backend = self._current_renderer.backend
            try:
                current_index = self._fallback_chain.index(current_backend)
                if current_index + 1 < len(self._fallback_chain):
                    target_backend = self._fallback_chain[current_index + 1]
                else:
                    logger.warning("已经是最后一个后端，无法继续降级")
                    return False
            except ValueError:
                logger.error("当前后端不在降级链中")
                return False

        # 切换到目标后端
        if target_backend in self._renderers:
            target_renderer = self._renderers[target_backend]
            if target_renderer._initialized or target_renderer.initialize():
                self._current_renderer = target_renderer
                logger.info(f"强制切换到 {target_backend.value} 渲染器")
                return True

        logger.error(f"无法切换到 {target_backend.value} 渲染器")
        return False
