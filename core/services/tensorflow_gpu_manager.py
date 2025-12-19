#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TensorFlow GPU智能管理器

功能：
1. 自动检测GPU硬件和环境
2. 智能配置TensorFlow GPU支持
3. 提供GPU/CPU自动选择机制
4. 监控GPU资源使用情况
5. 故障回退到CPU模式

作者: FactorWeave-Quant团队
版本: 1.0
"""

import os
import sys
import platform
import subprocess
import ctypes
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# 设置日志
logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow未安装，无法使用GPU管理功能")

class GPUStatus(Enum):
    """GPU状态枚举"""
    UNAVAILABLE = "unavailable"          # GPU不可用
    CUDA_ERROR = "cuda_error"            # CUDA环境错误
    DRIVER_ERROR = "driver_error"        # 驱动错误
    AVAILABLE = "available"              # GPU可用
    CONFIGURED = "configured"            # 已配置GPU
    TESTING = "testing"                  # 正在测试
    READY = "ready"                      # GPU就绪
    ERROR = "error"                      # GPU错误
    FALLBACK_CPU = "fallback_cpu"        # 回退到CPU

@dataclass
class GPUInfo:
    """GPU信息数据类"""
    name: str = "Unknown"
    memory_total: int = 0
    memory_free: int = 0
    memory_used: int = 0
    compute_capability: str = "unknown"
    cuda_version: str = "unknown"
    driver_version: str = "unknown"
    status: GPUStatus = GPUStatus.UNAVAILABLE
    
class TensorFlowGPUManager:
    """TensorFlow GPU智能管理器"""
    
    def __init__(self):
        self.gpu_info: Optional[GPUInfo] = None
        self.is_configured = False
        self.device_preference = "auto"  # auto, gpu, cpu
        self.auto_fallback_enabled = True
        self.performance_threshold = 0.5  # 性能阈值
        
        # 配置参数
        self.config = {
            'allow_memory_growth': True,
            'memory_fraction': 0.8,
            'inter_op_threads': 4,
            'intra_op_threads': 4,
            'mixed_precision': False
        }
        
        logger.info("TensorFlow GPU管理器初始化完成")
    
    def detect_gpu_hardware(self) -> GPUInfo:
        """检测GPU硬件信息"""
        logger.info("🔍 开始GPU硬件检测...")
        gpu_info = GPUInfo()
        
        try:
            # 尝试使用pynvml检测NVIDIA GPU
            import pynvml
            logger.info("✅ pynvml库加载成功")
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                logger.info(f"🎯 检测到 {device_count} 个NVIDIA GPU设备")
                logger.info("=" * 60)
                
                # 获取第一个GPU的信息
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name_result = pynvml.nvmlDeviceGetName(handle)
                name = name_result.decode('utf-8') if isinstance(name_result, bytes) else str(name_result)
                
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                gpu_info.name = name
                gpu_info.memory_total = memory_info.total // 1024 // 1024
                gpu_info.memory_free = memory_info.free // 1024 // 1024
                gpu_info.status = GPUStatus.AVAILABLE
                
                logger.info(f"🚀 GPU设备: {name}")
                logger.info(f"📊 显存总量: {gpu_info.memory_total:,} MB")
                logger.info(f"💾 可用显存: {gpu_info.memory_free:,} MB")
                logger.info(f"📈 当前使用率: {utilization_info.gpu}%")
                logger.info(f"💿 显存使用率: {utilization_info.memory}%")
                logger.info("=" * 60)
                
                pynvml.nvmlShutdown()
                
                # 性能评估
                if gpu_info.memory_total >= 8000:
                    logger.info("🎉 高性能GPU配置，适合深度学习训练")
                elif gpu_info.memory_total >= 4000:
                    logger.info("👍 中等性能GPU，适合模型推理和小规模训练")
                elif gpu_info.memory_total >= 2000:
                    logger.info("⚡ 入门级GPU，适合模型推理")
                else:
                    logger.info("⚠️ 显存较少，建议使用CPU模式")
                
            else:
                logger.warning("⚠️ 未检测到NVIDIA GPU设备")
                logger.info("💡 提示：请检查GPU驱动是否正确安装")
                gpu_info.status = GPUStatus.UNAVAILABLE
                
        except ImportError:
            logger.warning("❌ pynvml库未安装，无法检测GPU")
            logger.info("💡 解决方案：pip install nvidia-ml-py3")
            gpu_info.status = GPUStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"❌ GPU检测失败: {e}")
            logger.info("💡 建议：检查NVIDIA驱动和CUDA安装")
            gpu_info.status = GPUStatus.ERROR
            
        return gpu_info
    
    def _detect_cuda_version(self) -> str:
        """检测CUDA版本"""
        try:
            # 尝试从环境变量获取
            cuda_path = os.environ.get('CUDA_PATH')
            if cuda_path:
                version_file = Path(cuda_path) / "version.txt"
                if version_file.exists():
                    return version_file.read_text().strip()
            
            # 尝试从nvcc获取
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout
                # 提取版本信息
                lines = output.split('\n')
                for line in lines:
                    if 'release' in line.lower():
                        version = line.split('release')[1].strip().split(',')[0]
                        return version
            
            return "unknown"
        except Exception:
            return "unknown"
    
    def _detect_cuda_windows(self) -> Optional[Dict[str, str]]:
        """Windows系统CUDA检测"""
        try:
            # 尝试加载CUDA库
            cuda_lib = ctypes.WinDLL("cudart64_110.dll")
            cuda_version = cuda_lib.cudaGetErrorString(0)  # 测试库加载
            return {'cuda_version': '11.0'}  # 简化版本检测
        except Exception:
            return None
    
    def verify_cuda_environment(self) -> bool:
        """验证CUDA环境"""
        logger.info("验证CUDA环境...")
        
        try:
            # 1. 检查CUDA库
            cuda_libraries = [
                "cudart64_110.dll",  # Windows
                "cudart.so.11.0",    # Linux
                "cudnn64_8.dll",     # Windows
                "libcudnn.so.8",     # Linux
            ]
            
            for lib in cuda_libraries:
                try:
                    if platform.system() == "Windows":
                        ctypes.WinDLL(lib)
                        logger.info(f"✅ CUDA库加载成功: {lib}")
                        break
                    else:
                        ctypes.CDLL(lib)
                        logger.info(f"✅ CUDA库加载成功: {lib}")
                        break
                except (OSError, FileNotFoundError):
                    continue
            else:
                logger.warning("⚠️ 未找到CUDA库")
                return False
            
            # 2. 检查TensorFlow构建信息
            if TENSORFLOW_AVAILABLE:
                build_info = tf.sysconfig.get_build_info()
                cuda_version = build_info.get("cuda_version", "unknown")
                cudnn_version = build_info.get("cudnn_version", "unknown")
                
                logger.info(f"TensorFlow构建信息:")
                logger.info(f"  CUDA版本: {cuda_version}")
                logger.info(f"  cuDNN版本: {cudnn_version}")
                
                # 检查版本兼容性
                if cuda_version != "unknown" and cudnn_version != "unknown":
                    logger.info("✅ TensorFlow CUDA环境验证通过")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ CUDA环境验证失败: {e}")
            return False
    
    def configure_tensorflow_gpu(self) -> bool:
        """配置TensorFlow GPU支持"""
        if not TENSORFLOW_AVAILABLE:
            logger.error("❌ TensorFlow未安装，无法配置GPU")
            logger.info("💡 解决方案：pip install tensorflow")
            return False
        
        logger.info("🚀 开始配置TensorFlow GPU...")
        logger.info("=" * 60)
        
        try:
            # 1. 列出物理设备
            gpus = tf.config.list_physical_devices('GPU')
            logger.info(f"📊 TensorFlow检测到 {len(gpus)} 个物理GPU设备")
            
            if len(gpus) == 0:
                logger.warning("⚠️ TensorFlow未检测到GPU设备")
                logger.info("💡 可能原因：")
                logger.info("   1. GPU驱动未正确安装")
                logger.info("   2. CUDA版本不兼容")
                logger.info("   3. cuDNN库缺失")
                self.gpu_info.status = GPUStatus.UNAVAILABLE
                return False
            
            logger.info("🎯 开始配置GPU设备...")
            # 2. 配置GPU设备
            for i, gpu in enumerate(gpus):
                logger.info(f"  ⚙️ 配置GPU设备 {i}: {gpu.name}")
                
                # 设置显存增长
                if self.config['allow_memory_growth']:
                    tf.config.experimental.set_memory_growth(gpu, True)
                    logger.info(f"    ✅ 启用显存增长")
                
                # 设置显存限制
                if self.config['memory_fraction'] < 1.0:
                    memory_limit = int(
                        self.gpu_info.memory_total * self.config['memory_fraction']
                    ) if self.gpu_info.memory_total > 0 else 1024
                    
                    tf.config.set_logical_device_configuration(
                        gpu,
                        [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=memory_limit)]
                    )
                    logger.info(f"    ✅ 设置显存限制: {self.config['memory_fraction']*100}% ({memory_limit}MB)")
                else:
                    logger.info(f"    ℹ️ 使用完整显存: {self.gpu_info.memory_total}MB")
            
            # 3. 配置并行线程
            if self.config['inter_op_threads'] > 0:
                tf.config.threading.set_inter_op_parallelism_threads(self.config['inter_op_threads'])
                logger.info(f"    ✅ 设置inter_op_threads: {self.config['inter_op_threads']}")
            
            if self.config['intra_op_threads'] > 0:
                tf.config.threading.set_intra_op_parallelism_threads(self.config['intra_op_threads'])
                logger.info(f"    ✅ 设置intra_op_threads: {self.config['intra_op_threads']}")
            
            # 4. 混合精度训练
            if self.config['mixed_precision']:
                try:
                    tf.keras.mixed_precision.set_global_policy('mixed_float16')
                    logger.info("    ✅ 启用混合精度训练（加速计算）")
                except Exception as e:
                    logger.warning(f"    ⚠️ 混合精度设置失败: {e}")
            
            # 5. 设置可见设备
            visible_devices = [f"GPU:{i}" for i in range(len(gpus))]
            tf.config.set_visible_devices(visible_devices, 'GPU')
            
            self.is_configured = True
            self.gpu_info.status = GPUStatus.CONFIGURED
            
            logger.info("=" * 60)
            logger.info("🎉 TensorFlow GPU配置完成")
            logger.info(f"💡 可用GPU设备: {len(gpus)}")
            logger.info(f"⚡ 内存管理: {'显存增长' if self.config['allow_memory_growth'] else '固定显存'}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ TensorFlow GPU配置失败: {e}")
            self.gpu_info.status = GPUStatus.ERROR
            return False
    
    def test_gpu_computation(self) -> Tuple[bool, float]:
        """测试GPU计算性能"""
        if not TENSORFLOW_AVAILABLE or not self.is_configured:
            return False, 0.0
        
        logger.info("🧪 开始GPU计算性能测试...")
        logger.info("=" * 60)
        
        try:
            # 创建简单的测试模型
            logger.info("📋 创建测试模型...")
            with tf.device('/GPU:0'):
                model = tf.keras.Sequential([
                    tf.keras.layers.Dense(1000, activation='relu', input_shape=(100,)),
                    tf.keras.layers.Dense(500, activation='relu'),
                    tf.keras.layers.Dense(1, activation='sigmoid')
                ])
                
                model.compile(optimizer='adam', loss='binary_crossentropy')
                
                # 生成测试数据
                logger.info("📊 生成测试数据...")
                x_train = tf.random.normal([1000, 100])
                y_train = tf.random.uniform([1000, 1])
                
                # GPU训练测试
                logger.info("🚀 GPU训练测试开始...")
                start_time = time.time()
                history = model.fit(x_train, y_train, epochs=5, verbose=0)
                gpu_time = time.time() - start_time
                
                logger.info(f"✅ GPU训练完成，耗时: {gpu_time:.2f}秒")
                logger.info(f"📈 最终损失: {history.history['loss'][-1]:.4f}")
            
            # CPU对比测试
            logger.info("🖥️ CPU训练测试开始...")
            with tf.device('/CPU:0'):
                model = tf.keras.Sequential([
                    tf.keras.layers.Dense(1000, activation='relu', input_shape=(100,)),
                    tf.keras.layers.Dense(500, activation='relu'),
                    tf.keras.layers.Dense(1, activation='sigmoid')
                ])
                
                model.compile(optimizer='adam', loss='binary_crossentropy')
                
                start_time = time.time()
                history = model.fit(x_train, y_train, epochs=5, verbose=0)
                cpu_time = time.time() - start_time
                
                logger.info(f"✅ CPU训练完成，耗时: {cpu_time:.2f}秒")
                logger.info(f"📈 最终损失: {history.history['loss'][-1]:.4f}")
            
            speedup = cpu_time / gpu_time
            
            logger.info("=" * 60)
            logger.info("📊 性能测试结果:")
            logger.info(f"   CPU时间: {cpu_time:.2f}秒")
            logger.info(f"   GPU时间: {gpu_time:.2f}秒")
            logger.info(f"   加速比: {speedup:.2f}x")
            
            if speedup > 1.2:
                logger.info("🎉 GPU性能测试通过，显著提升计算速度")
                if speedup > 5.0:
                    logger.info("🚀 卓越性能！GPU加速效果优秀")
                elif speedup > 2.0:
                    logger.info("👍 良好性能，GPU加速效果明显")
                else:
                    logger.info("✅ 一般性能，GPU仍有加速效果")
                
                self.gpu_info.status = GPUStatus.READY
                return True, speedup
            elif speedup > 1.0:
                logger.warning("⚠️ GPU加速效果微弱，建议检查GPU配置")
                logger.info("💡 可能原因：GPU负载过高或内存不足")
                return False, speedup
            else:
                logger.warning("⚠️ GPU性能不如CPU，可能存在配置问题")
                logger.info("💡 建议：检查GPU驱动和CUDA环境")
                return False, speedup
                
        except Exception as e:
            logger.error(f"❌ GPU计算测试失败: {e}")
            logger.info("💡 建议：检查TensorFlow GPU配置和依赖库")
            return False, 0.0
    
    def auto_detect_and_configure(self) -> bool:
        """自动检测和配置GPU"""
        logger.info("🚀 [TensorFlow GPU管理器] 开始自动检测和配置")
        logger.info("=" * 80)
        logger.info("🎯 智能GPU管理器 - 正在为您优化TensorFlow性能")
        logger.info("=" * 80)
        
        try:
            # 1. 检测GPU硬件
            logger.info("🔍 [步骤 1/4] 正在检测GPU硬件...")
            self.gpu_info = self.detect_gpu_hardware()
            
            # 2. 验证CUDA环境
            logger.info("🔧 [步骤 2/4] 正在验证CUDA环境...")
            cuda_ok = self.verify_cuda_environment()
            if not cuda_ok:
                logger.error("❌ [CUDA验证] CUDA环境验证失败")
                logger.info("💡 [建议] 请安装CUDA Toolkit和cuDNN库")
                if self.auto_fallback_enabled:
                    logger.info("🔄 [回退] 启用自动回退到CPU模式")
                    self.gpu_info.status = GPUStatus.FALLBACK_CPU
                    return False
                return False
            
            # 3. 配置TensorFlow GPU
            logger.info("⚙️ [步骤 3/4] 正在配置TensorFlow GPU...")
            config_ok = self.configure_tensorflow_gpu()
            if not config_ok:
                logger.error("❌ [配置失败] TensorFlow GPU配置失败")
                logger.info("💡 [建议] 请检查GPU驱动和TensorFlow GPU版本")
                if self.auto_fallback_enabled:
                    logger.info("🔄 [回退] 启用自动回退到CPU模式")
                    self.gpu_info.status = GPUStatus.FALLBACK_CPU
                    return False
                return False
            
            # 4. 测试GPU性能
            logger.info("🧪 [步骤 4/4] 正在测试GPU性能...")
            test_ok, speedup = self.test_gpu_computation()
            if not test_ok:
                logger.warning("⚠️ [性能测试] GPU性能测试未通过")
                logger.info("💡 [原因] GPU可能负载过高或配置不正确")
                if self.auto_fallback_enabled:
                    logger.info("🔄 [回退] 启用自动回退到CPU模式")
                    self.gpu_info.status = GPUStatus.FALLBACK_CPU
                    return False
                return False
            
            # 成功完成
            logger.info("=" * 80)
            logger.info("🎉 [成功] GPU自动配置完成！")
            logger.info(f"🚀 [加速] 检测到设备: {self.gpu_info.name}")
            logger.info(f"⚡ [性能] 加速比: {speedup:.2f}x")
            logger.info(f"💾 [内存] GPU显存: {self.gpu_info.memory_total:,}MB")
            logger.info("=" * 80)
            logger.info("✅ [就绪] TensorFlow现已使用GPU加速")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [异常] 自动GPU配置失败: {e}")
            logger.info("💡 [建议] 请检查系统环境和依赖安装")
            if self.auto_fallback_enabled:
                logger.info("🔄 [回退] 启用自动回退到CPU模式")
                self.gpu_info.status = GPUStatus.FALLBACK_CPU
            return False
    
    def get_device_strategy(self) -> str:
        """获取设备策略"""
        if self.device_preference == "gpu":
            return "/GPU:0"
        elif self.device_preference == "cpu":
            return "/CPU:0"
        else:
            # 自动选择
            if self.gpu_info and self.gpu_info.status == GPUStatus.READY:
                return "/GPU:0"
            else:
                return "/CPU:0"
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'gpu_info': {
                'name': self.gpu_info.name if self.gpu_info else 'Unknown',
                'status': self.gpu_info.status.value if self.gpu_info else 'unknown',
                'memory_total': self.gpu_info.memory_total if self.gpu_info else 0,
                'memory_free': self.gpu_info.memory_free if self.gpu_info else 0,
                'cuda_version': self.gpu_info.cuda_version if self.gpu_info else 'unknown',
            },
            'tensorflow_info': {
                'available': TENSORFLOW_AVAILABLE,
                'version': tf.__version__ if TENSORFLOW_AVAILABLE else 'unknown',
                'configured': self.is_configured,
            },
            'device_strategy': self.get_device_strategy(),
            'auto_fallback': self.auto_fallback_enabled,
        }
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理GPU资源
            if self.is_configured:
                tf.config.set_visible_devices([], 'GPU')
                logger.info("GPU资源清理完成")
        except Exception as e:
            logger.warning(f"GPU资源清理警告: {e}")

# 全局GPU管理器实例
_gpu_manager = None

def get_gpu_manager() -> TensorFlowGPUManager:
    """获取全局GPU管理器实例"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = TensorFlowGPUManager()
    return _gpu_manager

def auto_configure_gpu() -> bool:
    """便捷函数：自动配置GPU"""
    manager = get_gpu_manager()
    return manager.auto_detect_and_configure()

def get_device_for_training() -> str:
    """获取训练设备"""
    manager = get_gpu_manager()
    return manager.get_device_strategy()

def print_gpu_status():
    """打印GPU状态信息"""
    manager = get_gpu_manager()
    status = manager.get_status_info()
    
    print("=" * 80)
    print("📊 [TensorFlow GPU状态报告]")
    print("=" * 80)
    
    # GPU信息
    if status['gpu_info']['name'] != 'Unknown':
        print(f"🚀 GPU设备: {status['gpu_info']['name']}")
        print(f"📈 状态: {status['gpu_info']['status']}")
        print(f"💾 显存总量: {status['gpu_info']['memory_total']:,} MB")
        print(f"💿 可用显存: {status['gpu_info']['memory_free']:,} MB")
        print(f"🔧 CUDA版本: {status['gpu_info']['cuda_version']}")
    else:
        print("⚠️ 未检测到GPU设备")
    
    # TensorFlow信息
    if status['tensorflow_info']['available']:
        print(f"✅ TensorFlow版本: {status['tensorflow_info']['version']}")
        print(f"⚙️ GPU配置状态: {'已配置' if status['tensorflow_info']['configured'] else '未配置'}")
    else:
        print("❌ TensorFlow未安装")
    
    # 当前策略
    device = status['device_strategy']
    if device == '/GPU:0':
        print(f"🎯 当前策略: GPU加速模式 ⚡")
    else:
        print(f"🖥️ 当前策略: CPU模式")
    
    print(f"🔄 自动回退: {'启用' if status['auto_fallback'] else '禁用'}")
    print("=" * 80)

if __name__ == "__main__":
    # 测试脚本
    print("=== TensorFlow GPU管理器测试 ===")
    
    # 自动配置
    success = auto_configure_gpu()
    print(f"GPU配置结果: {'成功' if success else '失败'}")
    
    # 显示状态
    print_gpu_status()
    
    # 清理资源
    manager = get_gpu_manager()
    manager.cleanup()