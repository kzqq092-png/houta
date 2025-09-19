#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
长期运行稳定性测试

进行长期运行稳定性测试和内存泄漏检测，验证系统的长期可靠性和资源管理。
测试场景包括：
1. 长时间连续运行测试
2. 内存泄漏检测
3. 资源泄漏检测
4. 系统稳定性监控
5. 异常恢复能力测试
"""

import pytest
import unittest
import tempfile
import os
import time
import threading
import psutil
import gc
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, Mock
import sqlite3
import json
import signal
import sys
from pathlib import Path
import tracemalloc
import weakref

# 导入待测试的组件
from core.importdata.intelligent_config_manager import (
    IntelligentConfigManager, ImportTaskConfig, DataFrequency, ImportMode
)
from core.ai.data_anomaly_detector import (
    DataAnomalyDetector, AnomalyDetectionConfig
)
from core.ui_integration.smart_data_integration import (
    SmartDataIntegration, UIIntegrationConfig
)


class LongTermStabilityTest(unittest.TestCase):
    """长期稳定性测试基类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_start_time = time.time()
        cls.process = psutil.Process()
        cls.initial_memory = cls.process.memory_info().rss / 1024 / 1024  # MB
        cls.initial_open_files = len(cls.process.open_files())
        cls.initial_threads = cls.process.num_threads()
        
        # 启用内存跟踪
        tracemalloc.start()
        
        # 设置信号处理器用于优雅退出
        signal.signal(signal.SIGINT, cls._signal_handler)
        signal.signal(signal.SIGTERM, cls._signal_handler)
        
        cls.stop_flag = threading.Event()
        
        print(f"\n{'='*80}")
        print(f"开始长期稳定性测试")
        print(f"初始内存使用: {cls.initial_memory:.1f} MB")
        print(f"初始文件句柄: {cls.initial_open_files}")
        print(f"初始线程数: {cls.initial_threads}")
        print(f"测试进程PID: {os.getpid()}")
        print(f"{'='*80}")

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        final_memory = cls.process.memory_info().rss / 1024 / 1024  # MB
        final_open_files = len(cls.process.open_files())
        final_threads = cls.process.num_threads()
        test_duration = time.time() - cls.test_start_time
        
        # 获取内存跟踪信息
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\n{'='*80}")
        print(f"长期稳定性测试完成")
        print(f"测试总耗时: {test_duration:.2f} 秒 ({test_duration/3600:.2f} 小时)")
        print(f"最终内存使用: {final_memory:.1f} MB")
        print(f"内存增长: {final_memory - cls.initial_memory:.1f} MB")
        print(f"最终文件句柄: {final_open_files}")
        print(f"文件句柄增长: {final_open_files - cls.initial_open_files}")
        print(f"最终线程数: {final_threads}")
        print(f"线程数增长: {final_threads - cls.initial_threads}")
        print(f"内存跟踪 - 当前: {current / 1024 / 1024:.1f}MB, 峰值: {peak / 1024 / 1024:.1f}MB")
        print(f"{'='*80}")

    @classmethod
    def _signal_handler(cls, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在优雅退出...")
        cls.stop_flag.set()

    def setUp(self):
        """每个测试前的准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 记录测试开始时的资源使用情况
        self.test_start_memory = self.process.memory_info().rss / 1024 / 1024
        self.test_start_files = len(self.process.open_files())
        self.test_start_threads = self.process.num_threads()
        self.test_start_time = time.time()

    def tearDown(self):
        """每个测试后的清理"""
        try:
            os.unlink(self.db_path)
        except:
            pass
        
        # 强制垃圾回收
        gc.collect()
        
        # 记录测试结束时的资源使用情况
        test_end_memory = self.process.memory_info().rss / 1024 / 1024
        test_end_files = len(self.process.open_files())
        test_end_threads = self.process.num_threads()
        test_duration = time.time() - self.test_start_time
        
        memory_increase = test_end_memory - self.test_start_memory
        files_increase = test_end_files - self.test_start_files
        threads_increase = test_end_threads - self.test_start_threads
        
        print(f"  测试耗时: {test_duration:.2f}s")
        print(f"  内存增长: {memory_increase:.1f}MB")
        print(f"  文件句柄增长: {files_increase}")
        print(f"  线程数增长: {threads_increase}")


class TestMemoryLeakDetection(LongTermStabilityTest):
    """内存泄漏检测测试"""

    def test_config_manager_memory_leak(self):
        """测试配置管理器内存泄漏"""
        print("\n--- 测试配置管理器内存泄漏 ---")
        
        # 记录初始内存快照
        snapshot1 = tracemalloc.take_snapshot()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        
        # 创建和销毁多个配置管理器实例
        num_iterations = 100
        managers_created = 0
        
        print(f"创建和销毁 {num_iterations} 个配置管理器实例...")
        
        for iteration in range(num_iterations):
            if self.stop_flag.is_set():
                break
                
            try:
                # 创建临时数据库
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                # 创建配置管理器
                manager = IntelligentConfigManager(temp_db.name)
                managers_created += 1
                
                # 添加一些任务
                for i in range(10):
                    config = ImportTaskConfig(
                        task_id=f"leak_test_{iteration}_{i}",
                        name=f"内存泄漏测试{iteration}-{i}",
                        data_source="tongdaxin",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{i:06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH
                    )
                    manager.add_import_task(config)
                
                # 记录一些性能数据
                for i in range(5):
                    manager.record_performance_feedback(
                        config=config,
                        execution_time=np.random.uniform(30, 120),
                        success_rate=np.random.uniform(0.8, 1.0),
                        error_rate=np.random.uniform(0.0, 0.2),
                        throughput=np.random.uniform(500, 2000)
                    )
                
                # 获取统计信息
                stats = manager.get_intelligent_statistics()
                
                # 检测冲突
                conflicts = manager.detect_conflicts()
                
                # 显式删除管理器引用
                del manager
                
                # 清理数据库文件
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
                
                # 每10次迭代进行一次垃圾回收和内存检查
                if (iteration + 1) % 10 == 0:
                    gc.collect()
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory
                    
                    print(f"  迭代 {iteration + 1}/{num_iterations}, 内存增长: {memory_growth:.1f}MB")
                    
                    # 如果内存增长过快，提前警告
                    if memory_growth > 100:  # 超过100MB
                        print(f"  警告: 内存增长过快 ({memory_growth:.1f}MB)")
                
            except Exception as e:
                print(f"  迭代 {iteration} 失败: {e}")
        
        # 最终垃圾回收
        gc.collect()
        
        # 记录最终内存快照
        snapshot2 = tracemalloc.take_snapshot()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        
        # 分析内存差异
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        print(f"内存泄漏检测结果:")
        print(f"  创建管理器数: {managers_created}")
        print(f"  初始内存: {initial_memory:.1f}MB")
        print(f"  最终内存: {final_memory:.1f}MB")
        print(f"  内存增长: {final_memory - initial_memory:.1f}MB")
        print(f"  平均每个实例内存增长: {(final_memory - initial_memory) / managers_created:.3f}MB")
        
        # 显示内存增长最多的前5个位置
        print("  内存增长最多的代码位置:")
        for index, stat in enumerate(top_stats[:5]):
            print(f"    {index + 1}. {stat}")
        
        # 内存泄漏断言
        memory_growth = final_memory - initial_memory
        memory_per_instance = memory_growth / managers_created if managers_created > 0 else 0
        
        # 允许每个实例有少量内存残留（小于1MB）
        self.assertLess(memory_per_instance, 1.0, f"可能存在内存泄漏: 每个实例平均增长 {memory_per_instance:.3f}MB")
        self.assertLess(memory_growth, 50, f"总内存增长过大: {memory_growth:.1f}MB")

    def test_anomaly_detector_memory_leak(self):
        """测试异常检测器内存泄漏"""
        print("\n--- 测试异常检测器内存泄漏 ---")
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        
        # 创建和销毁多个异常检测器实例
        num_iterations = 50
        detectors_created = 0
        
        print(f"创建和销毁 {num_iterations} 个异常检测器实例...")
        
        for iteration in range(num_iterations):
            if self.stop_flag.is_set():
                break
                
            try:
                # 创建临时数据库
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                # 创建异常检测器
                config = AnomalyDetectionConfig(auto_repair_enabled=True)
                detector = DataAnomalyDetector(config, temp_db.name)
                detectors_created += 1
                
                # 创建测试数据
                test_data = pd.DataFrame({
                    'timestamp': pd.date_range('2024-01-01', periods=1000, freq='min'),
                    'symbol': f'LEAK_TEST_{iteration}',
                    'price': np.concatenate([
                        np.random.normal(100, 10, 900),  # 正常数据
                        [np.nan] * 50,  # 缺失数据
                        np.random.normal(300, 50, 50)   # 异常值
                    ]),
                    'volume': np.random.randint(1000, 100000, 1000)
                })
                
                # 执行异常检测
                anomalies = detector.detect_anomalies(
                    data=test_data,
                    data_source="leak_test",
                    symbol=f"LEAK_TEST_{iteration}",
                    data_type="kline"
                )
                
                # 尝试自动修复一些异常
                for anomaly in anomalies[:3]:  # 只修复前3个异常
                    detector.auto_repair_anomaly(anomaly.anomaly_id)
                
                # 获取统计信息
                stats = detector.get_anomaly_statistics()
                
                # 清理异常记录
                detector.cleanup_old_records(days=0)  # 清理所有记录
                
                # 显式删除检测器引用
                del detector
                del test_data
                
                # 清理数据库文件
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
                
                # 每10次迭代进行一次内存检查
                if (iteration + 1) % 10 == 0:
                    gc.collect()
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory
                    
                    print(f"  迭代 {iteration + 1}/{num_iterations}, 内存增长: {memory_growth:.1f}MB")
                
            except Exception as e:
                print(f"  迭代 {iteration} 失败: {e}")
        
        # 最终垃圾回收
        gc.collect()
        
        final_memory = self.process.memory_info().rss / 1024 / 1024
        
        print(f"异常检测器内存泄漏检测结果:")
        print(f"  创建检测器数: {detectors_created}")
        print(f"  初始内存: {initial_memory:.1f}MB")
        print(f"  最终内存: {final_memory:.1f}MB")
        print(f"  内存增长: {final_memory - initial_memory:.1f}MB")
        print(f"  平均每个实例内存增长: {(final_memory - initial_memory) / detectors_created:.3f}MB")
        
        # 内存泄漏断言
        memory_growth = final_memory - initial_memory
        memory_per_instance = memory_growth / detectors_created if detectors_created > 0 else 0
        
        self.assertLess(memory_per_instance, 2.0, f"可能存在内存泄漏: 每个实例平均增长 {memory_per_instance:.3f}MB")
        self.assertLess(memory_growth, 100, f"总内存增长过大: {memory_growth:.1f}MB")

    def test_data_integration_memory_leak(self):
        """测试数据集成组件内存泄漏"""
        print("\n--- 测试数据集成组件内存泄漏 ---")
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        
        # 创建和销毁多个数据集成实例
        num_iterations = 30
        integrations_created = 0
        
        print(f"创建和销毁 {num_iterations} 个数据集成实例...")
        
        for iteration in range(num_iterations):
            if self.stop_flag.is_set():
                break
                
            try:
                # 创建数据集成实例
                config = UIIntegrationConfig(
                    enable_caching=True,
                    cache_expiry_seconds=300,
                    enable_predictive_loading=True,
                    enable_adaptive_caching=True
                )
                
                with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
                    integration = SmartDataIntegration(config)
                    integrations_created += 1
                
                # 添加大量缓存数据
                for i in range(100):
                    cache_key = f"leak_test_{iteration}_{i}"
                    test_data = {
                        'symbol': f"TEST{i:06d}",
                        'data': [{'price': 10.0 + j * 0.1, 'volume': 1000 + j * 10} 
                                for j in range(50)]
                    }
                    integration._put_to_intelligent_cache(cache_key, test_data, "high", 300)
                
                # 记录使用模式
                for i in range(50):
                    integration._record_usage_pattern(
                        f"widget_{i % 5}", 
                        f"symbol_{i:06d}", 
                        "realtime" if i % 2 == 0 else "daily"
                    )
                
                # 执行性能优化
                integration.optimize_performance()
                
                # 获取统计信息
                stats = integration.get_statistics()
                
                # 清理缓存
                integration.intelligent_cache.clear()
                
                # 关闭集成实例
                integration.close()
                
                # 显式删除引用
                del integration
                
                # 每5次迭代进行一次内存检查
                if (iteration + 1) % 5 == 0:
                    gc.collect()
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory
                    
                    print(f"  迭代 {iteration + 1}/{num_iterations}, 内存增长: {memory_growth:.1f}MB")
                
            except Exception as e:
                print(f"  迭代 {iteration} 失败: {e}")
        
        # 最终垃圾回收
        gc.collect()
        
        final_memory = self.process.memory_info().rss / 1024 / 1024
        
        print(f"数据集成内存泄漏检测结果:")
        print(f"  创建集成实例数: {integrations_created}")
        print(f"  初始内存: {initial_memory:.1f}MB")
        print(f"  最终内存: {final_memory:.1f}MB")
        print(f"  内存增长: {final_memory - initial_memory:.1f}MB")
        print(f"  平均每个实例内存增长: {(final_memory - initial_memory) / integrations_created:.3f}MB")
        
        # 内存泄漏断言
        memory_growth = final_memory - initial_memory
        memory_per_instance = memory_growth / integrations_created if integrations_created > 0 else 0
        
        self.assertLess(memory_per_instance, 3.0, f"可能存在内存泄漏: 每个实例平均增长 {memory_per_instance:.3f}MB")
        self.assertLess(memory_growth, 100, f"总内存增长过大: {memory_growth:.1f}MB")


class TestResourceLeakDetection(LongTermStabilityTest):
    """资源泄漏检测测试"""

    def test_file_handle_leak(self):
        """测试文件句柄泄漏"""
        print("\n--- 测试文件句柄泄漏 ---")
        
        initial_files = len(self.process.open_files())
        
        # 创建和销毁多个组件实例，监控文件句柄
        num_iterations = 100
        components_created = 0
        
        print(f"创建和销毁 {num_iterations} 个组件实例，监控文件句柄...")
        
        for iteration in range(num_iterations):
            if self.stop_flag.is_set():
                break
                
            try:
                # 创建临时数据库文件
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                # 创建配置管理器
                manager = IntelligentConfigManager(temp_db.name)
                
                # 创建异常检测器
                anomaly_config = AnomalyDetectionConfig()
                detector = DataAnomalyDetector(anomaly_config, temp_db.name)
                
                components_created += 1
                
                # 执行一些操作
                config = ImportTaskConfig(
                    task_id=f"file_leak_test_{iteration}",
                    name=f"文件句柄泄漏测试{iteration}",
                    data_source="tongdaxin",
                    asset_type="stock",
                    data_type="kline",
                    symbols=["000001"],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH
                )
                
                manager.add_import_task(config)
                
                # 创建测试数据并检测异常
                test_data = pd.DataFrame({
                    'price': [10.0, np.nan, 12.0, 200.0, 11.0],
                    'volume': [1000, 1100, 1200, 1300, 1400]
                })
                
                anomalies = detector.detect_anomalies(
                    data=test_data,
                    data_source="file_leak_test",
                    symbol=f"TEST_{iteration}",
                    data_type="kline"
                )
                
                # 显式删除组件引用
                del manager
                del detector
                
                # 删除数据库文件
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
                
                # 每20次迭代检查文件句柄
                if (iteration + 1) % 20 == 0:
                    gc.collect()
                    current_files = len(self.process.open_files())
                    files_growth = current_files - initial_files
                    
                    print(f"  迭代 {iteration + 1}/{num_iterations}, 文件句柄增长: {files_growth}")
                    
                    # 如果文件句柄增长过多，提前警告
                    if files_growth > 50:
                        print(f"  警告: 文件句柄增长过多 ({files_growth})")
                        
                        # 显示当前打开的文件
                        open_files = self.process.open_files()
                        print(f"  当前打开文件数: {len(open_files)}")
                        if len(open_files) > initial_files + 10:
                            print("  部分打开的文件:")
                            for i, file_info in enumerate(open_files[-10:]):  # 显示最后10个
                                print(f"    {file_info.path}")
                
            except Exception as e:
                print(f"  迭代 {iteration} 失败: {e}")
        
        # 最终检查
        gc.collect()
        final_files = len(self.process.open_files())
        
        print(f"文件句柄泄漏检测结果:")
        print(f"  创建组件数: {components_created}")
        print(f"  初始文件句柄: {initial_files}")
        print(f"  最终文件句柄: {final_files}")
        print(f"  文件句柄增长: {final_files - initial_files}")
        print(f"  平均每个组件文件句柄增长: {(final_files - initial_files) / components_created:.2f}")
        
        # 文件句柄泄漏断言
        files_growth = final_files - initial_files
        files_per_component = files_growth / components_created if components_created > 0 else 0
        
        self.assertLess(files_per_component, 0.1, f"可能存在文件句柄泄漏: 每个组件平均增长 {files_per_component:.2f}")
        self.assertLess(files_growth, 10, f"总文件句柄增长过多: {files_growth}")

    def test_thread_leak(self):
        """测试线程泄漏"""
        print("\n--- 测试线程泄漏 ---")
        
        initial_threads = self.process.num_threads()
        
        # 创建和销毁多个使用线程的组件
        num_iterations = 20
        components_created = 0
        
        print(f"创建和销毁 {num_iterations} 个使用线程的组件...")
        
        for iteration in range(num_iterations):
            if self.stop_flag.is_set():
                break
                
            try:
                # 创建数据集成组件（使用线程池）
                config = UIIntegrationConfig(
                    enable_caching=True,
                    enable_predictive_loading=True
                )
                
                with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor') as mock_executor:
                    # 创建真实的线程池来测试线程泄漏
                    real_executor = ThreadPoolExecutor(max_workers=4)
                    mock_executor.return_value = real_executor
                    
                    integration = SmartDataIntegration(config)
                    components_created += 1
                    
                    # 执行一些需要线程的操作
                    futures = []
                    for i in range(10):
                        future = real_executor.submit(
                            lambda x: time.sleep(0.1) or x * x, i
                        )
                        futures.append(future)
                    
                    # 等待所有任务完成
                    for future in futures:
                        future.result()
                    
                    # 关闭组件
                    integration.close()
                    
                    # 显式关闭线程池
                    real_executor.shutdown(wait=True)
                    
                    # 删除引用
                    del integration
                    del real_executor
                
                # 每5次迭代检查线程数
                if (iteration + 1) % 5 == 0:
                    gc.collect()
                    time.sleep(0.5)  # 等待线程完全清理
                    
                    current_threads = self.process.num_threads()
                    threads_growth = current_threads - initial_threads
                    
                    print(f"  迭代 {iteration + 1}/{num_iterations}, 线程数增长: {threads_growth}")
                
            except Exception as e:
                print(f"  迭代 {iteration} 失败: {e}")
        
        # 最终检查
        gc.collect()
        time.sleep(1)  # 等待线程完全清理
        final_threads = self.process.num_threads()
        
        print(f"线程泄漏检测结果:")
        print(f"  创建组件数: {components_created}")
        print(f"  初始线程数: {initial_threads}")
        print(f"  最终线程数: {final_threads}")
        print(f"  线程数增长: {final_threads - initial_threads}")
        print(f"  平均每个组件线程增长: {(final_threads - initial_threads) / components_created:.2f}")
        
        # 线程泄漏断言
        threads_growth = final_threads - initial_threads
        threads_per_component = threads_growth / components_created if components_created > 0 else 0
        
        self.assertLess(threads_per_component, 0.5, f"可能存在线程泄漏: 每个组件平均增长 {threads_per_component:.2f}")
        self.assertLess(threads_growth, 5, f"总线程数增长过多: {threads_growth}")


class TestLongRunningStability(LongTermStabilityTest):
    """长时间运行稳定性测试"""

    def test_continuous_operation_stability(self):
        """测试连续操作稳定性"""
        print("\n--- 测试连续操作稳定性 ---")
        
        # 测试持续时间（秒）- 可以通过环境变量调整
        test_duration = int(os.environ.get('STABILITY_TEST_DURATION', '300'))  # 默认5分钟
        print(f"连续运行测试时长: {test_duration} 秒 ({test_duration/60:.1f} 分钟)")
        
        # 创建组件
        manager = IntelligentConfigManager(self.db_path)
        
        anomaly_config = AnomalyDetectionConfig(auto_repair_enabled=True)
        detector = DataAnomalyDetector(anomaly_config, self.db_path)
        
        integration_config = UIIntegrationConfig(enable_caching=True)
        with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
            integration = SmartDataIntegration(integration_config)
        
        # 统计信息
        operations_completed = 0
        errors_encountered = 0
        memory_samples = []
        
        # 运行状态
        start_time = time.time()
        last_report_time = start_time
        report_interval = 30  # 每30秒报告一次
        
        try:
            print("开始连续操作测试...")
            
            while time.time() - start_time < test_duration:
                if self.stop_flag.is_set():
                    print("收到停止信号，退出测试")
                    break
                
                try:
                    operation_start = time.time()
                    
                    # 1. 配置管理操作
                    task_id = f"stability_test_{operations_completed}"
                    config = ImportTaskConfig(
                        task_id=task_id,
                        name=f"稳定性测试任务{operations_completed}",
                        data_source="tongdaxin" if operations_completed % 2 == 0 else "akshare",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{(operations_completed % 1000):06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH,
                        max_workers=2 + (operations_completed % 4),
                        batch_size=500 + (operations_completed % 500)
                    )
                    
                    manager.add_import_task(config)
                    
                    # 记录性能数据
                    manager.record_performance_feedback(
                        config=config,
                        execution_time=np.random.uniform(30, 120),
                        success_rate=np.random.uniform(0.8, 1.0),
                        error_rate=np.random.uniform(0.0, 0.2),
                        throughput=np.random.uniform(500, 2000)
                    )
                    
                    # 2. 异常检测操作
                    if operations_completed % 5 == 0:  # 每5次操作执行一次异常检测
                        test_data = pd.DataFrame({
                            'timestamp': pd.date_range('2024-01-01', periods=100, freq='min'),
                            'symbol': f'STABILITY_{operations_completed}',
                            'price': np.concatenate([
                                np.random.normal(100, 10, 90),
                                [np.nan] * 5,
                                np.random.normal(300, 50, 5)
                            ]),
                            'volume': np.random.randint(1000, 100000, 100)
                        })
                        
                        anomalies = detector.detect_anomalies(
                            data=test_data,
                            data_source="stability_test",
                            symbol=f"STABILITY_{operations_completed}",
                            data_type="kline"
                        )
                        
                        # 尝试修复一些异常
                        for anomaly in anomalies[:2]:
                            detector.auto_repair_anomaly(anomaly.anomaly_id)
                    
                    # 3. 数据集成操作
                    if operations_completed % 3 == 0:  # 每3次操作执行一次数据集成
                        cache_key = f"stability_test_{operations_completed}"
                        test_data = {
                            'symbol': f"STABILITY_{operations_completed:06d}",
                            'price': 10.0 + (operations_completed % 100) * 0.1,
                            'volume': 1000 + operations_completed * 10
                        }
                        
                        integration._put_to_intelligent_cache(cache_key, test_data, "high", 300)
                        cached_data = integration._get_from_intelligent_cache(cache_key)
                        
                        integration._record_usage_pattern(
                            "stability_widget", 
                            f"STABILITY_{operations_completed:06d}", 
                            "realtime"
                        )
                    
                    operations_completed += 1
                    
                    # 定期清理以避免数据积累过多
                    if operations_completed % 100 == 0:
                        # 清理旧的异常记录
                        detector.cleanup_old_records(days=0)
                        
                        # 清理旧的任务（保留最近50个）
                        all_tasks = manager.get_all_import_tasks()
                        if len(all_tasks) > 50:
                            task_ids = list(all_tasks.keys())
                            for task_id in task_ids[:-50]:  # 删除除最后50个外的所有任务
                                manager.remove_import_task(task_id)
                        
                        # 垃圾回收
                        gc.collect()
                    
                    # 记录内存使用
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
                    
                    # 定期报告
                    current_time = time.time()
                    if current_time - last_report_time >= report_interval:
                        elapsed_time = current_time - start_time
                        operations_per_second = operations_completed / elapsed_time
                        avg_memory = np.mean(memory_samples[-10:]) if memory_samples else 0
                        
                        print(f"  运行时间: {elapsed_time:.0f}s, 完成操作: {operations_completed}, "
                              f"速度: {operations_per_second:.1f}ops/s, 内存: {avg_memory:.1f}MB, "
                              f"错误: {errors_encountered}")
                        
                        last_report_time = current_time
                    
                    # 控制操作频率，避免过于频繁
                    operation_time = time.time() - operation_start
                    if operation_time < 0.1:  # 如果操作太快，稍微等待
                        time.sleep(0.1 - operation_time)
                
                except Exception as e:
                    errors_encountered += 1
                    if errors_encountered <= 10:  # 只打印前10个错误
                        print(f"  操作 {operations_completed} 出错: {e}")
        
        finally:
            # 清理资源
            try:
                integration.close()
            except:
                pass
        
        # 测试结果分析
        total_time = time.time() - start_time
        operations_per_second = operations_completed / total_time if total_time > 0 else 0
        error_rate = errors_encountered / operations_completed if operations_completed > 0 else 0
        
        # 内存分析
        if memory_samples:
            initial_memory = memory_samples[0]
            final_memory = memory_samples[-1]
            max_memory = max(memory_samples)
            avg_memory = np.mean(memory_samples)
            memory_growth = final_memory - initial_memory
        else:
            initial_memory = final_memory = max_memory = avg_memory = memory_growth = 0
        
        print(f"连续操作稳定性测试结果:")
        print(f"  测试时长: {total_time:.2f}秒 ({total_time/60:.1f}分钟)")
        print(f"  完成操作数: {operations_completed}")
        print(f"  遇到错误数: {errors_encountered}")
        print(f"  操作速度: {operations_per_second:.2f} 操作/秒")
        print(f"  错误率: {error_rate:.4f} ({error_rate*100:.2f}%)")
        print(f"  内存使用:")
        print(f"    初始: {initial_memory:.1f}MB")
        print(f"    最终: {final_memory:.1f}MB")
        print(f"    最大: {max_memory:.1f}MB")
        print(f"    平均: {avg_memory:.1f}MB")
        print(f"    增长: {memory_growth:.1f}MB")
        
        # 稳定性断言
        self.assertGreater(operations_completed, test_duration / 2)  # 至少每2秒完成一个操作
        self.assertLess(error_rate, 0.05)  # 错误率小于5%
        self.assertLess(memory_growth, 200)  # 内存增长小于200MB
        self.assertGreater(operations_per_second, 0.5)  # 至少每秒0.5个操作

    def test_exception_recovery(self):
        """测试异常恢复能力"""
        print("\n--- 测试异常恢复能力 ---")
        
        manager = IntelligentConfigManager(self.db_path)
        
        # 测试各种异常情况下的恢复能力
        recovery_tests = [
            {
                'name': '数据库连接异常',
                'exception_func': lambda: self._simulate_db_error(manager),
                'recovery_func': lambda: self._verify_db_recovery(manager)
            },
            {
                'name': '内存不足异常',
                'exception_func': lambda: self._simulate_memory_error(manager),
                'recovery_func': lambda: self._verify_memory_recovery(manager)
            },
            {
                'name': '文件系统异常',
                'exception_func': lambda: self._simulate_file_error(manager),
                'recovery_func': lambda: self._verify_file_recovery(manager)
            }
        ]
        
        recovery_results = []
        
        for test in recovery_tests:
            print(f"  测试 {test['name']}...")
            
            try:
                # 记录异常前状态
                initial_tasks = len(manager.get_all_import_tasks())
                
                # 模拟异常
                test['exception_func']()
                
                # 等待一段时间让系统处理异常
                time.sleep(1)
                
                # 验证恢复
                recovery_success = test['recovery_func']()
                
                # 记录恢复后状态
                final_tasks = len(manager.get_all_import_tasks())
                
                recovery_results.append({
                    'test_name': test['name'],
                    'recovery_success': recovery_success,
                    'initial_tasks': initial_tasks,
                    'final_tasks': final_tasks
                })
                
                print(f"    恢复结果: {'成功' if recovery_success else '失败'}")
                
            except Exception as e:
                print(f"    测试异常: {e}")
                recovery_results.append({
                    'test_name': test['name'],
                    'recovery_success': False,
                    'error': str(e)
                })
        
        # 分析恢复结果
        successful_recoveries = sum(1 for r in recovery_results if r.get('recovery_success', False))
        total_tests = len(recovery_results)
        
        print(f"异常恢复测试结果:")
        print(f"  总测试数: {total_tests}")
        print(f"  成功恢复: {successful_recoveries}")
        print(f"  恢复成功率: {successful_recoveries/total_tests:.2%}")
        
        for result in recovery_results:
            status = "成功" if result.get('recovery_success', False) else "失败"
            print(f"  {result['test_name']}: {status}")
            if 'error' in result:
                print(f"    错误: {result['error']}")
        
        # 恢复能力断言
        self.assertGreaterEqual(successful_recoveries, total_tests * 0.7)  # 至少70%恢复成功

    def _simulate_db_error(self, manager):
        """模拟数据库错误"""
        # 临时修改数据库路径为无效路径
        original_path = manager.db_path
        manager.db_path = "/invalid/path/database.sqlite"
        
        try:
            # 尝试执行数据库操作
            config = ImportTaskConfig(
                task_id="db_error_test",
                name="数据库错误测试",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH
            )
            manager.add_import_task(config)
        except:
            pass  # 预期会出错
        finally:
            # 恢复正确的数据库路径
            manager.db_path = original_path

    def _verify_db_recovery(self, manager):
        """验证数据库恢复"""
        try:
            # 尝试正常的数据库操作
            config = ImportTaskConfig(
                task_id="db_recovery_test",
                name="数据库恢复测试",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH
            )
            
            success = manager.add_import_task(config)
            if success:
                # 验证任务确实被添加
                retrieved = manager.get_import_task("db_recovery_test")
                return retrieved is not None
            
            return False
        except:
            return False

    def _simulate_memory_error(self, manager):
        """模拟内存不足错误"""
        # 创建大量对象消耗内存
        large_objects = []
        try:
            for i in range(1000):
                # 创建大型DataFrame
                large_data = pd.DataFrame(np.random.rand(1000, 100))
                large_objects.append(large_data)
        except MemoryError:
            pass  # 预期可能出现内存错误
        finally:
            # 清理大对象
            del large_objects
            gc.collect()

    def _verify_memory_recovery(self, manager):
        """验证内存恢复"""
        try:
            # 执行正常操作验证系统仍然可用
            stats = manager.get_intelligent_statistics()
            return isinstance(stats, dict) and 'total_tasks' in stats
        except:
            return False

    def _simulate_file_error(self, manager):
        """模拟文件系统错误"""
        # 尝试访问不存在的文件
        try:
            with open("/nonexistent/path/file.txt", "r") as f:
                f.read()
        except:
            pass  # 预期会出错

    def _verify_file_recovery(self, manager):
        """验证文件系统恢复"""
        try:
            # 验证正常的文件操作
            conflicts = manager.detect_conflicts()
            return isinstance(conflicts, list)
        except:
            return False


def run_long_term_stability_tests():
    """运行长期稳定性测试"""
    print("开始运行长期稳定性测试...")
    print("=" * 100)
    
    # 检查测试环境
    test_duration = int(os.environ.get('STABILITY_TEST_DURATION', '300'))
    print(f"稳定性测试持续时间: {test_duration} 秒 ({test_duration/60:.1f} 分钟)")
    print("提示: 可通过环境变量 STABILITY_TEST_DURATION 调整测试时长")
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestMemoryLeakDetection,
        TestResourceLeakDetection,
        TestLongRunningStability
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    print("=" * 100)
    print(f"长期稳定性测试完成！")
    print(f"成功: {'是' if result.wasSuccessful() else '否'}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 所有长期稳定性测试通过！")
        print("系统具备良好的长期运行稳定性，适合生产环境部署。")
    else:
        print("❌ 存在稳定性测试失败或错误")
        
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\n错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful(), len(result.failures), len(result.errors)


if __name__ == "__main__":
    # 设置测试环境
    os.environ['TESTING'] = '1'
    
    # 运行长期稳定性测试
    success, failures, errors = run_long_term_stability_tests()
    
    # 返回适当的退出码
    exit_code = 0 if success else 1
    exit(exit_code)
