#!/usr/bin/env python
"""测试shutil.disk_usage()作为替代方案"""

import shutil
import platform

print("="*60)
print("测试shutil.disk_usage()")
print("="*60)
print(f"系统: {platform.system()}")

tests = [
    "C:/",
    "C:\\\\",
    "C:",
]

for path in tests:
    print(f"\n[测试] path = {repr(path)}")
    try:
        usage = shutil.disk_usage(path)
        print(f"  OK!")
        print(f"    total: {usage.total / (1024**3):.1f} GB")
        print(f"    used:  {usage.used / (1024**3):.1f} GB")
        print(f"    free:  {usage.free / (1024**3):.1f} GB")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*60)
print("结论: shutil.disk_usage()是标准库，更可靠")
print("="*60)
