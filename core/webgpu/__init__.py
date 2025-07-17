"""
WebGPU硬件加速渲染模块

提供WebGPU硬件加速图表渲染功能，包括：
- WebGPU环境检测和初始化
- GPU渲染管道管理
- 硬件兼容性处理
- 多层降级机制

版本: 1.0
"""

from .environment import WebGPUEnvironment, get_webgpu_environment, initialize_webgpu_environment
from .compatibility import GPUCompatibilityChecker
from .fallback import FallbackRenderer, WebGPURenderer, RenderBackend
from .manager import WebGPUManager, get_webgpu_manager, WebGPUConfig
from .interaction_engine import GPUInteractionEngine, ViewportState, InteractionType
from .crosshair_engine import GPUCrosshairEngine, CrosshairState, CrosshairStyle, CrosshairConfig

__all__ = [
    'WebGPUEnvironment',
    'get_webgpu_environment',
    'initialize_webgpu_environment',
    'WebGPURenderer',
    'GPUCompatibilityChecker',
    'FallbackRenderer',
    'RenderBackend',
    'WebGPUManager',
    'get_webgpu_manager',
    'WebGPUConfig',
    'GPUInteractionEngine',
    'ViewportState',
    'InteractionType',
    'GPUCrosshairEngine',
    'CrosshairState',
    'CrosshairStyle',
    'CrosshairConfig'
]
