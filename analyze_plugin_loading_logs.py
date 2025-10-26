"""分析插件加载日志"""
import re

print("="*80)
print("分析插件加载日志")
print("="*80)

log_file = 'logs/factorweave_2025-10-18.log'

# 关键词列表
keywords = [
    '开始发现和注册',
    '插件管理器中有',
    '成功注册:',
    '插件注册统计',
    '插件发现和注册完成',
    '_register_plugins_from_plugin_manager',
    'discover_and_register_data_source_plugins',
    '数据源插件',
]

found_lines = []

try:
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"\n日志文件总行数: {len(lines)}")

    # 搜索关键行
    for i, line in enumerate(lines):
        for keyword in keywords:
            if keyword in line:
                found_lines.append((i+1, line.strip()))
                break

    print(f"找到相关日志: {len(found_lines)} 行\n")

    if found_lines:
        print("插件加载相关日志:")
        print("-"*80)
        for line_num, line in found_lines[-20:]:  # 只显示最后20行
            # 提取关键信息
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 5:
                    timestamp = parts[0].strip()
                    level = parts[1].strip()
                    message = '|'.join(parts[4:]).strip()
                    print(f"[{timestamp}] [{level}] {message[:100]}")
                else:
                    print(line[:120])
            else:
                print(line[:120])
    else:
        print("[WARNING] 未找到插件加载相关日志")
        print("\n可能的原因:")
        print("  1. 系统还在启动中")
        print("  2. 插件加载使用了不同的日志格式")
        print("  3. 新方法尚未被调用")

        # 搜索最近的启动相关日志
        print("\n最近的启动日志（最后30行）:")
        print("-"*80)
        for line in lines[-30:]:
            if any(k in line for k in ['INFO', 'WARNING', 'ERROR', 'ServiceBootstrap', 'PluginManager']):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        timestamp = parts[0].strip()
                        level = parts[1].strip()
                        message = '|'.join(parts[4:]).strip()
                        print(f"[{level}] {message[:100]}")

except FileNotFoundError:
    print(f"[ERROR] 日志文件不存在: {log_file}")
except Exception as e:
    print(f"[ERROR] 读取日志失败: {e}")

print("\n" + "="*80)
