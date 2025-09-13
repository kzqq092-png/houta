#!/usr/bin/env python3
"""
通用网络配置系统测试脚本
测试和验证整个网络配置系统的功能
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)


def test_network_config_manager():
    """测试通用网络配置管理器"""
    logger.info("=== 测试通用网络配置管理器 ===")
    
    try:
        from core.network.universal_network_config import (
            get_universal_network_manager, NetworkEndpoint, PluginNetworkConfig
        )
        
        manager = get_universal_network_manager()
        logger.info("✓ 网络配置管理器创建成功")
        
        # 测试端点创建
        test_endpoint = NetworkEndpoint(
            name="test_endpoint",
            url="https://test.example.com/api",
            description="测试端点",
            priority=10
        )
        logger.info("✓ 端点对象创建成功")
        
        # 测试配置创建
        test_config = PluginNetworkConfig(
            plugin_id="test.plugin",
            plugin_name="测试插件",
            endpoints=[test_endpoint]
        )
        logger.info("✓ 插件配置对象创建成功")
        
        # 测试配置保存和加载
        success = manager.update_plugin_config("test.plugin", test_config)
        if success:
            logger.info("✓ 插件配置保存成功")
        else:
            logger.error("✗ 插件配置保存失败")
        
        # 测试配置读取
        loaded_config = manager.get_plugin_config("test.plugin")
        if loaded_config:
            logger.info("✓ 插件配置读取成功")
            logger.info(f"  - 插件名: {loaded_config.plugin_name}")
            logger.info(f"  - 端点数: {len(loaded_config.endpoints)}")
        else:
            logger.error("✗ 插件配置读取失败")
        
        # 测试端点字符串转换
        endpoints_str = manager.get_endpoints_as_string("test.plugin")
        logger.info(f"✓ 端点字符串: {endpoints_str}")
        
        # 测试从字符串更新端点
        new_endpoints = "https://api1.example.com;https://api2.example.com;https://api3.example.com"
        success = manager.update_endpoints_from_string("test.plugin", new_endpoints)
        if success:
            logger.info("✓ 从字符串更新端点成功")
            
            # 验证更新结果
            updated_config = manager.get_plugin_config("test.plugin")
            if updated_config and len(updated_config.endpoints) == 3:
                logger.info(f"✓ 端点更新验证成功，共 {len(updated_config.endpoints)} 个端点")
            else:
                logger.error("✗ 端点更新验证失败")
        else:
            logger.error("✗ 从字符串更新端点失败")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 网络配置管理器测试失败: {e}")
        return False


def test_plugin_registry():
    """测试插件网络配置注册表"""
    logger.info("=== 测试插件网络配置注册表 ===")
    
    try:
        from core.network.plugin_network_registry import get_plugin_network_registry
        
        registry = get_plugin_network_registry()
        logger.info("✓ 插件注册表创建成功")
        
        # 测试插件发现和注册
        registration_results = registry.discover_and_register_plugins()
        
        total_plugins = len(registration_results)
        successful_plugins = sum(1 for success in registration_results.values() if success)
        
        logger.info(f"✓ 插件发现完成: {successful_plugins}/{total_plugins} 成功注册")
        
        # 显示注册结果
        for plugin_id, success in registration_results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {plugin_id}")
        
        # 测试已注册插件列表
        registered_plugins = registry.get_registered_plugins()
        logger.info(f"✓ 获取已注册插件: {len(registered_plugins)} 个")
        
        # 测试网络统计
        stats = registry.get_plugin_network_statistics()
        logger.info(f"✓ 网络统计:")
        logger.info(f"  - 总插件数: {stats['total_plugins']}")
        logger.info(f"  - 总端点数: {stats['total_endpoints']}")
        logger.info(f"  - 启用代理插件: {stats['plugins_with_proxy']}")
        logger.info(f"  - 启用频率限制插件: {stats['plugins_with_rate_limit']}")
        
        return successful_plugins > 0
        
    except Exception as e:
        logger.error(f"✗ 插件注册表测试失败: {e}")
        return False


def test_auto_register():
    """测试自动注册功能"""
    logger.info("=== 测试自动注册功能 ===")
    
    try:
        from core.network.plugin_auto_register import get_plugin_auto_register
        
        auto_register = get_plugin_auto_register()
        logger.info("✓ 自动注册器创建成功")
        
        # 测试自动注册
        registration_results = auto_register.register_all_plugins()
        
        # 获取注册状态
        status = auto_register.get_registration_status()
        logger.info(f"✓ 自动注册完成:")
        logger.info(f"  - 状态: {status['status']}")
        logger.info(f"  - 总插件: {status['total_plugins']}")
        logger.info(f"  - 成功: {status['successful_registrations']}")
        logger.info(f"  - 失败: {status['failed_registrations']}")
        logger.info(f"  - 成功率: {status['success_rate']:.1%}")
        
        # 获取插件信息
        plugins_info = auto_register.get_registered_plugins_info()
        logger.info(f"✓ 插件详细信息:")
        for plugin_info in plugins_info:
            logger.info(f"  - {plugin_info['plugin_name']}: {plugin_info['endpoints_count']} 端点")
        
        # 获取网络摘要
        summary = auto_register.get_plugin_network_summary()
        recommendations = summary.get('recommendations', [])
        logger.info(f"✓ 配置建议:")
        for rec in recommendations:
            logger.info(f"  - {rec}")
        
        return status['successful_registrations'] > 0
        
    except Exception as e:
        logger.error(f"✗ 自动注册功能测试失败: {e}")
        return False


def test_app_initialization():
    """测试应用初始化"""
    logger.info("=== 测试应用初始化 ===")
    
    try:
        from core.app_initialization import get_app_initializer
        
        initializer = get_app_initializer()
        logger.info("✓ 应用初始化器创建成功")
        
        # 测试初始化
        results = initializer.initialize_all()
        
        logger.info(f"✓ 应用初始化完成:")
        
        # 网络配置结果
        network_config = results.get('network_config', {})
        if network_config.get('status') == 'success':
            logger.info(f"  ✓ 网络配置: {network_config['successful_plugins']}/{network_config['total_plugins']} 插件")
        else:
            logger.error(f"  ✗ 网络配置失败: {network_config.get('error')}")
        
        # 数据库结果
        database = results.get('database', {})
        if database.get('status') == 'success':
            logger.info("  ✓ 数据库初始化成功")
        else:
            logger.error(f"  ✗ 数据库初始化失败: {database.get('error')}")
        
        # 其他组件
        other = results.get('other_components', {})
        if other.get('status') == 'success':
            logger.info("  ✓ 其他组件初始化成功")
        else:
            logger.error(f"  ✗ 其他组件初始化失败: {other.get('error')}")
        
        return not results.get('error')
        
    except Exception as e:
        logger.error(f"✗ 应用初始化测试失败: {e}")
        return False


def test_akshare_plugin():
    """测试AkShare插件的网络配置"""
    logger.info("=== 测试AkShare插件网络配置 ===")
    
    try:
        from plugins.sentiment_data_sources.akshare_sentiment_plugin import AkShareSentimentPlugin
        
        plugin = AkShareSentimentPlugin()
        logger.info("✓ AkShare插件创建成功")
        
        # 测试默认端点
        default_endpoints = plugin.get_default_endpoints()
        logger.info(f"✓ 默认端点: {len(default_endpoints)} 个")
        for endpoint in default_endpoints:
            logger.info(f"  - {endpoint.name}: {endpoint.url}")
        
        # 测试网络配置架构
        schema = plugin.get_network_config_schema()
        logger.info("✓ 网络配置架构获取成功")
        logger.info(f"  - 端点类别: {list(schema['endpoints']['categories'].keys())}")
        logger.info(f"  - 默认请求频率: {schema['rate_limit']['default_requests_per_minute']}/分钟")
        
        # 测试网络状态
        network_status = plugin.get_network_status()
        logger.info("✓ 网络状态获取成功")
        logger.info(f"  - 请求计数: {network_status['request_count']}")
        logger.info(f"  - IP被封: {network_status['ip_blocked']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ AkShare插件测试失败: {e}")
        return False


def test_eastmoney_plugin():
    """测试东方财富插件的网络配置"""
    logger.info("=== 测试东方财富插件网络配置 ===")
    
    try:
        from plugins.examples.eastmoney_stock_plugin import EastMoneyStockPlugin
        
        plugin = EastMoneyStockPlugin()
        logger.info("✓ 东方财富插件创建成功")
        
        # 测试默认端点
        if hasattr(plugin, 'get_default_endpoints'):
            default_endpoints = plugin.get_default_endpoints()
            logger.info(f"✓ 默认端点: {len(default_endpoints)} 个")
            for endpoint in default_endpoints:
                logger.info(f"  - {endpoint.name}: {endpoint.url}")
        else:
            logger.warning("✗ 插件不支持get_default_endpoints方法")
        
        # 测试网络配置架构
        if hasattr(plugin, 'get_network_config_schema'):
            schema = plugin.get_network_config_schema()
            logger.info("✓ 网络配置架构获取成功")
            logger.info(f"  - 端点类别: {list(schema['endpoints']['categories'].keys())}")
            logger.info(f"  - 默认请求频率: {schema['rate_limit']['default_requests_per_minute']}/分钟")
        else:
            logger.warning("✗ 插件不支持get_network_config_schema方法")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 东方财富插件测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    logger.info("开始通用网络配置系统测试...")
    
    test_results = []
    
    # 运行各项测试
    tests = [
        ("网络配置管理器", test_network_config_manager),
        ("插件注册表", test_plugin_registry),
        ("自动注册功能", test_auto_register),
        ("应用初始化", test_app_initialization),
        ("AkShare插件", test_akshare_plugin),
        ("东方财富插件", test_eastmoney_plugin),
    ]
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*50}")
            success = test_func()
            test_results.append((test_name, success))
        except Exception as e:
            logger.error(f"测试 {test_name} 发生异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试摘要
    logger.info(f"\n{'='*50}")
    logger.info("=== 测试摘要 ===")
    
    passed_count = 0
    for test_name, success in test_results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} {test_name}")
        if success:
            passed_count += 1
    
    total_tests = len(test_results)
    logger.info(f"\n测试结果: {passed_count}/{total_tests} 通过 ({passed_count/total_tests:.1%})")
    
    if passed_count == total_tests:
        logger.info("🎉 所有测试通过！通用网络配置系统工作正常。")
        return True
    else:
        logger.warning(f"⚠️  有 {total_tests - passed_count} 个测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        sys.exit(1)
