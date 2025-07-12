#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
依赖检查和旧代码清理脚本
用于检查项目中是否还有对旧指标系统的依赖，并在确认安全后清理旧代码
"""

import os
import sys
import re
import logging
from typing import List, Dict, Tuple, Any, Optional
import subprocess

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('check_dependencies_cleanup')

# 旧的指标系统文件
OLD_INDICATOR_FILES = [
    os.path.join(parent_dir, 'indicators_algo.py'),
    os.path.join(parent_dir, 'features', 'basic_indicators.py'),
    os.path.join(parent_dir, 'features', 'advanced_indicators.py')
]

# 旧的导入语句模式
OLD_IMPORT_PATTERNS = [
    r'from\s+indicators_algo\s+import',
    r'from\s+features\.basic_indicators\s+import',
    r'from\s+features\.advanced_indicators\s+import',
    r'import\s+indicators_algo',
    r'import\s+features\.basic_indicators',
    r'import\s+features\.advanced_indicators'
]


def check_file_exists(file_path: str) -> bool:
    """
    检查文件是否存在

    参数:
        file_path: 文件路径

    返回:
        bool: 文件是否存在
    """
    return os.path.exists(file_path)


def find_imports_in_project(import_pattern: str) -> List[str]:
    """
    在项目中查找特定导入语句的文件

    参数:
        import_pattern: 导入语句模式

    返回:
        List[str]: 包含该导入语句的文件列表
    """
    try:
        # 使用grep查找包含特定导入语句的文件
        cmd = ['grep', '-r', import_pattern, '--include=*.py', parent_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode not in [0, 1]:  # 0表示找到匹配，1表示没有找到匹配
            logger.error(f"grep命令执行失败: {result.stderr}")
            return []

        # 解析结果
        files = []
        for line in result.stdout.splitlines():
            if ':' in line:
                file_path = line.split(':', 1)[0]
                if file_path not in files and os.path.exists(file_path):
                    files.append(file_path)

        return files

    except Exception as e:
        logger.error(f"查找导入语句时发生错误: {str(e)}")
        return []


def check_all_dependencies() -> Dict[str, List[str]]:
    """
    检查项目中所有对旧指标系统的依赖

    返回:
        Dict[str, List[str]]: 导入语句模式到依赖文件列表的映射
    """
    dependencies = {}
    for pattern in OLD_IMPORT_PATTERNS:
        files = find_imports_in_project(pattern)
        if files:
            dependencies[pattern] = files

    return dependencies


def backup_file(file_path: str) -> bool:
    """
    备份文件

    参数:
        file_path: 文件路径

    返回:
        bool: 是否成功备份
    """
    backup_path = f"{file_path}.bak"
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        logger.info(f"已备份文件: {file_path} -> {backup_path}")
        return True
    except Exception as e:
        logger.error(f"备份文件失败: {str(e)}")
        return False


def delete_file(file_path: str) -> bool:
    """
    删除文件

    参数:
        file_path: 文件路径

    返回:
        bool: 是否成功删除
    """
    try:
        os.remove(file_path)
        logger.info(f"已删除文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return False


def check_empty_directory(directory: str) -> bool:
    """
    检查目录是否为空

    参数:
        directory: 目录路径

    返回:
        bool: 目录是否为空
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return False

    return len(os.listdir(directory)) == 0


def delete_directory(directory: str) -> bool:
    """
    删除目录

    参数:
        directory: 目录路径

    返回:
        bool: 是否成功删除
    """
    try:
        os.rmdir(directory)
        logger.info(f"已删除目录: {directory}")
        return True
    except Exception as e:
        logger.error(f"删除目录失败: {str(e)}")
        return False


def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='检查依赖并清理旧代码')
    parser.add_argument('--check-only', action='store_true',
                        help='只检查依赖，不清理旧代码')
    parser.add_argument(
        '--force-delete', action='store_true', help='强制删除旧代码，即使还有依赖')
    args = parser.parse_args()

    # 检查旧文件是否存在
    existing_files = []
    for file_path in OLD_INDICATOR_FILES:
        if check_file_exists(file_path):
            existing_files.append(file_path)

    if not existing_files:
        logger.info("未找到任何旧指标系统文件，无需清理")
        return

    logger.info(f"找到以下旧指标系统文件: {existing_files}")

    # 检查依赖
    dependencies = check_all_dependencies()
    if dependencies:
        logger.warning("项目中仍有以下对旧指标系统的依赖:")
        for pattern, files in dependencies.items():
            logger.warning(f"  导入模式: {pattern}")
            for file in files:
                logger.warning(f"    - {file}")

        if not args.force_delete:
            logger.error("由于还存在依赖，不会删除旧代码。请先解决这些依赖，或使用--force-delete选项强制删除")
            return
        else:
            logger.warning("将强制删除旧代码，即使还有依赖")
    else:
        logger.info("未发现对旧指标系统的依赖，可以安全地删除旧代码")

    # 如果只是检查依赖，到此结束
    if args.check_only:
        logger.info("只检查依赖，不清理旧代码")
        return

    # 备份并删除旧文件
    for file_path in existing_files:
        if backup_file(file_path):
            delete_file(file_path)

    # 检查features目录是否为空，如果为空则删除
    features_dir = os.path.join(parent_dir, 'features')
    if check_empty_directory(features_dir):
        logger.info(f"features目录为空，将删除: {features_dir}")
        delete_directory(features_dir)
    else:
        logger.info(f"features目录不为空，不会删除: {features_dir}")


if __name__ == '__main__':
    main()
