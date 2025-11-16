# DatabaseWriterThread 实现说明

## 概述

为解决K线数据下载过程中的DuckDB并发写入死锁问题，实施了**单线程数据库写入器（DatabaseWriterThread）**方案。

## 问题描述

### 原始问题
- K线数据下载任务在处理 `max_workers` 数量的股票后停滞
- 数据库未保存任何数据
- 日志显示进程在批量写入时卡死

### 根本原因
1. **多线程并发写入竞争**：多个工作线程同时尝试写入DuckDB
2. **DuckDB单写入者限制**：DuckDB虽支持多读，但同一时刻只允许一个写入者
3. **锁竞争导致死锁**：多个线程在Python锁和DuckDB内部锁上相互等待

## 解决方案

### 架构设计

```
┌─────────────────────────────────────────────────┐
│         工作线程池 (ThreadPoolExecutor)          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │
│  │线程1 │  │线程2 │  │线程3 │  │线程4 │        │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘        │
│     │         │         │         │             │
│     └─────────┴─────────┴─────────┘             │
│                 │                                │
│                 ▼                                │
│     ┌───────────────────────┐                   │
│     │  无锁队列 (Queue)      │                   │
│     │   WriteTask 对象      │                   │
│     └───────────┬───────────┘                   │
│                 │                                │
│                 ▼                                │
│     ┌───────────────────────┐                   │
│     │ DatabaseWriterThread  │                   │
│     │   (单线程写入)         │                   │
│     │                       │                   │
│     │  1. 从队列取任务       │                   │
│     │  2. 合并相同buffer_key │                   │
│     │  3. 串行写入DuckDB    │                   │
│     └───────────┬───────────┘                   │
│                 │                                │
│                 ▼                                │
│        ┌────────────────┐                       │
│        │   DuckDB       │                       │
│        └────────────────┘                       │
└─────────────────────────────────────────────────┘
```

### 核心组件

#### 1. WriteTask 数据类
```python
@dataclass
class WriteTask:
    buffer_key: str          # 缓冲区键（asset_type_task_id）
    data: pd.DataFrame       # 待写入数据（副本）
    asset_type: Any          # 资产类型
    data_type: Any           # 数据类型
    priority: int = 0        # 优先级（暂未使用）
```

#### 2. DatabaseWriterThread 线程类

**主要特性：**
- 单线程运行，完全避免并发写入
- 使用无锁队列 `Queue.Queue` 接收写入任务
- 自动合并相同 `buffer_key` 的数据批量写入
- 优雅关闭机制，确保队列清空

**关键方法：**
- `put_write_task()`: 放入写入任务到队列
- `run()`: 主循环，消费队列并写入
- `_write_task_to_database()`: 执行单个任务写入
- `_flush_buffer_key()`: 刷新指定buffer的合并数据
- `stop()`: 停止线程并等待队列清空
- `get_stats()`: 获取统计信息

#### 3. 修改点

**`DataImportExecutionEngine.__init__`**
```python
# 初始化并启动DatabaseWriterThread
self.db_writer_thread = DatabaseWriterThread()
self.db_writer_thread.start()
```

**`_save_kdata_to_database`**
```python
# 创建写入任务
write_task = WriteTask(
    buffer_key=f"{asset_type.value}_{task_config.task_id}",
    data=kdata.copy(),
    asset_type=asset_type,
    data_type=DataType.HISTORICAL_KLINE
)

# 放入队列
success = self.db_writer_thread.put_write_task(write_task, timeout=10.0)
```

**任务结束 finally 块**
```python
# 等待队列清空
if hasattr(self, 'db_writer_thread'):
    queue_size = self.db_writer_thread.write_queue.qsize()
    if queue_size > 0:
        logger.info(f"等待队列清空: {queue_size}个任务")
        # 最多等待30秒
        start_time = time.time()
        while self.db_writer_thread.write_queue.qsize() > 0 and (time.time() - start_time) < 30:
            time.sleep(0.5)
```

**引擎清理 cleanup()**
```python
# 停止DatabaseWriterThread
if hasattr(self, 'db_writer_thread'):
    self.db_writer_thread.stop(wait=True, timeout=30.0)
    stats = self.db_writer_thread.get_stats()
    logger.info(f"DatabaseWriterThread统计: {stats}")
```

### 性能优化

#### 1. 数据库索引优化

在 `AssetSeparatedDatabaseManager._create_table_indexes()` 中添加了与 `ON CONFLICT` 字段完全匹配的复合索引：

```python
# K线数据表
CREATE INDEX IF NOT EXISTS idx_{table_name}_conflict_key 
ON {table_name}(symbol, data_source, timestamp, frequency)

# 实时行情表
CREATE INDEX IF NOT EXISTS idx_{table_name}_conflict_key 
ON {table_name}(symbol, timestamp)
```

**优势：**
- 加速 UPSERT 操作的冲突检测
- 减少 ON CONFLICT 子句的查询时间
- 预期性能提升 30-50%

#### 2. 批量合并策略

**合并逻辑：**
- 相同 `buffer_key` 的数据先放入内存缓冲区
- 达到阈值（5个DataFrame）或队列空闲时批量写入
- 使用 `pd.concat()` 合并多个 DataFrame

**优势：**
- 减少数据库写入次数
- 降低事务开销
- 提高吞吐量

### UI监控

#### 新增队列监控面板

在"K线下载情况"面板中新增：

1. **写入队列**: 显示队列当前大小和峰值
   - 绿色：正常（< 200）
   - 橙色：警告（200-500）
   - 红色：阻塞（> 500）

2. **合并缓冲**: 显示内存中待合并的buffer数量

3. **已写入数**: 显示总写入次数和失败次数

**实现：**
- `RealtimeWriteMonitoringWidget.update_queue_stats()`: 更新UI
- `DataImportExecutionEngine.get_database_writer_stats()`: 获取统计
- 每1秒自动刷新

## 数据一致性保证

### 机制

1. **数据副本**：每个 `WriteTask` 包含 DataFrame 的副本
   ```python
   data=kdata.copy()  # 防止后续修改影响
   ```

2. **串行写入**：单线程确保写入顺序
   - 相同 `buffer_key` 的任务按入队顺序处理
   - 无并发冲突

3. **合并原子性**：
   - `_merge_lock` 保护合并缓冲区
   - 批量合并后一次性写入
   - 全部成功或全部回滚

4. **优雅关闭**：
   - 任务结束时等待队列清空
   - 引擎cleanup时刷新所有缓冲区
   - 确保无数据丢失

### 不会导致错乱的原因

- ✅ 每个任务的数据独立（副本）
- ✅ 队列保证先进先出
- ✅ 单线程写入无竞争
- ✅ buffer_key 隔离不同任务
- ✅ 合并缓冲区有锁保护

## 测试验证步骤

### 测试场景

启动 **7个股票** 的K线数据下载任务，验证：

1. ✅ 所有任务完成（无卡死）
2. ✅ 数据全部保存到数据库
3. ✅ 数据完整性（行数、时间范围）
4. ✅ 无死锁或错误日志

### 操作步骤

1. **启动应用**
   ```bash
   cd hikyuu-ui
   python main.py
   ```

2. **配置任务**
   - 数据源：HIkyuu
   - 资产类型：股票
   - 频率：日线
   - 股票代码：输入7个股票（如：000001、000002、600000、600036、000858、601318、600519）
   - 工作线程数：4

3. **监控指标**
   - 观察"K线下载情况"面板
   - 写入队列大小变化
   - 已写入数持续增长
   - 任务进度到100%

4. **验证数据库**
   ```python
   from core.asset_database_manager import AssetSeparatedDatabaseManager
   manager = AssetSeparatedDatabaseManager()
   
   # 查询每个股票的数据量
   for symbol in ['000001', '000002', '600000', '600036', '000858', '601318', '600519']:
       conn = manager.get_connection(AssetType.STOCK)
       result = conn.execute(f"""
           SELECT COUNT(*) as count, MIN(timestamp) as start, MAX(timestamp) as end
           FROM kline_data
           WHERE symbol = '{symbol}'
       """).fetchone()
       print(f"{symbol}: {result[0]} 条记录, 范围: {result[1]} ~ {result[2]}")
   ```

5. **检查日志**
   - 搜索 `✅ 批量刷新成功` 或 `✅ [写入线程] 写入成功`
   - 无 `❌` 错误标记
   - 无 `死锁` 或 `timeout` 关键词

### 预期结果

- 所有7个股票下载完成
- 数据库包含所有股票的K线数据
- 队列最终清空（队列大小=0）
- 无错误日志

## 回滚方案（如需）

如果新方案出现问题，可恢复旧方案：

1. 注释掉 `DatabaseWriterThread` 的初始化
2. 恢复 `_save_kdata_to_database` 中的旧逻辑（直接调用 `_write_data_immediately` 或 `_add_to_batch_buffer`）
3. 取消注释 `finally` 块中的 `flush_all_buffers()`

## 总结

### 关键改进

1. ✅ **解决死锁**：单线程写入完全消除并发竞争
2. ✅ **性能优化**：批量合并 + 索引优化
3. ✅ **可观测性**：实时队列监控
4. ✅ **数据一致性**：副本 + 串行 + 原子合并

### 技术亮点

- 队列解耦：工作线程与数据库写入分离
- 无锁设计：使用 `Queue.Queue` 的内置线程安全
- 智能合并：减少数据库I/O
- 优雅降级：队列满时阻塞而非丢弃

### 未来改进（待办）

- [ ] 动态调整合并阈值（根据队列深度）
- [ ] 优先级队列（紧急数据优先写入）
- [ ] 写入性能指标（TPS、延迟）
- [ ] 异常重试机制（失败任务重新入队）

---

**版本**: 1.0  
**日期**: 2025-11-08  
**作者**: FactorWeave-Quant团队

