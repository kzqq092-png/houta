#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语法错误检查工具
"""

import ast
import traceback


def check_syntax():
    try:
        with open('gui/widgets/enhanced_data_import_widget.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 分段检查
        lines = content.split('\n')

        # 检查到1750行左右
        for i in range(1700, min(1800, len(lines)), 10):
            try:
                partial_content = '\n'.join(lines[:i])
                ast.parse(partial_content)
                print(f"✅ 第 {i} 行之前语法正常")
            except SyntaxError as e:
                print(f"❌ 第 {i} 行附近语法错误:")
                print(f"   错误行: {e.lineno}")
                print(f"   错误内容: {e.text}")
                print(f"   错误信息: {e.msg}")
                return e.lineno

        return None

    except Exception as e:
        print(f"检查失败: {e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("开始语法检查...")
    error_line = check_syntax()
    if error_line:
        print(f"\n发现语法错误在第 {error_line} 行")
    else:
        print("\n未发现语法错误")
