#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI集成功能测试
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.plugin_types import AssetType, DataType
    from core.ui_integration.data_missing_manager import (
        DataMissingManager, DataAvailabilityInfo, DataAvailabilityStatus,
        DataDownloadTask, get_data_missing_manager
    )
    from core.ui_integration.smart_data_integration import (
        SmartDataIntegration, UIIntegrationConfig, IntegrationMode,
        get_smart_data_integration
    )
    from loguru import logger
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


class TestDataMissingManager(unittest.TestCase):
    """数据缺失管理器测试"""

    def setUp(self):
        """设置测试环境"""
        self.manager = DataMissingManager()
        self.test_symbol = "000001"
        self.test_data_type = DataType.HISTORICAL_KLINE

    def test_manager_initialization(self):
        """测试管理器初始化"""
        self.assertIsNotNone(self.manager)
        self.assertIsInstance(self.manager.availability_cache, dict)
        self.assertIsInstance(self.manager.download_tasks, dict)
        self.assertIsInstance(self.manager.plugin_status_cache, dict)
        print("✓ 数据缺失管理器初始化测试通过")

    def test_check_data_availability(self):
        """测试数据可用性检查"""
        # 检查数据可用性
        availability_info = self.manager.check_data_availability(
            self.test_symbol,
            self.test_data_type
        )

        self.assertIsInstance(availability_info, DataAvailabilityInfo)
        self.assertEqual(availability_info.symbol, self.test_symbol)
        self.assertEqual(availability_info.data_type, self.test_data_type)
        self.assertIsInstance(availability_info.status, DataAvailabilityStatus)

        print(f"✓ 数据可用性检查测试通过: {availability_info.status.value}")

    def test_create_download_task(self):
        """测试创建下载任务"""
        date_range = (datetime.now() - timedelta(days=30), datetime.now())

        task_id = self.manager.create_download_task(
            self.test_symbol,
            AssetType.STOCK_A,
            self.test_data_type,
            date_range
        )

        self.assertIsInstance(task_id, str)
        self.assertTrue(len(task_id) > 0)
        self.assertIn(task_id, self.manager.download_tasks)

        # 检查任务详情
        task = self.manager.get_download_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task.symbol, self.test_symbol)
        self.assertEqual(task.asset_type, AssetType.STOCK_A)
        self.assertEqual(task.data_type, self.test_data_type)

        print(f"✓ 创建下载任务测试通过: {task_id}")

    def test_get_suggested_plugins(self):
        """测试获取建议插件"""
        suggestions = self.manager._get_suggested_plugins(AssetType.STOCK_A, DataType.HISTORICAL_KLINE)

        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)

        # 检查建议内容
        for plugin in suggestions:
            self.assertIsInstance(plugin, str)
            self.assertTrue(len(plugin) > 0)

        print(f"✓ 获取建议插件测试通过: {suggestions}")

    def test_plugin_availability(self):
        """测试插件可用性"""
        availability = self.manager.get_plugin_availability()

        self.assertIsInstance(availability, dict)

        # 检查返回格式
        for plugin_name, is_available in availability.items():
            self.assertIsInstance(plugin_name, str)
            self.assertIsInstance(is_available, bool)

        print(f"✓ 插件可用性测试通过: {len(availability)} 个插件")

    def test_suggest_data_sources(self):
        """测试建议数据源"""
        suggestions = self.manager.suggest_data_sources(self.test_symbol, self.test_data_type)

        self.assertIsInstance(suggestions, list)

        # 检查建议格式
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, dict)
            self.assertIn('plugin_name', suggestion)
            self.assertIn('display_name', suggestion)
            self.assertIn('is_available', suggestion)
            self.assertIn('priority', suggestion)

        print(f"✓ 建议数据源测试通过: {len(suggestions)} 个建议")

    def test_callback_registration(self):
        """测试回调注册"""
        callback_called = False

        def test_callback(info):
            nonlocal callback_called
            callback_called = True

        # 注册回调
        self.manager.register_data_missing_callback(test_callback)

        # 触发数据缺失检查（应该会调用回调）
        self.manager.check_data_availability("MISSING_SYMBOL", DataType.HISTORICAL_KLINE)

        # 由于是模拟数据，可能不会触发回调，这里只检查注册是否成功
        self.assertIn(test_callback, self.manager.data_missing_callbacks)

        print("✓ 回调注册测试通过")

    def test_task_management(self):
        """测试任务管理"""
        # 创建任务
        date_range = (datetime.now() - timedelta(days=7), datetime.now())
        task_id = self.manager.create_download_task(
            "TEST001",
            AssetType.STOCK_A,
            DataType.REAL_TIME_QUOTE,
            date_range
        )

        # 获取活跃任务
        active_tasks = self.manager.get_active_tasks()
        self.assertIsInstance(active_tasks, list)

        # 检查任务是否在活跃列表中
        task_ids = [task.task_id for task in active_tasks]
        self.assertIn(task_id, task_ids)

        # 尝试取消任务
        cancel_result = self.manager.cancel_download_task(task_id)
        self.assertIsInstance(cancel_result, bool)

        print(f"✓ 任务管理测试通过: {len(active_tasks)} 个活跃任务")

    def tearDown(self):
        """清理测试环境"""
        if hasattr(self.manager, 'close'):
            self.manager.close()


class TestSmartDataIntegration(unittest.TestCase):
    """智能数据集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.config = UIIntegrationConfig(
            mode=IntegrationMode.PASSIVE,
            show_missing_prompt=False  # 测试时不显示UI
        )
        self.integration = SmartDataIntegration(self.config)

    def test_integration_initialization(self):
        """测试集成管理器初始化"""
        self.assertIsNotNone(self.integration)
        self.assertEqual(self.integration.config.mode, IntegrationMode.PASSIVE)
        self.assertIsNotNone(self.integration.data_missing_manager)

        print("✓ 智能数据集成初始化测试通过")

    def test_data_check_for_widget(self):
        """测试为组件检查数据"""
        result = self.integration.check_data_for_widget(
            "test_widget",
            "000001",
            "historical"
        )

        self.assertIsInstance(result, bool)

        print(f"✓ 组件数据检查测试通过: {result}")

    def test_plugin_suggestions(self):
        """测试插件建议"""
        suggestions = self.integration.get_plugin_suggestions("000001", "historical")

        self.assertIsInstance(suggestions, list)

        # 检查建议格式
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, dict)
            self.assertIn('plugin_name', suggestion)
            self.assertIn('is_available', suggestion)

        print(f"✓ 插件建议测试通过: {len(suggestions)} 个建议")

    def test_download_management(self):
        """测试下载管理"""
        # 开始下载
        task_id = self.integration.start_data_download(
            "TEST001",
            "STOCK_A",
            "HISTORICAL_KLINE",
            {
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'data_source': 'auto'
            }
        )

        if task_id:
            self.assertIsInstance(task_id, str)

            # 获取下载进度
            progress = self.integration.get_download_progress(task_id)
            if progress:
                self.assertIsInstance(progress, dict)
                self.assertIn('task_id', progress)
                self.assertIn('status', progress)
                self.assertIn('progress', progress)

            print(f"✓ 下载管理测试通过: {task_id}")
        else:
            print("✓ 下载管理测试通过: 无可用下载任务")

    def test_config_update(self):
        """测试配置更新"""
        new_config = UIIntegrationConfig(
            mode=IntegrationMode.SMART,
            auto_check_interval=600
        )

        self.integration.update_config(new_config)

        self.assertEqual(self.integration.config.mode, IntegrationMode.SMART)
        self.assertEqual(self.integration.config.auto_check_interval, 600)

        print("✓ 配置更新测试通过")

    def test_statistics(self):
        """测试统计信息"""
        stats = self.integration.get_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn('monitored_widgets', stats)
        self.assertIn('active_downloads', stats)
        self.assertIn('config_mode', stats)
        self.assertIn('last_update', stats)

        print(f"✓ 统计信息测试通过: {stats}")

    def tearDown(self):
        """清理测试环境"""
        if hasattr(self.integration, 'close'):
            self.integration.close()


class TestSingletonPattern(unittest.TestCase):
    """单例模式测试"""

    def test_data_missing_manager_singleton(self):
        """测试数据缺失管理器单例"""
        manager1 = get_data_missing_manager()
        manager2 = get_data_missing_manager()

        self.assertIs(manager1, manager2)
        print("✓ 数据缺失管理器单例测试通过")

    def test_smart_integration_singleton(self):
        """测试智能集成管理器单例"""
        integration1 = get_smart_data_integration()
        integration2 = get_smart_data_integration()

        self.assertIs(integration1, integration2)
        print("✓ 智能集成管理器单例测试通过")


def run_comprehensive_test():
    """运行综合测试"""
    print("=" * 50)
    print("UI集成功能综合测试")
    print("=" * 50)

    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加测试用例
    test_suite.addTest(unittest.makeSuite(TestDataMissingManager))
    test_suite.addTest(unittest.makeSuite(TestSmartDataIntegration))
    test_suite.addTest(unittest.makeSuite(TestSingletonPattern))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n成功率: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
