#!/usr/bin/env python3
"""
简化的数据库自动创建测试

只测试基本的数据库和表创建功能
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


def simple_test():
    """简化测试"""
    print("=== 开始简化测试 ===")
    
    # 清理旧的数据库文件
    db_dir = Path("tools/db/datasource_separated")
    if db_dir.exists():
        import shutil
        shutil.rmtree(db_dir)
        print("清理旧的数据库文件")
    
    # 获取存储管理器
    storage_manager = get_separated_storage_manager()
    print("存储管理器初始化完成")
    
    # 生成简单测试数据
    test_data = pd.DataFrame([
        {
            'datetime': datetime.now() - timedelta(days=2),
            'open': 10.0,
            'high': 10.5,
            'low': 9.8,
            'close': 10.2,
            'volume': 1000000,
            'amount': 10200000.0
        },
        {
            'datetime': datetime.now() - timedelta(days=1),
            'open': 10.2,
            'high': 10.8,
            'low': 10.0,
            'close': 10.5,
            'volume': 1200000,
            'amount': 12600000.0
        }
    ])
    
    # 测试数据源
    test_source = "examples.akshare_stock_plugin"
    test_symbol = "000001"
    
    print(f"测试数据源: {test_source}")
    print(f"测试股票: {test_symbol}")
    print(f"测试数据条数: {len(test_data)}")
    
    # 保存数据
    success = storage_manager.save_data_to_source(
        plugin_id=test_source,
        table_type=TableType.KLINE_DATA,
        data=test_data,
        symbol=test_symbol,
        period='daily',
        upsert=True
    )
    
    if success:
        print("✅ 数据保存成功!")
        
        # 验证数据
        saved_data = storage_manager.query_data_from_source(
            plugin_id=test_source,
            table_type=TableType.KLINE_DATA,
            symbol=test_symbol,
            limit=10
        )
        
        if saved_data is not None and len(saved_data) > 0:
            print(f"✅ 数据验证成功! 查询到 {len(saved_data)} 条记录")
            print(saved_data.head())
        else:
            print("❌ 数据验证失败! 未查询到数据")
        
        # 检查数据库文件
        db_files = list(Path("tools/db/datasource_separated").glob("*.duckdb"))
        print(f"创建的数据库文件数量: {len(db_files)}")
        for db_file in db_files:
            file_size = db_file.stat().st_size / (1024 * 1024)  # MB
            print(f"  - {db_file.name}: {file_size:.2f} MB")
            
    else:
        print("❌ 数据保存失败!")
    
    print("=== 测试完成 ===")


if __name__ == "__main__":
    simple_test()
