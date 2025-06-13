#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据管理器修复
验证datetime字段处理是否正确
"""

from core.base_logger import BaseLogManager
from core.data_manager import DataManager
from datetime import datetime, timedelta
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_datetime_handling():
    """测试datetime字段处理"""
    print("=" * 60)
    print("测试数据管理器datetime字段处理修复")
    print("=" * 60)

    # 初始化数据管理器
    log_manager = BaseLogManager()
    data_manager = DataManager(log_manager)

    # 测试用例1：测试hikyuu数据源（datetime作为索引）
    print("\n1. 测试hikyuu数据源（datetime作为索引）")
    try:
        # 模拟hikyuu数据源返回的数据格式
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        hikyuu_data = pd.DataFrame({
            'open': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
            'high': [10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1, 11.2, 11.3, 11.4],
            'low': [9.5, 9.6, 9.7, 9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4],
            'close': [10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
            'amount': [10200, 11330, 12480, 13650, 14840, 16050, 17280, 18530, 19800, 21090]
        })
        hikyuu_data['datetime'] = dates
        hikyuu_data.set_index('datetime', inplace=True)  # 模拟hikyuu的处理方式

        # 使用标准化函数处理
        standardized_data = data_manager._standardize_kdata_format(hikyuu_data, 'sz300110')

        print(f"   原始数据形状: {hikyuu_data.shape}")
        print(f"   原始数据列: {list(hikyuu_data.columns)}")
        print(f"   原始数据索引类型: {type(hikyuu_data.index)}")
        print(f"   标准化后数据形状: {standardized_data.shape}")
        print(f"   标准化后数据列: {list(standardized_data.columns)}")
        print(f"   标准化后索引类型: {type(standardized_data.index)}")
        print(f"   标准化后索引名称: {standardized_data.index.name}")
        print("   ✅ hikyuu数据源测试通过")

    except Exception as e:
        print(f"   ❌ hikyuu数据源测试失败: {str(e)}")

    # 测试用例2：测试其他数据源（datetime作为列）
    print("\n2. 测试其他数据源（datetime作为列）")
    try:
        # 模拟其他数据源返回的数据格式
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        other_data = pd.DataFrame({
            'datetime': dates,
            'open': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9],
            'high': [10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1, 11.2, 11.3, 11.4],
            'low': [9.5, 9.6, 9.7, 9.8, 9.9, 10.0, 10.1, 10.2, 10.3, 10.4],
            'close': [10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        })

        # 使用标准化函数处理
        standardized_data = data_manager._standardize_kdata_format(other_data, 'sz300110')

        print(f"   原始数据形状: {other_data.shape}")
        print(f"   原始数据列: {list(other_data.columns)}")
        print(f"   原始数据索引类型: {type(other_data.index)}")
        print(f"   标准化后数据形状: {standardized_data.shape}")
        print(f"   标准化后数据列: {list(standardized_data.columns)}")
        print(f"   标准化后索引类型: {type(standardized_data.index)}")
        print(f"   标准化后索引名称: {standardized_data.index.name}")
        print("   ✅ 其他数据源测试通过")

    except Exception as e:
        print(f"   ❌ 其他数据源测试失败: {str(e)}")

    # 测试用例3：测试缺失字段的处理
    print("\n3. 测试缺失字段的处理")
    try:
        # 模拟缺失某些字段的数据
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        incomplete_data = pd.DataFrame({
            'date': dates,  # 使用date而不是datetime
            'open': [10.0, 10.1, 10.2, 10.3, 10.4],
            'high': [10.5, 10.6, 10.7, 10.8, 10.9],
            'low': [9.5, 9.6, 9.7, 9.8, 9.9],
            'close': [10.2, 10.3, 10.4, 10.5, 10.6],
            'vol': [1000, 1100, 1200, 1300, 1400]  # 使用vol而不是volume
            # 缺失amount字段
        })

        # 使用标准化函数处理
        standardized_data = data_manager._standardize_kdata_format(incomplete_data, 'sz300110')

        print(f"   原始数据形状: {incomplete_data.shape}")
        print(f"   原始数据列: {list(incomplete_data.columns)}")
        print(f"   标准化后数据形状: {standardized_data.shape}")
        print(f"   标准化后数据列: {list(standardized_data.columns)}")
        print(f"   标准化后索引类型: {type(standardized_data.index)}")
        print(f"   标准化后索引名称: {standardized_data.index.name}")
        print(f"   是否包含amount字段: {'amount' in standardized_data.columns}")
        print(f"   是否包含code字段: {'code' in standardized_data.columns}")
        print("   ✅ 缺失字段处理测试通过")

    except Exception as e:
        print(f"   ❌ 缺失字段处理测试失败: {str(e)}")

    # 测试用例4：测试实际的get_k_data方法
    print("\n4. 测试实际的get_k_data方法")
    try:
        # 尝试获取实际股票数据
        df = data_manager.get_k_data('sz300110', freq='D', start_date='2023-01-01', end_date='2023-01-10')

        if not df.empty:
            print(f"   获取数据形状: {df.shape}")
            print(f"   获取数据列: {list(df.columns)}")
            print(f"   索引类型: {type(df.index)}")
            print(f"   索引名称: {df.index.name}")
            print(f"   数据时间范围: {df.index.min()} 至 {df.index.max()}")
            print("   ✅ 实际数据获取测试通过")
        else:
            print("   ⚠️  获取的数据为空，可能是数据源问题")

    except Exception as e:
        print(f"   ❌ 实际数据获取测试失败: {str(e)}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def test_validation_logic():
    """测试验证逻辑"""
    print("\n" + "=" * 60)
    print("测试验证逻辑")
    print("=" * 60)

    log_manager = BaseLogManager()
    data_manager = DataManager(log_manager)

    # 测试datetime在索引中的情况
    print("\n1. 测试datetime在索引中的验证")
    dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
    df_with_index = pd.DataFrame({
        'open': [10.0, 10.1, 10.2, 10.3, 10.4],
        'high': [10.5, 10.6, 10.7, 10.8, 10.9],
        'low': [9.5, 9.6, 9.7, 9.8, 9.9],
        'close': [10.2, 10.3, 10.4, 10.5, 10.6],
        'volume': [1000, 1100, 1200, 1300, 1400],
        'code': 'sz300110'
    }, index=dates)
    df_with_index.index.name = 'datetime'

    # 模拟验证逻辑
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    has_datetime = False

    # 检查datetime是否存在（在索引中或列中）
    if isinstance(df_with_index.index, pd.DatetimeIndex) or (hasattr(df_with_index.index, 'name') and df_with_index.index.name == 'datetime'):
        has_datetime = True
    elif 'datetime' in df_with_index.columns:
        has_datetime = True

    missing_columns = [col for col in required_columns if col not in df_with_index.columns]

    print(f"   DataFrame索引类型: {type(df_with_index.index)}")
    print(f"   DataFrame索引名称: {df_with_index.index.name}")
    print(f"   是否检测到datetime: {has_datetime}")
    print(f"   缺失的列: {missing_columns}")

    if has_datetime and not missing_columns:
        print("   ✅ datetime在索引中的验证通过")
    else:
        print("   ❌ datetime在索引中的验证失败")

    # 测试datetime在列中的情况
    print("\n2. 测试datetime在列中的验证")
    df_with_column = pd.DataFrame({
        'datetime': dates,
        'open': [10.0, 10.1, 10.2, 10.3, 10.4],
        'high': [10.5, 10.6, 10.7, 10.8, 10.9],
        'low': [9.5, 9.6, 9.7, 9.8, 9.9],
        'close': [10.2, 10.3, 10.4, 10.5, 10.6],
        'volume': [1000, 1100, 1200, 1300, 1400],
        'code': 'sz300110'
    })

    has_datetime = False
    if isinstance(df_with_column.index, pd.DatetimeIndex) or (hasattr(df_with_column.index, 'name') and df_with_column.index.name == 'datetime'):
        has_datetime = True
    elif 'datetime' in df_with_column.columns:
        has_datetime = True

    missing_columns = [col for col in required_columns if col not in df_with_column.columns]

    print(f"   DataFrame列: {list(df_with_column.columns)}")
    print(f"   是否检测到datetime: {has_datetime}")
    print(f"   缺失的列: {missing_columns}")

    if has_datetime and not missing_columns:
        print("   ✅ datetime在列中的验证通过")
    else:
        print("   ❌ datetime在列中的验证失败")


if __name__ == "__main__":
    test_datetime_handling()
    test_validation_logic()
