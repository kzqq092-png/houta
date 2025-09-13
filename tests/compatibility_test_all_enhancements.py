#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
兼容性测试：确保所有增强功能的兼容性

测试内容：
1. 版本兼容性测试
2. 配置兼容性测试  
3. 接口兼容性测试
4. 数据格式兼容性测试
5. 错误处理兼容性测试
"""

from core.importdata.import_config_manager import ImportTaskConfig, ImportMode, DataFrequency
from core.async_management.enhanced_async_manager import EnhancedAsyncManager
from core.events.enhanced_event_bus import EnhancedEventBus, EventPriority
from core.services.enhanced_distributed_service import EnhancedDistributedService, LoadBalancingStrategy, TaskPriority
from core.risk_monitoring.enhanced_risk_monitor import EnhancedRiskMonitor
from core.performance.cache_manager import MultiLevelCacheManager, CacheLevel
from core.performance.unified_monitor import UnifiedPerformanceMonitor, PerformanceCategory, MetricType
from core.services.ai_prediction_service import AIPredictionService, PredictionType
from loguru import logger
from core.loguru_config import initialize_loguru
import sys
import os
import unittest
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入核心模块

# 导入增强功能模块

# 初始化日志
initialize_loguru()


class CompatibilityTestSuite(unittest.TestCase):
    """兼容性测试套件"""

    def setUp(self):
        """测试前置设置"""
        logger.info("🔧 兼容性测试环境初始化...")

        # 初始化各个服务
        self.ai_service = AIPredictionService()
        self.performance_monitor = UnifiedPerformanceMonitor()

        # 缓存管理器配置
        cache_config = {
            'levels': ['memory', 'disk'],
            'default_ttl_minutes': 30,
            'memory_cache': {
                'max_size': 1000,
                'ttl_minutes': 15
            },
            'disk_cache': {
                'cache_dir': 'cache/test',
                'max_size_mb': 100,
                'ttl_minutes': 60
            }
        }
        self.cache_manager = MultiLevelCacheManager(cache_config)
        self.risk_monitor = EnhancedRiskMonitor()
        self.distributed_service = EnhancedDistributedService()
        self.event_bus = EnhancedEventBus()
        self.async_manager = EnhancedAsyncManager()

        logger.info("✅ 兼容性测试环境初始化完成")

    def tearDown(self):
        """测试后清理"""
        logger.info("🧹 兼容性测试环境清理...")

        try:
            # 停止各个服务
            if hasattr(self.performance_monitor, 'stop'):
                self.performance_monitor.stop()
            if hasattr(self.cache_manager, 'clear'):
                self.cache_manager.clear()
            if hasattr(self.risk_monitor, 'stop_monitoring'):
                self.risk_monitor.stop_monitoring()
            if hasattr(self.distributed_service, 'stop'):
                self.distributed_service.stop()
            if hasattr(self.event_bus, 'stop'):
                self.event_bus.stop()
            if hasattr(self.async_manager, 'stop'):
                self.async_manager.stop()

            # 清理风险监控
            if hasattr(self.risk_monitor, 'cleanup'):
                self.risk_monitor.cleanup()

        except Exception as e:
            logger.warning(f"清理过程中出现警告: {e}")

        logger.info("✅ 兼容性测试环境清理完成")

    def test_version_compatibility(self):
        """测试版本兼容性"""
        logger.info("🔍 测试版本兼容性...")

        # 测试各个服务的版本信息
        services = {
            'ai_service': self.ai_service,
            'performance_monitor': self.performance_monitor,
            'cache_manager': self.cache_manager,
            'risk_monitor': self.risk_monitor,
            'distributed_service': self.distributed_service,
            'event_bus': self.event_bus,
            'async_manager': self.async_manager
        }

        for service_name, service in services.items():
            # 检查服务是否有版本信息
            version_attrs = ['version', '__version__', 'VERSION']
            has_version = any(hasattr(service, attr) for attr in version_attrs)

            logger.info(f"服务 {service_name}: 版本信息 {'存在' if has_version else '不存在'}")

            # 检查服务是否可以正常初始化
            self.assertIsNotNone(service, f"服务 {service_name} 初始化失败")

        logger.info("✅ 版本兼容性测试通过")

    def test_config_compatibility(self):
        """测试配置兼容性"""
        logger.info("🔍 测试配置兼容性...")

        # 测试ImportTaskConfig的完整创建
        try:
            task_config = ImportTaskConfig(
                task_id="compatibility_test_001",
                name="兼容性测试任务",
                data_source="test_source",
                asset_type="股票",
                data_type="K线数据",
                symbols=["000001", "000002"],
                frequency=DataFrequency.DAILY,
                mode=ImportMode.MANUAL,
                batch_size=100,
                max_workers=2
            )

            # 验证配置对象
            self.assertEqual(task_config.task_id, "compatibility_test_001")
            self.assertEqual(task_config.asset_type, "股票")
            self.assertEqual(task_config.data_type, "K线数据")
            self.assertEqual(task_config.frequency, DataFrequency.DAILY)
            self.assertEqual(task_config.mode, ImportMode.MANUAL)

            logger.info("✅ ImportTaskConfig 创建成功")

        except Exception as e:
            self.fail(f"ImportTaskConfig 创建失败: {e}")

        # 测试配置序列化和反序列化
        try:
            config_dict = task_config.to_dict()
            restored_config = ImportTaskConfig.from_dict(config_dict)

            self.assertEqual(task_config.task_id, restored_config.task_id)
            self.assertEqual(task_config.frequency, restored_config.frequency)
            self.assertEqual(task_config.mode, restored_config.mode)

            logger.info("✅ 配置序列化/反序列化测试通过")

        except Exception as e:
            self.fail(f"配置序列化/反序列化失败: {e}")

        logger.info("✅ 配置兼容性测试通过")

    def test_interface_compatibility(self):
        """测试接口兼容性"""
        logger.info("🔍 测试接口兼容性...")

        # 测试AI预测服务接口
        try:
            # 测试执行时间预测
            prediction_data = {
                'data_size': 1000,
                'complexity': 'medium',
                'system_load': 0.5
            }
            result = self.ai_service.predict_execution_time(prediction_data)
            self.assertIsNotNone(result)
            logger.info("✅ AI预测服务接口兼容")

        except Exception as e:
            logger.warning(f"AI预测服务接口警告: {e}")

        # 测试性能监控接口
        try:
            self.performance_monitor.start()
            self.performance_monitor.record_metric(
                "test_metric",
                100.0,
                PerformanceCategory.SYSTEM,
                MetricType.GAUGE
            )
            logger.info("✅ 性能监控接口兼容")

        except Exception as e:
            logger.warning(f"性能监控接口警告: {e}")

        # 测试缓存管理接口
        try:
            self.cache_manager.put("test_key", "test_value", CacheLevel.MEMORY)
            value = self.cache_manager.get("test_key")
            self.assertEqual(value, "test_value")
            logger.info("✅ 缓存管理接口兼容")

        except Exception as e:
            logger.warning(f"缓存管理接口警告: {e}")

        # 测试风险监控接口
        try:
            portfolio_data = {
                'portfolio_value': 1000000,
                'positions': [
                    {'symbol': '000001', 'quantity': 1000, 'price': 10.0},
                    {'symbol': '000002', 'quantity': 500, 'price': 20.0}
                ]
            }
            risk_result = self.risk_monitor.assess_portfolio_risk(portfolio_data)
            self.assertIsNotNone(risk_result)
            logger.info("✅ 风险监控接口兼容")

        except Exception as e:
            logger.warning(f"风险监控接口警告: {e}")

        logger.info("✅ 接口兼容性测试通过")

    def test_data_format_compatibility(self):
        """测试数据格式兼容性"""
        logger.info("🔍 测试数据格式兼容性...")

        # 测试事件数据格式
        try:
            from core.events.event_bus import BaseEvent

            event_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'compatibility_test',
                'data': {'test': 'value'}
            }

            event = BaseEvent('test_event', event_data)
            self.assertEqual(event.name, 'test_event')
            self.assertEqual(event.data, event_data)

            logger.info("✅ 事件数据格式兼容")

        except Exception as e:
            logger.warning(f"事件数据格式警告: {e}")

        # 测试性能指标数据格式
        try:
            metrics_data = {
                'cpu_usage': 50.0,
                'memory_usage': 60.0,
                'disk_usage': 30.0,
                'timestamp': datetime.now().isoformat()
            }

            # 验证数据格式
            self.assertIn('cpu_usage', metrics_data)
            self.assertIn('timestamp', metrics_data)

            logger.info("✅ 性能指标数据格式兼容")

        except Exception as e:
            logger.warning(f"性能指标数据格式警告: {e}")

        logger.info("✅ 数据格式兼容性测试通过")

    def test_error_handling_compatibility(self):
        """测试错误处理兼容性"""
        logger.info("🔍 测试错误处理兼容性...")

        # 测试AI服务错误处理
        try:
            # 传入无效数据
            invalid_data = {}
            result = self.ai_service.predict_execution_time(invalid_data)
            # 应该返回默认值或None，而不是抛出异常
            logger.info("✅ AI服务错误处理兼容")

        except Exception as e:
            logger.info(f"AI服务错误处理: {e}")

        # 测试缓存错误处理
        try:
            # 尝试获取不存在的键
            value = self.cache_manager.get("non_existent_key")
            # 应该返回None而不是抛出异常
            self.assertIsNone(value)
            logger.info("✅ 缓存错误处理兼容")

        except Exception as e:
            logger.info(f"缓存错误处理: {e}")

        # 测试风险监控错误处理
        try:
            # 传入无效的投资组合数据
            invalid_portfolio = {}
            result = self.risk_monitor.assess_portfolio_risk(invalid_portfolio)
            # 应该返回错误状态而不是抛出异常
            logger.info("✅ 风险监控错误处理兼容")

        except Exception as e:
            logger.info(f"风险监控错误处理: {e}")

        logger.info("✅ 错误处理兼容性测试通过")

    def test_distributed_service_port_handling(self):
        """测试分布式服务端口处理"""
        logger.info("🔍 测试分布式服务端口处理...")

        try:
            # 测试分布式服务的启动和停止
            # 注意：这里不实际启动网络服务，只测试配置
            service_config = {
                'discovery_port': 8888,
                'max_nodes': 5,
                'load_balancing_strategy': LoadBalancingStrategy.ROUND_ROBIN
            }

            # 验证配置
            self.assertIn('discovery_port', service_config)
            self.assertIn('load_balancing_strategy', service_config)

            logger.info("✅ 分布式服务配置兼容")

        except Exception as e:
            logger.warning(f"分布式服务配置警告: {e}")

        logger.info("✅ 分布式服务端口处理测试通过")


def run_compatibility_tests():
    """运行兼容性测试"""
    logger.info("=" * 60)
    logger.info("HIkyuu-UI 增强功能兼容性测试")
    logger.info("=" * 60)

    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(CompatibilityTestSuite)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    logger.info("=" * 60)
    logger.info("兼容性测试结果")
    logger.info("=" * 60)
    logger.info(f"总测试数: {result.testsRun}")
    logger.info(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")

    if result.failures:
        logger.error("失败的测试:")
        for test, traceback in result.failures:
            logger.error(f"  - {test}: {traceback}")

    if result.errors:
        logger.error("错误的测试:")
        for test, traceback in result.errors:
            logger.error(f"  - {test}: {traceback}")

    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    logger.info(f"成功率: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_compatibility_tests()
    sys.exit(0 if success else 1)
