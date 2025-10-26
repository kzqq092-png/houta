"""
全面检查迁移的数据源插件
- 检查文件结构
- 验证代码完整性
- 检查继承关系
- 验证方法实现
- 检查系统集成
"""
from core.plugin_manager import PluginManager
from typing import Dict, List, Any
import inspect
import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


# 要检查的插件列表
TARGET_PLUGINS = {
    "data_sources.crypto.binance_plugin": {
        "expected_class": "BinancePlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1200,
        "category": "crypto"
    },
    "data_sources.crypto.okx_plugin": {
        "expected_class": "OKXPlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1000,
        "category": "crypto"
    },
    "data_sources.crypto.huobi_plugin": {
        "expected_class": "HuobiPlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1000,
        "category": "crypto"
    },
    "data_sources.crypto.coinbase_plugin": {
        "expected_class": "CoinbasePlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1000,
        "category": "crypto"
    },
    "data_sources.crypto.crypto_universal_plugin": {
        "expected_class": "CryptoUniversalPlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1200,
        "category": "crypto"
    },
    "data_sources.futures.wenhua_plugin": {
        "expected_class": "WenhuaPlugin",
        "expected_base": "HTTPAPIPluginTemplate",
        "min_lines": 1000,
        "category": "futures"
    }
}

# 必需的方法
REQUIRED_METHODS = [
    'get_plugin_info',
    'initialize',
    '_do_connect',
    'connect',
    'get_connection_info',
    'get_asset_list',
    'get_real_time_quotes',
    'get_supported_asset_types',
    'get_supported_data_types',
    'get_kdata',
    '_get_default_config',
    '_get_default_headers',
    '_test_connection',
    '_sign_request'
]

# 必需的属性
REQUIRED_ATTRIBUTES = [
    'plugin_id',
    'name',
    'version',
    'description',
    'author',
    'plugin_type',
    'plugin_state',
    'initialized',
    'DEFAULT_CONFIG'
]


def check_file_exists(plugin_module: str, expected_info: Dict) -> Dict:
    """检查文件是否存在"""
    result = {"status": "FAIL", "issues": []}

    # 构建文件路径
    module_parts = plugin_module.split('.')
    file_path = Path("plugins") / "/".join(module_parts) / ".py".replace("/", ".py")
    file_path = Path("plugins") / module_parts[0] / module_parts[1] / f"{module_parts[2]}.py"

    if file_path.exists():
        result["status"] = "PASS"
        result["path"] = str(file_path)

        # 检查文件大小
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            result["lines"] = len(lines)

            if len(lines) < expected_info["min_lines"]:
                result["issues"].append(f"文件行数({len(lines)}) < 期望最小行数({expected_info['min_lines']}), 可能被精简")
    else:
        result["issues"].append(f"文件不存在: {file_path}")

    return result


def check_class_structure(plugin_module: str, expected_info: Dict) -> Dict:
    """检查类结构"""
    result = {"status": "FAIL", "issues": [], "methods": [], "attributes": []}

    try:
        # 导入模块
        module = __import__(plugin_module, fromlist=[expected_info["expected_class"]])
        plugin_class = getattr(module, expected_info["expected_class"], None)

        if not plugin_class:
            result["issues"].append(f"找不到类 {expected_info['expected_class']}")
            return result

        # 检查继承关系
        base_classes = [base.__name__ for base in plugin_class.__bases__]
        result["base_classes"] = base_classes

        if expected_info["expected_base"] not in base_classes:
            result["issues"].append(f"未继承 {expected_info['expected_base']}, 实际继承: {base_classes}")

        # 检查方法
        for method_name in REQUIRED_METHODS:
            if hasattr(plugin_class, method_name):
                method = getattr(plugin_class, method_name)
                if callable(method):
                    result["methods"].append(method_name)
                else:
                    result["issues"].append(f"{method_name} 不可调用")
            else:
                result["issues"].append(f"缺少方法: {method_name}")

        # 实例化检查属性
        try:
            instance = plugin_class()
            for attr_name in REQUIRED_ATTRIBUTES:
                if hasattr(instance, attr_name):
                    result["attributes"].append(attr_name)
                else:
                    result["issues"].append(f"缺少属性: {attr_name}")
        except Exception as e:
            result["issues"].append(f"实例化失败: {e}")

        if len(result["issues"]) == 0:
            result["status"] = "PASS"

    except Exception as e:
        result["issues"].append(f"导入失败: {e}")

    return result


def check_system_integration(plugin_module: str) -> Dict:
    """检查系统集成"""
    result = {"status": "FAIL", "issues": []}

    try:
        # 初始化插件管理器
        pm = PluginManager()
        pm.load_all_plugins()

        # 检查插件是否在plugin_instances中
        if plugin_module in pm.plugin_instances:
            result["status"] = "PASS"
            result["loaded"] = True

            # 获取插件实例
            plugin_instance = pm.plugin_instances[plugin_module]

            # 检查plugin_state
            if hasattr(plugin_instance, 'plugin_state'):
                result["plugin_state"] = str(plugin_instance.plugin_state)
            else:
                result["issues"].append("缺少 plugin_state 属性")

            # 检查initialized
            if hasattr(plugin_instance, 'initialized'):
                result["initialized"] = plugin_instance.initialized
            else:
                result["issues"].append("缺少 initialized 属性")

            # 检查是否注册到数据源路由器
            from core.services.unified_data_manager import get_unified_data_manager
            try:
                udm = get_unified_data_manager()
                if udm and hasattr(udm, 'data_router'):
                    router = udm.data_router
                    if hasattr(router, 'data_sources'):
                        plugin_ids = [ds.plugin_id if hasattr(ds, 'plugin_id') else 'N/A' for ds in router.data_sources.values()]
                        result["registered_to_router"] = plugin_module in router.data_sources or any(plugin_module in pid for pid in plugin_ids)
            except:
                pass
        else:
            result["loaded"] = False
            result["issues"].append("插件未加载到 plugin_instances")

    except Exception as e:
        result["issues"].append(f"系统集成检查失败: {e}")

    return result


def print_separator(title: str = ""):
    """打印分隔符"""
    if title:
        print(f"\n{'=' * 80}")
        print(f" {title}")
        print(f"{'=' * 80}")
    else:
        print(f"{'=' * 80}")


def print_check_result(check_name: str, result: Dict):
    """打印检查结果"""
    status_symbol = "[PASS]" if result["status"] == "PASS" else "[FAIL]"
    print(f"\n{status_symbol} {check_name}")

    for key, value in result.items():
        if key not in ["status", "issues"]:
            if isinstance(value, list):
                if len(value) > 0:
                    print(f"  {key}: {len(value)} 项")
                    for item in value[:5]:  # 只显示前5个
                        print(f"    - {item}")
                    if len(value) > 5:
                        print(f"    ... 还有 {len(value) - 5} 项")
            else:
                print(f"  {key}: {value}")

    if result["issues"]:
        print(f"  问题:")
        for issue in result["issues"]:
            print(f"    - {issue}")


def main():
    print_separator("数据源插件全面检查")

    all_passed = True
    results_summary = []

    for plugin_module, expected_info in TARGET_PLUGINS.items():
        print_separator(f"检查插件: {plugin_module}")

        # 1. 文件存在性检查
        file_check = check_file_exists(plugin_module, expected_info)
        print_check_result("1. 文件存在性检查", file_check)

        # 2. 类结构检查
        class_check = check_class_structure(plugin_module, expected_info)
        print_check_result("2. 类结构检查", class_check)

        # 3. 系统集成检查
        integration_check = check_system_integration(plugin_module)
        print_check_result("3. 系统集成检查", integration_check)

        # 汇总结果
        plugin_passed = (
            file_check["status"] == "PASS" and
            class_check["status"] == "PASS" and
            integration_check["status"] == "PASS"
        )

        results_summary.append({
            "plugin": plugin_module,
            "passed": plugin_passed,
            "file_check": file_check["status"],
            "class_check": class_check["status"],
            "integration_check": integration_check["status"],
            "total_issues": len(file_check["issues"]) + len(class_check["issues"]) + len(integration_check["issues"])
        })

        if not plugin_passed:
            all_passed = False

    # 打印总结
    print_separator("检查总结")
    print(f"\n检查的插件总数: {len(TARGET_PLUGINS)}")

    passed_count = sum(1 for r in results_summary if r["passed"])
    print(f"通过的插件数: {passed_count}")
    print(f"失败的插件数: {len(TARGET_PLUGINS) - passed_count}")

    print(f"\n详细结果:")
    for result in results_summary:
        status = "[PASS]" if result["passed"] else "[FAIL]"
        print(f"{status} {result['plugin']}")
        print(f"    文件检查: {result['file_check']}, 类结构: {result['class_check']}, 系统集成: {result['integration_check']}")
        if result['total_issues'] > 0:
            print(f"    总问题数: {result['total_issues']}")

    print_separator()
    if all_passed:
        print("结论: 所有插件检查通过!")
        return 0
    else:
        print("结论: 部分插件检查失败,需要修复")
        return 1


if __name__ == '__main__':
    sys.exit(main())
