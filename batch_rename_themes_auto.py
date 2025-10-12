#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主题自动批量重命名
根据主题内容智能推测并批量重命名为有意义的名称
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


# 预定义的重命名映射（基于对QSS文件的观察）
PREDEFINED_RENAME_MAP = {
    # 已有良好名称的保持不变
    'Material Dark': 'Material Dark',
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

    # 数字主题需要重命名
    '1': '炫彩渐变',
    '2': '蓝紫渐变',
    '5': '墨蓝深色',
    '7': '紫罗兰渐变',
    '12': '简约灰白',
    '13': '绿松石',
    '14': '金色辉煌',
    '15': '粉橙渐变',
    '17': '米白清新',
}


def get_rename_plan(theme_manager):
    """获取重命名计划"""
    logger.info("="*80)
    logger.info("📋 生成智能重命名方案")
    logger.info("="*80)

    available_themes = theme_manager.get_available_themes()

    rename_plan = []
    unchanged = []

    for theme_name in available_themes.keys():
        if theme_name in PREDEFINED_RENAME_MAP:
            new_name = PREDEFINED_RENAME_MAP[theme_name]

            if theme_name == new_name:
                unchanged.append(theme_name)
            else:
                rename_plan.append({
                    'old_name': theme_name,
                    'new_name': new_name
                })
        else:
            # 未在映射中的主题保持不变
            unchanged.append(theme_name)

    logger.info(f"\n计划重命名: {len(rename_plan)} 个主题")
    logger.info(f"保持不变: {len(unchanged)} 个主题\n")

    if rename_plan:
        logger.info("重命名清单：")
        for i, item in enumerate(rename_plan, 1):
            logger.info(f"  {i:2d}. {item['old_name']:25s} → {item['new_name']}")

    if unchanged:
        logger.info(f"\n保持不变的主题: {', '.join(unchanged)}")

    return rename_plan


def execute_rename(theme_manager, rename_plan, dry_run=True):
    """执行重命名"""
    logger.info("\n" + "="*80)
    if dry_run:
        logger.info("🔍 预演模式（不会实际修改数据库）")
    else:
        logger.info("✏️ 执行批量重命名")
    logger.info("="*80 + "\n")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for item in rename_plan:
        old_name = item['old_name']
        new_name = item['new_name']

        if old_name == new_name:
            skip_count += 1
            continue

        if dry_run:
            logger.info(f"📝 {old_name:25s} → {new_name}")
        else:
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
    logger.info("重命名结果汇总")
    logger.info("="*80)

    if dry_run:
        logger.info(f"  预演完成")
        logger.info(f"  计划重命名: {len(rename_plan)} 个")
    else:
        logger.info(f"  成功: {success_count} 个")
        logger.info(f"  失败: {fail_count} 个")
        logger.info(f"  跳过: {skip_count} 个")

    logger.info("="*80)

    return success_count, fail_count, skip_count


def main():
    """主函数"""
    logger.info("\n" + "🎨 主题智能批量重命名工具" + "\n")

    try:
        from utils.theme import get_theme_manager
        from utils.config_manager import ConfigManager

        config_manager = ConfigManager()
        theme_manager = get_theme_manager(config_manager)

        # 获取重命名计划
        rename_plan = get_rename_plan(theme_manager)

        if not rename_plan:
            logger.info("\n✅ 所有主题名称都已符合要求，无需重命名")
            return True

        # 先预演
        logger.info("\n" + "="*80)
        logger.info("步骤1：预演重命名（查看效果）")
        logger.info("="*80)
        execute_rename(theme_manager, rename_plan, dry_run=True)

        # 询问确认
        logger.info("\n" + "⚠️  注意：即将修改数据库中的主题名称")
        logger.info("确认执行重命名吗？")
        logger.info("  输入 'yes' 或 'y' 确认")
        logger.info("  输入其他任意内容取消")

        confirm = input("\n请输入: ").strip().lower()

        if confirm in ['yes', 'y', '是']:
            logger.info("\n" + "="*80)
            logger.info("步骤2：执行重命名")
            logger.info("="*80)

            success, fail, skip = execute_rename(theme_manager, rename_plan, dry_run=False)

            if fail == 0:
                logger.info(f"\n🎉 批量重命名完成！成功重命名 {success} 个主题")
                return True
            else:
                logger.error(f"\n⚠️  重命名完成，但有 {fail} 个主题失败")
                return False
        else:
            logger.info("\n❌ 用户取消操作")
            return False

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  用户中断")
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
