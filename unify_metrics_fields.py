#!/usr/bin/env python
"""
统一所有Metrics类的基础字段

确保所有Metrics类都有error_count等基础字段，解决测试中"字段不存在"的问题。
"""

from pathlib import Path
import re

print("="*80)
print("统一Metrics类基础字段")
print("="*80)

# 基础字段列表（所有Metrics类都应该有，与BaseService一致）
BASE_FIELDS = """    # 基础指标字段（与BaseService._metrics一致）
    initialization_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    operation_count: int = 0
"""

# 需要处理的服务和Metrics类
SERVICES = [
    ('core/services/database_service.py', 'DatabaseMetrics', 'total_queries'),
    ('core/services/cache_service.py', 'CacheMetrics', 'level'),
    ('core/services/data_service.py', 'DataMetrics', 'total_requests'),
    ('core/services/plugin_service.py', 'PluginMetrics', 'total_plugins'),
    ('core/services/network_service.py', 'NetworkMetrics', 'total_requests'),
]

updated = 0
failed = 0

for file_path, metrics_class, first_field in SERVICES:
    print(f"\n处理: {file_path} ({metrics_class})")
    print("-" * 60)

    path = Path(file_path)
    if not path.exists():
        print(f"  ⚠️ 文件不存在，跳过")
        continue

    try:
        content = path.read_text(encoding='utf-8')
        original_content = content

        # 查找Metrics类定义
        # 匹配模式: @add_dict_interface\n@dataclass\nclass MetricsName:\n    """..."""\n    first_field: ...
        pattern = rf'(@add_dict_interface\s+@dataclass\s+class {metrics_class}:\s+"""[^"]*"""\s+)({first_field}[^\n]+)'

        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            # 检查是否已经有error_count字段
            if 'error_count:' in content:
                # 查找error_count所在位置
                metrics_start = match.start()
                metrics_section = content[metrics_start:metrics_start+1000]

                if 'error_count:' in metrics_section:
                    print(f"  ℹ️ {metrics_class}已有error_count字段，跳过")
                    continue

            # 在第一个字段之前插入基础字段
            insert_pos = match.start(2)
            new_content = (
                content[:insert_pos] +
                BASE_FIELDS + "\n    " +
                content[insert_pos:]
            )

            # 检查是否需要添加Optional和datetime导入
            if 'Optional' not in new_content[:1000]:
                # 在typing导入中添加Optional
                new_content = new_content.replace(
                    'from typing import',
                    'from typing import Optional,'
                )

            if 'from datetime import datetime' not in new_content[:2000]:
                # 添加datetime导入
                import_section = new_content.find('from dataclasses import')
                if import_section != -1:
                    new_content = (
                        new_content[:import_section] +
                        'from datetime import datetime\n' +
                        new_content[import_section:]
                    )

            if 'field(default_factory' in BASE_FIELDS and 'from dataclasses import' in new_content:
                # 确保field已导入
                if ', field' not in new_content[:2000]:
                    new_content = new_content.replace(
                        'from dataclasses import dataclass',
                        'from dataclasses import dataclass, field'
                    )

            path.write_text(new_content, encoding='utf-8')
            print(f"  ✅ 已添加基础字段到{metrics_class}")
            updated += 1
        else:
            print(f"  ⚠️ 未找到{metrics_class}定义，可能已修改")

    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        failed += 1

print("\n" + "="*80)
print("统一完成")
print("="*80)
print(f"成功: {updated}")
print(f"失败: {failed}")
print(f"跳过: {len(SERVICES) - updated - failed}")

if updated > 0:
    print("\n✅ Metrics字段已统一！")
    print("\n建议:")
    print("1. 运行快速测试: python quick_metrics_test.py")
    print("2. 运行完整测试: python final_regression_test.py")
