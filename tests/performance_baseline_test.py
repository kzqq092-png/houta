#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HIkyuu-UI 系统性能基线测试

测试系统各个关键组件的性能表现，建立性能基线。
"""

import sys
import os
import time
import psutil
import threading
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入测试目标组件
try:
    from core.performance.unified_monitor import UnifiedPerformanceMonitor, get_performance_monitor
    from core.performance.cache_manager import MultiLevelCacheManager, CacheLevel
    from core.importdata.import_execution_engine import DataImportExecutionEngine
    from core.services.unified_data_manager import UnifiedDataManager
    from core.services.ai_prediction_service import AIPredictionService
    from core.risk_monitoring.enhanced_risk_monitor import EnhancedRiskMonitor
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"部分组件不可用: {e}")
    COMPONENTS_AVAILABLE = False


class PerformanceBaseline:
    """性能基线测试器"""

    def __init__(self):
        self.results = {}
        self.start_time = None
        self.system_baseline = {}

    def get_system_baseline(self) -> Dict[str, float]:
        """获取系统基线性能指标"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"获取系统基线失败: {e}")
            return {}

    def test_cache_performance(self) -> Dict[str, Any]:
        """测试缓存系统性能"""
        logger.info("🔄 开始缓存性能测试...")

        try:
            # 创建缓存管理器
            cache_config = {
                'levels': [CacheLevel.MEMORY, CacheLevel.DISK],
                'default_ttl_minutes': 30,
                'memory': {'max_size_mb': 100},
                'disk': {'cache_dir': 'test_cache', 'max_size_mb': 200}
            }
            cache_manager = MultiLevelCacheManager(cache_config)

            # 测试数据
            test_data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

            # 写入性能测试
            write_times = []
            for key, value in test_data.items():
                start = time.perf_counter()
                cache_manager.set(key, value)
                write_times.append(time.perf_counter() - start)

            # 读取性能测试
            read_times = []
            for key in test_data.keys():
                start = time.perf_counter()
                cache_manager.get(key)
                read_times.append(time.perf_counter() - start)

            # 统计信息
            stats = cache_manager.get_statistics()

            return {
                'write_avg_ms': statistics.mean(write_times) * 1000,
                'write_p95_ms': statistics.quantiles(write_times, n=20)[18] * 1000,
                'read_avg_ms': statistics.mean(read_times) * 1000,
                'read_p95_ms': statistics.quantiles(read_times, n=20)[18] * 1000,
                'cache_stats': stats,
                'test_items': len(test_data)
            }

        except Exception as e:
            logger.error(f"缓存性能测试失败: {e}")
            return {'error': str(e)}

    def test_data_manager_performance(self) -> Dict[str, Any]:
        """测试数据管理器性能"""
        logger.info("📊 开始数据管理器性能测试...")

        try:
            # 创建数据管理器
            data_manager = UnifiedDataManager()

            # 测试股票列表获取性能
            start = time.perf_counter()
            stock_list = data_manager.get_stock_list()
            stock_list_time = time.perf_counter() - start

            # 测试K线数据获取性能（如果有股票数据）
            kdata_times = []
            if not stock_list.empty and len(stock_list) > 0:
                test_stocks = stock_list.head(5)  # 测试前5只股票
                for _, stock in test_stocks.iterrows():
                    try:
                        start = time.perf_counter()
                        kdata = data_manager.get_kdata(stock['code'], 'D', 100)
                        kdata_times.append(time.perf_counter() - start)
                    except Exception:
                        continue

            return {
                'stock_list_time_ms': stock_list_time * 1000,
                'stock_count': len(stock_list),
                'kdata_avg_time_ms': statistics.mean(kdata_times) * 1000 if kdata_times else 0,
                'kdata_tests': len(kdata_times)
            }

        except Exception as e:
            logger.error(f"数据管理器性能测试失败: {e}")
            return {'error': str(e)}

    def test_ai_prediction_performance(self) -> Dict[str, Any]:
        """测试AI预测服务性能"""
        logger.info("🧠 开始AI预测服务性能测试...")

        try:
            ai_service = AIPredictionService()

            # 测试执行时间预测
            test_data = {
                'data_size': 1000,
                'complexity': 'medium',
                'system_load': 0.5
            }

            prediction_times = []
            for _ in range(10):  # 测试10次
                start = time.perf_counter()
                result = ai_service.predict_execution_time(test_data)
                prediction_times.append(time.perf_counter() - start)

            # 测试参数优化
            optimization_times = []
            for _ in range(5):  # 测试5次
                start = time.perf_counter()
                result = ai_service.optimize_parameters(test_data)
                optimization_times.append(time.perf_counter() - start)

            return {
                'prediction_avg_ms': statistics.mean(prediction_times) * 1000,
                'prediction_p95_ms': statistics.quantiles(prediction_times, n=20)[18] * 1000,
                'optimization_avg_ms': statistics.mean(optimization_times) * 1000,
                'optimization_p95_ms': statistics.quantiles(optimization_times, n=20)[18] * 1000,
                'prediction_tests': len(prediction_times),
                'optimization_tests': len(optimization_times)
            }

        except Exception as e:
            logger.error(f"AI预测服务性能测试失败: {e}")
            return {'error': str(e)}

    def test_performance_monitor_performance(self) -> Dict[str, Any]:
        """测试性能监控器性能"""
        logger.info("📈 开始性能监控器性能测试...")

        try:
            monitor = get_performance_monitor()

            # 测试指标记录性能
            record_times = []
            for i in range(1000):
                start = time.perf_counter()
                # 导入必需的枚举
                from core.performance.unified_monitor import PerformanceCategory, MetricType
                monitor.record_metric(
                    f"test_metric_{i % 10}",
                    i * 0.1,
                    PerformanceCategory.SYSTEM,
                    MetricType.GAUGE
                )
                record_times.append(time.perf_counter() - start)

            # 测试统计获取性能
            stats_times = []
            for _ in range(100):
                start = time.perf_counter()
                stats = monitor.get_statistics()
                stats_times.append(time.perf_counter() - start)

            return {
                'record_avg_ms': statistics.mean(record_times) * 1000,
                'record_p95_ms': statistics.quantiles(record_times, n=20)[18] * 1000,
                'stats_avg_ms': statistics.mean(stats_times) * 1000,
                'stats_p95_ms': statistics.quantiles(stats_times, n=20)[18] * 1000,
                'record_tests': len(record_times),
                'stats_tests': len(stats_times)
            }

        except Exception as e:
            logger.error(f"性能监控器性能测试失败: {e}")
            return {'error': str(e)}

    def test_risk_monitor_performance(self) -> Dict[str, Any]:
        """测试风险监控器性能"""
        logger.info("🛡️ 开始风险监控器性能测试...")

        try:
            risk_monitor = EnhancedRiskMonitor()

            # 测试风险评估性能
            test_data = {
                'portfolio_value': 1000000,
                'positions': [
                    {'symbol': 'TEST001', 'quantity': 1000, 'price': 10.5},
                    {'symbol': 'TEST002', 'quantity': 2000, 'price': 5.2},
                ]
            }

            assessment_times = []
            for _ in range(100):
                start = time.perf_counter()
                result = risk_monitor.assess_portfolio_risk(test_data)
                assessment_times.append(time.perf_counter() - start)

            # 测试风险规则检查性能
            rule_check_times = []
            for _ in range(100):
                start = time.perf_counter()
                result = risk_monitor.check_risk_rules(test_data)
                rule_check_times.append(time.perf_counter() - start)

            return {
                'assessment_avg_ms': statistics.mean(assessment_times) * 1000,
                'assessment_p95_ms': statistics.quantiles(assessment_times, n=20)[18] * 1000,
                'rule_check_avg_ms': statistics.mean(rule_check_times) * 1000,
                'rule_check_p95_ms': statistics.quantiles(rule_check_times, n=20)[18] * 1000,
                'assessment_tests': len(assessment_times),
                'rule_check_tests': len(rule_check_times)
            }

        except Exception as e:
            logger.error(f"风险监控器性能测试失败: {e}")
            return {'error': str(e)}

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行综合性能测试"""
        logger.info("🚀 开始综合性能基线测试...")

        if not COMPONENTS_AVAILABLE:
            logger.error("组件不可用，跳过性能测试")
            return {'error': '组件不可用'}

        self.start_time = datetime.now()

        # 获取系统基线
        self.system_baseline = self.get_system_baseline()
        logger.info(f"系统基线: {self.system_baseline}")

        # 运行各项测试
        test_results = {}

        # 1. 缓存性能测试
        test_results['cache'] = self.test_cache_performance()

        # 2. 数据管理器性能测试
        test_results['data_manager'] = self.test_data_manager_performance()

        # 3. AI预测服务性能测试
        test_results['ai_prediction'] = self.test_ai_prediction_performance()

        # 4. 性能监控器性能测试
        test_results['performance_monitor'] = self.test_performance_monitor_performance()

        # 5. 风险监控器性能测试
        test_results['risk_monitor'] = self.test_risk_monitor_performance()

        # 获取测试后的系统状态
        system_after = self.get_system_baseline()

        # 汇总结果
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        summary = {
            'test_start': self.start_time.isoformat(),
            'test_end': end_time.isoformat(),
            'total_duration_seconds': total_duration,
            'system_baseline': self.system_baseline,
            'system_after': system_after,
            'test_results': test_results,
            'performance_summary': self._generate_performance_summary(test_results)
        }

        return summary

    def _generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, str]:
        """生成性能总结"""
        summary = {}

        for component, results in test_results.items():
            if 'error' in results:
                summary[component] = f"❌ 测试失败: {results['error']}"
            else:
                # 根据不同组件生成不同的总结
                if component == 'cache':
                    avg_write = results.get('write_avg_ms', 0)
                    avg_read = results.get('read_avg_ms', 0)
                    if avg_write < 1 and avg_read < 1:
                        summary[component] = "✅ 优秀 (写入<1ms, 读取<1ms)"
                    elif avg_write < 5 and avg_read < 5:
                        summary[component] = "✅ 良好 (写入<5ms, 读取<5ms)"
                    else:
                        summary[component] = f"⚠️ 需优化 (写入{avg_write:.2f}ms, 读取{avg_read:.2f}ms)"

                elif component == 'data_manager':
                    stock_time = results.get('stock_list_time_ms', 0)
                    kdata_time = results.get('kdata_avg_time_ms', 0)
                    if stock_time < 100 and kdata_time < 200:
                        summary[component] = "✅ 优秀 (股票列表<100ms, K线<200ms)"
                    elif stock_time < 500 and kdata_time < 1000:
                        summary[component] = "✅ 良好 (响应时间合理)"
                    else:
                        summary[component] = f"⚠️ 需优化 (股票列表{stock_time:.0f}ms, K线{kdata_time:.0f}ms)"

                elif component == 'ai_prediction':
                    pred_time = results.get('prediction_avg_ms', 0)
                    opt_time = results.get('optimization_avg_ms', 0)
                    if pred_time < 50 and opt_time < 500:
                        summary[component] = "✅ 优秀 (预测<50ms, 优化<500ms)"
                    elif pred_time < 200 and opt_time < 2000:
                        summary[component] = "✅ 良好 (响应时间合理)"
                    else:
                        summary[component] = f"⚠️ 需优化 (预测{pred_time:.0f}ms, 优化{opt_time:.0f}ms)"

                else:
                    summary[component] = "✅ 测试完成"

        return summary


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("HIkyuu-UI 系统性能基线测试")
    logger.info("=" * 60)

    baseline_tester = PerformanceBaseline()
    results = baseline_tester.run_comprehensive_test()

    # 输出结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 性能测试结果汇总")
    logger.info("=" * 60)

    if 'error' in results:
        logger.error(f"测试失败: {results['error']}")
        return

    # 输出性能总结
    logger.info("\n🎯 性能评估:")
    for component, summary in results['performance_summary'].items():
        logger.info(f"  {component}: {summary}")

    # 输出系统资源使用
    logger.info(f"\n💻 系统资源:")
    baseline = results['system_baseline']
    after = results['system_after']
    logger.info(f"  CPU使用率: {baseline.get('cpu_usage', 0):.1f}% → {after.get('cpu_usage', 0):.1f}%")
    logger.info(f"  内存使用率: {baseline.get('memory_usage', 0):.1f}% → {after.get('memory_usage', 0):.1f}%")

    # 输出测试时长
    logger.info(f"\n⏱️ 测试耗时: {results['total_duration_seconds']:.2f}秒")

    logger.info("\n" + "=" * 60)
    logger.info("性能基线测试完成")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    main()
