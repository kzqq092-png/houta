#!/usr/bin/env python3
"""直接测试5个深度优化功能模块的注册"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_registration():
    """直接测试注册方法"""
    print("=" * 60)
    print("🔧 直接测试深度优化模块注册")
    print("=" * 60)
    
    try:
        # 1. 导入服务容器
        print("\n📋 第1步：导入服务容器...")
        from core.containers.service_container import ServiceContainer, ServiceScope
        
        # 2. 创建新的服务容器（避免冲突）
        print("\n📋 第2步：创建测试服务容器...")
        container = ServiceContainer()
        print(f"✅ 服务容器创建成功")
        
        # 3. 测试逐个注册每个模块
        print("\n📋 第3步：测试智能缓存管理器注册...")
        try:
            from core.advanced_optimization.cache.intelligent_cache import IntelligentCache
            
            def create_intelligent_cache():
                cache = IntelligentCache()
                return cache
            
            container.register_factory(
                IntelligentCache,
                create_intelligent_cache,
                scope=ServiceScope.SINGLETON
            )
            
            # 测试解析
            cache_instance = container.resolve(IntelligentCache)
            print(f"✅ 智能缓存管理器注册并解析成功: {type(cache_instance).__name__}")
            
        except Exception as e:
            print(f"❌ 智能缓存管理器注册失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n📋 第4步：测试组件虚拟化注册...")
        try:
            from core.advanced_optimization.performance.virtualization import VirtualScrollRenderer
            
            def create_virtual_scroll_renderer():
                renderer = VirtualScrollRenderer()
                return renderer
            
            container.register_factory(
                VirtualScrollRenderer,
                create_virtual_scroll_renderer,
                scope=ServiceScope.SINGLETON
            )
            
            # 测试解析
            renderer_instance = container.resolve(VirtualScrollRenderer)
            print(f"✅ 组件虚拟化注册并解析成功: {type(renderer_instance).__name__}")
            
        except Exception as e:
            print(f"❌ 组件虚拟化注册失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n📋 第5步：测试WebSocket客户端注册...")
        try:
            from core.advanced_optimization.timing.websocket_client import RealTimeDataProcessor
            
            def create_realtime_processor():
                processor = RealTimeDataProcessor()
                return processor
            
            container.register_factory(
                RealTimeDataProcessor,
                create_realtime_processor,
                scope=ServiceScope.SINGLETON
            )
            
            # 测试解析
            processor_instance = container.resolve(RealTimeDataProcessor)
            print(f"✅ WebSocket客户端注册并解析成功: {type(processor_instance).__name__}")
            
        except Exception as e:
            print(f"❌ WebSocket客户端注册失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n📋 第6步：测试智能图表推荐器注册...")
        try:
            from core.advanced_optimization.ai.smart_chart_recommender import UserBehaviorAnalyzer
            
            def create_user_analyzer():
                analyzer = UserBehaviorAnalyzer()
                return analyzer
            
            container.register_factory(
                UserBehaviorAnalyzer,
                create_user_analyzer,
                scope=ServiceScope.SINGLETON
            )
            
            # 测试解析
            analyzer_instance = container.resolve(UserBehaviorAnalyzer)
            print(f"✅ 智能图表推荐器注册并解析成功: {type(analyzer_instance).__name__}")
            
        except Exception as e:
            print(f"❌ 智能图表推荐器注册失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n📋 第7步：测试响应式界面适配器注册...")
        try:
            from core.advanced_optimization.ui.responsive_adapter import ResponsiveLayoutManager
            
            def create_layout_manager():
                manager = ResponsiveLayoutManager()
                return manager
            
            container.register_factory(
                ResponsiveLayoutManager,
                create_layout_manager,
                scope=ServiceScope.SINGLETON
            )
            
            # 测试解析
            manager_instance = container.resolve(ResponsiveLayoutManager)
            print(f"✅ 响应式界面适配器注册并解析成功: {type(manager_instance).__name__}")
            
        except Exception as e:
            print(f"❌ 响应式界面适配器注册失败: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("🎉 直接注册测试完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_registration()
    sys.exit(0 if success else 1)