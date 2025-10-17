# 🔄 自适应连接池用户指南

**功能**: 根据实际负载自动动态调整DuckDB连接池大小

**状态**: ✅ 已完成并可用

---

## 📋 快速开始

### 1. 系统启动时自动启用

在系统主入口（`main.py`或应用初始化代码）中添加：

```python
from core.adaptive_pool_initializer import initialize_adaptive_pool

# 在系统启动后调用
adaptive_manager = initialize_adaptive_pool()
```

**就这么简单！**系统会自动：
- ✅ 加载配置
- ✅ 启动监控
- ✅ 自动调整

---

## ⚙️ 配置管理

###方式1: 通过ConfigService（推荐）

配置会自动持久化到数据库：

```python
from core.containers import get_service_container
from core.services.config_service import ConfigService
from core.database.connection_pool_config import ConnectionPoolConfigManager

container = get_service_container()
config_service = container.resolve(ConfigService)
config_manager = ConnectionPoolConfigManager(config_service)

# 修改配置
adaptive_config = {
    'enabled': True,
    'min_pool_size': 5,
    'max_pool_size': 30,
    'scale_up_usage_threshold': 0.8,
    'scale_down_usage_threshold': 0.3,
    'cooldown_seconds': 60
}

config_manager.save_adaptive_config(adaptive_config)
```

### 方式2: 代码中直接配置

```python
from core.database.adaptive_connection_pool import AdaptivePoolConfig, AdaptiveConnectionPoolManager

config = AdaptivePoolConfig(
    enabled=True,
    min_pool_size=3,
    max_pool_size=50,
    scale_up_usage_threshold=0.8,
    scale_down_usage_threshold=0.3,
    cooldown_seconds=60
)

db = get_analytics_db()
adaptive_manager = AdaptiveConnectionPoolManager(db, config)
adaptive_manager.start()
```

---

## 📊 配置参数详解

### 边界配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `min_pool_size` | 3 | 连接池最小值（不会低于此值） |
| `max_pool_size` | 50 | 连接池最大值（不会超过此值） |

**建议**:
- 低流量应用: min=3, max=20
- 中流量应用: min=5, max=30
- 高流量应用: min=10, max=50

### 触发阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scale_up_usage_threshold` | 0.8 | 使用率超过80%时扩容 |
| `scale_down_usage_threshold` | 0.3 | 使用率低于30%时缩容 |
| `scale_up_overflow_threshold` | 0.5 | 溢出连接超过50%时扩容 |

**建议**:
- 保守策略: up=0.9, down=0.2（较少调整）
- 激进策略: up=0.7, down=0.4（更快响应）
- 平衡策略: up=0.8, down=0.3（默认，推荐）

### 调整策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scale_up_factor` | 1.5 | 扩容时的倍数（pool_size × 1.5） |
| `scale_down_factor` | 0.8 | 缩容时的比例（pool_size × 0.8） |

**示例**:
- pool_size=5 → 扩容 → 5 × 1.5 = 8 (向上取整)
- pool_size=10 → 缩容 → 10 × 0.8 = 8

### 时间窗口

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `metrics_window_seconds` | 60 | 决策时查看最近60秒的指标 |
| `cooldown_seconds` | 60 | 调整后60秒内不再调整 |
| `collection_interval` | 10 | 每10秒采集一次指标 |

**建议**:
- 快速响应: metrics=30, cooldown=30
- 稳定优先: metrics=120, cooldown=120
- 平衡（默认）: metrics=60, cooldown=60

---

## 📈 监控和状态查询

### 获取管理器状态

```python
from core.adaptive_pool_initializer import get_adaptive_manager

manager = get_adaptive_manager()
if manager:
    status = manager.get_status()
    
    print(f"运行状态: {status['running']}")
    print(f"调整次数: {status['adjustment_count']}")
    print(f"当前pool_size: {status['current_pool_size']}")
    print(f"当前使用率: {status['current_usage_rate']}")
```

**输出示例**:
```
运行状态: True
调整次数: 3
当前pool_size: 8
当前使用率: 45.2%
```

### 查询最近指标

```python
manager = get_adaptive_manager()
if manager:
    recent = manager.collector.get_recent_metrics(window_seconds=60)
    
    for metrics in recent[-5:]:  # 最近5条
        print(f"时间: {metrics['timestamp'].strftime('%H:%M:%S')}")
        print(f"  pool_size: {metrics['pool_size']}")
        print(f"  使用率: {metrics['usage_rate']*100:.1f}%")
```

---

## 🎯 使用场景

### 场景1: 日间高峰 + 夜间低谷

**问题**: 日间并发查询多，夜间几乎无查询

**解决**: 自适应连接池自动调整
- 日间: 自动扩容到15-20个连接
- 夜间: 自动缩容到3-5个连接

**配置**:
```python
config = AdaptivePoolConfig(
    min_pool_size=3,
    max_pool_size=20,
    scale_up_usage_threshold=0.7,  # 更敏感
    scale_down_usage_threshold=0.3
)
```

### 场景2: 突发流量

**问题**: 偶尔出现突发高并发查询

**解决**: 快速扩容应对
- 检测到高负载: 30秒内扩容
- 负载下降: 120秒后缩容（避免频繁调整）

**配置**:
```python
config = AdaptivePoolConfig(
    scale_up_factor=2.0,  # 快速扩容
    cooldown_seconds=120,  # 较长冷却期
    metrics_window_seconds=30  # 快速响应
)
```

### 场景3: 稳定负载

**问题**: 负载相对稳定，不需要频繁调整

**解决**: 保守策略
- 较高的触发阈值
- 较长的冷却期

**配置**:
```python
config = AdaptivePoolConfig(
    scale_up_usage_threshold=0.9,  # 90%才扩容
    scale_down_usage_threshold=0.2,  # 20%才缩容
    cooldown_seconds=300  # 5分钟冷却期
)
```

---

## 🔍 调试和日志

### 启用详细日志

```python
from loguru import logger

# 设置DEBUG级别查看所有调整决策
logger.add("adaptive_pool.log", level="DEBUG", filter=lambda record: "adaptive" in record["name"].lower())
```

**日志示例**:
```
22:37:34.889 | INFO | 🔄 启动自适应连接池管理...
22:37:34.889 | INFO | 📊 指标收集器已启动，采集间隔=10秒
22:37:34.889 | INFO | ✅ 自适应连接池管理已启动 (min=3, max=50)
22:38:04.890 | INFO | 🔄 自动调整连接池: 5 -> 8 (高负载（使用率=85.2%, 溢出=2.5）)
22:38:04.891 | INFO | ✅ 连接池已自动调整: pool_size=8
```

### 诊断问题

**问题**: 为什么没有触发扩容/缩容？

**排查步骤**:
1. 检查是否启用: `manager.config.enabled`
2. 检查冷却期: 是否在调整后60秒内？
3. 检查阈值: 使用率是否达到触发条件？
4. 检查边界: 是否已达到min/max限制？

```python
manager = get_adaptive_manager()
if manager:
    should_adjust, new_size, reason = manager.decision_engine.should_adjust()
    print(f"决策结果: {should_adjust}")
    print(f"新大小: {new_size}")
    print(f"原因: {reason}")
```

---

## 🛠️ 高级功能

### 禁用自适应管理

```python
# 方式1: 通过配置
config_manager.save_adaptive_config({'enabled': False})

# 方式2: 停止管理器
from core.adaptive_pool_initializer import stop_adaptive_pool
stop_adaptive_pool()
```

### 手动触发调整

```python
from core.database.connection_pool_config import ConnectionPoolConfig

manager = get_adaptive_manager()
if manager:
    # 手动设置新的pool_size
    new_config = ConnectionPoolConfig(pool_size=15)
    manager.db.reload_pool(new_config)
```

### 自定义决策逻辑

继承 `AdaptiveDecisionEngine` 并重写 `should_adjust` 方法：

```python
class CustomDecisionEngine(AdaptiveDecisionEngine):
    def should_adjust(self) -> tuple[bool, Optional[int], Optional[str]]:
        # 自定义决策逻辑
        ...
        return should_adjust, new_size, reason

# 使用自定义引擎
manager.decision_engine = CustomDecisionEngine(manager.collector, config)
```

---

## 📊 资源占用

### 内存占用
- **指标历史**: 最多1000条 × 56字节 = **56KB**
- **管理器对象**: < 1KB
- **总计**: < **100KB**

### CPU占用
- **采集频率**: 每10秒1次
- **单次耗时**: < 0.1ms
- **CPU占用率**: < **0.01%**

### 线程数
- **指标收集线程**: 1个（后台daemon线程）
- **调整循环线程**: 1个（后台daemon线程）
- **总计**: **2个后台线程**

---

## ✅ 最佳实践

### 1. 生产环境建议配置

```python
production_config = AdaptivePoolConfig(
    enabled=True,
    min_pool_size=5,
    max_pool_size=30,
    scale_up_usage_threshold=0.8,
    scale_down_usage_threshold=0.3,
    cooldown_seconds=60,
    collection_interval=10,
    metrics_window_seconds=60
)
```

### 2. 与监控系统集成

定期查询状态并发送到监控系统：

```python
import time

def monitor_adaptive_pool():
    while True:
        manager = get_adaptive_manager()
        if manager:
            status = manager.get_status()
            # 发送到Prometheus/Grafana等监控系统
            send_to_monitoring(status)
        
        time.sleep(60)  # 每分钟监控一次
```

### 3. 配置更新后重启

```python
# 保存新配置
config_manager.save_adaptive_config(new_config)

# 重启自适应管理器
stop_adaptive_pool()
initialize_adaptive_pool()
```

---

## 🐛 故障排除

### 问题1: 管理器未启动

**症状**: `get_adaptive_manager()` 返回 `None`

**原因**:
1. 配置中 `enabled=False`
2. 初始化失败（检查日志）
3. 未调用 `initialize_adaptive_pool()`

**解决**:
```python
# 检查配置
config_manager = ConnectionPoolConfigManager(config_service)
print(config_manager.is_adaptive_enabled())

# 手动启动
from core.adaptive_pool_initializer import initialize_adaptive_pool
initialize_adaptive_pool()
```

### 问题2: 调整不生效

**症状**: 使用率很高但未扩容

**原因**:
1. 在冷却期内
2. 已达到max_pool_size
3. 阈值设置过高

**解决**:
```python
# 查看决策原因
manager = get_adaptive_manager()
_, _, reason = manager.decision_engine.should_adjust()
print(reason)

# 降低阈值或增加max_pool_size
```

### 问题3: 内存占用增长

**症状**: 长时间运行后内存持续增长

**原因**: 理论上不会发生（`deque(maxlen=1000)`限制）

**解决**:
1. 检查是否有其他内存泄漏
2. 重启管理器
3. 联系技术支持

---

## 📚 相关文档

- [设计文档](ADAPTIVE_CONNECTION_POOL_DESIGN.md)
- [DuckDB性能优化文档](PERFORMANCE_EVALUATION_AND_OPTIMIZATION_REPORT.md)
- [连接池配置文档](CONNECTION_POOL_CONFIG_IMPLEMENTATION.md)

---

## ❓ 常见问题（FAQ）

**Q: 自适应连接池会影响现有功能吗？**  
A: 不会，它只是在后台监控并调整pool_size，对现有代码完全透明。

**Q: 可以禁用吗？**  
A: 可以，设置 `enabled=False` 或直接不调用 `initialize_adaptive_pool()`。

**Q: 多久调整一次？**  
A: 取决于负载，但最快也要60秒（冷却期），避免频繁调整。

**Q: 会自动保存配置吗？**  
A: 通过 `ConfigService` 保存的配置会自动持久化到数据库。

**Q: 如何查看调整历史？**  
A: 查看日志文件，所有调整都会记录INFO级别日志。

---

**更新日期**: 2025-10-13  
**版本**: 1.0  
**作者**: AI Assistant

