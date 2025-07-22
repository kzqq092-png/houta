#!/usr/bin/env python
"""
形态识别修复验证脚本 - 直接调用和测试修复后的代码
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback


def create_test_data(include_duplicates=True):
    """创建测试用的K线数据，可选择是否包含重复形态"""
    # 生成日期序列
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

    # 创建测试数据
    data = {
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(12, 22, 100),
        'low': np.random.uniform(9, 19, 100),
        'close': np.random.uniform(10, 20, 100),
        'volume': np.random.uniform(1000, 10000, 100),
        'datetime': dates
    }

    # 确保high >= max(open, close)，low <= min(open, close)
    for i in range(100):
        data['high'][i] = max(data['open'][i], data['close'][i], data['high'][i])
        data['low'][i] = min(data['open'][i], data['close'][i], data['low'][i])

    # 创建DataFrame
    df = pd.DataFrame(data, index=dates)

    # 添加典型的K线形态
    create_patterns(df)

    # 如果需要，创建一些重复的形态数据
    if include_duplicates:
        create_duplicate_patterns(df)

    return df


def create_patterns(df):
    """创建一些典型的K线形态"""
    # 1. 三白兵 (连续三根阳线)
    for i in range(50, 53):
        df.loc[df.index[i], 'open'] = 15.0
        df.loc[df.index[i], 'close'] = 17.0 + (i - 50) * 0.5
        df.loc[df.index[i], 'high'] = df.loc[df.index[i], 'close'] + 0.3
        df.loc[df.index[i], 'low'] = df.loc[df.index[i], 'open'] - 0.3

    # 2. 锤子线
    df.loc[df.index[60], 'open'] = 16.0
    df.loc[df.index[60], 'close'] = 16.2
    df.loc[df.index[60], 'high'] = 16.3
    df.loc[df.index[60], 'low'] = 14.5

    # 3. 看涨吞没
    df.loc[df.index[70], 'open'] = 17.0
    df.loc[df.index[70], 'close'] = 16.0
    df.loc[df.index[70], 'high'] = 17.2
    df.loc[df.index[70], 'low'] = 15.8

    df.loc[df.index[71], 'open'] = 15.8
    df.loc[df.index[71], 'close'] = 17.3
    df.loc[df.index[71], 'high'] = 17.5
    df.loc[df.index[71], 'low'] = 15.6

    # 4. 十字星
    df.loc[df.index[80], 'open'] = 18.0
    df.loc[df.index[80], 'close'] = 18.0
    df.loc[df.index[80], 'high'] = 18.5
    df.loc[df.index[80], 'low'] = 17.5


def create_duplicate_patterns(df):
    """模拟重复形态数据 - 故意添加一些数据不完整的条目"""
    # 十字星变种 - 同样的位置和形态，但数据格式不同
    df.loc[df.index[80], 'open'] = 18.01  # 轻微改变让形态仍然成立
    df.loc[df.index[80], 'close'] = 18.01

    # 流星线形态 - 在几个相邻位置，看起来像是重复
    for i in range(90, 95):
        df.loc[df.index[i], 'open'] = 19.0
        df.loc[df.index[i], 'close'] = 18.5
        df.loc[df.index[i], 'high'] = 20.0
        df.loc[df.index[i], 'low'] = 18.2


def test_pattern_detection_chain():
    """测试整个形态识别链路"""
    print("=" * 80)
    print("测试形态识别链路")
    print("=" * 80)

    try:
        # 创建测试数据
        test_data = create_test_data()
        print(f"创建测试数据成功，共{len(test_data)}条")

        # 导入形态管理器
        from analysis.pattern_manager import PatternManager
        manager = PatternManager()

        # 执行形态识别
        patterns = manager.identify_all_patterns(test_data, confidence_threshold=0.3)

        # 分析结果
        print(f"\n识别结果分析:")
        print(f"- 识别到的形态总数: {len(patterns)}")

        # 检查重复情况
        pattern_types = {}
        pattern_indices = {}

        for p in patterns:
            # 统计形态类型
            pattern_name = p.get('pattern_name', 'unknown')
            pattern_types[pattern_name] = pattern_types.get(pattern_name, 0) + 1

            # 检查索引位置
            idx = p.get('index', -1)
            if idx in pattern_indices:
                pattern_indices[idx].append(pattern_name)
            else:
                pattern_indices[idx] = [pattern_name]

        # 输出形态类型统计
        print("\n形态类型分布:")
        for ptype, count in pattern_types.items():
            print(f"  {ptype}: {count}个")

        # 输出可能的重复位置
        print("\n位置分析:")
        duplicate_positions = {k: v for k, v in pattern_indices.items() if len(v) > 1}
        if duplicate_positions:
            print(f"发现{len(duplicate_positions)}个位置有多个形态:")
            for pos, ptypes in duplicate_positions.items():
                print(f"  位置 {pos}: {', '.join(ptypes)}")
        else:
            print("  没有发现同一位置上的多个形态")

        # 检查数据完整性
        print("\n数据完整性检查:")
        missing_fields = 0
        for p in patterns:
            required_fields = ['pattern_name', 'type', 'signal', 'confidence', 'index', 'price']
            missing = [f for f in required_fields if f not in p or p[f] is None]
            if missing:
                missing_fields += 1
                if missing_fields <= 3:  # 只显示前3个
                    print(f"  发现缺失字段的形态: {missing}")

        if missing_fields > 0:
            print(f"  总共有{missing_fields}个形态缺少必要字段")
        else:
            print("  所有形态数据完整")

        return patterns

    except Exception as e:
        print(f"测试失败: {e}")
        print(traceback.format_exc())
        return []


def test_ui_rendering(patterns):
    """测试UI渲染 - 模拟pattern_tab的表格更新逻辑"""
    print("\n" + "=" * 80)
    print("测试UI渲染逻辑")
    print("=" * 80)

    try:
        # 导入测试所需的模块
        import sys
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
        from PyQt5.QtGui import QColor, QBrush

        # 创建一个最小的QApplication实例
        app = QApplication.instance() or QApplication(sys.argv)

        # 创建表格组件
        table = QTableWidget(0, 10)
        table.setHorizontalHeaderLabels([
            '形态名称', '类型', '置信度', '成功率', '信号',
            '位置', '区间', '价格', '目标价', '建议'
        ])

        # 使用独立的更新函数来测试表格渲染逻辑
        def update_table(table, patterns):
            """模拟_update_patterns_table方法的逻辑"""
            if not patterns:
                table.setRowCount(1)
                table.setItem(0, 0, QTableWidgetItem("未检测到形态"))
                for col in range(1, table.columnCount()):
                    table.setItem(0, col, QTableWidgetItem(""))
                return

            # 预处理：过滤无效数据并进行更强的去重
            valid_patterns = []
            seen_keys = {}  # 使用字典保存每个形态的最高置信度版本

            for pattern in patterns:
                if not isinstance(pattern, dict):
                    continue

                # 确保必要字段存在
                if 'pattern_name' not in pattern and 'type' not in pattern:
                    continue

                # 提取形态名称
                pattern_name = pattern.get('pattern_name', pattern.get('name', pattern.get('type', '未知形态')))

                # 使用更严格的去重方式 - 每种形态只保留最高置信度的一个
                confidence = pattern.get('confidence', 0)

                # 如果是新形态类型或比现有的更高置信度，则替换
                if pattern_name not in seen_keys or confidence > seen_keys[pattern_name][0]:
                    seen_keys[pattern_name] = (confidence, pattern)

            # 只保留每种形态的最高置信度版本
            valid_patterns = [p for _, p in seen_keys.values()]

            # 按置信度排序
            valid_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)

            # 设置表格行数
            table.setRowCount(len(valid_patterns))

            # 填充表格数据
            for row, pattern in enumerate(valid_patterns):
                # 1. 形态名称
                pattern_name = pattern.get('pattern_name', pattern.get('name', pattern.get('type', '未知形态')))
                table.setItem(row, 0, QTableWidgetItem(str(pattern_name)))

                # 2. 类型
                category = pattern.get('pattern_category', pattern.get('category', '未分类'))
                if hasattr(category, 'value'):
                    category = category.value
                table.setItem(row, 1, QTableWidgetItem(str(category)))

                # 3. 置信度
                confidence = pattern.get('confidence', 0.5)
                if isinstance(confidence, (int, float)):
                    confidence_str = f"{confidence:.2%}"
                else:
                    confidence_str = str(confidence)
                table.setItem(row, 2, QTableWidgetItem(confidence_str))

                # 4. 成功率
                success_rate = pattern.get('success_rate', 0.7)
                if isinstance(success_rate, (int, float)):
                    success_rate_str = f"{success_rate:.2%}" if success_rate <= 1 else f"{success_rate}%"
                else:
                    success_rate_str = str(success_rate)
                table.setItem(row, 3, QTableWidgetItem(success_rate_str))

                # 5. 信号
                signal = pattern.get('signal', '')
                signal_str = "买入" if signal == "buy" else "卖出" if signal == "sell" else "中性"
                table.setItem(row, 4, QTableWidgetItem(signal_str))

                # 6. 位置
                index = pattern.get('index')
                datetime_val = pattern.get('datetime')
                if datetime_val:
                    position_str = str(datetime_val)[:10]
                elif index is not None:
                    position_str = f"K线#{index}"
                else:
                    position_str = "未知位置"  # 确保没有空位置
                table.setItem(row, 5, QTableWidgetItem(position_str))

                # 7. 区间
                start_index = pattern.get('start_index')
                end_index = pattern.get('end_index')
                if start_index is not None and end_index is not None:
                    range_str = f"{start_index}-{end_index}"
                else:
                    range_str = "单点"  # 默认值不为空
                table.setItem(row, 6, QTableWidgetItem(range_str))

                # 8. 价格
                price = pattern.get('price')
                if price is not None and isinstance(price, (int, float)):
                    price_str = f"{price:.2f}"
                else:
                    price_str = "0.00"  # 确保不为空
                table.setItem(row, 7, QTableWidgetItem(price_str))

                # 9. 目标价
                target_price = pattern.get('target_price')
                if target_price is None and price is not None and isinstance(price, (int, float)):
                    if signal == "buy":
                        target_price = price * 1.05
                    elif signal == "sell":
                        target_price = price * 0.95
                    else:
                        target_price = price  # 中性信号

                if target_price is not None and isinstance(target_price, (int, float)):
                    target_price_str = f"{target_price:.2f}"
                else:
                    target_price_str = "0.00"  # 确保不为空
                table.setItem(row, 8, QTableWidgetItem(target_price_str))

                # 10. 建议
                if signal == "buy":
                    recommendation = "建议买入"
                elif signal == "sell":
                    recommendation = "建议卖出"
                else:
                    recommendation = "观望"
                table.setItem(row, 9, QTableWidgetItem(recommendation))

                return valid_patterns

        # 执行表格更新测试
        valid_patterns = update_table(table, patterns)

        # 分析渲染结果
        print(f"\n表格渲染分析:")
        print(f"- 有效形态数量: {len(valid_patterns)}")
        print(f"- 表格行数: {table.rowCount()}")

        # 检查表格中的值
        empty_cells = 0
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if not item or not item.text():
                    empty_cells += 1

        print(f"- 空单元格数量: {empty_cells}")
        print(f"- 空单元格占比: {empty_cells / (table.rowCount() * table.columnCount()):.2%}")

        # 检查表格中是否有重复形态
        pattern_names = []
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            if name_item:
                pattern_names.append(name_item.text())

        duplicate_names = set([name for name in pattern_names if pattern_names.count(name) > 1])
        if duplicate_names:
            print(f"- 警告: 表格中发现重复形态名称: {duplicate_names}")
        else:
            print(f"- 表格中没有重复的形态名称")

        print("\n表格前5行内容预览:")
        for row in range(min(5, table.rowCount())):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                text = item.text() if item else ""
                row_data.append(text)
            print(f"  行 {row+1}: {' | '.join(row_data)}")

        return True

    except Exception as e:
        print(f"UI渲染测试失败: {e}")
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    # 测试形态识别链路
    patterns = test_pattern_detection_chain()

    # 测试UI渲染
    if patterns:
        test_ui_rendering(patterns)

    print("\n验证测试完成!")
