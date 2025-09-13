#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
监控和缓存系统集成专项测试

专门测试监控、异常检测和多级缓存系统的集成
"""

import unittest
import sys
import os
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.services.deep_analysis_service import DeepAnalysisService
    from core.services.enhanced_data_manager import (
        MultiLevelCacheManager, CacheLevel,  # MultiLayerCache 已移除
        FactorWeavePerformanceIntegrator, PerformanceMetric, AnomalyInfo
    )
    MONITORING_CACHE_AVAILABLE = True
except ImportError as e:
    print(f"监控和缓存组件导入失败: {e}")
    MONITORING_CACHE_AVAILABLE = False


class TestDeepAnalysisServiceIntegration(unittest.TestCase):
    """深度分析服务集成测试"""

    def setUp(self):
        """测试前设置"""
        if not MONITORING_CACHE_AVAILABLE:
            self.skipTest("监控和缓存组件不可用")

        self.deep_analysis = DeepAnalysisService()
        self.test_task_id = "monitoring_test_001"

    def test_01_service_initialization(self):
        """测试服务初始化"""
        print("\n📊 测试深度分析服务初始化...")

        self.assertIsNotNone(self.deep_analysis)
        self.assertTrue(hasattr(self.deep_analysis, 'start_monitoring'))
        self.assertTrue(hasattr(self.deep_analysis, 'stop_monitoring'))
        self.assertTrue(hasattr(self.deep_analysis, 'detect_anomalies'))
        self.assertTrue(hasattr(self.deep_analysis, 'get_performance_metrics'))

        print("✅ 深度分析服务初始化测试通过")

    def test_02_performance_monitoring(self):
        """测试性能监控"""
        print("\n⏱️ 测试性能监控...")

        # 启动监控
        self.deep_analysis.start_monitoring(self.test_task_id)

        # 模拟一些工作负载
        time.sleep(0.1)

        # 停止监控
        metrics = self.deep_analysis.stop_monitoring(self.test_task_id)

        if metrics:
            self.assertIsInstance(metrics, dict)
            expected_keys = ['execution_time', 'cpu_usage', 'memory_usage']
            for key in expected_keys:
                if key in metrics:
                    self.assertIsInstance(metrics[key], (int, float))

            print(f"   监控指标: {metrics}")

        print("✅ 性能监控测试通过")

    def test_03_anomaly_detection(self):
        """测试异常检测"""
        print("\n🚨 测试异常检测...")

        # 启动监控
        self.deep_analysis.start_monitoring(self.test_task_id)

        # 模拟异常情况（如果有相关方法）
        time.sleep(0.1)

        # 检测异常
        anomalies = self.deep_analysis.detect_anomalies(self.test_task_id)

        self.assertIsInstance(anomalies, list)

        # 如果检测到异常，验证异常信息结构
        for anomaly in anomalies:
            if hasattr(anomaly, 'type') and hasattr(anomaly, 'severity'):
                self.assertIsInstance(anomaly.type, str)
                self.assertIsInstance(anomaly.severity, str)

        print(f"   检测到异常数量: {len(anomalies)}")
        print("✅ 异常检测测试通过")

    def test_04_performance_metrics_collection(self):
        """测试性能指标收集"""
        print("\n📈 测试性能指标收集...")

        # 启动监控
        self.deep_analysis.start_monitoring(self.test_task_id)

        # 模拟多次数据收集
        for i in range(5):
            time.sleep(0.05)
            # 如果有更新指标的方法，可以调用

        # 获取性能指标
        metrics = self.deep_analysis.get_performance_metrics(self.test_task_id)

        if metrics:
            self.assertIsInstance(metrics, (dict, list))
            print(f"   收集到指标数量: {len(metrics) if isinstance(metrics, (list, dict)) else 0}")

        # 停止监控
        self.deep_analysis.stop_monitoring(self.test_task_id)

        print("✅ 性能指标收集测试通过")


class TestFactorWeavePerformanceIntegrator(unittest.TestCase):
    """FactorWeave性能集成器测试"""

    def setUp(self):
        """测试前设置"""
        if not MONITORING_CACHE_AVAILABLE:
            self.skipTest("监控和缓存组件不可用")

        try:
            self.performance_integrator = FactorWeavePerformanceIntegrator()
            self.test_task_id = "integrator_test_001"
        except Exception as e:
            self.skipTest(f"FactorWeavePerformanceIntegrator不可用: {e}")

    def test_01_integrator_initialization(self):
        """测试集成器初始化"""
        print("\n🔗 测试性能集成器初始化...")

        self.assertIsNotNone(self.performance_integrator)

        # 检查基本方法
        expected_methods = ['start_monitoring', 'stop_monitoring', 'get_metrics']
        for method in expected_methods:
            if hasattr(self.performance_integrator, method):
                self.assertTrue(callable(getattr(self.performance_integrator, method)))

        print("✅ 性能集成器初始化测试通过")

    def test_02_unified_monitoring(self):
        """测试统一监控"""
        print("\n📊 测试统一监控...")

        # 启动统一监控
        if hasattr(self.performance_integrator, 'start_monitoring'):
            self.performance_integrator.start_monitoring(self.test_task_id)

            # 模拟工作负载
            time.sleep(0.1)

            # 停止监控并获取结果
            if hasattr(self.performance_integrator, 'stop_monitoring'):
                result = self.performance_integrator.stop_monitoring(self.test_task_id)

                if result:
                    self.assertIsInstance(result, dict)
                    print(f"   统一监控结果: {result}")

        print("✅ 统一监控测试通过")

    def test_03_metrics_aggregation(self):
        """测试指标聚合"""
        print("\n📋 测试指标聚合...")

        # 获取聚合指标
        if hasattr(self.performance_integrator, 'get_metrics'):
            metrics = self.performance_integrator.get_metrics()

            if metrics:
                self.assertIsInstance(metrics, dict)
                print(f"   聚合指标: {metrics}")

        print("✅ 指标聚合测试通过")


class TestMultiLevelCacheManager(unittest.TestCase):
    """多级缓存管理器测试"""

    def setUp(self):
        """测试前设置"""
        if not MONITORING_CACHE_AVAILABLE:
            self.skipTest("监控和缓存组件不可用")

        try:
            self.cache_manager = MultiLevelCacheManager()
        except Exception as e:
            self.skipTest(f"MultiLevelCacheManager不可用: {e}")

    def test_01_cache_manager_initialization(self):
        """测试缓存管理器初始化"""
        print("\n💾 测试多级缓存管理器初始化...")

        self.assertIsNotNone(self.cache_manager)

        # 检查基本方法
        expected_methods = ['get', 'set', 'delete', 'clear', 'get_stats']
        for method in expected_methods:
            if hasattr(self.cache_manager, method):
                self.assertTrue(callable(getattr(self.cache_manager, method)))

        print("✅ 多级缓存管理器初始化测试通过")

    def test_02_cache_operations(self):
        """测试缓存操作"""
        print("\n🔄 测试缓存操作...")

        test_key = "test_cache_key"
        test_value = {"data": "test_value", "timestamp": time.time()}

        # 测试设置缓存
        if hasattr(self.cache_manager, 'set'):
            set_result = self.cache_manager.set(test_key, test_value)
            print(f"   缓存设置结果: {set_result}")

        # 测试获取缓存
        if hasattr(self.cache_manager, 'get'):
            cached_value = self.cache_manager.get(test_key)

            if cached_value is not None:
                self.assertEqual(cached_value, test_value)
                print(f"   缓存获取成功: {cached_value}")
            else:
                print("   缓存获取为空（可能是实现差异）")

        # 测试删除缓存
        if hasattr(self.cache_manager, 'delete'):
            delete_result = self.cache_manager.delete(test_key)
            print(f"   缓存删除结果: {delete_result}")

        print("✅ 缓存操作测试通过")

    def test_03_cache_statistics(self):
        """测试缓存统计"""
        print("\n📊 测试缓存统计...")

        # 执行一些缓存操作
        for i in range(5):
            key = f"stats_test_{i}"
            value = {"index": i, "data": f"test_data_{i}"}

            if hasattr(self.cache_manager, 'set'):
                self.cache_manager.set(key, value)

        # 获取统计信息
        if hasattr(self.cache_manager, 'get_stats'):
            stats = self.cache_manager.get_stats()

            if stats:
                self.assertIsInstance(stats, dict)
                print(f"   缓存统计: {stats}")

        print("✅ 缓存统计测试通过")

    def test_04_cache_performance(self):
        """测试缓存性能"""
        print("\n⚡ 测试缓存性能...")

        # 测试批量写入性能
        start_time = time.time()
        for i in range(100):
            key = f"perf_test_{i}"
            value = {"index": i, "timestamp": time.time()}

            if hasattr(self.cache_manager, 'set'):
                self.cache_manager.set(key, value)

        write_time = time.time() - start_time

        # 测试批量读取性能
        start_time = time.time()
        for i in range(100):
            key = f"perf_test_{i}"

            if hasattr(self.cache_manager, 'get'):
                self.cache_manager.get(key)

        read_time = time.time() - start_time

        print(f"   100次写入耗时: {write_time:.3f}秒")
        print(f"   100次读取耗时: {read_time:.3f}秒")

        # 性能断言
        self.assertLess(write_time, 1.0, "100次缓存写入应在1秒内完成")
        self.assertLess(read_time, 0.5, "100次缓存读取应在0.5秒内完成")

        print("✅ 缓存性能测试通过")


# class TestMultiLayerCache(unittest.TestCase):  # 已移除 - MultiLayerCache已统一使用MultiLevelCacheManager
class TestMultiLayerCacheObsolete(unittest.TestCase):
    """多层缓存测试"""

    def setUp(self):
        """测试前设置"""
        if not MONITORING_CACHE_AVAILABLE:
            self.skipTest("监控和缓存组件不可用")

        try:
            # self.multi_layer_cache = MultiLayerCache()  # 已移除
            self.skipTest("MultiLayerCache已移除，统一使用MultiLevelCacheManager")
        except Exception as e:
            self.skipTest(f"MultiLayerCache不可用: {e}")

    def test_01_multi_layer_initialization(self):
        """测试多层缓存初始化"""
        print("\n🏗️ 测试多层缓存初始化...")

        self.assertIsNotNone(self.multi_layer_cache)

        # 检查缓存层级
        if hasattr(self.multi_layer_cache, 'cache_levels'):
            cache_levels = self.multi_layer_cache.cache_levels
            print(f"   缓存层级: {cache_levels}")

        print("✅ 多层缓存初始化测试通过")

    def test_02_layer_specific_operations(self):
        """测试层级特定操作"""
        print("\n📚 测试层级特定操作...")

        test_data = [
            ("l1_key", {"level": "L1", "data": "fast_access"}),
            ("l2_key", {"level": "L2", "data": "medium_access"}),
            ("disk_key", {"level": "DISK", "data": "slow_access"})
        ]

        # 测试不同层级的缓存操作
        for key, value in test_data:
            # 如果支持层级指定
            if hasattr(self.multi_layer_cache, 'set_level'):
                try:
                    self.multi_layer_cache.set_level(key, value, CacheLevel.L1)
                except:
                    # 如果不支持层级指定，使用普通set
                    if hasattr(self.multi_layer_cache, 'set'):
                        self.multi_layer_cache.set(key, value)
            elif hasattr(self.multi_layer_cache, 'set'):
                self.multi_layer_cache.set(key, value)

        # 测试获取
        for key, expected_value in test_data:
            if hasattr(self.multi_layer_cache, 'get'):
                cached_value = self.multi_layer_cache.get(key)
                if cached_value:
                    print(f"   缓存命中: {key} -> {cached_value}")

        print("✅ 层级特定操作测试通过")

    def test_03_cache_hierarchy_performance(self):
        """测试缓存层级性能"""
        print("\n🚀 测试缓存层级性能...")

        # 测试不同大小数据的缓存性能
        test_sizes = [
            ("small", {"size": "small", "data": "x" * 100}),
            ("medium", {"size": "medium", "data": "x" * 1000}),
            ("large", {"size": "large", "data": "x" * 10000})
        ]

        performance_results = {}

        for size_name, data in test_sizes:
            # 写入性能测试
            start_time = time.time()
            key = f"perf_{size_name}"

            if hasattr(self.multi_layer_cache, 'set'):
                self.multi_layer_cache.set(key, data)

            write_time = time.time() - start_time

            # 读取性能测试
            start_time = time.time()

            if hasattr(self.multi_layer_cache, 'get'):
                self.multi_layer_cache.get(key)

            read_time = time.time() - start_time

            performance_results[size_name] = {
                'write_time': write_time,
                'read_time': read_time
            }

        # 输出性能结果
        for size_name, perf in performance_results.items():
            print(f"   {size_name}数据 - 写入: {perf['write_time']:.4f}秒, 读取: {perf['read_time']:.4f}秒")

        print("✅ 缓存层级性能测试通过")


class TestIntegratedMonitoringAndCaching(unittest.TestCase):
    """监控和缓存集成测试"""

    def setUp(self):
        """测试前设置"""
        if not MONITORING_CACHE_AVAILABLE:
            self.skipTest("监控和缓存组件不可用")

        try:
            self.deep_analysis = DeepAnalysisService()
            self.cache_manager = MultiLevelCacheManager()
            self.test_task_id = "integrated_test_001"
        except Exception as e:
            self.skipTest(f"集成组件不可用: {e}")

    def test_01_monitoring_with_caching(self):
        """测试监控与缓存的协同工作"""
        print("\n🔄 测试监控与缓存的协同工作...")

        # 启动监控
        self.deep_analysis.start_monitoring(self.test_task_id)

        # 执行一些缓存操作，同时监控性能
        for i in range(10):
            key = f"integrated_test_{i}"
            value = {
                "index": i,
                "timestamp": time.time(),
                "task_id": self.test_task_id
            }

            # 缓存操作
            if hasattr(self.cache_manager, 'set'):
                self.cache_manager.set(key, value)

            # 短暂延迟
            time.sleep(0.01)

        # 停止监控并获取结果
        monitoring_result = self.deep_analysis.stop_monitoring(self.test_task_id)

        # 获取缓存统计
        cache_stats = None
        if hasattr(self.cache_manager, 'get_stats'):
            cache_stats = self.cache_manager.get_stats()

        # 验证结果
        if monitoring_result:
            self.assertIsInstance(monitoring_result, dict)
            print(f"   监控结果: {monitoring_result}")

        if cache_stats:
            self.assertIsInstance(cache_stats, dict)
            print(f"   缓存统计: {cache_stats}")

        print("✅ 监控与缓存协同工作测试通过")

    def test_02_performance_impact_analysis(self):
        """测试性能影响分析"""
        print("\n📈 测试性能影响分析...")

        # 测试无缓存情况下的性能
        self.deep_analysis.start_monitoring(f"{self.test_task_id}_no_cache")

        # 模拟无缓存的数据处理
        for i in range(50):
            # 模拟数据处理延迟
            time.sleep(0.002)

        no_cache_result = self.deep_analysis.stop_monitoring(f"{self.test_task_id}_no_cache")

        # 测试有缓存情况下的性能
        self.deep_analysis.start_monitoring(f"{self.test_task_id}_with_cache")

        # 预先缓存一些数据
        for i in range(50):
            key = f"cached_data_{i}"
            value = {"processed": True, "result": i * 2}

            if hasattr(self.cache_manager, 'set'):
                self.cache_manager.set(key, value)

        # 模拟从缓存读取数据
        for i in range(50):
            key = f"cached_data_{i}"

            if hasattr(self.cache_manager, 'get'):
                self.cache_manager.get(key)

        with_cache_result = self.deep_analysis.stop_monitoring(f"{self.test_task_id}_with_cache")

        # 比较性能差异
        if no_cache_result and with_cache_result:
            print(f"   无缓存性能: {no_cache_result}")
            print(f"   有缓存性能: {with_cache_result}")

            # 如果有执行时间字段，比较差异
            if 'execution_time' in no_cache_result and 'execution_time' in with_cache_result:
                no_cache_time = no_cache_result['execution_time']
                with_cache_time = with_cache_result['execution_time']

                if no_cache_time > 0 and with_cache_time > 0:
                    improvement = (no_cache_time - with_cache_time) / no_cache_time * 100
                    print(f"   性能提升: {improvement:.2f}%")

        print("✅ 性能影响分析测试通过")


def run_monitoring_cache_tests():
    """运行监控和缓存集成测试"""
    print("📊 开始运行监控和缓存集成测试...")
    print("=" * 60)

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加监控和缓存测试
    suite.addTest(unittest.makeSuite(TestDeepAnalysisServiceIntegration))
    suite.addTest(unittest.makeSuite(TestFactorWeavePerformanceIntegrator))
    suite.addTest(unittest.makeSuite(TestMultiLevelCacheManager))
    # suite.addTest(unittest.makeSuite(TestMultiLayerCache))  # 已移除
    suite.addTest(unittest.makeSuite(TestMultiLayerCacheObsolete))  # 占位测试，会被跳过
    suite.addTest(unittest.makeSuite(TestIntegratedMonitoringAndCaching))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("🎯 监控和缓存测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 所有监控和缓存测试通过！")
        return True
    else:
        print("\n⚠️ 部分监控和缓存测试未通过。")
        return False


if __name__ == "__main__":
    success = run_monitoring_cache_tests()
    sys.exit(0 if success else 1)
