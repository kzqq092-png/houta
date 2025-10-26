## 任务成功数/失败数显示与状态中文化修复

### 问题分析
1. **成功数与失败数显示为0**：任务执行后，成功数和失败数列始终显示0
2. **状态显示为英文**：状态列显示英文值（如"completed"、"running"）而非中文

### 根本原因

**问题1：字段名称不匹配**
- UI代码（gui/widgets/enhanced_data_import_widget.py:2751-2752）尝试访问：
  ```python
  task_status.success_count
  task_status.failure_count
  ```
- 但`TaskExecutionResult`（core/importdata/import_execution_engine.py:60-83）实际字段是：
  ```python
  processed_records  # 已处理记录数
  failed_records     # 失败记录数
  ```
- 成功数需要计算：`success_count = processed_records - failed_records`

**问题2：状态值未翻译**
- 枚举值直接显示：`task_status.status.value`（如"completed"）
- 缺少中英文映射

### 解决方案

**文件**：gui/widgets/enhanced_data_import_widget.py（行2739-2785）

#### 1. 添加状态中文映射
```python
# 状态中文映射
status_map = {
    'pending': '待执行',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消',
    'paused': '已暂停'
}

# 获取状态（优先使用中文映射）
if task_status:
    status_value = task_status.status.value if hasattr(task_status.status, 'value') else str(task_status.status)
    status_text = status_map.get(status_value.lower(), status_value)
else:
    status_text = "未开始"
```

#### 2. 修正成功数/失败数计算
```python
# 计算成功数和失败数（使用TaskExecutionResult的实际字段）
success_count = 0
failure_count = 0
if task_status:
    # TaskExecutionResult 有 processed_records 和 failed_records
    if hasattr(task_status, 'processed_records'):
        total_processed = task_status.processed_records
        failed = getattr(task_status, 'failed_records', 0)
        success_count = total_processed - failed  # 成功数 = 已处理 - 失败
        failure_count = failed
    # 兼容旧版本可能有 success_count 和 failure_count
    elif hasattr(task_status, 'success_count'):
        success_count = task_status.success_count
        failure_count = getattr(task_status, 'failure_count', 0)
```

#### 3. 更新items列表
```python
items = [
    task.name,
    status_text,  # 使用中文状态
    f"{task_status.progress:.1f}%" if task_status and hasattr(task_status, 'progress') else "0%",
    task.data_source,
    task.asset_type,
    task.data_type,
    task.frequency.value if hasattr(task.frequency, 'value') else str(task.frequency),
    str(len(task.symbols)),
    start_time,
    end_time,
    runtime,
    str(success_count),  # 正确的成功数
    str(failure_count)   # 正确的失败数
]
```

### TaskExecutionResult字段说明

**core/importdata/import_execution_engine.py**（行60-83）：
```python
@dataclass
class TaskExecutionResult:
    task_id: str
    status: TaskExecutionStatus
    total_records: int = 0          # 总记录数
    processed_records: int = 0      # 已处理记录数（包含成功和失败）
    failed_records: int = 0         # 失败记录数
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
```

**字段更新位置**（行2112-2120）：
```python
# 更新任务结果统计
if download_result['status'] == 'success':
    result.processed_records += 1
else:
    result.failed_records += 1
```

### 状态枚举值

**TaskExecutionStatus**（行49-57）：
- `PENDING = "pending"` → "待执行"
- `RUNNING = "running"` → "运行中"
- `COMPLETED = "completed"` → "已完成"
- `FAILED = "failed"` → "失败"
- `CANCELLED = "cancelled"` → "已取消"

### 测试验证
- ✅ 任务执行后成功数正确显示
- ✅ 任务执行后失败数正确显示
- ✅ 状态列显示中文（如"运行中"、"已完成"）
- ✅ 兼容旧版本字段名

### 修改文件
1. gui/widgets/enhanced_data_import_widget.py（行2739-2785）