# 插件配置管理指南

## 配置系统概览

FactorWeave-Quant系统提供了完整的插件配置管理系统，支持：

- **UI配置界面**: 通过插件管理器对话框进行可视化配置
- **数据库持久化**: 配置自动保存到SQLite数据库
- **实时应用**: 配置更改后立即生效
- **Schema验证**: 确保配置参数的有效性
- **默认值管理**: 提供合理的默认配置

## 访问配置界面

### 1. 打开插件管理器
```
主菜单 → 工具 → 插件管理器
或者
快捷键: Ctrl+P
```

### 2. 选择插件类型
- **数据源插件**: 股票、期货等数据源配置
- **情绪数据源**: 情绪分析插件配置
- **指标/策略**: 技术指标和策略配置

### 3. 配置插件
1. 在插件列表中选择要配置的插件
2. 点击 "配置" 按钮
3. 在弹出的配置对话框中修改参数
4. 点击 "保存" 应用配置

## 连接池配置参数详解

### AKShare股票插件配置

| 参数名称 | 类型 | 默认值 | 范围 | 说明 |
|---------|------|--------|------|------|
| **请求超时** | 整数 | 30 | 5-120 | HTTP请求超时时间（秒） |
| **最大重试次数** | 整数 | 3 | 0-10 | 网络失败时的重试次数 |
| **缓存时长** | 整数 | 3600 | 300-86400 | 数据缓存持续时间（秒） |
| **连接池大小** | 整数 | 10 | 1-50 | HTTP连接池连接数 |
| **最大连接数** | 整数 | 20 | 5-100 | 连接池最大连接数 |
| **请求间隔** | 小数 | 0.1 | 0.0-5.0 | 请求间隔时间（秒） |
| **会话复用** | 布尔 | true | - | 启用HTTP会话复用 |
| **用户代理** | 字符串 | Chrome UA | - | HTTP请求用户代理 |

### 东方财富插件配置

| 参数名称 | 类型 | 默认值 | 范围 | 说明 |
|---------|------|--------|------|------|
| **请求超时** | 整数 | 30 | 5-120 | HTTP请求超时时间（秒） |
| **最大重试次数** | 整数 | 3 | 0-10 | 网络失败时的重试次数 |
| **请求间隔** | 小数 | 0.1 | 0.0-2.0 | 请求间隔时间（秒） |
| **连接池大小** | 整数 | 10 | 1-30 | HTTP连接池连接数 |
| **最大连接数** | 整数 | 20 | 5-50 | 连接池最大连接数 |
| **API地址** | 字符串 | push2.eastmoney.com | - | 东方财富API基础URL |

## 配置持久化机制

### 数据库存储
- **数据库类型**: SQLite
- **存储位置**: `db/factorweave_system.sqlite`
- **存储表**: `plugin_configs`

### 配置类型
- **user**: 用户自定义配置
- **system**: 系统默认配置
- **runtime**: 运行时临时配置

### 配置加载顺序
1. 加载插件默认配置
2. 覆盖数据库中的用户配置
3. 应用运行时配置

## 配置最佳实践

### 1. 防封配置建议

**高频交易场景**:
```json
{
    "rate_limit_delay": 0.05,
    "pool_connections": 5,
    "pool_maxsize": 10,
    "max_retries": 2
}
```

**正常使用场景**:
```json
{
    "rate_limit_delay": 0.1,
    "pool_connections": 10,
    "pool_maxsize": 20,
    "max_retries": 3
}
```

**保守模式**:
```json
{
    "rate_limit_delay": 0.5,
    "pool_connections": 3,
    "pool_maxsize": 5,
    "max_retries": 5
}
```

### 2. 性能优化配置

**高性能模式**:
```json
{
    "timeout": 15,
    "pool_connections": 20,
    "pool_maxsize": 40,
    "cache_duration": 1800
}
```

**稳定模式**:
```json
{
    "timeout": 60,
    "pool_connections": 10,
    "pool_maxsize": 20,
    "cache_duration": 3600
}
```

### 3. 网络环境适配

**国内网络**:
```json
{
    "timeout": 30,
    "max_retries": 5,
    "rate_limit_delay": 0.2
}
```

**海外网络**:
```json
{
    "timeout": 60,
    "max_retries": 8,
    "rate_limit_delay": 0.5
}
```

## 配置导入导出

### 导出配置
1. 在插件管理器中点击 "导出配置"
2. 选择保存位置
3. 配置以JSON格式保存

### 导入配置
1. 在插件管理器中点击 "导入配置"
2. 选择配置文件
3. 系统自动验证并应用配置

### 配置文件格式
```json
{
    "akshare_stock_plugin": {
        "timeout": 30,
        "max_retries": 3,
        "pool_connections": 10,
        "rate_limit_delay": 0.1
    },
    "eastmoney_stock_plugin": {
        "timeout": 25,
        "max_retries": 2,
        "rate_limit_delay": 0.15
    }
}
```

## 故障排除

### 常见问题

**1. 配置不生效**
- 检查配置格式是否正确
- 确认已点击"保存"按钮
- 重启插件或重新连接

**2. 请求被限制**
- 增加 `rate_limit_delay` 值
- 减少 `pool_connections` 数量
- 调整 `user_agent` 字符串

**3. 连接超时**
- 增加 `timeout` 值
- 增加 `max_retries` 次数
- 检查网络连接

**4. 性能问题**
- 调整 `cache_duration` 缓存时间
- 优化连接池大小
- 监控内存使用情况

### 日志分析
```
插件配置已成功应用                    # 配置生效
连接池配置已更改，重新创建HTTP会话      # 连接池重建
速率限制已更新: 0.2秒                # 速率限制更新
```

## API接口

### 获取配置Schema
```python
plugin = AKShareStockPlugin()
schema = plugin.get_config_schema()
```

### 应用配置
```python
config = {
    "timeout": 45,
    "pool_connections": 15,
    "rate_limit_delay": 0.2
}
success = plugin.apply_config(config)
```

### 验证配置
```python
valid = plugin.validate_config(config)
```

---

**最后更新**: $(date)  
**适用版本**: FactorWeave-Quant v1.0+  
**技术支持**: 通过插件管理器反馈问题
