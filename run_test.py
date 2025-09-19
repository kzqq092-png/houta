#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from tests.core.test_unified_components import (
    TestIntelligentConfigManager,
    TestConfigRecommendationEngine,
    TestConfigImpactAnalyzer,
    TestSmartDataIntegration,
    TestDataAnomalyDetector
)
import sys
import unittest
sys.path.append('.')


def run_specific_tests():
    """运行特定的测试类"""

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加IntelligentConfigManager测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntelligentConfigManager))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n=== 测试结果汇总 ===")
    print(f"运行测试数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")

    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'Unknown failure'}")

    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].strip() if 'Error:' in traceback else 'Unknown error'}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_specific_tests()
    sys.exit(0 if success else 1)
