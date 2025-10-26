"""检查DuckDB数据库中的实际数据"""
import duckdb
from pathlib import Path

# 数据库路径
db_path = Path("db/databases/stock_a/stock_a_data.duckdb")

if not db_path.exists():
    print(f"[ERROR] Database file not exists: {db_path}")
    exit(1)

print(f"[OK] Database file exists: {db_path}")
print(f"   File size: {db_path.stat().st_size / (1024*1024):.2f} MB")
print()

# 连接数据库
conn = duckdb.connect(str(db_path), read_only=True)

# 1. 列出所有表
print("="*80)
print("1. 数据库中的所有表")
print("="*80)
tables = conn.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'main'
    ORDER BY table_name
""").fetchall()

if tables:
    for table in tables:
        print(f"  - {table[0]}")
else:
    print("  [ERROR] No tables found!")
print()

# 2. 检查是否有stock_basic表
print("="*80)
print("2. 检查stock_basic表")
print("="*80)
try:
    # 检查表结构
    columns = conn.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'stock_basic'
        ORDER BY ordinal_position
    """).fetchall()

    if columns:
        print("[OK] stock_basic table exists")
        print("\n表结构:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

        # 检查记录数
        count = conn.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0]
        print(f"\n总记录数: {count}")

        # 检查status字段的值分布
        if count > 0:
            status_dist = conn.execute("""
                SELECT status, COUNT(*) as cnt 
                FROM stock_basic 
                GROUP BY status 
                ORDER BY cnt DESC
            """).fetchall()

            print("\nstatus字段分布:")
            for status, cnt in status_dist:
                print(f"  - {status}: {cnt} 条")

            # 显示前5条记录
            print("\n前5条记录:")
            sample = conn.execute("""
                SELECT symbol, name, market, status 
                FROM stock_basic 
                LIMIT 5
            """).fetchall()

            for row in sample:
                print(f"  {row}")

            # 检查WHERE status = 'L'的结果
            l_count = conn.execute("""
                SELECT COUNT(*) 
                FROM stock_basic 
                WHERE status = 'L'
            """).fetchone()[0]

            print(f"\n满足 status = 'L' 的记录数: {l_count}")

    else:
        print("[ERROR] stock_basic table not exists")

except Exception as e:
    print(f"[ERROR] Error checking stock_basic: {e}")

print()

# 3. 检查其他可能的表
print("="*80)
print("3. 检查其他可能包含股票数据的表")
print("="*80)

possible_tables = [
    'stock_list', 'stocks', 'stock_info', 'stock_data',
    'historical_kline_data', 'kline_daily'
]

for table_name in possible_tables:
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"[OK] {table_name}: {count} records")
    except:
        pass

conn.close()

print()
print("="*80)
print("检查完成")
print("="*80)
