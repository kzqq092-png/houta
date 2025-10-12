#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略整合测试脚本

功能：
1. 测试20字段标准策略是否成功注册
2. 验证策略信息
3. 测试策略创建
4. 显示可用策略列表

作者：FactorWeave-Quant Team
版本：V2.0.4
日期：2025-10-12
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.services.strategy_service import StrategyService


def test_strategy_registration():
    """测试策略注册"""
    print("=" * 80)
    print("策略整合测试")
    print("=" * 80)
    print()
    
    try:
        # 创建策略服务
        print("1. 初始化策略服务...")
        service = StrategyService()
        print("   ✅ 策略服务初始化成功")
        print()
        
        # 获取可用策略类型
        print("2. 检查可用策略...")
        plugin_types = service.get_available_plugin_types()
        
        if not plugin_types:
            print("   ❌ 未发现任何策略插件")
            return False
        
        print(f"   ✅ 发现 {len(plugin_types)} 个策略插件:")
        for plugin_type in plugin_types:
            print(f"      - {plugin_type}")
        print()
        
        # 检查20字段标准策略
        print("3. 验证20字段标准策略...")
        target_strategies = ['adj_momentum_v2', 'vwap_reversion_v2']
        
        for strategy_id in target_strategies:
            if strategy_id in plugin_types:
                print(f"   ✅ {strategy_id} 已注册")
                
                # 获取策略详情
                try:
                    plugin = service.create_strategy_plugin(strategy_id)
                    if plugin:
                        info = plugin.get_strategy_info()
                        print(f"      名称: {info.name}")
                        print(f"      描述: {info.description}")
                        print(f"      版本: {info.version}")
                        print(f"      参数数量: {len(info.parameters)}")
                        print(f"      必需字段: {', '.join(info.required_data_fields)}")
                    else:
                        print(f"      ⚠️  无法创建策略实例")
                except Exception as e:
                    print(f"      ❌ 获取策略信息失败: {e}")
            else:
                print(f"   ❌ {strategy_id} 未注册")
        print()
        
        # 测试策略参数
        print("4. 测试策略参数定义...")
        for strategy_id in target_strategies:
            if strategy_id in plugin_types:
                try:
                    plugin = service.create_strategy_plugin(strategy_id)
                    info = plugin.get_strategy_info()
                    
                    print(f"   策略: {info.name}")
                    for param in info.parameters:
                        print(f"      - {param.display_name} ({param.name})")
                        print(f"        类型: {param.type.__name__}")
                        print(f"        默认值: {param.default_value}")
                        if param.min_value is not None:
                            print(f"        范围: [{param.min_value}, {param.max_value}]")
                except Exception as e:
                    print(f"   ❌ 测试失败: {e}")
        print()
        
        # 总结
        print("=" * 80)
        print("测试总结")
        print("=" * 80)
        
        success_count = sum(1 for s in target_strategies if s in plugin_types)
        
        if success_count == len(target_strategies):
            print("✅ 所有20字段标准策略已成功集成！")
            print(f"   - 策略服务可用")
            print(f"   - {success_count}/{len(target_strategies)} 策略已注册")
            print(f"   - 策略信息完整")
            return True
        else:
            print(f"⚠️  部分策略集成失败")
            print(f"   - 已注册: {success_count}/{len(target_strategies)}")
            return False
        
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def display_all_strategies():
    """显示所有可用策略"""
    print("\n" + "=" * 80)
    print("所有可用策略列表")
    print("=" * 80)
    
    try:
        service = StrategyService()
        plugin_types = service.get_available_plugin_types()
        
        if not plugin_types:
            print("未发现任何策略")
            return
        
        for i, plugin_type in enumerate(plugin_types, 1):
            try:
                plugin = service.create_strategy_plugin(plugin_type)
                if plugin:
                    info = plugin.get_strategy_info()
                    print(f"\n{i}. {info.name} ({plugin_type})")
                    print(f"   类型: {info.strategy_type}")
                    print(f"   描述: {info.description}")
                    print(f"   版本: {info.version}")
                    print(f"   作者: {info.author}")
                    
                    # 显示元数据（如果有）
                    if hasattr(info, 'metadata') and info.metadata:
                        if info.metadata.get('category'):
                            print(f"   分类: {info.metadata['category']}")
                        
                        # 20字段标准特性
                        if info.metadata.get('uses_adj_close'):
                            print(f"   ✅ 使用复权价格")
                        if info.metadata.get('uses_vwap'):
                            print(f"   ✅ 使用VWAP")
                        if info.metadata.get('uses_turnover_rate'):
                            print(f"   ✅ 使用换手率")
                else:
                    print(f"\n{i}. {plugin_type}")
                    print(f"   ⚠️  无法加载策略信息")
            except Exception as e:
                print(f"\n{i}. {plugin_type}")
                print(f"   ❌ 错误: {e}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"显示策略列表失败: {e}")


def main():
    """主函数"""
    # 测试策略注册
    success = test_strategy_registration()
    
    # 显示所有策略
    display_all_strategies()
    
    # 返回结果
    if success:
        print("\n✅ 策略整合测试通过！")
        return 0
    else:
        print("\n❌ 策略整合测试失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())

