"""
测试兼容层功能
验证indicator_manager.py和indicators_algo.py兼容层是否正常工作
"""

import pandas as pd
import numpy as np
import warnings


def create_test_data(days=100):
    """创建测试数据"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=days, freq='D')

    # 生成OHLCV数据
    close_prices = 100 + np.cumsum(np.random.randn(days) * 0.5)
    high_prices = close_prices + np.random.uniform(0.5, 2.0, days)
    low_prices = close_prices - np.random.uniform(0.5, 2.0, days)
    open_prices = close_prices + np.random.randn(days) * 0.3
    volume = np.random.randint(1000000, 10000000, days)

    return pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    }, index=dates)


def test_indicator_manager_compatibility():
    """测试indicator_manager兼容层"""
    print("=== 测试 indicator_manager 兼容层 ===")

    try:
        # 导入兼容层
        from core.indicator_manager import get_indicator_manager, get_indicator_categories

        # 获取管理器实例
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = get_indicator_manager()

        print("✓ indicator_manager 导入成功")

        # 测试指标列表获取
        indicators = manager.get_indicator_list()
        print(f"✓ 获取指标列表成功，共 {len(indicators)} 个指标")

        # 测试分类获取
        categories = manager.get_indicators_by_category()
        print(f"✓ 获取指标分类成功，共 {len(categories)} 个分类")

        # 测试中英文名称转换
        chinese_name = manager.get_chinese_name('MA')
        english_name = manager.get_english_name(chinese_name) if chinese_name else None
        print(f"✓ 中英文转换测试：MA -> {chinese_name} -> {english_name}")

        # 创建测试数据
        test_data = create_test_data()

        # 测试指标计算
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # 测试MA计算
            ma_result = manager.calc_ma(test_data, period=20)
            print(f"✓ MA计算成功，结果类型: {type(ma_result)}")

            # 测试EMA计算
            ema_result = manager.calc_ema(test_data, period=20)
            print(f"✓ EMA计算成功，结果类型: {type(ema_result)}")

            # 测试MACD计算
            macd_result = manager.calc_macd(test_data)
            print(f"✓ MACD计算成功，结果类型: {type(macd_result)}")

            # 测试RSI计算
            rsi_result = manager.calc_rsi(test_data, period=14)
            print(f"✓ RSI计算成功，结果类型: {type(rsi_result)}")

        print("✅ indicator_manager 兼容层测试全部通过\n")
        return True

    except Exception as e:
        print(f"❌ indicator_manager 兼容层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_indicators_algo_compatibility():
    """测试indicators_algo兼容层"""
    print("=== 测试 indicators_algo 兼容层 ===")

    try:
        # 导入兼容层
        from core.indicators_algo import (
            TechnicalIndicators, get_technical_indicators,
            calculate_sma, calculate_ema, calculate_macd, calculate_rsi
        )

        print("✓ indicators_algo 导入成功")

        # 获取技术指标实例
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            tech_indicators = get_technical_indicators()

        # 创建测试数据
        test_data = create_test_data()
        close_data = test_data['close']

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # 测试SMA计算
            sma_result = tech_indicators.sma(close_data, period=20)
            print(f"✓ SMA计算成功，结果类型: {type(sma_result)}")

            # 测试EMA计算
            ema_result = tech_indicators.ema(close_data, period=20)
            print(f"✓ EMA计算成功，结果类型: {type(ema_result)}")

            # 测试MACD计算
            macd_result = tech_indicators.macd(close_data)
            print(f"✓ MACD计算成功，结果类型: {type(macd_result)}")

            # 测试RSI计算
            rsi_result = tech_indicators.rsi(close_data, period=14)
            print(f"✓ RSI计算成功，结果类型: {type(rsi_result)}")

            # 测试便捷函数
            sma_func_result = calculate_sma(close_data, period=20)
            print(f"✓ calculate_sma便捷函数成功，结果类型: {type(sma_func_result)}")

        print("✅ indicators_algo 兼容层测试全部通过\n")
        return True

    except Exception as e:
        print(f"❌ indicators_algo 兼容层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有兼容层测试"""
    print("=== HIkyuu 指标兼容层测试 ===\n")

    success_count = 0
    total_tests = 2

    # 测试indicator_manager兼容层
    if test_indicator_manager_compatibility():
        success_count += 1

    # 测试indicators_algo兼容层
    if test_indicators_algo_compatibility():
        success_count += 1

    # 输出测试结果
    print("=== 测试结果汇总 ===")
    print(f"✅ 成功: {success_count}/{total_tests}")
    print(f"❌ 失败: {total_tests - success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n🎉 所有兼容层测试全部通过！")
        print("现在可以安全地导入这些模块而不会出现导入错误。")
    else:
        print(f"\n⚠️  有 {total_tests - success_count} 个兼容层测试失败，需要进一步修复。")

    return success_count == total_tests


if __name__ == "__main__":
    main()
