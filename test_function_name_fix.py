#!/usr/bin/env python3
"""
测试函数名冲突修复
验证get_talib_category函数名冲突是否已解决
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_function_imports():
    """测试函数导入"""
    print("=" * 60)
    print("测试函数导入")
    print("=" * 60)

    try:
        # 测试从indicator_service导入无参数版本
        from core.indicator_service import get_talib_category
        print("✓ 从indicator_service导入get_talib_category成功")

        # 测试调用无参数版本
        result = get_talib_category()
        print(f"✓ 无参数版本调用成功，返回类型: {type(result)}")

    except Exception as e:
        print(f"❌ indicator_service导入失败: {e}")
        return False

    try:
        # 测试从indicator_adapter导入有参数版本
        from core.indicator_adapter import get_indicator_category_by_name
        print("✓ 从indicator_adapter导入get_indicator_category_by_name成功")

        # 测试调用有参数版本
        result = get_indicator_category_by_name('MA')
        print(f"✓ 有参数版本调用成功，返回值: {result}")

    except Exception as e:
        print(f"❌ indicator_adapter导入失败: {e}")
        return False

    return True


def test_technical_tab_imports():
    """测试技术分析标签页导入"""
    print("\n" + "=" * 60)
    print("测试技术分析标签页导入")
    print("=" * 60)

    try:
        # 测试technical_tab的导入
        from gui.widgets.analysis_tabs.technical_tab import TechnicalAnalysisTab
        print("✓ TechnicalAnalysisTab导入成功")

        # 测试创建实例（模拟）
        print("✓ 导入测试通过，无函数名冲突")

    except Exception as e:
        print(f"❌ TechnicalAnalysisTab导入失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

    return True


def test_function_calls():
    """测试函数调用"""
    print("\n" + "=" * 60)
    print("测试函数调用")
    print("=" * 60)

    try:
        from core.indicator_adapter import (
            get_talib_indicator_list,
            get_talib_chinese_name,
            get_indicator_category_by_name
        )

        # 获取指标列表
        indicators = get_talib_indicator_list()
        print(f"✓ 获取指标列表成功，共{len(indicators)}个指标")

        if indicators:
            test_indicator = indicators[0]

            # 测试中文名称获取
            chinese_name = get_talib_chinese_name(test_indicator)
            print(f"✓ 指标{test_indicator}中文名称: {chinese_name}")

            # 测试分类获取
            category = get_indicator_category_by_name(test_indicator)
            print(f"✓ 指标{test_indicator}分类: {category}")

        return True

    except Exception as e:
        print(f"❌ 函数调用测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    print("函数名冲突修复验证测试")

    success = True

    # 测试导入
    if not test_function_imports():
        success = False

    # 测试技术分析标签页导入
    if not test_technical_tab_imports():
        success = False

    # 测试函数调用
    if not test_function_calls():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！函数名冲突已修复")
    else:
        print("❌ 部分测试失败，需要进一步修复")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
