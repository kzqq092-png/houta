# 数据库架构迁移分析

## 旧架构 vs 新架构

### 旧架构（已废弃）
- **表名**: `stock_kline`
- **设计**: 所有字段混合在一张表中
- **问题**: 数据冗余、无法支持多数据源、缺少元数据分离

### 新架构（当前使用）
- **主表1**: `historical_kline_data` - 存储K线历史数据
  - 主键: (symbol, data_source, timestamp, frequency)
  - 支持多数据源并存
  
- **主表2**: `asset_metadata` - 存储资产元数据
  - 主键: symbol
  - 包含: name, market, asset_type, listing_status等
  
- **视图**: `unified_best_quality_kline` - 自动选择最优质量K线数据

## 需要清理的文件

从代码搜索结果发现以下文件仍在使用旧架构：

1. **临时测试脚本**（可直接删除）:
   - `check_stock_kline_schema.py`
   - `migrate_database_to_new_schema.py`
   - `check_database_schema.py`
   
2. **测试文件**（需要更新）:
   - `regression_test_after_migration.py`
   - `quick_migration_verification.py`
   
3. **工具文件**（需要更新）:
   - `scripts/test_kline_import_with_new_fields.py`
   
4. **其他引用**（需要确认）:
   - `core/ai/data_anomaly_detector.py` - 仅作为示例字符串
   - `core/database/duckdb_connection_pool.py` - 仅作为示例字符串
   - `gui/workflows/simplified_import_workflow.py` - 模板ID（不影响）

## 关键点

1. **AssetSeparatedDatabaseManager** 已完全使用新架构
2. **UnifiedDataImportEngine** 已完全使用新架构
3. 没有业务代码在使用旧架构，只有测试脚本和示例代码

## 迁移已完成

数据库已成功从旧架构迁移到新架构，验证脚本确认：
- `asset_metadata`: 30条记录
- `historical_kline_data`: 7500条记录
