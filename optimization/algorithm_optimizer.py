from loguru import logger
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能算法优化器
使用遗传算法、贝叶斯优化等方法自动优化形态识别算法
"""

from analysis.pattern_manager import PatternManager
from optimization.version_manager import VersionManager
import random
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Callable
from datetime import datetime
import json
import re
from dataclasses import dataclass

# 导入性能指标类
from core.strategy_extensions import PerformanceMetrics

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceEvaluator:
    """性能评估器"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode

    def create_test_datasets(self, *args, **kwargs):
        """创建测试数据集"""
        # 简单的测试数据集创建逻辑
        return []

    def evaluate_algorithm(self, *args, **kwargs) -> PerformanceMetrics:
        """评估算法性能"""
        # 返回一个默认的性能指标
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=0.0,
            memory_mb=0.0,
            memory_percent=0.0,
            disk_io_read=0,
            disk_io_write=0,
            network_sent=0,
            network_recv=0,
            thread_count=1,
            open_files=0
        )


@dataclass
class OptimizationConfig:
    """优化配置"""
    method: str = "genetic"  # genetic, bayesian, random, gradient
    max_iterations: int = 50
    population_size: int = 20
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    target_metric: str = "overall_score"
    min_improvement: float = 0.05
    timeout_minutes: int = 30
    parallel_workers: int = 4


class AlgorithmOptimizer:
    """智能算法优化器"""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.evaluator = PerformanceEvaluator(debug_mode)
        self.version_manager = VersionManager()
        self.pattern_manager = PatternManager()

        # 优化历史
        self.optimization_history = []

    def optimize_algorithm(self, pattern_name: str,
                           config: OptimizationConfig = None,
                           test_datasets: List[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        优化指定形态的算法

        Args:
            pattern_name: 形态名称
            config: 优化配置
            test_datasets: 测试数据集

        Returns:
            优化结果
        """
        if config is None:
            config = OptimizationConfig()

        logger.info(f" 开始优化算法: {pattern_name}")
        logger.info(f" 优化方法: {config.method}")
        logger.info(f"目标指标: {config.target_metric}")

        # 获取当前算法配置
        pattern_config = self.pattern_manager.get_pattern_by_name(pattern_name)
        if not pattern_config:
            raise ValueError(f"未找到形态配置: {pattern_name}")

        # 创建测试数据集（如果没有提供）
        if test_datasets is None:
            test_datasets = self.evaluator.create_test_datasets(
                pattern_name, count=5)

        # 评估基准性能
        baseline_metrics = self.evaluator.evaluate_algorithm(
            pattern_name, test_datasets
        )

        logger.info(f"基准性能: {baseline_metrics.overall_score:.3f}")

        # 开始优化日志
        session_id = self.version_manager.db_manager.start_optimization_log(
            pattern_name=pattern_name,
            optimization_method=config.method,
            initial_version_id=0,  # 需要获取当前版本ID
            config=config.__dict__
        )

        try:
            # 根据优化方法选择优化策略
            if config.method == "genetic":
                result = self._genetic_optimization(
                    pattern_name, pattern_config, config, test_datasets, baseline_metrics
                )
            elif config.method == "bayesian":
                result = self._bayesian_optimization(
                    pattern_name, pattern_config, config, test_datasets, baseline_metrics
                )
            elif config.method == "random":
                result = self._random_optimization(
                    pattern_name, pattern_config, config, test_datasets, baseline_metrics
                )
            elif config.method == "gradient":
                result = self._gradient_optimization(
                    pattern_name, pattern_config, config, test_datasets, baseline_metrics
                )
            else:
                raise ValueError(f"不支持的优化方法: {config.method}")

            # 更新优化日志
            self.version_manager.db_manager.update_optimization_log(
                session_id=session_id,
                status="completed",
                final_version_id=result.get('best_version_id'),
                iterations=result.get('iterations', 0),
                best_score=result.get('best_score', 0),
                improvement_percentage=result.get('improvement_percentage', 0),
                optimization_log=json.dumps(result.get('optimization_log', []))
            )

            logger.info("优化完成！")
            logger.info(f"性能提升: {result.get('improvement_percentage', 0):.3f}%")

            return result

        except Exception as e:
            # 更新优化日志为失败状态
            self.version_manager.db_manager.update_optimization_log(
                session_id=session_id,
                status="failed",
                error_message=str(e)
            )
            raise e

    def _genetic_optimization(self, pattern_name: str, pattern_config,
                              config: OptimizationConfig, test_datasets: List[pd.DataFrame],
                              baseline_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """遗传算法优化"""
        logger.info("使用遗传算法优化...")

        # 初始化种群
        population = self._initialize_population(
            pattern_config, config.population_size)

        best_individual = None
        best_score = baseline_metrics.overall_score
        optimization_log = []

        for generation in range(config.max_iterations):
            logger.info(f"  第 {generation + 1}/{config.max_iterations} 代")

            # 评估种群
            fitness_scores = []
            for individual in population:
                try:
                    # 创建临时算法配置
                    temp_config = self._create_temp_config(
                        pattern_config, individual)

                    # 评估性能
                    metrics = self._evaluate_individual(
                        temp_config, test_datasets)
                    score = getattr(metrics, config.target_metric, 0)
                    fitness_scores.append(score)

                    # 更新最佳个体
                    if score > best_score:
                        best_score = score
                        best_individual = individual.copy()

                        logger.info(f"   发现更好的解: {score:.3f}")

                except Exception as e:
                    if self.debug_mode:
                        logger.info(f"     个体评估失败: {e}")
                    fitness_scores.append(0.0)

            # 记录当代最佳
            generation_best = max(fitness_scores) if fitness_scores else 0
            optimization_log.append({
                "generation": generation + 1,
                "best_score": generation_best,
                "avg_score": np.mean(fitness_scores) if fitness_scores else 0,
                "population_diversity": self._calculate_diversity(population)
            })

            # 检查收敛条件
            if generation_best - baseline_metrics.overall_score < config.min_improvement:
                if generation > 10:  # 至少运行10代
                    logger.info(f"     收敛，提前停止")
                    break

            # 选择、交叉、变异
            population = self._evolve_population(
                population, fitness_scores, config
            )

        # 保存最佳版本
        best_version_id = None
        if best_individual:
            best_version_id = self._save_optimized_version(
                pattern_name, pattern_config, best_individual,
                f"遗传算法优化 - 第{len(optimization_log)}代", best_score
            )

        improvement_percentage = (
            best_score - baseline_metrics.overall_score) / baseline_metrics.overall_score * 100

        return {
            "method": "genetic",
            "best_score": best_score,
            "baseline_score": baseline_metrics.overall_score,
            "improvement_percentage": improvement_percentage,
            "iterations": len(optimization_log),
            "best_version_id": best_version_id,
            "optimization_log": optimization_log
        }

    def _bayesian_optimization(self, pattern_name: str, pattern_config,
                               config: OptimizationConfig, test_datasets: List[pd.DataFrame],
                               baseline_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """贝叶斯优化"""
        logger.info("使用贝叶斯优化...")

        # 简化的贝叶斯优化实现
        # 在实际应用中，可以使用scikit-optimize等库

        best_individual = None
        best_score = baseline_metrics.overall_score
        optimization_log = []

        # 参数空间定义
        param_space = self._define_parameter_space(pattern_config)

        for iteration in range(config.max_iterations):
            logger.info(f"  第 {iteration + 1}/{config.max_iterations} 次迭代")

            # 选择下一个参数组合（简化版本）
            if iteration < 5:
                # 前几次随机采样
                individual = self._random_sample_parameters(param_space)
            else:
                # 基于历史结果选择有希望的区域
                individual = self._bayesian_sample_parameters(
                    param_space, optimization_log)

            try:
                # 评估参数组合
                temp_config = self._create_temp_config(
                    pattern_config, individual)
                metrics = self._evaluate_individual(temp_config, test_datasets)
                score = getattr(metrics, config.target_metric, 0)

                # 记录结果
                optimization_log.append({
                    "iteration": iteration + 1,
                    "parameters": individual,
                    "score": score
                })

                # 更新最佳结果
                if score > best_score:
                    best_score = score
                    best_individual = individual.copy()
                    logger.info(f"   发现更好的解: {score:.3f}")

            except Exception as e:
                if self.debug_mode:
                    logger.info(f"     参数评估失败: {e}")
                optimization_log.append({
                    "iteration": iteration + 1,
                    "parameters": individual,
                    "score": 0.0,
                    "error": str(e)
                })

        # 保存最佳版本
        best_version_id = None
        if best_individual:
            best_version_id = self._save_optimized_version(
                pattern_name, pattern_config, best_individual,
                f"贝叶斯优化 - {len(optimization_log)}次迭代", best_score
            )

        improvement_percentage = (
            best_score - baseline_metrics.overall_score) / baseline_metrics.overall_score * 100

        return {
            "method": "bayesian",
            "best_score": best_score,
            "baseline_score": baseline_metrics.overall_score,
            "improvement_percentage": improvement_percentage,
            "iterations": len(optimization_log),
            "best_version_id": best_version_id,
            "optimization_log": optimization_log
        }

    def _random_optimization(self, pattern_name: str, pattern_config,
                             config: OptimizationConfig, test_datasets: List[pd.DataFrame],
                             baseline_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """随机搜索优化"""
        logger.info("使用随机搜索优化...")

        best_individual = None
        best_score = baseline_metrics.overall_score
        optimization_log = []

        param_space = self._define_parameter_space(pattern_config)

        for iteration in range(config.max_iterations):
            logger.info(f"  第 {iteration + 1}/{config.max_iterations} 次尝试")

            # 随机采样参数
            individual = self._random_sample_parameters(param_space)

            try:
                temp_config = self._create_temp_config(
                    pattern_config, individual)
                metrics = self._evaluate_individual(temp_config, test_datasets)
                score = getattr(metrics, config.target_metric, 0)

                optimization_log.append({
                    "iteration": iteration + 1,
                    "parameters": individual,
                    "score": score
                })

                if score > best_score:
                    best_score = score
                    best_individual = individual.copy()
                    logger.info(f"   发现更好的解: {score:.3f}")

            except Exception as e:
                if self.debug_mode:
                    logger.info(f"     参数评估失败: {e}")

        # 保存最佳版本
        best_version_id = None
        if best_individual:
            best_version_id = self._save_optimized_version(
                pattern_name, pattern_config, best_individual,
                f"随机搜索优化 - {len(optimization_log)}次尝试", best_score
            )

        improvement_percentage = (
            best_score - baseline_metrics.overall_score) / baseline_metrics.overall_score * 100

        return {
            "method": "random",
            "best_score": best_score,
            "baseline_score": baseline_metrics.overall_score,
            "improvement_percentage": improvement_percentage,
            "iterations": len(optimization_log),
            "best_version_id": best_version_id,
            "optimization_log": optimization_log
        }

    def _gradient_optimization(self, pattern_name: str, pattern_config,
                               config: OptimizationConfig, test_datasets: List[pd.DataFrame],
                               baseline_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """梯度优化（数值梯度）"""
        logger.info("↑ 使用梯度优化...")

        # 这是一个简化的数值梯度实现
        # 实际应用中可能需要更复杂的梯度计算

        current_params = self._extract_numeric_parameters(pattern_config)
        best_score = baseline_metrics.overall_score
        optimization_log = []

        learning_rate = 0.01

        for iteration in range(config.max_iterations):
            logger.info(f"  第 {iteration + 1}/{config.max_iterations} 次迭代")

            # 计算数值梯度
            gradients = {}
            for param_name, param_value in current_params.items():
                if isinstance(param_value, (int, float)):
                    # 计算偏导数
                    epsilon = abs(param_value) * 0.01 + 1e-6

                    # 正向扰动
                    params_plus = current_params.copy()
                    params_plus[param_name] = param_value + epsilon
                    score_plus = self._evaluate_params(
                        pattern_config, params_plus, test_datasets, config.target_metric)

                    # 负向扰动
                    params_minus = current_params.copy()
                    params_minus[param_name] = param_value - epsilon
                    score_minus = self._evaluate_params(
                        pattern_config, params_minus, test_datasets, config.target_metric)

                    # 计算梯度
                    gradient = (score_plus - score_minus) / (2 * epsilon)
                    gradients[param_name] = gradient

            # 更新参数
            for param_name, gradient in gradients.items():
                current_params[param_name] += learning_rate * gradient

                # 参数约束
                current_params[param_name] = max(
                    0.01, min(10.0, current_params[param_name]))

            # 评估当前参数
            current_score = self._evaluate_params(
                pattern_config, current_params, test_datasets, config.target_metric)

            optimization_log.append({
                "iteration": iteration + 1,
                "parameters": current_params.copy(),
                "score": current_score,
                "gradients": gradients.copy()
            })

            if current_score > best_score:
                best_score = current_score
                logger.info(f"   发现更好的解: {current_score:.3f}")

        # 保存最佳版本
        best_version_id = self._save_optimized_version(
            pattern_name, pattern_config, current_params,
            f"梯度优化 - {len(optimization_log)}次迭代", best_score
        )

        improvement_percentage = (
            best_score - baseline_metrics.overall_score) / baseline_metrics.overall_score * 100

        return {
            "method": "gradient",
            "best_score": best_score,
            "baseline_score": baseline_metrics.overall_score,
            "improvement_percentage": improvement_percentage,
            "iterations": len(optimization_log),
            "best_version_id": best_version_id,
            "optimization_log": optimization_log
        }

    def _initialize_population(self, pattern_config, population_size: int) -> List[Dict[str, Any]]:
        """初始化遗传算法种群"""
        population = []
        param_space = self._define_parameter_space(pattern_config)

        for _ in range(population_size):
            individual = self._random_sample_parameters(param_space)
            population.append(individual)

        return population

    def _define_parameter_space(self, pattern_config) -> Dict[str, Dict[str, Any]]:
        """定义参数搜索空间"""
        param_space = {}

        # 从算法代码中提取可优化的参数
        if pattern_config.parameters:
            for param_name, param_value in pattern_config.parameters.items():
                if isinstance(param_value, (int, float)):
                    param_space[param_name] = {
                        "type": "numeric",
                        "min": param_value * 0.5,
                        "max": param_value * 2.0,
                        "current": param_value
                    }
                elif isinstance(param_value, bool):
                    param_space[param_name] = {
                        "type": "boolean",
                        "current": param_value
                    }

        # 添加通用的形态识别参数
        param_space.update({
            "confidence_threshold": {
                "type": "numeric",
                "min": 0.1,
                "max": 0.9,
                "current": pattern_config.confidence_threshold
            },
            "min_body_ratio": {
                "type": "numeric",
                "min": 0.1,
                "max": 0.8,
                "current": 0.3
            },
            "shadow_ratio_threshold": {
                "type": "numeric",
                "min": 1.5,
                "max": 4.0,
                "current": 2.0
            }
        })

        return param_space

    def _random_sample_parameters(self, param_space: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """随机采样参数"""
        individual = {}

        for param_name, param_info in param_space.items():
            if param_info["type"] == "numeric":
                value = random.uniform(param_info["min"], param_info["max"])
                individual[param_name] = value
            elif param_info["type"] == "boolean":
                individual[param_name] = random.choice([True, False])

        return individual

    def _bayesian_sample_parameters(self, param_space: Dict[str, Dict[str, Any]],
                                    history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基于贝叶斯优化采样参数（简化版本）"""
        # 这是一个简化的实现，实际应用中应该使用专业的贝叶斯优化库

        if len(history) < 3:
            return self._random_sample_parameters(param_space)

        # 找到历史最佳参数
        best_entry = max(history, key=lambda x: x.get("score", 0))
        best_params = best_entry.get("parameters", {})

        # 在最佳参数附近采样
        individual = {}
        for param_name, param_info in param_space.items():
            if param_info["type"] == "numeric":
                if param_name in best_params:
                    # 在最佳值附近添加噪声
                    best_value = best_params[param_name]
                    noise_scale = (param_info["max"] - param_info["min"]) * 0.1
                    value = best_value + random.gauss(0, noise_scale)
                    value = max(param_info["min"], min(
                        param_info["max"], value))
                else:
                    value = random.uniform(
                        param_info["min"], param_info["max"])
                individual[param_name] = value
            elif param_info["type"] == "boolean":
                if param_name in best_params:
                    # 80%概率保持最佳值
                    if random.random() < 0.8:
                        individual[param_name] = best_params[param_name]
                    else:
                        individual[param_name] = not best_params[param_name]
                else:
                    individual[param_name] = random.choice([True, False])

        return individual

    def _create_temp_config(self, base_config, parameters: Dict[str, Any]):
        """创建临时配置"""
        temp_config = base_config
        temp_config.parameters = parameters
        return temp_config

    def _evaluate_individual(self, config, test_datasets: List[pd.DataFrame]) -> PerformanceMetrics:
        """评估个体性能"""
        # 这里需要实现临时算法的创建和评估
        # 简化版本：直接使用现有的评估器
        return self.evaluator.evaluate_algorithm(
            config.english_name, test_datasets
        )

    def _evaluate_params(self, pattern_config, parameters: Dict[str, Any],
                         test_datasets: List[pd.DataFrame], target_metric: str) -> float:
        """评估参数组合"""
        try:
            temp_config = self._create_temp_config(pattern_config, parameters)
            metrics = self._evaluate_individual(temp_config, test_datasets)
            return getattr(metrics, target_metric, 0)
        except:
            return 0.0

    def _evolve_population(self, population: List[Dict[str, Any]],
                           fitness_scores: List[float],
                           config: OptimizationConfig) -> List[Dict[str, Any]]:
        """进化种群"""
        new_population = []

        # 精英保留
        elite_count = max(1, int(config.population_size * 0.1))
        elite_indices = sorted(range(len(fitness_scores)),
                               key=lambda i: fitness_scores[i], reverse=True)[:elite_count]

        for idx in elite_indices:
            new_population.append(population[idx].copy())

        # 生成新个体
        while len(new_population) < config.population_size:
            # 选择父母
            parent1 = self._tournament_selection(population, fitness_scores)
            parent2 = self._tournament_selection(population, fitness_scores)

            # 交叉
            if random.random() < config.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()

            # 变异
            if random.random() < config.mutation_rate:
                child1 = self._mutate(child1)
            if random.random() < config.mutation_rate:
                child2 = self._mutate(child2)

            new_population.extend([child1, child2])

        return new_population[:config.population_size]

    def _tournament_selection(self, population: List[Dict[str, Any]],
                              fitness_scores: List[float], tournament_size: int = 3) -> Dict[str, Any]:
        """锦标赛选择"""
        tournament_indices = random.sample(range(len(population)),
                                           min(tournament_size, len(population)))
        best_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return population[best_idx].copy()

    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """交叉操作"""
        child1 = parent1.copy()
        child2 = parent2.copy()

        # 对每个参数进行交叉
        for key in parent1.keys():
            if random.random() < 0.5:
                child1[key], child2[key] = child2[key], child1[key]

        return child1, child2

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """变异操作"""
        mutated = individual.copy()

        for key, value in mutated.items():
            if random.random() < 0.1:  # 10%的参数发生变异
                if isinstance(value, float):
                    # 高斯变异
                    noise = random.gauss(0, abs(value) * 0.1 + 0.01)
                    mutated[key] = max(0.01, value + noise)
                elif isinstance(value, bool):
                    mutated[key] = not value

        return mutated

    def _calculate_diversity(self, population: List[Dict[str, Any]]) -> float:
        """计算种群多样性"""
        if len(population) < 2:
            return 0.0

        # 简化的多样性计算
        total_distance = 0
        count = 0

        for i in range(len(population)):
            for j in range(i + 1, len(population)):
                distance = self._calculate_individual_distance(
                    population[i], population[j])
                total_distance += distance
                count += 1

        return total_distance / count if count > 0 else 0.0

    def _calculate_individual_distance(self, ind1: Dict[str, Any], ind2: Dict[str, Any]) -> float:
        """计算个体间距离"""
        distance = 0.0
        common_keys = set(ind1.keys()) & set(ind2.keys())

        for key in common_keys:
            val1, val2 = ind1[key], ind2[key]
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                distance += abs(val1 - val2)
            elif isinstance(val1, bool) and isinstance(val2, bool):
                distance += 0 if val1 == val2 else 1

        return distance

    def _extract_numeric_parameters(self, pattern_config) -> Dict[str, float]:
        """提取数值参数"""
        numeric_params = {}

        if pattern_config.parameters:
            for key, value in pattern_config.parameters.items():
                if isinstance(value, (int, float)):
                    numeric_params[key] = float(value)

        # 添加默认参数
        numeric_params.update({
            "confidence_threshold": pattern_config.confidence_threshold,
            "min_body_ratio": 0.3,
            "shadow_ratio_threshold": 2.0
        })

        return numeric_params

    def _save_optimized_version(self, pattern_name: str, base_config,
                                optimized_params: Dict[str, Any],
                                description: str, score: float) -> int:
        """保存优化后的版本"""
        # 生成优化后的算法代码
        optimized_code = self._generate_optimized_code(
            base_config, optimized_params)

        # 保存版本
        version_id = self.version_manager.save_version(
            pattern_id=0,  # 需要获取正确的pattern_id
            pattern_name=pattern_name,
            algorithm_code=optimized_code,
            parameters=optimized_params,
            description=description,
            optimization_method="auto_optimization"
        )

        return version_id

    def _generate_optimized_code(self, base_config, optimized_params: Dict[str, Any]) -> str:
        """生成优化后的算法代码"""
        # 这里需要实现代码生成逻辑
        # 简化版本：返回原始代码并更新参数

        original_code = base_config.algorithm_code

        # 替换参数值
        optimized_code = original_code
        for param_name, param_value in optimized_params.items():
            # 简单的字符串替换（实际应该使用AST解析）
            pattern = f"{param_name}\\s*=\\s*[\\d\\.]+|{param_name}\\s*=\\s*True|{param_name}\\s*=\\s*False"
            replacement = f"{param_name} = {param_value}"
            optimized_code = re.sub(pattern, replacement, optimized_code)

        return optimized_code


def create_algorithm_optimizer(debug_mode: bool = False) -> AlgorithmOptimizer:
    """创建算法优化器实例"""
    return AlgorithmOptimizer(debug_mode=debug_mode)


if __name__ == "__main__":
    # 测试算法优化器
    optimizer = create_algorithm_optimizer(debug_mode=True)

    # 创建优化配置
    config = OptimizationConfig(
        method="genetic",
        max_iterations=10,
        population_size=5
    )

    # 优化锤头线算法
    result = optimizer.optimize_algorithm("hammer", config)

    logger.info(f"\n优化结果:")
    logger.info(f"  方法: {result['method']}")
    logger.info(f"  最佳评分: {result['best_score']:.3f}")
    logger.info(f"  基准评分: {result['baseline_score']:.3f}")
    logger.info(f"  性能提升: {result['improvement_percentage']:.3f}%")
    logger.info(f"  迭代次数: {result['iterations']}")
    logger.info(f"  最佳版本ID: {result['best_version_id']}")
