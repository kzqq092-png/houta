#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件多进程数据下载功能
"""

import sys
import os
import time
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

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
        from core.importdata.unified_data_import_engine import UnifiedDataImportEngine, ImportTaskConfig
        from core.plugin_types import UnifiedTaskStatus
        
        print("✅ 模块导入成功")
        
        # 创建通达信插件实例
        plugin = TongdaxinStockPlugin()
        print(f"✅ 通达信插件创建成功")
        print(f"   多进程支持: {plugin.use_multiprocess}")
        print(f"   工作进程数: {plugin.multiprocess_workers}")
        print(f"   连接池大小: {plugin.connection_pool.pool_size if plugin.connection_pool else 'N/A'}")
        
        # 测试股票列表
        test_symbols = [
            '000001', '000002', '000858', '000876', '000895',
            '600000', '600036', '600519', '600887', '600900'
        ]
        
        print(f"\n📊 测试股票列表: {test_symbols}")
        
        # 创建导入任务配置
        task_config = ImportTaskConfig(
            task_id="test_multiprocess",
            symbols=test_symbols,
            data_source="tongdaxin",
            frequency="daily",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        
        # 创建导入引擎
        import_engine = UnifiedDataImportEngine()
        
        # 测试多进程导入
        print(f"\n🚀 开始多进程导入测试...")
        start_time = time.time()
        
        result = import_engine._import_kline_data(task_config, import_engine._create_import_result(task_config))
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n📈 导入结果:")
        print(f"   总记录数: {result.total_records}")
        print(f"   成功处理: {result.processed_records}")
        print(f"   失败记录: {result.failed_records}")
        print(f"   跳过记录: {result.skipped_records}")
        print(f"   耗时: {duration:.2f}秒")
        print(f"   平均每只股票: {duration/len(test_symbols):.2f}秒")
        
        if result.warnings:
            print(f"\n⚠️ 警告信息:")
            for warning in result.warnings[:5]:  # 只显示前5个警告
                print(f"   - {warning}")
        
        # 性能对比测试
        print(f"\n🔍 性能对比测试...")
        
        # 单进程测试
        print(f"   单进程模式测试...")
        plugin.use_multiprocess = False
        start_time = time.time()
        
        result_single = import_engine._import_kline_data(task_config, import_engine._create_import_result(task_config))
        
        end_time = time.time()
        duration_single = end_time - start_time
        
        print(f"   单进程耗时: {duration_single:.2f}秒")
        print(f"   多进程耗时: {duration:.2f}秒")
        
        if duration > 0 and duration_single > 0:
            speedup = duration_single / duration
            print(f"   性能提升: {speedup:.2f}x")
        
        print(f"\n✅ 多进程下载测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_connection_pool():
    """测试连接池功能"""
    
    print("\n" + "="*80)
    print("连接池功能测试")
    print("="*80)
    
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin, MultiprocessConnectionPool
        
        # 创建连接池
        pool = MultiprocessConnectionPool(
            host='119.147.212.81',
            port=7709,
            pool_size=4
        )
        
        print(f"✅ 连接池创建成功，大小: {pool.pool_size}")
        print(f"   可用连接数: {len(pool.connections)}")
        
        # 测试连接获取和释放
        print(f"\n🔗 测试连接获取和释放...")
        
        for i in range(6):  # 测试超过池大小的连接数
            with pool.get_connection() as client:
                if client:
                    print(f"   连接 {i+1}: 获取成功")
                else:
                    print(f"   连接 {i+1}: 获取失败")
        
        print(f"   最终可用连接数: {len(pool.connections)}")
        
        # 清理
        pool.close_all()
        print(f"✅ 连接池测试完成")
        
    except Exception as e:
        print(f"❌ 连接池测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 设置多进程启动方法
    mp.set_start_method('spawn', force=True)
    
    # 运行测试
    test_multiprocess_download()
    test_connection_pool()
    
    print(f"\n🎉 所有测试完成")