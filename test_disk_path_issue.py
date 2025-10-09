#!/usr/bin/env python
"""测试磁盘路径问题"""

import psutil
import platform

print("="*60)
print("测试磁盘路径问题")
print("="*60)

print(f"\n系统: {platform.system()}")

# 测试1: 原有的问题代码
print("\n[测试1] 原有代码: disk_path = \"C:\\\\\"")
try:
    disk_path = "C:\\"
    print(f"  disk_path = {repr(disk_path)}")
    print(f"  disk_path 长度 = {len(disk_path)}")
    disk_usage = psutil.disk_usage(disk_path)
    print(f"  ✅ 成功: total={disk_usage.total / (1024**3):.1f}GB")
except Exception as e:
    print(f"  ❌ 错误: {e}")
    print(f"  错误类型: {type(e).__name__}")

# 测试2: 使用raw string
print("\n[测试2] 使用raw string: disk_path = r\"C:\\\"")
try:
    disk_path = r"C:\\"
    print(f"  disk_path = {repr(disk_path)}")
    disk_usage = psutil.disk_usage(disk_path)
    print(f"  ✅ 成功: total={disk_usage.total / (1024**3):.1f}GB")
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试3: 使用正斜杠（推荐）
print("\n[测试3] 使用正斜杠: disk_path = \"C:/\"")
try:
    disk_path = "C:/"
    print(f"  disk_path = {repr(disk_path)}")
    disk_usage = psutil.disk_usage(disk_path)
    print(f"  ✅ 成功: total={disk_usage.total / (1024**3):.1f}GB")
except Exception as e:
    print(f"  ❌ 错误: {e}")

# 测试4: 只用盘符
print("\n[测试4] 只用盘符: disk_path = \"C:\"")
try:
    disk_path = "C:"
    print(f"  disk_path = {repr(disk_path)}")
    disk_usage = psutil.disk_usage(disk_path)
    print(f"  ✅ 成功: total={disk_usage.total / (1024**3):.1f}GB")
except Exception as e:
    print(f"  ❌ 错误: {e}")

print("\n" + "="*60)
print("结论: 使用 'C:/' 或 r'C:\\' 最安全")
print("="*60)
