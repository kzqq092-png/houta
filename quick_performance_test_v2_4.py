#!/usr/bin/env python
"""
v2.4性能快速测试
"""

from loguru import logger
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


print("="*80)
print("v2.4性能快速测试")
print("="*80)

# 测试1: 启动时间
print("\n[测试1] 启动时间测试...")
start_time = time.time()

try:
    from core.events import get_event_bus
    from core.containers import get_service_container
    from core.services.smart_bootstrap import smart_bootstrap_services

    # 初始化
    event_bus = get_event_bus()
    container = get_service_container()

    # 启动服务
    logger.info("开始服务启动...")
    success = smart_bootstrap_services(container)

    elapsed = time.time() - start_time

    print(f"\n✅ 启动完成")
    print(f"  耗时: {elapsed:.2f}秒")
    print(f"  成功: {'是' if success else '否'}")

    # 对比v2.3基准
    v23_baseline = 16.8
    improvement = ((v23_baseline - elapsed) / v23_baseline) * 100

    print(f"\n📊 性能对比:")
    print(f"  v2.3基准: {v23_baseline}秒")
    print(f"  v2.4实测: {elapsed:.2f}秒")
    print(f"  改进幅度: {improvement:+.1f}%")

    if elapsed <= 8.0:
        print(f"  ✅ 达到目标（≤8秒）")
    elif elapsed <= 10.0:
        print(f"  ⚠️  接近目标（8-10秒）")
    else:
        print(f"  ❌ 未达标（>{elapsed:.1f}秒）")

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("v2.4快速测试完成")
print("="*80)
