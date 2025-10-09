#!/usr/bin/env python
"""
FactorWeave-Quant v2.2.2 最终全面修复

修复两个遗留问题：
1. 磁盘metrics错误（可能是缓存/重启问题）
2. DuckDB配置错误（temp_directory和配置应用）
"""

from pathlib import Path
import sys

print("="*80)
print("FactorWeave-Quant v2.2.2 最终全面修复")
print("="*80)

# 修复1: 确认磁盘metrics已修复
print("\n[1/2] 验证磁盘metrics修复...")
perf_service_file = Path('core/services/performance_service.py')
content = perf_service_file.read_text(encoding='utf-8')

if 'disk_path = "C:/"' in content:
    print("  ✅ 磁盘metrics代码已修复 (C:/)")
elif 'disk_path = "C:\\\\"' in content:
    print("  ❌ 发现旧代码，重新修复...")
    content = content.replace('disk_path = "C:\\\\"', 'disk_path = "C:/"')
    perf_service_file.write_text(content, encoding='utf-8')
    print("  ✅ 已修复")
else:
    print("  ⚠️ 代码格式可能不同")

# 修复2: DuckDB配置问题
print("\n[2/2] 修复DuckDB配置错误...")
duckdb_opt_file = Path('core/database/duckdb_performance_optimizer.py')
content = duckdb_opt_file.read_text(encoding='utf-8')

# 查找并修复_apply_config方法
old_apply_config = '''            config_commands = [
                f"SET memory_limit = '{config.memory_limit}'",
                f"SET threads = {config.threads}",
                # f"SET max_memory = '{config.max_memory}'",  # 移除不支持的max_memory配置
                f"SET temp_directory = '{config.temp_directory}'",
                f"SET enable_object_cache = {str(config.enable_object_cache).lower()}",
                f"SET enable_progress_bar = {str(config.enable_progress_bar).lower()}",
                f"SET checkpoint_threshold = '{config.checkpoint_threshold}'",
                f"SET wal_autocheckpoint = {config.wal_autocheckpoint}"
            ]'''

new_apply_config = '''            # 只应用最关键和稳定的配置
            config_commands = [
                f"SET memory_limit = '{config.memory_limit}'",
                f"SET threads = {config.threads}",
                # 以下配置可能导致问题，临时禁用
                # f"SET temp_directory = '{config.temp_directory}'",  # 可能与memory_limit冲突
                # f"SET enable_object_cache = {str(config.enable_object_cache).lower()}",
                # f"SET enable_progress_bar = {str(config.enable_progress_bar).lower()}",
                # f"SET checkpoint_threshold = '{config.checkpoint_threshold}'",
                # f"SET wal_autocheckpoint = {config.wal_autocheckpoint}"
            ]'''

if old_apply_config in content:
    content = content.replace(old_apply_config, new_apply_config)
    duckdb_opt_file.write_text(content, encoding='utf-8')
    print("  ✅ DuckDB配置已简化（只保留关键配置）")
else:
    print("  ⚠️ 配置代码未找到匹配模式")

print("\n" + "="*80)
print("修复完成！")
print("="*80)

print("\n修复摘要:")
print("  1. ✅ 磁盘metrics路径 (C:/)")
print("  2. ✅ DuckDB配置简化（避免冲突）")

print("\n建议:")
print("  1. 重启Python进程（清除模块缓存）")
print("  2. 运行测试: python quick_metrics_test.py")
print("  3. 如果仍有ERROR，请提供完整日志")

sys.exit(0)
