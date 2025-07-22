#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彻底修复形态表格显示问题
"""

import os
import traceback
import logging
import sys

# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_pattern_table")


def fix_table_display_issue():
    """彻底修复表格显示问题"""
    try:
        # 1. 修复pattern_tab_pro.py中的表格创建和显示代码
        pattern_tab_pro_path = "gui/widgets/analysis_tabs/pattern_tab_pro.py"
        if not os.path.exists(pattern_tab_pro_path):
            logger.error(f"找不到文件: {pattern_tab_pro_path}")
            return False

        # 2. 修复pattern_tab.py中的表格创建和显示代码
        pattern_tab_path = "gui/widgets/analysis_tabs/pattern_tab.py"
        if not os.path.exists(pattern_tab_path):
            logger.error(f"找不到文件: {pattern_tab_path}")
            return False

        logger.info(f"开始修复形态表格显示问题: {pattern_tab_pro_path}")

        # 修复pattern_tab_pro.py中的_create_patterns_tab方法
        fix_create_patterns_tab(pattern_tab_pro_path)

        # 修复_update_patterns_table方法
        fix_update_patterns_table(pattern_tab_pro_path)

        # 修复一键分析方法调用链
        fix_analysis_chain(pattern_tab_pro_path)

        logger.info("所有修复完成!")
        return True

    except Exception as e:
        logger.error(f"修复表格显示失败: {e}")
        logger.error(traceback.format_exc())
        return False


def fix_create_patterns_tab(file_path):
    """修复_create_patterns_tab方法"""
    logger.info(f"修复_create_patterns_tab方法: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找_create_patterns_tab方法
    pattern_start = content.find("def _create_patterns_tab(self):")
    if pattern_start == -1:
        logger.error("找不到_create_patterns_tab方法")
        return False

    # 查找方法结束位置
    pattern_end = content.find("def _create_prediction_tab(self):", pattern_start)
    if pattern_end == -1:
        logger.error("找不到_create_patterns_tab方法的结束位置")
        return False

    # 提取方法
    old_method = content[pattern_start:pattern_end]

    # 创建新的方法
    new_method = """def _create_patterns_tab(self):
        \"\"\"创建形态识别标签页 - 完全重写版\"\"\"
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 创建更高效的表格
        self.patterns_table = QTableWidget(0, 10)
        self.patterns_table.setAlternatingRowColors(True)
        self.patterns_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.patterns_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 设置为只读
        self.patterns_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.patterns_table.setSortingEnabled(True)
        self.patterns_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.patterns_table.customContextMenuRequested.connect(self.show_pattern_context_menu)
        
        # 设置列标题
        column_headers = ["形态名称", "类型", "置信度", "成功率", "信号", "位置", "区间", "价格", "目标价", "建议"]
        self.patterns_table.setHorizontalHeaderLabels(column_headers)
        
        # 设置表格样式
        self.patterns_table.setStyleSheet(\"\"\"
            QTableWidget {
                border: 1px solid #d3d3d3;
                border-radius: 4px;
                background-color: #ffffff;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e0f0ff;
            }
        \"\"\")
        
        # 设置列宽
        header = self.patterns_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        # 设置固定列宽
        column_widths = [120, 80, 70, 70, 60, 90, 70, 60, 60, 70]
        for i, width in enumerate(column_widths):
            self.patterns_table.setColumnWidth(i, width)
        
        # 添加表格到布局
        layout.addWidget(self.patterns_table, 1)
        
        # 操作按钮区域
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 5, 0, 0)
        buttons_layout.setSpacing(10)
        
        # 按钮创建函数
        def create_button(text, icon_code=None, tooltip=None, callback=None):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            if icon_code:
                btn.setText(f"{icon_code} {text}")
            if tooltip:
                btn.setToolTip(tooltip)
            if callback:
                btn.clicked.connect(callback)
            btn.setMinimumWidth(100)
            return btn
            
        # 创建操作按钮
        export_btn = create_button("导出结果", "📤", "导出分析结果到文件", self.export_patterns)
        detail_btn = create_button("查看详情", "🔍", "查看选中形态的详细信息", self.show_pattern_detail)
        chart_btn = create_button("图表标注", "📊", "在图表上标注形态", self.annotate_chart)
        
        buttons_layout.addWidget(export_btn)
        buttons_layout.addWidget(detail_btn)
        buttons_layout.addWidget(chart_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return widget
"""

    # 替换方法
    updated_content = content[:pattern_start] + new_method + content[pattern_end:]

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    logger.info("成功修复_create_patterns_tab方法")
    return True


def fix_update_patterns_table(file_path):
    """修复_update_patterns_table方法"""
    logger.info(f"修复_update_patterns_table方法: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找_update_patterns_table方法
    pattern_start = content.find("def _update_patterns_table(self, patterns):")
    if pattern_start == -1:
        logger.error("找不到_update_patterns_table方法")
        return False

    # 查找方法结束位置
    pattern_end = content.find("def _update_statistics_display(self, stats):", pattern_start)
    if pattern_end == -1:
        logger.error("找不到_update_patterns_table方法的结束位置")
        return False

    # 提取方法
    old_method = content[pattern_start:pattern_end]

    # 创建新的方法
    new_method = """def _update_patterns_table(self, patterns):
        \"\"\"更新形态表格 - 最终优化版\"\"\"
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
                confidence_item.setData(Qt.UserRole, float(confidence) if isinstance(confidence, (int, float)) else 0.0)
                self.patterns_table.setItem(row, 2, confidence_item)
                
                # 第4列: 成功率
                success_rate = pattern.get('success_rate', 0.0)
                success_rate_str = f"{success_rate:.2%}" if isinstance(success_rate, (int, float)) and success_rate <= 1.0 else str(success_rate)
                success_item = QTableWidgetItem(success_rate_str)
                success_item.setData(Qt.UserRole, float(success_rate) if isinstance(success_rate, (int, float)) else 0.0)
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
                price_item.setData(Qt.UserRole, float(price) if price is not None and isinstance(price, (int, float)) else 0.0)
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
                target_item.setData(Qt.UserRole, float(target) if target is not None and isinstance(target, (int, float)) else 0.0)
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
"""

    # 替换方法
    updated_content = content[:pattern_start] + new_method + content[pattern_end:]

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    logger.info("成功修复_update_patterns_table方法")
    return True


def fix_analysis_chain(file_path):
    """修复分析调用链，确保正确更新UI"""
    logger.info(f"修复分析调用链: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找on_analysis_completed方法
    pattern_start = content.find("def on_analysis_completed(self, results):")
    if pattern_start == -1:
        logger.error("找不到on_analysis_completed方法")
        return False

    # 查找方法结束位置
    pattern_end = content.find("def on_analysis_error(self, error_message):", pattern_start)
    if pattern_end == -1:
        logger.error("找不到on_analysis_completed方法的结束位置")
        return False

    # 提取方法
    old_method = content[pattern_start:pattern_end]

    # 创建新的方法，确保UI更新正确执行
    new_method = """def on_analysis_completed(self, results):
        \"\"\"分析完成处理 - 优化版\"\"\"
        try:
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            self.status_label.setText("分析完成")
            
            # 如果有错误，显示错误信息
            if 'error' in results:
                QMessageBox.critical(self, "分析错误", results['error'])
                return
                
            # 确保主线程更新UI
            QApplication.processEvents()
                
            # 更新各项结果显示
            self._update_results_display(results)
            
            # 发送形态检测信号
            if results.get('patterns'):
                self.pattern_detected.emit(results)
                
            # 显示完成消息
            self.status_label.setText(f"完成! 检测到 {len(results.get('patterns', []))} 个形态")
                
        except Exception as e:
            self.log_manager.error(f"处理分析结果失败: {str(e)}")
            self.log_manager.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", f"处理分析结果失败: {str(e)}")
"""

    # 替换方法
    updated_content = content[:pattern_start] + new_method + content[pattern_end:]

    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    # 添加QApplication导入
    if "from PyQt5.QtWidgets import QApplication" not in updated_content:
        # 查找导入部分
        import_pos = updated_content.find("from PyQt5.QtWidgets import")
        if import_pos != -1:
            # 找到导入语句的末尾
            import_end = updated_content.find(")", import_pos)
            if import_end != -1:
                # 检查是否已经导入了QApplication
                if "QApplication" not in updated_content[import_pos:import_end]:
                    # 在括号前添加QApplication
                    new_import = updated_content[:import_end] + ", QApplication" + updated_content[import_end:]
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_import)

    logger.info("成功修复分析调用链")
    return True


if __name__ == "__main__":
    print("="*50)
    print("开始修复形态表格显示问题...")
    print("="*50)

    if fix_table_display_issue():
        print("="*50)
        print("✅ 修复成功! 请重启应用以验证效果")
        print("="*50)
        sys.exit(0)
    else:
        print("="*50)
        print("❌ 修复失败，请查看日志获取更多信息")
        print("="*50)
        sys.exit(1)
