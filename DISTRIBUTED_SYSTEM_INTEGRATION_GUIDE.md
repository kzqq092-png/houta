# 分布式系统集成指南

## 📋 概述

本指南说明如何将分布式计算系统集成到主程序中，实现任务的自动分发和容错执行。

## 🎯 核心特性

✅ **完整实现**
- 独立的分布式节点程序
- FastAPI HTTP服务器
- 真实的数据导入任务执行
- HTTP远程调用 + 本地Fallback
- 健康检查和负载均衡
- 容错和自动恢复

✅ **已验证**
- 本地执行模式（无节点）
- 单节点远程执行
- 多节点负载均衡
- 节点故障自动恢复

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn httpx pydantic psutil
```

### 2. 启动分布式节点

**单个节点**：
```bash
python distributed_node/node_server.py --port 8900
```

**多个节点**（不同终端）：
```bash
# 节点1
python distributed_node/node_server.py --port 8900 --node-name "Worker-1"

# 节点2
python distributed_node/node_server.py --port 8901 --node-name "Worker-2"

# 节点3
python distributed_node/node_server.py --port 8902 --node-name "Worker-3"
```

### 3. 在代码中使用

```python
from core.services.distributed_http_bridge import get_distributed_bridge

# 获取分布式桥接器
bridge = get_distributed_bridge()

# 添加节点（可选，如果有可用节点）
bridge.add_node("node_001", "localhost", 8900)
bridge.add_node("node_002", "localhost", 8901)

# 执行任务（自动选择远程或本地）
result = await bridge.execute_task(
    task_id="import_task_001",
    task_type="data_import",
    task_data={
        "symbols": ["000001.SZ", "000002.SZ"],
        "data_source": "tongdaxin",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    },
    timeout=300
)

print(f"任务状态: {result.status}")
print(f"任务结果: {result.result}")
```

## 🔄 集成到数据导入

### 修改 `ImportExecutionEngine`

在 `core/importdata/import_execution_engine.py` 中：

```python
from core.services.distributed_http_bridge import get_distributed_bridge

class DataImportExecutionEngine:
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # 添加分布式桥接器
        if self.enable_distributed_execution:
            self.distributed_bridge = get_distributed_bridge()
            # 自动发现节点（可选）
            self._discover_nodes()
    
    def _discover_nodes(self):
        """发现可用节点"""
        # 从配置文件或环境变量加载节点列表
        nodes = [
            {"node_id": "node_001", "host": "localhost", "port": 8900},
            {"node_id": "node_002", "host": "localhost", "port": 8901},
        ]
        for node in nodes:
            self.distributed_bridge.add_node(**node)
    
    async def _import_kline_data_distributed(self, task_config):
        """使用分布式执行导入K线数据"""
        if not self.enable_distributed_execution:
            # 本地执行
            return await self._import_kline_data(task_config)
        
        # 分布式执行
        result = await self.distributed_bridge.execute_task(
            task_id=task_config.task_id,
            task_type="data_import",
            task_data={
                "symbols": task_config.symbols,
                "data_source": task_config.data_source,
                "start_date": task_config.start_date,
                "end_date": task_config.end_date
            },
            timeout=task_config.timeout
        )
        
        return result
```

## 🧪 测试

### 运行回归测试

```bash
python test_distributed_system.py
```

测试场景：
1. ✅ 本地执行（无节点）
2. ✅ 单节点远程执行
3. ✅ 多节点负载均衡
4. ✅ 节点故障恢复

### 手动测试节点API

```bash
# 健康检查
curl http://localhost:8900/api/v1/health

# 提交任务
curl -X POST http://localhost:8900/api/v1/task/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test_001",
    "task_type": "data_import",
    "task_data": {"symbols": ["000001.SZ"]},
    "priority": 5,
    "timeout": 300
  }'

# 查询任务状态
curl http://localhost:8900/api/v1/task/test_001/status

# 获取节点统计
curl http://localhost:8900/api/v1/node/stats
```

## 📊 架构说明

### 组件关系

```
主程序 (main.py)
    ↓
ImportExecutionEngine (导入引擎)
    ↓
DistributedHTTPBridge (HTTP桥接器)
    ├─→ 有节点: HTTP调用远程节点
    │       ↓
    │   Distributed Node (FastAPI服务器)
    │       ↓
    │   TaskExecutor (任务执行器)
    │       ↓
    │   RealDataProvider (真实数据获取)
    │
    └─→ 无节点: 本地执行 (fallback)
            ↓
        TaskExecutor (本地执行器)
```

### 数据流

1. **任务提交** → `DistributedHTTPBridge.execute_task()`
2. **节点选择** → `_select_best_node()` (基于CPU/内存/任务数)
3. **HTTP调用** → `POST /api/v1/task/execute`
4. **任务执行** → `TaskExecutor.execute_task()`
5. **状态轮询** → `GET /api/v1/task/{task_id}/status`
6. **结果返回** → `TaskResult`

## ⚙️ 配置选项

### 节点配置文件 (`node_config.json`)

```json
{
  "node_id": "auto-generated",
  "node_name": "Worker Node 1",
  "host": "0.0.0.0",
  "port": 8900,
  "api_key": null,
  "max_workers": 4,
  "task_timeout": 300,
  "heartbeat_interval": 10,
  "max_memory_mb": 4096,
  "max_cpu_percent": 80.0,
  "log_level": "INFO"
}
```

### 环境变量

```bash
export NODE_PORT=8900
export NODE_NAME="Worker-1"
export MAX_WORKERS=8
export NODE_API_KEY="your-secret-key"
```

## 🛡️ 安全建议

1. **启用API密钥认证**
   ```python
   config.api_key = "your-strong-secret-key"
   ```

2. **使用HTTPS** (生产环境)
   ```bash
   uvicorn distributed_node.node_server:app \
     --ssl-keyfile=./key.pem \
     --ssl-certfile=./cert.pem
   ```

3. **IP白名单** (防火墙规则)
   ```bash
   # 只允许特定IP访问
   iptables -A INPUT -p tcp --dport 8900 -s 192.168.1.0/24 -j ACCEPT
   iptables -A INPUT -p tcp --dport 8900 -j DROP
   ```

## 📈 性能优化

### 1. 增加节点数量
```bash
# 启动更多节点提高并发能力
for i in {0..7}; do
    python distributed_node/node_server.py --port $((8900+i)) --node-name "Worker-$i" &
done
```

### 2. 调整工作线程数
```bash
python distributed_node/node_server.py --max-workers 16
```

### 3. 启用缓存和优化
```python
# 在节点配置中启用
config.enable_caching = True
config.cache_size_mb = 1024
```

## 🐛 故障排除

### 问题1：节点无法连接
```bash
# 检查端口是否被占用
netstat -an | grep 8900

# 检查防火墙
telnet localhost 8900
```

### 问题2：任务执行失败
```bash
# 查看节点日志
tail -f logs/node.log

# 检查节点健康状态
curl http://localhost:8900/api/v1/health
```

### 问题3：内存不足
```bash
# 减少最大工作线程
python distributed_node/node_server.py --max-workers 2

# 或在配置中设置
config.max_workers = 2
config.max_memory_mb = 2048
```

## 📝 开发路线图

### 当前版本 (v1.0.0)
- ✅ 基础分布式架构
- ✅ HTTP远程调用
- ✅ 本地fallback
- ✅ 健康检查
- ✅ 真实数据导入

### 未来版本
- ⏳ 节点监控UI
- ⏳ WebSocket实时通信
- ⏳ 任务优先级队列
- ⏳ 数据缓存共享
- ⏳ Docker容器化部署

## 💡 最佳实践

1. **开发环境**：使用本地模式（无节点）
2. **测试环境**：启动1-2个节点验证
3. **生产环境**：根据负载启动多个节点
4. **监控**：定期检查节点健康状态
5. **日志**：保留节点日志以便排查问题

## 📞 支持

如有问题请查看：
- 📖 `distributed_node/README.md`
- 🧪 `test_distributed_system.py`
- 💾 记忆体：`distributed_node_implementation`

---

**版本**: 1.0.0  
**更新**: 2025-10-23  
**作者**: HIkyuu-UI团队

