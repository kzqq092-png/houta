"""分析启动问题"""
import re
from collections import defaultdict

print("="*80)
print("启动问题全面分析")
print("="*80)

log_file = 'logs/factorweave_2025-10-18.log'

# 读取日志
try:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
except:
    print("[ERROR] 无法读取日志文件")
    exit(1)

print(f"\n日志总行数: {len(lines)}")

# 分析错误类型
errors = defaultdict(list)
warnings = defaultdict(list)

for i, line in enumerate(lines):
    if 'ERROR' in line:
        # 提取错误消息
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                error_msg = '|'.join(parts[4:]).strip()
                # 简化错误消息
                if 'performance_data_bridge' in error_msg:
                    key = 'performance_data_bridge'
                elif 'health_check' in error_msg and 'EastMoneyStockPlugin' in error_msg:
                    key = 'EastMoney_initialized'
                elif 'discover_and_register' in error_msg:
                    key = 'plugin_registration'
                else:
                    key = error_msg[:80]
                errors[key].append((i+1, line.strip()))

    elif 'WARNING' in line:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                warn_msg = '|'.join(parts[4:]).strip()
                key = warn_msg[:80]
                warnings[key].append((i+1, line.strip()))

print("\n" + "="*80)
print("错误统计")
print("="*80)

if errors:
    for error_type, occurrences in sorted(errors.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n[ERROR] {error_type}")
        print(f"  出现次数: {len(occurrences)}")
        # 只显示第一次出现
        line_num, line = occurrences[0]
        print(f"  首次出现: 第{line_num}行")
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                print(f"  消息: {parts[4].strip()[:100]}")
else:
    print("[OK] 没有ERROR级别日志")

print("\n" + "="*80)
print("关键问题分析")
print("="*80)

# 问题1: 性能指标收集
if 'performance_data_bridge' in errors:
    print("\n[问题1] 性能指标收集错误")
    print("  错误: argument 1 (impossible<bad format char>)")
    print("  影响: 性能监控功能")
    print("  严重性: 中等（不影响核心功能）")
    print("  建议: 检查performance_data_bridge的_collect_system_metrics方法")

# 问题2: EastMoney插件
if 'EastMoney_initialized' in errors:
    print("\n[问题2] EastMoney插件健康检查错误")
    print("  错误: 'EastMoneyStockPlugin' object has no attribute 'initialized'")
    print("  影响: 健康检查失败")
    print("  严重性: 低（插件仍可使用）")
    print("  建议: 为EastMoneyStockPlugin添加initialized属性")

# 搜索插件注册日志
print("\n" + "="*80)
print("插件注册日志分析")
print("="*80)

registration_keywords = [
    'discover_and_register_data_source_plugins',
    'register_plugins_from_plugin_manager',
    'DYNAMIC',
]

registration_logs = []
for i, line in enumerate(lines):
    if any(keyword in line for keyword in registration_keywords):
        registration_logs.append((i+1, line.strip()))

if registration_logs:
    print(f"\n找到 {len(registration_logs)} 条插件注册相关日志")
    print("\n最近的注册日志:")
    for line_num, line in registration_logs[-10:]:
        print(f"  [{line_num}] {line[:120]}")
else:
    print("\n[WARNING] 未找到插件注册相关日志")
    print("  可能原因:")
    print("    1. 新的动态加载方法未被调用")
    print("    2. 日志被emoji编码问题隐藏")
    print("    3. 插件注册在其他地方进行")

# 搜索启动成功标志
print("\n" + "="*80)
print("系统启动状态")
print("="*80)

startup_keywords = ['GUI initialized', '系统启动', 'MainWindow', 'QApplication']
startup_logs = []
for i, line in enumerate(lines):
    if any(keyword in line for keyword in startup_keywords):
        startup_logs.append((i+1, line.strip()))

if startup_logs:
    print(f"\n找到 {len(startup_logs)} 条启动相关日志")
    print("\n最近的启动日志:")
    for line_num, line in startup_logs[-5:]:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                print(f"  [{line_num}] {parts[4].strip()[:100]}")
else:
    print("\n[INFO] 未找到明确的启动成功日志")

# 总结
print("\n" + "="*80)
print("问题总结")
print("="*80)

print(f"\n错误类型数: {len(errors)}")
print(f"警告类型数: {len(warnings)}")

if len(errors) == 0:
    print("\n[SUCCESS] 系统运行正常，无ERROR")
elif len(errors) <= 2 and all(k in ['performance_data_bridge', 'EastMoney_initialized'] for k in errors.keys()):
    print("\n[PARTIAL SUCCESS] 系统运行，有非致命错误")
    print("  核心功能: 正常")
    print("  次要功能: 部分异常")
else:
    print("\n[WARNING] 系统有多个错误需要处理")

print("\n" + "="*80)
