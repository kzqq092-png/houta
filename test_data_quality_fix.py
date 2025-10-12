#!/usr/bin/env python3
"""测试数据质量监控修复"""

from gui.widgets.enhanced_ui.data_quality_monitor_tab_real_data import get_real_data_provider

print("=" * 60)
print("测试数据质量监控修复")
print("=" * 60)

# 获取真实数据提供者
provider = get_real_data_provider()
print("✅ 真实数据提供者初始化成功")

# 测试1: 获取质量指标
print("\n1. 测试质量指标获取...")
try:
    metrics = provider.get_quality_metrics()
    print(f"✅ 质量指标: {len(metrics)} 个")
    for key, value in metrics.items():
        print(f"   - {key}: {value:.2%}")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试2: 获取数据源质量
print("\n2. 测试数据源质量获取...")
try:
    sources = provider.get_data_sources_quality()
    print(f"✅ 数据源: {len(sources)} 个")
    for source in sources:
        print(f"   - {source['name']}: {'连接' if source['connected'] else '断开'} (评分: {source['score']:.2f})")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试3: 获取数据类型质量
print("\n3. 测试数据类型质量获取...")
try:
    datatypes = provider.get_datatypes_quality()
    print(f"✅ 数据类型: {len(datatypes)} 个")
    for dt in datatypes:
        print(f"   - {dt['type']}: {dt['count']:,} 条记录 (评分: {dt['score']:.2f})")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试4: 获取异常统计
print("\n4. 测试异常统计获取...")
try:
    stats = provider.get_anomaly_stats()
    print(f"✅ 异常统计:")
    print(f"   - 今日异常: {stats.get('today_anomalies', 0)}")
    print(f"   - 本周异常: {stats.get('week_anomalies', 0)}")
    print(f"   - 严重异常: {stats.get('critical_anomalies', 0)}")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试5: 获取异常记录
print("\n5. 测试异常记录获取...")
try:
    anomalies = provider.get_anomaly_records()
    print(f"✅ 异常记录: {len(anomalies)} 条")
    for i, anomaly in enumerate(anomalies[:3]):  # 只显示前3条
        print(f"   {i+1}. {anomaly.get('severity')} - {anomaly.get('description', 'N/A')}")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
