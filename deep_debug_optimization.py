#!/usr/bin/env python3
"""
深度调试优化模块注册问题
"""

import sys
import os
from loguru import logger
from core.services.service_bootstrap import ServiceBootstrap
from core.containers import get_service_container

def deep_debug_registration():
    print("🔍 深度调试优化模块注册问题")
    print("=" * 60)
    
    # 步骤1: 获取服务容器并检查其ID
    print("📋 步骤1: 检查服务容器实例")
    container = get_service_container()
    print(f"  容器ID: {id(container)}")
    print(f"  容器类型: {type(container)}")
    
    # 检查容器内部状态
    try:
        registry = container._registry
        print(f"  注册表类型: {type(registry)}")
        print(f"  注册表方法: {dir(registry)}")
        
        # 获取当前注册的服务
        all_services = registry.get_all_services()
        print(f"  当前已注册服务数量: {len(all_services)}")
        for service in all_services:
            print(f"    - {service.service_type.__name__} (名称: {service.name})")
            
    except Exception as e:
        print(f"  检查注册表失败: {e}")
    
    # 步骤2: 创建ServiceBootstrap并检查其容器引用
    print("\n🚀 步骤2: 检查ServiceBootstrap容器引用")
    bootstrap = ServiceBootstrap(container)
    print(f"  Bootstrap实例ID: {id(bootstrap)}")
    print(f"  Bootstrap容器ID: {id(bootstrap.service_container)}")
    print(f"  容器ID是否一致: {id(bootstrap.service_container) == id(container)}")
    
    # 步骤3: 手动执行注册并实时监控
    print("\n⚡ 步骤3: 执行智能缓存注册并监控")
    
    try:
        # 检查import是否成功
        print("  检查模块导入...")
        from core.advanced_optimization.cache.intelligent_cache import IntelligentCache
        print(f"  ✅ IntelligentCache 导入成功: {IntelligentCache}")
        
        # 检查注册前的状态
        print("  检查注册前状态...")
        print(f"    容器中是否已注册IntelligentCache: {container.is_registered(IntelligentCache)}")
        print(f"    容器中是否已注册'intelligent_cache': {container.is_registered('intelligent_cache')}")
        
        # 执行注册
        print("  执行_register_intelligent_cache...")
        bootstrap._register_intelligent_cache()
        
        # 立即检查注册后状态
        print("  检查注册后状态...")
        print(f"    容器中是否已注册IntelligentCache: {container.is_registered(IntelligentCache)}")
        print(f"    容器中是否已注册'intelligent_cache': {container.is_registered('intelligent_cache')}")
        print(f"    容器中是否已注册'cache_manager': {container.is_registered('cache_manager')}")
        
        # 重新获取注册的服务列表
        all_services = container._registry.get_all_services()
        print(f"  注册后服务总数: {len(all_services)}")
        for service in all_services:
            print(f"    - {service.service_type.__name__} (名称: {service.name})")
            
        # 步骤4: 尝试解析服务
        print("\n🔧 步骤4: 尝试解析服务")
        try:
            cache_service = container.resolve('intelligent_cache')
            print(f"  ✅ 成功解析缓存服务: {type(cache_service)}")
        except Exception as e:
            print(f"  ❌ 解析缓存服务失败: {e}")
            
        try:
            cache_service2 = container.resolve(IntelligentCache)
            print(f"  ✅ 成功按类型解析缓存服务: {type(cache_service2)}")
        except Exception as e:
            print(f"  ❌ 按类型解析缓存服务失败: {e}")
            
    except Exception as e:
        print(f"  ❌ 注册过程出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 步骤5: 检查ServiceContainer的is_registered方法实现
    print("\n🔍 步骤5: 检查is_registered方法")
    
    # 检查方法是否存在
    print(f"  is_registered方法存在: {hasattr(container, 'is_registered')}")
    
    if hasattr(container, 'is_registered'):
        # 获取方法源码
        import inspect
        try:
            source = inspect.getsource(container.is_registered)
            print(f"  is_registered方法源码:")
            for line in source.split('\n'):
                if line.strip():
                    print(f"    {line}")
        except Exception as e:
            print(f"  无法获取源码: {e}")

def main():
    # 配置日志以看到详细信息
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    deep_debug_registration()

if __name__ == "__main__":
    main()