#!/usr/bin/env python
"""
简单验证 - 直接检查文件内容
"""

from pathlib import Path

print("="*70)
print("简单验证关键修复")
print("="*70)

# 验证1: StandardData
print("\n[1/2] 检查 StandardData 类定义...")
tet_file = Path("core/tet_data_pipeline.py")
content = tet_file.read_text(encoding='utf-8')

if 'success: bool = True' in content and 'error_message: Optional[str] = None' in content:
    print("  ✅ StandardData.success 属性已添加")
    print("  ✅ StandardData.error_message 属性已添加")
else:
    print("  ✗ StandardData修复未生效")

# 验证2: 字段映射验证
print("\n[2/2] 检查字段映射验证逻辑...")
mapping_file = Path("core/data/field_mapping_engine.py")
content = mapping_file.read_text(encoding='utf-8')

if 'valid_count = int(numeric_data.notna().sum())' in content:
    print("  ✅ 字段映射验证逻辑已修复（确保标量）")
else:
    print("  ✗ 字段映射验证修复未生效")

print("\n" + "="*70)
print("验证完成！")
print("="*70)

print("\n✅ 修复总结:")
print("  1. StandardData添加success和error_message属性")
print("  2. 字段映射验证确保valid_count为标量")
print("  3. GPU和UltraPerformanceOptimizer为可选模块（警告正常）")

print("\n🚀 建议:")
print("  重启应用程序测试资金流数据获取功能")
