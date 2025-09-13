#!/usr/bin/env python3
"""
全面的数据源插件质量检查

检查所有数据源插件的：
1. 接口实现完整性
2. 功能实现质量
3. 元数据准确性
4. 实际可用性
"""

from core.plugin_types import AssetType, DataType
from core.data_source_extensions import IDataSourcePlugin
import sys
import inspect
from pathlib import Path
from typing import Dict, List, Any, Tuple
import importlib
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class PluginQualityChecker:
    """插件质量检查器"""

    def __init__(self):
        self.required_methods = [
            'plugin_info', 'connect', 'disconnect', 'is_connected',
            'get_connection_info', 'health_check', 'get_asset_list',
            'get_kdata', 'get_real_time_quotes'
        ]

    def check_interface_completeness(self, plugin_class) -> Dict[str, Any]:
        """检查接口实现完整性"""
        result = {
            'missing_methods': [],
            'abstract_methods': set(),
            'method_signatures': {},
            'has_proper_plugin_info': False
        }

        # 检查抽象方法
        abstract_methods = getattr(plugin_class, '__abstractmethods__', set())
        result['abstract_methods'] = abstract_methods

        # 检查必需方法
        for method_name in self.required_methods:
            if not hasattr(plugin_class, method_name):
                result['missing_methods'].append(method_name)
            else:
                method = getattr(plugin_class, method_name)
                if method_name == 'plugin_info':
                    # 检查是否是属性
                    result['has_proper_plugin_info'] = isinstance(inspect.getattr_static(plugin_class, method_name), property)
                else:
                    # 获取方法签名
                    try:
                        sig = inspect.signature(method)
                        result['method_signatures'][method_name] = str(sig)
                    except:
                        result['method_signatures'][method_name] = 'unknown'

        return result

    def check_implementation_quality(self, plugin_instance) -> Dict[str, Any]:
        """检查实现质量"""
        result = {
            'empty_implementations': [],
            'todo_implementations': [],
            'functional_methods': [],
            'plugin_info_quality': {}
        }

        # 检查plugin_info质量
        try:
            plugin_info = plugin_instance.plugin_info
            result['plugin_info_quality'] = {
                'has_id': bool(getattr(plugin_info, 'id', None)),
                'has_name': bool(getattr(plugin_info, 'name', None)),
                'has_version': bool(getattr(plugin_info, 'version', None)),
                'has_description': bool(getattr(plugin_info, 'description', None)),
                'has_author': bool(getattr(plugin_info, 'author', None)),
                'has_supported_asset_types': bool(getattr(plugin_info, 'supported_asset_types', None)),
                'has_supported_data_types': bool(getattr(plugin_info, 'supported_data_types', None)),
                'has_capabilities': bool(getattr(plugin_info, 'capabilities', None)),
                'id_value': getattr(plugin_info, 'id', 'N/A'),
                'name_value': getattr(plugin_info, 'name', 'N/A'),
                'version_value': getattr(plugin_info, 'version', 'N/A')
            }
        except Exception as e:
            result['plugin_info_quality']['error'] = str(e)

        # 检查方法实现质量
        for method_name in self.required_methods:
            if method_name == 'plugin_info':
                continue

            if hasattr(plugin_instance, method_name):
                method = getattr(plugin_instance, method_name)
                try:
                    # 获取方法源码
                    source = inspect.getsource(method)

                    # 检查是否是空实现
                    if 'pass' in source and source.count('\n') <= 3:
                        result['empty_implementations'].append(method_name)
                    elif 'TODO' in source or 'NotImplementedError' in source:
                        result['todo_implementations'].append(method_name)
                    else:
                        result['functional_methods'].append(method_name)

                except Exception as e:
                    # 无法获取源码，可能是内建方法
                    result['functional_methods'].append(method_name)

        return result

    def check_functional_capability(self, plugin_instance) -> Dict[str, Any]:
        """检查功能可用性"""
        result = {
            'connection_test': False,
            'plugin_info_accessible': False,
            'health_check_works': False,
            'asset_list_works': False,
            'connection_info_works': False,
            'errors': []
        }

        # 测试plugin_info访问
        try:
            plugin_info = plugin_instance.plugin_info
            result['plugin_info_accessible'] = True
        except Exception as e:
            result['errors'].append(f"plugin_info访问失败: {e}")

        # 测试连接功能
        try:
            # 注意：不实际连接，只测试方法是否可调用
            connect_result = plugin_instance.connect()
            result['connection_test'] = isinstance(connect_result, bool)
        except Exception as e:
            result['errors'].append(f"connect方法测试失败: {e}")

        # 测试健康检查
        try:
            health_result = plugin_instance.health_check()
            result['health_check_works'] = health_result is not None
        except Exception as e:
            result['errors'].append(f"health_check方法测试失败: {e}")

        # 测试连接信息
        try:
            conn_info = plugin_instance.get_connection_info()
            result['connection_info_works'] = conn_info is not None
        except Exception as e:
            result['errors'].append(f"get_connection_info方法测试失败: {e}")

        # 测试资产列表（不传入参数避免实际网络请求）
        try:
            asset_list = plugin_instance.get_asset_list(AssetType.STOCK)
            result['asset_list_works'] = isinstance(asset_list, list)
        except Exception as e:
            result['errors'].append(f"get_asset_list方法测试失败: {e}")

        return result


def check_data_source_plugin(module_path: str, class_name: str) -> Dict[str, Any]:
    """检查单个数据源插件"""
    result = {
        'module_path': module_path,
        'class_name': class_name,
        'import_success': False,
        'instantiation_success': False,
        'interface_check': {},
        'quality_check': {},
        'functional_check': {},
        'overall_score': 0,
        'issues': [],
        'recommendations': []
    }

    checker = PluginQualityChecker()

    try:
        # 导入模块
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        result['import_success'] = True

        # 检查接口完整性
        interface_result = checker.check_interface_completeness(plugin_class)
        result['interface_check'] = interface_result

        # 尝试实例化
        try:
            plugin_instance = plugin_class()
            result['instantiation_success'] = True

            # 检查实现质量
            quality_result = checker.check_implementation_quality(plugin_instance)
            result['quality_check'] = quality_result

            # 检查功能可用性
            functional_result = checker.check_functional_capability(plugin_instance)
            result['functional_check'] = functional_result

        except Exception as e:
            result['issues'].append(f"实例化失败: {e}")

    except Exception as e:
        result['issues'].append(f"导入失败: {e}")

    # 计算总体评分
    score = 0
    if result['import_success']:
        score += 20
    if result['instantiation_success']:
        score += 20
    if not result['interface_check'].get('abstract_methods'):
        score += 20
    if not result['interface_check'].get('missing_methods'):
        score += 20
    if result['quality_check'].get('functional_methods'):
        score += 10
    if result['functional_check'].get('plugin_info_accessible'):
        score += 10

    result['overall_score'] = score

    # 生成建议
    if result['interface_check'].get('abstract_methods'):
        result['recommendations'].append("需要实现抽象方法")
    if result['interface_check'].get('missing_methods'):
        result['recommendations'].append("需要添加缺失的方法")
    if result['quality_check'].get('empty_implementations'):
        result['recommendations'].append("需要完善空实现的方法")
    if result['quality_check'].get('todo_implementations'):
        result['recommendations'].append("需要完成TODO标记的方法")

    return result


def main():
    """主函数"""
    logger.info(" 开始全面的数据源插件质量检查...\n")

    # 需要检查的数据源插件
    plugins_to_check = [
        ('plugins.data_sources.hikyuu_data_plugin', 'HikyuuDataPlugin'),
        ('plugins.examples.tongdaxin_stock_plugin', 'TongdaxinStockPlugin'),
        ('plugins.examples.akshare_stock_plugin', 'AKShareStockPlugin'),
        ('plugins.examples.binance_crypto_plugin', 'BinanceCryptoPlugin'),
        ('plugins.examples.wind_data_plugin', 'WindDataPlugin'),
        ('plugins.examples.eastmoney_stock_plugin', 'EastmoneyStockPlugin'),
        ('plugins.examples.yahoo_finance_datasource', 'YahooFinanceDataSourcePlugin'),
        ('plugins.examples.coinbase_crypto_plugin', 'CoinbaseProPlugin'),
        ('plugins.examples.huobi_crypto_plugin', 'HuobiCryptoPlugin'),
        ('plugins.examples.okx_crypto_plugin', 'OKXCryptoPlugin'),
    ]

    results = []

    for module_path, class_name in plugins_to_check:
        logger.info(f" 检查插件: {class_name}")
        result = check_data_source_plugin(module_path, class_name)
        results.append(result)

        # 显示检查结果
        logger.info(f"  导入成功: {'' if result['import_success'] else ''}")
        logger.info(f"  实例化成功: {'' if result['instantiation_success'] else ''}")
        logger.info(f"  总体评分: {result['overall_score']}/100")

        if result['issues']:
            logger.info(f"  问题: {', '.join(result['issues'])}")

        if result['recommendations']:
            logger.info(f"  建议: {', '.join(result['recommendations'])}")

    # 生成总结报告
    logger.info(f"{'='*60}")
    logger.info(" 检查结果总结")
    logger.info(f"{'='*60}")

    total_plugins = len(results)
    successful_imports = sum(1 for r in results if r['import_success'])
    successful_instantiations = sum(1 for r in results if r['instantiation_success'])
    high_quality = sum(1 for r in results if r['overall_score'] >= 80)
    medium_quality = sum(1 for r in results if 50 <= r['overall_score'] < 80)
    low_quality = sum(1 for r in results if r['overall_score'] < 50)

    logger.info(f"总插件数: {total_plugins}")
    logger.info(f"成功导入: {successful_imports}/{total_plugins}")
    logger.info(f"成功实例化: {successful_instantiations}/{total_plugins}")
    logger.info(f"高质量插件 (≥80分): {high_quality}")
    logger.info(f"中等质量插件 (50-79分): {medium_quality}")
    logger.info(f"低质量插件 (<50分): {low_quality}")

    # 详细问题分析
    logger.info(f"\n 详细问题分析:")
    for result in results:
        if result['overall_score'] < 80:
            logger.info(f"\n{result['class_name']} (评分: {result['overall_score']}):")

            # 接口问题
            if result['interface_check'].get('abstract_methods'):
                logger.info(f"   未实现抽象方法: {result['interface_check']['abstract_methods']}")
            if result['interface_check'].get('missing_methods'):
                logger.info(f"   缺失方法: {result['interface_check']['missing_methods']}")

            # 实现质量问题
            if result['quality_check'].get('empty_implementations'):
                logger.info(f"   空实现方法: {result['quality_check']['empty_implementations']}")
            if result['quality_check'].get('todo_implementations'):
                logger.info(f"   TODO方法: {result['quality_check']['todo_implementations']}")

            # 功能问题
            if result['functional_check'].get('errors'):
                logger.info(f"   功能错误: {result['functional_check']['errors'][:2]}")  # 只显示前2个错误

    return results


if __name__ == "__main__":
    results = main()
