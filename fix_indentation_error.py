#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复pattern_tab_pro.py中第721行附近的缩进错误
"""

import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_indentation")


def fix_specific_indentation_error():
    """修复pattern_tab_pro.py中第721行附近的缩进错误"""
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False

    logger.info(f"开始修复文件: {file_path}")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到_create_statistics_tab方法的开始位置
    target_line = "def _create_statistics_tab(self):"
    line_pos = content.find(target_line)

    if line_pos == -1:
        logger.error(f"未找到目标行: {target_line}")
        return False

    # 获取行号
    line_number = content[:line_pos].count('\n') + 1
    logger.info(f"找到目标行，行号: {line_number}")

    # 读取文件为行列表
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到出现缩进错误的行
    error_line_idx = line_number - 1  # 转为0索引

    if error_line_idx >= len(lines):
        logger.error(f"行号超出范围: {line_number}, 最大行号: {len(lines)}")
        return False

    # 检查缩进并修复
    fixed_lines = lines.copy()

    # 找到_create_backtest_tab方法的开始位置（用于确认正确的缩进级别）
    backtest_line = "def _create_backtest_tab(self):"
    backtest_line_idx = -1

    for i, line in enumerate(lines):
        if backtest_line in line:
            backtest_line_idx = i
            break

    if backtest_line_idx == -1:
        logger.error(f"未找到参考行: {backtest_line}")
        return False

    # 获取正确的缩进
    correct_indent = ""
    backtest_line_content = lines[backtest_line_idx]
    for char in backtest_line_content:
        if char.isspace():
            correct_indent += char
        else:
            break

    logger.info(f"从参考行获取的正确缩进: '{correct_indent}', 长度: {len(correct_indent)}")

    # 修复目标行的缩进
    error_line_content = lines[error_line_idx]
    current_indent = ""
    for char in error_line_content:
        if char.isspace():
            current_indent += char
        else:
            break

    logger.info(f"当前行缩进: '{current_indent}', 长度: {len(current_indent)}")

    if current_indent != correct_indent:
        fixed_lines[error_line_idx] = correct_indent + error_line_content.lstrip()
        logger.info(f"修复第 {line_number} 行的缩进")

    # 检查并修复接下来的几行缩进
    start_idx = error_line_idx + 1
    expected_indent = correct_indent + "    "  # 函数内部缩进增加4个空格

    # 修复函数体内部的缩进
    i = start_idx
    while i < len(fixed_lines):
        line = fixed_lines[i]
        if line.strip() == "":
            i += 1
            continue

        # 检查当前行的缩进
        current_indent = ""
        for char in line:
            if char.isspace():
                current_indent += char
            else:
                break

        # 如果遇到下一个函数定义，退出循环
        if line.strip().startswith("def ") and current_indent == correct_indent:
            break

        # 修复函数体内部的缩进
        if current_indent != expected_indent:
            fixed_lines[i] = expected_indent + line.lstrip()
            logger.info(f"修复第 {i+1} 行的缩进")

        i += 1

    # 写入修复后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    logger.info(f"完成文件修复: {file_path}")
    return True


if __name__ == "__main__":
    print("="*50)
    print("开始修复特定的缩进错误...")
    print("="*50)

    if fix_specific_indentation_error():
        print("="*50)
        print("✅ 修复完成！请重启应用验证效果")
        print("="*50)
    else:
        print("="*50)
        print("❌ 修复失败！请查看日志")
        print("="*50)
