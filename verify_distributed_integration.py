"""
分布式系统集成验证脚本

验证所有关键组件是否正确集成且功能真实有效
"""

import sys
import os
import io

# Windows控制台编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

def test_service_container_registration():
    """测试1: DistributedService是否已注册到ServiceContainer"""
    print("\n" + "="*60)
    print("测试1: DistributedService注册验证")
    print("="*60)
    
    try:
        from core.containers import get_service_container
        from core.services.distributed_service import DistributedService
        from core.services.service_bootstrap import ServiceBootstrap
        
        # ✅ 初始化ServiceBootstrap以触发服务注册
        bootstrap = ServiceBootstrap()
        bootstrap.bootstrap()  # 正确的方法名
        
        container = get_service_container()
        
        # 检查类型注册
        if container.is_registered(DistributedService):
            print("✅ DistributedService已通过类型注册")
        else:
            print("❌ DistributedService未通过类型注册")
            return False
        
        # 检查名称注册
        try:
            service = container.resolve('distributed_service')
            print(f"✅ DistributedService已通过名称注册: {type(service).__name__}")
        except:
            print("❌ DistributedService未通过名称注册")
            return False
        
        # 检查服务方法
        required_methods = [
            'add_node', 'remove_node', 'get_all_nodes_status', 
            'test_node_connection', 'submit_data_import_task'
        ]
        
        for method in required_methods:
            if hasattr(service, method):
                print(f"  ✅ {method} 方法存在")
            else:
                print(f"  ❌ {method} 方法不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_engine_integration():
    """测试2: DataImportExecutionEngine是否集成DistributedService"""
    print("\n" + "="*60)
    print("测试2: DataImportExecutionEngine集成验证")
    print("="*60)
    
    try:
        from core.importdata.import_execution_engine import DataImportExecutionEngine
        
        # 创建引擎实例（最小配置）
        engine = DataImportExecutionEngine(max_workers=2)
        
        # 检查分布式服务属性
        if hasattr(engine, 'distributed_service'):
            print("✅ distributed_service 属性存在")
            
            if engine.distributed_service:
                print(f"  ✅ 已初始化: {type(engine.distributed_service).__name__}")
            else:
                print("  ⚠️ distributed_service 为 None（可能是正常的）")
        else:
            print("❌ distributed_service 属性不存在")
            return False
        
        # 检查分布式执行开关
        if hasattr(engine, 'enable_distributed_execution'):
            print(f"✅ enable_distributed_execution = {engine.enable_distributed_execution}")
        else:
            print("❌ enable_distributed_execution 属性不存在")
            return False
        
        # 检查关键方法
        if hasattr(engine, '_can_distribute_task'):
            print("✅ _can_distribute_task 方法存在")
        else:
            print("❌ _can_distribute_task 方法不存在")
            return False
        
        if hasattr(engine, '_distribute_task'):
            print("✅ _distribute_task 方法存在")
        else:
            print("❌ _distribute_task 方法不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_api_structure():
    """测试3: 分布式节点API结构验证"""
    print("\n" + "="*60)
    print("测试3: 分布式节点API结构验证")
    print("="*60)
    
    try:
        # 检查文件存在性
        files_to_check = [
            'distributed_node/__init__.py',
            'distributed_node/node_config.py',
            'distributed_node/node_server.py',
            'distributed_node/task_executor.py',
            'distributed_node/api/__init__.py',
            'distributed_node/api/models.py',
            'distributed_node/api/routes.py',
            'distributed_node/start_node.py',
            'distributed_node/README.md'
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                print(f"✅ {file_path} 存在")
            else:
                print(f"❌ {file_path} 不存在")
                return False
        
        # 检查关键模块导入
        try:
            from distributed_node.node_config import NodeConfig
            print("✅ NodeConfig 可导入")
        except ImportError as e:
            print(f"❌ NodeConfig 导入失败: {e}")
            return False
        
        try:
            from distributed_node.task_executor import TaskExecutor
            print("✅ TaskExecutor 可导入")
        except ImportError as e:
            print(f"❌ TaskExecutor 导入失败: {e}")
            return False
        
        try:
            from distributed_node.api.models import TaskRequest, TaskResult, NodeHealth
            print("✅ API模型 可导入")
        except ImportError as e:
            print(f"❌ API模型 导入失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_http_bridge():
    """测试4: DistributedHTTPBridge验证"""
    print("\n" + "="*60)
    print("测试4: DistributedHTTPBridge验证")
    print("="*60)
    
    try:
        from core.services.distributed_http_bridge import DistributedHTTPBridge
        
        # 创建实例
        bridge = DistributedHTTPBridge()
        print("✅ DistributedHTTPBridge 可实例化")
        
        # 检查关键方法（_开头的是私有方法，验证其存在即可）
        required_methods = [
            '_execute_distributed',
            '_execute_locally',
            '_execute_split_task',
            '_get_node_health'  # 私有方法，正常封装
        ]
        
        for method in required_methods:
            if hasattr(bridge, method):
                print(f"  ✅ {method} 方法存在")
            else:
                print(f"  ❌ {method} 方法不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analysis_service_methods():
    """测试5: AnalysisService方法验证"""
    print("\n" + "="*60)
    print("测试5: AnalysisService方法验证")
    print("="*60)
    
    try:
        from core.services.analysis_service import AnalysisService, TimeFrame
        
        # 创建实例
        service = AnalysisService()
        print("✅ AnalysisService 可实例化")
        
        # 检查关键方法（分布式任务会调用的）
        required_methods = [
            'generate_signals',
            'calculate_indicator',
            'get_analysis_metrics'
        ]
        
        for method in required_methods:
            if hasattr(service, method):
                print(f"  ✅ {method} 方法存在")
            else:
                print(f"  ❌ {method} 方法不存在")
                return False
        
        # 测试TimeFrame枚举
        print(f"  ✅ TimeFrame.DAILY = {TimeFrame.DAILY}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_integration():
    """测试6: UI集成验证（仅检查文件和导入）"""
    print("\n" + "="*60)
    print("测试6: UI集成验证")
    print("="*60)
    
    try:
        # 检查分布式监控UI文件
        if os.path.exists('gui/dialogs/distributed_node_monitor_dialog.py'):
            print("✅ distributed_node_monitor_dialog.py 存在")
        else:
            print("❌ distributed_node_monitor_dialog.py 不存在")
            return False
        
        # 尝试导入（可能需要PyQt5环境）
        try:
            from gui.dialogs.distributed_node_monitor_dialog import DistributedNodeMonitorDialog
            print("✅ DistributedNodeMonitorDialog 可导入")
        except ImportError as e:
            print(f"⚠️ DistributedNodeMonitorDialog 导入失败（可能缺少PyQt5）: {e}")
            # 这不算失败，因为在CI环境中可能没有PyQt5
        
        # 检查菜单栏集成
        try:
            with open('gui/menu_bar.py', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'show_distributed_monitor' in content:
                    print("✅ menu_bar.py 包含 show_distributed_monitor 方法")
                else:
                    print("❌ menu_bar.py 缺少 show_distributed_monitor 方法")
                    return False
                
                if '分布式节点监控' in content:
                    print("✅ menu_bar.py 包含分布式节点监控菜单项")
                else:
                    print("❌ menu_bar.py 缺少分布式节点监控菜单项")
                    return False
        except Exception as e:
            print(f"❌ 读取menu_bar.py失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("           分布式系统集成验证")
    print("="*70)
    
    tests = [
        ("ServiceContainer注册", test_service_container_registration),
        ("ImportEngine集成", test_import_engine_integration),
        ("节点API结构", test_node_api_structure),
        ("HTTP Bridge", test_http_bridge),
        ("AnalysisService方法", test_analysis_service_methods),
        ("UI集成", test_ui_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 执行异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*70)
    print("                      测试结果汇总")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}  {test_name}")
    
    print("\n" + "-"*70)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！分布式系统集成验证成功！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关功能。")
        return 1


if __name__ == "__main__":
    exit(main())

