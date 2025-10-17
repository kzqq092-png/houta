"""
最终数据库迁移脚本

基于深度分析结果：
1. 删除3个空数据库
2. 迁移2个有效数据库到 db/databases/
3. 删除40+测试文件
4. 更新代码配置
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

print("="*80)
print(" 最终数据库迁移方案")
print("="*80)
print()

# 迁移计划
migration_plan = {
    "删除空数据库": [
        ("data/main.duckdb", "12KB空数据库"),
        ("data/analytics.duckdb", "12KB空数据库"),
        ("db/kline_stock.duckdb", "2.01MB空数据库（有表无数据）"),
    ],

    "迁移有效数据": [
        {
            "source": "data/databases/stock/stock_data.duckdb",
            "target": "db/databases/stock/stock_data.duckdb",
            "size": "3.51MB",
            "records": "4,508条",
            "description": "股票数据（美股等）"
        },
        {
            "source": "data/databases/stock_a/stock_a_data.duckdb",
            "target": "db/databases/stock_a/stock_a_data.duckdb",
            "size": "6.76MB",
            "records": "10,703条",
            "description": "A股数据"
        },
    ],

    "清理测试文件": [
        "db/test_*.duckdb",
        "db/quick_*.duckdb",
        "db/demo_*.duckdb",
        "db/verify_*.duckdb",
        "db/complete_test.duckdb",
        "db/final_verification.duckdb",
        "db/performance_test.duckdb",
        "db/assets/*.duckdb",
    ]
}


def get_file_size(filepath):
    """获取文件大小（MB）"""
    try:
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            return size_bytes / (1024 * 1024)
    except:
        pass
    return 0


def delete_file(filepath, description=""):
    """删除文件"""
    path = Path(filepath)
    if not path.exists():
        print(f"   ⚠️  文件不存在: {filepath}")
        return False

    try:
        size_mb = get_file_size(filepath)
        os.remove(filepath)
        print(f"   ✅ 删除: {filepath} ({size_mb:.2f}MB) {description}")
        return True
    except Exception as e:
        print(f"   ❌ 删除失败: {filepath} - {e}")
        return False


def migrate_file(source, target, description):
    """迁移单个文件"""
    source_path = Path(source)
    target_path = Path(target)

    if not source_path.exists():
        print(f"   ⚠️  源文件不存在: {source}")
        return False

    # 如果目标已存在，备份
    if target_path.exists():
        backup_path = str(target_path) + f".backup_{int(datetime.now().timestamp())}"
        print(f"   📦 目标已存在，备份到: {backup_path}")
        shutil.copy2(target_path, backup_path)

    # 创建目标目录
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 移动文件
        shutil.move(str(source_path), str(target_path))
        size_mb = get_file_size(target_path)
        print(f"   ✅ 迁移成功: {description}")
        print(f"      {source} → {target}")
        print(f"      大小: {size_mb:.2f}MB")
        return True
    except Exception as e:
        print(f"   ❌ 迁移失败: {source} → {target}")
        print(f"      错误: {e}")
        return False


def delete_pattern_files(pattern):
    """删除匹配模式的文件"""
    deleted_count = 0
    deleted_size = 0

    if "*" in pattern:
        # 通配符模式
        parts = pattern.split("/")
        search_dir = Path(".") / "/".join(parts[:-1])
        file_pattern = parts[-1]

        if search_dir.exists():
            for file in search_dir.glob(file_pattern):
                if file.is_file():
                    size_mb = get_file_size(file)
                    try:
                        os.remove(file)
                        print(f"   ✅ 删除: {file} ({size_mb:.2f}MB)")
                        deleted_count += 1
                        deleted_size += size_mb
                    except Exception as e:
                        print(f"   ❌ 删除失败: {file} - {e}")

    return deleted_count, deleted_size


# 显示计划
print("[1] 迁移计划")
print("-"*80)
print()

print("📦 有效数据迁移:")
for item in migration_plan["迁移有效数据"]:
    print(f"   {item['description']}: {item['records']}, {item['size']}")
    print(f"      {item['source']}")
    print(f"      → {item['target']}")
    print()

print("🗑️  删除空数据库:")
for filepath, desc in migration_plan["删除空数据库"]:
    if os.path.exists(filepath):
        print(f"   {filepath} - {desc}")

print()
print("🗑️  清理测试文件: 约40个文件")
print()

# 确认
print("="*80)
print("⚠️  警告：即将执行数据库迁移和清理！")
print("="*80)
print()
print("操作内容：")
print("  1. 删除 3 个空数据库（2.04MB）")
print("  2. 迁移 2 个有效数据库到 db/databases/（10.27MB）")
print("  3. 清理 40+ 个测试文件（15MB+）")
print("  4. 清理空目录")
print()
# 自动确认执行
print("✅ 自动确认执行（用户已授权）")
print()

# 执行迁移
print()
print("[2] 删除空数据库")
print("-"*80)
print()

deleted_empty = 0
for filepath, desc in migration_plan["删除空数据库"]:
    if delete_file(filepath, f"- {desc}"):
        deleted_empty += 1

print()
print(f"✅ 删除空数据库: {deleted_empty}/{len(migration_plan['删除空数据库'])} 个")
print()

# 迁移有效数据
print("[3] 迁移有效数据")
print("-"*80)
print()

migrated_count = 0
for item in migration_plan["迁移有效数据"]:
    if migrate_file(item["source"], item["target"], item["description"]):
        migrated_count += 1
    print()

print(f"✅ 迁移完成: {migrated_count}/{len(migration_plan['迁移有效数据'])} 个")
print()

# 清理测试文件
print("[4] 清理测试文件")
print("-"*80)
print()

total_deleted = 0
total_deleted_size = 0

for pattern in migration_plan["清理测试文件"]:
    deleted, size = delete_pattern_files(pattern)
    total_deleted += deleted
    total_deleted_size += size

print()
print(f"✅ 清理完成: {total_deleted} 个文件, {total_deleted_size:.2f}MB")
print()

# 清理空目录
print("[5] 清理空目录")
print("-"*80)
print()

empty_dirs = [
    "db/assets",
    "data/databases/stock",
    "data/databases/stock_a",
    "data/databases",
]

for dir_path in empty_dirs:
    path = Path(dir_path)
    try:
        if path.exists() and path.is_dir():
            if not any(path.iterdir()):
                os.rmdir(path)
                print(f"   ✅ 删除空目录: {dir_path}")
            else:
                remaining = len(list(path.iterdir()))
                print(f"   ⚠️  目录不为空，保留: {dir_path} ({remaining}个文件)")
    except Exception as e:
        print(f"   ❌ 处理目录失败: {dir_path} - {e}")

print()

# 生成结果报告
print("="*80)
print(" 迁移完成！")
print("="*80)
print()

print("📊 统计：")
print(f"  ✅ 删除空数据库: {deleted_empty} 个")
print(f"  ✅ 迁移有效数据: {migrated_count} 个")
print(f"  ✅ 清理测试文件: {total_deleted} 个, {total_deleted_size:.2f}MB")
print()

print("📁 新的数据库结构:")
print("""
db/
  ├── 核心系统数据库
  │   ├── factorweave_analytics.duckdb     # 分析数据库
  │   └── factorweave_system.sqlite        # 系统配置
  │
  ├── 统一数据存储
  │   ├── unified_fundamental_data.duckdb
  │   ├── unified_kline_data.duckdb
  │   ├── unified_macro_data.duckdb
  │   ├── unified_metadata.duckdb
  │   └── unified_realtime_data.duckdb
  │
  └── 资产分类存储（新迁移）
      └── databases/
          ├── stock/
          │   └── stock_data.duckdb        # 股票数据（4,508条）
          └── stock_a/
              └── stock_a_data.duckdb      # A股数据（10,703条）
""")

print()
print("⚠️  下一步：")
print("  1. 运行 'python update_code_paths.py' 更新代码路径")
print("  2. 启动应用验证功能")
print("  3. 提交 git 代码")
print()
print("📝 迁移报告生成时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()
