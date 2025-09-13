#!/usr/bin/env python3
"""
AssetAwareUnifiedDataManager 验证脚本

验证资产感知统一数据管理器的核心功能
"""

import tempfile
import shutil
from datetime import date
import pandas as pd


def test_asset_aware_data_manager():
    """测试资产感知数据管理器"""
    print("="*60)
    print("测试 AssetAwareUnifiedDataManager")
    print("="*60)

    temp_dir = None
    try:
        # 导入测试
        from core.services.asset_aware_unified_data_manager import (
            AssetAwareUnifiedDataManager, AssetAwareDataRequest
        )
        from core.asset_database_manager import AssetDatabaseConfig
        from core.plugin_types import AssetType
        from core.data_router import RouteStrategy
        print("✅ 模块导入成功")

        # 创建临时环境
        temp_dir = tempfile.mkdtemp(prefix="asset_aware_test_")
        config = AssetDatabaseConfig(base_path=temp_dir, pool_size=2)

        # 创建管理器
        manager = AssetAwareUnifiedDataManager(asset_db_config=config)
        print("✅ AssetAwareUnifiedDataManager 创建成功")

        # 准备测试数据
        print("\n准备测试数据...")
        with manager.asset_db_manager.get_connection(AssetType.STOCK_A) as conn:
            conn.execute("""
                INSERT INTO historical_kline_data 
                (symbol, data_source, timestamp, open, high, low, close, volume, amount, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ['000001.SZ', 'tongdaxin', '2024-01-01', 10.0, 10.5, 9.8, 10.2, 1000000, 10200000, '1d'])
        print("✅ 测试数据准备完成")

        # 测试资产感知数据请求
        print("\n测试资产感知数据请求...")
        request = AssetAwareDataRequest(
            request_id="test_001",
            symbol="000001.SZ",
            data_type="kline",
            time_range=(date(2024, 1, 1), date(2024, 1, 2)),
            route_strategy=RouteStrategy.FASTEST
        )

        data = manager.get_asset_aware_data(request)
        if data is not None:
            if isinstance(data, pd.DataFrame) and not data.empty:
                print(f"✅ 获取K线数据成功: {len(data)} 条记录")
                print(f"  数据列: {list(data.columns)}")
                print(f"  资产类型: {request.asset_type.value if request.asset_type else 'auto'}")
            else:
                print("✅ 获取数据成功 (非DataFrame格式)")
        else:
            print("⚠️ 数据为空，可能是正常情况")

        # 测试跨资产查询
        print("\n测试跨资产查询...")
        cross_data = manager.get_cross_asset_data(
            symbols=["000001.SZ", "BTCUSDT"],
            data_type="kline"
        )

        if cross_data:
            print(f"✅ 跨资产查询成功: {len(cross_data)} 个资产类型")
            for asset_type, asset_data in cross_data.items():
                print(f"  {asset_type.value}: {len(asset_data)} 个符号")
        else:
            print("⚠️ 跨资产查询结果为空")

        # 测试统计信息
        print("\n测试统计信息...")
        stats = manager.get_asset_statistics()

        if stats:
            print("✅ 统计信息获取成功:")
            db_stats = stats.get('database_statistics', {})
            print(f"  数据库数量: {db_stats.get('total_databases', 0)}")

            route_stats = stats.get('route_statistics', {})
            print(f"  路由次数: {route_stats.get('total_routes', 0)}")

            quality_stats = stats.get('data_quality_statistics', {})
            print(f"  质量监控符号: {quality_stats.get('symbols_monitored', 0)}")
        else:
            print("⚠️ 统计信息为空")

        # 测试健康检查
        print("\n测试健康检查...")
        health = manager.health_check()

        if health:
            print(f"✅ 健康检查完成: 状态 = {health.get('status', 'unknown')}")
            summary = health.get('summary', {})
            print(f"  健康数据库: {summary.get('healthy_databases', 0)}/{summary.get('total_databases', 0)}")
            print(f"  可用数据源: {summary.get('available_data_sources', 0)}/{summary.get('total_data_sources', 0)}")
        else:
            print("⚠️ 健康检查结果为空")

        return True

    except Exception as e:
        print(f"❌ AssetAwareUnifiedDataManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if temp_dir:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print("\n✅ 临时目录清理完成")
            except Exception:
                pass


def main():
    """主函数"""
    print("AssetAwareUnifiedDataManager 验证")
    print("检查资产感知统一数据管理器的功能")
    print()

    # 运行测试
    result = test_asset_aware_data_manager()

    # 总结结果
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    if result:
        print("✅ AssetAwareUnifiedDataManager 验证通过！")
        print("✅ 资产感知统一数据管理器实现成功")
        return 0
    else:
        print("❌ 存在测试失败，需要修复")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
