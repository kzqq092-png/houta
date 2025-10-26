#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze stock data sources consistency
Compare official data with plugin API results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tongdaxin_plugin():
    """Test TongdaxinStockPlugin to get stock list"""
    try:
        print("=" * 80)
        print("1. Testing TongdaxinStockPlugin")
        print("=" * 80)
        
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        from core.plugin_types import DataType
        
        plugin = TongdaxinStockPlugin()
        
        # Get Shanghai stock list
        print("\n[Getting Shanghai (SH) stock list...]")
        try:
            sh_stock_list = plugin.fetch_stock_list('sh')  # Shanghai
            sh_count = len(sh_stock_list) if sh_stock_list else 0
            print("[OK] Shanghai (SH) total stocks: {}".format(sh_count))
            if sh_stock_list:
                codes = [s.get('code', s.get('symbol', str(s)))[:10] for s in sh_stock_list[:5]]
                print("     First 5: {}".format(codes))
        except Exception as e:
            print("[ERROR] Failed to get Shanghai data: {}".format(e))
            sh_count = 0
        
        # Get Shenzhen stock list
        print("\n[Getting Shenzhen (SZ) stock list...]")
        try:
            sz_stock_list = plugin.fetch_stock_list('sz')  # Shenzhen
            sz_count = len(sz_stock_list) if sz_stock_list else 0
            print("[OK] Shenzhen (SZ) total stocks: {}".format(sz_count))
            if sz_stock_list:
                codes = [s.get('code', s.get('symbol', str(s)))[:10] for s in sz_stock_list[:5]]
                print("     First 5: {}".format(codes))
        except Exception as e:
            print("[ERROR] Failed to get Shenzhen data: {}".format(e))
            sz_count = 0
        
        return {
            'source': 'tongdaxin',
            'sh_count': sh_count,
            'sz_count': sz_count,
            'total': sh_count + sz_count,
            'sh_list': sh_stock_list if sh_stock_list else [],
            'sz_list': sz_stock_list if sz_stock_list else []
        }
        
    except Exception as e:
        print("[ERROR] Testing TongdaxinStockPlugin failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return None


def test_other_plugins():
    """Test other data source plugins"""
    print("\n" + "=" * 80)
    print("2. Scanning other available data source plugins")
    print("=" * 80)
    
    try:
        from core.plugin_manager import get_plugin_manager
        
        plugin_manager = get_plugin_manager()
        
        # Get all stock data source plugins
        stock_plugins = plugin_manager.get_available_plugins_by_data_type('HISTORICAL_KLINE')
        
        print("\nFound {} K-line data source plugins:".format(len(stock_plugins)))
        for plugin_info in stock_plugins:
            plugin_name = plugin_info.get('name', plugin_info.get('plugin_id', 'Unknown'))
            print("  - {}".format(plugin_name))
            
            try:
                plugin = plugin_manager.load_plugin(plugin_info.get('plugin_id'))
                if hasattr(plugin, 'fetch_stock_list'):
                    print("    [OK] Supports fetch_stock_list method")
                else:
                    print("    [NO] Does not support fetch_stock_list method")
            except Exception as e:
                print("    [ERROR] Failed to load: {}".format(e))
        
        return True
        
    except Exception as e:
        print("[ERROR] Scanning plugins failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


def analyze_discrepancy_reasons(sh_diff, sz_diff, plugin_result):
    """Analyze reasons for discrepancy"""
    
    reasons = []
    
    # Analysis
    if sh_diff > 0 or sz_diff > 0:
        reasons.append(
            "Reason 1: [ST/PT Stocks] Plugin may include suspended or risk-warning stocks "
            "(ST, *ST, PT, etc.), which may be classified differently in official data"
        )
    
    if sh_diff < 0 or sz_diff < 0:
        reasons.append(
            "Reason 2: [Incomplete Data] Plugin data may be incomplete, with some newly listed "
            "or delisted companies missing"
        )
    
    # Generic reasons
    reasons.extend([
        "Reason 3: [Time Difference] Official data is from 2024-03-31, plugin data may be from different time",
        
        "Reason 4: [Data Source Difference] Tongdaxin API may use different counting method than official exchange",
        
        "Reason 5: [Update Delay] Plugin cache may not be updated in time, causing data lag",
        
        "Reason 6: [Sector Filtering] Plugin may filter specific sectors (main board, SME board, GEM separately)",
        
        "Reason 7: [B-share Difference] Exchange may count B-shares (foreign shares) but plugin only counts A-shares",
        
        "Reason 8: [Suspended Trading] Suspended stocks may be counted differently in different data sources",
        
        "Reason 9: [Delisting Status] Recently delisted companies may be counted or excluded differently",
        
        "Reason 10: [Data Processing] Different processing rules during data collection and transmission",
    ])
    
    return reasons


def analyze_data_consistency():
    """Analyze data consistency"""
    
    print("\n" + "=" * 80)
    print("3. Data Consistency Analysis")
    print("=" * 80)
    
    # Official data (2024-03-31)
    official_data = {
        'date': '2024-03-31',
        'source': 'China Securities Regulatory Commission',
        'sh_count': 2272,  # Shanghai
        'sz_count': 2851,  # Shenzhen
        'total': 5123
    }
    
    print("\nOfficial Data (as of {}):".format(official_data['date']))
    print("  Shanghai Exchange (SH): {} listed companies".format(official_data['sh_count']))
    print("  Shenzhen Exchange (SZ): {} listed companies".format(official_data['sz_count']))
    print("  Total: {} companies".format(official_data['total']))
    
    # Get plugin data
    tongdaxin_result = test_tongdaxin_plugin()
    
    if tongdaxin_result:
        print("\n" + "-" * 80)
        print("Data Comparison")
        print("-" * 80)
        
        # Shanghai comparison
        sh_diff = tongdaxin_result['sh_count'] - official_data['sh_count']
        sh_ratio = (sh_diff / official_data['sh_count'] * 100) if official_data['sh_count'] > 0 else 0
        print("\nShanghai Data:")
        print("  Official Data: {} companies".format(official_data['sh_count']))
        print("  Plugin Retrieved: {} companies".format(tongdaxin_result['sh_count']))
        print("  Difference: {} ({:+.1f}%)".format(sh_diff, sh_ratio))
        if sh_diff != 0:
            diff_text = "more" if sh_diff > 0 else "fewer"
            print("  [NOTE] {} {} companies".format(diff_text, abs(sh_diff)))
        
        # Shenzhen comparison
        sz_diff = tongdaxin_result['sz_count'] - official_data['sz_count']
        sz_ratio = (sz_diff / official_data['sz_count'] * 100) if official_data['sz_count'] > 0 else 0
        print("\nShenzhen Data:")
        print("  Official Data: {} companies".format(official_data['sz_count']))
        print("  Plugin Retrieved: {} companies".format(tongdaxin_result['sz_count']))
        print("  Difference: {} ({:+.1f}%)".format(sz_diff, sz_ratio))
        if sz_diff != 0:
            diff_text = "more" if sz_diff > 0 else "fewer"
            print("  [NOTE] {} {} companies".format(diff_text, abs(sz_diff)))
        
        # Overall comparison
        total_diff = tongdaxin_result['total'] - official_data['total']
        total_ratio = (total_diff / official_data['total'] * 100) if official_data['total'] > 0 else 0
        print("\nOverall Data:")
        print("  Official Data: {} companies".format(official_data['total']))
        print("  Plugin Retrieved: {} companies".format(tongdaxin_result['total']))
        print("  Difference: {} ({:+.1f}%)".format(total_diff, total_ratio))
        
        # Consistency check
        print("\n" + "-" * 80)
        if sh_diff == 0 and sz_diff == 0:
            print("[OK] Data is consistent (matches official data)")
        else:
            print("[WARNING] Data is inconsistent, root cause analysis needed")
            
            print("\nPossible Reasons:")
            print("=" * 80)
            
            reasons = analyze_discrepancy_reasons(sh_diff, sz_diff, tongdaxin_result)
            for reason in reasons:
                print(reason)
    
    return tongdaxin_result


if __name__ == '__main__':
    print("\n[STOCK DATA SOURCE CONSISTENCY ANALYSIS]")
    print("=" * 80)
    print("Target: Verify consistency between plugin and official data")
    print("=" * 80)
    
    try:
        # Execute analysis
        result = analyze_data_consistency()
        
        # Test other plugins
        test_other_plugins()
        
        print("\n" + "=" * 80)
        print("Analysis Complete")
        print("=" * 80)
        
    except Exception as e:
        print("\n[ERROR] An error occurred during analysis: {}".format(e))
        import traceback
        traceback.print_exc()
