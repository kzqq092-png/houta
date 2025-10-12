#!/usr/bin/env python3
"""
DuckDB初始化诊断脚本
用于追踪和诊断DuckDB初始化过程中的{"result": "error"}输出

作者: FactorWeave-Quant团队
"""

import sys
import os
from pathlib import Path
import json
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def diagnose_duckdb_initialization():
    """诊断DuckDB初始化过程"""
    print("=" * 80)
    print("DuckDB初始化诊断工具")
    print("=" * 80)
    print()

    results = {
        "database_files": {},
        "connection_test": {},
        "query_test": {},
        "recommendations": []
    }

    # 1. 检查数据库文件
    print("1. 检查数据库文件...")
    print("-" * 60)

    db_paths = [
        "db/kline_stock.duckdb",
        "db/factorweave_system.sqlite",
        "db/datasource_separated/"
    ]

    for db_path in db_paths:
        full_path = project_root / db_path
        if full_path.exists():
            if full_path.is_file():
                size = full_path.stat().st_size
                print(f"✅ {db_path}: 存在 ({size:,} bytes)")
                results["database_files"][db_path] = {"exists": True, "size": size}
            else:
                files = list(full_path.glob("*.duckdb"))
                print(f"✅ {db_path}: 目录存在 ({len(files)} 个数据库文件)")
                results["database_files"][db_path] = {
                    "exists": True,
                    "is_directory": True,
                    "file_count": len(files)
                }
        else:
            print(f"❌ {db_path}: 不存在")
            results["database_files"][db_path] = {"exists": False}

    print()

    # 2. 测试DuckDB连接
    print("2. 测试DuckDB连接...")
    print("-" * 60)

    try:
        from core.database.duckdb_manager import DuckDBConnectionManager, get_connection_manager

        print("正在初始化DuckDB连接管理器...")
        print("注意: 如果检测到数据库损坏，系统将自动创建备份并重建")
        manager = get_connection_manager()
        print("✅ DuckDB连接管理器初始化成功")
        results["connection_test"]["manager_init"] = "success"

        # 测试获取连接
        kline_db_path = str(project_root / "db" / "kline_stock.duckdb")
        print(f"正在测试连接到: {kline_db_path}")

        with manager.get_connection(kline_db_path) as conn:
            print("✅ 成功获取数据库连接")
            results["connection_test"]["connection_acquired"] = "success"

            # 测试简单查询
            try:
                result = conn.execute("SELECT 1 as test").fetchone()
                if result and result[0] == 1:
                    print("✅ 基本查询测试通过")
                    results["query_test"]["basic_query"] = "success"
                else:
                    print("⚠️ 基本查询返回意外结果")
                    results["query_test"]["basic_query"] = "unexpected_result"
            except Exception as e:
                print(f"❌ 基本查询失败: {e}")
                results["query_test"]["basic_query"] = f"error: {str(e)}"

            # 检查是否有表
            try:
                tables_result = conn.execute("SHOW TABLES").fetchall()
                table_count = len(tables_result)
                print(f"📊 数据库中有 {table_count} 个表")
                results["query_test"]["table_count"] = table_count

                if table_count == 0:
                    print("⚠️ 数据库为空，可能需要导入数据")
                    results["recommendations"].append("数据库为空，建议运行数据导入脚本")
                else:
                    print("表列表:")
                    for table in tables_result:
                        table_name = table[0]
                        count_result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                        row_count = count_result[0] if count_result else 0
                        print(f"  - {table_name}: {row_count:,} 条记录")

            except Exception as e:
                print(f"❌ 表查询失败: {e}")
                results["query_test"]["table_query"] = f"error: {str(e)}"
                results["recommendations"].append("无法查询表信息，可能需要重建数据库")

    except Exception as e:
        print(f"❌ DuckDB连接测试失败: {e}")
        logger.error(f"DuckDB连接测试失败: {e}")
        results["connection_test"]["manager_init"] = f"error: {str(e)}"
        results["recommendations"].append("DuckDB连接失败，请检查数据库文件完整性")

    print()

    # 3. 检查UnifiedDataManager初始化
    print("3. 检查UnifiedDataManager...")
    print("-" * 60)

    try:
        from core.services.unified_data_manager import UnifiedDataManager
        from core.events import get_event_bus
        from core.containers import get_service_container

        print("正在初始化UnifiedDataManager...")
        service_container = get_service_container()
        event_bus = get_event_bus()

        data_manager = UnifiedDataManager(service_container, event_bus)
        print("✅ UnifiedDataManager初始化成功")
        results["unified_data_manager"] = "success"

        # 测试DuckDB可用性
        if hasattr(data_manager, 'duckdb_available'):
            print(f"DuckDB可用性: {data_manager.duckdb_available}")
            results["unified_data_manager_duckdb"] = data_manager.duckdb_available

    except Exception as e:
        print(f"❌ UnifiedDataManager初始化失败: {e}")
        logger.error(f"UnifiedDataManager初始化失败: {e}")
        results["unified_data_manager"] = f"error: {str(e)}"
        results["recommendations"].append("UnifiedDataManager初始化失败，请检查依赖服务")

    print()

    # 4. 生成诊断报告
    print("=" * 80)
    print("诊断报告总结")
    print("=" * 80)

    # 保存结果到文件
    report_file = project_root / "logs" / "duckdb_diagnostic_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n详细报告已保存到: {report_file}")

    # 输出建议
    if results["recommendations"]:
        print("\n🔍 建议操作:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
    else:
        print("\n✅ 所有检查通过！")

    print()

    # 关于 {"result": "error"} 的说明
    print("=" * 80)
    print("关于 {\"result\": \"error\"} 输出的说明")
    print("=" * 80)
    print("""
该JSON输出未在核心代码中找到，可能来源：

1. **测试查询结果**: 可能是某个健康检查查询返回了error状态
   - 如果数据库为空，某些查询可能返回error
   - 这通常是正常的初始状态

2. **GUI组件验证**: 可能是UI层面的连接验证测试
   - 检查是否有弹出窗口或状态栏消息
   
3. **外部工具输出**: 可能是独立的诊断脚本输出
   - 检查是否有其他Python进程在运行

4. **插件系统**: 可能是某个插件的健康检查结果
   - 检查插件日志

**判断是否有问题的关键**:
- ✅ 如果应用程序正常启动并可以使用 → 可以忽略此消息
- ❌ 如果应用程序无法正常工作 → 需要进一步调查

**建议**:
1. 检查完整的启动日志，查找其他错误信息
2. 尝试执行一些基本操作，确认系统是否正常工作
3. 如果系统工作正常，可以安全地忽略此消息
4. 如果遇到功能问题，请提供完整的错误堆栈信息
""")

    return results


def main():
    """主函数"""
    try:
        # 确保日志目录存在
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # 运行诊断
        results = diagnose_duckdb_initialization()

        # 返回状态
        has_errors = any("error" in str(v).lower() for v in results.values() if isinstance(v, (str, dict)))
        return 0 if not has_errors else 1

    except Exception as e:
        logger.error(f"诊断脚本运行失败: {e}")
        print(f"\n❌ 诊断脚本运行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
