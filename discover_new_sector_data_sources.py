#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发现新的板块资金流数据源
"""

import sys
import os
import importlib
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_akshare_sector_apis():
    """测试akshare库的板块资金流API"""
    print("🔍 测试akshare库的板块资金流API...")

    try:
        import akshare as ak
        print(" ✅ akshare库已安装")

        # 尝试各种可能的板块资金流函数
        potential_functions = [
            'sector_fund_flow_rank',
            'stock_sector_fund_flow_rank',
            'stock_board_fund_flow_rank',
            'stock_board_concept_fund_flow_rank',
            'stock_board_industry_fund_flow_rank',
            'stock_fund_flow_individual',
            'stock_individual_fund_flow',
            'stock_board_fund_flow',
            'concept_fund_flow_rank',
            'industry_fund_flow_rank'
        ]

        available_functions = []

        for func_name in potential_functions:
            if hasattr(ak, func_name):
                available_functions.append(func_name)
                print(f"   ✅ 找到函数: ak.{func_name}")

                # 尝试调用函数获取数据
                try:
                    func = getattr(ak, func_name)
                    # 尝试不同的参数组合
                    test_params = [
                        {},
                        {'symbol': '概念板块'},
                        {'symbol': '行业板块'},
                        {'period': '今日'},
                        {'market': '沪深A股'}
                    ]

                    for params in test_params:
                        try:
                            data = func(**params)
                            if data is not None and not data.empty:
                                print(f"      ✅ 成功获取数据: {len(data)} 条记录")
                                print(f"      📊 数据列: {list(data.columns)}")
                                return True, func_name, data
                        except Exception as e:
                            continue

                except Exception as e:
                    print(f"      ❌ 调用失败: {e}")

        if not available_functions:
            print(" ❌ 未找到板块资金流相关函数")

        return False, None, None

    except ImportError:
        print(" ❌ akshare库未安装")
        return False, None, None
    except Exception as e:
        print(f"   ❌ 测试akshare失败: {e}")
        return False, None, None


def test_tushare_sector_apis():
    """测试tushare库的板块资金流API"""
    print("🔍 测试tushare库的板块资金流API...")

    try:
        import tushare as ts
        print(" ✅ tushare库已安装")

        # 尝试各种可能的板块资金流函数
        potential_functions = [
            'moneyflow',
            'moneyflow_hsgt',
            'fund_flow',
            'sector_fund_flow',
            'concept_detail',
            'ths_index',
            'index_basic'
        ]

        available_functions = []

        for func_name in potential_functions:
            if hasattr(ts, func_name):
                available_functions.append(func_name)
                print(f"   ✅ 找到函数: ts.{func_name}")

        if not available_functions:
            print(" ❌ 未找到板块资金流相关函数")

        # 注意：tushare需要token，这里只是检查函数是否存在
        print(" ⚠️ tushare需要API token才能获取数据")

        return len(available_functions) > 0, available_functions, None

    except ImportError:
        print(" ❌ tushare库未安装")
        return False, None, None
    except Exception as e:
        print(f"   ❌ 测试tushare失败: {e}")
        return False, None, None


def test_other_data_sources():
    """测试其他可能的数据源"""
    print("🔍 测试其他可能的数据源...")

    # 测试网易财经API
    try:
        import requests

        # 网易财经板块数据API
        netease_urls = [
            "http://quotes.money.163.com/hs/service/diyrank.php?host=http%3A%2F%2Fquotes.money.163.com%2Fhs%2Fservice%2Fdiyrank.php&page=0&query=STYPE%3AEQA&fields=SYMBOL%2CNAME%2CPRICE%2CPERCENT%2CUPDOWN%2CFIVE_MINUTE%2COPEN%2CYESTCLOSE%2CHIGH%2CLOW%2CVOLUME%2CTURNOVER%2CHS%2CLB%2CWB%2CZF%2CPE%2CMCAP%2CTCAP%2CMFSUM%2CMFRATIO.MFRATIO2%2CMFRATIO.MFRATIO10%2CSNAME&sort=PERCENT&order=desc&count=24&type=query",
            "http://quotes.money.163.com/hs/service/diyrank.php?host=/hs/service/diyrank.php&page=0&query=STYPE:EQA&fields=SYMBOL,NAME,PRICE,PERCENT,UPDOWN&sort=PERCENT&order=desc&count=40&type=query"
        ]

        for url in netease_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and 'list' in data:
                        print(f"   ✅ 网易财经API可用: {len(data['list'])} 条数据")
                        return True, 'netease', data
            except Exception as e:
                continue

        print(" ❌ 网易财经API不可用")

    except Exception as e:
        print(f"   ❌ 测试网易财经失败: {e}")

    # 测试腾讯财经API
    try:
        tencent_urls = [
            "http://qt.gtimg.cn/q=s_sh000001,s_sz399001,s_sz399006",
            "http://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get?param=hk00700,day,,,320,qfq"
        ]

        for url in tencent_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200 and response.text:
                    print(f"   ✅ 腾讯财经API可用: 数据长度 {len(response.text)}")
                    return True, 'tencent', response.text
            except Exception as e:
                continue

        print(" ❌ 腾讯财经API不可用")

    except Exception as e:
        print(f"   ❌ 测试腾讯财经失败: {e}")

    return False, None, None


def discover_new_sector_data_sources():
    """发现新的板块资金流数据源"""
    print("🔍 发现新的板块资金流数据源")
    print("=" * 60)
    print(f"发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    discovered_sources = []

    # 测试akshare
    ak_success, ak_func, ak_data = test_akshare_sector_apis()
    if ak_success:
        discovered_sources.append({
            'name': 'AKShare',
            'type': 'python_library',
            'function': ak_func,
            'data_sample': ak_data,
            'status': 'available'
        })

    print()

    # 测试tushare
    ts_success, ts_funcs, ts_data = test_tushare_sector_apis()
    if ts_success:
        discovered_sources.append({
            'name': 'TuShare',
            'type': 'python_library',
            'functions': ts_funcs,
            'data_sample': ts_data,
            'status': 'needs_token'
        })

    print()

    # 测试其他数据源
    other_success, other_name, other_data = test_other_data_sources()
    if other_success:
        discovered_sources.append({
            'name': other_name,
            'type': 'web_api',
            'data_sample': other_data,
            'status': 'available'
        })

    print()
    print("=" * 60)
    print("📊 发现结果总结:")
    print(f"   发现的数据源数量: {len(discovered_sources)}")

    if discovered_sources:
        print(f"\n✅ 可用的数据源:")
        for source in discovered_sources:
            print(f"   - {source['name']} ({source['type']}) - {source['status']}")
            if 'function' in source:
                print(f"     函数: {source['function']}")
            elif 'functions' in source:
                print(f"     函数: {', '.join(source['functions'])}")
    else:
        print(f"\n❌ 未发现新的可用数据源")

    return discovered_sources


if __name__ == "__main__":
    discovered_sources = discover_new_sector_data_sources()

    if discovered_sources:
        print(f"\n🚀 发现了 {len(discovered_sources)} 个新的数据源！")
        print(f"可以为这些数据源创建新的插件")
    else:
        print(f"\n⚠️ 未发现新的可用数据源")
        print(f"当前只有东方财富插件提供真实的板块资金流数据")

    sys.exit(0)
