# 数据库架构与资产元数据修复总结

## 核心架构

### 1. 分库存储策略
- **按资产类型分库**：每种资产类型使用独立的DuckDB数据库文件
  - `db/databases/stock_a/stock_a_data.duckdb` - A股数据
  - `db/databases/crypto/crypto_data.duckdb` - 加密货币
  - `db/databases/stock_us/stock_us_data.duckdb` - 美股
- **统一表结构**：所有资产库使用相同的标准表名
  - `historical_kline_data` - K线数据表
  - `asset_metadata` - 资产元数据表
  - `data_quality_monitor` - 数据质量监控表

### 2. 主键设计（支持多数据源、多频率）
```sql
PRIMARY KEY (symbol, data_source, timestamp, frequency)
```
这允许：
- 同一股票的不同数据源数据共存
- 同一股票的不同频率数据共存（1m, 5m, 1d等）
- 自动去重和更新

## 关键问题与修复

### 问题1: 表名生成逻辑错误
**原因**：生成`stock_a_kline`而不是`historical_kline_data`
**修复**：`_generate_table_name`直接返回统一表名

### 问题2: 字段名映射缺失
**原因**：数据用`datetime`，表结构用`timestamp`
**修复**：`_filter_dataframe_columns`自动映射字段名

### 问题3: 资产元数据不完整
**原因**：导入时直接用symbol作为name，未从插件获取真实信息
**修复**：新增`_extract_asset_metadata_from_kline`方法：
1. 从数据源插件的`get_stock_list()`获取完整信息
2. 包含真实的股票名称、行业、板块等
3. 优先使用插件数据，回退到推断或默认值

### 问题4: UI显示过多空列
**原因**：查询返回所有字段，包括NULL的industry/sector
**修复**：SQL查询优化，只返回核心有值的字段

## 数据流程

### 导入流程
1. 从插件获取K线数据
2. 标准化K线数据字段（datetime→timestamp）
3. 保存K线数据到`historical_kline_data`表
4. 从插件`get_stock_list()`获取资产完整信息
5. 保存资产元数据到`asset_metadata`表

### 查询流程
1. UI调用`UnifiedDataManager.get_stock_list()`
2. 查询`asset_metadata`表获取资产列表
3. 返回DataFrame包含code, name, market等字段
4. 查询K线数据时Join两表获取完整信息

## 修改的文件

1. `core/asset_database_manager.py`
   - `_generate_table_name()` - 使用统一表名
   - `_filter_dataframe_columns()` - 字段名映射
   - `_upsert_data()` - 正确的复合主键
   - `_create_asset_database()` - 视图创建修复

2. `core/importdata/unified_data_import_engine.py`
   - 新增`_extract_asset_metadata_from_kline()` - 从插件获取完整信息
   - `_import_kline_data()` - 使用新的元数据提取方法
   - `_import_kline_data_sync()` - 使用新的元数据提取方法

3. `core/services/unified_data_manager.py`
   - `_get_asset_list_from_duckdb()` - 优化SQL查询，减少空列显示
