# unified_best_quality_kline视图逻辑说明

## 视图目的
自动从多个数据源中选择最优质量的K线数据，提供统一的高质量数据访问接口。

## 核心逻辑

### 1. 质量评分机制
```sql
CASE 
    WHEN dqm.quality_score IS NOT NULL THEN dqm.quality_score  -- 优先使用实际评分
    WHEN hkd.data_source = 'tushare' THEN 65.0                -- Tushare默认65分
    WHEN hkd.data_source = 'tongdaxin' THEN 60.0              -- 通达信默认60分
    WHEN hkd.data_source = 'akshare' THEN 55.0                -- AKShare默认55分
    ELSE 50.0                                                  -- 其他数据源默认50分
END as effective_quality_score
```

### 2. 选择规则
按以下优先级排序（降序）：
1. **有效质量分数**（实际评分 > 默认评分）
2. **更新时间**（最新的优先）

### 3. 数据源默认优先级
- **Tushare (65分)**: 专业金融数据平台，数据质量最高
- **通达信 (60分)**: 本地数据，实时性好，数据较稳定
- **AKShare (55分)**: 开源数据，免费但可能存在质量波动

## 数据流

### 质量评分写入
由 `AssetAwareUnifiedDataManager._store_quality_to_database()` 写入：
- 文件：`core/services/asset_aware_unified_data_manager.py:422-436`
- 触发时机：数据查询请求完成后
- 评分内容：质量分数、缺失数、完整性等

### 视图查询
任何查询 `unified_best_quality_kline` 的代码都会自动获得最优数据：
```sql
SELECT * FROM unified_best_quality_kline
WHERE symbol = '000001' AND DATE(timestamp) = '2024-01-15'
```

## 实际验证结果（2025-10-23）

### 测试1：无质量评分
- 数据源：tongdaxin(10.80), akshare(10.82), tushare(10.79)
- **选择结果：tushare（默认65分最高）**
- 状态：✅ 正确

### 测试2：有质量评分
- akshare添加80分实际评分
- **选择结果：akshare（实际80分）**
- 状态：✅ 正确，实际评分覆盖默认值

## 依赖表结构

### historical_kline_data
- 主键：(symbol, data_source, timestamp, frequency)
- 支持多数据源并存

### data_quality_monitor
- 主键：monitor_id
- 关联条件：symbol + data_source + DATE(timestamp)
- 当前状态：表已创建，需要数据查询流程填充

## 已修复问题（本次会话）

### 问题1：表和视图未创建
- **原因**：`_create_asset_database`只跳过了一个视图，导致循环逻辑错误
- **修复**：区分表和视图，分两步创建（501-520行）
- **状态**：✅ 已修复并验证

### 问题2：视图逻辑过于简单
- **原因**：原逻辑只依赖`updated_at`，无法真正选择高质量数据
- **修复**：添加数据源默认评分，实现fallback机制（248-277行）
- **状态**：✅ 已修复并通过测试

## 未来优化建议

1. **自动质量评估**：导入数据时自动评估并写入质量分数
2. **动态权重调整**：根据历史表现动态调整数据源默认评分
3. **异常检测**：标记质量异常的数据，避免被选中
4. **多维度评分**：除了质量分，考虑数据新鲜度、完整性等

## 相关文件
- `core/asset_database_manager.py:239-277` - 视图定义
- `core/asset_database_manager.py:497-520` - 视图创建逻辑
- `core/services/asset_aware_unified_data_manager.py:415-438` - 质量评分写入
