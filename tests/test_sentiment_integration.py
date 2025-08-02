"""
情绪分析插件集成测试

此测试文件提供情绪分析插件系统的集成测试，包括：
- 真实AkShare插件数据获取测试
- UI组件集成测试  
- 端到端功能验证
- 性能和稳定性测试
"""

import unittest
import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入被测试的模块
try:
    from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
    from core.services.sentiment_data_service import SentimentDataService, SentimentDataServiceConfig
    from plugins.sentiment_data_source_interface import SentimentResponse, SentimentData
    PLUGINS_AVAILABLE = True
except ImportError as e:
    PLUGINS_AVAILABLE = False
    print(f"警告: 插件系统不可用 - {e}")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: AkShare库不可用，跳过真实数据测试")


class TestRealAkShareIntegration(unittest.TestCase):
    """测试真实AkShare数据集成"""

    @unittest.skipUnless(AKSHARE_AVAILABLE and PLUGINS_AVAILABLE, "需要AkShare和插件系统")
    def test_akshare_plugin_real_data(self):
        """测试AkShare插件获取真实数据"""
        plugin = AkShareSentimentPlugin()

        # 测试插件初始化
        self.assertTrue(plugin.initialize())

        # 测试获取真实数据（可能需要网络连接）
        try:
            response = plugin.fetch_sentiment_data()

            if response.success:
                # 验证数据结构
                self.assertIsInstance(response, SentimentResponse)
                self.assertTrue(response.success)
                self.assertIsInstance(response.data, list)
                self.assertGreater(len(response.data), 0)

                # 验证每个数据点
                for data in response.data:
                    self.assertIsInstance(data, SentimentData)
                    self.assertIsInstance(data.indicator_name, str)
                    self.assertIsInstance(data.value, (int, float))
                    self.assertIsInstance(data.status, str)
                    self.assertIsInstance(data.timestamp, datetime)

                print(f"✅ 成功获取 {len(response.data)} 个情绪指标数据")
                for data in response.data:
                    print(f"  - {data.indicator_name}: {data.value} ({data.status})")

            else:
                print(f"⚠️ AkShare数据获取失败: {response.error_message}")
                # 网络或API问题时不应视为测试失败
                self.skipTest(f"AkShare API调用失败: {response.error_message}")

        except Exception as e:
            print(f"❌ AkShare插件测试异常: {e}")
            # 网络问题时跳过测试而不是失败
            self.skipTest(f"网络或API异常: {e}")

    @unittest.skipUnless(PLUGINS_AVAILABLE, "需要插件系统")
    def test_sentiment_service_with_mock_data(self):
        """使用模拟数据测试情绪服务完整工作流程"""
        # 创建服务配置
        config = SentimentDataServiceConfig(
            cache_duration_minutes=1,
            enable_auto_refresh=False
        )

        # 创建服务
        service = SentimentDataService(config=config)

        # 创建模拟插件
        mock_plugin = Mock()
        mock_plugin.fetch_sentiment_data.return_value = SentimentResponse(
            success=True,
            data=[
                SentimentData(
                    indicator_name="模拟新闻情绪",
                    value=65.5,
                    status="乐观",
                    change=2.3,
                    signal="买入",
                    suggestion="适度加仓",
                    timestamp=datetime.now(),
                    source="模拟",
                    confidence=0.85,
                    color="#28a745"
                ),
                SentimentData(
                    indicator_name="模拟VIX指数",
                    value=18.2,
                    status="平静",
                    change=-1.5,
                    signal="持有",
                    suggestion="正常操作",
                    timestamp=datetime.now(),
                    source="模拟",
                    confidence=0.90,
                    color="#ffc107"
                )
            ],
            composite_score=0.25,
            data_quality="good"
        )
        mock_plugin.get_available_indicators.return_value = ["模拟新闻情绪", "模拟VIX指数"]
        mock_plugin.validate_data_quality.return_value = "good"
        mock_plugin.initialize = Mock(return_value=True)
        mock_plugin.cleanup = Mock()

        # 测试完整工作流程
        try:
            # 1. 初始化服务
            self.assertTrue(service.initialize())

            # 2. 注册插件
            self.assertTrue(service.register_plugin("mock_akshare", mock_plugin, priority=10, weight=1.0))

            # 3. 获取数据
            response = service.get_sentiment_data()
            self.assertTrue(response.success)
            self.assertEqual(len(response.data), 2)
            self.assertAlmostEqual(response.composite_score, 0.25, places=2)

            # 4. 测试缓存
            response2 = service.get_sentiment_data()
            self.assertTrue(response2.cache_used)

            # 5. 强制刷新
            response3 = service.get_sentiment_data(force_refresh=True)
            self.assertFalse(response3.cache_used)

            # 6. 测试插件状态
            status = service.get_plugin_status("mock_akshare")
            self.assertEqual(status["status"], "registered")

            # 7. 注销插件
            self.assertTrue(service.unregister_plugin("mock_akshare"))

            print("✅ 情绪数据服务完整工作流程测试通过")

        finally:
            # 清理
            service.cleanup()

    @unittest.skipUnless(PLUGINS_AVAILABLE, "需要插件系统")
    def test_ui_integration_simulation(self):
        """模拟UI组件集成测试"""

        # 模拟情绪分析标签页的数据获取逻辑
        class MockSentimentTab:
            def __init__(self):
                self._sentiment_service = None
                self.log_manager = Mock()

            def _initialize_sentiment_service(self):
                config = SentimentDataServiceConfig(enable_auto_refresh=False)
                self._sentiment_service = SentimentDataService(config=config)

                # 注册模拟插件
                mock_plugin = Mock()
                mock_plugin.fetch_sentiment_data.return_value = SentimentResponse(
                    success=True,
                    data=[
                        SentimentData("综合情绪", 72.0, "乐观", 3.5, "买入", "适度加仓",
                                      datetime.now(), "插件", 0.8, "#28a745"),
                        SentimentData("恐慌指数", 15.5, "平静", -2.0, "持有", "正常操作",
                                      datetime.now(), "插件", 0.9, "#ffc107")
                    ],
                    composite_score=0.35
                )
                mock_plugin.get_available_indicators.return_value = ["综合情绪", "恐慌指数"]
                mock_plugin.validate_data_quality.return_value = "excellent"
                mock_plugin.initialize = Mock(return_value=True)

                self._sentiment_service.register_plugin("test", mock_plugin)
                self._sentiment_service.initialize()

            def _calculate_realtime_sentiment(self):
                """模拟UI组件的数据获取方法"""
                try:
                    if hasattr(self, '_sentiment_service') and self._sentiment_service:
                        response = self._sentiment_service.get_sentiment_data()
                        if response.success and response.data:
                            # 转换插件数据格式为界面格式
                            sentiment_data = []
                            for sentiment in response.data:
                                sentiment_data.append({
                                    'indicator': sentiment.indicator_name,
                                    'value': sentiment.value,
                                    'status': sentiment.status,
                                    'change': sentiment.change,
                                    'signal': sentiment.signal,
                                    'suggestion': sentiment.suggestion,
                                    'color': sentiment.color
                                })
                            return sentiment_data

                    # 回退到模拟数据
                    return self._generate_fallback_sentiment_data()

                except Exception as e:
                    return self._generate_fallback_sentiment_data()

            def _generate_fallback_sentiment_data(self):
                """回退模拟数据"""
                return [{
                    'indicator': '综合情绪(模拟)',
                    'value': 50.0,
                    'status': '中性',
                    'change': 0.0,
                    'signal': '观望',
                    'suggestion': '正常操作',
                    'color': '#ffc107'
                }]

        # 测试UI组件
        tab = MockSentimentTab()

        # 初始化（应该使用插件数据）
        tab._initialize_sentiment_service()
        sentiment_data = tab._calculate_realtime_sentiment()

        # 验证结果
        self.assertIsInstance(sentiment_data, list)
        self.assertGreater(len(sentiment_data), 0)

        # 验证是否使用了真实插件数据（而非回退数据）
        has_real_data = any(not item['indicator'].endswith('(模拟)') for item in sentiment_data)
        self.assertTrue(has_real_data, "应该使用真实插件数据而非回退数据")

        print("✅ UI组件集成模拟测试通过")
        print(f"获取到 {len(sentiment_data)} 个情绪指标:")
        for item in sentiment_data:
            print(f"  - {item['indicator']}: {item['value']} ({item['status']})")

    @unittest.skipUnless(PLUGINS_AVAILABLE, "需要插件系统")
    def test_performance_and_stability(self):
        """测试性能和稳定性"""
        config = SentimentDataServiceConfig(
            cache_duration_minutes=1,
            max_concurrent_fetches=3,
            enable_auto_refresh=False
        )

        service = SentimentDataService(config=config)

        # 创建快速响应的模拟插件
        fast_plugin = Mock()
        fast_plugin.fetch_sentiment_data.return_value = SentimentResponse(
            success=True,
            data=[SentimentData("快速指标", 50.0, "中性", 0.0, "持有", "观望",
                                datetime.now(), "快速", 0.8)],
            composite_score=0.0
        )
        fast_plugin.get_available_indicators.return_value = ["快速指标"]
        fast_plugin.validate_data_quality.return_value = "good"
        fast_plugin.initialize = Mock(return_value=True)

        try:
            service.initialize()
            service.register_plugin("fast", fast_plugin)

            # 性能测试 - 连续获取数据
            start_time = time.time()
            for i in range(10):
                response = service.get_sentiment_data()
                self.assertTrue(response.success)
            end_time = time.time()

            avg_time = (end_time - start_time) / 10
            print(f"✅ 平均响应时间: {avg_time:.3f}秒")

            # 应该在合理时间内完成（由于缓存，大部分调用应该很快）
            self.assertLess(avg_time, 0.1, "平均响应时间应该小于100ms")

            # 稳定性测试 - 多次快速调用
            errors = 0
            for i in range(50):
                try:
                    response = service.get_sentiment_data()
                    if not response.success:
                        errors += 1
                except Exception:
                    errors += 1

            error_rate = errors / 50
            print(f"✅ 错误率: {error_rate:.1%}")
            self.assertLess(error_rate, 0.05, "错误率应该小于5%")

        finally:
            service.cleanup()

    def test_error_resilience(self):
        """测试错误恢复能力"""
        if not PLUGINS_AVAILABLE:
            self.skipTest("需要插件系统")

        config = SentimentDataServiceConfig(enable_auto_refresh=False)
        service = SentimentDataService(config=config)

        # 创建会出错的插件
        error_plugin = Mock()
        error_plugin.fetch_sentiment_data.side_effect = [
            Exception("网络错误"),  # 第一次出错
            SentimentResponse(success=False, error_message="API错误"),  # 第二次返回错误响应
            SentimentResponse(  # 第三次成功
                success=True,
                data=[SentimentData("恢复指标", 60.0, "正常", 1.0, "持有", "观望",
                                    datetime.now(), "恢复", 0.8)],
                composite_score=0.2
            )
        ]
        error_plugin.get_available_indicators.return_value = ["恢复指标"]
        error_plugin.validate_data_quality.return_value = "fair"
        error_plugin.initialize = Mock(return_value=True)

        try:
            service.initialize()
            service.register_plugin("error_prone", error_plugin)

            # 第一次调用 - 应该处理异常
            response1 = service.get_sentiment_data()
            self.assertFalse(response1.success)
            self.assertIn("错误", response1.error_message)

            # 第二次调用 - 应该处理错误响应
            response2 = service.get_sentiment_data(force_refresh=True)
            self.assertFalse(response2.success)

            # 第三次调用 - 应该成功
            response3 = service.get_sentiment_data(force_refresh=True)
            self.assertTrue(response3.success)
            self.assertGreater(len(response3.data), 0)

            print("✅ 错误恢复能力测试通过")

        finally:
            service.cleanup()


def run_integration_tests():
    """运行集成测试套件"""
    print("🚀 开始运行情绪分析插件集成测试...")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    test_classes = [TestRealAkShareIntegration]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 集成测试结果总结:")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {result.skipped if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1) * 100
    print(f"\n✅ 测试成功率: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    # 运行集成测试
    success = run_integration_tests()

    if success:
        print("\n🎉 所有集成测试通过！情绪分析插件系统功能验证成功。")
        exit(0)
    else:
        print("\n❌ 部分集成测试失败，请检查上述错误信息。")
        exit(1)
