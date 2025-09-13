# 连接池和会话复用优化方案

## 优化背景

根据用户建议，频繁创建HTTP请求可能被API服务商限制或封杀。为了解决这个问题，我们实施了连接池化技术和会话复用机制。

## 实施的优化措施

### 1. HTTP连接池化

**AKShare插件 (`akshare_stock_plugin.py`)**:
```python
# 连接池配置
adapter = HTTPAdapter(
    pool_connections=10,    # 连接池大小
    pool_maxsize=20,       # 最大连接数
    pool_block=False       # 非阻塞模式
)
```

**东方财富插件 (`eastmoney_stock_plugin.py`)**:
```python
# 相同的连接池配置
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    pool_block=False
)
```

### 2. 会话复用机制

- **单例会话**: 每个插件实例维护一个HTTP会话
- **连接保持**: 使用 `Connection: keep-alive` 头
- **自动重试**: 配置urllib3的重试策略

### 3. 智能速率限制

**AKShare插件**:
- 默认请求间隔: 100ms
- 可配置的速率限制延迟
- 自动计算等待时间

**东方财富插件**:
- 默认请求间隔: 100ms  
- 轻量级速率控制
- 防止请求过于频繁

### 4. 优化的请求头

模拟真实浏览器行为，减少被检测为机器人的概率：

```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://quote.eastmoney.com/'
}
```

## 技术优势

### 1. 减少连接开销
- **重用TCP连接**: 避免每次请求都建立新连接
- **减少握手时间**: 保持连接活跃状态
- **降低服务器负载**: 减少对API服务器的连接压力

### 2. 提高请求效率
- **连接池管理**: 自动管理连接的创建和销毁
- **并发控制**: 控制并发连接数，避免过载
- **智能重试**: HTTP层面的自动重试机制

### 3. 防止被封禁
- **速率限制**: 控制请求频率
- **真实请求头**: 模拟浏览器行为
- **连接复用**: 减少连接建立频率

### 4. 错误恢复
- **自动重试**: 针对特定HTTP状态码重试
- **指数退避**: 逐渐增加重试间隔
- **优雅降级**: 连接失败时的备选方案

## 配置参数

### AKShare插件配置
```python
{
    'timeout': 30,              # 请求超时时间
    'max_retries': 3,           # 最大重试次数
    'cache_duration': 3600,     # 缓存持续时间
    'pool_connections': 10,     # 连接池大小
    'pool_maxsize': 20,         # 最大连接数
    'rate_limit_delay': 0.1     # 请求间隔（秒）
}
```

### 东方财富插件配置
```python
{
    'timeout': 30,              # 请求超时时间
    'max_retries': 3,           # 最大重试次数
    '_rate_limit_delay': 0.1    # 请求间隔（秒）
}
```

## 使用示例

### 获取数据时自动应用优化
```python
# AKShare插件
plugin = AKShareStockPlugin()
plugin.connect()

# 使用优化的重试机制
df = plugin._execute_with_session_retry(
    lambda: ak.stock_individual_fund_flow_rank(indicator="今日"),
    "个股资金流数据"
)
```

### 东方财富插件自动速率限制
```python
# 东方财富插件  
plugin = EastMoneyStockPlugin()
plugin.connect()  # 自动创建优化的会话

# 所有请求自动应用速率限制
response = plugin._make_request_with_limit('GET', url, params=params)
```

## 监控和调优

### 1. 性能监控
- 监控请求响应时间
- 跟踪连接池使用情况
- 记录重试和失败率

### 2. 动态调整
- 根据API响应调整请求间隔
- 监控429状态码（Too Many Requests）
- 自适应重试策略

### 3. 日志记录
```python
self.logger.info("创建HTTP会话连接池")
self.logger.debug(f"速率限制：等待 {sleep_time:.2f} 秒")
self.logger.warning(f"网络连接失败，{delay}秒后重试: {e}")
```

## 最佳实践

1. **合理设置连接池大小**: 根据实际并发需求调整
2. **监控API使用配额**: 避免超出服务商限制
3. **实施优雅降级**: 在连接失败时提供备选方案
4. **定期清理资源**: 正确关闭会话和连接
5. **响应式调整**: 根据API响应动态调整策略

## 注意事项

1. **服务商政策**: 遵守各API服务商的使用条款
2. **资源清理**: 程序退出时正确关闭会话
3. **异常处理**: 处理连接池耗尽等边界情况
4. **配置调优**: 根据实际环境调整参数

---

**实施日期**: $(date)  
**优化范围**: AKShare插件、东方财富插件  
**预期效果**: 提高性能、减少封禁风险、增强稳定性
