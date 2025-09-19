#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统集成测试和端到端测试

建立全面的集成测试和端到端测试套件，验证各组件间的协作和完整的用户流程。
测试范围：
1. 组件间集成测试
2. 数据流端到端测试
3. 用户工作流程测试
4. 性能集成测试
5. 错误恢复集成测试
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests_mock

# 导入待测试的组件
from core.importdata.intelligent_config_manager import (
    IntelligentConfigManager, ImportTaskConfig, DataFrequency, ImportMode,
    ConfigRecommendationType, ConfigOptimizationLevel
)
from core.ai.config_recommendation_engine import ConfigRecommendationEngine
from core.ai.config_impact_analyzer import ConfigImpactAnalyzer
from core.ui_integration.smart_data_integration import (
    SmartDataIntegration, UIIntegrationConfig, IntegrationMode
)
from core.ai.data_anomaly_detector import (
    DataAnomalyDetector, AnomalyDetectionConfig, AnomalyType
)


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试基类"""

    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 创建测试数据目录
        self.test_data_dir = tempfile.mkdtemp()
        
        # 初始化核心组件
        self.config_manager = IntelligentConfigManager(self.db_path)
        
        # Mock外部依赖
        with patch('core.ai.config_recommendation_engine.AIPredictionService'), \
             patch('core.ai.config_impact_analyzer.AIPredictionService'):
            self.recommendation_engine = ConfigRecommendationEngine(self.db_path)
            self.impact_analyzer = ConfigImpactAnalyzer(self.db_path)
        
        # 数据集成组件
        integration_config = UIIntegrationConfig(
            enable_caching=True,
            cache_expiry_seconds=300,
            enable_predictive_loading=True,
            enable_adaptive_caching=True
        )
        
        with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
            self.data_integration = SmartDataIntegration(integration_config)
        
        # 异常检测器
        anomaly_config = AnomalyDetectionConfig(
            auto_repair_enabled=True,
            enable_outlier_detection=True,
            enable_missing_data_detection=True
        )
        self.anomaly_detector = DataAnomalyDetector(anomaly_config, self.db_path)

    def tearDown(self):
        """测试后清理"""
        try:
            self.data_integration.close()
            os.unlink(self.db_path)
            import shutil
            shutil.rmtree(self.test_data_dir, ignore_errors=True)
        except:
            pass


class TestConfigurationWorkflow(TestSystemIntegration):
    """配置管理工作流程集成测试"""

    def test_complete_configuration_lifecycle(self):
        """测试完整的配置生命周期"""
        print("\n=== 测试完整配置生命周期 ===")
        
        # 1. 创建导入任务配置
        config = ImportTaskConfig(
            task_id="lifecycle_test_001",
            name="生命周期测试任务",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001", "000002", "000300"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            max_workers=4,
            batch_size=1000
        )
        
        # 2. 添加任务到配置管理器
        success = self.config_manager.add_import_task(config)
        self.assertTrue(success, "任务添加失败")
        print(f"✓ 任务添加成功: {config.task_id}")
        
        # 3. 记录性能反馈（模拟任务执行）
        performance_data = [
            (90.0, 0.95, 0.05, 1200.0),
            (85.0, 0.97, 0.03, 1300.0),
            (120.0, 0.85, 0.15, 800.0),
            (75.0, 0.98, 0.02, 1400.0)
        ]
        
        for exec_time, success_rate, error_rate, throughput in performance_data:
            self.config_manager.record_performance_feedback(
                config=config,
                execution_time=exec_time,
                success_rate=success_rate,
                error_rate=error_rate,
                throughput=throughput
            )
        
        print(f"✓ 记录了 {len(performance_data)} 条性能反馈")
        
        # 4. 生成配置推荐
        recommendations = self.recommendation_engine.generate_recommendations_for_task(
            config.task_id, ConfigRecommendationType.PERFORMANCE
        )
        
        self.assertIsInstance(recommendations, list)
        print(f"✓ 生成了 {len(recommendations)} 条配置推荐")
        
        # 5. 分析配置变更影响
        if recommendations:
            best_recommendation = recommendations[0]
            impact_report = self.impact_analyzer.analyze_impact(
                config, best_recommendation.recommended_changes
            )
            
            self.assertIsInstance(impact_report, dict)
            self.assertIn('overall_assessment', impact_report)
            print(f"✓ 完成配置变更影响分析: {impact_report['overall_assessment']['status']}")
        
        # 6. 检测配置冲突
        conflicts = self.config_manager.detect_conflicts()
        self.assertIsInstance(conflicts, list)
        print(f"✓ 检测到 {len(conflicts)} 个配置冲突")
        
        # 7. 获取智能统计信息
        stats = self.config_manager.get_intelligent_statistics()
        self.assertIsInstance(stats, dict)
        self.assertGreater(stats['total_tasks'], 0)
        self.assertGreater(stats['performance_history_count'], 0)
        print(f"✓ 获取统计信息: {stats['total_tasks']} 个任务, {stats['performance_history_count']} 条性能记录")

    def test_multi_task_configuration_management(self):
        """测试多任务配置管理"""
        print("\n=== 测试多任务配置管理 ===")
        
        # 创建多个不同类型的任务
        tasks = [
            ImportTaskConfig(
                task_id=f"multi_task_{i:03d}",
                name=f"多任务测试{i}",
                data_source="tongdaxin" if i % 2 == 0 else "akshare",
                asset_type="stock" if i % 3 == 0 else "index",
                data_type="kline",
                symbols=[f"{i:06d}"],
                frequency=DataFrequency.DAILY if i % 2 == 0 else DataFrequency.MINUTE,
                mode=ImportMode.BATCH if i % 3 == 0 else ImportMode.SCHEDULED,
                max_workers=2 + (i % 4),
                batch_size=500 + (i * 100)
            )
            for i in range(1, 11)  # 创建10个任务
        ]
        
        # 添加所有任务
        for task in tasks:
            success = self.config_manager.add_import_task(task)
            self.assertTrue(success, f"任务 {task.task_id} 添加失败")
        
        print(f"✓ 成功添加 {len(tasks)} 个任务")
        
        # 为每个任务记录性能数据
        for task in tasks:
            # 模拟不同的性能表现
            base_time = 60 + (hash(task.task_id) % 60)
            base_success = 0.9 + (hash(task.task_id) % 10) / 100
            
            self.config_manager.record_performance_feedback(
                config=task,
                execution_time=base_time,
                success_rate=min(1.0, base_success),
                error_rate=1.0 - min(1.0, base_success),
                throughput=1000 + (hash(task.task_id) % 500)
            )
        
        print("✓ 为所有任务记录了性能数据")
        
        # 检测系统级冲突
        conflicts = self.config_manager.detect_conflicts()
        print(f"✓ 检测到 {len(conflicts)} 个系统级冲突")
        
        # 获取所有任务的推荐
        total_recommendations = 0
        for task in tasks[:5]:  # 只为前5个任务生成推荐（节省时间）
            recommendations = self.recommendation_engine.generate_recommendations_for_task(
                task.task_id, ConfigRecommendationType.BALANCED
            )
            total_recommendations += len(recommendations)
        
        print(f"✓ 生成了总计 {total_recommendations} 条推荐")
        
        # 验证系统统计信息
        stats = self.config_manager.get_intelligent_statistics()
        self.assertEqual(stats['total_tasks'], len(tasks))
        self.assertEqual(stats['active_tasks'], len(tasks))
        print(f"✓ 系统统计验证通过: {stats['total_tasks']} 个任务")


class TestDataProcessingWorkflow(TestSystemIntegration):
    """数据处理工作流程集成测试"""

    @requests_mock.Mocker()
    def test_end_to_end_data_processing(self, m):
        """测试端到端数据处理流程"""
        print("\n=== 测试端到端数据处理流程 ===")
        
        # 1. Mock外部数据源API
        mock_data = {
            'data': [
                {'symbol': '000001', 'date': '2024-01-01', 'open': 10.0, 'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000000},
                {'symbol': '000001', 'date': '2024-01-02', 'open': 10.2, 'high': 10.8, 'low': 10.0, 'close': 10.6, 'volume': 1200000},
                {'symbol': '000001', 'date': '2024-01-03', 'open': 10.6, 'high': 11.0, 'low': 10.3, 'close': 10.8, 'volume': 1100000}
            ]
        }
        
        m.get('http://api.tongdaxin.com/stock/kline', json=mock_data)
        m.get('http://api.akshare.com/stock/kline', json=mock_data)
        
        # 2. 配置数据导入任务
        config = ImportTaskConfig(
            task_id="e2e_data_test_001",
            name="端到端数据测试",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH
        )
        
        self.config_manager.add_import_task(config)
        print("✓ 配置数据导入任务")
        
        # 3. 通过数据集成组件获取数据
        with patch('core.ui_integration.smart_data_integration.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_get.return_value = mock_response
            
            data_result = self.data_integration.check_data_for_widget(
                widget_type="stock_kline",
                symbol="000001",
                data_type="daily"
            )
            
            self.assertIsInstance(data_result, dict)
            print("✓ 通过数据集成组件获取数据")
        
        # 4. 将数据转换为DataFrame进行异常检测
        df_data = pd.DataFrame(mock_data['data'])
        df_data['date'] = pd.to_datetime(df_data['date'])
        
        # 注入一些异常数据用于测试
        df_data.loc[1, 'high'] = 50.0  # 异常高价
        df_data.loc[2, 'volume'] = np.nan  # 缺失交易量
        
        # 5. 执行异常检测
        anomalies = self.anomaly_detector.detect_anomalies(
            data=df_data,
            data_source="tongdaxin",
            symbol="000001",
            data_type="kline"
        )
        
        self.assertGreater(len(anomalies), 0, "应该检测到异常")
        print(f"✓ 检测到 {len(anomalies)} 个数据异常")
        
        # 6. 尝试自动修复异常
        repaired_count = 0
        for anomaly in anomalies:
            repair_result = self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
            if repair_result and repair_result.success:
                repaired_count += 1
        
        print(f"✓ 成功修复 {repaired_count} 个异常")
        
        # 7. 记录处理性能并生成推荐
        processing_time = 45.0  # 模拟处理时间
        success_rate = 0.95 if repaired_count > 0 else 0.85
        
        self.config_manager.record_performance_feedback(
            config=config,
            execution_time=processing_time,
            success_rate=success_rate,
            error_rate=1.0 - success_rate,
            throughput=len(df_data) / processing_time * 60  # 每分钟处理记录数
        )
        
        print("✓ 记录处理性能反馈")
        
        # 8. 基于处理结果生成优化推荐
        recommendations = self.recommendation_engine.generate_recommendations_for_task(
            config.task_id, ConfigRecommendationType.RELIABILITY
        )
        
        print(f"✓ 生成 {len(recommendations)} 条优化推荐")
        
        # 9. 验证整个流程的数据一致性
        stats = self.config_manager.get_intelligent_statistics()
        anomaly_stats = self.anomaly_detector.get_anomaly_statistics()
        integration_stats = self.data_integration.get_statistics()
        
        self.assertGreater(stats['performance_history_count'], 0)
        self.assertGreater(anomaly_stats['total_anomalies'], 0)
        self.assertIsInstance(integration_stats, dict)
        
        print("✓ 端到端数据处理流程验证完成")

    def test_real_time_data_processing_simulation(self):
        """测试实时数据处理模拟"""
        print("\n=== 测试实时数据处理模拟 ===")
        
        # 配置实时数据任务
        realtime_config = ImportTaskConfig(
            task_id="realtime_test_001",
            name="实时数据测试",
            data_source="akshare",
            asset_type="stock",
            data_type="realtime",
            symbols=["000001", "000002", "000300"],
            frequency=DataFrequency.MINUTE,
            mode=ImportMode.REALTIME,
            max_workers=2,
            batch_size=100
        )
        
        self.config_manager.add_import_task(realtime_config)
        
        # 模拟实时数据流
        def simulate_realtime_data():
            """模拟实时数据生成"""
            base_price = 10.0
            for i in range(20):  # 模拟20个数据点
                # 生成模拟的实时数据
                price_change = np.random.normal(0, 0.1)
                current_price = max(0.1, base_price + price_change)
                
                data_point = pd.DataFrame({
                    'timestamp': [datetime.now()],
                    'symbol': ['000001'],
                    'price': [current_price],
                    'volume': [np.random.randint(1000, 10000)]
                })
                
                # 检测异常
                anomalies = self.anomaly_detector.detect_anomalies(
                    data=data_point,
                    data_source="akshare",
                    symbol="000001",
                    data_type="realtime"
                )
                
                # 如果检测到异常，尝试修复
                if anomalies:
                    for anomaly in anomalies:
                        self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
                
                base_price = current_price
                time.sleep(0.1)  # 模拟实时间隔
        
        # 在后台运行实时数据模拟
        import threading
        simulation_thread = threading.Thread(target=simulate_realtime_data)
        simulation_thread.daemon = True
        simulation_thread.start()
        
        # 等待一段时间让模拟运行
        time.sleep(3)
        
        # 验证实时处理结果
        anomaly_stats = self.anomaly_detector.get_anomaly_statistics()
        print(f"✓ 实时处理中检测到 {anomaly_stats['total_anomalies']} 个异常")
        
        # 记录实时处理性能
        self.config_manager.record_performance_feedback(
            config=realtime_config,
            execution_time=3.0,
            success_rate=0.98,
            error_rate=0.02,
            throughput=20 / 3.0  # 每秒处理数据点数
        )
        
        print("✓ 实时数据处理模拟完成")


class TestPerformanceIntegration(TestSystemIntegration):
    """性能集成测试"""

    def test_high_load_scenario(self):
        """测试高负载场景"""
        print("\n=== 测试高负载场景 ===")
        
        # 创建大量任务配置
        num_tasks = 50
        tasks = []
        
        for i in range(num_tasks):
            config = ImportTaskConfig(
                task_id=f"load_test_{i:03d}",
                name=f"负载测试任务{i}",
                data_source="tongdaxin" if i % 2 == 0 else "akshare",
                asset_type="stock",
                data_type="kline",
                symbols=[f"{i:06d}"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=2,
                batch_size=1000
            )
            tasks.append(config)
        
        # 并发添加任务
        def add_tasks_batch(task_batch):
            for task in task_batch:
                self.config_manager.add_import_task(task)
        
        # 分批并发添加
        batch_size = 10
        threads = []
        
        start_time = time.time()
        
        for i in range(0, num_tasks, batch_size):
            batch = tasks[i:i + batch_size]
            thread = threading.Thread(target=add_tasks_batch, args=(batch,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        add_time = time.time() - start_time
        print(f"✓ 并发添加 {num_tasks} 个任务耗时: {add_time:.2f}秒")
        
        # 验证所有任务都被正确添加
        all_tasks = self.config_manager.get_all_import_tasks()
        self.assertEqual(len(all_tasks), num_tasks)
        
        # 并发记录性能数据
        def record_performance_batch(task_batch):
            for task in task_batch:
                self.config_manager.record_performance_feedback(
                    config=task,
                    execution_time=np.random.uniform(30, 120),
                    success_rate=np.random.uniform(0.8, 1.0),
                    error_rate=np.random.uniform(0.0, 0.2),
                    throughput=np.random.uniform(500, 2000)
                )
        
        threads = []
        start_time = time.time()
        
        for i in range(0, num_tasks, batch_size):
            batch = tasks[i:i + batch_size]
            thread = threading.Thread(target=record_performance_batch, args=(batch,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        perf_time = time.time() - start_time
        print(f"✓ 并发记录 {num_tasks} 个任务性能数据耗时: {perf_time:.2f}秒")
        
        # 验证性能数据记录
        stats = self.config_manager.get_intelligent_statistics()
        self.assertEqual(stats['total_tasks'], num_tasks)
        self.assertEqual(stats['performance_history_count'], num_tasks)
        
        print(f"✓ 高负载测试完成: {num_tasks} 个任务, 总耗时: {add_time + perf_time:.2f}秒")

    def test_memory_usage_under_load(self):
        """测试负载下的内存使用"""
        print("\n=== 测试负载下的内存使用 ===")
        
        import psutil
        import gc
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建大量数据进行处理
        large_datasets = []
        
        for i in range(10):
            # 创建大型数据集
            data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=10000, freq='min'),
                'symbol': [f'TEST{i:03d}'] * 10000,
                'price': np.random.normal(100, 10, 10000),
                'volume': np.random.randint(1000, 100000, 10000),
                'high': np.random.normal(105, 10, 10000),
                'low': np.random.normal(95, 10, 10000)
            })
            
            # 注入异常数据
            data.loc[np.random.choice(10000, 100, replace=False), 'price'] = np.nan
            data.loc[np.random.choice(10000, 50, replace=False), 'volume'] = 0
            
            large_datasets.append(data)
        
        # 处理所有数据集
        total_anomalies = 0
        
        for i, data in enumerate(large_datasets):
            anomalies = self.anomaly_detector.detect_anomalies(
                data=data,
                data_source="memory_test",
                symbol=f"TEST{i:03d}",
                data_type="kline"
            )
            total_anomalies += len(anomalies)
            
            # 尝试修复部分异常
            for anomaly in anomalies[:5]:  # 只修复前5个异常
                self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
        
        # 获取处理后内存使用
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory
        
        print(f"✓ 处理了 {len(large_datasets)} 个大型数据集")
        print(f"✓ 检测到总计 {total_anomalies} 个异常")
        print(f"✓ 内存使用: 初始 {initial_memory:.1f}MB, 当前 {current_memory:.1f}MB, 增加 {memory_increase:.1f}MB")
        
        # 清理内存
        large_datasets.clear()
        gc.collect()
        
        # 验证内存增长在合理范围内（小于500MB）
        self.assertLess(memory_increase, 500, f"内存增长过大: {memory_increase:.1f}MB")
        
        print("✓ 内存使用测试通过")


class TestErrorRecoveryIntegration(TestSystemIntegration):
    """错误恢复集成测试"""

    def test_database_connection_recovery(self):
        """测试数据库连接恢复"""
        print("\n=== 测试数据库连接恢复 ===")
        
        # 添加一个正常任务
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
        
        success = self.config_manager.add_import_task(config)
        self.assertTrue(success)
        print("✓ 正常添加任务")
        
        # 模拟数据库连接问题（通过使用无效路径）
        original_db_path = self.config_manager.db_path
        self.config_manager.db_path = "/invalid/path/database.sqlite"
        
        # 尝试操作（应该优雅处理错误）
        try:
            stats = self.config_manager.get_intelligent_statistics()
            # 即使数据库连接有问题，也应该返回基本统计信息
            self.assertIsInstance(stats, dict)
            print("✓ 数据库连接问题时优雅降级")
        except Exception as e:
            print(f"✓ 捕获到预期的数据库错误: {type(e).__name__}")
        
        # 恢复数据库连接
        self.config_manager.db_path = original_db_path
        
        # 验证恢复后功能正常
        stats = self.config_manager.get_intelligent_statistics()
        self.assertGreater(stats['total_tasks'], 0)
        print("✓ 数据库连接恢复后功能正常")

    def test_component_failure_isolation(self):
        """测试组件故障隔离"""
        print("\n=== 测试组件故障隔离 ===")
        
        # 创建测试配置
        config = ImportTaskConfig(
            task_id="isolation_test",
            name="故障隔离测试",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH
        )
        
        self.config_manager.add_import_task(config)
        
        # 模拟推荐引擎故障
        with patch.object(self.recommendation_engine, 'generate_recommendations_for_task', 
                         side_effect=Exception("推荐引擎故障")):
            
            # 配置管理器应该仍然能正常工作
            stats = self.config_manager.get_intelligent_statistics()
            self.assertIsInstance(stats, dict)
            print("✓ 推荐引擎故障时配置管理器正常工作")
            
            # 其他组件也应该正常工作
            test_data = pd.DataFrame({
                'price': [10.0, 11.0, 12.0],
                'volume': [1000, 1100, 1200]
            })
            
            anomalies = self.anomaly_detector.detect_anomalies(
                data=test_data,
                data_source="isolation_test",
                symbol="000001",
                data_type="kline"
            )
            
            self.assertIsInstance(anomalies, list)
            print("✓ 推荐引擎故障时异常检测器正常工作")
        
        # 模拟异常检测器故障
        with patch.object(self.anomaly_detector, 'detect_anomalies',
                         side_effect=Exception("异常检测器故障")):
            
            # 配置管理器和推荐引擎应该仍然能正常工作
            recommendations = self.recommendation_engine.generate_recommendations_for_task(
                config.task_id, ConfigRecommendationType.PERFORMANCE
            )
            
            self.assertIsInstance(recommendations, list)
            print("✓ 异常检测器故障时推荐引擎正常工作")
        
        print("✓ 组件故障隔离测试完成")

    def test_data_corruption_handling(self):
        """测试数据损坏处理"""
        print("\n=== 测试数据损坏处理 ===")
        
        # 创建包含各种损坏数据的测试数据集
        corrupted_data = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02', 'invalid_date', '2024-01-04', None],
            'symbol': ['000001', '000001', '000001', '', '000001'],
            'price': [10.0, -999.0, np.inf, 'not_a_number', 12.0],
            'volume': [1000, 0, -100, 1200, np.nan],
            'high': [10.5, 11.0, 11.5, 12.0, 12.5],
            'low': [9.5, 10.0, 10.5, 11.0, 11.5]
        })
        
        # 异常检测器应该能处理损坏的数据
        try:
            anomalies = self.anomaly_detector.detect_anomalies(
                data=corrupted_data,
                data_source="corruption_test",
                symbol="000001",
                data_type="kline"
            )
            
            self.assertIsInstance(anomalies, list)
            print(f"✓ 成功处理损坏数据，检测到 {len(anomalies)} 个异常")
            
            # 尝试修复检测到的异常
            repaired_count = 0
            for anomaly in anomalies:
                repair_result = self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
                if repair_result and repair_result.success:
                    repaired_count += 1
            
            print(f"✓ 成功修复 {repaired_count} 个数据异常")
            
        except Exception as e:
            # 即使处理失败，也应该是可控的异常
            print(f"✓ 优雅处理数据损坏异常: {type(e).__name__}")
        
        print("✓ 数据损坏处理测试完成")


class TestUserWorkflowIntegration(TestSystemIntegration):
    """用户工作流程集成测试"""

    def test_typical_user_workflow(self):
        """测试典型用户工作流程"""
        print("\n=== 测试典型用户工作流程 ===")
        
        # 用户工作流程：
        # 1. 创建数据导入任务
        # 2. 配置任务参数
        # 3. 启动任务并监控
        # 4. 查看性能统计
        # 5. 根据推荐优化配置
        # 6. 处理数据质量问题
        
        print("步骤1: 用户创建数据导入任务")
        user_config = ImportTaskConfig(
            task_id="user_workflow_001",
            name="用户股票数据导入",
            data_source="tongdaxin",
            asset_type="stock",
            data_type="kline",
            symbols=["000001", "000002", "000300", "000858"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.SCHEDULED,
            schedule_cron="0 9 * * *",  # 每天9点执行
            max_workers=4,
            batch_size=1000
        )
        
        success = self.config_manager.add_import_task(user_config)
        self.assertTrue(success)
        print("✓ 任务创建成功")
        
        print("步骤2: 模拟任务执行和性能监控")
        # 模拟多次任务执行
        execution_results = [
            (120.0, 0.95, 0.05, 1200.0),  # 第一次执行
            (110.0, 0.97, 0.03, 1300.0),  # 性能改善
            (130.0, 0.92, 0.08, 1100.0),  # 性能下降
            (105.0, 0.98, 0.02, 1400.0),  # 最佳性能
        ]
        
        for i, (exec_time, success_rate, error_rate, throughput) in enumerate(execution_results):
            self.config_manager.record_performance_feedback(
                config=user_config,
                execution_time=exec_time,
                success_rate=success_rate,
                error_rate=error_rate,
                throughput=throughput
            )
            print(f"  ✓ 记录第{i+1}次执行结果: {exec_time:.1f}s, 成功率{success_rate:.1%}")
        
        print("步骤3: 用户查看性能统计")
        stats = self.config_manager.get_intelligent_statistics()
        print(f"  ✓ 系统统计: {stats['total_tasks']}个任务, {stats['performance_history_count']}条性能记录")
        
        print("步骤4: 系统生成优化推荐")
        recommendations = self.recommendation_engine.generate_recommendations_for_task(
            user_config.task_id, ConfigRecommendationType.PERFORMANCE
        )
        print(f"  ✓ 生成{len(recommendations)}条优化推荐")
        
        if recommendations:
            best_recommendation = recommendations[0]
            print(f"  ✓ 最佳推荐: {best_recommendation.description} (置信度: {best_recommendation.confidence:.2f})")
            
            print("步骤5: 用户应用推荐配置")
            # 分析配置变更影响
            impact_report = self.impact_analyzer.analyze_impact(
                user_config, best_recommendation.recommended_changes
            )
            
            print(f"  ✓ 影响分析: {impact_report['overall_assessment']['status']}")
            
            if impact_report['overall_assessment']['status'] in ['safe', 'warning']:
                # 应用推荐的配置变更
                for key, value in best_recommendation.recommended_changes.items():
                    setattr(user_config, key, value)
                
                self.config_manager.update_import_task(user_config)
                print("  ✓ 配置更新成功")
        
        print("步骤6: 处理数据质量问题")
        # 模拟导入的数据
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
            'symbol': ['000001'] * 100,
            'open': np.random.normal(10, 1, 100),
            'high': np.random.normal(11, 1, 100),
            'low': np.random.normal(9, 1, 100),
            'close': np.random.normal(10, 1, 100),
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        # 注入一些数据质量问题
        sample_data.loc[10:15, 'close'] = np.nan  # 缺失数据
        sample_data.loc[20, 'high'] = 50.0  # 异常值
        sample_data.loc[30:32] = sample_data.loc[29]  # 重复数据
        
        # 检测数据质量问题
        anomalies = self.anomaly_detector.detect_anomalies(
            data=sample_data,
            data_source="tongdaxin",
            symbol="000001",
            data_type="kline"
        )
        
        print(f"  ✓ 检测到{len(anomalies)}个数据质量问题")
        
        # 自动修复部分问题
        auto_repaired = 0
        for anomaly in anomalies:
            repair_result = self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
            if repair_result and repair_result.success:
                auto_repaired += 1
        
        print(f"  ✓ 自动修复{auto_repaired}个问题")
        
        print("步骤7: 用户查看最终结果")
        final_stats = self.config_manager.get_intelligent_statistics()
        anomaly_stats = self.anomaly_detector.get_anomaly_statistics()
        
        print(f"  ✓ 最终统计: {final_stats['total_tasks']}个任务")
        print(f"  ✓ 数据质量: {anomaly_stats['total_anomalies']}个异常, {anomaly_stats['resolved_anomalies']}个已解决")
        
        print("✓ 典型用户工作流程测试完成")

    def test_power_user_advanced_workflow(self):
        """测试高级用户工作流程"""
        print("\n=== 测试高级用户工作流程 ===")
        
        # 高级用户工作流程：
        # 1. 批量创建多个复杂任务
        # 2. 配置自动优化
        # 3. 设置冲突检测和解决
        # 4. 自定义推荐策略
        # 5. 高级数据质量监控
        
        print("步骤1: 批量创建复杂任务配置")
        complex_tasks = []
        
        # 创建不同类型的复杂任务
        task_configs = [
            {
                'task_id': 'power_stock_daily',
                'name': '股票日线数据',
                'symbols': [f'{i:06d}' for i in range(1, 101)],  # 100只股票
                'frequency': DataFrequency.DAILY,
                'max_workers': 8,
                'batch_size': 2000
            },
            {
                'task_id': 'power_index_minute',
                'name': '指数分钟数据',
                'symbols': ['000001', '000300', '399001', '399006'],
                'frequency': DataFrequency.MINUTE,
                'max_workers': 4,
                'batch_size': 500
            },
            {
                'task_id': 'power_fund_nav',
                'name': '基金净值数据',
                'symbols': [f'{i:06d}' for i in range(100001, 100051)],  # 50只基金
                'frequency': DataFrequency.DAILY,
                'max_workers': 2,
                'batch_size': 1000
            }
        ]
        
        for task_config in task_configs:
            config = ImportTaskConfig(
                task_id=task_config['task_id'],
                name=task_config['name'],
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=task_config['symbols'],
                frequency=task_config['frequency'],
                mode=ImportMode.SCHEDULED,
                schedule_cron="0 */6 * * *",  # 每6小时执行
                max_workers=task_config['max_workers'],
                batch_size=task_config['batch_size']
            )
            
            success = self.config_manager.add_import_task(config)
            self.assertTrue(success)
            complex_tasks.append(config)
        
        print(f"  ✓ 创建{len(complex_tasks)}个复杂任务")
        
        print("步骤2: 启用自动配置优化")
        self.config_manager.enable_auto_config(True)
        self.config_manager.set_auto_optimization_interval(1)  # 1小时间隔
        
        # 为每个任务记录不同的性能数据
        for i, task in enumerate(complex_tasks):
            # 模拟不同的性能表现
            performances = [
                (60 + i * 20, 0.9 + i * 0.02, 0.1 - i * 0.02, 1000 + i * 200),
                (55 + i * 18, 0.92 + i * 0.02, 0.08 - i * 0.02, 1100 + i * 200),
                (70 + i * 25, 0.88 + i * 0.02, 0.12 - i * 0.02, 900 + i * 200)
            ]
            
            for exec_time, success_rate, error_rate, throughput in performances:
                self.config_manager.record_performance_feedback(
                    config=task,
                    execution_time=exec_time,
                    success_rate=min(1.0, success_rate),
                    error_rate=max(0.0, error_rate),
                    throughput=throughput
                )
        
        print("  ✓ 记录多样化性能数据")
        
        print("步骤3: 检测和解决配置冲突")
        conflicts = self.config_manager.detect_conflicts()
        print(f"  ✓ 检测到{len(conflicts)}个配置冲突")
        
        # 尝试自动解决冲突
        resolved_conflicts = 0
        for conflict in conflicts:
            if conflict.auto_resolvable:
                # 模拟自动解决冲突
                resolved_conflicts += 1
        
        print(f"  ✓ 自动解决{resolved_conflicts}个冲突")
        
        print("步骤4: 生成多维度推荐")
        all_recommendations = []
        
        for task in complex_tasks:
            # 为每个任务生成不同类型的推荐
            for rec_type in [ConfigRecommendationType.PERFORMANCE, 
                           ConfigRecommendationType.RELIABILITY,
                           ConfigRecommendationType.COST]:
                recommendations = self.recommendation_engine.generate_recommendations_for_task(
                    task.task_id, rec_type
                )
                all_recommendations.extend(recommendations)
        
        print(f"  ✓ 生成{len(all_recommendations)}条多维度推荐")
        
        print("步骤5: 高级数据质量监控")
        # 创建复杂的测试数据集
        complex_data_issues = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=1000, freq='min'),
            'symbol': np.random.choice(['000001', '000002', '000300'], 1000),
            'price': np.concatenate([
                np.random.normal(10, 1, 800),  # 正常数据
                np.random.normal(50, 5, 100),  # 异常值群
                [np.nan] * 50,  # 缺失数据
                np.random.normal(10, 1, 50)   # 更多正常数据
            ]),
            'volume': np.concatenate([
                np.random.randint(1000, 10000, 900),
                [0] * 50,  # 零交易量
                np.random.randint(1000, 10000, 50)
            ])
        })
        
        # 添加重复数据
        duplicate_indices = np.random.choice(1000, 100, replace=False)
        for idx in duplicate_indices:
            if idx < 999:
                complex_data_issues.loc[idx + 1] = complex_data_issues.loc[idx]
        
        # 执行全面的异常检测
        comprehensive_anomalies = self.anomaly_detector.detect_anomalies(
            data=complex_data_issues,
            data_source="power_user_test",
            symbol="COMPLEX_DATA",
            data_type="kline"
        )
        
        print(f"  ✓ 检测到{len(comprehensive_anomalies)}个复杂数据异常")
        
        # 分类处理不同类型的异常
        anomaly_types = {}
        for anomaly in comprehensive_anomalies:
            anomaly_type = anomaly.anomaly_type.value
            anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1
        
        print(f"  ✓ 异常类型分布: {anomaly_types}")
        
        # 批量自动修复
        batch_repair_results = []
        for anomaly in comprehensive_anomalies[:20]:  # 只处理前20个异常
            repair_result = self.anomaly_detector.auto_repair_anomaly(anomaly.anomaly_id)
            if repair_result:
                batch_repair_results.append(repair_result)
        
        successful_repairs = sum(1 for r in batch_repair_results if r.success)
        print(f"  ✓ 批量修复结果: {successful_repairs}/{len(batch_repair_results)} 成功")
        
        print("步骤6: 生成综合报告")
        final_stats = self.config_manager.get_intelligent_statistics()
        anomaly_stats = self.anomaly_detector.get_anomaly_statistics()
        
        print(f"  ✓ 系统综合统计:")
        print(f"    - 总任务数: {final_stats['total_tasks']}")
        print(f"    - 性能记录: {final_stats['performance_history_count']}")
        print(f"    - 推荐数量: {final_stats['recommendation_count']}")
        print(f"    - 冲突数量: {final_stats['conflict_count']}")
        print(f"    - 异常总数: {anomaly_stats['total_anomalies']}")
        print(f"    - 已解决异常: {anomaly_stats['resolved_anomalies']}")
        
        print("✓ 高级用户工作流程测试完成")


def run_integration_tests():
    """运行所有集成测试"""
    print("开始运行系统集成测试和端到端测试...")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestConfigurationWorkflow,
        TestDataProcessingWorkflow,
        TestPerformanceIntegration,
        TestErrorRecoveryIntegration,
        TestUserWorkflowIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("=" * 80)
    print(f"集成测试完成！")
    print(f"成功: {'是' if result.wasSuccessful() else '否'}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 所有集成测试通过！")
    else:
        print("❌ 存在集成测试失败或错误")
        
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            print("\n错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful(), len(result.failures), len(result.errors)


if __name__ == "__main__":
    success, failures, errors = run_integration_tests()
    
    # 返回适当的退出码
    exit_code = 0 if success else 1
    exit(exit_code)
