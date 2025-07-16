#!/usr/bin/env python3
"""
测试技术分析标签页在RightPanel中的数据传递功能

验证以下功能：
1. TechnicalAnalysisTab是否正确集成到RightPanel
2. UIDataReadyEvent是否正确传递K线数据
3. 技术分析功能是否正常工作
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
import sys
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


# 测试导入
try:
    from core.ui.panels.right_panel import RightPanel, TECHNICAL_TAB_AVAILABLE
    from core.events import UIDataReadyEvent
    from core.events.event_bus import EventBus
    from core.logger import LogManager
    print(f"✓ 成功导入RightPanel，技术分析标签页可用: {TECHNICAL_TAB_AVAILABLE}")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)


class TestCoordinator:
    """测试协调器"""

    def __init__(self):
        self.event_bus = EventBus()

    def get_event_bus(self):
        return self.event_bus


def create_test_kdata(days: int = 100) -> pd.DataFrame:
    """创建测试用的K线数据"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')

    # 生成模拟的K线数据
    np.random.seed(42)  # 固定随机种子以便重现
    base_price = 100.0

    data = []
    current_price = base_price

    for date in dates:
        # 模拟价格波动
        change = np.random.normal(0, 0.02)  # 2%的标准波动
        current_price *= (1 + change)

        # 生成OHLC数据
        open_price = current_price
        high_price = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low_price = current_price * (1 - abs(np.random.normal(0, 0.01)))
        close_price = current_price * (1 + np.random.normal(0, 0.005))
        volume = np.random.randint(1000000, 10000000)

        data.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })

        current_price = close_price

    df = pd.DataFrame(data, index=dates)
    return df


def create_test_analysis_data() -> Dict[str, Any]:
    """创建测试用的分析数据"""
    return {
        'technical_indicators': {
            'trend': {
                'MA20': {'value': 105.2, 'signal': 'buy'},
                'MA50': {'value': 102.8, 'signal': 'neutral'},
            },
            'momentum': {
                'RSI': {'value': 65.5, 'signal': 'neutral'},
                'MACD': {'value': 1.2, 'signal': 'buy'},
            },
            'volume': {
                'summary': '成交量较前期放大，表明市场关注度提升'
            }
        },
        'trading_signals': {
            'current_signal': {
                'type': 'buy',
                'description': '技术指标显示买入信号',
                'strength': 75
            },
            'history': []
        },
        'risk_assessment': {
            'risk_level': 'medium',
            'volatility': 0.15
        },
        'backtest_results': {
            'total_return': 0.12,
            'sharpe_ratio': 1.2
        }
    }


class TestMainWindow(QMainWindow):
    """测试主窗口"""

    def __init__(self):
        super().__init__()
        self.coordinator = TestCoordinator()
        self.log_manager = LogManager()

        self.setWindowTitle("技术分析集成测试")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建测试按钮
        test_button = QPushButton("测试技术分析数据传递")
        test_button.clicked.connect(self.test_data_transmission)
        layout.addWidget(test_button)

        # 创建RightPanel
        try:
            self.right_panel = RightPanel(self, self.coordinator, width=400)
            layout.addWidget(self.right_panel)
            print("✓ RightPanel创建成功")

            # 检查技术分析标签页
            if hasattr(self.right_panel, '_technical_tab'):
                print("✓ 完整的TechnicalAnalysisTab已集成")
            else:
                print("✗ 未找到完整的TechnicalAnalysisTab")

        except Exception as e:
            print(f"✗ RightPanel创建失败: {e}")
            import traceback
            traceback.print_exc()

    def test_data_transmission(self):
        """测试数据传递功能"""
        try:
            print("\n开始测试数据传递...")

            # 创建测试数据
            kdata = create_test_kdata(100)
            analysis_data = create_test_analysis_data()

            print(f"✓ 创建测试K线数据: {len(kdata)} 条")
            print(f"✓ 创建测试分析数据: {len(analysis_data)} 类")

            # 创建UIDataReadyEvent
            ui_data = {
                'kline_data': kdata,
                'analysis': analysis_data,
                'stock_code': '000001',
                'stock_name': '平安银行',
                'period': '日线',
                'time_range': '最近100天'
            }

            event = UIDataReadyEvent(
                source="测试",
                stock_code="000001",
                stock_name="平安银行",
                ui_data=ui_data
            )

            # 发布事件
            self.coordinator.event_bus.publish(event)
            print("✓ UIDataReadyEvent事件已发布")

            # 延迟检查结果
            QTimer.singleShot(1000, self.check_results)

        except Exception as e:
            print(f"✗ 测试数据传递失败: {e}")
            import traceback
            traceback.print_exc()

    def check_results(self):
        """检查测试结果"""
        try:
            print("\n检查测试结果...")

            # 检查股票信息是否更新
            if hasattr(self.right_panel, '_current_stock_code'):
                if self.right_panel._current_stock_code == '000001':
                    print("✓ 股票信息已更新")
                else:
                    print("✗ 股票信息未更新")

            # 检查技术分析标签页是否有数据
            if hasattr(self.right_panel, '_technical_tab'):
                technical_tab = self.right_panel._technical_tab

                # 检查K线数据
                if hasattr(technical_tab, 'current_kdata') and technical_tab.current_kdata is not None:
                    data_len = len(technical_tab.current_kdata)
                    print(f"✓ 技术分析标签页已接收K线数据: {data_len} 条")

                    # 检查自动计算状态
                    if hasattr(technical_tab, 'auto_calculate'):
                        print(f"✓ 自动计算状态: {technical_tab.auto_calculate}")

                    # 检查指标计算功能
                    if hasattr(technical_tab, 'calculate_indicators'):
                        print("✓ 指标计算功能可用")

                        # 可以尝试手动触发计算
                        try:
                            technical_tab.calculate_indicators()
                            print("✓ 指标计算执行成功")
                        except Exception as e:
                            print(f"✗ 指标计算失败: {e}")

                else:
                    print("✗ 技术分析标签页未接收到K线数据")
            else:
                print("✗ 未找到技术分析标签页")

            print("\n测试完成!")

        except Exception as e:
            print(f"✗ 检查结果失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    print("=== 技术分析集成测试 ===")

    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    app = QApplication(sys.argv)

    try:
        window = TestMainWindow()
        window.show()

        print("\n测试窗口已显示，请点击按钮进行测试")
        print("观察控制台输出和UI反应")

        sys.exit(app.exec_())

    except Exception as e:
        print(f"程序运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
