#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能基准测试

使用pytest-benchmark进行性能测试和回归检测。
"""

import pytest
import tempfile
import os
import pandas as pd
import numpy as np
from datetime import datetime
import time

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


class TestConfigManagerPerformance:
    """配置管理器性能测试"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库fixture"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        yield temp_db.name
        try:
            os.unlink(temp_db.name)
        except:
            pass

    @pytest.fixture
    def config_manager(self, temp_db):
        """配置管理器fixture"""
        return IntelligentConfigManager(temp_db)

    @pytest.fixture
    def sample_configs(self):
        """示例配置数据"""
        configs = []
        for i in range(100):
            config = ImportTaskConfig(
                task_id=f"perf_test_{i:03d}",
                name=f"性能测试任务{i}",
                data_source="tongdaxin" if i % 2 == 0 else "akshare",
                asset_type="stock",
                data_type="kline",
                symbols=[f"{j:06d}" for j in range(i, i + 10)],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=2 + (i % 4),
                batch_size=500 + (i * 10)
            )
            configs.append(config)
        return configs

    def test_add_tasks_performance(self, benchmark, config_manager, sample_configs):
        """测试批量添加任务的性能"""
        def add_all_tasks():
            for config in sample_configs:
                config_manager.add_import_task(config)
        
        result = benchmark(add_all_tasks)
        
        # 验证所有任务都被添加
        all_tasks = config_manager.get_all_import_tasks()
        assert len(all_tasks) == len(sample_configs)

    def test_get_tasks_performance(self, benchmark, config_manager, sample_configs):
        """测试批量获取任务的性能"""
        # 先添加任务
        for config in sample_configs:
            config_manager.add_import_task(config)
        
        def get_all_tasks():
            return config_manager.get_all_import_tasks()
        
        result = benchmark(get_all_tasks)
        assert len(result) == len(sample_configs)

    def test_performance_feedback_recording(self, benchmark, config_manager, sample_configs):
        """测试性能反馈记录的性能"""
        # 先添加一个任务
        config = sample_configs[0]
        config_manager.add_import_task(config)
        
        def record_performance():
            config_manager.record_performance_feedback(
                config=config,
                execution_time=np.random.uniform(30, 120),
                success_rate=np.random.uniform(0.8, 1.0),
                error_rate=np.random.uniform(0.0, 0.2),
                throughput=np.random.uniform(500, 2000)
            )
        
        result = benchmark.pedantic(record_performance, iterations=100, rounds=5)

    def test_conflict_detection_performance(self, benchmark, config_manager, sample_configs):
        """测试冲突检测的性能"""
        # 添加可能冲突的任务
        for config in sample_configs[:50]:  # 只添加50个任务以控制测试时间
            config_manager.add_import_task(config)
        
        def detect_conflicts():
            return config_manager.detect_conflicts()
        
        result = benchmark(detect_conflicts)
        assert isinstance(result, list)

    def test_statistics_generation_performance(self, benchmark, config_manager, sample_configs):
        """测试统计信息生成的性能"""
        # 添加任务和性能数据
        for config in sample_configs[:20]:
            config_manager.add_import_task(config)
            config_manager.record_performance_feedback(
                config=config,
                execution_time=np.random.uniform(30, 120),
                success_rate=np.random.uniform(0.8, 1.0),
                error_rate=np.random.uniform(0.0, 0.2),
                throughput=np.random.uniform(500, 2000)
            )
        
        def get_statistics():
            return config_manager.get_intelligent_statistics()
        
        result = benchmark(get_statistics)
        assert isinstance(result, dict)
        assert result['total_tasks'] > 0


class TestAnomalyDetectorPerformance:
    """异常检测器性能测试"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库fixture"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        yield temp_db.name
        try:
            os.unlink(temp_db.name)
        except:
            pass

    @pytest.fixture
    def anomaly_detector(self, temp_db):
        """异常检测器fixture"""
        config = AnomalyDetectionConfig(
            auto_repair_enabled=True,
            enable_outlier_detection=True,
            enable_missing_data_detection=True,
            enable_duplicate_detection=True
        )
        return DataAnomalyDetector(config, temp_db)

    @pytest.fixture
    def large_dataset(self):
        """大型数据集fixture"""
        np.random.seed(42)
        
        # 创建包含10000行数据的大型数据集
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='min'),
            'symbol': np.random.choice(['000001', '000002', '000300'], 10000),
            'price': np.concatenate([
                np.random.normal(100, 10, 9000),  # 正常数据
                np.random.normal(200, 20, 500),   # 异常值群1
                np.random.normal(50, 5, 300),     # 异常值群2
                [np.nan] * 200                    # 缺失数据
            ]),
            'volume': np.concatenate([
                np.random.randint(1000, 100000, 9500),
                [0] * 300,  # 零交易量
                np.random.randint(1000, 100000, 200)
            ]),
            'high': np.random.normal(105, 10, 10000),
            'low': np.random.normal(95, 10, 10000)
        })
        
        # 添加重复数据
        duplicate_indices = np.random.choice(10000, 500, replace=False)
        for i, idx in enumerate(duplicate_indices):
            if idx < 9999:
                data.loc[idx + 1] = data.loc[idx]
        
        return data

    def test_large_dataset_anomaly_detection(self, benchmark, anomaly_detector, large_dataset):
        """测试大型数据集异常检测性能"""
        def detect_anomalies():
            return anomaly_detector.detect_anomalies(
                data=large_dataset,
                data_source="performance_test",
                symbol="LARGE_DATASET",
                data_type="kline"
            )
        
        result = benchmark(detect_anomalies)
        assert isinstance(result, list)
        assert len(result) > 0  # 应该检测到异常

    def test_missing_data_detection_performance(self, benchmark, anomaly_detector):
        """测试缺失数据检测性能"""
        # 创建包含大量缺失数据的数据集
        data = pd.DataFrame({
            'price': [10.0] * 5000 + [np.nan] * 2000 + [11.0] * 3000,
            'volume': [1000] * 8000 + [np.nan] * 2000,
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='min')
        })
        
        def detect_missing_anomalies():
            return anomaly_detector._detect_missing_data(
                data, "perf_test", "MISSING_TEST", "kline"
            )
        
        result = benchmark(detect_missing_anomalies)
        assert isinstance(result, list)

    def test_outlier_detection_performance(self, benchmark, anomaly_detector):
        """测试异常值检测性能"""
        # 创建包含明显异常值的数据集
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 9000)
        outliers = np.random.normal(500, 50, 1000)
        
        data = pd.DataFrame({
            'price': np.concatenate([normal_data, outliers]),
            'volume': np.random.randint(1000, 10000, 10000),
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='min')
        })
        
        def detect_outlier_anomalies():
            return anomaly_detector._detect_outliers(
                data, "perf_test", "OUTLIER_TEST", "kline"
            )
        
        result = benchmark(detect_outlier_anomalies)
        assert isinstance(result, list)

    def test_auto_repair_performance(self, benchmark, anomaly_detector, large_dataset):
        """测试自动修复性能"""
        # 先检测异常
        anomalies = anomaly_detector.detect_anomalies(
            data=large_dataset,
            data_source="repair_test",
            symbol="REPAIR_TEST",
            data_type="kline"
        )
        
        if not anomalies:
            pytest.skip("没有检测到异常，跳过修复性能测试")
        
        # 选择第一个异常进行修复性能测试
        anomaly_id = anomalies[0].anomaly_id
        
        def auto_repair():
            return anomaly_detector.auto_repair_anomaly(anomaly_id)
        
        result = benchmark(auto_repair)
        # 注意：第二次调用可能返回None（已经修复过）


class TestDataIntegrationPerformance:
    """数据集成性能测试"""

    @pytest.fixture
    def data_integration(self):
        """数据集成组件fixture"""
        config = UIIntegrationConfig(
            enable_caching=True,
            cache_expiry_seconds=300,
            enable_predictive_loading=True,
            enable_adaptive_caching=True
        )
        
        from unittest.mock import patch
        with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
            integration = SmartDataIntegration(config)
        
        yield integration
        
        try:
            integration.close()
        except:
            pass

    def test_cache_operations_performance(self, benchmark, data_integration):
        """测试缓存操作性能"""
        # 准备测试数据
        test_data = {
            'symbol': '000001',
            'data': [{'price': 10.0 + i * 0.1, 'volume': 1000 + i * 10} for i in range(1000)]
        }
        
        def cache_operations():
            # 缓存存储
            for i in range(100):
                cache_key = f"test_key_{i}"
                data_integration._put_to_intelligent_cache(
                    cache_key, test_data, "high", 300
                )
            
            # 缓存检索
            retrieved_count = 0
            for i in range(100):
                cache_key = f"test_key_{i}"
                cached_data = data_integration._get_from_intelligent_cache(cache_key)
                if cached_data:
                    retrieved_count += 1
            
            return retrieved_count
        
        result = benchmark(cache_operations)
        assert result > 0

    def test_data_source_selection_performance(self, benchmark, data_integration):
        """测试数据源选择性能"""
        def select_data_sources():
            results = []
            for i in range(1000):
                symbol = f"{i:06d}"
                source = data_integration._select_optimal_data_source(
                    "stock", "realtime", symbol
                )
                results.append(source)
            return results
        
        result = benchmark(select_data_sources)
        assert len(result) == 1000
        assert all(isinstance(source, str) for source in result)

    def test_predictive_loading_performance(self, benchmark, data_integration):
        """测试预测性加载性能"""
        # 先记录一些使用模式
        for i in range(100):
            data_integration._record_usage_pattern(
                "stock_quote", f"{i:06d}", "realtime"
            )
        
        def predictive_operations():
            # 预测可能的标的
            likely_symbols = data_integration._predict_likely_symbols(
                "stock_quote", "realtime"
            )
            
            # 执行预测性加载
            data_integration._perform_predictive_loading()
            
            return len(likely_symbols)
        
        result = benchmark(predictive_operations)
        assert isinstance(result, int)

    def test_performance_optimization(self, benchmark, data_integration):
        """测试性能优化操作"""
        # 添加一些缓存数据和性能指标
        for i in range(50):
            cache_key = f"opt_test_{i}"
            test_data = {'data': f'test_data_{i}'}
            data_integration._put_to_intelligent_cache(
                cache_key, test_data, "medium", 300
            )
        
        def optimize_performance():
            data_integration.optimize_performance()
        
        benchmark(optimize_performance)

    def test_statistics_generation_performance(self, benchmark, data_integration):
        """测试统计信息生成性能"""
        # 添加一些测试数据
        for i in range(100):
            cache_key = f"stats_test_{i}"
            test_data = {'timestamp': datetime.now().isoformat()}
            data_integration._put_to_intelligent_cache(
                cache_key, test_data, "high", 300
            )
            
            # 记录一些性能指标
            data_integration._record_cache_hit(cache_key)
            if i % 10 == 0:
                data_integration._record_cache_miss(cache_key)
        
        def get_statistics():
            return data_integration.get_statistics()
        
        result = benchmark(get_statistics)
        assert isinstance(result, dict)
        assert 'cache_stats' in result


class TestMemoryUsagePerformance:
    """内存使用性能测试"""

    def test_memory_usage_under_load(self, benchmark):
        """测试高负载下的内存使用"""
        import psutil
        import gc
        
        def memory_intensive_operations():
            # 获取初始内存
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            
            # 创建临时数据库
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
            temp_db.close()
            
            try:
                # 创建配置管理器
                manager = IntelligentConfigManager(temp_db.name)
                
                # 创建大量任务
                for i in range(200):
                    config = ImportTaskConfig(
                        task_id=f"memory_test_{i}",
                        name=f"内存测试任务{i}",
                        data_source="tongdaxin",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{j:06d}" for j in range(10)],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH
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
                
                # 获取最终内存
                final_memory = process.memory_info().rss
                memory_increase = final_memory - initial_memory
                
                # 清理
                gc.collect()
                
                return memory_increase / 1024 / 1024  # 返回MB
                
            finally:
                try:
                    os.unlink(temp_db.name)
                except:
                    pass
        
        memory_increase_mb = benchmark(memory_intensive_operations)
        
        # 验证内存增长在合理范围内（小于200MB）
        assert memory_increase_mb < 200, f"内存增长过大: {memory_increase_mb:.1f}MB"


# 性能回归测试配置
@pytest.mark.performance
class TestPerformanceRegression:
    """性能回归测试"""

    def test_config_manager_regression(self, benchmark):
        """配置管理器性能回归测试"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        
        try:
            manager = IntelligentConfigManager(temp_db.name)
            
            # 基准操作：添加100个任务
            def baseline_operations():
                for i in range(100):
                    config = ImportTaskConfig(
                        task_id=f"regression_test_{i}",
                        name=f"回归测试任务{i}",
                        data_source="tongdaxin",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{i:06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH
                    )
                    manager.add_import_task(config)
                
                # 获取统计信息
                stats = manager.get_intelligent_statistics()
                return stats['total_tasks']
            
            result = benchmark(baseline_operations)
            assert result == 100
            
        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    def test_anomaly_detector_regression(self, benchmark):
        """异常检测器性能回归测试"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()
        
        try:
            config = AnomalyDetectionConfig()
            detector = DataAnomalyDetector(config, temp_db.name)
            
            # 创建标准测试数据集
            np.random.seed(42)
            test_data = pd.DataFrame({
                'price': np.concatenate([
                    np.random.normal(100, 10, 900),
                    [np.nan] * 50,
                    np.random.normal(200, 20, 50)
                ]),
                'volume': np.random.randint(1000, 10000, 1000),
                'timestamp': pd.date_range('2024-01-01', periods=1000, freq='min')
            })
            
            def baseline_detection():
                anomalies = detector.detect_anomalies(
                    data=test_data,
                    data_source="regression_test",
                    symbol="BASELINE",
                    data_type="kline"
                )
                return len(anomalies)
            
            result = benchmark(baseline_detection)
            assert result > 0  # 应该检测到异常
            
        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([
        __file__,
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-columns=min,max,mean,stddev,median,iqr,outliers,rounds,iterations",
        "-v"
    ])
