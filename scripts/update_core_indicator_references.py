#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
核心逻辑组件指标引用更新脚本
用于将核心逻辑组件中对旧指标系统的引用更新为新指标系统
"""

import os
import sys
import re
import logging
from typing import List, Dict, Tuple, Any, Optional

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_core_references')

# 需要检查的核心逻辑组件目录
CORE_DIRS = [
    os.path.join(parent_dir, 'core'),
    os.path.join(parent_dir, 'analysis'),
    os.path.join(parent_dir, 'signals')
]

# 特别需要检查的文件
SPECIFIC_FILES = [
    os.path.join(parent_dir, 'core', 'stock_screener.py'),
    os.path.join(parent_dir, 'core', 'signal', 'enhanced.py'),
    os.path.join(parent_dir, 'analysis', 'enhanced_stock_analyzer.py')
]

# 旧的导入语句模式
OLD_IMPORT_PATTERNS = [
    r'from\s+indicators_algo\s+import\s+([^;]+)',
    r'from\s+features\.basic_indicators\s+import\s+([^;]+)',
    r'from\s+features\.advanced_indicators\s+import\s+([^;]+)',
    r'import\s+indicators_algo',
    r'import\s+features\.basic_indicators',
    r'import\s+features\.advanced_indicators'
]

# 旧的函数调用模式
OLD_FUNCTION_PATTERNS = [
    r'calc_talib_indicator\s*\(',
    r'calc_ma\s*\(',
    r'calc_macd\s*\(',
    r'calc_rsi\s*\(',
    r'calc_kdj\s*\(',
    r'calc_boll\s*\(',
    r'calc_atr\s*\(',
    r'calc_obv\s*\(',
    r'calc_cci\s*\(',
    r'calculate_basic_indicators\s*\(',
    r'calculate_advanced_indicators\s*\(',
    r'create_pattern_recognition_features\s*\('
]

# 新的导入语句
NEW_IMPORTS = [
    'from core.indicator_service import calculate_indicator, get_indicator_metadata, get_all_indicators_metadata',
    'from core.indicator_adapter import calc_talib_indicator, calc_ma, calc_macd, calc_rsi, calc_kdj, calc_boll, calc_atr, calc_obv, calc_cci'
]

# 函数调用替换映射
FUNCTION_REPLACEMENTS = {
    r'calc_talib_indicator\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([^,]+)\s*(?:,\s*({[^}]+}))?\s*\)':
        r'calculate_indicator("\1", \2, \3)',

    r'calculate_basic_indicators\(\s*([^)]+)\s*\)':
        r'  # 替换为多个calculate_indicator调用\n    # 原始调用: # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    # TODO: 需要根据实际需求拆分为多个calculate_indicator调用',
    calculate_basic_indicators(\1)\n

    r'calculate_advanced_indicators\(\s*([^)]+)\s*\)':
        r'  # 替换为多个calculate_indicator调用\n    # 原始调用: # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    # TODO: 需要根据实际需求拆分为多个calculate_indicator调用',
    calculate_advanced_indicators(\1)\n

    r'create_pattern_recognition_features\(\s*([^)]+)\s*\)':
        r'  # 替换为pattern指标的calculate_indicator调用\n    # 原始调用: # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    # TODO: 需要更新为新指标系统的调用
    create_pattern_recognition_features(\1)\n    # TODO: 需要根据实际需求使用pattern类指标'
}


def find_py_files(directories: List[str], specific_files: List[str] = None) -> List[str]:
    """
    在指定目录中查找所有Python文件，并添加特定文件

    参数:
        directories: 要搜索的目录列表
        specific_files: 特定要检查的文件列表

    返回:
        List[str]: Python文件路径列表
    """
    py_files = []

    # 添加特定文件
    if specific_files:
        for file_path in specific_files:
            if os.path.exists(file_path) and file_path not in py_files:
                py_files.append(file_path)

    # 搜索目录
    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            continue

        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if file_path not in py_files:
                        py_files.append(file_path)

    logger.info(f"找到 {len(py_files)} 个Python文件")
    return py_files


def check_file_for_old_references(file_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    检查文件中是否包含对旧指标系统的引用

    参数:
        file_path: 文件路径

    返回:
        Tuple[bool, List[str], List[str]]: 
            - 是否包含旧引用
            - 匹配的旧导入语句列表
            - 匹配的旧函数调用列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查旧的导入语句
    old_imports = []
    for pattern in OLD_IMPORT_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            old_imports.append(pattern)

    # 检查旧的函数调用
    old_functions = []
    for pattern in OLD_FUNCTION_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            old_functions.append(pattern)

    has_old_references = bool(old_imports or old_functions)
    return has_old_references, old_imports, old_functions


def update_file(file_path: str, dry_run: bool = True) -> bool:
    """
    更新文件中的指标引用

    参数:
        file_path: 文件路径
        dry_run: 是否只是模拟运行，不实际修改文件

    返回:
        bool: 是否进行了更新
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否包含旧引用
    has_old_references, old_imports, old_functions = check_file_for_old_references(
        file_path)
    if not has_old_references:
        logger.info(f"文件没有旧引用，跳过: {file_path}")
        return False

    # 备份原始内容
    backup_path = f"{file_path}.bak"
    if not dry_run:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"已创建备份: {backup_path}")

    # 更新导入语句
    updated_content = content
    for pattern in OLD_IMPORT_PATTERNS:
        updated_content = re.sub(pattern, '# 已移除旧导入', updated_content)

    # 在文件开头添加新的导入语句
    import_section_end = updated_content.find('\n\n')
    if import_section_end == -1:
        import_section_end = updated_content.find('\n')

    if import_section_end != -1:
        updated_content = updated_content[:import_section_end] + '\n' + \
            '\n'.join(NEW_IMPORTS) + updated_content[import_section_end:]
    else:
        updated_content = '\n'.join(NEW_IMPORTS) + '\n\n' + updated_content

    # 更新函数调用
    for old_pattern, new_pattern in FUNCTION_REPLACEMENTS.items():
        updated_content = re.sub(old_pattern, new_pattern, updated_content)

    # 对于其他未明确替换的旧函数调用，添加TODO注释
    for pattern in OLD_FUNCTION_PATTERNS:
        if pattern not in ''.join(FUNCTION_REPLACEMENTS.keys()):
            updated_content = re.sub(
                pattern,
                r'# TODO: 需要更新为新指标系统的调用\n    ' + r'\g<0>',
                updated_content
            )

    # 保存更新后的内容
    if not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        logger.info(f"已更新文件: {file_path}")
    else:
        logger.info(f"模拟更新文件: {file_path}")
        # 打印差异
        import difflib
        diff = difflib.unified_diff(
            content.splitlines(keepends=True),
            updated_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}"
        )
        logger.info(''.join(diff))

    return True


def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='更新核心逻辑组件中的指标引用')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际修改文件')
    parser.add_argument('--dirs', nargs='+', help='要检查的目录列表，默认为CORE_DIRS')
    parser.add_argument('--files', nargs='+',
                        help='要检查的特定文件列表，默认为SPECIFIC_FILES')
    args = parser.parse_args()

    # 获取要检查的目录和文件
    directories = args.dirs if args.dirs else CORE_DIRS
    specific_files = args.files if args.files else SPECIFIC_FILES
    logger.info(f"将检查以下目录: {directories}")
    logger.info(f"将特别检查以下文件: {specific_files}")

    # 查找Python文件
    py_files = find_py_files(directories, specific_files)

    # 检查并更新文件
    updated_files = 0
    for file_path in py_files:
        has_old_references, old_imports, old_functions = check_file_for_old_references(
            file_path)
        if has_old_references:
            logger.info(f"文件包含旧引用: {file_path}")
            logger.info(f"  旧导入: {old_imports}")
            logger.info(f"  旧函数调用: {old_functions}")

            updated = update_file(file_path, dry_run=args.dry_run)
            if updated:
                updated_files += 1

    # 打印统计信息
    logger.info(f"共检查了 {len(py_files)} 个文件，其中 {updated_files} 个文件需要更新")
    if args.dry_run:
        logger.info("这是一次模拟运行，没有实际修改文件")
    else:
        logger.info("文件已更新，原始文件已备份为 .bak 文件")


if __name__ == '__main__':
    main()
