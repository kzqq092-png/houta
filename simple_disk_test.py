#!/usr/bin/env python
"""简单测试不同路径格式"""

import psutil
import platform

print("="*60)
print("测试不同路径格式")
print("="*60)
print(f"系统: {platform.system()}")
print(f"psutil版本: {psutil.__version__}")

# 测试路径
tests = [
    ("C:/", "正斜杠"),
    ("C:\\\\", "双反斜杠"),
    (r"C:\\", "raw string"),
    ("C:", "仅盘符"),
]

for path, desc in tests:
    print(f"\n[{desc}] path = {repr(path)}")
    try:
        result = psutil.disk_usage(path)
        print(f"  OK - total: {result.total / (1024**3):.1f} GB")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")

print("\n" + "="*60)
