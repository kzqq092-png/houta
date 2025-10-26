#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct analysis of TongdaxinStockPlugin code
"""

import re
import os

def analyze_tongdaxin_code():
    """Analyze TongdaxinStockPlugin code directly"""
    
    plugin_file = r"plugins\data_sources\stock\tongdaxin_plugin.py"
    
    if not os.path.exists(plugin_file):
        print("[ERROR] Plugin file not found: {}".format(plugin_file))
        return
    
    print("=" * 80)
    print("Direct Code Analysis of TongdaxinStockPlugin")
    print("=" * 80)
    
    with open(plugin_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find fetch_stock_list method
    print("\n1. Searching for fetch_stock_list method...")
    match = re.search(r'def fetch_stock_list\(.*?\):(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    
    if match:
        method_content = match.group(0)
        lines = method_content.split('\n')[:50]  # First 50 lines
        print("[OK] Found fetch_stock_list method")
        print("-" * 80)
        for i, line in enumerate(lines[:30], 1):
            print("{:3d}: {}".format(i, line))
    else:
        print("[NO] fetch_stock_list method not found")
    
    # Find API calls
    print("\n" + "=" * 80)
    print("2. Searching for API calls...")
    api_patterns = [
        r'pytdx.*get.*stock',
        r'hq\.get_security_list',
        r'requests\.get',
        r'get_security_list',
        r'API.*stock',
        r'http.*stock'
    ]
    
    found_apis = set()
    for pattern in api_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            found_apis.add(match.group(0))
    
    if found_apis:
        print("[OK] Found {} API references:".format(len(found_apis)))
        for api in sorted(found_apis):
            print("  - {}".format(api[:60]))
    else:
        print("[NO] No API calls found")
    
    # Find limit/filter logic
    print("\n" + "=" * 80)
    print("3. Searching for data filtering/limiting logic...")
    
    filter_keywords = [
        'ST', 'suspend', 'exclude', 'filter', 'limit', 'skip', 
        'status', 'trade_status', 'listing_status', 'delisting'
    ]
    
    for keyword in filter_keywords:
        pattern = r'\b' + keyword + r'\b'
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            print("  - '{}': {} occurrences".format(keyword, len(matches)))
    
    # Find configuration constants
    print("\n" + "=" * 80)
    print("4. Searching for configuration and constants...")
    
    const_patterns = [
        (r'MAX_STOCK.*?=.*', 'MAX_STOCK constants'),
        (r'LIMIT.*?=.*', 'LIMIT constants'),
        (r'timeout.*?=', 'timeout settings'),
        (r'retry.*?=', 'retry settings'),
    ]
    
    for pattern, desc in const_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            print("  [{}] {}".format(desc, match.group(0)[:70]))
    
    # Check for data source settings
    print("\n" + "=" * 80)
    print("5. Searching for data source and exchange configuration...")
    
    sh_sz_patterns = [
        r'sh|SH|shanghai|SHANGHAI|1',
        r'sz|SZ|shenzhen|SHENZHEN|0'
    ]
    
    for market_code, market_name in [('sh', 'Shanghai'), ('sz', 'Shenzhen')]:
        pattern = r"['\"]" + market_code + r"['\"]"
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            print("  - Market code '{}': {} occurrences".format(market_code, len(matches)))
            
            # Show context around first match
            for i, match in enumerate(matches[:3]):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                print("    Occurrence {}: ...{}...".format(i+1, context[:80]))
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("6. Code Statistics")
    print("=" * 80)
    lines = content.split('\n')
    print("  Total lines: {}".format(len(lines)))
    print("  Classes: {}".format(len(re.findall(r'^class ', content, re.MULTILINE))))
    print("  Methods: {}".format(len(re.findall(r'^\s+def ', content, re.MULTILINE))))
    print("  Comments: {}".format(len(re.findall(r'#', content))))


if __name__ == '__main__':
    analyze_tongdaxin_code()
