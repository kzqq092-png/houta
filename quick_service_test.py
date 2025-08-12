#!/usr/bin/env python3
"""快速服务注册测试"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("开始测试服务注册...")

try:
    # 1. 测试服务引导
    print("1. 测试服务引导...")
    from core.services.service_bootstrap import bootstrap_services
    result = bootstrap_services()
    print(f"   结果: {'成功' if result else '失败'}")

    # 2. 测试UnifiedDataManager获取
    print("2. 测试UnifiedDataManager...")
    from core.services.unified_data_manager import get_unified_data_manager
    manager = get_unified_data_manager()
    if manager:
        print(f"   ✅ 获取成功: {type(manager).__name__}")
    else:
        print("   ❌ 获取失败")

    # 3. 测试容器解析
    print("3. 测试容器解析...")
    from core.containers import get_service_container
    from core.services.unified_data_manager import UnifiedDataManager

    container = get_service_container()

    try:
        by_type = container.resolve(UnifiedDataManager)
        print(f"   类型解析: ✅ 成功")
    except Exception as e:
        print(f"   类型解析: ❌ 失败 - {e}")

    try:
        by_name = container.resolve_by_name('unified_data_manager')
        print(f"   名称解析: ✅ 成功")
    except Exception as e:
        print(f"   名称解析: ❌ 失败 - {e}")

    print("测试完成！")

except Exception as e:
    print(f"测试异常: {e}")
    import traceback
    traceback.print_exc()
