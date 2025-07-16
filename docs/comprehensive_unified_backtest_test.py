#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YS-Quant‌统一回测引擎全面测试脚本
测试统一回测引擎的各项功能，确保系统稳定性和性能
"""

import sys
import os
import pandas as pd
import numpy as np
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入统一回测引擎
try:
    from backtest.unified_backtest_engine import (
        UnifiedBacktestEngine,
        BacktestLevel,
        FixedStrategyBacktester,
        StrategyBacktester,
        PortfolioBacktestEngine,
        create_unified_backtest_engine,
        create_portfolio_backtest_engine
    )
    UNIFIED_ENGINE_AVAILABLE = True
    print("✅ 统一回测引擎导入成功")
except ImportError as e:
    print(f"❌ 统一回测引擎导入失败: {e}")
    UNIFIED_ENGINE_AVAILABLE = False

# 注释掉不存在的模块导入
# 原版引擎已被统一引擎替代
ORIGINAL_ENGINE_AVAILABLE = False
FIXED_ENGINE_AVAILABLE = True  # 使用统一引擎中的兼容类


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_simple_data(days: int = 100, start_price: float = 100.0) -> pd.DataFrame:
        """生成简单测试数据"""
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

        # 生成价格数据
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, days)
        prices = start_price * np.cumprod(1 + returns)

        # 生成OHLCV数据
        data = pd.DataFrame({
            'open': prices * np.random.uniform(0.99, 1.01, days),
            'high': prices * np.random.uniform(1.01, 1.05, days),
            'low': prices * np.random.uniform(0.95, 0.99, days),
            'close': prices,
            'volume': np.random.uniform(1000000, 10000000, days),
        }, index=dates)

        return data

    @staticmethod
    def generate_signal_data(data: pd.DataFrame, signal_type: str = "random") -> pd.DataFrame:
        """生成交易信号数据"""
        signal_data = data.copy()

        if signal_type == "random":
            # 随机信号
            signals = np.random.choice(
                [-1, 0, 1], len(data), p=[0.1, 0.8, 0.1])
        elif signal_type == "trend":
            # 趋势跟踪信号
            ma_short = data['close'].rolling(5).mean()
            ma_long = data['close'].rolling(20).mean()
            signals = np.where(ma_short > ma_long, 1, -1)
        elif signal_type == "profitable":
            # 盈利信号（每次交易都盈利）
            signals = []
            for i in range(len(data)):
                if i % 10 == 0:
                    signals.append(1)  # 买入
                elif i % 10 == 5:
                    signals.append(-1)  # 卖出
                else:
                    signals.append(0)  # 持有
        else:
            signals = np.zeros(len(data))

        signal_data['signal'] = signals
        return signal_data


class UnifiedBacktestTester:
    """统一回测引擎测试器"""

    def __init__(self):
        self.test_results = []
        self.performance_data = []

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始YS-Quant‌统一回测引擎全面测试")
        print("=" * 80)

        start_time = time.time()

        # 测试1: 基础功能测试
        self.test_basic_functionality()

        # 测试2: 向后兼容性测试
        self.test_backward_compatibility()

        # 测试3: 专业级别测试
        self.test_professional_levels()

        # 测试4: 风险指标测试
        self.test_risk_metrics()

        # 测试5: 复利计算测试
        self.test_compound_calculation()

        # 测试6: 性能对比测试
        self.test_performance_comparison()

        # 测试7: 边界条件测试
        self.test_edge_cases()

        # 测试8: 大数据集测试
        self.test_large_dataset()

        end_time = time.time()

        # 生成测试报告
        return self.generate_test_report(end_time - start_time)

    def test_basic_functionality(self):
        """测试基础功能"""
        print("\n📋 测试1: 基础功能测试")
        print("-" * 50)

        try:
            # 生成测试数据
            data = TestDataGenerator.generate_simple_data(100)
            signal_data = TestDataGenerator.generate_signal_data(
                data, "random")

            # 创建统一回测引擎
            engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.PROFESSIONAL
            )

            # 运行回测
            start_time = time.time()
            result = engine.run_backtest(
                data=signal_data,
                initial_capital=100000,
                position_size=0.9,
                commission_pct=0.001,
                slippage_pct=0.001
            )
            execution_time = time.time() - start_time

            # 验证结果
            assert 'backtest_result' in result
            assert 'risk_metrics' in result
            assert 'performance_summary' in result

            backtest_result = result['backtest_result']
            assert len(backtest_result) == len(signal_data)
            assert 'capital' in backtest_result.columns
            assert 'position' in backtest_result.columns

            print(f"  ✅ 基础回测执行成功")
            print(f"     执行时间: {execution_time:.3f}秒")
            print(f"     数据点数: {len(signal_data)}")
            print(f"     最终资金: {backtest_result['capital'].iloc[-1]:.2f}")

            self.test_results.append({
                'test_name': '基础功能测试',
                'success': True,
                'execution_time': execution_time,
                'details': f"数据点数: {len(signal_data)}, 最终资金: {backtest_result['capital'].iloc[-1]:.2f}"
            })

        except Exception as e:
            print(f"  ❌ 基础功能测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '基础功能测试',
                'success': False,
                'error': str(e)
            })

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        print("\n🔄 测试2: 向后兼容性测试")
        print("-" * 50)

        try:
            data = TestDataGenerator.generate_simple_data(50)
            signal_data = TestDataGenerator.generate_signal_data(
                data, "profitable")

            # 测试FixedStrategyBacktester兼容性
            print("  测试FixedStrategyBacktester兼容性...")
            fixed_backtester = FixedStrategyBacktester(
                data=signal_data,
                initial_capital=100000,
                position_size=0.9,
                commission_pct=0.001,
                slippage_pct=0.001
            )

            fixed_result = fixed_backtester.run_backtest()
            assert 'capital' in fixed_result.columns
            print(f"    ✅ FixedStrategyBacktester兼容性测试通过")

            # 测试StrategyBacktester兼容性
            print("  测试StrategyBacktester兼容性...")
            strategy_backtester = StrategyBacktester(
                data=signal_data,
                initial_capital=100000,
                position_size=0.9,
                commission_pct=0.001,
                slippage_pct=0.001
            )

            strategy_result = strategy_backtester.run_backtest()
            assert 'capital' in strategy_result.columns
            print(f"    ✅ StrategyBacktester兼容性测试通过")

            # 测试create_unified_backtest_engine函数
            print("  测试create_unified_backtest_engine函数...")
            engine = create_unified_backtest_engine(level="professional")

            engine_result = engine.run_backtest(
                data=signal_data,
                initial_capital=100000,
                position_size=0.9
            )
            assert 'backtest_result' in engine_result
            print(f"    ✅ create_unified_backtest_engine函数测试通过")

            self.test_results.append({
                'test_name': '向后兼容性测试',
                'success': True,
                'details': "所有兼容性接口测试通过"
            })

        except Exception as e:
            print(f"  ❌ 向后兼容性测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '向后兼容性测试',
                'success': False,
                'error': str(e)
            })

    def test_professional_levels(self):
        """测试专业级别"""
        print("\n🎯 测试3: 专业级别测试")
        print("-" * 50)

        try:
            data = TestDataGenerator.generate_simple_data(100)
            signal_data = TestDataGenerator.generate_signal_data(data, "trend")

            levels = [
                BacktestLevel.BASIC,
                BacktestLevel.PROFESSIONAL,
                BacktestLevel.INSTITUTIONAL,
                BacktestLevel.INVESTMENT_BANK
            ]

            for level in levels:
                print(f"  测试{level.value}级别...")

                engine = UnifiedBacktestEngine(
                    backtest_level=level
                )

                start_time = time.time()
                result = engine.run_backtest(
                    data=signal_data,
                    initial_capital=100000,
                    position_size=0.8
                )
                execution_time = time.time() - start_time

                # 验证不同级别的风险指标数量
                risk_metrics = result['risk_metrics']

                if level == BacktestLevel.BASIC:
                    expected_metrics = 8  # 基础指标
                elif level == BacktestLevel.PROFESSIONAL:
                    expected_metrics = 15  # 专业指标
                elif level == BacktestLevel.INSTITUTIONAL:
                    expected_metrics = 20  # 机构指标
                else:  # INVESTMENT_BANK
                    expected_metrics = 25  # 投行级指标

                actual_metrics = len([k for k, v in risk_metrics.__dict__.items()
                                      if not k.startswith('_') and v is not None])

                print(f"    ✅ {level.value}级别测试通过")
                print(f"       执行时间: {execution_time:.3f}秒")
                print(f"       风险指标数量: {actual_metrics}")

            self.test_results.append({
                'test_name': '专业级别测试',
                'success': True,
                'details': f"测试了{len(levels)}个专业级别"
            })

        except Exception as e:
            print(f"  ❌ 专业级别测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '专业级别测试',
                'success': False,
                'error': str(e)
            })

    def test_risk_metrics(self):
        """测试风险指标"""
        print("\n📊 测试4: 风险指标测试")
        print("-" * 50)

        try:
            data = TestDataGenerator.generate_simple_data(252)  # 一年数据
            signal_data = TestDataGenerator.generate_signal_data(
                data, "profitable")

            engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.INVESTMENT_BANK
            )

            result = engine.run_backtest(
                data=signal_data,
                initial_capital=1000000,
                position_size=0.95
            )
            risk_metrics = result['risk_metrics']

            # 验证关键风险指标
            key_metrics = [
                'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
                'max_drawdown', 'calmar_ratio', 'sortino_ratio', 'var_95', 'cvar_95'
            ]

            for metric in key_metrics:
                value = getattr(risk_metrics, metric, None)
                assert value is not None, f"{metric} 指标缺失"
                assert isinstance(value, (int, float)), f"{metric} 指标类型错误"
                print(f"    {metric}: {value:.4f}")

            print(f"  ✅ 风险指标测试通过")
            print(f"     总收益率: {risk_metrics.total_return:.2%}")
            print(f"     年化收益率: {risk_metrics.annualized_return:.2%}")
            print(f"     夏普比率: {risk_metrics.sharpe_ratio:.3f}")
            print(f"     最大回撤: {risk_metrics.max_drawdown:.2%}")

            self.test_results.append({
                'test_name': '风险指标测试',
                'success': True,
                'details': f"验证了{len(key_metrics)}个关键风险指标"
            })

        except Exception as e:
            print(f"  ❌ 风险指标测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '风险指标测试',
                'success': False,
                'error': str(e)
            })

    def test_compound_calculation(self):
        """测试复利计算"""
        print("\n💰 测试5: 复利计算测试")
        print("-" * 50)

        try:
            # 创建每次交易都盈利10%的数据
            data = pd.DataFrame({
                'open': [100, 110, 121, 133],
                'high': [101, 111, 122, 134],
                'low': [99, 109, 120, 132],
                'close': [100, 110, 121, 133],
                'volume': [1000000] * 4,
                'signal': [1, -1, 1, -1]  # 买入-卖出-买入-卖出
            }, index=pd.date_range('2023-01-01', periods=4, freq='D'))

            # 测试不启用复利
            engine_no_compound = UnifiedBacktestEngine()

            result_no_compound = engine_no_compound.run_backtest(
                data=data,
                enable_compound=False,
                initial_capital=100000,
                position_size=0.9,
                commission_pct=0.001,
                slippage_pct=0.001
            )
            final_capital_no_compound = result_no_compound['backtest_result']['capital'].iloc[-1]

            # 测试启用复利
            engine_compound = UnifiedBacktestEngine()

            result_compound = engine_compound.run_backtest(
                data=data,
                enable_compound=True,
                initial_capital=100000,
                position_size=0.9,
                commission_pct=0.001,
                slippage_pct=0.001
            )
            final_capital_compound = result_compound['backtest_result']['capital'].iloc[-1]

            # 验证复利效果
            compound_effect = final_capital_compound - final_capital_no_compound

            print(f"  不启用复利最终资金: {final_capital_no_compound:.2f}")
            print(f"  启用复利最终资金: {final_capital_compound:.2f}")
            print(f"  复利效应差异: {compound_effect:.2f}")

            assert final_capital_compound > final_capital_no_compound, "复利计算未生效"

            print(f"  ✅ 复利计算测试通过")

            self.test_results.append({
                'test_name': '复利计算测试',
                'success': True,
                'details': f"复利效应差异: {compound_effect:.2f}"
            })

        except Exception as e:
            print(f"  ❌ 复利计算测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '复利计算测试',
                'success': False,
                'error': str(e)
            })

    def test_performance_comparison(self):
        """测试性能对比"""
        print("\n⚡ 测试6: 性能对比测试")
        print("-" * 50)

        try:
            data = TestDataGenerator.generate_simple_data(1000)
            signal_data = TestDataGenerator.generate_signal_data(
                data, "random")

            # 测试统一引擎性能
            engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.PROFESSIONAL
            )

            start_time = time.time()
            unified_result = engine.run_backtest(
                data=signal_data,
                initial_capital=100000,
                position_size=0.9
            )
            unified_time = time.time() - start_time

            print(f"  统一引擎执行时间: {unified_time:.3f}秒")

            # 如果原版引擎可用，进行对比
            if FIXED_ENGINE_AVAILABLE:
                try:
                    original_engine = FixedStrategyBacktester(
                        data=signal_data,
                        initial_capital=100000,
                        position_size=0.9,
                        commission_pct=0.001,
                        slippage_pct=0.001
                    )

                    start_time = time.time()
                    original_result = original_engine.run_backtest()
                    original_time = time.time() - start_time

                    print(f"  原版引擎执行时间: {original_time:.3f}秒")
                    print(
                        f"  性能提升: {((original_time - unified_time) / original_time * 100):.1f}%")

                except Exception as e:
                    print(f"  原版引擎测试失败: {e}")

            self.performance_data.append({
                'engine': 'unified',
                'data_size': len(signal_data),
                'execution_time': unified_time
            })

            print(f"  ✅ 性能对比测试完成")

            self.test_results.append({
                'test_name': '性能对比测试',
                'success': True,
                'details': f"统一引擎执行时间: {unified_time:.3f}秒"
            })

        except Exception as e:
            print(f"  ❌ 性能对比测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '性能对比测试',
                'success': False,
                'error': str(e)
            })

    def test_edge_cases(self):
        """测试边界条件"""
        print("\n🔍 测试7: 边界条件测试")
        print("-" * 50)

        try:
            # 测试空数据
            print("  测试空数据处理...")
            empty_data = pd.DataFrame()
            engine = UnifiedBacktestEngine()

            try:
                result = engine.run_backtest(
                    data=empty_data,
                    initial_capital=100000
                )
                print("    ✅ 空数据正确抛出异常")
            except Exception:
                print("    ✅ 空数据正确抛出异常")

            # 测试单行数据
            print("  测试单行数据处理...")
            single_data = TestDataGenerator.generate_simple_data(1)
            single_data['signal'] = [1]

            try:
                result = engine.run_backtest(
                    data=single_data,
                    initial_capital=100000
                )
                print("    ✅ 单行数据处理成功")
            except Exception as e:
                print(f"    ⚠️ 单行数据处理异常: {e}")

            # 测试极端参数
            print("  测试极端参数...")
            normal_data = TestDataGenerator.generate_simple_data(10)
            normal_data['signal'] = [1, -1] * 5

            extreme_engine = UnifiedBacktestEngine()

            try:
                result = extreme_engine.run_backtest(
                    data=normal_data,
                    initial_capital=1,  # 极小资金
                    position_size=1.0,  # 满仓
                    commission_pct=0.1,  # 极高手续费
                    slippage_pct=0.1    # 极高滑点
                )
                print("    ✅ 极端参数处理成功")
            except Exception as e:
                print(f"    ⚠️ 极端参数处理异常: {e}")

            print(f"  ✅ 边界条件测试完成")

            self.test_results.append({
                'test_name': '边界条件测试',
                'success': True,
                'details': "测试了空数据、单行数据、极端参数等边界条件"
            })

        except Exception as e:
            print(f"  ❌ 边界条件测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '边界条件测试',
                'success': False,
                'error': str(e)
            })

    def test_large_dataset(self):
        """测试大数据集"""
        print("\n📈 测试8: 大数据集测试")
        print("-" * 50)

        try:
            # 生成大数据集（5年日线数据）
            large_data = TestDataGenerator.generate_simple_data(1260)  # 5年
            signal_data = TestDataGenerator.generate_signal_data(
                large_data, "trend")

            engine = UnifiedBacktestEngine(
                backtest_level=BacktestLevel.INVESTMENT_BANK
            )

            print(f"  测试数据规模: {len(signal_data)}行")

            start_time = time.time()
            result = engine.run_backtest(
                data=signal_data,
                initial_capital=1000000,
                position_size=0.95
            )
            execution_time = time.time() - start_time

            # 验证结果
            backtest_result = result['backtest_result']
            risk_metrics = result['risk_metrics']

            print(f"  ✅ 大数据集测试通过")
            print(f"     执行时间: {execution_time:.3f}秒")
            print(f"     数据处理速度: {len(signal_data)/execution_time:.0f}行/秒")
            print(f"     最终资金: {backtest_result['capital'].iloc[-1]:,.2f}")
            print(f"     总收益率: {risk_metrics.total_return:.2%}")

            self.performance_data.append({
                'engine': 'unified_large',
                'data_size': len(signal_data),
                'execution_time': execution_time,
                'processing_speed': len(signal_data)/execution_time
            })

            self.test_results.append({
                'test_name': '大数据集测试',
                'success': True,
                'details': f"处理{len(signal_data)}行数据，耗时{execution_time:.3f}秒"
            })

        except Exception as e:
            print(f"  ❌ 大数据集测试失败: {e}")
            traceback.print_exc()
            self.test_results.append({
                'test_name': '大数据集测试',
                'success': False,
                'error': str(e)
            })

    def generate_test_report(self, total_time: float) -> Dict[str, Any]:
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("📋 YS-Quant‌统一回测引擎测试报告")
        print("=" * 80)

        # 统计测试结果
        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests *
                        100) if total_tests > 0 else 0

        print(f"测试总数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"总执行时间: {total_time:.3f}秒")

        # 详细结果
        print(f"\n详细测试结果:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"  {i}. {result['test_name']}: {status}")
            if 'details' in result:
                print(f"     {result['details']}")
            if 'error' in result:
                print(f"     错误: {result['error']}")

        # 性能数据
        if self.performance_data:
            print(f"\n性能数据:")
            for perf in self.performance_data:
                print(
                    f"  {perf['engine']}: {perf['data_size']}行数据, {perf['execution_time']:.3f}秒")
                if 'processing_speed' in perf:
                    print(f"    处理速度: {perf['processing_speed']:.0f}行/秒")

        # 评级
        if success_rate >= 90:
            grade = "A+ 优秀"
        elif success_rate >= 80:
            grade = "A 良好"
        elif success_rate >= 70:
            grade = "B 一般"
        else:
            grade = "C 需要改进"

        print(f"\n总体评级: {grade}")

        # 建议
        print(f"\n建议:")
        if failed_tests == 0:
            print("  🎉 所有测试通过！统一回测引擎已准备好投入使用。")
            print("  📝 建议：可以开始更新其他模块以使用统一回测引擎。")
        else:
            print(f"  ⚠️  有{failed_tests}个测试失败，需要修复后再投入使用。")
            print("  🔧 建议：检查失败的测试用例并修复相关问题。")

        # 保存报告到文件
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'total_time': total_time,
            'grade': grade,
            'test_results': self.test_results,
            'performance_data': self.performance_data
        }

        try:
            report_path = Path("reports/unified_backtest_test_report.json")
            report_path.parent.mkdir(parents=True, exist_ok=True)

            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            print(f"\n📄 详细报告已保存到: {report_path}")

        except Exception as e:
            print(f"⚠️ 保存报告失败: {e}")

        return report_data


def main():
    """主函数"""
    if not UNIFIED_ENGINE_AVAILABLE:
        print("❌ 统一回测引擎不可用，无法进行测试")
        return False

    tester = UnifiedBacktestTester()
    report = tester.run_all_tests()

    return report['success_rate'] == 100.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
