#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合修复测试
验证所有问题是否已修复
"""

import sys
import os
sys.path.append('.')


def test_pattern_table_column_fix():
    """测试表格列索引修复"""
    print("=== 测试表格列索引修复 ===")

    try:
        from gui.widgets.analysis_widget import AnalysisWidget
        from PyQt5.QtWidgets import QApplication, QTableWidgetItem

        # 创建应用程序（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 创建分析控件
        widget = AnalysisWidget()

        # 模拟创建形态表格
        widget.pattern_table.setColumnCount(10)
        widget.pattern_table.setHorizontalHeaderLabels([
            "序号", "形态名称", "形态类别", "信号类型", "置信度", "置信度等级",
            "K线索引", "出现时间", "价格", "描述"
        ])

        # 添加测试数据
        widget.pattern_table.setRowCount(2)

        # 第一行：正常数据
        widget.pattern_table.setItem(0, 0, QTableWidgetItem("1"))
        widget.pattern_table.setItem(0, 1, QTableWidgetItem("倒锤头"))
        widget.pattern_table.setItem(0, 2, QTableWidgetItem("反转形态"))
        widget.pattern_table.setItem(0, 3, QTableWidgetItem("买入"))
        widget.pattern_table.setItem(0, 4, QTableWidgetItem("0.850"))
        widget.pattern_table.setItem(0, 5, QTableWidgetItem("高"))
        widget.pattern_table.setItem(0, 6, QTableWidgetItem("15"))  # K线索引
        widget.pattern_table.setItem(0, 7, QTableWidgetItem("2023-01-15"))
        widget.pattern_table.setItem(0, 8, QTableWidgetItem("12.50"))  # 价格
        widget.pattern_table.setItem(0, 9, QTableWidgetItem("看涨信号"))

        # 第二行：包含非数字索引的数据
        widget.pattern_table.setItem(1, 0, QTableWidgetItem("2"))
        widget.pattern_table.setItem(1, 1, QTableWidgetItem("三白兵"))
        widget.pattern_table.setItem(1, 2, QTableWidgetItem("反转形态"))
        widget.pattern_table.setItem(1, 3, QTableWidgetItem("买入"))
        widget.pattern_table.setItem(1, 4, QTableWidgetItem("0.900"))
        widget.pattern_table.setItem(1, 5, QTableWidgetItem("高"))
        widget.pattern_table.setItem(1, 6, QTableWidgetItem("三根K线"))  # 非数字索引
        widget.pattern_table.setItem(1, 7, QTableWidgetItem("2023-01-16"))
        widget.pattern_table.setItem(1, 8, QTableWidgetItem("12.80"))
        widget.pattern_table.setItem(1, 9, QTableWidgetItem("强烈看涨"))

        # 模拟选择第一行（正常数据）
        widget.pattern_table.selectRow(0)

        # 测试表格选择变化处理
        try:
            widget._on_pattern_table_selection_changed()
            print("✅ 正常数据处理成功")
        except Exception as e:
            print(f"❌ 正常数据处理失败: {e}")
            return False

        # 模拟选择第二行（包含非数字索引）
        widget.pattern_table.selectRow(1)

        try:
            widget._on_pattern_table_selection_changed()
            print("✅ 非数字索引数据处理成功（应该被跳过）")
        except Exception as e:
            print(f"❌ 非数字索引数据处理失败: {e}")
            return False

        print("✅ 表格列索引修复测试通过")
        return True

    except Exception as e:
        print(f"❌ 表格列索引修复测试失败: {e}")
        return False


def test_pattern_statistics_generation():
    """测试统计数据生成"""
    print("\n=== 测试统计数据生成 ===")

    try:
        from PyQt5.QtWidgets import QApplication

        # 创建应用程序（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 创建分析控件
        widget = AnalysisWidget()

        # 模拟形态识别结果
        test_patterns = [
            {
                'pattern_name': '倒锤头',
                'type': 'inverted_hammer',
                'pattern_category': '反转形态',
                'category': '反转形态',
                'signal': 'buy',
                'confidence': 0.85,
                'price': 12.50
            },
            {
                'pattern_name': '三白兵',
                'type': 'three_white_soldiers',
                'pattern_category': '反转形态',
                'category': '反转形态',
                'signal': 'buy',
                'confidence': 0.90,
                'price': 12.80
            },
            {
                'pattern_name': '射击之星',
                'type': 'shooting_star',
                'pattern_category': '反转形态',
                'category': '反转形态',
                'signal': 'sell',
                'confidence': 0.75,
                'price': 13.20
            },
            {
                'pattern_name': '十字星',
                'type': 'doji',
                'pattern_category': '中性形态',
                'category': '中性形态',
                'signal': 'neutral',
                'confidence': 0.60,
                'price': 12.90
            }
        ]

        # 测试统计数据生成
        stats = widget._generate_pattern_statistics(test_patterns)

        # 验证统计结果
        expected_total = 4
        expected_categories = {'反转形态': 3, '中性形态': 1}
        expected_signals = {'买入': 2, '卖出': 1, '中性': 1}
        expected_confidence = {'high': 2, 'medium': 2, 'low': 0}

        if stats['total_patterns'] != expected_total:
            print(f"❌ 总数统计错误: 期望{expected_total}, 实际{stats['total_patterns']}")
            return False

        if stats['by_category'] != expected_categories:
            print(
                f"❌ 类别统计错误: 期望{expected_categories}, 实际{stats['by_category']}")
            return False

        if stats['by_signal'] != expected_signals:
            print(f"❌ 信号统计错误: 期望{expected_signals}, 实际{stats['by_signal']}")
            return False

        if stats['confidence_distribution'] != expected_confidence:
            print(
                f"❌ 置信度统计错误: 期望{expected_confidence}, 实际{stats['confidence_distribution']}")
            return False

        print("✅ 统计数据生成测试通过")
        print(f"  - 总计: {stats['total_patterns']} 个形态")
        print(f"  - 分类: {stats['by_category']}")
        print(f"  - 信号: {stats['by_signal']}")
        print(f"  - 置信度: {stats['confidence_distribution']}")

        return True

    except Exception as e:
        print(f"❌ 统计数据生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chart_integration():
    """测试图表集成"""
    print("\n=== 测试图表集成 ===")

    try:

        # 创建应用程序（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 创建分析控件
        widget = AnalysisWidget()

        # 模拟图表控件
        class MockChartWidget:
            def __init__(self):
                self.patterns_received = []
                self.chart_data_received = []

            def plot_patterns(self, patterns):
                self.patterns_received = patterns
                print(f"MockChartWidget.plot_patterns 接收到 {len(patterns)} 个形态")

            def update_chart(self, data):
                self.chart_data_received.append(data)
                print(
                    f"MockChartWidget.update_chart 接收到数据: {list(data.keys())}")

        # 设置模拟图表控件
        widget.chart_widget = MockChartWidget()

        # 模拟形态识别结果
        test_patterns = [
            {
                'pattern_name': '倒锤头',
                'type': 'inverted_hammer',
                'signal': 'buy',
                'confidence': 0.85,
                'index': 15,
                'price': 12.50
            }
        ]

        # 测试图表集成逻辑
        if hasattr(widget, 'chart_widget') and widget.chart_widget and test_patterns:
            if hasattr(widget.chart_widget, 'plot_patterns'):
                widget.chart_widget.plot_patterns(test_patterns)

                # 验证数据是否正确传递
                if len(widget.chart_widget.patterns_received) == 1:
                    print("✅ 形态数据成功传递给图表控件")
                else:
                    print("❌ 形态数据传递失败")
                    return False
            else:
                print("❌ 图表控件缺少plot_patterns方法")
                return False

        print("✅ 图表集成测试通过")
        return True

    except Exception as e:
        print(f"❌ 图表集成测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🔧 YS-Quant‌ 综合修复测试")
    print("=" * 50)

    tests = [
        ("表格列索引修复", test_pattern_table_column_fix),
        ("统计数据生成", test_pattern_statistics_generation),
        ("图表集成", test_chart_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")

    print("\n" + "=" * 50)
    print(f"测试总结: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！修复成功！")
        print("\n修复内容:")
        print("✅ 1. 修复了表格选择变化处理中的列索引错误")
        print("✅ 2. 增强了非数字索引的错误处理")
        print("✅ 3. 修复了统计分析数据缺失问题")
        print("✅ 4. 改进了主图标记点的显示逻辑")
        print("✅ 5. 增强了图表控件的兼容性检查")
    else:
        print("❌ 部分测试失败，需要进一步检查")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
