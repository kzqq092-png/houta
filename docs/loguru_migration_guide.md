# FactorWeave-Quant 纯Loguru日志系统指南

## 概述

FactorWeave-Quant 已完成从传统 Python `logging` 模块到纯 Loguru 日志系统的迁移。本指南提供了新日志系统的详细使用说明。

## 🎯 迁移亮点

- ✅ **纯净架构**: 完全移除传统logging模块，使用100%纯Loguru
- ✅ **零配置**: 开箱即用，无需复杂的日志配置
- ✅ **结构化日志**: 原生支持JSON结构化日志记录
- ✅ **异步处理**: 内置异步日志处理，避免UI阻塞
- ✅ **智能异常处理**: 自动异常分析和恢复建议
- ✅ **PyQt5集成**: 无缝集成到UI组件中

## 📁 核心组件

### 1. 核心配置文件

```
core/
├── loguru_config.py          # 核心Loguru配置
├── loguru_manager_simple.py  # 简化管理器
├── loguru_interface.py       # 统一接口
└── loguru_performance_sink.py # 性能监控sink
```

### 2. UI集成文件

```
gui/
├── loguru_qt_handler.py       # PyQt5集成处理器
└── widgets/
    └── log_widget_loguru.py   # 纯Loguru日志控件
```

### 3. 错误处理系统

```
core/services/
└── error_service.py          # 基于Loguru的错误处理服务

utils/
└── exception_handler.py      # 增强的异常处理器
```

## 🚀 快速开始

### 基本使用

```python
from loguru import logger

# 基本日志记录
logger.info("这是一条信息日志")
logger.warning("这是一条警告日志")
logger.error("这是一条错误日志")
logger.success("这是一条成功日志")

# 异常日志（自动捕获堆栈跟踪）
try:
    result = 10 / 0
except ZeroDivisionError:
    logger.exception("发生除零错误")
```

### 结构化日志

```python
from loguru import logger

# 使用bind添加结构化数据
logger.bind(
    user_id="12345",
    operation="data_processing",
    module="stock_service"
).info("处理股票数据完成")

# 性能监控日志
logger.bind(
    performance=True,
    operation="chart_render",
    duration_ms=150,
    chart_type="kline"
).info("图表渲染完成")
```

### 错误处理集成

```python
from core.services.error_service import handle_error
from core.services.error_service import ErrorCategory, ErrorSeverity

try:
    # 可能出错的操作
    risky_operation()
except Exception as e:
    # 使用统一错误处理
    error_id = handle_error(
        e,
        context={"operation": "data_fetch", "symbol": "000001"},
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        auto_recover=True
    )
    logger.info(f"错误已记录，ID: {error_id}")
```

## 🔧 高级功能

### 1. 上下文管理

```python
# 创建带上下文的logger
stock_logger = logger.bind(
    module="stock_service",
    stock_code="000001",
    session_id="abc123"
)

stock_logger.info("开始处理股票数据")
stock_logger.debug("数据验证完成")
stock_logger.success("股票数据处理成功")
```

### 2. 自定义Sink

```python
from loguru import logger
from pathlib import Path

# 添加自定义日志文件
logger.add(
    Path("logs") / "custom_{time}.log",
    level="DEBUG",
    format="{time} | {level} | {name}:{function}:{line} - {message}",
    rotation="50 MB",
    retention="10 days",
    compression="zip",
    enqueue=True,  # 异步处理
    backtrace=True,
    diagnose=True
)
```

### 3. 条件过滤

```python
# 只记录特定模块的日志
logger.add(
    "logs/trading_only.log",
    filter=lambda record: "trading" in record["extra"]
)

# 使用过滤器
logger.bind(trading=True).info("交易相关日志")  # 会被记录
logger.info("普通日志")  # 不会被记录到trading_only.log
```

## 🎨 UI集成

### 日志控件使用

```python
from gui.widgets.log_widget_loguru import LogWidgetLoguru
from PyQt5.QtWidgets import QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 创建Loguru日志控件
        self.log_widget = LogWidgetLoguru()
        self.setCentralWidget(self.log_widget)
        
        # 日志控件会自动接收Loguru消息
        logger.info("主窗口初始化完成")
```

### 自定义UI Sink

```python
from gui.loguru_qt_handler import LoguruQtHandler

# 创建Qt处理器
qt_handler = LoguruQtHandler()

# 连接到UI组件
qt_handler.log_message.connect(your_widget.append_log)

# 注册到Loguru
logger.add(qt_handler.emit, level="INFO")
```

## 🧪 测试环境

### 测试配置

项目提供了完整的测试环境Loguru配置（`tests/conftest.py`）:

```python
import pytest
from loguru import logger

def test_with_loguru(test_logger, capture_logs):
    """使用Loguru的测试"""
    test_logger.info("测试日志消息")
    
    logs = capture_logs()
    assert len(logs) > 0
```

### 测试辅助工具

```python
def test_error_handling(loguru_helper, capture_logs, test_context):
    test_context.error("测试错误")
    
    logs = capture_logs()
    loguru_helper.assert_log_contains(logs, "测试错误", "ERROR")
    loguru_helper.assert_no_errors(logs)  # 确保没有意外错误
```

## 📊 性能监控

### 自动性能日志

```python
# 使用性能监控装饰器
from loguru import logger
import time

def performance_monitor(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        logger.bind(
            performance=True,
            function=func.__name__,
            duration_ms=duration * 1000,
            args_count=len(args),
            kwargs_count=len(kwargs)
        ).info(f"函数 {func.__name__} 执行完成")
        
        return result
    return wrapper

@performance_monitor
def process_data():
    # 你的业务逻辑
    pass
```

### 性能分析

```python
# 查询性能日志
from core.loguru_performance_sink import query_performance_logs

# 获取最近的性能数据
recent_performance = query_performance_logs(
    start_time=datetime.now() - timedelta(hours=1),
    operation="chart_render"
)
```

## 🔄 迁移指南

### 从旧代码迁移

#### 1. 替换导入

```python
# 旧代码
import logging
logger = logging.getLogger(__name__)

# 新代码
from loguru import logger
```

#### 2. 替换日志调用

```python
# 旧代码
logger.info(f"处理用户 {user_id} 的请求")

# 新代码 - 结构化日志
logger.bind(user_id=user_id).info("处理用户请求")
```

#### 3. 异常处理

```python
# 旧代码
try:
    risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}")

# 新代码 - 自动堆栈跟踪
try:
    risky_operation()
except Exception as e:
    logger.exception("操作失败")  # 自动包含完整堆栈信息
```

## 🛠️ 故障排除

### 常见问题

1. **日志未出现在文件中**
   ```python
   # 确保日志目录存在
   from pathlib import Path
   Path("logs").mkdir(exist_ok=True)
   ```

2. **UI日志显示异常**
   ```python
   # 检查Qt Sink注册
   from core.loguru_manager_simple import get_loguru_manager_simple
   manager = get_loguru_manager_simple()
   # 确保Qt sink已注册
   ```

3. **测试中日志缺失**
   ```python
   # 使用测试专用配置
   pytest tests/ -v  # conftest.py会自动配置测试环境
   ```

### 调试模式

```python
# 启用详细调试
logger.add(
    sys.stderr,
    level="TRACE",
    format="{time} | {level} | {name}:{function}:{line} | {extra} - {message}",
    colorize=True,
    backtrace=True,
    diagnose=True
)
```

## 📈 最佳实践

### 1. 结构化日志
- 使用 `bind()` 添加上下文信息
- 避免在消息中嵌入变量，使用结构化字段

### 2. 性能考虑
- 对高频日志使用 `enqueue=True` 异步处理
- 合理设置日志级别，避免过度日志记录

### 3. 错误处理
- 使用 `logger.exception()` 自动捕获堆栈跟踪
- 结合错误服务进行统一错误管理

### 4. UI集成
- 使用专用的UI sink避免阻塞主线程
- 为用户显示友好的错误消息

## 🔗 相关文档

- [Loguru官方文档](https://loguru.readthedocs.io/)
- [错误处理服务API](./error_service_api.md)
- [性能监控指南](./performance_monitoring.md)
- [测试环境配置](./testing_with_loguru.md)

## 🆕 版本历史

### v2.0.0 - 纯Loguru迁移
- 完全移除传统logging模块
- 引入结构化日志记录
- 新增智能错误处理系统
- 优化UI集成体验
- 完善测试环境支持

---

> 💡 **提示**: 如果您在使用过程中遇到问题，请查看日志文件 `logs/factorweave_*.log` 获取详细信息，或使用错误处理服务的分析功能。 