#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件实际返回的数据量和类型
分析为什么会有上万条数据
"""

import sys
import os
import pandas as pd
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tongdaxin_actual_data():
    """测试通达信插件实际返回的数据"""
    
    print("="*80)
    print("通达信插件实际数据测试")
    print("="*80)
    
    try:
        # 导入通达信插件
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        print("\n1. 初始化通达信插件...")
        plugin = TongdaxinStockPlugin()
        
        print("\n2. 调用get_stock_list()方法...")
        stock_df = plugin.get_stock_list()
        
        if stock_df.empty:
            print("❌ 获取数据失败或为空")
            return
        
        print(f"\n3. 数据统计:")
        print(f"   总记录数: {len(stock_df)}")
        print(f"   列名: {list(stock_df.columns)}")
        
        # 按市场分组统计
        if 'market' in stock_df.columns:
            market_counts = stock_df['market'].value_counts()
            print(f"\n4. 按市场分组:")
            for market, count in market_counts.items():
                print(f"   {market}: {count} 只")
        
        # 分析代码前缀分布
        if 'code' in stock_df.columns:
            print(f"\n5. 代码前缀分析:")
            prefixes = []
            for code in stock_df['code']:
                if len(str(code)) >= 3:
                    prefixes.append(str(code)[:3])
            
            prefix_counts = Counter(prefixes)
            print("   前10个最常见的前缀:")
            for prefix, count in prefix_counts.most_common(10):
                print(f"   {prefix}xxx: {count} 只")
        
        # 显示样本数据
        print(f"\n6. 样本数据 (前20条):")
        for i, row in stock_df.head(20).iterrows():
            print(f"   {row['code']} - {row['name']} - {row['market']}")
        
        # 检查是否有重复
        if 'code' in stock_df.columns:
            duplicates = stock_df['code'].duplicated().sum()
            print(f"\n7. 重复检查:")
            print(f"   重复代码数: {duplicates}")
            if duplicates > 0:
                print("   重复的代码:")
                dup_codes = stock_df[stock_df['code'].duplicated(keep=False)]['code'].unique()
                for code in dup_codes[:10]:  # 只显示前10个
                    print(f"     {code}")
        
        # 分析数据质量
        print(f"\n8. 数据质量分析:")
        print(f"   空代码数: {stock_df['code'].isna().sum()}")
        print(f"   空名称数: {stock_df['name'].isna().sum()}")
        print(f"   代码长度分布:")
        code_lengths = stock_df['code'].str.len().value_counts().sort_index()
        for length, count in code_lengths.items():
            print(f"     {length}位: {count} 只")
        
        # 检查是否包含非A股数据
        print(f"\n9. 非A股数据检查:")
        non_a_stocks = []
        for _, row in stock_df.iterrows():
            code = str(row['code'])
            market = row['market']
            
            # 检查是否符合A股规则
            is_a_stock = False
            if market == 'SH':
                is_a_stock = code[:3] in ('600', '601', '603', '605', '688')
            elif market == 'SZ':
                is_a_stock = code[:3] in ('000', '002', '003', '300')
            
            if not is_a_stock:
                non_a_stocks.append(f"{code} - {row['name']} - {market}")
        
        print(f"   非A股数据: {len(non_a_stocks)} 只")
        if non_a_stocks:
            print("   非A股样本:")
            for stock in non_a_stocks[:10]:  # 只显示前10个
                print(f"     {stock}")
        
        return stock_df
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_data_source_issue():
    """分析数据源问题的根本原因"""
    
    print("\n" + "="*80)
    print("数据源问题根本原因分析")
    print("="*80)
    
    print("\n可能的原因:")
    print("1. 通达信API返回的数据包含了大量非A股证券")
    print("   - B股 (900xxx, 200xxx)")
    print("   - 基金 (5xxxxx, 1xxxxx)")
    print("   - 债券 (1xxxxx, 0xxxxx)")
    print("   - 权证 (5xxxxx)")
    print("   - 其他金融产品")
    
    print("\n2. 过滤逻辑问题")
    print("   - _is_a_stock方法有重复定义")
    print("   - 过滤条件不够严格")
    print("   - 代码格式处理有问题")
    
    print("\n3. 数据重复问题")
    print("   - 同一股票在不同市场重复")
    print("   - 缓存数据与实时数据混合")
    print("   - API返回重复记录")
    
    print("\n4. 官方数据与API数据差异")
    print("   - 官方统计可能只计算A股")
    print("   - API可能包含所有证券类型")
    print("   - 统计时间点不同")

if __name__ == '__main__':
    # 执行测试
    result = test_tongdaxin_actual_data()
    
    # 分析问题
    analyze_data_source_issue()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
