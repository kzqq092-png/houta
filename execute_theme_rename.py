#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接执行主题批量重命名（非交互式）
"""

from loguru import logger
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(project_root))

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level:8}</level> | <level>{message}</level>")


# 重命名映射
RENAME_MAP = {
    '1': '炫彩渐变',
    '2': '蓝紫渐变',
    '5': '墨蓝深色',
    '7': '紫罗兰渐变',
    '12': '简约灰白',
    '13': '绿松石',
    '14': '金色辉煌',
    '15': '粉橙渐变',
    '17': '米白清新',
    'Neon  (QpushButton)': '霓虹按钮',
    'Ubuntu': 'Ubuntu风格',
    'AMOLED': 'AMOLED深黑',
    'Aqua': '水蓝风格',
    'Dark Console': '暗黑控制台',
    'ElegantDark': '优雅深色',
    'ManjaroMix': 'Manjaro混搭',
    'Light': '浅色经典',
    'Dark': '深色经典',
    'Gradient': '渐变彩色',
}


def main():
    """主函数"""
    logger.info("\n" + "🎨 执行主题批量重命名" + "\n")

    try:
        from utils.theme import get_theme_manager
        from utils.config_manager import ConfigManager

        config_manager = ConfigManager()
        theme_manager = get_theme_manager(config_manager)

        available_themes = theme_manager.get_available_themes()

        logger.info("="*80)
        logger.info(f"当前共有 {len(available_themes)} 个主题")
        logger.info("="*80 + "\n")

        success_count = 0
        fail_count = 0
        skip_count = 0

        for old_name, new_name in RENAME_MAP.items():
            if old_name not in available_themes:
                logger.warning(f"⏭️  跳过: {old_name:25s} (主题不存在)")
                skip_count += 1
                continue

            if old_name == new_name:
                logger.info(f"⏭️  跳过: {old_name:25s} (名称未变)")
                skip_count += 1
                continue

            try:
                result = theme_manager.rename_theme(old_name, new_name)
                if result:
                    logger.info(f"✅ {old_name:25s} → {new_name}")
                    success_count += 1
                else:
                    logger.error(f"❌ {old_name:25s} → {new_name} (重命名失败)")
                    fail_count += 1
            except Exception as e:
                logger.error(f"❌ {old_name:25s} → {new_name} (异常: {e})")
                fail_count += 1

        logger.info("\n" + "="*80)
        logger.info("重命名完成")
        logger.info("="*80)
        logger.info(f"  成功: {success_count} 个")
        logger.info(f"  失败: {fail_count} 个")
        logger.info(f"  跳过: {skip_count} 个")
        logger.info("="*80)

        if fail_count == 0:
            logger.info(f"\n🎉 批量重命名成功！已重命名 {success_count} 个主题")

            # 显示更新后的主题列表
            logger.info("\n" + "="*80)
            logger.info("更新后的主题列表")
            logger.info("="*80)

            updated_themes = theme_manager.get_available_themes()
            for idx, theme_name in enumerate(sorted(updated_themes.keys()), 1):
                theme_info = updated_themes[theme_name]
                theme_type = theme_info.get('type', 'unknown')
                logger.info(f"  {idx:2d}. {theme_name:25s} ({theme_type})")

            return True
        else:
            logger.error(f"\n⚠️  重命名完成，但有 {fail_count} 个主题失败")
            return False

    except Exception as e:
        logger.error(f"\n❌ 发生错误: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        sys.exit(1)
