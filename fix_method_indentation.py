#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复pattern_tab_pro.py中方法缩进错误
"""

import os


def fix_indentation():
    """修复文件中的方法缩进错误"""
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 {file_path}")
        return False

    print(f"开始修复文件: {file_path}")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定位错误的方法
    error_method = "def on_analysis_error(self, error_message):"
    error_pos = content.find(error_method)

    if error_pos == -1:
        print("错误: 未找到目标方法")
        return False

    # 获取方法前的缩进情况
    prev_newline = content.rfind('\n', 0, error_pos)
    if prev_newline == -1:
        prev_newline = 0

    # 检查缩进
    indentation = ""
    for i in range(prev_newline + 1, error_pos):
        if content[i].isspace():
            indentation += content[i]
        else:
            break

    # 获取方法的实际内容
    method_start = error_pos

    # 找下一个方法的开始
    next_method = content.find("\n    def ", method_start + 1)
    if next_method == -1:
        next_method = len(content)

    method_content = content[method_start:next_method]

    # 修复方法缩进
    correct_indent = "    "  # 类方法应该缩进4个空格
    if indentation != correct_indent:
        # 获取整个方法的内容，按行分割
        method_lines = method_content.split('\n')

        # 修复第一行的缩进
        fixed_first_line = correct_indent + method_lines[0].lstrip()

        # 修复后续行的缩进
        fixed_lines = [fixed_first_line]
        for line in method_lines[1:]:
            if line.strip():  # 非空行
                # 计算当前行的缩进
                current_indent = ""
                for char in line:
                    if char.isspace():
                        current_indent += char
                    else:
                        break

                # 如果当前行的缩进是方法体内的缩进，加上8个空格
                if len(current_indent) > len(indentation):
                    extra_indent = len(current_indent) - len(indentation)
                    new_indent = correct_indent + " " * extra_indent
                    fixed_lines.append(new_indent + line.lstrip())
                else:
                    # 其他情况，可能是空行或者下一个方法
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)  # 保留空行

        # 组合修复后的方法
        fixed_method = '\n'.join(fixed_lines)

        # 替换原始内容
        new_content = content[:method_start] + fixed_method + content[method_start + len(method_content):]

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"成功修复方法 {error_method} 的缩进")
        return True
    else:
        print(f"方法 {error_method} 的缩进已经正确")
        return True


def manual_fix():
    """手动修复文件"""
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 {file_path}")
        return False

    # 读取文件内容为行列表
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 查找错误行
    error_line_idx = -1
    for i, line in enumerate(lines):
        if "def on_analysis_error(self, error_message):" in line and not line.startswith("    def "):
            error_line_idx = i
            break

    if error_line_idx == -1:
        print("未找到错误行")
        return False

    print(f"找到错误行 {error_line_idx + 1}: {lines[error_line_idx].strip()}")

    # 修复缩进
    fixed_lines = lines.copy()
    fixed_lines[error_line_idx] = "    " + lines[error_line_idx].lstrip()

    # 检查后续行是否需要修复
    i = error_line_idx + 1
    while i < len(lines) and not lines[i].lstrip().startswith("def "):
        if lines[i].strip():  # 非空行
            # 检查当前缩进
            current_indent = ""
            for char in lines[i]:
                if char.isspace():
                    current_indent += char
                else:
                    break

            # 如果缩进不是方法体内的标准缩进（8个空格），进行修复
            if len(current_indent) != 8 and lines[i].lstrip():
                fixed_lines[i] = "        " + lines[i].lstrip()
        i += 1

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"成功修复了 {file_path} 中的缩进错误")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("开始修复方法缩进错误...")
    print("=" * 60)

    # 尝试使用函数修复
    if not fix_indentation():
        # 如果函数修复失败，尝试手动修复
        if manual_fix():
            print("=" * 60)
            print("✅ 手动修复成功！请重启应用验证效果")
            print("=" * 60)
        else:
            print("=" * 60)
            print("❌ 修复失败！")
            print("=" * 60)
    else:
        print("=" * 60)
        print("✅ 修复成功！请重启应用验证效果")
        print("=" * 60)
