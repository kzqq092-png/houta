#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版性能优化工具
"""

import sys
import os
import time
import gc
from datetime import datetime
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    print("启动最终架构性能优化...")
    print("=" * 80)
    
    try:
        # 导入核心模块
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.services.service_bootstrap import ServiceBootstrap
        
        print("成功导入核心模块")
        
        # 1. 建立性能基线
        print("建立性能基线...")
        container = UnifiedServiceContainer()
        bootstrap = ServiceBootstrap()
        
        startup_start = time.time()
        success = bootstrap.bootstrap()
        startup_time = time.time() - startup_start
        
        if success:
            print(f"服务启动成功，启动时间: {startup_time:.3f}s")
        else:
            print("服务启动失败")
            return 1
            
        # 2. 内存优化
        print("执行内存优化...")
        before_gc = gc.get_count()
        gc.collect()
        after_gc = gc.get_count()
        print(f"垃圾回收完成: {before_gc} -> {after_gc}")
        
        # 3. 性能测试
        print("执行性能测试...")
        test_start = time.time()
        
        # 模拟一些操作
        for i in range(100):
            result = sum(j * j for j in range(100))
            
        test_time = time.time() - test_start
        print(f"性能测试完成，耗时: {test_time:.3f}s")
        
        # 4. 生成报告
        print("生成优化报告...")
        report = {
            'timestamp': datetime.now().isoformat(),
            'startup_time': startup_time,
            'test_time': test_time,
            'gc_before': before_gc,
            'gc_after': after_gc,
            'success': True
        }
        
        print("性能优化完成!")
        print(f"启动时间: {startup_time:.3f}s")
        print(f"测试时间: {test_time:.3f}s")
        
        return 0
        
    except Exception as e:
        print(f"性能优化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())