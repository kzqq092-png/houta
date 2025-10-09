#!/usr/bin/env python
"""
深度调试磁盘metrics问题
"""

import sys
import psutil
import platform
import traceback

print("="*80)
print("深度调试磁盘metrics问题")
print("="*80)

print(f"\n系统信息:")
print(f"  平台: {platform.system()}")
print(f"  Python版本: {sys.version}")
print(f"  psutil版本: {psutil.__version__}")

# 测试不同的路径
test_paths = [
    "C:/",
    "C:\\\\",
    r"C:\\",
    "C:",
    "/",
]

print(f"\n测试psutil.disk_usage()...")
for path in test_paths:
    print(f"\n[测试] path = {repr(path)}")
    try:
        result = psutil.disk_usage(path)
        print(f"  ✅ 成功!")
        print(f"     total: {result.total / (1024**3):.1f} GB")
        print(f"     used:  {result.used / (1024**3):.1f} GB")
        print(f"     free:  {result.free / (1024**3):.1f} GB")
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        print(f"     类型: {type(e).__name__}")
        traceback.print_exc()

# 测试实际的_collect_disk_metrics方法
print(f"\n" + "="*80)
print("测试实际的PerformanceService._collect_disk_metrics方法")
print("="*80)

try:
    from core.services.performance_service import PerformanceService

    print("\n创建PerformanceService实例...")
    service = PerformanceService()

    print("\n调用_collect_disk_metrics()...")
    metrics = service._collect_disk_metrics()

    print("\n✅ 成功!")
    print(f"结果: {metrics}")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    print(f"类型: {type(e).__name__}")
    traceback.print_exc()

print("\n" + "="*80)
print("调试完成")
print("="*80)
