#!/usr/bin/env python3
"""
阶段1 性能基准测试脚本

对比 _standardize_kline_data_fields() 和 TETDataPipeline.transform_data() 的性能
测试数据: 10000 条 K 线记录
"""

import sys
import os
import pandas as pd
import numpy as np
import time
import psutil
import tracemalloc
from typing import Dict, Tuple, List
from datetime import datetime, timedelta
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入相关组件
from core.importdata.import_execution_engine import ImportExecutionEngine
from core.tet_data_pipeline import TETDataPipeline, StandardQuery, DataType
from core.plugin_types import AssetType


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        self.import_engine = ImportExecutionEngine()
        self.tet_pipeline = TETDataPipeline()
        self.results = {
            'quick_standardization': [],
            'tet_pipeline': [],
            'summary': {}
        }
        self.test_data = None
        
    def generate_test_data(self, num_records: int = 10000) -> pd.DataFrame:
        """生成测试数据 - 模拟通达信格式的K线数据"""
        print(f"生成 {num_records} 条测试数据...")
        
        dates = pd.date_range('2023-01-01', periods=num_records, freq='D')
        base_price = 100.0
        
        data = pd.DataFrame({
            'Datetime': dates,
            'Open': base_price + np.random.randn(num_records) * 2,
            'High': base_price + np.random.randn(num_records) * 3,
            'Low': base_price + np.random.randn(num_records) * 2.5,
            'Close': base_price + np.random.randn(num_records) * 2,
            'Volume': np.random.randint(1000000, 10000000, num_records),
            'Amount': np.random.randint(500000000, 5000000000, num_records)
        })
        
        # 确保 High >= max(Open, Close) 和 Low <= min(Open, Close)
        data['High'] = data[['Open', 'High', 'Close']].max(axis=1) * 1.01
        data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1) * 0.99
        
        self.test_data = data
        print(f"✓ 测试数据生成完成，形状: {data.shape}")
        return data
    
    def measure_execution_time_and_memory(self, func, *args, **kwargs) -> Tuple[float, float, float, float]:
        """测量函数执行时间和内存占用
        
        返回: (执行时间, 峰值内存, 平均内存, CPU占用百分比)
        """
        # 启动内存追踪
        tracemalloc.start()
        process = psutil.Process()
        
        # 记录开始状态
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()
        
        # 执行函数
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"  ❌ 执行出错: {e}")
            tracemalloc.stop()
            return None
        
        # 记录结束状态
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = process.cpu_percent()
        
        # 获取内存峰值
        current, peak = tracemalloc.get_traced_memory()
        peak_memory = peak / 1024 / 1024  # MB
        tracemalloc.stop()
        
        elapsed_time = end_time - start_time
        memory_used = end_memory - start_memory
        avg_cpu = (start_cpu + end_cpu) / 2
        
        return elapsed_time, peak_memory, memory_used, avg_cpu, result
    
    def test_quick_standardization(self, iterations: int = 10):
        """测试快速标准化方法"""
        print(f"\n【测试快速标准化】运行 {iterations} 次...")
        
        data = self.test_data.copy()
        times = []
        peak_mems = []
        memory_used_list = []
        cpu_list = []
        
        for i in range(iterations):
            print(f"  运行 {i+1}/{iterations}...", end='')
            
            elapsed, peak_mem, mem_used, cpu_usage, _ = self.measure_execution_time_and_memory(
                self.import_engine._standardize_kline_data_fields,
                data.copy(),
                data_source='tongdaxin'
            )
            
            if elapsed is not None:
                times.append(elapsed)
                peak_mems.append(peak_mem)
                memory_used_list.append(mem_used)
                cpu_list.append(cpu_usage)
                print(f" ✓ {elapsed*1000:.2f}ms, 内存: {mem_used:.2f}MB")
            else:
                print(f" ✗ 执行失败")
        
        # 计算统计
        stats = {
            'iterations': len(times),
            'avg_time_ms': np.mean(times) * 1000 if times else 0,
            'min_time_ms': np.min(times) * 1000 if times else 0,
            'max_time_ms': np.max(times) * 1000 if times else 0,
            'std_time_ms': np.std(times) * 1000 if times else 0,
            'avg_peak_memory_mb': np.mean(peak_mems) if peak_mems else 0,
            'avg_memory_used_mb': np.mean(memory_used_list) if memory_used_list else 0,
            'avg_cpu_percent': np.mean(cpu_list) if cpu_list else 0
        }
        
        self.results['quick_standardization'] = stats
        print(f"✓ 快速标准化完成")
        print(f"  - 平均耗时: {stats['avg_time_ms']:.2f}ms")
        print(f"  - 最小耗时: {stats['min_time_ms']:.2f}ms")
        print(f"  - 最大耗时: {stats['max_time_ms']:.2f}ms")
        print(f"  - 平均内存峰值: {stats['avg_peak_memory_mb']:.2f}MB")
        print(f"  - 平均 CPU: {stats['avg_cpu_percent']:.2f}%")
        
        return stats
    
    def test_tet_pipeline(self, iterations: int = 10):
        """测试 TET 管道"""
        print(f"\n【测试 TET 管道】运行 {iterations} 次...")
        
        data = self.test_data.copy()
        times = []
        peak_mems = []
        memory_used_list = []
        cpu_list = []
        
        for i in range(iterations):
            print(f"  运行 {i+1}/{iterations}...", end='')
            
            query = StandardQuery(
                data_type=DataType.HISTORICAL_KLINE,
                asset_type=AssetType.STOCK_A,
                provider='tongdazhin',
                period='D'
            )
            
            elapsed, peak_mem, mem_used, cpu_usage, result = self.measure_execution_time_and_memory(
                self.tet_pipeline.transform_data,
                data.copy(),
                query
            )
            
            if elapsed is not None:
                times.append(elapsed)
                peak_mems.append(peak_mem)
                memory_used_list.append(mem_used)
                cpu_list.append(cpu_usage)
                print(f" ✓ {elapsed*1000:.2f}ms, 内存: {mem_used:.2f}MB")
            else:
                print(f" ✗ 执行失败")
        
        # 计算统计
        stats = {
            'iterations': len(times),
            'avg_time_ms': np.mean(times) * 1000 if times else 0,
            'min_time_ms': np.min(times) * 1000 if times else 0,
            'max_time_ms': np.max(times) * 1000 if times else 0,
            'std_time_ms': np.std(times) * 1000 if times else 0,
            'avg_peak_memory_mb': np.mean(peak_mems) if peak_mems else 0,
            'avg_memory_used_mb': np.mean(memory_used_list) if memory_used_list else 0,
            'avg_cpu_percent': np.mean(cpu_list) if cpu_list else 0
        }
        
        self.results['tet_pipeline'] = stats
        print(f"✓ TET 管道测试完成")
        print(f"  - 平均耗时: {stats['avg_time_ms']:.2f}ms")
        print(f"  - 最小耗时: {stats['min_time_ms']:.2f}ms")
        print(f"  - 最大耗时: {stats['max_time_ms']:.2f}ms")
        print(f"  - 平均内存峰值: {stats['avg_peak_memory_mb']:.2f}MB")
        print(f"  - 平均 CPU: {stats['avg_cpu_percent']:.2f}%")
        
        return stats
    
    def compare_results(self):
        """对比测试结果"""
        print("\n【性能对比】")
        
        quick = self.results['quick_standardization']
        tet = self.results['tet_pipeline']
        
        if not quick or not tet:
            print("❌ 没有完整的测试结果")
            return
        
        # 计算性能差异
        time_diff_percent = ((tet['avg_time_ms'] - quick['avg_time_ms']) / quick['avg_time_ms'] * 100) if quick['avg_time_ms'] > 0 else 0
        memory_diff_percent = ((tet['avg_peak_memory_mb'] - quick['avg_peak_memory_mb']) / quick['avg_peak_memory_mb'] * 100) if quick['avg_peak_memory_mb'] > 0 else 0
        
        print(f"\n【耗时对比】")
        print(f"快速标准化: {quick['avg_time_ms']:.2f}ms (±{quick['std_time_ms']:.2f}ms)")
        print(f"TET 管道:   {tet['avg_time_ms']:.2f}ms (±{tet['std_time_ms']:.2f}ms)")
        print(f"差异:      {time_diff_percent:+.2f}% {'📈 变慢' if time_diff_percent > 0 else '📉 变快'}")
        
        print(f"\n【内存对比】")
        print(f"快速标准化: {quick['avg_peak_memory_mb']:.2f}MB")
        print(f"TET 管道:   {tet['avg_peak_memory_mb']:.2f}MB")
        print(f"差异:      {memory_diff_percent:+.2f}%")
        
        print(f"\n【CPU 占用对比】")
        print(f"快速标准化: {quick['avg_cpu_percent']:.2f}%")
        print(f"TET 管道:   {tet['avg_cpu_percent']:.2f}%")
        
        # 推进建议
        print(f"\n【推进建议】")
        if abs(time_diff_percent) < 10:
            print("✅ 性能差异 < 10%，建议推进到阶段2")
            self.results['summary']['recommendation'] = 'PROCEED'
        elif abs(time_diff_percent) < 15:
            print("⚠️  性能差异 10-15%，建议进行优化后推进")
            self.results['summary']['recommendation'] = 'OPTIMIZE_THEN_PROCEED'
        else:
            print("❌ 性能差异 > 15%，建议进行深入优化")
            self.results['summary']['recommendation'] = 'REQUIRES_OPTIMIZATION'
        
        self.results['summary']['time_diff_percent'] = time_diff_percent
        self.results['summary']['memory_diff_percent'] = memory_diff_percent
    
    def save_results(self, output_file: str = 'phase1_performance_benchmark_results.json'):
        """保存测试结果"""
        output_path = Path(__file__).parent / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 测试结果已保存到: {output_path}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("K线数据导入性能基准测试")
        print("=" * 60)
        
        # 生成测试数据
        self.generate_test_data(num_records=10000)
        
        # 运行测试
        self.test_quick_standardization(iterations=5)  # 先做5次测试
        self.test_tet_pipeline(iterations=5)           # 再做5次测试
        
        # 对比结果
        self.compare_results()
        
        # 保存结果
        self.save_results()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)


def main():
    """主函数"""
    try:
        benchmark = PerformanceBenchmark()
        benchmark.run_all_tests()
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
