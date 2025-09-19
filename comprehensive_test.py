#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import tempfile
import os
import unittest
from io import StringIO

sys.path.append('.')


def run_comprehensive_test():
    """运行综合测试"""
    print("开始运行综合自动化测试...")
    print("=" * 60)

    results = {}

    # 1. 基本功能测试
    print("1. 基本功能测试...")
    try:
        from core.importdata.intelligent_config_manager import IntelligentConfigManager
        from core.importdata.import_config_manager import ImportTaskConfig, DataFrequency, ImportMode

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()

        try:
            manager = IntelligentConfigManager(temp_db.name)

            config = ImportTaskConfig(
                task_id="comprehensive_test",
                name="综合测试任务",
                data_source="tongdaxin",
                asset_type="stock",
                data_type="kline",
                symbols=["000001"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH
            )

            # 测试基本操作
            assert manager.add_import_task(config) == True
            assert manager.get_import_task("comprehensive_test") is not None

            # 测试性能反馈
            manager.record_performance_feedback(
                config=config,
                execution_time=60.0,
                success_rate=0.95,
                error_rate=0.05,
                throughput=1000.0
            )

            # 测试统计信息
            stats = manager.get_intelligent_statistics()
            assert isinstance(stats, dict)

            # 测试冲突检测
            conflicts = manager.detect_config_conflicts()
            assert isinstance(conflicts, list)

            results['basic_functionality'] = "✅ 通过"

        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results['basic_functionality'] = f"❌ 失败: {e}"

    # 2. 异常检测测试
    print("2. 异常检测测试...")
    try:
        from core.ai.data_anomaly_detector import DataAnomalyDetector, AnomalyDetectionConfig
        import pandas as pd
        import numpy as np

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()

        try:
            config = AnomalyDetectionConfig(
                enable_outlier_detection=True,
                enable_missing_data_detection=True,
                enable_duplicate_detection=True,
                auto_repair_enabled=False
            )

            detector = DataAnomalyDetector(config, temp_db.name)

            # 创建测试数据
            test_data = pd.DataFrame({
                'price': [10.0, 11.0, np.nan, 12.0, 13.0],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })

            anomalies = detector.detect_anomalies(
                data=test_data,
                data_source="test",
                symbol="TEST001",
                data_type="kline"
            )

            assert isinstance(anomalies, list)

            # 测试统计信息
            stats = detector.get_anomaly_statistics()
            assert isinstance(stats, dict)

            results['anomaly_detection'] = "✅ 通过"

        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results['anomaly_detection'] = f"❌ 失败: {e}"

    # 3. 数据集成测试
    print("3. 数据集成测试...")
    try:
        from core.ui_integration.smart_data_integration import SmartDataIntegration, UIIntegrationConfig
        from unittest.mock import patch

        config = UIIntegrationConfig()

        with patch('core.ui_integration.smart_data_integration.ThreadPoolExecutor'):
            integration = SmartDataIntegration(config)

            # 测试基本功能
            assert integration is not None
            assert hasattr(integration, 'config')

            # 测试统计信息
            stats = integration.get_statistics()
            assert isinstance(stats, dict)

            # 清理
            integration.close()

            results['data_integration'] = "✅ 通过"

    except Exception as e:
        results['data_integration'] = f"❌ 失败: {e}"

    # 4. 配置推荐测试
    print("4. 配置推荐测试...")
    try:
        from core.ai.config_recommendation_engine import ConfigRecommendationEngine
        from unittest.mock import patch

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()

        try:
            with patch('core.ai.config_recommendation_engine.AIPredictionService'):
                engine = ConfigRecommendationEngine(temp_db.name)

                # 测试基本功能
                assert engine is not None

                results['config_recommendation'] = "✅ 通过"

        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results['config_recommendation'] = f"❌ 失败: {e}"

    # 5. 配置影响分析测试
    print("5. 配置影响分析测试...")
    try:
        from core.ai.config_impact_analyzer import ConfigImpactAnalyzer
        from unittest.mock import patch

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        temp_db.close()

        try:
            with patch('core.ai.config_impact_analyzer.AIPredictionService'):
                analyzer = ConfigImpactAnalyzer(temp_db.name)

                # 测试基本功能
                assert analyzer is not None

                results['config_impact_analysis'] = "✅ 通过"

        finally:
            try:
                os.unlink(temp_db.name)
            except:
                pass

    except Exception as e:
        results['config_impact_analysis'] = f"❌ 失败: {e}"

    # 输出结果
    print("\n" + "=" * 60)
    print("综合测试结果汇总:")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        print(f"{test_name:25} : {result}")
        if "✅" in result:
            passed += 1

    print("=" * 60)
    print(f"总计: {passed}/{total} 通过")
    print(f"成功率: {passed/total*100:.1f}%")

    if passed == total:
        print("🎉 所有测试通过！系统运行正常！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
