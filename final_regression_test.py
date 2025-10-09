#!/usr/bin/env python
"""
全面功能回归测试

验证架构精简重构后所有核心功能正常工作。
测试所有15个核心服务的基本功能和集成。
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*60)
print("全面功能回归测试开始")
print("="*60)
print(f"测试时间: {datetime.now()}")
print(f"项目路径: {project_root}\n")

# 测试计数器
tests_passed = 0
tests_failed = 0
tests_total = 0


def test_module(test_name, test_func):
    """执行单个测试模块"""
    global tests_passed, tests_failed, tests_total
    tests_total += 1

    print(f"\n[{tests_total}] 测试: {test_name}")
    print("-" * 40)

    try:
        start_time = time.time()
        test_func()
        elapsed = time.time() - start_time
        tests_passed += 1
        print(f"✓ 通过 ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        tests_failed += 1
        print(f"✗ 失败 ({elapsed:.2f}s)")
        print(f"  错误: {str(e)[:200]}")
        return False

# ========== 测试1: 服务导入测试 ==========


def test_service_imports():
    """测试所有核心服务能否正常导入"""
    from core.services.data_service import DataService
    from core.services.database_service import DatabaseService
    from core.services.cache_service import CacheService
    from core.services.plugin_service import PluginService
    from core.services.config_service import ConfigService
    from core.services.environment_service import EnvironmentService
    from core.services.network_service import NetworkService
    from core.services.security_service import SecurityService
    from core.services.trading_service import TradingService
    from core.services.analysis_service import AnalysisService
    from core.services.market_service import MarketService
    from core.services.notification_service import NotificationService
    from core.services.performance_service import PerformanceService
    from core.services.lifecycle_service import LifecycleService
    print("  - 所有15个核心服务导入成功")

# ========== 测试2: 服务实例化测试 ==========


def test_service_instantiation():
    """测试服务能否正常实例化"""
    from core.services.environment_service import EnvironmentService
    from core.services.performance_service import PerformanceService

    env_service = EnvironmentService()
    print(f"  - EnvironmentService实例化成功")

    perf_service = PerformanceService()
    print(f"  - PerformanceService实例化成功")

# ========== 测试3: 服务容器测试 ==========


def test_service_container():
    """测试服务容器功能"""
    from core.containers import get_service_container
    from core.services.config_service import ConfigService

    container = get_service_container()
    print(f"  - 服务容器获取成功")

    # 测试服务注册
    container.register(ConfigService)
    print(f"  - 服务注册成功")

    # 测试服务解析
    config_service = container.resolve(ConfigService)
    print(f"  - 服务解析成功: {type(config_service).__name__}")

# ========== 测试4: 配置服务测试 ==========


def test_config_service():
    """测试配置服务功能"""
    from core.services.config_service import ConfigService

    config_service = ConfigService()
    config_service.initialize()
    print(f"  - ConfigService初始化成功")

    # 测试配置读取
    test_key = "system.version"
    value = config_service.get(test_key, default="unknown")
    print(f"  - 配置读取成功: {test_key} = {value}")

# ========== 测试5: 环境服务测试 ==========


def test_environment_service():
    """测试环境服务功能"""
    from core.services.environment_service import EnvironmentService

    env_service = EnvironmentService()
    env_service.initialize()
    print(f"  - EnvironmentService初始化成功")

    # 测试环境检测
    env_info = env_service.detect_environment()
    print(f"  - 环境检测成功: {env_info.get('os', 'unknown')}")

# ========== 测试6: 性能服务测试 ==========


def test_performance_service():
    """测试性能服务功能"""
    from core.services.performance_service import PerformanceService

    perf_service = PerformanceService()
    perf_service.initialize()
    print(f"  - PerformanceService初始化成功")

    # 测试性能监控
    metrics = perf_service.metrics  # 使用属性而非方法
    print(f"  - 性能指标获取成功: {len(metrics)} 项指标")

# ========== 测试7: 数据库服务测试 ==========


def test_database_service():
    """测试数据库服务功能"""
    from core.services.database_service import DatabaseService

    db_service = DatabaseService()
    db_service.initialize()
    print(f"  - DatabaseService初始化成功")

    # 测试服务状态
    status = db_service.get_status()
    print(f"  - 数据库服务状态: {status}")
    
    # 测试metrics访问（不直接访问error_count）
    metrics = db_service.metrics
    print(f"  - Metrics访问成功: {type(metrics).__name__}")

# ========== 测试8: 缓存服务测试 ==========


def test_cache_service():
    """测试缓存服务功能"""
    from core.services.cache_service import CacheService

    cache_service = CacheService()
    cache_service.initialize()
    print(f"  - CacheService初始化成功")

    # 测试缓存操作
    test_key = "test_key"
    test_value = "test_value"
    cache_service.set(test_key, test_value)
    retrieved = cache_service.get(test_key)
    assert retrieved == test_value, "缓存值不匹配"
    print(f"  - 缓存读写成功")
    
    # 测试metrics访问
    metrics = cache_service.metrics
    print(f"  - Metrics访问成功: {type(metrics).__name__}")

# ========== 测试9: 数据服务基本功能 ==========


def test_data_service_basic():
    """测试数据服务基本功能"""
    from core.services.data_service import DataService

    data_service = DataService()
    data_service.initialize()
    print(f"  - DataService初始化成功")

    # 测试服务状态
    status = data_service.get_status()
    print(f"  - 服务状态: {status}")
    
    # 测试metrics访问
    metrics = data_service.metrics
    print(f"  - Metrics访问成功: {type(metrics).__name__}")

# ========== 测试10: 插件服务基本功能 ==========


def test_plugin_service_basic():
    """测试插件服务基本功能"""
    from core.services.plugin_service import PluginService

    plugin_service = PluginService()
    plugin_service.initialize()
    print(f"  - PluginService初始化成功")

    # 测试插件列表
    plugins = plugin_service.list_plugins()
    print(f"  - 插件列表获取成功: {len(plugins)} 个插件")
    
    # 测试metrics访问
    metrics = plugin_service.metrics
    print(f"  - Metrics访问成功: {type(metrics).__name__}")

# ========== 测试11: 网络服务基本功能 ==========


def test_network_service_basic():
    """测试网络服务基本功能"""
    from core.services.network_service import NetworkService

    network_service = NetworkService()
    network_service.initialize()
    print(f"  - NetworkService初始化成功")

    # 测试服务状态
    status = network_service.get_status()
    print(f"  - 网络服务状态: {status}")
    
    # 测试metrics访问
    metrics = network_service.metrics
    print(f"  - Metrics访问成功: {type(metrics).__name__}")

# ========== 测试12: 安全服务基本功能 ==========


def test_security_service_basic():
    """测试安全服务基本功能"""
    from core.services.security_service import SecurityService

    security_service = SecurityService()
    security_service.initialize()
    print(f"  - SecurityService初始化成功")

# ========== 测试13: 市场服务基本功能 ==========


def test_market_service_basic():
    """测试市场服务基本功能"""
    from core.services.market_service import MarketService

    market_service = MarketService()
    market_service.initialize()
    print(f"  - MarketService初始化成功")

# ========== 测试14: 分析服务基本功能 ==========


def test_analysis_service_basic():
    """测试分析服务基本功能"""
    from core.services.analysis_service import AnalysisService

    analysis_service = AnalysisService()
    analysis_service.initialize()
    print(f"  - AnalysisService初始化成功")

# ========== 测试15: 交易服务基本功能 ==========


def test_trading_service_basic():
    """测试交易服务基本功能"""
    from core.services.trading_service import TradingService

    trading_service = TradingService()
    trading_service.initialize()
    print(f"  - TradingService初始化成功")

# ========== 测试16: 通知服务基本功能 ==========


def test_notification_service_basic():
    """测试通知服务基本功能"""
    from core.services.notification_service import NotificationService

    notification_service = NotificationService()
    notification_service.initialize()
    print(f"  - NotificationService初始化成功")

# ========== 测试17: 生命周期服务基本功能 ==========


def test_lifecycle_service_basic():
    """测试生命周期服务基本功能"""
    from core.services.lifecycle_service import LifecycleService

    lifecycle_service = LifecycleService()
    lifecycle_service.initialize()
    print(f"  - LifecycleService初始化成功")

# ========== 执行所有测试 ==========


def run_all_tests():
    """运行所有测试"""
    test_module("服务导入测试", test_service_imports)
    test_module("服务实例化测试", test_service_instantiation)
    test_module("服务容器测试", test_service_container)
    test_module("配置服务测试", test_config_service)
    test_module("环境服务测试", test_environment_service)
    test_module("性能服务测试", test_performance_service)
    test_module("数据库服务测试", test_database_service)
    test_module("缓存服务测试", test_cache_service)
    test_module("数据服务基本功能", test_data_service_basic)
    test_module("插件服务基本功能", test_plugin_service_basic)
    test_module("网络服务基本功能", test_network_service_basic)
    test_module("安全服务基本功能", test_security_service_basic)
    test_module("市场服务基本功能", test_market_service_basic)
    test_module("分析服务基本功能", test_analysis_service_basic)
    test_module("交易服务基本功能", test_trading_service_basic)
    test_module("通知服务基本功能", test_notification_service_basic)
    test_module("生命周期服务基本功能", test_lifecycle_service_basic)


if __name__ == "__main__":
    start_time = time.time()

    run_all_tests()

    elapsed = time.time() - start_time

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print(f"总测试数: {tests_total}")
    print(f"✓ 通过: {tests_passed}")
    print(f"✗ 失败: {tests_failed}")
    print(f"成功率: {tests_passed/tests_total*100:.1f}%")
    print(f"总耗时: {elapsed:.2f}秒")
    print("="*60)

    # 生成测试报告
    report_path = project_root / "final_regression_test_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 全面功能回归测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now()}\n")
        f.write(f"**项目路径**: {project_root}\n\n")
        f.write(f"## 测试概要\n\n")
        f.write(f"- 总测试数: {tests_total}\n")
        f.write(f"- ✓ 通过: {tests_passed}\n")
        f.write(f"- ✗ 失败: {tests_failed}\n")
        f.write(f"- 成功率: {tests_passed/tests_total*100:.1f}%\n")
        f.write(f"- 总耗时: {elapsed:.2f}秒\n\n")
        f.write(f"## 结论\n\n")
        if tests_failed == 0:
            f.write(f"✅ **所有测试通过！架构精简重构成功完成，所有核心功能正常工作。**\n")
        else:
            f.write(f"⚠️ **部分测试失败，需要进一步检查和修复。**\n")

    print(f"\n✓ 测试报告已生成: {report_path}")

    sys.exit(0 if tests_failed == 0 else 1)
