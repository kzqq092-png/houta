#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复利计算修复验证测试
"""

from backtest.unified_backtest_engine import FixedStrategyBacktester
import sys
import os
import numpy as np
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_compound_calculation():
    """测试复利计算修复"""
    print("=" * 60)
    print("复利计算修复验证测试")
    print("=" * 60)

    # 创建简单的盈利数据：每次交易都盈利10%
    data = pd.DataFrame({
        'open': [100, 110, 121, 133],
        'high': [101, 111, 122, 134],
        'low': [99, 109, 120, 132],
        'close': [100, 110, 121, 133],
        'volume': [1000000] * 4,
        'signal': [1, -1, 1, -1]  # 买入-卖出-买入-卖出
    }, index=pd.date_range('2023-01-01', periods=4, freq='D'))

    print("测试数据:")
    print(f"价格序列: {data['close'].tolist()}")
    print(f"信号序列: {data['signal'].tolist()}")
    print(f"预期每次交易盈利约10%")

    # 测试不启用复利
    print("\n--- 不启用复利 ---")
    backtester_no_compound = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        position_size=0.9,  # 90%仓位
        commission_pct=0.001,
        slippage_pct=0.001
    )
    results_no_compound = backtester_no_compound.run_backtest(enable_compound=False)

    print("交易记录:")
    trades_no_compound = backtester_no_compound.get_trade_summary()
    for i, trade in trades_no_compound.iterrows():
        if 'profit' in trade:
            print(f"  交易{i+1}: 收益 {trade['profit']:.2f}")

    final_capital_no_compound = results_no_compound['capital'].iloc[-1]
    print(f"最终资金: {final_capital_no_compound:.2f}")

    # 测试启用复利
    print("\n--- 启用复利 ---")
    backtester_compound = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        position_size=0.9,  # 90%仓位
        commission_pct=0.001,
        slippage_pct=0.001
    )
    results_compound = backtester_compound.run_backtest(enable_compound=True)

    print("交易记录:")
    trades_compound = backtester_compound.get_trade_summary()
    for i, trade in trades_compound.iterrows():
        if 'profit' in trade:
            print(f"  交易{i+1}: 收益 {trade['profit']:.2f}")

    final_capital_compound = results_compound['capital'].iloc[-1]
    print(f"最终资金: {final_capital_compound:.2f}")

    # 分析结果
    print("\n--- 结果分析 ---")
    print(f"不启用复利最终资金: {final_capital_no_compound:.2f}")
    print(f"启用复利最终资金: {final_capital_compound:.2f}")
    print(f"复利效应差异: {final_capital_compound - final_capital_no_compound:.2f}")

    # 验证复利效果
    if final_capital_compound > final_capital_no_compound:
        print("✅ 复利计算修复成功")
        return True
    else:
        print("❌ 复利计算仍有问题")
        return False


if __name__ == "__main__":
    test_compound_calculation()
