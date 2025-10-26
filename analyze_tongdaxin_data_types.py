#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信API返回的数据类型分析

目标：分析为什么通达信API返回上万条数据，而官方A股只有5123家
"""

import sys
import os
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_tongdaxin_data():
    """分析通达信API返回的数据类型"""
    
    print("=" * 80)
    print("通达信API数据类型分析")
    print("=" * 80)
    
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        plugin = TongdaxinStockPlugin()
        
        print("\n1. 获取原始数据...")
        stock_df = plugin.get_stock_list()
        
        if stock_df is None or len(stock_df) == 0:
            print("❌ 无法获取数据")
            return
        
        print(f"✅ 获取到 {len(stock_df)} 条数据")
        
        # 分析代码模式
        print("\n2. 分析代码模式...")
        code_patterns = {}
        
        for row in stock_df:
            code = str(row['code'])
            market = row['market']
            
            # 提取代码前缀
            if len(code) >= 3:
                prefix = code[:3]
                key = f"{market}_{prefix}"
                if key not in code_patterns:
                    code_patterns[key] = []
                code_patterns[key].append({
                    'code': code,
                    'name': row['name']
                })
        
        # 统计各模式的数量
        print("\n3. 代码模式统计:")
        print("-" * 80)
        
        pattern_stats = {}
        for pattern, items in code_patterns.items():
            count = len(items)
            pattern_stats[pattern] = count
            print(f"{pattern:12} : {count:5} 条")
        
        # 分类分析
        print("\n4. 证券类型分类:")
        print("-" * 80)
        
        categories = {
            'A股主板': [],
            'A股中小板': [],
            'A股创业板': [],
            'A股科创板': [],
            'B股': [],
            '基金': [],
            '债券': [],
            '权证': [],
            '其他': []
        }
        
        for row in stock_df:
            code = str(row['code'])
            market = row['market']
            
            # A股分类
            if market == 'SH':
                if code.startswith(('600', '601', '603', '605')):
                    categories['A股主板'].append(code)
                elif code.startswith('688'):
                    categories['A股科创板'].append(code)
                elif code.startswith('900'):
                    categories['B股'].append(code)
                elif code.startswith(('5', '1')):
                    categories['基金'].append(code)
                else:
                    categories['其他'].append(code)
            elif market == 'SZ':
                if code.startswith(('000', '003')):
                    categories['A股主板'].append(code)
                elif code.startswith('002'):
                    categories['A股中小板'].append(code)
                elif code.startswith('300'):
                    categories['A股创业板'].append(code)
                elif code.startswith('200'):
                    categories['B股'].append(code)
                elif code.startswith(('5', '1')):
                    categories['基金'].append(code)
                else:
                    categories['其他'].append(code)
        
        # 输出分类统计
        total_a_stocks = 0
        for category, codes in categories.items():
            count = len(codes)
            if 'A股' in category:
                total_a_stocks += count
            print(f"{category:12} : {count:5} 条")
        
        print("-" * 80)
        print(f"{'A股总计':12} : {total_a_stocks:5} 条")
        print(f"{'官方数据':12} : {5123:5} 条")
        print(f"{'差异':12} : {total_a_stocks - 5123:+5} 条")
        
        # 详细分析
        print("\n5. 详细分析:")
        print("-" * 80)
        
        if total_a_stocks > 5123:
            print(f"⚠️  A股数量({total_a_stocks}) > 官方数据(5123)")
            print("可能原因:")
            print("  - 包含了ST股票")
            print("  - 包含了暂停交易的股票")
            print("  - 包含了已退市但未清理的股票")
            print("  - 数据源统计口径不同")
        elif total_a_stocks < 5123:
            print(f"⚠️  A股数量({total_a_stocks}) < 官方数据(5123)")
            print("可能原因:")
            print("  - 数据不完整")
            print("  - 某些新股未包含")
            print("  - API限制或过滤")
        else:
            print("✅ A股数量与官方数据一致")
        
        # 输出样本数据
        print("\n6. A股样本数据:")
        print("-" * 80)
        
        a_stocks = []
        for category in ['A股主板', 'A股中小板', 'A股创业板', 'A股科创板']:
            for code in categories[category]:
                # 找到对应的行数据
                for row in stock_df:
                    if row['code'] == code:
                        a_stocks.append({
                            'code': code,
                            'name': row['name'],
                            'market': row['market'],
                            'category': category
                        })
                        break
        
        # 显示前10条
        for i, stock in enumerate(a_stocks[:10]):
            print(f"{stock['code']:8} {stock['name']:20} {stock['market']:4} {stock['category']}")
        
        print(f"\n总共A股: {len(a_stocks)} 条")
        
        return a_stocks, categories
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == '__main__':
    print("开始分析通达信API数据类型...")
    
    # 分析数据
    a_stocks, categories = analyze_tongdaxin_data()
    
    if a_stocks is not None:
        print("\n" + "=" * 80)
        print("分析完成")
        print("=" * 80)
        print("建议:")
        print("1. 修改通达信插件的get_stock_list方法")
        print("2. 添加A股过滤逻辑")
        print("3. 只返回A股股票，排除B股、基金、债券等")
        print("4. 确保返回数量与官方数据一致")
    
    print("\n分析结束")
