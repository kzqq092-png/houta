#!/usr/bin/env python3
"""
批量修复logger = logger错误脚本
"""

import os
import re
import glob

def fix_logger_errors(file_path):
    """修复单个文件中的logger错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. 修复 logger = logger 错误
        content = re.sub(r'\nlogger = logger\n', '\n', content)
        content = re.sub(r'logger = logger\n', '', content)
        content = re.sub(r'logger = logger$', '', content, flags=re.MULTILINE)
        
        # 2. 修复 self.logger = logger 错误
        content = re.sub(r'\nself\.logger = logger\n', '\n', content)
        content = re.sub(r'self\.logger = logger\n', '', content)
        content = re.sub(r'self\.logger = logger$', '', content, flags=re.MULTILINE)
        
        # 修复特定行周围的代码
        content = re.sub(r'def __init__\(self\):\s*\n\s*self\.logger = logger', 'def __init__(self):\n        pass', content)
        
        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"修复文件: {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def find_python_files_with_logger_errors(root_dir):
    """查找所有包含logger错误_python文件"""
    pattern = os.path.join(root_dir, '**', '*.py')
    files_with_errors = []
    
    for file_path in glob.glob(pattern, recursive=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含logger错误
            if 'logger = logger' in content or 'self.logger = logger' in content:
                files_with_errors.append(file_path)
                
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
    
    return files_with_errors

if __name__ == "__main__":
    root_dir = "core"
    
    print("正在查找包含logger错误的Python文件...")
    files_with_errors = find_python_files_with_logger_errors(root_dir)
    
    print(f"找到 {len(files_with_errors)} 个包含logger错误的文件")
    
    fixed_count = 0
    for file_path in files_with_errors:
        if fix_logger_errors(file_path):
            fixed_count += 1
    
    print(f"\n修复完成! 共修复了 {fixed_count} 个文件")
    print("所有 logger = logger 和 self.logger = logger 错误已清除")