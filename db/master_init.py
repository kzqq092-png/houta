#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FactorWeave-Quant 数据库系统统一初始化入口

这是系统唯一的数据库初始化入口点，整合了所有初始化逻辑：
1. 完整数据库架构初始化（SQLite + DuckDB）
2. 形态算法代码初始化
3. 系统配置和初始数据
4. 完整性验证和报告生成
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db/init_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MasterDatabaseInitializer:
    """主数据库初始化器"""

    def __init__(self):
        self.db_dir = Path(__file__).parent
        self.success_steps = []
        self.failed_steps = []

    def initialize_all(self):
        """执行完整的数据库初始化流程"""
        logger.info("开始FactorWeave-Quant数据库系统完整初始化")

        try:
            # 步骤1: 完整数据库架构初始化
            self._step1_database_schema()

            # 步骤2: 形态算法初始化
            self._step2_pattern_algorithms()

            # 步骤3: 系统验证
            self._step3_system_verification()

            # 步骤4: 生成报告
            self._step4_generate_report()

            logger.info("SUCCESS 数据库系统初始化完成")
            return True

        except Exception as e:
            logger.error(f"ERROR 数据库初始化失败: {e}")
            self._generate_error_report(e)
            return False

    def _step1_database_schema(self):
        """步骤1: 数据库架构初始化"""
        logger.info("执行数据库架构初始化...")

        try:
            from complete_database_init import CompleteDatabaseInitializer

            initializer = CompleteDatabaseInitializer()
            if initializer.initialize_all_databases():
                self.success_steps.append("数据库架构初始化")
                logger.info("SUCCESS 数据库架构初始化完成")
            else:
                raise Exception("数据库架构初始化失败")

        except Exception as e:
            self.failed_steps.append(f"数据库架构初始化: {e}")
            raise

    def _step2_pattern_algorithms(self):
        """步骤2: 形态算法初始化"""
        logger.info("执行形态算法初始化...")

        try:
            from init_pattern_algorithms import init_pattern_algorithms

            init_pattern_algorithms()
            self.success_steps.append("形态算法初始化")
            logger.info("SUCCESS 形态算法初始化完成")

        except Exception as e:
            self.failed_steps.append(f"形态算法初始化: {e}")
            logger.warning(f"WARNING 形态算法初始化失败: {e}")
            # 不抛出异常，允许继续执行

    def _step3_system_verification(self):
        """步骤3: 系统完整性验证"""
        logger.info("执行系统完整性验证...")

        try:
            # 验证SQLite数据库
            sqlite_ok = self._verify_sqlite_database()

            # 验证DuckDB数据库
            duckdb_ok = self._verify_duckdb_database()

            if sqlite_ok and duckdb_ok:
                self.success_steps.append("系统完整性验证")
                logger.info("SUCCESS 系统完整性验证通过")
            else:
                raise Exception("系统完整性验证失败")

        except Exception as e:
            self.failed_steps.append(f"系统完整性验证: {e}")
            raise

    def _step4_generate_report(self):
        """步骤4: 生成初始化报告"""
        logger.info("生成初始化报告...")

        report_path = self.db_dir / f"init_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# FactorWeave-Quant 数据库初始化报告\n\n")
            f.write(f"**初始化时间**: {datetime.now().isoformat()}\n\n")

            f.write(f"## ✅ 成功步骤 ({len(self.success_steps)})\n")
            for step in self.success_steps:
                f.write(f"- {step}\n")

            if self.failed_steps:
                f.write(f"\n## ❌ 失败步骤 ({len(self.failed_steps)})\n")
                for step in self.failed_steps:
                    f.write(f"- {step}\n")

            f.write(f"\n## 📊 数据库文件状态\n")
            for db_file in self.db_dir.glob("*.db"):
                size = db_file.stat().st_size / 1024 / 1024  # MB
                f.write(f"- {db_file.name}: {size:.2f} MB\n")

        logger.info(f"初始化报告已生成: {report_path}")
        self.success_steps.append("初始化报告生成")

    def _verify_sqlite_database(self):
        """验证SQLite数据库"""
        import sqlite3

        try:
            db_path = self.db_dir / "factorweave_system.sqlite"
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # 检查关键表
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

                if table_count < 10:  # 预期至少有10个表
                    return False

                # 检查关键数据
                cursor.execute("SELECT COUNT(*) FROM config")
                config_count = cursor.fetchone()[0]

                return config_count > 0

        except Exception as e:
            logger.error(f"SQLite验证失败: {e}")
            return False

    def _verify_duckdb_database(self):
        """验证DuckDB数据库"""
        try:
            import duckdb

            db_path = self.db_dir / "factorweave_analytics.duckdb"
            conn = duckdb.connect(str(db_path))

            # 检查表数量
            result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'").fetchone()
            table_count = result[0] if result else 0

            conn.close()
            return table_count >= 5  # 预期至少有5个分析表

        except Exception as e:
            logger.error(f"DuckDB验证失败: {e}")
            return False

    def _generate_error_report(self, error):
        """生成错误报告"""
        error_path = self.db_dir / f"init_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f"数据库初始化错误报告\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"错误: {error}\n\n")

            f.write("成功步骤:\n")
            for step in self.success_steps:
                f.write(f"  ✅ {step}\n")

            f.write("\n失败步骤:\n")
            for step in self.failed_steps:
                f.write(f"  ❌ {step}\n")

        logger.error(f"错误报告已生成: {error_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("FactorWeave-Quant 数据库系统统一初始化")
    print("=" * 60)

    initializer = MasterDatabaseInitializer()
    success = initializer.initialize_all()

    if success:
        print("\n🎉 数据库系统初始化成功！")
        print("\n📊 初始化内容:")
        print("  ✅ SQLite系统数据库 (OLTP)")
        print("  ✅ DuckDB分析数据库 (OLAP)")
        print("  ✅ 完整表结构和索引")
        print("  ✅ 初始配置和数据")
        print("  ✅ 形态算法代码")
        print("  ✅ 系统完整性验证")

        return True
    else:
        print("\n❌ 数据库系统初始化失败！")
        print("请查看错误报告了解详细信息。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
