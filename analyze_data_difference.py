#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析通达信插件数据差异原因
检查过滤逻辑是否过于严格
"""

import sys
import os
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_filtering_logic():
    """分析过滤逻辑是否过于严格"""
    
    print("="*80)
    print("TONGDAXIN PLUGIN DATA DIFFERENCE ANALYSIS")
    print("="*80)
    
    print("\n当前A股过滤规则:")
    print("SH (上海): 600xxx, 601xxx, 603xxx, 605xxx, 688xxx")
    print("SZ (深圳): 000xxx, 002xxx, 003xxx, 300xxx")
    
    print("\n可能遗漏的A股代码段:")
    print("1. 深证可能还有其他A股代码:")
    print("   - 001xxx (深证主板)")
    print("   - 004xxx (深证主板)")
    print("   - 其他可能的代码段")
    
    print("\n2. 官方统计可能包含:")
    print("   - 北交所A股 (8xxxxx)")
    print("   - 其他交易所A股")
    print("   - 特殊A股代码")
    
    print("\n3. 通达信API可能的问题:")
    print("   - 数据不完整")
    print("   - 某些股票未包含")
    print("   - API限制或超时")
    
    print("\n建议的修复方案:")
    print("1. 扩展A股过滤规则")
    print("2. 添加更详细的日志记录")
    print("3. 检查被过滤掉的代码段")
    print("4. 对比官方统计的具体分类")

def create_enhanced_filter():
    """创建增强的过滤逻辑"""
    
    print("\n" + "="*80)
    print("ENHANCED A-SHARE FILTERING LOGIC")
    print("="*80)
    
    # 扩展的A股代码规则
    sh_a_stock_prefixes = {
        '600': '主板',
        '601': '主板', 
        '603': '主板',
        '605': '主板',
        '688': '科创板',
        # 可能遗漏的
        '689': '科创板',  # 科创板扩展
    }
    
    sz_a_stock_prefixes = {
        '000': '主板',
        '001': '主板',  # 深证主板扩展
        '002': '中小板',
        '003': '主板',
        '300': '创业板',
        # 可能遗漏的
        '004': '主板',  # 深证主板扩展
    }
    
    print("\n扩展的A股代码规则:")
    print("SH (上海):")
    for prefix, desc in sh_a_stock_prefixes.items():
        print(f"   {prefix}xxx - {desc}")
    
    print("\nSZ (深圳):")
    for prefix, desc in sz_a_stock_prefixes.items():
        print(f"   {prefix}xxx - {desc}")
    
    return sh_a_stock_prefixes, sz_a_stock_prefixes

if __name__ == '__main__':
    analyze_filtering_logic()
    create_enhanced_filter()