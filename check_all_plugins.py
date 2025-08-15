#!/usr/bin/env python3
"""
检查所有数据源插件的必需属性和方法
"""

import sys
import os
import importlib.util
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_plugin_requirements(plugin_class):
    """检查插件是否有必需的属性和方法"""
    required_attributes = ['initialized']
    required_methods = ['is_connected', 'initialize', 'health_check', 'get_plugin_info']

    results = {
        'attributes': {},
        'methods': {},
        'missing': []
    }

    # 创建插件实例
    try:
        plugin_instance = plugin_class()
    except Exception as e:
        return {'error': f'无法创建插件实例: {e}'}

    # 检查属性
    for attr in required_attributes:
        has_attr = hasattr(plugin_instance, attr)
        results['attributes'][attr] = has_attr
        if not has_attr:
            results['missing'].append(f'属性: {attr}')

    # 检查方法
    for method in required_methods:
        has_method = hasattr(plugin_instance, method) and callable(getattr(plugin_instance, method))
        results['methods'][method] = has_method
        if not has_method:
            results['missing'].append(f'方法: {method}')

    return results


def load_plugin_from_file(file_path):
    """从文件加载插件类"""
    try:
        spec = importlib.util.spec_from_file_location("plugin_module", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 查找继承自IDataSourcePlugin的类
        plugin_classes = []
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and
                hasattr(obj, '__bases__') and
                    any('IDataSourcePlugin' in str(base) for base in obj.__bases__)):
                plugin_classes.append(obj)

        return plugin_classes
    except Exception as e:
        return None, str(e)


def main():
    """主函数"""
    print("🔍 检查所有数据源插件的必需属性和方法")
    print("=" * 80)

    plugins_dir = project_root / "plugins" / "examples"

    # 数据源插件文件列表
    data_source_plugins = [
        'akshare_stock_plugin.py',
        'binance_crypto_plugin.py',
        'bond_data_plugin.py',
        'coinbase_crypto_plugin.py',
        'crypto_data_plugin.py',
        'ctp_futures_plugin.py',
        'custom_data_plugin.py',
        'eastmoney_stock_plugin.py',
        'forex_data_plugin.py',
        'futures_data_plugin.py',
        'huobi_crypto_plugin.py',
        'mysteel_data_plugin.py',
        'okx_crypto_plugin.py',
        'wenhua_data_plugin.py',
        'wind_data_plugin.py',
        'yahoo_finance_datasource.py'
    ]

    total_plugins = 0
    plugins_with_issues = 0
    all_issues = []

    for plugin_file in data_source_plugins:
        plugin_path = plugins_dir / plugin_file
        if not plugin_path.exists():
            print(f"⚠️ 文件不存在: {plugin_file}")
            continue

        print(f"\n📋 检查插件: {plugin_file}")

        plugin_classes = load_plugin_from_file(plugin_path)
        if isinstance(plugin_classes, tuple):  # 错误情况
            print(f"  ❌ 加载失败: {plugin_classes[1]}")
            continue

        if not plugin_classes:
            print(f"  ⚠️ 未找到数据源插件类")
            continue

        for plugin_class in plugin_classes:
            total_plugins += 1
            print(f"  🔍 检查类: {plugin_class.__name__}")

            results = check_plugin_requirements(plugin_class)

            if 'error' in results:
                print(f"    ❌ {results['error']}")
                plugins_with_issues += 1
                all_issues.append(f"{plugin_file}::{plugin_class.__name__} - {results['error']}")
                continue

            # 显示检查结果
            has_issues = False

            print("    📊 属性检查:")
            for attr, has_attr in results['attributes'].items():
                status = "✅" if has_attr else "❌"
                print(f"      {status} {attr}")
                if not has_attr:
                    has_issues = True

            print("    📊 方法检查:")
            for method, has_method in results['methods'].items():
                status = "✅" if has_method else "❌"
                print(f"      {status} {method}")
                if not has_method:
                    has_issues = True

            if has_issues:
                plugins_with_issues += 1
                missing_items = ", ".join(results['missing'])
                all_issues.append(f"{plugin_file}::{plugin_class.__name__} - 缺少: {missing_items}")
                print(f"    ⚠️ 缺少: {missing_items}")
            else:
                print("    ✅ 所有必需项都存在")

    # 总结报告
    print("\n" + "=" * 80)
    print("📊 检查总结:")
    print(f"  📈 总插件数: {total_plugins}")
    print(f"  ❌ 有问题的插件: {plugins_with_issues}")
    print(f"  ✅ 正常插件: {total_plugins - plugins_with_issues}")
    print(f"  📈 成功率: {(total_plugins - plugins_with_issues) / total_plugins * 100:.1f}%")

    if all_issues:
        print("\n🔧 需要修复的问题:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n🎉 所有插件都符合要求！")

    return 0 if plugins_with_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
