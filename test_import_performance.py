#!/usr/bin/env python3
"""
数据导入性能测试脚本

用于测试优化后的并发下载和批量保存功能
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s [%(name)s::%(funcName)s]'
)
logger = logging.getLogger(__name__)


def test_import_performance():
    """测试导入性能"""
    try:
        # 导入必要的模块
        from core.importdata.import_execution_engine import DataImportExecutionEngine
        from core.importdata.import_config_manager import ImportTaskConfig, ImportMode, DataFrequency
        from core.services.unified_data_manager import get_unified_data_manager

        logger.info("🚀 开始数据导入性能测试")

        # 创建测试任务配置
        test_symbols = [
            "000001",  # 平安银行
            "000002",  # 万科A
            "000858",  # 五粮液
            "002415",  # 海康威视
            "600036",  # 招商银行
        ]

        task_config = ImportTaskConfig(
            task_id="test_performance_001",
            data_source="examples.akshare_stock_plugin",
            asset_type="股票",
            data_type="K线数据",
            symbols=test_symbols,
            start_date="2024-01-01",
            end_date="2024-08-30",
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            max_workers=4  # 测试并发数
        )

        logger.info(f"📊 测试配置:")
        logger.info(f"  - 股票数量: {len(test_symbols)}")
        logger.info(f"  - 时间范围: {task_config.start_date} 到 {task_config.end_date}")
        logger.info(f"  - 并发线程: {task_config.max_workers}")
        logger.info(f"  - 数据频率: {task_config.frequency.value}")

        # 创建导入引擎
        data_manager = get_unified_data_manager()
        import_engine = DataImportExecutionEngine(data_manager=data_manager)

        # 记录开始时间
        start_time = time.time()

        # 执行导入任务
        logger.info("🔄 开始执行导入任务...")
        task_id = import_engine.start_task(task_config.task_id)

        if task_id:
            logger.info(f"✅ 任务启动成功，任务ID: {task_id}")

            # 等待任务完成
            max_wait_time = 300  # 最多等待5分钟
            wait_start = time.time()

            while time.time() - wait_start < max_wait_time:
                status = import_engine.get_task_status(task_id)
                logger.info(f"📊 任务状态: {status}")

                if status and status.get('status') in ['completed', 'failed', 'cancelled']:
                    break

                time.sleep(2)  # 每2秒检查一次

            # 记录结束时间
            end_time = time.time()
            total_time = end_time - start_time

            # 获取最终状态
            final_status = import_engine.get_task_status(task_id)

            logger.info("📈 性能测试结果:")
            logger.info(f"  - 总耗时: {total_time:.2f} 秒")
            logger.info(f"  - 平均每只股票: {total_time/len(test_symbols):.2f} 秒")
            logger.info(f"  - 最终状态: {final_status}")

            # 检查数据库中的数据
            logger.info("🔍 检查导入的数据...")
            check_imported_data()

        else:
            logger.error("❌ 任务启动失败")

    except Exception as e:
        logger.error(f"❌ 性能测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


def check_imported_data():
    """检查导入的数据"""
    try:
        import duckdb

        db_path = "db/kline_stock.duckdb"
        if not Path(db_path).exists():
            logger.warning(f"⚠️ 数据库文件不存在: {db_path}")
            return

        with duckdb.connect(db_path) as conn:
            # 检查表是否存在
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_name LIKE '%kline%'
            """
            tables_result = conn.execute(tables_query).fetchall()

            if not tables_result:
                logger.warning("⚠️ 没有找到K线数据表")
                return

            for table_row in tables_result:
                table_name = table_row[0]
                logger.info(f"📊 检查表: {table_name}")

                # 统计数据
                stats_query = f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as stock_count,
                    MIN(datetime) as min_date,
                    MAX(datetime) as max_date
                FROM {table_name}
                """
                stats_result = conn.execute(stats_query).fetchone()

                if stats_result:
                    total_records, stock_count, min_date, max_date = stats_result
                    logger.info(f"  ✅ 总记录数: {total_records:,}")
                    logger.info(f"  📈 股票数量: {stock_count}")
                    logger.info(f"  📅 日期范围: {min_date} 到 {max_date}")

                    # 显示每只股票的记录数
                    stock_stats_query = f"""
                    SELECT symbol, COUNT(*) as records
                    FROM {table_name}
                    GROUP BY symbol
                    ORDER BY symbol
                    """
                    stock_stats = conn.execute(stock_stats_query).fetchall()

                    logger.info("  📊 各股票记录数:")
                    for symbol, records in stock_stats:
                        logger.info(f"    - {symbol}: {records:,} 条")

    except Exception as e:
        logger.error(f"❌ 检查导入数据失败: {e}")


if __name__ == "__main__":
    test_import_performance()
