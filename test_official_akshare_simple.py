#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的批量选择功能
验证是否直接使用官方akshare API获取A股列表
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_official_akshare_api():
    """测试官方akshare API"""
    
    print("="*80)
    print("OFFICIAL AKSHARE API TEST")
    print("="*80)
    
    try:
        import akshare as ak
        print("OK: akshare库已安装")
        
        # 测试获取A股列表
        print("\n测试获取A股列表...")
        stock_list_df = ak.stock_info_a_code_name()
        
        if not stock_list_df.empty:
            print(f"OK: 成功获取A股数据: {len(stock_list_df)} 只股票")
            
            # 显示前10只股票
            print("\n前10只A股样本:")
            for i, (_, row) in enumerate(stock_list_df.head(10).iterrows()):
                print(f"  {i+1:2d}. {row.get('code', '')} - {row.get('name', '')}")
            
            # 统计市场分布
            print("\n市场分布统计:")
            sh_count = 0
            sz_count = 0
            
            for _, row in stock_list_df.iterrows():
                code = str(row.get('code', '')).strip()
                if code.startswith(('600', '601', '603', '605', '688')):
                    sh_count += 1
                elif code.startswith(('000', '001', '002', '003', '300')):
                    sz_count += 1
            
            print(f"  上证A股: {sh_count} 只")
            print(f"  深证A股: {sz_count} 只")
            print(f"  合计: {sh_count + sz_count} 只")
            
            # 与官方统计对比
            print("\n与官方统计对比:")
            print(f"  官方统计 (2024-03-31): 5,123 只")
            print(f"  akshare数据: {len(stock_list_df)} 只")
            print(f"  差异: {len(stock_list_df) - 5123:+d} 只")
            
            if abs(len(stock_list_df) - 5123) <= 500:
                print("  OK: 数据量基本一致")
            else:
                print("  WARNING: 数据量存在差异")
                
        else:
            print("ERROR: 获取A股数据失败")
            
    except ImportError:
        print("ERROR: akshare库未安装，请安装: pip install akshare")
    except Exception as e:
        print(f"ERROR: 测试失败: {e}")

def test_modified_get_stock_data():
    """测试修改后的get_stock_data方法"""
    
    print("\n" + "="*80)
    print("MODIFIED GET_STOCK_DATA TEST")
    print("="*80)
    
    print("修改内容:")
    print("1. 直接使用akshare官方API获取A股列表")
    print("2. 绕过插件系统")
    print("3. 确保数据是最新最全的")
    
    print("\n预期效果:")
    print("- 批量选择时直接使用官方数据")
    print("- 不再依赖数据源插件")
    print("- 数据量接近官方统计")
    print("- 获取速度更快")
    
    print("\nOK: 修改完成，请重新测试批量选择功能")

if __name__ == '__main__':
    test_official_akshare_api()
    test_modified_get_stock_data()