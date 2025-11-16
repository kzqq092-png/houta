# Phase 4: 数据库层和事件流验证

## 目标
验证事件系统的完整性，确保导入引擎、事件发布、服务层都正确集成，为UI增强做准备。

## 实施计划

### 4.1 事件流程验证

#### 4.1.1 WriteStartedEvent 验证
**目标**: 任务开始时，正确发布开始事件，包含完整的元数据

**验证点**:
- [ ] 事件发布时间点正确（在任务初始化后，循环开始前）
- [ ] 事件包含正确的 task_id, task_name, symbols, total_records
- [ ] 事件时间戳正确
- [ ] 事件能正确传递到 EventBus

**测试代码**:
```python
# 在导入开始时检查事件发布
started_event = WriteStartedEvent(...)
event_bus.publish(started_event)
# 验证事件被接收和处理
```

**验证方法**:
1. 添加日志监听器追踪事件
2. 检查事件处理器的任务统计
3. 验证时间戳准确性

#### 4.1.2 WriteProgressEvent 验证
**目标**: 每个符号写入完成后，正确发布进度事件

**验证点**:
- [ ] 进度计算正确（已完成/总数 × 100）
- [ ] 写入速度计算准确（总记录/耗时）
- [ ] 事件发布频率合理（不应过多也不应过少）
- [ ] ETA 计算正确（剩余/速度）

**测试场景**:
1. 小规模（5只股票）：验证基础功能
2. 中等规模（100只股票）：验证速度计算
3. 大规模（1000只股票）：验证性能和内存

#### 4.1.3 WriteCompletedEvent 验证
**目标**: 任务完成时，发布正确的完成事件

**验证点**:
- [ ] 包含最终统计信息（总符号数、成功数、失败数）
- [ ] 总耗时计算准确
- [ ] 平均写入速度计算正确
- [ ] 事件发布时间点正确（在所有数据写入后）

#### 4.1.4 WriteErrorEvent 验证
**目标**: 异常捕获时，正确发布错误事件

**验证点**:
- [ ] 捕获网络错误
- [ ] 捕获数据库错误
- [ ] 捕获数据格式错误
- [ ] 错误事件包含足够的调试信息

### 4.2 服务层验证

#### 4.2.1 RealtimeWriteService 验证
**目标**: 验证实时写入服务的核心功能

**验证点**:
- [ ] start_write() 正确初始化任务状态
- [ ] write_data() 正确调用 AssetSeparatedDatabaseManager
- [ ] 数据实际写入数据库
- [ ] 完成_write() 正确清理任务状态
- [ ] 异常处理正确

**测试方法**:
```python
# 1. 创建测试数据
test_data = pd.DataFrame({...})

# 2. 调用写入服务
service.start_write("test_task")
success = service.write_data("000001", test_data, "STOCK_A")
service.complete_write("test_task")

# 3. 验证数据库
# 检查数据是否实际写入
```

#### 4.2.2 WriteProgressService 验证
**目标**: 验证进度跟踪服务

**验证点**:
- [ ] start_tracking() 初始化进度
- [ ] update_progress() 计算正确的进度
- [ ] get_progress() 返回准确的统计
- [ ] complete_tracking() 返回最终统计

### 4.3 数据库层验证

#### 4.3.1 数据完整性验证
**目标**: 验证数据正确写入数据库

**验证点**:
- [ ] 所有列都正确写入
- [ ] 数据类型正确
- [ ] 没有丢失数据
- [ ] 没有重复数据

**测试**:
```python
# 导入小规模数据
# 查询数据库
result = asset_manager.query_data("STOCK_A", "000001")
# 验证行数、列数、数据内容
```

#### 4.3.2 幂等性验证
**目标**: 验证重复写入不会导致数据不一致

**测试**:
```python
# 第一次写入
write_data(symbol, data1)
# 验证行数
count1 = query_count(symbol)

# 第二次写入相同数据
write_data(symbol, data1)
# 验证行数相同或使用 upsert 逻辑
count2 = query_count(symbol)

assert count1 == count2 or 符合 upsert 预期
```

#### 4.3.3 并发写入验证
**目标**: 验证并发写入不会导致冲突

**测试**:
```python
# 多线程并发写入
# 验证最终数据一致性
```

### 4.4 导入引擎验证

#### 4.4.1 K线数据导入完整流程验证
**目标**: 验证 _import_kline_data 的完整工作流程

**测试步骤**:
1. 创建任务配置
2. 调用 _import_kline_data()
3. 验证事件发布序列：
   - WriteStartedEvent → 已发布 ✓
   - WriteProgressEvent → 每个符号发布 ✓
   - WriteCompletedEvent → 任务结束发布 ✓
4. 验证数据库中数据完整

**验证脚本**:
```python
# 创建任务
config = ImportTaskConfig(
    task_id="test_kline_001",
    symbols=["000001", "000002", "000003"],
    data_source="akshare",
    asset_type="STOCK_A",
    ...
)

# 执行导入
engine = DataImportExecutionEngine()
result = engine._import_kline_data(config, ...)

# 验证结果
assert result.status == TaskExecutionStatus.SUCCESS
assert result.processed_records > 0
# 检查数据库中的数据
```

#### 4.4.2 实时行情导入验证
**目标**: 验证 _import_realtime_data 正常工作

**验证点**:
- [ ] 串行下载正常
- [ ] 事件按序发布
- [ ] 数据正确写入
- [ ] 完成事件包含正确统计

#### 4.4.3 基本面数据导入验证
**目标**: 验证 _import_fundamental_data 正常工作

**验证点**:
- [ ] 处理缓慢数据正确
- [ ] 事件完整发布
- [ ] 数据格式转换正确

### 4.5 集成验证

#### 4.5.1 端到端流程验证
**目标**: 验证整个系统从导入到数据库的完整流程

**完整流程**:
1. UI 创建导入任务
2. 导入引擎开始执行
3. 发布 WriteStartedEvent
4. 循环处理每个符号
5. 发布 WriteProgressEvent
6. 实时写入数据
7. 发布完成事件
8. UI 接收并显示进度

#### 4.5.2 错误恢复验证
**目标**: 验证系统在各种错误情况下的表现

**测试场景**:
- [ ] 网络中断：验证错误事件和重试
- [ ] 数据库离线：验证错误处理和恢复
- [ ] 无效数据：验证数据验证
- [ ] 内存不足：验证内存管理

#### 4.5.3 性能验证
**目标**: 验证系统性能达到预期

**性能指标**:
- [ ] 写入速度 > 1000条/秒
- [ ] 事件处理延迟 < 50ms
- [ ] 内存稳定（不随符号数增加而增加）
- [ ] CPU 使用率合理

**测试方法**:
```python
import time
import psutil

# 获取基准性能
start_time = time.time()
total_records = 0

# 执行导入
result = engine._import_kline_data(config, ...)
total_records = result.total_processed_records

# 计算性能指标
duration = time.time() - start_time
speed = total_records / duration
print(f"写入速度: {speed:.0f} 条/秒")

# 检查内存
process = psutil.Process()
mem_info = process.memory_info()
print(f"内存使用: {mem_info.rss / 1024 / 1024:.0f} MB")
```

### 4.6 验证清单

**必须通过的验证**:
- [ ] 所有模块能正确导入
- [ ] 服务容器能正确解析服务
- [ ] 事件总线能正确发布和订阅事件
- [ ] 事件处理器能正确处理事件
- [ ] 导入引擎能发布完整的事件序列
- [ ] 数据正确写入数据库
- [ ] 性能达到预期目标

**建议的验证工具**:
1. `test_event_integration.py` - 基础集成测试
2. `test_realtime_write_events.py` - 完整事件流测试
3. 自定义数据库查询脚本 - 数据完整性验证
4. 性能测试脚本 - 性能验证

### 4.7 故障排查指南

如果验证失败：

1. **事件未发布**
   - 检查 EventBus 是否正确初始化
   - 检查 REALTIME_WRITE_AVAILABLE 标志
   - 查看日志中的警告信息

2. **事件未被处理**
   - 检查事件处理器是否注册
   - 检查 EventBus 订阅配置
   - 验证处理器逻辑

3. **数据未写入数据库**
   - 检查 AssetSeparatedDatabaseManager 初始化
   - 检查数据库权限
   - 查看数据库错误日志
   - 验证数据格式

4. **性能不达预期**
   - 检查数据库连接池
   - 检查并发度设置
   - 分析耗时操作

## 下一步行动

1. **立即执行**: 运行集成测试脚本
2. **手动测试**: 执行小规模数据导入
3. **数据验证**: 检查数据库中的数据
4. **性能测试**: 执行大规模导入测试
5. **进入 Phase 5**: UI 增强和完善
