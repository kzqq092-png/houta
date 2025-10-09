#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB股票列表获取优先级测试脚本
测试修复后的股票列表获取逻辑，验证DuckDB优先级
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_duckdb_stock_list_priority():
    """测试DuckDB股票列表获取优先级"""
    print("HIkyuu-UI DuckDB股票列表获取优先级测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        print("🧪 测试DuckDB股票列表获取优先级")
        print("=" * 50)

        # 1. 初始化日志系统
        print("📝 初始化日志系统...")
        from core.loguru_config import initialize_loguru
        initialize_loguru()

        # 2. 获取服务容器
        print("📦 正在获取服务容器...")
        from core.containers.unified_service_container import UnifiedServiceContainer
        container = UnifiedServiceContainer()

        # 3. 引导服务
        print("🚀 引导服务...")
        from core.services.service_bootstrap import bootstrap_services
        bootstrap_success = bootstrap_services()
        if not bootstrap_success:
            print("❌ 服务引导失败")
            return False

        # 4. 获取UnifiedDataManager
        print("🔍 正在获取统一数据管理器...")
        from core.services.unified_data_manager import UnifiedDataManager
        data_manager = container.resolve(UnifiedDataManager)

        if not data_manager:
            print("❌ 无法获取UnifiedDataManager")
            return False

        print("✅ UnifiedDataManager获取成功")

        # 5. 检查DuckDB可用性
        print("🗄️ 检查DuckDB可用性...")
        print(f"   DuckDB可用: {data_manager.duckdb_available}")
        print(f"   DuckDB操作器: {data_manager.duckdb_operations is not None}")

        # 6. 测试股票列表获取
        print("📊 测试股票列表获取...")

        # 测试不同市场的股票列表获取
        markets = [None, "SH", "SZ"]

        for market in markets:
            print(f"\n🔍 测试市场: {market if market else '全部市场'}")

            try:
                # 调用get_stock_list方法
                stock_list = data_manager.get_stock_list(market=market)

                if stock_list is not None and not stock_list.empty:
                    print(f"✅ 获取股票列表成功: {len(stock_list)} 只股票")
                    print(f"   数据来源: {'DuckDB数据库' if hasattr(stock_list, '_from_duckdb') else 'TET插件系统'}")

                    # 显示前5条数据
                    if len(stock_list) > 0:
                        print(" 前5条数据:")
                        for i, row in stock_list.head().iterrows():
                            code = row.get('code', row.get('symbol', 'N/A'))
                            name = row.get('name', 'N/A')
                            market_info = row.get('market', 'N/A')
                            print(f"     {code} - {name} ({market_info})")
                else:
                    print("⚠️ 未获取到股票列表数据")

            except Exception as e:
                print(f"❌ 获取股票列表失败: {e}")
                import traceback
                traceback.print_exc()

        # 7. 测试DuckDB直接查询
        print(f"\n🗄️ 测试DuckDB直接查询...")
        if data_manager.duckdb_operations:
            try:
                # 直接查询DuckDB
                result = data_manager.duckdb_operations.execute_query(
                    database_path="db/kline_stock.duckdb",
                    query="SELECT COUNT(*) as count FROM stock_basic WHERE status = 'L'",
                    params=[]
                )

                if result.success and result.data:
                    count = result.data[0]['count'] if result.data else 0
                    print(f"✅ DuckDB中有 {count} 只上市股票")
                else:
                    print("⚠️ DuckDB查询失败或无数据")

            except Exception as e:
                print(f"❌ DuckDB直接查询失败: {e}")

        print("\n🎉 测试完成！")
        return True

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_duckdb_stock_list_priority()
    if success:
        print("\n✅ DuckDB股票列表获取优先级测试成功")
    else:
        print("\n❌ DuckDB股票列表获取优先级测试失败")

    sys.exit(0 if success else 1)
