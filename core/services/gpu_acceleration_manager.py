from loguru import logger
#!/usr/bin/env python3
"""
GPU加速数据处理管理器

利用GPU进行数据处理加速，包括：
- CUDA/OpenCL支持检测
- GPU内存管理
- 并行数据处理
- 性能监控和优化
"""

import threading
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

logger = logger

# 尝试导入GPU计算库
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    logger.info("CuPy GPU加速库可用")
except ImportError:
    CUPY_AVAILABLE = False
    cp = None

try:
    import pyopencl as cl
    OPENCL_AVAILABLE = True
    logger.info("OpenCL GPU加速库可用")
except ImportError:
    OPENCL_AVAILABLE = False
    cl = None

try:
    import numba
    from numba import cuda, jit
    NUMBA_CUDA_AVAILABLE = True
    logger.info("Numba CUDA加速库可用")
except ImportError:
    NUMBA_CUDA_AVAILABLE = False
    numba = None
    cuda = None
    jit = None


class GPUBackend(Enum):
    """GPU后端类型"""
    CUDA = "cuda"
    OPENCL = "opencl"
    NUMBA_CUDA = "numba_cuda"
    CPU_FALLBACK = "cpu_fallback"


@dataclass
class GPUDeviceInfo:
    """GPU设备信息"""
    device_id: int
    name: str
    memory_total: int  # MB
    memory_free: int   # MB
    compute_capability: str
    backend: GPUBackend
    is_available: bool = True


@dataclass
class GPUTaskConfig:
    """GPU任务配置"""
    task_type: str
    batch_size: int = 1000
    use_gpu: bool = True
    preferred_backend: GPUBackend = GPUBackend.CUDA
    memory_limit_mb: int = 1024
    thread_blocks: int = 256
    threads_per_block: int = 256


class GPUMemoryManager:
    """GPU内存管理器"""

    def __init__(self, backend: GPUBackend):
        self.backend = backend
        self.allocated_memory = {}
        self.memory_pool = {}
        self._lock = threading.Lock()

    def allocate(self, size: int, dtype=np.float32) -> Optional[Any]:
        """分配GPU内存"""
        try:
            with self._lock:
                if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
                    return cp.zeros(size, dtype=dtype)
                elif self.backend == GPUBackend.NUMBA_CUDA and NUMBA_CUDA_AVAILABLE:
                    return cuda.device_array(size, dtype=dtype)
                else:
                    # CPU fallback
                    return np.zeros(size, dtype=dtype)
        except Exception as e:
            logger.error(f"GPU内存分配失败: {e}")
            return None

    def deallocate(self, memory_obj: Any):
        """释放GPU内存"""
        try:
            with self._lock:
                if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
                    if hasattr(memory_obj, 'data'):
                        memory_obj.data.mem.free()
                elif self.backend == GPUBackend.NUMBA_CUDA and NUMBA_CUDA_AVAILABLE:
                    # Numba CUDA内存会自动管理
                    pass
                # CPU内存由Python GC管理
        except Exception as e:
            logger.error(f"GPU内存释放失败: {e}")

    def get_memory_info(self) -> Dict[str, int]:
        """获取内存信息"""
        try:
            if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
                mempool = cp.get_default_memory_pool()
                return {
                    'used_bytes': mempool.used_bytes(),
                    'total_bytes': mempool.total_bytes()
                }
            elif self.backend == GPUBackend.NUMBA_CUDA and NUMBA_CUDA_AVAILABLE:
                context = cuda.current_context()
                return {
                    'used_bytes': 0,  # Numba不直接提供内存使用信息
                    'total_bytes': 0
                }
            else:
                import psutil
                memory = psutil.virtual_memory()
                return {
                    'used_bytes': memory.used,
                    'total_bytes': memory.total
                }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            return {'used_bytes': 0, 'total_bytes': 0}


class GPUDataProcessor:
    """GPU数据处理器"""

    def __init__(self, backend: GPUBackend, memory_manager: GPUMemoryManager):
        self.backend = backend
        self.memory_manager = memory_manager
        self._compile_kernels()

    def _compile_kernels(self):
        """编译GPU计算核函数"""
        try:
            if self.backend == GPUBackend.NUMBA_CUDA and NUMBA_CUDA_AVAILABLE:
                # 编译CUDA核函数
                self._compile_cuda_kernels()
            elif self.backend == GPUBackend.OPENCL and OPENCL_AVAILABLE:
                # 编译OpenCL核函数
                self._compile_opencl_kernels()
        except Exception as e:
            logger.error(f"编译GPU核函数失败: {e}")

    def _compile_cuda_kernels(self):
        """编译CUDA核函数"""
        if not NUMBA_CUDA_AVAILABLE:
            return

        @cuda.jit
        def vector_add_kernel(a, b, c):
            """向量加法核函数"""
            idx = cuda.grid(1)
            if idx < c.size:
                c[idx] = a[idx] + b[idx]

        @cuda.jit
        def matrix_multiply_kernel(A, B, C):
            """矩阵乘法核函数"""
            row, col = cuda.grid(2)
            if row < C.shape[0] and col < C.shape[1]:
                tmp = 0.0
                for k in range(A.shape[1]):
                    tmp += A[row, k] * B[k, col]
                C[row, col] = tmp

        @cuda.jit
        def data_transform_kernel(input_data, output_data, scale, offset):
            """数据变换核函数"""
            idx = cuda.grid(1)
            if idx < input_data.size:
                output_data[idx] = input_data[idx] * scale + offset

        self.vector_add_kernel = vector_add_kernel
        self.matrix_multiply_kernel = matrix_multiply_kernel
        self.data_transform_kernel = data_transform_kernel

    def _compile_opencl_kernels(self):
        """编译OpenCL核函数"""
        if not OPENCL_AVAILABLE:
            return

        # OpenCL核函数源码
        kernel_source = """
        __kernel void vector_add(__global const float* a,
                                __global const float* b,
                                __global float* c) {
            int idx = get_global_id(0);
            c[idx] = a[idx] + b[idx];
        }
        
        __kernel void data_transform(__global const float* input,
                                   __global float* output,
                                   float scale,
                                   float offset) {
            int idx = get_global_id(0);
            output[idx] = input[idx] * scale + offset;
        }
        """

        try:
            # 创建OpenCL上下文和程序
            self.cl_context = cl.create_some_context()
            self.cl_queue = cl.CommandQueue(self.cl_context)
            self.cl_program = cl.Program(self.cl_context, kernel_source).build()
        except Exception as e:
            logger.error(f"编译OpenCL核函数失败: {e}")

    def process_batch_data(self, data: np.ndarray, operation: str, **kwargs) -> np.ndarray:
        """批量处理数据"""
        try:
            if self.backend == GPUBackend.CUDA and CUPY_AVAILABLE:
                return self._process_with_cupy(data, operation, **kwargs)
            elif self.backend == GPUBackend.NUMBA_CUDA and NUMBA_CUDA_AVAILABLE:
                return self._process_with_numba_cuda(data, operation, **kwargs)
            elif self.backend == GPUBackend.OPENCL and OPENCL_AVAILABLE:
                return self._process_with_opencl(data, operation, **kwargs)
            else:
                # CPU fallback
                return self._process_with_cpu(data, operation, **kwargs)
        except Exception as e:
            logger.error(f"GPU数据处理失败: {e}")
            # 降级到CPU处理
            return self._process_with_cpu(data, operation, **kwargs)

    def _process_with_cupy(self, data: np.ndarray, operation: str, **kwargs) -> np.ndarray:
        """使用CuPy处理数据"""
        gpu_data = cp.asarray(data)

        if operation == "normalize":
            mean = cp.mean(gpu_data, axis=0)
            std = cp.std(gpu_data, axis=0)
            result = (gpu_data - mean) / (std + 1e-8)
        elif operation == "scale":
            scale = kwargs.get('scale', 1.0)
            offset = kwargs.get('offset', 0.0)
            result = gpu_data * scale + offset
        elif operation == "filter":
            threshold = kwargs.get('threshold', 0.0)
            result = cp.where(gpu_data > threshold, gpu_data, 0)
        else:
            result = gpu_data

        return cp.asnumpy(result)

    def _process_with_numba_cuda(self, data: np.ndarray, operation: str, **kwargs) -> np.ndarray:
        """使用Numba CUDA处理数据"""
        # 分配GPU内存
        gpu_data = cuda.to_device(data)
        gpu_result = cuda.device_array_like(data)

        # 计算网格和块大小
        threads_per_block = 256
        blocks_per_grid = (data.size + threads_per_block - 1) // threads_per_block

        if operation == "scale":
            scale = kwargs.get('scale', 1.0)
            offset = kwargs.get('offset', 0.0)
            self.data_transform_kernel[blocks_per_grid, threads_per_block](
                gpu_data.ravel(), gpu_result.ravel(), scale, offset
            )
        else:
            # 默认复制数据
            gpu_result = gpu_data

        return gpu_result.copy_to_host()

    def _process_with_opencl(self, data: np.ndarray, operation: str, **kwargs) -> np.ndarray:
        """使用OpenCL处理数据"""
        if not hasattr(self, 'cl_context'):
            return self._process_with_cpu(data, operation, **kwargs)

        # 创建缓冲区
        mf = cl.mem_flags
        input_buffer = cl.Buffer(self.cl_context, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=data)
        output_buffer = cl.Buffer(self.cl_context, mf.WRITE_ONLY, data.nbytes)

        if operation == "scale":
            scale = np.float32(kwargs.get('scale', 1.0))
            offset = np.float32(kwargs.get('offset', 0.0))

            # 执行核函数
            self.cl_program.data_transform(
                self.cl_queue, data.shape, None,
                input_buffer, output_buffer, scale, offset
            )
        else:
            # 默认复制
            cl.enqueue_copy(self.cl_queue, output_buffer, input_buffer)

        # 读取结果
        result = np.empty_like(data)
        cl.enqueue_copy(self.cl_queue, result, output_buffer)
        return result

    def _process_with_cpu(self, data: np.ndarray, operation: str, **kwargs) -> np.ndarray:
        """CPU处理数据（降级方案）"""
        if operation == "normalize":
            mean = np.mean(data, axis=0)
            std = np.std(data, axis=0)
            return (data - mean) / (std + 1e-8)
        elif operation == "scale":
            scale = kwargs.get('scale', 1.0)
            offset = kwargs.get('offset', 0.0)
            return data * scale + offset
        elif operation == "filter":
            threshold = kwargs.get('threshold', 0.0)
            return np.where(data > threshold, data, 0)
        else:
            return data.copy()


class GPUAccelerationManager(QObject):
    """GPU加速管理器"""

    # 信号定义
    device_detected = pyqtSignal(dict)  # GPU设备检测到
    processing_started = pyqtSignal(str)  # 处理开始
    processing_progress = pyqtSignal(str, int)  # 处理进度
    processing_completed = pyqtSignal(str, dict)  # 处理完成
    processing_failed = pyqtSignal(str, str)  # 处理失败

    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_devices = []
        self.current_backend = GPUBackend.CPU_FALLBACK
        self.memory_manager = None
        self.data_processor = None

        # 检测GPU设备
        self._detect_gpu_devices()

        # 初始化最佳后端
        self._initialize_backend()

        logger.info(f"GPU加速管理器初始化完成，当前后端: {self.current_backend.value}")

    def _detect_gpu_devices(self):
        """检测可用的GPU设备"""
        self.available_devices = []

        # 检测CUDA设备
        if CUPY_AVAILABLE:
            try:
                device_count = cp.cuda.runtime.getDeviceCount()
                for i in range(device_count):
                    with cp.cuda.Device(i):
                        props = cp.cuda.runtime.getDeviceProperties(i)
                        device_info = GPUDeviceInfo(
                            device_id=i,
                            name=props['name'].decode('utf-8'),
                            memory_total=props['totalGlobalMem'] // (1024 * 1024),
                            memory_free=props['totalGlobalMem'] // (1024 * 1024),  # 简化
                            compute_capability=f"{props['major']}.{props['minor']}",
                            backend=GPUBackend.CUDA
                        )
                        self.available_devices.append(device_info)
                        self.device_detected.emit(device_info.__dict__)

                logger.info(f"检测到 {device_count} 个CUDA设备")
            except Exception as e:
                logger.warning(f"CUDA设备检测失败: {e}")

        # 检测OpenCL设备
        if OPENCL_AVAILABLE:
            try:
                platforms = cl.get_platforms()
                for platform in platforms:
                    devices = platform.get_devices(cl.device_type.GPU)
                    for i, device in enumerate(devices):
                        device_info = GPUDeviceInfo(
                            device_id=len(self.available_devices),
                            name=device.name,
                            memory_total=device.global_mem_size // (1024 * 1024),
                            memory_free=device.global_mem_size // (1024 * 1024),
                            compute_capability="OpenCL",
                            backend=GPUBackend.OPENCL
                        )
                        self.available_devices.append(device_info)
                        self.device_detected.emit(device_info.__dict__)

                logger.info(f"检测到 {len(devices)} 个OpenCL设备")
            except Exception as e:
                logger.warning(f"OpenCL设备检测失败: {e}")

        # 如果没有GPU设备，添加CPU fallback
        if not self.available_devices:
            cpu_info = GPUDeviceInfo(
                device_id=0,
                name="CPU (Fallback)",
                memory_total=0,
                memory_free=0,
                compute_capability="N/A",
                backend=GPUBackend.CPU_FALLBACK
            )
            self.available_devices.append(cpu_info)

    def _initialize_backend(self):
        """初始化最佳GPU后端"""
        if not self.available_devices:
            self.current_backend = GPUBackend.CPU_FALLBACK
        else:
            # 优先选择CUDA
            for device in self.available_devices:
                if device.backend == GPUBackend.CUDA:
                    self.current_backend = GPUBackend.CUDA
                    break
            else:
                # 其次选择OpenCL
                for device in self.available_devices:
                    if device.backend == GPUBackend.OPENCL:
                        self.current_backend = GPUBackend.OPENCL
                        break
                else:
                    self.current_backend = GPUBackend.CPU_FALLBACK

        # 初始化内存管理器和数据处理器
        self.memory_manager = GPUMemoryManager(self.current_backend)
        self.data_processor = GPUDataProcessor(self.current_backend, self.memory_manager)

    def get_device_info(self) -> List[Dict[str, Any]]:
        """获取设备信息"""
        return [device.__dict__ for device in self.available_devices]

    def get_current_backend(self) -> GPUBackend:
        """获取当前后端"""
        return self.current_backend

    def process_data_batch(self, task_id: str, data: np.ndarray,
                           operation: str, config: GPUTaskConfig = None) -> Optional[np.ndarray]:
        """处理数据批次"""
        try:
            if config is None:
                config = GPUTaskConfig(task_type=operation)

            self.processing_started.emit(task_id)

            # 检查是否使用GPU
            if not config.use_gpu or self.current_backend == GPUBackend.CPU_FALLBACK:
                result = self.data_processor._process_with_cpu(data, operation)
            else:
                result = self.data_processor.process_batch_data(data, operation)

            self.processing_completed.emit(task_id, {
                'status': 'success',
                'processed_records': len(data),
                'backend': self.current_backend.value
            })

            return result

        except Exception as e:
            logger.error(f"GPU数据处理失败: {e}")
            self.processing_failed.emit(task_id, str(e))
            return None

    def benchmark_performance(self) -> Dict[str, float]:
        """性能基准测试"""
        try:
            # 生成测试数据
            test_data = np.random.rand(10000, 100).astype(np.float32)

            results = {}

            # CPU基准
            start_time = time.time()
            cpu_result = self.data_processor._process_with_cpu(test_data, "normalize")
            cpu_time = time.time() - start_time
            results['cpu'] = cpu_time

            # GPU基准（如果可用）
            if self.current_backend != GPUBackend.CPU_FALLBACK:
                start_time = time.time()
                gpu_result = self.data_processor.process_batch_data(test_data, "normalize")
                gpu_time = time.time() - start_time
                results['gpu'] = gpu_time
                results['speedup'] = cpu_time / gpu_time if gpu_time > 0 else 0

            return results

        except Exception as e:
            logger.error(f"性能基准测试失败: {e}")
            return {}

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        if self.memory_manager:
            return self.memory_manager.get_memory_info()
        return {'used_bytes': 0, 'total_bytes': 0}

    def optimize_batch_size(self, data_size: int, available_memory: int) -> int:
        """优化批处理大小"""
        # 估算每个样本的内存使用量（字节）
        bytes_per_sample = data_size * 4  # 假设float32

        # 预留20%的内存空间
        usable_memory = available_memory * 0.8

        # 计算最优批大小
        optimal_batch_size = int(usable_memory / bytes_per_sample)

        # 限制在合理范围内
        return max(100, min(optimal_batch_size, 10000))


# 全局服务实例
_gpu_acceleration_manager = None


def get_gpu_acceleration_manager() -> GPUAccelerationManager:
    """获取GPU加速管理器实例"""
    global _gpu_acceleration_manager
    if _gpu_acceleration_manager is None:
        _gpu_acceleration_manager = GPUAccelerationManager()
    return _gpu_acceleration_manager


def is_gpu_available() -> bool:
    """检查GPU是否可用"""
    return CUPY_AVAILABLE or OPENCL_AVAILABLE or NUMBA_CUDA_AVAILABLE


def get_gpu_info() -> Dict[str, Any]:
    """获取GPU信息"""
    manager = get_gpu_acceleration_manager()
    return {
        'available': is_gpu_available(),
        'current_backend': manager.get_current_backend().value,
        'devices': manager.get_device_info(),
        'memory_usage': manager.get_memory_usage()
    }
