#!/usr/bin/env python3
"""测试表创建功能"""

import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.database.table_manager import TableType, TableSchemaRegistry, DynamicTableManager
    from core.database.data_source_separated_storage import DataSourceSeparatedStorageManager
    
    # 测试简单的表创建
    print("测试表创建功能...")
    
    # 1. 初始化Schema注册表
    registry = TableSchemaRegistry()
    print(f"Schema注册表初始化完成")
    
    # 2. 检查所有表类型
    all_types = list(TableType)
    print(f"发现 {len(all_types)} 种表类型:")
    
    for i, table_type in enumerate(all_types, 1):
        schema = registry.get_schema(table_type)
        status = "✅" if schema else "❌"
        column_count = len(schema.columns) if schema else 0
        index_count = len(schema.indexes) if schema else 0
        print(f"  {i:2d}. {status} {table_type.value:20s} | {column_count:2d}字段 {index_count:2d}索引")
    
    # 3. 测试表名生成
    print("\n测试表名生成...")
    table_manager = DynamicTableManager()
    
    for table_type in [TableType.KLINE_DATA, TableType.REAL_TIME_QUOTE, TableType.FUND_FLOW]:
        try:
            table_name = table_manager.generate_table_name(
                table_type=table_type,
                plugin_name="examples.test_plugin",
                period="daily" if table_type == TableType.KLINE_DATA else None
            )
            print(f"  ✅ {table_type.value}: {table_name}")
        except Exception as e:
            print(f"  ❌ {table_type.value}: {e}")
    
    # 4. 测试数据源分离存储
    print("\n测试数据源分离存储管理器...")
    try:
        storage_manager = DataSourceSeparatedStorageManager()
        print("  ✅ 数据源分离存储管理器初始化成功")
        
        # 测试配置获取
        config = storage_manager._get_storage_config("examples.test_plugin")
        print(f"  ✅ 存储配置获取成功: {config.plugin_name}")
        
    except Exception as e:
        print(f"  ❌ 数据源分离存储管理器初始化失败: {e}")
    
    print("\n🎉 基本功能测试完成")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
