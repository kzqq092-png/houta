from loguru import logger
"""
WebGPU性能基准测试系统

提供全面的性能测试功能：
- 图表渲染性能测试
- 内存使用监控
- GPU利用率测试
- 帧率测试
- 与传统渲染方式对比分析
- 自动化性能回归检测

作者: HIkyuu团队
版本: 1.0.0
"""

import time
import json
import threading
import statistics
import psutil
import gc
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from pathlib import Path
import numpy as np

logger = logger

class BenchmarkType(Enum):
    """基准测试类型"""
    RENDERING = "rendering"      # 渲染性能
    MEMORY = "memory"           # 内存使用
    GPU_UTILIZATION = "gpu"     # GPU利用率
    FRAME_RATE = "framerate"    # 帧率
    COMPARISON = "comparison"   # 对比测试

class RenderingEngine(Enum):
    """渲染引擎类型"""
    WEBGPU = "webgpu"
    OPENGL = "opengl"
    CANVAS2D = "canvas2d"
    MATPLOTLIB = "matplotlib"
    SOFTWARE = "software"

@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 渲染性能
    render_time_ms: float = 0.0
    frame_rate: float = 0.0
    frames_rendered: int = 0

    # 内存使用
    memory_usage_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0

    # GPU相关
    gpu_utilization_percent: float = 0.0
    gpu_temperature: float = 0.0

    # 用户体验
    input_latency_ms: float = 0.0
    scroll_smoothness: float = 0.0
    zoom_responsiveness: float = 0.0

    # 统计数据
    min_frame_time: float = 0.0
    max_frame_time: float = 0.0
    avg_frame_time: float = 0.0
    frame_time_std: float = 0.0

@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    test_duration_seconds: int = 30
    target_fps: int = 60
    data_points: int = 1000
    chart_width: int = 1920
    chart_height: int = 1080
    enable_memory_profiling: bool = True
    enable_gpu_monitoring: bool = True
    warm_up_time: int = 5
    cooldown_time: int = 2

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    benchmark_type: BenchmarkType
    rendering_engine: RenderingEngine
    config: BenchmarkConfig
    metrics: PerformanceMetrics
    raw_data: Dict[str, List[float]] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    success: bool = True
    error_message: str = ""

@dataclass
class ComparisonResult:
    """对比测试结果"""
    baseline_result: BenchmarkResult
    test_result: BenchmarkResult
    performance_improvement: float  # 百分比改进
    memory_improvement: float
    detailed_comparison: Dict[str, float] = field(default_factory=dict)

class MemoryMonitor:
    """内存监控器"""

    def __init__(self):
        self.monitoring = False
        self.memory_samples: List[float] = []
        self.gpu_memory_samples: List[float] = []
        self.monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self) -> None:
        """开始内存监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.memory_samples.clear()
        self.gpu_memory_samples.clear()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("内存监控已启动")

    def stop_monitoring(self) -> Dict[str, float]:
        """停止内存监控并返回统计结果"""
        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        if not self.memory_samples:
            return {'avg_memory': 0.0, 'peak_memory': 0.0, 'avg_gpu_memory': 0.0}

        memory_stats = {
            'avg_memory': statistics.mean(self.memory_samples),
            'peak_memory': max(self.memory_samples),
            'min_memory': min(self.memory_samples),
            'memory_std': statistics.stdev(self.memory_samples) if len(self.memory_samples) > 1 else 0.0
        }

        if self.gpu_memory_samples:
            memory_stats.update({
                'avg_gpu_memory': statistics.mean(self.gpu_memory_samples),
                'peak_gpu_memory': max(self.gpu_memory_samples)
            })

        logger.info(f"内存监控已停止，统计结果: {memory_stats}")
        return memory_stats

    def _monitor_loop(self) -> None:
        """内存监控循环"""
        while self.monitoring:
            try:
                # 获取系统内存使用
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                self.memory_samples.append(memory_mb)

                # 尝试获取GPU内存使用（如果可用）
                gpu_memory = self._get_gpu_memory_usage()
                if gpu_memory is not None:
                    self.gpu_memory_samples.append(gpu_memory)

                time.sleep(1)  # 1000ms采样间隔

            except Exception as e:
                logger.warning(f"内存监控异常: {e}")
                time.sleep(0.5)

    def _get_gpu_memory_usage(self) -> Optional[float]:
        """获取GPU内存使用（MB）"""
        try:
            # 尝试使用nvidia-smi获取NVIDIA GPU内存
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                memory_mb = float(result.stdout.strip().split('\n')[0])
                return memory_mb
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        # TODO: 添加AMD和Intel GPU内存监控支持
        return None

class FrameRateMonitor:
    """帧率监控器"""

    def __init__(self):
        self.frame_times: List[float] = []
        self.last_frame_time: float = 0.0
        self.monitoring = False

    def start_monitoring(self) -> None:
        """开始帧率监控"""
        self.frame_times.clear()
        self.last_frame_time = time.time()
        self.monitoring = True
        logger.info("帧率监控已启动")

    def record_frame(self) -> None:
        """记录一帧"""
        if not self.monitoring:
            return

        current_time = time.time()
        if self.last_frame_time > 0:
            frame_time = current_time - self.last_frame_time
            self.frame_times.append(frame_time)

        self.last_frame_time = current_time

    def stop_monitoring(self) -> Dict[str, float]:
        """停止帧率监控并返回统计结果"""
        self.monitoring = False

        if not self.frame_times:
            return {'avg_fps': 0.0, 'min_fps': 0.0, 'max_fps': 0.0}

        # 计算帧率统计
        avg_frame_time = statistics.mean(self.frame_times)
        min_frame_time = min(self.frame_times)
        max_frame_time = max(self.frame_times)

        stats = {
            'avg_fps': 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0,
            'min_fps': 1.0 / max_frame_time if max_frame_time > 0 else 0.0,
            'max_fps': 1.0 / min_frame_time if min_frame_time > 0 else 0.0,
            'avg_frame_time': avg_frame_time * 1000,  # 转换为毫秒
            'frame_time_std': statistics.stdev(self.frame_times) * 1000 if len(self.frame_times) > 1 else 0.0,
            'total_frames': len(self.frame_times)
        }

        logger.info(f"帧率监控已停止，统计结果: {stats}")
        return stats

class GPUMonitor:
    """GPU监控器"""

    def __init__(self):
        self.monitoring = False
        self.gpu_utilization_samples: List[float] = []
        self.gpu_temperature_samples: List[float] = []
        self.monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self) -> None:
        """开始GPU监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.gpu_utilization_samples.clear()
        self.gpu_temperature_samples.clear()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("GPU监控已启动")

    def stop_monitoring(self) -> Dict[str, float]:
        """停止GPU监控并返回统计结果"""
        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        stats = {}

        if self.gpu_utilization_samples:
            stats.update({
                'avg_gpu_utilization': statistics.mean(self.gpu_utilization_samples),
                'max_gpu_utilization': max(self.gpu_utilization_samples),
                'min_gpu_utilization': min(self.gpu_utilization_samples)
            })

        if self.gpu_temperature_samples:
            stats.update({
                'avg_gpu_temperature': statistics.mean(self.gpu_temperature_samples),
                'max_gpu_temperature': max(self.gpu_temperature_samples)
            })

        logger.info(f"GPU监控已停止，统计结果: {stats}")
        return stats

    def _monitor_loop(self) -> None:
        """GPU监控循环"""
        while self.monitoring:
            try:
                # 获取GPU利用率和温度
                gpu_stats = self._get_gpu_stats()

                if gpu_stats.get('utilization') is not None:
                    self.gpu_utilization_samples.append(gpu_stats['utilization'])

                if gpu_stats.get('temperature') is not None:
                    self.gpu_temperature_samples.append(gpu_stats['temperature'])

                time.sleep(1.0)  # 1秒采样间隔

            except Exception as e:
                logger.warning(f"GPU监控异常: {e}")
                time.sleep(2.0)

    def _get_gpu_stats(self) -> Dict[str, Optional[float]]:
        """获取GPU统计信息"""
        stats = {'utilization': None, 'temperature': None}

        try:
            # 尝试使用nvidia-smi获取NVIDIA GPU信息
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=utilization.gpu,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=3)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split(', ')
                    if len(parts) >= 2:
                        stats['utilization'] = float(parts[0])
                        stats['temperature'] = float(parts[1])
                        break  # 只取第一个GPU的信息

        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
            # nvidia-smi不可用或出错
            pass

        # TODO: 添加AMD和Intel GPU监控支持
        return stats

class RenderingBenchmark:
    """渲染性能基准测试"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.memory_monitor = MemoryMonitor()
        self.frame_monitor = FrameRateMonitor()
        self.gpu_monitor = GPUMonitor()

    def run_rendering_test(self, rendering_engine: RenderingEngine,
                           render_function: Callable[[], None]) -> BenchmarkResult:
        """
        运行渲染性能测试

        Args:
            rendering_engine: 渲染引擎类型
            render_function: 渲染函数，应该渲染一帧并调用frame_monitor.record_frame()
        """
        logger.info(f"开始渲染性能测试: {rendering_engine.value}")

        test_name = f"Rendering Performance - {rendering_engine.value}"
        start_time = time.time()

        try:
            # 预热阶段
            logger.info("预热阶段...")
            self._warm_up(render_function)

            # 开始监控
            if self.config.enable_memory_profiling:
                self.memory_monitor.start_monitoring()

            if self.config.enable_gpu_monitoring:
                self.gpu_monitor.start_monitoring()

            self.frame_monitor.start_monitoring()

            # 主测试阶段
            logger.info(f"主测试阶段，持续 {self.config.test_duration_seconds} 秒...")
            test_start = time.time()
            frame_count = 0

            while time.time() - test_start < self.config.test_duration_seconds:
                frame_start = time.time()

                # 执行渲染
                render_function()
                self.frame_monitor.record_frame()
                frame_count += 1

                # 目标帧率控制
                target_frame_time = 1.0 / self.config.target_fps
                elapsed = time.time() - frame_start

                if elapsed < target_frame_time:
                    time.sleep(target_frame_time - elapsed)

            # 停止监控并收集结果
            frame_stats = self.frame_monitor.stop_monitoring()
            memory_stats = self.memory_monitor.stop_monitoring() if self.config.enable_memory_profiling else {}
            gpu_stats = self.gpu_monitor.stop_monitoring() if self.config.enable_gpu_monitoring else {}

            # 冷却阶段
            if self.config.cooldown_time > 0:
                logger.info(f"冷却阶段，等待 {self.config.cooldown_time} 秒...")
                time.sleep(self.config.cooldown_time)
                gc.collect()  # 强制垃圾回收

            # 创建性能指标
            metrics = PerformanceMetrics(
                render_time_ms=frame_stats.get('avg_frame_time', 0.0),
                frame_rate=frame_stats.get('avg_fps', 0.0),
                frames_rendered=frame_stats.get('total_frames', frame_count),
                memory_usage_mb=memory_stats.get('avg_memory', 0.0),
                gpu_memory_mb=memory_stats.get('avg_gpu_memory', 0.0),
                peak_memory_mb=memory_stats.get('peak_memory', 0.0),
                gpu_utilization_percent=gpu_stats.get('avg_gpu_utilization', 0.0),
                gpu_temperature=gpu_stats.get('avg_gpu_temperature', 0.0),
                min_frame_time=frame_stats.get('min_fps', 0.0),
                max_frame_time=frame_stats.get('max_fps', 0.0),
                avg_frame_time=frame_stats.get('avg_frame_time', 0.0),
                frame_time_std=frame_stats.get('frame_time_std', 0.0)
            )

            duration = time.time() - start_time

            result = BenchmarkResult(
                test_name=test_name,
                benchmark_type=BenchmarkType.RENDERING,
                rendering_engine=rendering_engine,
                config=self.config,
                metrics=metrics,
                raw_data={
                    'frame_stats': frame_stats,
                    'memory_stats': memory_stats,
                    'gpu_stats': gpu_stats
                },
                duration=duration,
                success=True
            )

            logger.info(f"渲染性能测试完成: {rendering_engine.value}")
            logger.info(f"平均帧率: {metrics.frame_rate:.1f} FPS")
            logger.info(f"平均内存使用: {metrics.memory_usage_mb:.1f} MB")

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"渲染性能测试失败: {e}")

            return BenchmarkResult(
                test_name=test_name,
                benchmark_type=BenchmarkType.RENDERING,
                rendering_engine=rendering_engine,
                config=self.config,
                metrics=PerformanceMetrics(),
                duration=duration,
                success=False,
                error_message=str(e)
            )

    def _warm_up(self, render_function: Callable[[], None]) -> None:
        """预热阶段"""
        warm_up_start = time.time()
        while time.time() - warm_up_start < self.config.warm_up_time:
            render_function()
            time.sleep(0.016)  # ~60 FPS

class ComparisonBenchmark:
    """对比基准测试"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.rendering_benchmark = RenderingBenchmark(config)

    def compare_rendering_engines(self,
                                  baseline_engine: RenderingEngine,
                                  test_engine: RenderingEngine,
                                  baseline_function: Callable[[], None],
                                  test_function: Callable[[], None]) -> ComparisonResult:
        """
        对比两个渲染引擎的性能

        Args:
            baseline_engine: 基准渲染引擎
            test_engine: 测试渲染引擎
            baseline_function: 基准渲染函数
            test_function: 测试渲染函数
        """
        logger.info(f"开始对比测试: {baseline_engine.value} vs {test_engine.value}")

        # 运行基准测试
        baseline_result = self.rendering_benchmark.run_rendering_test(
            baseline_engine, baseline_function
        )

        # 等待系统稳定
        time.sleep(2.0)

        # 运行对比测试
        test_result = self.rendering_benchmark.run_rendering_test(
            test_engine, test_function
        )

        # 计算性能改进
        performance_improvement = self._calculate_improvement(
            baseline_result.metrics.frame_rate,
            test_result.metrics.frame_rate
        )

        memory_improvement = self._calculate_improvement(
            baseline_result.metrics.memory_usage_mb,
            test_result.metrics.memory_usage_mb,
            lower_is_better=True
        )

        # 详细对比分析
        detailed_comparison = {
            'fps_improvement': performance_improvement,
            'memory_improvement': memory_improvement,
            'frame_time_improvement': self._calculate_improvement(
                baseline_result.metrics.avg_frame_time,
                test_result.metrics.avg_frame_time,
                lower_is_better=True
            ),
            'gpu_utilization_improvement': self._calculate_improvement(
                baseline_result.metrics.gpu_utilization_percent,
                test_result.metrics.gpu_utilization_percent
            )
        }

        comparison_result = ComparisonResult(
            baseline_result=baseline_result,
            test_result=test_result,
            performance_improvement=performance_improvement,
            memory_improvement=memory_improvement,
            detailed_comparison=detailed_comparison
        )

        logger.info(f"对比测试完成:")
        logger.info(f"性能改进: {performance_improvement:.1f}%")
        logger.info(f"内存改进: {memory_improvement:.1f}%")

        return comparison_result

    def _calculate_improvement(self, baseline: float, test: float,
                               lower_is_better: bool = False) -> float:
        """计算改进百分比"""
        if baseline == 0:
            return 0.0

        improvement = ((test - baseline) / baseline) * 100

        if lower_is_better:
            improvement = -improvement

        return improvement

class PerformanceBenchmarkSuite:
    """性能基准测试套件"""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.rendering_benchmark = RenderingBenchmark(self.config)
        self.comparison_benchmark = ComparisonBenchmark(self.config)
        self.results: List[BenchmarkResult] = []
        self.comparison_results: List[ComparisonResult] = []

    def run_full_benchmark_suite(self, render_functions: Dict[RenderingEngine, Callable[[], None]]) -> Dict[str, Any]:
        """
        运行完整的基准测试套件

        Args:
            render_functions: 渲染引擎到渲染函数的映射
        """
        logger.info("开始完整基准测试套件...")
        suite_start = time.time()

        # 清空之前的结果
        self.results.clear()
        self.comparison_results.clear()

        # 单独性能测试
        for engine, render_func in render_functions.items():
            try:
                result = self.rendering_benchmark.run_rendering_test(engine, render_func)
                self.results.append(result)
            except Exception as e:
                logger.error(f"测试引擎 {engine.value} 失败: {e}")

        # 对比测试（以第一个引擎为基准）
        if len(render_functions) >= 2:
            engines = list(render_functions.keys())
            baseline_engine = engines[0]
            baseline_function = render_functions[baseline_engine]

            for test_engine in engines[1:]:
                try:
                    comparison = self.comparison_benchmark.compare_rendering_engines(
                        baseline_engine, test_engine,
                        baseline_function, render_functions[test_engine]
                    )
                    self.comparison_results.append(comparison)
                except Exception as e:
                    logger.error(f"对比测试 {baseline_engine.value} vs {test_engine.value} 失败: {e}")

        suite_duration = time.time() - suite_start

        # 生成综合报告
        report = self._generate_comprehensive_report(suite_duration)

        logger.info(f"完整基准测试套件完成，耗时: {suite_duration:.2f}秒")
        return report

    def _generate_comprehensive_report(self, suite_duration: float) -> Dict[str, Any]:
        """生成综合性能报告"""
        report = {
            'timestamp': time.time(),
            'suite_duration': suite_duration,
            'config': {
                'test_duration': self.config.test_duration_seconds,
                'target_fps': self.config.target_fps,
                'chart_resolution': f"{self.config.chart_width}x{self.config.chart_height}"
            },
            'individual_results': [],
            'comparison_results': [],
            'performance_ranking': [],
            'recommendations': []
        }

        # 单独测试结果
        for result in self.results:
            report['individual_results'].append({
                'engine': result.rendering_engine.value,
                'success': result.success,
                'fps': result.metrics.frame_rate,
                'memory_mb': result.metrics.memory_usage_mb,
                'gpu_utilization': result.metrics.gpu_utilization_percent,
                'frame_time_ms': result.metrics.avg_frame_time
            })

        # 对比测试结果
        for comparison in self.comparison_results:
            report['comparison_results'].append({
                'baseline': comparison.baseline_result.rendering_engine.value,
                'test': comparison.test_result.rendering_engine.value,
                'performance_improvement': comparison.performance_improvement,
                'memory_improvement': comparison.memory_improvement,
                'detailed_comparison': comparison.detailed_comparison
            })

        # 性能排名
        successful_results = [r for r in self.results if r.success]
        if successful_results:
            ranked_results = sorted(successful_results,
                                    key=lambda x: x.metrics.frame_rate, reverse=True)

            for i, result in enumerate(ranked_results):
                report['performance_ranking'].append({
                    'rank': i + 1,
                    'engine': result.rendering_engine.value,
                    'score': self._calculate_performance_score(result.metrics),
                    'fps': result.metrics.frame_rate,
                    'memory_efficiency': self._calculate_memory_efficiency(result.metrics)
                })

        # 生成建议
        report['recommendations'] = self._generate_recommendations()

        return report

    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """计算综合性能得分"""
        # 基于多个指标的综合评分
        fps_score = min(100, (metrics.frame_rate / 60) * 50)  # 60FPS = 50分
        memory_score = max(0, 25 - (metrics.memory_usage_mb / 100) * 25)  # 内存使用越少得分越高
        stability_score = max(0, 25 - metrics.frame_time_std)  # 帧时间稳定性

        return fps_score + memory_score + stability_score

    def _calculate_memory_efficiency(self, metrics: PerformanceMetrics) -> float:
        """计算内存效率（FPS/MB）"""
        if metrics.memory_usage_mb > 0:
            return metrics.frame_rate / metrics.memory_usage_mb
        return 0.0

    def _generate_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        if not self.results:
            return ["无法生成建议：没有可用的测试结果"]

        # 分析最佳性能引擎
        successful_results = [r for r in self.results if r.success]
        if successful_results:
            best_result = max(successful_results, key=lambda x: x.metrics.frame_rate)
            recommendations.append(f"推荐使用 {best_result.rendering_engine.value} 引擎以获得最佳性能")

            # 内存使用分析
            high_memory_results = [r for r in successful_results if r.metrics.memory_usage_mb > 500]
            if high_memory_results:
                recommendations.append("检测到高内存使用，建议启用内存优化选项")

            # 帧率分析
            low_fps_results = [r for r in successful_results if r.metrics.frame_rate < 30]
            if low_fps_results:
                recommendations.append("检测到低帧率，建议降低图表复杂度或分辨率")

            # GPU利用率分析
            low_gpu_results = [r for r in successful_results if r.metrics.gpu_utilization_percent < 50]
            if low_gpu_results and len(low_gpu_results) < len(successful_results):
                recommendations.append("部分引擎GPU利用率较低，WebGPU可能提供更好的硬件加速")

        if not recommendations:
            recommendations.append("系统性能良好，所有测试引擎都能提供优质体验")

        return recommendations

    def save_report(self, report: Dict[str, Any], file_path: str) -> None:
        """保存性能测试报告"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"性能测试报告已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存性能报告失败: {e}")

# 快捷函数
def run_quick_performance_test(render_function: Callable[[], None],
                               engine: RenderingEngine = RenderingEngine.WEBGPU) -> BenchmarkResult:
    """快速性能测试"""
    config = BenchmarkConfig(test_duration_seconds=10, warm_up_time=2)
    benchmark = RenderingBenchmark(config)
    return benchmark.run_rendering_test(engine, render_function)

def compare_webgpu_vs_traditional(webgpu_function: Callable[[], None],
                                  traditional_function: Callable[[], None]) -> ComparisonResult:
    """WebGPU与传统渲染对比测试"""
    config = BenchmarkConfig(test_duration_seconds=15)
    comparison = ComparisonBenchmark(config)
    return comparison.compare_rendering_engines(
        RenderingEngine.MATPLOTLIB, RenderingEngine.WEBGPU,
        traditional_function, webgpu_function
    )

if __name__ == "__main__":
    # 性能测试示例
    def dummy_render():
        """模拟渲染函数"""
        time.sleep(0.001)  # 模拟1ms渲染时间

    logger.info("运行WebGPU性能基准测试...")

    # 快速测试
    result = run_quick_performance_test(dummy_render, RenderingEngine.WEBGPU)
    logger.info(f"\n性能测试结果:")
    logger.info(f"平均帧率: {result.metrics.frame_rate:.1f} FPS")
    logger.info(f"内存使用: {result.metrics.memory_usage_mb:.1f} MB")
    logger.info(f"测试时长: {result.duration:.2f}秒")
