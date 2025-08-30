#!/usr/bin/env python3
"""
DuckDB数据库检查工具

用于检查HIkyuu-UI系统中的DuckDB数据库：
- 查看数据库文件位置
- 检查表结构
- 统计数据量
- 验证数据完整性

作者: FactorWeave-Quant团队
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import duckdb
    import pandas as pd
except ImportError as e:
    print(f"缺少必要的库: {e}")
    print("请安装: pip install duckdb pandas")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DuckDBChecker:
    """DuckDB数据库检查器"""

    def __init__(self):
        """初始化检查器"""
        self.project_root = Path(__file__).parent
        self.db_paths = [
            self.project_root / "db" / "kline_stock.duckdb",
            self.project_root / "db" / "import_data.db",
            self.project_root / "db" / "factorweave_system.db"
        ]

    def check_database_files(self):
        """检查数据库文件是否存在"""
        print("🔍 检查数据库文件...")
        print("=" * 60)

        for db_path in self.db_paths:
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                modified_time = datetime.fromtimestamp(db_path.stat().st_mtime)
                print(f"✅ {db_path.name}")
                print(f"   📍 路径: {db_path}")
                print(f"   📊 大小: {size_mb:.2f} MB")
                print(f"   🕒 修改时间: {modified_time}")
                print()
            else:
                print(f"❌ {db_path.name} - 文件不存在")
                print(f"   📍 预期路径: {db_path}")
                print()

    def check_table_structure(self, db_path: Path):
        """检查数据库表结构"""
        if not db_path.exists():
            print(f"❌ 数据库文件不存在: {db_path}")
            return

        print(f"🔍 检查数据库表结构: {db_path.name}")
        print("=" * 60)

        try:
            with duckdb.connect(str(db_path)) as conn:
                # 获取所有表
                tables_query = """
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'main'
                ORDER BY table_name
                """
                tables_df = conn.execute(tables_query).fetchdf()

                if tables_df.empty:
                    print("📋 数据库中没有表")
                    return

                print(f"📋 发现 {len(tables_df)} 个表:")
                print()

                for _, row in tables_df.iterrows():
                    table_name = row['table_name']
                    table_type = row['table_type']

                    print(f"📊 表名: {table_name} ({table_type})")

                    # 获取表结构
                    try:
                        columns_query = f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' AND table_schema = 'main'
                        ORDER BY ordinal_position
                        """
                        columns_df = conn.execute(columns_query).fetchdf()

                        if not columns_df.empty:
                            print("   列结构:")
                            for _, col_row in columns_df.iterrows():
                                nullable = "NULL" if col_row['is_nullable'] == 'YES' else "NOT NULL"
                                print(f"     - {col_row['column_name']}: {col_row['data_type']} ({nullable})")

                        # 获取数据量
                        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                        count_result = conn.execute(count_query).fetchone()
                        record_count = count_result[0] if count_result else 0
                        print(f"   📊 记录数: {record_count:,}")

                        # 如果是K线数据表，显示股票数量和日期范围
                        if 'kline' in table_name.lower():
                            try:
                                stats_query = f"""
                                SELECT 
                                    COUNT(DISTINCT symbol) as stock_count,
                                    MIN(datetime) as min_date,
                                    MAX(datetime) as max_date
                                FROM {table_name}
                                WHERE datetime IS NOT NULL
                                """
                                stats_result = conn.execute(stats_query).fetchone()
                                if stats_result:
                                    stock_count, min_date, max_date = stats_result
                                    print(f"   📈 股票数量: {stock_count}")
                                    print(f"   📅 日期范围: {min_date} 到 {max_date}")
                            except Exception as e:
                                print(f"   ⚠️ 无法获取统计信息: {e}")

                    except Exception as e:
                        print(f"   ❌ 获取表结构失败: {e}")

                    print()

        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")

    def check_kline_data_samples(self, db_path: Path):
        """检查K线数据样本"""
        if not db_path.exists():
            return

        print(f"📊 K线数据样本检查: {db_path.name}")
        print("=" * 60)

        try:
            with duckdb.connect(str(db_path)) as conn:
                # 查找K线数据表
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main' AND table_name LIKE '%kline%'
                """
                kline_tables = conn.execute(tables_query).fetchdf()

                if kline_tables.empty:
                    print("📋 没有找到K线数据表")
                    return

                for _, row in kline_tables.iterrows():
                    table_name = row['table_name']
                    print(f"📊 表: {table_name}")

                    try:
                        # 获取样本数据
                        sample_query = f"""
                        SELECT symbol, datetime, open, high, low, close, volume
                        FROM {table_name}
                        ORDER BY datetime DESC
                        LIMIT 5
                        """
                        sample_df = conn.execute(sample_query).fetchdf()

                        if not sample_df.empty:
                            print("   最新5条记录:")
                            for _, sample_row in sample_df.iterrows():
                                print(f"     {sample_row['symbol']} | {sample_row['datetime']} | "
                                      f"开:{sample_row['open']} 高:{sample_row['high']} "
                                      f"低:{sample_row['low']} 收:{sample_row['close']} "
                                      f"量:{sample_row['volume']}")
                        else:
                            print("   📋 表中没有数据")

                    except Exception as e:
                        print(f"   ❌ 获取样本数据失败: {e}")

                    print()

        except Exception as e:
            print(f"❌ 检查K线数据失败: {e}")

    def run_full_check(self):
        """运行完整检查"""
        print("🚀 HIkyuu-UI DuckDB数据库检查工具")
        print("=" * 60)
        print(f"📍 项目根目录: {self.project_root}")
        print(f"🕒 检查时间: {datetime.now()}")
        print()

        # 1. 检查数据库文件
        self.check_database_files()

        # 2. 检查主数据库表结构
        main_db = self.project_root / "db" / "kline_stock.duckdb"
        if main_db.exists():
            self.check_table_structure(main_db)
            self.check_kline_data_samples(main_db)

        # 3. 检查导入数据库
        import_db = self.project_root / "db" / "import_data.db"
        if import_db.exists():
            self.check_table_structure(import_db)
            self.check_kline_data_samples(import_db)

        print("✅ 数据库检查完成!")


def main():
    """主函数"""
    checker = DuckDBChecker()
    checker.run_full_check()


if __name__ == "__main__":
    main()
