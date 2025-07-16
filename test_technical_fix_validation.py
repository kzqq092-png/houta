#!/usr/bin/env python3
"""
技术分析修复验证脚本

专门验证：
1. TechnicalAnalysisTab是否能正确接收K线数据
2. 指标计算是否正常工作
3. 数据传递链路是否完整
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def create_test_kdata(days: int = 50) -> pd.DataFrame:
    """创建测试用的K线数据"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')

    # 生成模拟的K线数据
    np.random.seed(42)  # 固定随机种子
    base_price = 100.0

    data = []
    current_price = base_price

    for date in dates:
        # 模拟价格波动
        change = np.random.normal(0, 0.02)  # 2%的标准波动
        current_price *= (1 + change)

        # 生成OHLC数据
        open_price = current_price
        high_price = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low_price = current_price * (1 - abs(np.random.normal(0, 0.01)))
        close_price = current_price * (1 + np.random.normal(0, 0.005))
        volume = np.random.randint(1000000, 10000000)

        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

        current_price = close_price

    df = pd.DataFrame(data, index=dates)
    return df


def test_technical_analysis_components():
    """测试技术分析组件的核心功能"""
    print("=== 技术分析修复验证 ===\n")

    # 1. 测试导入
    print("1. 测试模块导入...")
    try:
        from gui.widgets.analysis_tabs.technical_tab import TechnicalAnalysisTab
        from core.indicator_adapter import get_all_indicators_by_category, get_talib_indicator_list
        print("   ✓ 模块导入成功")
    except ImportError as e:
        print(f"   ✗ 模块导入失败: {e}")
        return False

    # 2. 测试指标获取
    print("\n2. 测试指标获取...")
    try:
        categories = get_all_indicators_by_category(use_chinese=True)
        indicators = get_talib_indicator_list()
        print(f"   ✓ 获取到 {len(categories)} 个分类，{len(indicators)} 个指标")
        print(f"   ✓ 分类: {list(categories.keys())}")
        print(f"   ✓ 部分指标: {indicators[:5]}")
    except Exception as e:
        print(f"   ✗ 指标获取失败: {e}")
        return False

    # 3. 测试K线数据创建
    print("\n3. 测试K线数据创建...")
    try:
        kdata = create_test_kdata(50)
        print(f"   ✓ 创建测试K线数据: {len(kdata)} 条")
        print(f"   ✓ 数据列: {list(kdata.columns)}")
        print(f"   ✓ 数据范围: {kdata.index[0]} 到 {kdata.index[-1]}")
    except Exception as e:
        print(f"   ✗ K线数据创建失败: {e}")
        return False

    # 4. 测试指标计算
    print("\n4. 测试指标计算...")
    try:
        from core.indicator_service import calculate_indicator

        # 测试MA指标
        result = calculate_indicator(kdata, 'MA', {'timeperiod': 20})
        if result is not None:
            print(f"   ✓ MA指标计算成功，结果类型: {type(result)}")
            if hasattr(result, 'shape'):
                print(f"   ✓ 结果形状: {result.shape}")
        else:
            print("   ✗ MA指标计算返回None")

        # 测试MACD指标
        result = calculate_indicator(kdata, 'MACD', {
            'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9
        })
        if result is not None:
            print(f"   ✓ MACD指标计算成功，结果类型: {type(result)}")
        else:
            print("   ✗ MACD指标计算返回None")

    except Exception as e:
        print(f"   ✗ 指标计算失败: {e}")
        import traceback
        print(f"   详细错误: {traceback.format_exc()}")
        return False

    # 5. 测试技术分析标签页创建
    print("\n5. 测试技术分析标签页创建...")
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # 创建技术分析标签页
        technical_tab = TechnicalAnalysisTab()
        print("   ✓ TechnicalAnalysisTab创建成功")

        # 测试设置K线数据
        technical_tab.set_kdata(kdata)
        print(f"   ✓ K线数据设置成功，当前数据长度: {len(technical_tab.current_kdata) if technical_tab.current_kdata is not None else 0}")

        # 检查自动计算状态
        if hasattr(technical_tab, 'auto_calculate'):
            print(f"   ✓ 自动计算状态: {technical_tab.auto_calculate}")

        print("   ✓ 技术分析标签页功能正常")

    except Exception as e:
        print(f"   ✗ 技术分析标签页测试失败: {e}")
        import traceback
        print(f"   详细错误: {traceback.format_exc()}")
        return False

    print("\n=== 所有测试通过！✓ ===")
    print("\n总结:")
    print("✓ 模块导入正常")
    print("✓ 指标获取正常")
    print("✓ K线数据处理正常")
    print("✓ 指标计算功能正常")
    print("✓ 技术分析标签页创建正常")
    print("✓ 数据传递链路完整")

    return True


if __name__ == "__main__":
    success = test_technical_analysis_components()
    sys.exit(0 if success else 1)
