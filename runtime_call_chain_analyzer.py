#!/usr/bin/env python3
"""
运行时调用链分析器
================

通过动态装饰器和钩子来追踪实际运行时的方法调用链和性能数据
"""

import sys
import time
import functools
import threading
import traceback
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@dataclass
class CallRecord:
    """调用记录"""
    function_name: str
    module_name: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    depth: int = 0
    parent_call: Optional[str] = None
    children: List[str] = field(default_factory=list)
    exception: Optional[str] = None
    memory_usage: float = 0.0
    cpu_time: float = 0.0


class RuntimeCallChainAnalyzer:
    """运行时调用链分析器"""

    def __init__(self):
        self.call_records = {}
        self.call_stack = deque()
        self.current_depth = 0
        self.enabled = False
        self.lock = threading.Lock()
        self.target_modules = set()
        self.call_counts = defaultdict(int)
        self.total_times = defaultdict(float)
        self.max_times = defaultdict(float)
        self.min_times = defaultdict(lambda: float('inf'))

    def enable(self, target_modules: List[str] = None):
        """启用调用链分析"""
        self.enabled = True
        if target_modules:
            self.target_modules = set(target_modules)
        print("🔍 运行时调用链分析已启用")

    def disable(self):
        """禁用调用链分析"""
        self.enabled = False
        print("🔍 运行时调用链分析已禁用")

    def should_trace(self, module_name: str) -> bool:
        """判断是否应该追踪此模块"""
        if not self.target_modules:
            return True

        return any(target in module_name for target in self.target_modules)

    def trace_calls(self, func: Callable) -> Callable:
        """调用追踪装饰器"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            module_name = func.__module__ or 'unknown'
            if not self.should_trace(module_name):
                return func(*args, **kwargs)

            func_name = f"{module_name}.{func.__qualname__}"
            call_id = f"{func_name}_{id(threading.current_thread())}_{time.time()}"

            with self.lock:
                # 记录调用开始
                start_time = time.perf_counter()

                parent_call = None
                if self.call_stack:
                    parent_call = self.call_stack[-1]

                call_record = CallRecord(
                    function_name=func_name,
                    module_name=module_name,
                    start_time=start_time,
                    depth=self.current_depth,
                    parent_call=parent_call
                )

                self.call_records[call_id] = call_record
                self.call_stack.append(call_id)
                self.current_depth += 1

                # 更新父调用的子调用列表
                if parent_call and parent_call in self.call_records:
                    self.call_records[parent_call].children.append(call_id)

            try:
                # 执行函数
                result = func(*args, **kwargs)

                with self.lock:
                    # 记录调用结束
                    end_time = time.perf_counter()
                    duration = end_time - start_time

                    call_record.end_time = end_time
                    call_record.duration = duration

                    # 更新统计信息
                    self.call_counts[func_name] += 1
                    self.total_times[func_name] += duration
                    self.max_times[func_name] = max(self.max_times[func_name], duration)
                    self.min_times[func_name] = min(self.min_times[func_name], duration)

                    # 出栈
                    if self.call_stack and self.call_stack[-1] == call_id:
                        self.call_stack.pop()
                        self.current_depth -= 1

                return result

            except Exception as e:
                with self.lock:
                    # 记录异常
                    end_time = time.perf_counter()
                    duration = end_time - start_time

                    call_record.end_time = end_time
                    call_record.duration = duration
                    call_record.exception = str(e)

                    # 更新统计信息
                    self.call_counts[func_name] += 1
                    self.total_times[func_name] += duration

                    # 出栈
                    if self.call_stack and self.call_stack[-1] == call_id:
                        self.call_stack.pop()
                        self.current_depth -= 1

                raise

        return wrapper

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.call_records:
            return {"error": "没有调用记录"}

        # 计算总体统计
        total_calls = len(self.call_records)
        total_duration = sum(record.duration for record in self.call_records.values())

        # 按函数聚合统计
        function_stats = {}
        for func_name in self.call_counts:
            avg_time = self.total_times[func_name] / self.call_counts[func_name]
            function_stats[func_name] = {
                'call_count': self.call_counts[func_name],
                'total_time': self.total_times[func_name],
                'avg_time': avg_time,
                'max_time': self.max_times[func_name],
                'min_time': self.min_times[func_name],
                'percentage': (self.total_times[func_name] / total_duration * 100) if total_duration > 0 else 0
            }

        # 找出最耗时的调用
        slowest_calls = sorted(
            [(call_id, record) for call_id, record in self.call_records.items()],
            key=lambda x: x[1].duration,
            reverse=True
        )[:10]

        # 找出最深的调用链
        deepest_calls = sorted(
            [(call_id, record) for call_id, record in self.call_records.items()],
            key=lambda x: x[1].depth,
            reverse=True
        )[:5]

        # 分析调用链模式
        call_chains = self._analyze_call_chains()

        return {
            'total_calls': total_calls,
            'total_duration': total_duration,
            'unique_functions': len(function_stats),
            'function_stats': function_stats,
            'slowest_calls': [(call_id, {
                'function': record.function_name,
                'duration': record.duration,
                'depth': record.depth,
                'exception': record.exception
            }) for call_id, record in slowest_calls],
            'deepest_calls': [(call_id, {
                'function': record.function_name,
                'depth': record.depth,
                'duration': record.duration
            }) for call_id, record in deepest_calls],
            'call_chains': call_chains
        }

    def _analyze_call_chains(self) -> Dict[str, Any]:
        """分析调用链模式"""
        # 找出根调用（没有父调用的）
        root_calls = [
            (call_id, record) for call_id, record in self.call_records.items()
            if record.parent_call is None
        ]

        chains = []
        for call_id, record in root_calls:
            chain = self._build_call_chain(call_id, record)
            if chain:
                chains.append(chain)

        # 分析链的特征
        if chains:
            max_depth = max(chain['depth'] for chain in chains)
            avg_depth = sum(chain['depth'] for chain in chains) / len(chains)
            longest_chain = max(chains, key=lambda x: x['depth'])
            slowest_chain = max(chains, key=lambda x: x['total_duration'])
        else:
            max_depth = avg_depth = 0
            longest_chain = slowest_chain = None

        return {
            'total_chains': len(chains),
            'max_depth': max_depth,
            'avg_depth': avg_depth,
            'longest_chain': longest_chain,
            'slowest_chain': slowest_chain
        }

    def _build_call_chain(self, call_id: str, record: CallRecord) -> Optional[Dict[str, Any]]:
        """构建调用链"""
        chain = {
            'root_function': record.function_name,
            'depth': self._get_chain_depth(call_id),
            'total_duration': record.duration,
            'call_path': self._get_call_path(call_id)
        }

        return chain

    def _get_chain_depth(self, call_id: str) -> int:
        """获取调用链深度"""
        record = self.call_records.get(call_id)
        if not record or not record.children:
            return 1

        max_child_depth = 0
        for child_id in record.children:
            child_depth = self._get_chain_depth(child_id)
            max_child_depth = max(max_child_depth, child_depth)

        return 1 + max_child_depth

    def _get_call_path(self, call_id: str, path: List[str] = None) -> List[str]:
        """获取调用路径"""
        if path is None:
            path = []

        record = self.call_records.get(call_id)
        if not record:
            return path

        path.append(record.function_name.split('.')[-1])

        # 找出最耗时的子调用
        if record.children:
            slowest_child = None
            max_duration = 0

            for child_id in record.children:
                child_record = self.call_records.get(child_id)
                if child_record and child_record.duration > max_duration:
                    max_duration = child_record.duration
                    slowest_child = child_id

            if slowest_child:
                return self._get_call_path(slowest_child, path)

        return path

    def generate_analysis_report(self) -> str:
        """生成分析报告"""
        summary = self.get_performance_summary()

        if "error" in summary:
            return summary["error"]

        report = []
        report.append("# 运行时调用链性能分析报告")
        report.append("=" * 60)

        # 总体统计
        report.append(f"\n## 📊 运行时统计")
        report.append(f"- 总调用次数: {summary['total_calls']:,}")
        report.append(f"- 总执行时间: {summary['total_duration']:.4f} 秒")
        report.append(f"- 唯一函数数: {summary['unique_functions']}")

        # 调用链统计
        chains = summary['call_chains']
        report.append(f"- 调用链数量: {chains['total_chains']}")
        report.append(f"- 最大调用深度: {chains['max_depth']}")
        report.append(f"- 平均调用深度: {chains['avg_depth']:.1f}")

        # 最耗时的函数
        function_stats = summary['function_stats']
        top_functions = sorted(
            function_stats.items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )[:10]

        if top_functions:
            report.append(f"\n## ⏱️ 最耗时的函数 (Top 10)")
            for i, (func_name, stats) in enumerate(top_functions, 1):
                short_name = func_name.split('.')[-1]
                report.append(f"{i}. **{short_name}**")
                report.append(f"   - 总耗时: {stats['total_time']:.4f}秒 ({stats['percentage']:.1f}%)")
                report.append(f"   - 调用次数: {stats['call_count']}")
                report.append(f"   - 平均耗时: {stats['avg_time']:.6f}秒")
                report.append(f"   - 最大耗时: {stats['max_time']:.6f}秒")

        # 最慢的单次调用
        if summary['slowest_calls']:
            report.append(f"\n## 🐌 最慢的单次调用 (Top 5)")
            for i, (call_id, call_info) in enumerate(summary['slowest_calls'][:5], 1):
                short_name = call_info['function'].split('.')[-1]
                report.append(f"{i}. **{short_name}**: {call_info['duration']:.4f}秒")
                report.append(f"   - 调用深度: {call_info['depth']}")
                if call_info['exception']:
                    report.append(f"   - 异常: {call_info['exception']}")

        # 最深的调用链
        if summary['deepest_calls']:
            report.append(f"\n## 🔗 最深的调用链")
            for i, (call_id, call_info) in enumerate(summary['deepest_calls'], 1):
                short_name = call_info['function'].split('.')[-1]
                report.append(f"{i}. **{short_name}** (深度: {call_info['depth']})")
                report.append(f"   - 执行时间: {call_info['duration']:.4f}秒")

        # 调用链分析
        if chains['longest_chain']:
            report.append(f"\n## 📈 调用链分析")
            longest = chains['longest_chain']
            report.append(f"**最长调用链**:")
            report.append(f"- 根函数: {longest['root_function'].split('.')[-1]}")
            report.append(f"- 调用深度: {longest['depth']}")
            report.append(f"- 总耗时: {longest['total_duration']:.4f}秒")
            if longest['call_path']:
                path_str = " → ".join(longest['call_path'])
                report.append(f"- 调用路径: {path_str}")

        if chains['slowest_chain']:
            slowest = chains['slowest_chain']
            report.append(f"\n**最慢调用链**:")
            report.append(f"- 根函数: {slowest['root_function'].split('.')[-1]}")
            report.append(f"- 总耗时: {slowest['total_duration']:.4f}秒")
            report.append(f"- 调用深度: {slowest['depth']}")
            if slowest['call_path']:
                path_str = " → ".join(slowest['call_path'])
                report.append(f"- 调用路径: {path_str}")

        return "\n".join(report)

    def save_raw_data(self, filename: str = "call_chain_raw_data.json"):
        """保存原始调用数据"""
        data = {
            'call_records': {
                call_id: {
                    'function_name': record.function_name,
                    'module_name': record.module_name,
                    'start_time': record.start_time,
                    'end_time': record.end_time,
                    'duration': record.duration,
                    'depth': record.depth,
                    'parent_call': record.parent_call,
                    'children': record.children,
                    'exception': record.exception
                }
                for call_id, record in self.call_records.items()
            },
            'statistics': {
                'call_counts': dict(self.call_counts),
                'total_times': dict(self.total_times),
                'max_times': dict(self.max_times),
                'min_times': {k: v for k, v in self.min_times.items() if v != float('inf')}
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"📄 原始调用数据已保存到 {filename}")


def create_backtest_tracer():
    """创建回测系统追踪器"""
    analyzer = RuntimeCallChainAnalyzer()

    # 设置要追踪的模块
    target_modules = [
        'backtest',
        'plugins.strategies',
        'core.metrics',
        'gui.widgets.backtest'
    ]

    analyzer.enable(target_modules)
    return analyzer


def patch_backtest_methods(analyzer: RuntimeCallChainAnalyzer):
    """为回测系统的关键方法添加追踪装饰器"""
    try:
        # 导入并装饰UnifiedBacktestEngine
        from backtest.unified_backtest_engine import UnifiedBacktestEngine

        # 装饰关键方法
        key_methods = [
            'run_backtest',
            '_run_core_backtest',
            '_process_trading_signals',
            '_execute_open_position',
            '_check_exit_conditions',
            '_calculate_unified_risk_metrics'
        ]

        for method_name in key_methods:
            if hasattr(UnifiedBacktestEngine, method_name):
                original_method = getattr(UnifiedBacktestEngine, method_name)
                decorated_method = analyzer.trace_calls(original_method)
                setattr(UnifiedBacktestEngine, method_name, decorated_method)
                print(f"✅ 已装饰 UnifiedBacktestEngine.{method_name}")

        # 装饰策略插件
        try:
            from plugins.strategies.hikyuu_strategy_plugin import HikyuuStrategyPlugin

            hikyuu_methods = ['run_backtest', 'create_trading_system']
            for method_name in hikyuu_methods:
                if hasattr(HikyuuStrategyPlugin, method_name):
                    original_method = getattr(HikyuuStrategyPlugin, method_name)
                    decorated_method = analyzer.trace_calls(original_method)
                    setattr(HikyuuStrategyPlugin, method_name, decorated_method)
                    print(f"✅ 已装饰 HikyuuStrategyPlugin.{method_name}")

        except ImportError as e:
            print(f"⚠️ 无法导入 HikyuuStrategyPlugin: {e}")

        # 装饰指标仓库
        try:
            from core.metrics.repository import MetricsRepository

            metrics_methods = ['save_metric', 'get_latest_metric', 'query_metrics']
            for method_name in metrics_methods:
                if hasattr(MetricsRepository, method_name):
                    original_method = getattr(MetricsRepository, method_name)
                    decorated_method = analyzer.trace_calls(original_method)
                    setattr(MetricsRepository, method_name, decorated_method)
                    print(f"✅ 已装饰 MetricsRepository.{method_name}")

        except ImportError as e:
            print(f"⚠️ 无法导入 MetricsRepository: {e}")

        return True

    except ImportError as e:
        print(f"❌ 无法导入回测引擎: {e}")
        return False


def main():
    """主函数 - 演示如何使用运行时调用链分析器"""
    print("🚀 运行时调用链分析器演示")
    print("=" * 50)

    # 创建分析器
    analyzer = create_backtest_tracer()

    # 尝试装饰回测系统的方法
    if patch_backtest_methods(analyzer):
        print("✅ 回测系统方法装饰完成")
    else:
        print("❌ 回测系统方法装饰失败")

    # 模拟一些调用来演示功能
    @analyzer.trace_calls
    def demo_backtest_function():
        """演示回测函数"""
        time.sleep(0.01)  # 模拟计算时间
        demo_signal_processing()
        demo_risk_calculation()
        return "backtest_complete"

    @analyzer.trace_calls
    def demo_signal_processing():
        """演示信号处理"""
        time.sleep(0.005)
        for i in range(3):
            demo_trade_execution()

    @analyzer.trace_calls
    def demo_trade_execution():
        """演示交易执行"""
        time.sleep(0.002)

    @analyzer.trace_calls
    def demo_risk_calculation():
        """演示风险计算"""
        time.sleep(0.008)
        demo_metrics_calculation()

    @analyzer.trace_calls
    def demo_metrics_calculation():
        """演示指标计算"""
        time.sleep(0.003)

    # 运行演示
    print("\n🔍 运行演示回测...")
    start_time = time.time()

    for i in range(3):
        demo_backtest_function()

    end_time = time.time()

    # 禁用追踪
    analyzer.disable()

    # 生成报告
    print(f"\n📊 演示完成，总耗时: {end_time - start_time:.4f}秒")

    # 获取性能摘要
    summary = analyzer.get_performance_summary()
    print(f"📈 捕获了 {summary['total_calls']} 次调用")
    print(f"📈 涉及 {summary['unique_functions']} 个唯一函数")

    # 生成详细报告
    report = analyzer.generate_analysis_report()

    # 保存报告
    with open('runtime_call_chain_analysis.md', 'w', encoding='utf-8') as f:
        f.write(report)

    # 保存原始数据
    analyzer.save_raw_data()

    print("📄 运行时调用链分析报告已保存到 runtime_call_chain_analysis.md")
    print("📄 原始调用数据已保存到 call_chain_raw_data.json")

    return analyzer


if __name__ == "__main__":
    main()
