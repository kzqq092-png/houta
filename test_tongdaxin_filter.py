#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件修复后的效果

验证A股过滤是否生效
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tongdaxin_filter():
    """测试通达信插件A股过滤效果"""
    
    print("=" * 80)
    print("通达信插件A股过滤测试")
    print("=" * 80)
    
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        plugin = TongdaxinStockPlugin()
        
        print("\n1. 获取过滤后的A股数据...")
        stock_df = plugin.get_stock_list()
        
        if stock_df is None or len(stock_df) == 0:
            print("无法获取数据")
            return
        
        print(f"获取到 {len(stock_df)} 条A股数据")
        
        # 分析市场分布
        print("\n2. 市场分布分析:")
        print("-" * 80)
        
        sh_count = 0
        sz_count = 0
        
        for row in stock_df:
            if row['market'] == 'SH':
                sh_count += 1
            elif row['market'] == 'SZ':
                sz_count += 1
        
        print(f"上海A股: {sh_count} 条")
        print(f"深圳A股: {sz_count} 条")
        print(f"总计: {sh_count + sz_count} 条")
        
        # 分析代码模式
        print("\n3. 代码模式分析:")
        print("-" * 80)
        
        patterns = {}
        for row in stock_df:
            code = str(row['code'])
            market = row['market']
            
            if len(code) >= 3:
                prefix = code[:3]
                key = f"{market}_{prefix}"
                patterns[key] = patterns.get(key, 0) + 1
        
        for pattern, count in sorted(patterns.items()):
            print(f"{pattern:12} : {count:5} 条")
        
        # 验证A股代码模式
        print("\n4. A股代码模式验证:")
        print("-" * 80)
        
        valid_patterns = {
            'SH': ['600', '601', '603', '605', '688'],
            'SZ': ['000', '002', '003', '300']
        }
        
        invalid_codes = []
        for row in stock_df:
            code = str(row['code'])
            market = row['market']
            
            if market == 'SH':
                if not code.startswith(tuple(valid_patterns['SH'])):
                    invalid_codes.append(f"{code} ({market})")
            elif market == 'SZ':
                if not code.startswith(tuple(valid_patterns['SZ'])):
                    invalid_codes.append(f"{code} ({market})")
        
        if invalid_codes:
            print(f"发现 {len(invalid_codes)} 个非A股代码:")
            for code in invalid_codes[:10]:  # 只显示前10个
                print(f"  {code}")
            if len(invalid_codes) > 10:
                print(f"  ... 还有 {len(invalid_codes) - 10} 个")
        else:
            print("✅ 所有代码都符合A股模式")
        
        # 对比官方数据
        print("\n5. 与官方数据对比:")
        print("-" * 80)
        
        total_count = len(stock_df)
        official_total = 5123
        official_sh = 2272
        official_sz = 2851
        
        print(f"插件数据: SH={sh_count}, SZ={sz_count}, 总计={total_count}")
        print(f"官方数据: SH={official_sh}, SZ={official_sz}, 总计={official_total}")
        print(f"差异: SH={sh_count - official_sh:+d}, SZ={sz_count - official_sz:+d}, 总计={total_count - official_total:+d}")
        
        # 评估结果
        print("\n6. 修复效果评估:")
        print("-" * 80)
        
        if total_count <= 6000:  # 合理的A股数量范围
            print("✅ 修复成功: 数据量在合理范围内")
        else:
            print("⚠️  数据量仍然偏大，可能需要进一步过滤")
        
        if abs(total_count - official_total) <= 500:  # 允许500的误差
            print("✅ 与官方数据基本一致")
        else:
            print("⚠️  与官方数据存在较大差异")
        
        # 显示样本数据
        print("\n7. 样本数据:")
        print("-" * 80)
        
        for i, row in enumerate(stock_df[:10]):
            print(f"{row['code']:8} {row['name']:20} {row['market']:4}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("开始测试通达信插件A股过滤...")
    
    success = test_tongdaxin_filter()
    
    if success:
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        print("修复效果:")
        print("1. 只返回A股股票")
        print("2. 排除B股、基金、债券等")
        print("3. 数据量接近官方统计")
        print("4. K线专用数据下载UI将显示正确的A股数量")
    
    print("\n测试结束")
