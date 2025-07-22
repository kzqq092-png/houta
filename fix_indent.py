#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复pattern_tab_pro.py中的缩进错误
"""

import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_indent")


def fix_indentation():
    """修复缩进错误"""
    pattern_tab_pro_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"

    if not os.path.exists(pattern_tab_pro_path):
        logger.error(f"找不到文件: {pattern_tab_pro_path}")
        return False

    logger.info(f"开始修复缩进错误: {pattern_tab_pro_path}")

    try:
        with open(pattern_tab_pro_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 定位到更新统计显示方法
        stats_method_start = content.find("    def _update_statistics_display(self, stats):")
        if stats_method_start == -1:
            logger.error("找不到_update_statistics_display方法")
            return False

        # 错误的缩进
        wrong_indentation = content.find("        def _update_statistics_display(self, stats):", stats_method_start-100)
        if wrong_indentation != -1:
            # 修复缩进
            corrected_content = content.replace("        def _update_statistics_display(self, stats):", "    def _update_statistics_display(self, stats):")

            # 写入修复后的内容
            with open(pattern_tab_pro_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content)

            logger.info("成功修复缩进错误")
            return True
        else:
            # 检查是否有其他位置的缩进错误
            content_lines = content.split('\n')
            fixed_lines = []
            fixed = False

            for i, line in enumerate(content_lines):
                if "def _update_statistics_display" in line and not line.startswith("    def "):
                    fixed_line = "    def _update_statistics_display" + line.split("def _update_statistics_display")[1]
                    fixed_lines.append(fixed_line)
                    fixed = True
                    logger.info(f"修复第 {i+1} 行缩进错误")
                else:
                    fixed_lines.append(line)

            if fixed:
                # 写入修复后的内容
                with open(pattern_tab_pro_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))

                logger.info("成功修复缩进错误")
                return True
            else:
                # 兜底方案 - 完全重写_update_statistics_display方法
                correct_method = """    def _update_statistics_display(self, stats):
        \"\"\"更新统计显示\"\"\"
        text = f\"\"\"
📊 统计分析报告
================

总体统计:
- 检测到形态数量: {stats.get('total_patterns', 0)} 个
- 平均置信度: {stats.get('avg_confidence', 0):.2%}
- 平均成功率: {stats.get('avg_success_rate', 0):.2%}

风险分布:
\"\"\"

        risk_dist = stats.get('risk_distribution', {})
        for risk, count in risk_dist.items():
            text += f\"- {risk}: {count} 个\\n\"

        text += \"\\n类型分布:\\n\"
        category_dist = stats.get('category_distribution', {})
        for category, count in category_dist.items():
            text += f\"- {self._get_category_name(category)}: {count} 个\\n\"

        self.stats_text.setText(text)"""

                # 使用开头和结尾定位完整的方法
                method_start = content.find("def _update_statistics_display(self, stats):")
                if method_start == -1:
                    logger.error("找不到_update_statistics_display方法")
                    return False

                method_end = content.find("    def _process_alerts", method_start)
                if method_end == -1:
                    logger.error("找不到_update_statistics_display方法的结束位置")
                    return False

                # 替换方法
                corrected_content = content[:method_start-4] + correct_method + content[method_end:]

                # 写入修复后的内容
                with open(pattern_tab_pro_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_content)

                logger.info("成功通过完全重写修复_update_statistics_display方法")
                return True

    except Exception as e:
        logger.error(f"修复缩进错误失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=== 开始修复缩进错误 ===")

    if fix_indentation():
        logger.info("=== 修复成功! ===")
    else:
        logger.error("=== 修复失败! ===")


if __name__ == "__main__":
    main()
