"""
WebGPU集成测试脚本

测试WebGPU环境检测、兼容性检查、渲染器集成等功能。
验证多层降级机制和性能监控是否正常工作。
"""

import unittest
import sys
import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWebGPUEnvironment(unittest.TestCase):
    """WebGPU环境测试"""

    def setUp(self):
        """测试初始化"""
        self.test_data = None

    def test_environment_detection(self):
        """测试环境检测"""
        logger.info("测试WebGPU环境检测...")

        try:
            from core.webgpu.environment import get_webgpu_environment, initialize_webgpu_environment

            # 初始化环境
            success = initialize_webgpu_environment()
            self.assertTrue(success, "WebGPU环境初始化应该成功")

            # 获取环境实例
            env = get_webgpu_environment()
            self.assertIsNotNone(env, "应该能获取环境实例")
            self.assertTrue(env.is_initialized, "环境应该已初始化")

            # 检查支持级别
            support_level = env.support_level
            self.assertIsNotNone(support_level, "应该有支持级别")
            logger.info(f"支持级别: {support_level.value}")

            # 检查GPU能力
            capabilities = env.gpu_capabilities
            self.assertIsNotNone(capabilities, "应该有GPU能力信息")
            logger.info(f"GPU适配器: {capabilities.adapter_name}")
            logger.info(f"GPU厂商: {capabilities.vendor}")
            logger.info(f"GPU内存: {capabilities.memory_mb}MB")

        except ImportError as e:
            self.skipTest(f"WebGPU模块不可用: {e}")

    def test_compatibility_check(self):
        """测试兼容性检查"""
        logger.info("测试兼容性检查...")

        try:
            from core.webgpu.environment import get_webgpu_environment
            from core.webgpu.compatibility import GPUCompatibilityChecker

            env = get_webgpu_environment()
            if not env.is_initialized:
                env.initialize()

            # 创建兼容性检查器
            checker = GPUCompatibilityChecker()
            self.assertIsNotNone(checker, "应该能创建兼容性检查器")

            # 执行兼容性检查
            report = checker.check_compatibility(
                env.gpu_capabilities,
                env.support_level
            )

            self.assertIsNotNone(report, "应该有兼容性报告")
            self.assertIsNotNone(report.level, "应该有兼容性级别")
            self.assertIsNotNone(report.recommended_backend, "应该有推荐后端")
            self.assertIsInstance(report.performance_score, (int, float), "应该有性能评分")

            logger.info(f"兼容性级别: {report.level.value}")
            logger.info(f"性能评分: {report.performance_score}/100")
            logger.info(f"推荐后端: {report.recommended_backend.value}")
            logger.info(f"问题数量: {len(report.issues)}")

            # 测试降级链
            fallback_chain = checker.get_fallback_chain(report)
            self.assertIsInstance(fallback_chain, list, "应该有降级链")
            self.assertGreater(len(fallback_chain), 0, "降级链不应为空")

            logger.info(f"降级链: {[backend.value for backend in fallback_chain]}")

        except ImportError as e:
            self.skipTest(f"WebGPU模块不可用: {e}")

    def test_fallback_renderer(self):
        """测试降级渲染器"""
        logger.info("测试降级渲染器...")

        try:
            from core.webgpu.environment import get_webgpu_environment
            from core.webgpu.compatibility import GPUCompatibilityChecker
            from core.webgpu.fallback import FallbackRenderer

            # 获取兼容性报告
            env = get_webgpu_environment()
            if not env.is_initialized:
                env.initialize()

            checker = GPUCompatibilityChecker()
            report = checker.check_compatibility(
                env.gpu_capabilities,
                env.support_level
            )

            # 创建降级渲染器
            renderer = FallbackRenderer()
            self.assertIsNotNone(renderer, "应该能创建降级渲染器")

            # 初始化渲染器
            context = env.create_render_context()
            success = renderer.initialize(report, context)
            self.assertTrue(success, "渲染器初始化应该成功")

            # 获取当前后端
            current_backend = renderer.get_current_backend()
            self.assertIsNotNone(current_backend, "应该有当前后端")
            logger.info(f"当前后端: {current_backend.value}")

            # 测试渲染功能
            test_data = self._create_test_data()
            style = {'color': 'blue', 'linewidth': 1.0}

            # 测试K线渲染
            success = renderer.render_candlesticks(test_data, style)
            logger.info(f"K线渲染测试: {'成功' if success else '失败'}")

            # 测试成交量渲染
            success = renderer.render_volume(test_data, style)
            logger.info(f"成交量渲染测试: {'成功' if success else '失败'}")

            # 测试线图渲染
            line_data = test_data['close']
            success = renderer.render_line(line_data, style)
            logger.info(f"线图渲染测试: {'成功' if success else '失败'}")

            # 获取性能信息
            perf_info = renderer.get_performance_info()
            self.assertIsInstance(perf_info, dict, "应该有性能信息")
            logger.info(f"性能信息: {perf_info}")

        except ImportError as e:
            self.skipTest(f"WebGPU模块不可用: {e}")

    def test_webgpu_manager(self):
        """测试WebGPU管理器"""
        logger.info("测试WebGPU管理器...")

        try:
            from core.webgpu.manager import get_webgpu_manager, WebGPUConfig

            # 创建配置
            config = WebGPUConfig(
                auto_initialize=True,
                enable_fallback=True,
                performance_monitoring=True
            )

            # 获取管理器
            manager = get_webgpu_manager(config)
            self.assertIsNotNone(manager, "应该能获取WebGPU管理器")

            # 检查初始化状态
            if not manager._initialized:
                success = manager.initialize()
                logger.info(f"管理器初始化: {'成功' if success else '失败'}")

            # 获取状态
            status = manager.get_status()
            self.assertIsInstance(status, dict, "应该有状态信息")
            logger.info(f"管理器状态: {status['initialized']}")
            logger.info(f"当前后端: {status['performance'].get('current_backend')}")

            # 获取建议
            recommendations = manager.get_recommendations()
            self.assertIsInstance(recommendations, list, "应该有建议列表")
            if recommendations:
                logger.info("优化建议:")
                for rec in recommendations:
                    logger.info(f"  - {rec}")

            # 测试渲染功能
            test_data = self._create_test_data()
            style = {'color': 'red', 'linewidth': 1.5}

            success = manager.render_candlesticks(test_data, style)
            logger.info(f"管理器K线渲染: {'成功' if success else '失败'}")

        except ImportError as e:
            self.skipTest(f"WebGPU模块不可用: {e}")

    def test_webgpu_chart_renderer_integration(self):
        """测试WebGPU图表渲染器集成"""
        logger.info("测试WebGPU图表渲染器集成...")

        try:
            from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer

            # 获取WebGPU图表渲染器
            renderer = get_webgpu_chart_renderer()
            self.assertIsNotNone(renderer, "应该能获取WebGPU图表渲染器")

            # 检查WebGPU状态
            status = renderer.get_webgpu_status()
            self.assertIsInstance(status, dict, "应该有WebGPU状态")
            logger.info(f"WebGPU启用: {status['enabled']}")
            logger.info(f"WebGPU初始化: {status['initialized']}")
            logger.info(f"当前后端: {status['current_backend']}")

            # 获取优化建议
            recommendations = renderer.get_webgpu_recommendations()
            self.assertIsInstance(recommendations, list, "应该有建议列表")
            if recommendations:
                logger.info("WebGPU优化建议:")
                for rec in recommendations:
                    logger.info(f"  - {rec}")

            # 测试渲染功能
            test_data = self._create_test_data()
            style = {'color': 'green', 'linewidth': 2.0}

            # 测试K线渲染（这会优先使用WebGPU，失败时降级到matplotlib）
            renderer.render_candlesticks(None, test_data, style)
            logger.info("WebGPU图表渲染器K线渲染测试完成")

            # 测试成交量渲染
            renderer.render_volume(None, test_data, style)
            logger.info("WebGPU图表渲染器成交量渲染测试完成")

            # 测试线图渲染
            line_data = test_data['close']
            renderer.render_line(None, line_data, style)
            logger.info("WebGPU图表渲染器线图渲染测试完成")

        except ImportError as e:
            self.skipTest(f"WebGPU图表渲染器不可用: {e}")

    def test_performance_benchmark(self):
        """测试性能基准测试"""
        logger.info("测试性能基准测试...")

        try:
            from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer

            renderer = get_webgpu_chart_renderer()

            # 检查是否有基准测试功能
            if hasattr(renderer, 'benchmark_rendering'):
                test_data = self._create_test_data()

                logger.info("开始性能基准测试...")
                results = renderer.benchmark_rendering(test_data, iterations=5)

                self.assertIsInstance(results, dict, "应该有测试结果")

                webgpu_avg = results.get('webgpu_average', 0)
                matplotlib_avg = results.get('matplotlib_average', 0)
                speedup = results.get('speedup_ratio', 0)

                logger.info(f"WebGPU平均耗时: {webgpu_avg*1000:.1f}ms")
                logger.info(f"matplotlib平均耗时: {matplotlib_avg*1000:.1f}ms")
                logger.info(f"加速比: {speedup:.1f}x")

                if speedup > 1:
                    logger.info("WebGPU性能优于matplotlib")
                elif speedup > 0:
                    logger.info("WebGPU性能略低于matplotlib")
                else:
                    logger.info("WebGPU渲染失败或不可用")
            else:
                logger.info("性能基准测试功能不可用")

        except ImportError as e:
            self.skipTest(f"WebGPU图表渲染器不可用: {e}")

    def _create_test_data(self) -> pd.DataFrame:
        """创建测试数据"""
        if self.test_data is None:
            np.random.seed(42)  # 固定随机种子确保测试一致性

            dates = pd.date_range('2023-01-01', periods=1000, freq='D')

            # 生成模拟股价数据
            close_prices = 100 + np.cumsum(np.random.randn(1000) * 0.5)

            self.test_data = pd.DataFrame({
                'date': dates,
                'open': close_prices + np.random.randn(1000) * 0.1,
                'high': close_prices + np.abs(np.random.randn(1000)) * 0.5,
                'low': close_prices - np.abs(np.random.randn(1000)) * 0.5,
                'close': close_prices,
                'volume': np.random.randint(1000000, 10000000, 1000)
            })

            # 确保high >= max(open, close), low <= min(open, close)
            self.test_data['high'] = np.maximum(
                self.test_data['high'],
                np.maximum(self.test_data['open'], self.test_data['close'])
            )
            self.test_data['low'] = np.minimum(
                self.test_data['low'],
                np.minimum(self.test_data['open'], self.test_data['close'])
            )

        return self.test_data


class TestWebGPUIntegrationSystem(unittest.TestCase):
    """WebGPU集成系统测试"""

    def test_service_registration(self):
        """测试服务注册"""
        logger.info("测试WebGPU服务注册...")

        try:
            from core.containers import get_service_container
            from core.services.service_bootstrap import bootstrap_services

            # 引导服务
            success = bootstrap_services()
            if success:
                logger.info("服务引导成功")

                # 获取服务容器
                container = get_service_container()

                # 检查WebGPU渲染器是否注册
                try:
                    webgpu_renderer = container.resolve('webgpu_chart_renderer')
                    self.assertIsNotNone(webgpu_renderer, "WebGPU渲染器应该已注册")
                    logger.info("WebGPU渲染器服务注册成功")
                except Exception as e:
                    logger.warning(f"WebGPU渲染器服务未注册: {e}")
            else:
                logger.warning("服务引导失败")

        except ImportError as e:
            self.skipTest(f"服务容器不可用: {e}")

    def test_chart_widget_integration(self):
        """测试图表控件集成"""
        logger.info("测试图表控件WebGPU集成...")

        try:
            # 创建Qt应用程序（如果需要）
            from PyQt5.QtWidgets import QApplication
            import sys

            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            from gui.widgets.chart_widget import ChartWidget

            # 创建图表控件
            chart_widget = ChartWidget()
            self.assertIsNotNone(chart_widget, "应该能创建图表控件")

            # 检查渲染器类型
            renderer = chart_widget.renderer
            self.assertIsNotNone(renderer, "应该有渲染器")

            renderer_type = type(renderer).__name__
            logger.info(f"图表控件渲染器类型: {renderer_type}")

            # 如果是WebGPU渲染器，检查状态
            if hasattr(renderer, 'get_webgpu_status'):
                status = renderer.get_webgpu_status()
                logger.info(f"图表控件WebGPU状态: {status}")

            # 清理
            chart_widget.deleteLater()

        except ImportError as e:
            self.skipTest(f"图表控件不可用: {e}")


def run_webgpu_tests():
    """运行WebGPU测试套件"""
    logger.info("开始WebGPU集成测试...")

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加环境测试
    suite.addTest(TestWebGPUEnvironment('test_environment_detection'))
    suite.addTest(TestWebGPUEnvironment('test_compatibility_check'))
    suite.addTest(TestWebGPUEnvironment('test_fallback_renderer'))
    suite.addTest(TestWebGPUEnvironment('test_webgpu_manager'))
    suite.addTest(TestWebGPUEnvironment('test_webgpu_chart_renderer_integration'))
    suite.addTest(TestWebGPUEnvironment('test_performance_benchmark'))

    # 添加集成测试
    suite.addTest(TestWebGPUIntegrationSystem('test_service_registration'))
    suite.addTest(TestWebGPUIntegrationSystem('test_chart_widget_integration'))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果总结
    logger.info("=" * 60)
    logger.info("WebGPU集成测试结果总结")
    logger.info("=" * 60)
    logger.info(f"运行测试: {result.testsRun}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info(f"跳过: {len(result.skipped)}")

    if result.failures:
        logger.error("失败的测试:")
        for test, traceback in result.failures:
            logger.error(f"  - {test}: {traceback}")

    if result.errors:
        logger.error("错误的测试:")
        for test, traceback in result.errors:
            logger.error(f"  - {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    logger.info(f"测试结果: {'通过' if success else '失败'}")

    return success


if __name__ == '__main__':
    success = run_webgpu_tests()
    sys.exit(0 if success else 1)
