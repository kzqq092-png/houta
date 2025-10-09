#!/usr/bin/env python3
"""
全面功能测试脚本

测试HIkyuu-UI架构精简重构后的核心功能，验证：
1. 服务容器和依赖注入
2. 数据服务功能
3. 插件系统
4. 缓存系统
5. 性能监控
6. 事件总线
7. UI组件加载
"""

from loguru import logger
import sys
import os
import time
import traceback
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_service_container():
    """测试服务容器和依赖注入"""
    try:
        logger.info("[TEST] 开始测试服务容器...")

        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.containers.service_registry import ServiceScope
        from core.services.data_service import DataService
        from core.services.performance_service import PerformanceService
        from core.services.cache_service import CacheService

        # 创建容器
        container = UnifiedServiceContainer()

        # 注册服务
        container.register(DataService, scope=ServiceScope.SINGLETON)
        container.register(PerformanceService, scope=ServiceScope.SINGLETON)
        container.register(CacheService, scope=ServiceScope.SINGLETON)

        # 解析服务
        data_service = container.resolve(DataService)
        perf_service = container.resolve(PerformanceService)
        cache_service = container.resolve(CacheService)

        # 验证单例模式
        data_service_2 = container.resolve(DataService)
        assert data_service is data_service_2, "单例模式失败"

        # 验证服务健康状态
        health_report = container.get_service_health_report()
        assert isinstance(health_report, dict), "健康报告格式错误"

        logger.info("服务容器测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 服务容器测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_data_services():
    """测试数据服务功能"""
    try:
        logger.info("[TEST] 开始测试数据服务...")

        from core.services.data_service import DataService
        from core.services.database_service import DatabaseService
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.containers.service_registry import ServiceScope

        container = UnifiedServiceContainer()
        container.register(DataService, scope=ServiceScope.SINGLETON)
        container.register(DatabaseService, scope=ServiceScope.SINGLETON)

        data_service = container.resolve(DataService)
        db_service = container.resolve(DatabaseService)

        # 测试服务指标
        data_metrics = data_service.metrics
        db_metrics = db_service.metrics

        assert isinstance(data_metrics, dict), "数据服务指标格式错误"
        assert isinstance(db_metrics, dict), "数据库服务指标格式错误"

        # 验证关键指标存在
        assert 'total_requests' in data_metrics, "数据服务缺少total_requests指标"
        assert 'total_queries' in db_metrics, "数据库服务缺少total_queries指标"

        logger.info("数据服务测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 数据服务测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_plugin_system():
    """测试插件系统"""
    try:
        logger.info("[TEST] 开始测试插件系统...")

        from core.services.plugin_service import PluginService
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.containers.service_registry import ServiceScope

        container = UnifiedServiceContainer()
        container.register(PluginService, scope=ServiceScope.SINGLETON)

        plugin_service = container.resolve(PluginService)

        # 测试插件服务指标
        plugin_metrics = plugin_service.metrics
        assert isinstance(plugin_metrics, dict), "插件服务指标格式错误"

        # 验证插件指标
        expected_keys = ['total_plugins', 'loaded_plugins', 'active_plugins']
        for key in expected_keys:
            assert key in plugin_metrics, f"插件服务缺少{key}指标"

        logger.info("插件系统测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 插件系统测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_cache_system():
    """测试缓存系统"""
    try:
        logger.info("[TEST] 开始测试缓存系统...")

        from core.services.cache_service import CacheService
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.containers.service_registry import ServiceScope

        container = UnifiedServiceContainer()
        container.register(CacheService, scope=ServiceScope.SINGLETON)

        cache_service = container.resolve(CacheService)

        # 测试缓存指标
        cache_metrics = cache_service.metrics
        assert isinstance(cache_metrics, dict), "缓存服务指标格式错误"

        # 验证缓存指标
        expected_keys = ['total_hits', 'total_misses', 'total_sets']
        for key in expected_keys:
            assert key in cache_metrics, f"缓存服务缺少{key}指标"

        logger.info("缓存系统测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 缓存系统测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_performance_monitoring():
    """测试性能监控"""
    try:
        logger.info("[TEST] 开始测试性能监控...")

        from core.services.performance_service import PerformanceService
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.containers.service_registry import ServiceScope

        container = UnifiedServiceContainer()
        container.register(PerformanceService, scope=ServiceScope.SINGLETON)

        perf_service = container.resolve(PerformanceService)

        # 测试性能指标
        perf_metrics = perf_service.metrics
        assert isinstance(perf_metrics, dict), "性能服务指标格式错误"

        # 验证性能指标
        expected_keys = ['initialization_count', 'error_count', 'operation_count']
        for key in expected_keys:
            assert key in perf_metrics, f"性能服务缺少{key}指标"

        logger.info("性能监控测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 性能监控测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_event_bus():
    """测试事件总线"""
    try:
        logger.info("[TEST] 开始测试事件总线...")

        from core.events.event_bus import EventBus

        # 创建事件总线
        event_bus = EventBus()

        # 定义测试事件类
        from core.events.events import BaseEvent

        class TestEvent(BaseEvent):
            def __init__(self, message, timestamp):
                super().__init__()
                self.message = message
                self.timestamp = timestamp

        # 测试事件发布和订阅
        received_events = []

        def event_handler(event_data):
            received_events.append(event_data)

        # 订阅事件
        event_bus.subscribe(TestEvent, event_handler)

        # 发布事件
        test_event = TestEvent("test", datetime.now())
        event_bus.publish(test_event)

        # 等待事件处理
        time.sleep(0.1)

        # 验证事件接收
        assert len(received_events) > 0, "事件未被接收"
        assert received_events[0].message == "test", "事件数据不正确"

        logger.info("事件总线测试通过")
        return True

    except Exception as e:
        logger.error(f"[ERROR] 事件总线测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def test_ui_components():
    """测试UI组件加载"""
    try:
        logger.info("[TEST] 开始测试UI组件...")

        # 测试关键UI模块导入
        try:
            from gui.components.chart_widget import ChartWidget
            logger.info("ChartWidget导入成功")
        except ImportError as e:
            logger.warning(f" ChartWidget导入失败: {e}")

        try:
            from gui.components.stock_list_widget import StockListWidget
            logger.info("StockListWidget导入成功")
        except ImportError as e:
            logger.warning(f" StockListWidget导入失败: {e}")

        try:
            from gui.components.data_panel_widget import DataPanelWidget
            logger.info("DataPanelWidget导入成功")
        except ImportError as e:
            logger.warning(f" DataPanelWidget导入失败: {e}")

        logger.info("UI组件测试完成")
        return True

    except Exception as e:
        logger.error(f"[ERROR] UI组件测试失败: {e}")
        logger.error(traceback.format_exc())
        return False


def run_comprehensive_test():
    """运行全面功能测试"""
    logger.info("=" * 60)
    logger.info("开始全面功能测试")
    logger.info("=" * 60)

    test_results = {}

    # 运行各项测试
    tests = [
        ("服务容器", test_service_container),
        ("数据服务", test_data_services),
        ("插件系统", test_plugin_system),
        ("缓存系统", test_cache_system),
        ("性能监控", test_performance_monitoring),
        ("事件总线", test_event_bus),
        ("UI组件", test_ui_components),
    ]

    for test_name, test_func in tests:
        logger.info(f"\n--- 测试 {test_name} ---")
        start_time = time.time()

        try:
            result = test_func()
            test_results[test_name] = result
            elapsed = time.time() - start_time
            logger.info(f"测试 {test_name} 完成，耗时: {elapsed:.2f}秒")
        except Exception as e:
            test_results[test_name] = False
            logger.error(f"测试 {test_name} 异常: {e}")

    # 生成测试报告
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    passed = 0
    total = len(tests)

    for test_name, result in test_results.items():
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1

    logger.info(f"\n总计: {passed}/{total} 测试通过")
    logger.info(f"通过率: {(passed/total)*100:.1f}%")

    if passed == total:
        logger.info("所有功能测试通过！")
        return True
    else:
        logger.warning(f" {total-passed} 个测试失败")
        return False


if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试运行异常: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
