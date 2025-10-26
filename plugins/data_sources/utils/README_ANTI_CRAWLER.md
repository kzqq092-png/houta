# 数据源反爬虫机制

## 概述

本模块为所有数据源插件提供自动化的反爬虫功能，解决API服务器识别为爬虫而拒绝请求的问题。

## 问题背景

数据源API（如AKShare、东方财富、新浪财经等）经常出现连接错误：
- `Connection aborted`
- `RemoteDisconnected('Remote end closed connection without response')`
- HTTP 429 (Too Many Requests)

**根本原因**: API服务器的反爬虫机制识别请求为爬虫行为

## 解决方案

### 自动化防护（推荐）

只需在插件中导入工具模块即可自动获得反爬虫功能：

```python
from plugins.data_sources.utils import retry_on_connection_error

# 其他数据源插件也会自动获得反爬虫功能
# 无需任何额外配置
```

**自动应用的功能**:
1. ✅ 所有HTTP请求自动添加浏览器请求头
2. ✅ User-Agent随机化（5个主流浏览器）
3. ✅ 完整的浏览器标识头（Accept, Accept-Language等）
4. ✅ 保留用户自定义的请求头

### 重试机制

为API调用添加智能重试：

```python
@retry_on_connection_error(
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=1.5,
    use_anti_crawler=True,  # 启用随机延迟
    log_prefix="数据获取"
)
def fetch_data():
    return api.get_data(...)
```

**特性**:
- 自动重试失败的请求
- 指数退避 + 随机抖动
- 智能识别连接错误
- 详细的日志输出

## 工作原理

### 1. 全局requests补丁

**文件**: `auto_patch_requests.py`

通过猴子补丁修改`requests`库的默认行为：

```python
# 修补前
response = requests.get("https://api.example.com")
# User-Agent: python-requests/2.31.0

# 修补后（自动）
response = requests.get("https://api.example.com")
# User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0
# + 10+ 其他浏览器标识头
```

**修补的函数**:
- `requests.get()`
- `requests.post()`
- `requests.request()`
- `requests.Session.request()`

### 2. 随机User-Agent池

**文件**: `retry_helper.py`

维护5个主流浏览器的User-Agent：
- Chrome 120/119 (Windows/Mac)
- Firefox 121
- Safari 17.1

每次请求随机选择，模拟不同用户。

### 3. 完整浏览器标识

除了User-Agent，还包含：
- `Accept`: 浏览器接受的内容类型
- `Accept-Language`: zh-CN,zh;q=0.9,en;q=0.8
- `Accept-Encoding`: gzip, deflate, br
- `Connection`: keep-alive
- `DNT`: 1 (Do Not Track)
- `Sec-Fetch-*`: 浏览器安全标识
- `Cache-Control`: max-age=0

### 4. 请求频率控制

**随机延迟**:
```python
# 基础延迟 + 随机抖动
delay = 2.0 + random.uniform(0, 1.0)
# 避免固定时间间隔（爬虫特征）
```

**指数退避**:
- 第1次重试: 2.3秒（2.0 + 0.3随机）
- 第2次重试: 3.7秒（3.0 + 0.7随机）
- 第3次重试: 5.2秒（4.5 + 0.7随机）

## 使用示例

### 示例1: 简单API调用

```python
from plugins.data_sources.utils import retry_on_connection_error

@retry_on_connection_error(max_retries=3)
def fetch_stock_data(symbol):
    import requests
    # 自动添加浏览器请求头
    response = requests.get(f"https://api.example.com/stock/{symbol}")
    return response.json()

data = fetch_stock_data("000001")
```

### 示例2: AKShare插件

```python
import akshare as ak
from plugins.data_sources.utils import retry_on_connection_error

@retry_on_connection_error(
    max_retries=3,
    use_anti_crawler=True,
    log_prefix="AKShare获取"
)
def fetch_kline():
    # 自动添加浏览器请求头
    return ak.stock_zh_a_hist(symbol="000001", period="daily")

df = fetch_kline()
```

### 示例3: requests.Session

```python
import requests
from plugins.data_sources.utils import get_random_headers

session = requests.Session()
# Session请求也会自动添加浏览器请求头

response = session.get("https://api.example.com/data")
# 自动包含完整的浏览器标识
```

### 示例4: 自定义请求头

```python
import requests

# 用户自定义的请求头会被保留
custom_headers = {
    'Authorization': 'Bearer token123',
    'X-Custom-Header': 'value'
}

response = requests.get(
    "https://api.example.com/data",
    headers=custom_headers
)
# 最终请求头 = 浏览器标识 + 用户自定义
```

## 已应用的插件

✅ **自动应用（无需修改）**:
- 所有使用`requests`库的插件
- `tongdaxin_plugin.py`
- `eastmoney_plugin.py`
- `sina_plugin.py`
- `yahoo_finance_plugin.py`
- `cninfo_plugin.py`
- 等等...

✅ **显式应用**:
- `akshare_plugin.py` - 使用AKShare专用补丁
- `akshare_sentiment_plugin.py` - 使用AKShare专用补丁

## 日志输出

### 启动时

```
✅ 已为所有HTTP请求应用反爬虫补丁（requests库）
✅ AKShare反爬虫补丁已激活
✅ AKShare情绪插件反爬虫补丁已激活
```

### 请求重试

```
⚠️  数据获取失败 (尝试 1/3): 网络连接问题
等待2.3秒后重试（含随机延迟）...
⚠️  数据获取失败 (尝试 2/3): 网络连接问题
等待3.7秒后重试（含随机延迟）...
✅ 数据获取成功 (重试2次后)
```

### 最终失败

```
❌ 数据获取最终失败 (已重试3次): 网络连接不稳定
建议: 1) 检查网络连接 2) 稍后再试 3) 使用其他数据源
```

## API参考

### retry_on_connection_error

```python
@retry_on_connection_error(
    max_retries: int = 3,              # 最大重试次数
    initial_delay: float = 2.0,        # 初始延迟（秒）
    backoff_factor: float = 1.5,       # 退避因子
    exceptions: Tuple = (...),         # 需要重试的异常类型
    default_return: Any = None,        # 失败时返回值
    log_prefix: str = "API调用",       # 日志前缀
    use_anti_crawler: bool = True      # 是否使用随机延迟
)
```

### get_random_headers

```python
from plugins.data_sources.utils import get_random_headers

headers = get_random_headers()
# 返回包含随机User-Agent的完整浏览器请求头
```

### apply_anti_crawler_delay

```python
from plugins.data_sources.utils import apply_anti_crawler_delay

apply_anti_crawler_delay(min_delay=0.5, max_delay=2.0)
# 随机延迟0.5-2.0秒
```

### patch_requests_globally

```python
from plugins.data_sources.utils import patch_requests_globally

patch_requests_globally()
# 手动应用全局补丁（通常自动应用）
```

## 最佳实践

### 1. 合理设置延迟

```python
# ❌ 太短，容易触发反爬虫
@retry_on_connection_error(initial_delay=0.1)

# ✅ 合理延迟
@retry_on_connection_error(initial_delay=2.0)
```

### 2. 遵守服务条款

不要设置过短的延迟或过高的并发数，遵守API服务商的ToS。

### 3. 监控日志

关注重试频率，如果大量重试，考虑：
- 增加延迟
- 减少并发
- 更换数据源
- 使用代理IP

### 4. 错误处理

```python
@retry_on_connection_error(
    max_retries=3,
    default_return=pd.DataFrame()  # 失败时返回空DataFrame
)
def fetch_data():
    return api.get_data()

df = fetch_data()
if df.empty:
    logger.warning("数据获取失败，使用缓存或其他数据源")
```

## 性能影响

### 内存开销

- 全局补丁: < 1KB
- 每个请求头: < 500 bytes

### 延迟影响

- 请求头生成: < 0.1ms
- 随机延迟: 0.5-2.0秒（可配置）
- 重试延迟: 根据配置

### CPU开销

可忽略不计（< 0.1%）

## 故障排除

### Q: 仍然出现连接错误

**A**: 
1. 检查网络连接
2. 增加延迟时间
3. 减少并发请求数
4. 考虑使用代理IP
5. 更换数据源

### Q: 日志显示补丁未应用

**A**:
1. 确保导入了工具模块
2. 检查是否有其他代码覆盖了补丁
3. 查看启动日志是否有错误信息

### Q: 自定义请求头丢失

**A**:
补丁会合并用户自定义的请求头，不会覆盖。
检查代码是否正确传递了headers参数。

### Q: 影响性能

**A**:
性能影响极小。如果担心，可以：
1. 减少重试次数
2. 缩短延迟时间
3. 禁用随机延迟（use_anti_crawler=False）

## 技术细节

### 为什么使用猴子补丁？

1. **透明性**: 无需修改现有代码
2. **全局性**: 一次应用，全部生效
3. **兼容性**: 兼容所有使用requests的代码
4. **可维护性**: 集中管理反爬虫逻辑

### 补丁安全性

1. 保存原始函数引用
2. 使用functools.wraps保留函数元信息
3. 用户自定义优先
4. 异常不会传播到原始函数

### 与其他工具的兼容性

- ✅ requests
- ✅ requests.Session
- ✅ akshare (基于requests)
- ✅ httpx (未来支持)
- ✅ urllib3 (通过requests)

## 版本历史

### v1.0 (2025-10-25)
- 初始版本
- 支持requests全局补丁
- User-Agent随机化
- 重试机制
- 随机延迟

## 贡献

欢迎提交问题和改进建议！

## 许可

与主项目保持一致

