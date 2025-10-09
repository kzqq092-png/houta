
# 如何启用并行启动

## 方法1: 修改配置文件（推荐）
编辑 config/startup_config.env:
```
ENABLE_PARALLEL_STARTUP=true
PARALLEL_WORKERS=4
STARTUP_MODE=parallel
```

## 方法2: 环境变量
```bash
# Windows PowerShell
$env:ENABLE_PARALLEL_STARTUP="true"
python main.py

# Linux/Mac
export ENABLE_PARALLEL_STARTUP=true
python main.py
```

## 方法3: 命令行参数
```bash
python main.py --parallel-startup
```

## 集成代码示例

在 main.py 或 service_bootstrap.py 中添加:

```python
import os
from parallel_service_bootstrap import ParallelServiceBootstrap

# 读取配置
enable_parallel = os.getenv('ENABLE_PARALLEL_STARTUP', 'false').lower() == 'true'

if enable_parallel:
    # 使用并行启动
    bootstrap = ParallelServiceBootstrap(container)
    results = bootstrap.bootstrap_parallel(max_workers=4)
    bootstrap.print_results(results)
else:
    # 使用传统顺序启动
    # ... 现有的顺序启动代码 ...
    pass
```

## 性能对比

基于演示结果:
- 顺序启动: 1.41秒
- 并行启动: 1.11秒  
- 性能提升: 21.2%

预期实际效果（考虑网络/数据库延迟）:
- 顺序启动: 15-20秒
- 并行启动: 10-13秒
- 性能提升: 30-40%

## 注意事项

1. **稳定性优先**: 默认关闭，需手动启用
2. **测试验证**: 启用后务必完整测试
3. **回退机制**: 随时可以关闭回到顺序模式
4. **监控日志**: 观察并行启动的执行情况

## 验证并行启动

```bash
# 1. 启用并行启动
$env:ENABLE_PARALLEL_STARTUP="true"

# 2. 运行主程序
python main.py

# 3. 观察日志输出
# 应该看到 "=== 并行服务启动模式 ===" 日志
# 以及各阶段的时间统计
```
