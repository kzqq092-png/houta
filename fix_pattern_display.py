#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终修复形态表格显示问题 - 修复表格中只显示形态名称且重复的问题
"""

import os
import traceback
import logging

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_pattern_display")


def fix_table_display():
    """修复表格显示问题"""
    try:
        pattern_tab_pro_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"

        if not os.path.exists(pattern_tab_pro_path):
            logger.error(f"找不到文件: {pattern_tab_pro_path}")
            return False

        logger.info(f"开始最终修复形态表格显示问题: {pattern_tab_pro_path}")

        with open(pattern_tab_pro_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找_update_patterns_table方法
        method_start = content.find("def _update_patterns_table(self, patterns):")
        if method_start == -1:
            logger.error("找不到_update_patterns_table方法")
            return False

        # 完全替换_update_patterns_table方法
        old_method_start = method_start
        method_end = content.find("    def _update_statistics_display", method_start)
        if method_end == -1:
            logger.error("找不到_update_patterns_table方法的结束位置")
            return False

        old_method = content[old_method_start:method_end]

        # 新的更新方法 - 彻底简化和重写
        new_method = """def _update_patterns_table(self, patterns):
        '''更新形态表格 - 最终修复版'''
        try:
            # 清空表格
            self.patterns_table.setRowCount(0)
            
            # 如果没有形态，显示提示信息
            if not patterns:
                self.log_manager.warning("没有检测到形态")
                self.patterns_table.setRowCount(1)
                self.patterns_table.setItem(0, 0, QTableWidgetItem("未检测到形态"))
                # 填充其他单元格
                for col in range(1, self.patterns_table.columnCount()):
                    self.patterns_table.setItem(0, col, QTableWidgetItem(""))
                return

            # 输出详细的调试信息
            self.log_manager.info(f"收到 {len(patterns)} 个形态数据")
            if patterns:
                self.log_manager.info(f"第一个形态数据的键: {list(patterns[0].keys() if isinstance(patterns[0], dict) else [])}")
                self.log_manager.info(f"第一个形态数据的值: {patterns[0]}")
                
            # 去重处理
            unique_patterns = []
            seen_patterns = set()
            for pattern in patterns:
                # 创建唯一标识符
                if isinstance(pattern, dict):
                    pattern_type = pattern.get('type', pattern.get('pattern_name', ''))
                    index = pattern.get('index', -1)
                    key = f"{pattern_type}_{index}"
                    if key not in seen_patterns:
                        seen_patterns.add(key)
                        unique_patterns.append(pattern)
                else:
                    unique_patterns.append(pattern)
                
            self.log_manager.info(f"去重后剩余 {len(unique_patterns)} 个形态")
            patterns = unique_patterns
                
            # 设置表格行数
            self.patterns_table.setRowCount(len(patterns))
            
            # 列名和对应的键名
            columns = [
                {"name": "形态名称", "keys": ["pattern_name", "name", "type"]},
                {"name": "类型", "keys": ["pattern_category", "category"]},
                {"name": "置信度", "keys": ["confidence", "confidence_level"]},
                {"name": "成功率", "keys": ["success_rate"]},
                {"name": "信号", "keys": ["risk_level", "signal", "signal_type"]},
                {"name": "位置", "keys": ["index", "datetime"]},
                {"name": "区间", "keys": ["start_index", "end_index"]},
                {"name": "价格", "keys": ["price"]},
                {"name": "目标", "keys": ["target_price"]},
                {"name": "建议", "keys": ["recommendation"]}
            ]
            
            # 设置列头
            self.patterns_table.setColumnCount(len(columns))
            for i, col in enumerate(columns):
                self.patterns_table.setHorizontalHeaderItem(i, QTableWidgetItem(col["name"]))
            
            # 填充表格数据
            for row, pattern in enumerate(patterns):
                if not isinstance(pattern, dict):
                    continue
                    
                for col, column in enumerate(columns):
                    # 尝试从多个可能的键中获取值
                    value = None
                    for key in column["keys"]:
                        if key in pattern:
                            value = pattern[key]
                            break
                            
                    # 特殊处理某些列
                    if value is None:
                        if col == 0:  # 形态名称
                            value = "未知形态"
                        elif col == 1:  # 类型
                            category = pattern.get("category", None)
                            if category is not None and hasattr(category, "value"):
                                value = category.value
                            else:
                                value = "未分类"
                        elif col == 2:  # 置信度
                            value = 0.5
                        elif col == 3:  # 成功率
                            value = 0.7
                        elif col == 4:  # 信号
                            signal = pattern.get("signal")
                            if signal == "buy":
                                value = "买入"
                            elif signal == "sell":
                                value = "卖出"
                            else:
                                value = "中性"
                        elif col == 5:  # 位置
                            idx = pattern.get("index")
                            if idx is not None:
                                value = f"K线#{idx}"
                            else:
                                value = ""
                        elif col == 6:  # 区间
                            start = pattern.get("start_index")
                            end = pattern.get("end_index")
                            if start is not None and end is not None:
                                value = f"{start}-{end}"
                            else:
                                value = ""
                        elif col == 7:  # 价格
                            price = pattern.get("price")
                            if price is not None:
                                value = f"{price:.2f}"
                            else:
                                value = ""
                        elif col == 8:  # 目标价
                            target = pattern.get("target_price")
                            if target is not None:
                                value = f"{target:.2f}"
                            else:
                                value = ""
                        elif col == 9:  # 建议
                            signal = pattern.get("signal")
                            if signal == "buy":
                                value = "建议买入"
                            elif signal == "sell":
                                value = "建议卖出"
                            else:
                                value = "观望"
                    
                    # 格式化处理
                    if col == 2 and isinstance(value, (int, float)) and not isinstance(value, str):
                        value = f"{value:.2%}"
                    elif col == 3 and isinstance(value, (int, float)) and not isinstance(value, str):
                        value = f"{value:.2%}"
                    
                    # 创建单元格项
                    item = QTableWidgetItem(str(value))
                    
                    # 为信号列设置颜色
                    if col == 4:
                        signal = pattern.get("signal", "")
                        if signal == "buy" or (isinstance(value, str) and "买入" in value):
                            item.setForeground(QBrush(QColor(255, 0, 0)))  # 红色
                        elif signal == "sell" or (isinstance(value, str) and "卖出" in value):
                            item.setForeground(QBrush(QColor(0, 128, 0)))  # 绿色
                    
                    self.patterns_table.setItem(row, col, item)
            
            # 设置风险等级行背景色
            for row, pattern in enumerate(patterns):
                if not isinstance(pattern, dict):
                    continue
                    
                risk_level = pattern.get("risk_level", "medium").lower()
                if risk_level == "high":
                    for col in range(self.patterns_table.columnCount()):
                        item = self.patterns_table.item(row, col)
                        if item:
                            item.setBackground(QColor(255, 230, 230))  # 浅红色
                elif risk_level == "low":
                    for col in range(self.patterns_table.columnCount()):
                        item = self.patterns_table.item(row, col)
                        if item:
                            item.setBackground(QColor(230, 255, 230))  # 浅绿色
            
            # 自适应列宽
            self.patterns_table.resizeColumnsToContents()
            
            # 确保表格为只读
            self.patterns_table.setEditTriggers(QTableWidget.NoEditTriggers)
            
            self.log_manager.info(f"成功更新形态表格，共 {len(patterns)} 条记录")
            
        except Exception as e:
            self.log_manager.error(f"更新形态表格失败: {e}")
            import traceback
            self.log_manager.error(traceback.format_exc())
    
    """

        # 替换方法
        updated_content = content.replace(old_method, new_method)

        # 写入更新后的内容
        with open(pattern_tab_pro_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        logger.info("成功完全重写_update_patterns_table方法")
        return True

    except Exception as e:
        logger.error(f"修复表格显示失败: {e}")
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=== 开始最终修复形态表格显示问题 ===")

    # 修复表格显示
    success = fix_table_display()

    if success:
        logger.info("=== 修复成功！请重启应用验证效果 ===")
    else:
        logger.error("=== 修复失败，请检查日志 ===")


if __name__ == "__main__":
    main()
