from loguru import logger
"""
深度分析服务

提供系统性能的深度分析功能，包括瓶颈分析、趋势预测、异常检测等
"""

import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
import threading

logger = logger


@dataclass
class PerformanceMetric:
    """性能指标数据"""
    timestamp: datetime
    metric_name: str
    value: float
    category: str = "system"


@dataclass
class BottleneckInfo:
    """性能瓶颈信息"""
    component: str
    avg_duration: float
    call_count: int
    percentage: float
    severity: str


@dataclass
class AnomalyInfo:
    """异常信息"""
    timestamp: datetime
    metric_name: str
    value: float
    threshold: float
    severity: str
    description: str


class DeepAnalysisService:
    """深度分析服务"""

    def __init__(self, max_history_size: int = 10000):
        self.max_history_size = max_history_size
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.operation_timings: Dict[str, List[float]] = defaultdict(list)
        self.anomaly_thresholds: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

        # 初始化默认阈值
        self._init_default_thresholds()

    def _init_default_thresholds(self):
        """初始化默认异常检测阈值"""
        self.anomaly_thresholds = {
            'cpu_usage': (0.0, 90.0),  # CPU使用率 0-90%
            'memory_usage': (0.0, 85.0),  # 内存使用率 0-85%
            'disk_usage': (0.0, 95.0),  # 磁盘使用率 0-95%
            'response_time': (0.0, 5.0),  # 响应时间 0-5秒
            'query_time': (0.0, 3.0),  # 查询时间 0-3秒
        }

    def record_metric(self, metric_name: str, value: float, category: str = "system"):
        """记录性能指标"""
        with self._lock:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=metric_name,
                value=value,
                category=category
            )
            self.metrics_history.append(metric)

    def record_operation_timing(self, operation_name: str, duration: float):
        """记录操作耗时"""
        with self._lock:
            self.operation_timings[operation_name].append(duration)
            # 保持最近1000次记录
            if len(self.operation_timings[operation_name]) > 1000:
                self.operation_timings[operation_name] = self.operation_timings[operation_name][-1000:]

    def analyze_bottlenecks(self) -> List[BottleneckInfo]:
        """分析性能瓶颈"""
        bottlenecks = []

        with self._lock:
            total_time = 0
            operation_stats = {}

            # 计算各操作的统计信息
            for op_name, timings in self.operation_timings.items():
                if timings:
                    avg_duration = statistics.mean(timings)
                    call_count = len(timings)
                    total_duration = sum(timings)

                    operation_stats[op_name] = {
                        'avg_duration': avg_duration,
                        'call_count': call_count,
                        'total_duration': total_duration
                    }
                    total_time += total_duration

            # 计算各操作占比并确定瓶颈
            for op_name, stats in operation_stats.items():
                percentage = (stats['total_duration'] / total_time * 100) if total_time > 0 else 0

                # 确定严重程度
                if percentage > 30:
                    severity = "严重"
                elif percentage > 15:
                    severity = "中等"
                elif percentage > 5:
                    severity = "轻微"
                else:
                    severity = "正常"

                bottleneck = BottleneckInfo(
                    component=op_name,
                    avg_duration=stats['avg_duration'],
                    call_count=stats['call_count'],
                    percentage=percentage,
                    severity=severity
                )
                bottlenecks.append(bottleneck)

        # 按占比排序
        bottlenecks.sort(key=lambda x: x.percentage, reverse=True)
        return bottlenecks

    def get_operation_ranking(self) -> List[Tuple[str, float, int]]:
        """获取操作耗时排行"""
        ranking = []

        with self._lock:
            for op_name, timings in self.operation_timings.items():
                if timings:
                    avg_duration = statistics.mean(timings) * 1000  # 转换为毫秒
                    call_count = len(timings)
                    ranking.append((op_name, avg_duration, call_count))

        # 按平均耗时排序
        ranking.sort(key=lambda x: x[1], reverse=True)
        return ranking

    def predict_trends(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """预测性能趋势"""
        trends = {}
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            # 按指标分组
            metric_groups = defaultdict(list)
            for metric in self.metrics_history:
                if metric.timestamp >= cutoff_time:
                    metric_groups[metric.metric_name].append(metric)

        # 对每个指标进行趋势分析
        for metric_name, metrics in metric_groups.items():
            if len(metrics) < 2:
                continue

            # 按时间排序
            metrics.sort(key=lambda x: x.timestamp)

            # 计算趋势
            values = [m.value for m in metrics]
            current_avg = statistics.mean(values[-10:]) if len(values) >= 10 else statistics.mean(values)

            # 简单线性趋势预测
            if len(values) >= 5:
                recent_values = values[-5:]
                older_values = values[-10:-5] if len(values) >= 10 else values[:-5]

                if older_values:
                    recent_avg = statistics.mean(recent_values)
                    older_avg = statistics.mean(older_values)
                    trend_rate = (recent_avg - older_avg) / older_avg if older_avg != 0 else 0

                    # 预测未来值
                    predicted_next_week = current_avg * (1 + trend_rate * 7)
                    predicted_next_month = current_avg * (1 + trend_rate * 30)

                    trends[metric_name] = {
                        'current': current_avg,
                        'next_week': predicted_next_week,
                        'next_month': predicted_next_month,
                        'trend_rate': trend_rate
                    }

        return trends

    def detect_anomalies(self, hours: int = 24) -> List[AnomalyInfo]:
        """检测异常"""
        anomalies = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            # 按指标分组
            metric_groups = defaultdict(list)
            for metric in self.metrics_history:
                if metric.timestamp >= cutoff_time:
                    metric_groups[metric.metric_name].append(metric)

        # 检测每个指标的异常
        for metric_name, metrics in metric_groups.items():
            if len(metrics) < 10:  # 数据太少，无法检测异常
                continue

            values = [m.value for m in metrics]
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0

            # 使用3σ原则检测异常
            threshold_upper = mean_val + 3 * std_val
            threshold_lower = mean_val - 3 * std_val

            # 检查预定义阈值
            if metric_name in self.anomaly_thresholds:
                min_threshold, max_threshold = self.anomaly_thresholds[metric_name]
                threshold_lower = max(threshold_lower, min_threshold)
                threshold_upper = min(threshold_upper, max_threshold)

            # 查找异常值
            for metric in metrics:
                if metric.value > threshold_upper or metric.value < threshold_lower:
                    severity = "严重" if abs(metric.value - mean_val) > 4 * std_val else "中等"

                    description = f"{metric_name}异常: 当前值{metric.value:.2f}"
                    if metric.value > threshold_upper:
                        description += f", 超出上限{threshold_upper:.2f}"
                    else:
                        description += f", 低于下限{threshold_lower:.2f}"

                    anomaly = AnomalyInfo(
                        timestamp=metric.timestamp,
                        metric_name=metric_name,
                        value=metric.value,
                        threshold=threshold_upper if metric.value > threshold_upper else threshold_lower,
                        severity=severity,
                        description=description
                    )
                    anomalies.append(anomaly)

        # 按时间排序
        anomalies.sort(key=lambda x: x.timestamp, reverse=True)
        return anomalies

    def generate_optimization_suggestions(self) -> Dict[str, Any]:
        """生成优化建议"""
        suggestions = {
            'high_priority': [],
            'medium_priority': [],
            'low_priority': [],
            'expected_improvement': {}
        }

        # 分析瓶颈并生成建议
        bottlenecks = self.analyze_bottlenecks()

        for bottleneck in bottlenecks[:5]:  # 只分析前5个瓶颈
            if bottleneck.percentage > 20:
                priority = 'high_priority'
                improvement = f"预计性能提升: {min(bottleneck.percentage * 0.6, 50):.0f}%"
            elif bottleneck.percentage > 10:
                priority = 'medium_priority'
                improvement = f"预计性能提升: {min(bottleneck.percentage * 0.4, 30):.0f}%"
            else:
                priority = 'low_priority'
                improvement = f"预计性能提升: {min(bottleneck.percentage * 0.2, 15):.0f}%"

            suggestion = {
                'component': bottleneck.component,
                'issue': f"占用{bottleneck.percentage:.1f}%的执行时间",
                'suggestion': self._get_optimization_suggestion(bottleneck.component),
                'improvement': improvement
            }

            suggestions[priority].append(suggestion)

        # 分析异常并生成建议
        anomalies = self.detect_anomalies()
        anomaly_counts = defaultdict(int)
        for anomaly in anomalies:
            anomaly_counts[anomaly.metric_name] += 1

        for metric_name, count in anomaly_counts.items():
            if count > 5:  # 频繁异常
                suggestion = {
                    'component': metric_name,
                    'issue': f"检测到{count}次异常",
                    'suggestion': self._get_anomaly_suggestion(metric_name),
                    'improvement': "预计稳定性提升: 显著"
                }
                suggestions['high_priority'].append(suggestion)

        return suggestions

    def _get_optimization_suggestion(self, component: str) -> str:
        """获取组件优化建议"""
        suggestions_map = {
            'database_query': "优化SQL查询，添加索引，实现查询缓存",
            'chart_rendering': "使用Canvas渲染，实现图表懒加载",
            'data_processing': "优化算法复杂度，使用并行处理",
            'ui_update': "减少DOM操作，使用虚拟滚动",
            'file_io': "使用异步IO，实现文件缓存",
            'network_request': "实现请求合并，添加重试机制",
            'memory_allocation': "优化数据结构，减少内存拷贝",
        }

        for key, suggestion in suggestions_map.items():
            if key in component.lower():
                return suggestion

        return "分析具体实现，优化算法和数据结构"

    def _get_anomaly_suggestion(self, metric_name: str) -> str:
        """获取异常处理建议"""
        suggestions_map = {
            'cpu_usage': "检查CPU密集型任务，优化算法复杂度",
            'memory_usage': "检查内存泄漏，优化缓存策略",
            'disk_usage': "清理临时文件，实现数据归档",
            'response_time': "优化数据库查询，减少网络延迟",
            'error_rate': "增强错误处理，提高系统容错性",
        }

        for key, suggestion in suggestions_map.items():
            if key in metric_name.lower():
                return suggestion

        return "监控相关指标，分析根本原因"

    def get_performance_comparison(self, days: int = 7) -> Dict[str, List[float]]:
        """获取性能对比数据"""
        comparison_data = defaultdict(list)

        # 计算时间段
        now = datetime.now()
        periods = []
        for i in range(days):
            start_time = now - timedelta(days=i+1)
            end_time = now - timedelta(days=i)
            periods.append((start_time, end_time))

        with self._lock:
            # 为每个时间段计算平均值
            for start_time, end_time in periods:
                period_metrics = defaultdict(list)

                for metric in self.metrics_history:
                    if start_time <= metric.timestamp < end_time:
                        period_metrics[metric.metric_name].append(metric.value)

                # 计算各指标的平均值
                for metric_name, values in period_metrics.items():
                    if values:
                        avg_value = statistics.mean(values)
                        comparison_data[metric_name].append(avg_value)
                    else:
                        comparison_data[metric_name].append(0)

        return dict(comparison_data)


# 全局服务实例
_deep_analysis_service = None


def get_deep_analysis_service() -> DeepAnalysisService:
    """获取深度分析服务实例"""
    global _deep_analysis_service
    if _deep_analysis_service is None:
        _deep_analysis_service = DeepAnalysisService()
    return _deep_analysis_service
