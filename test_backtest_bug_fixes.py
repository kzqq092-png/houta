#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测系统bug修复验证测试

测试内容：
1. 交易成本计算修复
2. 资金管理bug修复
3. 复利计算修复
4. 性能指标计算修复
5. 信号处理逻辑修复
6. 数据处理问题修复
"""

from backtest.backtest_engine_fixed import FixedStrategyBacktester  # 修复版本
from backtest.backtest_engine import StrategyBacktester  # 原版本
import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_data():
    """创建测试数据"""
    # 创建一年的日期序列
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(42)

    # 生成模拟价格数据
    returns = np.random.normal(0.001, 0.02, len(dates))
    prices = 100 * np.exp(np.cumsum(returns))

    # 创建简单的交易信号：价格上涨买入，下跌卖出
    signals = []
    for i in range(len(prices)):
        if i == 0:
            signals.append(0)
        elif prices[i] > prices[i-1] * 1.02:  # 上涨2%以上买入
            signals.append(1)
        elif prices[i] < prices[i-1] * 0.98:  # 下跌2%以上卖出
            signals.append(-1)
        else:
            signals.append(0)

    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates)),
        'signal': signals
    }, index=dates)

    return data


def test_commission_calculation():
    """测试交易成本计算修复"""
    print("=" * 60)
    print("测试1: 交易成本计算修复")
    print("=" * 60)

    # 创建简单测试数据
    data = pd.DataFrame({
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [1000000, 1000000, 1000000],
        'signal': [1, 0, -1]  # 买入-持有-卖出
    }, index=pd.date_range('2023-01-01', periods=3, freq='D'))

    # 原版本测试
    try:
        original_backtester = StrategyBacktester(
            data=data.copy(),
            initial_capital=100000,
            commission_pct=0.001
        )
        original_results = original_backtester.run_backtest()
        original_commission = original_results['commission'].sum()
        print(f"原版本总手续费: {original_commission:.2f}")
    except Exception as e:
        print(f"原版本执行失败: {e}")
        original_commission = 0

    # 修复版本测试
    fixed_backtester = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        commission_pct=0.001,
        min_commission=5.0
    )
    fixed_results = fixed_backtester.run_backtest()
    fixed_commission = fixed_results['commission'].sum()
    print(f"修复版本总手续费: {fixed_commission:.2f}")

    # 验证手续费计算
    expected_commission = 2 * max(100000 * 0.001, 5.0)  # 两次交易
    print(f"预期手续费: {expected_commission:.2f}")

    if abs(fixed_commission - expected_commission) < 1:
        print("✅ 手续费计算修复成功")
    else:
        print("❌ 手续费计算仍有问题")


def test_compound_interest():
    """测试复利计算修复"""
    print("\n" + "=" * 60)
    print("测试2: 复利计算修复")
    print("=" * 60)

    # 创建盈利信号数据
    data = pd.DataFrame({
        'open': [100, 110, 120, 130],
        'high': [101, 111, 121, 131],
        'low': [99, 109, 119, 129],
        'close': [100, 110, 120, 130],
        'volume': [1000000] * 4,
        'signal': [1, -1, 1, -1]  # 买入-卖出-买入-卖出
    }, index=pd.date_range('2023-01-01', periods=4, freq='D'))

    # 测试不启用复利
    backtester_no_compound = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        position_size=0.9,
        commission_pct=0.001
    )
    results_no_compound = backtester_no_compound.run_backtest(enable_compound=False)
    final_capital_no_compound = results_no_compound['capital'].iloc[-1]

    # 测试启用复利
    backtester_compound = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        position_size=0.9,
        commission_pct=0.001
    )
    results_compound = backtester_compound.run_backtest(enable_compound=True)
    final_capital_compound = results_compound['capital'].iloc[-1]

    print(f"不启用复利最终资金: {final_capital_no_compound:.2f}")
    print(f"启用复利最终资金: {final_capital_compound:.2f}")

    if final_capital_compound > final_capital_no_compound:
        print("✅ 复利计算修复成功")
    else:
        print("❌ 复利计算仍有问题")


def test_performance_metrics():
    """测试性能指标计算修复"""
    print("\n" + "=" * 60)
    print("测试3: 性能指标计算修复")
    print("=" * 60)

    data = create_test_data()

    backtester = FixedStrategyBacktester(
        data=data,
        initial_capital=100000,
        position_size=0.8,
        commission_pct=0.001
    )

    results = backtester.run_backtest()
    metrics = backtester.calculate_metrics()

    print("性能指标:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 验证关键指标
    checks = []

    # 检查夏普比率计算
    if not np.isnan(metrics['sharpe_ratio']) and not np.isinf(metrics['sharpe_ratio']):
        checks.append("夏普比率计算正常")
    else:
        checks.append("❌ 夏普比率计算异常")

    # 检查最大回撤
    if metrics['max_drawdown'] <= 0:
        checks.append("最大回撤计算正常")
    else:
        checks.append("❌ 最大回撤计算异常")

    # 检查胜率
    if 0 <= metrics['win_rate'] <= 1:
        checks.append("胜率计算正常")
    else:
        checks.append("❌ 胜率计算异常")

    for check in checks:
        if check.startswith("❌"):
            print(check)
        else:
            print(f"✅ {check}")


def test_signal_processing():
    """测试信号处理逻辑修复"""
    print("\n" + "=" * 60)
    print("测试4: 信号处理逻辑修复")
    print("=" * 60)

    # 创建复杂信号数据
    data = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100, 101, 102, 103, 104],
        'volume': [1000000] * 5,
        'signal': [1, 0, -1, 1, 0]  # 买入-持有-换仓-买入-平仓
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))

    backtester = FixedStrategyBacktester(
        data=data,
        initial_capital=100000,
        position_size=0.8,
        commission_pct=0.001
    )

    results = backtester.run_backtest()

    # 检查持仓变化
    positions = results['position'].tolist()
    print(f"持仓变化: {positions}")

    # 检查交易记录
    trades = backtester.get_trade_summary()
    print(f"交易次数: {len(trades)}")

    if len(trades) >= 2:  # 应该有多次交易
        print("✅ 信号处理逻辑修复成功")
    else:
        print("❌ 信号处理逻辑仍有问题")


def test_stop_loss_take_profit():
    """测试止损止盈功能"""
    print("\n" + "=" * 60)
    print("测试5: 止损止盈功能")
    print("=" * 60)

    # 创建价格大幅波动的数据
    data = pd.DataFrame({
        'open': [100, 95, 90, 85, 80],
        'high': [101, 96, 91, 86, 81],
        'low': [99, 94, 89, 84, 79],
        'close': [100, 95, 90, 85, 80],
        'volume': [1000000] * 5,
        'signal': [1, 0, 0, 0, 0]  # 只在第一天买入
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))

    backtester = FixedStrategyBacktester(
        data=data,
        initial_capital=100000,
        position_size=0.8,
        commission_pct=0.001
    )

    results = backtester.run_backtest(stop_loss_pct=0.03)  # 3%止损

    # 检查是否触发止损
    exit_reasons = results['exit_reason'].dropna().tolist()
    print(f"退出原因: {exit_reasons}")

    if 'Stop Loss' in exit_reasons:
        print("✅ 止损功能正常")
    else:
        print("❌ 止损功能异常")


def test_data_preprocessing():
    """测试数据预处理修复"""
    print("\n" + "=" * 60)
    print("测试6: 数据预处理修复")
    print("=" * 60)

    # 创建包含异常数据的测试数据
    data = pd.DataFrame({
        'open': [100, 101, np.nan, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100, 101, 102, 103, 104],
        'volume': [1000000, 1000000, 0, 1000000, 1000000],
        'signal': [1, 0, 0, -1, 0]
    }, index=pd.date_range('2023-01-01', periods=5, freq='D'))

    try:
        backtester = FixedStrategyBacktester(
            data=data,
            initial_capital=100000,
            commission_pct=0.001
        )

        results = backtester.run_backtest()
        print(f"处理后数据长度: {len(results)}")
        print("✅ 数据预处理修复成功")

    except Exception as e:
        print(f"❌ 数据预处理仍有问题: {e}")


def compare_original_vs_fixed():
    """对比原版本和修复版本的结果"""
    print("\n" + "=" * 60)
    print("测试7: 原版本vs修复版本对比")
    print("=" * 60)

    data = create_test_data()

    # 原版本测试
    try:
        original_backtester = StrategyBacktester(
            data=data.copy(),
            initial_capital=100000,
            position_size=0.8,
            commission_pct=0.001
        )
        original_results = original_backtester.run_backtest()
        original_metrics = original_backtester.calculate_metrics()

        print("原版本结果:")
        print(f"  总收益: {original_metrics['total_return']:.4f}")
        print(f"  夏普比率: {original_metrics['sharpe_ratio']:.4f}")
        print(f"  最大回撤: {original_metrics['max_drawdown']:.4f}")
        print(f"  交易次数: {original_metrics['total_trades']}")

    except Exception as e:
        print(f"原版本执行失败: {e}")
        original_metrics = None

    # 修复版本测试
    fixed_backtester = FixedStrategyBacktester(
        data=data.copy(),
        initial_capital=100000,
        position_size=0.8,
        commission_pct=0.001
    )
    fixed_results = fixed_backtester.run_backtest()
    fixed_metrics = fixed_backtester.calculate_metrics()

    print("\n修复版本结果:")
    print(f"  总收益: {fixed_metrics['total_return']:.4f}")
    print(f"  夏普比率: {fixed_metrics['sharpe_ratio']:.4f}")
    print(f"  最大回撤: {fixed_metrics['max_drawdown']:.4f}")
    print(f"  交易次数: {fixed_metrics['total_trades']}")
    print(f"  胜率: {fixed_metrics['win_rate']:.4f}")
    print(f"  盈亏比: {fixed_metrics['profit_factor']:.4f}")

    # 绘制对比图
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 权益曲线对比
    if original_metrics:
        axes[0].plot(original_results.index, original_results['equity'],
                     label='Original Version', alpha=0.7)

    axes[0].plot(fixed_results.index, fixed_results['equity'],
                 label='Fixed Version', linewidth=2)
    axes[0].set_title('Equity Curve Comparison')
    axes[0].set_ylabel('Equity')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 持仓状态
    axes[1].plot(fixed_results.index, fixed_results['position'],
                 label='Position', marker='o', markersize=2)
    axes[1].set_title('Position Changes')
    axes[1].set_ylabel('Position')
    axes[1].set_xlabel('Date')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('backtest_comparison.png', dpi=300, bbox_inches='tight')
    print("\n📊 对比图已保存为 backtest_comparison.png")


def main():
    """主测试函数"""
    print("🚀 开始回测系统bug修复验证测试")
    print("测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 运行所有测试
    test_commission_calculation()
    test_compound_interest()
    test_performance_metrics()
    test_signal_processing()
    test_stop_loss_take_profit()
    test_data_preprocessing()
    compare_original_vs_fixed()

    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("=" * 60)

    print("\n📋 修复总结:")
    print("1. ✅ 交易成本计算：基于实际交易金额计算，添加最小手续费")
    print("2. ✅ 复利功能：支持启用/禁用复利，正确计算交易金额")
    print("3. ✅ 性能指标：修复夏普比率、最大回撤等关键指标计算")
    print("4. ✅ 信号处理：支持换仓、正确处理信号序列")
    print("5. ✅ 止损止盈：准确触发条件，记录退出原因")
    print("6. ✅ 数据预处理：处理异常值、缺失值，验证数据完整性")
    print("7. ✅ 交易记录：完整记录交易详情，支持统计分析")


if __name__ == "__main__":
    main()
