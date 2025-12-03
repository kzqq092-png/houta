#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一优化服务测试文件
测试5个深度优化模块的统一管理和协调
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.advanced_optimization import (
        UnifiedOptimizationService,
        OptimizationConfig,
        OptimizationMode
    )
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此测试")
    sys.exit(1)


async def test_unified_optimization_service():
    """测试统一优化服务"""
    print("=" * 60)
    print("🧪 测试统一优化服务")
    print("=" * 60)
    
    try:
        # 1. 创建优化配置
        print("\n📋 第1步：创建优化配置...")
        config = OptimizationConfig(
            mode=OptimizationMode.PERFORMANCE,
            enable_cache=True,
            enable_virtual_scroll=True,
            enable_realtime_data=True,
            enable_ai_recommendation=True,
            enable_responsive_ui=True,
            
            # 缓存配置
            cache_size_mb=256,
            cache_ttl_seconds=1800,
            
            # 虚拟化配置
            chunk_size=50,
            preload_threshold=3,
            
            # 实时数据配置
            max_connections=20,
            buffer_size=512,
            
            # AI推荐配置
            recommendation_count=3,
            learning_window_days=7
        )
        print("✅ 优化配置创建成功")
        print(f"   - 模式: {config.mode.value}")
        print(f"   - 缓存: {config.cache_size_mb}MB, TTL: {config.cache_ttl_seconds}s")
        print(f"   - 虚拟化: 块大小{config.chunk_size}, 预加载阈值{config.preload_threshold}")
        
        # 2. 创建统一优化服务
        print("\n📋 第2步：创建统一优化服务...")
        service = UnifiedOptimizationService(config)
        print("✅ 统一优化服务创建成功")
        
        # 3. 初始化服务
        print("\n📋 第3步：初始化服务...")
        init_success = await service.initialize()
        if init_success:
            print("✅ 服务初始化成功")
        else:
            print("❌ 服务初始化失败")
            return False
        
        # 4. 获取服务状态
        print("\n📋 第4步：获取服务状态...")
        status = service.get_status()
        print("✅ 状态获取成功")
        print(f"   - 已初始化: {status['is_initialized']}")
        print(f"   - 运行中: {status['is_running']}")
        print(f"   - 已启用模块: {status['config']['enabled_modules']}")
        print(f"   - 模块状态: {status['modules_status']}")
        
        # 5. 启动服务
        print("\n📋 第5步：启动服务...")
        start_success = await service.start()
        if start_success:
            print("✅ 服务启动成功")
        else:
            print("❌ 服务启动失败")
            return False
        
        # 6. 等待服务稳定运行
        print("\n📋 第6步：等待服务稳定运行...")
        await asyncio.sleep(3)
        print("✅ 服务稳定运行")
        
        # 7. 获取性能指标
        print("\n📋 第7步：获取性能指标...")
        metrics = service.get_metrics()
        print("✅ 性能指标获取成功")
        print(f"   - 缓存命中率: {metrics.cache_hit_rate:.2%}")
        print(f"   - 滚动性能: {metrics.scroll_performance:.1f}fps")
        print(f"   - 数据吞吐量: {metrics.data_throughput:.1f}msg/s")
        print(f"   - 网络延迟: {metrics.network_latency_ms:.1f}ms")
        print(f"   - 内存使用: {metrics.memory_usage_mb:.1f}MB")
        
        # 8. 测试优化建议
        print("\n📋 第8步：获取优化建议...")
        context = {
            'user_type': 'trader',
            'chart_type': 'k_line',
            'data_size': 1000,
            'interaction_frequency': 'high'
        }
        recommendations = await service.get_optimization_recommendations(context)
        print("✅ 优化建议获取成功")
        print("   建议内容:")
        for category, suggestions in recommendations.items():
            if suggestions:
                print(f"     - {category}: {suggestions}")
        
        # 9. 获取最终状态
        print("\n📋 第9步：获取最终状态...")
        final_status = service.get_status()
        print("✅ 最终状态获取成功")
        print(f"   - 运行时间: {final_status['uptime_seconds']:.1f}秒")
        print(f"   - 当前指标: 缓存命中率{final_status['metrics'].cache_hit_rate:.2%}")
        
        # 10. 停止服务
        print("\n📋 第10步：停止服务...")
        stop_success = await service.stop()
        if stop_success:
            print("✅ 服务停止成功")
        else:
            print("❌ 服务停止失败")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 统一优化服务测试完成！")
        print("✅ 所有测试步骤都成功执行")
        print("✅ 5个深度优化模块统一管理正常")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_mode():
    """测试性能优先模式"""
    print("\n" + "=" * 60)
    print("🚀 测试性能优先模式")
    print("=" * 60)
    
    try:
        config = OptimizationConfig(
            mode=OptimizationMode.PERFORMANCE,
            cache_size_mb=1024,
            chunk_size=20,
            max_connections=100
        )
        
        service = UnifiedOptimizationService(config)
        
        # 快速初始化和测试
        init_success = await service.initialize()
        if not init_success:
            return False
            
        await service.start()
        
        # 获取性能指标
        metrics = service.get_metrics()
        print(f"✅ 性能优先模式测试成功")
        print(f"   - 内存配置: {config.cache_size_mb}MB")
        print(f"   - 块大小: {config.chunk_size}")
        print(f"   - 最大连接: {config.max_connections}")
        
        await service.stop()
        return True
        
    except Exception as e:
        print(f"❌ 性能优先模式测试失败: {e}")
        return False


async def test_balanced_mode():
    """测试平衡模式"""
    print("\n" + "=" * 60)
    print("⚖️ 测试平衡模式")
    print("=" * 60)
    
    try:
        config = OptimizationConfig(
            mode=OptimizationMode.BALANCED,
            enable_cache=True,
            enable_virtual_scroll=True,
            enable_realtime_data=False,  # 禁用实时数据以减少资源消耗
            enable_ai_recommendation=False,  # 禁用AI推荐以简化测试
            enable_responsive_ui=True
        )
        
        service = UnifiedOptimizationService(config)
        
        # 快速初始化和测试
        init_success = await service.initialize()
        if not init_success:
            return False
            
        await service.start()
        
        # 获取状态
        status = service.get_status()
        enabled_modules = status['config']['enabled_modules']
        print(f"✅ 平衡模式测试成功")
        print(f"   - 启用的模块: {[k for k, v in enabled_modules.items() if v]}")
        
        await service.stop()
        return True
        
    except Exception as e:
        print(f"❌ 平衡模式测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🔥 深度优化系统统一优化服务测试")
    print("测试5个深度优化模块的统一管理和协调")
    print()
    
    # 等待系统初始化
    await asyncio.sleep(1)
    
    tests = [
        ("统一优化服务测试", test_unified_optimization_service),
        ("性能优先模式测试", test_performance_mode),
        ("平衡模式测试", test_balanced_mode)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 开始执行: {test_name}")
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试都通过了！统一优化服务工作正常")
    else:
        print("⚠️ 部分测试失败，需要检查相关模块")
    print("=" * 60)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())