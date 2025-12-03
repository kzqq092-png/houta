#!/usr/bin/env python3
"""
深度优化模块注册调试脚本
"""

import sys
import os
import traceback
from loguru import logger

# 添加项目路径到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_import_module(module_path: str, description: str):
    """测试导入模块"""
    print(f"\n🔍 测试导入 {description} ({module_path})")
    print("-" * 60)
    
    try:
        module = __import__(module_path, fromlist=[''])
        print(f"✅ {description} 导入成功")
        
        # 检查关键类是否存在
        if 'intelligent_cache' in module_path:
            from core.advanced_optimization.cache.intelligent_cache import IntelligentCache
            print(f"   IntelligentCache 类存在: {IntelligentCache}")
        elif 'virtualization' in module_path:
            from core.advanced_optimization.performance.virtualization import VirtualScrollRenderer
            print(f"   VirtualScrollRenderer 类存在: {VirtualScrollRenderer}")
        elif 'websocket_client' in module_path:
            from core.advanced_optimization.timing.websocket_client import RealTimeDataProcessor
            print(f"   RealTimeDataProcessor 类存在: {RealTimeDataProcessor}")
        elif 'smart_chart_recommender' in module_path:
            from core.advanced_optimization.ai.smart_chart_recommender import UserBehaviorAnalyzer
            print(f"   UserBehaviorAnalyzer 类存在: {UserBehaviorAnalyzer}")
        elif 'responsive_adapter' in module_path:
            from core.advanced_optimization.ui.responsive_adapter import ResponsiveLayoutManager
            print(f"   ResponsiveLayoutManager 类存在: {ResponsiveLayoutManager}")
        elif 'unified_optimization_service' in module_path:
            from core.advanced_optimization.unified_optimization_service import UnifiedOptimizationService
            print(f"   UnifiedOptimizationService 类存在: {UnifiedOptimizationService}")
        
        return True
        
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print(f"   详细错误: {traceback.format_exc()}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        print(f"   详细错误: {traceback.format_exc()}")
        return False

def test_service_bootstrap():
    """测试服务引导过程"""
    print("\n🚀 测试服务引导过程")
    print("=" * 60)
    
    try:
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container
        
        container = get_service_container()
        bootstrap = ServiceBootstrap(container)
        
        print("✅ ServiceBootstrap 初始化成功")
        
        # 测试各个注册方法
        print("\n🔧 测试各个注册方法:")
        
        try:
            print("  测试 _register_intelligent_cache...")
            bootstrap._register_intelligent_cache()
            print("  ✅ _register_intelligent_cache 执行完成")
        except Exception as e:
            print(f"  ❌ _register_intelligent_cache 失败: {e}")
            
        try:
            print("  测试 _register_component_virtualization...")
            bootstrap._register_component_virtualization()
            print("  ✅ _register_component_virtualization 执行完成")
        except Exception as e:
            print(f"  ❌ _register_component_virtualization 失败: {e}")
            
        try:
            print("  测试 _register_websocket_client...")
            bootstrap._register_websocket_client()
            print("  ✅ _register_websocket_client 执行完成")
        except Exception as e:
            print(f"  ❌ _register_websocket_client 失败: {e}")
            
        try:
            print("  测试 _register_smart_chart_recommender...")
            bootstrap._register_smart_chart_recommender()
            print("  ✅ _register_smart_chart_recommender 执行完成")
        except Exception as e:
            print(f"  ❌ _register_smart_chart_recommender 失败: {e}")
            
        try:
            print("  测试 _register_responsive_adapter...")
            bootstrap._register_responsive_adapter()
            print("  ✅ _register_responsive_adapter 执行完成")
        except Exception as e:
            print(f"  ❌ _register_responsive_adapter 失败: {e}")
            
        try:
            print("  测试 _register_unified_optimization_service...")
            bootstrap._register_unified_optimization_service()
            print("  ✅ _register_unified_optimization_service 执行完成")
        except Exception as e:
            print(f"  ❌ _register_unified_optimization_service 失败: {e}")
            
        # 最终检查注册状态
        print("\n📋 最终注册状态检查:")
        
        services_to_check = [
            ('intelligent_cache', '智能缓存管理器'),
            ('component_virtualization', '组件虚拟化引擎'),
            ('websocket_client', 'WebSocket客户端'),
            ('smart_chart_recommender', '智能图表推荐器'),
            ('responsive_adapter', '响应式界面适配器'),
            ('unified_optimization_service', '统一优化服务')
        ]
        
        for service_name, display_name in services_to_check:
            if container.is_registered(service_name):
                print(f"  ✅ {display_name}: 已注册")
            else:
                print(f"  ❌ {display_name}: 未注册")
                
    except Exception as e:
        print(f"❌ 服务引导测试失败: {e}")
        print(f"详细错误: {traceback.format_exc()}")

def main():
    print("🔍 深度优化模块注册调试工具")
    print("=" * 60)
    
    # 测试每个模块的导入
    modules_to_test = [
        ('core.advanced_optimization.cache.intelligent_cache', '智能缓存管理器'),
        ('core.advanced_optimization.performance.virtualization', '组件虚拟化引擎'),
        ('core.advanced_optimization.timing.websocket_client', 'WebSocket客户端'),
        ('core.advanced_optimization.ai.smart_chart_recommender', '智能图表推荐器'),
        ('core.advanced_optimization.ui.responsive_adapter', '响应式界面适配器'),
        ('core.advanced_optimization.unified_optimization_service', '统一优化服务')
    ]
    
    import_success_count = 0
    for module_path, description in modules_to_test:
        if test_import_module(module_path, description):
            import_success_count += 1
    
    print(f"\n📊 导入测试总结: {import_success_count}/{len(modules_to_test)} 个模块导入成功")
    
    # 测试服务引导
    test_service_bootstrap()

if __name__ == "__main__":
    main()