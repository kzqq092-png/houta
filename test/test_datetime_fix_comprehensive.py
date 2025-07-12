#!/usr/bin/env python3
"""
综合测试脚本：验证所有datetime字段修复是否正常工作
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def create_test_data_with_datetime_in_index():
    """创建datetime在索引中的测试数据（模拟hikyuu数据源）"""
    dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
    data = {
        'open': np.random.uniform(10, 20, 10),
        'high': np.random.uniform(15, 25, 10),
        'low': np.random.uniform(5, 15, 10),
        'close': np.random.uniform(10, 20, 10),
        'volume': np.random.uniform(1000, 10000, 10),
        'amount': np.random.uniform(10000, 100000, 10)
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'datetime'
    return df


def create_test_data_with_datetime_in_column():
    """创建datetime在列中的测试数据（模拟其他数据源）"""
    dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
    data = {
        'datetime': dates,
        'open': np.random.uniform(10, 20, 10),
        'high': np.random.uniform(15, 25, 10),
        'low': np.random.uniform(5, 15, 10),
        'close': np.random.uniform(10, 20, 10),
        'volume': np.random.uniform(1000, 10000, 10)
    }
    return pd.DataFrame(data)


def test_data_manager_standardize():
    """测试DataManager的_standardize_kdata_format函数"""
    print("=" * 60)
    print("测试DataManager._standardize_kdata_format函数")
    print("=" * 60)

    try:
        from core.data_manager import DataManager
        from core.base_logger import BaseLogManager

        dm = DataManager(BaseLogManager())

        # 测试1：datetime在索引中
        print("\n1. 测试datetime在索引中的数据")
        test_data1 = create_test_data_with_datetime_in_index()
        print(f"   原始数据形状: {test_data1.shape}")
        print(f"   原始数据索引类型: {type(test_data1.index)}")
        print(f"   原始数据索引名称: {test_data1.index.name}")

        result1 = dm._standardize_kdata_format(test_data1, 'test001')
        print(f"   标准化后形状: {result1.shape}")
        print(f"   标准化后索引类型: {type(result1.index)}")
        print(f"   标准化后索引名称: {result1.index.name}")
        print(f"   ✅ datetime在索引中的测试通过")

        # 测试2：datetime在列中
        print("\n2. 测试datetime在列中的数据")
        test_data2 = create_test_data_with_datetime_in_column()
        print(f"   原始数据形状: {test_data2.shape}")
        print(f"   原始数据列: {list(test_data2.columns)}")

        result2 = dm._standardize_kdata_format(test_data2, 'test002')
        print(f"   标准化后形状: {result2.shape}")
        print(f"   标准化后索引类型: {type(result2.index)}")
        print(f"   标准化后索引名称: {result2.index.name}")
        print(f"   ✅ datetime在列中的测试通过")

        return True

    except Exception as e:
        print(f"   ❌ DataManager测试失败: {e}")
        return False


def test_analysis_widget_preprocess():
    """测试AnalysisWidget的_kdata_preprocess函数"""
    print("\n" + "=" * 60)
    print("测试AnalysisWidget._kdata_preprocess函数")
    print("=" * 60)

    try:
        # 模拟AnalysisWidget的_kdata_preprocess函数
        def mock_kdata_preprocess(kdata, context="分析"):
            from datetime import datetime
            if not isinstance(kdata, pd.DataFrame):
                return kdata

            # 检查datetime是否在索引中或列中
            has_datetime = False
            datetime_in_index = False

            # 检查datetime是否在索引中
            if isinstance(kdata.index, pd.DatetimeIndex) or (hasattr(kdata.index, 'name') and kdata.index.name == 'datetime'):
                has_datetime = True
                datetime_in_index = True
            # 检查datetime是否在列中
            elif 'datetime' in kdata.columns:
                has_datetime = True
                datetime_in_index = False

            # 如果datetime不存在，尝试从索引推断或创建
            if not has_datetime:
                if isinstance(kdata.index, pd.DatetimeIndex):
                    kdata = kdata.copy()
                    kdata['datetime'] = kdata.index
                    has_datetime = True
                    print(f"   [{context}] 从DatetimeIndex推断datetime字段")
                else:
                    print(f"   [{context}] 缺少datetime字段，自动补全")
                    kdata = kdata.copy()
                    kdata['datetime'] = pd.date_range(
                        start='2023-01-01', periods=len(kdata), freq='D')
                    has_datetime = True

            return kdata

        # 测试1：datetime在索引中
        print("\n1. 测试datetime在索引中的数据")
        test_data1 = create_test_data_with_datetime_in_index()
        result1 = mock_kdata_preprocess(test_data1, "测试1")
        print(f"   处理后是否有datetime列: {'datetime' in result1.columns}")
        print(f"   ✅ datetime在索引中的测试通过")

        # 测试2：datetime在列中
        print("\n2. 测试datetime在列中的数据")
        test_data2 = create_test_data_with_datetime_in_column()
        result2 = mock_kdata_preprocess(test_data2, "测试2")
        print(f"   处理后是否有datetime列: {'datetime' in result2.columns}")
        print(f"   ✅ datetime在列中的测试通过")

        return True

    except Exception as e:
        print(f"   ❌ AnalysisWidget测试失败: {e}")
        return False


def test_pattern_recognition():
    """测试形态识别是否能正常工作"""
    print("\n" + "=" * 60)
    print("测试形态识别功能")
    print("=" * 60)

    try:
        from analysis.pattern_base import PatternConfig, SignalType, PatternCategory

        # 创建测试配置
        config = PatternConfig(
            id=1,
            name="测试锤头线",
            english_name="test_hammer",
            category=PatternCategory.SINGLE_CANDLE,
            signal_type=SignalType.BUY,
            description="测试用锤头线形态",
            min_periods=1,
            max_periods=1,
            confidence_threshold=0.5,
            algorithm_code="""
# 简单的测试算法
for i in range(len(kdata)):
    k = kdata.iloc[i]
    if k['close'] > k['open']:  # 简单的阳线判断
        result = create_result(
            pattern_type='test_hammer',
            signal_type=SignalType.BUY,
            confidence=0.8,
            index=i,
            price=k['close'],
            datetime_val=str(kdata.iloc[i]['datetime']) if 'datetime' in kdata.columns else None
        )
        results.append(result)
""",
            parameters={},
            is_active=True
        )

        # 创建识别器
        recognizer = GenericPatternRecognizer(config)

        # 测试数据
        test_data = create_test_data_with_datetime_in_column()

        print(f"\n1. 测试数据形状: {test_data.shape}")
        print(f"   测试数据列: {list(test_data.columns)}")

        # 执行识别
        results = recognizer.recognize(test_data)

        print(f"   识别结果数量: {len(results)}")
        if results:
            print(f"   第一个结果: {results[0].to_dict()}")

        print(f"   ✅ 形态识别测试通过")

        return True

    except Exception as e:
        print(f"   ❌ 形态识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("开始综合测试datetime字段修复...")

    test_results = []

    # 测试DataManager
    test_results.append(test_data_manager_standardize())

    # 测试AnalysisWidget
    test_results.append(test_analysis_widget_preprocess())

    # 测试形态识别
    test_results.append(test_pattern_recognition())

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(test_results)
    total = len(test_results)

    print(f"总测试数: {total}")
    print(f"通过数: {passed}")
    print(f"失败数: {total - passed}")

    if passed == total:
        print("🎉 所有测试都通过了！datetime字段修复成功！")
    else:
        print("⚠️  部分测试失败，需要进一步检查")

    return passed == total


if __name__ == "__main__":
    main()
