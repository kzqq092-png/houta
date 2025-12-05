#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语法错误修复脚本
系统性修复core目录下Python文件的语法错误
"""

import os
import ast
import re
from pathlib import Path

def fix_file_syntax(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # 修复1: 修复缺少缩进的类定义
        lines = content.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查类定义后是否有缺少缩进的问题
            if re.match(r'^\s*class\s+\w+.*:', line) and i + 1 < len(lines):
                # 如果下一行不是缩进的代码块，添加pass
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('#'):
                    # 检查是否需要添加pass
                    if not next_line.startswith(('def ', 'class ', 'pass', '"""', "'''", 'async def')):
                        fixed_lines.append(line)
                        if not any(next_line.startswith(x) for x in ['def ', 'class ', 'pass', '"""', "'''", 'async def']):
                            # 插入pass语句
                            if line.strip().endswith(':'):
                                indent = len(line) - len(line.lstrip())
                                fixed_lines.append(' ' * (indent + 4) + 'pass')
                        i += 1
                        continue
            
            # 修复2: 修复无意义的代码块
            # 移除孤立的方法定义（如只有pass的方法定义）
            if re.match(r'^\s+def\s+\w+.*:', line):
                # 查找方法定义后是否只有pass
                method_indent = len(line) - len(line.lstrip())
                method_found = False
                j = i + 1
                method_body = []
                
                while j < len(lines):
                    next_line = lines[j]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    if next_indent <= method_indent:
                        break
                    
                    if not next_line.strip():
                        j += 1
                        continue
                        
                    if next_line.strip() == 'pass':
                        # 如果方法体只有pass，检查是否是预期的
                        if not method_body:  # 空方法体
                            # 检查是否有docstring
                            if j + 1 < len(lines):
                                next_next_line = lines[j + 1].strip()
                                if not (next_next_line.startswith('"""') or next_next_line.startswith("'''")):
                                    # 可能是空方法，保留pass
                                    method_found = True
                                    method_body.append(next_line)
                            else:
                                method_found = True
                                method_body.append(next_line)
                        break
                    
                    method_body.append(next_line)
                    method_found = True
                    j += 1
                
                fixed_lines.append(line)
                if method_body:
                    for body_line in method_body:
                        fixed_lines.append(body_line)
                    i = j
                else:
                    # 如果没有找到方法体，检查是否需要添加pass
                    if j >= len(lines) or (j < len(lines) and len(lines[j]) - len(lines[j].lstrip()) <= method_indent):
                        if j < len(lines) and lines[j].strip() != 'pass':
                            # 添加pass
                            fixed_lines.append(' ' * (method_indent + 4) + 'pass')
                    i = j if j < len(lines) else i + 1
                continue
            
            # 修复3: 修复错误的导入和变量声明
            if 'from loguru import logger' in line:
                # 检查是否有logger相关的语法错误
                if 'self.logger = logger' in content and 'self.logger = logger.bind' not in content:
                    # 修复logger初始化
                    content = re.sub(r'self\.logger = logger\s*$', 
                                   r'self.logger = logger.bind(module=self.__class__.__name__)', 
                                   content, flags=re.MULTILINE)
                    changes_made.append("修复logger初始化语法")
            
            fixed_lines.append(line)
            i += 1
        
        if fixed_lines != lines:
            content = '\n'.join(fixed_lines)
            changes_made.append("修复缩进问题")
        
        # 修复4: 修复类定义后的错误语法
        content = re.sub(r'(def __init__\(self\):)@property', r'\1\n    @property', content)
        changes_made.append("修复@property装饰器位置")
        
        # 修复5: 修复不完整的类定义
        content = re.sub(r'class INone\s*"""缓存管理器接口"""', r'class INone:', content)
        changes_made.append("修复不完整的类定义")
        
        # 修复6: 修复缩进错误的类成员
        content = re.sub(r'^(\s+)@abstractmethod\s+async def', r'\1    @abstractmethod\n\1    async def', content, flags=re.MULTILINE)
        changes_made.append("修复@abstractmethod装饰器缩进")
        
        # 如果有修改，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes_made
        
        return False, []
        
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False, [f"错误: {e}"]

def validate_syntax(file_path):
    """验证文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    except Exception as e:
        return False, f"其他错误: {e}"

def main():
    """主函数"""
    print("开始修复语法错误...")
    
    # 需要修复的文件列表
    files_to_fix = [
        "core/integration/data_router.py",
        "core/interfaces/cache.py",
        "core/interfaces/circuit_breaker.py",
        "core/migration/dependency_analyzer.py",
        "core/migration/migration_monitor.py",
        "core/migration/pre_migration_health_check.py",
        "core/services/legacy_datasource_adapter.py",
        "core/services/unified_data_accessor.py",
        "core/ui_integration/ui_business_logic_adapter.py",
        "core/akshare_data_source.py",
        "core/data_source_extensions.py",
        "core/indicator_extensions.py",
        "core/performance_optimizer.py",
        "core/risk_exporter.py",
        "core/metrics/resource_service.py"
    ]
    
    fixed_count = 0
    total_files = len(files_to_fix)
    
    for file_path in files_to_fix:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            print(f"修复文件: {file_path}")
            success, changes = fix_file_syntax(full_path)
            if success:
                print(f"  ✓ 修复成功: {', '.join(changes)}")
                fixed_count += 1
            else:
                print(f"  - 无需修复")
        else:
            print(f"  × 文件不存在: {file_path}")
    
    print(f"\n修复完成! 成功修复 {fixed_count}/{total_files} 个文件")
    
    # 验证修复结果
    print("\n验证修复结果...")
    still_errors = 0
    for file_path in files_to_fix:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            valid, error = validate_syntax(full_path)
            if not valid:
                print(f"  × 仍有语法错误: {file_path} - {error}")
                still_errors += 1
    
    if still_errors == 0:
        print("🎉 所有语法错误已修复!")
    else:
        print(f"⚠️  仍有 {still_errors} 个文件存在语法错误")

if __name__ == "__main__":
    main()