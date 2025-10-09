#!/usr/bin/env python
"""
批量更新所有Metrics类，添加字典接口支持

解决测试失败问题: "Metrics对象不可下标"
"""

from pathlib import Path
import re

print("="*80)
print("统一Metrics接口 - 批量更新")
print("="*80)

# 需要更新的服务文件
services_to_update = [
    ('core/services/database_service.py', 'DatabaseMetrics'),
    ('core/services/data_service.py', 'DataMetrics'),
    ('core/services/cache_service.py', 'CacheMetrics'),
    ('core/services/plugin_service.py', 'PluginMetrics'),
    ('core/services/network_service.py', 'NetworkMetrics'),
    ('core/services/performance_service.py', 'PerformanceMetrics'),
]

updated_count = 0
failed_count = 0

for file_path, metrics_class in services_to_update:
    print(f"\n处理: {file_path} ({metrics_class})")
    print("-" * 60)

    path = Path(file_path)
    if not path.exists():
        print(f"  ⚠️ 文件不存在，跳过")
        continue

    try:
        content = path.read_text(encoding='utf-8')
        original_content = content

        # 1. 添加导入（如果不存在）
        if 'from .metrics_base import add_dict_interface' not in content:
            # 找到@dataclass所在行
            if '@dataclass' in content:
                # 在文件开头的导入部分添加
                import_section_end = content.find('\n\n\nclass')
                if import_section_end == -1:
                    import_section_end = content.find('\n\nclass')

                if import_section_end != -1:
                    content = (
                        content[:import_section_end] +
                        '\nfrom .metrics_base import add_dict_interface' +
                        content[import_section_end:]
                    )
                    print(f"  ✓ 添加导入")

        # 2. 为Metrics类添加装饰器
        # 查找类定义
        pattern = rf'@dataclass\s+class {metrics_class}:'
        if re.search(pattern, content):
            # 检查是否已有装饰器
            decorator_pattern = rf'@add_dict_interface\s+@dataclass\s+class {metrics_class}:'
            if not re.search(decorator_pattern, content):
                # 添加装饰器
                content = re.sub(
                    pattern,
                    f'@add_dict_interface\n@dataclass\nclass {metrics_class}:',
                    content
                )
                print(f"  ✓ 添加@add_dict_interface装饰器")

        # 3. 保存文件
        if content != original_content:
            path.write_text(content, encoding='utf-8')
            print(f"  ✅ {file_path} 更新成功")
            updated_count += 1
        else:
            print(f"  ℹ️ 无需更新（可能已更新）")

    except Exception as e:
        print(f"  ❌ 更新失败: {e}")
        failed_count += 1

print("\n" + "="*80)
print("更新汇总")
print("="*80)
print(f"总文件数: {len(services_to_update)}")
print(f"✓ 成功更新: {updated_count}")
print(f"✗ 失败: {failed_count}")
print(f"ℹ️ 跳过: {len(services_to_update) - updated_count - failed_count}")
print("="*80)

if updated_count > 0:
    print("\n✅ Metrics接口统一完成！")
    print("\n建议:")
    print("1. 运行测试验证: python final_regression_test.py")
    print("2. 预期通过率提升到80%+")
else:
    print("\n⚠️ 没有文件需要更新")
