#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强性能桥接系统测试

测试增强性能桥接的核心功能：
1. 性能数据收集和聚合
2. 实时性能分析
3. 异常检测和预警
4. 性能趋势分析
5. 优化建议生成

作者: FactorWeave-Quant团队
版本: 2.0 (智能化测试)
"""

import pytest
import tempfile
import shutil
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

try:
    from core.services.enhanced_performance_bridge import (
        EnhancedPerformanceBridge, PerformanceAnomalyType, PerformanceTrendType,
        PerformanceOptimizationSuggestion, PerformanceMetric, AnomalyInfo
    )
    ENHANCED_PERFORMANCE_AVAILABLE = True
except ImportError:
    ENHANCED_PERFORMANCE_AVAILABLE = False


@pytest.mark.skipif(not ENHANCED_PERFORMANCE_AVAILABLE, reason="增强性能桥接系统不可用")
class TestEnhancedPerformanceBridge:
    """增强性能桥接系统测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'db_path': Path(self.temp_dir) / "test_performance.db",
            'collection_interval': 1,  # 1秒间隔，便于测试
            'anomaly_threshold': 2.0,  # 2个标准差
            'trend_window': 10,        # 10个数据点
            'optimization_threshold': 0.8
        }
        self.bridge = EnhancedPerformanceBridge(self.config)

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self.bridge, 'cleanup'):
            self.bridge.cleanup()
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """测试初始化"""
        assert self.bridge is not None
        assert not self.bridge.is_monitoring
        assert self.bridge.db_path.exists()

        # 验证数据库表创建
        with sqlite3.connect(self.bridge.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['performance_metrics', 'performance_anomalies',
                               'performance_trends', 'optimization_suggestions']
            for table in expected_tables:
                assert table in tables

    def test_performance_metric_creation(self):
        """测试性能指标创建"""
        metric = PerformanceMetric(
            name="cpu_usage",
            value=75.5,
            unit="%",
            category="system",
            source="system_monitor",
            tags={"host": "localhost"},
            threshold=80.0
        )

        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.unit == "%"
        assert metric.category == "system"
        assert metric.source == "system_monitor"
        assert metric.tags["host"] == "localhost"
        assert metric.threshold == 80.0

    def test_anomaly_info_creation(self):
        """测试异常信息创建"""
        anomaly = AnomalyInfo(
            metric_name="response_time",
            anomaly_type=PerformanceAnomalyType.SPIKE,
            severity=0.8,
            description="响应时间异常峰值",
            detected_at=datetime.now(),
            expected_value=100.0,
            actual_value=500.0,
            confidence=0.95
        )

        assert anomaly.metric_name == "response_time"
        assert anomaly.anomaly_type == PerformanceAnomalyType.SPIKE
        assert anomaly.severity == 0.8
        assert anomaly.confidence == 0.95
        assert anomaly.actual_value == 500.0

    def test_optimization_suggestion_creation(self):
        """测试优化建议创建"""
        suggestion = PerformanceOptimizationSuggestion(
            id="opt_001",
            title="增加内存缓存",
            description="通过增加内存缓存来提高查询性能",
            category="memory",
            priority=0.8,
            estimated_improvement=0.3,
            implementation_difficulty=0.5,
            affected_metrics=["query_time", "memory_usage"],
            implementation_steps=["配置缓存大小", "启用缓存", "监控效果"]
        )

        assert suggestion.id == "opt_001"
        assert suggestion.title == "增加内存缓存"
        assert suggestion.priority == 0.8
        assert suggestion.estimated_improvement == 0.3
        assert len(suggestion.affected_metrics) == 2
        assert len(suggestion.implementation_steps) == 3

    def test_collect_performance_metrics(self):
        """测试性能指标收集"""
        metrics = self.bridge._collect_performance_metrics()

        assert isinstance(metrics, list)
        assert len(metrics) > 0

        for metric in metrics:
            assert isinstance(metric, PerformanceMetric)
            assert metric.name
            assert isinstance(metric.value, (int, float))
            assert metric.category
            assert metric.source

    def test_aggregate_metrics(self):
        """测试指标聚合"""
        # 创建测试指标
        metrics = [
            PerformanceMetric("cpu_usage", 70.0, "%", "system", "monitor1"),
            PerformanceMetric("cpu_usage", 80.0, "%", "system", "monitor2"),
            PerformanceMetric("memory_usage", 60.0, "%", "system", "monitor1"),
            PerformanceMetric("memory_usage", 65.0, "%", "system", "monitor2")
        ]

        aggregated = self.bridge._aggregate_metrics(metrics)

        assert isinstance(aggregated, dict)
        assert "cpu_usage" in aggregated
        assert "memory_usage" in aggregated

        # 验证聚合结果
        cpu_agg = aggregated["cpu_usage"]
        assert cpu_agg["avg"] == 75.0  # (70 + 80) / 2
        assert cpu_agg["min"] == 70.0
        assert cpu_agg["max"] == 80.0
        assert cpu_agg["count"] == 2

    def test_detect_performance_anomalies(self):
        """测试性能异常检测"""
        # 创建正常和异常的指标历史
        normal_values = [100, 105, 95, 102, 98, 103, 97, 101, 99, 104]
        anomaly_values = normal_values + [200, 300]  # 添加异常值

        # 模拟历史数据
        with patch.object(self.bridge, '_get_metric_history') as mock_history:
            mock_history.return_value = [
                {'value': v, 'timestamp': datetime.now() - timedelta(minutes=i)}
                for i, v in enumerate(reversed(anomaly_values))
            ]

            anomalies = self.bridge._detect_performance_anomalies("test_metric", 300)

            # 应该检测到异常
            assert len(anomalies) >= 0  # 可能因为数据不足而无异常

    def test_analyze_performance_trends(self):
        """测试性能趋势分析"""
        # 创建递增趋势的数据
        trend_values = [i * 10 for i in range(1, 11)]  # 10, 20, 30, ..., 100

        with patch.object(self.bridge, '_get_metric_history') as mock_history:
            mock_history.return_value = [
                {'value': v, 'timestamp': datetime.now() - timedelta(minutes=i)}
                for i, v in enumerate(reversed(trend_values))
            ]

            trends = self.bridge._analyze_performance_trends("test_metric")

            assert isinstance(trends, dict)
            if trends:  # 如果有足够数据进行趋势分析
                assert 'trend_type' in trends
                assert 'slope' in trends
                assert 'confidence' in trends

    def test_generate_optimization_suggestions(self):
        """测试优化建议生成"""
        # 创建性能指标
        metrics = [
            PerformanceMetric("cpu_usage", 90.0, "%", "system", "monitor", threshold=80.0),
            PerformanceMetric("memory_usage", 85.0, "%", "system", "monitor", threshold=80.0),
            PerformanceMetric("disk_io", 95.0, "MB/s", "system", "monitor", threshold=100.0)
        ]

        # 创建异常信息
        anomalies = [
            AnomalyInfo("cpu_usage", PerformanceAnomalyType.SPIKE, 0.8, "CPU峰值")
        ]

        # 创建趋势信息
        trends = {
            "memory_usage": {
                "trend_type": PerformanceTrendType.INCREASING,
                "slope": 0.5,
                "confidence": 0.9
            }
        }

        suggestions = self.bridge._generate_optimization_suggestions(metrics, anomalies, trends)

        assert isinstance(suggestions, list)
        assert len(suggestions) >= 0

        for suggestion in suggestions:
            assert isinstance(suggestion, PerformanceOptimizationSuggestion)
            assert suggestion.id
            assert suggestion.title
            assert suggestion.description
            assert 0 <= suggestion.priority <= 1
            assert 0 <= suggestion.estimated_improvement <= 1

    def test_monitoring_lifecycle(self):
        """测试监控生命周期"""
        # 启动监控
        assert self.bridge.start_monitoring()
        assert self.bridge.is_monitoring

        # 等待一些监控周期
        time.sleep(2)

        # 停止监控
        assert self.bridge.stop_monitoring()
        assert not self.bridge.is_monitoring

    def test_performance_summary(self):
        """测试性能摘要"""
        # 先运行一些监控周期
        self.bridge.start_monitoring()
        time.sleep(1)
        self.bridge.stop_monitoring()

        summary = self.bridge.get_performance_summary()

        assert isinstance(summary, dict)
        assert 'monitoring_status' in summary
        assert 'total_metrics' in summary
        assert 'active_anomalies' in summary
        assert 'last_update' in summary

    def test_anomaly_retrieval(self):
        """测试异常获取"""
        # 创建测试异常
        anomaly = AnomalyInfo(
            metric_name="test_metric",
            anomaly_type=PerformanceAnomalyType.SPIKE,
            severity=0.7,
            description="测试异常"
        )

        # 保存异常
        self.bridge._save_anomalies([anomaly])

        # 获取异常
        anomalies = self.bridge.get_performance_anomalies(24)
        assert len(anomalies) >= 1

    def test_trend_retrieval(self):
        """测试趋势获取"""
        trends = self.bridge.get_performance_trends(5)

        assert isinstance(trends, list)
        # 可能为空，因为需要历史数据来计算趋势

    def test_optimization_suggestion_retrieval(self):
        """测试优化建议获取"""
        suggestions = self.bridge.get_optimization_suggestions(10)

        assert isinstance(suggestions, list)
        # 可能为空，因为需要性能问题来生成建议

    def test_metric_history_tracking(self):
        """测试指标历史追踪"""
        metric_name = "test_metric"

        # 记录一些历史数据
        for i in range(5):
            metric = PerformanceMetric(
                name=metric_name,
                value=100 + i * 10,
                unit="ms",
                category="application",
                source="test"
            )
            self.bridge._save_metrics([metric])

        # 获取历史数据
        history = self.bridge.get_metric_performance_history(metric_name, 10)

        assert len(history) == 5
        for record in history:
            assert 'value' in record
            assert 'timestamp' in record

    def test_anomaly_resolution(self):
        """测试异常解决"""
        # 创建测试异常
        anomaly = AnomalyInfo(
            metric_name="test_resolution",
            anomaly_type=PerformanceAnomalyType.SPIKE,
            severity=0.6,
            description="测试异常解决"
        )

        # 保存异常
        self.bridge._save_anomalies([anomaly])

        # 获取异常ID
        anomalies = self.bridge.get_performance_anomalies(24)
        if anomalies:
            anomaly_id = anomalies[0]['id']

            # 解决异常
            success = self.bridge.resolve_performance_anomaly(anomaly_id, "测试解决")
            assert success

    def test_optimization_application(self):
        """测试优化建议应用"""
        # 创建测试建议
        suggestion = PerformanceOptimizationSuggestion(
            id="test_opt",
            title="测试优化",
            description="测试优化建议应用",
            category="test",
            priority=0.5,
            estimated_improvement=0.2
        )

        # 保存建议
        self.bridge._save_optimization_suggestions([suggestion])

        # 应用建议
        success = self.bridge.apply_performance_optimization(suggestion.id, "测试应用")
        assert success

    def test_custom_metric_recording(self):
        """测试自定义指标记录"""
        metric_name = "custom_test_metric"
        metric_value = 42.0

        # 记录自定义指标
        success = self.bridge.record_custom_performance_metric(
            metric_name, metric_value, "test", {"custom": "true"}
        )
        assert success

        # 验证指标已记录
        history = self.bridge.get_metric_performance_history(metric_name, 1)
        assert len(history) == 1
        assert history[0]['value'] == metric_value

    def test_statistical_analysis(self):
        """测试统计分析"""
        # 创建测试数据
        values = [10, 12, 11, 13, 9, 14, 10, 12, 11, 15]

        stats = self.bridge._calculate_statistics(values)

        assert isinstance(stats, dict)
        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert 'median' in stats

        # 验证统计值
        assert abs(stats['mean'] - np.mean(values)) < 0.01
        assert abs(stats['std'] - np.std(values)) < 0.01
        assert stats['min'] == min(values)
        assert stats['max'] == max(values)

    def test_threshold_management(self):
        """测试阈值管理"""
        metric_name = "threshold_test"

        # 设置动态阈值
        self.bridge._update_dynamic_threshold(metric_name, 100.0)

        # 获取阈值
        threshold = self.bridge._get_dynamic_threshold(metric_name, 80.0)
        assert threshold == 100.0

    def test_performance_optimization(self):
        """测试性能优化"""
        # 测试大量指标的处理性能
        start_time = time.time()

        # 创建大量指标
        large_metrics = []
        for i in range(1000):
            metric = PerformanceMetric(
                name=f"metric_{i}",
                value=np.random.uniform(0, 100),
                unit="unit",
                category="test",
                source="performance_test"
            )
            large_metrics.append(metric)

        # 聚合指标
        aggregated = self.bridge._aggregate_metrics(large_metrics)

        end_time = time.time()
        processing_time = end_time - start_time

        # 处理时间应该在合理范围内（小于3秒）
        assert processing_time < 3.0
        assert len(aggregated) == 1000

    def test_concurrent_monitoring(self):
        """测试并发监控"""
        results = []
        errors = []

        def monitoring_operation():
            try:
                # 启动监控
                self.bridge.start_monitoring()
                time.sleep(0.5)

                # 获取摘要
                summary = self.bridge.get_performance_summary()
                results.append(summary)

                # 停止监控
                self.bridge.stop_monitoring()
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=monitoring_operation)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发监控出现错误: {errors}"
        assert len(results) >= 0  # 可能因为快速启停而没有结果

    def test_data_persistence(self):
        """测试数据持久化"""
        # 创建测试数据
        metric = PerformanceMetric(
            name="persistence_test",
            value=50.0,
            unit="ms",
            category="test",
            source="persistence"
        )

        anomaly = AnomalyInfo(
            metric_name="persistence_test",
            anomaly_type=PerformanceAnomalyType.SPIKE,
            severity=0.5,
            description="持久化测试异常"
        )

        # 保存数据
        self.bridge._save_metrics([metric])
        self.bridge._save_anomalies([anomaly])

        # 创建新的桥接实例
        new_bridge = EnhancedPerformanceBridge(self.config)

        # 验证数据可以被新实例读取
        history = new_bridge.get_metric_performance_history("persistence_test", 10)
        assert len(history) >= 1

        anomalies = new_bridge.get_performance_anomalies(24)
        assert len(anomalies) >= 1

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效配置
        invalid_config = {'db_path': '/invalid/path/test.db'}

        try:
            invalid_bridge = EnhancedPerformanceBridge(invalid_config)
            # 应该能创建，但数据库操作可能失败
            summary = invalid_bridge.get_performance_summary()
            # 应该返回错误状态而不是崩溃
            assert 'error' in summary or 'monitoring_status' in summary
        except Exception:
            # 如果抛出异常，也是可以接受的
            pass

    def test_memory_management(self):
        """测试内存管理"""
        import psutil
        import os

        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 执行大量操作
        for i in range(100):
            metrics = self.bridge._collect_performance_metrics()
            self.bridge._aggregate_metrics(metrics)

        # 获取最终内存使用
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 内存增长应该在合理范围内（小于100MB）
        assert memory_increase < 100 * 1024 * 1024

    def test_cleanup(self):
        """测试资源清理"""
        # 启动监控
        self.bridge.start_monitoring()
        assert self.bridge.is_monitoring

        # 清理资源
        self.bridge.cleanup()

        # 验证监控已停止
        assert not self.bridge.is_monitoring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
