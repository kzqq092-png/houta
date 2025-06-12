#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法性能评估器
提供全面的性能指标评估，包括准确性、性能、业务和稳定性指标
"""

from analysis.pattern_base import PatternAlgorithmFactory, PatternResult
from analysis.pattern_manager import PatternManager
import time
import psutil
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import tracemalloc
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    # 准确性指标
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0

    # 性能指标
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

    # 业务指标
    signal_quality: float = 0.0
    confidence_avg: float = 0.0
    confidence_std: float = 0.0
    patterns_found: int = 0

    # 稳定性指标
    robustness_score: float = 0.0
    parameter_sensitivity: float = 0.0

    # 综合评分
    overall_score: float = 0.0


class PerformanceEvaluator:
    """算法性能评估器"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.manager = PatternManager()

    def evaluate_algorithm(self, pattern_name: str, test_datasets: List[pd.DataFrame],
                           ground_truth: Optional[List[List[Dict]]] = None,
                           test_conditions: Dict[str, Any] = None) -> PerformanceMetrics:
        """
        评估算法性能

        Args:
            pattern_name: 形态名称
            test_datasets: 测试数据集列表
            ground_truth: 真实标签（如果有的话）
            test_conditions: 测试条件

        Returns:
            性能指标
        """
        print(f"🔍 开始评估算法: {pattern_name}")

        # 获取形态配置
        config = self.manager.get_pattern_by_name(pattern_name)
        if not config:
            raise ValueError(f"未找到形态配置: {pattern_name}")

        # 创建识别器
        recognizer = PatternAlgorithmFactory.create(config)

        metrics = PerformanceMetrics()
        all_results = []
        execution_times = []
        memory_usages = []
        cpu_usages = []

        # 对每个测试数据集进行评估
        for i, dataset in enumerate(test_datasets):
            print(f"  测试数据集 {i+1}/{len(test_datasets)}")

            # 性能监控
            start_time = time.time()
            tracemalloc.start()
            cpu_start = psutil.cpu_percent()

            try:
                # 执行识别
                results = recognizer.recognize(dataset)
                all_results.extend(results)

                # 记录性能指标
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)

                # 内存使用
                current, peak = tracemalloc.get_traced_memory()
                memory_usages.append(peak / 1024 / 1024)  # MB
                tracemalloc.stop()

                # CPU使用
                cpu_end = psutil.cpu_percent()
                cpu_usages.append(max(0, cpu_end - cpu_start))

                if self.debug_mode:
                    print(f"    ⏱️  执行时间: {execution_time:.3f}秒")
                    print(f"    💾 内存使用: {peak/1024/1024:.3f}MB")
                    print(f"    🔢 识别结果: {len(results)}个形态")

            except Exception as e:
                print(f"    ❌ 测试失败: {e}")
                if self.debug_mode:
                    traceback.print_exc()
                continue

        # 计算性能指标
        metrics.execution_time = np.mean(execution_times) if execution_times else 0
        metrics.memory_usage = np.mean(memory_usages) if memory_usages else 0
        metrics.cpu_usage = np.mean(cpu_usages) if cpu_usages else 0
        metrics.patterns_found = len(all_results)

        # 计算业务指标
        if all_results:
            confidences = [r.confidence for r in all_results]
            metrics.confidence_avg = np.mean(confidences)
            metrics.confidence_std = np.std(confidences)
            metrics.signal_quality = self._calculate_signal_quality(all_results)

        # 计算准确性指标（如果有真实标签）
        if ground_truth:
            accuracy_metrics = self._calculate_accuracy_metrics(all_results, ground_truth)
            metrics.true_positives = accuracy_metrics['tp']
            metrics.false_positives = accuracy_metrics['fp']
            metrics.true_negatives = accuracy_metrics['tn']
            metrics.false_negatives = accuracy_metrics['fn']
            metrics.precision = accuracy_metrics['precision']
            metrics.recall = accuracy_metrics['recall']
            metrics.f1_score = accuracy_metrics['f1_score']
            metrics.accuracy = accuracy_metrics['accuracy']

        # 计算稳定性指标
        metrics.robustness_score = self._calculate_robustness_score(
            pattern_name, test_datasets, recognizer
        )

        # 计算参数敏感性
        metrics.parameter_sensitivity = self._calculate_parameter_sensitivity(
            pattern_name, test_datasets[0] if test_datasets else None
        )

        # 计算综合评分
        metrics.overall_score = self._calculate_overall_score(metrics)

        print(f"✅ 评估完成，综合评分: {metrics.overall_score:.3f}")
        return metrics

    def _calculate_signal_quality(self, results: List[PatternResult]) -> float:
        """计算信号质量"""
        if not results:
            return 0.0

        # 基于置信度分布和信号一致性计算质量
        confidences = [r.confidence for r in results]

        # 高置信度结果的比例
        high_confidence_ratio = sum(1 for c in confidences if c > 0.7) / len(confidences)

        # 置信度的稳定性（标准差越小越好）
        confidence_stability = 1.0 - min(1.0, np.std(confidences))

        # 信号强度（平均置信度）
        signal_strength = np.mean(confidences)

        # 综合质量评分
        quality = (high_confidence_ratio * 0.4 +
                   confidence_stability * 0.3 +
                   signal_strength * 0.3)

        return quality

    def _calculate_accuracy_metrics(self, results: List[PatternResult],
                                    ground_truth: List[List[Dict]]) -> Dict[str, float]:
        """计算准确性指标"""
        # 这里需要实现与真实标签的比较逻辑
        # 由于没有标准的真实标签，这里提供一个框架

        tp = fp = tn = fn = 0

        # TODO: 实现具体的准确性计算逻辑
        # 这需要根据具体的标注数据格式来实现

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

        return {
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
            'precision': precision, 'recall': recall,
            'f1_score': f1_score, 'accuracy': accuracy
        }

    def _calculate_robustness_score(self, pattern_name: str,
                                    test_datasets: List[pd.DataFrame],
                                    recognizer) -> float:
        """计算鲁棒性评分"""
        if len(test_datasets) < 2:
            return 0.5  # 默认中等鲁棒性

        results_consistency = []

        # 在不同数据集上测试一致性
        for dataset in test_datasets:
            try:
                results = recognizer.recognize(dataset)
                # 计算结果的一致性指标
                if results:
                    avg_confidence = np.mean([r.confidence for r in results])
                    results_consistency.append(avg_confidence)
                else:
                    results_consistency.append(0.0)
            except:
                results_consistency.append(0.0)

        if not results_consistency:
            return 0.0

        # 一致性越高，鲁棒性越好
        consistency_score = 1.0 - np.std(results_consistency) / (np.mean(results_consistency) + 1e-6)
        return max(0.0, min(1.0, consistency_score))

    def _calculate_parameter_sensitivity(self, pattern_name: str,
                                         test_dataset: Optional[pd.DataFrame]) -> float:
        """计算参数敏感性"""
        if test_dataset is None:
            return 0.5

        try:
            config = self.manager.get_pattern_by_name(pattern_name)
            if not config or not config.parameters:
                return 0.5

            # 获取基准结果
            base_recognizer = PatternAlgorithmFactory.create(config)
            base_results = base_recognizer.recognize(test_dataset)
            base_score = np.mean([r.confidence for r in base_results]) if base_results else 0

            # 测试参数变化对结果的影响
            sensitivity_scores = []

            for param_name, param_value in config.parameters.items():
                if isinstance(param_value, (int, float)):
                    # 测试参数变化±20%
                    for factor in [0.8, 1.2]:
                        try:
                            modified_params = config.parameters.copy()
                            modified_params[param_name] = param_value * factor

                            # 创建修改参数的配置
                            modified_config = config
                            modified_config.parameters = modified_params

                            modified_recognizer = PatternAlgorithmFactory.create(modified_config)
                            modified_results = modified_recognizer.recognize(test_dataset)
                            modified_score = np.mean([r.confidence for r in modified_results]) if modified_results else 0

                            # 计算敏感性
                            if base_score > 0:
                                sensitivity = abs(modified_score - base_score) / base_score
                                sensitivity_scores.append(sensitivity)
                        except:
                            continue

            # 敏感性越低越好
            if sensitivity_scores:
                avg_sensitivity = np.mean(sensitivity_scores)
                return max(0.0, min(1.0, 1.0 - avg_sensitivity))
            else:
                return 0.5

        except Exception as e:
            if self.debug_mode:
                print(f"参数敏感性计算失败: {e}")
            return 0.5

    def _calculate_overall_score(self, metrics: PerformanceMetrics) -> float:
        """计算综合评分"""
        scores = []
        weights = []

        # 业务指标权重最高
        if metrics.signal_quality > 0:
            scores.append(metrics.signal_quality)
            weights.append(0.3)

        if metrics.confidence_avg > 0:
            scores.append(metrics.confidence_avg)
            weights.append(0.2)

        # 性能指标
        if metrics.execution_time > 0:
            # 执行时间越短越好，转换为评分
            time_score = max(0, min(1.0, 1.0 - metrics.execution_time / 10.0))
            scores.append(time_score)
            weights.append(0.15)

        # 稳定性指标
        if metrics.robustness_score > 0:
            scores.append(metrics.robustness_score)
            weights.append(0.15)

        if metrics.parameter_sensitivity > 0:
            scores.append(metrics.parameter_sensitivity)
            weights.append(0.1)

        # 准确性指标（如果有）
        if metrics.f1_score > 0:
            scores.append(metrics.f1_score)
            weights.append(0.1)

        if not scores:
            return 0.5  # 默认评分

        # 加权平均
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        return max(0.0, min(1.0, weighted_score))

    def create_test_datasets(self, pattern_name: str, count: int = 5) -> List[pd.DataFrame]:
        """创建测试数据集"""
        print(f"为 {pattern_name} 创建 {count} 个测试数据集")

        datasets = []

        for i in range(count):
            # 创建不同市场条件的测试数据
            dataset = self._generate_test_data(
                periods=200,
                volatility=0.02 + i * 0.01,  # 不同波动率
                trend=0.001 * (i - 2),       # 不同趋势
                pattern_injection=True
            )
            datasets.append(dataset)

        return datasets

    def _generate_test_data(self, periods: int = 200, volatility: float = 0.02,
                            trend: float = 0.0, pattern_injection: bool = True) -> pd.DataFrame:
        """生成测试数据"""
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
        data = []

        base_price = 100.0

        for i, date in enumerate(dates):
            # 趋势和随机波动
            price_change = trend + np.random.normal(0, volatility)
            base_price *= (1 + price_change)

            # 生成OHLC
            open_price = base_price
            close_price = base_price * (1 + np.random.normal(0, volatility * 0.5))
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility * 0.3)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility * 0.3)))

            data.append({
                'datetime': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': np.random.randint(800000, 1500000)
            })

        return pd.DataFrame(data)

    def benchmark_against_baseline(self, pattern_name: str,
                                   current_metrics: PerformanceMetrics,
                                   baseline_metrics: Optional[PerformanceMetrics] = None) -> Dict[str, float]:
        """与基准进行对比"""
        if baseline_metrics is None:
            # 使用默认基准
            baseline_metrics = PerformanceMetrics(
                signal_quality=0.5,
                confidence_avg=0.5,
                execution_time=1.0,
                robustness_score=0.5,
                overall_score=0.5
            )

        improvements = {}

        # 计算各项指标的改进百分比
        metrics_to_compare = [
            'signal_quality', 'confidence_avg', 'robustness_score',
            'parameter_sensitivity', 'overall_score'
        ]

        for metric in metrics_to_compare:
            current_value = getattr(current_metrics, metric)
            baseline_value = getattr(baseline_metrics, metric)

            if baseline_value > 0:
                improvement = (current_value - baseline_value) / baseline_value * 100
                improvements[metric] = improvement
            else:
                improvements[metric] = 0.0

        # 执行时间改进（越小越好）
        if baseline_metrics.execution_time > 0:
            time_improvement = (baseline_metrics.execution_time - current_metrics.execution_time) / baseline_metrics.execution_time * 100
            improvements['execution_time'] = time_improvement

        return improvements


def create_performance_evaluator(debug_mode: bool = False) -> PerformanceEvaluator:
    """创建性能评估器实例"""
    return PerformanceEvaluator(debug_mode=debug_mode)


if __name__ == "__main__":
    # 测试性能评估器
    evaluator = create_performance_evaluator(debug_mode=True)

    # 创建测试数据集
    test_datasets = evaluator.create_test_datasets("hammer", count=3)

    # 评估锤头线算法
    metrics = evaluator.evaluate_algorithm("hammer", test_datasets)

    print(f"\n性能评估结果:")
    print(f"  综合评分: {metrics.overall_score:.3f}")
    print(f"  信号质量: {metrics.signal_quality:.3f}")
    print(f"  平均置信度: {metrics.confidence_avg:.3f}")
    print(f"  执行时间: {metrics.execution_time:.3f}秒")
    print(f"  鲁棒性: {metrics.robustness_score:.3f}")
    print(f"  识别形态数: {metrics.patterns_found}")
