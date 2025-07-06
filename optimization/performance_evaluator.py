#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能评估器
用于评估算法性能和生成性能指标
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import time
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    overall_score: float = 0.0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    execution_time: float = 0.0
    memory_usage: float = 0.0
    stability: float = 0.0
    robustness: float = 0.0
    efficiency: float = 0.0

    # 详细指标
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    # 时间指标
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0

    # 错误统计
    error_count: int = 0
    error_rate: float = 0.0

    # 额外信息
    evaluation_time: datetime = None
    sample_count: int = 0
    notes: str = ""

    def __post_init__(self):
        if self.evaluation_time is None:
            self.evaluation_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def calculate_derived_metrics(self):
        """计算派生指标"""
        # 计算精确度和召回率
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)

        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)

        # 计算F1分数
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)

        # 计算准确率
        total_samples = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        if total_samples > 0:
            self.accuracy = (self.true_positives + self.true_negatives) / total_samples

        # 计算错误率
        if self.sample_count > 0:
            self.error_rate = self.error_count / self.sample_count

        # 计算综合得分
        self.overall_score = (
            self.accuracy * 0.3 +
            self.f1_score * 0.3 +
            self.efficiency * 0.2 +
            self.stability * 0.1 +
            self.robustness * 0.1
        )


class PerformanceEvaluator:
    """性能评估器"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.evaluation_history = []

        # 评估配置
        self.config = {
            'timeout_seconds': 30,
            'memory_limit_mb': 1024,
            'min_samples': 100,
            'max_samples': 10000,
            'stability_runs': 5,
            'robustness_noise_levels': [0.1, 0.2, 0.3]
        }

    def evaluate_algorithm(self, pattern_name: str,
                           test_datasets: List[pd.DataFrame],
                           algorithm_config: Dict[str, Any] = None) -> PerformanceMetrics:
        """
        评估算法性能

        Args:
            pattern_name: 形态名称
            test_datasets: 测试数据集
            algorithm_config: 算法配置

        Returns:
            性能指标
        """
        if self.debug_mode:
            logger.info(f"开始评估算法: {pattern_name}")

        metrics = PerformanceMetrics()
        metrics.sample_count = sum(len(df) for df in test_datasets)

        start_time = time.time()

        try:
            # 1. 基础性能评估
            basic_metrics = self._evaluate_basic_performance(pattern_name, test_datasets)

            # 2. 稳定性评估
            stability_score = self._evaluate_stability(pattern_name, test_datasets)

            # 3. 鲁棒性评估
            robustness_score = self._evaluate_robustness(pattern_name, test_datasets)

            # 4. 效率评估
            efficiency_score = self._evaluate_efficiency(pattern_name, test_datasets)

            # 合并指标
            metrics.accuracy = basic_metrics.get('accuracy', 0.0)
            metrics.precision = basic_metrics.get('precision', 0.0)
            metrics.recall = basic_metrics.get('recall', 0.0)
            metrics.f1_score = basic_metrics.get('f1_score', 0.0)
            metrics.stability = stability_score
            metrics.robustness = robustness_score
            metrics.efficiency = efficiency_score

            # 设置统计数据
            metrics.true_positives = basic_metrics.get('true_positives', 0)
            metrics.false_positives = basic_metrics.get('false_positives', 0)
            metrics.true_negatives = basic_metrics.get('true_negatives', 0)
            metrics.false_negatives = basic_metrics.get('false_negatives', 0)

            # 计算派生指标
            metrics.calculate_derived_metrics()

            metrics.execution_time = time.time() - start_time

            if self.debug_mode:
                logger.info(f"评估完成，总分: {metrics.overall_score:.3f}")

            # 记录评估历史
            self.evaluation_history.append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"算法评估失败: {e}")
            metrics.error_count += 1
            metrics.notes = f"评估失败: {str(e)}"
            metrics.execution_time = time.time() - start_time
            return metrics

    def _evaluate_basic_performance(self, pattern_name: str,
                                    test_datasets: List[pd.DataFrame]) -> Dict[str, Any]:
        """评估基础性能"""
        # 模拟算法执行和结果统计
        total_samples = sum(len(df) for df in test_datasets)

        # 模拟性能指标（实际应用中应该调用真实的算法）
        accuracy = np.random.uniform(0.7, 0.95)  # 模拟准确率
        precision = np.random.uniform(0.6, 0.9)  # 模拟精确率
        recall = np.random.uniform(0.6, 0.9)     # 模拟召回率

        # 模拟混淆矩阵
        tp = int(total_samples * accuracy * 0.5)
        fp = int(total_samples * (1 - precision) * 0.3)
        tn = int(total_samples * accuracy * 0.5)
        fn = int(total_samples * (1 - recall) * 0.3)

        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'true_positives': tp,
            'false_positives': fp,
            'true_negatives': tn,
            'false_negatives': fn
        }

    def _evaluate_stability(self, pattern_name: str,
                            test_datasets: List[pd.DataFrame]) -> float:
        """评估稳定性"""
        # 多次运行算法，计算结果的稳定性
        scores = []

        for i in range(self.config['stability_runs']):
            # 模拟多次运行的结果
            score = np.random.uniform(0.7, 0.95)
            scores.append(score)

        # 计算稳定性（标准差越小越稳定）
        if len(scores) > 1:
            std_dev = np.std(scores)
            stability = max(0, 1 - std_dev * 5)  # 转换为0-1分数
        else:
            stability = 0.8  # 默认稳定性

        return stability

    def _evaluate_robustness(self, pattern_name: str,
                             test_datasets: List[pd.DataFrame]) -> float:
        """评估鲁棒性"""
        # 在不同噪声水平下测试算法
        robustness_scores = []

        for noise_level in self.config['robustness_noise_levels']:
            # 模拟在噪声环境下的性能
            base_score = 0.85
            noise_impact = noise_level * 0.5  # 噪声影响
            noisy_score = max(0, base_score - noise_impact)
            robustness_scores.append(noisy_score)

        # 计算平均鲁棒性
        return np.mean(robustness_scores)

    def _evaluate_efficiency(self, pattern_name: str,
                             test_datasets: List[pd.DataFrame]) -> float:
        """评估效率"""
        total_samples = sum(len(df) for df in test_datasets)

        # 模拟执行时间（基于数据量）
        base_time = 0.1  # 基础时间
        scale_factor = total_samples / 1000  # 规模因子
        execution_time = base_time * (1 + scale_factor * 0.1)

        # 模拟内存使用
        memory_usage = total_samples * 0.001  # MB

        # 计算效率分数（时间和内存的倒数）
        time_efficiency = 1 / (1 + execution_time)
        memory_efficiency = 1 / (1 + memory_usage / 100)

        efficiency = (time_efficiency + memory_efficiency) / 2
        return min(1.0, efficiency)

    def create_test_datasets(self, pattern_name: str, count: int = 5) -> List[pd.DataFrame]:
        """
        创建测试数据集

        Args:
            pattern_name: 形态名称
            count: 数据集数量

        Returns:
            测试数据集列表
        """
        datasets = []

        for i in range(count):
            # 生成模拟的股票数据
            size = np.random.randint(100, 1000)

            # 生成基础数据
            dates = pd.date_range(start='2020-01-01', periods=size, freq='D')

            # 生成价格数据（随机游走）
            initial_price = 100
            returns = np.random.normal(0, 0.02, size)
            prices = [initial_price]

            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            # 创建OHLC数据
            df = pd.DataFrame({
                'date': dates,
                'open': prices,
                'high': [p * (1 + np.random.uniform(0, 0.05)) for p in prices],
                'low': [p * (1 - np.random.uniform(0, 0.05)) for p in prices],
                'close': [p * (1 + np.random.uniform(-0.02, 0.02)) for p in prices],
                'volume': np.random.randint(1000, 100000, size)
            })

            # 添加技术指标
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['rsi'] = np.random.uniform(20, 80, size)  # 模拟RSI

            # 添加形态标记（模拟）
            df['pattern_signal'] = np.random.choice([0, 1], size=size, p=[0.8, 0.2])

            datasets.append(df)

        if self.debug_mode:
            logger.info(f"创建了 {count} 个测试数据集，总样本数: {sum(len(df) for df in datasets)}")

        return datasets

    def compare_algorithms(self, results: List[PerformanceMetrics]) -> Dict[str, Any]:
        """
        比较多个算法的性能

        Args:
            results: 性能指标列表

        Returns:
            比较结果
        """
        if not results:
            return {}

        comparison = {
            'best_overall': max(results, key=lambda x: x.overall_score),
            'best_accuracy': max(results, key=lambda x: x.accuracy),
            'best_efficiency': max(results, key=lambda x: x.efficiency),
            'best_stability': max(results, key=lambda x: x.stability),
            'best_robustness': max(results, key=lambda x: x.robustness),
            'average_scores': {
                'overall_score': np.mean([r.overall_score for r in results]),
                'accuracy': np.mean([r.accuracy for r in results]),
                'efficiency': np.mean([r.efficiency for r in results]),
                'stability': np.mean([r.stability for r in results]),
                'robustness': np.mean([r.robustness for r in results])
            },
            'score_distribution': {
                'overall_score': [r.overall_score for r in results],
                'accuracy': [r.accuracy for r in results],
                'efficiency': [r.efficiency for r in results],
                'stability': [r.stability for r in results],
                'robustness': [r.robustness for r in results]
            }
        }

        return comparison

    def generate_report(self, metrics: PerformanceMetrics,
                        pattern_name: str = "") -> str:
        """
        生成性能报告

        Args:
            metrics: 性能指标
            pattern_name: 形态名称

        Returns:
            报告文本
        """
        report = f"""
性能评估报告 - {pattern_name}
{'='*50}

评估时间: {metrics.evaluation_time}
样本数量: {metrics.sample_count}
执行时间: {metrics.execution_time:.3f}秒

核心指标:
  综合得分: {metrics.overall_score:.3f}
  准确率:   {metrics.accuracy:.3f}
  精确率:   {metrics.precision:.3f}
  召回率:   {metrics.recall:.3f}
  F1分数:   {metrics.f1_score:.3f}

性能指标:
  稳定性:   {metrics.stability:.3f}
  鲁棒性:   {metrics.robustness:.3f}
  效率:     {metrics.efficiency:.3f}

统计数据:
  真正例:   {metrics.true_positives}
  假正例:   {metrics.false_positives}
  真负例:   {metrics.true_negatives}
  假负例:   {metrics.false_negatives}

时间指标:
  平均响应时间: {metrics.avg_response_time:.3f}秒
  最大响应时间: {metrics.max_response_time:.3f}秒
  最小响应时间: {metrics.min_response_time:.3f}秒

错误统计:
  错误数量: {metrics.error_count}
  错误率:   {metrics.error_rate:.3f}

备注: {metrics.notes}
"""
        return report

    def save_evaluation_history(self, filename: str = None):
        """保存评估历史"""
        if filename is None:
            filename = f"evaluation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        history_data = []
        for metrics in self.evaluation_history:
            history_data.append(metrics.to_dict())

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False, default=str)

            if self.debug_mode:
                logger.info(f"评估历史已保存到: {filename}")

        except Exception as e:
            logger.error(f"保存评估历史失败: {e}")

    def load_evaluation_history(self, filename: str):
        """加载评估历史"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            self.evaluation_history = []
            for data in history_data:
                metrics = PerformanceMetrics(**data)
                self.evaluation_history.append(metrics)

            if self.debug_mode:
                logger.info(f"评估历史已加载: {len(self.evaluation_history)} 条记录")

        except Exception as e:
            logger.error(f"加载评估历史失败: {e}")


def create_performance_evaluator(debug_mode: bool = False) -> PerformanceEvaluator:
    """创建性能评估器实例"""
    return PerformanceEvaluator(debug_mode)


# 示例用法
if __name__ == "__main__":
    # 创建评估器
    evaluator = PerformanceEvaluator(debug_mode=True)

    # 创建测试数据
    test_datasets = evaluator.create_test_datasets("test_pattern", count=3)

    # 评估算法
    metrics = evaluator.evaluate_algorithm("test_pattern", test_datasets)

    # 生成报告
    report = evaluator.generate_report(metrics, "test_pattern")
    print(report)

    # 保存历史
    evaluator.save_evaluation_history()
