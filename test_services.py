#!/usr/bin/env python3
"""测试5个深度优化功能模块的服务注册"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_service_registration():
    """测试服务注册"""
    print("=" * 60)
    print("🔧 测试5个深度优化功能模块服务注册")
    print("=" * 60)
    
    try:
        # 1. 测试服务引导
        print("\n📋 第1步：测试服务引导...")
        from core.services.service_bootstrap import bootstrap_services
        success = bootstrap_services()
        print(f"服务引导结果: {'✅ 成功' if success else '❌ 失败'}")
        
        if not success:
            print("❌ 服务引导失败，跳过后续测试")
            return False
        
        # 2. 检查服务容器
        print("\n📋 第2步：检查服务容器...")
        from core.containers.service_container import get_service_container
        container = get_service_container()
        
        # 3. 列出已注册的服务类型
        print("\n📋 第3步：列出已注册的深度优化模块...")
        
        # 定义要测试的模块
        test_services = [
            ("IntelligentCache", "智能缓存管理器"),
            ("VirtualScrollRenderer", "组件虚拟化"), 
            ("RealTimeDataProcessor", "WebSocket客户端"),
            ("UserBehaviorAnalyzer", "智能图表推荐器"),
            ("ResponsiveLayoutManager", "响应式界面适配器")
        ]
        
        success_count = 0
        for service_name, description in test_services:
            try:
                # 按类型解析
                print(f"\n🔍 测试 {description} ({service_name}):")
                
                # 尝试导入类
                if "IntelligentCache" in service_name:
                    from core.advanced_optimization.cache.intelligent_cache import IntelligentCache
                    service_class = IntelligentCache
                elif "VirtualScrollRenderer" in service_name:
                    from core.advanced_optimization.performance.virtualization import VirtualScrollRenderer
                    service_class = VirtualScrollRenderer
                elif "RealTimeDataProcessor" in service_name:
                    from core.advanced_optimization.timing.websocket_client import RealTimeDataProcessor
                    service_class = RealTimeDataProcessor
                elif "UserBehaviorAnalyzer" in service_name:
                    from core.advanced_optimization.ai.smart_chart_recommender import UserBehaviorAnalyzer
                    service_class = UserBehaviorAnalyzer
                elif "ResponsiveLayoutManager" in service_name:
                    from core.advanced_optimization.ui.responsive_adapter import ResponsiveLayoutManager
                    service_class = ResponsiveLayoutManager
                else:
                    print(f"   ❌ 未知服务类型: {service_name}")
                    continue
                
                # 尝试解析服务实例
                instance = container.resolve(service_class)
                print(f"   ✅ 按类型注册成功: {type(instance).__name__}")
                
                # 尝试按名称解析
                names_to_try = ['smart_chart_recommender', 'chart_recommender'] if 'UserBehaviorAnalyzer' in service_name \
                             else ['component_virtualization'] if 'VirtualScrollRenderer' in service_name \
                             else ['websocket_client', 'ws_client'] if 'RealTimeDataProcessor' in service_name \
                             else ['responsive_adapter', 'ui_adapter'] if 'ResponsiveLayoutManager' in service_name \
                             else ['intelligent_cache']
                
                name_success = False
                for name in names_to_try:
                    try:
                        named_instance = container.resolve(service_class, name=name)
                        print(f"   ✅ 按名称 '{name}' 注册成功")
                        name_success = True
                        break
                    except:
                        continue
                
                if not name_success:
                    print(f"   ⚠️ 按名称注册失败（可能未设置名称注册）")
                
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 4. 总结结果
        print(f"\n{'='*60}")
        print(f"📊 测试总结:")
        print(f"   总测试模块: {len(test_services)}")
        print(f"   成功注册: {success_count}")
        print(f"   成功率: {success_count/len(test_services)*100:.1f}%")
        
        if success_count == len(test_services):
            print("🎉 所有5个深度优化功能模块服务注册成功！")
            return True
        else:
            print("⚠️ 部分模块注册失败，需要进一步检查")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_service_registration()
    sys.exit(0 if success else 1)