#!/usr/bin/env python
"""快速测试Metrics接口"""

print("="*60)
print("快速Metrics接口测试")
print("="*60)

# 测试1: DatabaseMetrics
print("\n[1] 测试DatabaseMetrics...")
try:
    from core.services.database_service import DatabaseService
    db = DatabaseService()
    db.initialize()
    metrics = db.metrics
    print(f"  ✓ metrics类型: {type(metrics).__name__}")
    print(f"  ✓ metrics内容: {list(metrics.keys())[:5]}")  # 前5个键
    print(f"  ✓ 字典访问: metrics['total_connections'] = {metrics.get('total_connections', 'N/A')}")
except Exception as e:
    print(f"  ✗ 失败: {e}")

# 测试2: CacheMetrics
print("\n[2] 测试CacheMetrics...")
try:
    from core.services.cache_service import CacheService
    cache = CacheService()
    cache.initialize()
    metrics = cache.metrics
    print(f"  ✓ metrics类型: {type(metrics).__name__}")
    print(f"  ✓ metrics内容: {list(metrics.keys())[:5]}")
    print(f"  ✓ 字典访问: metrics['total_requests'] = {metrics.get('total_requests', 'N/A')}")
except Exception as e:
    print(f"  ✗ 失败: {e}")

# 测试3: PerformanceMetrics
print("\n[3] 测试PerformanceMetrics...")
try:
    from core.services.performance_service import PerformanceService
    perf = PerformanceService()
    perf.initialize()

    # 测试.metrics属性
    metrics = perf.metrics
    print(f"  ✓ metrics类型: {type(metrics).__name__}")
    print(f"  ✓ metrics内容: {list(metrics.keys())[:5]}")

    # 测试get_metrics方法是否存在
    if hasattr(perf, 'get_metrics'):
        print(f"  ℹ️ get_metrics方法存在")
    else:
        print(f"  ℹ️ get_metrics方法不存在（正常）")

except Exception as e:
    print(f"  ✗ 失败: {e}")

print("\n" + "="*60)
print("测试完成")
print("="*60)
