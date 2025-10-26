## 通达信插件多进程数据下载修改

### 修改目标
修改通达信插件，使其支持多进程数据下载，提高数据下载效率。

### 修改内容

#### 1. 修改文件
**文件**: `core/importdata/unified_data_import_engine.py`
**方法**: `_import_kline_data()`

**文件**: `plugins/data_sources/stock/tongdaxin_plugin.py`
**方法**: `get_kline_data()`, `_ensure_connection()`, `__init__()`

#### 2. 核心修改

##### A. 多进程导入引擎
**原始逻辑**: 串行处理所有股票
**修改后逻辑**: 
- 自动检测股票数量，少于10只使用单进程
- 多于10只使用多进程并行处理
- 动态分配进程数（CPU核心数、股票数量、最大8个进程）
- 将股票列表分割成批次，每个进程处理一个批次

**关键实现**:
```python
# 多进程配置
max_workers = min(
    os.cpu_count() or 4,  # CPU核心数
    len(task_config.symbols),  # 股票数量
    8  # 最大进程数限制
)

# 使用ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=max_workers) as executor:
    future_to_batch = {
        executor.submit(self._process_symbol_batch, args): args['batch_id']
        for args in process_args
    }
```

##### B. 多进程连接池
**新增类**: `MultiprocessConnectionPool`
- 为每个进程提供独立的连接
- 线程安全的连接管理
- 自动连接创建和释放
- 连接池大小可配置

**关键特性**:
```python
class MultiprocessConnectionPool:
    def __init__(self, host: str, port: int, pool_size: int = 4):
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.connections = []
        self.lock = threading.Lock()
```

##### C. 通达信插件多进程支持
**新增配置**:
```python
'use_multiprocess': True,     # 是否使用多进程模式
'multiprocess_workers': 4     # 多进程工作进程数
```

**多进程友好连接**:
```python
def _get_multiprocess_friendly_client(self):
    """获取多进程友好的客户端连接"""
    client = TdxHq_API()
    if client.connect(self.host, self.port):
        return client
    return None
```

#### 3. 性能优化

##### A. 智能进程分配
- 根据CPU核心数和股票数量动态调整
- 避免过度创建进程导致的资源浪费
- 小批量数据自动降级为单进程模式

##### B. 连接池管理
- 每个进程独立的连接，避免连接冲突
- 自动连接重试机制
- 连接超时和错误处理

##### C. 数据同步
- 进程间结果聚合
- 进度更新同步
- 错误信息收集

#### 4. 错误处理

##### A. 进程级错误处理
- 单个进程失败不影响其他进程
- 详细的错误日志记录
- 失败重试机制

##### B. 连接级错误处理
- 连接超时处理
- 网络异常恢复
- 服务器切换支持

#### 5. 兼容性保证

##### A. 向后兼容
- 保留原有的单进程模式
- 配置开关控制多进程启用
- 渐进式升级支持

##### B. 配置灵活性
- 可配置进程数
- 可配置连接池大小
- 可配置超时时间

### 预期效果

1. **性能提升**: 多进程并行下载，理论上可提升2-8倍下载速度
2. **资源利用**: 充分利用多核CPU资源
3. **稳定性**: 单个进程失败不影响整体任务
4. **可扩展性**: 支持大规模股票数据下载
5. **用户体验**: 更快的批量数据导入

### 测试验证

创建了测试脚本 `test_tongdaxin_multiprocess.py` 用于验证：
- 多进程功能正常性
- 连接池工作状态
- 性能对比测试
- 错误处理验证

### 注意事项

1. **内存使用**: 多进程会增加内存使用量
2. **网络连接**: 需要足够的网络连接数支持
3. **服务器限制**: 注意通达信服务器的连接限制
4. **进程通信**: 使用进程安全的通信机制