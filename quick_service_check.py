#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速服务注册状态检查
"""

import sys
import traceback
from datetime import datetime

def main():
    print("快速服务注册状态检查")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    try:
        # 导入核心模块
        from core.services.service_bootstrap import ServiceBootstrap
        from core.containers.service_container import get_service_container
        print("✓ 核心模块导入成功")
        
        # 获取服务容器
        container = get_service_container()
        print("✓ 服务容器获取成功")
        
        # 执行服务引导
        print("\n开始服务引导初始化...")
        bootstrap = ServiceBootstrap(container)
        bootstrap_success = bootstrap.bootstrap()
        
        if bootstrap_success:
            print("✓ 服务引导初始化成功")
            
            # 检查特定服务注册状态
            print("\n检查服务注册状态:")
            
            # 检查DatabaseService
            try:
                db_info = container.registry.get_service_info_by_name('DatabaseService')
                if db_info:
                    print("✓ DatabaseService: 注册成功")
                else:
                    print("✗ DatabaseService: 未注册")
            except Exception as e:
                print(f"✗ DatabaseService: 检查失败 - {e}")
            
            # 检查风险控制服务
            try:
                risk_info = container.registry.get_service_info_by_name('AISelectionRiskControlService')
                if risk_info:
                    print("✓ AISelectionRiskControlService: 注册成功")
                else:
                    print("✗ AISelectionRiskControlService: 未注册")
            except Exception as e:
                print(f"✗ AISelectionRiskControlService: 检查失败 - {e}")
            
            print("\n✅ 所有检查完成")
            return True
        else:
            print("✗ 服务引导初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)