# data_quality_monitor表自动创建修复

## 问题描述
```
WARNING | core.importdata.import_execution_engine:_validate_imported_data:1260 - 
[质量评分写入] 写入000001质量评分失败: Catalog Error: Table with name data_quality_monitor does not exist!
```

## 根本原因
在写入数据质量评分到`data_quality_monitor`表之前，没有先确保表存在。当表被删除或首次使用时，会导致写入失败。

## 解决方案
在`core/importdata/import_execution_engine.py`的`_validate_imported_data`方法中，添加表存在检查和自动创建逻辑。

### 修复位置
**文件**: `core/importdata/import_execution_engine.py`  
**方法**: `_validate_imported_data`  
**行号**: ~1240-1260

### 修复内容
在写入质量评分数据前，添加以下逻辑：

```python
with asset_manager.get_connection(asset_type) as conn:
    # ✅ 确保data_quality_monitor表存在
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_a_data.data_quality_monitor (
                monitor_id VARCHAR PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                data_source VARCHAR NOT NULL,
                check_date DATE NOT NULL,
                quality_score DECIMAL(5,2),
                anomaly_count INTEGER DEFAULT 0,
                missing_count INTEGER DEFAULT 0,
                completeness_score DECIMAL(5,4),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.debug(f"[质量评分写入] data_quality_monitor表已确保存在")
    except Exception as table_error:
        logger.error(f"[质量评分写入] 创建data_quality_monitor表失败: {table_error}")
        continue
    
    # 继续写入数据...
```

## 修复效果

### Before ❌
- 表不存在时抛出`Catalog Error`
- 写入失败但不影响数据导入主流程
- 用户看到WARNING日志

### After ✅
- 自动创建表（如果不存在）
- 写入成功
- 表被删除后也能自动恢复
- DEBUG日志记录表创建状态

## 表结构
```sql
CREATE TABLE IF NOT EXISTS stock_a_data.data_quality_monitor (
    monitor_id VARCHAR PRIMARY KEY,      -- 监控ID (symbol_datasource_date)
    symbol VARCHAR NOT NULL,             -- 股票代码
    data_source VARCHAR NOT NULL,        -- 数据源
    check_date DATE NOT NULL,            -- 检查日期
    quality_score DECIMAL(5,2),          -- 质量评分 (0-100)
    anomaly_count INTEGER DEFAULT 0,     -- 异常数量
    missing_count INTEGER DEFAULT 0,     -- 缺失数量
    completeness_score DECIMAL(5,4),     -- 完整性评分 (0-1)
    details TEXT,                        -- 详细信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## 关键特性
1. **自愈能力**: 表被删除后自动重新创建
2. **优雅降级**: 表创建失败时跳过该symbol，继续处理其他symbol
3. **日志记录**: DEBUG级别记录表创建状态，ERROR级别记录失败

## 相关代码路径
- 质量评分计算: `_validate_imported_data` (Line ~1180-1210)
- 表自动创建: `_validate_imported_data` (Line ~1240-1260)
- 质量评分写入: `_validate_imported_data` (Line ~1264-1280)

## 测试验证
1. 删除`data_quality_monitor`表
2. 执行数据导入
3. 确认表自动创建
4. 确认质量评分成功写入
5. 确认无WARNING日志

## 相关记忆
- ValidationResult_参数修复_2025_10_23
- 数据库目录统一完成_2025_10_23
- db_models功能完整性检查_2025_10_23
