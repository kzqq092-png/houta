#!/usr/bin/env python3
"""
测试深度优化模块注册状态的脚本
"""

import sys
import os

# 添加项目路径到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    print("🔍 测试深度优化模块注册状态...")
    print("=" * 60)
    
    try:
        # 导入服务容器
        from core.containers import get_service_container
        container = get_service_container()
        print("✅ 服务容器导入成功")
        
        # 定义要检查的深度优化服务
        optimization_services = [
            ('intelligent_cache', '智能缓存管理器'),
            ('component_virtualization', '组件虚拟化引擎'),
            ('websocket_client', 'WebSocket客户端'),
            ('smart_chart_recommender', '智能图表推荐器'),
            ('responsive_adapter', '响应式界面适配器'),
            ('unified_optimization_service', '统一优化服务')
        ]
        
        print("\n📋 深度优化模块注册检查:")
        print("-" * 60)
        
        registered_count = 0
        total_count = len(optimization_services)
        
        for service_name, display_name in optimization_services:
            try:
                if container.is_registered(service_name):
                    print(f"✅ {display_name:20} ({service_name}) - 已注册")
                    registered_count += 1
                else:
                    print(f"❌ {display_name:20} ({service_name}) - 未注册")
            except Exception as e:
                print(f"⚠️  {display_name:20} ({service_name}) - 检查失败: {e}")
        
        print("-" * 60)
        print(f"📊 注册状态: {registered_count}/{total_count} 个深度优化模块已注册")
        
        if registered_count == total_count:
            print("🎉 所有深度优化模块都已成功注册!")
            
            # 测试解析并获取状态
            print("\n🔧 测试服务解析和功能验证:")
            print("-" * 60)
            
            try:
                unified_service = container.resolve('unified_optimization_service')
                print(f"✅ 统一优化服务解析成功: {type(unified_service).__name__}")
                
                if hasattr(unified_service, 'get_available_modules'):
                    modules = unified_service.get_available_modules()
                    print(f"📦 可用模块: {list(modules.keys())}")
                    
            except Exception as e:
                print(f"⚠️  统一优化服务测试失败: {e}")
                
        else:
            print("⚠️  部分深度优化模块未注册，需要进一步检查")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()