"""
数据库升级脚本 - V2.0.3 to V2.0.4
添加标准量化表字段（5个新字段）

新增字段：
1. adj_close - 复权收盘价
2. adj_factor - 复权因子
3. turnover_rate - 换手率
4. vwap - 成交量加权均价
5. data_source - 数据来源
"""
import sys
import duckdb
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseUpgrader:
    """数据库升级工具"""

    def __init__(self):
        self.upgraded_tables = []
        self.failed_tables = []

    def upgrade_database(self, db_path: str) -> bool:
        """升级单个数据库"""
        try:
            if not Path(db_path).exists():
                logger.warning(f"数据库不存在，跳过: {db_path}")
                return False

            logger.info(f"\n{'='*60}")
            logger.info(f"正在升级数据库: {db_path}")
            logger.info(f"{'='*60}")

            conn = duckdb.connect(db_path)

            # 获取所有K线表
            tables = conn.execute("""
                SELECT table_name 
                FROM duckdb_tables() 
                WHERE table_name LIKE '%kline%'
            """).fetchall()

            if not tables:
                logger.warning("未发现K线表，跳过此数据库")
                conn.close()
                return True

            logger.info(f"发现 {len(tables)} 个K线表需要升级")

            for (table_name,) in tables:
                self._upgrade_table(conn, table_name)

            # 验证升级
            self._verify_upgrade(conn)

            conn.close()
            logger.success(f"✅ 数据库 {db_path} 升级完成！")
            return True

        except Exception as e:
            logger.error(f"❌ 数据库升级失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _upgrade_table(self, conn, table_name: str):
        """升级单个表"""
        try:
            logger.info(f"\n正在升级表: {table_name}")

            # 检查字段是否已存在
            existing_columns = self._get_table_columns(conn, table_name)

            # 添加新字段
            new_fields = {
                'adj_close': 'ALTER TABLE {} ADD COLUMN IF NOT EXISTS adj_close DOUBLE',
                'adj_factor': 'ALTER TABLE {} ADD COLUMN IF NOT EXISTS adj_factor DOUBLE DEFAULT 1.0',
                'turnover_rate': 'ALTER TABLE {} ADD COLUMN IF NOT EXISTS turnover_rate DOUBLE',
                'vwap': 'ALTER TABLE {} ADD COLUMN IF NOT EXISTS vwap DOUBLE',
                'data_source': "ALTER TABLE {} ADD COLUMN IF NOT EXISTS data_source VARCHAR DEFAULT 'unknown'"
            }

            added_fields = []
            for field_name, sql_template in new_fields.items():
                if field_name not in existing_columns:
                    sql = sql_template.format(table_name)
                    conn.execute(sql)
                    added_fields.append(field_name)
                    logger.debug(f"  ✅ 添加字段: {field_name}")
                else:
                    logger.debug(f"  ⏭️  字段已存在: {field_name}")

            if added_fields:
                # 更新现有数据的默认值
                self._update_default_values(conn, table_name)
                logger.success(f"✅ 表 {table_name} 升级成功，新增 {len(added_fields)} 个字段")
                self.upgraded_tables.append(table_name)
            else:
                logger.info(f"ℹ️  表 {table_name} 已是最新版本，跳过")

        except Exception as e:
            logger.error(f"❌ 表 {table_name} 升级失败: {e}")
            self.failed_tables.append((table_name, str(e)))

    def _get_table_columns(self, conn, table_name: str) -> set:
        """获取表的所有列名"""
        try:
            result = conn.execute(f"""
                SELECT column_name 
                FROM duckdb_columns() 
                WHERE table_name = '{table_name}'
            """).fetchall()
            return {row[0] for row in result}
        except Exception as e:
            logger.error(f"获取表列名失败: {e}")
            return set()

    def _update_default_values(self, conn, table_name: str):
        """更新现有数据的默认值"""
        try:
            # 检查表中是否有数据
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            if count == 0:
                logger.debug("  表为空，跳过默认值更新")
                return

            logger.info(f"  正在更新 {count} 条记录的默认值...")

            # 更新adj_factor和adj_close
            conn.execute(f"""
                UPDATE {table_name} 
                SET adj_factor = 1.0
                WHERE adj_factor IS NULL
            """)

            conn.execute(f"""
                UPDATE {table_name} 
                SET adj_close = close * adj_factor
                WHERE adj_close IS NULL AND close IS NOT NULL
            """)

            # 更新vwap
            conn.execute(f"""
                UPDATE {table_name} 
                SET vwap = CASE 
                    WHEN volume > 0 THEN amount / volume 
                    ELSE NULL 
                END
                WHERE vwap IS NULL AND amount IS NOT NULL AND volume IS NOT NULL
            """)

            # 更新data_source
            conn.execute(f"""
                UPDATE {table_name} 
                SET data_source = 'legacy'
                WHERE data_source = 'unknown' OR data_source IS NULL
            """)

            logger.debug("  ✅ 默认值更新完成")

        except Exception as e:
            logger.warning(f"  ⚠️  默认值更新失败: {e}")

    def _verify_upgrade(self, conn):
        """验证升级结果"""
        try:
            logger.info("\n" + "="*60)
            logger.info("升级验证")
            logger.info("="*60)

            result = conn.execute("""
                SELECT 
                    table_name,
                    COUNT(*) as total_columns,
                    SUM(CASE WHEN column_name = 'adj_close' THEN 1 ELSE 0 END) as has_adj_close,
                    SUM(CASE WHEN column_name = 'adj_factor' THEN 1 ELSE 0 END) as has_adj_factor,
                    SUM(CASE WHEN column_name = 'turnover_rate' THEN 1 ELSE 0 END) as has_turnover_rate,
                    SUM(CASE WHEN column_name = 'vwap' THEN 1 ELSE 0 END) as has_vwap,
                    SUM(CASE WHEN column_name = 'data_source' THEN 1 ELSE 0 END) as has_data_source
                FROM duckdb_columns()
                WHERE table_name LIKE '%kline%'
                GROUP BY table_name
            """).fetchall()

            logger.info("\n升级后的表结构：")
            for row in result:
                table_name, total_cols, has_adj_close, has_adj_factor, has_turnover_rate, has_vwap, has_data_source = row
                status = "✅" if all([has_adj_close, has_adj_factor, has_turnover_rate, has_vwap, has_data_source]) else "⚠️"
                logger.info(f"  {status} {table_name}: {total_cols}列 (新字段: {has_adj_close + has_adj_factor + has_turnover_rate + has_vwap + has_data_source}/5)")

        except Exception as e:
            logger.error(f"验证失败: {e}")

    def print_summary(self):
        """打印升级总结"""
        logger.info("\n" + "="*60)
        logger.info("升级总结")
        logger.info("="*60)

        logger.success(f"✅ 成功升级: {len(self.upgraded_tables)} 个表")
        if self.upgraded_tables:
            for table in self.upgraded_tables:
                logger.info(f"  - {table}")

        if self.failed_tables:
            logger.error(f"\n❌ 失败: {len(self.failed_tables)} 个表")
            for table, error in self.failed_tables:
                logger.error(f"  - {table}: {error}")

        logger.info("\n升级内容：")
        logger.info("  ✅ adj_close - 复权收盘价（量化回测必需）")
        logger.info("  ✅ adj_factor - 复权因子（默认1.0）")
        logger.info("  ✅ turnover_rate - 换手率（行业标准）")
        logger.info("  ✅ vwap - 成交量加权均价（机构常用）")
        logger.info("  ✅ data_source - 数据来源（追溯管理）")


def main():
    """主升级流程"""
    logger.info("="*60)
    logger.info("FactorWeave-Quant 数据库升级工具")
    logger.info("版本：V2.0.3 → V2.0.4")
    logger.info("升级内容：K线表增加5个字段（标准量化表）")
    logger.info("="*60)

    # 创建升级器
    upgrader = DatabaseUpgrader()

    # 需要升级的数据库列表
    db_paths = [
        "data/factorweave_system.sqlite",
        "data/enhanced_risk_monitor.db",
        # 自动搜索其他数据库
    ]

    # 自动搜索db和data目录下的所有数据库文件
    search_dirs = [ 'data']
    for search_dir in search_dirs:
        if Path(search_dir).exists():
            for ext in ['*.sqlite', '*.duckdb']:
                db_paths.extend(Path(search_dir).rglob(ext))

    # 去重
    db_paths = list(set(str(p) for p in db_paths))

    logger.info(f"\n发现 {len(db_paths)} 个数据库文件")

    # 逐个升级
    success_count = 0
    for db_path in db_paths:
        if upgrader.upgrade_database(db_path):
            success_count += 1

    # 打印总结
    upgrader.print_summary()

    logger.info("\n" + "="*60)
    if success_count == len(db_paths):
        logger.success("🎉 所有数据库升级完成！")
    else:
        logger.warning(f"⚠️  部分数据库升级失败 ({success_count}/{len(db_paths)})")
    logger.info("="*60)

    return success_count == len(db_paths)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
