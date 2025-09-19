# DuckDB专业数据导入系统 API参考文档 v3.0

## 文档信息

- **版本**: 3.0
- **更新日期**: 2024年1月
- **API版本**: v3
- **文档类型**: API参考和开发者指南

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [认证和授权](#认证和授权)
4. [REST API](#rest-api)
5. [Python SDK](#python-sdk)
6. [WebSocket API](#websocket-api)
7. [插件开发](#插件开发)
8. [数据源扩展](#数据源扩展)
9. [错误处理](#错误处理)
10. [最佳实践](#最佳实践)

## 概述

DuckDB专业数据导入系统提供了完整的API接口，支持第三方开发者进行系统集成、功能扩展和自定义开发。API采用RESTful设计风格，支持JSON格式的数据交换，并提供Python SDK简化开发工作。

### API特性

- **RESTful设计**: 遵循REST架构风格，接口简洁易用
- **JSON数据格式**: 统一使用JSON进行数据交换
- **完整的CRUD操作**: 支持创建、读取、更新、删除操作
- **实时数据推送**: 通过WebSocket提供实时数据推送
- **插件系统**: 支持自定义插件扩展系统功能
- **SDK支持**: 提供Python SDK简化开发工作

### 支持的功能

- **任务管理**: 创建、配置、执行、监控数据导入任务
- **数据查询**: 查询已导入的各类金融数据
- **系统监控**: 获取系统状态、性能指标、告警信息
- **配置管理**: 管理系统配置、数据源配置
- **异常处理**: 查询和处理数据异常
- **用户管理**: 用户认证、权限管理

## 快速开始

### 环境准备

**系统要求**:
- Python 3.9+
- 网络连接
- API访问权限

**安装SDK**:
```bash
pip install hikyuu-client
```

### 第一个API调用

```python
import requests

# API基础URL
BASE_URL = "http://localhost:8080/api/v3"

# 获取系统状态
response = requests.get(f"{BASE_URL}/system/status")
if response.status_code == 200:
    status = response.json()
    print(f"系统状态: {status['status']}")
    print(f"运行时间: {status['uptime']}")
else:
    print(f"请求失败: {response.status_code}")
```

### 使用Python SDK

```python
from hikyuu_client import HikyuuClient

# 创建客户端
client = HikyuuClient(
    host='localhost',
    port=8080,
    api_key='your_api_key'
)

# 获取系统状态
status = client.get_system_status()
print(f"系统状态: {status.status}")

# 创建数据导入任务
task = client.create_task(
    name='测试任务',
    data_source='tongdaxin',
    symbols=['000001', '000002'],
    start_date='2024-01-01'
)

print(f"任务创建成功: {task.id}")
```

## 认证和授权

### API密钥认证

系统使用API密钥进行身份认证。在请求头中包含API密钥：

```http
Authorization: Bearer your_api_key_here
Content-Type: application/json
```

### 获取API密钥

1. 登录系统管理界面
2. 进入"API管理"页面
3. 点击"生成新密钥"
4. 复制并保存生成的密钥

### 权限级别

- **只读权限**: 只能查询数据和系统状态
- **操作权限**: 可以创建和管理任务
- **管理权限**: 可以修改系统配置和用户权限

### 认证示例

```python
import requests

headers = {
    'Authorization': 'Bearer your_api_key_here',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:8080/api/v3/tasks',
    headers=headers
)
```

## REST API

### 基础信息

**基础URL**: `http://localhost:8080/api/v3`

**请求格式**: JSON
**响应格式**: JSON
**字符编码**: UTF-8

### 通用响应格式

```json
{
    "success": true,
    "data": {},
    "message": "操作成功",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

**错误响应格式**:
```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "参数无效",
        "details": "symbol参数不能为空"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req_123456789"
}
```

### 任务管理API

#### 获取任务列表

```http
GET /api/v3/tasks
```

**查询参数**:
- `page` (int, 可选): 页码，默认1
- `size` (int, 可选): 每页大小，默认20
- `status` (string, 可选): 任务状态过滤
- `data_source` (string, 可选): 数据源过滤

**响应示例**:
```json
{
    "success": true,
    "data": {
        "tasks": [
            {
                "id": "task_001",
                "name": "沪深300日线数据",
                "status": "running",
                "data_source": "tongdaxin",
                "created_at": "2024-01-01T09:00:00Z",
                "progress": 75.5
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20
    }
}
```

#### 创建新任务

```http
POST /api/v3/tasks
```

**请求体**:
```json
{
    "name": "测试任务",
    "data_source": "tongdaxin",
    "asset_type": "stock",
    "data_type": "kline",
    "symbols": ["000001", "000002"],
    "frequency": "daily",
    "mode": "batch",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "max_workers": 4,
    "batch_size": 1000
}
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": "task_002",
        "name": "测试任务",
        "status": "created",
        "created_at": "2024-01-01T10:00:00Z"
    }
}
```

#### 获取任务详情

```http
GET /api/v3/tasks/{task_id}
```

**路径参数**:
- `task_id` (string): 任务ID

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": "task_001",
        "name": "沪深300日线数据",
        "status": "running",
        "data_source": "tongdaxin",
        "asset_type": "stock",
        "symbols": ["000001", "000002"],
        "progress": 75.5,
        "created_at": "2024-01-01T09:00:00Z",
        "started_at": "2024-01-01T09:05:00Z",
        "performance": {
            "execution_time": 1800,
            "success_rate": 0.98,
            "throughput": 1200
        }
    }
}
```

#### 启动任务

```http
POST /api/v3/tasks/{task_id}/start
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": "task_001",
        "status": "running",
        "started_at": "2024-01-01T10:00:00Z"
    }
}
```

#### 停止任务

```http
POST /api/v3/tasks/{task_id}/stop
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": "task_001",
        "status": "stopped",
        "stopped_at": "2024-01-01T10:30:00Z"
    }
}
```

#### 删除任务

```http
DELETE /api/v3/tasks/{task_id}
```

**响应示例**:
```json
{
    "success": true,
    "message": "任务删除成功"
}
```

### 数据查询API

#### 查询股票数据

```http
GET /api/v3/data/stocks
```

**查询参数**:
- `symbols` (string): 股票代码，多个用逗号分隔
- `start_date` (string): 开始日期 (YYYY-MM-DD)
- `end_date` (string): 结束日期 (YYYY-MM-DD)
- `frequency` (string): 数据频率 (daily, minute)
- `fields` (string, 可选): 返回字段，多个用逗号分隔

**响应示例**:
```json
{
    "success": true,
    "data": {
        "records": [
            {
                "symbol": "000001",
                "date": "2024-01-01",
                "open": 10.50,
                "high": 10.80,
                "low": 10.30,
                "close": 10.65,
                "volume": 1000000,
                "amount": 10650000
            }
        ],
        "total": 1
    }
}
```

#### 自定义数据查询

```http
POST /api/v3/data/query
```

**请求体**:
```json
{
    "sql": "SELECT * FROM stock_data WHERE symbol = ? AND date >= ?",
    "params": ["000001", "2024-01-01"],
    "limit": 1000
}
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "columns": ["symbol", "date", "open", "high", "low", "close", "volume"],
        "records": [
            ["000001", "2024-01-01", 10.50, 10.80, 10.30, 10.65, 1000000]
        ],
        "total": 1
    }
}
```

### 系统监控API

#### 获取系统状态

```http
GET /api/v3/system/status
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "status": "running",
        "version": "3.0.0",
        "uptime": 86400,
        "cpu_usage": 25.5,
        "memory_usage": 60.2,
        "disk_usage": 45.8,
        "active_tasks": 3,
        "total_tasks": 15
    }
}
```

#### 获取性能指标

```http
GET /api/v3/system/metrics
```

**查询参数**:
- `start_time` (string, 可选): 开始时间
- `end_time` (string, 可选): 结束时间
- `metrics` (string, 可选): 指标名称，多个用逗号分隔

**响应示例**:
```json
{
    "success": true,
    "data": {
        "metrics": [
            {
                "name": "cpu_usage",
                "values": [
                    {"timestamp": "2024-01-01T10:00:00Z", "value": 25.5},
                    {"timestamp": "2024-01-01T10:01:00Z", "value": 26.2}
                ]
            }
        ]
    }
}
```

#### 获取系统日志

```http
GET /api/v3/system/logs
```

**查询参数**:
- `level` (string, 可选): 日志级别 (DEBUG, INFO, WARNING, ERROR)
- `start_time` (string, 可选): 开始时间
- `end_time` (string, 可选): 结束时间
- `limit` (int, 可选): 返回条数限制

**响应示例**:
```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "level": "INFO",
                "message": "任务 task_001 开始执行",
                "module": "task_manager"
            }
        ],
        "total": 1
    }
}
```

### 配置管理API

#### 获取系统配置

```http
GET /api/v3/config/system
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "max_concurrent_tasks": 10,
        "default_batch_size": 1000,
        "cache_enabled": true,
        "cache_expiry_seconds": 3600
    }
}
```

#### 更新系统配置

```http
PUT /api/v3/config/system
```

**请求体**:
```json
{
    "max_concurrent_tasks": 15,
    "default_batch_size": 1500
}
```

#### 获取数据源配置

```http
GET /api/v3/config/datasources
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "tongdaxin": {
            "enabled": true,
            "api_url": "http://api.tongdaxin.com",
            "timeout": 30,
            "retry_count": 3
        },
        "akshare": {
            "enabled": true,
            "timeout": 60,
            "retry_count": 5
        }
    }
}
```

### 异常管理API

#### 获取异常列表

```http
GET /api/v3/anomalies
```

**查询参数**:
- `type` (string, 可选): 异常类型过滤
- `severity` (string, 可选): 严重程度过滤
- `resolved` (boolean, 可选): 是否已解决
- `start_time` (string, 可选): 开始时间
- `end_time` (string, 可选): 结束时间

**响应示例**:
```json
{
    "success": true,
    "data": {
        "anomalies": [
            {
                "id": "anomaly_001",
                "type": "missing_data",
                "severity": "high",
                "description": "字段 close 缺失率过高: 15.00%",
                "symbol": "000001",
                "detected_at": "2024-01-01T10:00:00Z",
                "resolved": false
            }
        ],
        "total": 1
    }
}
```

#### 修复异常

```http
POST /api/v3/anomalies/{anomaly_id}/repair
```

**请求体**:
```json
{
    "repair_method": "interpolate",
    "parameters": {
        "method": "linear"
    }
}
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "repair_id": "repair_001",
        "status": "completed",
        "description": "使用线性插值修复缺失数据"
    }
}
```

## Python SDK

### 安装和初始化

```bash
pip install hikyuu-client
```

```python
from hikyuu_client import HikyuuClient

# 创建客户端实例
client = HikyuuClient(
    host='localhost',
    port=8080,
    api_key='your_api_key',
    timeout=30
)
```

### 任务管理

#### 创建任务

```python
from hikyuu_client.models import TaskConfig

# 创建任务配置
config = TaskConfig(
    name='Python SDK测试任务',
    data_source='tongdaxin',
    asset_type='stock',
    symbols=['000001', '000002'],
    frequency='daily',
    start_date='2024-01-01',
    max_workers=4,
    batch_size=1000
)

# 创建任务
task = client.create_task(config)
print(f"任务创建成功: {task.id}")
```

#### 管理任务

```python
# 获取任务列表
tasks = client.get_tasks(status='running')
print(f"运行中的任务: {len(tasks)}")

# 获取任务详情
task = client.get_task('task_001')
print(f"任务状态: {task.status}")
print(f"执行进度: {task.progress}%")

# 启动任务
client.start_task('task_001')

# 停止任务
client.stop_task('task_001')

# 删除任务
client.delete_task('task_001')
```

#### 监控任务执行

```python
import time

# 创建并启动任务
task = client.create_task(config)
client.start_task(task.id)

# 监控任务执行
while True:
    task = client.get_task(task.id)
    print(f"进度: {task.progress}%, 状态: {task.status}")
    
    if task.status in ['completed', 'failed', 'cancelled']:
        break
    
    time.sleep(5)

print(f"任务执行完成，最终状态: {task.status}")
```

### 数据查询

#### 查询股票数据

```python
from datetime import datetime, timedelta

# 查询单只股票数据
data = client.get_stock_data(
    symbols=['000001'],
    start_date='2024-01-01',
    end_date='2024-01-31',
    frequency='daily'
)

print(f"获取到 {len(data)} 条数据")
for record in data[:5]:  # 显示前5条
    print(f"{record.symbol} {record.date}: {record.close}")
```

#### 批量查询数据

```python
# 查询多只股票数据
symbols = ['000001', '000002', '000300']
data = client.get_stock_data(
    symbols=symbols,
    start_date='2024-01-01',
    end_date='2024-01-31'
)

# 按股票代码分组
from collections import defaultdict
grouped_data = defaultdict(list)
for record in data:
    grouped_data[record.symbol].append(record)

for symbol, records in grouped_data.items():
    print(f"{symbol}: {len(records)} 条记录")
```

#### 自定义SQL查询

```python
# 执行自定义SQL查询
sql = """
SELECT symbol, date, close, volume
FROM stock_data 
WHERE symbol IN (?, ?) 
  AND date >= ? 
  AND volume > ?
ORDER BY date DESC
LIMIT 100
"""

results = client.execute_query(
    sql=sql,
    params=['000001', '000002', '2024-01-01', 1000000]
)

print(f"查询结果: {len(results)} 条记录")
```

### 系统监控

#### 获取系统状态

```python
# 获取系统状态
status = client.get_system_status()
print(f"系统状态: {status.status}")
print(f"CPU使用率: {status.cpu_usage}%")
print(f"内存使用率: {status.memory_usage}%")
print(f"活跃任务数: {status.active_tasks}")
```

#### 监控性能指标

```python
from datetime import datetime, timedelta

# 获取最近1小时的性能指标
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)

metrics = client.get_metrics(
    start_time=start_time,
    end_time=end_time,
    metrics=['cpu_usage', 'memory_usage', 'task_throughput']
)

for metric in metrics:
    print(f"{metric.name}: 平均值 {metric.avg_value:.2f}")
```

### 异常处理

#### 查询和处理异常

```python
# 获取未解决的异常
anomalies = client.get_anomalies(resolved=False)
print(f"未解决异常: {len(anomalies)}")

for anomaly in anomalies:
    print(f"异常ID: {anomaly.id}")
    print(f"类型: {anomaly.type}")
    print(f"严重程度: {anomaly.severity}")
    print(f"描述: {anomaly.description}")
    
    # 获取修复建议
    suggestions = client.get_repair_suggestions(anomaly.id)
    if suggestions:
        best_suggestion = suggestions[0]  # 选择最佳建议
        print(f"建议修复方法: {best_suggestion.action}")
        
        # 执行修复
        repair_result = client.repair_anomaly(
            anomaly.id, 
            method=best_suggestion.action,
            parameters=best_suggestion.parameters
        )
        
        if repair_result.success:
            print("修复成功")
        else:
            print(f"修复失败: {repair_result.error}")
```

### 配置管理

#### 管理系统配置

```python
# 获取当前配置
config = client.get_system_config()
print(f"最大并发任务数: {config.max_concurrent_tasks}")

# 更新配置
client.update_system_config({
    'max_concurrent_tasks': 15,
    'default_batch_size': 1500
})

print("配置更新成功")
```

### 错误处理

```python
from hikyuu_client.exceptions import (
    HikyuuAPIError, 
    AuthenticationError, 
    RateLimitError
)

try:
    task = client.create_task(config)
except AuthenticationError:
    print("认证失败，请检查API密钥")
except RateLimitError:
    print("请求频率过高，请稍后重试")
except HikyuuAPIError as e:
    print(f"API错误: {e.message}")
    print(f"错误代码: {e.error_code}")
```

## WebSocket API

### 连接建立

```javascript
// JavaScript示例
const ws = new WebSocket('ws://localhost:8080/ws/v3');

ws.onopen = function(event) {
    console.log('WebSocket连接已建立');
    
    // 发送认证信息
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your_api_key'
    }));
};
```

```python
# Python示例
import websocket
import json

def on_open(ws):
    print("WebSocket连接已建立")
    # 发送认证信息
    auth_message = {
        'type': 'auth',
        'token': 'your_api_key'
    }
    ws.send(json.dumps(auth_message))

ws = websocket.WebSocketApp(
    "ws://localhost:8080/ws/v3",
    on_open=on_open
)
```

### 订阅实时数据

#### 订阅任务状态更新

```python
# 订阅任务状态更新
subscribe_message = {
    'type': 'subscribe',
    'channel': 'task_status',
    'task_ids': ['task_001', 'task_002']
}
ws.send(json.dumps(subscribe_message))
```

#### 订阅系统指标

```python
# 订阅系统性能指标
subscribe_message = {
    'type': 'subscribe',
    'channel': 'system_metrics',
    'metrics': ['cpu_usage', 'memory_usage', 'active_tasks']
}
ws.send(json.dumps(subscribe_message))
```

#### 订阅异常告警

```python
# 订阅异常告警
subscribe_message = {
    'type': 'subscribe',
    'channel': 'anomaly_alerts',
    'severity': ['high', 'critical']
}
ws.send(json.dumps(subscribe_message))
```

### 处理实时消息

```python
def on_message(ws, message):
    data = json.loads(message)
    
    if data['type'] == 'task_status_update':
        task_id = data['task_id']
        status = data['status']
        progress = data.get('progress', 0)
        print(f"任务 {task_id} 状态更新: {status}, 进度: {progress}%")
    
    elif data['type'] == 'system_metrics':
        metrics = data['metrics']
        for metric in metrics:
            print(f"{metric['name']}: {metric['value']}")
    
    elif data['type'] == 'anomaly_alert':
        anomaly = data['anomaly']
        print(f"异常告警: {anomaly['description']}")

ws.on_message = on_message
```

## 插件开发

### 插件架构

系统采用插件化架构，支持以下类型的插件：

- **数据处理插件**: 自定义数据处理逻辑
- **数据源插件**: 扩展新的数据源
- **分析插件**: 添加自定义分析功能
- **UI插件**: 扩展用户界面组件
- **导出插件**: 支持新的数据导出格式

### 插件接口规范

#### 基础插件接口

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.get_name()
        self.version = self.get_version()
    
    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """获取插件版本"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """清理插件资源"""
        pass
```

#### 数据处理插件

```python
from core.plugins.base import BasePlugin
import pandas as pd

class DataProcessorPlugin(BasePlugin):
    """数据处理插件基类"""
    
    @abstractmethod
    def process_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理数据"""
        pass
    
    @abstractmethod
    def get_supported_data_types(self) -> List[str]:
        """获取支持的数据类型"""
        pass

# 示例：数据清洗插件
class DataCleaningPlugin(DataProcessorPlugin):
    
    def get_name(self) -> str:
        return "数据清洗插件"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self) -> bool:
        return True
    
    def cleanup(self):
        pass
    
    def process_data(self, data: pd.DataFrame) -> pd.DataFrame:
        # 删除重复数据
        data = data.drop_duplicates()
        
        # 填充缺失值
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        data[numeric_columns] = data[numeric_columns].fillna(method='ffill')
        
        return data
    
    def get_supported_data_types(self) -> List[str]:
        return ['kline', 'tick', 'fundamental']
```

#### 数据源插件

```python
class DataSourcePlugin(BasePlugin):
    """数据源插件基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def get_data(self, symbols: List[str], start_date: str, 
                 end_date: str, frequency: str) -> pd.DataFrame:
        """获取数据"""
        pass
    
    @abstractmethod
    def get_supported_assets(self) -> List[str]:
        """获取支持的资产类型"""
        pass

# 示例：自定义数据源插件
class CustomDataSourcePlugin(DataSourcePlugin):
    
    def get_name(self) -> str:
        return "自定义数据源"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self) -> bool:
        self.api_url = self.config.get('api_url')
        self.api_key = self.config.get('api_key')
        return self.api_url and self.api_key
    
    def cleanup(self):
        self.disconnect()
    
    def connect(self) -> bool:
        # 实现连接逻辑
        return True
    
    def disconnect(self):
        # 实现断开连接逻辑
        pass
    
    def get_data(self, symbols: List[str], start_date: str, 
                 end_date: str, frequency: str) -> pd.DataFrame:
        # 实现数据获取逻辑
        import requests
        
        response = requests.get(
            f"{self.api_url}/data",
            params={
                'symbols': ','.join(symbols),
                'start_date': start_date,
                'end_date': end_date,
                'frequency': frequency
            },
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data['records'])
        else:
            raise Exception(f"数据获取失败: {response.status_code}")
    
    def get_supported_assets(self) -> List[str]:
        return ['stock', 'index', 'fund']
```

### 插件配置文件

每个插件需要包含一个`plugin.json`配置文件：

```json
{
    "name": "数据清洗插件",
    "version": "1.0.0",
    "description": "提供数据清洗和预处理功能",
    "author": "开发者姓名",
    "email": "developer@example.com",
    "type": "data_processor",
    "entry_point": "data_cleaning_plugin.DataCleaningPlugin",
    "dependencies": [
        "pandas>=1.3.0",
        "numpy>=1.21.0"
    ],
    "config_schema": {
        "type": "object",
        "properties": {
            "fill_method": {
                "type": "string",
                "enum": ["ffill", "bfill", "interpolate"],
                "default": "ffill"
            },
            "remove_duplicates": {
                "type": "boolean",
                "default": true
            }
        }
    }
}
```

### 插件注册和管理

#### 注册插件

```python
from core.plugins.manager import PluginManager

# 创建插件管理器
plugin_manager = PluginManager()

# 注册插件
plugin_manager.register_plugin(
    plugin_path='/path/to/plugin',
    config={
        'fill_method': 'interpolate',
        'remove_duplicates': True
    }
)

# 启用插件
plugin_manager.enable_plugin('数据清洗插件')
```

#### 使用插件

```python
# 获取数据处理插件
processor_plugins = plugin_manager.get_plugins_by_type('data_processor')

# 处理数据
for plugin in processor_plugins:
    if plugin.is_enabled():
        processed_data = plugin.process_data(raw_data)
```

## 数据源扩展

### 数据源接口规范

要扩展新的数据源，需要实现以下接口：

```python
from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict, Any, Optional

class DataSourceInterface(ABC):
    """数据源接口"""
    
    @abstractmethod
    def get_name(self) -> str:
        """获取数据源名称"""
        pass
    
    @abstractmethod
    def get_supported_assets(self) -> List[str]:
        """获取支持的资产类型"""
        pass
    
    @abstractmethod
    def get_supported_frequencies(self) -> List[str]:
        """获取支持的数据频率"""
        pass
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def get_symbols(self, asset_type: str) -> List[str]:
        """获取标的代码列表"""
        pass
    
    @abstractmethod
    def get_kline_data(self, symbols: List[str], start_date: str, 
                       end_date: str, frequency: str) -> pd.DataFrame:
        """获取K线数据"""
        pass
    
    @abstractmethod
    def get_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时数据"""
        pass
    
    @abstractmethod
    def get_fundamental_data(self, symbols: List[str], 
                           data_type: str) -> pd.DataFrame:
        """获取基本面数据"""
        pass
```

### 示例：实现自定义数据源

```python
import requests
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

class MyCustomDataSource(DataSourceInterface):
    """自定义数据源实现"""
    
    def __init__(self):
        self.api_url = None
        self.api_key = None
        self.session = None
    
    def get_name(self) -> str:
        return "MyCustomDataSource"
    
    def get_supported_assets(self) -> List[str]:
        return ['stock', 'index', 'fund', 'bond']
    
    def get_supported_frequencies(self) -> List[str]:
        return ['1min', '5min', '15min', '30min', '1h', '1d', '1w', '1M']
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """建立连接"""
        try:
            self.api_url = config['api_url']
            self.api_key = config['api_key']
            
            # 创建会话
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            
            # 测试连接
            response = self.session.get(f"{self.api_url}/health")
            return response.status_code == 200
            
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.session:
            self.session.close()
            self.session = None
    
    def get_symbols(self, asset_type: str) -> List[str]:
        """获取标的代码列表"""
        try:
            response = self.session.get(
                f"{self.api_url}/symbols",
                params={'asset_type': asset_type}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['symbols']
            else:
                return []
                
        except Exception as e:
            print(f"获取标的列表失败: {e}")
            return []
    
    def get_kline_data(self, symbols: List[str], start_date: str, 
                       end_date: str, frequency: str) -> pd.DataFrame:
        """获取K线数据"""
        try:
            response = self.session.post(
                f"{self.api_url}/kline",
                json={
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'frequency': frequency
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data['records'])
                
                # 标准化列名
                column_mapping = {
                    'ts': 'timestamp',
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume',
                    'a': 'amount'
                }
                df = df.rename(columns=column_mapping)
                
                # 转换数据类型
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
                df[numeric_columns] = df[numeric_columns].astype(float)
                
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """获取实时数据"""
        try:
            response = self.session.post(
                f"{self.api_url}/realtime",
                json={'symbols': symbols}
            )
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data['records'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取实时数据失败: {e}")
            return pd.DataFrame()
    
    def get_fundamental_data(self, symbols: List[str], 
                           data_type: str) -> pd.DataFrame:
        """获取基本面数据"""
        try:
            response = self.session.post(
                f"{self.api_url}/fundamental",
                json={
                    'symbols': symbols,
                    'data_type': data_type
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return pd.DataFrame(data['records'])
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取基本面数据失败: {e}")
            return pd.DataFrame()
```

### 注册自定义数据源

```python
from core.datasources.manager import DataSourceManager

# 创建数据源管理器
ds_manager = DataSourceManager()

# 注册自定义数据源
ds_manager.register_datasource(
    name='my_custom_source',
    datasource_class=MyCustomDataSource,
    config={
        'api_url': 'https://api.example.com/v1',
        'api_key': 'your_api_key_here'
    }
)

# 测试数据源
if ds_manager.test_connection('my_custom_source'):
    print("数据源连接成功")
else:
    print("数据源连接失败")
```

## 错误处理

### 错误代码规范

系统使用标准化的错误代码来标识不同类型的错误：

#### 通用错误 (1000-1999)
- `1000`: 未知错误
- `1001`: 参数无效
- `1002`: 资源不存在
- `1003`: 权限不足
- `1004`: 操作超时
- `1005`: 系统繁忙

#### 认证错误 (2000-2099)
- `2000`: 认证失败
- `2001`: API密钥无效
- `2002`: API密钥过期
- `2003`: 权限不足
- `2004`: 账户被锁定

#### 任务错误 (3000-3099)
- `3000`: 任务创建失败
- `3001`: 任务不存在
- `3002`: 任务状态无效
- `3003`: 任务配置错误
- `3004`: 任务执行失败

#### 数据错误 (4000-4099)
- `4000`: 数据获取失败
- `4001`: 数据格式错误
- `4002`: 数据源连接失败
- `4003`: 数据质量异常
- `4004`: 数据不存在

#### 系统错误 (5000-5099)
- `5000`: 内部服务器错误
- `5001`: 数据库连接失败
- `5002`: 存储空间不足
- `5003`: 内存不足
- `5004`: 服务不可用

### 错误响应格式

```json
{
    "success": false,
    "error": {
        "code": "3001",
        "message": "任务不存在",
        "details": "指定的任务ID 'task_123' 不存在",
        "timestamp": "2024-01-01T12:00:00Z",
        "request_id": "req_123456789"
    }
}
```

### Python SDK错误处理

```python
from hikyuu_client.exceptions import (
    HikyuuAPIError,
    AuthenticationError,
    TaskNotFoundError,
    DataSourceError,
    RateLimitError
)

try:
    # API调用
    task = client.get_task('invalid_task_id')
    
except TaskNotFoundError as e:
    print(f"任务不存在: {e.message}")
    
except AuthenticationError as e:
    print(f"认证失败: {e.message}")
    # 重新获取API密钥
    
except DataSourceError as e:
    print(f"数据源错误: {e.message}")
    # 检查数据源配置
    
except RateLimitError as e:
    print(f"请求频率限制: {e.message}")
    # 等待后重试
    time.sleep(e.retry_after)
    
except HikyuuAPIError as e:
    print(f"API错误: {e.error_code} - {e.message}")
    # 通用错误处理
```

### 重试机制

```python
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1, backoff=2):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (RateLimitError, HikyuuAPIError) as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    wait_time = delay * (backoff ** (retries - 1))
                    print(f"请求失败，{wait_time}秒后重试 ({retries}/{max_retries})")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator

# 使用重试装饰器
@retry_on_error(max_retries=3, delay=2)
def get_task_with_retry(task_id):
    return client.get_task(task_id)
```

## 最佳实践

### API使用最佳实践

#### 1. 认证和安全

```python
# 安全存储API密钥
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('HIKYUU_API_KEY')

# 使用HTTPS连接
client = HikyuuClient(
    host='api.hikyuu.com',
    port=443,
    use_ssl=True,
    api_key=api_key
)
```

#### 2. 错误处理和重试

```python
import time
import random

def exponential_backoff_retry(func, max_retries=3):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise e
            
            # 指数退避 + 随机抖动
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)
```

#### 3. 批量操作优化

```python
# 批量创建任务
def create_tasks_in_batch(configs, batch_size=10):
    """批量创建任务"""
    results = []
    
    for i in range(0, len(configs), batch_size):
        batch = configs[i:i + batch_size]
        batch_results = []
        
        for config in batch:
            try:
                task = client.create_task(config)
                batch_results.append(task)
            except Exception as e:
                print(f"任务创建失败: {e}")
                batch_results.append(None)
        
        results.extend(batch_results)
        
        # 批次间延迟，避免请求过于频繁
        if i + batch_size < len(configs):
            time.sleep(0.5)
    
    return results
```

#### 4. 资源管理

```python
from contextlib import contextmanager

@contextmanager
def hikyuu_client_context(host, port, api_key):
    """客户端上下文管理器"""
    client = HikyuuClient(host=host, port=port, api_key=api_key)
    try:
        yield client
    finally:
        client.close()  # 确保资源被正确释放

# 使用上下文管理器
with hikyuu_client_context('localhost', 8080, api_key) as client:
    tasks = client.get_tasks()
    # 客户端会自动关闭
```

### 性能优化建议

#### 1. 连接池配置

```python
from hikyuu_client import HikyuuClient

# 配置连接池
client = HikyuuClient(
    host='localhost',
    port=8080,
    api_key=api_key,
    pool_connections=10,  # 连接池大小
    pool_maxsize=20,      # 最大连接数
    max_retries=3         # 最大重试次数
)
```

#### 2. 异步操作

```python
import asyncio
from hikyuu_client.async_client import AsyncHikyuuClient

async def async_data_processing():
    """异步数据处理"""
    async with AsyncHikyuuClient(
        host='localhost',
        port=8080,
        api_key=api_key
    ) as client:
        
        # 并发获取多个任务状态
        task_ids = ['task_001', 'task_002', 'task_003']
        tasks = await asyncio.gather(*[
            client.get_task(task_id) for task_id in task_ids
        ])
        
        return tasks

# 运行异步任务
tasks = asyncio.run(async_data_processing())
```

#### 3. 缓存策略

```python
from functools import lru_cache
import time

class CachedHikyuuClient:
    def __init__(self, client):
        self.client = client
        self._cache_timestamps = {}
    
    @lru_cache(maxsize=128)
    def get_system_status_cached(self, cache_key):
        """缓存系统状态"""
        return self.client.get_system_status()
    
    def get_system_status(self, cache_duration=60):
        """获取系统状态（带缓存）"""
        current_time = time.time()
        cache_key = int(current_time // cache_duration)
        return self.get_system_status_cached(cache_key)
```

### 开发调试技巧

#### 1. 启用调试日志

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hikyuu_client')

# 创建客户端时启用调试
client = HikyuuClient(
    host='localhost',
    port=8080,
    api_key=api_key,
    debug=True  # 启用调试模式
)
```

#### 2. 请求响应拦截

```python
class DebuggingClient(HikyuuClient):
    def _make_request(self, method, url, **kwargs):
        """拦截请求进行调试"""
        print(f"请求: {method} {url}")
        if 'json' in kwargs:
            print(f"请求体: {kwargs['json']}")
        
        response = super()._make_request(method, url, **kwargs)
        
        print(f"响应状态: {response.status_code}")
        print(f"响应体: {response.text[:200]}...")  # 只显示前200字符
        
        return response
```

#### 3. 性能监控

```python
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise e
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"函数 {func.__name__} 执行时间: {duration:.3f}秒")
            print(f"执行结果: {'成功' if success else '失败'}")
        
        return result
    return wrapper

# 使用性能监控
@monitor_performance
def get_large_dataset():
    return client.get_stock_data(
        symbols=['000001', '000002'],
        start_date='2020-01-01',
        end_date='2024-01-01'
    )
```

## 版本更新和兼容性

### API版本管理

系统采用语义化版本管理，API版本格式为 `v{major}.{minor}`：

- **主版本号 (major)**: 不兼容的API变更
- **次版本号 (minor)**: 向后兼容的功能性新增

### 版本兼容性

| API版本 | 系统版本 | 兼容性 | 说明 |
|---------|----------|--------|------|
| v3.0    | 3.0+     | 当前版本 | 最新功能和接口 |
| v2.1    | 2.1-2.9  | 维护模式 | 仅修复关键bug |
| v2.0    | 2.0-2.0  | 已废弃 | 不再维护 |

### 迁移指南

#### 从v2.x迁移到v3.0

**主要变更**:
1. 认证方式从Basic Auth改为Bearer Token
2. 响应格式标准化
3. 新增异常管理API
4. WebSocket API重构

**迁移步骤**:

```python
# v2.x 代码
import requests
import base64

username = 'your_username'
password = 'your_password'
credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()

headers = {
    'Authorization': f'Basic {credentials}'
}

# v3.0 代码
headers = {
    'Authorization': f'Bearer {api_key}'
}
```

**响应格式变更**:

```python
# v2.x 响应
{
    "status": "success",
    "result": {...}
}

# v3.0 响应
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}
```

## 社区和支持

### 开发者社区

- **GitHub仓库**: [https://github.com/hikyuu/hikyuu-ui](https://github.com/hikyuu/hikyuu-ui)
- **问题反馈**: [https://github.com/hikyuu/hikyuu-ui/issues](https://github.com/hikyuu/hikyuu-ui/issues)
- **讨论区**: [https://github.com/hikyuu/hikyuu-ui/discussions](https://github.com/hikyuu/hikyuu-ui/discussions)

### 技术支持

- **官方文档**: [https://docs.hikyuu.org](https://docs.hikyuu.org)
- **API文档**: [https://api.hikyuu.org/docs](https://api.hikyuu.org/docs)
- **技术支持**: support@hikyuu.org

### 贡献指南

欢迎开发者为项目做出贡献：

1. **Fork项目**: 在GitHub上fork项目
2. **创建分支**: 为新功能创建专门的分支
3. **编写代码**: 遵循项目的编码规范
4. **编写测试**: 为新功能编写相应的测试
5. **提交PR**: 提交Pull Request并描述变更内容

### 许可证

本项目采用MIT许可证，详情请参见[LICENSE](LICENSE)文件。

---

*本文档最后更新于2024年1月，如有疑问或建议，请联系开发团队。*
