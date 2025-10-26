"""
综合回归测试 - 插件迁移后的全面验证

测试范围:
1. 数据库系统测试
2. 插件系统测试
3. 数据管理器测试
4. UI组件基础测试
5. 核心服务测试
"""

from typing import List, Tuple
import traceback
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


# 测试统计
total_tests = 0
passed_tests = 0
failed_tests = 0
test_results: List[Tuple[str, bool, str]] = []


def test_assert(condition, test_name, error_msg=""):
    """测试断言"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1

    if condition:
        print(f"   PASS {test_name}")
        passed_tests += 1
        test_results.append((test_name, True, ""))
        return True
    else:
        print(f"   FAIL {test_name}")
        if error_msg:
            print(f"      Error: {error_msg}")
        failed_tests += 1
        test_results.append((test_name, False, error_msg))
        return False


print("=" * 80)
print(" Hikyuu-UI Comprehensive Regression Test Suite")
print("=" * 80)
print()

# ============================================================================
# Test 1: Database System
# ============================================================================
print("[1] Database System Tests")
print("-" * 80)

try:
    from core.database.factorweave_analytics_db import FactorWeaveAnalyticsDB
    from core.plugin_types import AssetType
    from core.asset_database_manager import AssetSeparatedDatabaseManager, AssetDatabaseConfig
    import duckdb

    # 1.1 Database file existence
    db_path = Path("db/databases/stock_cn/stock_a_data.duckdb")
    test_assert(db_path.exists(), "Database file exists", f"Path: {db_path}")

    # 1.2 Asset database manager initialization
    try:
        asset_db_manager = AssetSeparatedDatabaseManager()
        test_assert(True, "AssetSeparatedDatabaseManager initialization")
    except Exception as e:
        test_assert(False, "AssetSeparatedDatabaseManager initialization", str(e))

    # 1.3 Database path routing
    try:
        stock_a_path = asset_db_manager.get_database_path(AssetType.STOCK_A)
        test_assert(
            "stock_cn/stock_a_data.duckdb" in str(stock_a_path),
            "Database path routing for STOCK_A",
            f"Got: {stock_a_path}"
        )
    except Exception as e:
        test_assert(False, "Database path routing for STOCK_A", str(e))

    # 1.4 FactorWeave Analytics DB
    try:
        analytics_db = FactorWeaveAnalyticsDB()
        test_assert(True, "FactorWeaveAnalyticsDB initialization")
    except Exception as e:
        test_assert(False, "FactorWeaveAnalyticsDB initialization", str(e))

    print()
except Exception as e:
    print(f"   FAIL Database system test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 2: Plugin System
# ============================================================================
print("[2] Plugin System Tests")
print("-" * 80)

try:
    from core.plugin_manager import PluginManager
    from plugins.plugin_interface import IDataSourcePlugin, PluginState

    # 2.1 PluginManager initialization
    try:
        plugin_manager = PluginManager()
        test_assert(True, "PluginManager initialization")
    except Exception as e:
        test_assert(False, "PluginManager initialization", str(e))

    # 2.2 Load all plugins
    try:
        plugin_manager.load_all_plugins()
        test_assert(True, "Load all plugins")
    except Exception as e:
        test_assert(False, "Load all plugins", str(e))

    # 2.3 Verify new migrated plugins are loaded
    expected_plugins = [
        "data_sources.crypto.binance_plugin",
        "data_sources.crypto.okx_plugin",
        "data_sources.crypto.huobi_plugin",
        "data_sources.crypto.coinbase_plugin",
        "data_sources.crypto.crypto_universal_plugin",
        "data_sources.futures.wenhua_plugin",
    ]

    loaded_plugins = plugin_manager.get_all_plugins()
    loaded_plugin_ids = [p.plugin_id for p in loaded_plugins if hasattr(p, 'plugin_id')]

    for expected_id in expected_plugins:
        test_assert(
            expected_id in loaded_plugin_ids,
            f"Plugin loaded: {expected_id}"
        )

    # 2.4 Verify plugin attributes
    for plugin_id in expected_plugins:
        plugin = next((p for p in loaded_plugins if hasattr(p, 'plugin_id') and p.plugin_id == plugin_id), None)
        if plugin:
            test_assert(hasattr(plugin, 'plugin_state'), f"{plugin_id}: has plugin_state")
            test_assert(hasattr(plugin, 'initialized'), f"{plugin_id}: has initialized")
            test_assert(hasattr(plugin, 'name'), f"{plugin_id}: has name")
            test_assert(hasattr(plugin, 'version'), f"{plugin_id}: has version")

    print()
except Exception as e:
    print(f"   FAIL Plugin system test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 3: Data Manager System
# ============================================================================
print("[3] Data Manager System Tests")
print("-" * 80)

try:
    from core.services.unified_data_manager import UnifiedDataManager
    from core.services.service_container import ServiceContainer

    # 3.1 ServiceContainer
    try:
        service_container = ServiceContainer()
        test_assert(True, "ServiceContainer initialization")
    except Exception as e:
        test_assert(False, "ServiceContainer initialization", str(e))

    # Note: UnifiedDataManager requires full system initialization
    # which is tested in Phase 7 (main.py startup)
    print("   SKIP UnifiedDataManager tests (requires full system startup)")

    print()
except Exception as e:
    print(f"   FAIL Data manager test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 4: Plugin Discovery Mechanism
# ============================================================================
print("[4] Plugin Discovery Mechanism Tests")
print("-" * 80)

try:
    from plugins.data_sources import discover_plugins_by_category, get_all_plugins, PLUGIN_CATEGORIES

    # 4.1 Category discovery
    test_assert(len(PLUGIN_CATEGORIES) > 0, "Plugin categories defined", f"Found {len(PLUGIN_CATEGORIES)} categories")

    # 4.2 Discover crypto plugins
    crypto_plugins = discover_plugins_by_category("crypto")
    test_assert(
        len(crypto_plugins) >= 5,
        "Discover crypto plugins",
        f"Found {len(crypto_plugins)} plugins"
    )

    # 4.3 Get all plugins
    all_plugins = get_all_plugins()
    test_assert(
        len(all_plugins) > 0,
        "Get all plugins from discovery",
        f"Found {len(all_plugins)} categories"
    )

    print()
except Exception as e:
    print(f"   FAIL Plugin discovery test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 5: Plugin Template System
# ============================================================================
print("[5] Plugin Template System Tests")
print("-" * 80)

try:
    from plugins.data_sources.templates.base_plugin_template import BasePluginTemplate
    from plugins.data_sources.templates.http_api_plugin_template import HTTPAPIPluginTemplate
    from plugins.data_sources.templates.websocket_plugin_template import WebSocketPluginTemplate

    # 5.1 BasePluginTemplate
    test_assert(
        hasattr(BasePluginTemplate, 'initialize'),
        "BasePluginTemplate has initialize method"
    )
    test_assert(
        hasattr(BasePluginTemplate, '_do_connect'),
        "BasePluginTemplate has _do_connect method"
    )

    # 5.2 HTTPAPIPluginTemplate
    test_assert(
        hasattr(HTTPAPIPluginTemplate, '_get_default_config'),
        "HTTPAPIPluginTemplate has _get_default_config method"
    )
    test_assert(
        hasattr(HTTPAPIPluginTemplate, '_test_connection'),
        "HTTPAPIPluginTemplate has _test_connection method"
    )

    # 5.3 WebSocketPluginTemplate
    test_assert(
        hasattr(WebSocketPluginTemplate, '_manage_websocket_pool'),
        "WebSocketPluginTemplate has _manage_websocket_pool method"
    )

    print()
except Exception as e:
    print(f"   FAIL Plugin template test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 6: Core Utilities
# ============================================================================
print("[6] Core Utilities Tests")
print("-" * 80)

try:
    from core.asset_type_display import AssetTypeDisplay
    from utils.asset_type_identifier import AssetTypeIdentifier, get_asset_type_identifier

    # 6.1 AssetTypeDisplay
    display_stock_a = AssetTypeDisplay.get_display_name(AssetType.STOCK_A)
    test_assert(
        display_stock_a is not None,
        "AssetTypeDisplay.get_display_name",
        f"STOCK_A -> {display_stock_a}"
    )

    # 6.2 AssetTypeIdentifier
    try:
        identifier = get_asset_type_identifier()
        test_assert(True, "AssetTypeIdentifier singleton")
    except Exception as e:
        test_assert(False, "AssetTypeIdentifier singleton", str(e))

    print()
except Exception as e:
    print(f"   FAIL Core utilities test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Test 7: Data Source Extensions
# ============================================================================
print("[7] Data Source Extensions Tests")
print("-" * 80)

try:
    from core.data_source_extensions import DataSourcePluginAdapter, PluginInfo
    from plugins.plugin_interface import PluginType

    # 7.1 PluginInfo dataclass
    try:
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test Author",
            supported_asset_types=[AssetType.STOCK_A],
            supported_data_types=["kline"]
        )
        test_assert(True, "PluginInfo dataclass instantiation")
    except Exception as e:
        test_assert(False, "PluginInfo dataclass instantiation", str(e))

    print()
except Exception as e:
    print(f"   FAIL Data source extensions test suite: {e}")
    traceback.print_exc()
    print()

# ============================================================================
# Final Summary
# ============================================================================
print("=" * 80)
print(" Test Results Summary")
print("=" * 80)
print(f"Total Tests:  {total_tests}")
print(f"Passed:       {passed_tests} ({passed_tests/total_tests*100:.1f}%)" if total_tests > 0 else "N/A")
print(f"Failed:       {failed_tests} ({failed_tests/total_tests*100:.1f}%)" if total_tests > 0 else "N/A")
print()

if failed_tests > 0:
    print("Failed Tests:")
    print("-" * 80)
    for test_name, passed, error_msg in test_results:
        if not passed:
            print(f"  - {test_name}")
            if error_msg:
                print(f"    Error: {error_msg}")
    print()

print("=" * 80)
if failed_tests == 0:
    print(" REGRESSION TEST PASSED")
    print("=" * 80)
    sys.exit(0)
else:
    print(" REGRESSION TEST FAILED")
    print("=" * 80)
    sys.exit(1)
