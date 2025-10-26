#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析通达信插件代码问题
直接检查代码逻辑，不运行插件
"""

import re
import os

def analyze_tongdaxin_code():
    """分析通达信插件代码"""
    
    plugin_file = r"plugins\data_sources\stock\tongdaxin_plugin.py"
    
    if not os.path.exists(plugin_file):
        print("[ERROR] Plugin file not found: {}".format(plugin_file))
        return
    
    print("="*80)
    print("Tongdaxin Plugin Code Analysis")
    print("="*80)
    
    with open(plugin_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查重复的方法定义
    print("\n1. Checking for duplicate method definitions...")
    is_a_stock_count = content.count('def _is_a_stock(')
    print("   _is_a_stock method definitions: {}".format(is_a_stock_count))
    
    if is_a_stock_count > 1:
        print("   [ISSUE] Found {} duplicate _is_a_stock method definitions".format(is_a_stock_count))
    else:
        print("   [OK] Only one _is_a_stock method definition")
    
    # 检查数据截断问题
    print("\n2. Checking for data truncation issues...")
    min_count_pattern = r'min\([^,]+,\s*10000\)'
    min_matches = re.findall(min_count_pattern, content)
    
    if min_matches:
        print("   [ISSUE] Found data truncation at 10,000:")
        for match in min_matches:
            print("     {}".format(match))
    else:
        print("   [OK] No data truncation found")
    
    # 检查过滤逻辑
    print("\n3. Checking A-share filtering logic...")
    
    # 查找_is_a_stock方法
    is_a_stock_match = re.search(r'def _is_a_stock\(.*?\):(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    
    if is_a_stock_match:
        method_content = is_a_stock_match.group(0)
        print("   [OK] Found _is_a_stock method")
        
        # 检查A股规则
        sh_rules = re.findall(r"'600'|'601'|'603'|'605'|'688'", method_content)
        sz_rules = re.findall(r"'000'|'002'|'003'|'300'", method_content)
        
        print("   SH A-share rules: {}".format(sh_rules))
        print("   SZ A-share rules: {}".format(sz_rules))
        
        if len(sh_rules) >= 5 and len(sz_rules) >= 4:
            print("   [OK] A-share filtering rules look complete")
        else:
            print("   [WARNING] A-share filtering rules may be incomplete")
    else:
        print("   [ERROR] _is_a_stock method not found")
    
    # 检查get_stock_list方法
    print("\n4. Checking get_stock_list method...")
    
    get_stock_list_match = re.search(r'def get_stock_list\(.*?\):(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    
    if get_stock_list_match:
        method_content = get_stock_list_match.group(0)
        print("   [OK] Found get_stock_list method")
        
        # 检查是否调用了_is_a_stock
        if '_is_a_stock(' in method_content:
            print("   [OK] Method calls _is_a_stock for filtering")
        else:
            print("   [ERROR] Method does not call _is_a_stock")
        
        # 检查是否有去重逻辑
        if 'drop_duplicates' in method_content:
            print("   [OK] Method includes deduplication logic")
        else:
            print("   [WARNING] Method may not have deduplication logic")
        
        # 检查错误处理
        if 'try:' in method_content and 'except' in method_content:
            print("   [OK] Method has error handling")
        else:
            print("   [WARNING] Method may lack proper error handling")
    else:
        print("   [ERROR] get_stock_list method not found")
    
    # 分析可能的数据量问题
    print("\n5. Analyzing potential data volume issues...")
    
    print("   Possible reasons for large data volume:")
    print("   1. API returns all securities (not just A-shares)")
    print("   2. Includes B-shares, funds, bonds, warrants")
    print("   3. Data duplication")
    print("   4. Filtering logic not working properly")
    print("   5. Cache issues")
    
    # 检查API调用
    print("\n6. Checking API calls...")
    
    api_calls = re.findall(r'get_security_count|get_security_list', content)
    if api_calls:
        print("   Found API calls: {}".format(set(api_calls)))
        print("   [OK] Uses correct API methods")
    else:
        print("   [ERROR] No API calls found")
    
    # 总结
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    
    issues = []
    
    if is_a_stock_count > 1:
        issues.append("Duplicate _is_a_stock method definitions")
    
    if min_matches:
        issues.append("Data truncation at 10,000 records")
    
    if issues:
        print("Issues found:")
        for i, issue in enumerate(issues, 1):
            print("  {}. {}".format(i, issue))
    else:
        print("No major issues found in code analysis")
    
    print("\nRecommendations:")
    print("1. Remove duplicate method definitions")
    print("2. Remove data truncation limits")
    print("3. Ensure proper A-share filtering")
    print("4. Add deduplication logic")
    print("5. Improve error handling")

if __name__ == '__main__':
    analyze_tongdaxin_code()