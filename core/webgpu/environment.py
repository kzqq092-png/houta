"""
WebGPU环境检测和初始化模块

负责：
1. WebGPU支持检测
2. GPU硬件能力检测
3. 环境初始化和配置
4. 浏览器兼容性检查
"""

import logging
import platform
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class GPUSupportLevel(Enum):
    """GPU支持级别"""
    NONE = "none"           # 无GPU支持
    BASIC = "basic"         # 基础GPU支持
    WEBGL = "webgl"         # WebGL支持
    WEBGPU = "webgpu"       # WebGPU支持
    NATIVE = "native"       # 原生GPU支持


@dataclass
class GPUCapabilities:
    """GPU能力信息"""
    adapter_name: str = ""
    vendor: str = ""
    device_id: str = ""
    memory_mb: int = 0
    compute_units: int = 0
    max_texture_size: int = 0
    supports_compute: bool = False
    webgpu_features: List[str] = None
    webgl_extensions: List[str] = None

    def __post_init__(self):
        if self.webgpu_features is None:
            self.webgpu_features = []
        if self.webgl_extensions is None:
            self.webgl_extensions = []


@dataclass
class EnvironmentInfo:
    """环境信息"""
    platform: str = ""
    browser: str = ""
    browser_version: str = ""
    user_agent: str = ""
    screen_width: int = 0
    screen_height: int = 0
    device_pixel_ratio: float = 1.0
    supports_webworkers: bool = False
    supports_offscreen_canvas: bool = False


class WebGPUEnvironment:
    """WebGPU环境管理器"""

    def __init__(self):
        self._initialized = False
        self._support_level = GPUSupportLevel.NONE
        self._gpu_capabilities = GPUCapabilities()
        self._environment_info = EnvironmentInfo()
        self._lock = threading.Lock()

        # 检测缓存
        self._detection_cache = {}

        # 配置
        self.config = {
            'enable_fallback': True,
            'prefer_discrete_gpu': True,
            'min_memory_mb': 256,
            'timeout_ms': 5000
        }

    def initialize(self) -> bool:
        """
        初始化WebGPU环境

        Returns:
            是否初始化成功
        """
        with self._lock:
            if self._initialized:
                return True

            try:
                logger.info("开始初始化WebGPU环境...")

                # 1. 检测基础环境
                self._detect_environment()

                # 2. 检测GPU支持级别
                self._detect_gpu_support()

                # 3. 检测GPU能力
                if self._support_level in [GPUSupportLevel.WEBGPU, GPUSupportLevel.WEBGL]:
                    self._detect_gpu_capabilities()

                # 4. 验证环境
                success = self._validate_environment()

                if success:
                    self._initialized = True
                    logger.info(f"WebGPU环境初始化成功 - 支持级别: {self._support_level.value}")
                    self._log_environment_info()
                else:
                    logger.warning("WebGPU环境初始化失败，将使用降级方案")

                return success

            except Exception as e:
                logger.error(f"WebGPU环境初始化异常: {e}")
                return False

    def _detect_environment(self):
        """检测基础环境信息"""
        try:
            # 检测平台信息
            self._environment_info.platform = platform.system()

            # 检测屏幕信息（如果在Qt环境中）
            try:
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtGui import QScreen

                app = QApplication.instance()
                if app:
                    screen = app.primaryScreen()
                    geometry = screen.geometry()
                    self._environment_info.screen_width = geometry.width()
                    self._environment_info.screen_height = geometry.height()
                    self._environment_info.device_pixel_ratio = screen.devicePixelRatio()

            except ImportError:
                pass

            # 检测其他能力
            self._environment_info.supports_webworkers = True  # 假设支持

            logger.info(f"环境检测完成: {self._environment_info.platform}, "
                        f"屏幕: {self._environment_info.screen_width}x{self._environment_info.screen_height}")

        except Exception as e:
            logger.warning(f"环境检测失败: {e}")

    def _detect_gpu_support(self):
        """检测GPU支持级别"""
        try:
            # 1. 检测WebGPU支持
            if self._check_webgpu_support():
                self._support_level = GPUSupportLevel.WEBGPU
                logger.info("检测到WebGPU支持")
                return

            # 2. 检测WebGL支持
            if self._check_webgl_support():
                self._support_level = GPUSupportLevel.WEBGL
                logger.info("检测到WebGL支持")
                return

            # 3. 检测原生GPU支持
            if self._check_native_gpu_support():
                self._support_level = GPUSupportLevel.NATIVE
                logger.info("检测到原生GPU支持")
                return

            # 4. 基础支持
            self._support_level = GPUSupportLevel.BASIC
            logger.info("使用基础GPU支持")

        except Exception as e:
            logger.error(f"GPU支持检测失败: {e}")
            self._support_level = GPUSupportLevel.NONE

    def _check_webgpu_support(self) -> bool:
        """检查WebGPU支持"""
        try:
            # 在Python环境中，我们通过集成的WebGPU库来检测
            # 这里使用模拟检测，实际项目中需要调用WebGPU JS API

            # 检查浏览器内核支持
            return self._check_browser_webgpu_support()

        except Exception as e:
            logger.debug(f"WebGPU支持检测异常: {e}")
            return False

    def _check_webgl_support(self) -> bool:
        """检查WebGL支持"""
        try:
            # 模拟WebGL检测
            # 实际项目中需要通过QWebEngine检测WebGL支持
            return True

        except Exception as e:
            logger.debug(f"WebGL支持检测异常: {e}")
            return False

    def _check_native_gpu_support(self) -> bool:
        """检查原生GPU支持"""
        try:
            # 检测OpenGL支持（通过PyOpenGL）
            try:
                import OpenGL.GL as gl
                return True
            except ImportError:
                pass

            # 检测其他GPU库
            return False

        except Exception as e:
            logger.debug(f"原生GPU支持检测异常: {e}")
            return False

    def _check_browser_webgpu_support(self) -> bool:
        """检查浏览器WebGPU支持"""
        # 模拟浏览器检测逻辑
        # 实际项目中需要通过JavaScript接口检测

        platform_name = self._environment_info.platform.lower()

        # Windows 10+ 支持更好
        if "windows" in platform_name:
            return True

        # macOS 支持
        if "darwin" in platform_name:
            return True

        # Linux 支持（需要新内核）
        if "linux" in platform_name:
            return True

        return False

    def _detect_gpu_capabilities(self):
        """检测GPU能力"""
        try:
            if self._support_level == GPUSupportLevel.WEBGPU:
                self._detect_webgpu_capabilities()
            elif self._support_level == GPUSupportLevel.WEBGL:
                self._detect_webgl_capabilities()
            elif self._support_level == GPUSupportLevel.NATIVE:
                self._detect_native_gpu_capabilities()

        except Exception as e:
            logger.warning(f"GPU能力检测失败: {e}")

    def _detect_webgpu_capabilities(self):
        """检测WebGPU能力"""
        # 模拟WebGPU能力检测
        self._gpu_capabilities.adapter_name = "WebGPU Adapter"
        self._gpu_capabilities.vendor = "Unknown"
        self._gpu_capabilities.memory_mb = 1024  # 默认假设1GB
        self._gpu_capabilities.max_texture_size = 8192
        self._gpu_capabilities.supports_compute = True
        self._gpu_capabilities.webgpu_features = [
            "depth-clip-control",
            "depth32float-stencil8",
            "texture-compression-bc",
            "timestamp-query"
        ]

    def _detect_webgl_capabilities(self):
        """检测WebGL能力"""
        # 模拟WebGL能力检测
        self._gpu_capabilities.adapter_name = "WebGL Adapter"
        self._gpu_capabilities.vendor = "Unknown"
        self._gpu_capabilities.memory_mb = 512  # WebGL通常限制更多
        self._gpu_capabilities.max_texture_size = 4096
        self._gpu_capabilities.supports_compute = False
        self._gpu_capabilities.webgl_extensions = [
            "OES_texture_float",
            "OES_texture_half_float",
            "WEBGL_depth_texture",
            "EXT_texture_filter_anisotropic"
        ]

    def _detect_native_gpu_capabilities(self):
        """检测原生GPU能力"""
        try:
            import OpenGL.GL as gl

            # 获取GPU信息
            self._gpu_capabilities.adapter_name = gl.glGetString(gl.GL_RENDERER).decode()
            self._gpu_capabilities.vendor = gl.glGetString(gl.GL_VENDOR).decode()

            # 获取纹理大小限制
            max_texture_size = gl.glGetIntegerv(gl.GL_MAX_TEXTURE_SIZE)
            self._gpu_capabilities.max_texture_size = max_texture_size

            # 估算显存（需要其他库支持）
            self._gpu_capabilities.memory_mb = 1024  # 默认值

        except Exception as e:
            logger.warning(f"原生GPU能力检测失败: {e}")

    def _validate_environment(self) -> bool:
        """验证环境是否满足要求"""
        try:
            # 检查最小内存要求
            if self._gpu_capabilities.memory_mb < self.config['min_memory_mb']:
                logger.warning(f"GPU内存不足: {self._gpu_capabilities.memory_mb}MB < {self.config['min_memory_mb']}MB")

            # 检查纹理大小支持
            if self._gpu_capabilities.max_texture_size < 2048:
                logger.warning(f"纹理大小支持不足: {self._gpu_capabilities.max_texture_size} < 2048")

            # 对于图表渲染，基础支持就足够了
            return self._support_level != GPUSupportLevel.NONE

        except Exception as e:
            logger.error(f"环境验证失败: {e}")
            return False

    def _log_environment_info(self):
        """记录环境信息"""
        logger.info("=== WebGPU环境信息 ===")
        logger.info(f"支持级别: {self._support_level.value}")
        logger.info(f"GPU适配器: {self._gpu_capabilities.adapter_name}")
        logger.info(f"GPU厂商: {self._gpu_capabilities.vendor}")
        logger.info(f"GPU内存: {self._gpu_capabilities.memory_mb}MB")
        logger.info(f"最大纹理: {self._gpu_capabilities.max_texture_size}")
        logger.info(f"计算支持: {self._gpu_capabilities.supports_compute}")
        logger.info(f"平台: {self._environment_info.platform}")
        logger.info(f"屏幕: {self._environment_info.screen_width}x{self._environment_info.screen_height}")
        logger.info("========================")

    # 公共接口
    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized

    @property
    def support_level(self) -> GPUSupportLevel:
        """获取支持级别"""
        return self._support_level

    @property
    def gpu_capabilities(self) -> GPUCapabilities:
        """获取GPU能力"""
        return self._gpu_capabilities

    @property
    def environment_info(self) -> EnvironmentInfo:
        """获取环境信息"""
        return self._environment_info

    def get_recommended_settings(self) -> Dict[str, Any]:
        """获取推荐设置"""
        settings = {
            'max_texture_size': min(self._gpu_capabilities.max_texture_size, 4096),
            'enable_compute': self._gpu_capabilities.supports_compute,
            'memory_limit_mb': self._gpu_capabilities.memory_mb // 2,  # 使用一半显存
            'use_instanced_rendering': self._support_level == GPUSupportLevel.WEBGPU,
            'max_points_per_batch': 10000 if self._support_level == GPUSupportLevel.WEBGPU else 5000
        }

        return settings

    def create_render_context(self) -> Optional[Any]:
        """创建渲染上下文"""
        if not self._initialized:
            return None

        # 根据支持级别创建相应的渲染上下文
        if self._support_level == GPUSupportLevel.WEBGPU:
            return self._create_webgpu_context()
        elif self._support_level == GPUSupportLevel.WEBGL:
            return self._create_webgl_context()
        elif self._support_level == GPUSupportLevel.NATIVE:
            return self._create_opengl_context()
        else:
            return None

    def _create_webgpu_context(self):
        """创建WebGPU上下文"""
        # 实际项目中这里会创建WebGPU设备和上下文
        logger.info("创建WebGPU渲染上下文")
        return {"type": "webgpu", "capabilities": self._gpu_capabilities}

    def _create_webgl_context(self):
        """创建WebGL上下文"""
        logger.info("创建WebGL渲染上下文")
        return {"type": "webgl", "capabilities": self._gpu_capabilities}

    def _create_opengl_context(self):
        """创建OpenGL上下文"""
        logger.info("创建OpenGL渲染上下文")
        return {"type": "opengl", "capabilities": self._gpu_capabilities}


# 全局环境实例
_webgpu_environment = None
_env_lock = threading.Lock()


def get_webgpu_environment() -> WebGPUEnvironment:
    """获取WebGPU环境实例"""
    global _webgpu_environment

    with _env_lock:
        if _webgpu_environment is None:
            _webgpu_environment = WebGPUEnvironment()
        return _webgpu_environment


def initialize_webgpu_environment() -> bool:
    """初始化WebGPU环境"""
    env = get_webgpu_environment()
    return env.initialize()
