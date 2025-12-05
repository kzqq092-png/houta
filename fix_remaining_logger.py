#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确修复剩余的logger问题
"""

import os
import re

def fix_analysis_manager():
    """修复AnalysisManager的logger问题"""
    file_path = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\business\\analysis_manager.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在__init__方法后添加logger属性
    init_pattern = r'(def __init__\(self, data_access: DataAccess\):.*?\n    )'
    
    def replace_init(match):
        init_content = match.group(1)
        if 'self.logger' not in init_content:
            return init_content + "        self.logger = logger.bind(module=self.__class__.__name__)\n"
        return init_content
    
    content = re.sub(init_pattern, replace_init, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")

def fix_unified_data_accessor():
    """修复UnifiedDataAccessor的logger问题"""
    file_path = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\services\\unified_data_accessor.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复__init__方法的语法错误
    content = content.replace('def __init__t__', 'def __init__')
    content = content.replace('        self.', '        self.logger = logger.bind(module=self.__class__.__name__)\n        self.')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")

def check_and_fix_property_logger(file_path, class_name):
    """检查并修复需要property装饰器的logger"""
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有正确的logger
    if 'self.logger = logger.bind(' in content:
        return False
    
    # 检查类定义
    class_pattern = rf'class {class_name}.*?:'
    if not re.search(class_pattern, content):
        return False
    
    # 如果__init__方法存在且为空，则添加property
    init_pattern = r'def __init__\(self[^)]*\):\s*\n\s*pass'
    if re.search(init_pattern, content):
        # 在pass前添加logger属性
        content = re.sub(
            r'(def __init__\(self[^)]*\):\s*\n)(\s*pass)',
            r'\1\2\n\1        self.logger = logger.bind(module=self.__class__.__name__)',
            content
        )
    else:
        # 如果没有__init__，添加一个
        class_match = re.search(class_pattern + r'.*?(?=\nclass|\n\S|\Z)', content, re.DOTALL)
        if class_match:
            init_method = "\n    def __init__(self):\n        self.logger = logger.bind(module=self.__class__.__name__)\n"
            class_def = class_match.group(0)
            # 在类定义后插入__init__方法
            class_header = class_match.group(0).split(':')[0] + ':'
            content = content.replace(class_header, class_header + init_method, 1)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")
    return True

def main():
    """主修复函数"""
    # 修复已知有问题的文件
    fix_analysis_manager()
    fix_unified_data_accessor()
    
    # 修复其他使用@property的类
    property_files = [
        ("d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\trading\\execution_benchmarks.py", "ExecutionBenchmarks"),
        ("d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\strategy_extensions.py", "StrategyPluginAdapter")
    ]
    
    for file_path, class_name in property_files:
        check_and_fix_property_logger(file_path, class_name)
    
    print("\n所有剩余logger问题已修复完成！")

if __name__ == "__main__":
    main()