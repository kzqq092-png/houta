#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大规模数据处理压力测试

执行大规模数据处理的压力测试和性能验证，验证系统在高负载下的稳定性和性能。
测试场景包括：
1. 大数据量导入测试
2. 高并发任务执行测试
3. 长时间运行压力测试
4. 内存和CPU压力测试
5. 数据库性能压力测试
"""

import pytest
import unittest
import tempfile
import os
import time
import threading
import multiprocessing
import psutil
import gc
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from unittest.mock import patch, Mock
import sqlite3
import json
from pathlib import Path

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


class LargeScalePerformanceTest(unittest.TestCase):
    """大规模性能测试基类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_start_time = time.time()
        cls.process = psutil.Process()
        cls.initial_memory = cls.process.memory_info().rss / 1024 / 1024  # MB
        cls.initial_cpu_percent = cls.process.cpu_percent()
        
        print(f"\n{'='*80}")
        print(f"开始大规模性能测试")
        print(f"初始内存使用: {cls.initial_memory:.1f} MB")
        print(f"测试进程PID: {os.getpid()}")
        print(f"CPU核心数: {multiprocessing.cpu_count()}")
        print(f"{'='*80}")

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        final_memory = cls.process.memory_info().rss / 1024 / 1024  # MB
        final_cpu_percent = cls.process.cpu_percent()
        test_duration = time.time() - cls.test_start_time
        
        print(f"\n{'='*80}")
        print(f"大规模性能测试完成")
        print(f"测试总耗时: {test_duration:.2f} 秒")
        print(f"最终内存使用: {final_memory:.1f} MB")
        print(f"内存增长: {final_memory - cls.initial_memory:.1f} MB")
        print(f"平均CPU使用率: {final_cpu_percent:.1f}%")
        print(f"{'='*80}")

    def setUp(self):
        """每个测试前的准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 记录测试开始时的资源使用情况
        self.test_start_memory = self.process.memory_info().rss / 1024 / 1024
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
        test_duration = time.time() - self.test_start_time
        memory_increase = test_end_memory - self.test_start_memory
        
        print(f"  测试耗时: {test_duration:.2f}s, 内存增长: {memory_increase:.1f}MB")


class TestLargeDatasetProcessing(LargeScalePerformanceTest):
    """大数据集处理测试"""

    def test_massive_task_creation(self):
        """测试大量任务创建性能"""
        print("\n--- 测试大量任务创建性能 ---")
        
        manager = IntelligentConfigManager(self.db_path)
        
        # 创建1000个任务
        num_tasks = 1000
        tasks_created = 0
        failed_tasks = 0
        
        start_time = time.time()
        
        for i in range(num_tasks):
            try:
                config = ImportTaskConfig(
                    task_id=f"massive_test_{i:04d}",
                    name=f"大规模测试任务{i}",
                    data_source="tongdaxin" if i % 2 == 0 else "akshare",
                    asset_type="stock",
                    data_type="kline",
                    symbols=[f"{j:06d}" for j in range(i % 10, (i % 10) + 5)],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH,
                    max_workers=2 + (i % 4),
                    batch_size=500 + (i * 10)
                )
                
                success = manager.add_import_task(config)
                if success:
                    tasks_created += 1
                else:
                    failed_tasks += 1
                    
            except Exception as e:
                failed_tasks += 1
                if failed_tasks <= 5:  # 只打印前5个错误
                    print(f"任务创建失败 {i}: {e}")
        
        creation_time = time.time() - start_time
        
        # 验证结果
        all_tasks = manager.get_all_import_tasks()
        
        print(f"任务创建完成:")
        print(f"  目标任务数: {num_tasks}")
        print(f"  成功创建: {tasks_created}")
        print(f"  创建失败: {failed_tasks}")
        print(f"  实际存储: {len(all_tasks)}")
        print(f"  总耗时: {creation_time:.2f}秒")
        print(f"  平均创建速度: {tasks_created/creation_time:.1f}任务/秒")
        
        # 性能断言
        self.assertGreater(tasks_created, num_tasks * 0.95)  # 至少95%成功
        self.assertLess(creation_time, 60)  # 1分钟内完成
        self.assertGreater(tasks_created/creation_time, 10)  # 至少10任务/秒

    def test_massive_performance_data_recording(self):
        """测试大量性能数据记录"""
        print("\n--- 测试大量性能数据记录 ---")
        
        manager = IntelligentConfigManager(self.db_path)
        
        # 创建基础任务
        base_config = ImportTaskConfig(
            task_id="perf_test_base",
            name="性能测试基础任务",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH
        )
        manager.add_import_task(base_config)
        
        # 记录大量性能数据
        num_records = 10000
        records_created = 0
        
        start_time = time.time()
        
        for i in range(num_records):
            try:
                manager.record_performance_feedback(
                    config=base_config,
                    execution_time=np.random.uniform(30, 300),
                    success_rate=np.random.uniform(0.7, 1.0),
                    error_rate=np.random.uniform(0.0, 0.3),
                    throughput=np.random.uniform(100, 2000)
                )
                records_created += 1
                
            except Exception as e:
                if records_created <= 5:  # 只打印前5个错误
                    print(f"性能记录失败 {i}: {e}")
        
        recording_time = time.time() - start_time
        
        # 获取统计信息
        stats = manager.get_intelligent_statistics()
        
        print(f"性能数据记录完成:")
        print(f"  目标记录数: {num_records}")
        print(f"  成功记录: {records_created}")
        print(f"  统计记录数: {stats['performance_history_count']}")
        print(f"  总耗时: {recording_time:.2f}秒")
        print(f"  平均记录速度: {records_created/recording_time:.1f}记录/秒")
        
        # 性能断言
        self.assertGreater(records_created, num_records * 0.95)  # 至少95%成功
        self.assertLess(recording_time, 120)  # 2分钟内完成
        self.assertGreater(records_created/recording_time, 50)  # 至少50记录/秒

    def test_large_dataset_anomaly_detection(self):
        """测试大数据集异常检测性能"""
        print("\n--- 测试大数据集异常检测性能 ---")
        
        config = AnomalyDetectionConfig(
            auto_repair_enabled=True,
            enable_outlier_detection=True,
            enable_missing_data_detection=True,
            enable_duplicate_detection=True
        )
        detector = DataAnomalyDetector(config, self.db_path)
        
        # 创建大型数据集 (100,000 行)
        print("生成大型测试数据集...")
        dataset_size = 100000
        
        np.random.seed(42)
        
        # 生成基础数据
        base_data = pd.DataFrame({
            'timestamp': pd.date_range('2020-01-01', periods=dataset_size, freq='min'),
            'symbol': np.random.choice(['000001', '000002', '000300', '000858'], dataset_size),
            'price': np.random.normal(100, 15, dataset_size),
            'volume': np.random.randint(1000, 100000, dataset_size),
            'high': np.random.normal(105, 15, dataset_size),
            'low': np.random.normal(95, 15, dataset_size),
            'amount': np.random.uniform(100000, 10000000, dataset_size)
        })
        
        # 注入各种异常
        print("注入异常数据...")
        
        # 1. 缺失数据 (5%)
        missing_indices = np.random.choice(dataset_size, int(dataset_size * 0.05), replace=False)
        base_data.loc[missing_indices, 'price'] = np.nan
        
        # 2. 异常值 (3%)
        outlier_indices = np.random.choice(dataset_size, int(dataset_size * 0.03), replace=False)
        base_data.loc[outlier_indices, 'price'] = np.random.choice([500, 1000, -50, 0], len(outlier_indices))
        
        # 3. 重复数据 (2%)
        duplicate_indices = np.random.choice(dataset_size-1, int(dataset_size * 0.02), replace=False)
        for idx in duplicate_indices:
            if idx < dataset_size - 1:
                base_data.loc[idx + 1] = base_data.loc[idx]
        
        # 4. 零交易量 (1%)
        zero_volume_indices = np.random.choice(dataset_size, int(dataset_size * 0.01), replace=False)
        base_data.loc[zero_volume_indices, 'volume'] = 0
        
        print(f"数据集生成完成: {len(base_data)} 行")
        
        # 执行异常检测
        print("开始异常检测...")
        detection_start = time.time()
        
        anomalies = detector.detect_anomalies(
            data=base_data,
            data_source="large_scale_test",
            symbol="LARGE_DATASET",
            data_type="kline"
        )
        
        detection_time = time.time() - detection_start
        
        print(f"异常检测完成:")
        print(f"  数据集大小: {len(base_data):,} 行")
        print(f"  检测到异常: {len(anomalies)} 个")
        print(f"  检测耗时: {detection_time:.2f}秒")
        print(f"  检测速度: {len(base_data)/detection_time:.0f} 行/秒")
        
        # 分析异常类型分布
        anomaly_types = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.anomaly_type.value
            anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1
        
        print(f"  异常类型分布: {anomaly_types}")
        
        # 性能断言
        self.assertGreater(len(anomalies), 0)  # 应该检测到异常
        self.assertLess(detection_time, 300)  # 5分钟内完成
        self.assertGreater(len(base_data)/detection_time, 100)  # 至少100行/秒

    def test_concurrent_anomaly_detection(self):
        """测试并发异常检测性能"""
        print("\n--- 测试并发异常检测性能 ---")
        
        config = AnomalyDetectionConfig(auto_repair_enabled=False)  # 关闭自动修复以提高速度
        detector = DataAnomalyDetector(config, self.db_path)
        
        # 创建多个中等大小的数据集
        def create_test_dataset(dataset_id, size=10000):
            """创建测试数据集"""
            np.random.seed(42 + dataset_id)
            
            data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=size, freq='min'),
                'symbol': f'TEST{dataset_id:03d}',
                'price': np.concatenate([
                    np.random.normal(100, 10, int(size * 0.9)),  # 90% 正常数据
                    np.random.normal(300, 50, int(size * 0.05)),  # 5% 异常值
                    [np.nan] * int(size * 0.05)  # 5% 缺失数据
                ]),
                'volume': np.random.randint(1000, 100000, size)
            })
            
            return data, dataset_id
        
        def detect_anomalies_worker(args):
            """异常检测工作函数"""
            data, dataset_id = args
            start_time = time.time()
            
            try:
                anomalies = detector.detect_anomalies(
                    data=data,
                    data_source="concurrent_test",
                    symbol=f"DATASET_{dataset_id}",
                    data_type="kline"
                )
                
                detection_time = time.time() - start_time
                
                return {
                    'dataset_id': dataset_id,
                    'success': True,
                    'anomaly_count': len(anomalies),
                    'detection_time': detection_time,
                    'data_size': len(data),
                    'error': None
                }
                
            except Exception as e:
                return {
                    'dataset_id': dataset_id,
                    'success': False,
                    'anomaly_count': 0,
                    'detection_time': time.time() - start_time,
                    'data_size': len(data),
                    'error': str(e)
                }
        
        # 创建测试数据集
        num_datasets = 20
        datasets = []
        
        print(f"创建 {num_datasets} 个测试数据集...")
        for i in range(num_datasets):
            dataset = create_test_dataset(i, size=5000)  # 每个数据集5000行
            datasets.append(dataset)
        
        # 并发执行异常检测
        print("开始并发异常检测...")
        concurrent_start = time.time()
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(detect_anomalies_worker, datasets))
        
        concurrent_time = time.time() - concurrent_start
        
        # 分析结果
        successful_detections = [r for r in results if r['success']]
        failed_detections = [r for r in results if not r['success']]
        
        total_anomalies = sum(r['anomaly_count'] for r in successful_detections)
        total_data_size = sum(r['data_size'] for r in successful_detections)
        avg_detection_time = np.mean([r['detection_time'] for r in successful_detections]) if successful_detections else 0
        
        print(f"并发异常检测完成:")
        print(f"  数据集数量: {num_datasets}")
        print(f"  成功检测: {len(successful_detections)}")
        print(f"  检测失败: {len(failed_detections)}")
        print(f"  总数据量: {total_data_size:,} 行")
        print(f"  总异常数: {total_anomalies}")
        print(f"  并发总耗时: {concurrent_time:.2f}秒")
        print(f"  平均单个检测时间: {avg_detection_time:.2f}秒")
        print(f"  并发处理速度: {total_data_size/concurrent_time:.0f} 行/秒")
        
        if failed_detections:
            print(f"  失败详情:")
            for failure in failed_detections[:3]:  # 只显示前3个失败
                print(f"    数据集{failure['dataset_id']}: {failure['error']}")
        
        # 性能断言
        self.assertGreater(len(successful_detections), num_datasets * 0.8)  # 至少80%成功
        self.assertLess(concurrent_time, 120)  # 2分钟内完成
        self.assertGreater(total_data_size/concurrent_time, 500)  # 至少500行/秒


class TestHighConcurrencyOperations(LargeScalePerformanceTest):
    """高并发操作测试"""

    def test_concurrent_task_management(self):
        """测试并发任务管理性能"""
        print("\n--- 测试并发任务管理性能 ---")
        
        manager = IntelligentConfigManager(self.db_path)
        
        def task_management_worker(worker_id, num_tasks_per_worker=50):
            """任务管理工作函数"""
            results = {
                'worker_id': worker_id,
                'tasks_created': 0,
                'tasks_updated': 0,
                'tasks_queried': 0,
                'errors': []
            }
            
            created_task_ids = []
            
            try:
                # 创建任务
                for i in range(num_tasks_per_worker):
                    task_id = f"worker_{worker_id}_task_{i:03d}"
                    config = ImportTaskConfig(
                        task_id=task_id,
                        name=f"并发测试任务 Worker{worker_id}-{i}",
                        data_source="tongdaxin" if i % 2 == 0 else "akshare",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{(worker_id*100+i):06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH,
                        max_workers=2 + (i % 4),
                        batch_size=500 + (i * 10)
                    )
                    
                    if manager.add_import_task(config):
                        results['tasks_created'] += 1
                        created_task_ids.append(task_id)
                
                # 更新任务
                for task_id in created_task_ids[:num_tasks_per_worker//2]:
                    try:
                        config = manager.get_import_task(task_id)
                        if config:
                            config.max_workers = 6
                            config.batch_size = 1500
                            if manager.update_import_task(config):
                                results['tasks_updated'] += 1
                    except Exception as e:
                        results['errors'].append(f"更新任务失败 {task_id}: {e}")
                
                # 查询任务
                for task_id in created_task_ids:
                    try:
                        config = manager.get_import_task(task_id)
                        if config:
                            results['tasks_queried'] += 1
                    except Exception as e:
                        results['errors'].append(f"查询任务失败 {task_id}: {e}")
                
            except Exception as e:
                results['errors'].append(f"Worker {worker_id} 执行异常: {e}")
            
            return results
        
        # 启动多个并发工作线程
        num_workers = 10
        tasks_per_worker = 30
        
        print(f"启动 {num_workers} 个并发工作线程，每个创建 {tasks_per_worker} 个任务...")
        
        concurrent_start = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(task_management_worker, i, tasks_per_worker) 
                      for i in range(num_workers)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Worker执行异常: {e}")
        
        concurrent_time = time.time() - concurrent_start
        
        # 统计结果
        total_created = sum(r['tasks_created'] for r in results)
        total_updated = sum(r['tasks_updated'] for r in results)
        total_queried = sum(r['tasks_queried'] for r in results)
        total_errors = sum(len(r['errors']) for r in results)
        
        # 验证数据库中的实际任务数
        all_tasks = manager.get_all_import_tasks()
        
        print(f"并发任务管理完成:")
        print(f"  工作线程数: {num_workers}")
        print(f"  目标任务总数: {num_workers * tasks_per_worker}")
        print(f"  实际创建任务: {total_created}")
        print(f"  更新任务数: {total_updated}")
        print(f"  查询任务数: {total_queried}")
        print(f"  数据库任务数: {len(all_tasks)}")
        print(f"  总错误数: {total_errors}")
        print(f"  并发总耗时: {concurrent_time:.2f}秒")
        print(f"  任务创建速度: {total_created/concurrent_time:.1f} 任务/秒")
        
        # 显示部分错误信息
        if total_errors > 0:
            print("  错误示例:")
            error_count = 0
            for result in results:
                for error in result['errors'][:2]:  # 每个worker最多显示2个错误
                    print(f"    {error}")
                    error_count += 1
                    if error_count >= 5:  # 最多显示5个错误
                        break
                if error_count >= 5:
                    break
        
        # 性能断言
        self.assertGreater(total_created, num_workers * tasks_per_worker * 0.8)  # 至少80%成功
        self.assertLess(concurrent_time, 60)  # 1分钟内完成
        self.assertGreater(total_created/concurrent_time, 20)  # 至少20任务/秒

    def test_concurrent_data_integration(self):
        """测试并发数据集成性能"""
        print("\n--- 测试并发数据集成性能 ---")
        
        config = UIIntegrationConfig(
            enable_caching=True,
            cache_expiry_seconds=300,
            enable_predictive_loading=True,
            enable_adaptive_caching=True
        )
        
        with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
            integration = SmartDataIntegration(config)
        
        def data_integration_worker(worker_id, num_requests=100):
            """数据集成工作函数"""
            results = {
                'worker_id': worker_id,
                'successful_requests': 0,
                'failed_requests': 0,
                'cache_hits': 0,
                'total_response_time': 0,
                'errors': []
            }
            
            try:
                for i in range(num_requests):
                    request_start = time.time()
                    
                    try:
                        # 模拟数据请求
                        widget_type = f"stock_quote_{i % 5}"
                        symbol = f"{(worker_id*1000+i):06d}"
                        data_type = "realtime" if i % 2 == 0 else "daily"
                        
                        # 检查缓存
                        cache_key = f"{widget_type}_{symbol}_{data_type}"
                        cached_data = integration._get_from_intelligent_cache(cache_key)
                        
                        if cached_data:
                            results['cache_hits'] += 1
                            results['successful_requests'] += 1
                        else:
                            # 模拟数据获取
                            mock_data = {
                                'symbol': symbol,
                                'price': 10.0 + (i % 100) * 0.1,
                                'volume': 1000 + i * 10,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # 存入缓存
                            integration._put_to_intelligent_cache(
                                cache_key, mock_data, "high", 300
                            )
                            
                            results['successful_requests'] += 1
                        
                        # 记录使用模式
                        integration._record_usage_pattern(widget_type, symbol, data_type)
                        
                    except Exception as e:
                        results['failed_requests'] += 1
                        if len(results['errors']) < 5:  # 只记录前5个错误
                            results['errors'].append(f"请求失败 {i}: {e}")
                    
                    request_time = time.time() - request_start
                    results['total_response_time'] += request_time
                
            except Exception as e:
                results['errors'].append(f"Worker {worker_id} 执行异常: {e}")
            
            return results
        
        # 启动并发数据集成测试
        num_workers = 15
        requests_per_worker = 50
        
        print(f"启动 {num_workers} 个并发工作线程，每个执行 {requests_per_worker} 个数据请求...")
        
        concurrent_start = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(data_integration_worker, i, requests_per_worker) 
                      for i in range(num_workers)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Worker执行异常: {e}")
        
        concurrent_time = time.time() - concurrent_start
        
        # 统计结果
        total_successful = sum(r['successful_requests'] for r in results)
        total_failed = sum(r['failed_requests'] for r in results)
        total_cache_hits = sum(r['cache_hits'] for r in results)
        total_response_time = sum(r['total_response_time'] for r in results)
        total_errors = sum(len(r['errors']) for r in results)
        
        avg_response_time = total_response_time / total_successful if total_successful > 0 else 0
        cache_hit_rate = total_cache_hits / total_successful if total_successful > 0 else 0
        
        # 获取集成统计信息
        integration_stats = integration.get_statistics()
        
        print(f"并发数据集成完成:")
        print(f"  工作线程数: {num_workers}")
        print(f"  目标请求总数: {num_workers * requests_per_worker}")
        print(f"  成功请求数: {total_successful}")
        print(f"  失败请求数: {total_failed}")
        print(f"  缓存命中数: {total_cache_hits}")
        print(f"  缓存命中率: {cache_hit_rate:.2%}")
        print(f"  平均响应时间: {avg_response_time*1000:.2f}ms")
        print(f"  并发总耗时: {concurrent_time:.2f}秒")
        print(f"  请求处理速度: {total_successful/concurrent_time:.1f} 请求/秒")
        print(f"  总错误数: {total_errors}")
        
        # 清理资源
        try:
            integration.close()
        except:
            pass
        
        # 性能断言
        self.assertGreater(total_successful, num_workers * requests_per_worker * 0.9)  # 至少90%成功
        self.assertLess(concurrent_time, 30)  # 30秒内完成
        self.assertGreater(total_successful/concurrent_time, 50)  # 至少50请求/秒
        self.assertLess(avg_response_time, 0.1)  # 平均响应时间小于100ms


class TestMemoryAndResourceStress(LargeScalePerformanceTest):
    """内存和资源压力测试"""

    def test_memory_usage_under_extreme_load(self):
        """测试极端负载下的内存使用"""
        print("\n--- 测试极端负载下的内存使用 ---")
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        # 创建多个组件实例
        managers = []
        detectors = []
        integrations = []
        
        try:
            # 创建多个配置管理器实例
            print("创建多个配置管理器实例...")
            for i in range(10):
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                manager = IntelligentConfigManager(temp_db.name)
                managers.append((manager, temp_db.name))
                
                # 为每个管理器创建任务
                for j in range(100):
                    config = ImportTaskConfig(
                        task_id=f"memory_test_{i}_{j}",
                        name=f"内存测试任务{i}-{j}",
                        data_source="tongdaxin",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{(i*100+j):06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH
                    )
                    manager.add_import_task(config)
                
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
            
            print(f"配置管理器创建完成，当前内存: {current_memory:.1f}MB")
            
            # 创建多个异常检测器实例
            print("创建多个异常检测器实例...")
            for i in range(5):
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                config = AnomalyDetectionConfig()
                detector = DataAnomalyDetector(config, temp_db.name)
                detectors.append((detector, temp_db.name))
                
                # 为每个检测器处理数据
                test_data = pd.DataFrame({
                    'price': np.random.normal(100, 10, 10000),
                    'volume': np.random.randint(1000, 100000, 10000),
                    'timestamp': pd.date_range('2024-01-01', periods=10000, freq='min')
                })
                
                # 注入异常
                test_data.loc[np.random.choice(10000, 500, replace=False), 'price'] = np.nan
                
                anomalies = detector.detect_anomalies(
                    data=test_data,
                    data_source=f"memory_test_{i}",
                    symbol=f"MEM_TEST_{i}",
                    data_type="kline"
                )
                
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
            
            print(f"异常检测器创建完成，当前内存: {current_memory:.1f}MB")
            
            # 创建多个数据集成实例
            print("创建多个数据集成实例...")
            for i in range(5):
                config = UIIntegrationConfig(enable_caching=True)
                
                with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
                    integration = SmartDataIntegration(config)
                    integrations.append(integration)
                
                # 为每个集成实例添加缓存数据
                for j in range(1000):
                    cache_key = f"memory_test_{i}_{j}"
                    test_data = {
                        'symbol': f"TEST{j:06d}",
                        'data': [{'price': 10.0 + k * 0.1, 'volume': 1000 + k * 10} 
                                for k in range(100)]
                    }
                    integration._put_to_intelligent_cache(cache_key, test_data, "high", 3600)
                
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
            
            print(f"数据集成实例创建完成，当前内存: {current_memory:.1f}MB")
            
            # 执行内存密集型操作
            print("执行内存密集型操作...")
            
            # 大量数据处理
            large_datasets = []
            for i in range(5):
                large_data = pd.DataFrame({
                    'timestamp': pd.date_range('2020-01-01', periods=50000, freq='min'),
                    'symbol': f'LARGE_{i}',
                    'price': np.random.normal(100, 15, 50000),
                    'volume': np.random.randint(1000, 100000, 50000)
                })
                large_datasets.append(large_data)
                
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
            
            print(f"大数据集创建完成，当前内存: {current_memory:.1f}MB")
            
            # 强制垃圾回收
            print("执行垃圾回收...")
            gc.collect()
            
            after_gc_memory = self.process.memory_info().rss / 1024 / 1024
            
            print(f"内存使用情况:")
            print(f"  初始内存: {initial_memory:.1f}MB")
            print(f"  峰值内存: {peak_memory:.1f}MB")
            print(f"  GC后内存: {after_gc_memory:.1f}MB")
            print(f"  内存增长: {peak_memory - initial_memory:.1f}MB")
            print(f"  GC回收: {peak_memory - after_gc_memory:.1f}MB")
            
            # 内存使用断言
            memory_increase = peak_memory - initial_memory
            self.assertLess(memory_increase, 2000)  # 内存增长不超过2GB
            
            # GC效果断言
            gc_recovered = peak_memory - after_gc_memory
            self.assertGreater(gc_recovered, memory_increase * 0.3)  # GC至少回收30%
            
        finally:
            # 清理资源
            print("清理测试资源...")
            
            for manager, db_path in managers:
                try:
                    os.unlink(db_path)
                except:
                    pass
            
            for detector, db_path in detectors:
                try:
                    os.unlink(db_path)
                except:
                    pass
            
            for integration in integrations:
                try:
                    integration.close()
                except:
                    pass
            
            # 最终垃圾回收
            gc.collect()
            
            final_memory = self.process.memory_info().rss / 1024 / 1024
            print(f"  最终内存: {final_memory:.1f}MB")

    def test_cpu_intensive_operations(self):
        """测试CPU密集型操作"""
        print("\n--- 测试CPU密集型操作 ---")
        
        initial_cpu = self.process.cpu_percent()
        
        def cpu_intensive_task(task_id, duration=10):
            """CPU密集型任务"""
            start_time = time.time()
            operation_count = 0
            
            # 创建临时数据库
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
            temp_db.close()
            
            try:
                manager = IntelligentConfigManager(temp_db.name)
                detector_config = AnomalyDetectionConfig()
                detector = DataAnomalyDetector(detector_config, temp_db.name)
                
                while time.time() - start_time < duration:
                    # 1. 创建和管理任务
                    for i in range(10):
                        config = ImportTaskConfig(
                            task_id=f"cpu_test_{task_id}_{operation_count}_{i}",
                            name=f"CPU测试任务{task_id}-{operation_count}-{i}",
                            data_source="tongdaxin",
                            asset_type="stock",
                            data_type="kline",
                            symbols=[f"{(task_id*10000+operation_count*10+i):06d}"],
                            frequency=DataFrequency.DAILY,
                            mode=ImportMode.BATCH
                        )
                        manager.add_import_task(config)
                    
                    # 2. 生成和处理数据
                    test_data = pd.DataFrame({
                        'price': np.random.normal(100, 10, 1000),
                        'volume': np.random.randint(1000, 100000, 1000),
                        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='min')
                    })
                    
                    # 注入异常
                    test_data.loc[np.random.choice(1000, 50, replace=False), 'price'] = np.nan
                    test_data.loc[np.random.choice(1000, 30, replace=False), 'price'] = np.random.normal(500, 50, 30)
                    
                    # 3. 异常检测
                    anomalies = detector.detect_anomalies(
                        data=test_data,
                        data_source=f"cpu_test_{task_id}",
                        symbol=f"CPU_TEST_{operation_count}",
                        data_type="kline"
                    )
                    
                    # 4. 数学计算
                    matrix_a = np.random.rand(100, 100)
                    matrix_b = np.random.rand(100, 100)
                    result = np.dot(matrix_a, matrix_b)
                    
                    operation_count += 1
                
                return {
                    'task_id': task_id,
                    'operations_completed': operation_count,
                    'duration': time.time() - start_time,
                    'operations_per_second': operation_count / (time.time() - start_time)
                }
                
            finally:
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
        
        # 启动多个CPU密集型任务
        num_cpu_tasks = multiprocessing.cpu_count()
        task_duration = 15  # 15秒
        
        print(f"启动 {num_cpu_tasks} 个CPU密集型任务，每个运行 {task_duration} 秒...")
        
        cpu_test_start = time.time()
        
        with ProcessPoolExecutor(max_workers=num_cpu_tasks) as executor:
            futures = [executor.submit(cpu_intensive_task, i, task_duration) 
                      for i in range(num_cpu_tasks)]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"CPU任务执行异常: {e}")
        
        cpu_test_time = time.time() - cpu_test_start
        
        # 获取CPU使用率
        final_cpu = self.process.cpu_percent()
        
        # 统计结果
        total_operations = sum(r['operations_completed'] for r in results)
        avg_ops_per_second = np.mean([r['operations_per_second'] for r in results])
        
        print(f"CPU密集型测试完成:")
        print(f"  并发任务数: {num_cpu_tasks}")
        print(f"  总测试时间: {cpu_test_time:.2f}秒")
        print(f"  总操作次数: {total_operations}")
        print(f"  平均操作速度: {avg_ops_per_second:.1f} 操作/秒")
        print(f"  初始CPU使用率: {initial_cpu:.1f}%")
        print(f"  最终CPU使用率: {final_cpu:.1f}%")
        
        # 性能断言
        self.assertGreater(total_operations, num_cpu_tasks * 10)  # 每个任务至少完成10个操作
        self.assertLess(cpu_test_time, task_duration + 5)  # 测试时间不应该超出太多


class TestDatabasePerformanceStress(LargeScalePerformanceTest):
    """数据库性能压力测试"""

    def test_massive_database_operations(self):
        """测试大规模数据库操作"""
        print("\n--- 测试大规模数据库操作 ---")
        
        manager = IntelligentConfigManager(self.db_path)
        
        # 1. 大量插入操作
        print("执行大量插入操作...")
        insert_start = time.time()
        
        num_tasks = 5000
        batch_size = 100
        
        for batch_start in range(0, num_tasks, batch_size):
            batch_end = min(batch_start + batch_size, num_tasks)
            
            # 批量创建任务
            for i in range(batch_start, batch_end):
                config = ImportTaskConfig(
                    task_id=f"db_stress_{i:05d}",
                    name=f"数据库压力测试任务{i}",
                    data_source="tongdaxin" if i % 3 == 0 else ("akshare" if i % 3 == 1 else "wind"),
                    asset_type="stock" if i % 2 == 0 else "index",
                    data_type="kline",
                    symbols=[f"{(i % 1000):06d}", f"{((i+1) % 1000):06d}"],
                    frequency=DataFrequency.DAILY if i % 2 == 0 else DataFrequency.MINUTE,
                    mode=ImportMode.BATCH if i % 3 == 0 else ImportMode.SCHEDULED,
                    max_workers=2 + (i % 6),
                    batch_size=500 + (i % 1000)
                )
                
                manager.add_import_task(config)
            
            # 每批次后检查进度
            if (batch_end) % 1000 == 0:
                current_time = time.time() - insert_start
                print(f"  已插入 {batch_end} 个任务，耗时 {current_time:.1f}秒")
        
        insert_time = time.time() - insert_start
        
        # 验证插入结果
        all_tasks = manager.get_all_import_tasks()
        
        print(f"插入操作完成:")
        print(f"  目标插入数: {num_tasks}")
        print(f"  实际插入数: {len(all_tasks)}")
        print(f"  插入耗时: {insert_time:.2f}秒")
        print(f"  插入速度: {len(all_tasks)/insert_time:.1f} 任务/秒")
        
        # 2. 大量查询操作
        print("执行大量查询操作...")
        query_start = time.time()
        
        num_queries = 10000
        successful_queries = 0
        
        task_ids = list(all_tasks.keys())
        
        for i in range(num_queries):
            # 随机选择任务ID进行查询
            task_id = np.random.choice(task_ids)
            
            try:
                config = manager.get_import_task(task_id)
                if config:
                    successful_queries += 1
            except Exception as e:
                if successful_queries <= 5:  # 只打印前5个错误
                    print(f"查询失败 {task_id}: {e}")
        
        query_time = time.time() - query_start
        
        print(f"查询操作完成:")
        print(f"  查询次数: {num_queries}")
        print(f"  成功查询: {successful_queries}")
        print(f"  查询耗时: {query_time:.2f}秒")
        print(f"  查询速度: {successful_queries/query_time:.1f} 查询/秒")
        
        # 3. 大量更新操作
        print("执行大量更新操作...")
        update_start = time.time()
        
        num_updates = 1000
        successful_updates = 0
        
        update_task_ids = np.random.choice(task_ids, num_updates, replace=False)
        
        for task_id in update_task_ids:
            try:
                config = manager.get_import_task(task_id)
                if config:
                    # 修改配置
                    config.max_workers = np.random.randint(2, 10)
                    config.batch_size = np.random.randint(500, 2000)
                    
                    if manager.update_import_task(config):
                        successful_updates += 1
            except Exception as e:
                if successful_updates <= 5:  # 只打印前5个错误
                    print(f"更新失败 {task_id}: {e}")
        
        update_time = time.time() - update_start
        
        print(f"更新操作完成:")
        print(f"  更新次数: {num_updates}")
        print(f"  成功更新: {successful_updates}")
        print(f"  更新耗时: {update_time:.2f}秒")
        print(f"  更新速度: {successful_updates/update_time:.1f} 更新/秒")
        
        # 4. 大量性能数据记录
        print("执行大量性能数据记录...")
        perf_start = time.time()
        
        num_perf_records = 50000
        successful_records = 0
        
        # 选择一些任务进行性能记录
        perf_task_ids = np.random.choice(task_ids, min(100, len(task_ids)), replace=False)
        
        for i in range(num_perf_records):
            task_id = np.random.choice(perf_task_ids)
            
            try:
                config = manager.get_import_task(task_id)
                if config:
                    manager.record_performance_feedback(
                        config=config,
                        execution_time=np.random.uniform(30, 300),
                        success_rate=np.random.uniform(0.7, 1.0),
                        error_rate=np.random.uniform(0.0, 0.3),
                        throughput=np.random.uniform(100, 2000)
                    )
                    successful_records += 1
            except Exception as e:
                if successful_records <= 5:  # 只打印前5个错误
                    print(f"性能记录失败: {e}")
        
        perf_time = time.time() - perf_start
        
        # 获取统计信息
        stats = manager.get_intelligent_statistics()
        
        print(f"性能记录完成:")
        print(f"  记录次数: {num_perf_records}")
        print(f"  成功记录: {successful_records}")
        print(f"  记录耗时: {perf_time:.2f}秒")
        print(f"  记录速度: {successful_records/perf_time:.1f} 记录/秒")
        print(f"  统计记录数: {stats['performance_history_count']}")
        
        # 5. 数据库文件大小检查
        db_size = os.path.getsize(self.db_path) / 1024 / 1024  # MB
        print(f"数据库文件大小: {db_size:.1f}MB")
        
        # 总体性能断言
        total_time = insert_time + query_time + update_time + perf_time
        
        print(f"\n数据库压力测试总结:")
        print(f"  总测试时间: {total_time:.2f}秒")
        print(f"  数据库大小: {db_size:.1f}MB")
        
        # 性能断言
        self.assertGreater(len(all_tasks), num_tasks * 0.95)  # 至少95%插入成功
        self.assertGreater(successful_queries, num_queries * 0.95)  # 至少95%查询成功
        self.assertGreater(successful_updates, num_updates * 0.9)  # 至少90%更新成功
        self.assertGreater(successful_records, num_perf_records * 0.9)  # 至少90%记录成功
        self.assertLess(total_time, 300)  # 总时间不超过5分钟
        self.assertLess(db_size, 500)  # 数据库大小不超过500MB


def run_large_scale_performance_tests():
    """运行大规模性能测试"""
    print("开始运行大规模数据处理压力测试...")
    print("=" * 100)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestLargeDatasetProcessing,
        TestHighConcurrencyOperations,
        TestMemoryAndResourceStress,
        TestDatabasePerformanceStress
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    print("=" * 100)
    print(f"大规模性能测试完成！")
    print(f"成功: {'是' if result.wasSuccessful() else '否'}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 所有大规模性能测试通过！")
        print("系统在高负载下表现良好，满足生产环境要求。")
    else:
        print("❌ 存在性能测试失败或错误")
        
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
    
    # 运行大规模性能测试
    success, failures, errors = run_large_scale_performance_tests()
    
    # 返回适当的退出码
    exit_code = 0 if success else 1
    exit(exit_code)
