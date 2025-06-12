#!/usr/bin/env python3
"""
系统性能评估模块

提供全面的系统性能评估功能，包括：
- 交易策略性能评估
- 形态识别性能评估
- 系统运行性能评估
- 风险调整后收益评估
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import sqlite3
import json
from dataclasses import dataclass
from enum import Enum


class PerformanceMetricType(Enum):
    """性能指标类型"""
    RETURN = "return"           # 收益指标
    RISK = "risk"              # 风险指标
    EFFICIENCY = "efficiency"   # 效率指标
    STABILITY = "stability"     # 稳定性指标


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    name: str
    value: float
    type: PerformanceMetricType
    description: str
    benchmark: Optional[float] = None
    score: Optional[float] = None


class PerformanceEvaluator:
    """系统性能评估器"""

    def __init__(self, db_path: str = 'db/hikyuu_system.db'):
        """
        初始化性能评估器

        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.metrics_cache = {}

    def evaluate_strategy_performance(self,
                                      strategy_name: str,
                                      returns: pd.Series,
                                      benchmark_returns: Optional[pd.Series] = None,
                                      risk_free_rate: float = 0.03) -> Dict[str, PerformanceMetric]:
        """
        评估策略性能

        Args:
            strategy_name: 策略名称
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            risk_free_rate: 无风险利率

        Returns:
            性能指标字典
        """
        metrics = {}

        # 基础收益指标
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1

        metrics['total_return'] = PerformanceMetric(
            name="总收益率",
            value=total_return,
            type=PerformanceMetricType.RETURN,
            description="策略总收益率"
        )

        metrics['annual_return'] = PerformanceMetric(
            name="年化收益率",
            value=annual_return,
            type=PerformanceMetricType.RETURN,
            description="策略年化收益率"
        )

        # 风险指标
        volatility = returns.std() * np.sqrt(252)
        max_drawdown = self._calculate_max_drawdown(returns)

        metrics['volatility'] = PerformanceMetric(
            name="年化波动率",
            value=volatility,
            type=PerformanceMetricType.RISK,
            description="策略年化波动率"
        )

        metrics['max_drawdown'] = PerformanceMetric(
            name="最大回撤",
            value=max_drawdown,
            type=PerformanceMetricType.RISK,
            description="策略最大回撤"
        )

        # 风险调整收益指标
        if volatility > 0:
            sharpe_ratio = (annual_return - risk_free_rate) / volatility
            metrics['sharpe_ratio'] = PerformanceMetric(
                name="夏普比率",
                value=sharpe_ratio,
                type=PerformanceMetricType.EFFICIENCY,
                description="风险调整后收益指标"
            )

        if max_drawdown < 0:
            calmar_ratio = annual_return / abs(max_drawdown)
            metrics['calmar_ratio'] = PerformanceMetric(
                name="卡玛比率",
                value=calmar_ratio,
                type=PerformanceMetricType.EFFICIENCY,
                description="年化收益与最大回撤比率"
            )

        # 基准比较指标
        if benchmark_returns is not None:
            excess_returns = returns - benchmark_returns
            tracking_error = excess_returns.std() * np.sqrt(252)

            if tracking_error > 0:
                information_ratio = excess_returns.mean() * 252 / tracking_error
                metrics['information_ratio'] = PerformanceMetric(
                    name="信息比率",
                    value=information_ratio,
                    type=PerformanceMetricType.EFFICIENCY,
                    description="相对基准的风险调整收益"
                )

        # 稳定性指标
        win_rate = (returns > 0).mean()
        metrics['win_rate'] = PerformanceMetric(
            name="胜率",
            value=win_rate,
            type=PerformanceMetricType.STABILITY,
            description="盈利交易占比"
        )

        return metrics

    def evaluate_pattern_performance(self,
                                     pattern_name: str,
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> Dict[str, PerformanceMetric]:
        """
        评估形态识别性能

        Args:
            pattern_name: 形态名称
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            性能指标字典
        """
        metrics = {}

        try:
            conn = sqlite3.connect(self.db_path)

            # 构建查询条件
            where_clause = "WHERE pattern_type = ?"
            params = [pattern_name]

            if start_date:
                where_clause += " AND trigger_date >= ?"
                params.append(start_date.strftime('%Y-%m-%d'))

            if end_date:
                where_clause += " AND trigger_date <= ?"
                params.append(end_date.strftime('%Y-%m-%d'))

            # 查询形态历史数据
            query = f"""
                SELECT 
                    COUNT(*) as total_signals,
                    AVG(confidence) as avg_confidence,
                    AVG(return_rate) as avg_return,
                    COUNT(CASE WHEN is_successful = 1 THEN 1 END) as successful_signals,
                    AVG(CASE WHEN is_successful = 1 THEN return_rate END) as avg_successful_return,
                    AVG(CASE WHEN is_successful = 0 THEN return_rate END) as avg_failed_return
                FROM pattern_history 
                {where_clause}
            """

            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()

            if result and result[0] > 0:
                total_signals, avg_confidence, avg_return, successful_signals, avg_successful_return, avg_failed_return = result

                # 信号质量指标
                metrics['total_signals'] = PerformanceMetric(
                    name="信号总数",
                    value=total_signals,
                    type=PerformanceMetricType.EFFICIENCY,
                    description="形态识别信号总数"
                )

                metrics['avg_confidence'] = PerformanceMetric(
                    name="平均置信度",
                    value=avg_confidence or 0,
                    type=PerformanceMetricType.EFFICIENCY,
                    description="形态识别平均置信度"
                )

                # 成功率指标
                success_rate = successful_signals / total_signals if total_signals > 0 else 0
                metrics['success_rate'] = PerformanceMetric(
                    name="成功率",
                    value=success_rate,
                    type=PerformanceMetricType.STABILITY,
                    description="形态识别成功率"
                )

                # 收益指标
                metrics['avg_return'] = PerformanceMetric(
                    name="平均收益率",
                    value=avg_return or 0,
                    type=PerformanceMetricType.RETURN,
                    description="形态信号平均收益率"
                )

                if avg_successful_return is not None:
                    metrics['avg_successful_return'] = PerformanceMetric(
                        name="成功信号平均收益",
                        value=avg_successful_return,
                        type=PerformanceMetricType.RETURN,
                        description="成功形态信号平均收益率"
                    )

                if avg_failed_return is not None:
                    metrics['avg_failed_return'] = PerformanceMetric(
                        name="失败信号平均收益",
                        value=avg_failed_return,
                        type=PerformanceMetricType.RETURN,
                        description="失败形态信号平均收益率"
                    )

            conn.close()

        except Exception as e:
            print(f"评估形态性能失败: {e}")

        return metrics

    def evaluate_system_performance(self) -> Dict[str, PerformanceMetric]:
        """
        评估系统运行性能

        Returns:
            系统性能指标字典
        """
        metrics = {}

        try:
            import psutil
            import time

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage'] = PerformanceMetric(
                name="CPU使用率",
                value=cpu_percent,
                type=PerformanceMetricType.EFFICIENCY,
                description="系统CPU使用率",
                benchmark=80.0  # 80%为基准
            )

            # 内存使用率
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = PerformanceMetric(
                name="内存使用率",
                value=memory.percent,
                type=PerformanceMetricType.EFFICIENCY,
                description="系统内存使用率",
                benchmark=80.0  # 80%为基准
            )

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            metrics['disk_usage'] = PerformanceMetric(
                name="磁盘使用率",
                value=disk.percent,
                type=PerformanceMetricType.EFFICIENCY,
                description="系统磁盘使用率",
                benchmark=90.0  # 90%为基准
            )

        except ImportError:
            print("psutil未安装，无法获取系统性能指标")
        except Exception as e:
            print(f"获取系统性能指标失败: {e}")

        return metrics

    def generate_performance_report(self,
                                    strategy_name: Optional[str] = None,
                                    pattern_name: Optional[str] = None,
                                    include_system: bool = True) -> Dict[str, Any]:
        """
        生成性能报告

        Args:
            strategy_name: 策略名称
            pattern_name: 形态名称
            include_system: 是否包含系统性能

        Returns:
            完整性能报告
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'summary': {},
            'recommendations': []
        }

        # 策略性能评估
        if strategy_name:
            # 这里需要从数据库获取策略收益数据
            # 暂时使用模拟数据
            returns = pd.Series(np.random.normal(0.001, 0.02, 252))
            strategy_metrics = self.evaluate_strategy_performance(strategy_name, returns)
            report['metrics']['strategy'] = {k: self._metric_to_dict(v) for k, v in strategy_metrics.items()}

        # 形态性能评估
        if pattern_name:
            pattern_metrics = self.evaluate_pattern_performance(pattern_name)
            report['metrics']['pattern'] = {k: self._metric_to_dict(v) for k, v in pattern_metrics.items()}

        # 系统性能评估
        if include_system:
            system_metrics = self.evaluate_system_performance()
            report['metrics']['system'] = {k: self._metric_to_dict(v) for k, v in system_metrics.items()}

        # 生成总结和建议
        report['summary'] = self._generate_summary(report['metrics'])
        report['recommendations'] = self._generate_recommendations(report['metrics'])

        return report

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """计算最大回撤"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    def _metric_to_dict(self, metric: PerformanceMetric) -> Dict[str, Any]:
        """将性能指标转换为字典"""
        return {
            'name': metric.name,
            'value': metric.value,
            'type': metric.type.value,
            'description': metric.description,
            'benchmark': metric.benchmark,
            'score': metric.score
        }

    def _generate_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能总结"""
        summary = {
            'overall_score': 0.0,
            'strengths': [],
            'weaknesses': [],
            'key_metrics': {}
        }

        # 计算综合评分
        scores = []

        # 策略评分
        if 'strategy' in metrics:
            strategy_score = self._calculate_strategy_score(metrics['strategy'])
            scores.append(strategy_score)
            summary['key_metrics']['strategy_score'] = strategy_score

        # 形态评分
        if 'pattern' in metrics:
            pattern_score = self._calculate_pattern_score(metrics['pattern'])
            scores.append(pattern_score)
            summary['key_metrics']['pattern_score'] = pattern_score

        # 系统评分
        if 'system' in metrics:
            system_score = self._calculate_system_score(metrics['system'])
            scores.append(system_score)
            summary['key_metrics']['system_score'] = system_score

        if scores:
            summary['overall_score'] = np.mean(scores)

        return summary

    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于指标生成建议
        if 'strategy' in metrics:
            strategy_metrics = metrics['strategy']

            if 'sharpe_ratio' in strategy_metrics and strategy_metrics['sharpe_ratio']['value'] < 1.0:
                recommendations.append("夏普比率偏低，建议优化风险管理策略")

            if 'max_drawdown' in strategy_metrics and abs(strategy_metrics['max_drawdown']['value']) > 0.2:
                recommendations.append("最大回撤过大，建议加强止损控制")

        if 'system' in metrics:
            system_metrics = metrics['system']

            if 'cpu_usage' in system_metrics and system_metrics['cpu_usage']['value'] > 80:
                recommendations.append("CPU使用率过高，建议优化算法性能")

            if 'memory_usage' in system_metrics and system_metrics['memory_usage']['value'] > 80:
                recommendations.append("内存使用率过高，建议优化内存管理")

        return recommendations

    def _calculate_strategy_score(self, strategy_metrics: Dict[str, Any]) -> float:
        """计算策略评分"""
        score = 50.0  # 基础分

        # 夏普比率评分
        if 'sharpe_ratio' in strategy_metrics:
            sharpe = strategy_metrics['sharpe_ratio']['value']
            if sharpe > 2.0:
                score += 20
            elif sharpe > 1.0:
                score += 10
            elif sharpe > 0.5:
                score += 5

        # 最大回撤评分
        if 'max_drawdown' in strategy_metrics:
            drawdown = abs(strategy_metrics['max_drawdown']['value'])
            if drawdown < 0.05:
                score += 15
            elif drawdown < 0.1:
                score += 10
            elif drawdown < 0.2:
                score += 5

        # 胜率评分
        if 'win_rate' in strategy_metrics:
            win_rate = strategy_metrics['win_rate']['value']
            if win_rate > 0.6:
                score += 15
            elif win_rate > 0.5:
                score += 10
            elif win_rate > 0.4:
                score += 5

        return min(score, 100.0)

    def _calculate_pattern_score(self, pattern_metrics: Dict[str, Any]) -> float:
        """计算形态评分"""
        score = 50.0  # 基础分

        # 成功率评分
        if 'success_rate' in pattern_metrics:
            success_rate = pattern_metrics['success_rate']['value']
            if success_rate > 0.8:
                score += 25
            elif success_rate > 0.6:
                score += 15
            elif success_rate > 0.5:
                score += 10

        # 平均置信度评分
        if 'avg_confidence' in pattern_metrics:
            confidence = pattern_metrics['avg_confidence']['value']
            if confidence > 0.8:
                score += 15
            elif confidence > 0.6:
                score += 10
            elif confidence > 0.5:
                score += 5

        # 平均收益评分
        if 'avg_return' in pattern_metrics:
            avg_return = pattern_metrics['avg_return']['value']
            if avg_return > 0.05:
                score += 10
            elif avg_return > 0.02:
                score += 5
            elif avg_return > 0:
                score += 2

        return min(score, 100.0)

    def _calculate_system_score(self, system_metrics: Dict[str, Any]) -> float:
        """计算系统评分"""
        score = 100.0  # 满分开始

        # CPU使用率扣分
        if 'cpu_usage' in system_metrics:
            cpu_usage = system_metrics['cpu_usage']['value']
            if cpu_usage > 90:
                score -= 30
            elif cpu_usage > 80:
                score -= 20
            elif cpu_usage > 70:
                score -= 10

        # 内存使用率扣分
        if 'memory_usage' in system_metrics:
            memory_usage = system_metrics['memory_usage']['value']
            if memory_usage > 90:
                score -= 25
            elif memory_usage > 80:
                score -= 15
            elif memory_usage > 70:
                score -= 8

        # 磁盘使用率扣分
        if 'disk_usage' in system_metrics:
            disk_usage = system_metrics['disk_usage']['value']
            if disk_usage > 95:
                score -= 20
            elif disk_usage > 90:
                score -= 10
            elif disk_usage > 85:
                score -= 5

        return max(score, 0.0)


def create_performance_evaluator(db_path: str = 'db/hikyuu_system.db') -> PerformanceEvaluator:
    """
    创建性能评估器实例

    Args:
        db_path: 数据库路径

    Returns:
        性能评估器实例
    """
    return PerformanceEvaluator(db_path)


if __name__ == "__main__":
    # 测试代码
    evaluator = create_performance_evaluator()

    # 生成性能报告
    report = evaluator.generate_performance_report(
        pattern_name="hammer",
        include_system=True
    )

    print("性能评估报告:")
    print("=" * 50)
    print(f"总体评分: {report['summary']['overall_score']:.1f}")
    print(f"生成时间: {report['timestamp']}")

    if report['recommendations']:
        print("\n改进建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
