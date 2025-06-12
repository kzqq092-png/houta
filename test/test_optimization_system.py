#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
形态识别算法优化系统完整测试脚本
验证所有组件的功能和集成效果
"""

from analysis.pattern_manager import PatternManager
from optimization.main_controller import OptimizationController
from optimization.ui_integration import UIIntegration
from optimization.auto_tuner import AutoTuner
from optimization.algorithm_optimizer import AlgorithmOptimizer, OptimizationConfig
from optimization.version_manager import VersionManager
from optimization.performance_evaluator import PerformanceEvaluator
from optimization.database_schema import OptimizationDatabaseManager
import sys
import os
import time
import traceback
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入所有优化系统组件


class OptimizationSystemTester:
    """优化系统测试器"""

    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()

        print("🧪 HiKyuu 形态识别算法优化系统测试")
        print("=" * 60)
        print(f"测试开始时间: {self.start_time}")
        print()

    def run_all_tests(self):
        """运行所有测试"""
        tests = [
            ("数据库架构测试", self.test_database_schema),
            ("性能评估器测试", self.test_performance_evaluator),
            ("版本管理器测试", self.test_version_manager),
            ("算法优化器测试", self.test_algorithm_optimizer),
            ("自动调优器测试", self.test_auto_tuner),
            ("UI集成测试", self.test_ui_integration),
            ("主控制器测试", self.test_main_controller),
            ("系统集成测试", self.test_system_integration)
        ]

        for test_name, test_func in tests:
            print(f"🔍 {test_name}")
            print("-" * 40)

            try:
                start_time = time.time()
                result = test_func()
                end_time = time.time()

                self.test_results[test_name] = {
                    "status": "PASS" if result else "FAIL",
                    "duration": end_time - start_time,
                    "details": result if isinstance(result, dict) else {}
                }

                status_icon = "✅" if result else "❌"
                print(f"{status_icon} {test_name}: {'通过' if result else '失败'} "
                      f"({end_time - start_time:.3f}秒)")

            except Exception as e:
                self.test_results[test_name] = {
                    "status": "ERROR",
                    "duration": 0,
                    "error": str(e)
                }
                print(f"💥 {test_name}: 错误 - {e}")
                if "--debug" in sys.argv:
                    traceback.print_exc()

            print()

        # 生成测试报告
        self.generate_test_report()

    def test_database_schema(self) -> bool:
        """测试数据库架构"""
        try:
            # 创建数据库管理器
            db_manager = OptimizationDatabaseManager()

            # 测试表创建
            db_manager.init_tables()
            print("  ✓ 数据库表创建成功")

            # 测试版本保存
            version_id = db_manager.save_algorithm_version(
                pattern_id=1,
                pattern_name="test_pattern",
                algorithm_code="# Test algorithm",
                parameters={"test_param": 1.0},
                description="测试版本"
            )
            print(f"  ✓ 版本保存成功，ID: {version_id}")

            # 测试性能指标保存
            metrics = {
                "overall_score": 0.85,
                "signal_quality": 0.8,
                "confidence_avg": 0.75,
                "execution_time": 0.01
            }
            metric_id = db_manager.save_performance_metrics(version_id, "test_pattern", metrics)
            print(f"  ✓ 性能指标保存成功，ID: {metric_id}")

            # 测试统计信息获取
            stats = db_manager.get_optimization_statistics()
            print(f"  ✓ 统计信息获取成功: {len(stats)} 项")

            return True

        except Exception as e:
            print(f"  ❌ 数据库测试失败: {e}")
            return False

    def test_performance_evaluator(self) -> bool:
        """测试性能评估器"""
        try:
            evaluator = PerformanceEvaluator(debug_mode=True)

            # 测试数据集创建
            datasets = evaluator.create_test_datasets("hammer", count=2)
            print(f"  ✓ 创建测试数据集: {len(datasets)} 个")

            # 测试性能评估
            metrics = evaluator.evaluate_algorithm("hammer", datasets)
            print(f"  ✓ 性能评估完成，综合评分: {metrics.overall_score:.3f}")

            # 验证指标完整性
            required_metrics = [
                'overall_score', 'signal_quality', 'confidence_avg',
                'execution_time', 'patterns_found', 'robustness_score'
            ]

            for metric in required_metrics:
                if not hasattr(metrics, metric):
                    raise ValueError(f"缺少指标: {metric}")

            print("  ✓ 所有性能指标完整")
            return True

        except Exception as e:
            print(f"  ❌ 性能评估器测试失败: {e}")
            return False

    def test_version_manager(self) -> bool:
        """测试版本管理器"""
        try:
            version_manager = VersionManager()

            # 测试版本保存
            version_id = version_manager.save_version(
                pattern_id=1,
                pattern_name="test_pattern_vm",
                algorithm_code="# Test version management",
                parameters={"vm_param": 2.0},
                description="版本管理测试"
            )
            print(f"  ✓ 版本保存成功，ID: {version_id}")

            # 测试版本获取
            versions = version_manager.get_versions("test_pattern_vm")
            print(f"  ✓ 获取版本列表: {len(versions)} 个版本")

            # 测试版本激活
            if versions:
                success = version_manager.activate_version(versions[0].id)
                print(f"  ✓ 版本激活: {'成功' if success else '失败'}")

            # 测试最佳版本获取
            best_version = version_manager.get_best_version("test_pattern_vm")
            print(f"  ✓ 最佳版本获取: {'成功' if best_version else '无版本'}")

            return True

        except Exception as e:
            print(f"  ❌ 版本管理器测试失败: {e}")
            return False

    def test_algorithm_optimizer(self) -> bool:
        """测试算法优化器"""
        try:
            optimizer = AlgorithmOptimizer(debug_mode=True)

            # 创建简单的优化配置
            config = OptimizationConfig(
                method="random",  # 使用快速的随机优化
                max_iterations=3,
                population_size=5,
                timeout_minutes=2
            )

            # 测试单个形态优化
            result = optimizer.optimize_algorithm("hammer", config)

            print(f"  ✓ 优化完成")
            print(f"    基准评分: {result.get('baseline_score', 0):.3f}")
            print(f"    最佳评分: {result.get('best_score', 0):.3f}")
            print(f"    性能提升: {result.get('improvement_percentage', 0):.3f}%")
            print(f"    迭代次数: {result.get('iterations', 0)}")

            # 验证结果完整性
            required_keys = ['baseline_score', 'best_score', 'improvement_percentage', 'iterations']
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"缺少结果字段: {key}")

            return True

        except Exception as e:
            print(f"  ❌ 算法优化器测试失败: {e}")
            return False

    def test_auto_tuner(self) -> bool:
        """测试自动调优器"""
        try:
            auto_tuner = AutoTuner(max_workers=2, debug_mode=True)

            # 测试状态获取
            status = auto_tuner.get_optimization_status()
            print(f"  ✓ 获取优化状态: {status['active_optimizations']} 个活跃任务")

            # 测试一键优化（仅测试几个形态）
            test_patterns = ["hammer", "doji"]
            result = auto_tuner.one_click_optimize(
                pattern_names=test_patterns,
                optimization_method="random",
                max_iterations=3
            )

            summary = result.get("summary", {})
            print(f"  ✓ 一键优化完成")
            print(f"    总任务数: {summary.get('total_tasks', 0)}")
            print(f"    成功任务数: {summary.get('successful_tasks', 0)}")
            print(f"    平均改进: {summary.get('average_improvement', 0):.3f}%")

            return True

        except Exception as e:
            print(f"  ❌ 自动调优器测试失败: {e}")
            return False

    def test_ui_integration(self) -> bool:
        """测试UI集成"""
        try:
            ui_integration = UIIntegration(debug_mode=True)

            # 测试状态获取
            status = ui_integration.get_optimization_status()
            print(f"  ✓ UI状态获取: {status['active_optimizations']} 个活跃优化")

            # 测试右键菜单创建（无GUI模式）
            menu = ui_integration.create_pattern_context_menu("hammer")
            print(f"  ✓ 右键菜单创建: {'成功' if menu is not None else '无GUI模式'}")

            # 测试快速优化
            print("  ⏳ 测试快速优化...")
            ui_integration.quick_optimize("hammer")
            print("  ✓ 快速优化启动成功")

            # 等待优化完成
            time.sleep(2)

            return True

        except Exception as e:
            print(f"  ❌ UI集成测试失败: {e}")
            return False

    def test_main_controller(self) -> bool:
        """测试主控制器"""
        try:
            controller = OptimizationController(debug_mode=True)

            # 测试系统初始化
            controller.initialize_system()
            print("  ✓ 系统初始化成功")

            # 测试形态列表
            patterns = controller.pattern_manager.get_all_patterns()
            print(f"  ✓ 形态列表获取: {len(patterns)} 个形态")

            # 测试性能评估
            if patterns:
                test_pattern = patterns[0].english_name
                controller.evaluate_pattern(test_pattern, dataset_count=2)
                print(f"  ✓ 性能评估完成: {test_pattern}")

            return True

        except Exception as e:
            print(f"  ❌ 主控制器测试失败: {e}")
            return False

    def test_system_integration(self) -> bool:
        """测试系统集成"""
        try:
            # 测试组件间协作
            pattern_manager = PatternManager()
            db_manager = OptimizationDatabaseManager()

            # 获取形态列表
            patterns = pattern_manager.get_all_patterns()
            print(f"  ✓ 获取形态列表: {len(patterns)} 个")

            # 检查数据库连接
            stats = db_manager.get_optimization_statistics()
            print(f"  ✓ 数据库连接正常，统计项: {len(stats)}")

            # 测试端到端流程
            if patterns:
                test_pattern = patterns[0].english_name

                # 创建评估器并评估
                evaluator = PerformanceEvaluator(debug_mode=True)
                datasets = evaluator.create_test_datasets(test_pattern, count=1)
                metrics = evaluator.evaluate_algorithm(test_pattern, datasets)

                # 保存性能指标
                metric_id = db_manager.save_performance_metrics(
                    version_id=1,
                    pattern_name=test_pattern,
                    metrics={
                        "overall_score": metrics.overall_score,
                        "signal_quality": metrics.signal_quality,
                        "confidence_avg": metrics.confidence_avg,
                        "execution_time": metrics.execution_time,
                        "patterns_found": metrics.patterns_found
                    }
                )

                print(f"  ✓ 端到端流程测试完成，指标ID: {metric_id}")

            return True

        except Exception as e:
            print(f"  ❌ 系统集成测试失败: {e}")
            return False

    def generate_test_report(self):
        """生成测试报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        print("测试报告")
        print("=" * 60)
        print(f"测试开始时间: {self.start_time}")
        print(f"测试结束时间: {end_time}")
        print(f"总测试时间: {duration}")
        print()

        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.test_results.values() if r["status"] == "FAIL")
        error_tests = sum(1 for r in self.test_results.values() if r["status"] == "ERROR")

        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests} ✅")
        print(f"失败测试: {failed_tests} ❌")
        print(f"错误测试: {error_tests} 💥")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        print()

        # 详细结果
        print("详细结果:")
        print("-" * 40)
        for test_name, result in self.test_results.items():
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[result["status"]]
            duration = result.get("duration", 0)
            print(f"{status_icon} {test_name:<25} {result['status']:<6} ({duration:.3f}s)")

            if "error" in result:
                print(f"    错误: {result['error']}")

        print()

        # 系统评估
        if passed_tests == total_tests:
            print("🎉 所有测试通过！优化系统已准备就绪。")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️  大部分测试通过，系统基本可用，但需要修复部分问题。")
        else:
            print("❌ 多个测试失败，系统需要进一步调试。")

        # 保存报告到文件
        report_path = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"HiKyuu 形态识别算法优化系统测试报告\n")
                f.write(f"生成时间: {end_time}\n")
                f.write(f"测试时长: {duration}\n\n")

                for test_name, result in self.test_results.items():
                    f.write(f"{test_name}: {result['status']}\n")
                    if "error" in result:
                        f.write(f"  错误: {result['error']}\n")
                    f.write(f"  耗时: {result.get('duration', 0):.3f}秒\n\n")

            print(f"📄 测试报告已保存到: {report_path}")

        except Exception as e:
            print(f"⚠️  保存测试报告失败: {e}")


def main():
    """主函数"""
    print("🚀 启动形态识别算法优化系统测试")
    print()

    # 检查命令行参数
    if "--help" in sys.argv or "-h" in sys.argv:
        print("用法: python test_optimization_system.py [--debug]")
        print("  --debug: 启用调试模式，显示详细错误信息")
        return

    # 创建测试器并运行测试
    tester = OptimizationSystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
