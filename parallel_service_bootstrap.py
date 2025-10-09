#!/usr/bin/env python
"""
并行服务启动优化 - 保守实现

这是一个可选的优化模块，用于加速系统启动。
当前采用保守策略，仅在稳定性验证后启用。

使用方式:
1. 测试通过率达到90%+后
2. 修改main.py中的服务初始化部分
3. 调用此模块的parallel_bootstrap()函数
"""

from concurrent.futures import ThreadPoolExecutor, wait, as_completed
from typing import List, Type
import time
from loguru import logger


class ParallelServiceBootstrap:
    """并行服务启动器"""

    def __init__(self, container):
        """
        初始化并行启动器

        Args:
            container: 服务容器实例
        """
        self.container = container

        # 服务分组（按依赖关系）
        self.core_services = [
            # 核心基础服务（必须顺序启动）
            'ConfigService',
            'EnvironmentService',
            'DatabaseService',
            'CacheService',
        ]

        self.independent_services = [
            # 独立服务（可并行启动）
            'MarketService',
            'NotificationService',
            'SecurityService',
            'PerformanceService',
        ]

        self.business_services = [
            # 业务服务（依赖核心服务）
            'DataService',
            'PluginService',
            'NetworkService',
            'AnalysisService',
            'TradingService',
            'LifecycleService',
        ]

    def bootstrap_sequential(self) -> dict:
        """
        顺序启动（兼容模式）

        Returns:
            启动结果统计
        """
        logger.info("=== 顺序服务启动模式 ===")
        start_time = time.time()

        all_services = self.core_services + self.independent_services + self.business_services

        success_count = 0
        failed = []

        for service_name in all_services:
            try:
                service = self.container.resolve_by_name(service_name)
                service.initialize()
                success_count += 1
                logger.debug(f"✓ {service_name} 初始化成功")
            except Exception as e:
                failed.append((service_name, str(e)))
                logger.error(f"✗ {service_name} 初始化失败: {e}")

        elapsed = time.time() - start_time

        return {
            'mode': 'sequential',
            'total': len(all_services),
            'success': success_count,
            'failed': len(failed),
            'failed_services': failed,
            'elapsed_seconds': elapsed
        }

    def bootstrap_parallel(self, max_workers: int = 4) -> dict:
        """
        并行启动（优化模式）

        Args:
            max_workers: 最大并行数

        Returns:
            启动结果统计
        """
        logger.info("=== 并行服务启动模式 ===")
        start_time = time.time()

        results = {
            'mode': 'parallel',
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_services': [],
            'phase_times': {}
        }

        # Phase 1: 顺序启动核心服务
        logger.info("Phase 1: 核心服务初始化...")
        phase1_start = time.time()

        for service_name in self.core_services:
            try:
                service = self.container.resolve_by_name(service_name)
                service.initialize()
                results['success'] += 1
                logger.info(f"  ✓ {service_name}")
            except Exception as e:
                results['failed'] += 1
                results['failed_services'].append((service_name, str(e)))
                logger.error(f"  ✗ {service_name}: {e}")

        results['total'] += len(self.core_services)
        results['phase_times']['core'] = time.time() - phase1_start

        # Phase 2: 并行启动独立服务
        logger.info("Phase 2: 独立服务并行初始化...")
        phase2_start = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for service_name in self.independent_services:
                try:
                    service = self.container.resolve_by_name(service_name)
                    future = executor.submit(self._initialize_service, service_name, service)
                    futures[future] = service_name
                except Exception as e:
                    results['failed'] += 1
                    results['failed_services'].append((service_name, str(e)))
                    logger.error(f"  ✗ {service_name}: {e}")

            # 等待所有任务完成
            for future in as_completed(futures):
                service_name = futures[future]
                try:
                    success = future.result()
                    if success:
                        results['success'] += 1
                        logger.info(f"  ✓ {service_name}")
                    else:
                        results['failed'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['failed_services'].append((service_name, str(e)))
                    logger.error(f"  ✗ {service_name}: {e}")

        results['total'] += len(self.independent_services)
        results['phase_times']['parallel'] = time.time() - phase2_start

        # Phase 3: 顺序启动业务服务
        logger.info("Phase 3: 业务服务初始化...")
        phase3_start = time.time()

        for service_name in self.business_services:
            try:
                service = self.container.resolve_by_name(service_name)
                service.initialize()
                results['success'] += 1
                logger.info(f"  ✓ {service_name}")
            except Exception as e:
                results['failed'] += 1
                results['failed_services'].append((service_name, str(e)))
                logger.error(f"  ✗ {service_name}: {e}")

        results['total'] += len(self.business_services)
        results['phase_times']['business'] = time.time() - phase3_start

        # 总计
        results['elapsed_seconds'] = time.time() - start_time

        return results

    def _initialize_service(self, name: str, service) -> bool:
        """
        初始化单个服务

        Args:
            name: 服务名称
            service: 服务实例

        Returns:
            是否成功
        """
        try:
            service.initialize()
            return True
        except Exception as e:
            logger.error(f"Service {name} initialization failed: {e}")
            return False

    def print_results(self, results: dict):
        """打印启动结果"""
        print("\n" + "="*70)
        print(f"服务启动结果 - {results['mode'].upper()}模式")
        print("="*70)
        print(f"总服务数: {results['total']}")
        print(f"成功: {results['success']}")
        print(f"失败: {results['failed']}")
        print(f"总耗时: {results['elapsed_seconds']:.2f}秒")

        if 'phase_times' in results:
            print("\n各阶段耗时:")
            print(f"  核心服务: {results['phase_times']['core']:.2f}秒")
            print(f"  独立服务: {results['phase_times']['parallel']:.2f}秒")
            print(f"  业务服务: {results['phase_times']['business']:.2f}秒")

        if results['failed_services']:
            print("\n失败的服务:")
            for name, error in results['failed_services']:
                print(f"  - {name}: {error[:50]}...")

        print("="*70)


def demo_parallel_bootstrap():
    """演示并行启动（测试用）"""
    print("并行服务启动演示")
    print("注意：这只是一个演示，需要实际的服务容器才能运行")

    # 模拟容器
    class MockContainer:
        def resolve_by_name(self, name):
            class MockService:
                def initialize(self):
                    time.sleep(0.1)  # 模拟初始化耗时
            return MockService()

    container = MockContainer()
    bootstrap = ParallelServiceBootstrap(container)

    # 对比测试
    print("\n1. 顺序启动测试...")
    seq_results = bootstrap.bootstrap_sequential()
    bootstrap.print_results(seq_results)

    print("\n2. 并行启动测试...")
    par_results = bootstrap.bootstrap_parallel(max_workers=4)
    bootstrap.print_results(par_results)

    # 性能对比
    improvement = (seq_results['elapsed_seconds'] - par_results['elapsed_seconds']) / seq_results['elapsed_seconds'] * 100
    print(f"\n性能提升: {improvement:.1f}%")
    print(f"节省时间: {seq_results['elapsed_seconds'] - par_results['elapsed_seconds']:.2f}秒")


if __name__ == '__main__':
    demo_parallel_bootstrap()
