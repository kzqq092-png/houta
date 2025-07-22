#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复pattern_tab_pro.py中的缩进错误
"""

import os
import sys
import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_indentation")


def fix_file_indentation(file_path):
    """修复文件中的缩进问题"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False

    logger.info(f"开始修复文件: {file_path}")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 确保文件是缩进一致的
    fixed_lines = []
    in_multiline_string = False
    string_start_pattern = None

    # 前一个非空行的缩进
    prev_indent = ""

    for i, line in enumerate(lines):
        # 处理多行字符串
        if in_multiline_string:
            fixed_lines.append(line)

            # 检查多行字符串是否结束
            if string_start_pattern in line and line.strip().endswith(string_start_pattern):
                in_multiline_string = False
                string_start_pattern = None

            continue

        # 检查是否开始多行字符串
        if '"""' in line and line.count('"""') % 2 == 1:
            in_multiline_string = True
            string_start_pattern = '"""'
            fixed_lines.append(line)
            continue

        if "'''" in line and line.count("'''") % 2 == 1:
            in_multiline_string = True
            string_start_pattern = "'''"
            fixed_lines.append(line)
            continue

        # 处理普通行
        if line.strip() == "" or line.strip().startswith("#"):
            # 保持空行和注释行不变
            fixed_lines.append(line)
            continue

        # 检查行是否以缩进开头
        indent_match = re.match(r'^(\s+)', line)
        if indent_match:
            current_indent = indent_match.group(1)

            # 检查是否是类或函数定义行
            is_def_line = bool(re.match(r'\s*def\s+\w+\(', line))
            is_class_line = bool(re.match(r'\s*class\s+\w+', line))

            # 修复常见的缩进问题
            if is_def_line or is_class_line:
                # 函数和类定义应该是4空格的倍数
                if len(current_indent) % 4 != 0:
                    # 修正缩进为最接近的4空格的倍数
                    correct_indent = ' ' * (4 * (len(current_indent) // 4))
                    line = correct_indent + line.lstrip()
                    logger.info(f"修复第 {i+1} 行的缩进: {repr(current_indent)} -> {repr(correct_indent)}")

        fixed_lines.append(line)

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    logger.info(f"完成文件修复: {file_path}")
    return True


def main():
    """主函数"""
    # 指定要修复的文件
    pattern_tab_pro_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"

    print("="*50)
    print("开始修复文件缩进问题...")
    print("="*50)

    success = fix_file_indentation(pattern_tab_pro_path)

    if success:
        print("="*50)
        print("✅ 修复完成! 请重启应用验证效果")
        print("="*50)
        return 0
    else:
        print("="*50)
        print("❌ 修复失败，请查看日志获取更多信息")
        print("="*50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
