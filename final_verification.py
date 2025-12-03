#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度优化模块注册状态最终验证脚本
使用正确的方法检查注册状态
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

def final_verification():
    print("🔍 深度优化模块注册状态最终验证")
    print("=" * 60)
    
    try:
        from core.services.service_bootstrap import ServiceBootstrap
        from core.advanced_optimization.cache.intelligent_cache import IntelligentCache
        from core.advanced_optimization.performance.virtualization import VirtualScrollRenderer
        from core.advanced_optimization.timing.websocket_client import RealTimeDataProcessor
        from core.advanced_optimization.ai.smart_chart_recommender import UserBehaviorAnalyzer
        from core.advanced_optimization.ui.responsive_adapter import ResponsiveLayoutManager
        from core.advanced_optimization.unified_optimization_service import UnifiedOptimizationService
        
        print("✅ 所有模块导入成功")
        print()
        
        # 初始化服务容器和引导
        bootstrap = ServiceBootstrap()
        container = bootstrap.service_container
        
        print("🏗️ 执行模块注册...")
        
        # 执行注册过程
        try:
            bootstrap._register_intelligent_cache()
            print("✅ IntelligentCache 注册完成")
        except Exception as e:
            print(f"❌ IntelligentCache 注册失败: {e}")
            
        try:
            bootstrap._register_component_virtualization()
            print("✅ VirtualScrollRenderer 注册完成")
        except Exception as e:
            print(f"❌ VirtualScrollRenderer 注册失败: {e}")
            
        try:
            bootstrap._register_websocket_client()
            print("✅ RealTimeDataProcessor 注册完成")
        except Exception as e:
            print(f"❌ RealTimeDataProcessor 注册失败: {e}")
            
        try:
            bootstrap._register_smart_chart_recommender()
            print("✅ UserBehaviorAnalyzer 注册完成")
        except Exception as e:
            print(f"❌ UserBehaviorAnalyzer 注册失败: {e}")
            
        try:
            bootstrap._register_responsive_adapter()
            print("✅ ResponsiveLayoutManager 注册完成")
        except Exception as e:
            print(f"❌ ResponsiveLayoutManager 注册失败: {e}")
            
        try:
            bootstrap._register_unified_optimization_service()
            print("✅ UnifiedOptimizationService 注册完成")
        except Exception as e:
            print(f"❌ UnifiedOptimizationService 注册失败: {e}")
        
        print()
        print("📊 注册状态验证:")
        print("-" * 40)
        
        # 正确的注册状态检查
        verification_results = {}
        
        # 检查IntelligentCache
        print("🧠 IntelligentCache:")
        try:
            # 按类型检查
            type_registered = container.is_registered(IntelligentCache)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            # 按名称检查 - 使用ServiceRegistry的方法
            registry = container._registry
            name_registered = registry.get_service_info_by_name('intelligent_cache') is not None
            print(f"   按名称检查 (intelligent_cache): {'✅ 已注册' if name_registered else '❌ 未注册'}")
            
            name_registered2 = registry.get_service_info_by_name('cache_manager') is not None
            print(f"   按名称检查 (cache_manager): {'✅ 已注册' if name_registered2 else '❌ 未注册'}")
            
            verification_results['IntelligentCache'] = type_registered or name_registered or name_registered2
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['IntelligentCache'] = False
        
        # 检查VirtualScrollRenderer
        print("\n🔄 VirtualScrollRenderer:")
        try:
            type_registered = container.is_registered(VirtualScrollRenderer)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            registry = container._registry
            name_registered = registry.get_service_info_by_name('component_virtualization') is not None
            print(f"   按名称检查 (component_virtualization): {'✅ 已注册' if name_registered else '❌ 未注册'}")
            
            verification_results['VirtualScrollRenderer'] = type_registered or name_registered
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['VirtualScrollRenderer'] = False
        
        # 检查RealTimeDataProcessor
        print("\n🌐 RealTimeDataProcessor:")
        try:
            type_registered = container.is_registered(RealTimeDataProcessor)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            registry = container._registry
            name_registered1 = registry.get_service_info_by_name('websocket_client') is not None
            print(f"   按名称检查 (websocket_client): {'✅ 已注册' if name_registered1 else '❌ 未注册'}")
            
            name_registered2 = registry.get_service_info_by_name('ws_client') is not None
            print(f"   按名称检查 (ws_client): {'✅ 已注册' if name_registered2 else '❌ 未注册'}")
            
            verification_results['RealTimeDataProcessor'] = type_registered or name_registered1 or name_registered2
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['RealTimeDataProcessor'] = False
        
        # 检查UserBehaviorAnalyzer
        print("\n📊 UserBehaviorAnalyzer:")
        try:
            type_registered = container.is_registered(UserBehaviorAnalyzer)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            registry = container._registry
            name_registered1 = registry.get_service_info_by_name('smart_chart_recommender') is not None
            print(f"   按名称检查 (smart_chart_recommender): {'✅ 已注册' if name_registered1 else '❌ 未注册'}")
            
            name_registered2 = registry.get_service_info_by_name('chart_recommender') is not None
            print(f"   按名称检查 (chart_recommender): {'✅ 已注册' if name_registered2 else '❌ 未注册'}")
            
            verification_results['UserBehaviorAnalyzer'] = type_registered or name_registered1 or name_registered2
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['UserBehaviorAnalyzer'] = False
        
        # 检查ResponsiveLayoutManager
        print("\n📱 ResponsiveLayoutManager:")
        try:
            type_registered = container.is_registered(ResponsiveLayoutManager)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            registry = container._registry
            name_registered1 = registry.get_service_info_by_name('responsive_adapter') is not None
            print(f"   按名称检查 (responsive_adapter): {'✅ 已注册' if name_registered1 else '❌ 未注册'}")
            
            name_registered2 = registry.get_service_info_by_name('ui_adapter') is not None
            print(f"   按名称检查 (ui_adapter): {'✅ 已注册' if name_registered2 else '❌ 未注册'}")
            
            verification_results['ResponsiveLayoutManager'] = type_registered or name_registered1 or name_registered2
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['ResponsiveLayoutManager'] = False
        
        # 检查UnifiedOptimizationService
        print("\n🎯 UnifiedOptimizationService:")
        try:
            type_registered = container.is_registered(UnifiedOptimizationService)
            print(f"   按类型检查: {'✅ 已注册' if type_registered else '❌ 未注册'}")
            
            registry = container._registry
            name_registered1 = registry.get_service_info_by_name('unified_optimization_service') is not None
            print(f"   按名称检查 (unified_optimization_service): {'✅ 已注册' if name_registered1 else '❌ 未注册'}")
            
            name_registered2 = registry.get_service_info_by_name('optimization_service') is not None
            print(f"   按名称检查 (optimization_service): {'✅ 已注册' if name_registered2 else '❌ 未注册'}")
            
            verification_results['UnifiedOptimizationService'] = type_registered or name_registered1 or name_registered2
            
        except Exception as e:
            print(f"   ❌ 检查失败: {e}")
            verification_results['UnifiedOptimizationService'] = False
        
        print()
        print("📋 最终统计:")
        print("-" * 40)
        
        registered_count = sum(1 for result in verification_results.values() if result)
        total_count = len(verification_results)
        
        print(f"已注册模块: {registered_count}/{total_count}")
        
        for module, status in verification_results.items():
            print(f"  {'✅' if status else '❌'} {module}")
        
        if registered_count == total_count:
            print("\n🎉 所有深度优化模块注册成功！")
        else:
            print(f"\n⚠️  仍有 {total_count - registered_count} 个模块未注册")
            
        return verification_results
        
    except Exception as e:
        print(f"❌ 验证过程失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

if __name__ == "__main__":
    results = final_verification()