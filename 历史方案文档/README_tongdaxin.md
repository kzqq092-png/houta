# 通达信股票数据源插件

## 概述

通达信股票数据源插件是为 系统开发的数据源插件，基于 `pytdx` 库实现，提供A股市场的实时和历史数据获取功能。

## 功能特性

- ✅ **实时行情数据**: 获取股票实时价格、成交量、买卖盘等信息
- ✅ **历史K线数据**: 支持多种周期的K线数据（1分钟、5分钟、15分钟、30分钟、60分钟、日线、周线、月线）
- ✅ **股票列表**: 获取上海、深圳交易所的股票列表
- ✅ **自动服务器选择**: 自动选择响应最快的通达信服务器
- ✅ **连接管理**: 自动重连和故障转移
- ✅ **数据缓存**: 智能缓存机制，提高数据获取效率
- ✅ **健康检查**: 实时监控插件连接状态

## 支持的市场

- 上海证券交易所 (SH)
- 深圳证券交易所 (SZ)

## 支持的数据类型

- 历史K线数据 (HISTORICAL_KLINE)
- 实时行情数据 (REAL_TIME_QUOTE)
- 基本面数据 (FUNDAMENTAL)
- 逐笔成交数据 (TRADE_TICK)

## 安装依赖

在使用插件之前，请确保安装以下依赖库：

```bash
pip install pytdx pandas requests
```

## 配置参数

插件支持以下配置参数：

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| host | string | "119.147.212.81" | 通达信服务器地址 |
| port | integer | 7709 | 通达信服务器端口 |
| timeout | integer | 30 | 连接超时时间（秒） |
| max_retries | integer | 3 | 最大重试次数 |
| cache_duration | integer | 300 | 缓存持续时间（秒） |
| auto_select_server | boolean | true | 是否自动选择最快服务器 |
| use_local_data | boolean | false | 是否使用本地数据文件 |
| local_data_path | string | "" | 本地数据文件路径 |

## 使用方法

### 1. 基本使用

```python
from plugins.examples.tongdaxin_stock_plugin import create_plugin

# 创建插件实例
plugin = create_plugin()

# 配置参数
config = {
    'host': '119.147.212.81',
    'port': 7709,
    'timeout': 30,
    'auto_select_server': True
}

# 初始化插件
if plugin.initialize(config):
    print("插件初始化成功")
else:
    print("插件初始化失败")
```

### 2. 获取股票列表

```python
# 获取股票列表
stock_list = plugin.get_stock_list()
print(f"共获取 {len(stock_list)} 只股票")
print(stock_list.head())
```

### 3. 获取K线数据

```python
# 获取日K线数据
daily_data = plugin.get_kline_data('000001.SZ', period='daily', count=100)
print(f"获取日K线数据 {len(daily_data)} 条")

# 获取分钟K线数据
minute_data = plugin.get_kline_data('000001.SZ', period='5min', count=50)
print(f"获取5分钟K线数据 {len(minute_data)} 条")
```

### 4. 获取实时行情

```python
# 获取实时行情
symbols = ['000001.SZ', '600000.SH', '000002.SZ']
real_time_data = plugin.get_real_time_data(symbols)

for symbol, data in real_time_data.items():
    print(f"{symbol}: {data['name']} 价格: {data['price']}")
```

### 5. 使用通用接口

```python
# 获取历史K线数据
df = plugin.fetch_data('000001.SZ', 'historical_kline', period='daily', count=30)

# 获取实时行情数据
df = plugin.fetch_data('000001.SZ', 'real_time_quote', symbols=['000001.SZ'])
```

### 6. 健康检查

```python
# 执行健康检查
health_result = plugin.health_check()
print(f"健康状态: {health_result.is_healthy}")
print(f"响应时间: {health_result.response_time_ms}ms")
if health_result.error_message:
    print(f"错误信息: {health_result.error_message}")
```

### 7. 关闭插件

```python
# 关闭插件，释放资源
plugin.shutdown()
```

## 服务器列表

插件内置了多个通达信服务器地址，支持自动选择最快的服务器：

- 119.147.212.81:7709 (深圳主站)
- 114.80.63.12:7709 (上海主站)
- 119.147.171.206:7709 (深圳备用)
- 113.105.142.136:7709 (广州备用)
- 180.153.18.170:7709 (杭州备用)
- 180.153.18.171:7709 (杭州备用2)

## 数据格式

### K线数据格式

```python
# 返回的DataFrame包含以下列：
# - datetime: 时间索引
# - open: 开盘价
# - high: 最高价
# - low: 最低价
# - close: 收盘价
# - volume: 成交量
# - amount: 成交额（如果有）
```

### 实时行情数据格式

```python
{
    'symbol': '000001.SZ',
    'name': '平安银行',
    'price': 12.34,
    'open': 12.30,
    'high': 12.45,
    'low': 12.25,
    'pre_close': 12.28,
    'volume': 1234567,
    'amount': 15234567.89,
    'bid1': 12.33,
    'bid_vol1': 1000,
    'ask1': 12.34,
    'ask_vol1': 2000,
    'timestamp': '2024-01-01T09:30:00'
}
```

## 测试

运行测试脚本验证插件功能：

```bash
python test_tongdaxin_plugin.py
```

测试脚本将验证以下功能：
- 依赖库检查
- 插件初始化
- 健康检查
- 股票列表获取
- K线数据获取
- 实时行情获取
- 通用接口测试

## 错误处理

插件包含完善的错误处理机制：

1. **连接错误**: 自动重试和服务器切换
2. **数据错误**: 返回空DataFrame，记录错误日志
3. **超时错误**: 可配置的超时时间和重试机制
4. **依赖错误**: 检查必要的库是否安装

## 性能优化

1. **连接池**: 复用连接，减少连接开销
2. **数据缓存**: 智能缓存机制，避免重复请求
3. **服务器选择**: 自动选择最快的服务器
4. **并发控制**: 线程安全的连接管理

## 注意事项

1. 通达信服务器可能有访问频率限制，建议合理控制请求频率
2. 部分服务器可能在特定时间段不可用，插件会自动切换到可用服务器
3. 实时数据的准确性取决于通达信服务器的数据质量
4. 建议在交易时间内使用，以获取最新的实时数据

## 许可证

本插件遵循 MIT 许可证。

## 作者

FactorWeave-Quant 开发团队

## 版本历史

- v1.0.0 (2024): 初始版本
  - 实现基本的数据获取功能
  - 支持实时行情和历史K线数据
  - 自动服务器选择和连接管理
  - 完善的错误处理和日志记录 