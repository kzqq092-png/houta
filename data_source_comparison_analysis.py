#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源插件对比分析 - 为什么能获取上万条数据

发现：用户可能使用的是东方财富插件，而不是通达信插件！
"""

def analyze_data_source_differences():
    """分析不同数据源插件的差异"""
    
    print("="*80)
    print("数据源插件对比分析 - 为什么能获取上万条数据")
    print("="*80)
    
    print("\n【关键发现】用户可能使用的是东方财富插件，而不是通达信插件！")
    
    print("\n" + "-"*80)
    print("1. 通达信插件 (TongdaxinStockPlugin)")
    print("-"*80)
    
    print("文件: plugins/data_sources/stock/tongdaxin_plugin.py")
    print("方法: get_stock_list() [第1158-1219行]")
    print("\n限制分析:")
    print("  [OK] 第1178行: for start in range(0, min(sh_count, 10000), 1000)")
    print("  [OK] 第1191行: for start in range(0, min(sz_count, 10000), 1000)")
    print("  [OK] 硬性限制: 每个市场最多10,000条记录")
    print("  [OK] 当前状态: SH(2,272) + SZ(2,851) = 5,123 < 10,000 [安全]")
    
    print("\nAPI调用:")
    print("  - get_security_count(1) → 上证总数")
    print("  - get_security_list(1, start) → 上证数据")
    print("  - get_security_count(0) → 深证总数") 
    print("  - get_security_list(0, start) → 深证数据")
    
    print("\n" + "-"*80)
    print("2. 东方财富插件 (EastMoneyStockPlugin)")
    print("-"*80)
    
    print("文件: plugins/data_sources/stock/eastmoney_plugin.py")
    print("方法: get_stock_list() [第492行开始]")
    print("\n限制分析:")
    print("  [OK] 第502行: 'pz': '5000'  # 获取更多数据")
    print("  [OK] 无硬性限制: 一次获取5000条")
    print("  [OK] 可多次调用: 通过分页获取更多数据")
    print("  [OK] 包含更多板块: 科创板、创业板等")
    
    print("\nAPI参数分析:")
    print("  - pn: '1' (页码)")
    print("  - pz: '5000' (每页数量)")
    print("  - fs: 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23' (板块筛选)")
    
    print("\n板块说明:")
    print("  - m:0+t:6  → 沪市A股")
    print("  - m:0+t:80 → 沪市科创板")
    print("  - m:1+t:2  → 深市A股") 
    print("  - m:1+t:23 → 深市创业板")
    
    print("\n" + "-"*80)
    print("3. 数据量对比分析")
    print("-"*80)
    
    print("通达信插件预期数据量:")
    print("  - 上证A股: ~2,272")
    print("  - 深证A股: ~2,851")
    print("  - 总计: ~5,123")
    print("  - 限制: 10,000 (暂未触发)")
    
    print("\n东方财富插件预期数据量:")
    print("  - 沪市A股: ~2,272")
    print("  - 沪市科创板: ~500+")
    print("  - 深市A股: ~2,851")
    print("  - 深市创业板: ~1,000+")
    print("  - 总计: ~6,600+")
    print("  - 限制: 无硬性限制")
    
    print("\n" + "-"*80)
    print("4. 为什么用户看到上万条数据？")
    print("-"*80)
    
    reasons = [
        "【原因1】使用东方财富插件而非通达信插件",
        "【原因2】东方财富包含更多板块（科创板、创业板）",
        "【原因3】东方财富无10,000条限制",
        "【原因4】可能包含B股、ST股等特殊股票",
        "【原因5】可能包含基金、债券等其他证券",
        "【原因6】数据源更新频率不同",
        "【原因7】可能有其他数据源插件在工作"
    ]
    
    for reason in reasons:
        print(f"  {reason}")
    
    print("\n" + "-"*80)
    print("5. 验证方法")
    print("-"*80)
    
    print("要确认用户实际使用的数据源，可以：")
    print("\n1. 检查日志输出:")
    print("   - 查看 '获取股票列表成功，共 X 只股票' 的日志")
    print("   - 确认是哪个插件输出的")
    
    print("\n2. 检查插件管理器:")
    print("   - 查看当前激活的数据源插件")
    print("   - 确认默认使用的插件")
    
    print("\n3. 检查配置:")
    print("   - 查看数据源配置")
    print("   - 确认优先级设置")
    
    print("\n4. 代码验证:")
    print("   - 在get_stock_list方法中添加日志")
    print("   - 确认实际调用的插件")
    
    print("\n" + "-"*80)
    print("6. 解决方案建议")
    print("-"*80)
    
    print("如果用户确实在使用东方财富插件:")
    print("  [OK] 无需修复通达信插件的10,000限制")
    print("  [OK] 东方财富插件工作正常")
    print("  [OK] 数据量差异是正常的")
    
    print("\n如果用户想使用通达信插件:")
    print("  [OK] 需要修复10,000限制")
    print("  [OK] 需要确认数据源配置")
    print("  [OK] 可能需要调整插件优先级")
    
    print("\n" + "-"*80)
    print("7. 总结")
    print("-"*80)
    
    print("""
关键发现：
- 通达信插件有10,000条限制（当前未触发）
- 东方财富插件无此限制，且包含更多板块
- 用户看到的"上万条数据"很可能来自东方财富插件
- 这解释了为什么数据量超过官方统计的5,123条

建议：
1. 确认用户实际使用的数据源插件
2. 如果使用东方财富，则无需修复通达信限制
3. 如果使用通达信，则需要修复限制问题
4. 可以同时支持多个数据源，让用户选择
""")
    
    print("="*80)
    print("分析完成")
    print("="*80)


if __name__ == '__main__':
    analyze_data_source_differences()
