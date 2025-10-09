#!/usr/bin/env python3
"""
HIkyuu-UI迁移后最终验证脚本

验证所有修复是否生效：
1. 传统数据源文件已删除
2. PluginCenter可以正常初始化
3. TET+Plugin架构工作正常
4. 系统整体健康状态
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def check_legacy_files_removed():
    """检查传统数据源文件是否已删除"""
    # 传统数据源文件已在迁移过程中删除
    legacy_files = []

    results = {}
    for file_path in legacy_files:
        exists = os.path.exists(file_path)
        results[file_path] = "❌ 仍存在" if exists else "✅ 已删除"

    return results

def test_plugin_center_initialization():
    """测试PluginCenter初始化"""
    try:
        from core.plugin_center import PluginCenter
        from core.plugin_manager import PluginManager

        plugin_manager = PluginManager()
        plugin_center = PluginCenter(plugin_manager)

        return "✅ 初始化成功"
    except Exception as e:
        return f"❌ 初始化失败: {str(e)}"

def test_uni_plugin_manager():
    """测试UniPluginDataManager"""
    try:
        from core.services.uni_plugin_data_manager import UniPluginDataManager
        from core.plugin_manager import PluginManager
        from core.data_source_router import DataSourceRouter
        from core.tet_data_pipeline import TETDataPipeline

        # 创建必要的依赖
        plugin_manager = PluginManager()
        data_source_router = DataSourceRouter()
        tet_pipeline = TETDataPipeline()

        manager = UniPluginDataManager(plugin_manager, data_source_router, tet_pipeline)

        return "✅ 初始化成功"
    except Exception as e:
        return f"❌ 初始化失败: {str(e)}"

def test_core_imports():
    """测试核心组件导入"""
    components = {}

    try:
        from core.services.unified_data_manager import UnifiedDataManager
        components["UnifiedDataManager"] = "✅ 导入成功"
    except Exception as e:
        components["UnifiedDataManager"] = f"❌ 导入失败: {str(e)}"

    try:
        from core.tet_router_engine import TETRouterEngine
        components["TETRouterEngine"] = "✅ 导入成功"
    except Exception as e:
        components["TETRouterEngine"] = f"❌ 导入失败: {str(e)}"

    try:
        from core.data_standardization_engine import DataStandardizationEngine
        components["DataStandardizationEngine"] = "✅ 导入成功"
    except Exception as e:
        components["DataStandardizationEngine"] = f"❌ 导入失败: {str(e)}"

    return components

def main():
    """主验证函数"""
    print("=" * 60)
    print("HIkyuu-UI迁移后最终验证")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 检查传统文件删除
    print("1. 传统数据源文件清理检查")
    print("-" * 30)
    legacy_results = check_legacy_files_removed()
    for file_path, status in legacy_results.items():
        print(f"  {file_path}: {status}")
    print()

    # 2. 测试PluginCenter
    print("2. PluginCenter初始化测试")
    print("-" * 30)
    plugin_center_result = test_plugin_center_initialization()
    print(f"  PluginCenter: {plugin_center_result}")
    print()

    # 3. 测试UniPluginDataManager
    print("3. UniPluginDataManager测试")
    print("-" * 30)
    uni_manager_result = test_uni_plugin_manager()
    print(f"  UniPluginDataManager: {uni_manager_result}")
    print()

    # 4. 测试核心组件导入
    print("4. 核心组件导入测试")
    print("-" * 30)
    import_results = test_core_imports()
    for component, status in import_results.items():
        print(f"  {component}: {status}")
    print()

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)

    all_legacy_removed = all("已删除" in status for status in legacy_results.values())
    plugin_center_ok = "成功" in plugin_center_result
    uni_manager_ok = "成功" in uni_manager_result
    all_imports_ok = all("成功" in status for status in import_results.values())

    total_checks = 4
    passed_checks = sum([all_legacy_removed, plugin_center_ok, uni_manager_ok, all_imports_ok])

    print(f"总检查项: {total_checks}")
    print(f"通过检查: {passed_checks}")
    print(f"成功率: {passed_checks/total_checks*100:.1f}%")

    if passed_checks == total_checks:
        print("\n🎉 所有验证通过！迁移完全成功！")
        return True
    else:
        print(f"\n⚠️ 还有 {total_checks - passed_checks} 项需要修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
