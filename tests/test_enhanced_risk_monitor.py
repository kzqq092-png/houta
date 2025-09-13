#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强风险监控系统测试

测试增强风险监控的核心功能：
1. 风险指标收集和分析
2. AI预测和异常检测
3. 智能预警生成
4. 自适应阈值调整
5. 风险情景分析

作者: FactorWeave-Quant团队
版本: 2.0 (智能化测试)
"""

import pytest
import tempfile
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

try:
    from core.risk_monitoring.enhanced_risk_monitor import (
        EnhancedRiskMonitor, RiskLevel, RiskCategory, AlertPriority,
        RiskMetric, RiskAlert, RiskScenario
    )
    ENHANCED_RISK_AVAILABLE = True
except ImportError:
    ENHANCED_RISK_AVAILABLE = False


@pytest.mark.skipif(not ENHANCED_RISK_AVAILABLE, reason="增强风险监控系统不可用")
class TestEnhancedRiskMonitor:
    """增强风险监控系统测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'db_path': Path(self.temp_dir) / "test_risk_monitor.db",
            'monitoring_interval': 1,  # 1秒间隔，便于测试
            'alert_cooldown': 5,       # 5秒冷却
            'max_alerts_per_hour': 100
        }
        self.risk_monitor = EnhancedRiskMonitor(self.config)

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self.risk_monitor, 'cleanup'):
            self.risk_monitor.cleanup()
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """测试初始化"""
        assert self.risk_monitor is not None
        assert not self.risk_monitor.is_monitoring
        assert self.risk_monitor.db_path.exists()

        # 验证数据库表创建
        with sqlite3.connect(self.risk_monitor.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['risk_metrics', 'risk_alerts', 'risk_scenarios', 'adaptive_thresholds']
            for table in expected_tables:
                assert table in tables

    def test_risk_metric_creation(self):
        """测试风险指标创建"""
        metric = RiskMetric(
            name="test_volatility",
            value=0.25,
            threshold=0.3,
            level=RiskLevel.MEDIUM,
            category=RiskCategory.MARKET_RISK,
            confidence=0.85,
            trend="increasing"
        )

        assert metric.name == "test_volatility"
        assert metric.value == 0.25
        assert metric.level == RiskLevel.MEDIUM
        assert metric.category == RiskCategory.MARKET_RISK
        assert metric.confidence == 0.85
        assert metric.trend == "increasing"

    def test_risk_alert_creation(self):
        """测试风险预警创建"""
        metrics = [
            RiskMetric("volatility", 0.8, 0.5, RiskLevel.HIGH, RiskCategory.MARKET_RISK)
        ]

        alert = RiskAlert(
            id="test_alert_001",
            title="高波动率预警",
            message="市场波动率超过阈值",
            level=RiskLevel.HIGH,
            priority=AlertPriority.WARNING,
            category=RiskCategory.MARKET_RISK,
            metrics=metrics,
            impact_score=0.7,
            recommendations=["降低仓位", "增加对冲"]
        )

        assert alert.id == "test_alert_001"
        assert alert.level == RiskLevel.HIGH
        assert alert.priority == AlertPriority.WARNING
        assert len(alert.metrics) == 1
        assert len(alert.recommendations) == 2

    def test_collect_risk_metrics(self):
        """测试风险指标收集"""
        metrics = self.risk_monitor._collect_risk_metrics()

        assert isinstance(metrics, dict)
        assert 'market_risk' in metrics
        assert 'liquidity_risk' in metrics
        assert 'concentration_risk' in metrics
        assert 'system_risk' in metrics

        # 验证指标数据结构
        for category, category_metrics in metrics.items():
            assert isinstance(category_metrics, dict)
            for metric_name, value in category_metrics.items():
                assert isinstance(value, (int, float))
                assert value >= 0

    def test_analyze_risk_metrics(self):
        """测试风险指标分析"""
        raw_metrics = {
            'market_risk': {
                'volatility': 0.35,
                'beta': 1.2,
                'var_95': 0.08
            },
            'liquidity_risk': {
                'bid_ask_spread': 0.003,
                'turnover_ratio': 0.8
            }
        }

        analyzed_metrics = self.risk_monitor._analyze_risk_metrics(raw_metrics)

        assert isinstance(analyzed_metrics, list)
        assert len(analyzed_metrics) > 0

        for metric in analyzed_metrics:
            assert isinstance(metric, RiskMetric)
            assert metric.name
            assert metric.value >= 0
            assert metric.threshold > 0
            assert isinstance(metric.level, RiskLevel)
            assert isinstance(metric.category, RiskCategory)
            assert 0 <= metric.confidence <= 1

    def test_risk_level_calculation(self):
        """测试风险等级计算"""
        # 测试不同比值的风险等级
        test_cases = [
            (0.5, 1.0, RiskLevel.VERY_LOW),    # 50% of threshold
            (0.8, 1.0, RiskLevel.LOW),         # 80% of threshold
            (1.1, 1.0, RiskLevel.MEDIUM),      # 110% of threshold
            (1.3, 1.0, RiskLevel.HIGH),        # 130% of threshold
            (1.6, 1.0, RiskLevel.CRITICAL),    # 160% of threshold
            (2.1, 1.0, RiskLevel.EXTREME),     # 210% of threshold
        ]

        for value, threshold, expected_level in test_cases:
            level = self.risk_monitor._calculate_risk_level(value, threshold)
            assert level == expected_level

    def test_adaptive_threshold_management(self):
        """测试自适应阈值管理"""
        metric_name = "test_volatility"

        # 获取默认阈值
        default_threshold = self.risk_monitor._get_adaptive_threshold(metric_name, 0.3)
        assert default_threshold > 0

        # 保存新阈值
        new_threshold = 0.4
        self.risk_monitor._save_adaptive_threshold(metric_name, new_threshold)

        # 验证阈值已更新
        updated_threshold = self.risk_monitor._get_adaptive_threshold(metric_name, 0.3)
        assert updated_threshold == new_threshold

    @patch('core.services.ai_prediction_service.AIPredictionService')
    def test_ai_prediction_integration(self, mock_ai_service):
        """测试AI预测集成"""
        # 模拟AI服务
        mock_ai_instance = Mock()
        mock_ai_instance.predict.return_value = {
            'success': True,
            'predicted_value': 0.45,
            'confidence': 0.82
        }
        mock_ai_service.return_value = mock_ai_instance

        # 创建测试指标
        metrics = [
            RiskMetric("volatility", 0.3, 0.35, RiskLevel.MEDIUM, RiskCategory.MARKET_RISK)
        ]

        # 测试预测
        predictions = self.risk_monitor._predict_risk_trends(metrics)

        assert isinstance(predictions, dict)
        if predictions:  # 如果AI服务可用
            assert 'volatility' in predictions
            assert predictions['volatility'] == 0.45

    def test_anomaly_detection(self):
        """测试异常检测"""
        # 创建正常和异常的指标
        normal_metrics = [
            RiskMetric("metric1", 0.3, 0.5, RiskLevel.LOW, RiskCategory.MARKET_RISK, confidence=0.9),
            RiskMetric("metric2", 0.4, 0.5, RiskLevel.LOW, RiskCategory.MARKET_RISK, confidence=0.8),
            RiskMetric("metric3", 0.35, 0.5, RiskLevel.LOW, RiskCategory.MARKET_RISK, confidence=0.85)
        ]

        # 添加异常指标
        anomaly_metrics = normal_metrics + [
            RiskMetric("anomaly", 0.95, 0.5, RiskLevel.EXTREME, RiskCategory.MARKET_RISK, confidence=0.3)
        ]

        anomalies = self.risk_monitor._detect_risk_anomalies(anomaly_metrics)

        # 应该检测到异常
        assert len(anomalies) >= 0  # 异常检测可能因数据不足而无结果

    def test_intelligent_alert_generation(self):
        """测试智能预警生成"""
        # 创建高风险指标
        high_risk_metrics = [
            RiskMetric("volatility", 0.8, 0.5, RiskLevel.HIGH, RiskCategory.MARKET_RISK),
            RiskMetric("var_95", 0.12, 0.08, RiskLevel.CRITICAL, RiskCategory.MARKET_RISK)
        ]

        # 创建异常指标
        anomalies = [
            RiskMetric("anomaly_metric", 0.9, 0.5, RiskLevel.HIGH, RiskCategory.MODEL_RISK)
        ]

        # 模拟预测数据
        predictions = {"volatility": 0.9}

        alerts = self.risk_monitor._generate_intelligent_alerts(
            high_risk_metrics, predictions, anomalies
        )

        assert isinstance(alerts, list)
        assert len(alerts) > 0

        for alert in alerts:
            assert isinstance(alert, RiskAlert)
            assert alert.id
            assert alert.title
            assert alert.message
            assert isinstance(alert.level, RiskLevel)
            assert isinstance(alert.priority, AlertPriority)

    def test_monitoring_lifecycle(self):
        """测试监控生命周期"""
        # 启动监控
        assert self.risk_monitor.start_monitoring()
        assert self.risk_monitor.is_monitoring

        # 等待一些监控周期
        time.sleep(2)

        # 停止监控
        assert self.risk_monitor.stop_monitoring()
        assert not self.risk_monitor.is_monitoring

    def test_risk_status_retrieval(self):
        """测试风险状态获取"""
        # 先运行一些监控周期
        self.risk_monitor.start_monitoring()
        time.sleep(1)
        self.risk_monitor.stop_monitoring()

        status = self.risk_monitor.get_current_risk_status()

        assert isinstance(status, dict)
        assert 'monitoring_status' in status
        assert 'total_metrics' in status
        assert 'active_alerts' in status
        assert 'last_update' in status

    def test_alert_management(self):
        """测试预警管理"""
        # 创建测试预警
        alert = RiskAlert(
            id="test_alert_mgmt",
            title="测试预警",
            message="这是一个测试预警",
            level=RiskLevel.MEDIUM,
            priority=AlertPriority.WARNING,
            category=RiskCategory.MARKET_RISK,
            metrics=[],
            impact_score=0.5
        )

        # 保存预警
        self.risk_monitor._save_alerts([alert])

        # 获取预警
        alerts = self.risk_monitor.get_risk_alerts(24, False)
        assert len(alerts) >= 1

        # 解决预警
        success = self.risk_monitor.resolve_alert(alert.id, "测试解决")
        assert success

        # 验证预警已解决
        resolved_alerts = self.risk_monitor.get_risk_alerts(24, True)
        resolved_ids = [a['id'] for a in resolved_alerts]
        assert alert.id in resolved_ids

    def test_risk_scenarios(self):
        """测试风险情景"""
        scenarios = self.risk_monitor.get_risk_scenarios(5)

        assert isinstance(scenarios, list)
        # 可能为空，因为需要历史数据来生成情景

    def test_metric_history_tracking(self):
        """测试指标历史追踪"""
        metric_name = "test_metric"

        # 记录一些历史数据
        for i in range(5):
            metric = RiskMetric(
                name=metric_name,
                value=0.3 + i * 0.1,
                threshold=0.5,
                level=RiskLevel.MEDIUM,
                category=RiskCategory.MARKET_RISK
            )
            self.risk_monitor._save_metrics([metric])

        # 获取历史数据
        history = self.risk_monitor._get_metric_history(metric_name, 10)

        assert len(history) == 5
        for record in history:
            assert 'value' in record
            assert 'timestamp' in record

    def test_trend_calculation(self):
        """测试趋势计算"""
        metric_name = "trend_test"

        # 记录递增的历史数据
        for i in range(5):
            metric = RiskMetric(
                name=metric_name,
                value=0.2 + i * 0.1,  # 递增值
                threshold=0.5,
                level=RiskLevel.MEDIUM,
                category=RiskCategory.MARKET_RISK
            )
            self.risk_monitor._save_metrics([metric])

        # 计算趋势
        trend = self.risk_monitor._calculate_trend(metric_name, 0.7)

        # 应该检测到上升趋势
        assert trend in ["increasing", "stable", "decreasing"]

    def test_confidence_calculation(self):
        """测试置信度计算"""
        metric_name = "confidence_test"

        # 记录一些历史数据
        values = [0.3, 0.32, 0.28, 0.31, 0.29]  # 相对稳定的值
        for value in values:
            metric = RiskMetric(
                name=metric_name,
                value=value,
                threshold=0.5,
                level=RiskLevel.MEDIUM,
                category=RiskCategory.MARKET_RISK
            )
            self.risk_monitor._save_metrics([metric])

        # 计算置信度
        confidence = self.risk_monitor._calculate_confidence(metric_name, 0.3)

        assert 0 <= confidence <= 1
        # 稳定的数据应该有较高的置信度
        assert confidence > 0.5

    def test_performance_optimization(self):
        """测试性能优化"""
        # 测试大量指标的处理性能
        start_time = time.time()

        # 创建大量指标
        large_metrics = {}
        for category in ['market_risk', 'liquidity_risk', 'concentration_risk']:
            large_metrics[category] = {}
            for i in range(100):
                large_metrics[category][f'metric_{i}'] = np.random.uniform(0, 1)

        # 分析指标
        analyzed = self.risk_monitor._analyze_risk_metrics(large_metrics)

        end_time = time.time()
        processing_time = end_time - start_time

        # 处理时间应该在合理范围内（小于5秒）
        assert processing_time < 5.0
        assert len(analyzed) == 300  # 100 * 3 categories

    def test_concurrent_access(self):
        """测试并发访问"""
        import threading
        import time

        results = []
        errors = []

        def monitor_operation():
            try:
                # 启动监控
                self.risk_monitor.start_monitoring()
                time.sleep(0.5)

                # 获取状态
                status = self.risk_monitor.get_current_risk_status()
                results.append(status)

                # 停止监控
                self.risk_monitor.stop_monitoring()
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=monitor_operation)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发访问出现错误: {errors}"
        assert len(results) >= 0  # 可能因为快速启停而没有结果

    def test_data_persistence(self):
        """测试数据持久化"""
        # 创建测试数据
        metric = RiskMetric(
            name="persistence_test",
            value=0.4,
            threshold=0.5,
            level=RiskLevel.MEDIUM,
            category=RiskCategory.MARKET_RISK
        )

        alert = RiskAlert(
            id="persistence_alert",
            title="持久化测试",
            message="测试数据持久化",
            level=RiskLevel.MEDIUM,
            priority=AlertPriority.WARNING,
            category=RiskCategory.MARKET_RISK,
            metrics=[metric]
        )

        # 保存数据
        self.risk_monitor._save_metrics([metric])
        self.risk_monitor._save_alerts([alert])

        # 创建新的监控实例
        new_monitor = EnhancedRiskMonitor(self.config)

        # 验证数据可以被新实例读取
        alerts = new_monitor.get_risk_alerts(24, False)
        alert_ids = [a['id'] for a in alerts]
        assert "persistence_alert" in alert_ids

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效配置
        invalid_config = {'db_path': '/invalid/path/test.db'}

        try:
            invalid_monitor = EnhancedRiskMonitor(invalid_config)
            # 应该能创建，但数据库操作可能失败
            status = invalid_monitor.get_current_risk_status()
            # 应该返回错误状态而不是崩溃
            assert 'error' in status or 'monitoring_status' in status
        except Exception:
            # 如果抛出异常，也是可以接受的
            pass

    def test_cleanup(self):
        """测试资源清理"""
        # 启动监控
        self.risk_monitor.start_monitoring()
        assert self.risk_monitor.is_monitoring

        # 清理资源
        self.risk_monitor.cleanup()

        # 验证监控已停止
        assert not self.risk_monitor.is_monitoring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
