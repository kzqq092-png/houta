#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU管理系统独立验证脚本
独立运行，验证GPU管理系统的核心功能
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_gpu_detection():
    """测试GPU硬件检测"""
    print("\n=== 测试GPU硬件检测 ===")
    
    try:
        # 测试nvidia-ml-py3
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            print(f"✅ NVIDIA GPU检测成功: 发现 {device_count} 个GPU设备")
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name_result = pynvml.nvmlDeviceGetName(handle)
                # 兼容不同版本的pynvml返回类型
                name = name_result.decode('utf-8') if isinstance(name_result, bytes) else str(name_result)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                print(f"  GPU {i}: {name}")
                print(f"    显存: {memory_info.total // 1024 // 1024} MB")
                print(f"    可用: {memory_info.free // 1024 // 1024} MB")
                print(f"    已用: {memory_info.used // 1024 // 1024} MB")
            
            pynvml.nvmlShutdown()
            return True
            
        except ImportError:
            print("❌ pynvml库未安装，无法进行GPU检测")
        except Exception as e:
            print(f"❌ GPU检测失败: {e}")
            
        return False
        
    except Exception as e:
        print(f"❌ GPU检测异常: {e}")
        return False

def test_tensorflow_gpu():
    """测试TensorFlow GPU支持"""
    print("\n=== 测试TensorFlow GPU支持 ===")
    
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow版本: {tf.__version__}")
        
        # 检测GPU可用性
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✅ TensorFlow检测到 {len(gpus)} 个GPU设备")
            
            # 显示GPU详细信息
            for i, gpu in enumerate(gpus):
                print(f"  GPU {i}: {gpu.name}")
                try:
                    # 设置显存增长
                    tf.config.experimental.set_memory_growth(gpu, True)
                    print(f"    显存增长: 已启用")
                except Exception as e:
                    print(f"    显存增长: 失败 ({e})")
            
            # 简单GPU计算测试
            with tf.device('/GPU:0'):
                a = tf.constant([[1.0, 2.0], [3.0, 4.0]])
                b = tf.constant([[1.0, 1.0], [0.0, 1.0]])
                c = tf.matmul(a, b)
                print(f"    GPU计算测试: 成功 (结果形状: {c.shape})")
            
            return True
        else:
            print("❌ TensorFlow未检测到GPU设备")
            return False
            
    except ImportError:
        print("❌ TensorFlow未安装")
        return False
    except Exception as e:
        print(f"❌ TensorFlow GPU测试失败: {e}")
        return False

def test_cuda_environment():
    """测试CUDA环境"""
    print("\n=== 测试CUDA环境 ===")
    
    try:
        # 检查CUDA库
        try:
            import ctypes
            cuda_lib = ctypes.CDLL('nvcuda.dll' if sys.platform == 'win32' else 'libcuda.so.1')
            print("✅ CUDA运行时库加载成功")
        except Exception as e:
            print(f"❌ CUDA运行时库加载失败: {e}")
            return False
        
        # 检查cuDNN
        try:
            cudnn_lib = ctypes.CDLL('cudnn64_8.dll' if sys.platform == 'win32' else 'libcudnn.so.8')
            print("✅ cuDNN库加载成功")
        except Exception as e:
            print(f"❌ cuDNN库加载失败: {e}")
            return False
        
        print("✅ CUDA环境基本验证通过")
        return True
        
    except Exception as e:
        print(f"❌ CUDA环境测试失败: {e}")
        return False

def test_gpu_manager_module():
    """测试GPU管理器模块"""
    print("\n=== 测试GPU管理器模块 ===")
    
    try:
        # 尝试导入GPU管理器模块
        gpu_manager_path = Path(__file__).parent.parent / 'core' / 'services' / 'tensorflow_gpu_manager.py'
        
        if not gpu_manager_path.exists():
            print("❌ GPU管理器模块文件不存在")
            return False
        
        print("✅ GPU管理器模块文件存在")
        
        # 验证文件内容
        with open(gpu_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查关键类和方法
        required_elements = [
            'class TensorFlowGPUManager',
            'def auto_detect_and_configure',
            'def detect_gpu_hardware',
            'def configure_tensorflow_gpu',
            'GPUStatus'
        ]
        
        for element in required_elements:
            if element in content:
                print(f"  ✅ 找到关键元素: {element}")
            else:
                print(f"  ❌ 缺少关键元素: {element}")
                return False
        
        print("✅ GPU管理器模块结构验证通过")
        return True
        
    except Exception as e:
        print(f"❌ GPU管理器模块测试失败: {e}")
        return False

def generate_verification_report(results):
    """生成验证报告"""
    print("\n" + "="*60)
    print("GPU管理系统验证报告")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"验证时间: {timestamp}")
    print(f"运行环境: {sys.platform} - Python {sys.version}")
    
    print("\n验证结果:")
    test_names = {
        'gpu_detection': 'GPU硬件检测',
        'tensorflow_gpu': 'TensorFlow GPU支持',
        'cuda_environment': 'CUDA环境',
        'gpu_manager': 'GPU管理器模块'
    }
    
    passed = 0
    total = len(results)
    
    for test_key, result in results.items():
        test_name = test_names.get(test_key, test_key)
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 GPU管理系统验证完全通过！")
        print("💡 建议: 系统已准备好使用GPU加速功能")
    elif passed >= total * 0.5:
        print("⚠️ GPU管理系统部分可用")
        print("💡 建议: 部分功能正常，可尝试使用，但建议完善缺失的组件")
    else:
        print("❌ GPU管理系统存在重大问题")
        print("💡 建议: 需要安装依赖库或配置CUDA环境")
    
    return passed, total

def main():
    """主函数"""
    print("GPU管理系统独立验证脚本")
    print("="*60)
    print("此脚本将独立验证GPU管理系统的各个组件")
    
    results = {}
    
    # 执行各项测试
    tests = [
        ('gpu_detection', test_gpu_detection),
        ('tensorflow_gpu', test_tensorflow_gpu),
        ('cuda_environment', test_cuda_environment),
        ('gpu_manager', test_gpu_manager_module)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n开始执行: {test_name}")
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ 测试异常: {test_name} - {e}")
            results[test_name] = False
    
    # 生成报告
    passed, total = generate_verification_report(results)
    
    # 保存详细报告到文件
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'platform': sys.platform,
        'python_version': sys.version,
        'results': results,
        'summary': {
            'passed': passed,
            'total': total,
            'success_rate': passed / total if total > 0 else 0
        }
    }
    
    report_file = Path("gpu_verification_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细报告已保存到: {report_file}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)