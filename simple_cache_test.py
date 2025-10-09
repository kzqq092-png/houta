#!/usr/bin/env python
"""简单的CacheService测试"""

import sys
sys.path.insert(0, '.')

print("="*60)
print("测试CacheService Metrics修复")
print("="*60)

try:
    print("\n[1] 导入CacheService...")
    from core.services.cache_service import CacheService
    print("  ✅ 导入成功")

    print("\n[2] 创建CacheService实例...")
    cache_service = CacheService()
    print("  ✅ 创建成功")

    print("\n[3] 初始化CacheService...")
    cache_service.initialize()
    print("  ✅ 初始化成功")

    print("\n[4] 获取metrics...")
    metrics = cache_service.metrics
    print(f"  ✅ metrics类型: {type(metrics).__name__}")
    print(f"  ✅ metrics内容: {list(metrics.keys())[:10]}")

    print("\n[5] 测试字典访问...")
    try:
        error_count = metrics['error_count']
        print(f"  ✅ error_count = {error_count}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        raise

    try:
        init_count = metrics['initialization_count']
        print(f"  ✅ initialization_count = {init_count}")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        raise

    print("\n" + "="*60)
    print("✅ 所有测试通过！CacheService已修复")
    print("="*60)

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
