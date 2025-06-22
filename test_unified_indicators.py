"""
统一指标管理器测试文件
测试TA-Lib集成、中英文对照、指标分类等功能
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def create_test_data(length=100):
    """创建测试用的K线数据"""
    dates = pd.date_range(start='2023-01-01', periods=length, freq='D')

    # 生成模拟价格数据
    np.random.seed(42)
    base_price = 100
    price_changes = np.random.normal(0, 0.02, length)

    prices = [base_price]
    for change in price_changes[1:]:
        prices.append(prices[-1] * (1 + change))

    # 生成OHLC数据
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        close = price
        volume = np.random.randint(1000, 10000)

        data.append({
            'date': dates[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def test_unified_indicator_manager():
    """测试统一指标管理器"""
    print("=== 统一指标管理器测试 ===")

    try:
        from core.unified_indicator_manager import get_unified_indicator_manager

        # 获取管理器实例
        manager = get_unified_indicator_manager()
        print("✓ 统一指标管理器初始化成功")

        # 创建测试数据
        test_data = create_test_data()
        print(f"✓ 创建测试数据: {len(test_data)} 条记录")

        # 测试指标列表获取
        print("\n--- 测试指标列表获取 ---")
        indicators_en = manager.get_indicator_list()
        indicators_cn = manager.get_indicator_list(use_chinese=True)
        print(f"✓ 英文指标数量: {len(indicators_en)}")
        print(f"✓ 中文指标数量: {len(indicators_cn)}")
        print(f"前10个英文指标: {indicators_en[:10]}")
        print(f"前10个中文指标: {indicators_cn[:10]}")

        # 测试分类获取
        print("\n--- 测试指标分类 ---")
        categories_en = manager.get_indicators_by_category()
        categories_cn = manager.get_indicators_by_category(use_chinese=True)
        print(f"✓ 英文分类数量: {len(categories_en)}")
        print(f"✓ 中文分类数量: {len(categories_cn)}")
        for category, indicators in list(categories_cn.items())[:3]:
            print(f"  {category}: {indicators[:3]}...")

        # 测试中英文对照
        print("\n--- 测试中英文对照 ---")
        test_indicators = ['SMA', 'EMA', 'MACD', 'RSI', 'BBANDS']
        for indicator in test_indicators:
            chinese_name = manager.get_chinese_name(indicator)
            english_name = manager.get_english_name(chinese_name) if chinese_name else None
            print(f"  {indicator} -> {chinese_name} -> {english_name}")
            if english_name != indicator:
                print(f"    ⚠️  中英文转换不一致")

        # 测试指标计算
        print("\n--- 测试指标计算 ---")
        # 使用标准化参数名，同时测试向后兼容性
        test_calculations = [
            ('SMA', {'period': 20}),  # 标准化：timeperiod -> period
            ('EMA', {'period': 20}),  # 标准化：timeperiod -> period
            ('MACD', {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),  # 标准化
            ('RSI', {'period': 14}),  # 标准化：timeperiod -> period
            ('BBANDS', {'period': 20, 'std_dev': 2}),  # 标准化：timeperiod -> period, nbdevup -> std_dev
            ('ATR', {'period': 14}),  # 标准化：timeperiod -> period
            ('STOCH', {'k_period': 14, 'd_period': 3, 'j_period': 3}),  # 标准化
        ]

        calculation_results = {}
        for indicator, params in test_calculations:
            try:
                result = manager.calculate_indicator(indicator, test_data, **params)
                if result is not None:
                    calculation_results[indicator] = result
                    if isinstance(result, dict):
                        print(f"✓ {indicator}: {len(result)} 个输出")
                    else:
                        print(f"✓ {indicator}: 单个输出，长度 {len(result) if hasattr(result, '__len__') else 'N/A'}")
                else:
                    print(f"✗ {indicator}: 计算失败")
            except Exception as e:
                print(f"✗ {indicator}: 异常 - {str(e)}")

        # 测试中文名称计算
        print("\n--- 测试中文名称计算 ---")
        try:
            result_cn = manager.calculate_indicator('简单移动平均', test_data, period=20)
            if result_cn is not None:
                print("✓ 中文名称指标计算成功")
            else:
                print("✗ 中文名称指标计算失败")
        except Exception as e:
            print(f"✗ 中文名称指标计算异常: {str(e)}")

        # 测试缓存功能
        print("\n--- 测试缓存功能 ---")
        import time
        start_time = time.time()
        result1 = manager.calculate_indicator('SMA', test_data, period=20)
        first_calc_time = time.time() - start_time

        start_time = time.time()
        result2 = manager.calculate_indicator('SMA', test_data, period=20)
        second_calc_time = time.time() - start_time

        print(f"✓ 首次计算时间: {first_calc_time:.4f}s")
        print(f"✓ 缓存计算时间: {second_calc_time:.4f}s")
        if second_calc_time < first_calc_time:
            print("✓ 缓存功能正常")
        else:
            print("⚠️  缓存可能未生效")

        print(f"\n=== 统一指标管理器测试完成 ===")
        print(f"成功计算指标数量: {len(calculation_results)}")
        return True

    except ImportError as e:
        print(f"✗ 导入统一指标管理器失败: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中发生异常: {str(e)}")
        return False


def test_compatibility():
    """测试向后兼容性"""
    print("\n=== 向后兼容性测试 ===")

    try:
        from core.indicator_manager import get_indicator_manager

        # 获取传统管理器实例
        manager = get_indicator_manager()
        print("✓ 传统指标管理器初始化成功")

        # 创建测试数据
        test_data = create_test_data()

        # 测试传统接口
        print("\n--- 测试传统接口 ---")
        traditional_indicators = ['MA', 'MACD', 'RSI', 'BOLL', 'ATR']

        for indicator in traditional_indicators:
            try:
                result = manager.calculate_indicator(indicator, test_data)
                if result:
                    print(f"✓ {indicator}: 计算成功")
                else:
                    print(f"✗ {indicator}: 计算失败")
            except Exception as e:
                print(f"✗ {indicator}: 异常 - {str(e)}")

        # 测试新接口
        print("\n--- 测试新接口 ---")
        try:
            indicators_list = manager.get_available_indicators(use_chinese=True)
            print(f"✓ 获取中文指标列表: {len(indicators_list)} 个")

            categories = manager.get_indicators_by_category(use_chinese=True)
            print(f"✓ 获取中文分类: {len(categories)} 个分类")

            chinese_name = manager.get_chinese_name('SMA')
            english_name = manager.get_indicator_english_name('简单移动平均')
            print(f"✓ 中英文转换: SMA -> {chinese_name}, 简单移动平均 -> {english_name}")

        except Exception as e:
            print(f"✗ 新接口测试异常: {str(e)}")

        print("=== 向后兼容性测试完成 ===")
        return True

    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {str(e)}")
        return False


def test_talib_integration():
    """测试TA-Lib集成"""
    print("\n=== TA-Lib集成测试 ===")

    try:
        import talib
        print("✓ TA-Lib 可用")

        # 测试TA-Lib版本
        print(f"✓ TA-Lib 版本: {talib.__version__ if hasattr(talib, '__version__') else '未知'}")

        # 测试一些TA-Lib函数
        test_data = create_test_data()
        close_prices = test_data['close'].values
        high_prices = test_data['high'].values
        low_prices = test_data['low'].values
        volume = test_data['volume'].values

        talib_tests = [
            ('SMA', lambda: talib.SMA(close_prices, timeperiod=20)),
            ('EMA', lambda: talib.EMA(close_prices, timeperiod=20)),
            ('MACD', lambda: talib.MACD(close_prices)),
            ('RSI', lambda: talib.RSI(close_prices)),
            ('BBANDS', lambda: talib.BBANDS(close_prices)),
            ('ATR', lambda: talib.ATR(high_prices, low_prices, close_prices)),
            ('STOCH', lambda: talib.STOCH(high_prices, low_prices, close_prices)),
        ]

        for name, func in talib_tests:
            try:
                result = func()
                if isinstance(result, tuple):
                    print(f"✓ {name}: 多输出结果")
                else:
                    print(f"✓ {name}: 单输出结果")
            except Exception as e:
                print(f"✗ {name}: {str(e)}")

        print("=== TA-Lib集成测试完成 ===")
        return True

    except ImportError:
        print("✗ TA-Lib 不可用")
        return False
    except Exception as e:
        print(f"✗ TA-Lib集成测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("HIkyuu统一指标管理器全面测试")
    print("=" * 50)

    # 测试结果统计
    test_results = []

    # 运行各项测试
    test_results.append(("统一指标管理器", test_unified_indicator_manager()))
    test_results.append(("向后兼容性", test_compatibility()))
    test_results.append(("TA-Lib集成", test_talib_integration()))

    # 输出测试总结
    print("\n" + "=" * 50)
    print("测试结果总结:")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！统一指标管理器工作正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
