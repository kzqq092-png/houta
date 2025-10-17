"""
更新代码中的数据库路径配置

基于深度分析，修复3个关键问题：
1. 更新 AssetSeparatedDatabaseManager 的 base_path
2. 删除 DatabaseService 中未使用的 main_duckdb 配置
3. 修复硬编码 "db/kline_stock.duckdb" 的地方
"""

import os
import re
from pathlib import Path

print("="*80)
print(" 代码路径更新工具")
print("="*80)
print()

# 修改计划
modifications = []

# 1. 更新 AssetSeparatedDatabaseManager 的 base_path
modifications.append({
    "file": "core/asset_database_manager.py",
    "description": "更新 base_path 配置",
    "changes": [
        {
            "pattern": r'base_path:\s*str\s*=\s*["\']data/databases["\']',
            "replacement": 'base_path: str = "db/databases"',
            "description": "data/databases → db/databases"
        }
    ]
})

# 2. 删除 DatabaseService 中的 main_duckdb 配置
modifications.append({
    "file": "core/services/database_service.py",
    "description": "删除未使用的 main_duckdb 配置",
    "changes": [
        {
            "pattern": r'"main_duckdb":\s*DatabaseConfig\([^)]+\),\s*\n',
            "replacement": "",
            "description": "删除 main_duckdb 配置项"
        },
        {
            "pattern": r'["\']data/main\.duckdb["\']',
            "replacement": '"db/factorweave_analytics.duckdb"',
            "description": "data/main.duckdb → db/factorweave_analytics.duckdb"
        },
        {
            "pattern": r'["\']data/analytics\.duckdb["\']',
            "replacement": '"db/factorweave_analytics.duckdb"',
            "description": "data/analytics.duckdb → db/factorweave_analytics.duckdb"
        }
    ]
})

# 3. 修复 unified_data_manager.py 中的硬编码
modifications.append({
    "file": "core/services/unified_data_manager.py",
    "description": "移除硬编码路径",
    "changes": [
        {
            "pattern": r'database_path\s*=\s*["\']db/kline_stock\.duckdb["\']',
            "replacement": 'database_path=self.asset_manager.get_database_path(asset_type)',
            "description": "使用 AssetSeparatedDatabaseManager"
        }
    ]
})

# 4. 修复 import_execution_engine.py 中的硬编码
modifications.append({
    "file": "core/importdata/import_execution_engine.py",
    "description": "移除硬编码路径",
    "changes": [
        {
            "pattern": r'db_path\s*=\s*["\']db/kline_stock\.duckdb["\']',
            "replacement": 'db_path = self.asset_manager.get_database_path(asset_type)',
            "description": "使用 AssetSeparatedDatabaseManager"
        }
    ]
})


def apply_changes(filepath, changes):
    """应用修改到文件"""
    path = Path(filepath)

    if not path.exists():
        print(f"   ⚠️  文件不存在: {filepath}")
        return False, 0

    try:
        # 读取文件
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        total_changes = 0

        # 应用每个修改
        for change in changes:
            matches = re.findall(change["pattern"], content, re.MULTILINE)
            if matches:
                content = re.sub(change["pattern"], change["replacement"], content, flags=re.MULTILINE)
                count = len(matches)
                total_changes += count
                print(f"      ✅ {change['description']} ({count}处)")

        # 如果有修改，写回文件
        if content != original_content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, total_changes
        else:
            return False, 0

    except Exception as e:
        print(f"   ❌ 处理文件失败: {e}")
        return False, 0


# 执行修改
print("[1] 应用代码修改")
print("-"*80)
print()

total_files_modified = 0
total_changes_made = 0

for mod in modifications:
    print(f"📝 {mod['file']}")
    print(f"   {mod['description']}")

    modified, changes = apply_changes(mod["file"], mod["changes"])

    if modified:
        total_files_modified += 1
        total_changes_made += changes
        print(f"   ✅ 修改成功")
    else:
        if changes == 0:
            print(f"   ⏭️  无需修改（已是最新）")
        else:
            print(f"   ❌ 修改失败")
    print()

print("="*80)
print(" 代码更新完成")
print("="*80)
print()
print(f"📊 统计：")
print(f"  ✅ 修改文件: {total_files_modified} 个")
print(f"  ✅ 修改次数: {total_changes_made} 处")
print()

if total_changes_made > 0:
    print("📋 主要修改：")
    print("  1. asset_database_manager.py:")
    print("     - base_path: 'data/databases' → 'db/databases'")
    print()
    print("  2. database_service.py:")
    print("     - 删除未使用的 main_duckdb 配置")
    print("     - 统一使用 db/factorweave_analytics.duckdb")
    print()
    print("  3. unified_data_manager.py:")
    print("     - 移除硬编码 'db/kline_stock.duckdb'")
    print("     - 使用 AssetSeparatedDatabaseManager")
    print()
    print("  4. import_execution_engine.py:")
    print("     - 移除硬编码 'db/kline_stock.duckdb'")
    print("     - 使用 AssetSeparatedDatabaseManager")
    print()
else:
    print("ℹ️  没有需要修改的内容（代码已是最新）")

print()
print("✅ 完成！现在可以启动应用验证功能。")
print()
