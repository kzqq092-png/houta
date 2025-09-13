#!/usr/bin/env python3
"""
测试自动创建数据库、表结构和索引的功能

用于验证按数据源分离存储的自动创建机制
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.database.data_source_separated_storage import (
    get_separated_storage_manager, 
    DataSourceIsolationLevel
)
from core.database.table_manager import TableType


def test_auto_creation():
    """测试自动创建数据库、表和索引功能"""
    logger.info("=== 开始测试自动创建数据库功能 ===")
    
    # 获取存储管理器
    storage_manager = get_separated_storage_manager()
    
    # 测试数据源列表
    test_sources = [
        "examples.akshare_stock_plugin",
        "examples.eastmoney_stock_plugin", 
        "examples.tongdaxin_stock_plugin"
    ]
    
    # 生成测试K线数据
    def generate_test_kline_data(symbol: str, days: int = 30) -> pd.DataFrame:
        """生成测试K线数据"""
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=days),
            end=datetime.now(),
            freq='D'
        )
        
        # 生成模拟价格数据
        import numpy as np
        np.random.seed(42)  # 固定随机种子
        
        base_price = 10.0
        prices = []
        current_price = base_price
        
        for _ in dates:
            # 模拟价格波动
            change = np.random.normal(0, 0.02)  # 2%的标准差
            current_price *= (1 + change)
            prices.append(current_price)
        
        # 创建OHLCV数据
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            open_price = close * (1 + np.random.normal(0, 0.01))
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.01)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.01)))
            volume = int(np.random.uniform(1000000, 10000000))
            
            data.append({
                'datetime': date,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume,
                'amount': round(volume * close, 2)
            })
        
        return pd.DataFrame(data)
    
    # 测试每个数据源
    for source_id in test_sources:
        logger.info(f"--- 测试数据源: {source_id} ---")
        
        try:
            # 生成测试数据
            test_symbols = ['000001', '000002', '600000']
            
            for symbol in test_symbols:
                logger.info(f"测试保存 {symbol} 的数据到 {source_id}")
                
                # 生成测试K线数据
                kline_data = generate_test_kline_data(symbol, days=10)
                
                # 保存数据（这会自动创建数据库、表和索引）
                success = storage_manager.save_data_to_source(
                    plugin_id=source_id,
                    table_type=TableType.KLINE_DATA,
                    data=kline_data,
                    symbol=symbol,
                    period='daily',
                    upsert=True
                )
                
                if success:
                    logger.success(f"✅ {symbol} 数据保存成功到 {source_id}")
                else:
                    logger.error(f"❌ {symbol} 数据保存失败到 {source_id}")
                
                # 验证数据是否正确保存
                saved_data = storage_manager.query_data_from_source(
                    plugin_id=source_id,
                    table_type=TableType.KLINE_DATA,
                    symbol=symbol,
                    limit=5
                )
                
                if saved_data is not None and len(saved_data) > 0:
                    logger.info(f"验证成功: 从 {source_id} 查询到 {len(saved_data)} 条 {symbol} 数据")
                else:
                    logger.warning(f"验证失败: 从 {source_id} 未查询到 {symbol} 数据")
            
        except Exception as e:
            logger.error(f"测试数据源 {source_id} 时发生异常: {e}")
    
    # 显示数据源统计信息
    logger.info("=== 数据源统计信息 ===")
    available_sources = storage_manager.list_available_data_sources()
    
    for source_info in available_sources:
        plugin_id = source_info['plugin_id']
        logger.info(f"数据源: {plugin_id}")
        logger.info(f"  - 数据库路径: {source_info['database_path']}")
        logger.info(f"  - 隔离级别: {source_info['isolation_level']}")
        
        # 获取详细统计
        stats = storage_manager.get_data_source_statistics(plugin_id)
        if stats:
            logger.info(f"  - 数据库大小: {stats.get('database_size_mb', 0):.2f} MB")
            logger.info(f"  - 表数量: {stats.get('table_count', 0)}")
            logger.info(f"  - 记录数量: {stats.get('record_count', 0)}")
    
    # 检查实际创建的文件
    logger.info("=== 检查创建的数据库文件 ===")
    db_base_dir = Path("db/datasource_separated")
    if db_base_dir.exists():
        for db_file in db_base_dir.glob("*.duckdb"):
            file_size = db_file.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"数据库文件: {db_file.name} ({file_size:.2f} MB)")
    else:
        logger.warning("数据库目录不存在")
    
    logger.info("=== 测试完成 ===")


if __name__ == "__main__":
    test_auto_creation()
