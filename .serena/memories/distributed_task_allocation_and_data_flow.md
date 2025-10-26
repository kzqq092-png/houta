# 分布式任务分配与数据保存流程

## 核心修复（2025-10-23）

### 问题诊断
**原问题：**
1. ❌ 单任务单节点：每个任务只分配给一个节点，无法并行
2. ❌ 数据不保存：节点执行完任务后数据丢失
3. ❌ 无法利用多节点：100只股票的任务不会拆分

### 修复方案

#### 1. 任务拆分与并行执行（core/services/distributed_http_bridge.py）

**关键方法：**
- `_execute_distributed()`: 智能判断任务是否可拆分
- `_execute_split_task()`: 将股票列表拆分到多个节点并行执行
- `_execute_on_specific_node()`: 在指定节点执行子任务

**拆分逻辑：**
```python
# 如果有多只股票且有多个节点，进行拆分
if len(symbols) > 1 and len(available_nodes) > 1:
    symbols_per_node = math.ceil(len(symbols) / len(available_nodes))
    # 为每个节点创建子任务
    for i, node in enumerate(available_nodes):
        sub_symbols = symbols[start_idx:end_idx]
        # 并行执行所有子任务
        results = await asyncio.gather(*sub_tasks)
```

#### 2. 数据收集与保存流程

**节点侧（distributed_node/task_executor.py）：**
```python
# 执行数据导入任务
def _execute_data_import():
    # 1. 获取真实数据
    kdata = provider.get_real_kdata(...)
    
    # 2. 转换为可序列化格式
    serializable_data = combined_data.to_dict('records')
    
    # 3. 返回给主系统（不在节点保存）
    return {
        "kdata": serializable_data,
        "imported_count": count
    }
```

**主系统侧（core/services/distributed_http_bridge.py）：**
```python
# 分布式执行
async def _execute_split_task():
    # 1. 并行执行所有节点任务
    results = await asyncio.gather(*sub_tasks)
    
    # 2. 收集所有节点返回的数据
    all_kdata = []
    for result in results:
        node_kdata = result.result.get("kdata", [])
        all_kdata.extend(node_kdata)
    
    # 3. 主系统统一保存
    combined_data = pd.DataFrame(all_kdata)
    asset_manager.store_standardized_data(
        data=combined_data,
        asset_type=asset_type,
        data_type=DataType.HISTORICAL_KLINE
    )
```

**本地执行（fallback）：**
```python
async def _execute_locally():
    # 执行任务
    result = await executor.execute_task(...)
    
    # 同样需要保存到主系统数据库
    if task_type == "data_import":
        kdata = result.result.get("kdata", [])
        asset_manager.store_standardized_data(...)
```

### 执行流程图

```
用户触发导入任务（100只股票）
    ↓
DistributedHttpBridge.execute_task()
    ↓
检查是否有可用节点
    ↓
   是 → _execute_distributed()
    ↓       ↓
    |    检查是否可拆分（多只股票 + 多个节点）
    |       ↓
    |      是 → _execute_split_task()
    |       ↓
    |    拆分任务：
    |    - 节点1: 0-33只股票
    |    - 节点2: 34-66只股票
    |    - 节点3: 67-99只股票
    |       ↓
    |    并行发送HTTP请求到各节点
    |       ↓
    |    [节点1]          [节点2]          [节点3]
    |    task_executor    task_executor    task_executor
    |    ↓                ↓                ↓
    |    获取数据         获取数据         获取数据
    |    返回33只数据     返回33只数据     返回34只数据
    |       ↓                ↓                ↓
    |       └────────────────┴────────────────┘
    |                       ↓
    |                主系统收集所有数据
    |                       ↓
    |                pd.DataFrame(all_kdata)
    |                       ↓
    |                asset_manager.store_standardized_data()
    |                       ↓
    |                保存到主系统DuckDB
    ↓
   否 → _execute_locally()
    ↓
本地TaskExecutor执行
    ↓
保存到主系统DuckDB
```

### 关键优势

1. **真正并行**：多节点同时处理不同股票
2. **统一存储**：所有数据都保存到主系统数据库
3. **容错机制**：单节点失败不影响其他节点
4. **本地fallback**：无节点时自动降级到本地执行

### 文件修改清单

- `core/services/distributed_http_bridge.py`:
  - 新增 `_execute_distributed()`
  - 新增 `_execute_split_task()`
  - 新增 `_execute_on_specific_node()`
  - 修改 `_execute_locally()` 增加数据保存

- `distributed_node/task_executor.py`:
  - 修改 `_execute_data_import()` 返回序列化数据
