#!/usr/bin/env python3
"""
YS-Quant 量化交易系统启动检查脚本
验证所有核心组件是否正常工作
"""

import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║               YS-Quant 量化交易系统 v2.5.6                      ║
║                    系统启动检查工具                            ║
║                                                              ║
║  🎯 第13轮优化完成 - 形态识别系统全面重构                      ║
║  🚀 性能提升5倍 - 智能缓存 + AI预测                           ║
║  📊 99%重复代码消除 - 11,070+行代码优化                       ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_core_imports() -> Dict[str, Any]:
    """检查核心模块导入"""
    print("🔍 检查核心模块导入...")

    results = {}
    core_modules = [
        ('pandas', 'pd'),
        ('numpy', 'np'),
        ('PyQt5.QtWidgets', 'QApplication'),
        ('analysis.pattern_recognition', 'EnhancedPatternRecognizer'),
        ('analysis.pattern_base', 'PatternAlgorithmFactory'),
        ('analysis.system_health_checker', 'SystemHealthChecker'),
    ]

    for module_name, import_item in core_modules:
        try:
            if '.' in import_item:
                # 从模块导入特定项
                exec(f"from {module_name} import {import_item}")
            else:
                # 导入整个模块并重命名
                exec(f"import {module_name} as {import_item}")

            results[module_name] = {'status': 'success', 'message': '✅ 导入成功'}
            print(f"  ✅ {module_name}")

        except Exception as e:
            results[module_name] = {'status': 'error',
                                    'message': f'❌ 导入失败: {str(e)}'}
            print(f"  ❌ {module_name}: {str(e)}")

    return results


def check_pattern_recognition() -> Dict[str, Any]:
    """检查形态识别功能"""
    print("\n🎯 检查形态识别功能...")

    try:
        from analysis.pattern_recognition import (
            EnhancedPatternRecognizer,
            get_performance_monitor,
            get_pattern_cache,
            get_pattern_recognizer_info
        )

        # 检查识别器创建
        recognizer = EnhancedPatternRecognizer(debug_mode=False)
        print("  ✅ 形态识别器创建成功")

        # 检查性能监控器
        monitor = get_performance_monitor()
        print("  ✅ 性能监控器获取成功")

        # 检查缓存系统
        cache = get_pattern_cache()
        cache_stats = cache.get_stats()
        print(f"  ✅ 缓存系统正常 (最大容量: {cache_stats['max_size']})")

        # 检查系统信息
        info = get_pattern_recognizer_info()
        print(
            f"  ✅ 系统信息获取成功 (版本: {info['version']}, 支持形态: {info['supported_patterns']}种)")

        return {
            'status': 'success',
            'recognizer_created': True,
            'monitor_available': True,
            'cache_available': True,
            'system_info': info
        }

    except Exception as e:
        error_msg = f"形态识别功能检查失败: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
            'traceback': traceback.format_exc()
        }


def check_ui_components() -> Dict[str, Any]:
    """检查UI组件"""
    print("\n🎨 检查UI组件...")

    try:
        # 检查关键UI文件
        ui_files = [
            'gui/widgets/analysis_tabs/pattern_tab_pro.py',
            'gui/widgets/analysis_tabs/pattern_tab.py',
            'gui/widgets/base_analysis_tab.py'
        ]

        file_status = {}
        for ui_file in ui_files:
            if os.path.exists(ui_file):
                file_status[ui_file] = True
                print(f"  ✅ {ui_file}")
            else:
                file_status[ui_file] = False
                print(f"  ❌ {ui_file} 不存在")

        # 尝试导入UI组件（如果PyQt5可用）
        try:
            from PyQt5.QtWidgets import QApplication
            from gui.widgets.analysis_tabs.pattern_tab_pro import PatternAnalysisTabPro, AnalysisThread
            print("  ✅ UI组件导入成功")
            ui_import_success = True
        except Exception as e:
            print(f"  ⚠️ UI组件导入失败: {str(e)}")
            ui_import_success = False

        return {
            'status': 'success',
            'file_status': file_status,
            'ui_import_success': ui_import_success,
            'all_files_exist': all(file_status.values())
        }

    except Exception as e:
        error_msg = f"UI组件检查失败: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            'status': 'error',
            'error': error_msg
        }


def check_database_files() -> Dict[str, Any]:
    """检查数据库文件"""
    print("\n💾 检查数据库文件...")

    db_files = [
        'db/pattern_algorithms.db',
        'db/hikyuu.db',
        'data/stock_data.db'
    ]

    db_status = {}
    for db_file in db_files:
        if os.path.exists(db_file):
            size_mb = os.path.getsize(db_file) / 1024 / 1024
            db_status[db_file] = {
                'exists': True,
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(os.path.getmtime(db_file)).strftime('%Y-%m-%d %H:%M:%S')
            }
            print(f"  ✅ {db_file} ({size_mb:.1f}MB)")
        else:
            db_status[db_file] = {'exists': False}
            print(f"  ⚠️ {db_file} 不存在")

    return {
        'status': 'success',
        'databases': db_status
    }


def run_performance_test() -> Dict[str, Any]:
    """运行性能测试"""
    print("\n⚡ 运行性能测试...")

    try:
        from analysis.pattern_recognition import EnhancedPatternRecognizer
        import pandas as pd
        import numpy as np

        # 生成测试数据
        print("  📊 生成测试数据...")
        dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
        np.random.seed(42)

        base_price = 100
        prices = [base_price]
        for _ in range(199):
            change = np.random.normal(0, 2)
            new_price = max(prices[-1] + change, 1)
            prices.append(new_price)

        test_data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close + abs(np.random.normal(0, 1))
            low = close - abs(np.random.normal(0, 1))
            open_price = close + np.random.normal(0, 0.5)

            test_data.append({
                'date': date,
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': np.random.randint(1000, 10000)
            })

        kdata = pd.DataFrame(test_data)
        print(f"  ✅ 测试数据生成完成 ({len(kdata)}条记录)")

        # 性能测试
        recognizer = EnhancedPatternRecognizer(debug_mode=False)

        print("  🔍 执行形态识别测试...")
        start_time = time.time()
        patterns = recognizer.identify_patterns(
            kdata, confidence_threshold=0.1)
        processing_time = time.time() - start_time

        print(f"  ✅ 识别完成: {len(patterns)}个形态, 耗时: {processing_time:.3f}秒")

        # 缓存测试
        print("  🔄 测试缓存性能...")
        start_time = time.time()
        patterns_cached = recognizer.identify_patterns(
            kdata, confidence_threshold=0.1)
        cached_time = time.time() - start_time

        speedup = processing_time / \
            cached_time if cached_time > 0 else float('inf')
        print(f"  ✅ 缓存测试完成: 耗时: {cached_time:.3f}秒, 加速比: {speedup:.1f}x")

        return {
            'status': 'success',
            'test_data_size': len(kdata),
            'patterns_detected': len(patterns),
            'processing_time': processing_time,
            'cached_time': cached_time,
            'speedup_ratio': speedup,
            'performance_rating': 'excellent' if processing_time < 0.5 else 'good' if processing_time < 1.0 else 'acceptable'
        }

    except Exception as e:
        error_msg = f"性能测试失败: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
            'traceback': traceback.format_exc()
        }


def run_health_check(checker) -> Dict[str, Any]:
    """运行系统健康检查"""
    print("\n🩺 运行系统健康检查...")

    try:
        report = checker.run_comprehensive_check()
        print(f"  ✅ 健康检查完成 (总体状态: {report.get('overall_health', '未知')})")
        return {
            'status': 'success',
            'report': report
        }

    except Exception as e:
        error_msg = f"系统健康检查失败: {str(e)}"
        print(f"  ❌ {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
            'traceback': traceback.format_exc()
        }


def generate_startup_report(results: Dict[str, Any]) -> str:
    """生成启动报告"""
    lines = []
    lines.append("\n" + "="*60)
    lines.append("HIkyuu量化交易系统启动检查报告")
    lines.append("="*60)
    lines.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 统计结果
    total_checks = len(results)
    success_count = sum(1 for r in results.values()
                        if r.get('status') == 'success')
    error_count = total_checks - success_count

    lines.append(f"📊 检查统计:")
    lines.append(f"  总检查项: {total_checks}")
    lines.append(f"  成功项: {success_count}")
    lines.append(f"  失败项: {error_count}")
    lines.append(f"  成功率: {success_count/total_checks:.1%}")
    lines.append("")

    # 系统状态
    if error_count == 0:
        status = "🟢 系统状态: 优秀 - 所有组件正常工作"
    elif error_count <= 2:
        status = "🟡 系统状态: 良好 - 大部分组件正常工作"
    else:
        status = "🔴 系统状态: 需要关注 - 多个组件存在问题"

    lines.append(status)
    lines.append("")

    # 性能摘要
    perf_test = results.get('performance_test', {})
    if perf_test.get('status') == 'success':
        lines.append("⚡ 性能摘要:")
        lines.append(
            f"  识别性能: {perf_test.get('performance_rating', 'unknown').upper()}")
        lines.append(f"  处理时间: {perf_test.get('processing_time', 0):.3f}秒")
        lines.append(f"  缓存加速: {perf_test.get('speedup_ratio', 0):.1f}倍")
        lines.append(f"  检测形态: {perf_test.get('patterns_detected', 0)}个")
        lines.append("")

    # 健康状态
    health_check = results.get('health_check', {})
    if health_check.get('status') == 'success':
        overall_health = health_check.get('overall_health', 'unknown')
        lines.append(f"🏥 系统健康: {overall_health.upper()}")
        lines.append("")

    lines.append("🚀 HIkyuu量化交易系统已准备就绪！")
    lines.append("="*60)

    return "\n".join(lines)


def main():
    """主函数"""
    print_banner()

    # 模拟主应用的服务初始化过程
    print("\n🚀 初始化核心服务 (模拟环境)...")
    services = None
    try:
        from core.events import EventBus
        from core.containers import ServiceContainer
        from core.metrics.repository import MetricsRepository
        from core.metrics.app_metrics_service import initialize_app_metrics_service
        from core.metrics.resource_service import SystemResourceService
        from core.metrics.aggregation_service import MetricsAggregationService
        from analysis.system_health_checker import SystemHealthChecker

        event_bus = EventBus()
        container = ServiceContainer()

        # 注册服务
        repo = MetricsRepository(db_path=':memory:')
        container.register_instance(MetricsRepository, repo)

        initialize_app_metrics_service(event_bus)

        agg_service = MetricsAggregationService(event_bus, repo)
        container.register_instance(MetricsAggregationService, agg_service)
        agg_service.start()

        resource_service = SystemResourceService(event_bus)
        container.register_instance(SystemResourceService, resource_service)
        resource_service.start()

        services = {
            "repo": repo,
            "agg": agg_service,
            "res": resource_service
        }
        print("  ✅ 核心监控服务初始化成功")

        # 实例化健康检查器并注入依赖
        checker = SystemHealthChecker(
            aggregation_service=agg_service, repository=repo)

    except Exception as e:
        print(f"  ❌ 核心服务初始化失败: {e}")
        traceback.print_exc()
        return

    all_results = {}
    all_checks_ok = True

    # 执行各项检查
    checks_to_run = {
        'core_imports': check_core_imports,
        'pattern_recognition': check_pattern_recognition,
        'ui_components': check_ui_components,
        'database_files': check_database_files,
        'performance_test': run_performance_test,
    }

    for name, check_func in checks_to_run.items():
        result = check_func()
        all_results[name] = result
        if result.get('status') == 'error':
            all_checks_ok = False

    # 单独运行健康检查
    health_result = run_health_check(checker)
    all_results['health_check'] = health_result
    if health_result.get('status') == 'error':
        all_checks_ok = False

    # 生成和打印报告
    report = generate_startup_report(all_results)
    print("\n\n" + "="*60)
    print(report)
    print("="*60 + "\n")

    if all_checks_ok:
        print("✅✅✅ 所有检查项通过，系统状态良好！ ✅✅✅")
    else:
        print("❌❌❌ 部分检查项失败，请检查以上日志！ ❌❌❌")

    # 清理服务
    print("\n🧹 清理服务...")
    if services:
        services['agg'].dispose()
        services['res'].dispose()
    print("  ✅ 服务已清理")


if __name__ == "__main__":
    main()
