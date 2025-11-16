#!/usr/bin/env python3
"""
实时写入集成验证脚本 - 精简版

快速验证核心功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("\n=== 实时写入集成验证 ===\n")

# 验证 1: 导入核心模块
print("[1/5] 验证核心模块...")
errors = []

try:
    from core.importdata.import_execution_engine import REALTIME_WRITE_AVAILABLE
    print(f"  [OK] REALTIME_WRITE_AVAILABLE = {REALTIME_WRITE_AVAILABLE}")
except ImportError as e:
    errors.append(f"导入引擎导入失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

try:
    from core.events.realtime_write_events import WriteStartedEvent, WriteProgressEvent
    print("  [OK] 事件类导入成功")
except ImportError as e:
    errors.append(f"事件类导入失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

try:
    from core.services.realtime_write_service import RealtimeWriteService
    print("  [OK] RealtimeWriteService 导入成功")
except ImportError as e:
    errors.append(f"服务导入失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

# 验证 2: 检查方法存在
print("\n[2/5] 验证导入方法...")

try:
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    
    methods = ['_import_kline_data', '_import_realtime_data', '_import_fundamental_data']
    for method in methods:
        if hasattr(DataImportExecutionEngine, method):
            print(f"  [OK] {method} 存在")
        else:
            errors.append(f"方法 {method} 不存在")
            print(f"  [FAIL] {errors[-1]}")
except Exception as e:
    errors.append(str(e))
    print(f"  [FAIL] {e}")

# 验证 3: 检查事件发布代码
print("\n[3/5] 验证事件发布代码...")

try:
    with open('core/importdata/import_execution_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    checks = {
        'WriteStartedEvent': 'WriteStartedEvent' in content,
        'WriteProgressEvent': 'WriteProgressEvent' in content,
        'WriteCompletedEvent': 'WriteCompletedEvent' in content,
        'event_bus.publish': 'event_bus.publish' in content,
    }
    
    for check, result in checks.items():
        if result:
            print(f"  [OK] {check} 代码存在")
        else:
            errors.append(f"{check} 代码未找到")
            print(f"  [FAIL] {errors[-1]}")
            
except Exception as e:
    errors.append(f"文件检查失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

# 验证 4: 检查服务初始化
print("\n[4/5] 验证服务初始化代码...")

try:
    with open('core/importdata/import_execution_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    init_checks = {
        'get_service_container': 'get_service_container' in content,
        'get_event_bus': 'get_event_bus' in content,
        'realtime_write_service.start_write': 'realtime_write_service.start_write' in content,
        'realtime_write_service.write_data': 'realtime_write_service.write_data' in content,
        'realtime_write_service.complete_write': 'realtime_write_service.complete_write' in content,
    }
    
    for check, result in init_checks.items():
        if result:
            print(f"  [OK] {check} 代码存在")
        else:
            errors.append(f"{check} 代码未找到")
            print(f"  [FAIL] {errors[-1]}")
            
except Exception as e:
    errors.append(f"代码检查失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

# 验证 5: 检查错误处理
print("\n[5/5] 验证错误处理代码...")

try:
    with open('core/importdata/import_execution_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    error_checks = {
        'WriteErrorEvent': 'WriteErrorEvent' in content,
        '异常捕获': 'except Exception' in content,
        '日志记录': 'logger.error' in content,
    }
    
    for check, result in error_checks.items():
        if result:
            print(f"  [OK] {check} 代码存在")
        else:
            errors.append(f"{check} 代码未找到")
            print(f"  [FAIL] {errors[-1]}")
            
except Exception as e:
    errors.append(f"错误检查失败: {e}")
    print(f"  [FAIL] {errors[-1]}")

# 输出结果
print("\n" + "="*40)
if errors:
    print(f"[FAIL] 验证失败，共 {len(errors)} 个问题：")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("[SUCCESS] 所有验证通过！")
    print("\n系统已准备好进行：")
    print("  1. 小规模数据导入测试 (5-10只股票)")
    print("  2. 事件流程验证")
    print("  3. 数据完整性检查")
    print("  4. 性能测试")
    sys.exit(0)
