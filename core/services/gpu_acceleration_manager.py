"""
GPU加速管理器服务

提供统一的GPU加速接口，整合：
1. WebGPU硬件加速渲染
2. CUDA/CuPy数值计算加速  
3. 性能监控和降级处理

作者: FactorWeave-Quant Team
版本: v2.5
"""

from loguru import logger
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

from .base_service import BaseService
from .metrics_base import add_dict_interface


class GPUBackendType(Enum):
    """GPU后端类型"""
    WEBGPU = "webgpu"           # WebGPU（图表渲染）
    CUDA = "cuda"               # CUDA（数值计算）
    OPENCL = "opencl"           # OpenCL（跨平台）
    METAL = "metal"             # Metal（macOS）
    CPU_FALLBACK = "cpu"        # CPU降级


class GPUAccelerationLevel(Enum):
    """GPU加速级别"""
    NONE = 0        # 无加速
    BASIC = 1       # 基础加速
    STANDARD = 2    # 标准加速
    HIGH = 3        # 高级加速
    ULTRA = 4       # 极致加速


@dataclass
class GPUCapabilities:
    """GPU能力信息"""
    webgpu_available: bool = False
    cuda_available: bool = False
    opencl_available: bool = False
    metal_available: bool = False

    # 详细信息
    gpu_name: str = "Unknown"
    gpu_memory_gb: float = 0.0
    compute_capability: str = "N/A"
    driver_version: str = "N/A"

    # 支持的功能
    supports_float16: bool = False
    supports_float64: bool = False
    supports_tensor_cores: bool = False

    last_check: datetime = field(default_factory=datetime.now)


@add_dict_interface
@dataclass
class GPUMetrics:
    """GPU性能指标"""
    # 基础指标（来自BaseService）
    initialization_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    operation_count: int = 0

    # GPU特定指标
    gpu_utilization: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_temperature: float = 0.0

    # 渲染统计
    total_renders: int = 0
    successful_renders: int = 0
    failed_renders: int = 0
    fallback_count: int = 0

    # 性能统计
    average_render_time_ms: float = 0.0
    average_compute_time_ms: float = 0.0
    peak_memory_usage_mb: float = 0.0

    current_backend: str = "none"
    acceleration_level: str = "none"

    last_update: datetime = field(default_factory=datetime.now)


class GPUAccelerationManager(BaseService):
    """
    GPU加速管理器服务

    统一管理各种GPU加速后端：
    - WebGPU: 图表渲染加速
    - CUDA/CuPy: 数值计算加速
    - 自动降级: GPU不可用时使用CPU
    """

    def __init__(self):
        super().__init__("GPUAccelerationManager")

        # GPU能力
        self._capabilities = GPUCapabilities()
        self._acceleration_level = GPUAccelerationLevel.NONE

        # 后端管理器
        self._webgpu_manager = None
        self._cuda_context = None
        self._fallback_enabled = True

        # 性能监控
        self._metrics = GPUMetrics()
        self._metrics_lock = threading.RLock()

        # 配置
        self._config = {
            "auto_detect": True,
            "prefer_webgpu": True,
            "prefer_cuda": True,
            "enable_fallback": True,
            "max_gpu_memory_usage_gb": 4.0,
        }

    def _do_initialize(self) -> None:
        """初始化GPU加速管理器"""
        logger.info("初始化GPU加速管理器...")

        # 检测GPU能力
        self._detect_gpu_capabilities()

        # 初始化后端
        self._initialize_backends()

        # 设置加速级别
        self._determine_acceleration_level()

        logger.info(f"GPU加速管理器初始化完成 - 加速级别: {self._acceleration_level.name}")
        logger.info(f"  WebGPU: {'✅' if self._capabilities.webgpu_available else '❌'}")
        logger.info(f"  CUDA: {'✅' if self._capabilities.cuda_available else '❌'}")

    def _detect_gpu_capabilities(self) -> None:
        """检测GPU能力"""
        logger.info("检测GPU能力...")

        # 检测WebGPU
        self._capabilities.webgpu_available = self._check_webgpu()

        # 检测CUDA
        self._capabilities.cuda_available = self._check_cuda()

        # 检测OpenCL
        self._capabilities.opencl_available = self._check_opencl()

        # 检测Metal（macOS）
        self._capabilities.metal_available = self._check_metal()

        # 更新检测时间
        self._capabilities.last_check = datetime.now()

    def _check_webgpu(self) -> bool:
        """检测WebGPU可用性"""
        try:
            from core.webgpu import WebGPUManager, get_webgpu_manager

            # 尝试获取WebGPU管理器
            manager = get_webgpu_manager()
            if manager and manager.is_available():
                self._capabilities.gpu_name = "WebGPU Compatible"
                logger.info("✅ WebGPU可用")
                return True
            else:
                logger.info("⚠️ WebGPU不可用（环境不支持）")
                return False

        except ImportError as e:
            logger.debug(f"WebGPU模块导入失败: {e}")
            return False
        except Exception as e:
            logger.debug(f"WebGPU检测失败: {e}")
            return False

    def _check_cuda(self) -> bool:
        """检测CUDA可用性"""
        try:
            import cupy as cp

            # 检测CUDA设备
            if cp.cuda.is_available():
                device = cp.cuda.Device(0)
                self._capabilities.gpu_name = device.name.decode('utf-8') if isinstance(device.name, bytes) else str(device.name)
                self._capabilities.gpu_memory_gb = device.mem_info[1] / (1024**3)
                self._capabilities.compute_capability = f"{device.compute_capability[0]}.{device.compute_capability[1]}"

                logger.info(f"✅ CUDA可用 - {self._capabilities.gpu_name}")
                logger.info(f"   GPU内存: {self._capabilities.gpu_memory_gb:.1f}GB")
                return True
            else:
                logger.info("⚠️ CUDA不可用（无GPU设备）")
                return False

        except ImportError:
            logger.debug("CuPy未安装，CUDA不可用")
            return False
        except Exception as e:
            logger.debug(f"CUDA检测失败: {e}")
            return False

    def _check_opencl(self) -> bool:
        """检测OpenCL可用性"""
        try:
            import pyopencl as cl

            platforms = cl.get_platforms()
            if platforms:
                logger.info(f"✅ OpenCL可用 - {len(platforms)}个平台")
                return True
            else:
                return False

        except ImportError:
            logger.debug("PyOpenCL未安装")
            return False
        except Exception as e:
            logger.debug(f"OpenCL检测失败: {e}")
            return False

    def _check_metal(self) -> bool:
        """检测Metal可用性（macOS）"""
        import sys

        if sys.platform != 'darwin':
            return False

        try:
            # Metal API检测（macOS特定）
            # 这里可以添加Metal框架的检测逻辑
            logger.debug("Metal检测需要macOS环境")
            return False
        except Exception as e:
            logger.debug(f"Metal检测失败: {e}")
            return False

    def _initialize_backends(self) -> None:
        """初始化GPU后端"""
        # 初始化WebGPU（如果可用）
        if self._capabilities.webgpu_available and self._config["prefer_webgpu"]:
            try:
                from core.webgpu import get_webgpu_manager
                self._webgpu_manager = get_webgpu_manager()
                logger.info("✅ WebGPU后端已初始化")
            except Exception as e:
                logger.warning(f"WebGPU后端初始化失败: {e}")

        # 初始化CUDA（如果可用）
        if self._capabilities.cuda_available and self._config["prefer_cuda"]:
            try:
                import cupy as cp
                self._cuda_context = cp.cuda.Device(0)
                logger.info("✅ CUDA后端已初始化")
            except Exception as e:
                logger.warning(f"CUDA后端初始化失败: {e}")

    def _determine_acceleration_level(self) -> None:
        """确定加速级别"""
        if self._capabilities.cuda_available and self._capabilities.webgpu_available:
            self._acceleration_level = GPUAccelerationLevel.ULTRA
            self._metrics.current_backend = "hybrid"
        elif self._capabilities.cuda_available:
            self._acceleration_level = GPUAccelerationLevel.HIGH
            self._metrics.current_backend = "cuda"
        elif self._capabilities.webgpu_available:
            self._acceleration_level = GPUAccelerationLevel.STANDARD
            self._metrics.current_backend = "webgpu"
        elif self._capabilities.opencl_available:
            self._acceleration_level = GPUAccelerationLevel.BASIC
            self._metrics.current_backend = "opencl"
        else:
            self._acceleration_level = GPUAccelerationLevel.NONE
            self._metrics.current_backend = "cpu_fallback"

        self._metrics.acceleration_level = self._acceleration_level.name.lower()

    def get_capabilities(self) -> GPUCapabilities:
        """获取GPU能力信息"""
        return self._capabilities

    def get_acceleration_level(self) -> GPUAccelerationLevel:
        """获取当前加速级别"""
        return self._acceleration_level

    def is_gpu_available(self) -> bool:
        """GPU是否可用"""
        return (self._capabilities.webgpu_available or
                self._capabilities.cuda_available or
                self._capabilities.opencl_available)

    def get_webgpu_manager(self):
        """获取WebGPU管理器"""
        return self._webgpu_manager

    def get_cuda_context(self):
        """获取CUDA上下文"""
        return self._cuda_context

    def get_metrics(self) -> Dict[str, Any]:
        """获取GPU指标"""
        with self._metrics_lock:
            return {
                'gpu_available': self.is_gpu_available(),
                'acceleration_level': self._acceleration_level.name,
                'current_backend': self._metrics.current_backend,
                'webgpu_available': self._capabilities.webgpu_available,
                'cuda_available': self._capabilities.cuda_available,
                'gpu_name': self._capabilities.gpu_name,
                'gpu_memory_gb': self._capabilities.gpu_memory_gb,
                'total_renders': self._metrics.total_renders,
                'successful_renders': self._metrics.successful_renders,
                'fallback_count': self._metrics.fallback_count,
                'average_render_time_ms': self._metrics.average_render_time_ms,
            }

    def dispose(self) -> None:
        """清理GPU资源"""
        try:
            if self._webgpu_manager:
                # WebGPU清理
                logger.info("清理WebGPU资源...")
                self._webgpu_manager = None

            if self._cuda_context:
                # CUDA清理
                logger.info("清理CUDA资源...")
                self._cuda_context = None

            logger.info("GPU加速管理器已清理")

        except Exception as e:
            logger.error(f"GPU资源清理失败: {e}")


# 全局单例
_gpu_manager_instance: Optional[GPUAccelerationManager] = None
_gpu_manager_lock = threading.Lock()


def get_gpu_acceleration_manager() -> Optional[GPUAccelerationManager]:
    """获取GPU加速管理器单例"""
    global _gpu_manager_instance

    if _gpu_manager_instance is None:
        with _gpu_manager_lock:
            if _gpu_manager_instance is None:
                try:
                    _gpu_manager_instance = GPUAccelerationManager()
                    _gpu_manager_instance.initialize()
                except Exception as e:
                    logger.warning(f"GPU加速管理器初始化失败: {e}")
                    _gpu_manager_instance = None

    return _gpu_manager_instance


if __name__ == '__main__':
    # 测试GPU加速管理器
    print("="*60)
    print("GPU加速管理器测试")
    print("="*60)

    manager = GPUAccelerationManager()
    manager.initialize()

    caps = manager.get_capabilities()
    print(f"\nGPU能力:")
    print(f"  WebGPU: {caps.webgpu_available}")
    print(f"  CUDA: {caps.cuda_available}")
    print(f"  OpenCL: {caps.opencl_available}")
    print(f"  GPU名称: {caps.gpu_name}")
    print(f"  GPU内存: {caps.gpu_memory_gb:.1f}GB")

    print(f"\n加速级别: {manager.get_acceleration_level().name}")
    print(f"GPU可用: {manager.is_gpu_available()}")

    metrics = manager.get_metrics()
    print(f"\n指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    print("\n" + "="*60)
