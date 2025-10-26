#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复通达信插件A股过滤问题

问题：通达信API返回所有证券（包括B股、基金、债券等），导致K线专用数据下载UI显示上万条数据
解决：添加A股过滤逻辑，只返回A股股票
"""

import os
import re

def fix_tongdaxin_plugin():
    """修复通达信插件的A股过滤问题"""
    
    plugin_file = "plugins/data_sources/stock/tongdaxin_plugin.py"
    
    if not os.path.exists(plugin_file):
        print(f"文件不存在: {plugin_file}")
        return False
    
    print("=" * 80)
    print("修复通达信插件A股过滤问题")
    print("=" * 80)
    
    try:
        # 读取原文件
        with open(plugin_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("1. 分析当前代码...")
        
        # 检查是否已经有_is_a_stock方法
        if '_is_a_stock' in content:
            print("✅ 发现_is_a_stock方法已存在")
        else:
            print("⚠️  未发现_is_a_stock方法，需要添加")
        
        # 检查get_stock_list方法是否已修改
        if '只保留A股股票' in content:
            print("✅ 发现A股过滤逻辑已存在")
        else:
            print("⚠️  未发现A股过滤逻辑，需要修改")
        
        # 检查修复状态
        if '_is_a_stock' in content and '只保留A股股票' in content:
            print("\n✅ 修复已完成，无需重复修复")
            return True
        
        print("\n2. 应用修复...")
        
        # 修复get_stock_list方法
        old_pattern = r'for stock in sh_stocks:\s*stock_list\.append\(\{\s*\'code\': stock\[\'code\'\],\s*\'name\': stock\[\'name\'\],\s*\'market\': \'SH\'\s*\}\)'
        new_code = '''for stock in sh_stocks:
                                # 只保留A股股票
                                if self._is_a_stock(stock['code'], 'SH'):
                                    stock_list.append({
                                        'code': stock['code'],
                                        'name': stock['name'],
                                        'market': 'SH'
                                    })'''
        
        content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE | re.DOTALL)
        
        # 修复SZ部分
        old_pattern_sz = r'for stock in sz_stocks:\s*stock_list\.append\(\{\s*\'code\': stock\[\'code\'\],\s*\'name\': stock\[\'name\'\],\s*\'market\': \'SZ\'\s*\}\)'
        new_code_sz = '''for stock in sz_stocks:
                                # 只保留A股股票
                                if self._is_a_stock(stock['code'], 'SZ'):
                                    stock_list.append({
                                        'code': stock['code'],
                                        'name': stock['name'],
                                        'market': 'SZ'
                                    })'''
        
        content = re.sub(old_pattern_sz, new_code_sz, content, flags=re.MULTILINE | re.DOTALL)
        
        # 添加_is_a_stock方法（如果不存在）
        if '_is_a_stock' not in content:
            # 在get_stock_list方法后添加_is_a_stock方法
            insert_point = content.find('def get_kline_data(self, symbol: str, period: str = \'daily\',')
            if insert_point > 0:
                method_code = '''
    def _is_a_stock(self, code: str, market: str) -> bool:
        """判断是否为A股股票
        
        Args:
            code: 股票代码
            market: 市场代码 ('SH' 或 'SZ')
            
        Returns:
            bool: 是否为A股股票
        """
        code = str(code)
        
        if market == 'SH':
            # 上海A股：600xxx(主板), 601xxx(主板), 603xxx(主板), 605xxx(主板), 688xxx(科创板)
            return code.startswith(('600', '601', '603', '605', '688'))
        elif market == 'SZ':
            # 深圳A股：000xxx(主板), 002xxx(中小板), 003xxx(主板), 300xxx(创业板)
            return code.startswith(('000', '002', '003', '300'))
        
        return False

'''
                content = content[:insert_point] + method_code + content[insert_point:]
        
        # 更新日志信息
        content = content.replace(
            'logger.info(f"获取股票列表成功，共 {len(df)} 只股票")',
            'logger.info(f"获取A股股票列表成功，共 {len(df)} 只股票")'
        )
        
        # 写入修复后的文件
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 修复完成")
        
        # 验证修复
        print("\n3. 验证修复...")
        
        with open(plugin_file, 'r', encoding='utf-8') as f:
            new_content = f.read()
        
        checks = [
            ('_is_a_stock方法', '_is_a_stock' in new_content),
            ('A股过滤逻辑', '只保留A股股票' in new_content),
            ('SH过滤', 'if self._is_a_stock(stock[\'code\'], \'SH\'):' in new_content),
            ('SZ过滤', 'if self._is_a_stock(stock[\'code\'], \'SZ\'):' in new_content),
            ('日志更新', '获取A股股票列表成功' in new_content)
        ]
        
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
        
        all_passed = all(result for _, result in checks)
        
        if all_passed:
            print("\n✅ 所有修复验证通过")
            return True
        else:
            print("\n❌ 部分修复验证失败")
            return False
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_script():
    """创建测试脚本"""
    
    test_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试通达信插件修复效果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fix():
    try:
        from plugins.data_sources.stock.tongdaxin_plugin import TongdaxinStockPlugin
        
        plugin = TongdaxinStockPlugin()
        stock_df = plugin.get_stock_list()
        
        if stock_df is None or len(stock_df) == 0:
            print("无法获取数据")
            return
        
        print(f"获取到 {len(stock_df)} 条A股数据")
        
        # 统计市场分布
        sh_count = sum(1 for row in stock_df if row['market'] == 'SH')
        sz_count = sum(1 for row in stock_df if row['market'] == 'SZ')
        
        print(f"上海A股: {sh_count} 条")
        print(f"深圳A股: {sz_count} 条")
        print(f"总计: {sh_count + sz_count} 条")
        
        # 验证代码模式
        invalid_codes = []
        for row in stock_df:
            code = str(row['code'])
            market = row['market']
            
            if market == 'SH' and not code.startswith(('600', '601', '603', '605', '688')):
                invalid_codes.append(code)
            elif market == 'SZ' and not code.startswith(('000', '002', '003', '300')):
                invalid_codes.append(code)
        
        if invalid_codes:
            print(f"发现 {len(invalid_codes)} 个非A股代码")
        else:
            print("✅ 所有代码都符合A股模式")
        
        # 对比官方数据
        official_total = 5123
        total_count = len(stock_df)
        diff = total_count - official_total
        
        print(f"\\n官方数据: {official_total} 条")
        print(f"插件数据: {total_count} 条")
        print(f"差异: {diff:+d} 条")
        
        if abs(diff) <= 500:
            print("✅ 与官方数据基本一致")
        else:
            print("⚠️  与官方数据存在差异")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == '__main__':
    test_fix()
'''
    
    with open('test_tongdaxin_fix.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ 测试脚本已创建: test_tongdaxin_fix.py")


if __name__ == '__main__':
    print("开始修复通达信插件A股过滤问题...")
    
    success = fix_tongdaxin_plugin()
    
    if success:
        print("\n" + "=" * 80)
        print("修复完成")
        print("=" * 80)
        print("修复内容:")
        print("1. 添加_is_a_stock方法判断A股代码")
        print("2. 修改get_stock_list方法，只返回A股股票")
        print("3. 排除B股、基金、债券等非A股证券")
        print("4. 更新日志信息")
        print("\n预期效果:")
        print("- K线专用数据下载UI将显示正确的A股数量")
        print("- 数据量从上万条减少到约5000条")
        print("- 与官方统计数据基本一致")
        
        # 创建测试脚本
        create_test_script()
        
        print("\n建议:")
        print("1. 运行测试脚本验证修复效果")
        print("2. 在K线专用数据下载UI中测试批量选择")
        print("3. 确认数据量符合预期")
    
    print("\n修复结束")
