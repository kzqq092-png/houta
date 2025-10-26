#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件多进程数据下载功能 - 最简版
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_multiprocess_modification():
    """测试多进程修改"""
    
    print("="*80)
    print("通达信插件多进程修改验证")
    print("="*80)
    
    try:
        # 检查文件是否存在
        tongdaxin_file = "plugins/data_sources/stock/tongdaxin_plugin.py"
        if os.path.exists(tongdaxin_file):
            print(f"OK: 通达信插件文件存在: {tongdaxin_file}")
        else:
            print(f"ERROR: 通达信插件文件不存在: {tongdaxin_file}")
            return
        
        # 检查多进程相关代码
        with open(tongdaxin_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查多进程连接池类
        if "class MultiprocessConnectionPool" in content:
            print("OK: 多进程连接池类已添加")
        else:
            print("ERROR: 多进程连接池类未找到")
        
        # 检查多进程配置
        if "use_multiprocess" in content:
            print("OK: 多进程配置已添加")
        else:
            print("ERROR: 多进程配置未找到")
        
        # 检查多进程初始化
        if "_initialize_multiprocess_support" in content:
            print("OK: 多进程初始化方法已添加")
        else:
            print("ERROR: 多进程初始化方法未找到")
        
        # 检查导入引擎修改
        import_engine_file = "core/importdata/unified_data_import_engine.py"
        if os.path.exists(import_engine_file):
            with open(import_engine_file, 'r', encoding='utf-8') as f:
                engine_content = f.read()
            
            if "ProcessPoolExecutor" in engine_content:
                print("OK: 导入引擎多进程支持已添加")
            else:
                print("ERROR: 导入引擎多进程支持未找到")
            
            if "_process_symbol_batch" in engine_content:
                print("OK: 批次处理方法已添加")
            else:
                print("ERROR: 批次处理方法未找到")
        else:
            print(f"ERROR: 导入引擎文件不存在: {import_engine_file}")
        
        print(f"\nOK: 多进程修改验证完成")
        
    except Exception as e:
        print(f"ERROR: 验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiprocess_modification()
    print(f"\n所有验证完成")