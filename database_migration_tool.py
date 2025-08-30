#!/usr/bin/env python3
"""
HIkyuu-UI 数据库迁移工具

实现数据库架构重构：
- 从多个分散的数据库迁移到统一的双数据库架构
- 自动备份、迁移、验证和清理
- 更新代码中的数据库路径引用

作者: FactorWeave-Quant团队
"""

import os
import sys
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json

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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_migration.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigrationTool:
    """数据库迁移工具"""

    def __init__(self, dry_run: bool = False):
        """
        初始化迁移工具

        Args:
            dry_run: 是否为试运行模式（不实际执行迁移）
        """
        self.project_root = Path(__file__).parent
        self.db_dir = self.project_root / "db"
        self.backup_dir = self.project_root / "db_backup" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.dry_run = dry_run

        # 目标数据库路径
        self.target_system_db = self.db_dir / "hikyuu_system.sqlite"
        self.target_analytics_db = self.db_dir / "hikyuu_analytics.duckdb"

        # 迁移映射配置
        self.migration_map = self._load_migration_config()

    def _load_migration_config(self) -> Dict:
        """加载迁移配置"""
        return {
            # SQLite 数据库迁移到系统数据库
            "system_migrations": [
                {
                    "source": "factorweave_system.db",
                    "target": "hikyuu_system.sqlite",
                    "action": "migrate",
                    "description": "系统配置和元数据"
                },
                {
                    "source": "import_config.db",
                    "target": "hikyuu_system.sqlite",
                    "action": "merge",
                    "description": "导入配置数据"
                },
                {
                    "source": "strategies.db",
                    "target": "hikyuu_system.sqlite",
                    "action": "migrate",
                    "description": "策略定义数据"
                }
            ],

            # DuckDB 数据库迁移到分析数据库
            "analytics_migrations": [
                {
                    "source": "market_data.duckdb",
                    "target": "hikyuu_analytics.duckdb",
                    "action": "migrate",
                    "description": "市场数据"
                },
                {
                    "source": "performance_metrics.duckdb",
                    "target": "hikyuu_analytics.duckdb",
                    "action": "merge",
                    "description": "性能指标"
                },
                {
                    "source": "backtest_results.duckdb",
                    "target": "hikyuu_analytics.duckdb",
                    "action": "migrate",
                    "description": "回测结果"
                },
                {
                    "source": "analytics.duckdb",
                    "target": "hikyuu_analytics.duckdb",
                    "action": "migrate",
                    "description": "分析数据"
                },
                {
                    "source": "kline_stock.duckdb",
                    "target": "hikyuu_analytics.duckdb",
                    "action": "migrate",
                    "description": "K线数据"
                },
                {
                    "source": "metrics.db",  # SQLite -> DuckDB
                    "target": "hikyuu_analytics.duckdb",
                    "action": "migrate_sqlite_to_duckdb",
                    "description": "性能指标数据（SQLite转DuckDB）"
                }
            ],

            # 需要删除的重复/废弃文件
            "cleanup_files": [
                "factorweave_strategies.db",  # 重复
                "factorweave_analytics.duckdb",  # 重复
                "analytics_factorweave_analytics.duckdb",  # 重复
                "hikyuu_system.db",  # 空文件
                "hikyuu_system.db.bakck",  # 备份文件
            ]
        }

    def run_migration(self) -> bool:
        """运行完整的数据库迁移"""
        try:
            logger.info("🚀 开始数据库架构迁移")
            logger.info(f"📍 项目根目录: {self.project_root}")
            logger.info(f"🔄 模式: {'试运行' if self.dry_run else '正式迁移'}")

            # 1. 创建备份
            if not self._create_backup():
                return False

            # 2. 检查源数据库
            if not self._check_source_databases():
                return False

            # 3. 创建目标数据库
            if not self._create_target_databases():
                return False

            # 4. 迁移系统数据
            if not self._migrate_system_data():
                return False

            # 5. 迁移分析数据
            if not self._migrate_analytics_data():
                return False

            # 6. 验证迁移结果
            if not self._verify_migration():
                return False

            # 7. 更新代码引用
            if not self._update_code_references():
                return False

            # 8. 清理旧文件
            if not self._cleanup_old_files():
                return False

            logger.info("✅ 数据库迁移完成！")
            self._print_migration_summary()
            return True

        except Exception as e:
            logger.error(f"❌ 迁移失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _create_backup(self) -> bool:
        """创建数据库备份"""
        try:
            logger.info("📦 创建数据库备份...")

            if self.dry_run:
                logger.info("🔄 试运行模式：跳过备份创建")
                return True

            # 创建备份目录
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # 备份所有数据库文件
            backup_count = 0
            for db_file in self.db_dir.glob("*.db"):
                if db_file.is_file() and db_file.stat().st_size > 0:
                    backup_path = self.backup_dir / db_file.name
                    shutil.copy2(db_file, backup_path)
                    backup_count += 1
                    logger.info(f"  ✅ 备份: {db_file.name}")

            for db_file in self.db_dir.glob("*.duckdb"):
                if db_file.is_file() and db_file.stat().st_size > 0:
                    backup_path = self.backup_dir / db_file.name
                    shutil.copy2(db_file, backup_path)
                    backup_count += 1
                    logger.info(f"  ✅ 备份: {db_file.name}")

            logger.info(f"📦 备份完成，共备份 {backup_count} 个文件到: {self.backup_dir}")
            return True

        except Exception as e:
            logger.error(f"❌ 创建备份失败: {e}")
            return False

    def _check_source_databases(self) -> bool:
        """检查源数据库"""
        logger.info("🔍 检查源数据库...")

        all_sources = []
        all_sources.extend([m["source"] for m in self.migration_map["system_migrations"]])
        all_sources.extend([m["source"] for m in self.migration_map["analytics_migrations"]])

        missing_files = []
        existing_files = []

        for source_file in all_sources:
            source_path = self.db_dir / source_file
            if source_path.exists() and source_path.stat().st_size > 0:
                existing_files.append(source_file)
                logger.info(f"  ✅ 找到: {source_file}")
            else:
                missing_files.append(source_file)
                logger.warning(f"  ⚠️ 缺失: {source_file}")

        logger.info(f"📊 检查结果: {len(existing_files)} 个存在, {len(missing_files)} 个缺失")

        if missing_files:
            logger.warning("⚠️ 部分源数据库缺失，将跳过相关迁移")

        return len(existing_files) > 0

    def _create_target_databases(self) -> bool:
        """创建目标数据库"""
        try:
            logger.info("🏗️ 创建目标数据库...")

            if self.dry_run:
                logger.info("🔄 试运行模式：跳过目标数据库创建")
                return True

            # 创建系统数据库（SQLite）
            if not self.target_system_db.exists():
                with sqlite3.connect(str(self.target_system_db)) as conn:
                    conn.execute("SELECT 1")  # 创建数据库文件
                logger.info(f"  ✅ 创建系统数据库: {self.target_system_db.name}")

            # 创建分析数据库（DuckDB）
            if not self.target_analytics_db.exists():
                with duckdb.connect(str(self.target_analytics_db)) as conn:
                    conn.execute("SELECT 1")  # 创建数据库文件
                logger.info(f"  ✅ 创建分析数据库: {self.target_analytics_db.name}")

            return True

        except Exception as e:
            logger.error(f"❌ 创建目标数据库失败: {e}")
            return False

    def _migrate_system_data(self) -> bool:
        """迁移系统数据"""
        logger.info("🔄 迁移系统数据...")

        for migration in self.migration_map["system_migrations"]:
            source_path = self.db_dir / migration["source"]

            if not source_path.exists():
                logger.warning(f"  ⚠️ 跳过缺失文件: {migration['source']}")
                continue

            try:
                logger.info(f"  🔄 迁移: {migration['source']} -> {migration['target']}")

                if self.dry_run:
                    logger.info(f"    🔄 试运行: {migration['description']}")
                    continue

                # 实际迁移逻辑
                if migration["action"] == "migrate":
                    self._migrate_sqlite_database(source_path, self.target_system_db)
                elif migration["action"] == "merge":
                    self._merge_sqlite_database(source_path, self.target_system_db)

                logger.info(f"    ✅ 完成: {migration['description']}")

            except Exception as e:
                logger.error(f"    ❌ 迁移失败 {migration['source']}: {e}")
                return False

        return True

    def _migrate_analytics_data(self) -> bool:
        """迁移分析数据"""
        logger.info("🔄 迁移分析数据...")

        for migration in self.migration_map["analytics_migrations"]:
            source_path = self.db_dir / migration["source"]

            if not source_path.exists():
                logger.warning(f"  ⚠️ 跳过缺失文件: {migration['source']}")
                continue

            try:
                logger.info(f"  🔄 迁移: {migration['source']} -> {migration['target']}")

                if self.dry_run:
                    logger.info(f"    🔄 试运行: {migration['description']}")
                    continue

                # 实际迁移逻辑
                if migration["action"] == "migrate":
                    if source_path.suffix == ".duckdb":
                        self._migrate_duckdb_database(source_path, self.target_analytics_db)
                    else:
                        self._migrate_sqlite_to_duckdb(source_path, self.target_analytics_db)
                elif migration["action"] == "merge":
                    self._merge_duckdb_database(source_path, self.target_analytics_db)
                elif migration["action"] == "migrate_sqlite_to_duckdb":
                    self._migrate_sqlite_to_duckdb(source_path, self.target_analytics_db)

                logger.info(f"    ✅ 完成: {migration['description']}")

            except Exception as e:
                logger.error(f"    ❌ 迁移失败 {migration['source']}: {e}")
                return False

        return True

    def _migrate_sqlite_database(self, source_path: Path, target_path: Path):
        """迁移SQLite数据库"""
        # 简化实现：复制所有表结构和数据
        with sqlite3.connect(str(source_path)) as source_conn:
            with sqlite3.connect(str(target_path)) as target_conn:
                # 获取所有表
                tables = source_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()

                for (table_name,) in tables:
                    # 复制表结构
                    schema = source_conn.execute(
                        f"SELECT sql FROM sqlite_master WHERE name='{table_name}'"
                    ).fetchone()

                    if schema and schema[0]:
                        target_conn.execute(schema[0])

                    # 复制数据
                    data = source_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                    if data:
                        columns = [desc[0] for desc in source_conn.execute(f"SELECT * FROM {table_name}").description]
                        placeholders = ','.join(['?' for _ in columns])
                        target_conn.executemany(
                            f"INSERT INTO {table_name} VALUES ({placeholders})", data
                        )

    def _merge_sqlite_database(self, source_path: Path, target_path: Path):
        """合并SQLite数据库（避免表名冲突）"""
        # 实现表名前缀策略避免冲突
        prefix = source_path.stem + "_"

        with sqlite3.connect(str(source_path)) as source_conn:
            with sqlite3.connect(str(target_path)) as target_conn:
                tables = source_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()

                for (table_name,) in tables:
                    new_table_name = prefix + table_name

                    # 复制表结构（重命名表）
                    schema = source_conn.execute(
                        f"SELECT sql FROM sqlite_master WHERE name='{table_name}'"
                    ).fetchone()

                    if schema and schema[0]:
                        new_schema = schema[0].replace(table_name, new_table_name)
                        target_conn.execute(new_schema)

                    # 复制数据
                    data = source_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                    if data:
                        columns = [desc[0] for desc in source_conn.execute(f"SELECT * FROM {table_name}").description]
                        placeholders = ','.join(['?' for _ in columns])
                        target_conn.executemany(
                            f"INSERT INTO {new_table_name} VALUES ({placeholders})", data
                        )

    def _migrate_duckdb_database(self, source_path: Path, target_path: Path):
        """迁移DuckDB数据库"""
        with duckdb.connect(str(source_path)) as source_conn:
            with duckdb.connect(str(target_path)) as target_conn:
                # 获取所有表
                tables = source_conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()

                for (table_name,) in tables:
                    # 复制表结构和数据
                    target_conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM '{source_path}'::{table_name}")

    def _merge_duckdb_database(self, source_path: Path, target_path: Path):
        """合并DuckDB数据库"""
        # 类似SQLite合并，但使用DuckDB语法
        prefix = source_path.stem + "_"

        with duckdb.connect(str(source_path)) as source_conn:
            with duckdb.connect(str(target_path)) as target_conn:
                tables = source_conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()

                for (table_name,) in tables:
                    new_table_name = prefix + table_name
                    target_conn.execute(f"CREATE TABLE IF NOT EXISTS {new_table_name} AS SELECT * FROM '{source_path}'::{table_name}")

    def _migrate_sqlite_to_duckdb(self, source_path: Path, target_path: Path):
        """从SQLite迁移到DuckDB"""
        with sqlite3.connect(str(source_path)) as source_conn:
            with duckdb.connect(str(target_path)) as target_conn:
                tables = source_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()

                for (table_name,) in tables:
                    # 使用DuckDB的SQLite扩展直接读取
                    target_conn.execute("INSTALL sqlite")
                    target_conn.execute("LOAD sqlite")
                    target_conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM sqlite_scan('{source_path}', '{table_name}')")

    def _verify_migration(self) -> bool:
        """验证迁移结果"""
        logger.info("🔍 验证迁移结果...")

        if self.dry_run:
            logger.info("🔄 试运行模式：跳过验证")
            return True

        try:
            # 验证系统数据库
            if self.target_system_db.exists():
                with sqlite3.connect(str(self.target_system_db)) as conn:
                    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    logger.info(f"  ✅ 系统数据库包含 {len(tables)} 个表")

            # 验证分析数据库
            if self.target_analytics_db.exists():
                with duckdb.connect(str(self.target_analytics_db)) as conn:
                    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
                    logger.info(f"  ✅ 分析数据库包含 {len(tables)} 个表")

            return True

        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return False

    def _update_code_references(self) -> bool:
        """更新代码中的数据库路径引用"""
        logger.info("🔄 更新代码引用...")

        if self.dry_run:
            logger.info("🔄 试运行模式：跳过代码更新")
            return True

        # 这里可以实现自动代码更新逻辑
        # 暂时只记录需要手动更新的文件
        logger.info("  ⚠️ 需要手动更新以下文件中的数据库路径:")
        logger.info("    - core/services/config_service.py")
        logger.info("    - core/importdata/import_execution_engine.py")
        logger.info("    - utils/config_manager.py")
        logger.info("    - database_check_tool.py")

        return True

    def _cleanup_old_files(self) -> bool:
        """清理旧的数据库文件"""
        logger.info("🧹 清理旧文件...")

        if self.dry_run:
            logger.info("🔄 试运行模式：跳过文件清理")
            for filename in self.migration_map["cleanup_files"]:
                logger.info(f"  🔄 将删除: {filename}")
            return True

        cleaned_count = 0
        for filename in self.migration_map["cleanup_files"]:
            file_path = self.db_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"  ✅ 删除: {filename}")
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"  ⚠️ 删除失败 {filename}: {e}")

        logger.info(f"🧹 清理完成，删除了 {cleaned_count} 个文件")
        return True

    def _print_migration_summary(self):
        """打印迁移摘要"""
        logger.info("📊 迁移摘要:")
        logger.info("=" * 50)
        logger.info(f"📦 备份位置: {self.backup_dir}")
        logger.info(f"🎯 目标数据库:")
        logger.info(f"  - 系统数据库: {self.target_system_db}")
        logger.info(f"  - 分析数据库: {self.target_analytics_db}")
        logger.info("✅ 迁移完成！新的数据库架构已就绪。")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="HIkyuu-UI 数据库迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式（不实际执行迁移）")
    parser.add_argument("--backup-only", action="store_true", help="仅创建备份")

    args = parser.parse_args()

    migration_tool = DatabaseMigrationTool(dry_run=args.dry_run)

    if args.backup_only:
        logger.info("📦 仅执行备份操作...")
        success = migration_tool._create_backup()
    else:
        success = migration_tool.run_migration()

    if success:
        logger.info("🎉 操作完成！")
        sys.exit(0)
    else:
        logger.error("💥 操作失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
