#!/usr/bin/env python3
"""
调试算法代码脚本
"""

import sqlite3


def debug_algorithm():
    """调试算法代码"""
    conn = sqlite3.connect('db/hikyuu_system.db')
    cursor = conn.cursor()

    cursor.execute(
        'SELECT algorithm_code FROM pattern_types WHERE english_name = "hammer"')
    code = cursor.fetchone()[0]

    print("算法代码前100个字符:")
    print(repr(code[:100]))

    print("\n算法代码前10行:")
    lines = code.split('\n')[:10]
    for i, line in enumerate(lines, 1):
        print(f"{i:2d}: {repr(line)}")

    print(f"\n算法代码总长度: {len(code)}")

    # 检查是否有八进制数字
    import re
    octal_pattern = r'\b0[0-7]+\b'
    matches = re.findall(octal_pattern, code)
    if matches:
        print(f"\n发现可能的八进制数字: {matches}")
    else:
        print("\n未发现八进制数字")

    # 尝试编译代码
    try:
        compile(code, '<hammer>', 'exec')
        print("✅ 代码编译成功")
    except SyntaxError as e:
        print(f"❌ 代码编译失败: {e}")
        print(f"错误位置: 第{e.lineno}行, 第{e.offset}列")
        if e.lineno and e.lineno <= len(lines):
            error_line = lines[e.lineno - 1]
            print(f"错误行: {repr(error_line)}")

    conn.close()


if __name__ == "__main__":
    debug_algorithm()
