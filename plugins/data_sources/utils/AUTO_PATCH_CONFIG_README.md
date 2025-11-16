# Auto Patch Requests 配置说明

## 概述

`auto_patch_requests.py` 自动为所有HTTP请求添加反爬虫功能和连接池优化，解决 `RemoteDisconnected` 等网络连接问题。

## RemoteDisconnected错误原因

**错误信息**：`('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`

**根本原因**：
1. **服务器主动关闭连接**：服务器识别为爬虫或请求频繁
2. **网络不稳定**：连接在传输过程中断开
3. **请求超时**：服务器处理时间过长
4. **连接未复用**：每次请求新建连接，被服务器识别为异常
5. **缺少Keep-Alive**：连接不保持活跃状态

## 解决方案

### 1. 连接池（Connection Pool）

使用全局Session对象复用连接，减少建立新连接的次数：

```python
# 启用连接池（默认）
AUTO_PATCH_CONFIG = {
    'enable_connection_pool': True,    # 启用连接池
    'pool_connections': 10,             # 连接池大小
    'pool_maxsize': 20,                 # 最大连接数
}
```

**优势**：
- 复用TCP连接，减少握手开销
- 减少服务器连接数
- 自动管理连接生命周期
- 支持Keep-Alive

### 2. 自动重试策略

urllib3的Retry机制自动重试失败的请求：

```python
AUTO_PATCH_CONFIG = {
    'max_retries': 3,                  # 最大重试次数
    'retry_backoff_factor': 1.0,       # 指数退避因子（1秒、2秒、4秒...）
}
```

**重试场景**：
- HTTP状态码：429（请求过多）、500、502、503、504
- 连接错误：RemoteDisconnected、ConnectionError
- 超时错误：ReadTimeout、ConnectTimeout

### 3. 超时控制

自动为所有请求添加超时，防止连接挂起：

```python
AUTO_PATCH_CONFIG = {
    'timeout': 30,  # 默认超时30秒
}
```

### 4. 日志级别控制

控制连接错误日志级别，避免日志刷屏：

```python
AUTO_PATCH_CONFIG = {
    'log_level': 'debug',  # 可选：debug, info, warning, error
}
```

推荐设置：
- **开发环境**：`'debug'` - 查看所有连接问题
- **生产环境**：`'warning'` - 只记录重要错误

## 完整配置示例

```python
# 在应用启动时修改配置
from plugins.data_sources.utils.auto_patch_requests import AUTO_PATCH_CONFIG

# 生产环境配置（推荐）
AUTO_PATCH_CONFIG.update({
    'enable_connection_pool': True,      # 启用连接池
    'pool_connections': 20,              # 增加连接池大小
    'pool_maxsize': 40,                  # 增加最大连接数
    'max_retries': 5,                    # 增加重试次数
    'timeout': 60,                       # 增加超时时间
    'log_level': 'warning',              # 只记录警告和错误
    'retry_backoff_factor': 2.0,         # 更激进的退避策略
})

# 低延迟环境配置
AUTO_PATCH_CONFIG.update({
    'enable_connection_pool': True,
    'pool_connections': 50,              # 大连接池
    'pool_maxsize': 100,
    'max_retries': 2,                    # 减少重试
    'timeout': 10,                       # 短超时
    'log_level': 'error',
    'retry_backoff_factor': 0.5,
})

# 不稳定网络环境配置
AUTO_PATCH_CONFIG.update({
    'enable_connection_pool': True,
    'pool_connections': 5,               # 小连接池
    'pool_maxsize': 10,
    'max_retries': 10,                   # 大量重试
    'timeout': 120,                      # 长超时
    'log_level': 'info',
    'retry_backoff_factor': 3.0,         # 激进退避
})
```

## 使用建议

### 1. 根据网络环境调整

- **稳定内网**：小连接池、短超时、少重试
- **公网API**：中等配置（默认）
- **不稳定网络**：大重试次数、长超时

### 2. 根据请求频率调整

- **高频请求**（>100 req/s）：大连接池（50+）
- **中频请求**（10-100 req/s）：中等连接池（20）
- **低频请求**（<10 req/s）：小连接池（10，默认）

### 3. 监控和优化

查看日志中的连接池信息：
```
✅ 创建全局Session对象（连接池:20, 最大重试:5, 超时:60秒）
```

如果经常看到 "连接错误重试失败"，考虑：
1. 增加 `max_retries`
2. 增加 `timeout`
3. 增加 `retry_backoff_factor`
4. 检查网络或目标服务器状态

## 技术细节

### 连接池工作原理

1. **首次请求**：建立TCP连接，加入连接池
2. **后续请求**：复用连接池中的连接
3. **Keep-Alive**：保持连接活跃，避免被服务器关闭
4. **自动清理**：空闲连接自动清理

### 重试策略

```
尝试1: 立即重试
尝试2: 等待 1 * backoff_factor 秒后重试
尝试3: 等待 2 * backoff_factor 秒后重试
尝试4: 等待 4 * backoff_factor 秒后重试
...
```

### 线程安全

全局Session对象是线程安全的，可以在多线程环境中使用。

## 常见问题

### Q: 为什么还是出现 RemoteDisconnected？

A: 这是正常的网络波动。关键看：
1. 是否最终重试成功？（看后续日志）
2. 失败率是否很高？（如果<5%是正常的）
3. 考虑增加重试次数或延长超时

### Q: 连接池会占用太多资源吗？

A: 不会。默认配置（10个连接）只占用很少的内存和端口。只有在高并发场景才需要增加。

### Q: 可以禁用连接池吗？

A: 可以，但不推荐：
```python
AUTO_PATCH_CONFIG['enable_connection_pool'] = False
```

### Q: 如何查看连接池状态？

A: 目前没有直接的API。可以通过日志观察重试频率来间接判断。

## 更新日志

- **2024-11-07**：添加连接池和自动重试策略
- **2024-11-07**：添加可配置的日志级别
- **2024-11-07**：添加超时和Keep-Alive支持

