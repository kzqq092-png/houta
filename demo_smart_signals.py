#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能信号聚合系统演示
展示技术分析 + 情绪分析 + 基本面分析的综合信号
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def demo_smart_signals():
    """演示智能信号聚合"""
    print("🚀 智能信号聚合系统演示")
    print("=" * 60)

    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
        from PyQt5.QtCore import QTimer
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta

        # 导入我们的组件
        from gui.widgets.sentiment_overview_widget import SentimentOverviewWidget
        from gui.widgets.smart_alert_widget import SmartAlertWidget
        from gui.widgets.signal_aggregator import SignalAggregator
        from gui.widgets.signal_detectors.base_detector import SignalDetectorRegistry

        class DemoWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("智能信号聚合系统演示")
                self.setGeometry(100, 100, 1200, 800)

                # 创建主窗口
                main_widget = QWidget()
                main_layout = QHBoxLayout()

                # 左侧：情绪概览
                self.sentiment_widget = SentimentOverviewWidget()

                # 右侧：智能提醒
                self.alert_widget = SmartAlertWidget()

                # 信号聚合器
                self.signal_aggregator = SignalAggregator()
                self.signal_aggregator.alert_generated.connect(self.alert_widget.add_alert)

                # 检测器注册中心
                self.detector_registry = SignalDetectorRegistry()

                main_layout.addWidget(self.sentiment_widget)
                main_layout.addWidget(self.alert_widget)

                main_widget.setLayout(main_layout)
                self.setCentralWidget(main_widget)

                # 模拟数据定时器
                self.timer = QTimer()
                self.timer.timeout.connect(self.generate_demo_signals)
                self.timer.start(5000)  # 每5秒生成一次信号

                print("✅ 演示窗口已创建")

                # 初始化一些模拟数据
                self.generate_initial_data()

            def generate_initial_data(self):
                """生成初始演示数据"""
                # 模拟情绪数据
                sentiment_data = {
                    'fear_greed_index': np.random.uniform(20, 80),
                    'news_sentiment': np.random.uniform(0.3, 0.7),
                    'money_flow': np.random.uniform(-0.5, 0.5),
                    'vix_index': np.random.uniform(15, 35)
                }

                self.sentiment_widget.update_sentiment_data(sentiment_data)
                print(f"📊 初始情绪数据: 恐贪指数 {sentiment_data['fear_greed_index']:.0f}")

            def generate_demo_signals(self):
                """生成演示信号"""
                try:
                    # 生成模拟K线数据
                    kdata = self.generate_mock_kdata()

                    # 生成模拟技术指标
                    technical_indicators = self.generate_mock_technical_indicators()

                    # 生成模拟情绪数据
                    sentiment_data = self.generate_mock_sentiment_data()

                    # 更新情绪组件
                    self.sentiment_widget.update_sentiment_data(sentiment_data)

                    # 模拟基本面数据
                    fundamental_data = self.generate_mock_fundamental_data()

                    # 准备数据包
                    data_package = {
                        'kdata': kdata,
                        'technical': technical_indicators,
                        'sentiment': sentiment_data,
                        'fundamental': fundamental_data
                    }

                    # 使用检测器注册中心检测信号
                    detector_signals = self.detector_registry.detect_all_signals(data_package)

                    # 执行信号聚合
                    alerts = self.signal_aggregator.process_data(
                        kdata=kdata,
                        technical_indicators=technical_indicators,
                        sentiment_data=sentiment_data,
                        fundamental_data=fundamental_data
                    )

                    if alerts:
                        print(f"🔔 生成了 {len(alerts)} 个聚合警报")
                        for alert in alerts:
                            print(f"   📢 {alert.title}: {alert.message}")

                    # 显示检测器统计
                    total_signals = sum(len(signals) for signals in detector_signals.values())
                    if total_signals > 0:
                        print(f"🎯 检测到 {total_signals} 个原始信号")
                        for detector_name, signals in detector_signals.items():
                            if signals:
                                print(f"   {detector_name}: {len(signals)} 个信号")

                except Exception as e:
                    print(f"❌ 信号生成错误: {e}")

            def generate_mock_kdata(self):
                """生成模拟K线数据"""
                dates = pd.date_range(start=datetime.now() - timedelta(days=30),
                                      end=datetime.now(), freq='D')

                base_price = 100
                prices = [base_price]
                for i in range(1, len(dates)):
                    change = np.random.normal(0, 0.02)
                    new_price = prices[-1] * (1 + change)
                    prices.append(new_price)

                return pd.DataFrame({
                    'date': dates,
                    'open': [p * np.random.uniform(0.98, 1.02) for p in prices],
                    'high': [p * np.random.uniform(1.01, 1.05) for p in prices],
                    'low': [p * np.random.uniform(0.95, 0.99) for p in prices],
                    'close': prices,
                    'volume': [np.random.randint(1000000, 10000000) for _ in prices]
                })

            def generate_mock_technical_indicators(self):
                """生成模拟技术指标"""
                # 有时生成极端值来触发信号
                extreme_chance = np.random.random()

                if extreme_chance < 0.3:  # 30%概率生成极端值
                    rsi = np.random.choice([np.random.uniform(75, 90), np.random.uniform(10, 25)])
                else:
                    rsi = np.random.uniform(30, 70)

                return {
                    'rsi': rsi,
                    'macd': {
                        'dif': np.random.uniform(-1, 1),
                        'dea': np.random.uniform(-1, 1),
                        'histogram': np.random.uniform(-0.5, 0.5)
                    },
                    'ma': {
                        'ma5': np.random.uniform(95, 105),
                        'ma10': np.random.uniform(90, 110),
                        'ma20': np.random.uniform(85, 115)
                    }
                }

            def generate_mock_sentiment_data(self):
                """生成模拟情绪数据"""
                # 有时生成极端情绪值
                extreme_chance = np.random.random()

                if extreme_chance < 0.2:  # 20%概率生成极端情绪
                    fear_greed = np.random.choice([np.random.uniform(85, 95), np.random.uniform(5, 15)])
                else:
                    fear_greed = np.random.uniform(30, 70)

                return {
                    'fear_greed_index': fear_greed,
                    'news_sentiment': np.random.uniform(0.2, 0.8),
                    'money_flow': np.random.uniform(-0.8, 0.8),
                    'vix_index': np.random.uniform(12, 40)
                }

            def generate_mock_fundamental_data(self):
                """生成模拟基本面数据"""
                return {
                    'pe_ratio': np.random.uniform(10, 35),
                    'pb_ratio': np.random.uniform(0.8, 4),
                    'roe': np.random.uniform(5, 25),
                    'earnings_growth': np.random.uniform(-20, 30)
                }

        # 创建应用
        if not QApplication.instance():
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()

        # 创建演示窗口
        demo_window = DemoWindow()
        demo_window.show()

        print("\n🎭 智能信号聚合系统演示功能:")
        print("   • 情绪数据实时更新和可视化")
        print("   • 技术指标信号检测")
        print("   • 情绪信号检测")
        print("   • 基本面信号检测")
        print("   • 成交量信号检测")
        print("   • 多源信号智能聚合")
        print("   • 实时智能提醒和警报")
        print("   • 信号组合分析 (如: 技术超买 + 情绪贪婪)")
        print("\n💡 特色功能:")
        print("   🎯 当RSI>80且恐贪指数>85时，生成强烈卖出信号")
        print("   🎯 当价格突破且情绪恐惧时，生成谨慎买入信号")
        print("   🎯 基本面PE/PB估值分析")
        print("   🎯 成交量异常和价量背离检测")
        print("\n⏰ 每5秒自动生成新的模拟信号，观察聚合效果")
        print("📱 点击警报卡片可查看详细信号分析")

        # 运行应用
        return app.exec_()

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    success = demo_smart_signals()
    print(f"\n🏁 演示{'成功' if success == 0 else '失败'}!")
    sys.exit(success)
