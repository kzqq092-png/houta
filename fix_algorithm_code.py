#!/usr/bin/env python3
"""
修复数据库中的算法代码问题
"""

import sqlite3
import re


def fix_algorithm_codes():
    """修复数据库中的算法代码"""
    conn = sqlite3.connect('db/hikyuu_system.db')
    cursor = conn.cursor()

    try:
        # 获取所有包含算法代码的形态
        cursor.execute(
            'SELECT id, english_name, algorithm_code FROM pattern_types WHERE algorithm_code IS NOT NULL AND algorithm_code != ""')
        patterns = cursor.fetchall()

        print(f"找到 {len(patterns)} 个包含算法代码的形态")

        for pattern_id, english_name, algorithm_code in patterns:
            print(f"\n检查形态: {english_name}")

            # 检查代码前100个字符
            print(f"原始代码前100个字符: {repr(algorithm_code[:100])}")

            # 清理代码
            cleaned_code = clean_algorithm_code(algorithm_code)

            if cleaned_code != algorithm_code:
                print(f"代码需要清理")
                print(f"清理后前100个字符: {repr(cleaned_code[:100])}")

                # 更新数据库
                cursor.execute('UPDATE pattern_types SET algorithm_code = ? WHERE id = ?',
                               (cleaned_code, pattern_id))
                print(f"✅ 已更新 {english_name} 的算法代码")
            else:
                print(f"✅ {english_name} 的算法代码无需修改")

        conn.commit()
        print(f"\n🎉 算法代码修复完成！")

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        conn.rollback()
    finally:
        conn.close()


def clean_algorithm_code(code: str) -> str:
    """清理算法代码"""
    if not code:
        return code

    # 移除开头的时间戳或其他非代码内容
    lines = code.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped_line = line.strip()

        # 跳过时间戳行（格式如：2025-06-10 15:57:22）
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$', stripped_line):
            print(f"跳过时间戳行: {stripped_line}")
            continue

        # 跳过空行（但保留代码中的空行）
        if not stripped_line and not cleaned_lines:
            continue

        cleaned_lines.append(line)

    # 重新组合代码
    cleaned_code = '\n'.join(cleaned_lines)

    # 移除开头和结尾的空白
    cleaned_code = cleaned_code.strip()

    return cleaned_code


def test_cleaned_code():
    """测试清理后的代码"""
    conn = sqlite3.connect('db/hikyuu_system.db')
    cursor = conn.cursor()

    try:
        cursor.execute(
            'SELECT english_name, algorithm_code FROM pattern_types WHERE english_name = "hammer"')
        result = cursor.fetchone()

        if result:
            english_name, algorithm_code = result
            print(f"\n测试 {english_name} 的算法代码:")
            print(f"代码长度: {len(algorithm_code)}")
            print(f"前3行:")

            lines = algorithm_code.split('\n')[:3]
            for i, line in enumerate(lines, 1):
                print(f"  {i}: {repr(line)}")

            # 尝试编译
            try:
                compile(algorithm_code, f'<{english_name}>', 'exec')
                print("✅ 代码编译成功")
            except SyntaxError as e:
                print(f"❌ 代码编译失败: {e}")
                print(f"错误位置: 第{e.lineno}行")
                if e.text:
                    print(f"错误文本: {repr(e.text)}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("算法代码修复工具")
    print("=" * 50)

    fix_algorithm_codes()
    test_cleaned_code()
