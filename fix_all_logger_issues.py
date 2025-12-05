#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面修复所有logger问题
"""

import os
import re
import glob
from pathlib import Path

def find_python_files_with_self_logger(directory):
    """查找使用self.logger的Python文件"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # 跳过备份和临时文件目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', '.git', '.backup']]
        
        for file in files:
            if file.endswith('.py') and not file.endswith('.bak'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'self.logger.' in content:
                            python_files.append(file_path)
                except UnicodeDecodeError:
                    # 尝试其他编码
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                            if 'self.logger.' in content:
                                python_files.append(file_path)
                    except:
                        pass
    return python_files

def fix_file_logger_issues(file_path):
    """修复单个文件的logger问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 检查是否已经有正确的logger初始化
        has_property_logger = 'def logger(self)' in content or '@property' in content and 'def logger(self)' in content
        has_bind_logger = 'self.logger = logger.bind(' in content
        has_simple_logger = 'self.logger = logger' in content and 'self.logger = logger\n' not in content
        
        if has_property_logger or has_bind_logger:
            print(f"文件 {file_path} 已经有正确的logger初始化")
            return False
            
        # 查找类的__init__方法
        class_match = re.search(r'class\s+(\w+).*?:\s*(.*?)(?=\nclass|\n\S|\Z)', content, re.DOTALL)
        if not class_match:
            return False
            
        class_def = class_match.group(0)
        init_match = re.search(r'def __init__\(.*?\):(.*?)(?=\n    def|\n    @|\nclass|\Z)', class_def, re.DOTALL)
        
        if not init_match:
            # 没有__init__方法，添加一个
            init_body = init_match.group(1).strip() if init_match else ""
            if init_body and not init_body.endswith('pass'):
                new_init = f"def __init__(self):\n        {init_body}\n        self.logger = logger.bind(module=self.__class__.__name__)\n    "
            else:
                new_init = "def __init__(self):\n        self.logger = logger.bind(module=self.__class__.__name__)\n    "
            
            # 在类定义后插入新的__init__方法
            class_header = class_match.group(0).split(':')[0] + ':'
            content = content.replace(class_header, class_header + '\n' + new_init, 1)
        else:
            # 在现有的__init__方法中添加logger初始化
            init_body = init_match.group(1).strip()
            if 'self.logger' not in init_body:
                # 找到第一个缩进级别，在那添加logger初始化
                lines = init_body.split('\n')
                if lines:
                    first_line = lines[0]
                    indent_level = len(first_line) - len(first_line.lstrip())
                    indent = ' ' * (indent_level + 4)
                    
                    new_line = f"{indent}self.logger = logger.bind(module=self.__class__.__name__)"
                    lines.insert(1, new_line)
                    
                    new_init_body = '\n'.join(lines)
                    content = content.replace(init_match.group(0), f"def __init__{init_match.group(0)[9:]}{new_init_body}")
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"已修复文件: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def main():
    core_dir = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core"
    
    # 查找所有使用self.logger的文件
    files_with_self_logger = find_python_files_with_self_logger(core_dir)
    
    print(f"找到 {len(files_with_self_logger)} 个使用 self.logger 的文件:")
    for file_path in files_with_self_logger:
        print(f"  - {file_path}")
    
    # 修复每个文件
    fixed_count = 0
    for file_path in files_with_self_logger:
        if fix_file_logger_issues(file_path):
            fixed_count += 1
    
    print(f"\n修复完成! 总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()