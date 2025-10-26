#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试通达信API返回的原始数据

分析为什么只返回1379只股票
"""

import sys
import os
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_tongdaxin_raw_data():
    """调试通达信API返回的原始数据"""
    
    print("=" * 80)
    print("通达信API原始数据调试")
    print("=" * 80)
    
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        plugin = TongdaxinStockPlugin()
        
        print("\n1. 获取原始数据（无过滤）...")
        
        # 临时修改插件，获取原始数据
        original_get_stock_list = plugin.get_stock_list
        
        def debug_get_stock_list():
            """调试版本的get_stock_list，不过滤数据"""
            try:
                # 检查缓存
                current_time = time.time()
                if (plugin._stock_list_cache is not None and
                    plugin._cache_timestamp and
                        current_time - plugin._cache_timestamp < plugin._cache_duration):
                    return plugin._stock_list_cache

                if not plugin._ensure_connection():
                    print("无法连接到通达信服务器")
                    return []

                stock_list = []

                with plugin.connection_lock:
                    # 获取上海市场股票
                    sh_count = plugin.api_client.get_security_count(1)
                    print(f"上海市场证券总数: {sh_count}")
                    
                    if sh_count and sh_count > 0:
                        for start in range(0, min(sh_count, 10000), 1000):
                            sh_stocks = plugin.api_client.get_security_list(1, start)
                            if sh_stocks:
                                for stock in sh_stocks:
                                    stock_list.append({
                                        'code': stock['code'],
                                        'name': stock['name'],
                                        'market': 'SH'
                                    })

                    # 获取深圳市场股票
                    sz_count = plugin.api_client.get_security_count(0)
                    print(f"深圳市场证券总数: {sz_count}")
                    
                    if sz_count and sz_count > 0:
                        for start in range(0, min(sz_count, 10000), 1000):
                            sz_stocks = plugin.api_client.get_security_list(0, start)
                            if sz_stocks:
                                for stock in sz_stocks:
                                    stock_list.append({
                                        'code': stock['code'],
                                        'name': stock['name'],
                                        'market': 'SZ'
                                    })

                    plugin.api_client.disconnect()

                print(f"原始数据总数: {len(stock_list)}")
                return stock_list

            except Exception as e:
                print(f"获取原始数据失败: {e}")
                return []

        # 临时替换方法
        import time
        plugin.get_stock_list = debug_get_stock_list
        
        raw_data = plugin.get_stock_list()
        
        if not raw_data:
            print("无法获取原始数据")
            return
        
        print(f"\n2. 原始数据分析:")
        print(f"总数据量: {len(raw_data)}")
        
        # 分析市场分布
        market_counts = Counter()
        for item in raw_data:
            market_counts[item['market']] += 1
        
        print(f"市场分布: {dict(market_counts)}")
        
        # 分析代码格式
        print(f"\n3. 代码格式分析:")
        
        code_lengths = Counter()
        code_prefixes = Counter()
        
        for item in raw_data:
            code = str(item['code'])
            market = item['market']
            
            code_lengths[len(code)] += 1
            
            if len(code) >= 3:
                prefix = code[:3]
                code_prefixes[f"{market}_{prefix}"] += 1
        
        print(f"代码长度分布: {dict(code_lengths)}")
        print(f"代码前缀分布 (前20个):")
        
        for prefix, count in code_prefixes.most_common(20):
            print(f"  {prefix}: {count}")
        
        # 分析A股代码模式
        print(f"\n4. A股代码模式分析:")
        
        a_stock_patterns = {
            'SH': ['600', '601', '603', '605', '688'],
            'SZ': ['000', '002', '003', '300']
        }
        
        a_stock_count = 0
        non_a_stock_count = 0
        
        for item in raw_data:
            code = str(item['code'])
            market = item['market']
            
            is_a_stock = False
            if market == 'SH':
                is_a_stock = code.startswith(tuple(a_stock_patterns['SH']))
            elif market == 'SZ':
                is_a_stock = code.startswith(tuple(a_stock_patterns['SZ']))
            
            if is_a_stock:
                a_stock_count += 1
            else:
                non_a_stock_count += 1
        
        print(f"A股数量: {a_stock_count}")
        print(f"非A股数量: {non_a_stock_count}")
        print(f"A股比例: {a_stock_count / len(raw_data) * 100:.1f}%")
        
        # 显示样本数据
        print(f"\n5. 样本数据:")
        print(f"前20条数据:")
        for i, item in enumerate(raw_data[:20]):
            print(f"  {i+1:2d}. {item['code']:8} {item['name']:20} {item['market']}")
        
        # 显示A股样本
        print(f"\nA股样本数据:")
        a_stock_samples = []
        for item in raw_data:
            code = str(item['code'])
            market = item['market']
            
            is_a_stock = False
            if market == 'SH':
                is_a_stock = code.startswith(tuple(a_stock_patterns['SH']))
            elif market == 'SZ':
                is_a_stock = code.startswith(tuple(a_stock_patterns['SZ']))
            
            if is_a_stock:
                a_stock_samples.append(item)
                if len(a_stock_samples) >= 20:
                    break
        
        for i, item in enumerate(a_stock_samples):
            print(f"  {i+1:2d}. {item['code']:8} {item['name']:20} {item['market']}")
        
        # 分析问题
        print(f"\n6. 问题分析:")
        
        if a_stock_count < 2000:
            print(f"WARNING: A股数量({a_stock_count})明显偏少")
            print("可能原因:")
            print("  1. 通达信API返回的数据不完整")
            print("  2. 代码格式与预期不符")
            print("  3. 市场代码映射有问题")
            print("  4. API限制或过滤")
        
        # 恢复原方法
        plugin.get_stock_list = original_get_stock_list
        
        return raw_data, a_stock_count
        
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


if __name__ == '__main__':
    print("开始调试通达信API原始数据...")
    
    raw_data, a_stock_count = debug_tongdaxin_raw_data()
    
    if raw_data:
        print("\n" + "=" * 80)
        print("调试完成")
        print("=" * 80)
        print(f"原始数据总量: {len(raw_data)}")
        print(f"A股数量: {a_stock_count}")
        print(f"预期A股数量: 5000+")
        print(f"差异: {a_stock_count - 5000:+d}")
        
        if a_stock_count < 2000:
            print("\n问题确认: A股数量明显偏少")
            print("需要进一步分析通达信API的数据格式")
    
    print("\n调试结束")
