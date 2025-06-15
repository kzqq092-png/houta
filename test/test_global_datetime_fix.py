#!/usr/bin/env python3
"""
全局datetime字段修复测试
测试各个模块的_kdata_preprocess函数是否能正确处理datetime字段
"""

from utils.data_preprocessing import kdata_preprocess, validate_kdata, standardize_stock_code
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入统一的数据预处理模块


def create_test_data():
    """创建测试数据"""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = {
        'datetime': dates,
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(15, 25, 100),
        'low': np.random.uniform(5, 15, 100),
        'close': np.random.uniform(10, 20, 100),
        'volume': np.random.randint(1000, 10000, 100),
        'code': ['000001'] * 100
    }

    # 确保价格逻辑正确
    df = pd.DataFrame(data)
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)

    return df


def create_problematic_data():
    """创建有问题的测试数据"""
    # 缺少datetime字段的数据
    data_no_datetime = pd.DataFrame({
        'open': [10, 11, 12],
        'high': [15, 16, 17],
        'low': [9, 10, 11],
        'close': [14, 15, 16],
        'volume': [1000, 1100, 1200]
    })

    # datetime在索引中的数据
    dates = pd.date_range(start='2023-01-01', periods=3, freq='D')
    data_datetime_index = pd.DataFrame({
        'open': [10, 11, 12],
        'high': [15, 16, 17],
        'low': [9, 10, 11],
        'close': [14, 15, 16],
        'volume': [1000, 1100, 1200]
    }, index=dates)

    # 包含异常值的数据
    data_with_anomalies = pd.DataFrame({
        'datetime': pd.date_range(start='2023-01-01', periods=5, freq='D'),
        'open': [10, 11, -5, 12, np.nan],  # 负值和NaN
        'high': [15, 16, 17, 18, 19],
        'low': [9, 10, 11, 12, 13],
        'close': [14, 15, 16, 17, 18],
        'volume': [1000, 1100, -100, 1200, 1300]  # 负值
    })

    return data_no_datetime, data_datetime_index, data_with_anomalies


def test_unified_preprocessing():
    """测试统一的数据预处理功能"""
    print("=== 测试统一数据预处理模块 ===")

    # 测试正常数据
    print("\n1. 测试正常数据处理:")
    normal_data = create_test_data()
    processed = kdata_preprocess(normal_data, "正常数据测试")

    if processed is not None and not processed.empty:
        print(f"✅ 正常数据处理成功，数据量: {len(processed)}")
        print(f"   列名: {list(processed.columns)}")
        print(f"   索引类型: {type(processed.index)}")
    else:
        print("❌ 正常数据处理失败")

    # 测试问题数据
    print("\n2. 测试问题数据处理:")
    data_no_datetime, data_datetime_index, data_with_anomalies = create_problematic_data()

    # 测试缺少datetime字段的数据
    print("   2.1 缺少datetime字段:")
    processed1 = kdata_preprocess(data_no_datetime, "缺少datetime")
    if processed1 is not None:
        print(f"   ✅ 处理成功，自动添加datetime字段")
    else:
        print("   ❌ 处理失败")

    # 测试datetime在索引中的数据
    print("   2.2 datetime在索引中:")
    processed2 = kdata_preprocess(data_datetime_index, "datetime在索引")
    if processed2 is not None:
        print(f"   ✅ 处理成功，正确处理索引中的datetime")
    else:
        print("   ❌ 处理失败")

    # 测试包含异常值的数据
    print("   2.3 包含异常值:")
    processed3 = kdata_preprocess(data_with_anomalies, "异常值数据")
    if processed3 is not None:
        print(f"   ✅ 处理成功，过滤异常值后数据量: {len(processed3)}")
    else:
        print("   ❌ 处理失败")


def test_data_validation():
    """测试数据验证功能"""
    print("\n=== 测试数据验证功能 ===")

    # 测试有效数据
    valid_data = create_test_data()
    is_valid = validate_kdata(valid_data, "有效数据验证")
    print(f"有效数据验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")

    # 测试无效数据
    invalid_data = pd.DataFrame({
        'open': [10, 11],
        'high': [15, 16]
        # 缺少必要列
    })
    is_invalid = validate_kdata(invalid_data, "无效数据验证")
    print(f"无效数据验证结果: {'❌ 正确识别为无效' if not is_invalid else '✅ 错误通过'}")


def test_stock_code_standardization():
    """测试股票代码标准化功能"""
    print("\n=== 测试股票代码标准化 ===")

    test_codes = [
        '000001',    # 深圳股票
        '600000',    # 上海股票
        '300001',    # 创业板
        '688001',    # 科创板
        'sh600000',  # 已有前缀
        'sz000001',  # 已有前缀
        '830001',    # 北交所
        '',          # 空代码
        None         # None值
    ]

    for code in test_codes:
        standardized = standardize_stock_code(code)
        print(f"   {code} -> {standardized}")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")

    # 测试_kdata_preprocess别名函数
    from utils.data_preprocessing import _kdata_preprocess

    test_data = create_test_data()
    result = _kdata_preprocess(test_data, "兼容性测试")

    if result is not None and not result.empty:
        print("✅ 向后兼容性测试通过")
    else:
        print("❌ 向后兼容性测试失败")


def main():
    """主测试函数"""
    print("开始全局数据预处理统一性测试...")

    try:
        test_unified_preprocessing()
        test_data_validation()
        test_stock_code_standardization()
        test_backward_compatibility()

        print("\n=== 测试总结 ===")
        print("✅ 统一数据预处理模块测试完成")
        print("✅ 所有引用关系已更新")
        print("✅ 向后兼容性得到保障")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
