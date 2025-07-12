#!/usr/bin/env python3
"""
Analysis Widget模块全面测试脚本
测试所有8个专业模块的初始化和基本功能
"""

import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_module_import():
    """测试模块导入"""
    print("=" * 60)
    print("🔍 测试模块导入...")
    print("=" * 60)

    modules_to_test = [
        ('gui.widgets.analysis_tabs.base_tab', 'BaseAnalysisTab'),
        ('gui.widgets.analysis_tabs.technical_tab', 'TechnicalAnalysisTab'),
        ('gui.widgets.analysis_tabs.pattern_tab', 'PatternAnalysisTab'),
        ('gui.widgets.analysis_tabs.pattern_tab_pro', 'PatternAnalysisTabPro'),
        ('gui.widgets.analysis_tabs.trend_tab', 'TrendAnalysisTab'),
        ('gui.widgets.analysis_tabs.wave_tab', 'WaveAnalysisTab'),
        ('gui.widgets.analysis_tabs.wave_tab_pro', 'WaveAnalysisTabPro'),
        ('gui.widgets.analysis_tabs.sentiment_tab', 'SentimentAnalysisTab'),
        ('gui.widgets.analysis_tabs.sentiment_tab_pro', 'SentimentAnalysisTabPro'),
        ('gui.widgets.analysis_tabs.sector_flow_tab', 'SectorFlowTab'),
        ('gui.widgets.analysis_tabs.sector_flow_tab_pro', 'SectorFlowTabPro'),
        ('gui.widgets.analysis_tabs.hotspot_tab', 'HotspotAnalysisTab'),
        ('gui.widgets.analysis_tabs.sentiment_report_tab', 'SentimentReportTab'),
    ]

    imported_classes = {}
    failed_imports = []

    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            imported_classes[class_name] = cls
            print(f"✅ {class_name}: 导入成功")
        except Exception as e:
            failed_imports.append((class_name, str(e)))
            print(f"❌ {class_name}: 导入失败 - {e}")

    print(f"\n📊 导入结果: {len(imported_classes)}/{len(modules_to_test)} 成功")
    return imported_classes, failed_imports


def test_module_initialization(imported_classes):
    """测试模块初始化"""
    print("\n" + "=" * 60)
    print("🚀 测试模块初始化...")
    print("=" * 60)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    initialized_instances = {}
    failed_initializations = []

    for class_name, cls in imported_classes.items():
        try:
            print(f"🔄 正在初始化 {class_name}...")

            # 创建实例
            instance = cls()

            # 检查关键属性是否存在
            critical_attributes = []
            if hasattr(instance, 'trend_algorithms'):
                critical_attributes.append('trend_algorithms')
            if hasattr(instance, 'auto_update_cb'):
                critical_attributes.append('auto_update_cb')
            if hasattr(instance, 'algorithm_combo'):
                critical_attributes.append('algorithm_combo')

            # 验证属性
            missing_attrs = []
            for attr in critical_attributes:
                if not hasattr(instance, attr):
                    missing_attrs.append(attr)

            if missing_attrs:
                raise AttributeError(f"缺少关键属性: {missing_attrs}")

            initialized_instances[class_name] = instance
            print(f"✅ {class_name}: 初始化成功")

            # 显示关键属性信息
            if critical_attributes:
                print(f"   📋 关键属性: {', '.join(critical_attributes)}")

        except Exception as e:
            failed_initializations.append(
                (class_name, str(e), traceback.format_exc()))
            print(f"❌ {class_name}: 初始化失败 - {e}")

    print(
        f"\n📊 初始化结果: {len(initialized_instances)}/{len(imported_classes)} 成功")
    return initialized_instances, failed_initializations


def test_specific_functionality(initialized_instances):
    """测试特定功能"""
    print("\n" + "=" * 60)
    print("🧪 测试特定功能...")
    print("=" * 60)

    functionality_results = {}

    for class_name, instance in initialized_instances.items():
        print(f"\n🔍 测试 {class_name} 功能...")
        results = []

        # 测试基本方法
        basic_methods = ['refresh_data', 'clear_data']
        for method_name in basic_methods:
            try:
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    method()
                    results.append(f"✅ {method_name}: 正常")
                else:
                    results.append(f"⚠️ {method_name}: 方法不存在")
            except Exception as e:
                results.append(f"❌ {method_name}: 错误 - {e}")

        # 测试特殊方法（如果存在）
        special_methods = []
        if class_name == 'TrendAnalysisTab':
            special_methods = ['analyze_trend', 'clear_trend']
        elif class_name == 'TechnicalAnalysisTab':
            special_methods = ['calculate_indicators', 'clear_indicators']
        elif class_name == 'PatternAnalysisTab':
            special_methods = ['analyze_patterns', 'clear_patterns']

        for method_name in special_methods:
            try:
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    method()
                    results.append(f"✅ {method_name}: 正常")
                else:
                    results.append(f"⚠️ {method_name}: 方法不存在")
            except Exception as e:
                results.append(f"❌ {method_name}: 错误 - {e}")

        functionality_results[class_name] = results
        for result in results:
            print(f"   {result}")

    return functionality_results


def generate_comprehensive_report(imported_classes, failed_imports, initialized_instances,
                                  failed_initializations, functionality_results):
    """生成全面报告"""
    print("\n" + "=" * 80)
    print("📋 ANALYSIS WIDGET 模块全面测试报告")
    print("=" * 80)

    # 总体统计
    total_modules = len(imported_classes) + len(failed_imports)
    successful_imports = len(imported_classes)
    successful_initializations = len(initialized_instances)

    print(f"\n📊 总体统计:")
    print(f"   总模块数: {total_modules}")
    print(
        f"   导入成功: {successful_imports}/{total_modules} ({successful_imports/total_modules*100:.1f}%)")
    print(f"   初始化成功: {successful_initializations}/{successful_imports} ({successful_initializations/successful_imports*100:.1f}% if successful_imports > 0 else 0)")

    # 成功的模块
    print(f"\n✅ 成功的模块 ({len(initialized_instances)}):")
    for class_name in sorted(initialized_instances.keys()):
        print(f"   • {class_name}")

    # 失败的导入
    if failed_imports:
        print(f"\n❌ 导入失败的模块 ({len(failed_imports)}):")
        for class_name, error in failed_imports:
            print(f"   • {class_name}: {error}")

    # 失败的初始化
    if failed_initializations:
        print(f"\n❌ 初始化失败的模块 ({len(failed_initializations)}):")
        for class_name, error, traceback_info in failed_initializations:
            print(f"   • {class_name}: {error}")
            print(f"     详细错误信息:")
            for line in traceback_info.split('\n')[-5:]:
                if line.strip():
                    print(f"       {line}")

    # 功能测试结果
    print(f"\n🧪 功能测试结果:")
    for class_name, results in functionality_results.items():
        print(f"   {class_name}:")
        for result in results:
            print(f"     {result}")

    # 专业级功能统计
    pro_modules = [name for name in initialized_instances.keys()
                   if 'Pro' in name]
    print(f"\n⭐ 专业级模块: {len(pro_modules)}")
    for name in pro_modules:
        print(f"   • {name}")

    # 建议和下一步
    print(f"\n💡 建议和下一步:")
    if failed_imports:
        print("   1. 修复导入失败的模块")
    if failed_initializations:
        print("   2. 修复初始化失败的模块，特别关注属性初始化顺序")
    if len(initialized_instances) == total_modules:
        print("   1. 所有模块工作正常！可以进行更深入的功能测试")
        print("   2. 考虑添加单元测试和集成测试")
        print("   3. 性能优化和用户体验改进")

    return {
        'total_modules': total_modules,
        'successful_imports': successful_imports,
        'successful_initializations': successful_initializations,
        'failed_imports': failed_imports,
        'failed_initializations': failed_initializations,
        'pro_modules_count': len(pro_modules)
    }


def main():
    """主测试函数"""
    print("🚀 开始 Analysis Widget 模块全面测试")
    print("测试时间:", os.popen('date').read().strip()
          if os.name != 'nt' else 'Windows')

    try:
        # 1. 测试导入
        imported_classes, failed_imports = test_module_import()

        # 2. 测试初始化
        initialized_instances, failed_initializations = test_module_initialization(
            imported_classes)

        # 3. 测试功能
        functionality_results = test_specific_functionality(
            initialized_instances)

        # 4. 生成报告
        report_stats = generate_comprehensive_report(
            imported_classes, failed_imports, initialized_instances,
            failed_initializations, functionality_results
        )

        # 5. 退出状态
        if failed_imports or failed_initializations:
            print(f"\n⚠️ 测试完成，但存在问题需要修复")
            return 1
        else:
            print(f"\n🎉 所有测试通过！Analysis Widget 模块工作正常")
            return 0

    except Exception as e:
        print(f"\n💥 测试过程中发生严重错误: {e}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    # 创建QApplication实例（如果需要）
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # 运行测试
    exit_code = main()

    # 延迟退出以便查看结果
    if exit_code == 0:
        print("\n✨ 测试成功完成！3秒后自动退出...")
        QTimer.singleShot(3000, app.quit)
    else:
        print(f"\n❌ 测试失败 (退出码: {exit_code})，请检查上述错误信息")
        QTimer.singleShot(5000, app.quit)

    if len(sys.argv) == 1:  # 只有在直接运行时才启动事件循环
        sys.exit(app.exec_())
    else:
        sys.exit(exit_code)
