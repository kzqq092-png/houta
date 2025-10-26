#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证通达信插件修复效果
测试修复后的数据量和质量
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fixed_tongdaxin():
    """测试修复后的通达信插件"""
    
    print("="*80)
    print("通达信插件修复效果验证")
    print("="*80)
    
    try:
        # 导入通达信插件
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        print("\n1. 初始化通达信插件...")
        plugin = TongdaxinStockPlugin()
        
        print("\n2. 调用修复后的get_stock_list()方法...")
        stock_df = plugin.get_stock_list()
        
        if stock_df.empty:
            print("❌ 获取数据失败或为空")
            return
        
        print(f"\n3. 修复后数据统计:")
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
            
            from collections import Counter
            prefix_counts = Counter(prefixes)
            print("   所有前缀分布:")
            for prefix, count in sorted(prefix_counts.items()):
                print(f"   {prefix}xxx: {count} 只")
        
        # 检查是否有重复
        if 'code' in stock_df.columns:
            duplicates = stock_df['code'].duplicated().sum()
            print(f"\n6. 重复检查:")
            print(f"   重复代码数: {duplicates}")
            if duplicates > 0:
                print("   重复的代码:")
                dup_codes = stock_df[stock_df['code'].duplicated(keep=False)]['code'].unique()
                for code in dup_codes[:10]:  # 只显示前10个
                    print(f"     {code}")
        
        # 验证A股规则
        print(f"\n7. A股规则验证:")
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
        else:
            print("   ✅ 所有数据都符合A股规则")
        
        # 与官方数据对比
        print(f"\n8. 与官方数据对比:")
        print(f"   官方数据 (2024-03-31):")
        print(f"   上证所: 2,272 家")
        print(f"   深证所: 2,851 家")
        print(f"   合计: 5,123 家")
        print(f"   插件数据:")
        sh_count = len(stock_df[stock_df['market'] == 'SH']) if 'market' in stock_df.columns else 0
        sz_count = len(stock_df[stock_df['market'] == 'SZ']) if 'market' in stock_df.columns else 0
        print(f"   上证所: {sh_count} 家")
        print(f"   深证所: {sz_count} 家")
        print(f"   合计: {len(stock_df)} 家")
        
        # 差异分析
        sh_diff = sh_count - 2272
        sz_diff = sz_count - 2851
        total_diff = len(stock_df) - 5123
        
        print(f"\n9. 差异分析:")
        print(f"   上证差异: {sh_diff:+d} ({sh_diff/2272*100:+.1f}%)")
        print(f"   深证差异: {sz_diff:+d} ({sz_diff/2851*100:+.1f}%)")
        print(f"   总差异: {total_diff:+d} ({total_diff/5123*100:+.1f}%)")
        
        if abs(total_diff) < 100:  # 差异小于100认为是合理的
            print("   ✅ 数据量在合理范围内")
        else:
            print("   ⚠️ 数据量差异较大，需要进一步分析")
        
        return stock_df
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # 执行测试
    result = test_fixed_tongdaxin()
    
    print("\n" + "="*80)
    print("验证完成")
    print("="*80)