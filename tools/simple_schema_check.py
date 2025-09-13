#!/usr/bin/env python3
"""简单的表结构检查"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.database.table_manager import TableType, TableSchemaRegistry
    
    print("📊 检查表结构定义...")
    
    # 列出所有表类型
    all_types = list(TableType)
    print(f"定义的表类型数量: {len(all_types)}")
    
    for i, table_type in enumerate(all_types, 1):
        print(f"{i:2d}. {table_type.value}")
    
    print("\n🔍 检查Schema注册...")
    
    # 初始化注册表
    registry = TableSchemaRegistry()
    
    # 检查每个表类型的Schema
    complete_count = 0
    for table_type in all_types:
        schema = registry.get_schema(table_type)
        if schema:
            print(f"✅ {table_type.value}: {len(schema.columns)}字段, {len(schema.indexes)}索引")
            complete_count += 1
        else:
            print(f"❌ {table_type.value}: Schema缺失")
    
    print(f"\n📋 总结: {complete_count}/{len(all_types)} 表类型有完整Schema")
    
    if complete_count == len(all_types):
        print("🎉 所有表结构定义完整！")
    else:
        print(f"⚠️ 还有 {len(all_types) - complete_count} 个表类型缺少Schema")

except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()
