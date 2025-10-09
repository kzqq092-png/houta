#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证15个核心服务正常工作
"""

import sys
import os
import time
from datetime import datetime
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    print("验证15个核心服务...")
    print("=" * 80)
    
    try:
        # 导入核心模块
        from core.containers.unified_service_container import UnifiedServiceContainer
        from core.services.service_bootstrap import ServiceBootstrap, bootstrap_services
        
        print("成功导入核心模块")
        
        # 启动服务
        print("启动服务引导程序...")
        start_time = time.time()
        success = bootstrap_services()
        bootstrap_time = time.time() - start_time
        
        if success:
            print(f"服务引导成功，耗时: {bootstrap_time:.3f}s")
        else:
            print("服务引导失败")
            return 1
            
        # 获取服务容器
        from core.containers.unified_service_container import get_service_container
        container = get_service_container()
        
        print("验证15个核心服务...")
        
        # 定义15个核心服务
        core_services = [
            "ConfigService",
            "UnifiedDataManager", 
            "ThemeService",
            "ChartService",
            "AnalysisService",
            "IndustryService",
            "AIPredicationService",
            "AssetService",
            "SectorFundFlowService",
            "KLineChartRenderingService",
            "StrategyExecutionService",
            "PluginManager",
            "UniPluginDataManager",
            "StockService",
            "TradingService"
        ]
        
        validated_services = []
        failed_services = []
        
        for service_name in core_services:
            try:
                service = container.resolve_by_name(service_name)
                if service is not None:
                    print(f"✅ {service_name}: 正常")
                    validated_services.append(service_name)
                else:
                    print(f"❌ {service_name}: 未注册")
                    failed_services.append(service_name)
            except Exception as e:
                print(f"❌ {service_name}: 异常 - {e}")
                failed_services.append(service_name)
        
        # 统计结果
        total_services = len(core_services)
        success_count = len(validated_services)
        failure_count = len(failed_services)
        success_rate = (success_count / total_services) * 100
        
        print("\n" + "=" * 80)
        print("验证结果统计:")
        print("=" * 80)
        print(f"总服务数: {total_services}")
        print(f"验证成功: {success_count}")
        print(f"验证失败: {failure_count}")
        print(f"成功率: {success_rate:.1f}%")
        
        if failed_services:
            print(f"\n失败的服务: {', '.join(failed_services)}")
        
        # 生成验证报告
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'bootstrap_time': bootstrap_time,
            'total_services': total_services,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_rate,
            'validated_services': validated_services,
            'failed_services': failed_services,
            'overall_success': success_rate >= 80.0
        }
        
        print(f"\n总体验证: {'✅ 成功' if validation_report['overall_success'] else '❌ 失败'}")
        
        return 0 if validation_report['overall_success'] else 1
        
    except Exception as e:
        print(f"服务验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())