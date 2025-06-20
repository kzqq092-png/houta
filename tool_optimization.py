#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HiKyuu 形态识别算法优化系统使用示例
演示如何使用优化系统的各种功能
"""

from optimization.algorithm_optimizer import AlgorithmOptimizer, OptimizationConfig
from optimization.performance_evaluator import PerformanceEvaluator
from optimization.version_manager import VersionManager
from optimization.auto_tuner import AutoTuner
from optimization.main_controller import OptimizationController
import sys
import os
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def example_1_basic_usage():
    """示例1：基本使用方法"""
    print("=" * 60)
    print("示例1：基本使用方法")
    print("=" * 60)

    # 创建控制器
    controller = OptimizationController(debug_mode=True)

    # 初始化系统
    print("🔧 初始化系统...")
    controller.initialize_system()

    # 查看系统状态
    print("\n 查看系统状态...")
    controller.show_system_status()

    # 列出所有形态
    print("\n📋 列出所有形态...")
    controller.list_patterns()

    print("\n✅ 示例1完成")


def example_2_single_pattern_optimization():
    """示例2：单个形态优化"""
    print("=" * 60)
    print("示例2：单个形态优化")
    print("=" * 60)

    controller = OptimizationController(debug_mode=True)

    # 选择要优化的形态
    pattern_name = "hammer"  # 锤头线

    print(f"优化形态: {pattern_name}")

    # 评估当前性能
    print("\n 评估当前性能...")
    controller.evaluate_pattern(pattern_name, dataset_count=2)

    # 优化形态
    print(f"\n🚀 开始优化 {pattern_name}...")
    controller.optimize_pattern(
        pattern_name=pattern_name,
        method="random",  # 使用随机搜索（快速）
        iterations=5      # 少量迭代（演示用）
    )

    # 查看版本历史
    print(f"\n📋 查看 {pattern_name} 版本历史...")
    controller.show_versions(pattern_name)

    print("\n✅ 示例2完成")


def example_3_batch_optimization():
    """示例3：批量优化"""
    print("=" * 60)
    print("示例3：批量优化")
    print("=" * 60)

    controller = OptimizationController(debug_mode=True)

    # 批量优化（仅优化几个形态作为演示）
    print("🚀 开始批量优化...")

    # 使用AutoTuner进行批量优化
    auto_tuner = AutoTuner(max_workers=2, debug_mode=True)

    # 选择几个形态进行演示
    test_patterns = ["hammer", "doji", "shooting_star"]

    result = auto_tuner.one_click_optimize(
        pattern_names=test_patterns,
        optimization_method="random",
        max_iterations=3
    )

    # 显示结果
    summary = result.get("summary", {})
    print(f"\n↑ 批量优化结果:")
    print(f"  总任务数: {summary.get('total_tasks', 0)}")
    print(f"  成功任务数: {summary.get('successful_tasks', 0)}")
    print(f"  成功率: {summary.get('success_rate', 0):.1f}%")
    print(f"  平均改进: {summary.get('average_improvement', 0):.3f}%")

    print("\n✅ 示例3完成")


def example_4_smart_optimization():
    """示例4：智能优化"""
    print("=" * 60)
    print("示例4：智能优化")
    print("=" * 60)

    controller = OptimizationController(debug_mode=True)

    # 智能优化（自动识别需要优化的形态）
    print("🧠 开始智能优化...")
    controller.smart_optimize(
        threshold=0.8,    # 性能阈值
        target=0.05       # 改进目标（5%）
    )

    print("\n✅ 示例4完成")


def example_5_version_management():
    """示例5：版本管理"""
    print("=" * 60)
    print("示例5：版本管理")
    print("=" * 60)

    version_manager = VersionManager()
    pattern_name = "hammer"

    print(f"📋 管理 {pattern_name} 的版本...")

    # 获取版本列表
    versions = version_manager.get_versions(pattern_name, limit=5)

    if versions:
        print(f"\n发现 {len(versions)} 个版本:")
        for i, version in enumerate(versions, 1):
            status = "✓ 激活" if version.is_active else "未激活"
            print(f"  {i}. 版本 {version.version_number} - {status}")
            print(f"     创建时间: {version.created_time}")
            print(f"     优化方法: {version.optimization_method}")
            if version.performance_metrics:
                print(f"     性能评分: {version.performance_metrics.overall_score:.3f}")

        # 演示版本激活
        if len(versions) > 1:
            print(f"\n激活版本 {versions[1].version_number}...")
            success = version_manager.activate_version(versions[1].id)
            print(f"激活结果: {'成功' if success else '失败'}")
    else:
        print("暂无版本记录")

    print("\n✅ 示例5完成")


def example_6_performance_evaluation():
    """示例6：性能评估"""
    print("=" * 60)
    print("示例6：性能评估")
    print("=" * 60)

    evaluator = PerformanceEvaluator(debug_mode=True)
    pattern_name = "hammer"

    print(f"详细评估 {pattern_name} 性能...")

    # 创建测试数据集
    datasets = evaluator.create_test_datasets(pattern_name, count=3)
    print(f"创建了 {len(datasets)} 个测试数据集")

    # 执行评估
    metrics = evaluator.evaluate_algorithm(pattern_name, datasets)

    # 显示详细结果
    print(f"\n↑ 性能评估结果:")
    print(f"  综合评分: {metrics.overall_score:.3f}")
    print(f"  信号质量: {metrics.signal_quality:.3f}")
    print(f"  平均置信度: {metrics.confidence_avg:.3f}")
    print(f"  执行时间: {metrics.execution_time:.3f}秒")
    print(f"  识别形态数: {metrics.patterns_found}")
    print(f"  鲁棒性评分: {metrics.robustness_score:.3f}")
    print(f"  参数敏感性: {metrics.parameter_sensitivity:.3f}")

    print("\n✅ 示例6完成")


def example_7_export_import():
    """示例7：数据导出导入"""
    print("=" * 60)
    print("示例7：数据导出导入")
    print("=" * 60)

    controller = OptimizationController(debug_mode=True)

    # 导出数据
    print("💾 导出优化数据...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = f"example_export_{timestamp}.json"

    controller.export_data(output_path=export_path)

    # 检查导出文件
    if os.path.exists(export_path):
        file_size = os.path.getsize(export_path)
        print(f"✅ 导出成功，文件大小: {file_size} 字节")

        # 清理演示文件
        os.remove(export_path)
        print("🗑️  清理演示文件")
    else:
        print("❌ 导出失败")

    print("\n✅ 示例7完成")


def example_8_advanced_configuration():
    """示例8：高级配置"""
    print("=" * 60)
    print("示例8：高级配置")
    print("=" * 60)

    # 创建自定义优化配置
    config = OptimizationConfig(
        method="genetic",           # 遗传算法
        max_iterations=20,          # 最大迭代次数
        population_size=15,         # 种群大小
        mutation_rate=0.15,         # 变异率
        crossover_rate=0.85,        # 交叉率
        target_metric="overall_score",  # 目标指标
        timeout_minutes=10          # 超时时间
    )

    print("⚙️  自定义优化配置:")
    print(f"  优化方法: {config.method}")
    print(f"  最大迭代: {config.max_iterations}")
    print(f"  种群大小: {config.population_size}")
    print(f"  变异率: {config.mutation_rate}")
    print(f"  交叉率: {config.crossover_rate}")

    # 使用自定义配置优化
    optimizer = AlgorithmOptimizer(debug_mode=True)

    print(f"\n🚀 使用自定义配置优化 hammer...")
    result = optimizer.optimize_algorithm("hammer", config)

    print(f"↑ 优化结果:")
    print(f"  基准评分: {result.get('baseline_score', 0):.3f}")
    print(f"  最佳评分: {result.get('best_score', 0):.3f}")
    print(f"  性能提升: {result.get('improvement_percentage', 0):.3f}%")

    print("\n✅ 示例8完成")


def main():
    """主函数"""
    print("🚀 HiKyuu 形态识别算法优化系统使用示例")
    print(f"开始时间: {datetime.now()}")
    print()

    examples = [
        ("基本使用方法", example_1_basic_usage),
        ("单个形态优化", example_2_single_pattern_optimization),
        ("批量优化", example_3_batch_optimization),
        ("智能优化", example_4_smart_optimization),
        ("版本管理", example_5_version_management),
        ("性能评估", example_6_performance_evaluation),
        ("数据导出导入", example_7_export_import),
        ("高级配置", example_8_advanced_configuration)
    ]

    # 检查命令行参数
    if len(sys.argv) > 1:
        try:
            example_num = int(sys.argv[1])
            if 1 <= example_num <= len(examples):
                name, func = examples[example_num - 1]
                print(f"运行示例 {example_num}: {name}")
                func()
                return
            else:
                print(f"❌ 示例编号必须在 1-{len(examples)} 之间")
                return
        except ValueError:
            print("❌ 请提供有效的示例编号")
            return

    # 显示所有可用示例
    print("可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print(f"\n用法: python {sys.argv[0]} <示例编号>")
    print("或者运行所有示例:")

    # 询问是否运行所有示例
    try:
        choice = input("\n是否运行所有示例？(y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            for i, (name, func) in enumerate(examples, 1):
                print(f"\n运行示例 {i}: {name}")
                try:
                    func()
                    time.sleep(1)  # 短暂暂停
                except Exception as e:
                    print(f"❌ 示例 {i} 执行失败: {e}")
                    continue

            print(f"\n🎉 所有示例执行完成！")
            print(f"结束时间: {datetime.now()}")
        else:
            print("👋 再见！")

    except KeyboardInterrupt:
        print("\n⚠️  操作被用户中断")
    except Exception as e:
        print(f"❌ 执行失败: {e}")


if __name__ == "__main__":
    main()
