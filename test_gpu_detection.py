#!/usr/bin/env python3
"""
GPU检测测试脚本
用于验证增强的GPU检测功能是否正常工作
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_gpu_detection():
    """测试GPU检测功能"""
    try:
        from core.webgpu.enhanced_gpu_detection import get_gpu_detector, PowerPreference

        logger.info("🔍 开始测试GPU检测功能...")

        # 获取GPU检测器
        detector = get_gpu_detector()

        # 检测所有适配器
        logger.info("1️⃣ 检测所有GPU适配器...")
        adapters = detector.detect_all_adapters()

        logger.info(f"📊 检测到 {len(adapters)} 个GPU适配器:")
        for i, adapter in enumerate(adapters, 1):
            logger.info(f"  {i}. {adapter.name}")
            logger.info(f"     厂商: {adapter.vendor}")
            logger.info(f"     类型: {adapter.gpu_type.value}")
            logger.info(f"     显存: {adapter.memory_mb}MB")
            logger.info(f"     设备ID: {adapter.device_id}")
            logger.info(f"     驱动版本: {adapter.driver_version}")
            logger.info(f"     性能分数: {adapter.performance_score}")
            logger.info(f"     默认: {adapter.is_default}")
            logger.info("")

        # 测试最佳适配器选择
        logger.info("2️⃣ 测试最佳适配器选择...")

        # 高性能偏好
        best_performance = detector.select_best_adapter(
            power_preference=PowerPreference.HIGH_PERFORMANCE,
            require_discrete=False
        )

        if best_performance:
            logger.info(f"🚀 高性能最佳适配器: {best_performance.name} ({best_performance.vendor})")
            logger.info(f"   类型: {best_performance.gpu_type.value}")
            logger.info(f"   显存: {best_performance.memory_mb}MB")

        # 低功耗偏好
        best_low_power = detector.select_best_adapter(
            power_preference=PowerPreference.LOW_POWER,
            require_discrete=False
        )

        if best_low_power:
            logger.info(f"🔋 低功耗最佳适配器: {best_low_power.name} ({best_low_power.vendor})")
            logger.info(f"   类型: {best_low_power.gpu_type.value}")
            logger.info(f"   显存: {best_low_power.memory_mb}MB")

        # 要求独立显卡
        discrete_gpu = detector.select_best_adapter(
            power_preference=PowerPreference.HIGH_PERFORMANCE,
            require_discrete=True
        )

        if discrete_gpu:
            logger.info(f"🎮 独立显卡: {discrete_gpu.name} ({discrete_gpu.vendor})")
            logger.info(f"   显存: {discrete_gpu.memory_mb}MB")
        else:
            logger.warning("❌ 未找到独立显卡")

        logger.info("✅ GPU检测测试完成!")
        return True

    except Exception as e:
        logger.error(f"❌ GPU检测测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_webgpu_integration():
    """测试WebGPU集成"""
    try:
        from core.webgpu.environment import WebGPUEnvironment

        logger.info("3️⃣ 测试WebGPU集成...")

        env = WebGPUEnvironment()
        success = env.initialize()

        if success:
            logger.info("✅ WebGPU环境初始化成功")
            logger.info(f"GPU适配器: {env.gpu_capabilities.adapter_name}")
            logger.info(f"GPU厂商: {env.gpu_capabilities.vendor}")
            logger.info(f"GPU内存: {env.gpu_capabilities.memory_mb}MB")
        else:
            logger.warning("⚠️ WebGPU环境初始化失败")

        return success

    except Exception as e:
        logger.error(f"❌ WebGPU集成测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("GPU检测系统测试")
    logger.info("=" * 60)

    # 测试GPU检测
    gpu_test_result = test_gpu_detection()

    # 测试WebGPU集成
    webgpu_test_result = test_webgpu_integration()

    # 总结
    logger.info("=" * 60)
    logger.info("测试结果总结:")
    logger.info(f"GPU检测功能: {'✅ 通过' if gpu_test_result else '❌ 失败'}")
    logger.info(f"WebGPU集成: {'✅ 通过' if webgpu_test_result else '❌ 失败'}")

    if gpu_test_result and webgpu_test_result:
        logger.info("🎉 所有测试通过!")
        sys.exit(0)
    else:
        logger.error("💥 部分测试失败!")
        sys.exit(1)
