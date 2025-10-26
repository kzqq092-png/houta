"""
检查所有IDataSourcePlugin插件是否正确初始化initialized属性
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_plugin_init(file_path: str, class_name: str):
    """检查插件的__init__方法是否初始化了required属性"""
    print(f"\n检查: {file_path}")
    print(f"类名: {class_name}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有self.initialized赋值
        has_initialized = 'self.initialized' in content
        has_last_error = 'self.last_error' in content
        has_plugin_state = 'self.plugin_state' in content

        print(f"  self.initialized: {'OK' if has_initialized else 'FAIL'}")
        print(f"  self.last_error: {'OK' if has_last_error else 'FAIL'}")
        print(f"  self.plugin_state: {'OK' if has_plugin_state else 'FAIL'}")

        return has_initialized and has_last_error and has_plugin_state

    except Exception as e:
        print(f"  [ERROR] Check failed: {e}")
        return False


def main():
    plugins_to_check = [
        ("plugins/data_sources/stock/eastmoney_plugin.py", "EastMoneyStockPlugin"),
        ("plugins/data_sources/stock/akshare_plugin.py", "AKSharePlugin"),
        ("plugins/data_sources/stock/tongdaxin_plugin.py", "TongdaxinStockPlugin"),
        ("plugins/data_sources/eastmoney_unified_plugin.py", "EastmoneyUnifiedPlugin"),
        ("plugins/data_sources/stock_international/yahoo_finance_plugin.py", "YahooFinanceDataSourcePlugin"),
        ("plugins/data_sources/fundamental_data_plugins/eastmoney_fundamental_plugin.py", "EastmoneyFundamentalPlugin"),
    ]

    print("=" * 80)
    print("检查所有IDataSourcePlugin插件的必需属性")
    print("=" * 80)

    results = {}
    for file_path, class_name in plugins_to_check:
        results[class_name] = check_plugin_init(file_path, class_name)

    print("\n" + "=" * 80)
    print("检查结果摘要")
    print("=" * 80)

    ok_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - ok_count

    for class_name, ok in results.items():
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {class_name}: {status}")

    print(f"\n总计: {ok_count}/{len(results)} 通过, {failed_count} 失败")

    if failed_count > 0:
        print("\n[WARNING] Plugins that need fixing:")
        for class_name, ok in results.items():
            if not ok:
                print(f"  - {class_name}")
        print("\n建议修复方法:")
        print("在 __init__ 方法中添加:")
        print("  self.initialized = False")
        print("  self.last_error = None")
        print("  self.plugin_state = PluginState.UNINITIALIZED")

    return failed_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
