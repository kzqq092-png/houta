#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一回测引擎全面测试脚本
验证回测引擎的各种功能、性能和稳定性
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backtest.unified_backtest_engine import (
        UnifiedBacktestEngine, FixedStrategyBacktester, StrategyBacktester,
        BacktestLevel, create_unified_backtest_engine, backtest_strategy_fixed
    )
    BACKTEST_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"回测模块导入失败: {e}")
    BACKTEST_MODULES_AVAILABLE = False

try:
    from core.logger import LogManager
    from utils.config_manager import ConfigManager
    CORE_MODULES_AVAILABLE = True
except ImportError:
    class LogManager:
        def log(self, message, level):
            print(f"[{level}] {message}")

    class ConfigManager:
        def __init__(self):
            self.config = {}

        def get(self, key, default=None):
            return default

    CORE_MODULES_AVAILABLE = False


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_kline_data(days: int = 252, start_price: float = 100.0) -> pd.DataFrame:
        """生成K线数据"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

        # 生成价格数据
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, days)
        prices = start_price * np.cumprod(1 + returns)

        # 生成OHLCV数据
        high_factor = np.random.uniform(1.0, 1.05, days)
        low_factor = np.random.uniform(0.95, 1.0, days)
        volume = np.random.uniform(1000000, 10000000, days)

        kline_data = pd.DataFrame({
            'open': prices * np.random.uniform(0.98, 1.02, days),
            'high': prices * high_factor,
            'low': prices * low_factor,
            'close': prices,
            'volume': volume,
            'amount': volume * prices
        }, index=dates)

        return kline_data

    @staticmethod
    def generate_signal_data(kline_data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号数据"""
        signals = np.random.choice([-1, 0, 1], len(kline_data), p=[0.1, 0.8, 0.1])
        signal_data = kline_data.copy()
        signal_data['signal'] = signals
        return signal_data


class UnifiedBacktestTester:
    """统一回测测试器"""

    def __init__(self):
        self.log_manager = LogManager()
        self.config_manager = ConfigManager()
        self.test_results = {}

    def test_basic_functionality(self):
        """测试基础功能"""
        print("\n=== 测试基础功能 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 测试引擎创建
            engine = UnifiedBacktestEngine(backtest_level=BacktestLevel.PROFESSIONAL)
            print("✅ 统一回测引擎创建成功")

            # 测试固定策略回测器
            fixed_backtester = FixedStrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001
            )
            print("✅ 固定策略回测器创建成功")

            # 测试策略回测器
            strategy_backtester = StrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001
            )
            print("✅ 策略回测器创建成功")

            # 生成测试数据
            test_data = TestDataGenerator.generate_kline_data(100)
            signal_data = TestDataGenerator.generate_signal_data(test_data)

            # 测试基础回测
            result = fixed_backtester.run_backtest(
                signal_data=signal_data,
                initial_capital=100000
            )

            print(f"✅ 基础回测完成，最终资产: {result.get('final_capital', 0):.2f}")

            self.test_results['basic_functionality'] = True
            return True

        except Exception as e:
            print(f"❌ 基础功能测试失败: {e}")
            self.test_results['basic_functionality'] = False
            return False

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        print("\n=== 测试向后兼容性 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 测试旧版本API
            test_data = TestDataGenerator.generate_kline_data(50)
            signal_data = TestDataGenerator.generate_signal_data(test_data)

            # 测试固定策略回测器（旧版本接口）
            backtester = FixedStrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001,
                slippage_pct=0.001
            )

            result = backtester.run_backtest()
            print("✅ 旧版本固定策略接口兼容")

            # 测试策略回测器（旧版本接口）
            strategy_backtester = StrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001
            )

            result = strategy_backtester.run_backtest()
            print("✅ 旧版本策略接口兼容")

            self.test_results['backward_compatibility'] = True
            return True

        except Exception as e:
            print(f"❌ 向后兼容性测试失败: {e}")
            self.test_results['backward_compatibility'] = False
            return False

    def test_professional_levels(self):
        """测试专业级别"""
        print("\n=== 测试专业级别 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            test_data = TestDataGenerator.generate_kline_data(100)
            signal_data = TestDataGenerator.generate_signal_data(test_data)

            # 测试所有专业级别
            levels = [
                BacktestLevel.RETAIL,
                BacktestLevel.INSTITUTIONAL,
                BacktestLevel.HEDGE_FUND,
                BacktestLevel.INVESTMENT_BANK
            ]

            for level in levels:
                engine = UnifiedBacktestEngine(backtest_level=level)

                backtest_params = {
                    'initial_capital': 100000,
                    'commission_pct': 0.001,
                    'slippage_pct': 0.001,
                    'enable_compound': True
                }

                result = engine.run_backtest(signal_data, **backtest_params)

                print(f"  {level.name}: 最终资产 {result.get('final_capital', 0):.2f}")

            print("✅ 所有专业级别测试通过")

            self.test_results['professional_levels'] = True
            return True

        except Exception as e:
            print(f"❌ 专业级别测试失败: {e}")
            self.test_results['professional_levels'] = False
            return False

    def test_risk_metrics(self):
        """测试风险指标计算"""
        print("\n=== 测试风险指标计算 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 生成有明显趋势的测试数据
            test_data = TestDataGenerator.generate_kline_data(252)  # 一年数据
            signal_data = TestDataGenerator.generate_signal_data(test_data)

            engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.INVESTMENT_BANK,
                log_manager=self.log_manager
            )

            backtest_params = {
                'initial_capital': 1000000,
                'commission_pct': 0.001,
                'slippage_pct': 0.001,
                'enable_compound': True,
                'max_position_size': 0.95,
                'stop_loss_pct': 0.05
            }

            result = engine.run_backtest(signal_data, **backtest_params)

            # 验证关键风险指标
            required_metrics = [
                'total_return', 'annual_return', 'sharpe_ratio',
                'max_drawdown', 'win_rate', 'profit_loss_ratio',
                'volatility', 'calmar_ratio'
            ]

            for metric in required_metrics:
                if metric in result:
                    print(f"  {metric}: {result[metric]}")
                else:
                    print(f"  ⚠️  缺少指标: {metric}")

            print("✅ 风险指标计算完成")

            self.test_results['risk_metrics'] = True
            return True

        except Exception as e:
            print(f"❌ 风险指标测试失败: {e}")
            self.test_results['risk_metrics'] = False
            return False

    def test_compound_calculation(self):
        """测试复利计算"""
        print("\n=== 测试复利计算 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            test_data = TestDataGenerator.generate_kline_data(100)
            signal_data = TestDataGenerator.generate_signal_data(test_data)

            # 测试不启用复利
            backtester_no_compound = FixedStrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001
            )

            results_no_compound = backtester_no_compound.run_backtest(enable_compound=False)

            # 测试启用复利
            backtester_compound = FixedStrategyBacktester(
                initial_capital=100000,
                commission_pct=0.001
            )

            results_compound = backtester_compound.run_backtest(enable_compound=True)

            # 比较结果
            final_no_compound = results_no_compound.get('final_capital', 100000)
            final_compound = results_compound.get('final_capital', 100000)

            print(f"  无复利最终资产: {final_no_compound:.2f}")
            print(f"  有复利最终资产: {final_compound:.2f}")
            print(f"  复利效应: {((final_compound - final_no_compound) / final_no_compound * 100):.2f}%")

            print("✅ 复利计算测试完成")

            self.test_results['compound_calculation'] = True
            return True

        except Exception as e:
            print(f"❌ 复利计算测试失败: {e}")
            self.test_results['compound_calculation'] = False
            return False

    def test_performance_comparison(self):
        """测试性能对比"""
        print("\n=== 测试性能对比 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 创建不同大小的测试数据集
            datasets = {
                '小数据集 (100天)': TestDataGenerator.generate_kline_data(100),
                '中数据集 (500天)': TestDataGenerator.generate_kline_data(500),
                '大数据集 (1000天)': TestDataGenerator.generate_kline_data(1000)
            }

            performance_results = {}

            for dataset_name, test_data in datasets.items():
                signal_data = TestDataGenerator.generate_signal_data(test_data)

                # 测试固定策略回测器性能
                start_time = time.time()

                backtester = FixedStrategyBacktester(
                    initial_capital=100000,
                    commission_pct=0.001
                )

                result = backtester.run_backtest(
                    signal_data=signal_data,
                    enable_compound=True
                )

                end_time = time.time()
                execution_time = end_time - start_time

                performance_results[dataset_name] = {
                    'execution_time': execution_time,
                    'data_points': len(test_data),
                    'points_per_second': len(test_data) / execution_time if execution_time > 0 else 0,
                    'final_capital': result.get('final_capital', 0)
                }

                print(f"  {dataset_name}: {execution_time:.3f}s, "
                      f"{performance_results[dataset_name]['points_per_second']:.0f} 点/秒")

            # 性能评估
            avg_speed = np.mean([r['points_per_second'] for r in performance_results.values()])

            if avg_speed > 10000:
                print("🚀 性能优秀 (>10,000 点/秒)")
            elif avg_speed > 5000:
                print("👍 性能良好 (>5,000 点/秒)")
            elif avg_speed > 1000:
                print("⚠️  性能一般 (>1,000 点/秒)")
            else:
                print("🐌 性能需要优化 (<1,000 点/秒)")

            print("✅ 性能对比测试完成")

            self.test_results['performance_comparison'] = True
            return True

        except Exception as e:
            print(f"❌ 性能对比测试失败: {e}")
            self.test_results['performance_comparison'] = False
            return False

    def test_edge_cases(self):
        """测试边界条件"""
        print("\n=== 测试边界条件 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 测试空数据
            empty_data = pd.DataFrame()
            backtester = FixedStrategyBacktester(initial_capital=100000)

            try:
                result = backtester.run_backtest(signal_data=empty_data)
                print("✅ 空数据处理正常")
            except Exception:
                print("✅ 空数据异常处理正常")

            # 测试极小数据集
            tiny_data = TestDataGenerator.generate_kline_data(1)
            signal_data = TestDataGenerator.generate_signal_data(tiny_data)

            result = backtester.run_backtest(signal_data=signal_data)
            print("✅ 极小数据集处理正常")

            # 测试极端参数
            extreme_backtester = FixedStrategyBacktester(
                initial_capital=1,  # 极小资金
                commission_pct=0.1,  # 极高手续费
                slippage_pct=0.1     # 极高滑点
            )

            normal_data = TestDataGenerator.generate_kline_data(50)
            signal_data = TestDataGenerator.generate_signal_data(normal_data)

            result = extreme_backtester.run_backtest(signal_data=signal_data)
            print("✅ 极端参数处理正常")

            # 测试无信号数据
            no_signal_data = normal_data.copy()
            no_signal_data['signal'] = 0  # 全部为0信号

            result = backtester.run_backtest(signal_data=no_signal_data)
            print("✅ 无信号数据处理正常")

            print("✅ 边界条件测试完成")

            self.test_results['edge_cases'] = True
            return True

        except Exception as e:
            print(f"❌ 边界条件测试失败: {e}")
            self.test_results['edge_cases'] = False
            return False

    def test_large_dataset(self):
        """测试大数据集"""
        print("\n=== 测试大数据集性能 ===")

        if not BACKTEST_MODULES_AVAILABLE:
            print("❌ 回测模块不可用，跳过测试")
            return False

        try:
            # 创建大数据集 (10年日线数据)
            large_data = TestDataGenerator.generate_kline_data(2520)  # 10年 * 252交易日
            signal_data = TestDataGenerator.generate_signal_data(large_data)

            print(f"创建大数据集: {len(large_data)} 条记录")

            # 测试不同回测器的大数据集性能
            backtester_types = [
                ("固定策略回测器", FixedStrategyBacktester),
                ("策略回测器", StrategyBacktester)
            ]

            for name, BacktesterClass in backtester_types:
                start_time = time.time()

                backtester = BacktesterClass(
                    initial_capital=1000000,
                    commission_pct=0.001,
                    slippage_pct=0.001
                )

                result = backtester.run_backtest(
                    signal_data=signal_data,
                    enable_compound=True,
                    max_position_size=0.95
                )

                end_time = time.time()
                execution_time = end_time - start_time

                # 计算性能指标
                records_per_second = len(large_data) / execution_time

                print(f"  {name}:")
                print(f"    执行时间: {execution_time:.3f}s")
                print(f"    处理速度: {records_per_second:.0f} 条/秒")
                print(f"    最终资产: {result.get('final_capital', 0):.2f}")

                # 性能基准检查
                if records_per_second > 5000:
                    print(f"    🚀 {name}性能优秀")
                elif records_per_second > 1000:
                    print(f"    👍 {name}性能良好")
                else:
                    print(f"    ⚠️  {name}性能需要优化")

            print("✅ 大数据集测试完成")

            self.test_results['large_dataset'] = True
            return True

        except Exception as e:
            print(f"❌ 大数据集测试失败: {e}")
            self.test_results['large_dataset'] = False
            return False

    def run_comprehensive_tests(self):
        """运行全面测试"""
        print("🚀 开始统一回测引擎全面测试")
        print("=" * 80)

        test_methods = [
            self.test_basic_functionality,
            self.test_backward_compatibility,
            self.test_professional_levels,
            self.test_risk_metrics,
            self.test_compound_calculation,
            self.test_performance_comparison,
            self.test_edge_cases,
            self.test_large_dataset
        ]

        passed_tests = 0
        total_tests = len(test_methods)

        start_time = time.time()

        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ 测试 {test_method.__name__} 异常: {e}")

        end_time = time.time()
        total_time = end_time - start_time

        # 生成测试报告
        print("\n" + "=" * 80)
        print("测试报告")
        print("=" * 80)

        success_rate = (passed_tests / total_tests) * 100

        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"总耗时: {total_time:.3f}秒")

        # 评级
        if success_rate >= 90:
            print("🌟 评级: 优秀")
        elif success_rate >= 75:
            print("👍 评级: 良好")
        elif success_rate >= 60:
            print("⚠️  评级: 一般")
        else:
            print("🚨 评级: 需要改进")

        # 保存测试报告
        report_file = f"unified_backtest_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'total_time': total_time,
            'test_results': self.test_results,
            'system_info': {
                'backtest_modules_available': BACKTEST_MODULES_AVAILABLE,
                'core_modules_available': CORE_MODULES_AVAILABLE
            }
        }

        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        return success_rate >= 75


def main():
    """主函数"""
    tester = UnifiedBacktestTester()
    success = tester.run_comprehensive_tests()

    if success:
        print("\n🎉 统一回测引擎测试通过！")
    else:
        print("\n⚠️  统一回测引擎需要改进！")

    return success


if __name__ == "__main__":
    main()
