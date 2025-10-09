#!/usr/bin/env python
"""
最终修复所有Metrics类

确保：
1. 正确的字段顺序
2. 统一的基础字段（initialization_count, error_count, last_error, operation_count）
3. 正确的缩进
4. 无重复字段
"""

from pathlib import Path

print("="*80)
print("最终修复所有Metrics类")
print("="*80)

# DataMetrics
print("\n[1/4] 修复DataMetrics...")
data_file = Path('core/services/data_service.py')
content = data_file.read_text(encoding='utf-8')

# 查找并替换DataMetrics定义
old_pattern = '''class DataMetrics:
    """数据服务指标"""
        # 基础指标字段（所有Metrics统一）
    total_operations: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.now)

    total_requests: int = 0'''

new_pattern = '''class DataMetrics:
    """数据服务指标"""
    # 基础指标字段（与BaseService一致）
    initialization_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    operation_count: int = 0
    
    # 数据服务特定字段
    total_requests: int = 0'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    data_file.write_text(content, encoding='utf-8')
    print("  ✅ DataMetrics已修复")
else:
    print("  ⚠️ DataMetrics未找到匹配模式")

# PluginMetrics
print("\n[2/4] 修复PluginMetrics...")
plugin_file = Path('core/services/plugin_service.py')
content = plugin_file.read_text(encoding='utf-8')

old_pattern = '''class PluginMetrics:
    """插件服务指标"""
        # 基础指标字段（所有Metrics统一）
    total_operations: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.now)

    total_plugins: int = 0'''

new_pattern = '''class PluginMetrics:
    """插件服务指标"""
    # 基础指标字段（与BaseService一致）
    initialization_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    operation_count: int = 0
    
    # 插件服务特定字段
    total_plugins: int = 0'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    plugin_file.write_text(content, encoding='utf-8')
    print("  ✅ PluginMetrics已修复")
else:
    print("  ⚠️ PluginMetrics未找到匹配模式")

# NetworkMetrics
print("\n[3/4] 修复NetworkMetrics...")
network_file = Path('core/services/network_service.py')
content = network_file.read_text(encoding='utf-8')

old_pattern = '''class NetworkMetrics:
    """网络服务指标"""
        # 基础指标字段（所有Metrics统一）
    total_operations: int = 0
    success_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.now)

    total_requests: int = 0'''

new_pattern = '''class NetworkMetrics:
    """网络服务指标"""
    # 基础指标字段（与BaseService一致）
    initialization_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    operation_count: int = 0
    
    # 网络服务特定字段
    total_requests: int = 0'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    network_file.write_text(content, encoding='utf-8')
    print("  ✅ NetworkMetrics已修复")
else:
    print("  ⚠️ NetworkMetrics未找到匹配模式")

# PerformanceMetrics检查
print("\n[4/4] 检查PerformanceMetrics...")
perf_file = Path('core/services/performance_service.py')
content = perf_file.read_text(encoding='utf-8')

if 'initialization_count' in content and 'class PerformanceMetrics' in content:
    print("  ✅ PerformanceMetrics已正确")
else:
    print("  ⚠️ PerformanceMetrics可能需要检查")

print("\n" + "="*80)
print("修复完成！")
print("="*80)
print("\n运行测试验证: python final_regression_test.py")
