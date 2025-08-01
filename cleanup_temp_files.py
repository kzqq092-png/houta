#!/usr/bin/env python3
"""
临时文件清理脚本

清理HIkyuu-UI项目中的临时文件和无效文件
"""

import os
import logging
from pathlib import Path
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent


def cleanup_temp_files():
    """清理临时文件"""
    logger.info("开始清理临时文件...")

    # 定义需要清理的临时文件和目录
    temp_patterns = [
        # Python缓存文件
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',

        # 系统临时文件
        '**/.DS_Store',
        '**/Thumbs.db',
        '**/*.tmp',
        '**/*.temp',

        # 编辑器临时文件
        '**/*~',
        '**/*.swp',
        '**/*.swo',
        '**/.vscode/settings.json',

        # 日志文件
        '**/logs/*.log',
        '**/*.log',

        # 测试文件
        '**/.pytest_cache',
        '**/test_*.py.bak',

        # 大型分析报告（保留最新的）
        'SYSTEM_ANALYSIS_REPORT.json',  # 太大，可以删除
        'REGRESSION_VALIDATION_REPORT.json'  # 可以删除，已有最终报告
    ]

    # 特定的临时测试文件
    specific_temp_files = [
        'test_model_types_validation.py',
        'test_model_types_simple.py',
        'test_config_only.py',
        'test_model_accuracy_validation.py',
        'test_model_standalone_validation.py',
        'test_enhanced_model_validation.py',
        'test_config_integration.py',
        'professional_ai_trading_validation.py',
        'regression_validation.py'  # 保留final_validation.py
    ]

    deleted_files = []
    deleted_dirs = []

    # 清理模式匹配的文件
    for pattern in temp_patterns:
        for path in project_root.glob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    deleted_files.append(str(path.relative_to(project_root)))
                    logger.info(f"删除文件: {path.relative_to(project_root)}")
                elif path.is_dir() and path.name == '__pycache__':
                    import shutil
                    shutil.rmtree(path)
                    deleted_dirs.append(str(path.relative_to(project_root)))
                    logger.info(f"删除目录: {path.relative_to(project_root)}")
            except Exception as e:
                logger.warning(f"删除失败 {path}: {e}")

    # 清理特定临时文件
    for file_name in specific_temp_files:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_files.append(file_name)
                logger.info(f"删除临时文件: {file_name}")
            except Exception as e:
                logger.warning(f"删除失败 {file_name}: {e}")

    return deleted_files, deleted_dirs


def cleanup_duplicate_reports():
    """清理重复的报告文件，保留最新的"""
    logger.info("清理重复报告文件...")

    # 保留最重要的报告，删除中间版本
    reports_to_keep = [
        '最终修复总结报告.md',
        'FINAL_VALIDATION_REPORT.json',
        'PERFORMANCE_OPTIMIZATION_GUIDE.md',
        '剩余配置模块优化分析报告.md'
    ]

    reports_to_remove = [
        '系统功能修复总结报告.md'  # 已有最终版本
    ]

    deleted_reports = []

    for report_name in reports_to_remove:
        report_path = project_root / report_name
        if report_path.exists():
            try:
                report_path.unlink()
                deleted_reports.append(report_name)
                logger.info(f"删除重复报告: {report_name}")
            except Exception as e:
                logger.warning(f"删除失败 {report_name}: {e}")

    return deleted_reports


def cleanup_old_backups():
    """清理旧的备份文件"""
    logger.info("清理旧备份文件...")

    backup_patterns = [
        '**/*.bak',
        '**/*.backup',
        '**/*_backup.py',
        '**/backup_*',
        # 清理已知的备份目录中的旧文件（如果存在）
    ]

    deleted_backups = []

    for pattern in backup_patterns:
        for path in project_root.glob(pattern):
            if path.is_file():
                try:
                    path.unlink()
                    deleted_backups.append(str(path.relative_to(project_root)))
                    logger.info(f"删除备份文件: {path.relative_to(project_root)}")
                except Exception as e:
                    logger.warning(f"删除失败 {path}: {e}")

    return deleted_backups


def get_project_size():
    """获取项目大小"""
    total_size = 0
    file_count = 0

    for path in project_root.rglob('*'):
        if path.is_file():
            try:
                size = path.stat().st_size
                total_size += size
                file_count += 1
            except:
                pass

    return total_size, file_count


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def main():
    """主函数"""
    print("🧹 HIkyuu-UI 临时文件清理工具")
    print("=" * 50)

    # 获取清理前的项目大小
    size_before, files_before = get_project_size()
    logger.info(f"清理前: {files_before} 个文件, 总大小: {format_size(size_before)}")

    # 执行清理
    deleted_files, deleted_dirs = cleanup_temp_files()
    deleted_reports = cleanup_duplicate_reports()
    deleted_backups = cleanup_old_backups()

    # 获取清理后的项目大小
    size_after, files_after = get_project_size()
    size_saved = size_before - size_after
    files_deleted = files_before - files_after

    # 显示清理结果
    print(f"\n📊 清理结果统计:")
    print(f"   删除文件: {len(deleted_files)} 个")
    print(f"   删除目录: {len(deleted_dirs)} 个")
    print(f"   删除报告: {len(deleted_reports)} 个")
    print(f"   删除备份: {len(deleted_backups)} 个")
    print(f"   总删除: {files_deleted} 个文件")
    print(f"   节省空间: {format_size(size_saved)}")

    print(f"\n📈 项目状态:")
    print(f"   清理前: {files_before} 个文件, {format_size(size_before)}")
    print(f"   清理后: {files_after} 个文件, {format_size(size_after)}")

    # 显示保留的重要文件
    important_files = [
        'db/models/ai_config_models.py',
        'gui/widgets/analysis_tabs/pattern_tab_pro.py',
        'system_code_chain_analysis.py',
        'fix_syntax_errors.py',
        'enhance_config_modules.py',
        'final_validation.py',
        '最终修复总结报告.md',
        'FINAL_VALIDATION_REPORT.json',
        'PERFORMANCE_OPTIMIZATION_GUIDE.md'
    ]

    print(f"\n📋 保留的重要文件:")
    for file_path in important_files:
        if (project_root / file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")

    print(f"\n✅ 清理完成!")
    logger.info("临时文件清理完成")


if __name__ == "__main__":
    main()
