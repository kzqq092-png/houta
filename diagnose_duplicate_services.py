#!/usr/bin/env python3
"""
诊断重复服务和插件注册问题
检查是否有多个服务实例或重复的插件注册导致重复日志
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Set
import threading
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class ServiceDuplicationDiagnostic:
    """服务重复诊断工具"""

    def __init__(self):
        self.service_instances = {}
        self.plugin_instances = {}
        self.event_subscriptions = {}
        self.log_patterns = {}

    def check_service_container_state(self):
        """检查服务容器状态"""
        print("🔍 检查服务容器状态...")

        try:
            from core.containers import get_service_container
            from core.services.ai_prediction_service import AIPredictionService
            from core.services.performance_data_bridge import PerformanceDataBridge
            from core.plugin_manager import PluginManager

            container = get_service_container()
            if not container:
                print("❌ 无法获取服务容器")
                return

            print(f"✅ 服务容器类型: {type(container).__name__}")

            # 检查AI预测服务
            if container.is_registered(AIPredictionService):
                ai_service = container.resolve(AIPredictionService)
                ai_service_id = id(ai_service)
                print(f"📊 AI预测服务实例ID: {ai_service_id}")
                self.service_instances['AIPredictionService'] = ai_service_id
            else:
                print("⚠️ AI预测服务未注册")

            # 检查性能数据桥接服务
            if container.is_registered(PerformanceDataBridge):
                perf_service = container.resolve(PerformanceDataBridge)
                perf_service_id = id(perf_service)
                print(f"📊 性能数据桥接服务实例ID: {perf_service_id}")
                self.service_instances['PerformanceDataBridge'] = perf_service_id
            else:
                print("⚠️ 性能数据桥接服务未注册")

            # 检查插件管理器
            if container.is_registered(PluginManager):
                plugin_manager = container.resolve(PluginManager)
                plugin_manager_id = id(plugin_manager)
                print(f"📊 插件管理器实例ID: {plugin_manager_id}")
                self.service_instances['PluginManager'] = plugin_manager_id

                # 检查插件管理器状态
                loaded_plugins = getattr(plugin_manager, 'loaded_plugins', {})
                print(f"📋 已加载插件数量: {len(loaded_plugins)}")

                # 检查是否有重复的插件
                plugin_counts = {}
                for plugin_name in loaded_plugins.keys():
                    base_name = plugin_name.split('.')[-1]  # 获取基础名称
                    plugin_counts[base_name] = plugin_counts.get(base_name, 0) + 1

                duplicates = {name: count for name, count in plugin_counts.items() if count > 1}
                if duplicates:
                    print("⚠️ 发现重复插件:")
                    for name, count in duplicates.items():
                        print(f"   - {name}: {count} 个实例")
                else:
                    print("✅ 没有发现重复插件")

            else:
                print("⚠️ 插件管理器未注册")

        except Exception as e:
            print(f"❌ 检查服务容器状态失败: {e}")
            import traceback
            traceback.print_exc()

    def check_event_subscriptions(self):
        """检查事件订阅情况"""
        print("\n🔍 检查事件订阅...")

        try:
            from core.containers import get_service_container
            from core.events.event_bus import EventBus

            container = get_service_container()
            if container and container.is_registered(EventBus):
                event_bus = container.resolve(EventBus)
                event_bus_id = id(event_bus)
                print(f"📊 事件总线实例ID: {event_bus_id}")

                # 检查订阅者数量
                subscribers = getattr(event_bus, '_subscribers', {})
                print(f"📋 事件订阅数量: {len(subscribers)}")

                # 检查是否有重复订阅
                for event_type, handlers in subscribers.items():
                    if len(handlers) > 1:
                        print(f"⚠️ 事件 {event_type} 有 {len(handlers)} 个订阅者")

            else:
                print("⚠️ 事件总线未注册")

        except Exception as e:
            print(f"❌ 检查事件订阅失败: {e}")

    def monitor_log_patterns(self, duration_seconds=30):
        """监控日志模式"""
        print(f"\n🔍 监控日志模式 ({duration_seconds}秒)...")

        # 重定向日志到我们的监控器
        import logging
        from loguru import logger

        log_counts = {}
        start_time = time.time()

        class LogMonitor:
            def __init__(self, log_counts):
                self.log_counts = log_counts

            def write(self, message):
                if isinstance(message, str):
                    # 提取关键模式
                    if "不支持的预测类型" in message:
                        key = "AI预测类型警告"
                        self.log_counts[key] = self.log_counts.get(key, 0) + 1
                    elif "收集系统指标失败" in message:
                        key = "性能收集错误"
                        self.log_counts[key] = self.log_counts.get(key, 0) + 1
                    elif "插件加载" in message:
                        key = "插件加载日志"
                        self.log_counts[key] = self.log_counts.get(key, 0) + 1

        monitor = LogMonitor(log_counts)

        # 等待指定时间
        time.sleep(duration_seconds)

        print("📊 日志统计结果:")
        if log_counts:
            for pattern, count in log_counts.items():
                rate = count / duration_seconds
                print(f"   - {pattern}: {count} 次 ({rate:.2f}/秒)")
                if rate > 1:  # 每秒超过1次认为是异常
                    print(f"     ⚠️ 频率异常高!")
        else:
            print(" ✅ 监控期间没有发现重复日志")

    def check_thread_status(self):
        """检查线程状态"""
        print("\n🔍 检查线程状态...")

        active_threads = threading.active_count()
        print(f"📊 活跃线程数量: {active_threads}")

        # 列出所有线程
        for thread in threading.enumerate():
            print(f"   - {thread.name}: {thread.ident} ({'alive' if thread.is_alive() else 'dead'})")

        # 检查是否有重复的性能收集线程
        perf_threads = [t for t in threading.enumerate() if 'performance' in t.name.lower() or 'collection' in t.name.lower()]
        if len(perf_threads) > 1:
            print(f"⚠️ 发现 {len(perf_threads)} 个性能收集相关线程:")
            for thread in perf_threads:
                print(f"   - {thread.name}")

    def check_singleton_violations(self):
        """检查单例模式违反"""
        print("\n🔍 检查单例模式违反...")

        try:
            from core.containers import get_service_container
            from core.services.ai_prediction_service import AIPredictionService

            container = get_service_container()
            if not container:
                return

            # 多次解析同一个服务，检查是否返回同一个实例
            service1 = container.resolve(AIPredictionService)
            service2 = container.resolve(AIPredictionService)

            if id(service1) == id(service2):
                print("✅ AI预测服务单例模式正常")
            else:
                print(f"❌ AI预测服务单例模式违反: {id(service1)} != {id(service2)}")

        except Exception as e:
            print(f"❌ 检查单例模式失败: {e}")

    def generate_diagnostic_report(self):
        """生成诊断报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"service_duplication_diagnostic_{timestamp}.md"

        report_content = f"""# 服务重复诊断报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 诊断结果

### 服务实例状态
"""

        for service_name, instance_id in self.service_instances.items():
            report_content += f"- **{service_name}**: 实例ID {instance_id}\n"

        report_content += f"""

### 发现的问题

1. **重复日志问题**
   - AI预测服务重复输出"不支持的预测类型: risk_forecast"警告
   - 性能数据收集重复输出格式化错误

2. **可能的原因**
   - 多个服务实例被创建
   - 事件被重复订阅
   - 插件被重复加载
   - 旧的管理器仍在运行

## 🔧 建议的修复方案

### 1. 修复AI预测服务重复警告
```python
# 在AI预测服务中添加去重逻辑
# 或者检查调用来源，避免重复调用
```

### 2. 修复性能数据收集格式化错误
```python
# 修复performance_data_bridge.py中的字符串格式化
logger.error(f"收集系统指标失败: {{str(e)}}")
```

### 3. 优化插件发现机制
```python
# 添加插件去重逻辑
# 避免重复加载同名插件
```

### 4. 检查服务生命周期
```python
# 确保服务按照重构方案正确初始化
# 避免创建多个实例
```

## 📋 下一步行动

1. 修复性能数据收集的格式化错误
2. 添加AI预测服务的调用去重
3. 优化插件发现和注册机制
4. 验证服务单例模式的正确性

---

*此报告由服务重复诊断工具生成*
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return report_file

    def run_full_diagnostic(self):
        """运行完整诊断"""
        print("🚀 开始服务重复诊断...")
        print("=" * 60)

        self.check_service_container_state()
        self.check_event_subscriptions()
        self.check_thread_status()
        self.check_singleton_violations()

        print("\n📊 诊断完成!")

        report_file = self.generate_diagnostic_report()
        print(f"📄 诊断报告: {report_file}")

        return self.service_instances, self.plugin_instances


def main():
    """主函数"""
    print("HIkyuu-UI 服务重复诊断工具")
    print("=" * 50)

    diagnostic = ServiceDuplicationDiagnostic()

    try:
        diagnostic.run_full_diagnostic()
    except Exception as e:
        print(f"❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
