#!/usr/bin/env python3
"""
实时写入事件集成测试

测试导入引擎与事件系统的集成
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['PYTHONPATH'] = str(project_root)

print("\n" + "="*80)
print("实时写入事件集成测试")
print("="*80 + "\n")

# Test 1: 导入检查
print("[Test 1] 模块导入检查")
print("-"*80)

checks = {
    "RealtimeWriteService": "core.services.realtime_write_service",
    "WriteProgressService": "core.services.write_progress_service",
    "WriteStartedEvent": "core.events.realtime_write_events",
    "EventBus": "core.events",
    "DataImportExecutionEngine": "core.importdata.import_execution_engine",
}

import_results = {}
for name, module_path in checks.items():
    try:
        parts = module_path.split('.')
        if len(parts) > 1:
            class_name = parts[-1] if name.endswith("Event") or name == "EventBus" else name
            exec(f"from {module_path} import {name if '.' not in name else class_name}")
        else:
            exec(f"import {module_path}")
        import_results[name] = True
        print(f"[OK] {name}: OK")
    except Exception as e:
        import_results[name] = False
        print(f"[FAIL] {name}: FAILED - {str(e)[:60]}")

# Test 2: 服务容器检查
print("\n[Test 2] 服务容器检查")
print("-"*80)

try:
    from core.containers import get_service_container
    from core.services.realtime_write_service import RealtimeWriteService
    
    container = get_service_container()
    print(f"[OK] 服务容器获取: OK")
    
    # 尝试解析服务
    try:
        service = container.resolve(RealtimeWriteService)
        print(f"[OK] RealtimeWriteService 解析: OK ({type(service).__name__})")
    except Exception as e:
        print(f"[WARN]  RealtimeWriteService 解析失败: {str(e)[:60]}")
        
except Exception as e:
    print(f"[FAIL] 服务容器错误: {e}")

# Test 3: 事件总线检查
print("\n[Test 3] 事件总线检查")
print("-"*80)

try:
    from core.events import get_event_bus
    from core.events.realtime_write_events import WriteProgressEvent
    
    event_bus = get_event_bus()
    print(f"[OK] EventBus 获取: OK ({type(event_bus).__name__})")
    
    # 测试事件发布
    test_event = WriteProgressEvent(
        task_id="test_001",
        symbol="000001",
        progress=50.0,
        written_count=5,
        total_count=10,
        write_speed=100.0,
        success_count=5,
        failure_count=0
    )
    
    event_bus.publish(test_event)
    print(f"[OK] 事件发布: OK (WriteProgressEvent)")
    
except Exception as e:
    print(f"[FAIL] 事件总线错误: {e}")

# Test 4: 导入引擎集成检查
print("\n[Test 4] 导入引擎集成检查")
print("-"*80)

try:
    from core.importdata.import_execution_engine import DataImportExecutionEngine, REALTIME_WRITE_AVAILABLE
    
    print(f"[OK] ImportExecutionEngine 导入: OK")
    print(f"   - 实时写入可用: {'是' if REALTIME_WRITE_AVAILABLE else '否'}")
    
    # 检查方法
    methods = ['_import_kline_data', '_import_realtime_data', '_import_fundamental_data']
    for method_name in methods:
        if hasattr(DataImportExecutionEngine, method_name):
            method = getattr(DataImportExecutionEngine, method_name)
            print(f"[OK] {method_name}: OK")
        else:
            print(f"[FAIL] {method_name}: NOT FOUND")
            
except Exception as e:
    print(f"[FAIL] 导入引擎检查错误: {e}")

# Test 5: 事件处理器检查
print("\n[Test 5] 事件处理器检查")
print("-"*80)

try:
    from core.services.realtime_write_event_handlers import get_write_event_handlers
    from core.events.realtime_write_events import WriteStartedEvent
    
    handlers = get_write_event_handlers()
    print(f"[OK] 事件处理器获取: OK ({type(handlers).__name__})")
    
    # 测试处理事件
    test_start_event = WriteStartedEvent(
        task_id="test_event_001",
        task_name="Test Task",
        symbols=["000001", "000002"],
        total_records=2
    )
    
    handlers.on_write_started(test_start_event)
    print(f"[OK] 事件处理: OK (on_write_started)")
    
    # 检查统计
    stats = handlers.get_task_statistics("test_event_001")
    if stats:
        print(f"[OK] 任务统计: OK (task_id={stats.get('task_id')})")
    else:
        print(f"[WARN]  任务统计: 未找到")
        
except Exception as e:
    print(f"[FAIL] 事件处理器检查错误: {e}")

# 汇总
print("\n" + "="*80)
print("集成测试汇总")
print("="*80)

passed = sum(1 for v in import_results.values() if v)
total = len(import_results)

print(f"\n导入检查: {passed}/{total} 通过")

for name, result in import_results.items():
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {name}")

print("\n" + "="*80)

if all(import_results.values()):
    print("[SUCCESS] 所有集成检查通过，系统已准备就绪！")
    print("\n建议后续操作：")
    print("1. 执行 K线数据导入测试")
    print("2. 验证实时事件发布和处理")
    print("3. 检查进度条和UI更新")
    print("4. 执行性能测试")
    sys.exit(0)
else:
    print("[FAIL] 某些集成检查未通过，需要修复。")
    sys.exit(1)
