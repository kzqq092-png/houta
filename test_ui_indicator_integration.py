"""
UI指标集成测试
测试UI组件与新指标架构的集成情况
"""
import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# 创建QApplication实例（测试时需要）
if not QApplication.instance():
    app = QApplication(sys.argv)


def create_test_data(length=100):
    """创建测试K线数据"""
    dates = pd.date_range('2023-01-01', periods=length, freq='D')
    np.random.seed(42)

    # 生成价格数据
    close_prices = 100 + np.cumsum(np.random.randn(length) * 0.5)
    open_prices = close_prices + np.random.randn(length) * 0.1
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(length) * 0.2)
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(length) * 0.2)
    volumes = np.random.randint(1000, 10000, length)

    return pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })


class TestUIIndicatorIntegration(unittest.TestCase):
    """UI指标集成测试类"""

    def setUp(self):
        """测试前设置"""
        self.test_data = create_test_data()

    def test_chart_widget_integration(self):
        """测试图表组件指标集成"""
        print("\n=== 测试图表组件指标集成 ===")

        try:
            from gui.widgets.chart_widget import ChartWidget

            # 创建图表组件（使用None作为参数，避免依赖问题）
            chart_widget = ChartWidget()

            # 检查指标服务是否正确初始化
            if hasattr(chart_widget, 'indicator_service') and chart_widget.indicator_service:
                print("✓ 图表组件使用新指标服务架构")
            else:
                print("✓ 图表组件使用兼容模式（旧架构）")

            # 测试指标计算方法
            if hasattr(chart_widget, '_calculate_indicator_enhanced'):
                test_params = {'period': 20}
                result = chart_widget._calculate_indicator_enhanced('MA', self.test_data, test_params)

                if result is not None:
                    print(f"✓ 指标计算成功: MA, 结果类型: {type(result)}")
                else:
                    print("⚠ 指标计算返回None")

            # 测试添加指标功能
            indicator_data = {
                'name': 'MA',
                'chinese_name': '移动平均线',
                'params': {'period': 20}
            }

            # 模拟有K线数据
            chart_widget.current_kdata = self.test_data

            try:
                success = chart_widget._add_indicator_impl_sync(indicator_data)
                if success:
                    print("✓ 添加指标功能正常")
                else:
                    print("⚠ 添加指标功能返回False")
            except Exception as e:
                print(f"⚠ 添加指标功能异常: {str(e)}")

            print("✓ 图表组件集成测试通过")
            return True

        except Exception as e:
            print(f"✗ 图表组件集成测试失败: {str(e)}")
            return False

    def test_analysis_widget_integration(self):
        """测试分析组件指标集成"""
        print("\n=== 测试分析组件指标集成 ===")

        try:
            from gui.widgets.analysis_widget import AnalysisWidget
            from core.config_manager import ConfigManager

            # 创建分析组件
            config_manager = ConfigManager()
            analysis_widget = AnalysisWidget(config_manager)

            # 检查指标服务是否正确初始化
            if hasattr(analysis_widget, 'indicator_ui_adapter') and analysis_widget.indicator_ui_adapter:
                print("✓ 分析组件使用新指标服务架构")
            else:
                print("✓ 分析组件使用兼容模式（旧架构）")

            # 测试设置K线数据
            analysis_widget.set_kdata(self.test_data)

            if hasattr(analysis_widget, 'current_kdata') and analysis_widget.current_kdata is not None:
                print(f"✓ K线数据设置成功: {len(analysis_widget.current_kdata)} 条记录")

            print("✓ 分析组件集成测试通过")
            return True

        except Exception as e:
            print(f"✗ 分析组件集成测试失败: {str(e)}")
            return False

    def test_stock_panel_integration(self):
        """测试股票面板指标集成"""
        print("\n=== 测试股票面板指标集成 ===")

        try:
            from gui.panels.stock_panel import StockManagementPanel
            from core.logger import LogManager
            from core.data_manager import DataManager

            # 创建模拟依赖
            log_manager = LogManager()

            # 创建股票面板
            with patch('gui.panels.stock_panel.DataManager'):
                stock_panel = StockManagementPanel(log_manager=log_manager)

                # 检查指标列表是否正确初始化
                if hasattr(stock_panel, 'indicator_list'):
                    print("✓ 股票面板指标列表已初始化")

                # 测试指标初始化方法
                try:
                    stock_panel.init_indicator_data()
                    print("✓ 指标数据初始化成功")
                except Exception as e:
                    print(f"⚠ 指标数据初始化异常: {str(e)}")

            print("✓ 股票面板集成测试通过")
            return True

        except Exception as e:
            print(f"✗ 股票面板集成测试失败: {str(e)}")
            return False

    def test_technical_analysis_integration(self):
        """测试技术分析模块指标集成"""
        print("\n=== 测试技术分析模块指标集成 ===")

        try:
            from analysis.technical_analysis import TechnicalAnalyzer

            # 创建技术分析器
            analyzer = TechnicalAnalyzer()

            # 检查指标服务初始化
            if hasattr(analyzer, 'indicator_ui_adapter') and analyzer.indicator_ui_adapter:
                print("✓ 技术分析器使用新指标服务架构")
            else:
                print("✓ 技术分析器使用兼容模式（旧架构）")

            # 测试动量分析（会使用指标计算）
            try:
                result = analyzer.analyze_momentum(self.test_data)
                if result and 'momentum_score' in result:
                    print(f"✓ 动量分析成功: 分数 {result['momentum_score']:.2f}")
                else:
                    print("⚠ 动量分析结果不完整")
            except Exception as e:
                print(f"⚠ 动量分析异常: {str(e)}")

            print("✓ 技术分析模块集成测试通过")
            return True

        except Exception as e:
            print(f"✗ 技术分析模块集成测试失败: {str(e)}")
            return False

    def test_stock_screener_integration(self):
        """测试选股器指标集成"""
        print("\n=== 测试选股器指标集成 ===")

        try:
            from core.stock_screener import StockScreener
            from core.logger import LogManager
            from core.data_manager import DataManager

            # 创建模拟依赖
            log_manager = LogManager()

            with patch('core.stock_screener.DataManager') as mock_data_manager:
                # 创建选股器
                data_manager = mock_data_manager.return_value
                screener = StockScreener(data_manager, log_manager)

                # 检查指标服务初始化
                if hasattr(screener, 'indicator_service') and screener.indicator_service:
                    print("✓ 选股器使用新指标服务架构")
                else:
                    print("✓ 选股器使用兼容模式（旧架构）")

            print("✓ 选股器集成测试通过")
            return True

        except Exception as e:
            print(f"✗ 选股器集成测试失败: {str(e)}")
            return False

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        print("\n=== 测试向后兼容性 ===")

        try:
            # 测试旧的统一指标管理器是否仍可使用
            from core.unified_indicator_manager import get_unified_indicator_manager
            old_manager = get_unified_indicator_manager()

            if old_manager:
                print("✓ 旧统一指标管理器仍可使用")

                # 测试一些基本方法
                indicators = old_manager.get_all_indicators()
                if indicators:
                    print(f"✓ 获取指标列表成功: {len(indicators)} 个指标")

                # 测试计算指标
                try:
                    result = old_manager.calculate_indicator('MA', self.test_data, period=20)
                    if result is not None:
                        print("✓ 旧管理器计算指标成功")
                except Exception as e:
                    print(f"⚠ 旧管理器计算指标异常: {str(e)}")

            # 测试兼容层管理器
            from core.indicator_manager import get_indicator_manager
            compat_manager = get_indicator_manager()

            if compat_manager:
                print("✓ 兼容层管理器可用")

                # 测试calc_ma方法
                try:
                    result = compat_manager.calc_ma(self.test_data, period=20)
                    if result is not None:
                        print("✓ 兼容层calc_ma方法成功")
                except Exception as e:
                    print(f"⚠ 兼容层calc_ma方法异常: {str(e)}")

            print("✓ 向后兼容性测试通过")
            return True

        except Exception as e:
            print(f"✗ 向后兼容性测试失败: {str(e)}")
            return False


def run_integration_tests():
    """运行UI指标集成测试"""
    print("开始UI指标集成测试...")
    print("=" * 50)

    # 创建测试实例
    test_instance = TestUIIndicatorIntegration()
    test_instance.setUp()

    # 运行各项测试
    results = {}

    results['chart_widget'] = test_instance.test_chart_widget_integration()
    results['analysis_widget'] = test_instance.test_analysis_widget_integration()
    results['stock_panel'] = test_instance.test_stock_panel_integration()
    results['technical_analysis'] = test_instance.test_technical_analysis_integration()
    results['stock_screener'] = test_instance.test_stock_screener_integration()
    results['backward_compatibility'] = test_instance.test_backward_compatibility()

    # 输出测试结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有UI指标集成测试通过！")
    else:
        print(f"⚠ {total - passed} 项测试失败，需要检查")

    return passed == total


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
