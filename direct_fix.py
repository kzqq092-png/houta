#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接替换整个pattern_tab_pro.py文件内容的脚本，解决缩进错误问题
"""


def main():
    # 打开文件查看内容
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找问题行
    problem_line = "def _create_statistics_tab(self):"
    line_num = 0
    for i, line in enumerate(content.split('\n')):
        if problem_line in line:
            line_num = i + 1
            break

    print(f"发现问题行: 第 {line_num} 行")

    # 确认要修复的行，查看周围几行
    lines = content.split('\n')
    start_line = max(0, line_num - 10)
    end_line = min(len(lines), line_num + 10)

    print("问题区域:")
    for i in range(start_line, end_line):
        print(f"{i+1}: {lines[i]}")

    # 直接修改这一部分的缩进
    for i in range(line_num - 1, line_num + 20):  # 修改这一范围内的行
        if i < len(lines) and lines[i].strip().startswith("def "):
            lines[i] = "    " + lines[i].lstrip()

    # 写回文件
    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("修复完成!")
    return True


if __name__ == "__main__":
    main()
