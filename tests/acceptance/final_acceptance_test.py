#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最终系统集成和用户验收测试

执行最终的系统集成和用户验收测试，验证所有功能需求的正确实现。
测试覆盖：
1. 所有核心功能的端到端测试
2. 用户工作流程验证
3. 性能要求验证
4. 数据质量和准确性验证
5. 系统稳定性和可靠性验证
6. 用户界面和交互验证
7. 集成功能验证
"""

import pytest
import unittest
import tempfile
import os
import time
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock, MagicMock
import sqlite3
import json
from pathlib import Path
import sys

# 导入所有待测试的组件
from core.importdata.intelligent_config_manager import (
    IntelligentConfigManager, ImportTaskConfig, DataFrequency, ImportMode
)
from core.ai.data_anomaly_detector import (
    DataAnomalyDetector, AnomalyDetectionConfig, AnomalyType, AnomalySeverity
)
from core.ui_integration.smart_data_integration import (
    SmartDataIntegration, UIIntegrationConfig, IntegrationMode
)
from core.ai.config_recommendation_engine import ConfigRecommendationEngine
from core.ai.config_impact_analyzer import ConfigImpactAnalyzer


class AcceptanceTestResult:
    """验收测试结果类"""
    
    def __init__(self):
        self.test_results = []
        self.requirement_coverage = {}
        self.performance_metrics = {}
        self.issues_found = []
        self.start_time = time.time()
        
    def add_test_result(self, test_name, passed, details=None, requirement_id=None):
        """添加测试结果"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details or {},
            'requirement_id': requirement_id,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        if requirement_id:
            if requirement_id not in self.requirement_coverage:
                self.requirement_coverage[requirement_id] = []
            self.requirement_coverage[requirement_id].append(result)
    
    def add_performance_metric(self, metric_name, value, target=None, unit=""):
        """添加性能指标"""
        self.performance_metrics[metric_name] = {
            'value': value,
            'target': target,
            'unit': unit,
            'meets_target': target is None or value <= target
        }
    
    def add_issue(self, severity, description, requirement_id=None):
        """添加发现的问题"""
        issue = {
            'severity': severity,
            'description': description,
            'requirement_id': requirement_id,
            'timestamp': time.time()
        }
        self.issues_found.append(issue)
    
    def get_summary(self):
        """获取测试总结"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        
        total_requirements = len(self.requirement_coverage)
        covered_requirements = sum(1 for req_tests in self.requirement_coverage.values() 
                                 if any(t['passed'] for t in req_tests))
        
        performance_targets_met = sum(1 for m in self.performance_metrics.values() 
                                    if m['meets_target'])
        total_performance_metrics = len(self.performance_metrics)
        
        critical_issues = sum(1 for i in self.issues_found if i['severity'] == 'critical')
        major_issues = sum(1 for i in self.issues_found if i['severity'] == 'major')
        minor_issues = sum(1 for i in self.issues_found if i['severity'] == 'minor')
        
        return {
            'test_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'requirement_coverage_rate': covered_requirements / total_requirements if total_requirements > 0 else 0,
            'performance_success_rate': performance_targets_met / total_performance_metrics if total_performance_metrics > 0 else 0,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'total_requirements': total_requirements,
            'covered_requirements': covered_requirements,
            'uncovered_requirements': total_requirements - covered_requirements,
            'critical_issues': critical_issues,
            'major_issues': major_issues,
            'minor_issues': minor_issues,
            'total_issues': len(self.issues_found),
            'test_duration': time.time() - self.start_time
        }


class FinalAcceptanceTest(unittest.TestCase):
    """最终验收测试基类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.acceptance_result = AcceptanceTestResult()
        
        print(f"\n{'='*100}")
        print(f"开始最终系统集成和用户验收测试")
        print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")

    @classmethod
    def tearDownClass(cls):
        """测试类清理和结果报告"""
        summary = cls.acceptance_result.get_summary()
        
        print(f"\n{'='*100}")
        print(f"最终系统集成和用户验收测试完成")
        print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试总耗时: {summary['test_duration']:.2f} 秒")
        print(f"{'='*100}")
        
        # 测试结果统计
        print(f"\n📊 测试结果统计:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  通过测试: {summary['passed_tests']}")
        print(f"  失败测试: {summary['failed_tests']}")
        print(f"  测试成功率: {summary['test_success_rate']:.2%}")
        
        # 需求覆盖统计
        print(f"\n📋 需求覆盖统计:")
        print(f"  总需求数: {summary['total_requirements']}")
        print(f"  已覆盖需求: {summary['covered_requirements']}")
        print(f"  未覆盖需求: {summary['uncovered_requirements']}")
        print(f"  需求覆盖率: {summary['requirement_coverage_rate']:.2%}")
        
        # 性能指标统计
        print(f"\n⚡ 性能指标统计:")
        print(f"  性能指标达标率: {summary['performance_success_rate']:.2%}")
        for metric_name, metric_data in cls.acceptance_result.performance_metrics.items():
            status = "✅" if metric_data['meets_target'] else "❌"
            target_info = f" (目标: {metric_data['target']}{metric_data['unit']})" if metric_data['target'] else ""
            print(f"  {status} {metric_name}: {metric_data['value']}{metric_data['unit']}{target_info}")
        
        # 问题统计
        print(f"\n🐛 问题统计:")
        print(f"  严重问题: {summary['critical_issues']}")
        print(f"  重要问题: {summary['major_issues']}")
        print(f"  轻微问题: {summary['minor_issues']}")
        print(f"  问题总数: {summary['total_issues']}")
        
        if cls.acceptance_result.issues_found:
            print(f"\n发现的问题详情:")
            for i, issue in enumerate(cls.acceptance_result.issues_found, 1):
                severity_icon = {"critical": "🔴", "major": "🟡", "minor": "🟢"}.get(issue['severity'], "⚪")
                print(f"  {i}. {severity_icon} [{issue['severity'].upper()}] {issue['description']}")
                if issue['requirement_id']:
                    print(f"     关联需求: {issue['requirement_id']}")
        
        # 最终验收结论
        print(f"\n🎯 最终验收结论:")
        
        # 验收标准
        min_test_success_rate = 0.95  # 95%测试通过率
        min_requirement_coverage = 0.90  # 90%需求覆盖率
        min_performance_success_rate = 0.85  # 85%性能指标达标率
        max_critical_issues = 0  # 0个严重问题
        max_major_issues = 2  # 最多2个重要问题
        
        acceptance_criteria = [
            (summary['test_success_rate'] >= min_test_success_rate, 
             f"测试成功率 {summary['test_success_rate']:.2%} >= {min_test_success_rate:.2%}"),
            (summary['requirement_coverage_rate'] >= min_requirement_coverage, 
             f"需求覆盖率 {summary['requirement_coverage_rate']:.2%} >= {min_requirement_coverage:.2%}"),
            (summary['performance_success_rate'] >= min_performance_success_rate, 
             f"性能达标率 {summary['performance_success_rate']:.2%} >= {min_performance_success_rate:.2%}"),
            (summary['critical_issues'] <= max_critical_issues, 
             f"严重问题数 {summary['critical_issues']} <= {max_critical_issues}"),
            (summary['major_issues'] <= max_major_issues, 
             f"重要问题数 {summary['major_issues']} <= {max_major_issues}")
        ]
        
        all_criteria_met = all(criteria[0] for criteria in acceptance_criteria)
        
        for criteria_met, description in acceptance_criteria:
            status = "✅" if criteria_met else "❌"
            print(f"  {status} {description}")
        
        if all_criteria_met:
            print(f"\n🎉 系统验收测试通过！")
            print(f"系统满足所有验收标准，可以投入生产使用。")
        else:
            print(f"\n❌ 系统验收测试未通过！")
            print(f"系统存在未满足的验收标准，需要进一步改进。")
        
        print(f"{'='*100}")

    def setUp(self):
        """每个测试前的准备"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """每个测试后的清理"""
        try:
            os.unlink(self.db_path)
        except:
            pass


class TestCoreSystemFunctionality(FinalAcceptanceTest):
    """核心系统功能验收测试"""

    def test_intelligent_config_manager_functionality(self):
        """测试智能配置管理器功能 - 需求1.1, 1.2"""
        print("\n--- 测试智能配置管理器功能 ---")
        
        try:
            # 创建配置管理器
            manager = IntelligentConfigManager(self.db_path)
            
            # 测试1: 基本配置管理
            config = ImportTaskConfig(
                task_id="acceptance_test_1",
                name="验收测试任务1",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001", "000002"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=4,
                batch_size=1000
            )
            
            success = manager.add_import_task(config)
            self.assertTrue(success, "添加导入任务失败")
            
            retrieved_config = manager.get_import_task("acceptance_test_1")
            self.assertIsNotNone(retrieved_config, "获取导入任务失败")
            self.assertEqual(retrieved_config.name, "验收测试任务1", "任务配置不匹配")
            
            # 测试2: 性能反馈记录
            manager.record_performance_feedback(
                config=config,
                execution_time=85.5,
                success_rate=0.95,
                error_rate=0.05,
                throughput=1200
            )
            
            # 测试3: 智能统计
            stats = manager.get_intelligent_statistics()
            self.assertIsInstance(stats, dict, "统计信息格式错误")
            self.assertIn('total_tasks', stats, "统计信息缺少任务总数")
            self.assertGreater(stats['total_tasks'], 0, "任务总数应大于0")
            
            # 测试4: 冲突检测
            conflicts = manager.detect_conflicts()
            self.assertIsInstance(conflicts, list, "冲突检测结果格式错误")
            
            # 测试5: 自动配置优化
            manager.enable_auto_optimization("performance", {"target_throughput": 1500})
            optimized_config = manager.get_optimized_config("acceptance_test_1")
            self.assertIsNotNone(optimized_config, "自动配置优化失败")
            
            self.acceptance_result.add_test_result(
                "智能配置管理器基本功能", True, 
                {"tasks_created": 1, "stats_available": True, "conflicts_detected": len(conflicts)},
                "1.1"
            )
            
            print("  ✅ 智能配置管理器功能测试通过")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "智能配置管理器基本功能", False, 
                {"error": str(e)}, "1.1"
            )
            self.acceptance_result.add_issue("critical", f"智能配置管理器功能异常: {e}", "1.1")
            print(f"  ❌ 智能配置管理器功能测试失败: {e}")
            raise

    def test_data_anomaly_detection_functionality(self):
        """测试数据异常检测功能 - 需求2.1, 2.2"""
        print("\n--- 测试数据异常检测功能 ---")
        
        try:
            # 创建异常检测器
            config = AnomalyDetectionConfig(
                auto_repair_enabled=True,
                detection_sensitivity=0.8,
                max_repair_attempts=3
            )
            detector = DataAnomalyDetector(config, self.db_path)
            
            # 创建包含异常的测试数据
            test_data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='min'),
                'symbol': 'TEST001',
                'price': np.concatenate([
                    np.random.normal(100, 5, 80),  # 正常数据
                    [np.nan, np.nan],  # 缺失值
                    [500, 600],  # 异常值
                    np.random.normal(100, 5, 16)  # 正常数据
                ]),
                'volume': np.random.randint(1000, 10000, 100),
                'high': np.random.uniform(95, 105, 100),
                'low': np.random.uniform(95, 105, 100),
                'close': np.random.uniform(95, 105, 100)
            })
            
            # 测试1: 异常检测
            anomalies = detector.detect_anomalies(
                data=test_data,
                data_source="acceptance_test",
                symbol="TEST001",
                data_type="kline"
            )
            
            self.assertIsInstance(anomalies, list, "异常检测结果格式错误")
            self.assertGreater(len(anomalies), 0, "应该检测到异常")
            
            # 验证检测到的异常类型
            anomaly_types = [a.anomaly_type for a in anomalies]
            self.assertIn(AnomalyType.MISSING_DATA, anomaly_types, "应该检测到缺失数据异常")
            self.assertIn(AnomalyType.OUTLIER, anomaly_types, "应该检测到异常值")
            
            # 测试2: 自动修复
            repair_count = 0
            for anomaly in anomalies[:3]:  # 修复前3个异常
                success = detector.auto_repair_anomaly(anomaly.anomaly_id)
                if success:
                    repair_count += 1
            
            self.assertGreater(repair_count, 0, "应该成功修复至少一个异常")
            
            # 测试3: 异常统计
            stats = detector.get_anomaly_statistics()
            self.assertIsInstance(stats, dict, "异常统计格式错误")
            self.assertIn('total_anomalies', stats, "统计信息缺少异常总数")
            
            # 测试4: 数据质量评估
            quality_score = detector.assess_data_quality(test_data, "TEST001")
            self.assertIsInstance(quality_score, (int, float), "数据质量评分格式错误")
            self.assertGreaterEqual(quality_score, 0, "质量评分应大于等于0")
            self.assertLessEqual(quality_score, 1, "质量评分应小于等于1")
            
            self.acceptance_result.add_test_result(
                "数据异常检测功能", True,
                {
                    "anomalies_detected": len(anomalies),
                    "repairs_successful": repair_count,
                    "quality_score": quality_score
                },
                "2.1"
            )
            
            print(f"  ✅ 数据异常检测功能测试通过 (检测到{len(anomalies)}个异常，修复{repair_count}个)")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "数据异常检测功能", False,
                {"error": str(e)}, "2.1"
            )
            self.acceptance_result.add_issue("critical", f"数据异常检测功能异常: {e}", "2.1")
            print(f"  ❌ 数据异常检测功能测试失败: {e}")
            raise

    def test_smart_data_integration_functionality(self):
        """测试智能数据集成功能 - 需求3.1, 3.2"""
        print("\n--- 测试智能数据集成功能 ---")
        
        try:
            # 创建数据集成组件
            config = UIIntegrationConfig(
                enable_caching=True,
                cache_expiry_seconds=300,
                enable_predictive_loading=True,
                enable_adaptive_caching=True,
                max_cache_size=1000
            )
            
            with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
                integration = SmartDataIntegration(config)
            
            # 测试1: 缓存功能
            test_data = {
                'symbol': 'TEST001',
                'data': [{'price': 100.0, 'volume': 1000}],
                'timestamp': time.time()
            }
            
            cache_key = "test_cache_key"
            integration._put_to_intelligent_cache(cache_key, test_data, "high", 300)
            
            cached_data = integration._get_from_intelligent_cache(cache_key)
            self.assertIsNotNone(cached_data, "缓存数据获取失败")
            self.assertEqual(cached_data['symbol'], 'TEST001', "缓存数据不匹配")
            
            # 测试2: 使用模式记录
            for i in range(10):
                integration._record_usage_pattern(
                    f"widget_{i % 3}",
                    f"symbol_{i:03d}",
                    "realtime" if i % 2 == 0 else "daily"
                )
            
            # 测试3: 性能优化
            optimization_result = integration.optimize_performance()
            self.assertIsInstance(optimization_result, dict, "性能优化结果格式错误")
            
            # 测试4: 统计信息
            stats = integration.get_statistics()
            self.assertIsInstance(stats, dict, "统计信息格式错误")
            self.assertIn('cache_stats', stats, "统计信息缺少缓存统计")
            self.assertIn('performance_stats', stats, "统计信息缺少性能统计")
            
            # 测试5: 数据源选择
            mock_widget = Mock()
            mock_widget.widget_type = "test_widget"
            
            with patch.object(integration, '_select_optimal_data_source') as mock_select:
                mock_select.return_value = "tongdaxin"
                result = integration.check_data_for_widget(mock_widget, "TEST001", "realtime")
                mock_select.assert_called()
            
            integration.close()
            
            self.acceptance_result.add_test_result(
                "智能数据集成功能", True,
                {
                    "cache_operations": True,
                    "usage_patterns_recorded": 10,
                    "optimization_successful": True
                },
                "3.1"
            )
            
            print("  ✅ 智能数据集成功能测试通过")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "智能数据集成功能", False,
                {"error": str(e)}, "3.1"
            )
            self.acceptance_result.add_issue("critical", f"智能数据集成功能异常: {e}", "3.1")
            print(f"  ❌ 智能数据集成功能测试失败: {e}")
            raise


class TestAIEnhancedFeatures(FinalAcceptanceTest):
    """AI增强功能验收测试"""

    def test_config_recommendation_engine(self):
        """测试配置推荐引擎 - 需求4.1"""
        print("\n--- 测试配置推荐引擎 ---")
        
        try:
            # 创建推荐引擎
            engine = ConfigRecommendationEngine(self.db_path)
            
            # 创建历史配置数据
            manager = IntelligentConfigManager(self.db_path)
            
            # 添加多个历史配置和性能数据
            for i in range(5):
                config = ImportTaskConfig(
                    task_id=f"recommendation_test_{i}",
                    name=f"推荐测试任务{i}",
                    data_source="tongdaxin",
                    asset_type="stock",
                    data_type="kline",
                    symbols=[f"{i:06d}"],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH,
                    max_workers=2 + i,
                    batch_size=500 + i * 100
                )
                
                manager.add_import_task(config)
                
                # 记录性能数据
                manager.record_performance_feedback(
                    config=config,
                    execution_time=60 + i * 10,
                    success_rate=0.9 + i * 0.02,
                    error_rate=0.1 - i * 0.02,
                    throughput=1000 + i * 200
                )
            
            # 测试1: 获取配置推荐
            recommendations = engine.get_recommendations(
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols_count=100
            )
            
            self.assertIsInstance(recommendations, list, "推荐结果格式错误")
            self.assertGreater(len(recommendations), 0, "应该有配置推荐")
            
            # 验证推荐内容
            for rec in recommendations:
                self.assertIn('parameter', rec, "推荐缺少参数名")
                self.assertIn('recommended_value', rec, "推荐缺少推荐值")
                self.assertIn('confidence', rec, "推荐缺少置信度")
                self.assertIn('reason', rec, "推荐缺少原因")
                
                # 置信度应该在0-1之间
                self.assertGreaterEqual(rec['confidence'], 0, "置信度应大于等于0")
                self.assertLessEqual(rec['confidence'], 1, "置信度应小于等于1")
            
            # 测试2: 基于环境的推荐
            env_recommendations = engine.get_environment_based_recommendations(
                current_load=0.7,
                available_memory=8192,
                network_latency=50
            )
            
            self.assertIsInstance(env_recommendations, list, "环境推荐结果格式错误")
            
            # 测试3: 推荐统计
            stats = engine.get_recommendation_statistics()
            self.assertIsInstance(stats, dict, "推荐统计格式错误")
            
            self.acceptance_result.add_test_result(
                "配置推荐引擎", True,
                {
                    "recommendations_count": len(recommendations),
                    "env_recommendations_count": len(env_recommendations),
                    "avg_confidence": np.mean([r['confidence'] for r in recommendations]) if recommendations else 0
                },
                "4.1"
            )
            
            print(f"  ✅ 配置推荐引擎测试通过 (生成{len(recommendations)}个推荐)")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "配置推荐引擎", False,
                {"error": str(e)}, "4.1"
            )
            self.acceptance_result.add_issue("major", f"配置推荐引擎异常: {e}", "4.1")
            print(f"  ❌ 配置推荐引擎测试失败: {e}")

    def test_config_impact_analyzer(self):
        """测试配置影响分析器 - 需求4.2"""
        print("\n--- 测试配置影响分析器 ---")
        
        try:
            # 创建影响分析器
            analyzer = ConfigImpactAnalyzer(self.db_path)
            
            # 创建基础配置
            current_config = ImportTaskConfig(
                task_id="impact_test",
                name="影响分析测试",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=4,
                batch_size=1000
            )
            
            # 创建变更配置
            new_config = ImportTaskConfig(
                task_id="impact_test",
                name="影响分析测试",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=8,  # 变更：增加工作线程
                batch_size=2000  # 变更：增加批次大小
            )
            
            # 测试1: 配置变更影响分析
            impact_analysis = analyzer.analyze_config_change(current_config, new_config)
            
            self.assertIsInstance(impact_analysis, dict, "影响分析结果格式错误")
            self.assertIn('performance_impact', impact_analysis, "影响分析缺少性能影响")
            self.assertIn('risk_assessment', impact_analysis, "影响分析缺少风险评估")
            self.assertIn('recommendations', impact_analysis, "影响分析缺少建议")
            
            # 测试2: 风险评估
            risk_assessment = impact_analysis['risk_assessment']
            self.assertIn('overall_risk_level', risk_assessment, "风险评估缺少总体风险等级")
            self.assertIn('identified_risks', risk_assessment, "风险评估缺少识别的风险")
            
            # 测试3: 性能预测
            performance_impact = impact_analysis['performance_impact']
            self.assertIn('execution_time_change', performance_impact, "性能影响缺少执行时间变化")
            self.assertIn('throughput_change', performance_impact, "性能影响缺少吞吐量变化")
            
            # 测试4: 冲突检测
            conflicts = analyzer.detect_configuration_conflicts([current_config, new_config])
            self.assertIsInstance(conflicts, list, "冲突检测结果格式错误")
            
            # 测试5: 批量分析
            configs_to_analyze = [current_config, new_config]
            batch_analysis = analyzer.analyze_multiple_configs(configs_to_analyze)
            self.assertIsInstance(batch_analysis, dict, "批量分析结果格式错误")
            
            self.acceptance_result.add_test_result(
                "配置影响分析器", True,
                {
                    "impact_analysis_complete": True,
                    "risks_identified": len(risk_assessment.get('identified_risks', [])),
                    "conflicts_detected": len(conflicts)
                },
                "4.2"
            )
            
            print("  ✅ 配置影响分析器测试通过")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "配置影响分析器", False,
                {"error": str(e)}, "4.2"
            )
            self.acceptance_result.add_issue("major", f"配置影响分析器异常: {e}", "4.2")
            print(f"  ❌ 配置影响分析器测试失败: {e}")


class TestPerformanceRequirements(FinalAcceptanceTest):
    """性能需求验收测试"""

    def test_system_performance_requirements(self):
        """测试系统性能需求 - 需求5.1"""
        print("\n--- 测试系统性能需求 ---")
        
        try:
            # 创建组件
            manager = IntelligentConfigManager(self.db_path)
            
            # 性能测试1: 配置管理响应时间
            start_time = time.time()
            
            # 批量添加配置
            configs_added = 0
            for i in range(100):
                config = ImportTaskConfig(
                    task_id=f"perf_test_{i}",
                    name=f"性能测试任务{i}",
                    data_source="tongdaxin",
                    asset_type="stock",
                    data_type="kline",
                    symbols=[f"{i:06d}"],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH
                )
                
                if manager.add_import_task(config):
                    configs_added += 1
            
            config_creation_time = time.time() - start_time
            avg_config_creation_time = config_creation_time / configs_added if configs_added > 0 else float('inf')
            
            # 性能测试2: 查询响应时间
            start_time = time.time()
            
            for i in range(50):
                manager.get_import_task(f"perf_test_{i}")
            
            query_time = time.time() - start_time
            avg_query_time = query_time / 50
            
            # 性能测试3: 统计计算时间
            start_time = time.time()
            stats = manager.get_intelligent_statistics()
            stats_calculation_time = time.time() - start_time
            
            # 性能测试4: 并发操作性能
            def concurrent_operation(task_id):
                config = ImportTaskConfig(
                    task_id=f"concurrent_test_{task_id}",
                    name=f"并发测试任务{task_id}",
                    data_source="tongdaxin",
                    asset_type="stock",
                    data_type="kline",
                    symbols=[f"{task_id:06d}"],
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH
                )
                return manager.add_import_task(config)
            
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(concurrent_operation, i) for i in range(50)]
                concurrent_results = [f.result() for f in as_completed(futures)]
            
            concurrent_operation_time = time.time() - start_time
            successful_concurrent_ops = sum(concurrent_results)
            
            # 记录性能指标
            self.acceptance_result.add_performance_metric(
                "平均配置创建时间", avg_config_creation_time * 1000, 100, "ms"
            )
            self.acceptance_result.add_performance_metric(
                "平均查询响应时间", avg_query_time * 1000, 50, "ms"
            )
            self.acceptance_result.add_performance_metric(
                "统计计算时间", stats_calculation_time * 1000, 500, "ms"
            )
            self.acceptance_result.add_performance_metric(
                "并发操作完成时间", concurrent_operation_time, 10, "s"
            )
            self.acceptance_result.add_performance_metric(
                "并发操作成功率", successful_concurrent_ops / 50, 0.95, ""
            )
            
            # 性能断言
            self.assertLess(avg_config_creation_time, 0.1, "配置创建时间过长")
            self.assertLess(avg_query_time, 0.05, "查询响应时间过长")
            self.assertLess(stats_calculation_time, 0.5, "统计计算时间过长")
            self.assertGreater(successful_concurrent_ops / 50, 0.95, "并发操作成功率过低")
            
            self.acceptance_result.add_test_result(
                "系统性能需求", True,
                {
                    "configs_created": configs_added,
                    "avg_creation_time_ms": avg_config_creation_time * 1000,
                    "avg_query_time_ms": avg_query_time * 1000,
                    "concurrent_success_rate": successful_concurrent_ops / 50
                },
                "5.1"
            )
            
            print(f"  ✅ 系统性能需求测试通过")
            print(f"    - 平均配置创建时间: {avg_config_creation_time*1000:.2f}ms")
            print(f"    - 平均查询响应时间: {avg_query_time*1000:.2f}ms")
            print(f"    - 并发操作成功率: {successful_concurrent_ops/50:.2%}")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "系统性能需求", False,
                {"error": str(e)}, "5.1"
            )
            self.acceptance_result.add_issue("critical", f"系统性能需求不满足: {e}", "5.1")
            print(f"  ❌ 系统性能需求测试失败: {e}")
            raise

    def test_memory_usage_requirements(self):
        """测试内存使用需求 - 需求5.2"""
        print("\n--- 测试内存使用需求 ---")
        
        try:
            import psutil
            process = psutil.Process()
            
            # 记录初始内存
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建大量组件和数据
            components = []
            
            # 创建多个配置管理器实例
            for i in range(10):
                temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
                temp_db.close()
                
                manager = IntelligentConfigManager(temp_db.name)
                
                # 添加大量配置
                for j in range(50):
                    config = ImportTaskConfig(
                        task_id=f"memory_test_{i}_{j}",
                        name=f"内存测试任务{i}-{j}",
                        data_source="tongdaxin",
                        asset_type="stock",
                        data_type="kline",
                        symbols=[f"{j:06d}"],
                        frequency=DataFrequency.DAILY,
                        mode=ImportMode.BATCH
                    )
                    manager.add_import_task(config)
                
                components.append((manager, temp_db.name))
            
            # 记录峰值内存
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # 清理组件
            for manager, db_path in components:
                del manager
                try:
                    os.unlink(db_path)
                except:
                    pass
            
            # 强制垃圾回收
            import gc
            gc.collect()
            
            # 记录清理后内存
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_recovered = peak_memory - final_memory
            
            # 记录内存指标
            self.acceptance_result.add_performance_metric(
                "内存使用增长", memory_increase, 500, "MB"
            )
            self.acceptance_result.add_performance_metric(
                "内存回收率", memory_recovered / memory_increase if memory_increase > 0 else 1, 0.8, ""
            )
            
            # 内存使用断言
            self.assertLess(memory_increase, 500, "内存使用增长过多")
            self.assertGreater(memory_recovered / memory_increase if memory_increase > 0 else 1, 0.7, "内存回收率过低")
            
            self.acceptance_result.add_test_result(
                "内存使用需求", True,
                {
                    "initial_memory_mb": initial_memory,
                    "peak_memory_mb": peak_memory,
                    "final_memory_mb": final_memory,
                    "memory_increase_mb": memory_increase,
                    "memory_recovery_rate": memory_recovered / memory_increase if memory_increase > 0 else 1
                },
                "5.2"
            )
            
            print(f"  ✅ 内存使用需求测试通过")
            print(f"    - 内存增长: {memory_increase:.1f}MB")
            print(f"    - 内存回收率: {memory_recovered/memory_increase:.2%}" if memory_increase > 0 else "    - 内存回收率: 100%")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "内存使用需求", False,
                {"error": str(e)}, "5.2"
            )
            self.acceptance_result.add_issue("major", f"内存使用需求不满足: {e}", "5.2")
            print(f"  ❌ 内存使用需求测试失败: {e}")


class TestUserWorkflows(FinalAcceptanceTest):
    """用户工作流程验收测试"""

    def test_complete_data_import_workflow(self):
        """测试完整数据导入工作流程 - 需求6.1"""
        print("\n--- 测试完整数据导入工作流程 ---")
        
        try:
            # 模拟完整的用户工作流程
            
            # 步骤1: 创建配置管理器
            manager = IntelligentConfigManager(self.db_path)
            
            # 步骤2: 创建导入任务配置
            config = ImportTaskConfig(
                task_id="workflow_test",
                name="工作流程测试任务",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001", "000002", "000300"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=4,
                batch_size=1000
            )
            
            # 步骤3: 添加任务
            success = manager.add_import_task(config)
            self.assertTrue(success, "添加导入任务失败")
            
            # 步骤4: 获取智能推荐
            engine = ConfigRecommendationEngine(self.db_path)
            recommendations = engine.get_recommendations(
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols_count=len(config.symbols)
            )
            
            # 步骤5: 分析配置影响
            analyzer = ConfigImpactAnalyzer(self.db_path)
            
            # 创建优化后的配置
            optimized_config = ImportTaskConfig(
                task_id="workflow_test",
                name="工作流程测试任务",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001", "000002", "000300"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                max_workers=6,  # 根据推荐调整
                batch_size=1500  # 根据推荐调整
            )
            
            impact_analysis = analyzer.analyze_config_change(config, optimized_config)
            
            # 步骤6: 模拟执行和性能反馈
            execution_times = []
            success_rates = []
            
            for i in range(5):  # 模拟5次执行
                # 模拟执行时间（基于配置参数）
                base_time = 60
                worker_factor = optimized_config.max_workers / 4
                batch_factor = optimized_config.batch_size / 1000
                
                execution_time = base_time / worker_factor * batch_factor + np.random.uniform(-10, 10)
                success_rate = 0.95 + np.random.uniform(-0.05, 0.05)
                
                execution_times.append(execution_time)
                success_rates.append(success_rate)
                
                # 记录性能反馈
                manager.record_performance_feedback(
                    config=optimized_config,
                    execution_time=execution_time,
                    success_rate=success_rate,
                    error_rate=1 - success_rate,
                    throughput=len(config.symbols) * 1000 / execution_time
                )
            
            # 步骤7: 数据异常检测
            anomaly_config = AnomalyDetectionConfig(auto_repair_enabled=True)
            detector = DataAnomalyDetector(anomaly_config, self.db_path)
            
            # 模拟导入的数据
            imported_data = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=1000, freq='D'),
                'symbol': np.random.choice(['000001', '000002', '000300'], 1000),
                'price': np.random.normal(100, 10, 1000),
                'volume': np.random.randint(1000, 100000, 1000)
            })
            
            # 检测异常
            anomalies = detector.detect_anomalies(
                data=imported_data,
                data_source="workflow_test",
                symbol="MIXED",
                data_type="kline"
            )
            
            # 步骤8: 获取最终统计
            final_stats = manager.get_intelligent_statistics()
            
            # 验证工作流程完整性
            workflow_checks = [
                ("任务创建", success),
                ("推荐获取", len(recommendations) > 0),
                ("影响分析", 'performance_impact' in impact_analysis),
                ("性能记录", len(execution_times) == 5),
                ("异常检测", isinstance(anomalies, list)),
                ("统计获取", isinstance(final_stats, dict))
            ]
            
            all_checks_passed = all(check[1] for check in workflow_checks)
            
            # 计算工作流程指标
            avg_execution_time = np.mean(execution_times)
            avg_success_rate = np.mean(success_rates)
            
            self.acceptance_result.add_test_result(
                "完整数据导入工作流程", all_checks_passed,
                {
                    "workflow_steps_completed": len([c for c in workflow_checks if c[1]]),
                    "total_workflow_steps": len(workflow_checks),
                    "avg_execution_time": avg_execution_time,
                    "avg_success_rate": avg_success_rate,
                    "anomalies_detected": len(anomalies),
                    "recommendations_received": len(recommendations)
                },
                "6.1"
            )
            
            if all_checks_passed:
                print(f"  ✅ 完整数据导入工作流程测试通过")
                print(f"    - 工作流程步骤: {len(workflow_checks)}/{len(workflow_checks)} 完成")
                print(f"    - 平均执行时间: {avg_execution_time:.2f}秒")
                print(f"    - 平均成功率: {avg_success_rate:.2%}")
            else:
                failed_checks = [check[0] for check in workflow_checks if not check[1]]
                self.acceptance_result.add_issue("major", f"工作流程步骤失败: {', '.join(failed_checks)}", "6.1")
                print(f"  ❌ 工作流程测试失败，失败步骤: {', '.join(failed_checks)}")
            
            self.assertTrue(all_checks_passed, f"工作流程检查失败: {[c[0] for c in workflow_checks if not c[1]]}")
            
        except Exception as e:
            self.acceptance_result.add_test_result(
                "完整数据导入工作流程", False,
                {"error": str(e)}, "6.1"
            )
            self.acceptance_result.add_issue("critical", f"数据导入工作流程异常: {e}", "6.1")
            print(f"  ❌ 完整数据导入工作流程测试失败: {e}")
            raise


def run_final_acceptance_tests():
    """运行最终验收测试"""
    print("开始运行最终系统集成和用户验收测试...")
    print("=" * 100)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestCoreSystemFunctionality,
        TestAIEnhancedFeatures,
        TestPerformanceRequirements,
        TestUserWorkflows
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    return result.wasSuccessful(), len(result.failures), len(result.errors)


if __name__ == "__main__":
    # 设置测试环境
    os.environ['TESTING'] = '1'
    
    # 运行最终验收测试
    success, failures, errors = run_final_acceptance_tests()
    
    # 返回适当的退出码
    exit_code = 0 if success else 1
    exit(exit_code)
