#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运行所有集成测试的主脚本

统一运行阶段一、二、三完成的所有智能化功能的集成测试
包括：阶段一核心功能 + 阶段二智能化增强功能 + 阶段三架构增强功能
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入所有测试模块
try:
    # 阶段一：核心功能集成测试
    from tests.test_enhanced_import_engine_integration import run_integration_tests
    from tests.test_ai_services_integration import run_ai_services_tests
    from tests.test_monitoring_and_cache_integration import run_monitoring_cache_tests
    from tests.test_distributed_and_autotuner_integration import run_distributed_autotuner_tests
    from tests.test_data_quality_integration import run_data_quality_tests

    PHASE1_TESTS_AVAILABLE = True
except ImportError as e:
    print(f"阶段一测试模块导入失败: {e}")
    PHASE1_TESTS_AVAILABLE = False

try:
    # 阶段二：智能化增强功能测试
    import pytest

    # 检查阶段二测试文件是否存在
    phase2_test_files = [
        "tests/test_intelligent_config_manager.py",
        "tests/test_enhanced_risk_monitor.py",
        "tests/test_enhanced_performance_bridge.py"
    ]

    PHASE2_TESTS_AVAILABLE = all(Path(f).exists() for f in phase2_test_files)

except ImportError as e:
    print(f"阶段二测试依赖导入失败: {e}")
    PHASE2_TESTS_AVAILABLE = False

try:
    # 阶段三：架构增强功能测试
    # 检查阶段三测试文件是否存在
    phase3_test_files = [
        "tests/test_enhanced_event_bus.py",
        "tests/test_enhanced_async_manager.py",
        "tests/test_enhanced_distributed_service.py"
    ]

    PHASE3_TESTS_AVAILABLE = all(Path(f).exists() for f in phase3_test_files)

except Exception as e:
    print(f"阶段三测试检查失败: {e}")
    PHASE3_TESTS_AVAILABLE = False

ALL_TESTS_AVAILABLE = PHASE1_TESTS_AVAILABLE and PHASE2_TESTS_AVAILABLE and PHASE3_TESTS_AVAILABLE


def print_banner():
    """打印测试横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 FactorWeave-Quant 增强版数据导入系统                    ║
║                      阶段一+二+三 完整集成测试套件                            ║
║                                                                              ║
║  阶段一测试范围：                                                              ║
║  ✅ AI预测服务集成                                                            ║
║  📊 监控和异常检测系统集成                                                      ║
║  💾 多级缓存系统集成                                                          ║
║  🌐 服务发现和分布式服务增强                                                    ║
║  ⚙️ AutoTuner自动调优集成                                                     ║
║  ✅ 数据质量指标系统增强                                                       ║
║                                                                              ║
║  阶段二测试范围：                                                              ║
║  🧠 智能配置管理系统                                                          ║
║  ⚠️ 增强风险监控系统                                                          ║
║  📈 增强性能桥接系统                                                          ║
║                                                                              ║
║  阶段三测试范围：                                                              ║
║  🚌 增强版事件总线                                                            ║
║  ⚡ 增强版异步任务管理器                                                        ║
║  🌐 增强版分布式服务                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_test_suite(test_name, test_function):
    """运行单个测试套件"""
    print(f"\n{'='*80}")
    print(f"🧪 开始运行 {test_name}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        success = test_function()
        end_time = time.time()
        duration = end_time - start_time

        if success:
            print(f"✅ {test_name} 测试通过！耗时: {duration:.2f}秒")
            return True, duration, None
        else:
            print(f"❌ {test_name} 测试失败！耗时: {duration:.2f}秒")
            return False, duration, "测试失败"

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 {test_name} 测试遇到异常: {e}")
        print(f"耗时: {duration:.2f}秒")
        return False, duration, str(e)


def run_phase2_pytest_suite(test_file_path, test_name):
    """运行阶段二的pytest测试套件"""
    print(f"\n{'='*80}")
    print(f"🧪 开始运行 {test_name}")
    print(f"📁 测试文件: {test_file_path}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        # 使用pytest运行测试
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            test_file_path,
            "-v", "--tb=short", "--no-header"
        ], capture_output=True, text=True, cwd=project_root)

        end_time = time.time()
        duration = end_time - start_time

        # 打印测试输出
        if result.stdout:
            print("📋 测试输出:")
            print(result.stdout)

        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)

        success = result.returncode == 0

        if success:
            print(f"✅ {test_name} 测试通过！耗时: {duration:.2f}秒")
            return True, duration, None
        else:
            print(f"❌ {test_name} 测试失败！耗时: {duration:.2f}秒")
            return False, duration, f"pytest返回码: {result.returncode}"

    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 {test_name} 测试遇到异常: {e}")
        print(f"耗时: {duration:.2f}秒")
        return False, duration, str(e)


def generate_test_report(test_results):
    """生成测试报告"""
    report = {
        "测试时间": datetime.now().isoformat(),
        "测试概述": {
            "总测试套件数": len(test_results),
            "通过套件数": sum(1 for r in test_results if r['success']),
            "失败套件数": sum(1 for r in test_results if not r['success']),
            "总耗时": f"{sum(r['duration'] for r in test_results):.2f}秒"
        },
        "详细结果": []
    }

    for result in test_results:
        detail = {
            "测试套件": result['name'],
            "状态": "通过" if result['success'] else "失败",
            "耗时": f"{result['duration']:.2f}秒",
            "错误信息": result['error'] if result['error'] else "无"
        }
        report["详细结果"].append(detail)

    # 保存报告
    report_file = Path("tests/integration_test_full_report.json")
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report, report_file


def print_summary(test_results):
    """打印测试摘要"""
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r['success'])
    failed_tests = total_tests - passed_tests
    total_time = sum(r['duration'] for r in test_results)

    print(f"\n{'='*80}")
    print("🎯 集成测试总结")
    print(f"{'='*80}")
    print(f"📊 测试统计:")
    print(f"   总测试套件: {total_tests}")
    print(f"   通过套件: {passed_tests} ✅")
    print(f"   失败套件: {failed_tests} ❌")
    print(f"   成功率: {passed_tests/total_tests*100:.1f}%")
    print(f"   总耗时: {total_time:.2f}秒")

    if failed_tests > 0:
        print(f"\n❌ 失败的测试套件:")
        for result in test_results:
            if not result['success']:
                print(f"   - {result['name']}: {result['error']}")

    print(f"\n📋 详细结果:")
    phase1_results = [r for r in test_results if r.get('phase') == 'Phase 1']
    phase2_results = [r for r in test_results if r.get('phase') == 'Phase 2']
    phase3_results = [r for r in test_results if r.get('phase') == 'Phase 3']

    if phase1_results:
        print(f"   🚀 阶段一测试:")
        for result in phase1_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"     {result['name']}: {status} ({result['duration']:.2f}秒)")

    if phase2_results:
        print(f"   🧠 阶段二测试:")
        for result in phase2_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"     {result['name']}: {status} ({result['duration']:.2f}秒)")

    if phase3_results:
        print(f"   🚌 阶段三测试:")
        for result in phase3_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"     {result['name']}: {status} ({result['duration']:.2f}秒)")

    if passed_tests == total_tests:
        print(f"\n🎉 恭喜！所有集成测试都通过了！")
        if phase1_results and phase2_results and phase3_results:
            print(f"🚀 FactorWeave-Quant 增强版数据导入系统阶段一+二+三完整集成完成！")
        elif phase1_results and phase2_results:
            print(f"🚀 FactorWeave-Quant 增强版数据导入系统阶段一+二完整集成完成！")
        elif phase1_results:
            print(f"🚀 FactorWeave-Quant 增强版数据导入系统阶段一集成完成！")
        elif phase2_results:
            print(f"🧠 FactorWeave-Quant 增强版数据导入系统阶段二智能化增强完成！")
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试套件未通过，请检查并修复问题。")


def main():
    """主函数"""
    print_banner()

    # 检查测试可用性
    available_phases = []
    if PHASE1_TESTS_AVAILABLE:
        available_phases.append("阶段一")
    if PHASE2_TESTS_AVAILABLE:
        available_phases.append("阶段二")
    if PHASE3_TESTS_AVAILABLE:
        available_phases.append("阶段三")

    if not available_phases:
        print("❌ 没有可用的测试模块，请检查依赖和路径配置。")
        return False
    else:
        print(f"✅ 可用的测试模块: {', '.join(available_phases)}")

    # 定义阶段一测试套件
    phase1_suites = []
    if PHASE1_TESTS_AVAILABLE:
        phase1_suites = [
            ("增强版数据导入引擎集成测试", run_integration_tests),
            ("AI预测服务集成测试", run_ai_services_tests),
            ("监控和缓存系统集成测试", run_monitoring_cache_tests),
            ("分布式和自动调优集成测试", run_distributed_autotuner_tests),
            ("数据质量监控集成测试", run_data_quality_tests)
        ]

    # 定义阶段二测试套件
    phase2_suites = []
    if PHASE2_TESTS_AVAILABLE:
        phase2_suites = [
            ("智能配置管理系统测试", "tests/test_intelligent_config_manager.py"),
            ("增强风险监控系统测试", "tests/test_enhanced_risk_monitor.py"),
            ("增强性能桥接系统测试", "tests/test_enhanced_performance_bridge.py")
        ]

    # 定义阶段三测试套件
    phase3_suites = []
    if PHASE3_TESTS_AVAILABLE:
        phase3_suites = [
            ("增强版事件总线测试", "tests/test_enhanced_event_bus.py"),
            ("增强版异步任务管理器测试", "tests/test_enhanced_async_manager.py"),
            ("增强版分布式服务测试", "tests/test_enhanced_distributed_service.py")
        ]

    # 运行所有测试
    test_results = []
    overall_start_time = time.time()

    # 运行阶段一测试
    if phase1_suites:
        print(f"\n🚀 开始运行阶段一集成测试 ({len(phase1_suites)} 个套件)")
        for test_name, test_function in phase1_suites:
            success, duration, error = run_test_suite(test_name, test_function)

            test_results.append({
                'name': test_name,
                'success': success,
                'duration': duration,
                'error': error,
                'phase': 'Phase 1'
            })

    # 运行阶段二测试
    if phase2_suites:
        print(f"\n🧠 开始运行阶段二智能化增强测试 ({len(phase2_suites)} 个套件)")
        for test_name, test_file_path in phase2_suites:
            success, duration, error = run_phase2_pytest_suite(test_file_path, test_name)

            test_results.append({
                'name': test_name,
                'success': success,
                'duration': duration,
                'error': error,
                'phase': 'Phase 2'
            })

    # 运行阶段三测试
    if phase3_suites:
        print(f"\n🚌 开始运行阶段三架构增强测试 ({len(phase3_suites)} 个套件)")
        for test_name, test_file_path in phase3_suites:
            success, duration, error = run_phase2_pytest_suite(test_file_path, test_name)

            test_results.append({
                'name': test_name,
                'success': success,
                'duration': duration,
                'error': error,
                'phase': 'Phase 3'
            })

    overall_end_time = time.time()
    overall_duration = overall_end_time - overall_start_time

    # 生成测试报告
    report, report_file = generate_test_report(test_results)

    # 打印摘要
    print_summary(test_results)

    print(f"\n📄 详细测试报告已保存至: {report_file}")
    print(f"⏱️ 总体测试耗时: {overall_duration:.2f}秒")

    # 返回整体测试结果
    all_passed = all(r['success'] for r in test_results)
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n💥 测试运行遇到未预期的异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
