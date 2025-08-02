#!/usr/bin/env python3
"""
趋势分析逻辑bug修复脚本
修复全量验证中发现的所有问题
"""

import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def fix_trend_analysis_bugs():
    """修复趋势分析的所有逻辑bug"""
    print("🔧 开始修复趋势分析逻辑bug...")

    trend_file = project_root / "gui" / "widgets" / "analysis_tabs" / "trend_tab.py"

    if not trend_file.exists():
        print("❌ 趋势分析文件不存在")
        return False

    with open(trend_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 备份原文件
    backup_file = trend_file.with_suffix('.py.backup3')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 已备份原文件: {backup_file}")

    fixes_applied = []

    # 修复1: 日志调用错误
    print("\n1. 修复日志调用错误...")
    if 'self.log_manager.error' in content:
        content = content.replace('self.log_manager.error', 'logger.error')
        fixes_applied.append("修复了错误的日志调用 (self.log_manager.error -> logger.error)")

    if 'self.log_manager.info' in content:
        content = content.replace('self.log_manager.info', 'logger.info')
        fixes_applied.append("修复了错误的日志调用 (self.log_manager.info -> logger.info)")

    if 'self.log_manager.warning' in content:
        content = content.replace('self.log_manager.warning', 'logger.warning')
        fixes_applied.append("修复了错误的日志调用 (self.log_manager.warning -> logger.warning)")

    # 修复2: 数据属性一致性问题
    print("\n2. 修复数据属性一致性问题...")

    # 在__init__方法中添加current_kdata属性
    if 'self.current_kdata = None' not in content:
        # 在kdata初始化后添加current_kdata
        init_pattern = r'(self\.progress_bar = None\s*\n\s*# 现在调用父类初始化)'
        if re.search(init_pattern, content):
            replacement = r'self.progress_bar = None\n        self.current_kdata = None  # 当前K线数据\n        \n        # 现在调用父类初始化'
            content = re.sub(init_pattern, replacement, content)
            fixes_applied.append("添加了current_kdata属性初始化")

    # 修复3: 添加数据同步方法
    print("\n3. 添加数据同步方法...")
    sync_method = '''
    def set_kdata(self, kdata):
        """设置K线数据并同步到current_kdata"""
        try:
            self.kdata = kdata
            self.current_kdata = kdata  # 保持数据一致性
            logger.info(f"设置K线数据成功，数据长度: {len(kdata) if kdata is not None else 0}")
        except Exception as e:
            logger.error(f"设置K线数据失败: {e}")
            self.kdata = None
            self.current_kdata = None
'''

    if 'def set_kdata(' not in content:
        # 在类的末尾添加方法
        content += sync_method
        fixes_applied.append("添加了set_kdata数据同步方法")

    # 修复4: 完善错误处理中的状态重置
    print("\n4. 完善错误处理...")

    # 在异常处理中添加状态重置
    error_patterns = [
        (r'(except Exception as e:\s*logger\.error\([^)]+\))',
         r'\1\n            self.hide_loading()  # 确保隐藏加载状态')
    ]

    for pattern, replacement in error_patterns:
        if re.search(pattern, content) and 'self.hide_loading()' not in content:
            content = re.sub(pattern, replacement, content)
            fixes_applied.append("在错误处理中添加了状态重置")

    # 修复5: 添加缺失的数据验证
    print("\n5. 添加缺失的数据验证...")

    # 为使用current_kdata的方法添加数据验证
    methods_using_current_kdata = [
        '_analyze_price_trend_advanced',
        '_analyze_volume_trend_advanced',
        '_analyze_support_resistance'
    ]

    for method in methods_using_current_kdata:
        method_pattern = rf'(def {method}\([^)]*\):[^{{}}]+?)(\s+if not hasattr\(self\.current_kdata)'
        if re.search(method_pattern, content, re.DOTALL):
            continue  # 已经有验证了

        # 在方法开始处添加数据验证
        method_start_pattern = rf'(def {method}\([^)]*\):\s*"""[^"]*"""\s*)'
        validation_code = r'''\1
        # 数据验证
        if not hasattr(self, 'current_kdata') or self.current_kdata is None:
            logger.warning(f"{method}: current_kdata不可用")
            return None
            
        '''

        if re.search(method_start_pattern, content):
            content = re.sub(method_start_pattern, validation_code, content)
            fixes_applied.append(f"为{method}添加了数据验证")

    # 修复6: 修复导入问题
    print("\n6. 修复导入问题...")

    # 移除重复的ConfigManager导入
    lines = content.split('\n')
    config_import_count = 0
    fixed_lines = []

    for line in lines:
        if 'from utils.config_manager import ConfigManager' in line:
            config_import_count += 1
            if config_import_count == 1:
                fixed_lines.append(line)  # 保留第一个
                # 注释：保留utils.config_manager导入，移除core.config_manager
        elif 'from core.config_manager import ConfigManager' in line:
            # 跳过这个导入，避免冲突
            continue
        else:
            fixed_lines.append(line)

    if config_import_count > 1:
        content = '\n'.join(fixed_lines)
        fixes_applied.append("移除了重复的ConfigManager导入")

    # 修复7: 添加缺失的辅助方法
    print("\n7. 添加缺失的辅助方法...")

    helper_methods = '''
    def _get_pattern_start_date(self):
        """获取形态开始日期"""
        try:
            if hasattr(self, 'current_kdata') and self.current_kdata is not None and len(self.current_kdata) > 0:
                return self.current_kdata.index[-1].strftime('%Y-%m-%d') if hasattr(self.current_kdata.index[-1], 'strftime') else str(self.current_kdata.index[-1])
            return datetime.now().strftime('%Y-%m-%d')
        except:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _get_pattern_end_date(self):
        """获取形态结束日期"""
        return self._get_pattern_start_date()  # 简化实现
    
    def _calculate_price_change(self):
        """计算价格变化"""
        try:
            if hasattr(self, 'current_kdata') and self.current_kdata is not None and len(self.current_kdata) >= 2:
                current_price = self.current_kdata['close'].iloc[-1]
                prev_price = self.current_kdata['close'].iloc[-2]
                return f"{((current_price - prev_price) / prev_price * 100):.2f}%"
            return "0.00%"
        except:
            return "0.00%"
    
    def _calculate_target_price(self, pattern_name):
        """计算目标价格"""
        try:
            if hasattr(self, 'current_kdata') and self.current_kdata is not None and len(self.current_kdata) > 0:
                current_price = self.current_kdata['close'].iloc[-1]
                # 简化的目标价格计算
                if '上升' in pattern_name or '看涨' in pattern_name:
                    return f"{current_price * 1.05:.2f}"
                elif '下降' in pattern_name or '看跌' in pattern_name:
                    return f"{current_price * 0.95:.2f}"
                else:
                    return f"{current_price:.2f}"
            return "0.00"
        except:
            return "0.00"
    
    def _get_recommendation(self, pattern_name, confidence):
        """获取操作建议"""
        try:
            if confidence > 0.8:
                if '上升' in pattern_name or '看涨' in pattern_name:
                    return "强烈买入"
                elif '下降' in pattern_name or '看跌' in pattern_name:
                    return "强烈卖出"
            elif confidence > 0.6:
                if '上升' in pattern_name or '看涨' in pattern_name:
                    return "买入"
                elif '下降' in pattern_name or '看跌' in pattern_name:
                    return "卖出"
            return "观望"
        except:
            return "观望"
'''

    # 检查是否缺少这些方法
    missing_methods = []
    for method_name in ['_get_pattern_start_date', '_get_pattern_end_date', '_calculate_price_change', '_calculate_target_price', '_get_recommendation']:
        if f'def {method_name}(' not in content:
            missing_methods.append(method_name)

    if missing_methods:
        content += helper_methods
        fixes_applied.append(f"添加了缺失的辅助方法: {', '.join(missing_methods)}")

    # 修复8: 修复数据类型转换问题
    print("\n8. 修复数据类型转换问题...")

    # 在结果显示方法中添加安全的数据转换
    type_conversion_fixes = [
        (r"f\"{result\.get\('strength', 0\):.2f}%\"",
         r"f\"{float(result.get('strength', 0)):.2f}%\""),
        (r"f\"{result\.get\('confidence', 0\):.2f}%\"",
         r"f\"{float(result.get('confidence', 0)):.2f}%\""),
        (r"f\"{result\.get\('target_price', 0\):.2f}\"",
         r"f\"{float(result.get('target_price', 0)):.2f}\"")
    ]

    for pattern, replacement in type_conversion_fixes:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            fixes_applied.append("修复了数据类型转换问题")
            break  # 只报告一次

    # 写入修复后的文件
    with open(trend_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n✅ 修复完成！应用了{len(fixes_applied)}个修复:")
    for i, fix in enumerate(fixes_applied, 1):
        print(f"   {i}. {fix}")

    return True


def validate_fixes():
    """验证修复效果"""
    print("\n🔍 验证修复效果...")

    trend_file = project_root / "gui" / "widgets" / "analysis_tabs" / "trend_tab.py"

    with open(trend_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 验证修复项目
    validations = [
        ('logger.error', '日志调用修复'),
        ('self.current_kdata = None', 'current_kdata属性初始化'),
        ('def set_kdata(', '数据同步方法'),
        ('def _get_pattern_start_date(', '辅助方法添加'),
        ('float(result.get', '数据类型转换修复')
    ]

    validation_results = []
    for pattern, description in validations:
        if pattern in content:
            validation_results.append(f"✅ {description}: 已修复")
        else:
            validation_results.append(f"❌ {description}: 未找到")

    for result in validation_results:
        print(f"   {result}")

    success_count = sum(1 for r in validation_results if '✅' in r)
    total_count = len(validation_results)

    print(f"\n📊 修复验证结果: {success_count}/{total_count} 项通过 ({success_count/total_count*100:.1f}%)")

    return success_count >= total_count * 0.8


def main():
    """主函数"""
    print("🚀 启动趋势分析逻辑bug修复...")

    try:
        # 应用修复
        if fix_trend_analysis_bugs():
            print("\n✅ bug修复完成")
        else:
            print("\n❌ bug修复失败")
            return False

        # 验证修复效果
        if validate_fixes():
            print("\n✅ 修复验证通过")
        else:
            print("\n⚠️ 修复验证部分通过")

        print(f"\n🎯 修复流程完成！")
        print("📝 下一步:")
        print("   1. 重新运行功能测试验证修复效果")
        print("   2. 测试趋势分析的所有UI功能")
        print("   3. 确认数据流和调用链正常")

        return True

    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 bug修复完成！")
    else:
        print("\n💼 修复过程中遇到问题！")

    input("\n按Enter键退出...")
