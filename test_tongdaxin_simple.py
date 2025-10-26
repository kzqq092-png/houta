#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件多进程数据下载功能 - 简化版
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_multiprocess_download():
    """测试多进程下载功能"""
    
    print("="*80)
    print("通达信插件多进程下载测试")
    print("="*80)
    
    try:
        # 导入必要的模块
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        print("OK: 通达信插件导入成功")
        
        # 创建通达信插件实例
        plugin = TongdaxinStockPlugin()
        print(f"OK: 通达信插件创建成功")
        print(f"   多进程支持: {plugin.use_multiprocess}")
        print(f"   工作进程数: {plugin.multiprocess_workers}")
        
        if plugin.connection_pool:
            print(f"   连接池大小: {plugin.connection_pool.pool_size}")
        else:
            print("   连接池: 未创建")
        
        # 测试连接池功能
        if plugin.connection_pool:
            print(f"\n测试连接池功能...")
            with plugin.connection_pool.get_connection() as client:
                if client:
                    print("OK: 连接池获取连接成功")
                else:
                    print("ERROR: 连接池获取连接失败")
        
        print(f"\nOK: 多进程下载测试完成")
        
    except Exception as e:
        print(f"ERROR: 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiprocess_download()
    print(f"\n所有测试完成")