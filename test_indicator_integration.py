"""
指标系统集成测试
验证新的指标计算架构是否正常工作
"""

import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath('.'))


def create_test_data() -> pd.DataFrame:
    """创建测试用的K线数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    # 创建模拟K线数据
    base_price = 100
    data = []

    for i in range(len(dates)):
        # 模拟价格变动
        change = np.random.normal(0, 0.02)  # 2%的日波动
        base_price *= (1 + change)

        # 生成OHLC数据
        open_price = base_price
        high_price = open_price * (1 + abs(np.random.normal(0, 0.01)))
        low_price = open_price * (1 - abs(np.random.normal(0, 0.01)))
        close_price = low_price + (high_price - low_price) * np.random.random()
        volume = int(np.random.uniform(1000000, 5000000))

        data.append({
            'date': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df


def test_indicator_service():
    """测试指标计算服务"""
    print("=== 测试指标计算服务 ===")

    try:
        from core.services.indicator_service import get_indicator_service

        # 获取服务实例
        service = get_indicator_service()
        print("✓ 指标计算服务初始化成功")

        # 创建测试数据
        test_data = create_test_data()
        print(f"✓ 创建测试数据: {len(test_data)} 条记录")

        # 测试支持的指标
        supported_indicators = service.get_supported_indicators()
        print(f"✓ 支持的指标数量: {len(supported_indicators)}")
        print(f"前10个支持的指标: {supported_indicators[:10]}")

        # 测试单个指标计算
        print("\n--- 测试单个指标计算 ---")
        test_indicators = ['MA', 'EMA', 'MACD', 'RSI']

        for indicator in test_indicators:
            try:
                response = service.calculate_indicator(
                    indicator_name=indicator,
                    data=test_data,
                    period=20
                )

                if response.success:
                    print(f"✓ {indicator} 计算成功, 耗时: {response.computation_time:.4f}s")
                    if isinstance(response.result, dict):
                        print(f"  返回序列: {list(response.result.keys())}")
                    else:
                        print(f"  返回类型: {type(response.result).__name__}")
                else:
                    print(f"✗ {indicator} 计算失败: {response.error_message}")

            except Exception as e:
                print(f"✗ {indicator} 计算异常: {e}")

        return True

    except Exception as e:
        print(f"✗ 指标计算服务测试失败: {e}")
        return False


def test_ui_adapter():
    """测试UI适配器"""
    print("\n=== 测试UI适配器 ===")

    try:
        from core.services.indicator_ui_adapter import get_indicator_ui_adapter

        # 获取适配器实例
        adapter = get_indicator_ui_adapter()
        print("✓ UI适配器初始化成功")

        # 创建测试数据
        test_data = create_test_data()

        # 测试指标列表获取
        print("\n--- 测试指标列表获取 ---")
        indicators_en = adapter.get_indicator_list()
        indicators_cn = adapter.get_indicator_list(use_chinese=True)
        print(f"✓ 英文指标数量: {len(indicators_en)}")
        print(f"✓ 中文指标数量: {len(indicators_cn)}")

        # 测试指标分类
        print("\n--- 测试指标分类 ---")
        categories = adapter.get_indicators_by_category(use_chinese=True)
        print(f"✓ 指标分类数量: {len(categories)}")
        for category, indicators in list(categories.items())[:3]:
            print(f"  {category}: {indicators[:3]}...")

        # 测试UI格式的指标计算
        print("\n--- 测试UI格式指标计算 ---")
        test_indicators = [
            {'name': 'MA', 'params': {'period': 20}},
            {'name': 'MACD', 'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}},
            {'name': 'RSI', 'params': {'period': 14}}
        ]

        for indicator_config in test_indicators:
            try:
                result = adapter.calculate_indicator_for_ui(
                    indicator_name=indicator_config['name'],
                    kdata=test_data,
                    **indicator_config['params']
                )

                if result and result.get('success', False):
                    print(f"✓ {indicator_config['name']} UI计算成功")
                    print(f"  类型: {result.get('type', 'unknown')}")
                    print(f"  数据键: {list(result.get('data', {}).keys())}")
                else:
                    print(f"✗ {indicator_config['name']} UI计算失败")

            except Exception as e:
                print(f"✗ {indicator_config['name']} UI计算异常: {e}")

        # 测试批量计算
        print("\n--- 测试批量计算 ---")
        batch_results = adapter.batch_calculate_indicators(test_indicators, test_data)
        print(f"✓ 批量计算完成，成功计算: {len(batch_results)} 个指标")

        return True

    except Exception as e:
        print(f"✗ UI适配器测试失败: {e}")
        return False


def test_engines():
    """测试计算引擎"""
    print("\n=== 测试计算引擎 ===")

    try:
        from core.services.indicator_service import IndicatorRequest

        # 创建测试数据
        test_data = create_test_data()

        # 测试统一引擎
        print("\n--- 测试统一引擎 ---")
        try:
            from core.services.engines.unified_engine import UnifiedIndicatorEngine

            engine = UnifiedIndicatorEngine()
            print("✓ 统一引擎初始化成功")

            # 测试支持的指标
            supported = engine.get_supported_indicators()
            print(f"✓ 统一引擎支持指标: {len(supported)} 个")

            # 测试计算
            request = IndicatorRequest(
                indicator_name='MA',
                data=test_data,
                parameters={'period': 20}
            )

            response = engine.calculate(request)
            if response.success:
                print("✓ 统一引擎计算测试成功")
            else:
                print(f"✗ 统一引擎计算失败: {response.error_message}")

        except Exception as e:
            print(f"✗ 统一引擎测试失败: {e}")

        # 测试备用引擎
        print("\n--- 测试备用引擎 ---")
        try:
            from core.services.engines.fallback_engine import FallbackEngine

            engine = FallbackEngine()
            print("✓ 备用引擎初始化成功")

            # 测试支持的指标
            supported = engine.get_supported_indicators()
            print(f"✓ 备用引擎支持指标: {len(supported)} 个")

            # 测试计算
            request = IndicatorRequest(
                indicator_name='MA',
                data=test_data,
                parameters={'period': 20}
            )

            response = engine.calculate(request)
            if response.success:
                print("✓ 备用引擎计算测试成功")
            else:
                print(f"✗ 备用引擎计算失败: {response.error_message}")

        except Exception as e:
            print(f"✗ 备用引擎测试失败: {e}")

        return True

    except Exception as e:
        print(f"✗ 计算引擎测试失败: {e}")
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")

    try:
        # 测试旧的指标管理器接口
        print("\n--- 测试兼容层指标管理器 ---")
        from core.indicator_manager import get_indicator_manager

        manager = get_indicator_manager()
        print("✓ 兼容层指标管理器初始化成功")

        # 测试旧接口
        test_data = create_test_data()

        # 测试calc_*方法
        try:
            ma_result = manager.calc_ma(test_data, period=20)
            print(f"✓ calc_ma 方法正常工作, 结果长度: {len(ma_result)}")
        except Exception as e:
            print(f"✗ calc_ma 方法失败: {e}")

        try:
            ema_result = manager.calc_ema(test_data, period=20)
            print(f"✓ calc_ema 方法正常工作, 结果长度: {len(ema_result)}")
        except Exception as e:
            print(f"✗ calc_ema 方法失败: {e}")

        # 测试统一指标管理器的便捷函数
        print("\n--- 测试统一指标管理器便捷函数 ---")
        from core.unified_indicator_manager import (
            get_indicator_list, get_indicators_by_category,
            calculate_indicator, get_indicator_chinese_name
        )

        # 测试列表获取
        indicators = get_indicator_list()
        print(f"✓ get_indicator_list 正常工作, 指标数量: {len(indicators)}")

        # 测试分类获取
        categories = get_indicators_by_category(use_chinese=True)
        print(f"✓ get_indicators_by_category 正常工作, 分类数量: {len(categories)}")

        # 测试中文名称获取
        chinese_name = get_indicator_chinese_name('MA')
        print(f"✓ get_indicator_chinese_name 正常工作: MA -> {chinese_name}")

        # 测试计算
        try:
            result = calculate_indicator('MA', test_data, period=20)
            print(f"✓ calculate_indicator 正常工作, 结果类型: {type(result).__name__}")
        except Exception as e:
            print(f"✗ calculate_indicator 失败: {e}")

        return True

    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始指标系统集成测试...")
    print("=" * 50)

    test_results = []

    # 执行各项测试
    test_results.append(("指标计算服务", test_indicator_service()))
    test_results.append(("UI适配器", test_ui_adapter()))
    test_results.append(("计算引擎", test_engines()))
    test_results.append(("向后兼容性", test_backward_compatibility()))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！指标系统集成成功！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    main()
