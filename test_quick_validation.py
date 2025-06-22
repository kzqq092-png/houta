#!/usr/bin/env python3
"""
快速验证指标架构是否正常工作
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_data():
    """创建测试数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

    data = pd.DataFrame({
        'datetime': dates,
        'open': prices * (1 + np.random.randn(100) * 0.01),
        'high': prices * (1 + np.random.rand(100) * 0.02),
        'low': prices * (1 - np.random.rand(100) * 0.02),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    })
    data.set_index('datetime', inplace=True)
    return data


def test_core_imports():
    """测试核心模块导入"""
    print("=== 测试核心模块导入 ===")

    try:
        from core.unified_indicator_manager import get_unified_indicator_manager
        print("✓ 统一指标管理器导入成功")
    except Exception as e:
        print(f"✗ 统一指标管理器导入失败: {e}")
        return False

    try:
        from core.services.indicator_service import get_indicator_service
        print("✓ 指标服务导入成功")
    except Exception as e:
        print(f"✗ 指标服务导入失败: {e}")
        return False

    try:
        from core.services.indicator_ui_adapter import get_indicator_ui_adapter
        print("✓ UI适配器导入成功")
    except Exception as e:
        print(f"✗ UI适配器导入失败: {e}")
        return False

    return True


def test_indicator_calculation():
    """测试指标计算"""
    print("\n=== 测试指标计算 ===")

    try:
        from core.services.indicator_service import get_indicator_service
        service = get_indicator_service()

        # 创建测试数据
        test_data = create_test_data()

        # 测试MA指标
        response = service.calculate_indicator('MA', test_data, period=20)
        if response.success:
            print(f"✓ MA指标计算成功，结果长度: {len(response.result)}")
        else:
            print(f"✗ MA指标计算失败: {response.error_message}")
            return False

        # 测试MACD指标
        response = service.calculate_indicator('MACD', test_data, fast_period=12, slow_period=26, signal_period=9)
        if response.success:
            print(f"✓ MACD指标计算成功，结果类型: {type(response.result)}")
        else:
            print(f"✗ MACD指标计算失败: {response.error_message}")

        return True

    except Exception as e:
        print(f"✗ 指标计算测试失败: {e}")
        return False


def test_ui_adapter():
    """测试UI适配器"""
    print("\n=== 测试UI适配器 ===")

    try:
        from core.services.indicator_ui_adapter import get_indicator_ui_adapter
        adapter = get_indicator_ui_adapter()

        # 测试获取指标列表
        indicators = adapter.get_indicator_list()
        if indicators:
            print(f"✓ 获取指标列表成功，共 {len(indicators)} 个指标")
        else:
            print("⚠ 指标列表为空")

        # 测试按分类获取指标
        categories = adapter.get_indicators_by_category()
        if categories:
            print(f"✓ 获取指标分类成功，共 {len(categories)} 个分类")
        else:
            print("⚠ 指标分类为空")

        return True

    except Exception as e:
        print(f"✗ UI适配器测试失败: {e}")
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")

    try:
        from core.unified_indicator_manager import get_unified_indicator_manager
        manager = get_unified_indicator_manager()

        # 创建测试数据
        test_data = create_test_data()

        # 测试calculate_indicator方法
        result = manager.calculate_indicator('MA', test_data, period=20)
        if result is not None:
            print("✓ 旧接口calculate_indicator工作正常")
        else:
            print("⚠ 旧接口calculate_indicator返回None")

        return True

    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始快速验证指标架构...")
    print("=" * 50)

    test_results = []

    # 运行各项测试
    test_results.append(("核心模块导入", test_core_imports()))
    test_results.append(("指标计算", test_indicator_calculation()))
    test_results.append(("UI适配器", test_ui_adapter()))
    test_results.append(("向后兼容性", test_backward_compatibility()))

    # 输出测试结果
    print("\n" + "=" * 50)
    print("验证结果汇总:")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"总计: {passed}/{total} 项验证通过")

    if passed == total:
        print("🎉 指标架构验证完全通过！")
    else:
        print(f"⚠ {total - passed} 项验证失败，需要修复")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
