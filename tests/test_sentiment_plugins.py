"""
情绪数据源插件单元测试

此测试文件提供了情绪数据源插件系统的全面测试，包括：
- AkShare插件功能测试
- 情绪数据服务管理器测试
- 数据聚合和缓存机制测试
- 错误处理和回退机制测试
"""

from plugins.sentiment_data_source_interface import (
    ISentimentDataSource,
    SentimentData,
    SentimentResponse,
    BaseSentimentPlugin,
    SentimentStatus,
    TradingSignal
)
import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入被测试的模块

try:
    from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: AkShare插件不可用，跳过相关测试")

try:
    from core.services.sentiment_data_service import (
        SentimentDataService,
        SentimentDataServiceConfig
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False
    print("警告: 情绪数据服务不可用，跳过相关测试")


class TestSentimentDataStructures(unittest.TestCase):
    """测试情绪数据结构"""

    def test_sentiment_data_creation(self):
        """测试SentimentData数据结构创建"""
        now = datetime.now()
        sentiment = SentimentData(
            indicator_name="测试指标",
            value=75.5,
            status="乐观",
            change=2.3,
            signal="买入",
            suggestion="适当加仓",
            timestamp=now,
            source="测试源",
            confidence=0.85,
            color="#00AA44",
            metadata={"test": "value"}
        )

        self.assertEqual(sentiment.indicator_name, "测试指标")
        self.assertEqual(sentiment.value, 75.5)
        self.assertEqual(sentiment.status, "乐观")
        self.assertEqual(sentiment.change, 2.3)
        self.assertEqual(sentiment.signal, "买入")
        self.assertEqual(sentiment.suggestion, "适当加仓")
        self.assertEqual(sentiment.timestamp, now)
        self.assertEqual(sentiment.source, "测试源")
        self.assertEqual(sentiment.confidence, 0.85)
        self.assertEqual(sentiment.color, "#00AA44")
        self.assertEqual(sentiment.metadata["test"], "value")

    def test_sentiment_response_creation(self):
        """测试SentimentResponse数据结构创建"""
        sentiment_data = [
            SentimentData("指标1", 50.0, "中性", 0.0, "持有", "观望", datetime.now(), "测试", 0.7),
            SentimentData("指标2", 70.0, "乐观", 5.0, "买入", "加仓", datetime.now(), "测试", 0.8)
        ]

        response = SentimentResponse(
            success=True,
            data=sentiment_data,
            composite_score=0.6,
            error_message="",
            data_quality="good",
            update_time=datetime.now(),
            cache_used=False
        )

        self.assertTrue(response.success)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.composite_score, 0.6)
        self.assertEqual(response.data_quality, "good")
        self.assertFalse(response.cache_used)


class TestBaseSentimentPlugin(unittest.TestCase):
    """测试基础情绪插件"""

    def setUp(self):
        """设置测试环境"""
        from plugins.plugin_interface import PluginMetadata, PluginType, PluginCategory

        class MockSentimentPlugin(BaseSentimentPlugin):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="模拟情绪插件",
                    version="1.0.0",
                    author="测试",
                    description="用于测试的模拟插件",
                    type=PluginType.DATA_SOURCE,
                    category=PluginCategory.ANALYSIS,
                    dependencies=[]
                )

            def get_available_indicators(self) -> List[str]:
                return ["模拟指标1", "模拟指标2"]

            def validate_data_quality(self, data: List[SentimentData]) -> str:
                return "good" if len(data) > 0 else "poor"

            def _fetch_raw_sentiment_data(self) -> SentimentResponse:
                return SentimentResponse(
                    success=True,
                    data=[
                        SentimentData("模拟指标1", 60.0, "中性", 1.0, "持有", "观望", datetime.now(), "模拟", 0.8),
                        SentimentData("模拟指标2", 75.0, "乐观", 5.0, "买入", "加仓", datetime.now(), "模拟", 0.9)
                    ]
                )

        self.plugin = MockSentimentPlugin()

    def test_plugin_initialization(self):
        """测试插件初始化"""
        self.assertTrue(self.plugin.initialize())
        self.assertIsNotNone(self.plugin._cache)
        self.assertIsNone(self.plugin._last_fetch_time)

    def test_fetch_sentiment_data(self):
        """测试获取情绪数据"""
        response = self.plugin.fetch_sentiment_data()

        self.assertTrue(response.success)
        self.assertEqual(len(response.data), 2)
        self.assertGreater(response.composite_score, 0)
        self.assertEqual(response.data_quality, "good")

    def test_caching_mechanism(self):
        """测试缓存机制"""
        # 第一次调用
        response1 = self.plugin.fetch_sentiment_data()
        self.assertFalse(response1.cache_used)

        # 第二次调用（应该使用缓存）
        response2 = self.plugin.fetch_sentiment_data()
        self.assertTrue(response2.cache_used)

    def test_composite_sentiment_calculation(self):
        """测试综合情绪计算"""
        data = [
            SentimentData("VIX指数", 25.0, "恐慌", 2.0, "观望", "谨慎", datetime.now(), "测试", 0.8),
            SentimentData("消费者信心", 95.0, "乐观", 1.0, "买入", "加仓", datetime.now(), "测试", 0.7),
            SentimentData("新闻情绪", 65.0, "乐观", 3.0, "买入", "适度加仓", datetime.now(), "测试", 0.9)
        ]

        composite_score = self.plugin.calculate_composite_sentiment(data)

        self.assertIsInstance(composite_score, float)
        self.assertGreaterEqual(composite_score, -1.0)
        self.assertLessEqual(composite_score, 1.0)

    def test_sentiment_normalization(self):
        """测试情绪值标准化"""
        # 测试VIX指数标准化
        vix_low = self.plugin._normalize_sentiment_value(15.0, "VIX指数")
        vix_high = self.plugin._normalize_sentiment_value(35.0, "VIX恐慌指数")

        self.assertGreater(vix_low, 0)  # 低VIX应该是正面的
        self.assertLess(vix_high, 0)    # 高VIX应该是负面的

        # 测试消费者信心标准化
        confidence_high = self.plugin._normalize_sentiment_value(115.0, "消费者信心")
        confidence_low = self.plugin._normalize_sentiment_value(75.0, "消费者信心")

        self.assertGreater(confidence_high, confidence_low)

    def test_status_and_signal_mapping(self):
        """测试状态和信号映射"""
        # 测试极度看涨
        status = self.plugin.get_sentiment_status(0.8)
        signal = self.plugin.get_trading_signal(0.8)
        suggestion = self.plugin.get_investment_suggestion(0.8)
        color = self.plugin.get_status_color(0.8)

        self.assertEqual(status, SentimentStatus.EXTREMELY_BULLISH.value)
        self.assertEqual(signal, TradingSignal.STRONG_BUY.value)
        self.assertIn("获利", suggestion)
        self.assertEqual(color, "#FF4444")

        # 测试极度看跌
        status = self.plugin.get_sentiment_status(-0.8)
        signal = self.plugin.get_trading_signal(-0.8)
        suggestion = self.plugin.get_investment_suggestion(-0.8)
        color = self.plugin.get_status_color(-0.8)

        self.assertEqual(status, SentimentStatus.EXTREMELY_BEARISH.value)
        self.assertEqual(signal, TradingSignal.STRONG_SELL.value)
        self.assertIn("空仓", suggestion)
        self.assertEqual(color, "#00AA44")


@unittest.skipUnless(AKSHARE_AVAILABLE, "AkShare插件不可用")
class TestAkShareSentimentPlugin(unittest.TestCase):
    """测试AkShare情绪插件"""

    def setUp(self):
        """设置测试环境"""
        self.plugin = AkShareSentimentPlugin()

    def test_plugin_metadata(self):
        """测试插件元数据"""
        metadata = self.plugin.metadata

        self.assertEqual(metadata.name, "AkShare情绪数据源")
        self.assertEqual(metadata.type.value, "DATA_SOURCE")
        self.assertIn("akshare", metadata.dependencies)

    def test_available_indicators(self):
        """测试可用指标列表"""
        indicators = self.plugin.get_available_indicators()

        self.assertIsInstance(indicators, list)
        self.assertIn("新闻情绪", indicators)
        self.assertIn("微博情绪", indicators)
        self.assertIn("VIX指数", indicators)
        self.assertIn("消费者信心", indicators)
        self.assertIn("外汇情绪", indicators)

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        # 创建测试数据
        good_data = [
            SentimentData("测试", 50.0, "正常", 0.0, "持有", "观望", datetime.now(), "测试", 0.8),
            SentimentData("测试2", 60.0, "正常", 1.0, "买入", "加仓", datetime.now(), "测试", 0.9)
        ]

        poor_data = []

        self.assertEqual(self.plugin.validate_data_quality(good_data), "good")
        self.assertEqual(self.plugin.validate_data_quality(poor_data), "poor")

    def test_configuration_management(self):
        """测试配置管理"""
        default_config = self.plugin.get_default_config()

        self.assertIn("enabled", default_config)
        self.assertIn("news_sentiment_enabled", default_config)
        self.assertIn("weibo_enabled", default_config)
        self.assertIn("vix_enabled", default_config)
        self.assertIn("retry_attempts", default_config)

        # 测试配置验证
        valid_config = {"enabled": True}
        invalid_config = {}

        self.assertTrue(self.plugin.validate_config(valid_config))
        self.assertFalse(self.plugin.validate_config(invalid_config))

    @patch('akshare.index_news_sentiment_scope')
    def test_news_sentiment_fetch(self, mock_news):
        """测试新闻情绪获取（模拟）"""
        # 模拟akshare返回数据
        import pandas as pd
        mock_news.return_value = pd.DataFrame({
            'value': [65.5, 70.2, 58.9],
            'date': ['2024-01-15', '2024-01-14', '2024-01-13']
        })

        response = self.plugin._fetch_raw_sentiment_data()

        # 由于是模拟数据，我们主要验证方法调用和基本结构
        self.assertIsInstance(response, SentimentResponse)

    def test_sentiment_status_mapping(self):
        """测试情绪状态映射"""
        # 测试VIX状态映射
        low_vix_status = self.plugin._get_vix_status(12.0)
        high_vix_status = self.plugin._get_vix_status(35.0)

        self.assertIn("乐观", low_vix_status)
        self.assertIn("恐慌", high_vix_status)

        # 测试VIX信号映射
        low_vix_signal = self.plugin._get_vix_signal(12.0)
        high_vix_signal = self.plugin._get_vix_signal(35.0)

        self.assertIn("买入", low_vix_signal)
        self.assertIn("观望", high_vix_signal)


@unittest.skipUnless(SERVICE_AVAILABLE, "情绪数据服务不可用")
class TestSentimentDataService(unittest.TestCase):
    """测试情绪数据服务"""

    def setUp(self):
        """设置测试环境"""
        config = SentimentDataServiceConfig(
            cache_duration_minutes=1,
            auto_refresh_interval_minutes=5,
            max_concurrent_fetches=2,
            enable_auto_refresh=False
        )

        self.service = SentimentDataService(config=config)

        # 创建模拟插件
        self.mock_plugin = Mock(spec=ISentimentDataSource)
        self.mock_plugin.fetch_sentiment_data.return_value = SentimentResponse(
            success=True,
            data=[
                SentimentData("模拟指标", 55.0, "中性", 2.0, "持有", "观望", datetime.now(), "模拟", 0.8)
            ],
            composite_score=0.1
        )
        self.mock_plugin.get_available_indicators.return_value = ["模拟指标"]
        self.mock_plugin.validate_data_quality.return_value = "good"

    def test_service_initialization(self):
        """测试服务初始化"""
        self.assertFalse(self.service._is_initialized)
        self.assertFalse(self.service._is_running)

        # 模拟初始化
        success = self.service.initialize()

        # 由于没有插件管理器，初始化应该成功但没有插件
        self.assertTrue(success)
        self.assertTrue(self.service._is_initialized)
        self.assertTrue(self.service._is_running)

    def test_plugin_registration(self):
        """测试插件注册"""
        # 注册插件
        success = self.service.register_plugin("test_plugin", self.mock_plugin, priority=10, weight=1.0)

        self.assertTrue(success)
        self.assertIn("test_plugin", self.service._registered_plugins)
        self.assertEqual(self.service._plugin_priorities["test_plugin"], 10)
        self.assertEqual(self.service._plugin_weights["test_plugin"], 1.0)

    def test_plugin_unregistration(self):
        """测试插件注销"""
        # 先注册插件
        self.service.register_plugin("test_plugin", self.mock_plugin)

        # 注销插件
        success = self.service.unregister_plugin("test_plugin")

        self.assertTrue(success)
        self.assertNotIn("test_plugin", self.service._registered_plugins)

    def test_sentiment_data_retrieval(self):
        """测试情绪数据获取"""
        # 注册插件
        self.service.register_plugin("test_plugin", self.mock_plugin)

        # 获取数据
        response = self.service.get_sentiment_data()

        self.assertTrue(response.success)
        self.assertGreater(len(response.data), 0)
        self.assertIsInstance(response.composite_score, float)

    def test_caching_behavior(self):
        """测试缓存行为"""
        # 注册插件
        self.service.register_plugin("test_plugin", self.mock_plugin)

        # 第一次获取数据
        response1 = self.service.get_sentiment_data()
        self.assertFalse(response1.cache_used)

        # 第二次获取数据（应该使用缓存）
        response2 = self.service.get_sentiment_data()
        self.assertTrue(response2.cache_used)

    def test_service_status(self):
        """测试服务状态"""
        status = self.service.get_service_status()

        self.assertIn('is_initialized', status)
        self.assertIn('is_running', status)
        self.assertIn('registered_plugins', status)
        self.assertIn('cache_valid', status)

    def test_plugin_status(self):
        """测试插件状态"""
        # 注册插件
        self.service.register_plugin("test_plugin", self.mock_plugin)

        status = self.service.get_plugin_status("test_plugin")

        self.assertEqual(status["status"], "registered")
        self.assertEqual(status["priority"], 100)  # 默认优先级
        self.assertEqual(status["weight"], 1.0)    # 默认权重
        self.assertIn("available_indicators", status)

    def test_error_handling(self):
        """测试错误处理"""
        # 创建会抛出异常的模拟插件
        error_plugin = Mock(spec=ISentimentDataSource)
        error_plugin.fetch_sentiment_data.side_effect = Exception("测试错误")

        # 注册错误插件
        self.service.register_plugin("error_plugin", error_plugin)

        # 获取数据应该处理错误
        response = self.service.get_sentiment_data()

        # 应该返回错误响应
        self.assertFalse(response.success)
        self.assertIn("错误", response.error_message)

    def test_multi_plugin_aggregation(self):
        """测试多插件数据聚合"""
        # 创建第二个模拟插件
        plugin2 = Mock(spec=ISentimentDataSource)
        plugin2.fetch_sentiment_data.return_value = SentimentResponse(
            success=True,
            data=[
                SentimentData("模拟指标2", 75.0, "乐观", 5.0, "买入", "加仓", datetime.now(), "模拟2", 0.9)
            ],
            composite_score=0.5
        )
        plugin2.get_available_indicators.return_value = ["模拟指标2"]
        plugin2.validate_data_quality.return_value = "excellent"

        # 注册两个插件
        self.service.register_plugin("plugin1", self.mock_plugin, weight=0.6)
        self.service.register_plugin("plugin2", plugin2, weight=0.4)

        # 获取聚合数据
        response = self.service.get_sentiment_data()

        self.assertTrue(response.success)
        self.assertEqual(len(response.data), 2)  # 应该有两个数据源的数据

        # 综合评分应该是加权平均
        expected_score = (0.1 * 0.6 + 0.5 * 0.4) / (0.6 + 0.4)
        self.assertAlmostEqual(response.composite_score, expected_score, places=2)


class TestSentimentIntegration(unittest.TestCase):
    """测试情绪分析系统集成"""

    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        if not (AKSHARE_AVAILABLE and SERVICE_AVAILABLE):
            self.skipTest("需要AkShare插件和情绪数据服务")

        # 创建服务
        config = SentimentDataServiceConfig(enable_auto_refresh=False)
        service = SentimentDataService(config=config)

        # 创建并注册AkShare插件
        akshare_plugin = AkShareSentimentPlugin()
        service.register_plugin("akshare", akshare_plugin)

        # 初始化服务
        service.initialize()

        # 获取数据
        response = service.get_sentiment_data()

        # 验证响应结构
        self.assertIsInstance(response, SentimentResponse)
        self.assertIsInstance(response.success, bool)
        self.assertIsInstance(response.data, list)
        self.assertIsInstance(response.composite_score, float)

        # 清理
        service.cleanup()


def run_automated_tests():
    """运行自动化测试套件"""
    print("🚀 开始运行情绪分析插件自动化测试...")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    test_classes = [
        TestSentimentDataStructures,
        TestBaseSentimentPlugin,
    ]

    if AKSHARE_AVAILABLE:
        test_classes.append(TestAkShareSentimentPlugin)

    if SERVICE_AVAILABLE:
        test_classes.append(TestSentimentDataService)

    if AKSHARE_AVAILABLE and SERVICE_AVAILABLE:
        test_classes.append(TestSentimentIntegration)

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")

    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2] if chr(10) in traceback else traceback}")

    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n✅ 测试成功率: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    # 运行自动化测试
    success = run_automated_tests()

    if success:
        print("\n🎉 所有测试通过！情绪分析插件系统验证成功。")
        exit(0)
    else:
        print("\n❌ 部分测试失败，请检查上述错误信息。")
        exit(1)
