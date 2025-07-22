#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终修复形态表格显示问题
"""

import os
import sys


def main():
    # 文件路径
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"

    print("开始最终修复...")

    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 {file_path}")
        return False

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找到_update_patterns_table方法的起始行
    start_idx = -1
    for i, line in enumerate(lines):
        if "def _update_patterns_table(self, patterns):" in line:
            start_idx = i
            break

    if start_idx == -1:
        print("错误: 未找到_update_patterns_table方法")
        return False

    # 找到方法结束的位置
    end_idx = -1
    for i in range(start_idx + 1, len(lines)):
        if "def _update_statistics_display(self, stats):" in lines[i]:
            end_idx = i
            break

    if end_idx == -1:
        print("错误: 未找到方法结束位置")
        return False

    print(f"找到方法: 行 {start_idx+1} 到 {end_idx}")

    # 创建新的方法实现
    new_method_lines = []
    new_method_lines.append("    def _update_patterns_table(self, patterns):\n")
    new_method_lines.append("        '''更新形态表格 - 最终修复版'''\n")
    new_method_lines.append("        try:\n")
    new_method_lines.append("            # 清空表格\n")
    new_method_lines.append("            self.patterns_table.setRowCount(0)\n")
    new_method_lines.append("            \n")
    new_method_lines.append("            # 如果没有形态，显示提示信息\n")
    new_method_lines.append("            if not patterns:\n")
    new_method_lines.append("                self.log_manager.warning(\"没有检测到形态\")\n")
    new_method_lines.append("                self.patterns_table.setRowCount(1)\n")
    new_method_lines.append("                self.patterns_table.setItem(0, 0, QTableWidgetItem(\"未检测到形态\"))\n")
    new_method_lines.append("                # 填充其他单元格\n")
    new_method_lines.append("                for col in range(1, self.patterns_table.columnCount()):\n")
    new_method_lines.append("                    self.patterns_table.setItem(0, col, QTableWidgetItem(\"\"))\n")
    new_method_lines.append("                return\n")
    new_method_lines.append("\n")
    new_method_lines.append("            # 输出详细的调试信息\n")
    new_method_lines.append("            self.log_manager.info(f\"收到 {len(patterns)} 个形态数据\")\n")
    new_method_lines.append("            if patterns:\n")
    new_method_lines.append("                self.log_manager.info(f\"第一个形态数据的键: {list(patterns[0].keys() if isinstance(patterns[0], dict) else [])}\")\n")
    new_method_lines.append("                self.log_manager.info(f\"第一个形态数据的值: {patterns[0]}\")\n")
    new_method_lines.append("                \n")
    new_method_lines.append("            # 去重处理\n")
    new_method_lines.append("            unique_patterns = []\n")
    new_method_lines.append("            seen_patterns = set()\n")
    new_method_lines.append("            for pattern in patterns:\n")
    new_method_lines.append("                # 创建唯一标识符\n")
    new_method_lines.append("                if isinstance(pattern, dict):\n")
    new_method_lines.append("                    pattern_type = pattern.get('type', pattern.get('pattern_name', ''))\n")
    new_method_lines.append("                    index = pattern.get('index', -1)\n")
    new_method_lines.append("                    key = f\"{pattern_type}_{index}\"\n")
    new_method_lines.append("                    if key not in seen_patterns:\n")
    new_method_lines.append("                        seen_patterns.add(key)\n")
    new_method_lines.append("                        unique_patterns.append(pattern)\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    unique_patterns.append(pattern)\n")
    new_method_lines.append("                \n")
    new_method_lines.append("            self.log_manager.info(f\"去重后剩余 {len(unique_patterns)} 个形态\")\n")
    new_method_lines.append("            patterns = unique_patterns\n")
    new_method_lines.append("                \n")
    new_method_lines.append("            # 设置表格行数\n")
    new_method_lines.append("            self.patterns_table.setRowCount(len(patterns))\n")
    new_method_lines.append("            \n")
    new_method_lines.append("            # 填充表格数据\n")
    new_method_lines.append("            for row, pattern in enumerate(patterns):\n")
    new_method_lines.append("                if not isinstance(pattern, dict):\n")
    new_method_lines.append("                    continue\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 1. 形态名称 - 列0\n")
    new_method_lines.append("                pattern_name = pattern.get('pattern_name', pattern.get('name', pattern.get('type', '未知形态')))\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 0, QTableWidgetItem(str(pattern_name)))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 2. 类型 - 列1\n")
    new_method_lines.append("                category = pattern.get('pattern_category', pattern.get('category', '未分类'))\n")
    new_method_lines.append("                if hasattr(category, 'value'):  # 如果是枚举\n")
    new_method_lines.append("                    category = category.value\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 1, QTableWidgetItem(str(category)))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 3. 置信度 - 列2\n")
    new_method_lines.append("                confidence = pattern.get('confidence', pattern.get('confidence_level', 0.5))\n")
    new_method_lines.append("                if isinstance(confidence, (int, float)) and not isinstance(confidence, str):\n")
    new_method_lines.append("                    confidence_str = f\"{confidence:.2%}\"\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    confidence_str = str(confidence)\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 2, QTableWidgetItem(confidence_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 4. 成功率 - 列3\n")
    new_method_lines.append("                success_rate = pattern.get('success_rate', 0.7)\n")
    new_method_lines.append("                if isinstance(success_rate, (int, float)) and not isinstance(success_rate, str):\n")
    new_method_lines.append("                    success_rate_str = f\"{success_rate:.2%}\" if success_rate <= 1 else f\"{success_rate}%\"\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    success_rate_str = str(success_rate)\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 3, QTableWidgetItem(success_rate_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 5. 信号 - 列4\n")
    new_method_lines.append("                signal = pattern.get('signal', '')\n")
    new_method_lines.append("                signal_str = \"买入\" if signal == \"buy\" else \"卖出\" if signal == \"sell\" else \"中性\"\n")
    new_method_lines.append("                signal_item = QTableWidgetItem(signal_str)\n")
    new_method_lines.append("                if signal == \"buy\":\n")
    new_method_lines.append("                    signal_item.setForeground(QBrush(QColor(255, 0, 0)))  # 红色买入\n")
    new_method_lines.append("                elif signal == \"sell\":\n")
    new_method_lines.append("                    signal_item.setForeground(QBrush(QColor(0, 128, 0)))  # 绿色卖出\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 4, signal_item)\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 6. 位置 - 列5\n")
    new_method_lines.append("                index = pattern.get('index')\n")
    new_method_lines.append("                datetime_val = pattern.get('datetime')\n")
    new_method_lines.append("                if datetime_val:\n")
    new_method_lines.append("                    position_str = str(datetime_val)\n")
    new_method_lines.append("                elif index is not None:\n")
    new_method_lines.append("                    position_str = f\"K线#{index}\"\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    position_str = \"\"\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 5, QTableWidgetItem(position_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 7. 区间 - 列6\n")
    new_method_lines.append("                start_index = pattern.get('start_index')\n")
    new_method_lines.append("                end_index = pattern.get('end_index')\n")
    new_method_lines.append("                if start_index is not None and end_index is not None:\n")
    new_method_lines.append("                    range_str = f\"{start_index}-{end_index}\"\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    range_str = \"\"\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 6, QTableWidgetItem(range_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 8. 价格 - 列7\n")
    new_method_lines.append("                price = pattern.get('price')\n")
    new_method_lines.append("                price_str = f\"{price:.2f}\" if price is not None else \"\"\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 7, QTableWidgetItem(price_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 9. 目标价 - 列8\n")
    new_method_lines.append("                target_price = pattern.get('target_price')\n")
    new_method_lines.append("                if target_price is None and price is not None:\n")
    new_method_lines.append("                    # 简单估算目标价\n")
    new_method_lines.append("                    if signal == \"buy\":\n")
    new_method_lines.append("                        target_price = price * 1.05  # 假设上涨5%\n")
    new_method_lines.append("                    elif signal == \"sell\":\n")
    new_method_lines.append("                        target_price = price * 0.95  # 假设下跌5%\n")
    new_method_lines.append("                target_price_str = f\"{target_price:.2f}\" if target_price is not None else \"\"\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 8, QTableWidgetItem(target_price_str))\n")
    new_method_lines.append("                \n")
    new_method_lines.append("                # 10. 建议 - 列9\n")
    new_method_lines.append("                if signal == \"buy\":\n")
    new_method_lines.append("                    recommendation = \"建议买入\"\n")
    new_method_lines.append("                elif signal == \"sell\":\n")
    new_method_lines.append("                    recommendation = \"建议卖出\"\n")
    new_method_lines.append("                else:\n")
    new_method_lines.append("                    recommendation = \"观望\"\n")
    new_method_lines.append("                self.patterns_table.setItem(row, 9, QTableWidgetItem(recommendation))\n")
    new_method_lines.append("            \n")
    new_method_lines.append("            # 自适应列宽\n")
    new_method_lines.append("            self.patterns_table.resizeColumnsToContents()\n")
    new_method_lines.append("            \n")
    new_method_lines.append("            # 确保表格为只读\n")
    new_method_lines.append("            self.patterns_table.setEditTriggers(QTableWidget.NoEditTriggers)\n")
    new_method_lines.append("            \n")
    new_method_lines.append("            self.log_manager.info(f\"成功更新形态表格，共 {len(patterns)} 条记录\")\n")
    new_method_lines.append("            \n")
    new_method_lines.append("        except Exception as e:\n")
    new_method_lines.append("            self.log_manager.error(f\"更新形态表格失败: {e}\")\n")
    new_method_lines.append("            import traceback\n")
    new_method_lines.append("            self.log_manager.error(traceback.format_exc())\n")
    new_method_lines.append("\n")

    # 替换原方法
    new_lines = lines[:start_idx] + new_method_lines + lines[end_idx:]

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"成功修复 _update_patterns_table 方法!")
    return True


if __name__ == "__main__":
    print("="*60)
    print("最终修复形态表格显示问题")
    print("="*60)

    if main():
        print("="*60)
        print("✓ 修复成功! 请重启应用验证效果")
        print("="*60)
    else:
        print("="*60)
        print("✗ 修复失败! 请查看错误信息")
        print("="*60)
