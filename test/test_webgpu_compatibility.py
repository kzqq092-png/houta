"""
WebGPU兼容性测试框架测试用例

测试兼容性检测、报告生成和测试套件功能

作者: HIkyuu团队
版本: 1.0.0
"""

from core.webgpu.compatibility_testing import (
    CompatibilityTestSuite,
    BrowserCompatibilityTest,
    GPUCompatibilityTest,
    OSCompatibilityTest,
    WebGPUFeatureTest,
    CompatibilityLevel,
    TestResult,
    run_compatibility_test,
    check_webgpu_compatibility
)
import unittest
import tempfile
import json
import os
from unittest.mock import Mock, patch, MagicMock
import sys
import platform

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestBrowserCompatibilityTest(unittest.TestCase):
    """浏览器兼容性测试"""

    def setUp(self):
        self.browser_test = BrowserCompatibilityTest()

    def test_get_browser_info(self):
        """测试获取浏览器信息"""
        browser_info = self.browser_test.get_browser_info()

        self.assertIsInstance(browser_info, dict)
        self.assertIn('default_browser', browser_info)
        self.assertIn('webgpu_available', browser_info)
        self.assertIn('user_agent', browser_info)

    def test_webgpu_support_test(self):
        """测试WebGPU支持检测"""
        result = self.browser_test.test_webgpu_support()

        self.assertEqual(result.test_case.name, "WebGPU Browser Support")
        self.assertEqual(result.test_case.category, "browser")
        self.assertIn(result.result, [TestResult.PASSED, TestResult.FAILED, TestResult.ERROR])
        self.assertIsInstance(result.duration, float)
        self.assertGreater(result.duration, 0)

        if result.result == TestResult.PASSED:
            self.assertIn('browser_info', result.details)
            self.assertIn('webgpu_api_available', result.details)
            self.assertIn('supported_features', result.details)


class TestGPUCompatibilityTest(unittest.TestCase):
    """GPU兼容性测试"""

    def setUp(self):
        self.gpu_test = GPUCompatibilityTest()

    def test_get_gpu_info(self):
        """测试获取GPU信息"""
        gpu_info = self.gpu_test.get_gpu_info()

        self.assertIsInstance(gpu_info, list)
        self.assertGreater(len(gpu_info), 0)

        for gpu in gpu_info:
            self.assertIsInstance(gpu, dict)
            self.assertIn('name', gpu)
            self.assertIn('vendor', gpu)
            self.assertIn('driver_version', gpu)

    def test_detect_vendor(self):
        """测试GPU厂商检测"""
        test_cases = [
            ("NVIDIA GeForce RTX 3080", "nvidia"),
            ("AMD Radeon RX 6800 XT", "amd"),
            ("Intel HD Graphics 630", "intel"),
            ("Apple M1 GPU", "apple"),
            ("Unknown Graphics Card", "unknown")
        ]

        for gpu_name, expected_vendor in test_cases:
            with self.subTest(gpu_name=gpu_name):
                vendor = self.gpu_test._detect_vendor(gpu_name)
                self.assertEqual(vendor, expected_vendor)

    def test_gpu_compatibility_test(self):
        """测试GPU兼容性检测"""
        result = self.gpu_test.test_gpu_compatibility()

        self.assertEqual(result.test_case.name, "GPU Hardware Compatibility")
        self.assertEqual(result.test_case.category, "hardware")
        self.assertIn(result.result, [TestResult.PASSED, TestResult.FAILED, TestResult.ERROR])

        if result.result in [TestResult.PASSED, TestResult.FAILED]:
            self.assertIn('gpu_count', result.details)
            self.assertIn('compatibility_results', result.details)
            self.assertIn('overall_compatibility', result.details)
            self.assertGreater(result.details['gpu_count'], 0)

    def test_assess_gpu_compatibility(self):
        """测试GPU兼容性评估"""
        test_cases = [
            ({"vendor": "apple"}, CompatibilityLevel.EXCELLENT),
            ({"vendor": "nvidia"}, CompatibilityLevel.EXCELLENT),
            ({"vendor": "amd"}, CompatibilityLevel.GOOD),
            ({"vendor": "intel"}, CompatibilityLevel.FAIR),
            ({"vendor": "unknown"}, CompatibilityLevel.UNSUPPORTED)
        ]

        for gpu_info, expected_level in test_cases:
            with self.subTest(vendor=gpu_info["vendor"]):
                level = self.gpu_test._assess_gpu_compatibility(gpu_info)
                self.assertEqual(level, expected_level)


class TestOSCompatibilityTest(unittest.TestCase):
    """操作系统兼容性测试"""

    def setUp(self):
        self.os_test = OSCompatibilityTest()

    def test_get_system_info(self):
        """测试获取系统信息"""
        system_info = self.os_test.get_system_info()

        self.assertIsNotNone(system_info.os_name)
        self.assertIsNotNone(system_info.os_version)
        self.assertIsNotNone(system_info.architecture)
        self.assertIsNotNone(system_info.python_version)
        self.assertIsNotNone(system_info.platform_info)
        self.assertIsNotNone(system_info.cpu_info)
        self.assertIsNotNone(system_info.memory_info)
        self.assertIsInstance(system_info.gpu_info, list)
        self.assertIsInstance(system_info.browser_info, dict)

    def test_os_compatibility_test(self):
        """测试操作系统兼容性检测"""
        result = self.os_test.test_os_compatibility()

        self.assertEqual(result.test_case.name, "Operating System Compatibility")
        self.assertEqual(result.test_case.category, "system")
        self.assertIn(result.result, [TestResult.PASSED, TestResult.FAILED, TestResult.ERROR])

        if result.result in [TestResult.PASSED, TestResult.FAILED]:
            self.assertIn('os_name', result.details)
            self.assertIn('compatibility', result.details)
            self.assertIn('supported_features', result.details)

    def test_assess_os_compatibility(self):
        """测试操作系统兼容性评估"""
        # 创建模拟系统信息
        from core.webgpu.compatibility_testing import SystemInfo

        test_cases = [
            ("Windows", CompatibilityLevel.EXCELLENT),
            ("Darwin", CompatibilityLevel.EXCELLENT),
            ("Linux", CompatibilityLevel.GOOD),
            ("FreeBSD", CompatibilityLevel.UNSUPPORTED)
        ]

        for os_name, expected_level in test_cases:
            with self.subTest(os_name=os_name):
                system_info = SystemInfo(
                    os_name=os_name,
                    os_version="Unknown",
                    architecture="x64",
                    python_version="3.8.0",
                    platform_info="Test",
                    cpu_info="Test CPU",
                    memory_info="8 GB"
                )
                level = self.os_test._assess_os_compatibility(system_info)
                self.assertEqual(level, expected_level)

    def test_get_supported_features(self):
        """测试获取支持的特性"""
        from core.webgpu.compatibility_testing import SystemInfo

        # Windows系统
        windows_info = SystemInfo(
            os_name="Windows",
            os_version="10",
            architecture="x64",
            python_version="3.8.0",
            platform_info="Windows",
            cpu_info="Intel CPU",
            memory_info="16 GB"
        )

        features = self.os_test._get_supported_features(windows_info)
        self.assertIn('basic-webgpu', features)
        self.assertIn('d3d12-backend', features)
        self.assertIn('vulkan-backend', features)


class TestWebGPUFeatureTest(unittest.TestCase):
    """WebGPU特性测试"""

    def setUp(self):
        self.feature_test = WebGPUFeatureTest()

    def test_feature_support_test(self):
        """测试WebGPU特性支持检测"""
        result = self.feature_test.test_feature_support()

        self.assertEqual(result.test_case.name, "WebGPU Feature Support")
        self.assertEqual(result.test_case.category, "features")
        self.assertIn(result.result, [TestResult.PASSED, TestResult.FAILED, TestResult.ERROR])

        if result.result in [TestResult.PASSED, TestResult.FAILED]:
            self.assertIn('total_features', result.details)
            self.assertIn('supported_features', result.details)
            self.assertIn('unsupported_features', result.details)
            self.assertIn('support_ratio', result.details)

            # 验证特性列表
            total_features = result.details['total_features']
            supported_count = len(result.details['supported_features'])
            unsupported_count = len(result.details['unsupported_features'])

            self.assertEqual(total_features, supported_count + unsupported_count)
            self.assertGreaterEqual(result.details['support_ratio'], 0.0)
            self.assertLessEqual(result.details['support_ratio'], 1.0)


class TestCompatibilityTestSuite(unittest.TestCase):
    """兼容性测试套件测试"""

    def setUp(self):
        self.test_suite = CompatibilityTestSuite()

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.test_suite.browser_test)
        self.assertIsNotNone(self.test_suite.gpu_test)
        self.assertIsNotNone(self.test_suite.os_test)
        self.assertIsNotNone(self.test_suite.feature_test)
        self.assertGreater(len(self.test_suite.test_cases), 0)

    def test_run_all_tests(self):
        """测试运行所有测试"""
        report = self.test_suite.run_all_tests()

        # 验证报告结构
        self.assertIsNotNone(report.system_info)
        self.assertIsInstance(report.test_results, list)
        self.assertGreater(len(report.test_results), 0)
        self.assertIsInstance(report.overall_compatibility, CompatibilityLevel)
        self.assertIsInstance(report.recommendations, list)
        self.assertIsInstance(report.performance_score, float)
        self.assertIsInstance(report.test_summary, dict)
        self.assertGreater(report.test_duration, 0)

        # 验证测试摘要
        expected_keys = ['total', 'passed', 'failed', 'error', 'skipped']
        for key in expected_keys:
            self.assertIn(key, report.test_summary)

        # 验证测试结果数量
        total_results = len(report.test_results)
        summary_total = report.test_summary['total']
        self.assertEqual(total_results, summary_total)

    def test_calculate_overall_compatibility(self):
        """测试总体兼容性计算"""
        # 模拟测试结果
        from core.webgpu.compatibility_testing import TestCase, TestCaseResult

        # 全部通过
        self.test_suite.test_results = [
            TestCaseResult(
                test_case=TestCase("Test1", "Desc1", "func1", "cat1"),
                result=TestResult.PASSED,
                duration=1.0
            ),
            TestCaseResult(
                test_case=TestCase("Test2", "Desc2", "func2", "cat2"),
                result=TestResult.PASSED,
                duration=1.0
            )
        ]

        compatibility = self.test_suite._calculate_overall_compatibility()
        self.assertEqual(compatibility, CompatibilityLevel.EXCELLENT)

        # 部分失败
        self.test_suite.test_results[1].result = TestResult.FAILED
        compatibility = self.test_suite._calculate_overall_compatibility()
        self.assertNotEqual(compatibility, CompatibilityLevel.EXCELLENT)

    def test_calculate_performance_score(self):
        """测试性能得分计算"""
        # 模拟测试结果
        from core.webgpu.compatibility_testing import TestCase, TestCaseResult

        self.test_suite.test_results = [
            TestCaseResult(
                test_case=TestCase("Test1", "Desc1", "func1", "cat1"),
                result=TestResult.PASSED,
                duration=1.0
            )
        ]

        score = self.test_suite._calculate_performance_score()
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_save_report(self):
        """测试保存报告"""
        report = self.test_suite.run_all_tests()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            self.test_suite.save_report(report, temp_file)

            # 验证文件存在
            self.assertTrue(os.path.exists(temp_file))

            # 验证文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)

            self.assertIn('timestamp', saved_data)
            self.assertIn('system_info', saved_data)
            self.assertIn('overall_compatibility', saved_data)
            self.assertIn('test_results', saved_data)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestQuickFunctions(unittest.TestCase):
    """快捷函数测试"""

    def test_run_compatibility_test(self):
        """测试运行兼容性测试快捷函数"""
        report = run_compatibility_test()

        self.assertIsNotNone(report)
        self.assertIsInstance(report.overall_compatibility, CompatibilityLevel)
        self.assertGreater(len(report.test_results), 0)

    def test_check_webgpu_compatibility(self):
        """测试检查WebGPU兼容性快捷函数"""
        is_compatible = check_webgpu_compatibility()

        self.assertIsInstance(is_compatible, bool)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""

    def test_browser_test_error_handling(self):
        """测试浏览器测试错误处理"""
        browser_test = BrowserCompatibilityTest()

        # 模拟异常情况
        with patch.object(browser_test, 'get_browser_info', side_effect=Exception("Test error")):
            result = browser_test.test_webgpu_support()

            self.assertEqual(result.result, TestResult.ERROR)
            self.assertIn("Test error", result.message)
            self.assertIsNotNone(result.error_info)

    def test_gpu_test_error_handling(self):
        """测试GPU测试错误处理"""
        gpu_test = GPUCompatibilityTest()

        # 模拟GPU信息获取失败
        with patch.object(gpu_test, 'get_gpu_info', side_effect=Exception("GPU error")):
            result = gpu_test.test_gpu_compatibility()

            self.assertEqual(result.result, TestResult.ERROR)
            self.assertIn("GPU error", result.message)

    def test_os_test_error_handling(self):
        """测试操作系统测试错误处理"""
        os_test = OSCompatibilityTest()

        # 模拟系统信息获取失败
        with patch.object(os_test, 'get_system_info', side_effect=Exception("OS error")):
            result = os_test.test_os_compatibility()

            self.assertEqual(result.result, TestResult.ERROR)
            self.assertIn("OS error", result.message)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_full_compatibility_check(self):
        """测试完整兼容性检查流程"""
        # 运行完整的兼容性测试
        report = run_compatibility_test()

        # 验证系统信息
        self.assertIsNotNone(report.system_info)
        self.assertEqual(report.system_info.os_name, platform.system())

        # 验证测试结果
        self.assertGreater(len(report.test_results), 0)

        # 验证每个测试类别都有结果
        categories = {result.test_case.category for result in report.test_results}
        expected_categories = {'browser', 'hardware', 'system', 'features'}
        self.assertTrue(expected_categories.issubset(categories))

        # 验证建议不为空
        self.assertGreater(len(report.recommendations), 0)

        # 验证性能得分在合理范围内
        self.assertGreaterEqual(report.performance_score, 0.0)
        self.assertLessEqual(report.performance_score, 100.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
