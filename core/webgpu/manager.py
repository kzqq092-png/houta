from loguru import logger
"""
WebGPU管理器模块

负责整合所有WebGPU组件：
- 环境检测和初始化
- 兼容性检查
- 渲染器管理
- 降级处理
"""

import threading
import time
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from .environment import WebGPUEnvironment, get_webgpu_environment, GPUSupportLevel
from .fallback import FallbackRenderer, RenderBackend
from .webgpu_renderer import WebGPURenderer, GPUResourcePool
from .compatibility import GPUCompatibilityChecker, CompatibilityReport, CompatibilityLevel


@dataclass
class WebGPUConfig:
    """WebGPU配置"""
    auto_initialize: bool = True
    enable_fallback: bool = True
    auto_fallback_on_error: bool = True
    max_fallback_attempts: int = 3

class WebGPUManager:
    """WebGPU管理器

    提供统一的WebGPU硬件加速渲染接口，包括：
    - 自动环境检测和初始化
    - 兼容性检查和优化建议
    - 多层降级渲染
    - 性能监控和优化
    """

    def __init__(self, config: Optional[WebGPUConfig] = None):
        self.config = config or WebGPUConfig()

        # 核心组件
        self._environment = None
        self._webgpu_renderer = None  # ✅ 新增：真正的WebGPU渲染器
        self._fallback_renderer = None
        self._compatibility_checker = GPUCompatibilityChecker()
        self._compatibility_report = None

        # 状态管理
        self._initialized = False
        self._initialization_lock = threading.Lock()

        # 回调函数
        self._initialization_callbacks = []
        self._fallback_callbacks = []
        self._error_callbacks = []

        # 初始化性能统计
        self._performance_stats = {
            'total_renders': 0,
            'successful_renders': 0,
            'failed_renders': 0,
            'fallback_triggered': 0,
            'average_render_time': 0.0,
            'current_backend': None
        }

        # 自动初始化
        if self.config.auto_initialize:
            self.initialize()

    def initialize(self) -> bool:
        """
        初始化WebGPU管理器

        Returns:
            是否初始化成功
        """
        with self._initialization_lock:
            if self._initialized:
                return True

            try:
                logger.info("开始初始化WebGPU管理器...")

                # 1. 初始化环境
                self._environment = get_webgpu_environment()
                if not self._environment.initialize():
                    logger.warning("WebGPU环境初始化失败")
                    if not self.config.enable_fallback:
                        return False



                # 3. 生成兼容性报告
                self._compatibility_report = None
                if self._environment:
                    try:
                        capabilities = self._environment.gpu_capabilities
                        support_level = self._environment.support_level
                        self._compatibility_report = self._compatibility_checker.check_compatibility(capabilities, support_level)
                        logger.info(f"生成兼容性报告: {self._compatibility_report.level.value}")
                    except Exception as e:
                        logger.warning(f"生成兼容性报告失败: {e}")
                        # 如果生成失败，创建一个默认的兼容性报告
                        from .compatibility import CompatibilityReport, CompatibilityLevel, GPUSupportLevel
                        self._compatibility_report = CompatibilityReport(
                            level=CompatibilityLevel.FAIR,
                            recommended_backend=GPUSupportLevel.WEBGPU,
                            issues=[],
                            performance_score=75.0,
                            recommendations=["使用默认兼容性设置"]
                        )
                else:
                    # 如果没有环境信息，创建默认兼容性报告
                    from .compatibility import CompatibilityReport, CompatibilityLevel, GPUSupportLevel
                    logger.warning("⚠️ 没有GPU环境信息，使用默认兼容性报告")
                    self._compatibility_report = CompatibilityReport(
                        level=CompatibilityLevel.FAIR,
                        recommended_backend=GPUSupportLevel.WEBGPU,
                        issues=[],
                        performance_score=75.0,
                        recommendations=["默认GPU支持配置"]
                    )

                # 4. 初始化WebGPU渲染器（主要渲染器）
                logger.info("🚀 初始化WebGPU渲染器...")
                from .webgpu_renderer import WebGPURenderer, GPURendererConfig
                
                gpu_config = GPURendererConfig(
                    backend_type=self._compatibility_report.recommended_backend,
                    preferred_backend=self._compatibility_report.recommended_backend
                )
                
                self._webgpu_renderer = WebGPURenderer(gpu_config)
                webgpu_success = self._webgpu_renderer.initialize(self._compatibility_report)
                
                if webgpu_success:
                    logger.info(f"✅ WebGPU渲染器初始化成功，使用后端: {self._webgpu_renderer.backend_type.value}")
                    self._performance_stats['current_backend'] = self._webgpu_renderer.backend_type.value
                else:
                    logger.warning("⚠️ WebGPU渲染器初始化失败，将使用降级渲染器")
                    self._performance_stats['current_backend'] = "fallback"

                # 5. 初始化降级渲染器
                if self.config.enable_fallback:
                    self._fallback_renderer = FallbackRenderer()
                    render_context = self._environment.create_render_context()

                    if not self._fallback_renderer.initialize(self._compatibility_report, render_context):
                        logger.error("降级渲染器初始化失败")
                        return False

                self._initialized = True

                # 调用初始化回调
                self._call_initialization_callbacks(True)

                logger.info("WebGPU管理器初始化成功")
                return True

            except Exception as e:
                logger.error(f"WebGPU管理器初始化失败: {e}")
                self._call_initialization_callbacks(False)
                return False



    def render_candlesticks(self, ax, data, style: Dict[str, Any] = None, x: np.ndarray = None, use_datetime_axis: bool = True) -> bool:
        """
        渲染K线图

        Args:
            ax: matplotlib轴对象
            data: K线数据
            style: 样式设置
            x: 可选，X轴数据（可以是datetime数组或数字索引）
            use_datetime_axis: 是否使用datetime X轴

        Returns:
            是否渲染成功
        """
        return self._render('render_candlesticks', ax, data, style or {}, x, use_datetime_axis)

    def render_volume(self, ax, data, style: Dict[str, Any] = None, x: np.ndarray = None, use_datetime_axis: bool = True) -> bool:
        """
        渲染成交量

        Args:
            ax: matplotlib轴对象
            data: 成交量数据
            style: 样式设置
            x: 可选，X轴数据（可以是datetime数组或数字索引）
            use_datetime_axis: 是否使用datetime X轴

        Returns:
            是否渲染成功
        """
        return self._render('render_volume', ax, data, style or {}, x, use_datetime_axis)

    def render_line(self, ax, data, style: Dict[str, Any] = None) -> bool:
        """
        渲染线图

        Args:
            ax: matplotlib轴对象
            data: 线图数据
            style: 样式设置

        Returns:
            是否渲染成功
        """
        return self._render('render_line', ax, data, style or {})

    def _render(self, method_name: str, *args, **kwargs) -> bool:
        """执行渲染操作"""
        if not self._initialized:
            logger.error("WebGPU管理器未初始化")
            return False

        start_time = time.time()
        
        try:
            # ✅ 优先使用WebGPU渲染器
            if self._webgpu_renderer and self._webgpu_renderer.initialized:
                logger.info(f"🚀 使用WebGPU渲染器执行: {method_name}")
                method = getattr(self._webgpu_renderer, method_name)
                success = method(*args, **kwargs)
                
                if success:
                    # 更新性能统计
                    render_time = time.time() - start_time
                    self._update_performance_stats(True, render_time)
                    logger.info(f"✅ WebGPU渲染成功: {method_name} ({render_time:.3f}s)")
                    return True
                else:
                    logger.warning(f"⚠️ WebGPU渲染失败: {method_name}")
            
            # 如果WebGPU渲染器不可用或失败，使用降级渲染器
            if self._fallback_renderer:
                logger.info(f"🔄 使用降级渲染器执行: {method_name}")
                method = getattr(self._fallback_renderer, method_name)
                success = method(*args, **kwargs)
                
                # 更新性能统计
                render_time = time.time() - start_time
                self._update_performance_stats(success, render_time)
                
                if success:
                    logger.info(f"✅ 降级渲染成功: {method_name} ({render_time:.3f}s)")
                else:
                    logger.warning(f"⚠️ 降级渲染失败: {method_name}")
                    
                return success
            else:
                logger.error("没有可用的渲染器")
                self._update_performance_stats(False, time.time() - start_time)
                return False

        except Exception as e:
            render_time = time.time() - start_time
            self._update_performance_stats(False, render_time)
            logger.error(f"渲染异常: {method_name}, 错误: {e}")
            
            # 尝试降级
            if self.config.auto_fallback_on_error and self._fallback_renderer:
                logger.info(f"🔄 尝试降级渲染: {method_name}")
                try:
                    method = getattr(self._fallback_renderer, method_name)
                    success = method(*args, **kwargs)
                    if success:
                        logger.info(f"✅ 降级渲染成功: {method_name}")
                        self._performance_stats['fallback_triggered'] += 1
                    return success
                except Exception as fallback_error:
                    logger.error(f"降级渲染也失败: {fallback_error}")
            
            return False
    
    def _update_performance_stats(self, success: bool, render_time: float):
        """更新性能统计"""
        self._performance_stats['total_renders'] += 1
        if success:
            self._performance_stats['successful_renders'] += 1
        else:
            self._performance_stats['failed_renders'] += 1
        
        # 更新平均渲染时间
        total_renders = self._performance_stats['total_renders']
        current_avg = self._performance_stats['average_render_time']
        self._performance_stats['average_render_time'] = (
            (current_avg * (total_renders - 1) + render_time) / total_renders
        )

    def _try_fallback(self) -> bool:
        """尝试降级"""
        if self._fallback_renderer and not self._fallback_renderer._initialized:
            try:
                render_context = self._environment.create_render_context()
                if self._fallback_renderer.initialize(self._compatibility_report, render_context):
                    logger.info("✅ 降级渲染器初始化成功")
                    return True
            except Exception as e:
                logger.error(f"降级渲染器初始化失败: {e}")
        return False
    
    @property
    def current_backend(self) -> str:
        """获取当前渲染后端"""
        if not self._initialized:
            return "uninitialized"
        
        # 优先从WebGPU渲染器获取
        if self._webgpu_renderer and hasattr(self._webgpu_renderer, 'backend_type'):
            return self._webgpu_renderer.backend_type.value
        
        # 从性能统计获取
        return self._performance_stats.get('current_backend', 'unknown')
        if not self._fallback_renderer:
            return False

        try:
            # 强制降级到下一个后端
            if self._fallback_renderer.force_fallback():
                # 调用降级回调
                self._call_fallback_callbacks()
                return True
            else:
                logger.error("降级失败，没有更多可用后端")
                return False

        except Exception as e:
            logger.error(f"降级处理异常: {e}")
            return False

    def clear(self) -> None:
        """清空渲染内容"""
        if self._fallback_renderer:
            self._fallback_renderer.clear()

    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        status = {
            'initialized': self._initialized,
            'environment': {
                'support_level': self._environment.support_level.value if self._environment else None,
                'gpu_capabilities': self._environment.gpu_capabilities.__dict__ if self._environment else None
            },
            'config': self.config.__dict__
        }

        if self._fallback_renderer:
            status['renderer'] = self._fallback_renderer.get_performance_info()

        return status

    def get_compatibility_report(self) -> Optional[CompatibilityReport]:
        """获取兼容性报告"""
        if not self._initialized:
            logger.warning("WebGPU管理器未初始化，无法获取兼容性报告")
            return None

        return self._compatibility_report

    def get_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        # 基于性能统计添加建议
        if self._performance_stats['failed_renders'] > 0:
            failure_rate = self._performance_stats['failed_renders'] / max(1, self._performance_stats['total_renders'])
            if failure_rate > 0.1:  # 10%失败率
                recommendations.append("渲染失败率较高，建议检查数据格式或降低复杂度")

        return recommendations

    def force_backend(self, backend: RenderBackend) -> bool:
        """强制切换到指定后端"""
        if not self._fallback_renderer:
            return False

        success = self._fallback_renderer.force_fallback(backend)
        if success:
            self._update_current_backend()
            logger.info(f"强制切换到后端: {backend.value}")

        return success

    def _update_current_backend(self):
        """更新当前后端信息"""
        if self._fallback_renderer:
            self._performance_stats['current_backend'] = self._fallback_renderer.get_current_backend()

    def reset_performance_stats(self):
        """重置性能统计"""
        current_backend = self._performance_stats.get('current_backend')
        self._performance_stats = {
            'total_renders': 0,
            'successful_renders': 0,
            'failed_renders': 0,
            'fallback_triggered': 0,
            'average_render_time': 0.0,
            'current_backend': current_backend
        }

    # 回调函数管理
    def add_initialization_callback(self, callback: Callable[[bool], None]):
        """添加初始化回调"""
        self._initialization_callbacks.append(callback)

    def add_fallback_callback(self, callback: Callable[[], None]):
        """添加降级回调"""
        self._fallback_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str], None]):
        """添加错误回调"""
        self._error_callbacks.append(callback)

    def _call_initialization_callbacks(self, success: bool):
        """调用初始化回调"""
        for callback in self._initialization_callbacks:
            try:
                callback(success)
            except Exception as e:
                logger.warning(f"初始化回调执行失败: {e}")

    def _call_fallback_callbacks(self):
        """调用降级回调"""
        for callback in self._fallback_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"降级回调执行失败: {e}")

    def _call_error_callbacks(self, error_msg: str):
        """调用错误回调"""
        for callback in self._error_callbacks:
            try:
                callback(error_msg)
            except Exception as e:
                logger.warning(f"错误回调执行失败: {e}")

    # 上下文管理器支持
    def __enter__(self):
        if not self._initialized:
            self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源
        if self._fallback_renderer:
            self._fallback_renderer.clear()

# 全局WebGPU管理器实例
_webgpu_manager = None
_manager_lock = threading.Lock()

def get_webgpu_manager(config: Optional[WebGPUConfig] = None) -> WebGPUManager:
    """获取全局WebGPU管理器实例"""
    global _webgpu_manager

    with _manager_lock:
        if _webgpu_manager is None:
            _webgpu_manager = WebGPUManager(config)
        return _webgpu_manager

def initialize_webgpu_manager(config: Optional[WebGPUConfig] = None) -> bool:
    """初始化全局WebGPU管理器"""
    manager = get_webgpu_manager(config)
    return manager.initialize()

def render_chart_webgpu(chart_type: str, ax, data, style: Dict[str, Any] = None, x: np.ndarray = None, use_datetime_axis: bool = True) -> bool:
    """
    使用WebGPU渲染图表的便捷函数

    Args:
        chart_type: 图表类型 ('candlesticks', 'volume', 'line')
        ax: matplotlib轴对象
        data: 图表数据
        style: 样式设置
        x: 可选，X轴数据
        use_datetime_axis: 是否使用datetime轴

    Returns:
        是否渲染成功
    """
    manager = get_webgpu_manager()

    if chart_type == 'candlesticks':
        return manager.render_candlesticks(ax, data, style, x, use_datetime_axis)
    elif chart_type == 'volume':
        return manager.render_volume(ax, data, style, x, use_datetime_axis)
    elif chart_type == 'line':
        return manager.render_line(ax, data, style)
    else:
        logger.error(f"不支持的图表类型: {chart_type}")
        return False
