#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接执行QSS文件重命名（非交互式）
"""

from loguru import logger
import sys
import os
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(project_root))

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level:8}</level> | <level>{message}</level>")


# QSS文件重命名映射
QSS_FILE_RENAME_MAP = {
    '1.qss': '炫彩渐变.qss',
    '2.qss': '蓝紫渐变.qss',
    '3.qss': 'AMOLED深黑.qss',
    '4.qss': '水蓝风格.qss',
    '5.qss': '墨蓝深色.qss',
    '6.qss': '暗黑控制台.qss',
    '8.qss': '优雅深色.qss',
    '9.qss': 'Manjaro混搭.qss',
    '10.qss': 'Material Dark.qss',
    '11.qss': '霓虹按钮.qss',
    '12.qss': '简约灰白.qss',
    '13.qss': '绿松石.qss',
    '14.qss': '金色辉煌.qss',
    '15.qss': '粉橙渐变.qss',
    '16.qss': 'Ubuntu风格.qss',
    '17.qss': '米白清新.qss',
}


def main():
    """主函数"""
    logger.info("\n🎨 执行QSS文件批量重命名\n")

    qss_directory = "QSSThemeBack"
    qss_dir = Path(qss_directory)

    if not qss_dir.exists():
        logger.error(f"❌ 目录不存在: {qss_directory}")
        return False

    # 创建备份
    backup_dir = f"{qss_directory}_backup"
    if not os.path.exists(backup_dir):
        try:
            shutil.copytree(qss_directory, backup_dir)
            logger.info(f"✅ 已创建备份: {backup_dir}\n")
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return False
    else:
        logger.info(f"⚠️  备份目录已存在: {backup_dir}\n")

    # 执行重命名
    logger.info("="*80)
    logger.info("开始重命名QSS文件")
    logger.info("="*80 + "\n")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for old_name, new_name in QSS_FILE_RENAME_MAP.items():
        old_path = qss_dir / old_name
        new_path = qss_dir / new_name

        if not old_path.exists():
            logger.warning(f"⏭️  跳过: {old_name:20s} (文件不存在)")
            skip_count += 1
            continue

        if new_path.exists() and old_path != new_path:
            logger.warning(f"⚠️  跳过: {old_name:20s} → {new_name} (目标已存在)")
            skip_count += 1
            continue

        try:
            old_path.rename(new_path)
            logger.info(f"✅ {old_name:20s} → {new_name}")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ {old_name:20s} → {new_name} (失败: {e})")
            fail_count += 1

    # 显示结果
    logger.info("\n" + "="*80)
    logger.info("重命名完成")
    logger.info("="*80)
    logger.info(f"  成功: {success_count} 个")
    logger.info(f"  失败: {fail_count} 个")
    logger.info(f"  跳过: {skip_count} 个")
    logger.info("="*80)

    if fail_count == 0:
        logger.info(f"\n🎉 文件重命名成功！已重命名 {success_count} 个文件")

        # 显示重命名后的文件列表
        logger.info("\n" + "="*80)
        logger.info("重命名后的文件列表（QSSThemeBack目录）")
        logger.info("="*80 + "\n")

        qss_files = sorted(qss_dir.glob('*.qss'))
        for i, file_path in enumerate(qss_files, 1):
            logger.info(f"  {i:2d}. {file_path.name}")

        return True
    else:
        logger.error(f"\n⚠️  重命名完成，但有 {fail_count} 个文件失败")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        sys.exit(1)
