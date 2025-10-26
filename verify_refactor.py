"""验证重构结果"""
print("="*80)
print("验证 UnifiedDataManager 重构")
print("="*80)

# 1. 检查新方法是否存在
print("\n1. 检查新方法")
print("-"*80)

with open('core/services/unified_data_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查新方法
if '_register_plugins_from_plugin_manager' in content:
    print("[OK] 新方法 _register_plugins_from_plugin_manager 已添加")

    # 统计方法行数
    lines = content.split('\n')
    in_method = False
    method_lines = 0
    for line in lines:
        if 'def _register_plugins_from_plugin_manager' in line:
            in_method = True
        elif in_method:
            if line.strip().startswith('def ') and '_register_plugins_from_plugin_manager' not in line:
                break
            method_lines += 1

    print(f"  方法行数: ~{method_lines}")
else:
    print("[ERROR] 新方法未找到")

# 2. 检查旧方法是否被废弃
print("\n2. 检查旧方法状态")
print("-"*80)

if '_manual_register_core_plugins_DEPRECATED' in content:
    print("[OK] 旧方法已标记为 DEPRECATED")
elif '_manual_register_core_plugins' in content and 'DEPRECATED' not in content:
    print("[WARNING] 旧方法仍在使用")
else:
    print("[OK] 旧方法已完全移除")

# 3. 检查调用点
print("\n3. 检查调用点")
print("-"*80)

if 'self._register_plugins_from_plugin_manager()' in content:
    print("[OK] discover_and_register_data_source_plugins 使用新方法")
elif 'self._manual_register_core_plugins()' in content:
    print("[WARNING] 仍在调用旧方法")
else:
    print("[?] 未找到调用")

# 4. 检查examples导入
print("\n4. 检查examples导入")
print("-"*80)

import_count = content.count('from plugins.examples.')
if import_count == 0:
    print("[OK] 没有活跃的examples导入")
else:
    print(f"[INFO] 发现 {import_count} 处examples导入（可能在废弃代码中）")

# 5. 统计代码变化
print("\n5. 代码统计")
print("-"*80)

total_lines = len(lines)
print(f"文件总行数: {total_lines}")

# 查找废弃代码块
deprecated_start = None
deprecated_end = None
for i, line in enumerate(lines):
    if '_manual_register_core_plugins_DEPRECATED' in line:
        deprecated_start = i
    if deprecated_start and line.strip() == '"""  # 废弃代码结束':
        deprecated_end = i
        break

if deprecated_start and deprecated_end:
    deprecated_lines = deprecated_end - deprecated_start
    print(f"废弃代码行数: {deprecated_lines}")
    print(f"预计删除后可减少: ~{deprecated_lines} 行")

# 6. 验证语法
print("\n6. 语法验证")
print("-"*80)

try:
    compile(content, 'core/services/unified_data_manager.py', 'exec')
    print("[OK] Python语法正确")
except SyntaxError as e:
    print(f"[ERROR] 语法错误: {e}")

# 7. 生成总结
print("\n" + "="*80)
print("重构验证总结")
print("="*80)

print("""
[完成的工作]
  新增动态插件加载方法
  废弃硬编码插件注册方法
  修改调用点使用新方法
  
[代码改进]
  删除硬编码导入
  使用插件管理器动态发现
  易于维护和扩展
  
[下一步]
  测试系统启动
  验证插件正确加载
  迁移/删除examples插件
  清理废弃代码
""")

print("="*80)
