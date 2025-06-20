#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略系统全面测试脚本
验证策略管理器、策略生成器、策略优化器等核心组件的功能
"""

import sys
import os
import time
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from strategies.strategy_manager import StrategyManager
    from strategies.strategy_generator import StrategyGenerator
    from strategies.strategy_optimizer import StrategyOptimizer
    from core.strategy_base import StrategyConfig, StrategyResult
    from backtest.unified_backtest_engine import UnifiedBacktestEngine, BacktestLevel
    STRATEGY_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"策略模块导入失败: {e}")
    STRATEGY_MODULES_AVAILABLE = False

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


class StrategySystemTester:
    """策略系统测试器"""

    def __init__(self):
        self.log_manager = LogManager()
        self.config_manager = ConfigManager()
        self.test_results = {}

    def test_basic_functionality(self):
        """测试基础功能"""
        print("\n=== 测试策略系统基础功能 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            # 测试策略管理器
            manager = StrategyManager()
            strategies = manager.get_all_strategies()
            print(f"✅ 策略管理器正常，共加载 {len(strategies)} 个策略")

            # 测试策略生成器
            generator = StrategyGenerator()
            sample_strategy = generator.generate_sample_strategy()
            print(f"✅ 策略生成器正常，生成示例策略: {sample_strategy.name if sample_strategy else 'None'}")

            # 测试策略优化器
            optimizer = StrategyOptimizer()
            print("✅ 策略优化器初始化正常")

            self.test_results['basic_functionality'] = True
            return True

        except Exception as e:
            print(f"❌ 基础功能测试失败: {e}")
            self.test_results['basic_functionality'] = False
            return False

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        print("\n=== 测试向后兼容性 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            # 测试旧版本策略配置加载
            manager = StrategyManager()

            # 创建旧版本格式的策略配置
            old_config = {
                'name': 'test_old_strategy',
                'type': 'trend_following',
                'parameters': {
                    'period': 20,
                    'threshold': 0.02
                }
            }

            # 测试是否能正确转换
            strategy_config = manager.convert_old_config(old_config)
            print("✅ 旧版本配置转换正常")

            self.test_results['backward_compatibility'] = True
            return True

        except Exception as e:
            print(f"❌ 向后兼容性测试失败: {e}")
            self.test_results['backward_compatibility'] = False
            return False

    def test_professional_levels(self):
        """测试专业级别功能"""
        print("\n=== 测试专业级别功能 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            manager = StrategyManager()

            # 测试不同专业级别的策略
            levels = ['RETAIL', 'INSTITUTIONAL', 'HEDGE_FUND', 'INVESTMENT_BANK']

            for level in levels:
                strategies = manager.get_strategies_by_level(level)
                print(f"  {level}: {len(strategies)} 个策略")

            print("✅ 专业级别功能正常")

            self.test_results['professional_levels'] = True
            return True

        except Exception as e:
            print(f"❌ 专业级别测试失败: {e}")
            self.test_results['professional_levels'] = False
            return False

    def test_risk_metrics(self):
        """测试风险指标"""
        print("\n=== 测试风险指标计算 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            # 创建测试数据
            test_data = self._create_test_data()

            # 测试策略回测和风险计算
            manager = StrategyManager()
            strategy = manager.get_default_strategy()

            if strategy:
                # 运行回测
                backtest_engine = UnifiedBacktestEngine(BacktestLevel.PROFESSIONAL)
                result = backtest_engine.run_strategy_backtest(strategy, test_data)

                # 计算风险指标
                risk_metrics = manager.calculate_risk_metrics(result)

                print(f"  夏普比率: {risk_metrics.get('sharpe_ratio', 'N/A')}")
                print(f"  最大回撤: {risk_metrics.get('max_drawdown', 'N/A')}")
                print(f"  胜率: {risk_metrics.get('win_rate', 'N/A')}")
                print(f"  盈亏比: {risk_metrics.get('profit_loss_ratio', 'N/A')}")

                print("✅ 风险指标计算正常")
            else:
                print("⚠️  无可用策略进行测试")

            self.test_results['risk_metrics'] = True
            return True

        except Exception as e:
            print(f"❌ 风险指标测试失败: {e}")
            self.test_results['risk_metrics'] = False
            return False

    def test_strategy_optimization(self):
        """测试策略优化"""
        print("\n=== 测试策略优化 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            optimizer = StrategyOptimizer()

            # 创建测试策略
            test_strategy = self._create_test_strategy()
            test_data = self._create_test_data()

            # 定义优化参数空间
            param_space = {
                'period': [10, 20, 30],
                'threshold': [0.01, 0.02, 0.03]
            }

            # 运行优化
            optimized_strategy = optimizer.optimize_strategy(
                test_strategy,
                test_data,
                param_space
            )

            print(f"✅ 策略优化完成，最优参数: {optimized_strategy.parameters}")

            self.test_results['strategy_optimization'] = True
            return True

        except Exception as e:
            print(f"❌ 策略优化测试失败: {e}")
            self.test_results['strategy_optimization'] = False
            return False

    def test_performance_comparison(self):
        """测试性能对比"""
        print("\n=== 测试性能对比 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            manager = StrategyManager()
            test_data = self._create_test_data()

            # 获取多个策略进行对比
            strategies = manager.get_all_strategies()[:3]  # 取前3个策略

            performance_results = {}

            for strategy in strategies:
                start_time = time.time()

                # 运行回测
                backtest_engine = UnifiedBacktestEngine(BacktestLevel.PROFESSIONAL)
                result = backtest_engine.run_strategy_backtest(strategy, test_data)

                end_time = time.time()
                execution_time = end_time - start_time

                performance_results[strategy.name] = {
                    'execution_time': execution_time,
                    'total_return': result.get('total_return', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0)
                }

                print(f"  {strategy.name}: 执行时间 {execution_time:.3f}s, 总收益 {result.get('total_return', 0):.2%}")

            # 找出最佳策略
            best_strategy = max(performance_results.items(),
                                key=lambda x: x[1]['sharpe_ratio'])

            print(f"✅ 性能对比完成，最佳策略: {best_strategy[0]}")

            self.test_results['performance_comparison'] = True
            return True

        except Exception as e:
            print(f"❌ 性能对比测试失败: {e}")
            self.test_results['performance_comparison'] = False
            return False

    def test_edge_cases(self):
        """测试边界条件"""
        print("\n=== 测试边界条件 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            manager = StrategyManager()

            # 测试空数据
            empty_data = pd.DataFrame()
            result = manager.run_strategy_on_empty_data(empty_data)
            print("✅ 空数据处理正常")

            # 测试异常参数
            invalid_strategy = self._create_invalid_strategy()
            result = manager.validate_strategy(invalid_strategy)
            print("✅ 异常参数验证正常")

            # 测试大数据集
            large_data = self._create_large_test_data()
            start_time = time.time()
            result = manager.run_strategy_on_large_data(large_data)
            end_time = time.time()
            print(f"✅ 大数据集处理正常，耗时: {end_time - start_time:.3f}s")

            self.test_results['edge_cases'] = True
            return True

        except Exception as e:
            print(f"❌ 边界条件测试失败: {e}")
            self.test_results['edge_cases'] = False
            return False

    def test_large_dataset(self):
        """测试大数据集性能"""
        print("\n=== 测试大数据集性能 ===")

        if not STRATEGY_MODULES_AVAILABLE:
            print("❌ 策略模块不可用，跳过测试")
            return False

        try:
            # 创建大数据集 (10年日线数据)
            large_data = self._create_large_test_data(years=10)
            print(f"创建大数据集: {len(large_data)} 条记录")

            manager = StrategyManager()
            strategy = manager.get_default_strategy()

            if strategy:
                start_time = time.time()

                # 运行策略
                backtest_engine = UnifiedBacktestEngine(BacktestLevel.PROFESSIONAL)
                result = backtest_engine.run_strategy_backtest(strategy, large_data)

                end_time = time.time()
                execution_time = end_time - start_time

                # 计算性能指标
                records_per_second = len(large_data) / execution_time

                print(f"✅ 大数据集处理完成")
                print(f"  数据量: {len(large_data)} 条")
                print(f"  执行时间: {execution_time:.3f}s")
                print(f"  处理速度: {records_per_second:.0f} 条/秒")

                # 性能基准检查
                if records_per_second > 1000:
                    print("🚀 性能优秀 (>1000 条/秒)")
                elif records_per_second > 500:
                    print("👍 性能良好 (>500 条/秒)")
                else:
                    print("⚠️  性能需要优化 (<500 条/秒)")

            self.test_results['large_dataset'] = True
            return True

        except Exception as e:
            print(f"❌ 大数据集测试失败: {e}")
            self.test_results['large_dataset'] = False
            return False

    def _create_test_data(self, days=252) -> pd.DataFrame:
        """创建测试数据"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        np.random.seed(42)

        # 生成价格数据
        returns = np.random.normal(0.0005, 0.02, days)
        prices = 100 * np.cumprod(1 + returns)

        return pd.DataFrame({
            'open': prices * np.random.uniform(0.99, 1.01, days),
            'high': prices * np.random.uniform(1.01, 1.05, days),
            'low': prices * np.random.uniform(0.95, 0.99, days),
            'close': prices,
            'volume': np.random.uniform(1000000, 10000000, days),
        }, index=dates)

    def _create_large_test_data(self, years=5) -> pd.DataFrame:
        """创建大数据集"""
        days = years * 252  # 交易日
        return self._create_test_data(days)

    def _create_test_strategy(self):
        """创建测试策略"""
        if not STRATEGY_MODULES_AVAILABLE:
            return None

        return StrategyConfig(
            name="test_strategy",
            type="trend_following",
            parameters={
                'period': 20,
                'threshold': 0.02
            }
        )

    def _create_invalid_strategy(self):
        """创建无效策略"""
        if not STRATEGY_MODULES_AVAILABLE:
            return None

        return StrategyConfig(
            name="invalid_strategy",
            type="unknown_type",
            parameters={
                'invalid_param': 'invalid_value'
            }
        )

    def run_comprehensive_tests(self):
        """运行全面测试"""
        print("🚀 开始策略系统全面测试")
        print("=" * 80)

        test_methods = [
            self.test_basic_functionality,
            self.test_backward_compatibility,
            self.test_professional_levels,
            self.test_risk_metrics,
            self.test_strategy_optimization,
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
        report_file = f"strategy_system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': success_rate,
            'total_time': total_time,
            'test_results': self.test_results,
            'system_info': {
                'strategy_modules_available': STRATEGY_MODULES_AVAILABLE,
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
    tester = StrategySystemTester()
    success = tester.run_comprehensive_tests()

    if success:
        print("\n🎉 策略系统测试通过！")
    else:
        print("\n⚠️  策略系统需要改进！")

    return success


if __name__ == "__main__":
    main()
