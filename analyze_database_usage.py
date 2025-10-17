"""
深度分析数据库文件的实际使用情况
"""

import re
import subprocess
from datetime import datetime
import sqlite3
import duckdb
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


print("="*80)
print(" 数据库使用情况深度分析")
print("="*80)
print()


def analyze_duckdb(db_path, description):
    """分析DuckDB数据库"""
    print(f"\n[{description}]")
    print(f"路径: {db_path}")
    print("-"*80)

    path = Path(db_path)

    if not path.exists():
        print("❌ 文件不存在")
        return

    size_mb = path.stat().st_size / (1024 * 1024)
    modified = datetime.fromtimestamp(path.stat().st_mtime)

    print(f"大小: {size_mb:.2f}MB")
    print(f"修改时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        conn = duckdb.connect(str(db_path), read_only=True)

        # 获取所有表
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()

        if not tables:
            print("⚠️  数据库为空（无表）")
            conn.close()
            return

        print(f"表数量: {len(tables)}")
        print()

        # 分析每个表
        for (table_name,) in tables:
            try:
                # 获取记录数
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                record_count = count_result[0] if count_result else 0

                # 获取列信息
                columns = conn.execute(f"DESCRIBE {table_name}").fetchall()
                col_count = len(columns)

                # 获取样本数据（如果有）
                sample = None
                if record_count > 0:
                    sample_result = conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchone()
                    sample = sample_result

                status = "✅" if record_count > 0 else "⚠️ "
                print(f"  {status} {table_name}")
                print(f"      - 记录数: {record_count:,}")
                print(f"      - 列数: {col_count}")

                if record_count > 0 and sample:
                    print(f"      - 样本: {str(sample)[:100]}...")

                    # 获取数据源信息（如果有data_source列）
                    col_names = [col[0] for col in columns]
                    if 'data_source' in col_names:
                        sources = conn.execute(f"SELECT DISTINCT data_source FROM {table_name}").fetchall()
                        if sources:
                            print(f"      - 数据源: {', '.join([s[0] for s in sources])}")

                    # 获取时间范围（如果有datetime列）
                    if 'datetime' in col_names:
                        time_range = conn.execute(f"SELECT MIN(datetime), MAX(datetime) FROM {table_name}").fetchone()
                        if time_range and time_range[0]:
                            print(f"      - 时间范围: {time_range[0]} ~ {time_range[1]}")

                print()

            except Exception as e:
                print(f"  ❌ {table_name}: 分析失败 - {e}")
                print()

        conn.close()

    except Exception as e:
        print(f"❌ 无法打开数据库: {e}")


# 分析所有数据库
databases = [
    ("data/main.duckdb", "data/main.duckdb - 主数据库"),
    ("data/analytics.duckdb", "data/analytics.duckdb - 旧分析库"),
    ("data/databases/stock/stock_data.duckdb", "stock/stock_data.duckdb - 股票数据"),
    ("data/databases/stock_a/stock_a_data.duckdb", "stock_a/stock_a_data.duckdb - A股数据"),
    ("db/factorweave_analytics.duckdb", "db/factorweave_analytics.duckdb - 当前分析库"),
    ("db/kline_stock.duckdb", "db/kline_stock.duckdb - K线数据"),
]

for db_path, description in databases:
    analyze_duckdb(db_path, description)

print()
print("="*80)
print(" 关键发现")
print("="*80)
print()

# 检查代码引用
print("[代码引用分析]")
print("-"*80)
print()


def count_references(pattern, description):
    """统计代码中的引用次数"""
    try:
        result = subprocess.run(
            ['grep', '-r', '-c', pattern, 'core/'],
            capture_output=True,
            text=True,
            shell=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            total = sum(int(line.split(':')[1]) for line in lines if ':' in line and line.split(':')[1].isdigit())
            print(f"{description}: {total} 处引用")
        else:
            print(f"{description}: 0 处引用")
    except Exception as e:
        print(f"{description}: 检查失败 - {e}")


count_references("data/main.duckdb", "data/main.duckdb")
count_references("main_duckdb", "main_duckdb配置")
count_references("stock_data.duckdb", "stock_data.duckdb")
count_references("stock_a_data.duckdb", "stock_a_data.duckdb")

print()
