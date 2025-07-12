#!/usr/bin/env python3
"""
检查数据库中的算法代码
"""

import sqlite3


def check_hammer_code():
    conn = sqlite3.connect('db/hikyuu_system.db')
    cursor = conn.cursor()

    cursor.execute(
        'SELECT algorithm_code FROM pattern_types WHERE english_name = "hammer"')
    code = cursor.fetchone()[0]

    print("算法代码前5行:")
    lines = code.split('\n')[:5]
    for i, line in enumerate(lines, 1):
        print(f"{i}: {repr(line)}")

    print(f"\n算法代码总长度: {len(code)}")

    # 尝试编译
    try:
        compile(code, '<hammer>', 'exec')
        print("✅ 代码编译成功")
    except SyntaxError as e:
        print(f"❌ 代码编译失败: {e}")
        print(f"错误位置: 第{e.lineno}行")
        if e.text:
            print(f"错误文本: {repr(e.text)}")

    conn.close()


if __name__ == "__main__":
    check_hammer_code()
