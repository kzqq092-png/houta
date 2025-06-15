#!/usr/bin/env python3
"""
快速测试TrendAnalysisTab初始化问题
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_trend_tab():
    """测试TrendAnalysisTab初始化"""
    print("🔍 测试TrendAnalysisTab初始化...")

    try:
        from utils.config_manager import ConfigManager
        from gui.widgets.analysis_tabs.trend_tab import TrendAnalysisTab

        config_manager = ConfigManager()

        print("📋 创建TrendAnalysisTab...")
        trend_tab = TrendAnalysisTab(config_manager)
        print("✅ TrendAnalysisTab 创建成功")

        # 检查关键属性
        print("🔧 检查关键属性...")
        if hasattr(trend_tab, 'trend_algorithms'):
            print(f"✅ trend_algorithms 存在: {len(trend_tab.trend_algorithms)} 个算法")
        else:
            print("❌ trend_algorithms 不存在")

        if hasattr(trend_tab, 'auto_update_cb'):
            print("✅ auto_update_cb 存在")
        else:
            print("❌ auto_update_cb 不存在")

        if hasattr(trend_tab, 'timeframes'):
            print(f"✅ timeframes 存在: {len(trend_tab.timeframes)} 个时间框架")
        else:
            print("❌ timeframes 不存在")

        # 测试UI创建
        print("🎨 测试UI创建...")
        if hasattr(trend_tab, 'create_ui'):
            print("✅ create_ui 方法存在")
        else:
            print("❌ create_ui 方法不存在")

        # 测试数据操作
        print("💾 测试数据操作...")
        import pandas as pd
        import numpy as np

        # 创建模拟数据
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        mock_data = pd.DataFrame({
            'open': np.random.uniform(10, 20, 50),
            'high': np.random.uniform(15, 25, 50),
            'low': np.random.uniform(5, 15, 50),
            'close': np.random.uniform(10, 20, 50),
            'volume': np.random.uniform(1000, 10000, 50)
        }, index=dates)

        trend_tab.set_kdata(mock_data)
        print("✅ 数据设置成功")

        trend_tab.refresh_data()
        print("✅ 数据刷新成功")

        trend_tab.clear_data()
        print("✅ 数据清除成功")

        print("\n🎉 TrendAnalysisTab 测试完全成功！")
        return True

    except Exception as e:
        print(f"❌ TrendAnalysisTab 测试失败: {e}")
        traceback.print_exc()
        return False


def test_all_tabs():
    """测试所有标签页"""
    print("\n🚀 测试所有标签页...")

    try:
        from gui.widgets.analysis_tabs import (
            TechnicalAnalysisTab, PatternAnalysisTab, TrendAnalysisTab,
            WaveAnalysisTab, SentimentAnalysisTab, SectorFlowTab,
            HotspotAnalysisTab, SentimentReportTab
        )

        config_manager = ConfigManager()
        tabs = {}

        # 测试每个标签页
        tab_classes = [
            ('technical', TechnicalAnalysisTab),
            ('pattern', PatternAnalysisTab),
            ('trend', TrendAnalysisTab),
            ('wave', WaveAnalysisTab),
            ('sentiment', SentimentAnalysisTab),
            ('sector_flow', SectorFlowTab),
            ('hotspot', HotspotAnalysisTab),
            ('sentiment_report', SentimentReportTab)
        ]

        for tab_name, tab_class in tab_classes:
            try:
                print(f"📋 创建 {tab_name}...")
                tab = tab_class(config_manager)
                tabs[tab_name] = tab
                print(f"✅ {tab_name} 创建成功")
            except Exception as e:
                print(f"❌ {tab_name} 创建失败: {e}")

        print(f"\n📊 成功创建 {len(tabs)}/8 个标签页")

        if len(tabs) == 8:
            print("🎉 所有标签页创建成功！")
            return True
        else:
            print("⚠️ 部分标签页创建失败")
            return False

    except Exception as e:
        print(f"❌ 标签页测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始快速测试...")

    # 测试TrendAnalysisTab
    trend_success = test_trend_tab()

    # 测试所有标签页
    all_success = test_all_tabs()

    if trend_success and all_success:
        print("\n🎉 所有测试通过！Analysis Widget模块功能正常！")
    else:
        print("\n❌ 部分测试失败，需要进一步检查")


if __name__ == "__main__":
    main()
