# ValidationResult 参数修复记录

## 问题描述
数据质量验证失败，错误信息：
- `ValidationResult.__init__() got an unexpected keyword argument 'overall_score'`
- `Table with name data_quality_monitor does not exist! Did you mean "stock_a_data.data_quality_monitor"?`

## 根本原因
1. **ValidationResult类定义不匹配**: `core/data_validator.py`中定义的ValidationResult类参数与`core/importdata/import_execution_engine.py`中使用的参数不一致
2. **SQL表名缺少schema前缀**: 插入语句使用`data_quality_monitor`而不是`stock_a_data.data_quality_monitor`

## ValidationResult正确参数
根据`core/data_validator.py` (lines 31-41):
```python
@dataclass
class ValidationResult:
    is_valid: bool
    quality_score: float  # 0-100分
    quality_level: DataQuality
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    metrics: Dict[str, Any]
    validation_time: datetime
```

## 修复内容

### 1. 修复ValidationResult实例化 (4处)
- Line 1250-1259: 异常处理返回的ValidationResult
- Line 1271-1280: 数据为空返回的ValidationResult
- Line 1346-1363: 正常验证返回的ValidationResult
- Line 1368-1377: 创建验证结果失败返回的ValidationResult

**参数映射**:
- `overall_score` → `quality_score`
- `issues` → `errors`
- 新增 `warnings`, `suggestions`, `validation_time`
- 额外数据放入 `metrics` 字典

### 2. 修复SQL表名 (Line 1210)
```sql
-- 修改前
INSERT OR REPLACE INTO data_quality_monitor

-- 修改后
INSERT OR REPLACE INTO stock_a_data.data_quality_monitor
```

### 3. 修复ValidationResult属性访问 (2处)
- Line 1396-1411: `_handle_quality_issues`方法中使用`errors`和`warnings`替代`issues`
- Line 2237-2242: 验证完成日志中使用`quality_score`替代`overall_score`，使用`errors`替代`issues`

### 4. 增强日志记录
添加带标签的日志便于追踪:
- `[数据质量验证]` - 验证流程日志
- `[质量评分写入]` - DuckDB写入日志
- `[数据验证]` - 详细验证信息
- `[质量问题处理]` - 问题处理日志

包括:
- 任务ID、数据源、数据类型
- 记录数、质量评分
- symbol处理详情
- 空值率、重复率
- 异常堆栈信息

## 影响范围
- `core/importdata/import_execution_engine.py`: 主要修改文件
- 相关方法: `_validate_imported_data`, `_create_detailed_validation_result`, `_handle_quality_issues`

## 测试建议
1. 运行K线数据导入任务
2. 检查日志确认ValidationResult创建成功
3. 验证DuckDB中`stock_a_data.data_quality_monitor`表有数据
4. 确认`unified_best_quality_kline`视图能正常使用质量评分
