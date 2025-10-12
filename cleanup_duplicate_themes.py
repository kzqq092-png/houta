#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理重复的主题"""

from utils.config_manager import ConfigManager
from utils.theme import get_theme_manager
from loguru import logger
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(project_root))

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>")


def main():
    logger.info("\n🧹 清理重复主题")

    tm = get_theme_manager(ConfigManager())
    themes = tm.get_available_themes()

    # 要删除的重复主题
    duplicates_to_remove = ['Dark', 'Light', 'Gradient']

    logger.info(f"\n当前主题总数: {len(themes)}")
    logger.info(f"计划删除重复主题: {', '.join(duplicates_to_remove)}\n")

    for theme_name in duplicates_to_remove:
        if theme_name in themes:
            try:
                result = tm.delete_theme(theme_name)
                if result:
                    logger.info(f"✅ 已删除: {theme_name}")
                else:
                    logger.error(f"❌ 删除失败: {theme_name}")
            except Exception as e:
                logger.error(f"❌ 删除异常: {theme_name} - {e}")
        else:
            logger.warning(f"⏭️  跳过: {theme_name} (不存在)")

    # 显示最终主题列表
    final_themes = tm.get_available_themes()
    logger.info(f"\n✅ 清理完成！")
    logger.info(f"\n最终主题总数: {len(final_themes)}")
    logger.info(f"\n主题列表（按拼音排序）:\n")

    for i, name in enumerate(sorted(final_themes.keys()), 1):
        theme_type = final_themes[name].get('type', 'unknown')
        logger.info(f"  {i:2d}. {name:25s} ({theme_type})")


if __name__ == "__main__":
    main()
