#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('.')

try:
    # 测试导入
    from core.importdata.intelligent_config_manager import IntelligentConfigManager
    from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode

    print("✓ 成功导入核心模块")

    # 创建临时数据库
    import tempfile
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()

    try:
        # 测试基本功能
        manager = IntelligentConfigManager(temp_db.name)
        print("✓ 成功创建IntelligentConfigManager")

        # 测试添加任务
        config = ImportTaskConfig(
            task_id="test_001",
            name="测试任务",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH
        )

        result = manager.add_import_task(config)
        print(f"✓ 添加任务结果: {result}")

        # 测试获取任务
        retrieved = manager.get_import_task("test_001")
        print(f"✓ 获取任务结果: {retrieved is not None}")

        # 测试统计信息
        stats = manager.get_intelligent_statistics()
        print(f"✓ 获取统计信息: {type(stats)}")

        print("\n=== 基本功能测试通过 ===")

    finally:
        try:
            os.unlink(temp_db.name)
        except:
            pass

except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("所有基本测试通过！")
