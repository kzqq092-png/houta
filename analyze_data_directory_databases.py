"""
分析 data/ 目录下的所有数据库文件

检查：
1. 文件类型（SQLite还是其他）
2. 文件大小和修改时间
3. 数据库内容（表结构）
4. 业务用途
5. 文件命名规范
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

print("="*80)
print(" data/ 目录数据库文件分析")
print("="*80)
print()

data_dir = Path("data")

# 获取所有数据库文件
db_files = []
for pattern in ["*.db", "*.sqlite"]:
    db_files.extend(data_dir.glob(pattern))

print(f"找到 {len(db_files)} 个数据库文件")
print()

# 分析每个文件
for db_file in sorted(db_files):
    print(f"[{db_file.name}]")
    print("-"*80)

    # 文件信息
    stat = db_file.stat()
    size_kb = stat.st_size / 1024
    modified = datetime.fromtimestamp(stat.st_mtime)

    print(f"📁 文件路径: {db_file}")
    print(f"📏 文件大小: {size_kb:.2f} KB ({stat.st_size} bytes)")
    print(f"📅 修改时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

    # 检测文件类型
    try:
        with open(db_file, 'rb') as f:
            header = f.read(16)
            if header.startswith(b'SQLite format 3'):
                file_type = "SQLite 3"
                is_sqlite = True
            else:
                file_type = f"未知格式 (头16字节: {header.hex()[:32]}...)"
                is_sqlite = False
    except Exception as e:
        file_type = f"无法读取: {e}"
        is_sqlite = False

    print(f"🔍 文件类型: {file_type}")

    # 如果是SQLite，分析内容
    if is_sqlite and size_kb > 0:
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            if tables:
                print(f"📊 表数量: {len(tables)}")
                print(f"📋 表列表:")

                total_records = 0
                for (table_name,) in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        total_records += count

                        # 获取表结构
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        col_count = len(columns)

                        status = "✅" if count > 0 else "⚠️ "
                        print(f"   {status} {table_name}: {count:,} 条记录, {col_count} 列")

                        # 显示前几列的名称
                        if col_count > 0:
                            col_names = [col[1] for col in columns[:5]]
                            if col_count > 5:
                                col_names_str = ", ".join(col_names) + "..."
                            else:
                                col_names_str = ", ".join(col_names)
                            print(f"       列: {col_names_str}")

                    except Exception as e:
                        print(f"   ❌ {table_name}: 查询失败 - {e}")

                print(f"💾 总记录数: {total_records:,}")

            else:
                print(f"⚠️  数据库为空（无表）")

            conn.close()

        except Exception as e:
            print(f"❌ 无法打开数据库: {e}")

    # 推测业务用途（根据文件名）
    print(f"💡 推测用途:", end=" ")
    name_lower = db_file.stem.lower()

    purpose_map = {
        "strategy": "策略管理",
        "task_status": "任务状态追踪",
        "enhanced_risk_monitor": "风险监控",
        "factorweave": "系统核心配置",
        "tdx_servers": "通达信服务器配置",
        "unified_quality_monitor": "数据质量监控",
    }

    purpose = purpose_map.get(name_lower, "未知用途")
    print(purpose)

    # 文件命名建议
    correct_ext = ".sqlite" if is_sqlite else ".db"
    current_ext = db_file.suffix

    if is_sqlite and current_ext != ".sqlite":
        print(f"📝 建议重命名: {db_file.stem}{correct_ext} (当前: {current_ext})")
    elif not is_sqlite and current_ext == ".sqlite":
        print(f"⚠️  文件扩展名与类型不符")

    print()

# 总结
print("="*80)
print(" 总结与建议")
print("="*80)
print()

print("[1] 文件统计")
print("-"*80)
print()

total_size = sum(f.stat().st_size for f in db_files)
sqlite_files = []
other_files = []

for db_file in db_files:
    try:
        with open(db_file, 'rb') as f:
            if f.read(16).startswith(b'SQLite format 3'):
                sqlite_files.append(db_file)
            else:
                other_files.append(db_file)
    except:
        other_files.append(db_file)

print(f"总文件数: {len(db_files)}")
print(f"SQLite文件: {len(sqlite_files)}")
print(f"其他类型: {len(other_files)}")
print(f"总大小: {total_size / 1024:.2f} KB ({total_size / (1024*1024):.2f} MB)")
print()

print("[2] 命名规范建议")
print("-"*80)
print()

print("应该按实际数据库类型命名：")
print("  - SQLite 数据库 → .sqlite 后缀")
print("  - DuckDB 数据库 → .duckdb 后缀")
print("  - 其他数据库 → .db 后缀（通用）")
print()

rename_suggestions = []
for db_file in sqlite_files:
    if db_file.suffix == ".db":
        old_name = db_file.name
        new_name = f"{db_file.stem}.sqlite"
        rename_suggestions.append((old_name, new_name))

if rename_suggestions:
    print(f"需要重命名的文件（{len(rename_suggestions)}个）：")
    for old, new in rename_suggestions:
        print(f"  {old} → {new}")
else:
    print("✅ 所有文件命名规范正确")

print()

print("[3] 业务用途分析")
print("-"*80)
print()

print("data/ 目录应该存储：")
print("  ✅ 系统配置数据库（如 factorweave.sqlite）")
print("  ✅ 策略定义数据库（如 strategy.sqlite）")
print("  ✅ 任务状态数据库（如 task_status.sqlite）")
print("  ✅ 系统监控数据库（如 *_monitor.sqlite）")
print()

print("不应该存储：")
print("  ❌ 资产数据（K线、财务等）→ 应在 db/databases/")
print("  ❌ 分析数据（策略执行、指标计算等）→ 应在 db/factorweave_analytics.duckdb")
print()

print("[4] 与 db/ 目录的区别")
print("-"*80)
print()

print("data/：")
print("  - SQLite 数据库（轻量配置和状态）")
print("  - 系统级配置")
print("  - 任务和监控状态")
print()

print("db/：")
print("  - DuckDB 数据库（大数据分析）")
print("  - 资产数据（K线、财务等）")
print("  - 分析数据（策略执行、指标计算等）")
print()
