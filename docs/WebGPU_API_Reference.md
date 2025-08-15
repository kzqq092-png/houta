# WebGPU硬件加速系统 API参考文档

## 概述

FactorWeave-Quant WebGPU硬件加速系统为量化分析平台提供高性能图表渲染能力。系统采用渐进式降级架构，支持WebGPU、OpenGL、Canvas2D、matplotlib等多种渲染后端，确保在各种环境下都能提供最佳性能。

## 核心架构

```
WebGPU System
├── Environment Detection    # 环境检测
├── Compatibility Testing   # 兼容性测试
├── Performance Benchmarks  # 性能基准测试
├── Error Recovery          # 错误恢复
├── Memory Management        # 内存管理
├── Pipeline Optimization   # 管道优化
└── Rendering Integration   # 渲染集成
```

## 1. 环境检测模块 (core.webgpu.environment)

### WebGPUEnvironment

检测WebGPU运行环境的核心类。

```python
from core.webgpu.environment import WebGPUEnvironment

# 创建环境检测器
env = WebGPUEnvironment()

# 检测WebGPU支持
support_info = env.detect_webgpu_support()
print(f"WebGPU支持: {support_info['supported']}")
print(f"支持级别: {support_info['support_level']}")

# 检测GPU信息
gpu_info = env.detect_gpu_capabilities()
print(f"GPU厂商: {gpu_info['vendor']}")
print(f"GPU型号: {gpu_info['renderer']}")
```

#### 主要方法

- `detect_webgpu_support() -> Dict[str, Any]`: 检测WebGPU支持情况
- `detect_gpu_capabilities() -> Dict[str, Any]`: 检测GPU能力
- `get_browser_info() -> Dict[str, str]`: 获取浏览器信息
- `is_webgpu_available() -> bool`: 快速检查WebGPU可用性

## 2. 兼容性测试模块 (core.webgpu.compatibility_testing)

### CompatibilityTestSuite

执行全面兼容性测试的主要类。

```python
from core.webgpu.compatibility_testing import CompatibilityTestSuite, run_compatibility_test

# 快速兼容性检查
is_compatible = check_webgpu_compatibility()

# 详细兼容性测试
test_suite = CompatibilityTestSuite()
report = test_suite.run_all_tests()

print(f"总体兼容性: {report.overall_compatibility.value}")
print(f"性能得分: {report.performance_score:.1f}/100")
print(f"测试通过率: {report.test_summary['passed']}/{report.test_summary['total']}")

# 保存测试报告
test_suite.save_report(report, "compatibility_report.json")
```

#### 兼容性等级

- `EXCELLENT`: 完全兼容，性能优异
- `GOOD`: 良好兼容，性能较好  
- `FAIR`: 基本兼容，性能一般
- `POOR`: 兼容性差，性能较差
- `UNSUPPORTED`: 不支持

### 专项测试类

```python
# 浏览器兼容性测试
browser_test = BrowserCompatibilityTest()
browser_result = browser_test.test_webgpu_support()

# GPU硬件兼容性测试
gpu_test = GPUCompatibilityTest()
gpu_result = gpu_test.test_gpu_compatibility()

# 操作系统兼容性测试
os_test = OSCompatibilityTest()
os_result = os_test.test_os_compatibility()

# WebGPU特性支持测试
feature_test = WebGPUFeatureTest()
feature_result = feature_test.test_feature_support()
```

## 3. 性能基准测试模块 (core.webgpu.performance_benchmarks)

### PerformanceBenchmarkSuite

执行性能基准测试的主要类。

```python
from core.webgpu.performance_benchmarks import (
    PerformanceBenchmarkSuite, 
    BenchmarkConfig,
    RenderingEngine,
    run_quick_performance_test
)

# 快速性能测试
def my_render_function():
    # 您的渲染逻辑
    pass

result = run_quick_performance_test(my_render_function, RenderingEngine.WEBGPU)
print(f"平均帧率: {result.metrics.frame_rate:.1f} FPS")
print(f"内存使用: {result.metrics.memory_usage_mb:.1f} MB")

# 完整性能测试套件
config = BenchmarkConfig(
    test_duration_seconds=30,
    target_fps=60,
    chart_width=1920,
    chart_height=1080
)

benchmark_suite = PerformanceBenchmarkSuite(config)

# 定义不同引擎的渲染函数
render_functions = {
    RenderingEngine.WEBGPU: webgpu_render_function,
    RenderingEngine.OPENGL: opengl_render_function,
    RenderingEngine.CANVAS2D: canvas2d_render_function
}

# 运行完整测试
report = benchmark_suite.run_full_benchmark_suite(render_functions)
print(f"性能排名: {report['performance_ranking']}")
```

### 性能指标

- `frame_rate`: 平均帧率 (FPS)
- `memory_usage_mb`: 内存使用 (MB)
- `gpu_utilization_percent`: GPU利用率 (%)
- `avg_frame_time`: 平均帧时间 (ms)
- `input_latency_ms`: 输入延迟 (ms)

### 对比测试

```python
from core.webgpu.performance_benchmarks import compare_webgpu_vs_traditional

# WebGPU vs 传统渲染对比
comparison = compare_webgpu_vs_traditional(
    webgpu_function=webgpu_render,
    traditional_function=matplotlib_render
)

print(f"性能提升: {comparison.performance_improvement:.1f}%")
print(f"内存优化: {comparison.memory_improvement:.1f}%")
```

## 4. 错误处理模块 (core.webgpu.error_recovery)

### ErrorRecoveryManager

智能错误处理和恢复的核心类。

```python
from core.webgpu.error_recovery import (
    get_error_recovery_manager,
    handle_webgpu_error,
    setup_error_recovery_context
)

# 获取全局错误管理器
error_manager = get_error_recovery_manager()

# 设置错误恢复上下文
context = setup_error_recovery_context(
    current_engine="webgpu",
    switch_engine_function=lambda engine: switch_to_engine(engine),
    quality_settings={'resolution_scale': 1.0, 'antialiasing': 4}
)

# 处理错误
try:
    # WebGPU操作
    webgpu_operation()
except Exception as e:
    recovery_result = error_manager.handle_error(
        str(e), 
        exception=e, 
        context=context
    )
    
    if recovery_result and recovery_result.success:
        print(f"错误已恢复: {recovery_result.message}")
        if recovery_result.new_engine:
            print(f"已切换到: {recovery_result.new_engine}")
    else:
        print("错误无法自动恢复，需要用户干预")
```

### 错误类别

- `WEBGPU_NOT_SUPPORTED`: WebGPU不支持
- `DEVICE_LOST`: GPU设备丢失
- `OUT_OF_MEMORY`: 内存不足
- `SHADER_COMPILATION`: 着色器编译错误
- `RENDERING_ERROR`: 渲染错误
- `CONTEXT_LOST`: 上下文丢失

### 恢复策略

- `RETRY`: 重试操作
- `RECREATE_DEVICE`: 重新创建设备
- `FALLBACK_ENGINE`: 降级到备用引擎
- `REDUCE_QUALITY`: 降低质量设置
- `CLEAR_CACHE`: 清理缓存
- `USER_INTERVENTION`: 需要用户干预

## 5. 内存管理模块 (core.webgpu.memory_manager)

### WebGPUMemoryManager

GPU内存管理和优化的核心类。

```python
from core.webgpu.memory_manager import WebGPUMemoryManager

# 创建内存管理器
memory_manager = WebGPUMemoryManager()

# 申请GPU内存
buffer_id = memory_manager.allocate_buffer(
    size=1024*1024,  # 1MB
    usage='vertex',
    priority='high'
)

# 创建纹理
texture_id = memory_manager.allocate_texture(
    width=1024,
    height=1024,
    format='rgba8',
    usage='render_target'
)

# 获取内存统计
stats = memory_manager.get_memory_statistics()
print(f"已用内存: {stats.used_memory_mb:.1f}MB")
print(f"空闲内存: {stats.free_memory_mb:.1f}MB")
print(f"内存利用率: {stats.utilization_percent:.1f}%")

# 手动清理内存
memory_manager.garbage_collect()

# 释放资源
memory_manager.deallocate_buffer(buffer_id)
memory_manager.deallocate_texture(texture_id)
```

### 内存类型

- `VERTEX`: 顶点数据
- `INDEX`: 索引数据  
- `UNIFORM`: 统一变量
- `TEXTURE`: 纹理数据
- `RENDER_TARGET`: 渲染目标

### 内存优先级

- `HIGH`: 高优先级，优先分配
- `MEDIUM`: 中等优先级
- `LOW`: 低优先级，可被回收

## 6. 管道优化模块 (core.webgpu.pipeline_optimizer)

### WebGPUPipelineOptimizer

渲染管道优化和批处理管理。

```python
from core.webgpu.pipeline_optimizer import WebGPUPipelineOptimizer

# 创建管道优化器
optimizer = WebGPUPipelineOptimizer()

# 添加渲染命令
command_id = optimizer.add_render_command(
    pipeline='chart_pipeline',
    vertex_buffer='chart_vertices',
    index_buffer='chart_indices',
    uniforms={'mvp_matrix': mvp_matrix},
    priority='high'
)

# 批量提交渲染命令
batch_commands = [
    {'pipeline': 'line_pipeline', 'data': line_data},
    {'pipeline': 'point_pipeline', 'data': point_data},
    {'pipeline': 'text_pipeline', 'data': text_data}
]

batch_id = optimizer.submit_batch(batch_commands)

# 执行渲染
optimizer.execute_render_queue()

# 获取性能统计
perf_stats = optimizer.get_performance_statistics()
print(f"渲染批次数: {perf_stats.total_batches}")
print(f"平均批次大小: {perf_stats.avg_batch_size:.1f}")
print(f"GPU利用率: {perf_stats.gpu_utilization:.1f}%")
```

### 渲染优先级

- `CRITICAL`: 关键渲染，立即执行
- `HIGH`: 高优先级
- `MEDIUM`: 中等优先级
- `LOW`: 低优先级，可延迟执行

## 7. 渲染集成模块 (optimization.webgpu_chart_renderer)

### WebGPUChartRenderer

高级图表渲染接口。

```python
from optimization.webgpu_chart_renderer import WebGPUChartRenderer

# 创建渲染器
renderer = WebGPUChartRenderer(
    width=1920,
    height=1080,
    enable_antialiasing=True,
    enable_optimization=True
)

# 渲染K线图
kline_data = {
    'dates': dates,
    'open': open_prices,
    'high': high_prices,
    'low': low_prices,
    'close': close_prices,
    'volume': volumes
}

renderer.render_kline_chart(kline_data, style='candlestick')

# 渲染技术指标
indicator_data = {
    'ma5': ma5_values,
    'ma10': ma10_values,
    'ma20': ma20_values
}

renderer.render_indicators(indicator_data)

# 添加交互功能
renderer.enable_zoom_pan()
renderer.enable_crosshair()

# 导出图像
renderer.export_image('chart.png', format='png')
```

## 8. 管理器集成 (core.webgpu.manager)

### WebGPUManager

统一的WebGPU系统管理接口。

```python
from core.webgpu.manager import WebGPUManager

# 创建管理器（单例模式）
manager = WebGPUManager.get_instance()

# 初始化系统
init_result = manager.initialize()
if init_result.success:
    print(f"WebGPU系统初始化成功，使用引擎: {init_result.active_engine}")
else:
    print(f"初始化失败: {init_result.error_message}")

# 获取系统状态
status = manager.get_system_status()
print(f"当前引擎: {status.current_engine}")
print(f"系统性能: {status.performance_level}")
print(f"内存使用: {status.memory_usage_mb}MB")

# 切换渲染引擎
switch_result = manager.switch_engine('opengl')
if switch_result.success:
    print("引擎切换成功")

# 清理系统
manager.cleanup()
```

## 使用最佳实践

### 1. 初始化检查

```python
# 系统启动时进行兼容性检查
from core.webgpu.compatibility_testing import check_webgpu_compatibility

if check_webgpu_compatibility():
    print("系统支持WebGPU硬件加速")
    # 使用WebGPU渲染
else:
    print("使用传统渲染方式")
    # 降级到matplotlib
```

### 2. 错误处理

```python
# 在所有WebGPU操作中添加错误处理
from core.webgpu.error_recovery import handle_webgpu_error

try:
    # WebGPU操作
    webgpu_render_operation()
except Exception as e:
    # 自动错误恢复
    recovery_result = handle_webgpu_error(str(e), e, context)
    if recovery_result and recovery_result.success:
        # 恢复成功，继续操作
        continue_rendering()
    else:
        # 降级到备用方案
        fallback_to_traditional_rendering()
```

### 3. 性能监控

```python
# 定期进行性能监控
from core.webgpu.performance_benchmarks import run_quick_performance_test

def monitor_performance():
    result = run_quick_performance_test(current_render_function)
    
    if result.metrics.frame_rate < 30:
        # 性能不足，降低质量
        reduce_rendering_quality()
    elif result.metrics.memory_usage_mb > 1000:
        # 内存使用过高，清理缓存
        clear_render_cache()
```

### 4. 内存管理

```python
# 合理管理GPU内存
from core.webgpu.memory_manager import WebGPUMemoryManager

memory_manager = WebGPUMemoryManager()

# 定期检查内存使用
stats = memory_manager.get_memory_statistics()
if stats.utilization_percent > 90:
    # 内存使用率过高，进行清理
    memory_manager.garbage_collect()
    memory_manager.optimize_memory_layout()
```

## 配置选项

### 系统配置

```python
webgpu_config = {
    # 渲染设置
    'default_resolution': (1920, 1080),
    'enable_antialiasing': True,
    'antialiasing_samples': 4,
    'enable_vsync': True,
    
    # 性能设置
    'max_texture_size': 4096,
    'max_buffer_size': 64 * 1024 * 1024,  # 64MB
    'enable_gpu_timing': True,
    'enable_memory_profiling': True,
    
    # 兼容性设置
    'enable_fallback': True,
    'fallback_engines': ['opengl', 'canvas2d', 'matplotlib'],
    'auto_quality_adjustment': True,
    
    # 调试设置
    'enable_debug_layers': False,
    'log_level': 'INFO',
    'enable_error_recovery': True
}
```

## 故障排除

### 常见问题

1. **WebGPU不支持**
   - 确保使用支持WebGPU的浏览器版本
   - 检查GPU驱动是否为最新版本
   - 系统会自动降级到兼容模式

2. **性能问题**
   - 使用性能基准测试诊断问题
   - 检查GPU内存使用情况
   - 考虑降低渲染质量设置

3. **内存泄漏**
   - 定期调用垃圾回收
   - 检查资源是否正确释放
   - 使用内存管理器监控使用情况

4. **渲染错误**
   - 检查错误恢复日志
   - 验证数据格式是否正确
   - 确保着色器编译成功

### 调试工具

```python
# 启用调试模式
from core.webgpu.manager import WebGPUManager

manager = WebGPUManager.get_instance()
manager.enable_debug_mode()

# 获取详细系统信息
debug_info = manager.get_debug_info()
print(debug_info)

# 导出错误报告
manager.export_error_report('webgpu_debug_report.json')
```

## API版本兼容性

当前API版本：v1.0.0

- 支持WebGPU规范版本：1.0
- 最低Python版本：3.8
- 推荐PyQt版本：5.15+

## 更新日志

### v1.0.0 (2025-01-18)
- 初始版本发布
- 完整的WebGPU硬件加速系统
- 兼容性测试框架
- 性能基准测试
- 智能错误恢复
- 内存管理优化
- 渲染管道优化 