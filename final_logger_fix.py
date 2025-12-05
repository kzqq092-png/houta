#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终logger修复脚本
解决语法错误和重复代码
"""

import re

def fix_analysis_manager():
    """修复AnalysisManager的语法错误"""
    file_path = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\business\\analysis_manager.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复logger导入位置
    content = content.replace('from loguru import logger\n"""\n分析管理业务逻辑', '"""\n分析管理业务逻辑')
    content = 'from loguru import logger\n\n' + content
    
    # 修复TechnicalSignal类的错误代码
    content = re.sub(r'def __init__\(self\):\s*\n\s*self\.logger = logger\.bind\(module=self\.__class__.__name__\)\s*\n\s*""".*?"""', 
                     '', content, flags=re.DOTALL)
    
    # 修复AnalysisManager类的__init__方法
    content = re.sub(r'def __init__\(self, data_access: DataAccess\):\s*\n\s*self\.logger = logger\.bind\(module=self\.__class__.__name__\)\s*\n\s*self\.data_access = data_access\s*\n\s*self\._analysis_cache = \{\}  # 分析结果缓存',
                     'def __init__(self, data_access: DataAccess):\n        self.data_access = data_access\n        self._analysis_cache = {}  # 分析结果缓存\n        self.logger = logger.bind(module=self.__class__.__name__)', 
                     content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")

def fix_execution_benchmarks():
    """修复ExecutionBenchmarks的重复__init__方法"""
    file_path = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\trading\\execution_benchmarks.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除重复的__init__方法
    content = re.sub(r'def __init__\(self\):\s*\n\s*pass\s*\n', '', content)
    content = re.sub(r'def __init__\(self\):\s*\n\s*self\.logger = logger\.bind\(module=self\.__class__.__name__\)\s*',
                     'def __init__(self):', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修复: {file_path}")

def fix_asset_service():
    """检查并修复AssetService的logger问题"""
    file_path = "d:\\DevelopTool\\FreeCode\\HIkyuu-UI\\hikyuu-ui\\core\\services\\asset_service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有logger初始化
    if 'self.logger =' not in content:
        # 在__init__方法最后添加logger初始化
        init_pattern = r'(def __init__\(.*?\):.*?self\.logger\.info\("AssetService初始化完成"\))'
        
        def add_logger_init(match):
            return match.group(1) + '\n        self.logger = logger.bind(module=self.__class__.__name__)'
        
        content = re.sub(init_pattern, add_logger_init, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已检查: {file_path}")

def main():
    """主修复函数"""
    fix_analysis_manager()
    fix_execution_benchmarks()
    fix_asset_service()
    
    print("\n最终logger修复完成！")

if __name__ == "__main__":
    main()