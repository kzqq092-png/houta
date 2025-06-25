#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试涨跌颜色功能
验证change_color状态设置涨跌文本颜色的功能
"""

import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gui.widgets.chart_widget import ChartWidget
    from utils.theme_utils import ThemeManager
    from core.logger import LogManager
    print("✓ 成功导入必要模块")
except ImportError as e:
    print(f"✗ 导入模块失败: {e}")
    sys.exit(1)


class TestChangeColorWindow(QMainWindow):
    """测试涨跌颜色功能的窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试涨跌颜色功能")
        self.setGeometry(100, 100, 1200, 800)

        # 初始化管理器
        self.theme_manager = ThemeManager()
        self.log_manager = LogManager()

        # 设置中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建图表控件
        self.chart_widget = ChartWidget(
            parent=self,
            theme_manager=self.theme_manager,
            log_manager=self.log_manager
        )
        layout.addWidget(self.chart_widget)

        # 生成测试数据
        self.generate_test_data()

        print("✓ 测试窗口初始化完成")

    def generate_test_data(self):
        """生成包含涨跌情况的测试K线数据"""
        try:
            # 生成50个交易日的数据
            dates = pd.date_range('2024-01-01', periods=50, freq='D')

            # 初始价格
            base_price = 100.0
            prices = []

            # 生成有涨有跌的价格序列
            for i in range(50):
                if i == 0:
                    prices.append(base_price)
                else:
                    # 随机涨跌，制造明显的涨跌情况
                    if i % 10 < 3:  # 30%概率大涨
                        change_pct = np.random.uniform(2, 8)
                    elif i % 10 < 6:  # 30%概率大跌
                        change_pct = np.random.uniform(-8, -2)
                    elif i % 10 < 8:  # 20%概率小涨
                        change_pct = np.random.uniform(0.1, 2)
                    elif i % 10 < 9:  # 10%概率小跌
                        change_pct = np.random.uniform(-2, -0.1)
                    else:  # 10%概率平盘
                        change_pct = 0

                    new_price = prices[-1] * (1 + change_pct / 100)
                    prices.append(new_price)

            # 生成完整的OHLCV数据
            kdata = []
            for i, (date, close) in enumerate(zip(dates, prices)):
                if i == 0:
                    open_price = close
                else:
                    open_price = prices[i-1]  # 开盘价等于前一日收盘价

                # 生成高低价
                high = max(open_price, close) * (1 + np.random.uniform(0, 0.02))
                low = min(open_price, close) * (1 - np.random.uniform(0, 0.02))
                volume = np.random.randint(1000000, 10000000)

                kdata.append({
                    'datetime': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume
                })

            df = pd.DataFrame(kdata)
            df.set_index('datetime', inplace=True)

            # 更新图表
            self.chart_widget.update_chart({
                'kdata': df,
                'title': '测试涨跌颜色功能',
                'stock_code': 'TEST001'
            })

            print("✓ 测试数据生成完成")
            print("数据统计:")

            # 计算涨跌统计
            changes = df['close'].pct_change().dropna() * 100
            up_days = (changes > 0).sum()
            down_days = (changes < 0).sum()
            flat_days = (changes == 0).sum()

            print(f"  上涨天数: {up_days} (应显示红色)")
            print(f"  下跌天数: {down_days} (应显示绿色)")
            print(f"  平盘天数: {flat_days} (应显示灰色)")
            print(f"  最大涨幅: {changes.max():.2f}%")
            print(f"  最大跌幅: {changes.min():.2f}%")

        except Exception as e:
            print(f"✗ 生成测试数据失败: {e}")
            import traceback
            traceback.print_exc()


def test_change_color_feature():
    """测试涨跌颜色功能"""
    print("=" * 60)
    print("测试涨跌颜色功能")
    print("=" * 60)

    app = QApplication(sys.argv)

    try:
        # 创建测试窗口
        window = TestChangeColorWindow()
        window.show()

        print("\n测试说明:")
        print("1. 移动鼠标到K线图上，观察十字光标信息")
        print("2. 查看涨跌信息的颜色:")
        print("   - ↑ 上涨应显示红色")
        print("   - ↓ 下跌应显示绿色")
        print("   - → 平盘应显示灰色")
        print("3. 验证颜色是否根据涨跌状态正确显示")
        print("\n按 Ctrl+C 退出测试")

        # 运行应用
        sys.exit(app.exec_())

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"✗ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_change_color_feature()
