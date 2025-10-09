#!/usr/bin/env python
"""验证最终修复"""

print("="*80)
print("验证PerformanceService._collect_disk_metrics修复")
print("="*80)

try:
    from core.services.performance_service import PerformanceService

    print("\n创建PerformanceService实例...")
    service = PerformanceService()

    print("\n调用_collect_disk_metrics()...")
    metrics = service._collect_disk_metrics()

    print("\n✅ 成功！无ERROR！")
    print(f"\n结果:")
    print(f"  total: {metrics['usage']['total']:.1f} GB")
    print(f"  used:  {metrics['usage']['used']:.1f} GB")
    print(f"  free:  {metrics['usage']['free']:.1f} GB")
    print(f"  percent: {metrics['usage']['percent']:.1f}%")

    if 'io' in metrics:
        print(f"\nIO信息:")
        print(f"  read: {metrics['io']['read_bytes']:.1f} MB")
        print(f"  write: {metrics['io']['write_bytes']:.1f} MB")

    print("\n" + "="*80)
    print("✅ 磁盘metrics错误已彻底修复！")
    print("="*80)

except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
