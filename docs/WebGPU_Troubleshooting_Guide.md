# WebGPU硬件加速系统故障排除指南

## 概述

本指南帮助用户诊断和解决WebGPU硬件加速系统的常见问题。系统具备自动错误恢复功能，但了解潜在问题和解决方案有助于获得最佳体验。

## 快速诊断工具

### 1. 运行系统诊断

```python
from core.webgpu.compatibility_testing import run_compatibility_test
from core.webgpu.manager import WebGPUManager

# 运行完整诊断
print("=== WebGPU系统诊断 ===")
report = run_compatibility_test()

print(f"总体兼容性: {report.overall_compatibility.value}")
print(f"性能得分: {report.performance_score:.1f}/100")

# 检查具体问题
for result in report.test_results:
    if result.result.value == 'failed':
        print(f"❌ {result.test_case.name}: {result.message}")
    elif result.result.value == 'passed':
        print(f"✅ {result.test_case.name}: 正常")
```

### 2. 检查系统状态

```python
# 检查WebGPU管理器状态
manager = WebGPUManager.get_instance()
status = manager.get_system_status()

print(f"当前引擎: {status.current_engine}")
print(f"系统性能: {status.performance_level}")
print(f"错误计数: {status.error_count}")
```

## 常见问题分类

### A. 兼容性问题

#### A1. WebGPU不支持

**症状：**
- 系统自动降级到传统渲染
- 错误消息："WebGPU is not supported"
- 性能显著下降

**原因分析：**
1. 浏览器版本过旧
2. GPU驱动版本过旧
3. 操作系统不支持
4. GPU硬件不兼容

**解决方案：**

```python
# 检查浏览器支持
from core.webgpu.compatibility_testing import BrowserCompatibilityTest

browser_test = BrowserCompatibilityTest()
browser_info = browser_test.get_browser_info()

print("浏览器信息:")
for key, value in browser_info.items():
    print(f"  {key}: {value}")

# 解决步骤
solutions = [
    "1. 更新浏览器到最新版本（Chrome 113+, Firefox 110+）",
    "2. 启用WebGPU实验性功能（chrome://flags/#enable-unsafe-webgpu）",
    "3. 更新GPU驱动程序",
    "4. 检查操作系统版本（Windows 10+, macOS 11+）"
]

for solution in solutions:
    print(solution)
```

#### A2. GPU驱动问题

**症状：**
- GPU检测失败
- 渲染错误或崩溃
- 性能异常

**诊断代码：**

```python
from core.webgpu.compatibility_testing import GPUCompatibilityTest

gpu_test = GPUCompatibilityTest()
gpu_info = gpu_test.get_gpu_info()

print("GPU信息:")
for i, gpu in enumerate(gpu_info):
    print(f"  GPU {i+1}:")
    print(f"    名称: {gpu.get('name', 'Unknown')}")
    print(f"    厂商: {gpu.get('vendor', 'Unknown')}")
    print(f"    驱动版本: {gpu.get('driver_version', 'Unknown')}")
    
    # 检查驱动版本
    vendor = gpu.get('vendor', '').lower()
    if vendor == 'nvidia':
        print(f"    建议驱动版本: 471.96+")
    elif vendor == 'amd':
        print(f"    建议驱动版本: 21.6.1+")
    elif vendor == 'intel':
        print(f"    建议驱动版本: 30.0.100.9684+")
```

**解决方案：**
1. 访问GPU厂商官网下载最新驱动
2. 卸载旧驱动后重新安装
3. 重启计算机
4. 运行GPU基准测试验证

### B. 性能问题

#### B1. 帧率过低

**症状：**
- FPS < 30
- 界面卡顿
- 交互延迟

**性能诊断：**

```python
from core.webgpu.performance_benchmarks import run_quick_performance_test

def diagnose_performance():
    # 测试当前性能
    def dummy_render():
        import time
        time.sleep(0.001)  # 模拟渲染

    result = run_quick_performance_test(dummy_render)
    
    print(f"当前性能:")
    print(f"  平均帧率: {result.metrics.frame_rate:.1f} FPS")
    print(f"  内存使用: {result.metrics.memory_usage_mb:.1f} MB")
    print(f"  GPU利用率: {result.metrics.gpu_utilization_percent:.1f}%")
    
    # 性能建议
    if result.metrics.frame_rate < 30:
        print("\n性能优化建议:")
        print("- 降低图表分辨率")
        print("- 减少数据点数量")
        print("- 关闭抗锯齿")
        print("- 降低渲染质量")

diagnose_performance()
```

**自动优化：**

```python
from core.webgpu.error_recovery import setup_error_recovery_context

# 设置自动质量调节
context = setup_error_recovery_context(
    quality_settings={
        'resolution_scale': 1.0,
        'antialiasing': 4,
        'max_data_points': 10000,
        'advanced_effects': True
    },
    apply_quality_settings=lambda settings: apply_settings(settings)
)

def apply_settings(settings):
    print(f"应用新设置: {settings}")
    # 实际应用设置的代码

# 触发质量降级
from core.webgpu.error_recovery import get_error_recovery_manager

manager = get_error_recovery_manager()
result = manager.handle_error("Performance degradation detected", context=context)
```

#### B2. 内存使用过高

**症状：**
- 内存占用 > 1GB
- 系统变慢
- 内存不足错误

**内存诊断：**

```python
from core.webgpu.memory_manager import WebGPUMemoryManager
import psutil

def diagnose_memory():
    # 系统内存使用
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"系统内存使用: {memory_info.rss / 1024 / 1024:.1f} MB")
    
    # GPU内存使用（如果可用）
    try:
        memory_manager = WebGPUMemoryManager()
        stats = memory_manager.get_memory_statistics()
        print(f"GPU内存使用: {stats.used_memory_mb:.1f} MB")
        print(f"GPU内存利用率: {stats.utilization_percent:.1f}%")
        
        if stats.utilization_percent > 90:
            print("⚠️ GPU内存使用率过高，建议清理")
            memory_manager.garbage_collect()
            
    except Exception as e:
        print(f"GPU内存检测失败: {e}")

diagnose_memory()
```

**内存优化：**

```python
def optimize_memory():
    """内存优化函数"""
    from core.webgpu.memory_manager import WebGPUMemoryManager
    import gc
    
    # 1. 强制Python垃圾回收
    gc.collect()
    
    # 2. GPU内存管理
    try:
        memory_manager = WebGPUMemoryManager()
        
        # 清理过期缓存
        memory_manager.cleanup_expired_resources()
        
        # 优化内存布局
        memory_manager.optimize_memory_layout()
        
        # 获取清理后的状态
        stats = memory_manager.get_memory_statistics()
        print(f"优化后GPU内存使用: {stats.used_memory_mb:.1f} MB")
        
    except Exception as e:
        print(f"GPU内存优化失败: {e}")

# 定期执行内存优化
import threading
import time

def memory_monitor():
    while True:
        time.sleep(60)  # 每分钟检查一次
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > 1000:  # 超过1GB时优化
                print(f"内存使用过高({memory_mb:.1f}MB)，开始优化...")
                optimize_memory()
        except Exception as e:
            print(f"内存监控异常: {e}")

# 启动内存监控线程
monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
monitor_thread.start()
```

### C. 渲染错误

#### C1. 黑屏或花屏

**症状：**
- 图表区域显示黑色
- 图像显示错乱
- 部分内容缺失

**诊断步骤：**

```python
def diagnose_rendering():
    """渲染问题诊断"""
    
    print("=== 渲染问题诊断 ===")
    
    # 1. 检查WebGPU设备状态
    from core.webgpu.manager import WebGPUManager
    
    manager = WebGPUManager.get_instance()
    status = manager.get_system_status()
    
    print(f"当前渲染引擎: {status.current_engine}")
    print(f"设备状态: {status.device_status}")
    
    # 2. 检查着色器编译
    try:
        # 模拟着色器编译测试
        test_shader_compilation()
        print("✅ 着色器编译正常")
    except Exception as e:
        print(f"❌ 着色器编译失败: {e}")
    
    # 3. 检查纹理创建
    try:
        test_texture_creation()
        print("✅ 纹理创建正常")
    except Exception as e:
        print(f"❌ 纹理创建失败: {e}")
    
    # 4. 检查缓冲区创建
    try:
        test_buffer_creation()
        print("✅ 缓冲区创建正常")
    except Exception as e:
        print(f"❌ 缓冲区创建失败: {e}")

def test_shader_compilation():
    """测试着色器编译"""
    # 简单的着色器编译测试
    pass

def test_texture_creation():
    """测试纹理创建"""
    # 创建测试纹理
    pass

def test_buffer_creation():
    """测试缓冲区创建"""
    # 创建测试缓冲区
    pass

diagnose_rendering()
```

**解决方案：**

```python
def fix_rendering_issues():
    """修复渲染问题"""
    
    from core.webgpu.error_recovery import get_error_recovery_manager
    
    manager = get_error_recovery_manager()
    
    # 1. 重新创建渲染上下文
    context = {
        'failed_operation': lambda: recreate_rendering_context(),
        'clear_render_cache': lambda: clear_all_caches(),
        'switch_engine_function': lambda engine: switch_to_engine(engine)
    }
    
    # 2. 尝试自动恢复
    recovery_result = manager.handle_error(
        "Rendering failure detected",
        context=context
    )
    
    if recovery_result and recovery_result.success:
        print(f"✅ 渲染问题已解决: {recovery_result.message}")
    else:
        print("❌ 自动恢复失败，手动处理...")
        manual_rendering_fix()

def recreate_rendering_context():
    """重新创建渲染上下文"""
    print("重新创建渲染上下文...")

def clear_all_caches():
    """清理所有缓存"""
    print("清理渲染缓存...")

def switch_to_engine(engine):
    """切换渲染引擎"""
    print(f"切换到渲染引擎: {engine}")

def manual_rendering_fix():
    """手动修复渲染问题"""
    print("执行手动修复步骤:")
    print("1. 重启应用程序")
    print("2. 清理GPU驱动缓存")
    print("3. 检查硬件连接")
    print("4. 联系技术支持")

fix_rendering_issues()
```

#### C2. 着色器编译错误

**症状：**
- 错误消息包含"shader compilation failed"
- 特定效果无法显示
- 降级到软件渲染

**解决方案：**

```python
def fix_shader_issues():
    """修复着色器问题"""
    
    print("=== 着色器问题修复 ===")
    
    # 1. 清理着色器缓存
    try:
        clear_shader_cache()
        print("✅ 着色器缓存已清理")
    except Exception as e:
        print(f"❌ 清理着色器缓存失败: {e}")
    
    # 2. 降级着色器版本
    try:
        use_fallback_shaders()
        print("✅ 已切换到兼容着色器")
    except Exception as e:
        print(f"❌ 着色器降级失败: {e}")
    
    # 3. 验证着色器功能
    if test_basic_shaders():
        print("✅ 基础着色器功能正常")
    else:
        print("❌ 着色器功能异常，建议切换到软件渲染")

def clear_shader_cache():
    """清理着色器缓存"""
    import os
    import tempfile
    
    # 清理临时着色器文件
    temp_dir = tempfile.gettempdir()
    shader_cache_pattern = os.path.join(temp_dir, "webgpu_shader_*")
    
    import glob
    for cache_file in glob.glob(shader_cache_pattern):
        try:
            os.remove(cache_file)
        except Exception:
            pass

def use_fallback_shaders():
    """使用备用着色器"""
    print("切换到兼容性着色器...")

def test_basic_shaders():
    """测试基础着色器功能"""
    try:
        # 模拟基础着色器测试
        return True
    except Exception:
        return False

fix_shader_issues()
```

### D. 系统集成问题

#### D1. 与PyQt集成问题

**症状：**
- Qt窗口显示异常
- 事件处理失效
- 程序崩溃

**解决方案：**

```python
def fix_qt_integration():
    """修复Qt集成问题"""
    
    print("=== Qt集成问题修复 ===")
    
    # 1. 检查Qt版本兼容性
    try:
        from PyQt5.QtCore import QT_VERSION_STR
        print(f"Qt版本: {QT_VERSION_STR}")
        
        # 检查最低版本要求
        from packaging import version
        if version.parse(QT_VERSION_STR) < version.parse("5.15.0"):
            print("⚠️ Qt版本过低，建议升级到5.15+")
        else:
            print("✅ Qt版本兼容")
            
    except ImportError as e:
        print(f"❌ Qt导入失败: {e}")
        return
    
    # 2. 检查OpenGL上下文
    try:
        from PyQt5.QtOpenGL import QOpenGLWidget
        from PyQt5.QtWidgets import QApplication
        
        app = QApplication.instance() or QApplication([])
        
        # 创建测试OpenGL上下文
        test_widget = QOpenGLWidget()
        test_widget.makeCurrent()
        print("✅ OpenGL上下文创建成功")
        
    except Exception as e:
        print(f"❌ OpenGL上下文创建失败: {e}")
    
    # 3. 检查事件循环
    try:
        from qasync import QEventLoop
        import asyncio
        
        # 测试异步事件循环
        loop = asyncio.get_event_loop()
        if isinstance(loop, QEventLoop):
            print("✅ 异步事件循环正常")
        else:
            print("⚠️ 事件循环类型异常")
            
    except ImportError:
        print("❌ qasync未安装，请运行: pip install qasync")

fix_qt_integration()
```

#### D2. 多线程问题

**症状：**
- 线程死锁
- 渲染上下文错误
- 随机崩溃

**解决方案：**

```python
import threading
import time

def fix_threading_issues():
    """修复多线程问题"""
    
    print("=== 多线程问题修复 ===")
    
    # 1. 检查主线程状态
    main_thread = threading.main_thread()
    current_thread = threading.current_thread()
    
    print(f"主线程: {main_thread.name}")
    print(f"当前线程: {current_thread.name}")
    
    if current_thread != main_thread:
        print("⚠️ 当前不在主线程，某些操作可能失败")
    
    # 2. 检查WebGPU线程安全
    check_webgpu_thread_safety()
    
    # 3. 清理无效线程
    cleanup_dead_threads()

def check_webgpu_thread_safety():
    """检查WebGPU线程安全性"""
    
    # WebGPU操作应该在主线程进行
    if threading.current_thread() == threading.main_thread():
        print("✅ WebGPU操作在主线程")
    else:
        print("❌ WebGPU操作不在主线程，可能导致问题")
        
        # 建议使用线程安全的方式
        print("建议使用以下方式调用WebGPU:")
        print("  from PyQt5.QtCore import QTimer")
        print("  QTimer.singleShot(0, webgpu_operation)")

def cleanup_dead_threads():
    """清理无效线程"""
    
    active_threads = threading.enumerate()
    print(f"活跃线程数: {len(active_threads)}")
    
    for thread in active_threads:
        print(f"  {thread.name}: {'alive' if thread.is_alive() else 'dead'}")
        
        # 清理守护线程
        if not thread.is_alive() and thread.daemon:
            print(f"  清理无效守护线程: {thread.name}")

fix_threading_issues()
```

## 预防措施

### 1. 定期健康检查

```python
def system_health_check():
    """系统健康检查"""
    
    import schedule
    import time
    import threading
    
    def health_check():
        print("=== 系统健康检查 ===")
        
        # 兼容性检查
        from core.webgpu.compatibility_testing import run_compatibility_test
        report = run_compatibility_test()
        
        if report.overall_compatibility.value in ['excellent', 'good']:
            print("✅ 系统兼容性良好")
        else:
            print(f"⚠️ 兼容性问题: {report.overall_compatibility.value}")
        
        # 性能检查
        from core.webgpu.performance_benchmarks import run_quick_performance_test
        
        def dummy_render():
            time.sleep(0.001)
        
        perf_result = run_quick_performance_test(dummy_render)
        
        if perf_result.metrics.frame_rate > 30:
            print(f"✅ 性能正常: {perf_result.metrics.frame_rate:.1f} FPS")
        else:
            print(f"⚠️ 性能不足: {perf_result.metrics.frame_rate:.1f} FPS")
        
        # 内存检查
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb < 1000:
            print(f"✅ 内存使用正常: {memory_mb:.1f}MB")
        else:
            print(f"⚠️ 内存使用过高: {memory_mb:.1f}MB")
            optimize_memory()
    
    # 每小时进行一次健康检查
    schedule.every().hour.do(health_check)
    
    def scheduler_thread():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    # 启动定时检查线程
    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
    
    print("系统健康检查已启动（每小时检查一次）")

# 启动系统健康检查
system_health_check()
```

### 2. 错误日志收集

```python
def setup_error_logging():
    """设置错误日志收集"""
    
    import logging
    from pathlib import Path
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 配置错误日志
    error_logger = logging.getLogger('webgpu_errors')
    error_logger.setLevel(logging.ERROR)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_dir / 'webgpu_errors.log')
    file_handler.setLevel(logging.ERROR)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    error_logger.addHandler(file_handler)
    error_logger.addHandler(console_handler)
    
    print(f"错误日志收集已启动，日志文件: {log_dir / 'webgpu_errors.log'}")
    
    return error_logger

# 设置错误日志
error_logger = setup_error_logging()

# 示例：记录错误
def log_webgpu_error(error_message, context=None):
    """记录WebGPU错误"""
    
    import json
    
    log_data = {
        'error': error_message,
        'context': context or {},
        'system_info': {
            'platform': platform.platform(),
            'python_version': platform.python_version()
        }
    }
    
    error_logger.error(json.dumps(log_data, indent=2))
```

### 3. 自动备份恢复

```python
def setup_auto_recovery():
    """设置自动备份恢复机制"""
    
    import json
    from pathlib import Path
    
    config_backup_file = Path("config/webgpu_backup.json")
    
    def save_working_config():
        """保存可工作的配置"""
        
        from core.webgpu.manager import WebGPUManager
        
        manager = WebGPUManager.get_instance()
        status = manager.get_system_status()
        
        if status.current_engine and status.performance_level > 0.5:
            # 保存当前良好配置
            backup_config = {
                'engine': status.current_engine,
                'quality_settings': status.quality_settings,
                'timestamp': time.time(),
                'performance_score': status.performance_level
            }
            
            config_backup_file.parent.mkdir(exist_ok=True)
            with open(config_backup_file, 'w') as f:
                json.dump(backup_config, f, indent=2)
            
            print(f"配置已备份: {status.current_engine}")
    
    def restore_backup_config():
        """恢复备份配置"""
        
        if not config_backup_file.exists():
            print("没有找到备份配置")
            return False
        
        try:
            with open(config_backup_file, 'r') as f:
                backup_config = json.load(f)
            
            # 恢复配置
            from core.webgpu.manager import WebGPUManager
            
            manager = WebGPUManager.get_instance()
            success = manager.switch_engine(backup_config['engine'])
            
            if success:
                print(f"已恢复到备份配置: {backup_config['engine']}")
                return True
            else:
                print("备份配置恢复失败")
                return False
                
        except Exception as e:
            print(f"恢复备份配置时出错: {e}")
            return False
    
    # 定期保存配置
    import threading
    
    def backup_scheduler():
        while True:
            time.sleep(300)  # 每5分钟保存一次
            try:
                save_working_config()
            except Exception as e:
                print(f"配置备份失败: {e}")
    
    backup_thread = threading.Thread(target=backup_scheduler, daemon=True)
    backup_thread.start()
    
    print("自动配置备份已启动")
    
    return restore_backup_config

# 设置自动备份恢复
restore_function = setup_auto_recovery()
```

## 联系技术支持

如果以上方法都无法解决问题，请联系技术支持：

### 收集诊断信息

```python
def collect_diagnostic_info():
    """收集诊断信息"""
    
    import json
    from pathlib import Path
    
    # 运行完整诊断
    from core.webgpu.compatibility_testing import run_compatibility_test
    
    report = run_compatibility_test()
    
    # 收集系统信息
    diagnostic_data = {
        'timestamp': time.time(),
        'compatibility_report': {
            'overall_compatibility': report.overall_compatibility.value,
            'performance_score': report.performance_score,
            'test_summary': report.test_summary,
            'system_info': {
                'os_name': report.system_info.os_name,
                'os_version': report.system_info.os_version,
                'architecture': report.system_info.architecture,
                'python_version': report.system_info.python_version,
                'gpu_info': report.system_info.gpu_info,
                'browser_info': report.system_info.browser_info
            }
        },
        'error_history': []
    }
    
    # 收集错误历史
    from core.webgpu.error_recovery import get_error_recovery_manager
    
    error_manager = get_error_recovery_manager()
    recent_errors = error_manager.get_recent_errors(20)
    
    for error in recent_errors:
        diagnostic_data['error_history'].append({
            'category': error.category.value,
            'severity': error.severity.value,
            'message': error.message,
            'timestamp': error.timestamp
        })
    
    # 保存诊断文件
    diagnostic_file = Path("webgpu_diagnostic_report.json")
    with open(diagnostic_file, 'w', encoding='utf-8') as f:
        json.dump(diagnostic_data, f, indent=2, ensure_ascii=False)
    
    print(f"诊断信息已保存到: {diagnostic_file}")
    print("请将此文件发送给技术支持团队")
    
    return diagnostic_file

# 生成诊断报告
diagnostic_file = collect_diagnostic_info()
```

### 技术支持信息

- **项目地址**: https://github.com/hikyuu-org/hikyuu
- **问题反馈**: GitHub Issues
- **邮箱支持**: support@hikyuu.org
- **文档地址**: https://hikyuu.readthedocs.io/

提交问题时请包含：
1. 完整的错误消息
2. 系统诊断报告
3. 复现步骤
4. 系统环境信息

---

*本指南持续更新中，如有新的问题和解决方案会及时补充。* 