"""
全面验证所有修改的插件 - 检查完整性、功能和实现质量
"""
from core.plugin_manager import PluginManager
import sys
from pathlib import Path
import inspect

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_plugin_completeness(plugin_name, plugin_instance):
    """检查单个插件的完整性"""
    results = {
        'plugin_name': plugin_name,
        'basic_attrs': {},
        'required_methods': {},
        'state_attrs': {},
        'config_attrs': {},
        'issues': []
    }

    # 1. 检查基本属性
    basic_attrs = ['plugin_id', 'name', 'version', 'description', 'author', 'plugin_type']
    for attr in basic_attrs:
        if hasattr(plugin_instance, attr):
            value = getattr(plugin_instance, attr)
            results['basic_attrs'][attr] = 'OK' if value else 'EMPTY'
            if not value:
                results['issues'].append(f"Basic attribute '{attr}' is empty")
        else:
            results['basic_attrs'][attr] = 'MISSING'
            results['issues'].append(f"Basic attribute '{attr}' is missing")

    # 2. 检查必需方法
    required_methods = [
        'get_plugin_info',
        'initialize',
        'connect',
        'get_connection_info',
        'get_asset_list',
        'get_real_time_quotes',
        'get_supported_asset_types',
        'get_supported_data_types',
        '_get_default_headers',
        '_test_connection',
        '_sign_request',
        'get_kdata'
    ]

    for method_name in required_methods:
        if hasattr(plugin_instance, method_name):
            method = getattr(plugin_instance, method_name)
            if callable(method):
                results['required_methods'][method_name] = 'OK'
            else:
                results['required_methods'][method_name] = 'NOT_CALLABLE'
                results['issues'].append(f"Method '{method_name}' exists but not callable")
        else:
            results['required_methods'][method_name] = 'MISSING'
            results['issues'].append(f"Required method '{method_name}' is missing")

    # 3. 检查状态属性
    state_attrs = ['plugin_state', 'initialized', 'last_error']
    for attr in state_attrs:
        if hasattr(plugin_instance, attr):
            results['state_attrs'][attr] = 'OK'
        else:
            results['state_attrs'][attr] = 'MISSING'
            results['issues'].append(f"State attribute '{attr}' is missing")

    # 4. 检查配置属性
    config_attrs = ['DEFAULT_CONFIG', 'config']
    for attr in config_attrs:
        if hasattr(plugin_instance, attr):
            value = getattr(plugin_instance, attr)
            results['config_attrs'][attr] = 'OK' if value else 'EMPTY'
        else:
            results['config_attrs'][attr] = 'MISSING'
            results['issues'].append(f"Config attribute '{attr}' is missing")

    # 5. 检查get_plugin_info的返回值
    if hasattr(plugin_instance, 'get_plugin_info'):
        try:
            info = plugin_instance.get_plugin_info()
            if info:
                # 检查PluginInfo的必需字段
                info_fields = ['id', 'name', 'version', 'description', 'author',
                               'supported_asset_types', 'supported_data_types']
                for field in info_fields:
                    if not hasattr(info, field):
                        results['issues'].append(f"PluginInfo missing field '{field}'")
            else:
                results['issues'].append("get_plugin_info() returned None")
        except Exception as e:
            results['issues'].append(f"get_plugin_info() raised exception: {e}")

    return results


def print_plugin_report(results):
    """打印单个插件的检查报告"""
    plugin_name = results['plugin_name']
    print(f"\n{'='*80}")
    print(f"Plugin: {plugin_name}")
    print(f"{'='*80}")

    # 基本属性
    print("\n[Basic Attributes]")
    for attr, status in results['basic_attrs'].items():
        symbol = "[OK]" if status == 'OK' else ("[WARN]" if status == 'EMPTY' else "[FAIL]")
        print(f"  {symbol} {attr}: {status}")

    # 必需方法
    print("\n[Required Methods]")
    for method, status in results['required_methods'].items():
        symbol = "[OK]" if status == 'OK' else "[FAIL]"
        print(f"  {symbol} {method}: {status}")

    # 状态属性
    print("\n[State Attributes]")
    for attr, status in results['state_attrs'].items():
        symbol = "[OK]" if status == 'OK' else "[FAIL]"
        print(f"  {symbol} {attr}: {status}")

    # 配置属性
    print("\n[Config Attributes]")
    for attr, status in results['config_attrs'].items():
        symbol = "[OK]" if status == 'OK' else ("[WARN]" if status == 'EMPTY' else "[FAIL]")
        print(f"  {attr}: {status}")

    # 问题汇总
    if results['issues']:
        print(f"\n[Issues Found: {len(results['issues'])}]")
        for i, issue in enumerate(results['issues'], 1):
            print(f"  {i}. {issue}")
    else:
        print("\n[Status: ALL CHECKS PASSED]")

    return len(results['issues']) == 0


def main():
    """主验证流程"""
    print("="*80)
    print("全面插件完整性验证")
    print("="*80)

    # 初始化插件管理器
    plugin_manager = PluginManager()
    plugin_manager.load_all_plugins()

    # 目标插件列表
    target_plugins = [
        'data_sources.crypto.binance_plugin',
        'data_sources.crypto.okx_plugin',
        'data_sources.crypto.huobi_plugin',
        'data_sources.crypto.coinbase_plugin',
        'data_sources.crypto.crypto_universal_plugin',
        'data_sources.futures.wenhua_plugin'
    ]

    all_passed = True
    results_summary = []

    for plugin_name in target_plugins:
        if plugin_name in plugin_manager.plugin_instances:
            plugin_instance = plugin_manager.plugin_instances[plugin_name]
            results = check_plugin_completeness(plugin_name, plugin_instance)
            passed = print_plugin_report(results)

            results_summary.append({
                'name': plugin_name,
                'passed': passed,
                'issue_count': len(results['issues'])
            })

            if not passed:
                all_passed = False
        else:
            print(f"\n[ERROR] Plugin not loaded: {plugin_name}")
            results_summary.append({
                'name': plugin_name,
                'passed': False,
                'issue_count': 999
            })
            all_passed = False

    # 总结报告
    print("\n" + "="*80)
    print("验证总结")
    print("="*80)

    for result in results_summary:
        status = "[PASS]" if result['passed'] else f"[FAIL - {result['issue_count']} issues]"
        print(f"{status} {result['name']}")

    print("\n" + "="*80)
    if all_passed:
        print("结论: 所有插件验证通过!")
        print("="*80)
        return 0
    else:
        failed_count = sum(1 for r in results_summary if not r['passed'])
        print(f"结论: {failed_count}/{len(target_plugins)} 个插件存在问题")
        print("="*80)
        return 1


if __name__ == '__main__':
    sys.exit(main())
