from loguru import logger
#!/usr/bin/env python3
"""
HIkyuu-UI插件系统综合自动化测试

基于调用链分析的全面测试，包括：
1. 插件生命周期测试
2. UI交互测试
3. 数据源插件测试
4. 错误处理测试
5. 性能监控测试

作者: FactorWeave-Quant 开发团队
"""

import os
import sys
import unittest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入被测试的模块
try:
    from core.plugin_manager import PluginManager, PluginInfo, PluginStatus
    from core.plugin_config_manager import PluginConfigManager, PluginPermission
    from core.services.plugin_database_service import PluginDatabaseService
    from db.models.plugin_models import PluginDatabaseManager, PluginRecord, PluginType
    from plugins.plugin_interface import IPlugin, PluginMetadata, PluginType as InterfacePluginType
    from plugins.plugin_market import PluginMarket
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.info(f"警告: 部分模块导入失败: {e}")
    IMPORTS_AVAILABLE = False

# 设置日志 - 使用纯Loguru
# # Loguru配置在core.loguru_config中统一管理  # 已移除，使用Loguru
# logger = logger  # Loguru已在文件开头导入


class MockPlugin(IPlugin):
    """模拟插件用于测试"""

    def __init__(self, name: str = "test_plugin"):
        self.name = name
        self.initialized = False
        self.cleaned_up = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version="1.0.0",
            description="测试插件",
            author="测试作者",
            email="test@example.com",
            website="https://test.com",
            license="MIT",
            plugin_type=InterfacePluginType.ANALYSIS,
            category=None,
            dependencies=[],
            min_hikyuu_version="2.0.0",
            max_hikyuu_version="3.0.0",
            tags=["test"]
        )

    def initialize(self, context) -> bool:
        self.initialized = True
        return True

    def enable(self) -> None:
        """启用插件"""
        self.initialized = True

    def disable(self) -> None:
        """禁用插件"""
        self.initialized = False
        self.cleanup()

    def cleanup(self) -> None:
        self.cleaned_up = True


class TestPluginLifecycle(unittest.TestCase):
    """插件生命周期测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin_dir = os.path.join(self.temp_dir, "plugins")
        os.makedirs(self.plugin_dir, exist_ok=True)

        # 创建临时数据库
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_plugin_discovery_chain(self):
        """测试插件发现调用链"""
        logger.info("测试插件发现调用链")

        # 创建测试插件文件
        plugin_path = os.path.join(self.plugin_dir, "test_plugin")
        os.makedirs(plugin_path, exist_ok=True)

        # 创建plugin.json
        plugin_json = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "测试插件",
            "author": "测试作者",
            "plugin_type": "analysis",
            "entry_point": "test_plugin.TestPlugin"
        }

        with open(os.path.join(plugin_path, "plugin.json"), "w") as f:
            import json
            json.dump(plugin_json, f)

        # 创建插件Python文件
        plugin_code = '''
from plugins.plugin_interface import IPlugin, PluginMetadata, PluginType, PluginCategory

class TestPlugin(IPlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="测试插件",
            author="测试作者",
            email="test@example.com",
            website="",
            license="MIT",
            plugin_type=PluginType.ANALYSIS,
            category=PluginCategory.COMMUNITY,
            dependencies=[],
            min_hikyuu_version="2.0.0",
            max_hikyuu_version="3.0.0",
            tags=["test"]
        )
    
    def initialize(self, context):
        return True
    
    def cleanup(self):
        pass
'''

        with open(os.path.join(plugin_path, "test_plugin.py"), "w") as f:
            f.write(plugin_code)

        # 测试插件管理器发现插件
        try:
            plugin_manager = PluginManager(plugin_dir=self.plugin_dir)

            # 发现插件
            discovered_plugins = plugin_manager.discover_enhanced_plugins()

            # 验证插件被发现
            self.assertGreater(len(discovered_plugins), 0, "应该发现至少一个插件")

            # 验证插件信息
            test_plugin = next((p for p in discovered_plugins if p.name == "test_plugin"), None)
            self.assertIsNotNone(test_plugin, "应该找到test_plugin")
            self.assertEqual(test_plugin.name, "test_plugin")
            self.assertEqual(test_plugin.version, "1.0.0")

            logger.info(" 插件发现调用链测试通过")

        except Exception as e:
            logger.error(f"插件发现调用链测试失败: {e}")
            self.fail(f"插件发现调用链测试失败: {e}")

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_plugin_loading_chain(self):
        """测试插件加载调用链"""
        logger.info("测试插件加载调用链")

        try:
            # 创建插件管理器
            plugin_manager = PluginManager(plugin_dir=self.plugin_dir)

            # 创建模拟插件
            mock_plugin = MockPlugin("test_load_plugin")
            plugin_info = PluginInfo(
                name="test_load_plugin",
                version="1.0.0",
                description="测试加载插件",
                author="测试作者",
                path=self.plugin_dir,
                status=PluginStatus.UNLOADED,
                config={},
                dependencies=[]
            )

            # 手动添加插件信息
            plugin_manager.loaded_plugins["test_load_plugin"] = plugin_info
            plugin_manager.plugin_instances["test_load_plugin"] = mock_plugin
            plugin_manager.enhanced_plugins["test_load_plugin"] = plugin_info

            # 测试插件启用
            result = plugin_manager.enable_plugin("test_load_plugin")
            self.assertTrue(result, "插件启用应该成功")

            # 验证插件状态 - 给一点时间让状态同步
            import time
            time.sleep(0.1)

            self.assertEqual(plugin_info.status, PluginStatus.ENABLED)
            self.assertTrue(mock_plugin.initialized, "插件应该被初始化")

            # 测试插件禁用
            result = plugin_manager.disable_plugin("test_load_plugin")
            self.assertTrue(result, "插件禁用应该成功")

            # 验证插件状态
            self.assertEqual(plugin_info.status, PluginStatus.DISABLED)
            self.assertTrue(mock_plugin.cleaned_up, "插件应该被清理")

            logger.info(" 插件加载调用链测试通过")

        except Exception as e:
            logger.error(f"插件加载调用链测试失败: {e}")
            self.fail(f"插件加载调用链测试失败: {e}")


class TestPluginUIInteractions(unittest.TestCase):
    """插件UI交互测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_plugin_config_chain(self):
        """测试插件配置调用链"""
        logger.info("测试插件配置调用链")

        try:
            # 创建配置管理器
            config_manager = PluginConfigManager(config_dir=self.temp_dir)

            # 测试创建插件配置
            plugin_config = config_manager.create_plugin_config(
                plugin_name="test_config_plugin",
                version="1.0.0",
                security_policy_name="default"
            )

            self.assertIsNotNone(plugin_config, "应该创建插件配置")
            self.assertEqual(plugin_config.name, "test_config_plugin")
            self.assertTrue(plugin_config.enabled, "插件应该默认启用")

            # 测试更新配置
            test_config_data = {"api_key": "test_key", "timeout": 30}
            result = config_manager.update_plugin_config("test_config_plugin", test_config_data)
            self.assertTrue(result, "配置更新应该成功")

            # 验证配置更新
            updated_config = config_manager.get_plugin_config("test_config_plugin")
            self.assertIsNotNone(updated_config, "应该获取到更新后的配置")
            self.assertEqual(updated_config.config_data["api_key"], "test_key")
            self.assertEqual(updated_config.config_data["timeout"], 30)

            # 测试权限检查
            has_read_permission = config_manager.check_permission(
                "test_config_plugin", PluginPermission.READ_DATA
            )
            self.assertTrue(has_read_permission, "应该有读取数据权限")

            has_system_permission = config_manager.check_permission(
                "test_config_plugin", PluginPermission.SYSTEM_COMMANDS
            )
            self.assertFalse(has_system_permission, "不应该有系统命令权限")

            logger.info(" 插件配置调用链测试通过")

        except Exception as e:
            logger.error(f"插件配置调用链测试失败: {e}")
            self.fail(f"插件配置调用链测试失败: {e}")


class TestPluginDatabaseService(unittest.TestCase):
    """插件数据库服务测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_plugin.db")

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_database_service_chain(self):
        """测试数据库服务调用链"""
        logger.info("测试数据库服务调用链")

        try:
            # 创建数据库服务
            db_service = PluginDatabaseService(db_path=self.db_path)

            # 测试插件注册
            plugin_metadata = {
                "name": "test_db_plugin",
                "version": "1.0.0",
                "description": "测试数据库插件",
                "author": "测试作者",
                "plugin_type": "analysis",
                "path": "/test/path"
            }

            result = db_service.register_plugin_from_metadata("test_db_plugin", plugin_metadata)
            self.assertTrue(result, "插件注册应该成功")

            # 测试状态更新
            from db.models.plugin_models import PluginStatus as DBPluginStatus
            result = db_service.update_plugin_status(
                "test_db_plugin",
                DBPluginStatus.ENABLED,
                "测试启用"
            )
            self.assertTrue(result, "状态更新应该成功")

            # 验证状态获取
            status = db_service.get_plugin_status("test_db_plugin")
            self.assertEqual(status, DBPluginStatus.ENABLED, "状态应该是ENABLED")

            # 测试获取所有插件
            all_plugins = db_service.get_all_plugins()
            self.assertGreater(len(all_plugins), 0, "应该有至少一个插件")

            # 验证插件信息
            test_plugin = next((p for p in all_plugins if p["name"] == "test_db_plugin"), None)
            self.assertIsNotNone(test_plugin, "应该找到测试插件")
            self.assertEqual(test_plugin["status"], "enabled")

            # 测试状态统计
            stats = db_service.get_status_statistics()
            self.assertIn("enabled", stats, "统计中应该包含enabled状态")
            self.assertGreater(stats["enabled"], 0, "enabled状态的插件数量应该大于0")

            logger.info(" 数据库服务调用链测试通过")

        except Exception as e:
            logger.error(f"数据库服务调用链测试失败: {e}")
            self.fail(f"数据库服务调用链测试失败: {e}")


class TestPluginMarketChain(unittest.TestCase):
    """插件市场调用链测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.temp_dir, "plugins")
        self.cache_dir = os.path.join(self.temp_dir, "cache")
        os.makedirs(self.plugins_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    @patch('requests.Session.get')
    def test_plugin_market_search_chain(self, mock_get):
        """测试插件市场搜索调用链"""
        logger.info("测试插件市场搜索调用链")

        try:
            # 模拟API响应
            mock_response = Mock()
            mock_response.json.return_value = {
                "plugins": [
                    {
                        "metadata": {
                            "name": "test_market_plugin",
                            "version": "1.0.0",
                            "description": "测试市场插件",
                            "author": "测试作者",
                            "email": "test@example.com",
                            "website": "",
                            "license": "MIT",
                            "plugin_type": "analysis",
                            "category": "community",
                            "dependencies": [],
                            "min_hikyuu_version": "2.0.0",
                            "max_hikyuu_version": "3.0.0",
                            "tags": ["test"]
                        },
                        "download_url": "https://example.com/plugin.zip",
                        "file_size": 1024,
                        "download_count": 100,
                        "rating": 4.5,
                        "rating_count": 10,
                        "last_updated": "2024-01-01T00:00:00Z",
                        "screenshots": [],
                        "readme": "测试插件说明",
                        "changelog": "初始版本",
                        "verified": True,
                        "featured": False
                    }
                ],
                "total": 1
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # 创建插件市场
            plugin_market = PluginMarket(self.plugins_dir, self.cache_dir)

            # 测试搜索插件
            plugins, total = plugin_market.search_plugins(query="test")

            self.assertEqual(total, 1, "应该找到1个插件")
            self.assertEqual(len(plugins), 1, "插件列表应该有1个元素")

            plugin = plugins[0]
            self.assertEqual(plugin.metadata.name, "test_market_plugin")
            self.assertEqual(plugin.rating, 4.5)
            self.assertEqual(plugin.download_count, 100)

            # 验证API调用
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            self.assertIn("search", call_args[0][0])  # URL应该包含search

            logger.info(" 插件市场搜索调用链测试通过")

        except Exception as e:
            logger.error(f"插件市场搜索调用链测试失败: {e}")
            self.fail(f"插件市场搜索调用链测试失败: {e}")


class TestErrorHandlingChain(unittest.TestCase):
    """错误处理调用链测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_plugin_error_handling_chain(self):
        """测试插件错误处理调用链"""
        logger.info("测试插件错误处理调用链")

        try:
            # 创建会抛出异常的模拟插件
            class ErrorPlugin(IPlugin):
                @property
                def metadata(self):
                    return PluginMetadata(
                        name="error_plugin",
                        version="1.0.0",
                        description="错误插件",
                        author="测试作者",
                        email="test@example.com",
                        website="",
                        license="MIT",
                        plugin_type=InterfacePluginType.ANALYSIS,
                        category=None,
                        dependencies=[],
                        min_hikyuu_version="2.0.0",
                        max_hikyuu_version="3.0.0",
                        tags=["test"]
                    )

                def initialize(self, context):
                    raise Exception("初始化失败")

                def enable(self):
                    raise Exception("启用失败")

                def cleanup(self):
                    pass

            # 创建插件管理器
            plugin_manager = PluginManager(plugin_dir=self.temp_dir)

            # 创建错误插件信息
            error_plugin = ErrorPlugin()
            plugin_info = PluginInfo(
                name="error_plugin",
                version="1.0.0",
                description="错误插件",
                author="测试作者",
                path=self.temp_dir,
                status=PluginStatus.UNLOADED,
                config={},
                dependencies=[]
            )

            # 手动添加插件
            plugin_manager.loaded_plugins["error_plugin"] = plugin_info
            plugin_manager.plugin_instances["error_plugin"] = error_plugin
            plugin_manager.enhanced_plugins["error_plugin"] = plugin_info

            # 测试启用错误插件
            result = plugin_manager.enable_plugin("error_plugin")
            self.assertFalse(result, "错误插件启用应该失败")

            # 给一点时间让状态同步
            import time
            time.sleep(0.1)

            # 验证插件状态变为ERROR
            logger.info(f"错误插件状态: {plugin_info.status}")
            # 检查enhanced_plugins中的状态，因为这是enable_plugin直接设置的
            enhanced_plugin_status = plugin_manager.enhanced_plugins["error_plugin"].status
            logger.info(f"enhanced_plugins中的错误插件状态: {enhanced_plugin_status}")
            self.assertEqual(enhanced_plugin_status, PluginStatus.ERROR)

            # 测试错误恢复 - 禁用错误插件
            result = plugin_manager.disable_plugin("error_plugin")
            self.assertTrue(result, "错误插件禁用应该成功")

            logger.info(" 插件错误处理调用链测试通过")

        except Exception as e:
            logger.error(f"插件错误处理调用链测试失败: {e}")
            self.fail(f"插件错误处理调用链测试失败: {e}")


class TestPerformanceMonitoring(unittest.TestCase):
    """性能监控测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_perf.db")

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(IMPORTS_AVAILABLE, "所需模块未导入")
    def test_performance_monitoring_chain(self):
        """测试性能监控调用链"""
        logger.info("测试性能监控调用链")

        try:
            # 创建数据库管理器
            db_manager = PluginDatabaseManager(self.db_path)

            # 注册测试插件
            plugin_record = PluginRecord(
                name="perf_test_plugin",
                display_name="性能测试插件",
                version="1.0.0",
                plugin_type=PluginType.ANALYSIS.value,
                status="enabled",
                description="用于性能测试的插件",
                author="测试作者"
            )

            plugin_id = db_manager.register_plugin(plugin_record)
            self.assertIsNotNone(plugin_id, "插件注册应该成功")

            # 记录性能指标
            result = db_manager.record_plugin_performance(
                plugin_name="perf_test_plugin",
                metric_name="load_time",
                metric_value=0.5,
                metric_unit="seconds",
                additional_data={"memory_usage": "10MB"}
            )
            self.assertTrue(result, "性能指标记录应该成功")

            # 获取性能指标
            metrics = db_manager.get_plugin_performance_metrics(
                plugin_name="perf_test_plugin",
                metric_name="load_time",
                limit=10
            )

            self.assertGreater(len(metrics), 0, "应该有性能指标记录")

            metric = metrics[0]
            self.assertEqual(metric["metric_name"], "load_time")
            self.assertEqual(metric["metric_value"], 0.5)
            self.assertEqual(metric["metric_unit"], "seconds")

            logger.info(" 性能监控调用链测试通过")

        except Exception as e:
            logger.error(f"性能监控调用链测试失败: {e}")
            self.fail(f"性能监控调用链测试失败: {e}")


class PluginSystemTestSuite:
    """插件系统测试套件"""

    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.end_time = None

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info(" 开始HIkyuu-UI插件系统全面自动化测试")
        logger.info("=" * 80)

        self.start_time = time.time()

        # 创建测试套件
        test_suite = unittest.TestSuite()

        # 添加测试类
        test_classes = [
            TestPluginLifecycle,
            TestPluginUIInteractions,
            TestPluginDatabaseService,
            TestPluginMarketChain,
            TestErrorHandlingChain,
            TestPerformanceMonitoring
        ]

        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            test_suite.addTests(tests)

        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(test_suite)

        self.end_time = time.time()

        # 生成测试报告
        return self._generate_report(result)

    def _generate_report(self, result: unittest.TestResult) -> Dict[str, Any]:
        """生成测试报告"""
        total_time = self.end_time - self.start_time

        report = {
            "total_tests": result.testsRun,
            "passed_tests": result.testsRun - len(result.failures) - len(result.errors),
            "failed_tests": len(result.failures),
            "error_tests": len(result.errors),
            "skipped_tests": len(result.skipped) if hasattr(result, 'skipped') else 0,
            "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            "total_time": total_time,
            "failures": [str(failure[1]) for failure in result.failures],
            "errors": [str(error[1]) for error in result.errors]
        }

        # 打印报告
        logger.info("\n" + "=" * 80)
        logger.info("HIkyuu-UI插件系统测试报告")
        logger.info("=" * 80)
        logger.info(f"测试总数: {report['total_tests']}")
        logger.info(f"通过数量: {report['passed_tests']}")
        logger.info(f"失败数量: {report['failed_tests']}")
        logger.info(f"错误数量: {report['error_tests']}")
        logger.info(f"跳过数量: {report['skipped_tests']}")
        logger.info(f"成功率: {report['success_rate']:.1f}%")
        logger.info(f"总耗时: {report['total_time']:.2f} 秒")

        if report['failures']:
            logger.info("\n失败的测试:")
            for i, failure in enumerate(report['failures'], 1):
                logger.info(f"{i}. {failure}")

        if report['errors']:
            logger.info("\n错误的测试:")
            for i, error in enumerate(report['errors'], 1):
                logger.info(f"{i}. {error}")

        return report


def main():
    """主函数"""
    if not IMPORTS_AVAILABLE:
        logger.info(" 无法导入必要的模块，跳过测试")
        return False

    # 运行测试套件
    test_suite = PluginSystemTestSuite()
    report = test_suite.run_all_tests()

    # 返回测试是否全部通过
    return report['failed_tests'] == 0 and report['error_tests'] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
