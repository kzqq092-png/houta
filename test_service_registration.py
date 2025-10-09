#!/usr/bin/env python3
"""
测试服务注册情况
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_service_registration():
    """测试服务注册情况"""
    print("🧪 测试服务注册情况")
    print("=" * 50)

    try:
        # 导入服务引导程序
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container

        print("📦 正在获取服务容器...")
        container = get_service_container()

        print("🔍 检查已注册的服务...")

        # 检查容器中的服务
        if hasattr(container, '_services'):
            services = container._services
            print(f"📊 已注册服务数量: {len(services)}")
            print("📋 已注册的服务:")
            for service_name in services.keys():
                print(f"   - {service_name}")
        elif hasattr(container, '_instances'):
            instances = container._instances
            print(f"📊 已注册实例数量: {len(instances)}")
            print("📋 已注册的实例:")
            for instance_type in instances.keys():
                print(f"   - {instance_type}")
        else:
            print("❌ 无法访问服务容器的内部结构")

        # 尝试手动引导服务
        print("\n🚀 尝试手动引导服务...")
        bootstrap = ServiceBootstrap()
        bootstrap.bootstrap()

        print("✅ 服务引导完成")

        # 再次检查服务
        print("\n🔍 引导后检查服务...")
        from core.services.unified_data_manager import UnifiedDataManager

        try:
            data_manager = container.resolve(UnifiedDataManager)
            if data_manager:
                print("✅ UnifiedDataManager 已成功注册和解析")
                return True
            else:
                print("❌ UnifiedDataManager 解析为None")
                return False
        except Exception as e:
            print(f"❌ 解析UnifiedDataManager失败: {e}")
            return False

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("HIkyuu-UI 服务注册测试")
    print("=" * 40)

    success = test_service_registration()

    print("\n" + "=" * 40)
    if success:
        print("🎉 服务注册测试通过！")
    else:
        print("⚠️ 服务注册有问题")


if __name__ == "__main__":
    main()
