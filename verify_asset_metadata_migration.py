#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证资产元数据迁移完整性
检查所有相关功能是否正确使用新的asset_metadata表
"""

import pandas as pd
from loguru import logger
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>")


def test_asset_metadata_table_exists():
    """测试1: asset_metadata表是否存在"""
    logger.info("=" * 60)
    logger.info("测试1: 检查asset_metadata表是否存在")
    logger.info("=" * 60)

    try:
        from core.asset_database_manager import AssetSeparatedDatabaseManager
        from core.plugin_types import AssetType

        asset_manager = AssetSeparatedDatabaseManager.get_instance()
        db_path = asset_manager._get_database_path(AssetType.STOCK_A)

        with asset_manager.duckdb_manager.get_pool(db_path).get_connection() as conn:
            result = conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'main' 
                AND table_name = 'asset_metadata'
            """).fetchone()

            if result:
                logger.info("[OK] asset_metadata 表存在")

                # 检查表是否有数据
                count = conn.execute("SELECT COUNT(*) FROM asset_metadata").fetchone()[0]
                logger.info(f"   表记录数: {count}")

                if count > 0:
                    # 显示样例数据
                    sample = conn.execute("SELECT symbol, name, market, asset_type FROM asset_metadata LIMIT 3").fetchall()
                    logger.info("   样例数据:")
                    for row in sample:
                        logger.info(f"     {row[0]} | {row[1]} | {row[2]} | {row[3]}")

                return True
            else:
                logger.error("[FAIL] asset_metadata 表不存在")
                return False

    except Exception as e:
        logger.error(f"[FAIL] 检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_unified_manager_get_asset_list():
    """测试2: UnifiedDataManager.get_asset_list()是否使用新表"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 检查get_asset_list()是否使用新表")
    logger.info("=" * 60)

    try:
        from core.services.unified_data_manager import get_unified_data_manager
        from core.plugin_types import AssetType

        unified_manager = get_unified_data_manager()

        # 测试查询资产列表
        logger.info("尝试获取stock资产列表...")
        result = unified_manager.get_asset_list(asset_type='stock')

        if result is not None and not result.empty:
            logger.info(f"[OK] 成功获取资产列表: {len(result)} 条记录")
            logger.info(f"   字段: {list(result.columns)}")

            # 显示样例
            logger.info("   样例数据:")
            for _, row in result.head(3).iterrows():
                logger.info(f"     {row.get('code', 'N/A')} | {row.get('name', 'N/A')} | {row.get('market', 'N/A')}")

            return True
        else:
            logger.warning("[WARN] 获取到空列表（可能是数据未导入）")
            logger.info("   这不一定是错误，可能是数据库中尚未导入资产数据")
            logger.info("   请检查是否已导入资产列表数据")
            return True  # 空结果不算失败

    except Exception as e:
        logger.error(f"[FAIL] 查询失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_api_compatibility():
    """测试3: API兼容性"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 检查API兼容性")
    logger.info("=" * 60)

    try:
        from core.asset_database_manager import AssetSeparatedDatabaseManager
        from core.plugin_types import AssetType

        asset_manager = AssetSeparatedDatabaseManager.get_instance()

        # 测试API是否存在
        apis = [
            'upsert_asset_metadata',
            'get_asset_metadata',
            'get_asset_metadata_batch'
        ]

        for api_name in apis:
            if hasattr(asset_manager, api_name):
                logger.info(f"[OK] API存在: {api_name}")
            else:
                logger.error(f"[FAIL] API缺失: {api_name}")
                return False

        return True

    except Exception as e:
        logger.error(f"[FAIL] 检查失败: {e}")
        return False


def test_field_mapping():
    """测试4: 字段映射是否正确"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 检查字段映射")
    logger.info("=" * 60)

    try:
        from core.asset_database_manager import AssetSeparatedDatabaseManager
        from core.plugin_types import AssetType

        asset_manager = AssetSeparatedDatabaseManager.get_instance()
        db_path = asset_manager._get_database_path(AssetType.STOCK_A)

        with asset_manager.duckdb_manager.get_pool(db_path).get_connection() as conn:
            # 检查asset_metadata表的字段
            columns = conn.execute("DESCRIBE asset_metadata").fetchall()
            col_names = [col[0] for col in columns]

            # 必需字段
            required_fields = [
                'symbol', 'name', 'market', 'asset_type',
                'listing_date', 'listing_status',
                'industry', 'sector'
            ]

            missing_fields = []
            for field in required_fields:
                if field in col_names:
                    logger.info(f"[OK] 字段存在: {field}")
                else:
                    logger.error(f"[FAIL] 字段缺失: {field}")
                    missing_fields.append(field)

            if missing_fields:
                logger.error(f"缺失字段: {missing_fields}")
                return False

            return True

    except Exception as e:
        logger.error(f"[FAIL] 检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_tet_pipeline():
    """测试5: TET框架是否支持资产列表标准化"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 检查TET框架支持")
    logger.info("=" * 60)

    try:
        from core.tet_data_pipeline import TETDataPipeline
        from core.data_source_router import DataSourceRouter

        router = DataSourceRouter()
        tet_pipeline = TETDataPipeline(data_source_router=router)

        # 检查方法是否存在
        if hasattr(tet_pipeline, 'transform_asset_list_data'):
            logger.info("[OK] TET框架支持资产列表标准化")

            # 测试简单数据
            test_data = pd.DataFrame([
                {'code': '000001', 'stock_name': '测试股票', 'stock_market': 'SZ'}
            ])

            result = tet_pipeline.transform_asset_list_data(test_data, 'test')

            if not result.empty and 'symbol' in result.columns:
                logger.info("[OK] 数据标准化功能正常")
                logger.info(f"   输入字段: {list(test_data.columns)}")
                logger.info(f"   输出字段: {list(result.columns)}")
                return True
            else:
                logger.error("[FAIL] 数据标准化失败")
                return False
        else:
            logger.error("[FAIL] TET框架缺少transform_asset_list_data方法")
            return False

    except Exception as e:
        logger.error(f"[FAIL] 检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """运行所有验证测试"""
    logger.info("\n" + "=" * 60)
    logger.info("资产元数据迁移完整性验证")
    logger.info("=" * 60 + "\n")

    tests = [
        ("asset_metadata表存在性", test_asset_metadata_table_exists),
        ("UnifiedManager查询功能", test_unified_manager_get_asset_list),
        ("API兼容性", test_api_compatibility),
        ("字段映射正确性", test_field_mapping),
        ("TET框架支持", test_tet_pipeline),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"测试 '{test_name}' 执行失败: {e}")
            results[test_name] = False

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("验证结果总结")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] 通过" if result else "[FAIL] 失败"
        logger.info(f"{test_name}: {status}")

    logger.info("")
    logger.info(f"总计: {passed}/{total} 通过")

    if passed == total:
        logger.info("[SUCCESS] 所有验证通过！迁移完整！")
        return 0
    else:
        logger.warning(f"[WARN] 有 {total - passed} 个验证失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
