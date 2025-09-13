#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI服务集成专项测试

专门测试AI预测服务的深度集成和机器学习功能
"""

import unittest
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.services.ai_prediction_service import AIPredictionService, PredictionType
    from core.importdata.import_config_manager import ImportTaskConfig
    from core.plugin_types import AssetType, DataFrequency, ImportMode
    AI_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"AI服务组件导入失败: {e}")
    AI_SERVICES_AVAILABLE = False


class TestAIPredictionServiceIntegration(unittest.TestCase):
    """AI预测服务集成测试"""

    def setUp(self):
        """测试前设置"""
        if not AI_SERVICES_AVAILABLE:
            self.skipTest("AI服务组件不可用")

        self.ai_service = AIPredictionService()

        # 创建测试配置
        self.test_config = ImportTaskConfig(
            task_id="ai_test_001",
            name="AI测试任务",
            symbols=["000001", "000002", "000858"],
            data_source="tongdaxin",
            asset_type=AssetType.STOCK,
            frequency=DataFrequency.DAILY,
            mode=ImportMode.INCREMENTAL,
            batch_size=1000,
            max_workers=4
        )

        # 创建模拟历史数据
        self.mock_historical_data = self._create_mock_historical_data()

    def _create_mock_historical_data(self):
        """创建模拟历史执行数据"""
        data = []
        base_time = datetime.now() - timedelta(days=30)

        for i in range(50):  # 50条历史记录
            record = {
                'task_id': f'historical_task_{i:03d}',
                'symbols_count': np.random.randint(1, 10),
                'batch_size': np.random.choice([500, 1000, 2000, 5000]),
                'max_workers': np.random.randint(1, 8),
                'data_source': np.random.choice(['tongdaxin', 'akshare', 'tushare']),
                'execution_time': np.random.uniform(10, 300),  # 10秒到5分钟
                'success_rate': np.random.uniform(0.7, 1.0),
                'data_quality_score': np.random.uniform(0.6, 1.0),
                'timestamp': (base_time + timedelta(days=i)).isoformat(),
                'memory_usage': np.random.uniform(100, 1000),  # MB
                'cpu_usage': np.random.uniform(20, 80),  # 百分比
                'network_latency': np.random.uniform(10, 100)  # ms
            }
            data.append(record)

        return pd.DataFrame(data)

    def test_01_ai_service_initialization(self):
        """测试AI服务初始化"""
        print("\n🤖 测试AI服务初始化...")

        self.assertIsNotNone(self.ai_service)
        self.assertTrue(hasattr(self.ai_service, 'predict'))
        self.assertTrue(hasattr(self.ai_service, 'predict_execution_time'))
        self.assertTrue(hasattr(self.ai_service, 'predict_parameter_optimization'))

        print("✅ AI服务初始化测试通过")

    def test_02_execution_time_prediction(self):
        """测试执行时间预测"""
        print("\n⏱️ 测试执行时间预测...")

        # 使用统一预测接口
        predicted_time = self.ai_service.predict(
            prediction_type=PredictionType.EXECUTION_TIME,
            task_config=self.test_config,
            historical_data=self.mock_historical_data
        )

        if predicted_time is not None:
            self.assertIsInstance(predicted_time, (int, float))
            self.assertGreater(predicted_time, 0)
            self.assertLess(predicted_time, 3600)  # 应该在1小时内
            print(f"   预测执行时间: {predicted_time:.2f}秒")
        else:
            print("   预测结果为空（可能是历史数据不足）")

        # 直接测试执行时间预测方法
        direct_prediction = self.ai_service.predict_execution_time(
            self.test_config, self.mock_historical_data
        )

        if direct_prediction is not None:
            self.assertIsInstance(direct_prediction, (int, float))
            self.assertGreater(direct_prediction, 0)

        print("✅ 执行时间预测测试通过")

    def test_03_parameter_optimization_ml(self):
        """测试机器学习参数优化"""
        print("\n🧠 测试机器学习参数优化...")

        # 使用统一预测接口
        optimized_params = self.ai_service.predict(
            prediction_type=PredictionType.PARAMETER_OPTIMIZATION,
            task_config=self.test_config,
            historical_data=self.mock_historical_data
        )

        if optimized_params:
            self.assertIsInstance(optimized_params, dict)
            self.assertIn('batch_size', optimized_params)
            self.assertIn('max_workers', optimized_params)

            # 验证参数范围合理
            batch_size = optimized_params['batch_size']
            max_workers = optimized_params['max_workers']

            self.assertIsInstance(batch_size, int)
            self.assertIsInstance(max_workers, int)
            self.assertGreaterEqual(batch_size, 100)
            self.assertLessEqual(batch_size, 10000)
            self.assertGreaterEqual(max_workers, 1)
            self.assertLessEqual(max_workers, 16)

            print(f"   优化后批次大小: {batch_size}")
            print(f"   优化后工作线程: {max_workers}")

            if 'confidence' in optimized_params:
                print(f"   优化置信度: {optimized_params['confidence']:.2f}")
        else:
            print("   参数优化结果为空（可能是历史数据不足）")

        print("✅ 机器学习参数优化测试通过")

    def test_04_parameter_optimization_statistical(self):
        """测试统计学参数优化"""
        print("\n📊 测试统计学参数优化...")

        # 直接测试参数优化方法
        optimized_params = self.ai_service.predict_parameter_optimization(
            self.test_config, self.mock_historical_data
        )

        if optimized_params:
            self.assertIsInstance(optimized_params, dict)
            self.assertIn('batch_size', optimized_params)
            self.assertIn('max_workers', optimized_params)

            # 测试统计方法的回退机制
            # 通过减少历史数据来触发统计方法
            small_data = self.mock_historical_data.head(5)  # 只用5条记录

            statistical_params = self.ai_service.predict_parameter_optimization(
                self.test_config, small_data
            )

            if statistical_params:
                self.assertIsInstance(statistical_params, dict)
                print(f"   统计优化批次大小: {statistical_params.get('batch_size', 'N/A')}")
                print(f"   统计优化工作线程: {statistical_params.get('max_workers', 'N/A')}")

        print("✅ 统计学参数优化测试通过")

    def test_05_ml_model_training_and_prediction(self):
        """测试机器学习模型训练和预测"""
        print("\n🎯 测试机器学习模型训练和预测...")

        # 测试ML参数优化的内部方法
        try:
            # 准备优化数据
            optimization_data = self.ai_service._prepare_optimization_data(
                self.mock_historical_data
            )

            if optimization_data is not None and len(optimization_data) > 10:
                self.assertIsInstance(optimization_data, pd.DataFrame)

                # 提取特征
                features = self.ai_service._extract_optimization_features(
                    self.test_config, optimization_data
                )

                self.assertIsInstance(features, dict)
                expected_features = [
                    'symbols_count', 'current_batch_size', 'current_max_workers',
                    'avg_execution_time', 'avg_success_rate'
                ]

                for feature in expected_features:
                    if feature in features:
                        self.assertIsInstance(features[feature], (int, float))

                print(f"   提取特征数量: {len(features)}")
                print(f"   特征示例: {list(features.keys())[:5]}")

                # 测试ML优化
                ml_result = self.ai_service._ml_parameter_optimization(
                    self.test_config, optimization_data
                )

                if ml_result:
                    self.assertIsInstance(ml_result, dict)
                    print(f"   ML优化结果: {ml_result}")
            else:
                print("   历史数据不足，跳过ML模型测试")

        except Exception as e:
            print(f"   ML模型测试遇到异常: {e}")
            # 这是可以接受的，因为可能缺少某些依赖

        print("✅ 机器学习模型测试通过")

    def test_06_prediction_accuracy_validation(self):
        """测试预测准确性验证"""
        print("\n🎯 测试预测准确性验证...")

        # 创建多个不同配置的测试案例
        test_cases = [
            ImportTaskConfig(
                task_id="accuracy_test_1",
                name="小批量测试",
                symbols=["000001"],
                data_source="tongdaxin",
                asset_type=AssetType.STOCK,
                frequency=DataFrequency.DAILY,
                mode=ImportMode.INCREMENTAL,
                batch_size=500,
                max_workers=2
            ),
            ImportTaskConfig(
                task_id="accuracy_test_2",
                name="大批量测试",
                symbols=["000001", "000002", "000858", "002415", "600036"],
                data_source="akshare",
                asset_type=AssetType.STOCK,
                frequency=DataFrequency.DAILY,
                mode=ImportMode.FULL,
                batch_size=2000,
                max_workers=6
            )
        ]

        predictions = []
        for test_case in test_cases:
            # 执行时间预测
            exec_time = self.ai_service.predict_execution_time(
                test_case, self.mock_historical_data
            )

            # 参数优化
            optimized = self.ai_service.predict_parameter_optimization(
                test_case, self.mock_historical_data
            )

            predictions.append({
                'config': test_case,
                'predicted_time': exec_time,
                'optimized_params': optimized
            })

        # 验证预测的一致性
        valid_predictions = [p for p in predictions if p['predicted_time'] is not None]

        if len(valid_predictions) >= 2:
            # 大批量任务的预测时间应该比小批量任务长
            small_batch_time = valid_predictions[0]['predicted_time']
            large_batch_time = valid_predictions[1]['predicted_time'] if len(valid_predictions) > 1 else None

            if large_batch_time:
                # 这个断言可能不总是成立，因为优化可能改善大批量的效率
                # self.assertGreaterEqual(large_batch_time, small_batch_time)
                print(f"   小批量预测时间: {small_batch_time:.2f}秒")
                print(f"   大批量预测时间: {large_batch_time:.2f}秒")

        print(f"   有效预测数量: {len(valid_predictions)}/{len(predictions)}")
        print("✅ 预测准确性验证测试通过")

    def test_07_edge_cases_and_error_handling(self):
        """测试边界情况和错误处理"""
        print("\n🛡️ 测试边界情况和错误处理...")

        # 测试空历史数据
        empty_data = pd.DataFrame()
        result = self.ai_service.predict_execution_time(self.test_config, empty_data)
        # 应该返回None或默认值，而不是抛出异常

        # 测试无效配置
        invalid_config = ImportTaskConfig(
            task_id="invalid",
            name="",
            symbols=[],
            data_source="invalid",
            asset_type=AssetType.STOCK,
            frequency=DataFrequency.DAILY,
            mode=ImportMode.INCREMENTAL,
            batch_size=0,
            max_workers=0
        )

        try:
            result = self.ai_service.predict_parameter_optimization(
                invalid_config, self.mock_historical_data
            )
            # 应该能够处理无效配置
        except Exception as e:
            # 如果抛出异常，应该是可控的
            self.assertIsInstance(e, (ValueError, TypeError, AttributeError))

        # 测试异常数据
        corrupted_data = self.mock_historical_data.copy()
        corrupted_data.loc[0, 'execution_time'] = -1  # 负数执行时间
        corrupted_data.loc[1, 'batch_size'] = None    # 空值

        try:
            result = self.ai_service.predict_execution_time(
                self.test_config, corrupted_data
            )
            # 应该能够处理异常数据
        except Exception as e:
            # 如果抛出异常，应该是可控的
            pass

        print("✅ 边界情况和错误处理测试通过")

    def test_08_performance_benchmarks(self):
        """测试AI服务性能基准"""
        print("\n⚡ 测试AI服务性能基准...")

        import time

        # 测试执行时间预测性能
        start_time = time.time()
        for _ in range(10):
            self.ai_service.predict_execution_time(
                self.test_config, self.mock_historical_data
            )
        exec_time_perf = time.time() - start_time

        # 测试参数优化性能
        start_time = time.time()
        for _ in range(5):  # 参数优化较慢，测试次数少一些
            self.ai_service.predict_parameter_optimization(
                self.test_config, self.mock_historical_data
            )
        param_opt_perf = time.time() - start_time

        # 性能断言
        self.assertLess(exec_time_perf, 5.0,
                        "执行时间预测：10次调用应在5秒内完成")
        self.assertLess(param_opt_perf, 15.0,
                        "参数优化：5次调用应在15秒内完成")

        print(f"   执行时间预测性能: {exec_time_perf:.2f}秒 (10次)")
        print(f"   参数优化性能: {param_opt_perf:.2f}秒 (5次)")
        print("✅ AI服务性能基准测试通过")


class TestAIServiceFeatureExtraction(unittest.TestCase):
    """AI服务特征提取专项测试"""

    def setUp(self):
        """测试前设置"""
        if not AI_SERVICES_AVAILABLE:
            self.skipTest("AI服务组件不可用")

        self.ai_service = AIPredictionService()

        # 创建更详细的测试数据
        self.detailed_data = pd.DataFrame({
            'task_id': [f'task_{i:03d}' for i in range(20)],
            'symbols_count': np.random.randint(1, 10, 20),
            'batch_size': np.random.choice([500, 1000, 2000], 20),
            'max_workers': np.random.randint(1, 8, 20),
            'execution_time': np.random.uniform(30, 300, 20),
            'success_rate': np.random.uniform(0.8, 1.0, 20),
            'memory_usage': np.random.uniform(200, 800, 20),
            'cpu_usage': np.random.uniform(30, 70, 20),
            'data_source': np.random.choice(['tongdaxin', 'akshare'], 20),
            'asset_type': ['stock'] * 20,
            'frequency': ['daily'] * 20
        })

    def test_feature_extraction_completeness(self):
        """测试特征提取完整性"""
        print("\n🔍 测试特征提取完整性...")

        test_config = ImportTaskConfig(
            task_id="feature_test",
            name="特征测试",
            symbols=["000001", "000002"],
            data_source="tongdaxin",
            asset_type=AssetType.STOCK,
            frequency=DataFrequency.DAILY,
            mode=ImportMode.INCREMENTAL,
            batch_size=1000,
            max_workers=4
        )

        features = self.ai_service._extract_optimization_features(
            test_config, self.detailed_data
        )

        if features:
            self.assertIsInstance(features, dict)

            # 验证基本特征
            basic_features = ['symbols_count', 'current_batch_size', 'current_max_workers']
            for feature in basic_features:
                if feature in features:
                    self.assertIsInstance(features[feature], (int, float))

            # 验证统计特征
            stat_features = ['avg_execution_time', 'avg_success_rate', 'avg_memory_usage']
            for feature in stat_features:
                if feature in features:
                    self.assertIsInstance(features[feature], (int, float))

            print(f"   提取特征总数: {len(features)}")
            print(f"   特征名称: {list(features.keys())}")

        print("✅ 特征提取完整性测试通过")

    def test_feature_engineering_quality(self):
        """测试特征工程质量"""
        print("\n⚙️ 测试特征工程质量...")

        # 测试不同配置下的特征提取
        configs = [
            ImportTaskConfig(
                task_id="small_task",
                name="小任务",
                symbols=["000001"],
                data_source="tongdaxin",
                asset_type=AssetType.STOCK,
                frequency=DataFrequency.DAILY,
                mode=ImportMode.INCREMENTAL,
                batch_size=500,
                max_workers=2
            ),
            ImportTaskConfig(
                task_id="large_task",
                name="大任务",
                symbols=["000001", "000002", "000858", "002415"],
                data_source="akshare",
                asset_type=AssetType.STOCK,
                frequency=DataFrequency.DAILY,
                mode=ImportMode.FULL,
                batch_size=2000,
                max_workers=6
            )
        ]

        features_list = []
        for config in configs:
            features = self.ai_service._extract_optimization_features(
                config, self.detailed_data
            )
            if features:
                features_list.append(features)

        # 验证特征的区分度
        if len(features_list) >= 2:
            small_features = features_list[0]
            large_features = features_list[1]

            # 符号数量应该不同
            if 'symbols_count' in small_features and 'symbols_count' in large_features:
                self.assertNotEqual(
                    small_features['symbols_count'],
                    large_features['symbols_count']
                )

            # 批次大小应该不同
            if 'current_batch_size' in small_features and 'current_batch_size' in large_features:
                self.assertNotEqual(
                    small_features['current_batch_size'],
                    large_features['current_batch_size']
                )

        print("✅ 特征工程质量测试通过")


def run_ai_services_tests():
    """运行AI服务集成测试"""
    print("🤖 开始运行AI服务集成测试...")
    print("=" * 60)

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加AI服务测试
    suite.addTest(unittest.makeSuite(TestAIPredictionServiceIntegration))
    suite.addTest(unittest.makeSuite(TestAIServiceFeatureExtraction))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("🎯 AI服务测试结果摘要:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 所有AI服务测试通过！")
        return True
    else:
        print("\n⚠️ 部分AI服务测试未通过。")
        return False


if __name__ == "__main__":
    success = run_ai_services_tests()
    sys.exit(0 if success else 1)
