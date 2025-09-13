#!/usr/bin/env python3
"""
验证完整的27种表类型Schema定义
确保所有表结构完整、DataType映射正确、索引配置合理
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    try:
        from core.database.table_manager import TableType, TableSchemaRegistry, DynamicTableManager
        from core.plugin_types import DataType

        print("🎯 验证完整的27种表类型Schema定义")
        print("="*60)

        # 初始化Schema注册表
        registry = TableSchemaRegistry()
        table_manager = DynamicTableManager()

        # 获取所有TableType
        all_table_types = list(TableType)
        print(f"📊 系统定义的表类型总数: {len(all_table_types)}")

        # 分类验证
        basic_types = [
            TableType.STOCK_BASIC_INFO, TableType.KLINE_DATA, TableType.FINANCIAL_STATEMENT,
            TableType.MACRO_ECONOMIC, TableType.REAL_TIME_QUOTE, TableType.MARKET_DEPTH,
            TableType.TRADE_TICK, TableType.NEWS, TableType.ANNOUNCEMENT,
            TableType.FUND_FLOW, TableType.TECHNICAL_INDICATOR
        ]

        core_types = [
            TableType.OPTION_DATA, TableType.FUTURES_DATA, TableType.INDEX_DATA,
            TableType.PORTFOLIO_DATA, TableType.ORDER_DATA, TableType.ACCOUNT_DATA,
            TableType.STRATEGY_DATA, TableType.RISK_METRICS, TableType.FACTOR_DATA,
            TableType.INTRADAY_DATA
        ]

        auxiliary_types = [
            TableType.BOND_DATA, TableType.FUND_DATA, TableType.EVENT_DATA,
            TableType.ASSET_LIST, TableType.SECTOR_DATA, TableType.PATTERN_RECOGNITION
        ]

        print(f"📋 基础数据类型: {len(basic_types)} 种")
        print(f"🎯 量化核心类型: {len(core_types)} 种")
        print(f"🔧 辅助数据类型: {len(auxiliary_types)} 种")
        print(f"📈 总计: {len(basic_types) + len(core_types) + len(auxiliary_types)} 种")
        print()

        # 验证每个表类型
        schema_results = {}
        mapping_results = {}

        print("🔍 验证Schema定义完整性...")
        for table_type in all_table_types:
            # 检查Schema定义
            schema = registry.get_schema(table_type)
            if schema:
                required_fields = ['data_source', 'created_at', 'data_quality_score', 'plugin_specific_data']
                missing_fields = [f for f in required_fields if f not in schema.columns]

                has_primary_key = len(schema.primary_key) > 0
                has_indexes = len(schema.indexes) > 0
                has_data_source_index = any('data_source' in idx.get('columns', []) for idx in schema.indexes)

                schema_results[table_type.value] = {
                    'schema_exists': True,
                    'columns_count': len(schema.columns),
                    'missing_fields': missing_fields,
                    'has_primary_key': has_primary_key,
                    'primary_key': schema.primary_key,
                    'indexes_count': len(schema.indexes),
                    'has_data_source_index': has_data_source_index,
                    'has_partitions': schema.partitions is not None,
                    'status': 'OK' if not missing_fields and has_primary_key and has_indexes and has_data_source_index else 'ISSUES'
                }
            else:
                schema_results[table_type.value] = {
                    'schema_exists': False,
                    'status': 'MISSING'
                }

            # 检查DataType映射
            try:
                table_name = table_manager.generate_table_name(
                    table_type=table_type,
                    plugin_name="test.plugin"
                )
                mapping_results[table_type.value] = {
                    'mapping_works': True,
                    'generated_name': table_name,
                    'status': 'OK'
                }
            except Exception as e:
                mapping_results[table_type.value] = {
                    'mapping_works': False,
                    'error': str(e),
                    'status': 'ERROR'
                }

        # 输出验证结果
        print("\n📋 Schema验证结果:")
        print("-" * 100)
        print(f"{'表类型':<25} {'Schema':<8} {'字段数':<6} {'主键':<8} {'索引数':<6} {'数据源索引':<10} {'分区':<6} {'状态':<10}")
        print("-" * 100)

        for table_type in all_table_types:
            result = schema_results[table_type.value]
            if result['schema_exists']:
                print(
                    f"{table_type.value:<25} {'✅':<8} {result['columns_count']:<6} {'✅' if result['has_primary_key'] else '❌':<8} {result['indexes_count']:<6} {'✅' if result['has_data_source_index'] else '❌':<10} {'✅' if result['has_partitions'] else '❌':<6} {result['status']:<10}")
            else:
                print(f"{table_type.value:<25} {'❌':<8} {'N/A':<6} {'N/A':<8} {'N/A':<6} {'N/A':<10} {'N/A':<6} {'MISSING':<10}")

        # 统计结果
        schema_ok = sum(1 for r in schema_results.values() if r.get('status') == 'OK')
        schema_issues = sum(1 for r in schema_results.values() if r.get('status') == 'ISSUES')
        schema_missing = sum(1 for r in schema_results.values() if r.get('status') == 'MISSING')

        mapping_ok = sum(1 for r in mapping_results.values() if r.get('status') == 'OK')
        mapping_error = sum(1 for r in mapping_results.values() if r.get('status') == 'ERROR')

        print("\n📊 验证统计:")
        print(f"✅ Schema完整: {schema_ok}/{len(all_table_types)} ({schema_ok/len(all_table_types)*100:.1f}%)")
        print(f"⚠️ Schema有问题: {schema_issues}/{len(all_table_types)}")
        print(f"❌ Schema缺失: {schema_missing}/{len(all_table_types)}")
        print(f"✅ DataType映射正常: {mapping_ok}/{len(all_table_types)} ({mapping_ok/len(all_table_types)*100:.1f}%)")
        print(f"❌ DataType映射错误: {mapping_error}/{len(all_table_types)}")

        # 详细问题报告
        if schema_issues > 0 or schema_missing > 0 or mapping_error > 0:
            print("\n🚨 问题详情:")
            for table_type, result in schema_results.items():
                if result.get('status') != 'OK':
                    print(f"\n❌ {table_type}:")
                    if not result['schema_exists']:
                        print(f"   - Schema定义缺失")
                    else:
                        if result['missing_fields']:
                            print(f"   - 缺少必要字段: {result['missing_fields']}")
                        if not result['has_primary_key']:
                            print(f"   - 缺少主键定义")
                        if not result['has_data_source_index']:
                            print(f"   - 缺少数据源索引")

            for table_type, result in mapping_results.items():
                if result.get('status') == 'ERROR':
                    print(f"\n❌ {table_type} DataType映射错误:")
                    print(f"   - 错误信息: {result['error']}")

        # 最终评估
        total_success_rate = (schema_ok + mapping_ok) / (len(all_table_types) * 2) * 100

        print("\n" + "="*60)
        print(f"🎯 总体评估: {total_success_rate:.1f}% 完整性")

        if total_success_rate >= 95:
            print("🎉 优秀！量化系统表结构非常完整")
        elif total_success_rate >= 85:
            print("✅ 良好！表结构基本完整，存在少量问题")
        elif total_success_rate >= 70:
            print("⚠️ 需要改进！存在一些重要问题")
        else:
            print("❌ 需要大量修复！表结构问题较多")

        # 显示覆盖范围
        print(f"\n📈 量化系统覆盖范围:")
        print(f"   基础数据支持: {len(basic_types)} 种表类型")
        print(f"   衍生品支持: OPTION_DATA, FUTURES_DATA, BOND_DATA")
        print(f"   组合管理支持: PORTFOLIO_DATA, ACCOUNT_DATA")
        print(f"   交易执行支持: ORDER_DATA")
        print(f"   策略研发支持: STRATEGY_DATA, FACTOR_DATA")
        print(f"   风险管理支持: RISK_METRICS")
        print(f"   技术分析支持: TECHNICAL_INDICATOR, PATTERN_RECOGNITION")
        print(f"   高频交易支持: INTRADAY_DATA, TRADE_TICK")

        return 0 if total_success_rate >= 95 else 1

    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
