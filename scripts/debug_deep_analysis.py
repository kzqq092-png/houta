#!/usr/bin/env python3
"""
深度分析服务调试脚本
分析为什么深度分析tab没有数据输出和展示
"""

import time
import random
from datetime import datetime
from core.services.deep_analysis_service import get_deep_analysis_service
from loguru import logger

def test_deep_analysis_service():
    """测试深度分析服务的数据收集和分析功能"""
    
    print("🔍 开始调试深度分析服务...")
    
    # 1. 获取深度分析服务实例
    try:
        analysis_service = get_deep_analysis_service()
        print("✅ 深度分析服务实例获取成功")
        print(f"   - 服务实例: {analysis_service}")
        print(f"   - 最大历史记录数: {analysis_service.max_history_size}")
    except Exception as e:
        print(f"❌ 获取深度分析服务失败: {e}")
        return False
    
    # 2. 检查当前数据状态
    print("\n📊 检查当前数据状态:")
    print(f"   - 指标历史记录数: {len(analysis_service.metrics_history)}")
    print(f"   - 操作计时记录数: {len(analysis_service.operation_timings)}")
    
    if analysis_service.operation_timings:
        for op_name, timings in analysis_service.operation_timings.items():
            print(f"   - {op_name}: {len(timings)} 次记录")
    else:
        print("   - ⚠️ 当前没有任何操作计时记录")
    
    # 3. 模拟数据收集
    print("\n🔄 模拟数据收集...")
    
    # 模拟性能指标
    metrics = [
        ('cpu_usage', lambda: random.uniform(20, 80)),
        ('memory_usage', lambda: random.uniform(30, 70)),
        ('disk_usage', lambda: random.uniform(10, 90)),
        ('response_time', lambda: random.uniform(0.1, 2.0)),
        ('query_time', lambda: random.uniform(0.05, 1.5))
    ]
    
    # 模拟操作计时
    operations = [
        ('数据加载', lambda: random.uniform(0.1, 1.0)),
        ('图表渲染', lambda: random.uniform(0.2, 0.8)),
        ('策略计算', lambda: random.uniform(0.3, 1.5)),
        ('数据库查询', lambda: random.uniform(0.1, 0.6)),
        ('指标计算', lambda: random.uniform(0.05, 0.4)),
        ('UI更新', lambda: random.uniform(0.01, 0.2))
    ]
    
    # 收集模拟数据
    for i in range(50):  # 模拟50次数据收集
        # 记录性能指标
        for metric_name, value_func in metrics:
            value = value_func()
            analysis_service.record_metric(metric_name, value)
        
        # 记录操作计时
        for op_name, duration_func in operations:
            duration = duration_func()
            analysis_service.record_operation_timing(op_name, duration)
        
        if i % 10 == 0:
            print(f"   - 已收集 {i+1}/50 批数据")
    
    print("✅ 模拟数据收集完成")
    
    # 4. 测试各个分析功能
    print("\n🧪 测试各个分析功能:")
    
    # 4.1 测试瓶颈分析
    print("\n   📊 测试瓶颈分析:")
    try:
        bottlenecks = analysis_service.analyze_bottlenecks()
        print(f"      - 发现 {len(bottlenecks)} 个性能瓶颈")
        for i, bottleneck in enumerate(bottlenecks[:3], 1):
            print(f"      - {i}. {bottleneck.component}: {bottleneck.percentage:.1f}% ({bottleneck.severity})")
    except Exception as e:
        print(f"      ❌ 瓶颈分析失败: {e}")
    
    # 4.2 测试操作排行
    print("\n   ⏱️ 测试操作排行:")
    try:
        ranking = analysis_service.get_operation_ranking()
        print(f"      - 获得 {len(ranking)} 个操作记录")
        for i, (name, duration, count) in enumerate(ranking[:3], 1):
            print(f"      - {i}. {name}: {duration:.2f}ms ({count}次)")
    except Exception as e:
        print(f"      ❌ 操作排行失败: {e}")
    
    # 4.3 测试异常检测
    print("\n   🚨 测试异常检测:")
    try:
        anomalies = analysis_service.detect_anomalies(hours=1)
        print(f"      - 检测到 {len(anomalies)} 个异常")
        for i, anomaly in enumerate(anomalies[:3], 1):
            print(f"      - {i}. {anomaly.metric_name}: {anomaly.value:.2f} (阈值: {anomaly.threshold:.2f})")
    except Exception as e:
        print(f"      ❌ 异常检测失败: {e}")
    
    # 4.4 测试趋势预测
    print("\n   📈 测试趋势预测:")
    try:
        trends = analysis_service.predict_trends(hours=1)
        print(f"      - 预测 {len(trends)} 个指标趋势")
        for metric_name, trend_data in list(trends.items())[:3]:
            current = trend_data['current']
            next_week = trend_data['next_week']
            print(f"      - {metric_name}: 当前 {current:.2f} → 下周 {next_week:.2f}")
    except Exception as e:
        print(f"      ❌ 趋势预测失败: {e}")
    
    # 4.5 测试优化建议
    print("\n   💡 测试优化建议:")
    try:
        suggestions = analysis_service.generate_optimization_suggestions()
        high_priority = suggestions.get('high_priority', [])
        medium_priority = suggestions.get('medium_priority', [])
        low_priority = suggestions.get('low_priority', [])
        
        print(f"      - 高优先级建议: {len(high_priority)} 个")
        print(f"      - 中优先级建议: {len(medium_priority)} 个")
        print(f"      - 低优先级建议: {len(low_priority)} 个")
        
        for i, suggestion in enumerate(high_priority[:2], 1):
            print(f"      - {i}. {suggestion['component']}: {suggestion['suggestion']}")
    except Exception as e:
        print(f"      ❌ 优化建议失败: {e}")
    
    # 5. 检查数据持久化
    print("\n💾 检查数据持久化:")
    print(f"   - 当前指标历史: {len(analysis_service.metrics_history)} 条")
    print(f"   - 当前操作记录: {sum(len(timings) for timings in analysis_service.operation_timings.values())} 条")
    
    # 6. 测试UI集成
    print("\n🖥️ 模拟UI调用:")
    try:
        from gui.widgets.performance.tabs.deep_analysis_tab import ModernDeepAnalysisTab
        
        # 这里我们只是测试导入，不实际创建UI组件
        print("   ✅ DeepAnalysisTab 导入成功")
        
        # 测试UI调用的基本流程
        print("   📊 模拟UI瓶颈分析调用...")
        bottlenecks = analysis_service.analyze_bottlenecks()
        if bottlenecks:
            print(f"      ✅ UI可以获取到 {len(bottlenecks)} 个瓶颈数据")
        else:
            print("      ⚠️ UI将显示'暂无数据'")
            
    except Exception as e:
        print(f"   ❌ UI集成测试失败: {e}")
    
    print("\n🎉 深度分析服务调试完成!")
    return True

def check_performance_monitoring_integration():
    """检查性能监控集成"""
    print("\n🔍 检查性能监控系统集成...")
    
    try:
        # 检查统一性能监控器
        from core.performance.unified_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        print("✅ 统一性能监控器可用")
        
        # 检查是否有实际的性能数据
        if hasattr(monitor, 'stats') and monitor.stats:
            print(f"   - 性能统计数据: {len(monitor.stats)} 项")
            for name in list(monitor.stats.keys())[:3]:
                print(f"   - {name}")
        else:
            print("   ⚠️ 性能监控器没有统计数据")
            
    except Exception as e:
        print(f"❌ 性能监控器检查失败: {e}")
    
    try:
        # 检查应用指标服务
        from core.metrics.app_metrics_service import ApplicationMetricsService
        from core.containers import get_service_container
        
        container = get_service_container()
        if container:
            app_metrics = container.resolve(ApplicationMetricsService)
            metrics = app_metrics.get_metrics()
            print(f"✅ 应用指标服务可用，包含 {len(metrics)} 个指标")
            
            for name in list(metrics.keys())[:3]:
                metric = metrics[name]
                print(f"   - {name}: {metric.get('call_count', 0)} 次调用")
        else:
            print("⚠️ 服务容器不可用")
            
    except Exception as e:
        print(f"❌ 应用指标服务检查失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 深度分析服务调试和问题诊断")
    print("=" * 60)
    
    # 检查性能监控集成
    check_performance_monitoring_integration()
    
    # 测试深度分析服务
    test_deep_analysis_service()
    
    print("\n" + "=" * 60)
    print("📋 调试结果总结:")
    print("1. 检查深度分析服务是否能正常获取实例")
    print("2. 检查是否有实际的性能数据收集")
    print("3. 验证各个分析功能是否正常工作")
    print("4. 确认UI组件是否能正确调用服务接口")
    print("=" * 60)

if __name__ == "__main__":
    main()