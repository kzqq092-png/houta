#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证真实的板块资金流API接口
"""

import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_eastmoney_api():
    """测试东方财富板块资金流API"""
    print("🔍 测试东方财富板块资金流API...")

    # 东方财富板块资金流API
    urls_to_test = [
        "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124",
        "http://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=TRADE_DATE&sortTypes=-1&pageSize=50&pageNumber=1&reportName=RPT_INDUSTRY_FUNDFLOW&columns=INDUSTRY_CODE,INDUSTRY_NAME,CLOSE_PRICE,CHANGE_RATE,MAIN_FORCE_NET,MAIN_FORCE_NET_RATE,SUPER_LARGE_NET,SUPER_LARGE_NET_RATE,LARGE_NET,LARGE_NET_RATE,MEDIUM_NET,MEDIUM_NET_RATE,SMALL_NET,SMALL_NET_RATE",
        "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=m:90+t:2&fields=f12,f14,f2,f3,f62"
    ]

    for i, url in enumerate(urls_to_test, 1):
        try:
            print(f"   测试API {i}: {url[:80]}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://data.eastmoney.com/'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data and 'data' in data:
                        print(f"   ✅ API {i} 可用 - 返回数据: {len(data.get('data', {}).get('diff', []))} 条记录")
                        return True, url, data
                    else:
                        print(f"   ⚠️ API {i} 响应格式异常")
                except json.JSONDecodeError:
                    print(f"   ❌ API {i} 返回非JSON数据")
            else:
                print(f"   ❌ API {i} 请求失败: {response.status_code}")

        except Exception as e:
            print(f"   ❌ API {i} 异常: {e}")

    return False, None, None


def test_sina_api():
    """测试新浪财经板块资金流API"""
    print("🔍 测试新浪财经板块资金流API...")

    urls_to_test = [
        "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=20&sort=changepercent&asc=0&node=hy_s&symbol=&_s_r_a=page",
        "http://vip.stock.finance.sina.com.cn/q/go.php/vInvestConsult/kind/historySearchResult",
        "http://hq.sinajs.cn/list=s_sh000001"
    ]

    for i, url in enumerate(urls_to_test, 1):
        try:
            print(f"   测试API {i}: {url[:80]}...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text
                if content and len(content) > 10:
                    print(f"   ✅ API {i} 可用 - 返回数据长度: {len(content)}")
                    # 检查是否包含板块相关数据
                    if any(keyword in content for keyword in ['板块', '行业', 'sector', 'industry']):
                        print(f"   ✅ API {i} 包含板块相关数据")
                        return True, url, content
                    else:
                        print(f"   ⚠️ API {i} 不包含板块数据")
                else:
                    print(f"   ❌ API {i} 返回空数据")
            else:
                print(f"   ❌ API {i} 请求失败: {response.status_code}")

        except Exception as e:
            print(f"   ❌ API {i} 异常: {e}")

    return False, None, None


def verify_real_apis():
    """验证真实的板块资金流API接口"""
    print("🧪 验证真实的板块资金流API接口")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {}

    # 测试东方财富API
    em_success, em_url, em_data = test_eastmoney_api()
    results['eastmoney'] = {
        'success': em_success,
        'url': em_url,
        'has_real_data': em_success
    }

    print()

    # 测试新浪财经API
    sina_success, sina_url, sina_data = test_sina_api()
    results['sina'] = {
        'success': sina_success,
        'url': sina_url,
        'has_real_data': sina_success
    }

    print()
    print("=" * 60)
    print("📊 验证结果总结:")

    for source, result in results.items():
        status = "✅ 可用" if result['success'] else "❌ 不可用"
        print(f"   {source.upper()}: {status}")
        if result['success']:
            print(f"      - 可用API: {result['url'][:80]}...")

    return results


if __name__ == "__main__":
    results = verify_real_apis()

    print(f"\n🎯 建议操作:")
    if results['eastmoney']['success']:
        print(f"   ✅ 保留东方财富插件的板块资金流功能")
    else:
        print(f"   ❌ 删除东方财富插件的板块资金流功能")

    if results['sina']['success']:
        print(f"   ✅ 保留新浪插件的板块资金流功能")
    else:
        print(f"   ❌ 删除新浪插件的板块资金流功能")

    print(f"   ❌ 删除自定义数据插件的板块资金流功能（无法验证真实数据源）")

    sys.exit(0)
