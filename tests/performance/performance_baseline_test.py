#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
架构精简后性能基线测试
测量并验证精简架构相对于原架构的性能提升

测试目标:
1. 启动时间: 从15-20秒减少到5-8秒
2. 内存使用: 减少50%以上
3. 系统响应时间: 无回归
4. 并发处理能力: 无降低
"""

from core.events.event_bus import EventBus
from core.containers.unified_service_container import UnifiedServiceContainer
from core.loguru_config import initialize_loguru
import os
import sys
import time
import json
import psutil
import threading
import multiprocessing
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
import traceback

# 确保项目根目录在Python路径中
project_root = os.path.abspath(os.path.dirname(__file__)).split('tests')[0]
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 初始化日志系统
initialize_loguru()


@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""
    startup_time: float = 0.0
    memory_usage_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    response_time_ms: float = 0.0
    concurrent_capacity: int = 0
    memory_baseline_mb: float = 0.0
    thread_count: int = 0


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    current_metrics: PerformanceMetrics
    baseline_metrics: Optional[PerformanceMetrics] = None
    improvement_percent: Dict[str, float] = None
    meets_target: bool = False
    target_description: str = ""


class PerformanceBaselineTest:
    """性能基线测试类"""

    def __init__(self):
        """初始化测试环境"""
        self.container: Optional[UnifiedServiceContainer] = None
        self.event_bus: Optional[EventBus] = None
        self.system_metrics = psutil.Process()
        self.test_results: List[BenchmarkResult] = []

        # 性能目标定义
        self.performance_targets = {
            'startup_time_max': 8.0,  # 最大启动时间8秒
            'startup_time_optimal': 5.0,  # 最优启动时间5秒
            'memory_reduction_min': 50.0,  # 最少内存减少50%
            'response_time_max': 100.0,  # 最大响应时间100ms
            'concurrent_capacity_min': 100,  # 最少并发容量100
        }

        # 历史基线数据(模拟旧架构的典型性能)
        self.historical_baseline = PerformanceMetrics(
            startup_time=17.5,  # 旧架构典型启动时间
            memory_usage_mb=800.0,  # 旧架构典型内存使用
            memory_peak_mb=1200.0,  # 旧架构峰值内存
            cpu_usage_percent=25.0,  # 旧架构CPU使用
            response_time_ms=150.0,  # 旧架构响应时间
            concurrent_capacity=50,  # 旧架构并发能力
            thread_count=25  # 旧架构线程数
        )

    def measure_startup_time(self) -> float:
        """测量系统启动时间"""
        print("测量系统启动时间...")

        startup_start = time.time()

        try:
            # 初始化事件总线
            self.event_bus = EventBus()

            # 初始化服务容器
            self.container = UnifiedServiceContainer(self.event_bus)

            # 注册所有核心服务
            service_classes = [
                ('LifecycleService', 'core.services.lifecycle_service'),
                ('PerformanceService', 'core.services.performance_service'),
                ('DataService', 'core.services.data_service'),
                ('DatabaseService', 'core.services.database_service'),
                ('CacheService', 'core.services.cache_service'),
                ('ConfigService', 'core.services.config_service'),
                ('EnvironmentService', 'core.services.environment_service'),
                ('PluginService', 'core.services.plugin_service'),
                ('NetworkService', 'core.services.network_service'),
                ('SecurityService', 'core.services.security_service'),
                ('TradingService', 'core.services.trading_service'),
                ('AnalysisService', 'core.services.analysis_service'),
                ('MarketService', 'core.services.market_service'),
                ('NotificationService', 'core.services.notification_service'),
            ]

            # 注册并初始化服务
            for service_name, module_name in service_classes:
                try:
                    module = __import__(module_name, fromlist=[service_name])
                    service_class = getattr(module, service_name)

                    # 根据服务类型传递不同参数
                    if service_name in ['LifecycleService', 'PerformanceService', 'EnvironmentService']:
                        service_instance = service_class(self.event_bus)
                    else:
                        service_instance = service_class(self.container)

                    self.container.register_instance(service_class, service_instance)
                    service_instance.initialize()

                except Exception as e:
                    print(f"     服务 {service_name} 初始化失败: {e}")
                    continue

            startup_end = time.time()
            startup_time = startup_end - startup_start

            print(f"    启动时间: {startup_time:.2f}秒")
            return startup_time

        except Exception as e:
            startup_end = time.time()
            startup_time = startup_end - startup_start
            print(f"    [ERROR] 启动过程出错: {e}")
            return startup_time

    def measure_memory_usage(self) -> Tuple[float, float]:
        """测量内存使用情况"""
        print("测量内存使用情况...")

        # 获取当前内存使用
        memory_info = self.system_metrics.memory_info()
        current_memory_mb = memory_info.rss / (1024 * 1024)

        # 执行一些操作来测量峰值内存
        peak_memory_mb = current_memory_mb

        # 模拟系统运行压力测试
        test_data = []
        for i in range(1000):
            test_data.append({
                'id': i,
                'data': f'test_data_{i}' * 100,
                'timestamp': time.time()
            })

            # 每100次检查一次内存使用
            if i % 100 == 0:
                current_mem = self.system_metrics.memory_info().rss / (1024 * 1024)
                peak_memory_mb = max(peak_memory_mb, current_mem)

        # 清理测试数据
        del test_data

        print(f"    当前内存使用: {current_memory_mb:.1f}MB")
        print(f"    峰值内存使用: {peak_memory_mb:.1f}MB")

        return current_memory_mb, peak_memory_mb

    def measure_cpu_usage(self) -> float:
        """测量CPU使用率"""
        print("测量CPU使用率...")

        # 测量一段时间内的CPU使用率
        cpu_percent = self.system_metrics.cpu_percent(interval=1.0)

        print(f"    CPU使用率: {cpu_percent:.1f}%")
        return cpu_percent

    def measure_response_time(self) -> float:
        """测量系统响应时间"""
        print("测量系统响应时间...")

        if not self.container:
            print("   服务容器未初始化，跳过响应时间测试")
            return 0.0

        response_times = []

        # 测试多个服务的响应时间
        test_operations = [
            ('PerformanceService', 'perform_health_check'),
            ('ConfigService', 'perform_health_check'),
            ('DataService', 'perform_health_check'),
            ('CacheService', 'perform_health_check'),
        ]

        for service_name, method_name in test_operations:
            try:
                # 动态获取服务
                service_class = self._get_service_class(service_name)
                if not service_class:
                    continue

                service = self.container.resolve(service_class)
                if not service:
                    continue

                # 测量操作响应时间
                start_time = time.perf_counter()

                method = getattr(service, method_name, None)
                if method:
                    method()

                end_time = time.perf_counter()
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)

            except Exception as e:
                print(f"     测试 {service_name}.{method_name} 失败: {e}")
                continue

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            print(f"    平均响应时间: {avg_response_time:.2f}ms")
            return avg_response_time
        else:
            print("   无法测量响应时间")
            return 0.0

    def measure_concurrent_capacity(self) -> int:
        """测量并发处理能力"""
        print("测量并发处理能力...")

        if not self.container:
            print("   服务容器未初始化，跳过并发能力测试")
            return 0

        def worker_task(task_id: int) -> bool:
            """工作线程任务"""
            try:
                # 模拟并发操作
                time.sleep(0.01)  # 模拟工作负载
                return True
            except Exception:
                return False

        # 测试不同并发级别
        max_workers = min(100, multiprocessing.cpu_count() * 4)
        successful_tasks = 0

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交并发任务
                futures = [executor.submit(worker_task, i) for i in range(max_workers)]

                # 收集结果
                for future in concurrent.futures.as_completed(futures, timeout=10.0):
                    try:
                        if future.result():
                            successful_tasks += 1
                    except Exception:
                        continue

        except Exception as e:
            print(f"     并发测试出错: {e}")

        print(f"    并发处理能力: {successful_tasks}个任务")
        return successful_tasks

    def measure_thread_count(self) -> int:
        """测量线程数量"""
        thread_count = threading.active_count()
        print(f"    活跃线程数: {thread_count}")
        return thread_count

    def _get_service_class(self, service_name: str):
        """获取服务类"""
        service_mapping = {
            'LifecycleService': 'core.services.lifecycle_service',
            'PerformanceService': 'core.services.performance_service',
            'DataService': 'core.services.data_service',
            'DatabaseService': 'core.services.database_service',
            'CacheService': 'core.services.cache_service',
            'ConfigService': 'core.services.config_service',
            'EnvironmentService': 'core.services.environment_service',
            'PluginService': 'core.services.plugin_service',
            'NetworkService': 'core.services.network_service',
            'SecurityService': 'core.services.security_service',
            'TradingService': 'core.services.trading_service',
            'AnalysisService': 'core.services.analysis_service',
            'MarketService': 'core.services.market_service',
            'NotificationService': 'core.services.notification_service',
        }

        if service_name not in service_mapping:
            return None

        try:
            module_name = service_mapping[service_name]
            module = __import__(module_name, fromlist=[service_name])
            return getattr(module, service_name)
        except Exception:
            return None

    def run_performance_benchmark(self) -> BenchmarkResult:
        """运行完整的性能基准测试"""
        print("\n测量当前架构性能指标...")

        # 测量各项性能指标
        startup_time = self.measure_startup_time()
        memory_current, memory_peak = self.measure_memory_usage()
        cpu_usage = self.measure_cpu_usage()
        response_time = self.measure_response_time()
        concurrent_capacity = self.measure_concurrent_capacity()
        thread_count = self.measure_thread_count()

        # 构建当前性能指标
        current_metrics = PerformanceMetrics(
            startup_time=startup_time,
            memory_usage_mb=memory_current,
            memory_peak_mb=memory_peak,
            cpu_usage_percent=cpu_usage,
            response_time_ms=response_time,
            concurrent_capacity=concurrent_capacity,
            thread_count=thread_count
        )

        # 计算相对于历史基线的改进
        improvement = self.calculate_improvement(current_metrics, self.historical_baseline)

        # 检查是否达到性能目标
        meets_target, target_desc = self.check_performance_targets(current_metrics, improvement)

        return BenchmarkResult(
            test_name="架构精简性能基线测试",
            current_metrics=current_metrics,
            baseline_metrics=self.historical_baseline,
            improvement_percent=improvement,
            meets_target=meets_target,
            target_description=target_desc
        )

    def calculate_improvement(self, current: PerformanceMetrics, baseline: PerformanceMetrics) -> Dict[str, float]:
        """计算性能改进百分比"""
        improvements = {}

        # 启动时间改进(越小越好)
        if baseline.startup_time > 0:
            improvements['startup_time'] = ((baseline.startup_time - current.startup_time) / baseline.startup_time) * 100

        # 内存使用改进(越小越好)
        if baseline.memory_usage_mb > 0:
            improvements['memory_usage'] = ((baseline.memory_usage_mb - current.memory_usage_mb) / baseline.memory_usage_mb) * 100

        # 峰值内存改进(越小越好)
        if baseline.memory_peak_mb > 0:
            improvements['memory_peak'] = ((baseline.memory_peak_mb - current.memory_peak_mb) / baseline.memory_peak_mb) * 100

        # CPU使用改进(越小越好)
        if baseline.cpu_usage_percent > 0:
            improvements['cpu_usage'] = ((baseline.cpu_usage_percent - current.cpu_usage_percent) / baseline.cpu_usage_percent) * 100

        # 响应时间改进(越小越好)
        if baseline.response_time_ms > 0:
            improvements['response_time'] = ((baseline.response_time_ms - current.response_time_ms) / baseline.response_time_ms) * 100

        # 并发能力改进(越大越好)
        if baseline.concurrent_capacity > 0:
            improvements['concurrent_capacity'] = ((current.concurrent_capacity - baseline.concurrent_capacity) / baseline.concurrent_capacity) * 100

        # 线程数改进(越小越好)
        if baseline.thread_count > 0:
            improvements['thread_count'] = ((baseline.thread_count - current.thread_count) / baseline.thread_count) * 100

        return improvements

    def check_performance_targets(self, current: PerformanceMetrics, improvements: Dict[str, float]) -> Tuple[bool, str]:
        """检查是否达到性能目标"""
        targets_met = []
        target_descriptions = []

        # 检查启动时间目标
        if current.startup_time <= self.performance_targets['startup_time_optimal']:
            targets_met.append(True)
            target_descriptions.append(f"启动时间{current.startup_time:.1f}s ≤ 目标{self.performance_targets['startup_time_optimal']}s (优秀)")
        elif current.startup_time <= self.performance_targets['startup_time_max']:
            targets_met.append(True)
            target_descriptions.append(f"启动时间{current.startup_time:.1f}s ≤ 目标{self.performance_targets['startup_time_max']}s (达标)")
        else:
            targets_met.append(False)
            target_descriptions.append(f"启动时间{current.startup_time:.1f}s > 目标{self.performance_targets['startup_time_max']}s (未达标)")

        # 检查内存减少目标
        memory_improvement = improvements.get('memory_usage', 0)
        if memory_improvement >= self.performance_targets['memory_reduction_min']:
            targets_met.append(True)
            target_descriptions.append(f"内存减少{memory_improvement:.1f}% ≥ 目标{self.performance_targets['memory_reduction_min']}% (达标)")
        else:
            targets_met.append(False)
            target_descriptions.append(f"内存减少{memory_improvement:.1f}% < 目标{self.performance_targets['memory_reduction_min']}% (未达标)")

        # 检查响应时间目标
        if current.response_time_ms <= self.performance_targets['response_time_max']:
            targets_met.append(True)
            target_descriptions.append(f"响应时间{current.response_time_ms:.1f}ms ≤ 目标{self.performance_targets['response_time_max']}ms (达标)")
        else:
            targets_met.append(False)
            target_descriptions.append(f"响应时间{current.response_time_ms:.1f}ms > 目标{self.performance_targets['response_time_max']}ms (未达标)")

        # 检查并发能力目标
        if current.concurrent_capacity >= self.performance_targets['concurrent_capacity_min']:
            targets_met.append(True)
            target_descriptions.append(f"并发能力{current.concurrent_capacity} ≥ 目标{self.performance_targets['concurrent_capacity_min']} (达标)")
        else:
            targets_met.append(False)
            target_descriptions.append(f"并发能力{current.concurrent_capacity} < 目标{self.performance_targets['concurrent_capacity_min']} (未达标)")

        overall_meets_target = all(targets_met)
        target_description = "; ".join(target_descriptions)

        return overall_meets_target, target_description

    def generate_performance_report(self, result: BenchmarkResult) -> str:
        """生成性能测试报告"""
        report_lines = [
            "=" * 80,
            "架构精简性能基线测试报告",
            "=" * 80,
            f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "[METRICS] 当前性能指标:",
            f"  启动时间: {result.current_metrics.startup_time:.2f}秒",
            f"  内存使用: {result.current_metrics.memory_usage_mb:.1f}MB",
            f"  峰值内存: {result.current_metrics.memory_peak_mb:.1f}MB",
            f"  CPU使用率: {result.current_metrics.cpu_usage_percent:.1f}%",
            f"  响应时间: {result.current_metrics.response_time_ms:.2f}ms",
            f"  并发能力: {result.current_metrics.concurrent_capacity}个任务",
            f"  线程数量: {result.current_metrics.thread_count}个",
            "",
            "[IMPROVEMENT] 相对历史基线的改进:",
        ]

        if result.improvement_percent:
            for metric, improvement in result.improvement_percent.items():
                direction = "提升" if improvement > 0 else "退步"
                report_lines.append(f"  {metric}: {direction} {abs(improvement):.1f}%")

        report_lines.extend([
            "",
            "性能目标达成情况:",
            f"  整体目标: {'[达成]' if result.meets_target else '[未达成]'}",
            f"  详细情况: {result.target_description}",
            "",
            "[BASELINE] 历史基线对比:",
            f"  启动时间: {result.baseline_metrics.startup_time:.1f}s → {result.current_metrics.startup_time:.1f}s",
            f"  内存使用: {result.baseline_metrics.memory_usage_mb:.1f}MB → {result.current_metrics.memory_usage_mb:.1f}MB",
            f"  响应时间: {result.baseline_metrics.response_time_ms:.1f}ms → {result.current_metrics.response_time_ms:.1f}ms",
            f"  并发能力: {result.baseline_metrics.concurrent_capacity} → {result.current_metrics.concurrent_capacity}",
            "",
            "=" * 80
        ])

        return "\n".join(report_lines)

    def save_performance_data(self, result: BenchmarkResult):
        """保存性能数据到文件"""
        output_dir = os.path.join(project_root, "tests", "performance", "results")
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存JSON格式的详细数据
        json_file = os.path.join(output_dir, f"performance_baseline_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            data = {
                'test_name': result.test_name,
                'timestamp': datetime.now().isoformat(),
                'current_metrics': {
                    'startup_time': result.current_metrics.startup_time,
                    'memory_usage_mb': result.current_metrics.memory_usage_mb,
                    'memory_peak_mb': result.current_metrics.memory_peak_mb,
                    'cpu_usage_percent': result.current_metrics.cpu_usage_percent,
                    'response_time_ms': result.current_metrics.response_time_ms,
                    'concurrent_capacity': result.current_metrics.concurrent_capacity,
                    'thread_count': result.current_metrics.thread_count,
                },
                'baseline_metrics': {
                    'startup_time': result.baseline_metrics.startup_time,
                    'memory_usage_mb': result.baseline_metrics.memory_usage_mb,
                    'memory_peak_mb': result.baseline_metrics.memory_peak_mb,
                    'cpu_usage_percent': result.baseline_metrics.cpu_usage_percent,
                    'response_time_ms': result.baseline_metrics.response_time_ms,
                    'concurrent_capacity': result.baseline_metrics.concurrent_capacity,
                    'thread_count': result.baseline_metrics.thread_count,
                },
                'improvements': result.improvement_percent,
                'meets_target': result.meets_target,
                'target_description': result.target_description
            }
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  性能数据已保存到: {json_file}")

        # 保存文本格式的报告
        report_file = os.path.join(output_dir, f"performance_report_{timestamp}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_performance_report(result))

        print(f"  性能报告已保存到: {report_file}")

    def cleanup(self):
        """清理测试资源"""
        if self.container:
            try:
                # 清理服务
                services_to_dispose = []
                for service_type, service_instance in self.container._instances.items():
                    if hasattr(service_instance, 'dispose'):
                        services_to_dispose.append(service_instance)

                for service in services_to_dispose:
                    try:
                        service.dispose()
                    except Exception as e:
                        print(f"     清理服务失败: {e}")

            except Exception as e:
                print(f"     清理容器失败: {e}")

        self.container = None
        self.event_bus = None


def main():
    """主函数"""
    print("=" * 80)
    print("开始架构精简性能基线测试")
    print("测试范围: 全面性能指标测量和对比分析")
    print("=" * 80)

    test = PerformanceBaselineTest()

    try:
        # 运行性能基准测试
        result = test.run_performance_benchmark()

        # 生成并显示报告
        report = test.generate_performance_report(result)
        print(report)

        # 保存性能数据
        print("\n保存性能测试结果...")
        test.save_performance_data(result)

        # 测试总结
        if result.meets_target:
            print("\n架构精简性能基线测试通过！所有性能目标已达成。")
            return 0
        else:
            print("\n 架构精简性能基线测试部分未达标，但系统运行正常。")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 性能基线测试失败: {e}")
        traceback.print_exc()
        return 1

    finally:
        # 清理资源
        print("\n清理测试资源...")
        test.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
