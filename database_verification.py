#!/usr/bin/env python3
"""
数据库验证脚本
检查插件独立数据库的状态和内容
"""

import os
import sys
import duckdb
from pathlib import Path


def check_database_files():
    """检查数据库文件是否存在"""
    print("=== 检查数据库文件 ===")

    base_dir = Path("db/datasource_separated")
    if not base_dir.exists():
        print(f"❌ 数据库目录不存在: {base_dir}")
        return []

    print(f"✅ 数据库目录存在: {base_dir}")

    db_files = list(base_dir.glob("*.duckdb"))
    if not db_files:
        print("❌ 没有找到数据库文件")
        return []

    print(f"✅ 找到 {len(db_files)} 个数据库文件:")
    for db_file in db_files:
        size = db_file.stat().st_size
        print(f"  - {db_file.name}: {size:,} bytes")

    return db_files


def check_database_content(db_path):
    """检查数据库内容"""
    print(f"\n=== 检查数据库内容: {db_path.name} ===")

    try:
        conn = duckdb.connect(str(db_path))

        # 获取所有表
        tables_result = conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in tables_result]

        if not tables:
            print("❌ 数据库中没有表")
            return

        print(f"✅ 找到 {len(tables)} 个表:")

        for table in tables:
            try:
                # 获取表的行数
                count_result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = count_result[0] if count_result else 0

                print(f"  - {table}: {count:,} 条记录")

                # 如果有数据，显示几条样本
                if count > 0:
                    sample_result = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
                    columns_result = conn.execute(f"DESCRIBE {table}").fetchall()
                    columns = [row[0] for row in columns_result]

                    print(f"    字段: {', '.join(columns)}")
                    print("  样本数据:")
                    for i, row in enumerate(sample_result):
                        print(f"      第{i+1}行: {dict(zip(columns, row))}")

            except Exception as e:
                print(f"    ❌ 查询表 {table} 失败: {e}")

        conn.close()

    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")


def check_config_file():
    """检查配置文件"""
    print("\n=== 检查存储配置文件 ===")

    config_path = Path("db/datasource_separated/storage_configs.json")
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return

    print(f"✅ 配置文件存在: {config_path}")

    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print(f"✅ 配置了 {len(config)} 个数据源:")
        for plugin_id, config_data in config.items():
            db_path = config_data.get('database_path', 'Unknown')
            print(f"  - {plugin_id}: {db_path}")

    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")


def main():
    """主函数"""
    print("数据库验证脚本")
    print("="*50)

    # 检查配置文件
    check_config_file()

    # 检查数据库文件
    db_files = check_database_files()

    # 检查每个数据库的内容
    for db_file in db_files:
        check_database_content(db_file)

    print("\n=== 总结 ===")
    if db_files:
        print(f"✅ 发现 {len(db_files)} 个数据库文件")
        print("建议：")
        print("1. 如果数据库为空，说明数据导入失败")
        print("2. 如果数据库有数据，检查界面刷新机制")
        print("3. 可以尝试使用AKShare数据源作为备选")
    else:
        print("❌ 没有找到数据库文件")
        print("建议：")
        print("1. 检查数据导入是否正常执行")
        print("2. 检查数据源连接是否正常")
        print("3. 查看导入任务的错误日志")


if __name__ == "__main__":
    main()
