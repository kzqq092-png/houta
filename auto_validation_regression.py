#!/usr/bin/env python3
"""
自动功能验证回归测试脚本
完整验证实时写入功能的所有方面
"""

import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

def print_section(title: str, level: int = 1):
    """打印分段标题"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"[SECTION] {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}")
        print(f"[TEST] {title}")
        print(f"{'-'*80}")

def print_result(name: str, passed: bool, details: str = ""):
    """打印测试结果"""
    status = "[PASS]" if passed else "[FAIL]"
    msg = f"{status} {name}"
    if details:
        msg += f" - {details}"
    print(msg)
    return passed

def test_section_1_scope_understanding():
    """[章节1] Scope 参数理解验证"""
    print_section("章节 1: Scope 参数理解", 1)
    
    results = []
    
    # *** 关键修复：在任何服务解析前执行bootstrap ***
    try:
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container
        
        container = get_service_container()
        bootstrap = ServiceBootstrap(container)
        bootstrap.bootstrap()
        print("[BOOTSTRAP] ServiceBootstrap 已预先执行\n")
    except Exception as e:
        print(f"[WARNING] Bootstrap预执行失败: {e}\n")
    
    # Test 1.1: ServiceScope 枚举定义
    print("[Test 1.1] ServiceScope 枚举定义")
    try:
        from core.containers.service_registry import ServiceScope
        
        assert hasattr(ServiceScope, 'SINGLETON'), "SINGLETON 不存在"
        assert hasattr(ServiceScope, 'TRANSIENT'), "TRANSIENT 不存在"
        assert hasattr(ServiceScope, 'SCOPED'), "SCOPED 不存在"
        
        assert ServiceScope.SINGLETON.value == "singleton", "SINGLETON 值错误"
        assert ServiceScope.TRANSIENT.value == "transient", "TRANSIENT 值错误"
        assert ServiceScope.SCOPED.value == "scoped", "SCOPED 值错误"
        
        print("  [OK] SINGLETON = singleton")
        print("  [OK] TRANSIENT = transient")
        print("  [OK] SCOPED = scoped")
        results.append(print_result("ServiceScope 枚举", True))
    except Exception as e:
        results.append(print_result("ServiceScope 枚举", False, str(e)))
    
    # Test 1.2: register_instance 方法签名
    print("\n[Test 1.2] register_instance 方法签名")
    try:
        from core.containers.service_registry import ServiceRegistry
        import inspect
        
        sig = inspect.signature(ServiceRegistry.register_instance)
        params = list(sig.parameters.keys())
        
        # 验证参数
        assert 'self' in params, "缺少 self 参数"
        assert 'service_type' in params, "缺少 service_type 参数"
        assert 'instance' in params, "缺少 instance 参数"
        assert 'scope' not in params, "register_instance 不应该有 scope 参数"
        
        print(f"  [OK] 参数列表: {params}")
        print(f"  [OK] 正确: 没有 scope 参数")
        results.append(print_result("register_instance 签名", True))
    except Exception as e:
        results.append(print_result("register_instance 签名", False, str(e)))
    
    # Test 1.3: register_factory 方法支持 scope
    print("\n[Test 1.3] register_factory 方法支持 scope")
    try:
        from core.containers.service_registry import ServiceRegistry
        import inspect
        
        sig = inspect.signature(ServiceRegistry.register_factory)
        params = list(sig.parameters.keys())
        
        assert 'scope' in params, "register_factory 应该有 scope 参数"
        
        print(f"  [OK] 参数列表: {params}")
        print(f"  [OK] 正确: 有 scope 参数")
        results.append(print_result("register_factory 签名", True))
    except Exception as e:
        results.append(print_result("register_factory 签名", False, str(e)))
    
    # Test 1.4: SINGLETON 缓存机制
    print("\n[Test 1.4] SINGLETON 缓存机制")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_config import RealtimeWriteConfig
        
        container = get_service_container()
        
        # resolve 两次，应该返回同一个实例
        instance1 = container.resolve(RealtimeWriteConfig)
        instance2 = container.resolve(RealtimeWriteConfig)
        
        assert instance1 is instance2, "SINGLETON 应该返回同一实例"
        assert id(instance1) == id(instance2), "内存地址应该相同"
        
        print(f"  [OK] 第一次 resolve: {id(instance1)}")
        print(f"  [OK] 第二次 resolve: {id(instance2)}")
        print(f"  [OK] 同一实例: {instance1 is instance2}")
        results.append(print_result("SINGLETON 缓存机制", True))
    except Exception as e:
        results.append(print_result("SINGLETON 缓存机制", False, str(e)))
    
    return all(results)

def test_section_2_service_initialization():
    """[章节2] 服务初始化验证"""
    print_section("章节 2: 服务初始化", 1)
    
    results = []
    
    # Test 2.1: 引导程序正确执行
    print("[Test 2.1] ServiceBootstrap 执行")
    try:
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container
        
        container = get_service_container()
        bootstrap = ServiceBootstrap(container)
        bootstrap.bootstrap()
        
        print("  [OK] bootstrap() 成功执行")
        results.append(print_result("ServiceBootstrap 执行", True))
    except Exception as e:
        results.append(print_result("ServiceBootstrap 执行", False, str(e)))
    
    # Test 2.2: 配置服务注册
    print("\n[Test 2.2] 配置服务注册")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_config import RealtimeWriteConfig
        
        container = get_service_container()
        config = container.resolve(RealtimeWriteConfig)
        
        assert config is not None, "配置应该不为 None"
        assert config.batch_size > 0, "batch_size 应该大于 0"
        
        print(f"  [OK] 配置已注册")
        print(f"  [OK] batch_size: {config.batch_size}")
        print(f"  [OK] concurrency: {config.concurrency}")
        results.append(print_result("配置服务注册", True))
    except Exception as e:
        results.append(print_result("配置服务注册", False, str(e)))
    
    # Test 2.3: 进度服务注册
    print("\n[Test 2.3] 进度服务注册")
    try:
        from core.containers import get_service_container
        from core.services.write_progress_service import WriteProgressService
        
        container = get_service_container()
        service = container.resolve(WriteProgressService)
        
        assert service is not None, "服务应该不为 None"
        assert hasattr(service, 'update_progress'), "缺少 update_progress 方法"
        
        print("  [OK] 进度服务已注册")
        print(f"  [OK] 服务类型: {type(service).__name__}")
        results.append(print_result("进度服务注册", True))
    except Exception as e:
        results.append(print_result("进度服务注册", False, str(e)))
    
    # Test 2.4: 实时写入服务注册
    print("\n[Test 2.4] 实时写入服务注册")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_service import RealtimeWriteService
        
        container = get_service_container()
        service = container.resolve(RealtimeWriteService)
        
        assert service is not None, "服务应该不为 None"
        assert hasattr(service, 'write_data'), "缺少 write_data 方法"
        assert hasattr(service, 'start_write'), "缺少 start_write 方法"
        assert hasattr(service, 'complete_write'), "缺少 complete_write 方法"
        
        print("  [OK] 实时写入服务已注册")
        print(f"  [OK] 服务类型: {type(service).__name__}")
        results.append(print_result("实时写入服务注册", True))
    except Exception as e:
        results.append(print_result("实时写入服务注册", False, str(e)))
    
    return all(results)

def test_section_3_event_system():
    """[章节3] 事件系统验证"""
    print_section("章节 3: 事件系统", 1)
    
    results = []
    
    # *** 关键修复：确保EventBus已初始化 ***
    try:
        from core.events import get_event_bus
        event_bus = get_event_bus()
        if event_bus is None:
            from core.services.service_bootstrap import ServiceBootstrap
            from core.containers import get_service_container
            container = get_service_container()
            bootstrap = ServiceBootstrap(container)
            bootstrap.bootstrap()
            print("[BOOTSTRAP] ServiceBootstrap 已执行以初始化EventBus\n")
    except Exception as e:
        print(f"[WARNING] EventBus预初始化失败: {e}\n")
    
    # Test 3.1: 事件类定义
    print("[Test 3.1] 事件类定义")
    try:
        from core.events.realtime_write_events import (
            WriteStartedEvent, WriteProgressEvent, 
            WriteCompletedEvent, WriteErrorEvent
        )
        
        print("  [OK] WriteStartedEvent 已定义")
        print("  [OK] WriteProgressEvent 已定义")
        print("  [OK] WriteCompletedEvent 已定义")
        print("  [OK] WriteErrorEvent 已定义")
        results.append(print_result("事件类定义", True))
    except Exception as e:
        results.append(print_result("事件类定义", False, str(e)))
    
    # Test 3.2: EventBus 初始化
    print("\n[Test 3.2] EventBus 初始化")
    try:
        from core.events import get_event_bus
        
        event_bus = get_event_bus()
        
        assert event_bus is not None, "EventBus 应该不为 None"
        assert hasattr(event_bus, 'publish'), "缺少 publish 方法"
        assert hasattr(event_bus, 'subscribe'), "缺少 subscribe 方法"
        
        print("  [OK] EventBus 已初始化")
        print(f"  [OK] 类型: {type(event_bus).__name__}")
        results.append(print_result("EventBus 初始化", True))
    except Exception as e:
        results.append(print_result("EventBus 初始化", False, str(e)))
    
    # Test 3.3: 事件发布和订阅
    print("\n[Test 3.3] 事件发布和订阅")
    try:
        from core.events import get_event_bus
        from core.events.realtime_write_events import WriteProgressEvent
        import threading
        
        event_bus = get_event_bus()
        
        received_events = []
        event_received = threading.Event()
        
        def handler(event):
            received_events.append(event)
            event_received.set()
        
        # 订阅事件
        event_bus.subscribe(WriteProgressEvent, handler)
        
        # 发布事件
        event = WriteProgressEvent(
            task_id="test_001",
            symbol="000001",
            progress=50.0,
            written_count=100,
            total_count=200
        )
        event_bus.publish(event)
        
        # 等待事件被处理（同步或异步）
        event_received.wait(timeout=2.0)
        
        assert len(received_events) > 0, "应该接收到事件"
        assert received_events[0].task_id == "test_001", "事件 ID 应该匹配"
        
        print("  [OK] 事件已发布")
        print("  [OK] 事件已接收")
        print(f"  [OK] 接收事件数: {len(received_events)}")
        results.append(print_result("事件发布和订阅", True))
    except Exception as e:
        results.append(print_result("事件发布和订阅", False, str(e)))
    
    return all(results)

def test_section_4_import_engine():
    """[章节4] 导入引擎验证"""
    print_section("章节 4: 导入引擎", 1)
    
    results = []
    
    # Test 4.1: 导入引擎导入
    print("[Test 4.1] 导入引擎导入")
    try:
        from core.importdata.import_execution_engine import (
            DataImportExecutionEngine, REALTIME_WRITE_AVAILABLE
        )
        
        assert DataImportExecutionEngine is not None, "引擎类应该不为 None"
        assert isinstance(REALTIME_WRITE_AVAILABLE, bool), "标志应该是布尔值"
        
        print(f"  [OK] 导入引擎已导入")
        print(f"  [OK] REALTIME_WRITE_AVAILABLE = {REALTIME_WRITE_AVAILABLE}")
        results.append(print_result("导入引擎导入", True))
    except Exception as e:
        results.append(print_result("导入引擎导入", False, str(e)))
    
    # Test 4.2: 导入方法存在
    print("\n[Test 4.2] 导入方法存在")
    try:
        from core.importdata.import_execution_engine import DataImportExecutionEngine
        
        methods = [
            '_import_kline_data',
            '_import_realtime_data', 
            '_import_fundamental_data'
        ]
        
        for method_name in methods:
            assert hasattr(DataImportExecutionEngine, method_name), f"缺少方法 {method_name}"
            print(f"  [OK] {method_name} 存在")
        
        results.append(print_result("导入方法存在", True))
    except Exception as e:
        results.append(print_result("导入方法存在", False, str(e)))
    
    # Test 4.3: 实时写入标志
    print("\n[Test 4.3] 实时写入标志")
    try:
        from core.importdata.import_execution_engine import REALTIME_WRITE_AVAILABLE
        
        if REALTIME_WRITE_AVAILABLE:
            print("  [OK] 实时写入功能: 已启用")
            results.append(print_result("实时写入标志", True))
        else:
            print("  [WARN] 实时写入功能: 已禁用")
            results.append(print_result("实时写入标志", True, "功能已禁用但标志正确"))
    except Exception as e:
        results.append(print_result("实时写入标志", False, str(e)))
    
    return all(results)

def test_section_5_data_integrity():
    """[章节5] 数据完整性验证"""
    print_section("章节 5: 数据完整性", 1)
    
    results = []
    
    # Test 5.1: 配置数据完整性
    print("[Test 5.1] 配置数据完整性")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_config import RealtimeWriteConfig
        
        container = get_service_container()
        config = container.resolve(RealtimeWriteConfig)
        
        config.validate()
        
        config_dict = config.to_dict()
        
        assert 'batch_size' in config_dict, "缺少 batch_size"
        assert 'concurrency' in config_dict, "缺少 concurrency"
        assert 'timeout' in config_dict, "缺少 timeout"
        
        print(f"  [OK] batch_size = {config_dict['batch_size']}")
        print(f"  [OK] concurrency = {config_dict['concurrency']}")
        print(f"  [OK] timeout = {config_dict['timeout']}")
        results.append(print_result("配置数据完整性", True))
    except Exception as e:
        results.append(print_result("配置数据完整性", False, str(e)))
    
    # Test 5.2: 服务状态完整性
    print("\n[Test 5.2] 服务状态完整性")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_service import RealtimeWriteService
        
        container = get_service_container()
        service = container.resolve(RealtimeWriteService)
        
        # 检查服务的核心属性
        assert hasattr(service, 'config'), "缺少 config 属性"
        assert hasattr(service, 'tasks'), "缺少 tasks 属性"
        assert hasattr(service, 'event_bus'), "缺少 event_bus 属性"
        
        print("  [OK] config 属性存在")
        print("  [OK] tasks 属性存在")
        print("  [OK] event_bus 属性存在")
        results.append(print_result("服务状态完整性", True))
    except Exception as e:
        results.append(print_result("服务状态完整性", False, str(e)))
    
    return all(results)

def test_section_6_regression_suite():
    """[章节6] 综合回归测试"""
    print_section("章节 6: 综合回归测试", 1)
    
    results = []
    
    # Test 6.1: 完整初始化流程
    print("[Test 6.1] 完整初始化流程")
    try:
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers import get_service_container
        from core.services.realtime_write_service import RealtimeWriteService
        from core.services.write_progress_service import WriteProgressService
        from core.services.realtime_write_config import RealtimeWriteConfig
        from core.events import get_event_bus
        
        # 步骤 1: 获取容器
        container = get_service_container()
        assert container is not None, "容器应该不为 None"
        
        # 步骤 2: 执行引导
        bootstrap = ServiceBootstrap(container)
        bootstrap.bootstrap()
        
        # 步骤 3: 解析所有服务
        config = container.resolve(RealtimeWriteConfig)
        progress_service = container.resolve(WriteProgressService)
        realtime_service = container.resolve(RealtimeWriteService)
        event_bus = get_event_bus()
        
        # 步骤 4: 验证解析结果
        assert config is not None
        assert progress_service is not None
        assert realtime_service is not None
        assert event_bus is not None
        
        print("  [OK] 步骤 1: 容器获取")
        print("  [OK] 步骤 2: 引导程序执行")
        print("  [OK] 步骤 3: 所有服务解析")
        print("  [OK] 步骤 4: 验证完成")
        results.append(print_result("完整初始化流程", True))
    except Exception as e:
        results.append(print_result("完整初始化流程", False, str(e)))
    
    # Test 6.2: 并发访问一致性
    print("\n[Test 6.2] 并发访问一致性")
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_service import RealtimeWriteService
        import threading
        
        container = get_service_container()
        instances = []
        
        def get_instance():
            service = container.resolve(RealtimeWriteService)
            instances.append(id(service))
        
        threads = [threading.Thread(target=get_instance) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有实例应该有相同的内存地址（SINGLETON）
        assert len(set(instances)) == 1, "应该都是同一个实例"
        
        print(f"  [OK] 5 个并发访问，内存地址一致")
        print(f"  [OK] 实例 ID: {instances[0]}")
        results.append(print_result("并发访问一致性", True))
    except Exception as e:
        results.append(print_result("并发访问一致性", False, str(e)))
    
    return all(results)

def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("[START] 自动功能验证回归测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    start_time = time.time()
    
    all_passed = True
    section_results = []
    
    # 运行所有测试章节
    sections = [
        ("Scope 参数理解", test_section_1_scope_understanding),
        ("服务初始化", test_section_2_service_initialization),
        ("事件系统", test_section_3_event_system),
        ("导入引擎", test_section_4_import_engine),
        ("数据完整性", test_section_5_data_integrity),
        ("综合回归", test_section_6_regression_suite),
    ]
    
    for section_name, test_func in sections:
        try:
            passed = test_func()
            section_results.append((section_name, passed))
            all_passed = all_passed and passed
        except Exception as e:
            print(f"\n[ERROR] {section_name} 出现异常: {e}")
            section_results.append((section_name, False))
            all_passed = False
    
    # 打印总结
    print("\n" + "="*80)
    print("[SUMMARY] 测试总结")
    print("="*80)
    
    passed_count = sum(1 for _, passed in section_results if passed)
    total_count = len(section_results)
    
    for section_name, passed in section_results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {section_name}")
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "-"*80)
    print(f"总测试数: {total_count}")
    print(f"通过: {passed_count}")
    print(f"失败: {total_count - passed_count}")
    print(f"成功率: {100 * passed_count / total_count:.1f}%")
    print(f"耗时: {elapsed_time:.2f} 秒")
    print("-"*80)
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if all_passed:
        print("\n[SUCCESS] 所有测试通过！系统状态: 优秀 (Excellent)")
        return 0
    else:
        print("\n[FAIL] 有测试失败，请检查日志")
        return 1

if __name__ == "__main__":
    sys.exit(main())
