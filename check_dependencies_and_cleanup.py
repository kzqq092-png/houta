#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
依赖检查和清理脚本
用于检查旧指标系统的依赖关系，并在确认安全后清理旧代码
"""

import os
import sys
import re
import shutil
import logging
import argparse
from typing import List, Dict, Tuple, Set, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='dependencies_report.txt',
    filemode='w'
)

# 添加控制台处理器
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger('dependencies_check')

# 要检查的旧文件
OLD_FILES = [
    'indicators_algo.py',
    'features/basic_indicators.py',
    'features/advanced_indicators.py',
    'features/feature_selection.py'
]

# 导入模式
IMPORT_PATTERNS = [
    r'from\s+indicators_algo\s+import\s+([^#\n]+)',
    r'from\s+features\.basic_indicators\s+import\s+([^#\n]+)',
    r'from\s+features\.advanced_indicators\s+import\s+([^#\n]+)',
    r'from\s+features\.feature_selection\s+import\s+([^#\n]+)',
    r'import\s+indicators_algo',
    r'import\s+features\.basic_indicators',
    r'import\s+features\.advanced_indicators',
    r'import\s+features\.feature_selection'
]

# 函数调用模式
FUNCTION_PATTERNS = [
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


def find_all_python_files(root_dir: str) -> List[str]:
    """
    查找目录中的所有Python文件

    参数:
        root_dir: 根目录路径

    返回:
        List[str]: Python文件路径列表
    """
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # 跳过.git目录
        if '.git' in dirs:
            dirs.remove('.git')

        # 跳过__pycache__目录
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')

        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def check_file_dependencies(file_path: str, old_files: List[str]) -> Dict[str, List[str]]:
    """
    检查文件的依赖关系

    参数:
        file_path: 文件路径
        old_files: 旧文件列表

    返回:
        Dict[str, List[str]]: 依赖关系字典，键为旧文件路径，值为依赖的行列表
    """
    dependencies = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # 检查导入语句
        for i, line in enumerate(lines):
            for pattern in IMPORT_PATTERNS:
                if re.search(pattern, line):
                    for old_file in old_files:
                        if old_file.replace('/', '.').replace('.py', '') in line:
                            if old_file not in dependencies:
                                dependencies[old_file] = []
                            dependencies[old_file].append(f"{i+1}: {line}")

        # 检查函数调用
        for i, line in enumerate(lines):
            for pattern in FUNCTION_PATTERNS:
                if re.search(pattern, line):
                    for old_file in old_files:
                        # 这里简化处理，假设所有函数调用都依赖于indicators_algo.py
                        if old_file == 'indicators_algo.py' or old_file == 'features/basic_indicators.py' or old_file == 'features/advanced_indicators.py':
                            if old_file not in dependencies:
                                dependencies[old_file] = []
                            dependencies[old_file].append(f"{i+1}: {line}")

    except Exception as e:
        logger.error(f"检查文件 {file_path} 时发生错误: {str(e)}")

    return dependencies


def check_all_dependencies(root_dir: str, old_files: List[str]) -> Dict[str, Dict[str, List[str]]]:
    """
    检查所有文件的依赖关系

    参数:
        root_dir: 根目录路径
        old_files: 旧文件列表

    返回:
        Dict[str, Dict[str, List[str]]]: 依赖关系字典，键为文件路径，值为依赖关系字典
    """
    all_dependencies = {}

    # 查找所有Python文件
    python_files = find_all_python_files(root_dir)
    logger.info(f"找到 {len(python_files)} 个Python文件")

    # 检查每个文件的依赖关系
    for file_path in python_files:
        # 跳过旧文件本身
        if any(file_path.endswith(old_file) for old_file in old_files):
            continue

        dependencies = check_file_dependencies(file_path, old_files)
        if dependencies:
            all_dependencies[file_path] = dependencies

    return all_dependencies


def generate_dependency_report(all_dependencies: Dict[str, Dict[str, List[str]]]) -> None:
    """
    生成依赖报告

    参数:
        all_dependencies: 依赖关系字典
    """
    logger.info("=== 依赖关系报告 ===")

    if not all_dependencies:
        logger.info("未发现依赖关系，可以安全删除旧文件")
        return

    logger.info(f"发现 {len(all_dependencies)} 个文件仍然依赖于旧指标系统")

    for file_path, dependencies in all_dependencies.items():
        logger.info(f"\n文件: {file_path}")
        for old_file, lines in dependencies.items():
            logger.info(f"  依赖于 {old_file}:")
            for line in lines[:5]:  # 只显示前5行
                logger.info(f"    {line}")
            if len(lines) > 5:
                logger.info(f"    ... 还有 {len(lines) - 5} 行")

    logger.info("\n请先解决这些依赖关系，然后再尝试清理旧文件")


def backup_old_files(old_files: List[str]) -> None:
    """
    备份旧文件

    参数:
        old_files: 旧文件列表
    """
    backup_dir = 'backups/old_indicator_system'
    os.makedirs(backup_dir, exist_ok=True)

    for old_file in old_files:
        if os.path.exists(old_file):
            # 创建目标目录
            backup_file = os.path.join(backup_dir, old_file)
            os.makedirs(os.path.dirname(backup_file), exist_ok=True)

            # 复制文件
            shutil.copy2(old_file, backup_file)
            logger.info(f"已备份 {old_file} 到 {backup_file}")


def cleanup_old_files(old_files: List[str]) -> None:
    """
    清理旧文件

    参数:
        old_files: 旧文件列表
    """
    for old_file in old_files:
        if os.path.exists(old_file):
            os.remove(old_file)
            logger.info(f"已删除 {old_file}")

    # 检查并删除空目录
    directories = set(os.path.dirname(old_file) for old_file in old_files)
    for directory in directories:
        if os.path.exists(directory) and not os.listdir(directory):
            os.rmdir(directory)
            logger.info(f"已删除空目录 {directory}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='检查旧指标系统的依赖关系，并在确认安全后清理旧代码')
    parser.add_argument('--check-only', action='store_true', help='只检查依赖关系，不清理旧代码')
    parser.add_argument('--cleanup', action='store_true', help='清理旧代码，不检查依赖关系')
    parser.add_argument('--root-dir', default='.', help='项目根目录，默认为当前目录')
    args = parser.parse_args()

    # 确保old_files中的路径是相对于root_dir的
    old_files = [os.path.join(args.root_dir, old_file) for old_file in OLD_FILES]

    if args.cleanup:
        # 备份旧文件
        backup_old_files(old_files)

        # 清理旧文件
        cleanup_old_files(old_files)

        logger.info("旧代码清理完成")
    else:
        # 检查依赖关系
        all_dependencies = check_all_dependencies(args.root_dir, old_files)

        # 生成依赖报告
        generate_dependency_report(all_dependencies)

        if not args.check_only and not all_dependencies:
            # 如果没有依赖关系，并且不是只检查模式，则清理旧代码
            backup_old_files(old_files)
            cleanup_old_files(old_files)
            logger.info("旧代码清理完成")


if __name__ == '__main__':
    main()
