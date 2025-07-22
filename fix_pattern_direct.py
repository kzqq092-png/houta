#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接修复pattern_tab_pro.py中的_update_patterns_table方法，解决只显示形态名称的问题
"""

import os
import sys


def direct_fix():
    """直接替换_update_patterns_table方法"""
    file_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"

    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return False

    print(f"开始直接修复文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找_update_patterns_table方法
    method_start = content.find("def _update_patterns_table(self, patterns):")
    if method_start == -1:
        print("错误: 未找到_update_patterns_table方法")
        return False

    # 找到方法结束位置
    method_end = content.find("    def _update_statistics_display(self, stats):", method_start)
    if method_end == -1:
        print("错误: 未找到方法结束位置")
        return False

    # 提取原方法
    original_method = content[method_start:method_end]
    print(f"找到原方法，长度: {len(original_method)} 字符")

    # 替换方法
    new_method = '''    def _update_patterns_table(self, patterns):
        """更新形态表格 - 最终直接修复版"""
        try:
            # 清空表格并暂停排序
            self.patterns_table.setSortingEnabled(False)
            self.patterns_table.setRowCount(0)
            
            # 如果没有形态，显示提示信息
            if not patterns:
                self.log_manager.warning("没有检测到形态")
                self.patterns_table.setRowCount(1)
                self.patterns_table.setItem(0, 0, QTableWidgetItem("未检测到形态"))
                for col in range(1, self.patterns_table.columnCount()):
                    self.patterns_table.setItem(0, col, QTableWidgetItem(""))
                return
            
            # 输出调试信息
            self.log_manager.info(f"收到 {len(patterns)} 个形态数据")
            if patterns and isinstance(patterns[0], dict):
                self.log_manager.info(f"第一个形态数据的键: {list(patterns[0].keys())}")
                self.log_manager.info(f"第一个形态数据的值: {patterns[0]}")
            
            # 去重处理
            unique_patterns = []
            seen_keys = set()
            
            for pattern in patterns:
                if not isinstance(pattern, dict):
                    continue
                    
                # 创建唯一键
                key = f"{pattern.get('type', pattern.get('pattern_name', ''))}-{pattern.get('index', -1)}"
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_patterns.append(pattern)
            
            self.log_manager.info(f"去重后剩余 {len(unique_patterns)} 个形态")
            patterns = unique_patterns
            
            # 设置表格行数
            self.patterns_table.setRowCount(len(patterns))
            
            # 填充表格数据
            for row, pattern in enumerate(patterns):
                # 第1列: 形态名称
                name = pattern.get('pattern_name', pattern.get('name', pattern.get('type', '未知形态')))
                self.patterns_table.setItem(row, 0, QTableWidgetItem(str(name)))
                
                # 第2列: 类型
                category = pattern.get('pattern_category', pattern.get('category', ''))
                if hasattr(category, 'value'):
                    category = category.value
                self.patterns_table.setItem(row, 1, QTableWidgetItem(str(category)))
                
                # 第3列: 置信度
                confidence = pattern.get('confidence', 0.0)
                confidence_str = f"{confidence:.2%}" if isinstance(confidence, (int, float)) else str(confidence)
                confidence_item = QTableWidgetItem(confidence_str)
                if isinstance(confidence, (int, float)):
                    confidence_item.setData(Qt.UserRole, float(confidence))
                self.patterns_table.setItem(row, 2, confidence_item)
                
                # 第4列: 成功率
                success_rate = pattern.get('success_rate', 0.0)
                success_rate_str = f"{success_rate:.2%}" if isinstance(success_rate, (int, float)) and success_rate <= 1.0 else str(success_rate)
                success_item = QTableWidgetItem(success_rate_str)
                if isinstance(success_rate, (int, float)):
                    success_item.setData(Qt.UserRole, float(success_rate))
                self.patterns_table.setItem(row, 3, success_item)
                
                # 第5列: 信号
                signal = pattern.get('signal', '')
                signal_str = "买入" if signal == "buy" else "卖出" if signal == "sell" else "中性"
                signal_item = QTableWidgetItem(signal_str)
                if signal == "buy":
                    signal_item.setForeground(QColor(255, 0, 0))  # 红色买入信号
                    signal_item.setBackground(QColor(255, 240, 240))  # 浅红色背景
                elif signal == "sell":
                    signal_item.setForeground(QColor(0, 128, 0))  # 绿色卖出信号
                    signal_item.setBackground(QColor(240, 255, 240))  # 浅绿色背景
                self.patterns_table.setItem(row, 4, signal_item)
                
                # 第6列: 位置
                index = pattern.get('index')
                datetime_val = pattern.get('datetime')
                position_str = str(datetime_val) if datetime_val else f"K线#{index}" if index is not None else ""
                self.patterns_table.setItem(row, 5, QTableWidgetItem(position_str))
                
                # 第7列: 区间
                start = pattern.get('start_index')
                end = pattern.get('end_index')
                range_str = f"{start}-{end}" if start is not None and end is not None else ""
                self.patterns_table.setItem(row, 6, QTableWidgetItem(range_str))
                
                # 第8列: 价格
                price = pattern.get('price')
                price_str = f"{price:.2f}" if price is not None and isinstance(price, (int, float)) else ""
                price_item = QTableWidgetItem(price_str)
                if price is not None and isinstance(price, (int, float)):
                    price_item.setData(Qt.UserRole, float(price))
                self.patterns_table.setItem(row, 7, price_item)
                
                # 第9列: 目标价
                target = pattern.get('target_price')
                if target is None and price is not None and isinstance(price, (int, float)):
                    # 如果没有目标价格，使用信号预测
                    if signal == "buy":
                        target = price * 1.05  # 上涨5%
                    elif signal == "sell":
                        target = price * 0.95  # 下跌5%
                target_str = f"{target:.2f}" if target is not None and isinstance(target, (int, float)) else ""
                target_item = QTableWidgetItem(target_str)
                if target is not None and isinstance(target, (int, float)):
                    target_item.setData(Qt.UserRole, float(target))
                self.patterns_table.setItem(row, 8, target_item)
                
                # 第10列: 建议
                if signal == "buy":
                    recommendation = "建议买入"
                elif signal == "sell":
                    recommendation = "建议卖出"
                else:
                    recommendation = "观望"
                self.patterns_table.setItem(row, 9, QTableWidgetItem(recommendation))
                
                # 设置风险等级行背景色
                risk_level = pattern.get('risk_level', '').lower()
                if risk_level == 'high':
                    for col in range(self.patterns_table.columnCount()):
                        item = self.patterns_table.item(row, col)
                        if item and col != 4:  # 不覆盖信号列的颜色
                            item.setBackground(QColor(255, 230, 230))  # 浅红色
                elif risk_level == 'low':
                    for col in range(self.patterns_table.columnCount()):
                        item = self.patterns_table.item(row, col)
                        if item and col != 4:  # 不覆盖信号列的颜色
                            item.setBackground(QColor(230, 255, 230))  # 浅绿色
            
            # 恢复排序功能
            self.patterns_table.setSortingEnabled(True)
            # 默认按置信度降序排序
            self.patterns_table.sortByColumn(2, Qt.DescendingOrder)
            
            # 调整列宽以适应内容
            self.patterns_table.resizeColumnsToContents()
            
            self.log_manager.info(f"成功更新形态表格，共 {len(patterns)} 条记录")
            
        except Exception as e:
            self.log_manager.error(f"更新形态表格失败: {e}")
            self.log_manager.error(traceback.format_exc())
'''

    # 替换内容
    new_content = content[:method_start] + new_method + content[method_end:]

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"成功直接修复 _update_patterns_table 方法")
    return True


if __name__ == "__main__":
    print("="*60)
    print("开始直接修复表格显示问题...")
    print("="*60)

    if direct_fix():
        print("="*60)
        print("✅ 修复成功! 请重启应用验证效果")
        print("="*60)
        sys.exit(0)
    else:
        print("="*60)
        print("❌ 修复失败! 请查看错误信息")
        print("="*60)
        sys.exit(1)
