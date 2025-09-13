"""
数据标准化引擎验证脚本

验证数据标准化引擎的核心功能：
1. 引擎初始化
2. 内置规则和模式
3. 数据标准化流程
4. 质量检查功能
5. 统计信息收集

作者: FactorWeave-Quant团队
版本: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.data_standardization_engine import (
        get_data_standardization_engine, FieldMapping, StandardDataSchema
    )
    from core.plugin_types import AssetType, DataType
    from core.data_router import DataSource
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 模块导入失败: {e}")
    exit(1)


def test_engine_initialization():
    """测试引擎初始化"""
    print("\n=== 测试引擎初始化 ===")

    try:
        engine = get_data_standardization_engine()
        print(f"✅ 引擎创建成功: {type(engine).__name__}")

        # 检查内置模式
        schemas = engine._builtin_schemas
        print(f"✅ 内置模式数量: {len(schemas)}")
        for name, schema in schemas.items():
            print(f"  - {name}: {schema.description}")

        # 检查内置规则
        rules = engine._standardization_rules
        print(f"✅ 内置规则数量: {len(rules)}")
        for rule_key in rules.keys():
            print(f"  - {rule_key}")

        return engine

    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_field_mapping():
    """测试字段映射功能"""
    print("\n=== 测试字段映射功能 ===")

    try:
        # 基本字段映射
        mapping = FieldMapping(
            source_field="price",
            target_field="close",
            data_type="float"
        )

        result = mapping.apply_transform("100.5")
        print(f"✅ 基本映射: '100.5' -> {result} ({type(result).__name__})")

        # 带转换函数的映射
        def price_to_cents(value):
            return float(value) * 100

        mapping_with_func = FieldMapping(
            source_field="price",
            target_field="price_cents",
            transform_func=price_to_cents
        )

        result = mapping_with_func.apply_transform("1.23")
        print(f"✅ 转换函数映射: '1.23' -> {result}")

        # 默认值处理
        mapping_with_default = FieldMapping(
            source_field="volume",
            target_field="volume",
            data_type="int",
            default_value=0,
            is_required=False
        )

        result = mapping_with_default.apply_transform(None)
        print(f"✅ 默认值处理: None -> {result}")

        return True

    except Exception as e:
        print(f"❌ 字段映射测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tongdaxin_data_standardization(engine):
    """测试通达信数据标准化"""
    print("\n=== 测试通达信数据标准化 ===")

    try:
        # 模拟通达信K线数据
        raw_data = pd.DataFrame({
            'Datetime': ['2023-01-01 09:30:00', '2023-01-02 09:30:00', '2023-01-03 09:30:00'],
            'Open': [100.0, 101.5, 99.8],
            'High': [102.0, 103.2, 101.0],
            'Low': [99.0, 100.8, 99.0],
            'Close': [101.0, 102.0, 100.5],
            'Volume': [1000000, 1200000, 800000],
            'Amount': [101000000.0, 122400000.0, 80400000.0]
        })

        print(f"原始数据形状: {raw_data.shape}")
        print("原始数据列:", list(raw_data.columns))

        # 执行标准化
        result = engine.standardize_data(
            raw_data=raw_data,
            source=DataSource.TONGDAXIN,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.STOCK_A,
            symbol="000001.SZ"
        )

        if result.success:
            print("✅ 通达信数据标准化成功")
            print(f"  - 原始记录数: {result.original_count}")
            print(f"  - 标准化记录数: {result.standardized_count}")
            print(f"  - 质量分数: {result.quality_score:.2f}")
            print(f"  - 处理时间: {result.processing_time_ms:.2f}ms")

            if result.quality_issues:
                print("  - 质量问题:")
                for issue in result.quality_issues:
                    print(f"    * {issue}")

            if result.data is not None:
                print("  - 标准化后的列:", list(result.data.columns))
                print("  - 样本数据:")
                print(result.data.head(2).to_string(index=False))
        else:
            print(f"❌ 通达信数据标准化失败: {result.metadata.get('error', '未知错误')}")

        return result.success

    except Exception as e:
        print(f"❌ 通达信数据标准化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_binance_data_standardization(engine):
    """测试币安数据标准化"""
    print("\n=== 测试币安数据标准化 ===")

    try:
        # 模拟币安K线数据（嵌套列表格式）
        raw_data = [
            [1640995200000, "47000.0", "48000.0", "46000.0", "47500.0", "100.5",
             1641081599999, "4750000.0", 1000, "50.0", "2375000.0", "0"],
            [1641081600000, "47500.0", "48500.0", "47000.0", "48000.0", "120.3",
             1641167999999, "5760000.0", 1200, "60.0", "2880000.0", "0"],
            [1641168000000, "48000.0", "49000.0", "47500.0", "48800.0", "95.7",
             1641254399999, "4670000.0", 950, "45.0", "2190000.0", "0"]
        ]

        print(f"原始数据记录数: {len(raw_data)}")

        # 执行标准化
        result = engine.standardize_data(
            raw_data=raw_data,
            source=DataSource.BINANCE,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.CRYPTO,
            symbol="BTCUSDT"
        )

        if result.success:
            print("✅ 币安数据标准化成功")
            print(f"  - 原始记录数: {result.original_count}")
            print(f"  - 标准化记录数: {result.standardized_count}")
            print(f"  - 质量分数: {result.quality_score:.2f}")
            print(f"  - 处理时间: {result.processing_time_ms:.2f}ms")

            if result.quality_issues:
                print("  - 质量问题:")
                for issue in result.quality_issues:
                    print(f"    * {issue}")

            if result.data is not None:
                print("  - 标准化后的列:", list(result.data.columns))
                print("  - 样本数据:")
                print(result.data.head(2).to_string(index=False))
        else:
            print(f"❌ 币安数据标准化失败: {result.metadata.get('error', '未知错误')}")

        return result.success

    except Exception as e:
        print(f"❌ 币安数据标准化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_checks(engine):
    """测试质量检查功能"""
    print("\n=== 测试质量检查功能 ===")

    try:
        # 创建有问题的数据
        bad_data = pd.DataFrame({
            'open': [100.0, 101.0, -50.0],  # 包含负价格
            'high': [99.0, 103.0, 102.0],   # 第一条记录最高价低于开盘价
            'low': [99.0, 100.0, 98.0],
            'close': [101.0, 102.0, 100.0]
        })

        print("测试价格有效性检查...")
        issues = engine._check_kline_price_validity(bad_data)
        print(f"✅ 发现 {len(issues)} 个价格问题:")
        for issue in issues:
            print(f"  - {issue}")

        # 创建不完整的数据
        incomplete_data = pd.DataFrame({
            'symbol': ['AAPL', None, 'MSFT'],  # 包含缺失值
            'timestamp': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0]
        })

        print("\n测试数据完整性检查...")
        issues = engine._check_kline_completeness(incomplete_data)
        print(f"✅ 发现 {len(issues)} 个完整性问题:")
        for issue in issues:
            print(f"  - {issue}")

        return True

    except Exception as e:
        print(f"❌ 质量检查测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_custom_rule_registration(engine):
    """测试自定义规则注册"""
    print("\n=== 测试自定义规则注册 ===")

    try:
        # 创建自定义模式
        custom_schema = StandardDataSchema(
            name="custom_test_schema",
            description="自定义测试模式",
            fields=[
                FieldMapping("sym", "symbol", "str", is_required=True),
                FieldMapping("dt", "timestamp", "datetime", is_required=True),
                FieldMapping("p", "price", "float", is_required=True),
                FieldMapping("v", "volume", "int", default_value=0)
            ],
            primary_key=["symbol", "timestamp"]
        )

        # 注册自定义规则
        engine.register_standardization_rule(
            source=DataSource.YAHOO,
            data_type=DataType.REAL_TIME_QUOTE,
            asset_type=AssetType.STOCK_US,
            schema=custom_schema
        )

        print("✅ 自定义规则注册成功")

        # 验证规则已注册
        rule_key = f"{DataSource.YAHOO.value}_{DataType.REAL_TIME_QUOTE.value}_{AssetType.STOCK_US.value}"
        if rule_key in engine._standardization_rules:
            print(f"✅ 规则验证成功: {rule_key}")
        else:
            print(f"❌ 规则验证失败: {rule_key}")
            return False

        # 测试自定义规则
        test_data = pd.DataFrame({
            'sym': ['AAPL'],
            'dt': ['2023-01-01 10:30:00'],
            'p': [150.5],
            'v': [1000]
        })

        result = engine.standardize_data(
            raw_data=test_data,
            source=DataSource.YAHOO,
            data_type=DataType.REAL_TIME_QUOTE,
            asset_type=AssetType.STOCK_US,
            symbol="AAPL"
        )

        if result.success:
            print("✅ 自定义规则数据标准化成功")
            print(f"  - 标准化记录数: {result.standardized_count}")
        else:
            print(f"❌ 自定义规则数据标准化失败: {result.metadata.get('error', '未知错误')}")

        return result.success

    except Exception as e:
        print(f"❌ 自定义规则注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_processing_statistics(engine):
    """测试处理统计功能"""
    print("\n=== 测试处理统计功能 ===")

    try:
        # 获取统计信息
        stats = engine.get_processing_statistics()

        print("✅ 处理统计信息:")
        print(f"  - 规则数量: {stats['rules_count']}")
        print(f"  - 模式数量: {stats['schemas_count']}")
        print(f"  - 总体成功率: {stats['success_rate']:.2%}")

        # 显示详细统计
        if stats['processing_stats']:
            print("  - 详细统计:")
            for rule_key, rule_stats in stats['processing_stats'].items():
                print(f"    * {rule_key}:")
                print(f"      - 总请求数: {rule_stats['total_requests']}")
                print(f"      - 成功请求数: {rule_stats['successful_requests']}")
                print(f"      - 失败请求数: {rule_stats['failed_requests']}")
                print(f"      - 平均处理时间: {rule_stats['avg_processing_time_ms']:.2f}ms")
                print(f"      - 平均质量分数: {rule_stats['avg_quality_score']:.2f}")

        # 获取支持的组合
        combinations = engine.get_supported_combinations()
        print(f"\n✅ 支持的数据源组合数量: {len(combinations)}")
        print("  - 支持的组合:")
        for combo in combinations[:5]:  # 只显示前5个
            print(f"    * {combo['source']} + {combo['data_type']} + {combo['asset_type']} -> {combo['schema']}")
        if len(combinations) > 5:
            print(f"    ... 还有 {len(combinations) - 5} 个组合")

        return True

    except Exception as e:
        print(f"❌ 处理统计测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始数据标准化引擎验证测试")

    # 测试结果统计
    test_results = []

    # 1. 引擎初始化测试
    engine = test_engine_initialization()
    test_results.append(("引擎初始化", engine is not None))

    if engine is None:
        print("\n❌ 引擎初始化失败，终止测试")
        return

    # 2. 字段映射测试
    result = test_field_mapping()
    test_results.append(("字段映射", result))

    # 3. 通达信数据标准化测试
    result = test_tongdaxin_data_standardization(engine)
    test_results.append(("通达信数据标准化", result))

    # 4. 币安数据标准化测试
    result = test_binance_data_standardization(engine)
    test_results.append(("币安数据标准化", result))

    # 5. 质量检查测试
    result = test_quality_checks(engine)
    test_results.append(("质量检查", result))

    # 6. 自定义规则注册测试
    result = test_custom_rule_registration(engine)
    test_results.append(("自定义规则注册", result))

    # 7. 处理统计测试
    result = test_processing_statistics(engine)
    test_results.append(("处理统计", result))

    # 汇总测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总")
    print("="*50)

    passed = 0
    total = len(test_results)

    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1

    print(f"\n总体结果: {passed}/{total} 通过 ({passed/total:.1%})")

    if passed == total:
        print("🎉 所有测试通过！数据标准化引擎验证成功")
    else:
        print(f"⚠️  有 {total - passed} 个测试失败，需要检查相关功能")


if __name__ == "__main__":
    main()
